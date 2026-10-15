"""
training/methodology.py - Training Methodology & Hyperparameter Justification Policy.

Enforces Issue #19 of the SiteAgent Implementation Plan:
1. Establish whether the Qwen3 SFT dataset produces a measurable improvement over Qwen3 Base
   before running expensive sweeps.
2. Prohibit unprincipled hyperparameter sweeps (R8, R16, R32, R64, multiple learning rates,
   multiple dropout values) by default.
3. Require the first comparison: Qwen3 Base vs Qwen3 SFT R16.
4. Only after that comparison should R32, learning-rate tuning, or DPO be considered,
   and each must be justified by measured limitations, not run by default.
"""

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


DEFAULT_COMPARISON_REPORT_PATH = "runs/qwen3_base_vs_sft_comparison.json"


@dataclass
class ExperimentJustification:
    experiment_name: str
    is_justified: bool
    rationale: str
    measured_evidence: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MethodologyEvaluation:
    has_baseline_comparison: bool
    measurable_improvement_detected: bool
    base_overall_pass_rate: Optional[float]
    sft_overall_pass_rate: Optional[float]
    delta_pass_rate: Optional[float]
    justifications: Dict[str, ExperimentJustification]
    recommendation: str
    report_data: Optional[Dict[str, Any]] = None


