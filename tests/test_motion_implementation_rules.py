"""
tests/test_motion_implementation_rules.py - Comprehensive Unit & Integration Tests for:
Section 5: Motion Implementation Rules
Rule 1: Scroll reveal (IntersectionObserver, cleanup, opacity/transform, reduced-motion)
Rule 2: Parallax (passive listener, RAF, bounded translation, zero wheel.preventDefault, mobile/reduced-motion disable)
Rule 3: Horizontal scroll (normal vertical scroll -> sticky viewport -> translate3d track, mobile scroll-snap, no hijacking)
Rule 4: Sticky storytelling (CSS position: sticky, no ancestor overflow:hidden conflict, semantic DOM order)
Rule 5: Text reveal (accessible h1 aria-label, decorative aria-hidden spans, instant reduced-motion fallback)
Rule 6: Micro-interactions (:hover + :focus-visible parity, aria-pressed/aria-selected, <=250ms, zero layout shift)
Integration with SiteBenchmarkScorer and project_validator.
"""

import pytest
from pathlib import Path
import tempfile

from agent.motion_patterns import (
    MotionType,
    MotionSpec,
    validate_motion_rules,
    generate_scroll_reveal_snippet,
    generate_parallax_snippet,
    generate_horizontal_scroll_snippet,
    generate_sticky_story_snippet,
    generate_text_reveal_snippet,
    generate_micro_interaction_snippet,
)
from evaluation.site_benchmark_scorer import SiteBenchmarkScorer
from agent.project_validator import ValidationResult, run_motion_rules_check


# ── Rule 1: Scroll Reveal Tests ──────────────────────────────────────────────

def test_rule1_scroll_reveal_compliant():
    """Scroll reveal with IntersectionObserver, unobserve cleanup, and reduced-motion passes."""
    tsx = """
    import React, { useEffect, useRef } from 'react';
    export function Features() {
        const ref = useRef<HTMLDivElement>(null);
        useEffect(() => {
            const observer = new IntersectionObserver((entries) => {
                entries.forEach(e => {
                    if (e.isIntersecting) e.target.classList.add('is-visible');
                });
            });
            if (ref.current) observer.observe(ref.current);
            return () => observer.disconnect();
        }, []);
        return <div ref={ref} className="reveal-box">Feature</div>;
    }
    """
    css = """
    .reveal-box {
        opacity: 0;
        transform: translateY(20px);
        transition: opacity 0.5s ease, transform 0.5s ease;
    }
    .reveal-box.is-visible {
        opacity: 1;
        transform: translateY(0);
    }
    @media (prefers-reduced-motion: reduce) {
        .reveal-box {
            opacity: 1 !important;
            transform: none !important;
        }
    }
    """
    files = {"src/Features.tsx": tsx, "src/Features.css": css}
    res = validate_motion_rules(files, [MotionSpec(type=MotionType.SCROLL_REVEAL, target_section="features")])
    assert res.is_valid is True
    assert len(res.violations) == 0
    assert any("Rule 1" in p for p in res.passed_rules)


def test_rule1_scroll_reveal_missing_cleanup():
    """Scroll reveal missing unobserve() or disconnect() cleanup fails Rule 1."""
    tsx = """
    import React, { useEffect } from 'react';
    export function Features() {
        useEffect(() => {
            const observer = new IntersectionObserver(() => {});
            // Missing observer cleanup
        }, []);
        return <div>Feature</div>;
    }
    """
    css = """
    @media (prefers-reduced-motion: reduce) {
        .item { opacity: 1; }
    }
    """
    files = {"src/Features.tsx": tsx, "src/Features.css": css}
    res = validate_motion_rules(files, [MotionSpec(type=MotionType.SCROLL_REVEAL, target_section="features")])
    assert res.is_valid is False
    assert any("cleanup" in v for v in res.violations)


