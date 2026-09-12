#!/usr/bin/env bash
# ==============================================================================
# ReactAgent SLM - One-Command Web UI Workbench Launcher
# Launches Flask SSE server + Isolated PTY shell runner and opens browser
# ==============================================================================
set -euo pipefail

cd "$(dirname "$0")/.."

echo "Starting ReactAgent SLM Workbench at http://127.0.0.1:5000..."
python server/app.py "$@"
