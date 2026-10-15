"""
tests/test_verify_and_repair_project.py - Comprehensive Unit & Integration Tests for:
1. Unified verify_and_repair_project pipeline (typecheck -> build -> Qwen repair -> runtime -> interaction -> visual -> full revalidation)
2. ProjectRepairResult dataclass, properties, and tuple destructuring
3. Self-correction and repair attempt tracking (max_attempts = 3)
4. Integration with _run_site_generation and _run_session_edit_turn
5. Rollback on exhausted repairs in session edit turns
"""

import os
import shutil
import tempfile
import pytest
from pathlib import Path
from unittest.mock import MagicMock

from agent.project_validator import ValidationResult
from server.app import (
    ProjectRepairResult,
    verify_and_repair_project,
    MAX_REPAIR_ATTEMPTS,
)


# ── 1. ProjectRepairResult Dataclass Tests ─────────────────────────────────────

def test_project_repair_result_properties():
    clean_val = ValidationResult(
        typecheck_passed=True,
        build_passed=True,
        lint_passed=True,
        contract_passed=True,
        accessibility_passed=True,
        motion_passed=True,
        runtime_passed=True,
        preview_running=True,
    )
    res = ProjectRepairResult(validation=clean_val, files_modified=["App.tsx"], repair_attempts=0)
    assert res.passed is True
    assert res.self_corrected is False
    assert res.repair_attempts == 0
    assert res.files_modified == ["App.tsx"]

    # Tuple destructuring
    v, files, attempts = res
    assert v.passed is True
    assert files == ["App.tsx"]
    assert attempts == 0


def test_project_repair_result_self_corrected():
    repaired_val = ValidationResult(
        typecheck_passed=True,
        build_passed=True,
        lint_passed=True,
        contract_passed=True,
        accessibility_passed=True,
        motion_passed=True,
        runtime_passed=True,
        preview_running=True,
        repair_attempts=2,
    )
    res = ProjectRepairResult(validation=repaired_val, files_modified=["Hero.tsx"], repair_attempts=2)
    assert res.passed is True
    assert res.self_corrected is True
    assert res.repair_attempts == 2


def test_project_repair_result_failed():
    failed_val = ValidationResult(
        typecheck_passed=False,
        errors=["Syntax error in App.tsx"],
        repair_attempts=3,
    )
    res = ProjectRepairResult(validation=failed_val, repair_attempts=3)
    assert res.passed is False
    assert res.self_corrected is False


# ── 2. Clean Workspace Passes without Repairs ─────────────────────────────────

def test_verify_and_repair_passes_clean_workspace(tmp_path, monkeypatch):
    """When workspace already passes all gates, verify_and_repair_project returns immediately with 0 repairs."""
    clean_val = ValidationResult(
        typecheck_passed=True,
        build_passed=True,
        lint_passed=True,
        contract_passed=True,
        accessibility_passed=True,
        motion_passed=True,
        runtime_passed=True,
        preview_running=True,
    )
    monkeypatch.setattr("server.app._validate_workspace", lambda ws, **kwargs: clean_val)
    monkeypatch.setattr("server.app.take_screenshot", lambda **kwargs: None)

    runner = MagicMock()
    res = verify_and_repair_project(
        workspace=tmp_path,
        runner=runner,
        original_prompt="Build a SaaS landing page",
        max_attempts=3,
        run_visual_check=False,
    )

    assert res.passed is True
    assert res.repair_attempts == 0
    assert res.self_corrected is False
    # Runner should NOT have been invoked because workspace was already clean!
    runner.generate_turn.assert_not_called()


# ── 3. TypeScript Syntax Error Triggers Qwen Repair Loop ──────────────────────

