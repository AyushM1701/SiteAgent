# SiteAgent Updated Audit, Completion Check & Motion Professionalization Plan

## Audit scope and limitation

This report audits `architecture_and_source(2).md`, a 134,596-line exported architecture/source artifact, against the earlier 32-step `SiteAgent_Full_Implementation_Plan.md`.

The updated project has made substantial progress. Most of the original implementation plan is now represented in code. However, several issues prevent calling the plan fully complete—most importantly the model identity / Qwen3 verification problem, mock-contaminated benchmark/promotion reports, fail-open validation paths, frontend default-green validation states, and incomplete replacement of SSE with the project WebSocket.

The exported source document itself also contains at least one serialization defect where embedded Markdown fences/code appear to corrupt the `server/app.py` section. The underlying repository should therefore be treated as authoritative for executable verification.

---

# 1. 32-Step Implementation Plan Status

| # | Plan item | Status | Required follow-up |
|---:|---|---|---|
| 1 | Strict validation contract | **Mostly complete** | Backend `passed` is strict, but docs call this 5-gate while result object does not expose independent contract/accessibility gates. |
| 2 | Remove fabricated success | **Partial** | Backend read-only state is improved, but frontend event/summary code still defaults missing validation values to green/true. |
| 3 | Diff frontend/backend contract | **Complete structurally** | Keep contract tests and run E2E against a real session. |
| 4 | Real project ZIP export | **Complete structurally** | Add extracted-project build test to E2E. |
| 5 | Monaco behavior | **Complete structurally** | Dirty state, save/discard and Ctrl/Cmd+S are present. |
| 6 | New-project state isolation | **Complete structurally** | Project-scoped logs are represented; verify in live E2E. |
| 7 | New project during GPU task | **Complete structurally** | Cancellation/reset path exists; verify with actual GPU generation. |
| 8 | Project WebSocket migration | **Partial** | Backend project WS exists and Vite can proxy it, but core generation still retains SSE. Choose one authoritative channel. |
| 9 | Backend queue ownership | **Mostly complete** | Backend lifecycle/queue is authoritative; remove remaining duplicate client scheduling paths. |
| 10 | Workspace resizer capture | **Complete structurally** | `currentTarget`, cancellation/lost-capture handling are represented. |
| 11 | Replace native confirm/alert | **Complete structurally** | Custom confirmation/toast system is represented. |
| 12 | Bare `--preflight-only` | **Complete** | CLI defaults exist. |
| 13 | `benchmark_qwen3.py` | **Implemented but evidence invalid for promotion** | Real benchmark must run with `mock=False`; mock report must never select production configuration. |
| 14 | Evidence-based 6144/8192 decision | **Partial** | Decision machinery exists, but current migration orchestration creates/uses mock benchmark output when absent. |
| 15 | Single source context length | **Complete structurally** | `ModelRuntimeConfig` centralizes context length and real-tokenizer counting. |
| 16 | Native Qwen3 chat template | **Complete structurally** | `apply_chat_template(... enable_thinking=False)` path exists. |
| 17 | Remove thought targets | **Complete structurally** | Preflight rejects `<think>` and `<thought>`; cleaner exists. |
| 18 | Train Qwen3 LoRA from scratch | **Not trustworthy / must be redone** | The embedded `base-model/config.json` is Qwen2 architecture data relabeled as Qwen3. Reinstall authentic Qwen3-4B, then retrain. |
| 19 | Methodology before sweeps | **Complete structurally** | Gating code exists. |
| 20 | Benchmark untouched Qwen3 base | **Not complete as a real baseline** | Orchestrator calls base benchmark in mock mode. Run real 153-task baseline. |
| 21 | Protect 153-task benchmark | **Complete structurally** | Sealed benchmark and leakage checks are represented. |
| 22 | Interaction curriculum | **Complete structurally** | Interaction curriculum exists; keep expanding from real failures. |
| 23 | Self-contained code | **Complete structurally** | No-invention rule and guards/tests exist. |
| 24 | Dynamic output budgets | **Complete structurally** | Output-budget module/tests represented. |
| 25 | Full-site benchmark | **Partial** | 36-site suite exists, but orchestration can evaluate handcrafted mock sites. Real model outputs are required. |
| 26 | Remove style bias | **Mostly complete** | Structured style presets exist; balance presets/data so styles do not become prompt templates. |
| 27 | Anti-template collapse | **Complete and useful** | Diversity evaluator exists and correctly detects centered-hero concentration. |
| 28 | First-class 3D | **Complete structurally** | 3D tool layer/evaluation exists; continue runtime/performance tests. |
| 29 | Workbench control audit | **Implemented** | Static/control audit exists. Live runtime remains the final authority. |
| 30 | Playwright workbench E2E | **Implemented, not independently re-run from the source export** | Run the actual repository test suite in CI and retain artifacts/screenshots/traces. |
| 31 | Full Qwen3 migration sequence | **Not complete** | Migration orchestration uses mocks and model identity is wrong; real sequence must be rerun. |
| 32 | Standard model comparison | **Implemented but currently not valid evidence** | Report contains hardcoded/synthetic metrics. Generate from real immutable benchmark reports only. |

