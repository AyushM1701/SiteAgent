"""
scripts/verify_stock_photo_grid.py - End-to-end verification of features grid stock photo generation.

Tests generating feature grids with abstract and domain concepts across:
1. Cloud/SaaS Observability ("Real-Time Pipeline Execution", "Automated Distributed Tracing",
   "Enterprise Security Governance", "Predictive Telemetry & AI Alerts")
2. Modern Architecture Studio ("Sustainable Passive Design", "Raw Natural Materiality",
   "Precision BIM Modeling", "Luxury Villa Residence")
3. Specialty Coffee Roastery ("Micro-Lot Direct Trade", "Commercial Precision Roasting",
   "Peak Freshness Delivery", "Handcrafted Pour Over Bar")

Validates:
- Every image is a real, plausible photograph (Unsplash / Pexels)
- Zero Wikimedia/Wikipedia URLs or document scans/diagrams
- All images pass photographic sanity filtering
- Abstract concepts are translated to photographable visual terms
- No duplicate URLs across hero and grid items
"""

import sys
from pathlib import Path

# Add workspace root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from agent.site_brief import generate_content_brief, _is_valid_photograph


def verify_domain_features_grid(prompt: str, domain_name: str):
    print("\n" + "=" * 75)
    print(f"VERIFYING FEATURES GRID FOR: {domain_name.upper()}")
    print(f"Prompt: {prompt}")
    print("=" * 75)

    brief = generate_content_brief(prompt, provider="auto", resolve_images=True)

    assert brief, "Failed to generate brief"
    assert "images" in brief, "Brief missing 'images' payload"

    images_payload = brief["images"]
    hero = images_payload.get("hero")
    items = images_payload.get("items", [])
    attribution = brief.get("image_attribution", "")

    print(f"\n[Hero Image]")
    assert hero and hero.get("url"), f"Missing hero image for {domain_name}"
    hero_url = hero["url"]
    print(f"  URL:    {hero_url}")
    print(f"  Alt:    {hero.get('alt')}")
    print(f"  Source: {hero.get('source')}")
    print(f"  Credit: {hero.get('credit')}")

    assert "wikimedia" not in hero_url.lower(), f"Forbidden Wikimedia in hero: {hero_url}"
    assert "wikipedia" not in hero_url.lower(), f"Forbidden Wikipedia in hero: {hero_url}"
    assert hero_url.startswith("https://images.unsplash.com/") or hero_url.startswith("https://images.pexels.com/"), (
        f"Hero URL must be Unsplash or Pexels: {hero_url}"
    )
    assert _is_valid_photograph(hero), f"Hero failed photographic sanity check: {hero}"

    print(f"\n[Grid Item Images] ({len(items)} items resolved)")
    seen_urls = {hero_url}

    for idx, itm in enumerate(items):
        itm_name = itm.get("name", f"Item #{idx+1}")
        url = itm.get("url", "")
        alt = itm.get("alt", "")
        credit = itm.get("credit", "")
        source = itm.get("source", "")

        print(f"  Item {idx+1}: '{itm_name}'")
        print(f"    URL:    {url}")
        print(f"    Alt:    {alt}")
        print(f"    Source: {source} | Credit: {credit}")

        assert url, f"Item '{itm_name}' missing URL"
        assert "wikimedia" not in url.lower(), f"Forbidden Wikimedia in item: {url}"
        assert "wikipedia" not in url.lower(), f"Forbidden Wikipedia in item: {url}"
        assert url.startswith("https://images.unsplash.com/") or url.startswith("https://images.pexels.com/"), (
            f"Item URL must be Unsplash or Pexels: {url}"
        )
        assert _is_valid_photograph(itm), f"Item failed photographic sanity check: {itm}"
        assert url not in seen_urls, f"Duplicate image URL used across cards: {url}"
        seen_urls.add(url)

    print(f"\n[Attribution Line]")
    print(f"  {attribution}")
    assert "photographers" in attribution.lower(), f"Missing photography attribution: {attribution}"
    assert "wikimedia" not in attribution.lower(), f"Attribution mentions Wikimedia: {attribution}"

    print(f"\nSUCCESS: {domain_name} features grid verified with {len(items)} plausible stock photographs.")


if __name__ == "__main__":
    test_domains = [
        (
            "Create a high-tech dark landing page for ApexCloud telemetry platform with features: "
            "Real-Time Pipeline Execution, Automated Distributed Tracing, Enterprise Security Governance, "
            "Predictive Telemetry & AI Alerts",
            "Cloud / SaaS Infrastructure",
        ),
        (
            "Modern minimalist architecture studio showcasing: "
            "Sustainable Passive Design, Raw Natural Materiality, Precision BIM Modeling, Luxury Villa Residence",
            "Modern Architecture Studio",
        ),
        (
            "Artisanal coffee roasters offering: "
            "Micro-Lot Direct Trade, Commercial Precision Roasting, Peak Freshness Delivery, Handcrafted Pour Over Bar",
            "Specialty Coffee Roastery",
        ),
    ]

    for prompt, name in test_domains:
        verify_domain_features_grid(prompt, name)

    print("\n" + "=" * 75)
    print("ALL FEATURE GRID IMAGE VERIFICATIONS COMPLETED SUCCESSFULLY!")
    print("=" * 75)
