"""
agent/base_model_fingerprint.py - Authoritative Base Model Architecture & Fingerprint Verifier

Guarantees authentic model identity before training, startup, or promotion:
- Architecture class (Qwen3ForCausalLM vs relabeled Qwen2ForCausalLM)
- model_type ('qwen3' vs relabeled 'qwen2')
- Hidden size, intermediate size, attention heads, KV heads, layer count
- Tensor shapes in model shards (reading safetensors file headers directly)
- Tokenizer / config compatibility (vocabulary size and special tokens)
- Model repository revision / commit hash and cryptographic SHA-256 file checksums
- Immutable model fingerprint stored in manifest.json
"""

import hashlib
import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class IncompatibleBaseModelError(RuntimeError):
    """Raised when base model architecture does not match authentic Qwen3 identity."""
    pass


def verify_lora_adapter_compatibility(adapter_dir: Path, base_dir: Path) -> None:
    """Check LoRA tensor dimensions against the local base before loading weights.

    Adapter metadata can retain a plausible base path after weights have been
    copied from a different model, so config names alone are insufficient.
    This inspects safetensors metadata without allocating the tensors.

    If the adapter directory contains a promotion_manifest.json, the stricter
    verify_adapter_promotion_manifest() check is also applied (P1-05).
    """
    from safetensors import safe_open

    adapter_dir = Path(adapter_dir).resolve()
    base_dir = Path(base_dir).resolve()
    adapter_cfg = json.loads((adapter_dir / "adapter_config.json").read_text(encoding="utf-8"))
    raw_base = str(adapter_cfg.get("base_model_name_or_path", ""))
    claimed_base = Path(raw_base).resolve()
    # Portable references to the same base are accepted (the tensor shapes below are
    # the real check): this repo's base-model folder on any machine, or the hub id the
    # base was downloaded from. Any other model name or path is refused.
    portable = (Path(raw_base.replace("\\", "/")).name == base_dir.name == "base-model"
                or re.fullmatch(r"(?:qwen|unsloth)/qwen3-4b(?:-instruct-2507)?", raw_base.strip().lower()) is not None)
    if claimed_base != base_dir and not portable:
        raise IncompatibleBaseModelError(f"Adapter base {claimed_base} differs from {base_dir}")
    cfg = json.loads((base_dir / "config.json").read_text(encoding="utf-8"))
    if cfg.get("model_type") != "qwen3" or "Qwen3ForCausalLM" not in cfg.get("architectures", []):
        raise IncompatibleBaseModelError("Adapter target is not the verified Qwen3 base")
    hidden = int(cfg["hidden_size"])
    intermediate = int(cfg["intermediate_size"])
    attention = int(cfg["num_attention_heads"]) * int(cfg["head_dim"])
    kv = int(cfg["num_key_value_heads"]) * int(cfg["head_dim"])
    modules = {
        "q_proj": (hidden, attention), "k_proj": (hidden, kv),
        "v_proj": (hidden, kv), "o_proj": (attention, hidden),
        "gate_proj": (hidden, intermediate), "up_proj": (hidden, intermediate),
        "down_proj": (intermediate, hidden),
    }
    weights = adapter_dir / "adapter_model.safetensors"
    if not weights.is_file():
        raise IncompatibleBaseModelError(f"Adapter weights missing: {weights}")
    checked = 0
    with safe_open(str(weights), framework="pt", device="cpu") as tensors:
        for key in tensors.keys():
            match = re.search(r"\.(q_proj|k_proj|v_proj|o_proj|gate_proj|up_proj|down_proj)\.lora_([AB])(?:\.default)?\.weight$", key)
            if not match:
                continue
            module, side = match.groups()
            in_features, out_features = modules[module]
            shape = tensors.get_slice(key).get_shape()
            expected_feature = in_features if side == "A" else out_features
            feature = (shape[1] if side == "A" else shape[0]) if len(shape) == 2 else None
            if feature != expected_feature:
                raise IncompatibleBaseModelError(
                    f"Adapter tensor {key} has shape {shape}; Qwen3 expects {expected_feature} {side}-side features"
                )
            checked += 1
    if checked == 0:
        raise IncompatibleBaseModelError("Adapter contains no recognized LoRA projection tensors")

    # P1-05: If a promotion manifest exists, perform the stricter identity check.
    promo_manifest_path = adapter_dir / "promotion_manifest.json"
    if promo_manifest_path.is_file():
        verify_adapter_promotion_manifest(adapter_dir, base_dir, strict=True)


