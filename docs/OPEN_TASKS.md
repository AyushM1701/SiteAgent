# SiteAgent — Open Tasks

> Consolidated from all planning docs. Tasks already implemented are excluded.
> Last updated: 2026-09-29

---

## P0 — Trust & Release Blockers

### Base Model Identity

- [ ] Invalidate the incompatible motion adapter promotion pointer (`models/qwen3-siteagent-motion-r16` has wrong tensor shape `[16, 11008]` vs required `[16, 9728]`)
- [ ] Expose actual loaded base/adapter fingerprints and compatibility via `/api/status`; do not let the frontend claim Qwen3-4B from hardcoded Zustand defaults
- [ ] Strengthen base-model fingerprint verification: reject startup/training unless base model passes architecture class, `model_type`, hidden size, intermediate size, attention heads, KV heads, layer count, tensor shapes, tokenizer/config compatibility, and model revision/hash checks
- [ ] Store an immutable model fingerprint in `base-model/manifest.json`
- [ ] Replace the relabeled Qwen2 base (current `base-model/config.json` declares `Qwen2ForCausalLM` / `model_type: qwen2`) with authentic Qwen3-4B weights

### Mock Benchmarks in Promotion Path

- [ ] Remove mock/hardcoded benchmark metrics from the migration orchestrator (`mock=True` steps and hardcoded Step J / Step M metric dicts)
- [ ] Every benchmark report must include `provenance: "real"`, `model_sha256`, `adapter_sha256`, `dataset_sha256`, `git_commit`, `hardware`, `mock: false`; promotion must reject reports where `mock != false`
- [ ] Keep mock runs in a separate dashboard from live model evaluations
- [ ] Publish separate scorecards for model-native output, deterministic repair, model repair, and final rendered site; require all four in every promotion report

### Validation Contract

- [ ] Fix frontend validation defaults: agent store treats absent typecheck/build/lint values as `true`; use tri-state (`unknown` / `passed` / `failed`) and never render green for an absent value
- [ ] Make static lint fail closed: if the static/acceptance checker throws, `run_static_lint` must return `status: unknown/failed`, not success
- [ ] Fix browser runtime fallback: if Playwright is unavailable, a static root-container check must be reported as `runtime_unverified`, never `passed`
- [ ] Resolve the "5-gate" documentation vs. code mismatch — either add `contract_passed` and `accessibility_passed` fields or rename docs to match the actual gate model

### Source-Export Integrity

- [ ] Fix the documentation generator: use length-prefixed source blocks or escaped fences, store a SHA-256 next to each embedded section, validate extracted source bytes against original file hashes, fail export if round-trip reconstruction is not exact

---

## P0 — Model Training Correctness

### Qwen3 Migration

- [ ] Download authentic `Qwen/Qwen3-4B` weights into `base-model/` (current weights are Qwen2 relabeled)
- [ ] Retrain Qwen3 LoRA from scratch (rank=16, alpha=16, dropout=0, 4-bit QLoRA, batch=1, grad_accum=4, assistant-only loss, no target truncation) — output to `models/qwen3-siteagent-r16-sft/`
- [ ] Do NOT reuse any Qwen2.5 adapter weights to initialize the Qwen3 run
- [ ] Rerun Qwen3 tokenizer preflight after installing authentic weights
- [ ] Run real 6144/8192 context-length benchmark (not mock) and write result to `runs/qwen3_context_benchmark.json`
- [ ] Run real untouched Qwen3 base baseline on the 153-task set before SFT — record first-turn pass rate, agentic final pass rate, category breakdown, failures, truncations, VRAM
- [ ] After SFT, run real component + interaction + site + motion benchmarks before any promotion decision

### Real Benchmark Execution

- [ ] Run the real (not mock) 153-task agentic baseline benchmark against the Qwen3 base
- [ ] Run the real 36-site full-site benchmark with live model outputs (current report is `mock: true`)
- [ ] Run the real development benchmark with `mock=False`
- [ ] Generate the standard model comparison report from real immutable benchmark reports only (current report has hardcoded/synthetic metrics)

---

## P1 — Generation & Planning Quality

### 3D Gate

- [ ] Require a visible scene contract: canvas + drawable mesh/model or explicit CSS 3D composition — an isolated `<canvas />` must not pass
- [ ] Require browser evidence of rendered pixels and no WebGL errors
- [ ] Add context-loss/fallback checks and a short captured motion timeline
- [ ] Test 3D at mobile and reduced-motion settings
- [ ] Report static 3D policy separately from runtime 3D success
- [ ] Store `three_d_runtime_evidence.json` per workspace with canvas pixels, WebGL state, sampled motion frames, mobile/reduced-motion/fallback visibility

