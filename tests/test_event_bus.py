"""
tests/test_event_bus.py - Blueprint Event Bus & "One Stream, Two Interfaces" Tests

Validates:
1. Full 13-event blueprint taxonomy (AgentEventType)
2. "One stream, two interfaces" dual representation (to_chat_message() vs to_log_line())
3. EventBus pub/sub architecture and subscriber queues
4. TaskEventEmitter drop-in queue compatibility and auto-enrichment
5. Backward compatibility for legacy queue readers (text, status, result)
6. SafeExecutor & DependencyManager typed event emissions
"""

import json
import queue
import time
from unittest.mock import Mock, patch
import pytest

from server.event_bus import (
    AgentEvent,
    AgentEventType,
    EventBus,
    TaskEventEmitter,
    event_bus,
)
from agent.safe_executor import SafeExecutor, ExecutionResult
from agent.dependency_manager import DependencyManager


# ── 1. Taxonomy Tests ─────────────────────────────────────────────────────────

def test_event_types_taxonomy():
    """Verify that all 13 authoritative blueprint event types exist."""
    expected = [
        "agent.status",
        "activity.started",
        "activity.updated",
        "activity.completed",
        "file.created",
        "file.modified",
        "command.started",
        "command.output",
        "command.completed",
        "build.result",
        "preview.ready",
        "task.completed",
        "task.failed",
    ]
    actual = [e.value for e in AgentEventType]
    for exp in expected:
        assert exp in actual, f"Missing blueprint event type: {exp}"


# ── 2. "One Stream, Two Interfaces" Dual Representation ──────────────────────

def test_command_started_dual_presentation():
    """Verify that command.started maps to friendly chat and technical log."""
    evt = AgentEvent(
        type=AgentEventType.COMMAND_STARTED,
        data={"command": "npm run build", "cwd": "/workspace"},
    )
    chat = evt.to_chat_message()
    log = evt.to_log_line()

    assert "Checking the build" in chat or "npm run build" in chat
    assert "◌" in chat
    assert "[Command] Started: npm run build" in log
    assert "(cwd: /workspace)" in log
    assert evt.iso_timestamp in log


def test_command_completed_dual_presentation():
    """Verify that command.completed maps to friendly outcome and exit code log."""
    # Success
    evt_ok = AgentEvent(
        type=AgentEventType.COMMAND_COMPLETED,
        data={"command": "npm run build", "exit_code": 0, "duration_ms": 820.0},
    )
    assert "✓ Build passed" in evt_ok.to_chat_message()
    assert "820" in evt_ok.to_chat_message()
    assert "[Command] Exited with code 0: npm run build" in evt_ok.to_log_line()

    # Failure
    evt_fail = AgentEvent(
        type=AgentEventType.COMMAND_COMPLETED,
        data={"command": "npm run build", "exit_code": 1, "duration_ms": 300.0},
    )
    assert "✗ `npm run build` failed (exit code 1)" in evt_fail.to_chat_message()
    assert "Exited with code 1" in evt_fail.to_log_line()


def test_file_events_dual_presentation():
    """Verify that file.created and file.modified format appropriately."""
    evt_created = AgentEvent(
        type=AgentEventType.FILE_CREATED,
        data={"path": "src/components/Hero.tsx", "chars": 1420},
    )
    assert "+ Created `src/components/Hero.tsx`" in evt_created.to_chat_message()
    assert "[File] Created src/components/Hero.tsx" in evt_created.to_log_line()

    evt_mod = AgentEvent(
        type=AgentEventType.FILE_MODIFIED,
        data={"path": "src/components/Hero.tsx", "diff_summary": "(+10 / -2 lines)"},
    )
    assert "~ Updated `src/components/Hero.tsx`" in evt_mod.to_chat_message()
    assert "[File] Modified src/components/Hero.tsx" in evt_mod.to_log_line()


def test_build_result_dual_presentation():
    """Verify that build.result formats summary for chat and diagnostics for log."""
    evt_pass = AgentEvent(
        type=AgentEventType.BUILD_RESULT,
        data={"passed": True, "errors": [], "warnings": []},
    )
    assert "✓ TypeScript & Production build passed" in evt_pass.to_chat_message()
    assert "[Build] Result: passed=True errors=0" in evt_pass.to_log_line()

    evt_fail = AgentEvent(
        type=AgentEventType.BUILD_RESULT,
        data={"passed": False, "errors": ["Line 1: TS2304", "Line 2: TS2307"]},
    )
    assert "✗ Build failed with 2 diagnostic issues" in evt_fail.to_chat_message()
    assert "[Build] Result: passed=False errors=2" in evt_fail.to_log_line()


def test_preview_ready_dual_presentation():
    """Verify preview.ready representation."""
    evt = AgentEvent(
        type=AgentEventType.PREVIEW_READY,
        data={"url": "http://127.0.0.1:5174", "port": 5174, "mode": "site"},
    )
    assert "🚀 Preview running at http://127.0.0.1:5174" in evt.to_chat_message()
    assert "[Preview] Ready at http://127.0.0.1:5174" in evt.to_log_line()


