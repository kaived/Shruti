import hashlib
import json
import secrets
import shutil
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

import anyio
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import update

from core.config import Settings
from core.database import Database, Job, now
from pipeline.queueing import Dispatcher

ARTIFACTS = {
    "bengali.vtt": "text/vtt",
    "english.srt": "application/x-subrip",
    "hindi.srt": "application/x-subrip",
    "english.vtt": "text/vtt",
    "hindi.vtt": "text/vtt",
    "qc_report.json": "application/json",
    "manifest.json": "application/json",
}


def create_app(settings: Settings | None = None, dispatcher=None) -> FastAPI:
    settings = settings or Settings()
    db = Database(settings)
    dispatch = dispatcher or Dispatcher(settings)

    @asynccontextmanager
    async def lifespan(app):
        db.initialize()
        yield
        db.engine.dispose()

    app = FastAPI(title="Shruti", version="0.1.0", lifespan=lifespan)
    app.state.database = db
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type", "X-Upload-Key"],
    )

    def authorize(job_id: str, request: Request) -> Job:
        bearer = request.headers.get("authorization", "")
        token = (
            bearer[7:]
            if bearer.startswith("Bearer ")
            else request.cookies.get(f"shruti_{job_id}", "")
        )
        with db.sessions() as session:
            job = session.get(Job, job_id)
            if (
                not job
                or not token
                or not secrets.compare_digest(
                    job.token_hash, hashlib.sha256(token.encode()).hexdigest()
                )
            ):
                raise HTTPException(404, "Job not found or access denied")
            return job

    def summary(job: Job) -> dict:
        return {
            key: getattr(job, key)
            for key in (
                "id",
                "filename",
                "state",
                "stage",
                "qc_state",
                "error_code",
                "message",
                "attempts",
                "created_at",
                "updated_at",
                "media",
                "stage_metrics",
            )
        }

    def enqueue(job_id: str) -> None:
        with db.sessions.begin() as session:
            result = session.execute(
                update(Job)
                .where(
                    Job.id == job_id,
                    Job.state.in_(["uploaded", "failed", "blocked", "partial"]),
                    Job.attempts < settings.max_attempts,
                )
                .values(
                    state="queued",
                    stage="queued",
                    attempts=Job.attempts + 1,
                    error_code=None,
                    message=None,
                    updated_at=now(),
                )
            )
            if result.rowcount != 1:
                raise HTTPException(
                    409, "Job is already active, finished, or has reached its attempt limit"
                )
        try:
            dispatch.enqueue(job_id)
        except Exception:
            db.update_job(
                job_id,
                state="failed",
                qc_state="incomplete",
                error_code="QUEUE_UNAVAILABLE",
                message="The processing queue is unavailable. Start Redis and retry.",
            )

    def run_directory(job: Job) -> Path:
        run_id = job.media.get("run_id")
        if not run_id or job.state not in {"completed", "partial"}:
            raise HTTPException(409, "Results are not ready")
        return settings.data_dir / "jobs" / job.id / "runs" / run_id

    @app.get("/api/health")
    def health():
        return {"status": "ok", "service": "shruti"}

    @app.get("/api/readiness")
    def readiness():
        queue_ok = dispatch.healthy()
        with db.engine.connect() as connection:
            connection.exec_driver_sql("SELECT 1")
        media_ok = bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))
        return JSONResponse(
            {"database": True, "queue": queue_ok, "media_tools": media_ok},
            status_code=200 if queue_ok and media_ok else 503,
        )

    @app.get("/api/capabilities")
    def capabilities():
        return {
            "inference_configured": bool(
                settings.provider_factory and settings.provider_revision != "unconfigured"
            ),
            "max_upload_bytes": settings.max_upload_bytes,
            "max_duration_seconds": settings.max_duration_seconds,
            "upload_key_required": bool(settings.upload_key),
            "caption_profile": "provisional-1",
            "release_approval_available": False,
        }

    @app.post("/api/jobs", status_code=202)
    async def upload(request: Request, filename: str):
        if settings.upload_key and not secrets.compare_digest(
            request.headers.get("x-upload-key", ""), settings.upload_key
        ):
            raise HTTPException(403, "Upload key required")
        clean_name = Path(filename.replace("\\", "/")).name[:255]
        if Path(clean_name).suffix.lower() not in {".mp4", ".mkv", ".webm"}:
            raise HTTPException(415, "Supported upload containers: MP4, MKV, WebM")
        job_id, token = uuid4().hex, secrets.token_urlsafe(32)
        folder = settings.data_dir / "jobs" / job_id
        folder.mkdir(parents=True)
        checksum, size = hashlib.sha256(), 0
        try:
            async with await anyio.open_file(folder / "source", "wb") as output:
                async for chunk in request.stream():
                    size += len(chunk)
                    if size > settings.max_upload_bytes:
                        raise HTTPException(413, "Upload exceeds the configured limit")
                    checksum.update(chunk)
                    await output.write(chunk)
            if size == 0:
                raise HTTPException(400, "The upload is empty")
            with db.sessions.begin() as session:
                session.add(
                    Job(
                        id=job_id,
                        token_hash=hashlib.sha256(token.encode()).hexdigest(),
                        filename=clean_name,
                        sha256=checksum.hexdigest(),
                    )
                )
        except BaseException:
            shutil.rmtree(folder, ignore_errors=True)
            raise
        await anyio.to_thread.run_sync(enqueue, job_id)
        response = JSONResponse({"id": job_id, "access_token": token}, status_code=202)
        response.set_cookie(
            f"shruti_{job_id}",
            token,
            httponly=True,
            secure=settings.cookie_secure,
            samesite="strict",
            path=f"/api/jobs/{job_id}",
        )
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/api/jobs/{job_id}")
    def get_job(job_id: str, request: Request):
        return summary(authorize(job_id, request))

    @app.post("/api/jobs/{job_id}/retry", status_code=202)
    def retry(job_id: str, request: Request):
        authorize(job_id, request)
        enqueue(job_id)
        return {"id": job_id, "message": "Retry requested"}

    @app.get("/api/jobs/{job_id}/media")
    def media(job_id: str, request: Request):
        job = authorize(job_id, request)
        mimetype = {".mp4": "video/mp4", ".webm": "video/webm", ".mkv": "video/x-matroska"}[
            Path(job.filename).suffix.lower()
        ]
        return FileResponse(
            settings.data_dir / "jobs" / job.id / "source",
            media_type=mimetype,
            headers={"Cache-Control": "private, no-store"},
        )

    @app.get("/api/jobs/{job_id}/results")
    def results(job_id: str, request: Request):
        job = authorize(job_id, request)
        folder = run_directory(job)
        return {
            "tracks": json.loads((folder / "tracks.json").read_text(encoding="utf-8")),
            "qc": json.loads((folder / "qc_report.json").read_text(encoding="utf-8")),
            "downloads": list(ARTIFACTS),
        }

    @app.get("/api/jobs/{job_id}/artifacts/{name}")
    def artifact(job_id: str, name: str, request: Request):
        job = authorize(job_id, request)
        if name not in ARTIFACTS:
            raise HTTPException(404, "Unknown artifact")
        path = run_directory(job) / name
        if not path.is_file():
            raise HTTPException(404, "Artifact not available")
        return FileResponse(
            path, media_type=ARTIFACTS[name], headers={"Cache-Control": "private, no-store"}
        )

    return app
