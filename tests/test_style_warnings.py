"""
tests/test_style_warnings.py - Regression test for unparsed design-system constraints warning.
"""

import sys
from pathlib import Path

# Add workspace root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from agent.style_ingest import parse_css_tokens, StyleSpec
from server.sessions import generate_post_generation_summary


def test_non_standard_rules_triggers_parse_warning():
    """Verify non-standard rules format (e.g. 'Rules: never use box-shadow') generates parse_warnings."""
    custom_doc = """
Rules: never use box-shadow
Always maintain crisp borders.

:root {
  --color-primary: #121212;
  --accent-color: #38bdf8;
  --radius-buttons: 4px;
}
"""
    spec = parse_css_tokens(custom_doc, name="Test Custom Doc")

    # Verify parse_warnings is non-empty
    assert len(spec.parse_warnings) > 0, "Expected spec.parse_warnings to be non-empty for non-standard rules format"
    expected_fragment = "Could not detect explicit Do's/Don'ts sections in the pasted design system"
    assert any(expected_fragment in w for w in spec.parse_warnings), f"Warning not found in: {spec.parse_warnings}"

    # Verify summary reflects the warning in Status section
    summary = generate_post_generation_summary(
        mode="site",
        files_touched=["Header.tsx", "Hero.tsx"],
        passed=True,
        auto_recovered=[],
        user_instruction="Build modern homepage",
        is_edit=False,
        sections_completed=2,
        sections_planned=2,
        parse_warnings=spec.parse_warnings,
    )

    assert "## Status" in summary
    assert "⚠️ Design System Warning:" in summary
    assert expected_fragment in summary
    print("PASS: test_non_standard_rules_triggers_parse_warning")


def test_standard_rules_no_warning():
    """Verify standard Do's: and Don'ts: headers populate rules without generating parse_warnings."""
    standard_doc = """
Do's:
- Use subtle border glow on hover
- Maintain 8px spacing scale

Don'ts:
- Never hardcode raw hex values
- Avoid saturated gradients

:root {
  --color-primary: #0a0a0a;
  --accent-color: #22c55e;
}
"""
    spec = parse_css_tokens(standard_doc, name="Standard Doc")
    assert len(spec.parse_warnings) == 0, f"Expected 0 parse_warnings for standard doc, got: {spec.parse_warnings}"
    assert len(spec.dos) == 2
    assert any("raw hex" in d for d in spec.donts)
    print("PASS: test_standard_rules_no_warning")


def test_pure_css_tokens_no_warning():
    """Verify pure CSS :root {...} block without prose does not trigger parse_warnings."""
    pure_css = """
:root {
  --color-primary: #090d16;
  --accent-color: #38bdf8;
  --radius-buttons: 8px;
}
"""
    spec = parse_css_tokens(pure_css, name="Pure CSS Tokens")
    assert len(spec.parse_warnings) == 0, f"Expected 0 parse_warnings for pure CSS, got: {spec.parse_warnings}"
    print("PASS: test_pure_css_tokens_no_warning")


if __name__ == "__main__":
    test_non_standard_rules_triggers_parse_warning()
    test_standard_rules_no_warning()
    test_pure_css_tokens_no_warning()
    print("\nALL DESIGN SYSTEM PARSE WARNING TESTS PASSED.")
