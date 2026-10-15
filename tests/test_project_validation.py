"""
tests/test_project_validation.py - Comprehensive Unit & Integration Tests for:
1. Multi-stage Project Validation sequence (typecheck -> build -> preview -> runtime check)
2. ValidationResult 4-gate structure, aliases, and passed/all_gates_passed properties
3. Cross-file import error detection via tsc --noEmit
4. Production bundler failure detection via vite build
5. Browser runtime error and unhandled exception detection
"""

import os
import shutil
import tempfile
import pytest
from pathlib import Path

from agent.project_validator import (
    ValidationResult,
    run_static_lint,
    run_project_typecheck,
    run_project_build,
    run_browser_runtime_check,
    validate_project,
)


# ── 1. ValidationResult Structure & Property Tests ────────────────────────────

def test_validation_result_defaults():
    vr = ValidationResult()
    assert vr.typecheck_passed is False
    assert vr.build_passed is False
    assert vr.lint_passed is False
    assert vr.contract_passed is False
    assert vr.accessibility_passed is False
    assert vr.runtime_passed is False
    assert vr.preview_running is False
    assert vr.contractPassed is False
    assert vr.accessibilityPassed is False
    assert vr.errors == []
    assert vr.warnings == []
    assert vr.repair_attempts == 0
    assert vr.code_passed is False
    assert vr.codePassed is False
    assert vr.passed is False
    assert vr.all_gates_passed is False


def test_validation_result_camel_case_aliases():
    vr = ValidationResult(
        typecheck_passed=True,
        build_passed=True,
        lint_passed=True,
        contract_passed=True,
        accessibility_passed=True,
        runtime_passed=True,
        preview_running=True,
        errors=["warn: note"],
        warnings=["notice"],
        repair_attempts=2,
    )
    assert vr.typecheckPassed is True
    assert vr.buildPassed is True
    assert vr.lintPassed is True
    assert vr.contractPassed is True
    assert vr.accessibilityPassed is True
    assert vr.runtimePassed is True
    assert vr.previewRunning is True
    assert vr.codePassed is True
    assert vr.code_passed is True
    assert vr.repairAttempts == 2
    assert vr.passed is True
    assert vr.all_gates_passed is True


def test_validation_result_to_dict():
    vr = ValidationResult(
        typecheck_passed=True,
        build_passed=True,
        lint_passed=True,
        contract_passed=True,
        accessibility_passed=True,
        runtime_passed=True,
        preview_running=True,
    )
    d = vr.to_dict()
    assert d["typecheck_passed"] is True
    assert d["typecheckPassed"] is True
    assert d["build_passed"] is True
    assert d["buildPassed"] is True
    assert d["contract_passed"] is True
    assert d["contractPassed"] is True
    assert d["accessibility_passed"] is True
    assert d["accessibilityPassed"] is True
    assert d["runtime_passed"] is True
    assert d["runtimePassed"] is True
    assert d["preview_running"] is True
    assert d["previewRunning"] is True
    assert d["code_passed"] is True
    assert d["codePassed"] is True
    assert d["passed"] is True


