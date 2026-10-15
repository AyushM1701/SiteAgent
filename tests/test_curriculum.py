"""
tests/test_curriculum.py

Unit tests for training/curriculum.py:
  - 8-stage training curriculum (Stage A through Stage H)
  - 10 design genomes for Stage C
  - 8 section archetypes for Stage D
  - 6 targeted repair categories for Stage F
  - Known-safe motion primitives for Stage G
  - Aesthetic preference criteria and hard correctness gating for Stage H
  - Stage prerequisite sequencing via CurriculumProgressionController
  - Fail-closed stage validation rules
"""

import json
from pathlib import Path
import pytest

from training.curriculum import (
    CurriculumStage,
    CurriculumProgressionController,
    DESIGN_GENOMES,
    FEATURE_ARCHETYPES,
    REPAIR_CATEGORIES,
    MOTION_PRIMITIVES,
    PREFERENCE_CRITERIA,
    STAGE_SPECS,
    StageValidationResult,
    validate_curriculum_stage,
)


class TestCurriculumTaxonomyAndMetadata:
    """Verifies complete taxonomy of the 8-stage curriculum."""

    def test_all_eight_stages_defined(self):
        expected_stages = {
            "stage_a_protocol_fidelity",
            "stage_b_react_correctness",
            "stage_c_design_system_execution",
            "stage_d_section_archetype_diversity",
            "stage_e_full_site_multi_turn",
            "stage_f_repair_trajectories",
            "stage_g_motion_interactions",
            "stage_h_preference_optimization",
        }
        actual_stages = {s.value for s in CurriculumStage}
        assert actual_stages == expected_stages

    def test_stage_specs_coverage(self):
        for stage in CurriculumStage:
            assert stage in STAGE_SPECS
            spec = STAGE_SPECS[stage]
            assert spec.name.startswith("Stage ")
            assert len(spec.objective) > 10
            assert len(spec.key_constraints) >= 3
            assert len(spec.evaluation_gate) > 10

    def test_stage_c_ten_design_genomes(self):
        expected_genomes = {
            "paper editorial",
            "luxury dark",
            "neo-brutalist",
            "technical monochrome",
            "soft organic",
            "Swiss grid",
            "high-fashion typography",
            "product glass",
            "warm hospitality",
            "playful geometric",
        }
        assert set(DESIGN_GENOMES) == expected_genomes

    def test_stage_d_eight_feature_archetypes(self):
        expected_archetypes = {
            "bento",
            "editorial list",
            "sticky deck",
            "diagram",
            "horizontal ribbon",
            "asymmetric split",
            "comparison table",
            "metric narrative",
        }
        assert set(FEATURE_ARCHETYPES) == expected_archetypes

    def test_stage_f_six_repair_categories(self):
        expected_repairs = {
            "fix_typescript_only",
            "fix_overflow_only",
            "fix_contrast_only",
            "fix_one_interaction",
            "fix_one_token",
            "fix_one_component",
        }
        assert set(REPAIR_CATEGORIES) == expected_repairs

    def test_stage_g_known_safe_primitives(self):
        assert "StickyNarrative" in MOTION_PRIMITIVES
        assert "ScrollReveal" in MOTION_PRIMITIVES
        assert "StaggeredEntrance" in MOTION_PRIMITIVES

    def test_stage_h_preference_criteria(self):
        expected_criteria = {
            "composition",
            "typography",
            "uniqueness",
            "information_hierarchy",
            "polish",
            "responsive_composition",
        }
        assert set(PREFERENCE_CRITERIA) == expected_criteria


class TestCurriculumProgressionController:
    """Verifies strict sequential graduation and prerequisite gating."""

    def test_stage_a_can_start_immediately(self):
        can_advance, msg = CurriculumProgressionController.can_advance_to_stage(
            CurriculumStage.STAGE_A_PROTOCOL_FIDELITY,
            completed_stages=set(),
        )
        assert can_advance is True
        assert "Prerequisites met" in msg

    def test_stage_b_blocked_without_stage_a(self):
        can_advance, msg = CurriculumProgressionController.can_advance_to_stage(
            CurriculumStage.STAGE_B_REACT_CORRECTNESS,
            completed_stages=set(),
        )
        assert can_advance is False
        assert "Stage A" in msg

    def test_stage_c_requires_stage_b(self):
        can_advance, msg = CurriculumProgressionController.can_advance_to_stage(
            CurriculumStage.STAGE_C_DESIGN_SYSTEM_EXECUTION,
            completed_stages={CurriculumStage.STAGE_A_PROTOCOL_FIDELITY},
        )
        assert can_advance is False
        assert "Stage B" in msg

    def test_stage_h_requires_e_f_g(self):
        # Stage H (preference optimization) is strictly forbidden until correctness is proven
        can_advance, msg = CurriculumProgressionController.can_advance_to_stage(
            CurriculumStage.STAGE_H_PREFERENCE_OPTIMIZATION,
            completed_stages={
                CurriculumStage.STAGE_A_PROTOCOL_FIDELITY,
                CurriculumStage.STAGE_B_REACT_CORRECTNESS,
                CurriculumStage.STAGE_C_DESIGN_SYSTEM_EXECUTION,
                CurriculumStage.STAGE_D_SECTION_ARCHETYPE_DIVERSITY,
            },
        )
        assert can_advance is False
        assert "Stage E" in msg or "Stage F" in msg or "Stage G" in msg

        # With all foundational stages A through G completed
        can_advance, msg = CurriculumProgressionController.can_advance_to_stage(
            CurriculumStage.STAGE_H_PREFERENCE_OPTIMIZATION,
            completed_stages={
                CurriculumStage.STAGE_A_PROTOCOL_FIDELITY,
                CurriculumStage.STAGE_B_REACT_CORRECTNESS,
                CurriculumStage.STAGE_C_DESIGN_SYSTEM_EXECUTION,
                CurriculumStage.STAGE_D_SECTION_ARCHETYPE_DIVERSITY,
                CurriculumStage.STAGE_E_FULL_SITE_MULTI_TURN,
                CurriculumStage.STAGE_F_REPAIR_TRAJECTORIES,
                CurriculumStage.STAGE_G_MOTION_INTERACTIONS,
            },
        )
        assert can_advance is True


