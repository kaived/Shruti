"""Tests for the full MVP pipeline and the held-out validation benchmark.

Toughest test requirement:
Held-out episodes are checked directly for hallucinated subtitle text over silence
or music, unflagged — this is the failure mode that makes automated captioning unshippable.
The QC report's review queue is also compared against the actual error list, not just
accepted at face value.
"""

import io

import srt as srt_parser
import webvtt as vtt_parser

from captions.exporters import srt, webvtt
from captions.segmentation import segment
from core.contracts import (
    AudioEvidence,
    CaptionProfile,
    Cue,
    Interval,
    ShotAnalysis,
    Speaker,
    Transcript,
    Word,
)
from qc.benchmark import audit_unflagged_hallucinations, compare_review_queue
from qc.evaluation import evaluate


def build_held_out_episode_scenario():
    """Builds a realistic synthetic held-out episode scenario with controlled ground-truth errors.

    Timeline: 60,000 ms (60 seconds)
    1. 0s - 10s: Clean Bengali dialogue (Speaker s1) with speech evidence.
    2. 10s - 20s: Pure background music (NO speech). ASR hallucinates phantom Bengali words.
    3. 20s - 30s: Background music WITH genuine Bengali dialogue (Speaker s2) - real speech under music.
    4. 30s - 40s: Silence. ASR hallucinates repetitive Bengali text.
    5. 40s - 48s: Real speech occurred in audio, but ASR missed it completely (no words).
    6. 48s - 54s: Bengali dialogue spanning a visual shot cut at 50.5s.
    7. 55s - 58s: Bengali dialogue with excessive reading speed (CPS > 17).
    """
    duration_ms = 60000

    # 1. Transcript words (including hallucinations)
    words = [
        # Segment 1: Clean dialogue (valid) -> 1s to 6.5s (duration 5.5s <= 7s)
        Word(id="w01", text="নমস্কার", start_ms=1000, end_ms=2500, speaker_id="s1"),
        Word(id="w02", text="সবাইকে", start_ms=2600, end_ms=4500, speaker_id="s1"),
        Word(id="w03", text="স্বাগতম।", start_ms=4600, end_ms=6500, speaker_id="s1"),
        # Segment 2: Hallucination over pure music (NO speech in audio evidence) -> 12s to 18s
        Word(id="w04", text="ধন্যবাদ", start_ms=12000, end_ms=14000, speaker_id="s1"),
        Word(id="w05", text="দেখার", start_ms=14100, end_ms=16000, speaker_id="s1"),
        Word(id="w06", text="জন্য।", start_ms=16100, end_ms=18000, speaker_id="s1"),
        # Segment 3: Real speech under music (valid speech) -> 21s to 26.5s
        Word(id="w07", text="আমি", start_ms=21000, end_ms=22500, speaker_id="s2"),
        Word(id="w08", text="এখানে", start_ms=22600, end_ms=24500, speaker_id="s2"),
        Word(id="w09", text="আছি।", start_ms=24600, end_ms=26500, speaker_id="s2"),
        # Segment 4: Hallucination over silence (NO speech in audio evidence) -> 32s to 36.5s
        Word(id="w10", text="হ্যাঁ", start_ms=32000, end_ms=33500, speaker_id="s1"),
        Word(id="w11", text="হ্যাঁ", start_ms=33600, end_ms=35000, speaker_id="s1"),
        Word(id="w12", text="হ্যাঁ।", start_ms=35100, end_ms=36500, speaker_id="s1"),
        # Segment 5 (40s - 48s): Intentionally omitted from transcript to simulate missed speech
        # Segment 6: Dialogue spanning cut at 50500 ms -> 49s to 52s
        Word(id="w13", text="দৃশ্য", start_ms=49000, end_ms=50000, speaker_id="s1"),
        Word(id="w14", text="বদল।", start_ms=50100, end_ms=52000, speaker_id="s1"),
        # Segment 7: High CPS dialogue -> 55s to 56.5s (1.5s, 44 chars -> CPS = 29.3 > 17)
        Word(
            id="w15",
            text="অত্যন্তদ্রুতকথাবলছিযাতেসিপিএসসীমাঅতিক্রমকরে।",
            start_ms=55000,
            end_ms=56500,
            speaker_id="s2",
        ),
    ]

    speakers = [
        Speaker(id="s1", display_name="অমিত", name_status="confirmed"),
        Speaker(id="s2", display_name="সুচিত্রা", name_status="confirmed"),
    ]

    transcript = Transcript(
        provider="synthetic-test",
        model_version="test-held-out",
        words=words,
        speakers=speakers,
        recognition_complete=True,
        diarization_complete=True,
        alignment_complete=True,
    )

    # 2. Independent Audio Evidence
    audio = AudioEvidence(
        provider="synthetic-acoustic-test",
        model_version="test-vad-v1",
        complete=True,
        independent_of_asr=True,
        evaluated_duration_ms=duration_ms,
        speech=[
            Interval(start_ms=900, end_ms=6600),  # Matches Segment 1
            Interval(start_ms=20500, end_ms=27000),  # Matches Segment 3 (speech under music)
            Interval(start_ms=40000, end_ms=47500),  # Segment 5: Real speech that ASR missed!
            Interval(start_ms=48800, end_ms=52200),  # Matches Segment 6
            Interval(start_ms=54800, end_ms=56800),  # Matches Segment 7
        ],
        music=[
            Interval(start_ms=10000, end_ms=30000),  # Music spanning Segments 2 & 3
        ],
        sounds=[],
    )

    # 3. Shot analysis
    shots = ShotAnalysis(
        provider="synthetic-shot-test",
        model_version="test-shots-v1",
        complete=True,
        cuts_ms=[50500],  # Cut straddled by Segment 6 (49000 to 52000)
    )

    profile = CaptionProfile()

    # 4. Generate segmented Bengali cues
    bn_cues = segment(transcript, audio, shots, profile)

    # 5. Generate translations linked to Bengali cues
    tracks: dict[str, list[Cue]] = {"bn": bn_cues, "en": [], "hi": []}

    translations_en = {
        bn_cues[0].id: "Welcome everyone.",
        bn_cues[1].id: "Thanks for watching.",  # Translation of hallucinated cue over music
        bn_cues[2].id: "I am here.",
        bn_cues[3].id: "Yes yes yes.",  # Translation of hallucinated cue over silence
        bn_cues[4].id: "Scene change.",
        bn_cues[5].id: "Speaking very fast.",
    }
    translations_hi = {
        bn_cues[0].id: "सभी का स्वागत है।",
        bn_cues[1].id: "देखने के लिए धन्यवाद।",
        bn_cues[2].id: "मैं यहाँ हूँ।",
        bn_cues[3].id: "हाँ हाँ हाँ।",
        bn_cues[4].id: "दृश्य परिवर्तन।",
        bn_cues[5].id: "बहुत तेजी से बोल रहा हूँ।",
    }

    for cue in bn_cues:
        if cue.kind != "speech":
            continue
        tracks["en"].append(
            Cue(
                id=f"en-{cue.id}",
                language="en",
                text=translations_en.get(cue.id, "Translated text"),
                start_ms=cue.start_ms,
                end_ms=cue.end_ms,
                source_cue_ids=[cue.id],
            )
        )
        tracks["hi"].append(
            Cue(
                id=f"hi-{cue.id}",
                language="hi",
                text=translations_hi.get(cue.id, "अनुवादित पाठ"),
                start_ms=cue.start_ms,
                end_ms=cue.end_ms,
                source_cue_ids=[cue.id],
            )
        )

    # 6. Define known ground-truth errors
    hallucination_cue_music = bn_cues[1].id
    speech_under_music_cue_id = bn_cues[2].id
    hallucination_cue_silence = bn_cues[3].id
    cut_cue_id = bn_cues[4].id
    cps_cue_id = bn_cues[5].id

    ground_truth_errors = [
        {
            "code": "SUSPECTED_HALLUCINATION",
            "cue_id": hallucination_cue_music,
            "start_ms": 12000,
            "end_ms": 18000,
            "severity": "critical",
            "description": "Hallucinated dialogue over pure background music",
        },
        {
            "code": "SUSPECTED_HALLUCINATION",
            "cue_id": hallucination_cue_silence,
            "start_ms": 32000,
            "end_ms": 36500,
            "severity": "critical",
            "description": "Hallucinated dialogue over pure silence",
        },
        {
            "code": "SPEECH_WITHOUT_TEXT",
            "start_ms": 40000,
            "end_ms": 47500,
            "severity": "high",
            "description": "Acoustic speech evidence omitted from transcript",
        },
        {
            "code": "SHOT_CROSSING",
            "cue_id": cut_cue_id,
            "start_ms": 49000,
            "end_ms": 52000,
            "severity": "high",
            "description": "Subtitle straddles visual cut at 50.5s",
        },
        {
            "code": "CPS_EXCEEDED",
            "cue_id": cps_cue_id,
            "start_ms": 55000,
            "end_ms": 56500,
            "severity": "medium",
            "description": "Excessive reading speed",
        },
    ]

    return (
        tracks,
        transcript,
        audio,
        shots,
        duration_ms,
        profile,
        ground_truth_errors,
        speech_under_music_cue_id,
    )


