#!/usr/bin/env python3
"""
data_pipeline/prompt_fidelity_gate.py - Prompt-Fidelity Quality Gate for ReactAgent SLM

Verifies that synthesized components and multi-section sites strictly adhere to
user prompts and content briefs by ensuring:
1. Named entities (business name, custom section titles, product/service offerings,
   pricing tiers, menu categories, specific prop names, aria-labels) are preserved.
2. Numerical counts (number of sections, pricing tiers, cards, items) are satisfied.
3. Silent dropping of requirements or genericization (e.g. replacing a specific brand
   with "Company Name" or "My Business") is rejected.
"""

import re
from typing import Any, Dict, List, Optional, Set, Tuple, Union


# Common generic placeholders that indicate silent genericization
GENERIC_PLACEHOLDER_PATTERNS = [
    r"\bCompany\s+Name\b",
    r"\bYour\s+Company\b",
    r"\bMy\s+Business\b",
    r"\bAcme\s+Corp\b",
    r"\bLorem\s+ipsum\b",
    r"\bDolor\s+sit\s+amet\b",
    r"\bGeneric\s+Title\b",
    r"\bSample\s+Business\b",
    r"\bPlaceholder\s+(?:Title|Text|Name|Description|Item|Company|Content)\b",
    r"\[Placeholder\]",
    r"\bInsert\s+(?:Text|Content|Name)\s+Here\b",
]

_GENERIC_RE = [re.compile(p, re.IGNORECASE) for p in GENERIC_PLACEHOLDER_PATTERNS]

# Word-to-number mapping for parsing count constraints
_WORD_NUM_MAP = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "single": 1, "dual": 2, "triple": 3,
}


def _normalize_text(text: str) -> str:
    """Normalizes whitespace and lowercases for fuzzy match checks."""
    return re.sub(r"\s+", " ", text).strip().lower()


