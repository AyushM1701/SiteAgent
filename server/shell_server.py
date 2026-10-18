"""
shell_server.py — Dedicated WebSocket PowerShell Server (Port 5001)
Runs as an isolated OS process with its own Python interpreter and GIL.
Completely eliminates GIL contention with PyTorch/Unsloth model inference.
Features a dedicated persistent writer thread with queue batching for zero-latency keystrokes.
"""

import asyncio
import hashlib
import hmac
import json
import os
import queue
import re
import socket
import sys
import threading
import time
import urllib.parse
from pathlib import Path

BASE_DIR = Path(__file__).parent.resolve()
REPO_ROOT = BASE_DIR.parent
PROJECTS_ROOT = (REPO_ROOT / "generated_components").resolve()


def _shell_cwd(requested: str) -> Path:
    """Open the shell in the requested project folder, if it is a generated project."""
    if requested:
        try:
            candidate = Path(requested).resolve()
            if candidate.is_dir() and PROJECTS_ROOT in candidate.parents:
                return candidate
        except (OSError, ValueError):
            pass
    return REPO_ROOT
DEBUG = os.environ.get("SHELL_DEBUG", "").lower() in ("1", "true", "yes")
HOST = os.environ.get("SHELL_HOST", "127.0.0.1")
AUTH_TOKEN = os.environ.get("SHELL_AUTH_TOKEN", "").strip()

# Cross-platform PTY support: WinPTY on Windows, ptyprocess on POSIX
_HAS_WINPTY = False
_HAS_POSIX_PTY = False

if os.name == "nt":
    try:
        from winpty import PtyProcess
        from winpty.enums import Backend
        _HAS_WINPTY = True
    except ImportError:
        print("[Shell Server] Error: pywinpty is not installed; Windows shell unavailable.")
        sys.exit(1)
else:
    try:
        from ptyprocess import PtyProcessUnicode as PtyProcess
        _HAS_POSIX_PTY = True
    except ImportError:
        print("[Shell Server] Error: ptyprocess is not installed; POSIX shell unavailable.")
        sys.exit(1)

import websockets

