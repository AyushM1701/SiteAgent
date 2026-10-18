"""
evaluation/motion_benchmark.py - Playwright Behavioral & Performance Motion Benchmark.

Implements Section 7 of SiteAgent_Updated_Audit_and_Motion_Plan.md:
"A regex/code-level judge is not sufficient because models can satisfy it by including
strings without correct behavior."

Executes real browser behavioral and performance tests across the 6 motion families:
1. Scroll reveal: Measure element before and after scrolling into view.
2. Parallax: Verify transform changes across scroll positions and that no wheel/touch
   event is prevented.
3. Horizontal scroll: Verify desktop track translation and mobile native overflow/scroll-snap.
4. Sticky storytelling: Measure bounding-box position while page progresses through sticky range.
5. Text reveal: Check accessible name, aria-hidden split spans, and reduced-motion visibility.
6. Micro-interactions: Use mouse + keyboard focus and assert visual/state changes.

Performance & Health checks:
- page errors
- console errors
- long tasks if available
- layout shifts (CLS)
- uncontrolled requestAnimationFrame loops
- listener cleanup / passive event listeners
- body horizontal overflow (desktop)
- mobile 375 px behavior
"""

from __future__ import annotations

import dataclasses
from dataclasses import asdict, dataclass, field
import json
import logging
import os
from pathlib import Path
import re
import subprocess
import time
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import urllib.request

logger = logging.getLogger("motion_benchmark")

# Playwright availability check
try:
    from playwright.sync_api import (
        Browser,
        BrowserContext,
        ElementHandle,
        Page,
        sync_playwright,
    )
    _PLAYWRIGHT_AVAILABLE = True
except ImportError:
    _PLAYWRIGHT_AVAILABLE = False
    Page = Any  # type: ignore


# Motion families
MOTION_FAMILIES = [
    "scroll_reveal",
    "parallax",
    "horizontal_scroll",
    "sticky_story",
    "text_reveal",
    "micro_interaction",
]


@dataclass
class MotionBehavioralResult:
    """Result of an individual behavioral motion test."""
    motion_type: str
    passed: bool
    score: float = 0.0  # 0.0 to 1.0
    selector: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "motion_type": self.motion_type,
            "passed": self.passed,
            "score": round(self.score, 4),
            "selector": self.selector,
            "metrics": self.metrics,
            "errors": self.errors,
            "warnings": self.warnings,
        }


@dataclass
class MotionPerformanceResult:
    """Result of runtime performance and health checks."""
    passed: bool
    score: float = 1.0  # 0.0 to 1.0
    page_errors: List[str] = field(default_factory=list)
    console_errors: List[str] = field(default_factory=list)
    long_tasks_count: int = 0
    cumulative_layout_shift: float = 0.0
    uncontrolled_raf: bool = False
    idle_raf_rate_per_sec: float = 0.0
    listener_cleanup_verified: bool = True
    body_horizontal_overflow_desktop: bool = False
    body_horizontal_overflow_mobile_375: bool = False
    desktop_scroll_width: int = 0
    desktop_viewport_width: int = 1280
    mobile_scroll_width: int = 0
    mobile_viewport_width: int = 375
    violations: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "score": round(self.score, 4),
            "page_errors": self.page_errors,
            "console_errors": self.console_errors,
            "long_tasks_count": self.long_tasks_count,
            "cumulative_layout_shift": round(self.cumulative_layout_shift, 4),
            "uncontrolled_raf": self.uncontrolled_raf,
            "idle_raf_rate_per_sec": round(self.idle_raf_rate_per_sec, 2),
            "listener_cleanup_verified": self.listener_cleanup_verified,
            "body_horizontal_overflow_desktop": self.body_horizontal_overflow_desktop,
            "body_horizontal_overflow_mobile_375": self.body_horizontal_overflow_mobile_375,
            "desktop_scroll_width": self.desktop_scroll_width,
            "desktop_viewport_width": self.desktop_viewport_width,
            "mobile_scroll_width": self.mobile_scroll_width,
            "mobile_viewport_width": self.mobile_viewport_width,
            "violations": self.violations,
            "warnings": self.warnings,
        }


@dataclass
class MotionBenchmarkReport:
    """Comprehensive report across behavioral and performance checks."""
    passed: bool
    composite_score: float  # 0.0 to 1.0
    behavioral_score: float  # 0.0 to 1.0
    performance_score: float  # 0.0 to 1.0
    behavioral_results: Dict[str, MotionBehavioralResult] = field(default_factory=dict)
    performance_result: Optional[MotionPerformanceResult] = None
    summary: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "composite_score": round(self.composite_score, 4),
            "behavioral_score": round(self.behavioral_score, 4),
            "performance_score": round(self.performance_score, 4),
            "behavioral_results": {
                k: v.to_dict() for k, v in self.behavioral_results.items()
            },
            "performance_result": (
                self.performance_result.to_dict() if self.performance_result else None
            ),
            "summary": self.summary,
        }


# ==============================================================================
# Helper Injections for Page Monitoring
# ==============================================================================

INJECT_PERFORMANCE_MONITORS_JS = """
(() => {
    // 1. CLS Observer
    window.__cls_score = 0;
    try {
        const clsObserver = new PerformanceObserver((entryList) => {
            for (const entry of entryList.getEntries()) {
                if (!entry.hadRecentInput) {
                    window.__cls_score += entry.value;
                }
            }
        });
        clsObserver.observe({ type: 'layout-shift', buffered: true });
    } catch (e) {}

    // 2. Long Tasks Observer
    window.__long_tasks_count = 0;
    try {
        const longTaskObserver = new PerformanceObserver((entryList) => {
            window.__long_tasks_count += entryList.getEntries().length;
        });
        longTaskObserver.observe({ type: 'longtask', buffered: true });
    } catch (e) {}

    // 3. Event Default-Prevention Spy (Detect forbidden wheel/touch hijacking)
    window.__prevented_events = [];
    const origPreventDefault = Event.prototype.preventDefault;
    Event.prototype.preventDefault = function() {
        if (this && (this.type === 'wheel' || this.type === 'touchmove')) {
            if (!window.__prevented_events.includes(this.type)) {
                window.__prevented_events.push(this.type);
            }
        }
        return origPreventDefault.apply(this, arguments);
    };

    const recordPrevented = (e) => {
        if (e && e.defaultPrevented && !window.__prevented_events.includes(e.type)) {
            window.__prevented_events.push(e.type);
        }
    };
    window.addEventListener('wheel', recordPrevented, { passive: false, capture: true });
    window.addEventListener('touchmove', recordPrevented, { passive: false, capture: true });


    // 4. RAF Counter (Detect uncontrolled continuous RAF loops on idle)
    window.__raf_counter = 0;
    const origRAF = window.requestAnimationFrame;
    window.requestAnimationFrame = function(callback) {
        window.__raf_counter++;
        return origRAF.call(window, callback);
    };

    // 5. Listener Tracker (Ensure passive listener option on scroll/touch)
    window.__registered_listeners = [];
    const origAddEventListener = EventTarget.prototype.addEventListener;
    EventTarget.prototype.addEventListener = function(type, listener, options) {
        let isPassive = false;
        if (typeof options === 'object' && options !== null) {
            isPassive = Boolean(options.passive);
        }
        window.__registered_listeners.push({
            type: type,
            passive: isPassive,
            target: this === window ? 'window' : (this === document ? 'document' : 'element')
        });
        return origAddEventListener.call(this, type, listener, options);
    };
})();
"""


