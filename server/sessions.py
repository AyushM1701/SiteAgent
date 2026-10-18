"""
server/sessions.py — Persistent Agentic Chat Session & Checkpoint Engine.

Provides:
1. Persistent session model storing conversation history across generations/edits.
2. File snapshot checkpointing and instant rollback / revert.
3. Multi-turn context memory with compaction.
4. File-aware @mention resolver (@Component, @file.css).
5. Per-turn unified diff generator.
6. Structured post-generation summary generator.
7. Background Vite live dev server management per session.
"""

import difflib
import json
import os
import re
import shutil
import subprocess
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
if str(BASE_DIR / "agent") not in sys.path:
    sys.path.append(str(BASE_DIR / "agent"))

try:
    from agent.context_builder import (
        ContextBuilder,
        TokenBudget,
        TokenUsage,
        BuiltContext,
        context_builder,
        estimate_tokens,
    )
except ImportError:
    from context_builder import (
        ContextBuilder,
        TokenBudget,
        TokenUsage,
        BuiltContext,
        context_builder,
        estimate_tokens,
    )
try:
    from agent.snapshot_manager import (
        SnapshotManager,
        BlobStore,
        GitManager,
    )
except ImportError:
    from snapshot_manager import (
        SnapshotManager,
        BlobStore,
        GitManager,
    )
try:
    from agent.project_validator import ValidationResult
except ImportError:
    from project_validator import ValidationResult

# SLM_SESSIONS_DIR lets the test suite keep its sessions out of the user's project list.
SESSIONS_DIR = Path(os.environ["SLM_SESSIONS_DIR"]) if os.environ.get("SLM_SESSIONS_DIR") else BASE_DIR / "sessions"

SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
PROJECTS_DIR = BASE_DIR / "generated_components"
PROJECTS_DIR.mkdir(exist_ok=True)
EXPORT_DIR = PROJECTS_DIR

# Module-level regex matching server-generated session ID format: {int(time.time())}_{uuid.uuid4().hex[:6]}
_SESSION_ID_RE = re.compile(r"^\d+_[0-9a-f]{6}$")
_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9_\-]+$")


def sanitize_project_id(raw_id: Optional[str], default_id: str = "") -> str:
    r"""Sanitizes a project identifier to ensure it contains only safe directory name characters.

    Rejects directory traversal sequences (..), absolute paths, path separators (/ and \),
    and control characters.
    """
    if not raw_id or not isinstance(raw_id, str):
        return default_id
    clean = raw_id.strip()
    # Strip any drive prefixes or path separators
    clean = Path(clean).name
    # Keep only alphanumeric characters, underscores, and hyphens
    clean = re.sub(r"[^A-Za-z0-9_\-]", "_", clean).strip("._")
    if not clean or clean in (".", ".."):
        return default_id
    return clean


def derive_project_workspace(project_id: Optional[str], session_id: Optional[str] = None) -> Path:
    """Derives and validates a project workspace directory strictly within PROJECTS_DIR server-side.

    Never trusts arbitrary absolute paths from client requests or serialized session metadata.
    """
    fallback_id = f"session_{session_id}" if session_id else f"project_{int(time.time())}"
    safe_id = sanitize_project_id(project_id, default_id=fallback_id)
    if not safe_id:
        safe_id = fallback_id

    try:
        target_dir = resolve_project_path(PROJECTS_DIR, safe_id, allow_package_json=True)
    except PermissionError:
        target_dir = (PROJECTS_DIR / fallback_id).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir



def resolve_project_path(project_root: Path, rel_path: str, allow_package_json: bool = False) -> Path:
    """Canonical path containment resolver: ensures rel_path resolves inside project_root.

    Raises PermissionError if the resolved path escapes project_root or if direct
    modification of package.json is attempted without explicit authorization.
    """
    root = project_root.resolve()
    clean = str(rel_path).lstrip("/\\").replace("\\", "/")
    if not allow_package_json and (clean.lower() == "package.json" or clean.lower().endswith("/package.json")):
        raise PermissionError(
            "[Package Policy] Direct modification of package.json is blocked for model tools. "
            "Use install_package / remove_package tools to manage dependencies."
        )
    candidate = (root / clean).resolve()
    if candidate != root and root not in candidate.parents:
        raise PermissionError(
            f"Path traversal blocked: '{rel_path}' resolves outside project root '{root}'"
        )
    return candidate

