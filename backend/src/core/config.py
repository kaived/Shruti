from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SHRUTI_",
        env_file=(
            ".env",
            ".env.development",
            "../.env",
            "../.env.development",
            "../../.env.development",  # repository root when started from backend/src
        ),
        extra="ignore",
        populate_by_name=True,
    )

    data_dir: Path = Path("data")
    # Env var: SHRUTI_DB_URL (Neon Postgres). Empty -> local SQLite under data_dir.
    database_url: str = Field(default="", validation_alias="SHRUTI_DB_URL")
    # Env var: SHRUTI_REDIS_URL (Upstash rediss:// TCP URL).
    redis_url: str = "redis://localhost:6379/0"
    allowed_origins: list[str] = ["http://localhost:5173"]
    max_upload_bytes: int = Field(default=500 * 1024 * 1024, gt=0)
    max_duration_seconds: int = Field(default=7200, gt=0)
    job_timeout_seconds: int = Field(default=3600, gt=0)
    max_attempts: int = Field(default=3, ge=1, le=10)
    provider_factory: str = ""
    provider_revision: str = "unconfigured"
    upload_key: str = ""
    cookie_secure: bool = False
    gcs_bucket: str = ""
    cloud_run_worker_job: str = ""
    worker_burst: bool = False
    static_dir: Path | None = None

    @property
    def db_url(self) -> str:
        raw = self.database_url
        if not raw:
            return f"sqlite:///{self.data_dir.resolve() / 'shruti.sqlite3'}"
        if raw.startswith("postgresql://") and not raw.startswith("postgresql+"):
            return raw.replace("postgresql://", "postgresql+psycopg://", 1)
        if raw.startswith("postgres://") and not raw.startswith("postgres+"):
            return raw.replace("postgres://", "postgresql+psycopg://", 1)
        return raw

    def prepare(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "jobs").mkdir(exist_ok=True)
