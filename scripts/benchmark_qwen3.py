#!/usr/bin/env python3
"""
benchmark_qwen3.py - VRAM and Context-Length Benchmark for Qwen3-4B

Benchmarks 6144 and 8192 token contexts under exact local hardware and QLoRA conditions:
- Exact local: Qwen3-4B / base model, Unsloth, PyTorch, CUDA, 4-bit QLoRA
- Measures: dataset coverage, records exceeding context, sequence length distribution
  (p50, p75, p90, p95, p99, max), peak allocated VRAM, peak reserved VRAM, tokens/sec,
  step duration, forward stability, backward stability, OOM, shared-memory/WDDM spill.
- Outputs machine-readable report to runs/qwen3_context_benchmark.json
- Emits a deterministic context-length recommendation (6144 vs 8192).

Usage:
    python scripts/benchmark_qwen3.py [--context 6144 8192] [--output runs/qwen3_context_benchmark.json]
"""

import argparse
import importlib.util
import json
import math
import os
from pathlib import Path
import sys
import time

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

DEFAULT_MODEL_PATH = str(BASE_DIR / "base-model")
DEFAULT_DATASET_PATH = str(BASE_DIR / "data" / "quality_candidate" / "train.jsonl")
DEFAULT_OUTPUT_PATH = str(BASE_DIR / "runs" / "qwen3_context_benchmark.json")
VRAM_CEILING_GIB = 5.5  # RTX 4050 6GB safety limit (~0.5 GiB OS/WDDM headroom)

SAMPLE_PROMPT = (
    "<|im_start|>system\n"
    "You are an expert React TypeScript coding agent.\n"
    "<|im_end|>\n"
    "<|im_start|>user\n"
    "Write a React Button component.\n"
    "<|im_end|>\n"
    "<|im_start|>assistant\n"
)


def bytes_to_gib(n: int) -> float:
    return n / (1024 ** 3)


def calculate_sequence_stats(lengths: list[int]) -> dict:
    """Calculate descriptive statistics and percentiles for a list of token lengths."""
    if not lengths:
        return {
            "count": 0,
            "min": 0,
            "max": 0,
            "mean": 0.0,
            "p50": 0,
            "p75": 0,
            "p90": 0,
            "p95": 0,
            "p99": 0,
        }
    sorted_lengths = sorted(lengths)
    n = len(sorted_lengths)

    def percentile(p: float) -> int:
        idx = min(int(n * p), n - 1)
        return sorted_lengths[idx]

    return {
        "count": n,
        "min": sorted_lengths[0],
        "max": sorted_lengths[-1],
        "mean": round(sum(sorted_lengths) / n, 1),
        "p50": percentile(0.50),
        "p75": percentile(0.75),
        "p90": percentile(0.90),
        "p95": percentile(0.95),
        "p99": percentile(0.99),
    }


