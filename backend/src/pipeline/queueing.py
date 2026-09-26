from redis import Redis
from rq import Queue

from core.config import Settings
from core.database import Database


def worker_failure(job, connection, exc_type, exc_value, traceback):
    """Persist timeout/worker failure instead of leaving an eternal running state."""
    db = Database(Settings())
    try:
        if job.args:
            db.update_job(
                job.args[0],
                state="failed",
                qc_state="incomplete",
                error_code="WORKER_FAILED",
                message="Worker failed or timed out. Retry is available.",
            )
    finally:
        db.engine.dispose()


class Dispatcher:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.redis = Redis.from_url(settings.redis_url, socket_connect_timeout=2, socket_timeout=5)
        self.queue = Queue("shruti", connection=self.redis)

    def enqueue(self, job_id: str):
        return self.queue.enqueue(
            "pipeline.orchestrator.run_pipeline",
            job_id,
            job_timeout=self.settings.job_timeout_seconds,
            on_failure=worker_failure,
            result_ttl=86400,
            failure_ttl=604800,
        )

    def healthy(self) -> bool:
        try:
            return bool(self.redis.ping())
        except Exception:
            return False
