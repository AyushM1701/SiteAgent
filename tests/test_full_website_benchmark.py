"""
tests/test_full_website_benchmark.py - Verification for Issue #25:
Add a Dedicated Full-Website Benchmark.

Acceptance criteria:
- 30-50 full-site prompts covering all 12 domains:
  SaaS, portfolio, ecommerce, editorial, restaurant, healthcare, finance,
  agency, architecture, dashboard, 3D product, WebGL experience.
- Score every site across all 16 required dimensions:
  prompt fidelity, required section completion, TypeScript, production build,
  runtime, interactions, responsive design, accessibility, visual structure,
  content quality, design diversity, dependencies, assets, 3D runtime/performance,
  repair attempts, time-to-preview.
- Site benchmark becomes mandatory for model promotion.
"""

import json
from pathlib import Path
import pytest

from evaluation.site_benchmark_scorer import (
    SiteBenchmarkScore,
    SiteBenchmarkScorer,
    evaluate_site_workspace,
    aggregate_site_benchmark_scores,
    REQUIRED_SCORING_DIMENSIONS,
)
from training.leakage_guard import (
    audit_dataset_against_benchmark,
    SEALED_BENCHMARK_PATH,
)
from training.methodology import (
    evaluate_promotion_gate,
    PromotionGateEvaluation,
)
from scripts.benchmark_full_sites import (
    generate_mock_site_files,
    run_full_site_benchmark,
)

ROOT = Path(__file__).resolve().parents[1]
BENCHMARK_PATH = ROOT / "data" / "eval" / "full_website_benchmark.jsonl"

EXPECTED_12_DOMAINS = {
    "SaaS",
    "portfolio",
    "ecommerce",
    "editorial",
    "restaurant",
    "healthcare",
    "finance",
    "agency",
    "architecture",
    "dashboard",
    "3D product",
    "WebGL experience",
}


