"""Freeform-path fixes (IMPLEMENTATION_PLAN_2026-10-16 §10.2): the legacy loop is still used
for strategy="freeform" and for edits."""
import re
from copy import deepcopy
from types import SimpleNamespace

import pytest

from agent.agent import _adapt_radii, run_site_agent_on_example, synthesize_section_css


@pytest.fixture(autouse=True)
def _freeform(monkeypatch):
    monkeypatch.setenv("SITE_STRATEGY", "freeform")
    monkeypatch.setattr("agent.agent.run_command", lambda *a, **kw: SimpleNamespace(returncode=0, stdout="", stderr=""))


def _section(name: str, extra_css: str = "") -> str:
    slug = name.lower()
    return f'''<tool_call name="write_site">
<file path="src/components/{name}.tsx">
import React from 'react';
import './{name}.css';
export function {name}() {{return <section id="{slug}" className="{slug}-section"><p>{name} copy</p></section>;}}
export default {name};
</file>
<file path="src/components/{name}.css">:root {{ --brand-ink: #111; }}
.{slug}-section{{padding:2rem;color:#111;background:#fff}}{extra_css}</file>
</tool_call>'''


def test_freeform_sampling_follows_qwen3_non_thinking_guidance(tmp_path):
    calls = []

    def generate(**kwargs):
        calls.append(kwargs)
        return _section("Hero")

    run_site_agent_on_example(0, "Build a pottery hero", "Pottery", "", ["hero"],
                              SimpleNamespace(generate_turn=generate), workspace_root=tmp_path, max_turns=1)
    first = calls[0]
    assert (first["temperature"], first["top_p"], first["top_k"], first["repetition_penalty"]) == (0.7, 0.8, 20, 1.0)


def test_every_section_gets_three_repair_attempts_regardless_of_position(tmp_path):
    calls = []

    def generate(**kwargs):
        calls.append(kwargs)
        return "no tool call here"

    result = run_site_agent_on_example(0, "Build a pottery site", "Pottery", "", ["hero", "footer"],
                                       SimpleNamespace(generate_turn=generate), workspace_root=tmp_path, max_turns=2)
    per_section = [entry.get("section") for entry in result["turn_logs"] if entry.get("action") != "section_blocked"]
    assert len(calls) == 6, per_section
    assert set(result["blocked_sections"]) == {"hero", "footer"}


def test_next_section_prompt_lists_accepted_root_classes_and_tokens(tmp_path):
    histories = []

    def generate(**kwargs):
        histories.append(deepcopy(kwargs["history"]))
        return _section("Hero" if len(histories) == 1 else "Footer")

    result = run_site_agent_on_example(0, "Build a pottery portfolio", "Pottery", "", ["hero", "footer"],
                                       SimpleNamespace(generate_turn=generate), workspace_root=tmp_path, max_turns=2)
    assert result["sections_completed"] == 2
    second = "\n".join(item["content"] for item in histories[1])
    assert "hero-section" in second
    assert "--brand-ink" in second


def test_radius_adaptation_keeps_pill_buttons():
    css = (".card { border-radius: 12px; }\n"
           ".hero__cta, .btn-primary { border-radius: 40px; padding: 1rem; }\n"
           ".panel-media { border-radius: 8px; }\n")
    adapted = _adapt_radii(css, btn_radius="999px", card_radius="0px")
    assert re.search(r"\.card \{ border-radius: 0px;", adapted)
    assert re.search(r"\.hero__cta, \.btn-primary \{ border-radius: 40px;", adapted)


def test_synthesized_css_is_scoped_to_the_section_root():
    tsx = ('export function Pricing() { return <section id="pricing" className="pricing-block">'
           '<div className="pricing-block__grid"><div className="plan-card"><button className="plan-btn">Go</button>'
           '</div></div></section>; }')
    css = synthesize_section_css("pricing", tsx)
    selectors = []
    for block in re.findall(r"([^{}@]+)\{[^{}]*\}", css):
        for selector in block.split(","):
            selector = selector.strip()
            if selector and not selector.startswith(("/*", "from", "to")):
                selectors.append(selector)
    assert selectors, css
    unscoped = [s for s in selectors if not s.startswith(".pricing-block")]
    assert not unscoped, unscoped
