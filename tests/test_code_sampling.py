"""Code-writing turns (component mode, runtime edits, project repair) state their
sampling explicitly, so the runner's defaults — tuned for the design kit's JSON copy —
never silently change how code is written."""
import ast
from pathlib import Path
from types import SimpleNamespace

import pytest

from agent.agent import CODE_SAMPLING, execute_runtime_edit_policy, run_agent_on_example

ROOT = Path(__file__).resolve().parents[1]
SAMPLING_KEYS = {"temperature", "repetition_penalty", "top_p", "top_k"}


def _generate_turn_calls(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "generate_turn":
            yield node


@pytest.mark.parametrize("rel", ["agent/agent.py", "server/app.py"])
def test_every_generation_call_states_its_sampling(rel):
    missing = []
    for call in _generate_turn_calls(ROOT / rel):
        given = {kw.arg for kw in call.keywords}
        if None in given:  # **kwargs pass-through (the mock engine delegate)
            continue
        if not SAMPLING_KEYS <= given:
            missing.append((call.lineno, sorted(SAMPLING_KEYS - given)))
    assert not missing, f"{rel}: generate_turn calls inherit runner defaults: {missing}"


class _Recorder:
    is_mock = True
    max_seq_length = 8192
    last_generation_tokens = 10
    last_context_tokens = 100
    last_generation_diagnostics = {}

    def __init__(self, reply):
        self.reply = reply
        self.calls = []

    def generate_turn(self, **kwargs):
        self.calls.append(kwargs)
        return self.reply


def test_component_mode_uses_code_sampling(tmp_path, monkeypatch):
    monkeypatch.setattr("agent.agent.run_command", lambda *a, **kw: SimpleNamespace(returncode=0, stdout="", stderr=""))
    runner = _Recorder('<tool_call name="write_component">\nexport function Badge() { return <span>Hi</span>; }\n</tool_call>')
    item = {"prompt": "Create a Badge component.", "primary_export": "Badge",
            "test_code": "test('renders', () => {});", "check": "tsc_only"}
    run_agent_on_example(0, item, runner, tmp_path, max_turns=1, temperature=0.15)
    assert runner.calls
    for call in runner.calls:
        assert call["top_p"] == CODE_SAMPLING["top_p"] and call["top_k"] == CODE_SAMPLING["top_k"]
    assert runner.calls[0]["temperature"] == 0.15
    assert runner.calls[0]["repetition_penalty"] == CODE_SAMPLING["repetition_penalty"]


def test_runtime_edit_policy_uses_code_sampling(tmp_path):
    (tmp_path / "Button.tsx").write_text("export function Button() { return <button>Go</button>; }", encoding="utf-8")
    (tmp_path / "package.json").write_text('{"dependencies": {"react": "^19.0.0"}}', encoding="utf-8")
    runner = _Recorder("<finish>done</finish>")
    execute_runtime_edit_policy("Button.tsx", tmp_path, runner, "Add an aria-label.", primary_symbol="Button")
    call = runner.calls[0]
    assert call["repetition_penalty"] == CODE_SAMPLING["repetition_penalty"]
    assert call["top_p"] == CODE_SAMPLING["top_p"] and call["top_k"] == CODE_SAMPLING["top_k"]
