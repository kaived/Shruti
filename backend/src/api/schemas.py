from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from core.contracts import Cue, QCReport


class HealthResponse(BaseModel):
    status: str = Field(
        default="ok",
        description="Health status of the API service",
        examples=["ok"],
    )
    service: str = Field(
        default="shruti",
        description="Application identifier",
        examples=["shruti"],
    )


class ReadinessResponse(BaseModel):
    database: bool = Field(
        description="True if the primary SQLite/PostgreSQL database connection is alive and writable."
    )
    queue: bool = Field(
        description="True if the background task queue dispatcher (Redis/RQ) is reachable."
    )
    media_tools: bool = Field(
        description="True if external multimedia binaries (ffmpeg and ffprobe) are found on the system PATH."
    )


class CapabilitiesResponse(BaseModel):
    inference_configured: bool = Field(
        description="True if speech-to-text and translation AI model providers are configured and ready."
    )
    max_upload_bytes: int = Field(
        description="Maximum allowed media upload payload size in bytes (e.g. 524,288,000 for 500 MB)."
    )
    max_duration_seconds: int = Field(
        description="Maximum allowable video duration in seconds for pipeline ingestion."
    )
    upload_key_required: bool = Field(
        description="True if clients must supply the X-Upload-Key HTTP header for video uploads."
    )
    caption_profile: str = Field(
        description="Active subtitle standard and line-wrapping profile version.",
        examples=["provisional-1"],
    )
    release_approval_available: bool = Field(
        description="True if human-in-the-loop release gating and override approval is enabled."
    )


class JobUploadResponse(BaseModel):
    id: str = Field(
        description="Unique 32-character hexadecimal identifier assigned to the new job.",
        examples=["7e4a68c09e3e4a289650d3dfa539ebf1"],
    )
    access_token: str = Field(
        description="Cryptographic secret token required for subsequent job status queries, streaming, and retries.",
        examples=["X3Z_k0W49zP71bLkNmEq8rTyUiOpAsDfGhJkLzXc_Vb"],
    )


class JobSummaryResponse(BaseModel):
    id: str = Field(
        description="Unique job identifier.",
        examples=["7e4a68c09e3e4a289650d3dfa539ebf1"],
    )
    filename: str = Field(
        description="Sanitized name of the uploaded source video file.",
        examples=["interview_clip.mp4"],
    )
    state: str = Field(
        description="Current execution lifecycle state of the job (e.g. queued, running, completed, blocked, failed, partial).",
        examples=["running"],
    )
    stage: str = Field(
        description="Current active pipeline processing stage.",
        examples=["asr"],
    )
    qc_state: str = Field(
        description="Acoustic evidence and quality control evaluation status.",
        examples=["automated_checks_passed"],
    )
    error_code: str | None = Field(
        default=None,
        description="Machine-readable error identifier if the job failed or was blocked.",
        examples=[None],
    )
    message: str | None = Field(
        default=None,
        description="Human-readable informational or diagnostic failure message.",
        examples=[None],
    )
    attempts: int = Field(
        description="Total number of execution attempts logged for this job.",
        examples=[1],
    )
    created_at: str = Field(
        description="ISO-8601 UTC timestamp of initial upload.",
        examples=["2026-09-26T12:00:00+00:00"],
    )
    updated_at: str = Field(
        description="ISO-8601 UTC timestamp of most recent job state change.",
        examples=["2026-09-26T12:01:30+00:00"],
    )
    media: dict[str, Any] = Field(
        default_factory=dict,
        description="Extracted media properties (duration, dimensions, audio channels, stream info).",
    )
    stage_metrics: dict[str, Any] = Field(
        default_factory=dict,
        description="Execution durations and token/word metrics for completed pipeline stages.",
    )


class JobRetryResponse(BaseModel):
    id: str = Field(
        description="Job identifier.",
        examples=["7e4a68c09e3e4a289650d3dfa539ebf1"],
    )
    message: str = Field(
        default="Retry requested",
        description="Outcome confirmation message.",
        examples=["Retry requested"],
    )


class JobResultsResponse(BaseModel):
    tracks: dict[str, list[Cue]] = Field(
        description="Dictionary of subtitle cues keyed by language code: 'bn' (Bengali source), 'en' (English translation), 'hi' (Hindi translation)."
    )
    qc: QCReport = Field(
        description="Comprehensive acoustic evidence quality control report with check statuses and issue logs."
    )
    downloads: list[str] = Field(
        description="List of artifact filenames available for direct download via the artifacts API."
    )


class ArtifactName(StrEnum):
    bengali_vtt = "bengali.vtt"
    english_srt = "english.srt"
    hindi_srt = "hindi.srt"
    english_vtt = "english.vtt"
    hindi_vtt = "hindi.vtt"
    qc_report_json = "qc_report.json"
    manifest_json = "manifest.json"


class ErrorResponse(BaseModel):
    detail: str = Field(
        description="Human-readable error explanation.",
        examples=["Job not found or access denied"],
    )
