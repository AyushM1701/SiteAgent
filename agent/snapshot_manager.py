"""
agent/snapshot_manager.py - Scalable Checkpoint & Git Snapshot Engine

Implements the blueprint's snapshot architecture:
1. Content-Addressable Blob Store:
   - Stores file revisions once by SHA-256 hash in `workspace_dir/.snapshots/blobs/`.
   - Checkpoints store lightweight metadata and changed file hashes rather than
     duplicating the entire repository in session JSON.
2. Internal Git Repository:
   - Initializes an internal Git repository per workspace.
   - Uses `.gitignore` for dependencies and build artifacts.
   - Creates clean commits for pre-task snapshots and task completions.
   - Enables fast native diffs and rock-solid undo/rollback.
3. Pre-Task Snapshot Timing:
   - Captures workspace state BEFORE the model starts editing.
   - Provides safe rollback on repair failures or cancellation.
   - Commits successful edits on task completion.
"""

from __future__ import annotations

import difflib
import hashlib
import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


# Default .gitignore contents for generated workspaces
DEFAULT_GITIGNORE = """# Node & Bundler artifacts
node_modules/
.vite/
dist/
dist-ssr/
*.local
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# Snapshots & Media
.snapshots/
screenshot.webp
*.log
"""


# ── 1. Content-Addressable Blob Store ─────────────────────────────────────────

class BlobStore:
    """
    Stores immutable file blobs content-addressed by SHA-256.
    Avoids duplicate storage across multiple turns when files are unchanged.
    """

    def __init__(self, storage_dir: Path):
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _blob_path(self, sha256_hash: str) -> Path:
        # Use two-character prefix subdirectory to avoid directory bloat
        prefix = sha256_hash[:2]
        rest = sha256_hash[2:]
        return self.storage_dir / prefix / rest

    def store_blob(self, content: str) -> str:
        """Stores text content if not already present; returns its SHA-256 hash."""
        raw_bytes = content.encode("utf-8")
        sha = hashlib.sha256(raw_bytes).hexdigest()
        dest = self._blob_path(sha)
        if not dest.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(raw_bytes)
        return sha

    def get_blob(self, sha256_hash: str) -> Optional[str]:
        """Reads content by SHA-256 hash."""
        dest = self._blob_path(sha256_hash)
        if dest.exists():
            return dest.read_text(encoding="utf-8")
        # Legacy fallback if flat directory was used
        flat = self.storage_dir / sha256_hash
        if flat.exists():
            return flat.read_text(encoding="utf-8")
        return None

    def has_blob(self, sha256_hash: str) -> bool:
        return self._blob_path(sha256_hash).exists() or (self.storage_dir / sha256_hash).exists()


# ── 2. Git Manager ────────────────────────────────────────────────────────────

