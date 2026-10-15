from agent.site_prompt import section_behavior_contract


def test_shop_and_nav_share_a_sandbox_safe_cart_protocol():
    prompt = 'Shop with Add to cart and repeated clicks'
    assert 'site-cart-add' in section_behavior_contract('shop', prompt)
    nav = section_behavior_contract('navbar', prompt)
    assert 'site-cart-add' in nav and 'data-cart-count' in nav
    assert 'localStorage' in nav


def test_visual_features_are_assigned_to_hero_without_saas_assumptions():
    hero = section_behavior_contract('hero', 'Ceramics, parallax, scrolling text reveals, CSS 3D with flat-view toggle')
    assert 'IntersectionObserver' in hero and 'perspective' in hero and 'scroll' in hero
    assert 'flat-view' in hero
    assert 'pricing tiers' not in hero
