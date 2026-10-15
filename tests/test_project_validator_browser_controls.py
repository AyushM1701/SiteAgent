"""Regression checks against actual Chromium DOM and computed styles."""

import json

import pytest

from agent.project_validator import (
    _check_brief_interactions,
    _run_runtime_accessibility_eval,
    _visible_interactive_controls,
)


@pytest.fixture
def browser():
    playwright = pytest.importorskip("playwright.sync_api")
    with playwright.sync_playwright() as driver:
        try:
            instance = driver.chromium.launch(headless=True)
        except Exception as exc:
            pytest.skip(f"Chromium unavailable: {exc}")
        yield instance
        instance.close()


def test_shared_control_filter_excludes_skip_hidden_and_decorative(browser):
    page = browser.new_page()
    page.set_content("""
        <a class="site-skip-link" href="#main">Skip to content</a>
        <button style="display:none">Hidden display</button>
        <button style="opacity:0">Hidden opacity</button>
        <div aria-hidden="true"><button>Hidden ancestor</button></div>
        <button role="presentation">Decorative</button>
        <button disabled>Disabled</button>
        <button>Real action</button>
    """)
    controls = _visible_interactive_controls(page.locator("a, button"))
    assert [control.inner_text() for control in controls] == ["Real action"]
    page.close()


def test_brief_pricing_selects_visible_annual_button(browser):
    page = browser.new_page()
    page.set_content("""
        <section id="pricing">
          <button style="display:none">Annual</button>
          <button onclick="document.getElementById('price').textContent='$80'">Annual</button>
          <span id="price">$100</span>
        </section>
    """)
    evidence, failures, tested, required = _check_brief_interactions(
        page, json.dumps({"required_interactions": ["pricing_toggle"]})
    )
    assert (tested, required) == (1, 1)
    assert not failures
    assert evidence[0].passed
    page.close()


def test_browser_contrast_composites_alpha_and_marks_images_unverified(browser, tmp_path):
    page = browser.new_page()
    page.set_content("""
        <main style="background:rgb(0,0,0)">
          <p style="background:rgba(255,255,255,.5);color:rgba(255,255,255,.5)">Alpha text</p>
        </main>
        <p style="background-image:linear-gradient(white,black);color:black">Image text</p>
    """)
    errors, warnings, evidence = _run_runtime_accessibility_eval(page, browser, "about:blank", tmp_path)
    alpha = next(item for item in evidence["contrast_checks"] if item["text"] == "Alpha text")
    image = next(item for item in evidence["contrast_checks"] if item["text"] == "Image text")
    assert alpha["verified"] is True
    assert alpha["ratio"] == pytest.approx(2.17, abs=0.04)
    assert image["verified"] is False and image["ratio"] is None
    assert any("unverified" in warning and "Image text" in warning for warning in warnings)
    assert not any("Low computed text contrast" in error and "Image text" in error for error in errors)
    page.close()


def test_focus_and_target_checks_share_control_filter(browser, tmp_path):
    page = browser.new_page()
    page.set_content("""
        <a href="#main" class="site-skip-link">Skip to content</a>
        <button style="opacity:0">Invisible button</button>
        <button aria-hidden="true">Decorative button</button>
        <button style="width:30px;height:30px">Real button</button>
    """)
    _, _, evidence = _run_runtime_accessibility_eval(page, browser, "about:blank", tmp_path)
    assert [item["text"] for item in evidence["focus_checks"]] == ["Real button"]
    assert [item["text"] for item in evidence["target_size_checks"]] == ["Real button"]
    page.close()