---

# 2. Critical Issues to Fix Before More Model Training

## P0 — Base model identity is inconsistent

The exported `base-model/config.json` labels `_name_or_path` as `Qwen/Qwen3-4B` but declares `Qwen2ForCausalLM`, `model_type: qwen2`, hidden size 2048, 16 attention heads and 2 KV heads. This is not a sufficient Qwen3 identity.

The migration verifier currently checks mainly that `_name_or_path` contains `Qwen3`, so a relabeled older configuration can pass.

### Fix

Reject startup/training unless the base model fingerprint matches the expected Qwen3 architecture. At minimum verify:

- architecture class
- `model_type`
- hidden size
- intermediate size
- attention heads
- KV heads
- layer count
- tensor shapes in the model shards
- tokenizer/config compatibility
- model repository revision/hash

Store an immutable model fingerprint in `base-model/manifest.json`.

## P0 — Server still points at the legacy adapter path

`server/app.py` points `MODEL_PATH` at `my-react-agent-lora`, while the candidate Qwen3 adapter is under `models/qwen3-siteagent-r16-sft`.

Do not let the frontend claim `Qwen3-4B` from hardcoded Zustand defaults. `/api/status` must expose the model actually loaded, including base fingerprint and adapter fingerprint.

## P0 — Migration and benchmark orchestration uses mocks

The migration orchestrator calls context/base/site/comparison benchmark helpers with `mock=True` in several steps and Step J / Step M contain hardcoded metric dictionaries.

Mock mode is useful for CI contract tests, but it must never produce promotion evidence.

### Fix

Every benchmark report must include:

```json
{
  "provenance": "real",
  "model_sha256": "...",
  "adapter_sha256": "...",
  "dataset_sha256": "...",
  "git_commit": "...",
  "hardware": "...",
  "mock": false
}
```

Promotion must reject reports where `mock != false` or provenance is not `real`.

## P0 — Frontend validation can default to green

The agent store currently treats absent typecheck/build/lint values as `true`, and the completion summary also defaults absent code/build/preview values to true.

Use tri-state validation:

```text
unknown
passed
failed
```

Never render green for an absent value.

## P0 — Static lint fails open

If the static/acceptance checker throws, `run_static_lint` currently returns success with a warning.

For production verification this must fail closed:

```text
checker exception -> gate status unknown/failed -> aggregate not valid
```

## P0 — Browser runtime fallback can falsely pass

If Playwright is unavailable, the fallback only checks that returned HTML contains `<div id="root">`, then can report runtime success. That does not prove React mounted and does not detect console/page errors.

Production validation should require Playwright (or equivalent browser execution). A static root-container check should be reported as `runtime_unverified`, never `passed`.

## P1 — “5-gate” documentation and code differ

The documentation describes a separate contract/accessibility gate, but the current `ValidationResult` does not expose an independent contract/accessibility field; acceptance checks are folded into lint.

Either:

1. add `contract_passed` and `accessibility_passed`, or
2. rename the documentation to match the actual gate model.

## P1 — Project WebSocket migration remains hybrid

SSE remains in the generation path while a project WebSocket also exists.

Choose the WebSocket as authoritative and keep SSE only as a compatibility fallback until removal.

## P1 — Source-export generation is corruptible

The exported architecture/source markdown contains fence/code contamination inside the `server/app.py` section.

Fix the documentation generator by:

- using length-prefixed source blocks or escaped fences
- choosing a fence longer than any fence found in source
- storing a file SHA-256 next to each embedded section
- validating extracted source bytes against original file hashes
- failing export if round-trip reconstruction is not exact

---

# 3. Professional-Grade Website Model Improvements

The current project already has several strong ingredients: an explicit professional-site contract, interaction/accessibility requirements, responsive constraints, a visual judge, diversity evaluator, self-contained-code guards, full-site evaluation, 3D tooling, dynamic output budgets and a repair loop.

The next improvements should focus on **measured design quality**, not just more SFT rows.

## A. Fix the real Qwen3 foundation first

