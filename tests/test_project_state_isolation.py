"""
tests/test_project_state_isolation.py - Tests for complete project state isolation.

Verifies:
1. Frontend startNewProject() state isolation criteria:
   - currentProjectId = null
   - files = {}
   - messages = []
   - logs = []
   - selection = null
   - visualScore = null/undefined
   - turn metrics = null/0
   - workspace closed
   - Inspector project state cleared
   - Global system state preserved (model loaded, GPU readiness, server connection, theme preference)
2. Backend session state isolation between distinct sessions.
"""
import os

import sys
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from server.sessions import session_manager, Session


def test_frontend_start_new_project_state_isolation():
    """Run the TypeScript/Node state isolation runner to verify all stores reset properly."""
    script_path = BASE_DIR / "scripts" / "test_session_isolation.mjs"
    assert script_path.exists(), f"Script {script_path} does not exist"

    # Use npx --yes tsx to execute test_session_isolation.mjs
    res = subprocess.run(
        ["npx", "--yes", "tsx", str(script_path)],
        cwd=str(BASE_DIR),
        capture_output=True,
        text=True,
        shell=(os.name == "nt"),  # npx is npx.cmd on Windows
    )
    assert res.returncode == 0, f"Frontend state isolation test failed:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
    assert "ALL ACCEPTANCE CRITERIA VERIFIED SUCCESSFULLY!" in res.stdout


def test_backend_session_isolation(tmp_path, monkeypatch):
    """Verify that distinct backend sessions never leak files, turns, or checkpoints."""
    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)
    import server.sessions
    monkeypatch.setattr(server.sessions, "SESSIONS_DIR", sessions_dir)

    # Create Session A with workspace in tmp_path
    ws_a = tmp_path / "ws_a"
    ws_a.mkdir(parents=True, exist_ok=True)
    (ws_a / "src").mkdir()
    (ws_a / "src" / "Hero.tsx").write_text("export const Hero = () => <button>Hero</button>;", encoding="utf-8")

    sess_a = session_manager.create_session("Session A Component", mode="component", workspace_dir=str(ws_a))
    sess_a.history.append({
        "turn": 1,
        "prompt": "Create Hero button",
        "files_touched": ["src/Hero.tsx"],
    })
    sess_a.create_checkpoint("Turn 1 - Hero")
    sess_a.save()

    # Create Session B with workspace in tmp_path
    ws_b = tmp_path / "ws_b"
    ws_b.mkdir(parents=True, exist_ok=True)
    sess_b = session_manager.create_session("Session B Dashboard", mode="site", workspace_dir=str(ws_b))

    # Verify Session B starts clean with zero state leakage from Session A
    assert sess_b.session_id != sess_a.session_id
    assert len(sess_b.history) == 0
    assert len(sess_b.checkpoints) == 0
    assert "src/Hero.tsx" not in sess_b.get_current_files()

    # Verify Session A retained its independent state
    reloaded_a = session_manager.get_session(sess_a.session_id)
    assert reloaded_a is not None
    assert len(reloaded_a.history) == 1
    assert len(reloaded_a.checkpoints) == 1
    assert "src/Hero.tsx" in reloaded_a.get_current_files()

    # Verify Session B has no history or leaked files when reloaded
    reloaded_b = session_manager.get_session(sess_b.session_id)
    assert reloaded_b is not None
    assert len(reloaded_b.history) == 0
    assert len(reloaded_b.checkpoints) == 0
    assert "src/Hero.tsx" not in reloaded_b.get_current_files()
