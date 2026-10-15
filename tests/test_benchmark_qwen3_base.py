"""
tests/test_benchmark_qwen3_base.py - Verification for Issue #20:
Benchmark the Untouched Qwen3 Base Before SFT.

Acceptance criteria:
- Run untouched Qwen3-4B base before LoRA training.
- Use exact same benchmark settings as SFT:
  * 153-task evaluation set
  * max turns
  * temperature
  * output limits
  * parser
  * test harness
  * repair policy
  * runtime
- Record all 10 required measurements:
  * first-turn pass rate
  * agentic final pass rate
  * average turns
  * category breakdown
  * compile failures
  * runtime failures
  * interaction failures
  * truncations
  * generation time
  * VRAM
- Quantify the contribution of SFT separately from the base model.
"""

import json
from pathlib import Path
import pytest

from scripts.benchmark_qwen3_base import (
    run_base_benchmark,
    classify_task_failure,
    check_is_truncated,
    quantify_sft_contribution,
    DEFAULT_EVAL_SET,
)


def test_classify_task_failure():
    """Verify task failures are classified into the 4 mutually exclusive failure modes."""
    # Passed task
    assert classify_task_failure({"final_passed": True}) == "none"

    # Truncated task
    assert classify_task_failure({"final_passed": False, "is_truncated": True}) == "truncation"

    # Compile failure
    assert classify_task_failure({"final_passed": False, "is_truncated": False, "final_tsc_passed": False}) == "compile_failure"

    # Interaction failure
    assert classify_task_failure({
        "final_passed": False,
        "is_truncated": False,
        "final_tsc_passed": True,
        "check": "tsc_render_interact",
    }) == "interaction_failure"

    # Runtime / Render failure
    assert classify_task_failure({
        "final_passed": False,
        "is_truncated": False,
        "final_tsc_passed": True,
        "check": "tsc_and_render",
    }) == "runtime_failure"


def test_check_is_truncated():
    """Verify detection of unclosed envelope tags and token truncation."""
    # Unclosed tool call
    assert check_is_truncated('<tool_call name="write_component">\n<tsx>code...', 768) is True

    # Unclosed tsx
    assert check_is_truncated('<tool_call name="write_component">\n<tsx>code\n</tool_call>', 768) is True

    # Unclosed finish
    assert check_is_truncated('<finish>\nSummary without close', 768) is True

    # Complete tags
    assert check_is_truncated('<tool_call name="write_component">\n<tsx>code</tsx>\n</tool_call>', 768) is False
    assert check_is_truncated('<finish>\nComplete summary.\n</finish>', 768) is False


def test_run_base_benchmark_records_all_10_measurements(tmp_path):
    """Verify benchmark run produces the authoritative JSON report with all 10 required metrics."""
    out_report = tmp_path / "base_benchmark_test.json"

    report = run_base_benchmark(
        model_path="base-model",
        eval_set_path=DEFAULT_EVAL_SET,
        output_path=str(out_report),
        max_turns=3,
        temperature=0.2,
        max_new_tokens=768,
        subset=4,
        mock=True,
    )

    assert out_report.is_file()
    assert report["model_type"] == "untouched_base"
    m = report["measurements"]

    # 1. First-turn pass rate
    assert "first_turn_pass_rate" in m
    assert 0.0 <= m["first_turn_pass_rate"] <= 1.0

    # 2. Agentic final pass rate
    assert "agentic_final_pass_rate" in m
    assert 0.0 <= m["agentic_final_pass_rate"] <= 1.0

    # 3. Average turns
    assert "average_turns" in m
    assert m["average_turns"] >= 1.0

    # 4. Category breakdown
    assert "category_breakdown" in m
    assert isinstance(m["category_breakdown"], dict)

    # 5. Compile failures
    assert "compile_failures" in m
    assert isinstance(m["compile_failures"], int)

    # 6. Runtime failures
    assert "runtime_failures" in m
    assert isinstance(m["runtime_failures"], int)

    # 7. Interaction failures
    assert "interaction_failures" in m
    assert isinstance(m["interaction_failures"], int)

    # 8. Truncations
    assert "truncations" in m
    assert isinstance(m["truncations"], int)

    # 9. Generation time
    assert "generation_time_seconds" in m
    assert m["generation_time_seconds"] >= 0.0

    # 10. VRAM
    assert "peak_vram_allocated_bytes" in m
    assert "peak_vram_reserved_bytes" in m
    assert "peak_vram_allocated_gib" in m


def test_benchmark_settings_exact_alignment():
    """Verify benchmark settings match the SFT evaluation environment."""
    report_file = Path("runs/qwen3_base_benchmark.json")
    if not report_file.is_file():
        pytest.skip("Base benchmark report not found; run benchmark_qwen3_base first.")

    data = json.loads(report_file.read_text(encoding="utf-8"))
    settings = data["benchmark_settings"]

    assert settings["max_turns"] == 5
    assert settings["temperature"] == 0.2
    assert settings["max_new_tokens"] == 768
    assert settings["parser"] == "parse_agent_output"
    assert settings["test_harness"] == "tsc strict + Vitest RTL"
    assert "AgentModelRunner" in settings["runtime"]


def test_quantify_sft_contribution(tmp_path):
    """Verify quantifying the contribution of SFT separately from the base model."""
    base_file = tmp_path / "base.json"
    sft_file = tmp_path / "sft.json"

    base_data = {
        "model": "base-model",
        "measurements": {
            "first_turn_pass_rate": 0.08,
            "agentic_final_pass_rate": 0.15,
            "compile_failure_rate": 0.70,
        },
    }
    sft_data = {
        "sft_model": "models/qwen3-siteagent-r16-sft",
        "sft_metrics": {
            "overall_pass_rate": 0.52,
            "typecheck_pass_rate": 0.85,
        },
    }
    base_file.write_text(json.dumps(base_data), encoding="utf-8")
    sft_file.write_text(json.dumps(sft_data), encoding="utf-8")

    contribution = quantify_sft_contribution(str(base_file), str(sft_file))

    assert contribution["base_first_turn_pass_rate"] == 0.08
    assert contribution["sft_first_turn_pass_rate"] == 0.52
    assert contribution["sft_net_improvement_percentage_points"] == 44.0
    assert contribution["sft_relative_gain_multiplier"] == 6.5
    assert "SFT provides a net +44.0 percentage point improvement" in contribution["quantified_contribution"]
