"""
tests/test_diversity_evaluator.py - Tests for Anti-Template-Collapse Evaluation.

Enforces Issue #27 of the SiteAgent Implementation Plan:
1. Extraction of all 10 design dimensions:
   - hero layout
   - section order
   - font pairing
   - border-radius distribution
   - grid/card structure
   - dark/light choice
   - CTA shape
   - background treatment
   - visual asset type
   - navigation pattern
2. Flagging >80% collapse patterns:
   - >80% centered hero
   - >80% three-card features
   - >80% dark gradient
   - >80% pill CTAs
3. Measurement of normalized Shannon entropy and Simpson index.
4. Integration with aggregate_site_benchmark_scores and evaluate_promotion_gate.
"""

import pytest
from typing import Dict, List

from evaluation.diversity_evaluator import (
    SiteDesignSignature,
    BatchDiversityReport,
    AntiTemplateCollapseEvaluator,
    extract_site_design_signature,
    evaluate_site_batch_diversity,
    DIVERSITY_DIMENSIONS,
    COLLAPSE_PATTERNS,
)
from evaluation.site_benchmark_scorer import (
    SiteBenchmarkScore,
    aggregate_site_benchmark_scores,
)
from training.methodology import evaluate_promotion_gate


def test_extract_site_design_signature_10_dimensions():
    """Verify that extract_site_design_signature populates all 10 required dimensions."""
    files = {
        "src/index.css": """
:root {
  --color-bg: #0b0f19;
  --font-heading: 'Plus Jakarta Sans', sans-serif;
  --font-body: 'Inter', sans-serif;
  --radius-base: 6px;
  --radius-buttons: 6px;
}
body {
  background-image: radial-gradient(circle, #38bdf8 1px, transparent 1px);
  color: #f8fafc;
}
.btn {
  border-radius: 6px;
}
""",
        "src/components/Hero.tsx": """
export default function Hero() {
  return (
    <section className="hero grid-cols-2 hero__split">
      <h1>Title</h1>
      <p>Description</p>
    </section>
  );
}
""",
        "src/components/Features.tsx": """
export default function Features() {
  return (
    <section className="feature-grid grid-cols-4">
      <div className="card">Card 1</div>
      <div className="card">Card 2</div>
      <div className="card">Card 3</div>
      <div className="card">Card 4</div>
    </section>
  );
}
""",
        "src/App.tsx": """
import Hero from "./components/Hero";
import Features from "./components/Features";
import Contact from "./components/Contact";

export default function App() {
  return (
    <div>
      <nav className="w-full border-b sticky-topbar">Navbar</nav>
      <Hero />
      <Features />
      <Contact />
    </div>
  );
}
""",
        "package.json": """
{
  "dependencies": {
    "react": "^19.0.0",
    "lucide-react": "^0.475.0"
  }
}
""",
    }

    sig = extract_site_design_signature(files, task_id="test_site_01")
    assert isinstance(sig, SiteDesignSignature)
    sig_dict = sig.to_dict()

    # Verify all 10 dimensions are present and non-empty
    for dim in DIVERSITY_DIMENSIONS:
        assert dim in sig_dict, f"Dimension {dim} missing from signature dict"
        assert sig_dict[dim] != "", f"Dimension {dim} is empty"

    assert sig.hero_layout == "split_hero"
    assert "hero->features->contact" in sig.section_order
    assert "Plus Jakarta Sans" in sig.font_pairing
    assert sig.border_radius_distribution == "subtle_4_8px"
    assert sig.grid_card_structure == "four_card_grid"
    assert sig.dark_light_choice == "dark"
    assert sig.cta_shape == "rounded_subtle_cta"
    assert sig.background_treatment == "grid_mesh"
    assert sig.visual_asset_type == "lucide_svg_icons"
    assert sig.navigation_pattern == "full_width_banner"


