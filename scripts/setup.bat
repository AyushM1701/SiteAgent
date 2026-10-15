@echo off
REM ==============================================================================
REM ReactAgent SLM - One-Command Environment Setup (Windows)
REM ==============================================================================
setlocal enabledelayedexpansion

cd /d "%~dp0.."

echo ==============================================================================
echo [1/3] Installing Python Dependencies...
echo ==============================================================================
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [Error] Failed to install Python dependencies.
    exit /b %errorlevel%
)

echo ==============================================================================
echo [2/3] Installing Node.js and Testing Harness Dependencies...
echo ==============================================================================
call npm install
if %errorlevel% neq 0 (
    echo [Error] Failed to install npm dependencies.
    exit /b %errorlevel%
)

echo ==============================================================================
echo [3/3] Downloading Qwen3-4B Base Model...
echo ==============================================================================
python -c "from huggingface_hub import snapshot_download; import os; target='base-model'; (print('Downloading...') or snapshot_download('Qwen/Qwen3-4B', local_dir=target, ignore_patterns=['*.msgpack', '*.h5'])) if not os.path.exists(target) or len(os.listdir(target))==0 else print('Base model already present in ./base-model')"

echo ==============================================================================
echo Setup Complete!
echo Run 'scripts\run_web_ui.bat' to launch the web workbench.
echo ==============================================================================
pause
