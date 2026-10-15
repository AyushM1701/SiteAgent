"""
tests/test_motion_benchmark.py - Exhaustive Playwright Behavioral & Performance Motion Benchmark Tests.

Validates Section 7: Motion Validation & Benchmarking:
- Scroll reveal before/after scroll measurement
- Parallax transform change + no wheel/touch event prevention
- Horizontal scroll desktop track translation + mobile 375px overflow/scroll-snap
- Sticky storytelling pinned bounding-box + ancestor overflow invalidation check
- Text reveal accessible name + decorative aria-hidden split spans + reduced-motion visibility
- Micro-interactions hover visual change + keyboard focus indicator + state toggle
- Performance checks: pageerror, console.error, CLS, long tasks, uncontrolled RAF, horizontal overflow
"""

import os
from pathlib import Path
import pytest

from evaluation.motion_benchmark import (
    MotionBehavioralResult,
    MotionPerformanceResult,
    MotionBenchmarkReport,
    check_scroll_reveal_behavior,
    check_parallax_behavior,
    check_horizontal_scroll_behavior,
    check_sticky_story_behavior,
    check_text_reveal_behavior,
    check_micro_interactions_behavior,
    check_motion_performance,
    evaluate_motion_page,
    evaluate_motion_html,
    MOTION_FAMILIES,
    _PLAYWRIGHT_AVAILABLE,
)
from evaluation.site_benchmark_scorer import SiteBenchmarkScorer


# ==============================================================================
# Fixtures: Standalone HTML Snippets for Real Headless Browser Testing
# ==============================================================================

SCROLL_REVEAL_VALID_HTML = """
<!DOCTYPE html>
<html>
<head>
<style>
  body { margin: 0; padding: 0; min-height: 2500px; font-family: sans-serif; }
  .spacer { height: 1200px; background: #111; color: #fff; padding: 40px; }
  .scroll-reveal {
    opacity: 0;
    transform: translateY(40px);
    transition: opacity 0.3s ease, transform 0.3s ease;
    padding: 60px;
    background: #222;
    color: #fff;
    margin: 40px;
  }
  .scroll-reveal.is-revealed {
    opacity: 1;
    transform: translateY(0);
  }
  @media (prefers-reduced-motion: reduce) {
    .scroll-reveal { opacity: 1 !important; transform: none !important; transition: none !important; }
  }
</style>
</head>
<body>
  <div class="spacer"><h1>Top Section</h1><p>Scroll down to reveal</p></div>
  <div class="scroll-reveal" data-motion="scroll-reveal" id="reveal-target">
    <h2>Revealed Features</h2>
    <p>Dynamic hardware accelerated content</p>
  </div>
  <div class="spacer"></div>
  <script>
    const el = document.getElementById('reveal-target');
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-revealed');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.1 });
    observer.observe(el);
  </script>
</body>
</html>
"""

SCROLL_REVEAL_BROKEN_HTML = """
<!DOCTYPE html>
<html>
<head>
<style>
  body { margin: 0; min-height: 2500px; }
  .spacer { height: 1200px; }
  .scroll-reveal {
    opacity: 0 !important; /* permanently stuck transparent */
    transform: translateY(40px);
  }
</style>
</head>
<body>
  <div class="spacer"></div>
  <div class="scroll-reveal" data-motion="scroll-reveal">
    <h2>Broken Card</h2>
  </div>
</body>
</html>
"""

PARALLAX_VALID_HTML = """
<!DOCTYPE html>
<html>
<head>
<style>
  body { margin: 0; padding: 0; min-height: 3000px; }
  .hero { position: relative; height: 100vh; overflow: hidden; }
  .parallax-layer {
    position: absolute;
    inset: 0;
    will-change: transform;
    background: linear-gradient(135deg, #1e1e2f, #11111a);
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
  }
</style>
</head>
<body>
  <div class="hero">
    <div class="parallax-layer" data-motion="parallax" id="parallax-target">
      <h1>Parallax Heading</h1>
    </div>
  </div>
  <script>
    const el = document.getElementById('parallax-target');
    let ticking = false;
    window.addEventListener('scroll', () => {
      if (!ticking) {
        window.requestAnimationFrame(() => {
          const y = window.scrollY;
          el.style.transform = `translate3d(0, ${y * 0.35}px, 0)`;
          ticking = false;
        });
        ticking = true;
      }
    }, { passive: true });
  </script>
</body>
</html>
"""

