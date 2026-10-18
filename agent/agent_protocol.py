"""
agent_protocol.py - Action Space, System Contract, and Parsing Engine for Agentic SLMs
Supports Qwen3-4B (primary) and Qwen2.5-Coder-3B (legacy fallback) on local hardware (RTX 4050 6GB).

Design Principles:
1. Action-First Protocol: Supports JSON actions and XML tags without requiring hidden reasoning.
2. Smart Observation Pruning: Preserves primary failure headlines & accessible roles within the token budget.
3. Forgiving Parser: Robustly extracts actions, tool calls, and final answers.
4. Dual-mode protocol: write_component (single atom) and write_site (multi-file page composition).
5. Chat Template: Uses tokenizer.apply_chat_template() when a tokenizer is registered (Qwen3-native);
   falls back to hard-coded ChatML for offline/test contexts where no tokenizer is loaded.
"""

import json
import os
import re
import sys as _sys
import textwrap

# One module, two import names. Scripts that put agent/ on sys.path import this
# file as "agent_protocol"; package code imports "agent.agent_protocol". Without
# the alias each name gets its own module and its own registered tokenizer, so
# token counting silently falls back to the legacy template (audit A3).
for _alias in ("agent_protocol", "agent.agent_protocol"):
    _sys.modules.setdefault(_alias, _sys.modules[__name__])
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple, Union
try:
    from agent.edit_actions import EditFileAction, ReplaceHunk
except ImportError:
    from edit_actions import EditFileAction, ReplaceHunk

# ==============================================================================
# Unified Sequence Length Constants (Single Source of Truth)
# ==============================================================================
try:
    from agent.config import ModelRuntimeConfig
except (ImportError, ModuleNotFoundError):
    from config import ModelRuntimeConfig

DEFAULT_MAX_SEQ_LENGTH = ModelRuntimeConfig.get_max_seq_length()
DEFAULT_INFERENCE_MAX_SEQ_LENGTH = ModelRuntimeConfig.get_max_seq_length()
DEFAULT_MAX_NEW_TOKENS = ModelRuntimeConfig.get_default_max_new_tokens()


# ==============================================================================
# 1. System Prompt Contract
# ==============================================================================

AGENT_SYSTEM_PROMPT = """You are an expert autonomous React, TypeScript, and CSS coding agent.
Your objective is to write, test, and self-correct React components until they pass all type checks and Vitest/Testing Library test suites.

You interact with an automated testing environment by emitting actions directly:

1. <tool_call name="write_component">
<tsx>
// Complete React + TypeScript component implementation
</tsx>
<css>
/* Optional CSS / CSS module code */
</css>
</tool_call>
Writes the component and optional CSS module to the workspace. The testing harness automatically runs TypeScript compilation (tsc --noEmit) and the Vitest test suite, returning results in an <observation>.

2. <tool_call name="read_file">
<path>src/components/Header.tsx</path>
</tool_call>
Reads the content of an existing file in the project.

3. <tool_call name="inspect_dependencies" />
Inspects the installed packages and devDependencies in package.json to verify what libraries actually exist.

4. 3D Capability Tools:
   - <tool_call name="install_package">{"package": "@react-three/fiber"}</tool_call>
     Installs an npm dependency into the project workspace.
   - <tool_call name="get_webgl_errors" />
     Inspects WebGL context availability, shader syntax, and context loss handlers.
   - <tool_call name="get_scene_metadata" />
     Inspects 3D scene architecture: camera, lights, DPR, frameloop, and useFrame allocations.
   - <tool_call name="get_asset_manifest" />
     Scans 3D models (GLTF/GLB), textures, HDR environments, and Suspense fallback coverage.

5. <finish>
Brief summary of your verified solution.
</finish>
Call this ONLY when you have verified that all tests pass, or when the task is fully complete.

OPERATING GUIDELINES:
- Every turn, emit your action directly: either ONE <tool_call> or <finish>. Do not output raw hidden reasoning or thought wrappers.
- Write clean, type-safe TypeScript. Use proper React hooks, accessibility attributes (aria-*, role), and event handlers.
- Put all types, interfaces, and helper utilities in the single <tsx> block. Do not import third-party npm packages (e.g. lodash) or non-existent local files.
- Write only production React component code in <tsx>. Do NOT import test frameworks or runners ('vitest', '@testing-library', 'jest') inside <tsx>.
- SELF-CONTAINED IMPLEMENTATION & NO-INVENTION RULE:
  Unless a tool confirms that an identifier, package, or file exists: DO NOT INVENT IT.
  * Never import uninstalled third-party packages (e.g. 'lodash', 'react-use', '@tanstack/react-table', 'react-hook-form', 'use-undo', 'lucide-react', 'react-router-dom', 'date-fns').
  * Never import from imagined local helper files or paths (e.g. '@/hooks/useCart', './utils', '../types').
  * Implement all custom hooks, context providers, helper utilities, generic components, and type definitions self-contained directly within the TSX implementation.
- RUNTIME EDIT POLICY:
  For edits and code modifications, follow the strict 4-step sequence:
  read_file -> inspect dependencies -> edit -> verify.
- Prop Fallback Aliasing: When implementing components where prompts are concise, support common standard prop aliases:
  * e.g. `const trendVal = props.trend ?? props.valueChange ?? props.change;`
  * e.g. `const initial = props.initialValues ?? props.initialState ?? props.defaultValues ?? {};`
  * e.g. `const labelVal = props.label ?? props.title ?? props.name;`
- NO-CREATEROOT IN COMPONENTS RULE:
  * Never import 'createRoot' from 'react-dom/client' or call 'createRoot' / 'ReactDOM.render' inside component TSX files or ref callbacks.
  * All components and child subcomponents must be rendered purely via standard React JSX (<Component {...props} /> or <div>...</div>).
  * Ref callbacks must ONLY attach DOM properties, event handlers, or IntersectionObserver instances — NEVER instantiate React roots.
- COMPLETE IMPLEMENTATION & NO-PLACEHOLDER RULE:
  * Never emit placeholder comments (e.g. {/* Render ... */}, {/* TODO: ... */}), empty containers with comments, ellipsis, or stubs.
  * Implement all sections, cards, tabs, calculators, and interactive widgets completely with working JSX, state, and markup.
- PERFORMANCE & MOTION RULE:
  * Scroll interactions must be passive ({ passive: true }) and throttled via requestAnimationFrame or built with IntersectionObserver.
  * Never query layout properties (e.g. clientHeight, offsetTop) repeatedly inside raw unthrottled scroll listeners.
  * Always respect @media (prefers-reduced-motion: reduce).
- Imperative DOM Dynamic Container Pattern:
  * This pattern is STRICTLY restricted to standalone imperative non-JSX hook helpers (e.g. `const confirm = useConfirm()`). Standard UI components must NEVER use dynamic DOM containers or createRoot.
- When you receive a test failure in <observation>, carefully inspect the error message and the rendered DOM, deduce what was missing or incorrect, and update the component.
- Do NOT output markdown code fences (```) around your <tool_call> tags.
"""


# ==============================================================================
# 1b. Site Agent System Prompt (multi-file page composition mode)
# ==============================================================================

try:
    from site_prompt import SITE_AGENT_SYSTEM_PROMPT
except ImportError:
    from agent.site_prompt import SITE_AGENT_SYSTEM_PROMPT



# ==============================================================================
# 2. Action Data Structures
# ==============================================================================

@dataclass
class WriteComponentAction:
    tsx: str
    css: str = ""

