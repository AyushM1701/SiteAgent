"""
evaluation/diversity_evaluator.py - Automated Anti-Template-Collapse Evaluation System.

Enforces Issue #27 of the SiteAgent Implementation Plan:
1. Automatically measures 10 key design dimensions across batch site generations:
   - hero layout
   - section order
   - font pairing
   - border-radius distribution
   - grid/card structure
   - dark/light choice
   - CTA shape
   - background treatment
   - visual asset type
   - navigation pattern
2. Flags dominant template collapse patterns exceeding the 80% threshold:
   - >80% centered hero
   - >80% three-card features
   - >80% dark gradient
   - >80% pill CTAs
3. Computes statistical diversity metrics:
   - Normalized Shannon Entropy (H_norm in [0.0, 1.0]) per dimension
   - Simpson's Diversity Index (1 - sum(p_i^2)) per dimension
   - Penalized Overall Diversity Score
   - Binary pass/fail diversity gate
"""

import collections
import dataclasses
import math
import re
from typing import Any, Dict, List, Optional, Set, Tuple


HERO_ARCHETYPES = [
    "split_hero",
    "editorial_asymmetric_hero",
    "full_bleed_visual_hero",
    "bento_hero",
    "terminal_data_hero",
    "product_stage_hero",
    "restrained_centered_hero",
]

CANONICAL_HERO_MAP = {
    "split": "split_hero",
    "split_hero": "split_hero",
    "editorial_asymmetric": "editorial_asymmetric_hero",
    "editorial_asymmetric_hero": "editorial_asymmetric_hero",
    "minimal_editorial_hero": "editorial_asymmetric_hero",
    "full_bleed_visual": "full_bleed_visual_hero",
    "full_bleed_visual_hero": "full_bleed_visual_hero",
    "full_bleed_hero": "full_bleed_visual_hero",
    "bento": "bento_hero",
    "bento_hero": "bento_hero",
    "asymmetric_bento_hero": "bento_hero",
    "terminal_data": "terminal_data_hero",
    "terminal_data_hero": "terminal_data_hero",
    "terminal_code_hero": "terminal_data_hero",
    "product_stage": "product_stage_hero",
    "product_stage_hero": "product_stage_hero",
    "restrained_centered": "restrained_centered_hero",
    "restrained_centered_hero": "restrained_centered_hero",
    "centered_hero": "restrained_centered_hero",
}


def get_canonical_hero_archetype(hero_layout: str) -> str:
    """Returns the canonical short archetype name from the 7 balanced archetypes."""
    clean = hero_layout.lower().strip()
    mapped = CANONICAL_HERO_MAP.get(clean, "restrained_centered_hero")
    # Map back to short form
    reverse_map = {
        "split_hero": "split",
        "editorial_asymmetric_hero": "editorial_asymmetric",
        "full_bleed_visual_hero": "full_bleed_visual",
        "bento_hero": "bento",
        "terminal_data_hero": "terminal_data",
        "product_stage_hero": "product_stage",
        "restrained_centered_hero": "restrained_centered",
    }
    return reverse_map.get(mapped, "restrained_centered")


DIVERSITY_DIMENSIONS = [
    "hero_layout",
    "section_order",
    "font_pairing",
    "border_radius_distribution",
    "grid_card_structure",
    "dark_light_choice",
    "cta_shape",
    "background_treatment",
    "visual_asset_type",
    "navigation_pattern",
]

COLLAPSE_PATTERNS = {
    "hero_layout": ("centered_hero", ">80% centered hero"),
    "grid_card_structure": ("three_card_features", ">80% three-card features"),
    "background_treatment": ("dark_gradient", ">80% dark gradient"),
    "cta_shape": ("pill_cta", ">80% pill CTAs"),
}


@dataclasses.dataclass
class SiteDesignSignature:
    """Design signature of an individual website capturing the 10 structural dimensions."""
    task_id: str
    hero_layout: str
    section_order: str
    font_pairing: str
    border_radius_distribution: str
    grid_card_structure: str
    dark_light_choice: str
    cta_shape: str
    background_treatment: str
    visual_asset_type: str
    navigation_pattern: str

    def to_dict(self) -> Dict[str, str]:
        return {
            "task_id": self.task_id,
            "hero_layout": self.hero_layout,
            "section_order": self.section_order,
            "font_pairing": self.font_pairing,
            "border_radius_distribution": self.border_radius_distribution,
            "grid_card_structure": self.grid_card_structure,
            "dark_light_choice": self.dark_light_choice,
            "cta_shape": self.cta_shape,
            "background_treatment": self.background_treatment,
            "visual_asset_type": self.visual_asset_type,
            "navigation_pattern": self.navigation_pattern,
        }