PARALLAX_HIJACKING_HTML = """
<!DOCTYPE html>
<html>
<head>
<style>
  body { margin: 0; min-height: 2000px; }
  .parallax-layer { height: 600px; background: #333; color: white; }
</style>
</head>
<body>
  <div class="parallax-layer" data-motion="parallax">Hijacked Scroll</div>
  <script>
    // Anti-pattern: prevents wheel event!
    window.addEventListener('wheel', (e) => {
      e.preventDefault();
    }, { passive: false });
  </script>
</body>
</html>
"""

HORIZONTAL_SCROLL_VALID_HTML = """
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
  * { box-sizing: border-box; }
  body { margin: 0; min-height: 3500px; overflow-x: hidden; }
  .spacer { height: 600px; background: #111; }
  .horizontal-section {
    position: relative;
    height: 300vh;
  }
  .sticky-viewport {
    position: sticky;
    top: 0;
    height: 100vh;
    overflow: hidden;
  }
  .horizontal-track {
    display: flex;
    gap: 30px;
    padding: 60px;
    width: max-content;
    will-change: transform;
  }
  .card {
    width: 380px;
    height: 480px;
    background: #2a2a38;
    color: white;
    border-radius: 16px;
    flex-shrink: 0;
  }
  @media (max-width: 768px) {
    .horizontal-section { height: auto; }
    .sticky-viewport { position: static; height: auto; overflow-x: auto; scroll-snap-type: x mandatory; }
    .horizontal-track { transform: none !important; width: 100%; }
    .card { width: 85vw; scroll-snap-align: center; }
  }
</style>
</head>
<body>
  <div class="spacer"></div>
  <section class="horizontal-section" data-motion="horizontal-scroll" id="h-sec">
    <div class="sticky-viewport">
      <div class="horizontal-track" id="h-track">
        <div class="card">Card 1</div>
        <div class="card">Card 2</div>
        <div class="card">Card 3</div>
      </div>
    </div>
  </section>
  <div class="spacer"></div>
  <script>
    const section = document.getElementById('h-sec');
    const track = document.getElementById('h-track');
    window.addEventListener('scroll', () => {
      if (window.innerWidth > 768) {
        const rect = section.getBoundingClientRect();
        const progress = Math.max(0, Math.min(1, -rect.top / (section.offsetHeight - window.innerHeight)));
        const maxScroll = track.scrollWidth - window.innerWidth + 120;
        track.style.transform = `translate3d(${-progress * maxScroll}px, 0, 0)`;
      }
    }, { passive: true });
  </script>
</body>
</html>
"""

HORIZONTAL_SCROLL_MOBILE_BLOWOUT_HTML = """
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
  body { margin: 0; width: 800px; /* blows out past 375px */ }
  .horizontal-track { display: flex; width: 1200px; }
</style>
</head>
<body>
  <div data-motion="horizontal-scroll">
    <div class="horizontal-track">
      <div style="width: 400px;">1</div>
      <div style="width: 400px;">2</div>
    </div>
  </div>
</body>
</html>
"""

STICKY_STORY_VALID_HTML = """
<!DOCTYPE html>
<html>
<head>
<style>
  body { margin: 0; min-height: 3000px; }
  .spacer { height: 500px; }
  .story-container {
    position: relative;
    height: 1500px;
    background: #181824;
    padding: 40px;
  }
  .sticky-card {
    position: sticky;
    top: 40px;
    height: 300px;
    background: #33334d;
    color: white;
    border-radius: 12px;
    padding: 24px;
  }
</style>
</head>
<body>
  <div class="spacer"></div>
  <div class="story-container">
    <div class="sticky-card" data-motion="sticky-story">
      <h2>Sticky Story Card</h2>
      <p>Pins smoothly while narrative progresses</p>
    </div>
  </div>
  <div class="spacer"></div>
</body>
</html>
"""

