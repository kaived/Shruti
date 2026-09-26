from fastapi.testclient import TestClient

from api.routes import create_app
from core.config import Settings
from pipeline.orchestrator import run_pipeline


class RecordingDispatcher:
    def __init__(self):
        self.jobs = []

    def enqueue(self, job_id):
        self.jobs.append(job_id)

    def healthy(self):
        return True


def test_upload_authorization_blocked_inference_and_retry_limit(tmp_path):
    settings = Settings(_env_file=None, data_dir=tmp_path, max_attempts=1)
    dispatcher = RecordingDispatcher()
    app = create_app(settings, dispatcher)
    with TestClient(app) as client:
        response = client.post("/api/jobs?filename=clip.mp4", content=b"synthetic-container-test")
        assert response.status_code == 202
        access = response.json()
        path = f"/api/jobs/{access['id']}"
        headers = {"Authorization": f"Bearer {access['access_token']}"}
        ranged = client.get(path + "/media", headers={"Range": "bytes=0-4"})
        assert ranged.status_code == 206
        assert ranged.content == b"synth"
        client.cookies.clear()
        assert client.get(path).status_code == 404
        assert client.get(path, headers={"Authorization": "Bearer wrong"}).status_code == 404
        assert client.get(path, headers=headers).json()["state"] == "queued"
        assert dispatcher.jobs == [access["id"]]
        run_pipeline(access["id"], settings)
        result = client.get(path, headers=headers).json()
        assert result["state"] == "blocked"
        assert result["qc_state"] == "incomplete"
        assert result["error_code"] == "PROVIDER_NOT_CONFIGURED"
        assert client.get(path + "/results", headers=headers).status_code == 409
        assert client.post(path + "/retry", headers=headers).status_code == 409
        assert not (tmp_path / "jobs" / access["id"] / "audio.wav").exists()


def test_oversized_upload_is_removed_and_never_queued(tmp_path):
    dispatcher = RecordingDispatcher()
    settings = Settings(_env_file=None, data_dir=tmp_path, max_upload_bytes=4)
    with TestClient(create_app(settings, dispatcher)) as client:
        response = client.post("/api/jobs?filename=large.mp4", content=b"12345")
        assert response.status_code == 413
        assert not list((tmp_path / "jobs").iterdir())
        assert not dispatcher.jobs


def test_upload_key_and_empty_input(tmp_path):
    settings = Settings(_env_file=None, data_dir=tmp_path, upload_key="test-only-key")
    with TestClient(create_app(settings, RecordingDispatcher())) as client:
        assert client.post("/api/jobs?filename=a.mp4", content=b"x").status_code == 403
        assert (
            client.post(
                "/api/jobs?filename=a.mp4", content=b"", headers={"X-Upload-Key": "test-only-key"}
            ).status_code
            == 400
        )


def test_queue_outage_is_visible(tmp_path):
    class UnavailableDispatcher(RecordingDispatcher):
        def enqueue(self, job_id):
            raise ConnectionError("test outage")

    settings = Settings(_env_file=None, data_dir=tmp_path)
    with TestClient(create_app(settings, UnavailableDispatcher())) as client:
        access = client.post("/api/jobs?filename=a.mp4", content=b"test").json()
        job = client.get(f"/api/jobs/{access['id']}").json()
        assert job["state"] == "failed"
        assert job["error_code"] == "QUEUE_UNAVAILABLE"
