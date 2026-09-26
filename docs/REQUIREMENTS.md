**Hoichoi PS2 — Overall Project Requirements**

Prepared: 26 September 2026. Status: proposed implementation requirements, not a claim that the system has been built or validated. Basis: the problem statement, rules, supplied-resource screenshots and decisions in this conversation.

The product accepts Bengali video and produces a Bengali closed-caption track, English and Hindi subtitle tracks, and an actionable quality-control report. The user has chosen PS2 and wants reliability, efficiency, convenient review and optional speaker naming.

The hackathon is a solo build, running from 11:00 AM to 11:00 PM IST on 26 September 2026. The submission requires a working demo link, public GitHub repository and explanatory video under five minutes. AI must be central to a functioning end-to-end solution.

**How to read the requirements**

| Label | Meaning |
| --- | --- |
| B | Required behaviour or deliverable in the supplied hackathon brief/rules. |
| D | Derived implementation requirement proposed to deliver that behaviour reliably. These are design decisions, not additional organiser rules. |
| O | Optional enrichment: speaker naming is requested if feasible; other enhancements are clearly identified. |
| P | Further work before a real production rollout. It is not all part of a 12-hour build. |

Requirements describe behaviour; they do not mandate a vendor, framework, model or multi-agent architecture. Thresholds and resource budgets absent from the brief remain open decisions. Numeric quality claims must come from measurements, not estimates presented as results.

**1. Scope, inputs and deliverables**

| ID | Level | Requirement |
| --- | --- | --- |
| SCP-01 | B | Process a Bengali-language video through ASR, diarization, forced alignment, cue segmentation, Bengali CC, English/Hindi translation and QC. Naming is optional. |
| SCP-02 | B | Produce Bengali WebVTT with speaker attribution and relevant non-speech sounds, English SRT, Hindi SRT, and a ranked review queue in a QC report. |
| SCP-03 | B | Generalize to held-out episodes. A hand-corrected transcript for sample episodes must not be substituted for pipeline output. |
| SCP-04 | B | Run live at presentation time through the deployed demo. A recorded walkthrough alone is insufficient. |
| SCP-05 | D | Use the same processing path for new uploads and supplied samples; do not branch on sample filenames or insert memorized transcripts/timestamps. |
| SCP-06 | D | Keep the original automated output distinguishable from any later reviewed version. Editing is an enhancement, not a substitute for automatic quality. |

Suggested output filenames are `bengali.vtt`, `english.srt`, `hindi.srt` and `qc_report.json`. JSON is a proposed report format, not an organiser-prescribed extension. The application also renders the report as a ranked queue. An optional downloadable bundle may contain all four outputs plus run metadata.

The screenshots show these input assets:

| File | Displayed size |
| --- | --- |
| `bhojon_bilashi.mp4` | 101.4 MB |
| `feluda.mp4` | 173 MB |
| `indubala_bhaater_hotel.mp4` | 107.6 MB |
| `mandaar.mp4` | 225.8 MB |
| `mohanagar.mp4` | 96.8 MB |
| `money_honey.mp4` | 106.1 MB |

Only the screenshots have been inspected for this specification. Video duration, codecs, audio quality, speaker counts and dialogue content are unverified. No reference transcripts, speaker annotations, models, evaluation scripts or caption profile are visible in these screenshots; this does not establish that organisers have no additional resources elsewhere.

**2. Media ingestion and timeline preservation**

| ID | Level | Requirement |
| --- | --- | --- |
| MED-01 | B | Accept and process the supplied Bengali videos. |
| MED-02 | D | Check the actual media container and decodability, duration, audio/video streams, timestamps and supported codecs. Reject corrupt, unsupported or missing-audio inputs with a specific error. |
| MED-03 | D | Display and enforce supported formats and configured file-size/duration limits. Limits must accommodate the actual evaluation inputs or the restriction must be explicitly disclosed. |
| MED-04 | D | Preserve original media and extract a working audio copy suitable for the chosen models. Record resampling, channel selection and preprocessing. Preserve useful channel separation when relevant. |
| MED-05 | D | Use one canonical timeline relative to the original video. Account for stream offsets, chunk offsets and variable frame rates; silence removal must not shift exported timestamps. |
| MED-06 | D | Assign a job ID and media checksum. Persist progress and processing status so refreshing the interface does not restart inference. |
| MED-07 | D | Support full recordings through bounded chunk processing where necessary. Short excerpts accelerate development but must not become the only supported runtime without an explicit limitation. |

