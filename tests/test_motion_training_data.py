"""
tests/test_motion_training_data.py - Verification Test Suite for Section 8: Motion Training Data.

Verifies:
1. Dataset file presence and synchronization (data/ and root).
2. Manifest cryptographic integrity (SHA-256 and byte sizes match on disk).
3. SFT trajectory structure: exactly 36 records (30 gold across 6 families + 6 repair).
4. Multi-turn repair trajectory contract and diagnostic observations.
5. Compliance with motion implementation rules and library policies in all SFT files.
6. Held-out evaluation benchmark: exactly 12 family-disjoint prompts across 6 families.
7. Disjointness guarantees (zero brand collisions, max Jaccard similarity < 0.40).
8. Training guide completeness (mixing ratios, QLoRA config, loss masking, promotion gates).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"

SFT_PATH_DATA = DATA_DIR / "siteagent_motion_sft_v1.jsonl"
SFT_PATH_ROOT = ROOT_DIR / "siteagent_motion_sft_v1.jsonl"

EVAL_PATH_DATA = DATA_DIR / "siteagent_motion_eval_v1.jsonl"
EVAL_PATH_ROOT = ROOT_DIR / "siteagent_motion_eval_v1.jsonl"

MANIFEST_PATH_DATA = DATA_DIR / "siteagent_motion_dataset_manifest.json"
MANIFEST_PATH_ROOT = ROOT_DIR / "siteagent_motion_dataset_manifest.json"

GUIDE_PATH_ROOT = ROOT_DIR / "SITEAGENT_MOTION_TRAINING_GUIDE.md"
GUIDE_PATH_DOCS = ROOT_DIR / "docs" / "SITEAGENT_MOTION_TRAINING_GUIDE.md"

MOTION_FAMILIES = [
    "scroll_reveal",
    "parallax",
    "horizontal_scroll",
    "sticky_story",
    "text_reveal",
    "micro_interactions",
]


def canonical_bytes(path: Path) -> bytes:
    """File content with CRLF normalised to LF: git checks text out differently per OS."""
    return path.read_bytes().replace(b"\r\n", b"\n")


def compute_sha256(path: Path) -> str:
    return hashlib.sha256(canonical_bytes(path)).hexdigest()


def tokenize(text: str) -> set[str]:
    cleaned = (
        text.lower()
        .replace(".", " ")
        .replace(",", " ")
        .replace(":", " ")
        .replace("-", " ")
        .replace("/", " ")
        .replace("(", " ")
        .replace(")", " ")
    )
    return set(cleaned.split())


# --------------------------------------------------------------------------
# 1. File Presence & Synchronization Tests
# --------------------------------------------------------------------------

def test_motion_dataset_files_exist():
    assert SFT_PATH_DATA.exists(), f"Missing {SFT_PATH_DATA}"
    assert SFT_PATH_ROOT.exists(), f"Missing {SFT_PATH_ROOT}"
    assert EVAL_PATH_DATA.exists(), f"Missing {EVAL_PATH_DATA}"
    assert EVAL_PATH_ROOT.exists(), f"Missing {EVAL_PATH_ROOT}"
    assert MANIFEST_PATH_DATA.exists(), f"Missing {MANIFEST_PATH_DATA}"
    assert MANIFEST_PATH_ROOT.exists(), f"Missing {MANIFEST_PATH_ROOT}"
    assert GUIDE_PATH_ROOT.exists(), f"Missing {GUIDE_PATH_ROOT}"
    assert GUIDE_PATH_DOCS.exists(), f"Missing {GUIDE_PATH_DOCS}"


def test_motion_dataset_files_are_synchronized():
    assert SFT_PATH_DATA.read_bytes() == SFT_PATH_ROOT.read_bytes(), "SFT root and data copies differ"
    assert EVAL_PATH_DATA.read_bytes() == EVAL_PATH_ROOT.read_bytes(), "Eval root and data copies differ"
    assert MANIFEST_PATH_DATA.read_bytes() == MANIFEST_PATH_ROOT.read_bytes(), "Manifest root and data copies differ"


# --------------------------------------------------------------------------
# 2. Manifest Cryptographic Integrity Tests
# --------------------------------------------------------------------------

def test_manifest_cryptographic_integrity():
    with open(MANIFEST_PATH_DATA, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    actual_sft_sha = compute_sha256(SFT_PATH_DATA)
    actual_sft_size = len(canonical_bytes(SFT_PATH_DATA))
    actual_eval_sha = compute_sha256(EVAL_PATH_DATA)
    actual_eval_size = len(canonical_bytes(EVAL_PATH_DATA))

    assert manifest["dataset_name"] == "siteagent_motion_v1"
    assert manifest["version"] in ("1.0.0", 1)
    assert manifest["train_sha256"] == actual_sft_sha
    assert manifest["eval_sha256"] == actual_eval_sha

    files_meta = manifest["files"]
    assert "siteagent_motion_sft_v1.jsonl" in files_meta
    assert "siteagent_motion_eval_v1.jsonl" in files_meta

    # Check SFT file hash and size
    sft_meta = files_meta["siteagent_motion_sft_v1.jsonl"]
    assert actual_sft_sha == sft_meta["sha256"], f"SFT SHA mismatch: {actual_sft_sha} vs {sft_meta['sha256']}"
    assert actual_sft_size == sft_meta["size_bytes"], f"SFT size mismatch: {actual_sft_size} vs {sft_meta['size_bytes']}"
    assert sft_meta["record_count"] == 36

    # Check Eval file hash and size
    eval_meta = files_meta["siteagent_motion_eval_v1.jsonl"]
    actual_eval_sha = compute_sha256(EVAL_PATH_DATA)
    actual_eval_size = len(canonical_bytes(EVAL_PATH_DATA))

    assert actual_eval_sha == eval_meta["sha256"], f"Eval SHA mismatch: {actual_eval_sha} vs {eval_meta['sha256']}"
    assert actual_eval_size == eval_meta["size_bytes"], f"Eval size mismatch: {actual_eval_size} vs {eval_meta['size_bytes']}"
    assert eval_meta["record_count"] == 12


# --------------------------------------------------------------------------
# 3. SFT Trajectory Architecture & Schema Tests
# --------------------------------------------------------------------------

def test_sft_record_count_and_family_distribution():
    records = [json.loads(line) for line in SFT_PATH_DATA.open(encoding="utf-8")]
    assert len(records) == 36, f"Expected 36 trajectories, got {len(records)}"

    gold_records = []
    repair_records = []
    family_counts = {}

    for item in records:
        assert "task_id" in item
        assert "messages" in item
        assert "metadata" in item

        m_type = item["metadata"].get("motion_type")
        if m_type == "micro_interaction":
            m_type = "micro_interactions"
        family_counts[m_type] = family_counts.get(m_type, 0) + 1

        if item["metadata"].get("trajectory_type") == "repair":
            repair_records.append(item)
        else:
            gold_records.append(item)

    assert len(gold_records) == 30, f"Expected 30 gold trajectories, got {len(gold_records)}"
    assert len(repair_records) == 6, f"Expected 6 repair trajectories, got {len(repair_records)}"

    # Exactly 6 per motion family (5 gold + 1 repair)
    for fam in MOTION_FAMILIES:
        assert family_counts.get(fam) == 6, f"Family {fam} count should be 6, got {family_counts.get(fam)}"


def test_sft_tool_call_contract():
    tool_call_pattern = re.compile(
        r'<tool_call name="write_site">\s*<file path="([^"]+)">([\s\S]*?)</file>\s*<file path="([^"]+)">([\s\S]*?)</file>\s*</tool_call>',
        re.MULTILINE
    )

    records = [json.loads(line) for line in SFT_PATH_DATA.open(encoding="utf-8")]
    for item in records:
        final_assistant_msg = None
        for msg in reversed(item["messages"]):
            if msg["role"] == "assistant":
                final_assistant_msg = msg["content"]
                break

        assert final_assistant_msg is not None, f"Trajectory {item['task_id']} missing assistant message"
        m = tool_call_pattern.search(final_assistant_msg)
        assert m is not None, f"Trajectory {item['task_id']} does not match write_site XML contract"

        file1, code1, file2, code2 = m.group(1), m.group(2), m.group(3), m.group(4)
        exts = {Path(file1).suffix.lower(), Path(file2).suffix.lower()}
        assert exts == {".tsx", ".css"}, f"Trajectory {item['task_id']} must have .tsx and .css files, got {exts}"
        assert len(code1.strip()) > 50, f"Trajectory {item['task_id']} has empty file {file1}"
        assert len(code2.strip()) > 50, f"Trajectory {item['task_id']} has empty file {file2}"


# --------------------------------------------------------------------------
# 4. Multi-Turn Repair Trajectories Tests
# --------------------------------------------------------------------------

def test_sft_repair_trajectories_structure():
    records = [json.loads(line) for line in SFT_PATH_DATA.open(encoding="utf-8")]
    repair_records = [r for r in records if r["metadata"].get("trajectory_type") == "repair"]
    assert len(repair_records) == 6

    expected_flaws = {
        "motion_repair_scroll_reveal_01": "observer is never disconnected",
        "motion_repair_parallax_02": "setState on every scroll event",
        "motion_repair_horizontal_scroll_03": "wheel.preventDefault()",
        "motion_repair_sticky_story_04": "overflow:hidden",
        "motion_repair_text_reveal_05": "screen readers announce every decorative span",
        "motion_repair_micro_interactions_06": "hover-only",
    }

    for item in repair_records:
        tid = item["task_id"]
        assert tid in expected_flaws
        messages = item["messages"]
        assert len(messages) >= 4, f"Repair trajectory {tid} should have at least 4 turns, got {len(messages)}"

        # Verify multi-turn structure
        roles = [m["role"] for m in messages]
        assert roles[:2] == ["system", "user"]
        assert "assistant" in roles[2:]
        assert "user" in roles[3:]

        # Verify diagnosis turn in user observation
        diag_msg = None
        for m in messages[2:]:
            if m["role"] == "user" and '<observation status="failed">' in m["content"]:
                diag_msg = m["content"]
                break

        assert diag_msg is not None, f"Repair trajectory {tid} missing <observation status=\"failed\"> diagnostic turn"


# --------------------------------------------------------------------------
# 5. Motion Rules & Native Library Policy Compliance
# --------------------------------------------------------------------------

def test_sft_code_passes_native_motion_policy():
    records = [json.loads(line) for line in SFT_PATH_DATA.open(encoding="utf-8")]

    forbidden_packages = [
        r'from\s+[\'"]gsap[\'"]',
        r'from\s+[\'"]framer-motion[\'"]',
        r'from\s+[\'"]@studio-freight/lenis[\'"]',
        r'require\([\'"]gsap[\'"]\)',
        r'require\([\'"]framer-motion[\'"]\)',
    ]

    for item in records:
        tid = item["task_id"]
        final_assistant_content = ""
        for msg in reversed(item["messages"]):
            if msg["role"] == "assistant":
                final_assistant_content = msg["content"]
                break

        # Zero unverified libraries
        for fp in forbidden_packages:
            assert not re.search(fp, final_assistant_content), (
                f"Trajectory {tid} illegally imports unverified package ({fp})"
            )

        # Prefers-reduced-motion media query present
        assert "prefers-reduced-motion" in final_assistant_content, (
            f"Trajectory {tid} missing prefers-reduced-motion fallback"
        )

        # Zero wheel/touch hijacking
        assert "wheel.preventdefault" not in final_assistant_content.lower(), (
            f"Trajectory {tid} violates zero wheel hijacking rule"
        )
        assert "touchmove.preventdefault" not in final_assistant_content.lower(), (
            f"Trajectory {tid} violates zero touchmove hijacking rule"
        )


def test_sft_motion_family_specific_mechanics():
    records = [json.loads(line) for line in SFT_PATH_DATA.open(encoding="utf-8")]

    for item in records:
        tid = item["task_id"]
        m_type = item["metadata"].get("motion_type")
        content = item["messages"][-1]["content"]

        if m_type == "scroll_reveal":
            assert "IntersectionObserver" in content
            assert ("unobserve" in content or "disconnect" in content)
        elif m_type == "parallax":
            assert "requestAnimationFrame" in content
            assert "passive: true" in content or "passive:true" in content
            assert "cancelAnimationFrame" in content
        elif m_type == "horizontal_scroll":
            assert "requestAnimationFrame" in content
            assert "scroll-snap" in content
            assert "cancelAnimationFrame" in content
        elif m_type == "sticky_story":
            assert "sticky" in content
            assert "IntersectionObserver" in content
            assert "disconnect" in content
        elif m_type == "text_reveal":
            assert "aria-label" in content
            assert "aria-hidden" in content
        elif m_type in ("micro_interaction", "micro_interactions"):
            assert ("focus-visible" in content or "focus-within" in content)
            assert "aria-pressed" in content


# --------------------------------------------------------------------------
# 6. Held-Out Evaluation Set & Disjointness Tests
# --------------------------------------------------------------------------

def test_eval_record_count_and_family_distribution():
    records = [json.loads(line) for line in EVAL_PATH_DATA.open(encoding="utf-8")]
    assert len(records) == 12, f"Expected 12 evaluation records, got {len(records)}"

    eval_families = {}
    brands = set()

    for item in records:
        assert "task_id" in item
        assert "family_id" in item
        assert "category" in item
        assert "motion_type" in item
        assert "brand" in item
        assert "prompt" in item
        assert "messages" in item
        assert "metadata" in item
        assert "checks" in item

        m_type = item["motion_type"]
        if m_type == "micro_interaction":
            m_type = "micro_interactions"
        eval_families[m_type] = eval_families.get(m_type, 0) + 1
        brands.add(item["brand"])

    # Exactly 2 tasks per motion family
    for fam in MOTION_FAMILIES:
        assert eval_families.get(fam) == 2, f"Eval family {fam} count should be 2, got {eval_families.get(fam)}"

    # Exactly 12 distinct brands
    assert len(brands) == 12, f"Expected 12 distinct brands in eval set, got {len(brands)}"


def test_eval_disjointness_and_similarity_threshold():
    sft_records = [json.loads(line) for line in SFT_PATH_DATA.open(encoding="utf-8")]
    eval_records = [json.loads(line) for line in EVAL_PATH_DATA.open(encoding="utf-8")]

    sft_brands = {
        "atelier north",
        "vector cloud",
        "arc audio",
        "field notes",
        "mira studio",
    }

    sft_prompts = []
    for item in sft_records:
        for msg in item["messages"]:
            if msg["role"] == "user":
                sft_prompts.append(msg["content"])

    max_jaccard = 0.0
    for er in eval_records:
        brand = er["brand"].lower()
        assert brand not in sft_brands, f"Eval brand '{brand}' collides with SFT brand"

        e_tok = tokenize(er["prompt"])
        for sp in sft_prompts:
            s_tok = tokenize(sp)
            j = len(e_tok & s_tok) / len(e_tok | s_tok)
            if j > max_jaccard:
                max_jaccard = j

    # Strictly lower than 0.40 requirement
    assert max_jaccard < 0.40, f"Max Jaccard similarity {max_jaccard:.4f} exceeds 0.40 threshold"
    assert max_jaccard < 0.30, f"Max Jaccard similarity {max_jaccard:.4f} should be well decoupled (<0.30)"


# --------------------------------------------------------------------------
# 7. Training Guide Verification Tests
# --------------------------------------------------------------------------

def test_training_guide_completeness():
    guide_text = GUIDE_PATH_ROOT.read_text(encoding="utf-8")

    required_keywords = [
        "Qwen3-4B",
        "siteagent_motion_sft_v1.jsonl",
        "siteagent_motion_eval_v1.jsonl",
        "siteagent_motion_dataset_manifest.json",
        "10% to 15%",
        "max_seq_length",
        "6144",
        "8192",
        "QLoRA",
        "R16",
        "alpha 32",
        "write_site",
        "prefers-reduced-motion",
        "wheel.preventDefault",
        "motion_benchmark.py",
    ]

    for kw in required_keywords:
        assert kw.lower() in guide_text.lower(), f"Training guide missing required topic: '{kw}'"
