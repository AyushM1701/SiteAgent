"""
evaluation/site_benchmark_scorer.py - Comprehensive 16-Metric Scoring Engine for Full Websites.

Evaluates generated full-website projects across the 16 mandatory dimensions specified by Issue #25:
1.  prompt fidelity
2.  required section completion
3.  TypeScript
4.  production build
5.  runtime
6.  interactions
7.  responsive design
8.  accessibility
9.  visual structure
10. content quality
11. design diversity
12. dependencies
13. assets
14. 3D runtime/performance
15. repair attempts
16. time-to-preview
"""

import dataclasses
import json
import math
import os
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Set, Tuple, Union

# Attempt relative/absolute imports for repository utilities
BASE_DIR = Path(__file__).resolve().parent.parent

try:
    from agent.site_acceptance import check_site_files
except ImportError:
    check_site_files = None

try:
    from agent.project_validator import (
        run_project_typecheck,
        run_project_build,
        run_browser_runtime_check,
        _ensure_project_configs,
    )
except ImportError:
    run_project_typecheck = None
    run_project_build = None
    run_browser_runtime_check = None
    _ensure_project_configs = None

try:
    from evaluation.diversity_evaluator import (
        SiteDesignSignature,
        extract_site_design_signature,
        evaluate_site_batch_diversity,
    )
except ImportError:
    try:
        from diversity_evaluator import (
            SiteDesignSignature,
            extract_site_design_signature,
            evaluate_site_batch_diversity,
        )
    except ImportError:
        SiteDesignSignature = None
        extract_site_design_signature = None
        evaluate_site_batch_diversity = None

try:
    from evaluation.three_d_performance_validator import (
        validate_three_d_performance,
        THREE_D_PERFORMANCE_CHECK_NAMES,
    )
except ImportError:
    try:
        from three_d_performance_validator import (
            validate_three_d_performance,
            THREE_D_PERFORMANCE_CHECK_NAMES,
        )
    except ImportError:
        validate_three_d_performance = None
        THREE_D_PERFORMANCE_CHECK_NAMES = []

try:
    from agent.motion_patterns import validate_motion_rules
except ImportError:
    try:
        from motion_patterns import validate_motion_rules
    except ImportError:
        validate_motion_rules = None

try:
    from evaluation.motion_benchmark import (
        evaluate_motion_url,
        evaluate_motion_html,
        evaluate_motion_page,
        MotionBenchmarkReport,
    )
except ImportError:
    try:
        from motion_benchmark import (
            evaluate_motion_url,
            evaluate_motion_html,
            evaluate_motion_page,
            MotionBenchmarkReport,
        )
    except ImportError:
        evaluate_motion_url = None
        evaluate_motion_html = None
        evaluate_motion_page = None
        MotionBenchmarkReport = None



REQUIRED_SCORING_DIMENSIONS = [
    "prompt_fidelity",
    "required_section_completion",
    "typescript",
    "production_build",
    "runtime",
    "interactions",
    "responsive_design",
    "accessibility",
    "visual_structure",
    "content_quality",
    "design_diversity",
    "dependencies",
    "assets",
    "three_d_runtime_performance",
    "repair_attempts",
    "time_to_preview",
]

# Section 3.D: 10 Decoupled Independent Outcome Axes
INDEPENDENT_EVALUATION_AXES = [
    "correctness_build_runtime",
    "prompt_fidelity",
    "interaction_behavior",
    "responsive_behavior",
    "accessibility",
    "visual_composition",
    "motion_quality",
    "performance",
    "diversity",
    "fallback_recovery_dependency",
]

# Section 3.E: First-Class Recovery Dependence Metrics
RECOVERY_METRICS = [
    "model_native_success_rate",
    "repair_success_rate",
    "fallback_free_completion_rate",
    "auto_scaffold_usage_rate",
]


@dataclasses.dataclass
class SiteBenchmarkScore:
    """Individual site evaluation across both legacy dimensions and decoupled outcome axes."""
    task_id: str
    domain: str
    project_name: str
    composite_score: float
    passed: bool

    # 16 Individual Dimensions (0.0 to 1.0 each)
    prompt_fidelity: float = 0.0
    required_section_completion: float = 0.0
    typescript: float = 0.0
    production_build: float = 0.0
    runtime: float = 0.0
    interactions: float = 0.0
    responsive_design: float = 0.0
    accessibility: float = 0.0
    visual_structure: float = 0.0
    content_quality: float = 0.0
    design_diversity: float = 0.0
    dependencies: float = 0.0
    assets: float = 0.0
    three_d_runtime_performance: float = 0.0
    repair_attempts: float = 0.0
    time_to_preview: float = 0.0
    motion_quality: float = 0.0

    # Section 3.D & 3.E: Decoupled Outcome Scores & Recovery Metrics
    independent_scores: Dict[str, float] = dataclasses.field(default_factory=dict)
    recovery_metrics: Dict[str, Any] = dataclasses.field(default_factory=dict)
    auto_scaffold_usage_rate: float = 0.0
    model_native_success_rate: float = 1.0
    fallback_free_completion_rate: float = 1.0
    repair_success_rate: float = 1.0

    # Diagnostic metadata
    details: Dict[str, Any] = dataclasses.field(default_factory=dict)
    errors: List[str] = dataclasses.field(default_factory=list)
    warnings: List[str] = dataclasses.field(default_factory=list)
    design_signature: Optional[Dict[str, str]] = None
    is_3d_site: bool = False
    three_d_performance_checks: Dict[str, Any] = dataclasses.field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "domain": self.domain,
            "project_name": self.project_name,
            "composite_score": round(self.composite_score, 4),
            "passed": self.passed,
            "motion_quality": round(self.motion_quality, 4),
            "scores": {
                "prompt_fidelity": _round(self.prompt_fidelity),
                "required_section_completion": _round(self.required_section_completion),
                "typescript": _round(self.typescript),
                "production_build": _round(self.production_build),
                "runtime": _round(self.runtime),
                "interactions": _round(self.interactions),
                "responsive_design": _round(self.responsive_design),
                "accessibility": _round(self.accessibility),
                "visual_structure": _round(self.visual_structure),
                "content_quality": _round(self.content_quality),
                "design_diversity": _round(self.design_diversity),
                "dependencies": _round(self.dependencies),
                "assets": _round(self.assets),
                "three_d_runtime_performance": _round(self.three_d_runtime_performance),
                "repair_attempts": _round(self.repair_attempts),
                "time_to_preview": _round(self.time_to_preview),
            },
            "independent_scores": {k: _round(v) for k, v in self.independent_scores.items()},
            "recovery_metrics": self.recovery_metrics,
            "auto_scaffold_usage_rate": round(self.auto_scaffold_usage_rate, 4),
            "model_native_success_rate": round(self.model_native_success_rate, 4),
            "fallback_free_completion_rate": round(self.fallback_free_completion_rate, 4),
            "repair_success_rate": round(self.repair_success_rate, 4),
            "errors": self.errors,
            "warnings": self.warnings,
            "details": self.details,
            "design_signature": self.design_signature,
            "is_3d_site": self.is_3d_site,
            "three_d_performance_checks": self.three_d_performance_checks,
        }


def _round(value):
    """Scores may be None when a check does not apply."""
    return None if value is None else round(value, 4)


def _applicable_mean(values) -> Optional[float]:
    """Mean over applicable scores; None when no site had the check (A16)."""
    present = [v for v in values if v is not None]
    return round(sum(present) / len(present), 4) if present else None


