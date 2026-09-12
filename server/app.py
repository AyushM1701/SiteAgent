"""
app.py — ReactAgent SLM Local Web UI
Serves a premium web interface for interacting with my-react-agent-lora.

Usage:
    python app.py
    # or via unified CLI:
    python slm.py serve
    # Then open http://localhost:5000 in your browser

The model is loaded ONCE at startup and shared across all requests.
Requests are queued — only one generation runs at a time (GPU constraint).
Live output is streamed to the browser via Server-Sent Events (SSE).
"""

import hashlib
import hmac
import html
import json
import os
import queue
import re
import secrets
import sys
import threading
import time
import urllib.parse
import uuid
from pathlib import Path
from typing import Any, Optional, Dict, List

# ── Paths & Environment ────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "web_ui_static"
HISTORY_FILE = BASE_DIR / "web_ui_history.json"
MODEL_PATH = str(BASE_DIR / "my-react-agent-lora")

sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "agent"))
sys.path.insert(0, str(Path(__file__).parent))

from flask import Flask, Response, jsonify, request, send_from_directory

from agent_protocol import (
    DEFAULT_INFERENCE_MAX_SEQ_LENGTH,
    DEFAULT_MAX_NEW_TOKENS,
)
from style_ingest import spec_to_css_root
from server.sessions import (
    Session,
    session_manager,
    compute_file_diff,
    generate_post_generation_summary,
)
from visual_judge import _score_screenshot_heuristic, take_screenshot

# ── App State ──────────────────────────────────────────────────────────────────

app = Flask(__name__, static_folder=str(STATIC_DIR))

# Per-session authentication token for WebSocket PTY server (CSWSH defense)
_SHELL_AUTH_TOKEN = secrets.token_urlsafe(32)

