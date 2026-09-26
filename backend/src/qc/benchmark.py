"""Benchmark and audit utilities for held-out evaluation and review queue validation.

These tools verify that:
1. No hallucinated subtitle text over silence or music remains unflagged.
2. The QC report's review queue matches the actual ground-truth error list,
   verifying detection recall, ranking order, and evidence attribution.
"""

from typing import Any

from core.contracts import AudioEvidence, CaptionProfile, Cue, Issue, QCReport, Transcript
from qc.evaluation import covered_ms


def audit_unflagged_hallucinations(
    tracks: dict[str, list[Cue]],
    transcript: Transcript,
    audio: AudioEvidence,
    report: QCReport,
    profile: CaptionProfile | None = None,
) -> list[dict[str, Any]]:
    """Audit all subtitle cues directly against independent acoustic evidence.

    Returns a list of unflagged hallucinated cues. For a compliant pipeline,
    this list must be strictly empty (zero unflagged occurrences).
    """
    profile = profile or CaptionProfile()
    if not audio.complete or not audio.independent_of_asr:
        raise ValueError("Hallucination audit requires complete independent acoustic evidence")
    words = {w.id: w for w in transcript.words}
    flagged_cue_ids = {
        cue_id
        for issue in report.issues
        if issue.code == "SUSPECTED_HALLUCINATION"
        for cue_id in issue.cue_ids
    }

    unflagged: list[dict[str, Any]] = []

    for cue in tracks.get("bn", []):
        if cue.kind != "speech":
            continue

        source_words = [words[wid] for wid in cue.source_word_ids if wid in words]
        if not source_words:
            continue

        unsupported_words = [
            w
            for w in source_words
            if (w.end_ms > w.start_ms)
            and (covered_ms(w, audio.speech) / (w.end_ms - w.start_ms) < profile.min_speech_support)
        ]

        if unsupported_words and cue.id not in flagged_cue_ids:
            unflagged.append(
                {
                    "cue_id": cue.id,
                    "text": cue.text,
                    "start_ms": cue.start_ms,
                    "end_ms": cue.end_ms,
                    "unsupported_word_ids": [w.id for w in unsupported_words],
                    "speech_coverage": [
                        round(covered_ms(w, audio.speech) / (w.end_ms - w.start_ms), 3)
                        for w in unsupported_words
                    ],
                    "music_overlap_ms": sum(covered_ms(w, audio.music) for w in unsupported_words),
                }
            )

    return unflagged


def compare_review_queue(
    report: QCReport,
    ground_truth_errors: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compare the QC report's review queue against the actual ground-truth error list.

    Evaluates:
    - True positives (matched actual errors)
    - False negatives (missed errors)
    - False positives (unmatched flags)
    - Severity ranking consistency (critical -> high -> medium)
    """
    matched_gt: list[dict[str, Any]] = []
    missed_gt: list[dict[str, Any]] = []
    matched_issues: set[str] = set()

    for gt in ground_truth_errors:
        code = gt["code"]
        cue_id = gt.get("cue_id")
        start_ms = gt.get("start_ms")
        end_ms = gt.get("end_ms")

        # Find matching issue in QC report
        found: Issue | None = None
        for issue in report.issues:
            if issue.code != code or issue.id in matched_issues:
                continue

            if cue_id:
                if cue_id in issue.cue_ids:
                    found = issue
                    break
            elif start_ms is not None and end_ms is not None and end_ms > start_ms:
                overlap = max(0, min(end_ms, issue.end_ms) - max(start_ms, issue.start_ms))
                if overlap / (end_ms - start_ms) >= 0.5:
                    found = issue
                    break

        if found:
            matched_gt.append({"ground_truth": gt, "matched_issue_id": found.id, "issue": found})
            matched_issues.add(found.id)
        else:
            missed_gt.append(gt)

    unmatched_issues = [issue for issue in report.issues if issue.id not in matched_issues]

    # Verify severity ranking
    severity_order = {"critical": 0, "high": 1, "medium": 2}
    severities = [severity_order[issue.severity] for issue in report.issues]
    ranking_order_valid = all(
        severities[i] <= severities[i + 1] for i in range(len(severities) - 1)
    )

    total_gt = len(ground_truth_errors)
    recall = len(matched_gt) / total_gt if total_gt > 0 else 1.0
    precision = (
        len(matched_gt) / (len(matched_gt) + len(unmatched_issues))
        if (len(matched_gt) + len(unmatched_issues)) > 0
        else 1.0
    )

    return {
        "total_ground_truth_errors": total_gt,
        "matched_count": len(matched_gt),
        "missed_count": len(missed_gt),
        "unmatched_issues_count": len(unmatched_issues),
        "recall": round(recall, 3),
        "precision": round(precision, 3),
        "ranking_order_valid": ranking_order_valid,
        "missed_errors": missed_gt,
        "matched_errors": matched_gt,
        "unmatched_issues": unmatched_issues,
    }
