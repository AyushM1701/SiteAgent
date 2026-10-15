"""
style_ingest.py - Design System Ingestion & Style Conformance Engine for ReactAgent SLM

Decouples visual aesthetic and design tokens from business domain heuristics.
Parses Refero-style design systems (e.g. styles.refero.design), custom :root CSS blocks,
and Tailwind @theme definitions into structured StyleSpec objects with zero LLM cost.
Enforces strict token compliance during multi-turn agent generation.
"""

import colorsys
import html
import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, Set, Union


@dataclass
class StyleSpec:
    """Complete, machine-verifiable design system specification."""
    name: str
    colors: Dict[str, str] = field(default_factory=dict)         # --color-* and --gradient-*
    fonts: Dict[str, str] = field(default_factory=dict)          # --font-* families
    type_scale: Dict[str, str] = field(default_factory=dict)     # --text-* and --leading-*
    spacing_scale: Dict[str, str] = field(default_factory=dict)  # --spacing-*
    radius: Dict[str, str] = field(default_factory=dict)         # --radius-*
    surfaces: Dict[str, str] = field(default_factory=dict)       # --surface-*
    layout: Dict[str, str] = field(default_factory=dict)         # --page-max-width, --section-gap, etc.
    other_tokens: Dict[str, str] = field(default_factory=dict)   # Any other custom CSS properties
    semantic_tokens: Dict[str, str] = field(default_factory=dict) # semantic color/elevation aliases
    motion_tokens: Dict[str, str] = field(default_factory=dict)   # duration/easing/stagger tokens
    icon_art_direction: str = "outline-round"
    raw_css: str = ""                                            # Complete verbatim :root block
    dos: List[str] = field(default_factory=list)                 # Positive design guidelines
    donts: List[str] = field(default_factory=list)               # Hard aesthetic constraints
    parse_warnings: List[str] = field(default_factory=list)      # Warnings about unparsed rules/sections
    source: str = "custom"                                       # "refero" | "preset" | "custom" | "heuristic"

    def get_primary_color(self) -> str:
        """Heuristically resolves a primary background or brand color for backwards compatibility."""
        for key in ["--surface-obsidian", "--color-obsidian", "--surface-primary", "--color-primary", "--color-background", "--surface-paper"]:
            if key in self.colors or key in self.surfaces:
                return self.colors.get(key) or self.surfaces.get(key)
        if self.colors:
            return next(iter(self.colors.values()))
        return "#090d16"

    def get_accent_color(self) -> str:
        """Heuristically resolves an accent color for CTAs and highlights."""
        for key in ["--color-iridescent-fade", "--color-accent", "--color-primary", "--color-brand", "--gradient-iridescent-fade"]:
            if key in self.colors:
                val = self.colors[key]
                if not val.startswith("linear-gradient"):
                    return val
        for key, val in self.colors.items():
            if "fade" in key or "accent" in key or "highlight" in key:
                if not val.startswith("linear-gradient"):
                    return val
        return "#38bdf8"

    def get_heading_font(self) -> str:
        for key in ["--font-heading", "--font-roobert", "--font-cinzel", "--font-space-grotesk", "--font-raleway"]:
            if key in self.fonts:
                return self.fonts[key].split(",")[0].strip("'\" ")
        if self.fonts:
            return next(iter(self.fonts.values())).split(",")[0].strip("'\" ")
        return "Inter"

    def get_body_font(self) -> str:
        for key in ["--font-body", "--font-raleway", "--font-inter", "--font-system-ui"]:
            if key in self.fonts:
                return self.fonts[key].split(",")[0].strip("'\" ")
        return "Inter"


# ==============================================================================
# 1. Zero-LLM CSS Custom Property Parser
# ==============================================================================

def parse_css_tokens(css_text: str, name: str = "Custom Design Tokens", source: str = "custom") -> StyleSpec:
    """
    Extracts CSS custom properties (--var-name: value;) from a raw :root { ... } or CSS block.
    Categorizes them deterministically into colors, fonts, scales, radii, and layout.
    Also extracts bulleted do's and don'ts if present in surrounding markdown.
    """
    spec = StyleSpec(name=name, source=source)
    spec.raw_css = css_text.strip()

    # Regex matches CSS custom property pairs: --name: value;
    prop_pattern = re.compile(r'(--[\w-]+)\s*:\s*([^;]+);')
    matches = prop_pattern.findall(css_text)

    for prop_name, prop_val in matches:
        prop_name = prop_name.strip()
        prop_val = prop_val.strip()

        # Categorize
        if prop_name.startswith(("--color-", "--gradient-")):
            spec.colors[prop_name] = prop_val
        elif prop_name.startswith("--font-"):
            spec.fonts[prop_name] = prop_val
        elif prop_name.startswith(("--text-", "--leading-", "--tracking-", "--step-")):
            spec.type_scale[prop_name] = prop_val
        elif prop_name.startswith("--spacing-"):
            spec.spacing_scale[prop_name] = prop_val
        elif prop_name.startswith("--radius-"):
            spec.radius[prop_name] = prop_val
        elif prop_name.startswith("--surface-"):
            spec.surfaces[prop_name] = prop_val
        elif prop_name.startswith(("--duration-", "--ease-", "--stagger")):
            spec.motion_tokens[prop_name] = prop_val
        elif prop_name.startswith(("--canvas", "--surface-", "--text-", "--border-", "--accent", "--on-accent", "--focus-ring", "--shadow-", "--glass-", "--noise-")):
            spec.semantic_tokens[prop_name] = prop_val
        elif prop_name in ("--page-max-width", "--section-gap", "--card-padding", "--element-gap", "--gutter", "--content-width", "--measure"):
            spec.layout[prop_name] = prop_val
        else:
            # Fallback categorization by name keywords
            if "color" in prop_name or prop_val.startswith(("#", "rgb", "hsl")):
                spec.colors[prop_name] = prop_val
            elif "radius" in prop_name:
                spec.radius[prop_name] = prop_val
            elif "font" in prop_name:
                spec.fonts[prop_name] = prop_val
            else:
                spec.other_tokens[prop_name] = prop_val

    # Parse Do's and Don'ts from markdown text if present
    do_pattern = re.compile(r'(?:Do\'?s?|Always|Required):\s*(.*?)(?=(?:Don\'?ts?|Never|Avoid|$))', re.DOTALL | re.IGNORECASE)
    dont_pattern = re.compile(r'(?:Don\'?ts?|Never|Avoid):\s*(.*?)(?=(?:Do\'?s?|Always|Required|$))', re.DOTALL | re.IGNORECASE)

    do_match = do_pattern.search(css_text)
    if do_match:
        items = re.findall(r'[-*•]\s*([^\n\r]+)', do_match.group(1))
        spec.dos.extend([item.strip() for item in items if item.strip()])

    dont_match = dont_pattern.search(css_text)
    if dont_match:
        items = re.findall(r'[-*•]\s*([^\n\r]+)', dont_match.group(1))
        spec.donts.extend([item.strip() for item in items if item.strip()])

    # Detect unparsed instructional prose outside :root { ... }
    text_outside_root = re.sub(r'(:root|@theme)\s*\{[^}]*\}', '', css_text, flags=re.DOTALL | re.IGNORECASE)
    text_outside_root = re.sub(r'[^{}]*\{[^{}]*\}', '', text_outside_root, flags=re.DOTALL)
    text_outside_root = re.sub(r'/\*\s*(?:colors|typography|fonts|spacing|radius|surfaces|layout|tokens)\s*\*/', '', text_outside_root, flags=re.IGNORECASE)
    has_prose = bool(re.search(r'[A-Za-z]{3,}', text_outside_root))

    if has_prose and not spec.dos and not spec.donts:
        spec.parse_warnings.append(
            "Could not detect explicit Do's/Don'ts sections in the pasted design system — "
            "only the generic default constraint was applied. Consider using 'Do's:'/'Don'ts:' "
            "headers if you have specific rules."
        )

    # Default guardrail constraints if none explicitly parsed
    if not spec.donts:
        spec.donts.append("Never hardcode raw hex, rgb, or hsl values; use var(--color-*) or var(--surface-*) exclusively.")
    if "--radius-buttons" in spec.radius:
        spec.dos.append(f"Buttons must strictly use var(--radius-buttons) ({spec.radius['--radius-buttons']}).")
    if "--radius-cards" in spec.radius and spec.radius["--radius-cards"] in ("0", "0px"):
        spec.donts.append("Cards and imagery containers must strictly use 0px border-radius (sharp corners).")

    return spec


# ==============================================================================
# 2. Curated Design System Archetype Presets
# ==============================================================================

# 1. Monopo Saigon / Refero Obsidian & Iridescent Fade (The user's exact specification)
_REFERO_EDITORIAL_CSS = """
:root {
  /* Colors */
  --color-obsidian: #000000;
  --color-paper: #ffffff;
  --color-inkstone: #181818;
  --color-felt-gray: #6d6d6d;
  --color-slate-pill: #636363;
  --color-ash-mist: #9a9a9a;
  --color-pewter: #808080;
  --color-iridescent-fade: #a02d25;
  --gradient-iridescent-fade: linear-gradient(90deg, rgb(160, 224, 171), rgb(255, 172, 46) 50%, rgb(165, 45, 37));

  /* Typography — Font Families */
  --font-roobert: 'Roobert', ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  --font-raleway: 'Raleway', ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  --font-system-ui: 'system-ui', ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;

  /* Typography — Scale */
  --text-caption: 12px;
  --leading-caption: 1.19;
  --text-body-sm: 16px;
  --leading-body-sm: 1.15;
  --text-body: 18px;
  --leading-body: 1.21;
  --text-subheading: 39px;
  --leading-subheading: 1.19;
  --text-subheading-lg: 45px;
  --leading-subheading-lg: 1.15;
  --text-heading-sm: 54px;
  --leading-heading-sm: 1.39;
  --text-heading: 78px;
  --leading-heading: 1.1;
  --text-heading-lg: 94px;
  --leading-heading-lg: 0.76;
  --text-display: 225px;
  --leading-display: 1.25;

  /* Typography — Weights */
  --font-weight-light: 300;
  --font-weight-regular: 400;
  --font-weight-semibold: 600;

  /* Spacing */
  --spacing-unit: 4px;
  --spacing-8: 8px;
  --spacing-12: 12px;
  --spacing-28: 28px;
  --spacing-40: 40px;
  --spacing-48: 48px;
  --spacing-64: 64px;
  --spacing-68: 68px;
  --spacing-152: 152px;

  /* Layout */
  --page-max-width: 1078px;
  --section-gap: 46px;
  --card-padding: 34px;
  --element-gap: 14px;

  /* Border Radius */
  --radius-lg: 10px;
  --radius-full: 75.024px;

  /* Named Radii */
  --radius-tags: 75px;
  --radius-cards: 0px;
  --radius-images: 0px;
  --radius-inputs: 0px;
  --radius-buttons: 75px;

  /* Surfaces */
  --surface-paper: #ffffff;
  --surface-slate-pill: #636363;
  --surface-obsidian: #000000;
  --surface-ash-mist: #9a9a9a;
}
"""

_NEO_BRUTALIST_CSS = """
:root {
  /* Colors */
  --color-bg: #fffbf0;
  --color-surface: #ffffff;
  --color-border: #000000;
  --color-text: #000000;
  --color-accent-yellow: #fde047;
  --color-accent-cyan: #38bdf8;
  --color-accent-pink: #f472b6;
  --color-muted: #e2e8f0;

  /* Typography */
  --font-heading: 'Space Grotesk', system-ui, sans-serif;
  --font-body: 'Space Grotesk', system-ui, sans-serif;
  --font-mono: 'Courier New', monospace;

  /* Brutalist Shadows & Borders */
  --border-width: 3px;
  --border-solid: 3px solid #000000;
  --shadow-hard: 4px 4px 0px #000000;
  --shadow-hard-lg: 8px 8px 0px #000000;

  /* Border Radii */
  --radius-buttons: 0px;
  --radius-cards: 0px;
  --radius-inputs: 0px;
  --radius-tags: 0px;

  /* Spacing */
  --page-max-width: 1200px;
  --section-gap: 56px;
  --card-padding: 28px;
}
"""

_GLASSMORPHIC_AURORA_CSS = """
:root {
  /* Deep Night & Aurora Colors */
  --color-bg: #070913;
  --color-surface: rgba(255, 255, 255, 0.05);
  --color-surface-hover: rgba(255, 255, 255, 0.09);
  --color-border: rgba(255, 255, 255, 0.12);
  --color-text: #f8fafc;
  --color-text-muted: #94a3b8;
  --color-accent-cyan: #38bdf8;
  --color-accent-purple: #818cf8;
  --gradient-aurora: linear-gradient(135deg, #38bdf8 0%, #818cf8 50%, #c084fc 100%);
  --gradient-glow: radial-gradient(circle at 50% 0%, rgba(56, 189, 248, 0.15), transparent 70%);

  /* Typography */
  --font-heading: 'Plus Jakarta Sans', system-ui, sans-serif;
  --font-body: 'Inter', system-ui, sans-serif;

  /* Glass Effects */
  --glass-blur: blur(16px);
  --glass-border: 1px solid rgba(255, 255, 255, 0.12);
  --glass-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);

  /* Border Radii */
  --radius-buttons: 9999px;
  --radius-cards: 20px;
  --radius-inputs: 12px;
  --radius-tags: 9999px;

  /* Spacing */
  --page-max-width: 1140px;
  --section-gap: 64px;
  --card-padding: 32px;
}
"""

_LUXURY_MINIMALIST_CSS = """
:root {
  /* Warm Alabaster & Bronze Colors */
  --color-bg: #f9f8f6;
  --color-surface: #ffffff;
  --color-surface-alt: #f1ede6;
  --color-border: #e6e0d4;
  --color-text: #1a1918;
  --color-text-muted: #6b665f;
  --color-bronze: #8c6d48;
  --color-bronze-dark: #634d31;

  /* Typography */
  --font-heading: 'Cinzel', 'Playfair Display', serif;
  --font-body: 'Inter', system-ui, sans-serif;

  /* Border Radii */
  --radius-buttons: 2px;
  --radius-cards: 0px;
  --radius-inputs: 2px;
  --radius-tags: 2px;

  /* Layout */
  --page-max-width: 1040px;
  --section-gap: 72px;
  --card-padding: 36px;
}
"""

_CYBERPUNK_NEON_CSS = """
:root {
  /* High-Voltage Cyberpunk Colors */
  --color-bg: #050508;
  --color-surface: #0e0e17;
  --color-border: #222235;
  --color-text: #f0f0f5;
  --color-text-muted: #757590;
  --color-neon-lime: #a3e635;
  --color-neon-pink: #f43f5e;
  --color-neon-cyan: #06b6d4;
  --gradient-cyber: linear-gradient(90deg, #a3e635 0%, #06b6d4 100%);

  /* Typography */
  --font-heading: 'Space Grotesk', monospace, sans-serif;
  --font-body: 'Inter', system-ui, sans-serif;

  /* Border Radii */
  --radius-buttons: 4px;
  --radius-cards: 6px;
  --radius-inputs: 4px;
  --radius-tags: 2px;

  /* Layout */
  --page-max-width: 1180px;
  --section-gap: 60px;
  --card-padding: 28px;
}
"""

_MINIMAL_CSS = """
:root {
  /* Ultra-Clean Minimalist Palette */
  --color-bg: #fafafa;
  --color-surface: #ffffff;
  --color-surface-alt: #f4f4f5;
  --color-border: #e4e4e7;
  --color-border-subtle: #f4f4f5;
  --color-text: #09090b;
  --color-text-muted: #71717a;
  --color-accent: #18181b;
  --color-accent-subtle: #f4f4f5;

  /* Typography */
  --font-heading: 'Inter', system-ui, -apple-system, sans-serif;
  --font-body: 'Inter', system-ui, -apple-system, sans-serif;

  /* Border Radii */
  --radius-buttons: 6px;
  --radius-cards: 8px;
  --radius-inputs: 6px;
  --radius-tags: 9999px;

  /* Layout */
  --page-max-width: 1100px;
  --section-gap: 64px;
  --card-padding: 28px;
  --shadow-subtle: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
}
"""

_TECHNICAL_CSS = """
:root {
  /* Precision Engineering & Developer Palette */
  --color-bg: #0d1117;
  --color-surface: #161b22;
  --color-surface-alt: #21262d;
  --color-border: #30363d;
  --color-border-subtle: #21262d;
  --color-text: #f0f6fc;
  --color-text-muted: #8b949e;
  --color-accent: #2f81f7;
  --color-accent-emerald: #2ea043;
  --color-accent-amber: #d29922;

  /* Typography */
  --font-heading: 'JetBrains Mono', 'Fira Code', monospace;
  --font-body: 'Inter', system-ui, -apple-system, sans-serif;

  /* Border Radii */
  --radius-buttons: 4px;
  --radius-cards: 6px;
  --radius-inputs: 4px;
  --radius-tags: 4px;

  /* Layout */
  --page-max-width: 1200px;
  --section-gap: 56px;
  --card-padding: 24px;
}
"""


def _build_preset_spec(name: str, css_text: str, dos: List[str], donts: List[str]) -> StyleSpec:
    spec = parse_css_tokens(css_text, name=name, source="preset")
    spec.dos = dos
    spec.donts = donts
    return spec


_EDITORIAL_SPEC = _build_preset_spec(
    name="Refero Editorial Monochrome (Monopo Saigon)",
    css_text=_REFERO_EDITORIAL_CSS,
    dos=[
        "Use var(--color-obsidian) for deep backgrounds, var(--color-paper) for clean contrast.",
        "Buttons must strictly use pill radius: border-radius: var(--radius-buttons); (75px).",
        "Hero accent badges, key CTAs, and active hover underlines must use var(--color-iridescent-fade) or var(--gradient-iridescent-fade).",
        "Use var(--font-roobert) or var(--font-raleway) with elegant generous line heights.",
    ],
    donts=[
        "Never use box-shadow or elevation blur; the design relies purely on crisp color contrast.",
        "Never set border-radius between 1px and 74px on buttons or cards.",
        "Cards, image wrappers, and inputs must strictly have 0px border-radius (border-radius: var(--radius-cards);).",
        "Never hardcode hex values like #000000 or #ffffff; use var(--color-*) tokens exclusively.",
    ]
)

_BRUTALIST_SPEC = _build_preset_spec(
    name="Neo-Brutalist High Contrast",
    css_text=_NEO_BRUTALIST_CSS,
    dos=[
        "All cards, buttons, and badges MUST have a solid black outline: border: var(--border-solid);",
        "Interactive buttons and cards MUST have hard drop shadows: box-shadow: var(--shadow-hard);",
        "Use vibrant punchy accent fills: var(--color-accent-yellow) or var(--color-accent-cyan).",
        "Hover states should translate: transform: translate(-2px, -2px); box-shadow: 6px 6px 0px #000;",
    ],
    donts=[
        "Never use rounded corners or border-radius > 0px.",
        "Never use blurry, diffuse box-shadows or gradients.",
        "Never use low-contrast gray text; keep typography bold black (#000000).",
    ]
)

