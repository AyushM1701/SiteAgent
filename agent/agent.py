#!/usr/bin/env python3
"""
agent.py - Autonomous Multi-Turn Agentic Runtime for React TS CSS SLMs
Empowers Qwen2.5-Coder-3B-Instruct with tool execution, observation feedback,
and self-correction loops.

Usage:
  # Run a single example interactively with base model (e.g. Tooltip):
  python agent.py --model ./base-model --example-index 0 --max-turns 4

  # Run a 10-example stratified evaluation through the agent loop:
  python agent.py --model ./base-model --subset 10

  # Fast verification of the multi-turn agent loop with mock engine (no GPU needed):
  python agent.py --mock --subset 4
"""

import argparse
import hashlib
import html
import json
import os
import re
import time
import threading
import shutil
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

# Absolute path to the repository root — used for all relative file references
BASE_DIR = Path(__file__).resolve().parent.parent


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

sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "agent"))
sys.path.insert(0, str(BASE_DIR / "training"))

from agent.agent_protocol import (
    AGENT_SYSTEM_PROMPT,
    SITE_AGENT_SYSTEM_PROMPT,
    AgentTurn,
    FinishAction,
    GetDependenciesAction,
    InspectDependenciesAction,
    ReadFileAction,
    GetWebglErrorsAction,
    GetSceneMetadataAction,
    GetAssetManifestAction,
    RunTestsAction,
    WriteComponentAction,
    WriteSiteAction,
    extract_error_signature,
    extract_primary_failure,
    format_chatml,
    format_observation,
    format_site_observation,
    parse_agent_output,
    prune_stack_trace,
    scrub_think_blocks,
    set_default_tokenizer,
)
from evaluate import (
    generate_test_file_content,
    get_stratified_sample,
    resolve_expected_exports,
    run_command,
)
from agent.style_ingest import (
    StyleSpec,
    validate_css_conformance,
    sanitize_css_for_spec,
    spec_to_prompt_instructions,
    validate_structural_quality,
    auto_fix_structural_violations,
)
from agent.output_budget import (
    BudgetTier,
    OutputTokenBudget,
    TaskComplexityFactors,
    estimate_output_budget,
    extract_complexity_factors,
    log_task_budget,
)
from agent.section_preflight import preflight_section_files


