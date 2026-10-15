from agent.site_file_normalizer import is_substantive_fallback_rewrite, normalize_site_section_files, remove_unresolved_section_links


def test_fallback_marker_flip_is_not_a_repair():
    before = '<header data-fallback="true"><nav>Home</nav></header>'
    marker_only = before.replace('"true"', '"false"')
    substantive = '<header><nav><a href="#hero">Home</a><button>Menu</button></nav></header>'
    assert not is_substantive_fallback_rewrite(before, marker_only)
    assert is_substantive_fallback_rewrite(before, substantive)


def test_normalizer_removes_pasted_tailwind_class_list_from_css_rule():
    files = [
        ("src/components/Hero.css", ".hero {\n  color: white;\n  px-4 py-2 border text-white\n}\n"),
    ]
    normalized = dict(normalize_site_section_files(files, "hero"))
    css = normalized["src/components/Hero.css"]
    assert "color: white;" in css
    assert "px-4 py-2" not in css


def test_normalizer_scopes_shared_inner_and_replaces_empty_anchor():
    files = [
        ("src/components/Footer.tsx", '<footer className="section__footer"><a href="#">Top</a></footer>'),
        ("src/components/Footer.css", ".section__inner { display: flex; }"),
    ]
    normalized = dict(normalize_site_section_files(files, "footer"))
    assert 'id="footer"' in normalized["src/components/Footer.tsx"]
    assert 'href="#site-main"' in normalized["src/components/Footer.tsx"]
    assert ".section__footer .section__inner {" in normalized["src/components/Footer.css"]


def test_normalizer_replaces_undeclared_link_with_native_anchor():
    files = [
        ("src/components/Header.tsx", 'export default function Header() { return <header><Link to="#">Home</Link></header>; }'),
    ]
    normalized = dict(normalize_site_section_files(files, "header"))["src/components/Header.tsx"]
    assert '<a href="#site-main">Home</a>' in normalized
    assert "<Link" not in normalized


def test_normalizer_closes_single_unfinished_button_icon_conditional():
    files = [
        ("src/components/Header.tsx", (
            "export default function Header() { return <header><button>\n"
            "{isDark ? <svg><path d=\"M0 0\" /></svg> : <svg><path d=\"M1 1\" /></svg></button>\n"
            "</header>; }"
        )),
    ]
    normalized = dict(normalize_site_section_files(files, "header"))["src/components/Header.tsx"]
    assert "</svg>}</button>" in normalized


def test_normalizer_removes_unrequested_contact_details_and_repairs_footer_anchor():
    files = [
        ("src/components/Footer.tsx", (
            '<footer><p>sales@invented.test | +1 (800) 555-0199</p>'
            '<a href="#contact">Contact</a></footer>'
        )),
    ]
    normalized = dict(normalize_site_section_files(
        files, "footer", original_prompt="Build a product site", known_sections=["hero", "footer"]
    ))["src/components/Footer.tsx"]
    assert "sales@invented.test" not in normalized
    assert "555-0199" not in normalized
    assert "Contact details are available upon request." in normalized
    assert 'href="#footer"' in normalized


def test_generated_section_gets_matching_css_import_and_anchor_once():
    files = [
        ("src/components/Hero.tsx", "export default function Hero() { return <section className=\"hero\" />; }"),
        ("src/components/Hero.css", ".hero { color: white; }"),
    ]
    once = normalize_site_section_files(files, "hero")
    twice = normalize_site_section_files(once, "hero")
    assert once == twice
    assert "import './Hero.css';" in once[0][1]
    assert '<section id="hero"' in once[0][1]


def test_missing_react_hook_import_is_added():
    files = [("src/components/Pricing.tsx", "export default function Pricing() { const [x, setX] = useState(false); return <section />; }")]
    result = normalize_site_section_files(files, "pricing")
    assert "import { useState } from 'react';" in result[0][1]


