# Next implementation steps

1. Run the starter and confirm API, Redis, worker and frontend connectivity.
2. Establish the actual inference budget: available GPU/VRAM or funded API access, and permitted external processing of supplied footage.
3. Select and implement one Bengali ASR + diarization path and one compatible alignment path; verify code-switched speech immediately.
4. Connect independent speech/music/sound analysis and shot detection; inspect evidence completeness.
5. Connect English/Hindi translation while preserving source links and timing.
6. Run the full pipeline on a short real clip; inspect the original outputs and QC queue.
7. Calibrate unsupported-word and missed-speech checks, then improve cue segmentation. Obtain the organiser's numeric caption profile.
8. Evaluate on a reserved clip/video and test returning speakers across long gaps. Report measured errors and false alarms honestly.
9. Add naming only if it does not compromise core pipeline reliability. Implement review corrections with separate revisions if time allows.
10. Deploy the working inference path, test a fresh upload, publish the public repository and record the under-five-minute submission video.

The current starter is not ready for hackathon submission: inference integration and held-out validation are still outstanding. Do not spend the remaining build time adding billing, enterprise administration or an elaborate editing timeline.