_GLASSMORPHIC_SPEC = _build_preset_spec(
    name="Glassmorphic Aurora Night",
    css_text=_GLASSMORPHIC_AURORA_CSS,
    dos=[
        "Cards and navigation must use frosted glass surfaces: background: var(--color-surface); backdrop-filter: var(--glass-blur); border: var(--glass-border);",
        "Hero headings and primary action buttons should use var(--gradient-aurora) with pill radius.",
        "Use generous card radii: border-radius: var(--radius-cards); (20px).",
    ],
    donts=[
        "Never use 100% opaque solid white card backgrounds.",
        "Never use sharp 0px corners on interactive cards or pills.",
    ]
)

_LUXURY_SPEC = _build_preset_spec(
    name="Luxury Minimalist Champagne & Bronze",
    css_text=_LUXURY_MINIMALIST_CSS,
    dos=[
        "Use warm, calming alabaster paper background: var(--color-bg).",
        "Headings must use refined serif typography with generous tracking (letter-spacing: 0.04em).",
        "Accents, divider lines, and fine details must use var(--color-bronze).",
    ],
    donts=[
        "Never use bright neon or saturated colors.",
        "Never use heavy drop shadows.",
        "Never use rounded pill buttons; keep edges sharp (0px - 2px).",
    ]
)

_CYBERPUNK_SPEC = _build_preset_spec(
    name="Cyberpunk Neon Terminal",
    css_text=_CYBERPUNK_NEON_CSS,
    dos=[
        "Deepest pitch black background (#050508) with high-voltage neon lime and cyan accents.",
        "Buttons and metric badges use neon borders and subtle terminal glow.",
        "Use monospaced numbers and technical uppercase subheadings.",
    ],
    donts=[
        "Never use pastel or earthy muted colors.",
        "Never use soft serif fonts.",
    ]
)

_MINIMAL_SPEC = _build_preset_spec(
    name="Clean Minimal Modernist",
    css_text=_MINIMAL_CSS,
    dos=[
        "Prioritize ample whitespace, generous margins, and distraction-free layout rhythm.",
        "Use 1px subtle hairline borders: border: 1px solid var(--color-border);",
        "Keep buttons and inputs understated with clean subtle radii: var(--radius-buttons);",
        "Typography should remain clean, crisp, and high-legibility sans-serif.",
    ],
    donts=[
        "Never use garish neon accents or chaotic decorative gradients.",
        "Never use heavy drop shadows or diffuse blur filters.",
        "Never crowd cards or eliminate breathing room.",
    ]
)

_TECHNICAL_SPEC = _build_preset_spec(
    name="Technical Engineering Precision",
    css_text=_TECHNICAL_CSS,
    dos=[
        "Use developer-grade dark background (var(--color-bg)) with crisp border grid definition.",
        "Use monospace typography for headings, metrics, status pills, and numeric figures.",
        "Primary interactions and active links use precision engineer blue (var(--color-accent)).",
        "Status badges and telemetry indicators use emerald and amber accents.",
    ],
    donts=[
        "Never use decorative script or soft serif fonts.",
        "Never use blurry, diffuse shadows or rounded pill shapes.",
        "Never use pastel or washed-out text colors.",
    ]
)


PRESET_STYLES: Dict[str, StyleSpec] = {
    # Canonical structured names
    "editorial": _EDITORIAL_SPEC,
    "brutalist": _BRUTALIST_SPEC,
    "minimal": _MINIMAL_SPEC,
    "technical": _TECHNICAL_SPEC,
    "luxury": _LUXURY_SPEC,
    "experimental": _GLASSMORPHIC_SPEC,

    # Backwards-compatible legacy names
    "refero_editorial": _EDITORIAL_SPEC,
    "neo_brutalist": _BRUTALIST_SPEC,
    "glassmorphic_aurora": _GLASSMORPHIC_SPEC,
    "luxury_minimalist": _LUXURY_SPEC,
    "cyberpunk_neon": _CYBERPUNK_SPEC,
}


def get_available_style_presets() -> List[Dict[str, Any]]:
    """
    Returns the authoritative list of supported structured style presets for UI & metadata selection.
    Includes the 8 canonical styles: Auto, Editorial, Brutalist, Minimal, Technical, Luxury, Experimental, Custom.
    """
    return [
        {
            "id": "auto",
            "label": "Auto",
            "description": "Smart domain-tailored aesthetic automatically chosen based on website intent.",
            "isDefault": True,
        },
        {
            "id": "editorial",
            "label": "Editorial",
            "description": "Sophisticated typographic hierarchy, high-contrast monochrome, and refined spacing.",
        },
        {
            "id": "brutalist",
            "label": "Brutalist",
            "description": "Bold high-contrast borders, punchy saturated accents, and stark geometric layouts.",
        },
        {
            "id": "minimal",
            "label": "Minimal",
            "description": "Ultra-clean whitespace, crisp subtle borders, and distraction-free clarity.",
        },
        {
            "id": "technical",
            "label": "Technical",
            "description": "Developer-grade dark theme, monospace accents, and precision engineering telemetry.",
        },
        {
            "id": "luxury",
            "label": "Luxury",
            "description": "Warm alabaster, bronze metallic accents, and elegant serif typography.",
        },
        {
            "id": "experimental",
            "label": "Experimental",
            "description": "Dynamic aurora gradients, luminous glass surfaces, and futuristic visual elements.",
        },
        {
            "id": "custom",
            "label": "Custom",
            "description": "User-defined CSS custom property design tokens (:root variables).",
        },
    ]


def resolve_style_preset(name: Optional[str]) -> Optional[StyleSpec]:
    """
    Resolves a structured style preset name (e.g. 'editorial', 'brutalist', 'minimal', 'technical',
    'luxury', 'experimental') to its corresponding StyleSpec.
    Returns None for 'auto', 'custom', None, or unrecognized names (which trigger heuristic archetype fallback).
    """
    if not name:
        return None
    normalized = str(name).strip().lower().replace(" ", "_").replace("-", "_")
    if normalized in ("auto", "none", "default", "custom"):
        return None

    preset_alias_map = {
        "editorial": "editorial",
        "refero_editorial": "refero_editorial",
        "brutalist": "brutalist",
        "brutalism": "brutalist",
        "neo_brutalist": "neo_brutalist",
        "neo_brutalism": "neo_brutalist",
        "minimal": "minimal",
        "minimalist": "minimal",
        "technical": "technical",
        "developer": "technical",
        "engineering": "technical",
        "luxury": "luxury",
        "luxury_minimalist": "luxury_minimalist",
        "experimental": "experimental",
        "glassmorphic": "experimental",
        "glassmorphic_aurora": "glassmorphic_aurora",
        "cyberpunk": "cyberpunk_neon",
        "cyberpunk_neon": "cyberpunk_neon",
    }

    canonical_key = preset_alias_map.get(normalized, normalized)
    return PRESET_STYLES.get(canonical_key)


# ==============================================================================
# 3. Style Conformance Validator (Runtime Observation Gate)
# ==============================================================================

def sanitize_css_for_spec(css_content: str, style_spec: StyleSpec) -> str:
    """
    Safely auto-remediates minor token discrepancies (e.g. bare #ffffff or #000000 or defined preset tokens)
    into their corresponding design tokens so trivial formatting differences do not trigger failure loops.
    """
    if not style_spec or not css_content:
        return css_content

    # 1. Remediate all exact color matches declared in style_spec.colors
    for token_name, hex_val in getattr(style_spec, "colors", {}).items():
        if not hex_val or not hex_val.startswith("#"):
            continue
        clean_hex = hex_val.strip()
        pattern = r'(?<!var\()(?<![\w-])' + re.escape(clean_hex) + r'\b(?!\s*[\w-]*\s*[,)])'
        css_content = re.sub(pattern, f"var({token_name}, {clean_hex})", css_content, flags=re.IGNORECASE)

    # 2. Common dark/light surface tokens
    dark_token = None
    for k in ["--surface-obsidian", "--color-obsidian", "--color-border", "--color-text", "--color-dark"]:
        if k in style_spec.colors:
            dark_token = k
            break
    light_token = None
    for k in ["--surface-paper", "--color-paper", "--color-surface", "--color-bg", "--color-light"]:
        if k in style_spec.colors:
            light_token = k
            break

    if light_token:
        css_content = re.sub(
            r'((?:color|background(?:-color)?)\s*:\s*)#(?:ffffff|fff)\b',
            rf'\1var({light_token}, #ffffff)',
            css_content,
            flags=re.IGNORECASE
        )
    if dark_token:
        css_content = re.sub(
            r'((?:color|background(?:-color)?)\s*:\s*)#(?:000000|000)\b',
            rf'\1var({dark_token}, #000000)',
            css_content,
            flags=re.IGNORECASE
        )

    # 3. If pill/sharp rule is active ("between 1px and 74px"),
    # normalize hairline icon/toggle bar 1px-2px border-radius to 0 so micro elements don't violate rules
    if any("between 1px and 74px" in d.lower() for d in style_spec.donts):
        css_content = re.sub(
            r'border-radius\s*:\s*[12]px\b',
            'border-radius: 0',
            css_content,
            flags=re.IGNORECASE
        )

    # 4. If zero-radius rule is active ("Never use rounded corners or border-radius > 0px")
    if any("border-radius > 0px" in d.lower() or "zero corner" in d.lower() for d in style_spec.donts):
        css_content = re.sub(
            r'border-radius\s*:\s*(?:var\([^)]+\)|\d+px)\b',
            'border-radius: 0px',
            css_content,
            flags=re.IGNORECASE
        )

    # 5. Remediate any remaining bare hex color to declared token from style_spec.colors
    if getattr(style_spec, "colors", None):
        primary_token = next(
            (k for k in ["--color-primary", "--color-accent", "--color-bronze", "--color-text"] if k in style_spec.colors),
            list(style_spec.colors.keys())[0]
        )
        css_content = re.sub(
            r'(?<!var\()(?<![\w-])#[0-9a-fA-F]{3,8}\b(?!\s*[\w-]*\s*[,)])',
            lambda m: f"var({primary_token}, {m.group(0)})",
            css_content
        )

    # 6. Auto-repair truncated CSS syntax (unclosed quotes, unclosed url(), unclosed brackets)
    lines = css_content.splitlines()
    if lines:
        last_line = lines[-1]
        if ("url('" in last_line and "')" not in last_line) or ('url("' in last_line and '")' not in last_line):
            quote = "'" if "url('" in last_line else '"'
            lines[-1] = last_line + quote + ");"
        for q in ("'", '"'):
            if lines[-1].count(q) % 2 != 0:
                lines[-1] = lines[-1] + q + ";"
        css_content = "\n".join(lines)
        open_b = css_content.count("{")
        close_b = css_content.count("}")
        if open_b > close_b:
            css_content = css_content.rstrip() + "\n" + ("}\n" * (open_b - close_b))

    return css_content


def _css_without_root_tokens(css: str) -> str:
    """Mask custom properties in exact :root rules, preserving all other rules.

    Track strings and braces so minification, quoted braces and nested rules
    cannot hide declarations following a token definition.
    """
    output = list(css)
    stack = []
    start = 0
    quote = None
    escaped = False
    for i, char in enumerate(css):
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if quote:
            if char == quote:
                quote = None
            continue
        if char in ('"', "'"):
            quote = char
            continue
        if char == "{":
            selector = css[start:i].strip()
            stack.append(selector == ":root")
            start = i + 1
        elif char in ";}":
            if stack and stack[-1] and re.match(r'\s*--[\w-]+\s*:', css[start:i]):
                output[start:i] = " " * (i - start)
            if char == "}" and stack:
                stack.pop()
            start = i + 1
    return "".join(output)


def validate_css_conformance(
    css_content: str,
    style_spec: StyleSpec,
    strict_colors: bool = True
) -> List[str]:
    """
    Validates that a generated CSS file conforms to the ingested StyleSpec.
    Detects hardcoded hex/rgb colors, unapproved box-shadows, or conflicting radii.
    Returns a list of descriptive violation strings (empty if fully compliant).
    """
    if not style_spec or not style_spec.colors:
        return []

    violations = []

    # Strip comments to prevent false positives in comments
    clean_css = re.sub(r'/\*.*?\*/', '', css_content, flags=re.DOTALL)

    # 1. Check for hardcoded hex colors that aren't inside var(...)
    # Ignore declarations inside :root or custom variable assignments
    body_css = _css_without_root_tokens(clean_css)

    if strict_colors:
        # Strip valid var(...) usages before checking for bare hex colors
        no_vars = re.sub(r'var\(\s*--[\w-]+(?:\s*,\s*[^)]+)?\)', '', body_css)
        # Allow brutalist hard shadows (e.g. 4px 4px 0px #000000) and solid outlines
        no_vars = re.sub(r'0px\s+#0{3,6}\b', '', no_vars, flags=re.IGNORECASE)
        no_vars = re.sub(r'solid\s+#0{3,6}\b', '', no_vars, flags=re.IGNORECASE)
        hex_matches = re.findall(r'(?<![\w-])#([0-9a-fA-F]{3,8})\b', no_vars)
        if hex_matches:
            unique_hex = list(set(f"#{h}" for h in hex_matches))
            # Filter out standard neutral black/white if already sanitized
            filtered = [h for h in unique_hex if h.lower() not in ("#000", "#000000", "#fff", "#ffffff")]
            if filtered:
                violations.append(
                    f"Found hardcoded hex color(s) {', '.join(filtered[:4])}. "
                    f"You MUST use design tokens such as var(--color-*), var(--surface-*), or var(--bg-color) exclusively."
                )

    # 2. Check specific "don'ts" constraints
    for dont in style_spec.donts:
        lower_dont = dont.lower()
        if "box-shadow" in lower_dont and ("never" in lower_dont or "avoid" in lower_dont):
            has_allowed_shadow = any("box-shadow" in d.lower() for d in style_spec.dos)
            if not has_allowed_shadow:
                # Box shadow is completely forbidden in this design system (e.g. Refero Editorial)
                for match in re.finditer(r'box-shadow\s*:\s*([^;]+);', body_css, re.IGNORECASE):
                    val = match.group(1).strip().lower()
                    if val not in ("none", "unset", "inherit", "initial", "0", "0px", "none !important"):
                        violations.append("Used 'box-shadow' contrary to the design constraint: 'Never use box-shadow or elevation blur'. Rely strictly on border and color contrast.")
                        break
            elif "blurry" in lower_dont or "diffuse" in lower_dont:
                # Hard shadows allowed (e.g. 4px 4px 0px #000 or var(--shadow-hard)), but blurry shadows forbidden
                for match in re.finditer(r'box-shadow\s*:\s*([^;]+);', body_css, re.IGNORECASE):
                    val = match.group(1).strip().lower()
                    if "var(--shadow-hard" in val or "0px #" in val or "0px rgba" in val or val in ("none", "unset", "inherit", "initial", "0", "0px"):
                        continue
                    if re.search(r'\d+px\s+\d+px\s+[1-9]\d*px', val):
                        violations.append("Used blurry box-shadow contrary to the constraint: 'Never use blurry, diffuse box-shadows'. Use hard offset shadows (e.g. 4px 4px 0px #000) or var(--shadow-hard).")
                        break

        if "border-radius" in lower_dont and "between 1px and 74px" in lower_dont:
            # Detect intermediate border-radius (e.g. 8px, 12px, 16px) on cards or buttons
            # Exclude micro hairlines (1px, 2px) or pills (>= 75px)
            radius_matches = re.findall(r'border-radius\s*:\s*(\d+)px', body_css)
            bad_radii = [r for r in radius_matches if 4 <= int(r) <= 74]
            if bad_radii:
                violations.append(
                    f"Used invalid border-radius ({bad_radii[0]}px). "
                    f"This design strictly requires pill radius for buttons (var(--radius-buttons): 75px) and 0px for cards/images."
                )

    # 3. Typographic hierarchy checks
    heading_font_sizes = []
    for selectors, declarations in re.findall(r'([^{}]+)\{([^{}]*)\}', body_css):
        # Check the element being styled, not an ancestor whose class includes
        # "title". For example .section-title > p is body copy, not a heading.
        endpoints = [re.split(r'[\s>+~]+', selector.strip())[-1] for selector in selectors.split(',')]
        if any(re.fullmatch(r'(?:h[1-6]|\.[\w-]*(?:title|heading))(?:[.:][\w()-]+)*', endpoint, re.I) for endpoint in endpoints):
            heading_font_sizes.extend(re.findall(r'font-size\s*:\s*(\d+(?:\.\d+)?)(px|rem)', declarations, re.I))
    for val, unit in heading_font_sizes:
        size_px = float(val) * 16 if unit == "rem" else float(val)
        if size_px < 15:
            violations.append(f"Heading font size ({val}{unit}) is too small (< 15px); maintain clear typographic hierarchy with prominent headings.")

    # 4. Spacing scale & rhythm checks
    if getattr(style_spec, "spacing_scale", None):
        irregular_spacings = re.findall(r'(?:margin|padding)\s*:\s*(\d+)px', body_css)
        weird = [s for s in irregular_spacings if int(s) not in (0, 1, 2, 4, 8, 12, 16, 20, 24, 32, 40, 48, 64, 80, 96, 128) and int(s) % 4 != 0]
        if len(weird) >= 3:
            violations.append(f"Found off-grid spacing values ({', '.join(weird[:3])}px). Use the established 4px/8px design system spacing scale or var(--spacing-*).")

    return violations


# ==============================================================================
# 4. Code Generation & System Prompt Formatters
# ==============================================================================

# Calibrated WCAG 2.1 relative luminance threshold separating light backgrounds
# (requiring dark text) from dark backgrounds (requiring light text).
_WCAG_LIGHT_THRESHOLD = 0.35

_NAMED_CSS_COLORS: Dict[str, Tuple[int, int, int]] = {
    "white": (255, 255, 255),
    "black": (0, 0, 0),
    "transparent": (0, 0, 0),
    "cream": (253, 251, 247),
    "ivory": (255, 255, 240),
    "snow": (255, 250, 250),
    "ghostwhite": (248, 248, 255),
    "aliceblue": (240, 248, 255),
    "floralwhite": (255, 250, 240),
    "seashell": (255, 245, 238),
    "honeydew": (240, 255, 240),
    "mintcream": (245, 255, 250),
    "azure": (240, 255, 255),
    "lightyellow": (255, 255, 224),
    "lightcyan": (224, 255, 255),
    "lightgray": (211, 211, 211),
    "lightgrey": (211, 211, 211),
    "gray": (128, 128, 128),
    "grey": (128, 128, 128),
    "darkgray": (169, 169, 169),
    "darkgrey": (169, 169, 169),
    "yellow": (255, 255, 0),
    "cyan": (0, 255, 255),
    "red": (255, 0, 0),
    "green": (0, 128, 0),
    "blue": (0, 0, 255),
}


