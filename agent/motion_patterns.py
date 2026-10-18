"""
agent/motion_patterns.py - First-Class Motion Architecture & Pattern Engine

Motion feature architecture and implementation rules:

Features:
1. Scrolling animations (IntersectionObserver scroll reveal)
2. Parallax scrolling (passive RAF scroll-driven transform)
3. Horizontal scroll sections (desktop translate3d track, mobile scroll-snap)
4. Sticky positioning / sticky storytelling (CSS position: sticky)
5. Text reveal on scroll (accessible aria-label with decorative spans)
6. Micro-interactions (hover/focus parity, aria-pressed state)

Decouples motion requirement extraction completely from section parsing.
"""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Set, Tuple, Union


class MotionType(str, Enum):
    SCROLL_REVEAL = "scroll_reveal"
    PARALLAX = "parallax"
    HORIZONTAL_SCROLL = "horizontal_scroll"
    STICKY_STORY = "sticky_story"
    TEXT_REVEAL = "text_reveal"
    MICRO_INTERACTION = "micro_interaction"


# Small native primitives are deliberately named so generated sites can compose
# audited behavior rather than reimplementing scroll physics in every component.
NATIVE_MOTION_PRIMITIVES: Dict[str, Dict[str, Any]] = {
    "MagneticTarget": {"event_model": "pointer", "layout_safe": True},
    "CursorFollower": {"event_model": "pointer+raf", "layout_safe": True},
    "TiltSurface": {"event_model": "pointer+raf", "layout_safe": True},
    "TextScramble": {"event_model": "raf", "layout_safe": True},
    "VelocityMarquee": {"event_model": "raf", "layout_safe": True},
    "StickyNarrative": {"event_model": "css-sticky", "layout_safe": True},
    "ParallaxLayer": {"event_model": "passive-scroll+raf", "layout_safe": True},
    "RevealGroup": {"event_model": "intersection-observer", "layout_safe": True},
    "ScrollProgress": {"event_model": "passive-scroll+raf", "layout_safe": True},
    "PointerLight": {"event_model": "pointer+raf", "layout_safe": True},
}

# Import contract used by site generators.  Keeping this in the planning module
# means generated pages can opt into primitives without copying implementation.
NATIVE_RUNTIME_MODULE = "agent/visual_assets/NativeMotion"
NATIVE_RUNTIME_EXPORTS = (
    "MagneticTarget", "ParallaxLayer", "StickyNarrative", "TiltSurface",
    "RevealGroup", "VelocityMarquee", "useReducedMotion", "usePointerRaf",
    "useScrollProgress", "useIntersectionReveal",
)

def get_native_runtime_contract() -> Dict[str, Any]:
    return {"module": NATIVE_RUNTIME_MODULE, "exports": list(NATIVE_RUNTIME_EXPORTS),
            "css": "agent/visual_assets/NativeMotion.css", "client_only": False}

def native_runtime_import(*names: str) -> str:
    """Render a stable import statement for generated TSX."""
    selected = [name for name in names if name in NATIVE_RUNTIME_EXPORTS]
    if not selected:
        selected = list(NATIVE_RUNTIME_EXPORTS)
    return f"import {{ {', '.join(selected)} }} from './visual_assets/NativeMotion';"


def get_native_motion_primitives() -> Dict[str, Dict[str, Any]]:
    """Return the audited primitive contract exposed to planning/generation."""
    return {name: {**meta, "reduced_motion": "static", "cleanup_required": True,
                   "uses_transform_or_opacity_only": True} for name, meta in NATIVE_MOTION_PRIMITIVES.items()}


@dataclass
class MotionSpec:
    type: MotionType
    target_section: str
    intensity: Literal["subtle", "medium", "cinematic"] = "subtle"
    axis: Literal["x", "y", "both", "none"] = "y"
    trigger: Literal["viewport", "scroll-progress", "interaction"] = "viewport"
    reduced_motion_behavior: Literal["static", "instant", "native-scroll"] = "static"
    mobile_fallback: Literal["stack", "native-horizontal", "static"] = "stack"
    implementation: Literal["native", "gsap", "framer-motion"] = "native"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value if isinstance(self.type, MotionType) else str(self.type),
            "target_section": self.target_section,
            "intensity": self.intensity,
            "axis": self.axis,
            "trigger": self.trigger,
            "reduced_motion_behavior": self.reduced_motion_behavior,
            "mobile_fallback": self.mobile_fallback,
            "implementation": self.implementation,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MotionSpec:
        m_type = data.get("type", "scroll_reveal")
        if isinstance(m_type, str):
            try:
                m_type = MotionType(m_type)
            except ValueError:
                m_type = MotionType.SCROLL_REVEAL

        return cls(
            type=m_type,
            target_section=str(data.get("target_section", "general")),
            intensity=data.get("intensity", "subtle"),
            axis=data.get("axis", "y"),
            trigger=data.get("trigger", "viewport"),
            reduced_motion_behavior=data.get("reduced_motion_behavior", "static"),
            mobile_fallback=data.get("mobile_fallback", "stack"),
            implementation=data.get("implementation", "native"),
        )


# ── Prompt Extraction (Decoupled from section parsing) ───────────────────────

_MOTION_PHRASES = [
    # (Regex pattern, MotionType, default_intensity, default_axis, default_trigger)
    (r"\b(?:text\s+reveals?|word\s+reveals?|animated\s+texts?|reveal\s+text)\b", MotionType.TEXT_REVEAL, "subtle", "y", "viewport"),
    (r"\b(?:parallax(?:\s+scrolling)?|depth\s+scrolls?)\b", MotionType.PARALLAX, "medium", "y", "scroll-progress"),
    (r"\b(?:horizontal\s+scroll(?:ing|s)?|horizontal\s+sections?|sideways\s+scrolls?)\b", MotionType.HORIZONTAL_SCROLL, "medium", "x", "scroll-progress"),
    (r"\b(?:sticky\s+stor(?:y|ies|ytelling)?|sticky\s+sections?|pin\s+sections?|pinned\s+sections?|sticky\s+positioning)\b", MotionType.STICKY_STORY, "medium", "y", "scroll-progress"),
    (r"\b(?:scroll\s+animations?|scroll\s+reveals?|fade\s+in\s+on\s+scroll|scroll-driven|scrubs?)\b", MotionType.SCROLL_REVEAL, "subtle", "y", "viewport"),
    (r"\b(?:micro\s+interactions?|micro-interactions?|hover\s+interactions?|interactive\s+hovers?|hover\s+lifts?)\b", MotionType.MICRO_INTERACTION, "subtle", "none", "interaction"),
]



