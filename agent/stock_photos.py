"""Small, curated photographic asset resolver for briefs that request imagery.

The resolver never substitutes diagrams, icons, or unrelated image-search results
for photographs. Sites may use these URLs directly and retain the credit metadata.
"""

import re
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse


@dataclass
class AssetSpec:
    """First-class media decision used by layout planning and rendering."""
    id: str
    purpose: str
    source: str
    src: str
    attribution: Optional[str]
    width: int
    height: int
    aspect_ratio: float
    focal_point: Optional[Tuple[float, float]]
    alt: str
    eager: bool = False

    def to_dict(self) -> Dict[str, Any]:
        value = asdict(self)
        value["aspectRatio"] = value.pop("aspect_ratio")
        value["focalPoint"] = value.pop("focal_point")
        return value


def build_asset_manifest(brief: Dict[str, Any]) -> Dict[str, Any]:
    """Resolve media intentionally, reserving geometry for every image."""
    resolved = resolve_site_images(brief)
    assets: List[AssetSpec] = []
    hero = (resolved.get("images") or {}).get("hero")
    if hero:
        assets.append(AssetSpec("hero", "hero", "stock", hero["url"], hero.get("credit"), 1200, 800, 1.5, None, hero["alt"], True))
    for index, image in enumerate((resolved.get("images") or {}).get("items", [])):
        assets.append(AssetSpec(f"editorial-{index+1}", "editorial", "stock", image["url"], image.get("credit"), 1200, 800, 1.5, None, image["alt"]))
    return {"assets": [asset.to_dict() for asset in assets], "media_decision": "photography" if assets else resolved.get("media_decision", "none"),
            "media_expectation": resolved.get("media_expectation", "")}


_PHOTO_ROWS = [
    ("1558494949-ef010cbdcc31", "Server racks in a modern datacenter", "cloud server datacenter saas"),
    ("1551288049-bebda4e38f71", "Analytics dashboard on a computer screen", "analytics dashboard telemetry saas"),
    ("1518770660439-4636190af475", "Electronic circuitry close up", "technology circuit hardware server"),
    ("1497366216548-37526070297c", "Sunlit modern office workspace", "office business saas team"),
    ("1497366811353-6870744d04b2", "Contemporary office workspace", "office business team"),
    ("1497366858526-0766cadbe8fa", "Bright collaborative office", "office team business"),
    ("1531297484001-80022131f5a1", "Laptop on a dark desk", "coding software laptop saas"),
    ("1516321318423-f06f85e504b3", "Collaborative technology workspace", "coding software engineer team"),
    ("1551434678-e076c223a692", "Team collaborating around a table", "team startup business"),
    ("1521737711867-e3b97375f902", "Professional team at work", "team office business"),
    ("1600585154340-be6161a56a0c", "Modern architectural exterior", "architecture building design"),
    ("1487958449943-2429e8be8625", "Contemporary building facade", "architecture building"),
    ("1511818966892-d7d671e672a2", "Minimal modern architecture", "architecture building minimal"),
    ("1501339847302-ac426a4a7cbb", "Warm cafe interior", "coffee cafe hospitality"),
    ("1559925393-8be0ec4767c8", "Coffee being prepared at a cafe", "coffee barista cafe"),
    ("1414235077428-338989a2e8c0", "Restaurant dining room", "restaurant hospitality dining"),
    ("1517248135467-4c7edcad34c4", "Restaurant interior", "restaurant dining hospitality"),
    ("1497366754035-f200968a6e72", "Modern office interior", "business finance office"),
    ("1486406146926-c627a92ad1ab", "Financial district skyline", "finance district city"),
    ("1556742049-0cfed4f6a45d", "Business payment workspace", "finance business"),
    ("1497366754035-f200968a6e72", "Office meeting space", "legal law office"),
    ("1497366811353-6870744d04b2", "Professional office interior", "legal law office"),
    ("1576091160399-112ba8d25d1d", "Healthcare worker in a clinic", "healthcare clinic medical"),
    ("1538108149393-fbbd81895907", "Modern healthcare environment", "healthcare clinic"),
    ("1506744038136-46273834b3fb", "Mountain landscape", "travel landscape nature"),
]

_STOCK_PHOTO_CURATED_CATALOG: List[Dict[str, Any]] = [
    {
        "url": f"https://images.unsplash.com/photo-{photo_id}?w=1200&q=80",
        "alt": alt,
        "title": alt,
        "credit": "Photo via Unsplash",
        "source": "Unsplash",
        "tags": tags.split(),
    }
    for photo_id, alt, tags in _PHOTO_ROWS
]


def _is_valid_photograph(candidate: Dict[str, Any]) -> bool:
    url = str(candidate.get("url", ""))
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in {"images.unsplash.com", "images.pexels.com"}:
        return False
    if re.search(r"\.(?:svg|gif|pdf)(?:$|\?)", parsed.path, re.I):
        return False
    description = " ".join(str(candidate.get(key, "")) for key in ("alt", "title", "source"))
    if re.search(r"\b(?:diagram|chart|flowchart|graph|scan|whitepaper|document|icon|vector|illustration|schematic)\b", description, re.I):
        return False
    width, height = candidate.get("width"), candidate.get("height")
    if width is not None and height is not None:
        try:
            width, height = int(width), int(height)
            if min(width, height) < 300 or max(width, height) / min(width, height) > 5:
                return False
        except (TypeError, ValueError, ZeroDivisionError):
            return False
    return bool(candidate.get("alt"))


