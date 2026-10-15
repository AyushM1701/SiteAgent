# SiteAgent quality audit — 2026-09-25

## Scope and evidence

This is a read-only engineering and product audit of the current workspace. It examines model selection, candidate training data, site planning and generation, repair, motion and 3D validation, benchmark scoring, and the React workbench. It does not claim a new model has been trained or promoted.

Checks performed:

- Frontend `npm run build`: TypeScript and Vite passed. Vite reported a 606.56 kB minified JavaScript entry chunk.
- Focused Python suites for site planning, 3D, motion, benchmark, and model fingerprinting: 91 passed.
- Live workbench at `http://127.0.0.1:5000/`: desktop 1440×900 and mobile 390×844 loaded without page errors or horizontal document overflow. Screenshots: `runs/audit_ui/desktop.png` and `runs/audit_ui/mobile.png`.
- Existing live model runs: `runs/cross_domain_portfolio_updated.json` failed at 0.6589; `runs/cross_domain_ecommerce_smoke.json` failed at 0.7855. The ecommerce saved workspace passed after deterministic project repair and rescored at 0.883 in `runs/cross_domain_ecommerce_postrepair.json`. These are one site each, not a statistical estimate.
- `runs/full_website_benchmark_report.json` reports 36/36 passes but identifies `mock: true` and `model: mock-runner`; this does not measure live model quality.

## P0: release and trust blockers

### 1. The promoted motion adapter is incompatible with the current base

`models/promoted_model.json` points to `models/qwen3-siteagent-motion-r16` and claims passed gates. Its first MLP down-projection LoRA A tensor has shape `[16, 11008]`, whereas the current `base-model/config.json` is Qwen3 with intermediate size 9728. `verify_lora_adapter_compatibility` rejects the adapter. The compatible `models/qwen3-siteagent-authentic-r16-candidate` has `[16, 9728]`, but has not passed a broad promotion gate. `server/app.py` currently skips incompatible defaults and falls back to the base model. The running server, started 2026-09-20, still reports the motion adapter as ready, so its in-memory state and the current on-disk selection logic are divergent.

**Action:** remove the invalid promotion claim; expose actual loaded base/adapter fingerprints and compatibility in `/api/status`; only promote a candidate after live held-out tests for completion, fidelity, interaction, visual quality, motion, and 3D. Restart the single model-owning process only after selecting a verified compatible target. Keep candidate and historical adapters untouched.

### 2. Mock passes and repaired passes can obscure native model weakness

The 36-site 100% benchmark is mock output. In the live portfolio run, final TypeScript, runtime, and section-completion gates failed. In the live ecommerce run, the model natively completed only 2 of 5 sections; the saved site later passed because the shop pair and navigation were repaired. The benchmark tracks native/repaired/fallback counts, but high composite scores can still be mistaken for model-native performance.

**Action:** publish separate scorecards for model-native output, deterministic repair, model repair, and final rendered site. Require every promotion report to display all four and its provenance. Keep mock runs in a separate dashboard from live model evaluations.

### 3. The 3D gate can pass a site with no 3D content

`agent/project_validator.py` checks for an R3F import or `<canvas` when the brief requests 3D, then uses `evaluation/three_d_performance_validator.py`. An isolated probe with `export default function Hero(){return <canvas />;}` passed all six performance checks. The checks are useful static limits, but do not establish that WebGL initialized, a scene rendered, the requested object exists, animation works, or the fallback appears when WebGL is unavailable.

**Action:** require a visible scene contract (canvas + drawable mesh/model or explicit CSS 3D composition), browser evidence of rendered pixels and no WebGL errors, context-loss/fallback checks, and a short captured motion timeline. Test mobile and reduced motion. Report static 3D policy separately from runtime 3D success.

## P1: model capability and output quality

### 4. Training coverage is uneven for the stated general website goal

The authentic Qwen3 candidate manifest uses `data/quality_v3/train.jsonl` with 787 rows and 220 family IDs. Of the 682 rows with explicit `<business_type>` tags, only 11 are portfolio and 13 ecommerce; SaaS has 35, and technology-adjacent types recur across fintech, database, cybersecurity, cloud, and AI. A text scan found 44 prompts with explicit 3D terms and five with `parallax`. The separately prepared motion curriculum contains 36 training rows and 12 evaluation rows, but the authentic candidate manifest does not name that curriculum. These counts are coverage signals, not quality scores.

**Action:** build reviewed full-site examples across stores, portfolios, editorial, arts, civic, events, education, hospitality, healthcare, dashboards, and unfamiliar topics. Include distinct structures and assets, not palette swaps. Add complete 3D and motion trajectories with actual browser verification, plus targeted repair examples. Preserve family-level separation and record source, license, validation, and visual review for each row.

### 5. Static and pixel heuristics overstate professional quality

`evaluation/site_benchmark_scorer.py` awards visual-structure credit for generic CSS words such as grid, padding, and margin. Its design-diversity metric rewards counts of variables, colors, fonts, radii, and shadows; more colors can score better even when the palette is incoherent. Motion quality largely scores the presence of `transition`, `:hover`, keyframes, transforms, and a reduced-motion query. `agent/visual_judge.py` samples screenshot color variance and coarse regional contrast. These are useful failure detectors, but cannot judge composition, typography, information hierarchy, believable content, art direction, scroll choreography, or perceived smoothness.

**Action:** create a visually reviewed holdout set with rubric scores for layout, hierarchy, typography, content specificity, imagery/asset quality, motion timing, and mobile composition. Capture full page screenshots and short scroll videos at desktop/mobile and reduced motion. Use blinded pairwise human review for candidate promotion, with static heuristics as guardrails rather than quality claims.

