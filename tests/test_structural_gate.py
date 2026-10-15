"""
test_structural_gate.py - Unit tests for the structural quality gate in the WriteSiteAction pipeline.

Verifies:
1. validate_structural_quality is called before writing to disk (gate is active).
2. Native sections with violations trigger a model rewrite request (not a disk write).
3. Native sections rejected at the retry cap remain blocked.
4. Missing native sections never become silent fallback completions.
5. Sections with no structural violations pass straight through to disk write.
6. turn_logs contain the correct action codes for each gate outcome.
"""
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from subprocess import CompletedProcess

from agent.agent import run_site_agent_on_example
from agent.style_ingest import validate_structural_quality


# ---------------------------------------------------------------------------
# 1. validate_structural_quality – smoke test: detects truncated CSS braces
# ---------------------------------------------------------------------------

def test_validate_structural_quality_detects_unbalanced_css_braces():
    """Structural validator must flag unbalanced CSS braces."""
    files = [
        ("src/components/Hero.tsx", "export function Hero() { return <section></section>; }"),
        ("src/components/Hero.css", ".hero { color: red;\n/* unclosed */"),  # missing closing }
    ]
    violations = validate_structural_quality(files, section_name="hero")
    assert len(violations) > 0
    # The validator emits "Unclosed block" for an unbalanced CSS brace
    assert any(
        "unclosed" in v.lower() or "unbalanced" in v.lower() or "brace" in v.lower()
        for v in violations
    ), f"Expected unclosed-block / unbalanced-brace violation, got: {violations}"


def test_validate_structural_quality_clean_files_produce_no_violations():
    """Structural validator should not flag valid, well-formed TSX and CSS."""
    files = [
        (
            "src/components/Hero.tsx",
            "import React from 'react';\nimport './Hero.css';\n"
            "export function Hero() { return <section className=\"hero\"><h1>Hello</h1></section>; }",
        ),
        (
            "src/components/Hero.css",
            ".hero { padding: 2rem; background: #000; color: #fff; }\n"
            ".hero h1 { font-size: 2rem; }\n",
        ),
    ]
    violations = validate_structural_quality(files, section_name="hero")
    assert violations == [], f"Expected no violations on clean files, got: {violations}"


# ---------------------------------------------------------------------------
# 2. Gate integration: native sections with violations → rewrite request
# ---------------------------------------------------------------------------

