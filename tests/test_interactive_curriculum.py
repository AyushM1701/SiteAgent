"""
Unit tests for the Interactive UI Curriculum and Promotion Gate (Issue #22).

Verifies:
1. Complete curriculum coverage of all 23 required interaction patterns.
2. Self-correction trajectory structure (initial output -> test failure -> diagnostic observation -> corrected output -> verified pass).
3. Zero-thought policy compliance across all assistant messages.
4. Strict leakage disjointness against the sealed final benchmark (all 6 checks).
5. Elevation of the interaction category pass rate to a first-class promotion metric.
"""

import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_pipeline.build_interactive_curriculum import (
    INTERACTIVE_TOPICS,
    OUTPUT_PATH,
    build_all_curriculum_trajectories,
)
from training.leakage_guard import (
    audit_dataset_against_benchmark,
    SEALED_BENCHMARK_PATH,
    SEALED_MANIFEST_PATH,
)
from training.preflight import validate_messages
from training.methodology import evaluate_promotion_gate, PromotionGateEvaluation
from scripts.compare_qwen3_base_vs_sft import run_comparison


@pytest.fixture(scope="module")
def curriculum_records():
    assert OUTPUT_PATH.exists(), f"Curriculum dataset missing at {OUTPUT_PATH}"
    with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def test_all_23_topics_present(curriculum_records):
    """Verifies that all 23 interaction topics required by Issue #22 are present."""
    assert len(INTERACTIVE_TOPICS) == 23
    dataset_topics = {r.get("topic") for r in curriculum_records}
    for topic in INTERACTIVE_TOPICS:
        assert topic in dataset_topics, f"Missing required topic: {topic}"


def test_trajectory_structure(curriculum_records):
    """
    Verifies that every trajectory strictly embodies the self-correction pattern:
      Turn 1 (User): Prompt
      Turn 2 (Assistant): Initial output
      Turn 3 (User / Simulator): Real test failure observation (<observation status="error">)
      Turn 4 (Assistant): Corrected output
      Turn 5 (User / Simulator): Verified pass confirmation (<observation status="ok">)
      Turn 6 (Assistant): Finish tag (<finish>)
    """
    assert len(curriculum_records) >= 23

    for row in curriculum_records:
        # Preflight validation confirms message alternation and balanced action tags
        messages = validate_messages(row)
        assert len(messages) == 6, f"Expected 6 turns in self-correction trajectory for {row.get('task_id')}"

        # Turn 1: User prompt
        assert messages[0]["role"] == "user"
        assert not messages[0]["content"].startswith("<observation")

        # Turn 2: Initial output with tool_call
        assert messages[1]["role"] == "assistant"
        assert '<tool_call name="write_component">' in messages[1]["content"]

        # Turn 3: Failure observation
        assert messages[2]["role"] == "user"
        assert '<observation status="error">' in messages[2]["content"]

        # Turn 4: Corrected output with tool_call
        assert messages[3]["role"] == "assistant"
        assert '<tool_call name="write_component">' in messages[3]["content"]

        # Turn 5: Verified pass observation
        assert messages[4]["role"] == "user"
        assert '<observation status="ok">' in messages[4]["content"]

        # Turn 6: Finish action
        assert messages[5]["role"] == "assistant"
        assert "<finish>" in messages[5]["content"]


def test_zero_thought_policy(curriculum_records):
    """Verifies that zero thought or think blocks exist in assistant messages."""
    for row in curriculum_records:
        for msg in row["messages"]:
            if msg["role"] == "assistant":
                content = msg["content"]
                for tag in ("<think>", "</think>", "<thought>", "</thought>"):
                    assert tag not in content, f"Forbidden {tag} in {row['task_id']}"