def test_rule1_scroll_reveal_missing_reduced_motion():
    """Scroll reveal missing prefers-reduced-motion fails Rule 1."""
    tsx = """
    import React, { useEffect } from 'react';
    export function Features() {
        useEffect(() => {
            const observer = new IntersectionObserver(() => {});
            return () => observer.disconnect();
        }, []);
        return <div>Feature</div>;
    }
    """
    css = ".item { opacity: 0; transform: translateY(10px); }"
    files = {"src/Features.tsx": tsx, "src/Features.css": css}
    res = validate_motion_rules(files, [MotionSpec(type=MotionType.SCROLL_REVEAL, target_section="features")])
    assert res.is_valid is False
    assert any("prefers-reduced-motion" in v for v in res.violations)


# ── Rule 2: Parallax Tests ───────────────────────────────────────────────────

def test_rule2_parallax_compliant():
    """Parallax with passive scroll listener, RAF, cleanup, and reduced-motion passes."""
    tsx = """
    import React, { useEffect, useRef } from 'react';
    export function Hero() {
        const bgRef = useRef<HTMLDivElement>(null);
        useEffect(() => {
            let rafId: number;
            const onScroll = () => {
                rafId = requestAnimationFrame(() => {
                    const offset = Math.min(50, window.scrollY * 0.2);
                    if (bgRef.current) bgRef.current.style.transform = `translate3d(0, ${offset}px, 0)`;
                });
            };
            window.addEventListener('scroll', onScroll, { passive: true });
            return () => {
                window.removeEventListener('scroll', onScroll);
                cancelAnimationFrame(rafId);
            };
        }, []);
        return <div ref={bgRef} className="parallax-hero">Hero</div>;
    }
    """
    css = """
    .parallax-hero {
        position: relative;
        overflow: hidden;
    }
    @media (prefers-reduced-motion: reduce), (max-width: 768px) {
        .parallax-hero { transform: none !important; }
    }
    """
    files = {"src/Hero.tsx": tsx, "src/Hero.css": css}
    res = validate_motion_rules(files, [MotionSpec(type=MotionType.PARALLAX, target_section="hero")])
    assert res.is_valid is True
    assert len(res.violations) == 0
    assert any("Rule 2" in p for p in res.passed_rules)


def test_rule2_parallax_forbidden_event_hijacking():
    """Parallax using wheel.preventDefault() or touchmove.preventDefault() triggers hard violation."""
    tsx = """
    import React, { useEffect } from 'react';
    export function Hero() {
        useEffect(() => {
            const onWheel = (e: WheelEvent) => {
                e.preventDefault(); // FORBIDDEN: event hijacking
            };
            window.addEventListener('wheel', onWheel);
            return () => window.removeEventListener('wheel', onWheel);
        }, []);
        return <div>Parallax Hero</div>;
    }
    """
    css = "@media (prefers-reduced-motion: reduce) { .hero { transform: none; } }"
    files = {"src/Hero.tsx": tsx, "src/Hero.css": css}
    res = validate_motion_rules(files, [MotionSpec(type=MotionType.PARALLAX, target_section="hero")])
    assert res.is_valid is False
    assert any("hijacking" in v.lower() or "preventdefault" in v.lower() for v in res.violations)


def test_rule2_parallax_missing_listener_cleanup():
    """Parallax missing removeEventListener cleanup triggers violation."""
    tsx = """
    import React, { useEffect } from 'react';
    export function Hero() {
        useEffect(() => {
            const onScroll = () => {};
            window.addEventListener('scroll', onScroll, { passive: true });
            // Intentionally missing unmount cleanup
        }, []);
        return <div>Parallax Hero</div>;
    }
    """
    css = "@media (prefers-reduced-motion: reduce) { .hero { transform: none; } }"
    files = {"src/Hero.tsx": tsx, "src/Hero.css": css}
    res = validate_motion_rules(files, [MotionSpec(type=MotionType.PARALLAX, target_section="hero")])
    assert res.is_valid is False
    assert any("removeeventlistener" in v.lower() for v in res.violations)


# ── Rule 3: Horizontal Scroll Tests ──────────────────────────────────────────

