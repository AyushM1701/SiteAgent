"""
tests/test_monaco_save_lifecycle.py - Tests for Monaco Editor Manual File Save Lifecycle

Validates Issue #5:
1. PATCH /api/projects/:projectId/file persists edits to disk and session
2. Saves trigger 4-gate workspace verification and update session.last_validation
3. Saves capture pre-task snapshots, create versioned checkpoints, and append history turns
4. Path traversal payloads outside project root are blocked with 403
5. Agent synchronization: context_builder immediately reads updated disk state
6. Alias route PATCH /api/sessions/:sessionId/file parity
"""

import json
import tempfile
from pathlib import Path

import pytest
from server.app import app
from server.sessions import Session, session_manager
from agent.context_builder import ContextBuilder, context_builder


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def sample_editor_session():
    """Sets up an isolated session workspace with valid site files."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        session_id = "1789000000_554433"
        session = Session(session_id=session_id, workspace_dir=tmp_dir, title="Portfolio Studio")
        session_manager._sessions[session_id] = session

        (tmp_path / "src").mkdir(parents=True, exist_ok=True)
        (tmp_path / "src" / "App.tsx").write_text(
            "import React from 'react';\nexport default function App() { return <h1>Original Studio</h1>; }\n",
            encoding="utf-8",
        )
        (tmp_path / "src" / "App.css").write_text("body { margin: 0; background: #000; }\n", encoding="utf-8")
        (tmp_path / "package.json").write_text(
            json.dumps({
                "name": "portfolio-studio",
                "version": "1.0.0",
                "scripts": {"build": "vite build", "dev": "vite"},
                "dependencies": {"react": "^19.0.0", "react-dom": "^19.0.0"},
            }),
            encoding="utf-8",
        )

        session.snapshot_manager.commit_task_success(
            session=session,
            summary="Synthesized initial site",
            files_touched=["src/App.tsx", "src/App.css"],
        )

        try:
            yield session, tmp_path
        finally:
            session_manager._sessions.pop(session_id, None)


def test_manual_file_save_persists_to_disk_and_session(client, sample_editor_session):
    """Verifies PATCH /api/projects/:projectId/file writes to disk and updates session files."""
    session, tmp_path = sample_editor_session
    new_content = "import React from 'react';\nexport default function App() { return <h1>Manually Edited Studio</h1>; }\n"

    res = client.patch(
        f"/api/projects/{session.session_id}/file",
        json={"file": "src/App.tsx", "content": new_content},
    )

    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["file"] == "src/App.tsx"
    assert "turnId" in data

    # Verify written to disk
    disk_content = (tmp_path / "src" / "App.tsx").read_text(encoding="utf-8")
    assert disk_content == new_content

    # Verify session scans updated file
    current_files = session.get_current_files()
    assert current_files["src/App.tsx"] == new_content


def test_manual_file_save_triggers_validation_and_updates_last_validation(client, sample_editor_session):
    """Verifies that saving a file executes workspace verification and updates session.last_validation."""
    session, _ = sample_editor_session
    new_content = "import React from 'react';\nexport default function App() { return <p>Valid JSX</p>; }\n"

    res = client.patch(
        f"/api/projects/{session.session_id}/file",
        json={"file": "src/App.tsx", "content": new_content},
    )

    assert res.status_code == 200
    data = res.get_json()
    assert "validation" in data
    assert "build_state" in data

    # Verify session authoritative validation is updated
    assert session.has_last_validation
    assert session.last_validation is not None
    assert isinstance(session.build_state, dict)


def test_manual_file_save_creates_checkpoint_and_history(client, sample_editor_session):
    """Verifies that saving creates a versioned checkpoint and appends a history turn."""
    session, _ = sample_editor_session
    initial_checkpoints = len(session.checkpoints)
    initial_history = len(session.history)

    res = client.patch(
        f"/api/projects/{session.session_id}/file",
        json={"file": "src/App.css", "content": "body { margin: 0; background: #111; }\n"},
    )
    assert res.status_code == 200
    data = res.get_json()

    # Checkpoints created: 1 pre-task snapshot + 1 task commit = +2 checkpoints
    assert len(session.checkpoints) == initial_checkpoints + 2
    latest_chk = session.checkpoints[-1]
    assert "src/App.css" in (latest_chk.get("changed_files") or [])

    # History record created
    assert len(session.history) == initial_history + 1
    latest_turn = session.history[-1]
    assert latest_turn["turn_id"] == data["turnId"]
    assert "src/App.css" in latest_turn.get("files_touched", [])


def test_manual_file_save_blocks_path_traversal(client, sample_editor_session):
    """Verifies that path traversal payloads escaping project root return 403."""
    session, tmp_path = sample_editor_session
    traversal_path = "../../outside_payload.txt"

    res = client.patch(
        f"/api/projects/{session.session_id}/file",
        json={"file": traversal_path, "content": "malicious content"},
    )

    assert res.status_code == 403
    assert "Path traversal blocked" in res.get_json().get("error", "")
    assert not (tmp_path.parent / "outside_payload.txt").exists()


def test_agent_synchronization_reads_manual_edit(client, sample_editor_session):
    """Verifies that subsequent agent context building sees the manually edited content on disk."""
    session, _ = sample_editor_session
    edited_jsx = "export default function App() { return <div className='art-gallery'>Art Space</div>; }\n"

    # Save edit
    res = client.patch(
        f"/api/projects/{session.session_id}/file",
        json={"file": "src/App.tsx", "content": edited_jsx},
    )
    assert res.status_code == 200

    # Build agent context
    builder = ContextBuilder()
    context = builder.build_context(
        session=session,
        new_instruction="Update gallery lighting",
    )

    # Agent context must contain the manual edit
    assert "art-gallery" in context.prompt_text
    assert "Art Space" in context.prompt_text


def test_sessions_alias_file_save_endpoint(client, sample_editor_session):
    """Verifies that PATCH /api/sessions/:sessionId/file behaves identically to projects route."""
    session, tmp_path = sample_editor_session
    updated_css = ".card { border-radius: 8px; }\n"

    res = client.patch(
        f"/api/sessions/{session.session_id}/file",
        json={"file": "src/App.css", "content": updated_css},
    )

    assert res.status_code == 200
    assert res.get_json()["success"] is True
    assert (tmp_path / "src" / "App.css").read_text(encoding="utf-8") == updated_css


def test_delete_project_file_endpoint(client, sample_editor_session):
    """Verifies that DELETE /api/projects/:projectId/file deletes file and updates session."""
    session, tmp_path = sample_editor_session
    css_file = tmp_path / "src" / "App.css"
    assert css_file.exists()

    res = client.delete(
        f"/api/projects/{session.session_id}/file",
        json={"file": "src/App.css"},
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert not css_file.exists()
    assert "src/App.css" not in session.get_current_files()

