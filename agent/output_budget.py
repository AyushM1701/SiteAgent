"""
agent/output_budget.py - Dynamic Output Token Budget Engine

Implements the authoritative policy for dynamic output token budgeting:
  small targeted patch          512–768    (tiny edits, single diagnostic repairs)
  normal component              1024–1536  (standard single components)
  complex interaction           1536–2048  (dnd, keyboard nav, forms, timers, undo/redo, data tables)
  simple site section           1600–2200  (basic multi-file sections: header, footer, about)
  interactive site section      2400–3200  (sliders, calculators, tabs, accordions, live-values)
  complex site section          2800–3600  (interactive + 3+ files or diagnostic complexity)
  3D site section               3000–4096  (Three.js, R3F, canvas, WebGL, shaders, animations)

Complexity is estimated using:
- task mode (component, site, patch, edit, 3d)
- requested files (single file vs multi-file section)
- current file length (short vs large existing code)
- interaction keywords (dnd, keyboard, cart, undo, table, etc.)
- site-specific interactive keywords (calculator, slider, chart, live, delta-v, etc.)
- 3D usage (three, r3f, canvas, shader, etc.)
- repair diagnostics (single localized fix vs complex assertion failures)

All budgets are clamped against the active context length (max_seq_length - prompt_tokens).
"""

from __future__ import annotations

import dataclasses
import enum
import re
from typing import Any, Dict, List, Optional, Set, Tuple


class BudgetTier(str, enum.Enum):
    SMALL_PATCH = "small targeted patch"
    NORMAL_COMPONENT = "normal component"
    COMPLEX_INTERACTION = "complex interaction"
    SIMPLE_SITE_SECTION = "simple site section"
    INTERACTIVE_SITE_SECTION = "interactive site section"
    COMPLEX_SITE_SECTION = "complex site section"
    SCENE_3D = "3D scene"
    SITE_SECTION_3D = "3D site section"
    # Legacy tier retained for callers that still request the old policy explicitly.
    SITE_SECTION = "site section"


# Exact token budget ranges according to the recommended policy
TIER_TOKEN_RANGES: Dict[str, Tuple[int, int, int]] = {
    # Tier: (min_tokens, max_tokens, recommended_target)
    BudgetTier.SMALL_PATCH.value:              (512,  768,  640),
    BudgetTier.NORMAL_COMPONENT.value:         (1024, 1536, 1280),
    BudgetTier.COMPLEX_INTERACTION.value:      (1536, 2048, 1792),
    BudgetTier.SITE_SECTION.value:             (1536, 2048, 1920),
    BudgetTier.SIMPLE_SITE_SECTION.value:      (1600, 2200, 1900),
    BudgetTier.INTERACTIVE_SITE_SECTION.value: (2400, 3200, 2800),
    BudgetTier.COMPLEX_SITE_SECTION.value:     (2800, 3600, 3200),
    BudgetTier.SCENE_3D.value:                 (2048, 2560, 2304),
    BudgetTier.SITE_SECTION_3D.value:          (3000, 4096, 3600),
}

# 3D Scene detection keywords (case-insensitive)
KEYWORDS_3D: Set[str] = {
    "three.js",
    "threejs",
    "r3f",
    "@react-three/fiber",
    "@react-three/drei",
    "canvas",
    "webgl",
    "3d",
    "mesh",
    "geometry",
    "shader",
    "shaders",
    "orbitcontrols",
    "perspectivecamera",
    "ambientlight",
    "pointlight",
    "directionallight",
    "gltf",
    "pointcloud",
    "particle",
    "particles",
    "spheregeometry",
    "boxgeometry",
    "useframe",
    "raycaster",
}

