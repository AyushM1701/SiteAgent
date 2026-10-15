"""Admission checks for newly authored, human-reviewed full-site trajectories."""

from __future__ import annotations

from pathlib import Path
from typing import Any
import hashlib

from evaluation.human_visual_review import RUBRIC_AXES


def validate_reviewed_site_rows(train: list[dict[str, Any]], heldout: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    train_families = {str(row.get("family_id")) for row in train}
    heldout_families = {str(row.get("family_id")) for row in heldout}
    if train_families & heldout_families:
        errors.append("train and held-out rows share family IDs")
    for split, rows in (("train", train), ("heldout", heldout)):
        for row in rows:
            task = str(row.get("task_id") or "unknown")
            prefix = f"{split}/{task}"
            if not row.get("family_id") or not row.get("domain"):
                errors.append(f"{prefix}: family_id and domain are required")
            if not row.get("source") or row.get("license") in (None, "", "unknown"):
                errors.append(f"{prefix}: source and license are required")
            source_files = row.get('source_files') or {}
            if not source_files:
                errors.append(f'{prefix}: reviewed source fingerprints are required')
            else:
                source_root = Path(str(row.get('source') or ''))
                for filename, fingerprint in source_files.items():
                    file = source_root / filename
                    if not file.is_file() or hashlib.sha256(file.read_bytes()).hexdigest() != fingerprint:
                        errors.append(f'{prefix}: source fingerprint mismatch for {filename}')
            validation = row.get("validation") or {}
            for gate in ("typecheck", "build", "runtime", "interaction"):
                if validation.get(gate) is not True:
                    errors.append(f"{prefix}: {gate} validation must pass")
            review = row.get("visual_review") or {}
            if not review.get("reviewer_id"):
                errors.append(f"{prefix}: named visual reviewer is required")
            review_form = review.get('review_form')
            review_hash = review.get('review_form_sha256')
            if not review_form or not review_hash or not Path(str(review_form)).is_file() or hashlib.sha256(Path(str(review_form)).read_bytes()).hexdigest() != review_hash:
                errors.append(f'{prefix}: human review form fingerprint mismatch')
            for axis in RUBRIC_AXES:
                score = (review.get("rubric_scores") or {}).get(axis)
                if isinstance(score, bool) or not isinstance(score, (int, float)) or not 1 <= score <= 5:
                    errors.append(f"{prefix}: visual review lacks {axis} score")
            evidence = row.get("browser_evidence") or {}
            for mode in ("desktop", "mobile", "reduced_motion"):
                capture = evidence.get(mode) or {}
                for artifact in ("screenshot", "scroll_video"):
                    path = capture.get(artifact)
                    if not path or not Path(str(path)).is_file():
                        errors.append(f"{prefix}: {mode} {artifact} evidence is missing")
                    elif capture.get(artifact + '_sha256') != hashlib.sha256(Path(str(path)).read_bytes()).hexdigest():
                        errors.append(f'{prefix}: {mode} {artifact} fingerprint mismatch')
            if row.get("category") == "repair" and not row.get("repair_diagnostics"):
                errors.append(f"{prefix}: repair example lacks compiler/DOM/interaction diagnostics")
    return errors


def require_reviewed_training_examples(rows: list[dict[str, Any]], heldout: list[dict[str, Any]]) -> dict:
    """Require varied approved examples before the next full training run."""
    reviewed = [row for row in rows if row.get('visual_review')]
    errors = validate_reviewed_site_rows(reviewed, heldout=[])
    families = {row.get('family_id') for row in reviewed}
    if len(families) < 3 or len({row.get('domain') for row in reviewed}) < 3:
        errors.append('training requires reviewed examples from at least three site families and domains')
    if families & {row.get('family_id') for row in heldout}:
        errors.append('reviewed training families overlap validation')
    for family in families:
        categories = {row.get('category') for row in reviewed if row.get('family_id') == family}
        if not {'full_site', 'repair'}.issubset(categories):
            errors.append(f'{family}: full-site and repair examples are both required')
    for row in reviewed:
        scores = list((row.get('visual_review', {}).get('rubric_scores') or {}).values())
        if not scores or not all(isinstance(v, (int, float)) and not isinstance(v, bool) and 3 <= v <= 5 for v in scores) or sum(scores) / len(scores) < 4:
            errors.append(f'{row.get("task_id")}: approved visual scores must be >=3 with mean >=4')
    if errors:
        raise ValueError('Reviewed training gate failed: ' + '; '.join(errors))
    return {'rows': len(reviewed), 'families': len(families), 'domains': len({r['domain'] for r in reviewed})}