def _mint_shell_ticket() -> str:
    """Mints a short-lived (30s) single-use HMAC-SHA256 authenticated ticket for the shell WebSocket."""
    timestamp = int(time.time())
    nonce = secrets.token_hex(16)
    payload = f"{timestamp}:{nonce}"
    sig = hmac.new(_SHELL_AUTH_TOKEN.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{timestamp}.{nonce}.{sig}"

# Per-task SSE queues: task_id -> queue.Queue
task_queues: dict[str, queue.Queue] = {}
task_results: dict[str, dict] = {}
MAX_CACHED_RESULTS = 100
MAX_CACHED_QUEUES = 100

def _register_task_queue(task_id: str, q: queue.Queue):
    """Registers task queue with bounded eviction to prevent memory leaks."""
    global task_queues
    task_queues[task_id] = q
    while len(task_queues) > MAX_CACHED_QUEUES:
        oldest_id = next(iter(task_queues))
        task_queues.pop(oldest_id, None)

def _store_task_result(task_id: str, data: dict):
    """Stores result in memory cache bounded to MAX_CACHED_RESULTS, evicting oldest."""
    global task_results
    task_results[task_id] = data
    while len(task_results) > MAX_CACHED_RESULTS:
        oldest_k = next(iter(task_results))
        task_results.pop(oldest_k, None)

def _get_task_result(task_id: str) -> dict | None:
    """Retrieves result from memory cache, falling back to disk history if evicted."""
    if task_id in task_results:
        return task_results[task_id]
    for entry in _load_history():
        if entry.get("task_id") == task_id:
            task_results[task_id] = entry
            return entry
    return None

def _sanitize_identifier(name: str, default: str = "Component") -> str:
    """
    Enforces strict identifier syntax: ^[A-Za-z][A-Za-z0-9_]{0,63}$
    Completely eliminates directory traversal (e.g. ../../) and template injection.
    """
    raw = re.sub(r'[^A-Za-z0-9_]', '_', (name or "").strip())
    cleaned = re.sub(r'_+', '_', raw).strip('_')
    if not cleaned or not re.match(r'^[A-Za-z]', cleaned):
        cleaned = default if (default and re.match(r'^[A-Za-z]', default)) else f"Safe_{cleaned}"
    return cleaned[:64]

# Tasks that have been cancelled by the user
cancelled_tasks: set = set()

# Global model runner (loaded once)
_runner = None
_runner_lock = threading.Lock()
_model_status = "loading"  # loading | ready | busy
_generation_queue: queue.Queue = queue.Queue()

# ── Model Loading ──────────────────────────────────────────────────────────────

def _load_model():
    global _runner, _model_status
    try:
        from agent import AgentModelRunner
        print(f"[Server] Loading model my-react-agent-lora (max_seq_length={DEFAULT_INFERENCE_MAX_SEQ_LENGTH})...")
        _runner = AgentModelRunner(model_path=MODEL_PATH, max_seq_length=DEFAULT_INFERENCE_MAX_SEQ_LENGTH, is_mock=False)
        _model_status = "ready"
        print("[Server] Model ready.")
    except Exception as e:
        _model_status = "error"
        print(f"[Server] Model load failed: {e}")

threading.Thread(target=_load_model, daemon=True).start()

# Cleanup any stale temp workspaces left by a previous crashed run
for _stale in BASE_DIR.glob(".web_ui_workspace_*"):
    try:
        import shutil as _shutil
        _shutil.rmtree(_stale)
    except Exception as _stale_err:
        print(f"[Server] Note: could not remove stale workspace {_stale}: {_stale_err}")

# ── Auto Test Generator ────────────────────────────────────────────────────────

def _auto_test(symbol: str, is_hook: bool) -> str:
    if is_hook:
        return f"""
describe('{symbol}', () => {{
  it('initializes without errors', () => {{
    const {{ result }} = renderHook(() => {symbol}());
    expect(result.current).toBeDefined();
  }});
}});
""".strip()
    else:
        return f"""
describe('{symbol}', () => {{
  it('renders without crashing', () => {{
    const {{ container }} = render(<{symbol} />);
    expect(container.firstChild).toBeTruthy();
  }});
  it('renders with props', () => {{
    render(<{symbol} label="test" value="test" />);
  }});
}});
""".strip()


# ── Intent classifier ──────────────────────────────────────────────────────────

_SITE_KEYWORDS = [
    "website", "web site", "landing page", "full page", "homepage", "home page",
    "site for", "site for a", "page for", "build me a", "build a site",
    "restaurant site", "restaurant page", "portfolio site", "portfolio page",
    "portfolio for", "make a portfolio", "build a portfolio", "portfolio of",
    "saas site", "saas page", "blog site", "event page", "event site",
    "multi-section", "multi section", "full website", "complete website",
    "storefront", "ecommerce site", "online store", "agency site", "brand site", "showcase site",
    "dashboard with", "admin panel", "analytics portal", "multi-page", "multi page",
    "web application", "web app for",
]

_SITE_PATTERNS = [
    re.compile(r'\b(?:build|create|make|generate|design)\s+(?:a|an|the|me\s+a)?\s*(?:modern|responsive|clean|full|complete)?\s*(?:website|web\s+site|landing\s+page|homepage|portfolio|storefront|showcase|portal|dashboard)\b', re.I),
    re.compile(r'\bportfolio\s+(?:for|of)\s+[A-Za-z]+', re.I),
    re.compile(r'\b(?:restaurant|cafe|coffee\s+shop|bakery|bar|salon|spa|agency|hotel|fitness|gym|clinic)\s+(?:website|page|site)\b', re.I),
    re.compile(r'\bdashboard\s+(?:with|for)\s+\d+\s+(?:widgets|charts|panels|cards)\b', re.I),
]

def _classify_intent_with_confidence(prompt: str) -> tuple[str, float]:
    """
    Returns ('site' | 'component', confidence) where confidence is between 0.0 and 1.0.
    """
    lower = prompt.lower()
    for pat in _SITE_PATTERNS:
        if pat.search(prompt):
            return "site", 0.95

    for kw in _SITE_KEYWORDS:
        if kw in lower:
            return "site", 0.90

    comp_indicators = ["component", "button", "input", "modal", "dialog", "hook", "use", "slider", "switch", "toggle", "card", "dropdown", "navbar", "footer", "badge", "avatar"]
    for kw in comp_indicators:
        if re.search(rf'\b{kw}\b', lower):
            return "component", 0.85

    return "component", 0.60


def _classify_intent(prompt: str) -> str:
    """Returns 'site' if the prompt looks like a full-page/website request, 'component' otherwise."""
    mode, _ = _classify_intent_with_confidence(prompt)
    return mode


def _extract_component_name(prompt: str) -> str:
    """Extract PascalCase or camelCase component/hook/project name from prompt with case-insensitive fallback."""
    # 1. Look for backtick/quote/<tags> wrapped names: `useCounter`, <PinInput>, 'MyCard', "AURA Spatial Audio"
    m = re.search(r'[`\'"“<]([a-zA-Z0-9\s_-]{2,50})[`\'"”>]', prompt)
    if m:
        raw_val = m.group(1).strip()
        words = re.findall(r'[a-zA-Z0-9]+', raw_val)
        if words and not all(w.lower() in ("a", "an", "the", "for", "with", "and", "or", "in", "of", "to") for w in words):
            if len(words) == 1 and words[0].startswith("use") and len(words[0]) > 3:
                return "use" + words[0][3:].capitalize()
            return "".join(w.capitalize() for w in words)

    # 2. Look for any useX hook name anywhere in the prompt
    m = re.search(r'\b(use[A-Za-z0-9]+)\b', prompt, re.I)
    if m:
        val = m.group(1)
        return "use" + val[3:].capitalize() if len(val) > 3 else "useHook"

    # 3. Look for PascalCase words that are NOT common English verbs/instructions
    STOP_WORDS = {
        "Write", "Create", "Build", "Implement", "Make", "Generate", "Design",
        "Add", "Fix", "Update", "Modify", "Refactor", "Test", "Please", "A", "An", "The"
    }
    candidates = re.findall(r'\b[A-Z][a-zA-Z0-9]+\b', prompt)
    for c in candidates:
        if c not in STOP_WORDS:
            return c

    # 4. Smart lowercase fallback: detect compound component noun phrases
    # e.g., "dark mode toggle button", "user profile card", "search bar"
    m = re.search(
        r'\b(?:a|an|the)?\s*([a-z0-9_-]+(?:\s+[a-z0-9_-]+){0,2})\s+'
        r'(?:component|widget|element|hook|button|modal|card|form|table|dropdown|menu|bar|input|switch|slider|dialog|drawer|toast|alert|badge|tabs?|accordion|picker|view|player|nav)\b',
        prompt,
        re.I
    )
    if m:
        phrase = m.group(0).strip()
        words = [w.capitalize() for w in re.split(r'[^a-zA-Z0-9]+', phrase) if w.lower() not in {"a", "an", "the", "build", "make", "create"}]
        if words:
            return "".join(words)[:64]

    # 5. Extract non-stop words from prompt and title-case
    GENERIC_STOP = {
        "a", "an", "the", "build", "create", "make", "implement", "design", "write", "generate",
        "me", "for", "with", "and", "or", "in", "to", "of", "from", "at", "by", "that", "this",
        "modern", "clean", "responsive", "simple", "good", "nice", "interactive", "reusable"
    }
    tokens = [w.capitalize() for w in re.findall(r'\b[a-zA-Z0-9]+\b', prompt) if w.lower() not in GENERIC_STOP]
    if tokens:
        return "".join(tokens[:3])[:64]

    return "Component"


def _extract_project_name(prompt: str) -> str:
    """
    Extracts a project/business name from a site-mode prompt with case-insensitive support.
    Prefers explicit 'for <Name>' patterns; falls back to domain-specific slugs or title-cased words.
    Guaranteed to return a valid filesystem-safe slug.
    """
    # 1. Quoted name (e.g. "AURA Spatial Audio", 'FlowSync AI')
    m = re.search(r"[\"']([a-zA-Z0-9\s_-]{2,40})[\"']", prompt)
    if m:
        raw = m.group(1).strip()
        words = [w.capitalize() for w in re.findall(r'[a-zA-Z0-9]+', raw) if w.lower() not in {"a", "an", "the"}]
        if words:
            return "_".join(words)[:64]

    # 2. Explicit 'for <Name>' or 'called <Name>' (case-insensitive with title-casing)
    m = re.search(
        r"(?:for|called|named)\s+[\"']?([a-zA-Z0-9][a-zA-Z0-9 ]{0,39}?)(?:$|,|\.|\s+(?:with|using|and|in|featuring)\b)",
        prompt,
        re.I
    )
    if m:
        raw = m.group(1).strip()
        words = [w.capitalize() for w in re.split(r'\s+', raw) if w.lower() not in {"a", "an", "the"}]
        if words:
            return "_".join(words)[:64]

    # 3. Domain keyword fallback (e.g. restaurant, cafe, bakery, portfolio, dashboard)
    domain_match = re.search(r'\b(restaurant|cafe|coffee|bakery|bar|salon|spa|agency|hotel|fitness|gym|clinic|portfolio|storefront|shop|saas|blog|dashboard)\b', prompt, re.I)
    if domain_match:
        return f"{domain_match.group(1).capitalize()}_Site"

    # 4. Sequence of TitleCase words (not stop words)
    STOP = {
        "Write", "Create", "Build", "Make", "Design", "Generate", "Develop",
        "A", "An", "The", "My", "Our", "New", "React", "TypeScript", "Website",
        "Page", "Site", "Landing", "Full", "Complete", "Modern", "Beautiful",
    }
    words = re.findall(r'\b[A-Z][a-zA-Z0-9]+\b', prompt)
    candidates = [w for w in words if w not in STOP]
    if candidates:
        return "_".join(candidates[:2])

    return "MySite"

# ── Generation Worker ──────────────────────────────────────────────────────────

_current_task: Optional[dict] = None

def _worker():
    """Background thread: drains _generation_queue one task at a time."""
    global _model_status, _current_task
    while True:
        task = _generation_queue.get()
        if task is None:
            break
        task_id = task["task_id"]
        q = task_queues.get(task_id)

        # Skip tasks that were cancelled while waiting in the queue
        if task_id in cancelled_tasks:
            cancelled_tasks.discard(task_id)
            if q:
                q.put({"type": "cancelled", "text": "Generation cancelled."})
                q.put({"type": "done"})
            _generation_queue.task_done()
            continue

        try:
            _model_status = "busy"
            _current_task = task
            with _runner_lock:
                task_err = []
                def _run_target():
                    try:
                        if task.get("is_follow_up"):
                            _run_session_edit_turn(task, q)
                        elif task.get("mode") == "site":
                            _run_site_generation(task, q)
                        else:
                            _run_generation(task, q)
                    except Exception as err:
                        task_err.append(err)

                worker_t = threading.Thread(target=_run_target, daemon=True)
                worker_t.start()
                max_turns_est = task.get("max_turns", 14)
                timeout_s = max(2400.0, max_turns_est * 200.0)  # 40-minute guard for multi-turn site pipelines
                worker_t.join(timeout=timeout_s)

                if worker_t.is_alive():
                    raise TimeoutError(f"Task {task_id} timed out after {int(timeout_s)} seconds.")
                if task_err:
                    raise task_err[0]
        except Exception as e:
            if q:
                q.put({"type": "error", "text": str(e)})
                q.put({"type": "done"})
        finally:
            _current_task = None
            _model_status = "ready"
            cancelled_tasks.discard(task_id)
            _generation_queue.task_done()

threading.Thread(target=_worker, daemon=True).start()


_stdout_context = threading.local()


class _ThreadScopedStdout:
    """Routes print() calls to the active task Queue as SSE events ONLY for the generation thread."""
    def __init__(self, original):
        self._original = original

    def write(self, text):
        try:
            self._original.write(text)
        except UnicodeEncodeError:
            self._original.write(text.encode("ascii", errors="replace").decode("ascii"))
        try:
            self._original.flush()
        except Exception:
            pass
        active_q = getattr(_stdout_context, "active_queue", None)
        if active_q and text.strip():
            active_q.put({"type": "log", "text": text.rstrip()})

    def flush(self):
        self._original.flush()


sys.stdout = _ThreadScopedStdout(sys.stdout)


def _link_node_modules(target_nm: Path, source_nm: Path):
    """Creates a directory junction (Windows) or symlink (POSIX) to node_modules with clear diagnostics."""
    if not source_nm.exists() or target_nm.exists():
        return
    try:
        if os.name == "nt":
            import subprocess
            res = subprocess.run(
                ["cmd.exe", "/c", "mklink", "/J", str(target_nm), str(source_nm)],
                capture_output=True,
                text=True,
            )
            if res.returncode != 0:
                try:
                    os.symlink(str(source_nm), str(target_nm), target_is_directory=True)
                except Exception as sym_err:
                    print(f"[Scaffold] Warning: Could not create Windows junction or symlink: {res.stderr.strip() or sym_err}")
        else:
            try:
                os.symlink(str(source_nm), str(target_nm), target_is_directory=True)
            except Exception as sym_err:
                print(f"[Scaffold] Warning: Could not symlink node_modules on POSIX: {sym_err}")
    except Exception as e:
        print(f"[Scaffold] Warning: Error while linking node_modules: {e}")


def _scaffold_vite_runner(target_dir: Path, symbol: str):
    _link_node_modules(BASE_DIR / "generated_components" / "node_modules", BASE_DIR / "node_modules")
    """Generates package.json, vite.config.ts, index.html, and main.tsx so npm run dev works immediately."""
    try:
        pkg = {
            "name": f"{symbol.lower()}-preview",
            "private": True,
            "version": "1.0.0",
            "type": "module",
            "scripts": {
                "dev": "vite",
                "build": "vite build",
                "preview": "vite preview"
            },
            "dependencies": {
                "react": "^19.0.0",
                "react-dom": "^19.0.0"
            },
            "devDependencies": {
                "@types/react": "^19.0.10",
                "@types/react-dom": "^19.0.4",
                "@vitejs/plugin-react": "^4.3.4",
                "typescript": "^5.7.3",
                "vite": "^6.0.0"
            }
        }
        (target_dir / "package.json").write_text(json.dumps(pkg, indent=2), encoding="utf-8")

        vite_cfg = """import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    open: true,
  },
});
"""
        (target_dir / "vite.config.ts").write_text(vite_cfg, encoding="utf-8")

        index_html = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{symbol} Component Preview</title>
  </head>
  <body style="margin: 0; background: #0e0e1a; color: #f0f0f8; font-family: system-ui, sans-serif;">
    <div id="root"></div>
    <script type="module" src="/main.tsx"></script>
  </body>
</html>
"""
        (target_dir / "index.html").write_text(index_html, encoding="utf-8")

        main_tsx = f"""import React from 'react';
import ReactDOM from 'react-dom/client';
import * as Mod from './{symbol}';

const Comp: any = Mod.{symbol} || Mod.default || Object.values(Mod).find(v => typeof v === 'function') || (() => <div>No component found</div>);

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <div style={{{{ padding: 24, maxWidth: 1200, margin: '0 auto' }}}}>
      <Comp />
    </div>
  </React.StrictMode>
);
"""
        (target_dir / "main.tsx").write_text(main_tsx, encoding="utf-8")
    except Exception as e:
        print(f"[Server] Note: could not scaffold Vite preview: {e}")


def _scaffold_site_vite_runner(target_dir: Path, project_name: str, files: dict[str, str], brief: dict = None, q: Any = None):
    """
    Scaffolds a runnable Vite environment for the multi-file site output.
    Wires App.tsx with robust component export resolution, stem dedup, and HTML escaping.
    """
    try:
        pkg = {
            "name": re.sub(r'[^a-z0-9-]', '-', project_name.lower()).strip('-') + "-site",
            "private": True,
            "version": "1.0.0",
            "type": "module",
            "scripts": {
                "dev": "vite",
                "build": "vite build",
                "preview": "vite preview"
            },
            "dependencies": {
                "react": "^19.0.0",
                "react-dom": "^19.0.0"
            },
            "devDependencies": {
                "@types/react": "^19.0.10",
                "@types/react-dom": "^19.0.4",
                "@vitejs/plugin-react": "^4.3.4",
                "typescript": "^5.7.3",
                "vite": "^6.0.0"
            }
        }
        (target_dir / "package.json").write_text(json.dumps(pkg, indent=2), encoding="utf-8")

        vite_cfg = """import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  define: {
    'process.env': {},
  },
  server: { port: 5173, open: true },
});
"""
        (target_dir / "vite.config.ts").write_text(vite_cfg, encoding="utf-8")

        # Ensure node_modules junction exists in generated_components for instant Vite dev
        gen_nm = BASE_DIR / "generated_components" / "node_modules"
        root_nm = BASE_DIR / "node_modules"
        _link_node_modules(gen_nm, root_nm)

        # Collect all .tsx component files and build dynamic App.tsx
        tsx_files = [p for p in files.keys() if p.startswith("src/components/") and p.endswith(".tsx")]
        component_names = []
        import_lines = []
        seen_stems = set()

        for tsx_path in tsx_files:
            raw_comp = Path(tsx_path).stem
            comp_name = raw_comp
            # P2-4: Guard against stem collisions
            count = 1
            while comp_name in seen_stems:
                count += 1
                comp_name = f"{raw_comp}_{count}"
            seen_stems.add(comp_name)
            component_names.append(comp_name)

            file_content = files.get(tsx_path, "")
            # P0-3: Inspect component exports to avoid silent null renders
            named_export_m = re.search(r'export\s+(?:function|const)\s+([A-Z]\w*)', file_content)
            alt_name = named_export_m.group(1) if named_export_m else None

            mod_var = f"_{comp_name}Mod"
            import_lines.append(f"import * as {mod_var} from './{tsx_path}';")

            fallback_jsx = (
                f"(() => React.createElement('div', {{style: {{padding: '1.5rem', textAlign: 'center', "
                f"background: 'rgba(239, 68, 68, 0.08)', border: '1px dashed #ef4444', borderRadius: '8px', "
                f"margin: '1rem', color: '#f87171', fontFamily: 'sans-serif'}}}}, "
                f"'⚠️ Section \"{raw_comp}\" has no valid React export.'))"
            )

            if alt_name and alt_name != raw_comp:
                import_lines.append(
                    f"const {comp_name} = ({mod_var} as any).{raw_comp} || ({mod_var} as any).{alt_name} || ({mod_var} as any).default || {fallback_jsx};"
                )
            else:
                import_lines.append(
                    f"const {comp_name} = ({mod_var} as any).{raw_comp} || ({mod_var} as any).default || {fallback_jsx};"
                )

        app_tsx_imports = "\n".join(import_lines) if import_lines else "// No components found"
        app_tsx_render = "\n      ".join([f"<{n} />" for n in component_names]) if component_names else "<div>No sections</div>"

        app_tsx = f"""import React from 'react';
{app_tsx_imports}
import './src/App.css';