@dataclass
class WriteSiteAction:
    """
    Carries an ordered list of (relative_path, content) pairs produced by a
    write_site tool call. Paths are relative to the project root, e.g.
    'src/components/Header.tsx' or 'src/components/Header.css'.
    """
    files: List[Tuple[str, str]] = field(default_factory=list)  # [(path, content), ...]

    def get_tsx_files(self) -> List[Tuple[str, str]]:
        """Returns only the .tsx / .ts file pairs."""
        return [(p, c) for p, c in self.files if p.endswith(('.tsx', '.ts'))]

    def get_css_files(self) -> List[Tuple[str, str]]:
        """Returns only the .css file pairs."""
        return [(p, c) for p, c in self.files if p.endswith('.css')]

    def has_real_css(self) -> bool:
        """Returns True if at least one CSS file has non-trivial content."""
        for _, content in self.get_css_files():
            stripped = content.strip()
            if stripped and stripped != "/* empty styles */" and len(stripped) > 20:
                return True
        return False

@dataclass
class InstallPackageAction:
    package: str
    version: Optional[str] = None
    is_dev: bool = False

@dataclass
class RemovePackageAction:
    package: str

@dataclass
class GetDependenciesAction:
    pass

@dataclass
class InspectDependenciesAction:
    pass

@dataclass
class ReadFileAction:
    path: str

@dataclass
class RunTestsAction:
    pass

@dataclass
class GetWebglErrorsAction:
    pass

@dataclass
class GetSceneMetadataAction:
    pass

@dataclass
class GetAssetManifestAction:
    pass

@dataclass
class FinishAction:
    summary: str

ActionType = Union[
    EditFileAction,
    WriteComponentAction,
    WriteSiteAction,
    RunTestsAction,
    InstallPackageAction,
    RemovePackageAction,
    GetDependenciesAction,
    InspectDependenciesAction,
    ReadFileAction,
    GetWebglErrorsAction,
    GetSceneMetadataAction,
    GetAssetManifestAction,
    FinishAction,
    None,
]

@dataclass
class AgentTurn:
    thought: str = ""
    action: ActionType = None
    raw_text: str = ""
    status_message: str = ""

    @property
    def is_finish(self) -> bool:
        return isinstance(self.action, FinishAction)

    @property
    def is_tool_call(self) -> bool:
        return isinstance(self.action, (
            WriteComponentAction,
            WriteSiteAction,
            EditFileAction,
            RunTestsAction,
            InstallPackageAction,
            RemovePackageAction,
            GetDependenciesAction,
            InspectDependenciesAction,
            ReadFileAction,
            GetWebglErrorsAction,
            GetSceneMetadataAction,
            GetAssetManifestAction,
        ))

    @property
    def is_write_site(self) -> bool:
        return isinstance(self.action, WriteSiteAction)


# ==============================================================================
# 3. Agent Output Parser
# ==============================================================================

def _clean_file_code(content: str) -> str:
    """Strips leading/trailing blank lines, markdown code fences, and removes common leading indentation."""
    if not content:
        return ""
    content = re.sub(r'<thought>[\s\S]*?</thought>', '', content).strip()
    # Strip opening markdown code fence, e.g. ```tsx, ```css, ```typescript, ```jsx, ```
    content = re.sub(r'^\s*```(?:tsx|ts|jsx|js|css|html|json|typescript|javascript)?\s*\n?', '', content, flags=re.IGNORECASE)
    # Strip trailing markdown code fence, e.g. ```
    content = re.sub(r'\n?\s*```\s*$', '', content)
    # Strip any trailing dangling <file path="..."> if caught accidentally
    content = re.sub(r'<file\s+(?:path|name)=["\'][^"\'>]+["\']>[\s\S]*$', '', content, flags=re.IGNORECASE)
    dedented = textwrap.dedent(content.strip("\r\n"))
    return dedented.strip()


