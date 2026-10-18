import os
import tempfile

# Sessions created by tests must never appear in the user's workbench project list.
os.environ.setdefault("SLM_SESSIONS_DIR", tempfile.mkdtemp(prefix="slm_test_sessions_"))
# Importing server.app must not load the 4B model onto the GPU during tests.
os.environ.setdefault("NO_AUTO_LOAD_MODEL", "1")
# Context-length expectations must not depend on the GPU of the machine running tests.
os.environ.setdefault("SLM_HARDWARE_CONTEXT", "0")

from pathlib import Path

import pytest
from agent.agent_protocol import get_default_tokenizer, set_default_tokenizer

_ROOT = Path(__file__).resolve().parent.parent
_HAS_BASE_MODEL = (_ROOT / "base-model" / "config.json").is_file() and (_ROOT / "base-model" / "tokenizer.json").is_file()
_HAS_LOCAL_RUNS = ((_ROOT / "models").is_dir() and (_ROOT / "runs").is_dir()
                   and (_ROOT / "data" / "full_site_training" / "train.jsonl").is_file())

# Tests that read the downloaded Qwen3-4B files (config, tokenizer, weights).
_NEEDS_BASE_MODEL = (
    "tests/test_base_model_fingerprint.py",
    "tests/test_benchmark_provenance.py::test_real_provenance_record_generation",
    "tests/test_context_decision.py::test_train_sft_preflight",
    "tests/test_execute_qwen3_migration.py",
    "tests/test_single_source_context_length.py::test_training_preflight_respects_slm_context_length_env",
    "tests/test_training_methodology.py::test_train_sft_preflight_enforces_methodology_guard",
    "tests/test_training_preflight.py",
    "tests/test_clean_qwen3_training_data.py::test_preflight_strictly_rejects_think_and_thought_tags",
    "tests/test_clean_qwen3_training_data.py::test_cleaned_row_passes_training_preflight",
)
# Tests that inspect training outputs and evidence produced on the original machine.
_NEEDS_LOCAL_RUNS = (
    "tests/test_retrain_qwen3_scratch.py",
    "tests/test_p1_quality_contracts.py::test_visual_holdout_is_distinct_from_training",
    "tests/test_qwen3_benchmark.py::test_run_benchmark_mock_generates_valid_report",
    "tests/test_qwen3_benchmark.py::test_cli_execution_with_mock",
    "tests/test_reference_curriculum.py::ReferenceCurriculumTests::test_stale_visual_evidence_blocks_publication",
)


def pytest_collection_modifyitems(config, items):
    """Skip, with a reason, tests that need the 8 GB model or local training runs
    when they are absent (a fresh clone or CI)."""
    no_model = pytest.mark.skip(reason="needs ./base-model (python scripts/download_models.py)")
    no_runs = pytest.mark.skip(reason="needs local training runs in ./models and ./runs")
    legacy_ui = pytest.mark.skip(reason="needs the legacy web_ui_static/index.monolith.html.bak")
    for item in items:
        nodeid = item.nodeid.replace("\\", "/")
        if not _HAS_BASE_MODEL and nodeid.startswith(_NEEDS_BASE_MODEL):
            item.add_marker(no_model)
        elif not _HAS_LOCAL_RUNS and nodeid.startswith(_NEEDS_LOCAL_RUNS):
            item.add_marker(no_runs)
        elif nodeid.endswith("test_markdown_link_scheme_allowlist") and \
                not (_ROOT / "web_ui_static" / "index.monolith.html.bak").exists():
            item.add_marker(legacy_ui)


@pytest.fixture(autouse=True)
def isolate_default_tokenizer():
    """Ensure the global _DEFAULT_TOKENIZER does not leak across test boundaries."""
    orig = get_default_tokenizer()
    yield
    set_default_tokenizer(orig)


def write_real_context_report(path, selected=8192, decision="choose_8192",
                              rationale="Full-site trajectories need more than 6144 tokens."):
    """A context benchmark report shaped like a real (mock=false) execution.

    training.context_decision refuses synthetic or incomplete reports, so tests
    that exercise training preflight supply one explicitly."""
    import json
    report = {
        "provenance": "real",
        "mock": False,
        "model_sha256": "0" * 64,
        "environment": {"model": "Qwen/Qwen3-4B", "model_path": "base-model"},
        "recommendation": {"selected_context_length": selected, "policy_decision": decision, "rationale": rationale},
    }
    path.write_text(json.dumps(report), encoding="utf-8")
    return str(path)


@pytest.fixture
def real_context_report(tmp_path):
    return write_real_context_report(tmp_path / "qwen3_context_benchmark.json")
