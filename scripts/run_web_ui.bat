@echo off
REM ==============================================================================
REM ReactAgent SLM - One-Command Web UI Workbench Launcher (Windows)
REM Launches Flask SSE server + Isolated PTY shell runner and opens browser
REM ==============================================================================
setlocal enabledelayedexpansion

cd /d "%~dp0.."

REM The base Qwen3-4B model writes the site copy for the design kit by default.
REM Set MODEL_PATH yourself to try a specific (unpromoted) adapter, e.g.
REM   set "MODEL_PATH=%CD%\models\qwen3-siteagent-audit-v6-candidate"
REM Set SITE_STRATEGY=freeform to use the legacy code-writing loop.

echo Starting ReactAgent SLM Workbench at http://127.0.0.1:5000...
python server\app.py %*
pause
