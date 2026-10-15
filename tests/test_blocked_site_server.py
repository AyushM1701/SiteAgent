"""Blocked agent results must remain blocked through server export and reporting."""

import queue
from types import SimpleNamespace

import pytest


@pytest.mark.parametrize("accepted", [True, False])
def test_blocked_site_preserves_only_accepted_files_without_project_repair(monkeypatch, tmp_path, accepted):
    import agent
    import agent.dependency_manager
    import server.app as app
    import site_brief

    files = ({"src/components/Header.tsx": "export function Header() { return <header>OK</header>; }"}
             if accepted else {})
    blocked = [{"section": "hero", "reason": "parser rejected JSX"}]
    monkeypatch.setattr(app, "BASE_DIR", tmp_path)
    monkeypatch.setattr(site_brief, "generate_content_brief", lambda *a, **kw: {"sections": ["header", "hero"]})
    monkeypatch.setattr(site_brief, "brief_to_xml", lambda brief: "<brief />")
    monkeypatch.setattr(agent, "run_site_agent_on_example", lambda **kw: {
        "files": files, "blocked_sections": blocked, "sections_completed": int(accepted),
        "sections_planned": ["header", "hero"], "generation_complete": False,
        "generation_quality": "blocked", "final_passed": False,
    })
    monkeypatch.setattr(agent.dependency_manager, "ensure_runtime_packages", lambda *a, **kw: [])
    session = SimpleNamespace(
        session_id="test_blocked", workspace_dir=tmp_path / "session", history=[],
        checkpoints=[], preview=None, context_tokens=0, title="Test", build_state={},
        create_checkpoint=lambda label: 1, save=lambda: None,
    )
    session.workspace_dir.mkdir()
    monkeypatch.setattr(app.session_manager, "create_session", lambda **kw: session)
    monkeypatch.setattr(app, "_scaffold_site_vite_runner", lambda *a, **kw: None)
    monkeypatch.setattr(app, "verify_and_repair_project", lambda **kw: pytest.fail("blocked site entered project repair"))
    results = []
    monkeypatch.setattr(app, "_store_task_result", lambda task_id, data: results.append(data))
    monkeypatch.setattr(app, "_append_history", lambda data: None)
    task = {"task_id": "blocked_test", "prompt": "Build site", "symbol": "Test"}
    events = queue.Queue()
    app._run_site_generation(task, events)

    result = results[0]
    assert result["status"] == "blocked"
    assert result["completion_status"] == "BLOCKED"
    assert result["final_passed"] is False
    assert result["generation_complete"] is False
    assert result["generation_quality"] == "blocked"
    assert result["blocked_sections"] == blocked
    assert "parser rejected JSX" in result["summary"]
    assert result["validation"]["passed"] is False
    assert result["files"] == files
    assert not (session.workspace_dir / "src/components/Hero.tsx").exists()
    assert (session.workspace_dir / "src/components/Header.tsx").exists() is accepted
    assert session.current_plan[1]["status"] == "blocked"
    assert next(item for item in list(events.queue) if item["type"] == "result")["data"] is result


def test_blocked_task_status_does_not_default_to_completed(monkeypatch):
    import server.app as app

    monkeypatch.setattr(app, "_get_task_result", lambda task_id: {
        "task_id": task_id, "status": "blocked", "blocked_sections": ["hero"]
    })
    with app.app.test_client() as client:
        payload = client.get("/api/generation/example/status").get_json()
    assert payload["status"] == "blocked"
    assert payload["data"]["blocked_sections"] == ["hero"]
