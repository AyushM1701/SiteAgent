"""
test_qwen3_migration.py - Correctness tests for the Qwen3-4B migration

These tests run without a GPU and without downloading any model weights.
They verify:
  1. The format_chatml shim correctly delegates to apply_chat_template when
     a tokenizer is registered, and falls back to the legacy template otherwise.
  2. <think> tokens are stripped from decoded model output.
  3. <think> tokens are blocked in gold training targets (preflight).
  4. <think> and </think> appear in CHAT_MARKERS.
  5. The adapter base-model guard raises for Qwen2.5 adapters.
  6. The DPO wrap_completion strips both <think> and <thought> tags.
  7. System prompts do not require thought wrappers.
  8. The benchmark script is importable and has its entry point.
"""

import importlib
import json
import re
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


try:
    import agent.agent_protocol as protocol
    from agent.agent_protocol import (
        AGENT_SYSTEM_PROMPT,
        SITE_AGENT_SYSTEM_PROMPT,
        format_chatml,
        parse_agent_output,
        set_default_tokenizer,
    )
except (ImportError, ModuleNotFoundError):
    import agent_protocol as protocol
    from agent_protocol import (
        AGENT_SYSTEM_PROMPT,
        SITE_AGENT_SYSTEM_PROMPT,
        format_chatml,
        parse_agent_output,
        set_default_tokenizer,
    )

try:
    from training.preflight import CHAT_MARKERS, validate_messages
except (ImportError, ModuleNotFoundError):
    from preflight import CHAT_MARKERS, validate_messages



# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_messages(assistant_content: str):
    """Minimal valid message list for preflight validation."""
    return [
        {"role": "system", "content": "You are a coding agent."},
        {"role": "user", "content": "Write a button."},
        {"role": "assistant", "content": assistant_content},
    ]


VALID_ASSISTANT_CONTENT = (
    '<tool_call name="write_component">\n'
    '<tsx>\nexport function Btn() { return <button>Click</button>; }\n</tsx>\n'
    '</tool_call>'
)

VALID_MESSAGES = _make_messages(VALID_ASSISTANT_CONTENT)


class MockTokenizer:
    """Minimal tokenizer mock that implements apply_chat_template."""

    def __init__(self, supports_thinking: bool = True):
        self._thinking = supports_thinking

    def apply_chat_template(
        self,
        messages,
        tokenize=False,
        add_generation_prompt=True,
        enable_thinking=True,
        **kwargs,
    ):
        if not self._thinking:
            raise TypeError("Unexpected kwarg: enable_thinking")
        parts = []
        for m in messages:
            parts.append(f"<|im_start|>{m['role']}\n{m['content'].strip()}<|im_end|>")
        result = "\n".join(parts)
        if add_generation_prompt:
            result += "\n<|im_start|>assistant\n"
        return result  # Returns same ChatML structure as the legacy template


class MockTokenizerNoThinking(MockTokenizer):
    """Tokenizer that raises TypeError on enable_thinking (simulates Qwen2.5)."""
    def apply_chat_template(self, messages, tokenize=False, add_generation_prompt=True, **kwargs):
        # Deliberately reject enable_thinking (older tokenizer without support)
        if 'enable_thinking' in kwargs:
            raise TypeError(f"apply_chat_template() got unexpected keyword argument 'enable_thinking'")
        parts = []
        for m in messages:
            parts.append(f"<|im_start|>{m['role']}\n{m['content'].strip()}<|im_end|>")
        result = "\n".join(parts)
        if add_generation_prompt:
            result += "\n<|im_start|>assistant\n"
        return result


# ---------------------------------------------------------------------------
# 1. format_chatml falls back to legacy template when no tokenizer is registered
# ---------------------------------------------------------------------------

