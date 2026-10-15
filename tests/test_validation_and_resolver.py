"""
tests/test_validation_and_resolver.py - Unit tests for:
1. resolve_project_path containment resolver (server & agent)
2. ValidationResult blueprint structure, properties, and to_dict
3. Safe snapshot restore in Session.revert_to_checkpoint
"""

import ast
import dataclasses
import sys
import tempfile
import pytest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def load_definitions(path, names, namespace=None):
    """Load production definitions without starting server/model side effects."""
    if namespace is None:
        namespace = {"Path": Path, "dataclasses": dataclasses}
    tree = ast.parse((ROOT / path).read_text(encoding="utf-8-sig"))
    nodes = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n.name in names]
    for node in nodes:
        if hasattr(node, "decorator_list") and not isinstance(node, ast.ClassDef):
            node.decorator_list = []
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), "exec"), namespace)
    return namespace


# Load resolvers cleanly without starting GPU/server
sessions_defs = load_definitions("server/sessions.py", ["resolve_project_path"])
server_defs = load_definitions("server/app.py", ["resolve_project_path"])
agent_defs = load_definitions("agent/agent.py", ["resolve_project_path"])

sessions_resolver = sessions_defs["resolve_project_path"]
server_resolver = server_defs["resolve_project_path"]
agent_resolver = agent_defs["resolve_project_path"]
from agent.project_validator import ValidationResult

from server.sessions import Session


# ── 1. resolve_project_path Tests ─────────────────────────────────────────────

@pytest.mark.parametrize("resolver", [sessions_resolver, server_resolver, agent_resolver])
def test_resolver_accepts_valid_relative_paths(resolver):
    with tempfile.TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir)
        # Simple relative
        resolved = resolver(root, "src/components/Header.tsx")
        assert resolved == (root / "src/components/Header.tsx").resolve()
        assert str(resolved).startswith(str(root.resolve()))

        # Subdirectory relative
        resolved2 = resolver(root, "styles/main.css")
        assert resolved2 == (root / "styles/main.css").resolve()


@pytest.mark.parametrize("resolver", [sessions_resolver, server_resolver, agent_resolver])
def test_resolver_blocks_traversal(resolver):
    with tempfile.TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir)
        escape_payloads = [
            "../../server/app.py",
            "../../../etc/passwd",
            r"..\..\..\Windows\win.ini",
            "foo/../../../../escape.txt",
            "src/components/../../../../sensitive.key",
        ]
        for payload in escape_payloads:
            with pytest.raises(PermissionError, match="outside project root"):
                resolver(root, payload)


@pytest.mark.parametrize("resolver", [sessions_resolver, server_resolver, agent_resolver])
def test_resolver_strips_leading_slashes(resolver):
    with tempfile.TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir)
        # Leading slash should not escape to filesystem root
        resolved = resolver(root, "/src/App.tsx")
        assert resolved == (root / "src/App.tsx").resolve()

        resolved_bs = resolver(root, r"\src\App.tsx")
        assert resolved_bs == (root / "src/App.tsx").resolve()


# ── 2. ValidationResult Structure & Blueprint Tests ───────────────────────────

def test_validation_result_default_fields():
    vr = ValidationResult()
    assert vr.typecheck_passed is False
    assert vr.build_passed is False
    assert vr.lint_passed is False
    assert vr.runtime_passed is False
    assert vr.preview_running is False
    assert vr.code_passed is False
    assert vr.codePassed is False
    assert vr.errors == []
    assert vr.warnings == []
    assert vr.repair_attempts == 0
    assert vr.passed is False


def test_validation_result_blueprint_camel_case_properties():
    vr = ValidationResult(
        typecheck_passed=True,
        build_passed=True,
        lint_passed=True,
        contract_passed=True,
        accessibility_passed=True,
        motion_passed=True,
        runtime_passed=True,
        preview_running=True,
        errors=["warn: unused var"],
        warnings=["style notice"],
        repair_attempts=2,
    )
    assert vr.typecheckPassed is True
    assert vr.buildPassed is True
    assert vr.lintPassed is True
    assert vr.contractPassed is True
    assert vr.accessibilityPassed is True
    assert vr.motionPassed is True
    assert vr.runtimePassed is True
    assert vr.previewRunning is True
    assert vr.codePassed is True
    assert vr.code_passed is True
    assert vr.repairAttempts == 2
    assert vr.passed is True


