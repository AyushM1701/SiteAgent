"""
Builds the sealed final benchmark and development benchmark splits.

1. Sealed Final Benchmark (153 tasks):
   - Canonical held-out benchmark derived from react_ts_css_eval_set_combined.jsonl
   - Enriched with stable task_id (bench_final_001..bench_final_153), family_id, and symbol
   - Sealed with cryptographic SHA-256 manifest: data/eval/sealed_final_benchmark_manifest.json

2. Development Benchmark (150 tasks):
   - Daily development benchmark derived from star_task_bank.jsonl
   - Enriched with dev_task_001..dev_task_150, dev_family_*, category, check, test_code
   - Strictly held out and disjoint from the sealed benchmark across all 6 checks
"""

import datetime
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Tuple

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from training.leakage_guard import (
    extract_symbols,
    audit_dataset_against_benchmark,
    SEALED_BENCHMARK_PATH,
    SEALED_MANIFEST_PATH,
    DEV_BENCHMARK_PATH,
    LEGACY_BENCHMARK_PATH,
)


def derive_component_symbol(prompt: str) -> str:
    """Extract the primary component symbol or hook name from the prompt."""
    # Look for backtick component name
    bt_matches = re.findall(r"`([A-Za-z0-9_]+)`", prompt)
    for m in bt_matches:
        if m.startswith("use") or (m[0].isupper() and not m.startswith("CSS")):
            return m
    # Look for PascalCase words
    pascal = re.findall(r"\b[A-Z][a-zA-Z0-9]+(?:[A-Z][a-z0-9]+)+\b", prompt)
    if pascal:
        return pascal[0]
    return "Component"