@dataclasses.dataclass
class BatchDiversityReport:
    """Comprehensive statistical diversity and anti-template-collapse report for a batch of sites."""
    total_sites: int
    dimension_distributions: Dict[str, Dict[str, int]]
    dimension_entropies: Dict[str, float]
    dimension_simpson_indices: Dict[str, float]
    dominant_patterns: Dict[str, Dict[str, Any]]
    collapse_flags: List[str]
    overall_diversity_score: float
    is_diverse: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_sites": self.total_sites,
            "dimension_distributions": self.dimension_distributions,
            "dimension_entropies": {k: round(v, 4) for k, v in self.dimension_entropies.items()},
            "dimension_simpson_indices": {k: round(v, 4) for k, v in self.dimension_simpson_indices.items()},
            "dominant_patterns": self.dominant_patterns,
            "collapse_flags": self.collapse_flags,
            "overall_diversity_score": round(self.overall_diversity_score, 4),
            "is_diverse": self.is_diverse,
        }


# ==============================================================================
# Signature Extraction Engine
# ==============================================================================

def _calculate_color_luminance(hex_or_rgb: str) -> float:
    """Calculates perceived relative luminance (0.0=black, 1.0=white)."""
    s = hex_or_rgb.strip().lower()
    if s.startswith("#"):
        s = s[1:]
        if len(s) == 3:
            s = "".join(c * 2 for c in s)
        if len(s) == 6:
            try:
                r = int(s[0:2], 16) / 255.0
                g = int(s[2:4], 16) / 255.0
                b = int(s[4:6], 16) / 255.0
                return 0.2126 * r + 0.7152 * g + 0.0722 * b
            except ValueError:
                pass
    rgb_match = re.search(r"rgb\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)", s)
    if rgb_match:
        r = int(rgb_match.group(1)) / 255.0
        g = int(rgb_match.group(2)) / 255.0
        b = int(rgb_match.group(3)) / 255.0
        return 0.2126 * r + 0.7152 * g + 0.0722 * b
    return 0.1  # default to dark if unparseable


