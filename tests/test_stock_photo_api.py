"""
tests/test_stock_photo_api.py - Unit & integration tests for real stock-photo API integration.

Verifies:
1. Query builder maps abstract concepts (e.g. 'Real-Time Pipeline Execution') to concrete,
   photographable terms (e.g. 'cloud server infrastructure') instead of literal abstract labels.
2. Sanity filter rejects non-photos (diagrams, charts, document scans, SVG vectors, Wikimedia/Wikipedia).
3. Sanity filter accepts valid Unsplash and Pexels stock photographs.
4. Curated stock photo catalog entries all pass sanity filtering.
5. fetch_single_image returns verified stock photos with zero Wikimedia traces.
6. resolve_site_images generates unique, plausible, photographable images for features grids.
"""

import sys
import urllib.request
from pathlib import Path

# Add workspace root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from agent.site_brief import (
    _map_to_concrete_photo_query,
    _is_valid_photograph,
    _resolve_curated_stock_photo,
    _STOCK_PHOTO_CURATED_CATALOG,
    fetch_single_image,
    resolve_site_images,
)


def test_abstract_to_concrete_query_builder():
    """Verify abstract feature titles are mapped to concrete, photographable visual terms."""
    test_cases = [
        ("Real-Time Pipeline Execution", "cloud_saas", "cloud server infrastructure"),
        ("Automated Tracing", "cloud_saas", "data analytics dashboard"),
        ("Developer Code Automation", "cloud_saas", "software engineer coding workspace"),
        ("Predictive Telemetry", "cloud_saas", "data analytics dashboard"),
        ("Enterprise Security", "cloud_saas", "cybersecurity operations center"),
        ("Distributed Scaling", "cloud_saas", "cloud server infrastructure"),
        ("Sustainable Passive Design", "architecture", "sustainable modern green architecture building"),
        ("Raw Natural Materiality", "architecture", "minimalist natural stone and wood architecture interior"),
        ("Micro-Lot Sourcing", "coffee_shop", "artisan coffee farmer harvest fresh cherries"),
        ("Handcrafted Pour Over", "coffee_shop", "artisan cafe barista"),
        ("Corporate Litigation Practice", "legal", "prestigious corporate law firm library books"),
        ("Private Wealth Advisory", "finance", "financial district modern corporate towers skyline"),
    ]

    for abstract_title, biz_type, expected_term in test_cases:
        primary, fallbacks = _map_to_concrete_photo_query(abstract_title, biz_type=biz_type)
        combined_queries = f"{primary} {' '.join(fallbacks)}".lower()
        assert expected_term.lower() in combined_queries, (
            f"Expected concrete query for '{abstract_title}' ({biz_type}) to contain '{expected_term}', got '{primary}' / '{fallbacks}'"
        )
        # Ensure abstract junk is not literally preserved without concrete visual terms
        assert any(
            t in combined_queries
            for t in ["server", "coding", "dashboard", "datacenter", "architecture", "coffee", "law", "district", "building", "engineer", "barista", "stone"]
        ), f"Query '{primary}' does not contain physical, photographable terms."

    print("PASS: test_abstract_to_concrete_query_builder")


def test_sanity_filter_rejects_wikimedia_and_non_photos():
    """Verify sanity filter strictly rejects non-photos, charts, document scans, and Wikimedia."""
    bad_candidates = [
        # Wikimedia Commons / Wikipedia URLs
        {
            "url": "https://upload.wikimedia.org/wikipedia/commons/8/8b/Mercedes_Citaro_G.jpg",
            "alt": "Mercedes Citaro bus for enterprise",
            "title": "Bus",
            "source": "Wikimedia",
        },
        {
            "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3a/Real_time_pipeline_diagram.svg/1024px.png",
            "alt": "Pipeline architecture diagram",
            "title": "Architecture schematic",
            "source": "Wikimedia",
        },
        # Document scans and charts
        {
            "url": "https://images.unsplash.com/photo-example-1",
            "alt": "Flowchart of system architecture and execution pipeline",
            "title": "Pipeline flowchart diagram",
            "source": "Unsplash",
        },
        {
            "url": "https://images.unsplash.com/photo-example-2",
            "alt": "Historical whitepaper document scan 1984",
            "title": "Document scan",
            "source": "Unsplash",
        },
        {
            "url": "https://images.unsplash.com/photo-example-3",
            "alt": "Financial quarterly earnings line graph and pie chart",
            "title": "Quarterly chart",
            "source": "Unsplash",
        },
        # Non-photographic extensions
        {
            "url": "https://example.com/assets/cloud-icon.svg",
            "alt": "Vector cloud icon",
            "title": "Icon",
            "source": "Custom",
        },
        {
            "url": "https://example.com/assets/animation.gif",
            "alt": "Animated pipeline GIF",
            "title": "Animation",
            "source": "Custom",
        },
        # Extreme dimensions / corrupt aspect ratios
        {
            "url": "https://images.unsplash.com/photo-example-4",
            "alt": "Data server",
            "width": 100,
            "height": 50,  # Below 300px min
            "source": "Unsplash",
        },
        {
            "url": "https://images.unsplash.com/photo-example-5",
            "alt": "Data server",
            "width": 3000,
            "height": 200,  # 15:1 banner ratio, not a standard card/hero photo
            "source": "Unsplash",
        },
    ]

    for candidate in bad_candidates:
        assert not _is_valid_photograph(candidate), (
            f"Sanity filter failed: candidate should have been rejected: {candidate}"
        )

    print("PASS: test_sanity_filter_rejects_wikimedia_and_non_photos")


