"""
Unit tests for the Benchmark Leakage Guard and benchmark separation policy.
Tests all 6 mandatory leakage checks:
1. Exact prompt matching
2. Normalized matching
3. Symbol overlap
4. Token similarity
5. Family-level holdout
6. Semantic similarity checks
Plus cryptographic manifest verification and dev/sealed benchmark disjointness.
"""

import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from training.leakage_guard import (
    BenchmarkRecord,
    LeakageAuditor,
    audit_dataset_against_benchmark,
    verify_sealed_benchmark_manifest,
    compute_token_jaccard,
    compute_semantic_similarity,
    normalize_text,
    extract_symbols,
    SEALED_BENCHMARK_PATH,
    SEALED_MANIFEST_PATH,
    DEV_BENCHMARK_PATH,
)
from training.train_sft import check_benchmark_disjointness
from training.preflight import check_holdout


@pytest.fixture
def mock_benchmark_records():
    return [
        BenchmarkRecord(
            task_id="bench_001",
            prompt="Write a React TypeScript component `Tooltip` that wraps its children and shows a `content: string` on hover after a configurable `delayMs`.",
            check="tsc_render_interact",
            family_id="family_tooltip",
            source_task_id="src_tooltip_01",
        ),
        BenchmarkRecord(
            task_id="bench_002",
            prompt="Build a compound `Tabs` component using React Context, supporting controlled activeKey and uncontrolled defaultActiveKey.",
            check="tsc_render_interact",
            family_id="family_tabs",
            source_task_id="src_tabs_01",
        ),
    ]


def test_check_1_exact_prompt_matching(mock_benchmark_records):
    """Verifies that an exact prompt match is detected and flagged."""
    auditor = LeakageAuditor(mock_benchmark_records)
    prompt = "Write a React TypeScript component `Tooltip` that wraps its children and shows a `content: string` on hover after a configurable `delayMs`."
    violations, _, _ = auditor.audit_prompt(prompt, "candidate_exact")
    assert any(v.check_type == "exact_prompt_matching" for v in violations)


def test_check_2_normalized_matching(mock_benchmark_records):
    """Verifies that punctuation, casing, and whitespace evasion is caught."""
    auditor = LeakageAuditor(mock_benchmark_records)
    # Alter casing, add extra spaces and punctuation
    prompt = "  WRITE a React typescript COMPONENT tooltip   that wraps its children AND shows a content string ON hover after a configurable delayMs!!  "
    violations, _, _ = auditor.audit_prompt(prompt, "candidate_normalized")
    assert any(v.check_type == "normalized_matching" for v in violations)


def test_check_3_symbol_overlap(mock_benchmark_records):
    """Verifies that shared symbols coupled with moderate similarity are caught."""
    auditor = LeakageAuditor(mock_benchmark_records, symbol_overlap_threshold=0.30)
    # Uses `Tooltip`, `delayMs`, and related phrasing
    prompt = "Write a React TypeScript component `Tooltip` with `delayMs` timing for hover state."
    violations, _, _ = auditor.audit_prompt(prompt, "candidate_symbol")
    assert any(v.check_type == "symbol_overlap" for v in violations)


def test_check_4_token_similarity(mock_benchmark_records):
    """Verifies that high token Jaccard similarity is caught."""
    auditor = LeakageAuditor(mock_benchmark_records, token_similarity_threshold=0.45)
    # High token overlap with bench_002 without using the exact symbol
    prompt = "Build a compound navigation component using React Context supporting controlled activeKey and uncontrolled defaultActiveKey."
    violations, t_sim, _ = auditor.audit_prompt(prompt, "candidate_token")
    assert t_sim >= 0.45
    assert any(v.check_type == "token_similarity" for v in violations)


def test_check_5_family_level_holdout(mock_benchmark_records):
    """Verifies that family_id, source_task_id, and task_id collisions are caught."""
    auditor = LeakageAuditor(mock_benchmark_records)
    # Totally disjoint prompt text, but matching family_id
    prompt = "Completely different unrelated component prompt."
    violations, _, _ = auditor.audit_prompt(prompt, "cand_fam", family_id="family_tooltip")
    assert any(v.check_type == "family_level_holdout" for v in violations)

    # Matching source_task_id
    violations2, _, _ = auditor.audit_prompt(prompt, "cand_src", source_task_id="src_tabs_01")
    assert any(v.check_type == "family_level_holdout" for v in violations2)


