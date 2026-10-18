# SiteAgent Motion Training & Curriculum Runbook (v1.0)

> **Target Architecture**: Qwen3-4B QLoRA SFT (R16 / Alpha 32)
> **Curriculum Version**: `siteagent_motion_v1`
> **Artifacts**: `data/siteagent_motion_sft_v1.jsonl`, `data/siteagent_motion_eval_v1.jsonl`, `data/siteagent_motion_dataset_manifest.json`

---

## 1. Executive Summary & Curriculum Scope

Modern high-converting web applications demand dynamic, responsive visual pacing: reveal-on-scroll, restrained parallax, cinematic sticky narratives, horizontal progress tracks, and tactile micro-interactions. However, smaller language models (SLMs) frequently exhibit catastrophic motion failures:
1. **Per-scroll React re-renders**: Calling `setState` inside unthrottled scroll listeners.
2. **Scroll-jacking & input hijacking**: Calling `wheel.preventDefault()` or `touchmove.preventDefault()`, breaking browser scrolling and trackpad navigation.
3. **Ghost observers**: Leaving `IntersectionObserver` or `requestAnimationFrame` loops active on unmount.
4. **Permanent hiding**: Starting elements at `opacity: 0` before JavaScript hydrates, making content invisible without JS or under SSR.
5. **Accessibility annihilation**: Splitting headings into separate `<span>` elements announced disjointedly by screen readers.
6. **Reduced-motion omission**: Forgetting `prefers-reduced-motion: reduce` CSS media queries.
7. **Mobile blowout**: Horizontal scroll sections overflowing the 375px viewport on mobile handsets.

The **SiteAgent Motion Curriculum** directly resolves these failure modes by providing supervised fine-tuning (SFT) trajectories that follow strict browser-native standards, paired with an immutable held-out evaluation benchmark and automated Playwright runtime verification.

---

## 2. Dataset Architecture & File Manifest

The motion curriculum consists of three coordinated files with cryptographic integrity maintained in `siteagent_motion_dataset_manifest.json`:

| File | Type | Records | Description |
|---|---|:---:|---|
| `data/siteagent_motion_sft_v1.jsonl` | Supervised Fine-Tuning | 36 | 30 gold trajectories across 6 families + 6 repair multi-turn trajectories |
| `data/siteagent_motion_eval_v1.jsonl` | Held-Out Evaluation | 12 | 2 family-disjoint tasks per motion family across 12 unseen brand domains |
| `data/siteagent_motion_dataset_manifest.json` | Dataset Manifest | 1 | SHA-256 checksums, token budgets, and hyperparameter policies |

### 2.1 The Six Motion Families

```
                               ┌───────────────────────────────┐
                               │     Motion Curriculum v1      │
                               └──────────────┬────────────────┘
             ┌────────────────┬───────────────┼───────────────┬────────────────┐
             ▼                ▼               ▼               ▼                ▼
     ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
     │Scroll Reveal │ │   Parallax   │ │ Horizontal   │ │ Sticky Story │ │ Text Reveal  │
     │(Intersection │ │  (RAF/Custom │ │   (Sticky +  │ │ (CSS Sticky  │ │(Accessible H1│
     │  Observer)   │ │  Properties) │ │  Snap Mobile)│ │ + Observer)  │ │ + Split Spans│
     └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘
                                              │
                                              ▼
                                     ┌───────────────────┐
                                     │Micro-Interactions │
                                     │(Hover/Focus/Active│
                                     │  <250ms feedback) │
                                     └───────────────────┘
```

1. **Scroll Reveal** (`motion_scroll_reveal`): Elements gracefully enter the viewport with staggered opacity/transform transitions.
   - *Contract*: `IntersectionObserver` with `threshold` and `rootMargin`, unobserving targets after reveal; initial content readable without JS; `prefers-reduced-motion` override.
2. **Parallax** (`motion_parallax`): Decorative visuals translate slower than document scroll.
   - *Contract*: Passive scroll listener driving `requestAnimationFrame`; CSS custom property `--parallax-y`; bounded translations; no React `setState` per tick; full listener/RAF cleanup; disabled on mobile and reduced motion.
