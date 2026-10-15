"""
SiteAgent Evaluation Package.
Houses benchmarks, metrics, and scoring engines for component and full-website evaluation.
"""

from evaluation.site_benchmark_scorer import (
    SiteBenchmarkScore,
    SiteBenchmarkScorer,
    evaluate_site_workspace,
    aggregate_site_benchmark_scores,
    REQUIRED_SCORING_DIMENSIONS,
)
from evaluation.diversity_evaluator import (
    SiteDesignSignature,
    BatchDiversityReport,
    AntiTemplateCollapseEvaluator,
    extract_site_design_signature,
    evaluate_site_batch_diversity,
    DIVERSITY_DIMENSIONS,
)
from evaluation.motion_benchmark import (
    MotionBehavioralResult,
    MotionPerformanceResult,
    MotionBenchmarkReport,
    evaluate_motion_page,
    evaluate_motion_html,
    evaluate_motion_url,
    evaluate_motion_project,
    MOTION_FAMILIES,
)

__all__ = [
    "SiteBenchmarkScore",
    "SiteBenchmarkScorer",
    "evaluate_site_workspace",
    "aggregate_site_benchmark_scores",
    "REQUIRED_SCORING_DIMENSIONS",
    "SiteDesignSignature",
    "BatchDiversityReport",
    "AntiTemplateCollapseEvaluator",
    "extract_site_design_signature",
    "evaluate_site_batch_diversity",
    "DIVERSITY_DIMENSIONS",
    "MotionBehavioralResult",
    "MotionPerformanceResult",
    "MotionBenchmarkReport",
    "evaluate_motion_page",
    "evaluate_motion_html",
    "evaluate_motion_url",
    "evaluate_motion_project",
    "MOTION_FAMILIES",
]