def test_disjointness_against_sealed_benchmark():
    """Verifies that the interactive curriculum has 0 leaks across all 6 checks against the sealed benchmark."""
    report = audit_dataset_against_benchmark(
        dataset_path=str(OUTPUT_PATH),
        benchmark_path=str(SEALED_BENCHMARK_PATH),
        manifest_path=str(SEALED_MANIFEST_PATH),
    )
    assert report.is_clean is True
    assert report.leak_count == 0
    assert report.peak_token_similarity < report.token_threshold
    assert report.peak_semantic_similarity < report.semantic_threshold


def test_promotion_gate_blocks_when_interaction_regresses():
    """
    Verifies that model promotion is STRICTLY BLOCKED if the interaction category
    pass rate regresses, even if overall pass rate increases.
    """
    base_metrics = {
        "overall_pass_rate": 0.40,
        "typecheck_pass_rate": 0.70,
        "category_pass_rates": {
            "tsc_render_interact": 0.50,
            "tsc_and_render": 0.40,
        },
    }
    # Candidate improved overall, but regressed on interactions
    cand_metrics = {
        "overall_pass_rate": 0.45,
        "typecheck_pass_rate": 0.75,
        "category_pass_rates": {
            "tsc_render_interact": 0.35,  # Regressed from 50% to 35%
            "tsc_and_render": 0.60,
        },
    }

    decision = evaluate_promotion_gate(
        candidate_metrics=cand_metrics,
        baseline_metrics=base_metrics,
    )
    assert decision.is_eligible is False
    assert any("REGRESSED" in b for b in decision.blocking_failures)
    assert "PROMOTION BLOCKED" in decision.summary


def test_promotion_gate_blocks_when_interaction_below_threshold():
    """Verifies that model promotion is blocked if interaction pass rate is below minimum threshold."""
    cand_metrics = {
        "overall_pass_rate": 0.60,
        "typecheck_pass_rate": 0.80,
        "category_pass_rates": {
            "tsc_render_interact": 0.30,  # Below 40% threshold
            "tsc_and_render": 0.70,
        },
    }
    decision = evaluate_promotion_gate(
        candidate_metrics=cand_metrics,
        min_interaction_threshold=0.40,
    )
    assert decision.is_eligible is False
    assert any("below minimum promotion threshold" in b for b in decision.blocking_failures)


def test_promotion_gate_permits_when_criteria_satisfied():
    """Verifies that model promotion is approved when interaction pass rate and all criteria pass."""
    base_metrics = {
        "overall_pass_rate": 0.30,
        "typecheck_pass_rate": 0.60,
        "category_pass_rates": {
            "tsc_render_interact": 0.30,
            "tsc_and_render": 0.30,
        },
        "site_benchmark_metrics": {
            "composite_score_mean": 0.75,
            "overall_pass_rate": 0.80,
            "metric_means": {
                "production_build": 0.85,
                "runtime": 0.80,
                "required_section_completion": 0.85,
            },
        },
    }
    cand_metrics = {
        "overall_pass_rate": 0.45,
        "typecheck_pass_rate": 0.75,
        "category_pass_rates": {
            "tsc_render_interact": 0.48,  # Healthy gain (+18%)
            "tsc_and_render": 0.50,
        },
        "site_benchmark_metrics": {
            "composite_score_mean": 0.85,
            "overall_pass_rate": 0.90,
            "metric_means": {
                "production_build": 0.95,
                "runtime": 0.90,
                "required_section_completion": 0.95,
            },
        },
    }
    decision = evaluate_promotion_gate(
        candidate_metrics=cand_metrics,
        baseline_metrics=base_metrics,
        min_interaction_threshold=0.40,
    )
    assert decision.is_eligible is True
    assert "PROMOTION ELIGIBLE" in decision.summary


def test_compare_script_includes_promotion_gate():
    """Verifies that compare_qwen3_base_vs_sft.py integrates the promotion gate."""
    report = run_comparison(
        subset=5,
        mock=True,
        output="runs/test_promotion_gate_comparison.json",
    )
    assert "promotion_gate" in report
    promo = report["promotion_gate"]
    assert "is_eligible" in promo
    assert "interaction_pass_rate" in promo
