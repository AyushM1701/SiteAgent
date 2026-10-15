"""Twelve art directions for kit-built sites.

Each theme is a complete, contrast-checked visual system: colours, a two-family
type pairing that Google Fonts actually ships, radii, density and hero styles.
The model never chooses colours or fonts; the prompt's subject chooses a theme.
"""
from __future__ import annotations

import colorsys
import dataclasses
import hashlib
import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class Theme:
    id: str
    name: str
    mode: str  # "light" | "dark"
    colors: dict = field(hash=False)
    display_font: str = ""
    body_font: str = ""
    font_query: str = ""
    display_weight: int = 500
    display_tracking: str = "-0.02em"
    display_line: float = 1.04
    body_size: str = "1.0625rem"
    radius: str = "8px"
    button_radius: str = "8px"
    density: str = "clamp(72px, 10vw, 136px)"
    hero_styles: tuple = ("split",)
    keywords: tuple = ()
    heading_case: str = "none"
    rule: bool = False
    lively: bool = False


def _theme(**kwargs) -> Theme:
    return Theme(**kwargs)


THEMES: dict[str, Theme] = {t.id: t for t in (
    _theme(
        id="atelier", name="Atelier", mode="light",
        colors={"bg": "#EEEAE3", "surface": "#F6F3EE", "surface2": "#E4DED4", "ink": "#28231E", "muted": "#5B5349",
                "line": "#D3CBBE", "accent": "#4D5B39", "accent_ink": "#FFFFFF", "accent_soft": "#DDE0D1"},
        display_font="Fraunces", body_font="Karla",
        font_query="family=Fraunces:wght@400;500;600&family=Karla:wght@400;500;700",
        display_weight=400, display_tracking="-0.025em", display_line=1.02,
        radius="4px", button_radius="2px", hero_styles=("split", "fullbleed"),
        keywords=("ceramic", "ceramics", "pottery", "potter", "clay", "kiln", "handmade", "hand-made", "craft", "crafts",
                  "maker", "makers", "stationery", "paper goods", "notebook", "woodwork", "leather", "textile", "weaving",
                  "candle", "artisan", "atelier", "studio pottery", "glaze"),
        rule=True,
    ),
    _theme(
        id="clinic", name="Clinic", mode="light",
        colors={"bg": "#FBFCFC", "surface": "#F1F5F6", "surface2": "#E5EDEF", "ink": "#122030", "muted": "#475665",
                "line": "#D4DDE1", "accent": "#0D6B70", "accent_ink": "#FFFFFF", "accent_soft": "#DCEEEE"},
        display_font="Schibsted Grotesk", body_font="Source Sans 3",
        font_query="family=Schibsted+Grotesk:wght@500;600;700&family=Source+Sans+3:wght@400;500;600",
        display_weight=600, display_tracking="-0.02em", display_line=1.06,
        radius="14px", button_radius="10px", hero_styles=("split",),
        keywords=("health", "healthcare", "clinic", "medical", "doctor", "doctors", "dental", "dentist", "physio",
                  "physiotherapy", "therapy", "therapist", "law", "lawyer", "legal", "attorney", "finance", "financial",
                  "accounting", "accountant", "tax", "consulting", "consultant", "insurance", "advisory", "pharmacy",
                  "veterinary", "vet"),
    ),
    _theme(
        id="nocturne", name="Nocturne", mode="dark",
        colors={"bg": "#14110E", "surface": "#1D1915", "surface2": "#27221C", "ink": "#EFE7DA", "muted": "#B3A896",
                "line": "#3A332A", "accent": "#C9A46A", "accent_ink": "#14110E", "accent_soft": "#2E2619"},
        display_font="Cormorant Garamond", body_font="Jost",
        font_query="family=Cormorant+Garamond:wght@400;500;600&family=Jost:wght@300;400;500",
        display_weight=500, display_tracking="-0.01em", display_line=1.02, body_size="1.0625rem",
        radius="0px", button_radius="0px", hero_styles=("fullbleed",),
        keywords=("fine dining", "tasting menu", "wine", "winery", "vineyard", "cocktail", "cocktails", "bar",
                  "speakeasy", "hotel", "boutique hotel", "jewellery", "jewelry", "luxury", "perfume", "fragrance",
                  "champagne", "whisky", "sommelier"),
        rule=True,
    ),
    _theme(
        id="signal", name="Signal", mode="dark",
        colors={"bg": "#0C1016", "surface": "#131A23", "surface2": "#1B2430", "ink": "#E7ECF2", "muted": "#9AA7B6",
                "line": "#26313F", "accent": "#7C95FF", "accent_ink": "#0C1016", "accent_soft": "#1A2240",
                "accent2": "#41D3C0"},
        display_font="Space Grotesk", body_font="IBM Plex Sans",
        font_query="family=Space+Grotesk:wght@500;600;700&family=IBM+Plex+Sans:wght@400;500;600",
        display_weight=600, display_tracking="-0.035em", display_line=1.0,
        radius="14px", button_radius="10px", hero_styles=("product",),
        keywords=("saas", "software", "platform", "analytics", "data", "ai", "machine learning", "developer",
                  "developers", "api", "devtools", "logistics", "b2b", "cloud", "dashboard", "startup", "app",
                  "automation", "security", "cybersecurity", "fintech", "infrastructure", "telemetry"),
        lively=True,
    ),
    _theme(
        id="verdant", name="Verdant", mode="light",
        colors={"bg": "#F2F4ED", "surface": "#F8F9F4", "surface2": "#E5E9DD", "ink": "#1D2A21", "muted": "#4C5A4F",
                "line": "#D3D9CA", "accent": "#2E5B45", "accent_ink": "#FFFFFF", "accent_soft": "#D9E5DC"},
        display_font="DM Serif Display", body_font="Nunito Sans",
        font_query="family=DM+Serif+Display&family=Nunito+Sans:wght@400;600;700",
        display_weight=400, display_tracking="-0.015em", display_line=1.05,
        radius="22px", button_radius="999px", hero_styles=("split", "fullbleed"),
        keywords=("yoga", "pilates", "meditation", "wellness", "wellbeing", "retreat", "spa", "massage", "plants",
                  "plant", "nursery", "florist", "flowers", "garden", "gardening", "nonprofit", "charity",
                  "sustainability", "organic", "herbal", "naturopath", "mindfulness"),
    ),
    _theme(
        id="gallery", name="Gallery", mode="light",
        colors={"bg": "#FAFAF7", "surface": "#F1F1EC", "surface2": "#E7E7E0", "ink": "#121315", "muted": "#55575C",
                "line": "#DADAD3", "accent": "#2343D1", "accent_ink": "#FFFFFF", "accent_soft": "#E3E7FA"},
        display_font="Instrument Serif", body_font="Inter Tight",
        font_query="family=Instrument+Serif&family=Inter+Tight:wght@400;500;600",
        display_weight=400, display_tracking="-0.02em", display_line=0.98,
        radius="0px", button_radius="0px", hero_styles=("typographic", "split"),
        keywords=("portfolio", "designer", "brand designer", "graphic designer", "design studio", "architecture",
                  "architect", "photographer", "photography", "illustrator", "illustration", "art director",
                  "creative director", "gallery", "artist", "type designer", "ux designer", "product designer"),
        rule=True,
    ),
    _theme(
        id="carnival", name="Carnival", mode="light",
        colors={"bg": "#FFF6E8", "surface": "#FFFBF3", "surface2": "#FBE9CF", "ink": "#22183A", "muted": "#574C6B",
                "line": "#EED9BA", "accent": "#C9303A", "accent_ink": "#FFFFFF", "accent_soft": "#FBDCD8",
                "accent2": "#2563D9"},
        display_font="Bricolage Grotesque", body_font="Figtree",
        font_query="family=Bricolage+Grotesque:wght@500;600;700;800&family=Figtree:wght@400;500;600",
        display_weight=700, display_tracking="-0.03em", display_line=1.0,
        radius="24px", button_radius="999px", hero_styles=("split",),
        keywords=("kids", "children", "child", "camp", "summer camp", "festival", "fair", "carnival", "sweets",
                  "candy", "ice cream", "toy", "toys", "pets", "pet", "party", "parties", "playful", "colourful",
                  "colorful", "fun", "games", "playground", "birthday"),
        lively=True,
    ),
    _theme(
        id="press", name="Press", mode="light",
        colors={"bg": "#F7F5F0", "surface": "#EFECE5", "surface2": "#E5E1D8", "ink": "#1A1917", "muted": "#57534B",
                "line": "#D9D4C9", "accent": "#7A2131", "accent_ink": "#FFFFFF", "accent_soft": "#EEDFE0"},
        display_font="Newsreader", body_font="Libre Franklin",
        font_query="family=Newsreader:wght@400;500;600&family=Libre+Franklin:wght@400;500;600",
        display_weight=500, display_tracking="-0.02em", display_line=1.03,
        radius="2px", button_radius="2px", hero_styles=("typographic", "split"),
        keywords=("magazine", "publication", "journal", "newsletter", "books", "bookshop", "bookstore", "publisher",
                  "publishing", "author", "writer", "podcast", "education", "school", "academy", "course", "courses",
                  "university", "library", "tutoring", "research", "blog", "essays"),
        rule=True,
    ),
    _theme(
        id="forge", name="Forge", mode="light",
        colors={"bg": "#F1F0EC", "surface": "#E8E7E2", "surface2": "#DDDCD6", "ink": "#131313", "muted": "#4D4D4A",
                "line": "#CFCEC8", "accent": "#E8551A", "accent_ink": "#131313", "accent_soft": "#F7DCCF"},
        display_font="Anton", body_font="Archivo",
        font_query="family=Anton&family=Archivo:wght@400;500;600;700",
        display_weight=400, display_tracking="0.005em", display_line=0.98,
        radius="0px", button_radius="0px", hero_styles=("fullbleed", "split"),
        keywords=("gym", "strength", "fitness", "crossfit", "boxing", "martial arts", "sport", "sports", "athletics",
                  "training", "coach", "coaching", "automotive", "garage", "mechanic", "cars", "motorcycle",
                  "trades", "construction", "builder", "plumber", "electrician", "barber", "barbershop", "tattoo"),
        heading_case="uppercase", lively=True,
    ),
    _theme(
        id="coastal", name="Coastal", mode="light",
        colors={"bg": "#F5F8F8", "surface": "#ECF2F3", "surface2": "#DFE9EB", "ink": "#0F2A33", "muted": "#46606A",
                "line": "#D0DDE0", "accent": "#1C6684", "accent_ink": "#FFFFFF", "accent_soft": "#D8E8EF"},
        display_font="Marcellus", body_font="Mulish",
        font_query="family=Marcellus&family=Mulish:wght@400;500;600;700",
        display_weight=400, display_tracking="-0.005em", display_line=1.06,
        radius="8px", button_radius="6px", hero_styles=("fullbleed", "split"),
        keywords=("travel", "tour", "tours", "resort", "beach", "island", "villa", "villas", "real estate", "realty",
                  "property", "properties", "homes", "apartment", "rental", "rentals", "surf", "sailing", "yacht",
                  "cruise", "holiday", "vacation", "guesthouse", "lodge"),
    ),
    _theme(
        id="spice", name="Spice", mode="dark",
        colors={"bg": "#1B1922", "surface": "#24212C", "surface2": "#2E2A37", "ink": "#F4ECDF", "muted": "#BCB1A2",
                "line": "#3B3646", "accent": "#E3A33A", "accent_ink": "#1B1922", "accent_soft": "#3A2F22"},
        display_font="Libre Bodoni", body_font="Outfit",
        font_query="family=Libre+Bodoni:wght@400;500;600&family=Outfit:wght@300;400;500;600",
        display_weight=500, display_tracking="-0.02em", display_line=1.02,
        radius="6px", button_radius="999px", hero_styles=("fullbleed", "split"),
        keywords=("restaurant", "indian", "thai", "ramen", "sushi", "bistro", "kitchen", "dining", "curry",
                  "tandoor", "tapas", "taqueria", "mexican", "korean", "vietnamese", "chinese", "biryani",
                  "street food", "eatery", "food truck", "chef", "cuisine"),
        lively=True,
    ),
    _theme(
        id="roast", name="Roast", mode="light",
        colors={"bg": "#F4F1EE", "surface": "#FAF8F6", "surface2": "#E9E3DD", "ink": "#2A1E18", "muted": "#5D4F47",
                "line": "#DDD4CC", "accent": "#2F4A3F", "accent_ink": "#FFFFFF", "accent_soft": "#DCE4DF"},
        display_font="Young Serif", body_font="Manrope",
        font_query="family=Young+Serif&family=Manrope:wght@400;500;600;700",
        display_weight=400, display_tracking="-0.02em", display_line=1.04,
        radius="12px", button_radius="999px", hero_styles=("split", "fullbleed"),
        keywords=("coffee", "cafe", "café", "espresso", "roastery", "roaster", "bakery", "bakehouse", "bread",
                  "pastry", "patisserie", "brunch", "breakfast", "tea", "tea room", "donut", "doughnut", "cake", "cakes"),
    ),
)}