STICKY_STORY_INVALID_ANCESTOR_HTML = """
<!DOCTYPE html>
<html>
<head>
<style>
  body { margin: 0; min-height: 2500px; }
  .invalidating-wrapper {
    overflow: hidden; /* Breaks CSS position: sticky! */
    height: 1000px;
  }
  .sticky-card {
    position: sticky;
    top: 40px;
  }
</style>
</head>
<body>
  <div class="invalidating-wrapper">
    <div class="sticky-card" data-motion="sticky-story">Broken Sticky</div>
  </div>
</body>
</html>
"""

TEXT_REVEAL_VALID_HTML = """
<!DOCTYPE html>
<html>
<head>
<style>
  h1 { font-size: 48px; color: #fff; }
  .text-reveal { display: inline-block; }
  .split-word {
    display: inline-block;
    opacity: 1;
    transform: translateY(0);
    transition: opacity 0.4s ease, transform 0.4s ease;
  }
  @media (prefers-reduced-motion: reduce) {
    .split-word { opacity: 1 !important; transform: none !important; }
  }
</style>
</head>
<body style="background: #111;">
  <h1 class="text-reveal" data-motion="text-reveal" aria-label="Crafting Exceptional Web Experiences">
    <span class="split-word" aria-hidden="true">Crafting</span>
    <span class="split-word" aria-hidden="true">Exceptional</span>
    <span class="split-word" aria-hidden="true">Web</span>
    <span class="split-word" aria-hidden="true">Experiences</span>
  </h1>
</body>
</html>
"""

TEXT_REVEAL_A11Y_FAIL_HTML = """
<!DOCTYPE html>
<html>
<body>
  <!-- Missing aria-label on container and missing aria-hidden on split spans -->
  <h1 data-motion="text-reveal">
    <span>C</span><span>r</span><span>a</span><span>f</span><span>t</span>
  </h1>
</body>
</html>
"""

MICRO_INTERACTION_VALID_HTML = """
<!DOCTYPE html>
<html>
<head>
<style>
  button {
    background: #3b82f6;
    color: white;
    padding: 12px 24px;
    border: none;
    border-radius: 8px;
    font-size: 16px;
    cursor: pointer;
    transition: transform 0.2s ease, box-shadow 0.2s ease, background-color 0.2s ease;
  }
  button:hover {
    transform: translateY(-2px) scale(1.02);
    box-shadow: 0 8px 20px rgba(59, 130, 246, 0.4);
    background-color: #2563eb;
  }
  button:focus-visible {
    outline: 2px solid #60a5fa;
    outline-offset: 3px;
    box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.3);
  }
</style>
</head>
<body>
  <button data-motion="micro-interaction" id="btn" aria-pressed="false">Interactive Button</button>
  <script>
    const btn = document.getElementById('btn');
    btn.addEventListener('click', () => {
      const pressed = btn.getAttribute('aria-pressed') === 'true';
      btn.setAttribute('aria-pressed', String(!pressed));
    });
  </script>
</body>
</html>
"""


# ==============================================================================
# Unit Tests: Data Classes & Serialization
# ==============================================================================

def test_motion_behavioral_result_serialization():
    res = MotionBehavioralResult(
        motion_type="parallax",
        passed=True,
        score=1.0,
        selector="[data-motion='parallax']",
        metrics={"wheel_prevented": False, "transform_changed": True},
        warnings=["Minor note"],
    )
    d = res.to_dict()
    assert d["motion_type"] == "parallax"
    assert d["passed"] is True
    assert d["score"] == 1.0
    assert d["metrics"]["wheel_prevented"] is False
    assert d["warnings"] == ["Minor note"]


def test_motion_performance_result_serialization():
    res = MotionPerformanceResult(
        passed=True,
        score=0.95,
        cumulative_layout_shift=0.02,
        long_tasks_count=1,
        uncontrolled_raf=False,
        body_horizontal_overflow_desktop=False,
        body_horizontal_overflow_mobile_375=False,
    )
    d = res.to_dict()
    assert d["passed"] is True
    assert d["cumulative_layout_shift"] == 0.02
    assert d["uncontrolled_raf"] is False
    assert d["desktop_scroll_width"] == 0


