#!/usr/bin/env python3
"""Section-level evaluation of native section authoring on held-out families.

Samples code rows from data/native_sections/validation.jsonl (business families
that never appear in training), asks a model to write each section, and checks:
  parsed     two files with the right paths and export
  preflight  the repo's TSX/CSS parser preflight passes
  copy       every approved string from the content JSON is kept verbatim
  typecheck  `tsc --noEmit` passes for the component (React types from the repo)
  accepted   all of the above: what native mode would actually use
  fidelity   difflib similarity to the design kit's own rendering (0..1)

Usage:
  python scripts/eval_native_sections.py --model base-model --out runs/native_sections/eval_base.json
  python scripts/eval_native_sections.py --model models/qwen3-siteagent-native-sections-r16 --out runs/native_sections/eval_adapter.json
"""
from __future__ import annotations

import argparse
import difflib
import json
import random
import re
import shutil
import subprocess
import sys
import tempfile
import time
from collections import defaultdict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))


def sample_rows(path: Path, n: int, seed: int) -> list[dict]:
    rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    rows = [r for r in rows if r.get("task_type") == "section_code"]
    by_kind = defaultdict(list)
    for r in rows:
        by_kind[r["kind"]].append(r)
    rng = random.Random(seed)
    for group in by_kind.values():
        rng.shuffle(group)
    picked, kinds = [], sorted(by_kind)
    while len(picked) < n and any(by_kind.values()):
        for kind in kinds:
            if by_kind[kind] and len(picked) < n:
                picked.append(by_kind[kind].pop())
    return picked


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--model", required=True)
    parser.add_argument("--data", default=str(BASE_DIR / "data/native_sections/validation.jsonl"))
    parser.add_argument("--samples", type=int, default=36)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--max-seconds", type=float, default=240)
    parser.add_argument("--kinds", help="Comma-separated section kinds to evaluate (default: all)")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    from agent.agent import AgentModelRunner
    from agent.section_preflight import preflight_section_files
    from agent.site_kit.native import parse_native_files, missing_copy, structural_gaps, typecheck_sections as typecheck

    rows = sample_rows(Path(args.data), args.samples, args.seed)
    if args.kinds:
        rows = [r for r in rows if r["kind"] in set(args.kinds.split(","))]
    model_path = str((BASE_DIR / args.model) if not Path(args.model).is_absolute() else Path(args.model))
    runner = AgentModelRunner(model_path=model_path, max_seq_length=8192)
    results, generated = [], {}
    for i, row in enumerate(rows):
        prompt, target = row["messages"][:2], row["messages"][2]["content"]
        component = re.search(r"Files: src/components/(\w+)\.tsx", prompt[1]["content"]).group(1)
        content = json.loads(prompt[1]["content"].split("Content JSON:\n", 1)[1].rsplit("\nFiles:", 1)[0])
        started = time.perf_counter()
        reply = runner.generate_turn(example_idx=0, history=prompt, primary_symbol=component, max_new_tokens=6144,
                                     temperature=0.2, top_p=0.9, top_k=40, repetition_penalty=1.0,
                                     max_time_seconds=args.max_seconds)
        seconds = time.perf_counter() - started
        files, problems = parse_native_files(reply, component)
        record = {"id": f"s{i:03d}", "kind": row["kind"], "family": row["family_id"], "component": component,
                  "seconds": round(seconds, 1), "tokens": getattr(runner, "last_generation_tokens", None),
                  "parsed": bool(files), "problems": problems, "reply": reply}
        if files:
            pre = preflight_section_files(files)
            lost = missing_copy(files[0][1], content)
            # Read the kit reference directly: older targets may break rules added later.
            reference = re.search(rf'<file path="src/components/{component}\.tsx">\n(.*?)\n</file>', target, re.S).group(1)
            gaps = structural_gaps(files[0][1], reference)
            record.update(preflight=not pre, preflight_errors=pre[:3], copy_kept=not lost, lost_copy=lost[:3],
                          structure_ok=not gaps, structure_gaps=gaps[:4])
            generated[record["id"]] = files
            record["fidelity"] = round(difflib.SequenceMatcher(None, target, reply.strip(), autojunk=False).ratio(), 3)
        else:
            record.update(preflight=False, copy_kept=False, structure_ok=False, fidelity=0.0)
        results.append(record)
        print(f"[{i + 1}/{len(rows)}] {row['kind']:9} parsed={record['parsed']} preflight={record['preflight']} "
              f"copy={record['copy_kept']} fidelity={record['fidelity']} {record['seconds']}s", flush=True)

    tsc_errors = typecheck(generated) if generated else {}
    for record in results:
        record["typecheck"] = record["parsed"] and record["id"] not in tsc_errors
        record["typecheck_errors"] = tsc_errors.get(record["id"], [])[:3]
        record["accepted"] = bool(record["parsed"] and record["preflight"] and record["copy_kept"]
                                  and record["structure_ok"] and record["typecheck"])

    def rate(key, subset=results):
        return round(sum(bool(r[key]) for r in subset) / max(1, len(subset)), 3)
    by_kind = {k: {"n": len(v), "accepted": rate("accepted", v)}
               for k, v in sorted({r["kind"]: [x for x in results if x["kind"] == r["kind"]] for r in results}.items())}
    report = {
        "model": args.model, "samples": len(results), "seed": args.seed,
        "rates": {k: rate(k) for k in ("parsed", "preflight", "copy_kept", "structure_ok", "typecheck", "accepted")},
        "mean_fidelity": round(sum(r["fidelity"] for r in results) / max(1, len(results)), 3),
        "mean_seconds": round(sum(r["seconds"] for r in results) / max(1, len(results)), 1),
        "by_kind": by_kind, "results": results,
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("model", "samples", "rates", "mean_fidelity", "mean_seconds")}, indent=2))


if __name__ == "__main__":
    main()
