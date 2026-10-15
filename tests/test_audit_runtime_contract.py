import json
import pytest
from playwright.sync_api import sync_playwright
from agent.project_validator import _check_brief_interactions, check_mobile_control_bounds
from agent.project_validator import check_broken_rendered_images


@pytest.fixture
def page():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(reduced_motion='reduce')
        yield page
        browser.close()


def test_failed_product_image_is_a_runtime_failure(page):
    page.set_content('<img alt="Orbit Mug" width="300" height="400" src="http://127.0.0.1:1/missing-pottery.png">')
    page.wait_for_function('document.images[0].complete')
    assert 'Orbit Mug' in check_broken_rendered_images(page)[0]


def test_clipped_nav_is_detected_even_when_document_overflow_is_hidden(page):
    page.set_viewport_size({'width':390,'height':844})
    page.set_content('<style>html{overflow-x:hidden}nav{width:1100px}a{margin-left:800px}</style><nav><a href="#shop">Shop</a></nav>')
    assert check_mobile_control_bounds(page)


def test_flat_toggle_label_change_is_insufficient(page):
    page.set_content('<button onclick="this.textContent=\'3D view\'">Flat view</button><div style="perspective:400px"><div style="transform-style:preserve-3d"><span style="display:block;transform:translateZ(30px)">Ceramic</span></div></div>')
    brief = {'requirement_manifest': {'interactions':['flat_view_toggle']}}
    evidence, errors, tested, required = _check_brief_interactions(page,json.dumps(brief))
    assert required == 1 and errors


def test_cart_all_products_and_repeated_clicks_are_required(page):
    page.set_content('<header><span data-cart-count>0</span></header><button onclick="document.querySelector(\'[data-cart-count]\').textContent=1">Add to cart</button><button>Add to cart</button>')
    brief = {'requirement_manifest': {'interactions':['cart_state'], 'interaction_constraints':[
        {'type':'cart_state','repeated_clicks_required':True,'products':[{'name':'Mug'},{'name':'Vase'}]}]}}
    evidence, errors, tested, required = _check_brief_interactions(page,json.dumps(brief))
    assert required == 1 and errors