def test_verify_and_repair_fixes_typescript_syntax_error(tmp_path, monkeypatch):
    """When initial validation fails with syntax/compiler errors, model is invoked and fixes the issue."""
    bad_val = ValidationResult(
        typecheck_passed=False,
        errors=["[Typecheck Error] src/components/Hero.tsx:10:3 - error TS1005: ';' expected."],
    )
    good_val = ValidationResult(
        typecheck_passed=True,
        build_passed=True,
        lint_passed=True,
        contract_passed=True,
        accessibility_passed=True,
        motion_passed=True,
        runtime_passed=True,
        preview_running=True,
    )

    call_count = 0
    def mock_validate(ws, **kwargs):
        nonlocal call_count
        call_count += 1
        return bad_val if call_count == 1 else good_val

    monkeypatch.setattr("server.app._validate_workspace", mock_validate)
    monkeypatch.setattr("server.app.take_screenshot", lambda **kwargs: None)

    # Mock runner that returns corrected Hero.tsx
    runner = MagicMock()
    runner.generate_turn.return_value = """I have fixed the missing semicolon in Hero.tsx.
<tool_call name="write_site">
<file path="src/components/Hero.tsx">
import React from 'react';
export function Hero() {
  return <div>Hero Content</div>;
}
</file>
</tool_call>"""

    comp_file = tmp_path / "src" / "components" / "Hero.tsx"
    comp_file.parent.mkdir(parents=True, exist_ok=True)
    comp_file.write_text("broken code", encoding="utf-8")

    res = verify_and_repair_project(
        workspace=tmp_path,
        runner=runner,
        original_prompt="Build hero section",
        max_attempts=3,
        run_visual_check=False,
    )

    assert res.passed is True
    assert res.repair_attempts == 1
    assert res.self_corrected is True
    assert "src/components/Hero.tsx" in res.files_modified
    assert comp_file.read_text(encoding="utf-8").strip() == (
        "import React from 'react';\nexport function Hero() {\n  return <div>Hero Content</div>;\n}"
    )
    assert runner.generate_turn.call_count == 1


# ── 4. Missing Import Triggers Qwen Repair Loop ───────────────────────────────

def test_verify_and_repair_fixes_missing_import(tmp_path, monkeypatch):
    """When a component has an unresolved import, compiler diagnostics are passed back to Qwen to fix."""
    bad_val = ValidationResult(
        typecheck_passed=False,
        errors=["[Typecheck Error] src/components/Feature.tsx:2:10 - error TS2307: Cannot find module './Icon'"],
    )
    good_val = ValidationResult(
        typecheck_passed=True,
        build_passed=True,
        lint_passed=True,
        contract_passed=True,
        accessibility_passed=True,
        motion_passed=True,
        runtime_passed=True,
        preview_running=True,
    )

    val_calls = 0
    def mock_validate(ws, **kwargs):
        nonlocal val_calls
        val_calls += 1
        return bad_val if val_calls == 1 else good_val

    monkeypatch.setattr("server.app._validate_workspace", mock_validate)
    monkeypatch.setattr("server.app.take_screenshot", lambda **kwargs: None)

    runner = MagicMock()
    runner.generate_turn.return_value = """Replaced missing import with inline SVG icon.
<tool_call name="write_site">
<file path="src/components/Feature.tsx">
import React from 'react';
export function Feature() {
  return <div><span>★</span> Feature</div>;
}
</file>
</tool_call>"""

    res = verify_and_repair_project(
        workspace=tmp_path,
        runner=runner,
        original_prompt="Build feature section",
        max_attempts=3,
        run_visual_check=False,
    )

    assert res.passed is True
    assert res.repair_attempts == 1
    assert res.self_corrected is True
    assert runner.generate_turn.call_count == 1


# ── 5. Exhausted Attempts Fails Closed ────────────────────────────────────────

def test_verify_and_repair_exhausted_attempts(tmp_path, monkeypatch):
    """When errors persist across all max_attempts, verify_and_repair_project fails closed."""
    persistent_bad_val = ValidationResult(
        typecheck_passed=False,
        errors=["[Typecheck Error] Unfixable TypeScript error"],
    )
    monkeypatch.setattr("server.app._validate_workspace", lambda ws, **kwargs: persistent_bad_val)
    monkeypatch.setattr("server.app.take_screenshot", lambda **kwargs: None)

    runner = MagicMock()
    runner.generate_turn.return_value = """Attempting fix...
<tool_call name="write_site">
<file path="src/components/Hero.tsx">
// Still broken
</file>
</tool_call>"""

    res = verify_and_repair_project(
        workspace=tmp_path,
        runner=runner,
        original_prompt="Build hero",
        max_attempts=3,
        run_visual_check=False,
    )

    assert res.passed is False
    assert res.self_corrected is False
    assert res.repair_attempts == 3
    assert runner.generate_turn.call_count == 3


