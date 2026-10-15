"""Measure website-domain coverage and review provenance before adding training rows."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re

DOMAINS = (
    "ecommerce", "portfolio", "editorial", "arts", "civic", "events",
    "education", "hospitality", "healthcare", "dashboard", "saas", "other",
)


def read_rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def audit(train_path: Path, motion_path: Path | None = None) -> dict:
    rows = read_rows(train_path)
    domain_counts: Counter[str] = Counter()
    family_domains: dict[str, set[str]] = defaultdict(set)
    missing = Counter()
    visual_terms = Counter()
    for row in rows:
        messages = row.get("messages") or []
        user_text = "\n".join(str(m.get("content", "")) for m in messages if m.get("role") == "user")
        match = re.search(r"<business_type>\s*([^<]+)\s*</business_type>", user_text, re.I)
        domain = match.group(1).strip().lower() if match else "untagged"
        domain_counts[domain] += 1
        family = str(row.get("family_id") or row.get("source_task_id") or row.get("task_id") or "unknown")
        family_domains[family].add(domain)
        for field in ("source", "license", "validation", "visual_review"):
            if not row.get(field):
                missing[field] += 1
        for term in ("3d", "webgl", "three.js", "parallax", "scroll reveal", "text reveal"):
            if term in user_text.lower():
                visual_terms[term] += 1
    report = {
        "dataset": str(train_path.resolve()), "rows": len(rows),
        "family_count": len(family_domains), "business_type_counts": dict(sorted(domain_counts.items())),
        "business_type_family_counts": {
            domain: sum(domain in domains for domains in family_domains.values()) for domain in DOMAINS
        },
        "target_family_gaps_at_five": {
            domain: max(0, 5 - sum(domain in domains for domains in family_domains.values())) for domain in DOMAINS
        },
        "motion_and_3d_prompt_counts": dict(visual_terms),
        "missing_explicit_review_metadata": dict(missing),
        "motion_curriculum_rows": len(read_rows(motion_path)) if motion_path and motion_path.is_file() else None,
        "eligible_for_new_reviewed_training": all(missing[field] == 0 for field in ("source", "license", "validation", "visual_review")),
    }
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--train", type=Path, default=Path("data/quality_v3/train.jsonl"))
    parser.add_argument("--motion", type=Path, default=Path("data/siteagent_motion_sft_v1.jsonl"))
    parser.add_argument("--output", type=Path, default=Path("runs/p1_training_coverage.json"))
    args = parser.parse_args()
    result = audit(args.train, args.motion)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