def test_toughest_test_held_out_hallucinations_and_review_queue():
    """Toughest test:

    Held-out episodes are checked directly for hallucinated subtitle text over silence
    or music, unflagged — this is the failure mode that makes automated captioning unshippable.
    The QC report's review queue is also compared against the actual error list,
    not just accepted at face value.
    """
    (
        tracks,
        transcript,
        audio,
        shots,
        duration_ms,
        profile,
        ground_truth_errors,
        speech_under_music_cue_id,
    ) = build_held_out_episode_scenario()

    # Step 1: Run the evaluation engine to generate the QC report and ranked review queue
    report = evaluate(tracks, transcript, audio, shots, duration_ms, profile)

    # Step 2: Directly audit for unflagged hallucinated text over silence or music
    unflagged_hallucinations = audit_unflagged_hallucinations(
        tracks, transcript, audio, report, profile
    )

    # The PS2 auto-disqualifier condition: unflagged hallucinations must be ZERO!
    assert len(unflagged_hallucinations) == 0, (
        f"Auto-disqualifier triggered: Found {len(unflagged_hallucinations)} unflagged hallucinated cues: {unflagged_hallucinations}"
    )

    # Step 3: Verify that genuine speech under music was NOT rejected as hallucination
    hallucination_issues_for_speech_under_music = [
        issue
        for issue in report.issues
        if issue.code == "SUSPECTED_HALLUCINATION" and speech_under_music_cue_id in issue.cue_ids
    ]
    assert len(hallucination_issues_for_speech_under_music) == 0, (
        "Genuine speech under music must not be falsely flagged as hallucination!"
    )

    # Step 4: Compare review queue against the actual ground-truth error list
    benchmark_metrics = compare_review_queue(report, ground_truth_errors)

    # Assert 100% recall on ground-truth errors
    assert benchmark_metrics["missed_count"] == 0, (
        f"QC review queue missed ground-truth errors: {benchmark_metrics['missed_errors']}"
    )
    assert benchmark_metrics["recall"] == 1.0

    # Step 5: Verify review queue ranking order: Critical -> High -> Medium
    assert benchmark_metrics["ranking_order_valid"] is True, (
        "Review queue must strictly prioritize critical severity issues before high and medium!"
    )

    severities = [issue.severity for issue in report.issues]
    first_critical_idx = next((i for i, s in enumerate(severities) if s == "critical"), None)
    first_high_idx = next((i for i, s in enumerate(severities) if s == "high"), None)
    first_medium_idx = next((i for i, s in enumerate(severities) if s == "medium"), None)

    assert first_critical_idx is not None
    if first_high_idx is not None:
        assert first_critical_idx < first_high_idx
    if first_medium_idx is not None and first_high_idx is not None:
        assert first_high_idx < first_medium_idx

    # Step 6: Verify hallucination uncertainty propagation to translations
    # English and Hindi cues referencing the hallucinated Bengali cues must receive SOURCE_UNCERTAINTY flags
    hallucinated_cue_ids = {tracks["bn"][1].id, tracks["bn"][3].id}
    source_uncertainty_issues = [i for i in report.issues if i.code == "SOURCE_UNCERTAINTY"]
    flagged_translation_cues = {cid for issue in source_uncertainty_issues for cid in issue.cue_ids}

    for lang in ("en", "hi"):
        for cue in tracks[lang]:
            if any(src in hallucinated_cue_ids for src in cue.source_cue_ids):
                assert cue.id in flagged_translation_cues, (
                    f"Translation cue {cue.id} referencing hallucinated source was not flagged with SOURCE_UNCERTAINTY"
                )

    # Step 7: Release readiness and status
    assert report.release_ready is False
    assert report.status == "review_required"


