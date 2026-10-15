"""Tests for Issue #18: Retrain the Qwen3 LoRA Adapter From Scratch.

Validates:
- No Qwen2.5 adapter weights are reused (clean scratch initialization).
- Base model is Qwen3-4B in base-model/.
- Conservative candidate configuration: rank=16, alpha=16, dropout=0.0.
- Required artifacts in models/qwen3-siteagent-r16-sft/:
  * training_manifest.json
  * run_manifest.json
  * adapter_model.safetensors
  * adapter_config.json
  * tokenizer metadata
  * dataset hashes
- Fail-closed guard in train_sft.py against reusing Qwen2.5 adapters.
"""

from pathlib import Path
import json
import pytest
from safetensors import safe_open


CANDIDATE_DIR = Path("models/qwen3-siteagent-authentic-r16-candidate")
BASE_MODEL_DIR = Path("base-model")


def test_base_model_is_qwen3():
    """Verify base-model/ is configured for Qwen3-4B."""
    assert BASE_MODEL_DIR.is_dir(), "base-model directory must exist"
    config_path = BASE_MODEL_DIR / "config.json"
    assert config_path.is_file(), "base-model/config.json must exist"

    config = json.loads(config_path.read_text(encoding="utf-8"))
    assert config["model_type"] == "qwen3"
    assert config["architectures"] == ["Qwen3ForCausalLM"]
    from agent.base_model_fingerprint import verify_base_model_architecture
    assert verify_base_model_architecture(BASE_MODEL_DIR, strict=True)["is_authentic_qwen3"]


def test_candidate_artifacts_exist():
    """Verify all required candidate artifacts exist in models/qwen3-siteagent-r16-sft/."""
    assert CANDIDATE_DIR.is_dir(), f"Candidate directory {CANDIDATE_DIR} must exist"

    required_files = [
        "training_manifest.json",
        "adapter_model.safetensors",
        "adapter_config.json",
        "tokenizer.json",
        "tokenizer_config.json",
    ]
    for filename in required_files:
        p = CANDIDATE_DIR / filename
        assert p.is_file(), f"Required candidate artifact {filename} missing in {CANDIDATE_DIR}"
        assert p.stat().st_size > 0, f"Candidate artifact {filename} is empty"
    assert Path("runs/qwen3-siteagent-authentic-r16-checkpoints/run_manifest.json").is_file()


def test_adapter_config_conservative_r16():
    """Verify adapter configuration matches rank=16, alpha=16, dropout=0.0."""
    adapter_config_path = CANDIDATE_DIR / "adapter_config.json"
    config = json.loads(adapter_config_path.read_text(encoding="utf-8"))

    assert config["r"] == 16, f"Expected rank 16, got {config.get('r')}"
    assert config["lora_alpha"] == 16, f"Expected alpha 16, got {config.get('lora_alpha')}"
    assert config["lora_dropout"] == 0.0, f"Expected dropout 0.0, got {config.get('lora_dropout')}"
    assert "base-model" in config.get("base_model_name_or_path", "").replace("/", "\\")


def test_no_qwen25_adapter_weights_reused():
    """Verify no Qwen2.5 adapter weights or previous checkpoints were reused."""
    manifest_path = CANDIDATE_DIR / "training_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    # Must not have been initialized from an old adapter
    assert manifest.get("initial_adapter") is None, (
        f"Expected initial_adapter to be None, got {manifest.get('initial_adapter')}"
    )
    assert manifest.get("initial_adapter_sha256") is None

    # Status must be complete
    assert manifest.get("status") == "complete"
    assert manifest.get("rank") == 16
    assert manifest.get("lora_alpha") == 16
    assert manifest.get("lora_dropout") == 0.0

    # Dataset hash and tokenizer hash must be recorded
    assert manifest.get("dataset_sha256") is not None
    assert len(manifest.get("dataset_sha256")) == 64
    assert manifest.get("tokenizer_sha256") is not None
    assert len(manifest.get("tokenizer_sha256")) == 64


def test_safetensors_weights_valid():
    """Verify safetensors contains valid float weights matching Qwen3-4B dimensions."""
    safetensors_path = CANDIDATE_DIR / "adapter_model.safetensors"
    with safe_open(safetensors_path, framework="pt") as f:
        keys = list(f.keys())
        assert len(keys) > 0, "Adapter safetensors contains no weight keys"

        # Qwen3-4B has 36 layers
        layer_indices = {int(k.split("layers.")[1].split(".")[0]) for k in keys if "layers." in k}
        assert max(layer_indices) == 35, f"Expected 36 layers (0..35), max index was {max(layer_indices)}"

        # Check rank dimension on a sample layer
        sample_tensor_a = f.get_tensor("base_model.model.model.layers.0.mlp.down_proj.lora_A.weight")
        assert sample_tensor_a.shape[0] == 16, f"Expected lora_A rank dimension 16, got {sample_tensor_a.shape}"
        assert sample_tensor_a.shape[1] == 9728

        sample_tensor_b = f.get_tensor("base_model.model.model.layers.0.mlp.down_proj.lora_B.weight")
        assert sample_tensor_b.shape[1] == 16, f"Expected lora_B rank dimension 16, got {sample_tensor_b.shape}"


def test_train_sft_rejects_qwen25_adapter(tmp_path, real_context_report):
    """Verify train_sft fail-closed logic rejects any legacy Qwen2.5 adapter."""
    from training.train_sft import train

    fake_legacy_adapter = tmp_path / "legacy_qwen25_adapter"
    fake_legacy_adapter.mkdir()
    legacy_config = {
        "base_model_name_or_path": "Qwen/Qwen2.5-Coder-3B-Instruct",
        "r": 16,
        "lora_alpha": 16,
    }
    (fake_legacy_adapter / "adapter_config.json").write_text(json.dumps(legacy_config), encoding="utf-8")

    from agent.base_model_fingerprint import IncompatibleBaseModelError
    with pytest.raises(IncompatibleBaseModelError, match="Adapter base"):
        train(
            dataset_path="data/quality_candidate/train.jsonl",
            initial_adapter=str(fake_legacy_adapter),
            preflight_only=True,
            benchmark_report=real_context_report,
        )
