"""Kit strategy integration (IMPLEMENTATION_PLAN_2026-10-16 §7): agent loop, runner sampling,
module identity and server scaffolding."""
import json
import re
from pathlib import Path

import pytest

from agent.agent import AgentModelRunner, run_site_agent_on_example
from agent.site_brief import brief_to_xml, generate_content_brief

PROMPT = ("Aster & Kiln — handmade ceramics studio in Lisbon. Warm editorial photography, clay textures. "
          "Sections: collection, glaze stories, care guide, studio notes. Email hello@asterkiln.com. No online checkout.")


class ScriptedRunner:
    """Stands in for AgentModelRunner: replies with JSON keyed on the section label."""

    is_mock = True
    max_seq_length = 8192

    def __init__(self, replies=None, default=None):
        self.calls = []
        self.replies = replies or {}
        self.default = default
        self.last_generation_tokens = 120
        self.last_context_tokens = 400
        self.last_generation_diagnostics = {"stop_reason": "eos"}

    def generate_turn(self, **kwargs):
        self.calls.append(kwargs)
        user = kwargs["history"][-1]["content"]
        label = re.search(r"Section: (.+)", user).group(1).strip()
        queue = self.replies.get(label)
        if isinstance(queue, list) and queue:
            return queue.pop(0)
        if isinstance(queue, str):
            return queue
        if self.default is not None:
            return self.default
        return json.dumps({"headline": f"{label} at Aster & Kiln", "title": label,
                           "lede": "Bowls, cups and vases thrown by hand in a small Lisbon studio.",
                           "intro": "Made slowly, one piece at a time.",
                           "items": [{"title": "Everyday bowls", "text": "Thrown by hand.", "name": "Everyday bowls",
                                      "description": "Stoneware for daily use.", "caption": "Stoneware.", "excerpt": "Notes."}],
                           "steps": [{"title": "Wash by hand", "text": "Warm water and a soft cloth."}],
                           "primary_cta": "See the collection", "secondary_cta": "Write to us", "tagline": "Ceramics studio"})


def _run(tmp_path, runner, events=None, stop_check=None, prompt=PROMPT):
    brief = generate_content_brief(prompt)
    return run_site_agent_on_example(
        orig_idx=0, prompt=prompt, project_name="AsterKiln", brief_xml=brief_to_xml(brief),
        sections=brief["sections"], runner=runner, workspace_root=tmp_path,
        event_callback=(events.append if events is not None else None), stop_check=stop_check,
        business_type=brief["business_type"], strategy="kit", brief=brief,
    )


def test_kit_strategy_builds_every_section_with_events(tmp_path):
    events = []
    runner = ScriptedRunner()
    result = _run(tmp_path, runner, events)

    assert result["blocked_sections"] == []
    assert result["generation_quality"] == "native"
    assert result["sections_planned"][0] == "header" and result["sections_planned"][-1] == "footer"
    for name in ("Header", "Hero", "Collection", "GlazeStories", "CareGuide", "StudioNotes", "Footer"):
        assert f"src/components/{name}.tsx" in result["files"]
        assert f"src/components/{name}.css" in result["files"]
        assert (Path(result["workspace_dir"]) / f"src/components/{name}.tsx").is_file()
    kit = result["kit"]
    assert ":root" in kit["base_css"] and "fonts.googleapis.com" in kit["font_href"]
    assert 'property="og:title"' in kit["head_tags"]
    assert {path for path, _ in kit["public_files"]} >= {"favicon.svg", "404.html"}
    assert kit["theme"]["id"] == "atelier"

    types = [e["type"] for e in events]
    assert types[0] == "plan" and "design_plan" in types
    design = next(e for e in events if e["type"] == "design_plan")["design_plan"]
    assert design["id"] == "atelier"
    completed = [e["section"] for e in events if e["type"] == "plan_update" and e["status"] == "completed"]
    assert completed == result["sections_planned"]
    assert not any(e.get("status") == "blocked" for e in events if e["type"] == "plan_update")

    # Header and footer are kit-owned; every other section asked the model once.
    assert len(runner.calls) == len(result["sections_planned"]) - 2
    call = runner.calls[0]
    assert (call["temperature"], call["top_p"], call["top_k"], call["repetition_penalty"]) == (0.7, 0.8, 20, 1.0)
    assert call["max_new_tokens"] <= 700
    assert result["validation"] is None and result["project_validation"] == "pending"


