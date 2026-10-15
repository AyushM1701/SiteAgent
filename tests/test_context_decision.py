"""
Tests for Issue #14: Choosing 6144 vs 8192 using data and selecting context length
from an explicit benchmark report.
"""

import json
from pathlib import Path
import subprocess
import sys
import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from training.context_decision import (
    calculate_percentiles,
    format_preflight_histogram,
    resolve_context_length,
)
from training.train_sft import train


def test_calculate_percentiles():
    lengths = [100 * i for i in range(1, 101)]
    stats = calculate_percentiles(lengths)
    assert stats["count"] == 100
    assert stats["min"] == 100
    assert stats["max"] == 10000
    assert stats["p50"] == 5100
    assert stats["p75"] == 7600
    assert stats["p90"] == 9100
    assert stats["p95"] == 9600
    assert stats["p99"] == 10000


def test_format_preflight_histogram():
    lengths = [1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000]
    out = format_preflight_histogram(lengths, [6144, 8192])
    assert "Records: 8" in out
    assert "p50   5000" in out
    assert "p75   7000" in out
    assert "Fits:" in out
    assert "6144 -> 75.0%" in out
    assert "8192 -> 100.0%" in out


def test_resolve_context_length_from_benchmark_report_8192(tmp_path):
    report_file = tmp_path / "qwen3_context_benchmark.json"
    data = {
        "6144": {"coverage": 0.95, "stable": True, "peakVramGiB": 3.2},
        "8192": {"coverage": 1.0, "stable": True, "peakVramGiB": 3.3},
        "recommendation": {
            "selected_context_length": 8192,
            "policy_decision": "choose_8192",
            "rationale": "High-value full-site trajectories require >6144 tokens.",
        }
    }
    report_file.write_text(json.dumps(data), encoding="utf-8")

    selected, info = resolve_context_length(str(report_file))
    assert selected == 8192
    assert info["policy_decision"] == "choose_8192"
    assert "High-value" in info["rationale"]


def test_resolve_context_length_from_benchmark_report_6144(tmp_path):
    report_file = tmp_path / "qwen3_context_benchmark.json"
    data = {
        "6144": {"coverage": 0.99, "stable": True, "peakVramGiB": 3.2},
        "8192": {"coverage": 1.0, "stable": False, "peakVramGiB": 5.8},
        "recommendation": {
            "selected_context_length": 6144,
            "policy_decision": "choose_6144",
            "rationale": "8192 exceeds VRAM ceiling.",
        }
    }
    report_file.write_text(json.dumps(data), encoding="utf-8")

    selected, info = resolve_context_length(str(report_file))
    assert selected == 6144
    assert info["policy_decision"] == "choose_6144"


def test_resolve_context_length_explicit_cli_override(tmp_path):
    report_file = tmp_path / "qwen3_context_benchmark.json"
    data = {
        "recommendation": {"selected_context_length": 8192, "policy_decision": "choose_8192"}
    }
    report_file.write_text(json.dumps(data), encoding="utf-8")

    selected, info = resolve_context_length(str(report_file), explicit_length=4096)
    assert selected == 4096
    assert info["source"] == "cli_argument"
    assert info["policy_decision"] == "explicit_user_override"


def test_resolve_context_length_fallback_when_report_missing(tmp_path):
    missing_file = tmp_path / "non_existent_report.json"
    selected, info = resolve_context_length(str(missing_file), default_length=8192)
    assert selected == 8192
    assert info["source"] == "default_fallback"


def test_train_sft_preflight_uses_benchmark_report_selection():
    manifest = train(preflight_only=True)
    assert manifest["status"] == "preflight_passed"
    assert manifest["max_seq_length"] == 8192
    assert "context_decision" in manifest
    assert manifest["context_decision"]["selected_context_length"] == 8192
    assert manifest["context_decision"]["policy_decision"] == "choose_8192"
    assert "sequence_length_stats" in manifest
    assert manifest["sequence_length_stats"]["fits_6144_pct"] == 95.1
    assert manifest["sequence_length_stats"]["fits_8192_pct"] == 100.0


def test_train_sft_preflight_with_custom_benchmark_report(tmp_path):
    custom_report = tmp_path / "custom_benchmark.json"
    data = {
        "recommendation": {
            "selected_context_length": 6144,
            "policy_decision": "choose_6144",
            "rationale": "Mock constraint test.",
        }
    }
    custom_report.write_text(json.dumps(data), encoding="utf-8")

    # Create a 10-row valid dataset fitting inside 6144
    dataset_file = tmp_path / "train_fit_6144.jsonl"
    with open(dataset_file, "w", encoding="utf-8") as f:
        for i in range(10):
            row = {
                "family_id": f"fam_{i}",
                "task_id": f"task_{i}",
                "messages": [
                    {"role": "user", "content": f"Build component variant {i}."},
                    {"role": "assistant", "content": "<finish></finish>"},
                ],
            }
            f.write(json.dumps(row) + "\n")

    manifest = train(
        dataset_path=str(dataset_file),
        preflight_only=True,
        benchmark_report=str(custom_report),
    )
    assert manifest["max_seq_length"] == 6144
    assert manifest["context_decision"]["selected_context_length"] == 6144
    assert manifest["context_decision"]["policy_decision"] == "choose_6144"