# ── 6. Repaired Files Mirrored to Export Directory ────────────────────────────

def test_verify_and_repair_mirrors_to_export_dir(tmp_path, monkeypatch):
    """Repaired files are written to both the working session directory and the export directory."""
    bad_val = ValidationResult(typecheck_passed=False, errors=["Error"])
    good_val = ValidationResult(
        typecheck_passed=True, build_passed=True, lint_passed=True,
        contract_passed=True, accessibility_passed=True, motion_passed=True,
        runtime_passed=True, preview_running=True,
    )

    calls = 0
    def mock_validate(ws, **kwargs):
        nonlocal calls
        calls += 1
        return bad_val if calls == 1 else good_val

    monkeypatch.setattr("server.app._validate_workspace", mock_validate)
    monkeypatch.setattr("server.app.take_screenshot", lambda **kwargs: None)

    session_ws = tmp_path / "workspace"
    export_dir = tmp_path / "export"
    session_ws.mkdir()
    export_dir.mkdir()

    runner = MagicMock()
    runner.generate_turn.return_value = """Fixing file...
<tool_call name="write_site">
<file path="src/components/Nav.tsx">
export function Nav() { return <nav>Navbar</nav>; }
</file>
</tool_call>"""

    res = verify_and_repair_project(
        workspace=session_ws,
        runner=runner,
        original_prompt="Build nav",
        export_dir=export_dir,
        max_attempts=2,
        run_visual_check=False,
    )

    assert res.passed is True
    # Verify file was written to both session_ws and export_dir
    assert (session_ws / "src" / "components" / "Nav.tsx").exists()
    assert (export_dir / "src" / "components" / "Nav.tsx").exists()
    assert (export_dir / "src" / "components" / "Nav.tsx").read_text(encoding="utf-8").strip() == (
        "export function Nav() { return <nav>Navbar</nav>; }"
    )


# ── 7. Visual Repair Triggers Full Revalidation ───────────────────────────────

def test_visual_repair_full_revalidation(tmp_path, monkeypatch):
    """When visual score is low (< 3/5), visual repair is executed and followed by FULL REVALIDATION."""
    clean_val = ValidationResult(
        typecheck_passed=True, build_passed=True, lint_passed=True,
        contract_passed=True, accessibility_passed=True, motion_passed=True,
        runtime_passed=True, preview_running=True,
    )

    validate_call_count = 0
    def mock_validate(ws, **kwargs):
        nonlocal validate_call_count
        validate_call_count += 1
        return clean_val

    monkeypatch.setattr("server.app._validate_workspace", mock_validate)

    # Mock screenshot heuristic returning low score 2/5 on first call, 5/5 on second call
    ss_mock = MagicMock()
    ss_mock.exists.return_value = True
    monkeypatch.setattr("server.app.take_screenshot", lambda **kwargs: ss_mock)

    ss_score_calls = 0
    def mock_score(ss):
        nonlocal ss_score_calls
        ss_score_calls += 1
        if ss_score_calls == 1:
            return {"score": 2.0, "pass": False, "issues": ["Hero section has low content density"]}
        return {"score": 5.0, "pass": True, "issues": []}

    monkeypatch.setattr("server.app._score_screenshot_heuristic", mock_score)

    hero_file = tmp_path / "src" / "components" / "Hero.tsx"
    hero_file.parent.mkdir(parents=True, exist_ok=True)
    hero_file.write_text("export function Hero() { return <div>Plain</div>; }", encoding="utf-8")

    runner = MagicMock()
    runner.generate_turn.return_value = """Visual polish patch:
<tool_call name="write_site">
<file path="src/components/Hero.tsx">
export function Hero() { return <div className="hero-polished">Polished Hero</div>; }
</file>
</tool_call>"""

    res = verify_and_repair_project(
        workspace=tmp_path,
        runner=runner,
        original_prompt="Build landing page",
        sections=["hero", "footer"],
        max_attempts=2,
        run_visual_check=True,
    )

    assert res.passed is True
    assert res.visual_score == 5.0
    # Full revalidation must have been called: 1 initial + 1 post-visual-repair = 2
    assert validate_call_count >= 2
    assert runner.generate_turn.call_count == 1
    assert "Polished Hero" in hero_file.read_text(encoding="utf-8")


