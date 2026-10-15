"""Local browser smoke check for the P1 workbench interactions."""

from playwright.sync_api import sync_playwright


def main() -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            mobile = browser.new_page(viewport={"width": 390, "height": 844})
            mobile.goto("http://127.0.0.1:5000", wait_until="networkidle")
            assert mobile.locator("aside").count() == 0
            assert mobile.locator("#composer-mode-site-btn").get_attribute("aria-pressed") == "true"
            mobile.locator("#topbar-sidebar-toggle").click()
            assert mobile.locator("aside").is_visible()
            mobile.keyboard.press("Escape")
            assert mobile.locator("aside").count() == 0
            assert mobile.evaluate("document.documentElement.scrollWidth <= innerWidth + 2")
            mobile.close()

            desktop = browser.new_page(viewport={"width": 1280, "height": 800})
            desktop.route("**/api/projects", lambda route: route.fulfill(
                status=200, content_type="application/json",
                body='[{"session_id":"example-session","title":"Museum site","timestamp":"2026-09-23 21:22:28","mode":"site"}]',
            ))
            desktop.goto("http://127.0.0.1:5000", wait_until="networkidle")
            desktop.get_by_text("Help me describe my website").click()
            desktop.get_by_label("Topic or business").fill("Independent bookshop")
            desktop.get_by_label("Pages or sections").fill("Home, catalog, events")
            desktop.get_by_role("button", name="Add details to prompt").click()
            desktop.wait_for_function("document.querySelector('#composer-textarea')?.value.includes('Independent bookshop')")
            assert "Independent bookshop" in desktop.locator("textarea").input_value()
            assert "Home, catalog, events" in desktop.locator("textarea").input_value()
            row = desktop.locator("#sidebar-project-item-example-session")
            assert row.is_visible()
            assert row.locator("button").first.count() == 1 and "Museum site" in row.locator("button").first.inner_text()
            assert "Just now" not in row.inner_text()
            assert row.locator("time").get_attribute("title") != "Update time unavailable"
            desktop.close()
        finally:
            browser.close()
    print("P1 workbench browser smoke check passed")


if __name__ == "__main__":
    main()