def test_benchmark_dataset_size_and_12_domains():
    """Verify benchmark contains 30-50 prompts across all 12 domains with >=3 prompts each."""
    assert BENCHMARK_PATH.exists(), f"Benchmark file missing at {BENCHMARK_PATH}"

    prompts = []
    with open(BENCHMARK_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line_str = line.strip()
            if line_str:
                prompts.append(json.loads(line_str))

    # Total prompts between 30 and 50
    assert 30 <= len(prompts) <= 50, f"Expected 30-50 prompts, found {len(prompts)}"

    # All 12 domains present
    domains_found = {p["domain"] for p in prompts}
    assert domains_found == EXPECTED_12_DOMAINS, f"Domain mismatch. Missing: {EXPECTED_12_DOMAINS - domains_found}"

    # Each domain has at least 3 prompts
    for dom in EXPECTED_12_DOMAINS:
        dom_prompts = [p for p in prompts if p["domain"] == dom]
        assert len(dom_prompts) >= 3, f"Domain '{dom}' has fewer than 3 prompts ({len(dom_prompts)})"


def test_benchmark_prompt_schema():
    """Verify schema integrity of all prompts in the benchmark."""
    with open(BENCHMARK_PATH, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f):
            p = json.loads(line)
            assert "task_id" in p, f"Task {idx} missing task_id"
            assert "domain" in p, f"Task {idx} missing domain"
            assert "name" in p, f"Task {idx} missing name"
            assert "title" in p, f"Task {idx} missing title"
            assert "prompt" in p and len(p["prompt"]) > 50, f"Task {idx} prompt too short"
            assert "required_sections" in p and len(p["required_sections"]) >= 4, f"Task {idx} needs >=4 sections"
            assert "required_interactions" in p and len(p["required_interactions"]) >= 2, f"Task {idx} needs >=2 interactions"
            assert "palette" in p and "background" in p["palette"], f"Task {idx} missing palette"
            assert "domain_keywords" in p and len(p["domain_keywords"]) >= 3, f"Task {idx} needs domain_keywords"

            # 3D and WebGL prompts must declare 3D requirements
            if p["domain"] in {"3D product", "WebGL experience"}:
                assert p.get("has_3d") or p.get("has_webgl"), f"Task {p['task_id']} must have 3D/WebGL flags enabled"


def test_benchmark_leakage_audit_against_sealed_benchmark():
    """Audit new full-website benchmark against sealed benchmark to guarantee 0 contamination."""
    report = audit_dataset_against_benchmark(
        dataset_path=str(BENCHMARK_PATH),
        benchmark_path=str(SEALED_BENCHMARK_PATH),
        token_similarity_threshold=0.50,
        semantic_similarity_threshold=0.65,
        verify_manifest=False,
    )
    assert report.leak_count == 0
    assert report.peak_token_similarity < 0.50
    assert report.peak_semantic_similarity < 0.65


def test_scorer_all_16_required_dimensions_defined():
    """Verify all 16 required scoring dimensions are present in the evaluation contract."""
    expected_dimensions = [
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
    assert len(REQUIRED_SCORING_DIMENSIONS) == 16
    assert set(REQUIRED_SCORING_DIMENSIONS) == set(expected_dimensions)


def test_scorer_evaluation_on_mock_site():
    """Verify site scorer computes all 16 dimensions accurately on a complete mock site."""
    prompt_spec = {
        "task_id": "test_saas_01",
        "domain": "SaaS",
        "name": "CloudPulse",
        "title": "CloudPulse Observability",
        "required_sections": ["navbar", "hero", "features", "pricing", "footer"],
        "required_interactions": ["pricing_toggle", "overview_tabs"],
        "domain_keywords": ["observability", "telemetry", "cloud", "metrics"],
        "palette": {"background": "#0a0e17", "surface": "#121826", "primary": "#00e5ff"},
        "has_3d": False,
        "has_webgl": False,
    }

    files = generate_mock_site_files(prompt_spec)
    scorer = SiteBenchmarkScorer()

    score = scorer.evaluate_site(
        prompt_spec=prompt_spec,
        files=files,
        turn_logs=[{"action": "write_site_ok", "completed": True}],
        elapsed_seconds=12.0,
    )

    assert isinstance(score, SiteBenchmarkScore)
    assert score.passed is True
    assert score.composite_score >= 0.70

    score_dict = score.to_dict()["scores"]
    for dim in REQUIRED_SCORING_DIMENSIONS:
        val = score_dict[dim]
        assert 0.0 <= val <= 1.0, f"Dimension {dim} out of range: {val}"


def test_responsive_score_counts_tailwind_breakpoint_utilities():
    files = {
        "src/components/Header.tsx": '<nav className="hidden md:flex"><button className="md:hidden" onClick={() => setIsMenuOpen(true)}>Menu</button></nav>',
        "src/components/Features.tsx": '<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4">Cards</div>',
        "src/App.css": '@import "tailwindcss";',
    }
    score, details = SiteBenchmarkScorer().score_responsive_design(files)
    assert details["has_mobile_bp"] is True
    assert details["has_desktop_bp"] is True
    assert details["has_grid_auto"] is True
    assert score >= 0.75


def test_interaction_score_does_not_credit_cosmetic_tabs():
    files = {
        "src/components/Features.tsx": (
            "const [activeTab, setActiveTab] = useState('all'); "
            "<button onClick={() => setActiveTab('security')}>Security</button>"
        ),
        "src/components/Pricing.tsx": (
            "const [billingType, setBillingType] = useState('monthly'); "
            "<button onClick={() => setBillingType('annual')}>Annual</button>"
        ),
    }
    _, details = SiteBenchmarkScorer().score_interactions(
        {"required_interactions": ["metrics_tab_filter", "pricing_toggle", "mobile_nav_toggle"]}, files
    )
    assert details["req_interactions_ratio"] == 0.333


def test_scorer_rejects_an_auto_scaffolded_section_even_with_good_build_score():
    prompt_spec = {
        "task_id": "fallback_site", "domain": "SaaS", "name": "CloudPulse",
        "required_sections": ["navbar", "hero", "features", "pricing", "footer"],
        "domain_keywords": ["observability"],
    }
    files = generate_mock_site_files(prompt_spec)
    files["src/components/Navbar.tsx"] = files["src/components/Navbar.tsx"].replace(
        '<section className=', '<section data-fallback="true" className=', 1
    )
    score = SiteBenchmarkScorer().evaluate_site(
        prompt_spec=prompt_spec,
        files=files,
        turn_logs=[{"action": "write_site_ok", "section": "navbar", "fallback_generated": True}],
        elapsed_seconds=12.0,
    )
    assert score.composite_score >= 0.65
    assert not score.passed
    assert any("Auto-scaffold fallback" in error for error in score.errors)


def test_scorer_penalizes_flaws():
    """Verify that specific quality flaws depress the respective dimensional scores."""
    prompt_spec = {
        "task_id": "flawed_site_01",
        "domain": "healthcare",
        "name": "CardioCare",
        "title": "CardioCare Health",
        "required_sections": ["navbar", "hero", "diagnostic_calc", "doctors", "booking", "footer"],
        "domain_keywords": ["cardiology", "biometric", "telemetry"],
        "has_3d": True,  # Demands 3D
    }

    # Flawed files: missing 3D canvas, has lorem ipsum, fake contacts, dead hrefs, count leaks
    flawed_files = {
        "src/App.tsx": """
            export default function App() {
                return (
                    <div>
                        <a href="#">Dead link</a>
                        <p>Lorem ipsum dolor sit amet, consectetur adipiscing elit.</p>
                        <p>Contact us at hello@example.com or (555) 019-2834.</p>
                        <p>CEO of Acme Corporation</p>
                        <div>Enterprise capability for 6 cards</div>
                    </div>
                );
            }
        """,
        "src/App.css": "div { color: red; }",  # Unscoped selector
    }

    scorer = SiteBenchmarkScorer()
    score = scorer.evaluate_site(
        prompt_spec=prompt_spec,
        files=flawed_files,
        turn_logs=[{"action": "tsc_error"}, {"action": "style_violation"}, {"action": "repair"}],
        elapsed_seconds=140.0,
    )

    # 1. Content quality penalized by lorem ipsum and fake contacts
    assert score.content_quality < 0.60
    assert score.details["content_quality"]["has_lorem"] is True
    assert score.details["content_quality"]["has_fake_contacts"] is True

    # 2. Visual structure penalized by count leak and unscoped CSS
    assert score.visual_structure < 0.80
    assert score.details["visual_structure"]["count_leak"] is True

    # 3. 3D performance penalized because required 3D canvas is missing
    assert score.three_d_runtime_performance == 0.0

    # 4. Repair attempts penalized
    assert score.repair_attempts <= 0.60

    # 5. Section completion low
    assert score.required_section_completion < 0.30

    # 6. Overall site fails
    assert score.passed is False


def test_aggregate_site_benchmark_scores():
    """Verify aggregation across sites and per-domain breakdown calculation."""
    scores = [
        SiteBenchmarkScore(
            task_id="t1", domain="SaaS", project_name="SaaS1", composite_score=0.90, passed=True,
            prompt_fidelity=0.9, required_section_completion=1.0, typescript=1.0, production_build=1.0,
            runtime=1.0, interactions=0.8, responsive_design=0.9, accessibility=1.0, visual_structure=1.0,
            content_quality=0.9, design_diversity=0.8, dependencies=1.0, assets=0.9,
            three_d_runtime_performance=1.0, repair_attempts=1.0, time_to_preview=1.0
        ),
        SiteBenchmarkScore(
            task_id="t2", domain="ecommerce", project_name="Shop1", composite_score=0.80, passed=True,
            prompt_fidelity=0.8, required_section_completion=0.9, typescript=1.0, production_build=1.0,
            runtime=1.0, interactions=0.7, responsive_design=0.8, accessibility=0.9, visual_structure=0.9,
            content_quality=0.8, design_diversity=0.8, dependencies=1.0, assets=0.8,
            three_d_runtime_performance=1.0, repair_attempts=0.85, time_to_preview=0.85
        ),
    ]

    agg = aggregate_site_benchmark_scores(scores)
    assert agg["total_sites"] == 2
    assert agg["overall_pass_rate"] == 1.0
    assert agg["composite_score_mean"] == pytest.approx(0.85, rel=1e-2)
    assert "SaaS" in agg["domain_breakdown"]
    assert "ecommerce" in agg["domain_breakdown"]
    assert agg["domain_breakdown"]["SaaS"]["composite_score"] == 0.90


def test_promotion_gate_strictly_requires_site_benchmark():
    """Acceptance criteria: Site benchmark becomes mandatory for model promotion."""
    # Candidate with perfect component pass rates but MISSING site benchmark
    cand_metrics_without_site = {
        "overall_pass_rate": 0.85,
        "typecheck_pass_rate": 0.95,
        "category_pass_rates": {
            "tsc_render_interact": 0.80,
            "tsc_and_render": 0.90,
        },
        # "site_benchmark_metrics" is omitted
    }

    decision = evaluate_promotion_gate(candidate_metrics=cand_metrics_without_site)
    assert decision.is_eligible is False
    assert decision.site_benchmark_passed is False
    assert any("Site benchmark evaluation is MISSING" in f for f in decision.blocking_failures)
    assert "PROMOTION BLOCKED" in decision.summary


def test_promotion_gate_blocks_when_site_benchmark_below_threshold():
    """Verifies promotion is blocked if site benchmark composite score is below minimum threshold."""
    cand_metrics = {
        "overall_pass_rate": 0.70,
        "typecheck_pass_rate": 0.85,
        "category_pass_rates": {
            "tsc_render_interact": 0.65,
            "tsc_and_render": 0.75,
        },
        "site_benchmark_metrics": {
            "composite_score_mean": 0.58,  # Below 0.70 threshold
            "overall_pass_rate": 0.60,
            "metric_means": {
                "production_build": 0.85,
                "runtime": 0.80,
                "required_section_completion": 0.90,
            },
        },
    }

    decision = evaluate_promotion_gate(candidate_metrics=cand_metrics)
    assert decision.is_eligible is False
    assert any("below minimum promotion threshold" in f for f in decision.blocking_failures)


def test_promotion_gate_blocks_when_site_benchmark_regresses():
    """Verifies promotion is blocked if site benchmark composite score regresses against baseline."""
    base_metrics = {
        "overall_pass_rate": 0.50,
        "typecheck_pass_rate": 0.70,
        "category_pass_rates": {"tsc_render_interact": 0.45},
        "site_benchmark_metrics": {
            "composite_score_mean": 0.82,
            "metric_means": {"production_build": 0.90, "runtime": 0.85, "required_section_completion": 0.90},
        },
    }
    cand_metrics = {
        "overall_pass_rate": 0.65,
        "typecheck_pass_rate": 0.85,
        "category_pass_rates": {"tsc_render_interact": 0.55},
        "site_benchmark_metrics": {
            "composite_score_mean": 0.74,  # Regressed from 0.82
            "metric_means": {"production_build": 0.85, "runtime": 0.80, "required_section_completion": 0.88},
        },
    }

    decision = evaluate_promotion_gate(candidate_metrics=cand_metrics, baseline_metrics=base_metrics)
    assert decision.is_eligible is False
    assert any("Site benchmark composite score REGRESSED" in f for f in decision.blocking_failures)


def test_promotion_gate_permits_when_all_gates_pass():
    """Verifies promotion approval when interaction and site benchmarks all pass."""
    base_metrics = {
        "overall_pass_rate": 0.40,
        "typecheck_pass_rate": 0.65,
        "category_pass_rates": {"tsc_render_interact": 0.42},
        "site_benchmark_metrics": {
            "composite_score_mean": 0.75,
            "metric_means": {"production_build": 0.85, "runtime": 0.80, "required_section_completion": 0.85},
        },
    }
    cand_metrics = {
        "overall_pass_rate": 0.60,
        "typecheck_pass_rate": 0.85,
        "category_pass_rates": {"tsc_render_interact": 0.58},
        "site_benchmark_metrics": {
            "composite_score_mean": 0.88,  # Healthy gain
            "metric_means": {"production_build": 0.95, "runtime": 0.92, "required_section_completion": 0.95},
        },
    }

    decision = evaluate_promotion_gate(candidate_metrics=cand_metrics, baseline_metrics=base_metrics)
    assert decision.is_eligible is True
    assert decision.site_benchmark_passed is True
    assert "PROMOTION ELIGIBLE" in decision.summary


def test_cli_runner_mock_mode_execution(tmp_path):
    """Test CLI runner execution with mock harness across 2 prompts."""
    output_json = tmp_path / "cli_test_report.json"
    summary = run_full_site_benchmark(
        benchmark_file=BENCHMARK_PATH,
        output_report_path=output_json,
        mock=True,
        subset=2,
        workspace_base=tmp_path / "benchmark_workspace",
    )

    assert summary["total_sites"] == 2
    assert summary["overall_pass_rate"] >= 0.50
    assert output_json.exists()
    saved = json.loads(output_json.read_text(encoding="utf-8"))
    assert saved["total_sites"] == 2
    assert "metric_means" in saved