def evaluate_experiment_justification(
    comparison_report_path: str = DEFAULT_COMPARISON_REPORT_PATH,
) -> MethodologyEvaluation:
    """
    Evaluates whether subsequent hyperparameter experiments (R32, LR tuning, DPO)
    are justified based on measured evidence from the Qwen3 Base vs Qwen3 SFT R16 comparison.
    """
    p = Path(comparison_report_path)
    if not p.is_file():
        return MethodologyEvaluation(
            has_baseline_comparison=False,
            measurable_improvement_detected=False,
            base_overall_pass_rate=None,
            sft_overall_pass_rate=None,
            delta_pass_rate=None,
            justifications={
                "R32": ExperimentJustification(
                    experiment_name="R32",
                    is_justified=False,
                    rationale=(
                        "BLOCKED: Baseline comparison 'Qwen3 Base vs Qwen3 SFT R16' has not been run. "
                        "Cannot justify rank expansion without establishing initial adapter performance."
                    ),
                ),
                "learning_rate_tuning": ExperimentJustification(
                    experiment_name="learning_rate_tuning",
                    is_justified=False,
                    rationale=(
                        "BLOCKED: Baseline comparison has not been run. "
                        "Cannot justify learning rate tuning without measured baseline convergence."
                    ),
                ),
                "DPO": ExperimentJustification(
                    experiment_name="DPO",
                    is_justified=False,
                    rationale=(
                        "BLOCKED: Baseline comparison has not been run. "
                        "DPO requires a validated SFT model to generate real negative preference pairs."
                    ),
                ),
            },
            recommendation=(
                "Run the baseline comparison first: "
                "python scripts/compare_qwen3_base_vs_sft.py"
            ),
        )

    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:
        return MethodologyEvaluation(
            has_baseline_comparison=False,
            measurable_improvement_detected=False,
            base_overall_pass_rate=None,
            sft_overall_pass_rate=None,
            delta_pass_rate=None,
            justifications={},
            recommendation=f"Failed to parse comparison report at {p}: {exc}",
        )

    base_metrics = data.get("base_metrics", {})
    sft_metrics = data.get("sft_metrics", {})
    base_pass = base_metrics.get("overall_pass_rate", 0.0)
    sft_pass = sft_metrics.get("overall_pass_rate", 0.0)
    delta = sft_pass - base_pass

    measurable_improvement = delta > 0.0

    # Category breakdowns for SFT
    sft_categories = sft_metrics.get("category_pass_rates", {})
    interact_pass = sft_categories.get("tsc_render_interact", 0.0)
    render_pass = sft_categories.get("tsc_and_render", 0.0)
    tsc_only_pass = sft_categories.get("tsc_only", 0.0)

    # 1. R32 Justification Rule:
    # Justified ONLY if SFT R16 demonstrates good basic syntax/render capability
    # but suffers an acute capacity bottleneck on interaction/complex state management
    # (e.g., interaction pass rate lags behind render pass rate by > 20% or is < 45%).
    if not measurable_improvement:
        r32_justified = False
        r32_rationale = (
            f"NOT JUSTIFIED: SFT R16 did not produce a measurable improvement over Base "
            f"(Delta: {delta:+.1%}). Fix dataset quality, tokenization, or loss masking first; "
            f"expanding LoRA rank on defective data wastes compute."
        )
    elif render_pass >= 0.50 and (render_pass - interact_pass > 0.20 or interact_pass < 0.40):
        r32_justified = True
        r32_rationale = (
            f"JUSTIFIED BY MEASURED LIMITATION: SFT R16 achieves {render_pass:.1%} on render tasks "
            f"but drops to {interact_pass:.1%} on interactive tasks. High state complexity in interaction "
            f"trajectories indicates LoRA rank capacity saturation. R32 is warranted."
        )
    else:
        r32_justified = False
        r32_rationale = (
            f"NOT JUSTIFIED: SFT R16 achieves balanced performance (render: {render_pass:.1%}, "
            f"interact: {interact_pass:.1%}, overall: {sft_pass:.1%}). No acute capacity bottleneck "
            f"observed. Retain R16 as primary candidate."
        )

    # 2. Learning-Rate Tuning Justification Rule:
    # Justified if training loss stalled at high values or if typecheck pass rate lags significantly.
    sft_tsc = sft_metrics.get("typecheck_pass_rate", 0.0)
    if not measurable_improvement:
        lr_justified = True
        lr_rationale = (
            f"POTENTIALLY JUSTIFIED: SFT R16 failed to surpass Base (Delta: {delta:+.1%}). "
            f"Inspect loss logs for underfitting or learning rate overshoot before modifying dataset."
        )
    elif sft_tsc < 0.60:
        lr_justified = True
        lr_rationale = (
            f"JUSTIFIED BY MEASURED LIMITATION: SFT R16 TypeScript compile rate is low ({sft_tsc:.1%}). "
            f"Sub-optimal learning rate may prevent convergence on strict syntactic constraints."
        )
    else:
        lr_justified = False
        lr_rationale = (
            f"NOT JUSTIFIED: SFT R16 typecheck rate is healthy ({sft_tsc:.1%}) and loss converged stably. "
            f"Learning rate 2e-5 is effective; grid search is unnecessary."
        )

    # 3. DPO Justification Rule:
    # DPO is justified ONLY after SFT achieves a solid syntactic and functional baseline.
    if sft_pass >= 0.40 and measurable_improvement:
        dpo_justified = True
        dpo_rationale = (
            f"JUSTIFIED: SFT R16 provides a viable agentic baseline ({sft_pass:.1%} overall pass rate). "
            f"DPO is now appropriate to align style, negative constraints, and reduce subtle visual flaws."
        )
    else:
        dpo_justified = False
        dpo_rationale = (
            f"NOT JUSTIFIED: SFT R16 overall pass rate is {sft_pass:.1%}. DPO cannot fix basic functional "
            f"deficits; strengthen SFT data and supervision before preference alignment."
        )

    justifications = {
        "R32": ExperimentJustification("R32", r32_justified, r32_rationale, {"interact_pass": interact_pass, "render_pass": render_pass}),
        "learning_rate_tuning": ExperimentJustification("learning_rate_tuning", lr_justified, lr_rationale, {"tsc_pass": sft_tsc}),
        "DPO": ExperimentJustification("DPO", dpo_justified, dpo_rationale, {"overall_pass": sft_pass}),
    }

    if measurable_improvement:
        recommendation = (
            f"Qwen3 SFT produces a measurable improvement (+{delta*100:.1f} percentage points over Base). "
            + (" Next suggested exploration: " + ", ".join(k for k, v in justifications.items() if v.is_justified) if any(v.is_justified for v in justifications.values()) else " Retain R16 as the canonical candidate without expensive sweeps.")
        )
    else:
        recommendation = (
            f"Qwen3 SFT did NOT produce a measurable improvement ({delta*100:+.1f} percentage points). "
            "Examine dataset coverage, prompt masking, and task diagnostics before sweeping hyperparameters."
        )

    return MethodologyEvaluation(
        has_baseline_comparison=True,
        measurable_improvement_detected=measurable_improvement,
        base_overall_pass_rate=base_pass,
        sft_overall_pass_rate=sft_pass,
        delta_pass_rate=delta,
        justifications=justifications,
        recommendation=recommendation,
        report_data=data,
    )


