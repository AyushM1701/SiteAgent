"""Native section authoring: prompt/target protocol, acceptance checks, fallback, data split."""
from pathlib import Path

import pytest

from agent.site_brief import generate_content_brief
from agent.site_kit import KitSite
from agent.site_kit.native import (NATIVE_SYSTEM_PROMPT, missing_copy, native_messages, native_target,
                                   parse_native_files)
from data_pipeline.native_site_prompts import HOLDOUT_FAMILIES, prompt_bank, section_slug

PROMPT = ("Larkspur Yoga — a small yoga studio in Leeds. Sections: classes, teachers, pricing, FAQ, contact. "
          "Calm sage and sand tones. Email hello@larkspuryoga.co.uk.")


def _site(prompt=PROMPT):
    kit = KitSite(prompt, generate_content_brief(prompt), None)
    for slug in kit.sections:
        kit.accept(slug, "")
    return kit


def test_kit_output_round_trips_through_the_native_protocol():
    kit = _site()
    for slug in kit.sections:
        files = kit.render(slug)
        parsed, problems = parse_native_files(native_target(files), kit.component(slug))
        assert not problems, (slug, problems)
        assert parsed == [(p, s.rstrip() + "\n") if p.endswith(".tsx") else (p, s.strip() + "\n") for p, s in files]
        assert not missing_copy(parsed[0][1], kit.final_content(slug)), slug


def test_native_prompt_carries_spec_and_exact_content():
    kit = _site()
    messages = native_messages(kit, "pricing")
    assert messages[0] == {"role": "system", "content": NATIVE_SYSTEM_PROMPT}
    user = messages[1]["content"]
    assert 'Section: Pricing (id "pricing", kind "pricing")' in user
    assert "Content JSON:" in user and "Files: src/components/Pricing.tsx and src/components/Pricing.css" in user
    assert kit.final_content("pricing")["title"] in user


@pytest.mark.parametrize("reply, problem", [
    ("no files at all", "missing src/components/Faq.tsx"),
    ('<file path="src/components/Faq.tsx">export function Other() { return null; }</file>\n'
     '<file path="src/components/Faq.css">.k-faq {}</file>', "does not export Faq"),
    ('<file path="src/components/Faq.tsx">import x from "lodash";\nexport function Faq() { return null; }</file>\n'
     '<file path="src/components/Faq.css">.k-faq {}</file>', "imports a package"),
    ('<file path="src/components/Faq.tsx">export function Faq() { return null; }</file>\n'
     '<file path="src/components/Faq.css">.k-faq {}</file>\n<file path="src/App.tsx">x</file>', "unexpected files"),
])
def test_parse_rejects_unusable_replies(reply, problem):
    files, problems = parse_native_files(reply, "Faq")
    assert files == [] and any(problem in p for p in problems), problems


def test_missing_copy_flags_rewritten_added_and_missing_text():
    content = {"title": "Questions", "items": [{"q": "Do you take walk-ins?", "a": "Yes, before 10am."}]}
    good = 'const DATA: any = {"title": "Questions", "items": [{"q": "Do you take walk-ins?", "a": "Yes, before 10am."}]};\n'
    assert missing_copy(good, content) == []
    assert missing_copy(good.replace("before 10am", "any time"), content) == ["Yes, before 10am.", "(added) Yes, any time."]
    assert missing_copy(good.replace('"Questions"', '"Questions and more"'), content)[0] == "Questions"
    assert missing_copy("export function Faq() {}", content) == ["no `const DATA = {...};` object"]


class _Runner:
    """Replies with fixed text; counts calls."""
    is_mock = True

    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = 0
        self.last_generation_tokens = 10

    def generate_turn(self, **kwargs):
        self.calls += 1
        return self.replies.pop(0) if self.replies else ""


def test_native_code_falls_back_to_the_kit_after_two_bad_replies():
    from agent.agent import _native_section_code
    kit = _site()
    runner = _Runner(["nonsense", "<file>still nonsense</file>"])
    files, problems = _native_section_code(kit, "faq", runner, 0, "Larkspur", None, lambda e: None, [], 1)
    assert files is None and problems and runner.calls == 2


def test_native_code_accepts_a_faithful_reply_on_the_first_attempt():
    from agent.agent import _native_section_code
    kit = _site()
    runner = _Runner([native_target(kit.render("faq"))])
    files, problems = _native_section_code(kit, "faq", runner, 0, "Larkspur", None, lambda e: None, [], 1)
    assert problems == [] and files and files[0][0] == "src/components/Faq.tsx" and runner.calls == 1


def test_native_code_rejects_changed_copy():
    from agent.agent import _native_section_code
    kit = _site()
    title = kit.final_content("faq")["title"]
    altered = native_target(kit.render("faq")).replace(title, title + " and more")
    files, problems = _native_section_code(kit, "faq", _Runner([altered, altered]), 0, "L", None, lambda e: None, [], 1)
    assert files is None and "approved copy" in problems[0]


def test_prompt_bank_is_deterministic_and_holds_out_whole_families():
    first, second = prompt_bank(3), prompt_bank(3)
    assert first == second
    assert {r["family_id"] for r in first if r["holdout"]} == HOLDOUT_FAMILIES
    assert len({r["prompt"] for r in first}) == len(first)
    assert section_slug("Areas we cover") == "areas-we-cover"


def test_native_strategy_is_selectable():
    from agent.agent import resolve_site_strategy
    assert resolve_site_strategy("native") == "native"
    assert resolve_site_strategy(None) in {"kit", "native", "freeform"}


def test_structural_gaps_catch_lost_behaviour_and_duplicate_ids():
    from agent.site_kit.native import structural_gaps
    kit = _site()
    for slug in kit.sections:
        reference = kit.render(slug)[0][1]
        assert structural_gaps(reference, reference) == [], slug
    reference = kit.render(kit.reveal_section)[0][1]
    assert 'data-motion="scroll-reveal"' in structural_gaps(reference.replace('data-motion="scroll-reveal"', ''), reference)
    tsx = 'const DATA: any = {};\nexport function Faq() { return <><h2 id="a"/><h2 id="a"/></>; }\n'
    files, problems = parse_native_files(f'<file path="src/components/Faq.tsx">\n{tsx}</file>\n'
                                         '<file path="src/components/Faq.css">\n.k-faq {}\n</file>', "Faq")
    assert not files and any("repeats element id" in p for p in problems)


def test_quotes_section_renders_one_heading():
    prompt = PROMPT.replace("FAQ", "testimonials, FAQ")
    kit = _site(prompt)
    slug = next(s for s in kit.sections if kit.kinds[s] == "quotes")
    assert kit.render(slug)[0][1].count(f'id="{slug}-title"') == 1
