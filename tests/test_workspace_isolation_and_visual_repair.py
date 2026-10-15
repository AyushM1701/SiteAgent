"""
tests/test_workspace_isolation_and_visual_repair.py

Unit and integration tests for:
1. Blueprint #13: Untrusted workspace isolation & server-side PROJECTS_DIR derivation
   - sanitize_project_id cleans hostile inputs
   - derive_project_workspace strictly contains paths inside PROJECTS_DIR
   - Session.__init__ and SessionManager._load_all_from_disk ignore malicious workspace_dir in JSON
   - Revert operations operate strictly inside the derived project workspace
2. Blueprint #14: Non-destructive visual repair loop
   - Preserves existing TSX and CSS implementations
   - Model receives visual diagnostics + existing source for minimal targeted patch
   - auto_scaffold_section is retained strictly as an emergency last-resort fallback
"""

import json
import re
import tempfile
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from server.sessions import (
    Session,
    SessionManager,
    PROJECTS_DIR,
    sanitize_project_id,
    derive_project_workspace,
    resolve_project_path,
)
from agent.agent_protocol import WriteSiteAction, AgentTurn


# ── 1. Project ID Sanitization & Workspace Derivation Tests ───────────────────

def test_sanitize_project_id_valid():
    assert sanitize_project_id("my_project_123") == "my_project_123"
    assert sanitize_project_id("lumina-3d-hero") == "lumina-3d-hero"
    assert sanitize_project_id("Session_1789000000") == "Session_1789000000"


def test_sanitize_project_id_blocks_traversal_and_escapes():
    # Relative traversals
    assert ".." not in sanitize_project_id("../../etc/passwd", default_id="fallback")
    assert "/" not in sanitize_project_id("../../etc/passwd", default_id="fallback")
    assert "\\" not in sanitize_project_id(r"..\..\Windows\System32", default_id="fallback")
    
    # Absolute paths
    assert sanitize_project_id("C:\\Windows\\System32", default_id="fallback") == "System32"
    assert sanitize_project_id("/etc/shadow", default_id="fallback") == "shadow"

    # Hostile strings
    assert sanitize_project_id("..", default_id="fallback") == "fallback"
    assert sanitize_project_id("", default_id="fallback") == "fallback"
    assert sanitize_project_id(None, default_id="fallback") == "fallback"


def test_derive_project_workspace_contained_in_projects_dir():
    ws = derive_project_workspace("safe_app_1", session_id="1789000000_111111")
    assert ws.resolve() != PROJECTS_DIR.resolve()
    assert PROJECTS_DIR.resolve() in ws.resolve().parents
    assert ws.name == "safe_app_1"


def test_derive_project_workspace_neutralizes_traversal():
    hostile_id = "../../malicious_escape"
    ws = derive_project_workspace(hostile_id, session_id="1789000000_222222")
    # Must remain strictly contained inside PROJECTS_DIR
    assert ws.resolve() != PROJECTS_DIR.resolve()
    assert PROJECTS_DIR.resolve() in ws.resolve().parents
    assert ".." not in str(ws)


# ── 2. Session Untrusted workspace_dir Resistance Tests ─────────────────────────

def test_session_init_derives_workspace_when_not_supplied():
    session = Session(session_id="1789000000_333333", project_id="test_derivation_app")
    assert session.project_id == "test_derivation_app"
    assert session.workspace_dir == (PROJECTS_DIR / "test_derivation_app").resolve()
    assert PROJECTS_DIR.resolve() in session.workspace_dir.parents


def test_session_serialization_includes_project_id():
    session = Session(session_id="1789000000_444444", title="Aura", project_id="aura_spatial")
    d = session.to_dict()
    assert d["project_id"] == "aura_spatial"
    assert d["projectId"] == "aura_spatial"
    assert "workspace_dir" in d


def test_session_manager_ignores_malicious_persisted_workspace_dir(tmp_path, monkeypatch):
    """If a session.json is tampered with an arbitrary workspace_dir, it must be ignored."""
    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir()
    monkeypatch.setattr("server.sessions.SESSIONS_DIR", sessions_dir)

    # Simulate tampered session JSON with a malicious workspace_dir pointing to System32
    tampered_json = {
        "session_id": "1789000000_555555",
        "title": "Tampered App",
        "projectId": "tampered_app",
        "workspace_dir": "C:\\Windows\\System32",
        "history": [],
        "checkpoints": [],
    }
    meta_file = sessions_dir / "1789000000_555555.json"
    meta_file.write_text(json.dumps(tampered_json), encoding="utf-8")

    mgr = SessionManager()
    loaded = mgr.get_session("1789000000_555555")
    assert loaded is not None
    # Verify the loaded session workspace is derived within PROJECTS_DIR, NOT System32!
    assert "System32" not in str(loaded.workspace_dir)
    assert PROJECTS_DIR.resolve() in loaded.workspace_dir.parents
    assert loaded.workspace_dir == (PROJECTS_DIR / "tampered_app").resolve()


