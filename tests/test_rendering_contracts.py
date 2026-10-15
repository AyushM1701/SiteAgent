import re

from agent.style_ingest import StyleSpec, build_site_root_css, parse_css_tokens, wcag_contrast_ratio


def token(css, name):
    return dict(re.findall(r'(--[\w-]+)\s*:\s*([^;]+);', css))[name]


def test_explicit_style_tokens_survive_default_collisions():
    spec = parse_css_tokens(':root { --color-obsidian: #090d16; --color-paper: #ffffff; --text-display: 225px; --font-heading: Georgia, serif; --radius-buttons: 0; }')
    css, _ = build_site_root_css(style_spec=spec)
    for name, expected in {'--color-paper': '#ffffff', '--text-display': '225px', '--font-heading': 'Georgia, serif', '--radius-buttons': '0'}.items():
        assert token(css, name) == expected
        assert len(re.findall(re.escape(name) + r'\s*:', css)) == 1


def test_structured_tokens_override_defaults_without_raw_css():
    spec = StyleSpec(name='Custom', colors={'--color-paper': '#fff'}, motion_tokens={'--duration-fast': '90ms'})
    css, _ = build_site_root_css(style_spec=spec)
    assert token(css, '--color-paper') == '#fff'
    assert token(css, '--duration-fast') == '90ms'


def test_generated_on_accent_is_chosen_against_accent_not_canvas():
    css, _ = build_site_root_css({'primary_color': '#090d16', 'accent_color': '#a02d25'})
    assert wcag_contrast_ratio(token(css, '--on-accent'), '#a02d25') >= 4.5


def test_reduced_scroll_override_survives_later_normal_rule():
    css, _ = build_site_root_css()
    assert 'scroll-behavior: auto !important' in css


def test_site_root_does_not_mask_control_overflow():
    css, _ = build_site_root_css()
    root = re.search(r'\.site-root\s*\{([^}]+)', css).group(1)
    assert 'overflow' not in root


def diagnostics(files, prompt=''):
    from agent.site_quality import collect_site_rendering_diagnostics
    return collect_site_rendering_diagnostics(files, prompt)


def test_identical_cta_and_hover_colors_are_diagnosed_with_variables():
    files = {'Hero.tsx': '<a className="cta" href="#shop">Shop</a>', 'Hero.css': ':root { --accent: #a02d25; } .cta {color: var(--accent); background: var(--accent);} .cta:hover {color:#fff; background:#fff;}'}
    errors = diagnostics(files)
    assert sum('[TEXT CONTRAST]' in error for error in errors) == 2
    assert any('.cta:hover' in error for error in errors)


def test_navbar_display_heading_is_diagnosed_contextually():
    files = {'Navbar.tsx': '<header><nav><h1 className="brand">Brand</h1></nav></header>', 'Navbar.css': ':root {--text-display: 225px;} .brand {font-size:var(--text-display);}'}
    errors = diagnostics(files)
    assert any('[NAV TYPOGRAPHY]' in error for error in errors)
    assert not any('[NAV TYPOGRAPHY]' in error for error in diagnostics({'Hero.tsx': '<section><h1 className="brand">Brand</h1></section>', 'Hero.css': files['Navbar.css']}))


def test_hidden_overflow_does_not_count_as_mobile_layout_evidence():
    errors = diagnostics({'App.css': '.site-root {overflow-x:hidden;}', 'Navbar.tsx': '<nav><button>Cart</button></nav>'})
    assert any('[CONTROL CLIPPING]' in error for error in errors)


def test_motion_and_3d_names_do_not_satisfy_requested_implementation():
    errors = diagnostics({'Hero.tsx': '<section className="parallax reveal"><button>Flat view</button></section>', 'Hero.css': '.parallax { transform: translate3d(0,0,0); }'}, 'Text reveal on scroll, scroll parallax, CSS 3D with a flat-view toggle')
    for label in ('[SCROLL PARALLAX]', '[SCROLL REVEAL]', '[3D COMPOSITION]', '[FLAT VIEW]'):
        assert any(label in error for error in errors)


def test_missing_anchor_and_late_smooth_scroll_are_diagnosed():
    files = {'App.tsx': '<main id="hero"><a href="#shop">Shop</a></main>', 'App.css': '@media (prefers-reduced-motion: reduce) {html {scroll-behavior:auto;}} html {scroll-behavior:smooth;}'}
    errors = diagnostics(files)
    assert any('[ANCHOR TARGET]' in error and '#shop' in error for error in errors)
    assert any('[REDUCED MOTION]' in error for error in errors)


def test_supported_source_evidence_is_not_reported_as_missing():
    files = {'Hero.tsx': '<main id="hero"><a href="#hero">Home</a><button onClick={() => setFlat(!flat)}>Flat view</button></main> const observer = new IntersectionObserver(cb); window.addEventListener("scroll", () => node.style.transform = `translateY(${window.scrollY * .2}px)`);', 'Hero.css': '.scene {perspective:800px;} .object {transform-style:preserve-3d; transform:rotateY(30deg);} .reveal {opacity:0; transition:opacity 400ms;} .reveal.visible {opacity:1;}'}
    assert diagnostics(files, 'Scroll parallax, scroll reveal and CSS 3D with flat view') == []


def test_home_alias_repairs_only_when_hero_target_exists():
    from agent.site_file_normalizer import remove_unresolved_section_links
    files = {'Hero.tsx': '<section id="hero">Hero</section>', 'Footer.tsx': '<footer><a href="#home">Home</a><a href="#shop">Shop</a></footer>'}
    changed = remove_unresolved_section_links(files)
    assert '<a href="#hero">Home</a>' in changed['Footer.tsx']
    assert '<span>Shop</span>' in changed['Footer.tsx']
    assert remove_unresolved_section_links({**files, **changed}) == {}
    files['Home.tsx'] = '<section id="home">Home</section>'
    assert '<a href="#home">Home</a>' in remove_unresolved_section_links(files)['Footer.tsx']


def test_normal_text_requires_aa_while_large_text_uses_large_text_threshold():
    files = {'Hero.css': '.copy { color:rgb(119,119,119); background:rgb(255,255,255); } .large { color:#777; background:#fff; font-size:32px; }'}
    errors = diagnostics(files)
    assert any('[TEXT CONTRAST]' in error and '.copy' in error for error in errors)
    assert not any('[TEXT CONTRAST]' in error and '.large' in error for error in errors)


def test_hover_foreground_is_checked_against_base_background():
    errors = diagnostics({'Hero.css': '.cta {color:#fff; background:#a02d25;} .cta:hover {color:#a02d25;}'})
    assert any('[TEXT CONTRAST]' in error and '.cta:hover' in error for error in errors)