def _try_parse_json_tool_call(text: str, thought: str = "") -> Optional[AgentTurn]:
    """
    Fallback and action-first parser for models emitting tool calls formatted as JSON
    (e.g. ```json ... ``` or raw JSON object with 'tool_calls', 'action', or 'name').
    Supports both legacy schemas and the blueprint format:
      {
        "action": "edit_file",
        "statusMessage": "Updating the hero layout",
        "arguments": { "path": "...", "content": "..." }
      }
    """
    # ── Backtick template-literal extraction (not valid JSON, needs regex) ───────
    _BACKTICK_FILE_RE = re.compile(
        r'"(src/components/[^"]+\.(?:tsx|ts|css))"\s*:\s*`((?:[^`\\]|\\.)*)`',
        re.DOTALL,
    )
    _WRITE_SITE_ENVELOPE_RE = re.compile(
        r'"function"\s*:\s*"write_(?:site|component)"|'
        r'"name"\s*:\s*"(?:write_(?:site|component)|edit_file|write_file)"|'
        r'"action"\s*:\s*"(?:write_(?:site|component)|edit_file|write_file|replace_hunks|edit_hunks)"',
    )
    if _WRITE_SITE_ENVELOPE_RE.search(text):
        backtick_files = _BACKTICK_FILE_RE.findall(text)
        if backtick_files:
            extracted_files: List[Tuple[str, str]] = []
            for fpath, fcode in backtick_files:
                fcode_clean = fcode.replace('\\`', '`').strip()
                if fpath and fcode_clean:
                    extracted_files.append((fpath.strip(), _clean_file_code(fcode_clean)))
            if extracted_files:
                return AgentTurn(
                    thought=thought,
                    action=WriteSiteAction(files=extracted_files),
                    raw_text=text,
                    status_message="Writing site files via structured action.",
                )

    candidates = []
    # 1. Look for fenced markdown code blocks
    for m in re.finditer(r'```(?:json)?\s*([\s\S]*?)```', text, re.IGNORECASE):
        candidates.append(m.group(1).strip())
    # 2. Look for explicit JSON object with tool_calls, action, name, or function
    m_tc = re.search(r'(\{[\s\S]*"tool_calls"\s*:[\s\S]*\})', text)
    if m_tc:
        candidates.append(m_tc.group(1).strip())
    m_name = re.search(r'(\{[\s\S]*"(?:name|action|function)"\s*:\s*"(?:write_site|write_component|edit_file|write_file|replace_hunks|edit_hunks|finish|run_tests|read_file|inspect_dependencies|get_dependencies)"[\s\S]*\})', text)
    if m_name:
        candidates.append(m_name.group(1).strip())
    if text.strip().startswith('{') and text.strip().endswith('}'):
        candidates.append(text.strip())

    for cand in candidates:
        data = None
        try:
            cleaned = re.sub(r',\s*([\]}])', r'\1', cand)
            data = json.loads(cleaned)
        except Exception:
            s_idx = cand.find('{')
            e_idx = cand.rfind('}')
            if s_idx != -1 and e_idx > s_idx:
                try:
                    sub = cand[s_idx:e_idx + 1]
                    sub = re.sub(r',\s*([\]}])', r'\1', sub)
                    data = json.loads(sub)
                except Exception:
                    pass

        if not data:
            continue

        calls = []
        if isinstance(data, dict):
            if "tool_calls" in data and isinstance(data["tool_calls"], list):
                calls = data["tool_calls"]
            elif "action" in data or "name" in data:
                calls = [data]
        elif isinstance(data, list):
            calls = data

        for call in calls:
            if not isinstance(call, dict):
                continue
            name = call.get("action") or call.get("name", "")
            status_msg = call.get("statusMessage") or call.get("status_message") or ""
            args = call.get("arguments") or call.get("args") or call.get("parameters") or {}
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except Exception:
                    pass

            extracted_thought = thought or call.get("thought", "")

            if name == "replace_hunks" or name == "edit_hunks":
                if not isinstance(args, dict):
                    continue
                raw_hunks = args.get("hunks") or []
                hunks = [ReplaceHunk(str(h.get("before", "")), str(h.get("after", "")), int(h.get("expected_count", 1)))
                         for h in raw_hunks if isinstance(h, dict) and "before" in h]
                if args.get("path") and args.get("base_sha256") and hunks:
                    return AgentTurn(thought=extracted_thought,
                                     action=EditFileAction(str(args["path"]), str(args["base_sha256"]), hunks),
                                     raw_text=text, status_message=status_msg or "Applying guarded edit.")

            if name in ("edit_file", "write_file", "write_site"):
                extracted_files: List[Tuple[str, str]] = []

                # Check if single file specified in args or call
                single_path = ""
                single_content = ""
                if isinstance(args, dict):
                    single_path = args.get("path") or args.get("file") or args.get("filename") or ""
                    single_content = args.get("content") or args.get("code") or ""
                if not single_path:
                    single_path = call.get("path") or call.get("file") or ""
                if not single_content:
                    single_content = call.get("content") or call.get("code") or ""

                if single_path and single_content:
                    extracted_files.append((str(single_path).strip(), _clean_file_code(str(single_content))))

                if isinstance(args, dict) and "files" in args:
                    f_val = args["files"]
                    if isinstance(f_val, list):
                        for item in f_val:
                            if isinstance(item, dict):
                                p = item.get("path") or item.get("name") or item.get("filename") or ""
                                c = item.get("content") or item.get("code") or ""
                                if p and c:
                                    extracted_files.append((str(p).strip(), _clean_file_code(str(c))))
                            elif isinstance(item, (list, tuple)) and len(item) == 2:
                                p, c = item[0], item[1]
                                if p and c:
                                    extracted_files.append((str(p).strip(), _clean_file_code(str(c))))
                    elif isinstance(f_val, dict):
                        for p, c in f_val.items():
                            extracted_files.append((str(p).strip(), _clean_file_code(str(c))))
                elif "files" in call and isinstance(call["files"], (list, dict)):
                    f_val = call["files"]
                    if isinstance(f_val, list):
                        for item in f_val:
                            if isinstance(item, dict):
                                p = item.get("path") or item.get("name") or item.get("filename") or ""
                                c = item.get("content") or item.get("code") or ""
                                if p and c:
                                    extracted_files.append((str(p).strip(), _clean_file_code(str(c))))
                            elif isinstance(item, (list, tuple)) and len(item) == 2:
                                p, c = item[0], item[1]
                                if p and c:
                                    extracted_files.append((str(p).strip(), _clean_file_code(str(c))))
                    elif isinstance(f_val, dict):
                        for p, c in f_val.items():
                            extracted_files.append((str(p).strip(), _clean_file_code(str(c))))

                if isinstance(args, dict) and "sections" in args and isinstance(args["sections"], list):
                    for sec in args["sections"]:
                        if isinstance(sec, dict):
                            sec_name = sec.get("name") or sec.get("section") or "Section"
                            pascal = "".join(w.capitalize() for w in re.split(r'[-_]', sec_name))
                            if "files" in sec and isinstance(sec["files"], list):
                                for item in sec["files"]:
                                    if isinstance(item, dict):
                                        p = item.get("path") or item.get("name") or ""
                                        c = item.get("content") or item.get("code") or ""
                                        if p and c:
                                            extracted_files.append((str(p).strip(), str(c).strip()))
                            if "tsx" in sec and sec["tsx"]:
                                extracted_files.append((f"src/components/{pascal}.tsx", str(sec["tsx"]).strip()))
                            if "css" in sec and sec["css"]:
                                extracted_files.append((f"src/components/{pascal}.css", str(sec["css"]).strip()))

                if isinstance(args, dict) and ("tsx" in args or "component" in args):
                    tsx_val = args.get("tsx") or args.get("component") or ""
                    css_val = args.get("css") or args.get("styles") or ""
                    p_name = args.get("name") or "Component"
                    pascal = "".join(w.capitalize() for w in re.split(r'[-_]', p_name))
                    if tsx_val:
                        extracted_files.append((f"src/components/{pascal}.tsx", str(tsx_val).strip()))
                    if css_val:
                        extracted_files.append((f"src/components/{pascal}.css", str(css_val).strip()))

                if extracted_files:
                    return AgentTurn(
                        thought=extracted_thought,
                        action=WriteSiteAction(files=extracted_files),
                        raw_text=text,
                        status_message=str(status_msg).strip(),
                    )

            elif name == "write_component":
                tsx_code = ""
                css_code = ""
                if isinstance(args, dict):
                    tsx_code = args.get("tsx") or args.get("code") or args.get("component") or ""
                    css_code = args.get("css") or args.get("styles") or ""
                if not tsx_code:
                    tsx_code = call.get("tsx") or call.get("code") or ""
                    css_code = call.get("css") or call.get("styles") or ""
                if tsx_code:
                    return AgentTurn(
                        thought=extracted_thought,
                        action=WriteComponentAction(tsx=str(tsx_code).strip(), css=str(css_code).strip()),
                        raw_text=text,
                        status_message=str(status_msg).strip(),
                    )

            elif name == "finish":
                summary = ""
                if isinstance(args, dict):
                    summary = args.get("summary") or args.get("message") or ""
                if not summary:
                    summary = call.get("summary") or call.get("message") or status_msg or ""
                return AgentTurn(
                    thought=extracted_thought,
                    action=FinishAction(summary=str(summary)),
                    raw_text=text,
                    status_message=str(status_msg).strip(),
                )

            elif name == "run_tests":
                return AgentTurn(
                    thought=extracted_thought,
                    action=RunTestsAction(),
                    raw_text=text,
                    status_message=str(status_msg).strip(),
                )

            elif name == "install_package":
                pkg = ""
                version = None
                is_dev = False
                if isinstance(args, dict):
                    pkg = args.get("package") or args.get("name") or ""
                    version = args.get("version")
                    is_dev = bool(args.get("is_dev") or args.get("dev") or False)
                elif isinstance(args, str):
                    pkg = args
                if not pkg:
                    pkg = call.get("package") or call.get("name") or ""
                return AgentTurn(
                    thought=extracted_thought,
                    action=InstallPackageAction(package=str(pkg).strip(), version=version, is_dev=is_dev),
                    raw_text=text,
                    status_message=str(status_msg).strip() or f"Installing {pkg}…",
                )

            elif name == "remove_package":
                pkg = ""
                if isinstance(args, dict):
                    pkg = args.get("package") or args.get("name") or ""
                elif isinstance(args, str):
                    pkg = args
                if not pkg:
                    pkg = call.get("package") or call.get("name") or ""
                return AgentTurn(
                    thought=extracted_thought,
                    action=RemovePackageAction(package=str(pkg).strip()),
                    raw_text=text,
                    status_message=str(status_msg).strip() or f"Removing {pkg}…",
                )

            elif name == "get_dependencies":
                return AgentTurn(
                    thought=extracted_thought,
                    action=GetDependenciesAction(),
                    raw_text=text,
                    status_message=str(status_msg).strip() or "Inspecting project dependencies…",
                )

            elif name == "inspect_dependencies":
                return AgentTurn(
                    thought=extracted_thought,
                    action=InspectDependenciesAction(),
                    raw_text=text,
                    status_message=str(status_msg).strip() or "Inspecting project dependencies…",
                )

            elif name == "get_webgl_errors":
                return AgentTurn(
                    thought=extracted_thought,
                    action=GetWebglErrorsAction(),
                    raw_text=text,
                    status_message=str(status_msg).strip() or "Inspecting WebGL diagnostics and errors…",
                )

            elif name == "get_scene_metadata":
                return AgentTurn(
                    thought=extracted_thought,
                    action=GetSceneMetadataAction(),
                    raw_text=text,
                    status_message=str(status_msg).strip() or "Inspecting 3D scene architecture and metadata…",
                )

            elif name == "get_asset_manifest":
                return AgentTurn(
                    thought=extracted_thought,
                    action=GetAssetManifestAction(),
                    raw_text=text,
                    status_message=str(status_msg).strip() or "Scanning 3D asset manifest…",
                )

            elif name == "read_file":
                fpath = ""
                if isinstance(args, dict):
                    fpath = args.get("path") or args.get("file") or args.get("filename") or ""
                elif isinstance(args, str):
                    fpath = args
                if not fpath:
                    fpath = call.get("path") or call.get("file") or ""
                return AgentTurn(
                    thought=extracted_thought,
                    action=ReadFileAction(path=str(fpath).strip()),
                    raw_text=text,
                    status_message=str(status_msg).strip() or f"Reading {fpath}…",
                )

    return None