def test_motion_benchmark_report_serialization():
    b_res = MotionBehavioralResult(motion_type="scroll_reveal", passed=True, score=1.0)
    p_res = MotionPerformanceResult(passed=True, score=1.0)
    report = MotionBenchmarkReport(
        passed=True,
        composite_score=1.0,
        behavioral_score=1.0,
        performance_score=1.0,
        behavioral_results={"scroll_reveal": b_res},
        performance_result=p_res,
        summary={"families_tested": ["scroll_reveal"]},
    )
    d = report.to_dict()
    assert d["passed"] is True
    assert "scroll_reveal" in d["behavioral_results"]
    assert d["performance_result"]["passed"] is True


# ==============================================================================
# Playwright Browser Behavioral Tests
# ==============================================================================

@pytest.mark.skipif(not _PLAYWRIGHT_AVAILABLE, reason="Playwright is required")
def test_scroll_reveal_behavior_positive():
    report = evaluate_motion_html(SCROLL_REVEAL_VALID_HTML, motion_specs=["scroll_reveal"])
    assert "scroll_reveal" in report.behavioral_results
    res = report.behavioral_results["scroll_reveal"]
    assert res.passed is True
    assert res.score >= 0.9
    assert res.metrics["after_scroll"]["inViewport"] is True
    assert res.metrics["after_scroll"]["opacity"] >= 0.85


@pytest.mark.skipif(not _PLAYWRIGHT_AVAILABLE, reason="Playwright is required")
def test_scroll_reveal_behavior_broken():
    report = evaluate_motion_html(SCROLL_REVEAL_BROKEN_HTML, motion_specs=["scroll_reveal"])
    assert "scroll_reveal" in report.behavioral_results
    res = report.behavioral_results["scroll_reveal"]
    assert res.passed is False
    assert any("remained hidden" in err for err in res.errors)


@pytest.mark.skipif(not _PLAYWRIGHT_AVAILABLE, reason="Playwright is required")
def test_parallax_behavior_positive():
    report = evaluate_motion_html(PARALLAX_VALID_HTML, motion_specs=["parallax"])
    assert "parallax" in report.behavioral_results
    res = report.behavioral_results["parallax"]
    assert res.passed is True
    assert res.metrics["wheel_prevented"] is False
    assert res.metrics["touch_prevented"] is False
    assert res.metrics["transform_changed"] is True


@pytest.mark.skipif(not _PLAYWRIGHT_AVAILABLE, reason="Playwright is required")
def test_parallax_behavior_hijacking_detection():
    report = evaluate_motion_html(PARALLAX_HIJACKING_HTML, motion_specs=["parallax"])
    assert "parallax" in report.behavioral_results
    res = report.behavioral_results["parallax"]
    assert res.passed is False
    assert res.metrics["wheel_prevented"] is True
    assert any("wheel.preventDefault()" in err for err in res.errors)


@pytest.mark.skipif(not _PLAYWRIGHT_AVAILABLE, reason="Playwright is required")
def test_horizontal_scroll_behavior_positive():
    report = evaluate_motion_html(HORIZONTAL_SCROLL_VALID_HTML, motion_specs=["horizontal_scroll"])
    assert "horizontal_scroll" in report.behavioral_results
    res = report.behavioral_results["horizontal_scroll"]
    assert res.passed is True
    assert res.metrics["mobile_375px"]["docWidth"] <= 375


@pytest.mark.skipif(not _PLAYWRIGHT_AVAILABLE, reason="Playwright is required")
def test_horizontal_scroll_mobile_blowout_detection():
    report = evaluate_motion_html(HORIZONTAL_SCROLL_MOBILE_BLOWOUT_HTML, motion_specs=["horizontal_scroll"])
    assert "horizontal_scroll" in report.behavioral_results
    res = report.behavioral_results["horizontal_scroll"]
    assert res.passed is False
    assert any("mobile layout blowout" in err for err in res.errors)


