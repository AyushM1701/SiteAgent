"""
tests/test_scalable_checkpoints.py - Unit & Integration Tests for Scalable Checkpoints

Validates:
1. Content-Addressable Blob Store deduplication
2. Pre-task snapshot timing (before edits begin)
3. Rollback on task failure restoring pre-task snapshot
4. Task commit on success storing changed blobs, diffs, and Git commits
5. Compact session JSON persistence (no full repo duplication)
6. Legacy checkpoint backward compatibility (inline "files" dict)
7. Path traversal defense during restore
8. Internal Git repository initialization, .gitignore, and commits
"""

import json
import tempfile
from pathlib import Path

from agent.snapshot_manager import (
    BlobStore,
    GitManager,
    SnapshotManager,
)
from server.sessions import Session, SessionManager, resolve_project_path, SESSIONS_DIR


# ── 1. Blob Store Deduplication ───────────────────────────────────────────────

def test_blob_store_deduplication():
    with tempfile.TemporaryDirectory() as tmp_dir:
        blob_store = BlobStore(Path(tmp_dir) / "blobs")
        content_a = "export const Navbar = () => <nav>Menu</nav>;"
        content_b = "export const Footer = () => <footer>Bottom</footer>;"

        # Store content_a twice
        sha1 = blob_store.store_blob(content_a)
        sha2 = blob_store.store_blob(content_a)
        assert sha1 == sha2

        # Store content_b
        sha3 = blob_store.store_blob(content_b)
        assert sha3 != sha1

        # Retrieve content
        assert blob_store.get_blob(sha1) == content_a
        assert blob_store.get_blob(sha3) == content_b

        # Verify only 2 unique blob files exist on disk
        blob_files = list((Path(tmp_dir) / "blobs").rglob("*"))
        raw_blobs = [p for p in blob_files if p.is_file()]
        assert len(raw_blobs) == 2


# ── 2. Pre-Task Snapshot Timing ───────────────────────────────────────────────

def test_pre_task_snapshot_timing():
    with tempfile.TemporaryDirectory() as tmp_dir:
        session = Session(session_id="1789000000_101010", workspace_dir=tmp_dir)
        (Path(tmp_dir) / "App.tsx").write_text("export default function App() { return <div>Original</div>; }", encoding="utf-8")
        (Path(tmp_dir) / "App.css").write_text(".root { color: blue; }", encoding="utf-8")

        # Take pre-task snapshot BEFORE any edits begin
        pre_snap = session.create_pre_task_snapshot("Pre-edit: make color red")
        assert pre_snap["is_pre_task"] is True
        assert pre_snap["turn_num"] == 1
        assert "App.tsx" in pre_snap["manifest"]
        assert "App.css" in pre_snap["manifest"]

        # Now simulate model writing edits to App.tsx
        (Path(tmp_dir) / "App.tsx").write_text("export default function App() { return <div>Modified</div>; }", encoding="utf-8")

        # The snapshot manifest still points to original content blob
        orig_sha = pre_snap["manifest"]["App.tsx"]
        assert session.snapshot_manager.blob_store.get_blob(orig_sha) == "export default function App() { return <div>Original</div>; }"


# ── 3. Failed Task Rollback to Pre-Task Snapshot ──────────────────────────────

def test_failed_task_rollback_to_pre_task_snapshot():
    with tempfile.TemporaryDirectory() as tmp_dir:
        session = Session(session_id="1789000000_202020", workspace_dir=tmp_dir)
        app_file = Path(tmp_dir) / "App.tsx"
        app_file.write_text("export default function App() { return <div>Working</div>; }", encoding="utf-8")

        pre_snap = session.create_pre_task_snapshot("Pre-edit: broken change attempt")
        pre_id = pre_snap["id"]

        # Corrupt workspace
        app_file.write_text("SYNTAX ERROR BROKEN CODE", encoding="utf-8")
        assert "SYNTAX ERROR" in app_file.read_text(encoding="utf-8")

        # Roll back to pre-task snapshot
        ok = session.revert_to_checkpoint(pre_id)
        assert ok is True
        assert app_file.read_text(encoding="utf-8") == "export default function App() { return <div>Working</div>; }"


# ── 4. Task Commit on Success Records Changed Blobs & Diffs ───────────────────

def test_success_task_commit_records_changed_blobs_and_diffs():
    with tempfile.TemporaryDirectory() as tmp_dir:
        session = Session(session_id="1789000000_303030", workspace_dir=tmp_dir)
        (Path(tmp_dir) / "App.tsx").write_text("export default function App() { return <div>Old</div>; }", encoding="utf-8")
        (Path(tmp_dir) / "Header.tsx").write_text("export const Header = () => <header>Unchanged</header>;", encoding="utf-8")

        # Pre-task snapshot
        session.create_pre_task_snapshot("Pre-edit: update App")

        # Modify App.tsx
        (Path(tmp_dir) / "App.tsx").write_text("export default function App() { return <div>New</div>; }", encoding="utf-8")

        # Commit task on success
        commit_res = session.commit_task("Edit: updated App layout", files_touched=["App.tsx"])
        assert commit_res["is_pre_task"] is False
        assert commit_res["changed_files"] == ["App.tsx"]
        assert "App.tsx" in commit_res["changed_blobs"]
        assert "Header.tsx" not in commit_res["changed_blobs"]
        assert "App.tsx" in commit_res["diffs"]
        assert "-export default function App() { return <div>Old</div>; }" in commit_res["diffs"]["App.tsx"]
        assert "+export default function App() { return <div>New</div>; }" in commit_res["diffs"]["App.tsx"]


