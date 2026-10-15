"""
tests/test_motion_patterns.py - Automated Unit & Integration Tests for Motion Architecture

Verifies Section 4 (New Motion Feature Architecture) and Section 5 (Motion Implementation Rules):
1. MotionType enum and MotionSpec dataclass definition.
2. Prompt extraction detecting phrases:
   - scroll animation / scroll reveal
   - parallax
   - horizontal scroll
   - sticky story / pin section
   - text reveal / word reveal
   - micro interaction / hover interaction
   - scroll-driven / scrub
3. Strict decoupling: motion parsing does not contaminate section parsing.
4. XML serialization to <motion_plan> and round-trip parsing.
5. ContentBrief integration with <motion_plan> in brief_to_xml.
6. ContextBuilder high-priority retention of current-section motion under token budget pressure.
7. History compaction retention of motion directives.
"""

import sys
from pathlib import Path

# Add workspace root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from agent.motion_patterns import (
    MotionType,
    MotionSpec,
    extract_motion_requirements,
    motion_spec_to_xml,
    motion_plan_to_xml,
    xml_to_motion_plan,
    get_motion_implementation_guidelines,
)

def test_native_runtime_contract_exposes_reusable_hooks_and_components():
    from agent.motion_patterns import get_native_runtime_contract, native_runtime_import
    contract = get_native_runtime_contract()
    assert contract["client_only"] is False
    assert {"MagneticTarget", "ParallaxLayer", "StickyNarrative", "TiltSurface", "RevealGroup", "VelocityMarquee"}.issubset(contract["exports"])
    assert "usePointerRaf" in native_runtime_import("usePointerRaf")
from agent.site_brief import _build_heuristic_brief, brief_to_xml
from agent.context_builder import ContextBuilder, TokenBudget
from agent.agent import _compact_site_history


def test_motion_type_enum_and_spec_schema():
    """Verify MotionType enum values and MotionSpec dataclass serialization."""
    assert MotionType.SCROLL_REVEAL.value == "scroll_reveal"
    assert MotionType.PARALLAX.value == "parallax"
    assert MotionType.HORIZONTAL_SCROLL.value == "horizontal_scroll"
    assert MotionType.STICKY_STORY.value == "sticky_story"
    assert MotionType.TEXT_REVEAL.value == "text_reveal"
    assert MotionType.MICRO_INTERACTION.value == "micro_interaction"

    spec = MotionSpec(
        type=MotionType.TEXT_REVEAL,
        target_section="hero",
        intensity="subtle",
        axis="y",
        trigger="viewport",
        reduced_motion_behavior="instant",
        mobile_fallback="static",
        implementation="native",
    )
    d = spec.to_dict()
    assert d["type"] == "text_reveal"
    assert d["target_section"] == "hero"
    assert d["intensity"] == "subtle"
    assert d["implementation"] == "native"

    spec_recovered = MotionSpec.from_dict(d)
    assert spec_recovered.type == MotionType.TEXT_REVEAL
    assert spec_recovered.target_section == "hero"


def test_extract_motion_requirements_all_phrases():
    """Verify phrase detection across all 6 motion types."""
    test_cases = [
        ("Build a SaaS hero with word reveal and animated text headline.", MotionType.TEXT_REVEAL),
        ("Create a parallax scrolling visual background in the hero.", MotionType.PARALLAX),
        ("Include a horizontal scroll section for the product showcase.", MotionType.HORIZONTAL_SCROLL),
        ("Design a sticky story narrative with pinned section steps.", MotionType.STICKY_STORY),
        ("Features should have fade in on scroll and scroll animation.", MotionType.SCROLL_REVEAL),
        ("Add interactive hover lifts and micro interactions to cards.", MotionType.MICRO_INTERACTION),
        ("Implement scroll-driven scrub animation on the roadmap.", MotionType.SCROLL_REVEAL),
    ]

    for prompt, expected_type in test_cases:
        specs = extract_motion_requirements(prompt)
        assert len(specs) >= 1, f"Failed to extract motion from '{prompt}'"
        found_types = [s.type for s in specs]
        assert expected_type in found_types, (
            f"Expected {expected_type} in {found_types} for prompt: '{prompt}'"
        )


