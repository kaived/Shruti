import hashlib
import json
import secrets
import shutil
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any, cast
from uuid import uuid4

import anyio
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi import Path as PathParam
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import HTTPBearer
from sqlalchemy import CursorResult, update

from api.cloud_uploads import add_cloud_upload_routes
from api.schemas import (
    CapabilitiesResponse,
    ErrorResponse,
    HealthResponse,
    JobResultsResponse,
    JobRetryResponse,
    JobSummaryResponse,
    JobUploadResponse,
    ReadinessResponse,
)
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

API_TAGS = [
    {
        "name": "System & Health",
        "description": "Liveness probes, infrastructure readiness checks, and pipeline capacity introspection.",
    },
    {
        "name": "Jobs",
        "description": "Asynchronous job lifecycle operations: video streaming upload, progress polling, and error retry.",
    },
    {
        "name": "Media & Streaming",
        "description": "Original source video streaming with HTTP 206 Partial Content range requests for synchronized video preview.",
    },
    {
        "name": "Results & Artifacts",
        "description": "Synchronized subtitle tracks (Bengali, English, Hindi), acoustic QC reports, and downloadable export files (.vtt, .srt, .json).",
    },
]

bearer_scheme = HTTPBearer(
    auto_error=False,
    description="Enter the Bearer access token received from POST /api/v1/jobs",
)


