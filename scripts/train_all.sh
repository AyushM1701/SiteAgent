#!/usr/bin/env bash
# ==============================================================================
# ReactAgent SLM - Full Training Pipeline (One Command)
# Merges all trajectory datasets -> Validates -> Runs QLoRA SFT Training
# ==============================================================================
set -euo pipefail

cd "$(dirname "$0")/.."

echo "=============================================================================="
echo " [Step 1/3] Merging all trajectory sources into data/training_data.jsonl"
echo "=============================================================================="
python data_pipeline/build_dataset.py merge --out data/training_data.jsonl

echo "=============================================================================="
echo " [Step 2/3] Validating dataset with live Vitest + TypeScript compiler"
echo "=============================================================================="
python data_pipeline/build_dataset.py validate data/training_data.jsonl --verify-only

echo "=============================================================================="
echo " [Step 3/3] Launching QLoRA SFT Fine-Tuning"
echo "=============================================================================="
python training/train_sft.py --max-seq-length 9216 --data data/training_data.jsonl "$@"

echo "Training complete! Model saved to ./my-react-agent-lora"