Audio normalization and denoising are implementation choices. They must not erase quiet speech or invalidate synchronization. Retain the original audio for review.

**3. Bengali recognition and speech evidence**

| ID | Level | Requirement |
| --- | --- | --- |
| ASR-01 | B | Recognize Bengali dialogue and inline English code-switching, including mixed constructions such as “ওর office-এ একটা meeting আছে”. |
| ASR-02 | D | Preserve meaning-bearing words, negation, names, numbers, relationships and register. Do not translate the Bengali source transcript into another language during recognition. |
| ASR-03 | D | Define a consistent punctuation, spelling and mixed-script policy. Any normalization must preserve the raw recognition result and must not invent missing speech. |
| ASR-04 | D | Examine speech/activity evidence across the recording, including background music, silence and low-volume dialogue. Do not treat music as proof that speech is absent. |
| ASR-05 | D | Retain provider confidence and acoustic/alignment evidence where available, with their provenance. A missing score is unknown, not a perfect score; arbitrary scores are not calibrated probabilities. |
| ASR-06 | D | Detect suspicious repetitions, unsupported text, likely omitted speech and gaps in coverage. Use reprocessing or review flags for uncertain intervals. |
| ASR-07 | D | Reconcile overlapping chunks without duplicated or omitted dialogue, and reconstruct global word/segment order. |
| ASR-08 | D | Evaluate code-switching and quiet speech separately from clean Bengali speech. A hard speech-detection gate must not silently discard difficult speech to improve apparent hallucination performance. |

A language model may assist with punctuation or contextual checks, but grammatical plausibility is not evidence that words were spoken. Corrections require audio support or explicit human review.

**4. Speaker diarization and optional naming**

| ID | Level | Requirement |
| --- | --- | --- |
| SPK-01 | B | Attribute dialogue to stable speaker IDs across the entire runtime without identity swaps. |
| SPK-02 | D | Reconcile identities across chunks and long gaps. IDs are local to a recording; cross-episode identity recognition is not required. |
| SPK-03 | D | Represent overlapping speech and ambiguous short turns. Do not force uncertain material into a falsely confident single-speaker assignment. |
| SPK-04 | D | Support off-screen speech; a person need not appear on screen to receive a speaker ID. Flag ambiguous attribution for review. |
| SPK-05 | D | Keep permanent internal speaker IDs separate from editable display names. A name change updates references consistently without rewriting attribution evidence. |
| NAM-01 | O | Accept an optional character/cast list and use it to constrain name candidates and spelling. Distinguish character names from actor names. |
| NAM-02 | O | Propose names using contextual evidence such as self-introductions or direct address. Store supporting timestamps and the evidence source. A cast list alone cannot map voices to names. |
| NAM-03 | O | Avoid assigning an addressed name to the person who said it. An adjacent reply alone is not conclusive identity evidence. |
| NAM-04 | O | Track unknown, suggested and confirmed naming states. Preserve anonymous labels when evidence is insufficient; naming failure must not block mandatory outputs. |
| NAM-05 | O | Allow confirmation/correction of suggested names while retaining the original automatic mapping and review history. Do not present manual name confirmation as automatic naming accuracy. |

Facial recognition, identification of real people and face-to-voice matching are not required by this MVP. Voice-based speaker attribution and evidence-backed fictional character names cover the requested scope.

**5. Forced alignment and shot information**

