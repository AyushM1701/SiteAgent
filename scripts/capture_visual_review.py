"""Capture review evidence for one running site without assigning a quality score."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright


def capture(url: str, output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    evidence = {"url": url, "captures": {}}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            for name, width, height, reduced in (
                ("desktop", 1280, 900, False),
                ("mobile", 390, 844, False),
                ("reduced_motion", 390, 844, True),
            ):
                context = browser.new_context(
                    viewport={"width": width, "height": height},
                    reduced_motion="reduce" if reduced else "no-preference",
                    record_video_dir=str(output_dir),
                    record_video_size={"width": width, "height": height},
                )
                page = context.new_page()
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
                page.goto(url, wait_until="domcontentloaded", timeout=20000)
                page.wait_for_timeout(500)
                # Trigger below-fold reveal observers before the full-page
                # overview; otherwise valid sections can appear as blank gaps.
                for fraction in (0.25, 0.5, 0.75, 1.0):
                    page.evaluate("fraction => window.scrollTo(0, (document.documentElement.scrollHeight - innerHeight) * fraction)", fraction)
                    page.wait_for_timeout(650)
                page.evaluate("window.scrollTo(0, 0)")
                page.wait_for_timeout(650)
                screenshot = output_dir / f"{name}_screenshot.png"
                page.screenshot(path=str(screenshot), full_page=True)
                for fraction in (0.25, 0.5, 0.75, 1.0):
                    page.evaluate("fraction => window.scrollTo(0, (document.documentElement.scrollHeight - innerHeight) * fraction)", fraction)
                    page.wait_for_timeout(350)
                video = page.video
                page.close()
                context.close()
                video_path = output_dir / f"{name}_scroll_video.webm"
                if video:
                    Path(video.path()).replace(video_path)
                evidence["captures"][name] = {
                    "screenshot": str(screenshot.resolve()),
                    "scroll_video": str(video_path.resolve()),
                    "viewport": {"width": width, "height": height},
                    "reduced_motion": reduced,
                    "browser_errors": errors,
                }
        finally:
            browser.close()
    (output_dir / "evidence.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    return evidence


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    print(json.dumps(capture(args.url, args.output_dir), indent=2))
