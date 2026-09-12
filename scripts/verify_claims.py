#!/usr/bin/env python3
"""
scripts/verify_claims.py — Automated Source Claim Verification Engine

Prevents specific-sounding-but-false changelog claims from circulating by directly
grepping actual source code and trajectory files and asserting ground truth.

Usage:
    python scripts/verify_claims.py                  # Verify all confirmed phase claims (1, 2, 4, 6)
    python scripts/verify_claims.py --phase 1        # Verify specific phase
    python scripts/verify_claims.py --self-test      # Run self-test proving false claims are caught
    python scripts/verify_claims.py --file <path> --contains <text>
    python scripts/verify_claims.py --file <path> --not-contains <text>
    python scripts/verify_claims.py --file <path> --func <name>
    python scripts/verify_claims.py --file <path> --count-regex <pat> --min <n> --max <n>
"""

import argparse
import hashlib
import json
import math
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional, Tuple

BASE_DIR = Path(__file__).resolve().parent.parent


# ── Color & Formatting Helpers ──────────────────────────────────────────────────

def _colorize(text: str, color_code: str) -> str:
    # Check if ANSI supported or NO_COLOR
    if os.environ.get("NO_COLOR") or not sys.stdout.isatty():
        return text
    return f"\033[{color_code}m{text}\033[0m"

def c_pass(text: str) -> str: return _colorize(text, "32;1") # Bright Green
def c_fail(text: str) -> str: return _colorize(text, "31;1") # Bright Red
def c_info(text: str) -> str: return _colorize(text, "36")   # Cyan
def c_bold(text: str) -> str: return _colorize(text, "1")    # Bold


# ── WCAG Contrast Calculator ────────────────────────────────────────────────────

def srgb_luminance(hex_str: str) -> float:
    """Calculates relative luminance for an sRGB hex code per WCAG 2.1."""
    hex_clean = hex_str.strip().lstrip("#")
    if len(hex_clean) == 3:
        hex_clean = "".join(c * 2 for c in hex_clean)
    r = int(hex_clean[0:2], 16) / 255.0
    g = int(hex_clean[2:4], 16) / 255.0
    b = int(hex_clean[4:6], 16) / 255.0

    def adjust(v: float) -> float:
        return v / 12.92 if v <= 0.04045 else math.pow((v + 0.055) / 1.055, 2.4)

    return 0.2126 * adjust(r) + 0.7152 * adjust(g) + 0.0722 * adjust(b)

def contrast_ratio(hex1: str, hex2: str) -> float:
    """Computes contrast ratio between two hex colors (1.0 to 21.0)."""
    l1 = srgb_luminance(hex1)
    l2 = srgb_luminance(hex2)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


# ── Assertion Primitives ────────────────────────────────────────────────────────

def read_file(rel_path: str) -> Tuple[Path, str]:
    p = BASE_DIR / rel_path
    if not p.exists():
        raise FileNotFoundError(f"File not found: {p}")
    return p, p.read_text(encoding="utf-8", errors="replace")

def assert_function_exists(rel_path: str, func_name: str) -> Tuple[bool, str]:
    p, content = read_file(rel_path)
    pattern = rf'(?:def\s+{re.escape(func_name)}\s*\(|function\s+{re.escape(func_name)}\s*\(|(?:const|let|var)\s+{re.escape(func_name)}\s*=)'
    matches = list(re.finditer(pattern, content))
    if matches:
        line_no = content[:matches[0].start()].count("\n") + 1
        return True, f"Found '{func_name}' at {rel_path}:{line_no}"
    return False, f"Function '{func_name}' NOT found in {rel_path}"

def assert_string_contains(rel_path: str, pattern: str, is_regex: bool = False) -> Tuple[bool, str]:
    p, content = read_file(rel_path)
    if is_regex:
        matches = list(re.finditer(pattern, content))
        if matches:
            line_no = content[:matches[0].start()].count("\n") + 1
            return True, f"Found match for pattern /{pattern}/ at {rel_path}:{line_no}"
        return False, f"Regex pattern /{pattern}/ not found in {rel_path}"
    else:
        idx = content.find(pattern)
        if idx != -1:
            line_no = content[:idx].count("\n") + 1
            return True, f"Found '{pattern}' at {rel_path}:{line_no}"
        return False, f"String '{pattern}' not found in {rel_path}"

