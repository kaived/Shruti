# Shruti — Bengali Caption & Subtitle Studio

Upload a Bengali video and get a **speaker-attributed Bengali closed-caption track (WebVTT) with non-speech sound captions**, **English and Hindi subtitles (SRT)**, and a **QC report with a ranked review queue** that tells a human exactly which lines to check — including any text that may have been hallucinated over silence or music.

> **Status:** deployed and working end to end (Cloudflare Pages frontend → Cloud Run API → Cloud Run Job AI worker). Outputs are automated drafts for human review; accuracy has been measured only on short sample clips, not on an independent held-out set. See [Results](#measured-results) and [Limitations](#limitations).

---

## How it works

Every stage is an AI model; deterministic code only validates formats, timing and access.

| # | Stage | Model / tool | Output |
|---|---|---|---|
| 1 | Media check | FFprobe / FFmpeg | 16 kHz mono audio on the original timeline |
| 2 | Bengali speech recognition | **Groq Whisper large-v3** (15 s overlapping chunks, word timestamps) | `transcription.json` |
| 3 | Speaker diarization | **pyannote Community-1**, run once over the whole recording → stable speaker IDs | `diarization.json` |
| 4 | Forced alignment | **stable-ts** (Whisper small) re-times every word against the audio | `alignment.json` |
| 5 | Code-switched English | **LLM (Groq GPT-OSS 120B)** respells English written in Bengali script (`মিটিং` → `meeting`, `অফিসে` → `office-এ`); raw ASR text is kept | `code_switch.json` |
| 6 | Independent audio evidence | **Silero VAD** (speech) + **PANNs** (music, laughter, applause, phone, door…) — independent of the ASR | `acoustics.json` |
| 7 | Shot changes | **PySceneDetect** | `shots.json` |
| 8 | Cue segmentation | Speaker / shot / pause / sentence boundaries, reading-speed retiming, no shot straddling | `bengali_cues.json` |
| 9 | Translation | **LLM (Groq GPT-OSS 120B)**, source-linked, per-cue retry | `translation_en.json`, `translation_hi.json` |
| 10 | Quality control | Cross-checks all evidence; ranked review queue | `qc_report.json` |
| 11 | Export | `bengali.vtt`, `english.srt`, `hindi.srt`, `manifest.json` | review studio + downloads |

### The hallucination safeguard (toughest test)

Whisper can invent text over silence or music. Shruti never trusts the ASR alone: each recognised word is checked against **independent** speech evidence (Silero VAD + PANNs). Words with weak support are flagged `SUSPECTED_HALLUCINATION` (critical) with the music overlap as evidence, and **these are ranked first** in the review queue. The reverse is checked too: detected speech with no transcript becomes `SPEECH_WITHOUT_TEXT` / `POSSIBLE_MISSED_SPEECH`. If any evidence stage fails, QC reports `incomplete` — it never claims an all-clear.

### Review queue ranking

Issues are ordered by severity (critical → high → medium), then by a documented priority: suspected hallucination → missing translation → speech without text → ASR timing problems → repetition → missed speech → overlapping speech → speaker uncertainty → acoustic uncertainty → shot crossing → cue overlap → reading speed → line length → duration → translation inheriting a flagged source. Each issue links to its cue(s), time range, language and evidence; clicking it in the studio plays that moment.

### Reliability

- Only a speech-recognition failure (after 6 retries) can stop a job — without text there is nothing to caption.
- Diarization, alignment, English respelling, sound detection, shot detection and translation **fall back and continue**; the gap is recorded and flagged in QC (e.g. an untranslated line keeps the Bengali text and is flagged `TRANSLATION_MISSING`).
- A worker killed by the platform cannot leave a job "running" forever: past the job time limit the API marks it failed with **Try again**.
- Completed stages are checkpointed; a retry reuses them.

---

## Architecture

```
Browser (Cloudflare Pages: React studio)
   │  1. POST /api/v1/cloud-uploads  ──►  Cloud Run service "shruti-api" (FastAPI)
   │  2. PUT video directly  ─────────►  Cloud Storage bucket (private)
   │  3. POST …/finalize  ───────────►  API verifies size + SHA-256, queues job (Upstash Redis),
   │                                      starts Cloud Run Job "shruti-worker"
   │                                      Worker (8 vCPU, 16 GiB): AI pipeline above,
   │                                      writes outputs to the bucket, state to Neon Postgres
   └─ polls /api/v1/jobs/{id}, then loads results, video and downloads
```

- Uploads go straight to Cloud Storage, bypassing Cloud Run's 32 MB request limit (videos up to 500 MB / 2 hours).
- Each job has its own random access token (stored hashed). The studio keeps job tokens in the browser's `localStorage`, so users can close the tab and reopen videos from **My videos**. There are no user accounts: a job is reachable only from the browser that uploaded it.
- Secrets (Groq, Hugging Face, database, Redis, upload key) live in Secret Manager and are never sent to the browser.

---

## Measured results

From real runs on a 2-minute clip of the supplied `mohanagar.mp4` (not a held-out evaluation):

| Measure | Result |
|---|---|
| End-to-end cloud run | ✅ completed; all tracks, QC report and manifest produced |
| Suspected hallucinations | 5 flagged as critical, ranked at the top of the queue |
| Code-switched English restored | e.g. `meeting`, `public`, `toilet-এর`, `parcel-এ`, `invitation`, `family-র`, `city` |
| Shot-straddling cues | 10 → **3** after reading-speed retiming |
| Reading-speed violations | 37 → **22** |
| Cues without a speaker label | 24 → **6** (of 42) |
| Processing time (warm, 8 vCPU) | ≈ 2 min of processing per minute of video (diarization ≈ 98 s and alignment ≈ 111 s for 2 min) |

A 30–40 minute episode is expected to take about 1–1.5 hours; the job limit is 3 hours. Full-length episodes have not yet been validated end to end.

---

## Limitations

- Accuracy is not validated on independently annotated held-out episodes; no WER/DER is claimed.
- Whisper's Bengali spelling is phonetic (e.g. `আছকে` for `আজকে`); the LLM only respells English words.
- Some cues remain without a confident speaker; they are flagged rather than guessed. Speaker names are not inferred automatically (speakers can be renamed in the studio).
- Fast speech can still exceed the reading-speed limit; such cues are flagged. Caption limits (17 CPS Bengali/Hindi, 20 English, 42 chars × 2 lines, 0.8–7 s) are provisional, not an official profile.
- Non-Bengali videos are transcribed as Bengali and are not detected.
- Groq plan limits (requests/tokens per day) bound how many long episodes can be processed per day.
- CPU inference; a GPU worker would cut processing time substantially.
- Access is per-browser (no accounts); the media URL carries the job token, so Cloud Run request logs contain it.
- The downloads menu currently rebuilds files in the browser from the reviewed cues; the backend's validated files are available at `/api/v1/jobs/{id}/artifacts/{name}`.

---

## Run locally

Requirements: Python 3.12 + [uv](https://docs.astral.sh/uv/), Node 22.12+, Docker (for the worker and FFmpeg on Windows).

```bash
cp .env.example .env.development          # fill in real values
cd backend && uv sync --frozen --extra inference --dev
uv run python src/server.py               # API on http://127.0.0.1:8000 (docs: /api-docs)
```

```bash
cd frontend
cp .env.example .env.development          # empty VITE_API_BASE_URL = use the local API via the Vite proxy
npm ci && npm run dev                      # studio on http://localhost:5173
```

The worker needs FFmpeg and Unix process forking; on Windows run it in Docker (`docker compose up --build worker`).

> Local `.env.development` pointing at the production Neon/Upstash shares their queue with the cloud worker. Use separate local services, or point the local studio at the deployed API instead.

---

## Deploy

**Backend (Google Cloud Run)** — one script, run from the repo root in Git Bash with `gcloud` signed in:

```bash
bash deploy/gcp.sh setup    # APIs, registry, bucket (+CORS), secrets from .env.production, service account, starts Cloud Build
bash deploy/gcp.sh status   # wait for SUCCESS
FRONTEND_ORIGINS=https://your-studio.pages.dev bash deploy/gcp.sh deploy
```

`deploy` creates the worker Cloud Run Job and the API service, mounts the bucket at `/data`, wires secrets, and allows the listed frontend origins for both the API (CORS) and direct bucket uploads. Details: [docs/CLOUD_RUN.md](docs/CLOUD_RUN.md).

**Frontend (Cloudflare Pages)** — root `frontend`, build `npm run build`, output `dist`, environment `VITE_API_BASE_URL=https://shruti-api-<project-number>.<region>.run.app` and `NODE_VERSION=22`. Or: `cd frontend && npm run build && npx wrangler pages deploy dist --project-name <name>`.

**Rotate the upload key:** add a new version of the `shruti-upload-key` secret, then `gcloud run services update shruti-api --update-secrets=SHRUTI_UPLOAD_KEY=shruti-upload-key:latest`.

---

## API

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/v1/health`, `/api/v1/readiness` | Liveness; database, queue and FFmpeg readiness |
| GET | `/api/v1/capabilities` | Upload/duration limits, whether an upload key is required |
| POST | `/api/v1/cloud-uploads` | Create a direct Cloud Storage upload session (`X-Upload-Key`) |
| POST | `/api/v1/cloud-uploads/{id}/finalize` | Verify the upload and start processing |
| POST | `/api/v1/jobs` | Fallback upload through the API (small files / local) |
| GET | `/api/v1/jobs/{id}` | State, current stage, timings |
| POST | `/api/v1/jobs/{id}/retry` | Retry a failed job (reuses finished stages; max 3 attempts) |
| GET | `/api/v1/jobs/{id}/media` | Original video (range requests) |
| GET | `/api/v1/jobs/{id}/results` | Bengali/English/Hindi cues and QC report |
| GET | `/api/v1/jobs/{id}/artifacts/{name}` | `bengali.vtt`, `english.srt`, `hindi.srt`, `*.vtt`, `qc_report.json`, `manifest.json` |

Job routes accept `Authorization: Bearer <token>`; the media route also accepts `?access_token=` for the `<video>` element. Interactive docs: `/api-docs`.

---

## Verification

```bash
cd backend && uv run ruff check ../ai src && uv run ruff format --check ../ai src
uvx pyrefly check                  # from the repo root; uses pyrefly.toml → backend/.venv
cd frontend && npm run build       # includes tsc -b
```

---

## Repository map

| Path | Responsibility |
|---|---|
| `ai/` | Model adapters: `transcriber`, `diarizer`, `aligner`, `codeswitch`, `acoustics`, `shots`, `translator`, `factory` |
| `backend/src/api/` | FastAPI routes, direct Cloud Storage uploads, schemas |
| `backend/src/pipeline/` | Orchestrator (stages, checkpoints, fallbacks), RQ queue/worker, Cloud Run Job trigger |
| `backend/src/captions/` | Cue segmentation/retiming, WebVTT/SRT export |
| `backend/src/qc/` | QC evaluation and ranking |
| `backend/src/core/` | Settings, typed contracts, database |
| `frontend/src/` | React studio: upload, progress, review workspace, My videos |
| `deploy/gcp.sh`, `cloudbuild.yaml` | Cloud Run build and deploy |
| `docs/` | `REQUIREMENTS.md` (PS2 requirements spec), `CLOUD_RUN.md` (deployment reference) |