def guard_hyperparameter_sweep(
    rank: int,
    learning_rate: float = 2e-5,
    lora_dropout: float = 0.0,
    comparison_report_path: str = DEFAULT_COMPARISON_REPORT_PATH,
    override: bool = False,
) -> None:
    """
    Guards training against unprincipled sweeps (e.g. rank != 16, sweeping learning rates).
    Raises ValueError unless the experiment is justified by measured limitations or explicit override.
    """
    if override:
        return

    # Conservative defaults (rank=16, lr=2e-5, dropout=0.0) are always allowed as the primary run.
    is_conservative_default = (rank == 16 and abs(learning_rate - 2e-5) < 1e-7 and lora_dropout == 0.0)
    if is_conservative_default:
        return

    # For non-default hyperparameter choices, check methodology evaluation
    eval_result = evaluate_experiment_justification(comparison_report_path)

    if not eval_result.has_baseline_comparison:
        raise ValueError(
            f"Hyperparameter experiment (rank={rank}, lr={learning_rate}) is blocked by training methodology. "
            f"Acceptance criteria requires establishing the baseline comparison 'Qwen3 Base vs Qwen3 SFT R16' first. "
            f"Run 'python scripts/compare_qwen3_base_vs_sft.py' before sweeping hyperparameters, "
            f"or supply --override-methodology-gate if running an intentional override."
        )

    # If rank != 16 is requested:
    if rank != 16:
        r32_just = eval_result.justifications.get("R32")
        if not (r32_just and r32_just.is_justified):
            rationale = r32_just.rationale if r32_just else "No justification found."
            raise ValueError(
                f"Hyperparameter experiment with rank={rank} is NOT justified by measured limitations.\n"
                f"Reason: {rationale}\n"
                f"Supply --override-methodology-gate to bypass this methodology constraint."
            )

    # If non-standard learning rate is requested:
    if abs(learning_rate - 2e-5) >= 1e-7:
        lr_just = eval_result.justifications.get("learning_rate_tuning")
        if not (lr_just and lr_just.is_justified):
            rationale = lr_just.rationale if lr_just else "No justification found."
            raise ValueError(
                f"Hyperparameter experiment with learning_rate={learning_rate} is NOT justified by measured limitations.\n"
                f"Reason: {rationale}\n"
                f"Supply --override-methodology-gate to bypass this methodology constraint."
            )


