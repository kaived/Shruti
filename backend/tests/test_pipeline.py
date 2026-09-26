import pytest
from fastapi.testclient import TestClient

from api.routes import create_app
from core.config import Settings
from core.contracts import AudioEvidence, Cue, Interval, ShotAnalysis, Speaker, Transcript, Word
from pipeline.orchestrator import run_pipeline
from providers.base import Providers


def test_stage_recovery_reuses_completed_inference_and_exports_drafts(tmp_path, monkeypatch):
    # Synthetic adapter doubles are confined to tests. They are never configured in the app.
    import pipeline.orchestrator as pipeline

    calls = {"transcribe": 0, "translate_en": 0}

    class TestAdapters:
        def transcribe(self, audio):
            calls["transcribe"] += 1
            return Transcript(
                provider="test-only",
                model_version="synthetic",
                words=[Word(id="w1", text="না", start_ms=200, end_ms=1200, speaker_id="s1")],
                speakers=[Speaker(id="s1")],
                recognition_complete=True,
                diarization_complete=True,
            )

        def align(self, audio, transcript):
            return transcript.model_copy(update={"alignment_complete": True})

        def analyze(self, audio, duration_ms):
            return AudioEvidence(
                provider="test-only",
                model_version="synthetic",
                complete=True,
                independent_of_asr=True,
                evaluated_duration_ms=duration_ms,
                speech=[Interval(start_ms=200, end_ms=1200)],
            )

        def detect(self, video, duration_ms):
            return ShotAnalysis(provider="test-only", model_version="synthetic", complete=True)

        def translate(self, cues, language):
            if language == "en":
                calls["translate_en"] += 1
                if calls["translate_en"] == 1:
                    raise RuntimeError("Synthetic transient failure")
            return [
                Cue(
                    id=f"{language}-1",
                    language=language,
                    text="No" if language == "en" else "नहीं",
                    start_ms=200,
                    end_ms=1200,
                    source_cue_ids=[cues[0].id],
                )
            ]

    class Queue:
        def enqueue(self, job_id):
            pass

        def healthy(self):
            return True

    def media(source, audio, settings):
        audio.write_bytes(b"test-only-placeholder")
        return {"duration_ms": 2000}

    adapters = TestAdapters()
    monkeypatch.setattr(
        pipeline,
        "load_providers",
        lambda settings: Providers(adapters, adapters, adapters, adapters, adapters),
    )
    monkeypatch.setattr(pipeline, "prepare_media", media)
    settings = Settings(_env_file=None, data_dir=tmp_path, provider_revision="test-only")
    with TestClient(create_app(settings, Queue())) as client:
        access = client.post("/api/jobs?filename=test.mp4", content=b"test-only-input").json()
        job_id = access["id"]
        with pytest.raises(RuntimeError):
            run_pipeline(job_id, settings)
        assert client.get(f"/api/jobs/{job_id}").json()["state"] == "failed"
        assert client.post(f"/api/jobs/{job_id}/retry").status_code == 202
        run_pipeline(job_id, settings)
        job = client.get(f"/api/jobs/{job_id}").json()
        assert job["state"] == "completed"
        assert job["stage_metrics"]["transcription"]["cached"] is True
        assert calls == {"transcribe": 1, "translate_en": 2}
        result = client.get(f"/api/jobs/{job_id}/results").json()
        assert result["qc"]["release_ready"] is False
        for filename in ("bengali.vtt", "english.srt", "hindi.srt", "qc_report.json"):
            assert client.get(f"/api/jobs/{job_id}/artifacts/{filename}").status_code == 200
        assert client.get(f"/api/jobs/{job_id}/artifacts/transcription.json").status_code == 404


def test_partial_retry_reruns_incomplete_stage_without_repeating_unchanged_translation(
    tmp_path, monkeypatch
):
    import pipeline.orchestrator as pipeline

    calls = {"transcribe": 0, "align": 0, "translate_en": 0, "translate_hi": 0}

    class TestAdapters:
        def transcribe(self, audio):
            calls["transcribe"] += 1
            return Transcript(
                provider="test-only",
                model_version="synthetic",
                words=[Word(id="w1", text="না", start_ms=200, end_ms=1200, speaker_id="s1")],
                speakers=[Speaker(id="s1")],
                recognition_complete=True,
                diarization_complete=True,
            )

        def align(self, audio, transcript):
            calls["align"] += 1
            return transcript.model_copy(update={"alignment_complete": calls["align"] > 1})

        def analyze(self, audio, duration_ms):
            return AudioEvidence(
                provider="test-only",
                model_version="synthetic",
                complete=True,
                independent_of_asr=True,
                evaluated_duration_ms=duration_ms,
                speech=[Interval(start_ms=200, end_ms=1200)],
            )

        def detect(self, video, duration_ms):
            return ShotAnalysis(provider="test-only", model_version="synthetic", complete=True)

        def translate(self, cues, language):
            calls[f"translate_{language}"] += 1
            return [
                Cue(
                    id=f"{language}-1",
                    language=language,
                    text="No" if language == "en" else "नहीं",
                    start_ms=200,
                    end_ms=1200,
                    source_cue_ids=[cues[0].id],
                )
            ]

    class Queue:
        def enqueue(self, job_id):
            pass

        def healthy(self):
            return True

    def media(source, audio, settings):
        audio.write_bytes(b"test-only-placeholder")
        return {"duration_ms": 2000}

    adapters = TestAdapters()
    monkeypatch.setattr(
        pipeline,
        "load_providers",
        lambda settings: Providers(adapters, adapters, adapters, adapters, adapters),
    )
    monkeypatch.setattr(pipeline, "prepare_media", media)
    settings = Settings(_env_file=None, data_dir=tmp_path, provider_revision="test-only")
    with TestClient(create_app(settings, Queue())) as client:
        access = client.post("/api/jobs?filename=test.mp4", content=b"test-only-input").json()
        job_id = access["id"]
        run_pipeline(job_id, settings)
        assert client.get(f"/api/jobs/{job_id}").json()["state"] == "partial"
        assert client.post(f"/api/jobs/{job_id}/retry").status_code == 202
        run_pipeline(job_id, settings)
        job = client.get(f"/api/jobs/{job_id}").json()
        assert job["state"] == "completed"
        assert job["stage_metrics"]["translation_en"]["cached"] is True
        assert calls == {
            "transcribe": 1,
            "align": 2,
            "translate_en": 1,
            "translate_hi": 1,
        }