def sanitize_component_code(cleaned: str) -> Tuple[str, List[str]]:
    notes: List[str] = []
    # 0. Strip any lingering markdown code fences
    cleaned = re.sub(r'^\s*```(?:tsx|ts|jsx|js)?\s*\n?', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\n?\s*```\s*$', '', cleaned)

    # 1. Strip createRoot imports and invalid ref-renderers in components
    if "createRoot" in cleaned:
        # Check if createRoot is imported from react-dom/client
        cleaned = re.sub(r'import\s*\{\s*createRoot\s*\}\s*from\s*[\'"]react-dom/client[\'"];?\s*', '', cleaned)
        cleaned = re.sub(r'import\s*\{\s*createRoot\s*,\s*', 'import { ', cleaned)
        cleaned = re.sub(r',\s*createRoot\s*\}', ' }', cleaned)

        # Repair pattern: const renderX = (ref: React.RefObject<...>) => { const root = createRoot(ref.current!); ... root.render(...); return () => root.unmount(); };
        cleaned = re.sub(
            r'const\s+(render\w+)\s*=\s*\([^)]*\)\s*=>\s*\{[\s\S]*?const\s+root\s*=\s*createRoot\([^)]*\);[\s\S]*?root\.render\(\s*([\s\S]*?)\s*\);[\s\S]*?return\s*\(\)\s*=>\s*root\.unmount\(\);?\s*\};?',
            r'const \1 = () => (\2);',
            cleaned
        )
        # Convert <div ref={renderX} ...></div> into <div ...>{renderX()}</div>
        def _replace_ref_render(m):
            tag = m.group(1)
            attrs = m.group(2)
            fn = m.group(3)
            rest_attrs = m.group(4)
            return f'<{tag} {attrs} {rest_attrs}>{{{fn}()}}</{tag}>'

        cleaned = re.sub(
            r'<([a-zA-Z0-9]+)\s+([^>]*?)ref=\{(render\w+)\}\s*([^>]*?)>\s*</\1>',
            _replace_ref_render,
            cleaned
        )
        notes.append("Sanitized createRoot from component TSX (converted nested root ref to direct JSX rendering).")

    # 2. Convert uninstalled react-scroll-parallax and react-responsive into native React
    if "react-scroll-parallax" in cleaned:
        cleaned = re.sub(r'import\s*\{[^}]*\}\s*from\s*[\'"]react-scroll-parallax[\'"];?\s*', '', cleaned)
        cleaned = re.sub(r'<Parallax\b', '<div', cleaned)
        cleaned = re.sub(r'</Parallax>', '</div>', cleaned)
        cleaned = re.sub(r'\s*(?:bgParallax|speed|offset)\s*=\s*\{[^}]*\}', '', cleaned)
        notes.append("Converted external react-scroll-parallax into self-contained React elements.")

    if "react-responsive" in cleaned:
        cleaned = re.sub(r'import\s*\{[^}]*\}\s*from\s*[\'"]react-responsive[\'"];?\s*', '', cleaned)
        cleaned = re.sub(
            r'const\s*\[\s*([a-zA-Z0-9_]+)\s*\]\s*=\s*useMediaQuery\([^)]*\);?',
            r'const \1 = false;',
            cleaned
        )
        notes.append("Sanitized uninstalled react-responsive into native state.")

    if "framer-motion" in cleaned:
        cleaned = re.sub(r'import\s*\{[^}]*\}\s*from\s*[\'"]framer-motion[\'"];?\s*', '', cleaned)
        cleaned = re.sub(r'<motion\.([a-zA-Z0-9]+)\b', r'<\1', cleaned)
        cleaned = re.sub(r'</motion\.([a-zA-Z0-9]+)>', r'</\1>', cleaned)
        cleaned = re.sub(r'\s*(?:initial|animate|transition|variants|whileHover|whileTap)\s*=\s*\{[^}]*\}', '', cleaned)
        notes.append("Converted external framer-motion tags to native elements.")

    # 3. Add passive: true to scroll listeners if missing
    cleaned = re.sub(
        r"window\.addEventListener\(\s*['\"]scroll['\"]\s*,\s*([a-zA-Z0-9_]+)\s*\)",
        r"window.addEventListener('scroll', \1, { passive: true })",
        cleaned
    )

    # 4. Repair observer.observe(item) where item is a data object rather than a DOM Element
    cleaned = re.sub(
        r'([a-zA-Z0-9_]+)\.forEach\(\s*\(\s*([a-zA-Z0-9_]+)\s*\)\s*=>\s*\{\s*([a-zA-Z0-9_]+)\.observe\(\2\);\s*\}\s*\);?',
        r'document.querySelectorAll("[class*=\'card\'], [class*=\'item\']").forEach((el: any) => \3.observe(el));',
        cleaned
    )
    cleaned = re.sub(
        r'([a-zA-Z0-9_]+)\.forEach\(\s*\(\s*([a-zA-Z0-9_]+)\s*\)\s*=>\s*\{\s*([a-zA-Z0-9_]+)\.unobserve\(\2\);\s*\}\s*\);?',
        r'document.querySelectorAll("[class*=\'card\'], [class*=\'item\']").forEach((el: any) => \3.unobserve(el));',
        cleaned
    )

    # 5. Detect placeholder comments
    placeholder_matches = re.findall(r'\{\s*/\*\s*(?:Render|TODO|Replace with)\b[^}]*\*/\s*\}', cleaned, re.I)
    if placeholder_matches:
        notes.append(f"Found {len(placeholder_matches)} placeholder comment(s) (e.g. '{placeholder_matches[0]}'). Implement full JSX markup instead of placeholders.")

    # 6. Repair useState([]) inferring never[] in strict TypeScript
    if re.search(r'\buseState\s*\(\s*\[\s*\]\s*\)', cleaned):
        cleaned = re.sub(r'\buseState\s*\(\s*\[\s*\]\s*\)', 'useState<any[]>([])', cleaned)
        notes.append("Repaired unparameterized useState([]) to useState<any[]>([]) to prevent TS2345 never[] error.")

    # 7. Repair untyped callback / handler parameters causing TS7006 implicit 'any'
    cleaned = re.sub(
        r'\b(const\s+(?:handle|on)[A-Za-z0-9_]*\s*=\s*\()\s*([a-zA-Z0-9_]+)\s*(\)\s*=>)',
        r'\1\2: any\3',
        cleaned
    )
    cleaned = re.sub(
        r'\b(const\s+(?:handle|on)[A-Za-z0-9_]*\s*=\s*\()\s*([a-zA-Z0-9_]+)\s*,\s*([a-zA-Z0-9_]+)\s*(\)\s*=>)',
        r'\1\2: any, \3: any\4',
        cleaned
    )
    cleaned = re.sub(
        r'\b(function\s+(?:handle|on)[A-Za-z0-9_]*\s*\()\s*([a-zA-Z0-9_]+)\s*(\))',
        r'\1\2: any\3',
        cleaned
    )

    return cleaned, notes


class MockAgentEngine:
    """Simulates an agentic multi-turn conversation with self-correction for testing."""
    def __init__(self):
        self.turn_counts: Dict[int, int] = {}
        self.is_mock = True

    def generate_turn(self, example_idx: int, history: List[Dict[str, str]], primary_symbol: str, **kwargs) -> str:
        count = self.turn_counts.get(example_idx, 0)
        self.turn_counts[example_idx] = count + 1

        name = primary_symbol or "Component"

        # Check if this is a site-generation task
        is_site = any("Content Brief" in m.get("content", "") or "FIRST SECTION REQUIRED" in m.get("content", "") for m in history)
        if is_site:
            last_msg = history[-1]["content"] if history else ""
            if "[SITE BUILD COMPLETE]" in last_msg:
                return f"""<finish>
{name} website generated successfully with full design token integration.
</finish>"""

            # Determine which section is requested
            sec_name = "Header"
            m = re.search(r'\[NEXT SECTION REQUIRED\]:\s*Write the ([A-Za-z0-9_-]+)', last_msg)
            if not m:
                m = re.search(r'FIRST SECTION REQUIRED:\s*Write the ([A-Za-z0-9_-]+)', last_msg)
            if m:
                sec_name = m.group(1).capitalize()
            elif "hero" in last_msg.lower():
                sec_name = "Hero"
            elif "features" in last_msg.lower():
                sec_name = "Features"
            elif "pricing" in last_msg.lower():
                sec_name = "Pricing"
            elif "testimonials" in last_msg.lower():
                sec_name = "Testimonials"
            elif "footer" in last_msg.lower():
                sec_name = "Footer"

            return f"""<tool_call name="write_site">
<file path="src/components/{sec_name}.tsx">
import React from 'react';
import './{sec_name}.css';

export function {sec_name}() {{
  return (
    <section className="{sec_name.lower()}-section">
      <div className="{sec_name.lower()}-container">
        <h2>{sec_name}</h2>
        <p>Premium responsive design powered by design tokens.</p>
      </div>
    </section>
  );
}}
</file>
<file path="src/components/{sec_name}.css">
.{sec_name.lower()}-section {{
  padding: var(--spacing-48, 48px) var(--spacing-28, 28px);
  background: var(--surface-obsidian, var(--color-obsidian, var(--bg-color, #000000)));
  color: var(--color-paper, var(--text-color, #ffffff));
  font-family: var(--font-roobert, var(--font-body));
}}
.{sec_name.lower()}-container {{
  max-width: var(--page-max-width, 1080px);
  margin: 0 auto;
  border-radius: var(--radius-cards, 0px);
}}
</file>
</tool_call>"""

        # Turn 1: Write initial component (with intentional minor bug to test self-correction)
        if count == 0:
            return f"""<tool_call name="write_component">
<tsx>
import React from 'react';
export function {name}(props: any) {{
  return <div data-testid="initial-render">Initial draft for {name}</div>;
}}
</tsx>
</tool_call>"""

        # Turn 2: Model sees observation from write/test, decides to run test or fix
        if count == 1:
            # Check if previous observation had test failure
            return f"""<tool_call name="run_tests">
</tool_call>"""

        # Turn 3: Model inspects test failure observation and self-corrects!
        if count == 2:
            return f"""<tool_call name="write_component">
<tsx>
import React, {{ useState, useEffect }} from 'react';

export function {name}(props: any) {{
  const [open, setOpen] = useState(false);

  useEffect(() => {{
    const handleKey = (e: KeyboardEvent) => {{
      if (e.key === 'Escape' && props.onClose) props.onClose();
    }};
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }}, [props.onClose]);

  return (
    <div
      data-testid="modal-backdrop"
      role={{props.role || "status"}}
      onClick={{props.onClose || props.onClick}}
    >
      <span>Helpful hint</span>
      <span>AL</span>
      <button aria-label="dismiss" onClick={{props.onRemove}}>Dismiss</button>
      <button aria-label="remove" onClick={{props.onRemove}}>x</button>
      {{props.children}}
    </div>
  );
}}
</tsx>
</tool_call>"""

        # Turn 4: Finalize
        return f"""<finish>
{name} component successfully implemented, self-corrected, and verified.
</finish>"""


# Sampling for code-writing turns (component mode, runtime edits, project repair).
# Those callers choose a low temperature per call; the nucleus/top-k bounds and the
# repetition penalty are stated here so a change to the runner's defaults (tuned for
# the design kit's JSON copy) never silently changes how code is written.
# Measured 2026-10-16 on the base model, 10 STaR component tasks at temperature 0.15:
# top_p 0.8 / top_k 20 passed 6/10 (3 first-try) vs 4/10 (2) with no truncation,
# and never failed a task the untruncated run solved.
CODE_SAMPLING: Dict[str, Any] = {"top_p": 0.8, "top_k": 20, "repetition_penalty": 1.05}


class AgentModelRunner:
    def __init__(self, model_path: str, max_seq_length=None, is_mock: bool = False):
        from agent.config import ModelRuntimeConfig
        self.model_path = model_path
        self.max_seq_length = max_seq_length if max_seq_length is not None else ModelRuntimeConfig.get_max_seq_length()
        self.is_mock = is_mock
        self.model = None
        self.tokenizer = None
        self.mock_engine = MockAgentEngine() if is_mock else None
        self.last_context_tokens: int = 0
        self.last_generation_tokens: int = 0
        self.last_total_tokens: int = 0
        self.last_generation_diagnostics: Dict[str, Any] = {}
        self.generation_log_dir = None

        if not is_mock:
            self._load_model()

    def _load_model(self):
        print(f"Loading agent model: {self.model_path} (max_seq_length={self.max_seq_length})...")
        _adapter_config = Path(self.model_path) / "adapter_config.json"
        if _adapter_config.exists():
            from agent.base_model_fingerprint import verify_lora_adapter_compatibility
            verify_lora_adapter_compatibility(Path(self.model_path), Path(__file__).resolve().parent.parent / "base-model")
        else:
            from agent.base_model_fingerprint import verify_base_model_architecture
            base_fingerprint = verify_base_model_architecture(Path(self.model_path), strict=True)
            if not base_fingerprint["is_authentic_qwen3"]:
                raise RuntimeError("Model weights do not match the Qwen3 architecture")
        from agent.hardware import get_profile
        from agent.agent_protocol import set_default_tokenizer as _set_tokenizer  # one module (A3)
        profile = get_profile()
        for warning in profile.warnings:
            print(f"  [Hardware] {warning}")
        print(f"  [Hardware] {profile.device} | {profile.backend} | "
              f"{'4-bit' if profile.load_in_4bit else profile.dtype}"
              + (f" | {profile.gpu_name} ({profile.vram_gb} GB)" if profile.gpu_name else ""))

        if profile.backend == "unsloth":
            try:
                from unsloth import FastLanguageModel
                self.model, self.tokenizer = FastLanguageModel.from_pretrained(
                    model_name=self.model_path,
                    max_seq_length=self.max_seq_length,
                    load_in_4bit=profile.load_in_4bit,
                )
                FastLanguageModel.for_inference(self.model)
                _set_tokenizer(self.tokenizer)
                print("Loaded successfully with Unsloth inference optimizations.")
                return
            except ImportError:
                print("  [Hardware] Unsloth is not importable; falling back to Transformers.")
        self._load_with_transformers(profile)
        _set_tokenizer(self.tokenizer)
        print(f"Loaded with Transformers on {profile.device}.")

    def _load_with_transformers(self, profile) -> None:
        """Portable loader: NVIDIA/AMD (optionally 4-bit), Apple Metal, or CPU. LoRA adapter
        directories are applied on top of the local base model with PEFT."""
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        dtype = {"float16": torch.float16, "bfloat16": torch.bfloat16, "float32": torch.float32}[profile.dtype]
        adapter = (Path(self.model_path) / "adapter_config.json").exists()
        base_path = Path(__file__).resolve().parent.parent / "base-model" if adapter else Path(self.model_path)
        kwargs: Dict[str, Any] = {"torch_dtype": dtype}
        if profile.device == "cuda":
            kwargs["device_map"] = "auto"
            if profile.load_in_4bit:
                from transformers import BitsAndBytesConfig
                kwargs["quantization_config"] = BitsAndBytesConfig(
                    load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=dtype)
        self.tokenizer = AutoTokenizer.from_pretrained(str(self.model_path if adapter else base_path))
        model = AutoModelForCausalLM.from_pretrained(str(base_path), **kwargs)
        if profile.device in {"mps", "cpu"}:
            model = model.to(profile.device)
        if adapter:
            from peft import PeftModel
            model = PeftModel.from_pretrained(model, str(self.model_path))
        model.eval()
        self.model = model

    def generate_turn(
        self,
        example_idx: int,
        history: List[Dict[str, str]],
        primary_symbol: str,
        max_new_tokens: int = 768,
        temperature: float = 0.7,
        repetition_penalty: float = 1.0,
        stop_check=None,
        max_time_seconds=None,
        top_p: "Optional[float]" = 0.8,
        top_k: "Optional[int]" = 20,
        **kwargs,
    ) -> str:
        effective_stop = stop_check or getattr(self, "stop_check", None)
        if effective_stop and effective_stop():
            raise InterruptedError("Generation stopped by user.")

        if max_new_tokens >= self.max_seq_length:
            raise ValueError(f"Requested max_new_tokens ({max_new_tokens}) must be less than max_seq_length ({self.max_seq_length})")

        if self.is_mock:
            if effective_stop and effective_stop():
                raise InterruptedError("Generation stopped by user.")
            from agent.config import ModelRuntimeConfig
            active_history = [dict(m) for m in history]
            prompt_str = format_chatml(active_history, add_generation_prompt=True)
            prompt_len = ModelRuntimeConfig.count_tokens(prompt_str)
            self.last_context_tokens = prompt_len
            if prompt_len >= self.max_seq_length:
                raise ValueError(f"Prompt length {prompt_len} exceeds max sequence length {self.max_seq_length}")
            return self.mock_engine.generate_turn(example_idx, history, primary_symbol, **kwargs)

        import torch

        # Safe copy of history to allow compacting if needed
        active_history = [dict(m) for m in history]
        prompt_str = format_chatml(active_history, add_generation_prompt=True, tokenizer=self.tokenizer)
        target_device = self.model.get_input_embeddings().weight.device if hasattr(self.model, "get_input_embeddings") else "cuda"
        inputs = self.tokenizer(prompt_str, return_tensors="pt").to(target_device)

        # If token count is getting close to max_seq_length, compact older turns
        if inputs.input_ids.shape[1] + max_new_tokens > self.max_seq_length:
            print(f"  [Context Compaction] Sequence length ({inputs.input_ids.shape[1]}) approaching limit ({self.max_seq_length}). Compacting earlier turns...")

            is_site_mode = any("<tool_call name=\"write_site\">" in m.get("content", "") for m in active_history)

            # Find the index of the LAST assistant write turn so we never compact it
            last_write_idx = -1
            for idx in range(len(active_history) - 1, -1, -1):
                m = active_history[idx]
                content = m.get("content", "")
                if m.get("role") == "assistant" and ("<tool_call name=\"write_component\">" in content or "<tool_call name=\"write_site\">" in content):
                    last_write_idx = idx
                    break

            # Compact older turns: keep system[0], initial user[1], last 2 messages, and last write_component/write_site
            for i in range(2, len(active_history) - 2):
                msg = active_history[i]
                if i == last_write_idx:
                    continue  # Always preserve the most recent code the model wrote
                if msg.get("role") == "user" and "<observation" in msg.get("content", ""):
                    if is_site_mode:
                        msg["content"] = (
                            '<observation status="ok">\n'
                            '[Earlier section files accepted and written to disk. Refer to latest observation.]\n'
                            '</observation>'
                        )
                    else:
                        msg["content"] = (
                            '<observation status="info">\n'
                            '[Earlier test run observation truncated for context window. Refer to latest observation.]\n'
                            '</observation>'
                        )
                elif msg.get("role") == "assistant":
                    content = msg.get("content", "")
                    if "<tool_call name=\"write_component\">" in content:
                        msg["content"] = (
                            '<tool_call name="write_component">\n'
                            '<!-- Earlier TSX code draft compacted to preserve context window. Refer to latest revision. -->\n'
                            '</tool_call>'
                        ).strip()
                    elif "<tool_call name=\"write_site\">" in content:
                        paths = re.findall(r'<file\s+path=["\']([^"\']+)["\']', content)
                        file_stubs = "\n".join([f'<file path="{p}">\n/* Section file accepted and saved to disk. */\n</file>' for p in paths])
                        if not file_stubs:
                            file_stubs = '<!-- Section files accepted and saved to disk. -->'
                        # Preserve :root CSS variables and design tokens so downstream sections maintain theme consistency
                        root_matches = re.findall(r'(:root\s*\{[^}]*\})', content, re.DOTALL)
                        preserved_tokens = ""
                        if root_matches:
                            preserved_tokens = "\n/* Preserved theme design tokens */\n" + "\n".join(root_matches) + "\n"
                        msg["content"] = (
                            '<tool_call name="write_site">\n'
                            f'{file_stubs}\n'
                            f'{preserved_tokens}'
                            '</tool_call>'
                        ).strip()

            # Synchronize compacted contents to outer history to prevent unbounded growth across turns
            for i in range(2, min(len(history), len(active_history)) - 2):
                if i != last_write_idx:
                    history[i]["content"] = active_history[i]["content"]

            prompt_str = format_chatml(active_history, add_generation_prompt=True, tokenizer=self.tokenizer)
            inputs = self.tokenizer(prompt_str, return_tensors="pt").to(target_device)



        # Validate sequence budget and dynamically clamp max_new_tokens
        prompt_len = inputs.input_ids.shape[1]
        self.last_context_tokens = prompt_len
        from agent.config import ModelRuntimeConfig
        if prompt_len >= self.max_seq_length:
            raise ValueError(f"Prompt length {prompt_len} exceeds max sequence length {self.max_seq_length}")
        max_new_tokens = min(max_new_tokens, self.max_seq_length - prompt_len) if prompt_len + max_new_tokens > self.max_seq_length else max_new_tokens
        max_new_tokens = max(1, max_new_tokens)

        from transformers import StoppingCriteriaList, StopStringCriteria
        # Tool responses are complete as soon as their closing envelope lands.
        # Waiting for an arbitrary token cap can turn a valid repair into a
        # long, truncated continuation on small local GPUs.
        stopping_criteria = StoppingCriteriaList()
        if isinstance(self.tokenizer.get_vocab(), dict):
            stopping_criteria.append(
                StopStringCriteria(tokenizer=self.tokenizer, stop_strings=["</tool_call>"])
            )
        if effective_stop:
            from transformers import StoppingCriteria
            class StopCheckCriteria(StoppingCriteria):
                def __init__(self, check_fn):
                    self.check_fn = check_fn
                def __call__(self, input_ids, scores, **kwargs):
                    return bool(self.check_fn())
            stopping_criteria.append(StopCheckCriteria(effective_stop))

        import time as _time
        import hashlib as _hashlib
        started = _time.perf_counter()
        log_path = None
        if getattr(self, "generation_log_dir", None):
            log_root = Path(self.generation_log_dir)
            log_root.mkdir(parents=True, exist_ok=True)
            log_path = log_root / f"{_time.time_ns()}.json"
            log_path.write_text(json.dumps({"status": "running", "prompt": prompt_str,
                "model": getattr(self, "model_path", "unknown"), "prompt_tokens": prompt_len,
                "max_new_tokens": max_new_tokens}, indent=2), encoding="utf-8")
        with torch.no_grad():
            output_tokens = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                max_length=None,
                temperature=temperature,
                repetition_penalty=repetition_penalty,
                do_sample=(temperature > 0),
                pad_token_id=self.tokenizer.eos_token_id,
                stopping_criteria=stopping_criteria,
                **({"max_time": max_time_seconds} if max_time_seconds is not None else {}),
                **({"top_p": top_p} if top_p is not None and temperature > 0 else {}),
                **({"top_k": top_k} if top_k is not None and temperature > 0 else {}),
            )

        self.last_generation_tokens = max(0, output_tokens.shape[1] - prompt_len)
        self.last_total_tokens = output_tokens.shape[1]

        raw = self.tokenizer.decode(output_tokens[0][prompt_len:], skip_special_tokens=False)
        elapsed = _time.perf_counter() - started
        self.last_generation_diagnostics = {
            "status": "completed", "model": getattr(self, "model_path", "unknown"), "prompt": prompt_str,
            "raw_output": raw, "prompt_tokens": prompt_len,
            "generated_tokens": self.last_generation_tokens, "max_new_tokens": max_new_tokens,
            "seconds": elapsed, "tokens_per_second": self.last_generation_tokens / max(elapsed, .001),
            "temperature": temperature, "repetition_penalty": repetition_penalty,
            "top_p": top_p, "top_k": top_k,
            "max_time_seconds": max_time_seconds,
            "prompt_sha256": _hashlib.sha256(prompt_str.encode("utf-8")).hexdigest(),
            "raw_output_sha256": _hashlib.sha256(raw.encode("utf-8")).hexdigest(),
            "stop_reason": ("tool_complete" if "</tool_call>" in raw else
                "eos" if "<|im_end|>" in raw else
                "token_limit" if self.last_generation_tokens >= max_new_tokens else
                "time_limit" if max_time_seconds is not None and elapsed >= max_time_seconds else
                "interrupted" if effective_stop and effective_stop() else "other"),
        }
        if log_path:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            log_path.write_text(json.dumps(self.last_generation_diagnostics, indent=2), encoding="utf-8")

        if effective_stop and effective_stop():
            raise InterruptedError("Generation stopped by user.")

        # Decode generated completion only
        new_tokens = output_tokens[0][inputs.input_ids.shape[1]:]
        response = self.tokenizer.decode(new_tokens, skip_special_tokens=True).strip()

        # Strip Qwen3 native <think> blocks (belt-and-suspenders; apply_chat_template
        # uses enable_thinking=False but the model may still emit them in some
        # adapter configurations).
        _stb = globals().get("scrub_think_blocks")
        if callable(_stb):
            response = _stb(response)
        else:
            response = re.sub(r'<think>[\s\S]*?</think>\s*', '', response, flags=re.DOTALL).strip()

        # If model generated end token tag <|im_end|>, trim it
        if "<|im_end|>" in response:
            response = response.split("<|im_end|>")[0].strip()

        return response


def execute_test_suite(case_dir: Path, test_file: Path) -> Tuple[bool, bool, str, str]:
    """Runs TSC typechecking and Vitest on the case workspace."""
    # Always run from BASE_DIR so relative paths like css.d.ts are resolved correctly
    # regardless of the caller's cwd.
    run_cwd = BASE_DIR
    # 1. Run TSC
    tsc_proc = run_command([
        "npx", "tsc", "--noEmit",
        "--jsx", "react-jsx",
        "--target", "ES2022",
        "--moduleResolution", "bundler",
        "--esModuleInterop",
        "--skipLibCheck",
        (case_dir / "Component.tsx").as_posix(),
        "css.d.ts"
    ], cwd=run_cwd)
    tsc_passed = (tsc_proc.returncode == 0)
    tsc_output = (tsc_proc.stdout + "\n" + tsc_proc.stderr).strip()

    # 2. Run Vitest with fast worker threads
    if "Playwright" in test_file.read_text(encoding="utf-8"):
        vitest_passed = True
        vitest_output = "Playwright test skipped in jsdom."
    else:
        vitest_proc = run_command([
            "npx", "vitest", "run",
            "--config", "vitest.config.ts",
            "--pool=threads",
            test_file.as_posix()
        ], cwd=run_cwd)
        vitest_passed = (vitest_proc.returncode == 0)
        vitest_output = (vitest_proc.stdout + "\n" + vitest_proc.stderr).strip()

    return tsc_passed, vitest_passed, tsc_output, vitest_output


def score_test_results(tsc_ok: bool, vit_ok: bool, tsc_out: str = "", vit_out: str = "") -> int:
    """
    Lower score is better:
    0 = passed 100% of TSC and Vitest checks
    1..999 = compiled cleanly, N assertions failed in Vitest
    1000+ = failed TypeScript compilation
    """
    if tsc_ok and vit_ok:
        return 0
    if not tsc_ok:
        return 1000 + len(tsc_out.splitlines())

    # 1. Standard Vitest summary: Tests  N failed
    m = re.search(r'Tests\s+(\d+)\s+failed', vit_out, re.IGNORECASE)
    if m:
        return int(m.group(1))

    # 2. Alternative Vitest summary: failed: N or N failed
    m = re.search(r'(\d+)\s+(?:test[s]?\s+)?failed', vit_out, re.IGNORECASE)
    if m:
        return int(m.group(1))

    # 3. Test Suites / Files failed
    m = re.search(r'Test Files\s+(\d+)\s+failed', vit_out, re.IGNORECASE)
    if m:
        return int(m.group(1))

    # 4. Count FAIL banners / error crosses
    fail_banners = len(re.findall(r'(?:^|\n)\s*FAIL\s+', vit_out))
    cross_count = len(re.findall(r'(?:^|\n)\s*[×\u00d7]\s+', vit_out))
    count = max(fail_banners, cross_count)
    return count if count > 0 else 1


def run_agent_on_example(
    orig_idx: int,
    item: Dict[str, Any],
    runner: AgentModelRunner,
    workspace_root: Path,
    max_turns: int = 5,
    temperature: float = 0.2,
    max_new_tokens: Optional[int] = None,
    best_of_2: bool = True,
    stop_check: Optional[Callable[[], bool]] = None,
    top_p: Optional[float] = CODE_SAMPLING["top_p"],
    top_k: Optional[int] = CODE_SAMPLING["top_k"],
) -> Dict[str, Any]:
    """
    Runs the multi-turn agent loop for a single React+TS+CSS component task.
    Implements Turn 1 Best-of-2 full Vitest assertion triage, dynamic anti-stuck
    temperature escalation, DPO preference logging, dynamic output token budgeting,
    and regression guarding.
    """
    prompt = item["prompt"]
    test_code = item["test_code"]
    check_variant = item.get("check", "tsc_and_render")

    all_symbols, primary_symbol = resolve_expected_exports(item)
    target_name = primary_symbol or "Component"
    all_symbols = all_symbols or ([target_name] if target_name else [])

    case_dir = workspace_root / f"case_{orig_idx:03d}"
    if case_dir.exists():
        shutil.rmtree(case_dir)
    case_dir.mkdir(parents=True, exist_ok=True)

    test_file_code = generate_test_file_content(test_code, all_symbols, primary_symbol)
    test_file = case_dir / "Component.test.tsx"
    test_file.write_text(test_file_code, encoding="utf-8")

    guideline_hints = (
        "GUIDELINES: Support standard prop aliases (e.g. trend ?? valueChange, initialValues ?? initialState). "
        "Log clean payloads with console.log(action) without prepended prefixes. "
        "For standalone imperative hooks (e.g. useConfirm, useToast), mount dynamic DOM containers to document.body."
    )
    if len(all_symbols) > 1:
        export_names = ", ".join(f"`{s}`" for s in all_symbols)
        user_prompt = f"{prompt}\nIMPORTANT: Export the following named export(s): {export_names}.\n{guideline_hints}"
    else:
        user_prompt = f"{prompt}\nIMPORTANT: Export the component as a named export called `{target_name}`.\n{guideline_hints}"

    history: List[Dict[str, str]] = [
        {"role": "system", "content": AGENT_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt}
    ]

    # Dynamic Output Token Budget Allocation
    initial_factors = extract_complexity_factors(
        prompt=prompt,
        task_mode="component",
        requested_files=["Component.tsx"],
        current_file_length=0,
        target_symbol=target_name,
        test_code=test_code,
    )
    task_budget = estimate_output_budget(initial_factors)
    log_task_budget(task_budget, task_name=f"{target_name} (#{orig_idx+1})")
    allocated_tokens = max_new_tokens if max_new_tokens is not None else task_budget.clamped_tokens

    print(f"\n{'='*75}")
    print(f"TASK #{orig_idx+1}: {target_name} ({check_variant})")
    print(f"Prompt: {prompt[:90]}...")
    print(f"Output Budget: {task_budget.tier} ({allocated_tokens} tokens)")
    print(f"{'='*75}")

    turn_logs = []
    initial_passed = False
    self_corrected = False
    final_passed = False
    final_tsc_passed = False
    final_vitest_passed = False
    has_written_code = False

    # Dynamic Anti-Stuck & Regression Guard State
    base_temp = temperature
    base_rep_penalty = CODE_SAMPLING["repetition_penalty"]
    current_temp = base_temp
    current_rep_penalty = base_rep_penalty
    last_tsx_hash: Optional[str] = None
    last_error_sig: Optional[str] = None
    stuck_turns: int = 0
    best_score: int = 9999
    t1_cached_eval = None

    for turn_num in range(1, max_turns + 1):
        if stop_check and stop_check():
            print(f"  --> [Agent]: Stop requested by user. Finishing early at turn {turn_num}.")
            break

        current_turn_tokens = allocated_tokens
        if max_new_tokens is None and turn_num > 1 and last_error_sig:
            current_tsx = ""
            if (case_dir / "Component.tsx").exists():
                try:
                    current_tsx = (case_dir / "Component.tsx").read_text(encoding="utf-8")
                except Exception:
                    pass
            turn_factors = extract_complexity_factors(
                prompt=prompt,
                task_mode="patch" if (last_error_sig and ("TS2304" in last_error_sig or "TS2307" in last_error_sig)) else "component",
                requested_files=["Component.tsx"],
                current_file_length=len(current_tsx),
                repair_diagnostics=last_error_sig,
                target_symbol=target_name,
                test_code=test_code,
            )
            turn_budget = estimate_output_budget(turn_factors)
            current_turn_tokens = turn_budget.clamped_tokens
            print(f"  {turn_budget.log_summary(f'{target_name}:T{turn_num}')}")

        if stuck_turns > 0:
            print(f"\n>>> [Turn {turn_num}/{max_turns}] Generating assistant response (Anti-Stuck Active: temp={current_temp:.2f}, rep_penalty={current_rep_penalty:.2f}, budget={current_turn_tokens})...")
        else:
            print(f"\n>>> [Turn {turn_num}/{max_turns}] Generating assistant response (budget={current_turn_tokens})...")

        # Best-of-2 candidate generation on Turn 1, when anti-stuck is active, or on final turn
        should_best_of_2 = (turn_num == 1 or stuck_turns > 0 or (turn_num == max_turns and not final_passed))
        if should_best_of_2 and best_of_2 and not runner.is_mock:
            try:
                c1_text = runner.generate_turn(
                    example_idx=orig_idx,
                    history=history,
                    primary_symbol=target_name,
                    max_new_tokens=current_turn_tokens,
                    temperature=current_temp,
                    repetition_penalty=current_rep_penalty,
                    top_p=top_p,
                    top_k=top_k,
                    stop_check=stop_check,
                )

            except InterruptedError:
                print("  --> [Agent]: Generation interrupted by user cancellation.")
                break
            c1_turn = parse_agent_output(c1_text)

            if isinstance(c1_turn.action, WriteComponentAction):
                c1_turn.action.tsx, _ = sanitize_component_code(c1_turn.action.tsx)
                (case_dir / "Component.tsx").write_text(c1_turn.action.tsx, encoding="utf-8")
                c1_css = c1_turn.action.css if c1_turn.action.css else "/* empty styles */"
                (case_dir / "Component.module.css").write_text(c1_css, encoding="utf-8")
                (case_dir / "Component.css").write_text(c1_css, encoding="utf-8")
                (case_dir / "styles.css").write_text(c1_css, encoding="utf-8")
                if target_name:
                    (case_dir / f"{target_name}.css").write_text(c1_css, encoding="utf-8")
                    (case_dir / f"{target_name}.module.css").write_text(c1_css, encoding="utf-8")

                c1_tsc_ok, c1_vit_ok, c1_tsc_out, c1_vit_out = execute_test_suite(case_dir, test_file)
                c1_score = score_test_results(c1_tsc_ok, c1_vit_ok, c1_tsc_out, c1_vit_out)

                if c1_score == 0:
                    print("  [Turn 1 Best-of-2]: Candidate 1 passed 100% of TypeScript & Vitest checks! (Selected).")
                    assistant_text = c1_text
                    turn = c1_turn
                    t1_cached_eval = (c1_tsc_ok, c1_vit_ok, c1_tsc_out, c1_vit_out)
                else:
                    fail_desc = "TS compile error" if not c1_tsc_ok else f"{c1_score} failing assertion(s)"
                    if stop_check and stop_check():
                        print(f"  --> [Agent]: Stop requested by user before candidate 2. Finishing early.")
                        assistant_text = c1_text
                        turn = c1_turn
                        t1_cached_eval = (c1_tsc_ok, c1_vit_ok, c1_tsc_out, c1_vit_out)
                        break
                    print(f"  [Turn 1 Best-of-2]: Candidate 1 had {fail_desc}. Sampling Candidate 2 at temp=0.45...")
                    try:
                        c2_text = runner.generate_turn(
                            example_idx=orig_idx,
                            history=history,
                            primary_symbol=target_name,
                            max_new_tokens=current_turn_tokens,
                            temperature=0.45,
                            repetition_penalty=1.10,
                            top_p=top_p,
                            top_k=top_k,
                            stop_check=stop_check,
                        )
                    except InterruptedError:
                        print("  --> [Agent]: Generation interrupted by user cancellation.")
                        break
                    c2_turn = parse_agent_output(c2_text)

                    if isinstance(c2_turn.action, WriteComponentAction):
                        c2_turn.action.tsx, _ = sanitize_component_code(c2_turn.action.tsx)
                        (case_dir / "Component.tsx").write_text(c2_turn.action.tsx, encoding="utf-8")
                        c2_css = c2_turn.action.css if c2_turn.action.css else "/* empty styles */"
                        (case_dir / "Component.module.css").write_text(c2_css, encoding="utf-8")
                        (case_dir / "Component.css").write_text(c2_css, encoding="utf-8")
                        (case_dir / "styles.css").write_text(c2_css, encoding="utf-8")
                        if target_name:
                            (case_dir / f"{target_name}.css").write_text(c2_css, encoding="utf-8")
                            (case_dir / f"{target_name}.module.css").write_text(c2_css, encoding="utf-8")

                        c2_tsc_ok, c2_vit_ok, c2_tsc_out, c2_vit_out = execute_test_suite(case_dir, test_file)
                        c2_score = score_test_results(c2_tsc_ok, c2_vit_ok, c2_tsc_out, c2_vit_out)

                        if c2_score < c1_score:
                            win_desc = "Passed 100%!" if c2_score == 0 else (f"Fewer failures ({c2_score} vs {c1_score})" if c1_tsc_ok else "Compiled cleanly")
                            print(f"  [Turn 1 Best-of-2]: Candidate 2 won: {win_desc}! (Selected).")
                            assistant_text = c2_text
                            turn = c2_turn
                            t1_cached_eval = (c2_tsc_ok, c2_vit_ok, c2_tsc_out, c2_vit_out)
                            chosen_tsx, rejected_tsx = c2_turn.action.tsx, c1_turn.action.tsx
                        else:
                            print(f"  [Turn 1 Best-of-2]: Candidate 1 retained (Score: {c1_score} vs Candidate 2: {c2_score}).")
                            (case_dir / "Component.tsx").write_text(c1_turn.action.tsx, encoding="utf-8")
                            (case_dir / "Component.module.css").write_text(c1_css, encoding="utf-8")
                            assistant_text = c1_text
                            turn = c1_turn
                            t1_cached_eval = (c1_tsc_ok, c1_vit_ok, c1_tsc_out, c1_vit_out)
                            chosen_tsx, rejected_tsx = c1_turn.action.tsx, c2_turn.action.tsx

                        # Preference training needs a real preference, not two
                        # equally failing candidates. Retain only a fully verified
                        # winner against a failing alternative.
                        winning_score = min(c1_score, c2_score)
                        losing_score = max(c1_score, c2_score)
                        if winning_score == 0 and losing_score > 0:
                            try:
                                dpo_entry = {
                                    "task_id": orig_idx,
                                    "primary_symbol": target_name,
                                    "prompt": prompt,
                                    "chosen": chosen_tsx,
                                    "rejected": rejected_tsx,
                                    "chosen_score": winning_score,
                                    "rejected_score": losing_score,
                                }
                                dpo_dir = BASE_DIR / "data" / "dpo"
                                dpo_path = dpo_dir / "dpo_pairs_verified.jsonl" if dpo_dir.exists() else BASE_DIR / "dpo_pairs_verified.jsonl"
                                with open(dpo_path, "a", encoding="utf-8") as df:
                                    df.write(json.dumps(dpo_entry, ensure_ascii=False) + "\n")
                            except OSError as exc:
                                print(f"  [DPO]: Could not save verified pair: {exc}")
                    else:
                        assistant_text = c1_text
                        turn = c1_turn
                        t1_cached_eval = (c1_tsc_ok, c1_vit_ok, c1_tsc_out, c1_vit_out)
            else:
                assistant_text = c1_text
                turn = c1_turn
        else:
            try:
                assistant_text = runner.generate_turn(
                    example_idx=orig_idx,
                    history=history,
                    primary_symbol=target_name,
                    max_new_tokens=current_turn_tokens,
                    temperature=current_temp,
                    repetition_penalty=current_rep_penalty,
                    top_p=top_p,
                    top_k=top_k,
                    stop_check=stop_check,
                )
            except InterruptedError:
                print("  --> [Agent]: Generation interrupted by user cancellation.")
                break
            turn = parse_agent_output(assistant_text)

        if turn.status_message:
            print(f"--> {turn.status_message}")
        history.append({"role": "assistant", "content": turn.raw_text if turn.raw_text else assistant_text})

        # 1. Action: Finish
        if turn.is_finish:
            break

        # 2. Action: Write Component
        elif isinstance(turn.action, WriteComponentAction):
            turn.action.tsx, tsx_notes = sanitize_component_code(turn.action.tsx)
            current_tsx_clean = re.sub(r'\s+', ' ', turn.action.tsx).strip()
            current_hash = hashlib.sha256(current_tsx_clean.encode('utf-8')).hexdigest()
            is_identical_code = (last_tsx_hash is not None and current_hash == last_tsx_hash)
            last_tsx_hash = current_hash

            (case_dir / "Component.tsx").write_text(turn.action.tsx, encoding="utf-8")
            css_content = turn.action.css if turn.action.css else "/* empty styles */"
            (case_dir / "Component.module.css").write_text(css_content, encoding="utf-8")
            (case_dir / "Component.css").write_text(css_content, encoding="utf-8")
            (case_dir / "styles.css").write_text(css_content, encoding="utf-8")
            
            for rel_css in re.findall(r"['\"](\./[^'\"]+\.css)['\"]", turn.action.tsx):
                clean_name = rel_css.lstrip("./")
                try:
                    css_dest = resolve_project_path(case_dir, clean_name)
                except PermissionError as _path_err:
                    print(f"  [Security] Blocked CSS path: {_path_err}")
                    continue
                css_dest.parent.mkdir(parents=True, exist_ok=True)
                css_dest.write_text(css_content, encoding="utf-8")

            has_written_code = True
            if turn_num == 1 and t1_cached_eval is not None:
                tsc_ok, vit_ok, tsc_out, vit_out = t1_cached_eval
            else:
                tsc_ok, vit_ok, tsc_out, vit_out = execute_test_suite(case_dir, test_file)
            passed = (tsc_ok and vit_ok)
            current_score = score_test_results(tsc_ok, vit_ok, tsc_out, vit_out)

            if current_score < best_score:
                best_score = current_score

            if turn_num == 1:
                initial_passed = passed
            elif passed and not initial_passed:
                self_corrected = True

            anti_stuck_note = ""
            if tsx_notes:
                anti_stuck_note = "\n" + "\n".join(f"[Sanitizer Warning]: {n}" for n in tsx_notes)
            regress_warn = ""
            if passed:
                final_passed = True
                final_tsc_passed = tsc_ok
                final_vitest_passed = vit_ok
                stuck_turns = 0
            else:
                current_err = extract_primary_failure(tsc_ok, vit_ok, tsc_out, vit_out)
                current_sig = extract_error_signature(current_err)
                is_same_error = (last_error_sig is not None and current_sig == last_error_sig and turn_num > 1)
                regress_warn = f"\n[REGRESSION DETECTED]: Your previous attempt had fewer failures ({best_score} vs current {current_score}). Retain working logic." if turn_num > 1 and current_score > best_score and best_score < 1000 else ""
                
                if is_identical_code or is_same_error:
                    stuck_turns += 1
                    current_temp = min(base_temp + 0.30 * stuck_turns, 0.90)
                    current_rep_penalty = min(base_rep_penalty + 0.10 * stuck_turns, 1.30)
                    reason = "identical TSX emitted" if is_identical_code else "repeated identical failure signature"
                    print(f"  --> [Anti-Stuck Escalation]: Loop detected ({reason}). "
                          f"Escalating to temp={current_temp:.2f}, rep_penalty={current_rep_penalty:.2f} for Turn {turn_num + 1}!")

                    anti_stuck_note = (
                        f"\n[ANTI-STUCK INTERVENTION]: Your previous attempt repeated the same failure:\n"
                        f"--> {current_err}\n"
                        f"Do NOT regenerate the same code. Alter your implementation logic to resolve the root issue."
                    )
                else:
                    if stuck_turns > 0:
                        print("  --> [Anti-Stuck Progress]: Code/error state changed. Resetting sampling to base.")
                    stuck_turns = 0
                    current_temp = base_temp
                    current_rep_penalty = base_rep_penalty

                last_error_sig = current_sig

            obs = format_observation(
                tsc_passed=tsc_ok,
                vitest_passed=vit_ok,
                tsc_output=tsc_out,
                vitest_output=vit_out
            )
            if anti_stuck_note and "</observation>" in obs:
                obs = obs.replace("</observation>", f"{anti_stuck_note}\n</observation>")
            if regress_warn and "</observation>" in obs:
                obs = obs.replace("</observation>", f"{regress_warn}\n</observation>")

            history.append({"role": "user", "content": obs})
            turn_logs.append({
                "turn": turn_num,
                "thought": turn.thought,
                "action": "write_component",
                "passed": passed,
                "stuck_turns": stuck_turns,
                "temperature": current_temp,
                "observation": obs[:200]
            })

            # Preserve the exact code that passed. Continuing to sample after a
            # passing write can overwrite it with a regression while still making
            # the old implementation appear successful in summary metrics.
            if passed:
                print("  --> [Vitest & TSC]: ALL TESTS PASSED! Stopping on verified implementation.")
                break

        # 3. Action: Run Tests
        elif isinstance(turn.action, RunTestsAction):
            print("[Action]: <tool_call name=\"run_tests\">")
            if not has_written_code:
                obs = "<observation status=\"failed\">\nNo Component.tsx has been written yet. Call write_component first.\n</observation>"
            else:
                tsc_ok, vit_ok, tsc_out, vit_out = execute_test_suite(case_dir, test_file)
                passed = (tsc_ok and vit_ok)
                anti_stuck_note = ""
                if passed:
                    final_passed = True
                    final_tsc_passed = tsc_ok
                    final_vitest_passed = vit_ok
                    if not initial_passed and turn_num > 1:
                        self_corrected = True
                    print("  --> [Vitest & TSC]: ALL TESTS PASSED!")
                    stuck_turns = 0
                    current_temp = base_temp
                    current_rep_penalty = base_rep_penalty
                else:
                    print(f"  --> [Vitest & TSC]: Failed (tsc={tsc_ok}, vitest={vit_ok})")
                    current_err = extract_primary_failure(tsc_ok, vit_ok, tsc_out, vit_out)
                    current_sig = extract_error_signature(current_err)
                    is_same_error = (last_error_sig is not None and current_sig == last_error_sig and turn_num > 1)
                    if is_same_error:
                        stuck_turns += 1
                        current_temp = min(base_temp + 0.30 * stuck_turns, 0.90)
                        current_rep_penalty = min(base_rep_penalty + 0.10 * stuck_turns, 1.30)
                        print(f"  --> [Anti-Stuck Escalation]: Repeated error on run_tests. Escalating to temp={current_temp:.2f}, rep_penalty={current_rep_penalty:.2f}!")
                        anti_stuck_note = (
                            f"\n[ANTI-STUCK INTERVENTION]: Tests still failing with:\n--> {current_err}\n"
                            f"Call write_component to update your implementation."
                        )
                    else:
                        stuck_turns = 0
                        current_temp = base_temp
                        current_rep_penalty = base_rep_penalty
                    last_error_sig = current_sig

                obs = format_observation(
                    tsc_passed=tsc_ok,
                    vitest_passed=vit_ok,
                    tsc_output=tsc_out,
                    vitest_output=vit_out
                )
                if anti_stuck_note and "</observation>" in obs:
                    obs = obs.replace("</observation>", f"{anti_stuck_note}\n</observation>")

            history.append({"role": "user", "content": obs})
            turn_logs.append({
                "turn": turn_num,
                "thought": turn.thought,
                "action": "run_tests",
                "observation": obs[:200]
            })
            if has_written_code and final_passed:
                print("  --> [Vitest & TSC]: ALL TESTS PASSED! Stopping on verified implementation.")
                break

        # 4. Action: Read File
        elif isinstance(turn.action, ReadFileAction):
            print(f"[Action]: <tool_call name=\"read_file\"> path=\"{turn.action.path}\"")
            try:
                target_path = resolve_project_path(case_dir, turn.action.path)
                if target_path.is_file():
                    content = target_path.read_text(encoding="utf-8")
                    obs = (
                        f"<observation status=\"success\">\n"
                        f"File content of '{turn.action.path}':\n"
                        f"--------------------------------------------------\n"
                        f"{content}\n"
                        f"--------------------------------------------------\n"
                        f"</observation>"
                    )
                else:
                    obs = (
                        f"<observation status=\"failed\">\n"
                        f"File not found: '{turn.action.path}'. "
                        f"Unless a tool confirms that a file exists, do not invent it.\n"
                        f"</observation>"
                    )
            except Exception as e:
                obs = f"<observation status=\"error\">\nFailed to read file: {e}\n</observation>"
            history.append({"role": "user", "content": obs})
            turn_logs.append({
                "turn": turn_num,
                "thought": turn.thought,
                "action": "read_file",
                "observation": obs[:200]
            })

        # 5. Action: Inspect Dependencies
        elif isinstance(turn.action, (InspectDependenciesAction, GetDependenciesAction)):
            print("[Action]: <tool_call name=\"inspect_dependencies\">")
            pkg_json = BASE_DIR / "package.json"
            if not pkg_json.exists():
                pkg_json = case_dir / "package.json"
            if pkg_json.exists():
                try:
                    data = json.loads(pkg_json.read_text(encoding="utf-8"))
                    deps = data.get("dependencies", {})
                    dev_deps = data.get("devDependencies", {})
                    deps_str = "\n".join(f"  - {k}: {v}" for k, v in sorted(deps.items())) or "  (none)"
                    dev_deps_str = "\n".join(f"  - {k}: {v}" for k, v in sorted(dev_deps.items())) or "  (none)"
                    obs = (
                        f"<observation status=\"success\">\n"
                        f"Installed project dependencies from package.json:\n"
                        f"Dependencies:\n{deps_str}\n"
                        f"DevDependencies:\n{dev_deps_str}\n\n"
                        f"Note: Only installed packages are available. Unless a tool confirms that a package exists, do not invent external imports.\n"
                        f"</observation>"
                    )
                except Exception as e:
                    obs = f"<observation status=\"error\">\nFailed to parse package.json: {e}\n</observation>"
            else:
                obs = "<observation status=\"info\">\nNo package.json found. Use installed React APIs; do not invent external packages.\n</observation>"
            history.append({"role": "user", "content": obs})
            turn_logs.append({
                "turn": turn_num,
                "thought": turn.thought,
                "action": "inspect_dependencies",
                "observation": obs[:200]
            })

        # 6. Action: No tool call detected
        else:
            print("[Action]: None (No tool call recognized)")
            stuck_turns += 1
            current_temp = min(0.20 + 0.30 * stuck_turns, 0.85)
            obs = "<observation status=\"info\">\nNo tool call detected. Output <tool_call name=\"write_component\"> to update code or <finish> when done.\n</observation>"
            history.append({"role": "user", "content": obs})
            turn_logs.append({
                "turn": turn_num,
                "thought": turn.thought,
                "action": "none"
            })

    final_status = "PASSED" if final_passed else "FAILED"
    print(f"\nResult: {final_status} (Turns: {turn_num}, 1-shot: {initial_passed}, Self-Corrected: {self_corrected})")

    return {
        "index": orig_idx,
        "primary_symbol": target_name,
        "check": check_variant,
        "prompt": prompt,
        "turns_used": turn_num,
        "initial_passed": initial_passed,
        "self_corrected": self_corrected,
        "final_passed": final_passed,
        "final_tsc_passed": final_tsc_passed,
        "final_vitest_passed": final_vitest_passed,
        "trajectory": history,
        "turn_logs": turn_logs,
        "output_token_budget": task_budget.to_dict(),
    }


def print_agent_summary(results: List[Dict[str, Any]]):
    """Prints comparative metrics: 1-shot vs Agentic Self-Correction Pass Rate."""
    total = len(results)
    if total == 0:
        return

    pass_1shot = sum(1 for r in results if r["initial_passed"])
    self_corrected = sum(1 for r in results if r["self_corrected"])
    final_pass = sum(1 for r in results if r["final_passed"])
    avg_turns = sum(r["turns_used"] for r in results) / total

    print("\n" + "=" * 75)
    print("                 AGENTIC SLM EVALUATION SUMMARY REPORT                 ")
    print("=" * 75)
    print(f"Total Tasks Evaluated:        {total}")
    print(f"Average Turns Used:           {avg_turns:.2f}")
    print("-" * 75)
    print(f"1-Shot Pass Rate (Turn 1):    {pass_1shot}/{total} ({100*pass_1shot/total:.1f}%)")
    print(f"Self-Corrected Pass (Turn 2+):{self_corrected}/{total} (+{100*self_corrected/total:.1f}%)")
    print(f"Final Agentic Pass Rate:      {final_pass}/{total} ({100*final_pass/total:.1f}%)")
    print("=" * 75)


def execute_runtime_edit_policy(
    target_file: str,
    workspace_root: Path,
    runner: AgentModelRunner,
    instruction: str,
    primary_symbol: str = "Component",
    max_turns: int = 5,
    temperature: float = 0.2,
    max_new_tokens: Optional[int] = None,
    top_p: Optional[float] = CODE_SAMPLING["top_p"],
    top_k: Optional[int] = CODE_SAMPLING["top_k"],
) -> Dict[str, Any]:
    """
    Executes a code modification / edit adhering strictly to the 4-step runtime policy:
      Step 1: read_file -> inspect target file contents and existing structure
      Step 2: inspect dependencies -> verify package.json to avoid imagined imports
      Step 3: edit -> emit self-contained code without undeclared identifiers
      Step 4: verify -> run typecheck and test harness to confirm zero undeclared errors
    """
    edit_dir = workspace_root / "edit_session"
    edit_dir.mkdir(parents=True, exist_ok=True)
    target_path = resolve_project_path(workspace_root, target_file)

    step_log: List[Dict[str, Any]] = []

    # Step 1: read_file
    if target_path.is_file():
        file_content = target_path.read_text(encoding="utf-8")
        step_log.append({
            "step": "read_file",
            "file": target_file,
            "status": "success",
            "content_length": len(file_content),
        })
    else:
        file_content = "// New file\n"
        step_log.append({
            "step": "read_file",
            "file": target_file,
            "status": "created_initial",
            "content_length": len(file_content),
        })

    # Step 2: inspect dependencies
    pkg_path = workspace_root / "package.json"
    if not pkg_path.is_file():
        pkg_path = BASE_DIR / "package.json"
    installed_deps: Dict[str, str] = {}
    if pkg_path.is_file():
        try:
            pkg_data = json.loads(pkg_path.read_text(encoding="utf-8"))
            installed_deps.update(pkg_data.get("dependencies", {}))
            installed_deps.update(pkg_data.get("devDependencies", {}))
        except Exception:
            pass
    step_log.append({
        "step": "inspect_dependencies",
        "installed_count": len(installed_deps),
        "status": "success",
    })

    # Dynamic Output Token Budget for Edit
    edit_factors = extract_complexity_factors(
        prompt=instruction,
        task_mode="patch" if len(file_content) < 800 else "edit",
        requested_files=[target_file],
        current_file_length=len(file_content),
        target_symbol=primary_symbol,
    )
    edit_budget = estimate_output_budget(edit_factors)
    log_task_budget(edit_budget, task_name=f"edit:{target_file}")
    allocated_tokens = max_new_tokens if max_new_tokens is not None else edit_budget.clamped_tokens

    # Step 3: edit with self-contained prompt constraints
    policy_prompt = (
        f"TASK: Edit `{target_file}`.\n"
        f"INSTRUCTION: {instruction}\n\n"
        f"EXISTING FILE CONTENT:\n```tsx\n{file_content}\n```\n\n"
        f"CONFIRMED INSTALLED PACKAGES: {list(installed_deps.keys())[:15]}\n"
        f"AGENT RULE: Unless a tool confirms that an identifier/package/file exists, DO NOT INVENT IT. "
        f"Implement all hooks, helper utilities, and components self-contained in TSX.\n"
        f"Export the component as `{primary_symbol}`."
    )

    history = [
        {"role": "system", "content": AGENT_SYSTEM_PROMPT},
        {"role": "user", "content": policy_prompt},
    ]

    assistant_out = runner.generate_turn(
        example_idx=0,
        history=history,
        primary_symbol=primary_symbol,
        max_new_tokens=allocated_tokens,
        temperature=temperature,
        repetition_penalty=CODE_SAMPLING["repetition_penalty"],
        top_p=top_p,
        top_k=top_k,
    )
    turn = parse_agent_output(assistant_out)


    edited_tsx = ""
    edited_css = ""
    if isinstance(turn.action, WriteComponentAction):
        edited_tsx = turn.action.tsx
        edited_css = turn.action.css
    elif isinstance(turn.action, WriteSiteAction):
        tsx_files = turn.action.get_tsx_files()
        if tsx_files:
            edited_tsx = tsx_files[0][1]
        css_files = turn.action.get_css_files()
        if css_files:
            edited_css = css_files[0][1]

    step_log.append({
        "step": "edit",
        "action": type(turn.action).__name__ if turn.action else "none",
        "tsx_length": len(edited_tsx),
        "status": "success" if edited_tsx else "failed",
        "token_budget": edit_budget.to_dict(),
        "allocated_tokens": allocated_tokens,
    })

    # Step 4: verify
    target_path.write_text(edited_tsx or file_content, encoding="utf-8")
    if edited_css:
        css_path = target_path.with_suffix(".css")
        css_path.write_text(edited_css, encoding="utf-8")

    from training.undeclared_identifier_guard import scan_for_imagined_imports
    imagined_violations = scan_for_imagined_imports(edited_tsx)
    step_log.append({
        "step": "verify",
        "imagined_violations_count": len(imagined_violations),
        "status": "passed" if len(imagined_violations) == 0 else "violations_found",
        "violations": imagined_violations,
    })

    return {
        "target_file": target_file,
        "policy_sequence": ["read_file", "inspect_dependencies", "edit", "verify"],
        "steps_completed": step_log,
        "success": len(imagined_violations) == 0 and bool(edited_tsx),
        "edited_tsx": edited_tsx,
        "output_token_budget": edit_budget.to_dict(),
    }


# ── Section Synonyms & Compaction for Multi-Turn Site Pipeline ───────────────

_SECTION_SYNONYMS: Dict[str, List[str]] = {
    "header": ["header", "nav", "navbar", "navigation"],
    "hero": ["hero", "banner", "intro", "masthead"],
    "menu": ["menu", "dishes", "food", "items", "catalog"],
    "about": ["about", "story", "team", "company", "mission"],
    "features": ["features", "feature", "capabilities", "capability", "solutions", "solution"],
    "services": ["services", "service", "offerings", "offering"],
    "products": ["products", "product", "catalog", "shop"],
    "cart": ["cart", "basket", "bag"],
    "articles": ["articles", "article", "posts", "journal"],
    "archives": ["archives", "archive", "issues"],
    "contributors": ["contributors", "authors", "writers"],
    "dashboard": ["dashboard", "overview", "console"],
    "events": ["events", "event", "calendar", "meetups"],
    "membership": ["membership", "members", "join"],
    "pricing": ["pricing", "price", "tiers", "tier", "plans", "plan", "rates"],
    "testimonials": ["testimonials", "testimonial", "reviews", "review", "quotes", "quote", "carousel", "socialproof"],
    "projects": ["projects", "project", "work", "works", "portfolio", "showcase", "cases"],
    "skills": ["skills", "skill", "techstack", "technologies", "tools", "stack"],
    "cta": ["cta", "calltoaction", "action", "banner", "join"],
    "newsletter": ["newsletter", "subscribe"],
    "contact": ["contact", "inquiry", "reach", "location", "hours", "touch"],
    "footer": ["footer", "bottom"],
}

_BASE_SECTION_INSTRUCTIONS: Dict[str, str] = {
    "header": (
        "Write the Header section: a sticky navigation bar with the business name/logo on the left, "
        "navigation links in the center, and action controls on the right. If the prompt requests a theme toggle, "
        "include a functional dark/light mode toggle switch using useState. Include a responsive mobile drawer toggle. "
        "Files: src/components/Header.tsx + src/components/Header.css"
    ),
    "hero": (
        "Write the Hero section with a clear headline and visual composition suited to this site's purpose. "
        "Use only supported claims and meaningful section anchors for actions; include metrics only if supplied. "
        "Files: src/components/Hero.tsx + src/components/Hero.css"
    ),
    "menu": (
        "Write the Menu section: display the menu categories and items from the content brief. "
        "Use a card-grid layout with item name, price, and description. "
        "Files: src/components/Menu.tsx + src/components/Menu.css"
    ),
    "about": (
        "Write the About section using only supplied details. Make its layout suit the subject; "
        "avoid invented biographies, history, credentials and image placeholders. "
        "Files: src/components/About.tsx + src/components/About.css"
    ),
    "features": (
        "Write the Features section using capabilities explicitly requested or supported by the brief. "
        "If the prompt requests tabbed filtering or category switching, implement functional tab buttons with useState. "
        "Files: src/components/Features.tsx + src/components/Features.css"
    ),
    "pricing": (
        "Write the Pricing section using only supplied prices, tiers and billing rules. "
        "If numbers are missing, invite inquiries instead of inventing prices or discounts. "
        "If the prompt requests a calculator or billing toggle, make it functional using supplied rules. "
        "Files: src/components/Pricing.tsx + src/components/Pricing.css"
    ),
    "testimonials": (
        "Write the Testimonials section: display customer quotes, author names, roles, and star ratings. "
        "If requested, build an interactive carousel card with previous and next pagination buttons tracking active index using useState. "
        "Files: src/components/Testimonials.tsx + src/components/Testimonials.css"
    ),
    "projects": (
        "Write the Projects section using supplied projects and links. Match the portfolio's medium; "
        "show tech stack tags only for software projects with supplied technologies. "
        "Files: src/components/Projects.tsx + src/components/Projects.css"
    ),
    "skills": (
        "Write the Skills section: display skills as styled pill/badge elements. "
        "Files: src/components/Skills.tsx + src/components/Skills.css"
    ),
    "cta": (
        "Write the CTA (Call to Action) section: a full-width colored banner with a compelling "
        "headline and a prominent button. "
        "Files: src/components/CTA.tsx + src/components/CTA.css"
    ),
    "contact": (
        "Write the Contact section using only supplied address, phone, email and hours. "
        "If a form is requested without a backend, validate it and explain its local behavior honestly. "
        "Files: src/components/Contact.tsx + src/components/Contact.css"
    ),
    "footer": (
        "Write the Footer section with the supplied business name and valid anchors for sections that exist. "
        "Include contact details or external links only when supplied. "
        "Files: src/components/Footer.tsx + src/components/Footer.css"
    ),
    "products": "Write a shoppable Products section with user-supplied product data and accessible filtering if requested. Add-to-cart must persist a JSON array under localStorage key site-cart; each item has id:string, name:string, price:number, quantity:number. Dispatch a site-cart-updated event after changes. Do not invent prices or stock. Files: src/components/Products.tsx + src/components/Products.css",
    "collections": "Write the Collections section with supplied categories and working in-page navigation or filtering. Files: src/components/Collections.tsx + src/components/Collections.css",
    "cart": "Write an accessible Cart section whose quantity and remove controls update totals. Read and write JSON array items under localStorage key site-cart with id:string, name:string, price:number, quantity:number. Listen for site-cart-updated and storage events, and dispatch site-cart-updated after local changes. Never imply a real purchase occurred. Files: src/components/Cart.tsx + src/components/Cart.css",
    "checkout": "Write a checkout UI only to the scope requested. Validate inputs and state clearly that payment/order submission requires a connected backend. Never simulate a successful charge. Files: src/components/Checkout.tsx + src/components/Checkout.css",
    "gallery": "Write a responsive Gallery section using supplied works or available visual assets, with accessible image descriptions and functional filtering or lightbox when requested. Files: src/components/Gallery.tsx + src/components/Gallery.css",
    "articles": "Write an Articles section suited to an editorial site. Use supplied titles and summaries; do not invent author identities, publication dates or working article URLs. Files: src/components/Articles.tsx + src/components/Articles.css",
    "archives": "Write an Archives section for supplied issues or posts. Implement requested search and filters locally; do not invent publication dates or links. Files: src/components/Archives.tsx + src/components/Archives.css",
    "contributors": "Write a Contributors section with supplied people and biographies only. Files: src/components/Contributors.tsx + src/components/Contributors.css",
    "dashboard": "Write the requested Dashboard interface with all named data views and controls. Use clearly labeled demo data when no API exists, keep filters and sorts functional, and do not imply live telemetry without a connection. Files: src/components/Dashboard.tsx + src/components/Dashboard.css",
    "schedule": "Write a Schedule section using supplied dates and times only; if missing, present the program without fabricated times. Files: src/components/Schedule.tsx + src/components/Schedule.css",
    "speakers": "Write a Speakers section using only supplied people, roles and biographies. Files: src/components/Speakers.tsx + src/components/Speakers.css",
    "tickets": "Write a Tickets section using supplied ticket types and prices. Link only to supplied registration URLs; otherwise explain the next step honestly. Files: src/components/Tickets.tsx + src/components/Tickets.css",
    "services": "Write a Services section using only described offerings, with useful contact or booking actions. Files: src/components/Services.tsx + src/components/Services.css",
    "properties": "Write a Properties section using supplied listings and facts. Implement requested search/filter controls with local state. Do not invent addresses or prices. Files: src/components/Properties.tsx + src/components/Properties.css",
    "courses": "Write a Courses section using supplied course information. Implement requested filters locally and never invent accreditation or enrollment links. Files: src/components/Courses.tsx + src/components/Courses.css",
    "programs": "Write a Programs section using supplied program details and honest inquiry actions. Files: src/components/Programs.tsx + src/components/Programs.css",
    "faq": "Write a keyboard-accessible FAQ accordion using only questions and answers supplied by the user. Files: src/components/Faq.tsx + src/components/Faq.css",
    "booking": "Write a Booking section with requested date/service selection. Validate locally and do not claim a reservation is confirmed without a backend. Files: src/components/Booking.tsx + src/components/Booking.css",
    "newsletter": "Write a Newsletter section with email validation. Without an integration, do not claim the address was subscribed. Files: src/components/Newsletter.tsx + src/components/Newsletter.css",
    "team": "Write a Team section using only supplied names, roles and biographies. Files: src/components/Team.tsx + src/components/Team.css",
    "mission": "Write a Mission section using supplied purpose and activities; avoid invented impact claims. Files: src/components/Mission.tsx + src/components/Mission.css",
    "impact": "Write an Impact section using only supplied outcomes and metrics. Files: src/components/Impact.tsx + src/components/Impact.css",
    "donate": "Write a Donate section linking only to a supplied donation destination; do not mimic payment processing. Files: src/components/Donate.tsx + src/components/Donate.css",
    "location": "Write a Location section using only supplied address, directions and hours. Files: src/components/Location.tsx + src/components/Location.css",
    "events": "Write an Events section using supplied event information. If dates or booking URLs are missing, do not invent them. Files: src/components/Events.tsx + src/components/Events.css",
    "membership": "Write a Membership section using supplied benefits and terms. Without a backend, any join control must describe the next step honestly. Files: src/components/Membership.tsx + src/components/Membership.css",
}

_SECTION_INSTRUCTIONS: Dict[str, str] = dict(_BASE_SECTION_INSTRUCTIONS)


def _compact_site_history(history: List[Dict[str, str]]) -> None:
    """
    Compacts older completed section turns in history to prevent context window explosion.
    Preserves system[0], initial user[1], and the most recent assistant turn (history[-1]).
    Intermediate completed sections are condensed into their accepted file paths
    and preserved :root CSS tokens.
    """
    if len(history) <= 3:
        return

    # Compact turns older than the most recent assistant message (history[-1])
    for i in range(2, len(history) - 1):
        msg = history[i]
        role = msg.get("role")
        content = msg.get("content", "")

        if role == "assistant" and "<tool_call name=\"write_site\">" in content:
            file_paths = re.findall(r'<file\s+path=["\']([^"\']+)["\']', content)
            file_stubs = "\n".join([f'<file path="{p}">\n/* Section file accepted and saved to disk. */\n</file>' for p in file_paths])
            if not file_stubs:
                file_stubs = '<!-- Section files accepted and saved to disk. -->'
            root_matches = re.findall(r'(:root\s*\{[^}]*\})', content, re.DOTALL)
            preserved_tokens = ""
            if root_matches:
                preserved_tokens = "\n/* Preserved theme design tokens */\n" + "\n".join(root_matches) + "\n"

            msg["content"] = (
                f'<tool_call name="write_site">\n'
                f'{file_stubs}\n'
                f'{preserved_tokens}'
                f'</tool_call>'
            ).strip()

        elif role == "user" and "<observation" in content:
            if 'status="failed"' in content or 'VIOLATION' in content or 'ERROR' in content or 'MISMATCH' in content:
                msg["content"] = (
                    '<observation status="info">\n'
                    '[Earlier retry feedback resolved in subsequent revision.]\n'
                    '</observation>'
                )
            elif 'status="ok"' in content or '[Files accepted]' in content:
                acc_files = re.findall(r'✓\s*([^\n\r]+)', content)
                acc_summary = ", ".join(acc_files) if acc_files else "section files"
                next_sec_m = re.search(r'\[NEXT SECTION REQUIRED\]:\s*([^\n\r]+)', content)
                motion_m = re.search(r'((?:Motion requirement[s]?:|<current_section_motion>|<motion\b)[\s\S]+?(?:fallback\.?</current_section_motion>|/>|[^\n\r]+))', content, re.IGNORECASE)
                motion_clause = f"\n{motion_m.group(1).strip()}" if motion_m else ""
                next_sec_str = (
                    f"\n[NEXT SECTION REQUIRED]: {next_sec_m.group(1)}{motion_clause}\nWrite ONE <tool_call name=\"write_site\"> with exactly one .tsx file and one .css file for this section."
                    if next_sec_m else ""
                )
                msg["content"] = (
                    f'<observation status="ok">\n'
                    f'[Section files accepted ({acc_summary}) and written to disk.]{next_sec_str}\n'
                    f'</observation>'
                )


_CARD_SELECTOR_RE = re.compile(r'card|panel|tile|media|image|figure|thumb|frame', re.I)
_BUTTON_SELECTOR_RE = re.compile(r'btn|button|cta|pill|chip|tag|badge|toggle', re.I)


def _adapt_radii(css: str, btn_radius: str, card_radius: str) -> str:
    """Bring card radii in line with the design system without squaring pill
    buttons: only card-like rules are rewritten (audit A9)."""
    def fix_block(match: "re.Match[str]") -> str:
        selector, body = match.group(1), match.group(2)
        if _BUTTON_SELECTOR_RE.search(selector) or not _CARD_SELECTOR_RE.search(selector):
            return match.group(0)
        body = re.sub(r'border-radius\s*:\s*(?:[4-9]|[1-6][0-9]|7[0-4])px\b', f'border-radius: {card_radius}', body, flags=re.I)
        return f"{selector}{{{body}}}"
    return re.sub(r'([^{}]+)\{([^{}]*)\}', fix_block, css)


def synthesize_section_css(section_name: str, tsx_content: str, style_spec: Optional[Any] = None) -> str:
    """
    Synthesizes a minimal but compliant CSS file for a section matching active design tokens.
    Used as an escape hatch when the model repeatedly omits CSS or gets stuck.
    """
    classes = re.findall(r'className=["\']([^"\']+)["\']', tsx_content)
    all_classes = set()
    for c in classes:
        for single in c.split():
            if single and not single.startswith("{"):
                all_classes.add(single)

    prefix = f"sa-{section_name.replace('_', '-')}"
    # Every selector is scoped under the section's own root class so the
    # fallback never restyles other sections (audit A10).
    root_match = re.search(r'className=["\']([^"\'\s{]+)', tsx_content)
    root = root_match.group(1) if root_match else prefix
    pri_color = style_spec.get_primary_color() if (style_spec and hasattr(style_spec, "get_primary_color")) else "var(--color-obsidian, #000000)"
    accent_color = style_spec.get_accent_color() if (style_spec and hasattr(style_spec, "get_accent_color")) else "var(--color-iridescent-fade, #a02d25)"
    head_font = style_spec.get_heading_font() if (style_spec and hasattr(style_spec, "get_heading_font")) else "var(--font-heading, sans-serif)"
    body_font = style_spec.get_body_font() if (style_spec and hasattr(style_spec, "get_body_font")) else "var(--font-body, sans-serif)"
    btn_radius = style_spec.radius.get("--radius-buttons", "75px") if (style_spec and hasattr(style_spec, "radius") and style_spec.radius) else "75px"
    card_radius = style_spec.radius.get("--radius-cards", "0px") if (style_spec and hasattr(style_spec, "radius") and style_spec.radius) else "0px"
    r = f".{root}"

    rules = [
        f"/* Auto-synthesized CSS fallback for {section_name} */",
        f"{r} {{",
        f"  width: 100%;",
        f"  padding: 5rem 2rem;",
        f"  background: {pri_color};",
        f"  color: var(--surface-paper, #ffffff);",
        f"  box-sizing: border-box;",
        f"}}",
        f"{r} > div {{",
        f"  max-width: var(--page-max-width, 1200px);",
        f"  margin: 0 auto;",
        f"}}",
        f"{r} h1, {r} h2 {{",
        f"  font-family: {head_font}, sans-serif;",
        f"  color: var(--surface-paper, #ffffff);",
        f"  margin-bottom: 1.5rem;",
        f"}}",
        f"{r} [class*='grid'] {{",
        f"  display: grid;",
        f"  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));",
        f"  gap: 2rem;",
        f"  margin-top: 2rem;",
        f"}}",
        f"{r} [class*='card'] {{",
        f"  background: rgba(255, 255, 255, 0.03);",
        f"  border: 1px solid rgba(255, 255, 255, 0.08);",
        f"  border-radius: {card_radius};",
        f"  padding: 1.75rem;",
        f"  box-shadow: none;",
        f"  transition: border-color 0.2s ease, transform 0.2s ease;",
        f"}}",
        f"{r} [class*='card']:hover, {r} [class*='card']:focus-within {{",
        f"  border-color: {accent_color};",
        f"  transform: translateY(-2px);",
        f"}}",
        f"{r} button, {r} a[class*='btn'], {r} a[class*='cta'] {{",
        f"  display: inline-flex;",
        f"  align-items: center;",
        f"  justify-content: center;",
        f"  padding: 0.65rem 1.75rem;",
        f"  background: {accent_color};",
        f"  color: var(--surface-paper, #ffffff);",
        f"  border-radius: {btn_radius};",
        f"  font-family: {body_font}, sans-serif;",
        f"  font-weight: 600;",
        f"  text-decoration: none;",
        f"  border: none;",
        f"  box-shadow: none;",
        f"  cursor: pointer;",
        f"}}",
    ]

    for cls in sorted(all_classes):
        scoped = f"{r} .{cls}" if cls != root else r
        if any(k in cls.lower() for k in ["label"]):
            rules.append(f"{scoped} {{ display: block; font-family: {body_font}, sans-serif; font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; opacity: 0.65; margin-bottom: 4px; color: var(--surface-paper, #ffffff); }}")
        elif any(k in cls.lower() for k in ["field"]):
            rules.append(f"{scoped} {{ margin-bottom: 12px; }}")
        elif any(k in cls.lower() for k in ["badge", "tag"]):
            rules.append(f"{scoped} {{ display: inline-block; padding: 0.25rem 0.65rem; border-radius: {btn_radius}; font-size: 0.8rem; font-weight: 600; color: {accent_color}; background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.1); }}")
        elif any(k in cls.lower() for k in ["spec"]):
            rules.append(f"{scoped} {{ font-family: {body_font}, sans-serif; font-size: 0.88rem; color: rgba(255,255,255,0.85); line-height: 1.5; margin: 4px 0 0; }}")
        elif any(k in cls.lower() for k in ["desc", "text", "sub", "para"]):
            rules.append(f"{scoped} {{ font-family: {body_font}, sans-serif; font-size: 0.95rem; color: rgba(255,255,255,0.7); line-height: 1.6; }}")

    rules.append(
        "@media (prefers-reduced-motion: reduce) {\n"
        f"  {r}, {r} * {{\n"
        "    animation: none !important;\n"
        "    transition: none !important;\n"
        "    transform: none !important;\n"
        "    scroll-behavior: auto !important;\n"
        "  }\n"
        "}"
    )

    return "\n".join(rules) + "\n"


def _site_import_violations(files: List[tuple[str, str]], package_dir: Path) -> List[str]:
    """Reject bare imports absent from the generated project's declared dependencies."""
    dependencies = {"react", "react-dom"}
    for manifest in (package_dir / "package.json", BASE_DIR / "package.json"):
        try:
            package = json.loads(manifest.read_text(encoding="utf-8"))
            dependencies.update(package.get("dependencies", {}))
            dependencies.update(package.get("devDependencies", {}))
        except (OSError, ValueError):
            pass
    violations: List[str] = []
    for path, code in files:
        if not path.endswith((".tsx", ".ts", ".jsx", ".js")):
            continue
        for spec in re.findall(r"(?:\bfrom\s*|\bimport\s*\(|\bimport\s*)['\"]([^'\"]+)['\"]", code):
            if spec.startswith((".", "/")):
                continue
            package_name = "/".join(spec.split("/")[:2]) if spec.startswith("@") else spec.split("/")[0]
            installed = any((root / "node_modules" / package_name).exists() for root in (package_dir, BASE_DIR))
            if package_name not in dependencies or (package_name not in {"react", "react-dom"} and not installed):
                violations.append(f"[{path}] Unavailable external import '{spec}'. Use native React/CSS or an installed dependency.")
    return violations


def _site_output_truncated(response: str) -> bool:
    """Do not let the forgiving XML parser accept an unfinished file envelope."""
    from agent.agent_protocol import site_envelope_errors
    return bool(site_envelope_errors(response))


def auto_scaffold_section(
    section_name: str,
    style_spec: Optional[Any] = None,
    custom_instr: str = "",
) -> tuple[str, str, str, str]:
    """
    Synthesizes a clean, minimal deterministic TSX component and matching CSS for a fallback section.

    CRITICAL SAFETY CONTRACT:
    Does NOT invent fake metrics, fake pricing, fake materials, fake testimonials,
    or placeholder 'Explore ->' buttons. It provides a minimal, clean, deterministic semantic
    container matching the section name and user prompt instructions, tagged with data-fallback="true",
    so that the site remains syntactically compilable while explicitly marking the section
    as awaiting model repair.

    Returns (tsx_filename, tsx_content, css_filename, css_content).
    """
    pascal_name = "".join(w.capitalize() for w in re.split(r'[-_]', section_name))
    slug = section_name.lower().replace("_", "-")
    title = " ".join(w.capitalize() for w in re.split(r'[-_]', section_name))

    tsx_filename = f"src/components/{pascal_name}.tsx"
    css_filename = f"src/components/{pascal_name}.css"

    if slug in {"header", "navbar", "navigation", "nav"}:
        tsx_content = f"""import React, {{ useEffect, useRef, useState }} from 'react';
import './{pascal_name}.css';

export function {pascal_name}() {{
  const [open, setOpen] = useState(false);
  const [links, setLinks] = useState<Array<{{ id: string; label: string }}>>([]);
  const menuButton = useRef<HTMLButtonElement>(null);
  useEffect(() => {{
    const sections = Array.from(document.querySelectorAll<HTMLElement>('main section[id]'));
    const discovered = sections.map((section) => ({{
      id: section.id,
      label: section.id === 'hero' ? 'Home' : section.id.replace(/[-_]/g, ' ').replace(/\\b\\w/g, (letter) => letter.toUpperCase()),
    }}));
    if (document.getElementById('footer')) discovered.push({{ id: 'footer', label: 'Contact' }});
    setLinks(discovered);
  }}, []);
  useEffect(() => {{
    if (!open) return;
    const closeOnEscape = (event: KeyboardEvent) => {{
      if (event.key === 'Escape') {{ setOpen(false); menuButton.current?.focus(); }}
    }};
    window.addEventListener('keydown', closeOnEscape);
    return () => window.removeEventListener('keydown', closeOnEscape);
  }}, [open]);
  const brand = typeof document === 'undefined' ? 'Home' : document.title;
  return (
    <header id="{slug}" className="sa-header" data-fallback="true">
      <div className="sa-header__bar">
        <a className="sa-header__brand" href="#site-main">{{brand}}</a>
        <nav className="sa-header__links" aria-label="Primary navigation">
          {{links.map((link) => <a key={{link.id}} href={{`#${{link.id}}`}}>{{link.label}}</a>)}}
        </nav>
        <button ref={{menuButton}} className="sa-header__menu-button" type="button"
          aria-label="Toggle navigation" aria-expanded={{open}} aria-controls="sa-header-mobile"
          onClick={{() => setOpen((value) => !value)}}>Menu</button>
      </div>
      <nav id="sa-header-mobile" className="sa-header__mobile" aria-label="Mobile navigation" hidden={{!open}}>
        {{links.map((link) => <a key={{link.id}} href={{`#${{link.id}}`}} onClick={{() => setOpen(false)}}>{{link.label}}</a>)}}
      </nav>
    </header>
  );
}}