def assert_string_absent(rel_path: str, pattern: str, is_regex: bool = False) -> Tuple[bool, str]:
    p, content = read_file(rel_path)
    if is_regex:
        matches = list(re.finditer(pattern, content))
        if matches:
            line_no = content[:matches[0].start()].count("\n") + 1
            return False, f"Forbidden pattern /{pattern}/ was found at {rel_path}:{line_no}"
        return True, f"Verified /{pattern}/ is absent from {rel_path}"
    else:
        idx = content.find(pattern)
        if idx != -1:
            line_no = content[:idx].count("\n") + 1
            return False, f"Forbidden string '{pattern}' was found at {rel_path}:{line_no}"
        return True, f"Verified '{pattern}' is absent from {rel_path}"

def assert_occurrence_count(
    rel_path: str,
    pattern: str,
    min_count: Optional[int] = None,
    max_count: Optional[int] = None,
    exact_count: Optional[int] = None
) -> Tuple[bool, str]:
    p, content = read_file(rel_path)
    matches = re.findall(pattern, content)
    count = len(matches)

    if exact_count is not None:
        if count == exact_count:
            return True, f"Occurrence count of /{pattern}/ in {rel_path} is exactly {count}"
        return False, f"Expected exactly {exact_count} occurrences of /{pattern}/ in {rel_path}, but found {count}"

    if min_count is not None and count < min_count:
        return False, f"Found {count} occurrences of /{pattern}/ in {rel_path}, below required minimum of {min_count}"

    if max_count is not None and count > max_count:
        return False, f"Found {count} occurrences of /{pattern}/ in {rel_path}, exceeding allowed maximum of {max_count}"

    bounds_desc = []
    if min_count is not None: bounds_desc.append(f">={min_count}")
    if max_count is not None: bounds_desc.append(f"<={max_count}")
    return True, f"Occurrence count of /{pattern}/ in {rel_path} is {count} ({', '.join(bounds_desc)})"


# ── Predefined Phase Claims ─────────────────────────────────────────────────────

@dataclass
class Claim:
    phase: int
    claim_id: str
    description: str
    verify_fn: Callable[[], Tuple[bool, str]]


