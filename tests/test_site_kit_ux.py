"""§8 UI/UX baseline and §9 motion system, as built into the design kit.

Browser behaviour is verified in the workbench self-check (§11); these tests pin
the source-level contracts so a refactor cannot silently drop them.
"""
import re

from agent.site_brief import generate_content_brief
from agent.site_kit import KitSite

ASTER = ("Aster & Kiln — handmade ceramics studio in Lisbon. Warm editorial photography, clay textures. "
         "Sections: collection, glaze stories, care guide, studio notes. Email hello@asterkiln.com. No online checkout.")
NORTHWIND = ("Northwind — a B2B analytics SaaS for logistics teams. Dark, technical look. "
             "Include a product preview and FAQ. Do not show pricing.")
SAFFRON = ("Saffron Table — modern Indian restaurant in Dehradun. Menu, about the chef, private dining. "
           "We do not take online reservations.")


def site(prompt):
    brief = generate_content_brief(prompt)
    kit = KitSite(prompt, brief, brief["sections"])
    files = {}
    for slug in kit.sections:
        kit.accept(slug, "")
        files.update(dict(kit.render(slug)))
    return kit, files


def test_spacing_type_and_colour_tokens():
    kit, _ = site(ASTER)
    css = kit.base_css()
    assert all(f"--k-space-{i}:" in css for i in range(1, 13))
    assert "--k-tap: 44px" in css and "line-height: 1.6" in css and "max-width: 65ch" in css
    assert css.count("--k-font-") >= 2  # two families only
    assert "#FFFFFF;" not in css.split("--k-bg:")[1].split(";")[0] and "#000000" not in css.split("--k-bg:")[1].split(";")[0]


def test_header_wayfinding_tucking_drawer_and_cta():
    kit, files = site(ASTER)
    header = files["src/components/Header.tsx"]
    assert "aria-current={active === link.id ? 'location' : undefined}" in header
    assert "is-tucked" in header and "y > 120" in header
    assert 'aria-controls="site-menu"' in header and "inert={!open}" in header
    assert "document.body.style.overflow = 'hidden'" in header and "'Escape'" in header
    assert "toggleRef.current?.focus()" in header
    # The drawer renders outside <header>: backdrop-filter would trap a fixed child.
    assert header.index("</header>") < header.index('id="site-menu"')
    assert len(kit._header_content()["links"]) <= 6


def test_footer_safety_net():
    _, files = site(ASTER)
    footer = files["src/components/Footer.tsx"]
    for needle in ("Explore", "Contact", "Privacy", "Back to top", "aria-controls=\"footer-privacy\"", "getFullYear"):
        assert needle in footer


def test_interaction_states_and_forms():
    kit, files = site(SAFFRON)
    css = kit.base_css()
    assert ":active { transform: scale(0.98); }" in css
    assert '[aria-busy="true"]' in css and ":focus-visible" in css
    contact = files["src/components/Contact.tsx"]
    assert "aria-invalid" in contact and "aria-describedby" in contact and "Preparing…" in contact
    assert contact.count("required") >= 3
    for path, source in files.items():
        if path.endswith(".css"):
            for hover in re.findall(r"([^{}]+):hover[^{]*\{", source):
                assert ":focus-visible" in source, path


def test_media_reserves_space_and_prioritises_the_hero():
    kit, files = site(SAFFRON)
    hero = files["src/components/Hero.tsx"]
    assert "fetchPriority={priority ? 'high' : 'auto'}" in hero and "width={img.w} height={img.h}" in hero
    assert 'rel="preload" as="image"' in kit.head_tags()
    assert all("aspect-ratio" in source for path, source in files.items()
               if path.endswith(".css") and ("-media" in source and "Hero" not in path and "Header" not in path
                                             and "Footer" not in path and "Contact" not in path))


def test_motion_system_is_native_once_and_reduced_motion_safe():
    kit, files = site(ASTER)
    css = kit.base_css()
    assert '[data-motion="scroll-reveal"].is-visible' in css and ".k-stagger > :nth-child(2)" in css
    assert "@supports (animation-timeline: view())" in css and "animation-timeline: scroll(root)" in css
    assert "(hover: hover) and (min-width: 900px)" in css
    reduce_block = css[css.index("@media (prefers-reduced-motion: reduce)"):]
    assert "opacity: 1 !important" in reduce_block and "scroll-behavior: auto !important" in reduce_block
    hero = files["src/components/Hero.tsx"]
    assert 'data-motion="text-in"' in hero and "useMagnet" in hero
    reveal_files = [s for p, s in files.items() if 'data-motion="scroll-reveal"' in s]
    assert len(reveal_files) == 1  # one reveal section, not fade-everything
    assert "observer.unobserve(entry.target)" in reveal_files[0] and "observer.disconnect()" in reveal_files[0]


def test_shader_backdrop_caps_frame_rate_and_pauses():
    _, files = site(NORTHWIND)
    hero = files["src/components/Hero.tsx"]
    assert "<ShaderBackdrop />" in hero and "Illustrative interface; not live data" in hero
    assert "window.setTimeout(loop, 33)" in hero and "requestAnimationFrame" not in hero
    assert "IntersectionObserver" in hero and "visibilitychange" in hero and "WEBGL_lose_context" in hero
    assert "Math.min(window.devicePixelRatio || 1, 1.5)" in hero


def test_menu_tabs_use_view_transitions_and_keyboard():
    _, files = site(SAFFRON)
    menu = files["src/components/Menu.tsx"]
    # Fallback menu has no categories, so build one with content.
    brief = generate_content_brief(SAFFRON)
    kit = KitSite(SAFFRON, brief, brief["sections"])
    kit.accept("menu", '{"title": "Menu", "categories": [{"name": "Starters", "items": [{"name": "Samosa"}]},'
                       ' {"name": "Mains", "items": [{"name": "Dal"}]}]}')
    menu = dict(kit.render("menu"))["src/components/Menu.tsx"]
    assert "startViewTransition" in menu and "flushSync" in menu
    for key in ("ArrowRight", "ArrowLeft", "Home", "End"):
        assert key in menu


def test_footer_wordmark_is_a_44px_target():
    kit, files = site(ASTER)
    css = files["src/components/Footer.css"]
    rule = css[css.index(".k-footer .k-footer__wordmark {"):]
    rule = rule[:rule.index("}")]
    assert "min-height: var(--k-tap)" in rule