| ID | Level | Requirement |
| --- | --- | --- |
| ALN-01 | B | Perform forced alignment of the transcript to the audio. Verify that the selected alignment approach can handle Bengali and mixed English; ASR timestamps alone must not be described as a separate alignment step. |
| ALN-02 | D | Store word/phrase boundaries and alignment failures, preserving the source transcript and global media offsets. Do not invent precise timings for unaligned words. |
| ALN-03 | D | Validate non-negative intervals, positive durations, ordering and media bounds. Distinguish real simultaneous speech from accidental timing overlaps. |
| ALN-04 | D | Flag poor alignment and uncertain boundaries. Alignment is timing evidence; a successfully aligned sentence is not proof that its text is correct. |
| SHT-01 | D | Obtain shot-change timestamps from video analysis and map them to the canonical timeline. Audio-only processing cannot verify visual-cut constraints. |
| SHT-02 | B | Enforce the brief's no-straddling requirement for cues. When constraints conflict, resegment/retime where possible and surface unresolved violations rather than claiming compliance. |

Some published timing guides permit limited shot-crossing exceptions. The hackathon wording is stricter; implement its rule unless the organisers explicitly clarify otherwise. External guides are references, not substitutes for this acceptance contract.

**6. Cue segmentation and readability**

| ID | Level | Requirement |
| --- | --- | --- |
| CUE-01 | B | Construct readable timed cues with CPS limits, line-length limits and compliance with shot boundaries. |
| CUE-02 | D | Use versioned language-specific profiles for maximum CPS, characters per line, line count, minimum/maximum duration, cue gaps, timing tolerances and speaker/sound-label conventions. |
| CUE-03 | D | Prefer linguistic boundaries; preserve negation and meaning. Respect speaker changes and the configured treatment of simultaneous speakers. |
| CUE-04 | D | Define what counts as a character for CPS and line length, including spaces, punctuation, labels and combining marks. Preserve Bengali/Devanagari character clusters and correct rendering. |
| CUE-05 | D | Adjust segmentation and timing within supported speech/shot constraints. Do not silently drop words, invent summaries or detach text from speech to pass readability checks. |
| CUE-06 | D | Validate duration, order, unwanted overlap, duplicates, blank cues, out-of-bounds times and shot crossings. Genuine overlap requires an explicit rendering policy. |
| CUE-07 | D | Apply checks independently to Bengali, English and Hindi. Translations may require different line breaks or cue boundaries while preserving source links and synchronization. |
| CUE-08 | D | Store unresolved constraint conflicts in QC. A valid file can still fail timing or readability requirements. |

The supplied brief specifies no numeric profile. Do not silently declare values such as a particular CPS or line length to be official. Document provisional values and replace them with organiser-supplied values when available. Forced narratives/on-screen text and lyrics require clarification; they must not be silently presented as ordinary spoken dialogue.

**7. Bengali CC and English/Hindi translation**

| ID | Level | Requirement |
| --- | --- | --- |
| CC-01 | B | Include Bengali dialogue, stable speaker attribution and relevant non-speech sound events in the Bengali WebVTT track. |
| CC-02 | D | Detect and time supported sound classes, such as music, laughter, crying, ringing or knocking. Use Bengali labels and disclose taxonomy limits; do not invent an event's source or emotional meaning. |
| CC-03 | D | Allow sound events and dialogue to coexist. Caption relevant events without turning every background sound into an unnecessary cue. |
| CC-04 | D | Distinguish sound captions from spoken text and unverified words. Sound-event detection must be grounded in audio and its uncertainties must reach QC. |
| CC-05 | D | Preserve machine-readable speaker linkage and verify viewer-visible attribution in the demo. Voice metadata alone must not be assumed to display a readable name in every player. |
| TRN-01 | B | Produce English and Hindi subtitle translations. |
| TRN-02 | D | Translate with sufficient surrounding context to preserve negation, numbers, names, relationships, pronouns, idioms and tone. Maintain a consistent name/term glossary. |
| TRN-03 | D | Link translated cues to source dialogue/cue IDs even when segmentation differs. Propagate source uncertainty and prevent ungrounded additions. |
| TRN-04 | D | Revalidate translation length, timing and completeness independently. Detect blank, duplicated or missing translations. |
| TRN-05 | D | If a source cue is corrected, invalidate affected translations/QC and regenerate only the affected context as needed. Do not export silently stale translations. |