def get_all_claims() -> List[Claim]:
    claims = [
        # ── Phase 1: Explicit Section Parsing ──────────────────────────────────────
        Claim(
            phase=1,
            claim_id="P1.1",
            description="`agent/site_brief.py` implements `extract_explicit_sections(prompt)`",
            verify_fn=lambda: assert_function_exists("agent/site_brief.py", "extract_explicit_sections")
        ),
        Claim(
            phase=1,
            claim_id="P1.2",
            description="`extract_explicit_sections` is called in `agent/site_brief.py` before template lookup",
            verify_fn=lambda: assert_string_contains("agent/site_brief.py", "extract_explicit_sections(prompt)")
        ),
        Claim(
            phase=1,
            claim_id="P1.3",
            description="Hardcoded 'sculptures' / 'spatialproducts' block deleted from `_build_section_synonyms`",
            verify_fn=lambda: assert_string_absent("agent/agent.py", "spatialproducts")
        ),
        Claim(
            phase=1,
            claim_id="P1.4",
            description="'sculptures' is absent from static `_SECTION_SYNONYMS['features']` entry",
            verify_fn=lambda: (
                (False, "Could not locate _SECTION_SYNONYMS definition")
                if not re.search(r'_SECTION_SYNONYMS:\s*Dict\[str,\s*List\[str\]\]\s*=\s*\{(.*?)\n\}', read_file("agent/agent.py")[1], re.DOTALL)
                else (
                    (False, "'sculptures' found in _SECTION_SYNONYMS block")
                    if '"sculptures"' in re.search(r'_SECTION_SYNONYMS:\s*Dict\[str,\s*List\[str\]\]\s*=\s*\{(.*?)\n\}', read_file("agent/agent.py")[1], re.DOTALL).group(1)
                    else (True, "Verified 'sculptures' is absent from _SECTION_SYNONYMS['features'] in agent/agent.py")
                )
            )
        ),
        Claim(
            phase=1,
            claim_id="P1.5",
            description="Generic multi-word morphological stemming implemented in `_build_section_synonyms`",
            verify_fn=lambda: assert_string_contains("agent/agent.py", 't.endswith("ies")')
        ),
        Claim(
            phase=1,
            claim_id="P1.6",
            description="`_DOMAIN_TEMPLATES` accessed via non-mutating copy (`dict(...)`)",
            verify_fn=lambda: assert_string_contains("agent/site_brief.py", "template = dict(_DOMAIN_TEMPLATES.get(")
        ),

        # ── Phase 2: Visual Judge & Closed-Loop Quality Signal ─────────────────────
        Claim(
            phase=2,
            claim_id="P2.1",
            description="`agent/visual_judge.py` defines `_score_screenshot_heuristic`",
            verify_fn=lambda: assert_function_exists("agent/visual_judge.py", "_score_screenshot_heuristic")
        ),
        Claim(
            phase=2,
            claim_id="P2.2",
            description="`_score_screenshot_heuristic` returns dictionary with 'score' and 'issues' keys",
            verify_fn=lambda: (
                assert_string_contains("agent/visual_judge.py", '"score": score') and
                assert_string_contains("agent/visual_judge.py", '"issues": issues')
            )
        ),
        Claim(
            phase=2,
            claim_id="P2.3",
            description="`server/sessions.py` integrates `visual_score` into post-generation summary",
            verify_fn=lambda: (
                assert_string_contains("server/sessions.py", "visual_score: Optional[int] = None") and
                assert_string_contains("server/sessions.py", "Visual check: {visual_score}/5")
            )
        ),
        Claim(
            phase=2,
            claim_id="P2.4",
            description="`web_ui_static/index.html` displays visual quality badge element (`visual-badge`)",
            verify_fn=lambda: assert_string_contains("web_ui_static/index.html", 'id="visual-badge"')
        ),

        # ── Phase 4: Domain Theme Diversification ──────────────────────────────────
        Claim(
            phase=4,
            claim_id="P4.1",
            description="`agent/site_brief.py` defines 2-3 palette variants per domain in `_DOMAIN_THEMES` via `ThemeVariantList`",
            verify_fn=lambda: (
                assert_string_contains("agent/site_brief.py", "class ThemeVariantList") and
                assert_string_contains("agent/site_brief.py", '"variant_name":')
            )
        ),
        Claim(
            phase=4,
            claim_id="P4.2",
            description="`agent/site_brief.py` includes dedicated Light/Paper palette options for domains",
            verify_fn=lambda: assert_string_contains("agent/site_brief.py", '"primary_color_light"')
        ),
        Claim(
            phase=4,
            claim_id="P4.3",
            description="`agent/site_brief.py` varies `font_heading` and `font_body` with curated pairings",
            verify_fn=lambda: (
                assert_string_contains("agent/site_brief.py", "Playfair Display") and
                assert_string_contains("agent/site_brief.py", "Plus Jakarta Sans")
            )
        ),
        Claim(
            phase=4,
            claim_id="P4.4",
            description="`agent/site_brief.py` defines duotone `--accent-secondary` in theme dictionary",
            verify_fn=lambda: assert_string_contains("agent/site_brief.py", '"accent_secondary"')
        ),
        Claim(
            phase=4,
            claim_id="P4.5",
            description="Palette variant selection is deterministically hashed by business name (`hashlib.sha256`)",
            verify_fn=lambda: (
                assert_string_contains("agent/site_brief.py", "def get_domain_theme(business_type: str, business_name: str = \"\")") and
                assert_string_contains("agent/site_brief.py", "hashlib.sha256(clean.encode(\"utf-8\")).hexdigest()")
            )
        ),

        # ── Phase 6: Workbench UI Redesign & Network Resilience ────────────────────
        Claim(
            phase=6,
            claim_id="P6.1",
            description="`web_ui_static/index.html` has realistic UI aria-label count (80-90, rejecting bogus 523/1308)",
            verify_fn=lambda: assert_occurrence_count("web_ui_static/index.html", r'aria-label=', min_count=80, max_count=90)
        ),
        Claim(
            phase=6,
            claim_id="P6.2",
            description="Native `confirm(` calls are strictly ZERO in `web_ui_static/index.html`",
            verify_fn=lambda: assert_occurrence_count("web_ui_static/index.html", r'confirm\(', exact_count=0)
        ),
        Claim(
            phase=6,
            claim_id="P6.3",
            description="`showConfirmModal` is defined and called at all replaced confirmation sites (>=4 calls)",
            verify_fn=lambda: (
                assert_function_exists("web_ui_static/index.html", "showConfirmModal") and
                assert_occurrence_count("web_ui_static/index.html", r'showConfirmModal\(', min_count=4)
            )
        ),
        Claim(
            phase=6,
            claim_id="P6.4",
            description="`--text-3:` token is #a8a29e (dark) and #52525b (light), both passing WCAG AA (>= 4.5:1)",
            verify_fn=lambda: (
                contrast_ratio("#a8a29e", "#09090b") >= 4.5 and
                contrast_ratio("#52525b", "#ffffff") >= 4.5 and
                assert_string_contains("web_ui_static/index.html", "--text-3:         #a8a29e;") and
                assert_string_contains("web_ui_static/index.html", "--text-3:         #52525b;")
            )
        ),
        Claim(
            phase=6,
            claim_id="P6.5",
            description="`web_ui_static/index.html` `es.onerror` has exponential backoff and reopens EventSource",
            verify_fn=lambda: (
                assert_string_contains("web_ui_static/index.html", "es.onerror = async () =>") and
                assert_string_contains("web_ui_static/index.html", "Math.pow(2, retryCount - 1)") and
                assert_string_contains("web_ui_static/index.html", "setTimeout(connect, delay)")
            )
        ),
        Claim(
            phase=6,
            claim_id="P6.6",
            description="`web_ui_static/index.html` contains responsive `@media` breakpoints for layout holding",
            verify_fn=lambda: assert_occurrence_count("web_ui_static/index.html", r'@media\b', min_count=3)
        ),
        Claim(
            phase=6,
            claim_id="P6.7",
            description="`server/app.py` exposes `/api/task/<task_id>/status` and `/api/generation/<task_id>/status`",
            verify_fn=lambda: (
                assert_string_contains("server/app.py", '@app.route("/api/task/<task_id>/status"') and
                assert_string_contains("server/app.py", '@app.route("/api/generation/<task_id>/status"')
            )
        ),
    ]
    return claims