def _map_to_concrete_photo_query(title: str, biz_type: str = "general") -> Tuple[str, List[str]]:
    text = title.lower()
    rules = [
        ({"cloud_saas", "saas", "technology"}, r"security|governance|vault", "cybersecurity operations center server room"),
        ({"cloud_saas", "saas", "technology"}, r"trac|telemetry|predict|analytic|alert", "data analytics dashboard"),
        ({"cloud_saas", "saas", "technology"}, r"pipelin|scal|distributed|cloud", "cloud server infrastructure"),
        ({"cloud_saas", "saas", "technology"}, r"code|developer|automation", "software engineer coding workspace"),
        ({"architecture", "realestate"}, r"sustain|passive", "sustainable modern green architecture building"),
        ({"architecture", "realestate"}, r"material|stone|wood", "minimalist natural stone and wood architecture interior"),
        ({"coffee_shop", "coffee"}, r"sourc|harvest|lot", "artisan coffee farmer harvest fresh cherries"),
        ({"coffee_shop", "coffee"}, r"pour|brew|barista", "artisan cafe barista"),
        ({"legal", "law"}, r"litigation|practice|counsel", "prestigious corporate law firm library books"),
        ({"finance", "fintech"}, r"wealth|advisory|finance", "financial district modern corporate towers skyline"),
    ]
    for domains, pattern, query in rules:
        if biz_type in domains and re.search(pattern, text):
            return query, [biz_type.replace("_", " ") + " photography"]
    defaults = {
        "cloud_saas": "cloud server infrastructure",
        "saas": "software coding workspace",
        "architecture": "modern architecture building",
        "coffee_shop": "artisan cafe barista",
        "legal": "corporate law firm library books",
        "finance": "financial district modern corporate towers skyline",
        "coffee": "artisan coffee cafe",
        "restaurant": "restaurant dining room",
        "healthcare": "healthcare clinic",
    }
    # Unknown subjects retain their own words. Inventing a workplace query turns
    # an uncovered product or topic into an unrelated but technically valid photo.
    query = defaults.get(biz_type, title.strip())
    return query, []


def _resolve_curated_stock_photo(query: str, biz_type: str = "general", used_urls: Optional[Set[str]] = None) -> Optional[Dict[str, Any]]:
    used_urls = used_urls or set()
    words = set(re.findall(r"[a-z]+", query.lower()))
    domain_words = set(re.findall(r"[a-z]+", biz_type.lower()))
    ranked = sorted(
        _STOCK_PHOTO_CURATED_CATALOG,
        key=lambda photo: len((words | domain_words) & set(photo["tags"])),
        reverse=True,
    )
    relevant_words = (words | domain_words) - {"general", "ecommerce", "photography", "editorial", "professional", "minimal", "design"}
    return next((dict(photo) for photo in ranked
                 if relevant_words.intersection(photo["tags"])
                 and photo["url"] not in used_urls and _is_valid_photograph(photo)), None)


def fetch_single_image(query: str, biz_type: str = "general", used_urls: Optional[Set[str]] = None) -> Optional[Dict[str, Any]]:
    concrete_query, _ = _map_to_concrete_photo_query(query, biz_type)
    return _resolve_curated_stock_photo(concrete_query, biz_type, used_urls)


def resolve_site_images(brief: Dict[str, Any]) -> Dict[str, Any]:
    biz_type = str(brief.get("archetype") or brief.get("business_type") or "general")
    used: Set[str] = set()
    hero = brief.get("hero") or {}
    business_name = str(brief.get("business_name", ""))
    if business_name.strip().lower() == "my business":
        business_name = ""  # the planner's placeholder is not a subject ("business" would match office stock)
    hero_query = str((hero.get("title") if isinstance(hero, dict) else "") or business_name)
    hero_photo = fetch_single_image(hero_query, biz_type, used)
    if hero_photo:
        used.add(hero_photo["url"])
    features = brief.get("features") or []
    items = features.get("items", []) if isinstance(features, dict) else features
    item_photos = []
    for item in items if isinstance(items, list) else []:
        title = item.get("title", "") if isinstance(item, dict) else str(item)
        photo = fetch_single_image(title, biz_type, used)
        if photo:
            item_photos.append(photo)
            used.add(photo["url"])
    prompt = str(brief.get("source_prompt") or (brief.get("requirement_manifest") or {}).get("source_prompt") or "")
    has_photos = bool(hero_photo or item_photos)
    illustration_requested = bool(re.search(r"\b(?:illustrations?|drawn|drawings?)\b", prompt, re.I))
    decision = "photography" if has_photos else ("illustration" if illustration_requested else "none")
    expectation = ("Use a clearly drawn illustration relevant to the requested subject; no curated photo matches."
                   if decision == "illustration" else ("No relevant curated photograph is available. Do not substitute an unrelated photo." if not has_photos else ""))
    return {**brief, "images": {"hero": hero_photo, "items": item_photos},
            "media_decision": decision, "media_expectation": expectation}
