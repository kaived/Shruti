from pathlib import Path

from core.contracts import Transcript


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
            recognition_complete=transcript.recognition_complete,
            diarization_complete=transcript.diarization_complete,
            alignment_complete=False,
        )
