"""Direct-to-GCS uploads that bypass Cloud Run's small HTTP request limit."""

import hashlib
import secrets
from collections.abc import Callable
from pathlib import Path
from uuid import uuid4

import anyio
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from core.config import Settings
from core.database import Database, Job, now

CONTENT_TYPES = {
    ".mp4": "video/mp4",
    ".mkv": "video/x-matroska",
    ".webm": "video/webm",
}


class CloudUploadRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=512)
    size_bytes: int = Field(gt=0)


def add_cloud_upload_routes(
    app: FastAPI,
    settings: Settings,
    db: Database,
    authorize: Callable,
    enqueue: Callable,
    storage_client=None,
) -> None:
    def bucket():
        if not settings.gcs_bucket:
            raise HTTPException(503, "Cloud Storage uploads are not configured")
        if storage_client is None:
            from google.cloud import storage

            client = storage.Client()
        else:
            client = storage_client
        return client.bucket(settings.gcs_bucket)

    @app.post("/api/v1/cloud-uploads", status_code=201, tags=["Jobs"])
    async def initiate_cloud_upload(payload: CloudUploadRequest, request: Request):
        if settings.upload_key:
            provided_key = request.headers.get("x-upload-key", "").strip()
            if not provided_key:
                raise HTTPException(403, "Upload key required")
            if not secrets.compare_digest(provided_key, settings.upload_key):
                raise HTTPException(403, "Invalid upload key")
        if payload.size_bytes > settings.max_upload_bytes:
            raise HTTPException(413, "Upload exceeds the configured limit")
        origin = request.headers.get("origin")
        if origin and origin not in settings.allowed_origins:
            raise HTTPException(403, "Upload origin is not allowed")
        filename = Path(payload.filename.replace("\\", "/")).name[:255]
        content_type = CONTENT_TYPES.get(Path(filename).suffix.lower())
        if not content_type:
            raise HTTPException(415, "Supported upload containers: MP4, MKV, WebM")
        job_id, token = uuid4().hex, secrets.token_urlsafe(32)
        blob = bucket().blob(f"jobs/{job_id}/source")
        try:
            upload_url = await anyio.to_thread.run_sync(
                lambda: blob.create_resumable_upload_session(
                    content_type=content_type,
                    size=payload.size_bytes,
                    origin=origin,
                    if_generation_match=0,
                )
            )
        except Exception as exc:
            raise HTTPException(503, "Could not create the Cloud Storage upload session") from exc
        with db.sessions.begin() as session:
            session.add(
                Job(
                    id=job_id,
                    token_hash=hashlib.sha256(token.encode()).hexdigest(),
                    filename=filename,
                    sha256="",
                    state="uploading",
                    media={"upload_expected_size": payload.size_bytes},
                )
            )
        response = JSONResponse(
            {"id": job_id, "access_token": token, "upload_url": upload_url},
            status_code=201,
        )
        response.set_cookie(
            f"shruti_{job_id}",
            token,
            httponly=True,
            secure=settings.cookie_secure,
            samesite="strict",
            path=f"/api/v1/jobs/{job_id}",
        )
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.post("/api/v1/cloud-uploads/{job_id}/finalize", status_code=202, tags=["Jobs"])
    async def finalize_cloud_upload(job_id: str, request: Request):
        job = authorize(job_id, request)
        if job.state != "uploading":
            raise HTTPException(409, "Upload has already been finalized or is not active")
        blob = bucket().blob(f"jobs/{job_id}/source")
        try:
            await anyio.to_thread.run_sync(blob.reload)
        except Exception as exc:
            raise HTTPException(409, "Uploaded object is not available yet") from exc
        if not blob.size or blob.size != job.media.get("upload_expected_size"):
            raise HTTPException(409, "Uploaded object size does not match the requested size")

        def checksum():
            digest = hashlib.sha256()
            with blob.open("rb") as source:
                while chunk := source.read(1024 * 1024):
                    digest.update(chunk)
            return digest.hexdigest()

        try:
            sha256 = await anyio.to_thread.run_sync(checksum)
        except Exception as exc:
            raise HTTPException(503, "Could not verify uploaded object") from exc
        with db.sessions.begin() as session:
            current = session.get(Job, job_id)
            if current is None:
                raise HTTPException(404, "Job not found or access denied")
            if current.state != "uploading":
                raise HTTPException(409, "Upload was finalized concurrently")
            current.sha256 = sha256
            current.state = "uploaded"
            current.stage = "upload_complete"
            current.media = {"gcs_generation": blob.generation, "upload_size": blob.size}
            current.updated_at = now()
        await anyio.to_thread.run_sync(enqueue, job_id)
        response = JSONResponse({"id": job_id, "message": "Upload finalized"}, status_code=202)
        response.headers["Cache-Control"] = "no-store"
        return response