_BUSINESS_TYPE_THEME = {
    "saas": "signal", "dashboard": "signal", "fintech": "clinic", "healthcare": "clinic", "restaurant": "spice",
    "coffee": "roast", "portfolio": "gallery", "agency": "gallery", "architecture": "gallery", "fitness": "forge",
    "realestate": "coastal", "education": "press", "blog": "press", "editorial": "press", "nonprofit": "verdant",
    "event": "carnival",
}
_ROTATION = ("gallery", "clinic", "press", "atelier", "coastal", "signal")
_DARK_WORDS = re.compile(r"\b(?:dark|black|night|moody|noir)\b")
_LIGHT_WORDS = re.compile(r"\b(?:light|white|airy|minimal|minimalist|bright|pale)\b")
_HUE_WORDS = r"(?:\s+(?:and\s+)?[a-z]+){0,1}\s+(?:green|blue|red|brown|grey|gray|purple|teal|navy|olive|orange|pink|gold|yellow|wood|oak|walnut|accents?)"


# ── Colour utilities ────────────────────────────────────────────────────────

def _rgb(hex_color: str) -> tuple[float, float, float]:
    value = hex_color.lstrip("#")
    if len(value) == 3:
        value = "".join(ch * 2 for ch in value)
    return tuple(int(value[i:i + 2], 16) / 255 for i in (0, 2, 4))  # type: ignore[return-value]