# Complex interaction detection keywords (case-insensitive)
KEYWORDS_INTERACTION: Set[str] = {
    "drag",
    "drop",
    "dnd",
    "drag-and-drop",
    "keyboard",
    "keydown",
    "keyup",
    "escape",
    "focus",
    "focus-trap",
    "focustrap",
    "trap focus",
    "timer",
    "interval",
    "timeout",
    "debounce",
    "debounced",
    "throttle",
    "throttled",
    "optimistic",
    "optimistic ui",
    "cart",
    "usecart",
    "shopping cart",
    "undo",
    "redo",
    "useundo",
    "history stack",
    "queryparams",
    "usequeryparams",
    "query param",
    "url search",
    "confirm",
    "useconfirm",
    "confirm dialog",
    "onclickoutside",
    "useonclickoutside",
    "click outside",
    "formprovider",
    "form context",
    "validation",
    "validate",
    "datatable",
    "data table",
    "kanban",
    "kanbanboard",
    "kanban board",
    "carousel",
    "slider",
    "pagination",
    "paginate",
    "sorting",
    "filtering",
    "filter",
    "accordion",
    "virtualized",
    "virtual list",
    "tabs",
    "tab list",
    "modal",
    "portal",
    "createportal",
    "reducer",
    "usereducer",
    "context provider",
    "state machine",
    "multistep",
    "stepper",
}

# Site-section-specific interactive keywords: common in section briefs but
# not always in standalone component requests.  Unioned with KEYWORDS_INTERACTION
# when evaluating site_section tasks.
KEYWORDS_INTERACTIVE_SITE: Set[str] = {
    # Physics / science calculators
    "calculator",
    "delta-v",
    "delta v",
    "orbital",
    "trajectory",
    "physics",
    "simulation",
    "simulate",
    "compute",
    "computed",
    # Data visualisation
    "chart",
    "graph",
    "plot",
    "dashboard",
    "live data",
    "real-time",
    "realtime",
    "live values",
    "derived values",
    # Map / geo
    "map",
    "mapbox",
    "leaflet",
    # Rich media / animation
    "orbit",
    "lottie",
    "gsap",
    # Accessibility / UX patterns common to complex sections
    "aria-live",
    "live region",
    "screen reader",
    "reduced-motion",
    "reduced motion",
    # Responsive / layout interactive
    "hamburger",
    "mobile drawer",
    "sticky",
    "infinite scroll",
    "lazy load",
}

# Combined set for site-mode classification
KEYWORDS_INTERACTION_SITE_ALL: Set[str] = KEYWORDS_INTERACTION | KEYWORDS_INTERACTIVE_SITE


@dataclasses.dataclass
class TaskComplexityFactors:
    """Signals extracted from the task to estimate generation complexity."""
    task_mode: str = "component"  # "patch", "edit", "component", "site", "site_section", "3d"
    requested_files: List[str] = dataclasses.field(default_factory=list)
    current_file_length: int = 0  # in characters or tokens
    interaction_keywords: List[str] = dataclasses.field(default_factory=list)
    has_3d_usage: bool = False
    repair_diagnostics: Optional[str] = None
    prompt: str = ""
    target_symbol: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_mode": self.task_mode,
            "requested_files": self.requested_files,
            "current_file_length": self.current_file_length,
            "interaction_keywords": self.interaction_keywords,
            "has_3d_usage": self.has_3d_usage,
            "has_repair_diagnostics": bool(self.repair_diagnostics),
            "target_symbol": self.target_symbol,
        }


@dataclasses.dataclass
class OutputTokenBudget:
    """Result of dynamic output token budget calculation."""
    tier: str
    min_tokens: int
    max_tokens: int
    recommended_tokens: int
    clamped_tokens: int
    factors: Dict[str, Any]
    explanation: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tier": self.tier,
            "min_tokens": self.min_tokens,
            "max_tokens": self.max_tokens,
            "recommended_tokens": self.recommended_tokens,
            "clamped_tokens": self.clamped_tokens,
            "explanation": self.explanation,
            "factors": self.factors,
        }

    def log_summary(self, task_name: str = "task") -> str:
        return (
            f"[TokenBudget] Task: '{task_name}' | Tier: '{self.tier}' | "
            f"Allocated: {self.clamped_tokens} max_new_tokens (Range: {self.min_tokens}–{self.max_tokens}) | "
            f"Reason: {self.explanation}"
        )