def _wcag_relative_luminance(r: int, g: int, b: int) -> float:
    """Computes WCAG 2.1 relative luminance with standard gamma-expansion."""
    def channel(c):
        c = c / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r_lin, g_lin, b_lin = channel(r), channel(g), channel(b)
    return 0.2126 * r_lin + 0.7152 * g_lin + 0.0722 * b_lin


def _extract_first_gradient_stop(gradient_str: str) -> str:
    """Extracts the first color stop from a CSS gradient string."""
    m = re.match(r'^(?:repeating-)?(?:linear|radial|conic)-gradient\s*\((.*)\)$', gradient_str.strip(), re.IGNORECASE | re.DOTALL)
    if not m:
        return ''
    inner = m.group(1).strip()
    args = []
    current = []
    depth = 0
    for ch in inner:
        if ch == '(':
            depth += 1
            current.append(ch)
        elif ch == ')':
            depth -= 1
            current.append(ch)
        elif ch == ',' and depth == 0:
            args.append(''.join(current).strip())
            current = []
        else:
            current.append(ch)
    if current:
        args.append(''.join(current).strip())
    if not args:
        return ''

    first = args[0].lower()
    is_direction = (
        first.startswith('to ') or
        first.startswith('from ') or
        first.startswith('at ') or
        first in ('circle', 'ellipse') or
        re.search(r'^-?[\d.]+\s*(?:deg|rad|grad|turn)$', first) is not None
    )
    stop = args[1] if is_direction and len(args) > 1 else args[0]

    if ')' in stop:
        idx = stop.rfind(')')
        return stop[:idx+1].strip()
    else:
        parts = stop.split()
        return parts[0].strip() if parts else stop.strip()


def _parse_css_color_to_rgb(color_str: str) -> Optional[Tuple[int, int, int]]:
    """
    Parses a CSS color string (#hex, rgb(), rgba(), hsl(), hsla(), or named color)
    into an (r, g, b) integer tuple in [0, 255]. Returns None if unparseable.
    """
    if not color_str or not isinstance(color_str, str):
        return None
    c = color_str.strip().lower()

    # 0. Strip var(--token, fallback)
    if c.startswith("var("):
        m_var = re.search(r',\s*([^)]+)\)', c)
        if m_var:
            c = m_var.group(1).strip()
        else:
            return None

    # 1. Named colors
    if c in _NAMED_CSS_COLORS:
        return _NAMED_CSS_COLORS[c]

    # 2. Hex formats: #rgb, #rgba, #rrggbb, #rrggbbaa
    m_hex = re.match(r'^#([0-9a-f]{3,8})$', c)
    if m_hex:
        h = m_hex.group(1)
        if len(h) in (3, 4):
            return (int(h[0]*2, 16), int(h[1]*2, 16), int(h[2]*2, 16))
        elif len(h) in (6, 8):
            return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))

    # 3. rgb(...) / rgba(...)
    m_rgb = re.match(r'^rgba?\(\s*([\d.]+%?)\s*[,/ ]\s*([\d.]+%?)\s*[,/ ]\s*([\d.]+%?)', c)
    if m_rgb:
        vals = []
        for g in m_rgb.groups():
            if g.endswith('%'):
                vals.append(int(round(float(g[:-1]) * 2.55)))
            else:
                vals.append(int(round(float(g))))
        return (max(0, min(255, vals[0])), max(0, min(255, vals[1])), max(0, min(255, vals[2])))

    # 4. hsl(...) / hsla(...)
    m_hsl = re.match(r'^hsla?\(\s*([\d.]+(?:deg)?)\s*[,/ ]\s*([\d.]+)%\s*[,/ ]\s*([\d.]+)%', c)
    if m_hsl:
        h_str, s_str, l_str = m_hsl.groups()
        h = float(h_str.replace('deg', '')) % 360
        s = max(0.0, min(100.0, float(s_str))) / 100.0
        l = max(0.0, min(100.0, float(l_str))) / 100.0
        r, g, b = colorsys.hls_to_rgb(h / 360.0, l, s)
        return (int(round(r * 255)), int(round(g * 255)), int(round(b * 255)))

    return None


def is_light_color(color_str: str) -> bool:
    """
    Returns True if the CSS color has WCAG 2.1 relative luminance > 0.35 (light/paper background).
    Supports:
    - #hex (#rgb, #rgba, #rrggbb, #rrggbbaa)
    - rgb(r, g, b) / rgba(r, g, b, a)
    - hsl(h, s%, l%) / hsla(h, s%, l%, a)
    - linear-gradient(...) (evaluates the first color stop)
    - Named CSS colors
    - Safe default: returns False if unparseable.
    """
    if not color_str or not isinstance(color_str, str):
        return False
    color_clean = color_str.strip().lower()

    # Fast path for common known light paper tints
    if color_clean in ("#fff", "#ffffff", "white", "#fdfbf7", "#fafafa", "#f8fafc", "#f1f5f9", "#f5f5f4", "#f4f4f5", "#f5ebe0"):
        return True

    # Handle linear/radial gradients by extracting first color stop
    if "gradient" in color_clean:
        first_stop = _extract_first_gradient_stop(color_clean)
        if first_stop and first_stop != color_clean:
            return is_light_color(first_stop)

    rgb = _parse_css_color_to_rgb(color_clean)
    if rgb is not None:
        lum = _wcag_relative_luminance(*rgb)
        return lum > _WCAG_LIGHT_THRESHOLD

    return False


def wcag_contrast_ratio(foreground: str, background: str) -> Optional[float]:
    """Return the WCAG contrast ratio for two parseable CSS colors."""
    fg = _parse_css_color_to_rgb(foreground)
    bg = _parse_css_color_to_rgb(background)
    if fg is None or bg is None:
        return None
    light, dark = sorted((_wcag_relative_luminance(*fg), _wcag_relative_luminance(*bg)), reverse=True)
    return (light + 0.05) / (dark + 0.05)


def validate_semantic_contrast(style_spec: StyleSpec, minimum: float = 7.0) -> List[str]:
    """Validate required semantic foreground/background pairs before generation.

    Unparseable values are reported instead of silently passing.  Themes may omit
    optional tokens, but any supplied required pair must meet AAA contrast.
    """
    tokens = {**style_spec.colors, **style_spec.surfaces, **style_spec.type_scale, **style_spec.semantic_tokens}
    aliases = {
        "canvas": ["--canvas", "--surface-canvas", "--surface-paper", "--color-bg"],
        "surface-1": ["--surface-1", "--surface-primary", "--color-surface"],
        "text-primary": ["--text-primary", "--color-text", "--text-color"],
        "text-secondary": ["--text-secondary", "--text-muted", "--color-text-muted"],
        "accent": ["--accent", "--accent-color", "--color-accent"],
        "on-accent": ["--on-accent"],
        "focus-ring": ["--focus-ring"],
    }
    def resolve(name: str) -> Optional[str]:
        for key in aliases[name]:
            if key in tokens:
                return tokens[key]
        return None

    errors: List[str] = []
    pairs = [("text-primary", "canvas"), ("text-primary", "surface-1"),
             ("text-secondary", "canvas"), ("on-accent", "accent")]
    for fg_name, bg_name in pairs:
        fg, bg = resolve(fg_name), resolve(bg_name)
        if fg is None or bg is None:
            continue
        ratio = wcag_contrast_ratio(fg, bg)
        if ratio is None:
            errors.append(f"Cannot compute WCAG contrast for {fg_name}/{bg_name}.")
        elif ratio < minimum:
            errors.append(f"{fg_name}/{bg_name} contrast {ratio:.2f}:1 is below AAA {minimum:.1f}:1.")
    focus, canvas = resolve("focus-ring"), resolve("canvas")
    if focus and canvas:
        ratio = wcag_contrast_ratio(focus, canvas)
        if ratio is not None and ratio < 3.0:
            errors.append(f"focus-ring/canvas contrast {ratio:.2f}:1 is below the 3.0:1 non-text minimum.")
    return errors


def build_site_root_css(
    brief: Optional[dict] = None,
    style_spec: Optional[StyleSpec] = None
) -> Tuple[str, Set[str]]:
    """
    Builds the authoritative :root { ... } stylesheet block for the site.
    Establishes a unified token contract upfront that bridges naming variations
    (--color-primary vs --primary-color, --color-bg vs --bg-color, etc.),
    provides surface and radius tokens, and sets motion fallbacks.

    Returns:
        (full_app_css: str, defined_tokens: Set[str])
    where defined_tokens is the set of all variable names (e.g. {'--primary-color', ...}).
    """
    spec = style_spec or (brief.get("style_spec") if brief else None)

    if spec:
        primary = spec.get_primary_color()
        accent = spec.get_accent_color()
        font_h = (brief.get("font_heading") if brief else None) or spec.get_heading_font()
        font_b = (brief.get("font_body") if brief else None) or spec.get_body_font()
    else:
        primary = (brief.get("primary_color") if brief else None) or "#090d16"
        accent  = (brief.get("accent_color") if brief else None) or "#38bdf8"
        font_h  = (brief.get("font_heading") if brief else None) or "Inter"
        font_b  = (brief.get("font_body") if brief else None) or "Inter"

    accent_sec = (brief.get("accent_secondary") if brief else None) or "#818cf8"
    # A CTA foreground depends on its accent background, not the page canvas.
    on_accent = max(("#000000", "#ffffff"),
                    key=lambda color: wcag_contrast_ratio(color, accent) or 0)
    is_light = is_light_color(primary)
    text_color = (brief.get("primary_color_dark") if brief and is_light else None) or ("#1c1917" if is_light else "#fafafa")
    text_muted = "rgba(28, 25, 23, 0.65)" if is_light else "rgba(250, 250, 250, 0.65)"

    paper = "#ffffff" if is_light else "#1e293b"
    surface = "#ffffff" if is_light else "#161f30"
    surface_alt = "rgba(0, 0, 0, 0.03)" if is_light else "rgba(255, 255, 255, 0.05)"
    border_color = "rgba(0, 0, 0, 0.08)" if is_light else "rgba(255, 255, 255, 0.12)"
    obsidian = "#090d16"

    # Radii
    rad_dict = spec.radius if (spec and spec.radius) else {}
    btn_rad = rad_dict.get("--radius-buttons", "8px")
    card_rad = rad_dict.get("--radius-cards", "16px")
    tag_rad = rad_dict.get("--radius-tags", "9999px")
    input_rad = rad_dict.get("--radius-inputs", "8px")

    system_name = spec.name if spec else "Default Adaptive"
    system_source = spec.source if spec else "brief"

    # Fail closed for explicitly supplied semantic tokens.  Legacy palettes that
    # do not declare semantic pairs remain backwards compatible.
    if spec and spec.semantic_tokens:
        contrast_errors = validate_semantic_contrast(spec)
        if contrast_errors:
            raise ValueError("Theme accessibility validation failed: " + " ".join(contrast_errors))

    lines = [
        "/* ==========================================================================",
        f"   DESIGN SYSTEM: {system_name} (Source: {system_source})",
        "   ========================================================================== */",
        ":root {",
        "  /* Core Color Tokens */",
        f"  --primary-color: {primary};",
        f"  --primary-color-light: rgba(255, 255, 255, 0.08);",
        f"  --accent-color: {accent};",
        f"  --accent-color-dark: rgba(0, 0, 0, 0.3);",
        f"  --accent-color-light: rgba(255, 255, 255, 0.15);",
        f"  --accent-secondary: {accent_sec};",
        f"  --bg-color: {primary};",
        f"  --text-color: {text_color};",
        f"  --text-muted: {text_muted};",
        f"  --canvas: {primary};",
        f"  --surface-1: {surface};",
        f"  --surface-2: {surface_alt};",
        f"  --surface-raised: {paper};",
        f"  --text-primary: {text_color};",
        f"  --text-secondary: {text_muted};",
        f"  --text-inverse: {'#000000' if not is_light else '#ffffff'};",
        f"  --border-subtle: {border_color};",
        f"  --border-strong: {'rgba(0, 0, 0, 0.22)' if is_light else 'rgba(255, 255, 255, 0.28)'};",
        f"  --accent: {accent};",
        f"  --accent-hover: {accent};",
        f"  --on-accent: {on_accent};",
        f"  --focus-ring: {accent};",
        f"  --color-heading: var(--text-color);",
        f"  --color-text-light: var(--text-muted);",
        f"  --color-text-subtle: var(--text-muted);",
        "",
        "  /* Surfaces & Borders */",
        f"  --color-paper: {paper};",
        f"  --color-surface: {surface};",
        f"  --color-surface-alt: {surface_alt};",
        f"  --color-border: {border_color};",
        f"  --surface-paper: {paper};",
        f"  --surface-obsidian: {obsidian};",
        f"  --color-obsidian: {obsidian};",
        "",
        "  /* Universal Compatibility Aliases */",
        "  --color-primary: var(--primary-color);",
        "  --color-accent: var(--accent-color);",
        "  --color-accent-dark: var(--accent-color-dark);",
        "  --color-accent-secondary: var(--accent-secondary);",
        "  --color-bg: var(--bg-color);",
        "  --color-text: var(--text-color);",
        "  --color-text-muted: var(--text-muted);",
        "",
        "  /* Typography Families */",
        f"  --font-heading: '{font_h}', system-ui, -apple-system, sans-serif;",
        f"  --font-body: '{font_b}', system-ui, -apple-system, sans-serif;",
        "",
        "  /* Border Radii */",
        f"  --radius-buttons: {btn_rad};",
        f"  --radius-cards: {card_rad};",
        f"  --radius-tags: {tag_rad};",
        f"  --radius-inputs: {input_rad};",
        "",
        "  /* Layout & Spacing */",
        "  --font-display: var(--font-heading);",
        "  --font-mono: ui-monospace, SFMono-Regular, Menlo, monospace;",
        "  --step--1: clamp(0.8rem, 0.77rem + 0.12vw, 0.875rem);",
        "  --step-0: clamp(1rem, 0.96rem + 0.18vw, 1.125rem);",
        "  --step-1: clamp(1.25rem, 1.16rem + 0.42vw, 1.5rem);",
        "  --step-2: clamp(1.56rem, 1.38rem + 0.8vw, 2rem);",
        "  --step-3: clamp(1.95rem, 1.63rem + 1.45vw, 2.67rem);",
        "  --step-4: clamp(2.44rem, 1.92rem + 2.35vw, 3.55rem);",
        "  --step-5: clamp(3.05rem, 2.25rem + 3.6vw, 4.74rem);",
        "  --step-6: clamp(3.81rem, 2.63rem + 5.3vw, 6.32rem);",
        "  --leading-tight: 1.08; --leading-body: 1.5; --leading-relaxed: 1.7;",
        "  --tracking-tight: -0.025em; --tracking-display: -0.04em; --tracking-caps: 0.12em;",
        "  --space-3xs: clamp(0.25rem, 0.22rem + 0.1vw, 0.375rem);",
        "  --space-2xs: clamp(0.5rem, 0.45rem + 0.2vw, 0.75rem);",
        "  --space-xs: clamp(0.75rem, 0.67rem + 0.35vw, 1rem);",
        "  --space-s: clamp(1rem, 0.9rem + 0.45vw, 1.5rem);",
        "  --space-m: clamp(1.5rem, 1.3rem + 0.9vw, 2.5rem);",
        "  --space-l: clamp(2rem, 1.65rem + 1.6vw, 3.5rem);",
        "  --space-xl: clamp(3rem, 2.3rem + 3.1vw, 5.5rem);",
        "  --space-2xl: clamp(4rem, 3rem + 4.5vw, 8rem);",
        "  --space-3xl: clamp(6rem, 4.5rem + 6.8vw, 12rem);",
        "  --gutter: clamp(1rem, 0.5rem + 2vw, 4rem);",
        "  --section-space: clamp(4rem, 2.5rem + 6vw, 10rem);",
        "  --content-width: min(100% - 2 * var(--gutter), 80rem);",
        "  --measure: 68ch;",
        "  --page-max-width: 80rem;",
        "  --section-gap: var(--section-space);",
        "  --card-padding: var(--space-m);",
        "  --shadow-soft: 0 1px 2px rgba(0,0,0,.08); --shadow-lift: 0 12px 32px rgba(0,0,0,.14); --shadow-float: 0 24px 64px rgba(0,0,0,.2);",
        "  --glass-bg: color-mix(in srgb, var(--surface-1) 72%, transparent); --glass-border: var(--border-subtle); --glass-blur: 18px; --noise-opacity: 0.035;",
        "",
        "  /* Animation & Motion Safety Fallbacks */",
        "  --scroll-transform: none;",
        "  --scroll-transition: transform var(--duration-normal) var(--ease-out), opacity var(--duration-normal) var(--ease-out);",
        "  --motion-layer: motion; --sticky-offset: clamp(3rem, 8vh, 6rem);",
        "  --duration-fast: 160ms; --duration-normal: 320ms; --duration-slow: 700ms;",
        "  --ease-out: cubic-bezier(.22, 1, .36, 1); --ease-spring-ish: cubic-bezier(.34, 1.56, .64, 1); --stagger: 60ms;",
    ]

    # Supplied declarations are authoritative, including names used by defaults.
    # Keep one declaration per name so prompt and rendered CSS agree exactly.
    if spec:
        explicit = dict(re.findall(r'(--[\w-]+)\s*:\s*([^;]+);', spec.raw_css))
        for category in (spec.colors, spec.fonts, spec.type_scale, spec.radius,
                         spec.surfaces, spec.spacing_scale, spec.layout,
                         spec.other_tokens, spec.semantic_tokens, spec.motion_tokens):
            explicit.update(category)
        declared = set()
        def preserve_token(match):
            name = match.group(1)
            declared.add(name)
            return f"{name}: {explicit.get(name, match.group(2))};"
        lines = [re.sub(r'(--[\w-]+)\s*:\s*([^;]+);', preserve_token, line) for line in lines]
        extras = [f"  {name}: {value};" for name, value in explicit.items() if name not in declared]
        if extras:
            lines.extend(["", "  /* Ingested StyleSpec Tokens */", *extras])

    lines.append("}")
    lines.append("")
    lines.append("*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }")
    lines.append("html { scroll-behavior: smooth; font-family: var(--font-body); }")
    lines.append("body { margin: 0; font-family: var(--font-body); background-color: var(--bg-color); color: var(--text-color); -webkit-font-smoothing: antialiased; }")
    lines.append(".site-root { display: flex; flex-direction: column; min-height: 100vh; }")
    lines.append(".site-skip-link { position: fixed; top: -100px; left: 16px; z-index: 99999; padding: 12px; background: var(--bg-color); color: var(--text-color); } .site-skip-link:focus { top: 12px; }")
    lines.append("@media (prefers-reduced-motion: reduce) { html { scroll-behavior: auto !important; } *, *::before, *::after { animation-duration: 0.01ms !important; animation-iteration-count: 1 !important; transition-duration: 0.01ms !important; } }")

    full_css = "\n".join(lines)
    defined_token_names = set(re.findall(r'(--[\w-]+)\s*:', full_css))
    return full_css, defined_token_names