The brief explicitly requires non-speech sounds and speaker attribution in Bengali CC. It does not explicitly require full SDH/CC treatment in the English/Hindi tracks; retain their internal speaker/source mappings and confirm any additional display convention with organisers.

**8. Hallucination safeguards and quality control**

| ID | Level | Requirement |
| --- | --- | --- |
| QC-01 | B | Surface hallucinated subtitle text over silence/music in held-out content. Unflagged occurrences are an auto-disqualifier under the brief. |
| QC-02 | D | Combine speech/activity evidence, alignment evidence and other available recognition signals. Do not depend exclusively on the ASR model's self-reported confidence or a text-only grammar check. |
| QC-03 | D | Check the underlying audio interval, not only whether a caption remains visible during a pause. Legitimate reading-time extensions and valid music/sound captions are not automatically hallucinations. |
| QC-04 | D | Detect both unsupported text and likely missing speech. Do not obtain apparent safety by exporting empty tracks or omitting difficult intervals without disclosure. |
| QC-05 | B | Produce a ranked review queue tied to specific cues/intervals. It will be evaluated against actual errors. |
| QC-06 | D | Each issue includes an ID, affected cue/interval and language, timestamps, type, severity, risk score or evidence summary, reason, suggested review action and review state. Missing-cue issues may reference an interval without a cue ID. |
| QC-07 | D | Include suspected hallucination, missed speech, recognition uncertainty, speaker ambiguity/overlap, naming uncertainty, alignment failure, readability, shot crossing, translation and serialization issues. |
| QC-08 | D | Rank by likely error and consequence using a documented policy. Deduplicate related issues and preserve their relationships to source and translated cues. |
| QC-09 | D | Report counts by issue type/severity, affected duration, unreviewed high-risk items, profile violations and check coverage. Unknown/unperformed checks must be explicit. |
| QC-10 | D | Keep processing status, QC status and review/release status separate. A failed QC component cannot yield an all-clear result. |
| QC-11 | D | Preserve suspicious raw output in the audit record. If text is removed or withheld, explain the decision in QC and keep omissions inspectable. Flagging a cue does not automatically correct it. |
| QC-12 | D | Require resolution of critical issues before calling an export reviewed/release-ready. Draft outputs remain downloadable with their flags for judging and review. This release distinction is our product design, not an extra organiser approval rule. |

Suggested issue codes include `SUSPECTED_HALLUCINATION`, `SPEECH_WITHOUT_TEXT`, `LOW_ASR_SUPPORT`, `SPEAKER_UNCERTAIN`, `OVERLAP_UNRESOLVED`, `ALIGNMENT_FAILED`, `CPS_EXCEEDED`, `LINE_LIMIT_EXCEEDED`, `SHOT_CROSSING`, `TRANSLATION_MISMATCH` and `INVALID_OUTPUT`.

**9. Reviewer experience and export behaviour**

| ID | Level | Requirement |
| --- | --- | --- |
| UX-01 | D | Provide upload, clear job progress, explicit errors, video preview, track selection, ranked QC queue and individual downloads. |
| UX-02 | D | Clicking an issue seeks to the relevant interval with a small context window. Show the cue, speaker, reason and supporting evidence beside playback. |
| UX-03 | D | Filter by issue type, severity, language and review state. Show the raw Bengali cue alongside corresponding translations and naming evidence when relevant. |
| UX-04 | D | Preserve the job after refresh; disable unavailable actions and describe partial results honestly. The interface must remain responsive while processing occurs. |
| UX-05 | O | Add focused editing of text, speaker/name and timing, with resolution/reopen controls. Revalidate changes and retain version history. A full timeline editor is not required by the brief. |
| EXP-01 | B | Export the required Bengali WebVTT and English/Hindi SRT files and the QC report from the same run. |
| EXP-02 | D | Validate syntax with a parser and check playback in the deployed player. Preserve UTF-8 text and use correct serialization for each format. Do not rename a VTT file to SRT. |
| EXP-03 | D | Ensure downloads, preview and QC reference the same content revision. Reparse outputs to catch dropped or duplicated cues. |
| EXP-04 | D | Provide a manifest/metadata section with media ID/checksum, language tracks, run/configuration versions, profile, status and generation time. Avoid exposing credentials or internal paths. |
| EXP-05 | D | If the preview needs a WebVTT derivative of an SRT track, generate it from the same canonical cues while retaining the required SRT download. Verify Bengali/Hindi glyph rendering. |

