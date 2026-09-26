# Cloud Run deployment

**Deployed.** The supported path is the script [`deploy/gcp.sh`](../deploy/gcp.sh)
(`setup` → `status` → `deploy`), which performs every step below automatically,
reading secrets from `.env.production`. What it creates:

| Resource | Name / setting |
| --- | --- |
| Cloud Run service (API) | `shruti-api`, port 8000, 1 vCPU / 1 GiB, bucket mounted at `/data`, public |
| Cloud Run Job (AI worker) | `shruti-worker`, 8 vCPU / 16 GiB, task timeout = job timeout + 10 min, 0 retries |
| Job time limit | `SHRUTI_JOB_TIMEOUT_SECONDS=10800` on **both** API and worker (the API enqueues with it) |
| Storage | private bucket `<project>-shruti-media`, CORS for the allowed frontend origins |
| Secrets | `shruti-db-url`, `shruti-redis-url`, `shruti-groq-api-key`, `shruti-hf-token`, `shruti-upload-key` |
| Images | built by Cloud Build (`cloudbuild.yaml`) into Artifact Registry `shruti` |
| Frontend origins | `FRONTEND_ORIGINS=https://a.pages.dev,http://localhost:5173 bash deploy/gcp.sh deploy` |

The frontend is deployed separately (Cloudflare Pages); the API image contains no frontend.
The PANNs checkpoint is kept in the bucket at `models/panns/Cnn14_DecisionLevelMax.pth`
so workers do not depend on Zenodo at run time.

Outputs are automated drafts for review; held-out accuracy has not been validated.
The manual checklist below is kept as reference for what the script does.

## Required values (replace placeholders yourself)

| Placeholder | Meaning |
| --- | --- |
| `PROJECT_ID` | Your Google Cloud project ID |
| `REGION` | One Cloud Run region near your users and Cloud Storage bucket |
| `BUCKET` | A private Cloud Storage bucket in the same region |
| `REGISTRY` | An Artifact Registry Docker repository |
| `STUDIO_ORIGIN` | Exact HTTPS origin of the frontend, no trailing slash |

Keep the Neon PostgreSQL URL, Upstash **TCP/TLS** `rediss://` URL, Groq key,
Hugging Face token, and a random upload key in Secret Manager. Never put their
values in a command, Docker build argument, repository file, or frontend bundle.
The Hugging Face account owning the token must have accepted the
`pyannote/speaker-diarization-community-1` terms.

## Architecture

1. A browser asks the API for `/api/cloud-uploads` with filename and byte size.
   The API creates a private GCS resumable session and returns its URL.
2. The browser PUTs the video directly to GCS. This avoids Cloud Run's HTTP
   request-size limit; the provided episodes are much larger than that limit.
3. The browser calls `/api/cloud-uploads/{id}/finalize`. The API verifies object
   size and SHA-256, records the job in Neon, enqueues it in Upstash Redis, and
   starts the configured Cloud Run Job.
4. A one-task Cloud Run Job starts an RQ worker with
   `SHRUTI_WORKER_BURST=true`. It processes the queue and exits. No idle
   inference worker is required.
5. API and worker mount the **same** GCS bucket at `/data` for source media and
   generated artifacts. The database remains in Neon; do not put SQLite on a
   GCS mount.

The GCS mount is a quick shared-storage integration, but Cloud Storage FUSE is
not POSIX-compliant. Its file replacement and metadata behavior must be tested
on the deployed service and job before treating this as production-hardened.
Keep one worker task and low concurrency for the demo. Do not mount the model
cache on GCS: set `HF_HOME=/tmp/shruti-models/hf` and
`SHRUTI_MODEL_CACHE_DIR=/tmp/shruti-models` on the Cloud Run Job. This makes
each execution download models; plan for cold-start time and network use.

## Google Cloud preparation

1. Enable Cloud Run, Artifact Registry, Cloud Storage, Secret Manager, Cloud
   Build, and IAM Credentials APIs. Create the private bucket and registry in
   `REGION`.
2. Create separate API and worker service accounts. Give both access to read
   and write objects in `BUCKET` and to access only their required secrets.
   Give the API service account permission to execute **only** the worker Cloud
   Run Job (`roles/run.invoker` on that job).
