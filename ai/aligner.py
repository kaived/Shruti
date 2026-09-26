import logging
import math
import os
import unicodedata
from itertools import pairwise
from pathlib import Path
from typing import Any

from core.contracts import Transcript

log = logging.getLogger(__name__)


def _match_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    return "".join(
        char for char in normalized if not unicodedata.category(char).startswith("P")
    ).strip()


def _alignment_segments(transcript: Transcript) -> list[dict[str, float | str]]:
    """Bound acoustic alignment work without losing per-word verification."""
    segments: list[dict[str, float | str]] = []
    group = []

    def flush() -> None:
        if group:
            segments.append(
                {
                    "start": group[0].start_ms / 1000,
                    "end": max(word.end_ms for word in group) / 1000,
                    "text": " ".join(word.text for word in group),
                }
            )
            group.clear()

    for word in transcript.words:
        if group and (
            word.end_ms - group[0].start_ms > 12_000
            or word.start_ms - group[-1].end_ms > 1_500
            or (
                word.speaker_id is not None
                and group[-1].speaker_id is not None
                and word.speaker_id != group[-1].speaker_id
            )
            or len(group) >= 20
        ):
            flush()
        group.append(word)
    flush()
    # stable-ts rejects overlapping or unsorted segments. Overlapping speakers can make
    # one segment end after the next begins, so make boundaries strictly ascending.
    for previous, current in pairwise(segments):
        prev_start, prev_end = float(previous["start"]), float(previous["end"])
        start, end = float(current["start"]), float(current["end"])
        start = max(start, prev_start + 0.01)
        if prev_end > start:
            previous["end"] = prev_end = max(prev_start + 0.01, start)
        current["start"] = max(start, prev_end)
        current["end"] = max(end, float(current["start"]) + 0.01)
    return segments


class StableWhisperAligner:
    """Acoustically refine Groq words with a local multilingual Whisper model.

    An unmatched or zero-duration word keeps its original coarse timestamp and
    makes the complete flag false. These timings are never certified as aligned.
    """

    def __init__(self, model=None, model_size: str = "small"):
        self.model: Any = model
        self.model_size = model_size

    def align(self, audio: Path, transcript: Transcript) -> Transcript:
        if not audio.is_file():
            raise FileNotFoundError(f"Alignment audio is missing: {audio}")
        if not transcript.words:
            return transcript.model_copy(
                update={
                    "provider": f"{transcript.provider}+stable-ts/{self.model_size}",
                    "alignment_complete": True,
                }
            )
        if self.model is None:
            import stable_whisper

            cache = Path(os.getenv("SHRUTI_MODEL_CACHE_DIR", "data/models")) / "whisper"
            cache.mkdir(parents=True, exist_ok=True)
            self.model = stable_whisper.load_model(
                self.model_size, device="cpu", download_root=str(cache)
            )
        # stable-ts attaches align_words dynamically; its stubs mistype it as a Tensor.
        model: Any = self.model
        input_segments = _alignment_segments(transcript)
        try:
            result = model.align_words(
                str(audio), input_segments, language="bn", verbose=None, regroup=False
            )
            returned = [
                word
                for segment in result.to_dict()["segments"]
                for word in segment.get("words", [])
            ]
        except Exception:
            log.exception("Forced alignment failed for %s", audio)
            return transcript.model_copy(update={"alignment_complete": False})
        if len(returned) != len(transcript.words):
            log.warning(
                "Forced alignment returned %s words for %s input words",
                len(returned),
                len(transcript.words),
            )
            return transcript.model_copy(update={"alignment_complete": False})

        def validated_word(original, result_word):
            start = result_word.get("start")
            end = result_word.get("end")
            same_text = _match_text(original.text) == _match_text(
                str(result_word.get("word", ""))
            )
            valid = (
                same_text
                and isinstance(start, int | float)
                and isinstance(end, int | float)
                and math.isfinite(start)
                and math.isfinite(end)
                and 0 <= start < end
                and abs(start * 1000 - original.start_ms) <= 1500
                and abs(end * 1000 - original.end_ms) <= 1500
            )
            if not valid:
                return None
            start_ms, end_ms = round(start * 1000), round(end * 1000)
            if end_ms <= start_ms:
                return None
            return original.model_copy(update={"start_ms": start_ms, "end_ms": end_ms})

        words = []
        complete = True
        invalid_indices = []
        for index, (original, result_word) in enumerate(
            zip(transcript.words, returned, strict=True)
        ):
            aligned_word = validated_word(original, result_word)
            if aligned_word is None:
                invalid_indices.append(index)
                words.append(original)
            else:
                words.append(aligned_word)

        def conflicts():
            return [
                index
                for index in range(len(words) - 1)
                if words[index].start_ms > words[index + 1].start_ms
            ]

        violations = conflicts()
        repair_indices = set(invalid_indices) | {
            item for at in violations for item in (at, at + 1)
        }
        if repair_indices:
            log.info(
                "Rechecking %s uncertain aligned words against their original audio windows",
                len(repair_indices),
            )
            # A long grouped segment can shift a short word across its neighbor.
            # Re-run only uncertain/conflicting words with original coarse bounds.
            for index in sorted(repair_indices):
                original = transcript.words[index]
                try:
                    single = model.align_words(
                        str(audio),
                        [
                            {
                                "start": original.start_ms / 1000,
                                "end": original.end_ms / 1000,
                                "text": original.text,
                            }
                        ],
                        language="bn",
                        verbose=None,
                        regroup=False,
                    )
                    candidates = [
                        word
                        for segment in single.to_dict()["segments"]
                        for word in segment.get("words", [])
                    ]
                    corrected = (
                        validated_word(original, candidates[0])
                        if len(candidates) == 1
                        else None
                    )
                except Exception:
                    log.exception(
                        "Single-word alignment fallback failed for %s", original.id
                    )
                    corrected = None
                if corrected is None:
                    complete = False
                    words[index] = original
                else:
                    words[index] = corrected
            if conflicts():
                log.warning(
                    "Forced alignment remains non-monotonic after local correction"
                )
                return transcript.model_copy(update={"alignment_complete": False})
        return transcript.model_copy(
            update={
                "provider": f"{transcript.provider}+stable-ts/{self.model_size}",
                "words": words,
                "alignment_complete": complete,
            }
        )


class MonotonicAligner:
    """Preserve ASR timestamps without claiming that forced alignment ran.

    A real Bengali/code-switched acoustic aligner must replace this adapter. It
    deliberately returns ``alignment_complete=False`` so QC cannot mistake
    cleaned-up ASR timestamps for independent forced-alignment evidence.
    """

    def align(self, audio: Path, transcript: Transcript) -> Transcript:
        if not audio.is_file():
            raise FileNotFoundError(f"Alignment audio is missing: {audio}")
        return Transcript(
            provider="asr-timestamp-pass-through",
            model_version="1.0.0",
            words=transcript.words,
            speakers=transcript.speakers,
            speaker_turns=transcript.speaker_turns,
            overlapping_speech=transcript.overlapping_speech,
            recognition_warnings=transcript.recognition_warnings,
            recognition_complete=transcript.recognition_complete,
            diarization_complete=transcript.diarization_complete,
            alignment_complete=False,
        )
