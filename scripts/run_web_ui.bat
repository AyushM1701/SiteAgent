@echo off
REM ==============================================================================
REM ReactAgent SLM - One-Command Web UI Workbench Launcher (Windows)
REM Launches Flask SSE server + Isolated PTY shell runner and opens browser
REM ==============================================================================
setlocal enabledelayedexpansion

cd /d "%~dp0.."

REM User-selected local candidate; this does not grant promotion approval.
if not defined MODEL_PATH set "MODEL_PATH=%CD%\models\qwen3-siteagent-audit-v6-candidate"

echo Starting ReactAgent SLM Workbench at http://127.0.0.1:5000...
python server\app.py %*
pause
