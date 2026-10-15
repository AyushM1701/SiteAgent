"""Design-kit tests (IMPLEMENTATION_PLAN_2026-10-16 §6.7).

The kit owns layout, typography, imagery and interaction; the model only writes
JSON copy. These tests prove the kit's output is valid and validator-clean for
realistic model output and for the deterministic fallback.
"""
import json
import shutil
import subprocess
import uuid
from pathlib import Path

import pytest

from agent.site_brief import generate_content_brief
from agent.site_kit import KitSite
from agent.site_kit.content import Integrity, parse_json_object, section_kind
from agent.site_kit.imagery import ImagePlanner
from agent.site_kit.themes import THEMES, contrast, select_theme

ROOT = Path(__file__).resolve().parents[1]

ASTER = ("Aster & Kiln — handmade ceramics studio in Lisbon. Warm editorial photography, clay textures. "
         "Sections: collection, glaze stories, care guide, studio notes. Email hello@asterkiln.com. No online checkout.")
NORTHWIND = ("Northwind — a B2B analytics SaaS for logistics teams. Dark, technical look. "
             "Include a product preview and FAQ. Do not show pricing.")
SAFFRON = ("Saffron Table — modern Indian restaurant in Dehradun. Menu, about the chef, private dining. "
           "We do not take online reservations.")
MAYA = ("Portfolio for Maya Chen, a brand designer. Minimal, lots of white space. "
        "Projects: Fern Studio rebrand, Halo app identity, Ostra packaging.")
THREADLEAF = ("Threadleaf stationery shop. Products: Notebook $12, Pencil set $8, Desk planner $24. "
              "Add to cart with a cart count. FAQ and contact.")
IRONWORKS = "Ironworks — a strength gym in Pune. Classes, coaches, membership pricing, FAQ, contact."
PROMPTS = {"aster": ASTER, "northwind": NORTHWIND, "saffron": SAFFRON, "maya": MAYA,
           "threadleaf": THREADLEAF, "ironworks": IRONWORKS}


def make_kit(prompt: str) -> KitSite:
    brief = generate_content_brief(prompt)
    return KitSite(prompt, brief, brief["sections"])


# ── Themes ──────────────────────────────────────────────────────────────────

def test_every_theme_meets_contrast_invariants():
    assert len(THEMES) == 12
    for theme in THEMES.values():
        c = theme.colors
        assert contrast(c["ink"], c["bg"]) >= 7, theme.id
        assert contrast(c["muted"], c["bg"]) >= 4.5, theme.id
        assert contrast(c["accent_ink"], c["accent"]) >= 4.5, theme.id


@pytest.mark.parametrize("prompt, business_type, theme_id", [
    (ASTER, "ecommerce", "atelier"),
    (NORTHWIND, "saas", "signal"),
    (SAFFRON, "restaurant", "spice"),
    (MAYA, "portfolio", "gallery"),
])
def test_theme_selection_matches_subject(prompt, business_type, theme_id):
    assert select_theme(prompt, business_type).id == theme_id


def test_mode_words_are_respected():
    assert select_theme("A dark, moody website for a design studio portfolio.", "portfolio").mode == "dark"
    assert select_theme("A light, airy website for a SaaS analytics product.", "saas").mode == "light"
    # A hue phrase is not a mode request.
    assert select_theme("A yoga studio with dark forest green accents.", "general").mode == "light"


def test_selection_is_deterministic_per_prompt():
    prompt = "A website for a local business."
    assert select_theme(prompt, "general").id == select_theme(prompt, "general").id


# ── Imagery ─────────────────────────────────────────────────────────────────

def test_image_planner_matches_subject_and_never_repeats():
    planner = ImagePlanner(ASTER)
    assert planner.topics[0] == "ceramics"
    photos = planner.take(3)
    assert len({p.id for p in photos}) == 3
    assert all(p.url(800).startswith("https://images.unsplash.com/photo-") for p in photos)
    assert all(p.alt for p in photos)


def test_image_planner_is_disabled_or_empty_when_appropriate():
    assert ImagePlanner("A bakery site. No photos, please.").take(2) == []
    assert ImagePlanner("A website for Zorblax.").take(2) == []
    assert ImagePlanner(SAFFRON).topics[0] == "indian_food"


# ── Content parsing and integrity ───────────────────────────────────────────