class GitManager:
    """
    Manages internal Git repository initialization, commits, and rollbacks
    for a project workspace.
    """

    @staticmethod
    def _run_git(workspace_dir: Path, args: List[str], timeout: int = 10) -> Tuple[int, str, str]:
        """Runs a git command inside workspace_dir."""
        cmd = ["git"] + args
        try:
            res = subprocess.run(
                cmd,
                cwd=str(workspace_dir),
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding="utf-8",
                errors="replace",
            )
            return res.returncode, res.stdout.strip(), res.stderr.strip()
        except Exception as e:
            return -1, "", str(e)

    @classmethod
    def init_repo(cls, workspace_dir: Path) -> bool:
        """Ensures an internal Git repository is initialized with a .gitignore."""
        if not workspace_dir.exists():
            workspace_dir.mkdir(parents=True, exist_ok=True)

        git_dir = workspace_dir / ".git"
        if not git_dir.exists():
            code, out, err = cls._run_git(workspace_dir, ["init"])
            if code != 0:
                return False
            # Set local committer identity
            cls._run_git(workspace_dir, ["config", "user.name", "SiteAgent"])
            cls._run_git(workspace_dir, ["config", "user.email", "agent@siteagent.local"])

        gitignore_path = workspace_dir / ".gitignore"
        if not gitignore_path.exists():
            gitignore_path.write_text(DEFAULT_GITIGNORE, encoding="utf-8")

        return True

    @classmethod
    def commit(cls, workspace_dir: Path, message: str) -> Optional[str]:
        """Stages all tracked/untracked workspace files and creates a commit."""
        cls.init_repo(workspace_dir)

        # Stage files
        cls._run_git(workspace_dir, ["add", "-A"])

        # Check status
        code, out, _ = cls._run_git(workspace_dir, ["status", "--porcelain"])
        if not out:
            # Nothing to commit, get current HEAD
            code, head, _ = cls._run_git(workspace_dir, ["rev-parse", "HEAD"])
            return head if code == 0 else None

        code, out, err = cls._run_git(workspace_dir, ["commit", "-m", message])
        if code == 0:
            c_code, head, _ = cls._run_git(workspace_dir, ["rev-parse", "HEAD"])
            return head if c_code == 0 else None
        return None

    @classmethod
    def restore(cls, workspace_dir: Path, commit_hash: str) -> bool:
        """Restores workspace to the exact commit state."""
        if not (workspace_dir / ".git").exists():
            return False

        # Discard working tree changes and reset to commit_hash
        code, _, _ = cls._run_git(workspace_dir, ["reset", "--hard", commit_hash])
        if code != 0:
            return False
        # Clean any untracked files
        cls._run_git(workspace_dir, ["clean", "-fd"])
        return True

    @classmethod
    def get_diff(cls, workspace_dir: Path, from_commit: str, to_commit: str = "HEAD") -> str:
        """Returns the unified diff between two commits."""
        code, out, _ = cls._run_git(workspace_dir, ["diff", from_commit, to_commit])
        return out if code == 0 else ""


# ── 3. Snapshot Manager ───────────────────────────────────────────────────────

