"""Extract user requirements without treating layout counts as business facts."""
import re
import json
from typing import Any, TypedDict


class RequirementManifest(TypedDict):
    version: int
    source_prompt: str
    sections: list[str]
    explicit_sections: list[str]
    routes: list[str]
    exact_facts: list[str]
    interactions: list[str]
    visual_constraints: list[str]
    motion_constraints: list[dict[str, Any]]
    three_d_constraints: list[dict[str, Any]]
    interaction_constraints: list[dict[str, Any]]
    cross_section_contracts: list[dict[str, str]]


def build_requirement_manifest(prompt: str, brief: dict[str, Any]) -> RequirementManifest:
    """Record user facts and behavior requirements before section generation."""
    lower = prompt.lower()
    facts: list[str] = []
    from agent.site_brief import extract_supplied_products, extract_explicit_sections
    supplied_products = extract_supplied_products(prompt)
    for value in [brief.get("business_name"), *(
        item.get(key) for group, keys in (("products", ("name", "price")), ("projects", ("name", "url")))
        for item in (supplied_products if group == "products" else brief.get(group, [])) if isinstance(item, dict) for key in keys
    )]:
        value = str(value or "").strip()
        if value and value.lower() in lower and value not in facts:
            facts.append(value)
    for value in (brief.get("contact") or {}).values():
        if isinstance(value, str) and value.strip() and value.lower() in lower and value not in facts:
            facts.append(value.strip())
    interactions = []
    for name, pattern in (
        ("cart_state", r"\b(?:cart|add to bag|add to basket)\b"),
        ("filter_state", r"\b(?:filter|category selector|sort products)\b"),
        ("form_validation", r"\b(?:contact form|booking form|registration form|reservation form|inquiry form)\b"),
        ("mobile_nav_toggle", r"\b(?:mobile menu|hamburger menu|mobile navigation)\b"),
        ("flat_view_toggle", r"\b(?:flat[- ]view|2d[- ]view|flat mode|flatten)\b.{0,40}\b(?:toggle|switch|control|button)\b|\b(?:toggle|switch)\b.{0,40}\b(?:flat[- ]view|2d[- ]view|flat mode)\b"),
        ("anchor_navigation", r"\b(?:navigation links?|anchors?)\b.{0,50}\b(?:scroll|real sections?|targets?)\b"),
    ):
        if re.search(pattern, lower):
            interactions.append(name)
    contracts = []
    if "cart_state" in interactions:
        contracts.append({"state": "cart", "producer": "product action", "consumer": "shared cart indicator or panel"})
    if "filter_state" in interactions:
        contracts.append({"state": "filter", "producer": "filter control", "consumer": "visible result list"})
    if "flat_view_toggle" in interactions:
        contracts.append({"state": "flat_view", "producer": "flat view toggle", "consumer": "visible 3D composition switches to flat view and back"})
    motion = [item.to_dict() if hasattr(item, "to_dict") else item for item in brief.get("motion_plan", [])]
    if not motion:
        from agent.motion_patterns import extract_motion_requirements
        motion = [item.to_dict() for item in extract_motion_requirements(prompt, brief.get("sections") or None)]
    behavior = {
        "text_reveal": "Text visibly reveals over a timeline when its requested trigger occurs.",
        "scroll_reveal": "Content visibly changes from hidden to visible as it enters the viewport.",
        "parallax": "The target visibly displaces relative to other content as scroll progress changes; hover zoom does not satisfy this.",
        "horizontal_scroll": "Vertical scroll progress visibly moves the horizontal track, with a mobile fallback.",
        "sticky_story": "The target remains pinned while the associated narrative scrolls.",
        "micro_interaction": "The target visibly responds to pointer or keyboard interaction.",
    }
    motion = [{**item, "observable_behavior": behavior.get(item.get("type"), "Visible motion matches the requested trigger."),
               "requested_trigger": "scroll" if item.get("type") in {"parallax", "scroll_reveal", "horizontal_scroll", "sticky_story"} or
               (item.get("type") == "text_reveal" and re.search(r"\bscroll(?:ing)?\b.{0,35}\btext reveals?\b", lower)) else item.get("trigger", "viewport")}
              for item in motion if isinstance(item, dict)]
    three_d = []
    if re.search(r"\b(?:3d|three[- ]dimensional|webgl|three\.js|r3f)\b", lower):
        engines = []
        if re.search(r"\bcss[- ]?3d\b|\bcss\b.{0,20}\b(?:composition|perspective|scene)\b", lower):
            engines.append("css")
        if re.search(r"\b(?:webgl|three\.js|r3f|react three fiber)\b", lower):
            engines.append("webgl")
        for engine in engines or ["unspecified"]:
            three_d.append({"engine": engine, "visible_composition_required": True,
                            "flat_view_toggle_required": "flat_view_toggle" in interactions,
                            "reduced_motion_required": "reduced motion" in lower,
                            "observable_behavior": "Visible perspective and multiple depth planes form a 3D composition; a translate3d wrapper alone is insufficient.",
                            "source": prompt})
    interaction_constraints = []
    if "cart_state" in interactions:
        interaction_constraints.append({"type": "cart_state", "visible_state_required": True,
                                        "repeated_clicks_required": bool(re.search(r"\b(?:repeated|multiple|every|each)\b.{0,30}\bclick", lower)),
                                        "products": supplied_products})
    if "flat_view_toggle" in interactions:
        interaction_constraints.append({"type": "flat_view_toggle", "observable_behavior": "Toggle visibly switches the composition between depth and flat view, and can switch back."})
    visual = [term for term in ("3d", "parallax", "editorial", "minimal", "brutalist", "dark", "light") if term in lower]
    routes = list(dict.fromkeys(re.findall(r"(?<![\w:/])/[a-z][a-z0-9/-]*", prompt, re.I)))
    return {
        "version": 1, "source_prompt": prompt, "sections": list(brief.get("sections") or []),
        "explicit_sections": [name for name, _ in (extract_explicit_sections(prompt) or [])],
        "routes": routes, "exact_facts": facts, "interactions": interactions,
        "visual_constraints": visual, "motion_constraints": motion,
        "three_d_constraints": three_d, "interaction_constraints": interaction_constraints,
        "cross_section_contracts": contracts,
    }

