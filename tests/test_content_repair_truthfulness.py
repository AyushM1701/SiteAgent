from agent.style_ingest import auto_fix_structural_violations


def test_content_repair_does_not_invent_brand_or_service_metrics():
    files = [("src/components/Header.tsx", (
        "export default function Header() { return <header>"
        "<h2>Header</h2><p>Series 01</p><p>Series 02</p>"
        "</header>; }"
    ))]
    fixed = dict(auto_fix_structural_violations(
        files, ["[CONTENT LEAK LINT] bare section title"], section_name="header"
    ))["src/components/Header.tsx"]
    assert "ApexCloud" not in fixed
    assert "99.999%" not in fixed
    assert "<h2>Navigation</h2>" in fixed
    assert "Performance" in fixed
    assert "Reliability" in fixed
