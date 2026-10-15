"""
tests/test_training_methodology.py - Verification for Issue #19:
Improve Training Methodology Before Running Expensive Sweeps.

Acceptance criteria:
- First goal: Establish whether the Qwen3 SFT dataset produces a measurable improvement.
- Prohibit unprincipled hyperparameter sweeps (R8, R16, R32, R64, multiple learning rates,
  multiple dropout values) by default.
- First comparison: Qwen3 Base vs Qwen3 SFT R16.
- Hyperparameter experiments are justified by measured limitations, not run by default.
"""

import json
from pathlib import Path
import pytest

from training.methodology import (
    evaluate_experiment_justification,
    guard_hyperparameter_sweep,
    MethodologyEvaluation,
)
from scripts.compare_qwen3_base_vs_sft import (
    run_comparison,
    compute_aggregate_metrics,
    format_comparison_table,
)


def test_default_conservative_r16_allowed_without_friction():
    """Verify conservative first run (rank=16, lr=2e-5, dropout=0.0) is allowed by default."""
    # Should not raise any error
    guard_hyperparameter_sweep(rank=16, learning_rate=2e-5, lora_dropout=0.0)


def test_hyperparameter_sweep_blocked_when_no_baseline_comparison(tmp_path):
    """Verify sweeps (e.g. rank=32, rank=64, non-standard lr) are blocked if no comparison exists."""
    missing_report = str(tmp_path / "non_existent_comparison.json")

    with pytest.raises(ValueError, match="is blocked by training methodology"):
        guard_hyperparameter_sweep(rank=32, comparison_report_path=missing_report)

    with pytest.raises(ValueError, match="is blocked by training methodology"):
        guard_hyperparameter_sweep(rank=64, comparison_report_path=missing_report)

    with pytest.raises(ValueError, match="is blocked by training methodology"):
        guard_hyperparameter_sweep(rank=16, learning_rate=1e-4, comparison_report_path=missing_report)


def test_hyperparameter_sweep_override_gate(tmp_path):
    """Verify explicit override bypasses the methodology guard when requested."""
    missing_report = str(tmp_path / "non_existent_comparison.json")
    # Should not raise when override=True
    guard_hyperparameter_sweep(rank=32, comparison_report_path=missing_report, override=True)
    guard_hyperparameter_sweep(rank=16, learning_rate=5e-5, comparison_report_path=missing_report, override=True)


def test_r32_justified_only_by_measured_interaction_capacity_limitation(tmp_path):
    """Verify R32 is justified only when measured interaction pass rate demonstrates a capacity bottleneck."""
    report_path = tmp_path / "comparison.json"

    # Case A: Balanced performance (render: 60%, interact: 55%) -> R32 NOT justified
    report_data_balanced = {
        "base_metrics": {"overall_pass_rate": 0.20, "typecheck_pass_rate": 0.50},
        "sft_metrics": {
            "overall_pass_rate": 0.58,
            "typecheck_pass_rate": 0.85,
            "category_pass_rates": {
                "tsc_and_render": 0.60,
                "tsc_render_interact": 0.55,
                "tsc_only": 0.65,
            },
        },
    }
    report_path.write_text(json.dumps(report_data_balanced), encoding="utf-8")
    eval_res = evaluate_experiment_justification(str(report_path))
    assert eval_res.measurable_improvement_detected is True
    assert eval_res.justifications["R32"].is_justified is False
    assert "No acute capacity bottleneck observed" in eval_res.justifications["R32"].rationale

    # Case B: Severe capacity drop on complex interaction tasks (render: 70%, interact: 30%) -> R32 JUSTIFIED
    report_data_bottleneck = {
        "base_metrics": {"overall_pass_rate": 0.20, "typecheck_pass_rate": 0.50},
        "sft_metrics": {
            "overall_pass_rate": 0.52,
            "typecheck_pass_rate": 0.85,
            "category_pass_rates": {
                "tsc_and_render": 0.70,
                "tsc_render_interact": 0.30,
                "tsc_only": 0.75,
            },
        },
    }
    report_path.write_text(json.dumps(report_data_bottleneck), encoding="utf-8")
    eval_res_bottleneck = evaluate_experiment_justification(str(report_path))
    assert eval_res_bottleneck.justifications["R32"].is_justified is True
    assert "JUSTIFIED BY MEASURED LIMITATION" in eval_res_bottleneck.justifications["R32"].rationale


