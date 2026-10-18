"""Honest gates: validators must not pass
fabricated results, and must not flag correct code."""
from pathlib import Path

import pytest

from agent.dependency_manager import external_imports
from agent.motion_patterns import validate_motion_rules
from agent.site_acceptance import check_site_files
from agent.site_quality import collect_site_rendering_diagnostics


# ── B9a: import scanner ignores string contents ─────────────────────────────

def test_import_scanner_ignores_from_inside_strings():
    source = (
        "import { useState } from 'react';\n"
        "import './Hero.css';\n"
        "export { helper } from './helpers';\n"
        "const subject = 'Order from ' + brand + '.';\n"
        "const note = \"Imported from\" + ' Lisbon';\n"
        "const lazy = () => import('chart.js');\n"
    )
    assert external_imports({"src/components/Hero.tsx": source}) == {"react", "chart.js"}


def test_import_scanner_still_reads_real_statements():
    source = "import Lib, { a } from 'lodash';\nimport * as THREE from 'three';\nimport 'swiper/css';\nexport * from '@scope/pkg/sub';\n"
    assert external_imports({"src/a.tsx": source}) == {"lodash", "three", "swiper", "@scope/pkg"}


# ── B9b: inert-button scanner understands JSX attributes ────────────────────

def test_button_with_ref_callback_before_onclick_is_not_inert():
    source = ('<button ref={(el) => { refs.current[0] = el; }} onClick={() => open()} type="button">Open</button>\n'
              '<button disabled={busy} onClick={() => go()} type="button">Go</button>')
    errors = collect_site_rendering_diagnostics({"src/components/A.tsx": source})
    assert not [e for e in errors if "INERT BUTTON" in e]


def test_button_without_handler_is_still_inert():
    errors = collect_site_rendering_diagnostics({"src/components/A.tsx": '<button type="button" className="x">Go</button>'})
    assert [e for e in errors if "INERT BUTTON" in e]


# ── B9c: motion rules key on real APIs ──────────────────────────────────────

def test_sticky_word_without_sticky_positioning_is_not_a_story():
    files = {"src/components/Nav.css": ".nav--sticky-shadow { position: fixed; top: 0; }\n",
             "src/components/Nav.tsx": "export function Nav() { return <nav className=\"nav--sticky-shadow\" />; }"}
    result = validate_motion_rules(files)
    assert not [v for v in result.violations if "sticky" in v.lower()]


def test_form_submit_prevent_default_is_not_wheel_hijacking():
    files = {"src/components/Contact.tsx": (
        "const alt = 'Hands shaping clay on a pottery wheel';\n"
        "function submit(e: any) { e.preventDefault(); }\n"),
        "src/components/Contact.css": "@media (prefers-reduced-motion: reduce) { * { animation: none; } }\n"}
    result = validate_motion_rules(files)
    assert not [v for v in result.violations if "hijack" in v.lower()]


def test_real_wheel_hijacking_is_still_a_violation():
    files = {"src/components/Gallery.tsx": (
        "useEffect(() => { const onWheel = (e: WheelEvent) => { e.preventDefault(); };\n"
        "window.addEventListener('wheel', onWheel, { passive: false });\n"
        "return () => window.removeEventListener('wheel', onWheel); }, []);\n"),
        "src/components/Gallery.css": "@media (prefers-reduced-motion: reduce) { * { animation: none; } }\n"}
    result = validate_motion_rules(files)
    assert [v for v in result.violations if "hijack" in v.lower()]


# ── A17: leaks, placeholder hosts and debug text are static errors ──────────

@pytest.mark.parametrize("snippet, label", [
    ("<p>Warm ivory and dark terracotta palette.</p>", "leak"),
    ("<p>No invented address.</p>", "leak"),
    ('<img alt="" src="https://via.placeholder.com/600x400" />', "placeholder"),
    ('<img alt="" src="https://picsum.photos/600/400" />', "placeholder"),
    ('<img alt="" src="https://placehold.co/600x400" />', "placeholder"),
    ("<div>Section Hero has no valid React export.</div>", "debug"),
])
def test_site_files_reject_leaks_placeholders_and_debug_text(snippet, label):
    result = check_site_files({"src/components/Hero.tsx": f"export function Hero() {{ return <section>{snippet}</section>; }}"})
    assert result["static_passed"] is False, label


def test_site_files_accept_honest_copy():
    result = check_site_files({"src/components/Hero.tsx":
                               "export function Hero() { return <section><p>A mug in a terracotta glaze.</p></section>; }"})
    assert result["static_passed"] is True


# ── A15: airy layouts are not blank pages ───────────────────────────────────