Do not add another large training run until authentic Qwen3-4B weights/config are installed and verified.

Then rerun:

1. real 6144/8192 benchmark
2. tokenizer preflight
3. real untouched Qwen3 baseline
4. scratch R16 SFT
5. real development benchmark
6. real 153-task benchmark
7. real full-site benchmark

## B. Balance layout archetypes

The diversity evaluator already detected hero collapse. Create balanced site trajectories across:

- split hero
- editorial asymmetric hero
- full-bleed image/visual hero
- bento hero
- terminal/data hero
- product-stage hero
- restrained centered hero

No archetype should dominate the training or promotion batch.

## C. Add design-planning supervision

Before file generation, condition the model on a compact structured design plan:

```json
{
  "artDirection": "editorial industrial",
  "heroArchetype": "split",
  "density": "airy",
  "typeScale": "display-heavy",
  "sectionRhythm": ["quiet", "dense", "immersive", "quiet"],
  "motion": ["text-reveal", "sticky-story"],
  "visualAnchor": "product-render",
  "mobileStrategy": "stack"
}
```

The plan should be generated/selected by deterministic orchestration where possible, not exposed as hidden reasoning.

## D. Evaluate behavioral and visual outcomes separately

A site can compile and still be poor.

Maintain independent scores for:

- correctness/build/runtime
- prompt fidelity
- interaction behavior
- responsive behavior
- accessibility
- visual composition
- motion quality
- performance
- diversity
- fallback/recovery dependency

## E. Penalize recovery dependence

A model that needs auto-scaffolding for every site is not stronger.

Track:

```text
model-native success rate
repair success rate
fallback-free completion rate
auto-scaffold usage rate
```

Lower fallback use should be better.

---

# 4. New Motion Feature Architecture

Add first-class support for:

1. scrolling animations
2. parallax scrolling
3. horizontal scroll sections
4. sticky positioning / sticky storytelling
5. text reveal on scroll
6. micro-interactions

## New module: `agent/motion_patterns.py`

Add:

```python
class MotionType(str, Enum):
    SCROLL_REVEAL = "scroll_reveal"
    PARALLAX = "parallax"
    HORIZONTAL_SCROLL = "horizontal_scroll"
    STICKY_STORY = "sticky_story"
    TEXT_REVEAL = "text_reveal"
    MICRO_INTERACTION = "micro_interaction"
```

Add a structured `MotionSpec`:

```python
@dataclass
class MotionSpec:
    type: MotionType
    target_section: str
    intensity: Literal["subtle", "medium", "cinematic"]
    axis: Literal["x", "y", "both", "none"]
    trigger: Literal["viewport", "scroll-progress", "interaction"]
    reduced_motion_behavior: Literal["static", "instant", "native-scroll"]
    mobile_fallback: Literal["stack", "native-horizontal", "static"]
    implementation: Literal["native", "gsap", "framer-motion"]
```

## Prompt extraction

Implement:

```python
extract_motion_requirements(prompt) -> list[MotionSpec]
```

Detect phrases such as:

```text
scroll animation
scroll reveal
parallax
horizontal scroll
sticky story
sticky section
pin section
text reveal
word reveal
micro interaction
hover interaction
scroll-driven
scrub
```

Keep motion parsing separate from section parsing.

## Content brief

Add:

```xml
<motion_plan>
  <motion type="text_reveal" section="hero" intensity="subtle" />
  <motion type="sticky_story" section="process" intensity="medium" />
</motion_plan>
```

## ContextBuilder

Give current-section motion requirements high priority so compaction never drops them.

---

# 5. Motion Implementation Rules

## Scroll reveal

Default implementation:

- `IntersectionObserver`
- opacity/transform only
- `observer.unobserve()` or `disconnect()`
- content not permanently hidden before JS
- `prefers-reduced-motion`

## Parallax

Default implementation:

- passive scroll listener
- `requestAnimationFrame`
- CSS transform / custom property
- bounded translation
- no React `setState()` every scroll tick
- cleanup listener + RAF
- disabled/reduced on mobile and reduced-motion

Never use `wheel.preventDefault()` for ordinary parallax.

## Horizontal scroll sections

Desktop:

```text
normal vertical document scroll
→ section progress
→ sticky viewport
→ translate3d horizontal track
```

Do not hijack wheel or touch.

Mobile:

```text
native overflow-x:auto + scroll-snap
```

or stack vertically.

## Sticky storytelling

Use CSS `position: sticky`.

Validate that no ancestor invalidates sticky through incompatible overflow/transform/layout choices.

