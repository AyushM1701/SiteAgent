"""
tests/test_recovery_metrics.py - Tests for Section 3.D & 3.E:
Decoupled Behavioral & Visual Outcomes, Motion Quality, and Recovery Dependence Penalization.
"""

import pytest
from typing import Dict, List

from evaluation.site_benchmark_scorer import (
    SiteBenchmarkScorer,
    SiteBenchmarkScore,
    aggregate_site_benchmark_scores,
    INDEPENDENT_EVALUATION_AXES,
    RECOVERY_METRICS,
)
from training.methodology import evaluate_promotion_gate


@pytest.fixture
def base_valid_files() -> Dict[str, str]:
    return {
        "src/index.css": """
:root {
  --color-bg: #0b0f19;
  --font-heading: 'Plus Jakarta Sans', sans-serif;
  --font-body: 'Inter', sans-serif;
  --radius-buttons: 8px;
}
body {
  background-color: var(--color-bg);
  color: #f8fafc;
  margin: 0;
  padding: 0;
}
.btn {
  display: inline-flex;
  transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.2s ease;
  border-radius: var(--radius-buttons);
}
.btn:hover {
  transform: translateY(-2px);
  opacity: 0.9;
}
@keyframes pulseGlow {
  0% { opacity: 0.4; }
  100% { opacity: 0.9; }
}
@media (prefers-reduced-motion: reduce) {
  .btn {
    transition: none !important;
    animation: none !important;
  }
}
""",
        "src/components/Hero.tsx": """
import React, { useState } from 'react';
import './Hero.css';

export default function Hero() {
  const [activeTab, setActiveTab] = useState(0);
  return (
    <section className="hero grid-cols-2 hero__split" id="hero">
      <div className="content">
        <h1>High-Velocity Computational Platform</h1>
        <p>Deterministic execution models built for scale and reliability.</p>
        <button onClick={() => setActiveTab(1)} className="btn">Get Started</button>
      </div>
    </section>
  );
}
""",
        "src/components/Hero.css": """
.hero {
  display: grid;
  grid-template-columns: 1fr 1fr;
  padding: 4rem 2rem;
}
@media (max-width: 768px) {
  .hero {
    grid-template-columns: 1fr;
  }
}
""",
        "src/components/Features.tsx": """
import React from 'react';
export default function Features() {
  return (
    <section className="features grid-cols-4" id="features">
      <div className="card"><h3>Security</h3><p>HMAC-SHA256 authenticated</p></div>
      <div className="card"><h3>Telemetry</h3><p>Real-time distributed tracing</p></div>
      <div className="card"><h3>Throughput</h3><p>114 tokens/sec execution</p></div>
      <div className="card"><h3>Reliability</h3><p>Deterministic self-contained</p></div>
    </section>
  );
}
""",
        "src/App.tsx": """
import React from 'react';
import Hero from './components/Hero';
import Features from './components/Features';

export default function App() {
  return (
    <div>
      <a href="#site-main" className="skip-link sr-only">Skip to content</a>
      <header role="banner"><nav>Platform Nav</nav></header>
      <main id="site-main">
        <Hero />
        <Features />
      </main>
      <footer role="contentinfo"><p>© 2026 Platform Inc.</p></footer>
    </div>
  );
}
""",
        "package.json": """
{
  "dependencies": {
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "lucide-react": "^0.475.0"
  }
}
""",
    }


def test_independent_evaluation_axes_are_computed(base_valid_files):
    """Verify that all 10 independent outcome axes are calculated and exposed."""
    scorer = SiteBenchmarkScorer()
    spec = {
        "name": "PlatformApp",
        "domain": "saas",
        "title": "Computational Platform",
        "required_sections": ["hero", "features"],
    }

    score = scorer.evaluate_site(spec, base_valid_files, turn_logs=[
        {"turn": 1, "action": "write_site", "section": "hero"},
        {"turn": 2, "action": "write_site", "section": "features"},
    ])

    assert isinstance(score, SiteBenchmarkScore)
    assert len(score.independent_scores) == 10

    for axis in INDEPENDENT_EVALUATION_AXES:
        assert axis in score.independent_scores, f"Axis {axis} missing from independent_scores"
        val = score.independent_scores[axis]
        assert 0.0 <= val <= 1.0, f"Axis {axis} value {val} out of [0.0, 1.0]"

    # Verify individual axes on high-quality site
    assert score.independent_scores["correctness_build_runtime"] >= 0.80
    assert score.independent_scores["motion_quality"] >= 0.85
    assert score.independent_scores["fallback_recovery_dependency"] == 1.0
    assert score.independent_scores["accessibility"] >= 0.70


def test_motion_quality_scoring(base_valid_files):
    """Verify that score_motion_quality awards points for transitions, hover, keyframes, and reduced motion."""
    scorer = SiteBenchmarkScorer()
    m_score, details = scorer.score_motion_quality(base_valid_files)

    assert details["has_transitions"] is True
    assert details["has_hover_states"] is True
    assert details["has_keyframes"] is True
    assert details["has_reduced_motion"] is True
    assert details["uses_transforms"] is True
    assert m_score >= 0.90