### 6. Motion plans need behavioral acceptance, not just source inspection

`agent/motion_patterns.py` parses scroll reveal, parallax, horizontal scroll, sticky story, text reveal, and micro-interactions. The policy checks catch several anti-patterns, but source keywords cannot prove that animation enters at the intended time, remains readable before JavaScript, preserves focus, or stops offscreen. Motion examples should include page-specific timing and fallbacks rather than repeated generic snippets.

**Action:** add browser probes that scroll by controlled increments and assert before/after transform/opacity/position, inspect frame timing/jank, repeat under `prefers-reduced-motion`, and test keyboard focus. For 3D, sample frame rate and memory with inference running on the same GPU.

### 7. Prompt fidelity and cross-section integration remain fragile

The live portfolio failed required section completion and project validation. The ecommerce output contained disconnected cart state, inert shop buttons, and footer links to nonexistent sections before repair. Current deterministic repair is useful but can replace substantial portions of the model's work. A source-level pass does not prove all navigation, filters, forms, and overlay controls are connected.

**Action:** have planning emit a typed requirement manifest with exact user facts, sections/routes, interactions, visual/motion constraints, and cross-section state contracts. Validate those contracts after each section and at final composition. Feed precise compiler, DOM, and interaction diagnostics into bounded repair. Do not allow a polished static page to pass while requested behavior is absent.

## P1: workbench UI and UX

### 8. The default mode conflicts with the product goal

`frontend/src/components/chat/ChatComposer.tsx` initializes generation mode to `component`. The Full Site switch is inside hidden Advanced Controls, while the empty-state chips say “Build a portfolio” and “Create a 3D site.” A user can reasonably expect those prompts to build websites but receive a component task.

**Action:** make Full Site the visible default for website prompts, or auto-detect site intent and display the chosen mode before sending. Keep Component as an explicit visible option. Starter prompts should cover more domains and should not imply a real checkout without payment integration.

### 9. Mobile opens with navigation covering the task

`frontend/src/state/workspace-store.ts` sets `sidebarOpen: true` at every viewport. The mobile screenshot shows the 256 px sidebar and backdrop covering most of a 390 px screen on initial load. The main composer is partially obscured until the user finds the top-left toggle.

**Action:** initialize the sidebar closed below the desktop breakpoint, preserve user preference per viewport, label the toggle for screen readers, and make the backdrop dismissible by Escape. Keep the composer visible on the first mobile visit.

### 10. Project recency labels are wrong; project rows are not keyboard targets

The API returns timestamps such as `2026-09-23 21:22:28`. `ProjectItem.tsx` applies `Number(timestamp) || Date.now()`, so nonnumeric timestamps display “Updated Just now.” The live sidebar showed this for multiple older projects. Each project row is a clickable `<div>` without keyboard semantics. Its delete button is hidden by opacity until hover, so keyboard users lack a clear affordance.

**Action:** parse ISO/date strings explicitly and handle invalid timestamps as unknown. Make the project title a button, keep delete as a separate button, and show delete on keyboard focus. Add readable date/tooltips and avoid exposing raw session IDs as the dominant subtitle.

### 11. Status and context indicators present estimates as facts

`frontend/src/app/App.tsx` sets `gpuReady: true` on any successful status response without a GPU readiness field. `InspectorDrawer.tsx` synthesizes a context-token count from characters and clamps it to at least 920, then displays it alongside authoritative metrics. The top bar can show “Motion Verified” from gate status even though behavioral motion is not measured. These labels can mislead users during model diagnosis.

**Action:** use explicit `verified`, `estimated`, and `unknown` states. Read GPU readiness from backend telemetry; omit unknown values. Label the context estimate and replace it with actual tokenizer counts when available. Rename motion status to “Motion checks passed” until browser motion verification exists.

### 12. The preview and editor can load faster and guide the user better

The initial desktop screen has a large empty center, while the preview workspace is closed by default. Vite reports a 606.56 kB entry chunk; `WorkspacePanel` imports Monaco/code, diff, logs, and terminal views up front. The preview toolbar has desktop/tablet/mobile widths but does not surface checked viewport dimensions, console errors, reduced-motion state, or validation results next to the preview.

**Action:** lazy-load Monaco and terminal tabs, open preview automatically after a site build, and keep a visible build-status summary. Use the empty state to collect topic, audience, pages, content, desired visual style, 3D/motion preference, and real assets. Add a compact preview diagnostics drawer for console, broken links, interaction checks, viewport, and reduced-motion results.

## Recommended execution order

1. **Trust first:** invalidate the incompatible promotion pointer, establish actual loaded model identity, and keep mock/live/native/repaired scores separate.
2. **Acceptance first:** add semantic 3D, motion, and cross-section interaction browser checks; make visual review and provenance mandatory for promotion.
3. **Data then training:** curate diverse independent full sites and repair trajectories, verify every record, keep holdout families disjoint, and train an isolated compatible candidate.
4. **Compare before promotion:** run the same unseen prompts on current base and candidate, measuring native completion, final pass, prompt fidelity, 3D/motion behavior, latency, GPU memory, and blinded visual preference.
5. **Workbench UX:** make full-site intent visible, fix mobile navigation and time labels, distinguish estimated from verified status, and prioritize preview plus diagnostics.

## Limits of this audit

No new live 3D or motion website was generated in this scan; those capabilities are assessed from source, tests, existing runs, and the empty-canvas probe. The two cited live cross-domain runs are too small to estimate general pass rates. The running server was not restarted or interrupted; its in-memory model identity requires a controlled restart and fingerprint check.