Keep semantic DOM order suitable for keyboard/screen-reader navigation.

## Text reveal

Use one accessible heading label and decorative split-word/line spans:

```tsx
<h1 aria-label="Full readable heading">
  <span aria-hidden="true">Full</span>
  ...
</h1>
```

Reduced motion shows full text immediately.

## Micro-interactions

Use:

- hover + focus-visible/focus-within parity
- `aria-pressed` / `aria-selected` for state
- transform/opacity/color/border
- short durations, typically 120–250 ms
- no layout shift

---

# 6. Motion Library Policy

Default to native browser/CSS implementations because the project runs on local constrained hardware and must not hallucinate packages.

Only use GSAP/ScrollTrigger or Framer Motion when:

1. dependency inspection confirms the package, or
2. the dependency manager successfully installs it.

Never train trajectories that silently import an unverified package.

If GSAP support is added, create **separate** library-specific trajectories rather than mixing them into native examples without labels.

---

# 7. Motion Validation & Benchmarking

Add `evaluation/motion_benchmark.py` and Playwright behavioral tests.

A regex/code-level judge is not sufficient because models can satisfy it by including strings without correct behavior.

## Runtime tests

### Scroll reveal

Measure an element before and after scrolling into view.

### Parallax

Verify transform changes across scroll positions and that no wheel/touch event is prevented.

### Horizontal scroll

Verify desktop track translation and mobile native overflow/scroll-snap.

### Sticky

Measure bounding-box position while the page progresses through the sticky range.

### Text reveal

Check accessible name, `aria-hidden` split spans, and reduced-motion visibility.

### Micro-interactions

Use mouse + keyboard focus and assert visual/state changes.

## Performance checks

Capture:

- page errors
- console errors
- long tasks if available
- layout shifts
- uncontrolled requestAnimationFrame loops
- listener cleanup
- body horizontal overflow
- mobile 375 px behavior

---

# 8. Motion Training Data

A separate training curriculum was generated alongside this report:

- `siteagent_motion_sft_v1.jsonl`
- `siteagent_motion_eval_v1.jsonl`
- `siteagent_motion_dataset_manifest.json`
- `SITEAGENT_MOTION_TRAINING_GUIDE.md`

The SFT file contains 36 trajectories:

- 5 scroll-reveal gold examples
- 5 parallax gold examples
- 5 horizontal-scroll gold examples
- 5 sticky-story gold examples
- 5 text-reveal gold examples
- 5 micro-interaction gold examples
- 6 repair trajectories, one for each motion family

The held-out eval set contains 12 family-disjoint prompts.

Do not train only on the motion dataset. Mix it with the existing component, interaction, repair, full-site, accessibility, diversity and 3D replay data.

---

# 9. Recommended Execution Order

```text
P0
1. Replace relabeled base model with authentic Qwen3-4B.
2. Strengthen base-model fingerprint verification.
3. Make server load the actual promoted adapter and report fingerprints.
4. Remove mock/hardcoded benchmark metrics from promotion.
5. Make validation fail closed.
6. Replace frontend default-green booleans with tri-state validation.
7. Repair source-document export round-trip integrity.

MOTION FOUNDATION
8. Add MotionSpec + prompt extraction.
9. Add motion plan to content brief and ContextBuilder.
10. Extend site prompt/professional contract with six motion families.
11. Add native motion utilities/patterns.
12. Add motion-specific runtime/Playwright validator.
13. Add motion benchmark prompts and promotion metrics.

TRAINING
14. Validate the provided motion SFT file.
15. Mix motion curriculum into existing replay data at a controlled ratio.
16. Rerun Qwen3 tokenizer preflight.
17. Train authentic Qwen3 R16 candidate.
18. Run real component + interaction + site + motion benchmarks.
19. Inspect layout/motion diversity.
20. Only then consider DPO from real verified rollouts.

WORKBENCH
21. Surface requested/implemented motion plan in Inspector.
22. Add a Motion capability badge only when verified.
23. Show motion runtime failures in Logs and completion summary.
24. Keep Preview live while tuning scroll behavior.
```

---

# Final acceptance target

A professional-grade SiteAgent candidate should only be promoted if:

- authentic model/base fingerprints are verified
- benchmark provenance is real, not mock
- TypeScript/build/runtime/contract gates all pass
- interaction benchmark improves
- full-site benchmark improves
- motion benchmark passes all six feature families
- 375 px mobile layout passes
- reduced-motion behavior passes
- no scroll-jacking is detected
- layout diversity clears fixed thresholds
- fallback/auto-scaffold dependence is low
- source export/documentation round-trips exactly
