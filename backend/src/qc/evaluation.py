from captions.segmentation import visible_text
from core.contracts import (
    AudioEvidence,
    CaptionProfile,
    Cue,
    Interval,
    Issue,
    QCReport,
    ShotAnalysis,
    Transcript,
)


def covered_ms(target: Interval, intervals: list[Interval]) -> int:
    pieces = sorted(
        (max(target.start_ms, x.start_ms), min(target.end_ms, x.end_ms))
        for x in intervals
        if x.start_ms < target.end_ms and x.end_ms > target.start_ms
    )
    total, last_end = 0, target.start_ms
    for start, end in pieces:
        total += max(0, end - max(start, last_end))
        last_end = max(last_end, end)
    return total


def evaluate(
    tracks: dict[str, list[Cue]],
    transcript: Transcript,
    audio: AudioEvidence,
    shots: ShotAnalysis,
    duration_ms: int,
    profile: CaptionProfile,
) -> QCReport:
    issues: list[Issue] = []
    words = {w.id: w for w in transcript.words}
    names = {
        s.id: s.display_name or s.id for s in transcript.speakers if s.name_status == "confirmed"
    }
    speech_checked = (
        audio.complete and audio.independent_of_asr and audio.evaluated_duration_ms >= duration_ms
    )
    incomplete = not (
        transcript.recognition_complete
        and transcript.diarization_complete
        and transcript.alignment_complete
        and speech_checked
        and shots.complete
    )

    def add(code, severity, language, start, end, reason, cue_ids=None, evidence=None):
        issues.append(
            Issue(
                id=f"issue-{len(issues) + 1:05d}",
                code=code,
                severity=severity,
                language=language,
                start_ms=start,
                end_ms=end,
                cue_ids=cue_ids or [],
                reason=reason,
                evidence=evidence or {},
            )
        )

    if incomplete:
        add(
            "QC_INCOMPLETE",
            "critical",
            "all",
            0,
            duration_ms,
            "Complete recognition, diarization, independent speech evidence, forced alignment "
            "and shot analysis are required.",
        )
    for language in ("bn", "en", "hi"):
        if language not in tracks:
            incomplete = True
            add("TRACK_MISSING", "critical", language, 0, duration_ms, "Required track is missing.")
            continue
        seen_ids: set[str] = set()
        previous: Cue | None = None
        repetitions: dict[str, list[Cue]] = {}
        for cue in tracks[language]:

            def flag(code, severity, reason, evidence=None, cue=cue, language=language):
                add(code, severity, language, cue.start_ms, cue.end_ms, reason, [cue.id], evidence)

            if cue.id in seen_ids:
                flag("DUPLICATE_CUE_ID", "critical", "Cue IDs must be unique within a track.")
            seen_ids.add(cue.id)
            if previous and cue.start_ms < previous.start_ms:
                flag("CUE_ORDER", "critical", "Cues must be ordered on the media timeline.")
            elif previous and cue.start_ms < previous.end_ms:
                flag(
                    "CUE_OVERLAP",
                    "high",
                    "Adjacent cues overlap and require timing review.",
                    {"previous_cue_id": previous.id},
                )
            normalized = " ".join(cue.text.casefold().split())
            if cue.kind == "speech" and normalized:
                occurrences = repetitions.setdefault(normalized, [])
                occurrences.append(cue)
                occurrences[:] = [
                    item for item in occurrences if cue.start_ms - item.end_ms <= 10000
                ]
                if len(occurrences) == 3:
                    flag(
                        "SUSPICIOUS_REPETITION",
                        "high",
                        "The same text repeats three times in a short interval; verify it against audio.",
                        {"cue_ids": [item.id for item in occurrences]},
                    )
            previous = cue
            if cue.end_ms > duration_ms:
                flag("OUT_OF_BOUNDS", "high", "Cue extends beyond the media duration.")
            if any(cue.start_ms < t < cue.end_ms for t in shots.cuts_ms):
                flag("SHOT_CROSSING", "high", "Cue straddles a detected shot change.")
            text = visible_text(cue, names, profile)
            length = len(text.replace("\n", ""))
            cps = length / ((cue.end_ms - cue.start_ms) / 1000)
            if cps > profile.max_cps[language]:
                flag(
                    "CPS_EXCEEDED",
                    "medium",
                    "Reading speed exceeds the provisional profile.",
                    {"cps": round(cps, 2), "limit": profile.max_cps[language]},
                )
            if len(text.splitlines()) > profile.max_lines or any(
                len(line) > profile.max_line_length for line in text.splitlines()
            ):
                flag(
                    "LINE_LIMIT_EXCEEDED",
                    "medium",
                    "Caption does not fit the configured line limits.",
                )
            if not profile.min_duration_ms <= cue.end_ms - cue.start_ms <= profile.max_duration_ms:
                flag("CUE_DURATION", "medium", "Cue duration is outside the provisional profile.")
            if cue.language != language:
                flag("LANGUAGE_MISMATCH", "critical", "Cue is in the wrong output track.")
            if language == "bn" and cue.kind == "speech":
                if not cue.speaker_ids:
                    flag("SPEAKER_UNCERTAIN", "high", "Speaker attribution is unresolved.")
                source = [words[w] for w in cue.source_word_ids if w in words]
                if not source or len(source) != len(cue.source_word_ids):
                    flag(
                        "SOURCE_LINK_MISSING",
                        "critical",
                        "Cannot trace this cue to recognized words.",
                    )
                elif speech_checked:
                    unsupported = [
                        w
                        for w in source
                        if covered_ms(w, audio.speech) / (w.end_ms - w.start_ms)
                        < profile.min_speech_support
                    ]
                    if unsupported:
                        flag(
                            "SUSPECTED_HALLUCINATION",
                            "critical",
                            "Recognized words have weak independent speech support. Listen before use.",
                            {
                                "word_ids": [w.id for w in unsupported],
                                "music_overlap_ms": sum(
                                    covered_ms(w, audio.music) for w in unsupported
                                ),
                                "rule_threshold": profile.min_speech_support,
                            },
                        )
    if speech_checked:
        for span in audio.speech:
            coverage = covered_ms(span, list(transcript.words)) / (span.end_ms - span.start_ms)
            if coverage < 0.4:
                add(
                    "SPEECH_WITHOUT_TEXT",
                    "high",
                    "bn",
                    span.start_ms,
                    span.end_ms,
                    "Speech evidence has little transcript coverage; inspect for omitted dialogue.",
                    evidence={"coverage": round(coverage, 3)},
                )
    source_ids = {c.id for c in tracks.get("bn", []) if c.kind == "speech"}
    flagged_sources = {
        cid
        for issue in issues
        if issue.language == "bn" and issue.severity in {"critical", "high"}
        for cid in issue.cue_ids
    }
    for language in ("en", "hi"):
        represented = set()
        for cue in tracks.get(language, []):
            linked = set(cue.source_cue_ids)
            represented |= linked
            if not linked or not linked <= source_ids:
                add(
                    "TRANSLATION_SOURCE_INVALID",
                    "critical",
                    language,
                    cue.start_ms,
                    cue.end_ms,
                    "Translation is missing valid Bengali source references.",
                    [cue.id],
                )
            if linked & flagged_sources:
                add(
                    "SOURCE_UNCERTAINTY",
                    "high",
                    language,
                    cue.start_ms,
                    cue.end_ms,
                    "The Bengali source requires review; verify this translation too.",
                    [cue.id],
                    {"source_cue_ids": sorted(linked & flagged_sources)},
                )
        if source_ids - represented:
            add(
                "TRANSLATION_INCOMPLETE",
                "critical",
                language,
                0,
                duration_ms,
                "Some Bengali speech cues have no linked translation.",
                evidence={"source_cue_ids": sorted(source_ids - represented)},
            )
    ranks = {"critical": 0, "high": 1, "medium": 2}
    issues.sort(key=lambda item: (ranks[item.severity], item.start_ms, item.id))
    return QCReport(
        status="incomplete"
        if incomplete
        else ("review_required" if issues else "automated_checks_passed"),
        profile=profile,
        checks={
            "recognition": "checked" if transcript.recognition_complete else "incomplete",
            "diarization": "checked" if transcript.diarization_complete else "incomplete",
            "speech_support": "checked" if speech_checked else "incomplete",
            "alignment": "checked" if transcript.alignment_complete else "incomplete",
            "shot_boundaries": "checked" if shots.complete else "incomplete",
            "cue_constraints": "checked",
            "translation_source_coverage": "checked",
            "speaker_identity_accuracy": "not_independently_validated",
            "translation_meaning": "not_independently_validated",
            "sound_event_accuracy": "not_independently_validated",
        },
        issues=issues,
        limitations=[
            "Provisional caption limits and heuristic acoustic thresholds require calibration.",
            "Speech activity and alignment do not prove lexical accuracy.",
            "No validated hallucination, diarization or translation accuracy is claimed.",
            "Automated checks do not grant human release approval.",
        ],
    )
