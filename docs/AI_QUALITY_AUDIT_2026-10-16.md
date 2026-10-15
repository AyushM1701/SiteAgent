# AI Website-Quality Audit — 2026-10-16

Goal under review: *the AI should generate professional-quality websites.*
Everything below was checked against the code, the logged prompts/outputs in `runs/`, or by
running the code. "Verified" means reproduced in this audit; "likely" means read from code but not
executed end to end.

## Bottom line

The system cannot currently produce professional websites, and its gates would not notice if it did
or didn't. Four root causes dominate:

1. **No trained model is in use.** The workbench serves the untuned Qwen3-4B base model
   (`models/promoted_model.json`: `gate_status: BLOCKED`, stage H failed 0/3). The latest candidate
   (`audit-v6`) was trained on **39 rows at lr 2e-5 for 2 epochs (~20 optimizer steps)** — far too
   little to change behaviour.
2. **The prompt the model sees at inference is self-contradictory and different from training.**
   One real prompt (`runs/audit_v6_candidate/.../raw_generation/1791229351696389800.json`) asks for
   three different visual systems at once; 0/39 training rows use that prompt format.
3. **The section planner and design planner are keyword heuristics that ignore or invert the user's
   request** (negations add sections; every un-keyworded site gets the identical design plan).
4. **Every quality gate measures plumbing, not quality.** The development gate forbids fonts, images,
   SVG, and caps output at 1,500 tokens; the benchmark scores vacuous checks as 1.0.

---

## P0 — Blocks professional output

### 1. Untuned base model is what users get
- `server/app.py:45-78` only accepts a promotion with `gate_status == "PASSED"`; the pointer is
  `BLOCKED`, so `MODEL_PATH` = `base-model` (raw Qwen3-4B).
- The latest candidate (`runs/audit_v6_candidate/workflow_state.json`): 39 train rows, 38 validation
  rows, `learning_rate 2e-05`, 2 epochs, grad-accum 4 → ~20 steps. Loss oscillates 0.28↔1.58
  (`runs/audit_v6_candidate_training.log`). For LoRA r=16 this LR/step count is ~10× too small
  (typical: 1e-4–2e-4, hundreds of steps).
- 21 of 39 rows come from 3 site families (`forma` 9, `paperkite` 7, `quiethours` 5).
- Validation set (38) ≈ training set (39): half the reviewed data is unused for learning.

### 2. Training data does not match the inference prompt (verified)
- 0/39 rows in `data/generation_mix_v5/train.jsonl` contain the `=== STRUCTURED DESIGN PLAN ===` /
  `<content_brief>` format the agent actually sends (`agent/agent.py:2287-2298`). Training user
  messages median 657 chars; real inference prompts are ~15.7k chars / ~4k tokens.
- The default pipeline (`scripts/train_all.bat`, `slm.py pipeline`) trains on
  `data/training_data.jsonl`, where **0/251** rows use the current system prompt and 10 rows
  (106–115) have no system message at all.

### 3. Contradictory design directives in a single prompt (verified from logged prompt)
For "Aster & Kiln ceramics… warm editorial photography, clay textures":
| Source | Palette / mode | Fonts | Layout | Imagery |
|---|---|---|---|---|
| Design plan genome | graphite-cobalt, **dark** | Syne / Manrope | split-stage, full_bleed_visual | photography-bleed |
| Brief layout | — | — | editorial | **"no photo available"** |
| Style preset | **black/white/red** (Monopo agency) | Roobert / Raleway | — | — |
| User | warm, clay | — | collection-led | editorial photography |

A 4B model cannot reconcile four art directions. Causes:
- `agent/site_brief.py:2164` — the single word "editorial" anywhere in the prompt forces the
  Refero/Monopo black-white-red preset, overriding the user's colour words.
- `agent/design_plan.py:352` — `"stage" in raw_prompt` is a substring test ("backstage", "stages").
- Design plan, brief archetype, and style preset are chosen by three independent selectors.
- Preset type scale copied from a reference site (`--text-display: 225px`,
  `--leading-heading-lg: 0.76`) is unusable as a general system.

### 4. Every workbench site gets the same design plan (verified)
`server/app.py:3457` always passes `orig_idx=0`; `synthesize_design_plan` round-robins on
`task_index` (`agent/design_plan.py:364-376`). Bakery, yoga studio and law firm prompts all produce
`split / graphite-cobalt / Syne`.

### 5. Section planner ignores requested sections and inverts negations (verified)
`agent/site_brief.py:1392` `extract_sections_from_prompt`:
| Prompt | Result |
|---|---|
| "…glaze stories, product detail, care guide and studio notes… checkout-unavailable" | header, hero, products, cart, **checkout**, collections, footer — all four requested sections dropped; checkout added |
| SaaS, "Do not show pricing… Include a product preview" | adds **pricing** and **testimonials** ("preview" contains "review") |
| Restaurant, "We do not take reservations and have no contact form" | adds **contact** and **booking** |

