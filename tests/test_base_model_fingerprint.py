"""
tests/test_base_model_fingerprint.py - Unit Tests for Base Model Architecture & Fingerprint Verification

Verifies:
1. Manifest generation creates immutable model fingerprint with all required architecture keys.
2. Architecture class, model_type, hidden_size, intermediate_size, attention heads, KV heads, and layer count are verified.
3. Shard tensor shapes are inspected.
4. Tokenizer/config compatibility is checked.
5. Strict verification rejects relabeled Qwen2 architecture unless explicitly bypassed.
6. get_model_fingerprint_info returns base and adapter fingerprints.
"""

import json
import os
import tempfile
from pathlib import Path
import pytest

from agent.base_model_fingerprint import (
    compute_base_model_fingerprint,
    verify_base_model_architecture,
    generate_and_save_manifest,
    get_model_fingerprint_info,
    IncompatibleBaseModelError,
)

ROOT = Path(__file__).resolve().parent.parent
BASE_MODEL_DIR = ROOT / "base-model"


def test_base_model_fingerprint_extraction():
    """Verify compute_base_model_fingerprint extracts all architectural fields."""
    fp = compute_base_model_fingerprint(BASE_MODEL_DIR)
    
    assert "model_name" in fp
    assert "architecture_class" in fp
    assert "model_type" in fp
    assert "hidden_size" in fp
    assert "intermediate_size" in fp
    assert "num_attention_heads" in fp
    assert "num_key_value_heads" in fp
    assert "num_hidden_layers" in fp
    assert "vocab_size" in fp
    assert "tensor_shapes" in fp
    assert "files" in fp
    assert "immutable_fingerprint_sha256" in fp
    assert len(fp["immutable_fingerprint_sha256"]) == 64
    assert fp["total_size_gib"] > 5.0


def test_authentic_base_model_passes_strict_verification():
    """Verify that the repository's base-model directory passes strict Qwen3 verification."""
    fp = verify_base_model_architecture(BASE_MODEL_DIR, strict=True)
    assert fp["is_authentic_qwen3"] is True
    assert fp["is_relabeled_qwen2"] is False
    assert fp["architecture_class"] == "Qwen3ForCausalLM"
    assert fp["model_type"] == "qwen3"
    assert fp["hidden_size"] == 2560


def test_strict_verification_rejects_relabeled_qwen2(monkeypatch):
    """Verify strict architecture verification fails closed on relabeled Qwen2 base model."""
    monkeypatch.delenv("ALLOW_LEGACY_BASE_MODEL", raising=False)
    
    with tempfile.TemporaryDirectory() as tmp:
        td = Path(tmp)
        legacy_config = {
            "_name_or_path": "Qwen/Qwen3-4B",
            "architectures": ["Qwen2ForCausalLM"],
            "model_type": "qwen2",
            "hidden_size": 2048,
            "vocab_size": 151936,
        }
        (td / "config.json").write_text(json.dumps(legacy_config), encoding="utf-8")
        (td / "model-00001-of-00002.safetensors").write_text("shard", encoding="utf-8")
        
        with pytest.raises(IncompatibleBaseModelError) as excinfo:
            verify_base_model_architecture(td, strict=True)
        
        msg = str(excinfo.value)
        assert "Relabeled Qwen2 architecture detected" in msg or "Architecture class mismatch" in msg
        assert "Startup and training are rejected" in msg


def test_verification_bypass_with_env_var(monkeypatch):
    """Verify ALLOW_LEGACY_BASE_MODEL=1 allows verification to pass with warnings on legacy model."""
    monkeypatch.setenv("ALLOW_LEGACY_BASE_MODEL", "1")
    with tempfile.TemporaryDirectory() as tmp:
        td = Path(tmp)
        legacy_config = {
            "_name_or_path": "Qwen/Qwen3-4B",
            "architectures": ["Qwen2ForCausalLM"],
            "model_type": "qwen2",
            "hidden_size": 2048,
            "vocab_size": 151936,
        }
        (td / "config.json").write_text(json.dumps(legacy_config), encoding="utf-8")
        (td / "model-00001-of-00002.safetensors").write_text("shard", encoding="utf-8")
        
        fp = verify_base_model_architecture(td, strict=True)
        assert "verification_warnings" in fp
        assert len(fp["verification_warnings"]) > 0


