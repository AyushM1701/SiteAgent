"""Regressions for model ownership, authentication and generated-content checks."""
import ast
import hashlib
import hmac
import json
import os
from pathlib import Path
import queue
import re
import subprocess
import threading
import time
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load_definitions(path, names, namespace):
    """Load production definitions without starting server/model side effects."""
    tree = ast.parse((ROOT / path).read_text(encoding="utf-8-sig"))
    nodes = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n.name in names]
    for node in nodes:
        if hasattr(node, "decorator_list"):
            node.decorator_list = []
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), "exec"), namespace)
    return namespace


def test_timeout_retains_model_ownership_until_generation_exits():
    started, release = threading.Event(), threading.Event()
    calls = []
    real_thread = threading.Thread

    class ImmediateTimeoutThread(real_thread):
        def join(self, timeout=None):
            # Simulate expiry without waiting forty minutes.
            if timeout is not None:
                started.wait(2)
                return
            return super().join()

    def generate(task, events):
        calls.append(task["task_id"])
        if task["task_id"] == "first":
            started.set()
            assert release.wait(5)

    tasks = queue.Queue()
    for task in ({"task_id": "first"}, {"task_id": "second"}, None):
        tasks.put(task)
    ns = dict(_generation_queue=tasks, task_queues={}, cancelled_tasks=set(),
              _runner=SimpleNamespace(stop_check=None), _runner_lock=threading.Lock(),
              _model_status="ready", _current_task=None,
              threading=SimpleNamespace(Thread=ImmediateTimeoutThread),
              _run_generation=generate, _run_site_generation=generate,
              _run_session_edit_turn=generate)
    load_definitions("server/app.py", {"_worker"}, ns)
    worker = real_thread(target=ns["_worker"], daemon=True)
    worker.start()
    try:
        assert started.wait(2)
        deadline = time.monotonic() + 2
        while "first" not in ns["cancelled_tasks"] and time.monotonic() < deadline:
            time.sleep(.01)
        assert "first" in ns["cancelled_tasks"]
        assert ns["_model_status"] == "busy"
        assert ns["_current_task"]["task_id"] == "first"
        assert ns["_runner_lock"].locked()
        assert calls == ["first"]
    finally:
        release.set()
        worker.join(3)
    assert not worker.is_alive()
    assert calls == ["first", "second"]
    assert ns["_runner"].stop_check is None


def test_cancel_does_not_release_active_model():
    ns = dict(_current_task={"task_id": "active"}, _model_status="busy",
              cancelled_tasks=set(), task_queues={}, _generation_queue=queue.Queue(),
              request=SimpleNamespace(args={}, is_json=False), jsonify=lambda x: x)
    load_definitions("server/app.py", {"cancel_task"}, ns)
    ns["cancel_task"]("active")
    assert ns["_current_task"] == {"task_id": "active"}
    assert ns["_model_status"] == "busy"


def test_shell_auth_fails_closed_and_rejects_ticket_replay():
    ns = dict(AUTH_TOKEN="", hmac=hmac, hashlib=hashlib, time=time, DEBUG=False, _SEEN_NONCES={})
    load_definitions("server/shell_server.py", {"_verify_shell_token", "_clean_stale_nonces"}, ns)
    verify = ns["_verify_shell_token"]
    assert not verify("anything")
    ns["AUTH_TOKEN"] = "secret"
    assert not verify({"token": "secret"})
    assert verify("secret")
    stamp = int(time.time())
    sig = hmac.new(b"secret", f"{stamp}:nonce".encode(), hashlib.sha256).hexdigest()
    ticket = f"{stamp}.nonce.{sig}"
    assert verify(ticket)
    assert not verify(ticket)


@pytest.mark.parametrize("css", [
    ":root{--a:#fff}body{color:#123456}",
    '.dark:root-ish{color:#123456}',
    ':root{--text:"}";--a:#fff}body{color:#123456}',
    '@media screen{:root{--a:#fff}body{color:#123456}}',
    ':root{--a:#fff;color:#123456}',
])
def test_css_cannot_hide_colors_after_root(css):
    from agent.style_ingest import StyleSpec, validate_css_conformance
    assert validate_css_conformance(css, StyleSpec(name="test", colors={"--a": "#fff"}))


def test_css_root_token_definitions_are_allowed():
    from agent.style_ingest import StyleSpec, validate_css_conformance
    assert not validate_css_conformance(':root{--a:#123456}body{color:var(--a)}', StyleSpec(name="test", colors={"--a": "#123456"}))