def test_validation_result_passed_logic():
    # Compilation/code valid, but preview did not start: passed MUST be False, code_passed True
    v1 = ValidationResult(
        typecheck_passed=True,
        build_passed=True,
        lint_passed=True,
        contract_passed=True,
        accessibility_passed=True,
        preview_running=False,
    )
    assert v1.passed is False
    assert v1.code_passed is True

    # Failed build: both passed and code_passed are False
    v2 = ValidationResult(
        typecheck_passed=True,
        build_passed=False,
        lint_passed=True,
        contract_passed=True,
        accessibility_passed=True,
        preview_running=False,
    )
    assert v2.passed is False
    assert v2.code_passed is False

    # Failed contract check: code_passed is False
    v_contract = ValidationResult(
        typecheck_passed=True,
        build_passed=True,
        lint_passed=True,
        contract_passed=False,
        accessibility_passed=True,
        preview_running=True,
    )
    assert v_contract.passed is False
    assert v_contract.code_passed is False

    # Failed accessibility check: code_passed is False
    v_a11y = ValidationResult(
        typecheck_passed=True,
        build_passed=True,
        lint_passed=True,
        contract_passed=True,
        accessibility_passed=False,
        preview_running=True,
    )
    assert v_a11y.passed is False
    assert v_a11y.code_passed is False

    # Preview ran but runtime check failed: passed MUST be False, code_passed True
    v3 = ValidationResult(
        typecheck_passed=True,
        build_passed=True,
        lint_passed=True,
        contract_passed=True,
        accessibility_passed=True,
        runtime_passed=False,
        preview_running=True,
    )
    assert v3.passed is False
    assert v3.code_passed is True

    # Preview failed to start even if other gates passed: passed MUST be False
    v4 = ValidationResult(
        typecheck_passed=True,
        build_passed=True,
        lint_passed=True,
        contract_passed=True,
        accessibility_passed=True,
        runtime_passed=True,
        preview_running=False,
    )
    assert v4.passed is False
    assert v4.code_passed is True

    # Runtime unverified MUST NOT pass even if runtime_passed=True:
    v4_unverified = ValidationResult(
        typecheck_passed=True,
        build_passed=True,
        lint_passed=True,
        contract_passed=True,
        accessibility_passed=True,
        runtime_passed=True,
        preview_running=True,
        runtime_unverified=True,
        runtime_status="runtime_unverified",
    )
    assert v4_unverified.passed is False
    assert v4_unverified.runtimeUnverified is True
    assert v4_unverified.runtimeStatus == "runtime_unverified"

    # Full project validation: all gates pass
    v5 = ValidationResult(
        typecheck_passed=True,
        build_passed=True,
        lint_passed=True,
        contract_passed=True,
        accessibility_passed=True,
        runtime_passed=True,
        preview_running=True,
        runtime_unverified=False,
        runtime_status="passed",
    )
    assert v5.passed is True
    assert v5.code_passed is True
    assert v5.all_gates_passed is True


# ── 2. Typecheck & Cross-File Error Detection ─────────────────────────────────

def test_run_project_typecheck_catches_cross_file_import_error():
    """Detects when ComponentA imports a non-existent export from ComponentB."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        workspace = Path(tmp_dir)

        # File A exports foo
        (workspace / "ComponentA.tsx").write_text(
            "export const foo = 42;\n",
            encoding="utf-8",
        )

        # File B tries to import non-existent bar from File A
        (workspace / "ComponentB.tsx").write_text(
            "import { bar } from './ComponentA';\nconsole.log(bar);\n",
            encoding="utf-8",
        )

        passed, errors = run_project_typecheck(workspace)
        assert passed is False
        assert any("bar" in err or "TS2724" in err or "TS2305" in err for err in errors)


def test_run_project_typecheck_succeeds_on_valid_workspace():
    """Verifies that a valid React component passes workspace typecheck."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        workspace = Path(tmp_dir)

        (workspace / "Button.tsx").write_text(
            "import React from 'react';\n"
            "export interface ButtonProps { label: string; }\n"
            "export const Button: React.FC<ButtonProps> = ({ label }) => <button>{label}</button>;\n",
            encoding="utf-8",
        )

        (workspace / "App.tsx").write_text(
            "import React from 'react';\n"
            "import { Button } from './Button';\n"
            "export default function App() { return <Button label=\"Click\" />; }\n",
            encoding="utf-8",
        )

        passed, errors = run_project_typecheck(workspace)
        assert passed is True
        assert errors == []


# ── 3. Production Bundler Error Detection (npm run build) ──────────────────────

