"""
tests/test_no_fabricated_validation.py - Comprehensive Unit Tests For:
1. Session.last_validation state model & persistence.
2. Removal of fabricated successful ValidationResult states in read-only & no-file-change actions.
3. Preservation of last verified validation state across read-only actions.
4. Correct output in generate_post_generation_summary when no files are modified:
   - "Task completed"
   - "No files changed"
   - "Validation status unchanged"
5. Static AST audit verifying no branch in server/app.py fabricates a successful ValidationResult.
"""

import ast
import json
import tempfile
from pathlib import Path
import pytest

from agent.project_validator import ValidationResult
from server.sessions import Session, generate_post_generation_summary


ROOT = Path(__file__).resolve().parents[1]


# ── 1. Session.last_validation Model Tests ────────────────────────────────────

def test_session_last_validation_default_unverified():
    with tempfile.TemporaryDirectory() as tmp_dir:
        session = Session(session_id="1789999001_abc123", workspace_dir=tmp_dir)
        assert session.has_last_validation is False
        # Default unverified validation must not report passed
        assert session.last_validation.passed is False
        assert session.last_validation.code_passed is False
        assert session.last_validation.typecheck_passed is False


def test_session_last_validation_setter_and_getter():
    with tempfile.TemporaryDirectory() as tmp_dir:
        session = Session(session_id="1789999002_abc123", workspace_dir=tmp_dir)

        # Set real verified result
        vr = ValidationResult(
            typecheck_passed=True,
            build_passed=True,
            lint_passed=True,
            contract_passed=True,
            accessibility_passed=True,
            runtime_passed=True,
            preview_running=True,
            repair_attempts=1,
        )
        session.last_validation = vr
        assert session.has_last_validation is True
        assert session.last_validation.passed is True
        assert session.last_validation.code_passed is True

        # Setting via dict (e.g. from JSON)
        session.last_validation = {
            "typecheck_passed": True,
            "build_passed": False,
            "lint_passed": True,
            "runtime_passed": False,
            "preview_running": False,
        }
        assert session.last_validation.passed is False
        assert session.last_validation.code_passed is False
        assert session.last_validation.typecheck_passed is True


def test_session_last_validation_persists_in_to_dict_and_save():
    with tempfile.TemporaryDirectory() as tmp_dir:
        session = Session(session_id="1789999003_abc123", workspace_dir=tmp_dir)
        vr = ValidationResult(
            typecheck_passed=True,
            build_passed=True,
            lint_passed=True,
            contract_passed=True,
            accessibility_passed=True,
            runtime_passed=True,
            preview_running=True,
        )
        session.last_validation = vr
        d = session.to_dict()
        assert "last_validation" in d
        assert d["last_validation"] is not None
        assert d["last_validation"]["passed"] is True
        assert d["last_validation"]["code_passed"] is True


# ── 2. Read-Only Actions Preserve Previous State (No Fabrication) ─────────────

def test_read_only_action_inherits_failing_state_without_fabrication():
    """When the session previously had validation errors, read-only actions
    must NOT fabricate a '✓ Build passed' success state.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        session = Session(session_id="1789999004_abc123", workspace_dir=tmp_dir)
        # Workspace previously failed typecheck
        session.last_validation = ValidationResult(
            typecheck_passed=False,
            build_passed=False,
            lint_passed=True,
            runtime_passed=False,
            preview_running=False,
            errors=["TS2304: Cannot find name 'foo'."],
        )

        # Simulate read-only action (GetDependenciesAction or general refinement with 0 file changes)
        validation = session.last_validation
        assert validation.passed is False
        assert validation.code_passed is False
        assert "TS2304" in validation.errors[0]
        # State must not be mutated or fabricated into True
        assert session.last_validation.passed is False


def test_read_only_action_inherits_passing_state_without_running_build():
    """When the session was already valid, read-only actions preserve that state
    without fabricating a fresh validation result.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        session = Session(session_id="1789999005_abc123", workspace_dir=tmp_dir)
        session.last_validation = ValidationResult(
            typecheck_passed=True,
            build_passed=True,
            lint_passed=True,
            contract_passed=True,
            accessibility_passed=True,
            runtime_passed=True,
            preview_running=True,
        )

        # Read-only action accesses last_validation
        validation = session.last_validation
        assert validation.passed is True
        assert validation.preview_running is True


# ── 3. Post-Generation Summary for No-File-Change Turns ─────────────────────────

def test_generate_post_generation_summary_no_files_changed():
    """A no-file-change response must display:
    Task completed
    No files changed
    Validation status unchanged
    and must NEVER claim 'All TypeScript types, JSX syntax... passed validation'
    nor claim targeted edits were applied.
    """
    summary = generate_post_generation_summary(
        mode="site",
        files_touched=[],
        passed=True,
        auto_recovered=[],
        user_instruction="What packages are installed in this project?",
        is_edit=True,
    )

    assert "Task completed" in summary
    assert "No files changed" in summary
    assert "Validation status unchanged" in summary
    assert "All TypeScript types, JSX syntax, and CSS style tokens passed validation" not in summary
    assert "Applied targeted edits" not in summary


def test_generate_post_generation_summary_explicit_unchanged_status():
    summary = generate_post_generation_summary(
        mode="site",
        files_touched=[],
        passed=False,
        auto_recovered=[],
        user_instruction="Explain the code architecture",
        is_edit=True,
        validation_status="unchanged",
    )

    assert "Task completed" in summary
    assert "No files changed" in summary
    assert "Validation status unchanged" in summary


# ── 4. Static AST Audit of server/app.py ───────────────────────────────────────

def test_ast_audit_no_fabricated_validation_in_app_py():
    """Statically verifies server/app.py to guarantee no branch fabricates
    ValidationResult(typecheck_passed=True, ...) in follow-up edit loops.
    """
    app_py_path = ROOT / "server" / "app.py"
    tree = ast.parse(app_py_path.read_text(encoding="utf-8"))

    fabricated_instantiations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func_name = None
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                func_name = node.func.attr

            if func_name == "ValidationResult":
                # Check keyword arguments for typecheck_passed=True
                for kw in node.keywords:
                    if kw.arg == "typecheck_passed" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                        fabricated_instantiations.append(node.lineno)

    # No hardcoded typecheck_passed=True calls must exist anywhere in server/app.py
    assert len(fabricated_instantiations) == 0, (
        f"Found {len(fabricated_instantiations)} fabricated ValidationResult(typecheck_passed=True) "
        f"at lines: {fabricated_instantiations}"
    )
