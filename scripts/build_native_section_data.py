#!/usr/bin/env python3
"""Build training data that teaches the model to write site sections itself.

Two stages, both resumable:

  generate  The base model writes each section's copy (the kit content step) for
            every brief in the prompt bank. Raw replies are saved per site under
            <out>/raw/<id>.json, so an interrupted run continues where it stopped.

  assemble  Each saved site is planned by the design kit (its own theme plus one
            alternative theme) and every section becomes a training row:
              * code rows:    native prompt (design spec + content JSON) -> the
                              section's TSX and CSS, exactly as the kit renders it;
              * content rows: the kit content prompt -> the model's own usable JSON
                              (keeps the copy-writing skill intact under the adapter).
            Families in HOLDOUT_FAMILIES go only to the validation split.

Usage:
  python scripts/build_native_section_data.py generate --per-family 5
  python scripts/build_native_section_data.py assemble
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from data_pipeline.native_site_prompts import HOLDOUT_FAMILIES, prompt_bank, rare_kind_bank, section_slug  # noqa: E402

DEFAULT_OUT = BASE_DIR / "data" / "native_sections"


def generate(out: Path, per_family: int, limit: int | None, model_path: str, bank: str = "main") -> None:
    from agent.agent import AgentModelRunner
    from agent.site_brief import generate_content_brief
    from agent.site_kit import KitSite

    raw_dir = out / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    rows = rare_kind_bank(per_family) if bank == "rare" else prompt_bank(per_family)
    todo = [r for r in rows if not (raw_dir / f"{r['id']}.json").exists() and not (raw_dir / f"{r['id']}.skipped").exists()]
    if limit:
        todo = todo[:limit]
    print(f"{len(rows)} briefs, {len(rows) - len(todo)} already generated, {len(todo)} to go", flush=True)
    if not todo:
        return
    runner = AgentModelRunner(model_path=model_path, max_seq_length=4096)
    started_all = time.perf_counter()
    for n, row in enumerate(todo, 1):
        started = time.perf_counter()
        brief = generate_content_brief(row["prompt"])
        kit = KitSite(row["prompt"], brief, None)
        wanted = {section_slug(s) for s in row["requested_sections"]}
        if set(kit.sections[2:-1]) != wanted:
            # The planner misread this brief; a training row must match its request.
            print(f"[skip] {row['id']}: planned {kit.sections[2:-1]} for {sorted(wanted)}", flush=True)
            (raw_dir / f"{row['id']}.skipped").write_text(json.dumps({"planned": kit.sections, "wanted": sorted(wanted)}), encoding="utf-8")
            continue
        raw: dict[str, str] = {}
        usable = 0
        for slug in kit.sections:
            if not kit.needs_model(slug):
                continue
            messages = kit.messages(slug)
            text = ""
            for temperature in (0.7, 0.55):
                text = runner.generate_turn(example_idx=0, history=messages, primary_symbol=kit.brand,
                                            max_new_tokens=kit.max_tokens(slug), temperature=temperature,
                                            top_p=0.8, top_k=20, repetition_penalty=1.0)
                if kit.is_usable(slug, text):
                    usable += 1
                    break
            raw[slug] = text
            kit.accept(slug, text)  # later sections see earlier headlines, as in production
        record = {**row, "brief": brief, "raw": raw, "sections": kit.sections,
                  "seconds": round(time.perf_counter() - started, 1)}
        tmp = raw_dir / f"{row['id']}.json.tmp"
        tmp.write_text(json.dumps(record, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        tmp.replace(raw_dir / f"{row['id']}.json")
        elapsed = time.perf_counter() - started_all
        eta = elapsed / n * (len(todo) - n)
        print(f"[{n}/{len(todo)}] {row['id']}: {usable}/{len(raw)} usable in {record['seconds']}s "
              f"(eta {eta / 60:.0f} min)", flush=True)


def _alternative_theme(site_id: str, current: str, mode: str) -> str:
    from agent.site_kit.themes import THEMES
    # Keep the requested light/dark mode so the copy still fits the look.
    pool = sorted(t for t, theme in THEMES.items() if t != current and theme.mode == mode) or \
        sorted(t for t in THEMES if t != current)
    digest = int(hashlib.sha256(site_id.encode()).hexdigest(), 16)
    return pool[digest % len(pool)]


def _site_rows(record: dict, theme_id: str | None, include_content: bool) -> tuple[list[dict], str]:
    from agent.site_kit import KitSite
    from agent.site_kit.native import native_messages, native_target, parse_native_files

    kit = KitSite(record["prompt"], record["brief"], record.get("sections"), theme_id=theme_id)
    rows: list[dict] = []
    for slug in kit.sections:
        text = record["raw"].get(slug, "")
        if include_content and kit.needs_model(slug) and text and kit.is_usable(slug, text):
            rows.append({"messages": kit.messages(slug) + [{"role": "assistant", "content": text.strip()}],
                         "task_type": "section_content", "kind": kit.kinds[slug], "slug": slug})
        kit.accept(slug, text)
    for slug in kit.sections:
        files = kit.render(slug)
        target = native_target(files)
        parsed, problems = parse_native_files(target, kit.component(slug))
        if problems:
            raise ValueError(f"{record['id']}/{slug}: kit output fails the native parser: {problems}")
        rows.append({"messages": native_messages(kit, slug) + [{"role": "assistant", "content": target}],
                     "task_type": "section_code", "kind": kit.kinds[slug], "slug": slug})
    for row in rows:
        row.update({"family_id": record["family_id"], "source_task_id": record["id"], "theme": kit.theme.id})
    return rows, kit.theme.id


def assemble(out: Path, content_fraction: float, seed: int) -> None:
    raw_files = sorted((out / "raw").glob("*.json"))
    if not raw_files:
        raise SystemExit("No raw sites; run the generate stage first.")
    train, validation = [], []
    for path in raw_files:
        record = json.loads(path.read_text(encoding="utf-8"))
        rows, theme = _site_rows(record, None, include_content=True)
        from agent.site_kit.themes import THEMES
        alt = _alternative_theme(record["id"], theme, THEMES[theme].mode)
        alt_rows, _ = _site_rows(record, alt, include_content=False)
        site_rows = rows + alt_rows
        (validation if record["family_id"] in HOLDOUT_FAMILIES else train).extend(site_rows)

    rng = random.Random(seed)
    def thin(rows: list[dict]) -> list[dict]:
        code = [r for r in rows if r["task_type"] == "section_code"]
        content = [r for r in rows if r["task_type"] == "section_content"]
        keep = min(len(content), int(len(code) * content_fraction))
        mixed = code + rng.sample(content, keep)
        rng.shuffle(mixed)
        return mixed
    train, validation = thin(train), thin(validation)
    # Drop exact duplicate conversations (the trainer refuses them).
    def dedupe(rows):
        seen, kept = set(), []
        for r in rows:
            key = json.dumps(r["messages"], sort_keys=True)
            if key not in seen:
                seen.add(key)
                kept.append(r)
        return kept
    train, validation = dedupe(train), dedupe(validation)
    for i, r in enumerate(train):
        r["task_id"] = f"native_train_{i:05d}"
    for i, r in enumerate(validation):
        r["task_id"] = f"native_val_{i:05d}"
    assert not ({r["family_id"] for r in train} & {r["family_id"] for r in validation}), "family leak"

    out.mkdir(parents=True, exist_ok=True)
    for name, rows in (("train.jsonl", train), ("validation.jsonl", validation)):
        with (out / name).open("w", encoding="utf-8") as handle:
            for r in rows:
                handle.write(json.dumps(r, ensure_ascii=False) + "\n")
    summary = {
        "sites": len(raw_files),
        "train_rows": len(train), "validation_rows": len(validation),
        "train_by_type": {t: sum(r["task_type"] == t for r in train) for t in ("section_code", "section_content")},
        "train_by_kind": dict(sorted(__import__("collections").Counter(r["kind"] for r in train if r["task_type"] == "section_code").items())),
        "holdout_families": sorted(HOLDOUT_FAMILIES),
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="stage", required=True)
    g = sub.add_parser("generate")
    g.add_argument("--per-family", type=int, default=5)
    g.add_argument("--limit", type=int)
    g.add_argument("--bank", choices=["main", "rare"], default="main", help="rare: briefs that force rare section kinds")
    g.add_argument("--model", default=str(BASE_DIR / "base-model"))
    g.add_argument("--out", type=Path, default=DEFAULT_OUT)
    a = sub.add_parser("assemble")
    a.add_argument("--out", type=Path, default=DEFAULT_OUT)
    a.add_argument("--content-fraction", type=float, default=0.25)
    a.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    if args.stage == "generate":
        generate(args.out, args.per_family, args.limit, args.model, args.bank)
    else:
        assemble(args.out, args.content_fraction, args.seed)