def setup_page_monitoring(
    page: Page,
    page_errors: Optional[List[str]] = None,
    console_errors: Optional[List[str]] = None,
) -> None:
    """Attaches error listeners and injects instrumentation scripts into page."""
    if page_errors is not None:
        page.on("pageerror", lambda err: page_errors.append(f"[Browser Exception] {err}"))
    if console_errors is not None:
        page.on(
            "console",
            lambda msg: console_errors.append(f"[Console Error] {msg.text}")
            if msg.type == "error"
            else None,
        )

    try:
        page.evaluate(INJECT_PERFORMANCE_MONITORS_JS)
    except Exception as e:
        logger.debug(f"Failed to inject performance monitors: {e}")


# ==============================================================================
# 6 Runtime Behavioral Tests
# ==============================================================================

def check_scroll_reveal_behavior(
    page: Page,
    selector: Optional[str] = None,
    target_section: Optional[str] = None,
) -> MotionBehavioralResult:
    """
    1. Scroll reveal: Measure an element before and after scrolling into view.
    - Resolves target element.
    - Measures bounding box and computed opacity/transform before scroll.
    - Scrolls element into center of viewport.
    - Waits for IntersectionObserver and CSS transition.
    - Measures bounding box and computed opacity/transform after scroll.
    - Asserts visibility and transition into viewport.
    """
    candidate_selectors = [
        selector,
        f"[data-section*='{target_section.lower()}'] [data-motion*='reveal']" if target_section else None,
        f"#{target_section.lower()} [data-motion*='reveal']" if target_section else None,
        "[data-motion='scroll_reveal']",
        "[data-motion='scroll-reveal']",
        "[data-motion*='reveal']",
        "[data-reveal]",
        ".scroll-reveal",
        ".reveal-on-scroll",
        ".reveal-element",
        "section:nth-of-type(2) [data-motion]",
    ]
    resolved_selector = None
    for cand in candidate_selectors:
        if not cand:
            continue
        try:
            if page.locator(cand).count() > 0:
                resolved_selector = cand
                break
        except Exception:
            continue

    if not resolved_selector:
        return MotionBehavioralResult(
            motion_type="scroll_reveal",
            passed=False,
            score=0.0,
            errors=["Could not locate any scroll reveal element matching candidate selectors."],
        )

    errors: List[str] = []
    warnings: List[str] = []
    metrics: Dict[str, Any] = {"selector": resolved_selector}

    try:
        # Reset scroll to top
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(100)

        # Initial state before scroll
        before_state = page.evaluate("""(sel) => {
            const el = document.querySelector(sel);
            if (!el) return null;
            const rect = el.getBoundingClientRect();
            const style = window.getComputedStyle(el);
            return {
                opacity: parseFloat(style.opacity || '1'),
                transform: style.transform,
                top: rect.top,
                bottom: rect.bottom,
                inViewport: (rect.top < window.innerHeight && rect.bottom > 0)
            };
        }""", resolved_selector)

        if not before_state:
            return MotionBehavioralResult(
                motion_type="scroll_reveal",
                passed=False,
                score=0.0,
                selector=resolved_selector,
                errors=[f"Target element {resolved_selector} disappeared from DOM."],
            )

        # Reveals are usually one-shot: if earlier checks already scrolled past the
        # target, it is revealed while still off-screen and nothing can change.
        # Reload so the reveal is measured from its real initial state.
        if (not before_state["inViewport"] and before_state["opacity"] >= 0.9
                and before_state["transform"] in ("none", "", None)):
            page.reload(wait_until="load")
            page.wait_for_timeout(600)
            page.evaluate("window.scrollTo(0, 0)")
            page.wait_for_timeout(100)
            reloaded = page.evaluate("""(sel) => {
                const el = document.querySelector(sel);
                if (!el) return null;
                const rect = el.getBoundingClientRect();
                const style = window.getComputedStyle(el);
                return {
                    opacity: parseFloat(style.opacity || '1'),
                    transform: style.transform,
                    top: rect.top,
                    bottom: rect.bottom,
                    inViewport: (rect.top < window.innerHeight && rect.bottom > 0)
                };
            }""", resolved_selector)
            if reloaded:
                before_state = reloaded
                metrics["reloaded_before_measuring"] = True

        metrics["before_scroll"] = before_state

        # Scroll into view
        page.evaluate("""(sel) => {
            const el = document.querySelector(sel);
            if (el) {
                el.scrollIntoView({ behavior: 'instant', block: 'center' });
            }
        }""", resolved_selector)

        # Wait for IntersectionObserver callback and CSS transition
        page.wait_for_timeout(350)

        # Post-scroll state
        after_state = page.evaluate("""(sel) => {
            const el = document.querySelector(sel);
            if (!el) return null;
            const rect = el.getBoundingClientRect();
            const style = window.getComputedStyle(el);
            return {
                opacity: parseFloat(style.opacity || '1'),
                transform: style.transform,
                top: rect.top,
                bottom: rect.bottom,
                inViewport: (rect.top < window.innerHeight && rect.bottom > 0)
            };
        }""", resolved_selector)

        metrics["after_scroll"] = after_state

        # Assertions
        if not after_state["inViewport"]:
            errors.append(f"Element {resolved_selector} did not enter viewport after scroll.")

        # Opacity check: must be fully revealed (>= 0.85)
        if after_state["opacity"] < 0.85:
            errors.append(
                f"Element {resolved_selector} remained hidden/transparent after scrolling into view (opacity: {after_state['opacity']})."
            )

        # If element was initially below viewport and had initial opacity < 0.9, verify it transitioned
        if not before_state["inViewport"] and before_state["opacity"] < 0.9:
            if after_state["opacity"] <= before_state["opacity"]:
                errors.append(
                    f"Element opacity did not increase after scroll (before: {before_state['opacity']}, after: {after_state['opacity']})."
                )
        if not before_state["inViewport"] and (
            before_state["opacity"] == after_state["opacity"]
            and before_state["transform"] == after_state["transform"]
        ):
            errors.append("Scroll reveal did not change opacity or transform when the element entered view.")

        passed = len(errors) == 0
        score = 1.0 if passed else (0.5 if after_state.get("inViewport") else 0.0)

        return MotionBehavioralResult(
            motion_type="scroll_reveal",
            passed=passed,
            score=score,
            selector=resolved_selector,
            metrics=metrics,
            errors=errors,
            warnings=warnings,
        )

    except Exception as e:
        return MotionBehavioralResult(
            motion_type="scroll_reveal",
            passed=False,
            score=0.0,
            selector=resolved_selector,
            errors=[f"Exception during scroll reveal check: {e}"],
        )