def test_validation_result_passed_requires_all_three():
    # Typecheck pass alone is not enough for code_passed or passed
    v1 = ValidationResult(typecheck_passed=True, build_passed=False, lint_passed=True, contract_passed=True, accessibility_passed=True, motion_passed=True)
    assert v1.passed is False
    assert v1.code_passed is False

    # Lint pass alone is not enough
    v2 = ValidationResult(typecheck_passed=False, build_passed=True, lint_passed=True, contract_passed=True, accessibility_passed=True, motion_passed=True)
    assert v2.passed is False
    assert v2.code_passed is False

    # All three compilation checks pass: code_passed is True, but passed is False without preview & runtime
    v3 = ValidationResult(typecheck_passed=True, build_passed=True, lint_passed=True, contract_passed=True, accessibility_passed=True, motion_passed=True)
    assert v3.code_passed is True
    assert v3.passed is False

    # Full 7-gate verification with preview running
    v4 = ValidationResult(
        typecheck_passed=True,
        build_passed=True,
        lint_passed=True,
        contract_passed=True,
        accessibility_passed=True,
        motion_passed=True,
        runtime_passed=True,
        preview_running=True,
    )
    assert v4.code_passed is True
    assert v4.passed is True


def test_validation_result_to_dict_includes_both_casing():
    vr = ValidationResult(
        typecheck_passed=True,
        build_passed=True,
        lint_passed=True,
        contract_passed=True,
        accessibility_passed=True,
        motion_passed=True,
        runtime_passed=True,
        preview_running=True,
        repair_attempts=1,
    )
    d = vr.to_dict()
    assert d["typecheck_passed"] is True
    assert d["typecheckPassed"] is True
    assert d["build_passed"] is True
    assert d["buildPassed"] is True
    assert d["lint_passed"] is True
    assert d["lintPassed"] is True
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
    assert d["repair_attempts"] == 1
    assert d["repairAttempts"] == 1
    assert d["passed"] is True


def test_validation_result_interaction_gate_affects_passed():
    """P0-02 Contract Guarantee: interaction gate directly governs overall validation success."""
    # Base 7 gates passing with interaction passed
    vr_good = ValidationResult(
        typecheck_passed=True,
        build_passed=True,
        lint_passed=True,
        contract_passed=True,
        accessibility_passed=True,
        motion_passed=True,
        runtime_passed=True,
        preview_running=True,
        interaction_passed=True,
        interaction_status="passed",
    )
    assert vr_good.passed is True
    assert vr_good.all_gates_passed is True

    # Interaction failed blocks overall passed even if runtime and preview succeeded
    vr_int_failed = ValidationResult(
        typecheck_passed=True,
        build_passed=True,
        lint_passed=True,
        contract_passed=True,
        accessibility_passed=True,
        motion_passed=True,
        runtime_passed=True,
        preview_running=True,
        interaction_passed=False,
        interaction_status="failed",
        interaction_errors=["[Interaction Error] Cart missing button"],
    )
    assert vr_int_failed.passed is False
    assert vr_int_failed.all_gates_passed is False

    # Runtime unverified sets interaction and runtime to 'unverified', blocking passed
    vr_unverified = ValidationResult(
        typecheck_passed=True,
        build_passed=True,
        lint_passed=True,
        contract_passed=True,
        accessibility_passed=True,
        motion_passed=True,
        runtime_passed=True,
        preview_running=True,
        runtime_unverified=True,
    )
    assert vr_unverified.runtime_status == "unverified"
    assert vr_unverified.interaction_status == "unverified"
    assert vr_unverified.passed is False


def test_server_app_exports_canonical_validation_result():
    """P0-02 Remediation: server/app.py exports the exact canonical ValidationResult class from agent.project_validator."""
    from server.app import ValidationResult as ServerVR
    from agent.project_validator import ValidationResult as AgentVR
    assert ServerVR is AgentVR, "server.app.ValidationResult is a duplicate rather than the canonical DTO!"


# ── 3. Session revert_to_checkpoint traversal defense ─────────────────────────

def test_session_revert_guards_traversal_payloads():
    with tempfile.TemporaryDirectory() as tmp_dir:
        session = Session(session_id="1789999999_abcdef", workspace_dir=tmp_dir)
        # Create a checkpoint that contains a malicious relative path
        malicious_checkpoint = {
            "turn_num": 1,
            "timestamp": "2026-09-17 12:00:00",
            "summary": "Malicious checkpoint",
            "files": {
                "../../escaped.txt": "EVIL CONTENT",
                "valid.txt": "SAFE CONTENT",
            },
        }
        session.checkpoints.append(malicious_checkpoint)

        # Reverting should NOT write escaped.txt outside workspace
        outside_file = Path(tmp_dir).parent / "escaped.txt"
        assert not outside_file.exists()

        revert_ok = session.revert_to_checkpoint(1)
        assert revert_ok is True

        # Ensure outside_file was NEVER created
        assert not outside_file.exists()

        # Ensure valid.txt was written safely
        valid_file = Path(tmp_dir) / "valid.txt"
        assert valid_file.exists()
        assert valid_file.read_text(encoding="utf-8") == "SAFE CONTENT"


# ── 4. Component Session Target File Resolution ───────────────────────────────

