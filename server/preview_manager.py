"""
server/preview_manager.py - Isolated production preview process lifecycle

Compiles per-project Vite assets and serves them from a dedicated loopback process:
- Dynamic port allocation starting from 5173 (5173, 5174, 5175...)
- Opaque-origin CORS for sandboxed module loading, without dev filesystem endpoints
- Process lifecycle management (start, stop, restart, getUrl, allocatePort, healthCheck, shutdownAll)
- Windows process tree termination via taskkill /F /T
- Automatic cleanup on server exit (atexit)
"""

import atexit
import argparse
import functools
import hashlib
import os
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.request
import urllib.error
from collections import deque
from pathlib import Path
from typing import Any, Dict, Optional, Union
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

BASE_DIR = Path(__file__).resolve().parent.parent


class IsolatedPreviewHandler(SimpleHTTPRequestHandler):
    """Serve only compiled public assets to the opaque sandbox origin."""

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', 'null')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        super().end_headers()

    def list_directory(self, path):
        self.send_error(404, 'Asset not found')
        return None

    def translate_path(self, path):
        translated = Path(super().translate_path(path)).resolve()
        root = Path(self.directory).resolve()
        if not translated.is_relative_to(root):
            return str(root / '.missing-asset')
        return str(translated)

    def log_message(self, format, *args):
        pass


