@echo off
REM ==============================================================================
REM SiteAgent - one-command setup (Windows)
REM   scripts\setup.bat [--cpu] [--skip-model] [--adapter AyushM1701/siteagent-native-qwen3-4b]
REM Creates .venv, installs PyTorch for your hardware and everything else, builds the
REM workbench UI, downloads Qwen3-4B and runs the doctor.
REM ==============================================================================
setlocal
cd /d "%~dp0.."

where py >nul 2>nul
if %errorlevel%==0 (set "PY=py -3") else (set "PY=python")

if not exist .venv\Scripts\python.exe (
    echo Creating virtual environment in .venv
    %PY% -m venv .venv
    if errorlevel 1 (
        echo [Error] Could not create a virtual environment. Install Python 3.10-3.13 from python.org.
        exit /b 1
    )
)

.venv\Scripts\python.exe scripts\install.py %*
if errorlevel 1 exit /b %errorlevel%

echo.
echo Start the workbench:  scripts\run_web_ui.bat
