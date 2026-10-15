#!/usr/bin/env python3
"""
evaluate.py - High-Performance Vitest + jsdom + RTL Evaluation Driver
for React + TypeScript + CSS SLMs (Qwen3-4B / fine-tuned LoRA).

Features:
- Enforces exact named export matching in prompt instructions to eliminate import-mismatch false negatives.
- Auto-binds named exports + default export fallback in generated test files.
- Splits TSX component code and CSS modules into separate files.
- Evaluates across all 4 check variants:
    * tsc_only
    * tsc_and_render
    * tsc_render_a11y
    * tsc_render_interact
- Supports both fast Batch Mode (runs entire suite in 10-15s) and Sequential Mode.
- Stratified subsampling (--subset N) for rapid Step 9 retraining feedback loops.
- Mock mode (--mock) for instant pipeline and harness testing without GPU inference.
- Saves detailed results to JSON for error taxonomy and Step 9 failure analysis.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "agent"))


# Built-in RTL and testing utilities that should not be treated as component exports
STANDARD_TEST_IDENTIFIERS = {
    "it", "test", "describe", "expect", "render", "screen", "fireEvent",
    "userEvent", "vi", "act", "renderHook", "waitFor", "within", "rerender",
    "cleanup", "setup", "fn", "mockClear", "mockReset", "mockRestore",
    "mockImplementation", "mockReturnValue", "mockResolvedValue",
    "toHaveBeenCalled", "toHaveBeenCalledTimes", "toHaveBeenCalledWith",
    "toHaveBeenLastCalledWith", "toBeInTheDocument", "toBeVisible",
    "toHaveAttribute", "toHaveTextContent", "toBeChecked", "toHaveFocus",
    "toHaveLength", "toEqual", "toBe", "toBeNull", "not", "useFakeTimers",
    "useRealTimers", "advanceTimersByTime", "click", "type", "keyboard",
    "hover", "unhover", "focus", "blur", "mouseEnter", "mouseLeave",
    "change", "submit", "selectOptions", "deselectOptions", "upload",
    "clear", "getByRole", "getByText", "getByTestId", "getByLabelText",
    "getByPlaceholderText", "queryByRole", "queryByText", "queryByTestId",
    "findByRole", "findByText", "findByTestId", "getAllByRole", "getAllByText",
    "queryAllByRole", "findAllByRole", "closest", "map", "filter", "reduce",
    "forEach", "find", "includes", "push", "slice", "splice", "trim",
    "toLowerCase", "toUpperCase", "toString", "indexOf", "split", "join",
    "replace", "match", "String", "Number", "Boolean", "Array", "Object",
    "Error", "Promise", "setTimeout", "clearTimeout", "setInterval",
    "clearInterval", "console", "log", "warn", "error", "info",
    "TestHarness", "Greeting", "Row", "Wrapper", "Component",
    "user", "spy", "validate", "validateFn", "onSave", "onClose", "onChange",
    "onSearch", "onSelect", "onPageChange", "onRemove", "dispatch",
    "transition", "handleChange", "handleBlur", "handleSubmit", "items",
    "state", "result", "bar", "input", "trigger", "cells", "nodes", "rules",
    "return", "if", "else", "for", "while", "switch", "case", "break",
    "continue", "default", "try", "catch", "finally", "throw", "function",
    "class", "const", "let", "var", "import", "export", "new", "typeof",
    "instanceof", "void", "delete", "in", "of", "async", "await", "yield",
    "super", "this", "true", "false", "null", "undefined",
    "File", "FileList", "Blob", "FormData", "Headers", "Request", "Response",
    "URL", "URLSearchParams", "Event", "CustomEvent", "MouseEvent", "KeyboardEvent",
    "DragEvent", "TouchEvent", "FocusEvent", "InputEvent", "WheelEvent",
    "AnimationEvent", "TransitionEvent", "HTMLElement", "Element", "Node",
    "Document", "Window", "DataTransfer", "FileReader", "AbortController",
    "IntersectionObserver", "ResizeObserver", "MutationObserver",
    "Map", "Set", "WeakMap", "WeakSet", "Date", "RegExp", "Math", "JSON",
    "Symbol", "Proxy", "Reflect", "Intl", "Uint8Array", "ArrayBuffer",
    "document", "window", "navigator", "localStorage", "sessionStorage", "location", "history", "performance",
    "removeAttribute", "setAttribute", "getAttribute", "hasAttribute",
    "addEventListener", "removeEventListener", "dispatchEvent", "preventDefault", "stopPropagation",
    "querySelector", "querySelectorAll", "getElementById", "getElementsByClassName", "getElementsByTagName",
    "append", "appendChild", "removeChild", "replaceChild", "contains",
    "focus", "blur", "click", "scrollIntoView", "scrollTo", "scrollBy", "reset",
    "setup", "clear", "getItem", "setItem", "removeItem", "assign", "code",
    "React", "ReactDOM", "HTMLButtonElement", "HTMLInputElement", "HTMLDivElement",
    "HTMLAnchorElement", "HTMLSelectElement", "HTMLTextAreaElement", "HTMLSpanElement",
    "HTMLFormElement", "HTMLImageElement", "HTMLParagraphElement", "HTMLHeadingElement",
    "HTMLOListElement", "HTMLUListElement", "HTMLLIElement", "HTMLTableElement",
    "HTMLTableRowElement", "HTMLTableCellElement", "SVGElement",
    "toBeInstanceOf", "toHaveClass", "toBeDisabled", "toBeEnabled", "toHaveValue",
    "toBeRequired", "toBeInvalid", "toThrow", "toThrowError",
    "useFakeTimers", "useRealTimers", "runOnlyPendingTimers", "advanceTimersByTime"
}


def extract_expected_symbols(prompt: str, test_code: str) -> Tuple[List[str], Optional[str]]:
    """
    Extract expected exported symbols (components, hooks, functions) from prompt and test_code.
    Returns (all_detected_symbols, primary_symbol).
    """
    # Identify local declarations inside test_code to avoid collision with imported bindings
    declared_in_test = set(re.findall(r'\b(?:function|class|const|let|var)\s+([A-Za-z0-9_]+)', test_code))
    # Also capture destructured bindings: const [a, b] = ... or const { c, d } = ...
    for m in re.finditer(r'\b(?:const|let|var)\s*(?:\[([^\]]+)\]|\{([^}]+)\})', test_code):
        group_text = m.group(1) or m.group(2) or ""
        for var in re.findall(r'\b([A-Za-z_][A-Za-z0-9_]*)\b', group_text):
            declared_in_test.add(var)

    # 1. JSX tags <PascalCase
    jsx_tags = (
        set(re.findall(r'<([A-Z][A-Za-z0-9_]*)', test_code))
        - declared_in_test
        - STANDARD_TEST_IDENTIFIERS
    )
    # 2. Hooks: use[A-Z]... (excluding object methods like vi.useFakeTimers)
    hooks = set(re.findall(r'(?<!\.)\b(use[A-Z][A-Za-z0-9_]*)\b', test_code)) - declared_in_test - STANDARD_TEST_IDENTIFIERS
    # 3. Functions called directly: fnName(...)
    raw_calls = set(re.findall(r'(?<!\.)\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', test_code))
    target_calls = {c for c in raw_calls if c not in STANDARD_TEST_IDENTIFIERS and not c.startswith("on")} - declared_in_test

    # 4. Backticks in prompt (e.g., `Tooltip`, `useInterval(callback: () => void, ...)` )
    backticks = re.findall(r'`([^`]+)`', prompt)
    prompt_symbols_ordered: List[str] = []
    for bt in backticks:
        # Split on opening parenthesis or generic bracket to handle nested callback signatures
        clean = bt.split('(')[0].split('<')[0].split(':')[0].split('.')[0].strip()
        if re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', clean) and len(clean) > 1:
            if clean not in {'string', 'number', 'boolean', 'any', 'void', 'null', 'true', 'false', 'T', 'K', 'V', 'P'}:
                if clean not in prompt_symbols_ordered:
                    prompt_symbols_ordered.append(clean)
    prompt_symbols = set(prompt_symbols_ordered)

    valid_exports: Set[str] = set()
    for s in (jsx_tags | hooks | target_calls | prompt_symbols):
        if s in STANDARD_TEST_IDENTIFIERS or s in declared_in_test:
            continue
        # Exported React symbol must be PascalCase (Component), a Hook (use[A-Z]...), or a function directly invoked in test
        if re.match(r'^[A-Z][A-Za-z0-9_]*$', s) or re.match(r'^use[A-Z][A-Za-z0-9_]*$', s) or s in target_calls:
            valid_exports.add(s)

    detected = sorted(list(valid_exports))

    # Pick the most prominent primary symbol (respecting prompt mention order)
    primary = None
    if jsx_tags:
        matching_jsx = [s for s in prompt_symbols_ordered if s in jsx_tags]
        primary = matching_jsx[0] if matching_jsx else sorted(list(jsx_tags))[0]
    elif hooks:
        matching_hooks = [s for s in prompt_symbols_ordered if s in hooks]
        primary = matching_hooks[0] if matching_hooks else sorted(list(hooks))[0]
    elif prompt_symbols_ordered:
        prompt_react_symbols = [s for s in prompt_symbols_ordered if s in detected]
        primary = prompt_react_symbols[0] if prompt_react_symbols else prompt_symbols_ordered[0]
    elif detected:
        primary = detected[0]

    if primary and primary not in detected:
        detected.append(primary)
        detected.sort()

    return detected, primary


def resolve_expected_exports(item: Dict[str, Any]) -> Tuple[List[str], Optional[str]]:
    """Uses reviewed dataset metadata instead of fragile source-code heuristics.

    Older eval rows may not yet include metadata, in which case the conservative
    heuristic remains available for backwards compatibility. New or migrated rows
    must carry ``exports`` so a TypeScript generic such as ``HTMLDivElement`` can
    never become a requested component export.
    """
    declared = item.get("exports")
    if declared is not None:
        if not isinstance(declared, list) or not declared:
            raise ValueError("Eval item 'exports' must be a non-empty list")
        exports: List[str] = []
        for symbol in declared:
            if not isinstance(symbol, str) or not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", symbol):
                raise ValueError(f"Invalid export name: {symbol!r}")
            if symbol in STANDARD_TEST_IDENTIFIERS:
                raise ValueError(f"Built-in identifier cannot be an eval export: {symbol}")
            if symbol not in exports:
                exports.append(symbol)
        primary = item.get("primary_export") or exports[0]
        if primary not in exports:
            raise ValueError("Eval item 'primary_export' must appear in 'exports'")
        return exports, primary
    return extract_expected_symbols(item["prompt"], item["test_code"])


def build_augmented_prompt(prompt: str, primary_symbol: Optional[str], all_symbols: List[str]) -> str:
    """
    Appends export instructions to eliminate export-name mismatch false negatives.
    """
    instruction_lines = [prompt.strip()]
    if primary_symbol:
        if len(all_symbols) > 1:
            sym_list = ", ".join(f"`{s}`" for s in all_symbols[:3])
            instruction_lines.append(f"IMPORTANT: Export the following as named exports: {sym_list}.")
        else:
            instruction_lines.append(f"IMPORTANT: Export the component as a named export called `{primary_symbol}`.")
    else:
        instruction_lines.append("IMPORTANT: Ensure you provide named exports for the requested component/function.")

    full_instruction = "\n".join(instruction_lines)
    return f"### Instruction:\n{full_instruction}\n\n### Response:\n"


def split_code_and_css(generated_text: str) -> Tuple[str, Optional[str]]:
    """
    Splits the generated model output into TSX code and optional CSS/CSS Module code.
    Strips markdown code fences if present.
    """
    clean_text = generated_text.strip()
    
    # Check for markdown code blocks
    if "```" in clean_text:
        # Find tsx or typescript blocks
        tsx_match = re.search(r'```(?:tsx|typescript|jsx|javascript)?\s*\n([\s\S]*?)```', clean_text)
        css_match = re.search(r'```css\s*\n([\s\S]*?)```', clean_text)
        
        tsx_code = tsx_match.group(1).strip() if tsx_match else clean_text
        css_code = css_match.group(1).strip() if css_match else None
        
        # If no css code block, check for comment separator like /* styles.module.css */
        if not css_code and "/* " in tsx_code:
            parts = tsx_code.split("/* ", 1)
            tsx_code = parts[0].strip()
            css_code = "/* " + parts[1].strip()
            
        return tsx_code, css_code

    # If not fenced, split on standard runbook format: /* Component.module.css */
    if "/* " in clean_text:
        parts = clean_text.split("/* ", 1)
        tsx_code = parts[0].strip()
        css_code = "/* " + parts[1].strip()
        return tsx_code, css_code

    return clean_text, None


def strip_test_imports(code: str) -> str:
    """
    Strips top-level imports of React, Vitest, Testing Library, and ./Component
    from test_code to avoid duplicate declaration collisions when prepended with
    the test runner's standard test harness header.
    """
    # 1. Match multi-line or single-line imports from packages we already inject
    import_from_pattern = r'import\s+[\s\S]*?from\s*[\'"][^\'"]+[\'"];?'
    def repl_from(m):
        txt = m.group(0)
        if any(pkg in txt for pkg in ['./Component', 'vitest', '@testing-library', "'react'", '"react"']):
            return ''
        return txt
    cleaned = re.sub(import_from_pattern, repl_from, code)

    # 2. Match side-effect imports like import '@testing-library/jest-dom';
    side_pattern = r'import\s+[\'"][^\'"]+[\'"];?'
    def repl_side(m):
        txt = m.group(0)
        if any(pkg in txt for pkg in ['./Component', 'vitest', '@testing-library']):
            return ''
        return txt
    cleaned = re.sub(side_pattern, repl_side, cleaned)

    return re.sub(r'\n{3,}', '\n\n', cleaned).strip()


def generate_test_file_content(
    test_code: str,
    all_symbols: List[str],
    primary_symbol: Optional[str]
) -> str:
    """
    Assembles the Vitest + Testing Library test file with proper imports,
    global bindings, and fallback support for default exports.
    """
    bindings = []
    for sym in all_symbols:
        # Auto-bind named export, with fallback to default export if named export was omitted
        if sym == primary_symbol:
            bindings.append(f"const {sym} = (__Mod as any).{sym} ?? (__Mod as any).default;")
        else:
            bindings.append(f"const {sym} = (__Mod as any).{sym};")

    bindings_code = "\n".join(bindings)

    # If test_code contains @playwright/test, wrap or guard it
    if "@playwright/test" in test_code:
        return f"""// Playwright-specific test skipped in Vitest jsdom harness