3. **Horizontal Scroll** (`motion_horizontal_scroll`): Vertical document scrolling progresses a horizontal track.
   - *Contract*: Desktop sticky track translated via `translate3d`; zero wheel/touch hijacking; mobile fallback to native `overflow-x: auto` with `scroll-snap-type: x mandatory`.
4. **Sticky Storytelling** (`motion_sticky_story`): Sticky visual pane paired with advancing narrative chapters.
   - *Contract*: Pure CSS `position: sticky; top: ...`; active chapter highlighting via `IntersectionObserver`; compatible overflow ancestor hierarchy; standard vertical stacking on mobile handsets.
5. **Text Reveal** (`motion_text_reveal`): Phased word appearance on scroll.
   - *Contract*: Unified accessible title on `<h1 aria-label="...">`; decorative word spans marked `aria-hidden="true"`; instant display under `prefers-reduced-motion` and no-JS.
6. **Micro-Interactions** (`motion_micro_interactions`): Tactical tactile button and card responses.
   - *Contract*: Strict parity between `:hover` and `:focus-visible` / `:focus-within`; tactile `:active` state; `aria-pressed` / `aria-selected` toggles; transitions under 250ms; zero layout shift.

### 2.2 SFT Composition (36 Trajectories)

- **30 Gold Trajectories**: 5 brand archetypes per motion family:
  - `atelier`: Atelier North (minimalist architectural design studio)
  - `saas`: Vector Cloud (enterprise telemetry & distributed cloud)
  - `product`: Arc Audio (audiophile hardware & acoustic design)
  - `editorial`: Field Notes (technical monograph & research publication)
  - `portfolio`: Mira Studio (creative agency & digital design practice)
- **6 Multi-Turn Repair Trajectories**:
  1. `motion_repair_scroll_reveal_01`: Fixes permanent zero-opacity and unclosed observer leak.
  2. `motion_repair_parallax_02`: Eliminates per-scroll `setState()` calls and non-passive listeners.
  3. `motion_repair_horizontal_scroll_03`: Removes `wheel.preventDefault()` hijacking and restores mobile scroll-snap.
  4. `motion_repair_sticky_story_04`: Resolves invalid ancestor `overflow: hidden` that breaks CSS sticky positioning.
  5. `motion_repair_text_reveal_05`: Replaces screen-reader fragmented span announcements with unified `aria-label`.
  6. `motion_repair_micro_interactions_06`: Adds keyboard focus parity, eliminates layout property animation, and preserves `aria-pressed`.

### 2.3 Held-Out Evaluation Set (12 Tasks)

The held-out evaluation set (`siteagent_motion_eval_v1.jsonl`) contains 12 family-disjoint evaluation prompts (2 per motion family) across 12 unseen brand domains:
- *Scroll Reveal*: Lumina Photonics (Laser Metrology) & Kanso Living (Minimalist Furniture)
- *Parallax*: Strata Geosystems (Subsurface Geology) & Vesper Robotics (Oceanic Drones)
- *Horizontal Scroll*: Chronos Timepieces (Horlogerie) & Helix Biotech (Cell Therapy)
- *Sticky Story*: Forge Composites (Aerospace Materials) & Nomad Botanical (Phytotherapy)
- *Text Reveal*: Aether Mobility (Autonomous Aviation) & Solstice Glassworks (Photovoltaic Glass)
- *Micro-Interactions*: Pulse Metrics (Cloud Telemetry) & Aethel Foundry (Type Design)

**Disjointness Guarantee**: Maximum token-level Jaccard similarity to any SFT prompt is **0.2466** (strictly below the 0.40 ceiling), with zero brand name or archetype collision.

---

## 3. Data Mixing Strategy & Curriculum Rebalancing

> [!IMPORTANT]
> **Never fine-tune exclusively on motion trajectories.** Training only on motion data causes catastrophic forgetting of generic React component structure, form handling, 3D Canvas integration, and pure utility layouts.

### 3.1 Recommended Training Mixture (10% to 15% Motion)

When preparing the training dataset for a model training run, mix the motion trajectories into the core replay dataset at a controlled ratio of 10% to 15% motion data:

