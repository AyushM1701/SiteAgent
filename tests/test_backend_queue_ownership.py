"""
tests/test_backend_queue_ownership.py
Verifies backend queue ownership lifecycle, authoritative positions,
disk persistence across restarts, and state events.
"""

import json
import pytest
from server.app import (
    app,
    session_manager,
    event_bus,
    _dispatch_prompt_queue,
    _dispatch_task_start,
    _dispatch_task_cancel,
    _project_queued_prompts,
)

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c

def test_dispatch_prompt_queue_assigns_task_id_and_position(tmp_path):
    # Setup test session
    sess = session_manager.create_session(title="TestQueueProject", mode="site", prompt="Initial hero")
    pid = sess.session_id

    # Subscribe to event bus for project
    event_queue = event_bus.subscribe_project(pid)

    try:
        # 1. Queue first prompt
        res1 = _dispatch_prompt_queue(pid, "Make the hero more cinematic")
        assert res1["status"] == "queued"
        assert res1["position"] == 1
        assert "taskId" in res1
        assert res1["taskId"] == res1["task_id"]
        tid1 = res1["taskId"]

        # Verify event bus emitted task.queued or activity.started with queue metadata
        evt1 = event_queue.get(timeout=2.0)
        assert evt1.get("type") in ("task.queued", "activity.started")
        assert evt1.get("data", {}).get("taskId") == tid1
        assert evt1.get("data", {}).get("position") == 1

        # 2. Queue second prompt
        res2 = _dispatch_prompt_queue(pid, "Add pricing table with 3 tiers")
        assert res2["status"] == "queued"
        assert res2["position"] == 2
        assert "taskId" in res2
        tid2 = res2["taskId"]

        # Verify event bus emitted task.queued or activity.started for second prompt
        evt2 = event_queue.get(timeout=2.0)
        assert evt2.get("type") in ("task.queued", "activity.started")
        assert evt2.get("data", {}).get("taskId") == tid2
        assert evt2.get("data", {}).get("position") == 2

        # 3. Verify session disk persistence
        reloaded_sess = session_manager.get_session(pid)
        assert len(reloaded_sess.queued_prompts) == 2
        assert reloaded_sess.queued_prompts[0]["taskId"] == tid1
        assert reloaded_sess.queued_prompts[0]["position"] == 1
        assert reloaded_sess.queued_prompts[1]["taskId"] == tid2
        assert reloaded_sess.queued_prompts[1]["position"] == 2

    finally:
        event_bus.unsubscribe_project(pid, event_queue)
        _project_queued_prompts.pop(pid, None)

def test_get_session_info_returns_authoritative_queue(client):
    sess = session_manager.create_session(title="QueueFetchTest", mode="component", prompt="Button")
    pid = sess.session_id

    try:
        _dispatch_prompt_queue(pid, "Make button green")
        _dispatch_prompt_queue(pid, "Add hover pulse effect")

        res = client.get(f"/api/projects/{pid}")
        assert res.status_code == 200
        data = res.get_json()

        # Both top-level and nested project access must have queued_prompts
        assert "queued_prompts" in data
        assert len(data["queued_prompts"]) == 2
        assert data["queued_prompts"][0]["position"] == 1
        assert data["queued_prompts"][0]["prompt"] == "Make button green"
        assert data["queued_prompts"][1]["position"] == 2
        assert data["queued_prompts"][1]["prompt"] == "Add hover pulse effect"

        # Check /api/tasks/:taskId/status endpoint for queued task
        tid1 = data["queued_prompts"][0]["taskId"]
        status_res = client.get(f"/api/tasks/{tid1}/status")
        assert status_res.status_code == 200
        status_data = status_res.get_json()
        assert status_data["status"] == "queued"
        assert status_data["position"] == 1

    finally:
        _project_queued_prompts.pop(pid, None)

def test_task_cancel_clears_backend_queue():
    sess = session_manager.create_session(title="CancelQueueTest", mode="site", prompt="Header")
    pid = sess.session_id

    try:
        _dispatch_prompt_queue(pid, "Queued prompt 1")
        _dispatch_prompt_queue(pid, "Queued prompt 2")

        assert len(_project_queued_prompts.get(pid, [])) == 2
        assert len(sess.queued_prompts) == 2

        # Cancel
        res = _dispatch_task_cancel(pid, reason="User clicked cancel")
        assert res["status"] == "cancelled"

        # Verify backend queue in memory and on disk are cleared
        assert len(_project_queued_prompts.get(pid, [])) == 0
        reloaded = session_manager.get_session(pid)
        assert len(reloaded.queued_prompts) == 0

    finally:
        _project_queued_prompts.pop(pid, None)

def test_auto_dequeue_updates_disk_and_queue():
    sess = session_manager.create_session(title="AutoDequeueTest", mode="component", prompt="Search")
    pid = sess.session_id

    try:
        res1 = _dispatch_prompt_queue(pid, "Add search icon")
        res2 = _dispatch_prompt_queue(pid, "Add autocomplete dropdown")

        assert len(sess.queued_prompts) == 2
        assert _project_queued_prompts[pid][0]["taskId"] == res1["taskId"]

        # Simulate completion of previous turn triggering auto-dequeue of next prompt
        next_item = _project_queued_prompts[pid].pop(0)
        sess.queued_prompts = [
            {
                "taskId": q.get("taskId") or q.get("task_id"),
                "task_id": q.get("taskId") or q.get("task_id"),
                "prompt": q["prompt"],
                "position": idx + 1,
                "status": "queued",
            }
            for idx, q in enumerate(_project_queued_prompts[pid])
        ]
        sess.save()

        # Check remaining on disk
        reloaded = session_manager.get_session(pid)
        assert len(reloaded.queued_prompts) == 1
        assert reloaded.queued_prompts[0]["taskId"] == res2["taskId"]
        assert reloaded.queued_prompts[0]["position"] == 1

    finally:
        _project_queued_prompts.pop(pid, None)

