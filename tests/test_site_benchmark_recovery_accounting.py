from evaluation.site_benchmark_scorer import SiteBenchmarkScorer


def test_header_satisfies_navbar_and_structural_repair_is_not_scaffold():
    scorer = SiteBenchmarkScorer()
    spec = {"required_sections": ["navbar", "hero"]}
    files = {
        "src/components/Header.tsx": "export default function Header() { return <header />; }",
        "src/components/Hero.tsx": "export default function Hero() { return <section />; }",
    }
    completion, detail = scorer.score_required_section_completion(spec, files)
    assert completion == 1.0
    assert detail["missing"] == []

    metrics = scorer.compute_recovery_metrics(spec, [{"section": "navbar", "action": "structural_cap_auto_fix"}])
    assert metrics["auto_scaffold_usage_rate"] == 0.0
    assert metrics["repaired_count"] == 1
