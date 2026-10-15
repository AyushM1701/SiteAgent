"""Prepare bounded, loss-target-preserving training examples and a family holdout.

This is data preparation, not visual verification. Existing scores are never treated
as proof of visual quality. Original data is retained unchanged.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import random
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from agent.agent_protocol import format_chatml


def digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def structural_tokens(row):
    code = "\n".join(m["content"] for m in row["messages"] if m["role"] == "assistant")
    code = re.sub(r'"[^"\n]*"|\x27[^\x27\n]*\x27|`[^`]*`', 'STR', code)
    tokens = re.findall(r"[A-Za-z_]+|[{}<>;=]", code)
    return {tuple(tokens[i:i + 5]) for i in range(max(0, len(tokens) - 4))}


def group_families(rows, threshold=.8):
    """Union exact prompts and similar code families before splitting windows."""
    parents = list(range(len(rows)))
    def find(i):
        while parents[i] != i:
            parents[i] = parents[parents[i]]
            i = parents[i]
        return i
    shingles = [structural_tokens(row) for row in rows]
    prompts = [next((m["content"].strip().lower() for m in r["messages"] if m["role"] == "user"), "") for r in rows]
    for i in range(len(rows)):
        for j in range(i):
            explicit_family = rows[i].get("family_id")
            same = (bool(explicit_family) and explicit_family == rows[j].get("family_id")) or prompts[i] == prompts[j] or rows[i].get("task_id") == rows[j].get("task_id") and bool(rows[i].get("task_id"))
            if not same and shingles[i] and shingles[j]:
                same = len(shingles[i] & shingles[j]) / len(shingles[i] | shingles[j]) >= threshold
            if same:
                parents[find(i)] = find(j)
    return [find(i) for i in range(len(rows))]


def make_windows(row, count_tokens, limit):
    """One assistant target per window. Never truncate the supervised completion.

    For later turns preserve initial instruction, latest observation, and the prior
    assistant implementation as user-side context. Drop distant history only.
    """
    messages = row["messages"]
    system = next((dict(m) for m in messages if m["role"] == "system"), None)
    initial = next((m["content"] for m in messages if m["role"] == "user"), "")
    windows, rejected = [], []
    previous_assistant = None
    latest_feedback = ""
    for turn, message in enumerate(messages):
        if message["role"] == "user":
            latest_feedback = message["content"]
        if message["role"] != "assistant":
            continue
        context = initial
        if previous_assistant is not None:
            context += "\n\nPrevious assistant implementation (context only):\n" + previous_assistant
            context += "\n\nLatest environment feedback:\n" + latest_feedback
        sample = ([system] if system else []) + [{"role": "user", "content": context}, dict(message)]
        length = count_tokens(format_chatml(sample, add_generation_prompt=False)) + 1
        if length <= limit:
            windows.append({"task_id": row.get("task_id", "unknown") + f"_turn{turn}",
                            "source_task_id": row.get("task_id", "unknown"),
                            "messages": sample, "token_count": length})
        else:
            rejected.append({"task_id": row.get("task_id"), "turn": turn, "tokens": length})
        previous_assistant = message["content"]
    return windows, rejected


def prepare(source, output, tokenizer_path, limit=8192, seed=42):
    from tokenizers import Tokenizer
    tokenizer = Tokenizer.from_file(str(tokenizer_path))
    count = lambda text: len(tokenizer.encode(text, add_special_tokens=False).ids)
    original = [json.loads(line) for line in source.read_text(encoding="utf-8").splitlines() if line.strip()]
    rows, seen = [], set()
    duplicates = 0
    for row in original:
        key = digest(json.dumps(row["messages"], sort_keys=True))
        if key in seen:
            duplicates += 1
            continue
        seen.add(key)
        rows.append(row)
    families = group_families(rows)
    groups = sorted(set(families))
    random.Random(seed).shuffle(groups)
    # Entire families stay together; report actual split rather than promise 10%.
    validation_groups = set(groups[:max(1, round(len(groups) * .1))]) if len(groups) > 1 else set()
    splits = {"train": [], "validation": []}
    rejected = []
    source_lengths = []
    for row, family in zip(rows, families):
        source_lengths.append(count(format_chatml(row["messages"], False)))
        windows, dropped = make_windows(row, count, limit)
        split = "validation" if family in validation_groups else "train"
        for window in windows:
            window["family_id"] = str(family)
        splits[split].extend(windows)
        rejected.extend(dropped)
    output.mkdir(parents=True, exist_ok=True)
    for split, windows in splits.items():
        (output / f"{split}.jsonl").write_text("".join(json.dumps(w, ensure_ascii=False) + "\n" for w in windows), encoding="utf-8")
    report = {"source": str(source), "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
              "tokenizer_sha256": hashlib.sha256(tokenizer_path.read_bytes()).hexdigest(),
              "seed": seed, "context_limit": limit, "source_trajectories": len(original),
              "exact_duplicates_removed": duplicates, "structural_families": len(groups),
              "source_trajectories_over_limit": sum(n > limit for n in source_lengths),
              "windows": {k: len(v) for k, v in splits.items()}, "rejected_oversize_targets": rejected,
              "visual_verification": "Not performed. These are candidates, not visually approved gold data.",
              "family_sizes": dict(Counter(map(str, families)))}
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "data/training_data.jsonl")
    parser.add_argument("--output", type=Path, default=ROOT / "data/quality_candidate")
    parser.add_argument("--tokenizer", type=Path, default=ROOT / "my-react-agent-lora/tokenizer.json")
    parser.add_argument("--max-seq-length", type=int, default=8192)
    args = parser.parse_args()
    report = prepare(args.source, args.output, args.tokenizer, args.max_seq_length)
    print(json.dumps({k: v for k, v in report.items() if k not in ("family_sizes", "rejected_oversize_targets")}, indent=2))
