@echo off
REM ==============================================================================
REM SiteAgent - start the workbench at http://127.0.0.1:5000
REM   scripts\run_web_ui.bat            design kit (fast; the model writes the copy)
REM   scripts\run_web_ui.bat --native   the model writes each section's code too
REM                                     (needs a native adapter in models\)
REM ==============================================================================
setlocal enabledelayedexpansion
cd /d "%~dp0.."

set "PY=python"
if exist .venv\Scripts\python.exe set "PY=.venv\Scripts\python.exe"

if /i "%~1"=="--native" (
    set "ADAPTER="
    for /f "delims=" %%d in ('dir /b /ad /o:n models\*native* 2^>nul') do set "ADAPTER=models\%%d"
    if "!ADAPTER!"=="" (
        echo No native adapter in models\. Download one with: python scripts\download_models.py --adapter USER/REPO
        exit /b 1
    )
    set "MODEL_PATH=!ADAPTER!"
    set "SITE_STRATEGY=native"
    echo Using adapter !ADAPTER! ^(native mode^)
)

echo Starting SiteAgent workbench at http://127.0.0.1:5000 ...
"%PY%" server\app.py