```text
┌─────────────────────────────────────────────────────────────┐
│                Full Training Blend (100%)                   │
├───────────────────────────────────────┬─────────┬───────────┤
│ Category                              │ Target  │ Purpose   │
├───────────────────────────────────────┼─────────┼───────────┤
│ 1. Core React/TS/CSS Components       │ 45%     │ Baseline  │
│ 2. Interactive & Stateful Flows       │ 20%     │ Logic     │
│ 3. Professional Motion Curriculum     │ 15%     │ Dynamics  │
│ 4. Full-Site Multi-Section Layouts    │ 10%     │ Scaffolding│
│ 5. Accessibility & Semantics Repairs  │ 5%      │ A11y      │
│ 6. Three.js / WebGL / R3F Canvases    │ 5%      │ 3D Visual │
└───────────────────────────────────────┴─────────┴───────────┘
```

### 3.2 Anti-Template Collapse & Layout Balancing

Ensure the full training blend does not over-represent any single visual layout. The diversity evaluator tracks layout distribution:
- **Split Hero**: 20%–25%
- **Editorial Asymmetric Hero**: 15%–20%
- **Full-Bleed / Immersive Visual Hero**: 15%–20%
- **Bento Hero**: 15%–20%
- **Product-Stage Hero**: 10%–15%
- **Restrained Centered Hero**: $\le 15\%$

No archetype should exceed 30% of the training or promotion batch.

---

## 4. Tokenizer Preflight & Context Length Decision

### 4.1 Tokenizer Preflight Verification

Before launching training, execute the preflight checker to ensure the tokenizer and prompt format match the expected production contract:
1. **Authentic Base Model**: Verify that `base-model/config.json` is genuine Qwen3-4B (attention heads, KV heads, layer dimensions) and matches `base-model/manifest.json`.
2. **Thought Target Rejection**: Preflight must confirm zero occurrences of `<think>` or `<thought>` in the training targets. Assistant responses must emit only:
   ```xml
   <tool_call name="write_site">
   <file path="src/components/Name.tsx">complete component</file>
   <file path="src/components/Name.css">complete stylesheet</file>
   </tool_call>
   ```
3. **No Unverified Packages**: Confirm that no trajectory imports unverified packages (`gsap`, `framer-motion`, `@studio-freight/lenis`). Native browser APIs (`IntersectionObserver`, `requestAnimationFrame`, CSS transitions, CSS variables) must be used.

### 4.2 Context Length Decision: 6,144 vs 8,192 Tokens

- **Motion Sections (Standalone)**: Mean token count is ~1,350 tokens (component TSX + stylesheet CSS). 6,144 tokens provides ample headroom for standalone sections, interactive forms, and multi-turn repairs.
- **Full Multi-Section Sites with Motion**: A complete multi-section site (Header + Hero with Text Reveal + Features + Sticky Storytelling + Micro-interaction Cards + Footer) reaches 4,500–6,800 tokens.
- **Decision Rule**:
  - For single-component / section training: Set `max_seq_length = 6144`.
  - For full-site assembly training: Set `max_seq_length = 8192` (using flash-attention-2 and gradient checkpointing on 24GB+ GPU).

---

## 5. QLoRA Training Configuration & Hyperparameters

```python
# Canonical training hyperparameters for Qwen3-4B QLoRA
LORA_CONFIG = {
    "r": 16,
    "lora_alpha": 32,
    "lora_dropout": 0.05,
    "bias": "none",
    "target_modules": [
        "q_proj",
        "k_proj",
        "v_proj",
        "o_proj",
        "gate_proj",
        "up_proj",
        "down_proj",
    ],
    "task_type": "CAUSAL_LM",
}

TRAINING_ARGS = {
    "per_device_train_batch_size": 1,
    "gradient_accumulation_steps": 8,  # Effective batch size = 8
    "learning_rate": 2e-4,
    "lr_scheduler_type": "cosine",
    "warmup_ratio": 0.03,
    "weight_decay": 0.01,
    "max_grad_norm": 1.0,
    "fp16": False,
    "bf16": True,
    "optim": "adamw_bnb_8bit",
    "gradient_checkpointing": True,
    "logging_steps": 10,
    "save_strategy": "epoch",
}
```

### 5.1 Response-Only Loss Masking

Loss must be computed **strictly on assistant tokens**:
- The prompt template masks all system messages and user turns with label `-100`.
- The cross-entropy loss begins at `<tool_call name="write_site">` and terminates at `</tool_call>`.
- This ensures the model learns generation syntax and code correctness without penalizing variations in prompt wording.

