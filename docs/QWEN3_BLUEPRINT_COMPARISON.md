# Blueprint comparison and improvement priorities

Reviewed 2026-09-17 against `Qwen3-4B_WebDev_3D_AI_Blueprint.md` supplied by the user. The document is a design proposal, not authorization to execute its installation, migration, or training instructions.

## Actual baseline

- Serving model: Qwen2.5-Coder-3B-Instruct, 4-bit, shipped LoRA rank 16 / alpha 16 / dropout 0.0. **Migration to Qwen3-4B in progress (Item 15): code layer complete, new adapter training pending.**
- Target model: Qwen3-4B (base). Chat template now uses `tokenizer.apply_chat_template(..., enable_thinking=False)`. Legacy ChatML hand-rolling removed. `<think>` token blocked at preflight and stripped at decode.
- Latest isolated candidate: `models/premium-reference-v1`; 984 training records, 104 validation records, 246 optimizer steps, one epoch. Training took 98.1 minutes with 3.18 GiB peak PyTorch allocated memory. This is not total system/GPU memory and is not a prediction for another model.
- Validation loss fell from 0.5944 to 0.3368. This does not establish better visual quality.
- Candidate passed the tabs compilation check that the original failed, but both failed the two interaction probes. Candidate hero/pricing responses were incomplete at the tested 2,048-token output budget. Candidate was not promoted; original adapter remains selected.
- These are one-shot section probes. The production site loop already has completeness, CSS, and TypeScript gates and repair attempts; probe failures do not establish that the full loop would deliver those exact broken outputs. The full 153-task benchmark was not rerun.
- The new reference curriculum contains 21 records derived from three original sites. The 984-record mix is neither 984 independent sites nor uniformly verified gold data.

Evidence: [training audit](TRAINING_AUDIT_2026-09-16.md), [results](../experiments/premium-reference-v1/RESULTS.md), [machine-readable outcome](../experiments/premium-reference-v1/outcome.json).

## Comparison

| Blueprint proposal | Current implementation | Recommendation |
|---|---|---|
| Generate, execute, inspect, repair | Component tests, site sections, TSC/CSS gates, previews already exist | Extend feedback to real site interactions and browser console; avoid rebuilding the workbench |
| General file/search/edit tools and project state | Specialized write-component/write-site/test protocol; human PTY terminal | Add workspace-bounded read/search/edit tools with explicit results and a persistent project manifest; a human terminal is not a model tool API |
| Qwen3-4B code model | Qwen2.5-Coder-3B plus existing adapter and Qwen2-specific training assumptions | Benchmark a separate base-model candidate before committing to migration |
| Three.js / R3F / advanced animation | Reusable CSS 3D scene and curated references | Add optional tested R3F scene assets, then train their composition and repair |
| Screenshot model | Screenshot capture and pixel heuristics | Use DOM/console checks and human visual review first; heuristic scores do not understand design |
| 30k–50k training examples | Small curated addition mixed into historical replay | Expand independent, verified examples before expanding volume; record provenance and avoid benchmark leakage |
| Many frontend/backend stacks | React/Vite/TypeScript/CSS focus | Stabilize this stack before adding Next.js, databases, physics, and multiple animation libraries |

## Corrections needed before adopting the recipe

