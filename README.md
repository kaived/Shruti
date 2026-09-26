# Shruti

Bengali captioning and multilingual subtitle review, with stable speaker contracts and evidence-based quality control.

**Status: tested engineering starter, not a completed PS2 submission.** A safety-first Groq ASR/translation factory and real shot detector are included, but diarization, Bengali forced alignment and validated independent acoustic classification remain incomplete. The application never substitutes canned dialogue or marks missing evidence as successful. The default configuration remains blocked until an explicit provider factory is selected.

## What works now

- React/TypeScript review interface: upload, persistent session job access, status, media preview, track selection, cue seeking, QC filters and downloads when outputs exist.
- FastAPI API with streaming upload limits, hashed per-job access tokens, HTTP-only media-access cookies and artifact allowlisting.
- Durable database records, Redis/RQ processing worker, bounded manual retries and versioned stage checkpoints.
- FFmpeg media inspection and timeline-preserving audio extraction.
- Typed contracts for words, global speaker IDs, alignment, independent acoustic evidence, shot analysis, sound events, cues and QC findings.
- Initial deterministic cue grouping, provisional readability checks, shot-crossing checks, suspected unsupported-word detection, missed-speech coverage and translation-source checks.
- Bounded Groq ASR chunks with overlap reconciliation, provider word timestamps, no fabricated confidence scores and explicitly unresolved speakers.
- Strict batched English/Hindi translation: malformed, missing, duplicate or source-copy responses fail instead of becoming mislabeled subtitles.
- Bengali WebVTT and English/Hindi SRT exporters; VTT preview derivatives for translated tracks.
- Explicit incomplete/review-required QC states. No automatic human release approval.
- Local SQLite mode, PostgreSQL/Redis Docker Compose configuration and dependency locks.

## What still needs implementation and validation

1. Validate Groq Bengali/code-switch ASR on held-out footage and connect a stable diarization adapter.
2. Bengali/code-switched forced alignment adapter.
3. Independent speech/music/sound-event analysis and empirical shot-detector validation.
4. Validate context-aware English/Hindi translation quality on supplied footage.
5. Empirical QC calibration and recognition/diarization/translation evaluation on the supplied footage.
6. More capable cue optimization: the current grouper flags hard cases rather than solving every readability/timing conflict.
7. Optional character-name inference/confirmation and editable review resolution. Current UI is read-only review; naming fields exist in contracts.
8. Public deployment, GitHub publication and the required submission video.

No accuracy, latency or cost results on Hoichoi footage have been measured. Unit tests use explicitly synthetic data and are not evidence of model accuracy. The inference-configured flag checks configuration presence; it does not certify provider health or quality.

## Start with Docker Compose

Requirements: Docker with Compose. From this directory:

```bash
cp .env.example .env
docker compose up --build -d
```

PowerShell users can replace the first command with `Copy-Item .env.example .env`.

- Review interface: http://localhost:8080
- API documentation: http://localhost:8000/docs
- API health: http://localhost:8000/api/health
- Infrastructure readiness: http://localhost:8000/api/readiness

Open the UI and upload a file to exercise job creation. With no inference configuration, the job becomes `blocked` rather than producing fake captions. The worker checks provider configuration before expensive audio extraction.

```bash
docker compose logs -f api worker
docker compose down
```

Compose stores jobs, media, PostgreSQL data and the Redis append-only log in named volumes. `docker compose down` retains these volumes. Docker Compose could not be executed in the creation environment because Docker was not installed; validate this deployment path on your machine before relying on it.

## Local development

Use Python 3.12 or 3.13, Node 22.12+ (Node 22 LTS recommended for this setup), uv, FFmpeg/FFprobe and Redis. On Windows, run the RQ worker in Docker or WSL2; the selected worker uses Unix process forking.

Start Redis using Docker if available:

```bash
docker compose up -d redis
```

Backend terminal:

```bash
cd backend
cp .env.example .env
uv sync --frozen --dev
uv run uvicorn api.routes:create_app --factory --reload --host 127.0.0.1 --port 8000
```

Worker terminal (same backend directory and environment):

```bash
uv run python -m pipeline.worker
```

Frontend terminal:

```bash
cd frontend
npm ci
npm run dev
```

Open http://localhost:5173. Vite proxies `/api` to the backend so protected video requests use the same browser origin. SQLite is the local default. API and worker must use the same database, data directory and provider configuration.

## Repository map

| Path | Responsibility |
| --- | --- |
| `backend/src/api/routes.py` | HTTP endpoints, upload/access boundary and job controls |
| `backend/src/core/database.py` | Job persistence and atomic worker claim |
| `backend/src/core/contracts.py` | Validated inference, caption and QC records |
| `backend/src/providers/base.py` | Real model integration protocols and factory loading |
| `backend/src/media/audio.py` | Media probing, limits and audio extraction |
| `backend/src/pipeline/orchestrator.py` | Stage ordering, checkpoints and output lineage |
| `backend/src/captions/` | Cue segmentation and WebVTT/SRT serialization |
| `backend/src/qc/` | Evidence checks and held-out benchmark utilities |
| `backend/src/pipeline/queueing.py`, `worker.py` | RQ execution and failure recording |
| `ai/` | Groq ASR/translation, shot detection and explicit incomplete adapters |
| `backend/tests/` | Safety, format, API and media-processing regression tests |
| `frontend/src/` | Upload and caption review application |
| `infra/nginx.conf` | Same-origin API proxy and static frontend serving |
| `docs/` | Requirements, integration contract, architecture and next steps |