import {{ describe, it }} from 'vitest';
describe('Playwright browser test (skipped in jsdom)', () => {{
  it.skip('requires real browser for focus-visible styles', () => {{}});
}});
"""

    cleaned_test_code = strip_test_imports(test_code)

    return f"""import React, {{ useState, useEffect, useRef, useMemo, useCallback }} from 'react';
import {{ render, screen, fireEvent, act, renderHook, waitFor, within }} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {{ vi, describe, it, test, expect, beforeEach, afterEach }} from 'vitest';
import '@testing-library/jest-dom';

import * as __Mod from './Component';

// Injected component bindings
{bindings_code}

// Test case
{cleaned_test_code}
"""



def get_stratified_sample(
    items: List[Dict[str, Any]],
    n: int,
    seed: int = 42
) -> List[Tuple[int, Dict[str, Any]]]:
    """
    Returns a stratified sample of n items preserving category proportions.
    Returns list of (original_index, item).
    """
    import random
    rng = random.Random(seed)
    
    by_category: Dict[str, List[Tuple[int, Dict[str, Any]]]] = {}
    for idx, item in enumerate(items):
        cat = item.get("check", "tsc_and_render")
        by_category.setdefault(cat, []).append((idx, item))

    total = len(items)
    if n >= total:
        return list(enumerate(items))

    sampled: List[Tuple[int, Dict[str, Any]]] = []
    for cat, group in by_category.items():
        # Proportional count, at least 1 per category if available
        cat_n = max(1, round(len(group) / total * n))
        cat_n = min(cat_n, len(group))
        sampled.extend(rng.sample(group, cat_n))

    # Adjust if slight rounding discrepancy
    if len(sampled) > n:
        sampled = rng.sample(sampled, n)
    elif len(sampled) < n:
        remaining = [item for item in enumerate(items) if item not in sampled]
        sampled.extend(rng.sample(remaining, min(n - len(sampled), len(remaining))))

    return sorted(sampled, key=lambda x: x[0])


def generate_mock_code(item: Dict[str, Any], primary_symbol: Optional[str]) -> str:
    """
    Mock code generator for testing the test harness end-to-end without loading GPU models.
    """
    name = primary_symbol or "Component"
    prompt = item["prompt"]
    test_code = item["test_code"]

    # Reducer mock
    if "cartReducer" in prompt or "cartReducer" in test_code:
        return """import React, { useReducer } from 'react';
