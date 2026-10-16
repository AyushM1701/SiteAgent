"""Regression tests for the planners: requested sections, negation, per-prompt
design seeding, and one art direction per prompt."""
from agent.design_plan import synthesize_design_plan
from agent.site_brief import extract_sections_from_prompt, generate_content_brief

CERAMICS = (
    "Build a complete responsive website for Aster & Kiln ceramics. Create a collection-led "
    "storefront with glaze stories, product detail, care guide and studio notes. Required "
    "interaction: Filter by vessel type and add an item to a shared cart; show honest "
    "checkout-unavailable messaging. Art direction: warm editorial photography, clay textures, "
    "restrained hover motion. Use specific honest content; do not invent testimonials, payment "
    "completion, or live data."
)


def test_prose_feature_list_becomes_sections_and_unavailable_checkout_is_excluded():
    sections = extract_sections_from_prompt(CERAMICS, "ecommerce")
    for wanted in ("glaze-stories", "product-detail", "care-guide", "studio-notes", "products", "cart"):
        assert wanted in sections
    assert "checkout" not in sections
    assert "testimonials" not in sections
    assert sections[0] == "header" and sections[-1] == "footer"


def test_negated_requests_do_not_add_sections():
    saas = extract_sections_from_prompt(
        "A SaaS landing page for a CI tool. Do not show pricing; we are invite-only. Include a product preview.", "saas")
    assert "pricing" not in saas
    assert "testimonials" not in saas  # "preview" is not "review"

    restaurant = extract_sections_from_prompt(
        "Restaurant site. We do not take reservations and have no contact form.", "restaurant")
    assert "booking" not in restaurant
    assert "contact" not in restaurant
    assert "menu" in restaurant


def test_negation_scope_ends_at_reset_words_and_hyphenated_no():
    assert "pricing" in extract_sections_from_prompt(
        "Bakery site without a signup wall, featuring pricing and a menu.", "restaurant")
    assert "pricing" in extract_sections_from_prompt("A no-code builder SaaS with pricing and an FAQ.", "saas")


def test_style_lists_are_not_sections():
    sections = extract_sections_from_prompt("A portfolio with warm colors, serif type and subtle motion.", "portfolio")
    assert not any(word in "-".join(sections) for word in ("color", "serif", "motion"))


def test_design_plan_varies_with_prompt_when_task_index_is_fixed():
    prompts = ["A bakery website for Crumb & Co", "A yoga studio site for Stillwater",
               "A law firm site for Hart Legal", "A florist site for Petal Row",
               "A bookshop site for Margins", "A tailor site for Fold & Hem"]
    plans = [synthesize_design_plan({"prompt": p}, "general", 0) for p in prompts]
    assert len({p.heroArchetype for p in plans}) > 1
    assert len({p.designGenome["palette"] for p in plans}) > 1
    # Same prompt, same plan.
    again = synthesize_design_plan({"prompt": prompts[0]}, "general", 0)
    assert again.to_dict() == plans[0].to_dict()


def test_non_technical_domains_never_get_terminal_hero():
    for i in range(30):
        plan = synthesize_design_plan({"prompt": f"A neighbourhood bakery number {i}"}, "restaurant", 0)
        assert plan.heroArchetype not in {"terminal_data", "product_stage"}


def test_brief_layout_archetype_guides_hero_when_prompt_is_silent():
    plan = synthesize_design_plan({"prompt": "A ceramics shop", "layoutArchetype": "bento"}, "ecommerce", 0)
    assert plan.heroArchetype == "bento"


def test_aligned_plan_defers_visual_system_to_brief():
    plan = synthesize_design_plan({"prompt": "A ceramics shop with warm editorial photography"}, "ecommerce", 0)
    plan.align_with_brief(media_available=False)
    for owned in ("palette", "display_font", "body_font", "theme_mode", "hero", "density"):
        assert owned not in plan.designGenome
    assert "photo" not in plan.visualAnchor
    assert "design system in the Content Brief" in plan.to_prompt_block()


def test_incidental_style_words_do_not_force_a_preset():
    brief = generate_content_brief(CERAMICS, provider="heuristic")
    assert "style_spec" not in brief
    luxury_goods = generate_content_brief("A shop selling luxury ceramics and champagne flutes.", provider="heuristic")
    assert "style_spec" not in luxury_goods
    styled = generate_content_brief("A ceramics shop in an editorial style.", provider="heuristic")
    assert "style_spec" in styled


# --- Phase 1 planner fixes (IMPLEMENTATION_PLAN_2026-10-16 §5) ---
import pytest

from agent.site_brief import detect_business_type, extract_business_name, parse_section_spec

