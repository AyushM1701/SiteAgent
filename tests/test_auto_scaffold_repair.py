"""
Test suite for auto-scaffolding reform and post-assembly Qwen rewrite loop.

Verifies:
1. auto_scaffold_section generates a minimal deterministic scaffold without hallucinating:
   - fake pricing ($29/mo, $79/mo)
   - fake frequency tags (10Hz – 48kHz)
   - fake materials (Hand-lathed brass, aerospace billet aluminum)
   - fake legal metrics (98% Win Rate)
   - generic placeholder buttons (Explore {item} ->)
2. Minimal scaffold includes data-fallback="true".
3. The freeform loop never writes fallback scaffolds: a stuck section is reported as blocked.
4. The design kit never blocks: unusable model output becomes honest fallback copy ("repaired").
"""
import re
import pytest
from pathlib import Path
from unittest.mock import MagicMock

from agent.agent import auto_scaffold_section, run_site_agent_on_example
from agent.project_validator import ValidationResult, InteractionValidationResult, VisualValidationResult


def test_header_fallback_is_functional_navigation_without_instruction_leak():
    _, tsx, _, css = auto_scaffold_section(
        "header",
        custom_instr="a sticky navigation bar with a responsive mobile drawer toggle",
    )
    assert '<header id="header"' in tsx
    assert 'aria-label="Primary navigation"' in tsx
    assert 'aria-expanded={open}' in tsx
    assert "a sticky navigation bar" not in tsx
    assert "ApexCloud" not in tsx
    assert ".sa-header__menu-button" in css


def test_auto_scaffold_produces_minimal_deterministic_scaffold_without_hallucinations():
    """Verify auto_scaffold_section does NOT invent pricing, metrics, materials, or buttons."""
    tsx_name, tsx_code, css_name, css_code = auto_scaffold_section(
        "features",
        style_spec=None,
        custom_instr="Write the features section highlighting core product capabilities.",
    )

    assert "Features.tsx" in tsx_name
    assert "export function Features" in tsx_code
    assert 'data-fallback="true"' in tsx_code
    assert "Features.css" in css_name

    # Prohibited hallucinated strings
    forbidden_tokens = [
        "$29/mo", "$79/mo", "$199/mo",
        "10Hz – 48kHz", "12Hz – 42kHz", "8Hz – 52kHz",
        "Hand-lathed brass", "obsidian damping baffle", "aerospace billet aluminum",
        "98% Win Rate", "140+ Trials", "AmLaw 100",
        "Explore Features", "Explore Features →", "Explore Features &rarr;",
        "sa-field__label",
    ]
    for token in forbidden_tokens:
        assert token not in tsx_code, f"Found forbidden fabricated token '{token}' in fallback scaffold!"


def test_auto_scaffold_preserves_explicit_items_without_fabricating_metrics():
    """Verify that explicitly listed item names are displayed without inventing fake metrics or buttons."""
    tsx_name, tsx_code, css_name, css_code = auto_scaffold_section(
        "products",
        style_spec=None,
        custom_instr="Showcase (Aura Monolith, Aura Sphere, Aura Studio).",
    )

    assert 'data-fallback="true"' in tsx_code
    assert "Aura Monolith" in tsx_code
    assert "Aura Sphere" in tsx_code
    assert "Aura Studio" in tsx_code

    assert "$29/mo" not in tsx_code
    assert "Explore Aura Monolith" not in tsx_code
    assert "Explore Aura Sphere" not in tsx_code


def test_stuck_freeform_sections_are_blocked_without_fallback_files(tmp_path):
    """A model that never emits a tool call blocks its sections; nothing is invented."""
    mock_runner = MagicMock()
    mock_runner.generate_turn.return_value = "Thinking: I am stuck.\nNo tool call here."

    events = []
    res = run_site_agent_on_example(
        orig_idx=10,
        prompt="Design an enterprise analytics suite",
        project_name="AnalyticsSuite",
        brief_xml="",
        sections=["header", "hero"],
        runner=mock_runner,
        workspace_root=tmp_path,
        max_turns=2,
        event_callback=events.append,
    )

    assert res["fallback_sections"] == []
    assert set(res["blocked_sections"]) == {"header", "hero"}
    assert res["files"] == {}
    assert res["generation_quality"] == "blocked"
    blocked_events = [e for e in events if e.get("type") == "plan_update" and e.get("status") == "blocked"]
    assert {e["section"] for e in blocked_events} == {"header", "hero"}
    assert all(e.get("reason") for e in blocked_events)


def test_kit_turns_unusable_output_into_fallback_copy_and_reports_repaired(tmp_path, monkeypatch):
    """With the design kit a section is never blocked: unusable output becomes honest
    fallback copy and the run is marked "repaired"."""
    monkeypatch.setenv("SITE_STRATEGY", "kit")
    mock_runner = MagicMock()
    mock_runner.is_mock = True
    mock_runner.generate_turn.return_value = "Thinking: I failed to emit JSON."

    res = run_site_agent_on_example(
        orig_idx=11,
        prompt="Portfolio for Maya Chen, a brand designer.",
        project_name="MayaChen",
        brief_xml="",
        sections=["header", "hero", "projects", "contact", "footer"],
        runner=mock_runner,
        workspace_root=tmp_path,
    )

    assert res["blocked_sections"] == []
    assert res["generation_quality"] == "repaired"
    assert res["section_completion"] == "5 / 5"
    assert "src/components/Projects.tsx" in res["files"]
    assert "Maya Chen" in res["files"]["src/components/Header.tsx"]


@pytest.fixture(autouse=True)
def _freeform_site_strategy(monkeypatch):
    """These tests exercise the legacy code-writing loop, not the design kit."""
    monkeypatch.setenv("SITE_STRATEGY", "freeform")