def test_visual_judge_does_not_penalise_airy_layouts(tmp_path):
    from PIL import Image, ImageDraw
    from agent.visual_judge import _score_screenshot_heuristic

    airy = Image.new("RGB", (1280, 2400), (250, 250, 247))
    draw = ImageDraw.Draw(airy)
    draw.rectangle((0, 0, 1280, 72), fill=(240, 240, 236))
    for y in range(160, 2300, 420):
        draw.rectangle((80, y, 760, y + 60), fill=(18, 19, 21))
        draw.rectangle((80, y + 90, 600, y + 104), fill=(85, 87, 92))
    path = tmp_path / "airy.png"
    airy.save(path)
    result = _score_screenshot_heuristic(path)
    assert not any("page appears blank" in issue.lower() for issue in result["issues"]), result["issues"]
    assert result["pass"] is True

    blank = tmp_path / "blank.png"
    Image.new("RGB", (1280, 2400), (255, 255, 255)).save(blank)
    assert any("page appears blank" in issue.lower() for issue in _score_screenshot_heuristic(blank)["issues"])


# ── A16: vacuous benchmark checks are not perfect scores ────────────────────

def test_benchmark_marks_vacuous_checks_not_applicable():
    from evaluation.site_benchmark_scorer import SiteBenchmarkScorer
    scorer = SiteBenchmarkScorer()
    score, details = scorer.score_prompt_fidelity({}, {"src/App.tsx": "x"})
    assert score is None and details.get("applicable") is False
    score, _ = scorer.score_required_section_completion({}, {"src/App.tsx": "x"})
    assert score is None


def test_benchmark_completion_uses_planner_sections():
    from evaluation.site_benchmark_scorer import SiteBenchmarkScorer
    spec = {"prompt": "Saffron Table — modern Indian restaurant in Dehradun. Menu, about the chef, private dining."}
    files = {"src/components/Menu.tsx": "x", "src/components/About.tsx": "x"}
    score, details = SiteBenchmarkScorer().score_required_section_completion(spec, files)
    assert score is not None and score < 1.0
    assert "private-dining" in details["missing"]


def test_benchmark_content_quality_ignores_word_count_and_flags_placeholders():
    from evaluation.site_benchmark_scorer import SiteBenchmarkScorer
    scorer = SiteBenchmarkScorer()
    short_honest, _ = scorer.score_content_quality({"src/components/Hero.tsx": "<h1>Bowls thrown by hand.</h1>"})
    placeholder, _ = scorer.score_content_quality(
        {"src/components/Hero.tsx": '<h1>John Doe</h1><img src="https://via.placeholder.com/300" alt="" />'})
    assert short_honest == 1.0
    assert placeholder < 0.7


def test_benchmark_composite_excludes_not_applicable_dimensions(tmp_path):
    from evaluation.site_benchmark_scorer import SiteBenchmarkScorer
    result = SiteBenchmarkScorer().evaluate_site({"task_id": "t", "name": ""}, {"src/App.tsx": "export default 1;"})
    as_dict = result.to_dict()
    assert as_dict["scores"]["required_section_completion"] is None
    assert 0.0 <= result.composite_score <= 1.0


# ── A14: no fabricated validation when the agent has no full project ───────

def test_freeform_run_without_a_project_reports_pending_validation(tmp_path, monkeypatch):
    from agent.agent import AgentModelRunner, run_site_agent_on_example
    monkeypatch.setenv("SITE_STRATEGY", "freeform")
    runner = AgentModelRunner(model_path="dummy", is_mock=True)
    result = run_site_agent_on_example(0, "A landing page for a bakery called Crumb & Co.", "Crumb", "",
                                       ["hero"], runner, tmp_path, max_turns=2)
    assert result["validation"] is None
    assert result["project_validation"] == "pending"


def test_contact_check_ignores_digits_inside_urls(tmp_path):
    from agent.project_validator import find_unverified_contact_files
    comp = tmp_path / "src" / "components"
    comp.mkdir(parents=True)
    (comp / "Hero.tsx").write_text(
        'const DATA = {"src": "https://images.unsplash.com/photo-1578749556568-bc2c40e68b61?auto=format&w=1200"};',
        encoding="utf-8")
    (comp / "Contact.tsx").write_text("<p>Call +1 415 555 0132 or write to hi@made-up.com</p>", encoding="utf-8")
    flagged = find_unverified_contact_files(tmp_path, "A pottery studio. Email hello@asterkiln.com.")
    assert flagged == ["src/components/Contact.tsx"]


@pytest.mark.parametrize("copy", [
    "Explore our palette of 200 paint colours.",
    "Palette knives in three sizes, from fine detail to broad strokes.",
    "Fonts licensed for print, web and packaging.",
    "We build design systems for product teams.",
    "Typography workshops every Saturday morning.",
])
def test_design_words_in_genuine_business_copy_are_not_leaks(copy):
    result = check_site_files({"src/components/Shop.tsx": f"export function Shop() {{ return <section><p>{copy}</p></section>; }}"})
    assert result["static_passed"] is True, result["errors"]


@pytest.mark.parametrize("copy", [
    "Warm ivory palette with editorial typography.",
    "Use a clean layout with generous white space.",
    "This website uses a muted colour scheme.",
    "The hero section pairs serif fonts with soft tones.",
])
def test_design_directions_are_still_leaks(copy):
    result = check_site_files({"src/components/Hero.tsx": f"export function Hero() {{ return <section><p>{copy}</p></section>; }}"})
    assert result["static_passed"] is False, copy
