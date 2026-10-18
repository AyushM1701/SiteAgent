#!/usr/bin/env bash
# ==============================================================================
# SiteAgent - one-command setup (macOS, Linux, Git Bash on Windows)
#   bash scripts/setup.sh [--cpu] [--skip-model] [--adapter USER/REPO]
# Creates .venv, installs PyTorch for your hardware and everything else, builds the
# workbench UI, downloads Qwen3-4B and runs the doctor.
# ==============================================================================
set -euo pipefail
cd "$(dirname "$0")/.."

PY="${PYTHON:-}"
if [ -z "$PY" ]; then
  for candidate in python3.12 python3.11 python3.13 python3.10 python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then PY="$candidate"; break; fi
  done
fi
[ -n "$PY" ] || { echo "Python 3.10-3.13 is required."; exit 1; }

if [ ! -d .venv ]; then
  echo "Creating virtual environment in .venv with $PY"
  "$PY" -m venv .venv
fi
if [ -f .venv/bin/python ]; then VENV_PY=.venv/bin/python; else VENV_PY=.venv/Scripts/python.exe; fi

"$VENV_PY" scripts/install.py "$@"
echo
echo "Start the workbench:  bash scripts/run_web_ui.sh"
