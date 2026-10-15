"""Killable subprocess boundary for hard-deadline work."""
from __future__ import annotations

import multiprocessing as mp
import os
import signal
import time
from dataclasses import dataclass
from typing import Any, Callable, Optional


@dataclass
class ProcessRunResult:
    completed: bool
    timed_out: bool = False
    value: Any = None
    error: Optional[str] = None
    terminated: bool = False


def _invoke(fn: Callable[..., Any], args: tuple, kwargs: dict, out: Any) -> None:
    try:
        out.put(("ok", fn(*args, **kwargs)))
    except BaseException as exc:
        out.put(("error", f"{type(exc).__name__}: {exc}"))


def run_killable(fn: Callable[..., Any], *args: Any, timeout: float, grace: float = 2.0, **kwargs: Any) -> ProcessRunResult:
    """Run a picklable callable in a process; never waits indefinitely."""
    ctx = mp.get_context("spawn" if os.name == "nt" else "fork")
    out = ctx.Queue(1)
    proc = ctx.Process(target=_invoke, args=(fn, args, kwargs, out), daemon=True)
    proc.start()
    proc.join(timeout)
    if proc.is_alive():
        proc.terminate()
        proc.join(grace)
        if proc.is_alive() and hasattr(proc, "kill"):
            proc.kill()
            proc.join(grace)
        return ProcessRunResult(False, timed_out=True, terminated=True, error=f"hard deadline exceeded ({timeout:.1f}s)")
    try:
        status, payload = out.get_nowait()
    except Exception:
        return ProcessRunResult(False, error=f"worker exited with code {proc.exitcode}")
    return ProcessRunResult(status == "ok", value=payload if status == "ok" else None, error=None if status == "ok" else str(payload))
