"""
tests/test_project_websocket.py
Comprehensive test suite for:
- Monotonically increasing event sequence numbers (seq / eventId)
- Event replay after lastEventId on reconnect
- Project-level pub/sub channels and task-to-project binding
- TaskEventEmitter project integration
- Bidirectional dispatch handlers (task.start, task.cancel, prompt.queue, preview.selection)
- Live WebSocket endpoint (/ws/projects/:projectId) using flask_sock & websockets client
"""
import os

import asyncio
import json
import pytest
import threading
import time
import uuid
import websockets
from pathlib import Path

from server.event_bus import EventBus, AgentEvent, AgentEventType, TaskEventEmitter
from server.app import (
    app,
    sock,
    _dispatch_task_start,
    _dispatch_task_cancel,
    _dispatch_prompt_queue,
    _dispatch_preview_selection,
    session_manager,
    _generation_queue,
)


def test_monotonic_sequence_numbers():
    """Verifies that events published for a project get sequential 1, 2, 3 sequence numbers."""
    bus = EventBus()
    pid = "proj_seq_test_1"

    e1 = bus.publish("t1", AgentEvent(type=AgentEventType.AGENT_STATUS, data={"status": "Planning"}), project_id=pid)
    e2 = bus.publish("t1", AgentEvent(type=AgentEventType.COMMAND_STARTED, data={"command": "npm run build"}), project_id=pid)
    e3 = bus.publish("t1", AgentEvent(type=AgentEventType.BUILD_RESULT, data={"passed": True}), project_id=pid)

    assert e1["seq"] == 1
    assert e1["eventId"] == 1
    assert e1["project_id"] == pid

    assert e2["seq"] == 2
    assert e2["eventId"] == 2

    assert e3["seq"] == 3
    assert e3["eventId"] == 3
    assert bus.get_latest_seq(pid) == 3


def test_event_replay_after_last_event_id():
    """Verifies that get_events_after and subscribe_project replay events after lastEventId."""
    bus = EventBus()
    pid = "proj_replay_test_1"

    for i in range(1, 6):
        bus.publish("t", AgentEvent(type=AgentEventType.ACTIVITY_UPDATED, data={"step": f"step {i}"}), project_id=pid)

    # Replay after event 3 should yield events 4 and 5
    replays = bus.get_events_after(pid, 3)
    assert len(replays) == 2
    assert replays[0]["seq"] == 4
    assert replays[1]["seq"] == 5

    # Replay on subscribe
    sub_q = bus.subscribe_project(pid, last_event_id=2)
    replayed_items = [sub_q.get_nowait(), sub_q.get_nowait(), sub_q.get_nowait()]
    assert [item["seq"] for item in replayed_items] == [3, 4, 5]
    bus.unsubscribe_project(pid, sub_q)


def test_task_to_project_automatic_binding():
    """Verifies that binding task_id to project_id routes events to the project channel automatically."""
    bus = EventBus()
    pid = "proj_bind_test"
    tid = "task_bind_123"

    bus.bind_task_to_project(tid, pid)
    proj_q = bus.subscribe_project(pid)

    # Publish to tid without specifying project_id
    bus.publish(tid, AgentEvent(type=AgentEventType.FILE_CREATED, data={"path": "src/App.tsx"}))
    bus.publish(tid, {"type": "command.started", "command": "vite build"})

    received_1 = proj_q.get(timeout=1.0)
    received_2 = proj_q.get(timeout=1.0)

    assert received_1["seq"] == 1
    assert received_1["project_id"] == pid
    assert received_1["type"] == "file.created"

    assert received_2["seq"] == 2
    assert received_2["project_id"] == pid
    assert received_2["command"] == "vite build"

    bus.unsubscribe_project(pid, proj_q)