# ── 5. Compact Session JSON Persistence (No Full Repo Duplication) ────────────

def test_compact_session_json_persistence():
    with tempfile.TemporaryDirectory() as tmp_dir:
        session = Session(session_id="1789000000_404040", workspace_dir=tmp_dir)
        # Create 10 files
        for i in range(10):
            (Path(tmp_dir) / f"Component{i}.tsx").write_text(f"export const C{i} = () => <div>{i}</div>;", encoding="utf-8")

        # Run 5 turns
        for turn in range(5):
            session.create_pre_task_snapshot(f"Pre-edit turn {turn}")
            (Path(tmp_dir) / "Component0.tsx").write_text(f"export const C0 = () => <div>Turn {turn}</div>;", encoding="utf-8")
            session.commit_task(f"Commit turn {turn}", files_touched=["Component0.tsx"])

        session.save()
        session_file = SESSIONS_DIR / f"{session.session_id}.json"
        history_file = SESSIONS_DIR / f"{session.session_id}_history.jsonl"
        try:
            assert session_file.exists()

            data = json.loads(session_file.read_text(encoding="utf-8"))
            # Verify checkpoints array does NOT contain raw "files" dicts
            for chk in data["checkpoints"]:
                assert "files" not in chk
                assert "manifest" in chk

            # Verify JSON file size remains very compact (< 30 KB for 10 checkpoints)
            assert session_file.stat().st_size < 30000
        finally:
            if session_file.exists():
                session_file.unlink()
            if history_file.exists():
                history_file.unlink()



# ── 6. Legacy Checkpoint Backward Compatibility ───────────────────────────────

def test_legacy_checkpoint_backward_compatibility():
    with tempfile.TemporaryDirectory() as tmp_dir:
        session = Session(session_id="1789000000_505050", workspace_dir=tmp_dir)
        # Manually attach a legacy checkpoint with inline "files" dict
        legacy_chk = {
            "turn_num": 1,
            "id": 1,
            "timestamp": "2026-09-17 10:00:00",
            "summary": "Legacy checkpoint",
            "files": {
                "LegacyButton.tsx": "export const LegacyButton = () => <button>Old</button>;",
            },
        }
        session.checkpoints.append(legacy_chk)

        # Reverting should successfully unpack inline files
        ok = session.revert_to_checkpoint(1)
        assert ok is True
        restored = Path(tmp_dir) / "LegacyButton.tsx"
        assert restored.exists()
        assert restored.read_text(encoding="utf-8") == "export const LegacyButton = () => <button>Old</button>;"


# ── 7. Path Traversal Defense During Restore ──────────────────────────────────

def test_traversal_payload_blocked_during_restore():
    with tempfile.TemporaryDirectory() as tmp_dir:
        session = Session(session_id="1789000000_606060", workspace_dir=tmp_dir)
        malicious_chk = {
            "turn_num": 1,
            "id": 1,
            "timestamp": "2026-09-17 12:00:00",
            "summary": "Malicious checkpoint",
            "files": {
                "../../escaped.txt": "MALICIOUS PAYLOAD",
                "valid.txt": "SAFE CONTENT",
            },
        }
        session.checkpoints.append(malicious_chk)

        outside_file = Path(tmp_dir).parent / "escaped.txt"
        assert not outside_file.exists()

        ok = session.revert_to_checkpoint(1)
        assert ok is True
        assert not outside_file.exists()

        valid_file = Path(tmp_dir) / "valid.txt"
        assert valid_file.exists()
        assert valid_file.read_text(encoding="utf-8") == "SAFE CONTENT"


# ── 8. Internal Git Repository Initialization & Commits ───────────────────────

def test_internal_git_repo_initialization_and_commits():
    with tempfile.TemporaryDirectory() as tmp_dir:
        session = Session(session_id="1789000000_707070", workspace_dir=tmp_dir)
        (Path(tmp_dir) / "Scene.tsx").write_text("export const Scene = () => <canvas />;", encoding="utf-8")

        # 1. Verify .git exists
        git_dir = Path(tmp_dir) / ".git"
        assert git_dir.exists()

        # 2. Verify .gitignore exists and ignores dependencies
        gitignore = Path(tmp_dir) / ".gitignore"
        assert gitignore.exists()
        gi_text = gitignore.read_text(encoding="utf-8")
        assert "node_modules/" in gi_text
        assert ".snapshots/" in gi_text

        # 3. Create pre-task snapshot and verify Git commit hash
        snap = session.create_pre_task_snapshot("Pre-edit: add lighting to Scene")
        assert snap.get("git_commit") is not None
        assert len(snap["git_commit"]) >= 7

        # 4. Modify and commit task
        (Path(tmp_dir) / "Scene.tsx").write_text("export const Scene = () => <canvas id='stars' />;", encoding="utf-8")
        c_res = session.commit_task("Task: added stars lighting", files_touched=["Scene.tsx"])
        assert c_res.get("git_commit") is not None
        assert c_res["git_commit"] != snap["git_commit"]

        # 5. Rollback via git
        ok = session.revert_to_checkpoint(snap["id"])
        assert ok is True
        assert Path(tmp_dir, "Scene.tsx").read_text(encoding="utf-8") == "export const Scene = () => <canvas />;"
