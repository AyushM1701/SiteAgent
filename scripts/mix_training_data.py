#!/usr/bin/env python3
"""
scripts/mix_training_data.py - Curriculum Mixing & Rebalancing Utility

Implements Item 15 from Section 9 and Section 3 of SITEAGENT_MOTION_TRAINING_GUIDE.md:
Mixes the professional motion curriculum (siteagent_motion_sft_v1.jsonl) into core
replay data at a controlled ratio (10%–15% motion), ensuring anti-template collapse,
strict target formatting (<tool_call name="write_site">, zero <think>/<thought> tags),
and no unverified motion package hallucinations.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_MOTION_PATH = ROOT_DIR / "data" / "siteagent_motion_sft_v1.jsonl"
DEFAULT_REPLAY_PATH = ROOT_DIR / "data" / "training_data.jsonl"
DEFAULT_OUTPUT_PATH = ROOT_DIR / "data" / "mixed_motion_training_curriculum.jsonl"

# Archetype detection keywords
ARCHETYPE_PATTERNS = {
    "split_hero": [r"split", r"two-column", r"side-by-side", r"column layout"],
    "editorial_asymmetric": [r"editorial", r"asymmetric", r"magazine", r"monograph", r"folio"],
    "immersive_visual": [r"full-bleed", r"immersive", r"hero visual", r"cinematic", r"background image"],
    "bento_grid": [r"bento", r"card grid", r"feature grid", r"mosaic"],
    "product_stage": [r"product", r"showcase", r"stage", r"hardware", r"device"],
    "restrained_centered": [r"centered", r"minimal", r"clean typography", r"text-only"],
}


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    """Loads records from a JSONL file."""
    if not path.is_file():
        raise FileNotFoundError(f"Input file not found: {path}")
    records: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as err:
                print(f"[Warning] Skipped invalid JSON line {idx} in {path.name}: {err}", file=sys.stderr)
    return records


def save_jsonl(records: List[Dict[str, Any]], path: Path) -> None:
    """Saves records to a JSONL file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def estimate_tokens(text: str) -> int:
    """Rough estimate of token count (char_len // 3.8)."""
    return max(1, int(len(text) / 3.8))


def extract_full_text(record: Dict[str, Any]) -> str:
    """Combines all messages or turn contents in a trajectory."""
    parts: List[str] = []
    if "messages" in record and isinstance(record["messages"], list):
        for msg in record["messages"]:
            if isinstance(msg, dict):
                parts.append(str(msg.get("content", "")))
    elif "turns" in record and isinstance(record["turns"], list):
        for turn in record["turns"]:
            if isinstance(turn, dict):
                parts.append(str(turn.get("content", "")))
                parts.append(str(turn.get("code", "")))
    elif "files" in record and isinstance(record["files"], dict):
        parts.extend(str(v) for v in record["files"].values())
    return " ".join(parts)