### Motion Behavioral Acceptance

- [ ] Add browser Playwright probes that scroll by controlled increments and assert before/after transform/opacity/position
- [ ] Inspect frame timing/jank under normal and `prefers-reduced-motion` conditions
- [ ] For 3D, sample frame rate and memory with inference running on the same GPU
- [ ] Verify listener cleanup and RAF cancellation in scroll/parallax implementations
- [ ] Test keyboard focus continuity through animated transitions

### Prompt Fidelity & Cross-Section Integration

- [ ] Have planning emit a typed requirement manifest with exact user facts, sections/routes, interactions, visual/motion constraints, and cross-section state contracts
- [ ] Validate requirement manifest contracts after each section and at final composition
- [ ] Feed precise compiler, DOM, and interaction diagnostics into bounded repair
- [ ] Do not allow a polished static page to pass while requested behavior is absent

### Training Coverage

- [ ] Build reviewed full-site examples across stores, portfolios, editorial, arts, civic, events, education, hospitality, healthcare, dashboards, and unfamiliar topics — distinct structures, not palette swaps
- [ ] Add complete 3D and motion trajectories with actual browser verification
- [ ] Add targeted repair examples with diagnostics that caused each repair
- [ ] Preserve family-level separation; record source, license, validation, and visual review for each row
- [ ] Audit older quality data for truncation, broken tool envelopes, duplicated families, fake metrics, missing CSS, broken interactions
- [ ] Split families before generating variants; add hashes, source provenance, parser/TSC/browser evidence, and review status per record

### Visual Quality Review

- [ ] Create a visually reviewed holdout set with rubric scores: layout, hierarchy, typography, content specificity, imagery/asset quality, motion timing, mobile composition
- [ ] Capture full-page screenshots and short scroll videos at desktop/mobile and reduced motion
- [ ] Implement blinded pairwise human review (`scripts/blinded_visual_review.py prepare` / `assemble` workflow)
- [ ] Two independent humans must score both A and B for each of the 30 sites in `data/eval/visual_holdout_v1.jsonl`
- [ ] Implement review/approval UI/workflow — `review_status == 'approved'` gate intentionally withheld until this exists

### Layout Archetype Diversity

- [ ] Create balanced site trajectories across: split hero, editorial asymmetric hero, full-bleed image/visual hero, bento hero, terminal/data hero, product-stage hero, restrained centered hero — no archetype should dominate
- [ ] Add design-planning supervision before file generation: condition the model on a compact structured plan (artDirection, heroArchetype, density, typeScale, sectionRhythm, motion, visualAnchor, mobileStrategy)

### Model Evaluation Metrics

- [ ] Maintain independent scores for: correctness/build/runtime, prompt fidelity, interaction behavior, responsive behavior, accessibility, visual composition, motion quality, performance, diversity, fallback/recovery dependency
- [ ] Track and penalize recovery dependence — lower fallback/auto-scaffold use should score better

---

## P1 — Motion Architecture

### Motion Module

- [ ] Wire up `MotionSpec` dataclass and `MotionType` enum in `agent/motion_patterns.py` with prompt extraction: `extract_motion_requirements(prompt) -> list[MotionSpec]`
- [ ] Add motion plan XML block `<motion_plan>` to content brief
- [ ] Give current-section motion requirements high priority in ContextBuilder so compaction never drops them
- [ ] Add motion-specific runtime/Playwright validator (`evaluation/motion_benchmark.py`)
- [ ] Add motion benchmark prompts and promotion metrics: all six feature families must pass before promotion

### Motion Training Data Integration

- [ ] Validate `siteagent_motion_sft_v1.jsonl` against leakage checks before merging
- [ ] Mix motion curriculum into existing replay data at ~10-20%, balanced by category not raw row count
- [ ] Confirm the authentic Qwen3 R16 candidate manifest explicitly names the motion curriculum
- [ ] Do NOT train exclusively on the motion dataset (catastrophic forgetting risk)

---

## P1 — Workbench UX

### Default Mode & Intent

- [ ] Make Full Site the visible default for website prompts, or auto-detect site intent and display mode before sending
- [ ] Keep Component as an explicit visible option
- [ ] Update starter prompts to cover more domains; avoid implying real checkout without payment integration