class TestStageValidators:
    """Validates datasets against stage-specific quality and architectural rules."""

    def test_stage_a_detects_thought_tags(self, tmp_path):
        bad_file = tmp_path / "bad_stage_a.jsonl"
        bad_row = {
            "messages": [
                {"role": "user", "content": "Build header"},
                {"role": "assistant", "content": "<thought>planning</thought><tool_call name=\"write_site\"><file path=\"src/components/Header.tsx\">code</file></tool_call>"},
            ]
        }
        bad_file.write_text(json.dumps(bad_row) + "\n", encoding="utf-8")
        result = validate_curriculum_stage(CurriculumStage.STAGE_A_PROTOCOL_FIDELITY, bad_file)
        assert result.is_valid is False
        assert any("thought tags" in v for v in result.violations)

    def test_stage_a_detects_multiple_actions(self, tmp_path):
        bad_file = tmp_path / "multi_action.jsonl"
        bad_row = {
            "messages": [
                {"role": "user", "content": "Build header"},
                {"role": "assistant", "content": "<tool_call name=\"write_site\"><file path=\"src/components/Header.tsx\">code</file></tool_call><finish>Done</finish>"},
            ]
        }
        bad_file.write_text(json.dumps(bad_row) + "\n", encoding="utf-8")
        result = validate_curriculum_stage(CurriculumStage.STAGE_A_PROTOCOL_FIDELITY, bad_file)
        assert result.is_valid is False
        assert any("exactly 1 action" in v for v in result.violations)

    def test_stage_a_passes_clean_row(self, tmp_path):
        clean_file = tmp_path / "clean_stage_a.jsonl"
        clean_row = {
            "messages": [
                {"role": "user", "content": "Build header"},
                {"role": "assistant", "content": "<tool_call name=\"write_site\"><file path=\"src/components/Header.tsx\">import React from 'react'; export function Header() { return <header>Hi</header>; }</file></tool_call>"},
            ]
        }
        clean_file.write_text(json.dumps(clean_row) + "\n", encoding="utf-8")
        result = validate_curriculum_stage(CurriculumStage.STAGE_A_PROTOCOL_FIDELITY, clean_file)
        assert result.is_valid is True
        assert len(result.violations) == 0

    def test_stage_d_detects_card_grid_monopoly(self, tmp_path):
        grid_file = tmp_path / "grid_monopoly.jsonl"
        rows = [
            {"prompt": "Features as 3 cards", "content": "uniform 3-card grid"}
            for _ in range(10)
        ]
        grid_file.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
        result = validate_curriculum_stage(CurriculumStage.STAGE_D_SECTION_ARCHETYPE_DIVERSITY, grid_file)
        assert result.is_valid is False
        assert any("dominance" in v for v in result.violations)

    def test_stage_g_detects_missing_reduced_motion(self, tmp_path):
        motion_file = tmp_path / "motion_no_reduced.jsonl"
        row = {"css": ".card { animation: float 3s infinite; }"}
        motion_file.write_text(json.dumps(row) + "\n", encoding="utf-8")
        result = validate_curriculum_stage(CurriculumStage.STAGE_G_MOTION_INTERACTIONS, motion_file)
        assert result.is_valid is False
        assert any("prefers-reduced-motion" in v for v in result.violations)

    def test_stage_h_requires_hard_gate_verification(self, tmp_path):
        unverified_file = tmp_path / "unverified_dpo.jsonl"
        row = {
            "prompt": "Build site",
            "chosen": "<tool_call>site A</tool_call>",
            "rejected": "<tool_call>site B</tool_call>",
            # Missing both_passed_hard_gates verification flag
        }
        unverified_file.write_text(json.dumps(row) + "\n", encoding="utf-8")
        result = validate_curriculum_stage(CurriculumStage.STAGE_H_PREFERENCE_OPTIMIZATION, unverified_file)
        assert result.is_valid is False
        assert any("missing hard gate verification" in v for v in result.violations)
