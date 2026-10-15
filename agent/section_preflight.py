"""Parser preflight for generated TSX/JSX/TS/JS and CSS before workspace writes.

This is syntax validation, not a replacement for compilation or quality gates.
The checked strings must be exactly the strings subsequently committed.
"""

import json
import subprocess
from pathlib import Path
from typing import Iterable, List, Tuple


_ROOT = Path(__file__).resolve().parent.parent
_SCRIPT = _ROOT / "scripts" / "preflight_sections.cjs"


def preflight_section_files(files: Iterable[Tuple[str, str]]) -> List[str]:
    candidates = [(path, source) for path, source in files
                  if path.lower().endswith((".tsx", ".jsx", ".ts", ".js", ".css"))]
    if not candidates:
        return []
    try:
        result = subprocess.run(
            ["node", str(_SCRIPT)], input=json.dumps(candidates), text=True,
            capture_output=True, cwd=_ROOT, timeout=15, check=True,
        )
        errors = json.loads(result.stdout)
        if not isinstance(errors, list) or not all(isinstance(error, str) for error in errors):
            raise ValueError("invalid parser response")
        return errors
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        # Parser availability is mandatory: never silently accept unvalidated code.
        return [f"[Parser preflight unavailable] {exc}"]
