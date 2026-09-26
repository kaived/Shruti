import math
import os
import tempfile
import wave
from pathlib import Path

from core.contracts import RecognitionWarning, Transcript, Word
from groq import Groq


def _value(item, name: str, default=None):
    return (
        item.get(name, default)
        if isinstance(item, dict)
        else getattr(item, name, default)
    )


def _confidence(item) -> float | None:
    value = _value(item, "probability", _value(item, "confidence"))
    if isinstance(value, int | float) and math.isfinite(value) and 0 <= value <= 1:
        return float(value)
    return None


def _deduplicate_overlapping_words(
    words: list[tuple[int, int, str, float | None]],
) -> list[tuple[int, int, str, float | None]]:
    deduplicated: list[tuple[int, int, str, float | None]] = []
    for candidate in words:
        match_index = None
        for index in range(max(0, len(deduplicated) - 4), len(deduplicated)):
            existing = deduplicated[index]
            overlap = max(
                0, min(existing[1], candidate[1]) - max(existing[0], candidate[0])
            )
            shorter = min(existing[1] - existing[0], candidate[1] - candidate[0])
            if (
                overlap
                and overlap / shorter >= 0.5
                and existing[2].casefold() == candidate[2].casefold()
            ):
                match_index = index
                break
        if match_index is None:
            deduplicated.append(candidate)
            continue
        existing = deduplicated[match_index]
        existing_score = existing[3] if existing[3] is not None else -1.0
        candidate_score = candidate[3] if candidate[3] is not None else -1.0
        if candidate_score > existing_score or (
            candidate_score == existing_score
            and candidate[1] - candidate[0] > existing[1] - existing[0]
        ):
            deduplicated[match_index] = candidate
    return sorted(deduplicated, key=lambda item: (item[0], item[1]))