export type CartState = { items: Array<{ id: string; qty: number }> };
export type CartAction = { type: 'ADD_ITEM'; item: { id: string; qty: number } } | { type: 'REMOVE_ITEM'; id: string } | { type: 'CLEAR' };
export function cartReducer(state: CartState, action: CartAction): CartState {
  switch (action.type) {
    case 'ADD_ITEM': return { items: [...state.items, action.item] };
    case 'REMOVE_ITEM': return { items: state.items.filter(i => i.id !== action.id) };
    case 'CLEAR': return { items: [] };
    default: return state;
  }
}
export function useCart() {
  const [state, dispatch] = useReducer(cartReducer, { items: [] });
  return { state, dispatch };
}
"""

    if name == "Modal":
        return """import React, { useEffect } from 'react';
export function Modal({ isOpen, onClose, children }: any) {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && onClose) onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  if (!isOpen) return null;
  return (
    <div>
      <div data-testid="modal-backdrop" onClick={onClose} />
      <div>{children}</div>
    </div>
  );
}
"""

    if name == "Chip":
        return """import React from 'react';
export function Chip({ label, onRemove }: any) {
  return (
    <div>
      <span>{label}</span>
      {onRemove && (
        <button aria-label="remove" onClick={onRemove}>x</button>
      )}
    </div>
  );
}
"""

    if name == "Breadcrumbs":
        return """import React from 'react';
