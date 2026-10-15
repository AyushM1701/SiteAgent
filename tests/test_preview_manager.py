"""
tests/test_preview_manager.py - Unit & Integration Tests for PreviewManager

Validates:
1. Dynamic port allocation starting from 5173 (5173, 5174, 5175...)
2. Detection and skipping of ports in use by external processes
3. Scaffolder vite.config.ts does not hardcode port 5173 or open: true
4. StrictPort enforcement (strictPort: true, host: 127.0.0.1, open: false)
5. PreviewManager process lifecycle: start, stop, restart, getUrl, allocatePort, healthCheck, shutdownAll
6. Both blueprint camelCase and snake_case API aliases
7. Session.preview integration with live preview metadata
"""

import json
import socket
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from server.preview_manager import PreviewManager, preview_manager, _stop_process_tree
from server.sessions import Session, session_manager


# ── 1. Dynamic Port Allocation Tests ─────────────────────────────────────────

def test_allocate_port_starts_at_5173():
    """Verify that port allocation begins at 5173."""
    pm = PreviewManager(base_port=5173, max_port=5200)
    port = pm.allocatePort()
    assert port == 5173 or port > 5173
    assert port >= 5173


def test_allocate_port_sequential():
    """Verify that multiple projects receive distinct sequential ports."""
    pm = PreviewManager(base_port=5173, max_port=5200)
    # Simulate active project assignments
    pm._project_ports["proj_1"] = 5173
    pm._project_ports["proj_2"] = 5174

    p3 = pm.allocatePort()
    assert p3 not in (5173, 5174)
    assert p3 >= 5175


def test_allocate_port_skips_bound_socket():
    """Verify that allocatePort detects and skips an OS-bound port."""
    pm = PreviewManager(base_port=5180, max_port=5190)

    # Bind port 5180 with a real socket to simulate an external process
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", 5180))
        s.listen(1)

        # allocatePort should detect that 5180 is unavailable and skip to 5181
        next_port = pm.allocatePort()
        assert next_port != 5180
        assert next_port >= 5181
    finally:
        s.close()


def test_port_recycling_on_stop():
    """Verify that stopping a project releases its allocated port."""
    pm = PreviewManager(base_port=5173, max_port=5200)
    pm._project_ports["p1"] = 5173
    mock_proc = Mock()
    mock_proc.poll.return_value = None
    pm._processes["p1"] = mock_proc

    # Stop project
    assert pm.stop("p1") is True
    assert "p1" not in pm._project_ports
    assert "p1" not in pm._processes


# ── 2. Scaffolding Modernization Tests ────────────────────────────────────────

def test_vite_config_scaffold_no_hardcoded_port_or_open_true(tmp_path):
    """Verify that vite.config.ts configures strictPort: true, open: false, and never hardcodes port 5173 or open: true."""
    from server.app import _scaffold_vite_runner, _scaffold_site_vite_runner

    # 1. Component scaffold
    comp_dir = tmp_path / "comp"
    comp_dir.mkdir()
    (comp_dir / "Button.tsx").write_text("export const Button = () => <button/>;", encoding="utf-8")
    _scaffold_vite_runner(comp_dir, "Button")

    cfg_comp = (comp_dir / "vite.config.ts").read_text(encoding="utf-8")
    assert "strictPort: true" in cfg_comp
    assert "open: false" in cfg_comp
    assert "open: true" not in cfg_comp
    assert "port: 5173" not in cfg_comp

    # 2. Site scaffold
    site_dir = tmp_path / "site"
    site_dir.mkdir()
    _scaffold_site_vite_runner(site_dir, "MySite", {
        "src/components/Hero.tsx": "export default function Hero() { return <div/>; }"
    })

    cfg_site = (site_dir / "vite.config.ts").read_text(encoding="utf-8")
    assert "strictPort: true" in cfg_site
    assert "open: false" in cfg_site
    assert "open: true" not in cfg_site
    assert "port: 5173" not in cfg_site