# ── P1-05: Adapter Promotion Manifest ────────────────────────────────────────

# Authoritative Qwen3-4B dimensional identity for this project.
# These values must never be changed without a controlled migration.
QWEN3_4B_IDENTITY = {
    "base_model": "Qwen/Qwen3-4B",
    "hidden_size": 2560,
    "intermediate_size": 9728,
    "num_hidden_layers": 36,
    "num_attention_heads": 32,
    "num_key_value_heads": 8,
}

EXPECTED_QWEN3_4B = {
    "architectures": ["Qwen3ForCausalLM"],
    "model_type": "qwen3",
    "head_dim": 128,
    "vocab_size": 151936,
    "hidden_size": 2560,
    "intermediate_size": 9728,
    "num_hidden_layers": 36,
    "num_attention_heads": 32,
    "num_key_value_heads": 8,
}


def assert_qwen3_4b(config: Dict[str, Any]) -> None:
    """Fail closed unless the config is the exact supported Qwen3-4B shape."""
    problems = []
    for key, expected in EXPECTED_QWEN3_4B.items():
        actual = config.get(key)
        if actual != expected:
            problems.append(f"{key}: expected {expected!r}, got {actual!r}")
    if problems:
        raise IncompatibleBaseModelError("Wrong foundation architecture:\n" + "\n".join(problems))


