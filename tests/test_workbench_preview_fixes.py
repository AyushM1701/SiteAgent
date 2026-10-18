"""Workbench fixes: preview bridge, project file list, persisted logs, shell folder, section targeting."""
import json
from pathlib import Path

from server.preview_manager import BRIDGE_TAG, inject_bridge


def test_bridge_is_injected_once_before_head_close():
    html = b"<!doctype html><html><head><title>x</title></head><body></body></html>"
    once = inject_bridge(html)
    assert once.count(BRIDGE_TAG) == 1 and once.index(BRIDGE_TAG) < once.index(b"</head>")
    assert inject_bridge(once) == once


def test_bridge_script_exists_and_answers_the_workbench_protocol():
    source = (Path(__file__).resolve().parents[1] / "server" / "preview_bridge.js").read_text(encoding="utf-8")
    for message in ("workbench:inspect_mode", "workbench:dom_select", "workbench:restore_scroll",
                    "workbench:scroll_update", "workbench:ready", "workbench:runtime_error", "workbench:highlight"):
        assert message in source


def test_code_tab_files_exclude_pipeline_artifacts():
    from server.sessions import editable_files
    files = {"src/App.tsx": "a", "static-preview.html": "b", "content_brief.json": "c",
             "motion_runtime_evidence.json": "d", "src/components/Hero.tsx": "e"}
    assert sorted(editable_files(files)) == ["src/App.tsx", "src/components/Hero.tsx"]


def test_snapshots_skip_preview_builds_and_raw_generation(tmp_path):
    from agent.snapshot_manager import SnapshotManager
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "App.tsx").write_text("x", encoding="utf-8")
    for folder in (".workbench-preview", "raw_generation"):
        (tmp_path / folder).mkdir()
        (tmp_path / folder / "f.json").write_text("{}", encoding="utf-8")
    scanned = list(SnapshotManager(tmp_path).scan_workspace_files())
    assert "src/App.tsx" in scanned
    assert not [p for p in scanned if p.startswith((".workbench-preview/", "raw_generation/"))]


def test_event_log_lines_reach_the_sink():
    from server.event_bus import EventBus
    bus = EventBus()
    seen = []
    bus.log_sink = lambda pid, payload: seen.append((pid, payload["log"]))
    bus.publish("t1", {"type": "log", "text": "hello"}, project_id="p1")
    bus.publish("t2", {"type": "log", "text": "no project"})
    assert len(seen) == 1 and seen[0][0] == "p1" and "hello" in seen[0][1]


def test_shell_opens_only_inside_generated_projects(tmp_path):
    from server import shell_server
    project = shell_server.PROJECTS_ROOT / "session_test_shell_cwd"
    project.mkdir(parents=True, exist_ok=True)
    try:
        assert shell_server._shell_cwd(str(project)) == project.resolve()
        assert shell_server._shell_cwd(str(tmp_path)) == shell_server.REPO_ROOT
        assert shell_server._shell_cwd("") == shell_server.REPO_ROOT
    finally:
        project.rmdir()


def test_selected_kebab_section_targets_its_pascal_component():
    from agent.context_builder import ContextBuilder
    files = {"src/components/VisitUs.tsx": "x", "src/components/Hero.tsx": "y", "src/App.tsx": "z"}
    result = ContextBuilder().resolve_context_files(files, "make the heading bigger",
                                                    preview_selection={"component": "visit-us"})
    assert "src/components/VisitUs.tsx" in [path for path, _ in result["selected"]]