def spec_to_css_root(style_spec: StyleSpec) -> str:
    """
    Builds a complete, modern :root { ... } stylesheet block from StyleSpec.
    Includes backward-compatible aliases (--primary-color, --accent-color, --font-heading, --font-body,
    --color-primary, --color-bg, etc.) so existing component patterns seamlessly interoperate.
    """
    full_css, _ = build_site_root_css(style_spec=style_spec)
    return full_css


def spec_to_prompt_instructions(style_spec: StyleSpec) -> str:
    """
    Generates strict system prompt instructions explaining the design system
    and enforcing token adherence for the model.
    """
    lines = [
        f"DESIGN SYSTEM SPECIFICATION: '{style_spec.name}'",
        "You MUST strictly adhere to the following design tokens and rules when writing .css files:",
        "",
        "Available Design Tokens (Defined in :root):",
    ]

    # Sample top tokens for prompt economy
    color_samples = [f"{k}: {v}" for k, v in list(style_spec.colors.items())[:8]]
    if color_samples:
        lines.append("  Colors: " + ", ".join(color_samples))

    radius_samples = [f"{k}: {v}" for k, v in style_spec.radius.items()]
    if radius_samples:
        lines.append("  Radii: " + ", ".join(radius_samples))

    font_samples = [f"{k}: {v.split(',')[0]}" for k, v in style_spec.fonts.items()]
    if font_samples:
        lines.append("  Fonts: " + ", ".join(font_samples))

    lines.append("")
    lines.append("STRICT CONSTRAINTS & DESIGN RULES:")
    lines.append("1. Use ONLY the CSS custom properties defined in :root for colors, spacing, radius, and typography.")
    lines.append("2. Do NOT invent new hex color codes or arbitrary pixel radii.")

    for do in style_spec.dos:
        lines.append(f"3. {do}")
    for dont in style_spec.donts:
        lines.append(f"4. CONSTRAINT: {dont}")

    return "\n".join(lines)


# ==============================================================================
# 5. Structural Quality & Layout Guardrails
# ==============================================================================

def parse_css_rule_blocks(css_text: str) -> List[Tuple[str, str, str]]:
    """
    Parses CSS into a list of (selector, declarations_text, full_block).
    Robust bracket-matching parser handling nested rules and @media/@supports queries.
    """
    clean_css = re.sub(r'/\*.*?\*/', '', css_text, flags=re.DOTALL)
    blocks: List[Tuple[str, str, str]] = []
    i = 0
    n = len(clean_css)
    while i < n:
        brace_open = clean_css.find('{', i)
        if brace_open == -1:
            break
        selector = clean_css[i:brace_open].strip()
        depth = 1
        j = brace_open + 1
        while j < n and depth > 0:
            if clean_css[j] == '{':
                depth += 1
            elif clean_css[j] == '}':
                depth -= 1
            j += 1
        block_content = clean_css[brace_open + 1:j - 1]
        if selector.startswith('@media') or selector.startswith('@supports'):
            blocks.extend(parse_css_rule_blocks(block_content))
        elif not selector.startswith('@keyframes'):
            decls_raw = re.sub(r'\{[^{}]*\}', '', block_content)
            blocks.append((selector, decls_raw, block_content))
            if '{' in block_content:
                blocks.extend(parse_css_rule_blocks(block_content))
        i = j
    return blocks


def check_sticky_misuse_lint(css_content: str, section_name: str = "", file_path: str = "") -> List[str]:
    """
    Flags any non-header section using position: sticky with a min-height at or near 100vh.
    Rule: Never use position: sticky on a section taller than a typical nav bar (roughly 100px).
    Sticky is for navigation headers only.
    """
    norm_sec = section_name.lower().strip().replace("-", "").replace("_", "")
    norm_path = file_path.lower().replace("-", "").replace("_", "")
    is_header = "header" in norm_sec or "header" in norm_path or "navbar" in norm_sec or "navbar" in norm_path

    if is_header:
        return []

    violations = []
    blocks = parse_css_rule_blocks(css_content)
    for selector, decls, _ in blocks:
        has_sticky = bool(re.search(r'\bposition\s*:\s*sticky\b', decls, re.I))
        # At or near 100vh includes 100vh, 100dvh, 100svh, 100lvh, >=85vh, or 100% full viewport
        has_full_height = bool(re.search(r'\b(?:min-height|height)\s*:\s*(?:100(?:vh|dvh|svh|lvh|%)|(?:8[5-9]|9[0-9])(?:vh|dvh|svh|lvh))\b', decls, re.I))
        if has_sticky and has_full_height:
            violations.append(
                f"[{file_path or 'CSS'}] Selector '{selector}' co-locates 'position: sticky' with a full-viewport height rule. "
                f"Never use position: sticky on a section taller than a typical nav bar (roughly 100px). Sticky is for navigation headers only."
            )
    return violations


def check_duplicate_heading_classes_lint(tsx_content: str, file_path: str = "") -> List[str]:
    """
    Flags the same CSS class name applied to elements at two different heading levels
    (<h2> and <h3> sharing a class) within one file.
    """
    h2_classes: set[str] = set()
    for m in re.finditer(r'<h2[^>]*\bclassName=["\']([^"\']+)["\']', tsx_content):
        for cls in m.group(1).split():
            h2_classes.add(cls)

    h3_classes: set[str] = set()
    for m in re.finditer(r'<h3[^>]*\bclassName=["\']([^"\']+)["\']', tsx_content):
        for cls in m.group(1).split():
            h3_classes.add(cls)

    overlap = h2_classes & h3_classes
    if overlap:
        sorted_overlap = sorted(list(overlap))
        suggested_card_class = sorted_overlap[0].replace('__title', '__card-title') if '__title' in sorted_overlap[0] else f"{sorted_overlap[0]}-card"
        return [
            f"[{file_path or 'TSX'}] Duplicate heading class detected: CSS class(es) {sorted_overlap} applied to both <h2> (section-level heading) "
            f"and <h3> (card-level heading) within the same component. Use distinct class names (e.g. '{sorted_overlap[0]}' for section title and "
            f"'{suggested_card_class}' for card titles) to maintain typographic hierarchy."
        ]
    return []


def check_placeholder_metrics_lint(tsx_content: str, file_path: str = "") -> List[str]:
    """
    Flags placeholder-metric detection: a card's 'metric'/'stat'/'badge' badge text
    matching (case-insensitively) its own title string.
    """
    violations = []
    # Find all metric/stat/badge spans or elements
    span_matches = list(re.finditer(
        r'<(?:span|div|p)[^>]*\bclassName=["\'][^"\']*(?:metric|stat|badge)[^"\']*["\'][^>]*>(.*?)</(?:span|div|p)>',
        tsx_content, re.DOTALL | re.I
    ))
    if not span_matches:
        return []

    heading_matches = list(re.finditer(
        r'<h[2-4][^>]*>(.*?)</h[2-4]>',
        tsx_content, re.DOTALL | re.I
    ))

    for sm in span_matches:
        raw_span = sm.group(1)
        span_clean = re.sub(r'<[^>]+>', '', raw_span).strip()
        span_lower = span_clean.lower()
        if not span_clean or len(span_clean) < 3:
            continue

        span_pos = sm.start()

        for hm in heading_matches:
            raw_h = hm.group(1)
            h_clean = re.sub(r'<[^>]+>', '', raw_h).strip()
            h_lower = h_clean.lower()
            if not h_clean:
                continue

            h_pos = hm.start()
            dist = abs(span_pos - h_pos)

            is_exact = span_lower == h_lower
            is_close_sub = (span_lower in h_lower or h_lower in span_lower) and len(span_lower) >= 4 and abs(len(span_lower) - len(h_lower)) <= 12

            if dist < 1500 and (is_exact or is_close_sub):
                violations.append(
                    f"[{file_path or 'TSX'}] Placeholder metric detected: Metric badge text '{span_clean}' duplicates or mirrors "
                    f"sibling card title '{h_clean}'. Card metrics must be authentic quantitative values (e.g. '250% Premium', '99.9%', '500+ users', '$49/mo') "
                    f"rather than repeating the heading string."
                )
                break
    return violations


def check_undefined_css_variables_lint(
    css_content: str,
    defined_tokens: Set[str],
    file_path: str = ""
) -> List[str]:
    """
    Parses every var(--xxx) reference in css_content and confirms --xxx
    was defined in the site's :root block (defined_tokens).
    Returns descriptive violation strings if any undefined variables are referenced.
    """
    if not css_content or not defined_tokens:
        return []

    clean_css = re.sub(r'/\*.*?\*/', '', css_content, flags=re.DOTALL)
    defined_bare = {t.lstrip('-') for t in defined_tokens}

    used_vars = set(re.findall(r'var\(\s*--([\w-]+)', clean_css))
    missing = used_vars - defined_bare

    if not missing:
        return []

    prefix = f"[{file_path}] " if file_path else ""
    sorted_missing = sorted(list(missing))
    missing_str = ", ".join(f"--{m}" for m in sorted_missing)
    sorted_avail = sorted(f"--{t}" for t in defined_bare)
    sample_avail = ", ".join(sorted_avail[:12])

    return [
        f"{prefix}Undefined CSS custom property referenced: {missing_str}. "
        f"All variables used in var(--...) MUST be defined in :root. "
        f"Available tokens for this site are: {sample_avail}..."
    ]


# ── Repeated-Item Spacing & Gap Placement Verification ────────────────────────

_SVG_TAGS = {
    'svg', 'path', 'rect', 'circle', 'line', 'polygon', 'polyline', 'g',
    'defs', 'clippath', 'mask', 'use', 'stop', 'lineargradient', 'radialgradient'
}


def extract_jsx_elements(jsx: str) -> dict:
    """
    Parses JSX into element nodes with tag, class_name, id, parent, children.
    Handles self-closing tags and standard JSX opening/closing tags.
    """
    tag_pattern = re.compile(
        r'<(/)?([a-zA-Z0-9_.-]+)'
        r'([^>]*?)'
        r'(/)?>',
        re.DOTALL
    )

    tokens = []
    for match in tag_pattern.finditer(jsx):
        is_closing = bool(match.group(1))
        tag_name = match.group(2)
        attrs = match.group(3)
        is_self_closing = bool(match.group(4))

        if tag_name in ('React', 'Fragment'):
            continue

        class_name = None
        cls_m = re.search(r'className=(?:\{["\']([^"\']+)["\']\}|["\']([^"\']+)["\'])', attrs)
        if cls_m:
            class_name = (cls_m.group(1) or cls_m.group(2) or "").strip()

        elem_id = None
        id_m = re.search(r'id=["\']([^"\']+)["\']', attrs)
        if id_m:
            elem_id = id_m.group(1).strip()

        tokens.append({
            'tag': tag_name,
            'is_closing': is_closing,
            'is_self_closing': is_self_closing,
            'class_name': class_name,
            'id': elem_id,
            'pos': match.start(),
        })

    root = {'tag': '__root__', 'class_name': None, 'id': None, 'children': []}
    stack = [root]

    for tok in tokens:
        if tok['is_closing']:
            for idx in range(len(stack) - 1, 0, -1):
                if stack[idx]['tag'] == tok['tag']:
                    stack = stack[:idx]
                    break
        elif tok['is_self_closing']:
            node = {
                'tag': tok['tag'],
                'class_name': tok['class_name'],
                'id': tok['id'],
                'parent': stack[-1],
                'children': []
            }
            stack[-1]['children'].append(node)
        else:
            node = {
                'tag': tok['tag'],
                'class_name': tok['class_name'],
                'id': tok['id'],
                'parent': stack[-1],
                'children': []
            }
            stack[-1]['children'].append(node)
            stack.append(node)

    return root


def find_repeated_item_groups(node: dict) -> List[dict]:
    """
    Recursively finds containers with 2+ sibling children sharing the same class or repeated semantic tags.
    """
    groups = []
    children = node.get('children', [])
    if len(children) >= 2:
        class_buckets: Dict[str, List[dict]] = {}
        tag_buckets: Dict[str, List[dict]] = {}

        for ch in children:
            if ch.get('class_name'):
                main_cls = ch['class_name'].split()[0]
                class_buckets.setdefault(main_cls, []).append(ch)
            tag_buckets.setdefault(ch['tag'], []).append(ch)

        for cls_name, items in class_buckets.items():
            if len(items) >= 2:
                groups.append({
                    'parent': node,
                    'item_count': len(items),
                    'item_class': cls_name,
                    'item_tag': items[0]['tag'],
                    'type': 'class_match'
                })

        for tag_name, items in tag_buckets.items():
            if tag_name in ('li', 'article') and len(items) >= 2:
                if not any(g['parent'] is node and g['item_tag'] == tag_name for g in groups):
                    groups.append({
                        'parent': node,
                        'item_count': len(items),
                        'item_class': items[0].get('class_name'),
                        'item_tag': tag_name,
                        'type': 'tag_match'
                    })

    for ch in children:
        groups.extend(find_repeated_item_groups(ch))

    return groups


def find_map_repeated_items(jsx: str) -> List[dict]:
    """
    Detects {items.map(... => <div className="card">...</div>)} patterns
    and identifies the direct parent container and child item class.
    """
    map_groups = []
    pattern = re.compile(
        r'<([a-zA-Z0-9_.-]+)([^>]*?)>\s*\{[^}]*?\.map\s*\([^{<]*?<([a-zA-Z0-9_.-]+)([^>]*?)className=["\']([^"\']+)["\']',
        re.DOTALL
    )
    for m in pattern.finditer(jsx):
        parent_tag = m.group(1)
        parent_attrs = m.group(2)
        item_tag = m.group(3)
        item_class = m.group(5).split()[0]

        cls_m = re.search(r'className=(?:\{["\']([^"\']+)["\']\}|["\']([^"\']+)["\'])', parent_attrs)
        parent_cls = (cls_m.group(1) or cls_m.group(2) or "").strip() if cls_m else None

        map_groups.append({
            'parent': {
                'tag': parent_tag,
                'class_name': parent_cls,
                'parent': None,
                'children': []
            },
            'item_count': 3,
            'item_class': item_class,
            'item_tag': item_tag,
            'type': 'map_pattern'
        })
    return map_groups


def parse_css_blocks(css: str) -> List[Tuple[str, str]]:
    """Strips comments and parses CSS into (selector, declarations) pairs, supporting nesting and media queries."""
    clean = re.sub(r'/\*.*?\*/', '', css, flags=re.DOTALL)
    blocks = []
    i = 0
    n = len(clean)
    while i < n:
        open_brace = clean.find('{', i)
        if open_brace == -1:
            break
        raw_sel = clean[i:open_brace].strip()
        depth = 1
        j = open_brace + 1
        while j < n and depth > 0:
            if clean[j] == '{':
                depth += 1
            elif clean[j] == '}':
                depth -= 1
            j += 1
        body = clean[open_brace + 1 : j - 1 if depth == 0 else j].strip()
        i = j
        if not raw_sel:
            continue
        # If raw_sel contains leftover declarations from unclosed preceding rule
        if ';' in raw_sel or '\n' in raw_sel:
            parts = [p.strip() for p in re.split(r'[;\n]', raw_sel) if p.strip()]
            sel = parts[-1] if parts else raw_sel
        else:
            sel = raw_sel
        if sel.startswith('@keyframes') or sel.startswith('@font-face'):
            continue
        if sel.startswith('@media') or sel.startswith('@supports'):
            blocks.extend(parse_css_blocks(body))
            continue
        blocks.append((sel, body))
        if '{' in body:
            inner_blocks = parse_css_blocks(body)
            for inner_sel, inner_body in inner_blocks:
                if '&' in inner_sel:
                    resolved = inner_sel.replace('&', sel)
                else:
                    resolved = f"{sel} {inner_sel}"
                blocks.append((resolved, inner_body))
    return blocks


def check_css_syntactic_completeness(css: str, file_path: str = "") -> Tuple[bool, List[str]]:
    """
    Parse CSS declarations and blocks with PostCSS; unavailable validation fails closed.
    Returns (is_valid, error_messages).
    """
    try:
        from css_validation import css_syntax_errors
    except ImportError:
        from agent.css_validation import css_syntax_errors
    prefix = f"[{file_path}] " if file_path else ""
    cleaned_css = re.sub(r'</?style\b[^>]*>', '', css, flags=re.IGNORECASE)
    cleaned_css = re.sub(r'font\s*:\s*size\s+([^,;]+),\s*([^;]+);', r'font-size: \1; color: \2;', cleaned_css)
    cleaned_css = re.sub(r'font\s*:\s*size\s+([^;]+);', r'font-size: \1;', cleaned_css)
    parser_errors = [prefix + error for error in css_syntax_errors(cleaned_css)]
    return not parser_errors, parser_errors

def check_tsx_syntactic_completeness(tsx: str, file_path: str = "") -> Tuple[bool, List[str]]:
    """
    Syntactic validity check for TSX:
    1. Verifies balanced braces '{' and '}'.
    2. Verifies balanced parentheses '(' and ')'.
    3. Verifies file does not truncate mid-tag at EOF (e.g. '<a', '<div className="...', etc.).
    Returns (is_valid, error_messages).
    """
    prefix = f"[{file_path}] " if file_path else ""
    errors = []

    # Check EOF truncation mid-tag
    trimmed = tsx.strip()
    if re.search(r'<[a-zA-Z][^>]*$', trimmed):
        unclosed_tag = re.search(r'<[a-zA-Z][^>]*$', trimmed).group(0)
        errors.append(f"{prefix}Truncated mid-tag: file cuts off with unclosed JSX tag '{unclosed_tag[:40]}'")

    open_braces = tsx.count('{')
    close_braces = tsx.count('}')
    if open_braces != close_braces:
        errors.append(f"{prefix}Unbalanced braces: found {open_braces} '{{' and {close_braces} '}}'")

    open_parens = tsx.count('(')
    close_parens = tsx.count(')')
    if open_parens != close_parens:
        errors.append(f"{prefix}Unbalanced parentheses: found {open_parens} '(' and {close_parens} ')'")

    return len(errors) == 0, errors


VOID_JSX_TAGS = {
    'img', 'input', 'br', 'hr', 'meta', 'link', 'source',
    'area', 'base', 'col', 'embed', 'param', 'track', 'wbr'
}

