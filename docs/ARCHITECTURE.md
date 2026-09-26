# Architecture decisions

**One repository, one API, one worker.** The frontend and backend are independently buildable; the pipeline uses explicit stages and provider protocols. The work is sufficiently predictable that an autonomous multi-agent loop would add little to this setup.

**Persistent jobs.** PostgreSQL is configured in Compose; SQLite supports local development. The API commits job state before enqueueing. The worker atomically claims queued work, so a duplicate queue delivery cannot execute an already-running/completed job. A future transactional outbox is needed to close the database/queue crash window.

**Separate status dimensions.** Processing has `uploaded`, `queued`, `running`, `blocked`, `failed`, `partial` and `completed` states. QC has its own status; all exports remain original automatic drafts. A missing provider results in blocked/incomplete, never success.

**Typed evidence boundary.** Provider outputs are validated before downstream use. Words, speakers, audio evidence, shots, cues and issues share a global timeline. Raw transcripts are checkpointed separately from aligned transcripts. Translations maintain source-cue links.

**Checkpoints, not hidden canned results.** Run directories are derived from media checksum, pipeline version, provider revision and caption profile. Retries reuse valid checkpoints. Media extraction is reusable for the same upload. Configuration changes invalidate run checkpoints; provider revision bumps are required for model/prompt behaviour changes.

**QC is inspectable.** The starter's hallucination detector is a heuristic check of word intervals against independent speech intervals. It does not establish spoken-word correctness; speech detectors can miss quiet dialogue. Unsupported words are flagged and their uncertainty is propagated to translations. Speech intervals without enough words receive omission flags. No text is silently removed by this QC layer.

**Mechanical captioning first.** The initial grouper uses word, speaker, punctuation, duration and shot information. A word spanning a shot cut, rapid speech or a long speaker label may still violate the profile and will be flagged. Implement constrained cue optimization after real alignment data is available.

**Scoped demo access.** Each upload receives a random capability token; only its hash is stored. The browser uses a bearer token for API requests and an HTTP-only same-origin cookie for native video/track requests. There is no public job listing. This is a limited demo access model; broader production use needs account-level authorization, expiry/rotation, retention and abuse controls.

**No premature infrastructure claims.** Docker configuration is provided but needs to be run on the target machine. The source tests validate deterministic behaviour, not model accuracy, PostgreSQL deployment, Redis durability or production capacity.