---

## 6. Promotion Gates & Verification Pipeline

Before any fine-tuned adapter is promoted to production, it must clear all eight immutable promotion gates:

| Gate | Criterion | Threshold | Enforcement Tool |
|:---:|---|:---:|---|
| **1** | TypeScript Typecheck | 100% pass | `tsc --noEmit` |
| **2** | Production Vite Build | 100% pass | `vite build` |
| **3** | Single-Action Tool Contract | 100% pass | XML parser (`tool_call name="write_site"`) |
| **4** | Native Motion Policy | 100% pass | `test_motion_library_policy.py` (zero unverified dependencies) |
| **5** | Behavioral Motion Benchmark | $\ge 90.0\%$ | `evaluation/motion_benchmark.py` (Playwright Chromium) |
| **6** | Runtime Performance & Health | $\ge 95.0\%$ | Page errors = 0, Console errors = 0, CLS $\le 0.05$ |
| **7** | Accessibility & Reduced Motion | 100% pass | `prefers-reduced-motion` override verified in browser |
| **8** | Zero Scroll-Jacking | 100% pass | Zero calls to `wheel.preventDefault()` / `touchmove.preventDefault()` |

---

## 7. Step-by-Step Training & Validation Walkthrough

### Step 1: Pre-Training Preflight Checks
Verify the manifest checksums and dataset integrity:
```bash
python -m pytest tests/test_motion_training_data.py -v
```

### Step 2: Mix Dataset
Assemble the composite training batch by mixing `data/siteagent_motion_sft_v1.jsonl` (15%) with the replay pool:
```bash
python scripts/mix_training_data.py --motion-ratio 0.15 --output data/composite_training_v1.jsonl
```

### Step 3: Run QLoRA Training
Launch the fine-tuning run:
```bash
python training/train_qwen3_sft.py \
  --base-model base-model \
  --train-file data/composite_training_v1.jsonl \
  --output-dir models/qwen3-siteagent-motion-r16 \
  --max-seq-length 6144 \
  --epochs 3
```

### Step 4: Run Held-Out Motion Benchmark
Evaluate the model against `data/siteagent_motion_eval_v1.jsonl`:
```bash
python evaluation/motion_benchmark.py \
  --model-path models/qwen3-siteagent-motion-r16 \
  --eval-file data/siteagent_motion_eval_v1.jsonl \
  --output-report runs/motion_benchmark_report.json
```

### Step 5: Verify Promotion Decision
Inspect promotion gates:
```bash
python -c "
import json
with open('runs/motion_benchmark_report.json') as f:
    rep = json.load(f)
assert rep['behavioral_score'] >= 0.90, 'Behavioral score too low'
assert rep['performance_score'] >= 0.95, 'Performance score too low'
assert rep['reduced_motion_passed'], 'Reduced motion check failed'
assert rep['no_scroll_jacking'], 'Scroll jacking detected'
print('All motion promotion gates passed successfully!')
"
```

---

## 8. Common Failure Modes & Quick Fixes

### Issue A: Observer callback fires before element dimensions exist
- **Cause**: Observing before mount or when element has `display: none`.
- **Fix**: Use `useRef` with `useEffect`; ensure container has explicit or intrinsic dimensions.

### Issue B: Element sticks at top but jumps during scroll
- **Cause**: An ancestor has `overflow: hidden`, `overflow-x: clip`, or `transform: translate(...)` which establishes a new containing block and breaks CSS `sticky`.
- **Fix**: Verify ancestor chain has `overflow: visible` or use native layout stacking.

### Issue C: Jittery parallax motion
- **Cause**: Translating elements via `top` or `margin` instead of `transform: translate3d(0, var(--parallax-y), 0)`.
- **Fix**: Update only CSS custom properties or transforms within `requestAnimationFrame`. Always mark listeners `{ passive: true }`.

### Issue D: Screen reader stutters across word reveal
- **Cause**: Splitting `<span key={i}>{word}</span>` without hiding them.
- **Fix**: Place `aria-label="Full sentence"` on `<h1 className="...">`, and mark individual word tokens with `<span aria-hidden="true">`.