ALLOWED_ORIGIN_PATTERNS = [
    re.compile(r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"),
    re.compile(rf"^https?://{re.escape(HOST)}(:\d+)?$"),
    None,  # Allow non-browser direct clients (curl, node tools, local scripts)
]

# Track seen nonces for short-lived HMAC tickets to prevent replay attacks
_SEEN_NONCES: dict[str, float] = {}

def _clean_stale_nonces():
    now = time.time()
    stale = [n for n, exp in _SEEN_NONCES.items() if exp < now]
    for n in stale:
        _SEEN_NONCES.pop(n, None)

def _verify_shell_token(token: str) -> bool:
    """Verifies either raw AUTH_TOKEN or single-use HMAC ticket (timestamp.nonce.sig)."""
    if not AUTH_TOKEN:
        return False
    if not isinstance(token, str) or not token:
        return False
    if hmac.compare_digest(token.encode("utf-8"), AUTH_TOKEN.encode("utf-8")):
        return True

    # Check if single-use HMAC ticket: {timestamp}.{nonce}.{sig}
    parts = token.split(".")
    if len(parts) == 3:
        ts_str, nonce, sig = parts
        try:
            ts = int(ts_str)
            now = time.time()
            if abs(now - ts) > 30.0:
                if DEBUG:
                    print(f"[Shell WS] Ticket expired (age: {now - ts:.1f}s)")
                return False
            _clean_stale_nonces()
            if nonce in _SEEN_NONCES:
                if DEBUG:
                    print("[Shell WS] Nonce replay attack prevented")
                return False
            payload = f"{ts}:{nonce}"
            expected_sig = hmac.new(AUTH_TOKEN.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
            if hmac.compare_digest(sig, expected_sig):
                _SEEN_NONCES[nonce] = now + 60.0  # cache nonce for 60s
                return True
        except Exception as e:
            if DEBUG:
                print(f"[Shell WS] Error validating ticket: {e}")
            return False
    return False


def process_request(connection, request):
    """Rejects cross-origin requests or invalid tokens before handshake completes."""
    # 1. Origin check against allowed patterns
    origin = request.headers.get("Origin")
    if origin:
        allowed = False
        for pat in ALLOWED_ORIGIN_PATTERNS:
            if pat and pat.match(origin):
                allowed = True
                break
        if not allowed:
            if DEBUG:
                print(f"[Shell Server] Rejected WebSocket from disallowed origin: {origin}")
            return connection.respond(403, "Forbidden: Cross-origin WebSocket blocked\n")

    # 2. Token check if query param supplied
    if not AUTH_TOKEN:
        return connection.respond(503, "Shell authentication is not configured\n")
    parsed = urllib.parse.urlparse(request.path)
    qs = urllib.parse.parse_qs(parsed.query)
    token = qs.get("token", [""])[0]
    if token:
        if not _verify_shell_token(token):
            return connection.respond(401, "Unauthorized: Invalid shell token\n")
        connection._shell_authenticated = True
    connection._shell_cwd = _shell_cwd(qs.get("cwd", [""])[0])
    return None


async def shell_handler(ws):
    cols, rows = 120, 30
    if DEBUG:
        print("[Shell WS] New client connected to port 5001")

    # If not already authenticated via query param, require initial auth message within 5s
    if not AUTH_TOKEN:
        await ws.close(code=4401, reason="Shell authentication is not configured")
        return
    if not getattr(ws, "_shell_authenticated", False):
        try:
            raw_msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
            if isinstance(raw_msg, bytes):
                raw_msg = raw_msg.decode("utf-8", errors="ignore")
            auth_data = json.loads(raw_msg) if raw_msg.startswith("{") else {}
            token = auth_data.get("token", "")
            if not _verify_shell_token(token):
                await ws.send("\r\n[Server] Unauthorized: Invalid session token.\r\n")
                await ws.close(code=4401, reason="Unauthorized")
                return
        except Exception:
            try:
                await ws.send("\r\n[Server] Unauthorized: Authentication timed out or failed.\r\n")
                await ws.close(code=4401, reason="Unauthorized")
            except Exception as _close_err:
                if DEBUG:
                    print(f"[Shell WS] Error closing unauthorized ws: {_close_err}")
            return

    try:
        if os.name == "nt":
            pty = PtyProcess.spawn(
                [
                    "powershell.exe",
                    "-NoLogo",
                    "-NoExit",
                    "-Command",
                    "Remove-Module PSReadLine -ErrorAction SilentlyContinue",
                ],
                dimensions=(rows, cols),
                cwd=str(getattr(ws, "_shell_cwd", REPO_ROOT)),
                backend=Backend.WinPTY,
            )
            try:
                pty.fileobj.settimeout(0.3)
            except Exception as e:
                if DEBUG:
                    print(f"[Shell WS] Note: socket settimeout not applicable to pty handle: {e}")
        else:
            shell_bin = os.environ.get("SHELL", "/bin/bash")
            pty = PtyProcess.spawn(
                [shell_bin, "-i"],
                dimensions=(rows, cols),
                cwd=str(getattr(ws, "_shell_cwd", REPO_ROOT)),
            )
    except Exception as exc:
        if DEBUG:
            print(f"[Shell WS] Failed to spawn PTY: {exc}")
        try:
            await ws.send(f"\r\n[Server] Failed to spawn shell: {exc}\r\n")
            await ws.close()
        except Exception as _close_err:
            if DEBUG:
                print(f"[Shell WS] Error closing ws: {_close_err}")
        return

    loop = asyncio.get_running_loop()
    stop_event = threading.Event()
    current_cols, current_rows = cols, rows

    # ── Reader Thread ──────────────────────────────────────────────────────────
    def pty_reader():
        if DEBUG:
            print("[Shell WS] pty_reader thread started")
        try:
            while not stop_event.is_set():
                try:
                    data = pty.read(4096)
                except (TimeoutError, socket.timeout):
                    continue
                except EOFError:
                    if DEBUG:
                        print("[Shell WS] pty_reader EOF reached")
                    break
                except Exception as e:
                    if "timed out" in str(e).lower():
                        continue
                    if DEBUG:
                        print(f"[Shell WS] pty_reader error: {e}")
                    break
                if data:
                    if DEBUG:
                        print(f"[Shell WS] pty_reader read {len(data)} chars: {repr(data[:60])}")
                    asyncio.run_coroutine_threadsafe(ws.send(data), loop)
        except Exception as e:
            if DEBUG:
                print(f"[Shell WS] pty_reader loop error: {e}")
        finally:
            stop_event.set()
            if DEBUG:
                print("[Shell WS] pty_reader thread exited")

    # ── Dedicated Persistent Writer Thread (Non-blocking queue batching) ───────
    write_queue = queue.Queue()

    def pty_writer():
        if DEBUG:
            print("[Shell WS] pty_writer thread started")
        while not stop_event.is_set():
            try:
                item = write_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            if item is None:
                break

            # Coalesce any queued keystrokes into a single batch for instantaneous throughput
            chunks = [item]
            while not write_queue.empty():
                try:
                    chunks.append(write_queue.get_nowait())
                except queue.Empty:
                    break

            combined = "".join(chunks)
            if DEBUG:
                print(f"[Shell WS] pty_writer dequeued {len(chunks)} chunks, combined len {len(combined)}: {repr(combined)}")
            try:
                if pty.isalive():
                    pty.write(combined)
                    if DEBUG:
                        print("[Shell WS] pty_writer write completed successfully")
                else:
                    if DEBUG:
                        print("[Shell WS] pty_writer: pty is not alive!")
            except Exception as e:
                if DEBUG:
                    print(f"[Shell WS] pty_writer write error: {e}")
                break

        if DEBUG:
            print("[Shell WS] pty_writer thread exited")

    reader_thread = threading.Thread(target=pty_reader, daemon=True)
    reader_thread.start()

    writer_thread = threading.Thread(target=pty_writer, daemon=True)
    writer_thread.start()

    try:
        async for msg in ws:
            if isinstance(msg, bytes):
                msg = msg.decode("utf-8", errors="ignore")

            # Check for JSON control messages (e.g. resize)
            if isinstance(msg, str) and msg.startswith("{"):
                try:
                    ctrl = json.loads(msg)
                    if isinstance(ctrl, dict) and ctrl.get("type") == "resize":
                        c = int(ctrl.get("cols", current_cols))
                        r = int(ctrl.get("rows", current_rows))
                        if (c != current_cols or r != current_rows) and c >= 20 and r >= 5:
                            current_cols, current_rows = c, r
                            if pty.isalive():
                                await loop.run_in_executor(None, pty.setwinsize, r, c)
                        continue
                except Exception as e:
                    if DEBUG:
                        print(f"[Shell WS] resize parsing error: {e}")

            # Non-blocking write: immediately hand off keystroke to writer thread
            if pty.isalive():
                write_queue.put(msg)

    except Exception as e:
        if DEBUG:
            print(f"[Shell WS] Connection exception: {e}")
    finally:
        stop_event.set()
        write_queue.put(None)  # Wake up writer thread to exit
        try:
            pty.terminate(force=True)
        except Exception as _term_err:
            if DEBUG:
                print(f"[Shell WS] Note: PTY termination error: {_term_err}")
        if DEBUG:
            print("[Shell WS] Connection closed, PTY terminated.")


async def main():
    if not AUTH_TOKEN:
        raise RuntimeError("SHELL_AUTH_TOKEN must be set; refusing to start an unauthenticated shell")
    print(f"[Shell Server] Dedicated PowerShell WebSocket server running on ws://{HOST}:5001")
    server = await websockets.serve(
        shell_handler,
        HOST,
        5001,
        process_request=process_request,
        ping_interval=20,
        ping_timeout=15,
    )
    await server.wait_closed()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
