#!/usr/bin/env python3
"""
scripts/compare_qwen3_base_vs_sft.py - Automated Head-to-Head Comparison: Qwen3 Base vs Qwen3 SFT R16.

Enforces Issue #19 of the SiteAgent Implementation Plan:
1. Compares untouched Qwen3-4B Base (base-model/) vs Qwen3 SFT R16 (models/qwen3-siteagent-r16-sft/).
2. Uses identical benchmark settings:
   - Evaluation dataset (canonical 153-task or stratified subset)
   - Decoding parameters (temperature, max_new_tokens)
   - Prompt formatting & chat template
   - TypeScript strict compiler and Vitest + jsdom + RTL test harness
3. Establishes whether the Qwen3 SFT dataset produces a measurable improvement.
4. Produces the standard comparison table matching Section 32 of the Implementation Plan.
5. Saves the authoritative comparison report to runs/qwen3_base_vs_sft_comparison.json.
6. Evaluates whether subsequent hyperparameter experiments (R32, LR tuning, DPO) are justified.
"""

import argparse
import json
import os
from pathlib import Path
import shutil
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "agent"))
sys.path.insert(0, str(ROOT / "training"))

from evaluate import (
    ModelEvaluator,
    evaluate_batch,
    evaluate_sequential,
    get_stratified_sample,
)
from methodology import (
    evaluate_experiment_justification,
    evaluate_promotion_gate,
    DEFAULT_COMPARISON_REPORT_PATH,
)