def test_unusable_output_retries_once_then_falls_back_without_blocking(tmp_path):
    runner = ScriptedRunner(replies={"Collection": ["not json", "still not json"]})
    result = _run(tmp_path, runner)
    collection_calls = [c for c in runner.calls if "Section: Collection" in c["history"][-1]["content"]]
    assert [c["temperature"] for c in collection_calls] == [0.7, 0.55]
    assert result["blocked_sections"] == []
    assert result["generation_quality"] == "repaired"
    assert "src/components/Collection.tsx" in result["files"]


def test_stop_check_ends_the_run_between_sections(tmp_path):
    runner = ScriptedRunner()
    calls = {"n": 0}

    def stop():
        calls["n"] += 1
        return calls["n"] > 3

    result = _run(tmp_path, runner, stop_check=stop)
    assert result["cancelled"] is True
    assert result["generation_complete"] is False


def test_kit_is_the_default_strategy(tmp_path, monkeypatch):
    monkeypatch.delenv("SITE_STRATEGY", raising=False)
    brief = generate_content_brief(PROMPT)
    result = run_site_agent_on_example(0, PROMPT, "AsterKiln", brief_to_xml(brief), brief["sections"],
                                       ScriptedRunner(), tmp_path)
    assert result.get("strategy") == "kit"
    monkeypatch.setenv("SITE_STRATEGY", "freeform")
    from agent.agent import resolve_site_strategy
    assert resolve_site_strategy(None) == "freeform"
    assert resolve_site_strategy("kit") == "kit"


# ── Runner sampling ─────────────────────────────────────────────────────────

class _FakeIds:
    def __init__(self, n):
        import torch
        self.input_ids = torch.zeros((1, n), dtype=torch.long)

    def to(self, _device):
        return self

    def __getitem__(self, key):
        return {"input_ids": self.input_ids}[key]

    def keys(self):
        return ["input_ids"]


class _FakeTokenizer:
    eos_token_id = 0

    def __call__(self, text, return_tensors=None):
        return _FakeIds(10)

    def get_vocab(self):
        return []

    def decode(self, tokens, skip_special_tokens=False):
        return '{"title": "ok"}'

    def apply_chat_template(self, messages, tokenize=False, add_generation_prompt=True, **kwargs):
        return "".join(m["content"] for m in messages)


class _FakeModel:
    def __init__(self):
        self.kwargs = None

    def get_input_embeddings(self):
        import torch
        class _E:
            weight = torch.zeros((1, 1))
        return _E()

    def generate(self, **kwargs):
        import torch
        self.kwargs = kwargs
        return torch.zeros((1, 14), dtype=torch.long)


def test_runner_passes_top_p_and_top_k_to_generate():
    runner = AgentModelRunner.__new__(AgentModelRunner)
    runner.is_mock = False
    runner.max_seq_length = 4096
    runner.model = _FakeModel()
    runner.tokenizer = _FakeTokenizer()
    runner.model_path = "fake"
    runner.generation_log_dir = None
    runner.stop_check = None
    runner.generate_turn(0, [{"role": "user", "content": "hi"}], "X", max_new_tokens=32,
                         temperature=0.7, top_p=0.8, top_k=20, repetition_penalty=1.0)
    kwargs = runner.model.kwargs
    assert kwargs["top_p"] == 0.8 and kwargs["top_k"] == 20 and kwargs["do_sample"] is True
    assert kwargs["repetition_penalty"] == 1.0


# ── Module identity (A3) ────────────────────────────────────────────────────

def test_registered_tokenizer_reaches_runtime_config():
    import agent.agent  # noqa: F401  (must not create a second agent_protocol module)
    from agent import agent_protocol
    from agent.config import ModelRuntimeConfig

    class CountingTokenizer:
        def encode(self, text, add_special_tokens=False):
            return list(range(7))

        def apply_chat_template(self, messages, tokenize=False, add_generation_prompt=True, **kwargs):
            return "TEMPLATE"

    # agent.py registers the loaded tokenizer through the name it imported;
    # that must be the same module agent.config reads from.
    import agent.agent as agent_module
    assert agent_module.set_default_tokenizer is agent_protocol.set_default_tokenizer
    agent_module.set_default_tokenizer(CountingTokenizer())
    try:
        assert ModelRuntimeConfig.count_tokens("anything at all") == 7
    finally:
        agent_protocol.set_default_tokenizer(None)


