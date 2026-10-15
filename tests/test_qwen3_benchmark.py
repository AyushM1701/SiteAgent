"""
Tests for scripts/benchmark_qwen3.py:
Verifies context-length benchmarking, sequence distribution metrics,
deterministic recommendation policies, and JSON report generation.
"""

import json
from pathlib import Path
import subprocess
import sys
import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from scripts.benchmark_qwen3 import (
    calculate_sequence_stats,
    analyze_dataset_coverage,
    make_recommendation,
    run_benchmark,
    bytes_to_gib,
    VRAM_CEILING_GIB,
)


def test_bytes_to_gib():
    assert bytes_to_gib(1024 ** 3) == 1.0
    assert bytes_to_gib(0) == 0.0
    assert round(bytes_to_gib(6 * 1024 ** 3), 2) == 6.0


def test_calculate_sequence_stats():
    # 100 lengths: 1..100
    lengths = list(range(1, 101))
    stats = calculate_sequence_stats(lengths)
    assert stats["count"] == 100
    assert stats["min"] == 1
    assert stats["max"] == 100
    assert stats["mean"] == 50.5
    assert stats["p50"] == 51
    assert stats["p75"] == 76
    assert stats["p90"] == 91
    assert stats["p95"] == 96
    assert stats["p99"] == 100


def test_calculate_sequence_stats_empty():
    stats = calculate_sequence_stats([])
    assert stats["count"] == 0
    assert stats["p50"] == 0