def test_extract_site_design_signature_editorial_archetype():
    """Verify extraction for an editorial/serif/sharp-corner archetype."""
    files = {
        "src/index.css": """
:root {
  --color-bg: #fcfbf7;
  --font-heading: 'Playfair Display', serif;
  --font-body: 'Source Serif Pro', Georgia, serif;
  --radius-base: 0px;
  --radius-buttons: 0px;
}
body {
  background-color: var(--color-bg);
  color: #1c1917;
}
.btn {
  border-radius: 0px;
}
""",
        "src/components/Hero.tsx": """
export default function Hero() {
  return (
    <section className="hero font-serif text-left editorial">
      <h1>Architectural Chronicle</h1>
    </section>
  );
}
""",
        "src/components/Articles.tsx": """
export default function Articles() {
  return (
    <section className="bento-grid">
      <div className="card">A1</div>
    </section>
  );
}
""",
        "src/App.tsx": """
import Hero from "./components/Hero";
import Articles from "./components/Articles";

export default function App() {
  return (
    <div>
      <header className="masthead edition">Header</header>
      <Hero />
      <Articles />
    </div>
  );
}
""",
    }

    sig = extract_site_design_signature(files, task_id="test_editorial")
    assert sig.hero_layout == "minimal_editorial_hero"
    assert "Playfair Display" in sig.font_pairing
    assert sig.border_radius_distribution == "sharp_0px"
    assert sig.dark_light_choice == "warm_neutral"
    assert sig.cta_shape == "sharp_square_cta"
    assert sig.navigation_pattern == "split_masthead"
    assert sig.grid_card_structure == "bento_heterogeneous"


def test_flag_all_four_template_collapse_patterns():
    """
    Flag patterns such as:
    >80% centered hero
    >80% three-card features
    >80% dark gradient
    >80% pill CTAs
    """
    # Create 10 site signatures where 9 out of 10 collapse into identical patterns (90% > 80%)
    collapsed_signatures = []
    for i in range(10):
        if i < 9:
            # Collapsed template
            collapsed_signatures.append(SiteDesignSignature(
                task_id=f"site_{i}",
                hero_layout="centered_hero",
                section_order="hero->features->footer",
                font_pairing="Inter + Inter",
                border_radius_distribution="pill_predominant",
                grid_card_structure="three_card_features",
                dark_light_choice="dark",
                cta_shape="pill_cta",
                background_treatment="dark_gradient",
                visual_asset_type="lucide_svg_icons",
                navigation_pattern="sticky_floating_island",
            ))
        else:
            # 1 odd site
            collapsed_signatures.append(SiteDesignSignature(
                task_id=f"site_{i}",
                hero_layout="split_hero",
                section_order="hero->about->services->contact",
                font_pairing="Playfair Display + Inter",
                border_radius_distribution="sharp_0px",
                grid_card_structure="four_card_grid",
                dark_light_choice="light",
                cta_shape="sharp_square_cta",
                background_treatment="grid_mesh",
                visual_asset_type="real_photography",
                navigation_pattern="full_width_banner",
            ))

    evaluator = AntiTemplateCollapseEvaluator(collapse_threshold=0.80)
    report = evaluator.evaluate_batch(collapsed_signatures)

    assert report.total_sites == 10
    assert not report.is_diverse, "Batch with 90% collapse must fail is_diverse"

    # Check that all 4 specified collapse patterns are explicitly flagged
    flags_text = " ".join(report.collapse_flags)
    assert ">80% centered hero" in flags_text, "Failed to flag >80% centered hero"
    assert ">80% three-card features" in flags_text, "Failed to flag >80% three-card features"
    assert ">80% dark gradient" in flags_text, "Failed to flag >80% dark gradient"
    assert ">80% pill CTAs" in flags_text, "Failed to flag >80% pill CTAs"

    # Verify diversity score is heavily penalized
    assert report.overall_diversity_score < 0.50, f"Expected penalized score < 0.50, got {report.overall_diversity_score}"


