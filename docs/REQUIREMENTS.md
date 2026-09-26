# Shruti Caption Studio — System Requirements & Architecture Specification

**Project**: Shruti Caption Studio  
**Domain**: Automated Bengali Closed Captioning, Multilingual Subtitling & Acoustic Quality Control  
**Document Status**: Official Project Technical Specification & Architecture Contract  
**Version**: 1.0 (Production Architecture)  

---

## 1. Executive Summary & System Scope

**Shruti Caption Studio** is a broadcast-grade automated closed-captioning, multilingual subtitling, and acoustic verification platform tailored for Bengali media. The platform ingests original Bengali video/audio assets and executes a synchronized multi-stage pipeline:

1. **Media Ingestion & Audio Prep**: Container validation, decodability verification, scene-cut/shot boundary detection, and extraction of normalized 16kHz mono audio streams.
2. **Bengali ASR & Inline Code-Switching**: High-fidelity speech recognition preserving Bengali syntax and inline English code-switching with precise word-level timestamps.
3. **Speaker Diarization & Character Tracking**: Voice clustering attributing dialogue to distinct characters across scenes, with studio tools for global character renaming.
4. **Forced Alignment & Shot-Cut Compliance**: Word-to-audio temporal alignment and cue segmentation that respects scene boundaries without straddling video cuts.
5. **Contextual Translation**: LLM-driven translation into colloquial, natural English and Hindi subtitle tracks while strictly preserving speaker voice, idioms, and narrative tone.
6. **Acoustic Evidence QC & Hallucination Audit**: Independent acoustic validation verifying subtitle presence against speech energy, detecting silence and music intervals to eliminate ungrounded hallucinations.
7. **Studio Review Workstation**: Split-pane reviewer interface featuring interactive video playback, synchronized audio scrubber, timeline tracks, inline cue editing, and an actionable QC issue queue.

---

## 2. Implemented Technology Stack

| Layer | Technologies & Components | Architecture Role |
|---|---|---|
| **Frontend Framework** | **React 19, TypeScript, Vite** | Fast, responsive Single Page Application with strict typing and modern tooling. |
| **Styling & Design System** | **Tailwind CSS v4 & Shared UI System** | Modular, responsive styling with theme design tokens (`#0047ab` Cobalt Blue, Alabaster canvas, Charcoal text). Shared UI library located in `frontend/src/shared/ui/components` (`Button`, `Modal`, `Input`, `Select`, `Textarea`, `FormField`). |
| **Backend API** | **FastAPI (Python 3.11+), Pydantic v2, Uvicorn** | Versioned RESTful API (`/api/v1/*`), async request processing, strict data schema validation, and health/readiness endpoints. |
| **Media Processing** | **FFmpeg & PyAV** | Container demuxing, video stream inspection, 16kHz mono audio normalization, and frame-accurate visual scene-cut/shot detection. |
| **Queue & Persistence** | **Redis, PostgreSQL & SQLite** | Atomic job leasing, decoupled asynchronous task execution, and durable job checkpointing across restarts. |
| **Containerization** | **Docker & Docker Compose** | Reproducible multi-service deployment (`frontend`, `backend`, `worker`, `redis`). |

### 2.1. Complete AI Models & Algorithmic Engines Suite

The platform orchestrates a multi-model ensemble across audio recognition, language translation, acoustic analysis, and computer vision:

