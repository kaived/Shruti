import logging
import os
import urllib.request
import wave
from hashlib import md5
from pathlib import Path

from core.contracts import AudioEvidence, Interval, SoundEvent

log = logging.getLogger(__name__)

SOUND_LABELS = {
    "Laughter": "হাসি",
    "Applause": "হাততালি",
    "Telephone bell ringing": "ফোন বাজছে",
    "Knock": "দরজায় কড়া নাড়ার শব্দ",
    "Door": "দরজার শব্দ",
}
PANNS_URL = "https://zenodo.org/record/3987831/files/Cnn14_DecisionLevelMax_mAP%3D0.385.pth?download=1"
PANNS_MD5 = "70539c43c18b6a289b3199c503a82c5a"  # Published by Zenodo; integrity only.
PANNS_SIZE = 327_428_481  # Published by Zenodo.
PANNS_LABELS_URL = "https://storage.googleapis.com/us_audioset/youtube_corpus/v1/csv/class_labels_indices.csv"


def _panns_labels() -> None:
    # panns_inference imports its labels from Path.home() and otherwise invokes
    # an insecure shell wget on import. Supply that small file ourselves first.
    target = Path.home() / "panns_data" / "class_labels_indices.csv"
    if target.is_file() and target.stat().st_size > 1000:
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(PANNS_LABELS_URL, timeout=30) as response:
        contents = response.read(100_001)
    if not 1000 < len(contents) <= 100_000 or not contents.startswith(
        b"index,mid,display_name"
    ):
        raise ValueError("AudioSet class labels are missing or invalid")
    temporary = target.with_suffix(".download")
    temporary.write_bytes(contents)
    temporary.replace(target)


