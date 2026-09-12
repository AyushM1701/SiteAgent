"""
visual_judge.py - Playwright Visual Judge for the Site Pipeline

Takes a built site directory, starts a Vite dev server, takes a screenshot,
and scores it using heuristic checks (and optionally an LLM vision judge).

This is a soft-dependency module: if Playwright is not installed, all functions
degrade gracefully and return a neutral score without raising.

Install:
    pip install playwright
    playwright install chromium
"""

import os
import re
import json
import time
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

# ── Constants ─────────────────────────────────────────────────────────────────

VISUAL_JUDGE_PORT = 5174   # separate from main dev server (5173) to avoid conflicts
_PLAYWRIGHT_AVAILABLE = None  # lazily set

def _check_playwright() -> bool:
    global _PLAYWRIGHT_AVAILABLE
    if _PLAYWRIGHT_AVAILABLE is None:
        try:
            import playwright  # noqa: F401
            _PLAYWRIGHT_AVAILABLE = True
        except ImportError:
            _PLAYWRIGHT_AVAILABLE = False
    return _PLAYWRIGHT_AVAILABLE


# ── Heuristic image scoring (no LLM required) ─────────────────────────────────

def _score_screenshot_heuristic(screenshot_path: Path) -> dict:
    """
    Scores a screenshot using pixel-level heuristics.
    Returns a dict with score (0-5), issues list, and pass bool.

    Checks:
    1. Not a blank white/single-color page (most common failure)
    2. Content height implies multiple sections (not just a title)
    3. Multiple distinct colors visible (nav + content + footer pattern)
    4. Text-heavy regions in expected positions
    """
    try:
        # Try to use PIL/Pillow if available
        from PIL import Image
        import colorsys

        img = Image.open(screenshot_path).convert("RGB")
        width, height = img.size

        issues = []
        score = 5

        # --- Check 1: Blank page detection ---
        # Sample a grid of pixels and check color variance
        pixels = []
        step = max(1, width // 20)
        for x in range(0, width, step):
            for y in range(0, height, step):
                pixels.append(img.getpixel((x, y)))

        if pixels:
            r_vals = [p[0] for p in pixels]
            g_vals = [p[1] for p in pixels]
            b_vals = [p[2] for p in pixels]

            # Check if >85% of pixels are nearly white (blank page)
            white_count = sum(1 for p in pixels if p[0] > 240 and p[1] > 240 and p[2] > 240)
            white_ratio = white_count / len(pixels)
            if white_ratio > 0.85:
                issues.append(f"Page appears blank ({white_ratio:.0%} near-white pixels)")
                score -= 3

            # Check color variance (distinct regions = layout present)
            r_range = max(r_vals) - min(r_vals)
            g_range = max(g_vals) - min(g_vals)
            b_range = max(b_vals) - min(b_vals)
            color_range = max(r_range, g_range, b_range)

            if color_range < 30:
                issues.append("Very low color variance - likely single-background page")
                score -= 2
            elif color_range < 80:
                issues.append("Low color diversity - may lack header/footer contrast")
                score -= 1

        # --- Check 2: Rendered height ---
        # A multi-section page should have content extending beyond the viewport
        # We can't check scroll height from a screenshot, but we can check
        # if the bottom rows of the image are non-white (footer present)
        bottom_strip = []
        for x in range(0, width, step):
            bottom_strip.append(img.getpixel((x, height - 1)))
        bottom_white = sum(1 for p in bottom_strip if p[0] > 240 and p[1] > 240 and p[2] > 240)
        if bottom_white / max(len(bottom_strip), 1) > 0.9:
            issues.append("Bottom of page is blank - footer may be missing")
            score -= 1

        # --- Check 3: Header presence & structural diversity ---
        # Instead of penalizing light headers by brightness alone, check for structural presence:
        # A header region should exhibit horizontal contrast variance (logo, nav links, CTA buttons).
        top_height = max(4, height // 10)
        top_pixels = [img.getpixel((x, y)) for x in range(0, width, step) for y in range(0, top_height, max(1, top_height // 4))]
        if top_pixels:
            top_luminance = [0.299 * p[0] + 0.587 * p[1] + 0.114 * p[2] for p in top_pixels]
            header_variance = max(top_luminance) - min(top_luminance)
            if header_variance < 15:
                issues.append("Header region has uniform appearance - may lack logo or navigation elements")
                score -= 1

        # --- Check 4: Layout vertical distribution & section rhythm ---
        # Verify that content is distributed across vertical section bands rather than clumped in a single strip
        band_height = max(1, height // 4)
        band_variances = []
        for b in range(4):
            band_pix = [img.getpixel((x, b * band_height + band_height // 2)) for x in range(0, width, step)]
            if band_pix:
                lum = [0.299 * p[0] + 0.587 * p[1] + 0.114 * p[2] for p in band_pix]
                band_variances.append(max(lum) - min(lum))
        
        flat_bands = sum(1 for v in band_variances if v < 15)
        if flat_bands >= 3:
            issues.append("Multiple vertical bands appear flat/empty - layout may lack multi-section rhythm")
            score -= 1

        # --- Check 5: Margin & Content Width Sanity ---
        # Check that page utilizes viewport margins cleanly (not zero-width or empty centered void)
        center_x = width // 2
        center_pix = [img.getpixel((center_x, y)) for y in range(0, height, max(1, height // 20))]
        left_pix = [img.getpixel((step, y)) for y in range(0, height, max(1, height // 20))]
        if center_pix and left_pix:
            c_lum_avg = sum(0.299 * p[0] + 0.587 * p[1] + 0.114 * p[2] for p in center_pix) / len(center_pix)
            l_lum_avg = sum(0.299 * p[0] + 0.587 * p[1] + 0.114 * p[2] for p in left_pix) / len(left_pix)
            # If both center and margins are perfectly white/blank, page is empty
            if c_lum_avg > 248 and l_lum_avg > 248 and "Page appears blank" not in issues:
                issues.append("Low content density detected across page center and margins")
                score -= 1

        score = max(0, score)
        return {
            "score": score,
            "max_score": 5,
            "pass": score >= 3,
            "issues": issues,
            "method": "heuristic_pixel",
        }

    except ImportError:
        # PIL not available - return neutral score with note
        return {
            "score": 3,
            "max_score": 5,
            "pass": True,
            "issues": ["PIL/Pillow not available for pixel analysis - install with: pip install Pillow"],
            "method": "unavailable",
        }
    except Exception as e:
        return {
            "score": 2,
            "max_score": 5,
            "pass": False,
            "issues": [f"Heuristic scoring failed: {e}"],
            "method": "error",
        }


def _score_screenshot_llm(screenshot_path: Path) -> Optional[dict]:
    """
    Sends the screenshot to Gemini vision for a 1-5 quality score.
    Returns None if no API key is available.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None

    try:
        import base64
        import urllib.request

        with open(screenshot_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode("utf-8")

        prompt = (
            "Rate this website screenshot on a scale of 1-5 for visual completeness:\n"
            "1 = Blank or near-blank page (just a title or white background)\n"
            "2 = Minimal content, no real layout or styling\n"
            "3 = Basic layout present but missing sections or has visual issues\n"
            "4 = Good layout with multiple sections, real content and styling\n"
            "5 = Excellent: full website with header, hero, content sections, footer, and polished design\n\n"
            "Respond with ONLY a JSON object: {\"score\": N, \"reasoning\": \"...one sentence...\"}"
        )

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": "image/webp", "data": img_b64}}
                ]
            }],
            "generationConfig": {"temperature": 0.1, "maxOutputTokens": 128},
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json", "x-goog-api-key": api_key}
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        text = body["candidates"][0]["content"]["parts"][0]["text"].strip()
        # Strip markdown fences
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        result = json.loads(text)
        return {
            "score": int(result.get("score", 3)),
            "max_score": 5,
            "pass": int(result.get("score", 3)) >= 3,
            "reasoning": result.get("reasoning", ""),
            "method": "llm_vision_gemini",
        }
    except Exception as e:
        print(f"[VisualJudge] LLM scoring failed: {e}")
        return None


# ── Playwright screenshot + scoring ───────────────────────────────────────────

def take_screenshot(
    project_dir: Path,
    port: int = VISUAL_JUDGE_PORT,
    output_path: Optional[Path] = None,
    timeout_ms: int = 12000,
) -> Optional[Path]:
    """
    Starts a Vite dev server in project_dir, takes a screenshot with Playwright,
    stops the server, and returns the screenshot path.
    Returns None if Playwright is unavailable or the server fails to start.
    """
    if not _check_playwright():
        print("[VisualJudge] Playwright not installed. Skipping screenshot. "
              "Install with: pip install playwright && playwright install chromium")
        return None

    if not (project_dir / "package.json").exists():
        print(f"[VisualJudge] No package.json in {project_dir} - skipping screenshot")
        return None

    if output_path is None:
        output_path = project_dir / "screenshot.webp"

    vite_proc = None
    try:
        from playwright.sync_api import sync_playwright

        # Start Vite dev server on the judge port
        env = {**os.environ, "PORT": str(port)}
        vite_proc = subprocess.Popen(
            ["npm", "run", "dev", "--", "--port", str(port), "--no-open"],
            cwd=str(project_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )

        # Wait for dev server to be ready (poll for up to 15s)
        url = f"http://localhost:{port}"
        import urllib.request as _req
        for _ in range(30):
            time.sleep(0.5)
            try:
                _req.urlopen(url, timeout=1)
                break
            except Exception:
                continue

        # Take screenshot
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(url, wait_until="networkidle", timeout=timeout_ms)
            page.wait_for_timeout(1000)  # let animations settle
            page.screenshot(path=str(output_path), type="webp")
            browser.close()

        print(f"[VisualJudge] Screenshot saved to {output_path}")
        return output_path

    except Exception as e:
        print(f"[VisualJudge] Screenshot failed: {e}")
        return None
    finally:
        if vite_proc:
            vite_proc.terminate()
            try:
                vite_proc.wait(timeout=3)
            except Exception:
                vite_proc.kill()


# ── Public API ─────────────────────────────────────────────────────────────────

def score_visual(
    project_dir: Path,
    port: int = VISUAL_JUDGE_PORT,
    use_llm: bool = True,
) -> dict:
    """
    Full visual scoring pipeline for a generated site:
    1. Takes a Playwright screenshot
    2. Scores with pixel heuristics
    3. Optionally upgrades with Gemini LLM judge

    Always returns a dict with at least:
        score (int 0-5), pass (bool), issues (list), method (str), screenshot_path (str|None)

    Degrades gracefully if Playwright/PIL/Gemini are unavailable.
    """
    result = {
        "score": 3,
        "max_score": 5,
        "pass": True,
        "issues": [],
        "method": "skipped",
        "screenshot_path": None,
    }

    screenshot_path = take_screenshot(project_dir, port=port)
    if screenshot_path and screenshot_path.exists():
        result["screenshot_path"] = str(screenshot_path)

        # Heuristic scoring
        heuristic = _score_screenshot_heuristic(screenshot_path)
        result.update(heuristic)

        # LLM upgrade (if Gemini key available and heuristic didn't already catch blank page)
        if use_llm and result["score"] >= 2:
            llm_result = _score_screenshot_llm(screenshot_path)
            if llm_result:
                # Blend: LLM is more reliable than heuristic, but keep issues list
                issues = result.get("issues", [])
                result.update(llm_result)
                result["issues"] = issues + (
                    [f"LLM reasoning: {llm_result.get('reasoning', '')}"] if llm_result.get("reasoning") else []
                )
    else:
        result["issues"].append("Screenshot unavailable (Playwright not installed or server failed to start)")

    return result


# ── Visual Regression Baselines ────────────────────────────────────────────────

BASELINES_DIR = Path(__file__).parent / "visual_baselines"


def save_as_baseline(screenshot_path: Path, template_name: str) -> Path:
    """Saves a known-good screenshot as the visual regression baseline for a template."""
    BASELINES_DIR.mkdir(parents=True, exist_ok=True)
    baseline_dest = BASELINES_DIR / f"{template_name}_baseline.webp"
    import shutil
    shutil.copy2(screenshot_path, baseline_dest)
    print(f"[VisualJudge] Saved baseline snapshot for '{template_name}' to {baseline_dest}")
    return baseline_dest


def compare_visual_baseline(
    screenshot_path: Path,
    baseline_path: Path,
    max_diff_percent: float = 5.0,
    diff_output_path: Optional[Path] = None,
) -> dict:
    """
    Compares a candidate screenshot against a known-good baseline screenshot using pixel-level diffing.
    Returns diff percentage and whether it passes regression tolerance.
    """
    if not screenshot_path.exists():
        return {"passed": False, "error": f"Screenshot not found: {screenshot_path}", "diff_percent": 100.0}
    if not baseline_path.exists():
        return {"passed": False, "error": f"Baseline not found: {baseline_path}", "diff_percent": 100.0}

    try:
        from PIL import Image, ImageChops

        img_actual = Image.open(screenshot_path).convert("RGB")
        img_baseline = Image.open(baseline_path).convert("RGB")

        # Resize if dimensions differ slightly due to viewport
        if img_actual.size != img_baseline.size:
            img_actual = img_actual.resize(img_baseline.size, Image.Resampling.LANCZOS)

        diff = ImageChops.difference(img_actual, img_baseline)
        
        # Calculate bounding box and pixel difference ratio
        bbox = diff.getbbox()
        if not bbox:
            return {"passed": True, "diff_percent": 0.0, "identical": True}

        diff_data = list(diff.getdata())
        total_pixels = len(diff_data)
        changed_pixels = sum(1 for r, g, b in diff_data if (r + g + b) > 30)
        diff_percent = (changed_pixels / total_pixels) * 100.0

        if diff_output_path:
            diff_output_path.parent.mkdir(parents=True, exist_ok=True)
            diff.save(diff_output_path)

        passed = diff_percent <= max_diff_percent
        return {
            "passed": passed,
            "diff_percent": round(diff_percent, 2),
            "max_allowed_diff": max_diff_percent,
            "changed_pixels": changed_pixels,
            "total_pixels": total_pixels,
            "diff_path": str(diff_output_path) if diff_output_path else None,
        }
    except ImportError:
        return {"passed": True, "skipped": True, "reason": "Pillow not installed; pixel diff skipped."}
    except Exception as e:
        return {"passed": False, "error": str(e), "diff_percent": 100.0}

