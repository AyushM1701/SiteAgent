#!/usr/bin/env bash
# ==============================================================================
# SiteAgent - start the workbench at http://127.0.0.1:5000
#   bash scripts/run_web_ui.sh            design kit (fast; the model writes the copy)
#   bash scripts/run_web_ui.sh --native   the model writes each section's code too
#                                          (needs a native adapter in models/)
# ==============================================================================
set -euo pipefail
cd "$(dirname "$0")/.."

if [ -f .venv/bin/python ]; then PY=.venv/bin/python
elif [ -f .venv/Scripts/python.exe ]; then PY=.venv/Scripts/python.exe
else PY=python; fi

if [ "${1:-}" = "--native" ]; then
  shift
  ADAPTER="$(ls -d models/*native* 2>/dev/null | sort | tail -n 1 || true)"
  if [ -z "$ADAPTER" ]; then
    echo "No native adapter in models/. Download one with: python scripts/download_models.py --adapter USER/REPO"
    exit 1
  fi
  export MODEL_PATH="$ADAPTER" SITE_STRATEGY=native
  echo "Using adapter $ADAPTER (native mode)"
fi

echo "Starting SiteAgent workbench at http://127.0.0.1:5000 ..."
"$PY" server/app.py "$@"
