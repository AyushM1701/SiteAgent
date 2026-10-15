"""
agent/design_plan.py - Deterministic Structured Design-Planning Supervision.

Implements Section 3.C of the Professional-Grade Website Model Improvements:
Conditioning the model on a compact structured design plan prior to file generation:
{
  "artDirection": "editorial industrial",
  "heroArchetype": "split",
  "density": "airy",
  "typeScale": "display-heavy",
  "sectionRhythm": ["quiet", "dense", "immersive", "quiet"],
  "motion": ["text-reveal", "sticky-story"],
  "visualAnchor": "product-render",
  "mobileStrategy": "stack"
}

The design plan is synthesized by deterministic orchestration to ensure perfectly
balanced archetype trajectories across training, benchmarking, and execution batches,
without reliance on hidden chain-of-thought or non-deterministic token reasoning.
"""

from dataclasses import asdict, dataclass, field
import hashlib
import json
import re
from typing import Any, Dict, List, Optional
from agent.design_director import plan_design_direction, DesignGenome, genome_history_from_brief


CANONICAL_HERO_ARCHETYPES = [
    "split",
    "editorial_asymmetric",
    "full_bleed_visual",
    "bento",
    "terminal_data",
    "product_stage",
    "restrained_centered",
]

# Genome fields that duplicate (and used to contradict) the brief's design system,
# or the plan's own heroArchetype / density / topology fields.
_BRIEF_OWNED_GENOME_FIELDS = {"palette", "display_font", "body_font", "theme_mode",
                              "hero", "density", "section_archetypes"}

VALID_DENSITIES = ["airy", "compact", "balanced", "dense"]
VALID_TYPE_SCALES = ["display-heavy", "typographic-contrast", "editorial-serif", "technical-mono", "balanced-clean"]
VALID_MOBILE_STRATEGIES = ["stack", "scroll-snap", "drawer-collapse", "tab-switch"]
VALID_TOPOLOGIES = {"quiet", "dense", "immersive", "interactive", "impact", "structured",
                    "asymmetric", "bento-asymmetric", "split", "sticky-deck", "editorial",
                    "horizontal-collection", "wide-cta", "product-stage", "three-column-grid"}


