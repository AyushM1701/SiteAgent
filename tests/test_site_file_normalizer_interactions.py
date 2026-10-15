from agent.site_file_normalizer import normalize_site_section_files


PROMPT = "Build an interactive metrics explorer with monthly vs annual pricing."


def normalize(name: str, source: str) -> str:
    path = f"src/components/{name}.tsx"
    return dict(normalize_site_section_files([(path, source)], name.lower(), PROMPT, [name.lower()]))[path]


def test_features_filter_changes_rendered_card_source():
    source = "const [activeTab, setActiveTab] = useState('all'); {features.map((feature) => <h3>{feature.title}</h3>)}"
    fixed = normalize("Features", source)
    assert "features.filter((feature) =>" in fixed
    assert "feature.id === activeTab.toLowerCase()" in fixed
    assert normalize("Features", fixed) == fixed


def test_pricing_toggle_changes_amount_and_removes_dead_cta():
    source = (
        "const [billingType, setBillingType] = useState('monthly'); "
        "<p>${tier.price}</p><button className=\"buy\">Get Started</button>"
    )
    fixed = normalize("Pricing", source)
    assert "billingType === 'annual'" in fixed
    assert "tier.price.replace" in fixed
    assert "Get Started" not in fixed
    assert normalize("Pricing", fixed) == fixed


def test_header_menu_is_named_and_cosmetic_theme_button_removed():
    source = (
        "const [isDark, setIsDark] = useState(true); "
        "const [isMenuOpen, setIsMenuOpen] = useState(false); "
        "<button onClick={() => setIsDark(!isDark)}>{isDark ? 'Moon' : 'Sun'}</button> "
        "<button onClick={() => setIsMenuOpen(!isMenuOpen)}>Menu</button> "
        "<div className={`md:hidden ${isMenuOpen ? 'block' : 'hidden'}`}>Links</div>"
    )
    fixed = normalize("Header", source)
    assert "setIsDark" not in fixed
    assert 'aria-label="Toggle navigation"' in fixed
    assert 'aria-controls="mobile-navigation"' in fixed
    assert 'id="mobile-navigation"' in fixed
    assert normalize("Header", fixed) == fixed


def test_footer_placeholder_navigation_becomes_plain_text():
    fixed = normalize("Footer", '<a href="#site-main" className="hover:text-blue-600">Careers</a>')
    assert fixed == "<span>Careers</span>"
    assert normalize("Footer", '<a href="#">Careers</a>') == fixed
