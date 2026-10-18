"""Browser self-check for a generated kit site.

Builds nothing itself: point it at a session workspace that the workbench produced
(it must contain dist/ after `vite build`, or it runs the build), serves dist/
locally, and exercises the site in Chromium. Writes screenshots and a JSON
result next to --out.

    python scripts/ui_selfcheck_site.py --workspace generated_components/session_x --out runs/ui_selfcheck_20261016/aster
"""
from __future__ import annotations

import argparse
import functools
import http.server
import json
import subprocess
import threading
from pathlib import Path


def serve(directory: Path) -> tuple[http.server.ThreadingHTTPServer, str]:
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(directory))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_address[1]}"


def check(url: str, out: Path, expect: dict) -> dict:
    from playwright.sync_api import sync_playwright

    out.mkdir(parents=True, exist_ok=True)
    results: dict = {"url": url, "checks": {}, "console_errors": [], "page_errors": []}
    c = results["checks"]
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.on("console", lambda m: m.type == "error" and results["console_errors"].append(m.text))
        page.on("pageerror", lambda e: results["page_errors"].append(str(e)))
        page.add_init_script("window.__frames = 0; (function t(){ window.__frames++; requestAnimationFrame(t); })();")
        page.goto(url, wait_until="networkidle")
        page.wait_for_timeout(1500)
        page.screenshot(path=str(out / "desktop_top.png"))

        head = page.evaluate("""() => ({
            title: document.title,
            description: !!document.querySelector('meta[name="description"]'),
            og: !!document.querySelector('meta[property="og:title"]') && !!document.querySelector('meta[property="og:image"]'),
            icon: !!document.querySelector('link[rel="icon"]') && !!document.querySelector('link[rel="apple-touch-icon"]'),
            themeColor: !!document.querySelector('meta[name="theme-color"]'),
        })""")
        c["head_tags"] = head
        fonts = page.evaluate("async () => { await document.fonts.ready; return [...document.fonts].filter(f => f.status === 'loaded').map(f => f.family.replace(/\"/g, '')); }")
        c["fonts_loaded"] = sorted(set(fonts))
        c["fonts_ok"] = all(any(name in f for f in fonts) for name in expect.get("fonts", []))
        c["h1_count"] = page.evaluate("() => document.querySelectorAll('h1').length")
        c["sections"] = page.evaluate("() => [...document.querySelectorAll('main section[id]')].map(s => s.id)")
        c["broken_images"] = page.evaluate("() => [...document.images].filter(i => i.complete && i.naturalWidth === 0).map(i => i.src)")
        c["image_count"] = page.evaluate("() => document.images.length")
        c["dead_anchors"] = page.evaluate("() => [...document.querySelectorAll('a[href^=\"#\"]')].map(a => a.getAttribute('href').slice(1)).filter(id => id && !document.getElementById(id))")
        text = page.evaluate("() => document.body.innerText")
        c["forbidden_text"] = [w for w in expect.get("forbidden", []) if w.lower() in text.lower()]
        c["required_text"] = {w: (w.lower() in text.lower()) for w in expect.get("required", [])}
        c["overflow_1280"] = page.evaluate("() => document.documentElement.scrollWidth > innerWidth")

        # Full scroll-through screenshots of every section.
        for sid in c["sections"]:
            page.evaluate(f"document.getElementById('{sid}').scrollIntoView({{behavior: 'instant', block: 'start'}})")
            page.wait_for_timeout(700)
            page.screenshot(path=str(out / f"desktop_{sid}.png"))
        page.evaluate("document.querySelector('footer') && document.querySelector('footer').scrollIntoView({behavior:'instant'})")
        page.wait_for_timeout(400)
        page.screenshot(path=str(out / "desktop_footer.png"))

        # Reveal fires once (items stay visible after scrolling away and back).
        c["reveal"] = page.evaluate("""() => {
            const items = [...document.querySelectorAll('[data-motion="scroll-reveal"]')];
            return {count: items.length, visible: items.filter(i => i.classList.contains('is-visible')).length};
        }""")

        # Header tucks on scroll down, returns on scroll up.
        page.evaluate("window.scrollTo({top: 0, behavior: 'instant'})")
        page.wait_for_timeout(300)
        page.mouse.wheel(0, 900)
        page.wait_for_timeout(700)
        tucked = page.evaluate("() => document.querySelector('.k-header').classList.contains('is-tucked')")
        page.mouse.wheel(0, -300)
        page.wait_for_timeout(700)
        returned = not page.evaluate("() => document.querySelector('.k-header').classList.contains('is-tucked')")
        c["header_tuck"] = {"tucked_on_down": tucked, "returned_on_up": returned}

        # Scroll-spy marks the section in view.
        first = c["sections"][1] if len(c["sections"]) > 1 else None
        if first:
            page.evaluate(f"document.getElementById('{first}').scrollIntoView({{behavior: 'instant', block: 'center'}})")
            page.wait_for_timeout(600)
            c["scroll_spy"] = page.evaluate(f"() => !!document.querySelector('.k-header__link[aria-current=\"location\"][href=\"#{first}\"]')")

        # Shader pauses when scrolled away (frame counter stops growing from its loop).
        if page.query_selector("canvas.k-shader"):
            page.evaluate("window.scrollTo({top: 0, behavior: 'instant'})")
            page.wait_for_timeout(500)
            draws = page.evaluate("""() => new Promise(r => { const c = document.querySelector('canvas.k-shader');
                const gl = c.getContext('webgl'); let n = 0; const orig = gl.drawArrays.bind(gl);
                gl.drawArrays = (...a) => { n++; return orig(...a); }; window.__shaderDraws = () => n; setTimeout(() => r(n), 1000); })""")
            page.evaluate("window.scrollTo({top: document.body.scrollHeight, behavior: 'instant'})")
            page.wait_for_timeout(600)
            before = page.evaluate("window.__shaderDraws()")
            page.wait_for_timeout(1000)
            after = page.evaluate("window.__shaderDraws()")
            c["shader"] = {"draws_per_s_visible": draws, "draws_while_hidden": after - before}

        # FAQ accordion and menu tabs when present.
        if page.query_selector("[aria-controls$='-a-1']"):
            btn = page.locator("[aria-controls$='-a-1']").first
            btn.scroll_into_view_if_needed()
            btn.click()
            page.wait_for_timeout(300)
            c["faq_accordion"] = btn.get_attribute("aria-expanded") == "true"
        tabs = page.locator("[role='tab']")
        if tabs.count() >= 2:
            tabs.nth(1).scroll_into_view_if_needed()
            before = page.locator("[role='tabpanel']").first.inner_text()
            tabs.nth(1).click()
            page.wait_for_timeout(500)
            c["menu_tabs"] = tabs.nth(1).get_attribute("aria-selected") == "true" and page.locator("[role='tabpanel']").first.inner_text() != before
            tabs.nth(1).press("ArrowRight")
            page.wait_for_timeout(400)
            c["menu_tabs_keyboard"] = page.evaluate("() => document.activeElement && document.activeElement.getAttribute('role') === 'tab'")

        # Contact form: empty submit shows inline errors; valid submit shows busy/done state.
        form = page.query_selector("form")
        if form:
            page.locator("form button[type=submit]").scroll_into_view_if_needed()
            page.locator("form button[type=submit]").click()
            page.wait_for_timeout(300)
            c["form_inline_errors"] = page.locator("form [aria-invalid='true']").count()
            page.screenshot(path=str(out / "desktop_form_errors.png"))

        # Reduced motion: everything static and visible.
        rm = browser.new_page(viewport={"width": 1280, "height": 800}, reduced_motion="reduce")
        rm.goto(url, wait_until="networkidle")
        rm.wait_for_timeout(600)
        c["reduced_motion_hidden"] = rm.evaluate("""() => [...document.querySelectorAll('[data-motion], .k-rise-2, .k-rise-3')]
            .filter(e => parseFloat(getComputedStyle(e).opacity) < 0.99).length""")
        rm.close()

        # Mobile 375 / 390: overflow, top, menu open, Escape returns focus, footer.
        mobile = browser.new_page(viewport={"width": 390, "height": 844}, has_touch=True, is_mobile=True)
        mobile.goto(url, wait_until="networkidle")
        mobile.wait_for_timeout(1200)
        mobile.screenshot(path=str(out / "mobile_top.png"))
        c["overflow_390"] = mobile.evaluate("() => document.documentElement.scrollWidth > innerWidth")
        mobile.click(".k-header__toggle")
        mobile.wait_for_timeout(500)
        c["drawer_open"] = mobile.evaluate("() => getComputedStyle(document.getElementById('site-menu')).visibility === 'visible'")
        c["drawer_scroll_lock"] = mobile.evaluate("() => document.body.style.overflow === 'hidden'")
        mobile.screenshot(path=str(out / "mobile_menu.png"))
        mobile.keyboard.press("Escape")
        mobile.wait_for_timeout(500)
        c["drawer_escape_focus"] = mobile.evaluate("() => document.activeElement && document.activeElement.classList.contains('k-header__toggle')")
        c["tap_targets_under_44"] = mobile.evaluate("""() => [...document.querySelectorAll('header a, header button, footer a, footer button')]
            .filter(e => { const r = e.getBoundingClientRect(); return r.width > 0 && (r.height < 43.5); })
            .map(e => (e.textContent || e.getAttribute('aria-label') || '').trim().slice(0, 30))""")
        mobile.evaluate("window.scrollTo({top: document.body.scrollHeight, behavior: 'instant'})")
        mobile.wait_for_timeout(600)
        mobile.screenshot(path=str(out / "mobile_footer.png"))
        m375 = browser.new_page(viewport={"width": 375, "height": 812})
        m375.goto(url, wait_until="networkidle")
        m375.wait_for_timeout(600)
        c["overflow_375"] = m375.evaluate("() => document.documentElement.scrollWidth > innerWidth")

        # 404 page.
        resp = page.goto(url.rstrip("/") + "/404.html")
        c["page_404"] = bool(resp and resp.ok and "doesn't exist" in page.content())
        browser.close()
    return results


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--expect", default="{}", help="JSON: fonts, forbidden, required")
    args = ap.parse_args()
    workspace = Path(args.workspace).resolve()
    if not (workspace / "dist" / "index.html").exists():
        subprocess.run("npx vite build", cwd=workspace, shell=True, check=True, capture_output=True)
    server, url = serve(workspace / "dist")
    try:
        result = check(url + "/", Path(args.out), json.loads(args.expect))
    finally:
        server.shutdown()
    (Path(args.out) / "checks.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result["checks"], indent=1))
    print("console_errors:", result["console_errors"][:5], "page_errors:", result["page_errors"][:5])


if __name__ == "__main__":
    main()
