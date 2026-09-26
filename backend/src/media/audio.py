import json
import math
import subprocess
from pathlib import Path

from core.config import Settings


class MediaError(RuntimeError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


def prepare_media(source: Path, audio: Path, settings: Settings) -> dict:
    try:
        probe = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-protocol_whitelist",
                "file,pipe",
                "-format_whitelist",
                "mov,matroska,webm",
                "-show_format",
                "-show_streams",
                "-of",
                "json",
                str(source),
            ],
            capture_output=True,
            text=True,
            timeout=60,
            check=True,
        )
        metadata = json.loads(probe.stdout)
        streams = metadata.get("streams", [])
        if not any(s.get("codec_type") == "audio" for s in streams):
            raise MediaError("NO_AUDIO", "The uploaded video has no audio stream.")
        if not any(s.get("codec_type") == "video" for s in streams):
            raise MediaError("NO_VIDEO", "A video stream is required.")
        duration = float(metadata.get("format", {}).get("duration", 0))
        if not math.isfinite(duration) or duration <= 0:
            raise MediaError("INVALID_DURATION", "Cannot establish the video duration.")
        if duration > settings.max_duration_seconds:
            raise MediaError("DURATION_LIMIT", "The video exceeds the configured duration limit.")
        audio.parent.mkdir(parents=True, exist_ok=True)
        temporary = audio.with_suffix(".partial.wav")
        try:
            subprocess.run(
                [
                    "ffmpeg",
                    "-nostdin",
                    "-v",
                    "error",
                    "-y",
                    "-copyts",
                    "-start_at_zero",
                    "-protocol_whitelist",
                    "file,pipe",
                    "-format_whitelist",
                    "mov,matroska,webm",
                    "-i",
                    str(source),
                    "-map",
                    "0:a:0",
                    "-vn",
                    "-af",
                    f"aresample=async=1:first_pts=0,apad,atrim=duration={duration}",
                    "-ar",
                    "16000",
                    "-ac",
                    "1",
                    "-c:a",
                    "pcm_s16le",
                    str(temporary),
                ],
                capture_output=True,
                timeout=settings.job_timeout_seconds,
                check=True,
            )
            temporary.replace(audio)
        finally:
            temporary.unlink(missing_ok=True)
        return {
            "duration_ms": round(duration * 1000),
            "format_start_seconds": metadata.get("format", {}).get("start_time", "0"),
            "audio_sample_rate": 16000,
            "audio_channels": 1,
            "audio_stream_selection": "first audio stream",
            "timestamp_origin": "video playback start",
            "streams": [
                {
                    k: s.get(k)
                    for k in (
                        "index",
                        "codec_type",
                        "codec_name",
                        "start_time",
                        "sample_rate",
                        "avg_frame_rate",
                    )
                }
                for s in streams
            ],
        }
    except FileNotFoundError as exc:
        raise MediaError("FFMPEG_MISSING", "FFmpeg and FFprobe must be installed.") from exc
    except (subprocess.SubprocessError, ValueError, KeyError) as exc:
        raise MediaError("MEDIA_DECODE_FAILED", "The file could not be decoded safely.") from exc