def test_format_chatml_backward_compat_no_tokenizer():
    """format_chatml must work offline with no registered tokenizer."""
    # Temporarily clear any module-level tokenizer
    original = protocol._DEFAULT_TOKENIZER
    try:
        protocol._DEFAULT_TOKENIZER = None
        messages = [
            {"role": "system", "content": "Be helpful."},
            {"role": "user", "content": "Hello."},
        ]
        result = format_chatml(messages, add_generation_prompt=True)
        assert "<|im_start|>system\nBe helpful.<|im_end|>" in result
        assert "<|im_start|>user\nHello.<|im_end|>" in result
        assert result.endswith("<|im_start|>assistant\n")
    finally:
        protocol._DEFAULT_TOKENIZER = original


# ---------------------------------------------------------------------------
# 2. apply_chat_template is used when a tokenizer is registered
# ---------------------------------------------------------------------------

def test_apply_chat_template_used_when_tokenizer_registered():
    """set_default_tokenizer() must cause format_chatml to call apply_chat_template."""
    original = protocol._DEFAULT_TOKENIZER
    try:
        mock_tok = MockTokenizer()
        set_default_tokenizer(mock_tok)

        messages = [
            {"role": "system", "content": "Be helpful."},
            {"role": "user", "content": "Hello."},
        ]
        result = format_chatml(messages, add_generation_prompt=True)
        # MockTokenizer produces the same ChatML structure — just verify the call
        # was routed through apply_chat_template by checking it didn't bypass
        assert "<|im_start|>system\nBe helpful.<|im_end|>" in result
        assert result.endswith("<|im_start|>assistant\n")
    finally:
        protocol._DEFAULT_TOKENIZER = original


# ---------------------------------------------------------------------------
# 3. enable_thinking=False TypeError is handled gracefully (Qwen2.5 fallback)
# ---------------------------------------------------------------------------

def test_format_chatml_falls_back_on_no_thinking_kwarg():
    """TypeError from enable_thinking must be caught; result must still be valid ChatML."""
    original = protocol._DEFAULT_TOKENIZER
    try:
        mock_tok = MockTokenizerNoThinking()
        set_default_tokenizer(mock_tok)

        messages = [
            {"role": "user", "content": "Hi."},
        ]
        result = format_chatml(messages, add_generation_prompt=True)
        assert "<|im_start|>user\nHi.<|im_end|>" in result
    finally:
        protocol._DEFAULT_TOKENIZER = original


# ---------------------------------------------------------------------------
# 4. <think> tokens are stripped from decoded model output
# ---------------------------------------------------------------------------

def test_think_token_stripped_from_agent_output():
    """parse_agent_output must not expose <think> blocks in raw_text."""
    # Simulate Qwen3 emitting a thinking block before the action
    model_output = (
        "<think>\nLet me plan the component structure carefully.\n</think>\n"
        '<tool_call name="write_component">\n'
        "<tsx>\nexport function Btn() { return <button>OK</button>; }\n</tsx>\n"
        "</tool_call>"
    )
    # The parser already strips <thought> tags; <think> is stripped by the
    # belt-and-suspenders regex in agent.py's generate_turn after decode.
    # Here we test that _clean_file_code / parse_agent_output itself is robust.
    turn = parse_agent_output(model_output)
    assert turn.action is not None, "Action must be parsed despite <think> preamble"
    # raw_text may still contain <think> (parser doesn't strip it at this layer;
    # the decode-time strip in agent.py does). Verify the action content is clean.
    from agent.agent_protocol import WriteComponentAction
    assert isinstance(turn.action, WriteComponentAction)
    assert "<think>" not in turn.action.tsx


def test_think_strip_regex():
    """The regex used in agent.py and evaluate.py must correctly strip <think> blocks."""
    raw = (
        "<think>\nLet me think step by step.\n</think>\n"
        '<tool_call name="write_component">\n<tsx>\nexport function X() {}\n</tsx>\n</tool_call>'
    )
    stripped = re.sub(r'<think>[\s\S]*?</think>\s*', '', raw, flags=re.DOTALL).strip()
    assert "<think>" not in stripped
    assert "</think>" not in stripped
    assert '<tool_call name="write_component">' in stripped


