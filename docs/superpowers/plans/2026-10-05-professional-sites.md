# Professional Website Generation Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Establish reliable native generation, build a generation-focused reviewed mix, expand verified design references, then train and evaluate an isolated candidate when evidence permits.

**Architecture:** Keep native output immutable and measure repairs separately. Filter historical supervision by actual final action and context, preserve family splits, and admit newly authored visual references only after browser checks and real human scores. Existing training and promotion guards remain mandatory.

**Tech Stack:** Qwen3 non-thinking, Python, React/TypeScript/CSS, Playwright, QLoRA.

**Spec:** User request in this conversation; release findings in runs/stage_h_release_decision_20261005.md.

## Global Constraints

- Native portfolio/store/unfamiliar gates must pass 3/3 without repairs before training.
- Preserve historical adapters and source datasets; new output directories only.
- Browser checks prove functionality; human scores establish reviewed visual quality.
- No fabricated reviews or verifier receipts. Promotion requires two-person blinded review.

## Review Focus

- Labels must identify real interactive controls and preserve requested accessible names.
- CSS coverage may not be waived because compilation passed.
- Finish-only targets require preceding accepted project evidence.
- Related source families may not cross train/validation/heldout boundaries.
- Pending examples may never be silently admitted as reviewed training data.

## Tasks

- [x] Clarify the common generation contract and rerun the exact native base suite; preserve logs and failures. Current evidence: runs/native_base_contract_v9/report.json, 3/3 native passes, zero repairs or fallbacks.
- [x] Add tested supervision classification and construct a new immutable generation mix, with exclusions and coverage manifest. data/generation_mix_v4_1 passed CPU preflight; expand after remaining reviews.
- [x] Expand reference sites across requested domains; verify compiler, interactions, motion, responsive and reduced-motion behavior and capture review materials. Nine references verified in three modes each.
- [x] Collect real source visual reviews and admit approved references with artifact fingerprints. All nine source references reviewed by Yash; 18 new rows admitted.
- [x] Run native/tokenizer/leakage/review gates, train a new isolated SFT candidate, and record provenance. generation_mix_v5: 39 reviewed rows across 12 families/domains, 38 validation rows; one epoch and 10 optimizer steps completed. Adapter compatibility verified. Validation loss 0.53454 before versus 0.51758 after. Candidate native/live promotion gates remain outstanding.
- [ ] Run candidate native and held-out live suites, prepare blinded A/B review, collect two humans' scores, and promote only on passed evidence.

## Current Review Progress

Yash approved Folio and Prism in the actual submitted CSV. Four complete-site/repair rows were admitted to data/reviewed_full_sites/design_v2_first_reviews.jsonl, bound to the exact reviewed sources and capture reports. The review portal resume bug was fixed and regression-tested; the remaining seven sites are available at http://127.0.0.1:8916/review_remaining.html with blank scores. Training remains pending the required remaining domain reviews. These source reviews do not replace the later two-person blinded candidate review.

Update: Remaining seven Yash reviews verified and admitted. Combined evidence: data/reviewed_full_sites/design_v2_all_reviews.jsonl and its manifest. Isolated candidate workflow started at runs/generation_v5_candidate; promotion remains pending actual candidate gates and two-person blinded review.

SFT saved to models/qwen3-siteagent-generation-v5-candidate, adapter SHA256 6243358fcf6b149e5eb491d23561ce9810d4936166426f8dd540985a7a41ce40. Current live workflow state: runs/generation_v5_candidate/workflow_state.json. No promotion or workbench model restart performed. Native evaluation is running; the workflow proceeds to candidate/base held-out benchmarks only if the candidate native development gate passes.
