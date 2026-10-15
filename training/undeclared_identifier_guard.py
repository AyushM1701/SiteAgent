"""
Undeclared Identifier & Imagined Helper Import Guard for SiteAgent.

Enforces Issue #23 of the SiteAgent Implementation Plan:
1. Detects undeclared identifiers and imagined helper imports in TypeScript diagnostics and runtime output:
   - TS2304: Cannot find name '{id}'
   - TS2307: Cannot find module '{mod}' or its corresponding type declarations
   - TS2552: Cannot find name '{id}'. Did you mean '{suggestion}'?
   - TS2686: '{id}' refers to a UMD global
   - TS2503: Cannot find namespace '{id}'
   - ReferenceError: '{id}' is not defined
2. Static inspection of code to ensure self-contained code compliance:
   - Rejects imagined third-party imports (e.g. '@tanstack/react-table', 'react-hook-form', 'use-undo')
   - Rejects imagined internal helper imports (e.g. '@/hooks/useCart', './utils', '../types')
3. Calculates undeclared-identifier failure rates on benchmark datasets.
4. Evaluates whether the undeclared-identifier failure rate drops on candidate models.
"""

import re
from typing import Any, Dict, List, Optional, Set, Tuple


UNDECLARED_PATTERNS = [
    (
        "TS2304",
        re.compile(r"(?:error\s+)?TS2304:\s*Cannot find name\s*['\"]([^'\"]+)['\"]", re.IGNORECASE),
    ),
    (
        "TS2307",
        re.compile(
            r"(?:error\s+)?TS2307:\s*Cannot find module\s*['\"]([^'\"]+)['\"](?:\s*or its corresponding type declarations)?",
            re.IGNORECASE,
        ),
    ),
    (
        "TS2552",
        re.compile(
            r"(?:error\s+)?TS2552:\s*Cannot find name\s*['\"]([^'\"]+)['\"]\.\s*Did you mean\s*['\"]([^'\"]+)['\"]",
            re.IGNORECASE,
        ),
    ),
    (
        "TS2686",
        re.compile(
            r"(?:error\s+)?TS2686:\s*['\"]([^'\"]+)['\"]\s*refers to a UMD global",
            re.IGNORECASE,
        ),
    ),
    (
        "TS2503",
        re.compile(
            r"(?:error\s+)?TS2503:\s*Cannot find namespace\s*['\"]([^'\"]+)['\"]",
            re.IGNORECASE,
        ),
    ),
    (
        "ReferenceError",
        re.compile(
            r"ReferenceError:\s*([A-Za-z0-9_$]+)\s*is not defined",
            re.IGNORECASE,
        ),
    ),
]

KNOWN_UNINSTALLED_IMAGINED_PACKAGES = {
    "lodash",
    "lodash-es",
    "use-undo",
    "@tanstack/react-table",
    "react-table",
    "react-hook-form",
    "@hookform/resolvers",
    "react-router-dom",
    "react-router",
    "use-onclick-outside",
    "use-hooks",
    "react-use",
    "lucide-react",
    "react-icons",
    "@heroicons/react",
    "date-fns",
    "dayjs",
    "moment",
    "framer-motion",
    "react-beautiful-dnd",
    "@dnd-kit/core",
    "@dnd-kit/sortable",
    "clsx",
    "tailwind-merge",
    "class-variance-authority",
    "zustand",
    "redux",
    "@reduxjs/toolkit",
    "axios",
    "swr",
    "@tanstack/react-query",
}

IMAGINED_LOCAL_MODULE_PREFIXES = (
    "@/hooks/",
    "@/components/",
    "@/utils/",
    "@/lib/",
    "@/types/",
    "../hooks/",
    "../utils/",
    "../types/",
    "./context",
    "./types",
    "./utils",
    "./hooks",
)


def detect_undeclared_identifiers(output_text: str) -> List[Dict[str, Any]]:
    """
    Scans compiler (tsc) or runtime (vitest/node) output text for undeclared identifier diagnostics.
    Returns a list of structured records containing error code, target identifier/module, and context snippet.
    """
    if not output_text:
        return []

    diagnostics: List[Dict[str, Any]] = []
    seen: Set[Tuple[str, str]] = set()

    for line in output_text.splitlines():
        line_clean = line.strip()
        for code, pattern in UNDECLARED_PATTERNS:
            m = pattern.search(line_clean)
            if m:
                target = m.group(1).strip()
                suggestion = m.group(2).strip() if m.lastindex and m.lastindex >= 2 else None
                key = (code, target)
                if key not in seen:
                    seen.add(key)
                    diagnostics.append({
                        "code": code,
                        "identifier": target,
                        "suggestion": suggestion,
                        "line": line_clean,
                    })

    return diagnostics


def is_undeclared_identifier_failure(task_result: Dict[str, Any]) -> bool:
    """
    Determines if a benchmark task result failed because of an undeclared identifier
    or an imagined helper/package import.
    """
    if task_result.get("final_passed", False):
        return False

    tsc_out = task_result.get("tsc_output", "") or ""
    vit_out = task_result.get("vitest_output", "") or ""
    obs_text = ""
    for turn in task_result.get("turn_logs", []):
        obs_text += " " + (turn.get("observation", "") or "")

    combined = f"{tsc_out}\n{vit_out}\n{obs_text}"
    diagnostics = detect_undeclared_identifiers(combined)
    return len(diagnostics) > 0