def test_rule3_horizontal_scroll_compliant():
    """Horizontal scroll with normal vertical mapping and mobile scroll-snap passes."""
    tsx = """
    import React, { useEffect, useRef } from 'react';
    export function Showcase() {
        const containerRef = useRef<HTMLDivElement>(null);
        useEffect(() => {
            const onScroll = () => {};
            window.addEventListener('scroll', onScroll, { passive: true });
            return () => window.removeEventListener('scroll', onScroll);
        }, []);
        return (
            <div ref={containerRef} className="horizontal-section">
                <div className="sticky-viewport">
                    <div className="horizontal-track">Cards</div>
                </div>
            </div>
        );
    }
    """
    css = """
    .horizontal-section { height: 300vh; }
    .sticky-viewport {
        position: sticky;
        top: 0;
        height: 100vh;
        overflow: hidden;
    }
    .horizontal-track { display: flex; will-change: transform; }
    @media (max-width: 768px) {
        .sticky-viewport {
            position: static;
            height: auto;
            overflow-x: auto;
            scroll-snap-type: x mandatory;
        }
    }
    """
    files = {"src/Showcase.tsx": tsx, "src/Showcase.css": css}
    res = validate_motion_rules(files, [MotionSpec(type=MotionType.HORIZONTAL_SCROLL, target_section="showcase")])
    assert res.is_valid is True
    assert len(res.violations) == 0
    assert any("Rule 3" in p for p in res.passed_rules)


def test_rule3_horizontal_scroll_wheel_hijacking_fails():
    """Horizontal scroll with wheel.preventDefault fails Rule 3."""
    tsx = """
    import React, { useEffect } from 'react';
    export function Showcase() {
        useEffect(() => {
            window.addEventListener('wheel', (e) => { e.preventDefault(); });
        }, []);
        return <div className="horizontal-section">Showcase</div>;
    }
    """
    css = ".sticky-viewport { position: sticky; overflow: hidden; }"
    files = {"src/Showcase.tsx": tsx, "src/Showcase.css": css}
    res = validate_motion_rules(files, [MotionSpec(type=MotionType.HORIZONTAL_SCROLL, target_section="showcase")])
    assert res.is_valid is False
    assert any("hijack" in v.lower() or "preventdefault" in v.lower() for v in res.violations)


# ── Rule 4: Sticky Storytelling Tests ────────────────────────────────────────

def test_rule4_sticky_story_compliant():
    """Sticky storytelling with position: sticky and semantic HTML tags passes."""
    tsx = """
    import React from 'react';
    export function Narrative() {
        return (
            <section className="story-section">
                <aside className="sticky-aside">
                    <h2>Chapter Overview</h2>
                </aside>
                <article className="scrolling-content">
                    <p>Narrative step 1</p>
                    <p>Narrative step 2</p>
                </article>
            </section>
        );
    }
    """
    css = """
    .story-section { display: flex; }
    .sticky-aside {
        position: sticky;
        top: 5rem;
    }
    """
    files = {"src/Narrative.tsx": tsx, "src/Narrative.css": css}
    res = validate_motion_rules(files, [MotionSpec(type=MotionType.STICKY_STORY, target_section="narrative")])
    assert res.is_valid is True
    assert len(res.violations) == 0
    assert any("Rule 4" in p for p in res.passed_rules)


def test_rule4_sticky_story_missing_sticky():
    """Sticky storytelling without position: sticky fails Rule 4."""
    tsx = "<section><h2>Narrative</h2></section>"
    css = ".sticky-aside { position: relative; }"
    files = {"src/Narrative.tsx": tsx, "src/Narrative.css": css}
    res = validate_motion_rules(files, [MotionSpec(type=MotionType.STICKY_STORY, target_section="narrative")])
    assert res.is_valid is False
    assert any("position: sticky" in v for v in res.violations)


def test_rule4_sticky_story_ancestor_overflow_warning():
    """Sticky storytelling detects ancestor overflow:hidden hazard and flags warning."""
    tsx = "<section><h2>Narrative</h2></section>"
    css = """
    .app-layout { overflow: hidden; }
    .sticky-aside { position: sticky; top: 0; }
    """
    files = {"src/Narrative.tsx": tsx, "src/Narrative.css": css}
    res = validate_motion_rules(files, [MotionSpec(type=MotionType.STICKY_STORY, target_section="narrative")])
    assert any("overflow: hidden" in w for w in res.warnings)