def extract_site_design_signature(
    files: Dict[str, str],
    prompt_spec: Optional[Dict[str, Any]] = None,
    task_id: str = "site",
) -> SiteDesignSignature:
    """
    Extracts the 10 structural design dimensions from a generated website codebase.
    Analyzes TSX/JSX, CSS (:root tokens, rules, media queries), and package.json.
    """
    prompt_spec = prompt_spec or {}
    css_content = " ".join(v for k, v in files.items() if k.endswith(".css"))
    tsx_content = " ".join(v for k, v in files.items() if k.endswith(".tsx") or k.endswith(".ts"))
    app_tsx = next((v for k, v in files.items() if "App.tsx" in k), tsx_content)
    hero_file_key = next((k for k in files.keys() if "hero" in k.lower() and (k.endswith(".tsx") or k.endswith(".css"))), None)
    hero_code = files[hero_file_key] if hero_file_key else app_tsx
    features_code = next((v for k, v in files.items() if "feature" in k.lower()), tsx_content)

    # 1. Hero Layout
    low_hero = hero_code.lower()
    if "split_hero" in low_hero or "hero__split" in low_hero or "split-hero" in low_hero or "split_screen" in low_hero:
        hero_layout = "split_hero"
    elif "product_stage" in low_hero or "product-stage" in low_hero or "plinth" in low_hero or "pedestal" in low_hero or ("stage" in low_hero and "viewport" in low_hero):
        hero_layout = "product_stage_hero"
    elif "terminal_data" in low_hero or "terminal-data" in low_hero or "terminal-window" in low_hero or ("terminal" in low_hero and "prompt" in low_hero):
        hero_layout = "terminal_data_hero"
    elif "editorial" in low_hero or ("font-serif" in low_hero and "text-left" in low_hero) or "editorial_asymmetric" in low_hero:
        hero_layout = "minimal_editorial_hero"
    elif "full-bleed" in low_hero or "bg-cover" in low_hero or "object-cover" in low_hero or "full_bleed" in low_hero:
        hero_layout = "full_bleed_visual_hero"
    elif "bento" in low_hero or ("col-span-2" in low_hero and "row-span-2" in low_hero) or "bento_hero" in low_hero:
        hero_layout = "bento_hero"
    elif "terminal" in low_hero or "monospace" in low_hero or "<pre" in low_hero or "terminal_code" in low_hero:
        hero_layout = "terminal_data_hero"
    elif "grid-cols-2" in low_hero or "1fr 1fr" in low_hero or "lg:flex-row" in low_hero:
        hero_layout = "split_hero"
    elif "restrained" in low_hero or "restrained_centered" in low_hero:
        hero_layout = "restrained_centered_hero"
    elif "text-center" in low_hero or "items-center" in low_hero or "mx-auto" in low_hero or "centered_hero" in low_hero or "hero-center" in low_hero:
        hero_layout = "centered_hero"
    else:
        hero_layout = "centered_hero"

    # 2. Section Order
    # Parse component tags rendered inside App.tsx
    section_tags = re.findall(r"<([A-Z][a-zA-Z0-9]+)\s*/>", app_tsx)
    clean_sections = [
        s.lower() for s in section_tags 
        if s.lower() not in ("fragment", "div", "header", "main", "footer")
    ]
    if not clean_sections:
        clean_sections = prompt_spec.get("required_sections", ["navbar", "hero", "features", "footer"])
    section_order = "->".join(clean_sections[:6])

    # 3. Font Pairing
    heading_font_match = re.search(r"--font-heading\s*:\s*([^;]+);", css_content)
    body_font_match = re.search(r"--font-body\s*:\s*([^;]+);", css_content)

    if heading_font_match:
        h_font = heading_font_match.group(1).split(",")[0].strip("'\" ")
    else:
        h_font_find = re.findall(r"font-family\s*:\s*([^;]+);", css_content)
        h_font = h_font_find[0].split(",")[0].strip("'\" ") if h_font_find else "Inter"

    if body_font_match:
        b_font = body_font_match.group(1).split(",")[0].strip("'\" ")
    else:
        b_font = "Inter"

    font_pairing = f"{h_font} + {b_font}"

    # 4. Border Radius Distribution
    radii_matches = re.findall(r"border-radius\s*:\s*([^;]+);|--radius-[a-z]+\s*:\s*([^;]+);", css_content)
    radii_values = []
    for m in radii_matches:
        v = (m[0] or m[1]).strip()
        radii_values.append(v)

    has_0px = any(r in ("0", "0px") for r in radii_values)
    has_pills = any(r in ("9999px", "50px", "75px", "100px") or "rounded-full" in tsx_content for r in radii_values)
    subtle_count = sum(1 for r in radii_values if re.match(r"^[2-8]px$", r))
    moderate_count = sum(1 for r in radii_values if re.match(r"^(1[0-9]|2[0-4])px$", r))

    if has_0px and not has_pills and subtle_count == 0 and moderate_count == 0:
        border_radius_distribution = "sharp_0px"
    elif has_0px and has_pills:
        border_radius_distribution = "mixed_hybrid"
    elif has_pills and subtle_count == 0:
        border_radius_distribution = "pill_predominant"
    elif moderate_count > subtle_count:
        border_radius_distribution = "moderate_12_20px"
    else:
        border_radius_distribution = "subtle_4_8px"

    # 5. Grid / Card Structure
    low_feat = features_code.lower()
    # Check for card count in features array or mapping
    card_items = re.findall(r"{\s*title\s*:\s*|{\s*icon\s*:\s*|{\s*name\s*:\s*", features_code)
    grid_cols_match = re.search(r"grid-cols-(\d+)", low_feat)

    if "bento" in low_feat or "bento-grid" in low_feat:
        grid_card_structure = "bento_heterogeneous"
    elif "tabs" in low_feat or "tablist" in low_feat or "activetab" in low_feat:
        grid_card_structure = "tabs_switcher"
    elif "timeline" in low_feat or "milestone" in low_feat:
        grid_card_structure = "timeline_vertical"
    elif "carousel" in low_feat or "slider" in low_feat:
        grid_card_structure = "carousel_slider"
    elif len(card_items) == 3 or (grid_cols_match and grid_cols_match.group(1) == "3" and len(card_items) <= 3):
        grid_card_structure = "three_card_features"
    elif len(card_items) == 4 or (grid_cols_match and grid_cols_match.group(1) == "4"):
        grid_card_structure = "four_card_grid"
    elif len(card_items) >= 6 or (grid_cols_match and grid_cols_match.group(1) == "3" and len(card_items) >= 6):
        grid_card_structure = "six_card_grid"
    elif len(card_items) == 2 or (grid_cols_match and grid_cols_match.group(1) == "2"):
        grid_card_structure = "two_column_split"
    elif len(card_items) == 3:
        grid_card_structure = "three_card_features"
    else:
        grid_card_structure = "three_card_features" if "3" in low_feat else "four_card_grid"

    # 6. Dark / Light Choice
    bg_token_match = re.search(r"--color-bg\s*:\s*([^;]+);|--color-background\s*:\s*([^;]+);", css_content)
    if bg_token_match:
        raw_bg = (bg_token_match.group(1) or bg_token_match.group(2)).strip()
        lum = _calculate_color_luminance(raw_bg)
    else:
        body_bg_match = re.search(r"body\s*{[^}]*background(?:-color)?\s*:\s*([^;]+);", css_content)
        if body_bg_match:
            lum = _calculate_color_luminance(body_bg_match.group(1))
        else:
            lum = 0.05 if any(k in css_content.lower() for k in ("#0f172a", "#0a0e17", "#050508", "#0d1117", "#121212")) else 0.9

    if any(c in css_content.lower() for c in ("#fcfbf7", "#f8f6f0", "#faf7f2", "#f5f3ec", "alabaster", "cream", "warm")):
        dark_light_choice = "warm_neutral"
    elif lum < 0.20:
        dark_light_choice = "dark"
    elif lum > 0.85:
        dark_light_choice = "light"
    elif any(c in css_content for c in ("#000000", "#000", "#ffffff", "#fff")):
        dark_light_choice = "high_contrast_mono"
    else:
        dark_light_choice = "dark" if lum < 0.50 else "light"

    # 7. CTA Shape
    cta_radius_match = re.search(r"--radius-buttons\s*:\s*([^;]+);", css_content)
    btn_radius_match = re.search(r"\.btn[^{]*{[^}]*border-radius\s*:\s*([^;]+);", css_content)
    raw_cta_rad = ""
    if cta_radius_match:
        raw_cta_rad = cta_radius_match.group(1).strip()
    elif btn_radius_match:
        raw_cta_rad = btn_radius_match.group(1).strip()

    if raw_cta_rad in ("9999px", "50px", "75px", "100px") or "rounded-full" in tsx_content:
        cta_shape = "pill_cta"
    elif raw_cta_rad in ("0", "0px") or "rounded-none" in tsx_content:
        cta_shape = "sharp_square_cta"
    elif re.match(r"^[2-8]px$", raw_cta_rad) or "rounded-md" in tsx_content or "rounded " in tsx_content:
        cta_shape = "rounded_subtle_cta"
    elif re.match(r"^(1[0-9]|2[0-4])px$", raw_cta_rad) or "rounded-xl" in tsx_content or "rounded-2xl" in tsx_content:
        cta_shape = "rounded_curved_cta"
    elif "underline" in tsx_content and "btn" not in tsx_content:
        cta_shape = "underline_minimal_cta"
    else:
        cta_shape = "pill_cta" if "pill" in css_content else "rounded_subtle_cta"

    # 8. Background Treatment
    low_css = css_content.lower()
    if "backdrop-filter" in low_css and "blur" in low_css:
        background_treatment = "glassmorphism_blur"
    elif "radial-gradient(circle" in low_css or "grid_mesh" in low_css or "grid-mesh" in low_css:
        background_treatment = "grid_mesh"
    elif "linear-gradient" in low_css or "radial-gradient" in low_css:
        if any(w in low_css for w in ("aurora", "cyan", "purple", "pink", "lime", "glow")):
            background_treatment = "aurora_vibrant"
        else:
            background_treatment = "dark_gradient"
    elif "mesh" in low_css or ("dot" in low_css and "background" in low_css):
        background_treatment = "grid_mesh"
    else:
        background_treatment = "solid_flat"

    # 9. Visual Asset Type
    low_tsx = tsx_content.lower()
    pkg_content = next((v for k, v in files.items() if "package.json" in k), "").lower()
    if "<canvas" in low_tsx or "from 'three'" in low_tsx or 'from "three"' in low_tsx or "webgl" in low_tsx:
        visual_asset_type = "three_d_canvas"
    elif "unsplash.com" in low_tsx or "pexels.com" in low_tsx or "<img" in low_tsx:
        visual_asset_type = "real_photography"
    elif "slider" in low_tsx or "calculator" in low_tsx or "quiz" in low_tsx:
        visual_asset_type = "interactive_simulator"
    elif ("lucide-react" in low_tsx or "lucide-react" in pkg_content) and "<img" not in low_tsx:
        visual_asset_type = "lucide_svg_icons"
    else:
        visual_asset_type = "abstract_geometric"

    # 10. Navigation Pattern
    low_nav = (next((v for k, v in files.items() if "Navbar" in k or "Header" in k or "Nav." in k), app_tsx)).lower()
    if "rounded-full" in low_nav or "island" in low_nav or "floating" in low_nav or ("sticky" in low_nav and "max-w-" in low_nav):
        navigation_pattern = "sticky_floating_island"
    elif "sidebar" in low_nav or "dock" in low_nav:
        navigation_pattern = "sidebar_dock"
    elif "masthead" in low_nav or "edition" in low_nav or "editorial" in low_nav:
        navigation_pattern = "split_masthead"
    elif "w-full" in low_nav and ("border-b" in low_nav or "border-border" in low_nav):
        navigation_pattern = "full_width_banner"
    elif "hamburger" in low_nav or "menu" in low_nav:
        navigation_pattern = "minimal_sparse"
    else:
        navigation_pattern = "full_width_banner"

    return SiteDesignSignature(
        task_id=task_id,
        hero_layout=hero_layout,
        section_order=section_order,
        font_pairing=font_pairing,
        border_radius_distribution=border_radius_distribution,
        grid_card_structure=grid_card_structure,
        dark_light_choice=dark_light_choice,
        cta_shape=cta_shape,
        background_treatment=background_treatment,
        visual_asset_type=visual_asset_type,
        navigation_pattern=navigation_pattern,
    )


