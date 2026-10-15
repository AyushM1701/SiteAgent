"""Deterministic design director and anti-fingerprint genome selector."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Tuple


@dataclass(frozen=True)
class DesignGenome:
    hero: str
    theme_mode: str
    palette: str
    display_font: str
    body_font: str
    section_archetypes: Tuple[str, ...]
    density: str
    surface_language: str
    motion_personality: str
    media_personality: str
    dominant_alignment: str = "left"

    def to_dict(self) -> Dict[str, Any]:
        return {**self.__dict__, "section_archetypes": list(self.section_archetypes)}


def genome_similarity(a: DesignGenome, b: DesignGenome) -> float:
    fields = ("hero", "theme_mode", "palette", "display_font", "body_font", "section_archetypes",
              "density", "surface_language", "motion_personality", "media_personality", "dominant_alignment")
    return sum(getattr(a, f) == getattr(b, f) for f in fields) / len(fields)


def _candidates(brief: Dict[str, Any], task_index: int = 0) -> List[DesignGenome]:
    domain = str(brief.get("business_type", "general")).lower()
    base = [
        DesignGenome("split-stage", "dark", "graphite-cobalt", "Syne", "Manrope", ("split", "bento-asymmetric", "sticky-deck", "editorial"), "airy", "bordered-glass", "precise", "product-render"),
        DesignGenome("editorial", "light", "paper-oxide", "Fraunces", "Manrope", ("editorial", "horizontal-collection", "immersive-full-bleed"), "airy", "paper-ink", "quiet", "photography"),
        DesignGenome("product-stage", "dark", "ink-copper", "Space Grotesk", "Inter", ("product-stage", "sticky-deck", "bento-asymmetric"), "compact", "technical-surface", "precise", "product-render"),
        DesignGenome("full-bleed", "light", "sand-olive", "DM Serif Display", "Satoshi", ("immersive-full-bleed", "editorial", "horizontal-collection"), "balanced", "flat-paper", "cinematic", "photography"),
        DesignGenome("asymmetric", "dark", "black-lime", "Instrument Serif", "IBM Plex Mono", ("asymmetric", "sticky-deck", "wide-cta"), "dense", "bordered-metal", "kinetic", "procedural"),
    ]
    if domain in {"saas", "fintech", "developer", "dashboard"}:
        return [base[0], base[2], base[4]]
    return base


def select_genome(brief: Dict[str, Any], recent: Iterable[DesignGenome] = (), task_index: int = 0) -> DesignGenome:
    recent_list = list(recent)[-20:]
    prefers_centered = bool(brief.get("prefers_centered"))
    def score(genome: DesignGenome) -> float:
        repetition = max((genome_similarity(genome, old) for old in recent_list), default=0.0)
        penalty = 0.0
        if genome.hero == "centered" and not prefers_centered:
            penalty += 2.0
        if genome.section_archetypes.count("three-column-grid") > 1:
            penalty += 3.0
        return (1.0 if genome.media_personality in {"photography", "product-render", "procedural"} else 0.5) - repetition * 2.5 - penalty
    candidates = _candidates(brief, task_index)
    scores = [score(genome) for genome in candidates]
    best = max(scores)
    # Ties were previously resolved by list order, so every site without
    # history got the same genome. Rotate among the best by the request seed.
    tied = [genome for genome, value in zip(candidates, scores) if value >= best - 1e-9]
    return tied[task_index % len(tied)]


def plan_design_direction(brief: Dict[str, Any], recent: Iterable[DesignGenome] = (), task_index: int = 0) -> Dict[str, Any]:
    genome = select_genome(brief, recent, task_index)
    return {"visual_thesis": f"{genome.surface_language} {genome.motion_personality} art direction",
            "mode": genome.theme_mode, "palette": genome.palette,
            "typography": {"display": genome.display_font, "body": genome.body_font, "mono": "IBM Plex Mono"},
            "density": genome.density, "corner_language": "soft-square", "surface_language": genome.surface_language,
            "hero": genome.hero, "section_rhythm": list(genome.section_archetypes),
            "motion_personality": genome.motion_personality, "media_personality": genome.media_personality,
            "dominant_alignment": genome.dominant_alignment,
            "avoid": ["centered hero", "three equal feature cards", "blue-purple generic gradient"] if genome.hero != "centered" else [] ,
             "genome": genome.to_dict()}


def genome_history_from_brief(brief: Dict[str, Any]) -> List[DesignGenome]:
    """Decode persisted recent genome history without allowing malformed data in."""
    result: List[DesignGenome] = []
    for raw in brief.get("recent_design_genomes", []) or []:
        if not isinstance(raw, dict):
            continue
        try:
            result.append(DesignGenome(
                hero=str(raw["hero"]), theme_mode=str(raw["theme_mode"]),
                palette=str(raw["palette"]), display_font=str(raw["display_font"]),
                body_font=str(raw["body_font"]),
                section_archetypes=tuple(raw["section_archetypes"]),
                density=str(raw["density"]), surface_language=str(raw["surface_language"]),
                motion_personality=str(raw["motion_personality"]),
                media_personality=str(raw["media_personality"]),
                dominant_alignment=str(raw.get("dominant_alignment", "left")),
            ))
        except (KeyError, TypeError, ValueError):
            continue
    return result[-20:]