def test_diverse_batch_passes_anti_template_collapse():
    """Verify that a diverse batch across multiple archetypes achieves high entropy and passes."""
    archetypes = [
        # Editorial
        ("minimal_editorial_hero", "Playfair + Georgia", "sharp_0px", "bento_heterogeneous", "warm_neutral", "sharp_square_cta", "solid_flat", "split_masthead"),
        # SaaS
        ("split_hero", "Inter + Inter", "subtle_4_8px", "four_card_grid", "dark", "rounded_subtle_cta", "grid_mesh", "full_width_banner"),
        # Dashboard
        ("split_hero", "Space Grotesk + JetBrains Mono", "subtle_4_8px", "tabs_switcher", "dark", "rounded_subtle_cta", "grid_mesh", "sidebar_dock"),
        # 3D Product
        ("full_bleed_hero", "Space Grotesk + Inter", "pill_predominant", "carousel_slider", "dark", "pill_cta", "aurora_vibrant", "sticky_floating_island"),
        # Portfolio
        ("full_bleed_hero", "Outfit + Inter", "moderate_12_20px", "carousel_slider", "light", "pill_cta", "solid_flat", "minimal_sparse"),
        # Restaurant
        ("minimal_editorial_hero", "Cinzel + Lato", "subtle_4_8px", "timeline_vertical", "warm_neutral", "rounded_subtle_cta", "solid_flat", "full_width_banner"),
        # Finance
        ("split_hero", "Plus Jakarta + Inter", "subtle_4_8px", "two_column_split", "dark", "rounded_subtle_cta", "grid_mesh", "full_width_banner"),
        # Agency
        ("asymmetric_bento_hero", "Syne + Inter", "pill_predominant", "bento_heterogeneous", "dark", "pill_cta", "aurora_vibrant", "sticky_floating_island"),
    ]

    signatures = []
    for idx, (hero, font, rad, grid, dl, cta, bg, nav) in enumerate(archetypes):
        signatures.append(SiteDesignSignature(
            task_id=f"diverse_site_{idx}",
            hero_layout=hero,
            section_order=f"order_{idx}",
            font_pairing=font,
            border_radius_distribution=rad,
            grid_card_structure=grid,
            dark_light_choice=dl,
            cta_shape=cta,
            background_treatment=bg,
            visual_asset_type=f"asset_{idx % 4}",
            navigation_pattern=nav,
        ))

    evaluator = AntiTemplateCollapseEvaluator(collapse_threshold=0.80)
    report = evaluator.evaluate_batch(signatures)

    assert report.total_sites == 8
    assert report.is_diverse, f"Diverse batch should pass: flags={report.collapse_flags}"
    assert len(report.collapse_flags) == 0
    assert report.overall_diversity_score >= 0.70, f"Expected diversity score >= 0.70, got {report.overall_diversity_score}"

    # Verify normalized Shannon entropies are healthy across dimensions
    for dim, entropy in report.dimension_entropies.items():
        assert 0.0 <= entropy <= 1.0, f"Entropy out of range for {dim}: {entropy}"
        assert entropy > 0.40, f"Expected high entropy for diverse dim {dim}, got {entropy}"


def test_aggregate_site_benchmark_scores_includes_diversity():
    """Verify that aggregate_site_benchmark_scores attaches batch diversity metrics."""
    scores = []
    for i in range(6):
        sig = SiteDesignSignature(
            task_id=f"site_{i}",
            hero_layout="split_hero" if i % 2 == 0 else "centered_hero",
            section_order=f"order_{i}",
            font_pairing="Inter + Inter" if i % 2 == 0 else "Playfair + Georgia",
            border_radius_distribution="subtle_4_8px" if i % 2 == 0 else "sharp_0px",
            grid_card_structure="four_card_grid" if i % 2 == 0 else "bento_heterogeneous",
            dark_light_choice="dark" if i % 2 == 0 else "light",
            cta_shape="rounded_subtle_cta" if i % 2 == 0 else "sharp_square_cta",
            background_treatment="grid_mesh" if i % 2 == 0 else "solid_flat",
            visual_asset_type="lucide_svg_icons" if i % 2 == 0 else "real_photography",
            navigation_pattern="full_width_banner" if i % 2 == 0 else "split_masthead",
        )
        score = SiteBenchmarkScore(
            task_id=f"site_{i}",
            domain="saas" if i % 2 == 0 else "editorial",
            project_name=f"Project_{i}",
            composite_score=0.88,
            passed=True,
            design_signature=sig.to_dict(),
        )
        scores.append(score)

    summary = aggregate_site_benchmark_scores(scores)
    assert "diversity_evaluation" in summary
    div_eval = summary["diversity_evaluation"]
    assert div_eval["total_sites"] == 6
    assert summary["site_diversity_score"] > 0.80
    assert summary["site_diversity_passed"] is True
    assert len(summary["site_diversity_flags"]) == 0