WebVTT file conformance and editorial quality are separate checks. The W3C specification defines WebVTT syntax and cue/voice semantics; a broadcaster's caption profile determines additional presentation requirements. [1]

**10. Data and processing contracts**

These are logical records. They do not each require a separate database table or service.

| Record | Minimum information |
| --- | --- |
| Media/job | IDs, ownership/access scope, input checksum, duration/streams, original timestamp mapping, run configuration, state and outputs. |
| Stage attempt | Stage/version, inputs, outputs, attempt count, start/end time, failure reason, provider/model version, measured cost and runtime. |
| Speech/word | Stable ID, raw and normalized text, language information, interval, speaker reference, confidence/evidence and alignment status. |
| Speaker/name mapping | Stable ID, evidence references, optional display name, candidate source and confirmation state. |
| Sound/shot event | Event type, interval or boundary, detector version, score/evidence and review state where relevant. |
| Cue | Stable ID, language, text, timing, speaker references, source word/event IDs, source links, profile/revision and validation results. |
| QC issue | Type, severity, ranking information, affected cues/intervals/languages, evidence, suggested action and review state. |
| Edit/export | Original and revised values, actor/time if applicable, change dependencies, output version and QC/review status. |

| ID | Level | Requirement |
| --- | --- | --- |
| DAT-01 | D | Maintain referential integrity across words, speakers, cues, translations, issues and exports. Store one canonical time unit and convert at boundaries. |
| DAT-02 | D | Preserve raw model responses separately from normalized/reviewed records. Record configuration/model/prompt versions needed to trace a result. |
| DAT-03 | D | Cache with keys incorporating media, relevant configuration and model versions. Source/config changes invalidate only affected downstream stages; do not share private media caches across access scopes. |
| DAT-04 | D | Define typed, validated stage inputs/outputs. Partial or malformed provider responses must fail or be flagged explicitly. |
| DAT-05 | D | Provide backend operations for upload/job creation, progress/results, issues, downloads and controlled retry. Review/name actions are added when those optional features are implemented. |

**11. Efficiency and recovery requirements**

| ID | Level | Requirement |
| --- | --- | --- |
| OPS-01 | D | Run long processing outside the web request lifecycle with durable state/checkpoints. A single backend plus worker is a reasonable initial design; microservices are not required. |
| OPS-02 | D | Reuse extracted audio, transcript, speaker mapping, alignment and shot analysis across output languages. Avoid retranscribing for each translation. |
| OPS-03 | D | Bound concurrency, chunk size, retries, timeout and spending. Retry transient failures with a cap; do not retry invalid inputs or missing credentials indefinitely. |
| OPS-04 | D | Resume from a failed stage without repeating unrelated successful inference. Ensure idempotent retries do not duplicate cues, exports or external charges unnecessarily. |
| OPS-05 | D | Use additional inference selectively on uncertain intervals where justified, while preserving adequate coverage checks on the full recording. |
| OPS-06 | D | Measure upload delay, queue time, processing wall time, stage latency, media duration, cost per minute, resource use and cache effectiveness. Separate cold and cached runs. |
| OPS-07 | D | Define a real-time factor as processing seconds divided by media seconds and report its conditions. Do not promise a speed or cost target before hardware/API measurements. |
| OPS-08 | D | Keep model/provider adapters replaceable, pin dependencies and validate required capabilities before adopting a component. Choose one working primary path for the hackathon. |
| OPS-09 | D | Report processing failures separately from caption quality. If a mandatory stage fails, label the run incomplete and expose usable partial drafts where appropriate. |