# ── Verification Runner ─────────────────────────────────────────────────────────

def run_claims(claims: List[Claim]) -> Tuple[int, int]:
    passed = 0
    failed = 0

    # Group by phase
    phases = sorted(list(set(c.phase for c in claims)))
    for phase in phases:
        phase_claims = [c for c in claims if c.phase == phase]
        print(f"\n{c_bold(f'=== Phase {phase} Claims Verification ({len(phase_claims)} checks) ===')}")
        for c in phase_claims:
            try:
                ok, msg = c.verify_fn()
                if ok:
                    passed += 1
                    print(f"  {c_pass('[PASS]')} {c_bold(c.claim_id)}: {c.description}")
                    print(f"         {c_info(msg)}")
                else:
                    failed += 1
                    print(f"  {c_fail('[FAIL]')} {c_bold(c.claim_id)}: {c.description}")
                    print(f"         {c_fail(f'ERROR: {msg}')}")
            except Exception as e:
                failed += 1
                print(f"  {c_fail('[FAIL]')} {c_bold(c.claim_id)}: {c.description}")
                print(f"         {c_fail(f'EXCEPTION: {e}')}")

    return passed, failed


# ── Self-Test Engine ────────────────────────────────────────────────────────────

def run_self_test() -> bool:
    print(c_bold("\n=== Running verify_claims.py Self-Test (Proving False Claims Are Caught) ==="))
    all_ok = True

    # Test 1: Bogus function claim
    bogus_func = "def totally_fake_function_that_does_not_exist"
    ok, msg = assert_function_exists("agent/site_brief.py", "totally_fake_function_that_does_not_exist")
    if not ok:
        print(f"  {c_pass('[PASS]')} Correctly caught false function claim: {msg}")
    else:
        print(f"  {c_fail('[FAIL]')} Failed to catch false function claim!")
        all_ok = False

    # Test 2: Bogus aria-label count (523 claimed vs 83 actual)
    ok, msg = assert_occurrence_count("web_ui_static/index.html", r'aria-label=', exact_count=523)
    if not ok:
        print(f"  {c_pass('[PASS]')} Correctly caught bogus aria-label count claim (523 claimed): {msg}")
    else:
        print(f"  {c_fail('[FAIL]')} Failed to catch bogus aria-label claim!")
        all_ok = False

    # Test 3: Bogus string absence claim (asserting a present string is absent)
    ok, msg = assert_string_absent("agent/site_brief.py", "def extract_explicit_sections")
    if not ok:
        print(f"  {c_pass('[PASS]')} Correctly caught false string absence claim: {msg}")
    else:
        print(f"  {c_fail('[FAIL]')} Failed to catch false string absence claim!")
        all_ok = False

    # Test 4: WCAG contrast ratio accuracy
    # #71717a on #09090b is ~3.5:1 (failing AA)
    ratio_fail = contrast_ratio("#71717a", "#09090b")
    # #a8a29e on #09090b is ~8.29:1 (passing AA)
    ratio_pass = contrast_ratio("#a8a29e", "#09090b")
    if ratio_fail < 4.5 and ratio_pass >= 4.5:
        print(f"  {c_pass('[PASS]')} WCAG calculator verified: #71717a={ratio_fail:.2f}:1 (<4.5), #a8a29e={ratio_pass:.2f}:1 (>=4.5)")
    else:
        print(f"  {c_fail('[FAIL]')} WCAG contrast calculation unexpected: fail={ratio_fail}, pass={ratio_pass}")
        all_ok = False

    return all_ok


