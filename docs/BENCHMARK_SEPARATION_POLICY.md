# SiteAgent Benchmark Separation and Leakage Protection Policy

## Release evidence

The mock full-site harness writes `runs/mock_full_website_benchmark_report.json`; it is never promotion evidence. Live runs write `runs/full_website_benchmark_report.json` and include four per-site outcome stages: model-native generation, deterministic repair, model repair, and final rendered site. Each stage reports its own pass count and provenance. A passing final site does not count as a native model pass.

Promotion requires a live report with these four scorecards and per-site records. The previously promoted motion adapter has been revoked because its LoRA tensor shape is incompatible with the current Qwen3 base. The compatible candidate remains unpromoted until held-out live evaluation covers completion, prompt fidelity, interaction, visual quality, motion, and runtime 3D on desktop, mobile, and reduced-motion settings.

3D validation reports static scene/performance policy separately from browser runtime success. A bare canvas fails the scene contract. Browser evidence is written to each generated workspace as `three_d_runtime_evidence.json`, including canvas pixels, WebGL state, sampled motion frames, mobile visibility, reduced-motion visibility, and fallback visibility without WebGL.

## 1. Overview and Problem Definition

Repeatedly training or prompt-tuning against failures on a single evaluation benchmark converts the evaluation set into an implicit development set. Over time, models overfit to specific phrasing, edge cases, and test assertions of that dataset, invalidating claimed benchmark gains.

To prevent evaluation leakage and maintain true generalization, SiteAgent enforces a strict two-tier benchmark architecture:
1. **Development Benchmark** (`data/eval/dev_benchmark.jsonl`)
2. **Sealed Final Benchmark** (`data/eval/sealed_final_benchmark.jsonl`)

---

## 2. Benchmark Split Specifications

| Dimension | Development Benchmark | Sealed Final Benchmark |
| :--- | :--- | :--- |
| **Path** | `data/eval/dev_benchmark.jsonl` | `data/eval/sealed_final_benchmark.jsonl` |
| **Task Count** | 150 tasks | 153 tasks |
| **Integrity Seal** | Disjointness verified | Cryptographic SHA-256 manifest (`sealed_final_benchmark_manifest.json`) |
| **Permitted Uses** | • Daily debugging<br>• Training decisions & ablation studies<br>• Failure harvesting & repair analysis<br>• DPO pair generation<br>• Prompt engineering & system prompt tuning | • Major milestone checkpoints only<br>• Final candidate release qualification |
| **Prohibited Uses** | • Overwriting with sealed benchmark prompts | • Training on task failures<br>• DPO generation from task prompts<br>• Prompt tuning to fit specific test codes<br>• Frequent/continuous evaluation loops |
| **Evaluation Frequency** | Continuous / Per-experiment | Infrequent / Major release milestones |

---

## 3. The 6 Mandatory Leakage Checks

Every candidate dataset (training, validation, synthetic, or dev splits) must pass all 6 leakage checks fail-closed against the Sealed Final Benchmark before preflight or training can commence:

### 1. Exact Prompt Matching
- **Definition**: Direct verbatim match between candidate prompt and benchmark prompt after trimming whitespace.
- **Rule**: If `candidate_prompt.strip() == benchmark_prompt.strip()`, reject immediately.

### 2. Normalized Matching
- **Definition**: Casefolded, punctuation-stripped, and whitespace-collapsed text matching.
- **Rule**: Eliminates trivial evasion (e.g. adding a period, changing casing, or substituting double spaces).

### 3. Symbol Overlap
- **Definition**: Extraction of component names (`PascalCase`), custom hooks (`useX`), backticked identifiers (`` `X` ``), CSS classes (`styles.X`), and `data-testid` values.
- **Rule**: If candidate shares core symbols with a benchmark task AND token Jaccard similarity exceeds 0.35, the sample is flagged as an unauthorized clone of the benchmark test case.

### 4. Token Similarity
- **Definition**: Word-level Jaccard similarity over alphanumeric tokens:
  $$\text{Jaccard}(A, B) = \frac{|A \cap B|}{|A \cup B|}$$
- **Rule**: Fails if $\text{Jaccard} \ge 0.50$.

### 5. Family-Level Holdout
- **Definition**: Metadata identifiers (`family_id`, `source_task_id`, `task_id`).
- **Rule**: Tasks derived from the same source component or architectural family as a sealed benchmark item cannot appear in training or validation splits.

### 6. Semantic Similarity Checks
- **Definition**: Composite similarity measuring:
  - Word bigram Jaccard (40%)
  - Character 4-gram Jaccard (35%)
  - Word token Jaccard (25%)
- **Rule**: Detects paraphrased prompts that express the exact same specification with reordered phrasing or synonyms. Fails if composite similarity $\ge 0.65$.

---

## 4. Cryptographic Manifest & Tamper Protection

The Sealed Final Benchmark is cryptographically anchored by `data/eval/sealed_final_benchmark_manifest.json`:
- **SHA-256 Digest**: Computed over the entire raw bytes of `sealed_final_benchmark.jsonl`.
- **Task Count Integrity**: Verifies exact task count (153).
- **Per-Task Hashing**: Retains per-task prompt hashes for fine-grained tamper detection.

Any manual modification, accidental corruption, or truncation of the sealed benchmark immediately aborts training and preflight with an integrity error.

---

## 5. Verification Tooling

### CLI Audit Tool
Audit any candidate training, validation, or dev dataset using:
```bash
python scripts/verify_benchmark_leakage.py --dataset data/training_data.jsonl
```

Audit the Development Benchmark:
```bash
python scripts/verify_benchmark_leakage.py --dataset data/eval/dev_benchmark.jsonl
```

### Preflight Integration
During SFT training (`python -m training.train_sft`), `check_benchmark_disjointness` automatically validates:
1. Manifest integrity of `sealed_final_benchmark.jsonl`
2. All 6 leakage dimensions against `sealed_final_benchmark.jsonl`
3. Disjointness against `dev_benchmark.jsonl` and `premium_sites.jsonl`
