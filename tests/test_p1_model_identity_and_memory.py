"""
tests/test_p1_model_identity_and_memory.py

Unit tests for P1-05 through P1-08:

  P1-05  Adapter promotion manifest generation and verification
  P1-06  VRAM ceiling constant (5.5 GiB) and HealthCallback separation
  P1-07  Code-level structural fingerprint extraction (_extract_code_fingerprint)
  P1-08  memory_loss.py scope boundary documentation
"""
import hashlib
import json
import tempfile
from pathlib import Path

import pytest


# ── Helpers ───────────────────────────────────────────────────────────────────

FAKE_CONFIG = {
    "_name_or_path": "Qwen/Qwen3-4B",
    "architectures": ["Qwen3ForCausalLM"],
    "model_type": "qwen3",
    "hidden_size": 2560,
    "intermediate_size": 9728,
    "num_hidden_layers": 36,
    "num_attention_heads": 32,
    "num_key_value_heads": 8,
    "vocab_size": 151936,
    "head_dim": 128,
}

FAKE_CHAT_TEMPLATE = "{% for message in messages %}{{ message.role }}: {{ message.content }}{% endfor %}"
FAKE_TOK_CFG = {"chat_template": FAKE_CHAT_TEMPLATE}
FAKE_TOKENIZER = {"model": {"type": "BPE", "vocab": {str(i): i for i in range(100)}}}


def _make_base_dir(tmp: Path) -> Path:
    """Write a minimal fake base-model directory."""
    base = tmp / "base-model"
    base.mkdir()
    (base / "config.json").write_text(json.dumps(FAKE_CONFIG), encoding="utf-8")
    (base / "tokenizer.json").write_text(json.dumps(FAKE_TOKENIZER), encoding="utf-8")
    (base / "tokenizer_config.json").write_text(json.dumps(FAKE_TOK_CFG), encoding="utf-8")
    return base


def _make_adapter_dir(tmp: Path) -> Path:
    adapter = tmp / "adapter"
    adapter.mkdir()
    return adapter


# ── P1-05: Promotion manifest generation ──────────────────────────────────────

from agent.base_model_fingerprint import (
    generate_adapter_promotion_manifest,
    verify_adapter_promotion_manifest,
    IncompatibleBaseModelError,
    QWEN3_4B_IDENTITY,
)


def test_p1_05_generate_writes_all_required_fields():
    with tempfile.TemporaryDirectory() as tmp_str:
        tmp = Path(tmp_str)
        base = _make_base_dir(tmp)
        adapter = _make_adapter_dir(tmp)

        manifest = generate_adapter_promotion_manifest(
            adapter_dir=adapter,
            base_dir=base,
            lora_rank=16,
            target_modules=["q_proj", "k_proj", "v_proj"],
        )
        assert (adapter / "promotion_manifest.json").is_file()

        required = [
            "base_model", "base_revision", "config_sha256", "tokenizer_sha256",
            "tokenizer_cfg_sha256", "chat_template_sha256",
            "hidden_size", "intermediate_size", "num_hidden_layers",
            "num_attention_heads", "num_key_value_heads",
            "lora_rank", "target_modules", "generated_at",
        ]
        for field in required:
            assert field in manifest, f"Field '{field}' missing from promotion manifest"


def test_p1_05_dimensions_match_qwen3_4b_identity():
    with tempfile.TemporaryDirectory() as tmp_str:
        tmp = Path(tmp_str)
        base = _make_base_dir(tmp)
        adapter = _make_adapter_dir(tmp)

        manifest = generate_adapter_promotion_manifest(adapter, base, lora_rank=16, target_modules=[])
        for key in ("hidden_size", "intermediate_size", "num_hidden_layers",
                    "num_attention_heads", "num_key_value_heads"):
            assert manifest[key] == QWEN3_4B_IDENTITY[key], (
                f"Manifest {key}={manifest[key]} does not match QWEN3_4B_IDENTITY={QWEN3_4B_IDENTITY[key]}"
            )


def test_p1_05_config_sha256_matches_live_file():
    with tempfile.TemporaryDirectory() as tmp_str:
        tmp = Path(tmp_str)
        base = _make_base_dir(tmp)
        adapter = _make_adapter_dir(tmp)

        manifest = generate_adapter_promotion_manifest(adapter, base, lora_rank=16, target_modules=[])
        expected_sha = hashlib.sha256(
            (base / "config.json").read_bytes()
        ).hexdigest()
        assert manifest["config_sha256"] == expected_sha


def test_p1_05_chat_template_sha256_matches():
    with tempfile.TemporaryDirectory() as tmp_str:
        tmp = Path(tmp_str)
        base = _make_base_dir(tmp)
        adapter = _make_adapter_dir(tmp)

        manifest = generate_adapter_promotion_manifest(adapter, base, lora_rank=16, target_modules=[])
        expected = hashlib.sha256(FAKE_CHAT_TEMPLATE.encode("utf-8")).hexdigest()
        assert manifest["chat_template_sha256"] == expected