def test_sanity_filter_accepts_valid_stock_photos():
    """Verify sanity filter accepts legitimate high-res stock photographs."""
    valid_candidates = [
        {
            "url": "https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=1200&q=80",
            "alt": "Cloud server infrastructure with glowing blue cables and server racks",
            "title": "Modern cloud datacenter",
            "source": "Unsplash",
            "width": 1920,
            "height": 1080,
        },
        {
            "url": "https://images.pexels.com/photos/1181675/pexels-photo-1181675.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=1",
            "alt": "Software developer working with dual monitor code editor",
            "title": "Developer workspace",
            "source": "Pexels",
            "width": 1260,
            "height": 750,
        },
        {
            "url": "https://images.unsplash.com/photo-1497366216548-37526070297c?w=1600&q=80",
            "alt": "Modern open-plan office interior with natural sunlight",
            "title": "Office workspace",
            "source": "Unsplash",
            "width": 1600,
            "height": 900,
        },
    ]

    for candidate in valid_candidates:
        assert _is_valid_photograph(candidate), (
            f"Sanity filter incorrectly rejected valid photo: {candidate}"
        )

    print("PASS: test_sanity_filter_accepts_valid_stock_photos")


def test_curated_catalog_validity():
    """Verify all catalog entries in _STOCK_PHOTO_CURATED_CATALOG pass sanity checks."""
    assert len(_STOCK_PHOTO_CURATED_CATALOG) >= 25, (
        f"Catalog has only {len(_STOCK_PHOTO_CURATED_CATALOG)} entries; expected at least 25."
    )

    domains_covered = set()
    for entry in _STOCK_PHOTO_CURATED_CATALOG:
        # Check mandatory fields
        assert "url" in entry and entry["url"].startswith("https://images.unsplash.com/photo-"), (
            f"Entry URL must be Unsplash stock photo: {entry}"
        )
        assert "alt" in entry and len(entry["alt"]) > 10, f"Entry alt must be descriptive: {entry}"
        assert "credit" in entry and "Unsplash" in entry["credit"], f"Entry credit missing Unsplash: {entry}"
        assert entry.get("source") == "Unsplash", f"Entry source must be Unsplash: {entry}"

        # Sanity check
        assert _is_valid_photograph(entry), f"Catalog entry failed sanity check: {entry}"

        # Domain tracking
        for kw in entry.get("tags", []):
            domains_covered.add(kw.lower())

    # Ensure key domains are covered
    expected_domains = {"cloud", "saas", "server", "architecture", "coffee", "finance", "legal", "healthcare"}
    for dom in expected_domains:
        assert dom in domains_covered, f"Domain keyword '{dom}' not represented in curated catalog."

    print(f"PASS: test_curated_catalog_validity ({len(_STOCK_PHOTO_CURATED_CATALOG)} photos verified)")


def test_fetch_single_image_with_abstract_queries():
    """Verify fetch_single_image returns verified stock photos with zero Wikimedia content."""
    abstract_queries = [
        ("Real-Time Pipeline Execution", "cloud_saas"),
        ("Automated Tracing", "cloud_saas"),
        ("Enterprise Security", "cloud_saas"),
        ("Sustainable Passive Design", "architecture"),
        ("Single-Origin Pour Over", "coffee_shop"),
    ]

    used_urls = set()
    for query, biz_type in abstract_queries:
        photo = fetch_single_image(query, biz_type=biz_type, used_urls=used_urls)
        assert photo is not None, f"fetch_single_image failed for query '{query}'"
        assert photo.get("url"), f"Missing URL in result for '{query}'"

        url = photo["url"]
        assert "wikimedia" not in url.lower(), f"Wikimedia URL returned for '{query}': {url}"
        assert "wikipedia" not in url.lower(), f"Wikipedia URL returned for '{query}': {url}"
        assert url.startswith("https://images.unsplash.com/") or url.startswith("https://images.pexels.com/"), (
            f"Expected Unsplash or Pexels URL, got: {url}"
        )

        assert _is_valid_photograph(photo), f"Sanity check failed for returned photo: {photo}"
        assert url not in used_urls, f"Duplicate URL returned: {url}"
        used_urls.add(url)

    print("PASS: test_fetch_single_image_with_abstract_queries")


