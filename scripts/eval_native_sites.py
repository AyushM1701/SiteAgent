#!/usr/bin/env python3
"""End-to-end site evaluation through a running workbench (the user's real path).

Generates complete sites for unseen briefs from the held-out families (never in
training), using whichever model the server loaded (MODEL_PATH) and the requested
strategy, then records the project gates, how many sections the model wrote the
code for, repairs, the visual score and timing.

  # base model, kit strategy (the default today)
  python scripts/eval_native_sites.py --strategy kit --out runs/native_sections/sites_base_kit.json
  # adapter loaded by the server, native strategy
  python scripts/eval_native_sites.py --strategy native --out runs/native_sections/sites_adapter_native.json
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from data_pipeline.native_site_prompts import FAMILIES, HOLDOUT_FAMILIES, build_prompt  # noqa: E402


def eval_prompts(count: int, seed: int) -> list[dict]:
    """Fresh briefs from held-out families (a different seed from the data builder)."""
    rng = random.Random(seed)
    families = [f for f in FAMILIES if f.id in HOLDOUT_FAMILIES]
    rows = []
    while len(rows) < count:
        family = families[len(rows) % len(families)]
        rows.append(build_prompt(family, rng))
    return rows


def call(base: str, path: str, payload: dict | None = None) -> dict:
    data = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(base + path, data=data, method="POST" if data else "GET",
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def run_one(base: str, prompt: str, strategy: str, timeout: float) -> dict:
    started = time.time()
    task = call(base, "/api/generate", {"prompt": prompt, "mode": "site", "strategy": strategy, "max_turns": 10})
    task_id, session_id = task["task_id"], task["session_id"]
    status = {}
    while time.time() - started < timeout:
        time.sleep(10)
        try:
            status = call(base, f"/api/generation/{task_id}/status")
        except Exception:
            continue
        if status.get("status") in ("completed", "blocked", "failed", "cancelled"):
            break
    seconds = round(time.time() - started, 1)
    project = call(base, f"/api/projects/{session_id}")
    turn = next((h for h in reversed(project.get("history", [])) if h.get("role") == "assistant"), {})
    validation = turn.get("validation") or {}
    planned = (turn.get("generation_scorecards") or {}).get("sections_planned")
    native = turn.get("native_code_sections") or []
    return {
        "session_id": session_id, "status": status.get("status"), "seconds": seconds,
        "final_passed": turn.get("final_passed"), "completion_status": turn.get("completion_status"),
        "gates": {k: validation.get(k) for k in ("typecheck_status", "build_status", "contract_status",
                                                   "accessibility_status", "motion_status", "runtime_status",
                                                   "interaction_status")},
        "repair_attempts": validation.get("repair_attempts"), "visual_score": turn.get("visual_score"),
        "strategy": turn.get("strategy"), "native_code_sections": native,
        "native_code_fallbacks": turn.get("native_code_fallbacks") or {},
        "sections": [p.split("/")[-1][:-4] for p in turn.get("files_touched", []) if p.endswith(".tsx")],
        "errors": (validation.get("errors") or [])[:5],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base-url", default="http://localhost:5000")
    parser.add_argument("--strategy", choices=["kit", "native"], required=True)
    parser.add_argument("--count", type=int, default=6)
    parser.add_argument("--seed", type=int, default=99)
    parser.add_argument("--timeout", type=float, default=3600)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    server = call(args.base_url, "/api/status")
    results = []
    for i, row in enumerate(eval_prompts(args.count, args.seed), 1):
        print(f"[{i}/{args.count}] {row['family_id']}: {row['prompt'][:90]}…", flush=True)
        result = run_one(args.base_url, row["prompt"], args.strategy, args.timeout)
        result.update(family_id=row["family_id"], prompt=row["prompt"])
        results.append(result)
        print(f"    passed={result['final_passed']} native={len(result['native_code_sections'])}/"
              f"{len(result['sections'])} repairs={result['repair_attempts']} {result['seconds']}s", flush=True)
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps({"model": server.get("model_path"), "strategy": args.strategy,
                                              "results": results}, indent=2) + "\n", encoding="utf-8")
    n = len(results)
    summary = {
        "model": server.get("model_path"), "strategy": args.strategy, "sites": n,
        "passed": sum(bool(r["final_passed"]) for r in results),
        "native_sections": sum(len(r["native_code_sections"]) for r in results),
        "total_sections": sum(len(r["sections"]) for r in results),
        "mean_seconds": round(sum(r["seconds"] for r in results) / max(1, n), 1),
        "mean_visual_score": round(sum(r["visual_score"] or 0 for r in results) / max(1, n), 2),
    }
    Path(args.out).write_text(json.dumps({**summary, "results": results}, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
