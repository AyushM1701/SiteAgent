#!/usr/bin/env python3
"""Check that this machine can run the SiteAgent workbench, and say how to fix what can't.

  python slm.py doctor
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
OK, WARN, FAIL = "ok  ", "warn", "FAIL"
results: list[tuple[str, str, str]] = []


def check(status: str, name: str, detail: str) -> None:
    results.append((status, name, detail))


def version_of(command: list[str]) -> str:
    exe = shutil.which(command[0])
    if not exe:
        return ""
    try:
        return subprocess.run([exe, *command[1:]], capture_output=True, text=True, timeout=20).stdout.strip()
    except Exception:
        return ""


def main() -> int:
    py = sys.version_info
    check(OK if (3, 10) <= py[:2] <= (3, 13) else FAIL, "Python", f"{py.major}.{py.minor}.{py.micro}"
          + ("" if (3, 10) <= py[:2] <= (3, 13) else " - use Python 3.10 to 3.13"))
    in_venv = sys.prefix != getattr(sys, "base_prefix", sys.prefix)
    check(OK if in_venv else WARN, "Virtual env", sys.prefix if in_venv else "not in a venv (the setup script creates .venv)")

    node = version_of(["node", "-v"])
    major = int(re.sub(r"\D", "", node.split(".")[0]) or 0) if node else 0
    check(OK if major >= 18 else FAIL, "Node.js", node or "not found - install Node.js 18+ from nodejs.org")
    check(OK if (BASE_DIR / "node_modules" / "vite").exists() else FAIL, "Site build tools",
          "node_modules ready" if (BASE_DIR / "node_modules" / "vite").exists() else "run `npm ci` in the repo root")

    index = BASE_DIR / "web_ui_static" / "index.html"
    assets = re.findall(r'(?:src|href)="/(assets/[^"]+)"', index.read_text(encoding="utf-8")) if index.exists() else []
    missing = [a for a in assets if not (BASE_DIR / "web_ui_static" / a).exists()]
    check(OK if assets and not missing else FAIL, "Workbench UI",
          "built" if assets and not missing else "run `npm ci && npm run build` in frontend/")

    try:
        import torch
        check(OK, "PyTorch", f"{torch.__version__} (CUDA {torch.version.cuda})" if torch.version.cuda else torch.__version__)
    except ImportError:
        check(FAIL, "PyTorch", "not installed - run the setup script")
        torch = None
    for module, why in (("transformers", "model loading"), ("peft", "fine-tuned adapters"), ("flask", "workbench server"),
                        ("playwright", "site checks")):
        try:
            __import__(module)
            check(OK, module, why)
        except ImportError:
            check(FAIL, module, f"missing ({why}) - pip install -r requirements.txt")

    browsers = Path.home() / ("AppData/Local/ms-playwright" if sys.platform == "win32" else
                              "Library/Caches/ms-playwright" if sys.platform == "darwin" else ".cache/ms-playwright")
    has_chromium = browsers.exists() and any(p.name.startswith("chromium") for p in browsers.iterdir())
    check(OK if has_chromium else WARN, "Chromium for checks",
          "installed" if has_chromium else "run `python -m playwright install chromium` (needed for browser checks)")

    base = BASE_DIR / "base-model"
    if (base / "config.json").exists() and any(base.glob("*.safetensors")):
        config = json.loads((base / "config.json").read_text(encoding="utf-8"))
        size = sum(p.stat().st_size for p in base.glob("*.safetensors")) / 1024**3
        check(OK if config.get("model_type") == "qwen3" else FAIL, "Base model",
              f"{config.get('architectures', ['?'])[0]}, {size:.1f} GB")
    else:
        check(FAIL, "Base model", "missing - run `python scripts/download_models.py`")
    adapters = sorted(p.name for p in (BASE_DIR / "models").glob("*native*") if (p / "adapter_config.json").exists()) \
        if (BASE_DIR / "models").exists() else []
    check(OK if adapters else WARN, "Native adapter",
          ", ".join(adapters[-3:]) if adapters else "none (optional) - kit mode works without one")

    free_gb = shutil.disk_usage(BASE_DIR).free / 1024**3
    check(OK if free_gb > 5 else WARN, "Disk space", f"{free_gb:.0f} GB free")

    profile = None
    if torch is not None:
        from agent.hardware import detect_profile
        profile = detect_profile()
        where = profile.gpu_name and f"{profile.gpu_name}, {profile.vram_gb} GB" or profile.device
        check(OK if not profile.warnings else WARN, "Hardware",
              f"{where} | {profile.backend} | {'4-bit' if profile.load_in_4bit else profile.dtype} | context {profile.context_length}")

    width = max(len(n) for _, n, _ in results)
    print("\nSiteAgent doctor\n")
    for status, name, detail in results:
        print(f"  [{status}] {name.ljust(width)}  {detail}")
    if profile is not None:
        for note in profile.notes:
            print(f"\n  note: {note}")
        for warning in profile.warnings:
            print(f"\n  warning: {warning}")
    failed = [n for s, n, _ in results if s == FAIL]
    print("\n" + ("Ready. Start the workbench with `python slm.py serve`." if not failed else
                  f"Fix {', '.join(failed)} and run this again."))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