export function Breadcrumbs({ items }: any) {
  return (
    <nav aria-label="Breadcrumb">
      {items.map((item: any, i: number) => {
        const isLast = i === items.length - 1;
        return isLast ? (
          <span key={i} aria-current="page">{item.label}</span>
        ) : (
          <a key={i} href={item.href || '#'}>{item.label}</a>
        );
      })}
    </nav>
  );
}
"""

    # Toast mock
    if "Toast" in name or "useToast" in test_code:
        return """import React, { createContext, useContext, useState } from 'react';
const ToastCtx = createContext<any>(null);
export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [msg, setMsg] = useState<string | null>(null);
  const toast = {
    success: (m: string) => setMsg(m),
    error: (m: string) => setMsg(m)
  };
  return (
    <ToastCtx.Provider value={toast}>
      {children}
      {msg && <div>{msg}</div>}
    </ToastCtx.Provider>
  );
}
export function useToast() {
  return useContext(ToastCtx);
}
"""

    # Hook mock
    if name.startswith("use"):
        return f"""import React, {{ useState }} from 'react';
export function {name}(...args: any[]) {{
  const [state, setState] = useState<any>(args[0] || 'red');
  return {{
    state,
    transition: (next: any) => setState(next),
    dispatchLogged: (act: any) => {{ console.log(act); setState((s: any) => s + 1); }},
    isValid: true,
    handleChange: () => {{}},
    handleBlur: () => {{}},
    handleSubmit: () => {{}}
  }};
}}
"""

    # Generic component mock that renders children and common roles
    return f"""import React, {{ useState }} from 'react';
import styles from './Component.module.css';

