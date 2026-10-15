#!/usr/bin/env python3
"""
CLI tool to audit any dataset against the sealed final benchmark or dev benchmark.
Enforces the 6 evaluation leakage checks:
1. Exact prompt matching
2. Normalized matching
3. Symbol overlap
4. Token similarity (Jaccard)
5. Family-level holdout
6. Semantic similarity checks

Usage:
  python scripts/verify_benchmark_leakage.py --dataset data/training_data.jsonl
  python scripts/verify_benchmark_leakage.py --dataset data/eval/dev_benchmark.jsonl
"""

import argparse
import json
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from training.leakage_guard import (
    audit_dataset_against_benchmark,
    verify_sealed_benchmark_manifest,
    SEALED_BENCHMARK_PATH,
    SEALED_MANIFEST_PATH,
)


def main():
    parser = argparse.ArgumentParser(
        description="Verify evaluation benchmark leakage protection."
    )
    parser.add_argument(
        "--dataset",
        type=str,
        required=True,
        help="Path to dataset to audit (training, validation, or dev set).",
    )
    parser.add_argument(
        "--benchmark",
        type=str,
        default=str(SEALED_BENCHMARK_PATH),
        help="Path to benchmark JSONL (default: sealed final benchmark).",
    )
    parser.add_argument(
        "--manifest",
        type=str,
        default=str(SEALED_MANIFEST_PATH),
        help="Path to manifest JSON (default: sealed benchmark manifest).",
    )
    parser.add_argument(
        "--report",
        type=str,
        default="runs/sealed_benchmark_leakage_report.json",
        help="Path to output report JSON.",
    )
    parser.add_argument(
        "--token-threshold",
        type=float,
        default=0.50,
        help="Token Jaccard similarity threshold (default: 0.50).",
    )
    parser.add_argument(
        "--semantic-threshold",
        type=float,
        default=0.65,
        help="Semantic similarity threshold (default: 0.65).",
    )
    parser.add_argument(
        "--symbol-threshold",
        type=float,
        default=0.35,
        help="Symbol-conditioned token similarity threshold (default: 0.35).",
    )
    parser.add_argument(
        "--no-manifest-check",
        action="store_true",
        help="Skip cryptographic manifest integrity check.",
    )

    args = parser.parse_args()

    print("=" * 70)
    print("SiteAgent Benchmark Leakage Verification")
    print("=" * 70)
    print(f"Dataset to audit:    {args.dataset}")
    print(f"Held-out benchmark:  {args.benchmark}")
    if not args.no_manifest_check:
        print(f"Benchmark manifest:  {args.manifest}")
    print(f"Token threshold:     {args.token_threshold:.2f}")
    print(f"Semantic threshold:  {args.semantic_threshold:.2f}")
    print("-" * 70)

    try:
        report = audit_dataset_against_benchmark(
            dataset_path=args.dataset,
            benchmark_path=args.benchmark,
            manifest_path=None if args.no_manifest_check else args.manifest,
            token_similarity_threshold=args.token_threshold,
            semantic_similarity_threshold=args.semantic_threshold,
            symbol_overlap_threshold=args.symbol_threshold,
            verify_manifest=not args.no_manifest_check,
        )
    except Exception as e:
        print(f"\n[AUDIT ABORTED - INTEGRITY ERROR]: {e}")
        sys.exit(2)

    # Save report
    report_path = Path(args.report)
    if not report_path.is_absolute():
        report_path = BASE_DIR / report_path
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report.to_dict(), f, indent=2)

    print(f"Audited candidate samples: {report.total_candidate_samples}")
    print(f"Benchmark tasks:           {report.total_benchmark_tasks}")
    print(f"Peak token similarity:     {report.peak_token_similarity:.4f}")
    print(f"Peak semantic similarity:  {report.peak_semantic_similarity:.4f}")
    print(f"Manifest verified:         {report.manifest_verified}")
    print("-" * 70)

    if report.is_clean:
        print("RESULT: PASSED (0 Leaks Detected)")
        print(f"Report saved to: {report_path}")
        print("=" * 70)
        sys.exit(0)
    else:
        print(f"RESULT: FAILED ({report.leak_count} Leaks Detected!)")
        print("Leak Breakdown:")
        for k, count in report.breakdown.items():
            print(f"  - {k}: {count}")
        print("\nTop Violations:")
        for v in report.violations[:5]:
            print(f"  [{v.check_type}] {v.candidate_identifier} -> {v.benchmark_task_id}")
            print(f"    Message: {v.message}")
            print(f"    Candidate: {v.candidate_snippet}")
            print(f"    Benchmark: {v.benchmark_snippet}")
        print(f"\nFull report saved to: {report_path}")
        print("=" * 70)
        sys.exit(1)


if __name__ == "__main__":
    main()
