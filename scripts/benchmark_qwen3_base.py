#!/usr/bin/env python3
"""
scripts/benchmark_qwen3_base.py - Benchmark the Untouched Qwen3 Base Model Before SFT.

Enforces Issue #20 of the SiteAgent Implementation Plan:
1. Benchmark untouched Qwen3-4B base model (base-model/) before LoRA training.
2. Uses the exact same benchmark settings used for SFT:
   - 153-task evaluation set (data/eval/react_ts_css_eval_set_combined.jsonl)
   - max turns (default: 5)
   - temperature (default: 0.2)
   - output limits (max_new_tokens = 768)
   - parser (parse_agent_output)
   - test harness (tsc strict + Vitest RTL)
   - repair policy (agentic observation feedback & anti-stuck temperature escalation)
   - runtime (AgentModelRunner / native Qwen3 chat template)
3. Records all 10 required measurements:
   - first-turn pass rate
   - agentic final pass rate
   - average turns
   - category breakdown (tsc_only, tsc_and_render, tsc_render_a11y, tsc_render_interact)
   - compile failures
   - runtime failures
   - interaction failures
   - truncations
   - generation time
   - VRAM
4. Quantifies the contribution of SFT separately from the base model.
5. Saves the report to runs/qwen3_base_benchmark.json.
"""

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent.agent import AgentModelRunner, run_agent_on_example
from agent.agent_protocol import parse_agent_output, WriteComponentAction
from training.evaluate import get_stratified_sample
from training.undeclared_identifier_guard import is_undeclared_identifier_failure


DEFAULT_EVAL_SET = "data/eval/react_ts_css_eval_set_combined.jsonl"
DEFAULT_OUTPUT_REPORT = "runs/qwen3_base_benchmark.json"


def classify_task_failure(result: Dict[str, Any]) -> str:
    """
    Classifies failure mode into compile_failure, runtime_failure, interaction_failure,
    truncation, or undeclared_identifier_failure.
    """
    if result.get("final_passed"):
        return "none"

    if result.get("is_truncated"):
        return "truncation"

    if is_undeclared_identifier_failure(result):
        return "undeclared_identifier_failure"

    if not result.get("final_tsc_passed"):
        return "compile_failure"

    check = result.get("check", "tsc_and_render")
    if check == "tsc_render_interact":
        return "interaction_failure"

    return "runtime_failure"


def check_is_truncated(response: str, max_new_tokens: int) -> bool:
    """
    Detects if the model response suffered token truncation or unclosed envelope tags.
    """
    clean = response.strip()
    # Check unclosed XML tags
    if "<tool_call" in clean and "</tool_call>" not in clean:
        return True
    if "<tsx>" in clean and "</tsx>" not in clean:
        return True
    if "<finish>" in clean and "</finish>" not in clean:
        return True
    return False


