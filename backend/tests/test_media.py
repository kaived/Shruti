import shutil
import subprocess
import wave

import pytest

from core.config import Settings
from media.audio import MediaError, prepare_media


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="FFmpeg unavailable")
def test_real_ffmpeg_extraction_preserves_duration(tmp_path):
    video = tmp_path / "clip.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-nostdin",
            "-v",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=s=160x90:r=25",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:sample_rate=16000",
            "-t",
            "2",
            "-c:v",
            "mpeg4",
            "-c:a",
            "aac",
            str(video),
        ],
        check=True,
        timeout=30,
    )
    audio = tmp_path / "audio.wav"
    metadata = prepare_media(video, audio, Settings(_env_file=None, data_dir=tmp_path))
    assert metadata["duration_ms"] == 2000
    with wave.open(str(audio)) as decoded:
        assert decoded.getframerate() == 16000
        assert decoded.getnchannels() == 1
        assert abs(decoded.getnframes() / 16000 - 2) < 0.05


def test_invalid_media_does_not_generate_a_caption_result(tmp_path):
    source = tmp_path / "bad.mp4"
    source.write_bytes(b"this is not a video")
    with pytest.raises(MediaError):
        prepare_media(source, tmp_path / "audio.wav", Settings(_env_file=None, data_dir=tmp_path))
