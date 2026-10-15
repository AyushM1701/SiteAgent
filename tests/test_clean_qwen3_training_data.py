"""
tests/test_clean_qwen3_training_data.py - Tests for Issue #17

Verifies:
1. Parse every conversation safely.
2. Remove legacy <thought>...</thought> (and <think>...</think>) blocks only when safe.
3. Validate exactly one action per assistant turn (<tool_call> or <finish>).
4. Reject malformed records (unclosed tags, zero actions, multiple actions, corrupt XML).
5. Preserve tool actions and final answers completely intact.
6. Write a report of modified/rejected rows to JSON.
7. Preflight checks reject <think>, </think>, <thought>, and </thought> inside supervised targets.
8. Qwen3 training set contains zero thought blocks.
"""

import json
from pathlib import Path
import re
from unittest.mock import Mock

import pytest
from tokenizers import Tokenizer

from agent.agent_protocol import parse_agent_output, WriteSiteAction, WriteComponentAction
from scripts.clean_qwen3_training_data import (
    clean_assistant_turn,
    clean_record,
    clean_dataset_file,
)
from training.preflight import validate_messages, encode_row

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def cpu_tokenizer():
    tok_path = ROOT / "my-react-agent-lora" / "tokenizer.json"
    if not tok_path.exists():
        tok_path = ROOT / "base-model" / "tokenizer.json"
    return Tokenizer.from_file(str(tok_path))


# ---------------------------------------------------------------------------
# 1. Turn-level Cleaning and Safety Checks
# ---------------------------------------------------------------------------

def test_clean_assistant_turn_finish():
    raw = "<thought>\nPlanning final response.\n</thought>\n<finish>Site generation complete!</finish>"
    ok, cleaned, err, had_thought = clean_assistant_turn(raw)
    assert ok is True
    assert err is None
    assert had_thought is True
    assert cleaned == "<finish>Site generation complete!</finish>"
    assert "<thought>" not in cleaned
    assert "</thought>" not in cleaned


def test_clean_assistant_turn_write_site():
    raw = (
        "<thought>\nBuilding the header and hero.\n</thought>\n"
        '<tool_call name="write_site">\n'
        '<file path="src/App.tsx">export default function App() { return <div>App</div>; }</file>\n'
        '<file path="src/App.css">.body { margin: 0; }</file>\n'
        "</tool_call>"
    )
    ok, cleaned, err, had_thought = clean_assistant_turn(raw)
    assert ok is True
    assert err is None
    assert had_thought is True
    assert cleaned.startswith('<tool_call name="write_site">')
    assert cleaned.endswith("</tool_call>")
    assert "<thought>" not in cleaned
    turn = parse_agent_output(cleaned)
    assert isinstance(turn.action, WriteSiteAction)
    assert len(turn.action.files) == 2
    assert turn.action.files[0][0] == "src/App.tsx"


def test_clean_assistant_turn_write_component():
    raw = (
        "<thought>Creating component</thought>\n"
        '<tool_call name="write_component">\n'
        '<tsx>export default function Button() { return <button>Click</button>; }</tsx>\n'
        '<css>.btn { color: red; }</css>\n'
        "</tool_call>"
    )
    ok, cleaned, err, had_thought = clean_assistant_turn(raw)
    assert ok is True
    assert had_thought is True
    turn = parse_agent_output(cleaned)
    assert isinstance(turn.action, WriteComponentAction)
    assert "export default function Button" in turn.action.tsx


def test_clean_assistant_turn_already_clean():
    raw = '<tool_call name="write_site"><file path="index.html"><h1>Hi</h1></file></tool_call>'
    ok, cleaned, err, had_thought = clean_assistant_turn(raw)
    assert ok is True
    assert had_thought is False
    assert cleaned == raw


# ---------------------------------------------------------------------------
# 2. Rejection of Malformed Records
# ---------------------------------------------------------------------------

def test_reject_unclosed_thought():
    raw = "<thought>Missing closing tag\n<finish>Done</finish>"
    ok, cleaned, err, had_thought = clean_assistant_turn(raw)
    assert ok is False
    assert "Unbalanced <thought> tags" in err


def test_reject_unclosed_think():
    raw = "<think>Native think missing closing tag\n<finish>Done</finish>"
    ok, cleaned, err, had_thought = clean_assistant_turn(raw)
    assert ok is False
    assert "Unbalanced <think> tags" in err


def test_reject_zero_actions_after_thought_removal():
    raw = "<thought>I am just contemplating without any action.</thought>"
    ok, cleaned, err, had_thought = clean_assistant_turn(raw)
    assert ok is False
    assert "No agent action found" in err