export function {name}(props: any) {{
  const [open, setOpen] = useState(false);
  return (
    <div
      data-testid="modal-backdrop"
      data-variant={{props.variant || 'circle'}}
      role={{props.role || 'status'}}
      aria-valuenow={{props.value}}
      aria-valuemin={{0}}
      aria-valuemax={{props.max}}
      aria-expanded={{!props.isCollapsed}}
      aria-current="step"
      onClick={{props.onClose || props.onClick || (() => props.onChange && props.onChange(true))}}
    >
      <button onClick={{() => props.onPageChange && props.onPageChange(3)}}>3</button>
      <button aria-label="dismiss" onClick={{props.onRemove}}>Dismiss</button>
      <span>AL</span>
      <span>+1</span>
      <span>Loading</span>
      <span>Helpful hint</span>
      <span>Modal content</span>
      <span>First content</span>
      <span>Second content</span>
      <span>Panel A</span>
      <span>Panel B</span>
      <span>Shipping</span>
      <span>Child</span>
      <span>Amy</span>
      <span>Apple</span>
      <input role="textbox" role="combobox" aria-label="Blue" onChange={{(e) => props.onChange && props.onChange(['blue'])}} />
      <span role="radio" aria-label="Small" tabIndex={{0}}></span>
      <span role="radio" aria-label="Medium" tabIndex={{0}}></span>
      <div role="slider" tabIndex={{0}} aria-valuenow={{props.value}}></div>
      <div role="switch" onClick={{() => props.onChange && props.onChange(true)}}></div>
      {{props.children}}
    </div>
  );
}}
/* Component.module.css */
.root {{ display: block; }}
"""


def _resolve_executable(exe: str) -> str:
    """Resolves executable path, ensuring .cmd/.exe shims on Windows are found for shell=False."""
    resolved = shutil.which(exe)
    if resolved:
        return resolved
    if os.name == "nt" and not exe.lower().endswith((".cmd", ".exe", ".bat")):
        for ext in (".cmd", ".exe", ".bat"):
            candidate = shutil.which(exe + ext)
            if candidate:
                return candidate
    return exe


def run_command(cmd: List[str], cwd: Optional[Path] = None, timeout: Optional[int] = 30) -> subprocess.CompletedProcess:
    if cwd is None:
        cwd = BASE_DIR
    """Executes a command safely with shell=False, resolving .cmd/.exe shims on Windows to prevent shell injection."""
    actual_cwd = str(cwd) if cwd is not None else str(Path.cwd())
    cmd_list = list(cmd) if isinstance(cmd, (list, tuple)) else [cmd]

    if cmd_list:
        cmd_list[0] = _resolve_executable(str(cmd_list[0]))

    try:
        return subprocess.run(
            cmd_list,
            cwd=actual_cwd,
            capture_output=True,
            text=True,
            shell=False,
            encoding="utf-8",
            errors="replace",
            timeout=timeout
        )
    except subprocess.TimeoutExpired as e:
        out = e.stdout or ""
        if isinstance(out, bytes):
            out = out.decode("utf-8", errors="replace")
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=-1,
            stdout=out,
            stderr=f"Command timed out after {timeout} seconds."
        )
    except Exception as exc:
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=-1,
            stdout="",
            stderr=f"Failed to execute command: {exc}"
        )


def write_typecheck_config(config_dir: Path, component_dirs: List[Path]) -> Path:
    """Creates a self-contained, strict TypeScript project for generated code.

    Running ``tsc`` with a source filename ignores the root tsconfig while running
    it without one can accidentally include unrelated generated cases. This small
    project makes batch and sequential scoring equivalent.
    """
    css_declarations = Path.cwd() / "css.d.ts"
    files = [os.path.relpath(css_declarations, config_dir)]
    files.extend(os.path.relpath(case_dir / "Component.tsx", config_dir) for case_dir in component_dirs)
    config = {
        "compilerOptions": {
            "target": "ES2022",
            "lib": ["DOM", "DOM.Iterable", "ES2022"],
            "module": "ESNext",
            "moduleResolution": "bundler",
            "jsx": "react-jsx",
            "strict": True,
            "esModuleInterop": True,
            "skipLibCheck": True,
            "noEmit": True,
        },
        "files": files,
    }
    config_path = config_dir / "tsconfig.eval.json"
    config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    return config_path


def run_typecheck(config_dir: Path, component_dirs: List[Path]) -> subprocess.CompletedProcess:
    config_path = write_typecheck_config(config_dir, component_dirs)
    return run_command(["npx", "tsc", "--project", str(config_path)], cwd=config_dir)


class ModelEvaluator:
    def __init__(
        self,
        model_name: str,
        max_seq_length: int = 8192,
        is_mock: bool = False,
        agent_protocol: bool = False,
    ):
        self.model_name = model_name
        self.max_seq_length = max_seq_length
        self.is_mock = is_mock
        self.agent_protocol = agent_protocol
        self.model = None
        self.tokenizer = None

        if not is_mock:
            self._init_model()

    def _init_model(self):
        print(f"Loading model: {self.model_name}...")
        try:
            from unsloth import FastLanguageModel
            self.model, self.tokenizer = FastLanguageModel.from_pretrained(
                model_name=self.model_name,
                max_seq_length=self.max_seq_length,
                load_in_4bit=True,
            )
            FastLanguageModel.for_inference(self.model)
            try:
                from agent.agent_protocol import set_default_tokenizer
            except (ImportError, ModuleNotFoundError):
                from agent_protocol import set_default_tokenizer
            set_default_tokenizer(self.tokenizer)
            print("Model loaded successfully with Unsloth.")
        except Exception as e:
            print(f"Unsloth load note ({e}), attempting standard transformers...")
            from transformers import AutoModelForCausalLM, AutoTokenizer
            import torch
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                torch_dtype=torch.float16,
                device_map="auto"
            )
            print("Model loaded with transformers.")
            try:
                from agent.agent_protocol import set_default_tokenizer
            except (ImportError, ModuleNotFoundError):
                from agent_protocol import set_default_tokenizer
            set_default_tokenizer(self.tokenizer)

    def generate(
        self,
        prompt: str,
        max_new_tokens: int = 768,
        temperature: float = 0.2
    ) -> str:
        if self.is_mock:
            return ""

        import torch
        if self.agent_protocol:
            from agent_protocol import AGENT_SYSTEM_PROMPT, WriteComponentAction, WriteSiteAction, format_chatml, parse_agent_output

            instruction = prompt
            if "### Instruction:\n" in instruction:
                instruction = instruction.split("### Instruction:\n", 1)[1]
            if "\n\n### Response:" in instruction:
                instruction = instruction.split("\n\n### Response:", 1)[0]
            prompt = format_chatml(
                [
                    {"role": "system", "content": AGENT_SYSTEM_PROMPT},
                    {"role": "user", "content": instruction},
                ],
                add_generation_prompt=True,
            )

        inputs = self.tokenizer(prompt, return_tensors="pt").to("cuda")
        with torch.no_grad():
            output = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                do_sample=(temperature > 0),
                pad_token_id=self.tokenizer.eos_token_id
            )
        completion_tokens = output[0][inputs.input_ids.shape[1]:]
        generated = self.tokenizer.decode(completion_tokens, skip_special_tokens=True)
        # Strip Qwen3 native <think> thinking blocks from decoded output.
        generated = re.sub(r'<think>[\s\S]*?</think>\s*', '', generated, flags=re.DOTALL).strip()
        if self.agent_protocol:
            turn = parse_agent_output(generated)
            if isinstance(turn.action, WriteComponentAction):
                if turn.action.css:
                    return f"{turn.action.tsx}\n/* Component.module.css */\n{turn.action.css}"
                return turn.action.tsx
            if isinstance(turn.action, WriteSiteAction) and turn.action.files:
                tsx_code = ""
                css_code = ""
                for fpath, fcontent in turn.action.files:
                    if fpath.endswith(('.tsx', '.ts')):
                        tsx_code = fcontent
                    elif fpath.endswith('.css'):
                        css_code = fcontent
                if tsx_code:
                    if css_code:
                        return f"{tsx_code}\n/* Component.module.css */\n{css_code}"
                    return tsx_code
            # Robust fallback for XML file tags
            file_matches = re.findall(r'<file path="([^"]*)">\s*([\s\S]*?)\s*</file>', generated)
            if file_matches:
                tsx_code = ""
                css_code = ""
                for fpath, fcontent in file_matches:
                    if fpath.endswith(('.tsx', '.ts')):
                        tsx_code = fcontent.strip()
                    elif fpath.endswith('.css'):
                        css_code = fcontent.strip()
                if tsx_code:
                    if css_code:
                        return f"{tsx_code}\n/* Component.module.css */\n{css_code}"
                    return tsx_code
            return ""
        if "### Response:\n" in generated:
            return generated.split("### Response:\n")[-1].strip()
        return generated.strip()


def evaluate_batch(
    eval_items: List[Tuple[int, Dict[str, Any]]],
    evaluator: ModelEvaluator,
    workspace_dir: Path,
    max_new_tokens: int = 768,
    temperature: float = 0.2
) -> List[Dict[str, Any]]:
    """
    High-speed batch evaluation:
    1. Generates all code outputs.
    2. Writes all test files to workspace.
    3. Runs tsc --noEmit once.
    4. Runs vitest run once with JSON reporter.
    """
    print(f"\n[Batch Mode] Preparing {len(eval_items)} evaluation cases...")
    test_dirs: List[Path] = []
    item_metadata: List[Dict[str, Any]] = []

    for i, (orig_idx, item) in enumerate(eval_items):
        prompt = item["prompt"]
        test_code = item["test_code"]
        check_variant = item.get("check", "tsc_and_render")

        all_symbols, primary_symbol = resolve_expected_exports(item)
        aug_prompt = build_augmented_prompt(prompt, primary_symbol, all_symbols)

        # 1. Model inference or mock
        if evaluator.is_mock:
            raw_generated = generate_mock_code(item, primary_symbol)
        else:
            print(f"[{i+1}/{len(eval_items)}] Generating response for Item #{orig_idx+1} ({primary_symbol})...")
            raw_generated = evaluator.generate(aug_prompt, max_new_tokens, temperature)

        tsx_code, css_code = split_code_and_css(raw_generated)
        test_file_code = generate_test_file_content(test_code, all_symbols, primary_symbol)

        case_dir = workspace_dir / f"case_{orig_idx:03d}"
        case_dir.mkdir(parents=True, exist_ok=True)
        test_dirs.append(case_dir)

        # Write Component.tsx
        (case_dir / "Component.tsx").write_text(tsx_code, encoding="utf-8")
        # Write CSS module
        css_content = css_code if css_code else "/* empty styles */"
        (case_dir / "Component.module.css").write_text(css_content, encoding="utf-8")
        for css_import in re.findall(r"import\s+['\"](\./[^'\"]+\.css)['\"]", tsx_code):
            (case_dir / Path(css_import).name).write_text(css_content, encoding="utf-8")
        # Write Component.test.tsx
        (case_dir / "Component.test.tsx").write_text(test_file_code, encoding="utf-8")

        item_metadata.append({
            "index": orig_idx,
            "check": check_variant,
            "primary_symbol": primary_symbol,
            "all_symbols": all_symbols,
            "prompt": prompt,
            "generated_code": raw_generated,
            "case_dir": case_dir,
            "test_file": case_dir / "Component.test.tsx"
        })

    # Step 1: Typecheck all cases with tsc
    print("\n[Step 1/2] Running isolated strict TypeScript check...")
    tsc_res = run_typecheck(workspace_dir, test_dirs)
    tsc_output = tsc_res.stdout + "\n" + tsc_res.stderr

    # Map tsc errors per case
    for meta in item_metadata:
        case_folder_name = meta["case_dir"].name
        # If folder name appears in tsc output with an error, mark failed
        has_tsc_error = f"{case_folder_name}/" in tsc_output or f"{case_folder_name}\\" in tsc_output
        meta["tsc_passed"] = not has_tsc_error
        meta["tsc_error"] = "\n".join([l for l in tsc_output.splitlines() if case_folder_name in l]) if has_tsc_error else ""

    # Step 2: Run Vitest across workspace with JSON reporter
    print("[Step 2/2] Running Vitest suite (concurrent execution across all files)...")
    report_file = workspace_dir / "vitest_results.json"
    if report_file.exists():
        report_file.unlink()

    vitest_cmd = [
        "npx", "vitest", "run",
        "--config", "vitest.config.ts",
        "--reporter=json",
        f"--outputFile={report_file}",
        str(workspace_dir.relative_to(Path.cwd()))
    ]
    vitest_proc = run_command(vitest_cmd, cwd=Path.cwd())

    # Parse Vitest results
    vitest_data = {}
    if report_file.exists():
        try:
            vitest_data = json.loads(report_file.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"Warning: could not parse vitest JSON report: {e}")

    # Map test results per test file
    test_results_by_path = {}
    for test_result in vitest_data.get("testResults", []):
        file_path = Path(test_result.get("name", "")).resolve()
        status = test_result.get("status", "failed")
        msg = test_result.get("message", "").strip()
        if not msg and test_result.get("assertionResults"):
            for ar in test_result["assertionResults"]:
                if ar.get("status") == "failed" and ar.get("failureMessages"):
                    msg = "\n".join(ar["failureMessages"])
                    break
        test_results_by_path[file_path] = (status == "passed", msg)

    results = []
    for meta in item_metadata:
        test_file_resolved = meta["test_file"].resolve()
        vitest_passed, vitest_err = test_results_by_path.get(test_file_resolved, (False, "Test did not complete"))

        # A skipped browser test is not a passing test. Keep it visible in the
        # report rather than silently inflating the pass rate.
        skipped = False
        if "@playwright/test" in meta["prompt"] or "Playwright" in meta["test_file"].read_text(encoding="utf-8"):
            vitest_passed = False
            vitest_err = "Playwright browser test skipped in jsdom; excluded from pass rate"
            skipped = True

        check = meta["check"]
        tsc_passed = meta["tsc_passed"]

        # Apply check variant rules
        if check == "tsc_only":
            overall_passed = tsc_passed and vitest_passed
        elif check in ("tsc_and_render", "tsc_render_a11y", "tsc_render_interact"):
            overall_passed = tsc_passed and vitest_passed
        else:
            overall_passed = tsc_passed and vitest_passed

        results.append({
            "index": meta["index"],
            "check": check,
            "primary_symbol": meta["primary_symbol"],
            "tsc_passed": tsc_passed,
            "vitest_passed": vitest_passed,
            "overall_passed": overall_passed,
            "skipped": skipped,
            "tsc_error": meta["tsc_error"],
            "vitest_error": vitest_err,
            "prompt": meta["prompt"],
            "generated_code": meta["generated_code"]
        })

    return results


def evaluate_sequential(
    eval_items: List[Tuple[int, Dict[str, Any]]],
    evaluator: ModelEvaluator,
    workspace_dir: Path,
    max_new_tokens: int = 768,
    temperature: float = 0.2
) -> List[Dict[str, Any]]:
    """
    Sequential evaluation mode: executes each item in isolation with live progress reporting.
    """
    print(f"\n[Sequential Mode] Evaluating {len(eval_items)} test cases one by one...")
    results = []

    for i, (orig_idx, item) in enumerate(eval_items):
        prompt = item["prompt"]
        test_code = item["test_code"]
        check_variant = item.get("check", "tsc_and_render")

        all_symbols, primary_symbol = resolve_expected_exports(item)
        aug_prompt = build_augmented_prompt(prompt, primary_symbol, all_symbols)

        if evaluator.is_mock:
            raw_generated = generate_mock_code(item, primary_symbol)
        else:
            print(f"[{i+1}/{len(eval_items)}] Generating response for Item #{orig_idx+1} ({primary_symbol})...")
            raw_generated = evaluator.generate(aug_prompt, max_new_tokens, temperature)

        tsx_code, css_code = split_code_and_css(raw_generated)
        test_file_code = generate_test_file_content(test_code, all_symbols, primary_symbol)

        case_dir = workspace_dir / f"case_{orig_idx:03d}"
        case_dir.mkdir(parents=True, exist_ok=True)

        (case_dir / "Component.tsx").write_text(tsx_code, encoding="utf-8")
        css_content = css_code or "/* styles */"
        (case_dir / "Component.module.css").write_text(css_content, encoding="utf-8")
        for css_import in re.findall(r"import\s+['\"](\./[^'\"]+\.css)['\"]", tsx_code):
            (case_dir / Path(css_import).name).write_text(css_content, encoding="utf-8")
        test_file = case_dir / "Component.test.tsx"
        test_file.write_text(test_file_code, encoding="utf-8")

        # Use the identical isolated strict compiler project as batch mode.
        tsc_res = run_typecheck(case_dir, [case_dir])
        tsc_passed = (tsc_res.returncode == 0)

        # Run vitest on this test file
        skipped = False
        if "@playwright/test" in test_code:
            vitest_passed = False
            vitest_err = "Playwright test skipped; excluded from pass rate"
            skipped = True
        else:
            vitest_res = run_command(
                ["npx", "vitest", "run", "--config", "vitest.config.ts", str(test_file)],
                cwd=Path.cwd()
            )
            vitest_passed = (vitest_res.returncode == 0)
            vitest_err = vitest_res.stderr if not vitest_passed else ""

        overall_passed = tsc_passed and vitest_passed
        status_sym = "[PASS]" if overall_passed else "[FAIL]"
        print(f"[{i+1}/{len(eval_items)}] {status_sym} #{orig_idx+1} {primary_symbol} ({check_variant}) | tsc={tsc_passed}, vitest={vitest_passed}")

        results.append({
            "index": orig_idx,
            "check": check_variant,
            "primary_symbol": primary_symbol,
            "tsc_passed": tsc_passed,
            "vitest_passed": vitest_passed,
            "overall_passed": overall_passed,
            "skipped": skipped,
            "tsc_error": tsc_res.stderr if not tsc_passed else "",
            "vitest_error": vitest_err,
            "prompt": prompt,
            "generated_code": raw_generated
        })

    return results


def print_summary_report(results: List[Dict[str, Any]]):
    """Prints compile, unit-test, and end-to-end rates without relabeling tests."""
    by_category: Dict[str, List[Dict[str, Any]]] = {}
    for r in results:
        by_category.setdefault(r["check"], []).append(r)

    print("\n" + "=" * 78)
    print("                 EVALUATION RESULTS SUMMARY REPORT                 ")
    print("=" * 78)
    print(f"{'Category':<24} {'Count':<8} {'Passed':<8} {'Pass %':<10} {'TSC %':<10} {'Vitest %':<10}")
    print("-" * 78)

    categories = ["tsc_only", "tsc_and_render", "tsc_render_a11y", "tsc_render_interact"]
    for cat in categories:
        group = by_category.get(cat, [])
        if not group:
            continue
        scored = [r for r in group if not r.get("skipped", False)]
        total = len(scored)
        skipped = len(group) - total
        if not total:
            print(f"{cat:<24} {'0':<8} {'0':<8} {'n/a':<10} {'n/a':<10} {'n/a':<10} ({skipped} skipped)")
            continue
        passed = sum(1 for r in scored if r["overall_passed"])
        tsc_pass = sum(1 for r in scored if r["tsc_passed"])
        vitest_pass = sum(1 for r in scored if r["vitest_passed"])
        suffix = f" ({skipped} skipped)" if skipped else ""
        print(f"{cat:<24} {total:<8} {passed:<8} {100*passed/total:>6.1f}%   {100*tsc_pass/total:>6.1f}%   {100*vitest_pass/total:>6.1f}%{suffix}")

    print("-" * 78)
    scored_all = [r for r in results if not r.get("skipped", False)]
    total_all = len(scored_all)
    passed_all = sum(1 for r in scored_all if r["overall_passed"])
    tsc_all = sum(1 for r in scored_all if r["tsc_passed"])
    vitest_all = sum(1 for r in scored_all if r["vitest_passed"])
    if total_all:
        print(f"{'OVERALL':<24} {total_all:<8} {passed_all:<8} {100*passed_all/total_all:>6.1f}%   {100*tsc_all/total_all:>6.1f}%   {100*vitest_all/total_all:>6.1f}%")
    else:
        print(f"{'OVERALL':<24} {'0':<8} {'0':<8} {'n/a':<10} {'n/a':<10} {'n/a':<10}")
    print("=" * 78)


def main():
    parser = argparse.ArgumentParser(description="Vitest + jsdom + RTL evaluation driver for React TS CSS SLM.")
    parser.add_argument("--model", type=str, default="./base-model", help="Path or HuggingFace ID of model.")
    default_eval = str(BASE_DIR / "data" / "eval" / "react_ts_css_eval_set_combined.jsonl")
    if not Path(default_eval).exists():
        default_eval = "react_ts_css_eval_set_combined.jsonl"
    parser.add_argument("--eval-set", type=str, default=default_eval, help="Path to JSONL eval set.")
    parser.add_argument("--subset", type=int, default=None, help="Sample N items using stratified sampling.")
    parser.add_argument("--mode", choices=["batch", "sequential"], default="batch", help="Execution mode (default: batch for 10x speed).")
    parser.add_argument("--mock", action="store_true", help="Run mock generator without loading GPU weights.")
    parser.add_argument(
        "--agent-protocol",
        action="store_true",
        help="Prompt the model with the same ChatML/XML contract used by agent.py (one-shot only).",
    )
    parser.add_argument("--output", type=str, default="eval_results.json", help="Path to save output report JSON.")
    parser.add_argument("--max-new-tokens", type=int, default=768, help="Max tokens to generate per example.")
    parser.add_argument("--temperature", type=float, default=0.2, help="Sampling temperature.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for sampling.")

    args = parser.parse_args()

    eval_file = Path(args.eval_set)
    if not eval_file.exists():
        print(f"Error: Evaluation set not found at {eval_file}")
        sys.exit(1)

    print(f"Loading evaluation dataset: {eval_file}")
    with open(eval_file, encoding="utf-8") as f:
        all_items = [json.loads(line) for line in f if line.strip()]

    print(f"Total examples in dataset: {len(all_items)}")

    # Subsetting
    if args.subset and args.subset < len(all_items):
        selected_items = get_stratified_sample(all_items, args.subset, seed=args.seed)
        print(f"Sampled {len(selected_items)} examples across all 4 check categories (stratified).")
    else:
        selected_items = list(enumerate(all_items))

    # Initialize evaluator
    evaluator = ModelEvaluator(
        model_name=args.model,
        is_mock=args.mock,
        agent_protocol=args.agent_protocol,
    )

    # Prepare temp eval workspace
    workspace_dir = Path.cwd() / ".eval_workspace"
    if workspace_dir.exists():
        shutil.rmtree(workspace_dir)
    workspace_dir.mkdir(parents=True, exist_ok=True)

    start_time = time.time()

    try:
        if args.mode == "batch":
            results = evaluate_batch(
                eval_items=selected_items,
                evaluator=evaluator,
                workspace_dir=workspace_dir,
                max_new_tokens=args.max_new_tokens,
                temperature=args.temperature
            )
        else:
            results = evaluate_sequential(
                eval_items=selected_items,
                evaluator=evaluator,
                workspace_dir=workspace_dir,
                max_new_tokens=args.max_new_tokens,
                temperature=args.temperature
            )
    finally:
        # Keep workspace for inspection or clean up as needed
        pass

    elapsed = time.time() - start_time
    print(f"\nEvaluation completed in {elapsed:.1f} seconds.")

    # Print summary
    print_summary_report(results)

    # Save output JSON
    output_path = Path(args.output)
    scored_results = [r for r in results if not r.get("skipped", False)]
    report_data = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "model": args.model,
        "mode": args.mode,
        "is_mock": args.mock,
        "agent_protocol": args.agent_protocol,
        "total_evaluated": len(results),
        "total_scored": len(scored_results),
        "skipped": len(results) - len(scored_results),
        "overall_pass_rate": sum(1 for r in scored_results if r["overall_passed"]) / len(scored_results) if scored_results else 0,
        "typecheck_pass_rate": sum(1 for r in scored_results if r["tsc_passed"]) / len(scored_results) if scored_results else 0,
        "unit_test_pass_rate": sum(1 for r in scored_results if r["vitest_passed"]) / len(scored_results) if scored_results else 0,
        "elapsed_seconds": elapsed,
        "results": results
    }
    output_path.write_text(json.dumps(report_data, indent=2), encoding="utf-8")
    print(f"\nDetailed JSON report saved to: {output_path.resolve()}")


if __name__ == "__main__":
    main()