def scan_for_imagined_imports(code_str: str) -> List[Dict[str, str]]:
    """
    Statically analyzes TSX/TS code to detect imagined third-party packages or non-existent local helper paths.
    Enforces the 'do not invent it' rule before compilation.
    """
    if not code_str:
        return []

    violations: List[Dict[str, str]] = []
    # Match ES6 import declarations: import ... from 'module' or import 'module'
    import_regex = re.compile(r"""(?:import\s+(?:[\w*\s{},$]+from\s+)?['"]([^'"]+)['"])|(?:require\(['"]([^'"]+)['"]\))""")

    for line in code_str.splitlines():
        stripped = line.strip()
        if stripped.startswith("//") or stripped.startswith("/*"):
            continue
        m = import_regex.search(stripped)
        if m:
            module_name = (m.group(1) or m.group(2) or "").strip()
            if not module_name:
                continue

            # Check known uninstalled third-party packages
            base_pkg = module_name.split("/")[0]
            if module_name.startswith("@") and len(module_name.split("/")) >= 2:
                base_pkg = "/".join(module_name.split("/")[:2])

            if base_pkg in KNOWN_UNINSTALLED_IMAGINED_PACKAGES or module_name in KNOWN_UNINSTALLED_IMAGINED_PACKAGES:
                violations.append({
                    "type": "uninstalled_package",
                    "module": module_name,
                    "line": stripped,
                    "message": (
                        f"Imagined uninstalled package '{module_name}'. "
                        "Unless a tool confirms that a package exists: do not invent it."
                    ),
                })

            # Check imagined local relative helper modules (e.g. '@/hooks/useCart', './utils')
            elif any(module_name.startswith(prefix) for prefix in IMAGINED_LOCAL_MODULE_PREFIXES):
                violations.append({
                    "type": "imagined_local_helper",
                    "module": module_name,
                    "line": stripped,
                    "message": (
                        f"Imagined local module '{module_name}'. "
                        "Unless a tool confirms that a file exists: do not invent it. "
                        "Implement helpers self-contained in the TSX file."
                    ),
                })

    return violations


def calculate_undeclared_identifier_rate(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculates the rate and breakdown of undeclared-identifier failures across benchmark tasks.
    """
    total = len(results)
    if total == 0:
        return {
            "total_tasks": 0,
            "undeclared_identifier_failures": 0,
            "undeclared_identifier_failure_rate": 0.0,
            "breakdown_by_code": {},
            "common_identifiers": [],
        }

    failure_count = 0
    code_counts: Dict[str, int] = {}
    identifier_counts: Dict[str, int] = {}

    for res in results:
        tsc_out = res.get("tsc_output", "") or ""
        vit_out = res.get("vitest_output", "") or ""
        obs_text = ""
        for turn in res.get("turn_logs", []):
            obs_text += " " + (turn.get("observation", "") or "")
        combined = f"{tsc_out}\n{vit_out}\n{obs_text}"

        diags = detect_undeclared_identifiers(combined)
        if diags:
            failure_count += 1
            for d in diags:
                code = d["code"]
                ident = d["identifier"]
                code_counts[code] = code_counts.get(code, 0) + 1
                identifier_counts[ident] = identifier_counts.get(ident, 0) + 1

    sorted_identifiers = sorted(identifier_counts.items(), key=lambda x: x[1], reverse=True)

    return {
        "total_tasks": total,
        "undeclared_identifier_failures": failure_count,
        "undeclared_identifier_failure_rate": round(failure_count / total, 4),
        "breakdown_by_code": code_counts,
        "common_identifiers": [
            {"identifier": ident, "count": cnt}
            for ident, cnt in sorted_identifiers[:10]
        ],
    }


def evaluate_undeclared_identifier_drop(
    baseline_metrics: Dict[str, Any],
    candidate_metrics: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Evaluates whether the undeclared-identifier failure rate drops on the development benchmark.
    Returns quantitative delta, percentage point drop, and promotion check pass status.
    """
    base_rate = float(baseline_metrics.get("undeclared_identifier_failure_rate", 0.0))
    cand_rate = float(candidate_metrics.get("undeclared_identifier_failure_rate", 0.0))

    delta = round(cand_rate - base_rate, 4)
    percentage_point_drop = round((base_rate - cand_rate) * 100.0, 2)
    has_dropped = cand_rate < base_rate or (base_rate == 0.0 and cand_rate == 0.0)

    if base_rate > 0:
        relative_reduction_pct = round(((base_rate - cand_rate) / base_rate) * 100.0, 2)
    else:
        relative_reduction_pct = 0.0

    return {
        "baseline_undeclared_rate": base_rate,
        "candidate_undeclared_rate": cand_rate,
        "delta": delta,
        "percentage_point_drop": percentage_point_drop,
        "relative_reduction_pct": relative_reduction_pct,
        "has_dropped": has_dropped,
        "acceptance_criteria_passed": has_dropped,
        "rationale": (
            f"Undeclared-identifier failure rate dropped from {base_rate * 100:.1f}% to {cand_rate * 100:.1f}% "
            f"(-{percentage_point_drop} pp, {relative_reduction_pct:.1f}% relative reduction)."
            if has_dropped
            else f"Undeclared-identifier failure rate did not drop ({base_rate * 100:.1f}% vs {cand_rate * 100:.1f}%)."
        ),
    }