# ── 3. Backward Compatibility Serialization ──────────────────────────────────

def test_event_serialization_backward_compatibility():
    """Verify that to_dict() provides typed fields plus text and status aliases."""
    evt = AgentEvent(
        type=AgentEventType.AGENT_STATUS,
        data={"status": "Planning project…"},
    )
    d = evt.to_dict()

    assert d["type"] == "agent.status"
    assert "chat" in d
    assert "log" in d
    assert "timestamp" in d
    assert "iso_time" in d
    # Backward compatibility aliases
    assert d["status"] == "Planning project…"
    assert d["text"] == d["log"]


# ── 4. EventBus Pub/Sub Lifecycle ─────────────────────────────────────────────

def test_event_bus_subscription_and_dispatch():
    """Verify that published events reach all subscribers for a given task_id."""
    bus = EventBus()
    task_id = "task-test-123"

    sub1 = bus.subscribe(task_id)
    sub2 = bus.subscribe(task_id)

    bus.publish(task_id, AgentEvent(
        type=AgentEventType.COMMAND_STARTED,
        data={"command": "npm run build"},
    ))

    msg1 = sub1.get(timeout=1)
    msg2 = sub2.get(timeout=1)

    assert msg1["type"] == "command.started"
    assert msg2["type"] == "command.started"
    assert msg1["chat"] == msg2["chat"]

    # Late subscriber replay
    sub3 = bus.subscribe(task_id)
    msg3 = sub3.get(timeout=1)
    assert msg3["type"] == "command.started"

    # Unsubscribe
    bus.unsubscribe(task_id, sub1)
    bus.clear_task(task_id)


# ── 5. TaskEventEmitter Drop-in Queue & Auto-Conversion ───────────────────────

def test_task_event_emitter_as_queue():
    """Verify that TaskEventEmitter behaves as an authentic queue.Queue with auto-conversion."""
    bus = EventBus()
    task_id = "emitter-task-456"
    emitter = TaskEventEmitter(task_id, bus)

    assert isinstance(emitter, queue.Queue)

    # Put raw legacy string dictionary
    emitter.put({"type": "log", "text": "Creating Header.tsx"})

    # Read from emitter
    item = emitter.get(timeout=1)
    assert item["type"] == "file.created"
    assert "chat" in item
    assert "log" in item
    assert item["text"] == "Creating Header.tsx"


def test_task_event_emitter_typed_helpers():
    """Verify TaskEventEmitter typed helper methods."""
    bus = EventBus()
    task_id = "emitter-typed-789"
    emitter = TaskEventEmitter(task_id, bus)

    emitter.command_started("npm run build")
    item1 = emitter.get(timeout=1)
    assert item1["type"] == "command.started"
    assert "build" in item1["chat"]

    emitter.build_result(passed=True)
    item2 = emitter.get(timeout=1)
    assert item2["type"] == "build.result"
    assert item2["passed"] is True

    emitter.preview_ready("http://127.0.0.1:5173")
    item3 = emitter.get(timeout=1)
    assert item3["type"] == "preview.ready"
    assert "http://127.0.0.1:5173" in item3["chat"]


# ── 6. SafeExecutor & DependencyManager Integration ───────────────────────────

def test_safe_executor_emits_blueprint_events(tmp_path):
    """Verify that SafeExecutor emits typed command.started and command.completed events."""
    events = []
    executor = SafeExecutor()

    with patch.object(executor, "_resolve_executable", return_value="npm"), \
         patch("subprocess.Popen") as mock_popen:
        proc = Mock()
        proc.communicate.return_value = (b"1.0.0\n", b"")
        proc.returncode = 0
        mock_popen.return_value = proc

        res = executor.execute(["npm", "--version"], cwd=tmp_path, event_callback=events.append)
        assert res.success is True
        assert len(events) == 2

        # First event: command.started
        assert events[0]["type"] == "command.started"
        assert events[0]["status"] == "running"
        assert events[0]["command"] == "npm --version"

        # Second event: command.completed
        assert events[1]["type"] == "command.completed"
        assert events[1]["status"] == "completed"
        assert events[1]["returncode"] == 0
        assert events[1]["exit_code"] == 0


def test_dependency_manager_emits_activity_event(tmp_path, monkeypatch):
    """Verify that DependencyManager emits activity.started when installing packages."""
    events = []
    (tmp_path / "package.json").write_text('{"dependencies": {}}', encoding="utf-8")

    dm = DependencyManager(tmp_path, event_callback=events.append)
    fake_res = ExecutionResult(command=["npm"], returncode=0, stdout="installed", stderr="", success=True, duration_ms=10.0)
    monkeypatch.setattr(dm.executor, "execute", lambda *args, **kwargs: fake_res)

    res = dm.install_package("three")
    assert res["success"] is True

    # Check that an activity.started event was emitted
    act_events = [e for e in events if e.get("type") == "activity.started"]
    assert len(act_events) >= 1
    assert "three" in act_events[0]["package"]