def test_reject_multiple_actions_in_turn():
    raw = (
        "<thought>Trying to do two things at once.</thought>\n"
        '<tool_call name="write_site"><file path="a.txt">A</file></tool_call>\n'
        "<finish>Done</finish>"
    )
    ok, cleaned, err, had_thought = clean_assistant_turn(raw)
    assert ok is False
    assert "Multiple agent actions" in err


def test_reject_unbalanced_xml_envelope():
    raw = (
        "<thought>Corrupted XML envelope</thought>\n"
        '<tool_call name="write_site"><file path="a.txt">unclosed file tag</tool_call>'
    )
    ok, cleaned, err, had_thought = clean_assistant_turn(raw)
    assert ok is False
    assert "Unbalanced <file> tags" in err


def test_reject_unsafe_file_path():
    raw = (
        "<thought>Path traversal</thought>\n"
        '<tool_call name="write_site"><file path="../../etc/passwd">secret</file></tool_call>'
    )
    ok, cleaned, err, had_thought = clean_assistant_turn(raw)
    assert ok is False
    assert "unsafe path traversal" in err


# ---------------------------------------------------------------------------
# 3. Conversation-level Cleaning & Preservation
# ---------------------------------------------------------------------------

def test_clean_record_preserves_content_and_cleans_multiturn():
    row = {
        "family_id": "bakery_site",
        "task_id": "bakery_001",
        "messages": [
            {"role": "system", "content": "You are SiteAgent."},
            {"role": "user", "content": "Create header."},
            {
                "role": "assistant",
                "content": "<thought>Build header</thought><tool_call name=\"write_site\"><file path=\"src/Header.tsx\">const H = () => <header/>;</file></tool_call>",
            },
            {"role": "user", "content": "Now finish."},
            {
                "role": "assistant",
                "content": "<thought>Finalizing</thought><finish>Bakery site ready!</finish>",
            },
        ],
    }

    ok, cleaned_row, was_modified, err, thoughts_removed = clean_record(row)
    assert ok is True
    assert was_modified is True
    assert thoughts_removed == 2
    assert err is None

    # Check preserved user & system messages
    assert cleaned_row["messages"][0]["content"] == "You are SiteAgent."
    assert cleaned_row["messages"][1]["content"] == "Create header."
    assert cleaned_row["messages"][3]["content"] == "Now finish."

    # Check cleaned assistant messages
    a1 = cleaned_row["messages"][2]["content"]
    assert "<thought>" not in a1
    assert a1 == '<tool_call name="write_site"><file path="src/Header.tsx">const H = () => <header/>;</file></tool_call>'

    a2 = cleaned_row["messages"][4]["content"]
    assert "<thought>" not in a2
    assert a2 == "<finish>Bakery site ready!</finish>"


def test_clean_record_already_clean_not_modified():
    row = {
        "family_id": "clean_fam",
        "task_id": "clean_001",
        "messages": [
            {"role": "user", "content": "Build header."},
            {"role": "assistant", "content": "<finish>Done</finish>"},
        ],
    }
    ok, cleaned_row, was_modified, err, thoughts_removed = clean_record(row)
    assert ok is True
    assert was_modified is False
    assert thoughts_removed == 0
    assert cleaned_row["messages"] == row["messages"]


# ---------------------------------------------------------------------------
# 4. File-level Cleaning, Atomic Write & Reporting
# ---------------------------------------------------------------------------