def close_complete_site_envelope(raw_text: str) -> str:
    """Recover a tool call whose files are complete but final tool tag was omitted."""
    start = re.search(r'<tool_call\s+name=["\']write_site["\']\s*>', raw_text, re.I)
    if not start or '</tool_call>' in raw_text[start.end():]:
        return raw_text
    body = raw_text[start.end():]
    openings = re.findall(r'<file\s+(?:path|name)=["\'][^"\']+["\']\s*>', body)
    complete = re.findall(r'<file\s+(?:path|name)=["\'][^"\']+["\']\s*>[\s\S]*?</file>', body)
    if openings and len(openings) == len(complete) == body.count('</file>'):
        return raw_text.rstrip() + '\n</tool_call>'
    return raw_text


def site_envelope_errors(raw_text: str) -> List[str]:
    """Reject incomplete live writes; retain permissive parsing only for old logs."""
    stripped = scrub_think_blocks(raw_text).strip()
    if stripped.startswith("```json"):
        stripped = re.sub(r"^```json\s*|\s*```$", "", stripped, flags=re.I).strip()
    if stripped.startswith("{"):
        try:
            json.loads(stripped)
        except json.JSONDecodeError:
            return ["JSON tool action is incomplete or malformed"]
        return []
    start = re.search(r'<tool_call\s+name=["\']write_site["\']\s*>', raw_text, re.I)
    if not start:
        return ["File tags require a complete write_site tool envelope"] if "<file " in raw_text else []
    body = raw_text[start.end():]
    if '</tool_call>' not in body:
        return ['write_site is missing its closing tool_call tag']
    body = body.split('</tool_call>', 1)[0]
    openings = re.findall(r'<file\s+(?:path|name)=["\'][^"\']+["\']\s*>', body)
    complete = re.findall(r'<file\s+(?:path|name)=["\'][^"\']+["\']\s*>[\s\S]*?</file>', body)
    if not openings or len(openings) != len(complete) or len(openings) != body.count('</file>'):
        return ['Every file must have a complete body and a closing file tag']
    return []


def scrub_think_blocks(text: str) -> str:
    """Strip Qwen3 native <think>...</think> blocks from model output.

    Defense-in-depth output scrubber: while apply_chat_template uses
    enable_thinking=False, models may still occasionally emit thinking blocks
    in certain checkpoint or adapter configurations. This ensures all downstream
    consumers receive clean, action-first text.
    """
    if not text or "<think>" not in text:
        return text or ""
    return re.sub(r'<think>[\s\S]*?</think>\s*', '', text, flags=re.DOTALL).strip()


