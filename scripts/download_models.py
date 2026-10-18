#!/usr/bin/env python3
"""Download the model weights the workbench needs.

  python scripts/download_models.py                       # Qwen/Qwen3-4B -> ./base-model
  python scripts/download_models.py --adapter USER/REPO   # also a fine-tuned adapter -> ./models/<name>
  python scripts/download_models.py --base Qwen/Qwen3-1.7B   # smaller base for low-memory machines

The fine-tuned "native" adapter only works on top of Qwen3-4B. Smaller bases run
the default kit strategy (the model writes the copy, the design kit writes the code).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def has_weights(folder: Path) -> bool:
    return (folder / "config.json").is_file() and any(folder.glob("*.safetensors"))


def download_base(repo: str, target: Path, force: bool) -> None:
    from huggingface_hub import snapshot_download
    if has_weights(target) and not force:
        config = json.loads((target / "config.json").read_text(encoding="utf-8"))
        print(f"Base model already present in {target} ({config.get('architectures', ['?'])[0]}). Use --force to replace it.")
        return
    print(f"Downloading {repo} to {target} (Qwen3-4B is about 8 GB) ...")
    snapshot_download(repo, local_dir=str(target), allow_patterns=["*.json", "*.safetensors", "*.txt", "*.model", "*.tiktoken", "merges.txt", "vocab.json"])
    print("Base model ready.")


def download_adapter(repo: str, models_dir: Path, force: bool) -> Path:
    from huggingface_hub import snapshot_download
    target = models_dir / repo.split("/")[-1]
    if (target / "adapter_config.json").is_file() and not force:
        print(f"Adapter already present in {target}.")
        return target
    print(f"Downloading adapter {repo} to {target} ...")
    snapshot_download(repo, local_dir=str(target))
    if not (target / "adapter_config.json").is_file():
        raise SystemExit(f"{repo} does not look like a LoRA adapter (no adapter_config.json).")
    print(f"Adapter ready. Start the workbench with MODEL_PATH={target} SITE_STRATEGY=native")
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base", default="Qwen/Qwen3-4B", help="Hugging Face repo of the base model")
    parser.add_argument("--adapter", help="Hugging Face repo of a fine-tuned LoRA adapter (optional)")
    parser.add_argument("--force", action="store_true", help="Download again even if files exist")
    args = parser.parse_args()
    try:
        download_base(args.base, BASE_DIR / "base-model", args.force)
        if args.adapter:
            download_adapter(args.adapter, BASE_DIR / "models", args.force)
    except KeyboardInterrupt:
        sys.exit("Download interrupted; run the command again to resume.")


if __name__ == "__main__":
    main()