ASTER = ("Aster & Kiln — handmade ceramics studio in Lisbon. Warm editorial photography, clay textures. "
         "Sections: collection, glaze stories, care guide, studio notes. Email hello@asterkiln.com. No online checkout.")
NORTHWIND = ("Northwind — a B2B analytics SaaS for logistics teams. Dark, technical look. "
             "Include a product preview and FAQ. Do not show pricing.")
SAFFRON = ("Saffron Table — modern Indian restaurant in Dehradun. Menu, about the chef, private dining. "
           "We do not take online reservations.")
MAYA = ("Portfolio for Maya Chen, a brand designer. Minimal, lots of white space. "
        "Projects: Fern Studio rebrand, Halo app identity, Ostra packaging.")
IRONWORKS = "Ironworks — a strength gym in Pune. Classes, coaches, membership pricing, FAQ, contact."
THREADLEAF = ("Threadleaf stationery shop. Products: Notebook $12, Pencil set $8, Desk planner $24. "
              "Add to cart with a cart count. FAQ and contact.")


@pytest.mark.parametrize("prompt, name", [
    (ASTER, "Aster & Kiln"),
    (NORTHWIND, "Northwind"),
    (SAFFRON, "Saffron Table"),
    (MAYA, "Maya Chen"),
    ("A website for a bakery called Crumb & Co.", "Crumb & Co"),
    ("A landing page for a yoga studio", "Yoga Studio"),
    (IRONWORKS, "Ironworks"),
    (THREADLEAF, "Threadleaf"),
])
def test_business_name_extraction(prompt, name):
    assert extract_business_name(prompt) == name


def test_bare_list_sentence_becomes_sections():
    sections = extract_sections_from_prompt(SAFFRON, detect_business_type(SAFFRON))
    assert sections == ["header", "hero", "menu", "about", "private-dining", "contact", "footer"]


@pytest.mark.parametrize("style_sentence", ["Minimal, lots of white space.", "Warm editorial photography, clay textures.",
                                            "Dark, technical look.", "Playful, colourful and cozy."])
def test_style_sentences_add_no_sections(style_sentence):
    base = extract_sections_from_prompt("A bakery website.", "restaurant")
    assert extract_sections_from_prompt("A bakery website. " + style_sentence, "restaurant") == base


def test_colon_item_list_is_parsed_into_items():
    spec = parse_section_spec("projects", MAYA)
    assert spec["parsed_items"] == ["Fern Studio rebrand", "Halo app identity", "Ostra packaging"]
    sections = extract_sections_from_prompt(MAYA, detect_business_type(MAYA))
    assert not any(word in "-".join(sections) for word in ("fern", "halo", "ostra"))
    brief = generate_content_brief(MAYA)
    assert brief["section_plans"]["projects"]["parsed_items"] == ["Fern Studio rebrand", "Halo app identity", "Ostra packaging"]


def test_skills_only_when_requested():
    assert "skills" not in extract_sections_from_prompt(MAYA, "portfolio")
    assert "skills" in extract_sections_from_prompt("Portfolio for a developer. Show my tech stack and projects.", "portfolio")


def test_synonym_sections_merge():
    sections = extract_sections_from_prompt(IRONWORKS, detect_business_type(IRONWORKS))
    class_like = [s for s in sections if s in {"programs", "classes", "courses", "services"}]
    price_like = [s for s in sections if s in {"pricing", "membership", "plans", "packages"}]
    assert class_like == ["classes"]
    assert len(price_like) == 1
    for wanted in ("coaches", "faq", "contact"):
        assert wanted in sections


def test_include_colon_lists_of_section_names_are_explicit():
    from agent.site_brief import extract_explicit_sections
    found = extract_explicit_sections("Build a shop for North Goods. Include: header, hero, features, footer. Add to cart.")
    assert [slug for slug, _ in found] == ["header", "hero", "features", "footer"]
    # An "Include:" list of styling or behaviour is not a section list.
    assert extract_explicit_sections("A bakery site. Include: dark mode, subtle animations, warm colours.") is None


def test_descriptive_include_lists_stay_with_the_heuristic_planner():
    from agent.site_brief import extract_explicit_sections
    prompt = ("A SaaS startup called NexaFlow. Include: a sticky nav with a CTA, a hero section with animated "
              "gradient text, a features grid (6 cards), a pricing section with a monthly/annual toggle, and a footer.")
    assert extract_explicit_sections(prompt) is None


@pytest.mark.parametrize("prompt, name", [
    ("A summer coding camp for kids in Bengaluru with schedule, pricing and FAQ", "Summer Coding Camp"),
    ("A small bakery in Leeds with a menu and contact", "Small Bakery"),
])
def test_a_place_is_not_a_business_name(prompt, name):
    assert extract_business_name(prompt) == name