def parse_agent_output(raw_text: str) -> AgentTurn:
    """
    Parses the raw generation from the model into an AgentTurn.
    Supports structured JSON actions (blueprint protocol) as well as XML <tool_call> formats.
    Forgiving of legacy <thought> tags (optional), unclosed tags, or mixed markdown.
    Priority order: JSON actions > write_site > write_component > run_tests > finish > fallback.
    """
    text = scrub_think_blocks(raw_text).strip()

    # Explicit write_site envelopes are a transactional protocol.  Never let the
    # permissive parser turn a truncated response into a partial write.
    if re.search(r'<tool_call\s+name=["\']write_site["\']\s*>', text, re.I):
        envelope_errors = site_envelope_errors(text)
        if envelope_errors:
            return AgentTurn(raw_text=text, status_message="Malformed write_site envelope: " + "; ".join(envelope_errors))

    # 1. Try structured JSON action envelope first (action / statusMessage / arguments)
    json_turn = _try_parse_json_tool_call(text)
    if json_turn and json_turn.action is not None:
        return json_turn

    # 2. Extract legacy <thought> if present (suppressed in UI runtime)
    thought = ""
    thought_match = re.search(r'<thought>([\s\S]*?)(?:</thought>|$)', text, re.IGNORECASE)
    if thought_match:
        thought = thought_match.group(1).strip()

    # 3. Check for <tool_call name="write_site"> FIRST (site pipeline)
    write_site_match = re.search(
        r'<tool_call\s+name=["\']write_site["\']>([\s\S]*?)(?:</tool_call>|$)',
        text,
        re.IGNORECASE
    )
    # If no explicit write_site envelope, recognize either file path attribute spelling.
    body = None
    if write_site_match:
        body = write_site_match.group(1)
    elif re.search(r'<file\s+(?:path|name)=["\'][^"\'>]+["\']>', text, re.IGNORECASE):
        body = text

    if body is not None:
        # Extract all file pairs; the lookahead prevents
        # an unclosed first file from swallowing the next file
        file_matches = re.findall(
            r'<file\s+(?:path|name)=["\']([^"\'>]+)["\']>([\s\S]*?)(?:</file>|(?=<file\s+(?:path|name)=)|$)',
            body,
            re.IGNORECASE
        )
        raw_files: List[Tuple[str, str]] = []
        for fpath, fcontent in file_matches:
            # Defensive check: if fcontent still contains an embedded file tag, split it.
            sub_matches = re.findall(
                r'<file\s+(?:path|name)=["\']([^"\'>]+)["\']>([\s\S]*?)(?:</file>|(?=<file\s+(?:path|name)=)|$)',
                fcontent,
                re.IGNORECASE
            )
            if sub_matches:
                first_sub_m = re.search(r'<file\s+(?:path|name)=', fcontent, re.IGNORECASE)
                first_sub_idx = first_sub_m.start() if first_sub_m else len(fcontent)
                raw_files.append((fpath.strip(), fcontent[:first_sub_idx]))
                for sub_path, sub_content in sub_matches:
                    raw_files.append((sub_path.strip(), sub_content))
            else:
                raw_files.append((fpath.strip(), fcontent))

        files: List[Tuple[str, str]] = []
        for fpath, fcontent in raw_files:
            cleaned_content = _clean_file_code(fcontent)
            if fpath and cleaned_content:
                files.append((fpath, cleaned_content))

        if files or write_site_match:
            clean_raw = text
            if "</tool_call>" in text:
                clean_raw = text[:text.find("</tool_call>") + len("</tool_call>")].strip()
            clean_raw = re.sub(r'<thought>[\s\S]*?</thought>', '', clean_raw).strip()

            return AgentTurn(
                thought=thought,
                action=WriteSiteAction(files=files),
                raw_text=clean_raw,
                status_message="Writing site files.",
            )

    # 4. Check for <tool_call name="write_component">
    write_comp_match = re.search(
        r'<tool_call\s+name=["\']write_component["\']>([\s\S]*?)(?:</tool_call>|$)',
        text,
        re.IGNORECASE
    )
    if write_comp_match:
        body = write_comp_match.group(1)
        tsx_match = re.search(r'<tsx>([\s\S]*?)(?:</tsx>|$)', body, re.IGNORECASE)
        css_match = re.search(r'<css>([\s\S]*?)(?:</css>|$)', body, re.IGNORECASE)

        tsx_code = ""
        css_code = ""

        if tsx_match:
            tsx_code = tsx_match.group(1).strip()
        if css_match:
            css_code = css_match.group(1).strip()

        # If <tsx> tags were omitted inside tool_call, fall back to code block or raw text
        if not tsx_code:
            code_block_match = re.search(r'```(?:tsx|typescript|jsx)?\s*\n([\s\S]*?)```', body)
            if code_block_match:
                tsx_code = code_block_match.group(1).strip()
            else:
                tsx_code = body.strip()

        # Check if CSS was provided via explicit fenced css block or trailing css comment
        if not css_code:
            css_block_match = re.search(r'```(?:css|scss|module\.css)\s*\n([\s\S]*?)```', body)
            if css_block_match:
                css_code = css_block_match.group(1).strip()
                tsx_code = re.sub(r'```(?:css|scss|module\.css)\s*\n[\s\S]*?```', '', tsx_code).strip()
            else:
                # Only split if there is a distinct CSS comment block at the end of the file following TSX exports
                css_comment_match = re.search(r'\n(/\*\s*(?:styles?|css|[\w.-]+\.css)[\s\S]*?\*/[\s\S]*)$', tsx_code, re.IGNORECASE)
                if css_comment_match and "export" in tsx_code[:css_comment_match.start(1)]:
                    split_idx = css_comment_match.start(1)
                    css_code = tsx_code[split_idx:].strip()
                    tsx_code = tsx_code[:split_idx].strip()

        # Clean text up to </tool_call> so post-call hallucinations don't enter history
        clean_raw = text
        if "</tool_call>" in text:
            clean_raw = text[:text.find("</tool_call>") + len("</tool_call>")].strip()
        clean_raw = re.sub(r'<thought>[\s\S]*?</thought>', '', clean_raw).strip()

        return AgentTurn(
            thought=thought,
            action=WriteComponentAction(tsx=_clean_file_code(tsx_code), css=_clean_file_code(css_code)),
            raw_text=clean_raw,
            status_message="Writing component implementation.",
        )

    # 4b. Check for JSON formatted tool calls (write_component fallback)
    if json_turn and isinstance(json_turn.action, WriteComponentAction):
        return json_turn

    # 5. Check for <tool_call name="run_tests">
    run_tests_match = re.search(
        r'<tool_call\s+name=["\']run_tests["\']\s*(?:/>|>[\s\S]*?</tool_call>)',
        text,
        re.IGNORECASE
    )
    if run_tests_match:
        clean_raw = text
        if "</tool_call>" in text:
            clean_raw = text[:text.find("</tool_call>") + len("</tool_call>")].strip()
        clean_raw = re.sub(r'<thought>[\s\S]*?</thought>', '', clean_raw).strip()
        return AgentTurn(thought=thought, action=RunTestsAction(), raw_text=clean_raw, status_message="Running tests.")

    # 6. Check for <finish>
    finish_match = re.search(r'<finish>([\s\S]*?)(?:</finish>|$)', text, re.IGNORECASE)
    if finish_match:
        summary = finish_match.group(1).strip()
        clean_raw = text
        if "</finish>" in text:
            clean_raw = text[:text.find("</finish>") + len("</finish>")].strip()
        clean_raw = re.sub(r'<thought>[\s\S]*?</thought>', '', clean_raw).strip()
        return AgentTurn(thought=thought, action=FinishAction(summary=summary), raw_text=clean_raw, status_message="Task finished.")

    # 6b. Check for XML <tool_call name="install_package">, "remove_package", "get_dependencies"
    inst_match = re.search(r'<tool_call\s+name=["\']install_package["\']\s*>([\s\S]*?)</tool_call>', text, re.IGNORECASE)
    if inst_match:
        body = inst_match.group(1).strip()
        pkg = body
        version = None
        is_dev = False
        try:
            d = json.loads(body)
            if isinstance(d, dict):
                pkg = d.get("package") or d.get("name") or pkg
                version = d.get("version")
                is_dev = bool(d.get("is_dev") or d.get("dev") or False)
        except Exception:
            pass
        clean_raw = re.sub(r'<thought>[\s\S]*?</thought>', '', text).strip()
        return AgentTurn(
            thought=thought,
            action=InstallPackageAction(package=pkg, version=version, is_dev=is_dev),
            raw_text=clean_raw,
            status_message=f"Installing {pkg}…",
        )

    rem_match = re.search(r'<tool_call\s+name=["\']remove_package["\']\s*>([\s\S]*?)</tool_call>', text, re.IGNORECASE)
    if rem_match:
        body = rem_match.group(1).strip()
        pkg = body
        try:
            d = json.loads(body)
            if isinstance(d, dict):
                pkg = d.get("package") or d.get("name") or pkg
        except Exception:
            pass
        clean_raw = re.sub(r'<thought>[\s\S]*?</thought>', '', text).strip()
        return AgentTurn(
            thought=thought,
            action=RemovePackageAction(package=pkg),
            raw_text=clean_raw,
            status_message=f"Removing {pkg}…",
        )

    get_deps_match = re.search(r'<tool_call\s+name=["\'](get_dependencies|inspect_dependencies)["\']\s*(?:/>|>[\s\S]*?</tool_call>)', text, re.IGNORECASE)
    if get_deps_match:
        tool_name = get_deps_match.group(1).lower()
        act_inst = GetDependenciesAction() if tool_name == "get_dependencies" else InspectDependenciesAction()
        clean_raw = re.sub(r'<thought>[\s\S]*?</thought>', '', text).strip()
        return AgentTurn(
            thought=thought,
            action=act_inst,
            raw_text=clean_raw,
            status_message="Inspecting dependencies…",
        )

    read_file_match = re.search(r'<tool_call\s+name=["\']read_file["\']\s*>([\s\S]*?)</tool_call>', text, re.IGNORECASE)
    if read_file_match:
        body = read_file_match.group(1).strip()
        path_m = re.search(r'<path>([\s\S]*?)</path>', body, re.IGNORECASE)
        read_path = path_m.group(1).strip() if path_m else body
        clean_raw = re.sub(r'<thought>[\s\S]*?</thought>', '', text).strip()
        return AgentTurn(
            thought=thought,
            action=ReadFileAction(path=read_path),
            raw_text=clean_raw,
            status_message=f"Reading {read_path}…",
        )

    webgl_err_match = re.search(r'<tool_call\s+name=["\']get_webgl_errors["\']\s*(?:/>|>[\s\S]*?</tool_call>)', text, re.IGNORECASE)
    if webgl_err_match:
        clean_raw = re.sub(r'<thought>[\s\S]*?</thought>', '', text).strip()
        return AgentTurn(
            thought=thought,
            action=GetWebglErrorsAction(),
            raw_text=clean_raw,
            status_message="Inspecting WebGL diagnostics and errors…",
        )

    scene_meta_match = re.search(r'<tool_call\s+name=["\']get_scene_metadata["\']\s*(?:/>|>[\s\S]*?</tool_call>)', text, re.IGNORECASE)
    if scene_meta_match:
        clean_raw = re.sub(r'<thought>[\s\S]*?</thought>', '', text).strip()
        return AgentTurn(
            thought=thought,
            action=GetSceneMetadataAction(),
            raw_text=clean_raw,
            status_message="Inspecting 3D scene architecture and metadata…",
        )

    asset_man_match = re.search(r'<tool_call\s+name=["\']get_asset_manifest["\']\s*(?:/>|>[\s\S]*?</tool_call>)', text, re.IGNORECASE)
    if asset_man_match:
        clean_raw = re.sub(r'<thought>[\s\S]*?</thought>', '', text).strip()
        return AgentTurn(
            thought=thought,
            action=GetAssetManifestAction(),
            raw_text=clean_raw,
            status_message="Scanning 3D asset manifest…",
        )

    # 6c. Check for JSON formatted tool calls (finish or dependency actions fallback)
    if json_turn and isinstance(json_turn.action, (
        FinishAction,
        RunTestsAction,
        InstallPackageAction,
        RemovePackageAction,
        GetDependenciesAction,
        InspectDependenciesAction,
        ReadFileAction,
        GetWebglErrorsAction,
        GetSceneMetadataAction,
        GetAssetManifestAction,
    )):
        return json_turn

    # 7. Fallback: If model generated code directly without <tool_call> wrapper
    if "import React" in text or "export function" in text or "export const" in text:
        clean_code = re.sub(r'<thought>[\s\S]*?</thought>', '', text).strip()
        clean_code = re.sub(r'^```(?:tsx|typescript|jsx)?\s*', '', clean_code)
        clean_code = re.sub(r'\s*```$', '', clean_code)
        
        tsx_code = clean_code
        css_code = ""
        # Check for explicit css code block in raw text
        css_block_match = re.search(r'```(?:css|scss|module\.css)\s*\n([\s\S]*?)```', text)
        if css_block_match:
            css_code = css_block_match.group(1).strip()
            tsx_code = re.sub(r'```(?:css|scss|module\.css)\s*\n[\s\S]*?```', '', tsx_code).strip()
        else:
            css_comment_match = re.search(r'\n(/\*\s*(?:styles?|css|[\w.-]+\.css)[\s\S]*?\*/[\s\S]*)$', tsx_code, re.IGNORECASE)
            if css_comment_match and "export" in tsx_code[:css_comment_match.start(1)]:
                split_idx = css_comment_match.start(1)
                css_code = tsx_code[split_idx:].strip()
                tsx_code = tsx_code[:split_idx].strip()

        # Built outside the f-string: Python < 3.12 forbids backslashes in f-string expressions.
        css_part = f"\n<css>\n{css_code}\n</css>" if css_code else ""
        clean_raw = (
            f"<tool_call name=\"write_component\">\n<tsx>\n{tsx_code}\n</tsx>"
            f"{css_part}\n</tool_call>"
        )

        return AgentTurn(
            thought=thought,
            action=WriteComponentAction(tsx=_clean_file_code(tsx_code), css=_clean_file_code(css_code)),
            raw_text=clean_raw,
        )

    # 8. If only thought or unrecognized action
    return AgentTurn(thought=thought or text, action=None, raw_text=text)


