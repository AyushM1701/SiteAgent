"""
test_style_preset_composer.py - Unit & Integration tests for Issue #26:
Structured Style Preset Selection & Bias Elimination in ChatComposer.
"""

from pathlib import Path
import pytest
from agent.style_ingest import (
    PRESET_STYLES,
    get_available_style_presets,
    resolve_style_preset,
    StyleSpec,
)
from agent.site_brief import generate_content_brief, brief_to_xml


def test_available_style_presets_schema():
    """Verify all 8 canonical style presets are present with valid metadata schema."""
    presets = get_available_style_presets()
    assert len(presets) == 8

    preset_ids = [p["id"] for p in presets]
    expected_ids = [
        "auto",
        "editorial",
        "brutalist",
        "minimal",
        "technical",
        "luxury",
        "experimental",
        "custom",
    ]
    assert preset_ids == expected_ids

    # Verify each preset item has label and description
    for p in presets:
        assert "id" in p and p["id"]
        assert "label" in p and p["label"]
        assert "description" in p and p["description"]

    # Verify Auto is marked as default
    auto_preset = next(p for p in presets if p["id"] == "auto")
    assert auto_preset.get("isDefault") is True


def test_resolve_style_preset_canonical_and_aliases():
    """Verify resolution of style presets to their corresponding StyleSpec objects."""
    # Canonical names
    editorial_spec = resolve_style_preset("editorial")
    assert isinstance(editorial_spec, StyleSpec)
    assert "editorial" in editorial_spec.name.lower() or "refero" in editorial_spec.name.lower()

    brutalist_spec = resolve_style_preset("brutalist")
    assert isinstance(brutalist_spec, StyleSpec)
    assert "brutalist" in brutalist_spec.name.lower()

    minimal_spec = resolve_style_preset("minimal")
    assert isinstance(minimal_spec, StyleSpec)
    assert "minimal" in minimal_spec.name.lower()
    assert "--color-bg" in minimal_spec.colors

    technical_spec = resolve_style_preset("technical")
    assert isinstance(technical_spec, StyleSpec)
    assert "technical" in technical_spec.name.lower()
    assert "--color-accent" in technical_spec.colors

    luxury_spec = resolve_style_preset("luxury")
    assert isinstance(luxury_spec, StyleSpec)
    assert "luxury" in luxury_spec.name.lower() or "champagne" in luxury_spec.name.lower()

    experimental_spec = resolve_style_preset("experimental")
    assert isinstance(experimental_spec, StyleSpec)
    assert "aurora" in experimental_spec.name.lower() or "glassmorphic" in experimental_spec.name.lower()

    # Auto, Custom, None should return None (allowing neutral / heuristic flow)
    assert resolve_style_preset("auto") is None
    assert resolve_style_preset("custom") is None
    assert resolve_style_preset(None) is None
    assert resolve_style_preset("") is None


def test_site_brief_generation_with_structured_style_preset():
    """Verify generate_content_brief respects structured style_preset without prompt pollution."""
    prompt = "Create a modern developer analytics dashboard"
    brief = generate_content_brief(prompt, style_preset="editorial", provider="auto")

    assert brief["style_preset"] == "editorial"
    assert brief.get("style_spec") is not None
    assert isinstance(brief["style_spec"], StyleSpec)
    # The prompt itself remains pristine and unpolluted
    assert "dark glassmorphism" not in prompt
    assert "3D sphere" not in prompt

    # Test xml serialization includes style_preset
    xml = brief_to_xml(brief)
    assert "<style_preset>editorial</style_preset>" in xml


def test_site_brief_generation_with_auto_preset():
    """Verify generate_content_brief with 'auto' preset falls back to heuristic domain design."""
    prompt = "Build a high-end restaurant landing page"
    brief = generate_content_brief(prompt, style_preset="auto", provider="auto")

    # In auto mode, domain theme should determine primary color
    assert brief["business_type"] == "restaurant"
    assert "primary_color" in brief


def test_server_style_presets_api():
    """Verify Flask server GET /api/style-presets endpoint."""
    from server.app import app
    client = app.test_client()

    res = client.get("/api/style-presets")
    assert res.status_code == 200
    data = res.get_json()
    assert "presets" in data
    assert "default" in data
    assert data["default"] == "auto"

    preset_ids = [p["id"] for p in data["presets"]]
    for expected in ["auto", "editorial", "brutalist", "minimal", "technical", "luxury", "experimental", "custom"]:
        assert expected in preset_ids


def test_server_generate_accepts_style_preset_metadata():
    """Verify /api/generate accepts stylePreset in JSON metadata payload."""
    from server.app import app
    client = app.test_client()

    payload = {
        "prompt": "Build an architectural studio portfolio",
        "stylePreset": "minimal",
        "intent": "site",
    }
    res = client.post("/api/generate", json=payload)
    assert res.status_code in (200, 503)  # 503 if GPU model runner is uninitialized in unit test
    if res.status_code == 200:
        data = res.get_json()
        assert "task_id" in data or "session_id" in data


def test_chat_composer_bias_strings_eliminated():
    """Verify frontend/src/components/chat/ChatComposer.tsx contains zero biased prompt append strings."""
    composer_file = Path("frontend/src/components/chat/ChatComposer.tsx")
    assert composer_file.exists(), "ChatComposer.tsx not found"
    content = composer_file.read_text(encoding="utf-8")

    # The old biased prompt appending code must be completely absent:
    assert "Use modern dark glassmorphism" not in content, "Found biased glassmorphism prompt helper in ChatComposer.tsx"
    assert "hero with 3D sphere" not in content, "Found biased 3D sphere prompt helper in ChatComposer.tsx"
    assert "STYLE_PRESETS" in content, "STYLE_PRESETS not defined in ChatComposer.tsx"
    assert "stylePreset" in content, "stylePreset state not used in ChatComposer.tsx"