## Connect real inference

The included safety-first factory is `ai.factory:create_providers`. It requires `GROQ_API_KEY` and provides chunked Groq recognition, strict Groq translation and PySceneDetect shot cuts. Its timestamp pass-through aligner and waveform-only acoustic validator deliberately keep jobs `partial`; they do not satisfy forced-alignment or independent-speech-evidence requirements. The detailed contract for replacing those adapters is in [docs/PROVIDER_INTEGRATION.md](docs/PROVIDER_INTEGRATION.md).

Set these variables in the API and worker environments:

```dotenv
GROQ_API_KEY=replace-with-server-side-secret
SHRUTI_PROVIDER_FACTORY=ai.factory:create_providers
SHRUTI_PROVIDER_REVISION=groq-safety-v1
```

Keep keys in environment variables. Restart API/worker after changing environment settings. In Docker, rebuild if code/dependencies changed. Do not describe this factory as fully complete until the remaining diarization, alignment and acoustic adapters are connected and validated.

Increment the revision when models, prompts, thresholds or provider behaviour change. Checkpoint fingerprints include the media checksum, pipeline version, profile and provider revision. A provider code change without a revision bump can reuse stale results. Raw recognition and alignment outputs remain separate.

## API essentials

| Endpoint | Behaviour |
| --- | --- |
| `GET /api/health` | API liveness |
| `GET /api/readiness` | Database, Redis and media tools |
| `GET /api/capabilities` | Configuration state and input limits |
| `POST /api/jobs?filename=clip.mp4` | Raw binary video body; returns job ID and one-time access token |
| `GET /api/jobs/{id}` | Processing/QC state and stage metadata |
| `POST /api/jobs/{id}/retry` | Bounded retry of a failed, blocked or partial job |
| `GET /api/jobs/{id}/media` | Protected original video, including range responses |
| `GET /api/jobs/{id}/results` | Tracks and QC after completion/partial completion |
| `GET /api/jobs/{id}/artifacts/{name}` | Allowlisted exports |

Job routes require `Authorization: Bearer <access_token>` or the matching HTTP-only job cookie. Tokens are hashed in the database; browser API access tokens live in sessionStorage, not URL query strings. The UI remembers up to 12 jobs in the current session. This is a scoped demo access scheme, not enterprise authentication.

## Verification

```bash
cd backend
uv run ruff check .
uv run ruff format --check .
uv run pytest -q
```

```bash
cd frontend
npm run build
```

Tests cover unsupported text over silence/music, real speech under music, caption dwell time, missing evidence, missed speech, source uncertainty propagation, shot crossings, absent translations, identity references, independent VTT/SRT parsing, upload limits, access isolation, queue failure, blocked inference and real FFmpeg extraction. See [docs/VALIDATION.md](docs/VALIDATION.md) for observed checks and limitations.

## Before public demo deployment

- Connect and test the actual inference providers; a blocked starter is not a hackathon submission.
- Replace local database credentials, set an upload access key, terminate HTTPS and set `SHRUTI_COOKIE_SECURE=true`.
- Add ingress request/rate/concurrency/storage limits and a worker heartbeat/reconciliation check. Readiness currently does not prove a worker is alive or model inference is healthy.
- Keep API/worker storage shared; verify codecs and original-video browser playback with the actual assets. Browser compatibility for every MKV/MP4 codec is not guaranteed.
- Align Nginx and API upload limits. The initial limit is 512 MiB and the initial runtime limit is two hours, both provisional.
- Establish retention/deletion and access controls appropriate to the intended users. Current code has no deletion UI, backup system, enterprise login or migration framework.
- Normal RQ failures/timeouts are recorded. Abrupt machine loss or a crash between database commit and enqueue needs operator reconciliation; an outbox/watchdog is later hardening.
- Keep source videos out of the public repository unless redistribution is authorised. Keep reference annotations out of live inference.
- Validate a fresh live upload, capture measured results, publish the repository/demo and record a walkthrough under five minutes.

## Technical references

- [FastAPI background computation guidance](https://fastapi.tiangolo.com/tutorial/background-tasks/)
- [RQ workers and job execution](https://python-rq.org/docs/workers/)
- [Vite runtime requirements](https://vite.dev/guide/)
- [WebVTT specification](https://www.w3.org/TR/webvtt1/)

The organiser's PS2 brief is authoritative. All caption thresholds in this starter are explicitly provisional and require validation against the supplied editorial/evaluation profile.
