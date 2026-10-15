# SiteAgent Motion Curriculum — Training Guide

## Files

- `siteagent_motion_sft_v1.jsonl` — 36 SFT trajectories.
- `siteagent_motion_eval_v1.jsonl` — 12 held-out motion prompts.
- `siteagent_motion_dataset_manifest.json` — hashes, counts, and validation metadata.

## Capability coverage

The training set contains six distinct capability families:

1. Scroll-triggered reveals using `IntersectionObserver`.
2. Parallax scrolling using passive scroll events + `requestAnimationFrame`.
3. Horizontal scroll storytelling using normal vertical progress and a sticky track, with **no wheel/touch hijacking**.
4. Sticky narrative layouts using CSS `position: sticky`.
5. Accessible text reveal on scroll with an unsplit accessible heading label.
6. Micro-interactions with hover/focus/pressed parity and short transform/color transitions.

Each family contains five positive examples across different visual domains, plus one repair trajectory targeting a common production failure. The data intentionally uses browser APIs and CSS rather than assuming GSAP or Framer Motion is installed.

## Important: do not train on this file alone

Use this as a **separate motion curriculum** mixed into the existing Qwen3 quality/replay data. Training exclusively on the motion set would increase catastrophic-forgetting and template-collapse risk.

A practical first experiment is to make motion examples roughly 10–20% of an SFT epoch while retaining the existing interaction, repair, full-site, component, accessibility, and 3D data. Keep sampling balanced by `category`, not by raw row count.

## Preflight

Run the repository's normal Qwen3 data checks on the motion file before merging:

```bash
python training/train_sft.py \
  --data siteagent_motion_sft_v1.jsonl \
  --preflight-only
```

The generated data contains no `<think>` or `<thought>` targets and every assistant turn emits exactly one tool action.

## Recommended integration

Do not copy held-out evaluation prompts into training.

Suggested pipeline:

```text
existing quality_candidate/train.jsonl
            +
siteagent_motion_sft_v1.jsonl
            ↓
family-aware / category-balanced mixer
            ↓
leakage check against:
  - react_ts_css_eval_set_combined.jsonl
  - full_website_benchmark.jsonl
  - siteagent_motion_eval_v1.jsonl
            ↓
Qwen3 tokenizer preflight
            ↓
scratch / continued Qwen3 SFT candidate
            ↓
motion behavioral benchmark
```

For an already-trained Qwen3 adapter, prefer a low-LR curriculum continuation only after confirming it is genuinely based on the correct Qwen3-4B weights. Keep replay examples in the same run.

## Motion behavioral acceptance tests

A motion model should not pass merely because the source contains strings such as `IntersectionObserver` or `position: sticky`. Run the generated site in Playwright and test behavior.

### Scroll reveal

- Element has readable content before JavaScript.
- Scrolling it into view changes its motion state.
- Observer disconnects / unobserves.
- `prefers-reduced-motion: reduce` keeps content visible without movement.

### Parallax

- Scroll changes transform without React state updates per scroll tick.
- Listener is passive.
- Updates are RAF-throttled.
- RAF/listeners are cleaned up.
- No wheel/touch `preventDefault`.
- Reduced motion disables transform.

### Horizontal scroll

- Desktop scroll progresses the horizontal track.
- The page still uses normal browser vertical scrolling.
- No wheel/touch hijacking.
- At 375px, panels use native overflow or stack vertically.
- No body-level horizontal overflow.

### Sticky storytelling

- Sticky element remains pinned through the intended chapter range.
- No ancestor invalidates sticky with incompatible overflow.
- Mobile layout becomes normal document flow.

### Text reveal

- One coherent accessible heading name.
- Decorative split-word spans are hidden from assistive technologies.
- Reduced-motion mode shows the full headline instantly.

### Micro-interactions

- Hover behavior has keyboard-focus parity.
- Toggle state exposes `aria-pressed`/equivalent state.
- Animation uses transform/opacity/color instead of layout-heavy properties.
- Typical durations stay around 120–250 ms.
- No layout shift occurs on interaction.

## Library policy

Default to native CSS + browser APIs. If the user explicitly asks for GSAP/ScrollTrigger or Framer Motion:

1. call dependency inspection;
2. install the package through the controlled dependency manager;
3. generate library-specific code only after installation succeeds;
4. still implement reduced-motion behavior and cleanup;
5. never train examples that silently import an unverified package.

## Dataset validation result

Structural validation issues found while generating this package: **0**.

Train SHA-256:

```text
ab1932e2ce71d08706b63e2461d3094b79e897d34d2619102cc8569dcae89790
```

Eval SHA-256:

```text
beb8737d2eada6a0a86928304a68243de98ac4685e9dc57d15737a010fd6fc83
```