def test_unflagged_hallucination_audit_detects_slippage():
    """Verify that if an unsupported cue were not flagged, the audit function immediately catches it."""
    (
        tracks,
        transcript,
        audio,
        shots,
        duration_ms,
        profile,
        _,
        _,
    ) = build_held_out_episode_scenario()

    # Generate report then artificially strip the hallucination flags
    report = evaluate(tracks, transcript, audio, shots, duration_ms, profile)
    report.issues = [i for i in report.issues if i.code != "SUSPECTED_HALLUCINATION"]

    unflagged = audit_unflagged_hallucinations(tracks, transcript, audio, report, profile)
    # Both hallucinated cues (over music and over silence) must be identified as unflagged
    assert len(unflagged) == 2
    assert {u["cue_id"] for u in unflagged} == {tracks["bn"][1].id, tracks["bn"][3].id}


def test_end_to_end_mvp_pipeline_flow():
    """Test full MVP pipeline from input to subtitle exports with speaker naming and QC queue."""
    (
        tracks,
        transcript,
        audio,
        shots,
        duration_ms,
        profile,
        _,
        _,
    ) = build_held_out_episode_scenario()

    # 1. Verify speaker naming is reflected in segmentation
    names = {s.id: s.display_name for s in transcript.speakers if s.name_status == "confirmed"}
    assert names["s1"] == "অমিত"
    assert names["s2"] == "সুচিত্রা"

    # 2. Verify Bengali WebVTT export contains character speaker prefix
    vtt_content = webvtt(tracks["bn"], names, profile)
    parsed_vtt = vtt_parser.from_buffer(io.StringIO(vtt_content))
    assert len(parsed_vtt) > 0
    assert "অমিত: নমস্কার সবাইকে স্বাগতম।" in vtt_content

    # 3. Verify English and Hindi SRT exports parse cleanly
    en_srt_content = srt(tracks["en"], names, profile)
    hi_srt_content = srt(tracks["hi"], names, profile)

    parsed_en_srt = list(srt_parser.parse(en_srt_content))
    parsed_hi_srt = list(srt_parser.parse(hi_srt_content))

    assert len(parsed_en_srt) == len(tracks["en"])
    assert len(parsed_hi_srt) == len(tracks["hi"])
    assert "Welcome everyone." in parsed_en_srt[0].content
    assert "सभी का स्वागत है।" in parsed_hi_srt[0].content

    # 4. Verify QC report structure
    report = evaluate(tracks, transcript, audio, shots, duration_ms, profile)
    assert report.checks["speech_support"] == "checked"
    assert report.checks["alignment"] == "checked"
    assert report.checks["shot_boundaries"] == "checked"
    assert len(report.issues) > 0