_SECTION = re.compile(
    r"^(?:(?:and|a|an|the|sticky|responsive|animated)\s+)*"
    r"(nav(?:bar|igation)?|header|hero|features?|pricing|footer|contact|about|testimonials?|cta)\b",
    re.I,
)


def inline_sections(prompt):
    """Recognize an explicit Include: list, splitting outside parentheses only."""
    match = re.search(r"\b(?i:include|sections)\s*:\s*(.+?)(?:\.\s+(?=[A-Z])|\.$|$)", prompt, re.S)
    if not match:
        return None
    chunks, current, depth = [], [], 0
    for char in match.group(1):
        depth += (char == "(") - (char == ")")
        if char in ",;" and depth == 0:
            chunks.append("".join(current).strip())
            current = []
        else:
            current.append(char)
    chunks.append("".join(current).strip())
    result = []
    for chunk in chunks:
        found = _SECTION.match(chunk)
        if not found:
            return None  # Leave ambiguous lists to the existing parser.
        slug = found.group(1).lower()
        slug = "header" if slug.startswith("nav") else {"feature": "features", "testimonial": "testimonials"}.get(slug, slug)
        if slug not in [name for name, _ in result]:
            result.append((slug, chunk))
    return result if len(result) >= 2 else None


def is_count_description(text):
    return bool(re.fullmatch(
        r"\s*(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten|twelve)\s+"
        r"(?:feature\s+)?(?:cards?|items?|columns?|rows?|tiers?|plans?|features?)\s*", text, re.I))


def explicit_font(prompt):
    # Only permit a bounded font name, not arbitrary CSS copied from the prompt.
    match = re.search(r"\b(Inter|Space Grotesk|Plus Jakarta Sans|Outfit|Raleway|Syne)\s+font\b", prompt, re.I)
    return match.group(1) if match else None


def product_description(prompt, business_name):
    match = re.search(r'called\s+["\'][^"\']+["\']\s*[-—–�]+\s*(?:an?\s+)?([^.;\n]+)', prompt, re.I)
    return match.group(1).strip() if match else business_name


def compact_brief_context(brief):
    """Keep content once; omit duplicate token listings, plans and generic prose."""
    keys = ('business_name','business_type','tagline','sections','font_heading','font_body',
            'content_provenance','features','pricing_tiers','testimonials','contact',
            'menu_categories','projects','skills','products','hero_image','images','image_attribution')
    content = {key:brief[key] for key in keys if brief.get(key)}
    return json.dumps(content, ensure_ascii=False, separators=(',', ':'))