def test_motion_parsing_decoupled_from_section_parsing():
    """Verify motion requirements extraction does not alter or pollute section parsing."""
    prompt = (
        "Build a website for NexaFlow.\n"
        "1. Header: sticky nav with CTA\n"
        "2. Hero: hero section with text reveal\n"
        "3. Features: features section with horizontal scroll\n"
        "4. Contact: contact section with micro interactions"
    )
    brief = _build_heuristic_brief(prompt)

    # Sections must strictly be standard semantic slugs, not motion phrases
    assert "header" in brief["sections"]
    assert "hero" in brief["sections"]
    assert "features" in brief["sections"]
    assert "contact" in brief["sections"]


    for sec in brief["sections"]:
        assert "reveal" not in sec
        assert "scroll" not in sec
        assert "interaction" not in sec
        assert "horizontal" not in sec

    # Motion plan must contain the extracted specs
    motion_plan = brief.get("motion_plan")
    assert motion_plan is not None
    types = [m.type for m in motion_plan]
    assert MotionType.TEXT_REVEAL in types
    assert MotionType.HORIZONTAL_SCROLL in types
    assert MotionType.MICRO_INTERACTION in types


def test_motion_plan_xml_serialization_and_roundtrip():
    """Verify XML generation matching the specification and round-trip parsing."""
    specs = [
        MotionSpec(type=MotionType.TEXT_REVEAL, target_section="hero", intensity="subtle"),
        MotionSpec(type=MotionType.STICKY_STORY, target_section="process", intensity="medium"),
    ]

    xml_out = motion_plan_to_xml(specs)
    expected_lines = [
        '<motion_plan>',
        '  <motion type="text_reveal" section="hero" intensity="subtle" />',
        '  <motion type="sticky_story" section="process" intensity="medium" />',
        '</motion_plan>',
    ]
    for line in expected_lines:
        assert line in xml_out, f"Missing '{line}' in generated XML:\n{xml_out}"

    # Round-trip parsing
    parsed_specs = xml_to_motion_plan(xml_out)
    assert len(parsed_specs) == 2
    assert parsed_specs[0].type == MotionType.TEXT_REVEAL
    assert parsed_specs[0].target_section == "hero"
    assert parsed_specs[0].intensity == "subtle"
    assert parsed_specs[1].type == MotionType.STICKY_STORY
    assert parsed_specs[1].target_section == "process"
    assert parsed_specs[1].intensity == "medium"


def test_content_brief_renders_motion_plan():
    """Verify brief_to_xml includes the <motion_plan> block."""
    brief = {
        "business_name": "Lumina",
        "business_type": "saas",
        "tagline": "Next-gen creative tooling",
        "sections": ["header", "hero", "features", "footer"],
        "motion_plan": [
            MotionSpec(type=MotionType.TEXT_REVEAL, target_section="hero", intensity="subtle"),
            MotionSpec(type=MotionType.SCROLL_REVEAL, target_section="features", intensity="subtle"),
        ]
    }
    xml = brief_to_xml(brief)
    assert "<motion_plan>" in xml
    assert '<motion type="text_reveal" section="hero" intensity="subtle" />' in xml
    assert '<motion type="scroll_reveal" section="features" intensity="subtle" />' in xml
    assert "</motion_plan>" in xml


def test_motion_implementation_guidelines_native_rules():
    """Verify implementation guidelines enforce native rules from Section 5."""
    scroll_guide = get_motion_implementation_guidelines(
        MotionSpec(type=MotionType.SCROLL_REVEAL, target_section="features")
    )
    assert "IntersectionObserver" in scroll_guide
    assert "prefers-reduced-motion" in scroll_guide

    parallax_guide = get_motion_implementation_guidelines(
        MotionSpec(type=MotionType.PARALLAX, target_section="hero")
    )
    assert "requestAnimationFrame" in parallax_guide
    assert "never call wheel.preventdefault" in parallax_guide.lower()


    text_guide = get_motion_implementation_guidelines(
        MotionSpec(type=MotionType.TEXT_REVEAL, target_section="hero")
    )
    assert "aria-label=" in text_guide
    assert 'aria-hidden="true"' in text_guide

    sticky_guide = get_motion_implementation_guidelines(
        MotionSpec(type=MotionType.STICKY_STORY, target_section="story")
    )
    assert "position: sticky" in sticky_guide