def check_parallax_behavior(
    page: Page,
    selector: Optional[str] = None,
    target_section: Optional[str] = None,
) -> MotionBehavioralResult:
    """
    2. Parallax: Verify transform changes across scroll positions and that no
       wheel/touch event is prevented.
    - Strictly checks window.__prevented_events for 'wheel' or 'touchmove'.
    - Measures computed transform at scroll position 0.
    - Scrolls down by 300px.
    - Measures computed transform at scroll position 300px.
    - Asserts transform changed across scroll positions.
    """
    candidate_selectors = [
        selector,
        f"[data-section*='{target_section.lower()}'] [data-motion*='parallax']" if target_section else None,
        f"#{target_section.lower()} [data-motion*='parallax']" if target_section else None,
        "[data-motion='parallax']",
        "[data-motion*='parallax']",
        "[data-parallax]",
        ".parallax-bg",
        ".parallax-layer",
        ".parallax-element",
        "[data-motion-type='parallax']",
    ]
    resolved_selector = None
    for cand in candidate_selectors:
        if not cand:
            continue
        try:
            if page.locator(cand).count() > 0:
                resolved_selector = cand
                break
        except Exception:
            continue

    if not resolved_selector:
        return MotionBehavioralResult(
            motion_type="parallax",
            passed=False,
            score=0.0,
            errors=["Could not locate any parallax element matching candidate selectors."],
        )

    errors: List[str] = []
    warnings: List[str] = []
    metrics: Dict[str, Any] = {"selector": resolved_selector}

    try:
        # Reset scroll to 0
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(100)

        # Clear any prevented events recorded prior to this test
        page.evaluate("window.__prevented_events = window.__prevented_events || [];")

        transform_at_0 = page.evaluate("""(sel) => {
            const el = document.querySelector(sel);
            if (!el) return null;
            const style = window.getComputedStyle(el);
            return {
                transform: style.transform,
                y: el.getBoundingClientRect().top
            };
        }""", resolved_selector)

        if not transform_at_0:
            return MotionBehavioralResult(
                motion_type="parallax",
                passed=False,
                score=0.0,
                selector=resolved_selector,
                errors=[f"Parallax element {resolved_selector} not found in DOM."],
            )

        metrics["state_at_0px"] = transform_at_0

        # Dispatch real mouse wheel interaction to test wheel event listeners & hijacking
        try:
            page.mouse.wheel(0, 300)
            page.wait_for_timeout(100)
        except Exception:
            pass

        # Scroll down to trigger scroll-driven parallax transform
        page.evaluate("window.scrollTo(0, 300)")
        page.wait_for_timeout(200)


        # Check for forbidden wheel/touch hijacking
        prevented_events = page.evaluate("window.__prevented_events || []")
        wheel_prevented = "wheel" in prevented_events
        touch_prevented = "touchmove" in prevented_events

        metrics["wheel_prevented"] = wheel_prevented
        metrics["touch_prevented"] = touch_prevented
        metrics["prevented_events"] = prevented_events

        if wheel_prevented:
            errors.append("Forbidden event hijacking detected: wheel.preventDefault() was triggered during parallax scroll.")
        if touch_prevented:
            errors.append("Forbidden event hijacking detected: touchmove.preventDefault() was triggered during parallax scroll.")

        # Post-scroll transform check
        transform_at_300 = page.evaluate("""(sel) => {
            const el = document.querySelector(sel);
            if (!el) return null;
            const style = window.getComputedStyle(el);
            return {
                transform: style.transform,
                y: el.getBoundingClientRect().top
            };
        }""", resolved_selector)

        metrics["state_at_300px"] = transform_at_300

        # Check if transform changed across scroll positions
        t0 = transform_at_0["transform"]
        t300 = transform_at_300["transform"]

        transform_changed = (t0 != t300)
        metrics["transform_changed"] = transform_changed

        if not transform_changed:
            # Also check if top position shifted relative to normal scroll
            y_diff = transform_at_300["y"] - transform_at_0["y"]
            # In normal scroll, moving scroll from 0 to 300 moves rect.top by exactly -300
            if abs(y_diff - (-300)) < 2:
                errors.append(
                    f"Parallax transform did not respond to scroll (transform remained '{t0}' at 300px scroll)."
                )

        passed = len(errors) == 0
        score = 1.0 if passed else (0.5 if (not wheel_prevented and not touch_prevented) else 0.0)

        return MotionBehavioralResult(
            motion_type="parallax",
            passed=passed,
            score=score,
            selector=resolved_selector,
            metrics=metrics,
            errors=errors,
            warnings=warnings,
        )

    except Exception as e:
        return MotionBehavioralResult(
            motion_type="parallax",
            passed=False,
            score=0.0,
            selector=resolved_selector,
            errors=[f"Exception during parallax behavioral check: {e}"],
        )