def test_contact_without_backend_cannot_claim_email_was_sent():
    files = [("src/components/Contact.tsx", (
        "export default function Contact() { return <section>"
        "<button onClick={() => alert('Email sent to invented@studio.test')}>Send</button>"
        "</section>; }"
    ))]
    result = dict(normalize_site_section_files(files, "contact", original_prompt="Build a contact form"))
    assert "Email sent" not in result["src/components/Contact.tsx"]
    assert "not connected to a service" in result["src/components/Contact.tsx"]


def test_gallery_string_selection_and_tag_callback_are_typed():
    files = [("src/components/CaseStudies.tsx", (
        "import React from 'react'; export default function CaseStudies(){ "
        "const [activeProject, setActiveProject] = React.useState(null); "
        "const open = (id: string) => setActiveProject(id); "
        "return <section>{project.tags.map((tag) => <span>{tag}</span>)}</section>; }"
    ))]
    source = dict(normalize_site_section_files(files, "case-studies"))["src/components/CaseStudies.tsx"]
    assert "React.useState<string | null>(null)" in source
    assert ".tags.map((tag: string) =>" in source


def test_separate_gallery_and_lightbox_share_open_event():
    gallery = (
        "export default function CaseStudies(){ const projects=[{id:'one',title:'One'}]; "
        "const handleProjectClick=(id:string)=>{document.querySelector('.lightbox')?.classList.add('active');}; "
        "return <section />; }"
    )
    lightbox = (
        "import React from 'react'; export default function Lightbox({ project }: { project: any }) { "
        "const [active,setActive]=React.useState(false); return ("
        "<section><button onClick={() => setActive(false)}>Close</button>{project.title}</section>); }"
    )
    gallery_out = dict(normalize_site_section_files([("src/components/CaseStudies.tsx", gallery)], "case-studies"))
    lightbox_out = dict(normalize_site_section_files([("src/components/Lightbox.tsx", lightbox)], "lightbox"))
    assert "site-open-lightbox" in gallery_out["src/components/CaseStudies.tsx"]
    source = lightbox_out["src/components/Lightbox.tsx"]
    assert "addEventListener('site-open-lightbox'" in source
    assert "if (!project) return null" in source
    assert "setProject(null)" in source


def test_single_page_navigation_routes_to_generated_sections():
    files = [("src/components/Header.tsx", (
        'export default function Header(){ return <header><a href="/">Home</a>'
        '<a href="/products">Products</a><a href="/cart">Cart</a></header>; }'
    ))]
    source = dict(normalize_site_section_files(
        files, "header", known_sections=["header", "hero", "products", "cart", "footer"]
    ))["src/components/Header.tsx"]
    assert 'href="#site-main"' in source
    assert 'href="#products"' in source
    assert 'href="#cart"' in source


def test_shop_hero_inert_button_becomes_product_anchor():
    files = [("src/components/Hero.tsx", (
        'export default function Hero(){ return <section><button className="cta">\n Shop Now\n</button></section>; }'
    ))]
    source = dict(normalize_site_section_files(
        files, "hero", known_sections=["hero", "products", "cart"]
    ))["src/components/Hero.tsx"]
    assert '<a href="#products" className="cta">Shop Now</a>' in source


def test_project_link_cleanup_preserves_real_targets_and_removes_missing_ones():
    files = {
        "src/components/Products.tsx": '<section id="products">Products</section>',
        "src/components/Footer.tsx": (
            '<footer id="footer"><a href="#products">Products</a>'
            '<a href="#faq" className="footer-link">FAQ</a>'
            '<a href="#site-main">Top</a></footer>'
        ),
    }
    changed = remove_unresolved_section_links(files)
    footer = changed["src/components/Footer.tsx"]
    assert '<a href="#products">Products</a>' in footer
    assert '<span className="footer-link">FAQ</span>' in footer
    assert '<a href="#site-main">Top</a>' in footer
    assert remove_unresolved_section_links({**files, **changed}) == {}
