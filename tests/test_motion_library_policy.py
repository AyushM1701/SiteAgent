"""
tests/test_motion_library_policy.py - Comprehensive Unit & Integration Tests for:
Section 6: Motion Library Policy
1. Default to native browser/CSS implementations on local constrained hardware.
2. Only use GSAP/ScrollTrigger or Framer Motion when dependency inspection confirms it.
3. Never train trajectories that silently import an unverified package.
4. If GSAP or Framer Motion support is added, create separate library-specific trajectories rather than mixing them into native examples without labels.
"""

import json
import pytest
import tempfile
from pathlib import Path

from agent.motion_patterns import (
    MotionType,
    MotionSpec,
    EXTERNAL_MOTION_LIBRARIES,
    inspect_motion_library_imports,
    verify_motion_library_dependency,
    validate_motion_library_policy,
    validate_trajectory_motion_policy,
    generate_gsap_trajectory_snippet,
    generate_framer_motion_trajectory_snippet,
    get_motion_implementation_guidelines,
    validate_motion_rules,
)
from agent.project_validator import run_motion_rules_check
from evaluation.site_benchmark_scorer import SiteBenchmarkScorer


# ── 1. Default Native Policy & Import Inspection Tests ────────────────────────

def test_default_native_policy_no_external_libraries():
    """Pure native React + CSS implementations pass Motion Library Policy with 0 violations."""
    files = {
        "src/Features.tsx": """
        import React, { useEffect, useRef } from 'react';
        export function Features() {
            const ref = useRef<HTMLDivElement>(null);
            useEffect(() => {
                const observer = new IntersectionObserver((entries) => {});
                if (ref.current) observer.observe(ref.current);
                return () => observer.disconnect();
            }, []);
            return <div ref={ref}>Native Content</div>;
        }
        """,
        "src/Features.css": "@media (prefers-reduced-motion: reduce) { div { opacity: 1; } }",
    }
    is_valid, violations, details = validate_motion_library_policy(files)
    assert is_valid is True
    assert len(violations) == 0
    assert details["external_libraries_detected"] == []


def test_inspect_motion_library_imports_detects_all_targets():
    """inspect_motion_library_imports accurately identifies gsap, framer-motion, and lenis."""
    files = {
        "src/A.tsx": "import { gsap } from 'gsap'; import { ScrollTrigger } from 'gsap/ScrollTrigger';",
        "src/B.tsx": "import { motion, AnimatePresence } from 'framer-motion';",
        "src/C.tsx": "import Lenis from '@studio-freight/lenis';",
        "src/D.tsx": "import React from 'react'; // pure native",
    }
    detected = inspect_motion_library_imports(files)
    assert "gsap" in detected
    assert "framer-motion" in detected
    assert "lenis" in detected
    assert "src/A.tsx" in detected["gsap"]
    assert "src/B.tsx" in detected["framer-motion"]
    assert "src/C.tsx" in detected["lenis"]


# ── 2. Unverified Import Rejection Tests ──────────────────────────────────────

def test_unverified_gsap_import_triggers_violation():
    """TSX importing gsap without declaration in package.json fails with a policy violation."""
    files = {
        "src/Hero.tsx": "import { gsap } from 'gsap'; export function Hero() { gsap.to('.box', { x: 100 }); return null; }",
        "package.json": json.dumps({"dependencies": {"react": "^19.0.0"}}),
    }
    is_valid, violations, details = validate_motion_library_policy(files)
    assert is_valid is False
    assert len(violations) == 1
    assert "unverified external package 'gsap'" in violations[0]
    assert "Section 6" in violations[0]
    assert "gsap" in details["unverified_libraries"]


def test_unverified_framer_motion_import_triggers_violation():
    """TSX importing framer-motion without declaration in package.json fails."""
    files = {
        "src/Card.tsx": "import { motion } from 'framer-motion'; export function Card() { return <motion.div />; }",
        "package.json": json.dumps({"dependencies": {"react": "^19.0.0"}}),
    }
    is_valid, violations, details = validate_motion_library_policy(files)
    assert is_valid is False
    assert len(violations) == 1
    assert "unverified external package 'framer-motion'" in violations[0]


def test_unverified_lenis_import_triggers_violation():
    """TSX importing Lenis without declaration in package.json fails."""
    files = {
        "src/Smooth.tsx": "import Lenis from '@studio-freight/lenis'; const lenis = new Lenis();",
        "package.json": json.dumps({"dependencies": {"react": "^19.0.0"}}),
    }
    is_valid, violations, details = validate_motion_library_policy(files)
    assert is_valid is False
    assert any("lenis" in v.lower() for v in violations)


