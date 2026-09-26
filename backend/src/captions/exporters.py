import html

from captions.segmentation import visible_text
from core.contracts import CaptionProfile, Cue


def timestamp(milliseconds: int, separator: str = ".") -> str:
    seconds, ms = divmod(milliseconds, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}{separator}{ms:03}"


def webvtt(cues: list[Cue], names: dict[str, str], profile: CaptionProfile) -> str:
    blocks = ["WEBVTT\n"]
    for index, cue in enumerate(sorted(cues, key=lambda c: c.start_ms), 1):
        text = html.escape(visible_text(cue, names, profile), quote=False)
        blocks.append(
            f"cue-{index}\n{timestamp(cue.start_ms)} --> {timestamp(cue.end_ms)}\n{text}\n"
        )
    return "\n".join(blocks) + "\n"


def srt(cues: list[Cue], names: dict[str, str], profile: CaptionProfile) -> str:
    blocks = []
    for index, cue in enumerate(sorted(cues, key=lambda c: c.start_ms), 1):
        text = visible_text(cue, names, profile).replace("\x00", "")
        blocks.append(
            f"{index}\n{timestamp(cue.start_ms, ',')} --> {timestamp(cue.end_ms, ',')}\n{text}\n"
        )
    return "\n".join(blocks) + "\n"