class SnapshotManager:
    """
    Orchestrates pre-task snapshots, task completion commits, and checkpoint
    restorations using content-addressable blobs and internal Git commits.
    """

    def __init__(self, workspace_dir: Path):
        self.workspace_dir = Path(workspace_dir)
        self.snapshots_dir = self.workspace_dir / ".snapshots"
        self.blob_store = BlobStore(self.snapshots_dir / "blobs")
        # Ensure Git is initialized if available
        GitManager.init_repo(self.workspace_dir)

    def scan_workspace_files(self) -> Dict[str, str]:
        """Scans current workspace source files, ignoring dependencies and build dirs."""
        files: Dict[str, str] = {}
        if not self.workspace_dir.exists():
            return files

        for p in self.workspace_dir.rglob("*"):
            if p.is_file() and not any(part in p.parts for part in ["node_modules", ".git", "dist", ".vite", ".snapshots"]):
                rel_path = p.relative_to(self.workspace_dir).as_posix()
                try:
                    files[rel_path] = p.read_text(encoding="utf-8")
                except Exception:
                    pass
        return files

    def create_pre_task_snapshot(
        self,
        session: Any,
        summary: str,
    ) -> Dict[str, Any]:
        """
        Takes a snapshot BEFORE any agent modifications take place.
        Returns the created pre-task snapshot metadata dict.
        """
        current_files = self.scan_workspace_files()
        manifest: Dict[str, str] = {}

        for rel_path, content in current_files.items():
            sha = self.blob_store.store_blob(content)
            manifest[rel_path] = sha

        # Commit to Git
        git_commit = GitManager.commit(self.workspace_dir, f"snapshot: pre-task: {summary}")

        turn_num = len(session.checkpoints) + 1
        snapshot = {
            "turn_num": turn_num,
            "id": turn_num,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "summary": summary,
            "manifest": manifest,
            "files": current_files,
            "changed_files": [],
            "changed_blobs": {},
            "diffs": {},
            "is_pre_task": True,
            "git_commit": git_commit,
        }

        session.checkpoints.append(snapshot)
        session.updated_at = time.strftime("%Y-%m-%d %H:%M:%S")
        session.save()
        return snapshot

    def commit_task_success(
        self,
        session: Any,
        summary: str,
        files_touched: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Commits a completed task with changed blobs and diffs.
        """
        current_files = self.scan_workspace_files()
        manifest: Dict[str, str] = {}
        changed_blobs: Dict[str, str] = {}
        diffs: Dict[str, str] = {}

        # Look up previous manifest to detect changed blobs
        prev_checkpoint = session.checkpoints[-1] if session.checkpoints else None
        prev_manifest = prev_checkpoint.get("manifest", {}) if prev_checkpoint else {}

        for rel_path, content in current_files.items():
            sha = self.blob_store.store_blob(content)
            manifest[rel_path] = sha

            old_sha = prev_manifest.get(rel_path)
            if old_sha != sha:
                changed_blobs[rel_path] = sha
                # Compute diff
                old_content = self.blob_store.get_blob(old_sha) if old_sha else ""
                diff = "".join(difflib.unified_diff(
                    old_content.splitlines(keepends=True) if old_content else [],
                    content.splitlines(keepends=True),
                    fromfile=f"a/{rel_path}",
                    tofile=f"b/{rel_path}",
                    lineterm="\n",
                ))
                diffs[rel_path] = diff

        # If files_touched was not supplied, infer from changed_blobs
        actual_touched = files_touched or list(changed_blobs.keys())

        # Commit to Git
        git_commit = GitManager.commit(self.workspace_dir, f"task: {summary}")

        turn_num = len(session.checkpoints) + 1
        checkpoint = {
            "turn_num": turn_num,
            "id": turn_num,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "summary": summary,
            "manifest": manifest,
            "files": current_files,
            "changed_files": actual_touched,
            "changed_blobs": changed_blobs,
            "diffs": diffs,
            "is_pre_task": False,
            "git_commit": git_commit,
        }

        session.checkpoints.append(checkpoint)
        session.updated_at = time.strftime("%Y-%m-%d %H:%M:%S")
        session.save()
        return checkpoint

    def get_checkpoint_files(self, checkpoint: Dict[str, Any]) -> Dict[str, str]:
        """
        Hydrates the complete file contents for a checkpoint:
        1. If checkpoint has legacy inline 'files', returns them directly.
        2. Otherwise reconstructs files from 'manifest' using BlobStore.
        """
        if "files" in checkpoint and checkpoint["files"]:
            return checkpoint["files"]

        manifest = checkpoint.get("manifest") or {}
        files: Dict[str, str] = {}
        for path, sha in manifest.items():
            content = self.blob_store.get_blob(sha)
            if content is not None:
                files[path] = content
        return files

    def revert_to_checkpoint(
        self,
        session: Any,
        target_num_or_id: int,
        resolve_path_func: Any,
    ) -> bool:
        """
        Reverts the workspace to the state saved at target_num_or_id:
        1. If git_commit is available, resets git tree.
        2. Otherwise, cleanly restores files from manifest + BlobStore.
        3. Enforces canonical path containment through resolve_path_func.
        """
        target = next(
            (c for c in session.checkpoints if c.get("turn_num") == target_num_or_id or c.get("id") == target_num_or_id),
            None
        )
        if not target:
            return False

        # Try Git restore first if git_commit is present
        git_commit = target.get("git_commit")
        git_success = False
        if git_commit and (self.workspace_dir / ".git").exists():
            git_success = GitManager.restore(self.workspace_dir, git_commit)

        if not git_success:
            # Fallback to BlobStore manifest restoration
            files = self.get_checkpoint_files(target)

            # Clear existing workspace files except node_modules and .git
            for p in self.workspace_dir.iterdir():
                if p.name not in ["node_modules", ".git", ".snapshots"]:
                    if p.is_dir():
                        shutil.rmtree(p)
                    else:
                        p.unlink()

            # Write snapshot files with security checks
            for rel_path, content in files.items():
                try:
                    dest = resolve_path_func(self.workspace_dir, rel_path, allow_package_json=True)
                except PermissionError as _err:
                    print(f"[SnapshotManager] Security: blocked restore write: {_err}")
                    continue
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(content, encoding="utf-8")

        # Record rollback event in session history
        session.history.append({
            "turn_id": len(session.history) + 1,
            "role": "system",
            "content": f"Reverted workspace to checkpoint #{target_num_or_id}: {target.get('summary', '')}",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "summary": f"Reverted to checkpoint #{target_num_or_id}",
            "files_touched": list((target.get("manifest") or target.get("files", {})).keys()),
            "diffs": target.get("diffs", {}),
        })
        session.updated_at = time.strftime("%Y-%m-%d %H:%M:%S")
        session.save()
        return True