# ── 8. _run_site_generation Calls verify_and_repair_project ──────────────────

def test_site_generation_calls_verify_and_repair(tmp_path, monkeypatch):
    """Verifies that _run_site_generation delegates its verification and repair to verify_and_repair_project."""
    import queue
    from server.app import _run_site_generation, session_manager
    from agent.project_validator import ValidationResult

    # Mock session
    sess = session_manager.create_session("TestSite", "site", "Build TestSite")
    monkeypatch.setattr("server.app.BASE_DIR", tmp_path)

    # Mock site agent run
    import agent
    monkeypatch.setattr(agent, "run_site_agent_on_example", lambda **kwargs: {
        "files": {
            "src/components/Header.tsx": "export function Header() { return <header>Header</header>; }",
            "src/components/Footer.tsx": "export function Footer() { return <footer>Footer</footer>; }",
        },
        "final_passed": True,
        "sections_completed": 2,
    })
    monkeypatch.setattr("server.app._scaffold_site_vite_runner", lambda *args, **kwargs: None)

    verify_mock = MagicMock()
    clean_val = ValidationResult(
        typecheck_passed=True, build_passed=True, lint_passed=True,
        contract_passed=True, accessibility_passed=True, motion_passed=True,
        runtime_passed=True, preview_running=True,
    )
    verify_mock.return_value = ProjectRepairResult(
        validation=clean_val,
        files_modified=["src/components/Header.tsx"],
        repair_attempts=1,
        self_corrected=True,
        passed=True,
        visual_score=4.5,
    )
    monkeypatch.setattr("server.app.verify_and_repair_project", verify_mock)

    q = queue.Queue()
    task = {
        "task_id": "site_test_task_123",
        "prompt": "Build TestSite",
        "symbol": "TestSite",
        "session_id": sess.session_id,
        "max_turns": 5,
        "max_tokens": 1024,
    }

    _run_site_generation(task, q)

    assert verify_mock.call_count == 1
    call_kwargs = verify_mock.call_args[1]
    assert call_kwargs["workspace"] == sess.workspace_dir
    assert call_kwargs["original_prompt"] == "Build TestSite"
    assert call_kwargs["max_attempts"] == 3
    assert call_kwargs["run_visual_check"] is True
    assert sess.last_validation.passed is True


# ── 9. _run_session_edit_turn Rollback On Failed Repair ───────────────────────

def test_session_edit_rollback_on_failed_repair(tmp_path, monkeypatch):
    """Verifies that _run_session_edit_turn calls verify_and_repair_project and rolls back if repair fails."""
    import queue
    from server.app import _run_session_edit_turn, session_manager
    from agent.project_validator import ValidationResult

    sess = session_manager.create_session("EditSite", "site", "Build EditSite")
    hero_file = sess.workspace_dir / "src" / "components" / "Hero.tsx"
    hero_file.parent.mkdir(parents=True, exist_ok=True)
    hero_file.write_text("export function Hero() { return <div>Good Version</div>; }", encoding="utf-8")
    chk = sess.create_checkpoint("Initial Good")

    runner_mock = MagicMock()
    runner_mock.generate_turn.return_value = """Edit:
<tool_call name="write_site">
<file path="src/components/Hero.tsx">
export function Hero() { return <div>Broken Version</div>; }
</file>
</tool_call>"""
    monkeypatch.setattr("server.app._runner", runner_mock)

    # Mock verify_and_repair_project returning failure after max_attempts
    failed_val = ValidationResult(typecheck_passed=False, errors=["Persistent compile failure"])
    verify_mock = MagicMock(return_value=ProjectRepairResult(
        validation=failed_val,
        files_modified=["src/components/Hero.tsx"],
        repair_attempts=MAX_REPAIR_ATTEMPTS,
        passed=False,
    ))
    monkeypatch.setattr("server.app.verify_and_repair_project", verify_mock)

    q = queue.Queue()
    task = {
        "task_id": "edit_test_task_456",
        "prompt": "Change hero to broken",
        "session_id": sess.session_id,
        "max_tokens": 1024,
    }

    _run_session_edit_turn(task, q)

    assert verify_mock.call_count == 1
    # Workspace should have been rolled back to initial good version!
    assert "Good Version" in hero_file.read_text(encoding="utf-8")

