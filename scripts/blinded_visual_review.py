"""Create an A/B capture package and assemble actual reviewer responses.

Inputs are browser captures from scripts/capture_visual_review.py. Review forms
contain no model identity. A private map is kept outside the review package.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import secrets
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from evaluation.human_visual_review import RUBRIC_AXES, validate_human_review

HOLDOUT = ROOT / "data/eval/visual_holdout_v1.jsonl"
CAPTURE_MODES = ("desktop", "mobile", "reduced_motion")


def read_cases() -> list[dict]:
    return [json.loads(line) for line in HOLDOUT.read_text(encoding="utf-8").splitlines() if line.strip()]


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_capture(source_dir: Path) -> dict:
    info = json.loads((source_dir / "evidence.json").read_text(encoding="utf-8"))
    captures = info.get("captures") or {}
    for mode in CAPTURE_MODES:
        for artifact in ("screenshot", "scroll_video"):
            if not Path(str((captures.get(mode) or {}).get(artifact, ""))).is_file():
                raise ValueError(f"Missing {mode} {artifact} in {source_dir}")
    return captures


def prepare(source_root: Path, package_root: Path, private_mapping: Path, reviewers: list[str]) -> None:
    if package_root.exists() or private_mapping.exists():
        raise FileExistsError("Review package or private mapping already exists; choose a new destination")
    cases = read_cases()
    if len(cases) != 30 or len({case["domain"] for case in cases}) != 12:
        raise ValueError("Visual holdout must contain 30 distinct cases across 12 domains")
    package_root.mkdir(parents=True)
    private_mapping.parent.mkdir(parents=True, exist_ok=True)
    mapping = {"holdout_sha256": file_sha(HOLDOUT), "cases": {}}
    public_rows = []
    for case in cases:
        task = case["task_id"]
        sources = {role: source_capture(source_root / task / role) for role in ("candidate", "baseline")}
        candidate_label = "A" if secrets.randbits(1) == 0 else "B"
        mapping["cases"][task] = {"candidate_label": candidate_label, "domain": case["domain"]}
        for label, role in ((candidate_label, "candidate"), ("B" if candidate_label == "A" else "A", "baseline")):
            dest = package_root / task / label
            dest.mkdir(parents=True)
            for mode in CAPTURE_MODES:
                for artifact in ("screenshot", "scroll_video"):
                    original = Path(sources[role][mode][artifact])
                    shutil.copy2(original, dest / f"{mode}_{artifact}{original.suffix}")
        public_rows.append({"task_id": task, "domain": case["domain"], "prompt": case["prompt"]})
    (package_root / "cases.json").write_text(json.dumps(public_rows, indent=2) + "\n", encoding="utf-8")
    private_mapping.write_text(json.dumps(mapping, indent=2) + "\n", encoding="utf-8")
    fields = ["task_id", "domain", "pairwise_winner"] + [f"{label}_{axis}" for label in ("A", "B") for axis in RUBRIC_AXES] + ["review_notes"]
    for reviewer in reviewers:
        form = package_root / f"review_form_{reviewer}.csv"
        with form.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows({"task_id": row["task_id"], "domain": row["domain"]} for row in public_rows)
    print(json.dumps({"public_package": str(package_root), "private_mapping": str(private_mapping), "sites": len(cases), "reviewers": reviewers}, indent=2))


def assemble(package_root: Path, private_mapping: Path, adapter_sha: str, forms: list[Path], report_path: Path) -> None:
    mapping = json.loads(private_mapping.read_text(encoding="utf-8"))
    site_reviews = []
    for form in forms:
        reviewer = form.stem.removeprefix("review_form_")
        with form.open(encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                task = row["task_id"]
                if task not in mapping["cases"]:
                    raise ValueError(f"Unknown review task {task}")
                scores = {label: {axis: int(row[f"{label}_{axis}"]) for axis in RUBRIC_AXES} for label in ("A", "B")}
                evidence = {}
                for label in ("A", "B"):
                    evidence[label] = {}
                    for mode in CAPTURE_MODES:
                        side = package_root / task / label
                        evidence[label][mode] = {
                            artifact: str(next(side.glob(f"{mode}_{artifact}.*")).resolve())
                            for artifact in ("screenshot", "scroll_video")
                        }
                site_reviews.append({
                    "task_id": task, "domain": mapping["cases"][task]["domain"],
                    "reviewer_id": reviewer, "candidate_label": mapping["cases"][task]["candidate_label"],
                    "pairwise_winner": row["pairwise_winner"], "rubric_scores": scores,
                    "review_notes": row.get("review_notes", ""), "evidence": evidence,
                })
    report = {
        "review_type": "blinded_pairwise_human", "candidate_adapter_sha256": adapter_sha,
        "blinding_manifest_sha256": file_sha(private_mapping), "holdout_sha256": mapping["holdout_sha256"],
        "site_reviews": site_reviews,
    }
    errors = validate_human_review(report, adapter_sha)
    if errors:
        raise ValueError("Review incomplete or failed: " + "; ".join(errors[:12]))
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Validated human review report: {report_path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("source_root", type=Path)
    p.add_argument("package_root", type=Path)
    p.add_argument("private_mapping", type=Path)
    p.add_argument("--reviewer", action="append", required=True)
    a = sub.add_parser("assemble")
    a.add_argument("package_root", type=Path)
    a.add_argument("private_mapping", type=Path)
    a.add_argument("adapter_sha")
    a.add_argument("report_path", type=Path)
    a.add_argument("forms", nargs="+", type=Path)
    args = parser.parse_args()
    if args.command == "prepare":
        if len(set(args.reviewer)) < 2:
            raise ValueError("Two distinct reviewers are required")
        prepare(args.source_root, args.package_root, args.private_mapping, args.reviewer)
    else:
        assemble(args.package_root, args.private_mapping, args.adapter_sha, args.forms, args.report_path)


if __name__ == "__main__":
    main()
