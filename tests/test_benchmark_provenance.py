"""
tests/test_benchmark_provenance.py - Tests for Benchmark Provenance Attestation & Promotion Gating

Verifies:
1. Benchmark reports contain the required provenance metadata schema:
   {
     "provenance": "real",
     "model_sha256": "...",
     "adapter_sha256": "...",
     "dataset_sha256": "...",
     "git_commit": "...",
     "hardware": "...",
     "mock": false
   }
2. Mock benchmarks generate "provenance": "synthetic_mock", "mock": True.
3. Promotion gate strictly rejects candidate reports when mock=True.
4. Promotion gate strictly rejects candidate reports when provenance is not "real".
5. Real benchmark evidence is eligible for promotion consideration.
"""

from pathlib import Path
import pytest

from training.provenance import (
    generate_provenance_record,
    validate_benchmark_provenance,
)
from training.methodology import evaluate_promotion_gate

ROOT = Path(__file__).resolve().parent.parent


def test_real_provenance_record_generation():
    """Verify generate_provenance_record creates schema-compliant real record."""
    rec = generate_provenance_record(
        mock=False,
        model_path=str(ROOT / "base-model"),
        adapter_path=str(ROOT / "models" / "qwen3-siteagent-r16-sft"),
    )
    assert rec["provenance"] == "real"
    assert rec["mock"] is False
    assert len(rec["model_sha256"]) == 64
    assert len(rec["adapter_sha256"]) == 64
    assert rec["git_commit"] != "unknown_commit"
    assert "hardware" in rec and len(rec["hardware"]) > 0


def test_mock_provenance_record_generation():
    """Verify mock benchmark record is explicitly tagged as mock."""
    rec = generate_provenance_record(
        mock=True,
        model_path=str(ROOT / "base-model"),
    )
    assert rec["provenance"] == "synthetic_mock"
    assert rec["mock"] is True


def test_promotion_gate_rejects_mock_candidate():
    """Verify promotion gate strictly rejects any candidate where mock != false."""
    candidate_metrics = {
        "overall_pass_rate": 0.55,
        "typecheck_pass_rate": 0.90,
        "category_pass_rates": {
            "tsc_render_interact": 0.45,
        },
        "mock": True,
        "provenance": "synthetic_mock",
        "site_benchmark_metrics": {
            "composite_score_mean": 0.85,
            "production_build_rate": 0.95,
            "runtime_pass_rate": 0.90,
            "section_completion_rate": 0.92,
            "mock": True,
        }
    }
    baseline_metrics = {
        "overall_pass_rate": 0.50,
        "typecheck_pass_rate": 0.80,
        "category_pass_rates": {
            "tsc_render_interact": 0.35,
        }
    }

    promo = evaluate_promotion_gate(
        candidate_metrics=candidate_metrics,
        baseline_metrics=baseline_metrics,
    )
    assert promo.is_eligible is False
    assert any("mock" in f.lower() for f in promo.blocking_failures)


def test_promotion_gate_rejects_non_real_provenance():
    """Verify promotion gate rejects candidate when provenance is not 'real'."""
    candidate_metrics = {
        "overall_pass_rate": 0.55,
        "typecheck_pass_rate": 0.90,
        "category_pass_rates": {
            "tsc_render_interact": 0.45,
        },
        "mock": False,
        "provenance": "synthetic_mock",
    }
    promo = evaluate_promotion_gate(
        candidate_metrics=candidate_metrics,
        baseline_metrics={"overall_pass_rate": 0.50},
        require_site_benchmark=False,
    )
    assert promo.is_eligible is False
    assert any("provenance" in f.lower() for f in promo.blocking_failures)


def test_promotion_gate_accepts_authentic_evidence():
    """Verify promotion gate accepts authentic, non-mock benchmark evidence meeting criteria."""
    candidate_metrics = {
        "overall_pass_rate": 0.55,
        "typecheck_pass_rate": 0.90,
        "category_pass_rates": {
            "tsc_render_interact": 0.45,
        },
        "mock": False,
        "provenance": "real",
        "site_benchmark_metrics": {
            "composite_score_mean": 0.85,
            "production_build_rate": 0.95,
            "runtime_pass_rate": 0.90,
            "section_completion_rate": 0.92,
            "site_diversity_score": 0.80,
            "mock": False,
            "provenance": "real",
        }
    }
    baseline_metrics = {
        "overall_pass_rate": 0.50,
        "typecheck_pass_rate": 0.80,
        "category_pass_rates": {
            "tsc_render_interact": 0.35,
        },
        "site_benchmark_metrics": {
            "composite_score_mean": 0.75,
            "production_build_rate": 0.85,
            "runtime_pass_rate": 0.80,
            "section_completion_rate": 0.85,
        }
    }

    promo = evaluate_promotion_gate(
        candidate_metrics=candidate_metrics,
        baseline_metrics=baseline_metrics,
        min_interaction_threshold=0.40,
    )
    assert promo.is_eligible is True
    assert len(promo.blocking_failures) == 0


def test_promotion_gate_rejects_missing_mock_strict():
    """Verify promotion gate strictly rejects candidate when 'mock' field is absent."""
    candidate_metrics = {
        "overall_pass_rate": 0.55,
        "typecheck_pass_rate": 0.90,
        "category_pass_rates": {"tsc_render_interact": 0.45},
        "provenance": "real",
    }
    promo = evaluate_promotion_gate(
        candidate_metrics=candidate_metrics,
        strict_provenance=True,
        require_site_benchmark=False,
    )
    assert promo.is_eligible is False
    assert any("missing mandatory 'mock' field" in f for f in promo.blocking_failures)


def test_promotion_gate_rejects_missing_provenance_strict():
    """Verify promotion gate strictly rejects candidate when 'provenance' is missing or not 'real'."""
    candidate_metrics = {
        "overall_pass_rate": 0.55,
        "typecheck_pass_rate": 0.90,
        "category_pass_rates": {"tsc_render_interact": 0.45},
        "mock": False,
    }
    promo = evaluate_promotion_gate(
        candidate_metrics=candidate_metrics,
        strict_provenance=True,
        require_site_benchmark=False,
    )
    assert promo.is_eligible is False
    assert any("provenance' must be 'real'" in f for f in promo.blocking_failures)