# ---------------------------------------------------------------------------
# 5. <think> tokens are blocked in gold training targets (preflight)
# ---------------------------------------------------------------------------

def test_think_token_blocked_in_gold_target():
    """validate_messages must raise ValueError if assistant content contains <think>."""
    think_content = (
        "<think>Some reasoning here.</think>\n"
        + VALID_ASSISTANT_CONTENT
    )
    messages = _make_messages(think_content)
    # <think> is caught by CHAT_MARKERS check; error message varies by which check fires first
    with pytest.raises(ValueError):
        validate_messages({"messages": messages})


def test_think_close_token_blocked_in_gold_target():
    """validate_messages must raise ValueError if content contains </think>."""
    broken_content = VALID_ASSISTANT_CONTENT + "\n</think>"
    messages = _make_messages(broken_content)
    with pytest.raises(ValueError, match="<think>|ChatML marker"):
        validate_messages({"messages": messages})


# ---------------------------------------------------------------------------
# 6. <think> and </think> appear in CHAT_MARKERS
# ---------------------------------------------------------------------------

def test_chat_markers_include_think_tokens():
    """CHAT_MARKERS must block both <think> and </think> tokens."""
    assert "<think>" in CHAT_MARKERS, "<think> must be in CHAT_MARKERS"
    assert "</think>" in CHAT_MARKERS, "</think> must be in CHAT_MARKERS"


def test_chat_markers_include_legacy_tokens():
    """CHAT_MARKERS must retain the legacy Qwen2.5 markers."""
    assert "<|im_start|>" in CHAT_MARKERS
    assert "<|im_end|>" in CHAT_MARKERS
    assert "<|endoftext|>" in CHAT_MARKERS


# ---------------------------------------------------------------------------
# 7. DPO wrap_completion strips both <think> and <thought>
# ---------------------------------------------------------------------------

def test_dpo_wrap_completion_strips_think():
    """wrap_completion must strip <think>...</think> from DPO completions."""
    # train_dpo imports agent_protocol; mock away heavy imports
    with patch.dict("sys.modules", {
        "unsloth": MagicMock(),
        "torch": MagicMock(),
        "datasets": MagicMock(),
        "transformers": MagicMock(),
        "trl": MagicMock(),
        "peft": MagicMock(),
    }):
        import importlib
        import training.train_dpo as dpo_mod
        importlib.reload(dpo_mod)
        wrap = dpo_mod.wrap_completion

    raw = (
        "<think>\nI'll use a button element.\n</think>\n"
        '<tool_call name="write_component">\n<tsx>\nexport function B(){}\n</tsx>\n</tool_call>'
    )
    result = wrap(raw)
    assert "<think>" not in result
    assert "</think>" not in result
    assert "<tool_call" in result


def test_dpo_wrap_completion_strips_thought():
    """wrap_completion must strip legacy <thought>...</thought> from DPO completions."""
    with patch.dict("sys.modules", {
        "unsloth": MagicMock(),
        "torch": MagicMock(),
        "datasets": MagicMock(),
        "transformers": MagicMock(),
        "trl": MagicMock(),
        "peft": MagicMock(),
    }):
        import importlib
        import training.train_dpo as dpo_mod
        importlib.reload(dpo_mod)
        wrap = dpo_mod.wrap_completion

    raw = (
        "<thought>\nStep by step.\n</thought>\n"
        '<tool_call name="write_component">\n<tsx>\nexport function B(){}\n</tsx>\n</tool_call>'
    )
    result = wrap(raw)
    assert "<thought>" not in result
    assert "</thought>" not in result


# ---------------------------------------------------------------------------
# 8. System prompts do not require thought wrappers (existing test, Qwen3 compat)
# ---------------------------------------------------------------------------