def _hex(rgb: tuple[float, float, float]) -> str:
    return "#" + "".join(f"{max(0, min(255, round(c * 255))):02X}" for c in rgb)


def luminance(hex_color: str) -> float:
    def channel(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = _rgb(hex_color)
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def contrast(a: str, b: str) -> float:
    la, lb = luminance(a), luminance(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def mix(a: str, b: str, amount: float) -> str:
    """amount=0 gives a, amount=1 gives b."""
    ra, rb = _rgb(a), _rgb(b)
    return _hex(tuple(x + (y - x) * amount for x, y in zip(ra, rb)))  # type: ignore[arg-type]


def _ensure_contrast(color: str, bg: str, target: float, toward: str) -> str:
    if contrast(color, bg) >= target:
        return color
    for step in range(1, 21):
        candidate = mix(color, toward, step / 20)
        if contrast(candidate, bg) >= target:
            return candidate
    return toward


def _lightness(hex_color: str) -> float:
    return colorsys.rgb_to_hls(*_rgb(hex_color))[1]


# ── Selection ───────────────────────────────────────────────────────────────

def _positive(text: str, pattern: str) -> list[re.Match]:
    try:
        from agent.site_brief import _is_negated
    except ImportError:  # pragma: no cover - script context
        from site_brief import _is_negated  # type: ignore
    return [m for m in re.finditer(pattern, text) if not _is_negated(text, m.start(), m.end())]


def requested_mode(prompt: str) -> Optional[str]:
    """Explicit light/dark wording; hue phrases ("dark forest green") don't count."""
    lower = prompt.lower()
    dark = [m for m in _positive(lower, _DARK_WORDS.pattern) if not re.match(_HUE_WORDS, lower[m.end():])]
    light = [m for m in _positive(lower, _LIGHT_WORDS.pattern) if not re.match(_HUE_WORDS, lower[m.end():])
             and not re.match(r"\s+(?:touch|weight|lunch|bites|meals?)\b", lower[m.end():])]
    if dark and not light:
        return "dark"
    if light and not dark:
        return "light"
    return None


def _score(theme: Theme, lower: str, business_type: str) -> float:
    score = 0.0
    for keyword in theme.keywords:
        hits = _positive(lower, r"\b" + re.escape(keyword) + r"\b")
        if hits:
            score += 3 * (2 if " " in keyword else 1)
    if _BUSINESS_TYPE_THEME.get(business_type) == theme.id:
        score += 2.5
    return score


def select_theme(prompt: str, business_type: str = "", preferred: Optional[str] = None) -> Theme:
    if preferred and preferred in THEMES:
        return THEMES[preferred]
    lower = prompt.lower()
    mode = requested_mode(prompt)
    candidates = [t for t in THEMES.values() if mode is None or t.mode == mode]
    digest = int(hashlib.sha256(prompt.encode("utf-8")).hexdigest(), 16)
    scored = sorted(((_score(t, lower, business_type), t.id) for t in candidates), reverse=True)
    best = scored[0][0] if scored else 0
    if best > 0:
        tied = sorted(theme_id for score, theme_id in scored if score == best)
        return THEMES[tied[digest % len(tied)]]
    rotation = [tid for tid in _ROTATION if mode is None or THEMES[tid].mode == mode] or [t.id for t in candidates]
    return THEMES[rotation[digest % len(rotation)]]


def apply_requested_palette(theme: Theme, brief: Optional[dict]) -> Theme:
    """Honour colours the user named, keeping every contrast invariant."""
    brief = brief or {}
    if not brief.get("requested_palette"):
        return theme
    colors = dict(theme.colors)
    bg = brief.get("background_color")
    if bg and re.fullmatch(r"#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?", bg):
        is_light = _lightness(bg) >= 0.5
        if is_light == (theme.mode == "light"):
            colors["bg"] = bg.upper() if len(bg) == 7 else _hex(_rgb(bg))
            toward = "#000000" if is_light else "#FFFFFF"
            colors["surface"] = mix(colors["bg"], "#FFFFFF" if is_light else "#FFFFFF", 0.35 if is_light else 0.05)
            colors["surface2"] = mix(colors["bg"], toward, 0.06)
            colors["line"] = mix(colors["bg"], toward, 0.14)
    accent = brief.get("accent_color")
    if accent and re.fullmatch(r"#[0-9a-fA-F]{6}", accent) and accent.lower() != (bg or "").lower():
        if contrast(accent, colors["bg"]) >= 3:
            colors["accent"] = accent.upper()
            colors["accent_ink"] = max(("#FFFFFF", colors["ink"], colors["bg"], "#111111"),
                                       key=lambda ink: contrast(ink, colors["accent"]))
            colors["accent_soft"] = mix(colors["bg"], colors["accent"], 0.14)
    dark_target = "#000000" if theme.mode == "light" else "#FFFFFF"
    colors["ink"] = _ensure_contrast(colors["ink"], colors["bg"], 7.0, dark_target)
    colors["muted"] = _ensure_contrast(colors["muted"], colors["bg"], 4.6, colors["ink"])
    return dataclasses.replace(theme, colors=colors)