def test_clean_dataset_file_generates_report_and_cleans_content(tmp_path):
    input_file = tmp_path / "raw_train.jsonl"
    output_file = tmp_path / "clean_train.jsonl"
    report_file = tmp_path / "cleaning_report.json"

    records = [
        # Record 1: Valid with thought
        {
            "family_id": "f1",
            "task_id": "t1",
            "messages": [
                {"role": "user", "content": "Make widget."},
                {"role": "assistant", "content": "<thought>Making</thought><finish>Done 1</finish>"},
            ],
        },
        # Record 2: Already clean
        {
            "family_id": "f2",
            "task_id": "t2",
            "messages": [
                {"role": "user", "content": "Make button."},
                {"role": "assistant", "content": "<finish>Done 2</finish>"},
            ],
        },
        # Record 3: Malformed (unclosed thought) - should be rejected
        {
            "family_id": "f3",
            "task_id": "t3",
            "messages": [
                {"role": "user", "content": "Make broken."},
                {"role": "assistant", "content": "<thought>Unclosed<finish>Done 3</finish>"},
            ],
        },
    ]

    with open(input_file, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")

    report = clean_dataset_file(
        input_path=input_file,
        output_path=output_file,
        report_path=report_file,
    )

    assert report["total_records"] == 3
    assert report["clean_records_count"] == 2
    assert report["modified_records_count"] == 1
    assert report["unmodified_records_count"] == 1
    assert report["rejected_records_count"] == 1
    assert report["thought_blocks_removed"] == 1
    assert report["zero_thought_verified"] is True
    assert len(report["rejected_records"]) == 1
    assert report["rejected_records"][0]["task_id"] == "t3"

    # Verify report file exists and matches
    assert report_file.exists()
    saved_report = json.loads(report_file.read_text(encoding="utf-8"))
    assert saved_report["clean_records_count"] == 2

    # Verify output file content
    with open(output_file, "r", encoding="utf-8") as f:
        clean_lines = [json.loads(line) for line in f]
    assert len(clean_lines) == 2
    assert "<thought>" not in clean_lines[0]["messages"][1]["content"]
    assert clean_lines[0]["messages"][1]["content"] == "<finish>Done 1</finish>"
    assert clean_lines[1]["messages"][1]["content"] == "<finish>Done 2</finish>"


def test_clean_dataset_file_inplace_creates_backup(tmp_path):
    target_file = tmp_path / "dataset.jsonl"
    record = {
        "family_id": "f1",
        "task_id": "t1",
        "messages": [
            {"role": "user", "content": "Do it."},
            {"role": "assistant", "content": "<thought>Thinking</thought><finish>Did it</finish>"},
        ],
    }
    target_file.write_text(json.dumps(record) + "\n", encoding="utf-8")

    report = clean_dataset_file(target_file, inplace=True, backup=True)
    assert report["clean_records_count"] == 1

    # Check backup file was created
    backup_file = tmp_path / "dataset.jsonl.bak_legacy_thought"
    assert backup_file.exists()
    assert "<thought>" in backup_file.read_text(encoding="utf-8")

    # Check target file was cleaned
    assert "<thought>" not in target_file.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 5. Preflight Integration & Zero-Thought Verification
# ---------------------------------------------------------------------------

def test_preflight_strictly_rejects_think_and_thought_tags(cpu_tokenizer):
    """Verifies that validate_messages and encode_row strictly reject both <think> and <thought>."""
    for bad_tag in ("<think>", "</think>", "<thought>", "</thought>"):
        bad_row = {
            "family_id": "test",
            "task_id": "test_reject",
            "messages": [
                {"role": "user", "content": "Build header."},
                {"role": "assistant", "content": f"{bad_tag}<finish>Done</finish>"},
            ],
        }
        with pytest.raises(ValueError, match=r"Gold target contains.*tag|Embedded ChatML marker"):
            validate_messages(bad_row)

        with pytest.raises(ValueError, match=r"Gold target contains.*tag|Embedded ChatML marker"):
            encode_row(bad_row, cpu_tokenizer, 8192)


def test_cleaned_row_passes_training_preflight(cpu_tokenizer):
    """Verifies that clean_record produces rows that cleanly pass training preflight and encode_row."""
    raw_row = {
        "family_id": "test_preflight",
        "task_id": "test_001",
        "messages": [
            {"role": "user", "content": "Build component."},
            {
                "role": "assistant",
                "content": "<thought>Creating the component.</thought><tool_call name=\"write_site\"><file path=\"src/Component.tsx\">export default function C() { return <div>C</div>; }</file></tool_call>",
            },
        ],
    }

    # Before cleaning: preflight rejects with ValueError
    with pytest.raises(ValueError, match=r"Gold target contains.*tag"):
        validate_messages(raw_row)

    # Clean the row
    ok, cleaned_row, was_modified, err, _ = clean_record(raw_row)
    assert ok is True
    assert was_modified is True

    # After cleaning: preflight and encode_row pass cleanly
    messages = validate_messages(cleaned_row)
    assert len(messages) == 2

    encoded = encode_row(cleaned_row, cpu_tokenizer, 8192)
    assert "input_ids" in encoded
    assert "labels" in encoded
    # Loss mask supervises only the action, with no thought tokens supervised
    supervised_tokens = [t for t in encoded["labels"] if t != -100]
    supervised_text = cpu_tokenizer.decode(supervised_tokens, skip_special_tokens=False)
    assert "<thought>" not in supervised_text
    assert '<tool_call name="write_site">' in supervised_text
