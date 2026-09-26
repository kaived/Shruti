import logging
import wave
from pathlib import Path

from core.contracts import AudioEvidence

log = logging.getLogger(__name__)


class WaveAcousticAnalyzer:
    """Validate the full waveform without inventing speech or sound labels.

    RMS energy is not reliable independent speech/music classification. Until a
    validated acoustic model is connected, this adapter reports incomplete
    evidence so hallucination QC cannot produce a false clean result.
    """

    def analyze(self, audio: Path, duration_ms: int) -> AudioEvidence:
        if not audio.is_file() or duration_ms <= 0:
            return self._incomplete(0)
        try:
            with wave.open(str(audio), "rb") as source:
                if source.getsampwidth() != 2 or source.getframerate() <= 0:
                    raise ValueError("Expected 16-bit PCM audio")
                expected_frames = source.getnframes()
                channels = source.getnchannels()
                bytes_per_frame = source.getsampwidth() * channels
                frames_read = 0
                while block := source.readframes(source.getframerate() * 60):
                    if len(block) % bytes_per_frame:
                        raise ValueError("Audio contains a partial PCM frame")
                    frames_read += len(block) // bytes_per_frame
            if frames_read != expected_frames:
                raise ValueError("Audio could not be read completely")
        except Exception:
            log.exception("Acoustic evidence validation failed for %s", audio)
            return self._incomplete(0)
        return self._incomplete(duration_ms)

    @staticmethod
    def _incomplete(evaluated_duration_ms: int) -> AudioEvidence:
        return AudioEvidence(
            provider="waveform-validation-only",
            model_version="1.0.0",
            complete=False,
            evaluated_duration_ms=evaluated_duration_ms,
            independent_of_asr=True,
            speech=[],
            music=[],
            sounds=[],
        )
