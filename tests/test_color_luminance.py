"""
tests/test_color_luminance.py - Standalone test for is_light_color() WCAG relative luminance & CSS formats.
"""

import sys
from pathlib import Path

# Add workspace root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from agent.style_ingest import is_light_color, _wcag_relative_luminance, _extract_first_gradient_stop


def test_required_formats():
    """Verify the three required format tests from Step 2 specification."""
    c1 = "rgb(250, 248, 240)"
    c2 = "hsl(40, 30%, 95%)"
    c3 = "linear-gradient(90deg, #fff, #000)"

    assert is_light_color(c1) is True, f"Expected is_light_color({c1!r}) == True, got False"
    assert is_light_color(c2) is True, f"Expected is_light_color({c2!r}) == True, got False"
    assert is_light_color(c3) is True, f"Expected is_light_color({c3!r}) == True (first stop #fff), got False"

    print("PASS: test_required_formats ('rgb(...)', 'hsl(...)', 'linear-gradient(...)')")


def test_gradient_first_stop_reflects_actual_luminance():
    """Verify linear gradients evaluate according to the first color stop."""
    light_grad = "linear-gradient(90deg, #fff, #000)"
    dark_grad = "linear-gradient(90deg, #000, #fff)"
    light_grad_angle = "linear-gradient(180deg, hsl(40, 30%, 95%) 0%, hsl(200, 20%, 10%) 100%)"
    dark_grad_rgba = "linear-gradient(135deg, rgba(8, 12, 20, 0.95) 0%, #38bdf8 100%)"

    assert is_light_color(light_grad) is True
    assert is_light_color(dark_grad) is False
    assert is_light_color(light_grad_angle) is True
    assert is_light_color(dark_grad_rgba) is False

    print("PASS: test_gradient_first_stop_reflects_actual_luminance")


def test_hex_rgb_hsl_edge_cases():
    """Verify various hex, rgb, and hsl color representations."""
    cases = [
        # Hex formats
        ("#fff", True),
        ("#ffffff", True),
        ("#000", False),
        ("#000000", False),
        ("#38bdf8", True),     # sky blue accent (requires dark text)
        ("#080c14", False),    # obsidian dark theme
        ("#f8fafc", True),     # slate-50 paper bg
        ("#0b0f19", False),    # saas obsidian

        # RGB/RGBA
        ("rgb(255, 255, 255)", True),
        ("rgb(0, 0, 0)", False),
        ("rgba(250, 248, 240, 0.9)", True),
        ("rgba(10, 15, 25, 0.8)", False),

        # HSL/HSLA
        ("hsl(0, 0%, 100%)", True),
        ("hsl(0, 0%, 0%)", False),
        ("hsl(40, 30%, 95%)", True),
        ("hsla(215, 25%, 8%, 0.9)", False),

        # Named colors
        ("white", True),
        ("black", False),
        ("cream", True),

        # Unparseable / fallbacks
        ("not-a-color", False),
        ("", False),
        (None, False),
    ]

    for color, expected in cases:
        result = is_light_color(color)
        assert result == expected, f"Failed for {color!r}: expected {expected}, got {result}"

    print("PASS: test_hex_rgb_hsl_edge_cases")


def test_wcag_relative_luminance_math():
    """Verify WCAG relative luminance formula calculations."""
    # Pure black = 0.0
    assert abs(_wcag_relative_luminance(0, 0, 0) - 0.0) < 1e-5
    # Pure white = 1.0
    assert abs(_wcag_relative_luminance(255, 255, 255) - 1.0) < 1e-5

    # sRGB 140 neutral gray should have L ~ 0.2623
    l_140 = _wcag_relative_luminance(140, 140, 140)
    assert 0.25 < l_140 < 0.27, f"Unexpected luminance for gray(140): {l_140}"

    print("PASS: test_wcag_relative_luminance_math")


if __name__ == "__main__":
    test_required_formats()
    test_gradient_first_stop_reflects_actual_luminance()
    test_hex_rgb_hsl_edge_cases()
    test_wcag_relative_luminance_math()
    print("\nALL COLOR LUMINANCE TESTS PASSED SUCCESSFULLY.")