def test_check_6_semantic_similarity(mock_benchmark_records):
    """Verifies that paraphrased prompts are caught by semantic similarity checks."""
    auditor = LeakageAuditor(mock_benchmark_records, semantic_similarity_threshold=0.60)
    # Paraphrased version of bench_001
    prompt = "Write a React TypeScript Tooltip component wrapping children to display content: string on hover given delayMs."
    violations, _, s_sim = auditor.audit_prompt(prompt, "candidate_semantic")
    assert s_sim >= 0.60
    assert any(v.check_type == "semantic_similarity_checks" for v in violations)


def test_disjoint_prompt_passes_all_checks(mock_benchmark_records):
    """Verifies that a genuinely clean, disjoint prompt produces 0 violations."""
    auditor = LeakageAuditor(mock_benchmark_records)
    clean_prompt = "Build a CanvasAudioVisualizer taking audioStream: MediaStream and rendering dynamic frequency bars using requestAnimationFrame."
    violations, t_sim, s_sim = auditor.audit_prompt(clean_prompt, "clean_sample")
    assert len(violations) == 0
    assert t_sim < 0.30
    assert s_sim < 0.30


def test_sealed_benchmark_manifest_integrity():
    """Verifies that the canonical sealed benchmark passes manifest verification."""
    result = verify_sealed_benchmark_manifest(
        str(SEALED_BENCHMARK_PATH),
        str(SEALED_MANIFEST_PATH),
    )
    assert result["status"] == "sealed_valid"
    assert result["task_count"] == 153


def test_sealed_benchmark_manifest_detects_tampering(tmp_path):
    """Verifies that modifying the sealed benchmark causes manifest verification failure."""
    fake_bench = tmp_path / "tampered_bench.jsonl"
    fake_bench.write_text('{"task_id":"t1","prompt":"tampered"}\n', encoding="utf-8")
    with pytest.raises(RuntimeError, match="SEALED BENCHMARK INTEGRITY VIOLATION"):
        verify_sealed_benchmark_manifest(str(fake_bench), str(SEALED_MANIFEST_PATH))


def test_dev_benchmark_is_strictly_disjoint():
    """
    Verifies that the official Development Benchmark (dev_benchmark.jsonl)
    has zero leaks across all 6 checks against the Sealed Final Benchmark.
    """
    report = audit_dataset_against_benchmark(
        dataset_path=str(DEV_BENCHMARK_PATH),
        benchmark_path=str(SEALED_BENCHMARK_PATH),
        manifest_path=str(SEALED_MANIFEST_PATH),
    )
    assert report.is_clean is True
    assert report.leak_count == 0
    assert report.total_candidate_samples == 150
    assert report.total_benchmark_tasks == 153
    assert report.peak_token_similarity < report.token_threshold
    assert report.peak_semantic_similarity < report.semantic_threshold


def test_check_benchmark_disjointness_catches_leak(tmp_path):
    """Verifies that check_benchmark_disjointness fails closed on leak injection."""
    eval_file = tmp_path / "eval.jsonl"
    eval_file.write_text(
        json.dumps({"task_id": "b1", "prompt": "Write a unique test component FooBar."}) + "\n",
        encoding="utf-8",
    )
    train_file = tmp_path / "train_leak.jsonl"
    train_file.write_text(
        json.dumps({
            "task_id": "t1",
            "messages": [
                {"role": "user", "content": "Write a unique test component FooBar."},
                {"role": "assistant", "content": "<finish>Done</finish>"}
            ]
        }) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="Pre-flight data integrity check FAILED"):
        check_benchmark_disjointness(str(train_file), str(eval_file))


def test_cli_verify_benchmark_leakage_tool():
    """Verifies that scripts/verify_benchmark_leakage.py runs successfully via CLI."""
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "verify_benchmark_leakage.py"),
        "--dataset", str(DEV_BENCHMARK_PATH),
        "--benchmark", str(SEALED_BENCHMARK_PATH),
        "--manifest", str(SEALED_MANIFEST_PATH),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT))
    assert res.returncode == 0
    assert "RESULT: PASSED (0 Leaks Detected)" in res.stdout