def balance_jsx_tags(tsx: str) -> str:
    """Detects and closes unclosed JSX container elements (e.g. section, div) before return statement ends."""
    m_return = re.search(r'return\s*\(\s*(<.*?>)', tsx, re.DOTALL)
    if not m_return:
        return tsx

    start_pos = m_return.start(1)
    m_close = re.search(r'(\n\s*\)\s*;?\s*(?:\n\s*})?)', tsx[start_pos:], re.DOTALL)
    if not m_close:
        return tsx

    jsx_content = tsx[start_pos : start_pos + m_close.start(1)]

    tag_stack = []
    tag_pat = re.compile(r'<(/)?([a-zA-Z][a-zA-Z0-9_.-]*)\b([^>]*?)(/)?>', re.DOTALL)
    for m in tag_pat.finditer(jsx_content):
        is_closing = bool(m.group(1))
        tag_name = m.group(2)
        is_self_closing = bool(m.group(4)) or (tag_name.lower() in VOID_JSX_TAGS)

        if is_closing:
            if tag_stack and tag_stack[-1].lower() == tag_name.lower():
                tag_stack.pop()
            elif any(t.lower() == tag_name.lower() for t in tag_stack):
                while tag_stack:
                    popped = tag_stack.pop()
                    if popped.lower() == tag_name.lower():
                        break
        elif not is_self_closing:
            tag_stack.append(tag_name)

    if tag_stack:
        closing_tags = '\n' + '\n'.join([f'    </{t}>' for t in reversed(tag_stack)])
        insert_idx = start_pos + m_close.start(1)
        return tsx[:insert_idx] + closing_tags + tsx[insert_idx:]
    return tsx


def auto_fix_truncated_tsx(files: Union[List[Tuple[str, str]], Dict[str, str]]) -> Union[List[Tuple[str, str]], Dict[str, str]]:
    """Balances unclosed JSX tags, parentheses, and braces in truncated TSX files."""
    return_dict = False
    items = files
    if isinstance(files, dict):
        return_dict = True
        items = list(files.items())

    fixed = []
    for p, c in items:
        if p.endswith('.tsx') or p.endswith('.jsx'):
            content = c.rstrip()
            # If cuts off mid-tag e.g. `<li...><a` or `<a href`, remove the unclosed partial tag
            content = balance_jsx_tags(content)
            content = re.sub(r'<[a-zA-Z][^>]*$', '', content).rstrip()
            open_p = content.count('(')
            close_p = content.count(')')
            if open_p > close_p:
                content += (")" * (open_p - close_p)) + ";"
            open_b = content.count('{')
            close_b = content.count('}')
            if open_b > close_b:
                content += "\n" + ("}\n" * (open_b - close_b))
            fixed.append((p, content))
        else:
            fixed.append((p, c))
    return dict(fixed) if return_dict else fixed



def check_css_selector_coverage(
    tsx: str, css: str, file_path: str = "", allow_tailwind: bool = False
) -> Tuple[bool, List[str]]:
    """
    Selector-coverage check: parses every className used in the paired .tsx file
    and confirms each one has at least one matching selector somewhere in the .css file.
    Returns (is_valid, missing_classes).
    """
    classes = set()
    for m in re.finditer(r'className\s*=\s*(?:"([^"]+)"|\'([^\']+)\'|\{`([^`]+)`\}|\{["\']([^"\']+)["\']\})', tsx):
        raw = m.group(1) or m.group(2) or m.group(3) or m.group(4) or ''
        cleaned = re.sub(r'\$\{[^}]*\}', ' ', raw)
        for c in re.split(r'\s+', cleaned):
            c = c.strip()
            if c and re.match(r'^[a-zA-Z0-9_-]+$', c):
                classes.add(c)

    ignored = {
        'site-root', 'sr-only', 'active', 'open', 'hidden', 'visible',
        'selected', 'disabled', 'loading', 'current', 'is-active', 'is-open'
    }
    clean_css = re.sub(r'/\*.*?\*/', '', css, flags=re.DOTALL)
    missing = []
    for cls in sorted(classes):
        if cls in ignored:
            continue
        if allow_tailwind:
            from agent.tailwind_support import is_tailwind_utility
            if is_tailwind_utility(cls):
                continue
        pattern = r'(?<![\w-])\.' + re.escape(cls) + r'(?![\w-])'
        if re.search(pattern, clean_css):
            continue
        # A base selector does not style a different class: .btn is not a
        # definition of .btn-terracotta or .btn--primary. Accepting prefixes
        # hid missing styles in native generation quality checks.
        missing.append(cls)

    prefix = f"[{file_path}] " if file_path else ""
    error_messages = [f"{prefix}Missing CSS rule for class '.{c}'" for c in missing]
    return len(missing) == 0, missing


def auto_fix_truncated_css(files: Union[List[Tuple[str, str]], Dict[str, str]]) -> Union[List[Tuple[str, str]], Dict[str, str]]:
    """Balances unclosed parentheses and braces in truncated CSS files."""
    return_dict = False
    items = files
    if isinstance(files, dict):
        return_dict = True
        items = list(files.items())

    fixed = []
    for p, c in items:
        if p.endswith('.css'):
            content = c.rstrip()
            open_p = content.count('(')
            close_p = content.count(')')
            if open_p > close_p:
                content += (")" * (open_p - close_p)) + ";"
            open_b = content.count('{')
            close_b = content.count('}')
            if open_b > close_b:
                content += "\n" + ("}\n" * (open_b - close_b))
            elif close_b > open_b:
                # Strip excess closing braces (e.g. model emits "}}" at end of a rule).
                # Walk from the end removing bare stray "}" that have no matching "{"
                # by targeting the most common pattern: ";}" followed immediately by "}".
                extra = close_b - open_b
                content = re.sub(r'(?<=;|\})(\s*\}){1,' + str(extra) + r'}(?=\s*(?:\.|#|@|$))',
                                 lambda m, e=extra: m.group(0)[max(0, len(m.group(0))-e):],
                                 content)
                # Fallback: if count still off, strip raw trailing excess braces
                open_b2 = content.count('{')
                close_b2 = content.count('}')
                if close_b2 > open_b2:
                    content = re.sub(r'\}(?=\})', '', content, count=close_b2 - open_b2)
            fixed.append((p, content))
        else:
            fixed.append((p, c))
    return dict(fixed) if return_dict else fixed



def auto_fix_css_coverage_gaps(
    files: List[Tuple[str, str]],
    missing_classes: List[str],
    section_name: str = "",
    style_spec: Optional[Any] = None
) -> List[Tuple[str, str]]:
    """Injects sensible default CSS rules for unstyled classNames."""
    fixed = []
    for p, c in files:
        if p.endswith('.css'):
            content = c.rstrip() + "\n\n/* [AUTO-REPAIR]: Injected styles for missing classes */\n"
            for cls in missing_classes:
                m = re.search(r"class '\.([^']+)'", cls)
                cname = m.group(1) if m else cls.lstrip('.')
                if f".{cname}" in content:
                    continue
                if "form" in cname:
                    content += f".{cname} {{\n  display: flex;\n  flex-direction: column;\n  gap: 1.25rem;\n  width: 100%;\n}}\n\n"
                elif "input" in cname or "textarea" in cname or "select" in cname:
                    content += f".{cname} {{\n  padding: 0.75rem 1rem;\n  border-radius: 8px;\n  border: 1px solid rgba(255, 255, 255, 0.15);\n  background: rgba(255, 255, 255, 0.05);\n  color: inherit;\n}}\n\n"
                elif "btn" in cname or "button" in cname:
                    content += f".{cname} {{\n  display: inline-flex;\n  align-items: center;\n  justify-content: center;\n  padding: 0.75rem 1.5rem;\n  border-radius: 8px;\n  background: var(--accent-color, #3b82f6);\n  color: #fff;\n  cursor: pointer;\n}}\n\n"
                elif "card" in cname:
                    content += f".{cname} {{\n  padding: 1.5rem;\n  border-radius: 12px;\n  background: var(--color-surface, rgba(255, 255, 255, 0.03));\n  border: 1px solid rgba(255, 255, 255, 0.08);\n}}\n\n"
                else:
                    content += f".{cname} {{\n  display: block;\n}}\n\n"
            fixed.append((p, content))
        else:
            fixed.append((p, c))
    return fixed


def check_repeated_item_spacing_lint(tsx: str, css: str, file_path: str = "", allow_tailwind: bool = False) -> List[str]:
    """
    Structural lint:
    For any list of 2+ sibling elements sharing the same class or tag (e.g. repeated nav links, cards, badges, map lists),
    verifies that their direct parent's computed layout includes either gap, justify-content spacing,
    or a margin rule between siblings.
    Flags gap-on-wrong-ancestor bugs where gap is defined on a single-child wrapper instead of the repeated items parent.
    """
    root = extract_jsx_elements(tsx)
    groups = find_repeated_item_groups(root)
    map_groups = find_map_repeated_items(tsx)
    for mg in map_groups:
        if not any(g.get('item_class') == mg['item_class'] for g in groups):
            groups.append(mg)

    if not groups:
        return []

    rules = parse_css_blocks(css)
    violations = []
    prefix = f"[{file_path}] " if file_path else ""
    seen_parents = set()

    for grp in groups:
        parent = grp['parent']
        item_count = grp['item_count']
        item_cls = grp.get('item_class')
        item_tag = (grp.get('item_tag') or "").lower()
        parent_cls = parent.get('class_name')
        parent_tag = (parent.get('tag') or "").lower()

        if allow_tailwind and parent_cls:
            utility_tokens = parent_cls.split()
            if any(token.startswith(("gap-", "gap-x-", "gap-y-", "space-x-", "space-y-"))
                   or token in {"justify-between", "justify-around", "justify-evenly"}
                   for token in utility_tokens):
                continue

        if item_tag in _SVG_TAGS or parent_tag in _SVG_TAGS:
            continue

        if parent_tag == '__root__':
            continue

        parent_key = (parent_tag, parent_cls)
        if parent_key in seen_parents:
            continue

        parent_selectors = []
        if parent_cls:
            for c in parent_cls.split():
                parent_selectors.append(f".{c}")
        if parent_tag and parent_tag not in ('div', 'section'):
            parent_selectors.append(parent_tag)

        item_selectors = []
        if item_cls:
            for c in item_cls.split():
                item_selectors.append(f".{c}")
        if item_tag and item_tag not in ('div', 'span'):
            item_selectors.append(item_tag)

        has_direct_gap = False
        has_direct_justify_spacing = False
        has_sibling_margin = False
        is_absolute_positioned = False

        for sel, body in rules:
            targets_parent = any(ps in sel for ps in parent_selectors) if parent_selectors else False
            targets_item = any(item_s in sel for item_s in item_selectors) if item_selectors else False
            targets_parent_children = any(f"{ps} >" in sel or f"{ps} " in sel for ps in parent_selectors) if parent_selectors else False

            if targets_parent:
                if re.search(r'\b(?:gap|column-gap|row-gap|grid-gap)\s*:\s*([^;]+)', body):
                    has_direct_gap = True
                if re.search(r'\bjustify-content\s*:\s*(?:space-between|space-around|space-evenly)', body):
                    has_direct_justify_spacing = True
                if re.search(r'\bposition\s*:\s*(?:absolute|fixed)', body):
                    is_absolute_positioned = True

            if targets_item or targets_parent_children:
                if re.search(r'\b(?:gap|column-gap|row-gap|grid-gap)\s*:\s*([^;]+)', body):
                    has_direct_gap = True
                if re.search(r'\bposition\s*:\s*absolute', body):
                    is_absolute_positioned = True
                m_search = re.search(r'\b(?:margin|margin-right|margin-left|margin-bottom|margin-top|margin-inline)\s*:\s*([^;]+)', body)
                if m_search:
                    m_val = m_search.group(1).strip()
                    if m_val not in ('0', '0px', '0rem', 'none', 'auto'):
                        has_sibling_margin = True

        if has_direct_gap or has_direct_justify_spacing or has_sibling_margin or is_absolute_positioned:
            continue

        ancestor = parent.get('parent')
        ancestor_with_gap = None
        if ancestor and ancestor.get('tag') != '__root__':
            anc_children = ancestor.get('children', [])
            if len(anc_children) == 1:
                anc_cls = ancestor.get('class_name')
                anc_selectors = []
                if anc_cls:
                    for c in anc_cls.split():
                        anc_selectors.append(f".{c}")
                if ancestor.get('tag') not in ('div', 'section'):
                    anc_selectors.append(ancestor.get('tag'))

                for sel, body in rules:
                    if any(as_el in sel for as_el in anc_selectors):
                        if re.search(r'\b(?:gap|column-gap|row-gap|grid-gap)\s*:', body):
                            ancestor_with_gap = f".{anc_cls.split()[0]}" if anc_cls else f"<{ancestor.get('tag')}>"
                            break

        seen_parents.add(parent_key)
        p_display = f".{parent_cls.split()[0]}" if parent_cls else f"<{parent_tag}>"
        i_display = f".{item_cls.split()[0]}" if item_cls else f"<{item_tag}>"

        if ancestor_with_gap:
            violations.append(
                f"{prefix}[REPEATED ITEM SPACING LINT]: Direct parent '{p_display}' of {item_count} repeated items ('{i_display}') "
                f"has no 'gap' or margin rule. Meanwhile, ancestor '{ancestor_with_gap}' defines 'gap' on a single-child wrapper. "
                f"Declare 'display: flex; gap: ...;' directly on the items' direct parent '{p_display}'."
            )
        else:
            violations.append(
                f"{prefix}[REPEATED ITEM SPACING LINT]: Container '{p_display}' holds repeated items ('{i_display}') "
                f"without any 'gap' or margin spacing defined on their direct parent. "
                f"Declare 'display: flex/grid' with 'gap' on '{p_display}' to ensure items do not render squished together."
            )

    return violations


def auto_fix_repeated_item_spacing(css: str, violations: List[str]) -> str:
    """
    Auto-fixes repeated item spacing violations by injecting display: flex/grid and gap
    onto the direct parent container.
    """
    fixed_css = css
    for v in violations:
        if "[REPEATED ITEM SPACING LINT]" not in v:
            continue

        p_match = re.search(r"(?:Direct parent|Container)\s+'([^']+)'", v)
        if not p_match:
            continue
        parent_sel = p_match.group(1).strip()

        anc_match = re.search(r"ancestor\s+'([^']+)'\s+defines\s+'gap'", v)
        anc_sel = anc_match.group(1).strip() if anc_match else None

        gap_val = "1.5rem"
        if anc_sel:
            m_anc = re.search(re.escape(anc_sel) + r'\s*\{[^}]*?\bgap\s*:\s*([^;]+)', fixed_css)
            if m_anc:
                gap_val = m_anc.group(1).strip()

        is_grid = any(k in parent_sel.lower() for k in ('grid', 'cards', 'bento', 'tiers'))
        if is_grid:
            rules_to_inject = f"  display: grid;\n  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));\n  gap: {gap_val};"
        else:
            rules_to_inject = f"  display: flex;\n  align-items: center;\n  gap: {gap_val};\n  list-style: none;"

        if parent_sel in fixed_css:
            fixed_css = re.sub(
                rf'({re.escape(parent_sel)}\s*\{{)([^}}]*?)(\}})',
                lambda m: f"{m.group(1)}{m.group(2)}\n{rules_to_inject}\n{m.group(3)}",
                fixed_css
            )
        else:
            fixed_css += f"\n\n{parent_sel} {{\n{rules_to_inject}\n}}\n"

    return fixed_css


# ==============================================================================
# Verified Icon Reference Table & Authenticity Validation
# ==============================================================================

ICON_ART_DIRECTIONS: Dict[str, Dict[str, Any]] = {
    "outline-round": {"stroke_width": 1.75, "linecap": "round", "linejoin": "round", "fill": "none"},
    "outline-square": {"stroke_width": 1.5, "linecap": "square", "linejoin": "miter", "fill": "none"},
    "filled-geometric": {"stroke_width": 0, "linecap": "butt", "linejoin": "miter", "fill": "currentColor"},
    "duotone": {"stroke_width": 1.5, "linecap": "round", "linejoin": "round", "fill": "currentColor", "accent_opacity": 0.22},
    "micro-technical": {"stroke_width": 1.25, "linecap": "square", "linejoin": "miter", "fill": "none"},
}


def get_icon_art_direction(name: str = "outline-round") -> Dict[str, Any]:
    """Return normalized icon styling; brand marks must remain supplied assets."""
    return dict(ICON_ART_DIRECTIONS.get(name, ICON_ART_DIRECTIONS["outline-round"]))


