"""
agent_protocol.py - Action Space, System Contract, and Parsing Engine for Agentic SLMs
Tailored for Qwen2.5-Coder-3B-Instruct running on local hardware (RTX 4050 6GB).

Design Principles:
1. XML Tag-Based Action Protocol: Eliminates JSON string-escaping hallucination in 3B models.
2. Smart Observation Pruning: Preserves primary failure headlines & accessible roles within the 4096-token budget.
3. Forgiving Parser: Robustly extracts thoughts, tool calls, and final answers even if tags are partially malformed.
4. Dual-mode protocol: write_component (single atom) and write_site (multi-file page composition).
"""

import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, Tuple, Union

# ==============================================================================
# Unified Sequence Length Constants (Single Source of Truth)
# ==============================================================================
DEFAULT_MAX_SEQ_LENGTH = int(os.environ.get("SLM_MAX_SEQ_LENGTH", "9216"))
DEFAULT_INFERENCE_MAX_SEQ_LENGTH = int(os.environ.get("SLM_INFERENCE_MAX_SEQ_LENGTH", "8192"))
DEFAULT_MAX_NEW_TOKENS = int(os.environ.get("SLM_MAX_NEW_TOKENS", "4096"))


# ==============================================================================
# 1. System Prompt Contract
# ==============================================================================

AGENT_SYSTEM_PROMPT = """You are an expert autonomous React, TypeScript, and CSS coding agent.
Your objective is to write, test, and self-correct React components until they pass all type checks and Vitest/Testing Library test suites.

You interact with an automated testing environment using structured XML tags:

1. <thought>
Explain your reasoning, plan, or diagnose previous test failures. Always output a thought first.
</thought>

2. <tool_call name="write_component">
<tsx>
// Complete React + TypeScript component implementation
</tsx>
<css>
/* Optional CSS / CSS module code */
</css>
</tool_call>
Writes the component and optional CSS module to the workspace. The testing harness automatically runs TypeScript compilation (tsc --noEmit) and the Vitest test suite, returning results in an <observation>.

3. <finish>
Brief summary of your verified solution.
</finish>
Call this ONLY when you have verified that all tests pass, or when the task is fully complete.

OPERATING GUIDELINES:
- Every turn, output your <thought> first, followed by either ONE <tool_call> or <finish>.
- Write clean, type-safe TypeScript. Use proper React hooks, accessibility attributes (aria-*, role), and event handlers.
- Put all types, interfaces, and helper utilities in the single <tsx> block. Do not import third-party npm packages (e.g. lodash) or non-existent local files.
- Write only production React component code in <tsx>. Do NOT import test frameworks or runners ('vitest', '@testing-library', 'jest') inside <tsx>.
- Prop Fallback Aliasing: When implementing components where prompts are concise, support common standard prop aliases:
  * e.g. `const trendVal = props.trend ?? props.valueChange ?? props.change;`
  * e.g. `const initial = props.initialValues ?? props.initialState ?? props.defaultValues ?? {};`
  * e.g. `const labelVal = props.label ?? props.title ?? props.name;`
- Minimal Clean Logging Rule: When asked to log an action, event, or payload (e.g. `dispatchLogged`), log the exact payload directly with `console.log(action)` with no prepended string prefixes or extra arguments.
- Imperative DOM Dynamic Container Pattern: For imperative hooks (e.g. `useConfirm`, `useToast`, `usePrompt`) where callers invoke `await confirm(message)` or `toast(message)` without rendering a dialog component in their own JSX, the function must dynamically create its own DOM container in `document.body` (e.g. using `document.createElement('div')`, appending to `document.body`, and rendering with `createRoot` or DOM elements, resolving and cleaning up on dismissal).
- When you receive a test failure in <observation>, carefully inspect the error message and the rendered DOM, deduce what was missing or incorrect, and update the component.
- Do NOT output markdown code fences (```) around your <tool_call> tags.
"""


# ==============================================================================
# 1b. Site Agent System Prompt (multi-file page composition mode)
# ==============================================================================