class GroqWhisperTranscriber:
    """Chunked Bengali/code-switched ASR using provider word timestamps.

    Speaker identity is intentionally left unresolved because Whisper word
    timestamps are not diarization evidence. QC will flag the missing speakers.
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        client=None,
        model: str = "whisper-large-v3",
        chunk_seconds: int = 15,
        overlap_seconds: int = 2,
    ):
        if chunk_seconds <= overlap_seconds:
            raise ValueError("Chunk duration must exceed overlap duration")
        if chunk_seconds <= 0 or overlap_seconds < 0:
            raise ValueError("Chunk and overlap durations must be non-negative")
        self.client = client or Groq(
            api_key=api_key or os.getenv("GROQ_API_KEY"), max_retries=6
        )
        self.model = model
        self.chunk_seconds = chunk_seconds
        self.overlap_seconds = overlap_seconds

    def _request(self, chunk: Path):
        prompt = (
            "বাঙালি কথোপকথন ও সংলাপ। বাংলা বাক্যের মধ্যে ব্যবহৃত ইংরেজি শব্দ "
            "স্বাভাবিক বানানে অক্ষুণ্ণ রাখুন। শোনা যায়নি এমন কোনো কথা যোগ করবেন না।"
        )
        with chunk.open("rb") as source:
            return self.client.audio.transcriptions.create(
                file=(chunk.name, source.read()),
                model=self.model,
                language="bn",
                prompt=prompt,
                response_format="verbose_json",
                timestamp_granularities=["word"],
                temperature=0,
            )

    def transcribe(self, audio: Path) -> Transcript:
        if not audio.is_file():
            raise FileNotFoundError(f"Transcription audio is missing: {audio}")

        collected: list[tuple[int, int, str, float | None]] = []
        warnings: list[RecognitionWarning] = []
        with wave.open(str(audio), "rb") as source:
            sample_rate = source.getframerate()
            channels = source.getnchannels()
            sample_width = source.getsampwidth()
            total_frames = source.getnframes()
            if (
                sample_rate <= 0
                or channels <= 0
                or sample_width != 2
                or total_frames <= 0
            ):
                raise ValueError("ASR requires non-empty 16-bit PCM WAV audio")

            chunk_frames = self.chunk_seconds * sample_rate
            overlap_frames = self.overlap_seconds * sample_rate
            total_ms = round(total_frames / sample_rate * 1000)
            starts = list(range(0, total_frames, chunk_frames))
            # Tiny final requests repeatedly caused untimed/hallucinated Groq
            # output. Include a short remainder in the preceding request.
            if len(starts) > 1 and total_frames - starts[-1] < chunk_frames // 4:
                starts.pop()

            with tempfile.TemporaryDirectory(prefix="shruti-asr-") as temporary:
                temp_root = Path(temporary)
                for chunk_index, nominal_start in enumerate(starts):
                    actual_start = max(0, nominal_start - overlap_frames)
                    actual_end = (
                        total_frames
                        if chunk_index == len(starts) - 1
                        else nominal_start + chunk_frames
                    )
                    source.setpos(actual_start)
                    frames = source.readframes(actual_end - actual_start)
                    chunk_path = temp_root / f"chunk-{chunk_index:05d}.wav"
                    with wave.open(str(chunk_path), "wb") as chunk:
                        chunk.setnchannels(channels)
                        chunk.setsampwidth(sample_width)
                        chunk.setframerate(sample_rate)
                        chunk.writeframes(frames)

                    response = self._request(chunk_path)
                    raw_words = _value(response, "words", []) or []
                    if not raw_words:
                        response_text = str(_value(response, "text", "") or "").strip()
                        raw_segments = _value(response, "segments", []) or []
                        if response_text or raw_segments:
                            warnings.append(
                                RecognitionWarning(
                                    code="ASR_UNTIMED_TEXT",
                                    start_ms=round(actual_start / sample_rate * 1000),
                                    end_ms=round(actual_end / sample_rate * 1000),
                                    rejected_words=0,
                                )
                            )
                        continue
                    chunk_duration = (actual_end - actual_start) / sample_rate
                    keep_from_seconds = nominal_start / sample_rate
                    offset_seconds = actual_start / sample_rate
                    rejected_words = 0
                    for item in raw_words:
                        text = str(_value(item, "word", "")).strip()
                        start = _value(item, "start")
                        end = _value(item, "end")
                        if (
                            not text
                            or not isinstance(start, int | float)
                            or not isinstance(end, int | float)
                            or not math.isfinite(start)
                            or not math.isfinite(end)
                            or start < 0
                            or end <= start
                            or end > chunk_duration + 0.5
                        ):
                            rejected_words += 1
                            continue
                        global_start = offset_seconds + float(start)
                        global_end = offset_seconds + float(end)
                        if (
                            chunk_index
                            and (global_start + global_end) / 2 < keep_from_seconds
                        ):
                            continue
                        start_ms = round(global_start * 1000)
                        end_ms = min(total_ms, round(global_end * 1000))
                        if end_ms <= start_ms:
                            rejected_words += 1
                            continue
                        collected.append((start_ms, end_ms, text, _confidence(item)))
                    if rejected_words:
                        warnings.append(
                            RecognitionWarning(
                                code="ASR_INVALID_WORD_TIMESTAMP",
                                start_ms=round(actual_start / sample_rate * 1000),
                                end_ms=round(actual_end / sample_rate * 1000),
                                rejected_words=rejected_words,
                            )
                        )

        collected = _deduplicate_overlapping_words(
            sorted(collected, key=lambda item: (item[0], item[1]))
        )
        words = [
            Word(
                id=f"w{index:07d}",
                text=text,
                start_ms=start_ms,
                end_ms=end_ms,
                speaker_id=None,
                confidence=confidence,
            )
            for index, (start_ms, end_ms, text, confidence) in enumerate(
                collected, start=1
            )
        ]
        return Transcript(
            provider=f"groq/{self.model}",
            model_version=self.model,
            words=words,
            speakers=[],
            recognition_warnings=warnings,
            recognition_complete=not warnings,
            diarization_complete=False,
            alignment_complete=False,
        )