def test_evaluate_promotion_gate_blocks_template_collapsed_candidate():
    """Verify that candidate model promotion is BLOCKED when template collapse occurs."""
    candidate_metrics = {
        "overall_pass_rate": 0.85,
        "typecheck_pass_rate": 0.95,
        "category_pass_rates": {"tsc_render_interact": 0.75},
        "site_benchmark_metrics": {
            "composite_score_mean": 0.88,
            "metric_means": {
                "production_build": 0.95,
                "runtime": 0.90,
                "required_section_completion": 0.92,
            },
            # Template collapse flags
            "diversity_evaluation": {
                "overall_diversity_score": 0.42,
                "is_diverse": False,
                "collapse_flags": [
                    "COLLAPSE_FLAG: >80% centered hero (90.0% > 80%)",
                    "COLLAPSE_FLAG: >80% three-card features (90.0% > 80%)",
                ],
            },
        },
    }

    eval_result = evaluate_promotion_gate(candidate_metrics)
    assert not eval_result.is_eligible, "Promotion must be blocked on template collapse"
    assert eval_result.site_diversity_passed is False
    assert any("Template collapse" in f for f in eval_result.blocking_failures)


def test_evaluate_promotion_gate_approves_diverse_candidate():
    """Verify that candidate model promotion succeeds when diversity standards are met."""
    candidate_metrics = {
        "mock": False, "provenance": "real",  # promotion evidence must come from real execution
        "overall_pass_rate": 0.85,
        "typecheck_pass_rate": 0.95,
        "category_pass_rates": {"tsc_render_interact": 0.75},
        "site_benchmark_metrics": {
            "mock": False, "provenance": "real",  # promotion evidence must come from real execution
            "composite_score_mean": 0.88,
            "metric_means": {
                "production_build": 0.95,
                "runtime": 0.90,
                "required_section_completion": 0.92,
            },
            "diversity_evaluation": {
                "overall_diversity_score": 0.84,
                "is_diverse": True,
                "collapse_flags": [],
            },
        },
    }

    eval_result = evaluate_promotion_gate(candidate_metrics)
    assert eval_result.is_eligible, f"Promotion should be eligible: {eval_result.blocking_failures}"
    assert eval_result.site_diversity_passed is True
    assert eval_result.site_diversity_score == 0.84
    assert len(eval_result.site_diversity_flags) == 0


def test_detect_all_7_hero_archetypes_in_diversity_evaluator():
    """Verify that extract_site_design_signature detects each of the 7 archetypes."""
    test_cases = [
        ("split_hero", "<section className='hero grid-cols-2 hero__split'>Split</section>"),
        ("product_stage_hero", "<section className='product_stage'>Stage Plinth Viewport</section>"),
        ("terminal_data_hero", "<section className='terminal_data terminal-window'>Shell</section>"),
        ("minimal_editorial_hero", "<section className='editorial font-serif text-left'>Chronicle</section>"),
        ("full_bleed_visual_hero", "<section className='full-bleed bg-cover object-cover'>Horizon</section>"),
        ("bento_hero", "<section className='bento-grid col-span-2 row-span-2'>Bento</section>"),
        ("restrained_centered_hero", "<section className='restrained_centered'>Restrained</section>"),
    ]

    for expected_layout, hero_snippet in test_cases:
        files = {
            "src/components/Hero.tsx": f"export default function Hero() {{ return {hero_snippet}; }}",
            "src/App.tsx": "<Hero />",
            "src/index.css": "body { background: #000; }",
        }
        sig = extract_site_design_signature(files)
        assert sig.hero_layout == expected_layout, f"Expected {expected_layout}, got {sig.hero_layout}"


def test_flag_non_centered_hero_collapse():
    """Verify that if ANY archetype dominates >80% (e.g. 90% split hero), it is flagged as hero collapse."""
    signatures = []
    # 9 split heroes out of 10 (90% > 80%)
    for i in range(10):
        layout = "split_hero" if i < 9 else "bento_hero"
        signatures.append(SiteDesignSignature(
            task_id=f"site_{i}",
            hero_layout=layout,
            section_order=f"hero->features_{i}->footer",
            font_pairing=f"Font_{i} + Sans",
            border_radius_distribution="mixed_hybrid",
            grid_card_structure="four_card_grid",
            dark_light_choice="dark",
            cta_shape="rounded_subtle_cta",
            background_treatment="glassmorphism_blur",
            visual_asset_type="interactive_simulator",
            navigation_pattern="sticky_floating_island",
        ))

    report = evaluate_site_batch_diversity(signatures)
    assert report.is_diverse is False, "Batch with 90% split hero must not pass diversity gate"
    assert any("split hero" in f or "hero_layout='split_hero'" in f for f in report.collapse_flags)