def create_app(settings: Settings | None = None, dispatcher=None, storage_client=None) -> FastAPI:
    settings = settings or Settings()
    db = Database(settings)
    dispatch = dispatcher or Dispatcher(settings)

    @asynccontextmanager
    async def lifespan(app):
        db.initialize()
        yield
        db.engine.dispose()

    app = FastAPI(
        title="Shruti Bengali Caption & Subtitle Studio API",
        summary="Automated Bengali speech recognition, multilingual subtitle translation, and acoustic evidence QC review.",
        description="""
## Shruti API Documentation

Shruti is a high-precision subtitle and caption generation platform engineered for Bengali video and audio content.

### Core Capabilities
* **Bengali ASR**: Segmented speech recognition with word-level timestamps and speaker diarization.
* **Multilingual Translation**: Context-aware subtitle translation into English (`en`) and Hindi (`hi`) via the configured Groq model.
* **Evidence-Based Quality Control (QC)**: Independent acoustic verification cross-referencing speech presence, music segments, and shot cut boundaries.
* **Broadcast Subtitle Compliance**: Line wrap constraints, characters-per-second (CPS) velocity limits, and duration thresholds.
* **Multi-Format Export**: Production WebVTT (`.vtt`), SubRip (`.srt`), and machine-readable JSON reports.

### Authentication & Access Control
* **Media Upload**: `POST /api/v1/jobs` creates a job and returns an `access_token` along with an HTTP-only session cookie (`shruti_<job_id>`). If configured, `X-Upload-Key` header is required.
* **Job Endpoints**: All `/api/v1/jobs/{job_id}/*` operations require authorization via either:
  * `Authorization: Bearer <access_token>` header
  * `shruti_<job_id>` session cookie
""",
        version="1.0.0",
        openapi_tags=API_TAGS,
        docs_url="/api-docs",
        redoc_url=None,
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )
    app.state.database = db
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type", "X-Upload-Key", "Cache-Control", "Pragma"],
    )

    def authorize(job_id: str, request: Request) -> Job:
        bearer = request.headers.get("authorization", "")
        # The query token serves <video src> on a separate frontend origin, where
        # neither a bearer header nor the SameSite cookie can be sent.
        token = (
            bearer[7:]
            if bearer.startswith("Bearer ")
            else request.cookies.get(f"shruti_{job_id}", "")
            or request.query_params.get("access_token", "")
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
            if cast(CursorResult, result).rowcount != 1:
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
                message="The processing queue is temporarily unavailable. Please retry in a few moments.",
            )

    def run_directory(job: Job) -> Path:
        run_id = job.media.get("run_id")
        if not run_id or job.state not in {"completed", "partial"}:
            raise HTTPException(409, "Results are not ready")
        return settings.data_dir / "jobs" / job.id / "runs" / run_id

    add_cloud_upload_routes(app, settings, db, authorize, enqueue, storage_client)

    @app.get(
        "/api/v1/health",
        tags=["System & Health"],
        summary="Service Health Check",
        description="Basic liveness probe indicating that the HTTP service is operational.",
        response_model=HealthResponse,
        responses={200: {"description": "Service is healthy and responding."}},
    )
    def health():
        return {"status": "ok", "service": "shruti"}

    @app.get("/api/health", include_in_schema=False)
    def legacy_health():
        return health()

    @app.get(
        "/api/v1/readiness",
        tags=["System & Health"],
        summary="System Readiness Probe",
        description="Verifies connectivity to the database, Redis task queue, and local FFmpeg/FFprobe binaries.",
        response_model=ReadinessResponse,
        responses={
            200: {"description": "All system dependencies are healthy and ready to process jobs."},
            503: {
                "description": "One or more required infrastructure components are unavailable.",
                "model": ReadinessResponse,
            },
        },
    )
    def readiness():
        queue_ok = dispatch.healthy()
        with db.engine.connect() as connection:
            connection.exec_driver_sql("SELECT 1")
        media_ok = bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))
        return JSONResponse(
            {"database": True, "queue": queue_ok, "media_tools": media_ok},
            status_code=200 if queue_ok and media_ok else 503,
        )

    @app.get("/api/readiness", include_in_schema=False)
    def legacy_readiness():
        return readiness()

    @app.get(
        "/api/v1/capabilities",
        tags=["System & Health"],
        summary="Pipeline Capabilities and Limits",
        description="Returns system upload size limits, media duration thresholds, captioning standard version, and inference readiness.",
        response_model=CapabilitiesResponse,
        responses={200: {"description": "Capabilities information returned."}},
    )
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

    @app.post(
        "/api/v1/jobs",
        status_code=202,
        tags=["Jobs"],
        summary="Upload Media and Create Processing Job",
        description=(
            "Streams and stores an incoming binary video file (.mp4, .mkv, .webm) up to 500 MB (or configured limit).\n\n"
            "Creates a new processing job, issues an access token, sets an HTTP-only authentication cookie (`shruti_<job_id>`), "
            "and enqueues the job for background pipeline processing."
        ),
        response_model=JobUploadResponse,
        responses={
            202: {
                "description": "Video uploaded and job successfully enqueued.",
                "model": JobUploadResponse,
            },
            400: {"description": "Empty payload received (0 bytes).", "model": ErrorResponse},
            403: {"description": "Upload key required or invalid.", "model": ErrorResponse},
            413: {
                "description": "File size exceeds the configured upload limit.",
                "model": ErrorResponse,
            },
            415: {
                "description": "Unsupported container format (allowed: MP4, MKV, WebM).",
                "model": ErrorResponse,
            },
        },
        openapi_extra={
            "requestBody": {
                "description": "Raw binary video stream (application/octet-stream, video/mp4, video/webm, video/x-matroska).",
                "required": True,
                "content": {
                    "application/octet-stream": {"schema": {"type": "string", "format": "binary"}},
                    "video/mp4": {"schema": {"type": "string", "format": "binary"}},
                    "video/webm": {"schema": {"type": "string", "format": "binary"}},
                    "video/x-matroska": {"schema": {"type": "string", "format": "binary"}},
                },
            }
        },
    )
    async def upload(
        request: Request,
        filename: Annotated[
            str,
            Query(
                description="Original video filename with extension (.mp4, .mkv, .webm)",
                examples=["clip.mp4"],
            ),
        ],
        x_upload_key: Annotated[
            str | None,
            Header(
                alias="X-Upload-Key",
                description="Optional system upload secret key required when server enforces it.",
            ),
        ] = None,
    ):
        if settings.upload_key:
            provided_key = request.headers.get("x-upload-key", "").strip()
            if not provided_key:
                raise HTTPException(403, "Upload key required")
            if not secrets.compare_digest(provided_key, settings.upload_key):
                raise HTTPException(403, "Invalid upload key")
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
            path=f"/api/v1/jobs/{job_id}",
        )
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.get(
        "/api/v1/jobs/{job_id}",
        tags=["Jobs"],
        summary="Get Job Status and Summary",
        description="Retrieves the current execution state, pipeline stage, acoustic QC state, error details, and extracted media metadata for a job. Requires Bearer authentication or session cookie.",
        response_model=JobSummaryResponse,
        responses={
            200: {"description": "Job summary and status retrieved.", "model": JobSummaryResponse},
            404: {"description": "Job not found or access denied.", "model": ErrorResponse},
        },
    )
    def get_job(
        request: Request,
        job_id: Annotated[
            str,
            PathParam(
                description="Unique 32-character hexadecimal job identifier",
                examples=["7e4a68c09e3e4a289650d3dfa539ebf1"],
            ),
        ],
        _auth: Annotated[Any, Depends(bearer_scheme)] = None,
    ):
        job = authorize(job_id, request)
        # Safety net: a worker killed by the platform (e.g. out of memory) cannot report
        # failure itself. Past the maximum possible run time, stop showing it as active.
        if job.state in {"queued", "running"}:
            try:
                idle = datetime.now(UTC) - datetime.fromisoformat(job.updated_at)
            except ValueError:
                idle = None
            if idle is not None and idle.total_seconds() > settings.job_timeout_seconds + 900:
                db.update_job(
                    job_id,
                    state="failed",
                    qc_state="incomplete",
                    error_code="WORKER_FAILED",
                    message="The job stopped responding and was marked failed. Retry is available.",
                )
                job = authorize(job_id, request)
        return summary(job)

    @app.post(
        "/api/v1/jobs/{job_id}/retry",
        status_code=202,
        tags=["Jobs"],
        summary="Retry Failed or Blocked Job",
        description="Re-enqueues a job that has failed, was blocked by a transient issue (e.g. queue outage), or stopped in a partial state, provided it has not exceeded the maximum allowed attempts.",
        response_model=JobRetryResponse,
        responses={
            202: {"description": "Job successfully re-enqueued.", "model": JobRetryResponse},
            404: {"description": "Job not found or access denied.", "model": ErrorResponse},
            409: {
                "description": "Job is already active, finished, or has reached its attempt limit.",
                "model": ErrorResponse,
            },
        },
    )
    def retry(
        request: Request,
        job_id: Annotated[
            str,
            PathParam(
                description="Unique 32-character hexadecimal job identifier",
                examples=["7e4a68c09e3e4a289650d3dfa539ebf1"],
            ),
        ],
        _auth: Annotated[Any, Depends(bearer_scheme)] = None,
    ):
        authorize(job_id, request)
        enqueue(job_id)
        return {"id": job_id, "message": "Retry requested"}

    @app.get(
        "/api/v1/jobs/{job_id}/media",
        tags=["Media & Streaming"],
        summary="Stream Source Video",
        description="Streams the original uploaded video file with support for HTTP 206 Partial Content range requests, allowing synchronized timeline scrubbing in video players.",
        responses={
            200: {
                "description": "Full video stream.",
                "content": {
                    "video/mp4": {},
                    "video/webm": {},
                    "video/x-matroska": {},
                },
            },
            206: {
                "description": "Partial byte range stream for video scrubbing.",
                "content": {
                    "video/mp4": {},
                    "video/webm": {},
                    "video/x-matroska": {},
                },
            },
            404: {"description": "Job not found or access denied.", "model": ErrorResponse},
        },
    )
    def media(
        request: Request,
        job_id: Annotated[
            str,
            PathParam(
                description="Unique 32-character hexadecimal job identifier",
                examples=["7e4a68c09e3e4a289650d3dfa539ebf1"],
            ),
        ],
        _auth: Annotated[Any, Depends(bearer_scheme)] = None,
    ):
        job = authorize(job_id, request)
        mimetype = {".mp4": "video/mp4", ".webm": "video/webm", ".mkv": "video/x-matroska"}[
            Path(job.filename).suffix.lower()
        ]
        return FileResponse(
            settings.data_dir / "jobs" / job.id / "source",
            media_type=mimetype,
            headers={"Cache-Control": "private, no-store"},
        )

    @app.get(
        "/api/v1/jobs/{job_id}/results",
        tags=["Results & Artifacts"],
        summary="Get Subtitle Tracks and QC Report",
        description="Returns the synchronized Bengali source cues and English/Hindi translated cues, along with the automated acoustic evidence QC report and available downloadable artifacts.",
        response_model=JobResultsResponse,
        responses={
            200: {
                "description": "Subtitle tracks and QC report retrieved.",
                "model": JobResultsResponse,
            },
            404: {"description": "Job not found or access denied.", "model": ErrorResponse},
            409: {
                "description": "Job results are not ready yet (job is still processing or has not completed).",
                "model": ErrorResponse,
            },
        },
    )
    def results(
        request: Request,
        job_id: Annotated[
            str,
            PathParam(
                description="Unique 32-character hexadecimal job identifier",
                examples=["7e4a68c09e3e4a289650d3dfa539ebf1"],
            ),
        ],
        _auth: Annotated[Any, Depends(bearer_scheme)] = None,
    ):
        job = authorize(job_id, request)
        folder = run_directory(job)
        return {
            "tracks": json.loads((folder / "tracks.json").read_text(encoding="utf-8")),
            "qc": json.loads((folder / "qc_report.json").read_text(encoding="utf-8")),
            "downloads": list(ARTIFACTS),
        }

    @app.get(
        "/api/v1/jobs/{job_id}/artifacts/{name}",
        tags=["Results & Artifacts"],
        summary="Download Generated Artifact File",
        description="Downloads a specific subtitle, caption, or quality report file produced by the pipeline (e.g. .vtt, .srt, or JSON reports).",
        responses={
            200: {
                "description": "Artifact file content stream.",
                "content": {
                    "text/vtt": {},
                    "application/x-subrip": {},
                    "application/json": {},
                },
            },
            404: {
                "description": "Job or artifact not found or not available.",
                "model": ErrorResponse,
            },
        },
    )
    def artifact(
        request: Request,
        job_id: Annotated[
            str,
            PathParam(
                description="Unique 32-character hexadecimal job identifier",
                examples=["7e4a68c09e3e4a289650d3dfa539ebf1"],
            ),
        ],
        name: Annotated[
            str,
            PathParam(
                description="Name of the artifact to download (bengali.vtt, english.srt, hindi.srt, english.vtt, hindi.vtt, qc_report.json, manifest.json)",
                examples=["bengali.vtt"],
            ),
        ],
        _auth: Annotated[Any, Depends(bearer_scheme)] = None,
    ):
        job = authorize(job_id, request)
        if name not in ARTIFACTS:
            raise HTTPException(404, "Unknown artifact")
        path = run_directory(job) / name
        if not path.is_file():
            raise HTTPException(404, "Artifact not available")
        return FileResponse(
            path, media_type=ARTIFACTS[name], headers={"Cache-Control": "private, no-store"}
        )

    # Serve the built studio from the API origin so the job cookie and API calls
    # share one Cloud Run URL. Registered last so every /api route wins.
    static_dir = settings.static_dir
    if static_dir and (static_dir / "index.html").is_file():
        static_root = static_dir.resolve()

        @app.get("/{asset_path:path}", include_in_schema=False)
        def studio(asset_path: str):
            if asset_path.startswith("api/"):
                raise HTTPException(404, "Not found")
            candidate = (static_root / asset_path).resolve()
            if asset_path and candidate.is_file() and candidate.is_relative_to(static_root):
                return FileResponse(candidate)
            return FileResponse(static_root / "index.html", headers={"Cache-Control": "no-cache"})

    return app