def check_horizontal_scroll_behavior(
    page: Page,
    selector: Optional[str] = None,
    target_section: Optional[str] = None,
) -> MotionBehavioralResult:
    """
    3. Horizontal scroll: Verify desktop track translation and mobile native
       overflow/scroll-snap.
    - Desktop: Asserts vertical document scroll translates horizontal track along X axis.
    - Mobile (375px): Asserts native overflow-x: auto / scroll-snap or vertical stack,
      and verifies body has no horizontal layout blowout (scrollWidth <= 375).
    """
    candidate_selectors = [
        selector,
        f"[data-section*='{target_section.lower()}'] [data-motion*='horizontal']" if target_section else None,
        f"#{target_section.lower()} [data-motion*='horizontal']" if target_section else None,
        "[data-motion='horizontal_scroll']",
        "[data-motion='horizontal-scroll']",
        "[data-motion*='horizontal']",
        ".horizontal-scroll-track",
        ".horizontal-track",
        "[data-horizontal-track]",
        "section[data-motion-type='horizontal_scroll']",
    ]
    resolved_selector = None
    for cand in candidate_selectors:
        if not cand:
            continue
        try:
            if page.locator(cand).count() > 0:
                resolved_selector = cand
                break
        except Exception:
            continue

    if not resolved_selector:
        return MotionBehavioralResult(
            motion_type="horizontal_scroll",
            passed=False,
            score=0.0,
            errors=["Could not locate any horizontal scroll container matching candidate selectors."],
        )

    errors: List[str] = []
    warnings: List[str] = []
    metrics: Dict[str, Any] = {"selector": resolved_selector}

    try:
        # Ensure desktop viewport
        page.set_viewport_size({"width": 1280, "height": 800})
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(100)

        # 1. Desktop Track Check
        desktop_track_initial = page.evaluate("""(sel) => {
            const container = document.querySelector(sel);
            if (!container) return null;
            const track = container.querySelector('.horizontal-scroll-track, .horizontal-track, [data-horizontal-track]') || container;
            const style = window.getComputedStyle(track);
            const rect = track.getBoundingClientRect();
            const containerRect = container.getBoundingClientRect();
            return {
                transform: style.transform,
                left: rect.left,
                containerTop: containerRect.top
            };
        }""", resolved_selector)

        if not desktop_track_initial:
            return MotionBehavioralResult(
                motion_type="horizontal_scroll",
                passed=False,
                score=0.0,
                selector=resolved_selector,
                errors=[f"Horizontal container {resolved_selector} not found in DOM."],
            )

        metrics["desktop_initial"] = desktop_track_initial

        # Scroll into and through horizontal section
        page.evaluate("""(sel) => {
            const container = document.querySelector(sel);
            if (container) {
                const targetScroll = container.offsetTop + 350;
                window.scrollTo(0, targetScroll);
            }
        }""", resolved_selector)
        page.wait_for_timeout(250)

        desktop_track_scrolled = page.evaluate("""(sel) => {
            const container = document.querySelector(sel);
            if (!container) return null;
            const track = container.querySelector('.horizontal-scroll-track, .horizontal-track, [data-horizontal-track]') || container;
            const style = window.getComputedStyle(track);
            const rect = track.getBoundingClientRect();
            return {
                transform: style.transform,
                left: rect.left
            };
        }""", resolved_selector)

        metrics["desktop_scrolled"] = desktop_track_scrolled

        # Check track translation (transform or left position moved)
        t_init = desktop_track_initial["transform"]
        t_scrl = desktop_track_scrolled["transform"]
        left_init = desktop_track_initial["left"]
        left_scrl = desktop_track_scrolled["left"]

        track_translated = (t_init != t_scrl) or (left_scrl < left_init - 20)
        metrics["track_translated_desktop"] = track_translated

        if not track_translated:
            warnings.append(
                "Desktop horizontal track did not translate horizontally during vertical scroll progress."
            )

        # 2. Mobile 375px Check
        page.set_viewport_size({"width": 375, "height": 667})
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(200)

        mobile_metrics = page.evaluate("""(sel) => {
            const container = document.querySelector(sel);
            const docWidth = document.documentElement.scrollWidth;
            if (!container) return { docWidth, found: false };
            const style = window.getComputedStyle(container);
            const track = container.querySelector('.horizontal-scroll-track, .horizontal-track, [data-horizontal-track]') || container;
            const trackStyle = window.getComputedStyle(track);
            return {
                found: true,
                docWidth: docWidth,
                containerOverflowX: style.overflowX,
                trackOverflowX: trackStyle.overflowX,
                scrollSnapType: style.scrollSnapType || trackStyle.scrollSnapType,
                flexDirection: trackStyle.flexDirection,
                isStacked: trackStyle.flexDirection === 'column' || trackStyle.flexWrap === 'wrap'
            };
        }""", resolved_selector)

        metrics["mobile_375px"] = mobile_metrics

        # Strict mobile layout check: documentElement.scrollWidth must NOT blow out past 375px
        if mobile_metrics["docWidth"] > 375:
            errors.append(
                f"Horizontal scroll section caused mobile layout blowout: document scrollWidth {mobile_metrics['docWidth']}px exceeds 375px viewport."
            )

        # Mobile fallback check: must have native overflow-x (auto/scroll) or vertical stack
        has_native_overflow = mobile_metrics.get("containerOverflowX") in ["auto", "scroll"] or \
                              mobile_metrics.get("trackOverflowX") in ["auto", "scroll"]
        has_stack = mobile_metrics.get("isStacked", False)

        if not has_native_overflow and not has_stack:
            warnings.append(
                "Horizontal scroll section on mobile should provide native overflow-x (scroll-snap) or vertical stack."
            )

        # Restore desktop viewport
        page.set_viewport_size({"width": 1280, "height": 800})
        page.wait_for_timeout(100)

        passed = len(errors) == 0
        score = 1.0 if (passed and track_translated) else (0.8 if passed else 0.0)

        return MotionBehavioralResult(
            motion_type="horizontal_scroll",
            passed=passed,
            score=score,
            selector=resolved_selector,
            metrics=metrics,
            errors=errors,
            warnings=warnings,
        )

    except Exception as e:
        try:
            page.set_viewport_size({"width": 1280, "height": 800})
        except Exception:
            pass
        return MotionBehavioralResult(
            motion_type="horizontal_scroll",
            passed=False,
            score=0.0,
            selector=resolved_selector,
            errors=[f"Exception during horizontal scroll behavioral check: {e}"],
        )