# ── Rule 5: Text Reveal Tests ────────────────────────────────────────────────

def test_rule5_text_reveal_compliant():
    """Text reveal with accessible aria-label and aria-hidden spans passes."""
    tsx = """
    import React from 'react';
    export function Hero() {
        return (
            <h1 aria-label="Engineered for Autonomy" className="text-reveal-heading">
                <span aria-hidden="true" className="reveal-word">Engineered</span>
                <span aria-hidden="true" className="reveal-word">for</span>
                <span aria-hidden="true" className="reveal-word">Autonomy</span>
            </h1>
        );
    }
    """
    css = """
    .reveal-word {
        display: inline-block;
        opacity: 0;
        animation: reveal 0.4s forwards;
    }
    @media (prefers-reduced-motion: reduce) {
        .reveal-word {
            animation: none !important;
            opacity: 1 !important;
        }
    }
    """
    files = {"src/Hero.tsx": tsx, "src/Hero.css": css}
    res = validate_motion_rules(files, [MotionSpec(type=MotionType.TEXT_REVEAL, target_section="hero")])
    assert res.is_valid is True
    assert len(res.violations) == 0
    assert any("Rule 5" in p for p in res.passed_rules)


def test_rule5_text_reveal_missing_aria_label_fails():
    """Text reveal with aria-hidden spans but missing accessible aria-label fails Rule 5."""
    tsx = """
    import React from 'react';
    export function Hero() {
        return (
            <h1 className="text-reveal-heading">
                <span aria-hidden="true">Engineered</span>
                <span aria-hidden="true">Scale</span>
            </h1>
        );
    }
    """
    css = """
    @media (prefers-reduced-motion: reduce) {
        .word { opacity: 1; }
    }
    """
    files = {"src/Hero.tsx": tsx, "src/Hero.css": css}
    res = validate_motion_rules(files, [MotionSpec(type=MotionType.TEXT_REVEAL, target_section="hero")])
    assert res.is_valid is False
    assert any("aria-label" in v for v in res.violations)


# ── Rule 6: Micro-Interactions Tests ─────────────────────────────────────────

def test_rule6_micro_interactions_compliant():
    """Micro-interactions with :focus-visible parity and aria-pressed passes."""
    tsx = """
    import React, { useState } from 'react';
    export function Pricing() {
        const [active, setActive] = useState(false);
        return (
            <button
                type="button"
                className="btn-toggle"
                aria-pressed={active}
                onClick={() => setActive(!active)}
            >
                Toggle
            </button>
        );
    }
    """
    css = """
    .btn-toggle {
        padding: 0.75rem 1.5rem;
        transition: transform 180ms ease, background-color 180ms ease;
    }
    .btn-toggle:hover {
        transform: translateY(-2px);
    }
    .btn-toggle:focus-visible {
        outline: 2px solid #6366f1;
    }
    """
    files = {"src/Pricing.tsx": tsx, "src/Pricing.css": css}
    res = validate_motion_rules(files, [MotionSpec(type=MotionType.MICRO_INTERACTION, target_section="pricing")])
    assert res.is_valid is True
    assert len(res.violations) == 0
    assert any("Rule 6" in p for p in res.passed_rules)


def test_rule6_micro_interactions_missing_focus_parity_warning():
    """Micro-interactions with :hover but lacking :focus-visible flags accessibility warning."""
    tsx = "<button type=\"button\" className=\"btn\">Action</button>"
    css = """
    .btn:hover {
        transform: scale(1.05);
    }
    """
    files = {"src/Btn.tsx": tsx, "src/Btn.css": css}
    res = validate_motion_rules(files, [MotionSpec(type=MotionType.MICRO_INTERACTION, target_section="button")])
    assert any("focus-visible" in w for w in res.warnings)


# ── Canonical Snippet Generators Full Compliance ─────────────────────────────

