"""
tests/test_dynamic_output_budget.py - Verification for Issue #24: Dynamic Output Token Budgets

Tests the authoritative output token budgeting engine:
1. Recommended policy tiers & token ranges (512–768, 1024–1536, 1536–2048, 1536–2048, 2048+).
2. Complexity estimation signals:
   - task mode
   - requested files
   - current file length
   - interaction keywords
   - 3D usage
   - repair diagnostics
3. Prevention of 4096-token generation for tiny edits (allocates 512–768).
4. Clamping against max_seq_length.
5. Truncation detection & reduction on complex interaction and 3D tasks.
6. Logging and metadata recording per task across execution paths.
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from agent.agent import (
    AgentModelRunner,
    execute_runtime_edit_policy,
    run_agent_on_example,
    run_site_agent_on_example,
)
from agent.config import ModelRuntimeConfig
from agent.output_budget import (
    BudgetTier,
    TIER_TOKEN_RANGES,
    TaskComplexityFactors,
    estimate_output_budget,
    extract_complexity_factors,
)


# ── Test 1: Policy Tiers & Token Ranges ──────────────────────────────────────

def test_policy_tiers_exact_token_ranges():
    """Verify all 5 tiers match the recommended policy ranges."""
    assert BudgetTier.SMALL_PATCH.value == "small targeted patch"
    assert BudgetTier.NORMAL_COMPONENT.value == "normal component"
    assert BudgetTier.COMPLEX_INTERACTION.value == "complex interaction"
    assert BudgetTier.SITE_SECTION.value == "site section"
    assert BudgetTier.SCENE_3D.value == "3D scene"

    # small targeted patch: 512–768
    min_tok, max_tok, rec = TIER_TOKEN_RANGES[BudgetTier.SMALL_PATCH.value]
    assert min_tok == 512
    assert max_tok == 768
    assert 512 <= rec <= 768

    # normal component: 1024–1536
    min_tok, max_tok, rec = TIER_TOKEN_RANGES[BudgetTier.NORMAL_COMPONENT.value]
    assert min_tok == 1024
    assert max_tok == 1536
    assert 1024 <= rec <= 1536

    # complex interaction: 1536–2048
    min_tok, max_tok, rec = TIER_TOKEN_RANGES[BudgetTier.COMPLEX_INTERACTION.value]
    assert min_tok == 1536
    assert max_tok == 2048
    assert 1536 <= rec <= 2048

    # site section: 1536–2048
    min_tok, max_tok, rec = TIER_TOKEN_RANGES[BudgetTier.SITE_SECTION.value]
    assert min_tok == 1536
    assert max_tok == 2048
    assert 1536 <= rec <= 2048

    # 3D scene: 2048+
    min_tok, max_tok, rec = TIER_TOKEN_RANGES[BudgetTier.SCENE_3D.value]
    assert min_tok >= 2048
    assert rec >= 2048


# ── Test 2: Complexity Estimation Signals ─────────────────────────────────────

def test_3d_usage_triggers_3d_tier():
    """Verify 3D keywords trigger 3D scene tier (2048+ tokens)."""
    test_cases = [
        "Create an interactive Three.js 3D rotating torus knot mesh with WebGL canvas.",
        "Build a 3D product showcase using @react-three/fiber and OrbitControls.",
        "A scene with custom GLSL shaders and particle geometries.",
    ]
    for prompt in test_cases:
        factors = extract_complexity_factors(prompt=prompt, task_mode="component")
        budget = estimate_output_budget(factors)
        assert budget.tier == BudgetTier.SCENE_3D.value
        assert budget.recommended_tokens >= 2048
        assert budget.min_tokens >= 2048


def test_three_products_does_not_trigger_3d_budget():
    factors = extract_complexity_factors(
        prompt="Build an ecommerce shop with three products, a cart, and natural materials.",
        task_mode="site",
    )
    assert not factors.has_3d_usage


def test_interaction_keywords_trigger_complex_interaction_tier():
    """Verify complex interaction keywords trigger complex interaction tier (1536–2048)."""
    interaction_prompts = [
        ("useCart hook with persistent items and checkout calculation", "useCart"),
        ("KanbanBoard<T> with drag and drop column containers", "KanbanBoard"),
        ("DataTable<T> with column sorting, filtering, and pagination", "DataTable"),
        ("Accessible Modal with keyboard navigation and focus-trap on Escape", "Modal"),
        ("useUndo hook managing past/present/future history stack", "useUndo"),
        ("Form with complex schema validation and custom FormProvider", "FormProvider"),
    ]
    for prompt, symbol in interaction_prompts:
        factors = extract_complexity_factors(prompt=prompt, target_symbol=symbol, task_mode="component")
        budget = estimate_output_budget(factors)
        assert budget.tier == BudgetTier.COMPLEX_INTERACTION.value, f"Failed for {symbol}: {budget.tier}"
        assert 1536 <= budget.recommended_tokens <= 2048


def test_site_mode_and_multi_file_trigger_site_section_tier():
    """Verify a simple multi-file site section gets its own budget tier."""
    factors = extract_complexity_factors(
        prompt="Write the Hero section with responsive modern layout and companion CSS.",
        task_mode="site_section",
        requested_files=["src/components/Hero.tsx", "src/components/Hero.css"],
        target_symbol="Hero",
    )
    budget = estimate_output_budget(factors)
    assert budget.tier == BudgetTier.SIMPLE_SITE_SECTION.value
    assert 1600 <= budget.recommended_tokens <= 2200


def test_normal_component_default():
    """Verify standard single component without heavy interaction receives normal component tier (1024–1536)."""
    factors = extract_complexity_factors(
        prompt="Write a clean Badge component that renders a label, variant, and status dot.",
        task_mode="component",
        target_symbol="Badge",
    )
    budget = estimate_output_budget(factors)
    assert budget.tier == BudgetTier.NORMAL_COMPONENT.value
    assert 1024 <= budget.recommended_tokens <= 1536


# ── Test 3: Prevention of 4096-Token Waste on Tiny Edits ───────────────────────

def test_small_patch_prevents_4096_waste():
    """Verify small targeted patch allocates 512–768 tokens, never 4096."""
    factors = extract_complexity_factors(
        prompt="Fix the prop name typo from onChnage to onChange in TextInput.",
        task_mode="patch",
        requested_files=["src/components/TextInput.tsx"],
        current_file_length=350,
        target_symbol="TextInput",
    )
    budget = estimate_output_budget(factors)
    assert budget.tier == BudgetTier.SMALL_PATCH.value
    assert 512 <= budget.recommended_tokens <= 768
    assert budget.clamped_tokens < 1000
    assert budget.clamped_tokens != 4096


def test_single_diagnostic_repair_allocates_small_patch():
    """Verify single undeclared identifier repair allocates small targeted patch."""
    factors = extract_complexity_factors(
        prompt="Component repair",
        task_mode="patch",
        current_file_length=400,
        repair_diagnostics="TS2304: Cannot find name 'useCallback'.",
        target_symbol="Button",
    )
    budget = estimate_output_budget(factors)
    assert budget.tier == BudgetTier.SMALL_PATCH.value
    assert 512 <= budget.recommended_tokens <= 768


# ── Test 4: Clamping Against Available Context Headroom ───────────────────────

def test_context_headroom_clamping():
    """Verify budget is clamped when prompt tokens approach context limit."""
    # When plenty of headroom exists in 8192 context window:
    factors = extract_complexity_factors(
        prompt="Build KanbanBoard<T> with drag and drop",
        target_symbol="KanbanBoard",
    )
    budget = estimate_output_budget(factors, prompt_tokens=2000, max_seq_length=8192)
    assert budget.clamped_tokens == budget.recommended_tokens
    assert budget.clamped_tokens + 2000 <= 8192

    # When context is tight: prompt_tokens = 7500 in 8192 max_seq_length
    budget_tight = estimate_output_budget(factors, prompt_tokens=7500, max_seq_length=8192)
    assert budget_tight.clamped_tokens == 8192 - 7500  # 692
    assert budget_tight.clamped_tokens + 7500 == 8192


# ── Test 5: Truncation Reduction on Complex Interaction ───────────────────────

def test_dynamic_budget_prevents_truncation_on_complex_interaction():
    """Verify dynamic budget gives >= 1536 tokens, preventing truncation seen with 512 tokens."""
    factors = extract_complexity_factors(
        prompt="Implement DataTable<T> with sort, filter, paginate, and custom row renderers.",
        target_symbol="DataTable",
    )
    budget = estimate_output_budget(factors)
    # Under fixed 512, complex tables truncate:
    fixed_low_tokens = 512
    assert budget.clamped_tokens > fixed_low_tokens
    assert budget.clamped_tokens >= 1536


# ── Test 6: ModelRuntimeConfig Integration ────────────────────────────────────

def test_model_runtime_config_delegation():
    """Verify ModelRuntimeConfig exposes dynamic budget methods."""
    factors = extract_complexity_factors(
        prompt="Three.js 3D sphere animation",
        task_mode="3d",
        target_symbol="SphereScene",
    )
    budget = ModelRuntimeConfig.estimate_output_budget(factors, prompt_tokens=500)
    assert budget.tier == BudgetTier.SCENE_3D.value

    dynamic_max = ModelRuntimeConfig.get_dynamic_max_new_tokens(factors, prompt_tokens=500)
    assert dynamic_max >= 2048


# ── Test 7: Logging and Metadata in Agent Execution Paths ─────────────────────

def test_token_budget_logged_in_execute_runtime_edit_policy(tmp_path):
    """Verify execute_runtime_edit_policy logs and records output token budget."""
    runner = AgentModelRunner(model_path="dummy", is_mock=True)
    target_file = tmp_path / "Button.tsx"
    target_file.write_text("export function Button() { return <button>Click</button>; }", encoding="utf-8")

    pkg_json = tmp_path / "package.json"
    pkg_json.write_text('{"dependencies": {"react": "^18.0.0"}}', encoding="utf-8")

    res = execute_runtime_edit_policy(
        target_file="Button.tsx",
        workspace_root=tmp_path,
        runner=runner,
        instruction="Add aria-label='Primary action'",
        primary_symbol="Button",
        max_new_tokens=None,  # test dynamic allocation
    )

    # Verify budget logged in step_log under edit step
    edit_step = next((s for s in res["steps_completed"] if s.get("step") == "edit"), None)
    assert edit_step is not None
    assert "token_budget" in edit_step
    assert edit_step["token_budget"]["tier"] == BudgetTier.SMALL_PATCH.value
    assert 512 <= edit_step["allocated_tokens"] <= 768

    # Verify budget in return dictionary
    assert "output_token_budget" in res
    assert res["output_token_budget"]["tier"] == BudgetTier.SMALL_PATCH.value


def test_token_budget_logged_in_run_agent_on_example(tmp_path):
    """Verify run_agent_on_example logs and records output token budget per task."""
    runner = AgentModelRunner(model_path="dummy", is_mock=True)
    item = {
        "prompt": "Create an accessible Modal with keyboard navigation and focus-trap on Escape.",
        "primary_export": "Modal",
        "test_code": "test('renders modal', () => {});",
        "check": "tsc_and_render",
    }
    res = run_agent_on_example(
        orig_idx=0,
        item=item,
        runner=runner,
        workspace_root=tmp_path,
        max_turns=1,
        max_new_tokens=None,  # dynamic budgeting
    )

    assert "output_token_budget" in res
    budget = res["output_token_budget"]
    assert budget["tier"] == BudgetTier.COMPLEX_INTERACTION.value
    assert 1536 <= budget["recommended_tokens"] <= 2048


def test_token_budget_logged_in_run_site_agent_on_example(tmp_path):
    """Verify run_site_agent_on_example logs and records output token budgets."""
    runner = AgentModelRunner(model_path="dummy", is_mock=True)
    res = run_site_agent_on_example(
        orig_idx=0,
        prompt="A modern SaaS landing page for analytics",
        project_name="AnalyticsApp",
        brief_xml="<brief><sections><section>header</section><section>hero</section></sections></brief>",
        sections=["header", "hero"],
        runner=runner,
        workspace_root=tmp_path,
        max_turns=2,
        max_new_tokens=None,  # dynamic budgeting
    )

    assert "output_token_budgets" in res
    assert len(res["output_token_budgets"]) > 0
    budget = res["output_token_budgets"][0]
    assert budget["tier"] == BudgetTier.SIMPLE_SITE_SECTION.value
    assert 1536 <= budget["recommended_tokens"] <= 2048


@pytest.fixture(autouse=True)
def _freeform_site_strategy(monkeypatch):
    """These tests exercise the legacy code-writing loop, not the design kit."""
    monkeypatch.setenv("SITE_STRATEGY", "freeform")
