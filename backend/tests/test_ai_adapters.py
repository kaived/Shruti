import json
import sys
import wave
from types import SimpleNamespace

import pytest
from ai.acoustics import WaveAcousticAnalyzer
from ai.aligner import MonotonicAligner
from ai.shots import SceneCutDetector
from ai.transcriber import GroqWhisperTranscriber
from ai.translator import GroqLLMTranslator

from core.contracts import Cue, Transcript, Word


def write_silence(path, seconds: int, sample_rate: int = 16000):
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(sample_rate)
        output.writeframes(b"\x00\x00" * sample_rate * seconds)


class FakeTranscriptions:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        response = next(self.responses)
        if isinstance(response, SimpleNamespace):
            return response
        return SimpleNamespace(words=response, text="", segments=[])


def transcriber_client(responses):
    transcriptions = FakeTranscriptions(responses)
    client = SimpleNamespace(audio=SimpleNamespace(transcriptions=transcriptions))
    return client, transcriptions


def test_chunked_asr_offsets_words_and_does_not_invent_speakers_or_confidence(tmp_path):
    audio = tmp_path / "audio.wav"
    write_silence(audio, 12)
    client, calls = transcriber_client(
        [
            [
                {"word": "এক", "start": 1.0, "end": 2.0, "probability": 0.8},
                {"word": "সীমা", "start": 4.6, "end": 5.0},
            ],
            [
                {"word": "পুরনো", "start": 0.2, "end": 0.8},
                {"word": "সীমা", "start": 0.8, "end": 1.4},
                {"word": "দুই", "start": 2.0, "end": 3.0},
            ],
            [{"word": "তিন", "start": 1.2, "end": 2.0}],
        ]
    )
    transcript = GroqWhisperTranscriber(
        client=client, chunk_seconds=5, overlap_seconds=1
    ).transcribe(audio)

    assert len(calls.calls) == 3
    assert [word.text for word in transcript.words] == ["এক", "সীমা", "দুই", "তিন"]
    assert [(word.start_ms, word.end_ms) for word in transcript.words] == [
        (1000, 2000),
        (4800, 5400),
        (6000, 7000),
        (10200, 11000),
    ]
    assert [word.confidence for word in transcript.words] == [0.8, None, None, None]
    assert transcript.speakers == []
    assert all(word.speaker_id is None for word in transcript.words)
    assert transcript.recognition_complete is True
    assert transcript.diarization_complete is False
    assert transcript.alignment_complete is False


def test_asr_rejects_missing_word_timestamps_instead_of_estimating_them(tmp_path):
    audio = tmp_path / "audio.wav"
    write_silence(audio, 1)
    client, _ = transcriber_client([SimpleNamespace(words=[], text="কথা", segments=[])])
    with pytest.raises(RuntimeError, match="without word timestamps"):
        GroqWhisperTranscriber(client=client).transcribe(audio)


class FakeCompletions:
    def __init__(self, payload):
        self.payload = payload

    def create(self, **kwargs):
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(self.payload)))]
        )


def translator(payload):
    client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions(payload)))
    return GroqLLMTranslator(client=client)


def source_cue():
    return Cue(id="bn-1", language="bn", text="আমি যাব না", start_ms=100, end_ms=1000)


def test_translation_requires_exact_nonempty_id_coverage_and_never_falls_back_to_source():
    with pytest.raises(RuntimeError, match="omitted"):
        translator({"translations": []}).translate([source_cue()], "en")
    with pytest.raises(RuntimeError, match="copied untranslated"):
        translator({"translations": [{"id": "bn-1", "text": "আমি যাব না"}]}).translate(
            [source_cue()], "en"
        )

    translated = translator({"translations": [{"id": "bn-1", "text": "I will not go."}]}).translate(
        [source_cue()], "en"
    )
    assert translated[0].text == "I will not go."
    assert translated[0].source_cue_ids == ["bn-1"]


def test_unconfigured_alignment_and_acoustics_remain_visibly_incomplete(tmp_path):
    audio = tmp_path / "audio.wav"
    write_silence(audio, 1)
    transcript = Transcript(
        provider="test",
        model_version="test",
        words=[Word(id="w1", text="না", start_ms=100, end_ms=500)],
        speakers=[],
    )
    aligned = MonotonicAligner().align(audio, transcript)
    evidence = WaveAcousticAnalyzer().analyze(audio, 1000)
    assert aligned.words == transcript.words
    assert aligned.alignment_complete is False
    assert evidence.complete is False
    assert evidence.speech == evidence.music == evidence.sounds == []


def test_shot_decode_failure_is_not_reported_as_complete(tmp_path, monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("decode failed")

    fake = SimpleNamespace(ContentDetector=lambda **kwargs: object(), detect=fail)
    monkeypatch.setitem(sys.modules, "scenedetect", fake)
    result = SceneCutDetector().detect(tmp_path / "bad.mp4", 1000)
    assert result.complete is False
    assert result.cuts_ms == []
