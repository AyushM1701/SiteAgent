from agent.site_brief import _build_heuristic_brief, parse_section_spec, brief_to_xml
from agent.style_ingest import check_css_syntactic_completeness

PROMPT = ('Generate a complete single-page React + TypeScript + CSS website for a SaaS startup called "NexaFlow" '
          '— an AI workflow automation platform. Include: a sticky nav with a CTA, a hero section with animated gradient text, '
          'a features grid (6 cards), a pricing section with a monthly/annual toggle, and a footer. '
          'Use a dark color scheme with cyan/violet accents, Inter font, and glassmorphism cards.')


def test_count_and_section_boundaries():
    brief = _build_heuristic_brief(PROMPT)
    assert brief['sections'] == ['header', 'hero', 'features', 'pricing', 'footer']
    assert brief['section_plans']['features']['target_count'] == 6
    assert brief['section_plans']['pricing']['target_count'] == 3
    assert '6 cards' not in [x['title'] for x in brief['features']]
    assert '6 cards' not in [x['name'] for x in brief['pricing_tiers']]
    assert brief['font_heading'] == brief['font_body'] == 'Inter'
    assert not brief['contact'] and not brief['testimonials']
    assert 'illustrative demo data' in brief_to_xml(brief)


def test_named_features_stay_in_their_section():
    prompt = 'Include: a hero, features (Capture, Connect, Publish), pricing (Basic, Team), and a footer.'
    assert parse_section_spec('features', prompt)['parsed_items'] == ['Capture', 'Connect', 'Publish']
    assert parse_section_spec('pricing', prompt)['parsed_items'] == ['Basic', 'Team']


def test_real_css_parser_rejects_balanced_but_truncated_declaration():
    assert not check_css_syntactic_completeness('.price { color: red; margin-right }')[0]
    assert check_css_syntactic_completeness('.price::after { content: "}"; margin-right: 0 }')[0]


def test_local_controls_do_not_choose_whole_site_layout():
    from agent.site_brief import detect_prompt_layout_signal, select_layout_archetype
    assert detect_prompt_layout_signal(PROMPT) is None
    assert detect_prompt_layout_signal(PROMPT + ' Layout: editorial') == 'editorial'
    assert detect_prompt_layout_signal('Editorial website. Include: hero, pricing with monthly/annual toggle, footer.') == 'editorial'
    for name in ('Bakery', 'Studio', 'Orbit', 'Signal', 'Folio'):
        assert select_layout_archetype('Build a website', business_name=name) not in {'tabs', 'timeline'}
