"""Record an early-stopped live site probe without inventing a completed benchmark."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", type=Path, required=True)
    parser.add_argument("--adapter", type=Path, required=True)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    screenshot = args.site / "screenshot.webp"
    adapter_file = args.adapter / "adapter_model.safetensors"
    if not screenshot.is_file() or not adapter_file.is_file():
        raise FileNotFoundError("The rendered screenshot and adapter are required")
    components = list((args.site / "src/components").glob("*.tsx"))
    fallbacks = [str(path.relative_to(args.site)) for path in components if 'data-fallback="true"' in path.read_text(encoding="utf-8")]
    if not fallbacks:
        raise ValueError("No fallback sections found; this early-failure summary does not apply")
    report = {
        "report_type": "live_probe_early_failure",
        "completed_benchmark": False,
        "task_id": args.task_id,
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "adapter_sha256": sha256(adapter_file),
        "site_dir": str(args.site.resolve()),
        "fallback_sections": fallbacks,
        "screenshot": str(screenshot.resolve()),
        "screenshot_sha256": sha256(screenshot),
        "native_gate": "failed",
        "reason": "Generated site includes fallback sections with unavailable content; the browser screenshot shows unusable output.",
        "outcome_scorecards": {
            "model_native": {"status": "evaluated_partial", "passed": False, "fallback_section_count": len(fallbacks)},
            "deterministic_repair": {"status": "not_fully_evaluated", "passed": None},
            "model_repair": {"status": "interrupted_after_native_failure", "passed": None},
            "final_rendered_site": {"status": "partial_screenshot_only", "passed": False},
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "fallback_sections": len(fallbacks), "native_gate": "failed"}))


if __name__ == "__main__":
    main()
