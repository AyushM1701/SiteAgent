import pytest
from playwright.sync_api import sync_playwright
from scripts.native_site_gate import verify_interactions


@pytest.fixture
def page():
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        page=browser.new_page()
        yield page
        browser.close()


def test_cart_probe_checks_both_products_and_initial_count(page):
    page.set_content('<section id="cart">Cart item count: <span id="count">0</span></section><button onclick="document.querySelector(\'#count\').textContent=Number(document.querySelector(\'#count\').textContent)+1">Add to cart</button><button>Add to cart</button>')
    assert verify_interactions(page,'store')['passed'] is False


def test_cart_probe_accepts_real_count_transitions(page):
    handler="document.querySelector('#count').textContent=Number(document.querySelector('#count').textContent)+1"
    page.set_content(f'<section id="cart">Cart item count: <span id="count">0</span></section><button onclick="{handler}">Add to cart</button><button onclick="{handler}">Add to cart</button>')
    result=verify_interactions(page,'store')
    assert result['passed'] is True
    assert result['counts']==[0,1,2,3]


def test_checkbox_must_have_exact_name_and_toggle_both_ways(page):
    page.set_content('<label><input type="checkbox"/>Record the habitat</label>')
    result=verify_interactions(page,'unfamiliar')
    assert result['passed'] is True
    assert result['states']==[False,True,False]
    page.set_content('<label for="missing">Record the habitat</label><label><input type="checkbox"/>Forest</label>')
    assert verify_interactions(page,'unfamiliar')['passed'] is False
