"""Start an on-demand Cloud Run Job after a job enters the Redis queue."""

import re

from core.config import Settings

JOB_NAME = re.compile(r"projects/[a-z][a-z0-9-]*/locations/[a-z0-9-]+/jobs/[a-z][a-z0-9-]*")


def start_worker_job(settings: Settings) -> None:
    name = settings.cloud_run_worker_job
    if not name:
        return
    if JOB_NAME.fullmatch(name) is None:
        raise ValueError("SHRUTI_CLOUD_RUN_WORKER_JOB must be a full Cloud Run Job resource name")

    import google.auth
    from google.auth.transport.requests import AuthorizedSession

    credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    response = AuthorizedSession(credentials).post(
        f"https://run.googleapis.com/v2/{name}:run",
        json={},
        timeout=20,
    )
    response.raise_for_status()