def test_context_builder_preserves_motion_under_token_compaction():
    """Verify ContextBuilder never drops current-section motion under budget pressure."""
    # Constrained budget forcing pruning
    tight_budget = TokenBudget(
        total=1200,
        system_contracts=200,
        current_instruction=200,
        project_metadata=100,
        selected_files=300,
        related_files=200,
        recent_conversation=100,
        build_diagnostics=50,
        reserve=50,
    )
    builder = ContextBuilder(budget=tight_budget)

    class MockSession:
        title = "MotionApp"
        history = [{"role": "user", "content": "previous long conversation turn " * 20}]
        build_state = {"errors": ["Mock compile error 1", "Mock error 2"]}
        def get_current_files(self):
            return {
                "src/components/Hero.tsx": "export function Hero() { return <div className='hero'>Long hero code " + ("x" * 800) + "</div>; }",
                "src/components/Header.tsx": "export function Header() { return <header>Header code " + ("y" * 800) + "</header>; }",
            }

    motion_spec = MotionSpec(
        type=MotionType.STICKY_STORY,
        target_section="features",
        intensity="medium",
    )

    ctx = builder.build_context(
        session=MockSession(),
        new_instruction="Implement the sticky narrative storytelling section.",
        current_section_motion=[motion_spec],
    )

    # Must contain the motion block
    assert "<current_section_motion>" in ctx.prompt_text
    assert "Pattern: sticky_story" in ctx.prompt_text
    assert ctx.motion_text != ""
    # Motion block survived even under tight allowance
    assert "</current_section_motion>" in ctx.prompt_text


def test_compact_site_history_retains_motion_requirement():
    """Verify _compact_site_history preserves motion directives in next section requirements."""
    history = [
        {"role": "system", "content": "System contract."},
        {"role": "user", "content": "Initial prompt."},
        {
            "role": "assistant",
            "content": '<tool_call name="write_site"><file path="src/components/Header.tsx">\ncode\n</file><file path="src/components/Header.css">\n:root { --primary: #000; }\n</file></tool_call>',
        },
        {
            "role": "user",
            "content": (
                '<observation status="ok">\n'
                '[Section files accepted (src/components/Header.tsx, src/components/Header.css) and written to disk.]\n'
                '[NEXT SECTION REQUIRED]: Write the Hero section.\n'
                'Motion requirement: Text reveal with staggered opacity and prefers-reduced-motion fallback.\n'
                'Write ONE <tool_call name="write_site"> with exactly one .tsx file and one .css file for this section.\n'
                '</observation>'
            ),
        },
        {
            "role": "assistant",
            "content": '<tool_call name="write_site"><file path="src/components/Hero.tsx">\nhero code\n</file><file path="src/components/Hero.css">\nhero css\n</file></tool_call>',
        },
    ]

    _compact_site_history(history)

    # Examine compacted turn history[3]
    compacted_obs = history[3]["content"]
    assert "[NEXT SECTION REQUIRED]" in compacted_obs
    assert "Motion requirement:" in compacted_obs
    assert "Text reveal" in compacted_obs


if __name__ == "__main__":
    test_motion_type_enum_and_spec_schema()
    print("PASS: test_motion_type_enum_and_spec_schema")
    test_extract_motion_requirements_all_phrases()
    print("PASS: test_extract_motion_requirements_all_phrases")
    test_motion_parsing_decoupled_from_section_parsing()
    print("PASS: test_motion_parsing_decoupled_from_section_parsing")
    test_motion_plan_xml_serialization_and_roundtrip()
    print("PASS: test_motion_plan_xml_serialization_and_roundtrip")
    test_content_brief_renders_motion_plan()
    print("PASS: test_content_brief_renders_motion_plan")
    test_motion_implementation_guidelines_native_rules()
    print("PASS: test_motion_implementation_guidelines_native_rules")
    test_context_builder_preserves_motion_under_token_compaction()
    print("PASS: test_context_builder_preserves_motion_under_token_compaction")
    test_compact_site_history_retains_motion_requirement()
    print("PASS: test_compact_site_history_retains_motion_requirement")
    print("\nALL 8 MOTION ARCHITECTURE TESTS PASSED SUCCESSFULLY!")
