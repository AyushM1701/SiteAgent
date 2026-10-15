"""Real CSS grammar validation through the project's installed PostCSS parser."""
from functools import lru_cache
import json
from pathlib import Path
import shutil
import subprocess


@lru_cache(maxsize=128)
def _inspect_css(css):
    node = shutil.which("node")
    if not node:
        return (("CSS validation unavailable: Node.js is required",), ())
    try:
        result = subprocess.run(
            [node, str(Path(__file__).resolve().parents[1] / "scripts" / "validate_css.cjs")],
            input=css, text=True, encoding="utf-8", capture_output=True, timeout=10,
            shell=False,
        )
        if result.returncode:
            return (("CSS validation unavailable: PostCSS parser failed",), ())
        parsed = json.loads(result.stdout)
        return tuple(parsed["errors"]), tuple(parsed.get("sharedSelectors", []))
    except (OSError, subprocess.TimeoutExpired, ValueError, KeyError):
        return (("CSS validation unavailable: parser could not complete",), ())


def css_syntax_errors(css):
    return _inspect_css(css)[0]


def css_shared_selectors(css):
    return _inspect_css(css)[1]
