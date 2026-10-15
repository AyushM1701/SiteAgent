"""
tests/test_workbench_control_audit.py

Verifies all backend endpoints, route aliases, contract shapes, and state isolations
required for the Workbench Button and Control Audit (Issue #29).

Covers:
1. Diff API endpoints:
   - GET /api/sessions/<session_id>/diff
   - GET /api/projects/<session_id>/diff
   - GET /api/sessions/<session_id>/diff/<turn_id>
   - GET /api/projects/<session_id>/diff/<turn_id>
   - Baseline synthesis when no checkpoint exists
2. ZIP Export route aliases:
   - GET /api/projects/<session_id>/export
   - GET /api/sessions/<session_id>/export
   - GET /api/projects/<session_id>/zip
   - GET /api/sessions/<session_id>/zip
   - GET /api/export/<session_id>
3. Shell token contract:
   - GET and POST /api/shell-token returns ticket, token, host, port: 5001
4. WebSocket route aliases:
   - /ws/projects/<project_id> and /ws/sessions/<project_id> registered
5. Queue isolation and lifecycle:
   - Queues per project, isolation across project boundaries
"""

import io
import json
import tempfile
import zipfile
from pathlib import Path

import pytest
from server.app import (
    app,
    session_manager,
    _dispatch_prompt_queue,
    _project_queued_prompts,
)
from server.sessions import Session


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


@pytest.fixture
def audit_session():
    """Sets up a test session with sample files for diff and zip audit."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        session_id = "1789999999_a1b2c3"
        session = Session(session_id=session_id, workspace_dir=tmp_dir, title="Audit Site")
        session_manager._sessions[session_id] = session

        # Add initial files
        (tmp_path / "src").mkdir(parents=True, exist_ok=True)
        (tmp_path / "src" / "App.tsx").write_text("export default function App() { return <div>Audit App</div>; }\n", encoding="utf-8")
        (tmp_path / "package.json").write_text('{"name": "audit-project", "version": "1.0.0"}\n', encoding="utf-8")
        (tmp_path / "index.html").write_text("<!DOCTYPE html><html><body><div id='root'></div></body></html>\n", encoding="utf-8")

        yield session

        # Cleanup
        session_manager._sessions.pop(session_id, None)
        _project_queued_prompts.pop(session_id, None)


def test_shell_token_contract(client):
    """GET and POST /api/shell-token must return ticket, token, host, and port 5001."""
    # Test GET
    resp_get = client.get("/api/shell-token")
    assert resp_get.status_code == 200
    data_get = resp_get.get_json()
    assert "ticket" in data_get
    assert "token" in data_get
    assert data_get["ticket"] == data_get["token"]
    assert len(data_get["ticket"]) > 10
    assert data_get["port"] == 5001
    assert "host" in data_get

    # Test POST
    resp_post = client.post("/api/shell-token")
    assert resp_post.status_code == 200
    data_post = resp_post.get_json()
    assert "ticket" in data_post
    assert "token" in data_post
    assert data_post["ticket"] == data_post["token"]
    assert data_post["port"] == 5001


def test_diff_endpoints_parameterized_and_unparameterized(client, audit_session):
    """Tests all 4 diff route variants return the canonical diff envelope."""
    sid = audit_session.session_id

    endpoints = [
        f"/api/sessions/{sid}/diff",
        f"/api/projects/{sid}/diff",
        f"/api/sessions/{sid}/diff/1",
        f"/api/projects/{sid}/diff/1",
    ]

    for ep in endpoints:
        resp = client.get(ep)
        assert resp.status_code == 200, f"Endpoint {ep} failed with {resp.status_code}"
        data = resp.get_json()
        assert "turnId" in data, f"Missing turnId in {ep}"
        assert "files" in data, f"Missing files in {ep}"
        assert isinstance(data["files"], dict)
        # Should synthesize baseline diff for initial files
        assert "src/App.tsx" in data["files"]
        file_diff = data["files"]["src/App.tsx"]
        assert "before" in file_diff
        assert "after" in file_diff
        assert "patch" in file_diff
        assert "Audit App" in file_diff["after"]


def test_zip_export_aliases(client, audit_session):
    """Tests all 5 ZIP export endpoints return a valid ZIP archive with site files."""
    sid = audit_session.session_id

    endpoints = [
        f"/api/projects/{sid}/export",
        f"/api/sessions/{sid}/export",
        f"/api/projects/{sid}/zip",
        f"/api/sessions/{sid}/zip",
        f"/api/export/{sid}",
    ]

    for ep in endpoints:
        resp = client.get(ep)
        assert resp.status_code == 200, f"Endpoint {ep} failed with {resp.status_code}"
        assert "application/zip" in resp.headers.get("Content-Type", "")

        # Verify valid zip
        zf = zipfile.ZipFile(io.BytesIO(resp.data))
        names = zf.namelist()
        assert any(n.endswith("src/App.tsx") for n in names)
        assert any(n.endswith("package.json") for n in names)
        assert any(n.endswith("index.html") for n in names)


def test_websocket_routes_registered():
    """Verify WebSocket routes /ws/projects/<project_id> and /ws/sessions/<project_id> are registered."""
    routes = [rule.rule for rule in app.url_map.iter_rules()]
    assert any("/ws/projects/" in r for r in routes)
    assert any("/ws/sessions/" in r for r in routes)


def test_queue_isolation_across_projects(audit_session):
    """Verify project queue isolation so queues don't leak between projects."""
    p1 = audit_session.session_id
    p2 = "1789999999_e4f5a6"

    _dispatch_prompt_queue(p1, "First prompt for P1")
    _dispatch_prompt_queue(p1, "Second prompt for P1")
    _dispatch_prompt_queue(p2, "First prompt for P2")

    assert len(_project_queued_prompts[p1]) == 2
    assert len(_project_queued_prompts[p2]) == 1
    assert _project_queued_prompts[p1][0]["prompt"] == "First prompt for P1"
    assert _project_queued_prompts[p2][0]["prompt"] == "First prompt for P2"

    # Cleanup
    _project_queued_prompts.pop(p1, None)
    _project_queued_prompts.pop(p2, None)