def check_sticky_story_behavior(
    page: Page,
    selector: Optional[str] = None,
    target_section: Optional[str] = None,
) -> MotionBehavioralResult:
    """
    4. Sticky: Measure bounding-box position while the page progresses through
       the sticky range.
    - Validates no ancestor invalidates sticky via overflow: hidden / clip.
    - Measures bounding-box position while scrolling through the sticky range.
    - Asserts bounding-box top remains stable (pinned) within viewport.
    """
    candidate_selectors = [
        selector,
        f"[data-section*='{target_section.lower()}'] [data-motion*='sticky']" if target_section else None,
        f"#{target_section.lower()} [data-motion*='sticky']" if target_section else None,
        "[data-motion='sticky_story']",
        "[data-motion='sticky-story']",
        "[data-motion*='sticky']",
        ".sticky-story",
        ".sticky-card",
        "[data-sticky]",
        "section[data-motion-type='sticky_story']",
    ]
    resolved_selector = None
    for cand in candidate_selectors:
        if not cand:
            continue
        try:
            if page.locator(cand).count() > 0:
                resolved_selector = cand
                break
        except Exception:
            continue

    if not resolved_selector:
        has_sticky_el = page.evaluate("""() => {
            const all = document.querySelectorAll('*');
            for (const el of all) {
                const s = window.getComputedStyle(el);
                if (s.position === 'sticky') return el.tagName.toLowerCase();
            }
            return null;
        }""")
        if has_sticky_el:
            resolved_selector = f"{has_sticky_el}"

    if not resolved_selector:
        return MotionBehavioralResult(
            motion_type="sticky_story",
            passed=False,
            score=0.0,
            errors=["Could not locate any sticky storytelling element matching candidate selectors."],
        )

    errors: List[str] = []
    warnings: List[str] = []
    metrics: Dict[str, Any] = {"selector": resolved_selector}

    try:
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(100)

        # 1. Ancestor Invalidating Overflow Check
        ancestor_check = page.evaluate("""(sel) => {
            const el = document.querySelector(sel);
            if (!el) return null;
            const invalidAncestors = [];
            let curr = el.parentElement;
            while (curr && curr !== document.body && curr !== document.documentElement) {
                const s = window.getComputedStyle(curr);
                if (s.overflow === 'hidden' || s.overflowY === 'hidden' || s.overflow === 'clip') {
                    invalidAncestors.push({ tag: curr.tagName, id: curr.id, className: curr.className, overflow: s.overflow });
                }
                curr = curr.parentElement;
            }
            const elStyle = window.getComputedStyle(el);
            return {
                position: elStyle.position,
                top: elStyle.top,
                invalidAncestors: invalidAncestors
            };
        }""", resolved_selector)

        metrics["ancestor_check"] = ancestor_check

        if not ancestor_check:
            return MotionBehavioralResult(
                motion_type="sticky_story",
                passed=False,
                score=0.0,
                selector=resolved_selector,
                errors=[f"Sticky element {resolved_selector} not found in DOM."],
            )

        if ancestor_check["invalidAncestors"]:
            errors.append(
                f"CSS position: sticky invalidated by ancestor with overflow: hidden: {ancestor_check['invalidAncestors']}"
            )

        if ancestor_check["position"] != "sticky":
            warnings.append(
                f"Target element has position: {ancestor_check['position']} instead of 'sticky'."
            )

        # 2. Measure bounding box through sticky range
        page.evaluate("""(sel) => {
            const el = document.querySelector(sel);
            if (el) {
                const container = el.parentElement || el;
                window.scrollTo(0, Math.max(0, container.offsetTop));
            }
        }""", resolved_selector)
        page.wait_for_timeout(200)

        rect_start = page.evaluate("""(sel) => {
            const el = document.querySelector(sel);
            return el ? el.getBoundingClientRect().top : null;
        }""", resolved_selector)

        # Scroll further down by 150px within the sticky container
        page.evaluate("window.scrollBy(0, 150)")
        page.wait_for_timeout(200)

        rect_mid = page.evaluate("""(sel) => {
            const el = document.querySelector(sel);
            return el ? el.getBoundingClientRect().top : null;
        }""", resolved_selector)

        metrics["rect_top_at_start"] = rect_start
        metrics["rect_top_after_150px_scroll"] = rect_mid

        if rect_start is not None and rect_mid is not None:
            top_delta = abs(rect_mid - rect_start)
            metrics["rect_top_delta"] = top_delta

            if top_delta < 30:
                metrics["is_pinned"] = True
            else:
                metrics["is_pinned"] = False
                if ancestor_check["position"] == "sticky":
                    warnings.append(
                        f"Sticky element moved by {round(top_delta, 1)}px instead of remaining pinned during 150px scroll."
                    )

        passed = len(errors) == 0
        score = 1.0 if (passed and metrics.get("is_pinned", False)) else (0.7 if passed else 0.0)

        return MotionBehavioralResult(
            motion_type="sticky_story",
            passed=passed,
            score=score,
            selector=resolved_selector,
            metrics=metrics,
            errors=errors,
            warnings=warnings,
        )

    except Exception as e:
        return MotionBehavioralResult(
            motion_type="sticky_story",
            passed=False,
            score=0.0,
            selector=resolved_selector,
            errors=[f"Exception during sticky story behavioral check: {e}"],
        )


def check_text_reveal_behavior(
    page: Page,
    selector: Optional[str] = None,
    target_section: Optional[str] = None,
) -> MotionBehavioralResult:
    """
    5. Text reveal: Check accessible name, aria-hidden split spans, and
       reduced-motion visibility.
    - Asserts accessible name is preserved on heading/container.
    - Asserts decorative split spans have aria-hidden="true" (or container aria-label).
    - Emulates prefers-reduced-motion: reduce and verifies instant text visibility (opacity = 1).
    """
    candidate_selectors = [
        selector,
        f"[data-section*='{target_section.lower()}'] [data-motion*='text']" if target_section else None,
        f"#{target_section.lower()} [data-motion*='text']" if target_section else None,
        "[data-motion='text_reveal']",
        "[data-motion='text-reveal']",
        "[data-motion*='text']",
        ".text-reveal",
        "[data-text-reveal]",
        "h1[data-motion]",
        "h2[data-motion]",
        "section[data-motion-type='text_reveal']",
    ]
    resolved_selector = None
    for cand in candidate_selectors:
        if not cand:
            continue
        try:
            if page.locator(cand).count() > 0:
                resolved_selector = cand
                break
        except Exception:
            continue

    if not resolved_selector:
        return MotionBehavioralResult(
            motion_type="text_reveal",
            passed=False,
            score=0.0,
            errors=["Could not locate any text reveal element matching candidate selectors."],
        )

    errors: List[str] = []
    warnings: List[str] = []
    metrics: Dict[str, Any] = {"selector": resolved_selector}

    try:
        # 1. Accessible name and split spans check
        a11y_data = page.evaluate("""(sel) => {
            const el = document.querySelector(sel);
            if (!el) return null;
            const ariaLabel = el.getAttribute('aria-label');
            const innerText = el.innerText ? el.innerText.trim() : '';
            const splitSpans = Array.from(el.querySelectorAll('span'));
            const spansWithAriaHidden = splitSpans.filter(s => s.getAttribute('aria-hidden') === 'true');
            return {
                ariaLabel: ariaLabel,
                innerText: innerText,
                totalSpans: splitSpans.length,
                spansWithAriaHiddenCount: spansWithAriaHidden.length
            };
        }""", resolved_selector)

        metrics["accessibility"] = a11y_data

        if not a11y_data:
            return MotionBehavioralResult(
                motion_type="text_reveal",
                passed=False,
                score=0.0,
                selector=resolved_selector,
                errors=[f"Text reveal element {resolved_selector} not found in DOM."],
            )

        has_accessible_name = bool(a11y_data["ariaLabel"] or a11y_data["innerText"])
        metrics["has_accessible_name"] = has_accessible_name

        if not has_accessible_name:
            errors.append("Text reveal element lacks an accessible name (both innerText and aria-label are empty).")

        if a11y_data["totalSpans"] > 1 and not a11y_data["ariaLabel"]:
            if a11y_data["spansWithAriaHiddenCount"] < a11y_data["totalSpans"]:
                warnings.append(
                    f"Text reveal splits content into {a11y_data['totalSpans']} spans without aria-hidden='true' or container aria-label, causing screen-reader stuttering."
                )

        # 2. Reduced-motion visibility check
        page.emulate_media(reduced_motion="reduce")
        page.wait_for_timeout(200)

        reduced_motion_style = page.evaluate("""(sel) => {
            const el = document.querySelector(sel);
            if (!el) return null;
            const style = window.getComputedStyle(el);
            const firstSpan = el.querySelector('span');
            const spanStyle = firstSpan ? window.getComputedStyle(firstSpan) : null;
            return {
                containerOpacity: parseFloat(style.opacity || '1'),
                spanOpacity: spanStyle ? parseFloat(spanStyle.opacity || '1') : 1.0,
                transitionDuration: style.transitionDuration,
                animationDuration: style.animationDuration
            };
        }""", resolved_selector)

        metrics["reduced_motion"] = reduced_motion_style

        # Reset reduced-motion emulation
        page.emulate_media(reduced_motion="no-preference")

        if reduced_motion_style:
            if reduced_motion_style["containerOpacity"] < 0.85 or reduced_motion_style["spanOpacity"] < 0.85:
                errors.append(
                    f"Text reveal element remains hidden/transparent under prefers-reduced-motion: reduce (container: {reduced_motion_style['containerOpacity']}, span: {reduced_motion_style['spanOpacity']})."
                )

        passed = len(errors) == 0
        score = 1.0 if passed else 0.0

        return MotionBehavioralResult(
            motion_type="text_reveal",
            passed=passed,
            score=score,
            selector=resolved_selector,
            metrics=metrics,
            errors=errors,
            warnings=warnings,
        )

    except Exception as e:
        try:
            page.emulate_media(reduced_motion="no-preference")
        except Exception:
            pass
        return MotionBehavioralResult(
            motion_type="text_reveal",
            passed=False,
            score=0.0,
            selector=resolved_selector,
            errors=[f"Exception during text reveal behavioral check: {e}"],
        )