def test_multisection_prompt_routing():
    ns = dict(re=re, _SITE_PATTERNS=[], _SITE_KEYWORDS=[])
    load_definitions("server/app.py", {"_classify_intent_with_confidence"}, ns)
    classify = ns["_classify_intent_with_confidence"]
    assert classify("build me something for my bakery with a menu, about section, and contact form")[0] == "site"
    assert classify("a reusable component with menu, about and contact links")[0] == "component"


def test_command_timeout_output_is_text(monkeypatch):
    from training.evaluate import run_command
    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired("tsc", 1, output=b"partial \xff")
    monkeypatch.setattr(subprocess, "run", timeout)
    result = run_command(["tsc"], timeout=1)
    assert isinstance(result.stdout, str)
    assert "partial" in result.stdout + result.stderr


def test_windows_process_tree_cleanup():
    ns = dict(os=SimpleNamespace(name="nt"), subprocess=SimpleNamespace(run=Mock(), DEVNULL=-3, TimeoutExpired=subprocess.TimeoutExpired))
    load_definitions("agent/visual_judge.py", {"_stop_process_tree"}, ns)
    proc = Mock(pid=1234)
    ns["_stop_process_tree"](proc)
    assert ns["subprocess"].run.call_args.args[0] == ["taskkill", "/F", "/T", "/PID", "1234"]
    proc.wait.assert_called_once_with(timeout=3)


