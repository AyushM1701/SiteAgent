"""
tests/test_single_source_context_length.py - Comprehensive Tests for Single Source of Truth Context Length

Verifies:
1. ModelRuntimeConfig as the authoritative single source of truth:
   - Reading and setting ModelRuntimeConfig.max_seq_length
   - Precedence order: explicit override -> SLM_CONTEXT_LENGTH env var -> benchmark report -> 8192 fallback
2. ContextBuilder and TokenBudget synchronization:
   - Changing context length in one place automatically updates TokenBudget and ContextBuilder
   - Proportional slice scaling when context length changes (e.g. 6144 vs 8192)
   - Sum of slices always equals total budget
3. Training & Preflight integration:
   - resolve_context_length and train_sft.py preflight respect SLM_CONTEXT_LENGTH and ModelRuntimeConfig
4. Inference & Server integration:
   - AgentModelRunner defaults to ModelRuntimeConfig
   - /api/status and connection.ready emit authoritative max_context_tokens
5. Token counting & validation:
   - Final prompt validation uses real tokenizer
   - Enforces prompt_tokens + max_new_tokens <= max_seq_length
   - Clamping dynamically restricts max_new_tokens without error unless prompt_tokens >= max_seq_length
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import torch

from agent.config import ModelRuntimeConfig
from agent.context_builder import ContextBuilder, TokenBudget
from agent.agent import AgentModelRunner
from server.sessions import Session
from training.context_decision import resolve_context_length
from training.train_sft import train


@pytest.fixture(autouse=True)
def reset_runtime_config():
    """Ensure clean state before and after each test."""
    ModelRuntimeConfig.reset()
    orig_env = os.environ.get("SLM_CONTEXT_LENGTH")
    yield
    ModelRuntimeConfig.reset()
    if orig_env is not None:
        os.environ["SLM_CONTEXT_LENGTH"] = orig_env
    else:
        os.environ.pop("SLM_CONTEXT_LENGTH", None)


# ── 1. ModelRuntimeConfig Precedence & Resolution ────────────────────────────

def test_model_runtime_config_precedence():
    # 1. Fallback when nothing set (or benchmark report if present)
    ModelRuntimeConfig.reset()
    os.environ.pop("SLM_CONTEXT_LENGTH", None)
    default_or_bench = ModelRuntimeConfig.get_max_seq_length()
    assert default_or_bench in (6144, 8192)

    # 2. SLM_CONTEXT_LENGTH env var overrides benchmark/default
    os.environ["SLM_CONTEXT_LENGTH"] = "6144"
    assert ModelRuntimeConfig.get_max_seq_length() == 6144
    assert ModelRuntimeConfig.max_seq_length == 6144

    os.environ["SLM_CONTEXT_LENGTH"] = "4096"
    assert ModelRuntimeConfig.get_max_seq_length() == 4096

    # 3. Explicit code override takes highest precedence
    ModelRuntimeConfig.max_seq_length = 5120
    assert ModelRuntimeConfig.max_seq_length == 5120

    # Reset clears explicit override back to env var
    ModelRuntimeConfig.reset()
    assert ModelRuntimeConfig.max_seq_length == 4096

    os.environ.pop("SLM_CONTEXT_LENGTH", None)
    ModelRuntimeConfig.reset()


# ── 2. ContextBuilder & TokenBudget Auto-Scaling ─────────────────────────────

def test_token_budget_auto_scales_with_runtime_config():
    # When context length is 8192
    ModelRuntimeConfig.max_seq_length = 8192
    budget_8192 = TokenBudget()
    assert budget_8192.total == 8192
    assert budget_8192.system_contracts == 1000
    assert budget_8192.current_instruction == 300
    assert budget_8192.project_metadata == 300
    assert budget_8192.selected_files == 3000
    assert budget_8192.related_files == 1600
    assert budget_8192.recent_conversation == 900
    assert budget_8192.build_diagnostics == 700
    assert budget_8192.reserve == 392
    assert (
        budget_8192.system_contracts
        + budget_8192.current_instruction
        + budget_8192.project_metadata
        + budget_8192.selected_files
        + budget_8192.related_files
        + budget_8192.recent_conversation
        + budget_8192.build_diagnostics
        + budget_8192.reserve
    ) == 8192

    # When context length is changed to 6144
    ModelRuntimeConfig.max_seq_length = 6144
    budget_6144 = TokenBudget()
    assert budget_6144.total == 6144
    assert budget_6144.system_contracts == 750
    assert budget_6144.current_instruction == 225
    assert budget_6144.project_metadata == 225
    assert budget_6144.selected_files == 2250
    assert budget_6144.related_files == 1200
    assert budget_6144.recent_conversation == 675
    assert budget_6144.build_diagnostics == 525
    assert budget_6144.reserve == 294
    assert (
        budget_6144.system_contracts
        + budget_6144.current_instruction
        + budget_6144.project_metadata
        + budget_6144.selected_files
        + budget_6144.related_files
        + budget_6144.recent_conversation
        + budget_6144.build_diagnostics
        + budget_6144.reserve
    ) == 6144


def test_context_builder_dynamically_tracks_runtime_config():
    builder = ContextBuilder()

    ModelRuntimeConfig.max_seq_length = 8192
    assert builder.budget.total == 8192

    # Changing context length in one place immediately updates builder
    ModelRuntimeConfig.max_seq_length = 6144
    assert builder.budget.total == 6144
    assert builder.budget.selected_files == 2250

    # Updating via environment variable also immediately updates builder
    ModelRuntimeConfig.reset()
    os.environ["SLM_CONTEXT_LENGTH"] = "4096"
    assert builder.budget.total == 4096


# ── 3. Real Tokenizer Prompt Validation & Enforcement ────────────────────────

def test_context_builder_real_tokenizer_validation_and_pruning():
    ModelRuntimeConfig.max_seq_length = 2048
    builder = ContextBuilder()

    # Large target files and history
    large_ts = "import React from 'react';\n" + "\n".join(f"export const item{i} = {i};" for i in range(1200))
    session = Session(session_id="1789000000_123456", title="TestApp")

    built = builder.build_context(
        session=session,
        new_instruction="Update component styling",
        target_files=[("src/App.tsx", large_ts)],
        diagnostics=None,
    )

    # Real tokenizer was used and total usage never exceeds the 2048 budget
    assert built.token_usage.total <= 2048
    real_counted = ModelRuntimeConfig.count_tokens(built.prompt_text)
    assert real_counted + built.budget.system_contracts <= 2048


# ── 4. Training & Preflight Single Source of Truth ───────────────────────────

def test_training_preflight_respects_slm_context_length_env(tmp_path):
    os.environ["SLM_CONTEXT_LENGTH"] = "6144"

    # Minimal dataset fitting inside 6144
    dataset_file = tmp_path / "train_preflight_env.jsonl"
    with open(dataset_file, "w", encoding="utf-8") as f:
        for i in range(10):
            row = {
                "family_id": f"fam_{i}",
                "task_id": f"task_{i}",
                "messages": [
                    {"role": "user", "content": f"Create widget {i}."},
                    {"role": "assistant", "content": f"<finish>Done {i}</finish>"},
                ],
            }
            f.write(json.dumps(row) + "\n")

    manifest = train(
        dataset_path=str(dataset_file),
        preflight_only=True,
    )
    assert manifest["max_seq_length"] == 6144
    assert manifest["context_decision"]["selected_context_length"] == 6144
    assert manifest["context_decision"]["source"] == "environment_variable"


def test_resolve_context_length_respects_model_runtime_config():
    ModelRuntimeConfig.max_seq_length = 6144
    selected, info = resolve_context_length()
    assert selected == 6144
    assert info["source"] == "model_runtime_config"


# ── 5. Generation Max-Token Clamping: prompt + max_new <= max_seq ────────────

def test_clamp_max_new_tokens_enforces_context_budget():
    ModelRuntimeConfig.max_seq_length = 6144

    # 1. Normal case: plenty of headroom
    clamped = ModelRuntimeConfig.clamp_max_new_tokens(prompt_tokens=2000, requested_max_new_tokens=1024)
    assert clamped == 1024
    assert 2000 + clamped <= 6144

    # 2. Clamping case: prompt + requested > max_seq
    # 5500 + 1024 > 6144 -> clamp to 6144 - 5500 = 644
    clamped = ModelRuntimeConfig.clamp_max_new_tokens(prompt_tokens=5500, requested_max_new_tokens=1024)
    assert clamped == 644
    assert 5500 + clamped == 6144

    # 3. Tight border case: prompt is 6143
    clamped = ModelRuntimeConfig.clamp_max_new_tokens(prompt_tokens=6143, requested_max_new_tokens=500)
    assert clamped == 1
    assert 6143 + clamped == 6144

    # 4. Overflow case: prompt >= max_seq -> raises ValueError
    with pytest.raises(ValueError) as excinfo:
        ModelRuntimeConfig.clamp_max_new_tokens(prompt_tokens=6144, requested_max_new_tokens=100)
    assert "exceeds or equals" in str(excinfo.value)

    with pytest.raises(ValueError):
        ModelRuntimeConfig.clamp_max_new_tokens(prompt_tokens=7000, requested_max_new_tokens=100)


def test_agent_model_runner_clamping_enforcement():
    ModelRuntimeConfig.max_seq_length = 100
    runner = AgentModelRunner(model_path="dummy", is_mock=True)
    assert runner.max_seq_length == 100

    # Case A: max_new_tokens >= max_seq_length raises ValueError
    with pytest.raises(ValueError) as exc:
        runner.generate_turn(example_idx=0, history=[], primary_symbol="Button", max_new_tokens=100)
    assert "must be less than max_seq_length" in str(exc.value)

    # Case B: Prompt exceeds max_seq_length raises ValueError
    huge_history = [
        {"role": "system", "content": "You are an assistant."},
        {"role": "user", "content": "word " * 300},
    ]
    with pytest.raises(ValueError) as exc:
        runner.generate_turn(example_idx=0, history=huge_history, primary_symbol="Button", max_new_tokens=10)
    assert "exceeds" in str(exc.value)

    # Case C: Valid prompt and tokens run and self-correct/generate
    valid_history = [
        {"role": "system", "content": "You are a coding agent."},
        {"role": "user", "content": "Write Button"},
    ]
    out = runner.generate_turn(example_idx=0, history=valid_history, primary_symbol="Button", max_new_tokens=20)
    assert "Button" in out


# ── 6. Server Status Endpoint Emission ───────────────────────────────────────

def test_server_status_emits_authoritative_context_length():
    from server.app import app

    ModelRuntimeConfig.max_seq_length = 6144
    client = app.test_client()
    resp = client.get("/api/status")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["max_context_tokens"] == 6144
    assert data["maxContextTokens"] == 6144