def generate_adapter_promotion_manifest(
    adapter_dir: Path,
    base_dir: Path,
    lora_rank: int,
    target_modules: List[str],
    base_revision: str = "unknown",
    *, strict: bool = False,
) -> Dict[str, Any]:
    """Write promotion_manifest.json into *adapter_dir*.

    The manifest records the immutable identity of the exact base-model build
    this adapter was trained against (P1-05 remediation).  At promotion time,
    verify_adapter_promotion_manifest() compares the live base-model files
    against these hashes and rejects any adapter whose provenance does not
    match exactly.

    Fields recorded
    ---------------
    base_model          : HuggingFace model ID
    base_revision       : git commit / revision (if known)
    config_sha256       : SHA-256 of base-model/config.json
    tokenizer_sha256    : SHA-256 of base-model/tokenizer.json
    tokenizer_cfg_sha256: SHA-256 of base-model/tokenizer_config.json
    chat_template_sha256: SHA-256 of the chat_template string in tokenizer_config
    hidden_size, intermediate_size, num_hidden_layers,
    num_attention_heads, num_key_value_heads  : exact dimensions from config
    lora_rank           : LoRA rank used during training
    target_modules      : list of projection names trained
    """
    adapter_dir = Path(adapter_dir).resolve()
    base_dir = Path(base_dir).resolve()

    cfg_path = base_dir / "config.json"
    tok_path = base_dir / "tokenizer.json"
    tok_cfg_path = base_dir / "tokenizer_config.json"

    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    assert_qwen3_4b(cfg)

    # Derive chat_template SHA from tokenizer_config if present
    chat_template_sha = ""
    if tok_cfg_path.is_file():
        try:
            tc = json.loads(tok_cfg_path.read_text(encoding="utf-8"))
            tmpl = tc.get("chat_template", "")
            if tmpl:
                chat_template_sha = hashlib.sha256(tmpl.encode("utf-8")).hexdigest()
        except Exception:
            pass

    manifest: Dict[str, Any] = {
        "base_model": cfg.get("_name_or_path", QWEN3_4B_IDENTITY["base_model"]),
        "base_revision": base_revision,
        "config_sha256": compute_sha256(cfg_path) if cfg_path.is_file() else "",
        "tokenizer_sha256": compute_sha256(tok_path) if tok_path.is_file() else "",
        "tokenizer_cfg_sha256": compute_sha256(tok_cfg_path) if tok_cfg_path.is_file() else "",
        "chat_template_sha256": chat_template_sha,
        # Exact architectural dimensions
        "hidden_size": int(cfg.get("hidden_size", 0)),
        "intermediate_size": int(cfg.get("intermediate_size", 0)),
        "num_hidden_layers": int(cfg.get("num_hidden_layers", 0)),
        "num_attention_heads": int(cfg.get("num_attention_heads", 0)),
        "num_key_value_heads": int(cfg.get("num_key_value_heads", 0)),
        # LoRA metadata
        "lora_rank": lora_rank,
        "target_modules": sorted(target_modules),
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    if strict:
        adapter_cfg = _verify_complete_adapter(adapter_dir, base_dir)
        if adapter_cfg['r'] != lora_rank or sorted(adapter_cfg['target_modules']) != sorted(target_modules):
            raise IncompatibleBaseModelError('Requested rank/modules differ from saved adapter config')
        for path in (tok_path, tok_cfg_path):
            if not path.is_file():
                raise IncompatibleBaseModelError(f'Required promotion evidence missing: {path}')
        if not chat_template_sha:
            raise IncompatibleBaseModelError('Required chat template evidence missing')
        shards = sorted(base_dir.glob('*.safetensors'))
        if not shards:
            raise IncompatibleBaseModelError('Required base shard evidence missing')
        manifest.update(
            schema_version=2,
            lora_alpha=adapter_cfg['lora_alpha'],
            adapter_config_sha256=compute_sha256(adapter_dir / 'adapter_config.json'),
            adapter_sha256=compute_sha256(adapter_dir / 'adapter_model.safetensors'),
            base_shard_sha256={path.name: compute_sha256(path) for path in shards},
        )

    dest = adapter_dir / "promotion_manifest.json"
    dest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def verify_adapter_promotion_manifest(adapter_dir: Path, base_dir: Path, *, strict: bool = False) -> Dict[str, Any]:
    """Verify that the adapter's promotion_manifest.json matches the live base model.

    Fails closed (raises IncompatibleBaseModelError) on any of:
      - promotion_manifest.json absent from adapter_dir
      - Any dimensional field (hidden_size, intermediate_size, layers, heads, kv_heads)
        does not match the live config.json
      - config_sha256, tokenizer_sha256, or chat_template_sha256 does not match the
        corresponding live file in base_dir

    Returns the loaded manifest on success.
    """
    adapter_dir = Path(adapter_dir).resolve()
    base_dir = Path(base_dir).resolve()

    promo_path = adapter_dir / "promotion_manifest.json"
    if not promo_path.is_file():
        raise IncompatibleBaseModelError(
            f"promotion_manifest.json absent from {adapter_dir}. "
            "Adapter was not generated by the canonical training pipeline and cannot be promoted."
        )

    manifest = json.loads(promo_path.read_text(encoding="utf-8"))
    cfg_path = base_dir / "config.json"
    tok_path = base_dir / "tokenizer.json"
    tok_cfg_path = base_dir / "tokenizer_config.json"

    if not cfg_path.is_file():
        raise IncompatibleBaseModelError(f"Base model config.json not found at {base_dir}")
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    assert_qwen3_4b(cfg)

    errors: List[str] = []

    # 1. Dimensional identity checks
    dim_fields = [
        ("hidden_size", "hidden_size"),
        ("intermediate_size", "intermediate_size"),
        ("num_hidden_layers", "num_hidden_layers"),
        ("num_attention_heads", "num_attention_heads"),
        ("num_key_value_heads", "num_key_value_heads"),
    ]
    for manifest_key, cfg_key in dim_fields:
        expected = manifest.get(manifest_key)
        actual = cfg.get(cfg_key)
        if expected is None or actual is None:
            errors.append(f"Missing dimension '{manifest_key}' in manifest or config")
        elif int(expected) != int(actual):
            errors.append(
                f"Dimension mismatch '{manifest_key}': manifest={expected}, live config={actual}. "
                "This adapter was trained against a different base model."
            )

    # 2. Cryptographic file identity checks
    crypto_checks = [
        ("config_sha256", cfg_path),
        ("tokenizer_sha256", tok_path),
        ("tokenizer_cfg_sha256", tok_cfg_path),
    ]
    if strict:
        if manifest.get('schema_version') != 2:
            errors.append('Strict promotion requires schema_version 2 and complete adapter/shard evidence')
        crypto_checks.extend([
            ('adapter_config_sha256', adapter_dir / 'adapter_config.json'),
            ('adapter_sha256', adapter_dir / 'adapter_model.safetensors'),
        ])
        shard_hashes = manifest.get('base_shard_sha256')
        live_shards = {path.name: path for path in base_dir.glob('*.safetensors')}
        if not isinstance(shard_hashes, dict) or not shard_hashes or set(shard_hashes) != set(live_shards):
            errors.append('Missing or mismatched base shard SHA evidence')
        else:
            for name, path in live_shards.items():
                if not _valid_sha(shard_hashes[name]) or compute_sha256(path) != shard_hashes[name]:
                    errors.append(f'Hash mismatch for base shard {name}')
        try:
            adapter_cfg = _verify_complete_adapter(adapter_dir, base_dir)
            for field, key in [('lora_rank', 'r'), ('lora_alpha', 'lora_alpha')]:
                if manifest.get(field) != adapter_cfg[key]:
                    errors.append(f'Adapter {field} differs from promotion manifest')
            if sorted(manifest.get('target_modules') or []) != sorted(adapter_cfg['target_modules']):
                errors.append('Adapter target_modules differ from promotion manifest')
        except (IncompatibleBaseModelError, OSError, ValueError, KeyError) as exc:
            errors.append(str(exc))
    for field, path in crypto_checks:
        expected_hash = manifest.get(field, "")
        if strict and not _valid_sha(expected_hash):
            errors.append(f'Missing or invalid SHA-256 evidence: {field}')
            continue
        if not expected_hash:
            # Manifest predates this field; skip gracefully
            continue
        if not path.is_file():
            errors.append(f"Base file missing: {path} (needed to verify {field})")
            continue
        actual_hash = compute_sha256(path)
        if actual_hash != expected_hash:
            errors.append(
                f"Hash mismatch for {path.name}: manifest={expected_hash[:12]}…, "
                f"live={actual_hash[:12]}…. "
                "The base model files have changed since this adapter was trained."
            )

    # 3. Chat-template hash (derived from tokenizer_config.json content)
    expected_tmpl_sha = manifest.get("chat_template_sha256", "")
    if strict and not _valid_sha(expected_tmpl_sha):
        errors.append('Missing or invalid SHA-256 evidence: chat_template_sha256')
    if expected_tmpl_sha and tok_cfg_path.is_file():
        try:
            tc = json.loads(tok_cfg_path.read_text(encoding="utf-8"))
            live_tmpl = tc.get("chat_template", "")
            live_tmpl_sha = hashlib.sha256(live_tmpl.encode("utf-8")).hexdigest() if live_tmpl else ""
            if live_tmpl_sha != expected_tmpl_sha:
                errors.append(
                    f"Chat-template hash mismatch: manifest={expected_tmpl_sha[:12]}…, "
                    f"live={live_tmpl_sha[:12]}…. "
                    "The tokenizer chat template has changed. Protocol corruption is possible."
                )
        except Exception as exc:
            errors.append(f"Could not verify chat_template_sha256: {exc}")

    if errors:
        raise IncompatibleBaseModelError(
            f"Adapter promotion manifest verification FAILED for {adapter_dir}:\n"
            + "\n".join(f"  ✗ {e}" for e in errors)
            + "\nThis adapter cannot be promoted to the served position."
        )

    return manifest


def _valid_sha(value):
    return isinstance(value, str) and re.fullmatch(r'[0-9a-f]{64}', value) is not None


def _verify_complete_adapter(adapter_dir: Path, base_dir: Path) -> Dict[str, Any]:
    """Validate every layer/module A/B pair, not just whichever tensors exist."""
    from safetensors import safe_open
    cfg = json.loads((base_dir / 'config.json').read_text(encoding='utf-8'))
    assert_qwen3_4b(cfg)
    acfg = json.loads((adapter_dir / 'adapter_config.json').read_text(encoding='utf-8'))
    if Path(acfg.get('base_model_name_or_path', '')).resolve() != base_dir.resolve():
        raise IncompatibleBaseModelError('Adapter base path differs from verified base')
    rank, alpha = acfg.get('r'), acfg.get('lora_alpha')
    if type(rank) is not int or rank <= 0 or not isinstance(alpha, (int, float)) or not 0 < alpha < float('inf'):
        raise IncompatibleBaseModelError('Invalid adapter rank/alpha')
    if acfg.get('peft_type') != 'LORA' or acfg.get('bias', 'none') != 'none':
        raise IncompatibleBaseModelError('Only bias-free LORA adapters are supported')
    for field in ('rank_pattern', 'alpha_pattern', 'layers_to_transform', 'layers_pattern', 'modules_to_save', 'use_dora', 'use_rslora'):
        if acfg.get(field):
            raise IncompatibleBaseModelError(f'Unsupported adapter configuration: {field}')
    dimensions = {'q_proj': (2560, 4096), 'k_proj': (2560, 1024), 'v_proj': (2560, 1024),
                  'o_proj': (4096, 2560), 'gate_proj': (2560, 9728),
                  'up_proj': (2560, 9728), 'down_proj': (9728, 2560)}
    modules = acfg.get('target_modules')
    if not isinstance(modules, list) or not modules or any(not isinstance(m, str) for m in modules) or len(set(modules)) != len(modules) or not set(modules) <= dimensions.keys():
        raise IncompatibleBaseModelError('Invalid adapter target_modules')
    expected = {(layer, module, side) for layer in range(cfg['num_hidden_layers']) for module in modules for side in ('A', 'B')}
    seen = set()
    with safe_open(str(adapter_dir / 'adapter_model.safetensors'), framework='pt', device='cpu') as tensors:
        for key in tensors.keys():
            match = re.fullmatch(r'base_model\.model\.model\.layers\.(\d+)\.(self_attn|mlp)\.([a-z_]+)\.lora_([AB])(?:\.default)?\.weight', key)
            if not match:
                raise IncompatibleBaseModelError(f'Unexpected adapter tensor: {key}')
            layer, block, module, side = match.groups()
            identity = (int(layer), module, side)
            if identity not in expected or identity in seen or block != ('self_attn' if module in ('q_proj', 'k_proj', 'v_proj', 'o_proj') else 'mlp'):
                raise IncompatibleBaseModelError(f'Unexpected or duplicate adapter pair: {key}')
            inputs, outputs = dimensions[module]
            shape = list(tensors.get_slice(key).get_shape())
            if shape != ([rank, inputs] if side == 'A' else [outputs, rank]):
                raise IncompatibleBaseModelError(f'Adapter rank/feature shape mismatch: {key}: {shape}')
            seen.add(identity)
    if seen != expected:
        raise IncompatibleBaseModelError(f'Incomplete adapter A/B pairs: missing {len(expected - seen)} tensors')
    return acfg


def compute_sha256(path: Path) -> str:
    """Computes SHA-256 checksum of a file in 64 KiB chunks."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def inspect_shard_tensor_shapes(base_dir: Path) -> Dict[str, List[int]]:
    """
    Directly inspects tensor shapes in base model safetensors shards without
    loading full weight tensors into memory.
    """
    tensor_shapes: Dict[str, List[int]] = {}
    safetensors_files = sorted(base_dir.glob("*.safetensors"))
    if not safetensors_files:
        return tensor_shapes

    try:
        from safetensors import safe_open
        for sf in safetensors_files:
            with safe_open(sf, framework="pt") as f:
                for key in f.keys():
                    # Retain key structural anchor tensors
                    if any(anchor in key for anchor in [
                        "embed_tokens",
                        "layers.0.self_attn.q_proj.weight",
                        "layers.0.self_attn.q_proj.bias",
                        "layers.0.self_attn.k_proj.weight",
                        "layers.0.self_attn.k_proj.bias",
                        "layers.0.self_attn.v_proj.weight",
                        "layers.0.self_attn.v_proj.bias",
                        "layers.0.self_attn.o_proj.weight",
                        "layers.0.self_attn.q_norm.weight",
                        "layers.0.self_attn.k_norm.weight",
                        "layers.0.mlp.gate_proj.weight",
                        "layers.0.mlp.up_proj.weight",
                        "layers.0.mlp.down_proj.weight",
                        "layers.0.input_layernorm.weight",
                        "lm_head.weight",
                    ]):
                        tensor_shapes[key] = list(f.get_slice(key).get_shape())
    except Exception as exc:
        tensor_shapes["_error"] = [str(exc)]

    return tensor_shapes


def qwen3_tensor_shape_errors(config: Dict[str, Any], shapes: Dict[str, List[int]]) -> List[str]:
    """Detect a relabeled checkpoint using the actual layer-zero tensor shapes."""
    try:
        hidden = int(config["hidden_size"])
        intermediate = int(config["intermediate_size"])
        head_dim = int(config["head_dim"])
        attention = int(config["num_attention_heads"]) * head_dim
        kv = int(config["num_key_value_heads"]) * head_dim
        vocab = int(config["vocab_size"])
    except (KeyError, TypeError, ValueError) as exc:
        return [f"Incomplete Qwen3 shape config: {exc}"]
    expected = {
        "model.embed_tokens.weight": [vocab, hidden],
        "model.layers.0.self_attn.q_proj.weight": [attention, hidden],
        "model.layers.0.self_attn.k_proj.weight": [kv, hidden],
        "model.layers.0.self_attn.v_proj.weight": [kv, hidden],
        "model.layers.0.self_attn.o_proj.weight": [hidden, attention],
        "model.layers.0.self_attn.q_norm.weight": [head_dim],
        "model.layers.0.self_attn.k_norm.weight": [head_dim],
        "model.layers.0.mlp.gate_proj.weight": [intermediate, hidden],
        "model.layers.0.mlp.up_proj.weight": [intermediate, hidden],
        "model.layers.0.mlp.down_proj.weight": [hidden, intermediate],
        "model.layers.0.input_layernorm.weight": [hidden],
    }
    errors = [
        f"{name}: expected {shape}, found {shapes.get(name)}"
        for name, shape in expected.items() if shapes.get(name) != shape
    ]
    for name in ("q_proj", "k_proj", "v_proj"):
        bias = f"model.layers.0.self_attn.{name}.bias"
        if bias in shapes:
            errors.append(f"Unexpected Qwen2-style attention bias: {bias}")
    if "_error" in shapes:
        errors.append(f"Could not inspect model tensors: {shapes['_error']}")
    return errors


def compute_base_model_fingerprint(base_dir: Path) -> Dict[str, Any]:
    """
    Computes a comprehensive, deterministic fingerprint of the base model
    spanning configuration, architecture, tokenizer, and shard shapes.
    """
    base_dir = Path(base_dir).resolve()
    config_path = base_dir / "config.json"
    if not config_path.is_file():
        raise FileNotFoundError(f"config.json missing in base model directory: {base_dir}")

    config = json.loads(config_path.read_text(encoding="utf-8"))
    
    # 1. Architecture class and model_type
    architectures = config.get("architectures", [])
    architecture_class = architectures[0] if architectures else "Unknown"
    model_type = config.get("model_type", "")
    model_name = config.get("_name_or_path", "")

    # 2. Key dimensional hyperparameters
    hidden_size = config.get("hidden_size")
    intermediate_size = config.get("intermediate_size")
    num_attention_heads = config.get("num_attention_heads")
    num_key_value_heads = config.get("num_key_value_heads")
    num_hidden_layers = config.get("num_hidden_layers")
    vocab_size = config.get("vocab_size")

    # 3. Inspect shard tensor shapes
    tensor_shapes = inspect_shard_tensor_shapes(base_dir)
    tensor_shape_errors = qwen3_tensor_shape_errors(config, tensor_shapes)

    # 4. Tokenizer compatibility
    tok_json = base_dir / "tokenizer.json"
    tok_cfg = base_dir / "tokenizer_config.json"
    tokenizer_vocab_size = None
    tokenizer_type = None
    if tok_json.is_file():
        try:
            tok_data = json.loads(tok_json.read_text(encoding="utf-8"))
            tokenizer_vocab_size = len(tok_data.get("model", {}).get("vocab", {}))
            tokenizer_type = tok_data.get("model", {}).get("type")
        except Exception:
            pass

    # 5. File checksums
    core_files = [
        "config.json",
        "tokenizer.json",
        "tokenizer_config.json",
        "vocab.json",
        "merges.txt",
        "generation_config.json",
    ]
    st_files = sorted(p.name for p in base_dir.glob("*.safetensors"))
    if not st_files:
        st_files = ["model-00001-of-00002.safetensors", "model-00002-of-00002.safetensors"]
    required_files = core_files + st_files
    if (base_dir / "model.safetensors.index.json").is_file():
        required_files.append("model.safetensors.index.json")

    files_manifest: Dict[str, Any] = {}
    total_bytes = 0
    file_hashes_concat = []

    for rf in set(required_files):
        fpath = base_dir / rf
        if fpath.is_file():
            fsize = fpath.stat().st_size
            total_bytes += fsize
            sha = compute_sha256(fpath)
            files_manifest[rf] = {"size_bytes": fsize, "sha256": sha}
            file_hashes_concat.append(f"{rf}:{sha}")

    # Check for git revision / hash
    git_head_path = base_dir / ".git" / "HEAD"
    repo_revision = "unknown"
    if git_head_path.is_file():
        try:
            repo_revision = git_head_path.read_text(encoding="utf-8").strip()
        except Exception:
            pass

    # Determine authenticity
    is_qwen3_arch = (
        architecture_class == "Qwen3ForCausalLM"
        and model_type == "qwen3"
    )
    is_relabeled_qwen2 = (
        "qwen2" in model_type.lower()
        or "Qwen2" in architecture_class
    )

    # Cryptographic immutable fingerprint
    fp_raw = f"{architecture_class}|{model_type}|{hidden_size}|{intermediate_size}|{num_attention_heads}|{num_key_value_heads}|{num_hidden_layers}|{vocab_size}|{'|'.join(sorted(file_hashes_concat))}"
    immutable_fingerprint_sha256 = hashlib.sha256(fp_raw.encode("utf-8")).hexdigest()

    return {
        "model_name": model_name,
        "architecture_class": architecture_class,
        "model_type": model_type,
        "hidden_size": hidden_size,
        "intermediate_size": intermediate_size,
        "num_attention_heads": num_attention_heads,
        "num_key_value_heads": num_key_value_heads,
        "num_hidden_layers": num_hidden_layers,
        "vocab_size": vocab_size,
        "tokenizer_vocab_size": tokenizer_vocab_size,
        "tokenizer_type": tokenizer_type,
        "tokenizer_compatible": (tokenizer_vocab_size is None or vocab_size is None or vocab_size >= tokenizer_vocab_size),
        "tensor_shapes": tensor_shapes,
        "tensor_shape_errors": tensor_shape_errors,
        "total_size_gib": round(total_bytes / (1024**3), 3),
        "files": files_manifest,
        "repo_revision": repo_revision,
        "is_authentic_qwen3": is_qwen3_arch and not is_relabeled_qwen2 and not tensor_shape_errors,
        "is_relabeled_qwen2": is_relabeled_qwen2,
        "immutable_fingerprint_sha256": immutable_fingerprint_sha256,
        "verified_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }


def verify_base_model_architecture(
    base_dir: Path,
    strict: bool = True,
    expected_arch: str = "Qwen3ForCausalLM",
    expected_model_type: str = "qwen3",
    require_4b: bool = False,
) -> Dict[str, Any]:
    """
    Verifies that the base model matches the expected authentic Qwen3 architecture.
    Fails closed: raises IncompatibleBaseModelError if relabeled older architecture is detected.
    """
    fingerprint = compute_base_model_fingerprint(base_dir)
    errors: List[str] = []
    if require_4b:
        # Production load gates request exact identity; the generic verifier also
        # supports deliberately tiny Qwen3 fixtures and diagnostic legacy reads.
        assert_qwen3_4b(json.loads((Path(base_dir) / 'config.json').read_text(encoding='utf-8')))

    # 1. Architecture class check
    if fingerprint["architecture_class"] != expected_arch:
        errors.append(
            f"Architecture class mismatch: declared '{fingerprint['architecture_class']}', expected '{expected_arch}'."
        )

    # 2. model_type check
    if fingerprint["model_type"] != expected_model_type:
        errors.append(
            f"model_type mismatch: declared '{fingerprint['model_type']}', expected '{expected_model_type}'."
        )

    # 3. Detect relabeled Qwen2 disguised as Qwen3
    if fingerprint["is_relabeled_qwen2"]:
        errors.append(
            "Relabeled Qwen2 architecture detected: Model uses Qwen2ForCausalLM / model_type='qwen2'. "
            "Relabeling _name_or_path as 'Qwen3' does not confer authentic Qwen3 identity."
        )
    if fingerprint["tensor_shape_errors"]:
        errors.extend(fingerprint["tensor_shape_errors"])

    # 4. Tokenizer / config compatibility
    if not fingerprint["tokenizer_compatible"]:
        errors.append(
            f"Tokenizer incompatible with config: config vocab ({fingerprint['vocab_size']}) < tokenizer vocab ({fingerprint['tokenizer_vocab_size']})."
        )

    # 5. Shard files presence
    safetensors_present = any(f.endswith(".safetensors") for f in fingerprint["files"])
    if not safetensors_present:
        errors.append("Model weight shards (*.safetensors) missing from files manifest.")

    if errors:
        msg = (
            f"Base model architecture verification FAILED for {base_dir}:\n"
            + "\n".join(f"  - {err}" for err in errors)
            + "\nStartup and training are rejected until authentic Qwen3-4B weights/config are installed."
        )
        allow_legacy = os.environ.get("ALLOW_LEGACY_BASE_MODEL", "").lower() in ("1", "true", "yes")
        if strict and (require_4b or not allow_legacy):
            raise IncompatibleBaseModelError(msg)
        else:
            fingerprint["verification_warnings"] = errors

    return fingerprint


def generate_and_save_manifest(base_dir: Path, manifest_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Computes fingerprint and writes the immutable model fingerprint to manifest.json.
    """
    base_dir = Path(base_dir).resolve()
    manifest = compute_base_model_fingerprint(base_dir)
    dest = manifest_path or (base_dir / "manifest.json")
    dest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def get_model_fingerprint_info(model_path: str) -> Dict[str, Any]:
    """
    Extracts loaded model, base fingerprint, and adapter fingerprint for runtime telemetry and /api/status.
    """
    p = Path(model_path).resolve()
    info: Dict[str, Any] = {
        "model_name": p.name,
        "model_path": str(p),
        "base_model": "base-model",
        "base_fingerprint": None,
        "adapter_fingerprint": None,
        "is_qwen3_architecture": False,
        "is_mock": False,
    }

    # If adapter directory
    adapter_config = p / "adapter_config.json"
    if adapter_config.is_file():
        try:
            acfg = json.loads(adapter_config.read_text(encoding="utf-8"))
            info["base_model"] = acfg.get("base_model_name_or_path", "base-model")
        except Exception:
            pass

    adapter_weights = p / "adapter_model.safetensors"
    if adapter_weights.is_file():
        info["adapter_fingerprint"] = compute_sha256(adapter_weights)
    elif (p / "training_manifest.json").is_file():
        try:
            tm = json.loads((p / "training_manifest.json").read_text(encoding="utf-8"))
            info["adapter_fingerprint"] = tm.get("adapter_sha256") or tm.get("sha256")
        except Exception:
            pass

    # Inspect base model
    base_dir = Path(info["base_model"])
    if not base_dir.is_absolute():
        base_dir = (p.parent / base_dir).resolve()
        if not base_dir.exists():
            base_dir = (Path(__file__).resolve().parent.parent / "base-model").resolve()

    manifest_path = base_dir / "manifest.json"
    if manifest_path.is_file():
        try:
            m = json.loads(manifest_path.read_text(encoding="utf-8"))
            if "tensor_shape_errors" not in m:
                m = compute_base_model_fingerprint(base_dir)
            info["base_fingerprint"] = m.get("immutable_fingerprint_sha256") or m.get("sha256")
            info["is_qwen3_architecture"] = m.get("is_authentic_qwen3", False)
        except Exception:
            pass
    elif (base_dir / "config.json").is_file():
        try:
            fp = compute_base_model_fingerprint(base_dir)
            info["base_fingerprint"] = fp.get("immutable_fingerprint_sha256")
            info["is_qwen3_architecture"] = fp.get("is_authentic_qwen3", False)
        except Exception:
            pass

    return info
