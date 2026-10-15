@echo off
REM ==============================================================================
REM ReactAgent SLM - Full Training Pipeline (Windows One Command)
REM Merges all trajectory datasets -> Validates -> Runs QLoRA SFT Training
REM
REM Usage:
REM   scripts\train_all.bat
REM   scripts\train_all.bat --epochs 3 --rank 32
REM
REM Required layout (set these ENV vars or edit the defaults below):
REM   SLM_OUTPUT_DIR      where the candidate adapter lands  (default: models\candidate_run)
REM   SLM_CHECKPOINT_DIR  where step checkpoints land        (default: runs\checkpoints)
REM
REM Context length:
REM   --max-seq-length is NOT passed here.  train_sft.py selects the context
REM   limit automatically from runs\qwen3_context_benchmark.json (ceiling 8192).
REM   The RTX 4050 6 GB profile forbids any value above 8192; passing 9216 would
REM   immediately raise ValueError inside the trainer.
REM ==============================================================================
setlocal enabledelayedexpansion

cd /d "%~dp0.."

REM ── Configurable output paths (override via environment variables) ─────────────
if not defined SLM_OUTPUT_DIR     set SLM_OUTPUT_DIR=models\candidate_run
if not defined SLM_CHECKPOINT_DIR set SLM_CHECKPOINT_DIR=runs\checkpoints

echo ==============================================================================
echo  [Step 1/4] Merging all trajectory sources into data\training_data.jsonl
echo ==============================================================================
python data_pipeline\build_dataset.py merge --out data\training_data.jsonl
if errorlevel 1 (
    echo [FATAL] Dataset merge failed.
    exit /b 1
)

echo ==============================================================================
echo  [Step 2/4] Stripping private reasoning blocks from raw trajectories
echo             (P1-03: removes ^<thought^>/^<think^> before validation)
echo ==============================================================================
python -m training.preflight data\training_data.jsonl data\training_data_clean.jsonl
if errorlevel 1 (
    echo [FATAL] Thought-block stripping failed.
    exit /b 1
)

echo ==============================================================================
echo  [Step 3/4] Validating dataset with live preflight contract
echo             (P1-02: validation is now FAIL-CLOSED)
echo ==============================================================================
python data_pipeline\build_dataset.py validate data\training_data_clean.jsonl --verify-only
if errorlevel 1 (
    echo [FATAL] Dataset validation failed. Fix errors before training.
    exit /b 1
)

echo ==============================================================================
echo  [Step 4/4] Launching QLoRA SFT Fine-Tuning
echo             Output:      %SLM_OUTPUT_DIR%
echo             Checkpoints: %SLM_CHECKPOINT_DIR%
echo             Data:        data\training_data_clean.jsonl  (thought-stripped)
echo             Context:     auto-selected from benchmark report (max 8192)
echo ==============================================================================
python training\train_sft.py ^
    --data data\training_data_clean.jsonl ^
    --output %SLM_OUTPUT_DIR% ^
    --checkpoint-dir %SLM_CHECKPOINT_DIR% ^
    %*
if errorlevel 1 (
    echo [FATAL] Training failed.
    exit /b 1
)

echo ==============================================================================
echo Training Complete!
echo   Candidate adapter : %SLM_OUTPUT_DIR%
echo   Run checkpoints   : %SLM_CHECKPOINT_DIR%
echo   Next step         : run the benchmark suite before promoting this adapter.
echo ==============================================================================
pause
