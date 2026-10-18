"""
server/event_bus.py - Blueprint Event Bus & Typed Event Stream

Implements the Qwen3 blueprint event architecture:
- Replaces ad-hoc string queues with structured, strongly-typed events
- "One stream, two interfaces" dual presentation:
    * CHAT UI: Concise, human-friendly progress indicators, action cards, and statuses
    * LOGS Viewer: Formatted timestamped technical logs for terminal / debug streams
- Pub/Sub broker managing task event subscriptions
- Full backward-compatibility adapter for legacy queue listeners
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
import queue
import re
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Set, Union


class AgentEventType(str, Enum):
    """Authoritative event taxonomy specified in the Qwen3 blueprint."""
    AGENT_STATUS = "agent.status"
    ACTIVITY_STARTED = "activity.started"
    ACTIVITY_UPDATED = "activity.updated"
    ACTIVITY_COMPLETED = "activity.completed"
    FILE_CREATED = "file.created"
    FILE_MODIFIED = "file.modified"
    COMMAND_STARTED = "command.started"
    COMMAND_OUTPUT = "command.output"
    COMMAND_COMPLETED = "command.completed"
    BUILD_RESULT = "build.result"
    PREVIEW_READY = "preview.ready"
    TASK_STARTED = "task.started"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    TASK_CANCELLED = "task.cancelled"


@dataclass
class AgentEvent:
    """
    A strongly-typed event with dual presentation capabilities:
    - to_chat_message(): Concise friendly string for chat interfaces (e.g. '◌ Checking the build...')
    - to_log_line(): Standardized timestamped line for logs viewer (e.g. '20:41:12 [Build] npm run build')
    """
    type: Union[AgentEventType, str]
    timestamp: float = field(default_factory=time.time)
    data: Dict[str, Any] = field(default_factory=dict)
    task_id: Optional[str] = None
    project_id: Optional[str] = None
    seq: Optional[int] = None

    def __post_init__(self):
        if isinstance(self.type, AgentEventType):
            self.type = self.type.value

    @property
    def iso_timestamp(self) -> str:
        return datetime.fromtimestamp(self.timestamp).strftime("%H:%M:%S")

    def to_chat_message(self) -> str:
        """Friendly human-facing string for Chat stream."""
        t = self.type
        d = self.data

        if t == AgentEventType.AGENT_STATUS.value:
            return d.get("status") or d.get("text") or "Working…"
        elif t == AgentEventType.ACTIVITY_STARTED.value:
            act = d.get("activity") or d.get("title") or "Task"
            return f"◌ {act}…"
        elif t == AgentEventType.ACTIVITY_UPDATED.value:
            step = d.get("step") or d.get("status") or ""
            prog = f" ({d['progress']})" if "progress" in d else ""
            return f"◌ {step}{prog}"
        elif t == AgentEventType.ACTIVITY_COMPLETED.value:
            act = d.get("activity") or d.get("title") or "Task"
            dur = f" ({d['duration_ms']}ms)" if "duration_ms" in d else ""
            return f"✓ {act} completed{dur}"
        elif t == AgentEventType.FILE_CREATED.value:
            path = d.get("path") or d.get("file") or "file"
            chars = f" ({d['chars']} chars)" if "chars" in d else ""
            return f"+ Created `{path}`{chars}"
        elif t == AgentEventType.FILE_MODIFIED.value:
            path = d.get("path") or d.get("file") or "file"
            diff = f" ({d['diff_summary']})" if "diff_summary" in d else ""
            return f"~ Updated `{path}`{diff}"
        elif t == AgentEventType.COMMAND_STARTED.value:
            cmd = d.get("command") or "command"
            desc = d.get("description")
            if desc:
                return f"◌ {desc}"
            if "build" in cmd:
                return "◌ Checking the build…"
            elif "typecheck" in cmd or "tsc" in cmd:
                return "◌ Running TypeScript checks…"
            elif "install" in cmd:
                pkg = d.get("package") or cmd.split()[-1]
                return f"◌ Installing {pkg}…"
            return f"◌ Running `{cmd}`…"
        elif t == AgentEventType.COMMAND_OUTPUT.value:
            return ""  # Terminal output streams directly to logs
        elif t == AgentEventType.COMMAND_COMPLETED.value:
            cmd = d.get("command") or "Command"
            exit_code = d.get("exit_code", 0)
            dur = f" ({d['duration_ms']}ms)" if "duration_ms" in d else ""
            if exit_code == 0:
                if "build" in cmd:
                    return f"✓ Build passed{dur}"
                elif "typecheck" in cmd or "tsc" in cmd:
                    return f"✓ TypeScript checks passed{dur}"
                return f"✓ `{cmd}` completed{dur}"
            return f"✗ `{cmd}` failed (exit code {exit_code})"
        elif t == AgentEventType.BUILD_RESULT.value:
            passed = d.get("passed", False)
            if passed:
                return "✓ TypeScript & Production build passed"
            errs = len(d.get("errors", []))
            return f"✗ Build failed with {errs} diagnostic issue{'s' if errs != 1 else ''}"
        elif t == AgentEventType.PREVIEW_READY.value:
            url = d.get("url") or "preview"
            return f"🚀 Preview running at {url}"
        elif t == AgentEventType.TASK_STARTED.value:
            return "◌ Generation task started…"
        elif t == AgentEventType.TASK_CANCELLED.value:
            reason = d.get("reason") or "Task cancelled by user"
            return f"⊘ Task cancelled: {reason}"
        elif t == AgentEventType.TASK_COMPLETED.value:
            return "✓ Project tasks completed successfully"
        elif t == AgentEventType.TASK_FAILED.value:
            err = d.get("error") or "Task encountered an error"
            return f"✗ {err}"
        return d.get("text") or d.get("status") or str(t)

    def to_log_line(self) -> str:
        """Standardized technical timestamped log line for Logs stream."""
        ts = self.iso_timestamp
        t = self.type
        d = self.data

        if t == AgentEventType.AGENT_STATUS.value:
            status = d.get("status") or d.get("text") or ""
            return f"{ts} [Status] {status}"
        elif t == AgentEventType.ACTIVITY_STARTED.value:
            act = d.get("activity") or d.get("title") or "Activity"
            return f"{ts} [Activity] Started: {act}"
        elif t == AgentEventType.ACTIVITY_UPDATED.value:
            step = d.get("step") or d.get("status") or ""
            return f"{ts} [Activity] Progress: {step}"
        elif t == AgentEventType.ACTIVITY_COMPLETED.value:
            act = d.get("activity") or d.get("title") or "Activity"
            dur = f" in {d['duration_ms']}ms" if "duration_ms" in d else ""
            return f"{ts} [Activity] Completed: {act}{dur}"
        elif t == AgentEventType.FILE_CREATED.value:
            path = d.get("path") or d.get("file") or "unknown"
            chars = f" ({d['chars']} chars)" if "chars" in d else ""
            return f"{ts} [File] Created {path}{chars}"
        elif t == AgentEventType.FILE_MODIFIED.value:
            path = d.get("path") or d.get("file") or "unknown"
            diff = f" {d['diff_summary']}" if "diff_summary" in d else ""
            return f"{ts} [File] Modified {path}{diff}"
        elif t == AgentEventType.COMMAND_STARTED.value:
            cmd = d.get("command") or ""
            cwd = f" (cwd: {d['cwd']})" if "cwd" in d else ""
            return f"{ts} [Command] Started: {cmd}{cwd}"
        elif t == AgentEventType.COMMAND_OUTPUT.value:
            line = d.get("line") or d.get("output") or ""
            stream = d.get("stream", "stdout")
            return f"{ts} [{stream}] {line}"
        elif t == AgentEventType.COMMAND_COMPLETED.value:
            cmd = d.get("command") or ""
            code = d.get("exit_code", 0)
            dur = f" ({d['duration_ms']}ms)" if "duration_ms" in d else ""
            return f"{ts} [Command] Exited with code {code}: {cmd}{dur}"
        elif t == AgentEventType.BUILD_RESULT.value:
            passed = d.get("passed", False)
            err_count = len(d.get("errors", []))
            return f"{ts} [Build] Result: passed={passed} errors={err_count}"
        elif t == AgentEventType.PREVIEW_READY.value:
            url = d.get("url") or ""
            return f"{ts} [Preview] Ready at {url}"
        elif t == AgentEventType.TASK_STARTED.value:
            return f"{ts} [Task] Started"
        elif t == AgentEventType.TASK_CANCELLED.value:
            reason = d.get("reason") or "cancelled"
            return f"{ts} [Task] Cancelled: {reason}"
        elif t == AgentEventType.TASK_COMPLETED.value:
            return f"{ts} [Task] Finished successfully"
        elif t == AgentEventType.TASK_FAILED.value:
            err = d.get("error") or "Unknown error"
            return f"{ts} [Task] Failed: {err}"
        return f"{ts} [Log] {d.get('text') or d.get('status') or str(d)}"

    def to_dict(self) -> Dict[str, Any]:
        """
        Serializes the event for SSE payload.
        Includes typed event fields, dual representations (chat, log),
        and backward-compatible aliases (type, text, status, data).
        """
        chat_msg = self.to_chat_message()
        log_msg = self.to_log_line()

        res: Dict[str, Any] = {
            "type": self.type,
            "timestamp": self.timestamp,
            "iso_time": self.iso_timestamp,
            "chat": chat_msg,
            "log": log_msg,
            "data": self.data,
        }

        if self.task_id:
            res["task_id"] = self.task_id
        if self.project_id:
            res["project_id"] = self.project_id
        if self.seq is not None:
            res["seq"] = self.seq
            res["eventId"] = self.seq

        # Flattens top-level data fields directly into the dict for clean frontend access
        for k, v in self.data.items():
            if k not in res:
                res[k] = v

        # Backward-compatibility fields:
        # If legacy code checks msg["text"], provide the log or chat string
        if "text" not in res:
            res["text"] = log_msg
        # If legacy code checks msg["status"] on status events
        if self.type == AgentEventType.AGENT_STATUS.value and "status" not in res:
            res["status"] = self.data.get("status", chat_msg)

        return res


class EventBus:
    """
    In-memory pub/sub broker keyed by task_id and project_id.
    Dispatches AgentEvent instances to registered subscriber queues.
    Maintains monotonically increasing sequence numbers (seq) per project,
    enabling WebSocket clients to reconnect and request events after lastEventId.
    Also translates legacy queue messages into typed AgentEvents.
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._subscribers: Dict[str, Set[queue.Queue]] = {}
        self._history: Dict[str, List[Dict[str, Any]]] = {}
        self._project_seq: Dict[str, int] = {}
        self._project_subscribers: Dict[str, Set[queue.Queue]] = {}
        self._project_history: Dict[str, List[Dict[str, Any]]] = {}
        self._task_to_project: Dict[str, str] = {}
        self.MAX_PROJECT_HISTORY: int = 1000
        # Optional callable(project_id, payload) that persists log lines (set by the server).
        self.log_sink = None

    def bind_task_to_project(self, task_id: str, project_id: str) -> None:
        """Associates a task_id with a project_id for automatic project-channel routing."""
        with self._lock:
            self._task_to_project[task_id] = project_id

    def subscribe(self, task_id: str, last_event_id: Optional[int] = None) -> queue.Queue:
        """Registers a new listener queue for task_id events."""
        with self._lock:
            q: queue.Queue = queue.Queue()
            self._subscribers.setdefault(task_id, set()).add(q)
            # Replay history if subscriber connects after events began
            for event_dict in self._history.get(task_id, []):
                if last_event_id is None or event_dict.get("seq", 0) > last_event_id:
                    q.put(event_dict)
            return q

    def unsubscribe(self, task_id: str, q: queue.Queue) -> None:
        """Removes a subscriber queue."""
        with self._lock:
            subs = self._subscribers.get(task_id)
            if subs and q in subs:
                subs.remove(q)
            if subs is not None and not subs:
                self._subscribers.pop(task_id, None)

    def subscribe_project(self, project_id: str, last_event_id: Optional[int] = None) -> queue.Queue:
        """
        Registers a new listener queue for project_id events.
        If last_event_id is provided, replays all missed events where seq > last_event_id.
        """
        with self._lock:
            q: queue.Queue = queue.Queue()
            self._project_subscribers.setdefault(project_id, set()).add(q)
            if last_event_id is not None:
                for event_dict in self._project_history.get(project_id, []):
                    if event_dict.get("seq", 0) > last_event_id:
                        q.put(event_dict)
            return q

    def unsubscribe_project(self, project_id: str, q: queue.Queue) -> None:
        """Removes a project subscriber queue."""
        with self._lock:
            subs = self._project_subscribers.get(project_id)
            if subs and q in subs:
                subs.remove(q)
            if subs is not None and not subs:
                self._project_subscribers.pop(project_id, None)

    def get_events_after(self, project_id: str, last_event_id: int) -> List[Dict[str, Any]]:
        """Retrieves events for a project with sequence number greater than last_event_id."""
        with self._lock:
            return [
                d for d in self._project_history.get(project_id, [])
                if d.get("seq", 0) > last_event_id
            ]

    def get_latest_seq(self, project_id: str) -> int:
        """Returns the current monotonic sequence counter for project_id."""
        with self._lock:
            return self._project_seq.get(project_id, 0)

    def publish(
        self,
        task_id: str,
        event: Union[AgentEvent, Dict[str, Any]],
        project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Publishes an event to all subscribers of task_id and project_id.
        Assigns a monotonically increasing sequence number (seq) per project.
        Accepts either an AgentEvent instance or a raw dict (which is converted).
        """
        # Determine associated project_id
        pid = project_id
        if pid is None:
            if isinstance(event, AgentEvent):
                pid = event.project_id
            elif isinstance(event, dict):
                pid = event.get("project_id")
        if pid is None:
            with self._lock:
                pid = self._task_to_project.get(task_id)

        if isinstance(event, AgentEvent):
            event_obj = event
            if not event_obj.task_id:
                event_obj.task_id = task_id
            if pid and not event_obj.project_id:
                event_obj.project_id = pid
        elif isinstance(event, dict):
            event_obj = self._convert_legacy_dict(event, task_id)
            if pid and not event_obj.project_id:
                event_obj.project_id = pid
        else:
            raise TypeError(f"Expected AgentEvent or dict, got {type(event)}")

        payload = self._publish_locked(task_id, event_obj, pid)
        sink = self.log_sink
        if sink and pid and payload.get("log"):
            try:
                sink(pid, payload)
            except Exception:
                pass
        return payload

    def _publish_locked(self, task_id: str, event_obj: "AgentEvent", pid: Optional[str]) -> Dict[str, Any]:
        with self._lock:
            # If bound to a project, stamp monotonic sequence number
            if pid:
                self._project_seq[pid] = self._project_seq.get(pid, 0) + 1
                seq = self._project_seq[pid]
                event_obj.seq = seq
                event_obj.project_id = pid

            payload = event_obj.to_dict()

            # Store in task event history
            self._history.setdefault(task_id, []).append(payload)

            # Store in project event history (bounded ring buffer)
            if pid:
                proj_hist = self._project_history.setdefault(pid, [])
                proj_hist.append(payload)
                if len(proj_hist) > self.MAX_PROJECT_HISTORY:
                    self._project_history[pid] = proj_hist[-self.MAX_PROJECT_HISTORY:]

            # Dispatch to task subscribers
            subs = self._subscribers.get(task_id, set())
            for q in list(subs):
                try:
                    q.put(payload)
                except Exception:
                    pass

            # Dispatch to project subscribers (e.g. WebSocket connections)
            if pid:
                p_subs = self._project_subscribers.get(pid, set())
                for q in list(p_subs):
                    try:
                        q.put(payload)
                    except Exception:
                        pass

        return payload

    def clear_task(self, task_id: str) -> None:
        """Cleans up subscribers and history for a completed task."""
        with self._lock:
            self._subscribers.pop(task_id, None)
            self._history.pop(task_id, None)
            self._task_to_project.pop(task_id, None)

    def _convert_legacy_dict(self, d: Dict[str, Any], task_id: str) -> AgentEvent:
        """Converts legacy ad-hoc queue objects (e.g. {'type': 'log', 'text': '...'}) to AgentEvent."""
        raw_type = d.get("type", "log")
        data = {k: v for k, v in d.items() if k != "type"}

        if raw_type == "status":
            return AgentEvent(
                type=AgentEventType.AGENT_STATUS,
                task_id=task_id,
                data={"status": d.get("status", ""), "phase": d.get("phase", "running")},
            )
        elif raw_type == "status_change":
            return AgentEvent(
                type=AgentEventType.AGENT_STATUS,
                task_id=task_id,
                data={"status": d.get("status", ""), "is_change": True},
            )
        elif raw_type == "log":
            text = d.get("text", "")
            # Infer specific event types from log text patterns
            if "Creating " in text or "Written: " in text:
                match = re.search(r"(?:Written:\s*|Creating\s+)([^\s]+\.(?:tsx?|jsx?|css|json|html))", text)
                if not match:
                    return AgentEvent(type=AgentEventType.ACTIVITY_UPDATED, task_id=task_id,
                                      data={"step": text, "text": text})
                return AgentEvent(
                    type=AgentEventType.FILE_CREATED,
                    task_id=task_id,
                    data={"text": text, "path": match.group(1)},
                )
            elif "Running TypeScript checks" in text or "Running acceptance" in text:
                return AgentEvent(
                    type=AgentEventType.COMMAND_STARTED,
                    task_id=task_id,
                    data={"command": "npm run typecheck", "description": "Running TypeScript checks…", "text": text},
                )
            elif "Preview ready" in text:
                return AgentEvent(
                    type=AgentEventType.PREVIEW_READY,
                    task_id=task_id,
                    data={"text": text},
                )
            return AgentEvent(
                type=AgentEventType.ACTIVITY_UPDATED,
                task_id=task_id,
                data={"step": text, "text": text},
            )
        elif raw_type == "command":
            cmd = d.get("command", "")
            status = d.get("status", "running")
            if status == "running":
                return AgentEvent(
                    type=AgentEventType.COMMAND_STARTED,
                    task_id=task_id,
                    data={"command": cmd, "cwd": d.get("cwd")},
                )
            return AgentEvent(
                type=AgentEventType.COMMAND_COMPLETED,
                task_id=task_id,
                data={"command": cmd, "exit_code": d.get("exit_code", 0), "duration_ms": d.get("duration_ms", 0)},
            )
        elif raw_type == "result":
            result = d.get("data", {})
            blocked = result.get("status") in ("blocked", "failed", "cancelled")
            return AgentEvent(
                type=AgentEventType.TASK_FAILED if blocked else AgentEventType.TASK_COMPLETED,
                task_id=task_id,
                data={"result": result, "text": "Generation blocked; partial files saved" if blocked else "Task completed successfully"},
            )
        elif raw_type == "cancelled":
            return AgentEvent(
                type=AgentEventType.TASK_FAILED,
                task_id=task_id,
                data={"error": d.get("text", "Task cancelled by user"), "cancelled": True},
            )
        elif raw_type == "error":
            return AgentEvent(
                type=AgentEventType.TASK_FAILED,
                task_id=task_id,
                data={"error": d.get("text", "Task encountered an error")},
            )
        elif raw_type == "done":
            # Direct pass-through for stream termination
            return AgentEvent(
                type=AgentEventType.TASK_COMPLETED,
                task_id=task_id,
                data={"done": True, "text": "Stream finished"},
            )

        # Catch-all
        return AgentEvent(
            type=raw_type,
            task_id=task_id,
            data=data,
        )


class TaskEventEmitter(queue.Queue):
    """
    A queue.Queue subclass bound to a specific task_id on the EventBus.
    Any call to q.put(...) translates through event_bus.publish and enqueues the typed dict.
    Provides typed convenience emitters: q.status(), q.activity_start(), q.command_started(), etc.
    """

    def __init__(
        self,
        task_id: str,
        project_id: Optional[str] = None,
        bus: Optional[EventBus] = None,
        maxsize: int = 0,
    ):
        super().__init__(maxsize=maxsize)
        self.task_id = task_id
        self.project_id = project_id
        self.bus = bus if bus is not None else event_bus
        if project_id:
            self.bus.bind_task_to_project(task_id, project_id)

    def put(self, item: Any, block: bool = True, timeout: Optional[float] = None) -> None:
        """Queue put method that automatically publishes to the event bus."""
        if isinstance(item, dict) and self.project_id and "project_id" not in item:
            item["project_id"] = self.project_id
        payload = self.bus.publish(self.task_id, item, project_id=self.project_id)
        super().put(payload, block=block, timeout=timeout)

    def put_nowait(self, item: Any) -> None:
        self.put(item, block=False)

    def emit(self, event_type: Union[AgentEventType, str], **kwargs) -> Dict[str, Any]:
        """Direct typed emit helper."""
        event = AgentEvent(
            type=event_type,
            task_id=self.task_id,
            project_id=self.project_id,
            data=kwargs,
        )
        payload = self.bus.publish(self.task_id, event, project_id=self.project_id)
        super().put(payload, block=False)
        return payload

    def status(self, status_text: str, phase: str = "running") -> Dict[str, Any]:
        return self.emit(AgentEventType.AGENT_STATUS, status=status_text, phase=phase)

    def activity_start(self, activity: str, **kwargs) -> Dict[str, Any]:
        return self.emit(AgentEventType.ACTIVITY_STARTED, activity=activity, **kwargs)

    def activity_complete(self, activity: str, duration_ms: Optional[float] = None, **kwargs) -> Dict[str, Any]:
        return self.emit(AgentEventType.ACTIVITY_COMPLETED, activity=activity, duration_ms=duration_ms, **kwargs)

    def file_created(self, path: str, chars: int = 0, **kwargs) -> Dict[str, Any]:
        return self.emit(AgentEventType.FILE_CREATED, path=path, chars=chars, **kwargs)

    def file_modified(self, path: str, diff_summary: str = "", **kwargs) -> Dict[str, Any]:
        return self.emit(AgentEventType.FILE_MODIFIED, path=path, diff_summary=diff_summary, **kwargs)

    def command_started(self, command: str, description: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        return self.emit(AgentEventType.COMMAND_STARTED, command=command, description=description, **kwargs)

    def command_output(self, line: str, stream: str = "stdout", **kwargs) -> Dict[str, Any]:
        return self.emit(AgentEventType.COMMAND_OUTPUT, line=line, stream=stream, **kwargs)

    def command_completed(self, command: str, exit_code: int = 0, duration_ms: float = 0.0, **kwargs) -> Dict[str, Any]:
        return self.emit(AgentEventType.COMMAND_COMPLETED, command=command, exit_code=exit_code, duration_ms=duration_ms, **kwargs)

    def build_result(self, passed: bool, errors: List[str] = None, warnings: List[str] = None, **kwargs) -> Dict[str, Any]:
        return self.emit(AgentEventType.BUILD_RESULT, passed=passed, errors=errors or [], warnings=warnings or [], **kwargs)

    def preview_ready(self, url: str, port: int = 5173, mode: str = "site", **kwargs) -> Dict[str, Any]:
        return self.emit(AgentEventType.PREVIEW_READY, url=url, port=port, mode=mode, **kwargs)

    def task_started(self, **kwargs) -> Dict[str, Any]:
        return self.emit(AgentEventType.TASK_STARTED, **kwargs)

    def task_completed(self, result: Dict[str, Any] = None, summary: str = "", **kwargs) -> Dict[str, Any]:
        return self.emit(AgentEventType.TASK_COMPLETED, result=result or {}, summary=summary, **kwargs)

    def task_failed(self, error: str, **kwargs) -> Dict[str, Any]:
        return self.emit(AgentEventType.TASK_FAILED, error=error, **kwargs)

    def task_cancelled(self, reason: str = "user_cancelled", **kwargs) -> Dict[str, Any]:
        return self.emit(AgentEventType.TASK_CANCELLED, reason=reason, **kwargs)


# Global EventBus singleton
event_bus = EventBus()