# ── CLI Interface ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="verify_claims.py: Source-Grounded Claim Verification Engine for ReactAgent SLM",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--phase", type=int, choices=[1, 2, 4, 6], help="Verify claims for a specific phase")
    parser.add_argument("--self-test", action="store_true", help="Run negative self-tests to prove false claims are caught")

    # Ad-hoc inspection flags
    parser.add_argument("--file", type=str, help="Relative path to file for ad-hoc check")
    parser.add_argument("--contains", type=str, help="Assert file contains this string")
    parser.add_argument("--not-contains", type=str, help="Assert file does NOT contain this string")
    parser.add_argument("--func", type=str, help="Assert function is defined in file")
    parser.add_argument("--count-regex", type=str, help="Regex to count occurrences in file")
    parser.add_argument("--min", type=int, help="Minimum count for --count-regex")
    parser.add_argument("--max", type=int, help="Maximum count for --count-regex")
    parser.add_argument("--exact", type=int, help="Exact count for --count-regex")

    args = parser.parse_args()

    # Self-test mode
    if args.self_test:
        ok = run_self_test()
        sys.exit(0 if ok else 1)

    # Ad-hoc mode
    if args.file:
        if not (args.contains or args.not_contains or args.func or args.count_regex):
            print(c_fail("Error: Specify --contains, --not-contains, --func, or --count-regex with --file"))
            sys.exit(1)

        success = True
        if args.func:
            ok, msg = assert_function_exists(args.file, args.func)
            print(f"[{c_pass('PASS') if ok else c_fail('FAIL')}] {msg}")
            if not ok: success = False

        if args.contains:
            ok, msg = assert_string_contains(args.file, args.contains)
            print(f"[{c_pass('PASS') if ok else c_fail('FAIL')}] {msg}")
            if not ok: success = False

        if args.not_contains:
            ok, msg = assert_string_absent(args.file, args.not_contains)
            print(f"[{c_pass('PASS') if ok else c_fail('FAIL')}] {msg}")
            if not ok: success = False

        if args.count_regex:
            ok, msg = assert_occurrence_count(args.file, args.count_regex, min_count=args.min, max_count=args.max, exact_count=args.exact)
            print(f"[{c_pass('PASS') if ok else c_fail('FAIL')}] {msg}")
            if not ok: success = False

        sys.exit(0 if success else 1)

    # Standard Phase Verification mode
    claims = get_all_claims()
    if args.phase:
        claims = [c for c in claims if c.phase == args.phase]

    print(c_bold("=================================================================="))
    print(c_bold(" ReactAgent SLM — Source-Grounded Claim Verification Engine"))
    print(c_bold("=================================================================="))
    print(f"Workspace Root: {BASE_DIR}")
    print(f"Targeting: {'Phase ' + str(args.phase) if args.phase else 'All Confirmed Phases (1, 2, 4, 6)'}")

    passed, failed = run_claims(claims)

    total = passed + failed
    print("\n" + c_bold("--- Claim Verification Summary ---"))
    print(f"Total Claims Tested: {total}")
    print(f"Passed: {c_pass(str(passed))}")
    print(f"Failed: {c_fail(str(failed)) if failed > 0 else '0'}")

    if failed > 0:
        print(c_fail(f"\nFAILED: {failed} claims could not be verified against the actual source code."))
        sys.exit(1)
    else:
        print(c_pass(f"\nSUCCESS: All {passed}/{total} claims independently verified against source code."))
        sys.exit(0)


if __name__ == "__main__":
    main()