# ==============================================================================
# Anti-Template-Collapse Statistical Evaluator
# ==============================================================================

class AntiTemplateCollapseEvaluator:
    """
    Evaluates design diversity across a batch of site signatures,
    calculates normalized entropy and Simpson diversity index per dimension,
    and flags critical template collapse patterns.
    """

    def __init__(self, collapse_threshold: float = 0.80):
        self.collapse_threshold = collapse_threshold

    def compute_normalized_entropy(self, counts: Dict[str, int], total_n: int) -> float:
        """
        Computes normalized Shannon entropy H_norm in [0.0, 1.0].
        0.0 = total collapse (all sites identical).
        1.0 = maximum possible diversity across observed categories.
        """
        if total_n <= 1 or not counts:
            return 1.0
        k = len(counts)
        if k <= 1:
            return 0.0

        entropy = 0.0
        for count in counts.values():
            if count > 0:
                p = count / total_n
                entropy -= p * math.log2(p)

        max_entropy = math.log2(k)
        return min(1.0, max(0.0, entropy / max_entropy))

    def compute_simpson_index(self, counts: Dict[str, int], total_n: int) -> float:
        """
        Computes Gini-Simpson diversity index: 1 - sum(p_i^2) in [0.0, 1.0].
        Represents the probability that two randomly selected sites have different designs.
        """
        if total_n <= 1 or not counts:
            return 1.0
        sum_p_squared = sum((cnt / total_n) ** 2 for cnt in counts.values())
        return min(1.0, max(0.0, 1.0 - sum_p_squared))

    def evaluate_batch(
        self,
        signatures: List[SiteDesignSignature],
        collapse_threshold: Optional[float] = None,
    ) -> BatchDiversityReport:
        """Evaluates a batch of site signatures and generates a comprehensive diversity report."""
        threshold = collapse_threshold if collapse_threshold is not None else self.collapse_threshold
        n = len(signatures)

        if n == 0:
            return BatchDiversityReport(
                total_sites=0,
                dimension_distributions={},
                dimension_entropies={dim: 0.0 for dim in DIVERSITY_DIMENSIONS},
                dimension_simpson_indices={dim: 0.0 for dim in DIVERSITY_DIMENSIONS},
                dominant_patterns={},
                collapse_flags=[],
                overall_diversity_score=0.0,
                is_diverse=False,
            )

        distributions: Dict[str, Dict[str, int]] = {}
        entropies: Dict[str, float] = {}
        simpson_indices: Dict[str, float] = {}
        dominant_patterns: Dict[str, Dict[str, Any]] = {}
        collapse_flags: List[str] = []

        # 1. Calculate distributions, entropies, and dominant patterns
        for dim in DIVERSITY_DIMENSIONS:
            values = [getattr(sig, dim) for sig in signatures]
            counts = dict(collections.Counter(values))
            distributions[dim] = counts

            entropies[dim] = round(self.compute_normalized_entropy(counts, n), 4)
            simpson_indices[dim] = round(self.compute_simpson_index(counts, n), 4)

            # Find dominant pattern
            top_val, top_cnt = max(counts.items(), key=lambda item: item[1])
            top_ratio = top_cnt / n
            dominant_patterns[dim] = {
                "pattern": top_val,
                "count": top_cnt,
                "percentage": round(top_ratio * 100.0, 1),
            }

            # Check for general >80% collapse in this dimension
            if n >= 5 and top_ratio > threshold:
                collapse_flags.append(f"COLLAPSE_FLAG: {top_ratio:.1%} {dim}='{top_val}' (threshold: {threshold:.0%})")

        # 2. Check for the four required target collapse patterns specifically + generalized hero collapse
        for dim, (target_val, flag_label) in COLLAPSE_PATTERNS.items():
            counts = distributions.get(dim, {})
            target_cnt = counts.get(target_val, 0)
            if target_val == "centered_hero":
                target_cnt += counts.get("restrained_centered_hero", 0)
            ratio = target_cnt / n
            if n >= 5 and ratio > threshold:
                spec_flag = f"COLLAPSE_FLAG: {flag_label} ({ratio:.1%} > {threshold:.0%})"
                if spec_flag not in collapse_flags:
                    collapse_flags.append(spec_flag)

        # Ensure NO single hero archetype dominates >80% (Section 3.B: Balance layout archetypes)
        hero_counts = distributions.get("hero_layout", {})
        for h_val, h_cnt in hero_counts.items():
            h_ratio = h_cnt / n
            if n >= 5 and h_ratio > threshold:
                canon_name = get_canonical_hero_archetype(h_val).replace("_", " ")
                arch_flag = f"COLLAPSE_FLAG: >{threshold:.0%} {canon_name} hero ({h_ratio:.1%} > {threshold:.0%})"
                if arch_flag not in collapse_flags and not ("centered" in h_val and any(">80% centered hero" in f for f in collapse_flags)):
                    collapse_flags.append(arch_flag)

        # 3. Overall Diversity Score calculation
        # Base score is the mean of the normalized Shannon entropies
        mean_entropy = sum(entropies.values()) / len(entropies)

        # Apply penalty for each collapse flag triggered:
        # Each collapse flag reduces overall diversity score by 20%
        penalty_factor = max(0.1, 1.0 - (0.20 * len(collapse_flags)))
        overall_score = round(min(1.0, max(0.0, mean_entropy * penalty_factor)), 4)

        # 4. Diversity Gate Decision
        # Requires overall score >= 0.60 and zero severe collapse flags
        is_diverse = overall_score >= 0.60 and len(collapse_flags) == 0

        return BatchDiversityReport(
            total_sites=n,
            dimension_distributions=distributions,
            dimension_entropies=entropies,
            dimension_simpson_indices=simpson_indices,
            dominant_patterns=dominant_patterns,
            collapse_flags=collapse_flags,
            overall_diversity_score=overall_score,
            is_diverse=is_diverse,
        )


def evaluate_site_batch_diversity(
    signatures: List[SiteDesignSignature],
    collapse_threshold: float = 0.80,
) -> BatchDiversityReport:
    """Public helper to evaluate a batch of site signatures."""
    evaluator = AntiTemplateCollapseEvaluator(collapse_threshold=collapse_threshold)
    return evaluator.evaluate_batch(signatures)
