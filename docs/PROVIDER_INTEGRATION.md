# Real inference integration contract

The included `ai.factory:create_providers` factory supplies bounded Groq recognition, strict Groq translation and PySceneDetect shot detection. It deliberately leaves diarization unresolved and reports alignment/acoustic evidence as incomplete. This boundary fails closed so ASR timestamps, energy heuristics or copied source text cannot be misrepresented as verified output.

Implement a trusted factory that returns `Providers(transcriber=..., aligner=..., acoustics=..., shots=..., translator=...)`. Configuration is server-controlled; it must never come from a request, transcript or model response.

| Adapter method | Input | Output / guarantees |
| --- | --- | --- |
| `transcribe(audio)` | Mono 16 kHz WAV preserving video-origin offsets | `Transcript`: real Bengali/mixed-English words, coarse global timings, provider/model identity and separate recognition/diarization completion. Handle chunk reconciliation internally; unresolved speakers stay unresolved. |
| `align(audio, transcript)` | Original working audio and recognized words | `Transcript`: same word IDs, text and speaker references, refined global intervals and truthful `alignment_complete`. Failures remain explicit. |
| `analyze(audio, duration_ms)` | Full working audio | `AudioEvidence`: independently obtained speech/music intervals, timed Bengali sound labels, evaluated duration and completeness. ASR-derived timestamps alone are not independent evidence. |
| `detect(video, duration_ms)` | Original video | `ShotAnalysis`: sorted shot-cut timestamps on the same timeline and truthful completeness. |
| `translate(cues, language)` | Bengali speech cues with context/source identity; `en` or `hi` | Target-language `Cue` objects with source cue IDs, coherent meaning and synchronized intervals. A legitimate no-dialogue video can yield an empty track. |

Use milliseconds relative to original video playback. Never reset timestamps or speaker IDs at a chunk boundary. Start/end times must be finite, ordered and in bounds. Code-switched words must survive alignment. Do not force an unsupported language through an aligner and silently label it complete.

Keep model versions and source artifacts. Store per-stage costs/tokens inside provider-specific traces if available, without secrets; the starter records stage timing but does not fabricate API costs. Bound provider requests, concurrency, retries and expenses. Prefer a single working provider configuration over a collection of untested fallbacks.

For optional naming, retain internal `speaker_id` and set `Speaker.display_name` with evidence and an accurate `name_status`. Only confirmed names are used by caption serialization. A real automatic naming/confirmation implementation is still required; there is no user-facing name editor in this starter.

The current QC layer validates acoustic support, source coverage and mechanical caption rules. It does not independently establish correct speaker identity, exact lexical content, sound meaning or translation semantics. Those limitations are exposed in every report. Connect stronger verification as evidence becomes available; do not set coverage labels to passed merely because a model call returned.

First integration experiment:

1. Choose a short real clip containing multiple speakers, a quiet/music interval and code-switching if available.
2. Exercise each adapter directly, checking returned contracts and actual audio.
3. Run the clip through the full worker, then parse/play all exports and inspect the queue.
4. Compare untouched output with a separately prepared reference excerpt; measure misses and false alarms.
5. Validate full-length speaker identity, then evaluate on footage not used for tuning.

Do not expose an API that accepts a transcript as if it came from uploaded-video recognition. Test doubles and fixtures must remain confined to the test suite.