VERIFIED_ICON_LOOKUP: Dict[str, Dict[str, Any]] = {
    "mail": {
        "canonical_name": "mail",
        "canonical_class": "feather feather-mail",
        "aliases": ["email", "envelope", "contact-email"],
        "elements": '<path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" /><polyline points="22,6 12,13 2,6" />',
        "reference_paths": [
            "M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z",
            "22,6 12,13 2,6",
        ],
    },
    "phone": {
        "canonical_name": "phone",
        "canonical_class": "feather feather-phone",
        "aliases": ["telephone", "call", "mobile", "contact-phone"],
        "elements": '<path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z" />',
        "reference_paths": [
            "M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z",
        ],
    },
    "map-pin": {
        "canonical_name": "map-pin",
        "canonical_class": "feather feather-map-pin",
        "aliases": ["location", "pin", "address", "map", "contact-address"],
        "elements": '<path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" /><circle cx="12" cy="10" r="3" />',
        "reference_paths": [
            "M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z",
        ],
    },
    "coffee": {
        "canonical_name": "coffee",
        "canonical_class": "feather feather-coffee",
        "aliases": ["mug", "cup", "cafe", "roast"],
        "elements": '<path d="M18 8h1a4 4 0 0 1 0 8h-1" /><path d="M2 8h16v9a4 4 0 0 1-4 4H6a4 4 0 0 1-4-4V8z" /><line x1="6" y1="1" x2="6" y2="4" /><line x1="10" y1="1" x2="10" y2="4" /><line x1="14" y1="1" x2="14" y2="4" />',
        "reference_paths": [
            "M18 8h1a4 4 0 0 1 0 8h-1",
            "M2 8h16v9a4 4 0 0 1-4 4H6a4 4 0 0 1-4-4V8z",
        ],
    },
    "flame": {
        "canonical_name": "flame",
        "canonical_class": "feather feather-flame",
        "aliases": ["fire", "hot", "heat", "roasting"],
        "elements": '<path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z" />',
        "reference_paths": [
            "M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z",
        ],
    },
    "box": {
        "canonical_name": "box",
        "canonical_class": "feather feather-box",
        "aliases": ["package", "delivery", "shipping"],
        "elements": '<line x1="16.5" y1="9.4" x2="7.5" y2="4.21" /><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" /><polyline points="3.27 6.96 12 12.01 20.73 6.96" /><line x1="12" y1="22.08" x2="12" y2="12" />',
        "reference_paths": [
            "M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z",
        ],
    },
    "check": {
        "canonical_name": "check",
        "canonical_class": "feather feather-check",
        "aliases": ["check-mark", "tick", "success"],
        "elements": '<polyline points="20 6 9 17 4 12" />',
        "reference_paths": [
            "20 6 9 17 4 12",
        ],
    },
    "star": {
        "canonical_name": "star",
        "canonical_class": "feather feather-star",
        "aliases": ["rating", "featured"],
        "elements": '<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />',
        "reference_paths": [
            "12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2",
        ],
    },
    "clock": {
        "canonical_name": "clock",
        "canonical_class": "feather feather-clock",
        "aliases": ["time", "hours"],
        "elements": '<circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" />',
        "reference_paths": [
            "12 6 12 12 16 14",
        ],
    },
    "calendar": {
        "canonical_name": "calendar",
        "canonical_class": "feather feather-calendar",
        "aliases": ["schedule", "date"],
        "elements": '<rect x="3" y="4" width="18" height="18" rx="2" ry="2" /><line x1="16" y1="2" x2="16" y2="6" /><line x1="8" y1="2" x2="8" y2="6" /><line x1="3" y1="10" x2="21" y2="10" />',
        "reference_paths": [
            "3 4 18 18",
        ],
    },
    "shield": {
        "canonical_name": "shield",
        "canonical_class": "feather feather-shield",
        "aliases": ["security", "protect", "guarantee"],
        "elements": '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />',
        "reference_paths": [
            "M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z",
        ],
    },
    "search": {
        "canonical_name": "search",
        "canonical_class": "feather feather-search",
        "aliases": ["lookup", "find"],
        "elements": '<circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />',
        "reference_paths": [
            "21 21 16.65 16.65",
        ],
    },
    "user": {
        "canonical_name": "user",
        "canonical_class": "feather feather-user",
        "aliases": ["profile", "account", "person"],
        "elements": '<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" /><circle cx="12" cy="7" r="4" />',
        "reference_paths": [
            "M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2",
        ],
    },
    "arrow-right": {
        "canonical_name": "arrow-right",
        "canonical_class": "feather feather-arrow-right",
        "aliases": ["forward", "arrow"],
        "elements": '<line x1="5" y1="12" x2="19" y2="12" /><polyline points="12 5 19 12 12 19" />',
        "reference_paths": [
            "12 5 19 12 12 19",
        ],
    },
    "zap": {
        "canonical_name": "zap",
        "canonical_class": "feather feather-zap",
        "aliases": ["bolt", "flash", "lightning", "energy"],
        "elements": '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />',
        "reference_paths": [
            "13 2 3 14 12 14 11 22 21 10 12 10 13 2",
        ],
    },
    "heart": {
        "canonical_name": "heart",
        "canonical_class": "feather feather-heart",
        "aliases": ["like", "favorite"],
        "elements": '<path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />',
        "reference_paths": [
            "M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z",
        ],
    },
    "database": {
        "canonical_name": "database",
        "canonical_class": "feather feather-database",
        "aliases": ["db", "storage", "sql", "data"],
        "elements": '<ellipse cx="12" cy="5" rx="9" ry="3" /><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" /><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" />',
        "reference_paths": [
            "M21 12c0 1.66-4 3-9 3s-9-1.34-9-3",
            "M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5",
            "12 5 9 3",
        ],
    },
    "lock": {
        "canonical_name": "lock",
        "canonical_class": "feather feather-lock",
        "aliases": ["security", "padlock", "private"],
        "elements": '<rect x="3" y="11" width="18" height="11" rx="2" ry="2" /><path d="M7 11V7a5 5 0 0 1 10 0v4" />',
        "reference_paths": [
            "M7 11V7a5 5 0 0 1 10 0v4",
            "3 11 18 11",
        ],
    },
    "activity": {
        "canonical_name": "activity",
        "canonical_class": "feather feather-activity",
        "aliases": ["pulse", "heartbeat", "monitoring", "telemetry", "tracing"],
        "elements": '<polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />',
        "reference_paths": [
            "22 12 18 12 15 21 9 3 6 12 2 12",
        ],
    },
    "server": {
        "canonical_name": "server",
        "canonical_class": "feather feather-server",
        "aliases": ["host", "node", "infrastructure"],
        "elements": '<rect x="2" y="2" width="20" height="8" rx="2" ry="2" /><rect x="2" y="14" width="20" height="8" rx="2" ry="2" /><line x1="6" y1="6" x2="6.01" y2="6" /><line x1="6" y1="18" x2="6.01" y2="18" />',
        "reference_paths": [
            "2 2 20 8",
            "2 14 20 8",
        ],
    },
    "cpu": {
        "canonical_name": "cpu",
        "canonical_class": "feather feather-cpu",
        "aliases": ["processor", "chip", "compute"],
        "elements": '<rect x="4" y="4" width="16" height="16" rx="2" ry="2" /><rect x="9" y="9" width="6" height="6" /><line x1="9" y1="1" x2="9" y2="4" /><line x1="15" y1="1" x2="15" y2="4" /><line x1="9" y1="20" x2="9" y2="23" /><line x1="15" y1="20" x2="15" y2="23" /><line x1="20" y1="9" x2="23" y1="9" /><line x1="20" y1="15" x2="23" y1="15" /><line x1="1" y1="9" x2="4" y1="9" /><line x1="1" y1="15" x2="4" y1="15" />',
        "reference_paths": [
            "4 4 16 16",
            "9 9 6 6",
        ],
    },
    "bar-chart-2": {
        "canonical_name": "bar-chart-2",
        "canonical_class": "feather feather-bar-chart-2",
        "aliases": ["chart", "analytics", "metrics", "stats", "graph"],
        "elements": '<line x1="18" y1="20" x2="18" y2="10" /><line x1="12" y1="20" x2="12" y2="4" /><line x1="6" y1="20" x2="6" y2="14" />',
        "reference_paths": [
            "18 20 18 10",
            "12 20 12 4",
            "6 20 6 14",
        ],
    },
    "layers": {
        "canonical_name": "layers",
        "canonical_class": "feather feather-layers",
        "aliases": ["stack", "pipeline", "architecture"],
        "elements": '<polygon points="12 2 2 7 12 12 22 7 12 2" /><polyline points="2 17 12 22 22 17" /><polyline points="2 12 12 17 22 12" />',
        "reference_paths": [
            "12 2 2 7 12 12 22 7 12 2",
            "2 17 12 22 22 17",
            "2 12 12 17 22 12",
        ],
    },
    "terminal": {
        "canonical_name": "terminal",
        "canonical_class": "feather feather-terminal",
        "aliases": ["console", "command-line", "cli", "prompt"],
        "elements": '<polyline points="4 17 10 11 4 5" /><line x1="12" y1="19" x2="20" y2="19" />',
        "reference_paths": [
            "4 17 10 11 4 5",
            "12 19 20 19",
        ],
    },
    "twitter": {
        "canonical_name": "twitter",
        "canonical_class": "feather feather-twitter",
        "aliases": ["tweet", "social-twitter", "fa-twitter", "x-social"],
        "elements": '<path d="M23 3a10.9 10.9 0 0 1-3.14 1.53 4.48 4.48 0 0 0-7.86 3v1A10.66 10.66 0 0 1 3 4s-4 9 5 13a11.64 11.64 0 0 1-7 2c9 5 20 0 20-11.5a4.5 4.5 0 0 0-.08-.83A7.72 7.72 0 0 0 23 3z" />',
        "reference_paths": [
            "M23 3a10.9 10.9 0 0 1-3.14 1.53",
        ],
    },
    "facebook": {
        "canonical_name": "facebook",
        "canonical_class": "feather feather-facebook",
        "aliases": ["social-facebook", "fa-facebook", "fa-facebook-f"],
        "elements": '<path d="M18 2h-3a5 5 0 0 0-5 5v3H7v4h3v8h4v-8h3l1-4h-4V7a1 1 0 0 1 1-1h3z" />',
        "reference_paths": [
            "M18 2h-3a5 5 0 0 0-5 5v3H7v4h3v8h4v-8h3l1-4h-4V7a1 1 0 0 1 1-1h3z",
        ],
    },
    "linkedin": {
        "canonical_name": "linkedin",
        "canonical_class": "feather feather-linkedin",
        "aliases": ["social-linkedin", "fa-linkedin", "fa-linkedin-in"],
        "elements": '<path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-2-2 2 2 0 0 0-2 2v7h-4v-7a6 6 0 0 1 6-6z" /><rect x="2" y="9" width="4" height="12" /><circle cx="4" cy="4" r="2" />',
        "reference_paths": [
            "M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-2-2 2 2 0 0 0-2 2v7h-4v-7a6 6 0 0 1 6-6z",
            "2 9 4 12",
        ],
    },
    "instagram": {
        "canonical_name": "instagram",
        "canonical_class": "feather feather-instagram",
        "aliases": ["social-instagram", "fa-instagram", "insta"],
        "elements": '<rect x="2" y="2" width="20" height="20" rx="5" ry="5" /><path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z" /><line x1="17.5" y1="6.5" x2="17.51" y2="6.5" />',
        "reference_paths": [
            "M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z",
            "2 2 20 20",
        ],
    },
    "github": {
        "canonical_name": "github",
        "canonical_class": "feather feather-github",
        "aliases": ["social-github", "fa-github", "git"],
        "elements": '<path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22" />',
        "reference_paths": [
            "M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87",
        ],
    },
    "globe": {
        "canonical_name": "globe",
        "canonical_class": "feather feather-globe",
        "aliases": ["world", "website", "internet", "web"],
        "elements": '<circle cx="12" cy="12" r="10" /><line x1="2" y1="12" x2="22" y2="12" /><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />',
        "reference_paths": [
            "12 12 10",
            "M12 2a15.3 15.3 0 0 1 4 10",
        ],
    },
}

FAKE_ICON_NAMES: Dict[str, str] = {
    "mug-hot": "coffee",
    "feather-mug-hot": "coffee",
    "fa-mug-hot": "coffee",
    "fire-flame-curved": "flame",
    "feather-fire-flame-curved": "flame",
    "fa-fire-flame-curved": "flame",
    "phone-volume": "phone",
    "envelope-open": "mail",
    "location-dot": "map-pin",
    "bolt": "zap",
    "feather-bolt": "zap",
    "fa-bolt": "zap",
    "fa-twitter": "twitter",
    "fa-facebook": "facebook",
    "fa-facebook-f": "facebook",
    "fa-linkedin": "linkedin",
    "fa-linkedin-in": "linkedin",
    "fa-instagram": "instagram",
    "fa-github": "github",
}

REAL_FEATHER_ICONS = set(VERIFIED_ICON_LOOKUP.keys()) | {
    "activity", "airplay", "alert-circle", "alert-octagon", "alert-triangle", "align-center", "align-justify",
    "align-left", "align-right", "anchor", "aperture", "archive", "arrow-down", "arrow-down-circle",
    "arrow-down-left", "arrow-down-right", "arrow-left", "arrow-left-circle", "arrow-right", "arrow-right-circle",
    "arrow-up", "arrow-up-circle", "arrow-up-left", "arrow-up-right", "at-sign", "award", "bar-chart", "bar-chart-2",
    "battery", "battery-charging", "bell", "bell-off", "bluetooth", "bold", "book", "book-open", "bookmark",
    "box", "briefcase", "calendar", "camera", "camera-off", "cast", "check", "check-circle", "check-square",
    "chevron-down", "chevron-left", "chevron-right", "chevron-up", "chevrons-down", "chevrons-left", "chevrons-right",
    "chevrons-up", "chrome", "circle", "clipboard", "clock", "cloud", "cloud-drizzle", "cloud-lightning", "cloud-off",
    "cloud-rain", "cloud-snow", "code", "codepen", "codesandbox", "coffee", "columns", "command", "compass",
    "copy", "corner-down-left", "corner-down-right", "corner-left-down", "corner-left-up", "corner-right-down",
    "corner-right-up", "corner-up-left", "corner-up-right", "cpu", "credit-card", "crop", "crosshair", "database",
    "delete", "disc", "divide", "divide-circle", "divide-square", "dollar-sign", "download", "download-cloud",
    "dribbble", "droplet", "edit", "edit-2", "edit-3", "external-link", "eye", "eye-off", "facebook", "fast-forward",
    "feather", "figma", "file", "file-minus", "file-plus", "file-text", "film", "filter", "flag", "folder",
    "folder-minus", "folder-plus", "framer", "frown", "gift", "git-branch", "git-commit", "git-merge", "git-pull-request",
    "github", "gitlab", "globe", "grid", "hard-drive", "hash", "headphones", "heart", "help-circle", "hexagon",
    "home", "image", "inbox", "info", "instagram", "italic", "key", "layers", "layout", "life-buoy", "link",
    "link-2", "linkedin", "list", "loader", "lock", "log-in", "log-out", "mail", "map", "map-pin", "maximize",
    "maximize-2", "meh", "menu", "message-circle", "message-square", "mic", "mic-off", "minimize", "minimize-2",
    "minus", "minus-circle", "minus-square", "monitor", "moon", "more-horizontal", "more-vertical", "mouse-pointer",
    "move", "music", "navigation", "navigation-2", "octagon", "package", "paperclip", "pause", "pause-circle",
    "pen-tool", "percent", "phone", "phone-call", "phone-forwarded", "phone-incoming", "phone-missed", "phone-off",
    "phone-outgoing", "pie-chart", "play", "play-circle", "plus", "plus-circle", "plus-square", "pocket", "power",
    "printer", "radio", "refresh-ccw", "refresh-cw", "repeat", "rewind", "rotate-ccw", "rotate-cw", "rss", "save",
    "scissors", "search", "send", "server", "settings", "share", "share-2", "shield", "shield-off", "shopping-bag",
    "shopping-cart", "shuffle", "sidebar", "skip-back", "skip-forward", "slack", "slash", "sliders", "smartphone",
    "smile", "speaker", "square", "star", "stop-circle", "sun", "sunrise", "sunset", "tablet", "tag", "target",
    "terminal", "thermometer", "thumbs-down", "thumbs-up", "toggle-left", "toggle-right", "tool", "trash", "trash-2",
    "trello", "trending-down", "trending-up", "triangle", "truck", "tv", "twitch", "twitter", "type", "umbrella",
    "underline", "unlock", "upload", "upload-cloud", "user", "user-check", "user-minus", "user-plus", "user-x",
    "users", "video", "video-off", "voicemail", "volume", "volume-1", "volume-2", "volume-x", "watch", "wifi",
    "wifi-off", "wind", "x", "x-circle", "x-octagon", "x-square", "youtube", "zap", "zap-off", "zoom-in", "zoom-out"
}


def _norm_path(s: str) -> str:
    """Normalizes path commands and coordinates for robust whitespace-invariant matching."""
    return re.sub(r'[\s,]+', ' ', s.strip().lower())


def resolve_canonical_icon(name: str) -> Optional[Dict[str, Any]]:
    clean = name.strip().lower()
    clean = re.sub(r'^(?:feather|lucide|fa|icon)[-_ ]+', '', clean)
    if clean in VERIFIED_ICON_LOOKUP:
        return VERIFIED_ICON_LOOKUP[clean]
    if clean in FAKE_ICON_NAMES:
        target = FAKE_ICON_NAMES[clean]
        return VERIFIED_ICON_LOOKUP.get(target)
    for k, data in VERIFIED_ICON_LOOKUP.items():
        if clean == k or clean in data.get("aliases", []):
            return data
    return None


def get_verified_inline_svg(name: str, extra_class: str = "", stroke_width: int = 2) -> str:
    """Returns a complete, self-contained verified SVG string for a given canonical icon or alias."""
    icon_data = resolve_canonical_icon(name) or VERIFIED_ICON_LOOKUP["check"]
    canonical_cls = icon_data["canonical_class"]
    full_cls = f"{canonical_cls} {extra_class}".strip() if extra_class else canonical_cls
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        f'stroke="currentColor" strokeWidth="{stroke_width}" strokeLinecap="round" strokeLinejoin="round" '
        f'className="{full_cls}">\n  {icon_data["elements"]}\n</svg>'
    )


def check_icon_authenticity_lint(tsx_content: str, file_path: str = "") -> List[str]:
    """
    Validation check:
    If a class name matches a known icon-library naming pattern (feather-*, lucide-*, fa-*):
    1. Flags fake icon library names (e.g. feather-mug-hot, feather-fire-flame-curved).
    2. Validates that the SVG's <path> data matches the library's actual published path data.
    """
    violations = []
    svg_blocks = list(re.finditer(r'<svg\b([^>]*)>([\s\S]*?)</svg>', tsx_content, re.IGNORECASE))

    for m in svg_blocks:
        svg_attrs = m.group(1)
        svg_body = m.group(2)

        cls_match = re.search(r'class(?:Name)?=["\']([^"\']+)["\']', svg_attrs, re.IGNORECASE)
        if not cls_match:
            continue

        full_class = cls_match.group(1).strip()
        classes = full_class.split()

        for cls in classes:
            feather_m = re.search(r'feather-([a-z0-9-]+)', cls, re.IGNORECASE)
            lucide_m = re.search(r'lucide-([a-z0-9-]+)', cls, re.IGNORECASE)
            fa_m = re.search(r'fa-([a-z0-9-]+)', cls, re.IGNORECASE)

            target_lib = ""
            icon_name = ""
            if feather_m:
                target_lib = "feather"
                icon_name = feather_m.group(1).lower()
            elif lucide_m:
                target_lib = "lucide"
                icon_name = lucide_m.group(1).lower()
            elif fa_m:
                target_lib = "fa"
                icon_name = fa_m.group(1).lower()

            if not target_lib or not icon_name:
                continue

            # Check 1: Fake icon name in library
            if target_lib == "feather":
                if icon_name in FAKE_ICON_NAMES or icon_name not in REAL_FEATHER_ICONS:
                    canonical = FAKE_ICON_NAMES.get(icon_name, "coffee" if "mug" in icon_name else "flame" if "fire" in icon_name else "")
                    sugg = f" Use verified 'feather-{canonical}' or authentic inline SVG." if canonical else ""
                    violations.append(
                        f"[{file_path}] [FAKE ICON LINT]: Class '{cls}' is not an authentic Feather icon (hallucinated library name).{sugg}"
                    )
                    continue

            # Check 2: Geometry verification against published reference table
            icon_data = resolve_canonical_icon(icon_name)
            if icon_data and "reference_paths" in icon_data:
                extracted_paths = [
                    _norm_path(d) for d in re.findall(r'\bd=["\']([^"\']+)["\']', svg_body, re.IGNORECASE)
                ]
                extracted_points = [
                    _norm_path(pts) for pts in re.findall(r'\bpoints=["\']([^"\']+)["\']', svg_body, re.IGNORECASE)
                ]
                all_extracted = extracted_paths + extracted_points

                ref_paths = [_norm_path(p) for p in icon_data["reference_paths"]]
                primary_ref = ref_paths[0]
                matched = any(primary_ref in cand or cand in primary_ref for cand in all_extracted)

                if not matched:
                    violations.append(
                        f"[{file_path}] [ICON PATH MISMATCH]: SVG for '{cls}' contains hallucinated path coordinates that do not match authentic published geometry."
                    )

    return violations


