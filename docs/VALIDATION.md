# Validation record — 26 September 2026

This is verification of an engineering starter. It is not a Bengali speech-model benchmark or a claim of hackathon completion.

| Check | Observed outcome |
| --- | --- |
| Backend dependency resolution | `uv.lock` created and installed successfully |
| Backend lint | Ruff passed |
| Backend formatting | Ruff format checks passed; final changed tests were formatted |
| Backend regression suite | 27 tests passed; one environment-dependent FFmpeg test skipped |
| Independent subtitle parsing | Generated Bengali VTT and Hindi SRT parsed successfully using webvtt-py and srt |
| Real media processing | FFmpeg generated and decoded a synthetic two-second video; extracted audio duration/rate/channel checks passed |
| API access isolation | Missing/wrong tokens rejected; protected range responses checked |
| Upload/resource controls | Oversized and empty uploads rejected; oversized temporary data removed |
| Inference configuration | Missing providers produce blocked/incomplete with no fake result |
| Queue outage | Visible failed state with explicit queue-unavailable message |
| Checkpoint recovery | Synthetic translation failure retried without repeating successful transcription; incomplete-stage retry invalidated only affected dependencies |
| AI adapter safety | Long audio chunk offsets/overlap deduplication, absent timestamp rejection, unresolved diarization, incomplete alignment/acoustics, shot decode failure and strict translation coverage tested |
| QC behaviour | Silence/music unsupported text, speech under music, dwell time, incomplete evidence, missing speech, shot crossings and translation coverage tested |
| Frontend dependency resolution | `package-lock.json` created and installed successfully |
| Frontend production build | TypeScript and Vite build passed; approximately 152 KB gzipped main JavaScript bundle in this build |
| Development servers | FastAPI and Vite started successfully |
| Browser visual inspection | Not performed: Playwright was available but no Chromium executable was installed |
| Docker Compose/PostgreSQL/real Redis worker | Not executed: Docker and redis-server were unavailable in the creation environment |
| Real Bengali inference | Not executed: real credentials were not used. Included Groq ASR/translation adapters remain unmeasured on Bengali footage; diarization, forced alignment and independent acoustic classification are intentionally incomplete |
| Supplied footage/held-out accuracy | Not evaluated; source videos were not available as video files in this workspace |
| Public demo / GitHub publication | Not performed; local repository and downloadable source archive only |

Runtime used: Python 3.12.14 and Node 24.19.0. The Docker/frontend configuration targets Node 22.12+; that container path still needs validation.

One upstream deprecation warning remains: the installed Starlette TestClient currently warns about its httpx integration. It did not cause test failures. No warnings were suppressed to obtain a passing result.

Synthetic data and adapter doubles are confined to the tests. They are not selected by default or exposed as live caption-generation endpoints. Real accuracy and QC usefulness must be measured on independently checked Bengali material before submission.