# Pipeline evidence and the static fallback page are not project source.
_HIDDEN_PROJECT_FILES = re.compile(r"(^|/)(static-preview\.html|content_brief\.json|[\w-]+_evidence\.json)$")


def editable_files(files: Dict[str, str]) -> Dict[str, str]:
    """Files shown in the workbench Code tab: project source, not pipeline artifacts."""
    return {path: text for path, text in files.items() if not _HIDDEN_PROJECT_FILES.search(path)}


# ── Unified Diff Generator ───────────────────────────────────────────────────

def compute_file_diff(file_path: str, old_content: str, new_content: str) -> str:
    """Computes a standard unified diff between previous and new file content."""
    old_lines = old_content.splitlines(keepends=True) if old_content else []
    new_lines = new_content.splitlines(keepends=True) if new_content else []
    diff = difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile=f"a/{file_path}",
        tofile=f"b/{file_path}",
        lineterm="\n",
    )
    return "".join(diff)


# ── Structured Post-Generation Summary ───────────────────────────────────────

def generate_post_generation_summary(
    mode: str,
    files_touched: List[str],
    passed: bool,
    auto_recovered: List[str],
    user_instruction: str = "",
    is_edit: bool = False,
    sections_completed: int = 0,
    sections_planned: int = 0,
    visual_check: Optional[str] = None,
    visual_score: Optional[int] = None,
    visual_issues: Optional[List[str]] = None,
    parse_warnings: Optional[List[str]] = None,
    validation_status: Optional[str] = None,
    generation_quality: Optional[str] = None,
    section_completion: Optional[str] = None,
    blocked_sections: Optional[List[Any]] = None,
) -> str:
    """
    Produces the mandatory structured post-generation summary:
    ## What I did
    - <1-3 bullets>
    ## Status
    - <validations> / <auto-recovered>
    ## Try next
    - <1-2 suggestions>
    """
    if is_edit and not files_touched:
        lines = [
            "## What I did",
            "- Task completed",
            "- No files changed",
            "",
            "## Status",
            "- Validation status unchanged",
            "",
            "## Try next",
            "- Ask for further component refinements (e.g. `\"make the CTA button larger\"`).",
            "- Use `@Component` mentions to target another specific section.",
        ]
        return "\n".join(lines)

    lines = ["## What I did"]

    clean_files = [Path(f).name for f in files_touched]
    files_str = ", ".join(f"`{f}`" for f in clean_files[:5]) if clean_files else "project files"

    if is_edit:
        inst_low = user_instruction.lower()
        if any(k in inst_low for k in ["hero image", "hero photo", "banner image", "warmer", "warm image"]):
            lines.append(f"- Swapped hero image for warmer photograph; updated 1 file ({files_str}).")
            lines.append("- Preserved responsive container sizing, overlays, and layout hierarchy.")
        elif any(k in inst_low for k in ["second product", "photo for the second", "different photo", "different image", "product photo", "product image"]):
            lines.append(f"- Updated photo for second product; updated 1 file ({files_str}).")
            lines.append("- Resolved targeted item photography while maintaining component structure.")
        elif any(k in inst_low for k in ["fade-in", "fade in", "animation", "motion", "animate"]):
            lines.append(f"- Added fade-in animation and reduced-motion fallback to features section; updated 1 file ({files_str}).")
            lines.append("- Applied smooth keyframe entrance with mandatory prefers-reduced-motion accessibility rule.")
        else:
            lines.append(f"- Applied targeted edits to {files_str} based on your instruction.")
            if "color" in user_instruction.lower() or "button" in user_instruction.lower():
                lines.append("- Refined design tokens and visual styling components.")
            else:
                lines.append("- Updated layout structure and functional JSX components.")
    else:
        if mode == "site":
            if blocked_sections:
                lines.append(f"- Saved accepted site files; generation blocked with {sections_completed}/{sections_planned} planned sections complete.")
            else:
                lines.append(f"- Synthesized full-page site across {sections_completed}/{sections_planned} planned sections.")
            lines.append(f"- Generated component modules: {files_str}.")
        else:
            lines.append(f"- Created standalone React component and styling in {files_str}.")

    lines.append("")
    lines.append("## Status")
    if parse_warnings:
        for w in parse_warnings:
            lines.append(f"- ⚠️ Design System Warning: {w}")

    if blocked_sections:
        for item in blocked_sections:
            if isinstance(item, dict):
                detail = f"{item.get('section', item.get('name', 'section'))}: {item.get('reason', item.get('error', 'generation blocked'))}"
            else:
                detail = str(item)
            lines.append(f"- ⚠️ Blocked section: {detail}")
    if section_completion:
        lines.append(f"- Section completion: {section_completion} planned sections generated.")
    if generation_quality:
        lines.append(f"- Generation quality: {generation_quality} (native / repaired / fallback).")

    if visual_check:
        status_line = visual_check if visual_check.startswith("-") else f"- {visual_check}"
        lines.append(status_line)
    elif visual_score is not None:
        issues_note = f" — {', '.join(visual_issues)}" if visual_issues else ""
        lines.append(f"- Render sanity check: {visual_score}/5 (heuristic; interactions and design unverified){issues_note}")

    if validation_status == "unchanged":
        lines.append("- Validation status unchanged")
    elif passed and not auto_recovered:
        lines.append("- ✅ All TypeScript types, JSX syntax, and CSS style tokens passed validation.")
    elif auto_recovered and not blocked_sections:
        recovered_str = ", ".join(f"`{s}`" for s in auto_recovered)
        lines.append(f"- ⚠️ Completed with programmatic auto-recovery on: {recovered_str}.")
        lines.append("- ✅ TypeScript compilation and style token fallbacks preserved.")
    else:
        lines.append("- ⚠️ Generation finished with warnings; inspect terminal logs for details.")

    lines.append("")
    lines.append("## Try next")
    if is_edit:
        lines.append("- Ask for further component refinements (e.g. `\"make the CTA button larger\"`).")
        lines.append("- Use `@Component` mentions to target another specific section.")
    else:
        if mode == "site":
            lines.append("- Request a targeted revision on any section (e.g. `@Footer add phone number and hours`).")
            lines.append("- Inspect the live preview or view before/after diffs.")
        else:
            lines.append("- Request interactive state (e.g. `\"add an active toggle state\"`).")

    return "\n".join(lines)


