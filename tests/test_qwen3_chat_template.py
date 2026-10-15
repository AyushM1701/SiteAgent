"""
tests/test_qwen3_chat_template.py - Tests for Qwen3 Native Chat Template Path (Issue #16)

Verifies:
1. Qwen3-native chat template is the primary path:
   - When tokenizer is registered, format_chatml delegates to apply_chat_template(..., enable_thinking=False)
2. Tokenizer registration via registry (set_default_tokenizer, register_tokenizer, ModelRuntimeConfig):
   - Setting and retrieving default tokenizer
3. enable_thinking=False disables Qwen3 native <think> blocks:
   - Handles TypeError gracefully for older tokenizers without enable_thinking kwarg
4. Output scrubber for accidental <think> blocks:
   - scrub_think_blocks removes <think>...</think> blocks from raw outputs
   - parse_agent_output automatically applies scrub_think_blocks
5. Retain hardcoded ChatML fallback only when no tokenizer is registered:
   - Offline tests and data inspection before tokenizer load fall back to valid ChatML
6. Training and inference use the exact same tokenizer / template path:
   - Both delegate through format_chatml with the registered Qwen3 tokenizer
"""

import os
import re
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from agent.agent_protocol import (
    AGENT_SYSTEM_PROMPT,
    format_chatml,
    get_default_tokenizer,
    parse_agent_output,
    register_tokenizer,
    scrub_think_blocks,
    set_default_tokenizer,
    WriteComponentAction,
    WriteSiteAction,
)
from agent.config import ModelRuntimeConfig


@pytest.fixture(autouse=True)
def restore_tokenizer_registry():
    """Ensure tokenizer registry is restored after each test."""
    orig_tok = get_default_tokenizer()
    yield
    set_default_tokenizer(orig_tok)


class MockQwen3Tokenizer:
    """Mock HuggingFace tokenizer exposing apply_chat_template with enable_thinking support."""

    def __init__(self):
        self.last_kwargs = {}
        self.eos_token = "<|im_end|>"
        self.eos_token_id = 151645

    def apply_chat_template(
        self,
        messages,
        tokenize=False,
        add_generation_prompt=True,
        enable_thinking=False,
        **kwargs,
    ):
        self.last_kwargs = {
            "tokenize": tokenize,
            "add_generation_prompt": add_generation_prompt,
            "enable_thinking": enable_thinking,
            **kwargs,
        }
        lines = []
        for m in messages:
            lines.append(f"<|im_start|>{m['role']}\n{m['content'].strip()}<|im_end|>")
        out = "\n".join(lines) + "\n"
        if add_generation_prompt:
            out += "<|im_start|>assistant\n"
        return out


class MockLegacyTokenizer:
    """Mock tokenizer that raises TypeError when enable_thinking kwarg is passed."""

    def __init__(self):
        self.last_kwargs = {}

    def apply_chat_template(
        self,
        messages,
        tokenize=False,
        add_generation_prompt=True,
        **kwargs,
    ):
        if "enable_thinking" in kwargs:
            raise TypeError("unexpected keyword argument 'enable_thinking'")
        self.last_kwargs = {
            "tokenize": tokenize,
            "add_generation_prompt": add_generation_prompt,
            **kwargs,
        }
        lines = []
        for m in messages:
            lines.append(f"<|im_start|>{m['role']}\n{m['content'].strip()}<|im_end|>")
        out = "\n".join(lines) + "\n"
        if add_generation_prompt:
            out += "<|im_start|>assistant\n"
        return out


# ── 1. Primary Qwen3 Native Template Path ─────────────────────────────────────

def test_qwen3_native_template_called_with_enable_thinking_false():
    mock_tok = MockQwen3Tokenizer()
    set_default_tokenizer(mock_tok)

    messages = [
        {"role": "system", "content": "You are an agent."},
        {"role": "user", "content": "Write Button"},
    ]
    prompt = format_chatml(messages, add_generation_prompt=True)

    # Verify apply_chat_template was called with enable_thinking=False
    assert mock_tok.last_kwargs["enable_thinking"] is False
    assert mock_tok.last_kwargs["tokenize"] is False
    assert mock_tok.last_kwargs["add_generation_prompt"] is True
    assert "<|im_start|>system\nYou are an agent.<|im_end|>" in prompt
    assert prompt.endswith("<|im_start|>assistant\n")