# ── 3. Verified Dependency Confirmation Tests ────────────────────────────────

def test_verified_gsap_import_in_package_json_passes():
    """When package.json declares gsap, imports pass policy verification."""
    files = {
        "src/Hero.tsx": "import { gsap } from 'gsap'; export function Hero() { return null; }",
        "package.json": json.dumps({
            "dependencies": {
                "react": "^19.0.0",
                "gsap": "^3.12.5",
            }
        }),
    }
    is_valid, violations, details = validate_motion_library_policy(files)
    assert is_valid is True
    assert len(violations) == 0
    assert "gsap" in details["verified_libraries"]


def test_verified_framer_motion_import_in_package_json_passes():
    """When package.json declares framer-motion, imports pass policy verification."""
    files = {
        "src/Card.tsx": "import { motion } from 'framer-motion'; export function Card() { return null; }",
        "package.json": json.dumps({
            "dependencies": {
                "react": "^19.0.0",
                "framer-motion": "^11.0.0",
            }
        }),
    }
    is_valid, violations, details = validate_motion_library_policy(files)
    assert is_valid is True
    assert len(violations) == 0
    assert "framer-motion" in details["verified_libraries"]


def test_verified_in_workspace_node_modules_passes():
    """When node_modules contains the package on disk, verification succeeds."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        workspace = Path(tmp_dir)
        gsap_nm = workspace / "node_modules" / "gsap"
        gsap_nm.mkdir(parents=True, exist_ok=True)

        assert verify_motion_library_dependency("gsap", workspace_dir=workspace) is True

        files = {
            "src/Hero.tsx": "import { gsap } from 'gsap'; export function Hero() { return null; }",
        }
        is_valid, violations, details = validate_motion_library_policy(files, workspace_dir=workspace)
        assert is_valid is True
        assert len(violations) == 0
        assert "gsap" in details["verified_libraries"]


# ── 4. Trajectory Training & Labeling Policy Tests ────────────────────────────

def test_trajectory_policy_unlabeled_gsap_rejected():
    """Trajectories silently importing GSAP without explicit label are rejected."""
    unlabeled_trajectory = {
        "id": "site_012",
        "prompt": "Build a modern full-stack developer portfolio with animations",
        "files": {
            "App.tsx": "import { gsap } from 'gsap'; export default function App() { return null; }",
            "package.json": json.dumps({"dependencies": {"gsap": "^3.12.5"}}),
        },
    }
    is_valid, violations = validate_trajectory_motion_policy(unlabeled_trajectory)
    assert is_valid is False
    assert len(violations) == 1
    assert "without explicit label" in violations[0]


def test_trajectory_policy_labeled_gsap_accepted():
    """Separate library-specific trajectories carrying explicit label and package are accepted."""
    labeled_trajectory = {
        "id": "site_gsap_01",
        "motion_implementation": "gsap",
        "prompt": "Build an editorial agency with [GSAP] ScrollTrigger horizontal pinned timeline",
        "package_json": {"dependencies": {"react": "^19.0.0", "gsap": "^3.12.5"}},
        "files": {
            "App.tsx": "import { gsap } from 'gsap'; export default function App() { return null; }",
        },
    }
    is_valid, violations = validate_trajectory_motion_policy(labeled_trajectory)
    assert is_valid is True
    assert len(violations) == 0


def test_trajectory_policy_missing_package_rejected():
    """Labeled trajectory that fails to declare package in package_json is rejected."""
    bad_trajectory = {
        "id": "site_framer_02",
        "motion_implementation": "framer-motion",
        "package_json": {"dependencies": {"react": "^19.0.0"}}, # missing framer-motion
        "files": {
            "App.tsx": "import { motion } from 'framer-motion'; export default function App() { return null; }",
        },
    }
    is_valid, violations = validate_trajectory_motion_policy(bad_trajectory)
    assert is_valid is False
    assert any("missing from package.json" in v for v in violations)


# ── 5. Canonical Library-Specific Trajectory Generators ───────────────────────

def test_canonical_gsap_trajectory_snippet():
    """generate_gsap_trajectory_snippet produces a separate, labeled GSAP component."""
    tsx, css, deps, spec = generate_gsap_trajectory_snippet("Showcase")
    assert "import { gsap } from 'gsap';" in tsx
    assert "gsap.registerPlugin(ScrollTrigger);" in tsx
    assert "ctx.revert()" in tsx
    assert "prefers-reduced-motion" in tsx
    assert deps == {"gsap": "^3.12.5"}
    assert spec.implementation == "gsap"

    # Trajectory validation passes when labeled
    traj = {
        "motion_implementation": "gsap",
        "package_json": {"dependencies": deps},
        "files": {"src/Showcase.tsx": tsx, "src/Showcase.css": css},
    }
    ok, violations = validate_trajectory_motion_policy(traj)
    assert ok is True
    assert len(violations) == 0


def test_canonical_framer_motion_trajectory_snippet():
    """generate_framer_motion_trajectory_snippet produces a separate, labeled Framer Motion component."""
    tsx, css, deps, spec = generate_framer_motion_trajectory_snippet("Features")
    assert "import { motion, useReducedMotion } from 'framer-motion';" in tsx
    assert "useReducedMotion()" in tsx
    assert deps == {"framer-motion": "^11.0.0"}
    assert spec.implementation == "framer-motion"

    # Trajectory validation passes when labeled
    traj = {
        "motion_implementation": "framer-motion",
        "package_json": {"dependencies": deps},
        "files": {"src/Features.tsx": tsx, "src/Features.css": css},
    }
    ok, violations = validate_trajectory_motion_policy(traj)
    assert ok is True
    assert len(violations) == 0


# ── 6. Project Validator & Scorer Integration ────────────────────────────────

def test_project_validator_motion_library_policy_violation():
    """run_motion_rules_check fails when an unverified motion package is imported on disk."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        workspace = Path(tmp_dir)

        # package.json without gsap
        (workspace / "package.json").write_text(
            json.dumps({"name": "test-site", "dependencies": {"react": "^19.0.0"}}),
            encoding="utf-8"
        )
        # TSX importing unverified gsap
        (workspace / "Hero.tsx").write_text(
            "import { gsap } from 'gsap'; export function Hero() { return <div>GSAP</div>; }",
            encoding="utf-8"
        )

        passed, errs, warns = run_motion_rules_check(workspace)
        assert passed is False
        assert any("unverified external package 'gsap'" in e.lower() for e in errs)