def run_base_benchmark(
    model_path: str = "base-model",
    eval_set_path: str = DEFAULT_EVAL_SET,
    output_path: str = DEFAULT_OUTPUT_REPORT,
    max_turns: int = 5,
    temperature: float = 0.2,
    max_new_tokens: int = 768,
    subset: Optional[int] = None,
    mock: bool = False,
    seed: int = 42,
    dynamic_budget: bool = False,
) -> Dict[str, Any]:
    print("\n" + "=" * 80)
    print("      BENCHMARKING UNTOUCHED QWEN3-4B BASE MODEL (PRE-SFT BASELINE)")
    print("=" * 80)
    print(f"Model Path        : {model_path}")
    print(f"Evaluation Dataset: {eval_set_path}")
    print(f"Max Turns         : {max_turns}")
    print(f"Temperature       : {temperature}")
    print(f"Max New Tokens    : {'Dynamic Budget' if dynamic_budget else max_new_tokens}")
    print(f"Subset Size       : {subset if subset else 'ALL (153)'}")
    print(f"Mock Mode         : {mock}")
    print("=" * 80)

    eval_file = Path(eval_set_path)
    if not eval_file.is_absolute() and not eval_file.exists() and (ROOT / eval_set_path).exists():
        eval_file = ROOT / eval_set_path

    if not eval_file.exists():
        raise FileNotFoundError(f"Evaluation set not found at: {eval_file}")

    with open(eval_file, encoding="utf-8") as f:
        all_items = [json.loads(line) for line in f if line.strip()]

    if subset and subset < len(all_items):
        selected_items = get_stratified_sample(all_items, subset, seed=seed)
        print(f"Selected {len(selected_items)} stratified evaluation examples.")
    else:
        selected_items = list(enumerate(all_items))

    workspace_dir = ROOT / ".eval_workspace_base_benchmark"
    if workspace_dir.exists():
        shutil.rmtree(workspace_dir)
    workspace_dir.mkdir(parents=True, exist_ok=True)

    # Initialize runner
    runner = AgentModelRunner(
        model_path=model_path,
        max_seq_length=8192,
        is_mock=mock,
    )

    # Reset VRAM peak stats if CUDA is active
    peak_vram_allocated = 0
    peak_vram_reserved = 0
    try:
        import torch
        if torch.cuda.is_available() and not mock:
            torch.cuda.reset_peak_memory_stats()
    except Exception:
        pass

    results = []
    start_total_time = time.time()
    compile_failures = 0
    runtime_failures = 0
    interaction_failures = 0
    undeclared_failures = 0
    truncation_count = 0

    for i, (orig_idx, item) in enumerate(selected_items):
        t_start = time.time()
        print(f"\n[{i+1}/{len(selected_items)}] Evaluating Base on Task #{orig_idx+1} ({item.get('primary_export', 'Component')})...")

        task_max_tokens = None if dynamic_budget else max_new_tokens
        task_res = run_agent_on_example(
            orig_idx=orig_idx,
            item=item,
            runner=runner,
            workspace_root=workspace_dir,
            max_turns=max_turns,
            temperature=temperature,
            max_new_tokens=task_max_tokens,
            best_of_2=False,  # Strict single-candidate evaluation for pure base model capability
        )
        t_elapsed = time.time() - t_start
        task_res["task_elapsed_seconds"] = round(t_elapsed, 2)

        # Check for truncation in trajectories
        check_limit = task_res.get("output_token_budget", {}).get("clamped_tokens", max_new_tokens)
        is_trunc = False
        for msg in task_res.get("trajectory", []):
            if msg.get("role") == "assistant" and check_is_truncated(msg.get("content", ""), check_limit):
                is_trunc = True
                break
        task_res["is_truncated"] = is_trunc
        if is_trunc:
            truncation_count += 1

        # Failure mode classification
        failure_mode = classify_task_failure(task_res)
        task_res["failure_mode"] = failure_mode
        if failure_mode == "compile_failure":
            compile_failures += 1
        elif failure_mode == "undeclared_identifier_failure":
            undeclared_failures += 1
        elif failure_mode == "runtime_failure":
            runtime_failures += 1
        elif failure_mode == "interaction_failure":
            interaction_failures += 1

        results.append(task_res)

    total_generation_time = time.time() - start_total_time

    # Record VRAM usage
    try:
        import torch
        if torch.cuda.is_available() and not mock:
            peak_vram_allocated = torch.cuda.max_memory_allocated()
            peak_vram_reserved = torch.cuda.max_memory_reserved()
    except Exception:
        pass

    total_count = len(results)
    first_turn_passes = sum(1 for r in results if r.get("initial_passed"))
    final_passes = sum(1 for r in results if r.get("final_passed"))
    first_turn_pass_rate = first_turn_passes / total_count if total_count > 0 else 0.0
    agentic_final_pass_rate = final_passes / total_count if total_count > 0 else 0.0
    avg_turns = sum(r.get("turns_used", 1) for r in results) / total_count if total_count > 0 else 1.0

    # Category breakdown
    by_category: Dict[str, List[Dict[str, Any]]] = {}
    for r in results:
        cat = r.get("check", "tsc_and_render")
        by_category.setdefault(cat, []).append(r)

    category_breakdown = {}
    for cat, items in by_category.items():
        c_tot = len(items)
        c_1shot = sum(1 for r in items if r.get("initial_passed"))
        c_final = sum(1 for r in items if r.get("final_passed"))
        category_breakdown[cat] = {
            "total": c_tot,
            "first_turn_passed": c_1shot,
            "first_turn_pass_rate": round(c_1shot / c_tot, 4) if c_tot > 0 else 0.0,
            "final_passed": c_final,
            "final_pass_rate": round(c_final / c_tot, 4) if c_tot > 0 else 0.0,
        }

    from training.provenance import generate_provenance_record
    prov_meta = generate_provenance_record(
        mock=mock,
        model_path=model_path,
        dataset_path=str(eval_file),
    )

    report = {
        **prov_meta,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "model": model_path,
        "model_type": "untouched_base",
        "eval_set": str(eval_file),
        "benchmark_settings": {
            "total_tasks": total_count,
            "max_turns": max_turns,
            "temperature": temperature,
            "max_new_tokens": max_new_tokens,
            "parser": "parse_agent_output",
            "test_harness": "tsc strict + Vitest RTL",
            "repair_policy": "agentic observation feedback & anti-stuck temperature escalation",
            "runtime": "AgentModelRunner (Qwen3 native chat template, enable_thinking=False)",
        },
        "measurements": {
            "first_turn_pass_rate": round(first_turn_pass_rate, 4),
            "first_turn_passed_count": first_turn_passes,
            "agentic_final_pass_rate": round(agentic_final_pass_rate, 4),
            "agentic_final_passed_count": final_passes,
            "average_turns": round(avg_turns, 2),
            "category_breakdown": category_breakdown,
            "compile_failures": compile_failures,
            "compile_failure_rate": round(compile_failures / total_count, 4) if total_count > 0 else 0.0,
            "undeclared_identifier_failures": undeclared_failures,
            "undeclared_identifier_failure_rate": round(undeclared_failures / total_count, 4) if total_count > 0 else 0.0,
            "runtime_failures": runtime_failures,
            "runtime_failure_rate": round(runtime_failures / total_count, 4) if total_count > 0 else 0.0,
            "interaction_failures": interaction_failures,
            "interaction_failure_rate": round(interaction_failures / total_count, 4) if total_count > 0 else 0.0,
            "truncations": truncation_count,
            "truncation_rate": round(truncation_count / total_count, 4) if total_count > 0 else 0.0,
            "generation_time_seconds": round(total_generation_time, 2),
            "average_task_time_seconds": round(total_generation_time / total_count, 2) if total_count > 0 else 0.0,
            "peak_vram_allocated_bytes": peak_vram_allocated,
            "peak_vram_allocated_gib": round(peak_vram_allocated / (1024 ** 3), 3),
            "peak_vram_reserved_bytes": peak_vram_reserved,
            "peak_vram_reserved_gib": round(peak_vram_reserved / (1024 ** 3), 3),
        },
        "results_summary": [
            {
                "index": r["index"],
                "primary_symbol": r["primary_symbol"],
                "check": r["check"],
                "turns_used": r["turns_used"],
                "initial_passed": r["initial_passed"],
                "final_passed": r["final_passed"],
                "failure_mode": r["failure_mode"],
                "is_truncated": r["is_truncated"],
                "output_token_budget": r.get("output_token_budget"),
            }
            for r in results
        ],
    }

    out_file = Path(output_path)
    if not out_file.is_absolute():
        out_file = ROOT / output_path
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"\nBenchmark report saved to: {out_file}")

    # Print comprehensive summary
    print_base_benchmark_summary(report)

    return report


