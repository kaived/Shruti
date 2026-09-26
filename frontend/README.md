# Shruti Studio — Frontend

React studio for uploading a Bengali video, following its progress, and reviewing the Bengali captions, English/Hindi subtitles and QC queue. Deployed on Cloudflare Pages; talks to the Cloud Run API.

## Stack

React 19 · Vite 7 · TypeScript (strict) · TanStack Query · Axios · Zod (runtime validation of every API response) · Tailwind + CSS tokens · lucide-react · JSZip

## Configuration

One variable, set in `.env.development` / `.env.production` (git-ignored; see [`.env.example`](.env.example)) or in Cloudflare Pages:

```dotenv
VITE_API_BASE_URL=https://shruti-api-624531715077.asia-south1.run.app
```

- Origin only — no `/api` and no trailing slash. The API version lives in [`src/shared/config/index.ts`](src/shared/config/index.ts) (`API_PREFIX = /api/v1`); all calls go through `apiPath()`.
- Empty value = same origin; in `npm run dev` the Vite proxy forwards `/api` to `127.0.0.1:8000`.
- Never put secrets in `VITE_` variables — they are embedded in the public bundle. The upload key is typed by the user and checked by the API.
- The API **and** Cloud Storage upload bucket must allow this site's exact origin. The deployment script includes `https://shruti.orbionixtech.com` and `https://shruti-ets.pages.dev` by default. After changing domains, set `FRONTEND_ORIGINS` and run `bash deploy/gcp.sh cors` to update both allowlists without rebuilding the API or worker.

## Develop and build

```bash
npm ci
npm run dev        # http://localhost:5173
npm run build      # tsc -b + production bundle in dist/
```

Deploy: `npx wrangler pages deploy dist --project-name <name>`, or connect the repo in Cloudflare Pages (root `frontend`, build `npm run build`, output `dist`, `NODE_VERSION=22`).

## How the studio works

- **Upload** (`features/upload-screen`): asks the API for a Cloud Storage upload session, uploads the file directly to the bucket with progress, then finalizes. Enter in the key field submits.
- **Progress** (`features/processing-screen`): polls job status and maps backend stages to six plain-language steps; finished steps keep their ✓, and errors are shown in plain words by error code.
- **Workspace** (`features/caption-workspace`): video player with caption overlay, captions list per language, ranked review queue (click to play the moment), speaker renaming, downloads.
- **My videos** (`layouts/Navbar.tsx`): job IDs and access tokens are stored in `localStorage` (last 15), so users can close the tab and reopen a video later in the same browser.
- **Keyboard shortcuts**: Space play/pause, J / L back/forward 2 s, 1 / 2 / 3 Bengali/English/Hindi (ignored while typing).

## API client

`src/shared/api-client/` — Axios instance with typed errors and plain-language messages (`core/client.ts`), Zod contracts (`core/contracts.ts`), and per-feature calls (`upload/`, `processing/`, `caption/`). The `<video>` element loads `/api/v1/jobs/{id}/media?access_token=…` because it cannot send an Authorization header across origins.
