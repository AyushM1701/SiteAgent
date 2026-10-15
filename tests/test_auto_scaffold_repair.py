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
3. Auto-scaffolding events and turn logs report fallback_generated with needs_model_repair=True.
4. Post-assembly Qwen rewrite loop feeds original requirements, fallback code, and compiler diagnostics.
5. Successful Qwen rewrite replaces fallback scaffold on disk and transitions quality to "repaired".
6. Failed Qwen rewrite retains safe minimal scaffold and keeps quality as "fallback".
"""
import re
import pytest
from pathlib import Path
from unittest.mock import MagicMock

from agent.agent import auto_scaffold_section, rewrite_fallback_sections, run_site_agent_on_example
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


def test_run_site_agent_logs_fallback_generated_and_needs_model_repair(tmp_path):
    """Verify that auto-scaffolding is tagged as fallback_generated with needs_model_repair=True."""
    mock_runner = MagicMock()
    mock_runner.generate_turn.return_value = "Thinking: I am stuck.\nNo tool call here."

    events = []
    def event_cb(evt):
        events.append(evt)

    res = run_site_agent_on_example(
        orig_idx=10,
        prompt="Design an enterprise analytics suite",
        project_name="AnalyticsSuite",
        brief_xml="",
        sections=["header", "hero"],
        runner=mock_runner,
        workspace_root=tmp_path,
        max_turns=2,
        event_callback=event_cb,
    )

    # Check fallback tracking
    assert len(res["fallback_sections"]) > 0
    assert "fallback_sections" in res
    assert "repaired_sections" in res
    assert "unrepaired_fallbacks" in res

    # Check turn logs tag
    fallback_logs = [entry for entry in res["turn_logs"] if entry.get("fallback_generated")]
    assert len(fallback_logs) > 0
    for log in fallback_logs:
        assert log.get("needs_model_repair") is True
        assert log.get("fallback_generated") is True

    # Check plan update events
    fallback_events = [e for e in events if e.get("type") == "plan_update" and e.get("status") == "fallback_generated"]
    assert len(fallback_events) > 0
    assert any(e.get("needs_model_repair") is True for e in fallback_events)


def test_rewrite_fallback_sections_success_replaces_scaffold_and_updates_quality(tmp_path, monkeypatch):
    """Verify that rewrite_fallback_sections invokes Qwen, verifies syntax, and overwrites fallback files."""
    case_dir = tmp_path / "site_001"
    case_dir.mkdir(parents=True, exist_ok=True)
    comp_dir = case_dir / "src" / "components"
    comp_dir.mkdir(parents=True, exist_ok=True)

    # Create initial fallback scaffold on disk
    t_name, t_code, c_name, c_code = auto_scaffold_section("hero", custom_instr="Hero section")
    (case_dir / t_name).write_text(t_code, encoding="utf-8")
    (case_dir / c_name).write_text(c_code, encoding="utf-8")
    assert 'data-fallback="true"' in (case_dir / t_name).read_text(encoding="utf-8")

    real_tsx = (
        "import React from 'react';\n"
        "import './Hero.css';\n\n"
        "export function Hero() {\n"
        "  return (\n"
        "    <section id=\"hero\" className=\"hero-section\">\n"
        "      <h1>Real Authentic Hero Component</h1>\n"
        "    </section>\n"
        "  );\n"
        "}\n"
    )
    real_css = ".hero-section { padding: 4rem; color: #fff; background: #000; }\n"

    # Mock Qwen rewrite response
    qwen_response = (
        '<tool_call name="write_site">\n'
        '<file path="src/components/Hero.tsx">\n'
        f'{real_tsx}\n'
        '</file>\n'
        '<file path="src/components/Hero.css">\n'
        f'{real_css}\n'
        '</file>\n'
        '</tool_call>'
    )

    mock_runner = MagicMock()
    mock_runner.generate_turn.return_value = qwen_response

    # Mock typecheck pass
    from subprocess import CompletedProcess
    monkeypatch.setattr("agent.agent.run_command", lambda *args, **kwargs: CompletedProcess(args=args[0], returncode=0, stdout="", stderr=""))

    repaired, rw_files, logs = rewrite_fallback_sections(
        case_dir=case_dir,
        fallback_sections=["hero"],
        runner=mock_runner,
        original_prompt="Build a clean landing page",
        project_name="CleanLanding",
        section_instructions={"hero": "Write a bold hero section."},
    )

    assert "hero" in repaired
    assert len(rw_files) == 2

    # Verify that disk content was replaced with real implementation
    disk_tsx = (case_dir / t_name).read_text(encoding="utf-8")
    assert "Real Authentic Hero Component" in disk_tsx
    assert 'data-fallback="true"' not in disk_tsx

    disk_css = (case_dir / c_name).read_text(encoding="utf-8")
    assert ".hero-section" in disk_css


def test_rewrite_fallback_sections_failure_retains_minimal_scaffold(tmp_path, monkeypatch):
    """Verify that when Qwen rewrite fails syntax checks, the minimal fallback scaffold is retained."""
    case_dir = tmp_path / "site_002"
    case_dir.mkdir(parents=True, exist_ok=True)
    comp_dir = case_dir / "src" / "components"
    comp_dir.mkdir(parents=True, exist_ok=True)

    t_name, t_code, c_name, c_code = auto_scaffold_section("footer", custom_instr="Footer section")
    (case_dir / t_name).write_text(t_code, encoding="utf-8")
    (case_dir / c_name).write_text(c_code, encoding="utf-8")

    broken_tsx = "export function Footer() { return <footer>broken JSX without closing tag"
    qwen_response = (
        '<tool_call name="write_site">\n'
        '<file path="src/components/Footer.tsx">\n'
        f'{broken_tsx}\n'
        '</file>\n'
        '<file path="src/components/Footer.css">\n'
        'footer { color: red; }\n'
        '</file>\n'
        '</tool_call>'
    )
    mock_runner = MagicMock()
    mock_runner.generate_turn.return_value = qwen_response

    # Mock typecheck failure on broken syntax
    from subprocess import CompletedProcess
    monkeypatch.setattr("agent.agent.run_command", lambda *args, **kwargs: CompletedProcess(args=args[0], returncode=1, stdout="Syntax error: Unterminated JSX", stderr=""))

    repaired, rw_files, logs = rewrite_fallback_sections(
        case_dir=case_dir,
        fallback_sections=["footer"],
        runner=mock_runner,
        original_prompt="Build landing page",
        project_name="CleanLanding",
        section_instructions={"footer": "Write footer."},
    )

    assert "footer" not in repaired
    assert len(rw_files) == 0

    # Ensure disk file still has the safe minimal scaffold
    disk_tsx = (case_dir / t_name).read_text(encoding="utf-8")
    assert 'data-fallback="true"' in disk_tsx
    assert "export function Footer" in disk_tsx


def test_run_site_agent_quality_transitions_to_repaired_on_successful_qwen_rewrite(tmp_path, monkeypatch):
    """Verify that if initial turns fall back but post-assembly Qwen rewrites them, quality is 'repaired'."""
    real_header_tsx = (
        "import React from 'react';\n"
        "import './Header.css';\n"
        "export function Header() { return <header>Authentic Header</header>; }\n"
    )
    real_header_css = "header { height: 60px; background: #111; }\n"

    turn_count = 0
    def mock_generate_turn(**kwargs):
        nonlocal turn_count
        turn_count += 1
        history = kwargs.get("history", [])
        last_msg = history[-1]["content"] if history else ""

        # During section generation: model fails
        if "[FALLBACK REWRITE REQUIRED" not in last_msg:
            return "Thinking: I failed to emit tool call."
        # During post-assembly fallback rewrite: model successfully provides real code
        return (
            '<tool_call name="write_site">\n'
            '<file path="src/components/Header.tsx">\n'
            f'{real_header_tsx}\n'
            '</file>\n'
            '<file path="src/components/Header.css">\n'
            f'{real_header_css}\n'
            '</file>\n'
            '</tool_call>'
        )

    mock_runner = MagicMock()
    mock_runner.generate_turn = mock_generate_turn

    # Mock typecheck success
    from subprocess import CompletedProcess
    monkeypatch.setattr("agent.agent.run_command", lambda *args, **kwargs: CompletedProcess(args=args[0], returncode=0, stdout="", stderr=""))

    res = run_site_agent_on_example(
        orig_idx=11,
        prompt="Portfolio site",
        project_name="PortfolioSite",
        brief_xml="",
        sections=["header"],
        runner=mock_runner,
        workspace_root=tmp_path,
        max_turns=2,
    )

    assert res["fallback_sections"] == ["header"]
    assert res["repaired_sections"] == ["header"]
    assert res["unrepaired_fallbacks"] == []
    # Generation quality MUST be 'repaired', not 'fallback'!
    assert res["generation_quality"] == "repaired"
    assert "Authentic Header" in res["files"]["src/components/Header.tsx"]


@pytest.fixture(autouse=True)
def _freeform_site_strategy(monkeypatch):
    """These tests exercise the legacy code-writing loop, not the design kit."""
    monkeypatch.setenv("SITE_STRATEGY", "freeform")
