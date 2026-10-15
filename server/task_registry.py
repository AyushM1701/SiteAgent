"""Locked task lifecycle and replayable per-task event storage."""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class TaskState(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    CANCELLING = "cancelling"
    CANCELLED = "cancelled"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


_LEGAL = {
    TaskState.QUEUED: {TaskState.RUNNING, TaskState.CANCELLING, TaskState.CANCELLED},
    TaskState.RUNNING: {TaskState.CANCELLING, TaskState.SUCCEEDED, TaskState.FAILED, TaskState.CANCELLED},
    TaskState.CANCELLING: {TaskState.CANCELLED, TaskState.FAILED},
    TaskState.CANCELLED: set(), TaskState.SUCCEEDED: set(), TaskState.FAILED: set(),
}


@dataclass
class TaskRecord:
    task_id: str
    state: TaskState = TaskState.QUEUED
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    error: Optional[str] = None


class EventBuffer:
    """Bounded append-only event log. Cursors are independent per subscriber."""
    def __init__(self, max_events: int = 512):
        self.max_events = max_events
        self._events: List[Tuple[int, Dict[str, Any]]] = []
        self._next_id = 1
        self._condition = threading.Condition()

    def append(self, event: Dict[str, Any]) -> int:
        with self._condition:
            event_id = self._next_id
            self._next_id += 1
            self._events.append((event_id, dict(event)))
            if len(self._events) > self.max_events:
                self._events = self._events[-self.max_events:]
            self._condition.notify_all()
            return event_id

    def since(self, last_id: int = 0) -> List[Tuple[int, Dict[str, Any]]]:
        with self._condition:
            return [(eid, dict(event)) for eid, event in self._events if eid > last_id]

    def wait_since(self, last_id: int, timeout: float = 3.0) -> List[Tuple[int, Dict[str, Any]]]:
        with self._condition:
            events = [(eid, dict(event)) for eid, event in self._events if eid > last_id]
            if events:
                return events
            self._condition.wait(timeout)
            return [(eid, dict(event)) for eid, event in self._events if eid > last_id]


class TaskRegistry:
    def __init__(self, max_tasks: int = 512):
        self.max_tasks = max_tasks
        self._lock = threading.RLock()
        self._tasks: Dict[str, TaskRecord] = {}
        self._events: Dict[str, EventBuffer] = {}

    def register(self, task_id: str) -> TaskRecord:
        with self._lock:
            record = TaskRecord(task_id)
            self._tasks[task_id] = record
            self._events[task_id] = EventBuffer()
            while len(self._tasks) > self.max_tasks:
                oldest = next(iter(self._tasks))
                self._tasks.pop(oldest, None)
                self._events.pop(oldest, None)
            return record

    def transition(self, task_id: str, state: TaskState, error: Optional[str] = None) -> TaskRecord:
        with self._lock:
            record = self._tasks.get(task_id) or self.register(task_id)
            if state not in _LEGAL[record.state] and state != record.state:
                raise ValueError(f"Illegal task transition {record.state.value} -> {state.value}")
            record.state = state
            record.updated_at = time.time()
            record.error = error
            return record

    def get(self, task_id: str) -> Optional[TaskRecord]:
        with self._lock:
            return self._tasks.get(task_id)

    def buffer(self, task_id: str) -> EventBuffer:
        with self._lock:
            return self._events.setdefault(task_id, EventBuffer())

    def cancel_queued(self) -> List[str]:
        with self._lock:
            ids = [tid for tid, rec in self._tasks.items() if rec.state == TaskState.QUEUED]
            for tid in ids:
                self.transition(tid, TaskState.CANCELLED)
            return ids
