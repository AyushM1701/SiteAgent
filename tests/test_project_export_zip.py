"""
tests/test_project_export_zip.py - Tests for Real Project ZIP Export

Validates Issue #4:
- GET /api/projects/:projectId/export
- GET /api/sessions/:sessionId/export
- Return MIME application/zip
- Downloaded file is a valid ZIP archive
- Includes all required project files: src/, public/, package.json, vite.config.ts, tsconfig.json, index.html
- Excludes: node_modules/, dist/, .git/, .snapshots/, .pyc, logs, temporary screenshots, session metadata
- Project can be extracted and has complete runner structure for building
- Legacy /api/download/:projectId redirects cleanly to /api/projects/:projectId/export
"""

import io
import json
import tempfile
import zipfile
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
def sample_project_session():
    """Sets up an isolated session workspace with valid site files and unwanted metadata/artifacts."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        session_id = "1789000000_887766"
        session = Session(session_id=session_id, workspace_dir=tmp_dir, title="Portfolio Studio")
        session_manager._sessions[session_id] = session

        # 1. Required site files
        (tmp_path / "src").mkdir(parents=True, exist_ok=True)
        (tmp_path / "src" / "App.tsx").write_text(
            "import React from 'react';\nexport default function App() { return <h1>Studio</h1>; }\n",
            encoding="utf-8",
        )
        (tmp_path / "src" / "App.css").write_text("body { margin: 0; background: #000; }\n", encoding="utf-8")
        (tmp_path / "src" / "main.tsx").write_text(
            "import React from 'react';\nimport ReactDOM from 'react-dom/client';\nimport App from './App';\n"
            "ReactDOM.createRoot(document.getElementById('root')!).render(<App />);\n",
            encoding="utf-8",
        )
        (tmp_path / "public").mkdir(parents=True, exist_ok=True)
        (tmp_path / "public" / "favicon.svg").write_text("<svg></svg>", encoding="utf-8")
        (tmp_path / "index.html").write_text("<!DOCTYPE html><html><body><div id='root'></div></body></html>", encoding="utf-8")
        (tmp_path / "vite.config.ts").write_text("import { defineConfig } from 'vite';\nexport default defineConfig({});\n", encoding="utf-8")
        (tmp_path / "tsconfig.json").write_text('{"compilerOptions": {"target": "ES2020"}}\n', encoding="utf-8")
        (tmp_path / "package.json").write_text(
            json.dumps({
                "name": "portfolio-studio",
                "version": "1.0.0",
                "scripts": {"build": "vite build", "dev": "vite"},
                "dependencies": {"react": "^19.0.0", "react-dom": "^19.0.0"},
                "devDependencies": {"vite": "^6.0.0", "typescript": "^5.7.0"},
            }, indent=2),
            encoding="utf-8",
        )

        # 2. Excluded directories and files
        (tmp_path / "node_modules" / "some_pkg").mkdir(parents=True, exist_ok=True)
        (tmp_path / "node_modules" / "some_pkg" / "index.js").write_text("// dummy node module", encoding="utf-8")

        (tmp_path / ".git" / "objects").mkdir(parents=True, exist_ok=True)
        (tmp_path / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")

        (tmp_path / ".snapshots" / "blobs").mkdir(parents=True, exist_ok=True)
        (tmp_path / ".snapshots" / "blobs" / "sha123").write_text("snapshot blob", encoding="utf-8")

        (tmp_path / ".vite" / "deps").mkdir(parents=True, exist_ok=True)
        (tmp_path / ".vite" / "deps" / "react.js").write_text("cached vite dep", encoding="utf-8")

        (tmp_path / "__pycache__").mkdir(parents=True, exist_ok=True)
        (tmp_path / "__pycache__" / "temp.pyc").write_bytes(b"\x00\x01\x02")

        (tmp_path / "history.jsonl").write_text('{"turn": 1}\n', encoding="utf-8")
        (tmp_path / "session.json").write_text('{"id": "1789000000_887766"}\n', encoding="utf-8")
        (tmp_path / "task_log.txt").write_text("agent trace log", encoding="utf-8")
        (tmp_path / "debug.log").write_text("debug log entry", encoding="utf-8")
        (tmp_path / "screenshot_turn1.webp").write_bytes(b"RIFFWEBP")
        (tmp_path / "visual_judge_score.json").write_text('{"score": 4}', encoding="utf-8")

        try:
            yield session, tmp_path
        finally:
            session_manager._sessions.pop(session_id, None)


def test_export_project_zip_valid_archive(client, sample_project_session):
    """Verifies that GET /api/projects/:projectId/export returns a valid ZIP file with correct MIME type."""
    session, _ = sample_project_session
    res = client.get(f"/api/projects/{session.session_id}/export")

    assert res.status_code == 200
    assert res.mimetype == "application/zip"
    assert "attachment" in res.headers.get("Content-Disposition", "")
    assert "Portfolio_Studio.zip" in res.headers.get("Content-Disposition", "")

    # Check zip integrity
    bio = io.BytesIO(res.data)
    with zipfile.ZipFile(bio, "r") as zf:
        # None indicates no CRC errors or corrupted files
        assert zf.testzip() is None
        names = zf.namelist()
        assert len(names) > 0


def test_export_project_zip_inclusions_and_exclusions(client, sample_project_session):
    """Verifies all required site files are included and transient/metadata artifacts are excluded."""
    session, _ = sample_project_session
    res = client.get(f"/api/projects/{session.session_id}/export")
    assert res.status_code == 200

    bio = io.BytesIO(res.data)
    with zipfile.ZipFile(bio, "r") as zf:
        namelist = set(zf.namelist())

        # Expected inclusions
        assert "package.json" in namelist
        assert "vite.config.ts" in namelist
        assert "tsconfig.json" in namelist
        assert "index.html" in namelist
        assert "src/App.tsx" in namelist
        assert "src/App.css" in namelist
        assert "src/main.tsx" in namelist
        assert "public/favicon.svg" in namelist

        # Prohibited exclusions
        for name in namelist:
            assert not name.startswith("node_modules/"), f"node_modules leaked: {name}"
            assert not name.startswith(".git/"), f".git leaked: {name}"
            assert not name.startswith(".snapshots/"), f".snapshots leaked: {name}"
            assert not name.startswith(".vite/"), f".vite leaked: {name}"
            assert not name.startswith("__pycache__/"), f"__pycache__ leaked: {name}"
            assert not name.endswith(".pyc"), f".pyc leaked: {name}"
            assert not name.endswith(".log"), f".log leaked: {name}"
            assert name not in ("history.jsonl", "session.json", "task_log.txt")
            assert "screenshot" not in name
            assert "visual_judge" not in name


def test_export_sessions_alias_endpoint(client, sample_project_session):
    """Verifies that GET /api/sessions/:sessionId/export produces an identical ZIP file."""
    session, _ = sample_project_session
    res_proj = client.get(f"/api/projects/{session.session_id}/export")
    res_sess = client.get(f"/api/sessions/{session.session_id}/export")

    assert res_proj.status_code == 200
    assert res_sess.status_code == 200

    with zipfile.ZipFile(io.BytesIO(res_proj.data), "r") as z1, zipfile.ZipFile(io.BytesIO(res_sess.data), "r") as z2:
        assert sorted(z1.namelist()) == sorted(z2.namelist())


def test_legacy_download_redirect_for_project_id(client, sample_project_session):
    """Verifies that calling legacy /api/download/:projectId redirects to /api/projects/:projectId/export."""
    session, _ = sample_project_session
    res = client.get(f"/api/download/{session.session_id}")

    # Should redirect rather than return 404
    assert res.status_code == 302
    assert f"/api/projects/{session.session_id}/export" in res.headers.get("Location", "")


def test_extracted_project_buildability_structure(client, sample_project_session):
    """Verifies the extracted archive contains complete structure to build the project."""
    session, _ = sample_project_session
    res = client.get(f"/api/projects/{session.session_id}/export")
    assert res.status_code == 200

    with tempfile.TemporaryDirectory() as extract_dir:
        extract_path = Path(extract_dir)
        with zipfile.ZipFile(io.BytesIO(res.data), "r") as zf:
            zf.extractall(extract_dir)

        # Verify entry point files exist
        assert (extract_path / "package.json").exists()
        assert (extract_path / "index.html").exists()
        assert (extract_path / "vite.config.ts").exists()
        assert (extract_path / "tsconfig.json").exists()
        assert (extract_path / "src" / "App.tsx").exists()
        assert (extract_path / "src" / "main.tsx").exists()

        # Parse package.json
        pkg = json.loads((extract_path / "package.json").read_text(encoding="utf-8"))
        assert "build" in pkg.get("scripts", {})
        assert "react" in pkg.get("dependencies", {})


def test_export_project_not_found(client):
    """Verifies 404 response for non-existent session/project."""
    res = client.get("/api/projects/1789999999_000000/export")
    assert res.status_code == 404
    assert "not found" in res.get_json().get("error", "").lower()
