# Standard Model Comparison Report (Section 32)

Generated during Issue #31 Full Migration Sequence.

## Head-to-Head Comparison Table

| Metric | Qwen2.5 Old LoRA | Qwen3 Base | Qwen3 SFT (R16) | Qwen3 SFT + DPO |
|---|---:|---:|---:|---:|
| 1-shot / 153 | 39.2% | 0.0% | N/A — not evaluated | N/A — not evaluated |
| Agentic / 153 | 51.0% | 20.0% | 13.3% | N/A — not evaluated |
| Interaction (`tsc_render_interact`) | 36.0% | 16.7% | 33.3% | N/A — not evaluated |
| TSC-only | 49.0% | 0.0% | 0.0% | N/A — not evaluated |
| Site build pass | 85.0% | N/A — not evaluated | N/A — not evaluated | N/A — not evaluated |
| Site runtime pass | 80.0% | N/A — not evaluated | N/A — not evaluated | N/A — not evaluated |
| Prompt fidelity | 0.680 | N/A — not evaluated | N/A — not evaluated | N/A — not evaluated |
| Median visual score | 0.750 | N/A — not evaluated | N/A — not evaluated | N/A — not evaluated |
| Design diversity | 0.280 | N/A — not evaluated | N/A — not evaluated | N/A — not evaluated |
| Auto-recovery rate | 45.0% | N/A — not evaluated | N/A — not evaluated | N/A — not evaluated |
| Avg repair attempts | 2.1 | 3.800 | N/A — not evaluated | N/A — not evaluated |
| Avg generation time | 85.2s | N/A — not evaluated | N/A — not evaluated | N/A — not evaluated |
| Time to first activity | 3.2s | N/A — not evaluated | N/A — not evaluated | N/A — not evaluated |
| Time to preview | 18.5s | N/A — not evaluated | N/A — not evaluated | N/A — not evaluated |
| Peak VRAM | 3.1 GiB | N/A — not evaluated | N/A — not evaluated | N/A — not evaluated |
| Context length | 2048 | 8192 | 8192 | N/A — not evaluated |

---

## Promotion Decision Summary
- **Promotion Status:** `MOCK HARNESS - NOT PROMOTABLE`
- **Site evidence:** `synthetic_mock` / `unknown`

| Outcome stage | Passed | Evaluated |
|---|---:|---:|
| model_native | 0 | 0 |
| deterministic_repair | 0 | 0 |
| model_repair | 0 | 0 |
| final_rendered_site | 0 | 0 |

- **Reasoning:**
  - [PASS] Interaction category pass rate improved/maintained (delta: +16.7%).
  - [PASS] Overall pass rate is 13.3%.
  - [PASS] Site benchmark composite score 0.927 meets minimum threshold 0.700.
  - [PASS] Site benchmark production build rate 100.0% meets threshold 80.0%.
  - [PASS] Site benchmark runtime pass rate 100.0% meets threshold 75.0%.
  - [PASS] Site benchmark section completion rate 100.0% meets threshold 85.0%.
  - [PASS] Site benchmark composite score maintained/improved vs baseline (0.927 >= 0.750).
  - [PASS] Site diversity score 0.306 meets minimum threshold 0.300.
  - [PASS] Auto-scaffold fallback usage rate 0.0% is within allowable threshold (25.0%).