### Mobile Navigation

- [ ] Initialize sidebar closed below the desktop breakpoint (`workspace-store.ts` currently sets `sidebarOpen: true` at every viewport)
- [ ] Preserve user sidebar preference per viewport
- [ ] Label the toggle for screen readers; make backdrop dismissible by Escape
- [ ] Ensure composer is visible on the first mobile visit without manual interaction

### Project List UX

- [ ] Parse ISO/date strings explicitly in `ProjectItem.tsx` — `Number(timestamp)` incorrectly shows "Updated Just now" for nonnumeric timestamps
- [ ] Make project title a focusable button; keep delete as a separate button; show delete on keyboard focus
- [ ] Add readable date labels and tooltips; avoid exposing raw session IDs as dominant subtitle

### Status & Context Indicators

- [ ] Read GPU readiness from explicit backend telemetry field — do not set `gpuReady: true` on any successful status response
- [ ] Label context-token count as estimated; replace with actual tokenizer counts when available (currently synthesized from characters, clamped to 920)
- [ ] Rename "Motion Verified" to "Motion checks passed" until real browser motion verification exists
- [ ] Use explicit `verified`, `estimated`, `unknown` states throughout; omit unknown values

### Preview & Editor Performance

- [ ] Lazy-load Monaco and terminal tabs (currently imported upfront in `WorkspacePanel`)
- [ ] Open preview automatically after a site build
- [ ] Use empty state to collect: topic, audience, pages, content, desired visual style, 3D/motion preference, real assets
- [ ] Add compact preview diagnostics drawer: console errors, broken links, interaction checks, viewport dimensions, reduced-motion results

### WebSocket Migration

- [ ] Choose WebSocket as the authoritative real-time channel; keep SSE only as a compatibility fallback pending removal
- [ ] Core generation path still retains SSE — migrate it to the project WebSocket
- [ ] Remove remaining duplicate client scheduling paths (`processNextQueuedTask()`, manual queue promotion, frontend task scheduling)

### Workbench Motion Surface

- [ ] Surface requested/implemented motion plan in Inspector drawer
- [ ] Add a Motion capability badge only when motion is browser-verified
- [ ] Show motion runtime failures in Logs and the completion summary

---

## P2 — Visual Assets & 3D

- [ ] Build a small library of original/licensed hero scenes with stable import paths and tested React interfaces
- [ ] Train the model to select, configure, and integrate assets instead of inventing remote GLB URLs
- [ ] Add optional R3F only where actual 3D interaction improves the design; keep CSS animation for simple effects
- [ ] Establish measured scene budgets: bounded pixel ratio, few lights, restrained textures/geometry, lazy loading, offscreen pause, reduced-motion behavior, static fallback when WebGL is unavailable
- [ ] Render idle scenes on demand; invalidate frames on scene state change
- [ ] Add training trajectories for camera/light adjustments, responsive composition, loading failures, and performance fixes with real browser feedback
- [ ] Test all 3D scenes while inference is active (GPU contention on RTX 4050)

---

## P3 — Optional / Future

### Optional Vision Feedback

- [ ] Evaluate a separate vision model only after browser evidence is integrated
- [ ] Load it sequentially; release code model GPU process before loading vision and vice versa
- [ ] Record screenshot observations as tool feedback and verify repairs
- [ ] No VL fine-tuning until baseline usefulness and memory feasibility are established

### DPO Alignment

- [ ] Only consider DPO from real verified rollouts — after authentic Qwen3 R16 SFT, real benchmarks, and layout/motion diversity inspection all pass
- [ ] Run original/candidate comparisons for completion, functional pass, regression, latency, memory, and blind visual preference before any DPO run

---

## Promotion Gate Checklist

A candidate should only be promoted if ALL of the following pass:

- [ ] Authentic model/base fingerprints verified (not relabeled Qwen2)
- [ ] Benchmark provenance is `real`, not `mock`
- [ ] TypeScript / build / runtime / contract gates all pass
- [ ] Interaction benchmark improves over baseline
- [ ] Full-site benchmark improves (real model outputs, not mock)
- [ ] Motion benchmark passes all six feature families
- [ ] 375 px mobile layout passes
- [ ] Reduced-motion behavior passes
- [ ] No scroll-jacking detected
- [ ] Layout diversity clears fixed thresholds
- [ ] Fallback/auto-scaffold dependence is low
- [ ] Source export/documentation round-trips exactly
- [ ] Two independent human reviewers have scored blinded A/B visual review
