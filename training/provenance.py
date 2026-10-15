"""
training/provenance.py - Cryptographic Benchmark Provenance & Integrity Attestation

Generates and validates provenance records for benchmark reports:
{
  "provenance": "real",
  "model_sha256": "...",
  "adapter_sha256": "...",
  "dataset_sha256": "...",
  "git_commit": "...",
  "hardware": "...",
  "mock": false
}

Enforces:
- Real model execution vs mock harness tagging
- Cryptographic SHA-256 verification of models, adapters, and datasets
- Fail-closed rejection of mock or unverified reports at the promotion gate
"""

import hashlib
import json
import os
import platform
import subprocess
import time
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent


def _compute_file_sha256(path: Path) -> str:
    if not path.is_file():
        return "none"
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _get_git_commit() -> str:
    """Gets the current git commit hash."""
    try:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=3,
        )
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip()
    except Exception:
        pass

    head_file = ROOT / ".git" / "HEAD"
    if head_file.is_file():
        try:
            content = head_file.read_text(encoding="utf-8").strip()
            if content.startswith("ref: "):
                ref_path = ROOT / ".git" / content[5:].strip()
                if ref_path.is_file():
                    return ref_path.read_text(encoding="utf-8").strip()
            return content
        except Exception:
            pass

    return "unknown_commit"


def _get_hardware_description() -> str:
    """Returns local GPU/CPU hardware description."""
    try:
        import torch
        if torch.cuda.is_available():
            dev_name = torch.cuda.get_device_name(0)
            props = torch.cuda.get_device_properties(0)
            total_gib = round(props.total_memory / (1024**3), 2)
            return f"NVIDIA {dev_name} ({total_gib} GiB VRAM, CUDA {torch.version.cuda})"
    except Exception:
        pass
    
    cpu_arch = platform.processor() or platform.machine()
    return f"CPU: {cpu_arch} ({platform.system()} {platform.release()})"


def generate_provenance_record(
    mock: bool = False,
    model_path: Optional[str] = None,
    adapter_path: Optional[str] = None,
    dataset_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Constructs the canonical provenance metadata block required for benchmark reports.
    """
    # 1. Base model SHA256
    model_sha256 = "unknown"
    resolved_model = Path(model_path) if model_path else (ROOT / "base-model")
    if not resolved_model.is_absolute():
        resolved_model = ROOT / resolved_model

    # A PEFT adapter directory identifies the adapter, not the loaded base.
    adapter_config = resolved_model / "adapter_config.json"
    if adapter_config.is_file():
        if adapter_path is None:
            adapter_path = str(resolved_model)
        config = json.loads(adapter_config.read_text(encoding="utf-8"))
        base_path = config.get("base_model_name_or_path")
        if not base_path:
            raise ValueError("Adapter provenance requires base_model_name_or_path")
        resolved_model = Path(base_path)
        if not resolved_model.is_absolute():
            resolved_model = ROOT / resolved_model

    if resolved_model.is_dir():
        manifest_path = resolved_model / "manifest.json"
        if manifest_path.is_file():
            try:
                m = json.loads(manifest_path.read_text(encoding="utf-8"))
                model_sha256 = m.get("immutable_fingerprint_sha256") or m.get("sha256") or "unknown"
            except Exception:
                pass
        if model_sha256 == "unknown":
            cfg_path = resolved_model / "config.json"
            if cfg_path.is_file():
                model_sha256 = _compute_file_sha256(cfg_path)
    elif resolved_model.is_file():
        model_sha256 = _compute_file_sha256(resolved_model)

    # 2. Adapter SHA256
    adapter_sha256 = "none"
    if adapter_path:
        resolved_adapter = Path(adapter_path)
        if not resolved_adapter.is_absolute():
            resolved_adapter = ROOT / resolved_adapter
        if resolved_adapter.is_dir():
            weights = resolved_adapter / "adapter_model.safetensors"
            if weights.is_file():
                adapter_sha256 = _compute_file_sha256(weights)
            else:
                tm = resolved_adapter / "training_manifest.json"
                if tm.is_file():
                    adapter_sha256 = _compute_file_sha256(tm)
        elif resolved_adapter.is_file():
            adapter_sha256 = _compute_file_sha256(resolved_adapter)

    # 3. Dataset SHA256
    dataset_sha256 = "none"
    if dataset_path:
        resolved_data = Path(dataset_path)
        if not resolved_data.is_absolute():
            resolved_data = ROOT / resolved_data
        if resolved_data.is_file():
            dataset_sha256 = _compute_file_sha256(resolved_data)

    return {
        "provenance": "real" if not mock else "synthetic_mock",
        "model_sha256": model_sha256,
        "adapter_sha256": adapter_sha256,
        "dataset_sha256": dataset_sha256,
        "git_commit": _get_git_commit(),
        "hardware": _get_hardware_description(),
        "mock": bool(mock),
    }


def validate_benchmark_provenance(report: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validates that a benchmark report contains genuine provenance attestation.
    Returns (is_valid, list_of_errors).
    """
    errors: List[str] = []
    
    prov = report.get("provenance")
    if not prov:
        errors.append("Benchmark report is missing mandatory 'provenance' field.")
    elif prov != "real":
        errors.append(f"Benchmark report provenance is '{prov}' (must be 'real' for promotion).")

    is_mock = report.get("mock", report.get("is_mock", True))
    if is_mock is not False:
        errors.append(f"Benchmark report has mock={is_mock} (must be False for promotion).")

    for key in ["model_sha256", "dataset_sha256", "git_commit", "hardware"]:
        val = report.get(key)
        if not val or val == "unknown":
            errors.append(f"Benchmark report has missing or invalid '{key}'.")
        elif key.endswith("sha256") and not re.fullmatch(r"[0-9a-f]{64}", str(val)):
            errors.append(f"Benchmark report has invalid SHA-256 '{key}'.")
    adapter_sha = report.get("adapter_sha256")
    if adapter_sha not in (None, "none") and not re.fullmatch(r"[0-9a-f]{64}", str(adapter_sha)):
        errors.append("Benchmark report has invalid SHA-256 'adapter_sha256'.")

    return (len(errors) == 0, errors)