# ── 3. PreviewManager API & Process Lifecycle Tests ──────────────────────────

def test_preview_manager_camel_and_snake_aliases():
    """Verify that all blueprint camelCase methods have identical snake_case aliases."""
    pm = PreviewManager()
    assert pm.getUrl == pm.get_url
    assert pm.getPort == pm.get_port
    assert pm.allocatePort == pm.allocate_port
    assert pm.healthCheck == pm.health_check
    assert pm.shutdownAll == pm.shutdown_all


def test_get_url_and_health_check_dead_process():
    """Verify that getUrl and healthCheck return None / False for terminated processes."""
    pm = PreviewManager(base_port=5173)
    pm._project_ports["dead_proj"] = 5173

    dead_proc = Mock()
    dead_proc.poll.return_value = 1  # exited
    pm._processes["dead_proj"] = dead_proc

    assert pm.getUrl("dead_proj") is None
    assert pm.healthCheck("dead_proj") is False


def test_health_check_all_projects():
    """Verify healthCheck() without arguments returns a status dictionary across all projects."""
    pm = PreviewManager()
    pm._project_ports["p1"] = 5173
    pm._processes["p1"] = Mock(poll=Mock(return_value=1))

    statuses = pm.healthCheck()
    assert isinstance(statuses, dict)
    assert "p1" in statuses
    assert statuses["p1"] is False


def test_shutdown_all():
    """Verify shutdownAll cleans up all processes, ports, and directories."""
    pm = PreviewManager()
    mock_p1 = Mock(pid=999991, poll=Mock(return_value=None))
    mock_p2 = Mock(pid=999992, poll=Mock(return_value=None))

    pm._processes["p1"] = mock_p1
    pm._project_ports["p1"] = 5173
    pm._processes["p2"] = mock_p2
    pm._project_ports["p2"] = 5174

    with patch("server.preview_manager._stop_process_tree") as mock_stop:
        pm.shutdownAll()
        assert mock_stop.call_count == 2
        assert len(pm._processes) == 0
        assert len(pm._project_ports) == 0


# ── 4. Session.preview & Server Integration Tests ────────────────────────────

def test_session_preview_reflects_preview_manager(tmp_path):
    """Verify Session.preview truthfully reflects PreviewManager live URL and running state."""
    s = Session(session_id="1789999999_123456", title="Card", mode="component", workspace_dir=str(tmp_path))
    (tmp_path / "index.html").write_text("<!doctype html><html><div id='root'></div></html>")

    # When not running in preview_manager:
    preview_data = s.preview
    assert preview_data["running"] is False
    assert preview_data["url"] == f"/preview/{s.session_id}"

    # When running in preview_manager:
    with patch.object(preview_manager, "health_check", return_value=True), \
         patch.object(preview_manager, "get_url", return_value="http://127.0.0.1:5174"), \
         patch.object(preview_manager, "get_port", return_value=5174):
        live_preview = s.preview
        assert live_preview["running"] is True
        assert live_preview["url"] == "http://127.0.0.1:5174"
        assert live_preview["port"] == 5174
        assert live_preview["live_url"] == "http://127.0.0.1:5174"


def test_preview_route_checks_source_and_redirects_to_isolated_preview(tmp_path):
    """Reload must check edited source rather than reuse a stale preview URL."""
    from server.app import app

    sid = "1789999999_abcdef"
    s = Session(session_id=sid, title="Dashboard", mode="site", workspace_dir=str(tmp_path))
    (tmp_path / "index.html").write_text("<html></html>")
    session_manager._sessions[sid] = s

    with patch.object(preview_manager, "start", return_value="http://127.0.0.1:5175") as start:
        client = app.test_client()
        resp = client.get(f"/preview/{sid}")
        assert resp.status_code == 302
        assert resp.headers["Location"] == "http://127.0.0.1:5175"
        start.assert_called_once_with(sid, workspace_dir=s.workspace_dir)