def test_p1_05_verify_passes_on_matching_base():
    with tempfile.TemporaryDirectory() as tmp_str:
        tmp = Path(tmp_str)
        base = _make_base_dir(tmp)
        adapter = _make_adapter_dir(tmp)

        generate_adapter_promotion_manifest(adapter, base, lora_rank=16, target_modules=[])
        # Must not raise
        result = verify_adapter_promotion_manifest(adapter, base)
        assert result["hidden_size"] == 2560


def test_p1_05_verify_fails_if_manifest_absent():
    with tempfile.TemporaryDirectory() as tmp_str:
        tmp = Path(tmp_str)
        base = _make_base_dir(tmp)
        adapter = _make_adapter_dir(tmp)
        # Do NOT call generate — no manifest present
        with pytest.raises(IncompatibleBaseModelError, match="promotion_manifest.json absent"):
            verify_adapter_promotion_manifest(adapter, base)


def test_p1_05_verify_fails_on_dimension_mismatch():
    with tempfile.TemporaryDirectory() as tmp_str:
        tmp = Path(tmp_str)
        base = _make_base_dir(tmp)
        adapter = _make_adapter_dir(tmp)

        generate_adapter_promotion_manifest(adapter, base, lora_rank=16, target_modules=[])

        # Tamper: change hidden_size in config to simulate a different base model
        cfg = json.loads((base / "config.json").read_text())
        cfg["hidden_size"] = 4096  # wrong
        (base / "config.json").write_text(json.dumps(cfg))

        with pytest.raises(IncompatibleBaseModelError, match="hidden_size"):
            verify_adapter_promotion_manifest(adapter, base)


def test_p1_05_verify_fails_on_config_hash_change():
    with tempfile.TemporaryDirectory() as tmp_str:
        tmp = Path(tmp_str)
        base = _make_base_dir(tmp)
        adapter = _make_adapter_dir(tmp)

        generate_adapter_promotion_manifest(adapter, base, lora_rank=16, target_modules=[])

        # Tamper: append a comment to config.json (changes hash but not dimensions)
        original = (base / "config.json").read_bytes()
        (base / "config.json").write_bytes(original + b"\n")

        with pytest.raises(IncompatibleBaseModelError, match="config.json"):
            verify_adapter_promotion_manifest(adapter, base)


def test_p1_05_verify_fails_on_chat_template_change():
    with tempfile.TemporaryDirectory() as tmp_str:
        tmp = Path(tmp_str)
        base = _make_base_dir(tmp)
        adapter = _make_adapter_dir(tmp)

        generate_adapter_promotion_manifest(adapter, base, lora_rank=16, target_modules=[])

        # Tamper: change chat_template
        tok_cfg = json.loads((base / "tokenizer_config.json").read_text())
        tok_cfg["chat_template"] = "DIFFERENT_TEMPLATE"
        (base / "tokenizer_config.json").write_text(json.dumps(tok_cfg))

        with pytest.raises(IncompatibleBaseModelError, match="[Cc]hat.template"):
            verify_adapter_promotion_manifest(adapter, base)


def test_p1_05_qwen3_4b_identity_constant_values():
    """Exact values must match documented Qwen3-4B architecture."""
    assert QWEN3_4B_IDENTITY["hidden_size"] == 2560
    assert QWEN3_4B_IDENTITY["intermediate_size"] == 9728
    assert QWEN3_4B_IDENTITY["num_hidden_layers"] == 36
    assert QWEN3_4B_IDENTITY["num_attention_heads"] == 32
    assert QWEN3_4B_IDENTITY["num_key_value_heads"] == 8


# ── P1-06: VRAM ceiling constant ──────────────────────────────────────────────

def test_p1_06_vram_ceiling_is_5_5_gib_not_5_0():
    """VRAM_CEILING_BYTES in train_sft.py must be 5.5 GiB (not 5.0 GiB)."""
    src = Path(__file__).resolve().parents[1] / "training" / "train_sft.py"
    text = src.read_text(encoding="utf-8")
    # Check that 5.5 appears as the ceiling constant
    assert "5.5 * 1024**3" in text or "5.5*1024**3" in text, (
        "VRAM_CEILING_BYTES must be defined as int(5.5 * 1024**3) — the RTX 4050 physical ceiling"
    )


def test_p1_06_health_callback_uses_vram_ceiling_not_total_bytes():
    """HealthCallback must check against VRAM_CEILING_BYTES, not total_bytes (physical RAM)."""
    src = Path(__file__).resolve().parents[1] / "training" / "train_sft.py"
    text = src.read_text(encoding="utf-8")
    assert "VRAM_CEILING_BYTES" in text, (
        "HealthCallback must reference VRAM_CEILING_BYTES (P1-06 governor)"
    )
    # The old comparison 'max_memory_allocated() > total_bytes' must be gone
    assert "max_memory_allocated() > total_bytes" not in text, (
        "Old check against total_bytes (physical RAM) must be replaced with VRAM_CEILING_BYTES"
    )


