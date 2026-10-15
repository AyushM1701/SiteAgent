"""Guarded surgical edit actions for conversational repair turns."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import List
from agent.section_preflight import preflight_section_files


@dataclass
class ReplaceHunk:
    before: str
    after: str
    expected_count: int = 1


@dataclass
class EditFileAction:
    path: str
    base_sha256: str
    hunks: List[ReplaceHunk] = field(default_factory=list)


def apply_edit(workspace: Path, action: EditFileAction) -> str:
    path = (workspace / action.path).resolve()
    root = workspace.resolve()
    if root not in path.parents or path == root:
        raise PermissionError(f"Edit path escapes workspace: {action.path}")
    original = path.read_text(encoding="utf-8")
    digest = hashlib.sha256(original.encode("utf-8")).hexdigest()
    if digest != action.base_sha256:
        raise ValueError("Edit rejected: file changed since model context was built")
    updated = original
    for hunk in action.hunks:
        count = updated.count(hunk.before)
        if count != hunk.expected_count:
            raise ValueError(f"Patch anchor mismatch: expected {hunk.expected_count}, found {count}")
        updated = updated.replace(hunk.before, hunk.after, hunk.expected_count)
    errors = preflight_section_files([(action.path, updated)])
    if errors:
        raise ValueError("Edit rejected by parser preflight: " + "; ".join(errors))
    path.write_text(updated, encoding="utf-8")
    return updated
