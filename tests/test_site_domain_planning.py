from agent.agent import _BASE_SECTION_INSTRUCTIONS
from agent.design_plan import synthesize_design_plan
from agent.site_brief import _build_heuristic_brief, _ground_provider_brief, brief_to_xml, detect_business_type, extract_explicit_sections


def test_requests_use_domain_sections_without_saas_defaults():
    cases = (
        ("Portfolio for Maya, a ceramic artist with a gallery and contact form", "portfolio", {"gallery", "contact"}),
        ("E-commerce store for handmade candles with products, cart and checkout", "ecommerce", {"products", "cart", "checkout"}),
        ("Travel blog with articles and newsletter", "blog", {"articles", "newsletter"}),
        ("Conference website with schedule, speakers and tickets", "event", {"schedule", "speakers", "tickets"}),
        ("Astronomy club website with events and gallery", "general", {"events", "gallery"}),
        ("An ecommerce store for a coffee roastery with cart", "ecommerce", {"products", "cart"}),
        ("An architectural review publication with issue archives", "editorial", {"articles", "archives"}),
        ("A Kubernetes cluster health dashboard with node filters", "dashboard", {"dashboard"}),
    )
    for prompt, expected_type, required in cases:
        brief = _build_heuristic_brief(prompt)
        assert brief["business_type"] == expected_type
        assert required.issubset(brief["sections"])
        assert "pricing" not in brief["sections"]
        assert "features" not in brief["sections"]
        if expected_type == "dashboard":
            assert "hero" not in brief["sections"]
        assert brief["features"] == brief["pricing_tiers"] == brief["testimonials"] == []


def test_generic_product_word_does_not_turn_any_request_into_saas():
    assert detect_business_type("A handmade product catalog for my studio") != "saas"


def test_provider_cannot_inject_sample_business_facts_or_saas_sections():
    supplied = {
        "source": "gemini",
        "business_name": "Fictional Corp",
        "business_type": "saas",
        "sections": ["header", "hero", "features", "pricing", "footer"],
        "pricing_tiers": [{"name": "Pro", "price": "$99"}],
        "testimonials": [{"author": "Made Up", "quote": "Great"}],
        "primary_color": "#123456",
    }
    brief = _ground_provider_brief("Art gallery for Maya with a contact section", supplied, None)
    assert brief["business_type"] != "saas"
    assert "pricing" not in brief["sections"]
    assert not brief["pricing_tiers"] and not brief["testimonials"]
    assert brief["primary_color"] == "#123456"


def test_provider_can_plan_requested_custom_section():
    brief = _ground_provider_brief(
        "Astronomy club website with a telescope simulator",
        {"sections": ["header", "hero", "telescope simulator", "footer"]},
        None,
    )
    assert "telescope-simulator" in brief["sections"]
    assert "pricing" not in brief["sections"]


def test_domain_section_instructions_have_specific_behavior():
    for section in ("products", "cart", "checkout", "articles", "gallery", "schedule", "tickets", "events", "dashboard"):
        assert section in _BASE_SECTION_INSTRUCTIONS
    assert "site-cart" in _BASE_SECTION_INSTRUCTIONS["products"]
    assert "site-cart" in _BASE_SECTION_INSTRUCTIONS["cart"]


def test_inline_section_list_preserves_parenthesized_commas():
    prompt = (
        "Build a portfolio. Sections: masthead navigation, curated case study gallery "
        "with filtering (Installations, Algorithmic Art, Spatial UI), design philosophy manifesto, "
        "and direct inquiry contact section."
    )
    sections = extract_explicit_sections(prompt)
    assert [slug for slug, _ in sections] == ["masthead", "case-studies", "manifesto", "contact"]
    assert "Installations, Algorithmic Art, Spatial UI" in sections[1][1]


def test_non_saas_design_plans_match_site_purpose():
    expected = {"editorial": "publication", "blog": "journal", "event": "event", "dashboard": "data"}
    for domain, cue in expected.items():
        plan = synthesize_design_plan({"prompt": f"Create a {domain} website"}, domain=domain)
        assert "product-render" not in plan.visualAnchor
        assert cue in plan.artDirection


def test_supplied_catalog_and_palette_reach_model_brief():
    brief = _build_heuristic_brief(
        "Build an ecommerce shop with warm cream and forest green. Products: "
        "Linen Table Runner at $48, Oak Candle Holder at $32, and Ceramic Bud Vase at $38."
    )
    assert brief["products"] == [
        {"name": "Linen Table Runner", "price": "$48"},
        {"name": "Oak Candle Holder", "price": "$32"},
        {"name": "Ceramic Bud Vase", "price": "$38"},
    ]
    assert brief["background_color"] == "#f6f1e7"
    assert brief["primary_color"] == "#203b2b"
    xml = brief_to_xml(brief)
    assert '<product name="Linen Table Runner" price="$48" />' in xml
    assert "warm cream, forest green" in xml


def test_product_color_name_is_not_treated_as_palette():
    brief = _build_heuristic_brief("Build a store. Products: Black Candle at $20.")
    assert "requested_palette" not in brief