# ── P1-07: Code-level fingerprint extraction ──────────────────────────────────

from training.train_sft import _extract_code_fingerprint


def _asst(content):
    return [{"role": "user", "content": "Go"}, {"role": "assistant", "content": content}]


def test_p1_07_extracts_jsx_tags_from_file_block():
    msgs = _asst('<tool_call name="write_site"><file path="Hero.tsx"><section><div><Button/></div></section></file></tool_call>')
    fp = _extract_code_fingerprint(msgs)
    assert "section" in fp["jsx_tags"]
    assert "div" in fp["jsx_tags"]
    assert "button" in fp["jsx_tags"]


def test_p1_07_extracts_css_declarations():
    msgs = _asst('<file path="Hero.css">display: flex;\ncolor: #333;\nmargin: 0 auto;</file>')
    fp = _extract_code_fingerprint(msgs)
    assert any("display" in d for d in fp["css_decls"])
    assert any("color" in d for d in fp["css_decls"])
    assert any("margin" in d for d in fp["css_decls"])


def test_p1_07_extracts_code_tokens():
    msgs = _asst('<file path="App.tsx">const HeroSection = () => { return <div className="hero">Hello</div>; };</file>')
    fp = _extract_code_fingerprint(msgs)
    assert "herosection" in fp["code_tokens"] or "herosection" in {t.lower() for t in fp["code_tokens"]}
    assert isinstance(fp["code_tokens"], frozenset)


def test_p1_07_empty_messages_return_empty_fingerprint():
    fp = _extract_code_fingerprint([])
    assert fp["jsx_tags"] == frozenset()
    assert fp["css_decls"] == frozenset()
    assert fp["code_tokens"] == frozenset()


def test_p1_07_user_messages_ignored():
    """Code in user messages must not contribute to fingerprint."""
    msgs = [
        {"role": "user", "content": "<file path='Hero.tsx'><BigUserComponent/></file>"},
        {"role": "assistant", "content": "<finish>Done</finish>"},
    ]
    fp = _extract_code_fingerprint(msgs)
    assert "bigusercomponent" not in fp["jsx_tags"]


def test_p1_07_high_code_token_similarity_detected(tmp_path):
    """Two trajectories with nearly identical code should have high Jaccard similarity."""
    code_a = "const HeroSection = () => <section className='hero'><h1>Title</h1><p>Body text here</p></section>"
    code_b = "const HeroSection = () => <section className='hero'><h1>Title</h1><p>Body text here</p></section>"
    fp_a = _extract_code_fingerprint(_asst(f"<file path='a.tsx'>{code_a}</file>"))
    fp_b = _extract_code_fingerprint(_asst(f"<file path='b.tsx'>{code_b}</file>"))
    common = fp_a["code_tokens"] & fp_b["code_tokens"]
    union = fp_a["code_tokens"] | fp_b["code_tokens"]
    jaccard = len(common) / len(union) if union else 0.0
    assert jaccard >= 0.90, f"Expected high code Jaccard for identical code; got {jaccard:.2f}"


def test_p1_07_low_code_token_similarity_for_different_code():
    code_a = "const Navbar = () => <nav><a href='/'>Home</a></nav>"
    code_b = ".pricing-table { display: grid; grid-template-columns: repeat(3, 1fr); }"
    fp_a = _extract_code_fingerprint(_asst(f"<file path='a.tsx'>{code_a}</file>"))
    fp_b = _extract_code_fingerprint(_asst(f"<file path='b.css'>{code_b}</file>"))
    common = fp_a["code_tokens"] & fp_b["code_tokens"]
    union = fp_a["code_tokens"] | fp_b["code_tokens"]
    jaccard = len(common) / len(union) if union else 0.0
    assert jaccard < 0.50, f"Expected low code Jaccard for different code; got {jaccard:.2f}"


# ── P1-08: memory_loss.py scope boundary documentation ────────────────────────

def test_p1_08_memory_loss_docstring_distinguishes_eval_from_training():
    src = Path(__file__).resolve().parents[1] / "training" / "memory_loss.py"
    text = src.read_text(encoding="utf-8")
    assert "EVALUATION" in text, "memory_loss.py docstring must explicitly scope to EVALUATION memory"
    assert "TRAINING" in text or "training" in text.lower(), (
        "memory_loss.py docstring must clarify it does NOT govern training activation memory"
    )
    assert "gradient checkpointing" in text.lower() or "backward" in text.lower(), (
        "memory_loss.py must reference gradient/backward pass as the separate concern"
    )
    assert "HealthCallback" in text or "VRAM_CEILING" in text or "train_sft" in text, (
        "memory_loss.py must point to the authoritative training-memory governor"
    )