def build_sealed_benchmark() -> Tuple[Path, Path]:
    """Create data/eval/sealed_final_benchmark.jsonl and its manifest."""
    source_file = LEGACY_BENCHMARK_PATH
    if not source_file.exists():
        raise FileNotFoundError(f"Source benchmark not found: {source_file}")

    target_file = SEALED_BENCHMARK_PATH
    target_file.parent.mkdir(parents=True, exist_ok=True)

    items = []
    task_hashes = {}

    with open(source_file, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            task_id = f"bench_final_{idx:03d}"
            symbol = derive_component_symbol(row["prompt"])
            family_id = f"family_{symbol.lower()}"

            entry = {
                "task_id": task_id,
                "family_id": family_id,
                "symbol": symbol,
                "check": row.get("check", "tsc_and_render"),
                "prompt": row["prompt"].strip(),
                "test_code": row.get("test_code", ""),
            }
            items.append(entry)
            p_hash = hashlib.sha256(entry["prompt"].encode("utf-8")).hexdigest()
            task_hashes[task_id] = p_hash

    # Write sealed benchmark lines
    with open(target_file, "w", encoding="utf-8", newline="\n") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    # Compute SHA-256
    sha = hashlib.sha256()
    with open(target_file, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            sha.update(chunk)
    file_hash = sha.hexdigest()

    manifest = {
        "status": "sealed",
        "benchmark_file": "data/eval/sealed_final_benchmark.jsonl",
        "task_count": len(items),
        "sha256": file_hash,
        "sealed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "purpose": "Authoritative held-out benchmark evaluated strictly at major checkpoints.",
        "leakage_checks_enforced": [
            "exact_prompt_matching",
            "normalized_matching",
            "symbol_overlap",
            "token_similarity",
            "family_level_holdout",
            "semantic_similarity_checks",
        ],
        "task_hashes": task_hashes,
    }

    with open(SEALED_MANIFEST_PATH, "w", encoding="utf-8", newline="\n") as f:
        json.dump(manifest, f, indent=2)

    print(f"Created sealed final benchmark: {target_file} ({len(items)} tasks, SHA: {file_hash[:12]}...)")
    print(f"Created manifest: {SEALED_MANIFEST_PATH}")
    return target_file, SEALED_MANIFEST_PATH


def build_dev_benchmark() -> Path:
    """Create data/eval/dev_benchmark.jsonl from clean non-leaking tasks."""
    star_file = BASE_DIR / "data" / "star_task_bank.jsonl"
    web_file = BASE_DIR / "data" / "website_task_bank.jsonl"
    if not star_file.exists():
        raise FileNotFoundError(f"Star task bank not found: {star_file}")

    target_file = DEV_BENCHMARK_PATH
    target_file.parent.mkdir(parents=True, exist_ok=True)

    # Load sealed benchmark prompts to filter out any semantic overlaps
    from training.leakage_guard import (
        compute_semantic_similarity,
        compute_token_jaccard,
        extract_symbols,
    )
    sealed = []
    if SEALED_BENCHMARK_PATH.exists():
        sealed = [json.loads(l) for l in open(SEALED_BENCHMARK_PATH, encoding="utf-8") if l.strip()]

    items = []
    skipped_count = 0
    with open(star_file, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            prompt = row["prompt"].strip()

            # Filter against sealed benchmark if semantic similarity is high
            is_leaky = any(
                compute_semantic_similarity(prompt, s["prompt"]) >= 0.58
                or compute_token_jaccard(prompt, s["prompt"]) >= 0.45
                for s in sealed
            )
            if is_leaky:
                skipped_count += 1
                continue

            symbol = row.get("symbol") or derive_component_symbol(prompt)
            family_id = f"dev_family_{symbol.lower()}"
            task_id = f"dev_task_{len(items) + 1:03d}"

            items.append({
                "task_id": task_id,
                "family_id": family_id,
                "symbol": symbol,
                "category": row.get("category", "general"),
                "check": row.get("check", "tsc_render_interact"),
                "prompt": prompt,
                "test_code": row.get("test_code", ""),
            })

    # Backfill with clean tasks from website_task_bank if needed to reach 150 tasks
    if len(items) < 150 and web_file.exists():
        with open(web_file, "r", encoding="utf-8") as f:
            for line in f:
                if len(items) >= 150:
                    break
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                prompt = row["prompt"].strip()
                if any(
                    compute_semantic_similarity(prompt, s["prompt"]) >= 0.50
                    or compute_token_jaccard(prompt, s["prompt"]) >= 0.35
                    for s in sealed
                ):
                    continue
                symbol = row.get("symbol") or derive_component_symbol(prompt)
                task_id = f"dev_task_{len(items) + 1:03d}"
                items.append({
                    "task_id": task_id,
                    "family_id": f"dev_family_{symbol.lower()}",
                    "symbol": symbol,
                    "category": row.get("category", "layout"),
                    "check": row.get("check", "tsc_and_render"),
                    "prompt": prompt,
                    "test_code": row.get("test_code", ""),
                })

    with open(target_file, "w", encoding="utf-8", newline="\n") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"Created development benchmark: {target_file} ({len(items)} tasks, filtered {skipped_count} near-leaks)")
    return target_file


def main():
    build_sealed_benchmark()
    dev_path = build_dev_benchmark()

    # Audit dev benchmark against sealed benchmark across all 6 checks
    print("\nAuditing Development Benchmark against Sealed Final Benchmark...")
    report = audit_dataset_against_benchmark(
        dataset_path=str(dev_path),
        benchmark_path=str(SEALED_BENCHMARK_PATH),
        manifest_path=str(SEALED_MANIFEST_PATH),
    )
    print(f"Dev Benchmark Disjointness: {'PASSED (0 leaks)' if report.is_clean else 'FAILED'}")
    print(f"Total dev tasks: {report.total_candidate_samples}")
    print(f"Peak token similarity: {report.peak_token_similarity:.3f} (threshold: {report.token_threshold})")
    print(f"Peak semantic similarity: {report.peak_semantic_similarity:.3f} (threshold: {report.semantic_threshold})")
    if not report.is_clean:
        print(f"Violations detected: {report.breakdown}")
        sys.exit(1)


if __name__ == "__main__":
    from typing import Tuple
    main()