def test_synthetic_authentic_qwen3_passes_verification():
    """Verify matching config and tensors pass strict verification."""
    import numpy as np
    from safetensors.numpy import save_file

    with tempfile.TemporaryDirectory() as tmp:
        td = Path(tmp)
        qwen3_config = {
            "_name_or_path": "Qwen/Qwen3-4B",
            "architectures": ["Qwen3ForCausalLM"],
            "model_type": "qwen3",
            "hidden_size": 8, "intermediate_size": 12,
            "num_attention_heads": 4, "num_key_value_heads": 2,
            "head_dim": 2, "num_hidden_layers": 1, "vocab_size": 20,
        }
        (td / "config.json").write_text(json.dumps(qwen3_config), encoding="utf-8")
        shapes = {
            "model.embed_tokens.weight": (20, 8),
            "model.layers.0.self_attn.q_proj.weight": (8, 8),
            "model.layers.0.self_attn.k_proj.weight": (4, 8),
            "model.layers.0.self_attn.v_proj.weight": (4, 8),
            "model.layers.0.self_attn.o_proj.weight": (8, 8),
            "model.layers.0.self_attn.q_norm.weight": (2,),
            "model.layers.0.self_attn.k_norm.weight": (2,),
            "model.layers.0.mlp.gate_proj.weight": (12, 8),
            "model.layers.0.mlp.up_proj.weight": (12, 8),
            "model.layers.0.mlp.down_proj.weight": (8, 12),
            "model.layers.0.input_layernorm.weight": (8,),
        }
        save_file({name: np.zeros(shape, dtype=np.float32) for name, shape in shapes.items()},
                  str(td / "model.safetensors"))

        fp = verify_base_model_architecture(td, strict=True)
        assert fp["is_authentic_qwen3"] is True
        assert fp["is_relabeled_qwen2"] is False
        assert fp["architecture_class"] == "Qwen3ForCausalLM"
        assert fp["model_type"] == "qwen3"


def test_manifest_generation_and_loading():
    """Verify manifest.json contains immutable fingerprint and valid files dict."""
    with tempfile.TemporaryDirectory() as tmp:
        td = Path(tmp)
        qwen3_config = {
            "_name_or_path": "Qwen/Qwen3-4B",
            "architectures": ["Qwen3ForCausalLM"],
            "model_type": "qwen3",
            "hidden_size": 2560,
            "num_hidden_layers": 36,
            "vocab_size": 151936,
        }
        (td / "config.json").write_text(json.dumps(qwen3_config), encoding="utf-8")
        (td / "model-00001-of-00002.safetensors").write_text("sh1", encoding="utf-8")
        (td / "model-00002-of-00002.safetensors").write_text("sh2", encoding="utf-8")
        
        manifest = generate_and_save_manifest(td)
        saved = json.loads((td / "manifest.json").read_text(encoding="utf-8"))
        
        assert saved["immutable_fingerprint_sha256"] == manifest["immutable_fingerprint_sha256"]
        assert saved["architecture_class"] == "Qwen3ForCausalLM"
        assert "model-00001-of-00002.safetensors" in saved["files"]


def test_get_model_fingerprint_info():
    """Verify runtime fingerprint info for candidate adapter."""
    cand = ROOT / "models" / "qwen3-siteagent-r16-sft"
    info = get_model_fingerprint_info(str(cand))
    
    assert info["model_name"] == "qwen3-siteagent-r16-sft"
    assert info["adapter_fingerprint"] is not None
    assert len(info["adapter_fingerprint"]) == 64
    assert info["base_fingerprint"] is not None
    assert len(info["base_fingerprint"]) == 64
