#!/usr/bin/env python3
"""
scripts/clean_qwen3_training_data.py - Remove Legacy <thought> Targets from Qwen3 Training Data

Adheres to Qwen3 zero-thought policy (Issue #17):
1. Parses every conversation in a JSONL training/validation dataset.
2. Removes legacy <thought>...</thought> (and <think>...</think>) blocks only when safe.
3. Validates exactly one action (<tool_call name=...> or <finish>) per assistant turn.
4. Rejects malformed records (unclosed tags, zero actions, multiple actions, corrupt XML).
5. Preserves tool actions (<file> code, arguments) and final answers completely intact.
6. Writes a detailed report of modified and rejected rows to JSON.
"""

import argparse
import copy
from datetime import datetime
import json
import os
from pathlib import Path
import re
import shutil
import sys
from typing import Any, Dict, List, Optional, Tuple, Union

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from agent.agent_protocol import (
    AGENT_SYSTEM_PROMPT,
    parse_agent_output,
    WriteComponentAction,
    WriteSiteAction,
)
from training.preflight import CHAT_MARKERS, validate_messages


def clean_assistant_turn(content: str) -> Tuple[bool, str, Optional[str], bool]:
    """
    Cleans a single assistant turn by removing thought blocks.

    Returns:
        (success, cleaned_content, error_message, had_thought)
    """
    if not isinstance(content, str) or not content.strip():
        return False, "", "Empty or non-string assistant content", False

    had_thought = False

    # 1. Check for unclosed or unbalanced <thought> tags
    thought_open = content.count("<thought>")
    thought_close = content.count("</thought>")
    if thought_open != thought_close:
        return (
            False,
            content,
            f"Unbalanced <thought> tags: {thought_open} opened vs {thought_close} closed",
            False,
        )

    # 2. Check for unclosed or unbalanced <think> tags
    think_open = content.count("<think>")
    think_close = content.count("</think>")
    if think_open != think_close:
        return (
            False,
            content,
            f"Unbalanced <think> tags: {think_open} opened vs {think_close} closed",
            False,
        )

    if thought_open > 0 or think_open > 0:
        had_thought = True

    # 3. Strip <thought>...</thought> and <think>...</think> blocks safely
    cleaned = re.sub(r"<thought>[\s\S]*?</thought>\s*", "", content, flags=re.DOTALL)
    cleaned = re.sub(r"<think>[\s\S]*?</think>\s*", "", cleaned, flags=re.DOTALL)
    cleaned = cleaned.strip()

    # 4. Verify no residual thinking markers remain
    for forbidden in ("<thought>", "</thought>", "<think>", "</think>"):
        if forbidden in cleaned:
            return (
                False,
                cleaned,
                f"Residual forbidden thinking tag {forbidden!r} after cleaning",
                had_thought,
            )

    # 5. Validate exactly one agent action in assistant turn
    action_matches = re.findall(r"<(?:tool_call\s+name=|finish>)", cleaned)
    if len(action_matches) == 0:
        return (
            False,
            cleaned,
            "No agent action found in assistant turn after removing thought blocks",
            had_thought,
        )
    if len(action_matches) > 1:
        return (
            False,
            cleaned,
            f"Multiple agent actions ({len(action_matches)}) found in assistant turn: expected exactly 1",
            had_thought,
        )

    # 6. Validate balanced XML envelope tags
    for tag in ("tool_call", "file", "tsx", "css", "finish"):
        opened = len(re.findall(r"<" + tag + r"(?:\s[^>]*|)>", cleaned))
        closed = cleaned.count(f"</{tag}>")
        if opened != closed:
            return (
                False,
                cleaned,
                f"Unbalanced <{tag}> tags: {opened} opened vs {closed} closed",
                had_thought,
            )

    # 7. Parse agent action and validate semantic integrity
    turn = parse_agent_output(cleaned)
    if turn.action is None:
        return False, cleaned, "Assistant target has no valid agent action", had_thought

    if isinstance(turn.action, WriteSiteAction):
        if not turn.action.files or any(not code.strip() for _, code in turn.action.files):
            return False, cleaned, "WriteSiteAction contains empty file target", had_thought
        paths = [path for path, _ in turn.action.files]
        if len(paths) != len(set(paths)):
            return False, cleaned, "WriteSiteAction contains duplicate file paths", had_thought
        if any(
            path.startswith(("/", "\\"))
            or ":" in path
            or ".." in path.replace("\\", "/").split("/")
            for path in paths
        ):
            return False, cleaned, "WriteSiteAction contains unsafe path traversal", had_thought

    if isinstance(turn.action, WriteComponentAction) and not turn.action.tsx.strip():
        return False, cleaned, "WriteComponentAction contains empty component target", had_thought

    return True, cleaned, None, had_thought


