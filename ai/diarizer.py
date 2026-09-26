"""Whole-recording diarization with explicit overlap and uncertainty."""

import os
import wave
from pathlib import Path
from typing import Any

from core.contracts import Interval, Speaker, SpeakerTurn, Transcript
from providers.base import ProviderUnavailable


def _overlaps(turns: list[SpeakerTurn]) -> list[Interval]:
    """Return merged intervals where distinct speakers are active together."""
    edges: list[tuple[int, int, str]] = []
    for turn in turns:
        edges.append((turn.start_ms, 1, turn.speaker_id))
        edges.append((turn.end_ms, -1, turn.speaker_id))
    edges.sort(key=lambda item: (item[0], item[1]))
    active: dict[str, int] = {}
    previous: int | None = None
    spans: list[Interval] = []
    for at, delta, speaker in edges:
        if previous is not None and at > previous and len(active) > 1:
            if spans and spans[-1].end_ms == previous:
                spans[-1].end_ms = at
            else:
                spans.append(Interval(start_ms=previous, end_ms=at))
        active[speaker] = active.get(speaker, 0) + delta
        if active[speaker] <= 0:
            del active[speaker]
        previous = at
    return spans


def assign_speakers(transcript: Transcript, turns: list[SpeakerTurn]) -> Transcript:
    """Use only unambiguous temporal evidence to assign a word to one voice."""
    speaker_ids = sorted({turn.speaker_id for turn in turns})
    speakers = [Speaker(id=speaker_id) for speaker_id in speaker_ids]
    overlaps = _overlaps(turns)
    words = []
    for word in transcript.words:
        span = word.end_ms - word.start_ms
        cover: dict[str, int] = {}
        for turn in turns:
            shared = max(
                0, min(word.end_ms, turn.end_ms) - max(word.start_ms, turn.start_ms)
            )
            if shared:
                cover[turn.speaker_id] = cover.get(turn.speaker_id, 0) + shared
        ranked = sorted(cover.items(), key=lambda item: item[1], reverse=True)
        speaker = None
        if ranked:
            # A clearly dominant voice owns the word; near-even overlap stays unresolved
            # (and remains flagged as OVERLAPPING_SPEECH in QC).
            if ranked[0][1] >= 0.5 * span and (
                len(ranked) == 1 or ranked[0][1] >= 2 * ranked[1][1]
            ):
                speaker = ranked[0][0]
        else:
            # Words in the short gap between turns belong to the adjacent voice.
            nearest = min(
                turns,
                key=lambda turn: max(
                    turn.start_ms - word.end_ms, word.start_ms - turn.end_ms
                ),
                default=None,
            )
            if (
                nearest
                and max(nearest.start_ms - word.end_ms, word.start_ms - nearest.end_ms)
                <= 600
            ):
                speaker = nearest.speaker_id
        words.append(word.model_copy(update={"speaker_id": speaker}))
    return transcript.model_copy(
        update={
            "provider": f"{transcript.provider}+pyannote/community-1",
            "words": words,
            "speakers": speakers,
            "speaker_turns": turns,
            "overlapping_speech": overlaps,
            "diarization_complete": True,
        }
    )


class PyannoteDiarizer:
    """Run Community-1 once over the complete waveform for stable episode IDs."""

    model_id = "pyannote/speaker-diarization-community-1"

    def __init__(self, token: str | None = None, pipeline=None):
        self.token = token or os.getenv("SHRUTI_HF_TOKEN")
        self.pipeline = pipeline

    def diarize(self, audio: Path, transcript: Transcript) -> Transcript:
        if not audio.is_file():
            raise FileNotFoundError(f"Diarization audio is missing: {audio}")
        if self.pipeline is None:
            if not self.token:
                raise ProviderUnavailable(
                    "SHRUTI_HF_TOKEN is required for speaker diarization."
                )
            from huggingface_hub.errors import GatedRepoError
            from pyannote.audio import Pipeline

            try:
                self.pipeline = Pipeline.from_pretrained(
                    self.model_id, token=self.token
                )
            except GatedRepoError as exc:
                raise ProviderUnavailable(
                    "Hugging Face access is not approved for pyannote Community-1. "
                    "Accept its model terms with the account that owns SHRUTI_HF_TOKEN."
                ) from exc
            if self.pipeline is None:
                raise ProviderUnavailable(
                    "The pyannote Community-1 model could not be loaded."
                )
        # The worker already has a canonical mono 16 kHz WAV. Pass the waveform
        # directly so pyannote does not depend on torchcodec's FFmpeg bindings.
        import numpy as np
        import torch

        with wave.open(str(audio), "rb") as source:
            if (
                source.getnchannels() != 1
                or source.getframerate() != 16000
                or source.getsampwidth() != 2
            ):
                raise ValueError("Diarization expects mono 16 kHz PCM audio")
            samples = np.frombuffer(source.readframes(source.getnframes()), dtype="<i2")
            waveform = torch.from_numpy(samples.astype(np.float32) / 32768.0).unsqueeze(
                0
            )
        result: Any = self.pipeline({"waveform": waveform, "sample_rate": 16000})
        annotation = result.speaker_diarization
        labels = sorted(annotation.labels())
        id_map = {label: f"SPEAKER_{index:02d}" for index, label in enumerate(labels)}
        turns = sorted(
            (
                SpeakerTurn(
                    start_ms=max(0, round(segment.start * 1000)),
                    end_ms=round(segment.end * 1000),
                    speaker_id=id_map[label],
                )
                for segment, _, label in annotation.itertracks(yield_label=True)
                if segment.end > segment.start
            ),
            key=lambda turn: (turn.start_ms, turn.end_ms, turn.speaker_id),
        )
        return assign_speakers(transcript, turns)