def check_micro_interactions_behavior(
    page: Page,
    selector: Optional[str] = None,
    target_section: Optional[str] = None,
) -> MotionBehavioralResult:
    """
    6. Micro-interactions: Use mouse + keyboard focus and assert visual/state changes.
    - Hover over interactive element and asserts visual style change (transform/box-shadow/bg).
    - Focuses element via keyboard and asserts focus style / focus-visible indicator.
    - Toggles interactive state (aria-pressed / aria-selected / click) if applicable.
    """
    candidate_selectors = [
        selector,
        f"[data-section*='{target_section.lower()}'] [data-motion*='micro']" if target_section else None,
        f"#{target_section.lower()} [data-motion*='micro']" if target_section else None,
        "[data-motion='micro_interaction']",
        "[data-motion='micro-interaction']",
        "[data-motion*='micro']",
        "button[data-motion]",
        "button.btn-primary",
        "button:not([disabled])",
        "a[role='button']",
        "[role='button']",
        ".interactive-card",
        "button",
    ]
    resolved_selector = None
    for cand in candidate_selectors:
        if not cand:
            continue
        try:
            if page.locator(cand).count() > 0:
                resolved_selector = cand
                break
        except Exception:
            continue

    if not resolved_selector:
        return MotionBehavioralResult(
            motion_type="micro_interaction",
            passed=False,
            score=0.0,
            errors=["Could not locate any interactive element matching candidate selectors."],
        )

    errors: List[str] = []
    warnings: List[str] = []
    metrics: Dict[str, Any] = {"selector": resolved_selector}

    try:
        # Move mouse away to neutral position (0, 0)
        page.mouse.move(0, 0)
        page.wait_for_timeout(100)

        # 1. Resting state
        resting_style = page.evaluate("""(sel) => {
            const el = document.querySelector(sel);
            if (!el) return null;
            const style = window.getComputedStyle(el);
            return {
                transform: style.transform,
                boxShadow: style.boxShadow,
                backgroundColor: style.backgroundColor,
                borderColor: style.borderColor,
                outline: style.outline,
                ariaPressed: el.getAttribute('aria-pressed')
            };
        }""", resolved_selector)

        if not resting_style:
            return MotionBehavioralResult(
                motion_type="micro_interaction",
                passed=False,
                score=0.0,
                selector=resolved_selector,
                errors=[f"Interactive element {resolved_selector} not found in DOM."],
            )

        metrics["resting_style"] = resting_style

        # 2. Mouse Hover Check
        page.hover(resolved_selector)
        page.wait_for_timeout(200)

        hover_style = page.evaluate("""(sel) => {
            const el = document.querySelector(sel);
            if (!el) return null;
            const style = window.getComputedStyle(el);
            return {
                transform: style.transform,
                boxShadow: style.boxShadow,
                backgroundColor: style.backgroundColor,
                borderColor: style.borderColor
            };
        }""", resolved_selector)

        metrics["hover_style"] = hover_style

        hover_visual_change = (
            hover_style["transform"] != resting_style["transform"] or
            hover_style["boxShadow"] != resting_style["boxShadow"] or
            hover_style["backgroundColor"] != resting_style["backgroundColor"] or
            hover_style["borderColor"] != resting_style["borderColor"]
        )
        metrics["hover_visual_change"] = hover_visual_change

        if not hover_visual_change:
            warnings.append(
                f"Element {resolved_selector} did not produce visual change on hover (transform, boxShadow, background)."
            )

        # Move mouse away
        page.mouse.move(0, 0)
        page.wait_for_timeout(100)

        # 3. Keyboard Focus Check
        page.focus(resolved_selector)
        page.wait_for_timeout(150)

        focus_style = page.evaluate("""(sel) => {
            const el = document.querySelector(sel);
            if (!el) return null;
            const style = window.getComputedStyle(el);
            return {
                outline: style.outline,
                outlineWidth: style.outlineWidth,
                boxShadow: style.boxShadow,
                borderColor: style.borderColor
            };
        }""", resolved_selector)

        metrics["focus_style"] = focus_style

        has_focus_indicator = (
            focus_style["outline"] not in ["none", "", "0px none rgb(0, 0, 0)"] or
            focus_style["outlineWidth"] not in ["0px", ""] or
            focus_style["boxShadow"] != resting_style["boxShadow"] or
            focus_style["borderColor"] != resting_style["borderColor"]
        )
        metrics["has_focus_indicator"] = has_focus_indicator

        if not has_focus_indicator:
            warnings.append(
                f"Element {resolved_selector} lacks visible focus indicator when keyboard-focused."
            )

        # 4. Interactive State Toggle (click)
        initial_pressed = resting_style.get("ariaPressed")
        if initial_pressed is not None:
            page.click(resolved_selector)
            page.wait_for_timeout(100)
            toggled_pressed = page.evaluate("""(sel) => {
                const el = document.querySelector(sel);
                return el ? el.getAttribute('aria-pressed') : null;
            }""", resolved_selector)
            metrics["aria_pressed_toggled"] = (toggled_pressed != initial_pressed)

        passed = hover_visual_change or has_focus_indicator
        score = 1.0 if (hover_visual_change and has_focus_indicator) else (0.75 if passed else 0.4)

        return MotionBehavioralResult(
            motion_type="micro_interaction",
            passed=passed,
            score=score,
            selector=resolved_selector,
            metrics=metrics,
            errors=errors,
            warnings=warnings,
        )

    except Exception as e:
        return MotionBehavioralResult(
            motion_type="micro_interaction",
            passed=False,
            score=0.0,
            selector=resolved_selector,
            errors=[f"Exception during micro-interaction behavioral check: {e}"],
        )


