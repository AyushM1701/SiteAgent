import pytest

from agent.site_brief import generate_content_brief, brief_to_xml, extract_supplied_products, _ground_provider_brief
from agent.site_requirements import build_requirement_manifest
from agent.stock_photos import _resolve_curated_stock_photo, fetch_single_image, resolve_site_images, build_asset_manifest


@pytest.mark.parametrize('palette', ['warm ivory, ink and terracotta', 'cream, navy and cobalt', 'white, charcoal and sage'])
def test_auto_explicit_palette_precedes_editorial_keyword(palette):
    brief = generate_content_brief(f'Build a shop. Use {palette}, bold editorial typography.', provider='heuristic', style_preset='Auto')
    assert not brief.get('style_spec')
    assert brief['requested_palette']
    assert 'Monochrome' not in brief_to_xml(brief)
    if 'ink' in palette:
        assert brief['primary_color'] == '#1c1917'
        assert brief['accent_color'] == '#b5654b'


def test_explicit_style_metadata_remains_authoritative():
    brief = generate_content_brief('Build a shop. Use ivory and terracotta editorial typography.', provider='heuristic', style_preset='editorial')
    assert brief['style_spec']
    assert brief['style_preset'] == 'editorial'


def test_provider_cannot_replace_user_palette():
    brief = _ground_provider_brief('Build a studio website. Use cream, navy and cobalt.', {'primary_color': '#000000', 'accent_color': '#ffffff'}, None)
    assert brief['primary_color'] == '#14213d'
    assert brief['accent_color'] == '#2454a6'


def test_provider_uses_the_same_subject_media_contract():
    brief = _ground_provider_brief('Build a ceramics shop. Use relevant imagery or ceramic illustrations.',
                                  {'business_name': 'Invented', 'images': {'hero': {'url': 'off-topic'}}}, None)
    assert brief['images']['hero'] is None
    assert brief['media_decision'] == 'illustration'


@pytest.mark.parametrize('clause, expected', [
    ('Products: Orbit Mug $28 and Arc Vase $64.', [('Orbit Mug', '$28'), ('Arc Vase', '$64')]),
    ('Catalog: Field Kit at $19.95, Trail Lamp for €34.50.', [('Field Kit', '$19.95'), ('Trail Lamp', '€34.50')]),
    ('Items: Studio Print — £45; Small Frame: £12.', [('Studio Print', '£45'), ('Small Frame', '£12')]),
])
def test_supplied_product_prices(clause, expected):
    assert [(p['name'], p['price']) for p in extract_supplied_products(clause)] == expected


@pytest.mark.parametrize('subject', ['ceramics pottery mugs', 'birdwatching binoculars', 'artisan violin instruments', 'wood violin instruments', 'pilot helmet shop'])
def test_uncovered_subject_does_not_get_generic_photo(subject):
    assert _resolve_curated_stock_photo(subject, 'ecommerce') is None
    assert fetch_single_image(subject, 'ecommerce') is None
    resolved = resolve_site_images({'business_type': 'ecommerce', 'business_name': subject, 'source_prompt': f'Use relevant imagery or drawn illustrations for {subject}'})
    assert resolved['images']['hero'] is None
    assert resolved['media_decision'] == 'illustration'
    assert build_asset_manifest(resolved)['media_decision'] == 'illustration'


def test_exhausted_relevant_photos_do_not_fall_through_to_other_domains():
    first = _resolve_curated_stock_photo('travel landscape nature', 'travel')
    assert first
    assert _resolve_curated_stock_photo('travel landscape nature', 'travel', {first['url']}) is None


def test_custom_token_metadata_remains_authoritative():
    brief = generate_content_brief('A ceramics shop with ivory and ink editorial style.', provider='heuristic',
                                   style_tokens=':root { --color-primary: #123456; --color-accent: #fedcba; }')
    assert brief['style_spec'].source == 'custom'
    assert brief['primary_color'] == '#123456'


def test_requirement_contract_retains_facts_and_observable_behavior():
    prompt = ('Build a ceramics shop. Products: Orbit Mug $28 and Arc Vase $64. '
              'Add to cart updates a visible count with repeated clicks. Include scrolling text reveals, '
              'a parallax hero illustration and visible CSS 3D composition with working flat-view toggle. Respect reduced motion.')
    brief = generate_content_brief(prompt, provider='heuristic')
    manifest = brief['requirement_manifest']
    assert {'Orbit Mug', '$28', 'Arc Vase', '$64'} <= set(manifest['exact_facts'])
    assert 'flat_view_toggle' in manifest['interactions']
    assert manifest['three_d_constraints'][0]['engine'] == 'css'
    assert any(c['state'] == 'flat_view' for c in manifest['cross_section_contracts'])
    assert any(c['type'] == 'text_reveal' and c['requested_trigger'] == 'scroll' for c in manifest['motion_constraints'])
    assert any(c['type'] == 'parallax' and c['observable_behavior'] for c in manifest['motion_constraints'])
    assert 'flat_view_toggle' in brief_to_xml(brief)
    assert 'engine="css"' in brief_to_xml(brief)


def test_manifest_extracts_user_facts_even_with_partial_brief():
    manifest = build_requirement_manifest('Products: Timber Desk $210 and Linen Chair $95. Include a WebGL 3D scene.', {'sections': ['hero']})
    assert {'Timber Desk', '$210', 'Linen Chair', '$95'} <= set(manifest['exact_facts'])
    assert manifest['three_d_constraints'][0]['engine'] == 'webgl'


def test_arbitrary_explicit_section_list_survives_manifest():
    brief = generate_content_brief('Build an instrument shop. Sections: Navbar, Hero, Shop, Repairs, Footer.', provider='heuristic')
    assert brief['requirement_manifest']['explicit_sections'] == brief['sections']