def test_structural_gate_requests_rewrite_for_native_section_with_violations(tmp_path, monkeypatch):
    """
    When the model emits a structurally violating section and the cap is NOT hit,
    the pipeline must request a rewrite (no disk write) and log
    action='write_site_structural_violation'.
    """
    # Bad CSS: opens two rule blocks but never closes the second one.
    # The first block is complete so has_real_css() passes; the unclosed
    # second block triggers the structural validator.
    bad_tsx = (
        "import React from 'react';\n"
        "import './Hero.css';\n"
        "export function Hero() { return <section className=\"hero\"><h1>Title</h1></section>; }\n"
    )
    bad_css = (
        ".hero {\n"
        "  padding: 4rem 2rem;\n"
        "  background: #000;\n"
        "  color: #fff;\n"
        "}\n"  # closed — passes has_real_css
        ".hero__inner {\n"  # opened but never closed — structural violation
        "  display: flex;\n"
    )

    # Turn 1: emit the violating section
    # Turn 2+: emit nothing (force model to "fail" again — gate will report violation again)
    call_count = [0]

    def mock_generate(**kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            return (
                '<tool_call name="write_site">\n'
                '<file path="src/components/Hero.tsx">\n'
                f'{bad_tsx}\n'
                '</file>\n'
                '<file path="src/components/Hero.css">\n'
                f'{bad_css}\n'
                '</file>\n'
                '</tool_call>'
            )
        # Subsequent: no action → will eventually trigger fallback scaffold
        return "Thinking: I cannot fix this."

    mock_runner = MagicMock()
    mock_runner.generate_turn = mock_generate

    # Monkeypatch TSC to pass so the violation comes purely from structural gate
    monkeypatch.setattr(
        "agent.agent.run_command",
        lambda *args, **kwargs: CompletedProcess(args=args[0], returncode=0, stdout="", stderr=""),
    )

    res = run_site_agent_on_example(
        orig_idx=20,
        prompt="Build a hero section",
        project_name="HeroTest",
        brief_xml="",
        sections=["hero"],
        runner=mock_runner,
        workspace_root=tmp_path,
        max_turns=3,
    )

    # The structural gate must have fired at least once on that native section
    structural_logs = [
        e for e in res["turn_logs"]
        if e.get("action") in ("write_site_structural_violation", "write_site_parser_error")
    ]
    assert len(structural_logs) >= 1, (
        "Expected at least one structural gate log entry; "
        f"turn_logs were: {res['turn_logs']}"
    )


# ---------------------------------------------------------------------------
# 3. Gate integration: cap-hit → auto-fix and accept
# ---------------------------------------------------------------------------

def test_structural_gate_blocks_at_cap_without_native_completion(tmp_path, monkeypatch):
    """
    When the retry cap is reached, invalid native output remains blocked.
    """
    bad_tsx = (
        "import React from 'react';\n"
        "import './Pricing.css';\n"
        "export function Pricing() { return <section className=\"pricing\"><h1>Plans</h1></section>; }\n"
    )
    bad_css = ".pricing { color: red;\n"  # unbalanced

    def mock_generate(**kwargs):
        # Always emit the same violating output so the cap is hit
        return (
            '<tool_call name="write_site">\n'
            '<file path="src/components/Pricing.tsx">\n'
            f'{bad_tsx}\n'
            '</file>\n'
            '<file path="src/components/Pricing.css">\n'
            f'{bad_css}\n'
            '</file>\n'
            '</tool_call>'
        )

    mock_runner = MagicMock()
    mock_runner.generate_turn = mock_generate

    monkeypatch.setattr(
        "agent.agent.run_command",
        lambda *args, **kwargs: CompletedProcess(args=args[0], returncode=0, stdout="", stderr=""),
    )

    # Use very low max_turns so cap is hit quickly
    res = run_site_agent_on_example(
        orig_idx=21,
        prompt="Build a pricing section",
        project_name="PricingTest",
        brief_xml="",
        sections=["pricing"],
        runner=mock_runner,
        workspace_root=tmp_path,
        max_turns=6,
    )

    assert res["sections_completed"] == 0
    assert res["generation_complete"] is False
    assert res["blocked_sections"]
    assert not res["files"]
    assert any(e.get("action") == "section_blocked" for e in res["turn_logs"])


# ---------------------------------------------------------------------------
# 4. Gate integration: fallback sections auto-fixed silently
# ---------------------------------------------------------------------------

def test_structural_gate_never_invents_fallback_completion(tmp_path, monkeypatch):
    """
    A model that never emits accepted code must not get fallback completion credit.
    """
    # Model always fails to emit any tool call → triggers auto-scaffold fallback
    mock_runner = MagicMock()
    mock_runner.generate_turn.return_value = "Thinking: cannot do this."

    monkeypatch.setattr(
        "agent.agent.run_command",
        lambda *args, **kwargs: CompletedProcess(args=args[0], returncode=0, stdout="", stderr=""),
    )

    # Inject a structural violation into the auto_scaffold output so the gate fires
    original_auto_scaffold = None
    import agent.agent as agent_module

    real_auto_scaffold = agent_module.auto_scaffold_section

    def patched_auto_scaffold(section_name, style_spec=None, custom_instr=""):
        t_name, t_code, c_name, c_code = real_auto_scaffold(section_name, style_spec, custom_instr)
        # Deliberately break the CSS to trigger the structural gate
        c_code_broken = c_code + "\n.unclosed-rule { color: red;\n"  # missing }
        return t_name, t_code, c_name, c_code_broken

    monkeypatch.setattr(agent_module, "auto_scaffold_section", patched_auto_scaffold)

    res = run_site_agent_on_example(
        orig_idx=22,
        prompt="Build a contact section",
        project_name="ContactTest",
        brief_xml="",
        sections=["contact"],
        runner=mock_runner,
        workspace_root=tmp_path,
        max_turns=3,
    )

    assert res["sections_completed"] == 0
    assert res["generation_complete"] is False
    assert res["blocked_sections"]
    assert not res["files"]
    assert not any(e.get("action") == "write_site_fallback" for e in res["turn_logs"])


# ---------------------------------------------------------------------------
# 5. Passing section: gate does not interfere
# ---------------------------------------------------------------------------

def test_structural_gate_does_not_block_clean_section(tmp_path, monkeypatch):
    """
    A section with clean TSX and CSS must be accepted on the first turn
    without any structural gate log entries.
    """
    clean_tsx = (
        "import React from 'react';\n"
        "import './Hero.css';\n"
        "export function Hero() {\n"
        "  return (\n"
        "    <section className=\"hero\">\n"
        "      <h1>Welcome</h1>\n"
        "    </section>\n"
        "  );\n"
        "}\n"
    )
    clean_css = (
        ".hero {\n"
        "  padding: 4rem 2rem;\n"
        "  background: #000;\n"
        "  color: #fff;\n"
        "}\n"
        ".hero h1 {\n"
        "  font-size: 2.5rem;\n"
        "}\n"
    )

    mock_runner = MagicMock()
    mock_runner.generate_turn.return_value = (
        '<tool_call name="write_site">\n'
        '<file path="src/components/Hero.tsx">\n'
        f'{clean_tsx}\n'
        '</file>\n'
        '<file path="src/components/Hero.css">\n'
        f'{clean_css}\n'
        '</file>\n'
        '</tool_call>'
    )

    monkeypatch.setattr(
        "agent.agent.run_command",
        lambda *args, **kwargs: CompletedProcess(args=args[0], returncode=0, stdout="", stderr=""),
    )

    res = run_site_agent_on_example(
        orig_idx=23,
        prompt="Build a hero section",
        project_name="CleanHeroTest",
        brief_xml="",
        sections=["hero"],
        runner=mock_runner,
        workspace_root=tmp_path,
        max_turns=3,
    )

    assert res["sections_completed"] == 1

    # No structural gate log entries expected for a clean section
    structural_logs = [
        e for e in res["turn_logs"]
        if e.get("action") in (
            "write_site_structural_violation",
            "structural_cap_auto_fix",
            "structural_auto_fix",
        )
    ]
    assert len(structural_logs) == 0, (
        f"Structural gate fired on clean section: {structural_logs}"
    )

    # Exactly one write_site_ok log
    ok_logs = [e for e in res["turn_logs"] if e.get("action") == "write_site_ok"]
    assert len(ok_logs) == 1