# ==============================================================================
# 4. Smart Observation Formatter (Pruning for Context Window)
# ==============================================================================

def extract_accessible_roles_summary(text: str, max_lines: int = 12) -> str:
    """
    Extracts Testing Library's 'Here are the accessible roles:' or
    'Here are the available accessible names:' table so the model
    immediately sees what accessible elements exist and their exact names.
    """
    m = re.search(
        r'(Here are the (?:accessible roles|available accessible names):[\s\S]*?)(?:<body>|Ignored nodes:|at\s+Object\.getElementError|$)',
        text,
        re.IGNORECASE
    )
    if not m:
        return ""

    block = m.group(1).strip()
    # Strip any internal delimiter clutter
    lines = [l.rstrip() for l in block.splitlines() if l.strip() and not l.strip().startswith("---")]
    if len(lines) > max_lines:
        lines = lines[:max_lines] + ["    ... [accessible roles list truncated] ..."]
    return "\n".join(lines).strip()


def prune_stack_trace(error_text: str, max_lines: int = 18) -> str:
    """
    Strips ANSI escape codes, irrelevant node_modules, and framework internals
    from stack traces, leaving only the assertion failure and relevant DOM dump.
    """
    # 1. Strip all ANSI escape sequences
    clean_text = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', error_text)

    lines = clean_text.splitlines()
    filtered: List[str] = []

    skip_patterns = [
        r'at Object\.getElementError \(.*node_modules',
        r'at .*\(.*node_modules[\\/]@testing-library',
        r'at .*\(.*node_modules[\\/]@vitest',
        r'at .*\(.*node_modules[\\/]react-dom',
        r'at .*\(.*node_modules[\\/]vite',
        r'TransformPluginContext\.',
        r'at runWithTimeout \(',
        r'at file:///',
        r'at new Promise \(<anonymous>\)',
        r'^\s*RUN\s+v\d+\.\d+',
        r'^\s*Failed Suites',
        r'^\s*FAIL\s+\.agent_workspace',
        r'^\s*Test Files\s+\d+\s+failed',
        r'^\s*Tests\s+\d+\s+failed',
        r'^\s*Start at\s+',
        r'^\s*Duration\s+',
        r'^\s*Ignored nodes:\s+comments'
    ]

    in_html_block = False
    html_line_count = 0

    for line in lines:
        if any(re.search(pat, line) for pat in skip_patterns):
            continue

        # Detect excessive HTML dumps from Testing Library
        if "<html" in line or "<body" in line:
            in_html_block = True
            html_line_count = 0

        if in_html_block:
            html_line_count += 1
            if html_line_count > 8:
                if html_line_count == 9:
                    filtered.append("    ... [DOM elements truncated for brevity] ...")
                if "</html>" in line or "</body>" in line:
                    in_html_block = False
                continue
            if "</html>" in line or "</body>" in line:
                in_html_block = False

        filtered.append(line)

    # Trim consecutive blank lines
    cleaned: List[str] = []
    for line in filtered:
        if not line.strip() and cleaned and not cleaned[-1].strip():
            continue
        cleaned.append(line)

    if len(cleaned) > max_lines:
        half = max_lines // 2
        cleaned = cleaned[:half] + ["  ... [stack lines omitted for brevity] ..."] + cleaned[-half:]

    return "\n".join(cleaned).strip()


def extract_primary_failure(
    tsc_passed: bool,
    vitest_passed: bool,
    tsc_output: str = "",
    vitest_output: str = ""
) -> str:
    """
    Lever 4: Extracts the primary, high-signal failure message so the model
    can focus immediately on the root cause rather than diagnosing noisy stack traces.
    """
    if not tsc_passed:
        # Match explicit TypeScript error lines, e.g.:
        # Component.tsx(68,15): error TS1308: 'await' expressions are only allowed...
        clean_tsc = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', tsc_output)
        m = re.search(r'([^\r\n]*\.tsx?\(\d+,\d+\):\s*error\s+TS\d+:[^\r\n]+)', clean_tsc, re.IGNORECASE)
        if m:
            return m.group(1).strip()
        m2 = re.search(r'(error\s+TS\d+:[^\r\n]+)', clean_tsc, re.IGNORECASE)
        if m2:
            return m2.group(1).strip()
        return "TypeScript syntax or type checking failed."

    if not vitest_passed:
        clean_v = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', vitest_output)
        patterns = [
            r'((?:TestingLibraryElementError|AssertionError|TypeError|ReferenceError|SyntaxError):\s*[^\r\n]+)',
            r'(Unable to find an accessible element[^\r\n]+)',
            r'(Unable to find an element[^\r\n]+)',
            r'(Cannot read properties of[^\r\n]+)',
            r'((?:Error:\s*)?Timeout\s*-\s*Async function did not complete[^\r\n]*)',
            r'(Warning:\s*An update to [^\r\n]+ was not wrapped in act\([^\r\n]*)',
            r'((?:expected|Expected)\s+[\s\S]{1,80}?(?:to be|to equal|to have|Received))',
            r'(Error:\s*expect\(received\)[^\r\n]+)',
            r'(AssertionError:\s*[^\r\n]+)',
            r'(\u2192\s*[^\r\n]+)'  # Vitest arrow indicator -> error message
        ]
        for pat in patterns:
            m = re.search(pat, clean_v)
            if m:
                return m.group(1).strip().replace("\n", " ")
        return "Vitest test assertions failed."

    return ""