def test_run_project_build_catches_bundler_failures():
    """Catches broken asset imports or rollup errors during vite build."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        workspace = Path(tmp_dir)

        # Component imports a completely missing package / module
        (workspace / "App.tsx").write_text(
            "import React from 'react';\n"
            "import { nonexistent } from 'nonexistent-package-xyz-123';\n"
            "export default function App() { return <div>{nonexistent()}</div>; }\n",
            encoding="utf-8",
        )

        passed, errors = run_project_build(workspace)
        assert passed is False
        assert len(errors) > 0


def test_run_project_build_succeeds_on_valid_project():
    """Verifies that Vite builds a valid project into dist/."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        workspace = Path(tmp_dir)

        (workspace / "App.tsx").write_text(
            "import React from 'react';\n"
            "export default function App() { return <h1>Production Ready</h1>; }\n",
            encoding="utf-8",
        )

        passed, errors = run_project_build(workspace)
        assert passed is True
        assert errors == []
        assert (workspace / "dist" / "index.html").exists()


# ── 4. End-to-End validate_project Sequence ───────────────────────────────────

def test_validate_project_e2e_successful_sequence():
    """Verifies the complete 4-gate verification sequence with event streaming."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        workspace = Path(tmp_dir)

        (workspace / "App.tsx").write_text(
            "import React from 'react';\n"
            "export default function App() { return <div id=\"root-content\">Hello World</div>; }\n",
            encoding="utf-8",
        )

        events = []
        result = validate_project(
            workspace_dir=workspace,
            port=5198,
            event_callback=lambda evt: events.append(evt),
        )

        assert result.typecheck_passed is True
        assert result.build_passed is True
        assert result.lint_passed is True
        assert result.runtime_passed is True
        assert result.preview_running is True
        assert result.passed is True
        assert result.all_gates_passed is True

        # Check status streaming events
        statuses = [e["status"] for e in events if e.get("type") == "status"]
        assert "Running TypeScript checks…" in statuses
        assert "Running production build…" in statuses
        assert "Checking browser runtime…" in statuses


def test_run_static_lint_fails_closed_on_exception(monkeypatch):
    """When the static checker throws an unexpected exception, it must fail closed."""
    import agent.site_acceptance as sa

    def mock_check_site_files(*args, **kwargs):
        raise RuntimeError("Simulated crash in static acceptance checker")

    monkeypatch.setattr(sa, "check_site_files", mock_check_site_files)

    with tempfile.TemporaryDirectory() as tmp_dir:
        workspace = Path(tmp_dir)
        (workspace / "App.tsx").write_text("export default function App() { return null; }", encoding="utf-8")

        passed, errors, warnings = run_static_lint(workspace)
        assert passed is False
        assert len(errors) == 1
        assert "Static lint failed closed: Simulated crash in static acceptance checker" in errors[0]


def test_run_browser_runtime_check_fallback_unverified(monkeypatch):
    """When Playwright is not installed/importable, fallback must report runtime_unverified and fail."""
    import builtins
    real_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if "playwright" in name:
            raise ImportError("No module named 'playwright'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", mock_import)

    with tempfile.TemporaryDirectory() as tmp_dir:
        workspace = Path(tmp_dir)
        (workspace / "index.html").write_text('<!DOCTYPE html><html><body><div id="root"></div></body></html>', encoding="utf-8")
        passed, preview_running, errors, _ = run_browser_runtime_check(workspace, port=5199, timeout_s=4)
        assert passed is False
        assert any("[Runtime Unverified]" in e for e in errors)
        assert any("reported as runtime_unverified, never passed" in e for e in errors)


def test_accessibility_gate_fails_on_missing_alt_and_missing_main():
    """Verify accessibility check strictly fails on missing image alt, missing main landmark, and broken controls."""
    from agent.project_validator import run_accessibility_check
    with tempfile.TemporaryDirectory() as tmp_dir:
        workspace = Path(tmp_dir)
        (workspace / "App.tsx").write_text("""
        export default function App() {
            return (
                <div>
                    <h2>Missing Main and Heading 1</h2>
                    <img src="pic.png" />
                    <button><svg /></button>
                    <input type="text" />
                </div>
            );
        }
        """, encoding="utf-8")
        (workspace / "Section.tsx").write_text("""
        export function Section() {
            return <div><h4>Sub</h4></div>;
        }
        """, encoding="utf-8")
        
        passed, errors, warnings = run_accessibility_check(workspace)
        assert passed is False
        assert any("<img> element missing required 'alt' attribute" in e for e in errors)
        assert any("Workspace missing required semantic <main" in e for e in errors)
        assert any("missing top-level <h1>" in e for e in errors)
        assert any("Inaccessible form <input" in e for e in errors)
        assert any("Interactive <button> is unlabeled" in e for e in errors)


def test_accessibility_gate_passes_on_compliant_markup():
    """Verify accessibility check passes on compliant semantic markup."""
    from agent.project_validator import run_accessibility_check
    with tempfile.TemporaryDirectory() as tmp_dir:
        workspace = Path(tmp_dir)
        (workspace / "App.tsx").write_text("""
        export default function App() {
            return (
                <main id="site-main">
                    <h1>Title</h1>
                    <h2>Section</h2>
                    <img src="pic.png" alt="A descriptive label" />
                    <button aria-label="Search"><svg /></button>
                    <input type="text" aria-label="Username" />
                </main>
            );
        }
        """, encoding="utf-8")
        
        passed, errors, warnings = run_accessibility_check(workspace)
        assert passed is True
        assert len(errors) == 0


def test_motion_rules_check_fails_closed_when_requested_and_validator_missing(monkeypatch):
    """Verify motion rules check fails closed if motion was requested and validator is unavailable."""
    from agent.project_validator import run_motion_rules_check
    import builtins
    real_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if "motion_patterns" in name:
            raise ImportError("No module named 'motion_patterns'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", mock_import)

    with tempfile.TemporaryDirectory() as tmp_dir:
        workspace = Path(tmp_dir)
        (workspace / "prompt.txt").write_text("Please create a parallax and scroll reveal experience", encoding="utf-8")
        (workspace / "App.tsx").write_text("export default function App() { return <div className='parallax'>test</div>; }", encoding="utf-8")

        passed, errors, warnings = run_motion_rules_check(workspace)
        assert passed is False
        assert any("[Motion Verification Error] Motion validation unavailable." in e for e in errors)


# ── 8. P0-03 & P0-04: Authoritative Interaction & WCAG Accessibility Tests ───

def test_interaction_gate_requires_tested_equals_required_and_passed_equals_required():
    """Verify Gate 4b requires tested == required AND passed == required."""
    from agent.project_validator import ValidationResult, InteractionEvidence

    # Case 1: 2 interactions required, only 1 tested -> must FAIL
    ev1 = InteractionEvidence(
        requirement_id="pricing_toggle",
        locator="#pricing button",
        initial_state=["$10"],
        action="click annual",
        expected_state=["$8"],
        observed_state=["$8"],
        passed=True,
    )
    v_partial = ValidationResult(
        typecheck_passed=True, build_passed=True, lint_passed=True,
        contract_passed=True, accessibility_passed=True, motion_passed=True,
        runtime_passed=True, preview_running=True,
        interactions_required=2,
        interactions_tested=1,
        interaction_evidence=[ev1],
    )
    assert v_partial.interaction_passed is False
    assert v_partial.interaction_status == "failed"
    assert v_partial.passed is False

    # Case 2: 2 interactions required, 2 tested, but 1 failed -> must FAIL
    ev2_fail = InteractionEvidence(
        requirement_id="tabs",
        locator='[role="tab"]',
        initial_state="tab 1",
        action="click tab 2",
        expected_state="tab 2 active and panel updated",
        observed_state="panel unchanged",
        passed=False,
        error="Tab panel content did not change.",
    )
    v_one_failed = ValidationResult(
        typecheck_passed=True, build_passed=True, lint_passed=True,
        contract_passed=True, accessibility_passed=True, motion_passed=True,
        runtime_passed=True, preview_running=True,
        interactions_required=2,
        interactions_tested=2,
        interaction_evidence=[ev1, ev2_fail],
    )
    assert v_one_failed.interaction_passed is False
    assert v_one_failed.interaction_status == "failed"
    assert v_one_failed.passed is False

    # Case 3: 2 interactions required, 2 tested, both passed -> must PASS
    ev2_pass = InteractionEvidence(
        requirement_id="tabs",
        locator='[role="tab"]',
        initial_state="tab 1",
        action="click tab 2",
        expected_state="tab 2 active and panel updated",
        observed_state="tab 2 active and panel updated",
        passed=True,
    )
    v_all_passed = ValidationResult(
        typecheck_passed=True, build_passed=True, lint_passed=True,
        contract_passed=True, accessibility_passed=True, motion_passed=True,
        runtime_passed=True, preview_running=True,
        interactions_required=2,
        interactions_tested=2,
        interaction_evidence=[ev1, ev2_pass],
    )
    assert v_all_passed.interaction_passed is True
    assert v_all_passed.interaction_status == "passed"
    assert v_all_passed.passed is True


def test_interaction_evidence_structure_and_serialization():
    """Verify InteractionEvidence holds all 8 canonical fields and serializes cleanly."""
    from agent.project_validator import InteractionEvidence

    ev = InteractionEvidence(
        requirement_id="metrics_tab_filter",
        locator="#features button[name=telemetry]",
        initial_state=["Card A", "Card B"],
        action="click telemetry button",
        expected_state=["Telemetry Card 1", "Telemetry Card 2"],
        observed_state=["Telemetry Card 1", "Telemetry Card 2"],
        passed=True,
        error=None,
    )
    d = ev.to_dict()
    assert d["requirement_id"] == "metrics_tab_filter"
    assert d["locator"] == "#features button[name=telemetry]"
    assert d["initial_state"] == ["Card A", "Card B"]
    assert d["action"] == "click telemetry button"
    assert d["expected_state"] == ["Telemetry Card 1", "Telemetry Card 2"]
    assert d["observed_state"] == ["Telemetry Card 1", "Telemetry Card 2"]
    assert d["passed"] is True
    assert d["error"] is None


def test_browser_runtime_check_result_tuple_compatibility():
    """Verify BrowserRuntimeCheckResult unpacks as a 4-tuple and exposes evidence attributes."""
    from agent.project_validator import BrowserRuntimeCheckResult, InteractionEvidence

    ev = InteractionEvidence(
        requirement_id="test",
        locator="btn",
        initial_state=None,
        action="click",
        expected_state="done",
        observed_state="done",
        passed=True,
    )
    res = BrowserRuntimeCheckResult(
        runtime_passed=True,
        preview_running=True,
        errors=[],
        saved_screenshot=Path("screenshot.webp"),
        interactions_tested=1,
        interactions_required=1,
        interaction_evidence=[ev],
        interaction_errors=[],
    )

    # 4-tuple unpacking
    passed, preview, errs, ss = res
    assert passed is True
    assert preview is True
    assert errs == []
    assert ss == Path("screenshot.webp")
    assert len(res) == 4

    # Structured attributes
    assert res.interactions_tested == 1
    assert res.interactions_required == 1
    assert len(res.interaction_evidence) == 1
    assert res.interaction_evidence[0].passed is True


def test_accessibility_input_accessible_name_rejects_bare_id_and_placeholder():
    """Verify WCAG SC 3.3.2 / 4.1.2: bare id= or placeholder= alone does not satisfy accessible name."""
    from agent.project_validator import run_accessibility_check

    with tempfile.TemporaryDirectory() as tmp_dir:
        workspace = Path(tmp_dir)
        (workspace / "App.tsx").write_text("""
        export default function App() {
            return (
                <main id="site-main">
                    <h1>Register</h1>
                    {/* Inaccessible: id alone does not give accessible name */}
                    <input id="user-email" type="email" />
                    {/* Inaccessible: placeholder alone is not a persistent accessible name */}
                    <input placeholder="Enter your full name" type="text" />
                </main>
            );
        }
        """, encoding="utf-8")

        passed, errors, warnings = run_accessibility_check(workspace)
        assert passed is False
        assert any("missing accessible name" in e and "bare 'id' or 'placeholder' is insufficient" in e for e in errors)


def test_accessibility_input_passes_with_persistent_labels():
    """Verify inputs pass with <label htmlFor="id">, aria-label, or wrapping <label>."""
    from agent.project_validator import run_accessibility_check

    with tempfile.TemporaryDirectory() as tmp_dir:
        workspace = Path(tmp_dir)
        (workspace / "App.tsx").write_text("""
        export default function App() {
            return (
                <main id="site-main">
                    <h1>Register</h1>
                    {/* Valid 1: label htmlFor matches id */}
                    <label htmlFor="user-email">Email Address</label>
                    <input id="user-email" type="email" />

                    {/* Valid 2: aria-label directly on input */}
                    <input type="text" aria-label="Full Name" />

                    {/* Valid 3: input wrapped inside label */}
                    <label>
                        Password
                        <input type="password" />
                    </label>
                </main>
            );
        }
        """, encoding="utf-8")

        passed, errors, warnings = run_accessibility_check(workspace)
        assert passed is True
        assert len(errors) == 0


def test_accessibility_catches_duplicate_ids_and_landmark_uniqueness_and_invalid_aria():
    """Verify WCAG SC 4.1.1 (duplicate IDs), SC 1.3.1 (unique landmarks), and SC 4.1.2 (valid ARIA)."""
    from agent.project_validator import run_accessibility_check

    with tempfile.TemporaryDirectory() as tmp_dir:
        workspace = Path(tmp_dir)
        (workspace / "App.tsx").write_text("""
        export default function App() {
            return (
                <main id="site-main">
                    <h1>Title</h1>
                    {/* Duplicate ID */}
                    <div id="duplicate-card">Card 1</div>
                    <div id="duplicate-card">Card 2</div>

                    {/* Multiple navs without distinct aria-labels */}
                    <nav><a href="#home">Home</a></nav>
                    <nav><a href="#footer">Links</a></nav>

                    {/* Invalid non-standard ARIA role */}
                    <div role="super-widget">Custom</div>
                </main>
            );
        }
        """, encoding="utf-8")

        passed, errors, warnings = run_accessibility_check(workspace)
        assert passed is False
        assert any("Duplicate element id 'duplicate-card' violates WCAG SC 4.1.1" in e for e in errors)
        assert any("Multiple <nav> landmarks detected; each must have a unique 'aria-label'" in e for e in errors)
        assert any("Invalid or non-standard ARIA role 'super-widget'" in e for e in errors)


def test_wcag_contrast_ratio_formula_precision():
    """Verify WCAG 2.1 relative luminance and contrast ratio calculations match the W3C spec."""
    from agent.project_validator import calculate_contrast_ratio, parse_color_to_rgb

    # Black on White: max contrast = 21.0:1
    black = parse_color_to_rgb("#000000")
    white = parse_color_to_rgb("#ffffff")
    assert black is not None and white is not None
    ratio_max = calculate_contrast_ratio(black, white)
    assert round(ratio_max, 1) == 21.0

    # #777777 on White: fails WCAG AA normal text (< 4.5:1)
    gray_777 = parse_color_to_rgb("#777777")
    assert gray_777 is not None
    ratio_777 = calculate_contrast_ratio(gray_777, white)
    assert ratio_777 < 4.5  # approx 4.48:1

    # #595959 on White: passes WCAG AA and AAA normal text (>= 7.0:1)
    gray_59 = parse_color_to_rgb("#595959")
    assert gray_59 is not None
    ratio_59 = calculate_contrast_ratio(gray_59, white)
    assert ratio_59 >= 7.0  # approx 7.00:1


def test_runtime_accessibility_error_fails_accessibility_gate():
    """Verify any runtime accessibility error ([A11y Runtime Error]) fails accessibility_passed."""
    from agent.project_validator import ValidationResult

    v_a11y_runtime_fail = ValidationResult(
        typecheck_passed=True, build_passed=True, lint_passed=True,
        contract_passed=True, accessibility_passed=False, motion_passed=True,
        runtime_passed=True, preview_running=True,
        accessibility_status="failed",
        errors=["[A11y Runtime Error] Low computed text contrast 2.1:1 on <p> (foreground #999, background #fff)."],
    )
    assert v_a11y_runtime_fail.accessibility_passed is False
    assert v_a11y_runtime_fail.accessibility_status == "failed"
    assert v_a11y_runtime_fail.passed is False