def test_resolve_site_images_features_grid_no_wikimedia():
    """Verify resolve_site_images produces plausible stock photographs for a features grid."""
    mock_brief = {
        "archetype": "cloud_saas",
        "business_name": "ApexCloud Telemetry",
        "hero": {
            "title": "Autonomous Observability for Modern Microservices",
            "subtitle": "Real-time trace telemetry and automated anomaly detection.",
        },
        "features": {
            "title": "Engineered for Mission-Critical Infrastructure",
            "items": [
                {
                    "title": "Real-Time Pipeline Execution",
                    "description": "Stream millions of metric points per second with zero drop rate.",
                },
                {
                    "title": "Automated Distributed Tracing",
                    "description": "Correlate bottlenecks across thousands of containerized microservices.",
                },
                {
                    "title": "Enterprise Security & Role Governance",
                    "description": "SOC2-certified vault encryption and granular audit logging.",
                },
                {
                    "title": "Predictive Telemetry & AI Alerts",
                    "description": "Detect degradation minutes before downstream customer impact.",
                },
            ],
        },
    }

    resolved = resolve_site_images(mock_brief)
    assert resolved is not None, "resolve_site_images returned None"

    # Verify images payload
    assert "images" in resolved, "Missing images in resolved output"
    images_payload = resolved["images"]
    assert "hero" in images_payload, "Missing hero in images payload"
    hero = images_payload["hero"]
    assert hero and hero.get("url"), "hero image missing or missing url"
    assert "wikimedia" not in hero["url"].lower(), f"Hero image is Wikimedia: {hero['url']}"
    assert hero["url"].startswith("https://images.unsplash.com/") or hero["url"].startswith("https://images.pexels.com/")
    assert _is_valid_photograph(hero), f"Hero failed sanity check: {hero}"

    # Verify item images
    assert "items" in images_payload, "Missing items in images payload"
    item_images = images_payload["items"]
    assert len(item_images) == 4, f"Expected 4 item images, got {len(item_images)}"

    seen_item_urls = set()
    seen_item_urls.add(hero["url"])

    for idx, item in enumerate(item_images):
        url = item.get("url")
        assert url, f"Item {idx} missing url"
        assert "wikimedia" not in url.lower(), f"Item {idx} is Wikimedia: {url}"
        assert url.startswith("https://images.unsplash.com/") or url.startswith("https://images.pexels.com/")
        assert _is_valid_photograph(item), f"Item {idx} failed sanity check: {item}"
        assert url not in seen_item_urls, f"Duplicate image URL used across grid items: {url}"
        seen_item_urls.add(url)

    print("PASS: test_resolve_site_images_features_grid_no_wikimedia (Hero + 4 unique feature photos verified)")


def test_live_photo_urls_connectivity_sample():
    """Verify that a representative sample of stock photo URLs are live (HTTP 200)."""
    sample_urls = [
        "https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=1200&q=80",  # server racks
        "https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=1200&q=80",  # analytics dashboard
        "https://images.unsplash.com/photo-1518770660439-4636190af475?w=1200&q=80",  # hardware circuit
        "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?w=1200&q=80",  # modern architecture
        "https://images.unsplash.com/photo-1501339847302-ac426a4a7cbb?w=1200&q=80",  # coffee shop
    ]

    for url in sample_urls:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        try:
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                assert resp.status == 200, f"URL {url} returned status {resp.status}"
        except Exception as e:
            assert False, f"Connectivity check failed for {url}: {e}"

    print("PASS: test_live_photo_urls_connectivity_sample (All 5 live stock photo URLs returned HTTP 200)")


if __name__ == "__main__":
    print("=" * 70)
    print("RUNNING STOCK PHOTO API & SANITY FILTER TEST SUITE")
    print("=" * 70)

    test_abstract_to_concrete_query_builder()
    test_sanity_filter_rejects_wikimedia_and_non_photos()
    test_sanity_filter_accepts_valid_stock_photos()
    test_curated_catalog_validity()
    test_fetch_single_image_with_abstract_queries()
    test_resolve_site_images_features_grid_no_wikimedia()
    test_live_photo_urls_connectivity_sample()

    print("=" * 70)
    print("ALL STOCK PHOTO API TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)