def test_dpo_justified_only_after_sft_functional_baseline(tmp_path):
    """Verify DPO is blocked when SFT fails or has low pass rate, and justified once SFT succeeds."""
    report_path = tmp_path / "comparison.json"

    # Case A: Low SFT pass rate (15%) -> DPO blocked
    report_low = {
        "base_metrics": {"overall_pass_rate": 0.10, "typecheck_pass_rate": 0.30},
        "sft_metrics": {
            "overall_pass_rate": 0.15,
            "typecheck_pass_rate": 0.35,
            "category_pass_rates": {},
        },
    }
    report_path.write_text(json.dumps(report_low), encoding="utf-8")
    eval_low = evaluate_experiment_justification(str(report_path))
    assert eval_low.justifications["DPO"].is_justified is False
    assert "strengthen SFT data and supervision before preference alignment" in eval_low.justifications["DPO"].rationale

    # Case B: Solid SFT baseline (55%) -> DPO justified
    report_high = {
        "base_metrics": {"overall_pass_rate": 0.15, "typecheck_pass_rate": 0.40},
        "sft_metrics": {
            "overall_pass_rate": 0.55,
            "typecheck_pass_rate": 0.80,
            "category_pass_rates": {},
        },
    }
    report_path.write_text(json.dumps(report_high), encoding="utf-8")
    eval_high = evaluate_experiment_justification(str(report_path))
    assert eval_high.justifications["DPO"].is_justified is True
    assert "SFT R16 provides a viable agentic baseline" in eval_high.justifications["DPO"].rationale


def test_run_comparison_mock_generates_standard_table_and_report(tmp_path):
    """Verify compare_qwen3_base_vs_sft script produces standard report and table."""
    out_file = tmp_path / "test_comparison.json"
    report = run_comparison(
        base_model="base-model",
        sft_model="models/qwen3-siteagent-r16-sft",
        eval_set="data/eval/react_ts_css_eval_set_combined.jsonl",
        output=str(out_file),
        subset=6,
        mock=True,
    )

    assert out_file.is_file()
    assert report["total_examples"] == 6
    assert "base_metrics" in report
    assert "sft_metrics" in report
    assert "delta" in report
    assert "measurable_improvement" in report

    # Test formatted comparison table
    table = format_comparison_table(
        report["base_metrics"],
        report["sft_metrics"],
        elapsed_base=1.5,
        elapsed_sft=1.2,
    )
    assert "HEAD-TO-HEAD COMPARISON: QWEN3 BASE vs QWEN3 SFT R16" in table
    assert "Overall Pass Rate" in table
    assert "TypeScript Compile Rate" in table
    assert "Interactive UI & State" in table


def test_train_sft_preflight_enforces_methodology_guard(tmp_path, real_context_report):
    """Verify train_sft preflight rejects unprincipled rank sweeps without justification or override."""
    from training.train_sft import train

    # Attempting rank 32 with a non-existent report should raise ValueError from methodology guard
    with pytest.raises(ValueError, match="is blocked by training methodology|NOT justified"):
        train(
            dataset_path="data/interactive_curriculum_trajectories.jsonl",
            rank=32,
            preflight_only=True,
            benchmark_report=real_context_report,
        )

    # With override_methodology_gate=True, preflight passes cleanly
    train(
        dataset_path="data/interactive_curriculum_trajectories.jsonl",
        rank=32,
        preflight_only=True,
        override_methodology_gate=True,
        benchmark_report=real_context_report,
    )