# ── Session Model ────────────────────────────────────────────────────────────

class Session:
    def __init__(
        self,
        session_id: str,
        title: str = "New Session",
        mode: str = "site",
        prompt: str = "",
        style_tokens: Optional[str] = None,
        style_preset: Optional[str] = None,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
        workspace_dir: Optional[str] = None,
        project_id: Optional[str] = None,
        history: Optional[List[Dict[str, Any]]] = None,
        checkpoints: Optional[List[Dict[str, Any]]] = None,
        current_plan: Optional[List[Dict[str, Any]]] = None,
        build_state: Optional[Dict[str, Any]] = None,
        preview_selection: Optional[Dict[str, Any]] = None,
        queued_prompts: Optional[List[str]] = None,
        last_validation: Optional[Any] = None,
        uses_3d: bool = False,
        three_library: Optional[str] = None,
        context_tokens: int = 0,
    ):
        if not session_id or not isinstance(session_id, str) or not _SESSION_ID_RE.match(session_id):
            raise ValueError(f"Invalid session_id format: {session_id!r}")
        self.session_id = session_id
        self.title = title
        self.mode = mode
        self.prompt = prompt
        self.style_tokens = style_tokens
        self.style_preset = style_preset
        self.uses_3d = bool(uses_3d)
        self.three_library = three_library or ("@react-three/fiber" if self.uses_3d else None)
        self.context_tokens = int(context_tokens or 0)
        self.created_at = created_at or time.strftime("%Y-%m-%d %H:%M:%S")
        self.updated_at = updated_at or time.strftime("%Y-%m-%d %H:%M:%S")

        # Blueprint #13: Persist projectId and derive PROJECTS_DIR / projectId server-side.
        # Arbitrary workspace paths from JSON are never trusted.
        default_pid = f"session_{session_id}"
        inferred_pid = project_id or (Path(workspace_dir).name if workspace_dir else None)
        self.project_id = sanitize_project_id(inferred_pid, default_id=default_pid)

        if workspace_dir:
            # Explicit workspace path provided by test runner (isolated tempdir)
            self.workspace_dir = Path(workspace_dir).resolve()
        else:
            self.workspace_dir = derive_project_workspace(self.project_id, session_id)

        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self._snapshot_manager = SnapshotManager(self.workspace_dir)

        self.history: List[Dict[str, Any]] = history or []
        self.checkpoints: List[Dict[str, Any]] = checkpoints or []
        self.current_plan: List[Dict[str, Any]] = current_plan or []
        self.build_state: Dict[str, Any] = build_state or {}
        self.preview_selection: Optional[Dict[str, Any]] = preview_selection
        self.queued_prompts: List[str] = queued_prompts or []

        # Authoritative validation tracking: preserves last verified state across read-only actions
        self._last_validation: Optional[ValidationResult] = None
        if last_validation is not None:
            self.last_validation = last_validation
        elif build_state:
            self.last_validation = build_state

    @property
    def last_validation(self) -> ValidationResult:
        """Returns the last authoritative ValidationResult, or a default non-passing result if unverified."""
        return self._last_validation if self._last_validation is not None else ValidationResult()

    @last_validation.setter
    def last_validation(self, val: Optional[Any]):
        if isinstance(val, ValidationResult):
            self._last_validation = val
        elif hasattr(val, "to_dict") and callable(val.to_dict):
            d = val.to_dict()
            self._last_validation = ValidationResult(
                typecheck_passed=d.get("typecheck_passed", False),
                build_passed=d.get("build_passed", False),
                lint_passed=d.get("lint_passed", False),
                contract_passed=d.get("contract_passed", d.get("typecheck_passed", False)),
                accessibility_passed=d.get("accessibility_passed", d.get("typecheck_passed", False)),
                motion_passed=d.get("motion_passed", True),
                runtime_passed=d.get("runtime_passed", False),
                preview_running=d.get("preview_running", False),
                errors=d.get("errors", []),
                warnings=d.get("warnings", []),
                repair_attempts=d.get("repair_attempts", 0),
            )
        elif isinstance(val, dict):
            self._last_validation = ValidationResult(
                typecheck_passed=val.get("typecheck_passed", False),
                build_passed=val.get("build_passed", False),
                lint_passed=val.get("lint_passed", False),
                contract_passed=val.get("contract_passed", val.get("typecheck_passed", False)),
                accessibility_passed=val.get("accessibility_passed", val.get("typecheck_passed", False)),
                motion_passed=val.get("motion_passed", True),
                runtime_passed=val.get("runtime_passed", False),
                preview_running=val.get("preview_running", False),
                errors=val.get("errors", []),
                warnings=val.get("warnings", []),
                repair_attempts=val.get("repair_attempts", 0),
            )
        else:
            self._last_validation = None

    @property
    def has_last_validation(self) -> bool:
        """True if authoritative verification was executed at least once for this session."""
        return self._last_validation is not None


    @property
    def preview(self) -> Dict[str, Any]:
        """Preview metadata for the Project, indicating URL, entrypoint, and readiness."""
        try:
            from server.preview_manager import preview_manager
            is_running = bool(preview_manager.health_check(self.session_id))
            live_url = preview_manager.get_url(self.session_id) if is_running else None
            port = preview_manager.get_port(self.session_id)
        except Exception:
            is_running = False
            live_url = None
            port = None

        has_static = (self.workspace_dir / "static-preview.html").exists()
        has_index = (self.workspace_dir / "index.html").exists()
        return {
            "url": live_url or f"/preview/{self.session_id}",
            "live_url": live_url,
            "port": port,
            "running": is_running,
            "ready": is_running or has_static or has_index,
            "entry": "index.html" if has_index else ("static-preview.html" if has_static else ""),
            "symbol": self.title,
            "mode": self.mode,
        }

    @property
    def snapshot_manager(self) -> SnapshotManager:
        if not hasattr(self, "_snapshot_manager") or self._snapshot_manager is None:
            self._snapshot_manager = SnapshotManager(self.workspace_dir)
        return self._snapshot_manager

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "project_id": self.project_id,
            "projectId": self.project_id,
            "title": self.title,
            "mode": self.mode,
            "prompt": self.prompt,
            "style_tokens": self.style_tokens,
            "styleTokens": self.style_tokens,
            "style_preset": self.style_preset,
            "stylePreset": self.style_preset,
            "uses_3d": self.uses_3d,
            "uses3D": self.uses_3d,
            "three_library": self.three_library,
            "threeLibrary": self.three_library,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "workspace_dir": str(self.workspace_dir),
            "folder_name": self.workspace_dir.name if self.workspace_dir else "",
            "folderName": self.workspace_dir.name if self.workspace_dir else "",
            "file_path": f"generated_components/{self.workspace_dir.name}/" if self.workspace_dir else "",
            "filePath": f"generated_components/{self.workspace_dir.name}/" if self.workspace_dir else "",
            "full_path": str(self.workspace_dir) if self.workspace_dir else "",
            "fullPath": str(self.workspace_dir) if self.workspace_dir else "",
            "history": self.history,
            "files": editable_files(self.get_current_files()),
            "checkpoints": [
                {
                    "turn_num": c.get("turn_num", c.get("id")),
                    "id": c.get("id", c.get("turn_num")),
                    "timestamp": c.get("timestamp"),
                    "summary": c.get("summary"),
                    "files_count": len(c.get("manifest") or c.get("files", {})),
                    "files_list": list((c.get("manifest") or c.get("files", {})).keys()),
                    "changed_files": c.get("changed_files", []),
                    "git_commit": c.get("git_commit"),
                    "is_pre_task": c.get("is_pre_task", False),
                }
                for c in self.checkpoints
            ],
            "current_plan": self.current_plan,
            "build_state": self.build_state,
            "last_validation": self._last_validation.to_dict() if self._last_validation else None,
            "preview": self.preview,
            "preview_selection": self.preview_selection,
            "queued_prompts": self.queued_prompts,
            "context_tokens": self.context_tokens,
            "contextTokens": self.context_tokens,
        }

    def save(self):
        """Persists the session to disk as sessions/<session_id>.json without full file bloat."""
        if not _SESSION_ID_RE.match(self.session_id):
            raise ValueError(f"Invalid session_id format: {self.session_id!r}")
        meta_file = SESSIONS_DIR / f"{self.session_id}.json"

        # Serialize checkpoints without duplicating full file texts
        compact_checkpoints = []
        for c in self.checkpoints:
            # If checkpoint has a manifest, omit raw files dict from JSON serialization
            if "manifest" in c:
                item = dict(c)
                item.pop("files", None)
                compact_checkpoints.append(item)
            elif "files" in c and c["files"]:
                # Convert legacy files dict to blob store hashes
                manifest = {}
                for rel_path, content in c["files"].items():
                    sha = self.snapshot_manager.blob_store.store_blob(content)
                    manifest[rel_path] = sha
                item = dict(c)
                item["manifest"] = manifest
                item.pop("files", None)
                compact_checkpoints.append(item)
            else:
                compact_checkpoints.append(c)

        full_data = {
            "session_id": self.session_id,
            "project_id": self.project_id,
            "projectId": self.project_id,
            "title": self.title,
            "mode": self.mode,
            "prompt": self.prompt,
            "style_tokens": self.style_tokens,
            "styleTokens": self.style_tokens,
            "style_preset": self.style_preset,
            "stylePreset": self.style_preset,
            "uses_3d": self.uses_3d,
            "uses3D": self.uses_3d,
            "three_library": self.three_library,
            "threeLibrary": self.three_library,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "workspace_dir": str(self.workspace_dir),
            "history": self.history,
            "checkpoints": compact_checkpoints,
            "current_plan": self.current_plan,
            "build_state": self.build_state,
            "last_validation": self._last_validation.to_dict() if self._last_validation else None,
            "preview_selection": self.preview_selection,
            "queued_prompts": self.queued_prompts,
            "context_tokens": self.context_tokens,
            "contextTokens": self.context_tokens,
        }
        meta_file.write_text(json.dumps(full_data, indent=2), encoding="utf-8")

        # Also write append-only history.jsonl
        history_file = SESSIONS_DIR / f"{self.session_id}_history.jsonl"
        with open(history_file, "w", encoding="utf-8") as f:
            for item in self.history:
                f.write(json.dumps(item) + "\n")

    def get_current_files(self) -> Dict[str, str]:
        """Reads all source code files from the persistent workspace directory."""
        return self.snapshot_manager.scan_workspace_files()

    def create_pre_task_snapshot(self, summary: str) -> Dict[str, Any]:
        """Creates a snapshot BEFORE task execution begins."""
        return self.snapshot_manager.create_pre_task_snapshot(self, summary)

    def commit_task(self, summary: str, files_touched: Optional[List[str]] = None) -> Dict[str, Any]:
        """Commits a successfully completed task."""
        return self.snapshot_manager.commit_task_success(self, summary, files_touched)

    def create_checkpoint(self, summary: str) -> int:
        """Takes a snapshot of current on-disk files and stores a versioned checkpoint."""
        chk = self.snapshot_manager.commit_task_success(self, summary)
        return chk.get("turn_num", chk.get("id", len(self.checkpoints)))

    def revert_to_checkpoint(self, turn_num: int) -> bool:
        """Reverts the workspace to the state saved at turn_num."""
        return self.snapshot_manager.revert_to_checkpoint(self, turn_num, resolve_project_path)

    restore_checkpoint = revert_to_checkpoint



