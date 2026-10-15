"""
context_decision.py - Data-Driven Context Length Selection and Reporting

Provides utilities to select context length (6144 vs 8192) from an explicit
benchmark report (e.g. runs/qwen3_context_benchmark.json) based on:
- dataset token coverage
- training stability
- VRAM headroom
- speed
- sequence-length distribution

Used by training preflight, inference configurations, and context builder.
"""

import json
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_BENCHMARK_REPORT = str(BASE_DIR / "runs" / "qwen3_context_benchmark.json")


def calculate_percentiles(lengths: List[int]) -> Dict[str, Any]:
    """Calculate p50, p75, p90, p95, p99, min, max, mean for token lengths."""
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

    def p(fraction: float) -> int:
        idx = min(int(n * fraction), n - 1)
        return sorted_lengths[idx]

    return {
        "count": n,
        "min": sorted_lengths[0],
        "max": sorted_lengths[-1],
        "mean": round(sum(sorted_lengths) / n, 1),
        "p50": p(0.50),
        "p75": p(0.75),
        "p90": p(0.90),
        "p95": p(0.95),
        "p99": p(0.99),
    }


def format_preflight_histogram(
    seq_lengths: List[int],
    context_options: List[int] = (6144, 8192),
) -> str:
    """
    Format histogram/summary matching SiteAgent specification:
    Records: N
    p50   ...
    p75   ...
    p90   ...
    p95   ...
    p99   ...
    max   ...

    Fits:
    6144 -> X%
    8192 -> Y%
    """
    stats = calculate_percentiles(seq_lengths)
    n = max(stats["count"], 1)

    lines = [
        f"Records: {stats['count']}\n",
        f"p50   {stats['p50']}",
        f"p75   {stats['p75']}",
        f"p90   {stats['p90']}",
        f"p95   {stats['p95']}",
        f"p99   {stats['p99']}",
        f"max   {stats['max']}\n",
        "Fits:",
    ]
    for ctx in sorted(context_options):
        fits = sum(1 for l in seq_lengths if l <= ctx)
        pct = round((fits / n) * 100, 1)
        lines.append(f"{ctx} -> {pct}%")

    return "\n".join(lines)


def resolve_context_length(
    benchmark_report_path: Optional[str] = None,
    explicit_length: Optional[int] = None,
    default_length: int = 8192,
) -> Tuple[int, Dict[str, Any]]:
    """
    Select context length from an explicit benchmark report.

    Parameters:
        benchmark_report_path: Path to benchmark report JSON (defaults to runs/qwen3_context_benchmark.json).
        explicit_length: Explicit context length if specified on CLI (overrides benchmark recommendation).
        default_length: Fallback length if report is missing or invalid (defaults to 8192).

    Returns:
        Tuple of (selected_context_length, decision_metadata_dict).
    """
    # 1. If user explicitly gave a sequence length on CLI
    if explicit_length is not None:
        if type(explicit_length) is not int or not 256 <= explicit_length <= 8192:
            raise ValueError(f"Context length must be an integer between 256 and 8192; got {explicit_length!r}")
        info = {
            "source": "cli_argument",
            "selected_context_length": explicit_length,
            "policy_decision": "explicit_user_override",
            "rationale": f"Explicit context length {explicit_length} supplied by user.",
        }
        return explicit_length, info

    # 1b. Check ModelRuntimeConfig explicit override if active
    try:
        from agent.config import ModelRuntimeConfig
        if ModelRuntimeConfig._explicit_max_seq_length is not None:
            ov = ModelRuntimeConfig._explicit_max_seq_length
            info = {
                "source": "model_runtime_config",
                "selected_context_length": ov,
                "policy_decision": "runtime_config_override",
                "rationale": f"ModelRuntimeConfig.set_max_seq_length({ov}) configured.",
            }
            return ov, info
    except Exception:
        pass

    # 1c. Environment variable SLM_CONTEXT_LENGTH (if default/no custom report specified)
    import os
    is_default_or_none_report = (
        benchmark_report_path is None
        or str(Path(benchmark_report_path).resolve()) == str(Path(DEFAULT_BENCHMARK_REPORT).resolve())
    )
    env_ctx = os.environ.get("SLM_CONTEXT_LENGTH")
    if env_ctx and is_default_or_none_report:
        try:
            parsed_env = int(env_ctx)
            if 256 <= parsed_env <= 32768:
                info = {
                    "source": "environment_variable",
                    "selected_context_length": parsed_env,
                    "policy_decision": "environment_variable_override",
                    "rationale": f"SLM_CONTEXT_LENGTH={parsed_env} environment variable configured.",
                }
                return parsed_env, info
        except ValueError:
            pass

    # 2. Try loading explicit benchmark report
    report_file = Path(benchmark_report_path or DEFAULT_BENCHMARK_REPORT)
    if not report_file.is_absolute() and not report_file.exists() and (BASE_DIR / report_file).exists():
        report_file = (BASE_DIR / report_file).resolve()
    else:
        report_file = report_file.resolve()

    if report_file.exists():
        try:
            report_data = json.loads(report_file.read_text(encoding="utf-8"))
            if report_data.get("mock") is not False or report_data.get("provenance") != "real":
                raise ValueError("context benchmark must be real execution with mock=false")
            if not isinstance(report_data.get("model_sha256"), str) or report_data.get("model_sha256") in {"", "none"}:
                raise ValueError("context benchmark is missing model identity")
            environment = report_data.get("environment")
            if not isinstance(environment, dict) or not environment.get("model_path"):
                raise ValueError("context benchmark is missing environment identity")
            if not isinstance(report_data, dict) or not isinstance(report_data.get("recommendation"), dict):
                raise ValueError("context benchmark report is missing a recommendation object")
            rec = report_data.get("recommendation", {})
            selected = rec.get("selected_context_length")
            if type(selected) is not int or not 256 <= selected <= 8192:
                raise ValueError("recommendation.selected_context_length must be an integer between 256 and 8192")
            if rec.get("policy_decision") is None or not isinstance(rec.get("policy_decision"), str):
                raise ValueError("recommendation.policy_decision is required")
            if not isinstance(rec.get("rationale", ""), str) or not rec.get("rationale", "").strip():
                raise ValueError("recommendation.rationale is required")
            if selected:
                info = {
                    "source": str(report_file),
                    "selected_context_length": selected,
                    "policy_decision": rec.get("policy_decision", "benchmark_recommended"),
                    "rationale": rec.get("rationale", f"Recommended by benchmark report at {report_file}"),
                    "benchmark_report_file": str(report_file),
                }
                return selected, info
        except (json.JSONDecodeError, OSError, ValueError) as err:
            raise ValueError(f"Invalid context benchmark report {report_file}: {err}") from err

    raise FileNotFoundError(
        f"No valid real context benchmark report found at {report_file}; refusing training."
    )