| Capability | Model / Engine Name | Provider / Runtime | Purpose & Specifications |
|---|---|---|---|
| **Bengali ASR & Transcriber** | **`whisper-large-v3`** | **Groq Cloud API** (`GroqWhisperTranscriber`) | Extracts Bengali speech transcriptions with word-level timestamps in 15-second chunks (2s overlap deduplication) with specialized Bengali prompting forbidding ungrounded hallucination. |
| **Multilingual Translation** | **`openai/gpt-oss-120b`** (or `llama-3.3-70b-versatile`) | **Groq Cloud API** (`GroqLLMTranslator`) | Context-windowed LLM translation generating natural, colloquial English and Hindi subtitles while strictly respecting subtitle pacing limits (17 CPS, 37 CPL). |
| **Code-Switching Normalizer** | **`openai/gpt-oss-120b`** (or `llama-3.3-70b-versatile`) | **Groq Cloud API** (`GroqCodeSwitchNormalizer`) | Normalizes Bengali-transliterated English loanwords into standard Latin orthography with hyphenated Bengali grammatical suffixes (e.g., *অফিসে* → *office-এ*, *মিটিংয়ে* → *meeting-এ*). |
| **Speaker Diarization** | **`pyannote/speaker-diarization-community-1`** | **pyannote.audio** via Hugging Face (`PyannoteDiarizer`) | Full-waveform voice clustering attributing turns to distinct character voices (`SPEAKER_00`, `SPEAKER_01`) and detecting overlapping speech segments. |
| **Forced Temporal Alignment** | **Multilingual Whisper (`small`)** | **`stable-ts` / `stable-whisper`** (`StableWhisperAligner`) | Monotonically aligns Groq ASR words against the 16 kHz audio track to compute millisecond-accurate acoustic phoneme boundaries. |
| **Sound Event Detection (SED)** | **PANNs CNN14** (`Cnn14_DecisionLevelMax`) | **AudioSet PANNs / PyTorch** (`ModelAcousticAnalyzer`) | Detects non-speech audio events (Laughter *হাসি*, Applause *হাততালি*, Telephone *ফোন বাজছে*, Knock *দরজায় কড়া নাড়ার শব্দ*, Door *দরজার শব্দ*, Music, Silence). |
| **Acoustic Evidence & VAD** | **Energy VAD & Spectral Analyzer** | **PyAV / NumPy Spectral** (`ModelAcousticAnalyzer`) | Audits speech energy across the recording to verify subtitle cues against acoustic evidence, flagging `SUSPECTED_HALLUCINATION` and `SPEECH_WITHOUT_TEXT`. |
| **Visual Shot Detection** | **PySceneDetect (`ContentDetector`)** | **PySceneDetect / OpenCV** (`SceneCutDetector`) | Frame-accurate camera cut detection to enforce broadcast compliance (cues never straddle video cuts). |

---

## 3. Standard Broadcast Subtitle Profile

The platform enforces the following broadcast captioning constraints across all generated and edited subtitle tracks:

| Parameter | Bengali Closed Captions (`.vtt`) | English Subtitles (`.srt`) | Hindi Subtitles (`.srt`) | Enforcement Method |
|---|---|---|---|---|
| **Max Reading Speed** | **17 CPS** (Characters / Sec) | **17 CPS** | **17 CPS** | Automated QC flag & cue retiming |
| **Max Line Length** | **37 CPL** (Characters / Line) | **37 CPL** | **37 CPL** | Monotonic linguistic line wrapping |
| **Max Lines per Cue** | **2 Lines** | **2 Lines** | **2 Lines** | Segmentation engine constraint |
| **Min Cue Duration** | **1.0 Second** (1000 ms) | **1.0 Second** | **1.0 Second** | Retiming filter with minimum gap |
| **Max Cue Duration** | **7.0 Seconds** (7000 ms) | **7.0 Seconds** | **7.0 Seconds** | Automatic cue splitting |
| **Shot-Crossing Policy** | **No Straddling Across Cuts** | **No Straddling Across Cuts** | **No Straddling Across Cuts** | Scene cut detector alignment |
| **Inter-Cue Gap** | **Min 2 Frames (~80 ms)** | **Min 2 Frames** | **Min 2 Frames** | Buffer insertion |

---

## 4. Functional Specifications by Module

### 4.1. Media Ingestion & Canonical Timeline
- **Format Support**: Ingest video containers in MP4, MKV, and WebM format up to 500 MB.
- **Integrity Validation**: Validate stream decodability, duration, video frame rate, and audio track presence. Reject corrupted files or video without audio with clear, actionable diagnostics.
- **Canonical Timeline**: All timestamps (words, cues, sound events, visual cuts, and QC issues) are anchored to a unified millisecond timeline relative to the original video media.
- **Resilient State Persistence**: Each processing run is assigned a unique `job_id` and media checksum. Job state and progress persist across browser refreshes.

### 4.2. Bengali Recognition & Inline Code-Switching
- **ASR Model**: Groq Whisper Large v3 extracts word-level transcriptions with millisecond start/end boundaries.
- **Code-Switching Support**: Accurate recognition of mixed Bengali-English sentences (e.g., *“ওর office-এ একটা urgent meeting আছে”*).
- **Acoustic Grounding**: Retain acoustic confidence for every word. The pipeline verifies that recognized text corresponds to audible speech rather than hallucinated patterns over silence or background music.

### 4.3. Speaker Diarization & Character Renaming
- **Cluster Tracking**: Dialogue turns are attributed to stable speaker identifiers (`Speaker 1`, `Speaker 2`, etc.) across the full duration.
- **Global Character Renaming**: The studio review workstation allows operators to rename any speaker ID (e.g., `Speaker 1` → `অমিত / Amit`). Renaming propagates instantly across all Bengali, English, and Hindi cues without altering the underlying acoustic evidence.

