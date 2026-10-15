from agent.site_acceptance import check_site_files


def test_recovery_does_not_excuse_invalid_or_globally_leaking_css():
    result = check_site_files({
        'src/components/Footer.css': '.section__inner {display:grid}',
        'src/components/Pricing.css': '.pricing {margin-right}',
        'src/components/Pricing.tsx': '<a href="#">Buy</a>',
    })
    assert not result['static_passed']
    assert len(result['errors']) == 3
    assert result['interaction_status'] == 'unverified'


def test_scoped_rules_do_not_claim_visual_or_behavior_verification():
    result = check_site_files({'src/components/Hero.css': '#hero .section__inner {display:grid}'})
    assert result['static_passed']
    assert result['visual_review_status'] == 'unverified'


def test_comma_selectors_cannot_hide_cross_section_rules():
    result = check_site_files({'src/components/Footer.css': '#footer p, .section__inner {display:grid}'})
    assert not result['static_passed']
    assert check_site_files({'src/components/Footer.css': '@scope (#footer) { .section__inner {display:grid} }'})['static_passed']


def test_incomplete_tool_envelopes_are_rejected_without_breaking_log_parser():
    from agent.agent_protocol import site_envelope_errors
    prefix = '<tool_call name="write_site"><file path="src/components/Hero.tsx">export default () => <div/>'
    assert site_envelope_errors(prefix)
    assert site_envelope_errors(prefix + '</tool_call>')
    assert not site_envelope_errors(prefix + '</file></tool_call>')


# ── P0-05: Fail-closed static lint (missing 'static_passed' key) ──────────────

def test_p0_05_malformed_acceptance_result_missing_static_passed_key():
    """If check_site_files returns a dict without 'static_passed', run_static_lint must
    return (False, [error_msg], warnings) — never default the missing key to True."""
    import tempfile
    from pathlib import Path
    from unittest.mock import patch
    from agent.project_validator import run_static_lint

    with tempfile.TemporaryDirectory() as tmp_dir:
        workspace = Path(tmp_dir)
        (workspace / "App.tsx").write_text(
            "export default function App() { return <div>Hello</div>; }",
            encoding="utf-8",
        )
        # Return a schema that omits 'static_passed' entirely
        malformed = {
            "errors": [],
            "checks": {},
            "interaction_status": "unverified",
            "visual_review_status": "unverified",
            # NOTE: 'static_passed' is intentionally absent
        }
        with patch("agent.site_acceptance.check_site_files", return_value=malformed):
            passed, errors, warnings = run_static_lint(workspace)
        assert passed is False, "Missing 'static_passed' must fail closed"
        assert any("Malformed acceptance result" in e for e in errors), (
            f"Expected a malformed-schema error message; got: {errors}"
        )


def test_p0_05_present_static_passed_false_still_fails():
    """Explicit static_passed=False still returns failure (regression guard)."""
    import tempfile
    from pathlib import Path
    from unittest.mock import patch
    from agent.project_validator import run_static_lint

    with tempfile.TemporaryDirectory() as tmp_dir:
        workspace = Path(tmp_dir)
        (workspace / "App.tsx").write_text(
            "export default function App() { return <div/>; }",
            encoding="utf-8",
        )
        failing = {
            "static_passed": False,
            "errors": ["CSS syntax error: unexpected token"],
            "checks": {"css_syntax": "fail"},
            "interaction_status": "unverified",
            "visual_review_status": "unverified",
        }
        with patch("agent.site_acceptance.check_site_files", return_value=failing):
            passed, errors, _warnings = run_static_lint(workspace)
        assert passed is False
        assert any("CSS syntax error" in e for e in errors)


def test_p0_05_present_static_passed_true_succeeds():
    """Explicit static_passed=True with no errors returns success."""
    import tempfile
    from pathlib import Path
    from unittest.mock import patch
    from agent.project_validator import run_static_lint

    with tempfile.TemporaryDirectory() as tmp_dir:
        workspace = Path(tmp_dir)
        (workspace / "App.tsx").write_text(
            "export default function App() { return <div/>; }",
            encoding="utf-8",
        )
        ok = {
            "static_passed": True,
            "errors": [],
            "checks": {},
            "interaction_status": "unverified",
            "visual_review_status": "unverified",
        }
        with patch("agent.site_acceptance.check_site_files", return_value=ok):
            passed, errors, _warnings = run_static_lint(workspace)
        assert passed is True
        assert errors == []


# ── P0-06: Content provenance — fabricated testimonials are hard errors ────────

def test_p0_06_fabricated_testimonial_is_hard_fail():
    """A file containing 'CEO of Acme' (job-title + org) must fail static_passed."""
    result = check_site_files({
        'src/components/Testimonials.tsx': (
            '<blockquote>"Best product ever." \u2014 Jane Smith, CEO of Acme Corp</blockquote>'
        ),
    })
    assert result['static_passed'] is False, (
        "Fabricated testimonial (generated_placeholder) must block static_passed"
    )
    assert result['checks']['fabricated_testimonials'] == 'fail'
    assert any("Content Provenance Error" in e for e in result['errors'])


def test_p0_06_testimonial_error_is_not_downgraded_to_warning():
    """The testimonial error message must NOT contain 'possible' (warn-language)."""
    result = check_site_files({
        'src/Testimonials.tsx': '"Great!" \u2014 Alice Wong, Director of Engineering at Widgets Inc',
    })
    testimonial_errors = [e for e in result['errors'] if 'fabricated testimonial' in e.lower()]
    assert testimonial_errors, "Expected at least one fabricated testimonial error"
    for e in testimonial_errors:
        assert 'possible' not in e.lower(), (
            f"Error message must not use warning language ('possible'): {e}"
        )


def test_p0_06_placeholder_contact_remains_warning_not_hard_fail():
    """Placeholder contact details (555 number / example.com) remain warnings — they
    may be clearly-illustrative and should not block static_passed alone."""
    result = check_site_files({
        'src/Contact.tsx': 'Call us at (555) 867-5309 or hello@example.com',
    })
    # Contact alone must NOT fail static_passed
    assert result['static_passed'] is True, (
        "Placeholder contact details should remain a warning, not a hard fail"
    )
    assert result['checks']['fabricated_contacts'] == 'warn'
    assert any('possible placeholder contact details' in e for e in result['errors'])


def test_p0_06_content_provenance_enum_exported():
    """ContentProvenance and BLOCKED_PLACEHOLDER_CATEGORIES must be importable."""
    from agent.site_acceptance import ContentProvenance, BLOCKED_PLACEHOLDER_CATEGORIES
    assert ContentProvenance.GENERATED_PLACEHOLDER.value == "generated_placeholder"
    assert "testimonials" in BLOCKED_PLACEHOLDER_CATEGORIES
    assert "people" in BLOCKED_PLACEHOLDER_CATEGORIES
    assert "awards" in BLOCKED_PLACEHOLDER_CATEGORIES


def test_p0_06_clean_file_passes_all_checks():
    """A file with no fabricated entities passes all provenance checks."""
    result = check_site_files({
        'src/Hero.tsx': (
            'export default function Hero() { return <h1>Welcome to Our Service</h1>; }'
        ),
    })
    assert result['static_passed'] is True
    assert result['checks']['fabricated_testimonials'] == 'ok'
    assert result['checks']['fabricated_contacts'] == 'ok'
