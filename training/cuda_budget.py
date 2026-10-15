"""Hard CUDA allocation budget used by training and benchmark paths."""
from __future__ import annotations

VRAM_CEILING = int(5.5 * 1024**3)


def assert_cuda_budget(label: str, torch_module=None) -> dict:
    import torch as _torch
    torch = torch_module or _torch
    if not torch.cuda.is_available():
        return {"label": label, "allocated": 0, "reserved": 0, "available": False}
    allocated = int(torch.cuda.memory_allocated())
    reserved = int(torch.cuda.memory_reserved())
    if reserved > VRAM_CEILING and allocated <= VRAM_CEILING:
        torch.cuda.empty_cache()
        reserved = int(torch.cuda.memory_reserved())
    print(f"[VRAM] {label}: allocated={allocated / 1024**3:.2f} GiB, reserved={reserved / 1024**3:.2f} GiB")
    if allocated > VRAM_CEILING or reserved > VRAM_CEILING:
        raise RuntimeError(f"{label}: CUDA allocation/reservation exceeded hard ceiling: "
                           f"allocated={allocated / 1024**3:.2f} GiB reserved={reserved / 1024**3:.2f} GiB")
    return {"label": label, "allocated": allocated, "reserved": reserved, "available": True}