def test_component_session_target_resolution_fallback():
    from server.sessions import SessionManager
    sm = SessionManager()
    with tempfile.TemporaryDirectory() as tmp_dir:
        session = Session(session_id="1789888888_1234ab", title="Button", mode="component", workspace_dir=tmp_dir)
        (Path(tmp_dir) / "Button.tsx").write_text("export const Button = () => <button>Click</button>;", encoding="utf-8")
        (Path(tmp_dir) / "Button.module.css").write_text(".btn { padding: 8px; }", encoding="utf-8")

        # Without @ mentions, resolve_target_files should find Button.tsx and companion CSS
        targets = sm.resolve_target_files(session, "Make the button rounded with 16px border radius")
        target_names = [p for p, _ in targets]
        assert "Button.tsx" in target_names
        assert "Button.module.css" in target_names


# ── 5. Component Mode Vite & Static Preview Scaffolding ───────────────────────

def test_component_scaffold_creates_all_preview_artifacts():
    scaffold_defs = load_definitions("server/app.py", ["_scaffold_vite_runner"], {
        "Path": Path,
        "_link_node_modules": lambda *args: None,
        "html": __import__("html"),
        "json": __import__("json"),
        "BASE_DIR": ROOT,
        "subprocess": type("SubprocessMock", (), {"run": lambda *a, **k: None})(),
    })
    scaffolder = scaffold_defs["_scaffold_vite_runner"]

    with tempfile.TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir)
        (root / "Card.tsx").write_text("export const Card = () => <div>Card</div>;", encoding="utf-8")
        scaffolder(root, "Card")

        assert (root / "package.json").exists()
        assert (root / "vite.config.ts").exists()
        assert (root / "index.html").exists()
        assert (root / "main.tsx").exists()
        assert (root / "static-preview.html").exists()
        assert (root / "tsconfig.json").exists()

        main_tsx = (root / "main.tsx").read_text(encoding="utf-8")
        assert "from './Card'" in main_tsx


# ── 6. Unified Project Entity Architecture Tests ──────────────────────────────

def test_project_aliases_exported():
    from server.sessions import Project, ProjectManager, project_manager, Session, SessionManager
    assert Project is Session
    assert ProjectManager is SessionManager
    assert isinstance(project_manager, SessionManager)


def test_project_entity_structure_component_and_site():
    """Verify that both component and site generation intents produce the exact same Project entity:
    Project
     ├── workspace/
     ├── Conversation
     ├── Tasks
     ├── Snapshots
     ├── Build state
     └── Preview
    """
    from server.sessions import Project, SessionManager
    sm = SessionManager()

    with tempfile.TemporaryDirectory() as tmp_dir:
        # 1. Component Intent Project
        comp_proj = Project(
            session_id="1789777777_112233",
            title="Lumina",
            mode="component",
            prompt="Build Lumina theme toggle",
            workspace_dir=tmp_dir,
            build_state={
                "typecheck_passed": True,
                "build_passed": True,
                "lint_passed": True,
                "runtime_passed": True,
                "errors": [],
                "warnings": [],
                "repair_attempts": 0,
            },
            current_plan=[
                {"task": "Synthesize Lumina", "status": "completed", "file": "Lumina.tsx"},
                {"task": "Verify types & syntax", "status": "completed"},
                {"task": "Bundle preview runner", "status": "completed"},
            ],
        )

        # 1a. workspace/
        assert comp_proj.workspace_dir == Path(tmp_dir)
        (Path(tmp_dir) / "Lumina.tsx").write_text("export const Lumina = () => <div>Lumina</div>;", encoding="utf-8")
        assert "Lumina.tsx" in comp_proj.get_current_files()

        # 1b. Conversation
        comp_proj.history.append({"role": "user", "content": "Build Lumina theme toggle"})
        comp_proj.history.append({"role": "assistant", "turn_id": 1, "summary": "## What I did\n- Created Lumina"})
        assert len(comp_proj.history) == 2

        # 1c. Tasks
        assert len(comp_proj.current_plan) == 3
        assert comp_proj.current_plan[0]["task"] == "Synthesize Lumina"

        # 1d. Snapshots
        chk_id = comp_proj.create_checkpoint("Initial component Lumina")
        assert chk_id == 1
        assert len(comp_proj.checkpoints) == 1
        assert "Lumina.tsx" in comp_proj.checkpoints[0]["files"]

        # 1e. Build state
        assert comp_proj.build_state["typecheck_passed"] is True
        assert comp_proj.build_state["repair_attempts"] == 0

        # 1f. Preview
        assert comp_proj.preview["url"] == "/preview/1789777777_112233"
        assert comp_proj.preview["symbol"] == "Lumina"

        # Serialization check
        comp_dict = comp_proj.to_dict()
        assert "workspace_dir" in comp_dict
        assert "history" in comp_dict
        assert "current_plan" in comp_dict
        assert "checkpoints" in comp_dict
        assert "build_state" in comp_dict
        assert "preview" in comp_dict

        # 2. Site Intent Project (produces the exact same schema)
        site_proj = Project(
            session_id="1789666666_445566",
            title="Portfolio",
            mode="site",
            prompt="Build dark developer portfolio",
            build_state={
                "typecheck_passed": True,
                "build_passed": True,
                "lint_passed": True,
                "runtime_passed": True,
                "errors": [],
                "warnings": [],
                "repair_attempts": 1,
            },
            current_plan=[
                {"task": "Section: header", "status": "completed"},
                {"task": "Section: hero", "status": "completed"},
                {"task": "Section: footer", "status": "completed"},
            ],
        )

        site_dict = site_proj.to_dict()
        # Ensure identical top-level keys
        assert set(comp_dict.keys()) == set(site_dict.keys())
        assert comp_dict["mode"] == "component"
        assert site_dict["mode"] == "site"


