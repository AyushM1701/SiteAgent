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
import io
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
import zipfile
from pathlib import Path
from typing import Any, Callable, Optional, Dict, List

# ── Paths & Environment ────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "web_ui_static"
HISTORY_FILE = BASE_DIR / "web_ui_history.json"
_PROMOTED_PTR = BASE_DIR / "models" / "promoted_model.json"
_MOTION_ADAPTER = BASE_DIR / "models" / "qwen3-siteagent-motion-r16"
_CANDIDATE_ADAPTER = BASE_DIR / "models" / "qwen3-siteagent-r16-sft"
_LEGACY_ADAPTER = BASE_DIR / "my-react-agent-lora"
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


def _resolve_default_model() -> str:
    # Promotion metadata alone cannot establish architecture compatibility.
    from agent.base_model_fingerprint import verify_lora_adapter_compatibility

    def usable(path: Path) -> bool:
        if not path.exists():
            return False
        if (path / "adapter_config.json").exists():
            try:
                verify_lora_adapter_compatibility(path, BASE_DIR / "base-model")
            except Exception as exc:
                print(f"[Server] Ignoring incompatible adapter {path}: {exc}")
                return False
        return (path / "config.json").exists() or (path / "adapter_config.json").exists()

    if _PROMOTED_PTR.is_file():
        try:
            data = json.loads(_PROMOTED_PTR.read_text(encoding="utf-8"))
            target = data.get("promoted_model_path")
            required_gates = {"completion", "fidelity", "interaction", "visual_quality", "motion", "runtime_3d"}
            if target and data.get("gate_status") == "PASSED" and required_gates.issubset(set(data.get("verified_gates", []))):
                p = BASE_DIR / target if not Path(target).is_absolute() else Path(target)
                if usable(p):
                    from training.promotion_evidence import require_promotion_evidence
                    require_promotion_evidence(data, p, BASE_DIR)
                    return str(p)
        except Exception as exc:
            print(f"[Server] Ignoring unverified promotion: {exc}")
    # Unpromoted historical/candidate adapters must never become an implicit default.
    return str(BASE_DIR / "base-model")


_DEFAULT_MODEL = _resolve_default_model()
MODEL_PATH = os.environ.get("MODEL_PATH", _DEFAULT_MODEL)

if str(BASE_DIR / "agent") not in sys.path:
    sys.path.append(str(BASE_DIR / "agent"))
if str(Path(__file__).parent) not in sys.path:
    sys.path.append(str(Path(__file__).parent))
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


from flask import Flask, Response, jsonify, redirect, request, send_file, send_from_directory
from flask_sock import Sock
from server.task_registry import TaskRegistry, TaskState

from agent_protocol import (
    DEFAULT_INFERENCE_MAX_SEQ_LENGTH,
    DEFAULT_MAX_NEW_TOKENS,
    InstallPackageAction,
    RemovePackageAction,
    GetDependenciesAction,
    InspectDependenciesAction,
    ReadFileAction,
    GetWebglErrorsAction,
    GetSceneMetadataAction,
    GetAssetManifestAction,
    EditFileAction,
)
from agent.edit_actions import apply_edit
from agent.section_preflight import preflight_section_files
try:
    from agent.output_budget import extract_complexity_factors, estimate_output_budget
except (ImportError, ModuleNotFoundError):
    from output_budget import extract_complexity_factors, estimate_output_budget
try:
    from agent.config import ModelRuntimeConfig
except (ImportError, ModuleNotFoundError):
    from config import ModelRuntimeConfig
from dependency_manager import DependencyManager, PackagePolicy, PackagePolicyError
from style_ingest import spec_to_css_root
from server.preview_manager import preview_manager
try:
    from server.event_bus import event_bus, AgentEvent, AgentEventType, TaskEventEmitter
except (ImportError, ModuleNotFoundError):
    from event_bus import event_bus, AgentEvent, AgentEventType, TaskEventEmitter
from server.sessions import (
    Session,
    session_manager,
    compute_file_diff,
    generate_post_generation_summary,
)
from visual_judge import _score_screenshot_heuristic, take_screenshot


def resolve_project_path(project_root: Path, rel_path: str, allow_package_json: bool = False) -> Path:
    """Resolve a model-provided relative path against project_root.

    Raises PermissionError if the resolved path escapes the root or if direct
    modification of package.json is attempted without explicit authorization.
    """
    root = project_root.resolve()
    clean = rel_path.lstrip("/\\").replace("\\", "/")
    if not allow_package_json and (clean.lower() == "package.json" or clean.lower().endswith("/package.json")):
        raise PermissionError(
            "[Package Policy] Direct modification of package.json is blocked for model tools. "
            "Use install_package / remove_package tools to manage dependencies."
        )
    candidate = (root / clean).resolve()
    if candidate != root and root not in candidate.parents:
        raise PermissionError(
            f"Path traversal blocked: '{rel_path}' resolves outside project root '{root}'"
        )
    return candidate

import dataclasses
import subprocess

# ── Validation Infrastructure ──────────────────────────────────────────────────

MAX_REPAIR_ATTEMPTS = 3  # blueprint: max 3 verify→repair cycles before FAILED


from agent.project_validator import (
    ValidationResult,
    InteractionValidationResult,
    VisualValidationResult,
)


def _validate_workspace(
    workspace_dir: Path,
    port: int = 0,
    event_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> ValidationResult:
    """Run full authoritative project verification sequence:
    1. Static linting via check_site_files
    2. Contract and Accessibility checks
    3. Full workspace TypeScript compilation (npm run typecheck)
    4. Production bundler build (npm run build)
    5. Start/reuse Vite preview server (preview_running)
    6. Browser runtime check (Playwright headless Chromium monitoring console and page errors, #root mount)
    7. DOM interaction evidence checks (Gate 4b)
    """
    try:
        from agent.project_validator import validate_project as _pv_validate
        return _pv_validate(workspace_dir=workspace_dir, port=port, event_callback=event_callback)
    except Exception as exc:
        print(f"[Server] Note: project_validator fallback: {exc}")
        try:
            brief = json.loads((workspace_dir / 'content_brief.json').read_text(encoding='utf-8'))
        except (OSError, ValueError):
            brief = {}
        return _validate_blocked_site(workspace_dir, brief, [f"[Validation Exception]: {exc}"])

# ── App State ──────────────────────────────────────────────────────────────────

app = Flask(__name__, static_folder=str(STATIC_DIR))
sock = Sock(app)
_project_socket_server = None

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
task_registry = TaskRegistry()
task_results: dict[str, dict] = {}
_task_results = task_results
MAX_CACHED_RESULTS = 100
MAX_CACHED_QUEUES = 100

def _register_task_queue(task_id: str, q: queue.Queue):
    """Registers task queue with bounded eviction to prevent memory leaks."""
    global task_queues
    task_queues[task_id] = q
    task_registry.register(task_id)
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
_loaded_model_info: Optional[Dict[str, Any]] = None
_runner_lock = threading.Lock()
_model_status = "loading"  # loading | ready | busy
_generation_queue: queue.Queue = queue.Queue()

# ── Model Loading ──────────────────────────────────────────────────────────────

def _load_model():
    global _runner, _model_status, _loaded_model_info
    try:
        from agent import AgentModelRunner
        from agent.config import ModelRuntimeConfig
        from agent.base_model_fingerprint import verify_lora_adapter_compatibility
        selected = Path(MODEL_PATH)
        if (selected / "adapter_config.json").is_file():
            verify_lora_adapter_compatibility(selected, BASE_DIR / "base-model")
        active_seq = ModelRuntimeConfig.get_max_seq_length()
        print(f"[Server] Loading model {MODEL_PATH} (max_seq_length={active_seq})...")
        _runner = AgentModelRunner(model_path=MODEL_PATH, max_seq_length=active_seq, is_mock=False)
        from agent.base_model_fingerprint import get_model_fingerprint_info
        _loaded_model_info = get_model_fingerprint_info(_runner.model_path)
        _loaded_model_info["adapter_compatible"] = True
        import torch
        _loaded_model_info["gpu_ready"] = bool(torch.cuda.is_available())
        _model_status = "ready"
        print("[Server] Model ready.")
    except Exception as e:
        _runner = None
        _loaded_model_info = None
        _model_status = "error"
        print(f"[Server] Model load failed: {e}")

if os.environ.get("NO_AUTO_LOAD_MODEL") != "1":
    threading.Thread(target=_load_model, daemon=True).start()

# Task owners clean their own temporary workspaces after saving diagnostics.
# Importing this module (including in tests) must never delete another process's
# active generation workspace. Crash leftovers remain available for inspection.

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
    "web application", "web app for", "monograph", "digital monograph",
    "interactive showcase", "showcase for", "precision-engineered", "web experience",
]

_SITE_PATTERNS = [
    re.compile(r'\b(?:build|create|make|generate|design)\s+(?:a|an|the|me\s+a)?\s*(?:modern|responsive|clean|full|complete|premier|dark-mode|dark)?\s*(?:website|web\s+site|landing\s+page|homepage|portfolio|storefront|showcase|portal|dashboard|monograph)\b', re.I),
    re.compile(r'\b(?:digital\s+)?monograph\b', re.I),
    re.compile(r'\binteractive\s+showcase\b', re.I),
    re.compile(r'\bshowcase\s+for\b', re.I),
    re.compile(r'\bportfolio\s+(?:for|of)\s+[A-Za-z]+', re.I),
    re.compile(r'\b(?:restaurant|cafe|coffee\s+shop|bakery|bar|salon|spa|agency|hotel|fitness|gym|clinic)\s+(?:website|page|site)\b', re.I),
    re.compile(r'\bdashboard\s+(?:with|for)\s+\d+\s+(?:widgets|charts|panels|cards)\b', re.I),
]

def _classify_intent_with_confidence(prompt: str) -> tuple[str, float]:
    """
    Returns ('site' | 'component', confidence) where confidence is between 0.0 and 1.0.
    """
    lower = prompt.lower()

    # 1. Structural multi-section detection: If prompt contains >= 2 explicit sections, it is definitely a site
    try:
        from agent.site_brief import extract_explicit_sections
        explicit_secs = extract_explicit_sections(prompt)
        if explicit_secs and len(explicit_secs) >= 2:
            return "site", 0.99
    except Exception:
        pass

    # 2. Strong site patterns
    for pat in _SITE_PATTERNS:
        if pat.search(prompt):
            return "site", 0.95

    # 3. Site keywords
    for kw in _SITE_KEYWORDS:
        if kw in lower:
            return "site", 0.90

    # 4. Multi-section hints: Check if prompt specifies multiple site sections
    site_section_hints = ["menu", "about section", "contact form", "hero", "pricing", "gallery", "footer", "features", "testimonial", "bento grid", "mission profile"]
    matched_hints = sum(1 for h in site_section_hints if h in lower)
    if matched_hints >= 2 or ("section" in lower and matched_hints >= 1):
        return "site", 0.88

    # 5. Component indicators (only when prompt does not describe multiple site sections)
    comp_indicators = ["component", "button", "input", "modal", "dialog", "hook", "use", "slider", "switch", "toggle", "card", "dropdown", "navbar", "badge", "avatar"]
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
    # 0. The planner's business-name rules ("Name — description", "Name: …",
    #    "Portfolio for Name, a …") — the same name the site itself uses.
    try:
        from agent.site_brief import extract_business_name as _business_name
        planned = _business_name(prompt)
    except Exception:
        planned = ""
    if planned and planned != "My Business":
        words = [w.capitalize() if w.islower() else w for w in re.findall(r'[A-Za-z0-9]+', planned)]
        if words:
            return "_".join(words)[:64]

    # 1. Quoted name after 'for' / 'called' / 'named' or near start of prompt
    m = re.search(r'''(?:for|called|named)\s+["']([a-zA-Z0-9\s_-]{2,40})["']''', prompt[:200], re.I)
    if m:
        raw = m.group(1).strip()
        words = [w.capitalize() for w in re.findall(r'[a-zA-Z0-9]+', raw) if w.lower() not in {"a", "an", "the"}]
        if words and words[0].lower() not in {"feel", "design", "website", "active", "style"}:
            return "_".join(words)[:64]

    # 2. Capitalized quoted name near start of prompt (first 120 chars)
    m = re.search(r'''["']([A-Z][a-zA-Z0-9\s_-]{1,39})["']''', prompt[:120])
    if m:
        raw = m.group(1).strip()
        words = [w.capitalize() for w in re.findall(r'[a-zA-Z0-9]+', raw) if w.lower() not in {"a", "an", "the"}]
        if words and words[0].lower() not in {"feel", "design", "website", "active", "style"}:
            return "_".join(words)[:64]

    # 3. Explicit 'for <Name>' or 'called <Name>' (unquoted or quoted with trailing boundary)
    m = re.search(
        r'''(?:for|called|named)\s+["']?([A-Za-z0-9&][a-zA-Z0-9&\s_-]{0,39}?)(?:["']?(?:$|,|\.|\s+(?:with|using|and|in|featuring|showcasing|show\s+casing|an?\b)))''',
        prompt[:200],
        re.I
    )
    if m:
        raw = m.group(1).strip()
        words = [w.capitalize() for w in re.split(r'\s+', raw) if w.lower() not in {"a", "an", "the", "me", "active", "inactive"}]
        if words:
            return "_".join(words)[:64]

    # 4. Domain keyword fallback (e.g. restaurant, cafe, coffee, bakery, portfolio, dashboard)
    domain_match = re.search(r'\b(restaurant|cafe|coffee|bakery|bar|salon|spa|agency|hotel|fitness|gym|clinic|portfolio|storefront|shop|saas|blog|dashboard)\b', prompt, re.I)
    if domain_match:
        return f"{domain_match.group(1).capitalize()}_Site"

    # 5. Sequence of TitleCase words near start (not stop words)
    STOP = {
        "Write", "Create", "Build", "Make", "Design", "Generate", "Develop",
        "A", "An", "The", "My", "Our", "New", "React", "TypeScript", "Website",
        "Page", "Site", "Landing", "Full", "Complete", "Modern", "Beautiful",
        "Active", "Inactive", "Style", "Reference",
    }
    words = re.findall(r'\b[A-Z][a-zA-Z0-9]+\b', prompt[:120])
    candidates = [w for w in words if w not in STOP]
    if candidates:
        return "_".join(candidates[:2])

    return "Website_Site"

    return "MySite"

# ── Project Dispatch & Queued Prompts ──────────────────────────────────────────

_project_queued_prompts: Dict[str, List[Dict[str, Any]]] = {}

