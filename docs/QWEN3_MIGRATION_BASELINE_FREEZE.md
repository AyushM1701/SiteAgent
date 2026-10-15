# Qwen3 Migration Baseline Freeze (Step A)

**Generated:** 2026-10-16 01:35:59  
**Git Commit:** `7e7bee321923f2a7059fb4cbc5ca3ee0d40e0ce8`

---

## 1. Historical Qwen2.5 Baseline Adapter
- **Base Model:** `Qwen/Qwen2.5-Coder-3B-Instruct`
- **PEFT Architecture:** LoRA (rank=16, alpha=16, dropout=0.0)
- **Historical Context Length:** 2048 tokens
- **Target Modules:** `q_proj, k_proj, v_proj, o_proj, gate_proj, up_proj, down_proj`

---

## 2. Historical 153-Task Agentic Benchmark (51.0%)
| Metric | Tasks Passed | Pass Rate |
|---|---:|---:|
| 1-Shot First-Turn | 60 / 153 | **39.2%** |
| Agentic Final Pass | 78 / 153 | **51.0%** |
| Interaction (`tsc_render_interact`) | 18 / 50 | **36.0%** |
| TSC-Only (`tsc_only`) | 25 / 51 | **49.0%** |

---

## 3. Dataset Integrity Manifest (SHA256)
| Dataset | Lines | Size (Bytes) | SHA256 Checksum |
|---|---:|---:|---|
| `data/quality_candidate/train.jsonl` | 963 | 12939959 | `53a3966ef1f053bf...` |
| `data/quality_candidate/val.jsonl` | 0 | 0 | `missing...` |
| `data/interactive_curriculum_trajectories.jsonl` | 23 | 89727 | `98cd37a8fdd463fe...` |
| `data/eval/react_ts_css_eval_set_combined.jsonl` | 153 | 101485 | `56ebf10e34b4e55a...` |
| `data/eval/premium_sites.jsonl` | 6 | 2433 | `d769e7fc3b4fe437...` |
| `data/eval/full_website_benchmark.jsonl` | 36 | 41446 | `47c794eaf1fac11c...` |
| `data/eval/sealed_final_benchmark.jsonl` | 153 | 115053 | `4a19c79ad0dfc063...` |

---

## 4. Environment Package Versions
- **Python:** `3.13.3` (Windows-11-10.0.26200-SP0)
- **PyTorch:** `2.14.0+cu130`
- **Transformers:** `5.5.0`
- **PEFT:** `0.20.0`
- **TRL:** `0.24.0`
- **Pytest:** `9.0.3`
- **Playwright:** `1.62.0`

---

## 5. Prerequisite Test Status
- **Steps 1–13 P0 Correctness:** PASSED
- **Workbench Control Audit (Issue #29):** PASSED (20/20 backend contracts)
- **Workbench Playwright E2E Suite (Issue #30):** PASSED (8/8 UI flows)
