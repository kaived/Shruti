import bisect
import math
import textwrap

from core.contracts import AudioEvidence, CaptionProfile, Cue, ShotAnalysis, Transcript

CUE_GAP_MS = 80  # minimum blank between consecutive dialogue cues (~2 frames)
MAX_LEAD_IN_MS = 300  # a cue may appear slightly before its first word to gain reading time
PAUSE_SPLIT_MS = 1200  # a longer silence always starts a new cue
ATTACH_UNATTRIBUTED_MS = 400  # max gap for an unattributed word to join a speaker's cue


def speaker_prefix(cue: Cue, names: dict[str, str]) -> str:
    if cue.language == "bn" and cue.kind == "speech" and cue.speaker_ids:
        return ", ".join(names.get(s, s) for s in cue.speaker_ids) + ": "
    return ""


def visible_text(cue: Cue, names: dict[str, str], profile: CaptionProfile) -> str:
    return "\n".join(
        textwrap.wrap(
            speaker_prefix(cue, names) + " ".join(cue.text.split()),
            width=profile.max_line_length,
            break_long_words=False,
            break_on_hyphens=False,
        )
    )


def _retime(cues: list[Cue], cuts: list[int], media_end_ms: int, profile: CaptionProfile) -> None:
    """Give each cue reading time inside its shot, without overlapping its neighbours.

    Timing only moves into silence around the cue's own words (a short lead-in and a
    hold after the last word); text is never dropped or rewritten to pass a limit.
    Cues that still violate CPS or a cut after this remain visible to QC.
    """
    for index, cue in enumerate(cues):
        previous_end = cues[index - 1].end_ms + CUE_GAP_MS if index else 0
        next_start = (
            cues[index + 1].start_ms - CUE_GAP_MS if index + 1 < len(cues) else media_end_ms
        )
        position = bisect.bisect_right(cuts, cue.start_ms)
        shot_start = cuts[position - 1] if position else 0
        shot_end = cuts[position] if position < len(cuts) else media_end_ms

        # Never straddle a cut: finish at the cut when the speech runs past it.
        if cue.end_ms > shot_end and shot_end - cue.start_ms >= profile.min_duration_ms // 2:
            cue.end_ms = shot_end
        limit_end = min(next_start, shot_end, cue.start_ms + profile.max_duration_ms, media_end_ms)

        characters = len(visible_text(cue, {}, profile).replace("\n", ""))
        cps_limit = profile.max_cps.get(cue.language, 17)
        needed = max(profile.min_duration_ms, math.ceil(characters / cps_limit * 1000))
        if cue.end_ms - cue.start_ms < needed and limit_end > cue.end_ms:
            cue.end_ms = min(cue.start_ms + needed, limit_end)
        shortfall = needed - (cue.end_ms - cue.start_ms)
        if shortfall > 0:
            earliest = max(previous_end, shot_start, cue.start_ms - MAX_LEAD_IN_MS, 0)
            cue.start_ms = max(earliest, cue.start_ms - shortfall)


def segment(
    transcript: Transcript, audio: AudioEvidence, shots: ShotAnalysis, profile: CaptionProfile
) -> list[Cue]:
    """Group words into readable cues at speaker, shot, pause and sentence boundaries."""
    cues: list[Cue] = []
    group = []
    cuts = sorted(shots.cuts_ms)
    budget = profile.max_line_length * profile.max_lines

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
            prefix = len(word.speaker_id or group[0].speaker_id or "") + 2
            text_length = prefix + len(" ".join(w.text for w in [*group, word]))
            # An unattributed word joins the running line when it follows without a pause;
            # its own speaker_id stays None, so QC evidence is unchanged. Two different
            # known speakers always start a new cue.
            group_speaker = next((w.speaker_id for w in group if w.speaker_id), None)
            gap = word.start_ms - group[-1].end_ms
            if word.speaker_id and group_speaker:
                changed = word.speaker_id != group_speaker
            elif word.speaker_id or group_speaker:
                changed = gap > ATTACH_UNATTRIBUTED_MS
            else:
                changed = False
            cut = any(group[0].start_ms < t <= word.start_ms for t in cuts)
            too_long = word.end_ms - group[0].start_ms > profile.max_duration_ms
            paused = word.start_ms - group[-1].end_ms > PAUSE_SPLIT_MS
            if changed or cut or too_long or paused or text_length > budget:
                flush()
        group.append(word)
        if word.text.rstrip().endswith(("।", ".", "?", "!")):
            flush()
    flush()

    media_end = max(
        audio.evaluated_duration_ms,
        max((w.end_ms for w in transcript.words), default=0),
    )
    _retime(cues, cuts, media_end, profile)

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
