#!/usr/bin/env python3
"""Upload a trained adapter to the Hugging Face Hub so others can download it.

  huggingface-cli login                      # once, with a write token
  python scripts/publish_adapter.py models/qwen3-siteagent-native-sections-r16-v2 --repo YOUR_NAME/siteagent-native-qwen3-4b

Others then run:
  python scripts/download_models.py --adapter YOUR_NAME/siteagent-native-qwen3-4b

Only the adapter (~130 MB) is uploaded; the Qwen3-4B base comes from Qwen's own repo.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

CARD = """---
base_model: Qwen/Qwen3-4B
library_name: peft
tags: [lora, qlora, react, typescript, website-generation]
license: apache-2.0
---

# SiteAgent native section adapter (Qwen3-4B, LoRA r16)

Teaches Qwen3-4B to write a website section's React/TypeScript component and CSS from a
design spec plus approved copy, for the SiteAgent workbench's *native* strategy.

* Training: {train_rows} rows from design-kit renderings of model-written copy, QLoRA r{rank},
  {steps} steps on an RTX 4050 (6 GB). Final validation loss {eval_loss}.
* Held-out evaluation (business families never seen in training): see the repository's
  `docs/NATIVE_SECTION_TRAINING.md`.

Load it with the SiteAgent repo (`MODEL_PATH=models/<this folder> SITE_STRATEGY=native`), or with
PEFT on top of `Qwen/Qwen3-4B`.
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("adapter_dir", type=Path)
    parser.add_argument("--repo", required=True, help="Destination repo id, e.g. your-name/siteagent-native-qwen3-4b")
    parser.add_argument("--private", action="store_true")
    args = parser.parse_args()
    if not (args.adapter_dir / "adapter_config.json").is_file():
        raise SystemExit(f"{args.adapter_dir} has no adapter_config.json")
    manifest_path = args.adapter_dir / "training_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    readme = args.adapter_dir / "README.md"
    readme.write_text(CARD.format(
        train_rows=manifest.get("train_rows", "?"), rank=manifest.get("rank", 16),
        steps=manifest.get("global_step", "?"),
        eval_loss=round((manifest.get("evaluation_metrics") or {}).get("eval_loss", 0) or 0, 4) or "?"), encoding="utf-8")
    # The adapter config may point at a local base path; point it at the public base instead.
    config_path = args.adapter_dir / "adapter_config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["base_model_name_or_path"] = "Qwen/Qwen3-4B"
    from huggingface_hub import HfApi
    api = HfApi()
    try:
        user = api.whoami()["name"]
    except Exception as error:
        raise SystemExit(f"Not signed in to Hugging Face ({str(error).splitlines()[-1]}).\n"
                         "Run:  hf auth login --force   (paste a token with 'write' access from "
                         "https://huggingface.co/settings/tokens), then run this again.")
    if args.repo.split("/")[0] != user:
        print(f"Note: signed in as '{user}'; publishing to '{args.repo}' needs write access to that namespace.")
    api.create_repo(args.repo, private=args.private, exist_ok=True)
    patterns = ["adapter_config.json", "adapter_model.safetensors", "README.md",
                "tokenizer*", "special_tokens_map.json", "chat_template.jinja", "added_tokens.json", "vocab.json", "merges.txt"]
    api.upload_folder(folder_path=str(args.adapter_dir), repo_id=args.repo, allow_patterns=patterns,
                      ignore_patterns=["adapter_config.json"])
    api.upload_file(path_or_fileobj=json.dumps(config, indent=2).encode(), path_in_repo="adapter_config.json", repo_id=args.repo)
    print(f"Published https://huggingface.co/{args.repo}")


if __name__ == "__main__":
    main()
