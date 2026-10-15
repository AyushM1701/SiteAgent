# Website quality evidence workflow

## Promotion selection and training guards (2026-10-05)

Automatic workbench adapter selection now requires `promotion_evidence` in the promotion pointer.
Its `native_gate`, `component_benchmark`, `site_benchmark`, and `human_review` entries each contain
`path` and `sha256`. Reports must match the selected adapter. The native report must pass the current
three-domain generation path without repairs or fallbacks. Live site reports must display all four
outcome scorecards, evaluate at least 30 native sites at an 85% pass rate or better, pass the existing
promotion metrics, include passed browser motion and 3D checks, and cover the exact sites scored by
the existing two-reviewer, 12-domain blinded human gate. Labels and an architecture manifest alone
do not establish release eligibility. Missing or changed evidence selects the base model.

`--override-methodology-gate` only overrides hyperparameter policy; SFT native completion and reviewed
data admission remain mandatory. DPO now also checks the native report for its initial adapter before
GPU loading, accepts `--native-gate-report`, and refuses an existing output directory. CPU preflight
does not certify a training run or promotion. Preserve candidates and historical adapters.

Use `python -m scripts.audit_curriculum_evidence --output runs/curriculum_evidence_audit.json` to count
final supervised action types, navigation, full Main file targets, source/review metadata, and preference
receipt artifacts. Inline booleans and provenance labels are counted separately from matching files.
This inventory measures available evidence and coverage; it does not assign human visual scores.

Run `python scripts/audit_site_training_coverage.py` before preparing another adapter. The report at `runs/p1_training_coverage.json` counts rows and source families separately. The current 787-row candidate set has only three explicitly tagged portfolio families and three ecommerce families; its rows do not carry top-level source, license, validation, or human visual-review records. These are coverage and provenance findings, not scores.

New full-site trajectories belong in a separate `reviewed_full_sites` train/held-out split. Each row needs a source, license, family ID, domain, compiler/build/runtime/interaction results, browser captures at desktop/mobile/reduced motion, and a named human reviewer with scores for layout, hierarchy, typography, content specificity, imagery/assets, motion timing, and mobile composition. Repair rows also need the diagnostics that caused the repair. `training/train_sft.py` rejects a `reviewed_full_sites` dataset if these fields are missing or source families cross the split. Historical candidate and motion datasets remain untouched.

Capture a running site with `python scripts/capture_visual_review.py http://127.0.0.1:5173 runs/review/example-id`. This saves full-page screenshots, scroll videos, viewport settings, and browser errors. A reviewer must inspect the artifacts and assign scores; the capture script does not declare visual quality. `data/eval/visual_holdout_v1.jsonl` contains 30 family-disjoint briefs across 12 domains. Capture both baseline and candidate for each brief under `runs/visual_pair_sources/<task_id>/{baseline,candidate}/`, then use `scripts/blinded_visual_review.py prepare` to randomize A/B and create score forms. Keep its private mapping outside the public package. Two independent humans must score both A and B for each of the 30 sites. Only `scripts/blinded_visual_review.py assemble` should unblind completed forms into `runs/visual_review_report.json`, tied to the adapter fingerprint. Static CSS and pixel scores remain diagnostic guardrails.

For generation, the content brief now includes a typed requirement manifest with exact user facts, sections/routes, requested interactions, visual/motion constraints, and shared cart/filter state contracts. Final validation checks the manifest and uses browser interaction and motion probes for explicit requests. Use the saved `motion_runtime_evidence.json` and `three_d_runtime_evidence.json` when reviewing behavior. A new adapter should not be promoted until the held-out live website evaluation and human review both pass.

The workbench defaults to Full Site, offers an optional structured prompt for topic, audience, pages, content, style, motion/3D, and assets, and opens the preview after a site build. On mobile the sidebar starts closed and has a separate saved preference. The preview shows reported build, runtime, motion, and 3D checks; it does not yet collect live iframe console output or a reduced-motion result for every preview. The current coverage audit and browser captures are preparation for reviewed examples, not a completed reviewed training set or evidence of a better adapter.

The first full eligible training pass combined all 787 accepted quality-v3 rows with the 36 motion curriculum rows. `data/full_site_training/manifest.json` records exact source hashes, 823 rows, and family separation from the 104-row validation split. `models/qwen3-siteagent-full-v1-candidate` was trained for one epoch and passed adapter compatibility with the current base. It remains a candidate until live held-out sites and the blinded human review pass. The three original reference websites have desktop, mobile, and reduced-motion captures in `runs/reviewed_source_candidates/`; those captures are review candidates, not human-approved examples.