def test_site_benchmark_scorer_penalizes_unverified_packages():
    """SiteBenchmarkScorer applies deductions when unverified external motion libraries are imported."""
    scorer = SiteBenchmarkScorer()

    # Codebase importing unverified GSAP without package.json
    unverified_files = {
        "src/Hero.tsx": "import { gsap } from 'gsap'; export function Hero() { return null; }",
        "src/Hero.css": ".hero { transition: transform 0.2s ease; }",
    }
    score_unverified, details_unverified = scorer.score_motion_quality(unverified_files)
    assert any("unverified external package 'gsap'" in v.lower() for v in details_unverified["violations"])
    assert details_unverified["rules_validation"]["is_valid"] is False

    # Codebase with verified GSAP in package.json
    verified_files = {
        "src/Hero.tsx": "import { gsap } from 'gsap'; export function Hero() { return null; }",
        "src/Hero.css": ".hero { transition: transform 0.2s ease; }",
        "package.json": json.dumps({"dependencies": {"gsap": "^3.12.5"}}),
    }
    score_verified, details_verified = scorer.score_motion_quality(verified_files)
    assert not any("unverified external package 'gsap'" in v.lower() for v in details_verified["violations"])


# ── 7. Guidelines Include Library Policy ──────────────────────────────────────

def test_guidelines_include_policy_and_library_rules():
    """get_motion_implementation_guidelines includes library-specific and native policy rules."""
    # Native includes reminder
    native_spec = MotionSpec(type=MotionType.SCROLL_REVEAL, target_section="hero", implementation="native")
    native_guide = get_motion_implementation_guidelines(native_spec)
    assert "Motion Library Policy: Default to native browser/CSS primitives" in native_guide

    # GSAP includes ScrollTrigger rules
    gsap_spec = MotionSpec(type=MotionType.HORIZONTAL_SCROLL, target_section="showcase", implementation="gsap")
    gsap_guide = get_motion_implementation_guidelines(gsap_spec)
    assert "GSAP ScrollTrigger" in gsap_guide
    assert "gsap.context()" in gsap_guide

    # Framer Motion includes hook rules
    framer_spec = MotionSpec(type=MotionType.SCROLL_REVEAL, target_section="features", implementation="framer-motion")
    framer_guide = get_motion_implementation_guidelines(framer_spec)
    assert "Framer Motion" in framer_guide
    assert "useReducedMotion" in framer_guide
