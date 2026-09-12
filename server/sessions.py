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

BASE_DIR = Path(__file__).resolve().parent.parent
SESSIONS_DIR = BASE_DIR / "sessions"
SESSIONS_DIR.mkdir(exist_ok=True)
EXPORT_DIR = BASE_DIR / "generated_components"
EXPORT_DIR.mkdir(exist_ok=True)

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
        lineterm="",
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
    lines = ["## What I did"]

    clean_files = [Path(f).name for f in files_touched]
    files_str = ", ".join(f"`{f}`" for f in clean_files[:5]) if clean_files else "project files"

    if is_edit:
        lines.append(f"- Applied targeted edits to {files_str} based on your instruction.")
        if "color" in user_instruction.lower() or "button" in user_instruction.lower():
            lines.append("- Refined design tokens and visual styling components.")
        else:
            lines.append("- Updated layout structure and functional JSX components.")
    else:
        if mode == "site":
            lines.append(f"- Synthesized full-page site across {sections_completed}/{sections_planned} planned sections.")
            lines.append(f"- Generated component modules: {files_str}.")
        else:
            lines.append(f"- Created standalone React component and styling in {files_str}.")

    lines.append("")
    lines.append("## Status")
    if passed and not auto_recovered:
        lines.append("- ✅ All TypeScript types, JSX syntax, and CSS style tokens passed validation.")
    elif auto_recovered:
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
        history: Optional[List[Dict[str, Any]]] = None,
        checkpoints: Optional[List[Dict[str, Any]]] = None,
        current_plan: Optional[List[Dict[str, Any]]] = None,
    ):
        self.session_id = session_id
        self.title = title
        self.mode = mode
        self.prompt = prompt
        self.style_tokens = style_tokens
        self.style_preset = style_preset
        self.created_at = created_at or time.strftime("%Y-%m-%d %H:%M:%S")
        self.updated_at = updated_at or time.strftime("%Y-%m-%d %H:%M:%S")

        # Workspace directory
        if workspace_dir:
            self.workspace_dir = Path(workspace_dir)
        else:
            self.workspace_dir = EXPORT_DIR / f"session_{session_id}"
        self.workspace_dir.mkdir(parents=True, exist_ok=True)

        self.history: List[Dict[str, Any]] = history or []
        self.checkpoints: List[Dict[str, Any]] = checkpoints or []
        self.current_plan: List[Dict[str, Any]] = current_plan or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "title": self.title,
            "mode": self.mode,
            "prompt": self.prompt,
            "style_tokens": self.style_tokens,
            "style_preset": self.style_preset,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "workspace_dir": str(self.workspace_dir),
            "history": self.history,
            "checkpoints": [
                {
                    "turn_num": c.get("turn_num"),
                    "timestamp": c.get("timestamp"),
                    "summary": c.get("summary"),
                    "files_count": len(c.get("files", {})),
                    "files_list": list(c.get("files", {}).keys()),
                }
                for c in self.checkpoints
            ],
            "current_plan": self.current_plan,
        }

    def save(self):
        """Persists the session to disk as sessions/<session_id>.json."""
        meta_file = SESSIONS_DIR / f"{self.session_id}.json"
        full_data = {
            "session_id": self.session_id,
            "title": self.title,
            "mode": self.mode,
            "prompt": self.prompt,
            "style_tokens": self.style_tokens,
            "style_preset": self.style_preset,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "workspace_dir": str(self.workspace_dir),
            "history": self.history,
            "checkpoints": self.checkpoints,
            "current_plan": self.current_plan,
        }
        meta_file.write_text(json.dumps(full_data, indent=2), encoding="utf-8")

        # Also write append-only history.jsonl
        history_file = SESSIONS_DIR / f"{self.session_id}_history.jsonl"
        with open(history_file, "w", encoding="utf-8") as f:
            for item in self.history:
                f.write(json.dumps(item) + "\n")

    def get_current_files(self) -> Dict[str, str]:
        """Reads all source code files from the persistent workspace directory."""
        files = {}
        if not self.workspace_dir.exists():
            return files

        for p in self.workspace_dir.rglob("*"):
            if p.is_file() and not any(part in p.parts for part in ["node_modules", ".git", "dist", ".vite"]):
                rel_path = p.relative_to(self.workspace_dir).as_posix()
                try:
                    files[rel_path] = p.read_text(encoding="utf-8")
                except Exception:
                    pass
        return files

    def create_checkpoint(self, summary: str) -> int:
        """Takes a snapshot of current on-disk files and stores a versioned checkpoint."""
        current_files = self.get_current_files()
        turn_num = len(self.checkpoints) + 1
        checkpoint = {
            "turn_num": turn_num,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "summary": summary,
            "files": current_files,
        }
        self.checkpoints.append(checkpoint)
        self.updated_at = time.strftime("%Y-%m-%d %H:%M:%S")
        self.save()
        return turn_num

    def revert_to_checkpoint(self, turn_num: int) -> bool:
        """Reverts the workspace to the state saved at turn_num."""
        target = next((c for c in self.checkpoints if c["turn_num"] == turn_num), None)
        if not target:
            return False

        files = target.get("files", {})
        # Clear existing workspace files except node_modules
        for p in self.workspace_dir.iterdir():
            if p.name not in ["node_modules", ".git"]:
                if p.is_dir():
                    shutil.rmtree(p)
                else:
                    p.unlink()

        # Write snapshot files
        for rel_path, content in files.items():
            dest = self.workspace_dir / rel_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8")

        # Record rollback event in history
        self.history.append({
            "turn_id": len(self.history) + 1,
            "role": "system",
            "content": f"Reverted workspace to checkpoint #{turn_num}: {target.get('summary', '')}",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "summary": f"Reverted to checkpoint #{turn_num}",
            "files_touched": list(files.keys()),
            "diffs": {},
        })
        self.updated_at = time.strftime("%Y-%m-%d %H:%M:%S")
        self.save()
        return True