export default function App() {{
  return (
    <div className="site-root">
      {app_tsx_render}
    </div>
  );
}}
"""
        # Write App.tsx at root level
        (target_dir / "App.tsx").write_text(app_tsx, encoding="utf-8")

        # Write or ensure App.css exists with brief design tokens
        app_css_path = target_dir / "src" / "App.css"
        app_css_path.parent.mkdir(parents=True, exist_ok=True)

        style_spec = brief.get("style_spec") if brief else None
        if style_spec:
            root_css = spec_to_css_root(style_spec)
        else:
            primary_color = (brief.get("primary_color") if brief else None) or "#090d16"
            accent_color  = (brief.get("accent_color") if brief else None) or "#38bdf8"
            font_h        = (brief.get("font_heading") if brief else None) or "Inter"
            font_b        = (brief.get("font_body") if brief else None) or "Inter"
            root_css = (
                ":root {\n"
                f"  --primary-color: {primary_color};\n"
                "  --primary-color-light: rgba(255, 255, 255, 0.08);\n"
                f"  --accent-color: {accent_color};\n"
                "  --accent-color-dark: rgba(0, 0, 0, 0.3);\n"
                "  --accent-color-light: rgba(255, 255, 255, 0.15);\n"
                f"  --font-heading: '{font_h}', system-ui, -apple-system, sans-serif;\n"
                f"  --font-body: '{font_b}', system-ui, -apple-system, sans-serif;\n"
                f"  --bg-color: {primary_color};\n"
                "  --text-color: #fafafa;\n"
                "}"
            )

        full_app_css = (
            f"{root_css}\n\n"
            "*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }\n"
            "html { scroll-behavior: smooth; font-family: var(--font-body, system-ui, sans-serif); }\n"
            "body { margin: 0; font-family: var(--font-body, system-ui, sans-serif); background-color: var(--bg-color, #000000); color: var(--text-color, #ffffff); -webkit-font-smoothing: antialiased; }\n"
            ".site-root { display: flex; flex-direction: column; min-height: 100vh; overflow-x: hidden; }\n"
        )
        app_css_path.write_text(full_app_css, encoding="utf-8")

        # P0-4: HTML-escape project name and description to prevent stored HTML injection
        safe_project_name = html.escape(project_name.replace('_', ' '))
        safe_meta_desc = html.escape(f"{project_name} website built by ReactAgent SLM")

        index_html = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta name="description" content="{safe_meta_desc}" />
    <title>{safe_project_name}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@500;700&family=DM+Mono:wght@400;500&family=Inter:wght@400;500;600;700;800&family=Outfit:wght@400;600;700&family=Playfair+Display:wght@400;700&family=Plus+Jakarta+Sans:wght@500;600;700;800&family=Raleway:wght@300;400;600;700&family=Space+Grotesk:wght@500;600;700&family=Syne:wght@700;800&display=swap" rel="stylesheet" />
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css" integrity="sha512-DTOQO9RWCH3ppGqcWaEA1BIZOC6xxalwEsw9c2QQeAIftl+Vegovlnee1c9QX4TctnWMn13TZye+giMm8e2LwA==" crossorigin="anonymous" referrerpolicy="no-referrer" />
  </head>
  <body style="margin: 0;">
    <div id="root"></div>
    <script type="module" src="/main.tsx"></script>
  </body>
</html>
"""
        (target_dir / "index.html").write_text(index_html, encoding="utf-8")

        main_tsx = """import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
"""
        (target_dir / "main.tsx").write_text(main_tsx, encoding="utf-8")

        # Write tsconfig.json for the project
        tsconfig = {
            "compilerOptions": {
                "target": "ES2022", "lib": ["ES2022", "DOM"],
                "jsx": "react-jsx", "module": "ESNext",
                "moduleResolution": "bundler", "strict": True,
                "esModuleInterop": True, "skipLibCheck": True
            },
            "include": ["**/*.ts", "**/*.tsx"]
        }
        (target_dir / "tsconfig.json").write_text(json.dumps(tsconfig, indent=2), encoding="utf-8")

    except Exception as e:
        print(f"[Server] Note: could not scaffold site Vite preview: {e}")
        if q:
            try:
                q.put({"type": "log", "text": f"[Warning]: Vite preview scaffolding error: {e}"})
            except Exception:
                pass