SITE_AGENT_SYSTEM_PROMPT = """You are an expert autonomous React, TypeScript, and CSS coding agent specialising in full-page website composition.
Your objective is to build a complete, visually rich, multi-section website from a structured content brief, one section at a time.

You interact with an automated build environment using structured XML tags:

1. <thought>
Explain your plan for the current section, describe styling decisions, and acknowledge the content brief.
</thought>

2. <tool_call name="write_site">
<file path="src/components/Header.tsx">
// Complete React + TypeScript component for this section
</file>
<file path="src/components/Header.css">
/* Required CSS — NEVER leave empty. Every section MUST have visual styles. */
</file>
</tool_call>
Writes ONE section (one .tsx file + one .css file) per turn. The environment will confirm what was written and instruct you on the next section.

3. <finish>
Brief summary of all sections produced.
</finish>
Call this ONLY after the environment confirms all required sections are complete.

OPERATING GUIDELINES:
- Every turn: output <thought> first, then ONE <tool_call name="write_site"> with exactly one .tsx and one .css <file> pair.
- CSS is MANDATORY. Every section must have real visual rules (colors, typography, spacing, layout). Empty or placeholder CSS is a hard failure.
- Use modern CSS: flexbox/grid for layout, CSS custom properties for design tokens, responsive units (rem/%, vw).
- Write production-quality TypeScript. Keep all types inline — no third-party imports except react and react-dom.
- Reconcile prompt and brief: Honor the content brief data (business name, tagline, tiers) while incorporating any specific interactive capabilities requested in the user prompt (e.g. dark/light mode toggle in Header, active category tabs in Features, annual/monthly billing toggle in Pricing, and next/prev carousel pagination in Testimonials).
- Real Interactive State: For interactive sections (pricing toggles, tab filtering, carousels, mobile menus), write functional React state (`useState`, `useEffect`) rather than static unclickable elements.
- Clean Iconography: Use clean inline SVGs or standard FontAwesome icon classes (e.g. `fa-solid fa-check`, `fa-solid fa-bolt`, `fa-solid fa-star`, `fa-brands fa-github`).
- Do NOT output markdown code fences (```) around your <tool_call> tags.
- Do NOT combine multiple sections into one turn — one section per tool_call only.
"""


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
class RunTestsAction:
    pass

@dataclass
class FinishAction:
    summary: str

ActionType = Union[WriteComponentAction, WriteSiteAction, RunTestsAction, FinishAction, None]

@dataclass
class AgentTurn:
    thought: str
    action: ActionType
    raw_text: str

    @property
    def is_finish(self) -> bool:
        return isinstance(self.action, FinishAction)

    @property
    def is_tool_call(self) -> bool:
        return isinstance(self.action, (WriteComponentAction, WriteSiteAction, RunTestsAction))

    @property
    def is_write_site(self) -> bool:
        return isinstance(self.action, WriteSiteAction)


# ==============================================================================
# 3. Agent Output Parser
# ==============================================================================