def _find_keyword_matches(text: str, keywords: Set[str]) -> List[str]:
    """Find whole-word or substring matches for multi-word keywords in text."""
    if not text:
        return []
    lower_text = text.lower()
    matches = []
    for kw in sorted(keywords, key=lambda k: -len(k)):
        if " " in kw or "-" in kw or "." in kw or "/" in kw or "@" in kw:
            if kw in lower_text:
                matches.append(kw)
        else:
            if re.search(r'\b' + re.escape(kw) + r'\b', lower_text):
                matches.append(kw)
    return sorted(list(set(matches)))


def extract_complexity_factors(
    prompt: str = "",
    task_mode: str = "component",
    requested_files: Optional[List[str]] = None,
    current_file_length: int = 0,
    repair_diagnostics: Optional[str] = None,
    target_symbol: str = "",
    test_code: str = "",
) -> TaskComplexityFactors:
    """Extract complexity signals from prompt, code, and diagnostics."""
    combined_text = f"{prompt}\n{target_symbol}\n{test_code}"
    files = list(requested_files or [])

    found_3d = _find_keyword_matches(combined_text, KEYWORDS_3D)
    has_3d = bool(found_3d) or (task_mode.lower() == "3d")

    # For site modes, use the larger combined keyword set so interactive
    # site-specific terms (calculator, chart, delta-v, etc.) are captured.
    is_site_mode = task_mode.lower() in ("site", "site_section")
    kw_set = KEYWORDS_INTERACTION_SITE_ALL if is_site_mode else KEYWORDS_INTERACTION
    found_interactions = _find_keyword_matches(combined_text, kw_set)

    return TaskComplexityFactors(
        task_mode=task_mode.lower(),
        requested_files=files,
        current_file_length=current_file_length,
        interaction_keywords=found_interactions,
        has_3d_usage=has_3d,
        repair_diagnostics=repair_diagnostics,
        prompt=prompt,
        target_symbol=target_symbol,
    )