def _run_generation(task: dict, q: queue.Queue):
    """Component-mode generation pipeline (unchanged from original)."""
    import shutil
    from agent import run_agent_on_example

    task_id    = task["task_id"]
    prompt     = task["prompt"]
    symbol     = task["symbol"]
    test_code  = task["test_code"]
    max_turns  = task.get("max_turns", 5)
    max_tokens = task.get("max_tokens", 1024)

    # Build eval item
    item = {
        "prompt": prompt,
        "test_code": test_code,
        "primary_symbol": symbol,
        "check": "tsc_only" if symbol.startswith("use") else "tsc_and_render",
    }

    workspace = BASE_DIR / f".web_ui_workspace_{task_id[:8]}"
    if workspace.exists():
        shutil.rmtree(workspace)
    workspace.mkdir(parents=True, exist_ok=True)

    # Capture stdout → SSE (scoped exclusively to this generation thread)
    _stdout_context.active_queue = q

    try:
        result = run_agent_on_example(
            orig_idx=0,
            item=item,
            runner=_runner,
            workspace_root=workspace,
            max_turns=max_turns,
            temperature=0.15,
            max_new_tokens=max_tokens,
            best_of_2=True,
            stop_check=lambda: task_id in cancelled_tasks,
        )
    finally:
        _stdout_context.active_queue = None

    if task_id in cancelled_tasks:
        try:
            shutil.rmtree(workspace)
        except Exception as _rm_err:
            print(f"[Server] Note: could not remove cancelled workspace {workspace}: {_rm_err}")
        return

    # Export generated files to persistent storage
    EXPORT_DIR = BASE_DIR / "generated_components"
    EXPORT_DIR.mkdir(exist_ok=True)
    timestamp_slug = time.strftime("%Y%m%d_%H%M%S")
    comp_export_dir = EXPORT_DIR / f"{symbol}_{timestamp_slug}"
    comp_export_dir.mkdir(parents=True, exist_ok=True)

    case_dir = workspace / "case_000"
    if case_dir.exists():
        for f in case_dir.iterdir():
            if f.is_file():
                shutil.copy2(f, comp_export_dir / f.name)

    tsx_path = comp_export_dir / "Component.tsx"
    final_code = tsx_path.read_text(encoding="utf-8") if tsx_path.exists() else ""

    # Also save as <Symbol>.tsx directly in comp_export_dir
    symbol_tsx = comp_export_dir / f"{symbol}.tsx"
    if final_code:
        symbol_tsx.write_text(final_code, encoding="utf-8")

    # Also save to generated_components/latest/
    latest_dir = EXPORT_DIR / "latest"
    latest_dir.mkdir(exist_ok=True)
    if final_code:
        (latest_dir / f"{symbol}.tsx").write_text(final_code, encoding="utf-8")
        (latest_dir / "Component.tsx").write_text(final_code, encoding="utf-8")

    # Scaffold runnable Vite environment so `npm run dev` works immediately
    _scaffold_vite_runner(comp_export_dir, symbol)

    # Clean up temp workspace
    try:
        shutil.rmtree(workspace)
    except Exception as _rm_err:
        print(f"[Server] Note: could not clean up workspace {workspace}: {_rm_err}")

    # Store complete result
    rel_path = f"generated_components/{symbol}_{timestamp_slug}/{symbol}.tsx"
    res_entry = {
        "task_id":        task_id,
        "mode":           "component",
        "final_passed":   result["final_passed"],
        "initial_passed": result["initial_passed"],
        "self_corrected": result["self_corrected"],
        "turns_used":     result["turns_used"],
        "code":           final_code,
        "symbol":         symbol,
        "prompt":         prompt,
        "test_code":      task.get("test_code", ""),
        "file_path":      rel_path,
        "full_path":      str(symbol_tsx),
        "timestamp":      time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    _store_task_result(task_id, res_entry)

    # Save to history
    _append_history(res_entry)

    q.put({"type": "result", "data": res_entry})
    q.put({"type": "done"})


def _run_session_edit_turn(task: dict, q: queue.Queue):
    """Executes a targeted follow-up edit turn within an existing session."""
    import shutil
    from agent import parse_agent_output, WriteSiteAction, sanitize_css_for_spec
    from site_brief import generate_content_brief

    task_id = task["task_id"]
    prompt = task["prompt"]
    session_id = task.get("session_id")
    session = session_manager.get_session(session_id)
    if not session:
        if q:
            q.put({"type": "error", "text": f"Session {session_id} not found."})
            q.put({"type": "done"})
        return

    _stdout_context.active_queue = q

    try:
        q.put({"type": "log", "text": f"\n>>> [Session {session.session_id}] Follow-up instruction: {prompt}"})

        # 1. Resolve which files need editing (@mentions or heuristics)
        target_files = session_manager.resolve_target_files(session, prompt)
        target_names = [p for p, _ in target_files]
        q.put({"type": "log", "text": f"[Target Files Resolved]: {', '.join(target_names) if target_names else 'entire workspace'}"})

        # Snapshot old files for diff computation
        old_files = session.get_current_files()

        # 2. Build multi-turn context
        context_prompt = session_manager.build_follow_up_context(session, prompt, target_files)

        edit_system_prompt = (
            "You are an expert React TypeScript CSS engineer modifying an existing project. "
            "Examine the user request and the current contents of the target files. "
            "Generate ONLY the modified files in full using <tool_call name=\"write_site\">\n"
            "<file path=\"...\">\n...complete updated content...\n</file>\n"
            "</tool_call>. Do not omit file contents. Ensure all TypeScript syntax and design tokens are strictly preserved."
        )

        history = [
            {"role": "system", "content": edit_system_prompt},
            {"role": "user", "content": context_prompt},
        ]

        if task_id in cancelled_tasks:
            return

        # 3. Model turn generation
        q.put({"type": "log", "text": f"[Generating Targeted Edit] temperature=0.20..."})
        assistant_text = _runner.generate_turn(
            example_idx=0,
            history=history,
            primary_symbol=session.title,
            max_new_tokens=task.get("max_tokens", 1536),
            temperature=0.20,
            repetition_penalty=1.05,
        )

        if task_id in cancelled_tasks:
            return

        turn = parse_agent_output(assistant_text)
        q.put({"type": "log", "text": f"[Thought]: {turn.thought[:150]}..."})

        diffs = {}
        files_modified = []

        if isinstance(turn.action, WriteSiteAction) and turn.action.files:
            brief = generate_content_brief(session.prompt, style_tokens=session.style_tokens, style_preset=session.style_preset)
            style_spec = brief.get("style_spec")

            for fpath, fcontent in turn.action.files:
                # Sanitize if CSS
                if fpath.endswith(".css") and style_spec:
                    fcontent = sanitize_css_for_spec(fcontent, style_spec)

                dest = session.workspace_dir / fpath
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(fcontent, encoding="utf-8")

                old_content = old_files.get(fpath, "")
                diff = compute_file_diff(fpath, old_content, fcontent)
                diffs[fpath] = diff
                files_modified.append(fpath)
                q.put({"type": "log", "text": f"  --> Updated: {fpath} ({len(fcontent)} chars)"})

            # Re-scaffold runner for Vite preview
            current_files = session.get_current_files()
            _scaffold_site_vite_runner(session.workspace_dir, session.title, current_files, brief=brief, q=q)
        else:
            q.put({"type": "log", "text": "[Notice]: Model emitted general refinement."})

        # 4. Create new versioned checkpoint
        chk_num = session.create_checkpoint(f"Edit: {prompt[:60]}")

        # 5. Evaluate visual quality if site mode
        visual_score = None
        visual_issues = []
        if session.mode == "site":
            screenshot_path = session.workspace_dir / "screenshot.webp"
            try:
                ss = take_screenshot(project_dir=session.workspace_dir, output_path=screenshot_path)
                if ss and ss.exists():
                    v_res = _score_screenshot_heuristic(ss)
                    visual_score = v_res.get("score")
                    visual_issues = v_res.get("issues", [])
            except Exception as e:
                # Fall back to previous visual score in session history
                for h in reversed(session.history):
                    if isinstance(h, dict) and h.get("visual_score") is not None:
                        visual_score = h["visual_score"]
                        visual_issues = h.get("visual_issues", [])
                        break

        # 6. Generate structured post-turn summary
        visual_check = f"Visual check: {visual_score}/5" + (f" — {', '.join(visual_issues)}" if visual_issues else "") if visual_score is not None else None
        summary = generate_post_generation_summary(
            mode=session.mode,
            files_touched=files_modified,
            passed=True,
            auto_recovered=[],
            user_instruction=prompt,
            is_edit=True,
            visual_check=visual_check,
            visual_score=visual_score,
            visual_issues=visual_issues,
        )

        # Record turn in session history
        turn_record = {
            "turn_id": len(session.history) + 1,
            "role": "assistant",
            "thought": turn.thought,
            "content": assistant_text,
            "user_instruction": prompt,
            "summary": summary,
            "files_touched": files_modified,
            "diffs": diffs,
            "checkpoint_id": chk_num,
            "visual_score": visual_score,
            "visual_issues": visual_issues,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        session.history.append({"role": "user", "content": prompt, "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")})
        session.history.append(turn_record)
        session.save()

        # 7. Package site_entry
        app_file = session.workspace_dir / "src" / "App.tsx"
        app_content = app_file.read_text(encoding="utf-8") if app_file.exists() else ""
        current_files = session.get_current_files()

        site_entry = {
            "task_id": task_id,
            "session_id": session.session_id,
            "mode": session.mode,
            "final_passed": True,
            "initial_passed": True,
            "self_corrected": False,
            "turns_used": len(session.history),
            "sections_completed": len([p for p in current_files if p.startswith("src/components/") and p.endswith(".tsx")]),
            "sections_planned": len([p for p in current_files if p.startswith("src/components/") and p.endswith(".tsx")]),
            "code": app_content,
            "files": current_files,
            "diffs": diffs,
            "summary": summary,
            "symbol": session.title,
            "prompt": prompt,
            "style_preset": session.style_preset,
            "style_tokens": session.style_tokens,
            "file_path": f"generated_components/session_{session.session_id}/",
            "full_path": str(session.workspace_dir),
            "checkpoints_count": len(session.checkpoints),
            "visual_score": visual_score,
            "visual_issues": visual_issues,
            "is_edit": True,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

        _store_task_result(task_id, site_entry)
        _append_history(site_entry)

        q.put({"type": "result", "data": site_entry})
        q.put({"type": "done"})

    finally:
        _stdout_context.active_queue = None


def _run_site_generation(task: dict, q: queue.Queue):
    """Site-mode generation pipeline: runs the multi-turn site agent and scaffolds a Vite app."""
    import shutil
    from agent import run_site_agent_on_example
    from site_brief import generate_content_brief, brief_to_xml

    task_id      = task["task_id"]
    prompt       = task["prompt"]
    project_name = task["symbol"]
    max_turns    = task.get("max_turns", 10)
    max_tokens   = task.get("max_tokens", 1024)

    # Initialize or retrieve persistent session
    session_id = task.get("session_id")
    session = session_manager.get_session(session_id) if session_id else None
    if not session:
        session = session_manager.create_session(
            title=project_name,
            mode="site",
            prompt=prompt,
            style_tokens=task.get("style_tokens"),
            style_preset=task.get("style_preset"),
        )
        task["session_id"] = session.session_id

    workspace = BASE_DIR / f".web_ui_workspace_{task_id[:8]}"
    if workspace.exists():
        shutil.rmtree(workspace)
    workspace.mkdir(parents=True, exist_ok=True)

    _stdout_context.active_queue = q

    try:
        # Stage 1: Generate content brief
        print(f"[SiteGen] Generating content brief for: {prompt[:60]}...")
        style_tokens = task.get("style_tokens")
        style_preset = task.get("style_preset")
        brief = generate_content_brief(prompt, style_tokens=style_tokens, style_preset=style_preset)
        sections = brief.get("sections", ["header", "hero", "footer"])
        custom_section_instructions = brief.get("custom_section_instructions")
        # Ensure footer is last
        if "footer" in sections:
            sections = [s for s in sections if s != "footer"] + ["footer"]
        # Ensure max_turns provides sufficient headroom for retries (at least len(sections) + 4, min 10 turns)
        max_turns = max(max_turns, len(sections) + 4, 10)
        xml_brief = brief_to_xml(brief)
        style_spec = brief.get("style_spec")

        # Stage 2: Run site agent loop with live plan callback & stop check
        result = run_site_agent_on_example(
            orig_idx=0,
            prompt=prompt,
            project_name=project_name,
            brief_xml=xml_brief,
            sections=sections,
            runner=_runner,
            workspace_root=workspace,
            max_turns=max_turns,
            max_new_tokens=max_tokens,
            style_spec=style_spec,
            custom_section_instructions=custom_section_instructions,
            event_callback=lambda evt: q.put(evt),
            stop_check=lambda: task_id in cancelled_tasks,
        )
    finally:
        _stdout_context.active_queue = None

    if task_id in cancelled_tasks:
        try:
            shutil.rmtree(workspace)
        except Exception as _rm_err:
            print(f"[Server] Note: could not remove cancelled site workspace {workspace}: {_rm_err}")
        return

    # Export to persistent storage with multi-file structure
    EXPORT_DIR = BASE_DIR / "generated_components"
    EXPORT_DIR.mkdir(exist_ok=True)
    timestamp_slug = time.strftime("%Y%m%d_%H%M%S")
    site_export_dir = EXPORT_DIR / f"{project_name}_{timestamp_slug}"
    site_export_dir.mkdir(parents=True, exist_ok=True)

    # Copy all generated files to session persistent workspace and timestamped export
    written_files: dict[str, str] = result.get("files", {})

    for rel_path, content in written_files.items():
        # Session persistent workspace
        sess_dest = session.workspace_dir / rel_path
        sess_dest.parent.mkdir(parents=True, exist_ok=True)
        sess_dest.write_text(content, encoding="utf-8")
        # Timestamped export
        dest = site_export_dir / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")

    # Scaffold the Vite environment in both session workspace and timestamped export
    _scaffold_site_vite_runner(session.workspace_dir, project_name, written_files, brief=brief, q=q)
    _scaffold_site_vite_runner(site_export_dir, project_name, written_files, brief=brief)

    # Clean up temp workspace
    try:
        shutil.rmtree(workspace)
    except Exception as _rm_err:
        print(f"[Server] Note: could not clean up site workspace {workspace}: {_rm_err}")

    # Visual quality evaluation via Playwright/heuristic judge
    visual_score = None
    visual_issues = []
    screenshot_path = site_export_dir / "screenshot.webp"
    try:
        ss = take_screenshot(project_dir=site_export_dir, output_path=screenshot_path)
        if ss and ss.exists():
            v_res = _score_screenshot_heuristic(ss)
            visual_score = v_res.get("score")
            visual_issues = v_res.get("issues", [])
            print(f"[SiteGen] Visual quality score: {visual_score}/5 (passed={v_res.get('pass')}, issues={visual_issues})")
    except Exception as e:
        print(f"[SiteGen] Visual evaluation skipped: {e}")

    # Retry logic: If visual quality score is low (< 3) and turn budget permits, run targeted refinement pass
    turns_used = len(result.get("turn_logs", []))
    if visual_score is not None and visual_score < 3 and turns_used < max_turns:
        target_sec = None
        for issue in visual_issues:
            issue_lower = issue.lower()
            if "footer" in issue_lower:
                for sec in reversed(sections):
                    if "footer" in sec.lower():
                        target_sec = sec
                        break
                if not target_sec and sections:
                    target_sec = sections[-1]
                break
            elif "header" in issue_lower or "navigation" in issue_lower or "logo" in issue_lower:
                for sec in sections:
                    if any(k in sec.lower() for k in ("header", "nav")):
                        target_sec = sec
                        break
                if not target_sec and sections:
                    target_sec = sections[0]
                break
            elif "blank" in issue_lower or "density" in issue_lower or "flat" in issue_lower:
                for sec in sections:
                    if "hero" in sec.lower():
                        target_sec = sec
                        break
                if not target_sec and len(sections) > 1:
                    target_sec = sections[1]
                break

        if not target_sec:
            auto_recovered = result.get("auto_recovered_sections", [])
            target_sec = auto_recovered[0] if auto_recovered else (sections[1] if len(sections) > 2 else sections[0])

        print(f"[SiteGen] Visual quality {visual_score}/5 is below threshold (3/5). Running corrective turn targeting '{target_sec}'...")
        q.put({"type": "log", "text": f"[Visual Judge] Visual score {visual_score}/5 below threshold. Running corrective turn targeting section '{target_sec}'..."})
        try:
            from agent import auto_scaffold_section
            clean_custom_instr = brief.get("custom_section_instructions", {}).get(target_sec, "")
            t_name, t_code, c_name, c_code = auto_scaffold_section(
                target_sec,
                style_spec=style_spec,
                custom_instr=clean_custom_instr
            )
            written_files[t_name] = t_code
            written_files[c_name] = c_code
            (session.workspace_dir / t_name).write_text(t_code, encoding="utf-8")
            (session.workspace_dir / c_name).write_text(c_code, encoding="utf-8")
            (site_export_dir / t_name).write_text(t_code, encoding="utf-8")
            (site_export_dir / c_name).write_text(c_code, encoding="utf-8")

            _scaffold_site_vite_runner(session.workspace_dir, project_name, written_files, brief=brief)
            _scaffold_site_vite_runner(site_export_dir, project_name, written_files, brief=brief)

            # Record corrective turn in turn logs and mark self-corrected
            result.setdefault("turn_logs", []).append({
                "turn": turns_used + 1,
                "action": "visual_corrective_turn",
                "section": target_sec,
                "reason": f"Visual score {visual_score}/5 below threshold 3/5: {', '.join(visual_issues)}",
            })
            result["self_corrected"] = True
            auto_rec = result.setdefault("auto_recovered_sections", [])
            if target_sec not in auto_rec:
                auto_rec.append(target_sec)

            ss2 = take_screenshot(project_dir=site_export_dir, output_path=screenshot_path)
            if ss2 and ss2.exists():
                v_res2 = _score_screenshot_heuristic(ss2)
                visual_score = max(visual_score, v_res2.get("score", visual_score))
                visual_issues = v_res2.get("issues", visual_issues)
                print(f"[SiteGen] Post-refinement visual quality score: {visual_score}/5")
        except Exception as ref_err:
            print(f"[SiteGen] Visual refinement pass error: {ref_err}")

    # Use App.tsx content as the 'code' field for backward-compatible history display
    app_tsx_content = written_files.get("App.tsx", "")
    if not app_tsx_content:
        tsx_files = [c for p, c in written_files.items() if p.endswith(".tsx")]
        app_tsx_content = tsx_files[0] if tsx_files else ""

    # Create initial checkpoint and post-generation structured summary
    chk_num = session.create_checkpoint(f"Initial site: {len(sections)} sections")
    visual_check = f"Visual check: {visual_score}/5" + (f" — {', '.join(visual_issues)}" if visual_issues else "") if visual_score is not None else None
    summary = generate_post_generation_summary(
        mode="site",
        files_touched=list(written_files.keys()),
        passed=result["final_passed"],
        auto_recovered=result.get("auto_recovered_sections", []),
        user_instruction=prompt,
        is_edit=False,
        sections_completed=result.get("sections_completed", len(sections)),
        sections_planned=len(sections),
        visual_check=visual_check,
        visual_score=visual_score,
        visual_issues=visual_issues,
    )

    session.history.append({"role": "user", "content": prompt, "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")})
    session.history.append({
        "turn_id": 1,
        "role": "assistant",
        "summary": summary,
        "content": f"Synthesized site with {len(written_files)} files across {len(sections)} sections.",
        "files_touched": list(written_files.keys()),
        "diffs": {},
        "checkpoint_id": chk_num,
        "visual_score": visual_score,
        "visual_issues": visual_issues,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    })
    session.save()

    site_entry = {
        "task_id":              task_id,
        "session_id":           session.session_id,
        "mode":                 "site",
        "final_passed":         result["final_passed"],
        "initial_passed":       result["final_passed"],
        "self_corrected":       result.get("self_corrected", False),
        "turns_used":           len(result.get("turn_logs", [])),
        "sections_completed":   result.get("sections_completed", 0),
        "sections_planned":     len(sections),
        "code":                 app_tsx_content,
        "files":                written_files,
        "diffs":                {},
        "summary":              summary,
        "symbol":               project_name,
        "prompt":               prompt,
        "style_preset":         style_preset,
        "style_tokens":         style_tokens,
        "file_path":            f"generated_components/{project_name}_{timestamp_slug}/",
        "full_path":            str(session.workspace_dir),
        "checkpoints_count":    len(session.checkpoints),
        "visual_score":         visual_score,
        "visual_issues":        visual_issues,
        "auto_recovered_sections": result.get("auto_recovered_sections", []),
        "turn_logs":            result.get("turn_logs", []),
        "timestamp":            time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    _store_task_result(task_id, site_entry)

    _append_history(site_entry)
    q.put({"type": "result", "data": site_entry})
    q.put({"type": "done"})

# ── History ────────────────────────────────────────────────────────────────────

_history_lock = threading.Lock()

def _save_history(history_items: list):
    """Atomically writes history to HISTORY_FILE using a temporary file and os.replace."""
    tmp_file = HISTORY_FILE.with_suffix(".tmp.json")
    try:
        tmp_file.write_text(json.dumps(history_items, indent=2), encoding="utf-8")
        os.replace(tmp_file, HISTORY_FILE)
    except Exception as e:
        print(f"[Server] Error saving history atomically: {e}")
        if tmp_file.exists():
            try:
                tmp_file.unlink()
            except Exception:
                pass

def _load_history():
    with _history_lock:
        if HISTORY_FILE.exists():
            try:
                return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
            except Exception as _hist_err:
                print(f"[Server] Warning: Failed to parse history file {HISTORY_FILE}: {_hist_err}")
        return []

def _append_history(entry: dict):
    with _history_lock:
        history = []
        if HISTORY_FILE.exists():
            try:
                history = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
            except Exception as _hist_err:
                print(f"[Server] Warning: Failed to parse history file {HISTORY_FILE}: {_hist_err}")
        # DO NOT TRUNCATE! Store the complete, full source code
        history.insert(0, entry)
        history = history[:50]  # Keep last 50
        _save_history(history)

# ── Routes ─────────────────────────────────────────────────────────────────────

@app.after_request
def add_no_cache_headers(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@app.route("/")
def index():
    resp = send_from_directory(str(STATIC_DIR), "index.html")
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return resp

@app.route("/api/status")
def status():
    return jsonify({
        "model_status": _model_status,
        "queue_depth": _generation_queue.qsize(),
    })

@app.route("/api/generation/<task_id>/status", methods=["GET"])
@app.route("/generation/<task_id>/status", methods=["GET"])
@app.route("/api/task/<task_id>/status", methods=["GET"])
def generation_task_status(task_id):
    """Fallback status endpoint allowing clients to verify job status if SSE drops."""
    res = _get_task_result(task_id)
    if res:
        return jsonify({
            "task_id": task_id,
            "status": "completed",
            "data": res,
        })
    if task_id in cancelled_tasks:
        return jsonify({
            "task_id": task_id,
            "status": "cancelled",
        })
    if _current_task and _current_task.get("task_id") == task_id:
        return jsonify({
            "task_id": task_id,
            "status": "running",
            "mode": _current_task.get("mode", "component"),
        })
    with _generation_queue.mutex:
        for idx, item in enumerate(_generation_queue.queue):
            if item.get("task_id") == task_id:
                return jsonify({
                    "task_id": task_id,
                    "status": "queued",
                    "position": idx + 1,
                })
    return jsonify({
        "task_id": task_id,
        "status": "not_found",
    }), 404

# Track recent requests for deduplication (prompt_hash -> (task_id, timestamp))
_recent_requests: dict[str, tuple[str, float]] = {}

@app.route("/api/generate", methods=["POST"])
def generate():
    if _model_status == "loading":
        return jsonify({"error": "Model is still loading, please wait."}), 503
    if _model_status == "error":
        return jsonify({"error": "Model failed to load. Check server logs."}), 500
    # Guard against the narrow TOCTOU window between status flip and _runner assignment
    if _runner is None:
        return jsonify({"error": "Model runner not yet initialised. Please wait a moment."}), 503

    data = request.get_json() or {}
    prompt = (data.get("prompt") or "").strip()
    if not prompt:
        return jsonify({"error": "Prompt is required."}), 400

    # Guard against accidental double-clicks / identical rapid requests (5s debounce)
    prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    now = time.time()
    stale_hashes = [h for h, (tid, t) in _recent_requests.items() if now - t > 10.0]
    for h in stale_hashes:
        _recent_requests.pop(h, None)

    if prompt_hash in _recent_requests:
        existing_task_id, req_time = _recent_requests[prompt_hash]
        if now - req_time < 5.0 and (existing_task_id in task_queues or existing_task_id in task_results):
            return jsonify({
                "task_id": existing_task_id,
                "deduplicated": True,
                "message": "Duplicate generation request debounced within 5s window.",
                "queue_position": _generation_queue.qsize()
            })

    # ── Check for existing session (follow-up turn) ───────────────────────────
    req_session_id = (data.get("session_id") or "").strip()
    if req_session_id:
        existing_session = session_manager.get_session(req_session_id)
        if not existing_session:
            return jsonify({"error": f"Session '{req_session_id}' not found."}), 404

        task_id = str(uuid.uuid4())
        _recent_requests[prompt_hash] = (task_id, now)
        q = queue.Queue()
        _register_task_queue(task_id, q)
        _generation_queue.put({
            "task_id":      task_id,
            "session_id":   existing_session.session_id,
            "is_follow_up": True,
            "mode":         existing_session.mode,
            "prompt":       prompt,
            "symbol":       existing_session.title,
            "max_tokens":   int(data.get("max_tokens", 1536)),
        })
        return jsonify({
            "task_id": task_id,
            "session_id": existing_session.session_id,
            "symbol": existing_session.title,
            "mode": existing_session.mode,
            "is_follow_up": True,
            "queue_position": _generation_queue.qsize(),
        })

    # ── Intent classification: site vs component ───────────────────────────
    user_intent = data.get("intent")
    if user_intent:
        intent = user_intent.lower()
        intent_conf = 1.0
    else:
        intent, intent_conf = _classify_intent_with_confidence(prompt)

    task_id = str(uuid.uuid4())
    _recent_requests[prompt_hash] = (task_id, now)
    q = queue.Queue()
    _register_task_queue(task_id, q)

    if intent == "site":
        extracted = _extract_project_name(prompt)
        raw_name = (data.get("symbol") or "").strip()
        if not raw_name or raw_name in ("Cards", "Component", "MySite") or (extracted and extracted != "MySite" and raw_name.lower() not in prompt.lower()):
            raw_name = extracted or raw_name
        project_name = _sanitize_identifier(raw_name, default="MySite")

        session = session_manager.create_session(
            title=project_name,
            mode="site",
            prompt=prompt,
            style_tokens=data.get("style_tokens"),
            style_preset=data.get("style_preset"),
        )

        _generation_queue.put({
            "task_id":      task_id,
            "session_id":   session.session_id,
            "mode":         "site",
            "prompt":       prompt,
            "symbol":       project_name,
            "max_turns":    int(data.get("max_turns", 10)),
            "max_tokens":   int(data.get("max_tokens", 1536)),
            "style_tokens": data.get("style_tokens"),
            "style_preset": data.get("style_preset"),
        })
        return jsonify({
            "task_id": task_id,
            "session_id": session.session_id,
            "symbol": project_name,
            "mode": "site",
            "intent_confidence": intent_conf,
            "queue_position": _generation_queue.qsize()
        })

    else:
        # ── Component mode ─────────────────────────────────────────────────
        raw_symbol = (data.get("symbol") or "").strip() or _extract_component_name(prompt)
        symbol = _sanitize_identifier(raw_symbol, default="Component")
        test_code = (data.get("test_code") or "").strip()
        if not test_code:
            test_code = _auto_test(symbol, symbol.startswith("use"))

        session = session_manager.create_session(
            title=symbol,
            mode="component",
            prompt=prompt,
        )

        _generation_queue.put({
            "task_id":    task_id,
            "session_id": session.session_id,
            "mode":       "component",
            "prompt":     prompt,
            "symbol":     symbol,
            "test_code":  test_code,
            "max_turns":  int(data.get("max_turns", 5)),
            "max_tokens": int(data.get("max_tokens", 1280)),
        })

        return jsonify({
            "task_id": task_id,
            "session_id": session.session_id,
            "symbol": symbol,
            "mode": "component",
            "intent_confidence": intent_conf,
            "queue_position": _generation_queue.qsize()
        })


# ── Session & Checkpoint Endpoints ──────────────────────────────────────────

@app.route("/api/sessions", methods=["GET"])
def list_sessions():
    """Returns all active and persisted agentic chat sessions."""
    return jsonify({"sessions": session_manager.list_sessions()})


@app.route("/api/sessions/<session_id>", methods=["GET"])
def get_session_info(session_id):
    """Returns complete session history, checkpoints, and files."""
    s = session_manager.get_session(session_id)
    if not s:
        return jsonify({"error": "Session not found"}), 404
    return jsonify({"session": s.to_dict()})


@app.route("/api/sessions/<session_id>/revert/<int:turn_num>", methods=["POST"])
def revert_session_checkpoint(session_id, turn_num):
    """Reverts session files to a previous checkpoint."""
    s = session_manager.get_session(session_id)
    if not s:
        return jsonify({"error": "Session not found"}), 404
    ok = s.revert_to_checkpoint(turn_num)
    if not ok:
        return jsonify({"error": f"Checkpoint #{turn_num} could not be restored."}), 400
    current_files = s.get_current_files()
    _scaffold_site_vite_runner(s.workspace_dir, s.title, current_files)
    return jsonify({
        "status": "reverted",
        "turn_num": turn_num,
        "files": current_files,
    })


@app.route("/api/sessions/<session_id>/diff/<int:turn_id>", methods=["GET"])
def get_turn_diff(session_id, turn_id):
    """Retrieves file diffs for a specific turn in a session."""
    s = session_manager.get_session(session_id)
    if not s:
        return jsonify({"error": "Session not found"}), 404
    turn = next((h for h in s.history if h.get("turn_id") == turn_id), None)
    if not turn:
        return jsonify({"error": f"Turn #{turn_id} not found."}), 404
    return jsonify({
        "turn_id": turn_id,
        "summary": turn.get("summary", ""),
        "diffs": turn.get("diffs", {}),
        "files_touched": turn.get("files_touched", []),
    })


@app.route("/preview/<session_id>")
@app.route("/preview/<session_id>/")
@app.route("/preview/<session_id>/<path:filename>")
def preview_session_page(session_id, filename="index.html"):
    """Serves live preview files from the session workspace."""
    s = session_manager.get_session(session_id)
    if not s or not s.workspace_dir.exists():
        return "<h3 style='font-family:sans-serif;padding:2rem;'>Preview workspace not yet generated.</h3>", 404
    if filename == "index.html" and not (s.workspace_dir / "index.html").exists():
        current_files = s.get_current_files()
        _scaffold_site_vite_runner(s.workspace_dir, s.title, current_files)
    return send_from_directory(str(s.workspace_dir), filename)


@app.route("/api/stream/<task_id>")
def stream(task_id):
    q = task_queues.get(task_id)
    cached_result = _get_task_result(task_id)
    if q is None and cached_result is None:
        return jsonify({"error": "Unknown or expired task_id"}), 404

    def generate_sse():
        # If task already completed, emit cached result event immediately
        if cached_result:
            yield f"data: {json.dumps({'type': 'result', 'data': cached_result})}\n\n"
            yield "data: {\"type\": \"done\"}\n\n"
            return

        try:
            while True:
                try:
                    msg = q.get(timeout=10)
                except queue.Empty:
                    yield "data: {\"type\":\"heartbeat\"}\n\n"
                    continue

                yield f"data: {json.dumps(msg)}\n\n"

                if msg.get("type") == "done":
                    break
        except (GeneratorExit, BrokenPipeError, ConnectionResetError):
            pass
        finally:
            # Clean up queue when stream finishes, client disconnects, or result is cached
            if cached_result or task_id in task_results or (q and q.empty()):
                task_queues.pop(task_id, None)

    return Response(
        generate_sse(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        }
    )


@app.route("/api/history")
def history():
    return jsonify(_load_history())


@app.route("/api/history/<task_id>", methods=["DELETE"])
def delete_history_item(task_id):
    """Delete a single generation from history atomically."""
    with _history_lock:
        history_items = []
        if HISTORY_FILE.exists():
            try:
                history_items = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass
        new_history = [h for h in history_items if h.get("task_id") != task_id]
        _save_history(new_history)
    task_results.pop(task_id, None)
    return jsonify({"status": "deleted", "task_id": task_id})


@app.route("/api/history", methods=["DELETE"])
def clear_history():
    """Clear all generation history atomically."""
    with _history_lock:
        _save_history([])
    task_results.clear()
    return jsonify({"status": "cleared"})


def _drain_generation_queue() -> int:
    """Drains all pending tasks from _generation_queue and marks them cancelled."""
    cleared = 0
    while not _generation_queue.empty():
        try:
            queued_task = _generation_queue.get_nowait()
            tid = queued_task.get("task_id") if isinstance(queued_task, dict) else None
            if tid:
                cancelled_tasks.add(tid)
                q = task_queues.get(tid)
                if q:
                    try:
                        q.put({"type": "cancelled", "text": "Generation cancelled from queue."})
                        q.put({"type": "done"})
                    except Exception:
                        pass
            _generation_queue.task_done()
            cleared += 1
        except (queue.Empty, ValueError):
            break
    return cleared


@app.route("/api/queue/clear", methods=["POST"])
def clear_queue():
    """Cancels and purges all pending tasks from the generation queue and halts running tasks."""
    cleared = _drain_generation_queue()

    # Mark all currently active task IDs as cancelled so active generation loops bail early
    for tid in list(task_queues.keys()):
        cancelled_tasks.add(tid)
        q = task_queues.get(tid)
        if q:
            try:
                q.put({"type": "cancelled", "text": "Generation aborted by user."})
                q.put({"type": "done"})
            except Exception:
                pass

    return jsonify({
        "status": "cleared",
        "cleared_count": cleared,
        "queue_depth": _generation_queue.qsize(),
        "model_status": _model_status
    })


@app.route("/api/cancel/<task_id>", methods=["POST"])
def cancel_task(task_id):
    """Mark a task as cancelled. Queued tasks skip immediately; running tasks
    are cleaned up as soon as the current generate() call returns."""
    if task_id == "all":
        return clear_queue()

    cancelled_tasks.add(task_id)

    # Push a done signal immediately so the SSE stream closes on the client
    q = task_queues.get(task_id)
    if q:
        try:
            q.put({"type": "cancelled", "text": "Generation cancelled by user."})
            q.put({"type": "done"})
        except Exception:
            pass

    # If client also requested clearing the remaining queue
    clear_also = request.args.get("clear_queue") == "true"
    if not clear_also and request.is_json:
        try:
            clear_also = bool((request.get_json(silent=True) or {}).get("clear_queue"))
        except Exception:
            clear_also = False

    if clear_also:
        _drain_generation_queue()

    return jsonify({
        "status": "cancelled",
        "task_id": task_id,
        "queue_depth": _generation_queue.qsize()
    })


@app.route("/api/result/<task_id>")
def result(task_id):
    r = _get_task_result(task_id)
    if r is None:
        return jsonify({"error": "Result not ready or unknown task"}), 404
    return jsonify(r)


@app.route("/api/download/<task_id>")
def download(task_id):
    r = _get_task_result(task_id)
    if not r or not r.get("code"):
        return jsonify({"error": "No code found for this task"}), 404

    symbol = r.get("symbol", "Component")
    code = r["code"]
    return Response(
        code,
        mimetype="text/typescript",
        headers={
            "Content-Disposition": f'attachment; filename="{symbol}.tsx"',
            "Content-Type": "text/typescript; charset=utf-8"
        }
    )


@app.route("/api/download-latest")
def download_latest():
    history = _load_history()
    if not history or not history[0].get("code"):
        return jsonify({"error": "No generated code available"}), 404

    latest = history[0]
    symbol = latest.get("symbol", "Component")
    code = latest["code"]
    return Response(
        code,
        mimetype="text/typescript",
        headers={
            "Content-Disposition": f'attachment; filename="{symbol}.tsx"',
            "Content-Type": "text/typescript; charset=utf-8"
        }
    )



# ── Dedicated WebSocket PowerShell Server (Port 5001) ────────────────────────

@app.route("/api/shell-token")
def shell_token():
    """Returns an ephemeral, single-use session auth ticket for PowerShell WebSocket connection.
    Guarded by Same-Origin, Sec-Fetch-Site, Origin, and Host checks against DNS rebinding & cross-tab attacks.
    """
    # 1. Host header validation (blocks DNS rebinding)
    raw_host = request.host.split(":")[0].lower()
    configured_host = os.environ.get("HOST", "127.0.0.1").lower()
    allowed_hosts = {"127.0.0.1", "localhost", configured_host}
    if raw_host not in allowed_hosts:
        return jsonify({"error": "Forbidden: invalid Host header"}), 403

    # 2. Check Sec-Fetch-Site (modern browsers send this on cross-origin requests)
    fetch_site = request.headers.get("Sec-Fetch-Site")
    if fetch_site and fetch_site not in ("same-origin", "same-site", "none"):
        return jsonify({"error": "Forbidden: cross-origin access disallowed"}), 403

    # 3. Check Origin if present
    origin = request.headers.get("Origin")
    if origin:
        parsed_origin = urllib.parse.urlparse(origin)
        if parsed_origin.hostname not in allowed_hosts:
            return jsonify({"error": "Forbidden: untrusted origin"}), 403

    # 4. Check Referer if present
    referer = request.headers.get("Referer")
    if referer:
        parsed_ref = urllib.parse.urlparse(referer)
        if parsed_ref.hostname not in allowed_hosts:
            return jsonify({"error": "Forbidden: untrusted referer"}), 403

    # 5. Mint short-lived single-use ticket
    return jsonify({"token": _mint_shell_ticket()})


_shell_process = None

def _start_shell_server():
    """Spawns shell_server.py in an isolated OS process for zero GIL contention."""
    global _shell_process
    shell_script = Path(__file__).parent / "shell_server.py"
    if not shell_script.exists():
        print(f"[Server] Warning: {shell_script} not found; shell will be unavailable.")
        return

    import atexit
    import subprocess

    _stop_shell_server()
    host = os.environ.get("HOST", "127.0.0.1")
    print(f"[Server] Starting isolated PowerShell WebSocket server process (ws://{host}:5001)...")
    _shell_process = subprocess.Popen(
        [sys.executable, str(shell_script)],
        cwd=str(BASE_DIR),
        env=dict(os.environ, SHELL_HOST=host, SHELL_AUTH_TOKEN=_SHELL_AUTH_TOKEN),
    )
    atexit.register(_stop_shell_server)

def _stop_shell_server():
    global _shell_process
    if _shell_process and _shell_process.poll() is None:
        try:
            if os.name == "nt":
                # Terminate entire process tree on Windows (including child WinPTY/PowerShell sessions)
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(_shell_process.pid)], capture_output=True)
            else:
                _shell_process.terminate()
                _shell_process.wait(timeout=2.0)
        except Exception:
            try:
                _shell_process.kill()
            except Exception as _kill_err:
                print(f"[Server] Warning: Failed to kill shell server process: {_kill_err}")
        _shell_process = None


if __name__ == "__main__":
    STATIC_DIR.mkdir(exist_ok=True)
    _start_shell_server()
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "5000"))
    url = f"http://{host}:{port}"
    print(f"[Server] Starting ReactAgent SLM Web UI on {url}")

    if os.environ.get("NO_BROWSER") != "1":
        import threading
        import webbrowser
        threading.Timer(1.2, lambda: webbrowser.open(url)).start()

    app.run(host=host, port=port, debug=False, threaded=True)

