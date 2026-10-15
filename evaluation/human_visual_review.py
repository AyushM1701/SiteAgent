"""Fail-closed human visual review contract for model promotion."""

from __future__ import annotations

from typing import Any
from pathlib import Path
import re
from collections import defaultdict
import hashlib

RUBRIC_AXES = (
    "layout", "hierarchy", "typography", "content_specificity",
    "imagery_assets", "motion_timing", "mobile_composition",
)
CAPTURE_MODES = ("desktop", "mobile", "reduced_motion")


def validate_human_review(report: dict[str, Any], adapter_sha256: str, min_sites: int = 30) -> list[str]:
    errors: list[str] = []
    if report.get("review_type") != "blinded_pairwise_human":
        errors.append("review_type must be blinded_pairwise_human")
    if not adapter_sha256 or adapter_sha256 in {"none", "unknown"} or report.get("candidate_adapter_sha256") != adapter_sha256:
        errors.append("reviewed adapter fingerprint does not match the live benchmark")
    rows = report.get("site_reviews") or []
    by_task: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_task[str(row.get("task_id") or "")].append(row)
    if len(by_task) < min_sites:
        errors.append(f"at least {min_sites} distinct sites are required")
    if len({row.get("domain") for row in rows if row.get("domain")}) < 12:
        errors.append("reviews must cover 12 website domains")
    for task, task_rows in by_task.items():
        if len({row.get("reviewer_id") for row in task_rows if row.get("reviewer_id")}) < 2:
            errors.append(f"{task or 'unknown'}: two independent reviewers are required")
        if len({row.get("domain") for row in task_rows}) != 1:
            errors.append(f"{task or 'unknown'}: reviewers disagree on the domain")
        if len({row.get("candidate_label") for row in task_rows}) != 1:
            errors.append(f"{task or 'unknown'}: reviewers have inconsistent A/B mapping")
    if not re.fullmatch(r"[0-9a-f]{64}", str(report.get("blinding_manifest_sha256") or "")):
        errors.append("blinding manifest hash is required")
    candidate_wins = sum(row.get("pairwise_winner") == row.get("candidate_label") for row in rows)
    baseline_wins = sum(row.get("pairwise_winner") in {"A", "B"} and row.get("pairwise_winner") != row.get("candidate_label") for row in rows)
    if candidate_wins <= baseline_wins:
        errors.append("candidate did not win more blinded comparisons than baseline")
    seen_paths: dict[str, str] = {}
    screenshot_hashes: dict[tuple[str, str], str] = {}
    for row in rows:
        task = row.get("task_id", "unknown")
        if not row.get("reviewer_id") or row.get("candidate_label") not in {"A", "B"}:
            errors.append(f"{task}: reviewer and blinded candidate label are required")
        if row.get("pairwise_winner") not in {"A", "B", "tie"}:
            errors.append(f"{task}: pairwise winner is missing")
        scores = row.get("rubric_scores") or {}
        for label in ("A", "B"):
            for axis in RUBRIC_AXES:
                score = (scores.get(label) or {}).get(axis)
                if not isinstance(score, (int, float)) or isinstance(score, bool) or not 1 <= score <= 5:
                    errors.append(f"{task}: {label} {axis} must have a 1–5 human score")
        evidence = row.get("evidence") or {}
        for label in ("A", "B"):
            for mode in ("desktop", "mobile", "reduced_motion"):
                capture = (evidence.get(label) or {}).get(mode) or {}
                for artifact in ("screenshot", "scroll_video"):
                    path = capture.get(artifact)
                    if not path or not Path(str(path)).is_file():
                        errors.append(f"{task}: {label} {mode} {artifact} file is missing")
                    else:
                        resolved = str(Path(str(path)).resolve())
                        identity = f"{task}/{label}/{mode}/{artifact}"
                        if resolved in seen_paths and seen_paths[resolved] != identity:
                            errors.append(f"{task}: evidence file is reused across distinct captures")
                        seen_paths[resolved] = identity
                        if artifact == "screenshot":
                            screenshot_hashes[(task, f"{label}/{mode}")] = hashlib.sha256(Path(resolved).read_bytes()).hexdigest()
    for task in by_task:
        for mode in CAPTURE_MODES:
            a = screenshot_hashes.get((task, f"A/{mode}"))
            b = screenshot_hashes.get((task, f"B/{mode}"))
            if a and b and a == b:
                errors.append(f"{task}: A and B {mode} screenshots are identical")
    return errors