def extract_error_signature(error_str: str) -> str:
    """
    Derives a normalized error signature for robust anti-stuck loop detection.
    Strips transient (line, col) or :line:col positions so regenerating code on shifted
    lines still matches the underlying bug signature. Extracts TS error codes.
    """
    if not error_str:
        return ""
    # Strip (line,col) or :line:col references
    norm = re.sub(r'\(\d+,\d+\)', '', error_str)
    norm = re.sub(r':\d+:\d+', '', norm)
    # Extract TypeScript error code if present (e.g. error TS2304)
    ts_code = re.search(r'error\s+(TS\d+)', norm, re.IGNORECASE)
    if ts_code:
        code = ts_code.group(1).upper()
        detail = re.sub(r'.*error\s+TS\d+:\s*', '', norm).strip()
        return f"{code}:{detail[:80]}"
    # For Vitest/JS errors, match error class name
    v_type = re.search(r'((?:TestingLibraryElementError|AssertionError|TypeError|ReferenceError|SyntaxError))', norm)
    if v_type:
        detail = norm.strip()
        return f"{v_type.group(1)}:{detail[:80]}"
    return norm.strip()[:100]


def format_observation(
    tsc_passed: bool,
    vitest_passed: bool,
    tsc_output: str = "",
    vitest_output: str = "",
    max_char_limit: int = 1500
) -> str:
    """
    Assembles a compact, high-signal observation for the model.
    Places the primary failure headline at the top, isolates TypeScript errors,
    preserves accessible roles/names tables, and strips secondary runner noise.
    """
    if tsc_passed and vitest_passed:
        return "<observation status=\"passed\">\n[TSC]: Passed (0 errors)\n[Vitest]: All tests passed successfully!\n</observation>"

    obs_lines = ["<observation status=\"failed\">"]
    primary_err = extract_primary_failure(tsc_passed, vitest_passed, tsc_output, vitest_output)

    # 1. TSC status
    if not tsc_passed:
        if primary_err:
            obs_lines.append(f"[CRITICAL TYPESCRIPT ERROR - FIX FIRST]:\n--> {primary_err}\n")
        if "error TS2304" in tsc_output or "Cannot find name" in tsc_output or "error TS2339" in tsc_output:
            obs_lines.append(
                "[CRITICAL ACTION REQUIRED - UNDECLARED IDENTIFIER]:\n"
                "--> This identifier or property does not exist in your scope. You MUST add the "
                "import (e.g. from 'react', 'react-dom') or declare/define it. Do NOT reference undeclared identifiers.\n"
            )
        obs_lines.append("[TSC Compilation Output]:")
        clean_tsc = prune_stack_trace(tsc_output, max_lines=6)
        obs_lines.append(clean_tsc)
        # Prune vitest output completely when TSC fails to avoid confusing the 3B model
        obs_lines.append("\n[Vitest]: Tests blocked by compilation failure. Fix TypeScript syntax/type error above first.")
    else:
        obs_lines.append("[TSC]: Passed (0 syntax/type errors)")
        if not vitest_passed:
            if primary_err:
                obs_lines.append(f"[PRIMARY TEST FAILURE - FIX REQUIRED]:\n--> {primary_err}\n")

            # Check if Testing Library provided an accessible roles/names table
            clean_raw_v = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', vitest_output)
            roles_table = extract_accessible_roles_summary(clean_raw_v, max_lines=10)
            if roles_table:
                obs_lines.append("[Testing Library Accessible Elements in Rendered DOM]:")
                obs_lines.append(roles_table)
                obs_lines.append("")

            obs_lines.append("[Vitest Test Failure Details]:")
            clean_vitest = prune_stack_trace(vitest_output, max_lines=14)
            obs_lines.append(clean_vitest)

    obs_lines.append("</observation>")
    full_obs = "\n".join(obs_lines)

    # Hard cap to protect token budget, cutting on nearest preceding newline
    if len(full_obs) > max_char_limit:
        cut_point = full_obs.rfind("\n", 0, max_char_limit)
        if cut_point > max_char_limit // 2:
            full_obs = full_obs[:cut_point] + "\n... [observation truncated]\n</observation>"
        else:
            full_obs = full_obs[:max_char_limit] + "\n... [observation truncated]\n</observation>"

    return full_obs


# ==============================================================================
# 5. Chat Template Serialization (Qwen3-4B native / Qwen2.5 legacy fallback)
# ==============================================================================

# Module-level tokenizer registry.  Set once after model load via
# set_default_tokenizer(); all format_chatml() callers upgrade automatically.
_DEFAULT_TOKENIZER: Any = None


def set_default_tokenizer(tokenizer: Any) -> None:
    """Register a loaded HuggingFace tokenizer as the module default.

    Once registered, format_chatml() will delegate to
    ``tokenizer.apply_chat_template(..., enable_thinking=False)`` instead of
    the hand-rolled legacy template.  This makes the Qwen3-4B native chat
    template active for all callers without any per-call-site changes.

    Args:
        tokenizer: A HuggingFace PreTrainedTokenizer / PreTrainedTokenizerFast
                   that exposes ``apply_chat_template``.
    """
    global _DEFAULT_TOKENIZER
    _DEFAULT_TOKENIZER = tokenizer


register_tokenizer = set_default_tokenizer


def get_default_tokenizer() -> Any:
    """Retrieve the module default registered tokenizer, if any."""
    return _DEFAULT_TOKENIZER


def format_chatml(
    messages: List[Dict[str, str]],
    add_generation_prompt: bool = True,
    tokenizer: Any = None,
) -> str:
    """Serialize ``messages`` into the active chat template.

    Behaviour:
    - When a *tokenizer* is supplied explicitly, or when one has been registered
      via ``set_default_tokenizer()``, delegates to
      ``tokenizer.apply_chat_template(messages, tokenize=False,
      add_generation_prompt=add_generation_prompt, enable_thinking=False)``.
      This is the Qwen3-4B–native path and must be used for all training and
      inference once the Qwen3 base model is in place.
    - When **no** tokenizer is available (offline tests, data pipeline scripts
      that run before the model is loaded), falls back to the hand-rolled
      Qwen2.5/ChatML template::

          <|im_start|>role\ncontent<|im_end|>\n

      This legacy fallback is NOT equivalent to Qwen3 non-thinking mode,
      which inserts an empty thinking prefix. Training must supply a native
      chat tokenizer explicitly, separately from a Rust token encoder.

    Args:
        messages:              List of ``{"role": str, "content": str}`` dicts.
        add_generation_prompt: Append ``<|im_start|>assistant\n`` suffix.
        tokenizer:             Optional explicit tokenizer; overrides the module
                               default registered via ``set_default_tokenizer``.
    """
    tok = tokenizer if tokenizer is not None else _DEFAULT_TOKENIZER
    if tok is not None and hasattr(tok, "apply_chat_template"):
        try:
            return tok.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=add_generation_prompt,
                enable_thinking=False,   # Disable Qwen3 native <think> blocks
            )
        except TypeError:
            # Older tokenizer without enable_thinking kwarg (Qwen2.5 fallback).
            return tok.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=add_generation_prompt,
            )

    # Legacy hand-rolled ChatML template (Qwen2.5 / offline fallback).
    formatted_parts = []
    for msg in messages:
        role = msg["role"]
        content = msg["content"].strip()
        formatted_parts.append(f"<|im_start|>{role}\n{content}<|im_end|>")

    prompt_str = "\n".join(formatted_parts)
    if add_generation_prompt:
        prompt_str += "\n<|im_start|>assistant\n"

    return prompt_str