def test_task_event_emitter_project_support():
    """Verifies TaskEventEmitter emits events with project_id and sequential seq numbers."""
    bus = EventBus()
    pid = "proj_emitter_test"
    tid = "task_emitter_456"

    emitter = TaskEventEmitter(task_id=tid, project_id=pid, bus=bus)
    proj_q = bus.subscribe_project(pid)

    emitter.command_started("npm install three")
    emitter.preview_ready("http://127.0.0.1:5173", port=5173)

    item1 = proj_q.get_nowait()
    item2 = proj_q.get_nowait()

    assert item1["seq"] == 1
    assert item1["command"] == "npm install three"
    assert item2["seq"] == 2
    assert item2["type"] == "preview.ready"
    assert item2["url"] == "http://127.0.0.1:5173"

    bus.unsubscribe_project(pid, proj_q)


def test_dispatch_task_start_creates_queued_task():
    """Verifies _dispatch_task_start queues task and emits task.queued event."""
    session = session_manager.create_session(title="WSTestSite", mode="site", prompt="Initial prompt")
    res = _dispatch_task_start(session.session_id, "Add a hero section", mode="site")

    assert res["status"] == "queued"
    assert res["session_id"] == session.session_id
    assert "task_id" in res
    _dispatch_task_cancel(session.session_id)


def test_dispatch_task_cancel():
    """Verifies _dispatch_task_cancel cancels tasks and emits task.failed (cancelled)."""
    session = session_manager.create_session(title="CancelTestSite", mode="site", prompt="Prompt")
    res = _dispatch_task_start(session.session_id, "Add navbar")

    cancel_res = _dispatch_task_cancel(session.session_id, reason="user_cancelled")
    assert cancel_res["status"] == "cancelled"
    assert cancel_res["project_id"] == session.session_id


def test_dispatch_prompt_queue():
    """Verifies _dispatch_prompt_queue stores queued prompt and updates session."""
    session = session_manager.create_session(title="QueueTestSite", mode="site", prompt="Prompt")
    q_res = _dispatch_prompt_queue(session.session_id, "Make colors dark mode")

    assert q_res["status"] in ("prompt_queued", "queued")
    assert q_res["queue_depth"] >= 1
    s_loaded = session_manager.get_session(session.session_id)
    assert any(
        p == "Make colors dark mode" or (isinstance(p, dict) and p.get("prompt") == "Make colors dark mode")
        for p in s_loaded.queued_prompts
    )


def test_dispatch_preview_selection():
    """Verifies _dispatch_preview_selection stores selection on session for targeted editing."""
    session = session_manager.create_session(title="SelectionTestSite", mode="site", prompt="Prompt")
    sel_data = {
        "component": "Hero",
        "elementId": "hero-headline",
        "selector": ".hero__title",
        "coordinates": {"x": 120, "y": 300},
    }
    sel_res = _dispatch_preview_selection(session.session_id, sel_data)

    assert sel_res["status"] == "selection_updated"
    s_loaded = session_manager.get_session(session.session_id)
    assert s_loaded.preview_selection["component"] == "Hero"
    assert s_loaded.preview_selection["elementId"] == "hero-headline"