def _panns_checkpoint() -> Path:
    """Download the public model once into a persistent cache, without a shell."""
    override = os.getenv("SHRUTI_PANNS_CHECKPOINT")
    target = (
        Path(override)
        if override
        else Path(os.getenv("SHRUTI_MODEL_CACHE_DIR", "data/models"))
        / "panns"
        / "Cnn14_DecisionLevelMax.pth"
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(".download")

    def valid(path: Path) -> bool:
        if not path.is_file() or path.stat().st_size != PANNS_SIZE:
            return False
        integrity = md5(usedforsecurity=False)
        with path.open("rb") as source:
            while chunk := source.read(1024 * 1024):
                integrity.update(chunk)
        return integrity.hexdigest() == PANNS_MD5

    if valid(target):
        return target
    if valid(temporary):
        temporary.replace(target)
        return target
    if target.is_file() and not temporary.is_file():
        target.replace(temporary)

    offset = temporary.stat().st_size if temporary.is_file() else 0
    if offset >= PANNS_SIZE:
        # A full-length cache with the wrong checksum cannot be resumed.
        offset = 0
    request = urllib.request.Request(
        PANNS_URL,
        headers={"Range": f"bytes={offset}-"} if offset else {},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        if offset and response.status == 206:
            expected_range = f"bytes {offset}-{PANNS_SIZE - 1}/{PANNS_SIZE}"
            if response.headers.get("Content-Range") != expected_range:
                raise ValueError("PANNs checkpoint returned an unexpected byte range")
            mode = "ab"
        elif response.status == 200:
            # Some mirrors ignore Range; restart cleanly in that case.
            offset = 0
            mode = "wb"
        else:
            raise ValueError(
                "PANNs checkpoint download returned an unexpected response"
            )
        total = offset
        with temporary.open(mode) as output:
            while chunk := response.read(1024 * 1024):
                total += len(chunk)
                if total > PANNS_SIZE:
                    raise ValueError("PANNs checkpoint exceeds published size")
                output.write(chunk)
    if total != PANNS_SIZE:
        raise ValueError(
            "PANNs checkpoint is incomplete; partial download retained for retry"
        )
    if not valid(temporary):
        raise ValueError("PANNs checkpoint checksum mismatch")
    temporary.replace(target)
    return target


def _merged(intervals: list[Interval], gap_ms: int = 100) -> list[Interval]:
    merged: list[Interval] = []
    for span in sorted(intervals, key=lambda item: (item.start_ms, item.end_ms)):
        if merged and span.start_ms <= merged[-1].end_ms + gap_ms:
            merged[-1].end_ms = max(merged[-1].end_ms, span.end_ms)
        else:
            merged.append(Interval(start_ms=span.start_ms, end_ms=span.end_ms))
    return merged


def _subtract(intervals: list[Interval], supported: list[Interval]) -> list[Interval]:
    remaining = []
    for candidate in intervals:
        fragments = [(candidate.start_ms, candidate.end_ms)]
        for known in supported:
            fragments = [
                piece
                for start, end in fragments
                for piece in (
                    [(start, end)]
                    if known.end_ms <= start or known.start_ms >= end
                    else [
                        (start, min(end, known.start_ms)),
                        (max(start, known.end_ms), end),
                    ]
                )
                if piece[1] > piece[0]
            ]
        remaining.extend(
            Interval(start_ms=start, end_ms=end) for start, end in fragments
        )
    return remaining


def _activity_frames(
    values, threshold: float, offset_ms: int, duration_ms: int
) -> list[Interval]:
    """Convert framewise class scores to coarse, local evidence intervals."""
    intervals = []
    if len(values) == 0:
        return intervals
    start = None
    for index, score in enumerate(values):
        if score >= threshold and start is None:
            start = index
        if score < threshold and start is not None:
            begin = offset_ms + round(start * duration_ms / len(values))
            end = offset_ms + round(index * duration_ms / len(values))
            if end > begin:
                intervals.append(Interval(start_ms=begin, end_ms=end))
            start = None
    if start is not None:
        begin = offset_ms + round(start * duration_ms / len(values))
        end = offset_ms + duration_ms
        if end > begin:
            intervals.append(Interval(start_ms=begin, end_ms=end))
    return intervals


class ModelAcousticAnalyzer:
    """Independent Silero speech VAD and PANNs AudioSet sound analysis.

    The models inspect every audio block, including music and quiet regions.
    Thresholds are provisional. A model failure leaves evidence incomplete.
    """

    def __init__(self, *, vad=None, sed=None, labels=None, block_seconds: int = 30):
        self.vad = vad
        self.sed = sed
        self.labels = labels
        self.block_seconds = block_seconds

    def _load_models(self):
        if self.vad is None:
            from silero_vad import load_silero_vad

            self.vad = load_silero_vad(onnx=True)
        if self.sed is None or self.labels is None:
            _panns_labels()
            from panns_inference import SoundEventDetection, labels

            self.sed = SoundEventDetection(
                checkpoint_path=str(_panns_checkpoint()), device="cpu"
            )
            self.labels = labels
        if not {"Speech", "Music"} <= set(self.labels):
            raise ValueError("Acoustic model lacks required speech/music labels")

    def analyze(self, audio: Path, duration_ms: int) -> AudioEvidence:
        if not audio.is_file() or duration_ms <= 0:
            return WaveAcousticAnalyzer._incomplete(0)
        try:
            import numpy as np
            import torch
            from scipy.signal import resample_poly
            from silero_vad import get_speech_timestamps

            self._load_models()
            sed, class_labels = self.sed, self.labels
            if sed is None or class_labels is None:
                raise ValueError("Acoustic models failed to load")
            indexes = {label: index for index, label in enumerate(class_labels)}
            speech, music, uncertain = [], [], []
            sound_candidates: list[tuple[str, Interval, float]] = []
            with wave.open(str(audio), "rb") as source:
                if (
                    source.getframerate() != 16000
                    or source.getnchannels() != 1
                    or source.getsampwidth() != 2
                ):
                    raise ValueError("Acoustic analysis expects mono 16 kHz PCM")
                total_frames = source.getnframes()
                if abs(total_frames / 16 - duration_ms) > 500:
                    raise ValueError("Acoustic audio duration differs from video")
                block_frames = self.block_seconds * 16000
                offsets = list(range(0, total_frames, block_frames))
                # PANNs' CNN cannot pool a sub-second input. Fold a short final
                # remainder into the preceding block so the tail is still analyzed.
                if len(offsets) > 1 and total_frames - offsets[-1] < 5 * 16000:
                    offsets.pop()
                ends = [*offsets[1:], total_frames]
                for frame_offset, block_end in zip(offsets, ends, strict=True):
                    source.setpos(frame_offset)
                    block = source.readframes(block_end - frame_offset)
                    if not block:
                        raise ValueError("Acoustic audio ended early")
                    waveform = (
                        np.frombuffer(block, dtype="<i2").astype(np.float32) / 32768.0
                    )
                    offset_ms = round(frame_offset / 16)
                    block_ms = round(len(waveform) / 16)
                    speech_stamps = get_speech_timestamps(
                        torch.from_numpy(waveform),
                        self.vad,
                        sampling_rate=16000,
                        min_speech_duration_ms=100,
                        min_silence_duration_ms=100,
                        speech_pad_ms=80,
                    )
                    for stamp in speech_stamps:
                        begin = offset_ms + round(stamp["start"] / 16)
                        end = offset_ms + round(stamp["end"] / 16)
                        if end > begin:
                            speech.append(Interval(start_ms=begin, end_ms=end))
                    model_audio = resample_poly(waveform, 2, 1).astype(np.float32)[
                        None, :
                    ]
                    scores = sed.inference(model_audio)
                    if (
                        getattr(scores, "ndim", 0) != 3
                        or scores.shape[0] != 1
                        or scores.shape[2] != len(class_labels)
                    ):
                        raise ValueError("Unexpected sound-event model output shape")
                    frame_scores = scores[0]
                    if "Speech" in indexes:
                        speech.extend(
                            _activity_frames(
                                frame_scores[:, indexes["Speech"]],
                                0.55,
                                offset_ms,
                                block_ms,
                            )
                        )
                        uncertain.extend(
                            _activity_frames(
                                frame_scores[:, indexes["Speech"]],
                                0.2,
                                offset_ms,
                                block_ms,
                            )
                        )
                    if "Music" in indexes:
                        music.extend(
                            _activity_frames(
                                frame_scores[:, indexes["Music"]],
                                0.55,
                                offset_ms,
                                block_ms,
                            )
                        )
                    for name, bengali in SOUND_LABELS.items():
                        if name not in indexes:
                            continue
                        values = frame_scores[:, indexes[name]]
                        for span in _activity_frames(values, 0.85, offset_ms, block_ms):
                            if span.end_ms - span.start_ms >= 300:
                                sound_candidates.append(
                                    (bengali, span, round(float(np.max(values)), 3))
                                )
            speech = _merged(speech)
            music = _merged(music)
            uncertain = _merged(uncertain)
            # Only retain uncertainty where speech has not already been supported.
            uncertain = _subtract(uncertain, speech)
            sounds = [
                SoundEvent(
                    id=f"sfx-{index:05d}",
                    label_bn=label,
                    start_ms=span.start_ms,
                    end_ms=span.end_ms,
                    confidence=score,
                )
                for index, (label, span, score) in enumerate(sound_candidates, 1)
            ]
            return AudioEvidence(
                provider="silero-vad+panns-sed",
                model_version="1.0.0",
                complete=True,
                evaluated_duration_ms=duration_ms,
                independent_of_asr=True,
                speech=speech,
                music=music,
                uncertain_speech=uncertain,
                sounds=sounds,
            )
        except Exception:
            log.exception("Independent acoustic analysis failed for %s", audio)
            return WaveAcousticAnalyzer._incomplete(0)


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