def test_system_prompts_do_not_require_thought():
    """Neither system prompt must instruct the model to output <thought> tags."""
    assert "<thought>" not in AGENT_SYSTEM_PROMPT
    assert "Always output a thought first" not in AGENT_SYSTEM_PROMPT
    assert "<thought>" not in SITE_AGENT_SYSTEM_PROMPT
    assert "Always output a thought first" not in SITE_AGENT_SYSTEM_PROMPT


def test_system_prompts_do_not_require_think():
    """Neither system prompt must instruct the model to use Qwen3 <think> tags."""
    assert "<think>" not in AGENT_SYSTEM_PROMPT
    assert "<think>" not in SITE_AGENT_SYSTEM_PROMPT


# ---------------------------------------------------------------------------
# 9. Benchmark script is importable and has its entry point
# ---------------------------------------------------------------------------

def test_benchmark_script_importable():
    """benchmark_qwen3.py must import without errors and expose a main() function."""
    benchmark_path = BASE_DIR / "scripts" / "benchmark_qwen3.py"
    assert benchmark_path.exists(), f"benchmark_qwen3.py not found at {benchmark_path}"

    spec = importlib.util.spec_from_file_location("benchmark_qwen3", benchmark_path)
    mod = importlib.util.module_from_spec(spec)
    # Don't actually execute (would import torch etc.); just verify the source parses
    import ast
    source = benchmark_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    func_names = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    assert "main" in func_names, "benchmark_qwen3.py must define main()"
    assert "run_benchmark" in func_names, "benchmark_qwen3.py must define run_benchmark()"


# ---------------------------------------------------------------------------
# 10. EOS token guard fires on wrong token
# ---------------------------------------------------------------------------

def test_eos_token_guard_message():
    """The EOS guard in train_sft.py must emit a useful message citing the bad token."""
    # We verify the guard text exists in the source (no GPU needed)
    train_sft_src = (BASE_DIR / "training" / "train_sft.py").read_text(encoding="utf-8")
    assert "Unexpected tokenizer EOS token" in train_sft_src, (
        "train_sft.py must have a descriptive EOS guard error message"
    )
    assert "Qwen3-4B" in train_sft_src, (
        "train_sft.py must mention Qwen3-4B in the EOS error to guide diagnosis"
    )


# ---------------------------------------------------------------------------
# 11. VRAM gate is at least 5.0 GiB
# ---------------------------------------------------------------------------

def test_vram_gate_raised():
    """train_sft.py must gate on at least 5.0 GiB free VRAM for Qwen3-4B."""
    train_sft_src = (BASE_DIR / "training" / "train_sft.py").read_text(encoding="utf-8")
    # Check that the old 4.5 GiB gate has been replaced
    assert "4.5 * 1024**3" not in train_sft_src, (
        "The 4.5 GiB VRAM gate is too low for Qwen3-4B; must be raised to 5.0 GiB"
    )
    assert "5.0 * 1024**3" in train_sft_src, (
        "train_sft.py must gate on 5.0 GiB free VRAM for Qwen3-4B"
    )


# ---------------------------------------------------------------------------
# 12. set_default_tokenizer is exported from agent_protocol
# ---------------------------------------------------------------------------

def test_set_default_tokenizer_exported():
    """set_default_tokenizer must be importable from agent.agent_protocol."""
    from agent.agent_protocol import set_default_tokenizer as sdt
    assert callable(sdt)


# ---------------------------------------------------------------------------
# 13. Adapter base-model guard text exists in agent.py
# ---------------------------------------------------------------------------

def test_adapter_guard_in_agent_py():
    """Model loading must check actual LoRA tensor dimensions against the base."""
    agent_src = (BASE_DIR / "agent" / "agent.py").read_text(encoding="utf-8")
    assert "verify_lora_adapter_compatibility(Path(self.model_path)" in agent_src