def _dispatch_task_start(
    project_id: str,
    prompt: str,
    mode: Optional[str] = None,
    options: Optional[Dict[str, Any]] = None,
    task_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Blueprint transport: client -> task.start
    Dispatches generation or edit turn for project_id, registering the TaskEventEmitter.
    """
    options = options or {}
    now = time.time()
    task_id = task_id or str(uuid.uuid4())
    prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    _recent_requests[prompt_hash] = (task_id, now)

    s = session_manager.get_session(project_id)
    if s:
        q = TaskEventEmitter(task_id, project_id=s.session_id)
        _register_task_queue(task_id, q)
        # Dynamic Output Token Budget for follow-up task
        if options.get("max_tokens") is not None:
            allocated_tokens = int(options["max_tokens"])
            budget_dict = {"tier": "custom", "allocated_tokens": allocated_tokens}
        else:
            factors = extract_complexity_factors(
                prompt=prompt,
                task_mode=s.mode,
                target_symbol=s.title,
            )
            budget = estimate_output_budget(factors)
            allocated_tokens = budget.clamped_tokens
            budget_dict = budget.to_dict()

        task_data = {
            "task_id": task_id,
            "session_id": s.session_id,
            "is_follow_up": True,
            "mode": s.mode,
            "prompt": prompt,
            "symbol": s.title,
            "max_tokens": allocated_tokens,
            "token_budget": budget_dict,
        }
        _generation_queue.put(task_data)
        event_bus.publish(
            task_id,
            AgentEvent(
                type="task.queued",
                task_id=task_id,
                project_id=s.session_id,
                data={
                    "taskId": task_id,
                    "task_id": task_id,
                    "project_id": s.session_id,
                    "prompt": prompt,
                    "queue_position": _generation_queue.qsize(),
                    "position": _generation_queue.qsize(),
                    "status": "queued",
                    "is_follow_up": True,
                },
            ),
            project_id=s.session_id,
        )
        return {
            "taskId": task_id,
            "task_id": task_id,
            "session_id": s.session_id,
            "queue_position": _generation_queue.qsize(),
            "position": _generation_queue.qsize(),
            "status": "queued",
            "is_follow_up": True,
        }
    else:
        # Create new project session if non-existent
        s_mode = (mode or "site").lower()
        title_raw = options.get("symbol") or (_extract_project_name(prompt) if s_mode == "site" else _extract_component_name(prompt))
        title = _sanitize_identifier(title_raw or ("MySite" if s_mode == "site" else "Component"))
        style_tokens = options.get("styleTokens") or options.get("style_tokens")
        style_preset = options.get("stylePreset") or options.get("style_preset")
        s = session_manager.create_session(
            title=title,
            mode=s_mode,
            prompt=prompt,
            style_tokens=style_tokens,
            style_preset=style_preset,
        )
        q = TaskEventEmitter(task_id, project_id=s.session_id)
        _register_task_queue(task_id, q)

        # Dynamic Output Token Budget for new session task
        if options.get("max_tokens") is not None:
            allocated_tokens = int(options["max_tokens"])
            budget_dict = {"tier": "custom", "allocated_tokens": allocated_tokens}
        else:
            factors = extract_complexity_factors(
                prompt=prompt,
                task_mode=s_mode,
                target_symbol=title,
            )
            budget = estimate_output_budget(factors)
            allocated_tokens = budget.clamped_tokens
            budget_dict = budget.to_dict()

        task_data = {
            "task_id": task_id,
            "session_id": s.session_id,
            "mode": s_mode,
            "prompt": prompt,
            "symbol": title,
            "max_turns": int(options.get("max_turns", 10 if s_mode == "site" else 5)),
            "max_tokens": allocated_tokens,
            "token_budget": budget_dict,
        }
        if s_mode == "site":
            task_data["style_tokens"] = style_tokens
            task_data["style_preset"] = style_preset
            task_data["stylePreset"] = style_preset
        else:
            test_code = (options.get("test_code") or "").strip()
            task_data["test_code"] = test_code or _auto_test(title, title.startswith("use"))

        _generation_queue.put(task_data)
        event_bus.publish(
            task_id,
            AgentEvent(
                type="task.queued",
                task_id=task_id,
                project_id=s.session_id,
                data={
                    "taskId": task_id,
                    "task_id": task_id,
                    "project_id": s.session_id,
                    "prompt": prompt,
                    "queue_position": _generation_queue.qsize(),
                    "position": _generation_queue.qsize(),
                    "status": "queued",
                    "mode": s_mode,
                },
            ),
            project_id=s.session_id,
        )
        return {
            "taskId": task_id,
            "task_id": task_id,
            "session_id": s.session_id,
            "queue_position": _generation_queue.qsize(),
            "position": _generation_queue.qsize(),
            "status": "queued",
            "mode": s_mode,
        }

def _dispatch_task_cancel(project_id: str, reason: str = "user_cancelled") -> Dict[str, Any]:
    """
    Blueprint transport: client -> task.cancel
    Cancels any active or pending task associated with project_id.
    """
    cancelled_ids = []
    # 1. Check current task
    if _current_task and _current_task.get("session_id") == project_id:
        tid = _current_task.get("task_id")
        if tid:
            cancelled_tasks.add(tid)
            cancelled_ids.append(tid)
            q = task_queues.get(tid)
            if q:
                try:
                    q.put({"type": "cancelled", "text": f"Task cancelled: {reason}", "cancelled": True})
                    q.put({"type": "done"})
                except Exception:
                    pass

    # 2. Check pending tasks in _generation_queue
    with _generation_queue.mutex:
        for item in list(_generation_queue.queue):
            if isinstance(item, dict) and item.get("session_id") == project_id:
                tid = item.get("task_id")
                if tid:
                    cancelled_tasks.add(tid)
                    cancelled_ids.append(tid)
                    q = task_queues.get(tid)
                    if q:
                        try:
                            q.put({"type": "cancelled", "text": f"Task cancelled: {reason}", "cancelled": True})
                            q.put({"type": "done"})
                        except Exception:
                            pass

    # Clear queued prompts on cancel
    if project_id in _project_queued_prompts:
        _project_queued_prompts[project_id].clear()
    s = session_manager.get_session(project_id)
    if s:
        s.queued_prompts = []
        s.save()

    event_bus.publish(
        project_id,
        AgentEvent(
            type=AgentEventType.TASK_FAILED,
            project_id=project_id,
            data={
                "cancelled": True,
                "reason": reason,
                "cancelled_tasks": cancelled_ids,
                "text": f"Task cancelled: {reason}",
            },
        ),
        project_id=project_id,
    )
    return {"status": "cancelled", "project_id": project_id, "cancelled_tasks": cancelled_ids}

def _dispatch_prompt_queue(
    project_id: str,
    prompt: str,
    options: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Blueprint transport: client -> prompt.queue
    Queues a follow-up prompt to run automatically after current turn completes.
    """
    task_id = f"task_{int(time.time())}_{uuid.uuid4().hex[:6]}"
    queue_list = _project_queued_prompts.setdefault(project_id, [])
    depth = len(queue_list) + 1
    item = {
        "task_id": task_id,
        "taskId": task_id,
        "prompt": prompt,
        "options": options or {},
        "position": depth,
        "status": "queued",
        "timestamp": time.time(),
    }
    queue_list.append(item)

    s = session_manager.get_session(project_id)
    if s:
        s.queued_prompts = [
            {
                "taskId": q.get("taskId") or q.get("task_id"),
                "task_id": q.get("taskId") or q.get("task_id"),
                "prompt": q["prompt"],
                "position": idx + 1,
                "status": "queued",
            }
            if isinstance(q, dict) else {"prompt": q, "position": idx + 1, "status": "queued"}
            for idx, q in enumerate(queue_list)
        ]
        s.save()

    event_bus.publish(
        project_id,
        AgentEvent(
            type=AgentEventType.ACTIVITY_STARTED,
            task_id=task_id,
            project_id=project_id,
            data={
                "activity": f"Queued prompt: {prompt}",
                "taskId": task_id,
                "task_id": task_id,
                "status": "queued",
                "position": depth,
                "queue_position": depth,
                "prompt": prompt,
                "queue_depth": depth,
                "queued": True,
            },
        ),
        project_id=project_id,
    )
    return {
        "type": "prompt.queued",
        "taskId": task_id,
        "task_id": task_id,
        "status": "queued",
        "position": depth,
        "queue_position": depth,
        "project_id": project_id,
        "queue_depth": depth,
    }

def _dispatch_preview_selection(
    project_id: str,
    selection: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Blueprint transport: client -> preview.selection
    Captures element/3D selection from live preview to guide targeted edits.
    """
    s = session_manager.get_session(project_id)
    if s:
        s.preview_selection = selection
        s.save()
    label = selection.get("component") or selection.get("selector") or selection.get("elementId") or "element"
    event_bus.publish(
        project_id,
        AgentEvent(
            type=AgentEventType.ACTIVITY_UPDATED,
            project_id=project_id,
            data={
                "activity": f"Selected {label} in preview",
                "selection": selection,
                "step": f"Targeting {label}",
            },
        ),
        project_id=project_id,
    )
    return {"status": "selection_updated", "project_id": project_id, "selection": selection}

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

        registry = globals().get("task_registry")
        try:
            if registry:
                try:
                    registry.transition(task_id, TaskState.RUNNING)
                except ValueError:
                    pass
            _model_status = "busy"
            _current_task = task
            pid = task.get("session_id") or task.get("project_id")
            if pid and "event_bus" in globals():
                event_bus.bind_task_to_project(task_id, pid)
                event_bus.publish(
                    task_id,
                    AgentEvent(
                        type="task.started",
                        task_id=task_id,
                        project_id=pid,
                        data={
                            "taskId": task_id,
                            "task_id": task_id,
                            "status": "started",
                            "project_id": pid,
                            "mode": task.get("mode", "component"),
                            "prompt": task.get("prompt", ""),
                        },
                    ),
                    project_id=pid,
                )
            if q:
                try:
                    q.put({
                        "type": "task.started",
                        "taskId": task_id,
                        "task_id": task_id,
                        "status": "started",
                        "project_id": pid,
                        "mode": task.get("mode", "component"),
                    })
                except Exception:
                    pass

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
                        import traceback
                        traceback.print_exc()
                        task_err.append(err)

                worker_t = threading.Thread(target=_run_target, daemon=True)
                worker_t.start()
                max_turns_est = task.get("max_turns", 14)
                timeout_s = max(2400.0, max_turns_est * 200.0)  # 40-minute guard for multi-turn site pipelines
                worker_t.join(timeout=timeout_s)

                if worker_t.is_alive():
                    cancelled_tasks.add(task_id)
                    if hasattr(_runner, "stop_check"):
                        _runner.stop_check = lambda: True
                    # A Python thread is not a kill boundary. Never block the
                    # serialized supervisor on a non-cooperative CUDA/native
                    # call; the daemon thread is abandoned and the task fails.
                    if registry:
                        worker_t.join(timeout=2.0)
                    else:
                        worker_t.join()
                    raise TimeoutError(f"Task {task_id} timed out after {int(timeout_s)} seconds.")
                if task_err:
                    raise task_err[0]
        except Exception as e:
            import traceback
            traceback.print_exc()
            # Recording the failure must never stop the supervisor: if it raises,
            # the queue would stall and every later task would hang.
            try:
                _store_task_failure(task, e)
            except Exception as store_err:
                print(f"[Worker] Could not record failure for {task_id}: {store_err}")
            if q:
                q.put({"type": "error", "text": str(e)})
                q.put({"type": "done"})
            if registry:
                try:
                    registry.transition(task_id, TaskState.FAILED, str(e))
                except ValueError:
                    pass
        finally:
            _current_task = None
            _model_status = "ready"
            if hasattr(_runner, "stop_check"):
                _runner.stop_check = None
            cancelled_tasks.discard(task_id)
            if registry and registry.get(task_id) and registry.get(task_id).state == TaskState.RUNNING:
                try:
                    outcome = _get_task_result(task_id)
                    if isinstance(outcome, dict) and outcome.get("status") in {"blocked", "failed"}:
                        registry.transition(task_id, TaskState.FAILED, outcome.get("summary"))
                    else:
                        registry.transition(task_id, TaskState.SUCCEEDED)
                except ValueError:
                    pass
            _generation_queue.task_done()

            # Blueprint: Check if there are queued prompts for this project
            proj_id = task.get("session_id")
            if proj_id and _project_queued_prompts.get(proj_id):
                next_item = _project_queued_prompts[proj_id].pop(0)
                s = session_manager.get_session(proj_id)
                if s:
                    s.queued_prompts = [
                        {
                            "taskId": q.get("taskId") or q.get("task_id"),
                            "task_id": q.get("taskId") or q.get("task_id"),
                            "prompt": q["prompt"],
                            "position": idx + 1,
                            "status": "queued",
                        }
                        if isinstance(q, dict) else {"prompt": q, "position": idx + 1, "status": "queued"}
                        for idx, q in enumerate(_project_queued_prompts[proj_id])
                    ]
                    s.save()
                try:
                    next_tid = next_item.get("taskId") or next_item.get("task_id")
                    print(f"[Worker] Auto-dequeuing next prompt for project {proj_id}: {next_item['prompt'][:40]}")
                    _dispatch_task_start(proj_id, next_item["prompt"], options=next_item.get("options"), task_id=next_tid)
                except Exception as _q_err:
                    print(f"[Worker] Failed to auto-dispatch queued prompt for {proj_id}: {_q_err}")

# The worker thread starts at the end of the module, once every function it calls exists (B6).


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


def repair_missing_critical_files(workspace_dir: Path, title: str, mode: str = "site") -> List[str]:
    """
    Blueprint lifecycle: repairs only missing critical runner files.
    Never overwrites or resets existing project files or developer customizations.
    Returns list of repaired file names.
    """
    workspace_dir = Path(workspace_dir).resolve()
    repaired: List[str] = []

    # 1. node_modules junction
    nm = workspace_dir / "node_modules"
    root_nm = BASE_DIR / "node_modules"
    if not nm.exists() and root_nm.exists():
        _link_node_modules(nm, root_nm)
        repaired.append("node_modules")

    # 2. package.json
    pkg_path = workspace_dir / "package.json"
    if not pkg_path.exists():
        pkg = {
            "name": f"{title.lower()}-project",
            "private": True,
            "version": "1.0.0",
            "type": "module",
            "scripts": {
                "dev": "vite",
                "typecheck": "tsc --noEmit",
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
        pkg_path.write_text(json.dumps(pkg, indent=2), encoding="utf-8")
        repaired.append("package.json")

    # 3. vite.config.ts
    vite_cfg = workspace_dir / "vite.config.ts"
    if not vite_cfg.exists():
        cfg_content = """import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  define: {
    'process.env': {},
  },
  server: {
    strictPort: true,
    host: '127.0.0.1',
    open: false,
  },
});
"""
        vite_cfg.write_text(cfg_content, encoding="utf-8")
        repaired.append("vite.config.ts")

    # 4. tsconfig.json
    tsconfig = workspace_dir / "tsconfig.json"
    if not tsconfig.exists():
        ts_cfg = {
            "compilerOptions": {
                "target": "ES2022",
                "lib": ["ES2022", "DOM"],
                "jsx": "react-jsx",
                "module": "ESNext",
                "moduleResolution": "bundler",
                "strict": True,
                "esModuleInterop": True,
                "skipLibCheck": True,
                "allowImportingTsExtensions": True,
                "noEmit": True
            },
            "include": ["**/*.ts", "**/*.tsx"]
        }
        tsconfig.write_text(json.dumps(ts_cfg, indent=2), encoding="utf-8")
        repaired.append("tsconfig.json")

    # 5. src/vite-env.d.ts
    vite_env = workspace_dir / "src" / "vite-env.d.ts"
    if not vite_env.exists():
        vite_env.parent.mkdir(parents=True, exist_ok=True)
        vite_env.write_text("""/// <reference types="vite/client" />

declare module '*.module.css' {
  const classes: { readonly [key: string]: string };
  export default classes;
}

declare module '*.css' {
  const content: any;
  export default content;
}
""", encoding="utf-8")
        repaired.append("src/vite-env.d.ts")

    # 6. index.html
    index_html = workspace_dir / "index.html"
    if not index_html.exists():
        safe_title = html.escape(title)
        html_content = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{safe_title}</title>
  </head>
  <body style="margin: 0; background: #0b0f19; color: #f0f0f8; font-family: system-ui, sans-serif;">
    <div id="root"></div>
    <script type="module" src="/main.tsx"></script>
  </body>
</html>
"""
        index_html.write_text(html_content, encoding="utf-8")
        repaired.append("index.html")

    # 7. main.tsx
    main_tsx = workspace_dir / "main.tsx"
    if not main_tsx.exists():
        target_entry = "App" if (mode == "site" or (workspace_dir / "App.tsx").exists()) else title
        main_content = f"""import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './{target_entry}';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
"""
        main_tsx.write_text(main_content, encoding="utf-8")
        repaired.append("main.tsx")

    # 8. App.tsx (for site mode, only if missing)
    if mode == "site":
        app_tsx = workspace_dir / "App.tsx"
        if not app_tsx.exists():
            app_content = f"""import React from 'react';

export default function App() {{
  return (
    <div className="site-root" style={{{{ padding: '2rem', fontFamily: 'system-ui, sans-serif' }}}}>
      <h1>{html.escape(title)}</h1>
      <p>Site initialized.</p>
    </div>
  );
}}
"""
            app_tsx.write_text(app_content, encoding="utf-8")
            repaired.append("App.tsx")
    else:
        comp_tsx = workspace_dir / f"{title}.tsx"
        if not comp_tsx.exists() and not (workspace_dir / "App.tsx").exists():
            comp_content = f"""import React from 'react';

export default function {title}() {{
  return (
    <div style={{{{ padding: '2rem', fontFamily: 'system-ui, sans-serif' }}}}>
      <h2>{html.escape(title)}</h2>
    </div>
  );
}}
"""
            comp_tsx.write_text(comp_content, encoding="utf-8")
            repaired.append(f"{title}.tsx")

    # 9. App.css (only if missing and no component css)
    app_css = workspace_dir / "App.css"
    if not app_css.exists() and not (workspace_dir / f"{title}.css").exists() and not (workspace_dir / f"{title}.module.css").exists():
        app_css.write_text("/* Default styles */\n:root { font-family: system-ui, sans-serif; }\n", encoding="utf-8")
        repaired.append("App.css")

    return repaired


def explicit_framework_change(
    workspace_dir: Path,
    action: str,
    payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Blueprint lifecycle: explicitFrameworkChange() -> alter project config.
    Applies explicit project configuration modifications such as:
    - Dependency management: "install_package", "remove_package"
    - Vite configuration: "add_vite_alias", "set_vite_config"
    - TypeScript configuration: "set_tsconfig_paths", "set_compiler_options"
    - CSS / Tailwind setup: "setup_tailwind"
    Never blindly overwrites unaffected settings or other files.
    """
    workspace_dir = Path(workspace_dir).resolve()
    payload = payload or {}
    changes_made: List[str] = []

    if action == "install_package":
        dm = DependencyManager(workspace_dir)
        pkg = payload.get("package")
        version = payload.get("version")
        is_dev = payload.get("dev", False)
        if not pkg:
            raise ValueError("Package name required for install_package")
        res = dm.install_package(pkg, version=version, is_dev=is_dev)
        if not res.get("success"):
            raise RuntimeError(res.get("output") or "Install failed")
        changes_made.append(f"Installed {pkg}: {res.get('version')}")

    elif action == "remove_package":
        dm = DependencyManager(workspace_dir)
        pkg = payload.get("package")
        if not pkg:
            raise ValueError("Package name required for remove_package")
        res = dm.remove_package(pkg)
        if not res.get("success"):
            raise RuntimeError(res.get("output") or "Remove failed")
        changes_made.append(f"Removed {pkg}")

    elif action == "add_vite_alias":
        alias_name = payload.get("alias", "@")
        target = payload.get("target", "./src")
        vite_cfg = workspace_dir / "vite.config.ts"
        if vite_cfg.exists():
            cfg_text = vite_cfg.read_text(encoding="utf-8")
            if "resolve:" not in cfg_text:
                resolve_snippet = f"""  resolve: {{
    alias: {{
      '{alias_name}': path.resolve(__dirname, '{target}'),
    }},
  }},
"""
                if "import path from 'path';" not in cfg_text and 'import path from "path";' not in cfg_text:
                    cfg_text = "import path from 'path';\n" + cfg_text
                if "defineConfig({" in cfg_text:
                    cfg_text = cfg_text.replace("defineConfig({", f"defineConfig({{\n{resolve_snippet}", 1)
                    vite_cfg.write_text(cfg_text, encoding="utf-8")
                    changes_made.append(f"Added Vite alias '{alias_name}' -> '{target}'")
            else:
                changes_made.append(f"Vite resolve block already present")

    elif action == "set_tsconfig_paths":
        tsconfig = workspace_dir / "tsconfig.json"
        paths = payload.get("paths", {"@/*": ["./src/*"]})
        if tsconfig.exists():
            try:
                data = json.loads(tsconfig.read_text(encoding="utf-8"))
            except Exception:
                data = {}
            comp_opts = data.setdefault("compilerOptions", {})
            comp_opts["baseUrl"] = payload.get("baseUrl", ".")
            comp_opts.setdefault("paths", {}).update(paths)
            tsconfig.write_text(json.dumps(data, indent=2), encoding="utf-8")
            changes_made.append(f"Updated tsconfig paths: {list(paths.keys())}")

    elif action == "setup_tailwind":
        css_file = workspace_dir / "App.css"
        if not css_file.exists():
            css_file = workspace_dir / "src" / "index.css"
        if css_file.exists():
            content = css_file.read_text(encoding="utf-8")
            if "@tailwind" not in content and '@import "tailwindcss"' not in content:
                tw_header = '@import "tailwindcss";\n\n'
                css_file.write_text(tw_header + content, encoding="utf-8")
                changes_made.append(f"Added Tailwind directives to {css_file.name}")
        else:
            (workspace_dir / "App.css").write_text('@import "tailwindcss";\n', encoding="utf-8")
            changes_made.append("Created App.css with Tailwind directive")

    else:
        raise ValueError(f"Unknown framework change action: {action!r}")

    return {
        "action": action,
        "changes": changes_made,
        "success": True,
    }


def _scaffold_vite_runner(target_dir: Path, symbol: str):
    """Generates package.json, vite.config.ts, index.html, static-preview.html, and main.tsx for component preview."""
    _link_node_modules(BASE_DIR / "generated_components" / "node_modules", BASE_DIR / "node_modules")
    _link_node_modules(target_dir / "node_modules", BASE_DIR / "node_modules")
    try:
        pkg = {
            "name": f"{symbol.lower()}-preview",
            "private": True,
            "version": "1.0.0",
            "type": "module",
            "scripts": {
                "dev": "vite",
                "typecheck": "tsc --noEmit",
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
        pkg_path = target_dir / "package.json"
        if pkg_path.exists():
            existing_pkg = json.loads(pkg_path.read_text(encoding="utf-8"))
            for key in ("dependencies", "devDependencies", "scripts"):
                pkg[key].update(existing_pkg.get(key, {}))
            for key, value in existing_pkg.items():
                if key not in pkg:
                    pkg[key] = value
        pkg_path.write_text(json.dumps(pkg, indent=2), encoding="utf-8")

        vite_cfg = """import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  define: {
    'process.env': {},
  },
  server: {
    strictPort: true,
    host: '127.0.0.1',
    open: false,
  },
});
"""
        (target_dir / "vite.config.ts").write_text(vite_cfg, encoding="utf-8")

        safe_symbol = html.escape(symbol)
        index_html = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{safe_symbol} Component Preview</title>
  </head>
  <body style="margin: 0; background: #0e0e1a; color: #f0f0f8; font-family: system-ui, sans-serif;">
    <div id="root"></div>
    <script type="module" src="/main.tsx"></script>
  </body>
</html>
"""
        (target_dir / "index.html").write_text(index_html, encoding="utf-8")

        # Determine component import name and check for companion CSS
        if (target_dir / f"{symbol}.tsx").exists():
            mod_name = symbol
        elif (target_dir / "App.tsx").exists():
            mod_name = "App"
        elif (target_dir / "Component.tsx").exists():
            mod_name = "Component"
        else:
            cands = [p.stem for p in target_dir.glob("*.tsx") if p.stem != "main"]
            mod_name = cands[0] if cands else "Component"
        css_import = ""
        for css_cand in [f"{symbol}.module.css", f"{symbol}.css", "Component.module.css", "Component.css", "styles.css"]:
            if (target_dir / css_cand).exists():
                css_import = f"import './{css_cand}';\n"
                break

        main_tsx = f"""import React from 'react';
import ReactDOM from 'react-dom/client';
{css_import}import * as Mod from './{mod_name}';

const Comp: any = (Mod as any).{symbol} || (Mod as any).Component || (Mod as any).default || Object.values(Mod).find(v => typeof v === 'function') || (() => React.createElement('div', null, 'No component found'));

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <div style={{{{ padding: 24, maxWidth: 1200, margin: '0 auto', display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '80vh' }}}}>
      <Comp />
    </div>
  </React.StrictMode>
);
"""
        (target_dir / "main.tsx").write_text(main_tsx, encoding="utf-8")

        # Static preview HTML & bundle
        static_html = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{safe_symbol} Component Preview</title>
    <link rel="stylesheet" href="./preview.css" />
  </head>
  <body style="margin: 0; background: #0e0e1a; color: #f0f0f8; font-family: system-ui, sans-serif;">
    <div id="root"></div>
    <script src="./preview.js"></script>
  </body>
</html>
"""
        (target_dir / "static-preview.html").write_text(static_html, encoding="utf-8")

        # Bundle for static preview
        try:
            subprocess.run([
                "npx", "esbuild", str(target_dir / "main.tsx"),
                "--bundle", f"--outfile={target_dir / 'preview.js'}",
                "--jsx=automatic", "--loader:.tsx=tsx", "--loader:.ts=ts",
                "--loader:.css=copy", "--sourcemap=inline"
            ], cwd=str(BASE_DIR), check=True, capture_output=True, text=True)
        except Exception:
            (target_dir / "static-preview.html").write_text(
                "<!doctype html><html><head><title>Preview unavailable</title></head><body><p>Preview unavailable</p></body></html>",
                encoding="utf-8"
            )

        # Write tsconfig.json for the project
        tsconfig = {
            "compilerOptions": {
                "target": "ES2022", "lib": ["ES2022", "DOM"],
                "jsx": "react-jsx", "module": "ESNext",
                "moduleResolution": "bundler", "strict": True,
                "esModuleInterop": True, "skipLibCheck": True,
                "allowImportingTsExtensions": True, "noEmit": True
            },
            "include": ["**/*.ts", "**/*.tsx"]
        }
        (target_dir / "tsconfig.json").write_text(json.dumps(tsconfig, indent=2), encoding="utf-8")

    except Exception as e:
        print(f"[Server] Note: could not scaffold Vite preview: {e}")


from agent.agent import CODE_SAMPLING  # noqa: E402  (explicit sampling for code-writing turns)


def _scaffold_site_vite_runner(target_dir: Path, project_name: str, files: dict[str, str], brief: dict = None, q: Any = None):
    """
    Scaffolds a runnable Vite environment for the multi-file site output.
    Wires App.tsx with robust component export resolution, stem dedup, and HTML escaping.
    """
    try:
        from agent.tailwind_support import site_uses_tailwind
        tailwind_enabled = site_uses_tailwind(files)
        pkg = {
            "name": re.sub(r'[^a-z0-9-]', '-', project_name.lower()).strip('-') + "-site",
            "private": True,
            "version": "1.0.0",
            "type": "module",
            "scripts": {
                "dev": "vite",
                "typecheck": "tsc --noEmit",
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
        if tailwind_enabled:
            pkg["devDependencies"].update({
                "tailwindcss": "^4.3.3",
                "@tailwindcss/vite": "^4.3.3",
            })
        from agent.dependency_manager import reconcile_manifest_imports

        pkg_path = target_dir / "package.json"
        if pkg_path.exists():
            existing_pkg = json.loads(pkg_path.read_text(encoding="utf-8"))
            for key in ("dependencies", "devDependencies", "scripts"):
                pkg[key].update(existing_pkg.get(key, {}))
            for key, value in existing_pkg.items():
                if key not in pkg:
                    pkg[key] = value
        import_errors = reconcile_manifest_imports(pkg, files)
        if import_errors and q:
            for error in import_errors:
                q.put({"type": "log", "text": f"[Dependencies] {error}"})
        pkg_path.write_text(json.dumps(pkg, indent=2), encoding="utf-8")

        tailwind_import = "import tailwindcss from '@tailwindcss/vite';\n" if tailwind_enabled else ""
        tailwind_plugin = ", tailwindcss()" if tailwind_enabled else ""
        vite_cfg = f"""import {{ defineConfig }} from 'vite';
import react from '@vitejs/plugin-react';
{tailwind_import}