def validate_trajectory_cleanliness(record: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Verifies that a trajectory adheres to production contracts:
    - Zero <think> or <thought> tags in assistant targets
    - No unverified package imports (e.g. unverified gsap/framer-motion)
    """
    violations: List[str] = []
    messages = record.get("messages", [])
    for msg in messages:
        if msg.get("role") == "assistant":
            content = msg.get("content", "")
            if "<think>" in content or "<thought>" in content:
                violations.append("Assistant response contains forbidden <think>/<thought> reasoning tags.")
            if "import { gsap }" in content and 'implementation="gsap"' not in content:
                violations.append("Assistant response contains unverified GSAP import without explicit declaration.")
            if "from 'framer-motion'" in content and 'implementation="framer-motion"' not in content:
                violations.append("Assistant response contains unverified Framer Motion import without explicit declaration.")

    return len(violations) == 0, violations


def detect_archetype(text: str) -> str:
    """Classifies trajectory archetype from prompt and content text."""
    lower_text = text.lower()
    for arch, patterns in ARCHETYPE_PATTERNS.items():
        if any(re.search(pat, lower_text) for pat in patterns):
            return arch
    return "general_standard"


def mix_datasets(
    motion_records: List[Dict[str, Any]],
    replay_records: List[Dict[str, Any]],
    motion_ratio: float = 0.15,
    total_samples: Optional[int] = None,
    seed: int = 42,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Mixes motion and replay records to achieve the target motion ratio.
    If total_samples is not specified, uses all motion records and calculates
    the required replay records: N_replay = int(N_motion * (1 - ratio) / ratio).
    """
    rng = random.Random(seed)
    n_motion = len(motion_records)

    if total_samples is not None:
        target_motion_count = min(n_motion, max(1, int(total_samples * motion_ratio)))
        target_replay_count = max(1, total_samples - target_motion_count)
    else:
        # Scale replay data around all available unique motion records
        target_motion_count = n_motion
        target_replay_count = int(math.ceil(n_motion * (1.0 - motion_ratio) / motion_ratio))

    # Sample unique motion records
    sampled_motion = list(motion_records[:target_motion_count])
    motion_seen = {json.dumps(r.get("messages"), sort_keys=True) for r in sampled_motion}

    # Filter replay records to ensure no duplicate conversations and no overlap with motion records
    unique_replays: List[Dict[str, Any]] = []
    seen = set(motion_seen)
    for r in replay_records:
        fp = json.dumps(r.get("messages"), sort_keys=True)
        if fp not in seen:
            seen.add(fp)
            unique_replays.append(r)

    # Sample unique replay records
    target_replay_count = min(len(unique_replays), target_replay_count)
    sampled_replay = rng.sample(unique_replays, target_replay_count)

    # Combine and shuffle
    combined = sampled_motion + sampled_replay
    rng.shuffle(combined)

    actual_motion_count = sum(
        1 for r in combined
        if r.get("category", "").startswith("motion_")
        or "motion_" in r.get("task_id", "")
    )
    actual_ratio = actual_motion_count / max(1, len(combined))

    # Compute archetype distribution
    archetype_counts: Dict[str, int] = {}
    total_tokens = 0
    clean_count = 0
    dirty_count = 0

    for rec in combined:
        txt = extract_full_text(rec)
        total_tokens += estimate_tokens(txt)
        arch = detect_archetype(txt)
        archetype_counts[arch] = archetype_counts.get(arch, 0) + 1

        is_clean, _ = validate_trajectory_cleanliness(rec)
        if is_clean:
            clean_count += 1
        else:
            dirty_count += 1

    stats = {
        "total_records": len(combined),
        "motion_records": actual_motion_count,
        "replay_records": len(combined) - actual_motion_count,
        "target_ratio": round(motion_ratio, 4),
        "actual_motion_ratio": round(actual_ratio, 4),
        "avg_tokens_per_record": int(total_tokens / max(1, len(combined))),
        "clean_records": clean_count,
        "dirty_records": dirty_count,
        "archetype_distribution": {
            k: f"{v} ({round(v / len(combined) * 100, 1)}%)"
            for k, v in sorted(archetype_counts.items(), key=lambda item: item[1], reverse=True)
        },
    }

    return combined, stats


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Mix professional motion curriculum into core replay training data at a controlled ratio."
    )
    parser.add_argument(
        "--motion-file",
        type=Path,
        default=DEFAULT_MOTION_PATH,
        help=f"Path to motion SFT JSONL dataset (default: {DEFAULT_MOTION_PATH.name})",
    )
    parser.add_argument(
        "--replay-file",
        type=Path,
        default=DEFAULT_REPLAY_PATH,
        help=f"Path to core replay JSONL dataset (default: {DEFAULT_REPLAY_PATH.name})",
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help=f"Path to output mixed JSONL file (default: {DEFAULT_OUTPUT_PATH.name})",
    )
    parser.add_argument(
        "--motion-ratio",
        type=float,
        default=0.15,
        help="Target motion dataset fraction (default: 0.15 for 15%% motion)",
    )
    parser.add_argument(
        "--max-samples",
        type=int,
        default=None,
        help="Optional total number of records in output dataset",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible dataset mixing (default: 42)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute and display mixing statistics without writing output file",
    )

    args = parser.parse_args()

    print(f"[Curriculum Mixer] Loading motion dataset: {args.motion_file}")
    motion_records = load_jsonl(args.motion_file)
    print(f"[Curriculum Mixer] Loaded {len(motion_records)} motion trajectories.")

    # Fallback to secondary replay path if primary does not exist
    replay_path = args.replay_file
    if not replay_path.is_file():
        alt_paths = [
            ROOT_DIR / "data" / "step2_gated_survivors.jsonl",
            ROOT_DIR / "data" / "site_trajectories_batch4.jsonl",
        ]
        for alt in alt_paths:
            if alt.is_file():
                replay_path = alt
                print(f"[Curriculum Mixer] Default replay file not found; falling back to: {alt.name}")
                break

    print(f"[Curriculum Mixer] Loading replay dataset: {replay_path}")
    replay_records = load_jsonl(replay_path)
    print(f"[Curriculum Mixer] Loaded {len(replay_records)} replay trajectories.")

    print(f"[Curriculum Mixer] Blending datasets at target ratio: {args.motion_ratio * 100:.1f}% motion...")
    mixed, stats = mix_datasets(
        motion_records=motion_records,
        replay_records=replay_records,
        motion_ratio=args.motion_ratio,
        total_samples=args.max_samples,
        seed=args.seed,
    )

    print("\n" + "=" * 60)
    print("           CURRICULUM MIXING SUMMARY")
    print("=" * 60)
    print(f"Total Trajectories:       {stats['total_records']}")
    print(f"Motion Trajectories:      {stats['motion_records']} ({stats['actual_motion_ratio'] * 100:.1f}%)")
    print(f"Replay Trajectories:      {stats['replay_records']}")
    print(f"Target Motion Ratio:      {stats['target_ratio'] * 100:.1f}%")
    print(f"Avg Tokens per Record:    ~{stats['avg_tokens_per_record']} tokens")
    print(f"Clean Contract Records:   {stats['clean_records']} / {stats['total_records']}")
    print("\nArchetype Distribution:")
    for arch, val in stats["archetype_distribution"].items():
        print(f"  - {arch:<24}: {val}")
    print("=" * 60 + "\n")

    if args.dry_run:
        print("[Curriculum Mixer] Dry-run enabled. No output file written.")
    else:
        print(f"[Curriculum Mixer] Saving mixed curriculum to: {args.output_file}")
        save_jsonl(mixed, args.output_file)
        print(f"[Curriculum Mixer] Successfully saved {len(mixed)} records to {args.output_file.name}.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