# ── 5. Protocol Action-First & Thought Removal Tests ─────────────────────────

try:
    from agent.agent_protocol import (
        parse_agent_output,
        AgentTurn,
        WriteComponentAction,
        WriteSiteAction,
        RunTestsAction,
        FinishAction,
        AGENT_SYSTEM_PROMPT,
    )
except (ImportError, ModuleNotFoundError):
    from agent_protocol import (
        parse_agent_output,
        AgentTurn,
        WriteComponentAction,
        WriteSiteAction,
        RunTestsAction,
        FinishAction,
        AGENT_SYSTEM_PROMPT,
    )

try:
    from agent.site_prompt import SITE_AGENT_SYSTEM_PROMPT
except (ImportError, ModuleNotFoundError):
    from site_prompt import SITE_AGENT_SYSTEM_PROMPT


def test_system_prompts_do_not_require_thought():
    assert "<thought>" not in AGENT_SYSTEM_PROMPT
    assert "Always output a thought first" not in AGENT_SYSTEM_PROMPT
    assert "<thought>" not in SITE_AGENT_SYSTEM_PROMPT
    assert "Always output a thought first" not in SITE_AGENT_SYSTEM_PROMPT


def test_action_first_json_edit_file():
    payload = """
    {
      "action": "edit_file",
      "statusMessage": "Updating the hero layout",
      "arguments": {
        "path": "src/components/Hero.tsx",
        "content": "import React from 'react'; export function Hero() { return <section>Updated</section>; }"
      }
    }
    """
    turn = parse_agent_output(payload)
    assert turn is not None
    assert isinstance(turn.action, WriteSiteAction)
    assert turn.status_message == "Updating the hero layout"
    assert len(turn.action.files) == 1
    assert turn.action.files[0][0] == "src/components/Hero.tsx"
    assert "Updated" in turn.action.files[0][1]


def test_action_first_json_write_site_multiple_files():
    payload = """
    {
      "action": "write_site",
      "statusMessage": "Generating feature cards",
      "arguments": {
        "files": [
          {"path": "src/components/Features.tsx", "content": "export function Features() { return <div/>; }"},
          {"path": "src/components/Features.css", "content": ".features { display: flex; }"}
        ]
      }
    }
    """
    turn = parse_agent_output(payload)
    assert turn is not None
    assert isinstance(turn.action, WriteSiteAction)
    assert turn.status_message == "Generating feature cards"
    assert len(turn.action.files) == 2


def test_action_first_json_finish():
    payload = """
    {
      "action": "finish",
      "statusMessage": "Completed all requested revisions",
      "arguments": {
        "summary": "Updated Hero typography and responsive cards."
      }
    }
    """
    turn = parse_agent_output(payload)
    assert turn is not None
    assert isinstance(turn.action, FinishAction)
    assert turn.status_message == "Completed all requested revisions"
    assert "Updated Hero typography" in turn.action.summary


def test_legacy_thought_stripped_from_raw_text():
    output = """<thought>
I need to fix the modal backdrop click handler and accessibility roles.
</thought>
<tool_call name="write_component">
<tsx>
import React from 'react';
export function Modal() { return <div role="dialog" />; }
</tsx>
</tool_call>"""
    turn = parse_agent_output(output)
    assert turn is not None
    assert isinstance(turn.action, WriteComponentAction)
    assert "<thought>" not in turn.raw_text
    assert "</thought>" not in turn.raw_text
    assert "<tool_call" in turn.raw_text


def test_legacy_thought_stripped_from_finish():
    output = """<thought>
All validations have passed successfully.
</thought>
<finish>
Component verified.
</finish>"""
    turn = parse_agent_output(output)
    assert turn is not None
    assert isinstance(turn.action, FinishAction)
    assert "<thought>" not in turn.raw_text
    assert "<finish>" in turn.raw_text