def check_font_awesome_lint(tsx_content: str, file_path: str = "") -> List[str]:
    """
    Detects Font Awesome icon class usage (fab fa-*, fas fa-*, far fa-*).
    Font Awesome is never loaded in generated sites; these render as empty inline elements.
    The system prompt mandates verified inline SVGs — never icon font classes.
    """
    violations: List[str] = []
    label = f"[{file_path}] " if file_path else ""
    fa_matches = re.findall(
        r'class(?:Name)?=["\'][^"\']*\b(fa[brs]?\s+fa-[a-z0-9-]+)[^"\']*["\']',
        tsx_content,
        re.IGNORECASE,
    )
    if fa_matches:
        violations.append(
            f"{label}[FONT AWESOME ICON]: Found Font Awesome icon class(es) "
            f"{fa_matches[:3]} — Font Awesome is not loaded in generated sites. "
            f"Replace with verified inline SVGs (feather-twitter, feather-linkedin, etc.) "
            f"as documented in the system prompt icon set."
        )
    return violations


def check_hero_cta_lint(tsx_content: str, file_path: str = "") -> List[str]:
    """
    Detects contact links (mailto:, tel:) used as CTAs inside the hero section.
    Hero CTAs should be action-oriented ('Get Started', 'View Demo', 'Start Free Trial'),
    not shortcut links to email/phone. Those belong in Contact or Footer.
    """
    violations: List[str] = []
    label = f"[{file_path}] " if file_path else ""

    # Only flag if this looks like a hero component (has a hero section/class)
    if not re.search(r'id=["\']hero["\']|className=["\'][^"\']*\bhero\b[^"\']*["\']', tsx_content, re.IGNORECASE):
        return violations

    contact_ctas = re.findall(
        r'<a\s[^>]*href=["\'](?:mailto:|tel:)[^"\']*["\'][^>]*>([^<]+)</a>',
        tsx_content,
        re.IGNORECASE,
    )
    if contact_ctas:
        violations.append(
            f"{label}[HERO CTA MISUSE]: Found contact links {contact_ctas[:3]} used as "
            f"hero section CTAs. Hero CTAs must be action-oriented (e.g. 'Get Started', "
            f"'View Demo', 'Start Free Trial'). Contact links (mailto:, tel:) belong "
            f"in the Contact or Footer sections, not the Hero."
        )
    return violations


def auto_fix_icon_paths(tsx_content: str, violations: List[str]) -> str:
    """
    Replaces fake icon library names and hallucinated SVG path coordinates
    with authentic, recognizable published inline SVG geometry.
    """
    has_fake = any("[FAKE ICON LINT]" in v or "[ICON PATH MISMATCH]" in v for v in violations)
    if not has_fake:
        return tsx_content

    fixed_tsx = tsx_content

    def _replace_svg(match: re.Match) -> str:
        full_svg = match.group(0)
        attrs = match.group(1)
        body = match.group(2)

        cls_match = re.search(r'class(?:Name)?=["\']([^"\']+)["\']', attrs, re.IGNORECASE)
        cls_str = cls_match.group(1) if cls_match else ""

        target_icon_data: Optional[Dict[str, Any]] = None

        for token in cls_str.split():
            clean = re.sub(r'^(?:feather|lucide|fa|icon)[-_ ]+', '', token.lower())
            icon_data = resolve_canonical_icon(clean)
            if icon_data:
                target_icon_data = icon_data
                break

        if not target_icon_data:
            if any(k in body.lower() or k in cls_str.lower() for k in ("mail", "email", "envelope")):
                target_icon_data = VERIFIED_ICON_LOOKUP["mail"]
            elif any(k in body.lower() or k in cls_str.lower() for k in ("phone", "call", "tel")):
                target_icon_data = VERIFIED_ICON_LOOKUP["phone"]
            elif any(k in body.lower() or k in cls_str.lower() for k in ("pin", "map", "address", "location")):
                target_icon_data = VERIFIED_ICON_LOOKUP["map-pin"]
            elif any(k in body.lower() or k in cls_str.lower() for k in ("mug", "coffee", "cup", "roast")):
                target_icon_data = VERIFIED_ICON_LOOKUP["coffee"]
            elif any(k in body.lower() or k in cls_str.lower() for k in ("fire", "flame", "heat")):
                target_icon_data = VERIFIED_ICON_LOOKUP["flame"]
            elif any(k in body.lower() or k in cls_str.lower() for k in ("box", "package", "delivery")):
                target_icon_data = VERIFIED_ICON_LOOKUP["box"]

        if not target_icon_data:
            return full_svg

        canonical_class = target_icon_data["canonical_class"]
        elements = target_icon_data["elements"]

        extra_classes = " ".join([
            c for c in cls_str.split()
            if not c.startswith("feather") and not c.startswith("fa-") and not c.startswith("lucide-")
        ])
        combined_class = f"{canonical_class} {extra_classes}".strip() if extra_classes else canonical_class

        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
            f'stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" '
            f'className="{combined_class}">\n  {elements}\n</svg>'
        )

    fixed_tsx = re.sub(r'<svg\b([^>]*)>([\s\S]*?)</svg>', _replace_svg, fixed_tsx, flags=re.IGNORECASE)
    return fixed_tsx


def check_content_leak_lint(tsx_content: str, file_path: str = "") -> List[str]:
    """
    Hard safety-net validator that scans the rendered JSX of any section for leaked
    internal content plans, scaffolding placeholders, and raw field schema strings:
    1. Section type name standing alone as a heading (e.g. <h2>Hero</h2>, <h2>Features</h2>, <h2>Contact</h2>)
    2. Any instance of "Specialized .* implementation for" or "Specialized offering and verified capability"
    3. Any bare "Series 0[0-9]\b" pattern
    4. Any field-label-style UI text where a schema name was used verbatim ("Feature Icon", "Capability Metric", "Description Tagline", "An Inquiry Form")
    """
    violations = []
    prefix = f"[{file_path}] " if file_path else ""

    # 1. Bare section type name standing alone as a heading
    sec_names = ["Hero", "Header", "Features", "Contact", "Footer"]
    for sec_name in sec_names:
        # Check <h1..6...>Hero</h1..6>
        m_h = re.search(
            rf'<h[1-6]\b[^>]*>\s*{re.escape(sec_name)}\s*</h[1-6]>',
            tsx_content,
            re.IGNORECASE
        )
        if m_h:
            violations.append(
                f"{prefix}[CONTENT LEAK LINT]: Section type name '{sec_name}' used directly as heading ({m_h.group(0)}). "
                f"Headings must contain authentic brand or value-proposition copy, not section type names."
            )

        # Check className="...title...">Hero<
        m_cls = re.search(
            rf'className=["\'][^"\']*(?:title|heading)[^"\']*["\'][^>]*>\s*{re.escape(sec_name)}\s*<',
            tsx_content,
            re.IGNORECASE
        )
        if m_cls and not any(sec_name in v for v in violations):
            violations.append(
                f"{prefix}[CONTENT LEAK LINT]: Section type name '{sec_name}' used directly as title ({m_cls.group(0)}). "
                f"Headings must contain authentic brand or value-proposition copy, not section type names."
            )

    # 2. Any instance of "Specialized .* implementation for"
    m_spec = re.search(r'Specialized\s+[\w\s-]+\s+implementation\s+for\b', tsx_content, re.IGNORECASE)
    if m_spec:
        violations.append(
            f"{prefix}[CONTENT LEAK LINT]: Template sentence '{m_spec.group(0)}' detected in rendered JSX. "
            f"Provide authentic, domain-appropriate descriptions."
        )

    m_spec2 = re.search(r'Specialized\s+offering\s+and\s+verified\s+capability\s+for\b', tsx_content, re.IGNORECASE)
    if m_spec2:
        violations.append(
            f"{prefix}[CONTENT LEAK LINT]: Template sentence '{m_spec2.group(0)}' detected in rendered JSX. "
            f"Provide authentic, domain-appropriate descriptions."
        )

    # 3. Any bare "Series 0[0-9]\b" pattern
    m_series = re.search(r'\bSeries\s+0[0-9]\b', tsx_content)
    if m_series:
        violations.append(
            f"{prefix}[CONTENT LEAK LINT]: Bare placeholder series label '{m_series.group(0)}' detected in rendered JSX. "
            f"Provide authentic metrics or tags."
        )

    # 4. Field-label-style UI text where a schema name was used verbatim
    raw_schema_labels = [
        "Feature Icon",
        "Capability Metric",
        "Description Tagline",
        "Feature Title",
        "An Inquiry Form",
        "Inquiry Message Form",
        "Physical Address",
        "Direct Email",
        "Office Phone",
    ]
    for schema_label in raw_schema_labels:
        m_lbl = re.search(
            rf'<(?:span|p|div|label|h[1-6])\b[^>]*>\s*{re.escape(schema_label)}\s*</(?:span|p|div|label|h[1-6])>',
            tsx_content,
            re.IGNORECASE
        )
        if m_lbl:
            violations.append(
                f"{prefix}[CONTENT LEAK LINT]: Verbatim field-schema label '{schema_label}' rendered in UI ({m_lbl.group(0)}). "
                f"Do not render schema names as visible UI spans or labels; render authentic content directly."
            )

    # 5. Check for leaked internal prompt instruction preambles in rendered text
    instruction_leaks = [
        "a high-impact full-width banner",
        "contact information including address",
        "display exactly 4 items",
        "display exactly 3 items",
        "a multi-column footer with brand info",
    ]
    for instr_leak in instruction_leaks:
        if instr_leak in tsx_content.lower():
            violations.append(
                f"{prefix}[CONTENT LEAK LINT]: Internal section instruction text '{instr_leak}' leaked into rendered output. "
                f"Replace with authentic user-facing copy."
            )

    return violations


def check_dead_tab_state_lint(tsx_content: str, file_path: str = "") -> List[str]:
    """
    Detects the 'dead tab state' and 'dead drawer/modal state' anti-patterns:
    1. Dead tab state: activeTab controls styling (className conditional + setter onClick)
       but is never referenced in filtering or conditional rendering.
    2. Dead drawer/modal state: boolean toggle (isDrawerOpen, isOpen, etc.) is declared and
       toggled in onClick, but has zero effect outside setter calls (no conditional panel render,
       no dynamic class on nav/drawer).
    """
    violations: List[str] = []
    label = f"[{file_path}] " if file_path else ""

    # Find useState declarations e.g. const [activeTab, setActiveTab] = useState
    state_decls = re.findall(
        r"const\s+\[(\w+),\s*(\w+)\]\s*=\s*useState",
        tsx_content,
    )
    for var_name, setter_name in state_decls:
        is_tab = any(kw in var_name.lower() for kw in ("tab", "active", "selected", "filter", "panel", "step", "tier", "channel"))
        is_drawer = any(kw in var_name.lower() for kw in ("open", "menu", "drawer", "modal", "visible", "expanded", "show", "toggle"))

        if not (is_tab or is_drawer):
            continue

        in_onclick = bool(re.search(
            rf"{re.escape(setter_name)}\s*\(",
            tsx_content,
        ))
        if not in_onclick:
            continue

        # Check for dead drawer/modal/toggle state:
        if is_drawer:
            stripped = re.sub(rf"const\s+\[{re.escape(var_name)},\s*{re.escape(setter_name)}\]\s*=\s*useState[^;]+;", "", tsx_content)
            stripped = re.sub(rf"{re.escape(setter_name)}\s*\([^)]*\)", "", stripped)
            has_jsx_usage = bool(re.search(
                rf"\{{\s*{re.escape(var_name)}\s*&&"
                rf"|\{{\s*!{re.escape(var_name)}\s*&&"
                rf"|\b{re.escape(var_name)}\s*\?[^{{}}:]+:[^{{}}:]+"
                rf"|\b{re.escape(var_name)}\b",
                stripped,
            ))
            if not has_jsx_usage:
                violations.append(
                    f"{label}[DEAD DRAWER/MODAL STATE]: '{var_name}' is declared with useState and toggled via "
                    f"'{setter_name}' in an onClick handler, but '{var_name}' is never referenced in any conditional "
                    f"render expression (e.g. {{{var_name} && <div className=\"header__drawer\">...</div>}} or dynamic class). "
                    f"The mobile toggle or modal has zero effect on the rendered DOM. "
                    f"Either conditionally render the drawer/menu element or toggle an open-state class on the navigation."
                )
                continue

        # Check for dead tab state:
        in_classname = bool(re.search(
            rf"{re.escape(var_name)}\s*===|===\s*{re.escape(var_name)}",
            tsx_content,
        ))
        if is_tab and in_classname:
            code_no_classname = re.sub(r'className=\{`[^`]*`\}', '', tsx_content)
            content_usage = bool(re.search(
                rf"\.filter\([^)]*\b{re.escape(var_name)}\b"
                rf"|\.find\([^)]*\b{re.escape(var_name)}\b"
                rf"|\{{\s*{re.escape(var_name)}\s*==="
                rf"|\{{\s*{re.escape(var_name)}\s*!=="
                rf"|&&\s*\(?\s*{re.escape(var_name)}\b"
                rf"|{re.escape(var_name)}\s*&&"
                rf"|{re.escape(var_name)}\s*\?[^:]+:[^{{}}]{{1,200}}(?=<)",
                code_no_classname,
            ))
            if not content_usage:
                violations.append(
                    f"{label}[DEAD TAB STATE]: '{var_name}' is used for tab styling (className "
                    f"conditional + {setter_name} onClick) but never referenced in a "
                    f".filter(), .find(), or conditional render expression. All items render "
                    f"simultaneously — the tab switch has no effect on displayed content. "
                    f"Gate content rendering on '{var_name}': either filter the items array "
                    f"before .map() or conditionally render only the matching panel."
                )
    return violations


def check_logo_image_lint(tsx_content: str, file_path: str = "") -> List[str]:
    """
    Detects external photographic images (e.g. Unsplash stock photos) used as brand logos.
    Brand logos in header or footer must be stylized brand text or authentic inline SVGs,
    never large external stock photos.
    """
    violations: List[str] = []
    label = f"[{file_path}] " if file_path else ""

    img_matches = re.finditer(r'<img\b([^>]*)>', tsx_content, re.IGNORECASE)
    for m in img_matches:
        attrs = m.group(1)
        cls_match = re.search(r'class(?:Name)?=["\']([^"\']+)["\']', attrs, re.IGNORECASE)
        src_match = re.search(r'src=["\']([^"\']+)["\']', attrs, re.IGNORECASE)
        if not cls_match or not src_match:
            continue
        cls_val = cls_match.group(1).lower()
        src_val = src_match.group(1).lower()

        if any(k in cls_val for k in ("logo", "brand-mark", "brand_mark", "site-logo")):
            if any(p in src_val for p in ("unsplash.com", "pexels.com", "photo-", "images.unsplash")):
                violations.append(
                    f"{label}[STOCK PHOTO LOGO LINT]: Stock photograph URL '{src_match.group(1)[:60]}...' used as "
                    f"brand logo in <img className=\"{cls_match.group(1)}\">. "
                    f"Company logos must be stylized brand text or clean inline SVGs, never full-bleed stock photos."
                )
    return violations


def check_css_missing_dot_lint(css_content: str, file_path: str = "") -> List[str]:
    """
    Detects CSS selectors containing bare BEM class names without a leading dot ('.').
    E.g. '.site-root.header header__inner' instead of '.site-root.header .header__inner'.
    HTML tags never contain double underscores ('__'); these are authoring typos.
    """
    violations: List[str] = []
    label = f"[{file_path}] " if file_path else ""

    clean_css = re.sub(r'/\*[\s\S]*?\*/', '', css_content)
    clean_css = re.sub(r'"[^"]*"|\'[^\']*\'', '', clean_css)

    for m in re.finditer(r'([^{}@]+)\{', clean_css):
        selector_block = m.group(1)
        tokens = re.finditer(r'(?:^|[\s,>+~])([a-zA-Z0-9_-]+__[a-zA-Z0-9_-]+)(?=[\s,{>+~:.[])', selector_block)
        for tok in tokens:
            bare_bem = tok.group(1)
            violations.append(
                f"{label}[CSS SELECTOR SYNTAX]: Selector contains bare class name '{bare_bem}' without a leading dot ('.'). "
                f"Use '.{bare_bem}' instead."
            )
            break
    return violations


def check_site_root_misuse_lint(content: str, file_path: str = "") -> List[str]:
    """
    Detects if the model incorrectly applies or references the 'site-root' class
    in individual components or their CSS.
    The 'site-root' class is strictly reserved for the global App wrapper.
    """
    violations = []
    label = f"[{file_path}] " if file_path else ""

    # Check for className="site-root" or className="... site-root ..." in TSX
    if re.search(r'className=["\'][^"\']*?\bsite-root\b[^"\']*?["\']', content):
        violations.append(
            f"{label}[GLOBAL WRAPPER MISUSE]: Component applies 'site-root' to its className. "
            f"The 'site-root' class is exclusively for the global application wrapper. Remove it from this component."
        )
    # Check for .site-root selectors in CSS
    if (file_path.endswith(".css") or "{" in content) and re.search(r'(?:^|[,\s>+~])\.site-root\b', content):
        violations.append(
            f"{label}[GLOBAL WRAPPER MISUSE]: CSS references '.site-root' in its selectors. "
            f"The '.site-root' class belongs exclusively to the global application wrapper. Remove it from component CSS."
        )
    return violations


