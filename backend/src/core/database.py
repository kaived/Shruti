from datetime import UTC, datetime
from typing import cast

from sqlalchemy import JSON, CursorResult, Integer, String, create_engine, update
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from core.config import Settings


def now() -> str:
    return datetime.now(UTC).isoformat()


class Base(DeclarativeBase):
    pass


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64))
    filename: Mapped[str] = mapped_column(String(255))
    sha256: Mapped[str] = mapped_column(String(64))
    state: Mapped[str] = mapped_column(String(32), default="uploaded")
    stage: Mapped[str] = mapped_column(String(64), default="upload")
    qc_state: Mapped[str] = mapped_column(String(32), default="not_run")
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    message: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[str] = mapped_column(String(40), default=now)
    updated_at: Mapped[str] = mapped_column(String(40), default=now)
    media: Mapped[dict] = mapped_column(JSON, default=dict)
    stage_metrics: Mapped[dict] = mapped_column(JSON, default=dict)


class Database:
    def __init__(self, settings: Settings):
        settings.prepare()
        options = {"connect_args": {"timeout": 30}} if settings.db_url.startswith("sqlite") else {}
        self.engine = create_engine(settings.db_url, pool_pre_ping=True, **options)
        self.sessions = sessionmaker(self.engine, expire_on_commit=False)

    def initialize(self) -> None:
        # Deliberately small initial schema. Add migrations before changing deployed tables.
        Base.metadata.create_all(self.engine)

    def update_job(self, job_id: str, **values) -> None:
        with self.sessions.begin() as session:
            session.execute(update(Job).where(Job.id == job_id).values(**values, updated_at=now()))

    def claim(self, job_id: str) -> bool:
        with self.sessions.begin() as session:
            result = session.execute(
                update(Job)
                .where(Job.id == job_id, Job.state == "queued")
                .values(state="running", stage="media", updated_at=now())
            )
            return cast(CursorResult, result).rowcount == 1