**12. Security and media handling**

| ID | Level | Requirement |
| --- | --- | --- |
| SEC-01 | D | Keep API keys and service credentials server-side and out of the public repository, downloads, browser bundle and logs. |
| SEC-02 | D | Protect uploaded videos, transcripts and exports with an access boundary. The public demo URL must not make every user's uploaded media publicly browsable. A scoped demo/session design is sufficient initially. |
| SEC-03 | D | Validate uploaded media, paths and resource limits. Run media commands with safe arguments and bounded CPU/memory/runtime; do not interpolate untrusted input into shell commands. |
| SEC-04 | D | Treat transcripts, filenames and cast-list text as data in model requests. Do not let embedded instructions control tools, export paths or secret handling. |
| SEC-05 | D | Document whether media is sent to external providers and the chosen retention/deletion behaviour. Remove temporary files and support deleting a job's derived artefacts. |
| SEC-06 | D | Serve the demo through HTTPS and use appropriate controlled access for media downloads. Public code does not imply permission to redistribute the supplied videos. |
| SEC-07 | P | Before wider rollout, validate role-based access, tenant isolation where applicable, encryption/backups, provider terms, audit retention and incident handling against the actual deployment context. |

These safeguards follow from handling uploaded media in a public demo and the user's production goals. Enterprise account management, billing and organisation administration are not hackathon MVP requirements.

**13. Evaluation and evidence**

Use short annotated excerpts for targeted evaluation and reserve at least one available video from tuning if feasible. Reference annotations must remain separate from inference inputs and exports. A video you reserve internally is not the same as the judges' held-out set.

| Metric | What to report |
| --- | --- |
| Word error rate (WER) | Substitutions + deletions + insertions, divided by reference words; disclose tokenization and normalization. |
| Character error rate (CER) | Equivalent character-level comparison with an explicit Unicode counting convention. |
| Code-switch accuracy | Errors on mixed Bengali/English spans, separately from overall results. |
| Diarization quality | Speaker confusion, missed speech and false-alarm speech; document overlap treatment, boundary tolerance and global speaker-label matching. |
| Alignment quality | Start/end boundary errors on manually checked words or cues, with the checked sample size. |
| Hallucination detection | Actual unsupported-text events caught and missed; report unflagged events and non-speech hours/minutes evaluated. |
| Speech coverage | True speech omitted or suppressed, including whispers and speech under music. |
| Review precision/recall | Confirmed actionable flags / flags reviewed; matched actual errors / actual errors. Specify cue/interval matching rules and avoid double-counting. |
| Queue usefulness | Actual errors found in the first K items and review workload, with K and sample size reported. |
| Translation quality | Human checks of meaning, negation, names, numbers, fluency and source uncertainty in English and Hindi. |
| Caption compliance | Violations by rule/language and parser/playback pass results. |
| Sound-event quality | Supported event detection/label errors and false alarms on annotated intervals. |
| Operational efficiency | Measured time/cost per media minute, stage failures, retry behaviour and cold versus cached performance. |
| Editor effort | Time to locate/resolve issues if measured; do not invent time-saving percentages. |

Absolute quality thresholds for WER, DER, latency, cost and review precision/recall are not supplied. Establish targets after a baseline and agree them for production. The explicit hackathon objective is zero unflagged hallucinated-text occurrences in its held-out tests; passing a small sample does not guarantee zero errors on all future content.

**14. Acceptance test matrix**

