import textwrap

from core.contracts import AudioEvidence, CaptionProfile, Cue, ShotAnalysis, Transcript


def visible_text(cue: Cue, names: dict[str, str], profile: CaptionProfile) -> str:
    prefix = ""
    if cue.language == "bn" and cue.kind == "speech" and cue.speaker_ids:
        prefix = ", ".join(names.get(s, s) for s in cue.speaker_ids) + ": "
    return "\n".join(
        textwrap.wrap(
            prefix + " ".join(cue.text.split()),
            width=profile.max_line_length,
            break_long_words=False,
            break_on_hyphens=False,
        )
    )


def segment(
    transcript: Transcript, audio: AudioEvidence, shots: ShotAnalysis, profile: CaptionProfile
) -> list[Cue]:
    """Conservative word grouping. Impossible cut/word conflicts remain visible to QC."""
    cues: list[Cue] = []
    group = []

    def flush():
        if not group:
            return
        speakers = sorted({w.speaker_id for w in group if w.speaker_id})
        cues.append(
            Cue(
                id=f"bn-{len(cues) + 1:05d}",
                language="bn",
                start_ms=group[0].start_ms,
                end_ms=max(w.end_ms for w in group),
                text=" ".join(w.text for w in group),
                speaker_ids=speakers,
                source_word_ids=[w.id for w in group],
            )
        )
        group.clear()

    for word in transcript.words:
        if group:
            text_length = len(" ".join(w.text for w in [*group, word]))
            changed = word.speaker_id != group[-1].speaker_id
            cut = any(group[0].start_ms < t <= word.start_ms for t in shots.cuts_ms)
            too_long = word.end_ms - group[0].start_ms > profile.max_duration_ms
            if (
                changed
                or cut
                or too_long
                or text_length > profile.max_line_length * profile.max_lines
            ):
                flush()
        group.append(word)
        if word.text.rstrip().endswith(("।", ".", "?", "!")):
            flush()
    flush()
    for event in audio.sounds:
        cues.append(
            Cue(
                id=f"sound-{event.id}",
                language="bn",
                kind="sound",
                start_ms=event.start_ms,
                end_ms=event.end_ms,
                text=f"[{event.label_bn}]",
            )
        )
    return sorted(cues, key=lambda c: (c.start_ms, c.end_ms, c.id))