def extract_motion_requirements(prompt: str, available_sections: Optional[List[str]] = None) -> List[MotionSpec]:
    """
    Extracts motion requirements from a prompt into structured MotionSpec objects.
    Completely decoupled from section parsing so that motion phrases do not contaminate
    section counts or names.
    """
    if not prompt or not isinstance(prompt, str):
        return []

    found_specs: List[MotionSpec] = []
    seen_types: set[Tuple[MotionType, str]] = set()

    sections = [s.lower() for s in (available_sections or ["hero", "features", "pricing", "contact", "footer"])]

    # Detect explicit motion directives
    for pattern, motion_type, default_intensity, default_axis, default_trigger in _MOTION_PHRASES:
        matches = list(re.finditer(pattern, prompt, re.IGNORECASE))
        if not matches:
            continue

        for m in matches:
            # Check surrounding context (window of ~60 chars before and after) to identify target section
            start = max(0, m.start() - 60)
            end = min(len(prompt), m.end() + 60)
            context_window = prompt[start:end].lower()

            target_sec = "general"
            for sec in sections:
                if sec in context_window:
                    target_sec = sec
                    break

            # Natural default targets if not explicitly mentioned
            if target_sec == "general":
                if motion_type == MotionType.TEXT_REVEAL:
                    target_sec = "hero" if "hero" in sections else sections[0]
                elif motion_type == MotionType.HORIZONTAL_SCROLL:
                    target_sec = "features" if "features" in sections else (sections[1] if len(sections) > 1 else sections[0])
                elif motion_type == MotionType.STICKY_STORY:
                    target_sec = "features" if "features" in sections else (sections[1] if len(sections) > 1 else sections[0])
                elif motion_type == MotionType.PARALLAX:
                    target_sec = "hero" if "hero" in sections else sections[0]
                elif motion_type == MotionType.SCROLL_REVEAL:
                    target_sec = "features" if "features" in sections else ("projects" if "projects" in sections else (sections[1] if len(sections) > 1 else sections[0]))
                elif motion_type == MotionType.MICRO_INTERACTION:
                    target_sec = "general"

            # Detect intensity from prompt window
            intensity: Literal["subtle", "medium", "cinematic"] = default_intensity
            if any(k in context_window for k in ["cinematic", "dramatic", "heavy", "intense", "high"]):
                intensity = "cinematic"
            elif any(k in context_window for k in ["medium", "moderate", "fluid", "smooth"]):
                intensity = "medium"
            elif any(k in context_window for k in ["subtle", "gentle", "minimal", "delicate", "quiet"]):
                intensity = "subtle"

            # Fallbacks and reduced motion rules per motion type
            reduced_behavior: Literal["static", "instant", "native-scroll"] = "static"
            mobile_fallback: Literal["stack", "native-horizontal", "static"] = "stack"

            if motion_type == MotionType.HORIZONTAL_SCROLL:
                mobile_fallback = "native-horizontal"
                reduced_behavior = "native-scroll"
            elif motion_type == MotionType.TEXT_REVEAL:
                reduced_behavior = "instant"
                mobile_fallback = "static"
            elif motion_type == MotionType.PARALLAX:
                reduced_behavior = "static"
                mobile_fallback = "static"

            key = (motion_type, target_sec)
            if key not in seen_types:
                seen_types.add(key)
                found_specs.append(
                    MotionSpec(
                        type=motion_type,
                        target_section=target_sec,
                        intensity=intensity,
                        axis=default_axis,
                        trigger=default_trigger,
                        reduced_motion_behavior=reduced_behavior,
                        mobile_fallback=mobile_fallback,
                        implementation="native",
                    )
                )

    return found_specs


# ── XML Serialization & Deserialization ──────────────────────────────────────

def motion_spec_to_xml(spec: MotionSpec) -> str:
    """Serializes a single MotionSpec into XML."""
    impl_attr = f' implementation="{spec.implementation}"' if spec.implementation != "native" else ""
    return (
        f'  <motion type="{spec.type.value}" '
        f'section="{spec.target_section}" '
        f'intensity="{spec.intensity}"{impl_attr} />'
    )


def motion_plan_to_xml(specs: List[MotionSpec]) -> str:
    """Formats a list of MotionSpecs into a canonical <motion_plan> XML block."""
    if not specs:
        return "<motion_plan />"
    lines = ["<motion_plan>"]
    for s in specs:
        lines.append(motion_spec_to_xml(s))
    lines.append("</motion_plan>")
    return "\n".join(lines)


def xml_to_motion_plan(xml_str: str) -> List[MotionSpec]:
    """Parses a <motion_plan> XML block into a list of MotionSpec objects."""
    if not xml_str or "<motion" not in xml_str:
        return []

    # Clean enclosing content if part of larger XML
    match = re.search(r"<motion_plan>([\s\S]*?)</motion_plan>", xml_str, re.IGNORECASE)
    block = match.group(0) if match else xml_str

    specs: List[MotionSpec] = []
    # Use regex to be robust against malformed or partial tags
    tag_pattern = re.compile(
        r'<motion\s+([^>]+)/?>',
        re.IGNORECASE
    )
    attr_pattern = re.compile(r'(\w+)=["\']([^"\']*)["\']')

    for m in tag_pattern.finditer(block):
        attr_text = m.group(1)
        attrs = dict(attr_pattern.findall(attr_text))
        type_str = attrs.get("type", "scroll_reveal")
        section = attrs.get("section", "general")
        intensity = attrs.get("intensity", "subtle")

        try:
            m_type = MotionType(type_str)
        except ValueError:
            m_type = MotionType.SCROLL_REVEAL

        intensity_val: Literal["subtle", "medium", "cinematic"] = (
            intensity if intensity in ("subtle", "medium", "cinematic") else "subtle"
        )

        axis: Literal["x", "y", "both", "none"] = "x" if m_type == MotionType.HORIZONTAL_SCROLL else ("none" if m_type == MotionType.MICRO_INTERACTION else "y")
        trigger: Literal["viewport", "scroll-progress", "interaction"] = (
            "interaction" if m_type == MotionType.MICRO_INTERACTION
            else ("scroll-progress" if m_type in (MotionType.PARALLAX, MotionType.HORIZONTAL_SCROLL, MotionType.STICKY_STORY) else "viewport")
        )

        impl = attrs.get("implementation", "native")
        implementation_val: Literal["native", "gsap", "framer-motion"] = (
            impl if impl in ("native", "gsap", "framer-motion") else "native"
        )

        specs.append(
            MotionSpec(
                type=m_type,
                target_section=section,
                intensity=intensity_val,
                axis=axis,
                trigger=trigger,
                reduced_motion_behavior="instant" if m_type == MotionType.TEXT_REVEAL else "static",
                mobile_fallback="native-horizontal" if m_type == MotionType.HORIZONTAL_SCROLL else "stack",
                implementation=implementation_val,
            )
        )

    return specs


# ── Canonical Motion Implementation Guidelines (Section 5) ───────────────────

def get_motion_implementation_guidelines(spec: MotionSpec) -> str:
    """
    Returns strict, production-ready coding rules for implementing the specified MotionSpec.
    Ensures accessibility, zero unverified packages, and performance on local machines.
    """
    if spec.implementation == "gsap":
        return (
            f"/* Motion Guideline [{spec.target_section} - GSAP ScrollTrigger]: */\n"
            "- Dependency: 'gsap' confirmed in package.json.\n"
            "- Import GSAP: import { gsap } from 'gsap'; import { ScrollTrigger } from 'gsap/ScrollTrigger';\n"
            "- Register plugin: gsap.registerPlugin(ScrollTrigger);\n"
            "- Cleanup: Wrap in useEffect with gsap.context() and return ctx.revert() on unmount.\n"
            "- Accessibility: Honor @media (prefers-reduced-motion) via ScrollTrigger.matchMedia() or early return."
        )
    elif spec.implementation == "framer-motion":
        return (
            f"/* Motion Guideline [{spec.target_section} - Framer Motion]: */\n"
            "- Dependency: 'framer-motion' confirmed in package.json.\n"
            "- Import: import { motion, useReducedMotion } from 'framer-motion';\n"
            "- Accessibility: Check const shouldReduce = useReducedMotion() and disable animations if true.\n"
            "- Animate only transform/opacity to prevent layout shifts."
        )

    # Native Browser/CSS implementations (Section 5 & 6 Policy)
    policy_note = "\n- Motion Library Policy: Default to native browser/CSS primitives. Do NOT import 'gsap' or 'framer-motion' unless confirmed in dependencies."
    m_type = spec.type

    if m_type == MotionType.SCROLL_REVEAL:
        return (
            f"/* Motion Guideline [{spec.target_section} - Scroll Reveal]: */\n"
            "- Implement with native IntersectionObserver (threshold: 0.15, rootMargin: '0px 0px -40px 0px').\n"
            "- Animate only opacity and transform (translateY(20px) -> translateY(0)).\n"
            "- Disconnect or unobserve elements once revealed to prevent memory leaks.\n"
            "- Content must NEVER remain permanently invisible if JS fails: default opacity should be visible or fallback.\n"
            "- Mandatory @media (prefers-reduced-motion: reduce) { opacity: 1 !important; transform: none !important; transition: none !important; }"
            + policy_note
        )

    elif m_type == MotionType.PARALLAX:
        return (
            f"/* Motion Guideline [{spec.target_section} - Parallax]: */\n"
            "- Use passive scroll event listener with window.requestAnimationFrame.\n"
            "- Update CSS transform or CSS custom property (--parallax-y) directly on the element ref.\n"
            "- DO NOT call React setState() on every scroll tick.\n"
            "- Clamp max translation bounds (e.g. max ±60px) to prevent layout distortion.\n"
            "- Never call wheel.preventDefault() or touchmove.preventDefault().\n"
            "- Clean up listener and cancelAnimationFrame on component unmount.\n"
            "- Disable completely on mobile (<768px) and in @media (prefers-reduced-motion: reduce)."
            + policy_note
        )

    elif m_type == MotionType.HORIZONTAL_SCROLL:
        return (
            f"/* Motion Guideline [{spec.target_section} - Horizontal Scroll]: */\n"
            "- Desktop: Normal vertical document scroll pinned via sticky viewport (position: sticky; top: 0; height: 100vh; overflow: hidden).\n"
            "- Horizontal track translates horizontally (translate3d(-calc(...), 0, 0)) mapped to container scroll progress.\n"
            "- Never hijack wheel or touch events.\n"
            "- Mobile (<768px): Fallback to native overflow-x: auto with scroll-snap-type: x mandatory, or stack vertically.\n"
            "- Reduced motion: native scroll-snap or clean vertical stack."
            + policy_note
        )

    elif m_type == MotionType.STICKY_STORY:
        return (
            f"/* Motion Guideline [{spec.target_section} - Sticky Storytelling]: */\n"
            "- Use native CSS position: sticky; top: 2rem (or top: 80px under navbar).\n"
            "- Ensure no ancestor container has overflow: hidden, overflow: auto, or transform properties that break sticky context.\n"
            "- Maintain semantic DOM order suitable for screen-readers and keyboard navigation.\n"
            "- Two-column layout: left column sticky story graphic/card, right column scrolling narrative steps."
            + policy_note
        )

    elif m_type == MotionType.TEXT_REVEAL:
        return (
            f"/* Motion Guideline [{spec.target_section} - Text Reveal]: */\n"
            "- Provide single accessible heading label: <h1 aria-label=\"Full readable headline\">\n"
            "- Split decorative text into spans with aria-hidden=\"true\": <span aria-hidden=\"true\" className=\"word\">Word</span>\n"
            "- Stagger animation via CSS animation-delay or transition-delay.\n"
            "- Reduced motion fallback: instantly visible with animation: none !important; opacity: 1 !important."
            + policy_note
        )

    elif m_type == MotionType.MICRO_INTERACTION:
        return (
            f"/* Motion Guideline [{spec.target_section} - Micro-Interactions]: */\n"
            "- Parity between :hover and :focus-visible / :focus-within.\n"
            "- Interactive toggle controls must declare aria-pressed or aria-selected state.\n"
            "- Snappy durations (150ms - 220ms ease-out) modifying transform/box-shadow/colors.\n"
            "- No layout shifts (avoid changing width/height/margin on hover)."
            + policy_note
        )

    return ""