| Test | Required evidence |
| --- | --- |
| Clean Bengali dialogue | Transcription, attribution, timing and all required exports are generated from audio. |
| Bengali with inline English | English words are preserved accurately under the documented mixed-script policy. |
| Silence and instrumental music | Unsupported dialogue is absent or visibly flagged with corresponding QC records. |
| Dialogue beneath music | Actual speech remains represented; music detection does not erase it. |
| Whispering/noisy speech | Uncertain text and potentially missed speech receive actionable flags. |
| Alternating speakers | Speaker IDs follow voices without unexplained swaps. |
| Returning speaker after a long gap | Identity remains consistent across scene/chunk boundaries. |
| Overlapping or off-screen speech | Overlap is represented or flagged; off-screen speech is not discarded. |
| Chunk boundary | No missing or duplicated words; global timestamps and speaker IDs are reconciled. |
| Rapid speech and camera cuts | Cue constraints are enforced or unresolved conflicts are accurately reported. |
| Meaningful sound event | A supported, correctly timed Bengali sound caption appears without invented details. |
| Long English/Hindi translation | Each language is independently resegmented/validated and remains source-linked. |
| Names, numbers and negation | Meaning survives recognition and translation or uncertainty is raised. |
| Optional name inference | Evidence-backed suggestion is visible; an addressed name is not blindly assigned to its speaker. |
| Optional name/cue edit | Original output remains accessible; related translations and QC are refreshed as needed. |
| Corrupt/missing-audio input | Clear failure with no fabricated successful outputs. |
| Provider timeout/QC failure | Bounded retries and an honest partial/failed/unchecked status. |
| Worker restart or page refresh | Job is recoverable; successful work is not repeated unnecessarily. |
| Export/playback | Bengali WebVTT and both SRT tracks parse; the deployed player renders synchronized, legible text. |
| Access and secrets | Another demo session cannot fetch private job assets; browser/repo outputs contain no credentials. |
| Fresh live upload | A new clip traverses the actual deployed pipeline. Cached examples are explicitly identified. |

Flags are diagnostic evidence, not a substitute for meeting every quality requirement. For example, a flagged shot-crossing cue remains a presentation issue until corrected. Likewise, flagging every cue is not an adequate review-queue solution.

**15. Development and deployment prerequisites**

Before selecting the stack, verify:

- Runtime access for media decoding/encoding, background processing and sufficient temporary storage.
- A primary ASR path that supports Bengali and code-switching, stable diarization, a compatible alignment method, sound analysis, shot detection and English/Hindi translation.
- Model availability, permissions/licences, dependency compatibility and authentication. Validate support through a real sample, not only a marketing feature list.
- Either adequate local/hosted inference hardware or funded API access with workable quotas, upload limits and timeouts. A GPU requirement depends on the selected models; none is assumed here.
- Persistent job/artefact storage, media playback support and a deployable backend that handles long jobs.
- Bengali/Devanagari fonts, caption parsers/serializers and a browser preview that displays the required scripts correctly.
- A small evaluation set covering the failure modes above and a source-control repository with reproducible setup instructions.

No model training from scratch is required by the brief. Resource-intensive training, multiple redundant providers and complex agent orchestration are not prerequisites for this MVP.

**16. Submission requirements**

| ID | Level | Requirement |
| --- | --- | --- |
| SUB-01 | B | Submit individually and solve PS2 end to end. |
| SUB-02 | B | Provide a live demo link judges can open and test, a public GitHub repository and an explanatory video under five minutes before the stated deadline. |
| SUB-03 | D | Verify the demo in a clean session, including uploads, outputs, permissions, playback and the deployed processing worker. Document any credentials judges need through the submission process. |
| SUB-04 | D | Include a README with setup, configuration, required credentials, pipeline explanation, run instructions, evaluation method/results, limitations and known unsupported cases. |
| SUB-05 | D | Pin dependencies and provide an environment-variable template with placeholders. Exclude secrets and avoid publishing supplied media unless authorised. |
| SUB-06 | D | Demonstrate automatic processing, stable speaker attribution, non-speech captions, English/Hindi tracks, a useful QC flag and exports. Identify manual review and cached examples honestly. |
| SUB-07 | D | Make AI's role clear in recognition, attribution, translation and acoustic analysis. Deterministic validation remains appropriate for formats, timing and access controls. |

The three PS2 auto-disqualifiers supplied by the organiser are a hand-corrected sample transcript shipped as the solution, unflagged hallucinated text over silence/music in the held-out set, and a demo that cannot run live.

