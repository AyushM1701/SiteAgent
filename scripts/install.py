#!/usr/bin/env python3
"""One-command install for any machine. Run through scripts/setup.sh or scripts\\setup.bat,
which create the .venv first, or directly inside your own environment:

  python scripts/install.py                    # everything
  python scripts/install.py --skip-model       # no 8 GB download
  python scripts/install.py --cpu              # force the CPU build of PyTorch
  python scripts/install.py --adapter USER/REPO  # also fetch a fine-tuned adapter

Steps: PyTorch for this hardware -> Python packages -> optional NVIDIA extras ->
Node packages and the workbench UI -> Chromium for site checks -> model weights -> doctor.
"""
from __future__ import annotations

import argparse
import platform
import shutil
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
TORCH_INDEX = {
    "cuda": "https://download.pytorch.org/whl/cu126",   # NVIDIA, driver 525+ (Windows and Linux)
    "rocm": "https://download.pytorch.org/whl/rocm6.2",  # AMD on Linux
    "cpu": "https://download.pytorch.org/whl/cpu",
}


def step(title: str) -> None:
    print(f"\n=== {title} ===", flush=True)


def run(cmd: list[str], cwd: Path = BASE_DIR, optional: bool = False) -> bool:
    print("  $", " ".join(cmd), flush=True)
    exe = shutil.which(cmd[0]) or cmd[0]
    result = subprocess.run([exe, *cmd[1:]], cwd=str(cwd))
    if result.returncode != 0:
        if optional:
            print(f"  (optional step failed with exit code {result.returncode}; continuing)")
            return False
        sys.exit(f"Command failed: {' '.join(cmd)}")
    return True


def pip(*args: str, optional: bool = False) -> bool:
    return run([sys.executable, "-m", "pip", *args], optional=optional)


def detect_accelerator(force_cpu: bool) -> str:
    if force_cpu:
        return "cpu"
    if platform.system() == "Darwin":
        return "mps"
    if shutil.which("nvidia-smi") and subprocess.run(["nvidia-smi", "-L"], capture_output=True).returncode == 0:
        return "cuda"
    if platform.system() == "Linux" and (shutil.which("rocm-smi") or Path("/opt/rocm").exists()):
        return "rocm"
    return "cpu"


def torch_matches(accel: str) -> bool:
    try:
        import torch
    except ImportError:
        return False
    if accel == "cuda":
        return bool(torch.version.cuda)
    if accel == "rocm":
        return bool(getattr(torch.version, "hip", None))
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--cpu", action="store_true", help="Install the CPU build of PyTorch even if a GPU is present")
    parser.add_argument("--skip-model", action="store_true", help="Do not download model weights")
    parser.add_argument("--base", default="Qwen/Qwen3-4B", help="Base model repo (Qwen/Qwen3-1.7B for low memory)")
    parser.add_argument("--adapter", help="Hugging Face repo of a fine-tuned native adapter to download")
    parser.add_argument("--torch-index", help="Override the PyTorch wheel index URL")
    args = parser.parse_args()

    if not (3, 10) <= sys.version_info[:2] <= (3, 13):
        sys.exit(f"Python {sys.version.split()[0]} is not supported; use Python 3.10 to 3.13.")
    if not shutil.which("node") or not shutil.which("npm"):
        sys.exit("Node.js 18+ (with npm) is required: https://nodejs.org")

    accel = detect_accelerator(args.cpu)
    step(f"1/7 PyTorch for this machine ({ {'cuda': 'NVIDIA CUDA', 'rocm': 'AMD ROCm', 'mps': 'Apple Metal', 'cpu': 'CPU only'}[accel] })")
    pip("install", "--upgrade", "pip", optional=True)
    if torch_matches(accel) and not args.torch_index:
        print("  PyTorch already installed for this hardware.")
    elif accel == "mps":
        pip("install", "torch")
    else:
        pip("install", "torch", "--index-url", args.torch_index or TORCH_INDEX[accel])

    step("2/7 Python packages")
    pip("install", "-r", "requirements.txt")

    step("3/7 NVIDIA extras (4-bit loading, Unsloth)")
    if accel == "cuda":
        if not pip("install", "bitsandbytes>=0.43.0", optional=True):
            print("  bitsandbytes unavailable: the model loads in float16 (needs ~8 GB VRAM).")
        if not pip("install", "unsloth>=2024.8", optional=True):
            print("  Unsloth unavailable: inference uses Transformers instead (a little slower; training scripts need Unsloth).")
    else:
        print("  Skipped (no NVIDIA GPU).")

    step("4/7 Node packages for building generated sites")
    run(["npm", "ci"] if (BASE_DIR / "package-lock.json").exists() else ["npm", "install"])

    step("5/7 Workbench UI")
    frontend = BASE_DIR / "frontend"
    run(["npm", "ci"] if (frontend / "package-lock.json").exists() else ["npm", "install"], cwd=frontend)
    run(["npm", "run", "build"], cwd=frontend)

    step("6/7 Chromium for browser checks")
    run([sys.executable, "-m", "playwright", "install", "chromium"], optional=True)

    step("7/7 Model weights")
    if args.skip_model:
        print("  Skipped; later run: python scripts/download_models.py")
    else:
        cmd = [sys.executable, "scripts/download_models.py", "--base", args.base]
        if args.adapter:
            cmd += ["--adapter", args.adapter]
        run(cmd)

    step("Doctor")
    run([sys.executable, "scripts/doctor.py"], optional=True)


if __name__ == "__main__":
    main()