# ==============================================================================
# 2. Section 5: Motion Implementation Rules Verification Engine
# ==============================================================================

@dataclass
class MotionRulesValidationResult:
    is_valid: bool
    score: float
    passed_rules: List[str]
    violations: List[str]
    warnings: List[str]
    details: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "score": round(self.score, 3),
            "passed_rules": self.passed_rules,
            "violations": self.violations,
            "warnings": self.warnings,
            "details": self.details,
        }


def _hijacks_scroll(tsx_lower: str) -> bool:
    """A wheel/touchmove listener (or onWheel/onTouchMove handler) that calls
    preventDefault. A form submit's preventDefault next to the word "wheel" in
    copy is not hijacking (B9c)."""
    listener = re.search(r'addeventlistener\(\s*["\'](?:wheel|touchmove|mousewheel)["\']', tsx_lower) \
        or re.search(r'\bon(?:wheel|touchmove)\s*=', tsx_lower)
    return bool(listener and re.search(r'\.\s*preventdefault\s*\(\s*\)', tsx_lower))


def _clean_code_for_analysis(code: str) -> str:
    """Removes single-line, multi-line, and JSX comments to avoid false-positive detections."""
    code = re.sub(r'//[^\n]*', '', code)
    code = re.sub(r'/\*[\s\S]*?\*/', '', code)
    code = re.sub(r'\{\s*/\*[\s\S]*?\*/\s*\}', '', code)
    return code


