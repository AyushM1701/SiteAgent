"""
tests/test_design_planning.py - Tests for Section 3.B & 3.C:
Balanced Layout Archetypes and Deterministic Design-Planning Supervision.
"""

import json
import pytest
from typing import Dict, List

from agent.design_plan import (
    DesignPlan,
    synthesize_design_plan,
    CANONICAL_HERO_ARCHETYPES,
    VALID_DENSITIES,
    VALID_TYPE_SCALES,
    VALID_MOBILE_STRATEGIES,
)
from agent.archetype_templates import (
    render_hero_archetype,
    render_product_stage_hero,
    render_full_bleed_hero,
    render_terminal_data_hero,
    render_restrained_centered_hero,
    render_split_hero,
    render_editorial_layout,
    render_bento_grid,
)
from evaluation.diversity_evaluator import (
    extract_site_design_signature,
    get_canonical_hero_archetype,
    HERO_ARCHETYPES,
    CANONICAL_HERO_MAP,
)


def test_design_plan_schema_and_json_serialization():
    """Verify that DesignPlan matches the exact JSON schema specified in Section 3.C."""
    plan = DesignPlan(
        artDirection="editorial industrial",
        heroArchetype="split",
        density="airy",
        typeScale="display-heavy",
        sectionRhythm=["quiet", "dense", "immersive", "quiet"],
        motion=["text-reveal", "sticky-story"],
        visualAnchor="product-render",
        mobileStrategy="stack",
    )

    d = plan.to_dict()
    assert d["artDirection"] == "editorial industrial"
    assert d["heroArchetype"] == "split"
    assert d["density"] == "airy"
    assert d["typeScale"] == "display-heavy"
    assert d["sectionRhythm"] == ["quiet", "dense", "immersive", "quiet"]
    assert d["motion"] == ["text-reveal", "sticky-story"]
    assert d["visualAnchor"] == "product-render"
    assert d["mobileStrategy"] == "stack"

    # Verify JSON serialization round-trip
    compact_json = plan.to_compact_json()
    parsed = json.loads(compact_json)
    assert parsed == d

    # Verify deserialization
    reconstructed = DesignPlan.from_dict(parsed)
    assert reconstructed.to_dict() == d


def test_design_plan_prompt_block():
    """Verify formatting of the design plan prompt conditioning block."""
    plan = DesignPlan(
        artDirection="technical precision",
        heroArchetype="bento",
        density="compact",
        typeScale="technical-mono",
    )
    prompt_str = plan.to_prompt_block()
    assert "=== STRUCTURED DESIGN PLAN ===" in prompt_str
    assert '"heroArchetype": "bento"' in prompt_str
    assert '"artDirection": "technical precision"' in prompt_str


def test_deterministic_design_plan_archetype_balancing():
    """Verify that synthesize_design_plan cycles evenly across all 7 archetypes."""
    plans = [synthesize_design_plan(domain="saas", task_index=i) for i in range(21)]
    archetypes = [p.heroArchetype for p in plans]

    # Every one of the 7 canonical archetypes must appear exactly 3 times in 21 tasks
    counts = {arch: archetypes.count(arch) for arch in CANONICAL_HERO_ARCHETYPES}
    for arch in CANONICAL_HERO_ARCHETYPES:
        assert counts[arch] == 3, f"Archetype {arch} count expected 3, got {counts[arch]}"

    # No archetype dominates the batch (max ratio = 1/7 ~= 14.3% << 80%)
    for arch, cnt in counts.items():
        ratio = cnt / len(plans)
        assert ratio < 0.20, f"Archetype {arch} ratio {ratio:.1%} exceeds 20%"


def test_deterministic_design_plan_domain_customization():
    """Verify that different domains receive domain-appropriate art directions and rhythm."""
    saas_plan = synthesize_design_plan(domain="saas", task_index=0)
    dev_plan = synthesize_design_plan(domain="developer", task_index=0)
    ecom_plan = synthesize_design_plan(domain="ecommerce", task_index=0)
    arch_plan = synthesize_design_plan(domain="architecture", task_index=0)

    assert "saas" in saas_plan.artDirection or "technical" in saas_plan.artDirection
    assert dev_plan.typeScale in ("technical-mono", "typographic-contrast")
    assert ecom_plan.density in ("airy", "dense")
    assert arch_plan.visualAnchor in ("3d-stage", "photography-bleed", "product-render")


def test_render_all_7_hero_archetypes_and_detect_signature():
    """Verify that all 7 hero templates compile to valid TSX/CSS and are detected by the diversity evaluator."""
    expected_archetypes = [
        "split",
        "editorial_asymmetric",
        "full_bleed_visual",
        "bento",
        "terminal_data",
        "product_stage",
        "restrained_centered",
    ]

    for arch in expected_archetypes:
        tsx, css = render_hero_archetype(arch, component_name="HeroSection")
        assert len(tsx) > 200, f"TSX code empty for {arch}"
        assert len(css) > 200, f"CSS code empty for {arch}"

        files = {
            "src/components/HeroSection.tsx": tsx,
            "src/components/HeroSection.css": css,
            "src/App.tsx": "import HeroSection from './components/HeroSection'; export default function App() { return <HeroSection />; }",
        }
        sig = extract_site_design_signature(files)
        detected_canon = get_canonical_hero_archetype(sig.hero_layout)
        assert detected_canon == arch, f"Expected canonical archetype {arch}, got {detected_canon} (raw: {sig.hero_layout})"