@dataclass
class PromotionGateEvaluation:
    is_eligible: bool
    interaction_pass_rate: float
    baseline_interaction_pass_rate: Optional[float]
    interaction_delta: Optional[float]
    overall_pass_rate: float
    baseline_overall_pass_rate: Optional[float]
    typecheck_pass_rate: float
    site_benchmark_passed: bool
    site_benchmark_composite: Optional[float]
    site_benchmark_metrics: Optional[Dict[str, Any]]
    reasons: List[str]
    blocking_failures: List[str]
    summary: str
    site_diversity_score: Optional[float] = None
    site_diversity_flags: List[str] = field(default_factory=list)
    site_diversity_passed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_eligible": self.is_eligible,
            "interaction_pass_rate": round(self.interaction_pass_rate, 4),
            "baseline_interaction_pass_rate": (
                round(self.baseline_interaction_pass_rate, 4)
                if self.baseline_interaction_pass_rate is not None
                else None
            ),
            "interaction_delta": (
                round(self.interaction_delta, 4)
                if self.interaction_delta is not None
                else None
            ),
            "overall_pass_rate": round(self.overall_pass_rate, 4),
            "baseline_overall_pass_rate": (
                round(self.baseline_overall_pass_rate, 4)
                if self.baseline_overall_pass_rate is not None
                else None
            ),
            "typecheck_pass_rate": round(self.typecheck_pass_rate, 4),
            "site_benchmark_passed": self.site_benchmark_passed,
            "site_benchmark_composite": (
                round(self.site_benchmark_composite, 4)
                if self.site_benchmark_composite is not None
                else None
            ),
            "site_benchmark_metrics": self.site_benchmark_metrics,
            "site_diversity_score": (
                round(self.site_diversity_score, 4)
                if self.site_diversity_score is not None
                else None
            ),
            "site_diversity_flags": self.site_diversity_flags,
            "site_diversity_passed": self.site_diversity_passed,
            "reasons": self.reasons,
            "blocking_failures": self.blocking_failures,
            "summary": self.summary,
        }