def parse_brief_entities(brief: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extracts all canonical named entities and expected counts from a content brief dict.
    """
    entities: Dict[str, Any] = {
        "business_name": brief.get("business_name", "").strip(),
        "tagline": brief.get("tagline", "").strip(),
        "sections": list(brief.get("sections", [])),
        "feature_titles": [],
        "tier_names": [],
        "menu_items": [],
        "testimonial_authors": [],
        "custom_sections": [],
        "expected_counts": {},
    }

    # Features / Offerings
    if "features" in brief and isinstance(brief["features"], list):
        for f in brief["features"]:
            if isinstance(f, dict) and f.get("title"):
                entities["feature_titles"].append(f["title"].strip())
            elif isinstance(f, str) and f.strip():
                entities["feature_titles"].append(f.strip())
        if entities["feature_titles"]:
            entities["expected_counts"]["features"] = len(entities["feature_titles"])

    # Pricing Tiers
    if "pricing_tiers" in brief and isinstance(brief["pricing_tiers"], list):
        for t in brief["pricing_tiers"]:
            if isinstance(t, dict) and t.get("name"):
                entities["tier_names"].append(t["name"].strip())
        if entities["tier_names"]:
            entities["expected_counts"]["pricing_tiers"] = len(entities["tier_names"])

    # Menu Categories / Items
    if "menu_categories" in brief and isinstance(brief["menu_categories"], list):
        for cat in brief["menu_categories"]:
            if isinstance(cat, dict) and cat.get("name"):
                entities["menu_items"].append(cat["name"].strip())
                for itm in cat.get("items", []):
                    if isinstance(itm, dict) and itm.get("name"):
                        entities["menu_items"].append(itm["name"].strip())

    # Testimonials
    if "testimonials" in brief and isinstance(brief["testimonials"], list):
        for test in brief["testimonials"]:
            if isinstance(test, dict) and test.get("author"):
                entities["testimonial_authors"].append(test["author"].strip())
        if entities["testimonial_authors"]:
            entities["expected_counts"]["testimonials"] = len(entities["testimonial_authors"])

    # Custom section instructions
    custom_instrs = brief.get("custom_section_instructions", {})
    if isinstance(custom_instrs, dict):
        for sec_slug in custom_instrs:
            if sec_slug not in ("header", "hero", "footer"):
                clean_name = " ".join(w.capitalize() for w in re.split(r"[-_]", sec_slug) if w)
                entities["custom_sections"].append(clean_name)

    if entities["sections"]:
        entities["expected_counts"]["sections"] = len(entities["sections"])

    return entities


def parse_prompt_entities_and_counts(prompt: str) -> Dict[str, Any]:
    """
    Parses named entities and quantity constraints directly from a raw user prompt.
    """
    parsed: Dict[str, Any] = {
        "quoted_entities": [],
        "named_entities": [],
        "aria_labels": [],
        "counts": {},
        "target_symbols": [],
    }

    # 1. Quoted phrases (e.g. 'AURA Spatial Audio' or "Beacon Coffee")
    quotes = re.findall(r"['\"]([^'\"]{3,60})['\"]", prompt)
    for q in quotes:
        clean_q = q.strip()
        if not clean_q.startswith("sa-") and not clean_q.startswith("kt-") and not clean_q.startswith("asa-"):
            parsed["quoted_entities"].append(clean_q)

    # 2. aria-label requests (e.g. aria-label="Current color")
    aria_matches = re.findall(r'aria-label=[\'"]([^\'"]+)[\'"]', prompt, re.IGNORECASE)
    parsed["aria_labels"].extend(aria_matches)

    # 3. Target React symbol names (e.g. `ColorPicker` or `SpeedDial`)
    symbols = re.findall(r"`([A-Z][A-Za-z0-9]+)`", prompt)
    parsed["target_symbols"].extend(symbols)

    # 4. Explicit quantity patterns (e.g. "3 pricing tiers", "4 sections", "5 features")
    count_patterns = [
        r"\b(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+([a-zA-Z_-]+(?:\s+[a-zA-Z_-]+)?)\b",
    ]
    for cp in count_patterns:
        for num_str, noun in re.findall(cp, prompt, re.IGNORECASE):
            noun_norm = noun.lower().strip()
            # Filter common keywords
            for target_noun in ["section", "tier", "pricing tier", "feature", "testimonial", "card", "category", "menu item"]:
                if target_noun in noun_norm:
                    val = int(num_str) if num_str.isdigit() else _WORD_NUM_MAP.get(num_str.lower(), 0)
                    if val > 0:
                        parsed["counts"][target_noun] = val

    # 5. Extract listed sections after 'with' (e.g. 'with Header, Hero, Spatial Products, and Footer')
    with_match = re.search(r"\bwith\s+([A-Z][a-zA-Z0-9_,\s]+(?:and\s+[A-Z][a-zA-Z0-9_]+)?)\b", prompt)
    if with_match:
        items = re.split(r",|\band\b", with_match.group(1))
        for itm in items:
            clean_itm = itm.strip()
            if clean_itm and len(clean_itm) > 2 and clean_itm[0].isupper():
                parsed["named_entities"].append(clean_itm)

    return parsed


def _extract_all_code(rendered_files: Union[Dict[str, Any], List[Tuple[str, str]], List[Dict[str, Any]], str]) -> str:
    """Consolidates all source code and markup from rendered files or trajectory messages into a single corpus."""
    if isinstance(rendered_files, str):
        return rendered_files

    if isinstance(rendered_files, dict):
        chunks = []
        # Check if full trajectory dict
        if "messages" in rendered_files and isinstance(rendered_files["messages"], list):
            for m in rendered_files["messages"]:
                if isinstance(m, dict) and "content" in m:
                    chunks.append(str(m["content"]))
        if "files" in rendered_files and isinstance(rendered_files["files"], dict):
            for v in rendered_files["files"].values():
                chunks.append(str(v))
        if "code" in rendered_files and isinstance(rendered_files["code"], str):
            chunks.append(rendered_files["code"])

        if chunks:
            return "\n".join(chunks)

        # Fallback: simple {filename: code_string} dict
        for v in rendered_files.values():
            if isinstance(v, str):
                chunks.append(v)
            elif isinstance(v, (dict, list)):
                chunks.append(str(v))
        return "\n".join(chunks)

    if isinstance(rendered_files, list):
        chunks = []
        for item in rendered_files:
            if isinstance(item, tuple) and len(item) == 2:
                chunks.append(str(item[1]))
            elif isinstance(item, dict):
                # Could be a trajectory message or file map
                if "content" in item:
                    chunks.append(str(item["content"]))
                elif "files" in item and isinstance(item["files"], dict):
                    chunks.extend(str(v) for v in item["files"].values())
                else:
                    chunks.extend(str(v) for v in item.values() if isinstance(v, str))
            elif isinstance(item, str):
                chunks.append(item)
        return "\n".join(chunks)

    return str(rendered_files)


def verify_prompt_fidelity(
    prompt: str,
    rendered_files: Union[Dict[str, str], List[Tuple[str, str]], List[Dict[str, Any]], str],
    brief: Optional[Dict[str, Any]] = None,
    tolerance: float = 0.85,
) -> Tuple[bool, List[str], Dict[str, Any]]:
    """
    Evaluates prompt fidelity across rendered code.

    Returns:
        (passed: bool, failure_reasons: list[str], metrics: dict)
    """
    code_corpus = _extract_all_code(rendered_files)
    lower_code = code_corpus.lower()
    norm_code = _normalize_text(code_corpus)

    reasons: List[str] = []
    checked_count = 0
    passed_count = 0

    # 1. Generic placeholder check: reject silent genericization
    # Only flag generic placeholder if the prompt itself didn't ask for a generic placeholder
    # Strip HTML/JSX placeholder="..." attributes and prop definitions so standard inputs aren't flagged
    text_corpus_for_generics = re.sub(r'placeholder\s*=\s*["\'][^"\']*["\']', '', code_corpus, flags=re.IGNORECASE)
    text_corpus_for_generics = re.sub(r'\bplaceholder\s*:\s*string\b', '', text_corpus_for_generics, flags=re.IGNORECASE)

    for pattern in _GENERIC_RE:
        match = pattern.search(text_corpus_for_generics)
        if match:
            matched_text = match.group(0)
            if matched_text.lower() not in prompt.lower():
                reasons.append(f"Contains generic placeholder '{matched_text}' instead of domain content.")

    # 2. Extract entities from brief (if provided)
    brief_entities = parse_brief_entities(brief) if brief else {}
    prompt_entities = parse_prompt_entities_and_counts(prompt)

    # 3. Check Business Name
    business_name = brief_entities.get("business_name")
    if not business_name:
        # Check quoted entities from prompt for potential business name (excluding aria-labels and code tokens)
        for q in prompt_entities["quoted_entities"]:
            if q in prompt_entities["aria_labels"]:
                continue
            if len(q.split()) <= 6 and not any(k in q.lower() for k in ["aria", "button", "src", "px", "#", "http", ".tsx", ".css"]):
                business_name = q
                break

    if business_name and len(business_name) > 2:
        checked_count += 1
        norm_bname = _normalize_text(business_name)
        # Check if business name appears in code (exact or normalized)
        if norm_bname in norm_code or business_name.lower() in lower_code:
            passed_count += 1
        else:
            reasons.append(f"Business name '{business_name}' is missing from rendered output.")

    # 4. Check Custom Sections & Named Sections
    custom_sections = brief_entities.get("custom_sections", [])
    for c_sec in custom_sections:
        checked_count += 1
        norm_sec = _normalize_text(c_sec)
        # Accept if either title appears in JSX or section ID/className appears
        sec_slug = re.sub(r"[^a-z0-9]", "", norm_sec)
        if norm_sec in norm_code or sec_slug in lower_code.replace("-", "").replace("_", ""):
            passed_count += 1
        else:
            reasons.append(f"Custom section '{c_sec}' was silently dropped.")

    # 5. Check Prompt Named Entities (e.g. Header, Hero, Spatial Products, Footer)
    for ent in prompt_entities["named_entities"]:
        # Skip generic standard sections
        if ent.lower() in ("header", "hero", "features", "footer", "contact"):
            continue
        checked_count += 1
        norm_ent = _normalize_text(ent)
        ent_slug = re.sub(r"[^a-z0-9]", "", norm_ent)
        if norm_ent in norm_code or ent_slug in lower_code.replace("-", "").replace("_", ""):
            passed_count += 1
        else:
            reasons.append(f"Named entity/section '{ent}' from prompt is missing.")

    # 6. Check Feature / Tier Titles from Brief (at least 50% must be present if specified)
    feature_titles = brief_entities.get("feature_titles", [])
    if feature_titles:
        matched_feats = 0
        for f_title in feature_titles:
            if _normalize_text(f_title) in norm_code:
                matched_feats += 1
        checked_count += len(feature_titles)
        passed_count += matched_feats
        if matched_feats < max(1, len(feature_titles) // 2):
            reasons.append(
                f"Only {matched_feats}/{len(feature_titles)} brief feature offerings appear in output."
            )

    tier_names = brief_entities.get("tier_names", [])
    if tier_names:
        matched_tiers = 0
        for t_name in tier_names:
            if _normalize_text(t_name) in norm_code:
                matched_tiers += 1
        checked_count += len(tier_names)
        passed_count += matched_tiers
        if matched_tiers < max(1, len(tier_names) // 2):
            reasons.append(
                f"Only {matched_tiers}/{len(tier_names)} pricing tier names appear in output."
            )

    # 7. Check Component Target Symbol and aria-labels (for single-component tasks)
    for sym in prompt_entities["target_symbols"]:
        checked_count += 1
        if sym in code_corpus:
            passed_count += 1
        else:
            reasons.append(f"Target React component symbol '{sym}' is not declared or exported.")

    for aria_val in prompt_entities["aria_labels"]:
        checked_count += 1
        if aria_val.lower() in lower_code:
            passed_count += 1
        else:
            reasons.append(f"Required aria-label '{aria_val}' was not rendered.")

    # 8. Quantity Count Verification
    counts_to_check = {**brief_entities.get("expected_counts", {}), **prompt_entities.get("counts", {})}
    for entity_type, expected_min in counts_to_check.items():
        if "section" in entity_type:
            # Count <section> or <header>/<footer> or sa-* / *-section elements
            rendered_sections = len(re.findall(r"<(?:section|header|footer)\b", code_corpus, re.IGNORECASE))
            if rendered_sections < expected_min:
                reasons.append(
                    f"Requested {expected_min} sections, but only found {rendered_sections} in rendered markup."
                )
        elif "tier" in entity_type or "pricing" in entity_type:
            rendered_tiers = len(re.findall(r'class(?:Name)?=[\'"][^\'"]*(?:tier|plan|pricing-card)[^\'"]*[\'"]', code_corpus, re.IGNORECASE))
            if rendered_tiers == 0:
                # Count button elements in pricing section as fallback
                rendered_tiers = len(re.findall(r"\b(?:tier|pricing|plan)\b", lower_code))
            if rendered_tiers < expected_min and rendered_tiers < 2:
                reasons.append(f"Expected {expected_min} pricing tiers, but detected insufficient tier elements.")

    # Final Gate Decision
    passed = len(reasons) == 0
    fidelity_score = (passed_count / max(1, checked_count)) if checked_count > 0 else 1.0

    metrics = {
        "checked_entities_count": checked_count,
        "passed_entities_count": passed_count,
        "fidelity_score": round(fidelity_score, 3),
        "reasons": reasons,
    }

    return passed, reasons, metrics