1. **Qwen3 is not a drop-in adapter replacement.** ✅ **IMPLEMENTED (Item 15)**: `agent.py` now includes a base-model guard that reads `adapter_config.json` and raises `RuntimeError` if a Qwen2.5 adapter is loaded against the Qwen3 base. A new adapter must be trained; the code migration (tokenizer registration, chat-template delegation, think-strip) is complete. See `scripts/benchmark_qwen3.py` for VRAM feasibility testing.
2. **The proposed 2,048-token training context cannot hold the current site system prompt.** That prompt alone measures about 4,750 tokens with the current tokenizer. Compact task-specific prompts and selective context retrieval must come first. Training context includes input and target; an output-token budget is a different setting. Do not silently truncate instructions or targets to fit.
3. **Do not copy alpha 32 / dropout 0.05 into continuation training.** The shipped adapter uses alpha 16 / dropout 0.0, and continuation checks enforce compatibility. Those proposed values are experiments for a new adapter, not corrections to the current one.
4. **The sample tool-call dataset is not compatible with our current trainer.** We use explicit XML tool outputs and validated conversation structure. Convert examples with real tool results and complete file content; do not paste the blueprint's illustrative messages directly into training JSONL.
5. **6 GB feasibility requires measurement.** ✅ **IMPLEMENTED (Item 15)**: `scripts/benchmark_qwen3.py` runs warm-up generation at 4096, 6144, and 8192 tokens and prints peak GPU GiB with PASS/FAIL against a 5.5 GiB ceiling. Run after placing Qwen3-4B weights in `base-model/`. The VRAM guard in `train_sft.py` has been raised from 4.5 GiB to 5.0 GiB.
6. **A target of 45,000 examples is not evidence of sufficient quality.** Start with a reviewed pilot of independent sites, modifications, and repairs. Split by project/design family before producing variations. Keep existing failing evaluation prompts held out; train different cases that exercise the same skills.

## Recommended order of work

### P0: Complete and correct outputs

- Preserve the system contract when compacting history; replace token slicing with explicit context budgeting and bounded file excerpts.
- Teach shorter complete file writes and targeted modifications instead of repeatedly emitting entire components and stylesheets.
- Expand held-out behavior checks: tabs selection/focus, billing arithmetic and labels, mobile navigation, forms, and in-page anchors. Promote only after complete outputs, compilation, and requested behaviors pass; then run the broader benchmark for regression evidence.
- Render complete themed sites at mobile and desktop sizes. Check overflow, browser errors, accessibility, reduced motion, and interaction behavior. Human review should judge hierarchy, typography, spacing, art direction, and consistency.
- Fixed during this review: section prompts no longer force three pricing tiers or fabricated testimonials. They now preserve supplied billing terms and require supplied or explicitly illustrative endorsements. Historical architecture claims of production readiness and fully verified data were corrected.

### P1: Useful tools and project memory

- Add read/search/edit operations constrained to the active project, with bounded outputs, path validation, and explicit success/error observations.
- Track routes, section responsibilities, design tokens, dependencies, assets, and verified behavior in a structured manifest.
- Retrieve only relevant local component/API examples. Keep command execution constrained; do not expose arbitrary shell execution merely because the UI already has a PTY.

### P2: Professional visual assets on the laptop

- Build a small library of original/licensed hero scenes with stable import paths and tested React interfaces. Train the model to select, configure, and integrate assets instead of inventing remote GLB URLs.
- Keep CSS animation for simple effects. Add R3F only where actual 3D interaction improves the design.
- Establish measured scene budgets: bounded pixel ratio, few lights, restrained textures/geometry, lazy loading, offscreen pause, reduced-motion behavior, and a static fallback when WebGL is unavailable.
- Render idle scenes on demand and invalidate frames when scene state changes; animated scenes still need frames. The [R3F performance guide](https://r3f.docs.pmnd.rs/advanced/scaling-performance) describes on-demand rendering and adaptive performance. Test while inference is active because both can contend for the laptop GPU.
- Add training trajectories for camera/light adjustments, responsive composition, loading failures, and performance fixes, with real browser feedback.

### P3: Decide whether Qwen3 earns a migration

Run the exact same unseen tasks, tool protocol, and output budget against an isolated Qwen3 candidate. Compare completion, interactions, full-site repair success, latency, peak memory, and blind visual preference. Revalidate chat formatting and chunked loss before any fine-tune. Adopt only if measured benefits justify migration; parameter count alone does not establish professional website quality.

### P4: Optional screenshot inspection

Evaluate a separate vision model only after browser evidence is integrated. Load it sequentially, record its observations as tool results, and verify proposed fixes through the browser. This is a separate capability from the text model; screenshot capture alone does not give the text model vision.

## How the user can help

Supply a few specific screenshots/sections that demonstrate desired typography, motion, and composition; licensed product imagery or 3D assets; and rankings of generated variants. Concrete acceptance feedback is more useful at this stage than collecting thousands of unreviewed examples. No additional hardware purchase is required to carry out the next correctness and dataset-quality improvements.
