"""Hardware detection: pick how to load the model on whatever machine this runs on.

The workbench was developed on a 6 GB RTX 4050, but anyone cloning the repo may have
a bigger or smaller NVIDIA GPU, an AMD GPU, an Apple Silicon Mac, or no GPU at all.
`detect_profile()` inspects the machine once and returns the backend, precision and
context length to use. Every choice can be overridden with environment variables:

  SLM_DEVICE          cuda | mps | cpu        (default: best available)
  SLM_BACKEND         unsloth | transformers  (default: unsloth on NVIDIA when installed)
  SLM_LOAD_IN_4BIT    1 | 0                   (default: 1 on CUDA when bitsandbytes is available)
  SLM_CONTEXT_LENGTH  tokens                  (default: from free memory, see below)

`python slm.py doctor` prints the detected profile and what to fix.
"""
from __future__ import annotations

import importlib.util
import os
import platform
from dataclasses import asdict, dataclass, field
from typing import Optional

# Approximate memory to hold Qwen3-4B weights. Context adds KV cache on top.
WEIGHTS_GB = {"4bit": 2.8, "fp16": 8.2, "fp32": 16.4}


@dataclass
class HardwareProfile:
    device: str                      # cuda | mps | cpu
    backend: str                     # unsloth | transformers
    load_in_4bit: bool
    dtype: str                       # float16 | bfloat16 | float32
    context_length: int
    gpu_name: str = ""
    vram_gb: float = 0.0
    ram_gb: float = 0.0
    notes: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _has(module: str) -> bool:
    return importlib.util.find_spec(module) is not None


def _ram_gb() -> float:
    try:
        import psutil  # optional
        return round(psutil.virtual_memory().total / 1024**3, 1)
    except Exception:
        pass
    try:
        if platform.system() == "Windows":
            import ctypes

            class _Status(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                            ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                            ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                            ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
            status = _Status()
            status.dwLength = ctypes.sizeof(_Status)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status))
            return round(status.ullTotalPhys / 1024**3, 1)
        pages, size = os.sysconf("SC_PHYS_PAGES"), os.sysconf("SC_PAGE_SIZE")
        return round(pages * size / 1024**3, 1)
    except Exception:
        return 0.0


def _context_for(free_gb: float) -> int:
    """Context length that fits next to the weights. The kit strategy needs ~3k tokens
    per call; native section authoring needs up to ~7.5k for the longest sections."""
    if free_gb >= 4.0:
        return 16384
    if free_gb >= 1.5:
        return 8192
    return 4096


def detect_profile() -> HardwareProfile:
    notes: list[str] = []
    warnings: list[str] = []
    ram = _ram_gb()
    try:
        import torch
    except ImportError:
        return HardwareProfile("cpu", "transformers", False, "float32", 4096, ram_gb=ram,
                               warnings=["PyTorch is not installed; run the setup script."])

    wanted = (os.environ.get("SLM_DEVICE") or "").strip().lower()
    cuda_ok = torch.cuda.is_available()
    mps_ok = bool(getattr(torch.backends, "mps", None) and torch.backends.mps.is_available())
    if wanted == "cuda" and not cuda_ok:
        warnings.append("SLM_DEVICE=cuda but no CUDA GPU is visible to PyTorch; using the best available device.")
        wanted = ""
    if wanted == "mps" and not mps_ok:
        warnings.append("SLM_DEVICE=mps but Metal is not available; using the best available device.")
        wanted = ""
    device = wanted or ("cuda" if cuda_ok else "mps" if mps_ok else "cpu")

    gpu_name, vram = "", 0.0
    if device == "cuda":
        props = torch.cuda.get_device_properties(0)
        gpu_name, vram = props.name, round(props.total_memory / 1024**3, 1)
        is_rocm = bool(getattr(torch.version, "hip", None))
        bnb = _has("bitsandbytes")
        want_4bit = os.environ.get("SLM_LOAD_IN_4BIT")
        load_in_4bit = (want_4bit != "0") if want_4bit is not None else (bnb or _has("unsloth"))
        backend = (os.environ.get("SLM_BACKEND") or "").strip().lower()
        if backend not in {"unsloth", "transformers"}:
            backend = "unsloth" if (_has("unsloth") and not is_rocm and load_in_4bit) else "transformers"
        if backend == "transformers" and load_in_4bit and not bnb:
            warnings.append("4-bit loading needs bitsandbytes; loading in float16 instead (needs ~8 GB VRAM).")
            load_in_4bit = False
        weights = WEIGHTS_GB["4bit" if load_in_4bit else "fp16"]
        free = vram - weights - 0.6  # CUDA context and activations
        if free < 0.5:
            warnings.append(f"{gpu_name} has {vram} GB VRAM; Qwen3-4B needs about {weights + 1:.0f} GB here. "
                            "Expect out-of-memory errors; try SLM_DEVICE=cpu or a smaller base model (see README).")
        dtype = "bfloat16" if torch.cuda.is_bf16_supported() else "float16"
        if is_rocm:
            notes.append("AMD ROCm GPU detected: using Transformers (Unsloth is NVIDIA-only).")
        context = _context_for(free)
    elif device == "mps":
        backend, load_in_4bit, dtype = "transformers", False, "float16"
        notes.append("Apple Silicon: the model runs in float16 on Metal (unified memory, ~8 GB).")
        if ram and ram < 16:
            warnings.append(f"{ram} GB unified memory is tight for a 4B model in float16; close other apps.")
        context = 8192
    else:
        backend, load_in_4bit = "transformers", False
        dtype = "bfloat16" if ram >= 12 else "float32"
        notes.append("No GPU: the model runs on the CPU. Expect a few tokens per second; "
                     "the kit strategy (the default) still works, native mode will be very slow.")
        if ram and ram < 10:
            warnings.append(f"{ram} GB RAM is below the ~10 GB a 4B model needs on CPU; use a smaller base model.")
        context = 8192

    override = os.environ.get("SLM_CONTEXT_LENGTH")
    if override and override.isdigit():
        context = int(override)
    return HardwareProfile(device, backend, load_in_4bit, dtype, context, gpu_name, vram, ram, notes, warnings)


_PROFILE: Optional[HardwareProfile] = None


def get_profile() -> HardwareProfile:
    global _PROFILE
    if _PROFILE is None:
        _PROFILE = detect_profile()
    return _PROFILE
