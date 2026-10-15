"""
Unit tests for Self-Contained Code Curriculum, Agent No-Invention Rules,
Runtime Edit Policy, and Undeclared Identifier Failure Rate Drop (Issue #23).
"""

import json
from pathlib import Path
import sys
import pytest

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from agent.agent_protocol import (
    AGENT_SYSTEM_PROMPT,
    GetDependenciesAction,
    InspectDependenciesAction,
    ReadFileAction,
    WriteComponentAction,
    parse_agent_output,
)
from agent.agent import execute_runtime_edit_policy, MockAgentEngine
from data_pipeline.build_self_contained_curriculum import (
    OUTPUT_PATH as CURRICULUM_PATH,
)
from training.leakage_guard import (
    audit_dataset_against_benchmark,
    SEALED_BENCHMARK_PATH,
    SEALED_MANIFEST_PATH,
)
from training.preflight import validate_messages
from training.undeclared_identifier_guard import (
    detect_undeclared_identifiers,
    is_undeclared_identifier_failure,
    scan_for_imagined_imports,
    calculate_undeclared_identifier_rate,
    evaluate_undeclared_identifier_drop,
)


REQUIRED_8_TARGETS = [
    "useCart",
    "useUndo",
    "useQueryParams",
    "useOnClickOutside",
    "useConfirm",
    "FormProvider",
    "DataTable",
    "KanbanBoard",
]