def test_parse_json_object_repairs_common_failures():
    assert parse_json_object('```json\n{"title": "Hi"}\n```') == {"title": "Hi"}
    assert parse_json_object('<think>hmm</think>{"a": [1, 2,], "b": "x",}') == {"a": [1, 2], "b": "x"}
    truncated = parse_json_object('{"title": "Menu", "items": [{"name": "Dal", "description": "Slow-cooked bla')
    assert truncated is not None and truncated["title"] == "Menu"
    assert parse_json_object("no json here") is None


def test_integrity_removes_leaked_instructions_and_invented_facts():
    prompt = ("Clay & Co — a pottery studio. Warm ivory and dark terracotta. No invented address. "
              "Sections: shop, about.")
    integrity = Integrity(prompt)
    text = ("Warm ivory and dark terracotta. No invented address. "
            "Each bowl is thrown by hand. Bowls are $45 each. We have served 500+ customers.")
    cleaned = integrity.clean_text(text)
    assert "terracotta." not in cleaned and "invented" not in cleaned
    assert "$45" not in cleaned and "500+" not in cleaned
    assert "Each bowl is thrown by hand." in cleaned
    # A product description may still mention a colour.
    assert integrity.clean_text("A mug in a terracotta glaze.") == "A mug in a terracotta glaze."


def test_supplied_products_keep_names_and_prices():
    kit = make_kit(THREADLEAF)
    products_slug = next(s for s in kit.sections if kit.kinds[s] == "products")
    content, _ = kit.accept(products_slug, json.dumps({
        "title": "Paper goods", "intro": "Simple tools for writing.",
        "items": [{"name": "Desk planner", "description": "A week on two pages. Only $99!"},
                  {"name": "Notebook", "description": "Dot grid, lay-flat binding."}],
    }))
    names = [item["name"] for item in content["items"]]
    assert names == ["Notebook", "Pencil set", "Desk planner"]
    prices = {item["name"]: item.get("price") for item in content["items"]}
    assert prices == {"Notebook": "$12", "Pencil set": "$8", "Desk planner": "$24"}
    assert all("$99" not in item["description"] for item in content["items"])


def test_section_kinds():
    assert section_kind("glaze-stories") == "articles"
    assert section_kind("care-guide") == "steps"
    assert section_kind("private-dining") == "split"
    assert section_kind("about") == "story"
    assert section_kind("product-preview") == "preview"
    assert section_kind("membership") == "pricing"
    assert section_kind("coaches") == "team"


# ── Site assembly ───────────────────────────────────────────────────────────

def test_kit_site_facts_and_order():
    aster = make_kit(ASTER)
    assert aster.brand == "Aster & Kiln"
    assert aster.email == "hello@asterkiln.com"
    assert aster.location == "Lisbon"
    assert aster.sections[0] == "header" and aster.sections[1] == "hero" and aster.sections[-1] == "footer"
    assert not aster.is_store and not aster.checkout_available

    store = make_kit(THREADLEAF)
    assert store.is_store
    assert make_kit(SAFFRON).location == "Dehradun"
    assert not make_kit(NORTHWIND).needs_model("header")
    assert make_kit(NORTHWIND).needs_model("hero")


def test_kit_head_and_public_files():
    kit = make_kit(ASTER)
    for slug in kit.sections:
        kit.accept(slug, "")
    head = kit.head_tags()
    for needle in ('name="description"', 'property="og:title"', 'property="og:image"', 'name="theme-color"',
                   'rel="icon"', 'rel="apple-touch-icon"', 'name="twitter:card"'):
        assert needle in head
    files = dict(kit.public_files())
    assert {"favicon.svg", "apple-touch-icon.png", "404.html"} <= set(files)
    assert isinstance(files["apple-touch-icon.png"], bytes)
    assert "fonts.googleapis.com/css2" in kit.font_href()


# ── Rendering through the project's own validators ──────────────────────────