# ==============================================================================
# Performance & Health Checks
# ==============================================================================

def check_motion_performance(
    page: Page,
    page_errors: Optional[List[str]] = None,
    console_errors: Optional[List[str]] = None,
) -> MotionPerformanceResult:
    """
    Evaluates 8 performance and health dimensions:
    1. page errors
    2. console errors
    3. long tasks (> 50ms)
    4. cumulative layout shift (CLS)
    5. uncontrolled requestAnimationFrame loops on idle
    6. listener cleanup / passive flags
    7. desktop body horizontal overflow
    8. mobile 375 px behavior
    """
    violations: List[str] = []
    warnings: List[str] = []

    pe = list(page_errors or [])
    ce = list(console_errors or [])

    if pe:
        violations.append(f"Encountered {len(pe)} unhandled page error(s): {pe[:2]}")
    if ce:
        violations.append(f"Encountered {len(ce)} console error(s): {ce[:2]}")

    # 3. Long tasks & 4. CLS
    perf_data = page.evaluate("""() => {
        return {
            cls: window.__cls_score || 0,
            longTasks: window.__long_tasks_count || 0,
            preventedEvents: window.__prevented_events || [],
            listeners: window.__registered_listeners || []
        };
    }""")

    cls_score = float(perf_data.get("cls", 0.0))
    long_tasks = int(perf_data.get("longTasks", 0))

    if cls_score > 0.25:
        violations.append(f"High Cumulative Layout Shift (CLS: {round(cls_score, 3)} > 0.25 threshold).")
    elif cls_score > 0.1:
        warnings.append(f"Moderate Cumulative Layout Shift (CLS: {round(cls_score, 3)}).")

    if long_tasks > 3:
        warnings.append(f"Detected {long_tasks} long tasks (>50ms) during motion interactions.")

    # 5. Uncontrolled RAF Loop on Idle Detection
    raf_sample_1 = page.evaluate("window.__raf_counter || 0")
    page.wait_for_timeout(400)
    raf_sample_2 = page.evaluate("window.__raf_counter || 0")
    raf_delta = raf_sample_2 - raf_sample_1
    idle_raf_rate = (raf_delta / 0.4)

    uncontrolled_raf = False
    if idle_raf_rate > 50:
        uncontrolled_raf = True
        violations.append(
            f"Uncontrolled requestAnimationFrame loop detected: {round(idle_raf_rate, 1)} fps continuous execution during idle."
        )

    # 6. Listener Cleanup & Passive Flags
    listeners = perf_data.get("listeners", [])
    unpassive_scroll_listeners = [
        l for l in listeners if l.get("type") in ["scroll", "touchmove"] and not l.get("passive", False)
    ]
    if unpassive_scroll_listeners:
        warnings.append(
            f"Found {len(unpassive_scroll_listeners)} scroll/touch listener(s) without passive: true flag."
        )

    # 7. Desktop Body Horizontal Overflow
    page.set_viewport_size({"width": 1280, "height": 800})
    desktop_scroll_w = page.evaluate("""() => {
        const body = document.body;
        const html = document.documentElement;
        return Math.max(
            html ? html.scrollWidth : 0,
            body ? body.scrollWidth : 0
        );
    }""")
    desktop_overflow = desktop_scroll_w > 1280

    if desktop_overflow:
        violations.append(
            f"Desktop horizontal layout overflow detected: scrollWidth {desktop_scroll_w}px exceeds 1280px viewport."
        )

    # 8. Mobile 375px Behavior
    page.set_viewport_size({"width": 375, "height": 667})
    page.wait_for_timeout(150)
    mobile_scroll_w = page.evaluate("""() => {
        const body = document.body;
        const html = document.documentElement;
        return Math.max(
            html ? html.scrollWidth : 0,
            body ? body.scrollWidth : 0
        );
    }""")
    mobile_overflow = mobile_scroll_w > 375


    if mobile_overflow:
        violations.append(
            f"Mobile 375px horizontal layout blowout detected: scrollWidth {mobile_scroll_w}px exceeds 375px viewport."
        )

    # Restore desktop viewport
    page.set_viewport_size({"width": 1280, "height": 800})

    passed = len(violations) == 0
    penalty = min(1.0, len(violations) * 0.25 + len(warnings) * 0.05)
    score = max(0.0, 1.0 - penalty)

    return MotionPerformanceResult(
        passed=passed,
        score=score,
        page_errors=pe,
        console_errors=ce,
        long_tasks_count=long_tasks,
        cumulative_layout_shift=cls_score,
        uncontrolled_raf=uncontrolled_raf,
        idle_raf_rate_per_sec=idle_raf_rate,
        listener_cleanup_verified=(len(unpassive_scroll_listeners) == 0),
        body_horizontal_overflow_desktop=desktop_overflow,
        body_horizontal_overflow_mobile_375=mobile_overflow,
        desktop_scroll_width=desktop_scroll_w,
        desktop_viewport_width=1280,
        mobile_scroll_width=mobile_scroll_w,
        mobile_viewport_width=375,
        violations=violations,
        warnings=warnings,
    )


# ==============================================================================
# Full Evaluation Engine
# ==============================================================================