def validate_motion_rules(
    files: Dict[str, str],
    motion_specs: Optional[List[MotionSpec]] = None,
    package_json: Optional[Union[Dict[str, Any], str, Path]] = None,
    workspace_dir: Optional[Path] = None,
) -> MotionRulesValidationResult:
    """
    Authoritative validator enforcing Section 5 (Motion Implementation Rules)
    and Section 6 (Motion Library Policy):
    Rule 1: Scroll reveal (IntersectionObserver, opacity/transform, disconnect/unobserve, reduced-motion)
    Rule 2: Parallax (passive listener, RAF, no setState per tick, no wheel.preventDefault, mobile/reduced-motion disable)
    Rule 3: Horizontal scroll (normal vertical scroll -> sticky viewport -> translate3d track, mobile scroll-snap/stack, no event hijacking)
    Rule 4: Sticky storytelling (position: sticky, no ancestor overflow conflict, semantic DOM order)
    Rule 5: Text reveal (accessible h1 aria-label, decorative aria-hidden spans, reduced motion instant visibility)
    Rule 6: Micro-interactions (:hover + :focus-visible parity, aria-pressed/aria-selected, 120–250 ms durations, zero layout shift)
    Rule 7: Motion library policy (default to native; only use GSAP/Framer Motion if verified in package.json/node_modules)
    """
    passed_rules: List[str] = []
    violations: List[str] = []
    warnings: List[str] = []
    details: Dict[str, Any] = {}

    all_tsx = "\n".join(v for k, v in files.items() if k.endswith((".tsx", ".jsx", ".ts", ".js")))
    all_css = "\n".join(v for k, v in files.items() if k.endswith(".css"))
    clean_tsx = _clean_code_for_analysis(all_tsx)
    clean_css = _clean_code_for_analysis(all_css)
    tsx_lower = clean_tsx.lower()
    css_lower = clean_css.lower()

    # Determine which motion types to evaluate
    active_types: Set[MotionType] = set()
    eval_all = motion_specs is None
    if motion_specs:
        for spec in motion_specs:
            if isinstance(spec, MotionType):
                active_types.add(spec)
            elif isinstance(spec, str):
                try:
                    active_types.add(MotionType(spec))
                except ValueError:
                    pass
            elif hasattr(spec, "type"):
                t = spec.type
                if isinstance(t, MotionType):
                    active_types.add(t)
                elif isinstance(t, str):
                    try:
                        active_types.add(MotionType(t))
                    except ValueError:
                        pass
            elif isinstance(spec, dict) and "type" in spec:
                try:
                    active_types.add(MotionType(spec["type"]))
                except ValueError:
                    pass
    else:
        # Detect active motion signals in code
        if "intersectionobserver" in tsx_lower:
            active_types.add(MotionType.SCROLL_REVEAL)
        if (
            ("requestanimationframe" in tsx_lower and "scroll" in tsx_lower)
            or re.search(r'data-motion=["\'][^"\']*parallax', tsx_lower)
            or _hijacks_scroll(tsx_lower)
        ):
            active_types.add(MotionType.PARALLAX)
        if (re.search(r'data-motion=["\'][^"\']*horizontal', tsx_lower)
                or re.search(r'scroll-snap-type\s*:\s*x\b', css_lower)
                or _hijacks_scroll(tsx_lower)):
            active_types.add(MotionType.HORIZONTAL_SCROLL)
        if re.search(r'position\s*:\s*sticky', css_lower):
            active_types.add(MotionType.STICKY_STORY)
        if re.search(r'<h[1-6][^>]*>[\s\S]*?aria-hidden[\s\S]*?</h[1-6]>', tsx_lower) or "text-reveal" in tsx_lower:
            active_types.add(MotionType.TEXT_REVEAL)
        if ":hover" in css_lower:
            active_types.add(MotionType.MICRO_INTERACTION)

    # ── Rule 1: Scroll Reveal ────────────────────────────────────────────────
    r1_pass = True
    r1_violations = []
    r1_warnings = []
    has_observer = "intersectionobserver" in tsx_lower
    if MotionType.SCROLL_REVEAL in active_types or (eval_all and has_observer):
        if has_observer:
            # Check cleanup
            has_cleanup = ("unobserve" in tsx_lower) or ("disconnect" in tsx_lower)
            if not has_cleanup:
                r1_violations.append("Scroll reveal uses IntersectionObserver but omits observer.unobserve() or disconnect() cleanup.")
                r1_pass = False

            # Check for hardware accelerated properties (opacity/transform)
            has_transform_opacity = ("opacity" in css_lower or "transform" in css_lower or "translate" in css_lower)
            if not has_transform_opacity:
                r1_warnings.append("Scroll reveal should animate opacity or transform for smooth hardware acceleration.")

            # Check reduced-motion fallback
            if "prefers-reduced-motion" not in css_lower:
                r1_violations.append("Scroll reveal missing mandatory @media (prefers-reduced-motion: reduce) fallback.")
                r1_pass = False

            # Check permanently hidden content hazard
            if re.search(r'opacity\s*:\s*0\s*;', clean_css) and "is-visible" not in clean_css and "active" not in clean_css and "reveal" not in clean_css:
                r1_warnings.append("Element has opacity: 0 without clear reveal trigger class.")

            if r1_pass:
                passed_rules.append("Rule 1: Scroll reveal satisfies IntersectionObserver, cleanup, and reduced-motion contract.")
        else:
            r1_violations.append("Scroll reveal requested but native IntersectionObserver not detected in components.")
            r1_pass = False

        details["rule_1_scroll_reveal"] = {"passed": r1_pass, "violations": r1_violations, "warnings": r1_warnings}
        violations.extend(r1_violations)
        warnings.extend(r1_warnings)

    # ── Rule 2: Parallax ─────────────────────────────────────────────────────
    r2_pass = True
    r2_violations = []
    r2_warnings = []
    has_parallax = (
        bool(re.search(r'data-motion=["\'][^"\']*parallax', tsx_lower))
        or ("scroll" in tsx_lower and "requestanimationframe" in tsx_lower)
        or _hijacks_scroll(tsx_lower)
    )
    if MotionType.PARALLAX in active_types or (eval_all and has_parallax):
        if "prefers-reduced-motion" not in css_lower:
            r2_violations.append("Parallax missing mandatory prefers-reduced-motion fallback.")
            r2_pass = False
        # Strict forbidden event hijacking check
        if _hijacks_scroll(tsx_lower):
            r2_violations.append("Forbidden event hijacking: never use wheel.preventDefault() or touchmove.preventDefault() for parallax.")
            r2_pass = False

        # Passive listener check
        if "addeventlistener" in tsx_lower and "scroll" in tsx_lower:
            if "passive" not in tsx_lower:
                r2_warnings.append("Scroll listener for parallax should specify { passive: true } to avoid scroll-thread blocking.")

        # Cleanup check
        if "addeventlistener" in tsx_lower and "removeeventlistener" not in tsx_lower:
            r2_violations.append("Parallax scroll listener missing removeEventListener cleanup in useEffect return.")
            r2_pass = False

        if "requestanimationframe" in tsx_lower and "cancelanimationframe" not in tsx_lower:
            r2_warnings.append("Parallax RAF loop should clean up with cancelAnimationFrame on unmount.")

        # Check for unthrottled setState in scroll tick
        if re.search(r'window\s*\.\s*addeventlistener\s*\(\s*["\']scroll["\']\s*,\s*\([^)]*\)\s*=>\s*\{[^}]*set[a-z0-9_]+\(', tsx_lower):
            r2_warnings.append("Avoid calling React setState() directly inside every raw scroll tick; use refs or RAF.")

        # Mobile and reduced-motion fallback check
        if "prefers-reduced-motion" not in css_lower:
            r2_warnings.append("Parallax should be disabled or clamped in @media (prefers-reduced-motion: reduce).")

        if r2_pass and not r2_violations:
            passed_rules.append("Rule 2: Parallax satisfies passive listener, cleanup, and non-hijacking contract.")

    details["rule_2_parallax"] = {"passed": r2_pass, "violations": r2_violations, "warnings": r2_warnings}
    violations.extend(r2_violations)
    warnings.extend(r2_warnings)

    # ── Rule 3: Horizontal Scroll ────────────────────────────────────────────
    r3_pass = True
    r3_violations = []
    r3_warnings = []
    has_horizontal = bool(re.search(r'data-motion=["\'][^"\']*horizontal', tsx_lower)) or ("translate3d" in css_lower and "100vh" in css_lower)
    if MotionType.HORIZONTAL_SCROLL in active_types or (eval_all and has_horizontal):
        # Check no wheel or touch hijacking
        if _hijacks_scroll(tsx_lower):
            r3_violations.append("Horizontal scroll must not hijack native wheel or touch events.")
            r3_pass = False

        # Check sticky viewport structure
        has_sticky = "sticky" in css_lower or "sticky" in tsx_lower
        if not has_sticky and not ("overflow-x" in css_lower):
            r3_warnings.append("Horizontal scroll should use a sticky viewport container on desktop.")

        # Check mobile fallback (scroll-snap or stack)
        has_snap_or_stack = ("scroll-snap" in css_lower) or ("overflow-x" in css_lower) or ("flex-direction: column" in css_lower) or ("grid-template-columns: 1fr" in css_lower)
        if not has_snap_or_stack and "@media" in css_lower:
            r3_warnings.append("Horizontal scroll should provide native scroll-snap or vertical stack on mobile (<768px).")

        if r3_pass:
            passed_rules.append("Rule 3: Horizontal scroll satisfies natural scroll mapping and mobile fallback contract.")

        details["rule_3_horizontal_scroll"] = {"passed": r3_pass, "violations": r3_violations, "warnings": r3_warnings}
        violations.extend(r3_violations)
        warnings.extend(r3_warnings)

    # ── Rule 4: Sticky Storytelling ──────────────────────────────────────────
    r4_pass = True
    r4_violations = []
    r4_warnings = []
    has_sticky = "position: sticky" in css_lower or "position:sticky" in css_lower
    if MotionType.STICKY_STORY in active_types or (eval_all and has_sticky):
        if not has_sticky:
            r4_violations.append("Sticky storytelling requires CSS position: sticky.")
            r4_pass = False

        # Check ancestor overflow conflict
        if re.search(r'\.[a-z0-9_-]*(?:container|wrapper|layout|app|root|page|main|body)[a-z0-9_-]*\s*\{[^}]*overflow\s*:\s*hidden', css_lower):
            r4_warnings.append("Ancestor container defines overflow: hidden, which may break child position: sticky.")

        # Check semantic DOM tags
        has_semantic_dom = any(tag in tsx_lower for tag in ["<section", "<article", "<aside", "<h2", "<h3"])
        if not has_semantic_dom:
            r4_warnings.append("Sticky storytelling should use semantic DOM elements (<section>, <article>, <h2>) for screen-reader order.")

        if r4_pass:
            passed_rules.append("Rule 4: Sticky storytelling satisfies CSS sticky positioning and semantic DOM contract.")

        details["rule_4_sticky_story"] = {"passed": r4_pass, "violations": r4_violations, "warnings": r4_warnings}
        violations.extend(r4_violations)
        warnings.extend(r4_warnings)

    # ── Rule 5: Text Reveal ──────────────────────────────────────────────────
    r5_pass = True
    r5_violations = []
    r5_warnings = []
    has_split_heading = bool(re.search(r'<h[1-6][^>]*>[\s\S]*?aria-hidden[\s\S]*?</h[1-6]>', tsx_lower))
    has_text_reveal = (
        ("text-reveal" in tsx_lower or "word-reveal" in tsx_lower or "animated-text" in tsx_lower)
        or has_split_heading
    )
    if MotionType.TEXT_REVEAL in active_types or (eval_all and has_text_reveal):
        # Check accessible label if decorative spans are used in heading
        if has_split_heading or 'aria-hidden="true"' in tsx_lower:
            has_accessible_label = "aria-label=" in tsx_lower
            if not has_accessible_label:
                r5_violations.append("Text reveal splits words/letters into decorative spans but parent heading is missing accessible aria-label.")
                r5_pass = False

        # Check reduced-motion immediate visibility
        if "prefers-reduced-motion" in css_lower:
            if not any(k in css_lower for k in ["animation: none", "animation:none", "opacity: 1", "opacity:1"]):
                r5_warnings.append("Text reveal should ensure instant visibility in @media (prefers-reduced-motion: reduce).")
        else:
            r5_warnings.append("Text reveal missing @media (prefers-reduced-motion: reduce) instant display fallback.")

        if r5_pass:
            passed_rules.append("Rule 5: Text reveal satisfies accessible aria-label and reduced-motion fallback contract.")

        details["rule_5_text_reveal"] = {"passed": r5_pass, "violations": r5_violations, "warnings": r5_warnings}
        violations.extend(r5_violations)
        warnings.extend(r5_warnings)

    # ── Rule 6: Micro-Interactions ───────────────────────────────────────────
    r6_pass = True
    r6_violations = []
    r6_warnings = []
    has_hover = ":hover" in css_lower
    if MotionType.MICRO_INTERACTION in active_types or (eval_all and has_hover):
        # Check parity with focus-visible / focus-within
        has_focus_parity = (":focus-visible" in css_lower) or (":focus-within" in css_lower) or (":focus" in css_lower)
        if not has_focus_parity:
            r6_warnings.append("Interactive elements declare :hover but lack :focus-visible / :focus parity for keyboard accessibility.")

        # Check for layout-shifting properties on hover
        hover_blocks = re.findall(r':hover\s*\{([^}]+)\}', all_css, re.IGNORECASE)
        for hb in hover_blocks:
            hb_low = hb.lower()
            if any(k in hb_low for k in ["width:", "height:", "margin:", "padding:"]):
                r6_warnings.append("Micro-interaction modifies layout dimensions (width/height/margin) on :hover; prefer transform / opacity.")
                break

        # Check transition duration
        durations = re.findall(r'transition(?:-duration)?\s*:[^;]*?(\d+(?:\.\d+)?)\s*(ms|s)', css_lower)
        for val_str, unit in durations:
            ms_val = float(val_str) * (1000 if unit == "s" else 1)
            if ms_val > 400:
                r6_warnings.append(f"Micro-interaction transition duration ({int(ms_val)}ms) exceeds recommended 120–250ms range.")
                break

        # Check interactive toggle controls have aria state
        if "<button" in tsx_lower and any(k in tsx_lower for k in ["toggle", "isopen", "active", "expanded"]):
            has_aria_state = ("aria-pressed" in tsx_lower) or ("aria-expanded" in tsx_lower) or ("aria-selected" in tsx_lower)
            if not has_aria_state:
                r6_warnings.append("Interactive toggle buttons should declare aria-pressed or aria-expanded state.")

        if r6_pass:
            passed_rules.append("Rule 6: Micro-interactions satisfy accessibility parity, timing, and layout stability contract.")

    details["rule_6_micro_interactions"] = {"passed": r6_pass, "violations": r6_violations, "warnings": r6_warnings}
    violations.extend(r6_violations)
    warnings.extend(r6_warnings)

    # ── Rule 7: Section 6 Motion Library Policy ──────────────────────────────
    policy_ok, policy_violations, policy_details = validate_motion_library_policy(
        files=files, package_json=package_json, workspace_dir=workspace_dir
    )
    details["rule_7_library_policy"] = {
        "passed": policy_ok,
        "violations": policy_violations,
        "details": policy_details,
    }
    violations.extend(policy_violations)
    if policy_ok:
        if policy_details.get("verified_libraries"):
            passed_rules.append(
                f"Rule 7: Motion Library Policy verified external dependencies: {', '.join(policy_details['verified_libraries'])}."
            )
        else:
            passed_rules.append("Rule 7: Motion Library Policy satisfied (compliant native browser/CSS implementations).")

    # ── Aggregate Compliance Score ───────────────────────────────────────────
    total_evaluated = max(1, len(details))
    rules_passed_count = sum(1 for v in details.values() if v.get("passed", True) and not v.get("violations"))
    base_score = rules_passed_count / total_evaluated

    # Deductions
    violation_deduction = len(violations) * 0.15
    warning_deduction = len(warnings) * 0.03
    final_score = max(0.0, min(1.0, base_score - violation_deduction - warning_deduction))

    is_valid = len(violations) == 0

    return MotionRulesValidationResult(
        is_valid=is_valid,
        score=final_score,
        passed_rules=passed_rules,
        violations=violations,
        warnings=warnings,
        details=details,
    )