# ── Server scaffolding ──────────────────────────────────────────────────────

def test_scaffold_uses_kit_css_fonts_head_and_public_files(tmp_path):
    from server.app import _scaffold_site_vite_runner
    from agent.site_kit import KitSite

    brief = generate_content_brief(PROMPT)
    kit = KitSite(PROMPT, brief, brief["sections"])
    files = {}
    for slug in kit.sections:
        kit.accept(slug, "")
        files.update(dict(kit.render(slug)))
    brief.update({"kit_base_css": kit.base_css(), "kit_font_href": kit.font_href(),
                  "kit_head_tags": kit.head_tags(), "kit_public_files": kit.public_files()})
    _scaffold_site_vite_runner(tmp_path, "AsterKiln", files, brief=brief)

    app_css = (tmp_path / "src" / "App.css").read_text(encoding="utf-8")
    assert app_css.startswith("/* Atelier")
    assert "*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }" not in app_css  # A11
    assert "var(--bg-color, #000000)" not in app_css  # A11
    index = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert "family=Fraunces" in index and 'property="og:title"' in index
    assert "website built by ReactAgent SLM" not in index
    assert (tmp_path / "public" / "favicon.svg").is_file()
    assert (tmp_path / "public" / "apple-touch-icon.png").read_bytes()[:4] == b"\x89PNG"
    assert (tmp_path / "public" / "404.html").is_file()
    app = (tmp_path / "App.tsx").read_text(encoding="utf-8")
    assert "has no valid React export" not in app


def test_freeform_scaffold_has_an_honest_description(tmp_path):
    from server.app import _scaffold_site_vite_runner
    files = {"src/components/Hero.tsx": "export function Hero() { return <section><h1>Hi</h1></section>; }\n",
             "src/components/Hero.css": ".hero { color: red; }\n"}
    _scaffold_site_vite_runner(tmp_path, "Plain_Site", files, brief={"tagline": "Fresh bread daily in Leeds"})
    index = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert "website built by ReactAgent SLM" not in index
    assert 'name="description"' in index
    assert "has no valid React export" not in (tmp_path / "App.tsx").read_text(encoding="utf-8")


@pytest.mark.parametrize("prompt, name", [
    ("Aster & Kiln — handmade ceramics studio in Lisbon. Warm editorial photography.", "Aster_Kiln"),
    ("Northwind — a B2B analytics SaaS for logistics teams. Dark, technical look.", "Northwind"),
    ("Saffron Table — modern Indian restaurant in Dehradun. Menu, about the chef, private dining.", "Saffron_Table"),
    ("Portfolio for Maya Chen, a brand designer. Minimal, lots of white space.", "Maya_Chen"),
])
def test_server_project_name_uses_the_business_name(prompt, name):
    from server.app import _extract_project_name
    assert _extract_project_name(prompt) == name


def test_edit_turns_receive_the_kit_design_summary(tmp_path):
    from server.app import _kit_edit_note
    assert _kit_edit_note(tmp_path) == ""
    (tmp_path / "content_brief.json").write_text(json.dumps({"kit_edit_summary": "DESIGN KIT: theme 'Atelier'"}), encoding="utf-8")
    assert "DESIGN KIT: theme 'Atelier'" in _kit_edit_note(tmp_path)


def test_generate_endpoint_honours_the_full_site_toggle(monkeypatch):
    """The composer sends mode="site" from its Full Site / Component toggle; the
    keyword classifier must not override an explicit choice."""
    import queue as _queue
    import server.app as app_module
    captured = _queue.Queue()
    monkeypatch.setattr(app_module, "_generation_queue", captured)
    monkeypatch.setattr(app_module, "_model_status", "ready")
    monkeypatch.setattr(app_module, "_runner", object())
    client = app_module.app.test_client()
    prompt = "Northwind — a B2B analytics SaaS for logistics teams. Dark, technical look. Include a product preview and FAQ."
    assert app_module._classify_intent_with_confidence(prompt)[0] == "component"  # the keyword guess
    response = client.post("/api/generate", json={"prompt": prompt, "mode": "site"})
    assert response.get_json()["mode"] == "site"
    assert captured.get_nowait()["mode"] == "site"
