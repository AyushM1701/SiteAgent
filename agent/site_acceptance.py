"""Post-recovery checks: a rendered page is not automatically a verified site.

These checks catch known failure patterns in generated code. A static pass does NOT
establish browser correctness, interaction behaviour, or visual quality — those require
browser testing and human review respectively.

Content Provenance (P0-06)
--------------------------
Every content entity produced by the model must carry one of:
  ContentProvenance.USER_SUPPLIED      — text/data taken verbatim from the user's prompt
  ContentProvenance.DATASET_GROUNDED   — fact present in the curated training corpus
  ContentProvenance.EXTERNAL_VERIFIED  — retrieved from a cited external source
  ContentProvenance.GENERATED_PLACEHOLDER — invented by the model; only permitted for
                                           structural scaffolding; NEVER for:
                                               • people / customer names
                                               • testimonials / endorsements
                                               • awards / certifications
                                               • addresses
                                               • revenue / customer counts
The `check_site_files` static gate enforces this: any file that contains detectable
generated-placeholder entities for the above categories is a HARD FAIL (not a warning).
"""
import enum
import re
try:
    from css_validation import css_syntax_errors, css_shared_selectors
except ImportError:
    from agent.css_validation import css_syntax_errors, css_shared_selectors


class ContentProvenance(enum.Enum):
    """Provenance labels for generated content entities."""
    USER_SUPPLIED = "user_supplied"
    DATASET_GROUNDED = "dataset_grounded"
    EXTERNAL_VERIFIED = "external_verified"
    GENERATED_PLACEHOLDER = "generated_placeholder"


# Entity categories that may NEVER carry ContentProvenance.GENERATED_PLACEHOLDER
# in a production export.  Violations are hard errors (block static_passed).
BLOCKED_PLACEHOLDER_CATEGORIES = frozenset({
    "people",
    "customer_names",
    "testimonials",
    "awards",
    "certifications",
    "addresses",
    "revenue_counts",
    "customer_counts",
})


# Patterns that indicate fabricated/placeholder contacts the model should not invent.
_FAKE_CONTACT_PATTERNS = [
    r'hello@example\.com',
    r'info@example\.com',
    r'contact@example\.com',
    r'support@example\.com',
    r'\bexample\.com\b',
    r'\byourdomain\.com\b',
    r'\+?1[-.\s]?\(555\)',
    r'\(555\)\s?\d{3}[-.\s]\d{4}',
]
_FAKE_CONTACT_RE = re.compile('|'.join(_FAKE_CONTACT_PATTERNS), re.I)

# Patterns that indicate fabricated testimonials paired with stock job titles.
# These are HARD FAIL (ContentProvenance.GENERATED_PLACEHOLDER for 'testimonials').
_FABRICATED_TESTIMONIAL_RE = re.compile(
    r'(?:CEO|CTO|CPO|COO|VP|Director|Head)\s+(?:of|at)\s+[A-Z][a-z]',
)

# Layout-count-as-content leak (e.g. "(6 cards)" or "Enterprise capability for 3 cards")
_COUNT_LEAK_RE = re.compile(
    r'Enterprise capability for \d+ cards|>\s*\d+ cards\s*<|\(\d+ cards\)',
)


def check_site_files(files):
    """Run static checks on all generated files.

    Returns a dict with:
      static_passed          — True only when no structural errors were found.
      errors                 — List of specific error strings for logging/display.
      checks                 — Per-check result dict for structured reporting.
      interaction_status     — Always 'unverified'; browser tests required.
      visual_review_status   — Always 'unverified'; human review required.

    Provenance policy (P0-06):
      Fabricated testimonials (job-title + org pattern) are HARD ERRORS — they represent
      ContentProvenance.GENERATED_PLACEHOLDER for the 'testimonials' category, which is
      unconditionally blocked in production exports.
      Placeholder contact details remain warnings (they may be clearly-illustrative).
    """
    errors = []
    checks = {
        'css_syntax': 'ok',
        'css_scope': 'ok',
        'placeholder_hrefs': 'ok',
        'count_leak': 'ok',
        'fabricated_contacts': 'ok',
        'fabricated_testimonials': 'ok',
    }

    for path, source in files.items():
        norm = path.replace('\\', '/')

        if path.endswith('.css'):
            syntax_errs = list(css_syntax_errors(source))
            if syntax_errs:
                checks['css_syntax'] = 'fail'
                errors.extend(f'{path}: {err}' for err in syntax_errs)

            if '/components/' in norm:
                shared = list(css_shared_selectors(source))
                if shared:
                    checks['css_scope'] = 'fail'
                    for sel in shared:
                        errors.append(
                            f'{path}: unscoped shared selector {sel!r} can restyle other sections'
                        )

        if path.endswith('.tsx') or path.endswith('.ts') or path.endswith('.jsx') or path.endswith('.js'):
            if re.search(r'href\s*=\s*["\']#["\']', source):
                checks['placeholder_hrefs'] = 'warn'
                errors.append(
                    f'{path}: possible placeholder href="#" — use anchor destinations '
                    f'(e.g. href="#section") or button elements for JS-only actions'
                )

            if _COUNT_LEAK_RE.search(source):
                checks['count_leak'] = 'fail'
                errors.append(f'{path}: layout count leaked into product content')

            if _FAKE_CONTACT_RE.search(source):
                checks['fabricated_contacts'] = 'warn'
                errors.append(
                    f'{path}: possible placeholder contact details detected '
                    f'(example.com, 555 numbers) — replace with real or clearly-illustrative values'
                )

            if _FABRICATED_TESTIMONIAL_RE.search(source):
                # P0-06: HARD FAIL — ContentProvenance.GENERATED_PLACEHOLDER is blocked
                # for the 'testimonials' category. Fabricated named endorsements must not ship.
                checks['fabricated_testimonials'] = 'fail'
                errors.append(
                    f'{path}: [Content Provenance Error] fabricated testimonial detected '
                    f'(job-title + org pattern, e.g. “CEO of Acme”). '
                    f'Provenance: generated_placeholder — blocked for testimonials/people. '
                    f'Use only user-supplied or explicitly-illustrative endorsements.'
                )

    # Hard errors block static_passed.  Warnings do not.
    # Hard errors: CSS syntax/scope failures, count leaks, fabricated testimonials
    #              (ContentProvenance.GENERATED_PLACEHOLDER for blocked categories).
    # Warnings: placeholder hrefs, fabricated contact details (may be illustrative).
    hard_errors = [
        e for e in errors
        if not (
            'possible placeholder href' in e
            or 'possible placeholder contact details' in e
        )
    ]

    return {
        'static_passed': len(hard_errors) == 0,
        'errors': errors,
        'checks': checks,
        'interaction_status': 'unverified',
        'visual_review_status': 'unverified',
        'live_interaction_evidence': False,
    }