# ==============================================================================
# 3. Canonical Section 5 React + CSS Snippet Generators
# ==============================================================================

def generate_scroll_reveal_snippet(section_name: str = "Features") -> Tuple[str, str]:
    """Generates a canonical Scroll Reveal component conforming to Rule 1."""
    pascal = section_name.replace(" ", "").capitalize()
    tsx = f"""import React, {{ useEffect, useRef }} from 'react';
import './{pascal}.css';

export function {pascal}() {{
  const sectionRef = useRef<HTMLElement | null>(null);

  useEffect(() => {{
    const target = sectionRef.current;
    if (!target) return;

    const observer = new IntersectionObserver(
      (entries) => {{
        entries.forEach((entry) => {{
          if (entry.isIntersecting) {{
            entry.target.classList.add('is-visible');
            observer.unobserve(entry.target); // Rule 1: unobserve once revealed
          }}
        }});
      }},
      {{ threshold: 0.15, rootMargin: '0px 0px -40px 0px' }}
    );

    const cards = target.querySelectorAll('.reveal-card');
    cards.forEach((el) => observer.observe(el));

    return () => observer.disconnect(); // Rule 1: cleanup
  }}, []);

  return (
    <section ref={{sectionRef}} className="{section_name.lower()}-section" id="{section_name.lower()}">
      <div className="section-container">
        <h2 className="section-title">Capabilities</h2>
        <div className="card-grid">
          <div className="reveal-card">
            <h3>High Performance</h3>
            <p>Accelerated execution with zero latency overhead.</p>
          </div>
          <div className="reveal-card">
            <h3>Autonomous Safety</h3>
            <p>Fail-closed guarantees on every build turn.</p>
          </div>
        </div>
      </div>
    </section>
  );
}}
"""
    css = f""".{section_name.lower()}-section {{
  padding: 5rem 2rem;
  background: var(--surface-bg, #0b0f19);
  color: var(--text-primary, #ffffff);
}}

.section-container {{
  max-width: 1200px;
  margin: 0 auto;
}}

.card-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1.5rem;
  margin-top: 2rem;
}}

.reveal-card {{
  padding: 2rem;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  opacity: 0;
  transform: translateY(24px);
  transition: opacity 0.6s cubic-bezier(0.16, 1, 0.3, 1), transform 0.6s cubic-bezier(0.16, 1, 0.3, 1);
}}

.reveal-card.is-visible {{
  opacity: 1;
  transform: translateY(0);
}}

/* Rule 1: Mandatory prefers-reduced-motion fallback */
@media (prefers-reduced-motion: reduce) {{
  .reveal-card,
  .reveal-card.is-visible {{
    opacity: 1 !important;
    transform: none !important;
    transition: none !important;
  }}
}}
"""
    return tsx, css


def generate_parallax_snippet(section_name: str = "Hero") -> Tuple[str, str]:
    """Generates a canonical Parallax component conforming to Rule 2."""
    pascal = section_name.replace(" ", "").capitalize()
    tsx = f"""import React, {{ useEffect, useRef }} from 'react';
import './{pascal}.css';

export function {pascal}() {{
  const bgRef = useRef<HTMLDivElement | null>(null);
  const rafRef = useRef<number | null>(null);

  useEffect(() => {{
    const el = bgRef.current;
    if (!el) return;

    // Check prefers-reduced-motion
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    if (mediaQuery.matches) return;

    const handleScroll = () => {{
      if (rafRef.current) return;
      rafRef.current = window.requestAnimationFrame(() => {{
        const scrollY = window.scrollY;
        // Bounded translation clamp to avoid distortion
        const translation = Math.max(-60, Math.min(60, scrollY * 0.15));
        el.style.transform = "translate3d(0, " + translation + "px, 0)";
        rafRef.current = null;
      }});
    }};

    // Rule 2: Passive scroll listener, zero wheel.preventDefault()
    window.addEventListener('scroll', handleScroll, {{ passive: true }});

    return () => {{
      window.removeEventListener('scroll', handleScroll);
      if (rafRef.current) window.cancelAnimationFrame(rafRef.current);
    }};
  }}, []);

  return (
    <section className="parallax-hero" id="hero">
      <div ref={{bgRef}} className="parallax-bg" aria-hidden="true" />
      <div className="hero-content">
        <h1 className="hero-title">Next Generation Architecture</h1>
        <p className="hero-subtitle">Engineered for seamless fidelity and performance.</p>
      </div>
    </section>
  );
}}
"""
    css = """.parallax-hero {
  position: relative;
  min-height: 80vh;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  background: #0b0f19;
  color: #ffffff;
}

.parallax-bg {
  position: absolute;
  top: -10%;
  left: 0;
  width: 100%;
  height: 120%;
  background: radial-gradient(circle at 50% 50%, rgba(99, 102, 241, 0.15), transparent 70%);
  pointer-events: none;
  will-change: transform;
}

.hero-content {
  position: relative;
  z-index: 2;
  text-align: center;
  padding: 2rem;
}

/* Rule 2: Disable on mobile and reduced-motion */
@media (max-width: 768px), (prefers-reduced-motion: reduce) {
  .parallax-bg {
    transform: none !important;
    will-change: auto;
  }
}
"""
    return tsx, css