def test_all_canonical_snippets_pass_motion_rules():
    """All 6 canonical motion generators must produce code that strictly passes validate_motion_rules."""
    snippets = [
        ("ScrollReveal", *generate_scroll_reveal_snippet("Features"), MotionType.SCROLL_REVEAL),
        ("Parallax", *generate_parallax_snippet("Hero"), MotionType.PARALLAX),
        ("HorizontalScroll", *generate_horizontal_scroll_snippet("Showcase"), MotionType.HORIZONTAL_SCROLL),
        ("StickyStory", *generate_sticky_story_snippet("Story"), MotionType.STICKY_STORY),
        ("TextReveal", *generate_text_reveal_snippet("Heading"), MotionType.TEXT_REVEAL),
        ("MicroInteraction", *generate_micro_interaction_snippet("Pricing"), MotionType.MICRO_INTERACTION),
    ]

    for name, tsx, css, m_type in snippets:
        files = {f"src/{name}.tsx": tsx, f"src/{name}.css": css}
        res = validate_motion_rules(files, [MotionSpec(type=m_type, target_section=name.lower())])
        assert res.is_valid is True, f"Snippet {name} failed validation: {res.violations}"
        assert len(res.violations) == 0, f"Snippet {name} had violations: {res.violations}"
        assert res.score == 1.0, f"Snippet {name} score expected 1.0, got {res.score}"


# ── Scorer & Validator Integration Tests ─────────────────────────────────────

def test_scorer_motion_quality_with_rules_validation():
    """SiteBenchmarkScorer integrates validate_motion_rules and heavily penalizes violations."""
    scorer = SiteBenchmarkScorer()

    # 1. Compliant codebase (multi-component with scroll reveal and micro-interactions)
    r_tsx, r_css = generate_scroll_reveal_snippet("Features")
    m_tsx, m_css = generate_micro_interaction_snippet("Pricing")
    compliant_files = {
        "src/Features.tsx": r_tsx,
        "src/Features.css": r_css,
        "src/Pricing.tsx": m_tsx,
        "src/Pricing.css": m_css,
    }
    score_clean, details_clean = scorer.score_motion_quality(compliant_files)
    assert score_clean >= 0.85
    assert "rules_validation" in details_clean
    assert len(details_clean["violations"]) == 0

    # 2. Codebase with hard violation (wheel.preventDefault hijacking)
    violating_files = {
        "src/Hero.tsx": "window.addEventListener('wheel', (e) => { e.preventDefault(); });",
        "src/Hero.css": ".hero:hover { transform: scale(1.1); }",
    }
    score_bad, details_bad = scorer.score_motion_quality(violating_files)
    assert len(details_bad["violations"]) > 0
    assert score_bad < score_clean


def test_project_validator_motion_rules_check():
    """run_motion_rules_check catches infractions in a workspace directory."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        workspace = Path(tmp_dir)

        # Write clean snippet
        p_tsx, p_css = generate_micro_interaction_snippet("Pricing")
        (workspace / "Pricing.tsx").write_text(p_tsx, encoding="utf-8")
        (workspace / "Pricing.css").write_text(p_css, encoding="utf-8")

        passed, errs, warns = run_motion_rules_check(workspace)
        assert passed is True
        assert len(errs) == 0

        # Inject wheel.preventDefault hard violation
        (workspace / "BadHero.tsx").write_text(
            "export function Bad() { window.addEventListener('wheel', (e) => e.preventDefault()); return null; }",
            encoding="utf-8"
        )
        passed_bad, errs_bad, _ = run_motion_rules_check(workspace)
        assert passed_bad is False
        assert any("hijack" in e.lower() or "preventdefault" in e.lower() for e in errs_bad)


def test_validation_result_motion_properties():
    """ValidationResult reflects motion_passed and motion_status in code_passed and passed."""
    vr = ValidationResult(
        typecheck_passed=True,
        build_passed=True,
        lint_passed=True,
        contract_passed=True,
        accessibility_passed=True,
        runtime_passed=True,
        preview_running=True,
        motion_passed=False,
        motion_status="failed",
    )
    assert vr.motion_passed is False
    assert vr.motionPassed is False
    assert vr.motionStatus == "failed"
    assert vr.code_passed is False
    assert vr.passed is False

    d = vr.to_dict()
    assert d["motion_passed"] is False
    assert d["motionPassed"] is False
    assert d["motion_status"] == "failed"