3. Configure bucket CORS to allow `STUDIO_ORIGIN` to `PUT` and `OPTIONS` with
   `Content-Type` and `Content-Range`. Test it in the browser. The resumable
   session URL is a bearer capability: never log or share it.
4. Build two images from `backend/Dockerfile`: API with
   `INSTALL_INFERENCE=0`, worker with `INSTALL_INFERENCE=1`. Push them to
   Artifact Registry. Do not place any secret in the image.
5. Create the worker Cloud Run Job with one task, zero retries, a timeout
   greater than `SHRUTI_JOB_TIMEOUT_SECONDS`, CPU and memory measured from a
   full sample episode, the worker service account, the private bucket mounted
   read/write at `/data` with UID/GID `10001`, and command
   `python -m pipeline.worker`. Set:

   - `SHRUTI_DATA_DIR=/data`
   - `SHRUTI_PROVIDER_FACTORY=ai.factory:create_providers`
   - `SHRUTI_PROVIDER_REVISION` to an explicit version string
   - `SHRUTI_WORKER_BURST=true`
   - `SHRUTI_JOB_TIMEOUT_SECONDS` below the Cloud Run Job timeout
   - `HF_HOME=/tmp/shruti-models/hf`
   - `SHRUTI_MODEL_CACHE_DIR=/tmp/shruti-models`
   - `SHRUTI_PANNS_CHECKPOINT=/data/models/panns/Cnn14_DecisionLevelMax.pth`
   - `SHRUTI_TRANSLATION_MODEL=openai/gpt-oss-120b` (or another model listed as active for your Groq account)
   - `SHRUTI_DB_URL`, `SHRUTI_REDIS_URL`, `GROQ_API_KEY`, and
     `SHRUTI_HF_TOKEN` from Secret Manager

6. Deploy the API Cloud Run service on container port `8000`, initially with
   minimum instances `0`, maximum instances `1`, low request concurrency, the
   API service account, and the same bucket mount at `/data` with UID/GID
   `10001`. Set:

   - `SHRUTI_DATA_DIR=/data`
   - `SHRUTI_GCS_BUCKET=BUCKET`
   - `SHRUTI_CLOUD_RUN_WORKER_JOB=projects/PROJECT_ID/locations/REGION/jobs/shruti-worker`
   - `SHRUTI_ALLOWED_ORIGINS=["STUDIO_ORIGIN"]` (replace the token with the full HTTPS origin)
   - `SHRUTI_PROVIDER_FACTORY=ai.factory:create_providers` and the same
     `SHRUTI_PROVIDER_REVISION` as the worker for accurate capability reporting
   - `SHRUTI_COOKIE_SECURE=true`
   - `SHRUTI_DB_URL`, `SHRUTI_REDIS_URL`, and `SHRUTI_UPLOAD_KEY` from
     Secret Manager

   The first worker execution downloads the public PANNs checkpoint into the
   shared bucket path above; prewarm it before a live demo and verify the
   published checksum `70539c43c18b6a289b3199c503a82c5a`. Later jobs reuse it. The API only requires the lightweight image; keep Groq/HF secrets on the worker, not on the public API. Ensure the worker also has `SHRUTI_GCS_BUCKET=BUCKET` if using the same upload path conventions.

7. Keep the API private until an authentication boundary is in place. A static
   `X-Upload-Key` embedded in a browser application is **not** a secure public
   authentication design.
8. Configure bucket lifecycle/retention and Neon backups according to your
   privacy and demo requirements; set a budget alert. These are not automated
   in this repository.

## Smoke test before release

1. Confirm `/api/readiness` returns database, queue, and media tools healthy.
2. Use a new 30–60 second clip (not a hand-corrected sample) with speech,
   background music, two speakers, and a silent section. Upload it through
   the direct-GCS flow. Watch Cloud Run Job logs and the job status API.
3. Verify all three subtitle tracks and the QC JSON. Listen to every cue
   over silence/music and verify it is absent or flagged. Check speaker IDs
   across the clip and word timings against the original video.
4. Repeat with a full provided episode and a cold worker start. Measure
   processing time, peak memory, model download time, storage operations,
   Groq usage, and actual cost. Then test a retry after an interrupted job.
5. Do not assert zero unflagged hallucinations or broadcast readiness until
   held-out reference annotations are available and the measured QC recall
   meets the organiser's criteria.