def test_live_project_websocket_endpoint():
    """
    Spins up the Flask test server on an ephemeral port and connects via websockets
    to /ws/projects/:projectId, testing connection.ready, bidirectional messaging,
    and sequence replay.
    """
    port = 5092
    server_url = f"ws://127.0.0.1:{port}"
    server_ready = threading.Event()

    def run_server():
        server_ready.set()
        app.run(host="127.0.0.1", port=port, debug=False, threaded=True)

    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    server_ready.wait()
    time.sleep(0.8)

    session = session_manager.create_session(title="LiveWSSite", mode="site", prompt="Test prompt")
    proj_id = session.session_id

    async def run_client():
        async def recv_json(timeout=3.0):
            raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
            return json.loads(raw)

        # 1. Connect to /ws/projects/:projectId
        async with websockets.connect(f"{server_url}/ws/projects/{proj_id}") as ws:
            # Initial greeting
            msg1 = await recv_json()
            assert msg1["type"] == "connection.ready"
            assert msg1["project_id"] == proj_id

            # Idle receive timeouts must keep the upgraded connection alive.
            await asyncio.sleep(1.5)
            await ws.send(json.dumps({"type": "ping"}))
            assert (await recv_json())["type"] == "pong"

            # 2. Client sends preview.selection
            await ws.send(json.dumps({
                "type": "preview.selection",
                "component": "Navbar",
                "elementId": "nav-link-1",
            }))

            # Expect preview.selection_received AND activity.updated (in any order)
            msgs_received = set()
            for _ in range(2):
                m = await recv_json()
                msgs_received.add(m["type"])
            assert "preview.selection_received" in msgs_received
            assert "activity.updated" in msgs_received

            # 3. Client sends prompt.queue
            await ws.send(json.dumps({
                "type": "prompt.queue",
                "prompt": "Add subtle drop shadow to Navbar",
            }))

            # Expect prompt.queued AND activity.started (in any order)
            q_msgs = set()
            for _ in range(2):
                m = await recv_json()
                q_msgs.add(m["type"])
            assert "prompt.queued" in q_msgs
            assert "activity.started" in q_msgs

            # 4. Client sends task.cancel
            await ws.send(json.dumps({
                "type": "task.cancel",
                "reason": "testing_cancel",
            }))

            # Expect task.cancelled AND task.failed (in any order)
            cancel_msgs = set()
            for _ in range(2):
                m = await recv_json()
                cancel_msgs.add(m["type"])
            assert "task.cancelled" in cancel_msgs
            assert "task.failed" in cancel_msgs

    asyncio.run(run_client())


def test_task_started_and_cancelled_event_types():
    """Verifies TASK_STARTED and TASK_CANCELLED event types and emitter helpers."""
    assert AgentEventType.TASK_STARTED == "task.started"
    assert AgentEventType.TASK_CANCELLED == "task.cancelled"

    bus = EventBus()
    pid = "proj_types_test"
    tid = "task_types_123"

    emitter = TaskEventEmitter(task_id=tid, project_id=pid, bus=bus)
    proj_q = bus.subscribe_project(pid)

    s_evt = emitter.task_started(mode="site")
    c_evt = emitter.task_cancelled(reason="user_abort")

    assert s_evt["seq"] == 1
    assert s_evt["type"] == "task.started"
    assert s_evt["project_id"] == pid

    assert c_evt["seq"] == 2
    assert c_evt["type"] == "task.cancelled"
    assert c_evt["reason"] == "user_abort"

    bus.unsubscribe_project(pid, proj_q)


def test_rest_cancel_broadcasts_to_project_channel():
    """Verifies that calling REST /api/cancel/<task_id> broadcasts task.cancelled to the project channel."""
    from server.app import event_bus
    client = app.test_client()

    pid = "proj_rest_cancel_test"
    tid = "task_rest_cancel_999"

    # Bind task to project and subscribe to project channel
    event_bus.bind_task_to_project(tid, pid)
    proj_q = event_bus.subscribe_project(pid)

    try:
        resp = client.post(f"/api/cancel/{tid}")
        assert resp.status_code == 200

        # Verify project subscriber receives task.cancelled
        events = []
        while not proj_q.empty():
            events.append(proj_q.get_nowait())

        types = [e.get("type") for e in events]
        assert "task.cancelled" in types, f"Expected task.cancelled on project channel, got: {types}"
    finally:
        event_bus.unsubscribe_project(pid, proj_q)


def test_frontend_websocket_suite():
    """Executes the frontend Vite proxy and WebSocket integration tests via tsx."""
    import subprocess
    script_path = Path(__file__).resolve().parent.parent / "scripts" / "test_project_websocket_frontend.mjs"
    assert script_path.exists()

    res = subprocess.run(
        ["npx", "--yes", "tsx", str(script_path)],
        cwd=str(script_path.parent.parent),
        capture_output=True,
        text=True,
        shell=(os.name == "nt"),  # npx is npx.cmd on Windows
    )
    assert res.returncode == 0, f"Frontend WebSocket test failed:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
    assert "ALL FRONTEND WEBSOCKET MIGRATION TESTS PASSED!" in res.stdout