def test_recovery_metrics_and_penalty_for_auto_scaffolding(base_valid_files):
    """Verify Section 3.E: Tracking recovery metrics and penalizing auto-scaffold reliance."""
    scorer = SiteBenchmarkScorer()
    spec = {
        "name": "PlatformApp",
        "domain": "saas",
        "required_sections": ["hero", "features"],
    }

    # Case 1: Model-native generation (0 auto-scaffold)
    native_score = scorer.evaluate_site(spec, base_valid_files, turn_logs=[
        {"turn": 1, "action": "write_site", "section": "hero"},
        {"turn": 2, "action": "write_site", "section": "features"},
    ])

    assert native_score.recovery_metrics["auto_scaffold_usage_rate"] == 0.0
    assert native_score.recovery_metrics["model_native_success_rate"] == 1.0
    assert native_score.recovery_metrics["fallback_free_completion_rate"] == 1.0
    assert native_score.auto_scaffold_usage_rate == 0.0
    assert native_score.passed is True

    # Case 2: Self-repair generation (Turn 1 error, Turn 2 model fixed natively)
    repaired_score = scorer.evaluate_site(spec, base_valid_files, turn_logs=[
        {"turn": 1, "action": "write_site_no_css", "section": "hero"},
        {"turn": 2, "action": "write_site", "section": "hero"},
        {"turn": 3, "action": "write_site", "section": "features"},
    ])

    assert repaired_score.recovery_metrics["auto_scaffold_usage_rate"] == 0.0
    assert repaired_score.recovery_metrics["repair_success_rate"] == 1.0
    assert repaired_score.auto_scaffold_usage_rate == 0.0
    assert repaired_score.passed is True

    # Case 3: Recovery-dependent generation (50% auto-scaffolded)
    scaffolded_score = scorer.evaluate_site(spec, base_valid_files, turn_logs=[
        {"turn": 1, "action": "write_site", "section": "hero"},
        {"turn": 2, "action": "write_site_auto_guarantee", "section": "features", "auto_recovered": True},
    ])

    assert scaffolded_score.recovery_metrics["auto_scaffold_usage_rate"] == 0.50
    assert scaffolded_score.auto_scaffold_usage_rate == 0.50
    assert scaffolded_score.recovery_metrics["fallback_free_completion_rate"] == 0.0

    # Verify composite score penalty
    # 50% auto-scaffold penalty = 0.50 * 0.40 = 0.20 deduction
    assert scaffolded_score.composite_score < native_score.composite_score
    diff = native_score.composite_score - scaffolded_score.composite_score
    assert diff >= 0.18, f"Expected recovery penalty >= 0.18, got {diff:.4f}"

    # Verify fallback dependency score drops
    assert scaffolded_score.independent_scores["fallback_recovery_dependency"] < native_score.independent_scores["fallback_recovery_dependency"]


def test_excessive_auto_scaffold_fails_pass_gate(base_valid_files):
    """Verify that a site with >50% auto-scaffold usage is rejected by the pass gate."""
    scorer = SiteBenchmarkScorer()
    spec = {
        "name": "PlatformApp",
        "domain": "saas",
        "required_sections": ["hero", "features", "pricing"],
    }

    # 2 out of 3 sections auto-scaffolded (66.7% > 50%)
    excessive_score = scorer.evaluate_site(spec, base_valid_files, turn_logs=[
        {"turn": 1, "action": "write_site", "section": "hero"},
        {"turn": 2, "action": "write_site_auto_guarantee", "section": "features", "auto_recovered": True},
        {"turn": 3, "action": "write_site_auto_guarantee", "section": "pricing", "auto_recovered": True},
    ])

    assert excessive_score.passed is False
    assert any("Excessive auto-scaffolding dependence" in err for err in excessive_score.errors)


def test_aggregate_site_benchmark_scores_includes_axes_and_recovery(base_valid_files):
    """Verify aggregate_site_benchmark_scores aggregates independent axes and recovery metrics."""
    scorer = SiteBenchmarkScorer()
    spec = {"name": "Site", "domain": "saas", "required_sections": ["hero", "features"]}

    s1 = scorer.evaluate_site(spec, base_valid_files, turn_logs=[
        {"turn": 1, "action": "write_site", "section": "hero"},
        {"turn": 2, "action": "write_site", "section": "features"},
    ])
    s2 = scorer.evaluate_site(spec, base_valid_files, turn_logs=[
        {"turn": 1, "action": "write_site", "section": "hero"},
        {"turn": 2, "action": "write_site_auto_guarantee", "section": "features", "auto_recovered": True},
    ])

    agg = aggregate_site_benchmark_scores([s1, s2])

    assert "independent_evaluation_axes_means" in agg
    assert "recovery_metrics_summary" in agg

    axes_means = agg["independent_evaluation_axes_means"]
    for axis in INDEPENDENT_EVALUATION_AXES:
        assert axis in axes_means

    rec_sum = agg["recovery_metrics_summary"]
    for metric in RECOVERY_METRICS:
        assert metric in rec_sum

    assert rec_sum["auto_scaffold_usage_rate"] == 0.25  # (0.0 + 0.50) / 2
    assert rec_sum["fallback_free_completion_rate"] == 0.50  # 1 of 2 sites had 0 scaffolding


def test_evaluate_promotion_gate_blocks_excessive_auto_scaffold_candidate():
    """Verify that model promotion rejects candidates with >25% auto-scaffolding."""
    candidate_metrics = {
        "pass_rate": 0.85,
        "typecheck_pass_rate": 0.95,
        "category_pass_rates": {"interaction": 0.80},
        "site_benchmark_metrics": {
            "composite_score_mean": 0.82,
            "production_build_rate": 0.90,
            "runtime_pass_rate": 0.90,
            "section_completion_rate": 0.90,
            "site_diversity_score": 0.75,
            "recovery_metrics_summary": {
                "auto_scaffold_usage_rate": 0.35,  # 35% > 25% threshold
                "fallback_free_completion_rate": 0.40,
            },
        },
    }

    result = evaluate_promotion_gate(candidate_metrics)
    assert result.is_eligible is False
    assert any("auto-scaffold usage rate 35.0% exceeds promotion threshold" in f for f in result.blocking_failures)