def clean_record(row: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]], bool, Optional[str], int]:
    """
    Cleans a single dataset record (conversation).

    Returns:
        (is_valid, cleaned_row_or_none, was_modified, rejection_reason, thoughts_removed)
    """
    if not isinstance(row, dict):
        return False, None, False, "Record is not a JSON object", 0

    messages = row.get("messages")
    if not isinstance(messages, list) or len(messages) < 2:
        return False, None, False, "Record must contain at least user and assistant messages", 0

    cleaned_row = copy.deepcopy(row)
    cleaned_messages = cleaned_row["messages"]
    was_modified = False
    thoughts_removed = 0

    # Validate message roles structure
    roles = [m.get("role") for m in cleaned_messages if isinstance(m, dict)]
    expected = ["system"] if roles and roles[0] == "system" else []
    remaining = len(cleaned_messages) - len(expected)
    expected += ["user", "assistant"] * (remaining // 2)
    if roles != expected or remaining % 2 != 0:
        return False, None, False, "Messages must alternate user/assistant after optional system", 0

    for i, msg in enumerate(cleaned_messages):
        if not isinstance(msg, dict):
            return False, None, False, f"Message {i} is not an object", 0

        role = msg.get("role")
        content = msg.get("content")

        if not isinstance(content, str) or not content.strip():
            return False, None, False, f"Message {i} ({role}) has empty content", 0

        if any(marker in content for marker in CHAT_MARKERS):
            return False, None, False, f"Message {i} ({role}) contains embedded ChatML marker", 0

        if role == "system":
            if "<thought>" in content or "</thought>" in content:
                if "You are an expert autonomous React, TypeScript, and CSS coding agent" in content:
                    msg["content"] = AGENT_SYSTEM_PROMPT
                    was_modified = True
                    thoughts_removed += 1
                else:
                    clean_content = re.sub(r"<thought>[\s\S]*?</thought>\s*", "", content, flags=re.DOTALL)
                    clean_content = re.sub(r"1\.\s*<thought>[^\n]*\n[^\n]*\n\n", "", clean_content)
                    if clean_content != content:
                        msg["content"] = clean_content
                        was_modified = True
                        thoughts_removed += 1

        elif role == "user":
            if "<thought>" in content or "<think>" in content:
                clean_content = re.sub(r"<thought>[\s\S]*?</thought>\s*", "", content, flags=re.DOTALL)
                clean_content = re.sub(r"<think>[\s\S]*?</think>\s*", "", clean_content, flags=re.DOTALL)
                if clean_content != content:
                    msg["content"] = clean_content
                    was_modified = True
                    thoughts_removed += 1

        elif role == "assistant":
            ok, clean_content, err, had_thought = clean_assistant_turn(content)
            if not ok:
                return False, None, False, f"Assistant message {i} failed cleaning: {err}", 0
            if had_thought or clean_content != content:
                was_modified = True
                thoughts_removed += 1
                msg["content"] = clean_content

    # Fail-closed validation using preflight check
    try:
        validate_messages(cleaned_row)
    except ValueError as e:
        return False, None, False, f"Preflight validation failed on cleaned row: {e}", 0

    return True, cleaned_row, was_modified, None, thoughts_removed


def clean_dataset_file(
    input_path: Union[str, Path],
    output_path: Optional[Union[str, Path]] = None,
    report_path: Optional[Union[str, Path]] = None,
    inplace: bool = False,
    backup: bool = True,
) -> Dict[str, Any]:
    """
    Cleans a dataset JSONL file, removes thought blocks, writes cleaned output,
    and produces a structured report of modified and rejected rows.
    """
    in_file = Path(input_path).resolve()
    if not in_file.exists():
        raise FileNotFoundError(f"Input dataset does not exist: {in_file}")

    if inplace:
        target_out = in_file
        if backup:
            bak_path = in_file.with_suffix(in_file.suffix + ".bak_legacy_thought")
            if not bak_path.exists():
                shutil.copy2(in_file, bak_path)
    elif output_path:
        target_out = Path(output_path).resolve()
    else:
        target_out = in_file.with_name(in_file.stem + ".clean" + in_file.suffix)

    target_out.parent.mkdir(parents=True, exist_ok=True)

    total_records = 0
    clean_records: List[Dict[str, Any]] = []
    modified_records: List[Dict[str, Any]] = []
    rejected_records: List[Dict[str, Any]] = []
    total_thoughts_removed = 0

    with open(in_file, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line_str = line.strip()
            if not line_str:
                continue
            total_records += 1

            try:
                row = json.loads(line_str)
            except json.JSONDecodeError as err:
                rejected_records.append({
                    "line_number": line_num,
                    "task_id": None,
                    "reason": f"Invalid JSON syntax: {err}",
                })
                continue

            task_id = row.get("task_id")
            family_id = row.get("family_id")

            ok, cleaned_row, modified, reason, thoughts_count = clean_record(row)
            if not ok:
                rejected_records.append({
                    "line_number": line_num,
                    "task_id": task_id,
                    "family_id": family_id,
                    "reason": reason,
                })
            else:
                clean_records.append(cleaned_row)
                total_thoughts_removed += thoughts_count
                if modified:
                    modified_records.append({
                        "line_number": line_num,
                        "task_id": task_id,
                        "family_id": family_id,
                        "thoughts_removed": thoughts_count,
                    })

    # Write cleaned rows atomically via temporary file
    temp_out = target_out.with_suffix(".tmp." + str(os.getpid()))
    with open(temp_out, "w", encoding="utf-8") as out_f:
        for rec in clean_records:
            out_f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    shutil.move(str(temp_out), str(target_out))

    # Verify zero thoughts in written file
    zero_thought_verified = True
    with open(target_out, "r", encoding="utf-8") as check_f:
        for idx, line in enumerate(check_f, 1):
            if "<thought>" in line or "</thought>" in line or "<think>" in line or "</think>" in line:
                zero_thought_verified = False
                break

    report: Dict[str, Any] = {
        "timestamp": datetime.now().isoformat(),
        "input_file": str(in_file),
        "output_file": str(target_out),
        "total_records": total_records,
        "clean_records_count": len(clean_records),
        "modified_records_count": len(modified_records),
        "unmodified_records_count": len(clean_records) - len(modified_records),
        "rejected_records_count": len(rejected_records),
        "thought_blocks_removed": total_thoughts_removed,
        "zero_thought_verified": zero_thought_verified,
        "status": "success" if not rejected_records else "completed_with_rejections",
        "modified_sample": modified_records[:20],
        "rejected_records": rejected_records,
    }

    # Save report
    if report_path:
        rep_p = Path(report_path).resolve()
    else:
        rep_p = BASE_DIR / "runs" / f"clean_qwen3_{target_out.stem}_report.json"

    rep_p.parent.mkdir(parents=True, exist_ok=True)
    with open(rep_p, "w", encoding="utf-8") as rep_f:
        json.dump(report, rep_f, indent=2)

    return report


def main():
    parser = argparse.ArgumentParser(
        description="Clean legacy <thought> blocks from Qwen3 training data."
    )
    parser.add_argument(
        "--input",
        "-i",
        default="data/quality_candidate/train.jsonl",
        help="Input JSONL file (default: data/quality_candidate/train.jsonl)",
    )
    parser.add_argument(
        "--output",
        "-o",
        default=None,
        help="Output JSONL file (default: in-place or input.clean.jsonl)",
    )
    parser.add_argument(
        "--inplace",
        action="store_true",
        help="Overwrite input file with cleaned version (creates .bak_legacy_thought)",
    )
    parser.add_argument(
        "--report",
        "-r",
        default=None,
        help="Report file path (default: runs/clean_qwen3_<name>_report.json)",
    )
    parser.add_argument(
        "--all-canonical",
        action="store_true",
        help="Clean all canonical Qwen3 quality datasets (quality_candidate train & val, quality_v3 train)",
    )

    args = parser.parse_args()

    if args.all_canonical:
        targets = [
            ("data/quality_candidate/train.jsonl", True),
            ("data/quality_candidate/validation.jsonl", True),
            ("data/quality_v3/train.jsonl", True),
        ]
        print("=== Cleaning All Canonical Qwen3 Quality Datasets ===")
        all_success = True
        for target, inplace in targets:
            full_path = BASE_DIR / target
            if not full_path.exists():
                print(f"Skipping {target}: does not exist")
                continue
            print(f"\nProcessing {target}...")
            res = clean_dataset_file(full_path, inplace=inplace)
            print(f"  Total: {res['total_records']}, Clean: {res['clean_records_count']}, "
                  f"Modified: {res['modified_records_count']}, Rejected: {res['rejected_records_count']}, "
                  f"Zero-Thought: {res['zero_thought_verified']}")
            if not res["zero_thought_verified"] or res["rejected_records_count"] > 0:
                all_success = False

        if all_success:
            print("\nAll canonical datasets cleaned successfully with 0 thought blocks!")
            sys.exit(0)
        else:
            print("\nSome datasets had rejections or failed verification.")
            sys.exit(1)

    input_path = BASE_DIR / args.input if not Path(args.input).is_absolute() else Path(args.input)
    output_path = (BASE_DIR / args.output if not Path(args.output).is_absolute() else Path(args.output)) if args.output else None

    print(f"Cleaning dataset: {input_path}")
    res = clean_dataset_file(
        input_path=input_path,
        output_path=output_path,
        report_path=args.report,
        inplace=args.inplace,
    )
    print(f"Results for {res['input_file']}:")
    print(f"  Total records:           {res['total_records']}")
    print(f"  Clean records written:   {res['clean_records_count']}")
    print(f"  Modified records:        {res['modified_records_count']}")
    print(f"  Unmodified records:      {res['unmodified_records_count']}")
    print(f"  Rejected records:        {res['rejected_records_count']}")
    print(f"  Thought blocks removed:  {res['thought_blocks_removed']}")
    print(f"  Zero-thought verified:   {res['zero_thought_verified']}")
    print(f"  Status:                  {res['status']}")

    if not res["zero_thought_verified"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
