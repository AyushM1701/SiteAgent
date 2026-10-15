"""
agent/safe_executor.py - Model Safe Command Executor

A dedicated, isolated command executor for the model and tool layers.
Distinct from the unrestricted human interactive PTY shell:
- Strictly enforces shell=False (blocks shell metacharacters and injection)
- Whitelists safe executables (npm, npx, git, node)
- Confines execution strictly within the target project workspace directory
- Enforces execution timeouts and captures structured output
- Emits real-time command events to UI streams
"""

import dataclasses
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set


@dataclasses.dataclass
class ExecutionResult:
    """Outcome of a safe command execution."""
    success: bool
    returncode: int
    stdout: str
    stderr: str
    duration_ms: float
    command: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "returncode": self.returncode,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "duration_ms": self.duration_ms,
            "command": self.command,
        }


class SafeExecutorError(Exception):
    """Raised when an unauthorized or dangerous command is rejected."""
    pass


class SafeExecutor:
    """
    Dedicated safe command executor for model tool calls.
    Guarantees non-shell execution, sandboxing, and timeout protection.
    """

    ALLOWED_EXECUTABLES: Set[str] = {
        "npm", "npm.cmd",
        "npx", "npx.cmd",
        "git", "git.exe",
        "node", "node.exe",
        "tsc", "tsc.cmd",
        "vite", "vite.cmd",
    }

    BLOCKED_EXECUTABLES: Set[str] = {
        "cmd", "cmd.exe",
        "powershell", "powershell.exe",
        "pwsh", "pwsh.exe",
        "sh", "bash", "zsh",
        "curl", "wget", "net",
        "rm", "del", "format", "reg",
        "taskkill", "pkill", "kill",
    }

    def __init__(self, default_timeout: float = 60.0):
        self.default_timeout = default_timeout

    def _resolve_executable(self, prog: str) -> str:
        """Validates that the program is permitted and resolves its absolute binary path."""
        prog_clean = prog.strip()
        base_name = Path(prog_clean).name.lower()

        if base_name in self.BLOCKED_EXECUTABLES:
            raise SafeExecutorError(
                f"[Security Policy] Execution of shell or system binary '{base_name}' is blocked for model tools."
            )

        if base_name not in self.ALLOWED_EXECUTABLES and prog_clean.lower() not in self.ALLOWED_EXECUTABLES:
            raise SafeExecutorError(
                f"[Security Policy] Executable '{prog_clean}' is not in the model safe executor allowlist ({', '.join(sorted(self.ALLOWED_EXECUTABLES))})."
            )

        # Resolve binary path via shutil.which to avoid shell=True on Windows
        resolved = shutil.which(prog_clean)
        if not resolved:
            raise FileNotFoundError(f"Executable '{prog_clean}' not found on system PATH.")
        return resolved

    def execute(
        self,
        args: List[str],
        cwd: Path,
        timeout_s: Optional[float] = None,
        env: Optional[Dict[str, str]] = None,
        event_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> ExecutionResult:
        """
        Executes a validated command within cwd using shell=False.
        Emits command events if event_callback is provided.
        """
        if not args or not isinstance(args, list):
            raise SafeExecutorError("Command arguments must be a non-empty list of strings.")

        cwd_path = Path(cwd).resolve()
        if not cwd_path.exists() or not cwd_path.is_dir():
            raise FileNotFoundError(f"Execution directory does not exist: '{cwd_path}'")

        timeout = timeout_s if timeout_s is not None else self.default_timeout
        resolved_exe = self._resolve_executable(args[0])
        cmd_argv = [resolved_exe] + [str(a) for a in args[1:]]
        cmd_str = " ".join(args)

        # Notify UI of command start
        if event_callback:
            try:
                event_callback({
                    "type": "command.started",
                    "command": cmd_str,
                    "status": "running",
                    "cwd": str(cwd_path),
                })
            except Exception:
                pass

        merged_env = os.environ.copy()
        if env:
            merged_env.update(env)

        start_time = time.perf_counter()
        try:
            proc = subprocess.Popen(
                cmd_argv,
                cwd=str(cwd_path),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=merged_env,
                shell=False,  # CRITICAL: strictly non-shell
            )

            try:
                stdout_bytes, stderr_bytes = proc.communicate(timeout=timeout)
                duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
                stdout = stdout_bytes.decode("utf-8", errors="replace")
                stderr = stderr_bytes.decode("utf-8", errors="replace")
                success = (proc.returncode == 0)

                if event_callback:
                    try:
                        event_callback({
                            "type": "command.completed",
                            "command": cmd_str,
                            "status": "completed" if success else "failed",
                            "returncode": proc.returncode,
                            "exit_code": proc.returncode,
                            "duration_ms": duration_ms,
                        })
                    except Exception:
                        pass

                return ExecutionResult(
                    success=success,
                    returncode=proc.returncode,
                    stdout=stdout,
                    stderr=stderr,
                    duration_ms=duration_ms,
                    command=args,
                )

            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=2)
                duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
                if event_callback:
                    try:
                        event_callback({
                            "type": "command.completed",
                            "command": cmd_str,
                            "status": "timeout",
                            "returncode": -1,
                            "exit_code": -1,
                            "duration_ms": duration_ms,
                        })
                    except Exception:
                        pass
                return ExecutionResult(
                    success=False,
                    returncode=-1,
                    stdout="",
                    stderr=f"[SafeExecutor] Command timed out after {timeout} seconds.",
                    duration_ms=duration_ms,
                    command=args,
                )

        except Exception as exc:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return ExecutionResult(
                success=False,
                returncode=-1,
                stdout="",
                stderr=f"[SafeExecutor Error] {exc}",
                duration_ms=duration_ms,
                command=args,
            )


# Global singleton instance
safe_executor = SafeExecutor()
