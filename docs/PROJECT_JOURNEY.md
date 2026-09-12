# Agentic SLM for React, TypeScript & CSS: Full Project Journey & Technical Findings

> **Hardware Constraint**: NVIDIA GeForce RTX 4050 Laptop GPU (6GB VRAM), 24GB DDR5 RAM, Windows OS  
> **Base Model**: `unsloth/Qwen2.5-Coder-3B-Instruct` (4-bit quantized QLoRA via Unsloth)  
> **Core Objective**: Build an autonomous coding agent capable of writing, diagnosing, and self-correcting React + TypeScript + CSS components against live Vitest and TypeScript compilers, achieving state-of-the-art multi-turn pass rates within a 6GB VRAM budget.

---

## Table of Contents
1. [Project Overview & Architecture](#1-project-overview--architecture)
2. [Phase 1 — Foundations: Single-Shot vs. Agentic Loop](#2-phase-1--foundations-single-shot-vs-agentic-loop)
3. [Phase 2 — The Action Space Protocol: Why XML?](#3-phase-2--the-action-space-protocol-why-xml)
4. [What Didn't Work: Failures, Bugs & Root Causes](#4-what-didnt-work-failures-bugs--root-causes)
   - [Bug 1: Unmasked Loss Dilution in SFT](#bug-1-unmasked-loss-dilution-in-sft)
   - [Bug 2: The "Hybrid" Non-Agent Dataset Contamination](#bug-2-the-hybrid-non-agent-dataset-contamination)
   - [Bug 3: Benchmark Eval Set Data Leakage](#bug-3-benchmark-eval-set-data-leakage)
   - [Bug 4: TypeScript Duplicate Declaration Crash (TS2440)](#bug-4-typescript-duplicate-declaration-crash-ts2440)
   - [Bug 5: Placeholder / Dummy Trajectory Harvesting](#bug-5-placeholder--dummy-trajectory-harvesting)
   - [Bug 6: UnboundLocalError Crash on Clean Passes](#bug-6-unboundlocalerror-crash-on-clean-passes)
5. [What Worked: Systematic Fixes & Engineering Solutions](#5-what-worked-systematic-fixes--engineering-solutions)
   - [Fix 1: Response-Only Loss Masking](#fix-1-response-only-loss-masking)
   - [Fix 2: Universal Test Import Sanitization](#fix-2-universal-test-import-sanitization)
   - [Fix 3: Anti-Stuck Escalation & Regression Guarding](#fix-3-anti-stuck-escalation--regression-guarding)
   - [Fix 4: Protocol Guidelines Injection](#fix-4-protocol-guidelines-injection)
   - [Fix 5: Incremental Flushing & Pipeline Resumption](#fix-5-incremental-flushing--pipeline-resumption)
6. [Phase 3 — Expanding the Held-Out STaR Task Bank (50 → 150 Tasks)](#6-phase-3--expanding-the-held-out-star-task-bank-50--150-tasks)
7. [Phase 4 — STaR Rejection Sampling Results](#7-phase-4--star-rejection-sampling-results)
8. [Phase 5 — Clean Training Corpus & SFT Training](#8-phase-5--clean-training-corpus--sft-training)
9. [Phase 6 — Final Benchmark Evaluation & Results](#9-phase-6--final-benchmark-evaluation--results)
   - [Headline Metrics](#headline-metrics)
   - [Per-Category Breakdown](#per-category-breakdown)
   - [Failure Taxonomy (75 Failing Tasks)](#failure-taxonomy-75-failing-tasks)
   - [Failure Pattern Deep-Dive](#failure-pattern-deep-dive)
10. [Phase 7 — Next Steps: DPO Alignment Training](#10-phase-7--next-steps-dpo-alignment-training)
11. [Key Lessons Learned for 3B SLM Fine-Tuning](#11-key-lessons-learned-for-3b-slm-fine-tuning)

---

## 1. Project Overview & Architecture

Modern code generation benchmarks often focus on single-shot output: a model receives an instruction and outputs code. If the code has a missing import, a misnamed prop, or a failing edge case, it receives a score of 0.

Human engineers do not write code this way: they compile, read compiler errors and test assertions, diagnose the root cause, and iterate until all tests pass.

```
       ┌────────────────────────────────────────────────────────┐
       │                       USER PROMPT                      │
       │    "Write a React TypeScript PinInputCode component"   │
       └───────────────────────────┬────────────────────────────┘
                                   │
                                   ▼
       ┌────────────────────────────────────────────────────────┐
       │                   AGENT MODEL (3B)                     │
       │   1. <thought> (Plan & diagnose failure)               │
       │   2. <tool_call name="write_component">                │
       │        <tsx>...</tsx>                                  │
       │        <css>...</css>                                  │
       │      </tool_call>                                      │
       └───────────────────────────┬────────────────────────────┘
                                   │
                                   ▼
       ┌────────────────────────────────────────────────────────┐
       │               AUTOMATED TEST HARNESS                   │
       │   1. TypeScript Compilation (tsc --noEmit)             │
       │   2. Live Vitest + Testing Library Test Runner         │
       └───────────────────────────┬────────────────────────────┘
                                   │
                    ┌──────────────┴──────────────┐
                    │                             │
             [Tests Passed?]               [Tests Failed?]
                    │                             │
                   YES                            NO
                    │                             │
                    ▼                             ▼
       ┌─────────────────────────┐   ┌─────────────────────────┐
       │       <finish>          │   │      <observation>      │
       │  Verified completion!   │   │  Error trace & DOM dump │
       └─────────────────────────┘   └────────────┬────────────┘
                                                  │
                                                  └──► (Next Turn: Self-Correct)
```

---

## 2. Phase 1 — Foundations: Single-Shot vs. Agentic Loop

Initially, the project explored standard 1-shot Alpaca-style fine-tuning (`### Instruction: ... \n### Response: ...`).
- **Base Model**: `unsloth/Qwen2.5-Coder-3B-Instruct`
- **Evaluation Benchmark**: 153 tasks (`react_ts_css_eval_set_combined.jsonl`) spanning forms, navigation, overlays, data tables, and custom hooks.

### The Problem with 1-Shot on 3B Models
A 3B model has high syntax capability but frequently trips on minor edge cases:
- Rendering `props.value` instead of `props.value || ""` (triggering uncontrolled input warnings).
- Forgetting an `aria-label="Digit 1"` attribute expected by `@testing-library/react`.
- Naming a prop `valueChange` when the test passes `onChange`.

In single-shot evaluation, these minor issues resulted in a **failed task**. Giving the model an interactive test loop with compiler feedback was necessary to unlock high pass rates.

---

## 3. Phase 2 — The Action Space Protocol: Why XML?

Standard function calling (JSON-based schemas like OpenAI Tools) failed consistently on 3B models:
- **JSON Escaping Hell**: Escaping double quotes, template literals (`` `${x}` ``), and multi-line strings inside JSON blocks caused frequent JSON parse crashes.
- **Context Waste**: JSON schema wrappers added 150+ tokens per turn of overhead.

### The XML Solution (`agent_protocol.py`)
We designed an XML tag-based action space:
```xml
<thought>
Explain reasoning, diagnose test failures, or formulate a plan.
</thought>
<tool_call name="write_component">
<tsx>
// Clean React + TypeScript code (no escaping needed)
</tsx>
<css>
/* Optional CSS / CSS module */
</css>
</tool_call>
```
When tests pass:
```xml
<finish>
Brief summary of the verified solution.
</finish>
```
The testing environment returns feedback via:
```xml
<observation status="failed">
[TSC]: Passed (0 errors)
[Vitest Test Failure]:
  × renders the correct number of digit inputs
    → Expected 4 inputs, found 0
</observation>
```

---

## 4. What Didn't Work: Failures, Bugs & Root Causes

During development, several critical failure modes were diagnosed and resolved:

### Bug 1: Unmasked Loss Dilution in SFT
- **Symptom**: The model was slow to learn self-correction logic and would often repeat test-runner phrases.
- **Root Cause**: `train_agent.py` was calling `SFTTrainer(dataset_text_field="text")` without token masking. Loss was computed across the entire conversation:
  - ~600 tokens of static `AGENT_SYSTEM_PROMPT`
  - User prompt
  - Large `<observation>` test output blocks (Vitest error stacks)
- **Impact**: On a 3B model with a small trajectory dataset, 70%+ of the gradient steps were wasted memorizing deterministic test-runner strings rather than learning code synthesis and error diagnosis.

---

### Bug 2: The "Hybrid" Non-Agent Dataset Contamination
- **Symptom**: When trained on `train_trajectories_hybrid.jsonl` (657 examples), the agent frequently output code directly inside `<finish>` without ever calling `write_component`.
- **Root Cause**: Upon inspection, 350 out of 657 examples (53.3%) in `train_trajectories_hybrid.jsonl` were legacy 3-message examples (`hybrid_ts_*`):
  ```xml
  <thought>
  I will write the TypeScript solution.
  </thought>
  <finish>
  ```typescript
  import path from "path";
  export default ...
  ```
  </finish>
  ```
- **Impact**: The model was rewarded for bypassing the test harness entirely. It treated `<finish>` as a markdown code block, directly violating the agentic tool-use protocol.

---

### Bug 3: Benchmark Eval Set Data Leakage
- **Symptom**: Suspiciously high 1-shot pass rates during initial evaluation.
- **Root Cause**: 164 of the 307 valid agent trajectories in `train_trajectories_hybrid.jsonl` had prompts identical to the 153 benchmark tasks in `react_ts_css_eval_set_combined.jsonl`.
- **Impact**: The evaluation was measuring memorization rather than true out-of-distribution reasoning and self-correction.

---

### Bug 4: TypeScript Duplicate Declaration Crash (`TS2440`)
- **Symptom**: During early STaR generation runs on `star_task_bank.jsonl`, **100% of tasks failed on Turn 1** with compiler errors like:
  ```
  TS2440: Import declaration conflicts with local declaration of 'PinInputCode'.
  Cannot redeclare block-scoped variable 'PinInputCode'.
  ```
- **Root Cause**:
  - `eval_custom.py` automatically generated component bindings:
    ```typescript
    import * as __Mod from './Component';
    const PinInputCode = (__Mod as any).PinInputCode ?? (__Mod as any).default;
    ```
  - Meanwhile, the test code written in `star_task_bank.jsonl` had top-level imports:
    ```typescript
    import { PinInputCode } from './Component';
    ```
  - When concatenated into `Component.test.tsx`, TypeScript crashed before running Vitest.
  - Because the model can only write `Component.tsx` and cannot edit `Component.test.tsx`, it became stuck in an unresolvable loop.

---

### Bug 5: Placeholder / Dummy Trajectory Harvesting
- **Symptom**: Harvested STaR files had tiny file sizes and missing code.
- **Root Cause**: `generate_star_trajectories.py` had placeholder rollout logic:
  ```python
  # Old code:
  history.append({"role": "assistant", "content": "// Verified implementation"})
  ```
  It was discarding the agent's actual generated TSX, CSS, and intermediate repair turns.

---

### Bug 6: `UnboundLocalError` Crash on Clean Passes
- **Symptom**: In the middle of an overnight 150-task STaR run, the pipeline crashed at Task #12 (`ProgressStepBar`) with:
  ```
  UnboundLocalError: cannot access local variable 'regress_warn' where it is not associated with a value
  ```
- **Root Cause**: In `agent_loop.py`, `regress_warn` was defined only inside the test-failure `else:` block:
  ```python
  if passed:
      final_passed = True
  else:
      regress_warn = "..."
  # Later:
  if regress_warn and "</observation>" in obs: # <-- Crashed when passed=True!
  ```

---

## 5. What Worked: Systematic Fixes & Engineering Solutions

### Fix 1: Response-Only Loss Masking
In `train_agent.py`, we integrated Unsloth's response-only loss masking:
```python
from unsloth.chat_templates import train_on_responses_only

trainer = train_on_responses_only(
    trainer,
    instruction_part="<|im_start|>user\n",
    response_part="<|im_start|>assistant\n",
)
```
- **Result**: Tokens in the system prompt, user prompt, and `<observation>` blocks are assigned a label of `-100` (ignored by cross-entropy loss).
- **Benefit**: 100% of the model's limited 3B capacity is dedicated to generating high-quality `<thought>`, `<tool_call>`, and `<finish>` tokens.

---

### Fix 2: Universal Test Import Sanitization
In `eval_custom.py`, we introduced `strip_test_imports()`:
```python
def strip_test_imports(code: str) -> str:
    # 1. Strip import ... from './Component', 'vitest', '@testing-library/*', 'react'
    import_from_pattern = r'import\s+[\s\S]*?from\s*[\'"][^\'"]+[\'"];?'
    cleaned = re.sub(import_from_pattern, repl_from, code)
    # 2. Strip side-effect imports like import '@testing-library/jest-dom';
    side_pattern = r'import\s+[\'"][^\'"]+[\'"];?'
    return re.sub(side_pattern, repl_side, cleaned).strip()
```
And updated the test harness template to auto-inject standard bindings and React hooks:
```typescript
import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import { render, screen, fireEvent, act, renderHook, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi, describe, it, test, expect, beforeEach, afterEach } from 'vitest';
import '@testing-library/jest-dom';

import * as __Mod from './Component';

// Injected component bindings
const PinInputCode = (__Mod as any).PinInputCode ?? (__Mod as any).default;

// Sanitized test cases start here cleanly
describe('PinInputCode Component', () => { ... });
```
- **Result**: Eliminated `TS2440` duplicate declaration crashes across all test suites.

---

### Fix 3: Anti-Stuck Escalation & Regression Guarding
In `agent_loop.py`, we implemented dynamic sampling intervention:
- If the model generates identical TSX or repeats the exact same test failure:
  1. `stuck_turns` increments.
  2. Temperature escalates (`0.20` → `0.55` → `0.90`).
  3. Repetition penalty escalates (`1.05` → `1.15` → `1.30`).
  4. An explicit intervention note is injected into the next observation:
     `"[ANTI-STUCK INTERVENTION]: Your previous attempt repeated the same failure. Alter your implementation logic."`
- When code or error state changes, sampling immediately resets to base values.

---

### Fix 4: Protocol Guidelines Injection
In both `agent_protocol.py` and `agent_loop.py`, we codified three recurring UI component patterns:
1. **Prop Fallback Aliasing**:
   `const trendVal = props.trend ?? props.valueChange ?? props.change;`
   `const initial = props.initialValues ?? props.initialState ?? props.defaultValues ?? {};`
2. **Minimal Clean Logging Rule**:
   When asked to log an action (e.g. `dispatchLogged`), output `console.log(action)` with no prepended label strings.
3. **Imperative DOM Dynamic Container Pattern**:
   Imperative hooks (`useConfirm`, `useToast`) must dynamically create and mount a container `<div>` to `document.body` if no portal root is provided in JSX.

---

### Fix 5: Incremental Flushing & Pipeline Resumption
In `generate_star_trajectories.py`:
- **Immediate Disk Flush**: Every passing rollout is appended and flushed to `star_trajectories.jsonl` immediately. If a run is interrupted, no passing rollouts are lost.
- **Resume Flag (`--resume`)**: The script reads existing task IDs from `star_trajectories.jsonl` and automatically skips completed tasks.
- **Fixed `regress_warn`**: Initialized `regress_warn = ""` alongside `anti_stuck_note = ""` to prevent runtime variable errors.

---

## 6. Phase 3 — Expanding the Held-Out STaR Task Bank (50 → 150 Tasks)

To harvest genuine self-correction trajectories without test leakage, we constructed [`star_task_bank.jsonl`](file:///c:/Users/AYUSH/Documents/slm/star_task_bank.jsonl), expanded from 50 to **150 rigorous component tasks**:

| Range | Module File | Categories Covered | Example Components |
| :--- | :--- | :--- | :--- |
| **1–50** | `build_star_bank.py` | Forms, text inputs, navigation, overlays | `PinInputCode`, `NumericStepperInput`, `SearchFilterBar`, `RangeDualSlider` |
| **51–75** | `star_bank_batch_51_75.py` | Specialized inputs, formatters, gauges | `CurrencyAmountInput`, `CreditCardExpiryInput`, `PasswordEntropyGauge`, `SlugUrlInput` |
| **76–100** | `star_bank_batch_76_100.py` | Navigation, menus, data display, FABs | `FloatingActionButtonGroup`, `NestedTreeView`, `SortableDataColumnHeader`, `StatTrendCard` |
| **101–125** | `star_bank_batch_101_125.py` | Feedback, dialogs, modals, alerts | `StatusPillIndicator`, `InputPromptModal`, `SessionTimeoutWarning`, `FeedbackRatingDialog` |
| **126–150** | `star_bank_batch_126_150.py` | Custom React hooks & complex UI | `useDebounceValue`, `useLocalStorageState`, `useClickAwayListener`, `useWindowDimensions` |

### Disjointness & Integrity Verification
- **Overlap with 153 Benchmark Eval Tasks**: **0 overlapping symbols, 0 overlapping prompts (100% disjoint)**.
- **Duplicate IDs / Symbols**: **0 duplicates** (contiguous `star_001` to `star_150`).
- **Bracket / Syntax Balance**: **0 mismatches** across all 150 test suites.
- **Import Sanitization**: All 150 tasks use pre-sanitized test codes.

---

## 7. Phase 4 — STaR Rejection Sampling Results

Using `my-react-agent-lora` on the RTX 4050 GPU, we executed the full 150-task STaR pipeline:
```powershell
python -u generate_star_trajectories.py --model my-react-agent-lora --tasks 150
```

### Harvest Results Summary
- **Total Held-Out Tasks Evaluated**: **150 / 150**
- **Total Verified Passing Trajectories**: **102**
- **Overall Pass Rate**: **68.0%** (target was 80–110; 102 hit the exact sweet spot)
- **Multi-Turn Self-Correction Episodes**: **35 trajectories** (>5 dialogue turns)

### Notable Multi-Turn Self-Corrections Harvested
| Task Symbol | Total Messages | Turn Corrected | Failure Diagnosed & Repaired |
| :--- | :--- | :--- | :--- |
| `PinInputCode` | 13 | Turn 4 | Missing accessible `aria-label="Digit X"` on individual inputs |
| `PillMultiSelector` | 9 | Turn 3 | Button accessible name computation mismatch on removable badges |
| `DropdownBreadcrumb` | 9 | Turn 3 | Collapsed dropdown items missing proper role and keyboard toggle |
| `CommandKPalette` | 9 | Turn 3 | Keyboard shortcut listener missing event cleanup and focus trap |
| `InfiniteScrollTrigger`| 7 | Turn 2 | Missing `role="status"` element containing loading message |
| `DraggableListItem` | 7 | Turn 2 | Move up/down buttons lacking associated label bindings |
| `SplitButtonDropdown` | 7 | Turn 2 | Primary action button firing dropdown menu toggle inadvertently |
| `NestedTreeView` | 7 | Turn 2 | Child tree items missing recursive indentation and expand/collapse state |
| `RatingBreakdownBars` | 7 | Turn 2 | Progress bar aria attributes (`aria-valuenow`, `aria-valuemax`) missing |
| `NumericStepperInput` | 7 | Turn 2 | Clamp logic failing on min/max bounds when typing raw text |

---

## 8. Phase 5 — Clean Training Corpus & SFT Training

### Dataset Assembly via `build_clean_dataset()`
To prevent the model from unlearning earlier capabilities while eliminating leaked and corrupted examples, we ran `build_clean_dataset()` across both sources:

```
[Legacy train_trajectories_hybrid.jsonl (657)]  +  [Fresh star_trajectories.jsonl (102)]
                                     │
                                     ▼
                       build_clean_dataset() Filter
         ├── Rejects 350 non-agent examples (code in <finish>)
         ├── Rejects 164 eval-set duplicates (prevents benchmark leakage)
         └── Deduplicates 99 identical prompts
                                     │
                                     ▼
             train_trajectories_agentic.jsonl (146 Clean Trajectories)
```

### Final Dataset Verification
- **Total Trajectories**: **146**
- **Protocol Compliance**: **100%** (all have `<thought>`, `<tool_call name="write_component">`, live test observations, and end with `<finish>`).
- **Eval Set Leakage**: **0 examples** (100% held-out).

### Completed SFT Training Run (Epochs: 3, LR: 1e-4)
With `train_trajectories_agentic.jsonl` assembled (146 trajectories), training was executed on the RTX 4050 GPU using response-only loss masking:
```powershell
python train_agent.py --epochs 3 --learning-rate 1e-4
```
- **Base Model**: `./base-model` (`unsloth/Qwen2.5-Coder-3B-Instruct` 4-bit)
- **LoRA Targets**: `q_proj`, `k_proj`, `v_proj`, `o_proj`, `gate_proj`, `up_proj`, `down_proj` (rank=16, alpha=16, dropout=0.05)
- **Total Steps**: 96 steps across 3 epochs (batch size=1, gradient accumulation=4)
- **Loss Masking**: `train_on_responses_only` active (loss computed solely on assistant turns)
- **Convergence Metrics**:
  - Training loss dropped from **`0.9757`** (Step 5) → **`0.2930`** (Step 96).
  - Validation loss dropped steadily: **`0.5053`** (Step 25) → **`0.3848`** (Step 50) → **`0.3538`** (Step 75) → **`0.3503`** (Step 96, Best Metric).
- **Saved Model**: The best checkpoint (`checkpoint-96`, eval loss = 0.3503) was automatically saved to [`my-react-agent-lora`](file:///c:/Users/AYUSH/Documents/slm/my-react-agent-lora).
- **Output Artifact**: Ready for full evaluation on the held-out 153 benchmark tasks via `agent_loop.py`.

---

## 9. Phase 6 — Final Benchmark Evaluation & Results

The trained `my-react-agent-lora` was evaluated on the full held-out 153-task benchmark (`react_ts_css_eval_set_combined.jsonl`) via `agent_loop.py`, running for **16.17 hours** on the RTX 4050 GPU.

```powershell
python agent_loop.py --model my-react-agent-lora --eval-set react_ts_css_eval_set_combined.jsonl
```

### Headline Metrics

| Metric | Count | Rate |
| :--- | :--- | :--- |
| **1-Shot Pass Rate (Turn 1)** | 60 / 153 | **39.2%** |
| **Self-Corrected (Turn 2+)** | +18 / 153 | **+11.8%** |
| **Final Agentic Pass Rate** | **78 / 153** | **51.0%** |
| Failed (all 5 turns exhausted) | 75 / 153 | 49.0% |
| Average Turns Used (passing tasks) | — | 1.31 turns |

**Self-correction added +11.8 percentage points** on top of the base 1-shot rate — confirming that the agentic loop with live test feedback provides meaningful gains beyond a single-turn generation.

### Per-Category Breakdown

| Check Category | Description | Pass | 1-Shot | Self-Corrected |
| :--- | :--- | :--- | :--- | :--- |
| `tsc_and_render` | TSC + render sanity | **30/42 (71%)** | 24 | 6 |
| `tsc_render_a11y` | TSC + render + accessibility | **3/4 (75%)** | 2 | 1 |
| `tsc_render_interact` | TSC + render + user interactions | 21/58 **(36%)** | 14 | 7 |
| `tsc_only` | TypeScript compilation only | 24/49 **(49%)** | 20 | 4 |

The model is strongest on static structure + render tasks (71%), and weakest on interactive UI tests (36%) that require correct state transitions, DOM event handling, and exact ARIA attribute targeting.

### Turns Distribution (Passed Tasks Only)

| Turns Used | Tasks |
| :--- | :--- |
| 1 turn (1-shot) | 60 |
| 2 turns | 12 |
| 3 turns | 5 |
| 4 turns | 1 |

### Failure Taxonomy (75 Failing Tasks)

After analyzing the final `<observation>` from each exhausted-turn failure:

| Root Cause Cluster | Count | Pct |
| :--- | :--- | :--- |
| **TS: Unknown TSC failure** (complex multi-error TSC) | 33 | 44.0% |
| **TS: Undeclared identifier** (TS2304 — variable never declared) | 10 | 13.3% |
| **Test: Assertion failed** (wrong value / behavior) | 9 | 12.0% |
| **TS: Other parse/syntax** (TS1005, TS1109, TS1700, TS1701, etc.) | 8 | 10.7% |
| **Test: TypeError at runtime** (bad method call / null deref) | 4 | 5.3% |
| **Test: Element not found in DOM** (missing aria / testid) | 3 | 4.0% |
| **TS: Property does not exist** (TS2339) | 2 | 2.7% |
| Other isolated TS errors (TS2536, TS2315, TS2731, TS2345, etc.) | 6 | 8.0% |

### Failure Pattern Deep-Dive

**1. TS Unknown TSC Failure (33 tasks — biggest cluster)**
Dominant in `tsc_render_interact` (20/33) and `tsc_and_render` (7/33). The model generates syntactically plausible code that trips on multi-layered type errors it cannot resolve by turn 5. These include complex generic constraints on `DataTable`, `KanbanBoard`, `FormProvider`, and `FormWizard` where the component's internal state generics don't satisfy the test harness's type assertions.

**2. TS: Undeclared Identifier (10 tasks)**
The model references identifiers that were never declared in the same scope. Examples:
- `useQueryParams` references `parsedUrl`, `queryParamsToString`, `queryString` — none declared.
- `useCart` references cart state management variables from a non-existent import.
- `useConfirm` references `createPortal` without importing it.
Strategy: Use 3rd-party import rewriting to force model into self-contained code.

**3. Test Assertion Failures (9 tasks)**
The model's logic is close but produces wrong values. Examples:
- `useMediaQuery` returns `false` before `matchMedia` mock fires.
- `Slider` computes percentage incorrectly (off-by-one on boundary).
- `useIsMounted` returns stale ref value due to missing cleanup.
These are ideal targets for DPO pairs — the failing code vs. a corrected version.

**4. TS Parse/Syntax errors (8 tasks)**
TS1005 ("`;` expected") and TS1109 ("Expression expected") — the model generates truncated or malformed output, especially on complex hooks (`useUndo`, `useCart`, `useOnClickOutside`) where the code body is long enough to hit the `max_new_tokens=768` ceiling and gets cut off mid-statement.

---

## 10. Phase 7 — Next Steps: DPO Alignment Training

The benchmark run automatically harvested **22 verified DPO pairs** in [`dpo_pairs_verified.jsonl`](file:///c:/Users/AYUSH/Documents/slm/dpo_pairs_verified.jsonl). Each pair captures a task where:
- **Rejected**: Turn 1 output that failed TSC or Vitest.
- **Chosen**: A later-turn corrected output that passed all tests.

### DPO Training Plan

```
[agent_results.json (153 trajectories)]
         |
         v
  extract_dpo_pairs.py
  -- Filter self-corrected tasks (initial_passed=False, final_passed=True)
  -- Format: prompt + rejected_completion + chosen_completion
         |
         v
  [dpo_pairs_full.jsonl]  (target: 78 pairs from 18 self-corrected + 60 1-shot failures)
         |
         v
  python train_dpo.py --epochs 1 --beta 0.1
  -- DPO objective: increase log P(chosen) - log P(rejected)
  -- LoRA fine-tune on top of existing my-react-agent-lora checkpoint
         |
         v
  [my-react-agent-lora-dpo/]
         |
         v
  python agent_loop.py --model my-react-agent-lora-dpo ...
  -- Target: push Final Agentic Pass Rate from 51.0% -> 60%+
```

### Priority Targets for Targeted SFT (Beyond DPO)

Based on the failure taxonomy, the highest-leverage targeted data additions are:

| Priority | Error Type | Tasks Affected | Data Strategy |
| :--- | :--- | :--- | :--- |
| **P0** | TS: Undeclared identifier | 10 tasks | Add 20+ STaR examples showing correct self-contained hook implementations |
| **P1** | TS: Parse/Syntax truncation | 8 tasks | Increase `max_new_tokens` to 1024; add examples of complete long hooks |
| **P2** | Test: Assertion failures | 9 tasks | Harvest DPO pairs from agent_results.json self-corrections |
| **P3** | `tsc_render_interact` failures | 21 tasks | Curate interact-heavy STaR examples (DataTable, FormWizard, KanbanBoard variants) |

---

## 11. Key Lessons Learned for 3B SLM Fine-Tuning


| Area | What Failed | What Succeeded |
| :--- | :--- | :--- |
| **Action Protocol** | JSON tool schemas (parse errors, escaping bugs). | Plain XML tags (`<thought>`, `<tool_call>`, `<finish>`). |
| **Loss Computation** | Unmasked loss across system prompts and observations. | `train_on_responses_only`: loss computed solely on assistant turns. |
| **Data Cleanliness** | Including non-agent prompt-response pairs in agentic corpus. | Strict trajectory validation: must call `write_component` and pass tests before `<finish>`. |
| **Eval Integrity** | Training on prompts from the eval benchmark. | Complete disjointness between training task banks and benchmark tasks. |
| **Test Harness** | Allowing tests to declare arbitrary top-level imports. | Centralized test import stripping (`strip_test_imports`) with global bindings injection. |
| **Sampling Strategy** | Fixed low temperature when model gets stuck in repetitive errors. | Dynamic Anti-Stuck escalation (raising temp & rep_penalty on repeated errors). |
| **Pipeline Reliability**| In-memory trajectory accumulation until script end. | Immediate incremental disk flushing + automatic `--resume` support. |

---
*Document created autonomously by Antigravity IDE.*
