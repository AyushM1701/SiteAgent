@echo off
REM ==============================================================================
REM ReactAgent SLM - Full Training Pipeline (Windows One Command)
REM Merges all trajectory datasets -> Validates -> Runs QLoRA SFT Training
REM ==============================================================================
setlocal enabledelayedexpansion

cd /d "%~dp0.."

echo ==============================================================================
echo  [Step 1/3] Merging all trajectory sources into data/training_data.jsonl
echo ==============================================================================
python data_pipeline\build_dataset.py merge --out data\training_data.jsonl
if %errorlevel% neq 0 (
    echo [Error] Dataset merge failed.
    exit /b %errorlevel%
)

echo ==============================================================================
echo  [Step 2/3] Validating dataset with live Vitest + TypeScript compiler
echo ==============================================================================
python data_pipeline\build_dataset.py validate data\training_data.jsonl --verify-only
if %errorlevel% neq 0 (
    echo [Warning] Validation detected issues. Continuing with training...
)

echo ==============================================================================
echo  [Step 3/3] Launching QLoRA SFT Fine-Tuning
echo ==============================================================================
python training\train_sft.py --max-seq-length 9216 --data data\training_data.jsonl %*
if %errorlevel% neq 0 (
    echo [Error] Training failed.
    exit /b %errorlevel%
)

echo ==============================================================================
echo Training Complete! Model saved to ./my-react-agent-lora
echo ==============================================================================
pause