def validate_structural_quality(
    files: List[Tuple[str, str]],
    section_name: str = "",
    defined_tokens: Optional[Set[str]] = None,
    check_coverage: bool = False,
    tailwind_enabled: bool = False,
) -> List[str]:
    """
    Comprehensive structural quality gate checking:
    (a) Sticky misuse on non-header full-viewport sections
    (b) Duplicate class names across different heading levels (h2 and h3)
    (c) Placeholder metrics matching card titles
    (d) Undefined CSS custom properties in var(--xxx)
    (e) Repeated item spacing and gap placement (gap on direct parent, not outer wrapper)
    (f) CSS syntactic completeness (balanced braces and parens)
    (g) Optional CSS selector coverage
    (h) Icon library authenticity and verified path geometry
    (i) Content-plan leak detection (bare section names, template sentences, schema field labels)
    (j) Dead tab / drawer / modal state detection
    (k) Font Awesome icon class usage without loaded font
    (l) Hero CTA misuse (contact links instead of action CTAs)
    (m) Stock photo URL used as brand logo
    (n) CSS bare BEM selector missing dot syntax
    """
    violations = []
    if isinstance(files, dict):
        files = list(files.items())
    tsx_files = [(p, c) for p, c in files if p.endswith(".tsx") or p.endswith(".jsx")]
    css_files = [(p, c) for p, c in files if p.endswith(".css")]

    for fpath, fcontent in css_files:
        violations.extend(check_sticky_misuse_lint(fcontent, section_name=section_name, file_path=fpath))
        if defined_tokens:
            violations.extend(check_undefined_css_variables_lint(fcontent, defined_tokens, file_path=fpath))
        valid_syntax, syntax_errs = check_css_syntactic_completeness(fcontent, file_path=fpath)
        if not valid_syntax:
            violations.extend(syntax_errs)
        violations.extend(check_css_missing_dot_lint(fcontent, file_path=fpath))
        violations.extend(check_site_root_misuse_lint(fcontent, file_path=fpath))

    for fpath, fcontent in tsx_files:
        valid_tsx_syntax, tsx_syntax_errs = check_tsx_syntactic_completeness(fcontent, file_path=fpath)
        if not valid_tsx_syntax:
            violations.extend(tsx_syntax_errs)
        violations.extend(check_duplicate_heading_classes_lint(fcontent, file_path=fpath))
        violations.extend(check_placeholder_metrics_lint(fcontent, file_path=fpath))
        violations.extend(check_icon_authenticity_lint(fcontent, file_path=fpath))
        violations.extend(check_content_leak_lint(fcontent, file_path=fpath))
        violations.extend(check_dead_tab_state_lint(fcontent, file_path=fpath))
        violations.extend(check_font_awesome_lint(fcontent, file_path=fpath))
        violations.extend(check_hero_cta_lint(fcontent, file_path=fpath))
        violations.extend(check_logo_image_lint(fcontent, file_path=fpath))
        violations.extend(check_site_root_misuse_lint(fcontent, file_path=fpath))

        matching_css = ""
        base_stem = Path(fpath).stem
        for cp, cc in css_files:
            if Path(cp).stem == base_stem:
                matching_css += "\n" + cc
        if not matching_css and css_files:
            matching_css = "\n".join(cc for _, cc in css_files)
        if matching_css:
            violations.extend(check_repeated_item_spacing_lint(
                fcontent, matching_css, file_path=fpath, allow_tailwind=tailwind_enabled
            ))
            if check_coverage:
                valid_cov, missing_cov = check_css_selector_coverage(
                    fcontent, matching_css, file_path=fpath, allow_tailwind=tailwind_enabled
                )
                if not valid_cov:
                    violations.extend([f"[{fpath}] [CSS COVERAGE GAP]: Missing CSS rule for class '.{c}'" for c in missing_cov])

    return violations


def auto_fix_structural_violations(
    files: List[Tuple[str, str]],
    violations: List[str],
    section_name: str = "",
    defined_tokens: Optional[Set[str]] = None,
) -> List[Tuple[str, str]]:
    """
    Safely auto-adapts files when turn cap or retry limit is reached on structural violations.
    """
    return_dict = False
    if isinstance(files, dict):
        return_dict = True
        files = list(files.items())
    fixed_files = []
    has_sticky_violation = any("position: sticky" in v for v in violations)
    has_dup_violation = any("Duplicate heading class" in v for v in violations)
    has_metric_violation = any("Placeholder metric" in v for v in violations)
    has_undefined_vars = any("Undefined CSS custom property referenced" in v or "Undefined CSS variable" in v for v in violations)
    has_spacing_violation = any("[REPEATED ITEM SPACING LINT]" in v for v in violations)
    has_truncated_css = any(("Unbalanced braces" in v or "Unbalanced parentheses" in v) for v in violations if (v.endswith(".css]") or ".css]" in v or ".css:" in v))
    has_truncated_tsx = any(
        ("Unbalanced braces" in v or "Unbalanced parentheses" in v or "Truncated mid-tag" in v)
        for v in violations if (v.endswith(".tsx]") or ".tsx]" in v or ".jsx]" in v or ".tsx:" in v)
    )
    has_icon_violation = any("[FAKE ICON LINT]" in v or "[ICON PATH MISMATCH]" in v for v in violations)
    coverage_gap_violations = [v for v in violations if "Missing CSS rule for class" in v]

    dup_classes_to_fix: set[str] = set()
    if has_dup_violation:
        for v in violations:
            matches = re.findall(r"CSS class\(es\)\s+\[(.*?)\]", v)
            for m in matches:
                for token in m.split(","):
                    c = token.strip(" '\"")
                    if c:
                        dup_classes_to_fix.add(c)

    metric_replacements: Dict[str, str] = {}
    if has_metric_violation:
        for v in violations:
            m = re.search(r"Metric badge text '([^']+)' duplicates", v)
            if m:
                metric_replacements[m.group(1)] = "99.9% Verified"

    undefined_vars_to_fix: set[str] = set()
    if has_undefined_vars:
        for v in violations:
            m = re.search(r'Undefined CSS (?:custom property|variable(?:\(s\)?)) referenced:\s*([^.]+)\.', v)
            if m:
                tokens = [t.strip() for t in m.group(1).split(",") if t.strip()]
                for tok in tokens:
                    undefined_vars_to_fix.add(tok.lstrip('-'))

    for fpath, fcontent in files:
        if fpath.endswith(".css"):
            new_css = fcontent
            new_css = re.sub(r'</?style\b[^>]*>', '', new_css, flags=re.IGNORECASE)
            new_css = re.sub(r'font\s*:\s*size\s+([^,;]+),\s*([^;]+);', r'font-size: \1; color: \2;', new_css)
            new_css = re.sub(r'font\s*:\s*size\s+([^;]+);', r'font-size: \1;', new_css)
            open_b = new_css.count('{')
            close_b = new_css.count('}')
            if open_b > close_b:
                new_css = new_css.rstrip() + "\n" + ("}\n" * (open_b - close_b))
            elif close_b > open_b:
                # Strip excess closing braces (model writes "}}" — extra stray "}").
                extra = close_b - open_b
                new_css = re.sub(r'(?<=;|\})(\s*\}){1,' + str(extra) + r'}(?=\s*(?:\.|#|@|$))',
                                 lambda m, e=extra: m.group(0)[max(0, len(m.group(0))-e):],
                                 new_css)
                open_b2 = new_css.count('{')
                close_b2 = new_css.count('}')
                if close_b2 > open_b2:
                    new_css = re.sub(r'\}(?=\})', '', new_css, count=close_b2 - open_b2)
            open_p = new_css.count('(')
            close_p = new_css.count(')')
            if open_p > close_p:
                new_css = new_css.rstrip() + (")" * (open_p - close_p)) + ";"
            if has_sticky_violation:
                # Replace position: sticky with position: relative on non-headers
                new_css = re.sub(r'(\bposition\s*:\s*)sticky(\s*;?)', r'\1relative\2', new_css, flags=re.I)
            if dup_classes_to_fix:
                # Add companion styles for the card heading class if needed
                for c in dup_classes_to_fix:
                    card_cls = c.replace('__title', '__card-title') if '__title' in c else f"{c}-card"
                    if f".{card_cls}" not in new_css:
                        new_css += f"\n\n.{card_cls} {{\n  font-size: 1.25rem;\n  font-weight: 600;\n  margin: 0.5rem 0;\n}}\n"
            if undefined_vars_to_fix:
                for u_var in undefined_vars_to_fix:
                    if u_var == "scroll-transform":
                        new_css = re.sub(r'var\(\s*--scroll-transform(?:\s*,\s*[^)]+)?\)', 'none', new_css)
                    elif u_var == "scroll-transition":
                        new_css = re.sub(
                            r'var\(\s*--scroll-transition(?:\s*,\s*[^)]+)?\)',
                            'transform 0.3s var(--ease-out), opacity 0.3s var(--ease-out)',
                            new_css,
                        )
                    elif u_var in ("color-bg", "bg-color", "bg"):
                        new_css = re.sub(rf'var\(\s*--{re.escape(u_var)}(?:\s*,\s*[^)]+)?\)', 'var(--bg-color)', new_css)
                    elif u_var in ("color-primary", "primary"):
                        new_css = re.sub(rf'var\(\s*--{re.escape(u_var)}(?:\s*,\s*[^)]+)?\)', 'var(--primary-color)', new_css)
                    elif u_var in ("color-accent", "accent"):
                        new_css = re.sub(rf'var\(\s*--{re.escape(u_var)}(?:\s*,\s*[^)]+)?\)', 'var(--accent-color)', new_css)
                    elif u_var in ("color-text", "text"):
                        new_css = re.sub(rf'var\(\s*--{re.escape(u_var)}(?:\s*,\s*[^)]+)?\)', 'var(--text-color)', new_css)
                    elif u_var in ("color-surface", "surface-paper", "color-paper"):
                        new_css = re.sub(rf'var\(\s*--{re.escape(u_var)}(?:\s*,\s*[^)]+)?\)', 'var(--color-surface)', new_css)
                    else:
                        # If var(--u_var, fallback) has a fallback, unwrap to fallback
                        new_css = re.sub(rf'var\(\s*--{re.escape(u_var)}\s*,\s*([^)]+)\)', r'\1', new_css)
                        # Otherwise replace bare var(--u_var) with safe default or inherit
                        new_css = re.sub(rf'var\(\s*--{re.escape(u_var)}\)', 'inherit', new_css)
            if has_spacing_violation:
                new_css = auto_fix_repeated_item_spacing(new_css, violations)
            if coverage_gap_violations:
                missing_classes = [re.search(r"class '\.([^']+)'", v).group(1) for v in coverage_gap_violations if re.search(r"class '\.([^']+)'", v)]
                # BUG FIX: previously extracted missing_classes but never injected them.
                # Now actually call the CSS gap injector so the stubs land in the file.
                if missing_classes:
                    new_css = auto_fix_css_coverage_gaps([(fpath, new_css)], missing_classes, section_name=section_name)[0][1]
            if has_icon_violation:
                if ".feather" not in new_css:
                    new_css += (
                        "\n\n.feather {\n"
                        "  width: 24px;\n"
                        "  height: 24px;\n"
                        "  stroke: currentColor;\n"
                        "  stroke-width: 2;\n"
                        "  stroke-linecap: round;\n"
                        "  stroke-linejoin: round;\n"
                        "  fill: none;\n"
                        "  display: inline-block;\n"
                        "  vertical-align: middle;\n"
                        "}\n"
                    )
                new_css = re.sub(r'(\b\w*__icon\s+svg\s*\{[^}]*?)\bfill\s*:\s*[^;\}]+;', r'\1fill: none; stroke: currentColor;', new_css)
            if any("[CSS SELECTOR SYNTAX]" in v for v in violations):
                new_css = re.sub(
                    r'(?<=[\s,>+~])([a-zA-Z0-9_-]+__[a-zA-Z0-9_-]+)(?=[\s,{>+~:.[])',
                    r'.\1',
                    new_css
                )
            if any("GLOBAL WRAPPER MISUSE" in v for v in violations):
                new_css = re.sub(r'(?:^|[,\s>+~])\.site-root\s*(?:>\s*|\+\s*|~\s*|\s+)?', ' ', new_css)
            # Strip redundant @import rules from component-level CSS
            new_css = re.sub(r'@import\s+url\([^)]+\)\s*;?\s*', '', new_css)
            fixed_files.append((fpath, new_css))

        elif fpath.endswith(".tsx") or fpath.endswith(".jsx"):
            new_tsx = balance_jsx_tags(fcontent)
            if dup_classes_to_fix:
                for c in dup_classes_to_fix:
                    card_cls = c.replace('__title', '__card-title') if '__title' in c else f"{c}-card"
                    def _replace_h3(match, target_cls=c, repl_cls=card_cls):
                        h3_tag = match.group(0)
                        return h3_tag.replace(target_cls, repl_cls)
                    new_tsx = re.sub(r'<h3[^>]*\bclassName=["\'][^"\']*' + re.escape(c) + r'[^"\']*["\'][^>]*>', _replace_h3, new_tsx)
            if metric_replacements:
                for old_val, new_val in metric_replacements.items():
                    # Target only the badge/metric tag contents, preserving heading titles intact
                    new_tsx = re.sub(
                        r'(<(?:span|div|p)\b[^>]*\bclassName=["\'][^"\']*(?:metric|stat|badge)[^"\']*["\'][^>]*>)(.*?)(</(?:span|div|p)>)',
                        lambda m, oval=old_val, nval=new_val: f"{m.group(1)}{nval}{m.group(3)}" if oval.lower() in m.group(2).lower() else m.group(0),
                        new_tsx,
                        flags=re.IGNORECASE | re.DOTALL
                    )
            if has_truncated_tsx:
                new_tsx = re.sub(r'<[a-zA-Z][^>]*$', '', new_tsx.rstrip()).rstrip()
                open_p = new_tsx.count('(')
                close_p = new_tsx.count(')')
                if open_p > close_p:
                    new_tsx += (")" * (open_p - close_p)) + ";"
                open_b = new_tsx.count('{')
                close_b = new_tsx.count('}')
                if open_b > close_b:
                    new_tsx += "\n" + ("}\n" * (open_b - close_b))
            if has_icon_violation:
                new_tsx = auto_fix_icon_paths(new_tsx, violations)
            if any("FONT AWESOME ICON" in v for v in violations):
                def _repl_fa(m: re.Match) -> str:
                    fa_cls = m.group(1)
                    m_name = re.search(r'fa-([a-z0-9-]+)', fa_cls)
                    if m_name:
                        icon_name = m_name.group(1).lower()
                        canonical = FAKE_ICON_NAMES.get(f"fa-{icon_name}", FAKE_ICON_NAMES.get(icon_name, icon_name))
                        svg = get_verified_inline_svg(canonical)
                        if svg:
                            return svg
                    return m.group(0)
                new_tsx = re.sub(r'<i\b[^>]*\bclass(?:Name)?=["\']([^"\']*\bfa[brs]?\s+fa-[^"\']*)["\'][^>]*>\s*</i>', _repl_fa, new_tsx)

            if any("STOCK PHOTO LOGO LINT" in v for v in violations):
                def _repl_logo(m: re.Match) -> str:
                    tag = m.group(0)
                    cls_m = re.search(r'class(?:Name)?=["\']([^"\']+)["\']', tag)
                    cls = cls_m.group(1) if cls_m else "logo"
                    alt_match = re.search(r'alt=["\']([^"\']+)["\']', tag)
                    label = alt_match.group(1) if alt_match else "Site"
                    return f'<span className="{cls}">{html.escape(label)}</span>'
                new_tsx = re.sub(
                    r'<img\b[^>]*>',
                    lambda m: _repl_logo(m) if (
                        re.search(r'class(?:Name)?=["\'][^"\']*(?:logo|brand)[^"\']*["\']', m.group(0), re.I) and
                        re.search(r'src=["\'][^"\']*(?:unsplash|pexels)[^"\']*["\']', m.group(0), re.I)
                    ) else m.group(0),
                    new_tsx
                )

            if any("GLOBAL WRAPPER MISUSE" in v for v in violations):
                # Safely remove 'site-root' from classNames in TSX
                new_tsx = re.sub(
                    r'(className=["\'][^"\']*?)\bsite-root\b\s*',
                    r'\1',
                    new_tsx
                )
                # Clean up empty trailing space in className if site-root was at the end
                new_tsx = re.sub(r' +(["\'])', r'\1', new_tsx)

            if any("DEAD DRAWER/MODAL STATE" in v for v in violations):
                m_drawer_v = [v for v in violations if "DEAD DRAWER/MODAL STATE" in v]
                for dv in m_drawer_v:
                    m_var = re.search(r"'(\w+)'\s+is declared with useState", dv)
                    if m_var:
                        d_var = m_var.group(1)
                        if f"{d_var} ?" not in new_tsx and f"{{{d_var} &&" not in new_tsx:
                            new_tsx = re.sub(
                                r'className=["\']([^"\']*\b(?:header__nav|nav)\b[^"\']*)["\']',
                                lambda m, dv=d_var: f'className={{`{m.group(1)} ${{ {dv} ? "{m.group(1).split()[0]}--open" : "" }}`}}',
                                new_tsx,
                                count=1
                            )

            if any("[CONTENT LEAK LINT]" in v for v in violations):
                # 1. Replace bare section headings
                new_tsx = re.sub(r'(<h[1-6]\b[^>]*>)\s*Hero\s*(</h[1-6]>)', r'\1Overview\2', new_tsx, flags=re.I)
                new_tsx = re.sub(r'(<h[1-6]\b[^>]*>)\s*Features\s*(</h[1-6]>)', r'\1Core Capabilities\2', new_tsx, flags=re.I)
                new_tsx = re.sub(r'(<h[1-6]\b[^>]*>)\s*Contact\s*(</h[1-6]>)', r'\1Contact\2', new_tsx, flags=re.I)
                new_tsx = re.sub(r'(<h[1-6]\b[^>]*>)\s*Header\s*(</h[1-6]>)', r'\1Navigation\2', new_tsx, flags=re.I)
                new_tsx = re.sub(r'(<h[1-6]\b[^>]*>)\s*Footer\s*(</h[1-6]>)', r'\1More information\2', new_tsx, flags=re.I)

                # 2. Remove raw schema field labels
                new_tsx = re.sub(r'<span\b[^>]*className=["\'][^"\']*sa-field__label[^"\']*["\'][^>]*>.*?</span>\s*', '', new_tsx, flags=re.I)
                for lbl in ["Feature Icon", "Capability Metric", "Description Tagline", "Feature Title", "An Inquiry Form", "Inquiry Message Form", "Physical Address", "Direct Email", "Office Phone"]:
                    new_tsx = re.sub(rf'<(?:span|p|div|label)\b[^>]*>\s*{re.escape(lbl)}\s*</(?:span|p|div|label)>\s*', '', new_tsx, flags=re.I)

                # 3. Replace generic template sentences
                new_tsx = re.sub(r'Specialized\s+[\w\s-]+\s+implementation\s+for\s+([^.<"]+)\.?', r'Enterprise-grade capability delivering robust execution for \1.', new_tsx, flags=re.I)
                new_tsx = re.sub(r'Specialized\s+offering\s+and\s+verified\s+capability\s+for\s+([^.<"]+)\.?', r'Information about \1.', new_tsx, flags=re.I)

                # 4. Replace bare Series 0X placeholders with neutral labels.
                series_map = {"Series 01": "Performance", "Series 02": "Reliability", "Series 03": "Throughput", "Series 04": "Data integrity"}
                for s_old, s_new in series_map.items():
                    new_tsx = re.sub(rf'\b{s_old}\b', s_new, new_tsx)

                # 5. Clean leaked instruction text
                new_tsx = re.sub(r'a high-impact full-width banner with business tagline as an h1, an engaging subtitle, and primary/secondary action buttons\.?', r'Explore this site and its available sections.', new_tsx, flags=re.I)
                new_tsx = re.sub(r'contact information including address, phone, email, hours, and an inquiry form\.?', r'Use the available contact options for more information.', new_tsx, flags=re.I)
                new_tsx = re.sub(r'Display exactly \d+ items \([^)]+\)\.?', r'Explore the available capabilities below.', new_tsx, flags=re.I)

            fixed_files.append((fpath, new_tsx))
        else:
            fixed_files.append((fpath, fcontent))

    if return_dict:
        return dict(fixed_files)
    return fixed_files