def _source_signature(workspace: Path) -> str:
    digest = hashlib.sha256()
    roots = [workspace / 'src', workspace / 'public']
    files = [p for root in roots if root.exists() for p in root.rglob('*') if p.is_file()]
    files += [p for p in workspace.iterdir() if p.is_file() and p.name != 'static-preview.html']
    for path in sorted(files):
        digest.update(str(path.relative_to(workspace)).encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _stop_process_tree(proc: subprocess.Popen):
    """Cleanly stops dev server processes and their entire child process tree."""
    if proc is None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    else:
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except Exception:
            pass
    try:
        proc.wait(timeout=3)
    except Exception:
        if os.name != "nt":
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except Exception:
                pass
        else:
            try:
                proc.kill()
            except Exception:
                pass
        try:
            proc.wait(timeout=2)
        except Exception:
            pass


def _link_node_modules(target_nm: Path, source_nm: Path):
    """Creates a directory junction (Windows) or symlink (POSIX) to node_modules."""
    if not source_nm.exists() or target_nm.exists():
        return
    try:
        if os.name == "nt":
            res = subprocess.run(
                ["cmd.exe", "/c", "mklink", "/J", str(target_nm), str(source_nm)],
                capture_output=True,
                text=True,
            )
            if res.returncode != 0:
                try:
                    os.symlink(str(source_nm), str(target_nm), target_is_directory=True)
                except Exception as sym_err:
                    print(f"[PreviewManager] Warning linking node_modules on Windows: {res.stderr.strip() or sym_err}")
        else:
            try:
                os.symlink(str(source_nm), str(target_nm), target_is_directory=True)
            except Exception as sym_err:
                print(f"[PreviewManager] Warning symlinking node_modules: {sym_err}")
    except Exception as e:
        print(f"[PreviewManager] Error linking node_modules: {e}")


class PreviewManager:
    """
    Manages isolated per-project production previews with dynamic port allocation.
    Blueprint API:
      start(projectId)
      stop(projectId)
      restart(projectId)
      getUrl(projectId)
      allocatePort()
      healthCheck(projectId=None)
      shutdownAll()
    """

    def __init__(self, base_port: int = 5173, max_port: int = 5273):
        self.base_port = base_port
        self.max_port = max_port
        self._lock = threading.RLock()
        self._processes: Dict[str, subprocess.Popen] = {}
        self._project_ports: Dict[str, int] = {}
        self._project_dirs: Dict[str, Path] = {}
        self._stderr: Dict[str, deque] = {}
        self._source_signatures: Dict[str, str] = {}

    def _start_stderr_reader(self, project_id: str, proc: subprocess.Popen) -> None:
        ring = deque(maxlen=200)
        self._stderr[project_id] = ring
        def drain() -> None:
            if proc.stderr is None:
                return
            try:
                for line in iter(proc.stderr.readline, b""):
                    if not line:
                        break
                    ring.append(line.decode("utf-8", errors="replace").rstrip())
            except Exception as exc:
                ring.append(f"stderr reader: {exc}")
        threading.Thread(target=drain, name=f"vite-stderr-{project_id}", daemon=True).start()

    def get_stderr(self, projectId: str) -> list[str]:
        with self._lock:
            return list(self._stderr.get(projectId, ()))

    @staticmethod
    def _is_port_available(port: int, host: str = "127.0.0.1") -> bool:
        """Verifies if port is unallocated and can be bound on the local interface."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.3)
            try:
                s.bind((host, port))
                return True
            except (OSError, socket.error):
                return False

    def allocatePort(self) -> int:
        """
        Allocates the next available port starting from 5173 upwards (5173, 5174, 5175...).
        Checks both internal tracked allocations and active OS socket binding.
        """
        with self._lock:
            active_ports = set(self._project_ports.values())
            for port in range(self.base_port, self.max_port + 1):
                if port in active_ports:
                    continue
                if self._is_port_available(port):
                    return port
            raise RuntimeError(f"No available preview ports in range {self.base_port}-{self.max_port}")

    def getUrl(self, projectId: str) -> Optional[str]:
        """Returns the live preview URL (e.g. http://127.0.0.1:5173) if running and healthy, else None."""
        with self._lock:
            port = self._project_ports.get(projectId)
            if not port:
                return None
            proc = self._processes.get(projectId)
            if not proc or proc.poll() is not None:
                return None
            return f"http://127.0.0.1:{port}"

    def getPort(self, projectId: str) -> Optional[int]:
        """Returns the port allocated to a project, if any."""
        with self._lock:
            return self._project_ports.get(projectId)

    def healthCheck(self, projectId: Optional[str] = None) -> Union[bool, Dict[str, bool]]:
        """
        Checks process liveness and sends an HTTP probe to verify the Vite dev server is serving.
        If projectId is provided: returns bool.
        If projectId is None: returns Dict[projectId, bool] for all active projects.
        """
        with self._lock:
            if projectId is not None:
                return self._check_project_health(projectId)
            return {pid: self._check_project_health(pid) for pid in list(self._processes.keys())}

    def _check_project_health(self, projectId: str) -> bool:
        """Internal helper to probe HTTP endpoint of a project dev server."""
        proc = self._processes.get(projectId)
        port = self._project_ports.get(projectId)
        if not proc or not port:
            return False
        if proc.poll() is not None:
            return False

        url = f"http://127.0.0.1:{port}/"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ReactAgent-SLM-PreviewCheck"})
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                return resp.status < 400
        except Exception:
            return False

    def start(
        self,
        projectId: str,
        workspace_dir: Optional[Path] = None,
        startup_timeout: float = 8.0,
        _attempt: int = 0,
    ) -> Optional[str]:
        """
        Builds compiled public assets and starts an isolated static preview server.
        Reuses unchanged builds and rebuilds when source files have changed.
        """
        with self._lock:
            if workspace_dir is None:
                workspace_dir = self._project_dirs.get(projectId)
            # 1. If already running and healthy, return URL immediately
            if projectId in self._processes:
                signature = _source_signature(Path(workspace_dir)) if workspace_dir else None
                if self.healthCheck(projectId) and signature == self._source_signatures.get(projectId):
                    return self.getUrl(projectId)
                # Stale process: stop it first
                self.stop(projectId)

            # 2. Resolve workspace directory
            if workspace_dir is None:
                try:
                    from server.sessions import session_manager
                    s = session_manager.get_session(projectId)
                    if s and s.workspace_dir:
                        workspace_dir = s.workspace_dir
                except Exception:
                    pass

            if workspace_dir is None or not Path(workspace_dir).exists():
                # Check generated_components fallback
                cand = BASE_DIR / "generated_components" / projectId
                if cand.exists():
                    workspace_dir = cand
                else:
                    raise FileNotFoundError(f"Project workspace not found for projectId: {projectId}")

            workspace_dir = Path(workspace_dir).resolve()

            # 3. Ensure node_modules junction exists in workspace
            _link_node_modules(workspace_dir / "node_modules", BASE_DIR / "node_modules")

            # Compile public assets before exposing them to an opaque-origin iframe.
            # A dev server would expose source and filesystem endpoints to that origin.
            output_dir = workspace_dir / '.workbench-preview'
            signature = _source_signature(workspace_dir)
            build = subprocess.run(
                ['npx', 'vite', 'build', '--outDir', str(output_dir), '--emptyOutDir'],
                cwd=str(workspace_dir), capture_output=True, text=True,
                encoding='utf-8', errors='replace', timeout=120,
                shell=(os.name == 'nt'),
            )
            if build.returncode != 0:
                raise RuntimeError(f"Preview production build failed: {(build.stderr or build.stdout).strip()[-6000:]}")

            # 4. Allocate port (reuse project's port if available, otherwise allocate fresh)
            port = self._project_ports.get(projectId)
            if not port or not self._is_port_available(port):
                port = self.allocatePort()

            # 5. Launch Vite dev server with explicit port, strictPort, and host.
            # The race between availability probing and bind is handled by retry.
            env = os.environ.copy()
            env["PORT"] = str(port)

            cmd = [sys.executable, str(Path(__file__).resolve()), '--serve', str(output_dir), '--port', str(port)]

            proc = subprocess.Popen(cmd, cwd=str(workspace_dir), stdout=subprocess.DEVNULL,
                                    stderr=subprocess.PIPE, env=env, shell=False,
                                    start_new_session=(os.name != 'nt'))

            self._processes[projectId] = proc
            self._project_ports[projectId] = port
            self._project_dirs[projectId] = workspace_dir
            self._source_signatures[projectId] = signature
            self._start_stderr_reader(projectId, proc)

            # 6. Wait for Vite server readiness
            poll_interval = 0.2
            elapsed = 0.0
            ready = False

            while elapsed < startup_timeout:
                time.sleep(poll_interval)
                elapsed += poll_interval

                if proc.poll() is not None:
                    # Process died prematurely
                    stderr_msg = ""
                    try:
                        stderr_msg = "\n".join(self.get_stderr(projectId))
                    except Exception:
                        pass
                    self.stop(projectId)
                    if ("EADDRINUSE" in stderr_msg or "address already in use" in stderr_msg.lower()) and _attempt < 3:
                        self.stop(projectId)
                        # Retry with a fresh allocation; external processes are
                        # outside our lock and may win the TOCTOU race.
                        return self.start(projectId, workspace_dir=workspace_dir, startup_timeout=startup_timeout, _attempt=_attempt + 1)
                    raise RuntimeError(
                        f"Vite dev server for project '{projectId}' terminated with code {proc.returncode}: {stderr_msg.strip()}"
                    )

                if self._check_project_health(projectId):
                    ready = True
                    break

            if not ready:
                self.stop(projectId)
                raise TimeoutError(
                    f"Vite dev server for project '{projectId}' did not respond on port {port} within {startup_timeout}s. stderr={self.get_stderr(projectId)[-5:]}"
                )

            return self.getUrl(projectId)

    def stop(self, projectId: str) -> bool:
        """Stops the Vite dev process for projectId, terminates process tree, and releases port."""
        with self._lock:
            proc = self._processes.pop(projectId, None)
            port = self._project_ports.pop(projectId, None)
            self._project_dirs.pop(projectId, None)
            self._stderr.pop(projectId, None)
            self._source_signatures.pop(projectId, None)

            if proc:
                _stop_process_tree(proc)
                return True
            return False

    def restart(
        self,
        projectId: str,
        workspace_dir: Optional[Path] = None,
        startup_timeout: float = 8.0,
    ) -> Optional[str]:
        """Restarts the Vite dev server for projectId."""
        with self._lock:
            wdir = workspace_dir or self._project_dirs.get(projectId)
            self.stop(projectId)
            time.sleep(0.3)
            return self.start(projectId, workspace_dir=wdir, startup_timeout=startup_timeout)

    def shutdownAll(self):
        """Terminates all managed preview processes cleanly across all projects."""
        with self._lock:
            for pid, proc in list(self._processes.items()):
                try:
                    _stop_process_tree(proc)
                except Exception as e:
                    print(f"[PreviewManager] Note: error shutting down {pid}: {e}")
            self._processes.clear()
            self._project_ports.clear()
            self._project_dirs.clear()
            self._source_signatures.clear()

    # Pythonic snake_case aliases matching blueprint requirements
    get_url = getUrl
    get_port = getPort
    allocate_port = allocatePort
    health_check = healthCheck
    shutdown_all = shutdownAll


# Global singleton instance
preview_manager = PreviewManager()

# Ensure all preview child processes are cleanly terminated when the server process exits
atexit.register(preview_manager.shutdownAll)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Isolated compiled site preview')
    parser.add_argument('--serve', type=Path, required=True)
    parser.add_argument('--port', type=int, required=True)
    arguments = parser.parse_args()
    handler = functools.partial(IsolatedPreviewHandler, directory=str(arguments.serve.resolve()))
    ThreadingHTTPServer(('127.0.0.1', arguments.port), handler).serve_forever()