def print_base_benchmark_summary(report: Dict[str, Any]) -> None:
    m = report["measurements"]
    tot = report["benchmark_settings"]["total_tasks"]

    print("\n" + "=" * 80)
    print("             QWEN3-4B UNTOUCHED BASE MODEL BENCHMARK RESULTS")
    print("=" * 80)
    print(f"{'Total Benchmark Tasks':<34}: {tot}")
    print(f"{'First-Turn Pass Rate (1-shot)':<34}: {m['first_turn_passed_count']}/{tot} ({m['first_turn_pass_rate']*100:.1f}%)")
    print(f"{'Agentic Final Pass Rate':<34}: {m['agentic_final_passed_count']}/{tot} ({m['agentic_final_pass_rate']*100:.1f}%)")
    print(f"{'Average Turns Used':<34}: {m['average_turns']:.2f}")
    print("-" * 80)
    print("Category Breakdown:")
    for cat_name, cat_data in m["category_breakdown"].items():
        print(f"  * {cat_name:<26}: 1-shot={cat_data['first_turn_pass_rate']*100:>5.1f}% | Final={cat_data['final_pass_rate']*100:>5.1f}% (n={cat_data['total']})")

    print("-" * 80)
    print("Failure Mode Taxonomy:")
    print(f"  * Compile Failures (tsc)          : {m['compile_failures']} ({m['compile_failure_rate']*100:.1f}%)")
    print(f"  * Runtime / Render Failures       : {m['runtime_failures']} ({m['runtime_failure_rate']*100:.1f}%)")
    print(f"  * Interaction / Assertion Failures: {m['interaction_failures']} ({m['interaction_failure_rate']*100:.1f}%)")
    print(f"  * Truncations / Unclosed Tags     : {m['truncations']} ({m['truncation_rate']*100:.1f}%)")
    print("-" * 80)
    print("Performance & Memory:")
    print(f"  * Total Generation Time           : {m['generation_time_seconds']}s (avg {m['average_task_time_seconds']}s / task)")
    print(f"  * Peak VRAM Allocated             : {m['peak_vram_allocated_gib']} GiB ({m['peak_vram_allocated_bytes']} bytes)")
    print(f"  * Peak VRAM Reserved              : {m['peak_vram_reserved_gib']} GiB ({m['peak_vram_reserved_bytes']} bytes)")
    print("=" * 80)