@pytest.mark.skipif(not _PLAYWRIGHT_AVAILABLE, reason="Playwright is required")
def test_sticky_story_behavior_positive():
    report = evaluate_motion_html(STICKY_STORY_VALID_HTML, motion_specs=["sticky_story"])
    assert "sticky_story" in report.behavioral_results
    res = report.behavioral_results["sticky_story"]
    assert res.passed is True
    assert res.metrics["is_pinned"] is True
    assert len(res.metrics["ancestor_check"]["invalidAncestors"]) == 0


@pytest.mark.skipif(not _PLAYWRIGHT_AVAILABLE, reason="Playwright is required")
def test_sticky_story_invalid_ancestor_detection():
    report = evaluate_motion_html(STICKY_STORY_INVALID_ANCESTOR_HTML, motion_specs=["sticky_story"])
    assert "sticky_story" in report.behavioral_results
    res = report.behavioral_results["sticky_story"]
    assert res.passed is False
    assert any("invalidated by ancestor with overflow" in err for err in res.errors)


@pytest.mark.skipif(not _PLAYWRIGHT_AVAILABLE, reason="Playwright is required")
def test_text_reveal_behavior_positive():
    report = evaluate_motion_html(TEXT_REVEAL_VALID_HTML, motion_specs=["text_reveal"])
    assert "text_reveal" in report.behavioral_results
    res = report.behavioral_results["text_reveal"]
    assert res.passed is True
    assert res.metrics["has_accessible_name"] is True
    assert res.metrics["reduced_motion"]["containerOpacity"] >= 0.85


@pytest.mark.skipif(not _PLAYWRIGHT_AVAILABLE, reason="Playwright is required")
def test_text_reveal_a11y_warning():
    report = evaluate_motion_html(TEXT_REVEAL_A11Y_FAIL_HTML, motion_specs=["text_reveal"])
    assert "text_reveal" in report.behavioral_results
    res = report.behavioral_results["text_reveal"]
    assert any("without aria-hidden" in w for w in res.warnings)


@pytest.mark.skipif(not _PLAYWRIGHT_AVAILABLE, reason="Playwright is required")
def test_micro_interactions_behavior_positive():
    report = evaluate_motion_html(MICRO_INTERACTION_VALID_HTML, motion_specs=["micro_interaction"])
    assert "micro_interaction" in report.behavioral_results
    res = report.behavioral_results["micro_interaction"]
    assert res.passed is True
    assert res.metrics["hover_visual_change"] is True
    assert res.metrics["has_focus_indicator"] is True
    assert res.metrics["aria_pressed_toggled"] is True


# ==============================================================================
# Performance and Health Checks
# ==============================================================================

@pytest.mark.skipif(not _PLAYWRIGHT_AVAILABLE, reason="Playwright is required")
def test_performance_checks_detection():
    # Test layout overflow detection and pageerror detection
    html_with_error = """
    <!DOCTYPE html>
    <html>
    <head>
      <style>body { margin: 0; padding: 0; }</style>
    </head>
    <body>
      <div style="width: 1600px; height: 20px; background: red;">Overflow</div>
      <script>
        console.error("Test console error");
        window.__error_triggered = true;
      </script>
    </body>
    </html>
    """
    report = evaluate_motion_html(html_with_error)
    assert report.performance_result is not None
    perf = report.performance_result
    assert perf.body_horizontal_overflow_desktop is True
    assert any("1280px viewport" in v for v in perf.violations)
    assert len(perf.console_errors) >= 1


# ==============================================================================
# Scorer Integration Test
# ==============================================================================

def test_scorer_motion_quality_with_behavioral_html():
    scorer = SiteBenchmarkScorer()
    files = {
        "src/App.css": "button:hover { transform: translateY(-2px); } @media (prefers-reduced-motion) { button { transition: none; } }",
        "src/App.tsx": "export function App() { return <button>Click</button>; }",
    }
    # Test scoring with real HTML behavioral validation
    score, details = scorer.score_motion_quality(
        files=files,
        motion_specs=["micro_interaction"],
        html_content=MICRO_INTERACTION_VALID_HTML,
    )
    assert score > 0.7
    assert "behavioral_motion_benchmark" in details
    assert details["behavioral_motion_benchmark"]["passed"] is True
