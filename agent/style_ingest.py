"""
style_ingest.py - Design System Ingestion & Style Conformance Engine for ReactAgent SLM

Decouples visual aesthetic and design tokens from business domain heuristics.
Parses Refero-style design systems (e.g. styles.refero.design), custom :root CSS blocks,
and Tailwind @theme definitions into structured StyleSpec objects with zero LLM cost.
Enforces strict token compliance during multi-turn agent generation.
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any


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
    raw_css: str = ""                                            # Complete verbatim :root block
    dos: List[str] = field(default_factory=list)                 # Positive design guidelines
    donts: List[str] = field(default_factory=list)               # Hard aesthetic constraints
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
        elif prop_name.startswith(("--text-", "--leading-")):
            spec.type_scale[prop_name] = prop_val
        elif prop_name.startswith("--spacing-"):
            spec.spacing_scale[prop_name] = prop_val
        elif prop_name.startswith("--radius-"):
            spec.radius[prop_name] = prop_val
        elif prop_name.startswith("--surface-"):
            spec.surfaces[prop_name] = prop_val
        elif prop_name in ("--page-max-width", "--section-gap", "--card-padding", "--element-gap"):
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


def _build_preset_spec(name: str, css_text: str, dos: List[str], donts: List[str]) -> StyleSpec:
    spec = parse_css_tokens(css_text, name=name, source="preset")
    spec.dos = dos
    spec.donts = donts
    return spec


PRESET_STYLES: Dict[str, StyleSpec] = {
    "refero_editorial": _build_preset_spec(
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
    ),
    "neo_brutalist": _build_preset_spec(
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
    ),
    "glassmorphic_aurora": _build_preset_spec(
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
    ),
    "luxury_minimalist": _build_preset_spec(
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
    ),
    "cyberpunk_neon": _build_preset_spec(
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
    ),
}


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

    return css_content


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
    non_root_lines = []
    in_root = False
    for line in clean_css.splitlines():
        if ":root" in line:
            in_root = True
        if in_root:
            if "}" in line:
                in_root = False
            continue
        non_root_lines.append(line)

    body_css = "\n".join(non_root_lines)

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
    heading_font_sizes = re.findall(r'(?:h1|h2|\.[\w-]*title|\.[\w-]*heading)[^{]*\{[^}]*font-size\s*:\s*(\d+(?:\.\d+)?)(px|rem)', body_css, re.IGNORECASE)
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

def spec_to_css_root(style_spec: StyleSpec) -> str:
    """
    Builds a complete, modern :root { ... } stylesheet block from StyleSpec.
    Includes backward-compatible aliases (--primary-color, --accent-color, --font-heading, --font-body)
    so existing component patterns seamlessly interoperate with the new design system.
    """
    primary = style_spec.get_primary_color()
    accent = style_spec.get_accent_color()
    font_h = style_spec.get_heading_font()
    font_b = style_spec.get_body_font()

    lines = [
        f"/* ==========================================================================",
        f"   DESIGN SYSTEM: {style_spec.name} (Source: {style_spec.source})",
        f"   ========================================================================== */",
        ":root {"
    ]

    # Primary bridge aliases for universal backward compatibility
    lines.append("  /* Universal Compatibility Aliases */")
    lines.append(f"  --primary-color: {primary};")
    lines.append(f"  --accent-color: {accent};")
    lines.append(f"  --font-heading: '{font_h}', system-ui, -apple-system, sans-serif;")
    lines.append(f"  --font-body: '{font_b}', system-ui, -apple-system, sans-serif;")
    lines.append(f"  --bg-color: {primary};")
    lines.append(f"  --text-color: #fafafa;")
    lines.append("")

    # If raw_css is already a valid :root block, extract properties
    prop_pattern = re.compile(r'(--[\w-]+)\s*:\s*([^;]+);')
    raw_props = prop_pattern.findall(style_spec.raw_css)

    if raw_props:
        lines.append("  /* Ingested Design System Tokens */")
        for k, v in raw_props:
            # Avoid duplicate definitions of universal aliases
            if k not in ("--primary-color", "--accent-color", "--bg-color", "--text-color"):
                lines.append(f"  {k}: {v};")
    else:
        # Assemble from categorized dicts
        if style_spec.colors:
            lines.append("  /* Colors & Gradients */")
            for k, v in style_spec.colors.items():
                lines.append(f"  {k}: {v};")
            lines.append("")
        if style_spec.fonts:
            lines.append("  /* Typography Families */")
            for k, v in style_spec.fonts.items():
                lines.append(f"  {k}: {v};")
            lines.append("")
        if style_spec.type_scale:
            lines.append("  /* Type Scale */")
            for k, v in style_spec.type_scale.items():
                lines.append(f"  {k}: {v};")
            lines.append("")
        if style_spec.radius:
            lines.append("  /* Border Radii */")
            for k, v in style_spec.radius.items():
                lines.append(f"  {k}: {v};")
            lines.append("")
        if style_spec.surfaces:
            lines.append("  /* Surfaces */")
            for k, v in style_spec.surfaces.items():
                lines.append(f"  {k}: {v};")
            lines.append("")
        if style_spec.spacing_scale:
            lines.append("  /* Spacing Scale */")
            for k, v in style_spec.spacing_scale.items():
                lines.append(f"  {k}: {v};")
            lines.append("")
        if style_spec.layout:
            lines.append("  /* Layout */")
            for k, v in style_spec.layout.items():
                lines.append(f"  {k}: {v};")

    lines.append("}")
    lines.append("")
    lines.append("*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }")
    lines.append("html { scroll-behavior: smooth; font-family: var(--font-body); }")
    lines.append("body { margin: 0; font-family: var(--font-body); background-color: var(--bg-color); color: var(--text-color); -webkit-font-smoothing: antialiased; }")
    lines.append(".site-root { display: flex; flex-direction: column; min-height: 100vh; overflow-x: hidden; }")
    return "\n".join(lines)


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