### 4.4. Multilingual Translation
- **Target Languages**: English (`.srt`) and Hindi (`.srt`), translated directly from the aligned Bengali transcript.
- **Contextual Integrity**: Context-windowed LLM translation (LLaMA 3.3 70B) preserves honorifics, colloquial phrasing, humor, and emotional weight.
- **Independent Timing & Line Pacing**: Translated subtitles are independently formatted to respect reading speed (17 CPS) and line length (37 CPL) limits while maintaining source-cue synchronization.

### 4.5. Acoustic QC & Hallucination Prevention
- **Speech vs. Non-Speech Audit**: The acoustic analyzer computes speech energy across the recording. Subtitle cues that fall in intervals of silence or background music without acoustic speech evidence are flagged as `SUSPECTED_HALLUCINATION`.
- **Missed Speech Detection**: Audible speech segments lacking transcript representation receive `SPEECH_WITHOUT_TEXT` warnings.
- **Ranked Review Queue**: QC issues are cataloged by severity (`critical`, `high`, `medium`, `clean`) with exact timestamps, evidence metrics (CPS velocity, rule thresholds, music overlap duration), and one-click seek navigation in the video player.

### 4.6. Studio Review Workstation & Playback Experience
- **Interactive Player**: Synchronized HTML5 video playback with custom caption overlay rendering, seek controls, speed selectors (0.5x to 2x), and keyboard shortcuts.
- **Timeline & Waveform Tracks**: Audio waveform visualization displaying cue boundaries, speaker color blocks, and flagged QC regions.
- **Inline Subtitle Editor**: Operators can adjust text, start/end timestamps, and speaker assignments directly with undo support.
- **Export Bundle**: Multi-format downloads including Bengali WebVTT (`bengali.vtt`), English Subtitles (`english.srt`), Hindi Subtitles (`hindi.srt`), Automated QC Report (`qc_report.json`), and comprehensive ZIP packages.

---

## 5. System API Architecture

All client-server interactions are standardized on the versioned REST API (`/api/v1/*`):

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/jobs` | Initialize a new captioning pipeline run for an uploaded video. |
| `GET` | `/api/v1/jobs/{job_id}` | Poll real-time pipeline status, progress percentage, current stage, and errors. |
| `GET` | `/api/v1/jobs/{job_id}/results` | Retrieve generated tracks (BN, EN, HI), speaker lists, and QC issues. |
| `PUT` | `/api/v1/jobs/{job_id}/tracks/{lang}/cues/{cue_id}` | Save user edits to a specific caption cue text, speaker, or timestamps. |
| `POST` | `/api/v1/jobs/{job_id}/speakers/rename` | Globally rename a speaker ID across all tracks. |
| `GET` | `/api/v1/jobs/{job_id}/export/{format}` | Download individual export files (`vtt`, `srt`, `json`, `zip`). |
| `GET` | `/api/v1/health` | Service health, model availability, and Redis queue status. |

---

## 6. Shared UI Design System Architecture

The frontend uses standard Tailwind CSS utilities and a modular shared design system in `frontend/src/shared/ui/components`:

- **`Button`**: High-accessibility button with standard professional sizing (`sm: h-8`, `md: h-9`, `lg: h-10`), studio Cobalt Blue theme (`#0047ab`), loading states, and icon slots.
- **`Modal`**: Flexible dialog component with backdrop blur, keyboard dismissal (Escape), scroll locking, responsive `maxWidth` presets, header badges, and structured footer.
- **`Input` / `Select` / `Textarea`**: Theme-calibrated form controls with Cobalt focus rings, labels, error hints, and icon slots.
- **`FormField`**: Wrapper component maintaining consistent label, badge, and validation spacing across all forms.

---

## 7. Deliverables & Output Formats

Every completed pipeline run generates production-compliant deliverables:

1. **`bengali.vtt`**: W3C WebVTT closed-caption file featuring Bengali dialogue, speaker voice annotations (`<v SpeakerName>`), and non-speech sound indicators.
2. **`english.srt`**: SubRip subtitle file with colloquial English translation timed to 17 CPS and 37 CPL standards.
3. **`hindi.srt`**: SubRip subtitle file with culturally natural Hindi translation timed to broadcast specifications.
4. **`qc_report.json`**: Machine-readable audit report documenting all acoustic checks, issue counts, reading rates, and system limitations.
5. **Multi-Track ZIP Bundle**: Unified archive package containing all three subtitle tracks, QC reports, and media run metadata.
