"""A failed section remains explicitly blocked, never a successful scaffold."""

from types import SimpleNamespace

import pytest

from agent import agent as site_agent


class SequenceRunner:
    is_mock = True
    max_seq_length = 8192
    last_generation_tokens = 10
    last_generation_diagnostics = {}

    def __init__(self, outputs):
        self.outputs = iter(outputs)
        self.calls = []

    def generate_turn(self, **kwargs):
        self.calls.append(kwargs)
        return next(self.outputs)


def section_write(section, body=None):
    body = body or f"export function {section}() {{ return <section>{section} content</section>; }}"
    return (f'<tool_call name="write_site">'
            f'<file path="src/components/{section}.tsx">{body}</file>'
            f'<file path="src/components/{section}.css">.{section.lower()} {{ padding: 24px; }}</file>'
            '</tool_call>')


@pytest.fixture
def fast_gates(monkeypatch):
    monkeypatch.setattr(site_agent, "validate_structural_quality", lambda *a, **kw: [])
    monkeypatch.setattr(site_agent, "preflight_section_files", lambda files: ["invalid syntax"] if any("BROKEN" in c for _, c in files) else [])
    monkeypatch.setattr(site_agent, "run_command", lambda *a, **kw: SimpleNamespace(returncode=0, stdout="", stderr=""))
    from agent import project_validator
    monkeypatch.setattr(project_validator, "run_project_typecheck", lambda *a: (True, []))


def run_site(tmp_path, outputs, sections, max_turns, **kwargs):
    events = []
    runner = SequenceRunner(outputs)
    result = site_agent.run_site_agent_on_example(
        0, "Build a website", "Demo", "<brief>Demo</brief>", sections, runner,
        tmp_path, max_turns=max_turns, event_callback=events.append, **kwargs,
    )
    return result, runner, events


def assert_blocked(result, sections):
    assert result["blocked_sections"] == sections
    assert not result["generation_complete"]
    assert not result["final_passed"]
    assert result["generation_quality"] == "blocked"
    assert result["fallback_sections"] == result["unrepaired_fallbacks"] == result["auto_recovered_sections"] == []
    assert all("data-fallback" not in text for text in result["files"].values())
    assert not any(log["action"].startswith("fallback_") for log in result["turn_logs"])


def test_exhausted_retries_preserve_accepted_files_and_skip_rewrite(tmp_path, fast_gates, monkeypatch):
    monkeypatch.setattr(site_agent, "rewrite_fallback_sections", lambda **kw: pytest.fail("blocked section must not be rewritten"))
    outputs = [section_write("Header"), '<tool_call name="write_site"></tool_call>',
               '<tool_call name="write_site"></tool_call>', section_write("Footer")]
    result, runner, events = run_site(tmp_path, outputs, ["Header", "Hero", "Footer"], 6)
    assert_blocked(result, ["Hero"])
    assert result["sections_completed"] == 2
    assert result["section_completion"] == "2 / 3"
    assert result["section_states"] == {"Header": "completed", "Hero": "blocked", "Footer": "completed"}
    assert (tmp_path / "site_000/src/components/Header.tsx").read_text() == result["files"]["src/components/Header.tsx"]
    assert not (tmp_path / "site_000/src/components/Hero.tsx").exists()
    assert len(runner.calls) == 4
    blocked_event = next(e for e in events if e.get("section") == "Hero" and e.get("status") == "blocked")
    assert blocked_event["completed"] == 1


def test_syntax_failures_do_not_write_draft_or_fallback(tmp_path, fast_gates):
    result, _, _ = run_site(tmp_path, [section_write("Hero", "BROKEN"), section_write("Hero", "BROKEN")], ["Hero"], 2)
    assert_blocked(result, ["Hero"])
    assert result["sections_completed"] == 0
    assert result["section_states"] == {"Hero": "blocked"}
    assert result["files"] == {}
    assert not (tmp_path / "site_000/src/components/Hero.tsx").exists()
    assert next(log for log in result["turn_logs"] if log["action"] == "section_blocked")["reason"] == "parser_error"


def test_typescript_failure_blocks_without_overwriting_accepted_section(tmp_path, fast_gates, monkeypatch):
    def tsc(command, **kwargs):
        broken = "Hero.tsx" in " ".join(command)
        return SimpleNamespace(returncode=1 if broken else 0, stdout="TS1005: syntax error" if broken else "", stderr="")

    monkeypatch.setattr(site_agent, "run_command", tsc)
    result, _, _ = run_site(tmp_path, [section_write("Header"), section_write("Hero")], ["Header", "Hero"], 2)
    assert_blocked(result, ["Hero"])
    assert result["sections_completed"] == 1
    assert result["section_states"] == {"Header": "completed", "Hero": "blocked"}
    assert (tmp_path / "site_000/src/components/Header.tsx").read_text() == result["files"]["src/components/Header.tsx"]
    assert not (tmp_path / "site_000/src/components/Hero.tsx").exists()
    assert next(log for log in result["turn_logs"] if log["action"] == "section_blocked")["reason"] == "typescript_error"


def test_budget_exhaustion_blocks_remaining_without_files(tmp_path, fast_gates):
    result, _, events = run_site(tmp_path, [section_write("Header")], ["Header", "Hero", "Footer"], 1)
    assert_blocked(result, ["Hero", "Footer"])
    assert result["section_states"] == {"Header": "completed", "Hero": "blocked", "Footer": "blocked"}
    assert result["sections_completed"] == 1
    assert len(result["files"]) == 2
    assert all(log["reason"] == "budget_exhausted" for log in result["turn_logs"] if log["action"] == "section_blocked")
    assert all(e["completed"] == 1 for e in events if e.get("status") == "blocked")


def test_no_action_cap_writes_no_fallback_files(tmp_path, fast_gates):
    result, _, _ = run_site(tmp_path, ["not a tool call", "still not a tool call"], ["Hero"], 2)
    assert_blocked(result, ["Hero"])
    assert result["files"] == {}
    assert not list((tmp_path / "site_000").rglob("*.tsx"))
    assert next(log for log in result["turn_logs"] if log["action"] == "section_blocked")["reason"] == "no_action"


def test_cancellation_keeps_unattempted_sections_pending(tmp_path, fast_gates):
    result, runner, _ = run_site(tmp_path, [], ["Hero", "Footer"], 2, stop_check=lambda: True)
    assert runner.calls == []
    assert result["blocked_sections"] == []
    assert result["section_states"] == {"Hero": "pending", "Footer": "pending"}
    assert result["sections_completed"] == 0
    assert result["files"] == {}