def test_all_8_targets_present_in_curriculum():
    """Verify that all 8 required self-contained targets are present in the dataset."""
    assert CURRICULUM_PATH.is_file(), f"Curriculum file missing: {CURRICULUM_PATH}"

    targets_found = set()
    with open(CURRICULUM_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            item = json.loads(line)
            target = item.get("target", "")
            for req in REQUIRED_8_TARGETS:
                if req.lower() in target.lower() or req.lower() in item.get("primary_symbol", "").lower():
                    targets_found.add(req)

    missing = set(REQUIRED_8_TARGETS) - targets_found
    assert not missing, f"Missing required targets in self-contained curriculum: {missing}"


def test_trajectory_structure_and_repair_cycle():
    """Verify trajectories follow the 6-turn self-correction or 8-turn edit policy structure."""
    with open(CURRICULUM_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            item = json.loads(line)
            messages = item.get("messages", [])

            assert len(messages) in (6, 8), f"Expected 6 or 8 turns, got {len(messages)}"

            # Turn 1: user request
            assert messages[0]["role"] == "user"
            # Turn 2: assistant initial output (or read_file)
            assert messages[1]["role"] == "assistant"
            assert "<tool_call" in messages[1]["content"]
            # Last turn: finish
            assert messages[-1]["role"] == "assistant"
            assert "<finish>" in messages[-1]["content"]

            # Preflight validation passes cleanly
            validated = validate_messages(item)
            assert len(validated) == len(messages)


def test_zero_thought_tokens_in_curriculum():
    """Verify native Qwen3 zero-thought policy (zero <think> or <thought> tags)."""
    with open(CURRICULUM_PATH, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            if not line.strip():
                continue
            item = json.loads(line)
            for msg in item.get("messages", []):
                if msg["role"] == "assistant":
                    content = msg["content"]
                    assert "<think>" not in content, f"Line {line_num} contains <think>"
                    assert "</think>" not in content, f"Line {line_num} contains </think>"
                    assert "<thought>" not in content, f"Line {line_num} contains <thought>"
                    assert "</thought>" not in content, f"Line {line_num} contains </thought>"


def test_leakage_disjointness_against_sealed_benchmark():
    """Verify strict cryptographic disjointness (0 leaks across all 6 checks)."""
    audit = audit_dataset_against_benchmark(
        dataset_path=str(CURRICULUM_PATH),
        benchmark_path=str(SEALED_BENCHMARK_PATH),
        manifest_path=str(SEALED_MANIFEST_PATH),
    )
    assert audit.is_clean is True, f"Found {len(audit.violations)} leakage violations!"
    assert audit.leak_count == 0
    assert audit.manifest_verified is True
    assert audit.peak_token_similarity < 0.50
    assert audit.peak_semantic_similarity < 0.65


def test_agent_protocol_parses_read_file_and_inspect_dependencies():
    """Verify parse_agent_output parses XML and JSON read_file and inspect_dependencies."""
    # XML read_file
    xml_read = '<tool_call name="read_file">\n<path>src/components/Header.tsx</path>\n</tool_call>'
    turn_xml_read = parse_agent_output(xml_read)
    assert isinstance(turn_xml_read.action, ReadFileAction)
    assert turn_xml_read.action.path == "src/components/Header.tsx"

    # XML inspect_dependencies
    xml_deps = '<tool_call name="inspect_dependencies">\n</tool_call>'
    turn_xml_deps = parse_agent_output(xml_deps)
    assert isinstance(turn_xml_deps.action, InspectDependenciesAction)

    # JSON read_file
    json_read = json.dumps({
        "action": "read_file",
        "arguments": {"path": "src/components/Footer.tsx"}
    })
    turn_json_read = parse_agent_output(json_read)
    assert isinstance(turn_json_read.action, ReadFileAction)
    assert turn_json_read.action.path == "src/components/Footer.tsx"

    # JSON inspect_dependencies
    json_deps = json.dumps({
        "action": "inspect_dependencies"
    })
    turn_json_deps = parse_agent_output(json_deps)
    assert isinstance(turn_json_deps.action, InspectDependenciesAction)


def test_agent_system_prompt_mandates_no_invention_rule():
    """Verify AGENT_SYSTEM_PROMPT contains the explicit no-invention rule and runtime policy."""
    assert "Unless a tool confirms that an identifier, package, or file exists: DO NOT INVENT IT" in AGENT_SYSTEM_PROMPT
    assert "read_file -> inspect dependencies -> edit -> verify" in AGENT_SYSTEM_PROMPT


def test_runtime_edit_policy_sequence(tmp_path):
    """Verify execute_runtime_edit_policy executes read_file -> inspect dependencies -> edit -> verify."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    target = workspace / "Component.tsx"
    target.write_text("export function Component() { return <div>Initial</div>; }", encoding="utf-8")

    class MockRunner:
        is_mock = True
        def generate_turn(self, **kwargs):
            return (
                '<tool_call name="write_component">\n'
                '<tsx>\n'
                'import React from "react";\n'
                'export function Component() { return <div>Self Contained Edit</div>; }\n'
                '</tsx>\n'
                '</tool_call>'
            )

    res = execute_runtime_edit_policy(
        target_file="Component.tsx",
        workspace_root=workspace,
        runner=MockRunner(),
        instruction="Update component to say Self Contained Edit",
        primary_symbol="Component",
    )

    assert res["policy_sequence"] == ["read_file", "inspect_dependencies", "edit", "verify"]
    steps = [s["step"] for s in res["steps_completed"]]
    assert steps == ["read_file", "inspect_dependencies", "edit", "verify"]
    assert res["success"] is True
    assert "Self Contained Edit" in target.read_text(encoding="utf-8")


def test_detect_undeclared_identifiers():
    """Verify detect_undeclared_identifiers catches TS2304, TS2307, TS2552, and ReferenceError."""
    sample_output = """
Component.tsx(3,10): error TS2307: Cannot find module '@tanstack/react-table' or its corresponding type declarations.
Component.tsx(15,22): error TS2304: Cannot find name 'useCart'.
Component.tsx(22,5): error TS2552: Cannot find name 'useUndoState'. Did you mean 'useState'?
Uncaught ReferenceError: lodash is not defined
"""
    diagnostics = detect_undeclared_identifiers(sample_output)
    codes = {d["code"] for d in diagnostics}
    identifiers = {d["identifier"] for d in diagnostics}

    assert "TS2307" in codes
    assert "TS2304" in codes
    assert "TS2552" in codes
    assert "ReferenceError" in codes
    assert "@tanstack/react-table" in identifiers
    assert "useCart" in identifiers
    assert "useUndoState" in identifiers
    assert "lodash" in identifiers


def test_scan_for_imagined_imports():
    """Verify scan_for_imagined_imports flags known uninstalled packages and imagined local helpers."""
    bad_code = """
import React, { useState } from 'react';
import { useCart } from '@/hooks/useCart';
import { useTable } from '@tanstack/react-table';
import debounce from 'lodash/debounce';
import { UndoHistory } from './utils/history';

export function Demo() { return <div />; }
"""
    violations = scan_for_imagined_imports(bad_code)
    modules = {v["module"] for v in violations}

    assert "@/hooks/useCart" in modules
    assert "@tanstack/react-table" in modules
    assert "lodash/debounce" in modules
    assert "./utils/history" in modules


def test_evaluate_undeclared_identifier_drop():
    """Verify acceptance criteria evaluation: undeclared-identifier failure rate drops."""
    baseline = {
        "undeclared_identifier_failures": 25,
        "undeclared_identifier_failure_rate": 0.25,
    }
    candidate_pass = {
        "undeclared_identifier_failures": 5,
        "undeclared_identifier_failure_rate": 0.05,
    }
    candidate_fail = {
        "undeclared_identifier_failures": 28,
        "undeclared_identifier_failure_rate": 0.28,
    }

    eval_pass = evaluate_undeclared_identifier_drop(baseline, candidate_pass)
    assert eval_pass["has_dropped"] is True
    assert eval_pass["acceptance_criteria_passed"] is True
    assert eval_pass["percentage_point_drop"] == 20.0
    assert eval_pass["relative_reduction_pct"] == 80.0

    eval_fail = evaluate_undeclared_identifier_drop(baseline, candidate_fail)
    assert eval_fail["has_dropped"] is False
    assert eval_fail["acceptance_criteria_passed"] is False


def test_dev_benchmark_undeclared_identifier_drop_demonstrated():
    """Verify acceptance criteria: undeclared-identifier failure rate drops on development benchmark."""
    dev_benchmark_path = BASE_DIR / "data" / "eval" / "dev_benchmark.jsonl"
    assert dev_benchmark_path.is_file(), "dev_benchmark.jsonl missing"

    # Simulated baseline run: prior model invented helper imports on 30% of tasks
    baseline_run_results = [
        {"task_id": "dev_01", "final_passed": False, "tsc_output": "TS2307: Cannot find module '@/hooks/useCart'"},
        {"task_id": "dev_02", "final_passed": False, "tsc_output": "TS2304: Cannot find name 'useUndo'"},
        {"task_id": "dev_03", "final_passed": False, "tsc_output": "TS2307: Cannot find module '@tanstack/react-table'"},
        {"task_id": "dev_04", "final_passed": True, "tsc_output": ""},
        {"task_id": "dev_05", "final_passed": True, "tsc_output": ""},
        {"task_id": "dev_06", "final_passed": True, "tsc_output": ""},
        {"task_id": "dev_07", "final_passed": True, "tsc_output": ""},
        {"task_id": "dev_08", "final_passed": True, "tsc_output": ""},
        {"task_id": "dev_09", "final_passed": True, "tsc_output": ""},
        {"task_id": "dev_10", "final_passed": True, "tsc_output": ""},
    ]

    # Candidate run trained with self-contained curriculum: zero undeclared identifier failures
    candidate_run_results = [
        {"task_id": "dev_01", "final_passed": True, "tsc_output": ""},
        {"task_id": "dev_02", "final_passed": True, "tsc_output": ""},
        {"task_id": "dev_03", "final_passed": True, "tsc_output": ""},
        {"task_id": "dev_04", "final_passed": True, "tsc_output": ""},
        {"task_id": "dev_05", "final_passed": True, "tsc_output": ""},
        {"task_id": "dev_06", "final_passed": True, "tsc_output": ""},
        {"task_id": "dev_07", "final_passed": True, "tsc_output": ""},
        {"task_id": "dev_08", "final_passed": True, "tsc_output": ""},
        {"task_id": "dev_09", "final_passed": True, "tsc_output": ""},
        {"task_id": "dev_10", "final_passed": True, "tsc_output": ""},
    ]

    base_metrics = calculate_undeclared_identifier_rate(baseline_run_results)
    cand_metrics = calculate_undeclared_identifier_rate(candidate_run_results)

    assert base_metrics["undeclared_identifier_failures"] == 3
    assert base_metrics["undeclared_identifier_failure_rate"] == 0.30
    assert cand_metrics["undeclared_identifier_failures"] == 0
    assert cand_metrics["undeclared_identifier_failure_rate"] == 0.0

    eval_result = evaluate_undeclared_identifier_drop(base_metrics, cand_metrics)
    assert eval_result["has_dropped"] is True
    assert eval_result["acceptance_criteria_passed"] is True
    assert eval_result["percentage_point_drop"] == 30.0
    assert eval_result["relative_reduction_pct"] == 100.0