class SiteBenchmarkScorer:
    """Authoritative scoring engine implementing all 16 full-site evaluation criteria."""

    def __init__(self, workspace_root: Optional[Path] = None):
        self.workspace_root = workspace_root or BASE_DIR

    # 1. Prompt Fidelity
    def score_prompt_fidelity(
        self, prompt_spec: Dict[str, Any], files: Dict[str, str]
    ) -> Tuple[float, Dict[str, Any]]:
        combined_text = " ".join(files.values()).lower()
        details: Dict[str, Any] = {}

        # Each part counts only when the spec gives something to check (A16).
        parts: List[Tuple[float, float]] = []
        expected_kws = [k.lower() for k in prompt_spec.get("domain_keywords", [])]
        matched_kws = [k for k in expected_kws if k in combined_text]
        if expected_kws:
            parts.append((0.50, len(matched_kws) / len(expected_kws)))
        project_name = prompt_spec.get("name", "").lower()
        has_brand = (project_name in combined_text) if project_name else None
        if has_brand is not None:
            parts.append((0.30, 1.0 if has_brand else 0.0))
        title = prompt_spec.get("title", "").lower()
        title_tokens = [w for w in re.findall(r"\w+", title) if len(w) > 3]
        matched_title_tokens = [t for t in title_tokens if t in combined_text]
        if title_tokens:
            parts.append((0.20, len(matched_title_tokens) / len(title_tokens)))

        details["matched_keywords"] = matched_kws
        details["total_keywords"] = expected_kws
        details["has_brand"] = has_brand
        details["applicable"] = bool(parts)
        if not parts:
            return None, details
        score = sum(w * v for w, v in parts) / sum(w for w, _ in parts)
        details["keyword_coverage"] = round(len(matched_kws) / len(expected_kws), 3) if expected_kws else None
        return min(1.0, max(0.0, score)), details

    # 2. Required Section Completion
    def score_required_section_completion(
        self, prompt_spec: Dict[str, Any], files: Dict[str, str]
    ) -> Tuple[float, Dict[str, Any]]:
        required = list(prompt_spec.get("required_sections", []))
        if not required and prompt_spec.get("prompt"):
            # Feed the planner's sections in when the spec lists none (A16).
            try:
                from agent.site_brief import detect_business_type, extract_sections_from_prompt
                text = prompt_spec["prompt"]
                required = [s for s in extract_sections_from_prompt(text, detect_business_type(text))
                            if s not in {"header", "hero", "footer"}]
            except Exception:
                required = []
        if not required:
            return None, {"completed": [], "missing": [], "applicable": False}

        # Normalize existing file stems and code content
        file_stems = {
            Path(p).stem.lower().replace("-", "").replace("_", ""): p
            for p in files.keys()
        }
        app_code = files.get("src/App.tsx", "") or files.get("App.tsx", "")

        completed: List[str] = []
        missing: List[str] = []

        for sec in required:
            norm_sec = sec.lower().replace("-", "").replace("_", "")
            equivalent_stems = {norm_sec}
            if norm_sec in {"navbar", "navigation", "nav", "header"}:
                equivalent_stems.update({"navbar", "navigation", "nav", "header"})
            # Check if file exists matching section name
            found_file = False
            for stem in file_stems.keys():
                if any(alias in stem or stem in alias for alias in equivalent_stems):
                    found_file = True
                    break

            # Check if mentioned / imported in App.tsx
            sec_pascal = "".join(w.capitalize() for w in re.split(r"[-_]", sec))
            found_in_app = (sec_pascal in app_code) or any(alias in app_code.lower() for alias in equivalent_stems)

            if found_file or found_in_app:
                completed.append(sec)
            else:
                missing.append(sec)

        ratio = len(completed) / len(required)
        return ratio, {"completed": completed, "missing": missing, "ratio": round(ratio, 3)}

    # 3. TypeScript Compilation
    def score_typescript(
        self, workspace_dir: Optional[Path], files: Dict[str, str]
    ) -> Tuple[float, Dict[str, Any]]:
        details: Dict[str, Any] = {}
        if workspace_dir and workspace_dir.exists() and run_project_typecheck:
            ts_ok, ts_errors = run_project_typecheck(workspace_dir)
            details["typecheck_passed"] = ts_ok
            details["error_count"] = len(ts_errors)
            details["sample_errors"] = ts_errors[:3]
            return (1.0 if ts_ok else 0.0), details

        # Fallback static TS syntax sanity
        has_tsx = any(k.endswith(".tsx") for k in files.keys())
        has_syntax_break = any("<<<<<<" in v or ">>>>>>" in v for v in files.values())
        score = 1.0 if (has_tsx and not has_syntax_break) else 0.0
        details["static_ts_valid"] = (not has_syntax_break)
        return score, details

    # 4. Production Build
    def score_production_build(
        self, workspace_dir: Optional[Path], files: Dict[str, str]
    ) -> Tuple[float, Dict[str, Any]]:
        details: Dict[str, Any] = {}
        if workspace_dir and workspace_dir.exists() and run_project_build:
            build_ok, build_errors = run_project_build(workspace_dir)
            final_ok = build_ok
            details["build_passed"] = final_ok
            details["error_count"] = len(build_errors)
            details["sample_errors"] = build_errors[:3]
            return (1.0 if final_ok else 0.0), details

        # Fallback check
        has_entry = "index.html" in files or "src/App.tsx" in files or "App.tsx" in files
        return (1.0 if has_entry else 0.0), {"fallback_check": has_entry}

    # 5. Runtime
    def score_runtime(
        self, workspace_dir: Optional[Path], files: Dict[str, str], live_check: bool = False
    ) -> Tuple[float, Dict[str, Any]]:
        details: Dict[str, Any] = {}
        if live_check and workspace_dir and workspace_dir.exists() and run_browser_runtime_check:
            try:
                rt_ok, prev_ok, rt_errors, _ = run_browser_runtime_check(workspace_dir, timeout_s=10)
                details["runtime_passed"] = rt_ok
                details["preview_running"] = prev_ok
                details["errors"] = rt_errors
                return (1.0 if (rt_ok and prev_ok) else (0.5 if prev_ok else 0.0)), details
            except Exception as exc:
                details["live_check_exception"] = str(exc)

        # Static verification: checks root mount in index.html & createRoot in main.tsx
        combined = " ".join(files.values())
        has_create_root = "createRoot" in combined or "ReactDOM" in combined
        has_root_id = "root" in combined
        has_page_crash = "Unhandled rejection" in combined or "Cannot find module" in combined
        score = 1.0 if (has_create_root and has_root_id and not has_page_crash) else 0.6
        details["static_runtime_mount_verified"] = (has_create_root and has_root_id)
        return score, details

    # 6. Interactions
    def score_interactions(
        self, prompt_spec: Dict[str, Any], files: Dict[str, str],
        live_evidence: Optional[Dict[str, Any]] = None,
    ) -> Tuple[float, Dict[str, Any]]:
        combined_code = " ".join(v for k, v in files.items() if k.endswith((".tsx", ".jsx", ".ts", ".js")))
        details: Dict[str, Any] = {}

        # Event handlers
        handlers = re.findall(r"\bon[A-Z][a-zA-Z]+\s*=", combined_code)
        handler_count = len(handlers)

        # State hooks
        state_hooks = re.findall(r"\buse(?:State|Reducer|Ref|Callback|Effect)\b", combined_code)
        hook_count = len(state_hooks)

        # Interactive HTML controls
        interactive_tags = re.findall(r"<(?:button|input|select|textarea|form)\b", combined_code)
        tag_count = len(interactive_tags)

        # Dead placeholder href penalty
        dead_hrefs = len(re.findall(r'href\s*=\s*["\']#["\']', combined_code))

        # Required interactions matching
        req_interactions = prompt_spec.get("required_interactions", [])
        matched_interactions = 0
        for inter in req_interactions:
            # Recognize code evidence for the benchmark's named behaviors.
            # Browser validation remains the authoritative behavior gate.
            key = str(inter).lower()
            if key == "pricing_toggle":
                matched = bool(re.search(r"annual|yearly", combined_code, re.I)
                               and re.search(r"monthly", combined_code, re.I)
                               and re.search(r"(?:billingType|billingCycle|isAnnual)", combined_code))
            elif key == "metrics_tab_filter":
                matched = bool(re.search(r"\.filter\s*\(", combined_code)
                               and re.search(r"(?:activeTab|selectedTab|activeFilter)", combined_code))
            elif key == "mobile_nav_toggle":
                matched = bool(re.search(r"(?:isMenuOpen|mobileMenu|navOpen)", combined_code)
                               and re.search(r"aria-(?:controls|expanded|label)", combined_code))
            else:
                tokens = [t.lower() for t in re.split(r"[-_]", key) if t]
                matched = all(tok in combined_code.lower() for tok in tokens)
            if matched:
                matched_interactions += 1

        req_ratio = (matched_interactions / max(1, len(req_interactions))) if req_interactions else 1.0

        # Interaction density sub-score
        density = min(1.0, (handler_count * 0.15 + hook_count * 0.15 + tag_count * 0.05))
        penalty = min(0.30, dead_hrefs * 0.05)

        final_score = min(1.0, max(0.0, 0.40 * req_ratio + 0.60 * density - penalty))
        # Static handlers demonstrate intent only.  Interaction correctness is a
        # live outcome and must have a browser receipt for a passing score.
        live_ok = isinstance(live_evidence, dict) and live_evidence.get("passed") is True
        if not live_ok:
            final_score = 0.0
            details["live_evidence_required"] = True
            details["live_evidence_present"] = False
        else:
            details["live_evidence_present"] = True
        details["handler_count"] = handler_count
        details["hook_count"] = hook_count
        details["tag_count"] = tag_count
        details["dead_hrefs"] = dead_hrefs
        details["req_interactions_ratio"] = round(req_ratio, 3)

        return final_score, details

    # 7. Responsive Design
    def score_responsive_design(self, files: Dict[str, str]) -> Tuple[float, Dict[str, Any]]:
        css_content = " ".join(v for k, v in files.items() if k.endswith(".css"))
        tsx_content = " ".join(v for k, v in files.items() if k.endswith((".tsx", ".jsx")))
        details: Dict[str, Any] = {}

        # Media query breakpoints (mobile, tablet, desktop)
        media_queries = re.findall(r"@media[^{]+{", css_content)
        # Tailwind breakpoint utilities compile through the Vite plugin, so
        # their media rules do not appear in authored CSS.
        tailwind_breakpoints = set(re.findall(r"\b(?:sm|md|lg|xl|2xl):[\w/-]+", tsx_content))
        has_mobile_bp = bool(re.search(r"max-width:\s*(?:375|480|640|768)px", css_content)) or any(
            bp.startswith(("sm:", "md:")) for bp in tailwind_breakpoints
        )
        has_desktop_bp = bool(re.search(r"min-width:\s*(?:768|1024|1280)px", css_content)) or any(
            bp.startswith(("md:", "lg:", "xl:", "2xl:")) for bp in tailwind_breakpoints
        )

        # Fluid units and layouts
        has_flex_wrap = "flex-wrap" in css_content or "wrap" in css_content or "flex-wrap" in tsx_content
        has_grid_auto = "auto-fit" in css_content or "auto-fill" in css_content or "minmax" in css_content or bool(re.search(r"\b(?:grid-cols-|(?:sm|md|lg):grid-cols-)", tsx_content))
        has_clamp = "clamp(" in css_content
        has_relative_units = bool(re.search(r"\b(?:rem|vh|vw|%)\b", css_content))

        # Mobile menu/nav toggle in TSX
        has_mobile_menu = bool(re.search(r"(?:mobileMenu|isMenuOpen|isOpen|menuOpen|navOpen)", tsx_content))

        sub_scores = [
            0.30 if ((media_queries or tailwind_breakpoints) and has_mobile_bp) else (0.15 if (media_queries or tailwind_breakpoints) else 0.0),
            0.20 if has_desktop_bp else 0.10,
            0.20 if (has_flex_wrap or has_grid_auto) else 0.0,
            0.15 if (has_clamp or has_relative_units) else 0.05,
            0.15 if has_mobile_menu else 0.05,
        ]
        score = min(1.0, sum(sub_scores))
        details["media_query_count"] = len(media_queries)
        details["has_mobile_bp"] = has_mobile_bp
        details["has_desktop_bp"] = has_desktop_bp
        details["has_grid_auto"] = has_grid_auto
        details["has_mobile_menu"] = has_mobile_menu

        return score, details

    # 8. Accessibility
    def score_accessibility(self, files: Dict[str, str]) -> Tuple[float, Dict[str, Any]]:
        tsx_content = " ".join(v for k, v in files.items() if k.endswith((".tsx", ".jsx")))
        css_content = " ".join(v for k, v in files.items() if k.endswith(".css"))
        details: Dict[str, Any] = {}

        # Semantic landmark tags
        landmarks = {"header", "nav", "main", "section", "footer"}
        found_landmarks = {tag for tag in landmarks if f"<{tag}" in tsx_content}

        # Heading hierarchy
        headings = {f"h{i}" for i in range(1, 4) if f"<h{i}" in tsx_content}

        # ARIA attributes
        aria_attrs = re.findall(r"\baria-[a-z]+\s*=", tsx_content)
        role_attrs = re.findall(r'\brole\s*=\s*["\'][a-z]+["\']', tsx_content)

        # Focus visible
        has_focus_visible = ":focus-visible" in css_content or ":focus" in css_content

        # Alt tags on images
        imgs = re.findall(r"<img\b[^>]*>", tsx_content)
        imgs_with_alt = [img for img in imgs if 'alt="' in img or "alt='" in img]
        img_alt_ratio = (len(imgs_with_alt) / max(1, len(imgs))) if imgs else 1.0

        landmark_score = len(found_landmarks) / len(landmarks)
        heading_score = len(headings) / 3.0
        aria_score = min(1.0, (len(aria_attrs) + len(role_attrs)) / 4.0)
        focus_score = 1.0 if has_focus_visible else 0.5

        score = 0.35 * landmark_score + 0.20 * heading_score + 0.20 * aria_score + 0.15 * focus_score + 0.10 * img_alt_ratio
        details["found_landmarks"] = list(found_landmarks)
        details["aria_count"] = len(aria_attrs) + len(role_attrs)
        details["has_focus_visible"] = has_focus_visible
        details["headings_found"] = list(headings)

        return min(1.0, max(0.0, score)), details

    # 9. Visual Structure
    def score_visual_structure(self, files: Dict[str, str]) -> Tuple[float, Dict[str, Any]]:
        details: Dict[str, Any] = {"evidence_level": "static_guardrail", "professional_visual_quality_verified": False}
        combined_text = " ".join(files.values())
        css_content = " ".join(v for k, v in files.items() if k.endswith(".css"))

        # Check for count leaks (e.g. "(6 cards)", "Enterprise capability for 3 cards")
        count_leak = bool(re.search(r'Enterprise capability for \d+ cards|>\s*\d+ cards\s*<|\(\d+ cards\)', combined_text))

        # Check CSS scoping
        unscoped_issues = 0
        acceptance_malformed = False
        if check_site_files:
            res = check_site_files(files)
            if "static_passed" not in res or not isinstance(res.get("static_passed"), bool):
                details["violations"].append("Malformed acceptance result: static_passed must be a boolean")
                acceptance_malformed = True
            elif not res["static_passed"]:
                unscoped_issues = len([e for e in res.get("errors", []) if "unscoped" in e or "css" in e])

        # Grid / card container presence
        has_grid_cards = bool(re.search(r"(?:grid|cards|card-grid|columns|container|wrapper)", css_content, re.I))

        # Spacing and layout hierarchy
        has_padding_margins = "padding" in css_content and "margin" in css_content

        score = 1.0
        if acceptance_malformed:
            score = 0.0
        if count_leak:
            score -= 0.30
        if unscoped_issues > 0:
            score -= min(0.30, unscoped_issues * 0.10)
        if not has_grid_cards:
            score -= 0.20
        if not has_padding_margins:
            score -= 0.10

        details["count_leak"] = count_leak
        details["unscoped_issues"] = unscoped_issues
        details["has_grid_cards"] = has_grid_cards

        return min(1.0, max(0.0, score)), details

    # 10. Content Quality
    def score_content_quality(self, files: Dict[str, str]) -> Tuple[float, Dict[str, Any]]:
        combined_text = " ".join(files.values())
        details: Dict[str, Any] = {}

        # Check for lorem ipsum
        has_lorem = bool(re.search(r"\blorem ipsum\b|dolor sit amet|consectetur adipiscing", combined_text, re.I))

        # Check for fake contacts (example.com, 555 numbers)
        has_fake_contacts = bool(re.search(r"\bexample\.com\b|\(555\)\s?\d{3}|555-\d{4}", combined_text, re.I))

        # Check for fabricated testimonials (CEO of Acme, etc.)
        has_fake_testimonials = bool(re.search(r"(?:CEO|CTO|CPO|COO|VP)\s+(?:of|at)\s+[A-Z][a-z]+", combined_text))

        # Copy richness: check word count of rendered JSX strings
        tsx_text = " ".join(v for k, v in files.items() if k.endswith((".tsx", ".jsx")))
        jsx_words = re.findall(r">([^<]+)<", tsx_text)
        total_text = " ".join(w.strip() for w in jsx_words if w.strip())
        word_count = len(total_text.split())

        # Score by the absence of placeholder content, not by word count (A16):
        # concise, honest copy is not a defect.
        has_placeholder_names = bool(re.search(
            r"\b(?:John|Jane)\s+(?:Doe|Smith)\b|\bAcme(?:\s+(?:Corp|Inc|Co))?\b|\bYour (?:Company|Brand|Name)\b|\bCompany Name\b",
            combined_text))
        has_placeholder_hosts = bool(re.search(
            r"via\.placeholder\.com|placehold\.(?:co|it)|placekitten\.com|picsum\.photos|dummyimage\.com", combined_text, re.I))

        score = 1.0
        if has_placeholder_names:
            score -= 0.25
        if has_placeholder_hosts:
            score -= 0.25
        if has_lorem:
            score -= 0.40
        if has_fake_contacts:
            score -= 0.25
        if has_fake_testimonials:
            score -= 0.20

        details["has_lorem"] = has_lorem
        details["has_fake_contacts"] = has_fake_contacts
        details["has_fake_testimonials"] = has_fake_testimonials
        details["copy_word_count"] = word_count
        details["has_placeholder_names"] = has_placeholder_names
        details["has_placeholder_hosts"] = has_placeholder_hosts

        return min(1.0, max(0.0, score)), details

    # 11. Design Diversity
    def score_design_diversity(self, files: Dict[str, str]) -> Tuple[float, Dict[str, Any]]:
        css_content = " ".join(v for k, v in files.items() if k.endswith(".css"))
        details: Dict[str, Any] = {"evidence_level": "token_variety_heuristic", "palette_coherence_verified": False}

        # CSS custom properties
        vars_found = set(re.findall(r"--[a-zA-Z0-9_-]+", css_content))

        # Color token palette variety
        colors_found = set(re.findall(r"#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})\b|rgba?\([^)]+\)|hsl\([^)]+\)", css_content))

        # Typography variety
        font_families = set(re.findall(r"font-family\s*:\s*([^;]+);", css_content))

        # Border radius / shadow tokens
        has_radii = "border-radius" in css_content
        has_shadows = "box-shadow" in css_content

        var_score = min(1.0, len(vars_found) / 6.0)
        color_score = min(1.0, len(colors_found) / 4.0)
        font_score = min(1.0, len(font_families) / 1.0)
        polish_score = 0.5 * (1.0 if has_radii else 0.0) + 0.5 * (1.0 if has_shadows else 0.0)

        score = 0.35 * var_score + 0.30 * color_score + 0.20 * font_score + 0.15 * polish_score
        details["vars_count"] = len(vars_found)
        details["colors_count"] = len(colors_found)
        details["font_families"] = list(font_families)[:2]

        return min(1.0, max(0.0, score)), details

    # 12. Dependencies
    def score_dependencies(
        self, workspace_dir: Optional[Path], files: Dict[str, str]
    ) -> Tuple[float, Dict[str, Any]]:
        details: Dict[str, Any] = {}
        pkg_data: Dict[str, Any] = {}

        if workspace_dir and (workspace_dir / "package.json").exists():
            try:
                pkg_data = json.loads((workspace_dir / "package.json").read_text(encoding="utf-8"))
            except Exception:
                pass
        elif "package.json" in files:
            try:
                pkg_data = json.loads(files["package.json"])
            except Exception:
                pass

        declared_deps = set(pkg_data.get("dependencies", {}).keys()) | set(pkg_data.get("devDependencies", {}).keys())
        declared_deps.update({"react", "react-dom", "react/jsx-runtime", "vite", "typescript", "lucide-react", "three", "@types/three"})

        # Scan imports in all tsx/ts files
        all_imports: Set[str] = set()
        for p, code in files.items():
            if p.endswith((".tsx", ".ts", ".jsx", ".js")):
                for imp in re.findall(r'(?:import|from)\s+["\']([^"\']+)["\']', code):
                    # Filter relative imports and CSS imports
                    if not imp.startswith(".") and not imp.startswith("/") and not imp.endswith(".css"):
                        # Extract top-level package name (e.g. @types/three or three)
                        parts = imp.split("/")
                        pkg_root = f"{parts[0]}/{parts[1]}" if imp.startswith("@") and len(parts) > 1 else parts[0]
                        all_imports.add(pkg_root)

        undeclared = [imp for imp in all_imports if imp not in declared_deps]
        score = 1.0 if not undeclared else max(0.0, 1.0 - (len(undeclared) * 0.35))

        details["declared_deps"] = sorted(list(declared_deps))[:10]
        details["detected_imports"] = sorted(list(all_imports))
        details["undeclared_imports"] = undeclared

        return score, details

    # 13. Assets
    def score_assets(self, files: Dict[str, str]) -> Tuple[float, Dict[str, Any]]:
        tsx_content = " ".join(v for k, v in files.items() if k.endswith((".tsx", ".jsx")))
        details: Dict[str, Any] = {}

        # Inline SVG usage
        svgs = re.findall(r"<svg\b[^>]*>", tsx_content)
        svg_count = len(svgs)

        # Lucide vector icons or valid icons
        has_vector_icons = bool(re.search(r"from\s+['\"]lucide-react['\"]|<svg", tsx_content))

        # Check for unverified / hallucinatory external hotlinks
        broken_hotlinks = re.findall(r'https?://[^\s"\'<>]+(?:unsplash|placeholder|fakeimg)[^\s"\'<>]*', tsx_content)

        score = 1.0
        if svg_count == 0 and not has_vector_icons:
            score -= 0.30
        if broken_hotlinks:
            score -= min(0.40, len(broken_hotlinks) * 0.15)

        details["svg_count"] = svg_count
        details["has_vector_icons"] = has_vector_icons
        details["broken_hotlinks_count"] = len(broken_hotlinks)

        return min(1.0, max(0.0, score)), details

    # 14. 3D Runtime / Performance
    def score_three_d_runtime_performance(
        self,
        prompt_spec: Dict[str, Any],
        files: Dict[str, str],
        turn_logs: Optional[List[Dict[str, Any]]] = None,
    ) -> Tuple[float, Dict[str, Any]]:
        combined = " ".join(files.values())
        needs_3d = bool(
            prompt_spec.get("has_3d", False)
            or prompt_spec.get("has_webgl", False)
            or prompt_spec.get("uses3D", False)
            or prompt_spec.get("uses_3d", False)
            or ("@react-three/fiber" in combined)
            or ("<Canvas" in combined)
        )
        details: Dict[str, Any] = {"needs_3d": needs_3d, "is_3d_site": needs_3d}

        # If site does not require or contain 3D/WebGL, award full neutral score
        if not needs_3d:
            return 1.0, details

        # Run 6 performance validation checks (Issue #28)
        perf_score = 1.0
        perf_report: Dict[str, Any] = {}
        if validate_three_d_performance is not None:
            perf_report = validate_three_d_performance(files, runtime_logs=turn_logs)
            details["three_d_checks"] = perf_report.get("checks", {})
            details["all_checks_passed"] = perf_report.get("all_passed", False)
            details["failed_checks"] = perf_report.get("failed_checks", [])
            perf_score = perf_report.get("score", 0.0)

        # Baseline architectural capabilities
        has_canvas = ("<canvas" in combined.lower()) or ("<Canvas" in combined)
        has_webgl_context = ("webgl" in combined.lower()) or ("three" in combined.lower()) or ("scene" in combined.lower())
        has_animation_loop = ("requestanimationframe" in combined.lower()) or ("useframe" in combined.lower()) or ("usetick" in combined.lower())
        has_cleanup = ("cancelanimationframe" in combined.lower()) or ("dispose" in combined.lower()) or ("removeeventlistener" in combined.lower()) or ("invalidate" in combined.lower())
        has_motion_control = ("prefers-reduced-motion" in combined.lower()) or ("pause" in combined.lower()) or ("isplaying" in combined.lower())

        feature_sub_scores = [
            0.25 if has_canvas else 0.0,
            0.20 if has_webgl_context else 0.0,
            0.20 if has_animation_loop else 0.0,
            0.15 if has_cleanup else 0.0,
            0.20 if has_motion_control else 0.0,
        ]
        base_feature_score = sum(feature_sub_scores)

        # If required 3D canvas is completely absent, award 0.0
        if (perf_report and not perf_report.get("scene_contract", {}).get("passed", False)) or (not has_canvas and not has_webgl_context):
            final_3d_score = 0.0
        else:
            # 50% base features + 50% strict performance checks
            final_3d_score = (0.50 * base_feature_score) + (0.50 * perf_score)

        details["has_canvas"] = has_canvas
        details["has_webgl_context"] = has_webgl_context
        details["has_animation_loop"] = has_animation_loop
        details["has_cleanup"] = has_cleanup
        details["has_motion_control"] = has_motion_control
        details["performance_checks_score"] = perf_score

        return min(1.0, max(0.0, final_3d_score)), details

    # 15. Repair Attempts
    def score_repair_attempts(
        self, turn_logs: Optional[List[Dict[str, Any]]]
    ) -> Tuple[float, Dict[str, Any]]:
        details: Dict[str, Any] = {}
        if not turn_logs:
            return 1.0, {"repair_attempts": 0}

        # Count turns flagged as repair / error / auto_recovered
        repairs = 0
        for entry in turn_logs:
            act = entry.get("action", "")
            if "error" in act or "violation" in act or "repair" in act or entry.get("auto_recovered"):
                repairs += 1

        details["repair_count"] = repairs
        if repairs == 0:
            return 1.0, details
        elif repairs == 1:
            return 0.85, details
        elif repairs == 2:
            return 0.70, details
        elif repairs == 3:
            return 0.50, details
        else:
            return max(0.0, 1.0 - (0.20 * repairs)), details

    # 16. Time to Preview
    def score_time_to_preview(self, elapsed_seconds: float) -> Tuple[float, Dict[str, Any]]:
        details = {"elapsed_seconds": round(elapsed_seconds, 2)}
        if elapsed_seconds <= 15.0:
            return 1.0, details
        elif elapsed_seconds <= 30.0:
            return 0.85, details
        elif elapsed_seconds <= 60.0:
            return 0.70, details
        elif elapsed_seconds <= 120.0:
            return 0.50, details
        else:
            return max(0.15, 1.0 - (elapsed_seconds / 240.0)), details

    # 17. Motion Quality (Section 3.D, Section 5, Section 6, Section 7)
    def score_motion_quality(
        self,
        files: Dict[str, str],
        motion_specs: Optional[List[Any]] = None,
        workspace_dir: Optional[Path] = None,
        package_json: Optional[Union[Dict[str, Any], str, Path]] = None,
        preview_url: Optional[str] = None,
        html_content: Optional[str] = None,
    ) -> Tuple[float, Dict[str, Any]]:
        css_content = " ".join(v for k, v in files.items() if k.endswith(".css")).lower()
        tsx_content = " ".join(v for k, v in files.items() if k.endswith((".tsx", ".jsx"))).lower()
        details: Dict[str, Any] = {}

        # 1. CSS transitions with explicit properties
        has_transitions = "transition" in css_content
        # 2. Hover / focus states
        has_hover_states = (":hover" in css_content) or ("hover:" in tsx_content) or (":focus-visible" in css_content)
        # 3. Keyframes or animated loops
        has_keyframes = ("@keyframes" in css_content) or ("animation:" in css_content) or ("requestanimationframe" in tsx_content)
        # 4. Reduced-motion accessibility support
        has_reduced_motion = "prefers-reduced-motion" in css_content
        # 5. Transform / opacity based (smooth hardware acceleration)
        uses_transforms = "transform" in css_content or "opacity" in css_content

        score = 0.0
        if has_transitions:
            score += 0.25
        if has_hover_states:
            score += 0.25
        if has_keyframes:
            score += 0.20
        if uses_transforms:
            score += 0.15
        if has_reduced_motion:
            score += 0.15

        details["has_transitions"] = has_transitions
        details["has_hover_states"] = has_hover_states
        details["has_keyframes"] = has_keyframes
        details["uses_transforms"] = uses_transforms
        details["has_reduced_motion"] = has_reduced_motion
        details["evidence_level"] = "source_heuristic"
        details["behavior_verified"] = False

        # Integrate Section 5 & 6 Motion Implementation Rules & Library Policy validation
        if validate_motion_rules is not None:
            rules_res = validate_motion_rules(
                files=files,
                motion_specs=motion_specs,
                package_json=package_json,
                workspace_dir=workspace_dir,
            )
            details["rules_validation"] = rules_res.to_dict()
            details["passed_rules"] = rules_res.passed_rules
            details["violations"] = rules_res.violations
            details["motion_rules_score"] = rules_res.score

            if rules_res.violations:
                # Deduct 0.2 per hard violation (e.g. wheel hijacking, missing cleanup, unverified packages)
                penalty = min(0.6, len(rules_res.violations) * 0.2)
                score = max(0.0, score - penalty)
            # Composite with rules score (50% base primitives, 50% strict implementation contract)
            score = (score * 0.5) + (rules_res.score * 0.5)

        # Section 7: Playwright Behavioral & Performance Motion Benchmark (if preview URL or HTML is provided)
        if evaluate_motion_url is not None and preview_url:
            try:
                motion_report = evaluate_motion_url(
                    url=preview_url,
                    motion_specs=motion_specs,
                    timeout_s=12,
                )
                details["behavioral_motion_benchmark"] = motion_report.to_dict()
                details["behavior_verified"] = bool(motion_report.passed)
                # 40% static/rules, 60% real Playwright browser behavioral verification
                score = (score * 0.4) + (motion_report.composite_score * 0.6)
            except Exception as ex:
                details["behavioral_motion_benchmark_error"] = str(ex)
        elif evaluate_motion_html is not None and html_content:
            try:
                motion_report = evaluate_motion_html(
                    html_content=html_content,
                    motion_specs=motion_specs,
                    timeout_s=10,
                )
                details["behavioral_motion_benchmark"] = motion_report.to_dict()
                details["behavior_verified"] = bool(motion_report.passed)
                score = (score * 0.4) + (motion_report.composite_score * 0.6)
            except Exception as ex:
                details["behavioral_motion_benchmark_error"] = str(ex)

        return min(1.0, max(0.0, score)), details


    # First-Class Recovery Metrics Computation (Section 3.E)
    def compute_recovery_metrics(
        self, prompt_spec: Dict[str, Any], turn_logs: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        required_sections = prompt_spec.get("required_sections", [])
        total_sections = max(1, len(required_sections) if required_sections else 4)

        if not turn_logs:
            return {
                "model_native_success_rate": 1.0,
                "repair_success_rate": 1.0,
                "fallback_free_completion_rate": 1.0,
                "auto_scaffold_usage_rate": 0.0,
                "auto_scaffolded_count": 0,
                "repaired_count": 0,
                "native_count": total_sections,
                "total_sections": total_sections,
            }

        auto_scaffolded_sections = set()
        repair_needed_sections = set()

        for entry in turn_logs:
            sec = entry.get("section")
            act = entry.get("action", "")
            is_auto = bool(entry.get("auto_recovered") or entry.get("fallback_generated") or act in {
                "write_site_fallback", "write_site_auto_guarantee"
            })
            if is_auto and sec:
                auto_scaffolded_sections.add(sec)
            elif ("repair" in act or "error" in act or "mismatch" in act or "no_css" in act
                  or act in {"structural_cap_auto_fix", "structural_auto_fix"}) and sec:
                repair_needed_sections.add(sec)

        auto_cnt = len(auto_scaffolded_sections)
        repaired_cnt = len(repair_needed_sections - auto_scaffolded_sections)
        native_cnt = max(0, total_sections - auto_cnt - repaired_cnt)

        auto_scaffold_usage_rate = round(auto_cnt / total_sections, 4)
        fallback_free_rate = 1.0 if auto_cnt == 0 else 0.0
        repair_success_rate = 1.0 if (repaired_cnt + auto_cnt) == 0 else round(repaired_cnt / (repaired_cnt + auto_cnt), 4)
        model_native_rate = round(native_cnt / total_sections, 4)

        return {
            "model_native_success_rate": model_native_rate,
            "repair_success_rate": repair_success_rate,
            "fallback_free_completion_rate": fallback_free_rate,
            "auto_scaffold_usage_rate": auto_scaffold_usage_rate,
            "auto_scaffolded_count": auto_cnt,
            "repaired_count": repaired_cnt,
            "native_count": native_cnt,
            "total_sections": total_sections,
        }

    # Comprehensive Evaluation Entry Point
    def evaluate_site(
        self,
        prompt_spec: Dict[str, Any],
        files: Dict[str, str],
        workspace_dir: Optional[Path] = None,
        turn_logs: Optional[List[Dict[str, Any]]] = None,
        elapsed_seconds: float = 12.0,
        live_browser_check: bool = False,
    ) -> SiteBenchmarkScore:
        """Evaluates a generated website across all criteria, independent outcome axes, and recovery metrics."""
        task_id = prompt_spec.get("task_id", "unknown_task")
        domain = prompt_spec.get("domain", "general")
        project_name = prompt_spec.get("name", "SiteApp")

        # 1. Prompt fidelity
        s_prompt, d_prompt = self.score_prompt_fidelity(prompt_spec, files)
        # 2. Required section completion
        s_sections, d_sections = self.score_required_section_completion(prompt_spec, files)
        # 3. TypeScript
        s_ts, d_ts = self.score_typescript(workspace_dir, files)
        # 4. Production build
        s_build, d_build = self.score_production_build(workspace_dir, files)
        # 5. Runtime
        s_rt, d_rt = self.score_runtime(workspace_dir, files, live_check=live_browser_check)
        # 6. Interactions
        live_evidence = prompt_spec.get("live_interaction_evidence")
        s_inter, d_inter = self.score_interactions(prompt_spec, files, live_evidence)
        # 7. Responsive design
        s_resp, d_resp = self.score_responsive_design(files)
        # 8. Accessibility
        s_a11y, d_a11y = self.score_accessibility(files)
        # 9. Visual structure
        s_vis, d_vis = self.score_visual_structure(files)
        # 10. Content quality
        s_content, d_content = self.score_content_quality(files)
        # 11. Design diversity
        s_div, d_div = self.score_design_diversity(files)
        # 12. Dependencies
        s_deps, d_deps = self.score_dependencies(workspace_dir, files)
        # 13. Assets
        s_assets, d_assets = self.score_assets(files)
        # 14. 3D Runtime / Performance
        s_3d, d_3d = self.score_three_d_runtime_performance(prompt_spec, files, turn_logs=turn_logs)
        # 15. Repair attempts
        s_repairs, d_repairs = self.score_repair_attempts(turn_logs)
        # 16. Time to preview
        s_ttp, d_ttp = self.score_time_to_preview(elapsed_seconds)
        # 17. Motion quality (Section 3.D, Section 5, Section 6)
        motion_plan = prompt_spec.get("motion_plan") or prompt_spec.get("motion_specs")
        s_motion, d_motion = self.score_motion_quality(
            files, motion_specs=motion_plan, workspace_dir=workspace_dir
        )

        # First-Class Recovery Dependence Metrics (Section 3.E)
        rec_metrics = self.compute_recovery_metrics(prompt_spec, turn_logs)

        # Composite score: balanced mean with emphasis on build/runtime/completion
        weights = {
            "prompt_fidelity": 0.08,
            "required_section_completion": 0.12,
            "typescript": 0.10,
            "production_build": 0.10,
            "runtime": 0.10,
            "interactions": 0.08,
            "responsive_design": 0.06,
            "accessibility": 0.06,
            "visual_structure": 0.05,
            "content_quality": 0.05,
            "design_diversity": 0.04,
            "dependencies": 0.04,
            "assets": 0.04,
            "three_d_runtime_performance": 0.04,
            "repair_attempts": 0.02,
            "time_to_preview": 0.02,
        }
        total_weight = sum(weights.values())
        raw_scores = {
            "prompt_fidelity": s_prompt,
            "required_section_completion": s_sections,
            "typescript": s_ts,
            "production_build": s_build,
            "runtime": s_rt,
            "interactions": s_inter,
            "responsive_design": s_resp,
            "accessibility": s_a11y,
            "visual_structure": s_vis,
            "content_quality": s_content,
            "design_diversity": s_div,
            "dependencies": s_deps,
            "assets": s_assets,
            "three_d_runtime_performance": s_3d,
            "repair_attempts": s_repairs,
            "time_to_preview": s_ttp,
        }

        # Not-applicable dimensions (None) are excluded from the mean (A16).
        applicable = [dim for dim in REQUIRED_SCORING_DIMENSIONS if raw_scores[dim] is not None]
        total_weight = sum(weights[dim] for dim in applicable) or 1.0
        base_composite = sum(raw_scores[dim] * weights[dim] for dim in applicable) / total_weight

        # Section 3.E: Penalize recovery dependence
        # A model that needs auto-scaffolding for every site is not stronger.
        auto_usage = rec_metrics.get("auto_scaffold_usage_rate", 0.0)
        recovery_penalty = round(auto_usage * 0.40, 4)
        composite = round(max(0.0, base_composite - recovery_penalty), 4)

        # Section 3.D: 10 Decoupled Independent Outcome Axes
        correctness_build_runtime = round(0.40 * s_ts + 0.40 * s_build + 0.20 * s_rt, 4)
        prompt_fidelity_score = round(s_prompt, 4) if s_prompt is not None else None
        interaction_behavior_score = round(s_inter, 4)
        responsive_behavior_score = round(s_resp, 4)
        accessibility_score = round(s_a11y, 4)
        visual_composition_score = round(s_vis, 4)
        motion_quality_score = round(s_motion, 4)
        performance_score = round(0.35 * s_deps + 0.35 * s_assets + 0.30 * s_3d, 4)
        diversity_score = round(s_div, 4)
        fallback_recovery_dependency = round(
            max(0.0, 1.0 - (1.0 * auto_usage) - (0.15 * (1.0 - rec_metrics["model_native_success_rate"]))),
            4
        )

        independent_scores = {
            "correctness_build_runtime": correctness_build_runtime,
            "prompt_fidelity": prompt_fidelity_score,
            "interaction_behavior": interaction_behavior_score,
            "responsive_behavior": responsive_behavior_score,
            "accessibility": accessibility_score,
            "visual_composition": visual_composition_score,
            "motion_quality": motion_quality_score,
            "performance": performance_score,
            "diversity": diversity_score,
            "fallback_recovery_dependency": fallback_recovery_dependency,
        }

        # A runnable site with a remaining fallback placeholder is incomplete
        # even if its weighted score is high. Repaired fallbacks retain their
        # recovery penalty but can pass once the placeholder is replaced.
        remaining_fallbacks = [
            path for path, source in files.items()
            if path.endswith((".tsx", ".jsx"))
            and re.search(r'data-fallback\s*=\s*["\']true["\']', source)
        ]
        has_live_workspace = bool(workspace_dir and workspace_dir.exists())
        passed = (
            s_ts >= 0.99
            and has_live_workspace
            and s_build >= 0.99 and s_rt >= 0.99
            and (s_sections is None or s_sections >= 0.99) and composite >= 0.65
            and not remaining_fallbacks and auto_usage <= 0.50
            and (not d_3d.get("needs_3d") or d_3d.get("all_checks_passed", False))
            and s_inter >= 0.99
        )

        errors: List[str] = []
        warnings: List[str] = []
        if s_ts < 0.99:
            errors.append("TypeScript compilation failed.")
        if s_build < 0.99:
            errors.append("Production build failed.")
        if s_rt < 0.99:
            errors.append("Browser runtime failed.")
        if s_sections is not None and s_sections < 0.99:
            errors.append(f"Section completion too low ({s_sections:.1%}).")
        if d_3d.get("needs_3d") and not d_3d.get("all_checks_passed", False):
            errors.append("3D scene contract or static performance validation failed.")
        if remaining_fallbacks:
            errors.append(f"Auto-scaffold fallback remains in {len(remaining_fallbacks)} section(s).")
        if auto_usage > 0.50:
            errors.append(f"Excessive auto-scaffolding dependence ({auto_usage:.1%} > 50.0%).")
        if d_content.get("has_lorem"):
            warnings.append("Lorem ipsum placeholder detected.")
        if d_vis.get("count_leak"):
            warnings.append("Layout count leak detected.")

        # Extract site design signature across 10 structural dimensions (Issue #27)
        design_sig_dict: Optional[Dict[str, str]] = None
        if extract_site_design_signature is not None:
            try:
                sig_obj = extract_site_design_signature(files, prompt_spec=prompt_spec, task_id=task_id)
                design_sig_dict = sig_obj.to_dict()
            except Exception:
                design_sig_dict = None

        details = {
            "prompt_fidelity": d_prompt,
            "required_section_completion": d_sections,
            "typescript": d_ts,
            "production_build": d_build,
            "runtime": d_rt,
            "interactions": d_inter,
            "responsive_design": d_resp,
            "accessibility": d_a11y,
            "visual_structure": d_vis,
            "content_quality": d_content,
            "design_diversity": d_div,
            "dependencies": d_deps,
            "assets": d_assets,
            "three_d_runtime_performance": d_3d,
            "repair_attempts": d_repairs,
            "time_to_preview": d_ttp,
            "motion_quality": d_motion,
            "recovery_metrics": rec_metrics,
            "recovery_penalty": recovery_penalty,
            "remaining_fallback_sections": remaining_fallbacks,
            "independent_scores": independent_scores,
            "design_signature": design_sig_dict,
        }

        is_3d_site = bool(d_3d.get("is_3d_site", False))
        three_d_checks = d_3d.get("three_d_checks", {})

        return SiteBenchmarkScore(
            task_id=task_id,
            domain=domain,
            project_name=project_name,
            composite_score=composite,
            passed=passed,
            is_3d_site=is_3d_site,
            three_d_performance_checks=three_d_checks,
            prompt_fidelity=s_prompt,
            required_section_completion=s_sections,
            typescript=s_ts,
            production_build=s_build,
            runtime=s_rt,
            interactions=s_inter,
            responsive_design=s_resp,
            accessibility=s_a11y,
            visual_structure=s_vis,
            content_quality=s_content,
            design_diversity=s_div,
            dependencies=s_deps,
            assets=s_assets,
            three_d_runtime_performance=s_3d,
            repair_attempts=s_repairs,
            time_to_preview=s_ttp,
            motion_quality=s_motion,
            independent_scores=independent_scores,
            recovery_metrics=rec_metrics,
            auto_scaffold_usage_rate=rec_metrics["auto_scaffold_usage_rate"],
            model_native_success_rate=rec_metrics["model_native_success_rate"],
            fallback_free_completion_rate=rec_metrics["fallback_free_completion_rate"],
            repair_success_rate=rec_metrics["repair_success_rate"],
            details=details,
            errors=errors,
            warnings=warnings,
            design_signature=design_sig_dict,
        )


def evaluate_site_workspace(
    prompt_spec: Dict[str, Any],
    workspace_dir: Path,
    turn_logs: Optional[List[Dict[str, Any]]] = None,
    elapsed_seconds: float = 15.0,
    live_browser_check: bool = False,
) -> SiteBenchmarkScore:
    """Helper function to load files from a workspace directory and evaluate."""
    files: Dict[str, str] = {}
    if workspace_dir.exists():
        for p in workspace_dir.rglob("*"):
            if p.is_file() and not any(part in p.parts for part in ["node_modules", ".git", "dist", ".vite"]):
                rel = p.relative_to(workspace_dir).as_posix()
                try:
                    files[rel] = p.read_text(encoding="utf-8")
                except Exception:
                    pass

    scorer = SiteBenchmarkScorer(workspace_root=workspace_dir)
    return scorer.evaluate_site(
        prompt_spec=prompt_spec,
        files=files,
        workspace_dir=workspace_dir,
        turn_logs=turn_logs,
        elapsed_seconds=elapsed_seconds,
        live_browser_check=live_browser_check,
    )


def aggregate_site_benchmark_scores(
    scores: List[SiteBenchmarkScore]
) -> Dict[str, Any]:
    """Computes global, per-domain, and batch diversity aggregates across site scores."""
    if not scores:
        return {
            "total_sites": 0,
            "overall_pass_rate": 0.0,
            "composite_score_mean": 0.0,
            "metric_means": {},
            "domain_breakdown": {},
            "diversity_evaluation": {},
            "site_diversity_score": 0.0,
            "site_diversity_flags": [],
            "site_diversity_passed": False,
        }

    n = len(scores)
    pass_count = sum(1 for s in scores if s.passed)
    overall_pass_rate = pass_count / n
    composite_mean = sum(s.composite_score for s in scores) / n

    metric_means: Dict[str, float] = {}
    for dim in REQUIRED_SCORING_DIMENSIONS:
        metric_means[dim] = _applicable_mean(getattr(s, dim) for s in scores)

    # Group by domain
    domain_scores: Dict[str, List[SiteBenchmarkScore]] = {}
    for s in scores:
        domain_scores.setdefault(s.domain, []).append(s)

    domain_breakdown: Dict[str, Any] = {}
    for dom, dom_list in domain_scores.items():
        dom_n = len(dom_list)
        dom_pass = sum(1 for s in dom_list if s.passed)
        dom_comp = sum(s.composite_score for s in dom_list) / dom_n
        domain_breakdown[dom] = {
            "count": dom_n,
            "pass_rate": round(dom_pass / dom_n, 4),
            "composite_score": round(dom_comp, 4),
            "typescript_pass_rate": round(sum(s.typescript for s in dom_list) / dom_n, 4),
            "production_build_rate": round(sum(s.production_build for s in dom_list) / dom_n, 4),
            "section_completion_rate": _applicable_mean(s.required_section_completion for s in dom_list),
        }

    # Anti-Template-Collapse / Batch Diversity Evaluation (Issue #27)
    diversity_eval_dict: Dict[str, Any] = {}
    if evaluate_site_batch_diversity is not None and SiteDesignSignature is not None:
        signatures = []
        for s in scores:
            sig_dict = s.design_signature or s.details.get("design_signature")
            if sig_dict and isinstance(sig_dict, dict):
                try:
                    signatures.append(SiteDesignSignature(**sig_dict))
                except Exception:
                    pass
        if signatures:
            batch_report = evaluate_site_batch_diversity(signatures)
            diversity_eval_dict = batch_report.to_dict()

    # ── Separate Evaluation: Normal DOM Sites vs 3D Sites (Issue #28) ────────
    dom_sites = [s for s in scores if not getattr(s, "is_3d_site", False)]
    three_d_sites = [s for s in scores if getattr(s, "is_3d_site", False)]

    def _summarize_partition(partition: List[SiteBenchmarkScore]) -> Dict[str, Any]:
        if not partition:
            return {"total_sites": 0, "pass_rate": 0.0, "composite_score_mean": 0.0, "metric_means": {}}
        p_n = len(partition)
        p_pass = sum(1 for s in partition if s.passed)
        p_means = {
            dim: _applicable_mean(getattr(s, dim) for s in partition)
            for dim in REQUIRED_SCORING_DIMENSIONS
        }
        return {
            "total_sites": p_n,
            "pass_rate": round(p_pass / p_n, 4),
            "composite_score_mean": round(sum(s.composite_score for s in partition) / p_n, 4),
            "metric_means": p_means,
        }

    dom_sites_summary = _summarize_partition(dom_sites)
    three_d_sites_summary = _summarize_partition(three_d_sites)

    # If 3D sites exist, attach performance check breakdown
    if three_d_sites:
        perf_names = [
            "no_webgl_errors",
            "reasonable_dpr",
            "bounded_particle_count",
            "no_expensive_unnecessary_shadows",
            "no_leaking_use_frame_allocations",
            "no_unbounded_post_processing",
        ]
        check_pass_counts: Dict[str, int] = {p: 0 for p in perf_names}
        all_passed_count = 0
        for s in three_d_sites:
            checks = s.three_d_performance_checks or s.details.get("three_d_checks", {})
            site_all_passed = True
            for p in perf_names:
                p_check = checks.get(p, {})
                if p_check.get("passed", False):
                    check_pass_counts[p] += 1
                else:
                    site_all_passed = False
            if site_all_passed:
                all_passed_count += 1

        t_n = len(three_d_sites)
        three_d_sites_summary["three_d_performance_pass_rate"] = round(all_passed_count / t_n, 4)
        three_d_sites_summary["performance_checks_breakdown"] = {
            p: round(check_pass_counts[p] / t_n, 4) for p in perf_names
        }

    # Section 3.D: Aggregate 10 Decoupled Independent Outcome Axes
    independent_axes_means: Dict[str, float] = {}
    for axis in INDEPENDENT_EVALUATION_AXES:
        independent_axes_means[axis] = _applicable_mean(s.independent_scores.get(axis, 0.0) for s in scores)

    # Section 3.E: Aggregate 4 First-Class Recovery Metrics
    recovery_metrics_summary = {
        "model_native_success_rate": round(sum(s.model_native_success_rate for s in scores) / n, 4),
        "repair_success_rate": round(sum(s.repair_success_rate for s in scores) / n, 4),
        "fallback_free_completion_rate": round(sum(1.0 if s.auto_scaffold_usage_rate == 0.0 else 0.0 for s in scores) / n, 4),
        "auto_scaffold_usage_rate": round(sum(s.auto_scaffold_usage_rate for s in scores) / n, 4),
    }

    result: Dict[str, Any] = {
        "total_sites": n,
        "overall_pass_rate": round(overall_pass_rate, 4),
        "composite_score_mean": round(composite_mean, 4),
        "metric_means": metric_means,
        "independent_evaluation_axes_means": independent_axes_means,
        "recovery_metrics_summary": recovery_metrics_summary,
        "domain_breakdown": domain_breakdown,
        "dom_sites_summary": dom_sites_summary,
        "three_d_sites_summary": three_d_sites_summary,
    }
    if diversity_eval_dict:
        result["diversity_evaluation"] = diversity_eval_dict
        result["site_diversity_score"] = diversity_eval_dict.get("overall_diversity_score", 0.0)
        result["site_diversity_flags"] = diversity_eval_dict.get("collapse_flags", [])
        result["site_diversity_passed"] = diversity_eval_dict.get("is_diverse", True)

    return result