Adding testimonials the user didn't ask for pushes the model to fabricate them.

### 6. Sections are generated blind to each other
`start_section_context` (`agent/agent.py:2337`) resets history to system + brief + list of accepted
section *names*. The model never sees earlier sections' markup, class names, colours or ids, so
the header links to sections that were later blocked (holdout_01 header links `#products`, which
was never written), and visual language drifts section to section.

### 7. Missing sections ship silently
In `visual_holdout_01` the store's **Products and Cart were blocked** (parser errors / truncation),
yet the site shipped with Hero → Checkout → Collections. `App.tsx` assembly also renders a red
"⚠️ Section has no valid React export" box for broken modules — a debug UI inside a customer site.

### 8. "Passing" output is not a website
The latest passing native gate (`runs/native_gate_audit_fixes_20261006/`) produced 700–970 token
sites: `font-family: sans-serif`, two list items, a nav link labelled "Hero", and prompt
instructions leaking into copy ("Commission enquiries welcome. No invented address."). The store
screenshot shows the nav bar overlapping the "Cart" heading — and it still passed, because
`scripts/native_site_gate.py` checks ids, copy fragments, overflow and a click counter only.
The gate prompt itself forbids fonts, images, SVG and libraries and caps output at 1,500 tokens,
so it cannot measure professional quality.

---

## P1 — Bugs that degrade output or falsify results

9. **Fabricated validation in the agent** (likely) — `agent/agent.py:3030-3044`: when
   `src/App.tsx` is absent (the agent never writes it), validation is synthesised with
   `motion_passed=True`, `build_passed=ts_ok`, and `interaction_passed`/`preview_running` derived
   from tsc. `visual_validation.score` becomes 5.0 if that passes. No browser ran.
10. **Benchmark scores vacuous checks as perfect** (verified on `candidate_heldout.progress.json`):
    - `score_prompt_fidelity` returns 1.0 for keyword coverage when the spec has no keywords
      (`evaluation/site_benchmark_scorer.py:258`) — holdout_01 shows `matched [] / total []` → 1.0.
    - `score_required_section_completion` returns 1.0 when the spec lists no sections (line 284) —
      holdout_01 scored 1.0 with Products and Cart missing.
    - `score_visual_structure` starts at 1.0 and gives full credit if CSS contains the word
      "container" or "wrapper".
    - `score_content_quality` is word count / 150; "Sample Vessel" ×3 and `via.placeholder.com`
      images score 1.0.
    - `score_design_diversity` on a single site rewards more colours, more variables, and
      `box-shadow` — penalising presets that forbid shadows.
11. **Visual judge penalises good minimal design** — `agent/visual_judge.py:104-108` subtracts 3
    points when >85 % of pixels are near-white, i.e. airy professional layouts look "blank". It
    cannot detect broken images, overlaps, or poor hierarchy.
12. **CSS auto-synthesis restyles the whole site** — `synthesize_section_css`
    (`agent/agent.py:1560`) emits global selectors `section`, `section > div`, `h1, h2`,
    `[class*='grid']` with a dark background and white text, and defaults to the Monopo colours
    even with no style spec. One fallback section repaints every other section.
13. **Radius auto-adapt destroys buttons** (verified) — `agent/agent.py:~2690` replaces every
    `border-radius` 4–74px with the *card* radius, so pill buttons become square, contradicting the
    preset rule the fix is enforcing.
14. **Duplicate module imports split global state** (verified) — `agent/agent.py:56-58` puts
    `agent/` on `sys.path` and imports `agent_protocol`, while other modules import
    `agent.agent_protocol`. They are different module objects: the tokenizer registered by the
    runner is invisible to `agent.config.count_tokens`/`format_chatml`, which silently fall back to
    the legacy Qwen2.5 ChatML template (no empty `<think>` block) wherever no tokenizer is passed
    explicitly. Same split for `style_ingest`.
15. **Sampling settings fight Qwen3** — temperature 0.2–0.25 with repetition_penalty 1.05–1.10
    (`agent/agent.py:420-421`, `2447`). Qwen3 non-thinking guidance is ~0.7/top-p 0.8; low temp
    + repetition penalty on code penalises legitimately repeated tokens (`className`, selectors) and
    is a known cause of malformed JSX/CSS at small scale.
16. **Too few turns to repair** — server uses `max(len(sections)+4, 10)` turns; with 7 sections
    that's 3 repairs for the whole site, and `effective_cap` drops to 1 once turns ≤ sections left.
    Per-section output budget is 1,600–2,200 tokens (`output_budget.py`), tight for a rich section.
17. **System prompt pushes toward minimal output** — "keep it concise", "keep styling concise:
    prefer a scoped root class", ~1,200 tokens of prohibitions, and a 5-line Arial/Georgia example
    that the model imitates. It also references `var(--on-accent)`, which is not in the token list
    shown to the model.