def parse_agent_output(raw_text: str) -> AgentTurn:
    """
    Parses the raw generation from the model into an AgentTurn.
    Forgiving of minor model quirks like unclosed tags or mixed markdown.
    Priority order: write_site > write_component > run_tests > finish > fallback.
    write_site is checked first so site-mode outputs aren't misrouted to the component parser.
    """
    text = raw_text.strip()

    # 1. Extract <thought>
    thought = ""
    thought_match = re.search(r'<thought>([\s\S]*?)(?:</thought>|$)', text, re.IGNORECASE)
    if thought_match:
        thought = thought_match.group(1).strip()

    # 2. Check for <tool_call name="write_site"> FIRST (site pipeline)
    write_site_match = re.search(
        r'<tool_call\s+name=["\']write_site["\']>([\s\S]*?)(?:</tool_call>|$)',
        text,
        re.IGNORECASE
    )
    if write_site_match:
        body = write_site_match.group(1)
        # Extract all <file path="...">...</file> pairs
        file_matches = re.findall(
            r'<file\s+path=["\']([^"\'>]+)["\']>([\s\S]*?)(?:</file>|$)',
            body,
            re.IGNORECASE
        )
        files: List[Tuple[str, str]] = []
        for fpath, fcontent in file_matches:
            files.append((fpath.strip(), fcontent.strip()))

        clean_raw = text
        if "</tool_call>" in text:
            clean_raw = text[:text.find("</tool_call>") + len("</tool_call>")].strip()

        return AgentTurn(
            thought=thought,
            action=WriteSiteAction(files=files),
            raw_text=clean_raw
        )

    # 3. Check for <tool_call name="write_component">
    write_comp_match = re.search(
        r'<tool_call\s+name=["\']write_component["\']>([\s\S]*?)(?:</tool_call>|$)',
        text,
        re.IGNORECASE
    )
    if write_comp_match:
        body = write_comp_match.group(1)

        # Extract <tsx>
        tsx_match = re.search(r'<tsx>([\s\S]*?)(?:</tsx>|$)', body, re.IGNORECASE)
        # Extract <css>
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

        return AgentTurn(
            thought=thought,
            action=WriteComponentAction(tsx=tsx_code, css=css_code),
            raw_text=clean_raw
        )

    # 4. Check for <tool_call name="run_tests">
    run_tests_match = re.search(
        r'<tool_call\s+name=["\']run_tests["\']\s*(?:/>|>[\s\S]*?</tool_call>)',
        text,
        re.IGNORECASE
    )
    if run_tests_match:
        clean_raw = text
        if "</tool_call>" in text:
            clean_raw = text[:text.find("</tool_call>") + len("</tool_call>")].strip()
        return AgentTurn(thought=thought, action=RunTestsAction(), raw_text=clean_raw)

    # 5. Check for <finish>
    finish_match = re.search(r'<finish>([\s\S]*?)(?:</finish>|$)', text, re.IGNORECASE)
    if finish_match:
        summary = finish_match.group(1).strip()
        clean_raw = text
        if "</finish>" in text:
            clean_raw = text[:text.find("</finish>") + len("</finish>")].strip()
        return AgentTurn(thought=thought, action=FinishAction(summary=summary), raw_text=clean_raw)

    # 6. Fallback: If model generated code directly without <tool_call> wrapper
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

        return AgentTurn(
            thought=thought or "Writing component implementation.",
            action=WriteComponentAction(tsx=tsx_code, css=css_code),
            raw_text=text
        )

    # 7. If only thought or unrecognized action
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
# 5. Qwen2.5 ChatML Serialization
# ==============================================================================

def format_chatml(messages: List[Dict[str, str]], add_generation_prompt: bool = True) -> str:
    """
    Serializes messages into Qwen2.5's native ChatML template:
    <|im_start|>role\ncontent<|im_end|>\n
    """
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
) -> str:
    """
    Produces a structural observation for the site pipeline (not test results).
    Tells the model which files were accepted, flags missing CSS or design token
    conformance violations as hard failures, and instructs it on what to write next.

    Args:
        written_files:    List of (path, content) that were successfully written.
        css_missing:      True if the previous turn emitted no real CSS.
        next_section:     Human-readable description of what to write next, or None.
        all_done:         True when all required sections have been written.
        extra_note:       Optional free-form text appended to the observation.
        style_violations: Optional list of design token violation descriptions.
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
        else:
            lines.append('<observation status="ok">')
            if written_files:
                lines.append("[Files accepted]:")
                for p, _ in written_files:
                    lines.append(f"  ✓ {p}")

        if next_section:
            lines.append(f"\n[NEXT SECTION REQUIRED]: {next_section}")
            lines.append(
                "Write ONE <tool_call name=\"write_site\"> with exactly one .tsx file and one .css file for this section."
            )

    if extra_note:
        lines.append(f"\n{extra_note}")

    lines.append("</observation>")
    return "\n".join(lines)
