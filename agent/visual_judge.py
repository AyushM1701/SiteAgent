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
import shutil
import signal
import socket
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

# ── Constants ─────────────────────────────────────────────────────────────────

VISUAL_JUDGE_PORT = 0  # choose a free port for each check
_PLAYWRIGHT_AVAILABLE = None  # lazily set


def _stop_process_tree(proc):
    """Reap the dev server and its children, including npm's Windows wrapper."""
    if os.name == "nt":
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    else:
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    try:
        proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        if os.name != "nt":
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        else:
            proc.kill()
        proc.wait(timeout=3)

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

            # A blank page is a uniform frame. A light, airy layout with generous
            # whitespace is not blank, however much of it is near-white (A15).
            lum = [0.2126 * p[0] + 0.7152 * p[1] + 0.0722 * p[2] for p in pixels]
            mean_lum = sum(lum) / len(lum)
            spread = (sum((v - mean_lum) ** 2 for v in lum) / len(lum)) ** 0.5
            distinct = sum(1 for v in lum if abs(v - mean_lum) > 24)
            if spread < 4 or distinct < max(3, len(lum) // 200):
                issues.append(f"Page appears blank (uniform frame, luminance spread {spread:.1f})")
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
        # No image analysis means visual quality is unverified.
        return {
            "score": 0,
            "max_score": 5,
            "pass": False,
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

    if port == 0:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]

    vite_proc = None
    try:
        from playwright.sync_api import sync_playwright

        # Start Vite dev server on the judge port
        # Fail before navigation when another process owns the port.
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.bind(("127.0.0.1", port))
        env = {**os.environ, "PORT": str(port)}
        vite_proc = subprocess.Popen(
            [shutil.which("npm") or "npm", "run", "dev", "--", "--host", "127.0.0.1", "--port", str(port), "--strictPort", "--no-open"],
            cwd=str(project_dir),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=env,
            start_new_session=(os.name != "nt"),
        )

        # Wait for dev server to be ready (poll for up to 15s)
        url = f"http://127.0.0.1:{port}"
        import urllib.request as _req
        for _ in range(30):
            time.sleep(0.5)
            if vite_proc.poll() is not None:
                raise RuntimeError("Vite exited before becoming ready (the port may already be occupied)")
            try:
                with _req.urlopen(url, timeout=1):
                    pass
                break
            except Exception:
                continue
        else:
            raise TimeoutError("Vite did not become ready within 15 seconds")

        # Take screenshot
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(url, wait_until="networkidle", timeout=timeout_ms)
            page.wait_for_timeout(1000)  # let animations settle
            page.screenshot(path=str(output_path), type="webp", full_page=True)
            page.set_viewport_size({"width": 390, "height": 844})
            page.wait_for_timeout(250)
            mobile_path = output_path.with_name(f"{output_path.stem}-mobile{output_path.suffix}")
            page.screenshot(path=str(mobile_path), type="webp", full_page=True)
            browser.close()

        print(f"[VisualJudge] Screenshot saved to {output_path}")
        return output_path

    except Exception as e:
        print(f"[VisualJudge] Screenshot failed: {e}")
        return None
    finally:
        if vite_proc:
            _stop_process_tree(vite_proc)


# ── Public API ─────────────────────────────────────────────────────────────────

def score_visual(
    project_dir: Path,
    port: int = VISUAL_JUDGE_PORT,
    use_llm: bool = True,
    layout_archetype: str = "grid",
) -> dict:
    """
    Full visual scoring pipeline for a generated site:
    1. Takes a Playwright screenshot
    2. Scores with pixel heuristics
    3. Evaluates code-level motion vocabulary and reduced-motion fallback
    4. Optionally upgrades with Gemini LLM judge

    Always returns a dict with at least:
        score (int 0-5), pass (bool), issues (list), polish_score (int 0-5),
        method (str), screenshot_path (str|None)

    Degrades gracefully if Playwright/PIL/Gemini are unavailable.
    """
    result = {
        "score": 0,
        "max_score": 5,
        "pass": False,
        "polish_score": 3,
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

    # Code-level motion & polish assessment
    src_dir = project_dir / "src"
    if src_dir.exists():
        src_code = []
        src_css = []
        for p in src_dir.rglob("*.tsx"):
            try:
                src_code.append(p.read_text(encoding="utf-8"))
            except Exception:
                pass
        for p in src_dir.rglob("*.css"):
            try:
                src_css.append(p.read_text(encoding="utf-8"))
            except Exception:
                pass
        if src_code or src_css:
            polish_res = evaluate_motion_polish("\n".join(src_code), "\n".join(src_css), layout_archetype=layout_archetype)
            result["polish_score"] = polish_res.get("score", 5)
            result["polish_issues"] = polish_res.get("issues", [])
            result["has_reduced_motion"] = polish_res.get("has_reduced_motion", True)
            for p_iss in polish_res.get("issues", []):
                if p_iss not in result.get("issues", []):
                    result["issues"].append(p_iss)
            if polish_res.get("score", 5) <= 2:
                result["score"] = min(result.get("score", 3), 2)
                result["pass"] = False

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
        return {"passed": False, "verified": False, "status": "unverified", "skipped": True,
                "reason": "Pillow not installed; pixel diff cannot be verified."}
    except Exception as e:
        return {"passed": False, "error": str(e), "diff_percent": 100.0}


# ── Code-Level Motion & Polish Quality Judge ──────────────────────────────────

def evaluate_motion_polish(
    code_or_files: Union[str, Dict[str, str]],
    css: str = "",
    layout_archetype: Union[str, Any] = "grid",
) -> dict:
    """
    Evaluates code-level motion and polish implementation against the
    systematic motion vocabulary registry (_MOTION_VOCABULARY).

    Checks:
    1. Mandatory Accessibility: @media (prefers-reduced-motion: reduce) fallback
       is present, disabling animations/transforms and ensuring instant opacity.
    2. Archetype Motion Pattern Alignment:
       - grid: scroll-staggered card reveal (via IntersectionObserver or staggered index delay) + hover lift.
       - timeline: sequential milestone reveal on scroll + connecting spine draw-in.
       - tabs: tab panel state crossfade/slide settling transition.
       - split_hero: coordinated asymmetric entrance with offset delay between left copy and right visual.
       - editorial: restrained quiet fade-only prose reveal, strictly no aggressive bounce/lift.
       - bento: span-weighted entrance stagger + hover lift and accent border-glow.
    3. Interactive Micro-interactions: hover elevation, border transitions, or active state pills.

    Returns dict with:
        score: int (0-5)
        polish_score: int (0-5)
        pass: bool (score >= 3 and has_reduced_motion)
        has_reduced_motion: bool
        has_archetype_motion: bool
        motion_pattern_matched: str
        archetype: str
        issues: list[str]
        method: "code_motion_polish_heuristic"
    """
    if isinstance(code_or_files, dict):
        tsx_parts = []
        css_parts = []
        for path, content in code_or_files.items():
            if str(path).endswith(".css"):
                css_parts.append(content)
            else:
                tsx_parts.append(content)
        full_tsx = "\n".join(tsx_parts)
        full_css = (css + "\n" + "\n".join(css_parts)).strip()
    else:
        full_tsx = str(code_or_files)
        full_css = str(css)

    norm_tsx = full_tsx.lower()
    norm_css = full_css.lower()
    combined = f"{norm_tsx}\n{norm_css}"

    # Normalize archetype string
    if hasattr(layout_archetype, "value"):
        arch_str = str(layout_archetype.value).lower()
    else:
        arch_str = str(layout_archetype).lower().strip()
    if "layoutarchetype." in arch_str:
        arch_str = arch_str.split("layoutarchetype.")[-1]
    if not arch_str or arch_str == "none":
        arch_str = "grid"

    issues = []

    # 1. Mandatory Accessibility Check: prefers-reduced-motion
    has_reduced_motion = "prefers-reduced-motion" in combined
    if not has_reduced_motion:
        issues.append("Missing @media (prefers-reduced-motion: reduce) accessibility fallback")

    # 2. General Motion Signal Detection
    has_any_animation = bool(re.search(r"\banimation(?:-[a-z]+)?\s*:", norm_css)) or "@keyframes" in norm_css
    has_any_transition = bool(re.search(r"\btransition(?:-[a-z]+)?\s*:", norm_css))
    has_intersection_observer = "intersectionobserver" in norm_tsx
    has_hover_interaction = ":hover" in norm_css or "hover:" in norm_css

    is_completely_static = not (has_any_animation or has_any_transition or has_intersection_observer)

    has_archetype_motion = False
    motion_pattern_matched = "none"

    if is_completely_static:
        issues.append(f"Missing motion: section is completely static with no animations, transitions, or IntersectionObserver for archetype '{arch_str}'")
        motion_pattern_matched = "completely_static"
    else:
        # 3. Archetype-Specific Motion Verification
        if arch_str == "grid":
            # Grid expects: scroll-staggered card reveal (IntersectionObserver or staggered delays) + subtle hover lift
            has_stagger = (
                has_intersection_observer
                or "transitiondelay" in norm_tsx
                or "transition-delay" in norm_css
                or "animation-delay" in norm_css
                or "stagger" in combined
                or re.search(r"style=\{\{\s*transitiondelay", norm_tsx) is not None
                or "delay" in norm_tsx
            )
            has_hover_lift = (
                bool(re.search(r":hover[^{]*\{[^}]*translate(?:y)?\s*\(\s*-\s*\d", norm_css))
                or (":hover" in norm_css and "transform" in norm_css)
            )
            if has_stagger and has_hover_lift:
                has_archetype_motion = True
                motion_pattern_matched = "grid_scroll_stagger_and_hover_lift"
            elif has_stagger or has_hover_lift:
                has_archetype_motion = True
                motion_pattern_matched = "grid_partial_motion"
                if not has_stagger:
                    issues.append("Suboptimal grid motion: missing scroll-staggered reveal (IntersectionObserver or index delay) for card catalog")
                if not has_hover_lift:
                    issues.append("Suboptimal grid motion: missing subtle hover lift (e.g. translateY(-4px)) on cards")
            else:
                issues.append("Missing archetype motion: 'grid' requires scroll-staggered card reveal (via IntersectionObserver or index delay) and subtle hover lift")

        elif arch_str == "timeline":
            # Timeline expects: sequential milestone reveal on scroll + connecting spine/line animation
            has_node_reveal = (
                has_intersection_observer
                or "is-revealed" in combined
                or "revealed" in combined
                or ("node" in norm_css and ("opacity" in norm_css or "translate" in norm_css))
                or (("phase" in combined or "milestone" in combined or "step" in combined) and (has_any_animation or has_any_transition))
            )
            has_spine_or_dot = any(k in norm_css for k in ("spine", "line", "dot", "pulse", "track", "connecting"))

            if has_node_reveal and (has_spine_or_dot or has_any_transition):
                has_archetype_motion = True
                motion_pattern_matched = "timeline_milestone_reveal_and_spine"
            elif has_node_reveal or has_any_animation:
                has_archetype_motion = True
                motion_pattern_matched = "timeline_partial_reveal"
                if not has_spine_or_dot:
                    issues.append("Suboptimal timeline motion: missing connecting spine/line draw-in or milestone node pulse animation")
            else:
                issues.append("Missing archetype motion: 'timeline' requires sequential milestone node reveal and connecting spine animation")

        elif arch_str == "tabs":
            # Tabs expects: smooth panel settling crossfade or slide transition on tab state change
            has_panel_transition = (
                ("panel" in norm_css or "showcase" in norm_css or "tab" in norm_css)
                and (has_any_animation or (has_any_transition and "opacity" in norm_css) or "crossfade" in combined)
            )
            if has_panel_transition:
                has_archetype_motion = True
                motion_pattern_matched = "tabs_panel_crossfade_slide"
            else:
                issues.append("Missing archetype motion: 'tabs' requires panel crossfade/slide settling transition on tab state change")

        elif arch_str == "split_hero":
            # Split Hero expects: coordinated asymmetric entrance with offset delay between left copy and right visual
            has_offset_delay = (
                bool(re.search(r"(?:left|right)[^{]*\{[^}]*(?:animation|delay)", norm_css))
                or ("delay" in norm_css and has_any_animation)
                or bool(re.search(r"\d+ms\s+(?:both|forwards)", norm_css))
                or ("split" in norm_css and has_any_animation)
            )
            if has_offset_delay:
                has_archetype_motion = True
                motion_pattern_matched = "split_hero_coordinated_entrance"
            elif has_any_animation or has_any_transition:
                has_archetype_motion = True
                motion_pattern_matched = "split_hero_partial_animation"
                issues.append("Suboptimal split_hero motion: missing coordinated offset delay between left text and right visual container")
            else:
                issues.append("Missing archetype motion: 'split_hero' requires coordinated asymmetric entrance with offset delays (e.g. 0ms vs 160ms)")

        elif arch_str == "editorial":
            # Editorial expects: restrained quiet fade-only prose reveal, strictly NO aggressive bounce/lift
            has_fade = (
                "fade" in norm_css
                or ("opacity" in norm_css and (has_any_animation or has_any_transition))
            )
            has_aggressive_motion = (
                bool(re.search(r"cubic-bezier\s*\([^)]*bounce", norm_css))
                or bool(re.search(r":hover[^{]*\{[^}]*scale\s*\(\s*1\.[1-9]", norm_css))
                or bool(re.search(r":hover[^{]*\{[^}]*translatey\s*\(\s*-\s*(?:1[0-9]|[2-9]\d)px", norm_css))
            )
            if has_fade and not has_aggressive_motion:
                has_archetype_motion = True
                motion_pattern_matched = "editorial_quiet_prose_fade"
            elif has_aggressive_motion:
                has_archetype_motion = True
                motion_pattern_matched = "editorial_with_excessive_motion"
                issues.append("Inappropriate editorial motion: contains aggressive bounce or large hover translations; editorial guidelines require restrained, quiet fade-only reveal")
            elif has_fade:
                has_archetype_motion = True
                motion_pattern_matched = "editorial_quiet_fade"
            else:
                issues.append("Missing archetype motion: 'editorial' requires restrained quiet fade-only prose reveal")

        elif arch_str == "bento":
            # Bento expects: span-weighted entrance stagger + hover lift and accent border-glow
            has_bento_stagger = (
                ("delay" in norm_css and "bento" in norm_css)
                or ("delay" in norm_css and has_any_animation)
                or any(f"card--{role}" in norm_css for role in ("hero", "tall", "metric", "feature", "standard"))
                or ("span" in norm_css and has_any_animation)
                or "bentoenter" in norm_css
            )
            has_border_glow = (
                ":hover" in norm_css
                and ("box-shadow" in norm_css or "border-color" in norm_css)
            )
            if has_bento_stagger and has_border_glow:
                has_archetype_motion = True
                motion_pattern_matched = "bento_span_stagger_and_border_glow"
            elif has_bento_stagger or has_border_glow:
                has_archetype_motion = True
                motion_pattern_matched = "bento_partial_motion"
                if not has_bento_stagger:
                    issues.append("Suboptimal bento motion: missing span-weighted entrance stagger matching card grid dimensions")
                if not has_border_glow:
                    issues.append("Suboptimal bento motion: missing hover accent border-glow / shadow bloom")
            else:
                issues.append("Missing archetype motion: 'bento' requires span-weighted entrance stagger and hover accent border-glow")

        else:
            if has_any_animation or has_any_transition:
                has_archetype_motion = True
                motion_pattern_matched = "generic_motion_present"
            else:
                issues.append(f"Missing motion: section lacks interactive transitions or animations for archetype '{arch_str}'")

    # 4. Polish Score Calculation (0 - 5 scale)
    if is_completely_static:
        score = 1
    else:
        score = 5
        if not has_archetype_motion:
            score -= 2
        elif len([iss for iss in issues if "Suboptimal" in iss or "Inappropriate" in iss]) > 0:
            score -= 1

        if not has_reduced_motion:
            score -= 1
            if score > 3:
                score = 3  # Cap at 3 if accessibility fallback is missing

    score = max(0, min(5, score))
    passed = score >= 3 and has_reduced_motion

    return {
        "score": score,
        "polish_score": score,
        "pass": passed,
        "has_reduced_motion": has_reduced_motion,
        "has_archetype_motion": has_archetype_motion,
        "motion_pattern_matched": motion_pattern_matched,
        "archetype": arch_str,
        "issues": issues,
        "method": "code_motion_polish_heuristic",
    }


# ── Training-Data Visual Filter (Harvesting & Quality Gating) ─────────────────

def score_code_visual_heuristic(code: str, css: str = "", layout_archetype: str = "grid") -> dict:
    """
    Scores code and stylesheet visual richness for training data harvesting
    when headless browser rendering is unavailable or for offline evaluation.

    Evaluates:
    1. CSS presence and rule depth (background, borders, shadow, radius, typography).
    2. Color diversity and contrast (palette presence vs monochrome void).
    3. Structural layout patterns (grid, flexbox, multi-section/card distribution).
    4. Interactive micro-styling (hover states, transitions, button styles).
    5. Archetype-appropriate motion vocabulary and prefers-reduced-motion fallback.

    Returns a dict with score (1-5), pass bool (>=3), issues list, polish_score, and method.
    """
    issues = []
    score = 5

    combined_text = f"{code}\n{css}"
    norm_css = css.lower()

    # Check 1: Mandatory CSS presence
    css_rules = re.findall(r"([^{]+)\{([^}]+)\}", css)
    if not css.strip() or len(css_rules) < 2:
        issues.append("Missing or minimal CSS stylesheet (fewer than 2 rules)")
        score -= 2
    elif len(css_rules) < 5:
        issues.append("Sparse styling: under 5 CSS rules defined")
        score -= 1

    # Check 2: Distinctive visual declarations
    has_background = bool(re.search(r"\bbackground(?:-color)?\s*:", norm_css))
    has_border = bool(re.search(r"\bborder(?:-radius)?\s*:", norm_css))
    has_typography = bool(re.search(r"\b(?:font-family|font-size|letter-spacing|line-height)\s*:", norm_css))
    has_layout = bool(re.search(r"\b(?:display\s*:\s*(?:flex|grid)|gap\s*:|grid-template)\b", norm_css))
    has_shadow = bool(re.search(r"\b(?:box-shadow|filter|backdrop-filter)\s*:", norm_css))

    missing_visuals = []
    if not has_background:
        missing_visuals.append("background")
    if not has_border:
        missing_visuals.append("border/radius")
    if not has_typography:
        missing_visuals.append("typography")
    if not has_layout:
        missing_visuals.append("flex/grid layout")

    if len(missing_visuals) >= 3:
        issues.append(f"Lacks primary visual styling properties: {', '.join(missing_visuals)}")
        score -= 2
    elif len(missing_visuals) >= 1:
        issues.append(f"Missing styling properties: {', '.join(missing_visuals)}")
        score -= 1

    # Check 3: Color diversity & palette presence
    # Find hex codes, rgb/rgba, hsl, and var(--color-*)
    hex_colors = set(re.findall(r"#(?:[0-9a-fA-F]{3,8})\b", combined_text))
    rgb_colors = set(re.findall(r"rgba?\([^)]+\)", combined_text))
    var_colors = set(re.findall(r"var\(--(?:color|accent|surface|primary)[^)]*\)", combined_text))
    total_colors = len(hex_colors | rgb_colors | var_colors)

    if total_colors == 0:
        issues.append("No explicit color tokens, hex codes, or theme variables detected")
        score -= 2
    elif total_colors < 2:
        issues.append("Monochrome appearance: only 1 color token found")
        score -= 1

    # Check 4: Interactive states & visual polish
    has_hover = ":hover" in norm_css or "hover:" in norm_css
    has_transition = "transition" in norm_css or "animation" in norm_css
    if not has_hover and not has_transition and score >= 4:
        issues.append("Lacks dynamic hover or transition micro-interactions")
        score -= 1

    # Check 5: Systematic Motion Vocabulary & Accessibility Check
    polish_res = evaluate_motion_polish(code, css, layout_archetype=layout_archetype)
    polish_score = polish_res.get("score", 5)
    polish_issues = polish_res.get("issues", [])
    for p_iss in polish_issues:
        if p_iss not in issues:
            issues.append(p_iss)

    # Penalize visual score if motion is absent for the archetype
    if polish_score <= 1:
        score = min(score, 2)  # Cap visual score to 2 (< 3 threshold)
    elif polish_score == 2:
        score = min(score, 2)
    elif polish_score == 3 and not polish_res.get("has_reduced_motion", True):
        score = min(score, 3)

    score = max(1, min(5, score))
    return {
        "score": score,
        "max_score": 5,
        "pass": score >= 3 and polish_res.get("pass", True),
        "polish_score": polish_score,
        "polish_issues": polish_issues,
        "has_reduced_motion": polish_res.get("has_reduced_motion", True),
        "has_archetype_motion": polish_res.get("has_archetype_motion", True),
        "motion_pattern_matched": polish_res.get("motion_pattern_matched", "none"),
        "issues": issues,
        "method": "code_visual_heuristic",
    }


def score_trajectory_visual(
    trajectory: Union[Dict[str, Any], str],
    workspace_dir: Optional[Path] = None,
    threshold: int = 3,
    exempt_single_components: bool = True,
) -> dict:
    """
    Universal visual judge scoring function for training data harvesting.
    Evaluates:
    1. Screenshot if available in workspace_dir (using pixel heuristics) + code motion audit.
    2. Cached visual_score if already recorded in trajectory metadata.
    3. Extracted TSX/CSS source code using code_visual_heuristic and evaluate_motion_polish.

    Returns dict with: score (1-5), pass (bool), issues (list[str]), polish_score, method (str).
    """
    # Check if exempt headless single-component primitive
    if exempt_single_components and isinstance(trajectory, dict):
        task_id = str(trajectory.get("task_id", "")).lower()
        if any(prefix in task_id for prefix in ["shadcn", "ts_instruct", "typescript_instruct"]):
            return {
                "score": 3,
                "max_score": 5,
                "pass": True,
                "polish_score": 3,
                "issues": ["Single-component headless primitive exempt from full-site visual gate"],
                "method": "exempt_headless_primitive",
            }

    layout_archetype = "grid"
    if isinstance(trajectory, dict):
        layout_archetype = trajectory.get("layout_archetype") or "grid"

    # 1. Check if on-disk screenshot exists
    if workspace_dir:
        w_path = Path(workspace_dir)
        screenshot_path = w_path / "screenshot.webp"
        if screenshot_path.exists():
            res = _score_screenshot_heuristic(screenshot_path)
            res["screenshot_path"] = str(screenshot_path)

            # Scan on-disk code for motion & polish quality check
            src_dir = w_path / "src"
            if src_dir.exists():
                src_code = []
                src_css = []
                for p in src_dir.rglob("*.tsx"):
                    try:
                        src_code.append(p.read_text(encoding="utf-8"))
                    except Exception:
                        pass
                for p in src_dir.rglob("*.css"):
                    try:
                        src_css.append(p.read_text(encoding="utf-8"))
                    except Exception:
                        pass
                if src_code or src_css:
                    polish_res = evaluate_motion_polish("\n".join(src_code), "\n".join(src_css), layout_archetype=layout_archetype)
                    res["polish_score"] = polish_res.get("score", 5)
                    res["polish_issues"] = polish_res.get("issues", [])
                    res["has_reduced_motion"] = polish_res.get("has_reduced_motion", True)
                    for p_iss in polish_res.get("issues", []):
                        if p_iss not in res.get("issues", []):
                            res.setdefault("issues", []).append(p_iss)
                    if polish_res.get("score", 5) <= 2:
                        res["score"] = min(res.get("score", 3), 2)
                        res["pass"] = False
            return res

    # Cached scores are claims, not evidence.  Only accept them when accompanied by
    # an explicit verification receipt tied to the current artifact.
    if isinstance(trajectory, dict):
        existing_score = trajectory.get("visual_score")
        existing_polish = trajectory.get("polish_score")
        receipt = trajectory.get("visual_verification")
        verified = (
            trajectory.get("visual_score_verified") is True
            and isinstance(receipt, dict)
            and all(receipt.get(key) for key in (
                "screenshot_sha256", "workspace_sha256", "evaluator_version", "signed_receipt"
            ))
        )
        if verified and isinstance(existing_score, (int, float)) and 1 <= existing_score <= 5:
            eff_score = int(existing_score)
            if isinstance(existing_polish, (int, float)) and existing_polish <= 2:
                eff_score = min(eff_score, 2)
            return {
                "score": eff_score,
                "max_score": 5,
                "pass": eff_score >= threshold,
                "polish_score": existing_polish if existing_polish is not None else eff_score,
                "issues": trajectory.get("visual_issues", []),
                "method": "cached_visual_score",
            }

    # 3. Extract code and CSS from trajectory
    tsx_chunks = []
    css_chunks = []

    if isinstance(trajectory, dict):
        # Direct files dictionary
        files = trajectory.get("files", {})
        if isinstance(files, dict):
            for path, content in files.items():
                if str(path).endswith(".css"):
                    css_chunks.append(content)
                elif str(path).endswith((".tsx", ".jsx")):
                    tsx_chunks.append(content)

        # Messages list in trajectory
        messages = trajectory.get("messages", [])
        if isinstance(messages, list):
            for m in messages:
                content = m.get("content", "") if isinstance(m, dict) else ""
                # Parse <file path="...">...</file>
                file_blocks = re.findall(r'<file\s+path=[\'"]([^\'"]+)[\'"]>(.*?)</file>', content, re.DOTALL)
                for fpath, fbody in file_blocks:
                    if fpath.endswith(".css"):
                        css_chunks.append(fbody)
                    elif fpath.endswith((".tsx", ".jsx")):
                        tsx_chunks.append(fbody)

                # Component tool call write_component / write_site
                component_matches = re.findall(r'<file\s+path=[\'"][^\'"]*\.tsx[\'"]>(.*?)</file>', content, re.DOTALL)
                tsx_chunks.extend(component_matches)

        # Standalone code/css fields
        if trajectory.get("code") and isinstance(trajectory["code"], str):
            tsx_chunks.append(trajectory["code"])
        if trajectory.get("css") and isinstance(trajectory["css"], str):
            css_chunks.append(trajectory["css"])

    elif isinstance(trajectory, str):
        # Could be raw code or JSON string
        try:
            parsed = json.loads(trajectory)
            return score_trajectory_visual(parsed, workspace_dir=workspace_dir, threshold=threshold)
        except Exception:
            tsx_chunks.append(trajectory)

    full_tsx = "\n".join(tsx_chunks)
    full_css = "\n".join(css_chunks)
    result = score_code_visual_heuristic(full_tsx, full_css, layout_archetype=layout_archetype)
    result.setdefault("issues", []).append("No rendered screenshot or verified visual receipt; visual score is code-only and unverified")
    result["visual_verified"] = False
    result["pass"] = False
    return result


def filter_trajectory_visual(
    trajectory: Union[Dict[str, Any], str],
    threshold: int = 3,
    workspace_dir: Optional[Path] = None,
    exempt_single_components: bool = True,
) -> Tuple[bool, dict]:
    """
    Enforces the inference-time visual quality threshold (>= threshold, default 3/5)
    when harvesting training data trajectories.
    Returns: (passes_filter: bool, score_result: dict)
    """
    res = score_trajectory_visual(
        trajectory,
        workspace_dir=workspace_dir,
        threshold=threshold,
        exempt_single_components=exempt_single_components,
    )
    passes = res.get("score", 0) >= threshold
    return passes, res