def estimate_output_budget(
    factors: TaskComplexityFactors,
    prompt_tokens: int = 0,
    max_seq_length: Optional[int] = None,
) -> OutputTokenBudget:
    """
    Select max_new_tokens according to the recommended dynamic output policy.

    Site sections are split into four tiers based on detected complexity:
      simple site section           1600–2200  (header, footer, about — no interaction keywords)
      interactive site section      2400–3200  (sliders, calculators, tabs, live values)
      complex site section          2800–3600  (interactive + many files or heavy diagnostics)
      3D site section               3000–4096  (Three.js / R3F / WebGL)

    Non-site tiers:
      small targeted patch     512–768
      normal component         1024–1536
      complex interaction      1536–2048
      3D scene (component)     2048–2560

    Clamps the budget to fit strictly within max_seq_length - prompt_tokens.
    """
    is_site_mode = factors.task_mode in ("site", "site_section") or len(factors.requested_files) > 1

    # ── Site-mode branch: evaluate sub-tiers internally ─────────────────────
    # IMPORTANT: This branch evaluates 3D and interaction keywords WITHIN the
    # site check so they are never shadowed by the later global branches.
    if is_site_mode:
        # 3D site section (highest footprint)
        if factors.has_3d_usage or factors.task_mode == "3d":
            tier = BudgetTier.SITE_SECTION_3D
            min_tok, max_tok, target_tok = TIER_TOKEN_RANGES[tier.value]
            explanation = (
                "3D site section detected (Three.js/R3F/canvas/WebGL); "
                "maximum token budget allocated for scene + layout code."
            )

        # Complex site section: many files AND interaction keywords, or interaction with repair pressure
        elif factors.interaction_keywords and (
            len(factors.requested_files) >= 3
            or (factors.repair_diagnostics and any(
                k in factors.repair_diagnostics.lower()
                for k in ["assertion", "event", "keyboard", "drag", "timer"]
            ))
        ):
            tier = BudgetTier.COMPLEX_SITE_SECTION
            min_tok, max_tok, target_tok = TIER_TOKEN_RANGES[tier.value]
            kw_str = ", ".join(factors.interaction_keywords[:4])
            explanation = (
                f"Complex site section: interactive patterns ({kw_str}) with "
                f"{len(factors.requested_files)} files; maximum section budget allocated."
            )

        # Interactive site section: interaction or site-specific interactive keywords present
        elif factors.interaction_keywords:
            tier = BudgetTier.INTERACTIVE_SITE_SECTION
            min_tok, max_tok, target_tok = TIER_TOKEN_RANGES[tier.value]
            kw_str = ", ".join(factors.interaction_keywords[:4])
            explanation = (
                f"Interactive site section detected ({kw_str}); "
                "generous budget allocated for live-value logic, controls, and CSS."
            )

        # Simple site section: no interaction keywords
        else:
            tier = BudgetTier.SIMPLE_SITE_SECTION
            min_tok, max_tok, target_tok = TIER_TOKEN_RANGES[tier.value]
            explanation = (
                f"Simple site section ({len(factors.requested_files)} file(s)); "
                "standard multi-file section budget allocated."
            )

    # ── Non-site branches ────────────────────────────────────────────────────

    # Standalone 3D component
    elif factors.has_3d_usage or factors.task_mode == "3d":
        tier = BudgetTier.SCENE_3D
        min_tok, max_tok, target_tok = TIER_TOKEN_RANGES[tier.value]
        explanation = "3D scene detected (Three.js/R3F/canvas/shader); high token budget allocated for scene logic."

    # Complex interaction component
    elif factors.interaction_keywords or (
        factors.repair_diagnostics
        and any(k in factors.repair_diagnostics.lower() for k in ["assertion", "event", "keyboard", "drag", "timer"])
    ):
        tier = BudgetTier.COMPLEX_INTERACTION
        min_tok, max_tok, target_tok = TIER_TOKEN_RANGES[tier.value]
        kw_str = ", ".join(factors.interaction_keywords[:4]) if factors.interaction_keywords else "interaction assertion failures"
        explanation = f"Complex interaction patterns detected ({kw_str}); allocated generous interaction budget."

    # Small targeted patch
    elif (
        factors.task_mode in ("patch", "edit", "fix")
        or (
            factors.repair_diagnostics
            and any(err in factors.repair_diagnostics for err in ["TS2304", "TS2307", "TS2552", "TS2686", "TS2503", "ReferenceError"])
            and not any(f in factors.repair_diagnostics.lower() for f in ["multiple assertion", "test suite failed", "failing assertions: 3", "failing assertions: 4"])
        )
        or (factors.current_file_length > 0 and factors.current_file_length < 800 and factors.task_mode != "site")
    ):
        tier = BudgetTier.SMALL_PATCH
        min_tok, max_tok, target_tok = TIER_TOKEN_RANGES[tier.value]
        # Fine-tune target within range based on current file length
        if factors.current_file_length > 0:
            est_tok = factors.current_file_length // 4
            target_tok = max(min_tok, min(max_tok, est_tok + 300))
        explanation = "Small targeted patch or localized repair detected; allocated compact 512–768 budget to avoid waste."

    # Normal component default
    else:
        tier = BudgetTier.NORMAL_COMPONENT
        min_tok, max_tok, target_tok = TIER_TOKEN_RANGES[tier.value]
        explanation = "Standard single component task; allocated normal 1024–1536 token budget."

    # Context window headroom clamping
    if max_seq_length is None:
        try:
            from agent.config import ModelRuntimeConfig
            max_seq_length = ModelRuntimeConfig.get_max_seq_length()
        except Exception:
            max_seq_length = 8192

    available_headroom = max_seq_length - prompt_tokens
    if available_headroom <= 0:
        clamped_tokens = 1
    else:
        clamped_tokens = max(1, min(target_tok, available_headroom))

    return OutputTokenBudget(
        tier=tier.value,
        min_tokens=min_tok,
        max_tokens=max_tok,
        recommended_tokens=target_tok,
        clamped_tokens=clamped_tokens,
        factors=factors.to_dict(),
        explanation=explanation,
    )


def log_task_budget(budget: OutputTokenBudget, task_name: str = "task") -> None:
    """Log the allocated token budget to stdout."""
    print(budget.log_summary(task_name))



