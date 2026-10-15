from agent.tailwind_support import is_tailwind_utility, site_uses_tailwind
from agent.style_ingest import check_css_selector_coverage
from server.app import _scaffold_site_vite_runner


def test_tailwind_detection_requires_multiple_actual_utilities():
    assert is_tailwind_utility("md:flex")
    assert is_tailwind_utility("hover:text-white")
    assert is_tailwind_utility("bg-[#2563eb]")
    assert not is_tailwind_utility("gc-hero__title")
    assert not site_uses_tailwind({"src/components/Hero.tsx": '<div className="gc-hero gc-hero__title" />'})
    assert site_uses_tailwind({"src/components/Header.tsx": '<header className="fixed bg-black md:flex" />'})


def test_css_coverage_accepts_supported_utilities_but_requires_custom_classes():
    tsx = '<header className="fixed bg-black site-header" />'
    valid, missing = check_css_selector_coverage(tsx, "", allow_tailwind=True)
    assert not valid
    assert missing == ["site-header"]


def test_vite_scaffold_enables_tailwind_for_generated_utility_classes(tmp_path):
    files = {
        "src/components/Hero.tsx": (
            "export default function Hero() { return "
            '<section className="bg-black text-white p-4">Hello</section>; }'
        ),
        "src/components/Hero.css": "",
    }
    _scaffold_site_vite_runner(tmp_path, "Tailwind Site", files)
    assert "tailwindcss()" in (tmp_path / "vite.config.ts").read_text(encoding="utf-8")
    app_css = (tmp_path / "src/App.css").read_text(encoding="utf-8")
    assert '@import "tailwindcss";' in app_css
    assert "@theme { --color-primary:" in app_css
    assert "@tailwindcss/vite" in (tmp_path / "package.json").read_text(encoding="utf-8")
