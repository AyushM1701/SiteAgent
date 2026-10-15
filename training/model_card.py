"""Write factual local candidate cards instead of the empty PEFT template."""
def write_candidate_card(export_dir, manifest):
    from pathlib import Path
    output = Path(export_dir)
    metrics = manifest.get('evaluation_metrics', {})
    runtime = manifest.get('training_metrics', {}).get('train_runtime', 0)
    text = f'''---
base_model: Qwen/Qwen3-4B
library_name: peft
pipeline_tag: text-generation
tags:
- lora
- sft
---

# {output.name}

Local candidate adapter for React, TypeScript and CSS agent generation. This is an experimental checkpoint; it is not automatically promoted to the workbench.

## Training

- Base architecture: Qwen3-4B; 4-bit QLoRA.
- Initialization adapter: `{manifest.get('initial_adapter')}`.
- Training records: {manifest.get('train_rows')}; validation records: {manifest.get('validation_rows')}.
- LoRA rank: {manifest.get('rank')}; alpha: {manifest.get('lora_alpha')}; dropout: {manifest.get('lora_dropout')}.
- Learning rate: {manifest.get('learning_rate')}; optimizer steps: {manifest.get('global_step')}.
- Context limit: {manifest.get('max_seq_length')} tokens; assistant-only loss, no target truncation.
- GPU: {manifest.get('gpu')}; peak allocated memory: {manifest.get('peak_gpu_allocated_bytes',0)/1024**3:.2f} GiB.
- Training runtime: {runtime/60:.1f} minutes, excluding model loading and final export evaluation.

## Data and evaluation

Dataset path: `{manifest.get('dataset_path')}`. Dataset SHA-256: `{manifest.get('dataset_sha256')}`.
The data mix retains replay examples and adds original reference-inspired website sections and synthetic repairs. Related site sections use family IDs to keep validation separate. The older replay data is not uniformly visually reviewed.

Final validation loss: **{metrics.get('eval_loss', 'not measured')}**. Validation loss measures prediction of supplied answers; it is not a website quality score or a task pass rate. Compile, interaction and visual comparisons are required before promotion. No new 153-task benchmark result is claimed.

## Limitations

The small model can still emit malformed file envelopes, truncate code, mishandle TypeScript generics or implement interactions incorrectly. Dimensional training examples use lightweight CSS artwork; this adapter does not synthesize 3D asset files or photographs. Generated code needs validation before use.

## Provenance

Adapter SHA-256: `{manifest.get('adapter_sha256')}`.
See `training_manifest.json` for exact library versions, data/tokenizer hashes, initialization, checkpoint selection and metrics. The parent model's licensing terms continue to apply; no new license grant is asserted here.
'''
    (output/'README.md').write_text(text, encoding='utf-8')
