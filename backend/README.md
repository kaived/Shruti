# Shruti Backend — API & AI Pipeline

FastAPI service plus an RQ worker that runs the Bengali captioning pipeline. In production the API runs as the Cloud Run service `shruti-api` and the worker as the Cloud Run Job `shruti-worker`. See the [root README](../README.md) for the pipeline, results and limitations.

## Layout

```
backend/
├── src/
│   ├── api/        # routes.py (jobs, media, results, artifacts), cloud_uploads.py, schemas.py
│   ├── captions/   # segmentation.py (cues + retiming), exporters.py (WebVTT/SRT)
│   ├── core/       # config.py (Settings), contracts.py (typed records), database.py
│   ├── media/      # audio.py (FFprobe checks, 16 kHz extraction)
│   ├── pipeline/   # orchestrator.py, queueing.py, worker.py, cloud_run.py
│   ├── providers/  # base.py (adapter protocols, factory loading)
│   ├── qc/         # evaluation.py (checks + ranking), benchmark.py
│   └── server.py   # local entrypoint
├── Dockerfile      # one image; INSTALL_INFERENCE=1 adds the AI worker dependencies
└── pyproject.toml
```

The AI adapters live in `../ai` and are loaded through `SHRUTI_PROVIDER_FACTORY=ai.factory:create_providers`.

## Configuration

All settings use the `SHRUTI_` prefix (except `GROQ_API_KEY`). Copy [`../.env.example`](../.env.example) to `../.env.development` for local work; `deploy/gcp.sh` reads `../.env.production`.

| Variable | Used by | Purpose |
|---|---|---|
| `SHRUTI_DB_URL` | API, worker | Postgres URL; empty = local SQLite |
| `SHRUTI_REDIS_URL` | API, worker | Redis/Upstash `rediss://` URL for the job queue |
| `SHRUTI_UPLOAD_KEY` | API | Key required to create uploads |
| `GROQ_API_KEY` | worker | Whisper ASR, code-switch respelling, translation |
| `SHRUTI_HF_TOKEN` | worker | pyannote diarization model download |
| `SHRUTI_PROVIDER_FACTORY`, `SHRUTI_PROVIDER_REVISION` | API, worker | AI suite and cache version |
| `SHRUTI_JOB_TIMEOUT_SECONDS` | API, worker | Job time limit (queue timeout and stuck-job detection); 10800 in production |
| `SHRUTI_ALLOWED_ORIGINS` | API | JSON list of browser origins (CORS and upload origin check) |
| `SHRUTI_GCS_BUCKET`, `SHRUTI_CLOUD_RUN_WORKER_JOB` | API | Direct uploads and worker start (Cloud Run only) |
| `SHRUTI_TRANSLATION_MODEL` | worker | Optional Groq chat model (default `openai/gpt-oss-120b`) |

## Run locally

```powershell
cd backend
uv sync --frozen --extra inference --dev
uv run python src/server.py     # http://127.0.0.1:8000, docs at /api-docs
```

The worker (`python -m pipeline.worker`) needs FFmpeg and Unix forking, so on Windows run it in Docker.

## Endpoints

See the [API table in the root README](../README.md#api) or `/api-docs`.

## Quality checks

```powershell
uv run ruff check ../ai src
uv run ruff format --check ../ai src
cd ..; uvx pyrefly check          # uses pyrefly.toml, which points at backend/.venv
```