def test_qwen3_template_handles_legacy_tokenizer_gracefully():
    mock_tok = MockLegacyTokenizer()
    set_default_tokenizer(mock_tok)

    messages = [
        {"role": "user", "content": "Hello"},
    ]
    prompt = format_chatml(messages, add_generation_prompt=True)
    assert mock_tok.last_kwargs["tokenize"] is False
    assert "<|im_start|>user\nHello<|im_end|>" in prompt


# ── 2. Tokenizer Registration API ─────────────────────────────────────────────

def test_tokenizer_registration_and_retrieval():
    mock_tok = MockQwen3Tokenizer()

    # set_default_tokenizer and register_tokenizer alias
    set_default_tokenizer(mock_tok)
    assert get_default_tokenizer() is mock_tok

    register_tokenizer(mock_tok)
    assert get_default_tokenizer() is mock_tok

    # ModelRuntimeConfig integration
    ModelRuntimeConfig.register_tokenizer(mock_tok)
    assert ModelRuntimeConfig.get_tokenizer() is mock_tok


# ── 3. Hardcoded ChatML Fallback for Offline Tests & Pre-Load Inspection ──────

def test_hardcoded_chatml_fallback_when_no_tokenizer_registered():
    set_default_tokenizer(None)
    assert get_default_tokenizer() is None

    messages = [
        {"role": "system", "content": "Test system prompt"},
        {"role": "user", "content": "Test user prompt"},
    ]
    prompt = format_chatml(messages, add_generation_prompt=True)

    # Emits valid ChatML even without any loaded tokenizer
    assert "<|im_start|>system\nTest system prompt<|im_end|>" in prompt
    assert "<|im_start|>user\nTest user prompt<|im_end|>" in prompt
    assert prompt.endswith("\n<|im_start|>assistant\n")

    # Without generation prompt
    prompt_no_gen = format_chatml(messages, add_generation_prompt=False)
    assert not prompt_no_gen.endswith("<|im_start|>assistant\n")


# ── 4. Accidental <think> Output Scrubber ─────────────────────────────────────

def test_scrub_think_blocks_cleans_model_thinking():
    raw_output = (
        "<think>\n"
        "The user wants a button with primary variant. Let's write the TSX.\n"
        "</think>\n"
        '<tool_call name="write_component">\n'
        '<tsx>\nexport const Btn = () => <button>Click</button>;\n</tsx>\n'
        '</tool_call>'
    )
    cleaned = scrub_think_blocks(raw_output)
    assert "<think>" not in cleaned
    assert "</think>" not in cleaned
    assert "Let's write the TSX" not in cleaned
    assert '<tool_call name="write_component">' in cleaned


def test_parse_agent_output_auto_scrubs_thinking_blocks():
    raw_output = (
        "<think>\nNeed to import React first.\n</think>\n"
        '<tool_call name="write_component">\n'
        '<tsx>\nexport function Button() { return <button>Test</button>; }\n</tsx>\n'
        '</tool_call>'
    )
    turn = parse_agent_output(raw_output)
    assert isinstance(turn.action, WriteComponentAction)
    assert "Button" in turn.action.tsx
    assert "<think>" not in turn.raw_text
    assert "</think>" not in turn.raw_text


def test_scrub_think_blocks_preserves_clean_output():
    clean_output = '<tool_call name="write_component">\n<tsx>export const A = 1;</tsx>\n</tool_call>'
    assert scrub_think_blocks(clean_output) == clean_output
    assert scrub_think_blocks("") == ""
    assert scrub_think_blocks(None) == ""


# ── 5. Training and Inference Parity with Real Base Model Tokenizer ──────────

def test_training_and_inference_use_same_template_path():
    base_model_dir = Path(__file__).resolve().parent.parent / "base-model"
    if not (base_model_dir / "tokenizer_config.json").exists():
        pytest.skip("base-model tokenizer not present locally")

    from transformers import AutoTokenizer

    real_tok = AutoTokenizer.from_pretrained(str(base_model_dir), local_files_only=True)
    set_default_tokenizer(real_tok)

    messages = [
        {"role": "system", "content": "You are a coding agent."},
        {"role": "user", "content": "Create a card."},
    ]

    # Format via format_chatml (used in inference and training)
    formatted = format_chatml(messages, add_generation_prompt=True)
    # Direct apply_chat_template call
    direct = real_tok.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
        enable_thinking=False,
    )

    assert formatted == direct