def generate_text_reveal_snippet(section_name: str = "Hero") -> Tuple[str, str]:
    """Generates a canonical Text Reveal component conforming to Rule 5."""
    pascal = section_name.replace(" ", "").capitalize()
    tsx = f"""import React from 'react';
import './{pascal}.css';

export function {pascal}() {{
  const words = ['Architectural', 'Precision', 'Engineered', 'for', 'Scale'];

  return (
    <section className="text-reveal-section">
      {{/* Rule 5: Single accessible heading label with decorative aria-hidden spans */}}
      <h1 className="text-reveal-heading" aria-label="Architectural Precision Engineered for Scale">
        {{words.map((word, idx) => (
          <span
            key={{idx}}
            aria-hidden="true"
            className="reveal-word"
            style={{{{ animationDelay: (idx * 80) + "ms" }}}}
          >
            {{word}}&nbsp;
          </span>
        ))}}
      </h1>
    </section>
  );
}}
"""
    css = """.text-reveal-section {
  padding: 6rem 2rem;
  background: #0b0f19;
  display: flex;
  justify-content: center;
}

.text-reveal-heading {
  font-family: var(--font-heading, sans-serif);
  font-size: clamp(2.5rem, 5vw, 4rem);
  font-weight: 700;
  color: #ffffff;
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
}

.reveal-word {
  display: inline-block;
  opacity: 0;
  transform: translateY(16px);
  animation: revealWord 0.5s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

@keyframes revealWord {
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Rule 5: Immediate display on reduced motion */
@media (prefers-reduced-motion: reduce) {
  .reveal-word {
    animation: none !important;
    opacity: 1 !important;
    transform: none !important;
  }
}
"""
    return tsx, css


def generate_horizontal_scroll_snippet(section_name: str = "Showcase") -> Tuple[str, str]:
    """Generates a canonical Horizontal Scroll component conforming to Rule 3."""
    pascal = section_name.replace(" ", "").capitalize()
    tsx = f"""import React, {{ useEffect, useRef }} from 'react';
import './{pascal}.css';

export function {pascal}() {{
  const containerRef = useRef<HTMLDivElement | null>(null);
  const trackRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {{
    const container = containerRef.current;
    const track = trackRef.current;
    if (!container || !track) return;

    const handleScroll = () => {{
      const rect = container.getBoundingClientRect();
      const totalScroll = container.offsetHeight - window.innerHeight;
      if (totalScroll <= 0) return;

      const progress = Math.max(0, Math.min(1, -rect.top / totalScroll));
      const maxTranslate = track.scrollWidth - window.innerWidth;
      track.style.transform = "translate3d(-" + (progress * maxTranslate) + "px, 0, 0)";
    }};

    // Rule 3: Normal vertical document scroll, zero wheel or touch hijacking
    window.addEventListener('scroll', handleScroll, {{ passive: true }});
    return () => window.removeEventListener('scroll', handleScroll);
  }}, []);

  return (
    <section ref={{containerRef}} className="horizontal-section" id="showcase">
      <div className="sticky-viewport">
        <div ref={{trackRef}} className="horizontal-track">
          <div className="horizontal-card">
            <h3>Milestone 01</h3>
            <p>Unified design token specification with dark-mode first contrast.</p>
          </div>
          <div className="horizontal-card">
            <h3>Milestone 02</h3>
            <p>Deterministic layout archetype balancing and diversity guards.</p>
          </div>
          <div className="horizontal-card">
            <h3>Milestone 03</h3>
            <p>Hardware-accelerated native motion architecture across 6 patterns.</p>
          </div>
        </div>
      </div>
    </section>
  );
}}
"""
    css = """.horizontal-section {
  position: relative;
  height: 300vh;
  background: #0b0f19;
  color: #ffffff;
}

/* Rule 3: Desktop sticky viewport */
.sticky-viewport {
  position: sticky;
  top: 0;
  height: 100vh;
  width: 100%;
  overflow: hidden;
  display: flex;
  align-items: center;
}

.horizontal-track {
  display: flex;
  gap: 2rem;
  padding: 0 4rem;
  will-change: transform;
}

.horizontal-card {
  flex: 0 0 380px;
  padding: 2.5rem;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
}

/* Rule 3: Mobile fallback with native scroll-snap */
@media (max-width: 768px) {
  .horizontal-section {
    height: auto;
  }
  .sticky-viewport {
    position: static;
    height: auto;
    overflow-x: auto;
    scroll-snap-type: x mandatory;
    -webkit-overflow-scrolling: touch;
    padding: 2rem 0;
  }
  .horizontal-track {
    transform: none !important;
    padding: 0 1.5rem;
  }
  .horizontal-card {
    scroll-snap-align: start;
    flex: 0 0 85vw;
  }
}
"""
    return tsx, css


def generate_sticky_story_snippet(section_name: str = "Story") -> Tuple[str, str]:
    """Generates a canonical Sticky Storytelling component conforming to Rule 4."""
    pascal = section_name.replace(" ", "").capitalize()
    tsx = f"""import React from 'react';
import './{pascal}.css';

export function {pascal}() {{
  return (
    <section className="sticky-story-section" id="story">
      <div className="story-container">
        {{/* Rule 4: Sticky column with position: sticky */}}
        <aside className="story-sticky-aside">
          <span className="story-tag">Narrative Sequence</span>
          <h2 className="story-heading">End-to-End Autonomous Platform</h2>
          <p className="story-desc">
            A continuous execution cycle maintaining strict quality contracts.
          </p>
        </aside>

        {{/* Scrolling narrative steps */}}
        <div className="story-steps">
          <article className="story-card">
            <h3>Phase 1: Foundation Verification</h3>
            <p>Fail-closed fingerprint check halts unauthorized execution early.</p>
          </article>
          <article className="story-card">
            <h3>Phase 2: Archetype Synthesis</h3>
            <p>Balanced composition across 7 distinct visual hero archetypes.</p>
          </article>
          <article className="story-card">
            <h3>Phase 3: Motion Engine</h3>
            <p>Hardware-accelerated native animations with zero external baggage.</p>
          </article>
        </div>
      </div>
    </section>
  );
}}
"""
    css = """.sticky-story-section {
  padding: 6rem 2rem;
  background: #0b0f19;
  color: #ffffff;
}

.story-container {
  max-width: 1200px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 1fr 1.5fr;
  gap: 4rem;
  align-items: start;
}

/* Rule 4: Native position: sticky without overflow: hidden ancestors */
.story-sticky-aside {
  position: sticky;
  top: 6rem;
  padding-right: 2rem;
}

.story-tag {
  display: inline-block;
  font-family: var(--font-mono, monospace);
  font-size: 0.8rem;
  color: #818cf8;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-bottom: 1rem;
}

.story-heading {
  font-family: var(--font-heading, sans-serif);
  font-size: 2.25rem;
  font-weight: 700;
  line-height: 1.25;
  margin-bottom: 1rem;
}

.story-desc {
  font-size: 1rem;
  color: #94a3b8;
  line-height: 1.6;
}

.story-steps {
  display: flex;
  flex-direction: column;
  gap: 3rem;
}

.story-card {
  padding: 2.5rem;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 14px;
}

.story-card h3 {
  font-size: 1.35rem;
  font-weight: 600;
  margin-bottom: 0.75rem;
}

.story-card p {
  color: #cbd5e1;
  line-height: 1.6;
}

@media (max-width: 768px) {
  .story-container {
    grid-template-columns: 1fr;
    gap: 2.5rem;
  }
  .story-sticky-aside {
    position: static;
    padding-right: 0;
  }
}
"""
    return tsx, css