def analyze_dataset_coverage(dataset_path: str, context_lengths: list[int], tokenizer_file: Path = None) -> tuple[dict, dict]:
    """
    Read training dataset, measure token lengths with the fast CPU tokenizer,
    and calculate coverage statistics for each context length.
    """
    from tokenizers import Tokenizer
    from agent.agent_protocol import format_chatml
    from training.preflight import read_jsonl, validate_messages

    path = Path(dataset_path)
    if not path.is_absolute() and not path.exists() and (BASE_DIR / dataset_path).exists():
        path = (BASE_DIR / dataset_path).resolve()
    else:
        path = path.resolve()

    if not path.exists():
        raise FileNotFoundError(f"Training dataset not found: {path}")

    rows = read_jsonl(path)

    # Load CPU tokenizer
    if tokenizer_file is None or not tokenizer_file.exists():
        tokenizer_file = BASE_DIR / "base-model" / "tokenizer.json"

    if tokenizer_file.exists():
        tok = Tokenizer.from_file(str(tokenizer_file))
        tok.no_truncation()
        tok.no_padding()
        lengths = []
        for row in rows:
            msgs = validate_messages(row)
            text = format_chatml(msgs, False)
            encoded = tok.encode(text, add_special_tokens=False)
            lengths.append(len(encoded.ids))
    else:
        # Fallback length estimation based on character ratio if tokenizer.json is absent
        lengths = [max(256, len(json.dumps(r.get("messages", []))) // 4) for r in rows]

    seq_stats = calculate_sequence_stats(lengths)

    context_coverage = {}
    for ctx in context_lengths:
        exceeding = sum(1 for l in lengths if l > ctx)
        coverage = (len(lengths) - exceeding) / len(lengths) if lengths else 1.0
        context_coverage[ctx] = {
            "coverage": round(coverage, 4),
            "records_exceeding": exceeding,
            "fits_pct": round(coverage * 100, 1),
        }

    return seq_stats, context_coverage


def make_recommendation(
    context_results: dict,
    seq_stats: dict,
    ceiling_gib: float = VRAM_CEILING_GIB,
) -> dict:
    """
    Produce a deterministic context-length decision (6144 vs 8192) based on:
      1. Dataset token coverage
      2. Training stability (forward, backward, no OOM, no spill)
      3. VRAM headroom against the safety ceiling
      4. Throughput (tokens/sec)
      5. Sequence-length distribution (tail max/p99)
    """
    ctx_6144 = context_results.get("6144")
    ctx_8192 = context_results.get("8192")

    if ctx_6144 and ctx_8192:
        stable_8192 = (
            bool(ctx_8192.get("stable"))
            and not ctx_8192.get("oom", False)
            and not ctx_8192.get("shared_memory_spill", False)
            and (ctx_8192.get("peakVramGiB", 999.0) <= ceiling_gib)
        )
        stable_6144 = (
            bool(ctx_6144.get("stable"))
            and not ctx_6144.get("oom", False)
            and not ctx_6144.get("shared_memory_spill", False)
            and (ctx_6144.get("peakVramGiB", 999.0) <= ceiling_gib)
        )

        cov_6144 = ctx_6144.get("coverage", 0.0)
        max_tok = seq_stats.get("max", 0)

        if stable_8192:
            headroom_8192 = round(ceiling_gib - ctx_8192.get("peakVramGiB", 0.0), 2)
            # If a meaningful portion (>2%) of trajectories exceed 6144, 8192 is required
            if cov_6144 < 0.98:
                pct_exceeding = round((1.0 - cov_6144) * 100, 1)
                return {
                    "selected_context_length": 8192,
                    "selectedContextLength": 8192,
                    "policy_decision": "choose_8192",
                    "policyDecision": "choose_8192",
                    "rationale": (
                        f"A meaningful portion ({pct_exceeding}%) of high-value full-site trajectories "
                        f"needs >6144 tokens (dataset maximum: {max_tok} tokens), and 8192 trains stably "
                        f"with {headroom_8192:.2f} GiB VRAM headroom under the {ceiling_gib:.1f} GiB ceiling "
                        f"without OOM or WDDM spill."
                    ),
                }
            else:
                # If >=98% of data fits inside 6144, check if 8192 incurs a heavy VRAM or speed penalty
                tps_6144 = ctx_6144.get("tokensPerSecond", 0.0)
                tps_8192 = ctx_8192.get("tokensPerSecond", 0.0)
                vram_6144 = ctx_6144.get("peakVramGiB", 0.0)
                vram_8192 = ctx_8192.get("peakVramGiB", 0.0)

                if (tps_6144 > 0 and tps_8192 > 0 and (tps_6144 - tps_8192) / tps_6144 > 0.35) or (vram_8192 > 5.2):
                    return {
                        "selected_context_length": 6144,
                        "selectedContextLength": 6144,
                        "policy_decision": "choose_6144",
                        "policyDecision": "choose_6144",
                        "rationale": (
                            f"≥98% of high-quality data fits inside 6144 ({round(cov_6144 * 100, 1)}% coverage) "
                            f"and 8192 increases VRAM pressure ({vram_8192:.2f} GiB vs {vram_6144:.2f} GiB) "
                            f"or reduces throughput ({tps_8192:.1f} vs {tps_6144:.1f} tok/s). "
                            f"Choosing 6144 provides optimal training efficiency and headroom."
                        ),
                    }
                else:
                    return {
                        "selected_context_length": 8192,
                        "selectedContextLength": 8192,
                        "policy_decision": "choose_8192",
                        "policyDecision": "choose_8192",
                        "rationale": (
                            f"8192 context fits with {headroom_8192:.2f} GiB VRAM headroom without significant "
                            f"throughput degradation, guaranteeing 100% trajectory coverage."
                        ),
                    }
        elif stable_6144:
            headroom_6144 = round(ceiling_gib - ctx_6144.get("peakVramGiB", 0.0), 2)
            return {
                "selected_context_length": 6144,
                "selectedContextLength": 6144,
                "policy_decision": "choose_6144",
                "policyDecision": "choose_6144",
                "rationale": (
                    f"8192 context exceeds the safe VRAM ceiling ({ctx_8192.get('peakVramGiB')} GiB) or "
                    f"encountered instability/OOM, whereas 6144 trains stably with {headroom_6144:.2f} GiB "
                    f"headroom and covers {round(cov_6144 * 100, 1)}% of dataset trajectories."
                ),
            }
        else:
            return {
                "selected_context_length": None,
                "selectedContextLength": None,
                "policy_decision": "insufficient_vram",
                "policyDecision": "insufficient_vram",
                "rationale": (
                    f"Neither 6144 nor 8192 passed stability and VRAM checks under the {ceiling_gib:.1f} GiB ceiling."
                ),
            }

    # Fallback if other context list passed
    for ctx_key in sorted(context_results.keys(), key=lambda x: int(x), reverse=True):
        entry = context_results[ctx_key]
        if entry.get("stable") and (entry.get("peakVramGiB", 999.0) <= ceiling_gib):
            return {
                "selected_context_length": int(ctx_key),
                "selectedContextLength": int(ctx_key),
                "policy_decision": f"choose_{ctx_key}",
                "policyDecision": f"choose_{ctx_key}",
                "rationale": f"Context length {ctx_key} is the largest stable context within the {ceiling_gib} GiB budget.",
            }

    return {
        "selected_context_length": None,
        "selectedContextLength": None,
        "policy_decision": "insufficient_vram",
        "policyDecision": "insufficient_vram",
        "rationale": "No context length passed stability and memory criteria.",
    }


def run_benchmark(
    model_path: str = DEFAULT_MODEL_PATH,
    context_lengths: list[int] = None,
    dataset_path: str = DEFAULT_DATASET_PATH,
    output_path: str = DEFAULT_OUTPUT_PATH,
    ceiling_gib: float = VRAM_CEILING_GIB,
    rank: int = 16,
    lora_alpha: int = 16,
    lora_dropout: float = 0.0,
    mock: bool = False,
) -> dict:
    """
    Load Qwen3 / base model at 4-bit, configure QLoRA, and measure forward/backward
    stability and peak VRAM across specified context lengths.
    """
    if context_lengths is None:
        context_lengths = [6144, 8192]

    # Normalize paths
    mp = Path(model_path)
    if not mp.is_absolute() and not mp.exists() and (BASE_DIR / model_path).exists():
        mp = (BASE_DIR / model_path).resolve()
    else:
        mp = mp.resolve()

    dp = Path(dataset_path)
    if not dp.is_absolute() and not dp.exists() and (BASE_DIR / dataset_path).exists():
        dp = (BASE_DIR / dataset_path).resolve()
    else:
        dp = dp.resolve()

    # 1. Dataset Analysis (CPU-only, fast)
    seq_stats, context_coverage = analyze_dataset_coverage(str(dp), context_lengths, mp / "tokenizer.json")

    # 2. Environment Info
    model_config_file = mp / "config.json"
    model_name = "Qwen/Qwen3-4B"
    if model_config_file.exists():
        try:
            mcfg = json.loads(model_config_file.read_text(encoding="utf-8"))
            model_name = mcfg.get("_name_or_path", mp.name)
        except Exception:
            model_name = mp.name

    target_modules = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]

    # 3. GPU or Mock Execution
    results = {}
    environment = {
        "model": model_name,
        "model_path": str(mp),
        "pytorch_version": None,
        "unsloth_version": None,
        "cuda_environment": {
            "device_name": "None",
            "cuda_version": None,
            "total_vram_gib": 0.0,
            "vram_ceiling_gib": ceiling_gib,
            "driver_model": "Unknown",
        },
        "qlora_configuration": {
            "rank": rank,
            "lora_alpha": lora_alpha,
            "lora_dropout": lora_dropout,
            "load_in_4bit": True,
            "target_modules": target_modules,
            "bias": "none",
            "use_gradient_checkpointing": "unsloth",
        },
    }

    if mock:
        # Synthetic / mock benchmark execution (for CI or testing without GPU)
        for ctx in context_lengths:
            cov_info = context_coverage.get(ctx, {"coverage": 1.0, "records_exceeding": 0})
            alloc_gib = 3.126 if ctx <= 6144 else 3.276
            res_gib = 3.775 if ctx <= 6144 else 3.916
            tps = 548.0 if ctx <= 6144 else 726.0
            dt = round(ctx / tps, 4)
            entry = {
                "coverage": cov_info["coverage"],
                "peakVramGiB": alloc_gib,
                "tokensPerSecond": tps,
                "stable": True,
                "dataset_coverage": cov_info["coverage"],
                "records_exceeding_context": cov_info["records_exceeding"],
                "recordsExceedingContext": cov_info["records_exceeding"],
                "p50_tokens": seq_stats["p50"],
                "p50Tokens": seq_stats["p50"],
                "p75_tokens": seq_stats["p75"],
                "p75Tokens": seq_stats["p75"],
                "p90_tokens": seq_stats["p90"],
                "p90Tokens": seq_stats["p90"],
                "p95_tokens": seq_stats["p95"],
                "p95Tokens": seq_stats["p95"],
                "p99_tokens": seq_stats["p99"],
                "p99Tokens": seq_stats["p99"],
                "maximum_tokens": seq_stats["max"],
                "maximumTokens": seq_stats["max"],
                "peak_allocated_vram_gib": alloc_gib,
                "peak_reserved_vram_gib": res_gib,
                "peakReservedGiB": res_gib,
                "tokens_per_second": tps,
                "step_duration_seconds": dt,
                "stepDuration": dt,
                "forward_stability": True,
                "forwardStability": True,
                "backward_stability": True,
                "backwardStability": True,
                "oom": False,
                "shared_memory_spill": False,
                "sharedMemorySpill": False,
                "vram_headroom_gib": round(ceiling_gib - alloc_gib, 3),
            }
            results[str(ctx)] = entry
    else:
        import torch

        if not torch.cuda.is_available():
            raise RuntimeError("CUDA is not available. Use --mock if testing without GPU.")

        device_name = torch.cuda.get_device_name(0)
        total_bytes = torch.cuda.get_device_properties(0).total_memory
        total_gib = bytes_to_gib(total_bytes)

        unsloth_version = None
        try:
            import unsloth
            unsloth_version = getattr(unsloth, "__version__", "unknown")
        except ImportError:
            pass

        environment["pytorch_version"] = torch.__version__
        environment["unsloth_version"] = unsloth_version
        environment["cuda_environment"] = {
            "device_name": device_name,
            "cuda_version": getattr(torch.version, "cuda", "unknown"),
            "total_vram_gib": round(total_gib, 3),
            "vram_ceiling_gib": ceiling_gib,
            "driver_model": "WDDM" if sys.platform == "win32" else "Linux",
        }

        # Load Unsloth model with QLoRA
        from unsloth import FastLanguageModel

        max_ctx = max(context_lengths)
        model, tokenizer = FastLanguageModel.from_pretrained(
            model_name=str(mp),
            max_seq_length=max_ctx,
            load_in_4bit=True,
            local_files_only=True,
        )

        model = FastLanguageModel.get_peft_model(
            model,
            r=rank,
            lora_alpha=lora_alpha,
            lora_dropout=lora_dropout,
            target_modules=target_modules,
            bias="none",
            use_gradient_checkpointing="unsloth",
            random_state=42,
        )
        FastLanguageModel.for_training(model, use_gradient_checkpointing="unsloth")

        # Benchmark each context length
        for ctx in sorted(context_lengths):
            cov_info = context_coverage.get(ctx, {"coverage": 1.0, "records_exceeding": 0})
            torch.cuda.empty_cache()
            torch.cuda.reset_peak_memory_stats()

            # Synthetic structured batch matching context length
            input_ids = torch.randint(100, 5000, (1, ctx), dtype=torch.long, device="cuda")
            labels = input_ids.clone()

            oom = False
            spill = False
            fwd_ok = False
            bwd_ok = False
            peak_alloc = 0.0
            peak_res = 0.0
            dt = 0.0
            tps = 0.0

            try:
                # Warmup pass (trigger Triton JIT kernels)
                warm_out = model(input_ids=input_ids, labels=labels)
                warm_out.loss.backward()
                model.zero_grad(set_to_none=True)

                torch.cuda.empty_cache()
                torch.cuda.reset_peak_memory_stats()
                torch.cuda.synchronize()

                # Measured pass
                t0 = time.perf_counter()
                out = model(input_ids=input_ids, labels=labels)
                loss = out.loss
                fwd_ok = bool(torch.isfinite(loss).item())

                loss.backward()
                torch.cuda.synchronize()
                t1 = time.perf_counter()

                bwd_ok = all(
                    torch.isfinite(p.grad).all().item()
                    for p in model.parameters()
                    if p.grad is not None
                )
                model.zero_grad(set_to_none=True)

                dt = max(t1 - t0, 1e-6)
                tps = ctx / dt
                peak_alloc_bytes = torch.cuda.max_memory_allocated()
                peak_res_bytes = torch.cuda.max_memory_reserved()
                peak_alloc = bytes_to_gib(peak_alloc_bytes)
                peak_res = bytes_to_gib(peak_res_bytes)

                # Check shared memory / WDDM spill (allocated exceeds physical VRAM)
                if peak_alloc_bytes > total_bytes or peak_res_bytes > total_bytes:
                    spill = True

            except torch.cuda.OutOfMemoryError:
                oom = True
                fwd_ok = False
                bwd_ok = False
                peak_alloc = bytes_to_gib(torch.cuda.max_memory_allocated())
                peak_res = bytes_to_gib(torch.cuda.max_memory_reserved())
                torch.cuda.empty_cache()

            is_stable = bool(
                fwd_ok
                and bwd_ok
                and not oom
                and not spill
                and (peak_alloc <= ceiling_gib)
            )

            entry = {
                "coverage": cov_info["coverage"],
                "peakVramGiB": round(peak_alloc, 3),
                "tokensPerSecond": round(tps, 1),
                "stable": is_stable,
                "dataset_coverage": cov_info["coverage"],
                "records_exceeding_context": cov_info["records_exceeding"],
                "recordsExceedingContext": cov_info["records_exceeding"],
                "p50_tokens": seq_stats["p50"],
                "p50Tokens": seq_stats["p50"],
                "p75_tokens": seq_stats["p75"],
                "p75Tokens": seq_stats["p75"],
                "p90_tokens": seq_stats["p90"],
                "p90Tokens": seq_stats["p90"],
                "p95_tokens": seq_stats["p95"],
                "p95Tokens": seq_stats["p95"],
                "p99_tokens": seq_stats["p99"],
                "p99Tokens": seq_stats["p99"],
                "maximum_tokens": seq_stats["max"],
                "maximumTokens": seq_stats["max"],
                "peak_allocated_vram_gib": round(peak_alloc, 3),
                "peak_reserved_vram_gib": round(peak_res, 3),
                "peakReservedGiB": round(peak_res, 3),
                "tokens_per_second": round(tps, 1),
                "step_duration_seconds": round(dt, 4),
                "stepDuration": round(dt, 4),
                "forward_stability": fwd_ok,
                "forwardStability": fwd_ok,
                "backward_stability": bwd_ok,
                "backwardStability": bwd_ok,
                "oom": oom,
                "shared_memory_spill": spill,
                "sharedMemorySpill": spill,
                "vram_headroom_gib": round(ceiling_gib - peak_alloc, 3),
            }
            results[str(ctx)] = entry
            torch.cuda.empty_cache()

    # 4. Recommendation
    rec = make_recommendation(results, seq_stats, ceiling_gib)

    # 5. Build Report Manifest
    from training.provenance import generate_provenance_record
    prov_meta = generate_provenance_record(
        mock=mock,
        model_path=model_path,
        dataset_path=str(dataset_path),
    )
    report = {
        **prov_meta,
        **results,
        "recommendation": rec,
        "environment": environment,
        "sequence_distribution": seq_stats,
    }

    # 6. Print Preflight & Benchmark Reporting
    print("======================================================================")
    print("QWEN3 CONTEXT BENCHMARK & HARDWARE PROFILE")
    print("======================================================================")
    cuda_env = environment.get("cuda_environment", {})
    print(f"GPU        : {cuda_env.get('device_name')} ({cuda_env.get('total_vram_gib', 0.0)} GiB total)")
    print(f"Framework  : PyTorch {environment.get('pytorch_version')} | Unsloth {environment.get('unsloth_version')}")
    print(f"Model      : {environment.get('model')}")
    qcfg = environment.get("qlora_configuration", {})
    print(f"LoRA       : rank={qcfg.get('rank')}, alpha={qcfg.get('lora_alpha')}, dropout={qcfg.get('lora_dropout')}, 4-bit QLoRA")
    print(f"Ceiling    : {ceiling_gib:.1f} GiB (safety limit)")
    print(f"Dataset    : {dp} ({seq_stats['count']} records)")
    print("----------------------------------------------------------------------")
    print(f"Records: {seq_stats['count']}\n")
    print(f"p50   {seq_stats['p50']}")
    print(f"p75   {seq_stats['p75']}")
    print(f"p90   {seq_stats['p90']}")
    print(f"p95   {seq_stats['p95']}")
    print(f"p99   {seq_stats['p99']}")
    print(f"max   {seq_stats['max']}\n")
    print("Fits:")
    for ctx in sorted(context_lengths):
        cov = context_coverage.get(ctx, {"fits_pct": 100.0})["fits_pct"]
        print(f"{ctx} -> {cov}%")
    print("----------------------------------------------------------------------")
    print(f"{'Context':<8} {'Coverage':<10} {'Exceeding':<10} {'Peak VRAM':<11} {'Reserved':<10} {'Tok/s':<8} {'Fwd':<5} {'Bwd':<5} {'OOM':<5} {'Spill':<6} {'Status':<6}")
    for ctx in sorted(context_lengths):
        res = results.get(str(ctx), {})
        cov_str = f"{res.get('coverage', 0.0)*100:.1f}%"
        exc_str = str(res.get("records_exceeding_context", 0))
        peak_str = f"{res.get('peakVramGiB', 0.0):.2f} GiB"
        res_str = f"{res.get('peakReservedGiB', 0.0):.2f} GiB"
        tps_str = f"{res.get('tokensPerSecond', 0.0):.1f}"
        fwd_str = "OK" if res.get("forward_stability") else "FAIL"
        bwd_str = "OK" if res.get("backward_stability") else "FAIL"
        oom_str = "YES" if res.get("oom") else "No"
        spill_str = "YES" if res.get("shared_memory_spill") else "No"
        status_str = "PASS" if res.get("stable") else "FAIL"
        print(f"{ctx:<8} {cov_str:<10} {exc_str:<10} {peak_str:<11} {res_str:<10} {tps_str:<8} {fwd_str:<5} {bwd_str:<5} {oom_str:<5} {spill_str:<6} {status_str:<6}")
    print("----------------------------------------------------------------------")
    print("Deterministic Recommendation:")
    print(f"  Selected context length : {rec.get('selected_context_length')}")
    print(f"  Policy decision         : {rec.get('policy_decision')}")
    print(f"  Rationale               : {rec.get('rationale')}")
    print("======================================================================")

    # 7. Write Machine-Readable Output
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Benchmark report written to: {out_file}\n")

    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--model", default=DEFAULT_MODEL_PATH,
        help="Path to the base model directory (default: ./base-model)",
    )
    parser.add_argument(
        "--data", "--dataset", dest="dataset", default=DEFAULT_DATASET_PATH,
        help="Path to training dataset JSONL (default: data/quality_candidate/train.jsonl)",
    )
    parser.add_argument(
        "--context", type=int, nargs="+", default=[6144, 8192],
        help="Context lengths to benchmark (default: 6144 8192)",
    )
    parser.add_argument(
        "--output", default=DEFAULT_OUTPUT_PATH,
        help="Path to write JSON benchmark report (default: runs/qwen3_context_benchmark.json)",
    )
    parser.add_argument(
        "--ceiling-gib", type=float, default=VRAM_CEILING_GIB,
        help=f"VRAM safety ceiling in GiB (default: {VRAM_CEILING_GIB})",
    )
    parser.add_argument("--rank", type=int, default=16, help="LoRA rank (default: 16)")
    parser.add_argument("--lora-alpha", type=int, default=16, help="LoRA alpha (default: 16)")
    parser.add_argument("--lora-dropout", type=float, default=0.0, help="LoRA dropout (default: 0.0)")
    parser.add_argument("--mock", action="store_true", help="Run with mock/dry-run benchmark metrics for testing")

    args = parser.parse_args()

    report = run_benchmark(
        model_path=args.model,
        context_lengths=args.context,
        dataset_path=args.dataset,
        output_path=args.output,
        ceiling_gib=args.ceiling_gib,
        rank=args.rank,
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout,
        mock=args.mock,
    )

    rec = report.get("recommendation", {})
    if rec.get("selected_context_length") is None:
        sys.exit(1)


if __name__ == "__main__":
    main()
