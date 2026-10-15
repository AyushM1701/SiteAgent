#!/usr/bin/env bash
# ==============================================================================
# ReactAgent SLM - One-Command Environment Setup
# ==============================================================================
set -euo pipefail

cd "$(dirname "$0")/.."

echo "=== 1/3: Installing Python Dependencies ==="
pip install -r requirements.txt

echo "=== 2/3: Installing Node.js & Testing Harness Dependencies ==="
npm install

echo "=== 3/3: Downloading Qwen3-4B Base Model ==="
python -c "
from huggingface_hub import snapshot_download
import os

target_dir = 'base-model'
if not os.path.exists(target_dir) or len(os.listdir(target_dir)) == 0:
    print('Downloading Qwen/Qwen3-4B to ./base-model...')
    snapshot_download(
        'Qwen/Qwen3-4B',
        local_dir=target_dir,
        ignore_patterns=['*.msgpack', '*.h5']
    )
    print('Download complete!')
else:
    print(f'{target_dir} already exists. Skipping download.')
"

echo "Setup complete! Run 'bash scripts/run_web_ui.sh' to launch the web workbench."