18. **Header instruction forces a dark-mode toggle** in practice: the base Header text says "if
    requested", but the model emits a toggle that only changes its label (holdout_01 `Header.tsx`).
    No check catches non-functional toggles.
19. **Content integrity not enforced on images/checkout** — holdout_01 shipped
    `https://via.placeholder.com` images (broken at runtime), and a "Submit Order" form with Credit
    Card/PayPal despite "honest checkout-unavailable messaging". Acceptance (`site_acceptance.py`)
    has no positive design checks and no placeholder-image check.
20. **Global reset hurts generated layouts** — `server/app.py:1665` injects
    `* { margin:0; padding:0 }` and a default `body { background:#000; color:#fff }` when
    `--bg-color` is unset, so sections without explicit spacing collapse and light sections sit on
    a black page.
21. **Font mismatch** — `index.html` loads the brief's fonts (`server/app.py:1678`) while the design
    plan tells the model to use Syne/Manrope; preset fonts like Roobert aren't on Google Fonts, so
    pages fall back to system fonts.

## P2 — Setup, docs, and hygiene

22. **Fresh install is broken** — `scripts/setup.sh:15-24` downloads **Qwen2.5-Coder-3B**, but the
    runtime requires Qwen3 (`agent/agent.py:368-370` raises "Model weights do not match the Qwen3
    architecture").
23. **README is wrong about the model** — claims Qwen2.5-Coder-3B and a shipped adapter in
    `my-react-agent-lora/`; that adapter is a Qwen2 adapter (`auto_mapping.base_model_class:
    Qwen2ForCausalLM`) incompatible with the Qwen3 `base-model/`.
24. **Dead code** — `rewrite_fallback_sections` (`agent/agent.py:1903`) is never called;
    `from site_brief import brief_to_xml` (`agent/agent.py:2171`) is imported and unused.
25. **Repository weight** — 20+ model/candidate directories, dozens of `runs/*workspace*` folders,
    and 1.4 MB trajectory files at the root; ~60 untracked files in `git status`.
26. **Test suite** — see the "Test results" section below.

---

## What would move quality the most (in order)

1. **Fix the planners before touching the model.** Honour explicit and implicit section requests;
   handle negation; seed design choices from a hash of the prompt (not `orig_idx`); pick *one* art
   direction and pass one coherent token set. Drop the design-plan genome when a preset or user
   palette exists.
2. **Give each section context of what exists**: the shared token block, the list of real section
   ids, and the class names/hero structure already written.
3. **Make gates measure quality**: placeholder/broken-image detection, overlap detection
   (element bounding boxes), required sections from the planner fed into the scorer, no
   vacuous 1.0s, and a real visual rubric (an LLM/VLM judge or human review) instead of pixel
   variance.
4. **Retrain with matching prompts**: build SFT rows in the exact inference format, hundreds to
   thousands of reviewed sections across many families, lr ~1e-4, and a held-out set of ~10–15 %.
5. **Use Qwen3's recommended sampling** (temp ~0.7, top-p 0.8, top-k 20, no repetition penalty for
   code) and give each section a larger budget with an extra repair turn.
6. Fix setup/README so a clean checkout actually runs.

## Test results

`python -m pytest tests --ignore=tests/e2e` → **25 failed, 905 passed** (6 min 37 s).

| Area | Failing tests | What it means |
|---|---|---|
| Auto-scaffold / site state | `test_auto_scaffold_repair.py` (3), `test_site_state_model.py` (2), `test_recovery_metrics.py` (1) | Tests still expect fallback scaffolding that the loop no longer does (it now blocks sections); `rewrite_fallback_sections` is dead code |
| Context length | `test_context_decision.py` (5) | Context-length selection no longer matches the benchmark-report contract |
| Promotion / benchmark gates | `test_full_website_benchmark.py` (3), `test_diversity_evaluator.py`, `test_interactive_curriculum.py` | Gate now fails closed on a mandatory `mock` field; tests weren't updated, so gate behaviour is unverified |
| Training preflight | `test_training_preflight.py` (2), `test_training_methodology.py`, `test_retrain_qwen3_scratch.py`, `test_execute_qwen3_migration.py` | Preflight/CLI contract changed under the tests |
| Docs export | `test_doc_export_integrity.py` (2) | `docs/architecture_and_source.md` no longer matches `server/app.py` |
| Other | `test_p1_quality_contracts.py::test_manifest_preserves_supplied_facts_and_cart_contract`, `test_runtime_hardening.py::test_timeout_retains_model_ownership_until_generation_exits` | Supplied facts / cart contract not preserved in the manifest; model ownership on timeout regressed |

Note: the 905 passing tests are mostly unit/contract tests with mock runners. None of them measure
whether a generated site looks professional.