def _realistic_json(kind: str, kit: KitSite, slug: str) -> str:
    supplied = kit.supplied_items(slug)
    names = supplied or ["Small-batch work", "Made to last", "Honest materials", "Careful finishing"]
    leak = "Warm ivory palette with editorial typography."
    data = {
        "hero": {"headline": f"Made slowly, made well at {kit.brand}", "tagline": kit.business_label(),
                 "lede": f"{leak} Thoughtful work from {kit.brand}, shaped by people who care about every detail you will notice.",
                 "primary_cta": "See the work", "secondary_cta": "Get in touch"},
        "features": {"title": "What we do", "intro": "A few things done with care.",
                     "items": [{"title": n, "text": "Built around how people actually use it."} for n in names]},
        "steps": {"title": "How it works", "intro": "A simple path from first idea to finished piece.",
                  "steps": [{"title": n, "text": "One clear step, explained plainly."} for n in names]},
        "story": {"title": "Our story", "paragraphs": ["We started small and stayed curious.", "Every piece is checked by hand."],
                  "highlights": ["Made in small batches", "Repairs welcome", "Plain-spoken advice"]},
        "work": {"title": "Selected work", "intro": "Recent projects.",
                 "items": [{"title": n, "caption": "A careful brief, delivered calmly."} for n in names]},
        "products": {"title": "Shop", "intro": "Everyday objects.",
                     "items": [{"name": n, "description": "Useful, durable and good to hold."} for n in names]},
        "menu": {"title": "Menu", "intro": "Seasonal cooking.",
                 "categories": [{"name": "Small plates", "items": [{"name": "Tomato chaat", "description": "Crisp, sharp, bright."}]},
                                {"name": "Mains", "items": [{"name": "Dal makhani", "description": "Slow-cooked overnight."}]}]},
        "faq": {"title": "Questions", "intro": "Straight answers.",
                "items": [{"q": "How do I start?", "a": "Write to us and tell us what you need."},
                          {"q": "Do you ship?", "a": "Ask us and we will tell you what is possible."},
                          {"q": "Can I visit?", "a": "Yes, get in touch first."}]},
        "articles": {"title": "Notes", "intro": "From the studio.",
                     "items": [{"title": n, "excerpt": "A short note on process.", "tag": "Process"} for n in names[:3]]},
        "pricing": {"title": "Membership", "intro": "Simple options.",
                    "tiers": [{"name": n, "description": "For steady progress.", "features": ["Coaching", "Open gym", "Plans"]} for n in names[:3]]},
        "quotes": {"title": "Kind words", "intro": "From people we work with.", "invite": "Tell us how it went."},
        "team": {"title": "Coaches", "intro": "The people you will train with.",
                 "members": [{"role": "Strength coach", "text": "Patient, precise, encouraging."} for _ in range(3)]},
        "contact": {"title": "Say hello", "text": "Tell us what you have in mind.", "button": "Send message"},
        "cta": {"title": "Stay in touch", "text": "Occasional letters, nothing more.", "button": "Write to us"},
        "preview": {"title": "See it in action", "intro": "A calm view of the work.", "labels": ["Routes", "Loads", "Alerts"],
                    "points": [{"title": "One view", "text": "Everything in one place."}, {"title": "Fewer surprises", "text": "Issues surface early."},
                               {"title": "Shared context", "text": "Everyone sees the same thing."}]},
        "split": {"title": "Private dining", "intro": "Gather around one long table.", "paragraphs": ["A room for your people."],
                  "bullets": ["Set menus", "Quiet room", "Planned with you"]},
        "cart": {"title": "Your cart", "text": "Review your picks."},
    }
    return json.dumps(data.get(kind, {"title": "Section"}))


def _site_dir(name: str) -> Path:
    target = ROOT / "generated_components" / f"_kit_test_{name}_{uuid.uuid4().hex[:6]}"
    target.mkdir(parents=True)
    return target


def _write_site(kit: KitSite, target: Path) -> dict:
    files: dict = {}
    for slug in kit.sections:
        for path, source in kit.render(slug):
            files[path] = source
    names = [Path(p).stem for p in files if p.endswith(".tsx")]
    headers = [n for n in names if n == "Header"]
    footers = [n for n in names if n == "Footer"]
    mains = [n for n in names if n not in headers + footers]
    imports = "\n".join(f"import {{ {n} }} from './src/components/{n}';" for n in names)
    body = "\n      ".join([*(f"<{n} />" for n in headers),
                            "<main id=\"site-main\" tabIndex={-1}>" + "".join(f"<{n} />" for n in mains) + "</main>",
                            *(f"<{n} />" for n in footers)])
    files["App.tsx"] = (f"import React from 'react';\n{imports}\nimport './src/App.css';\n\n"
                        f"export default function App() {{\n  return (\n    <div className=\"site-root\">\n"
                        f"      <a className=\"site-skip-link\" href=\"#site-main\">Skip to content</a>\n      {body}\n    </div>\n  );\n}}\n")
    files["src/App.css"] = kit.base_css()
    for path, source in files.items():
        out = target / path
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(source, encoding="utf-8")
    (target / "css.d.ts").write_text("declare module '*.css';\n", encoding="utf-8")
    return files


