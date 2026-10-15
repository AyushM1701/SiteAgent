---
base_model: Qwen/Qwen2.5-Coder-3B-Instruct
library_name: peft
pipeline_tag: text-generation
tags: [lora, react, typescript]
---

# ReactAgent LoRA

Adapter for React, TypeScript and CSS generation with compiler/test feedback. Generated code needs review, particularly interactive behavior and complex generic types.

## Verified export identity (September 15, 2026)

The local adapter weights match `agent_lora_output/checkpoint-46/adapter_model.safetensors` byte for byte:

```text
SHA256 82cc3d7686238c2ae2400a710eee423cd0f0baa2088f2cee255e53c1fb0dedf3
```

The export records rank 16, alpha 16, **dropout 0.0**, targeting `q_proj`, `k_proj`, `v_proj`, `o_proj`, `gate_proj`, `up_proj`, `down_proj`. The matching checkpoint records 46 steps, one epoch, batch size 1, and no validation metric or best checkpoint. This differs from the historical 96-step run below. Its exact training dataset snapshot and hardware were not preserved in a manifest and cannot be established from weights alone.

The adapter references `./base-model` (Qwen2.5-Coder-3B-Instruct). Loading requires base and adapter weights, which may be excluded from Git. CPU inference uses Transformers float32; CUDA prefers Unsloth. CPU execution requires enough RAM for the base model.

## Historical training and evaluation

[PROJECT_JOURNEY.md](../docs/PROJECT_JOURNEY.md) documents an older run: 146 trajectories, response-only loss masking, three epochs, learning rate 1e-4, 96 steps, NVIDIA RTX 4050, and best validation loss 0.3503. Its dropout=0.05 statement is historical; it does not describe the current export configuration.

The log reports 153 held-out tasks, up to five agent turns, and 16.17 hours elapsed:

| Metric | Result |
| --- | --- |
| First-turn passes | 60/153 (39.2%) |
| Additional passes after correction | 18/153 (11.8 percentage points) |
| Final passes | 78/153 (51.0%) |
| TSC + render | 30/42 (71.4%) |
| TSC + accessibility | 3/4 (75.0%) |
| TSC + interaction | 21/58 (36.2%) |
| TSC only | 24/49 (49.0%) |

These are historical log-reported results, **not a verified benchmark of checkpoint-46**. The current `docs/agent_results.json` and `docs/eval_results.json` contain mock runs of one and two tasks respectively. They cannot substantiate those scores. No fresh GPU benchmark was performed for this card.

## Limitations

The historical analysis groups 33/75 failures as unknown/multiple TypeScript errors and 8/75 as parse/syntax errors, with truncated output among the reported causes. Interactive state, event handling and ARIA targeting remain weak areas. Increasing the generation budget addresses a source of truncation; it does not establish better quality or solve generic-type reasoning.

Runtime defaults are an 8192-token context and 4096-token generation budget, configurable with `SLM_INFERENCE_MAX_SEQ_LENGTH` and `SLM_MAX_NEW_TOKENS`. Longer generations cost memory and latency. Re-evaluate the exact adapter and record its hash before making new quality claims.

## Evaluation

From the repository root with weights and Python/npm dependencies installed:

```sh
python agent/agent.py --model ./my-react-agent-lora --eval-set data/eval/react_ts_css_eval_set_combined.jsonl --max-turns 5 --no-best-of-2 --max-new-tokens 768 --max-seq-len 4096 --output docs/current_adapter_eval.json
```

This retains the historical token budget for comparison. Evaluate separately with `--max-new-tokens 4096 --max-seq-len 8192` to measure the runtime change. Preserve both outputs with the adapter and dataset hashes. No dataset licensing audit is recorded in the available training metadata.