def generate_micro_interaction_snippet(section_name: str = "Pricing") -> Tuple[str, str]:
    """Generates a canonical Micro-Interactions component conforming to Rule 6."""
    pascal = section_name.replace(" ", "").capitalize()
    tsx = f"""import React, {{ useState }} from 'react';
import './{pascal}.css';

export function {pascal}() {{
  const [isAnnual, setIsAnnual] = useState(false);

  return (
    <section className="pricing-section" id="pricing">
      <div className="pricing-container">
        <h2>Transparent Scalable Plans</h2>
        
        {{/* Rule 6: Interactive toggle with aria-pressed state */}}
        <div className="billing-toggle">
          <span>Monthly</span>
          <button
            type="button"
            className={{isAnnual ? "toggle-btn active" : "toggle-btn"}}
            aria-pressed={{isAnnual}}
            onClick={{() => setIsAnnual(!isAnnual)}}
          >
            <span className="toggle-slider" />
          </button>
          <span>Annual (20% Off)</span>
        </div>

        <div className="pricing-grid">
          <div className="pricing-card">
            <h3>Pro</h3>
            <div className="price-tag">
              <span className="amount">{{isAnnual ? '$39' : '$49'}}</span>
              <span className="period">/mo</span>
            </div>
            {{/* Rule 6: Hover & focus-visible parity on action buttons */}}
            <button type="button" className="pricing-btn">
              Get Started
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}}
"""
    css = """.pricing-section {
  padding: 5rem 2rem;
  background: #0b0f19;
  color: #ffffff;
  text-align: center;
}

.pricing-container {
  max-width: 1000px;
  margin: 0 auto;
}

.billing-toggle {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  margin: 2rem 0;
}

.toggle-btn {
  width: 52px;
  height: 28px;
  border-radius: 9999px;
  background: #334155;
  border: none;
  cursor: pointer;
  position: relative;
  /* Rule 6: Short duration (180ms) without layout shift */
  transition: background-color 180ms ease-out;
}

.toggle-btn:focus-visible {
  outline: 2px solid #818cf8;
  outline-offset: 2px;
}

.toggle-slider {
  position: absolute;
  top: 3px;
  left: 3px;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: #ffffff;
  transition: transform 180ms cubic-bezier(0.16, 1, 0.3, 1);
}

.toggle-btn.active {
  background: #6366f1;
}

.toggle-btn.active .toggle-slider {
  transform: translateX(24px);
}

.pricing-grid {
  display: flex;
  justify-content: center;
  margin-top: 2rem;
}

.pricing-card {
  padding: 2.5rem;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  width: 320px;
  /* Rule 6: Smooth hardware-accelerated lift, no layout shift */
  transition: transform 200ms ease-out, border-color 200ms ease-out, box-shadow 200ms ease-out;
}

/* Rule 6: Parity between :hover and :focus-within */
.pricing-card:hover,
.pricing-card:focus-within {
  transform: translateY(-4px);
  border-color: rgba(99, 102, 241, 0.4);
  box-shadow: 0 12px 28px rgba(0, 0, 0, 0.35);
}

.pricing-btn {
  width: 100%;
  padding: 0.75rem 1.5rem;
  border-radius: 8px;
  background: #6366f1;
  color: #ffffff;
  border: none;
  font-weight: 600;
  cursor: pointer;
  margin-top: 1.5rem;
  transition: background-color 180ms ease-out, transform 180ms ease-out;
}

/* Rule 6: Parity between :hover and :focus-visible */
.pricing-btn:hover,
.pricing-btn:focus-visible {
  background: #4f46e5;
  transform: translateY(-1px);
  outline: 2px solid #818cf8;
  outline-offset: 2px;
}
"""
    return tsx, css


# ==============================================================================
# 4. Section 6: Motion Library Policy & Dependency Guards
# ==============================================================================

EXTERNAL_MOTION_LIBRARIES: Dict[str, Dict[str, Any]] = {
    "gsap": {
        "packages": ["gsap", "@types/gsap"],
        "import_regex": re.compile(r'(?:import|from)\s+["\'](?:gsap|gsap/[^"\']+)["\']'),
        "canonical_version": "^3.12.5",
    },
    "framer-motion": {
        "packages": ["framer-motion"],
        "import_regex": re.compile(r'(?:import|from)\s+["\'](?:framer-motion|framer-motion/[^"\']+)["\']'),
        "canonical_version": "^11.0.0",
    },
    "lenis": {
        "packages": ["@studio-freight/lenis", "lenis"],
        "import_regex": re.compile(r'(?:import|from)\s+["\'](?:@studio-freight/lenis|lenis)(?:/[^"\']*)?["\']'),
        "canonical_version": "^1.0.42",
    },
}


def inspect_motion_library_imports(files: Dict[str, str]) -> Dict[str, List[str]]:
    """
    Scans files for external motion library imports (e.g. gsap, framer-motion, lenis).
    Returns mapping of library_key -> list of relative file paths.
    """
    detected: Dict[str, List[str]] = {}
    for path, content in files.items():
        if not path.endswith((".tsx", ".ts", ".jsx", ".js")):
            continue
        clean_content = _clean_code_for_analysis(content)
        for lib_key, lib_info in EXTERNAL_MOTION_LIBRARIES.items():
            if lib_info["import_regex"].search(clean_content):
                detected.setdefault(lib_key, []).append(path)
    return detected


def verify_motion_library_dependency(
    library_key: str,
    package_json: Optional[Union[Dict[str, Any], str, Path]] = None,
    workspace_dir: Optional[Path] = None,
) -> bool:
    """
    Verifies that an external motion library is confirmed in package.json or node_modules.
    Returns True if confirmed, False otherwise.
    """
    spec = EXTERNAL_MOTION_LIBRARIES.get(library_key.lower())
    if not spec:
        return False
    target_pkgs = set(spec["packages"])

    # 1. Check workspace node_modules if path provided
    if workspace_dir:
        nm_dir = Path(workspace_dir) / "node_modules"
        for pkg in target_pkgs:
            if (nm_dir / pkg).exists():
                return True

    # 2. Check package_json data
    pkg_data: Dict[str, Any] = {}
    if isinstance(package_json, dict):
        pkg_data = package_json
    elif isinstance(package_json, (str, Path)):
        p = Path(package_json)
        if p.is_file():
            try:
                pkg_data = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                pkg_data = {}
        elif isinstance(package_json, str) and "{" in package_json:
            try:
                pkg_data = json.loads(package_json)
            except Exception:
                pkg_data = {}

    deps = set(pkg_data.get("dependencies", {}).keys()) | set(pkg_data.get("devDependencies", {}).keys())
    return any(pkg in deps for pkg in target_pkgs)


def validate_motion_library_policy(
    files: Dict[str, str],
    package_json: Optional[Union[Dict[str, Any], str, Path]] = None,
    workspace_dir: Optional[Path] = None,
) -> Tuple[bool, List[str], Dict[str, Any]]:
    """
    Enforces Section 6: Motion Library Policy:
    - Default to native browser/CSS implementations because the project runs on local constrained hardware and must not hallucinate packages.
    - Only use GSAP/ScrollTrigger or Framer Motion when:
      1. dependency inspection confirms the package, or
      2. the dependency manager successfully installs it.
    - Never train trajectories that silently import an unverified package.
    """
    if package_json is None and "package.json" in files:
        package_json = files["package.json"]
    elif package_json is None and workspace_dir:
        pj_path = Path(workspace_dir) / "package.json"
        if pj_path.is_file():
            package_json = pj_path

    detected_imports = inspect_motion_library_imports(files)
    violations: List[str] = []
    verified_libraries: List[str] = []

    for lib_key, import_files in detected_imports.items():
        is_verified = verify_motion_library_dependency(
            library_key=lib_key,
            package_json=package_json,
            workspace_dir=workspace_dir,
        )
        if not is_verified:
            file_list = ", ".join(import_files[:3])
            violations.append(
                f"Motion Library Policy violation: unverified external package '{lib_key}' imported in {file_list}. "
                "Section 6 mandates defaulting to native browser/CSS implementations unless dependency inspection confirms the package or it is successfully installed."
            )
        else:
            verified_libraries.append(lib_key)

    is_valid = len(violations) == 0
    details = {
        "external_libraries_detected": list(detected_imports.keys()),
        "verified_libraries": verified_libraries,
        "unverified_libraries": [k for k in detected_imports.keys() if k not in verified_libraries],
        "imported_files": detected_imports,
    }
    return is_valid, violations, details


