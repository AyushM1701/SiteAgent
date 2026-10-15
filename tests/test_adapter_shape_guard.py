import json

import numpy as np
import pytest
from safetensors.numpy import save_file

from agent.base_model_fingerprint import (
    IncompatibleBaseModelError,
    qwen3_tensor_shape_errors,
    verify_lora_adapter_compatibility,
)


def test_lora_adapter_shape_guard_rejects_relabelled_weights(tmp_path):
    base = tmp_path / "base"
    adapter = tmp_path / "adapter"
    base.mkdir()
    adapter.mkdir()
    (base / "config.json").write_text(json.dumps({
        "model_type": "qwen3", "architectures": ["Qwen3ForCausalLM"],
        "hidden_size": 8, "intermediate_size": 12,
        "num_attention_heads": 4, "num_key_value_heads": 2, "head_dim": 2,
    }), encoding="utf-8")
    (adapter / "adapter_config.json").write_text(
        json.dumps({"base_model_name_or_path": str(base)}), encoding="utf-8"
    )
    key = "base_model.model.model.layers.0.self_attn.q_proj.lora_A.weight"
    weights = adapter / "adapter_model.safetensors"
    save_file({key: np.zeros((2, 8), dtype=np.float32)}, str(weights))
    verify_lora_adapter_compatibility(adapter, base)

    save_file({key: np.zeros((2, 7), dtype=np.float32)}, str(weights))
    with pytest.raises(IncompatibleBaseModelError, match="Qwen3 expects 8"):
        verify_lora_adapter_compatibility(adapter, base)


def test_base_shape_guard_detects_config_only_relabel():
    config = {
        "hidden_size": 8, "intermediate_size": 12, "vocab_size": 20,
        "num_attention_heads": 4, "num_key_value_heads": 2, "head_dim": 2,
    }
    shapes = {
        "model.embed_tokens.weight": [20, 7],
        "model.layers.0.self_attn.q_proj.bias": [8],
    }
    errors = qwen3_tensor_shape_errors(config, shapes)
    assert any("embed_tokens" in error for error in errors)
    assert any("q_norm" in error for error in errors)
    assert any("attention bias" in error for error in errors)