def test_analyze_dataset_coverage_synthetic(tmp_path):
    # Create a small dataset with known message lengths
    dataset_file = tmp_path / "train.jsonl"
    rows = [
        {"messages": [{"role": "user", "content": "hello"}, {"role": "assistant", "content": "<finish>Done</finish>"}]},
        {"messages": [{"role": "user", "content": "hi again"}, {"role": "assistant", "content": "<finish>Done</finish>"}]},
    ]
    with open(dataset_file, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")

    seq_stats, context_coverage = analyze_dataset_coverage(str(dataset_file), [6144, 8192])
    assert seq_stats["count"] == 2
    assert 6144 in context_coverage
    assert 8192 in context_coverage
    assert context_coverage[6144]["coverage"] == 1.0
    assert context_coverage[8192]["coverage"] == 1.0


def test_make_recommendation_selects_8192_when_tail_needs_it():
    context_results = {
        "6144": {
            "coverage": 0.96,  # 4% exceed 6144
            "peakVramGiB": 3.13,
            "tokensPerSecond": 550.0,
            "stable": True,
            "oom": False,
            "shared_memory_spill": False,
        },
        "8192": {
            "coverage": 1.0,
            "peakVramGiB": 3.28,
            "tokensPerSecond": 720.0,
            "stable": True,
            "oom": False,
            "shared_memory_spill": False,
        },
    }
    seq_stats = {"max": 7112, "p99": 6591, "p95": 6045}
    rec = make_recommendation(context_results, seq_stats, ceiling_gib=5.5)

    assert rec["selected_context_length"] == 8192
    assert rec["policy_decision"] == "choose_8192"
    assert "7112" in rec["rationale"]
    assert "8192 trains stably" in rec["rationale"]


def test_make_recommendation_selects_6144_when_8192_exceeds_ceiling():
    context_results = {
        "6144": {
            "coverage": 0.96,
            "peakVramGiB": 4.80,
            "tokensPerSecond": 500.0,
            "stable": True,
            "oom": False,
            "shared_memory_spill": False,
        },
        "8192": {
            "coverage": 1.0,
            "peakVramGiB": 5.85,  # Exceeds 5.5 GiB ceiling!
            "tokensPerSecond": 420.0,
            "stable": False,
            "oom": False,
            "shared_memory_spill": True,
        },
    }
    seq_stats = {"max": 7112}
    rec = make_recommendation(context_results, seq_stats, ceiling_gib=5.5)

    assert rec["selected_context_length"] == 6144
    assert rec["policy_decision"] == "choose_6144"
    assert "exceeds" in rec["rationale"]


def test_make_recommendation_selects_6144_when_8192_ooms():
    context_results = {
        "6144": {
            "coverage": 0.96,
            "peakVramGiB": 3.50,
            "tokensPerSecond": 500.0,
            "stable": True,
            "oom": False,
            "shared_memory_spill": False,
        },
        "8192": {
            "coverage": 1.0,
            "peakVramGiB": 6.0,
            "tokensPerSecond": 0.0,
            "stable": False,
            "oom": True,
            "shared_memory_spill": False,
        },
    }
    seq_stats = {"max": 7112}
    rec = make_recommendation(context_results, seq_stats, ceiling_gib=5.5)

    assert rec["selected_context_length"] == 6144
    assert rec["policy_decision"] == "choose_6144"


def test_make_recommendation_selects_6144_when_98pct_fits_and_8192_slow():
    context_results = {
        "6144": {
            "coverage": 0.995,  # 99.5% fits
            "peakVramGiB": 3.10,
            "tokensPerSecond": 600.0,
            "stable": True,
            "oom": False,
            "shared_memory_spill": False,
        },
        "8192": {
            "coverage": 1.0,
            "peakVramGiB": 5.30,  # High VRAM pressure
            "tokensPerSecond": 350.0,  # >35% slower
            "stable": True,
            "oom": False,
            "shared_memory_spill": False,
        },
    }
    seq_stats = {"max": 6200}
    rec = make_recommendation(context_results, seq_stats, ceiling_gib=5.5)

    assert rec["selected_context_length"] == 6144
    assert rec["policy_decision"] == "choose_6144"
    assert "6144" in rec["rationale"]


def test_make_recommendation_insufficient_vram():
    context_results = {
        "6144": {
            "coverage": 0.95,
            "peakVramGiB": 5.7,
            "tokensPerSecond": 0.0,
            "stable": False,
            "oom": True,
            "shared_memory_spill": True,
        },
        "8192": {
            "coverage": 1.0,
            "peakVramGiB": 6.2,
            "tokensPerSecond": 0.0,
            "stable": False,
            "oom": True,
            "shared_memory_spill": True,
        },
    }
    seq_stats = {"max": 7112}
    rec = make_recommendation(context_results, seq_stats, ceiling_gib=5.5)

    assert rec["selected_context_length"] is None
    assert rec["policy_decision"] == "insufficient_vram"


def test_run_benchmark_mock_generates_valid_report(tmp_path):
    output_file = tmp_path / "test_report.json"
    report = run_benchmark(
        context_lengths=[6144, 8192],
        output_path=str(output_file),
        mock=True,
    )

    assert output_file.exists()
    disk_data = json.loads(output_file.read_text(encoding="utf-8"))

    # Verify example JSON schema:
    # {
    #   "6144": { "coverage": ..., "peakVramGiB": ..., "tokensPerSecond": ..., "stable": ... },
    #   "8192": { "coverage": ..., "peakVramGiB": ..., "tokensPerSecond": ..., "stable": ... }
    # }
    for ctx in ["6144", "8192"]:
        assert ctx in disk_data
        entry = disk_data[ctx]
        assert "coverage" in entry
        assert "peakVramGiB" in entry
        assert "tokensPerSecond" in entry
        assert "stable" in entry
        assert "p50_tokens" in entry
        assert "maximum_tokens" in entry
        assert "forward_stability" in entry
        assert "backward_stability" in entry
        assert "oom" in entry
        assert "shared_memory_spill" in entry
        assert "vram_headroom_gib" in entry

    # Recommendation
    assert "recommendation" in disk_data
    rec = disk_data["recommendation"]
    assert rec["selected_context_length"] in [6144, 8192]
    assert rec["policy_decision"] in ["choose_6144", "choose_8192"]
    assert len(rec["rationale"]) > 10

    # Environment
    assert "environment" in disk_data
    env = disk_data["environment"]
    assert "qlora_configuration" in env
    assert env["qlora_configuration"]["rank"] == 16
    assert env["qlora_configuration"]["load_in_4bit"] is True

    # Sequence distribution
    assert "sequence_distribution" in disk_data
    dist = disk_data["sequence_distribution"]
    assert dist["p50"] > 0
    assert dist["max"] >= dist["p99"]


def test_cli_execution_with_mock(tmp_path):
    output_file = tmp_path / "cli_report.json"
    cmd = [
        sys.executable,
        str(BASE_DIR / "scripts" / "benchmark_qwen3.py"),
        "--mock",
        "--output",
        str(output_file),
    ]
    res = subprocess.run(cmd, cwd=str(BASE_DIR), capture_output=True, text=True)
    assert res.returncode == 0, f"Benchmark failed: {res.stderr}"
    assert output_file.exists()
    assert "QWEN3 CONTEXT BENCHMARK" in res.stdout
    assert "Deterministic Recommendation:" in res.stdout
    assert "Fits:" in res.stdout
    assert "6144 ->" in res.stdout
    assert "8192 ->" in res.stdout