def quantify_sft_contribution(
    base_benchmark_path: str = DEFAULT_OUTPUT_REPORT,
    sft_benchmark_path: str = "runs/qwen3_base_vs_sft_comparison.json",
) -> Dict[str, Any]:
    """
    Quantifies the isolated contribution of SFT separately from the base model across all metrics.
    """
    base_file = Path(base_benchmark_path)
    if not base_file.is_file():
        raise FileNotFoundError(f"Base benchmark report not found: {base_file}")

    sft_file = Path(sft_benchmark_path)
    if not sft_file.is_file():
        raise FileNotFoundError(f"SFT comparison report not found: {sft_file}")

    base_data = json.loads(base_file.read_text(encoding="utf-8"))
    sft_data = json.loads(sft_file.read_text(encoding="utf-8"))

    base_measurements = base_data.get("measurements", {})
    sft_metrics = sft_data.get("sft_metrics", {})
    base_overall = base_measurements.get("first_turn_pass_rate", sft_data.get("base_metrics", {}).get("overall_pass_rate", 0.0))
    sft_overall = sft_metrics.get("overall_pass_rate", 0.0)

    base_tsc = base_measurements.get("compile_failure_rate", 0.0)
    sft_tsc = sft_metrics.get("typecheck_pass_rate", 0.0)

    delta_overall = sft_overall - base_overall
    contribution = {
        "base_model": base_data.get("model", "base-model"),
        "sft_model": sft_data.get("sft_model", "models/qwen3-siteagent-r16-sft"),
        "base_first_turn_pass_rate": base_overall,
        "sft_first_turn_pass_rate": sft_overall,
        "sft_net_improvement_percentage_points": round(delta_overall * 100, 2),
        "sft_relative_gain_multiplier": round(sft_overall / base_overall, 2) if base_overall > 0 else None,
        "base_agentic_final_pass_rate": base_measurements.get("agentic_final_pass_rate", 0.0),
        "compile_error_reduction": round(base_tsc - (1.0 - sft_tsc), 4) if base_tsc > 0 else 0.0,
        "quantified_contribution": (
            f"SFT provides a net +{delta_overall*100:.1f} percentage point improvement over untouched Qwen3 base. "
            f"Base establishes the foundation ({base_overall*100:.1f}%), while SFT delivers "
            f"agentic protocol adherence and component contract conformity."
        ),
    }

    print("\n" + "=" * 80)
    print("             QUANTIFIED CONTRIBUTION OF SFT OVER QWEN3 BASE")
    print("=" * 80)
    print(f"Base 1-Shot Pass Rate      : {base_overall*100:.1f}%")
    print(f"SFT 1-Shot Pass Rate       : {sft_overall*100:.1f}%")
    print(f"Net SFT Improvement        : +{delta_overall*100:.1f}% ({contribution['sft_relative_gain_multiplier']}x gain)")
    print(f"Summary                    : {contribution['quantified_contribution']}")
    print("=" * 80)

    return contribution


def main():
    parser = argparse.ArgumentParser(description="Benchmark Untouched Qwen3-4B Base Model Before SFT")
    parser.add_argument("--model", default="base-model", help="Path to untouched base model directory")
    parser.add_argument("--eval-set", default=DEFAULT_EVAL_SET, help="Path to 153-task JSONL evaluation set")
    parser.add_argument("--output", default=DEFAULT_OUTPUT_REPORT, help="Path to save output benchmark report JSON")
    parser.add_argument("--max-turns", type=int, default=5, help="Max turns in agentic repair loop")
    parser.add_argument("--temperature", type=float, default=0.2, help="Sampling temperature")
    parser.add_argument("--max-new-tokens", type=int, default=768, help="Output token limit")
    parser.add_argument("--dynamic-budget", action="store_true", help="Enable dynamic output token budgeting")
    parser.add_argument("--subset", type=int, default=None, help="Stratified sample count")
    parser.add_argument("--mock", action="store_true", help="Run with mock generation for fast testing")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--compare-sft", default=None, help="Path to SFT comparison report to quantify contribution")

    args = parser.parse_args()
    report = run_base_benchmark(
        model_path=args.model,
        eval_set_path=args.eval_set,
        output_path=args.output,
        max_turns=args.max_turns,
        temperature=args.temperature,
        max_new_tokens=args.max_new_tokens,
        subset=args.subset,
        mock=args.mock,
        seed=args.seed,
        dynamic_budget=args.dynamic_budget,
    )

    if args.compare_sft:
        quantify_sft_contribution(
            base_benchmark_path=args.output,
            sft_benchmark_path=args.compare_sft,
        )


if __name__ == "__main__":
    main()