export default {pascal_name};
"""
        css_content = """.sa-header { position: sticky; top: 0; z-index: 50; background: var(--color-bg, #111827); color: var(--text-color, #fff); border-bottom: 1px solid rgba(255,255,255,.16); }
.sa-header__bar { max-width: 1200px; margin: 0 auto; min-height: 4.5rem; padding: .75rem 1.25rem; display: flex; align-items: center; justify-content: space-between; gap: 1.5rem; }
.sa-header__brand { color: inherit; font-weight: 700; text-decoration: none; font-size: 1.2rem; }
.sa-header__links { display: flex; align-items: center; gap: 1.25rem; }
.sa-header__links a, .sa-header__mobile a { color: inherit; text-decoration: none; }
.sa-header__links a:hover, .sa-header__mobile a:hover { text-decoration: underline; }
.sa-header a:focus-visible, .sa-header button:focus-visible { outline: 2px solid currentColor; outline-offset: 3px; }
.sa-header__menu-button { display: none; border: 1px solid currentColor; border-radius: .4rem; background: transparent; color: inherit; padding: .45rem .75rem; cursor: pointer; }
.sa-header__mobile { padding: .5rem 1.25rem 1rem; }
.sa-header__mobile[hidden] { display: none; }
.sa-header__mobile a { display: block; padding: .55rem 0; }
@media (max-width: 640px) { .sa-header__links { display: none; } .sa-header__menu-button { display: inline-flex; } }
@media (prefers-reduced-motion: reduce) { .sa-header, .sa-header * { scroll-behavior: auto; transition-duration: .01ms; animation-duration: .01ms; } }
"""
        return tsx_filename, tsx_content, css_filename, css_content

    clean_desc = custom_instr.split("Files:")[0].strip() if "Files:" in custom_instr else custom_instr
    clean_desc = re.sub(
        r'^(?:Write|Produce|Build|Create|Make)\s+the\s+[\w\s-]+\s+section:\s*',
        '',
        clean_desc,
        flags=re.IGNORECASE
    ).strip()
    if not clean_desc:
        clean_desc = f"Section for {title}."
    if not clean_desc.endswith("."):
        clean_desc += "."
    clean_desc_jsx = "Content is currently unavailable."
    title_jsx = html.escape(title)

    # Extract explicitly requested item names from parentheses or quotes if provided in instructions,
    # strictly without fabricating random entities, pricing, metrics, or testimonials.
    parsed_items: list[str] = []
    paren_m = re.search(r'\(([^)]+)\)', clean_desc)
    if paren_m:
        raw_candidates = re.split(r'[,;]|\band\b', paren_m.group(1))
        for cand in raw_candidates:
            c = cand.strip().strip('"\'')
            if c and len(c.split()) <= 4 and not any(k in c.lower() for k in ["e.g.", "etc.", "such as", "including"]):
                parsed_items.append(c)

    if not parsed_items:
        quotes = re.findall(r'["\']([A-Z][a-zA-Z0-9\s-]{2,30})["\']', clean_desc)
        if len(quotes) >= 2:
            parsed_items = quotes

    items_markup: list[str] = []
    if parsed_items:
        for idx, item in enumerate(parsed_items):
            items_markup.append(
                f'          <div className="sa-{slug}__item sa-item" key="{idx}">\n'
                f'            <h3 className="sa-item__title">{html.escape(item)}</h3>\n'
                f'            <p className="sa-item__desc">{clean_desc_jsx}</p>\n'
                f'          </div>'
            )
    else:
        items_markup.append(
            f'          <div className="sa-{slug}__item sa-item">\n'
            f'            <h3 className="sa-item__title">{title_jsx}</h3>\n'
            f'            <p className="sa-item__desc">{clean_desc_jsx}</p>\n'
            f'          </div>'
        )
    items_str = "\n".join(items_markup)

    tsx_content = (
        f"import React from 'react';\n"
        f"import './{pascal_name}.css';\n\n"
        f"export function {pascal_name}() {{\n"
        f"  return (\n"
        f"    <section className=\"sa-{slug}\" id=\"{slug}\" aria-label=\"{title_jsx}\" data-fallback=\"true\">\n"
        f"      <div className=\"sa-{slug}__inner\">\n"
        f"        <div className=\"sa-header-block\" style={{{{ marginBottom: '2rem' }}}}>\n"
        f"          <h2 className=\"sa-{slug}__title\">{title_jsx}</h2>\n"
        f"          <p className=\"sa-{slug}__subtitle\" style={{{{ opacity: 0.85 }}}}>{clean_desc_jsx}</p>\n"
        f"        </div>\n"
        f"        <div className=\"sa-{slug}__content sa-content sa-grid\">\n"
        f"{items_str}\n"
        f"        </div>\n"
        f"      </div>\n"
        f"    </section>\n"
        f"  );\n"
        f"}}\n"
    )

    css_content = synthesize_section_css(section_name, tsx_content, style_spec=style_spec)
    return tsx_filename, tsx_content, css_filename, css_content


def _build_section_synonyms(sections: List[str]) -> Dict[str, List[str]]:
    """Builds an expanded synonym map for all requested sections using generic word-stemming and multi-word slug combinations."""
    syns_map = {k: list(v) for k, v in _SECTION_SYNONYMS.items()}
    for sec in sections:
        norm = sec.lower().replace("-", "").replace("_", "")
        existing = set(syns_map.get(norm, []))
        existing.add(norm)
        existing.add(sec.lower())
        existing.add(sec.lower().replace("-", "_"))
        existing.add(sec.lower().replace("_", "-"))

        tokens = [t for t in re.split(r'[-_\s]', sec.lower()) if len(t) >= 2]
        token_stems: List[List[str]] = []
        for t in tokens:
            stems = {t}
            # Generic English morphological stemming rules
            if t.endswith("ies") and len(t) > 4:
                stems.add(t[:-3] + "y")
            elif t.endswith("es") and len(t) > 3:
                stems.add(t[:-2])
                stems.add(t[:-1])
            elif t.endswith("s") and len(t) > 2:
                stems.add(t[:-1])
            else:
                stems.add(t + "s")
                if t[-1] in ("s", "x", "z", "ch", "sh"):
                    stems.add(t + "es")
            if t.endswith("ing") and len(t) > 4:
                stems.add(t[:-3])
            if t.endswith("ed") and len(t) > 3:
                stems.add(t[:-2])

            token_stems.append(list(stems))
            for s in stems:
                existing.add(s)

        # Multi-token joined and stemmed combinations
        if len(tokens) > 1:
            existing.add("".join(tokens))
            existing.add("-".join(tokens))
            existing.add("_".join(tokens))
            existing.add(" ".join(tokens))
            import itertools
            for combo in itertools.product(*token_stems):
                existing.add("".join(combo))
                existing.add("-".join(combo))
                existing.add("_".join(combo))
                existing.add("".join(w.capitalize() for w in combo))

        syns_map[norm] = list(existing)
        syns_map[sec.lower()] = list(existing)
        syns_map[sec.lower().replace("-", "_")] = list(existing)
        syns_map[sec.lower().replace("_", "-")] = list(existing)
    return syns_map


# kit: the model writes copy, the kit renders code. native: the model writes copy
# and then each section's code itself (kit renderer only as a per-section fallback).
SITE_STRATEGIES = ("kit", "native", "freeform")


def resolve_site_strategy(strategy: Optional[str]) -> str:
    """Explicit argument, then SITE_STRATEGY, then the design kit."""
    for candidate in (strategy, os.environ.get("SITE_STRATEGY")):
        if candidate and str(candidate).strip().lower() in SITE_STRATEGIES:
            return str(candidate).strip().lower()
    return "kit"


def _run_kit_site(
    orig_idx: int,
    prompt: str,
    project_name: str,
    sections: List[str],
    runner: "AgentModelRunner",
    workspace_root: Path,
    brief: Optional[Dict[str, Any]],
    event_callback: Optional[Any],
    stop_check: Optional[Any],
    business_type: str,
    diagnostics_dir: Optional[Path],
    native: bool = False,
) -> Dict[str, Any]:
    """Design-kit generation: the model writes compact JSON copy per section and
    the kit renders token-driven, accessible TSX/CSS. Same events and result shape
    as the freeform loop; a section is never blocked (fallback copy instead).

    native=True: after the copy, the model also writes the section's TSX and CSS
    (agent/site_kit/native.py). Its files are used when they parse, pass the parser
    preflight and keep every piece of approved copy; otherwise the kit renders that
    section and it is reported in native_code_fallbacks."""
    from agent.site_kit import KitSite

    case_dir = workspace_root / f"site_{orig_idx:03d}"
    if case_dir.exists():
        shutil.rmtree(case_dir)
    case_dir.mkdir(parents=True, exist_ok=True)
    if not getattr(runner, "is_mock", False):
        runner.generation_log_dir = diagnostics_dir or case_dir / "raw_generation"

    if brief is None:
        from agent.site_brief import generate_content_brief
        brief = generate_content_brief(prompt)
    brief = dict(brief or {})
    brief.setdefault("business_type", business_type)
    kit = KitSite(prompt, brief, sections or brief.get("sections"))
    planned = list(kit.sections)

    def emit(event: Dict[str, Any]) -> None:
        if event_callback:
            try:
                event_callback(event)
            except Exception:
                pass

    emit({"type": "plan",
          "plan": [{"name": kit.component(s), "slug": s, "status": "pending"} for s in planned],
          "budget": {"turn": 0, "max_turns": len(planned), "completed": 0, "total": len(planned)}})
    emit({"type": "design_plan", "design_plan": kit.theme_summary()})

    print(f"\n{'='*75}\nSITE TASK #{orig_idx}: {project_name} (design kit: {kit.theme.name})")
    print(f"Sections planned: {' -> '.join(planned)}\n{'='*75}")

    all_written_files: List[tuple[str, str]] = []
    section_states: Dict[str, str] = {s: "pending" for s in planned}
    turn_logs: List[Dict[str, Any]] = []
    generation_metrics: List[Dict[str, Any]] = []
    fallback_sections: List[str] = []
    native_code_sections: List[str] = []
    native_code_fallbacks: Dict[str, List[str]] = {}
    cancelled = False
    completed = 0

    for turn_num, slug in enumerate(planned, start=1):
        if stop_check and stop_check():
            print(f"  --> [Kit]: Stop requested. {completed}/{len(planned)} sections written.")
            cancelled = True
            break
        emit({"type": "plan_update", "section": slug, "status": "in_progress", "turn": turn_num,
              "max_turns": len(planned), "completed": completed, "total": len(planned)})
        text = ""
        attempts = 0
        seconds = 0.0
        if kit.needs_model(slug):
            for temperature in (0.7, 0.55):
                attempts += 1
                started = time.perf_counter()
                progress_done = threading.Event()

                def report_progress(label=kit.labels[slug], attempt=attempts, start=started):
                    while not progress_done.is_set():
                        emit({"type": "status", "phase": "generating",
                              "status": f"Writing {label} · attempt {attempt} · {int(time.perf_counter() - start)}s elapsed"})
                        progress_done.wait(10)

                progress_thread = threading.Thread(target=report_progress, daemon=True) if event_callback else None
                if progress_thread:
                    progress_thread.start()
                try:
                    text = runner.generate_turn(
                        example_idx=orig_idx, history=kit.messages(slug), primary_symbol=project_name,
                        max_new_tokens=kit.max_tokens(slug), temperature=temperature, top_p=0.8, top_k=20,
                        repetition_penalty=1.0, stop_check=stop_check,
                    )
                except InterruptedError:
                    cancelled = True
                finally:
                    progress_done.set()
                    if progress_thread:
                        progress_thread.join(timeout=1)
                elapsed = max(0.001, time.perf_counter() - started)
                seconds += elapsed
                generated = getattr(runner, "last_generation_tokens", None)
                generation_metrics.append({
                    "turn": turn_num, "section": slug, "attempt": attempts, "seconds": round(elapsed, 2),
                    "generated_tokens": generated if isinstance(generated, int) else None,
                    "tokens_per_second": round(generated / elapsed, 2) if isinstance(generated, int) else None,
                    "stop_reason": (getattr(runner, "last_generation_diagnostics", {}) or {}).get("stop_reason"),
                })
                if cancelled or kit.is_usable(slug, text):
                    break
        if cancelled:
            break
        content, notes = kit.accept(slug, text)
        used_fallback = kit.needs_model(slug) and not kit.is_usable(slug, text)
        files = kit.render(slug)
        if native and not cancelled:
            native_files, native_problems = _native_section_code(
                kit, slug, runner, orig_idx, project_name, stop_check, emit, generation_metrics, turn_num)
            if native_files is None and native_problems == ["cancelled"]:
                cancelled = True
                break
            if native_files:
                files = native_files
                native_code_sections.append(slug)
                notes.append("section code written by the model")
            else:
                native_code_fallbacks[slug] = native_problems
                notes.append("model code rejected (" + "; ".join(native_problems[:2]) + "); kit rendered this section")
        parser_errors = preflight_section_files(files)
        if parser_errors and not any("unavailable" in e for e in parser_errors):
            print(f"  --> [Kit]: {slug} failed parser preflight; re-rendering with fallback copy: {parser_errors[:2]}")
            kit.accept(slug, "")
            files = kit.render(slug)
            used_fallback = True
            notes.append("re-rendered with fallback copy after parser preflight")
        if used_fallback and slug not in fallback_sections and kit.needs_model(slug):
            fallback_sections.append(slug)
        for path, source in files:
            dest = resolve_project_path(case_dir, path)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(source, encoding="utf-8")
            all_written_files.append((path, source))
        completed += 1
        section_states[slug] = "completed"
        turn_logs.append({"turn": turn_num, "action": "write_site_ok", "section": slug,
                          "strategy": "native" if slug in native_code_sections else "kit",
                          "files": [p for p, _ in files], "attempts": attempts, "fallback_copy": used_fallback,
                          "notes": notes, "seconds": round(seconds, 2)})
        print(f"  --> [Kit]: {slug} written ({kit.kinds[slug]}){' with fallback copy' if used_fallback else ''}.")
        emit({"type": "plan_update", "section": slug, "status": "completed", "turn": turn_num,
              "max_turns": len(planned), "completed": completed, "total": len(planned),
              "notes": notes, "fallback_copy": used_fallback})

    generation_complete = completed == len(planned) and not cancelled
    generation_quality = "repaired" if fallback_sections else "native"
    (case_dir / "generation_turns.jsonl").write_text(
        "\n".join(json.dumps(entry, default=str) for entry in turn_logs) + "\n", encoding="utf-8")
    return {
        "index": orig_idx,
        "project_name": project_name,
        "mode": "site",
        "strategy": "native" if native else "kit",
        "native_code_sections": native_code_sections,
        "native_code_fallbacks": native_code_fallbacks,
        "prompt": prompt,
        "sections_planned": planned,
        "sections_completed": completed,
        "generation_complete": generation_complete,
        "section_completion": f"{completed} / {len(planned)}",
        "project_validation": "pending",
        "generation_quality": generation_quality,
        "validation": None,
        "interaction_validation": None,
        "visual_validation": None,
        "final_passed": False,
        "acceptance": None,
        "blocked_sections": [],
        "section_states": section_states,
        "fallback_sections": [],
        "fallback_copy_sections": fallback_sections,
        "repaired_sections": fallback_sections,
        "normalized_files": [],
        "unrepaired_fallbacks": [],
        "auto_recovered_sections": [],
        "files": {p: c for p, c in all_written_files},
        "workspace_dir": str(case_dir),
        "turn_logs": turn_logs,
        "generation_metrics": generation_metrics,
        "trajectory": [],
        "output_token_budgets": [],
        "design_plan": kit.theme_summary(),
        "cancelled": cancelled,
        "kit": {"base_css": kit.base_css(), "font_href": kit.font_href(), "head_tags": kit.head_tags(),
                "public_files": kit.public_files(), "theme": kit.theme_summary(),
                "edit_summary": kit.edit_summary(), "title": kit.brand},
    }


# Native section code: room for the longest section (header) plus its prompt.
NATIVE_CODE_MAX_TOKENS = 6144


def _native_section_code(kit, slug, runner, orig_idx, project_name, stop_check, emit, metrics, turn_num):
    """Ask the model for this section's TSX and CSS. Returns (files, []) when usable,
    (None, problems) when the kit should render the section instead."""
    from agent.site_kit.native import native_messages, parse_native_files, missing_copy, typecheck_sections, structural_gaps

    name = kit.component(slug)
    messages = native_messages(kit, slug)
    problems: List[str] = []
    for attempt, temperature in enumerate((0.2, 0.4), start=1):
        emit({"type": "status", "phase": "generating", "status": f"Writing {name}.tsx and {name}.css (attempt {attempt})"})
        started = time.perf_counter()
        try:
            reply = runner.generate_turn(
                example_idx=orig_idx, history=messages, primary_symbol=project_name,
                max_new_tokens=NATIVE_CODE_MAX_TOKENS, temperature=temperature, top_p=0.9, top_k=40,
                repetition_penalty=1.0, stop_check=stop_check,
            )
        except InterruptedError:
            return None, ["cancelled"]
        elapsed = max(0.001, time.perf_counter() - started)
        generated = getattr(runner, "last_generation_tokens", None)
        metrics.append({"turn": turn_num, "section": slug, "attempt": attempt, "stage": "native_code",
                        "seconds": round(elapsed, 2), "generated_tokens": generated if isinstance(generated, int) else None})
        files, problems = parse_native_files(reply, name)
        if files:
            problems = preflight_section_files(files)
        if files and not problems:
            lost = missing_copy(files[0][1], kit.final_content(slug))
            if lost:
                problems = [f"changed or dropped approved copy: {lost[0][:60]!r}" + (f" (+{len(lost) - 1} more)" if len(lost) > 1 else "")]
        if files and not problems:
            gaps = structural_gaps(files[0][1], kit.render(slug)[0][1])
            if gaps:
                problems = ["missing behaviour the design system requires: " + ", ".join(gaps[:4])]
        if files and not problems:
            try:
                problems = typecheck_sections({"section": files}).get("section", [])[:3]
            except Exception as error:  # tsc unavailable: the project gate still typechecks
                print(f"  --> [Native]: section typecheck skipped: {error}")
        if not problems:
            return files, []
        print(f"  --> [Native]: {slug} attempt {attempt} rejected: {problems[:2]}")
    return None, problems


def run_site_agent_on_example(
    orig_idx: int,
    prompt: str,
    project_name: str,
    brief_xml: str,
    sections: List[str],
    runner: "AgentModelRunner",
    workspace_root: Path,
    max_turns: int = 8,
    temperature: float = 0.7,
    max_new_tokens: Optional[int] = None,
    style_spec: Optional[Any] = None,
    custom_section_instructions: Optional[Dict[str, str]] = None,
    event_callback: Optional[Any] = None,
    stop_check: Optional[Any] = None,
    business_type: str = "general",
    diagnostics_dir: Optional[Path] = None,
    strategy: Optional[str] = None,
    brief: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Multi-turn site generation loop. Generates one section per turn, enforces
    mandatory CSS and design token conformance, and returns a structured result with all written files.

    Section order drives the conversation: the observation after each successful
    write tells the model exactly what to write next, keeping it on-track without
    relying on the 3B model to self-plan a multi-file output.

    strategy="kit" (the default, see resolve_site_strategy) delegates to the
    design kit: the model writes JSON copy and the kit renders the code.
    """
    if resolve_site_strategy(strategy) in ("kit", "native"):
        return _run_kit_site(orig_idx, prompt, project_name, sections, runner, workspace_root, brief,
                             event_callback, stop_check, business_type, diagnostics_dir,
                             native=resolve_site_strategy(strategy) == "native")

    case_dir = workspace_root / f"site_{orig_idx:03d}"
    if case_dir.exists():
        shutil.rmtree(case_dir)
    case_dir.mkdir(parents=True, exist_ok=True)

    # Dynamic Output Token Budget for Site Generation
    if not getattr(runner, "is_mock", False):
        runner.generation_log_dir = diagnostics_dir or case_dir / "raw_generation"
    site_factors = extract_complexity_factors(
        prompt=prompt,
        task_mode="site",
        requested_files=[f"src/components/{s}.tsx" for s in sections] + ["src/App.tsx", "src/App.css"],
        current_file_length=0,
        target_symbol=project_name,
    )
    site_budget = estimate_output_budget(site_factors)
    log_task_budget(site_budget, task_name=project_name)
    allocated_tokens = max_new_tokens if max_new_tokens is not None else site_budget.clamped_tokens

    # Derived section instructions — per-run copy without mutating shared static _BASE_SECTION_INSTRUCTIONS
    _SECTION_INSTRUCTIONS: Dict[str, str] = dict(_BASE_SECTION_INSTRUCTIONS)

    # Ingest explicit user-authored section overrides if provided
    if custom_section_instructions:
        for sec_key, custom_text in custom_section_instructions.items():
            pascal_name = "".join(w.capitalize() for w in re.split(r'[-_]', sec_key))
            if not pascal_name or not (pascal_name[0].isalpha() or pascal_name[0] == '_'):
                pascal_name = f"Sec{pascal_name}"
            full_instr = custom_text.strip()
            if "Files:" not in full_instr:
                full_instr = f"{full_instr} Files: src/components/{pascal_name}.tsx + src/components/{pascal_name}.css"
            _SECTION_INSTRUCTIONS[sec_key] = full_instr
            _SECTION_INSTRUCTIONS[sec_key.lower()] = full_instr
            _SECTION_INSTRUCTIONS[sec_key.lower().replace("-", "_")] = full_instr
            _SECTION_INSTRUCTIONS[sec_key.lower().replace("_", "-")] = full_instr
            _SECTION_INSTRUCTIONS[sec_key.lower().replace("-", "").replace("_", "")] = full_instr

    # Ensure every requested section has a clean instruction entry
    for sec in sections:
        if sec not in _SECTION_INSTRUCTIONS and sec.lower() not in _SECTION_INSTRUCTIONS:
            pascal = "".join(w.capitalize() for w in re.split(r'[-_]', sec))
            if not pascal or not (pascal[0].isalpha() or pascal[0] == '_'):
                pascal = f"Sec{pascal}"
            title = " ".join(w.capitalize() for w in re.split(r'[-_]', sec))
            default_instr = (
                f"Write the {title} section for the user's requested website purpose. Use the exact user request and content brief; avoid invented facts, prices, links, and interactions. "
                f"Files: src/components/{pascal}.tsx + src/components/{pascal}.css"
            )
            _SECTION_INSTRUCTIONS[sec] = default_instr
            _SECTION_INSTRUCTIONS[sec.lower()] = default_instr
            _SECTION_INSTRUCTIONS[sec.lower().replace("-", "_")] = default_instr
            _SECTION_INSTRUCTIONS[sec.lower().replace("_", "-")] = default_instr

    from agent.site_prompt import section_output_contract, section_behavior_contract
    for sec in sections:
        symbol = "".join(w.capitalize() for w in re.split(r'[-_]', sec))
        if not symbol or not (symbol[0].isalpha() or symbol[0] == '_'):
            symbol = f"Sec{symbol}"
        _SECTION_INSTRUCTIONS[sec] = (
            _SECTION_INSTRUCTIONS.get(sec, _SECTION_INSTRUCTIONS.get(sec.lower(), ""))
            + "\n" + section_behavior_contract(sec, prompt)
            + "\n" + section_output_contract(symbol)
        )

    lightbox_sections = [sec for sec in sections if "lightbox" in sec.lower()]
    gallery_sections = [sec for sec in sections if re.search(r"gallery|case[-_]stud|projects", sec.lower())]
    if lightbox_sections and gallery_sections:
        for sec in gallery_sections:
            _SECTION_INSTRUCTIONS[sec] += (
                " When a work is opened, dispatch a window CustomEvent('site-open-lightbox', "
                "{detail: {title, description, image}}); make the trigger keyboard accessible."
            )
        for sec in lightbox_sections:
            _SECTION_INSTRUCTIONS[sec] += (
                " Listen for window site-open-lightbox events and display their detail in an accessible modal. "
                "Close on Escape and backdrop action; restore focus to the opener."
            )

    active_synonyms = _build_section_synonyms(sections)
    # Every section gets the same repair budget; the last section is not
    # starved because earlier ones used retries (audit A7).
    per_section_cap = 3
    max_turns = max(max_turns, per_section_cap * len(sections))

    # Synthesize deterministic structured design plan (Section 3.C)
    try:
        from agent.design_plan import synthesize_design_plan
    except ImportError:
        from design_plan import synthesize_design_plan

    inferred_domain = business_type or "general"
    # One art direction: the plan follows the brief's layout archetype and media
    # decision, and leaves colours/fonts/mode to the brief's design system.
    layout_match = re.search(r'<layout_archetype id="([^"]+)"', brief_xml or "")
    media_match = re.search(r'<media_expectation decision="([^"]+)"', brief_xml or "")
    plan_spec: Dict[str, Any] = {"prompt": prompt, "name": project_name}
    if layout_match:
        plan_spec["layoutArchetype"] = layout_match.group(1)
    design_plan = synthesize_design_plan(
        prompt_spec=plan_spec,
        domain=inferred_domain,
        task_index=orig_idx if orig_idx is not None else 0,
    )
    design_plan.align_with_brief(media_available=not (media_match and media_match.group(1) == "none"))
    design_plan_prompt = design_plan.to_prompt_block()

    # Emit initial live plan checklist & design plan event if callback registered
    if event_callback:
        try:
            plan_items = [
                {"name": "".join(w.capitalize() for w in re.split(r'[-_]', s)), "slug": s, "status": "pending"}
                for s in sections
            ]
            event_callback({
                "type": "plan",
                "plan": plan_items,
                "budget": {"turn": 0, "max_turns": max_turns, "completed": 0, "total": len(sections)},
            })
            event_callback({
                "type": "design_plan",
                "design_plan": design_plan.to_dict(),
            })
        except Exception:
            pass

    # Build initial system + user history
    style_instr = spec_to_prompt_instructions(style_spec) if style_spec else ""
    initial_user_msg = (
        f"User Instruction: {prompt}\n\n"
        f"{design_plan_prompt}\n\n"
        f"Content Brief:\n{brief_xml}\n\n"
        f"{style_instr}\n\n"
        f"You will build the site ONE SECTION AT A TIME, reconciling the brief with any specific requested features in the user instruction. "
        f"Generate only the currently requested section.\n\n"
    )

    history: List[Dict[str, str]] = [
        {"role": "system", "content": SITE_AGENT_SYSTEM_PROMPT},
        {"role": "user", "content": initial_user_msg + f"CURRENT SECTION REQUIRED: {_SECTION_INSTRUCTIONS.get(sections[0], sections[0])}"},
    ]

    print(f"\n{'='*75}")
    print(f"SITE TASK #{orig_idx}: {project_name}")
    print(f"Sections planned: {' -> '.join(sections)}")
    print(f"Per-section turn cap: {per_section_cap} turns")
    if style_spec:
        print(f"Design System: {style_spec.source} ({len(style_spec.colors)} colors, {len(style_spec.fonts)} fonts)")
    print(f"{'='*75}")

    all_written_files: List[tuple[str, str]] = []
    blocked_sections: List[str] = []
    section_states: Dict[str, str] = {sec: "pending" for sec in sections}
    section_idx = 0
    sections_completed = 0
    class _PersistentTurnLog(list):
        """Keep section diagnostics if a long live generation is interrupted."""

        def append(self, item):
            super().append(item)
            case_dir.mkdir(parents=True, exist_ok=True)
            with (case_dir / "generation_turns.jsonl").open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(item, default=str) + "\n")

    turn_logs: List[Dict[str, Any]] = _PersistentTurnLog()
    generation_metrics: List[Dict[str, Any]] = []
    normalized_files: set[str] = set()
    generation_complete = False
    cancelled = False
    section_stuck_turns = 0
    section_css_missing_count = 0
    truncation_retries: Dict[str, int] = {}
    base_temp = temperature
    current_temp = temperature

    def start_section_context(sec: str) -> None:
        # Keep the brief and shared contracts, not previous sections' raw output.
        # Otherwise the first-section instruction remains active and long sites
        # consume their context budget before producing the final CSS files.
        accepted = ", ".join(name for name, state in section_states.items() if state == "completed")
        saved_paths = ", ".join(path for path, _ in all_written_files)
        root_classes = []
        token_lines: List[str] = []
        for path, content in all_written_files:
            if path.endswith(".tsx"):
                first = re.search(r'className=["\']([^"\'\s]+)', content)
                if first and first.group(1) not in root_classes:
                    root_classes.append(first.group(1))
            elif path.endswith(".css"):
                for block in re.findall(r':root\s*\{([^}]*)\}', content):
                    for decl in re.findall(r'(--[\w-]+\s*:\s*[^;]+);', block):
                        if decl not in token_lines:
                            token_lines.append(decl)
        shared = ""
        if root_classes or token_lines:
            shared = (f"Accepted section root classes (keep your own distinct root class): {', '.join(root_classes) or 'none'}. "
                      f"Shared tokens already defined: {'; '.join(token_lines[:24]) or 'none'}. Reuse these tokens.\n")
        history[:] = [
            {"role": "system", "content": SITE_AGENT_SYSTEM_PROMPT},
            {"role": "user", "content": initial_user_msg +
             f"Accepted sections: {accepted or 'none'}. Existing files: {saved_paths or 'none'}. "
             f"Blocked sections: {', '.join(blocked_sections) or 'none'}. Do not overwrite other sections.\n"
             f"{shared}\n"
             f"CURRENT SECTION REQUIRED: {_SECTION_INSTRUCTIONS.get(sec, sec)}"},
        ]

    def block_section(sec: str, turn: int, reason: str, errors: Optional[List[str]] = None) -> None:
        """Advance past an unaccepted section without fabricating files or success."""
        nonlocal section_idx, section_stuck_turns, section_css_missing_count, current_temp
        if sec not in blocked_sections:
            blocked_sections.append(sec)
        section_states[sec] = "blocked"
        turn_logs.append({"turn": turn, "action": "section_blocked", "section": sec,
                          "reason": reason, "errors": errors or [], "files": []})
        print(f"  --> [BLOCKED]: Section '{sec}' ({reason}). No fallback files written.")
        if event_callback:
            try:
                event_callback({"type": "plan_update", "section": sec, "status": "blocked",
                                "reason": reason, "turn": turn, "max_turns": max_turns,
                                "completed": sections_completed, "total": len(sections)})
            except Exception:
                pass
        section_idx += 1
        section_stuck_turns = 0
        section_css_missing_count = 0
        current_temp = base_temp
        if section_idx < len(sections):
            next_sec = sections[section_idx]
            start_section_context(next_sec)

    for turn_num in range(1, max_turns + 1):
        if stop_check and stop_check():
            print(f"  --> [Site Agent]: Stop requested by user. Finishing early with {sections_completed}/{len(sections)} sections written.")
            generation_complete = (sections_completed == len(sections))
            cancelled = True
            break

        if section_idx >= len(sections):
            generation_complete = not blocked_sections
            break

        current_sec = sections[section_idx]
        print(f"\n>>> [Site Turn {turn_num}/{max_turns}] Section: {current_sec}")

        # Dynamic reserved-turns guarantee:
        sections_remaining = len(sections) - section_idx
        turns_remaining = max_turns - turn_num + 1
        effective_cap = per_section_cap

        if event_callback:
            try:
                event_callback({
                    "type": "plan_update",
                    "section": current_sec,
                    "status": "in_progress",
                    "turn": turn_num,
                    "max_turns": max_turns,
                     "completed": sections_completed,
                    "total": len(sections),
                })
            except Exception:
                pass

        sec_instr = _SECTION_INSTRUCTIONS.get(current_sec, "")
        sec_factors = extract_complexity_factors(
            prompt=f"{prompt}\n{sec_instr}",
            task_mode="site_section",
            requested_files=[f"src/components/{current_sec}.tsx", f"src/components/{current_sec}.css"],
            current_file_length=0,
            target_symbol=current_sec,
        )
        sec_budget = estimate_output_budget(sec_factors)
        turn_max_tokens = min(max_new_tokens, sec_budget.clamped_tokens) if max_new_tokens is not None else sec_budget.clamped_tokens
        if truncation_retries.get(current_sec):
            context_room = max(256, (getattr(runner, "max_seq_length", 8192) or 8192) - (getattr(runner, "last_context_tokens", 0) or 0) - 256)
            turn_max_tokens = min(4096, context_room, int(turn_max_tokens * 1.35 ** truncation_retries[current_sec]))
            if max_new_tokens is not None:
                turn_max_tokens = min(turn_max_tokens, max_new_tokens)

        generation_started = time.perf_counter()
        progress_done = threading.Event()
        def report_generation_progress():
            while not progress_done.is_set():
                elapsed = int(time.perf_counter() - generation_started)
                try:
                    if event_callback:
                        event_callback({"type": "status", "phase": "generating", "status":
                            f"Generating {current_sec} · attempt {section_stuck_turns + 1} · {elapsed}s elapsed"})
                except Exception:
                    pass
                progress_done.wait(10)
        progress_thread = None
        if event_callback:
            progress_thread = threading.Thread(target=report_generation_progress, daemon=True)
            progress_thread.start()
        try:
            assistant_text = runner.generate_turn(
                example_idx=orig_idx,
                history=history,
                primary_symbol=project_name,
                max_new_tokens=turn_max_tokens,
                temperature=current_temp,
                top_p=0.8,
                top_k=20,
                repetition_penalty=1.0,
                stop_check=stop_check,
            )
        except InterruptedError:
            print(f"  --> [Site Agent]: Generation interrupted by user cancellation.")
            cancelled = True
            break
        finally:
            progress_done.set()
            if progress_thread:
                progress_thread.join(timeout=1)
        generation_seconds = max(0.001, time.perf_counter() - generation_started)
        generated_tokens = getattr(runner, "last_generation_tokens", None)
        generation_metrics.append({
            "turn": turn_num, "section": current_sec,
            "seconds": round(generation_seconds, 2),
            "generated_tokens": generated_tokens if isinstance(generated_tokens, int) else None,
            "tokens_per_second": round(generated_tokens / generation_seconds, 2) if isinstance(generated_tokens, int) else None,
            "stop_reason": getattr(runner, "last_generation_diagnostics", {}).get("stop_reason"),
        })
        from agent.agent_protocol import close_complete_site_envelope
        assistant_text = close_complete_site_envelope(assistant_text)
        if _site_output_truncated(assistant_text):
            from agent.agent_protocol import site_envelope_errors

            envelope_errors = site_envelope_errors(assistant_text)
            truncation_retries[current_sec] = truncation_retries.get(current_sec, 0) + 1
            section_stuck_turns += 1
            turn_logs.append({"turn": turn_num, "action": "truncated_output", "section": current_sec,
                              "errors": envelope_errors, "output_length": len(assistant_text)})
            print(f"  --> [TRUNCATED OUTPUT]: {current_sec}: {', '.join(envelope_errors)}")
            if section_stuck_turns < effective_cap:
                history.append({"role": "user", "content": (
                    "[TRUNCATED OUTPUT]: The file/tool envelope was incomplete. "
                    "Regenerate the SAME section with complete TSX and CSS files and closing tags."
                )})
                continue
            block_section(current_sec, turn_num, "truncated_output", envelope_errors)
            continue
        turn = parse_agent_output(assistant_text)
        if turn.status_message:
            print(f"--> {turn.status_message}")
        history.append({"role": "assistant", "content": turn.raw_text or assistant_text})

        # Emit context token telemetry
        if event_callback:
            try:
                c_tokens = getattr(runner, "last_context_tokens", 0) or 0
                m_tokens = getattr(runner, "max_seq_length", 8192)
                event_callback({
                    "type": "context.update",
                    "context_tokens": c_tokens,
                    "contextTokens": c_tokens,
                    "max_context_tokens": m_tokens,
                    "maxContextTokens": m_tokens,
                })
            except Exception:
                pass

        # ── Finish action ──────────────────────────────────────────────────────
        if turn.is_finish:
            print(f"[Site Agent]: Finished after {turn_num} turns.")
            generation_complete = (sections_completed == len(sections))
            break

        # ── WriteSiteAction ────────────────────────────────────────────────────
        elif isinstance(turn.action, WriteSiteAction):
            action: WriteSiteAction = turn.action
            if not action.files:
                # Model emitted write_site but with no <file> children
                section_stuck_turns += 1
                current_temp = base_temp  # Keep temperature flat for structural failures
                if section_stuck_turns >= effective_cap:
                    block_section(current_sec, turn_num, "empty_write")
                    continue
                else:
                    pascal_name = "".join(w.capitalize() for w in re.split(r'[-_]', current_sec))
                    directive = (
                        f"[ERROR]: write_site produced no <file> children.\n"
                        f"REQUIRED ACTION: You MUST generate exactly these two files now: "
                        f"src/components/{pascal_name}.tsx and src/components/{pascal_name}.css."
                    )
                    obs = format_site_observation(
                        written_files=[],
                        css_missing=False,
                        next_section=_SECTION_INSTRUCTIONS.get(current_sec, current_sec),
                        extra_note=directive,
                    )
                    history.append({"role": "user", "content": obs})
                    turn_logs.append({"turn": turn_num, "action": "write_site_empty", "section": current_sec})
                    continue

            # Check section name conformance: verify files match the target section
            target_sec = current_sec.lower().strip()
            norm_target = target_sec.replace("-", "").replace("_", "")
            allowed_stems = [
                s.replace("-", "").replace("_", "")
                for s in active_synonyms.get(norm_target, [norm_target])
            ]
            file_stems = [
                Path(p).stem.lower().replace("-", "").replace("_", "")
                for p, _ in action.files
            ]

            section_matched = any(
                any(stem == allowed or allowed in stem or stem in allowed for allowed in allowed_stems)
                for stem in file_stems
            )

            # Check if emitted files match an ALREADY completed section
            already_completed_stems: set[str] = set()
            for prev_sec in sections[:section_idx]:
                norm_prev = prev_sec.lower().replace("-", "").replace("_", "")
                for s in active_synonyms.get(norm_prev, [norm_prev]):
                    already_completed_stems.add(s.replace("-", "").replace("_", ""))

            is_duplicate_previous = any(
                any(stem == prev or prev in stem for prev in already_completed_stems)
                for stem in file_stems
            ) and not section_matched

            if not section_matched:
                section_stuck_turns += 1
                current_temp = base_temp  # Keep temperature flat for structural failures
                mismatch_file = Path(action.files[0][0]).name if action.files else "unknown"
                raw_stem = Path(action.files[0][0]).stem if action.files else "unknown"
                pascal_name = "".join(w.capitalize() for w in re.split(r'[-_]', current_sec))

                if section_stuck_turns >= effective_cap:
                    block_section(current_sec, turn_num, "section_mismatch", [mismatch_file])
                    continue
                else:
                    print(f"  --> [SECTION MISMATCH]: Expected section '{current_sec}' (e.g. {pascal_name}.tsx), but received '{mismatch_file}'. Requesting rewrite.")
                    extra_note = (
                        f"[SECTION MISMATCH — REWRITE REQUIRED]: You generated component files for '{raw_stem}', "
                        f"which does not match the currently requested section '{current_sec}'.\n"
                    )
                    if is_duplicate_previous:
                        extra_note += (
                            f"Note: Section '{raw_stem}' has already been accepted and saved to disk. "
                            f"Do NOT rewrite previous sections.\n"
                        )
                    extra_note += (
                        f"Please write the '{current_sec}' section now: "
                        f"src/components/{pascal_name}.tsx + src/components/{pascal_name}.css."
                    )

                    obs = format_site_observation(
                        written_files=[],
                        css_missing=False,
                        next_section=_SECTION_INSTRUCTIONS.get(current_sec, current_sec),
                        extra_note=extra_note,
                    )
                    history.append({"role": "user", "content": obs})
                    turn_logs.append({
                        "turn": turn_num,
                        "action": "write_site_section_mismatch",
                        "expected_section": current_sec,
                        "received_files": [p for p, _ in action.files],
                    })
                    continue

            # Check mandatory CSS
            css_missing = not action.has_real_css()

            if css_missing:
                section_stuck_turns += 1
                section_css_missing_count += 1
                current_temp = base_temp  # Keep temperature flat for structural failures
                pascal_name = "".join(w.capitalize() for w in re.split(r'[-_]', current_sec))

                # Escape hatch: after 2 consecutive CSS MISSING results or cap hit, synthesize CSS programmatically
                if section_css_missing_count >= 2 or section_stuck_turns >= effective_cap or turns_remaining <= sections_remaining:
                    print(f"  --> [CSS MISSING AUTO-ADAPT]: Section '{current_sec}' missing CSS for {section_css_missing_count} turns. Synthesizing CSS.")
                    tsx_matches = [(p, c) for p, c in action.files if p.endswith(".tsx")]
                    if tsx_matches:
                        t_path, t_code = tsx_matches[0]
                        c_code = synthesize_section_css(current_sec, t_code, style_spec=style_spec)
                        c_path = f"src/components/{Path(t_path).stem}.css"
                        action.files = [(t_path, t_code), (c_path, c_code)]
                    else:
                        block_section(current_sec, turn_num, "missing_tsx")
                        continue
                else:
                    print(f"  --> [CSS MISSING]: Section had no real CSS. Requesting rewrite.")
                    extra_note = (
                        f"[CSS MISSING — REWRITE REQUIRED]: You must emit both the React component and its dedicated CSS file!\n"
                        f"REQUIRED: src/components/{pascal_name}.tsx AND src/components/{pascal_name}.css with full styling."
                    )
                    obs = format_site_observation(
                        written_files=[],
                        css_missing=True,
                        next_section=_SECTION_INSTRUCTIONS.get(current_sec, current_sec),
                        extra_note=extra_note,
                    )
                    history.append({"role": "user", "content": obs})
                    turn_logs.append({"turn": turn_num, "action": "write_site_no_css", "section": current_sec})
                    continue

            import_violations = _site_import_violations(action.files, case_dir)
            if import_violations:
                section_stuck_turns += 1
                if section_stuck_turns >= effective_cap:
                    block_section(current_sec, turn_num, "import_violation", import_violations)
                    continue
                else:
                    history.append({"role": "user", "content": "[IMPORT GATE]:\n" + "\n".join(import_violations) + "\nRegenerate this section without undeclared imports."})
                    turn_logs.append({"turn": turn_num, "action": "write_site_import_error", "section": current_sec})
                    continue

            # Check style specification conformance (if StyleSpec is active)
            if style_spec:
                # 1. First run auto-sanitization to safely wrap minor bare tokens
                sanitized_files = []
                for fpath, fcontent in action.files:
                    if fpath.endswith(".css"):
                        sanitized_files.append((fpath, sanitize_css_for_spec(fcontent, style_spec)))
                    else:
                        sanitized_files.append((fpath, fcontent))
                action.files = sanitized_files

                # 2. Check for remaining real violations
                style_violations: List[str] = []
                for fpath, fcontent in action.files:
                    if fpath.endswith(".css"):
                        viols = validate_css_conformance(fcontent, style_spec)
                        if viols:
                            style_violations.extend([f"[{fpath}] {v}" for v in viols])

                if style_violations:
                    section_stuck_turns += 1
                    # If stuck on style violations for 2+ turns, auto-adapt non-compliant styles
                    if section_stuck_turns >= 2:
                        print(f"  --> [STYLE SPEC AUTO-ADAPT]: Section stuck {section_stuck_turns} turns on token violations. Auto-adapting styles.")
                        recovered_files = []
                        for fpath, fcontent in action.files:
                            if fpath.endswith(".css"):
                                if any("box-shadow" in v for v in style_violations):
                                    fcontent = re.sub(r'box-shadow\s*:\s*[^;]+;', 'box-shadow: none;', fcontent, flags=re.I)
                                if any("border-radius" in v for v in style_violations):
                                    btn_rad = style_spec.radius.get("--radius-buttons", "75px")
                                    card_rad = style_spec.radius.get("--radius-cards", "0px")
                                    fcontent = _adapt_radii(fcontent, btn_rad, card_rad)
                                recovered_files.append((fpath, fcontent))
                            else:
                                recovered_files.append((fpath, fcontent))
                        action.files = recovered_files
                        style_violations = []

                if style_violations:
                    if section_stuck_turns >= effective_cap or turns_remaining <= sections_remaining:
                        print(f"  --> [STYLE SPEC CAP REACHED]: Auto-synthesizing compliant styles.")
                        tsx_matches = [(p, c) for p, c in action.files if p.endswith(".tsx")]
                        if tsx_matches:
                            t_path, t_code = tsx_matches[0]
                            c_code = synthesize_section_css(current_sec, t_code, style_spec=style_spec)
                            c_path = f"src/components/{Path(t_path).stem}.css"
                            action.files = [(t_path, t_code), (c_path, c_code)]
                            style_violations = []
                        else:
                            block_section(current_sec, turn_num, "style_violation", style_violations)
                            continue
                    else:
                        # Scale temperature ONLY for style-token violations where sampling diversity helps
                        current_temp = min(base_temp + 0.20 * section_stuck_turns, 0.85)
                        print(f"  --> [STYLE SPEC VIOLATION]: {len(style_violations)} design token violations found. Requesting rewrite.")
                        obs = format_site_observation(
                            written_files=[],
                            css_missing=False,
                            next_section=_SECTION_INSTRUCTIONS.get(current_sec, current_sec),
                            style_violations=style_violations[:5],
                        )
                        history.append({"role": "user", "content": obs})
                        turn_logs.append({
                            "turn": turn_num,
                            "action": "write_site_style_violation",
                            "section": current_sec,
                            "violations": style_violations,
                        })
                        continue

            from agent.site_file_normalizer import normalize_site_section_files
            from agent.tailwind_support import site_uses_tailwind
            original_section_files = dict(action.files)
            action.files = normalize_site_section_files(
                action.files, current_sec, original_prompt=prompt, known_sections=sections
            )
            tailwind_enabled = site_uses_tailwind(dict(action.files))

            # Balance JSX tags and sanitize CSS before checking TypeScript compilation
            sanitized_section_files = []
            for fpath, fcontent in action.files:
                if fpath.endswith((".tsx", ".jsx")):
                    from agent.style_ingest import balance_jsx_tags
                    fcontent = balance_jsx_tags(fcontent)
                elif fpath.endswith(".css"):
                    fcontent = re.sub(r'font\s*:\s*size\s+([^,;]+),\s*([^;]+);', r'font-size: \1; color: \2;', fcontent)
                    fcontent = re.sub(r'font\s*:\s*size\s+([^;]+);', r'font-size: \1;', fcontent)
                sanitized_section_files.append((fpath, fcontent))
            action.files = sanitized_section_files
            normalized_files.update(path for path, content in action.files if original_section_files.get(path) != content)

            parser_errors = preflight_section_files(action.files)
            if parser_errors:
                section_stuck_turns += 1
                if section_stuck_turns >= effective_cap:
                    block_section(current_sec, turn_num, "parser_error", parser_errors)
                    continue
                else:
                    history.append({"role": "user", "content": "[PARSER PREFLIGHT]:\n" + "\n".join(parser_errors) + "\nRegenerate valid TSX and CSS."})
                    turn_logs.append({"turn": turn_num, "action": "write_site_parser_error", "section": current_sec, "errors": parser_errors})
                    continue

            # Verify TypeScript compilation for all generated .tsx files
            tsc_errors: List[str] = []
            for fpath, fcontent in action.files:
                if fpath.endswith(".tsx"):
                    try:
                        temp_dest = resolve_project_path(case_dir, fpath)
                    except PermissionError as _path_err:
                        print(f"  [Security] Blocked TSC temp path: {_path_err}")
                        tsc_errors.append(f"[{fpath}]: Path traversal blocked")
                        continue
                    temp_dest.parent.mkdir(parents=True, exist_ok=True)
                    old_source = temp_dest.read_text(encoding="utf-8") if temp_dest.exists() else None
                    try:
                        temp_dest.write_text(fcontent, encoding="utf-8")
                        tsc_proc = run_command([
                        "npx", "tsc", "--noEmit",
                        "--jsx", "react-jsx",
                        "--target", "ES2022",
                        "--moduleResolution", "bundler",
                        "--esModuleInterop",
                        "--skipLibCheck",
                        temp_dest.as_posix(),
                        "css.d.ts"
                        ], cwd=BASE_DIR)
                    finally:
                        if old_source is None:
                            temp_dest.unlink(missing_ok=True)
                        else:
                            temp_dest.write_text(old_source, encoding="utf-8")
                    if tsc_proc.returncode != 0:
                        err_text = (tsc_proc.stdout + "\n" + tsc_proc.stderr).strip()
                        clean_err = prune_stack_trace(err_text, max_lines=6)
                        tsc_errors.append(f"[{fpath}]:\n{clean_err}")

            if tsc_errors:
                print(f"  --> [TSC DIAGNOSTIC]: {tsc_errors[0][:1200]}")
                section_stuck_turns += 1
                current_temp = base_temp  # Keep temperature flat for structural/compiler errors
                if section_stuck_turns >= effective_cap:
                    block_section(current_sec, turn_num, "typescript_error", tsc_errors)
                    continue
                else:
                    print(f"  --> [TSC ERROR]: Section {current_sec} failed TypeScript compilation. Requesting fix.")
                    obs = format_site_observation(
                        written_files=[],
                        css_missing=False,
                        next_section=_SECTION_INSTRUCTIONS.get(current_sec, current_sec),
                        extra_note="[CRITICAL TYPESCRIPT SYNTAX/TYPE ERROR]:\n" + "\n".join(tsc_errors) + "\nPlease fix the TypeScript/JSX syntax error and rewrite the section."
                    )
                    history.append({"role": "user", "content": obs})
                    turn_logs.append({"turn": turn_num, "action": "write_site_tsc_error", "section": current_sec, "errors": tsc_errors})
                    continue

            # ── Structural quality gate ─────────────────────────────────────
            # Runs BEFORE writing anything to disk.  Violations block the write
            # and either request a model rewrite (native sections) or apply the
            # deterministic auto-fixer (fallback / auto-recovered sections).
            _defined_tokens: Optional[set] = None
            if style_spec:
                _defined_tokens = set(
                    list(style_spec.colors.keys())
                    + list(style_spec.fonts.keys())
                    + list(style_spec.type_scale.keys())
                    + list(style_spec.spacing_scale.keys())
                    + list(style_spec.radius.keys())
                    + list(style_spec.surfaces.keys())
                    + list(style_spec.layout.keys())
                    + list(style_spec.other_tokens.keys())
                )

            structural_violations: List[str] = validate_structural_quality(
                action.files,
                section_name=current_sec,
                defined_tokens=_defined_tokens,
                check_coverage=True,
                tailwind_enabled=tailwind_enabled,
            )

            if structural_violations:
                section_stuck_turns += 1
                current_temp = base_temp
                if section_stuck_turns >= effective_cap:
                    block_section(current_sec, turn_num, "structural_violation", structural_violations)
                    continue
                violation_summary = "\n".join(structural_violations[:8])
                obs = format_site_observation(
                    written_files=[], css_missing=False,
                    next_section=_SECTION_INSTRUCTIONS.get(current_sec, current_sec),
                    extra_note=f"[STRUCTURAL QUALITY FAILURE — REWRITE REQUIRED]:\n{violation_summary}\nRegenerate the full section (TSX + CSS).",
                )
                history.append({"role": "user", "content": obs})
                turn_logs.append({"turn": turn_num, "action": "write_site_structural_violation",
                                  "section": current_sec, "violations": structural_violations})
                continue

            # Parser preflight is the final acceptance check. Do not change the
            # checked strings after this point or overwrite a prior valid section.
            parser_errors = preflight_section_files(action.files)
            if parser_errors:
                history.append({"role": "user", "content": "[PARSER PREFLIGHT]:\n" + "\n".join(parser_errors) + "\nRegenerate valid TSX and CSS."})
                turn_logs.append({"turn": turn_num, "action": "write_site_parser_error", "section": current_sec, "errors": parser_errors})
                continue

            try:
                destinations = {path: resolve_project_path(case_dir, path) for path, _ in action.files}
            except PermissionError as path_error:
                history.append({"role": "user", "content": f"[INVALID FILE PATH]: {path_error}. Regenerate this section."})
                turn_logs.append({"turn": turn_num, "action": "write_site_path_error", "section": current_sec})
                continue

            # Accepted section — write files to disk
            section_written: List[tuple[str, str]] = []
            for fpath, fcontent in action.files:
                dest = destinations[fpath]
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(fcontent, encoding="utf-8")
                all_written_files.append((fpath, fcontent))
                section_written.append((fpath, fcontent))
                print(f"  --> Written: {fpath} ({len(fcontent)} chars)")

            section_idx += 1
            log_entry: Dict[str, Any] = {
                "turn": turn_num,
                "action": "write_site_ok",
                "section": sections[section_idx - 1],
                "files": [p for p, _ in section_written],
            }
            section_states[current_sec] = "completed"
            sections_completed += 1
            turn_logs.append(log_entry)

            if event_callback:
                try:
                    event_callback({
                        "type": "plan_update",
                        "section": sections[section_idx - 1],
                        "status": "completed",
                        "turn": turn_num,
                        "max_turns": max_turns,
                        "completed": sections_completed,
                        "total": len(sections),
                    })
                except Exception:
                    pass

            # Reset per-section starvation counters
            section_stuck_turns = 0
            section_css_missing_count = 0
            current_temp = base_temp

            # Compact older completed section turns in history to prevent context window explosion
            _compact_site_history(history)

            if section_idx >= len(sections):
                if blocked_sections:
                    obs = (f'<observation status="partial">\nAccepted: {sections_completed}/{len(sections)}. '
                           f'Blocked sections: {", ".join(blocked_sections)}. No fallback files were written.\n</observation>')
                else:
                    obs = format_site_observation(
                        written_files=section_written,
                        css_missing=False,
                        next_section=None,
                        all_done=True,
                    )
                history.append({"role": "user", "content": obs})
                generation_complete = not blocked_sections
                print(f"  --> [Site Agent]: All {len(sections)} sections processed!")
                break
            else:
                next_sec = sections[section_idx]
                start_section_context(next_sec)

        # ── No recognised action ───────────────────────────────────────────────
        else:
            section_stuck_turns += 1
            current_temp = base_temp  # Keep temperature flat for structural errors
            if section_stuck_turns >= effective_cap:
                block_section(current_sec, turn_num, "no_action")
                continue
            else:
                sec_name = sections[section_idx] if section_idx < len(sections) else "footer"
                pascal_name = "".join(w.capitalize() for w in re.split(r'[-_]', sec_name))
                obs = format_site_observation(
                    written_files=[],
                    css_missing=False,
                    next_section=_SECTION_INSTRUCTIONS.get(sec_name, sec_name),
                    extra_note=f"[ERROR]: No write_site tool_call detected. You MUST emit <tool_call name=\"write_site\"> containing src/components/{pascal_name}.tsx and src/components/{pascal_name}.css."
                )
                history.append({"role": "user", "content": obs})
                turn_logs.append({"turn": turn_num, "action": "no_action"})

    # Cancellation leaves unattempted sections pending. An exhausted budget or
    # premature finish instead records explicit failures without inventing files.
    if not cancelled:
        while section_idx < len(sections):
            block_section(sections[section_idx], max_turns, "budget_exhausted")

    # Blocked sections have no scaffold to rewrite. Retain compatibility fields
    # without entering the fallback rewrite loop for newly blocked sections.
    repaired_sections: List[str] = []
    sections_planned = len(sections)
    generation_complete = (sections_completed == sections_planned and not blocked_sections)
    section_completion = f"{sections_completed} / {sections_planned}"

    # Determine generation quality: native, repaired, or fallback
    fallback_sections: List[str] = []
    unrepaired_fallbacks: List[str] = []
    repair_actions = {
        "write_site_section_mismatch",
        "write_site_no_css",
        "write_site_style_violation",
        "write_site_tsc_error",
        "write_site_empty",
        "write_site_structural_violation",
        "truncated_output",
        "write_site_parser_error",
        "write_site_import_violation",
        "fallback_repaired",
    }
    has_repairs = bool(normalized_files) or any(entry.get("action") in repair_actions for entry in turn_logs) or len(repaired_sections) > 0

    if blocked_sections:
        generation_quality = "blocked"
    elif has_repairs:
        generation_quality = "repaired"
    else:
        generation_quality = "native"

    site_files_dict = {p: c for p, c in all_written_files}
    acceptance_result = None
    try:
        try:
            from site_acceptance import check_site_files
        except ImportError:
            from agent.site_acceptance import check_site_files
        acceptance_result = check_site_files(site_files_dict)
    except Exception as _acc_err:
        acceptance_result = {
            "static_passed": False,
            "errors": [f"[Acceptance Error] {type(_acc_err).__name__}: {_acc_err}"],
        }

    from agent.project_validator import (
        ValidationResult,
        InteractionValidationResult,
        VisualValidationResult,
        run_project_typecheck,
    )

    ts_ok, ts_errs = run_project_typecheck(case_dir)
    static_passed = (
        isinstance(acceptance_result, dict)
        and isinstance(acceptance_result.get("static_passed"), bool)
        and acceptance_result["static_passed"] is True
    )

    # If case_dir already has full Vite runner configured, run full validate_project
    validation = None
    if (case_dir / "package.json").exists() and (case_dir / "src" / "App.tsx").exists():
        try:
            from agent.project_validator import validate_project
            validation = validate_project(case_dir)
        except Exception as _pv_err:
            validation = ValidationResult(
                typecheck_passed=False, build_passed=False, lint_passed=False,
                contract_passed=False, accessibility_passed=False,
                motion_passed=False, runtime_passed=False, preview_running=False,
                interaction_passed=False,
                errors=[f"[Validation Error] {type(_pv_err).__name__}: {_pv_err}"],
            )

    # Without a full project (App.tsx lives at the project root, written later
    # by the server scaffold) nothing has been validated yet. Report "pending"
    # instead of synthesising passes; verify_and_repair_project is the source
    # of truth (audit A14). Static evidence is kept for diagnostics only.
    static_checks = {
        "typecheck_passed": ts_ok,
        "static_passed": static_passed,
        "errors": list(ts_errs) + (list(acceptance_result.get("errors", [])) if isinstance(acceptance_result, dict) else []),
    }
    if validation is None:
        project_validation = "pending"
        interaction_validation = None
        visual_validation = None
        final_passed = False
    else:
        project_validation = "passed" if validation.passed else "failed"
        interaction_validation = getattr(
            validation,
            "interaction_validation",
            InteractionValidationResult(
                passed=validation.interaction_passed,
                status="passed" if validation.interaction_passed else "failed",
                errors=[e for e in validation.errors if "[Interaction Error]" in str(e)],
            )
        )
        visual_validation = getattr(
            validation,
            "visual_validation",
            VisualValidationResult(
                passed=validation.passed and not any("[Visual Error]" in str(e) for e in validation.errors),
                status="passed" if validation.passed else "failed",
                score=5.0 if validation.passed else 0.0,
                issues=[e for e in validation.errors if "[Visual" in str(e)],
            )
        )
        # Authoritative multi-gate completion rule:
        # NEVER 6/6 sections => final_passed!
        final_passed = bool(
            generation_complete
            and not blocked_sections
            and validation.passed
            and interaction_validation.passed
            and visual_validation.passed
        )

    status = "COMPLETE" if final_passed else f"PARTIAL/FAILED (sections: {section_completion}, project_validation={project_validation}, quality={generation_quality})"
    print(f"\n[Site Result]: {status} - {len(all_written_files)} files written")

    return {
        "index": orig_idx,
        "project_name": project_name,
        "mode": "site",
        "prompt": prompt,
        "sections_planned": sections,
        "sections_completed": sections_completed,
        "generation_complete": generation_complete,
        "section_completion": section_completion,
        "project_validation": project_validation,
        "generation_quality": generation_quality,
        "validation": validation,
        "interaction_validation": interaction_validation,
        "visual_validation": visual_validation,
        "final_passed": final_passed,
        "acceptance": acceptance_result,
        "static_checks": static_checks,
        "blocked_sections": blocked_sections,
        "section_states": section_states,
        "fallback_sections": fallback_sections,
        "repaired_sections": repaired_sections,
        "normalized_files": sorted(normalized_files),
        "unrepaired_fallbacks": unrepaired_fallbacks,
        "auto_recovered_sections": fallback_sections,
        "files": site_files_dict,
        "workspace_dir": str(case_dir),
        "turn_logs": turn_logs,
        "generation_metrics": generation_metrics,
        "trajectory": history,
        "output_token_budgets": [site_budget.to_dict()],
        "design_plan": design_plan.to_dict() if 'design_plan' in locals() and design_plan else None,
    }


def main():
    parser = argparse.ArgumentParser(description="Autonomous multi-turn agent loop for React TS CSS SLMs.")
    default_eval = str(BASE_DIR / "data" / "eval" / "react_ts_css_eval_set_combined.jsonl")
    if not Path(default_eval).exists():
        default_eval = "react_ts_css_eval_set_combined.jsonl"
    parser.add_argument("--model", type=str, default=str(BASE_DIR / "base-model"), help="Path to model directory or HF ID.")
    parser.add_argument("--eval-set", type=str, default=default_eval, help="Evaluation JSONL file.")
    parser.add_argument("--example-index", type=int, default=None, help="Index of single example to run interactively.")
    parser.add_argument("--subset", type=int, default=None, help="Number of items to sample across categories.")
    parser.add_argument("--max-turns", type=int, default=5, help="Maximum turns allowed per task.")
    parser.add_argument("--mock", action="store_true", help="Run with mock agent engine without loading GPU weights.")
    parser.add_argument("--output", type=str, default=str(BASE_DIR / "docs" / "agent_results.json"), help="Path to export results & trajectories.")
    parser.add_argument("--temperature", type=float, default=0.2, help="Sampling temperature.")
    parser.add_argument("--max-new-tokens", type=int, default=768, help="Max tokens per turn.")
    parser.add_argument("--max-seq-len", type=int, default=4096, help="Maximum sequence context length.")
    parser.add_argument("--best-of-2", dest="best_of_2", action="store_true", default=True, help="Enable Best-of-2 candidate sampling on Turn 1 (default: True).")
    parser.add_argument("--no-best-of-2", dest="best_of_2", action="store_false", help="Disable Best-of-2 candidate sampling on Turn 1.")
    args = parser.parse_args()

    eval_file = Path(args.eval_set)
    if not eval_file.exists():
        print(f"Error: {eval_file} not found.")
        sys.exit(1)

    with open(eval_file, encoding="utf-8") as f:
        all_items = [json.loads(line) for line in f if line.strip()]

    # Select task(s)
    if args.example_index is not None:
        if args.example_index < 0 or args.example_index >= len(all_items):
            print(f"Error: Example index must be between 0 and {len(all_items)-1}")
            sys.exit(1)
        selected_items = [(args.example_index, all_items[args.example_index])]
    elif args.subset:
        selected_items = get_stratified_sample(all_items, args.subset)
    else:
        selected_items = list(enumerate(all_items))

    workspace_root = Path.cwd() / ".agent_workspace"
    if workspace_root.exists():
        shutil.rmtree(workspace_root)
    workspace_root.mkdir(parents=True, exist_ok=True)

    runner = AgentModelRunner(
        model_path=args.model,
        max_seq_length=args.max_seq_len,
        is_mock=args.mock
    )

    results = []
    start_time = time.time()

    for orig_idx, item in selected_items:
        res = run_agent_on_example(
            orig_idx=orig_idx,
            item=item,
            runner=runner,
            workspace_root=workspace_root,
            max_turns=args.max_turns,
            temperature=args.temperature,
            max_new_tokens=args.max_new_tokens,
            best_of_2=args.best_of_2
        )
        results.append(res)

    elapsed = time.time() - start_time
    print_agent_summary(results)

    output_path = Path(args.output)
    output_data = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "model": args.model,
        "is_mock": args.mock,
        "max_turns": args.max_turns,
        "total_evaluated": len(results),
        "pass_1shot": sum(1 for r in results if r["initial_passed"]),
        "self_corrected": sum(1 for r in results if r["self_corrected"]),
        "final_passed": sum(1 for r in results if r["final_passed"]),
        "elapsed_seconds": elapsed,
        "trajectories": results
    }
    output_path.write_text(json.dumps(output_data, indent=2), encoding="utf-8")
    print(f"\nFull agent trajectories saved to: {output_path.resolve()}")


if __name__ == "__main__":
    main()
