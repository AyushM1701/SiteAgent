"""
tests/test_p2_layout_planning.py

Unit tests for P2-01:
  - Layout archetype planning across 3-tier priority (explicit -> domain-semantic -> entropy seeding)
  - Mathematical elimination of silent default 'grid' collapse
  - Intentional 'grid' preservation for explicit grid requests
  - Backward compatibility of select_layout_archetype and plan_layout_archetype
  - Export of LayoutArchetype, _LAYOUT_ARCHETYPE_GUIDELINES, and _MOTION_VOCABULARY
"""

import pytest
from agent.site_brief import (
    LayoutArchetype,
    _LAYOUT_ARCHETYPES,
    _LAYOUT_ARCHETYPE_GUIDELINES,
    _MOTION_VOCABULARY,
    _DOMAIN_DEFAULT_ARCHETYPE,
    _ENTROPY_POOL,
    detect_prompt_layout_signal,
    plan_layout_archetype,
    select_layout_archetype,
)


class TestP201ExplicitLayoutSignals:
    """Tier 1: Explicit layout declarations and strong keyword signals."""

    @pytest.mark.parametrize(
        "prompt,expected",
        [
            ("Build a SaaS landing page. Layout: editorial", "editorial"),
            ("Create a website with layout archetype: bento", "bento"),
            ("Personal site. Layout: split_hero", "split_hero"),
            ("Company history. Layout: timeline", "timeline"),
            ("Service portal. Layout: tabs", "tabs"),
            ("Creative studio. Layout: asymmetric", "asymmetric"),
            ("Storefront. Layout: grid", "grid"),
            ("Editorial website for a contemporary design studio", "editorial"),
            ("Bento layout dashboard for analytics monitoring", "bento"),
            ("Create a two column hero with split hero presentation", "split_hero"),
            ("Include an interactive milestone timeline roadmap", "timeline"),
            ("Showcase feature tabs with tabbed interface panels", "tabs"),
            ("Design an off-centre asymmetric poster style landing page", "asymmetric"),
            ("Display a uniform product grid for footwear", "grid"),
            ("Curate a masonry gallery grid of photographs", "grid"),
        ],
    )
    def test_explicit_and_keyword_signals(self, prompt, expected):
        detected = detect_prompt_layout_signal(prompt)
        assert detected == expected, f"Expected {expected}, got {detected} for prompt: {prompt}"
        planned = plan_layout_archetype(prompt)
        assert planned == expected


class TestP201DomainSemanticInference:
    """Tier 2: Domain-semantic inference when no explicit keyword is given."""

    @pytest.mark.parametrize(
        "business_type,expected_archetype",
        [
            ("saas", "bento"),
            ("fintech", "bento"),
            ("portfolio", "asymmetric"),
            ("agency", "asymmetric"),
            ("architecture", "editorial"),
            ("blog", "editorial"),
            ("restaurant", "magazine"),
            ("coffee", "magazine"),
            ("ecommerce", "magazine"),
            ("fitness", "split_hero"),
            ("event", "split_hero"),
            ("realestate", "split_hero"),
            ("education", "tabs"),
            ("healthcare", "tabs"),
            ("nonprofit", "timeline"),
        ],
    )
    def test_domain_semantic_archetype_mapping(self, business_type, expected_archetype):
        generic_prompt = f"Build a high-performance modern website for our brand"
        planned = plan_layout_archetype(generic_prompt, business_type=business_type)
        assert planned == expected_archetype, f"Domain {business_type} should map to {expected_archetype}, got {planned}"

    def test_domain_inferred_via_select_layout_archetype_wrapper(self):
        planned = select_layout_archetype(
            "Build an outstanding presence",
            business_name="CloudPulse",
            business_type="saas",
        )
        assert planned == "bento"


class TestP201EntropySeedingAndAntiGridCollapse:
    """Tier 3: Entropy seeding prevents template collapse into generic 'grid'."""

    def test_generic_prompts_never_silently_default_to_grid(self):
        """Generic prompts with diverse brand names should distribute across entropy pool and never collapse to grid."""
        brand_names = [
            "Aura Spatial Audio",
            "Nova Labs",
            "Apex Dynamics",
            "Vortex Systems",
            "Lumina Craft",
            "Solace Therapeutics",
            "Zenith Capital",
            "Kinetix Robotics",
            "Prism Media",
            "Echo Acoustics",
        ]
        results = set()
        for name in brand_names:
            prompt = f"Build a premium website for {name}"
            archetype = select_layout_archetype(prompt, business_name=name)
            # Silent fallback to 'grid' is forbidden
            assert archetype != "grid", f"Unprompted generic site for {name} unexpectedly defaulted to 'grid'!"
            assert archetype in _ENTROPY_POOL, f"Archetype {archetype} not in entropy pool!"
            results.add(archetype)

        # High compositional entropy: diverse businesses yield diverse archetypes
        assert len(results) >= 3, f"Expected at least 3 distinct archetypes across 10 businesses, got: {results}"

    def test_entropy_pool_contains_no_grid(self):
        """The entropy pool must exclude 'grid' so that grid is only chosen deliberately."""
        assert "grid" not in _ENTROPY_POOL


class TestP201IntentionalGridPreservation:
    """Grid must remain accessible when intentionally requested, but never as silent fallback."""

    def test_intentional_grid_via_explicit_syntax(self):
        assert select_layout_archetype("Build a site. Layout: grid", business_name="Store") == "grid"

    def test_intentional_grid_via_keyword(self):
        assert select_layout_archetype("Create a product grid for catalog items", business_name="Shop") == "grid"
        assert select_layout_archetype("Show our portfolio in a card grid", business_name="Artist") == "grid"


class TestP201BackwardCompatibilityAndSignatures:
    """Public API compatibility with legacy code calling select_layout_archetype."""

    def test_single_arg_call(self):
        result = select_layout_archetype("Create a modern website")
        assert isinstance(result, str)
        assert result in _LAYOUT_ARCHETYPES
        assert result != "grid"

    def test_positional_two_args(self):
        result = select_layout_archetype("Create a modern website", "AudioFlow")
        assert isinstance(result, str)
        assert result in _LAYOUT_ARCHETYPES
        assert result != "grid"

    def test_keyword_args(self):
        result = select_layout_archetype(
            prompt="Build a website",
            business_name="FitPulse",
            business_type="fitness",
        )
        assert result == "split_hero"


class TestP201ExportedArtifactsAndSchemas:
    """Verification of exported enums, registries, and schemas."""

    def test_layout_archetype_enum(self):
        expected_members = {"editorial", "bento", "split_hero", "magazine", "timeline", "tabs", "asymmetric", "grid"}
        actual_members = {e.value for e in LayoutArchetype}
        assert actual_members == expected_members

    def test_guidelines_and_motion_vocabulary_coverage(self):
        for archetype in LayoutArchetype:
            # String lookup
            assert archetype.value in _LAYOUT_ARCHETYPE_GUIDELINES
            assert archetype.value in _MOTION_VOCABULARY
            # Enum lookup
            assert _LAYOUT_ARCHETYPE_GUIDELINES.get(archetype) is not None
            assert _MOTION_VOCABULARY.get(archetype) is not None

            # Check motion vocabulary structure
            motion_info = _MOTION_VOCABULARY[archetype.value]
            assert "guidelines" in motion_info
            assert "reduced_motion" in motion_info
            assert "primary_pattern" in motion_info
