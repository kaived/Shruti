#!/usr/bin/env bash
# Manual Cloud Run deployment for Shruti. Run from the repository root in Git Bash:
#   bash deploy/gcp.sh setup    # APIs, registry, bucket, secrets, IAM, starts the image build
#   bash deploy/gcp.sh status   # shows the latest Cloud Build result
#   bash deploy/gcp.sh deploy   # deploys the worker job and the API + studio service
# Every step is safe to re-run. Secrets are read from .env.production/.env.development
# and are never printed.
set -euo pipefail
# Git Bash rewrites arguments that look like POSIX paths (/data -> C:/Program Files/Git/data).
# Exclude only the flags carrying container paths; gcloud's own wrapper still needs conversion.
export MSYS2_ARG_CONV_EXCL="--add-volume;--add-volume-mount;--set-env-vars"

PROJECT_ID=shruti-509808
PROJECT_NUMBER=624531715077
REGION=asia-south1
BUCKET=$PROJECT_ID-shruti-media
REPO=$REGION-docker.pkg.dev/$PROJECT_ID/shruti
SA=shruti-run@$PROJECT_ID.iam.gserviceaccount.com
JOB=shruti-worker
SERVICE=shruti-api
# One job time limit for both services: the API enqueues with it (RQ job timeout)
# and uses it to detect stuck jobs; the worker task timeout must exceed it.
JOB_TIMEOUT=10800
TASK_TIMEOUT=$((JOB_TIMEOUT + 600))
APP_URL=https://$SERVICE-$PROJECT_NUMBER.$REGION.run.app
VOLUME="name=data,type=cloud-storage,bucket=$BUCKET,mount-options=uid=10001;gid=10001"

cd "$(dirname "$0")/.."
gcloud config set project "$PROJECT_ID" --quiet >/dev/null

