"""
tests/test_diff_contract.py - Canonical Diff Viewer API Contract Tests

Tests the canonical contract required by Issue #3:
{
  "turnId": 3,
  "files": {
    "src/components/Hero.tsx": {
      "before": "...",
      "after": "...",
      "patch": "..."
    }
  }
}

Validates:
1. Canonical response schema on GET /api/sessions/<id>/diff/<turn_id>
2. All changed files present with non-empty before / after / patch
3. Initial turn 1 baseline behavior (before is empty, after contains code)
4. Read-only zero-change turn behavior (files is {}, files_touched is [])
5. Alias route GET /api/projects/<id>/diff/<turn_id> parity
6. Revert endpoint uses the exact same turn identifier and restores file state
"""

import json
import tempfile
from pathlib import Path

import pytest
from server.app import app
from server.sessions import Session, session_manager


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def mock_session():
    """Creates a temporary isolated session with multiple checkpoint turns."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        session_id = "1789000000_998877"
        session = Session(session_id=session_id, workspace_dir=tmp_dir)
        session_manager._sessions[session_id] = session

        # Setup turn 1: Initial files
        app_v1 = "export default function App() { return <div>Version 1</div>; }\n"
        hero_v1 = "export function Hero() { return <h1>Original Hero</h1>; }\n"
        (tmp_path / "src").mkdir(parents=True, exist_ok=True)
        (tmp_path / "src" / "App.tsx").write_text(app_v1, encoding="utf-8")
        (tmp_path / "src" / "Hero.tsx").write_text(hero_v1, encoding="utf-8")

        session.snapshot_manager.commit_task_success(
            session=session,
            summary="Synthesized initial site with App and Hero",
            files_touched=["src/App.tsx", "src/Hero.tsx"],
        )
        session.history.append({
            "turn_id": 1,
            "role": "assistant",
            "summary": "Synthesized initial site with App and Hero",
            "files_touched": ["src/App.tsx", "src/Hero.tsx"],
        })

        # Setup turn 2: Edit Hero.tsx
        hero_v2 = "export function Hero() { return <h1>Updated Hero with CTA</h1>; }\n"
        (tmp_path / "src" / "Hero.tsx").write_text(hero_v2, encoding="utf-8")

        session.snapshot_manager.commit_task_success(
            session=session,
            summary="Refined Hero with new CTA heading",
            files_touched=["src/Hero.tsx"],
        )
        session.history.append({
            "turn_id": 2,
            "role": "assistant",
            "summary": "Refined Hero with new CTA heading",
            "files_touched": ["src/Hero.tsx"],
        })

        # Setup turn 3: Read-only query (0 files changed)
        session.checkpoints.append({
            "turn_num": 3,
            "id": 3,
            "summary": "Inspected dependencies without modifying files",
            "manifest": dict(session.checkpoints[-1].get("manifest", {})),
            "changed_files": [],
            "changed_blobs": {},
            "diffs": {},
            "files": session.snapshot_manager.scan_workspace_files(),
        })
        session.history.append({
            "turn_id": 3,
            "role": "assistant",
            "summary": "Inspected dependencies without modifying files",
            "files_touched": [],
        })
        session.save()

        try:
            yield session, tmp_path
        finally:
            session_manager._sessions.pop(session_id, None)


def test_canonical_diff_contract_turn_2(client, mock_session):
    """Verifies Turn 2 diff response matches the canonical contract."""
    session, _ = mock_session
    res = client.get(f"/api/sessions/{session.session_id}/diff/2")
    assert res.status_code == 200

    data = res.get_json()
    # Canonical top-level keys
    assert data["turnId"] == 2
    assert "files" in data
    assert isinstance(data["files"], dict)

    # Changed files check
    assert "src/Hero.tsx" in data["files"]
    hero_diff = data["files"]["src/Hero.tsx"]

    # Each entry must contain before, after, patch
    assert "before" in hero_diff
    assert "after" in hero_diff
    assert "patch" in hero_diff

    # Content must be non-empty and reflect actual changes
    assert "Original Hero" in hero_diff["before"]
    assert "Updated Hero with CTA" in hero_diff["after"]
    assert "-export function Hero() { return <h1>Original Hero</h1>; }" in hero_diff["patch"]
    assert "+export function Hero() { return <h1>Updated Hero with CTA</h1>; }" in hero_diff["patch"]

    # Backward compatibility fields
    assert "turn_id" in data and data["turn_id"] == 2
    assert "files_touched" in data and "src/Hero.tsx" in data["files_touched"]
    assert "original_files" in data and "src/Hero.tsx" in data["original_files"]
    assert "modified_files" in data and "src/Hero.tsx" in data["modified_files"]


def test_canonical_diff_contract_baseline_turn_1(client, mock_session):
    """Verifies Turn 1 (initial generation) returns canonical structure with before=''."""
    session, _ = mock_session
    res = client.get(f"/api/sessions/{session.session_id}/diff/1")
    assert res.status_code == 200

    data = res.get_json()
    assert data["turnId"] == 1
    assert "files" in data
    assert "src/App.tsx" in data["files"]
    assert "src/Hero.tsx" in data["files"]

    app_diff = data["files"]["src/App.tsx"]
    assert app_diff["before"] == ""
    assert "Version 1" in app_diff["after"]
    assert app_diff["patch"] != ""


def test_canonical_diff_contract_read_only_turn_3(client, mock_session):
    """Verifies a read-only turn with 0 file changes returns empty files dictionary."""
    session, _ = mock_session
    res = client.get(f"/api/sessions/{session.session_id}/diff/3")
    assert res.status_code == 200

    data = res.get_json()
    assert data["turnId"] == 3
    assert data["files"] == {}
    assert data["files_touched"] == []


def test_canonical_diff_contract_alias_project_route(client, mock_session):
    """Verifies GET /api/projects/<id>/diff/<turn_id> behaves identically to sessions route."""
    session, _ = mock_session
    res1 = client.get(f"/api/sessions/{session.session_id}/diff/2")
    res2 = client.get(f"/api/projects/{session.session_id}/diff/2")
    assert res1.status_code == 200
    assert res2.status_code == 200
    assert res1.get_json() == res2.get_json()


def test_revert_uses_same_turn_identifier(client, mock_session):
    """Verifies POST /api/sessions/<id>/revert/<turn_id> uses the exact same turn identifier and restores state."""
    session, tmp_path = mock_session

    # In turn 2, Hero.tsx has "Updated Hero with CTA"
    assert "Updated Hero with CTA" in (tmp_path / "src" / "Hero.tsx").read_text(encoding="utf-8")

    # Revert to turn 1 using the turn identifier 1
    res = client.post(f"/api/sessions/{session.session_id}/revert/1")
    assert res.status_code == 200
    data = res.get_json()
    assert data.get("success") is True

    # Check that Hero.tsx was reverted back to Version 1 content
    reverted_hero = (tmp_path / "src" / "Hero.tsx").read_text(encoding="utf-8")
    assert "Original Hero" in reverted_hero
    assert "Updated Hero with CTA" not in reverted_hero