def _build(name: str, with_model: bool):
    kit = make_kit(PROMPTS[name])
    for slug in kit.sections:
        text = _realistic_json(kit.kinds[slug], kit, slug) if with_model and kit.needs_model(slug) else ""
        kit.accept(slug, text)
    return kit


@pytest.mark.parametrize("with_model", [True, False], ids=["model", "fallback"])
@pytest.mark.parametrize("name", list(PROMPTS))
def test_rendered_site_passes_project_validators(name, with_model):
    from agent.project_validator import (run_accessibility_check, run_contract_check, run_motion_rules_check,
                                         run_rendering_contract_check, run_static_lint)
    from agent.section_preflight import preflight_section_files

    kit = _build(name, with_model)
    target = _site_dir(name)
    try:
        files = _write_site(kit, target)
        section_files = [(p, s) for p, s in files.items() if p.startswith("src/components/")]
        assert preflight_section_files(section_files) == []
        for check in (run_static_lint, run_contract_check, run_accessibility_check, run_motion_rules_check):
            ok, errors, _ = check(target)
            assert ok, (check.__name__, errors)
        assert run_rendering_contract_check(target, PROMPTS[name]) == []
        rendered = "\n".join(files.values())
        # Leaks and debug text never reach the page.
        for needle in ("palette", "typography", "has no valid React export", 'href="#"', "lorem"):
            assert needle not in rendered.lower(), needle
    finally:
        shutil.rmtree(target, ignore_errors=True)


@pytest.mark.slow
@pytest.mark.parametrize("with_model", [True, False], ids=["model", "fallback"])
@pytest.mark.parametrize("name", list(PROMPTS))
def test_rendered_site_typechecks_strict(name, with_model):
    kit = _build(name, with_model)
    target = _site_dir(name)
    try:
        _write_site(kit, target)
        tsc = ROOT / "node_modules" / "typescript" / "bin" / "tsc"
        result = subprocess.run(
            ["node", str(tsc), "--noEmit", "--strict", "--jsx", "react-jsx", "--target", "ES2022",
             "--lib", "ES2022,DOM,DOM.Iterable", "--module", "ESNext", "--moduleResolution", "bundler",
             "--skipLibCheck", "--esModuleInterop", "App.tsx", "css.d.ts"],
            cwd=target, capture_output=True, text=True, timeout=120)
        assert result.returncode == 0, result.stdout + result.stderr
    finally:
        shutil.rmtree(target, ignore_errors=True)


def test_store_and_menu_and_steps_render_expected_interactions():
    store = _build("threadleaf", True)
    header_tsx = dict(store.render("header"))["src/components/Header.tsx"]
    assert "data-cart-count" in header_tsx and "kit-cart-add" in header_tsx
    products = next(s for s in store.sections if store.kinds[s] == "products")
    assert "Add to cart" in dict(store.render(products))[f"src/components/{store.component(products)}.tsx"]

    menu_site = _build("saffron", True)
    menu_tsx = dict(menu_site.render("menu"))["src/components/Menu.tsx"]
    assert 'role="tablist"' in menu_tsx and "ArrowRight" in menu_tsx

    aster = _build("aster", True)
    care = dict(aster.render("care-guide"))["src/components/CareGuide.tsx"]
    assert 'aria-current' in care and "pathLength" in care
    collection = dict(aster.render("collection"))["src/components/Collection.tsx"]
    assert "Ask about this piece" in collection and "Add to cart" not in collection


def test_text_stays_legible_on_tinted_surfaces():
    for theme in THEMES.values():
        c = theme.colors
        for surface in ("surface", "surface2", "accent_soft"):
            assert contrast(c["ink"], c[surface]) >= 7, (theme.id, surface)
        assert contrast(c["muted"], c["surface"]) >= 4.5, theme.id


def test_generic_stock_never_pairs_with_a_specific_subject():
    assert ImagePlanner(MAYA).topics == ["design"]
    assert ImagePlanner(NORTHWIND).topics == ["tech", "office"]


def test_single_image_sections_get_photos_before_grids():
    kit = make_kit(ASTER)
    assert kit.section_images["care-guide"], "steps visual should not be starved by the collection grid"
    ids = [p.id for photos in kit.section_images.values() for p in photos]
    assert len(ids) == len(set(ids))