export default defineConfig({{
  plugins: [react(){tailwind_plugin}],
  define: {{
    'process.env': {{}},
  }},
  server: {{
    strictPort: true,
    host: '127.0.0.1',
    open: false,
  }},
}});
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
            # Guard against invalid JavaScript identifiers (e.g. starting with digits)
            if not comp_name or not (comp_name[0].isalpha() or comp_name[0] == '_'):
                comp_name = f"Sec_{comp_name}"
            comp_name = re.sub(r'[^a-zA-Z0-9_$]', '_', comp_name)

            # P2-4: Guard against stem collisions
            count = 1
            base_comp = comp_name
            while comp_name in seen_stems:
                count += 1
                comp_name = f"{base_comp}_{count}"
            seen_stems.add(comp_name)
            component_names.append(comp_name)

            file_content = files.get(tsx_path, "")
            # P0-3: Inspect component exports to avoid silent null renders
            named_export_m = re.search(r'export\s+(?:function|const)\s+([A-Z]\w*)', file_content)
            alt_name = named_export_m.group(1) if named_export_m else None

            mod_var = f"_{comp_name}Mod"
            clean_import = tsx_path[:-4] if tsx_path.endswith(".tsx") else tsx_path
            import_lines.append(f"import * as {mod_var} from './{clean_import}';")

            # A section without a usable export renders nothing in the customer
            # site; the problem is reported to the developer console only.
            fallback_jsx = (
                f"(() => {{ console.warn('Section {raw_comp} is missing a React export and was skipped.'); return null; }})"
            )

            if alt_name and alt_name != raw_comp:
                import_lines.append(
                    f"const {comp_name} = ({mod_var} as any)['{raw_comp}'] || ({mod_var} as any)['{alt_name}'] || ({mod_var} as any).default || {fallback_jsx};"
                )
            else:
                import_lines.append(
                    f"const {comp_name} = ({mod_var} as any)['{raw_comp}'] || ({mod_var} as any).default || {fallback_jsx};"
                )

        # Collect header, footer, and main sections
        headers = []
        footers = []
        mains = []
        for n in component_names:
            nl = n.lower()
            if "header" in nl or "navbar" in nl or "masthead" in nl or nl in {"nav", "navigation"}:
                headers.append(n)
            elif "footer" in nl:
                footers.append(n)
            else:
                mains.append(n)

        header_tags = "\n      ".join([f"<{n} />" for n in headers])
        main_tags = "\n      ".join([f"<{n} />" for n in mains])
        footer_tags = "\n      ".join([f"<{n} />" for n in footers])

        app_body_parts = ['<a className="site-skip-link" href="#site-main">Skip to content</a>']
        if header_tags:
            app_body_parts.append(header_tags)
        has_generated_h1 = any(
            re.search(r"<h1\b", source, re.I)
            for path, source in files.items()
            if path.startswith("src/components/") and path.endswith((".tsx", ".jsx"))
        )
        landmark_h1 = "" if has_generated_h1 else f'<h1 className="site-visually-hidden">{html.escape(project_name)}</h1>\n      '
        app_body_parts.append(f'<main id="site-main" tabIndex={{-1}}>\n      {landmark_h1}{main_tags or "<div>No sections</div>"}\n      </main>')
        if footer_tags:
            app_body_parts.append(footer_tags)

        app_tsx_render = "\n      ".join(app_body_parts)
        app_tsx_imports = "\n".join(import_lines)

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

        kit_base_css = (brief or {}).get("kit_base_css")
        if kit_base_css:
            root_css = ""
        else:
            from style_ingest import build_site_root_css
            root_css, _ = build_site_root_css(brief=brief)

        tailwind_theme = ""
        if tailwind_enabled:
            def theme_color(names: tuple[str, ...], fallback: str) -> str:
                for name in names:
                    match = re.search(rf'--{re.escape(name)}\s*:\s*(#[0-9a-fA-F]{{3,8}})\b', root_css)
                    if match:
                        return match.group(1)
                return fallback

            primary_theme = theme_color(("color-primary", "primary-color"), "#2563eb")
            accent_theme = theme_color(("color-accent", "accent-color"), "#38bdf8")
            tailwind_theme = (
                '@import "tailwindcss";\n'
                f'@theme {{ --color-primary: {primary_theme}; --color-accent: {accent_theme}; }}\n\n'
            )
        if kit_base_css:
            # The kit stylesheet carries its own tokens and reset (no global
            # zero-padding, no black default background).
            full_app_css = tailwind_theme + kit_base_css
        else:
            full_app_css = (
            tailwind_theme +
            f"{root_css}\n\n"
            "*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }\n"
            "html { font-family: var(--font-body, system-ui, sans-serif); }\n"
            "body { margin: 0; font-family: var(--font-body, system-ui, sans-serif); background-color: var(--bg-color, #000000); color: var(--text-color, #ffffff); -webkit-font-smoothing: antialiased; }\n"
            ".site-root { display: flex; flex-direction: column; min-height: 100vh; }\n"
            ".site-skip-link { position: fixed; top: -100px; left: 16px; z-index: 99999; padding: 12px; background: var(--bg-color, #000); color: var(--text-color, #fff); }\n"
            ".site-skip-link:focus { top: 12px; }\n"
            ".site-visually-hidden { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0, 0, 0, 0); white-space: nowrap; border: 0; }\n"
        )
        app_css_path.write_text(full_app_css, encoding="utf-8")

        # P0-4: HTML-escape project name and description to prevent stored HTML injection
        safe_project_name = html.escape((brief or {}).get("kit_title") or project_name.replace('_', ' '))
        display_name = project_name.replace('_', ' ')
        tagline = str((brief or {}).get("description") or (brief or {}).get("tagline") or "").strip()
        meta_desc = tagline if tagline and tagline.lower() != display_name.lower() else display_name
        safe_meta_desc = html.escape(meta_desc)

        kit_font_href = (brief or {}).get("kit_font_href")
        if kit_font_href:
            font_href = html.escape(kit_font_href)
        else:
            font_h = (brief.get("font_heading") if brief else None) or "Inter"
            font_b = (brief.get("font_body") if brief else None) or "Inter"
            fonts_set = {font_h, font_b}
            font_links = "&".join([f"family={urllib.parse.quote_plus(f)}:wght@400;500;600;700;800" for f in sorted(fonts_set)])
            font_href = f"https://fonts.googleapis.com/css2?{font_links}&amp;display=swap"
        kit_head = (brief or {}).get("kit_head_tags") or ""
        description_tag = "" if 'name="description"' in kit_head else f'<meta name="description" content="{safe_meta_desc}" />\n    '
        head_extra = (kit_head + "\n    ") if kit_head else ""
        icon_css = "" if kit_base_css else (
            '<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css" '
            'integrity="sha512-DTOQO9RWCH3ppGqcWaEA1BIZOC6xxalwEsw9c2QQeAIftl+Vegovlnee1c9QX4TctnWMn13TZye+giMm8e2LwA==" '
            'crossorigin="anonymous" referrerpolicy="no-referrer" />\n    ')
        for public_rel, public_data in ((brief or {}).get("kit_public_files") or []):
            public_dest = target_dir / "public" / public_rel
            public_dest.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(public_data, (bytes, bytearray)):
                public_dest.write_bytes(bytes(public_data))
            else:
                public_dest.write_text(str(public_data), encoding="utf-8")

        index_html = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    {description_tag}<title>{safe_project_name}</title>
    {head_extra}<link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="{font_href}" rel="stylesheet" />
    {icon_css}  </head>
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

        static_html = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    {description_tag}<title>{safe_project_name}</title>
    {head_extra}<link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="{font_href}" rel="stylesheet" />
    {icon_css}    <link rel="stylesheet" href="./preview.css" />
  </head>
  <body style="margin: 0;">
    <div id="root"></div>
    <script src="./preview.js"></script>
  </body>
