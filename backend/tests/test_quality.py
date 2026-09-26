import io

import pytest
import srt as srt_parser
import webvtt as vtt_parser
from pydantic import ValidationError

from captions.exporters import srt, webvtt
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
from qc.benchmark import audit_unflagged_hallucinations
from qc.evaluation import evaluate


def sample(*, speech=True, music=False, evidence_complete=True, cue_end=2000):
    # Synthetic unit-test data. Never loaded by a live provider or used as a sample-episode transcript.
    word = Word(id="w1", text="না", start_ms=1000, end_ms=2000, speaker_id="speaker-1")
    transcript = Transcript(
        provider="test",
        model_version="test",
        words=[word],
        speakers=[Speaker(id="speaker-1")],
        recognition_complete=True,
        diarization_complete=True,
        alignment_complete=True,
    )
    audio = AudioEvidence(
        provider="test",
        model_version="test",
        complete=evidence_complete,
        independent_of_asr=True,
        evaluated_duration_ms=5000,
        speech=[Interval(start_ms=1000, end_ms=2000)] if speech else [],
        music=[Interval(start_ms=0, end_ms=5000)] if music else [],
    )
    cue = Cue(
        id="bn-1",
        language="bn",
        text="না",
        start_ms=1000,
        end_ms=cue_end,
        speaker_ids=["speaker-1"],
        source_word_ids=["w1"],
    )
    tracks = {"bn": [cue]}
    for language, text in (("en", "No"), ("hi", "नहीं")):
        tracks[language] = [
            Cue(
                id=f"{language}-1",
                language=language,
                text=text,
                start_ms=1000,
                end_ms=cue_end,
                source_cue_ids=["bn-1"],
            )
        ]
    shots = ShotAnalysis(provider="test", model_version="test", complete=True)
    return tracks, transcript, audio, shots


def codes(report):
    return {issue.code for issue in report.issues}


@pytest.mark.parametrize("music", [False, True])
def test_unsupported_words_are_flagged_and_propagate_to_translations(music):
    report = evaluate(*sample(speech=False, music=music), 5000, CaptionProfile())
    assert "SUSPECTED_HALLUCINATION" in codes(report)
    assert {i.language for i in report.issues if i.code == "SOURCE_UNCERTAINTY"} == {"en", "hi"}
    assert not report.release_ready


def test_real_speech_under_music_is_not_automatically_rejected():
    report = evaluate(*sample(speech=True, music=True), 5000, CaptionProfile())
    assert "SUSPECTED_HALLUCINATION" not in codes(report)


def test_caption_lingering_after_actual_words_is_not_hallucination():
    report = evaluate(*sample(cue_end=3500), 5000, CaptionProfile())
    assert "SUSPECTED_HALLUCINATION" not in codes(report)


def test_missing_evidence_cannot_produce_a_clean_qc_status():
    tracks, transcript, audio, shots = sample(evidence_complete=False)
    report = evaluate(tracks, transcript, audio, shots, 5000, CaptionProfile())
    assert report.status == "incomplete"
    assert "QC_INCOMPLETE" in codes(report)
    with pytest.raises(ValueError, match="complete independent"):
        audit_unflagged_hallucinations(tracks, transcript, audio, report)


def test_empty_transcript_cannot_hide_detected_speech():
    tracks, transcript, audio, shots = sample()
    transcript.words = []
    report = evaluate(
        {"bn": [], "en": [], "hi": []}, transcript, audio, shots, 5000, CaptionProfile()
    )
    assert "SPEECH_WITHOUT_TEXT" in codes(report)


def test_shot_crossing_and_missing_translation_are_reported():
    tracks, transcript, audio, shots = sample()
    shots.cuts_ms = [1500]
    tracks["hi"] = []
    report = evaluate(tracks, transcript, audio, shots, 5000, CaptionProfile())
    assert {"SHOT_CROSSING", "TRANSLATION_INCOMPLETE"} <= codes(report)


def test_unknown_speaker_and_duplicate_words_are_invalid_contracts():
    _, transcript, _, _ = sample()
    payload = transcript.model_dump()
    payload["words"].append(payload["words"][0])
    with pytest.raises(ValidationError):
        Transcript.model_validate(payload)
    payload["words"] = [payload["words"][0]]
    payload["speakers"] = []
    with pytest.raises(ValidationError):
        Transcript.model_validate(payload)


def test_exports_parse_with_independent_libraries_and_preserve_script():
    tracks, _, _, _ = sample()
    vtt = vtt_parser.from_buffer(io.StringIO(webvtt(tracks["bn"], {}, CaptionProfile())))
    parsed = list(srt_parser.parse(srt(tracks["hi"], {}, CaptionProfile())))
    assert len(vtt) == len(parsed) == 1
    assert "না" in vtt[0].text
    assert parsed[0].content == "नहीं"
    assert parsed[0].start.total_seconds() == 1
    assert parsed[0].end.total_seconds() == 2


def test_vtt_escapes_model_generated_markup():
    tracks, _, _, _ = sample()
    tracks["bn"][0].text = "<script>alert(1)</script> & text"
    text = webvtt(tracks["bn"], {}, CaptionProfile())
    assert "<script>" not in text
    assert "&lt;script&gt;" in text


def test_srt_preserves_literal_ampersands():
    tracks, _, _, _ = sample()
    tracks["en"][0].text = "R&D"
    text = srt(tracks["en"], {}, CaptionProfile())
    assert "R&D" in text
    assert "R&amp;D" not in text


def test_overlaps_and_short_interval_repetition_are_review_flags():
    tracks, transcript, audio, shots = sample()
    tracks["bn"] = [
        Cue(
            id=f"bn-{index}",
            language="bn",
            text="হ্যাঁ",
            start_ms=start,
            end_ms=end,
            speaker_ids=["speaker-1"],
            source_word_ids=["w1"],
        )
        for index, (start, end) in enumerate(((1000, 2000), (1900, 2600), (2700, 3400)), 1)
    ]
    report = evaluate(tracks, transcript, audio, shots, 5000, CaptionProfile())
    assert {"CUE_OVERLAP", "SUSPICIOUS_REPETITION"} <= codes(report)
