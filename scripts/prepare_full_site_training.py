"""Create an auditable SFT input from the admitted quality and motion pools.

This does not assign human-review metadata to historical rows. Reviewed full-site
examples are admitted separately after their real browser and reviewer evidence exists.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SOURCES = (
    ROOT / "data/quality_v3/train.jsonl",
    ROOT / "data/siteagent_motion_sft_v1.jsonl",
)
VALIDATION = ROOT / "data/quality_candidate/validation.jsonl"
OUTPUT = ROOT / "data/full_site_training/train.jsonl"
MANIFEST = ROOT / "data/full_site_training/manifest.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    rows: list[dict] = []
    source_summary = []
    families: set[str] = set()
    task_ids: set[str] = set()
    for source in SOURCES:
        source_rows = read_jsonl(source)
        for row in source_rows:
            family = str(row.get("family_id") or "")
            task = str(row.get("task_id") or "")
            if not family or not task or not row.get("messages"):
                raise ValueError(f"Missing family, task, or messages in {source}")
            if task in task_ids:
                raise ValueError(f"Duplicate task_id: {task}")
            task_ids.add(task)
            families.add(family)
            rows.append(row)
        source_summary.append({"path": str(source.relative_to(ROOT)), "sha256": sha256(source), "rows": len(source_rows)})
    heldout = read_jsonl(VALIDATION)
    heldout_families = {str(row.get("family_id")) for row in heldout}
    if families & heldout_families:
        raise ValueError(f"Train/validation family overlap: {sorted(families & heldout_families)[:5]}")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in rows), encoding="utf-8")
    manifest = {
        "status": "unreviewed_candidate_training_input",
        "output": str(OUTPUT.relative_to(ROOT)),
        "sha256": sha256(OUTPUT),
        "rows": len(rows),
        "families": len(families),
        "validation_path": str(VALIDATION.relative_to(ROOT)),
        "validation_sha256": sha256(VALIDATION),
        "validation_rows": len(heldout),
        "family_overlap": 0,
        "sources": source_summary,
        "human_visual_review": "not performed",
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