@dataclass
class DesignPlan:
    """Compact structured design plan conditioning site generation."""
    artDirection: str
    heroArchetype: str
    density: str
    typeScale: str
    sectionRhythm: List[str] = field(default_factory=lambda: ["quiet", "dense", "immersive", "quiet"])
    motion: List[str] = field(default_factory=lambda: ["text-reveal", "sticky-story"])
    visualAnchor: str = "product-render"
    mobileStrategy: str = "stack"
    topology: List[str] = field(default_factory=list)
    designGenome: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Converts design plan to exact camelCase JSON dictionary."""
        return {
            "artDirection": self.artDirection,
            "heroArchetype": self.heroArchetype,
            "density": self.density,
            "typeScale": self.typeScale,
            "sectionRhythm": self.sectionRhythm,
            "motion": self.motion,
            "visualAnchor": self.visualAnchor,
            "mobileStrategy": self.mobileStrategy,
            "topology": self.topology,
            "designGenome": self.designGenome,
        }

    def to_compact_json(self) -> str:
        """Emits compact single-line or clean multi-line JSON."""
        return json.dumps(self.to_dict(), separators=(",", ": "))

    def align_with_brief(self, media_available: bool = True) -> "DesignPlan":
        """Make the plan agree with the content brief, which owns the visual system.

        The genome's palette names, fonts and light/dark mode are dropped: the
        brief's design system (colours, fonts, CSS variables) is the only source,
        and it is what the preview's index.html actually loads. When the brief has
        no usable photography, photo-led anchors become typographic ones.
        """
        if isinstance(self.designGenome, dict):
            self.designGenome = {key: value for key, value in self.designGenome.items()
                                 if key not in _BRIEF_OWNED_GENOME_FIELDS}
            if not media_available and self.designGenome.get("media_personality") == "photography":
                self.designGenome["media_personality"] = "typographic"
        if not media_available and "photo" in self.visualAnchor:
            self.visualAnchor = "typographic-composition"
        return self

    def to_prompt_block(self) -> str:
        """Formats the design plan as a high-visibility conditioning block."""
        plan_json = json.dumps(self.to_dict(), indent=2)
        return (
            "=== STRUCTURED DESIGN PLAN ===\n"
            "Follow this plan for layout, hero composition, rhythm, density and motion. "
            "Colours, fonts and light/dark mode come only from the design system in the Content Brief:\n"
            f"{plan_json}\n"
            "==============================\n"
        )

    def to_layout_xml(self) -> str:
        """Serialize the layout contract used by generators and validators."""
        import xml.etree.ElementTree as ET
        root = ET.Element("layout", {"archetype": self.heroArchetype, "density": self.density})
        topology = ET.SubElement(root, "topology")
        for item in self.topology:
            ET.SubElement(topology, "section", {"archetype": item})
        return ET.tostring(root, encoding="unicode", short_empty_elements=True)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DesignPlan":
        """Instantiates DesignPlan, rejecting malformed plans instead of silently repairing them."""
        if not isinstance(data, dict):
            raise ValueError("design plan must be an object")
        required = {"artDirection", "heroArchetype", "density", "typeScale", "sectionRhythm", "motion", "visualAnchor", "mobileStrategy", "topology", "designGenome"}
        missing = required - set(data)
        if missing:
            raise ValueError("design plan missing fields: " + ", ".join(sorted(missing)))
        hero = data.get("heroArchetype", "split")
        if hero not in CANONICAL_HERO_ARCHETYPES:
            raise ValueError(f"unsupported hero archetype: {hero}")
        if data.get("density") not in VALID_DENSITIES or data.get("typeScale") not in VALID_TYPE_SCALES or data.get("mobileStrategy") not in VALID_MOBILE_STRATEGIES:
            raise ValueError("invalid design plan enum")
        if not isinstance(data.get("sectionRhythm"), list) or not isinstance(data.get("motion"), list) or not isinstance(data.get("topology"), list):
            raise ValueError("sectionRhythm, motion, and topology must be arrays")
        unknown = set(data["topology"]) - VALID_TOPOLOGIES
        if unknown:
            raise ValueError("unsupported topology: " + ", ".join(sorted(unknown)))
        density = data.get("density", "airy")
        type_scale = data.get("typeScale", "display-heavy")
        mobile = data.get("mobileStrategy", "stack")
        if density not in VALID_DENSITIES:
            raise ValueError(f"Invalid density: {density}")
        if type_scale not in VALID_TYPE_SCALES:
            raise ValueError(f"Invalid typeScale: {type_scale}")
        if mobile not in VALID_MOBILE_STRATEGIES:
            raise ValueError(f"Invalid mobileStrategy: {mobile}")
        topology = data.get("topology", [])
        if not isinstance(topology, list) or any(not isinstance(item, str) for item in topology):
            raise ValueError("Invalid topology")
        return cls(
            artDirection=data.get("artDirection", "editorial industrial"),
            heroArchetype=hero,
            density=density,
            typeScale=type_scale,
            sectionRhythm=data.get("sectionRhythm", ["quiet", "dense", "immersive", "quiet"]),
            motion=data.get("motion", ["text-reveal", "sticky-story"]),
            visualAnchor=data.get("visualAnchor", "product-render"),
            mobileStrategy=mobile,
            topology=data.get("topology", []),
            designGenome=data.get("designGenome"),
        )


# ==============================================================================
# Deterministic Domain & Style Presets Catalog
# ==============================================================================

_DOMAIN_ART_DIRECTIONS: Dict[str, List[Dict[str, Any]]] = {
    "saas": [
        {
            "artDirection": "high-velocity modern saas",
            "density": "balanced",
            "typeScale": "display-heavy",
            "sectionRhythm": ["quiet", "dense", "interactive", "quiet"],
            "motion": ["text-reveal", "stagger-grid"],
            "visualAnchor": "interactive-canvas",
            "mobileStrategy": "stack",
        },
        {
            "artDirection": "technical precision enterprise",
            "density": "compact",
            "typeScale": "balanced-clean",
            "sectionRhythm": ["impact", "structured", "dense", "quiet"],
            "motion": ["fade-up", "smooth-scroll"],
            "visualAnchor": "product-render",
            "mobileStrategy": "drawer-collapse",
        },
    ],
    "fintech": [
        {
            "artDirection": "editorial industrial",
            "density": "airy",
            "typeScale": "display-heavy",
            "sectionRhythm": ["quiet", "dense", "immersive", "quiet"],
            "motion": ["text-reveal", "sticky-story"],
            "visualAnchor": "product-render",
            "mobileStrategy": "stack",
        },
        {
            "artDirection": "cryptographic dark mono",
            "density": "compact",
            "typeScale": "technical-mono",
            "sectionRhythm": ["dense", "structured", "quiet"],
            "motion": ["text-reveal", "counter-ticker"],
            "visualAnchor": "data-terminal",
            "mobileStrategy": "tab-switch",
        },
    ],
    "developer": [
        {
            "artDirection": "minimalist command runtime",
            "density": "compact",
            "typeScale": "technical-mono",
            "sectionRhythm": ["quiet", "dense", "immersive", "quiet"],
            "motion": ["text-reveal", "terminal-typing"],
            "visualAnchor": "data-terminal",
            "mobileStrategy": "stack",
        },
        {
            "artDirection": "systems infrastructure blueprint",
            "density": "balanced",
            "typeScale": "typographic-contrast",
            "sectionRhythm": ["impact", "dense", "interactive"],
            "motion": ["fade-up", "stagger-grid"],
            "visualAnchor": "interactive-canvas",
            "mobileStrategy": "drawer-collapse",
        },
    ],
    "ecommerce": [
        {
            "artDirection": "minimalist luxury atelier",
            "density": "airy",
            "typeScale": "editorial-serif",
            "sectionRhythm": ["immersive", "dense", "quiet"],
            "motion": ["parallax-float", "magnetic-hover"],
            "visualAnchor": "product-render",
            "mobileStrategy": "scroll-snap",
        },
        {
            "artDirection": "kinetic streetwear editorial",
            "density": "dense",
            "typeScale": "display-heavy",
            "sectionRhythm": ["impact", "immersive", "dense"],
            "motion": ["marquee-scroll", "stagger-grid"],
            "visualAnchor": "photography-bleed",
            "mobileStrategy": "scroll-snap",
        },
    ],
    "portfolio": [
        {
            "artDirection": "monolithic architectural gallery",
            "density": "airy",
            "typeScale": "display-heavy",
            "sectionRhythm": ["quiet", "immersive", "quiet"],
            "motion": ["smooth-pan", "text-reveal"],
            "visualAnchor": "photography-bleed",
            "mobileStrategy": "stack",
        },
        {
            "artDirection": "swiss international typographic",
            "density": "balanced",
            "typeScale": "typographic-contrast",
            "sectionRhythm": ["structured", "dense", "quiet"],
            "motion": ["fade-up", "magnetic-hover"],
            "visualAnchor": "interactive-canvas",
            "mobileStrategy": "stack",
        },
    ],
    "architecture": [
        {
            "artDirection": "spatial brutalist plinth",
            "density": "airy",
            "typeScale": "display-heavy",
            "sectionRhythm": ["quiet", "immersive", "structured", "quiet"],
            "motion": ["ambient-float", "sticky-story"],
            "visualAnchor": "3d-stage",
            "mobileStrategy": "stack",
        },
    ],
    "restaurant": [
        {
            "artDirection": "warm culinary editorial",
            "density": "balanced",
            "typeScale": "editorial-serif",
            "sectionRhythm": ["immersive", "dense", "quiet"],
            "motion": ["fade-up", "ambient-float"],
            "visualAnchor": "photography-bleed",
            "mobileStrategy": "scroll-snap",
        },
    ],
    "healthcare": [
        {
            "artDirection": "clinical serenity & modern bio",
            "density": "airy",
            "typeScale": "balanced-clean",
            "sectionRhythm": ["quiet", "structured", "dense", "quiet"],
            "motion": ["fade-up", "smooth-scroll"],
            "visualAnchor": "product-render",
            "mobileStrategy": "stack",
        },
    ],
    "editorial": [{
        "artDirection": "publication typography and story hierarchy",
        "density": "balanced", "typeScale": "editorial-serif",
        "sectionRhythm": ["immersive", "structured", "dense", "quiet"],
        "motion": ["text-reveal", "fade-up"],
        "visualAnchor": "photography-bleed", "mobileStrategy": "stack",
    }],
    "blog": [{
        "artDirection": "readable journal typography",
        "density": "airy", "typeScale": "editorial-serif",
        "sectionRhythm": ["quiet", "structured", "quiet"],
        "motion": ["fade-up"],
        "visualAnchor": "photography-bleed", "mobileStrategy": "stack",
    }],
    "event": [{
        "artDirection": "event identity and program clarity",
        "density": "balanced", "typeScale": "display-heavy",
        "sectionRhythm": ["impact", "structured", "dense", "quiet"],
        "motion": ["text-reveal", "fade-up"],
        "visualAnchor": "photography-bleed", "mobileStrategy": "stack",
    }],
    "dashboard": [{
        "artDirection": "operational data clarity",
        "density": "dense", "typeScale": "balanced-clean",
        "sectionRhythm": ["structured", "dense", "structured"],
        "motion": ["fade-up"],
        "visualAnchor": "data-terminal", "mobileStrategy": "stack",
    }],
}

_DEFAULT_PRESET = {
    "artDirection": "purpose-led visual identity",
    "density": "airy",
    "typeScale": "display-heavy",
    "sectionRhythm": ["quiet", "dense", "immersive", "quiet"],
    "motion": ["text-reveal", "sticky-story"],
    "visualAnchor": "photography-bleed",
    "mobileStrategy": "stack",
}


# Brief layout archetypes (agent/site_brief.py) -> hero archetype.
_LAYOUT_TO_HERO_ARCHETYPE = {
    "editorial": "editorial_asymmetric",
    "magazine": "editorial_asymmetric",
    "asymmetric": "editorial_asymmetric",
    "bento": "bento",
    "split_hero": "split",
    "grid": "split",
    "tabs": "split",
    "timeline": "restrained_centered",
}


_TECH_DOMAINS = {"saas", "fintech", "developer", "dashboard", "agency"}
_PRODUCT_STAGE_DOMAINS = {"ecommerce", "architecture", "coffee"}


def prompt_design_seed(prompt: str) -> int:
    """Stable per-request seed; 0 for an empty prompt."""
    text = " ".join((prompt or "").lower().split())
    if not text:
        return 0
    return int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:8], 16)


def synthesize_design_plan(
    prompt_spec: Optional[Dict[str, Any]] = None,
    domain: str = "general",
    task_index: int = 0,
) -> DesignPlan:
    """
    Deterministically synthesizes a compact structured design plan.
    
    Guarantees:
    1. Perfect layout archetype balance across tasks (round-robin cycle across 7 archetypes).
    2. Authentic domain-appropriate art direction and rhythm.
    3. Respects explicit user overrides if present in prompt_spec.
    """
    spec = prompt_spec or {}
    dom = (spec.get("domain") or domain or "general").lower().strip()
    
    # 1. Determine hero archetype:
    # Check for explicit request in prompt/spec
    raw_prompt = (spec.get("prompt") or spec.get("title") or spec.get("description") or "").lower()
    selected_archetype: Optional[str] = None
    
    explicit_archetype = spec.get("heroArchetype")
    if explicit_archetype in CANONICAL_HERO_ARCHETYPES:
        selected_archetype = explicit_archetype
    elif re.search(r"\bbento\b", raw_prompt):
        selected_archetype = "bento"
    elif re.search(r"\b(?:terminal|cli)\b", raw_prompt) or (re.search(r"\bdeveloper\b", raw_prompt) and re.search(r"\bcode\b", raw_prompt)):
        selected_archetype = "terminal_data"
    elif re.search(r"\b(?:product stage|plinth|pedestal)\b", raw_prompt):
        selected_archetype = "product_stage"
    elif re.search(r"\b(?:full[- ]bleed|cinematic|photography|photographic)\b", raw_prompt):
        selected_archetype = "full_bleed_visual"
    elif re.search(r"\b(?:editorial|magazine)\b", raw_prompt):
        selected_archetype = "editorial_asymmetric"
    elif re.search(r"\bcentered (?:hero|layout|composition)\b", raw_prompt):
        selected_archetype = "restrained_centered"
    elif re.search(r"\bsplit(?:[- ]screen| layout| hero| composition)\b", raw_prompt):
        selected_archetype = "split"
    elif spec.get("layoutArchetype") in _LAYOUT_TO_HERO_ARCHETYPE:
        # Keep the hero consistent with the content brief's layout archetype.
        selected_archetype = _LAYOUT_TO_HERO_ARCHETYPE[spec["layoutArchetype"]]

    # Seed from the request itself so different prompts get different plans even
    # when every caller passes task_index=0 (the workbench does). An empty prompt
    # keeps plain task_index round-robin for batch balancing.
    seed = task_index + prompt_design_seed(raw_prompt)

    # If no explicit keyword, balance systematically using the seed
    if not selected_archetype:
        # Round-robin across the archetypes that suit the domain: a terminal or
        # product-render stage is wrong for a bakery or a law firm.
        pool = list(CANONICAL_HERO_ARCHETYPES)
        if dom not in _TECH_DOMAINS:
            pool.remove("terminal_data")
            if dom not in _PRODUCT_STAGE_DOMAINS:
                pool.remove("product_stage")
        selected_archetype = pool[seed % len(pool)]

    # 2. Select domain art direction & rhythm preset
    domain_presets = _DOMAIN_ART_DIRECTIONS.get(dom)
    if not domain_presets:
        # Match fuzzy domain
        matched_key = next((k for k in _DOMAIN_ART_DIRECTIONS if k in dom or dom in k), None)
        domain_presets = _DOMAIN_ART_DIRECTIONS.get(matched_key, [_DEFAULT_PRESET])
    
    preset_idx = seed % len(domain_presets)
    preset = domain_presets[preset_idx]

    # 3. Synchronize visual anchor with hero archetype
    anchor = preset.get("visualAnchor", "product-render")
    if selected_archetype == "terminal_data":
        anchor = "data-terminal"
    elif selected_archetype == "product_stage":
        anchor = "3d-stage"
    elif selected_archetype == "full_bleed_visual":
        anchor = "photography-bleed"
    elif selected_archetype == "bento":
        anchor = "interactive-canvas"

    direction = plan_design_direction({**spec, "business_type": dom}, recent=genome_history_from_brief(spec), task_index=seed)
    topology = list(spec.get("topology") or direction["section_rhythm"])
    # Planner-level diversity constraints: topology, not implementation, owns
    # the anti-template rules.
    if topology.count("three-column-grid") > 1:
        topology = [item for idx, item in enumerate(topology) if item != "three-column-grid" or idx == topology.index(item)]
    if not any(item in topology for item in ("asymmetric", "bento-asymmetric", "split", "sticky-deck")):
        topology.insert(0, "asymmetric")
    if not any(item in topology for item in ("editorial", "sticky-deck", "horizontal-collection", "wide-cta")):
        topology.append("wide-cta")

    return DesignPlan(
        artDirection=spec.get("artDirection") or preset.get("artDirection", "editorial industrial"),
        heroArchetype=selected_archetype,
        density=spec.get("density") or preset.get("density", "airy"),
        typeScale=spec.get("typeScale") or preset.get("typeScale", "display-heavy"),
        sectionRhythm=spec.get("sectionRhythm") or preset.get("sectionRhythm", ["quiet", "dense", "immersive", "quiet"]),
        motion=spec.get("motion") or preset.get("motion", ["text-reveal", "sticky-story"]),
        visualAnchor=anchor,
        mobileStrategy=spec.get("mobileStrategy") or preset.get("mobileStrategy", "stack"),
        topology=topology,
        designGenome=direction["genome"],
    )
