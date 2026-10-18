import os
import tempfile

# Sessions created by tests must never appear in the user's workbench project list.
os.environ.setdefault("SLM_SESSIONS_DIR", tempfile.mkdtemp(prefix="slm_test_sessions_"))
# Importing server.app must not load the 4B model onto the GPU during tests.
os.environ.setdefault("NO_AUTO_LOAD_MODEL", "1")

import pytest
from agent.agent_protocol import get_default_tokenizer, set_default_tokenizer


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
