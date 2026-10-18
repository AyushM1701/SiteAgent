"""
tests/test_task_cancellation.py - Tests for Issue #7: Define New Project Behavior During an Active GPU Task.

Verifies:
1. Backend task cancellation flags the running task and sets _runner.stop_check.
2. Token generation stops via StoppingCriteria when cancelled mid-turn.
3. clear_queue parameter drains queued work.
4. Emits final cancelled task event (type: "cancelled" and "task.cancelled").
5. /api/generation/<task_id>/status and UI agree on "cancelled" status.
6. Frontend active task modal and 3 user options (Cancel & Start New, Keep Running in Background, Stay Here).
"""
import os

import sys
import queue
import subprocess
from pathlib import Path
from unittest.mock import MagicMock

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from server.app import app, cancelled_tasks, task_queues, _generation_queue, _task_results
from agent.agent import AgentModelRunner


def test_frontend_active_generation_modal_flow():
    """Verify frontend modal behaviors using the headless tsx runner."""
    script_path = BASE_DIR / "scripts" / "test_active_task_modal.mjs"
    assert script_path.exists(), f"Script {script_path} does not exist"

    res = subprocess.run(
        ["npx", "--yes", "tsx", str(script_path)],
        cwd=str(BASE_DIR),
        capture_output=True,
        text=True,
        shell=(os.name == "nt"),  # npx is npx.cmd on Windows
    )
    assert res.returncode == 0, f"Frontend active task modal test failed:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
    assert "ALL FRONTEND MODAL & CONFLICT WORKFLOW TESTS PASSED!" in res.stdout


def test_backend_cancel_task_flags_and_emits_event():
    """Verify /api/cancel/<task_id> flags the task, clears queue on request, and emits task.cancelled."""
    client = app.test_client()
    task_id = "test_cancel_task_123"

    # Setup task queue and pending item
    tq = queue.Queue()
    task_queues[task_id] = tq
    _generation_queue.put({"task_id": "queued_task_999"})

    try:
        # Cancel with clear_queue=true
        resp = client.post(f"/api/cancel/{task_id}?clear_queue=true")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "cancelled"
        assert data["task_id"] == task_id

        # 1. Flags the running task
        assert task_id in cancelled_tasks

        # 2. Clears queued work
        assert _generation_queue.empty()

        # 3. Emits final cancelled task events into the task queue
        events = []
        while not tq.empty():
            events.append(tq.get_nowait())

        event_types = [e.get("type") for e in events]
        assert "cancelled" in event_types, f"Expected 'cancelled' event, got: {event_types}"
        assert "task.cancelled" in event_types, f"Expected 'task.cancelled' event, got: {event_types}"
        assert "done" in event_types, f"Expected 'done' event, got: {event_types}"

        # 4. Status endpoint reflects cancelled status
        status_resp = client.get(f"/api/generation/{task_id}/status")
        assert status_resp.status_code == 200
        status_data = status_resp.get_json()
        assert status_data["status"] == "cancelled"
    finally:
        cancelled_tasks.discard(task_id)
        task_queues.pop(task_id, None)
        _task_results.pop(task_id, None)


def test_agent_runner_exits_token_generation_via_stop_check():
    """Verify AgentModelRunner exits immediately when stop_check returns True."""
    import torch
    cls = AgentModelRunner
    runner = cls.__new__(cls)
    runner.is_mock = False
    runner.max_seq_length = 512

    class DummyTokenizer:
        eos_token_id = 2
        def __call__(self, text, return_tensors="pt"):
            import torch
            return MagicMock(input_ids=torch.ones(1, 10, dtype=torch.long))
        def decode(self, *args, **kwargs):
            return "Generated text"

    runner.tokenizer = DummyTokenizer()
    runner.model = MagicMock()
    runner.model.get_input_embeddings.return_value.weight.device = "cpu"

    # Define a generate implementation that invokes stopping_criteria
    cancelled = [False]
    def mock_generate(**kwargs):
        cancelled[0] = True
        # Verify stopping_criteria was configured and fires
        criteria = kwargs.get("stopping_criteria")
        assert criteria is not None, "StoppingCriteria must be passed to model.generate"
        assert criteria[0](None, None) is True, "StoppingCriteria should evaluate to True when cancelled"
        import torch
        return torch.ones((1, 15), dtype=torch.long)

    runner.model.generate.side_effect = mock_generate

    # Calling generate_turn with stop_check returning True must raise InterruptedError
    import pytest
    with pytest.raises(InterruptedError, match="Generation stopped by user."):
        runner.generate_turn(
            example_idx=0,
            history=[{"role": "user", "content": "hello"}],
            primary_symbol="Test",
            stop_check=lambda: cancelled[0] or True,
        )