def compute_aggregate_metrics(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    scored = [r for r in results if not r.get("skipped", False)]
    total = len(scored)
    if not total:
        return {
            "total": 0,
            "overall_pass_rate": 0.0,
            "typecheck_pass_rate": 0.0,
            "unit_test_pass_rate": 0.0,
            "category_pass_rates": {},
        }

    overall_passed = sum(1 for r in scored if r.get("overall_passed"))
    tsc_passed = sum(1 for r in scored if r.get("tsc_passed"))
    vitest_passed = sum(1 for r in scored if r.get("vitest_passed"))

    by_category: Dict[str, List[Dict[str, Any]]] = {}
    for r in scored:
        by_category.setdefault(r.get("check", "tsc_and_render"), []).append(r)

    category_rates = {}
    for cat, items in by_category.items():
        cat_total = len(items)
        cat_pass = sum(1 for r in items if r.get("overall_passed"))
        category_rates[cat] = cat_pass / cat_total if cat_total > 0 else 0.0

    return {
        "total": total,
        "overall_pass_rate": overall_passed / total,
        "typecheck_pass_rate": tsc_passed / total,
        "unit_test_pass_rate": vitest_passed / total,
        "category_pass_rates": category_rates,
    }


def format_comparison_table(
    base_metrics: Dict[str, Any],
    sft_metrics: Dict[str, Any],
    elapsed_base: float,
    elapsed_sft: float,
) -> str:
    lines = []
    lines.append("=" * 86)
    lines.append("           HEAD-TO-HEAD COMPARISON: QWEN3 BASE vs QWEN3 SFT R16")
    lines.append("=" * 86)
    lines.append(f"{'Metric':<32} {'Qwen3 Base':<16} {'Qwen3 SFT R16':<16} {'Delta':<16}")
    lines.append("-" * 86)

    # Overall pass rate
    base_overall = base_metrics.get("overall_pass_rate", 0.0)
    sft_overall = sft_metrics.get("overall_pass_rate", 0.0)
    delta_overall = sft_overall - base_overall
    lines.append(f"{'Overall Pass Rate (1-shot)':<32} {base_overall*100:>12.1f}%   {sft_overall*100:>12.1f}%   {delta_overall*100:>+12.1f}%")

    # Typecheck pass rate
    base_tsc = base_metrics.get("typecheck_pass_rate", 0.0)
    sft_tsc = sft_metrics.get("typecheck_pass_rate", 0.0)
    lines.append(f"{'TypeScript Compile Rate (tsc)':<32} {base_tsc*100:>12.1f}%   {sft_tsc*100:>12.1f}%   {(sft_tsc - base_tsc)*100:>+12.1f}%")

    # Vitest pass rate
    base_vitest = base_metrics.get("unit_test_pass_rate", 0.0)
    sft_vitest = sft_metrics.get("unit_test_pass_rate", 0.0)
    lines.append(f"{'Vitest RTL Test Rate':<32} {base_vitest*100:>12.1f}%   {sft_vitest*100:>12.1f}%   {(sft_vitest - base_vitest)*100:>+12.1f}%")

    lines.append("-" * 86)
    lines.append("Category Breakdown:")
    categories = [
        ("tsc_only", "TSC-only Components"),
        ("tsc_and_render", "Static Render Components"),
        ("tsc_render_a11y", "Accessibility (A11y)"),
        ("tsc_render_interact", "Interactive UI & State"),
    ]
    base_cats = base_metrics.get("category_pass_rates", {})
    sft_cats = sft_metrics.get("category_pass_rates", {})

    for cat_key, cat_label in categories:
        b_rate = base_cats.get(cat_key, 0.0)
        s_rate = sft_cats.get(cat_key, 0.0)
        d_rate = s_rate - b_rate
        lines.append(f"  {cat_label:<30} {b_rate*100:>12.1f}%   {s_rate*100:>12.1f}%   {d_rate*100:>+12.1f}%")

    lines.append("-" * 86)
    lines.append(f"{'Benchmark Elapsed Time':<32} {elapsed_base:>12.1f}s   {elapsed_sft:>12.1f}s   {elapsed_sft - elapsed_base:>+12.1f}s")
    lines.append("=" * 86)

    # -------------------------------------------------------------
    # Promotion Gate Evaluation (Issue #22 Requirement)
    # -------------------------------------------------------------
    from training.methodology import evaluate_promotion_gate
    promo = evaluate_promotion_gate(candidate_metrics=sft_metrics, baseline_metrics=base_metrics)

    lines.append("           MODEL PROMOTION GATE (Interaction Correctness Bar)")
    lines.append("=" * 86)
    status_str = "ELIGIBLE FOR PROMOTION" if promo.is_eligible else "PROMOTION BLOCKED"
    lines.append(f"Promotion Gate Status        : {status_str}")
    lines.append(f"First-Class Promotion Metric : Interaction UI & State (tsc_render_interact)")
    base_interact = promo.baseline_interaction_pass_rate if promo.baseline_interaction_pass_rate is not None else 0.0
    lines.append(f"  * Candidate Rate           : {promo.interaction_pass_rate*100:.1f}%")
    lines.append(f"  * Baseline Rate            : {base_interact*100:.1f}%")
    lines.append(f"  * Interaction Delta        : {(promo.interaction_delta or 0.0)*100:+.1f}%")
    lines.append("Gate Diagnostics:")
    for r in promo.reasons:
        lines.append(f"  [PASS] {r}")
    for b in promo.blocking_failures:
        lines.append(f"  [FAIL] {b}")
    lines.append(f"Summary: {promo.summary}")
    lines.append("=" * 86)
    return "\n".join(lines)


def run_comparison(
    base_model: str = "base-model",
    sft_model: str = "models/qwen3-siteagent-r16-sft",
    eval_set: str = "data/eval/react_ts_css_eval_set_combined.jsonl",
    output: str = DEFAULT_COMPARISON_REPORT_PATH,
    subset: Optional[int] = None,
    mode: str = "batch",
    mock: bool = False,
    max_new_tokens: int = 768,
    temperature: float = 0.2,
    seed: int = 42,
) -> Dict[str, Any]:
    base_model_path = base_model
    sft_model_path = sft_model
    eval_set_path = eval_set
    output_path = output
    print("\n" + "=" * 86)
    print("           STARTING QWEN3 BASE vs SFT R16 METHODOLOGY COMPARISON")
    print("=" * 86)
    print(f"Base Model Target : {base_model_path}")
    print(f"SFT Model Target  : {sft_model_path}")
    print(f"Evaluation Dataset: {eval_set_path}")
    print(f"Subset Size       : {subset if subset else 'ALL'}")
    print(f"Execution Mode    : {mode} (mock={mock})")

    eval_file = Path(eval_set_path)
    if not eval_file.is_absolute() and not eval_file.exists() and (ROOT / eval_set_path).exists():
        eval_file = ROOT / eval_set_path

    if not eval_file.exists():
        raise FileNotFoundError(f"Evaluation set not found at: {eval_file}")

    with open(eval_file, encoding="utf-8") as f:
        all_items = [json.loads(line) for line in f if line.strip()]

    if subset and subset < len(all_items):
        selected_items = get_stratified_sample(all_items, subset, seed=seed)
        print(f"Using stratified sample of {len(selected_items)} examples.")
    else:
        selected_items = list(enumerate(all_items))

    workspace_base = ROOT / ".eval_compare_base"
    workspace_sft = ROOT / ".eval_compare_sft"
    for w in (workspace_base, workspace_sft):
        if w.exists():
            shutil.rmtree(w)
        w.mkdir(parents=True, exist_ok=True)

    # -------------------------------------------------------------
    # 1. Evaluate Qwen3 Base
    # -------------------------------------------------------------
    print("\n>>> [1/2] Evaluating Untouched Qwen3 Base Model...")
    start_base = time.time()
    evaluator_base = ModelEvaluator(
        model_name=base_model_path,
        is_mock=mock,
        agent_protocol=False,
    )
    if mode == "batch":
        base_results = evaluate_batch(
            eval_items=selected_items,
            evaluator=evaluator_base,
            workspace_dir=workspace_base,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
        )
    else:
        base_results = evaluate_sequential(
            eval_items=selected_items,
            evaluator=evaluator_base,
            workspace_dir=workspace_base,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
        )
    elapsed_base = time.time() - start_base

    # If mock, simulate slight baseline vs fine-tuned difference for realistic test verification
    if mock:
        # In mock mode, base passes ~30% and SFT passes ~85%
        for i, r in enumerate(base_results):
            if i % 3 != 0:
                r["overall_passed"] = False
                r["vitest_passed"] = False

    base_metrics = compute_aggregate_metrics(base_results)

    # Clean up base evaluator GPU memory before loading SFT
    del evaluator_base
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        pass

    # -------------------------------------------------------------
    # 2. Evaluate Qwen3 SFT R16
    # -------------------------------------------------------------
    print("\n>>> [2/2] Evaluating Retrained Qwen3 SFT R16 Model...")
    start_sft = time.time()
    evaluator_sft = ModelEvaluator(
        model_name=sft_model_path,
        is_mock=mock,
        agent_protocol=False,
    )
    if mode == "batch":
        sft_results = evaluate_batch(
            eval_items=selected_items,
            evaluator=evaluator_sft,
            workspace_dir=workspace_sft,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
        )
    else:
        sft_results = evaluate_sequential(
            eval_items=selected_items,
            evaluator=evaluator_sft,
            workspace_dir=workspace_sft,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
        )
    elapsed_sft = time.time() - start_sft

    sft_metrics = compute_aggregate_metrics(sft_results)

    # -------------------------------------------------------------
    # 3. Format & Output Comparison
    # -------------------------------------------------------------
    table_str = format_comparison_table(base_metrics, sft_metrics, elapsed_base, elapsed_sft)
    print("\n" + table_str)

    delta = sft_metrics["overall_pass_rate"] - base_metrics["overall_pass_rate"]
    is_measurable_improvement = delta > 0.0

    out_file = Path(output_path)
    if not out_file.is_absolute():
        out_file = ROOT / output_path
    out_file.parent.mkdir(parents=True, exist_ok=True)

    from training.provenance import generate_provenance_record
    prov_meta = generate_provenance_record(
        mock=mock,
        model_path=base_model_path,
        adapter_path=sft_model_path,
        dataset_path=str(eval_file),
    )
    cand_metrics_with_prov = {**sft_metrics, **prov_meta}

    report = {
        **prov_meta,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "base_model": base_model_path,
        "sft_model": sft_model_path,
        "eval_set": str(eval_file),
        "total_examples": len(selected_items),
        "mode": mode,
        "is_mock": mock,
        "base_metrics": base_metrics,
        "sft_metrics": sft_metrics,
        "delta": {
            "overall_pass_rate": delta,
            "typecheck_pass_rate": sft_metrics["typecheck_pass_rate"] - base_metrics["typecheck_pass_rate"],
            "unit_test_pass_rate": sft_metrics["unit_test_pass_rate"] - base_metrics["unit_test_pass_rate"],
        },
        "measurable_improvement": is_measurable_improvement,
        "promotion_gate": evaluate_promotion_gate(cand_metrics_with_prov, base_metrics).to_dict(),
        "elapsed_seconds": {
            "base": round(elapsed_base, 2),
            "sft": round(elapsed_sft, 2),
        },
    }

    out_file.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"\nAuthoritative comparison report written to: {out_file}")

    # Evaluate justification for future experiments
    justification = evaluate_experiment_justification(str(out_file))
    print("\nNext Experiment Justification Analysis:")
    for name, just in justification.justifications.items():
        status = "[JUSTIFIED]" if just.is_justified else "[BLOCKED / NOT JUSTIFIED]"
        print(f"  * {name:<22}: {status}")
        print(f"    Rationale: {just.rationale}")

    print(f"\nRecommendation: {justification.recommendation}")
    print("=" * 86)

    return report


def main():
    parser = argparse.ArgumentParser(description="Qwen3 Base vs SFT R16 Head-to-Head Methodology Comparison")
    parser.add_argument("--base-model", default="base-model", help="Path to base model directory")
    parser.add_argument("--sft-model", default="models/qwen3-siteagent-r16-sft", help="Path to SFT adapter directory")
    parser.add_argument(
        "--eval-set",
        default="data/eval/react_ts_css_eval_set_combined.jsonl",
        help="Path to evaluation JSONL dataset",
    )
    parser.add_argument("--subset", type=int, default=None, help="Stratified sample count")
    parser.add_argument("--output", default=DEFAULT_COMPARISON_REPORT_PATH, help="Output comparison JSON report")
    parser.add_argument("--mode", choices=["batch", "sequential"], default="batch", help="Execution mode")
    parser.add_argument("--mock", action="store_true", help="Run with mock generation for fast testing")
    parser.add_argument("--max-new-tokens", type=int, default=768)
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)

    args = parser.parse_args()
    run_comparison(**vars(args))


if __name__ == "__main__":
    main()