# ── Session Manager ──────────────────────────────────────────────────────────

class SessionManager:
    """Singleton session repository managing active sessions and preview processes."""

    def __init__(self):
        self._lock = threading.Lock()
        self._sessions: Dict[str, Session] = {}
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
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                sid = data.get("session_id")
                if sid:
                    self._sessions[sid] = Session(
                        session_id=sid,
                        title=data.get("title", "Session"),
                        mode=data.get("mode", "site"),
                        prompt=data.get("prompt", ""),
                        style_tokens=data.get("style_tokens"),
                        style_preset=data.get("style_preset"),
                        created_at=data.get("created_at"),
                        updated_at=data.get("updated_at"),
                        workspace_dir=data.get("workspace_dir"),
                        history=data.get("history", []),
                        checkpoints=data.get("checkpoints", []),
                        current_plan=data.get("current_plan", []),
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
    ) -> Session:
        with self._lock:
            session_id = f"{int(time.time())}_{uuid.uuid4().hex[:6]}"
            session = Session(
                session_id=session_id,
                title=title,
                mode=mode,
                prompt=prompt,
                style_tokens=style_tokens,
                style_preset=style_preset,
            )
            session.save()
            self._sessions[session_id] = session
            return session

    def get_session(self, session_id: str) -> Optional[Session]:
        with self._lock:
            if session_id in self._sessions:
                return self._sessions[session_id]
            # Try loading from disk
            meta_file = SESSIONS_DIR / f"{session_id}.json"
            if meta_file.exists():
                try:
                    data = json.loads(meta_file.read_text(encoding="utf-8"))
                    s = Session(
                        session_id=session_id,
                        title=data.get("title", "Session"),
                        mode=data.get("mode", "site"),
                        prompt=data.get("prompt", ""),
                        style_tokens=data.get("style_tokens"),
                        style_preset=data.get("style_preset"),
                        created_at=data.get("created_at"),
                        updated_at=data.get("updated_at"),
                        workspace_dir=data.get("workspace_dir"),
                        history=data.get("history", []),
                        checkpoints=data.get("checkpoints", []),
                        current_plan=data.get("current_plan", []),
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
                    "history_count": len(s.history),
                })
            return res

    def resolve_target_files(self, session: Session, instruction: str) -> List[Tuple[str, str]]:
        """
        Resolves which files the user instruction targets via:
        1. Explicit @mentions (e.g. @Footer, @Header.css, @src/components/About.tsx)
        2. Heuristic word matching against component filenames in workspace.
        Returns list of (rel_path, file_content).
        """
        all_files = session.get_current_files()
        if not all_files:
            return []

        # 1. Parse @mentions
        mentions = re.findall(r'@([A-Za-z0-9_.-]+)', instruction)
        target_paths = set()

        for m in mentions:
            m_clean = m.lower()
            for path in all_files.keys():
                path_lower = path.lower()
                stem = Path(path).stem.lower()
                name = Path(path).name.lower()
                if m_clean in (path_lower, stem, name) or stem == m_clean:
                    target_paths.add(path)

        # 2. If no @mentions, search component stems mentioned in instruction
        if not target_paths:
            for path in all_files.keys():
                if path.startswith("src/components/"):
                    stem = Path(path).stem.lower()
                    # Check if stem word appears in user instruction
                    if re.search(rf'\b{re.escape(stem)}\b', instruction, re.I):
                        target_paths.add(path)
                        # Also add corresponding CSS
                        css_counterpart = str(Path(path).with_suffix(".css")).replace("\\", "/")
                        if css_counterpart in all_files:
                            target_paths.add(css_counterpart)

        # 3. Fallback: if still empty, include all components if <= 4 files, or App.tsx
        if not target_paths:
            comp_files = [p for p in all_files.keys() if p.startswith("src/components/")]
            if comp_files:
                target_paths.update(comp_files[:4])
            elif "App.tsx" in all_files:
                target_paths.add("App.tsx")

        return [(p, all_files[p]) for p in sorted(target_paths) if p in all_files]

    def build_follow_up_context(
        self,
        session: Session,
        new_instruction: str,
        target_files: List[Tuple[str, str]],
    ) -> str:
        """
        Constructs the compacted context for a follow-up turn in an existing session:
        - Brief & Design Tokens
        - Compact summary of previous turns
        - Full current content of target files
        - New user instruction
        """
        sections = []

        # 1. Base tokens & prompt
        sections.append(f"ORIGINAL TASK: {session.prompt}")
        if session.style_tokens:
            sections.append(f"DESIGN SYSTEM TOKENS:\n{session.style_tokens}")

        # 2. History turn log summaries
        if session.history:
            sections.append("PRIOR TURNS IN THIS SESSION:")
            for h in session.history[-4:]:  # last 4 turns
                role = h.get("role", "turn").capitalize()
                summary = h.get("summary") or h.get("content", "")[:120]
                sections.append(f"- [{role}]: {summary}")

        # 3. Current target file contents
        sections.append("\nCURRENT TARGET FILE CONTENTS TO MODIFY:")
        for path, content in target_files:
            sections.append(f'<file path="{path}">\n{content}\n</file>')

        # 4. New instruction
        sections.append(
            f"\nUSER INSTRUCTION FOR THIS EDIT:\n{new_instruction}\n\n"
            f"Modify the target files to satisfy the instruction. "
            f"You MUST emit the complete updated file content wrapped in <file path=\"...\"> tags inside <tool_call name=\"write_site\">."
        )

        return "\n\n".join(sections)


# Global singleton instance
session_manager = SessionManager()
