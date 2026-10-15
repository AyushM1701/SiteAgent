"""Run with the demo served on port 5182; verifies real browser behavior."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

OUTPUT = Path(__file__).resolve().parents[1] / "examples/premium-product-lab"


def verify():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto("http://127.0.0.1:5182", wait_until="networkidle")
        page.get_by_role("button", name="Pause motion").click()
        page.screenshot(path=str(OUTPUT / "desktop.png"), full_page=True)
        page.get_by_role("button", name="Change view").click()
        assert page.locator(".premium-scene").get_attribute("data-view") == "1"
        page.get_by_role("tab", name="Explore").click()
        assert "Explore with intention." in page.get_by_role("tabpanel").inner_text()
        page.get_by_role("tab", name="Explore").press("ArrowRight")
        assert page.get_by_role("tab", name="Refine").get_attribute("aria-selected") == "true"
        page.get_by_label("Try the local interaction demo").fill("test@example.com")
        page.get_by_role("button", name="Try it").click()
        assert "not sent or stored" in page.get_by_role("status").inner_text()
        page.set_viewport_size({"width": 375, "height": 812})
        page.reload(wait_until="networkidle")
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        page.emulate_media(reduced_motion="reduce")
        assert page.locator(".premium-scene__cube").evaluate("el => getComputedStyle(el).animationName") == "none"
        page.screenshot(path=str(OUTPUT / "mobile.png"), full_page=True)
        assert not errors, errors
        browser.close()
    result = {"desktop_width": 1440, "mobile_width": 375, "horizontal_overflow": False,
              "view_control": True, "pause_control": True, "keyboard_tabs": True,
              "form_demo": True, "reduced_motion": True, "page_errors": errors}
    (OUTPUT / "verification.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("Premium demo browser checks passed")


if __name__ == "__main__":
    verify()