read_env_file() {  # literal KEY=VALUE parsing: URLs contain '&' and must not be shell-evaluated
  [ -f "$1" ] || return 0
  local line key value
  while IFS= read -r line || [ -n "$line" ]; do
    line=${line%$'\r'}
    [[ $line =~ ^[[:space:]]*([A-Za-z_][A-Za-z0-9_]*)=(.*)$ ]] || continue
    key=${BASH_REMATCH[1]} value=${BASH_REMATCH[2]}
    value=${value%"${value##*[![:space:]]}"}
    if [[ $value =~ ^\"(.*)\"$ || $value =~ ^\'(.*)\'$ ]]; then value=${BASH_REMATCH[1]}; fi
    printf -v "$key" '%s' "$value"
  done < "$1"
}

load_env() {
  read_env_file .env.development
  read_env_file .env.production
  REDIS=${SHRUTI_REDIS_URL:-}
  REVISION=${SHRUTI_PROVIDER_REVISION:-groq-safety-v1}
  for name in SHRUTI_DB_URL GROQ_API_KEY SHRUTI_HF_TOKEN SHRUTI_UPLOAD_KEY; do
    [ -n "${!name:-}" ] || { echo "Missing $name in .env.production"; exit 1; }
  done
  [[ $REDIS == rediss://* || $REDIS == redis://* ]] || { echo "SHRUTI_REDIS_URL must be the Upstash rediss:// URL"; exit 1; }
}

put_secret() {  # name value
  if gcloud secrets describe "$1" >/dev/null 2>&1; then
    printf '%s' "$2" | gcloud secrets versions add "$1" --data-file=- >/dev/null
  else
    printf '%s' "$2" | gcloud secrets create "$1" --data-file=- --replication-policy=automatic >/dev/null
  fi
  echo "  secret $1 stored"
}

grant() {  # role
  gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:$SA" \
    --role="$1" --condition=None --quiet >/dev/null
  echo "  granted $1"
}

set_cors() {  # origins...
  local origins
  origins=$(printf '"%s",' "$@")
  printf '[{"origin":[%s],"method":["PUT","OPTIONS"],"responseHeader":["Content-Type","Content-Range","x-goog-resumable"],"maxAgeSeconds":3600}]' \
    "${origins%,}" > "${TMPDIR:-/tmp}/shruti-cors.json"
  gcloud storage buckets update "gs://$BUCKET" --cors-file="${TMPDIR:-/tmp}/shruti-cors.json" --quiet >/dev/null
}

setup() {
  load_env
  echo "[1/6] Enabling APIs (1-2 min)"
  gcloud services enable run.googleapis.com artifactregistry.googleapis.com \
    cloudbuild.googleapis.com secretmanager.googleapis.com storage.googleapis.com \
    iamcredentials.googleapis.com logging.googleapis.com

  echo "[2/6] Artifact Registry"
  gcloud artifacts repositories describe shruti --location="$REGION" >/dev/null 2>&1 ||
    gcloud artifacts repositories create shruti --repository-format=docker --location="$REGION"

  echo "[3/6] Media bucket"
  gcloud storage buckets describe "gs://$BUCKET" >/dev/null 2>&1 ||
    gcloud storage buckets create "gs://$BUCKET" --location="$REGION" --uniform-bucket-level-access
  set_cors "$APP_URL"

  echo "[4/6] Secrets"
  put_secret shruti-db-url "$SHRUTI_DB_URL"
  put_secret shruti-redis-url "$REDIS"
  put_secret shruti-groq-api-key "$GROQ_API_KEY"
  put_secret shruti-hf-token "$SHRUTI_HF_TOKEN"
  put_secret shruti-upload-key "$SHRUTI_UPLOAD_KEY"

  echo "[5/6] Service account and permissions"
  gcloud iam service-accounts describe "$SA" >/dev/null 2>&1 ||
    gcloud iam service-accounts create shruti-run --display-name="Shruti Cloud Run"
  sleep 10
  gcloud storage buckets add-iam-policy-binding "gs://$BUCKET" --member="serviceAccount:$SA" \
    --role=roles/storage.objectAdmin --quiet >/dev/null
  for role in roles/secretmanager.secretAccessor roles/run.developer roles/run.invoker \
      roles/artifactregistry.writer roles/logging.logWriter roles/storage.objectViewer; do
    grant "$role"
  done
  gcloud iam service-accounts add-iam-policy-binding "$SA" --member="serviceAccount:$SA" \
    --role=roles/iam.serviceAccountUser --quiet >/dev/null
  echo "  waiting 60s for IAM to propagate"
  sleep 60

  echo "[6/6] Starting Cloud Build (runs 10-15 min in the cloud)"
  gcloud builds submit --config cloudbuild.yaml --substitutions="_REPO=$REPO" \
    --service-account="projects/$PROJECT_ID/serviceAccounts/$SA" --async
  echo
  echo "Setup done. Check the build with:  bash deploy/gcp.sh status"
}

status() {
  gcloud builds list --limit=1 --format="table(id,status,createTime.date('%H:%M'),logUrl)"
}

deploy() {
  load_env
  local latest
  latest=$(gcloud builds list --limit=1 --format="value(status)")
  [ "$latest" = "SUCCESS" ] || [ -n "${SKIP_BUILD_CHECK:-}" ] || { echo "Latest build is '$latest'. Wait for SUCCESS (bash deploy/gcp.sh status)."; exit 1; }

  echo "[1/3] Worker job"
  gcloud run jobs deploy "$JOB" --image="$REPO/shruti-worker:latest" --region="$REGION" \
    --service-account="$SA" --command=python --args=-m,pipeline.worker \
    --cpu=8 --memory=16Gi --task-timeout=${TASK_TIMEOUT}s --max-retries=0 --tasks=1 \
    --add-volume="$VOLUME" --add-volume-mount=volume=data,mount-path=/data \
    --set-env-vars="^@^SHRUTI_DATA_DIR=/data@SHRUTI_GCS_BUCKET=$BUCKET@SHRUTI_PROVIDER_FACTORY=ai.factory:create_providers@SHRUTI_PROVIDER_REVISION=$REVISION@SHRUTI_WORKER_BURST=true@SHRUTI_JOB_TIMEOUT_SECONDS=$JOB_TIMEOUT@HF_HOME=/tmp/shruti-models/hf@SHRUTI_MODEL_CACHE_DIR=/tmp/shruti-models@SHRUTI_PANNS_CHECKPOINT=/data/models/panns/Cnn14_DecisionLevelMax.pth" \
    --set-secrets=SHRUTI_DB_URL=shruti-db-url:latest,SHRUTI_REDIS_URL=shruti-redis-url:latest,GROQ_API_KEY=shruti-groq-api-key:latest,SHRUTI_HF_TOKEN=shruti-hf-token:latest

  echo "[2/3] API + studio service"
  # Browser origins allowed to call the API and upload to the bucket: this service's
  # URLs plus any separately hosted frontend (FRONTEND_ORIGINS, comma-separated).
  local origins=("$APP_URL") actual
  actual=$(gcloud run services describe "$SERVICE" --region="$REGION" --format="value(status.url)" 2>/dev/null || true)
  [ -n "$actual" ] && [ "$actual" != "$APP_URL" ] && origins+=("$actual")
  IFS=',' read -ra extra <<< "${FRONTEND_ORIGINS:-}"
  for origin in "${extra[@]}"; do [ -n "$origin" ] && origins+=("${origin%/}"); done
  set_cors "${origins[@]}"
  deploy_service "[$(printf '"%s",' "${origins[@]}" | sed 's/,$//')]"
  echo "  allowed origins: ${origins[*]}"

  echo "[3/3] Readiness"
  sleep 5
  curl -s "$APP_URL/api/readiness"; echo
  echo
  echo "Open the studio: $APP_URL"
}

deploy_service() {  # allowed-origins JSON
  gcloud run deploy "$SERVICE" --image="$REPO/shruti-api:latest" --region="$REGION" \
    --service-account="$SA" --port=8000 --allow-unauthenticated --execution-environment=gen2 \
    --cpu=1 --memory=1Gi --min-instances=0 --max-instances=1 --timeout=600 \
    --add-volume="$VOLUME" --add-volume-mount=volume=data,mount-path=/data \
    --set-env-vars="^@^SHRUTI_DATA_DIR=/data@SHRUTI_GCS_BUCKET=$BUCKET@SHRUTI_CLOUD_RUN_WORKER_JOB=projects/$PROJECT_ID/locations/$REGION/jobs/$JOB@SHRUTI_ALLOWED_ORIGINS=$1@SHRUTI_PROVIDER_FACTORY=ai.factory:create_providers@SHRUTI_PROVIDER_REVISION=$REVISION@SHRUTI_COOKIE_SECURE=true@SHRUTI_JOB_TIMEOUT_SECONDS=$JOB_TIMEOUT" \
    --set-secrets=SHRUTI_DB_URL=shruti-db-url:latest,SHRUTI_REDIS_URL=shruti-redis-url:latest,SHRUTI_UPLOAD_KEY=shruti-upload-key:latest
}

case "${1:-}" in
  setup) setup ;;
  status) status ;;
  deploy) deploy ;;
  *) echo "Usage: bash deploy/gcp.sh setup|status|deploy"; exit 1 ;;
esac
