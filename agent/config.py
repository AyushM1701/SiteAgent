"""
agent/config.py - Single Source of Truth for Model Runtime Configuration

Provides ModelRuntimeConfig which centralizes context length and model runtime
parameters across:
- training (training/train_sft.py, training/preflight.py)
- inference (agent/agent.py, server/app.py)
- ContextBuilder (agent/context_builder.py)
- Inspector (server/app.py, frontend/src/state/agent-store.ts)
- benchmark script (scripts/benchmark_qwen3.py)
- generation max-token clamp (agent/agent.py)

Precedence order for max_seq_length:
1. Explicit runtime override: ModelRuntimeConfig.set_max_seq_length(...)
2. Environment variable: SLM_CONTEXT_LENGTH
3. Benchmark recommendation: runs/qwen3_context_benchmark.json
4. Default fallback: 8192
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_BENCHMARK_REPORT = BASE_DIR / "runs" / "qwen3_context_benchmark.json"


class _ModelRuntimeConfigMeta(type):
    """Metaclass allowing ModelRuntimeConfig.max_seq_length to be read and set directly."""

    @property
    def max_seq_length(cls) -> int:
        return cls.get_max_seq_length()

    @max_seq_length.setter
    def max_seq_length(cls, value: Optional[int]) -> None:
        cls.set_max_seq_length(value)


class ModelRuntimeConfig(metaclass=_ModelRuntimeConfigMeta):
    """Single source of truth for model runtime parameters."""

    _explicit_max_seq_length: Optional[int] = None
    _default_max_new_tokens: int = 4096
    _cpu_tokenizer: Any = None

    @classmethod
    def set_max_seq_length(cls, value: Optional[int]) -> None:
        """Explicitly override the active context length."""
        cls._explicit_max_seq_length = int(value) if value is not None else None

    @classmethod
    def reset(cls) -> None:
        """Reset any explicit overrides back to environment / benchmark resolution."""
        cls._explicit_max_seq_length = None

    @classmethod
    def register_tokenizer(cls, tokenizer: Any) -> None:
        """Register model tokenizer in agent_protocol."""
        from agent.agent_protocol import set_default_tokenizer
        set_default_tokenizer(tokenizer)

    @classmethod
    def get_tokenizer(cls) -> Any:
        """Retrieve the registered default tokenizer, if any."""
        from agent.agent_protocol import get_default_tokenizer
        return get_default_tokenizer()

    @classmethod
    def format_chatml(
        cls,
        messages: Any,
        add_generation_prompt: bool = True,
        tokenizer: Any = None,
    ) -> str:
        """Format messages using the Qwen3 native chat template when tokenizer is registered."""
        from agent.agent_protocol import format_chatml
        return format_chatml(messages, add_generation_prompt=add_generation_prompt, tokenizer=tokenizer)

    @classmethod
    def scrub_think_blocks(cls, text: str) -> str:
        """Strip accidental <think> blocks from model output."""
        from agent.agent_protocol import scrub_think_blocks
        return scrub_think_blocks(text)

    @classmethod
    def get_max_seq_length(cls) -> int:
        """
        Resolve the authoritative context length according to precedence:
        1. Explicit override
        2. SLM_CONTEXT_LENGTH env var
        3. Benchmark report recommendation
        4. Fallback 8192
        """
        # 1. Explicit override
        if cls._explicit_max_seq_length is not None:
            return cls._explicit_max_seq_length

        # 2. Environment variable SLM_CONTEXT_LENGTH
        env_val = os.environ.get("SLM_CONTEXT_LENGTH")
        if env_val:
            try:
                parsed = int(env_val)
                if 256 <= parsed <= 32768:
                    return parsed
            except ValueError:
                pass

        # 3. Benchmark report recommendation
        if DEFAULT_BENCHMARK_REPORT.exists():
            try:
                data = json.loads(DEFAULT_BENCHMARK_REPORT.read_text(encoding="utf-8"))
                selected = data.get("recommendation", {}).get("selected_context_length")
                if selected and isinstance(selected, int) and 256 <= selected <= 32768:
                    return selected
            except Exception:
                pass

        # 4. What fits this machine (agent/hardware.py); 8192 if detection fails.
        if os.environ.get("SLM_HARDWARE_CONTEXT", "1") != "0":
            try:
                from agent.hardware import get_profile
                return get_profile().context_length
            except Exception:
                pass
        return 8192

    @classmethod
    def get_default_max_new_tokens(cls) -> int:
        """Return the default max_new_tokens setting."""
        env_val = os.environ.get("SLM_MAX_NEW_TOKENS")
        if env_val:
            try:
                return int(env_val)
            except ValueError:
                pass
        return cls._default_max_new_tokens

    @classmethod
    def clamp_max_new_tokens(
        cls,
        prompt_tokens: int,
        requested_max_new_tokens: Optional[int] = None,
    ) -> int:
        """
        Enforce: prompt_tokens + max_new_tokens <= max_seq_length.
        Raises ValueError if prompt_tokens >= max_seq_length.
        Clamps max_new_tokens to fit strictly within the context window.
        """
        max_seq = cls.get_max_seq_length()
        if prompt_tokens >= max_seq:
            raise ValueError(
                f"Prompt length ({prompt_tokens} tokens) exceeds or equals maximum sequence length ({max_seq} tokens)"
            )
        available = max_seq - prompt_tokens
        requested = requested_max_new_tokens if requested_max_new_tokens is not None else cls.get_default_max_new_tokens()
        return max(1, min(requested, available))

    @classmethod
    def estimate_output_budget(
        cls,
        factors: Any,
        prompt_tokens: int = 0,
    ) -> Any:
        """Estimate dynamic output token budget using task complexity signals."""
        from agent.output_budget import estimate_output_budget
        return estimate_output_budget(
            factors=factors,
            prompt_tokens=prompt_tokens,
            max_seq_length=cls.get_max_seq_length(),
        )

    @classmethod
    def get_dynamic_max_new_tokens(
        cls,
        factors: Any,
        prompt_tokens: int = 0,
    ) -> int:
        """Compute the recommended clamped max_new_tokens for a task."""
        budget = cls.estimate_output_budget(factors=factors, prompt_tokens=prompt_tokens)
        return budget.clamped_tokens


    @classmethod
    def count_tokens(cls, text: str) -> int:
        """
        Accurately count tokens using the real Qwen3 / model tokenizer
        (HuggingFace PreTrainedTokenizer or fast CPU tokenizer.json).
        Falls back to character/word heuristics only if no tokenizer is present.
        """
        if not text:
            return 0

        # 1. Check registered default tokenizer in agent_protocol
        try:
            from agent.agent_protocol import _DEFAULT_TOKENIZER
            if _DEFAULT_TOKENIZER is not None:
                if hasattr(_DEFAULT_TOKENIZER, "encode"):
                    return len(_DEFAULT_TOKENIZER.encode(text, add_special_tokens=False))
                elif callable(_DEFAULT_TOKENIZER):
                    return len(_DEFAULT_TOKENIZER(text, add_special_tokens=False)["input_ids"])
        except Exception:
            pass

        # 2. Check fast CPU Tokenizer from base-model/tokenizer.json
        tok_file = BASE_DIR / "base-model" / "tokenizer.json"
        if tok_file.exists():
            try:
                if cls._cpu_tokenizer is None:
                    from tokenizers import Tokenizer
                    cls._cpu_tokenizer = Tokenizer.from_file(str(tok_file))
                    cls._cpu_tokenizer.no_truncation()
                    cls._cpu_tokenizer.no_padding()
                return len(cls._cpu_tokenizer.encode(text, add_special_tokens=False).ids)
            except Exception:
                pass

        # 3. Fallback heuristic estimation
        from agent.context_builder import estimate_tokens
        return estimate_tokens(text)

    @classmethod
    def get_token_budget(cls, total: Optional[int] = None) -> Any:
        """Create a proportional TokenBudget matching the active max_seq_length."""
        from agent.context_builder import TokenBudget
        target_total = total if total is not None else cls.get_max_seq_length()
        scale = target_total / 8192.0
        sys_contracts = int(round(1000 * scale))
        cur_instruction = int(round(300 * scale))
        proj_metadata = int(round(300 * scale))
        sel_files = int(round(3000 * scale))
        rel_files = int(round(1600 * scale))
        recent_conv = int(round(900 * scale))
        build_diag = int(round(700 * scale))
        reserve = target_total - (
            sys_contracts + cur_instruction + proj_metadata + sel_files + rel_files + recent_conv + build_diag
        )
        return TokenBudget(
            total=target_total,
            system_contracts=sys_contracts,
            current_instruction=cur_instruction,
            project_metadata=proj_metadata,
            selected_files=sel_files,
            related_files=rel_files,
            recent_conversation=recent_conv,
            build_diagnostics=build_diag,
            reserve=reserve,
        )