</html>
"""
        (target_dir / "static-preview.html").write_text(static_html, encoding="utf-8")

        # Bundle for static preview
        try:
            subprocess.run([
                "npx", "esbuild", str(target_dir / "main.tsx"),
                "--bundle", f"--outfile={target_dir / 'preview.js'}",
                "--jsx=automatic", "--loader:.tsx=tsx", "--loader:.ts=ts",
                "--loader:.css=copy", "--sourcemap=inline"
            ], cwd=str(BASE_DIR), check=True, capture_output=True, text=True)
        except Exception:
            (target_dir / "static-preview.html").write_text(
                "<!doctype html><html><head><title>Preview unavailable</title></head><body><p>Preview unavailable</p></body></html>",
                encoding="utf-8"
            )

        # Write tsconfig.json for the project
        tsconfig = {
            "compilerOptions": {
                "target": "ES2022", "lib": ["ES2022", "DOM"],
                "jsx": "react-jsx", "module": "ESNext",
                "moduleResolution": "bundler", "strict": True,
                "esModuleInterop": True, "skipLibCheck": True,
                "allowImportingTsExtensions": True, "noEmit": True
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


@dataclasses.dataclass
class ProjectRepairResult:
    """Structured outcome of verify_and_repair_project across compile, build, runtime, and visual gates."""
    validation: ValidationResult
    validation_after_deterministic: Optional[ValidationResult] = None
    deterministic_files: list = dataclasses.field(default_factory=list)
    files_modified: list = dataclasses.field(default_factory=list)
    diffs: dict = dataclasses.field(default_factory=dict)
    repair_attempts: int = 0
    visual_score: Optional[float] = None
    visual_score_before: Optional[float] = None
    visual_score_after: Optional[float] = None
    visual_score_best: Optional[float] = None
    visual_issues: list = dataclasses.field(default_factory=list)
    passed: bool = False
    self_corrected: bool = False
    generation_complete: bool = True
    section_completion: str = "6 / 6"
    project_validation: str = "passed"
    generation_quality: str = "native"
    interaction_validation: Optional[Any] = None
    visual_validation: Optional[Any] = None

    def __post_init__(self):
        from agent.project_validator import InteractionValidationResult, VisualValidationResult

        if self.interaction_validation is None:
            if hasattr(self.validation, "interaction_validation"):
                self.interaction_validation = self.validation.interaction_validation
            else:
                int_passed = bool(
                    self.validation
                    and getattr(self.validation, "interaction_passed", False)
                    and not any("[Interaction Error]" in str(e) for e in getattr(self.validation, "errors", []))
                )
                self.interaction_validation = InteractionValidationResult(
                    passed=int_passed,
                    status=getattr(self.validation, "interaction_status", "passed" if int_passed else "failed"),
                    errors=[str(e) for e in getattr(self.validation, "errors", []) if "[Interaction Error]" in str(e)],
                    interactions_tested=getattr(self.validation, "interactions_tested", 0),
                    interactions_required=getattr(self.validation, "interactions_required", 0),
                    interaction_evidence=getattr(self.validation, "interaction_evidence", []),
                )

        if self.visual_validation is None:
            vis_passed = bool(
                self.validation
                and self.validation.passed
                and (self.visual_score is None or self.visual_score >= 3.0)
            )
            self.visual_validation = VisualValidationResult(
                passed=vis_passed,
                status="passed" if vis_passed else "failed",
                score=self.visual_score,
                issues=list(self.visual_issues or []),
            )

        self.project_validation = "passed" if (self.validation and self.validation.passed) else "failed"

        # Authoritative 4-condition rule:
        # generation_complete and validation.passed and interaction_validation.passed and visual_validation.passed
        val_passed = bool(self.validation and self.validation.passed)
        int_passed = bool(self.interaction_validation and getattr(self.interaction_validation, "passed", False))
        vis_passed = bool(self.visual_validation and getattr(self.visual_validation, "passed", False))

        self.passed = bool(
            self.generation_complete
            and val_passed
            and int_passed
            and vis_passed
        )
        self.self_corrected = bool(self.passed and self.repair_attempts > 0)

    def __iter__(self):
        return iter((self.validation, self.files_modified, self.repair_attempts))


def verify_and_repair_project(
    workspace: Path,
    runner: Any = None,
    original_prompt: str = "",
    brief: Optional[Dict[str, Any]] = None,
    max_attempts: int = 3,
    q: Optional[queue.Queue] = None,
    session: Optional[Any] = None,
    stop_check: Optional[Callable[[], bool]] = None,
    export_dir: Optional[Path] = None,
    files_dict: Optional[Dict[str, str]] = None,
    project_name: Optional[str] = None,
    sections: Optional[List[str]] = None,
    history: Optional[List[Dict[str, str]]] = None,
    initial_files_modified: Optional[List[str]] = None,
    initial_diffs: Optional[Dict[str, Any]] = None,
    run_visual_check: bool = True,
) -> ProjectRepairResult:
    """Authoritative project verification & Qwen repair loop.

    Sequence:
      1. Full workspace verification across 7 gates (typecheck, build, lint, contract, accessibility, motion, runtime)
      2. If FAILED -> Qwen repair loop (up to max_attempts):
         - feed exact compiler/bundler/runtime diagnostics + affected file contents
         - generate minimal or complete repairs via <tool_call name="write_site">
         - write repaired files to workspace and sync to export_dir
         - re-scaffold/reconcile Vite runner and re-verify
      3. If PASSED and visual check requested:
         - evaluate visual quality via Playwright screenshot & heuristic judge
         - if visual score < 3/5, request targeted visual patch from Qwen
         - FULL REVALIDATION across all 7 gates (reverts patch if compile/runtime breaks)
      4. Returns structured ProjectRepairResult.
    """
    from agent import parse_agent_output, WriteSiteAction, sanitize_css_for_spec
    from agent.project_validator import _ensure_project_configs

    files_modified = list(initial_files_modified or [])
    diffs = dict(initial_diffs or {})
    style_spec = brief.get("style_spec") if brief else None
    active_sections = sections or (brief.get("sections") if brief else []) or []
    active_project_name = project_name or (session.title if session else "Project")
    runner_model = runner if runner is not None else _runner

    # Populate files_dict if not provided
    if files_dict is None:
        files_dict = {}
        for p in workspace.rglob("*"):
            if p.is_file() and not any(part in p.parts for part in ["node_modules", ".git", "dist", ".vite"]):
                try:
                    rel = p.relative_to(workspace).as_posix()
                    files_dict[rel] = p.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    pass

    # Initial site output, including fallback rewrites, may bypass the per-turn
    # normalizer. Apply the same narrow file-pair fixes before project gates.
    from agent.site_file_normalizer import normalize_site_section_files, remove_unresolved_section_links
    normalized_any = False
    deterministic_files: List[str] = []
    component_stems = {
        Path(path).stem for path in files_dict
        if path.startswith("src/components/") and path.endswith((".tsx", ".jsx"))
    }
    for stem in sorted(component_stems):
        pairs = [(path, content) for path, content in files_dict.items()
                 if path.startswith("src/components/") and Path(path).stem == stem
                 and path.endswith((".tsx", ".jsx", ".css"))]
        normalized_pairs = normalize_site_section_files(
            pairs, stem, original_prompt=original_prompt, known_sections=active_sections
        )
        parser_errors = preflight_section_files(normalized_pairs)
        if parser_errors:
            if q:
                q.put({"type": "log", "text": f"[Parser preflight] Kept previous section {stem}: {parser_errors}"})
            continue
        for path, content in normalized_pairs:
            if files_dict.get(path) == content:
                continue
            dest = resolve_project_path(workspace, path)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8")
            if export_dir:
                exp_dest = resolve_project_path(export_dir, path)
                exp_dest.parent.mkdir(parents=True, exist_ok=True)
                exp_dest.write_text(content, encoding="utf-8")
            files_dict[path] = content
            normalized_any = True
            if path not in deterministic_files:
                deterministic_files.append(path)
    if normalized_any:
        _scaffold_site_vite_runner(workspace, active_project_name, files_dict, brief=brief)
        if export_dir:
            _scaffold_site_vite_runner(export_dir, active_project_name, files_dict, brief=brief)

    # The final section set is known here. Remove generated links to sections
    # that do not exist instead of leaving runtime-broken navigation behind.
    for path, content in remove_unresolved_section_links(files_dict).items():
        dest = resolve_project_path(workspace, path)
        dest.write_text(content, encoding="utf-8")
        if export_dir:
            exp_dest = resolve_project_path(export_dir, path)
            exp_dest.parent.mkdir(parents=True, exist_ok=True)
            exp_dest.write_text(content, encoding="utf-8")
        files_dict[path] = content
        if path not in files_modified:
            files_modified.append(path)
        if path not in deterministic_files:
            deterministic_files.append(path)

    # When the model emits disconnected Products/Cart state, replace that pair
    # with a grounded local storefront built from products the user supplied.
    # This is recorded as a deterministic project repair, not model-native output.
    if brief and {"products", "cart"}.issubset({section.lower() for section in active_sections}):
        from agent.ecommerce_repair import build_shop_files, ground_shop_brief, shop_contract_missing
        shop_brief = ground_shop_brief(brief, original_prompt)
        if shop_brief.get("products") and shop_contract_missing(files_dict, active_sections):
            for path, source in build_shop_files(shop_brief).items():
                dest = resolve_project_path(workspace, path)
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(source, encoding="utf-8")
                if export_dir:
                    exp_dest = resolve_project_path(export_dir, path)
                    exp_dest.parent.mkdir(parents=True, exist_ok=True)
                    exp_dest.write_text(source, encoding="utf-8")
                files_dict[path] = source
                if path not in files_modified:
                    files_modified.append(path)
                if path not in deterministic_files:
                    deterministic_files.append(path)
            _scaffold_site_vite_runner(workspace, active_project_name, files_dict, brief=brief)
            if export_dir:
                _scaffold_site_vite_runner(export_dir, active_project_name, files_dict, brief=brief)
            if q:
                q.put({"type": "log", "text": "[Project Repair] Replaced disconnected shop sections with a shared cart implementation."})

    # ── Step 1: Initial Workspace Verification ────────────────────────────────
    from agent.dependency_manager import ensure_runtime_packages
    for dependency_error in ensure_runtime_packages(files_dict, BASE_DIR, event_callback=q.put if q else None):
        if q:
            q.put({"type": "log", "text": f"[Dependencies] {dependency_error}"})
    if q:
        q.put({
            "type": "command.started",
            "command": "npm run typecheck",
            "description": "Verifying workspace…",
            "status_change": "VERIFYING",
            "status": "Running TypeScript & project checks…",
            "text": "[VERIFYING] Running full workspace validation (TypeScript, build, runtime, static acceptance)…",
        })

    validation = _validate_workspace(workspace, event_callback=q.put if q else None)
    validation.repair_attempts = 0
    validation_after_deterministic = validation
    if session:
        session.last_validation = validation
        session.build_state = validation.to_dict()

    if q:
        q.put({
            "type": "build.result",
            "passed": validation.passed,
            "code_passed": validation.code_passed,
            "typecheck_passed": validation.typecheck_passed,
            "build_passed": validation.build_passed,
            "lint_passed": validation.lint_passed,
            "runtime_passed": validation.runtime_passed,
            "preview_running": validation.preview_running,
            "errors": validation.errors,
            "warnings": validation.warnings,
            "status_change": "COMPLETED" if validation.passed else "VERIFYING",
            "status": "Build passed" if validation.passed else "Fixing issues…",
            "text": f"[COMPLETED] ✓ All validations passed." if validation.passed else f"[VERIFYING] ✗ Validation failed — {len(validation.errors)} diagnostic lines.",
        })

    # ── Step 2: Qwen Repair Loop (if validation failed) ────────────────────────
    if not validation.passed and runner_model is not None and max_attempts > 0:
        if history is not None:
            active_history = history
        else:
            from agent.site_prompt import SITE_AGENT_SYSTEM_PROMPT
            active_history = [
                {"role": "system", "content": SITE_AGENT_SYSTEM_PROMPT},
                {"role": "user", "content": f"Project '{active_project_name}': {original_prompt}"}
            ]

        for attempt in range(1, max_attempts + 1):
            if stop_check and stop_check():
                break

            # Count model attempts even when the response is truncated or cannot
            # be parsed. Otherwise failed repairs are reported as zero cost.
            validation.repair_attempts = attempt

            n_errs = len(validation.errors)
            err_label = f"Fixing {n_errs} issue{'s' if n_errs != 1 else ''}…"
            if q:
                q.put({"type": "status_change", "status": "REPAIRING"})
                q.put({"type": "status", "status": f"{err_label} (attempt {attempt}/{max_attempts})…"})
                q.put({
                    "type": "log",
                    "text": (
                        f"[REPAIR REQUIRED — attempt {attempt}/{max_attempts}] Validation errors found ({n_errs} lines). "
                        f"{err_label} (attempt {attempt}/{max_attempts})…"
                    ),
                })

            from agent.repair_budget import focus_repair_errors, repair_timeout_seconds
            focused_errors = focus_repair_errors(validation.errors)
            error_block = "\n".join(focused_errors)[:4000]
            repair_note = (
                f"[REPAIR REQUIRED — attempt {attempt}/{max_attempts}]\n"
                "The TypeScript compiler / Vite production bundler / Browser runtime found the following errors in the workspace:\n\n"
                f"ERRORS:\n{error_block}\n\n"
                "Fix only the affected files and re-emit complete contents for those files using the <tool_call name=\"write_site\"> format:\n"
                "<tool_call name=\"write_site\">\n"
                "<file path=\"src/components/...\">\n...complete corrected code...\n</file>\n"
                "</tool_call>\n"
                "Do NOT rewrite unrelated files, omit file contents, or use placeholders. Preserve existing exports, props, CSS classes, state, and interaction contracts. Ensure all imports, exports, and styles are valid."
            )
            if any("[Fallback Error]" in error for error in validation.errors):
                repair_note += (
                    "\nA fallback marker change alone is not accepted. Replace the emergency scaffold "
                    "with a distinct, complete section implementation; preserve working navigation, mobile controls, and accessibility."
                )
            if any("[Interaction Error]" in error for error in validation.errors):
                repair_note += (
                    "\nInteraction repairs must change visible behavior, not only selected-button styling. "
                    "Metrics filters must change the rendered cards; annual billing must change displayed numeric prices; "
                    "mobile navigation needs an accessible named button and a menu that opens on small screens. "
                    "Icon-only buttons need aria-label. Keep all code TypeScript-valid."
                )

            # Extract content of files explicitly referenced in error diagnostics
            mentioned_files = set()
            for err_line in focused_errors:
                for cand in [p for p in workspace.rglob("*") if p.is_file() and p.suffix in (".tsx", ".ts", ".css", ".jsx", ".js")]:
                    if not any(part in cand.parts for part in ["node_modules", ".git", "dist", ".vite"]):
                        rel = cand.relative_to(workspace).as_posix()
                        if rel in err_line or cand.name in err_line:
                            mentioned_files.add(rel)
            interaction_targets = {
                "Metrics filter": "src/components/Features.tsx",
                "Annual pricing": "src/components/Pricing.tsx",
                "Mobile navigation": "src/components/Header.tsx",
            }
            for err_line in focused_errors:
                for message, rel in interaction_targets.items():
                    if message in err_line and (workspace / rel).is_file():
                        mentioned_files.add(rel)
            for rel in list(mentioned_files):
                if rel.endswith((".tsx", ".jsx")):
                    paired_css = str(Path(rel).with_suffix(".css")).replace("\\", "/")
                    if (workspace / paired_css).is_file():
                        mentioned_files.add(paired_css)

            file_context_parts = []
            context_chars = 0
            for rel in sorted(mentioned_files, key=lambda path: (not path.endswith((".tsx", ".jsx")), path))[:3]:
                f_p = workspace / rel
                if f_p.is_file():
                    try:
                        f_text = f_p.read_text(encoding="utf-8", errors="replace")
                        if context_chars + len(f_text) <= 12000:
                            file_context_parts.append(f"Current `{rel}`:\n```{Path(rel).suffix[1:]}\n{f_text}\n```")
                            context_chars += len(f_text)
                        else:
                            file_context_parts.append(f"Current `{rel}` is {len(f_text)} characters; request a targeted patch for this file instead of rewriting it from incomplete context.")
                    except Exception:
                        pass

            if file_context_parts:
                repair_note += "\n\nFiles with errors:\n" + "\n\n".join(file_context_parts)

            # Each attempt uses current file contents and current diagnostics.
            # Rejected generations aren't reliable project context.
            active_history = [active_history[0],
                {"role": "user", "content": f"Project '{active_project_name}': {original_prompt}\n\n{repair_note}"}]

            repair_factors = extract_complexity_factors(
                prompt=original_prompt,
                task_mode="site_section",
                requested_files=sorted(mentioned_files) or ["src/App.tsx"],
                repair_diagnostics=error_block,
            )
            repair_tokens = min(4096, max(1800, estimate_output_budget(repair_factors).clamped_tokens,
                                        int(context_chars / 3) + 256))

            # Repairs are deliberately short and scoped. A long timeout encourages
            # the small model to regenerate an entire project instead of making a
            # compiler-directed patch; callers can opt into a larger budget.
            repair_timeout_s = repair_timeout_seconds(repair_tokens,
                getattr(runner_model, 'last_generation_diagnostics', {}),
                os.environ.get("SITE_REPAIR_TURN_TIMEOUT_S"))
            repair_deadline = time.monotonic() + repair_timeout_s

            def repair_stop_check() -> bool:
                return bool((stop_check and stop_check()) or time.monotonic() >= repair_deadline)

            try:
                reply = runner_model.generate_turn(
                    example_idx=0,
                    history=active_history,
                    primary_symbol=active_project_name,
                    max_new_tokens=repair_tokens,
                    temperature=0.15 + 0.05 * (attempt - 1),
                    repetition_penalty=1.05,
                    top_p=CODE_SAMPLING["top_p"],
                    top_k=CODE_SAMPLING["top_k"],
                    stop_check=repair_stop_check,
                )
            except InterruptedError:
                if time.monotonic() >= repair_deadline and q:
                    q.put({"type": "log", "text": f"[Repair] Generation timed out after {repair_timeout_s}s."})
                break
            except Exception as gen_err:
                if q:
                    q.put({"type": "log", "text": f"[Repair Error]: Model generation error: {gen_err}"})
                break

            if stop_check and stop_check():
                break

            from agent.agent_protocol import close_complete_site_envelope, site_envelope_errors
            reply = close_complete_site_envelope(reply)
            envelope_errors = site_envelope_errors(reply)
            if envelope_errors:
                active_history.append({"role": "assistant", "content": reply})
                active_history.append({"role": "user", "content": "[PROTOCOL ERROR] " + "; ".join(envelope_errors) + ". Re-emit complete files."})
                if q:
                    q.put({"type": "log", "text": f"[Repair] Rejected incomplete model output: {envelope_errors}"})
                continue
            turn = parse_agent_output(reply)
            if turn.status_message and q:
                q.put({"type": "status", "status": turn.status_message})
                q.put({"type": "log", "text": f"--> {turn.status_message}"})

            if isinstance(turn.action, WriteSiteAction) and turn.action.files:
                from agent.site_file_normalizer import is_substantive_fallback_rewrite
                superficial = []
                for fpath, fcontent in turn.action.files:
                    try:
                        current_file = resolve_project_path(workspace, fpath)
                    except PermissionError:
                        continue
                    if current_file.is_file() and not is_substantive_fallback_rewrite(
                        current_file.read_text(encoding="utf-8", errors="replace"), fcontent
                    ):
                        superficial.append(fpath)
                if superficial:
                    active_history.append({"role": "assistant", "content": turn.raw_text or reply})
                    active_history.append({"role": "user", "content": (
                        "[REPAIR REJECTED]: Changing only data-fallback or formatting is not a repair. "
                        f"Replace {', '.join(superficial)} with a substantive implementation that satisfies its section requirements."
                    )})
                    if q:
                        q.put({"type": "log", "text": f"[Repair] Rejected marker-only fallback rewrite: {superficial}"})
                    continue

            repaired_any = False
            prior_validation = validation
            modified_before = set(files_modified)
            previous_contents: Dict[str, tuple[bool, str]] = {}
            previous_diffs: Dict[str, Any] = {}
            if isinstance(turn.action, WriteSiteAction) and turn.action.files:
                repair_files = []
                for stem in sorted({Path(path).stem for path, _ in turn.action.files}):
                    pairs = [(path, content) for path, content in turn.action.files if Path(path).stem == stem]
                    repair_files.extend(normalize_site_section_files(
                        pairs, stem, original_prompt=original_prompt, known_sections=active_sections
                    ))
                repair_files = [(path, sanitize_css_for_spec(content, style_spec)
                                 if path.endswith(".css") and style_spec else content)
                                for path, content in repair_files]
                parser_errors = preflight_section_files(repair_files)
                if parser_errors:
                    active_history.append({"role": "assistant", "content": turn.raw_text or reply})
                    active_history.append({"role": "user", "content": "[PARSER PREFLIGHT]: " + "; ".join(parser_errors) + ". Re-emit valid files."})
                    if q:
                        q.put({"type": "log", "text": f"[Repair] Rejected invalid files without overwriting existing content: {parser_errors}"})
                    continue
                for fpath, fcontent in repair_files:
                    try:
                        dest = resolve_project_path(workspace, fpath)
                    except PermissionError as p_err:
                        if q:
                            q.put({"type": "log", "text": f"  [Security] Blocked: {p_err}"})
                        continue

                    old_c = dest.read_text(encoding="utf-8", errors="replace") if dest.is_file() else ""
                    previous_contents.setdefault(fpath, (dest.is_file(), old_c))
                    previous_diffs.setdefault(fpath, diffs.get(fpath))
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_text(fcontent, encoding="utf-8")

                    if export_dir:
                        try:
                            exp_dest = resolve_project_path(export_dir, fpath)
                            exp_dest.parent.mkdir(parents=True, exist_ok=True)
                            exp_dest.write_text(fcontent, encoding="utf-8")
                        except Exception:
                            pass

                    files_dict[fpath] = fcontent
                    if fpath not in files_modified:
                        files_modified.append(fpath)
                    diffs[fpath] = compute_file_diff(fpath, old_c, fcontent)
                    repaired_any = True

                    if q:
                        q.put({
                            "type": "file.modified" if old_c else "file.created",
                            "path": fpath,
                            "file": Path(fpath).name,
                            "chars": len(fcontent),
                            "status": f"Repaired {Path(fpath).name}…",
                            "text": f"  --> Repaired: {fpath} ({len(fcontent)} chars)",
                        })

                if repaired_any:
                    for fpath, fcontent in remove_unresolved_section_links(files_dict).items():
                        dest = resolve_project_path(workspace, fpath)
                        old_c = dest.read_text(encoding="utf-8", errors="replace") if dest.is_file() else ""
                        previous_contents.setdefault(fpath, (dest.is_file(), old_c))
                        previous_diffs.setdefault(fpath, diffs.get(fpath))
                        dest.write_text(fcontent, encoding="utf-8")
                        if export_dir:
                            exp_dest = resolve_project_path(export_dir, fpath)
                            exp_dest.parent.mkdir(parents=True, exist_ok=True)
                            exp_dest.write_text(fcontent, encoding="utf-8")
                        files_dict[fpath] = fcontent
                        if fpath not in files_modified:
                            files_modified.append(fpath)
                        diffs[fpath] = compute_file_diff(fpath, old_c, fcontent)
                    for dependency_error in ensure_runtime_packages(files_dict, BASE_DIR, event_callback=q.put if q else None):
                        if q:
                            q.put({"type": "log", "text": f"[Dependencies] {dependency_error}"})
                    # Re-reconcile App.tsx & Vite runner if components changed
                    has_components = any(k.startswith("src/components/") and k.endswith(".tsx") for k in files_dict.keys())
                    if has_components:
                        _scaffold_site_vite_runner(workspace, active_project_name, files_dict, brief=brief)
                        if export_dir:
                            _scaffold_site_vite_runner(export_dir, active_project_name, files_dict, brief=brief)
                    else:
                        _ensure_project_configs(workspace)

            # Re-validate workspace after repair
            validation = _validate_workspace(workspace, event_callback=q.put if q else None)
            introduced_errors = set(validation.errors) - set(prior_validation.errors)
            critical_regression = (
                (prior_validation.typecheck_passed and not validation.typecheck_passed)
                or (prior_validation.build_passed and not validation.build_passed)
                or (prior_validation.runtime_passed and not validation.runtime_passed)
                or any(error.startswith(("[Interaction Error]", "[Responsive Error]")) for error in introduced_errors)
            )
            if repaired_any and critical_regression:
                for path, (existed, old_source) in previous_contents.items():
                    dest = resolve_project_path(workspace, path)
                    if existed:
                        dest.write_text(old_source, encoding="utf-8")
                        files_dict[path] = old_source
                    else:
                        dest.unlink(missing_ok=True)
                        files_dict.pop(path, None)
                    if export_dir:
                        exp_dest = resolve_project_path(export_dir, path)
                        if existed:
                            exp_dest.parent.mkdir(parents=True, exist_ok=True)
                            exp_dest.write_text(old_source, encoding="utf-8")
                        else:
                            exp_dest.unlink(missing_ok=True)
                    if path not in modified_before and path in files_modified:
                        files_modified.remove(path)
                    old_diff = previous_diffs[path]
                    if old_diff is None:
                        diffs.pop(path, None)
                    else:
                        diffs[path] = old_diff
                _scaffold_site_vite_runner(workspace, active_project_name, files_dict, brief=brief)
                if export_dir:
                    _scaffold_site_vite_runner(export_dir, active_project_name, files_dict, brief=brief)
                validation = _validate_workspace(workspace, event_callback=q.put if q else None)
                active_history.append({"role": "user", "content": (
                    "[REPAIR REGRESSION]: Your previous patch was reverted because it introduced "
                    + "; ".join(sorted(introduced_errors)[:4])
                    + ". Preserve existing working behavior while fixing the remaining errors."
                )})
                if q:
                    q.put({"type": "log", "text": "[Repair] Reverted patch that broke an existing project gate."})
            validation.repair_attempts = attempt
            if session:
                session.last_validation = validation
                session.build_state = validation.to_dict()

            if q:
                q.put({
                    "type": "build.result",
                    "passed": validation.passed,
                    "code_passed": validation.code_passed,
                    "typecheck_passed": validation.typecheck_passed,
                    "build_passed": validation.build_passed,
                    "lint_passed": validation.lint_passed,
                    "runtime_passed": validation.runtime_passed,
                    "preview_running": validation.preview_running,
                    "errors": validation.errors,
                    "warnings": validation.warnings,
                    "status_change": "COMPLETED" if validation.passed else "VERIFYING",
                    "status": "Build passed" if validation.passed else "Fixing issues…",
                    "text": (
                        f"[COMPLETED] ✓ All validations passed on attempt {attempt}/{max_attempts}."
                        if validation.passed
                        else f"[VERIFYING] ✗ Validation failed — {len(validation.errors)} diagnostic lines."
                    ),
                })

            if validation.passed:
                break
            else:
                active_history.append({"role": "assistant", "content": turn.raw_text or reply})

    # ── Step 3: Visual Check & Visual Repair with Full Revalidation ───────────
    visual_score = None
    visual_score_before = None
    visual_issues = []
    screenshot_path = (export_dir / "screenshot.webp") if export_dir else (workspace / "screenshot.webp")

    if validation.passed and run_visual_check:
        try:
            ss = take_screenshot(project_dir=workspace, output_path=screenshot_path)
            if ss and ss.exists():
                v_res = _score_screenshot_heuristic(ss)
                visual_score = v_res.get("score")
                visual_score_before = visual_score
                visual_issues = v_res.get("issues", [])
                if q:
                    q.put({"type": "log", "text": f"[Visual Judge] Visual quality score: {visual_score}/5 (issues={visual_issues})"})
        except Exception as ss_err:
            print(f"[ProjectRepair] Visual evaluation note: {ss_err}")

        # If visual quality is low (< 3/5), run targeted visual repair
        if visual_score is not None and visual_score < 3 and runner_model is not None and active_sections:
            target_sec = None
            for issue in visual_issues:
                issue_lower = issue.lower()
                if "footer" in issue_lower:
                    for sec in reversed(active_sections):
                        if "footer" in sec.lower():
                            target_sec = sec
                            break
                    if not target_sec and active_sections:
                        target_sec = active_sections[-1]
                    break
                elif "header" in issue_lower or "navigation" in issue_lower or "logo" in issue_lower:
                    for sec in active_sections:
                        if any(k in sec.lower() for k in ("header", "nav")):
                            target_sec = sec
                            break
                    if not target_sec and active_sections:
                        target_sec = active_sections[0]
                    break
                elif "blank" in issue_lower or "density" in issue_lower or "flat" in issue_lower:
                    for sec in active_sections:
                        if "hero" in sec.lower():
                            target_sec = sec
                            break
                    if not target_sec and len(active_sections) > 1:
                        target_sec = active_sections[1]
                    break

            if not target_sec and active_sections:
                target_sec = active_sections[0]

            if target_sec:
                pascal_sec = "".join(w.capitalize() for w in re.split(r'[-_]', target_sec))
                t_name = f"src/components/{pascal_sec}.tsx"
                c_name = f"src/components/{pascal_sec}.css"
                existing_t_code = (files_dict.get(t_name) if files_dict else "") or ((workspace / t_name).read_text(encoding="utf-8") if (workspace / t_name).exists() else "")
                existing_c_code = (files_dict.get(c_name) if files_dict else "") or ((workspace / c_name).read_text(encoding="utf-8") if (workspace / c_name).exists() else "")

                if existing_t_code or existing_c_code:
                    original_visual_issues = list(visual_issues)
                    if q:
                        q.put({"type": "log", "text": f"[Visual Repair] Visual score {visual_score}/5 below threshold. Requesting minimal patch from Qwen for '{target_sec}'..."})
                    issues_str = "\n".join(f"- {issue}" for issue in visual_issues)
                    vis_prompt = (
                        f"The component for section '{target_sec}' received a low visual quality evaluation:\n"
                        f"{issues_str}\n\n"
                        f"Existing TSX ({t_name}):\n```tsx\n{existing_t_code}\n```\n\n"
                        f"Existing CSS ({c_name}):\n```css\n{existing_c_code}\n```\n\n"
                        "TASK: Provide a minimal, non-destructive patch to resolve these visual issues.\n"
                        "- Enhance layout density, spacing, contrast, typography, and visual polish.\n"
                        "- DO NOT overwrite or discard existing component features or animations.\n"
                        "- Output the updated component files using write_site format."
                    )
                    try:
                        from agent.site_prompt import SITE_AGENT_SYSTEM_PROMPT
                        v_reply = runner_model.generate_turn(
                            example_idx=0,
                            history=[
                                {"role": "system", "content": SITE_AGENT_SYSTEM_PROMPT},
                                {"role": "user", "content": vis_prompt}
                            ],
                            primary_symbol=active_project_name,
                            max_new_tokens=estimate_output_budget(extract_complexity_factors(
                                prompt=vis_prompt,
                                task_mode="site_section",
                                requested_files=[t_name, c_name],
                                repair_diagnostics=issues_str,
                            )).clamped_tokens,
                            temperature=0.15,
                            repetition_penalty=1.05,
                            top_p=CODE_SAMPLING["top_p"],
                            top_k=CODE_SAMPLING["top_k"],
                        )
                        from agent.agent_protocol import site_envelope_errors
                        if site_envelope_errors(v_reply):
                            raise ValueError("Visual repair returned an incomplete write envelope")
                        v_turn = parse_agent_output(v_reply)
                        if isinstance(v_turn.action, WriteSiteAction) and v_turn.action.files:
                            patched = dict(v_turn.action.files)
                            if c_name in patched and style_spec:
                                patched[c_name] = sanitize_css_for_spec(patched[c_name], style_spec)
                            parser_errors = preflight_section_files([
                                (path, patched[path]) for path in (t_name, c_name) if path in patched and patched[path].strip()
                            ])
                            if parser_errors:
                                raise ValueError("Visual patch rejected by parser preflight: " + "; ".join(parser_errors))
                            if t_name in patched and patched[t_name].strip():
                                t_c = patched[t_name]
                                (workspace / t_name).write_text(t_c, encoding="utf-8")
                                if export_dir:
                                    (export_dir / t_name).write_text(t_c, encoding="utf-8")
                                files_dict[t_name] = t_c
                            if c_name in patched and patched[c_name].strip():
                                c_c = patched[c_name]
                                (workspace / c_name).write_text(c_c, encoding="utf-8")
                                if export_dir:
                                    (export_dir / c_name).write_text(c_c, encoding="utf-8")
                                files_dict[c_name] = c_c

                            # CRITICAL: FULL REVALIDATION after visual repair
                            if q:
                                q.put({"type": "log", "text": f"[Visual Repair] Applied visual patch for '{target_sec}'. Executing FULL REVALIDATION across all 7 gates…"})
                            reval = _validate_workspace(workspace, event_callback=q.put if q else None)
                            if reval.passed:
                                validation = reval
                                if session:
                                    session.last_validation = validation
                                    session.build_state = validation.to_dict()
                                ss2 = take_screenshot(project_dir=workspace, output_path=screenshot_path)
                                if ss2 and ss2.exists():
                                    v_res2 = _score_screenshot_heuristic(ss2)
                                    visual_score = v_res2.get("score", visual_score)
                                    visual_issues = v_res2.get("issues", visual_issues)
                                else:
                                    visual_score = None
                                    visual_issues = ["Visual recheck could not capture the repaired page."]
                                visual_patch_kept = visual_score is not None and visual_score > visual_score_before
                                if not visual_patch_kept:
                                    (workspace / t_name).write_text(existing_t_code, encoding="utf-8")
                                    (workspace / c_name).write_text(existing_c_code, encoding="utf-8")
                                    files_dict[t_name] = existing_t_code
                                    files_dict[c_name] = existing_c_code
                                    if export_dir:
                                        (export_dir / t_name).write_text(existing_t_code, encoding="utf-8")
                                        (export_dir / c_name).write_text(existing_c_code, encoding="utf-8")
                                    validation = _validate_workspace(workspace, event_callback=q.put if q else None)
                                    visual_score = visual_score_before
                                    visual_issues = original_visual_issues
                                    if q:
                                        q.put({"type": "log", "text": "[Visual Repair] Reverted patch because current visual evidence did not improve."})
                                elif q:
                                    q.put({"type": "log", "text": f"[Visual Repair] Full revalidation passed. Visual score improved to {visual_score}/5."})
                            else:
                                if q:
                                    q.put({"type": "log", "text": f"[Visual Repair Warning]: Patch failed revalidation ({len(reval.errors)} errors). Reverting visual patch to preserve valid build."})
                                if existing_t_code:
                                    (workspace / t_name).write_text(existing_t_code, encoding="utf-8")
                                    files_dict[t_name] = existing_t_code
                                    if export_dir:
                                        (export_dir / t_name).write_text(existing_t_code, encoding="utf-8")
                                if existing_c_code:
                                    (workspace / c_name).write_text(existing_c_code, encoding="utf-8")
                                    files_dict[c_name] = existing_c_code
                                    if export_dir:
                                        (export_dir / c_name).write_text(existing_c_code, encoding="utf-8")
                    except Exception as vis_err:
                        print(f"[ProjectRepair] Visual patch error: {vis_err}")

    from agent.project_validator import InteractionValidationResult, VisualValidationResult

    if hasattr(validation, "interaction_validation"):
        int_val = validation.interaction_validation
    else:
        int_passed = bool(
            validation
            and getattr(validation, "interaction_passed", False)
            and not any("[Interaction Error]" in str(e) for e in validation.errors)
        )
        int_val = InteractionValidationResult(
            passed=int_passed,
            status=getattr(validation, "interaction_status", "passed" if int_passed else "failed"),
            errors=[str(e) for e in validation.errors if "[Interaction Error]" in str(e)],
            interactions_tested=getattr(validation, "interactions_tested", 0),
            interactions_required=getattr(validation, "interactions_required", 0),
            interaction_evidence=getattr(validation, "interaction_evidence", []),
        )

    vis_passed = bool(
        validation
        and validation.passed
        and (not run_visual_check or (visual_score is not None and visual_score >= 3.0))
    )
    vis_val = VisualValidationResult(
        passed=vis_passed,
        status="passed" if vis_passed else "failed",
        score=visual_score,
        issues=list(visual_issues or []),
    )

    return ProjectRepairResult(
        validation=validation,
        validation_after_deterministic=validation_after_deterministic,
        deterministic_files=deterministic_files,
        files_modified=files_modified,
        diffs=diffs,
        repair_attempts=validation.repair_attempts,
        visual_score=visual_score,
        visual_score_before=visual_score_before,
        visual_score_after=visual_score,
        visual_score_best=max((s for s in (visual_score_before, visual_score) if s is not None), default=None),
        visual_issues=visual_issues,
        passed=bool(validation.passed and int_val.passed and vis_val.passed),
        self_corrected=(validation.repair_attempts > 0 and validation.passed),
        interaction_validation=int_val,
        visual_validation=vis_val,
    )


def _run_generation(task: dict, q: queue.Queue):
    """Component-mode generation pipeline: runs component agent with full session persistence."""
    import shutil
    from agent import run_agent_on_example

    task_id    = task["task_id"]
    prompt     = task["prompt"]
    symbol     = task["symbol"]
    test_code  = task["test_code"]
    max_turns  = task.get("max_turns", 5)
    max_tokens = task.get("max_tokens", 1024)

    # Initialize or retrieve persistent session
    session_id = task.get("session_id")
    session = session_manager.get_session(session_id) if session_id else None
    if not session:
        session = session_manager.create_session(
            title=symbol,
            mode="component",
            prompt=prompt,
        )
        task["session_id"] = session.session_id

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
        q.put({"type": "status", "status": "Planning component…"})
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

    # Extract all generated files from case_dir
    written_files: dict[str, str] = {}
    case_dir = workspace / "case_000"
    if case_dir.exists():
        for f in case_dir.iterdir():
            if f.is_file():
                try:
                    written_files[f.name] = f.read_text(encoding="utf-8")
                except Exception:
                    pass

    final_code = written_files.get(f"{symbol}.tsx") or written_files.get("Component.tsx", "")
    if final_code:
        written_files[f"{symbol}.tsx"] = final_code
        written_files["Component.tsx"] = final_code

    # Export to timestamped export dir for backwards-compatibility
    EXPORT_DIR = BASE_DIR / "generated_components"
    EXPORT_DIR.mkdir(exist_ok=True)
    timestamp_slug = time.strftime("%Y%m%d_%H%M%S")
    comp_export_dir = EXPORT_DIR / f"{symbol}_{timestamp_slug}"
    comp_export_dir.mkdir(parents=True, exist_ok=True)

    # 1. Write to persistent session workspace (guarded by resolve_project_path)
    for rel_path, content in written_files.items():
        if preflight_section_files([(rel_path, content)]):
            q.put({"type": "log", "text": f"[Parser preflight] Skipped invalid generated {rel_path}; retained previous file."})
            continue
        try:
            sess_dest = resolve_project_path(session.workspace_dir, rel_path)
            sess_dest.parent.mkdir(parents=True, exist_ok=True)
            sess_dest.write_text(content, encoding="utf-8")
        except PermissionError as _path_err:
            print(f"[ComponentGen] Blocked session write: {_path_err}")

    # 2. Write to timestamped export directory
    for rel_path, content in written_files.items():
        try:
            dest = resolve_project_path(comp_export_dir, rel_path)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8")
        except PermissionError:
            pass

    # 3. Also save to generated_components/latest/
    latest_dir = EXPORT_DIR / "latest"
    latest_dir.mkdir(exist_ok=True)
    if final_code:
        (latest_dir / f"{symbol}.tsx").write_text(final_code, encoding="utf-8")
        (latest_dir / "Component.tsx").write_text(final_code, encoding="utf-8")

    # 4. Scaffold runnable Vite environment & static preview in both locations
    q.put({"type": "status", "status": "Preparing preview…"})
    q.put({"type": "log", "text": "[Preview] Preparing preview…"})
    _scaffold_vite_runner(session.workspace_dir, symbol)
    _scaffold_vite_runner(comp_export_dir, symbol)

    # Clean up temp workspace
    try:
        shutil.rmtree(workspace)
    except Exception as _rm_err:
        print(f"[Server] Note: could not clean up workspace {workspace}: {_rm_err}")

    # 5. Verify & repair project workspace
    verify_res = verify_and_repair_project(
        workspace=session.workspace_dir,
        runner=_runner,
        original_prompt=prompt,
        brief=None,
        max_attempts=MAX_REPAIR_ATTEMPTS,
        q=q,
        session=session,
        stop_check=lambda: task_id in cancelled_tasks,
        export_dir=comp_export_dir,
        files_dict=written_files,
        project_name=symbol,
        run_visual_check=True,
    )
    validation = verify_res.validation
    visual_score = verify_res.visual_score
    visual_issues = verify_res.visual_issues
    session.last_validation = validation
    session.build_state = validation.to_dict()
    session.current_plan = [
        {"task": f"Synthesize {symbol}", "status": "completed", "file": f"{symbol}.tsx"},
        {"task": "Verify types & syntax", "status": "completed" if validation.passed else "failed"},
        {"task": "Bundle preview runner", "status": "completed"},
    ]

    # 7. Create initial checkpoint
    chk_num = session.create_checkpoint(f"Initial component: {symbol}")

    # 8. Post-generation structured summary
    visual_check = f"Visual check: {visual_score}/5" + (f" — {', '.join(visual_issues)}" if visual_issues else "") if visual_score is not None else None
    summary = generate_post_generation_summary(
        mode="component",
        files_touched=list(written_files.keys()),
        passed=validation.passed and result["final_passed"],
        auto_recovered=[],
        user_instruction=prompt,
        is_edit=False,
        visual_check=visual_check,
        visual_score=visual_score,
        visual_issues=visual_issues,
    )

    # 9. Session history & persistence
    session.history.append({
        "role": "user",
        "content": prompt,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    })
    session.history.append({
        "turn_id": 1,
        "role": "assistant",
        "summary": summary,
        "content": f"Synthesized component {symbol} with {len(written_files)} files.",
        "files_touched": list(written_files.keys()),
        "diffs": {},
        "checkpoint_id": chk_num,
        "visual_score": visual_score,
        "visual_issues": visual_issues,
        "validation": validation.to_dict(),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    })
    session.save()

    # 10. Store unified complete result
    current_files = session.get_current_files()
    rel_path = f"generated_components/session_{session.session_id}/{symbol}.tsx"
    symbol_tsx = session.workspace_dir / f"{symbol}.tsx"
    res_entry = {
        "task_id":          task_id,
        "session_id":       session.session_id,
        "mode":             "component",
        "final_passed":     validation.passed and result["final_passed"],
        "initial_passed":   validation.passed and result["initial_passed"],
        "self_corrected":   result["self_corrected"],
        "turns_used":       result["turns_used"],
        "code":             final_code,
        "files":            current_files,
        "diffs":            {},
        "summary":          summary,
        "symbol":           symbol,
        "prompt":           prompt,
        "test_code":        task.get("test_code", ""),
        "file_path":        rel_path,
        "full_path":        str(symbol_tsx),
        "checkpoints_count": len(session.checkpoints),
        "visual_score":     visual_score,
        "visual_issues":    visual_issues,
        "validation":       validation.to_dict(),
        "build_state":      session.build_state,
        "preview":          session.preview,
        "is_edit":          False,
        "timestamp":        time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    _store_task_result(task_id, res_entry)
    _append_history(res_entry)

    q.put({"type": "result", "data": res_entry})
    q.put({"type": "done"})


def _kit_edit_note(workspace_dir: Path) -> str:
    """Design-kit vocabulary for edit turns, so edits stay in the same system."""
    try:
        saved = json.loads((Path(workspace_dir) / "content_brief.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ""
    summary = str(saved.get("kit_edit_summary") or "").strip()
    return f" {summary}" if summary else ""


def _run_session_edit_turn(task: dict, q: queue.Queue):
    """Executes a targeted follow-up edit turn within an existing session.

    Implements the blueprint verify→repair→verify loop:
      VERIFYING → COMPLETED  (typecheck passes)
      VERIFYING → REPAIRING → VERIFYING → ...  (up to MAX_REPAIR_ATTEMPTS)
      VERIFYING → FAILED  (all repair attempts exhausted)

    The result's ``final_passed`` / ``initial_passed`` fields are now derived
    from the actual TypeScript compilation result, never hardcoded to True.
    """
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

        # 1. Resolve target files
        target_files = session_manager.resolve_target_files(session, prompt)
        target_names = [p for p, _ in target_files]
        q.put({"type": "log", "text": f"[Target Files Resolved]: {', '.join(target_names) if target_names else 'entire workspace'}"})

        # 1b. Pre-task Snapshot (taken BEFORE the agent edits anything)
        pre_task_snapshot = session.create_pre_task_snapshot(f"Pre-edit: {prompt[:60]}")
        pre_edit_checkpoint_id: int = pre_task_snapshot.get("id", pre_task_snapshot.get("turn_num", 1))
        old_files = session.get_current_files()
        git_hash = pre_task_snapshot.get("git_commit")
        q.put({
            "type": "log",
            "text": f"[Snapshot] Created pre-task snapshot #{pre_edit_checkpoint_id} (Git: {git_hash[:8] if git_hash else 'blob'}).",
        })


        # 2. Build generation context with ContextBuilder & TokenBudget
        detailed_context = session_manager.build_follow_up_context_detailed(
            session=session,
            new_instruction=prompt,
            target_files=target_files,
            diagnostics=session.build_state,
        )
        context_prompt = detailed_context.prompt_text
        usage = detailed_context.token_usage
        q.put({
            "type": "log",
            "text": f"[ContextBuilder] Allocated {usage.total}/{detailed_context.budget.total} tokens: {usage.summary()}",
        })
        allocated_output_budget = task.get("token_budget")
        if allocated_output_budget:
            q.put({
                "type": "log",
                "text": f"[TokenBudget] Allocated {task.get('max_tokens')} max_new_tokens (Tier: '{allocated_output_budget.get('tier', 'standard')}'): {allocated_output_budget.get('explanation', '')}",
            })

        edit_system_prompt = (
            "You are an expert React TypeScript CSS engineer modifying an existing project. "
            "Examine the user request and the current contents of the target files. "
            "Prefer a guarded surgical JSON action: {\"action\":\"replace_hunks\",\"arguments\":{\"path\":\"...\",\"base_sha256\":\"...\",\"hunks\":[{\"before\":\"exact text\",\"after\":\"replacement\",\"expected_count\":1}]}}. "
            "Only use write_site with complete contents when a surgical patch is impossible. "
            "Ensure all TypeScript syntax is correct and design tokens are strictly preserved."
            + _kit_edit_note(session.workspace_dir)
        )

        history = [
            {"role": "system", "content": edit_system_prompt},
            {"role": "user", "content": context_prompt},
        ]


        if task_id in cancelled_tasks:
            return

        brief = generate_content_brief(
            session.prompt,
            style_tokens=session.style_tokens,
            style_preset=session.style_preset,
        )
        style_spec = brief.get("style_spec") if brief else None

        # ── Execute follow-up edit turn with verification & repair ────────────
        validation: ValidationResult = session.last_validation or ValidationResult(typecheck_passed=False)
        diffs: dict = {}
        files_modified: list = []
        assistant_text: str = ""
        turn = None
        verify_res = None

        q.put({"type": "status_change", "status": "VERIFYING"})
        q.put({"type": "status", "status": "Planning edit…"})
        q.put({"type": "log", "text": f"[VERIFYING] Generating edit — attempt 1/{MAX_REPAIR_ATTEMPTS}…"})

        from agent.agent_protocol import site_envelope_errors
        for protocol_attempt in range(2):
            try:
                assistant_text = _runner.generate_turn(
                    example_idx=0,
                    history=history,
                    primary_symbol=session.title,
                    max_new_tokens=task.get("max_tokens", 1536),
                    temperature=0.15,
                    repetition_penalty=1.05,
                    top_p=CODE_SAMPLING["top_p"],
                    top_k=CODE_SAMPLING["top_k"],
                    stop_check=lambda: task_id in cancelled_tasks,
                )
            except InterruptedError:
                return
            envelope_errors = site_envelope_errors(assistant_text)
            if not envelope_errors:
                break
            history.append({"role": "assistant", "content": assistant_text})
            history.append({"role": "user", "content": "[PROTOCOL ERROR] " + "; ".join(envelope_errors) + ". Emit a complete edit action."})
        else:
            q.put({"type": "task.failed", "status_change": "FAILED", "error": "Model returned an incomplete edit action twice."})
            return

        if task_id in cancelled_tasks:
            return

        turn = parse_agent_output(assistant_text)
        if turn.status_message:
            q.put({"type": "status", "status": turn.status_message})
            q.put({"type": "log", "text": f"--> {turn.status_message}"})

        # ── Write generated files / process actions ───────────────────────────
        if isinstance(turn.action, EditFileAction):
            try:
                updated = apply_edit(session.workspace_dir, turn.action)
                fpath = turn.action.path
                old_content = old_files.get(fpath, "")
                diffs[fpath] = compute_file_diff(fpath, old_content, updated)
                files_modified.append(fpath)
                q.put({"type": "file.modified", "path": fpath, "file": Path(fpath).name,
                       "chars": len(updated), "diff_summary": f"({len(updated)} chars)",
                       "status": f"Editing {Path(fpath).name}…", "text": f"  --> Patched: {fpath}"})
            except Exception as exc:
                q.put({"type": "task.failed", "status_change": "FAILED", "error": str(exc)})
                return
        elif isinstance(turn.action, WriteSiteAction) and turn.action.files:
            candidate_files = [(fpath, sanitize_css_for_spec(fcontent, style_spec)
                                if fpath.endswith(".css") and style_spec else fcontent)
                               for fpath, fcontent in turn.action.files]
            parser_errors = preflight_section_files(candidate_files)
            if parser_errors:
                q.put({"type": "task.failed", "status_change": "FAILED",
                       "error": "Parser preflight rejected generated files: " + "; ".join(parser_errors)})
                return
            for fpath, fcontent in candidate_files:

                try:
                    dest = resolve_project_path(session.workspace_dir, fpath)
                except PermissionError as _path_err:
                    q.put({"type": "log", "text": f"  [Security] Blocked: {_path_err}"})
                    continue

                fname = Path(fpath).name
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(fcontent, encoding="utf-8")

                old_content = old_files.get(fpath, "")
                diffs[fpath] = compute_file_diff(fpath, old_content, fcontent)
                files_modified.append(fpath)

                event_type = "file.created" if not old_content else "file.modified"
                q.put({
                    "type": event_type,
                    "path": fpath,
                    "file": fname,
                    "chars": len(fcontent),
                    "diff_summary": f"({len(fcontent)} chars)",
                    "status": f"Writing {fname}…",
                    "text": f"  --> Written: {fpath} ({len(fcontent)} chars)",
                })

            history.append({"role": "assistant", "content": turn.raw_text or assistant_text})

            # Persist new acceptance requirements before verification. Rollback
            # restores this file together with the edited source on failure.
            brief_path = session.workspace_dir / "content_brief.json"
            if brief_path.is_file():
                brief_record = json.loads(brief_path.read_text(encoding="utf-8"))
                follow_ups = brief_record.setdefault("follow_up_requests", [])
                follow_ups.append(prompt)
                brief_path.write_text(json.dumps(brief_record, indent=2, default=str), encoding="utf-8")
                files_modified.append("content_brief.json")

            # Run unified verify_and_repair_project loop (typecheck -> build -> Qwen repair -> runtime -> interaction)
            verify_res = verify_and_repair_project(
                workspace=session.workspace_dir,
                runner=_runner,
                original_prompt=prompt,
                brief=brief,
                max_attempts=MAX_REPAIR_ATTEMPTS,
                q=q,
                session=session,
                stop_check=lambda: task_id in cancelled_tasks,
                export_dir=None,
                files_dict=None,
                project_name=session.title,
                history=history,
                initial_files_modified=files_modified,
                initial_diffs=diffs,
                run_visual_check=True,
            )
            validation = verify_res.validation
            files_modified = verify_res.files_modified
            diffs = verify_res.diffs

        elif isinstance(turn.action, InstallPackageAction):
            dm = DependencyManager(session.workspace_dir, event_callback=q.put)
            try:
                res = dm.install_package(turn.action.package, turn.action.version, turn.action.is_dev)
                if res.get("success"):
                    q.put({"type": "log", "text": f"  [Dependencies] Successfully installed '{turn.action.package}'."})
                    if "package.json" not in files_modified:
                        files_modified.append("package.json")
                else:
                    q.put({"type": "log", "text": f"  [Dependencies Error]: {res.get('output', 'Install failed')}"})
            except PackagePolicyError as p_err:
                q.put({"type": "log", "text": f"  [Security] {p_err}"})
            validation = _validate_workspace(session.workspace_dir)
            session.last_validation = validation

        elif isinstance(turn.action, RemovePackageAction):
            dm = DependencyManager(session.workspace_dir, event_callback=q.put)
            try:
                res = dm.remove_package(turn.action.package)
                if res.get("success"):
                    q.put({"type": "log", "text": f"  [Dependencies] Successfully removed '{turn.action.package}'."})
                    if "package.json" not in files_modified:
                        files_modified.append("package.json")
                else:
                    q.put({"type": "log", "text": f"  [Dependencies Error]: {res.get('output', 'Removal failed')}"})
            except PackagePolicyError as p_err:
                q.put({"type": "log", "text": f"  [Security] {p_err}"})
            validation = _validate_workspace(session.workspace_dir)
            session.last_validation = validation

        elif isinstance(turn.action, (GetDependenciesAction, InspectDependenciesAction)):
            dm = DependencyManager(session.workspace_dir, event_callback=q.put)
            deps = dm.get_dependencies()
            q.put({"type": "log", "text": f"  [Dependencies Inventory]: {json.dumps(deps.get('all', {}))}"})
            validation = session.last_validation or _validate_workspace(session.workspace_dir)

        elif isinstance(turn.action, ReadFileAction):
            try:
                f_path = resolve_project_path(session.workspace_dir, turn.action.path)
                if f_path.is_file():
                    c_text = f_path.read_text(encoding="utf-8")
                    q.put({"type": "log", "text": f"  [Read File]: Inspected '{turn.action.path}' ({len(c_text)} chars)."})
                else:
                    q.put({"type": "log", "text": f"  [Read File Warning]: File not found: '{turn.action.path}'."})
            except Exception as r_err:
                q.put({"type": "log", "text": f"  [Read File Error]: {r_err}"})
            validation = session.last_validation or _validate_workspace(session.workspace_dir)

        elif isinstance(turn.action, (GetWebglErrorsAction, GetSceneMetadataAction, GetAssetManifestAction)):
            try:
                from agent.three_d_tools import get_webgl_errors, get_scene_metadata, get_asset_manifest
                if isinstance(turn.action, GetWebglErrorsAction):
                    res = get_webgl_errors(session.workspace_dir)
                    q.put({"type": "log", "text": f"  [WebGL Diagnostics]: status={res.get('webgl_status')} errors={len(res.get('errors', []))} warnings={len(res.get('warnings', []))}"})
                elif isinstance(turn.action, GetSceneMetadataAction):
                    res = get_scene_metadata(session.workspace_dir)
                    q.put({"type": "log", "text": f"  [3D Scene Metadata]: lights={res.get('lights', {}).get('total')} dpr={res.get('canvas', {}).get('dpr')} flags={len(res.get('performance_flags', []))}"})
                else:
                    res = get_asset_manifest(session.workspace_dir)
                    q.put({"type": "log", "text": f"  [3D Asset Manifest]: models={len(res.get('models', []))} textures={len(res.get('textures', []))} suspense={res.get('has_suspense_boundaries')}"})
            except Exception as three_err:
                q.put({"type": "log", "text": f"  [3D Tool Error]: {three_err}"})
            validation = session.last_validation or _validate_workspace(session.workspace_dir)

        else:
            q.put({"type": "log", "text": "[Notice]: Model emitted general refinement (no file writes)."})
            validation = session.last_validation or _validate_workspace(session.workspace_dir)

        # ── Post-loop: determine final state ───────────────────────────────────
        if not files_modified:
            # Read-only or no-file-change action: preserve last verified state without fabricating success
            validation = session.last_validation
            final_passed = validation.passed
            self_corrected = False
            validation_status = "unchanged"

            q.put({
                "type": "task.completed",
                "status_change": "COMPLETED",
                "status": "Task completed",
                "text": "[Notice] Task completed. No files changed. Validation status unchanged.",
            })
            q.put({
                "type": "preview.ready",
                "url": f"/preview/{session.session_id}",
                "mode": session.mode,
                "status": "Preview ready",
                "text": "[Preview] Workspace unchanged (0 files modified). Validation status unchanged.",
            })
        else:
            final_passed = validation.passed and (verify_res.passed if verify_res is not None else True)
            self_corrected = validation.repair_attempts > 0 and final_passed
            validation_status = "passed" if final_passed else "failed"

            if not final_passed:
                # FAILED: roll back to the pre-edit checkpoint so the workspace
                # is left in a known-good state.
                q.put({
                    "type": "task.failed",
                    "status_change": "FAILED",
                    "status": "Edit failed",
                    "error": f"Edit could not be repaired after {MAX_REPAIR_ATTEMPTS} attempts.",
                    "text": (
                        f"[FAILED] Edit could not be repaired after "
                        f"{MAX_REPAIR_ATTEMPTS} attempts. "
                        "Rolling back workspace to last good checkpoint."
                    ),
                })
                if pre_edit_checkpoint_id is not None:
                    try:
                        session.revert_to_checkpoint(pre_edit_checkpoint_id)
                        q.put({"type": "log", "text": f"[Rollback] Restored checkpoint #{pre_edit_checkpoint_id}."})
                    except Exception as rb_err:
                        q.put({"type": "log", "text": f"[Rollback] Warning: could not restore checkpoint: {rb_err}"})
            else:
                # Validation is the final write boundary. Do not change runner
                # files after it has passed and before committing the project.
                q.put({
                    "type": "preview.ready",
                    "url": f"/preview/{session.session_id}",
                    "mode": session.mode,
                    "status": "Preview ready",
                    "text": f"[Preview] Project files updated ({len(files_modified)} modified). Vite HMR active.",
                })

        # 4. Checkpoint / Commit (only on actual successful file edits)
        chk_num: int | None = None
        if files_modified and final_passed:
            commit_res = session.commit_task(
                f"Edit ({'repaired' if self_corrected else 'clean'}): {prompt[:55]}",
                files_touched=files_modified,
            )
            chk_num = commit_res.get("turn_num", commit_res.get("id"))
            c_git = commit_res.get("git_commit")
            q.put({
                "type": "log",
                "text": f"[Commit] Committed task changes (checkpoint #{chk_num}, Git: {c_git[:8] if c_git else 'blob'}).",
            })


        # 5. Visual quality evaluation (success only)
        visual_score = verify_res.visual_score if verify_res is not None else None
        visual_issues: list = list(verify_res.visual_issues or []) if verify_res is not None else []
        if final_passed and verify_res is None:
            screenshot_path = session.workspace_dir / "screenshot.webp"
            try:
                ss = take_screenshot(project_dir=session.workspace_dir, output_path=screenshot_path)
                if ss and ss.exists():
                    v_res = _score_screenshot_heuristic(ss)
                    visual_score = v_res.get("score")
                    visual_issues = v_res.get("issues", [])
            except Exception as visual_error:
                visual_issues = [f"Visual check failed: {visual_error}"]

        # 6. Structured post-turn summary
        visual_check = (
            f"Visual check: {visual_score}/5"
            + (f" — {', '.join(visual_issues)}" if visual_issues else "")
        ) if visual_score is not None else None

        summary = generate_post_generation_summary(
            mode=session.mode,
            files_touched=files_modified,
            passed=final_passed,          # ← real result, not hardcoded True
            auto_recovered=[],
            user_instruction=prompt,
            is_edit=True,
            visual_check=visual_check,
            visual_score=visual_score,
            visual_issues=visual_issues,
            validation_status=validation_status,
        )

        validation_payload = validation.to_dict()
        if validation_status == "unchanged":
            validation_payload["validationStatus"] = "unchanged"
            validation_payload["validation_status"] = "unchanged"

        # 7. Record turn in session history & update build state / plan
        session.build_state = validation.to_dict()
        session.current_plan.append({
            "task": f"Edit: {prompt[:45]}",
            "status": "completed" if (final_passed or not files_modified) else "failed",
            "files": files_modified,
            "repair_attempts": validation.repair_attempts,
        })
        turn_record = {
            "turn_id": len(session.history) + 1,
            "role": "assistant",
            "status_message": turn.status_message if turn else "",
            "thought": "",
            "content": turn.raw_text if turn and turn.raw_text else assistant_text,
            "user_instruction": prompt,
            "summary": summary,
            "files_touched": files_modified,
            "diffs": diffs,
            "checkpoint_id": chk_num,
            "visual_score": visual_score,
            "visual_issues": visual_issues,
            "validation": validation_payload,
            "validation_status": validation_status,
            "validationStatus": validation_status,
            "file_path": f"generated_components/session_{session.session_id}/",
            "filePath": f"generated_components/session_{session.session_id}/",
            "folder_name": f"session_{session.session_id}",
            "folderName": f"session_{session.session_id}",
            "full_path": str(session.workspace_dir),
            "fullPath": str(session.workspace_dir),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        session.history.append({
            "role": "user",
            "content": prompt,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        })
        session.history.append(turn_record)
        session.save()

        # 8. Package site_entry for SSE result event
        app_file = session.workspace_dir / "src" / "App.tsx"
        app_content = app_file.read_text(encoding="utf-8") if app_file.exists() else ""
        if not app_content:
            sym_file = session.workspace_dir / f"{session.title}.tsx"
            comp_file = session.workspace_dir / "Component.tsx"
            if sym_file.exists():
                app_content = sym_file.read_text(encoding="utf-8")
            elif comp_file.exists():
                app_content = comp_file.read_text(encoding="utf-8")

        current_files = session.get_current_files()
        sec_count = len([
            p for p in current_files
            if p.startswith("src/components/") and p.endswith(".tsx")
        ]) if session.mode == "site" else 1

        site_entry = {
            "task_id":          task_id,
            "session_id":       session.session_id,
            "mode":             session.mode,
            "final_passed":     final_passed,      # ← real result
            "initial_passed":   not self_corrected and final_passed,
            "self_corrected":   self_corrected,
            "repair_attempts":  validation.repair_attempts,
            "turns_used":       len(session.history),
            "sections_completed": sec_count,
            "sections_planned": sec_count,
            "code":             app_content,
            "files":            current_files,
            "diffs":            diffs,
            "summary":          summary,
            "symbol":           session.title,
            "prompt":           prompt,
            "style_preset":     session.style_preset,
            "style_tokens":     session.style_tokens,
            "file_path":        f"generated_components/session_{session.session_id}/",
            "filePath":         f"generated_components/session_{session.session_id}/",
            "folder_name":      f"session_{session.session_id}",
            "folderName":       f"session_{session.session_id}",
            "full_path":        str(session.workspace_dir),
            "fullPath":         str(session.workspace_dir),
            "checkpoints_count": len(session.checkpoints),
            "visual_score":     visual_score,
            "visual_issues":    visual_issues,
            "validation":       validation_payload,
            "validation_status": validation_status,
            "validationStatus": validation_status,
            "build_state":      session.build_state,
            "preview":          session.preview,
            "is_edit":          True,
            "timestamp":        time.strftime("%Y-%m-%d %H:%M:%S"),
        }

        _store_task_result(task_id, site_entry)
        _append_history(site_entry)

        q.put({"type": "result", "data": site_entry})
        q.put({"type": "done"})

    finally:
        _stdout_context.active_queue = None


def _store_task_failure(task: dict, error: Exception) -> dict:
    """Keep failures recoverable through polling and reopening, including partial code."""
    session_id = task.get("session_id") or task.get("project_id")
    session = session_manager.get_session(session_id) if session_id else None
    files = {}
    if session and (session.workspace_dir / "src").exists():
        for path in (session.workspace_dir / "src").rglob("*"):
            if path.is_file() and path.suffix in {".tsx", ".ts", ".css", ".jsx", ".js"}:
                files[path.relative_to(session.workspace_dir).as_posix()] = path.read_text(encoding="utf-8", errors="replace")
    validation = ValidationResult(runtime_unverified=True, typecheck_status="unverified",
        build_status="unverified", lint_status="unverified", contract_status="blocked",
        accessibility_status="unverified", preview_status="unverified",
        errors=[f"[Generation Error] {error}"])
    result = {"task_id": task["task_id"], "session_id": session_id, "status": "failed",
        "mode": task.get("mode", "site"), "prompt": task.get("prompt", ""),
        "summary": f"Generation failed; {len(files)} accepted source files preserved. {error}",
        "files": files, "files_touched": list(files), "validation": validation.to_dict(),
        "generation_complete": False, "final_passed": False, "completion_status": "FAILED"}
    _store_task_result(task["task_id"], result)
    if session:
        if not session.history:
            session.history.append({"role": "user", "content": task.get("prompt", "")})
        session.history.append({"role": "assistant", "content": result["summary"],
            "summary": result["summary"], "status": "failed", "completion_status": "FAILED",
            "files": files, "validation": validation.to_dict(), "final_passed": False})
        session.last_validation = validation
        session.build_state = validation.to_dict()
        session.save()
    return result


def _validate_blocked_site(workspace: Path, brief: dict, diagnostics: list) -> ValidationResult:
    """Check saved partial code without confusing missing sections with compiler failure."""
    from agent.project_validator import run_project_typecheck, run_project_build
    from evaluation.three_d_performance_validator import is_three_d_requested
    # The agent may enrich the original planner brief after section generation.
    # Preserve those saved requirements even when the planner's in-memory brief
    # doesn't yet contain the manifest.
    try:
        saved_brief = json.loads((workspace / 'content_brief.json').read_text(encoding='utf-8'))
        brief = {**brief, **saved_brief}
    except (OSError, ValueError):
        pass
    motion_plan = [item.to_dict() if hasattr(item, "to_dict") else item for item in brief.get("motion_plan", [])]
    manifest = brief.get("requirement_manifest", {})
    three_d = bool(manifest.get("three_d_constraints")) or is_three_d_requested(json.dumps(brief, default=str))
    interactions = manifest.get("interaction_constraints", [])
    validation = ValidationResult(
        runtime_unverified=True, typecheck_status="unverified", build_status="unverified",
        lint_status="unverified", contract_status="blocked", accessibility_status="unverified",
        preview_status="unverified", motion_plan=motion_plan,
        motion_passed=not bool(motion_plan), motion_status="unverified" if motion_plan else "not_requested",
        motion_runtime_status="unverified" if motion_plan else "not_requested",
        three_d_passed=not three_d, three_d_status="unverified" if three_d else "not_requested",
        three_d_static_status="unverified" if three_d else "not_requested",
        three_d_runtime_status="unverified" if three_d else "not_requested",
        interactions_required=len(interactions),
        errors=[f"[Generation blocked] {diagnostic}" for diagnostic in diagnostics],
    )
    if (workspace / "package.json").is_file() and (workspace / "tsconfig.json").is_file():
        validation.typecheck_passed, errors = run_project_typecheck(workspace)
        validation.errors.extend(errors)
        validation.typecheck_status = "passed" if validation.typecheck_passed else "failed"
        if validation.typecheck_passed:
            validation.build_passed, errors = run_project_build(workspace)
            validation.errors.extend(errors)
            validation.build_status = "passed" if validation.build_passed else "failed"
    return validation


def _run_site_generation(task: dict, q: queue.Queue):
    """Site-mode generation pipeline: runs the multi-turn site agent and scaffolds a Vite app."""
    import shutil
    from agent import run_site_agent_on_example
    from agent.agent import resolve_site_strategy
    from site_brief import generate_content_brief, brief_to_xml

    task_id      = task["task_id"]
    prompt       = task["prompt"]
    project_name = task["symbol"]
    strategy     = resolve_site_strategy(task.get("strategy"))
    max_turns    = task.get("max_turns", 10)
    max_tokens   = task.get("max_tokens", 2048)

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
        q.put({"type": "status", "status": "Planning project…"})
        print(f"[SiteGen] Planning project… Generating content brief for: {prompt[:60]}...")
        style_tokens = task.get("style_tokens")
        style_preset = task.get("style_preset")
        brief = generate_content_brief(prompt, style_tokens=style_tokens, style_preset=style_preset)
        sections = (brief.get("sections", ["header", "hero", "footer"]) if brief else ["header", "hero", "footer"])
        custom_section_instructions = brief.get("custom_section_instructions") if brief else None
        # Ensure footer is last
        if "footer" in sections:
            sections = [s for s in sections if s != "footer"] + ["footer"]
        # The freeform loop needs retry headroom; the kit makes one call per section.
        if strategy == "freeform":
            max_turns = max(max_turns, len(sections) + 4, 10)
        xml_brief = brief_to_xml(brief) if brief else ""
        style_spec = brief.get("style_spec") if brief else None

        # Stage 2: Run site agent loop with live plan callback & stop check
        def _on_site_agent_event(evt):
            if isinstance(evt, dict):
                ctx_tokens = getattr(_runner, "last_context_tokens", 0) or 0
                max_ctx_tokens = getattr(_runner, "max_seq_length", ModelRuntimeConfig.get_max_seq_length())
                if ctx_tokens:
                    evt.setdefault("context_tokens", ctx_tokens)
                    evt.setdefault("contextTokens", ctx_tokens)
                    session.context_tokens = ctx_tokens
                evt.setdefault("max_context_tokens", max_ctx_tokens)
                evt.setdefault("maxContextTokens", max_ctx_tokens)

                if evt.get("type") == "plan_update" and evt.get("status") in ("completed", "auto_recovered"):
                    try:
                        for case_root in workspace.glob("site_*"):
                            for fpath in case_root.rglob("*"):
                                if fpath.is_file() and not fpath.name.endswith(".tsbuildinfo"):
                                    rel = fpath.relative_to(case_root)
                                    try:
                                        s_dest = resolve_project_path(session.workspace_dir, str(rel))
                                        s_dest.parent.mkdir(parents=True, exist_ok=True)
                                        s_dest.write_text(fpath.read_text(encoding="utf-8", errors="replace"), encoding="utf-8")
                                    except Exception:
                                        pass
                    except Exception:
                        pass
            q.put(evt)

        result = run_site_agent_on_example(
            orig_idx=0,
            prompt=prompt,
            project_name=project_name,
            brief_xml=xml_brief,
            sections=sections,
            runner=_runner,
            workspace_root=workspace,
            max_turns=max_turns,
            max_new_tokens=task.get("site_token_limit"),
            style_spec=style_spec,
            custom_section_instructions=custom_section_instructions,
            business_type=brief.get("business_type", "general") if brief else "general",
            event_callback=_on_site_agent_event,
            diagnostics_dir=session.workspace_dir / "raw_generation",
            stop_check=lambda: task_id in cancelled_tasks,
            strategy=strategy,
            brief=brief,
        )
    finally:
        _stdout_context.active_queue = None

    kit_output = result.get("kit") if isinstance(result, dict) else None
    if kit_output:
        # The kit decides the final section order and owns the site stylesheet,
        # fonts, head tags and public assets used by the scaffold below.
        brief = dict(brief or {})
        brief.update({
            "kit_base_css": kit_output.get("base_css"),
            "kit_font_href": kit_output.get("font_href"),
            "kit_head_tags": kit_output.get("head_tags"),
            "kit_public_files": kit_output.get("public_files") or [],
            "kit_edit_summary": kit_output.get("edit_summary", ""),
            "kit_title": kit_output.get("title", ""),
        })
        sections = list(result.get("sections_planned") or sections)


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
    blocked_sections = result.get("blocked_sections") or []
    blocked_reasons = {
        str(log.get("section")): log
        for log in result.get("turn_logs", [])
        if isinstance(log, dict) and log.get("action") == "section_blocked" and log.get("section")
    }
    blocked_diagnostics = [
        {"section": item, "reason": blocked_reasons.get(item, {}).get("reason", "generation blocked"),
         "errors": blocked_reasons.get(item, {}).get("errors", [])}
        if isinstance(item, str) else item
        for item in blocked_sections
    ]
    written_files: dict[str, str] = result.get("files", {})
    accepted_files: dict[str, str] = {}
    for rel_path, content in written_files.items():
        section_stem = Path(rel_path).stem.lower()
        if rel_path.startswith("src/components/") and section_stem in {
            str(item.get("section", item.get("name", "")) if isinstance(item, dict) else item).lower()
            for item in blocked_sections
        }:
            q.put({"type": "log", "text": f"[Generation blocked] Ignored unaccepted section file {rel_path}."})
            continue
        if preflight_section_files([(rel_path, content)]):
            q.put({"type": "log", "text": f"[Parser preflight] Skipped invalid generated {rel_path}; retained previous file."})
            try:
                previous = resolve_project_path(session.workspace_dir, rel_path)
                if previous.is_file():
                    old_content = previous.read_text(encoding="utf-8")
                    if not preflight_section_files([(rel_path, old_content)]):
                        accepted_files[rel_path] = old_content
            except (PermissionError, OSError):
                pass
        else:
            accepted_files[rel_path] = content
    written_files = accepted_files
    from agent.dependency_manager import ensure_runtime_packages
    for dependency_error in ensure_runtime_packages(written_files, BASE_DIR, event_callback=q.put):
        q.put({"type": "log", "text": f"[Dependencies] {dependency_error}"})

    for rel_path, content in written_files.items():
        # Session persistent workspace
        try:
            sess_dest = resolve_project_path(session.workspace_dir, rel_path)
        except PermissionError as _path_err:
            print(f"[SiteGen] Blocked session write: {_path_err}")
            continue
        sess_dest.parent.mkdir(parents=True, exist_ok=True)
        sess_dest.write_text(content, encoding="utf-8")
        # Timestamped export
        try:
            dest = resolve_project_path(site_export_dir, rel_path)
        except PermissionError as _path_err:
            print(f"[SiteGen] Blocked export write: {_path_err}")
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")

    # Scaffold the Vite environment in both session workspace and timestamped export
    q.put({"type": "status", "status": "Preparing preview…"})
    q.put({"type": "log", "text": "[Preview] Preparing preview…"})
    # A blocked generation is a partial result, not permission to invent the
    # missing sections in the project repair loop. A preview of accepted files
    # is still useful, but don't create an empty "No sections" site.
    if written_files:
        _scaffold_site_vite_runner(session.workspace_dir, project_name, written_files, brief=brief, q=q)
        _scaffold_site_vite_runner(site_export_dir, project_name, written_files, brief=brief)
    brief_record = {
        "original_prompt": prompt,
        "sections": sections,
        "custom_section_instructions": custom_section_instructions or {},
        "business_type": brief.get("business_type", "general") if brief else "general",
        "motion_plan": [item.to_dict() if hasattr(item, "to_dict") else item for item in brief.get("motion_plan", [])] if brief else [],
        "requirement_manifest": brief.get("requirement_manifest", {}) if brief else {},
        "strategy": strategy,
        "kit_edit_summary": (brief or {}).get("kit_edit_summary", ""),
    }
    for brief_workspace in (session.workspace_dir, site_export_dir):
        (brief_workspace / "content_brief.json").write_text(
            json.dumps(brief_record, default=str, indent=2), encoding="utf-8"
        )

    # Clean up temp workspace
    try:
        shutil.rmtree(workspace)
    except Exception as _rm_err:
        print(f"[Server] Note: could not clean up site workspace {workspace}: {_rm_err}")

    # ── Project-level verify and repair loop (TypeScript, build, browser runtime, visual, full revalidation) ──
    verify_res = None if blocked_sections else verify_and_repair_project(
        workspace=session.workspace_dir,
        runner=_runner,
        original_prompt=prompt,
        brief=brief,
        max_attempts=3,
        q=q,
        session=session,
        stop_check=lambda: task_id in cancelled_tasks,
        export_dir=site_export_dir,
        files_dict=written_files,
        project_name=project_name,
        sections=sections,
        run_visual_check=True,
    )
    if blocked_sections:
        diagnostics = [
            f"{item.get('section', item.get('name', 'section'))}: {item.get('reason', item.get('error', 'generation blocked'))}"
            if isinstance(item, dict) else str(item)
            for item in blocked_diagnostics
        ]
        validation = _validate_blocked_site(session.workspace_dir, brief or {}, diagnostics)
        verify_res = ProjectRepairResult(validation=validation, generation_complete=False)
        q.put({"type": "log", "text": "[Generation blocked] " + "; ".join(diagnostics)})
    validation = verify_res.validation
    visual_score = verify_res.visual_score
    visual_issues = verify_res.visual_issues
    if verify_res.self_corrected:
        result["self_corrected"] = True

    # Use App.tsx content as the 'code' field for backward-compatible history display
    app_tsx_content = written_files.get("App.tsx", "")
    if not app_tsx_content:
        tsx_files = [c for p, c in written_files.items() if p.endswith(".tsx")]
        app_tsx_content = tsx_files[0] if tsx_files else ""

    session.last_validation = validation
    session.build_state = validation.to_dict()
    blocked_names = {
        str(item.get("section", item.get("name", "")) if isinstance(item, dict) else item).lower()
        for item in blocked_sections
    }
    session.current_plan = [
        {
            "task": f"Section: {sec}",
            "status": "blocked" if sec.lower() in blocked_names else "completed",
            "file": f"src/components/{''.join(w[:1].upper() + w[1:] for w in re.split(r'[-_]', sec) if w)}.tsx",
        }
        for sec in sections
    ]

    # Create initial checkpoint and post-generation structured summary
    # Derive the 3 distinct concepts:
    # 1. section_completion (e.g. 6 / 6)
    # 2. project_validation (passed / failed)
    # 3. generation_quality (native / repaired / fallback)
    sections_planned_list = result.get("sections_planned") or sections
    sections_planned = len(sections_planned_list)
    sections_completed = result.get("sections_completed", len(sections) - len(blocked_names))
    if blocked_sections:
        sections_completed = min(sections_completed, max(0, sections_planned - len(blocked_names)))
    generation_complete = bool(not blocked_sections and result.get("generation_complete", (sections_completed == sections_planned)))
    section_completion = (f"{sections_completed} / {sections_planned}" if blocked_sections
                          else result.get("section_completion") or f"{sections_completed} / {sections_planned}")
    project_validation = "passed" if validation.passed else "failed"

    base_quality = result.get("generation_quality", "native")
    unrepaired = result.get("unrepaired_fallbacks", [])
    if blocked_sections:
        generation_quality = "blocked"
    elif base_quality == "fallback" or len(unrepaired) > 0:
        generation_quality = "fallback"
    elif verify_res.self_corrected or getattr(verify_res, 'deterministic_files', []) or base_quality == "repaired" or len(result.get("repaired_sections", [])) > 0:
        generation_quality = "repaired"
    else:
        generation_quality = "native"

    from agent.project_validator import InteractionValidationResult, VisualValidationResult
    interaction_validation = getattr(
        verify_res,
        "interaction_validation",
        InteractionValidationResult(
            passed=validation.interaction_passed,
            status="passed" if validation.interaction_passed else "failed",
            errors=[e for e in validation.errors if "[Interaction Error]" in str(e)],
        )
    )
    visual_validation = getattr(
        verify_res,
        "visual_validation",
        VisualValidationResult(
            passed=(visual_score is None or visual_score >= 3.0) and validation.passed,
            status="passed" if (visual_score is None or visual_score >= 3.0) and validation.passed else "failed",
            score=visual_score,
            issues=visual_issues,
        )
    )

    # Authoritative multi-gate completion rule:
    # NEVER 6/6 sections => final_passed!
    final_passed = bool(
        generation_complete
        and generation_quality != "fallback"
        and validation.passed
        and interaction_validation.passed
        and visual_validation.passed
    )
    completion_status = (
        "BLOCKED" if blocked_sections else
        "COMPLETE" if final_passed else
        "COMPLETED_WITH_QUALITY_FAILURE" if generation_complete and validation.passed and not visual_validation.passed else
        "FAILED"
    )

    from agent.generation_scorecards import generation_scorecards
    scorecards = generation_scorecards(result, verify_res, validation, final_passed,
        {"mode": "mock" if getattr(_runner, 'mock', False) else "live",
         "task_id": task_id, "model": dict(_loaded_model_info or {}),
         "raw_output_directory": str(session.workspace_dir / 'raw_generation')})

    # Create initial checkpoint and post-generation structured summary
    chk_num = session.create_checkpoint(f"Initial site: {len(sections)} sections")
    visual_check = f"Visual check: {visual_score}/5" + (f" — {', '.join(visual_issues)}" if visual_issues else "") if visual_score is not None else None
    summary = generate_post_generation_summary(
        mode="site",
        files_touched=list(written_files.keys()),
        passed=final_passed,
        auto_recovered=result.get("auto_recovered_sections", []),
        user_instruction=prompt,
        is_edit=False,
        sections_completed=sections_completed,
        sections_planned=sections_planned,
        visual_check=visual_check,
        visual_score=visual_score,
        visual_issues=visual_issues,
        generation_quality=generation_quality,
        section_completion=section_completion,
        blocked_sections=blocked_diagnostics,
    )

    session.history.append({"role": "user", "content": prompt, "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")})
    session.history.append({
        "turn_id": 1,
        "role": "assistant",
        "summary": summary,
        "content": (f"Generation blocked after saving {len(written_files)} accepted files; {len(blocked_sections)} sections blocked."
                    if blocked_sections else f"Synthesized site with {len(written_files)} files across {len(sections)} sections."),
        "files_touched": list(written_files.keys()),
        "file_path": f"generated_components/{project_name}_{timestamp_slug}/",
        "filePath": f"generated_components/{project_name}_{timestamp_slug}/",
        "folder_name": f"{project_name}_{timestamp_slug}",
        "folderName": f"{project_name}_{timestamp_slug}",
        "full_path": str(session.workspace_dir),
        "fullPath": str(session.workspace_dir),
        "diffs": {},
        "checkpoint_id": chk_num,
        "visual_score": visual_score,
        "visual_issues": visual_issues,
        "validation": validation.to_dict(),
        "generation_complete": generation_complete,
        "section_completion": section_completion,
        "project_validation": project_validation,
        "generation_quality": generation_quality,
        "generation_scorecards": scorecards,
        "final_passed": final_passed,
        "blocked_sections": blocked_sections,
        "blocked_diagnostics": blocked_diagnostics,
        "completion_status": completion_status,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    })
    session.save()

    site_entry = {
        "task_id":              task_id,
        "session_id":           session.session_id,
        "mode":                 "site",
        "final_passed":         final_passed,
        "completion_status":   completion_status,
        "status":              "blocked" if blocked_sections else "completed",
        "blocked_sections":    blocked_sections,
        "blocked_diagnostics": blocked_diagnostics,
        "initial_passed":       None,
        "initial_validation_status": "unverified",
        "generation_complete":  generation_complete,
        "section_completion":   section_completion,
        "project_validation":   project_validation,
        "generation_quality":   generation_quality,
        "generation_scorecards": scorecards,
        "self_corrected":       result.get("self_corrected", False) or verify_res.self_corrected,
        "turns_used":           len(result.get("turn_logs", [])),
        "sections_completed":   sections_completed,
        "sections_planned":     sections_planned,
        "code":                 app_tsx_content,
        "files":                written_files,
        "diffs":                {},
        "summary":              summary,
        "symbol":               project_name,
        "prompt":               prompt,
        "style_preset":         style_preset,
        "stylePreset":          style_preset,
        "style_tokens":         style_tokens,
        "styleTokens":          style_tokens,
        "context_tokens":       getattr(session, "context_tokens", 0) or getattr(_runner, "last_context_tokens", 0),
        "contextTokens":        getattr(session, "context_tokens", 0) or getattr(_runner, "last_context_tokens", 0),
        "max_context_tokens":   ModelRuntimeConfig.get_max_seq_length(),
        "maxContextTokens":     ModelRuntimeConfig.get_max_seq_length(),
        "file_path":            f"generated_components/{project_name}_{timestamp_slug}/",
        "filePath":             f"generated_components/{project_name}_{timestamp_slug}/",
        "folder_name":          f"{project_name}_{timestamp_slug}",
        "folderName":           f"{project_name}_{timestamp_slug}",
        "full_path":            str(session.workspace_dir),
        "fullPath":             str(session.workspace_dir),
        "checkpoints_count":    len(session.checkpoints),
        "visual_score":         visual_score,
        "visual_score_before":  verify_res.visual_score_before,
        "visual_score_after":   verify_res.visual_score_after,
        "visual_score_best":    verify_res.visual_score_best,
        "visual_issues":        visual_issues,
        "validation":           validation.to_dict(),
        "interaction_validation": interaction_validation.to_dict() if hasattr(interaction_validation, "to_dict") else interaction_validation,
        "visual_validation":    visual_validation.to_dict() if hasattr(visual_validation, "to_dict") else visual_validation,
        "build_state":          session.build_state,
        "preview":              session.preview,
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

@app.route("/assets/<path:filename>")
def serve_assets(filename):
    return send_from_directory(str(STATIC_DIR / "assets"), filename)

@app.route("/api/status")
def status():
    from agent.config import ModelRuntimeConfig
    loaded = _runner is not None and _model_status in {"ready", "busy"} and _loaded_model_info is not None
    fp_info = _loaded_model_info if loaded else {}
    loaded_path = str(Path(_runner.model_path).resolve()) if loaded else None
    try:
        promotion = json.loads(_PROMOTED_PTR.read_text(encoding="utf-8")) if _PROMOTED_PTR.is_file() else {}
    except (OSError, ValueError):
        promotion = {}
    return jsonify({
        "model_status": _model_status,
        "model_loaded": loaded,
        "loaded_model_path": loaded_path,
        "configured_model_path": MODEL_PATH,
        "adapter_compatible": fp_info.get("adapter_compatible") if loaded else None,
        "gpu_ready": fp_info.get("gpu_ready") if loaded else False,
        "promotion_gate_status": promotion.get("gate_status", "UNPROMOTED"),
        "queue_depth": _generation_queue.qsize(),
        "project_websocket_ready": bool(_project_socket_server and _project_socket_server.ready),
        "project_websocket_url": (
            f"ws://{os.environ.get('HOST', '127.0.0.1')}:{_project_socket_server.port}/ws/projects"
            if _project_socket_server and _project_socket_server.ready else None
        ),
        "max_context_tokens": ModelRuntimeConfig.get_max_seq_length(),
        "maxContextTokens": ModelRuntimeConfig.get_max_seq_length(),
        "model_name": fp_info.get("model_name"),
        "modelName": fp_info.get("model_name"),
        "model_path": loaded_path,
        "modelPath": loaded_path,
        "base_model": fp_info.get("base_model"),
        "base_fingerprint": fp_info.get("base_fingerprint"),
        "baseFingerprint": fp_info.get("base_fingerprint"),
        "adapter_fingerprint": fp_info.get("adapter_fingerprint"),
        "adapterFingerprint": fp_info.get("adapter_fingerprint"),
        "is_qwen3_architecture": fp_info.get("is_qwen3_architecture") if loaded else None,
        "mock": False,
    })

@app.route("/api/generation/<task_id>/status", methods=["GET"])
@app.route("/generation/<task_id>/status", methods=["GET"])
@app.route("/api/task/<task_id>/status", methods=["GET"])
@app.route("/api/tasks/<task_id>/status", methods=["GET"])
def generation_task_status(task_id):
    """Fallback status endpoint allowing clients to verify job status if SSE drops."""
    if task_id in cancelled_tasks:
        res = _get_task_result(task_id)
        return jsonify({
            "task_id": task_id,
            "status": "cancelled",
            "data": res,
        })
    res = _get_task_result(task_id)
    if res:
        status_val = res.get("status", "completed") if isinstance(res, dict) else "completed"
        return jsonify({
            "task_id": task_id,
            "status": status_val,
            "data": res,
        })
    if _current_task and _current_task.get("task_id") == task_id:
        return jsonify({
            "task_id": task_id,
            "status": "running",
            "mode": _current_task.get("mode", "component"),
        })
    with _generation_queue.mutex:
        for idx, item in enumerate(_generation_queue.queue):
            if item.get("task_id") == task_id or item.get("taskId") == task_id:
                return jsonify({
                    "task_id": task_id,
                    "taskId": task_id,
                    "status": "queued",
                    "position": idx + 1,
                })
    for pid, q_list in _project_queued_prompts.items():
        for idx, item in enumerate(q_list):
            if isinstance(item, dict) and (item.get("taskId") == task_id or item.get("task_id") == task_id):
                return jsonify({
                    "task_id": task_id,
                    "taskId": task_id,
                    "status": "queued",
                    "position": idx + 1,
                    "project_id": pid,
                })
    return jsonify({
        "task_id": task_id,
        "taskId": task_id,
        "status": "not_found",
    }), 404

# Track recent requests for deduplication (prompt_hash -> (task_id, timestamp))
_recent_requests: dict[str, tuple[str, float]] = {}

@app.route("/api/generate", methods=["POST"])
def generate():
    if _model_status == "loading":
        return jsonify({"error": "Model is still loading, please wait."}), 503
    if _model_status == "error":
        return jsonify({"error": "Model failed to load. Check server logs."}), 503
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
                "taskId": existing_task_id,
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

        is_project_busy = (
            (_current_task and (_current_task.get("session_id") == req_session_id or _current_task.get("project_id") == req_session_id))
            or bool(_project_queued_prompts.get(req_session_id))
        )
        if is_project_busy:
            res = _dispatch_prompt_queue(existing_session.session_id, prompt, options=data)
            return jsonify({
                "task_id": res["taskId"],
                "taskId": res["taskId"],
                "session_id": existing_session.session_id,
                "symbol": existing_session.title,
                "mode": existing_session.mode,
                "is_follow_up": True,
                "status": "queued",
                "position": res["position"],
                "queue_position": res["position"],
            })

        task_id = str(uuid.uuid4())
        _recent_requests[prompt_hash] = (task_id, now)
        q = TaskEventEmitter(task_id, project_id=existing_session.session_id)
        _register_task_queue(task_id, q)
        if data.get("max_tokens") is not None:
            allocated_tokens = int(data["max_tokens"])
            budget_dict = {"tier": "custom", "allocated_tokens": allocated_tokens}
        else:
            factors = extract_complexity_factors(prompt=prompt, task_mode=existing_session.mode, target_symbol=existing_session.title)
            budget = estimate_output_budget(factors)
            allocated_tokens = budget.clamped_tokens
            budget_dict = budget.to_dict()

        _generation_queue.put({
            "task_id":      task_id,
            "session_id":   existing_session.session_id,
            "is_follow_up": True,
            "mode":         existing_session.mode,
            "prompt":       prompt,
            "symbol":       existing_session.title,
            "max_tokens":   allocated_tokens,
            "token_budget": budget_dict,
        })
        return jsonify({
            "task_id": task_id,
            "taskId": task_id,
            "session_id": existing_session.session_id,
            "symbol": existing_session.title,
            "mode": existing_session.mode,
            "is_follow_up": True,
            "status": "queued" if _generation_queue.qsize() > 1 or _current_task else "running",
            "position": _generation_queue.qsize(),
            "queue_position": _generation_queue.qsize(),
        })

    # ── Intent classification: site vs component ───────────────────────────
    # The composer's Full Site / Component toggle arrives as "mode"; an explicit
    # choice outranks the keyword classifier.
    user_intent = data.get("intent") or (data.get("mode") if data.get("mode") in ("site", "component") else None)
    if user_intent:
        intent = user_intent.lower()
        intent_conf = 1.0
    else:
        intent, intent_conf = _classify_intent_with_confidence(prompt)

    task_id = str(uuid.uuid4())
    _recent_requests[prompt_hash] = (task_id, now)
    q = TaskEventEmitter(task_id)
    _register_task_queue(task_id, q)

    if intent == "site":
        extracted = _extract_project_name(prompt)
        raw_name = (data.get("symbol") or "").strip()
        if not raw_name or raw_name in ("Cards", "Component", "MySite") or (extracted and extracted != "MySite" and raw_name.lower() not in prompt.lower()):
            raw_name = extracted or raw_name
        project_name = _sanitize_identifier(raw_name, default="MySite")

        style_tokens = data.get("styleTokens") or data.get("style_tokens")
        style_preset = data.get("stylePreset") or data.get("style_preset")
        session = session_manager.create_session(
            title=project_name,
            mode="site",
            prompt=prompt,
            style_tokens=style_tokens,
            style_preset=style_preset,
        )
        q.project_id = session.session_id
        event_bus.bind_task_to_project(task_id, session.session_id)

        if data.get("max_tokens") is not None:
            allocated_tokens = int(data["max_tokens"])
            budget_dict = {"tier": "custom", "allocated_tokens": allocated_tokens}
        else:
            factors = extract_complexity_factors(prompt=prompt, task_mode="site", target_symbol=project_name)
            budget = estimate_output_budget(factors)
            allocated_tokens = budget.clamped_tokens
            budget_dict = budget.to_dict()

        _generation_queue.put({
            "task_id":      task_id,
            "session_id":   session.session_id,
            "mode":         "site",
            "prompt":       prompt,
            "symbol":       project_name,
            "max_turns":    int(data.get("max_turns", 10)),
            "max_tokens":   allocated_tokens,
            "token_budget": budget_dict,
            "site_token_limit": int(data["max_tokens"]) if data.get("max_tokens") is not None else None,
            "strategy":     data.get("strategy"),
            "style_tokens": style_tokens,
            "styleTokens":  style_tokens,
            "style_preset": style_preset,
            "stylePreset":  style_preset,
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
        q.project_id = session.session_id
        event_bus.bind_task_to_project(task_id, session.session_id)

        if data.get("max_tokens") is not None:
            allocated_tokens = int(data["max_tokens"])
            budget_dict = {"tier": "custom", "allocated_tokens": allocated_tokens}
        else:
            factors = extract_complexity_factors(prompt=prompt, task_mode="component", target_symbol=symbol)
            budget = estimate_output_budget(factors)
            allocated_tokens = budget.clamped_tokens
            budget_dict = budget.to_dict()

        _generation_queue.put({
            "task_id":      task_id,
            "session_id":   session.session_id,
            "mode":         "component",
            "prompt":       prompt,
            "symbol":       symbol,
            "test_code":    test_code,
            "max_turns":    int(data.get("max_turns", 5)),
            "max_tokens":   allocated_tokens,
            "token_budget": budget_dict,
        })

        return jsonify({
            "task_id": task_id,
            "session_id": session.session_id,
            "symbol": symbol,
            "mode": "component",
            "intent_confidence": intent_conf,
            "queue_position": _generation_queue.qsize()
        })


@app.route("/api/style-presets", methods=["GET"])
def list_style_presets():
    """Returns structured style presets available for generation."""
    try:
        from agent.style_ingest import get_available_style_presets
        presets = get_available_style_presets()
    except Exception:
        try:
            from style_ingest import get_available_style_presets
            presets = get_available_style_presets()
        except Exception:
            presets = [
                {"id": "auto", "label": "Auto", "description": "Smart domain-tailored aesthetic", "isDefault": True},
                {"id": "editorial", "label": "Editorial", "description": "Typographic hierarchy & refined spacing"},
                {"id": "brutalist", "label": "Brutalist", "description": "Bold high-contrast borders & geometric layouts"},
                {"id": "minimal", "label": "Minimal", "description": "Ultra-clean whitespace & subtle hairline clarity"},
                {"id": "technical", "label": "Technical", "description": "Developer dark theme & monospace metrics"},
                {"id": "luxury", "label": "Luxury", "description": "Warm alabaster, bronze & serif typography"},
                {"id": "experimental", "label": "Experimental", "description": "Dynamic aurora gradients & luminous glass"},
                {"id": "custom", "label": "Custom", "description": "User-defined :root tokens"},
            ]
    return jsonify({
        "presets": presets,
        "default": "auto",
    })


# ── Session & Checkpoint Endpoints ──────────────────────────────────────────

@app.route("/api/sessions", methods=["GET"])
@app.route("/api/projects", methods=["GET"])
def list_sessions():
    """Returns all active and persisted agentic chat sessions / projects."""
    return jsonify({"sessions": session_manager.list_sessions(), "projects": session_manager.list_sessions()})


@app.route("/api/sessions/<session_id>", methods=["GET"])
@app.route("/api/projects/<session_id>", methods=["GET"])
def get_session_info(session_id):
    """Returns complete session / project history, checkpoints, build state, preview, and files."""
    s = session_manager.get_session(session_id)
    if not s:
        return jsonify({"error": "Session not found"}), 404
    data = s.to_dict()
    active = _current_task
    data["active_task_id"] = active.get("task_id") if active and (active.get("session_id") == session_id or active.get("project_id") == session_id) else None
    resp = dict(data)
    resp["session"] = data
    resp["project"] = data
    return jsonify(resp)


@app.route("/api/sessions/<session_id>/revert/<int:turn_num>", methods=["POST"])
@app.route("/api/projects/<session_id>/revert/<int:turn_num>", methods=["POST"])
def revert_session_checkpoint(session_id, turn_num):
    """Reverts session files to a previous checkpoint, updates preview and build state."""
    s = session_manager.get_session(session_id)
    if not s:
        return jsonify({"error": "Session not found"}), 404
    ok = s.revert_to_checkpoint(turn_num)
    if not ok:
        return jsonify({"error": f"Checkpoint #{turn_num} could not be restored."}), 400
    repaired = repair_missing_critical_files(s.workspace_dir, s.title, s.mode)
    if repaired:
        print(f"[Checkpoint] Repaired missing critical file(s) on revert: {repaired}")
    current_files = s.get_current_files()
    val = _validate_workspace(s.workspace_dir)
    s.last_validation = val
    s.build_state = val.to_dict()
    s.save()
    return jsonify({
        "status": "reverted",
        "success": True,
        "turnId": turn_num,
        "turn_num": turn_num,
        "files": current_files,
        "build_state": s.build_state,
        "preview": s.preview,
    })


@app.route("/api/projects/<session_id>/framework-config", methods=["POST"])
@app.route("/api/sessions/<session_id>/framework-config", methods=["POST"])
def framework_config_endpoint(session_id):
    """
    Blueprint lifecycle: explicitFrameworkChange() API endpoint.
    Applies explicit project configuration modifications (aliases, Tailwind, tsconfig, packages).
    """
    s = session_manager.get_session(session_id)
    if not s:
        return jsonify({"error": "Session not found"}), 404
    data = request.get_json(silent=True) or {}
    action = data.get("action")
    if not action:
        return jsonify({"error": "Missing 'action' in request body"}), 400
    try:
        res = explicit_framework_change(s.workspace_dir, action, data.get("payload"))
        s.create_checkpoint(f"Framework config: {action}")
        return jsonify(res)
    except Exception as e:
        return jsonify({"error": str(e), "success": False}), 400


@app.route("/api/projects/<session_id>/3d/<action_name>", methods=["GET", "POST"])
@app.route("/api/sessions/<session_id>/3d/<action_name>", methods=["GET", "POST"])
def run_project_3d_tool(session_id: str, action_name: str):
    """Executes 3D diagnostic tool on session workspace."""
    s = session_manager.get_session(session_id)
    if not s:
        return jsonify({"error": "Session not found"}), 404
    payload = request.get_json(silent=True) or {}
    try:
        from agent.three_d_tools import run_three_d_tool
        result = run_three_d_tool(action_name, s.workspace_dir, payload)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e), "success": False}), 400


@app.route("/api/projects/<session_id>/file", methods=["PATCH", "PUT", "POST"])
@app.route("/api/sessions/<session_id>/file", methods=["PATCH", "PUT", "POST"])
def save_project_file(session_id):
    """
    Saves a manual file edit from the Monaco code editor.
    Lifecycle:
      1. Path traversal security check via resolve_project_path
      2. Capture pre-task snapshot (enabling rollback)
      3. Write new file content to disk
      4. Execute 4-gate verification (_validate_workspace)
      5. Commit checkpoint with blob store and Git commit
      6. Append history turn record
      7. Return updated validation state and files
    """
    s = session_manager.get_session(session_id)
    if not s:
        return jsonify({"error": "Session not found"}), 404

    data = request.get_json(silent=True) or {}
    rel_path = data.get("file")
    content = data.get("content")

    if not rel_path or content is None:
        return jsonify({"error": "Missing 'file' or 'content' in request body"}), 400

    try:
        dest_path = resolve_project_path(s.workspace_dir, rel_path, allow_package_json=True)
    except PermissionError as pe:
        return jsonify({"error": str(pe)}), 403

    # 1. Capture pre-task snapshot before overwriting
    try:
        s.create_pre_task_snapshot(f"Manual edit: {rel_path}")
    except Exception as e:
        print(f"[SaveFile] Warning: pre-task snapshot failed: {e}")

    # 2. Write file to disk
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    dest_path.write_text(content, encoding="utf-8")

    # 3. Execute workspace validation
    val = _validate_workspace(s.workspace_dir)
    s.last_validation = val
    s.build_state = val.to_dict()

    # 4. Commit task success checkpoint
    chk = s.commit_task(f"Manual edit: {rel_path}", files_touched=[rel_path])
    turn_num = chk.get("turn_num", len(s.checkpoints))

    # 5. Append turn to history
    s.history.append({
        "turn_id": turn_num,
        "role": "user",
        "summary": f"Manually edited `{rel_path}`",
        "files_touched": [rel_path],
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "validation": val.to_dict(),
    })
    s.save()

    # 6. Notify event bus / WebSocket if subscribed
    try:
        pid = s.project_id or s.session_id
        event_bus.publish(
            f"manual_edit_{int(time.time()*1000)}",
            AgentEvent(
                type="file.modified",
                timestamp=time.time(),
                project_id=pid,
                data={"file": rel_path, "path": rel_path},
            ),
            project_id=pid,
        )
        event_bus.publish(
            f"manual_edit_{int(time.time()*1000)}",
            AgentEvent(
                type="build.result",
                timestamp=time.time(),
                project_id=pid,
                data=s.build_state,
            ),
            project_id=pid,
        )
    except Exception as eb_err:
        print(f"[SaveFile] Event bus notification notice: {eb_err}")

    return jsonify({
        "success": True,
        "file": rel_path,
        "turnId": turn_num,
        "validation": val.to_dict(),
        "build_state": s.build_state,
        "files": s.get_current_files(),
        "preview": s.preview,
    })


@app.route("/api/projects/<session_id>/file", methods=["DELETE"])
@app.route("/api/sessions/<session_id>/file", methods=["DELETE"])
def delete_project_file(session_id):
    """
    Deletes a file from the project workspace.
    Lifecycle:
      1. Path traversal security check via resolve_project_path
      2. Capture pre-task snapshot (enabling rollback)
      3. Unlink file if exists
      4. Execute 4-gate verification (_validate_workspace)
      5. Commit checkpoint with blob store and Git commit
      6. Append history turn record
      7. Return updated validation state and files
    """
    s = session_manager.get_session(session_id)
    if not s:
        return jsonify({"error": "Session not found"}), 404

    data = request.get_json(silent=True) or {}
    rel_path = data.get("file") or request.args.get("file")

    if not rel_path:
        return jsonify({"error": "Missing 'file' in request"}), 400

    try:
        dest_path = resolve_project_path(s.workspace_dir, rel_path, allow_package_json=False)
    except PermissionError as pe:
        return jsonify({"error": str(pe)}), 403

    if not dest_path.exists():
        return jsonify({"error": f"File '{rel_path}' not found"}), 404

    # 1. Capture pre-task snapshot before deleting
    try:
        s.create_pre_task_snapshot(f"Delete file: {rel_path}")
    except Exception as e:
        print(f"[DeleteFile] Warning: pre-task snapshot failed: {e}")

    # 2. Delete file
    try:
        dest_path.unlink()
    except Exception as e:
        return jsonify({"error": f"Failed to delete file: {e}"}), 500

    # 3. Execute workspace validation
    val = _validate_workspace(s.workspace_dir)
    s.last_validation = val
    s.build_state = val.to_dict()

    # 4. Commit task success checkpoint
    chk = s.commit_task(f"Delete file: {rel_path}", files_touched=[rel_path])
    turn_num = chk.get("turn_num", len(s.checkpoints))

    # 5. Append turn to history
    s.history.append({
        "turn_id": turn_num,
        "role": "user",
        "summary": f"Deleted `{rel_path}`",
        "files_touched": [rel_path],
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "validation": val.to_dict(),
    })
    s.save()

    return jsonify({
        "success": True,
        "file": rel_path,
        "turnId": turn_num,
        "validation": val.to_dict(),
        "build_state": s.build_state,
        "files": s.get_current_files(),
        "preview": s.preview,
    })



@app.route("/api/sessions/<session_id>/diff", methods=["GET"])
@app.route("/api/projects/<session_id>/diff", methods=["GET"])
@app.route("/api/sessions/<session_id>/diff/<int:turn_id>", methods=["GET"])
@app.route("/api/projects/<session_id>/diff/<int:turn_id>", methods=["GET"])
def get_turn_diff(session_id, turn_id=None):
    """Retrieves file diffs for a specific turn in a session with canonical structure:

    {
        "turnId": 3,
        "files": {
            "src/components/Hero.tsx": {
                "before": "...",
                "after": "...",
                "patch": "..."
            }
        }
    }
    """
    s = session_manager.get_session(session_id)
    if not s:
        return jsonify({"error": "Session not found"}), 404

    # Default to latest turn if not explicitly passed
    if turn_id is None:
        if s.checkpoints:
            latest_chk = s.checkpoints[-1]
            turn_id = latest_chk.get("turn_num") or latest_chk.get("id") or len(s.checkpoints)
        elif s.history:
            turn_id = len(s.history)
        else:
            turn_id = 1

    turn = next((h for h in s.history if h.get("turn_id") == turn_id or h.get("turn") == turn_id or h.get("turn_num") == turn_id), None)
    if not turn and 1 <= turn_id <= len(s.history):
        turn = s.history[turn_id - 1]

    chk = next((c for c in s.checkpoints if c.get("turn_num") == turn_id or c.get("id") == turn_id), None)
    if not chk and 1 <= turn_id <= len(s.checkpoints):
        chk = s.checkpoints[turn_id - 1]

    # If neither turn nor checkpoint exists, check for baseline initial files
    curr_files_probe = s.get_current_files()
    if not turn and not chk:
        if turn_id == 1 and curr_files_probe:
            files_dict = {
                fpath: {
                    "before": "",
                    "after": content,
                    "patch": compute_file_diff(fpath, "", content),
                }
                for fpath, content in curr_files_probe.items()
            }
            return jsonify({
                "turnId": 1,
                "turn_id": 1,
                "files": files_dict,
                "summary": "Initial baseline workspace files",
                "files_touched": list(files_dict.keys()),
                "original_files": {p: "" for p in files_dict.keys()},
                "modified_files": {p: v["after"] for p, v in files_dict.items()},
                "diffs": {p: v["patch"] for p, v in files_dict.items()},
            })
        return jsonify({"error": f"Turn #{turn_id} not found."}), 404

    # Determine files touched and diff patches
    files_touched_explicit: Optional[List[str]] = None
    if turn and "files_touched" in turn:
        files_touched_explicit = list(turn.get("files_touched") or [])
    elif chk and "changed_files" in chk:
        files_touched_explicit = list(chk.get("changed_files") or [])
    elif chk and "changed_blobs" in chk:
        files_touched_explicit = list(chk.get("changed_blobs", {}).keys())

    diffs_map = {}
    if turn and turn.get("diffs"):
        diffs_map = dict(turn.get("diffs", {}))
    elif chk and chk.get("diffs"):
        diffs_map = dict(chk.get("diffs", {}))

    # Retrieve curr_files and prev_files from checkpoint snapshots or workspace
    curr_files: Dict[str, str] = {}
    prev_files: Dict[str, str] = {}

    if chk:
        try:
            curr_files = s.snapshot_manager.get_checkpoint_files(chk)
        except Exception:
            curr_files = {}

        chk_id = chk.get("turn_num") or chk.get("id") or turn_id
        prev_chk = next(
            (c for c in reversed(s.checkpoints) if (c.get("turn_num") or c.get("id", 0)) < chk_id),
            None
        )
        if prev_chk:
            try:
                prev_files = s.snapshot_manager.get_checkpoint_files(prev_chk)
            except Exception:
                prev_files = {}
    else:
        curr_files = s.get_current_files()

    if files_touched_explicit is not None:
        files_touched = files_touched_explicit
    elif diffs_map:
        files_touched = list(diffs_map.keys())
    elif turn_id == 1 and curr_files:
        files_touched = list(curr_files.keys())
    else:
        files_touched = []

    files_dict: Dict[str, Dict[str, str]] = {}
    for fpath in files_touched:
        before_content = prev_files.get(fpath, "")
        after_content = curr_files.get(fpath, "")
        if not after_content and (s.workspace_dir / fpath).exists():
            try:
                after_content = (s.workspace_dir / fpath).read_text(encoding="utf-8")
            except Exception:
                after_content = ""

        patch_content = diffs_map.get(fpath)
        if not patch_content:
            patch_content = compute_file_diff(fpath, before_content, after_content)

        files_dict[fpath] = {
            "before": before_content,
            "after": after_content,
            "patch": patch_content,
        }

    summary_text = turn.get("summary", "") if turn else (chk.get("summary", "") if chk else "")
    if isinstance(summary_text, dict):
        summary_text = json.dumps(summary_text)

    return jsonify({
        "turnId": turn_id,
        "turn_id": turn_id,
        "files": files_dict,
        "summary": summary_text,
        "files_touched": list(files_dict.keys()),
        "original_files": {p: v["before"] for p, v in files_dict.items()},
        "modified_files": {p: v["after"] for p, v in files_dict.items()},
        "diffs": {p: v["patch"] for p, v in files_dict.items()},
    })


@app.route("/preview/<session_id>")
@app.route("/preview/<session_id>/")
@app.route("/preview/<session_id>/<path:filename>")
def preview_session_page(session_id, filename="index.html"):
    """Redirect to an isolated production preview, rebuilding edited source."""
    s = session_manager.get_session(session_id)
    if not s or not s.workspace_dir.exists():
        return "<h3 style='font-family:sans-serif;padding:2rem;'>Preview workspace not yet generated.</h3>", 404

    # Ensure runner is scaffolded if index.html or critical runner files are missing
    if not (s.workspace_dir / "index.html").exists():
        repair_missing_critical_files(s.workspace_dir, s.title, s.mode)

    try:
        url = preview_manager.start(session_id, workspace_dir=s.workspace_dir)
    except Exception as e:
        print(f"[Preview] Could not build isolated preview for {session_id}: {e}")
        return "<h3>Preview build failed. Check the build diagnostics.</h3>", 503

    if url:
        if filename and filename not in ("index.html", ""):
            return redirect(f"{url.rstrip('/')}/{filename}")
        return redirect(url)

    # Fallback to static file serving if Vite server could not start
    if filename == "index.html" and (s.workspace_dir / "static-preview.html").exists():
        filename = "static-preview.html"
    return send_from_directory(str(s.workspace_dir), filename)


# ── Project WebSocket Endpoint (/ws/projects/:projectId) ─────────────────────

def _handle_project_websocket(ws, project_id):
    """
    Bidirectional Project WebSocket (/ws/projects/:projectId).
    Blueprint transport supporting:
    - client -> task.start
    - client -> task.cancel
    - client -> prompt.queue
    - client -> preview.selection
    - server -> agent.status
    - server -> activity.*
    - server -> file.*
    - server -> command.*
    - server -> build.result
    - server -> preview.ready
    - server -> task.*

    Includes monotonic sequence numbers (seq) and replay after lastEventId.
    """
    # 1. Origin verification (defense against CSWSH)
    origin = request.headers.get("Origin")
    if origin:
        allowed_hosts = {"localhost", "127.0.0.1", os.environ.get("HOST", "127.0.0.1")}
        parsed = urllib.parse.urlparse(origin)
        expected_origin = request.host_url.rstrip("/").lower()
        if parsed.hostname not in allowed_hosts or origin.rstrip("/").lower() != expected_origin:
            print(f"[Project WS] Rejected WebSocket from disallowed origin: {origin}")
            return

    # 2. Check query parameter lastEventId for initial sync
    last_event_id = request.args.get("lastEventId", type=int)

    # 3. Subscribe to project event bus channel
    event_queue = event_bus.subscribe_project(project_id, last_event_id=last_event_id)
    stop_event = threading.Event()
    send_lock = threading.Lock()

    def _safe_send(payload_dict: Dict[str, Any]) -> bool:
        with send_lock:
            try:
                ws.send(json.dumps(payload_dict))
                return True
            except Exception as exc:
                app.logger.warning("Project WebSocket send failed for %s: %s", project_id, exc)
                return False

    # Send initial connection acknowledgment
    from agent.config import ModelRuntimeConfig
    latest_seq = event_bus.get_latest_seq(project_id)
    _safe_send({
        "type": "connection.ready",
        "project_id": project_id,
        "latest_seq": latest_seq,
        "replayed_from": last_event_id,
        "max_context_tokens": ModelRuntimeConfig.get_max_seq_length(),
        "maxContextTokens": ModelRuntimeConfig.get_max_seq_length(),
    })

    # 4. Outbound event forwarder thread
    def _forwarder():
        while not stop_event.is_set():
            try:
                msg = event_queue.get(timeout=0.5)
                if not _safe_send(msg):
                    stop_event.set()
                    break
            except queue.Empty:
                continue
            except Exception as exc:
                app.logger.exception("Project WebSocket forwarder failed for %s: %s", project_id, exc)
                stop_event.set()
                break

    forwarder_thread = threading.Thread(target=_forwarder, daemon=True)
    forwarder_thread.start()

    # 5. Inbound client message loop
    try:
        while not stop_event.is_set():
            try:
                raw = ws.receive(timeout=1.0)
            except Exception as exc:
                app.logger.warning("Project WebSocket receive failed for %s: %s", project_id, exc)
                break

            if raw is None:
                continue

            try:
                data = json.loads(raw) if isinstance(raw, str) else raw
            except Exception:
                _safe_send({"type": "error", "error": "Invalid JSON payload", "project_id": project_id})
                continue

            msg_type = data.get("type", "")

            # Sync / subscribe request: replay events after lastEventId
            if msg_type in ("sync", "subscribe.events"):
                req_last_id = data.get("lastEventId", 0)
                replays = event_bus.get_events_after(project_id, req_last_id)
                for item in replays:
                    _safe_send(item)

            elif msg_type == "task.start":
                prompt = data.get("prompt", "").strip()
                if not prompt:
                    _safe_send({"type": "error", "error": "Prompt is required for task.start", "project_id": project_id})
                else:
                    mode = data.get("mode")
                    options = data.get("options", {})
                    res = _dispatch_task_start(project_id, prompt, mode=mode, options=options)
                    _safe_send({"type": "task.acknowledged", "task_id": res.get("task_id"), "project_id": project_id, "data": res})

            elif msg_type == "task.cancel":
                reason = data.get("reason", "user_cancelled")
                res = _dispatch_task_cancel(project_id, reason=reason)
                _safe_send({"type": "task.cancelled", "project_id": project_id, "data": res})

            elif msg_type == "prompt.queue":
                prompt = data.get("prompt", "").strip()
                if not prompt:
                    _safe_send({"type": "error", "error": "Prompt is required for prompt.queue", "project_id": project_id})
                else:
                    res = _dispatch_prompt_queue(project_id, prompt, options=data.get("options"))
                    _safe_send({
                        "type": "prompt.queued",
                        "project_id": project_id,
                        "taskId": res.get("taskId") or res.get("task_id"),
                        "task_id": res.get("taskId") or res.get("task_id"),
                        "status": "queued",
                        "position": res.get("position"),
                        "queue_position": res.get("position"),
                        "data": res,
                    })

            elif msg_type == "preview.selection":
                selection = data.get("selection") or {k: v for k, v in data.items() if k not in ("type", "project_id")}
                res = _dispatch_preview_selection(project_id, selection)
                _safe_send({"type": "preview.selection_received", "project_id": project_id, "data": res})

            elif msg_type == "ping":
                _safe_send({"type": "pong", "timestamp": time.time(), "project_id": project_id})

    finally:
        stop_event.set()
        event_bus.unsubscribe_project(project_id, event_queue)
        forwarder_thread.join(timeout=1.0)


@sock.route("/ws/projects/<project_id>")
def project_websocket(ws, project_id):
    """Bidirectional Project WebSocket endpoint."""
    return _handle_project_websocket(ws, project_id)


@sock.route("/ws/sessions/<project_id>")
def session_websocket(ws, project_id):
    """Compatibility alias for /ws/projects/:projectId."""
    return _handle_project_websocket(ws, project_id)


@app.route("/api/stream/<task_id>")
def stream(task_id):
    q = task_queues.get(task_id)
    last_event_id = request.headers.get("Last-Event-ID")
    try:
        replay_q = event_bus.subscribe(task_id, int(last_event_id)) if last_event_id else event_bus.subscribe(task_id)
    except (ValueError, TypeError):
        replay_q = event_bus.subscribe(task_id)
    cached_result = _get_task_result(task_id)
    is_active = (_current_task and _current_task.get("task_id") == task_id)
    if not is_active:
        with _generation_queue.mutex:
            for item in _generation_queue.queue:
                if item.get("task_id") == task_id:
                    is_active = True
                    break

    if q is None and cached_result is None and not is_active:
        return jsonify({"error": "Unknown or expired task_id"}), 404

    def generate_sse():
        # If task already completed, emit cached result event immediately
        if cached_result or task_id in task_results:
            res = cached_result or _get_task_result(task_id)
            if res:
                yield f"data: {json.dumps({'type': 'result', 'data': res})}\n\n"
            yield "data: {\"type\": \"done\"}\n\n"
            return

        try:
            while True:
                # If result was produced while reading, emit it
                latest_res = _get_task_result(task_id)
                if latest_res and (q is None or q.empty()):
                    yield f"data: {json.dumps({'type': 'result', 'data': latest_res})}\n\n"
                    yield "data: {\"type\": \"done\"}\n\n"
                    break

                if replay_q is None:
                    yield "data: {\"type\":\"heartbeat\"}\n\n"
                    time.sleep(1)
                    continue

                try:
                    msg = replay_q.get(timeout=3)
                except queue.Empty:
                    yield "data: {\"type\":\"heartbeat\"}\n\n"
                    continue

                if isinstance(msg, dict):
                    # EventBus subscriptions already contain typed envelopes.
                    # Re-conversion nests data twice and loses terminal results.
                    if "timestamp" not in msg or "data" not in msg:
                        converted = event_bus._convert_legacy_dict(msg, task_id)
                        msg = converted.to_dict()

                event_id = msg.get("seq") if isinstance(msg, dict) else None
                prefix = f"id: {event_id}\n" if event_id is not None else ""
                yield f"{prefix}data: {json.dumps(msg)}\n\n"

                if msg.get("type") in ("done", "task.completed") and (msg.get("type") == "done" or msg.get("done")):
                    break
        except (GeneratorExit, BrokenPipeError, ConnectionResetError):
            pass
        finally:
            event_bus.unsubscribe(task_id, replay_q)
            # Only clean up queue when task is completed or cancelled, NOT on transient client disconnect
            task_still_active = (_current_task and _current_task.get("task_id") == task_id)
            if not task_still_active and (cached_result or task_id in task_results):
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

    _r = globals().get("_runner")
    if _r and hasattr(_r, "stop_check"):
        _r.stop_check = lambda: True

    # Mark all currently active task IDs as cancelled so active generation loops bail early
    for tid in list(task_queues.keys()):
        cancelled_tasks.add(tid)
        if "_task_results" in globals():
            _task_results[tid] = {"status": "cancelled", "task_id": tid}
        elif "task_results" in globals():
            task_results[tid] = {"status": "cancelled", "task_id": tid}
        q = task_queues.get(tid)
        if q:
            try:
                q.put({"type": "cancelled", "text": "Generation aborted by user."})
                q.put({"type": "task.cancelled", "task_id": tid, "text": "Generation aborted by user."})
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
    if "_task_results" in globals():
        _task_results[task_id] = {"status": "cancelled", "task_id": task_id}
    elif "task_results" in globals():
        task_results[task_id] = {"status": "cancelled", "task_id": task_id}

    _r = globals().get("_runner")
    _curr = globals().get("_current_task")
    if _r and hasattr(_r, "stop_check") and (_curr is None or _curr.get("task_id") == task_id):
        _r.stop_check = lambda: True

    # Push a done signal immediately so the SSE stream closes on the client
    q = task_queues.get(task_id)
    if q:
        try:
            q.put({"type": "cancelled", "text": "Generation cancelled by user."})
            q.put({"type": "task.cancelled", "task_id": task_id, "text": "Generation cancelled by user."})
            q.put({"type": "done"})
        except Exception:
            pass

    _eb = globals().get("event_bus")
    if _eb:
        try:
            _eb.publish(
                task_id,
                AgentEvent(
                    type="task.cancelled",
                    task_id=task_id,
                    data={"task_id": task_id, "reason": "user_cancelled", "text": "Generation cancelled by user."},
                ),
            )
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


@app.route("/api/projects/<session_id>/export", methods=["GET"])
@app.route("/api/sessions/<session_id>/export", methods=["GET"])
@app.route("/api/projects/<session_id>/zip", methods=["GET"])
@app.route("/api/sessions/<session_id>/zip", methods=["GET"])
@app.route("/api/export/<session_id>", methods=["GET"])
def export_project_zip(session_id):
    """
    Exports the complete runnable project workspace as a clean ZIP archive.
    Includes:
      - src/
      - public/
      - package.json
      - vite.config.ts
      - tsconfig.json
      - index.html
      - all code, styles, and site assets
    Excludes:
      - node_modules/
      - dist/
      - .git/
      - .vite/
      - .snapshots/
      - Python cache directories (__pycache__, .pytest_cache)
      - temporary screenshots and visual-judge artifacts
      - session metadata not needed by the exported site
    """
    s = session_manager.get_session(session_id)
    if not s:
        return jsonify({"error": "Session/project not found"}), 404

    workspace_dir = Path(s.workspace_dir).resolve()
    if not workspace_dir.exists():
        return jsonify({"error": "Workspace directory does not exist"}), 404

    # Ensure critical runner scaffolding exists so the project builds after extraction
    repair_missing_critical_files(workspace_dir, s.title, s.mode)

    # Excluded directories
    EXCLUDE_DIRS = {
        "node_modules",
        "dist",
        "dist-ssr",
        ".git",
        ".vite",
        ".snapshots",
        "__pycache__",
        ".pytest_cache",
        ".turbo",
    }

    # Excluded file extensions
    EXCLUDE_FILE_EXTS = {
        ".pyc",
        ".pyo",
        ".pyd",
        ".log",
    }

    # Excluded specific metadata and temp files
    EXCLUDE_FILES = {
        "history.jsonl",
        "session.json",
        "task_log.txt",
        ".DS_Store",
        "thumbs.db",
        "Thumbs.db",
    }

    bio = io.BytesIO()
    with zipfile.ZipFile(bio, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(workspace_dir.rglob("*")):
            if not p.is_file():
                continue

            rel = p.relative_to(workspace_dir)
            rel_parts = rel.parts

            # Exclude directories
            if any(part in EXCLUDE_DIRS for part in rel_parts):
                continue

            # Exclude specific files or extensions
            if p.name in EXCLUDE_FILES or p.suffix.lower() in EXCLUDE_FILE_EXTS:
                continue

            # Exclude root/temporary screenshots and visual-judge artifacts
            name_lower = p.name.lower()
            if "visual_judge" in name_lower or "visual-judge" in name_lower:
                continue

            if ("screenshot" in name_lower or "judge" in name_lower) and (
                "public" not in rel_parts and "assets" not in rel_parts and "components" not in rel_parts
            ):
                continue

            rel_posix = rel.as_posix()
            try:
                zf.write(p, arcname=rel_posix)
            except Exception as e:
                print(f"[Export] Could not write {p} to zip: {e}")

    bio.seek(0)
    raw_title = s.title or s.session_id or "project"
    safe_title = re.sub(r'[^a-zA-Z0-9_\-]', '_', raw_title).strip('_') or "project"
    zip_filename = f"{safe_title}.zip"

    return send_file(
        bio,
        mimetype="application/zip",
        as_attachment=True,
        download_name=zip_filename,
    )


@app.route("/api/download/<task_id>")
def download(task_id):
    r = _get_task_result(task_id)
    if not r or not r.get("code"):
        # If task_id was mistakenly passed as a project/session ID, redirect to export
        s = session_manager.get_session(task_id)
        if s:
            return redirect(f"/api/projects/{task_id}/export")
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

@app.route("/api/shell-token", methods=["GET", "POST"])
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
    ticket = _mint_shell_ticket()
    host = os.environ.get("HOST", "127.0.0.1")
    return jsonify({
        "ticket": ticket,
        "token": ticket,
        "host": host,
        "port": 5001,
    })


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


threading.Thread(target=_worker, daemon=True).start()


if __name__ == "__main__":
    STATIC_DIR.mkdir(exist_ok=True)
    _start_shell_server()
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "5000"))
    from server.project_socket import ProjectSocketServer
    import atexit
    default_origins = [f"http://{name}:{number}" for name in ('127.0.0.1', 'localhost') for number in (port, 5173)]
    origins = os.environ.get('WORKBENCH_ORIGINS', ','.join(default_origins)).split(',')
    _project_socket_server = ProjectSocketServer(app, _handle_project_websocket, host=host,
        port=int(os.environ.get('PROJECT_WS_PORT', '5002')), origins=[item.strip().rstrip('/') for item in origins])
    _project_socket_server.start()
    atexit.register(_project_socket_server.stop)
    url = f"http://{host}:{port}"
    print(f"[Server] Starting ReactAgent SLM Web UI on {url}")

    if os.environ.get("NO_BROWSER") != "1":
        import threading
        import webbrowser
        threading.Timer(1.2, lambda: webbrowser.open(url)).start()

    app.run(host=host, port=port, debug=False, threaded=True)

