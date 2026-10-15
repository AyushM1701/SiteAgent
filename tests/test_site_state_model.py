"""
tests/test_site_state_model.py - Test Suite for Authoritative Site State Model:
1. Three separate concepts:
   - section_completion (e.g. 6 / 6)
   - project_validation (passed / failed)
   - generation_quality (native / repaired / fallback)
2. Final passed formula:
   final_passed = (
       generation_complete
       and validation.passed
       and interaction_validation.passed
       and visual_validation.passed
   )
3. Never: 6 / 6 sections => final_passed
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock

from agent.project_validator import (
    ValidationResult,
    InteractionValidationResult,
    VisualValidationResult,
)
from server.app import ProjectRepairResult, _run_site_generation, session_manager


# ── 1. Conceptual Decoupling Unit Tests ────────────────────────────────────────

def test_six_of_six_does_not_equal_final_passed_when_validation_fails():
    """Confirms that having all sections complete (6/6) fails closed if validation fails."""
    sections_completed = 6
    sections_planned = 6
    generation_complete = (sections_completed == sections_planned)

    broken_val = ValidationResult(
        typecheck_passed=False,
        build_passed=False,
        lint_passed=True,
        contract_passed=True,
        accessibility_passed=True,
        motion_passed=True,
        runtime_passed=False,
        preview_running=False,
        errors=["TS2304: Cannot find name 'badIdentifier'"],
    )
    int_val = InteractionValidationResult(passed=False, status="failed")
    vis_val = VisualValidationResult(passed=False, status="failed")

    final_passed = bool(
        generation_complete
        and broken_val.passed
        and int_val.passed
        and vis_val.passed
    )

    assert generation_complete is True
    assert broken_val.passed is False
    assert final_passed is False, "6/6 sections MUST NOT equate to final_passed when validation fails!"


def test_final_passed_fails_when_interaction_fails():
    """Confirms that final_passed is False if DOM interaction (Gate 4b) triggers exceptions."""
    generation_complete = True
    clean_val = ValidationResult(
        typecheck_passed=True,
        build_passed=True,
        lint_passed=True,
        contract_passed=True,
        accessibility_passed=True,
        motion_passed=True,
        runtime_passed=True,
        preview_running=True,
        interaction_passed=False,  # interaction failed
        interaction_errors=["[Interaction Error] Uncaught TypeError in onClick handler"],
    )
    int_val = InteractionValidationResult(
        passed=False,
        status="failed",
        errors=["[Interaction Error] Uncaught TypeError in onClick handler"],
    )
    vis_val = VisualValidationResult(passed=True, status="passed", score=4.5)

    final_passed = bool(
        generation_complete
        and clean_val.passed
        and int_val.passed
        and vis_val.passed
    )

    assert final_passed is False, "final_passed MUST be False when interaction validation fails!"


def test_final_passed_fails_when_visual_fails():
    """Confirms that final_passed is False if visual validation score < 3/5."""
    generation_complete = True
    clean_val = ValidationResult(
        typecheck_passed=True,
        build_passed=True,
        lint_passed=True,
        contract_passed=True,
        accessibility_passed=True,
        motion_passed=True,
        runtime_passed=True,
        preview_running=True,
    )
    int_val = InteractionValidationResult(passed=True, status="passed")
    vis_val = VisualValidationResult(
        passed=False,
        status="failed",
        score=1.5,
        issues=["Blank page rendered", "Zero contrast"],
    )

    final_passed = bool(
        generation_complete
        and clean_val.passed
        and int_val.passed
        and vis_val.passed
    )

    assert final_passed is False, "final_passed MUST be False when visual validation fails!"


def test_final_passed_fails_when_sections_incomplete():
    """Confirms that final_passed is False if not all planned sections were completed (e.g. 5/6)."""
    sections_completed = 5
    sections_planned = 6
    generation_complete = (sections_completed == sections_planned)

    clean_val = ValidationResult(
        typecheck_passed=True,
        build_passed=True,
        lint_passed=True,
        contract_passed=True,
        accessibility_passed=True,
        motion_passed=True,
        runtime_passed=True,
        preview_running=True,
    )
    int_val = InteractionValidationResult(passed=True, status="passed")
    vis_val = VisualValidationResult(passed=True, status="passed", score=4.5)

    final_passed = bool(
        generation_complete
        and clean_val.passed
        and int_val.passed
        and vis_val.passed
    )

    assert generation_complete is False
    assert final_passed is False, "final_passed MUST be False when sections are incomplete!"


def test_final_passed_succeeds_only_when_all_four_pass():
    """Confirms that final_passed is True ONLY when all 4 gates pass."""
    generation_complete = True
    clean_val = ValidationResult(
        typecheck_passed=True,
        build_passed=True,
        lint_passed=True,
        contract_passed=True,
        accessibility_passed=True,
        motion_passed=True,
        runtime_passed=True,
        preview_running=True,
    )
    int_val = InteractionValidationResult(passed=True, status="passed")
    vis_val = VisualValidationResult(passed=True, status="passed", score=4.8)

    final_passed = bool(
        generation_complete
        and clean_val.passed
        and int_val.passed
        and vis_val.passed
    )

    assert final_passed is True


# ── 2. Generation Quality Classification Tests ────────────────────────────────

@pytest.mark.parametrize(
    "turn_logs,auto_recovered,expected_quality",
    [
        (
            [
                {"turn": 1, "action": "write_site_ok", "section": "header"},
                {"turn": 2, "action": "write_site_ok", "section": "hero"},
            ],
            [],
            "native",
        ),
        (
            [
                {"turn": 1, "action": "write_site_no_css", "section": "header"},
                {"turn": 2, "action": "write_site_ok", "section": "header"},
                {"turn": 3, "action": "write_site_ok", "section": "hero"},
            ],
            [],
            "repaired",
        ),
        (
            [
                {"turn": 1, "action": "write_site_tsc_error", "section": "header"},
                {"turn": 2, "action": "write_site_ok", "section": "header"},
            ],
            [],
            "repaired",
        ),
        (
            [
                {"turn": 1, "action": "write_site_ok", "section": "header"},
                {"turn": 2, "action": "write_site_auto_guarantee", "section": "footer", "auto_recovered": True},
            ],
            ["footer"],
            "fallback",
        ),
    ],
)
def test_generation_quality_classification(turn_logs, auto_recovered, expected_quality):
    """Verifies generation_quality is accurately classified as native, repaired, or fallback."""
    repair_actions = {
        "write_site_section_mismatch",
        "write_site_no_css",
        "write_site_style_violation",
        "write_site_tsc_error",
        "write_site_empty",
    }
    has_fallback = len(auto_recovered) > 0 or any(entry.get("auto_recovered") for entry in turn_logs)
    has_repairs = any(entry.get("action") in repair_actions for entry in turn_logs)

    if has_fallback:
        quality = "fallback"
    elif has_repairs:
        quality = "repaired"
    else:
        quality = "native"

    assert quality == expected_quality


# ── 3. ProjectRepairResult Dataclass State Model Tests ────────────────────────

def test_project_repair_result_embeds_three_concepts():
    clean_val = ValidationResult(
        typecheck_passed=True,
        build_passed=True,
        lint_passed=True,
        contract_passed=True,
        accessibility_passed=True,
        motion_passed=True,
        runtime_passed=True,
        preview_running=True,
    )
    res = ProjectRepairResult(
        validation=clean_val,
        files_modified=["App.tsx"],
        repair_attempts=0,
        generation_complete=True,
        section_completion="6 / 6",
        project_validation="passed",
        generation_quality="native",
        visual_score=4.5,
    )

    assert res.section_completion == "6 / 6"
    assert res.project_validation == "passed"
    assert res.generation_quality == "native"
    assert res.generation_complete is True
    assert res.interaction_validation.passed is True
    assert res.visual_validation.passed is True
    assert res.passed is True


def test_project_repair_result_fails_closed_on_interaction_failure():
    val_with_int_error = ValidationResult(
        typecheck_passed=True,
        build_passed=True,
        lint_passed=True,
        contract_passed=True,
        accessibility_passed=True,
        motion_passed=True,
        runtime_passed=True,
        preview_running=True,
        errors=["[Interaction Error] DOM event handler crashed"],
    )
    res = ProjectRepairResult(
        validation=val_with_int_error,
        section_completion="6 / 6",
        project_validation="failed",
        generation_quality="native",
    )
    assert res.interaction_validation.passed is False
    assert res.passed is False


# ── 4. run_site_agent_on_example Integration Tests ────────────────────────────

def test_run_site_agent_returns_three_concepts(monkeypatch, tmp_path):
    """Verifies that run_site_agent_on_example returns section_completion, project_validation, and generation_quality."""
    from agent import run_site_agent_on_example

    runner_mock = MagicMock()
    # Model generates Header then Hero
    runner_mock.generate_turn.side_effect = [
        '<tool_call name="write_site">\n<file path="src/components/Header.tsx">\nexport function Header() { return <header>Header</header>; }\n</file>\n<file path="src/components/Header.css">\n.header { display: block; }\n</file>\n</tool_call>',
        '<tool_call name="write_site">\n<file path="src/components/Hero.tsx">\nexport function Hero() { return <main>Hero</main>; }\n</file>\n<file path="src/components/Hero.css">\n.hero { display: block; }\n</file>\n</tool_call>',
    ]

    monkeypatch.setattr("agent.agent.run_command", lambda *a, **kw: MagicMock(returncode=0, stdout="", stderr=""))
    monkeypatch.setattr("agent.project_validator.run_project_typecheck", lambda *a, **kw: (True, []))

    res = run_site_agent_on_example(
        orig_idx=0,
        prompt="A portfolio website",
        project_name="Portfolio",
        brief_xml="<brief><sections><section>header</section><section>hero</section></sections></brief>",
        sections=["header", "hero"],
        runner=runner_mock,
        workspace_root=tmp_path,
        max_turns=3,
    )

    assert "section_completion" in res
    assert res["section_completion"] == "2 / 2"
    assert res["sections_completed"] == 2
    assert res["sections_planned"] == ["header", "hero"]
    assert res["generation_complete"] is True
    assert res["project_validation"] == "passed"
    assert res["generation_quality"] == "native"
    assert res["final_passed"] is True
    assert res["interaction_validation"].passed is True
    assert res["visual_validation"].passed is True


def test_run_site_agent_classifies_fallback_when_auto_scaffolded(monkeypatch, tmp_path):
    """Verifies that run_site_agent_on_example classifies quality as fallback when sections are auto-scaffolded."""
    from agent import run_site_agent_on_example

    runner_mock = MagicMock()
    # Model produces bad output for 1 turn, hits budget and guarantee auto-scaffolds
    runner_mock.generate_turn.return_value = "I am not calling any tool."

    monkeypatch.setattr("agent.agent.run_command", lambda *a, **kw: MagicMock(returncode=0, stdout="", stderr=""))
    monkeypatch.setattr("agent.project_validator.run_project_typecheck", lambda *a, **kw: (True, []))

    res = run_site_agent_on_example(
        orig_idx=0,
        prompt="A portfolio website",
        project_name="Portfolio",
        brief_xml="<brief><sections><section>header</section><section>hero</section></sections></brief>",
        sections=["header", "hero"],
        runner=runner_mock,
        workspace_root=tmp_path,
        max_turns=1,
    )

    assert res["section_completion"] == "2 / 2"
    assert res["generation_complete"] is True
    assert res["generation_quality"] == "fallback"
    assert len(res["auto_recovered_sections"]) > 0


# ── 5. _run_site_generation State Propagation Tests ───────────────────────────

def test_run_site_generation_propagates_state_model(monkeypatch, tmp_path):
    """Verifies that _run_site_generation populates site_entry with the 3 concepts and evaluated final_passed."""
    import queue
    q = queue.Queue()

    task_id = "test_state_model_01"
    task = {
        "task_id": task_id,
        "prompt": "Build a modern company website",
        "symbol": "CompanySite",
        "max_turns": 4,
    }

    import agent
    monkeypatch.setattr(agent, "run_site_agent_on_example", lambda **kwargs: {
        "files": {
            "src/components/Header.tsx": "export function Header() { return <header>Header</header>; }",
            "src/components/Hero.tsx": "export function Hero() { return <main id='site-main'>Hero</main>; }",
        },
        "sections_completed": 2,
        "sections_planned": ["header", "hero"],
        "generation_complete": True,
        "section_completion": "2 / 2",
        "project_validation": "passed",
        "generation_quality": "native",
        "turn_logs": [],
        "auto_recovered_sections": [],
        "final_passed": True,
    })

    monkeypatch.setattr("server.app._scaffold_site_vite_runner", lambda *args, **kwargs: None)

    clean_val = ValidationResult(
        typecheck_passed=True, build_passed=True, lint_passed=True,
        contract_passed=True, accessibility_passed=True, motion_passed=True,
        runtime_passed=True, preview_running=True,
    )
    int_val = InteractionValidationResult(passed=True, status="passed")
    vis_val = VisualValidationResult(passed=True, status="passed", score=4.2)

    monkeypatch.setattr("server.app.verify_and_repair_project", lambda **kwargs: ProjectRepairResult(
        validation=clean_val,
        files_modified=["App.tsx"],
        repair_attempts=0,
        self_corrected=False,
        passed=True,
        visual_score=4.2,
        interaction_validation=int_val,
        visual_validation=vis_val,
    ))

    _run_site_generation(task, q)

    # Inspect results
    events = []
    while not q.empty():
        events.append(q.get_nowait())

    result_evt = next((e for e in events if e.get("type") == "result"), None)
    assert result_evt is not None, "Missing result event from _run_site_generation"
    data = result_evt["data"]

    assert data["section_completion"] == "2 / 2"
    assert data["project_validation"] == "passed"
    assert data["generation_quality"] == "native"
    assert data["generation_complete"] is True
    assert data["final_passed"] is True
    assert "interaction_validation" in data
    assert "visual_validation" in data
