@echo off
REM ==============================================================================
REM ReactAgent SLM - One-Command Web UI Workbench Launcher (Windows)
REM Launches Flask SSE server + Isolated PTY shell runner and opens browser
REM ==============================================================================
setlocal enabledelayedexpansion

cd /d "%~dp0.."

echo Starting ReactAgent SLM Workbench at http://127.0.0.1:5000...
python server\app.py %*
pause