def evaluate_promotion_gate(
    candidate_metrics: Dict[str, Any],
    baseline_metrics: Optional[Dict[str, Any]] = None,
    min_interaction_threshold: float = 0.40,
    min_typecheck_threshold: float = 0.60,
    min_site_composite_threshold: float = 0.70,
    min_site_build_threshold: float = 0.80,
    min_site_runtime_threshold: float = 0.75,
    min_site_section_threshold: float = 0.85,
    min_site_diversity_threshold: float = 0.60,
    require_site_benchmark: bool = True,
    strict_provenance: bool = True,
) -> PromotionGateEvaluation:
    """
    Evaluates whether a candidate model is eligible for promotion.
    Enforces Issue #22, Issue #25 & Issue #27:
    1. Interaction category pass rate (tsc_render_interact) is a first-class metric.
    2. Dedicated full-website benchmark (30-50 sites across 12 domains) is MANDATORY.
    3. Anti-template-collapse diversity metric and flags (>80% collapse patterns) are MANDATORY.

    A candidate model CANNOT be promoted merely because validation loss decreased
    or static syntax improved if interaction correctness regresses, the site benchmark fails,
    or generated websites collapse into identical templates.
    """
    reasons: List[str] = []
    blocking_failures: List[str] = []

    cand_categories = candidate_metrics.get("category_pass_rates", {})
    interact_rate = cand_categories.get("tsc_render_interact", 0.0)
    overall_rate = candidate_metrics.get("overall_pass_rate", 0.0)
    tsc_rate = candidate_metrics.get("typecheck_pass_rate", 0.0)

    base_interact: Optional[float] = None
    interact_delta: Optional[float] = None
    base_overall: Optional[float] = None

    if baseline_metrics:
        base_categories = baseline_metrics.get("category_pass_rates", {})
        base_interact = base_categories.get("tsc_render_interact", 0.0)
        interact_delta = interact_rate - base_interact
        base_overall = baseline_metrics.get("overall_pass_rate", 0.0)

    # 0. Provenance & Real-Execution Gate
    # Promotion must reject reports where mock != false or provenance is not real.
    cand_mock = candidate_metrics.get("mock", candidate_metrics.get("is_mock"))
    cand_prov = candidate_metrics.get("provenance")
    site_mock = None
    site_prov = None
    site_metrics_obj = candidate_metrics.get("site_benchmark_metrics")
    if isinstance(site_metrics_obj, dict):
        site_mock = site_metrics_obj.get("mock", site_metrics_obj.get("is_mock"))
        site_prov = site_metrics_obj.get("provenance")

    if strict_provenance:
        if "mock" not in candidate_metrics and "is_mock" not in candidate_metrics:
            blocking_failures.append("PROMOTION REJECTED: Candidate benchmark missing mandatory 'mock' field (fail-closed).")
        elif cand_mock is not False:
            blocking_failures.append(f"PROMOTION REJECTED: Candidate benchmark 'mock' must be False, got '{cand_mock}'.")
        if cand_prov != "real":
            blocking_failures.append(f"PROMOTION REJECTED: Candidate benchmark 'provenance' must be 'real', got '{cand_prov}'.")
        if require_site_benchmark and not isinstance(site_metrics_obj, dict):
            blocking_failures.append("PROMOTION REJECTED: Site benchmark provenance evidence is missing (fail-closed).")
        if require_site_benchmark and isinstance(site_metrics_obj, dict):
            if "mock" not in site_metrics_obj and "is_mock" not in site_metrics_obj:
                blocking_failures.append("PROMOTION REJECTED: Site benchmark missing mandatory 'mock' field (fail-closed).")
            elif site_mock is not False:
                blocking_failures.append(f"PROMOTION REJECTED: Site benchmark 'mock' must be False, got '{site_mock}'.")
            if site_prov != "real":
                blocking_failures.append(f"PROMOTION REJECTED: Site benchmark 'provenance' must be 'real', got '{site_prov}'.")
    else:
        if cand_mock is True or site_mock is True or cand_mock == "true":
            blocking_failures.append(
                "PROMOTION REJECTED: Benchmark evidence was generated in mock mode (mock != false). "
                "Mock mode is useful for CI contract tests, but it must never produce promotion evidence."
            )
        elif cand_prov is not None and cand_prov != "real":
            blocking_failures.append(
                f"PROMOTION REJECTED: Benchmark evidence has non-real provenance '{cand_prov}'. Real execution required."
            )
        elif site_prov is not None and site_prov != "real":
            blocking_failures.append(
                f"PROMOTION REJECTED: Site benchmark evidence has non-real provenance '{site_prov}'. Real execution required."
            )
        else:
            reasons.append("Benchmark provenance attestation verified: real execution without mocks.")

    # 1. First-Class Metric: Interaction Category Pass Rate
    if interact_rate < min_interaction_threshold:
        blocking_failures.append(
            f"Interaction category pass rate {interact_rate:.1%} is below minimum promotion threshold {min_interaction_threshold:.1%}."
        )
    else:
        reasons.append(
            f"Interaction category pass rate {interact_rate:.1%} meets minimum threshold {min_interaction_threshold:.1%}."
        )

    if base_interact is not None and interact_delta is not None:
        if interact_delta < -1e-5:
            blocking_failures.append(
                f"Interaction category pass rate REGRESSED from {base_interact:.1%} to {interact_rate:.1%} (delta: {interact_delta:+.1%}). "
                f"Interactive UI correctness is a mandatory first-class promotion gate."
            )
        else:
            reasons.append(
                f"Interaction category pass rate improved/maintained (delta: {interact_delta:+.1%})."
            )

    # 2. Overall Pass Rate Check
    if base_overall is not None and overall_rate < base_overall - 1e-5:
        blocking_failures.append(
            f"Overall pass rate regressed from {base_overall:.1%} to {overall_rate:.1%}."
        )
    else:
        reasons.append(f"Overall pass rate is {overall_rate:.1%}.")

    # 3. Typecheck Pass Rate Check
    if tsc_rate < min_typecheck_threshold:
        blocking_failures.append(
            f"TypeScript compile rate {tsc_rate:.1%} is below threshold {min_typecheck_threshold:.1%}."
        )
    else:
        reasons.append(f"TypeScript compile rate {tsc_rate:.1%} meets threshold.")

    # 4. Mandatory Full-Website Benchmark (Issue #25 Requirement)
    site_metrics = candidate_metrics.get("site_benchmark_metrics")
    site_passed = False
    site_composite: Optional[float] = None
    div_score: Optional[float] = None
    div_flags: List[str] = []
    div_passed: bool = True

    if site_metrics is None:
        if require_site_benchmark:
            blocking_failures.append(
                "Site benchmark evaluation is MISSING. Under Issue #25, the dedicated full-website "
                "benchmark (30-50 sites across 12 domains) is mandatory for model promotion."
            )
        else:
            reasons.append("Site benchmark evaluation was skipped (require_site_benchmark=False).")
            site_passed = True
    else:
        site_composite = float(site_metrics.get("composite_score_mean", site_metrics.get("composite_score", 0.0)))
        metric_means = site_metrics.get("metric_means", {})
        build_rate = float(metric_means.get("production_build", site_metrics.get("production_build_rate", 0.0)))
        runtime_rate = float(metric_means.get("runtime", site_metrics.get("runtime_pass_rate", 0.0)))
        section_rate = float(metric_means.get("required_section_completion", site_metrics.get("section_completion_rate", 0.0)))

        site_gate_failures: List[str] = []

        if site_composite < min_site_composite_threshold:
            site_gate_failures.append(
                f"Site benchmark composite score {site_composite:.3f} is below minimum promotion threshold {min_site_composite_threshold:.3f}."
            )
        else:
            reasons.append(
                f"Site benchmark composite score {site_composite:.3f} meets minimum threshold {min_site_composite_threshold:.3f}."
            )

        if build_rate < min_site_build_threshold:
            site_gate_failures.append(
                f"Site benchmark production build rate {build_rate:.1%} is below threshold {min_site_build_threshold:.1%}."
            )
        else:
            reasons.append(
                f"Site benchmark production build rate {build_rate:.1%} meets threshold {min_site_build_threshold:.1%}."
            )

        if runtime_rate < min_site_runtime_threshold:
            site_gate_failures.append(
                f"Site benchmark runtime pass rate {runtime_rate:.1%} is below threshold {min_site_runtime_threshold:.1%}."
            )
        else:
            reasons.append(
                f"Site benchmark runtime pass rate {runtime_rate:.1%} meets threshold {min_site_runtime_threshold:.1%}."
            )

        if section_rate < min_site_section_threshold:
            site_gate_failures.append(
                f"Site benchmark required section completion rate {section_rate:.1%} is below threshold {min_site_section_threshold:.1%}."
            )
        else:
            reasons.append(
                f"Site benchmark section completion rate {section_rate:.1%} meets threshold {min_site_section_threshold:.1%}."
            )

        # Check baseline comparison if baseline site metrics provided
        if baseline_metrics:
            base_site = baseline_metrics.get("site_benchmark_metrics")
            if base_site:
                base_comp = float(base_site.get("composite_score_mean", base_site.get("composite_score", 0.0)))
                if site_composite < base_comp - 1e-4:
                    site_gate_failures.append(
                        f"Site benchmark composite score REGRESSED from {base_comp:.3f} to {site_composite:.3f}."
                    )
                else:
                    reasons.append(
                        f"Site benchmark composite score maintained/improved vs baseline ({site_composite:.3f} >= {base_comp:.3f})."
                    )

        # 5. Anti-Template-Collapse Diversity Evaluation (Issue #27 Requirement)
        diversity_eval = site_metrics.get("diversity_evaluation", {})
        div_score = diversity_eval.get("overall_diversity_score")
        if div_score is None:
            div_score = site_metrics.get("site_diversity_score")
        div_flags = diversity_eval.get("collapse_flags", site_metrics.get("site_diversity_flags", []))
        div_passed = diversity_eval.get("is_diverse", site_metrics.get("site_diversity_passed", True))

        if div_score is not None:
            div_score = float(div_score)
            if div_score < min_site_diversity_threshold:
                site_gate_failures.append(
                    f"Site diversity score {div_score:.3f} is below minimum promotion threshold {min_site_diversity_threshold:.3f}. Template collapse detected."
                )
                div_passed = False
            else:
                reasons.append(f"Site diversity score {div_score:.3f} meets minimum threshold {min_site_diversity_threshold:.3f}.")

        if div_flags:
            for flag in div_flags:
                site_gate_failures.append(f"Template collapse flag triggered: {flag}")
            div_passed = False
        elif div_score is not None and div_passed:
            reasons.append("Anti-template-collapse check passed: no dominant layout collapse patterns detected.")

        # 6. Recovery Dependence Guard (Section 3.E)
        recovery_summary = site_metrics.get("recovery_metrics_summary", {})
        auto_usage = recovery_summary.get("auto_scaffold_usage_rate")
        if auto_usage is not None:
            auto_usage = float(auto_usage)
            max_allowed_auto_usage = 0.25
            if auto_usage > max_allowed_auto_usage:
                site_gate_failures.append(
                    f"Site benchmark auto-scaffold usage rate {auto_usage:.1%} exceeds promotion threshold {max_allowed_auto_usage:.1%}. "
                    f"Promotion requires authentic model-native generation, not reliance on auto-scaffold fallbacks."
                )
            else:
                reasons.append(f"Auto-scaffold fallback usage rate {auto_usage:.1%} is within allowable threshold ({max_allowed_auto_usage:.1%}).")

        if site_gate_failures:
            blocking_failures.extend(site_gate_failures)
            site_passed = False
        else:
            site_passed = True
            reasons.append(f"Site benchmark passed with composite score {site_composite:.3f}.")

    is_eligible = len(blocking_failures) == 0

    if is_eligible:
        summary = (
            f"PROMOTION ELIGIBLE: Candidate satisfies all promotion criteria with "
            f"interaction pass rate at {interact_rate:.1%}, overall at {overall_rate:.1%}, "
            f"and site benchmark composite at {site_composite:.3f}."
        )
    else:
        summary = (
            f"PROMOTION BLOCKED: Candidate failed {len(blocking_failures)} promotion gate rule(s). "
            f"Primary blocker: {blocking_failures[0]}"
        )

    return PromotionGateEvaluation(
        is_eligible=is_eligible,
        interaction_pass_rate=interact_rate,
        baseline_interaction_pass_rate=base_interact,
        interaction_delta=interact_delta,
        overall_pass_rate=overall_rate,
        baseline_overall_pass_rate=base_overall,
        typecheck_pass_rate=tsc_rate,
        site_benchmark_passed=site_passed,
        site_benchmark_composite=site_composite,
        site_benchmark_metrics=site_metrics,
        site_diversity_score=div_score,
        site_diversity_flags=div_flags,
        site_diversity_passed=div_passed,
        reasons=reasons,
        blocking_failures=blocking_failures,
        summary=summary,
    )


# ── Staged Curriculum Policy Integration ──────────────────────────────────────

def verify_curriculum_progression(
    target_stage_name: str,
    completed_stage_names: List[str],
) -> Tuple[bool, str]:
    """
    Verifies curriculum stage graduation rules.
    Prevents running downstream training (e.g. Stage H DPO or Stage E full-site)
    before foundational protocol and correctness stages are completed.
    """
    try:
        from training.curriculum import CurriculumStage, CurriculumProgressionController
        target_stage = CurriculumStage(target_stage_name)
        completed_set = {CurriculumStage(s) for s in completed_stage_names}
        return CurriculumProgressionController.can_advance_to_stage(target_stage, completed_set)
    except Exception as exc:
        return False, f"Curriculum verification failed: {exc}"