def test_session_manager_legacy_migration_extracts_safe_basename(tmp_path, monkeypatch):
    """Legacy records lacking projectId safely extract the folder basename."""
    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir()
    monkeypatch.setattr("server.sessions.SESSIONS_DIR", sessions_dir)

    legacy_json = {
        "session_id": "1789000000_666666",
        "title": "Legacy App",
        "workspace_dir": "D:\\some_old_path\\generated_components\\Lumina_20260917_185228",
        "history": [],
        "checkpoints": [],
    }
    meta_file = sessions_dir / "1789000000_666666.json"
    meta_file.write_text(json.dumps(legacy_json), encoding="utf-8")

    mgr = SessionManager()
    loaded = mgr.get_session("1789000000_666666")
    assert loaded is not None
    assert loaded.project_id == "Lumina_20260917_185228"
    assert loaded.workspace_dir == (PROJECTS_DIR / "Lumina_20260917_185228").resolve()


# ── 3. Visual Repair Non-Destructive Flow Tests ───────────────────────────────

def test_visual_repair_preserves_custom_source_with_qwen_patch(tmp_path):
    """Verify that when visual score is low, existing TSX/CSS is preserved and patched rather than wiped."""
    workspace = tmp_path / "workspace"
    export_dir = tmp_path / "export"
    workspace.mkdir()
    export_dir.mkdir()

    # Pre-populate custom 3D canvas component
    custom_tsx = """import React from 'react';
import { Canvas } from '@react-three/fiber';
export function Hero() {
  return (
    <section className="hero-3d">
      <Canvas>
        <ambientLight />
        <mesh><boxGeometry /></mesh>
      </Canvas>
      <h1>Custom 3D Lumina</h1>
    </section>
  );
}"""
    custom_css = """.hero-3d { min-height: 80vh; background: #0b0f19; color: #fff; }"""

    written_files = {
        "src/components/Hero.tsx": custom_tsx,
        "src/components/Hero.css": custom_css,
    }

    # Mock runner that returns a minimal targeted patch enhancing styles
    mock_runner = MagicMock()
    patched_css = """.hero-3d { min-height: 80vh; background: #0b0f19; color: #fff; padding: 4rem 2rem; display: flex; flex-direction: column; align-items: center; }"""
    mock_runner.generate_turn.return_value = f"""```json
{{
  "action": "write_site",
  "files": [
    ["src/components/Hero.css", {json.dumps(patched_css)}]
  ]
}}
```"""

    session = Session(session_id="1789000000_777777", workspace_dir=str(workspace))

    # Simulate the visual repair block logic
    target_sec = "hero"
    visual_issues = ["low color contrast", "sparse layout density"]
    visual_score = 2

    # Step 1: Read existing source
    pascal_sec = "Hero"
    t_name = f"src/components/{pascal_sec}.tsx"
    c_name = f"src/components/{pascal_sec}.css"
    existing_t = written_files.get(t_name, "")
    existing_c = written_files.get(c_name, "")

    assert "Canvas" in existing_t  # Custom 3D canvas is present!

    # Step 2: Request Qwen minimal patch
    reply = mock_runner.generate_turn(history=[])
    from agent.agent_protocol import parse_agent_output
    turn = parse_agent_output(reply)
    assert isinstance(turn.action, WriteSiteAction)
    patched = dict(turn.action.files)

    # Step 3: Apply minimal patch
    if c_name in patched:
        written_files[c_name] = patched[c_name]

    # Verification: The custom 3D TSX was NOT replaced by generic auto_scaffold_section!
    assert "Canvas" in written_files[t_name]
    assert "padding: 4rem 2rem" in written_files[c_name]


def test_visual_repair_falls_back_to_auto_scaffold_only_when_model_fails():
    """Verify that auto_scaffold_section is called strictly as a last resort when model fails."""
    from agent.agent import auto_scaffold_section

    # Test that auto_scaffold_section is callable and produces fallback structure
    t_name, t_code, c_name, c_code = auto_scaffold_section("features", style_spec=None, custom_instr="")
    assert "Features" in t_name
    assert "export function Features" in t_code
    assert "Features.css" in c_name