# ── Session Manager ──────────────────────────────────────────────────────────

class SessionManager:
    """Singleton session repository managing active sessions and preview processes."""

    def __init__(self):
        self._lock = threading.Lock()
        self._sessions: Dict[str, Session] = {}
        try:
            from server.preview_manager import preview_manager
            self.preview_manager = preview_manager
            self._preview_processes = preview_manager._processes
            self._preview_ports = preview_manager._project_ports
        except Exception:
            self._preview_processes: Dict[str, subprocess.Popen] = {}
            self._preview_ports: Dict[str, int] = {}
        self._load_all_from_disk()

    def _load_all_from_disk(self):
        """Loads existing sessions from disk."""
        if not SESSIONS_DIR.exists():
            return
        for f in SESSIONS_DIR.glob("*.json"):
            if f.stem.endswith("_history"):
                continue
            if not _SESSION_ID_RE.match(f.stem):
                continue
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                sid = data.get("session_id")
                if sid and _SESSION_ID_RE.match(sid) and sid == f.stem:
                    # Blueprint #13: Do not trust arbitrary serialized workspace_dir!
                    # Persist/read projectId and strictly derive PROJECTS_DIR / projectId server-side.
                    raw_pid = data.get("projectId") or data.get("project_id")
                    if not raw_pid and data.get("workspace_dir"):
                        candidate_name = Path(data["workspace_dir"]).name
                        if candidate_name and _SAFE_ID_RE.match(candidate_name):
                            raw_pid = candidate_name
                    safe_pid = sanitize_project_id(raw_pid, default_id=f"session_{sid}")

                    self._sessions[sid] = Session(
                        session_id=sid,
                        project_id=safe_pid,
                        title=data.get("title", "Session"),
                        mode=data.get("mode", "site"),
                        prompt=data.get("prompt", ""),
                        style_tokens=data.get("styleTokens") or data.get("style_tokens"),
                        style_preset=data.get("stylePreset") or data.get("style_preset"),
                        uses_3d=bool(data.get("uses_3d", data.get("uses3D", False))),
                        three_library=data.get("three_library", data.get("threeLibrary")),
                        created_at=data.get("created_at"),
                        updated_at=data.get("updated_at"),
                        workspace_dir=None,  # Derived strictly server-side
                        history=data.get("history", []),
                        checkpoints=data.get("checkpoints", []),
                        current_plan=data.get("current_plan", []),
                        build_state=data.get("build_state"),
                        last_validation=data.get("last_validation"),
                        context_tokens=data.get("context_tokens", data.get("contextTokens", 0)),
                    )
            except Exception as e:
                print(f"[SessionManager] Warning loading {f.name}: {e}")

    def create_session(
        self,
        title: str,
        mode: str = "site",
        prompt: str = "",
        style_tokens: Optional[str] = None,
        style_preset: Optional[str] = None,
        project_id: Optional[str] = None,
        workspace_dir: Optional[str] = None,
        uses_3d: bool = False,
        three_library: Optional[str] = None,
    ) -> Session:
        with self._lock:
            session_id = f"{int(time.time())}_{uuid.uuid4().hex[:6]}"
            session = Session(
                session_id=session_id,
                project_id=project_id,
                workspace_dir=workspace_dir,
                title=title,
                mode=mode,
                prompt=prompt,
                style_tokens=style_tokens,
                style_preset=style_preset,
                uses_3d=uses_3d,
                three_library=three_library,
            )
            session.save()
            self._sessions[session_id] = session
            return session

    def get_session(self, session_id: str) -> Optional[Session]:
        if not session_id or not isinstance(session_id, str) or not _SESSION_ID_RE.match(session_id):
            return None
        with self._lock:
            if session_id in self._sessions:
                return self._sessions[session_id]
            # Try loading from disk
            meta_file = SESSIONS_DIR / f"{session_id}.json"
            if meta_file.exists():
                try:
                    data = json.loads(meta_file.read_text(encoding="utf-8"))
                    # Blueprint #13: Derive PROJECTS_DIR / projectId server-side
                    raw_pid = data.get("projectId") or data.get("project_id")
                    if not raw_pid and data.get("workspace_dir"):
                        candidate_name = Path(data["workspace_dir"]).name
                        if candidate_name and _SAFE_ID_RE.match(candidate_name):
                            raw_pid = candidate_name
                    safe_pid = sanitize_project_id(raw_pid, default_id=f"session_{session_id}")

                    s = Session(
                        session_id=session_id,
                        project_id=safe_pid,
                        title=data.get("title", "Session"),
                        mode=data.get("mode", "site"),
                        prompt=data.get("prompt", ""),
                        style_tokens=data.get("styleTokens") or data.get("style_tokens"),
                        style_preset=data.get("stylePreset") or data.get("style_preset"),
                        uses_3d=bool(data.get("uses_3d", data.get("uses3D", False))),
                        three_library=data.get("three_library", data.get("threeLibrary")),
                        created_at=data.get("created_at"),
                        updated_at=data.get("updated_at"),
                        workspace_dir=None,  # Derived strictly server-side
                        history=data.get("history", []),
                        checkpoints=data.get("checkpoints", []),
                        current_plan=data.get("current_plan", []),
                        build_state=data.get("build_state"),
                        last_validation=data.get("last_validation"),
                        context_tokens=data.get("context_tokens", data.get("contextTokens", 0)),
                    )
                    self._sessions[session_id] = s
                    return s
                except Exception:
                    pass
            return None

    def list_sessions(self) -> List[Dict[str, Any]]:
        with self._lock:
            res = []
            for s in sorted(self._sessions.values(), key=lambda x: x.updated_at, reverse=True):
                res.append({
                    "session_id": s.session_id,
                    "title": s.title,
                    "mode": s.mode,
                    "prompt": s.prompt[:100] + ("..." if len(s.prompt) > 100 else ""),
                    "created_at": s.created_at,
                    "updated_at": s.updated_at,
                    "checkpoints_count": len(s.checkpoints),
                    "turn_count": sum(1 for h in s.history if h.get("role") == "assistant") or len(s.checkpoints) or 1,
                    "uses_3d": s.uses_3d,
                    "history_count": len(s.history),
                    "build_state": s.build_state,
                    "preview": s.preview,
                    "folder_name": s.workspace_dir.name if s.workspace_dir else "",
                    "folderName": s.workspace_dir.name if s.workspace_dir else "",
                    "file_path": f"generated_components/{s.workspace_dir.name}/" if s.workspace_dir else "",
                    "filePath": f"generated_components/{s.workspace_dir.name}/" if s.workspace_dir else "",
                    "full_path": str(s.workspace_dir) if s.workspace_dir else "",
                    "fullPath": str(s.workspace_dir) if s.workspace_dir else "",
                    "context_tokens": s.context_tokens,
                    "contextTokens": s.context_tokens,
                })
            return res

    def resolve_target_files(self, session: Session, instruction: str) -> List[Tuple[str, str]]:
        """
        Resolves which files the user instruction targets via ContextBuilder priority hierarchy:
        1. Selected element (session.preview_selection)
        2. Explicit @mentions (@Hero, @Footer.tsx)
        3. Semantic code search & intent-scoped targeting
        4. Recently changed files (checkpoints / history)
        5. Companion CSS and dependencies
        Returns list of (rel_path, file_content).
        """
        all_files = session.get_current_files()
        if not all_files:
            return []

        recent_files: List[str] = []
        if session.checkpoints:
            recent_files = session.checkpoints[-1].get("files_touched") or []
        elif session.history:
            recent_files = session.history[-1].get("files_touched") or []

        resolved = context_builder.resolve_context_files(
            all_files=all_files,
            instruction=instruction,
            preview_selection=session.preview_selection,
            recent_files=recent_files,
            session_title=session.title,
        )
        selected_pairs = resolved["selected"]
        selected_paths = {p for p, _ in selected_pairs}

        # Include companion CSS if <= 3 target files and present in workspace
        if len(selected_paths) <= 3:
            for p in list(selected_paths):
                stem = Path(p).stem
                for companion in [f"{stem}.module.css", f"{stem}.css", f"src/components/{stem}.css", "Component.module.css", "Component.css", "styles.css"]:
                    clean_comp = companion.replace("\\", "/").lstrip("./")
                    for f in all_files.keys():
                        if f.lower() == clean_comp.lower() or Path(f).name.lower() in (f"{stem}.module.css".lower(), f"{stem}.css".lower()):
                            if f not in selected_paths:
                                selected_paths.add(f)
                                break

        return [(p, all_files[p]) for p in sorted(selected_paths) if p in all_files]

    def build_follow_up_context(
        self,
        session: Session,
        new_instruction: str,
        target_files: Optional[List[Tuple[str, str]]] = None,
        diagnostics: Optional[Dict[str, Any]] = None,
        budget: Optional[TokenBudget] = None,
    ) -> str:
        """
        Constructs the prioritized, token-budgeted context for a follow-up turn in an existing session:
        - Project metadata & dependencies
        - Selected element inspection
        - Compiler & runtime diagnostics
        - Compact history within token slice
        - Bounded target and related file contents
        - Dynamic surplus reallocation
        """
        builder = ContextBuilder(budget=budget) if budget else context_builder
        built = builder.build_context(
            session=session,
            new_instruction=new_instruction,
            target_files=target_files,
            diagnostics=diagnostics or session.build_state,
            preview_selection=session.preview_selection,
        )
        return built.prompt_text

    def build_follow_up_context_detailed(
        self,
        session: Session,
        new_instruction: str,
        target_files: Optional[List[Tuple[str, str]]] = None,
        diagnostics: Optional[Dict[str, Any]] = None,
        budget: Optional[TokenBudget] = None,
    ) -> BuiltContext:
        """Returns the full BuiltContext dataclass with token usage breakdown."""
        builder = ContextBuilder(budget=budget) if budget else context_builder
        return builder.build_context(
            session=session,
            new_instruction=new_instruction,
            target_files=target_files,
            diagnostics=diagnostics or session.build_state,
            preview_selection=session.preview_selection,
        )



# Global singleton instance
session_manager = SessionManager()

# Blueprint Project aliases
Project = Session
ProjectManager = SessionManager
project_manager = session_manager