**17. Decisions that remain open**

| Decision | Needed clarification |
| --- | --- |
| Caption profile | CPS, characters per line, line count, cue durations/gaps and Unicode counting conventions for Bengali, English and Hindi. |
| Shot policy | Confirm strict no-straddling interpretation, timing tolerance and treatment of dialogue spanning a cut. Until clarified, retain the stricter brief requirement. |
| Speech policy | Rules for unintelligible speech, overlap, code-switch script, dialect spelling, punctuation and speaker display. |
| Sound/lyrics policy | Required sound classes, labelling style and whether song lyrics and on-screen text are expected. |
| Evaluation | Any organiser WER/DER/timing/QC thresholds, matching rules, sample references and live processing limits. |
| Inputs | Full asset runtime/codecs/audio streams, allowed maximum uploads and expected held-out episode length. |
| Cast information | Whether character lists, actor-to-character mappings or other authorised naming references are available. |
| Compute and spending | Available CPU/GPU, provider credentials/credits, per-job cost ceiling and deployment capacity. |
| Sharing and retention | Permitted handling of supplied footage, demo access and acceptable persistence/provider use. |

Proceed with documented, configurable assumptions while questions are pending; do not claim unspecified organiser thresholds or accuracy guarantees.

**18. Further production requirements**

After the hackathon, establish these before describing the system as production-ready:

- Broader, independently annotated evaluation spanning speakers, accents, dialogue density, soundtracks, recording conditions and long runtimes; investigate performance by subgroup and condition.
- Calibrated QC thresholds and monitored drift, with regression gates for changes to models, prompts, profiles and preprocessing.
- Agreed quality and latency objectives, capacity/load tests, queue/backpressure behaviour, cost controls and representative long-run reliability tests.
- Tested backup/restore, job recovery, rollback, provider outages and operational alerting.
- Reviewed security, access control, media retention/deletion, data-provider arrangements and audit behaviour appropriate to the deployment.
- Versioned editorial profiles, reviewer training, reproducible exports and an explicit operational release process.
- Measurement of actual reviewer time saved and translation/caption quality before making business performance claims.

Cross-episode speaker memory, a full editing timeline, live-stream captioning, more languages, face recognition, dubbing, billing and enterprise administration are outside the stated hackathon MVP. Speaker naming is the optional enrichment already selected for this project.

**19. Completion criteria**

The hackathon MVP is complete when a new Bengali video passes through every mandatory stage; the original automated Bengali CC, English/Hindi subtitles and actionable QC report are available; attribution/timing/readability are checked; suspicious silence/music text is flagged; outputs work in the deployed preview and download correctly; and the three submission deliverables are ready. Failed mandatory stages, unresolved quality issues and review states must remain visible.

Completion of the pipeline is not a guarantee of broadcast acceptance. Release readiness is a separate decision based on the applicable profile, QC results and review.

**20. Reference notes**

The user's pasted Hoichoi PS2 brief and hackathon rules are the authoritative task scope. External technical references below were checked on 26 September 2026 and clarify the distinction between file syntax and editorial requirements; they do not impose Netflix requirements on Hoichoi.

1. [W3C WebVTT specification](https://www.w3.org/TR/webvtt1/) — file format, cues and speaker voice annotations. The retrieved publication identifies itself as a Candidate Recommendation Draft.
2. [Netflix Timed Text Style Guide: General Requirements](https://partnerhelp.netflixstudios.com/hc/en-us/articles/215758617-Timed-Text-Style-Guide-General-Requirements) — an example of service-specific editorial rules with separate language, timing and file-type guidance. Do not copy its numeric limits into the hackathon as official values.
3. [Netflix Subtitle Timing Guidelines](https://partnerhelp.netflixstudios.com/hc/en-us/articles/360051554394-Timed-Text-Style-Guide-Subtitle-Timing-Guidelines) — permits some dialogue-related shot-crossing cases, illustrating why the stricter hackathon wording must take priority unless clarified.