def validate_trajectory_motion_policy(trajectory: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Enforces Section 6 Trajectory Policy:
    - Never train trajectories that silently import an unverified package.
    - If GSAP or Framer Motion support is added, create SEPARATE library-specific trajectories
      rather than mixing them into native examples without labels.
    - Trajectories using external motion libraries must declare an explicit label:
      e.g. `motion_implementation: 'gsap'`, `motion_library: 'gsap'`, or `<motion implementation='gsap' ...>`.
    """
    violations: List[str] = []

    files: Dict[str, str] = {}
    if "files" in trajectory and isinstance(trajectory["files"], dict):
        files = trajectory["files"]
    elif "turns" in trajectory and isinstance(trajectory["turns"], list):
        for t in trajectory["turns"]:
            if isinstance(t, dict):
                f_map = t.get("files") or t.get("project_files") or {}
                if isinstance(f_map, dict):
                    files.update(f_map)
                content = t.get("content") or t.get("code") or ""
                if content:
                    files[f"turn_{t.get('step', len(files))}.tsx"] = content

    detected_imports = inspect_motion_library_imports(files)
    if not detected_imports:
        return True, []

    traj_label = (
        trajectory.get("motion_implementation")
        or trajectory.get("motion_library")
        or trajectory.get("library")
    )
    prompt_or_brief = str(trajectory.get("prompt", "")) + " " + str(trajectory.get("brief", ""))

    for lib_key, file_paths in detected_imports.items():
        has_explicit_label = False
        if traj_label and lib_key in str(traj_label).lower():
            has_explicit_label = True
        elif f'implementation="{lib_key}"' in prompt_or_brief or f"implementation='{lib_key}'" in prompt_or_brief:
            has_explicit_label = True
        elif f"[{lib_key.upper()}]" in prompt_or_brief or f"library: {lib_key}" in prompt_or_brief.lower():
            has_explicit_label = True

        if not has_explicit_label:
            violations.append(
                f"Trajectory Policy violation: Trajectory imports '{lib_key}' in {file_paths[0]} without explicit "
                f"label ('motion_implementation: \"{lib_key}\"' or '<motion implementation=\"{lib_key}\">'). "
                "Section 6 requires creating separate library-specific trajectories rather than mixing into native examples without labels."
            )

        # Check dependency declaration in trajectory
        pkg_json = trajectory.get("package_json") or files.get("package.json")
        if pkg_json:
            is_verified = verify_motion_library_dependency(lib_key, package_json=pkg_json)
            if not is_verified:
                violations.append(
                    f"Trajectory Policy violation: Trajectory imports '{lib_key}' but '{lib_key}' is missing from package.json dependencies."
                )

    return len(violations) == 0, violations


# ── Canonical Library-Specific Trajectory Generators (Section 6) ─────────────

def generate_gsap_trajectory_snippet(section_name: str = "Showcase") -> Tuple[str, str, Dict[str, str], MotionSpec]:
    """Generates a separate, explicitly labeled GSAP trajectory component conforming to Section 6."""
    pascal = section_name.replace(" ", "").capitalize()
    tsx = f"""import React, {{ useEffect, useRef }} from 'react';
import {{ gsap }} from 'gsap';
import {{ ScrollTrigger }} from 'gsap/ScrollTrigger';
import './{pascal}.css';

gsap.registerPlugin(ScrollTrigger);

export function {pascal}() {{
  const sectionRef = useRef<HTMLElement | null>(null);
  const trackRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {{
    const ctx = gsap.context(() => {{
      const track = trackRef.current;
      if (!track) return;

      // Section 6: Explicit GSAP ScrollTrigger timeline with reduced-motion respect
      const mm = gsap.matchMedia();
      mm.add('(prefers-reduced-motion: no-preference)', () => {{
        gsap.to(track, {{
          x: () => -(track.scrollWidth - window.innerWidth),
          ease: 'none',
          scrollTrigger: {{
            trigger: sectionRef.current,
            start: 'top top',
            end: () => "+=" + track.scrollWidth,
            pin: true,
            scrub: 1,
            invalidateOnRefresh: true,
          }},
        }});
      }});
    }}, sectionRef);

    return () => ctx.revert();
  }}, []);

  return (
    <section ref={{sectionRef}} className="gsap-showcase-section" id="showcase">
      <div ref={{trackRef}} className="gsap-horizontal-track">
        <div className="gsap-card">
          <h3>GSAP Milestone 01</h3>
          <p>Verified library dependency with contextual cleanup.</p>
        </div>
        <div className="gsap-card">
          <h3>GSAP Milestone 02</h3>
          <p>Pinning and scrubbing mapped without event hijacking.</p>
        </div>
      </div>
    </section>
  );
}}
"""
    css = """.gsap-showcase-section {
  overflow: hidden;
  background: #0b0f19;
  color: #ffffff;
}

.gsap-horizontal-track {
  display: flex;
  gap: 2rem;
  padding: 4rem;
  width: max-content;
}

.gsap-card {
  flex: 0 0 400px;
  padding: 2.5rem;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 16px;
}
"""
    deps = {"gsap": "^3.12.5"}
    spec = MotionSpec(
        type=MotionType.HORIZONTAL_SCROLL,
        target_section=section_name.lower(),
        intensity="cinematic",
        implementation="gsap",
    )
    return tsx, css, deps, spec


def generate_framer_motion_trajectory_snippet(section_name: str = "Features") -> Tuple[str, str, Dict[str, str], MotionSpec]:
    """Generates a separate, explicitly labeled Framer Motion trajectory component conforming to Section 6."""
    pascal = section_name.replace(" ", "").capitalize()
    tsx = f"""import React from 'react';
import {{ motion, useReducedMotion }} from 'framer-motion';
import './{pascal}.css';

export function {pascal}() {{
  const shouldReduce = useReducedMotion();

  const containerVariants = {{
    hidden: {{ opacity: 0 }},
    visible: {{
      opacity: 1,
      transition: {{
        staggerChildren: shouldReduce ? 0 : 0.12,
      }},
    }},
  }};

  const cardVariants = {{
    hidden: {{ opacity: 0, y: shouldReduce ? 0 : 24 }},
    visible: {{
      opacity: 1,
      y: 0,
      transition: {{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }},
    }},
  }};

  return (
    <section className="framer-features-section" id="features">
      <motion.div
        className="features-grid"
        variants={{containerVariants}}
        initial="hidden"
        whileInView="visible"
        viewport={{{{ once: true, amount: 0.2 }}}}
      >
        <motion.div className="framer-card" variants={{cardVariants}}>
          <h3>Hardware Constrained</h3>
          <p>Verified Framer Motion execution without runtime hallucination.</p>
        </motion.div>
        <motion.div className="framer-card" variants={{cardVariants}}>
          <h3>Accessibility Guard</h3>
          <p>Automatically honors user prefers-reduced-motion settings.</p>
        </motion.div>
      </motion.div>
    </section>
  );
}}
"""
    css = """.framer-features-section {
  padding: 5rem 2rem;
  background: #0b0f19;
  color: #ffffff;
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 2rem;
  max-width: 1200px;
  margin: 0 auto;
}

.framer-card {
  padding: 2rem;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
}
"""
    deps = {"framer-motion": "^11.0.0"}
    spec = MotionSpec(
        type=MotionType.SCROLL_REVEAL,
        target_section=section_name.lower(),
        intensity="medium",
        implementation="framer-motion",
    )
    return tsx, css, deps, spec