def test_cpu_loader_skips_unsloth_and_uses_float32(monkeypatch, tmp_path):
    import sys
    from agent import base_model_fingerprint
    from agent import hardware
    torch = SimpleNamespace(cuda=SimpleNamespace(is_available=lambda: False),
                            float32="float32", float16="float16", bfloat16="bfloat16")
    model_loader, tokenizer_loader = Mock(), Mock()
    base = model_loader.from_pretrained.return_value
    base.to.return_value = base
    peft = SimpleNamespace(PeftModel=Mock())
    monkeypatch.setitem(sys.modules, "torch", torch)
    monkeypatch.setitem(sys.modules, "transformers", SimpleNamespace(AutoModelForCausalLM=model_loader, AutoTokenizer=tokenizer_loader))
    monkeypatch.setitem(sys.modules, "peft", peft)
    monkeypatch.setitem(sys.modules, "unsloth", None)  # importing it would raise
    monkeypatch.setattr(hardware, "_PROFILE", hardware.HardwareProfile("cpu", "transformers", False, "float32", 8192))
    adapter_dir = tmp_path / "adapter"
    adapter_dir.mkdir()
    (adapter_dir / "adapter_config.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(base_model_fingerprint, "verify_lora_adapter_compatibility", lambda *args: None)
    ns = dict(DEFAULT_INFERENCE_MAX_SEQ_LENGTH=8192, DEFAULT_MAX_NEW_TOKENS=4096,
              List=list, Dict=dict, Any=object, Path=Path, __file__=str(ROOT / "agent" / "agent.py"))
    load_definitions("agent/agent.py", {"AgentModelRunner"}, ns)
    runner = ns["AgentModelRunner"](str(adapter_dir))
    kwargs = model_loader.from_pretrained.call_args.kwargs
    assert kwargs["torch_dtype"] == "float32" and "quantization_config" not in kwargs
    base.to.assert_called_once_with("cpu")
    peft.PeftModel.from_pretrained.assert_called_once()  # the adapter is applied on the CPU base
    runner.model.eval.assert_called_once()


def test_generation_moves_to_embedding_device_and_stops(monkeypatch):
    import sys
    import torch
    from transformers import StoppingCriteria, StoppingCriteriaList
    # Exercise generation with real CPU tensors and a small fake model.
    ns = dict(DEFAULT_INFERENCE_MAX_SEQ_LENGTH=8192, DEFAULT_MAX_NEW_TOKENS=4096,
              List=list, Dict=dict, format_chatml=lambda *a, **k: "prompt", re=re)
    load_definitions("agent/agent.py", {"AgentModelRunner"}, ns)
    cls = ns["AgentModelRunner"]
    runner = cls.__new__(cls)
    runner.is_mock = False
    runner.stop_check = None
    runner.max_seq_length = 16

    class Inputs(dict):
        @property
        def input_ids(self):
            return self["input_ids"]
        def to(self, device):
            assert str(device) == "cpu"
            return self

    runner.tokenizer = Mock(return_value=Inputs(input_ids=torch.tensor([[1, 2]]), attention_mask=torch.ones(1, 2)))
    runner.tokenizer.eos_token_id = 0
    runner.tokenizer.decode.return_value = "done"
    runner.model = Mock()
    runner.model.get_input_embeddings.return_value.weight = torch.zeros(1)
    runner.model.generate.return_value = torch.tensor([[1, 2, 3]])
    assert runner.generate_turn(0, [], "Demo", max_new_tokens=4) == "done"
    with pytest.raises(ValueError):
        runner.generate_turn(0, [], "Demo", max_new_tokens=16)
    runner.stop_check = lambda: True
    with pytest.raises(InterruptedError):
        runner.generate_turn(0, [], "Demo", max_new_tokens=4)
    cancelled = [False]
    runner.stop_check = lambda: cancelled[0]
    def cancel_during_generate(**kwargs):
        cancelled[0] = True
        assert kwargs["stopping_criteria"][0](None, None)
        return torch.tensor([[1, 2, 3]])
    runner.model.generate.side_effect = cancel_during_generate
    with pytest.raises(InterruptedError):
        runner.generate_turn(0, [], "Demo", max_new_tokens=4)


def test_dynamic_context_headroom_clamping():
    import sys
    import torch
    ns = dict(DEFAULT_INFERENCE_MAX_SEQ_LENGTH=8192, DEFAULT_MAX_NEW_TOKENS=4096,
              List=list, Dict=dict, format_chatml=lambda *a, **k: "prompt", re=re)
    load_definitions("agent/agent.py", {"AgentModelRunner"}, ns)
    cls = ns["AgentModelRunner"]
    runner = cls.__new__(cls)
    runner.is_mock = False
    runner.stop_check = None
    runner.max_seq_length = 50

    class Inputs(dict):
        @property
        def input_ids(self):
            return self["input_ids"]
        def to(self, device):
            return self

    # Input length is 30, max_seq_length is 50. Request 40 new tokens (30 + 40 > 50).
    # With headroom, it should clamp max_new_tokens to fit within 50 without raising ValueError.
    runner.tokenizer = Mock(return_value=Inputs(input_ids=torch.ones(1, 30, dtype=torch.long), attention_mask=torch.ones(1, 30)))
    runner.tokenizer.eos_token_id = 0
    runner.tokenizer.decode.return_value = "done"
    runner.model = Mock()
    runner.model.get_input_embeddings.return_value.weight = torch.zeros(1)
    
    captured_kwargs = {}
    def mock_gen(**kwargs):
        captured_kwargs.update(kwargs)
        return torch.ones(1, 35, dtype=torch.long)
    runner.model.generate.side_effect = mock_gen

    out = runner.generate_turn(0, [], "Demo", max_new_tokens=40)
    assert out == "done"
    # Verify max_new_tokens was clamped to available budget (50 - 30 - margin <= 20)
    assert captured_kwargs["max_new_tokens"] < 40
    assert captured_kwargs["max_new_tokens"] <= 20



def test_markdown_link_scheme_allowlist():
    import shutil
    node = shutil.which("node")
    if not node:
        pytest.skip("Node unavailable")
    html_path = ROOT / "web_ui_static/index.monolith.html.bak"
    if not html_path.exists():
        html_path = ROOT / "web_ui_static/index.html"
    source = html_path.read_text(encoding="utf-8")
    start = source.index('    out = out.replace(/\\[')
    end = source.index('\n', source.index(': label);', start))
    statement = source[start:end]
    script = "const assert = require('node:assert/strict');\n"
    for url in ("javascript:alert", "data:text/html,test", "https://example.com", "HTTP://example.com"):
        script += "{let out=" + json.dumps(f"[click]({url})") + ";" + statement
        script += ";assert.equal(out.includes('<a ')," + str(url.lower().startswith("http")).lower() + ");}\n"
    subprocess.run([node, "-e", script], check=True, capture_output=True, text=True)


def test_site_envelope_recovery_and_autoclose():
    from agent.agent_protocol import site_envelope_errors

    # Verify that unclosed files are properly rejected
    incomplete_file = '<tool_call name="write_site"><file path="Hero.tsx">export default () => <div/>'
    assert site_envelope_errors(incomplete_file)

    # Verify that auto-closing tags when files are complete resolves missing tool_call
    complete_content = '<tool_call name="write_site"><file path="Hero.tsx">export default () => <div/></file><file path="Hero.css">.hero{}</file>'
    # Before closing tag
    assert site_envelope_errors(complete_content)
    # Auto-closing logic as implemented in agent.py
    open_files = re.findall(r'<file\s+path=["\'][^"\']+["\']\s*>', complete_content, re.I)
    close_files = complete_content.count('</file>')
    assert open_files and len(open_files) == close_files
    auto_closed = complete_content + "\n</tool_call>"
    assert not site_envelope_errors(auto_closed)