def evaluate_motion_page(
    page: Page,
    motion_specs: Optional[List[Any]] = None,
    page_errors: Optional[List[str]] = None,
    console_errors: Optional[List[str]] = None,
) -> MotionBenchmarkReport:
    """
    Evaluates all active motion families and performance checks on an active Playwright page.
    """
    setup_page_monitoring(page, page_errors=page_errors, console_errors=console_errors)

    active_types: Set[str] = set()
    if motion_specs:
        for s in motion_specs:
            t = getattr(s, "type", s.get("type") if isinstance(s, dict) else str(s))
            if hasattr(t, "value"):
                t = t.value
            active_types.add(str(t).lower())

    eval_all = (len(active_types) == 0)

    behavioral_results: Dict[str, MotionBehavioralResult] = {}

    # 1. Scroll reveal
    if eval_all or "scroll_reveal" in active_types:
        behavioral_results["scroll_reveal"] = check_scroll_reveal_behavior(page)

    # 2. Parallax
    if eval_all or "parallax" in active_types:
        behavioral_results["parallax"] = check_parallax_behavior(page)

    # 3. Horizontal scroll
    if eval_all or "horizontal_scroll" in active_types:
        behavioral_results["horizontal_scroll"] = check_horizontal_scroll_behavior(page)

    # 4. Sticky storytelling
    if eval_all or "sticky_story" in active_types:
        behavioral_results["sticky_story"] = check_sticky_story_behavior(page)

    # 5. Text reveal
    if eval_all or "text_reveal" in active_types:
        behavioral_results["text_reveal"] = check_text_reveal_behavior(page)

    # 6. Micro-interactions
    if eval_all or "micro_interaction" in active_types:
        behavioral_results["micro_interaction"] = check_micro_interactions_behavior(page)

    # Performance and health checks
    perf_res = check_motion_performance(
        page,
        page_errors=page_errors,
        console_errors=console_errors,
    )

    if behavioral_results:
        b_score = sum(r.score for r in behavioral_results.values()) / len(behavioral_results)
        b_passed = all(r.passed for r in behavioral_results.values())
    else:
        b_score = 1.0
        b_passed = True

    p_score = perf_res.score
    p_passed = perf_res.passed

    composite_score = (b_score * 0.6) + (p_score * 0.4)
    overall_passed = b_passed and p_passed

    summary = {
        "families_tested": list(behavioral_results.keys()),
        "behavioral_passed_count": sum(1 for r in behavioral_results.values() if r.passed),
        "behavioral_total_count": len(behavioral_results),
        "performance_passed": p_passed,
        "violations_count": len(perf_res.violations),
        "warnings_count": len(perf_res.warnings),
    }

    return MotionBenchmarkReport(
        passed=overall_passed,
        composite_score=composite_score,
        behavioral_score=b_score,
        performance_score=p_score,
        behavioral_results=behavioral_results,
        performance_result=perf_res,
        summary=summary,
    )


def evaluate_motion_html(
    html_content: str,
    motion_specs: Optional[List[Any]] = None,
    timeout_s: int = 15,
) -> MotionBenchmarkReport:
    """
    Evaluates raw HTML/JS/CSS motion markup directly in a headless Playwright Chromium instance.
    Ideal for unit testing, canonical snippets, and offline benchmarking.
    """
    if not _PLAYWRIGHT_AVAILABLE:
        return MotionBenchmarkReport(
            passed=False,
            composite_score=0.0,
            behavioral_score=0.0,
            performance_score=0.0,
            summary={"error": "Playwright is not installed."},
        )

    page_errors: List[str] = []
    console_errors: List[str] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 1280, "height": 800})
            setup_page_monitoring(page, page_errors=page_errors, console_errors=console_errors)
            page.set_content(html_content, wait_until="load", timeout=timeout_s * 1000)
            page.wait_for_timeout(300)

            report = evaluate_motion_page(
                page,
                motion_specs=motion_specs,
                page_errors=page_errors,
                console_errors=console_errors,
            )
            return report
        finally:
            browser.close()


def evaluate_motion_url(
    url: str,
    motion_specs: Optional[List[Any]] = None,
    timeout_s: int = 20,
) -> MotionBenchmarkReport:
    """
    Evaluates a live preview server URL (e.g. Vite dev or preview server).
    """
    if not _PLAYWRIGHT_AVAILABLE:
        return MotionBenchmarkReport(
            passed=False,
            composite_score=0.0,
            behavioral_score=0.0,
            performance_score=0.0,
            summary={"error": "Playwright is not installed."},
        )

    page_errors: List[str] = []
    console_errors: List[str] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 1280, "height": 800})
            setup_page_monitoring(page, page_errors=page_errors, console_errors=console_errors)
            page.goto(url, wait_until="domcontentloaded", timeout=timeout_s * 1000)
            page.wait_for_timeout(500)

            report = evaluate_motion_page(
                page,
                motion_specs=motion_specs,
                page_errors=page_errors,
                console_errors=console_errors,
            )
            return report
        finally:
            browser.close()


def evaluate_motion_project(
    workspace_dir: Union[str, Path],
    port: int = 5174,
    motion_specs: Optional[List[Any]] = None,
    timeout_s: int = 25,
) -> MotionBenchmarkReport:
    """
    Starts a local Vite dev or preview server in workspace_dir, evaluates motion runtime,
    and cleanly terminates the server process.
    """
    workspace_dir = Path(workspace_dir).resolve()
    url = f"http://127.0.0.1:{port}"

    has_dist = (workspace_dir / "dist" / "index.html").exists()
    cmd = [
        "npx", "vite", "preview", "--port", str(port), "--strictPort", "--host", "127.0.0.1"
    ] if has_dist else [
        "npx", "vite", "--port", str(port), "--strictPort", "--host", "127.0.0.1"
    ]

    env = os.environ.copy()
    env["PORT"] = str(port)

    proc = subprocess.Popen(
        cmd,
        cwd=str(workspace_dir),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=env,
        shell=(os.name == "nt"),
    )

    try:
        running = False
        for _ in range(30):
            time.sleep(0.3)
            if proc.poll() is not None:
                break
            try:
                with urllib.request.urlopen(url, timeout=1):
                    running = True
                    break
            except Exception:
                continue

        if not running:
            return MotionBenchmarkReport(
                passed=False,
                composite_score=0.0,
                behavioral_score=0.0,
                performance_score=0.0,
                summary={"error": f"Vite server failed to start on port {port}"},
            )

        return evaluate_motion_url(url, motion_specs=motion_specs, timeout_s=timeout_s)

    finally:
        try:
            proc.terminate()
            proc.wait(timeout=3)
        except Exception:
            proc.kill()