# ==============================================================================
# 6. Site Pipeline Observation Formatter
# ==============================================================================

def format_site_observation(
    written_files: List[Tuple[str, str]],
    css_missing: bool,
    next_section: Optional[str],
    all_done: bool = False,
    extra_note: str = "",
    style_violations: Optional[List[str]] = None,
    structural_violations: Optional[List[str]] = None,
    available_tokens: Optional[List[str]] = None,
    css_truncated: Optional[List[str]] = None,
    css_coverage_gap: Optional[List[str]] = None,
) -> str:
    """
    Produces a structural observation for the site pipeline (not test results).
    Tells the model which files were accepted, flags missing CSS or design token
    conformance violations as hard failures, and instructs it on what to write next.

    Args:
        written_files:         List of (path, content) that were successfully written.
        css_missing:           True if the previous turn emitted no real CSS.
        next_section:          Human-readable description of what to write next, or None.
        all_done:              True when all required sections have been written.
        extra_note:            Optional free-form text appended to the observation.
        style_violations:      Optional list of design token violation descriptions.
        structural_violations: Optional list of structural lint violation descriptions.
        available_tokens:      Optional list of defined CSS variable names to remind the model.
        css_truncated:         Optional list of CSS syntax/truncation error messages.
        css_coverage_gap:      Optional list of unstyled class names used in TSX without CSS rules.
    """
    lines = []

    if all_done:
        lines.append('<observation status="complete">')
        lines.append("[SITE BUILD COMPLETE]: All required sections have been written successfully.")
        if written_files:
            lines.append("[Files written in this session]:")
            for p, _ in written_files:
                lines.append(f"  ✓ {p}")
        lines.append("Output a <finish> tag with a brief summary of the site you built.")
    else:
        if css_missing:
            lines.append('<observation status="failed">')
            lines.append(
                "[CSS MISSING — HARD FAILURE]: Your last tool_call produced no real CSS content.\n"
                "Every section MUST include visual CSS rules (colors, font sizes, layout, spacing).\n"
                "Empty, placeholder, or comment-only CSS is rejected. Rewrite this section with real styles."
            )
        elif css_truncated:
            lines.append('<observation status="failed">')
            viol_list = "\n".join(f"  ✗ {e}" for e in css_truncated)
            lines.append(
                f"[CSS TRUNCATED — REWRITE REQUIRED]: The emitted CSS is incomplete or truncated mid-declaration:\n"
                f"{viol_list}\n\n"
                f"REQUIRED: Every CSS block, declaration, and selector must be completely written and closed with matching braces '{{' '}}' and parentheses '(' ')'.\n"
                f"Rewrite this section with complete, fully-closed CSS."
            )
        elif css_coverage_gap:
            lines.append('<observation status="failed">')
            viol_list = "\n".join(f"  ✗ .{c}" for c in css_coverage_gap)
            lines.append(
                f"[CSS COVERAGE GAP — REWRITE REQUIRED]: The paired .tsx file uses classNames that have no corresponding styling rules in .css:\n"
                f"{viol_list}\n\n"
                f"REQUIRED: Every className used in the component markup (especially forms, inputs, buttons, cards) must have visual rules defined in the CSS.\n"
                f"Rewrite this section providing real style rules for these classes."
            )
        elif structural_violations:
            lines.append('<observation status="failed">')
            viol_list = "\n".join(f"  ✗ {v}" for v in structural_violations)
            lines.append(
                f"[STRUCTURAL LINT ERROR — REWRITE REQUIRED]:\n"
                f"Your generated section violates structural quality rules:\n"
                f"{viol_list}\n\n"
                f"RULES TO COMPLY:\n"
                f"1. Never use position: sticky on a section taller than a typical nav bar (roughly 100px). Sticky is for navigation headers only.\n"
                f"2. Never reuse the same CSS class name on different heading levels (e.g. <h2> and <h3> sharing a class). Use distinct classes for card headings vs section titles.\n"
                f"3. Metric and badge text must not duplicate the card title string. Provide authentic quantitative or descriptive values.\n"
                f"4. Undefined CSS variables in var(--xxx) are forbidden. You MUST use ONLY the defined tokens established in :root.\n"
                f"5. Repeated items must have display: flex/grid and gap declared on their direct parent container, not on an outer single-child wrapper.\n"
                f"6. CSS files must be syntactically complete with balanced braces and parentheses. All classNames in JSX must have CSS rules.\n"
                f"7. Never invent fake icon library names (like feather-mug-hot or feather-fire-flame-curved) or hallucinate raw SVG path coordinates. Use verified authentic inline SVGs (feather-mail, feather-phone, feather-map-pin, feather-coffee, feather-flame, feather-box, feather-check-circle, feather-star, feather-shield, feather-server, feather-cloud, feather-zap, feather-lock, feather-users, feather-arrow-right).\n"
                f"8. Never apply className=\"site-root\" or reference .site-root in CSS. The .site-root class is reserved exclusively for the global application wrapper.\n"
                f"9. Component must include a named export matching the component name (e.g. export function Hero() {{ ... }}).\n"
                f"Rewrite this section now to fix these structural errors."
            )
        elif style_violations:
            lines.append('<observation status="failed">')
            viol_list = "\n".join(f"  ✗ {v}" for v in style_violations)
            lines.append(
                f"[STYLE SPEC VIOLATION — REWRITE REQUIRED]:\n"
                f"Your generated CSS violates the active design system tokens:\n"
                f"{viol_list}\n\n"
                f"RULES TO COMPLY:\n"
                f"1. Use ONLY the CSS custom properties defined in App.css / :root (e.g. var(--color-*), var(--radius-*), var(--font-*)).\n"
                f"2. Never use hardcoded hex colors, unauthorized box-shadows, or conflicting border-radii.\n"
                f"Rewrite this section now to strictly conform to the design system."
            )
        elif extra_note and any(k in extra_note for k in ("CRITICAL", "ERROR", "MISMATCH", "FAILURE", "REWRITE REQUIRED")):
            lines.append('<observation status="failed">')
        else:
            lines.append('<observation status="ok">')
            if written_files:
                lines.append("[Files accepted]:")
                for p, _ in written_files:
                    lines.append(f"  ✓ {p}")

        if next_section:
            lines.append(f"\n[NEXT SECTION REQUIRED]: {next_section}")
            if available_tokens:
                token_list = sorted(f"--{t.lstrip('-')}" for t in available_tokens)
                sample_tokens = ", ".join(token_list[:35])
                suffix = "..." if len(token_list) > 35 else ""
                lines.append(f"[Available CSS Tokens]: {sample_tokens}{suffix} (use ONLY defined tokens in var(--name))")
            lines.append(
                "Write ONE <tool_call name=\"write_site\"> with exactly one .tsx file and one .css file for this section."
            )

    if extra_note:
        lines.append(f"\n{extra_note}")

    lines.append("</observation>")
    return "\n".join(lines)
