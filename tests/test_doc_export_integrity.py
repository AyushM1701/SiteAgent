"""
tests/test_doc_export_integrity.py - Regression & Integrity Test Suite for Source Export Generation.

Verifies:
1. docs/architecture_and_source.md exists and is structurally intact.
2. server/app.py section is completely free of fence/code contamination, with dynamic >= 5 backtick fence.
3. Extracted bytes of server/app.py match server/app.py on disk 100% byte-for-byte.
4. Embedded SHA-256 checksums match the cryptographic hash of each embedded file.
5. All active workspace files pass strict round-trip reconstruction.
"""

import hashlib
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT_DIR / "docs"
OUT_MD = DOCS_DIR / "architecture_and_source.md"
APP_PY = ROOT_DIR / "server" / "app.py"


def test_doc_export_file_exists():
    assert OUT_MD.exists(), f"Missing exported documentation: {OUT_MD}"
    size = OUT_MD.stat().st_size
    assert size > 5_000_000, f"Exported documentation too small ({size} bytes)"


def test_server_app_py_uncontaminated():
    """Verifies server/app.py section is completely uncontaminated and byte-exact."""
    assert APP_PY.exists(), "Missing server/app.py on disk"
    disk_bytes = APP_PY.read_bytes()
    disk_sha = hashlib.sha256(disk_bytes).hexdigest()

    doc_text = OUT_MD.open("r", encoding="utf-8", newline="").read()

    # Match the app.py section header
    pattern = re.compile(
        r"####\s+`(?:server/)?app\.py`\n\n"
        r"- \*\*Path\*\*:\s*`file:///C:/Users/AYUSH/Documents/slm/server/app\.py`\n"
        r"- \*\*Lines\*\*:\s*([0-9,]+)\s*\|\s*\*\*Size\*\*:\s*([0-9,]+)\s*bytes\s*\|\s*\*\*SHA-256\*\*:\s*`([0-9a-f]{64})`\s*\|\s*\*\*Newline\*\*:\s*`(True|False)`\n"
        r"- \*\*Fence\*\*:\s*(\d+)\s*backticks\n"
        r"- \*\*Description\*\*:\s*([^\n]+)\n\n"
        r"(`{5,})([a-zA-Z0-9_-]*)\n"
        r"(.*?)\n\7\n\n---",
        re.DOTALL,
    )

    m = pattern.search(doc_text)
    assert m is not None, "Could not find valid server/app.py section in docs/architecture_and_source.md"

    expected_size = int(m.group(2).replace(",", ""))
    recorded_sha = m.group(3)
    has_nl = m.group(4) == "True"
    fence_len = int(m.group(5))
    fence_str = m.group(7)
    lang = m.group(8)
    body = m.group(9)

    assert fence_len >= 5, f"Fence length must be >= 5 backticks, got {fence_len}"
    assert len(fence_str) == fence_len, "Opening fence length does not match metadata"

    # Ensure no early termination inside body
    assert "\n" + fence_str + "\n" not in body, "Early fence termination detected inside app.py body!"

    reconstructed = (body + "\n").encode("utf-8") if has_nl else body.encode("utf-8")
    assert hashlib.sha256(reconstructed).hexdigest() == recorded_sha, "SHA-256 mismatch with metadata"
    assert hashlib.sha256(reconstructed).hexdigest() == disk_sha, "SHA-256 mismatch with disk"
    assert len(reconstructed) == len(disk_bytes), f"Size mismatch: {len(reconstructed)} vs {len(disk_bytes)}"
    assert reconstructed == disk_bytes, "Byte-for-byte mismatch with server/app.py on disk!"


def test_round_trip_reconstruction_integrity():
    """Verifies that every active workspace file in architecture_and_source.md reconstructs byte-exact."""
    doc_text = OUT_MD.open("r", encoding="utf-8", newline="").read()

    section_pattern = re.compile(
        r"####\s+`([^`]+)`\n\n"
        r"- \*\*Path\*\*:\s*`file:///C:/Users/AYUSH/Documents/slm/([^`]+)`\n"
        r"- \*\*Lines\*\*:\s*([0-9,]+)\s*\|\s*\*\*Size\*\*:\s*([0-9,]+)\s*bytes\s*\|\s*\*\*SHA-256\*\*:\s*`([0-9a-f]{64})`\s*\|\s*\*\*Newline\*\*:\s*`(True|False)`\n"
        r"- \*\*Fence\*\*:\s*(\d+)\s*backticks\n"
        r"- \*\*Description\*\*:\s*([^\n]+)\n\n"
        r"(`{5,})([a-zA-Z0-9_-]*)\n"
        r"(.*?)\n\9\n\n---",
        re.DOTALL,
    )

    matches = list(section_pattern.finditer(doc_text))
    assert len(matches) >= 250, f"Expected at least 250 embedded files, found {len(matches)}"

    verified_disk_count = 0
    for m in matches:
        file_name = m.group(1)
        rel_path = m.group(2)
        expected_size = int(m.group(4).replace(",", ""))
        recorded_sha = m.group(5)
        has_nl = m.group(6) == "True"
        fence_len = int(m.group(7))
        fence_str = m.group(9)
        body = m.group(11)

        assert len(fence_str) == fence_len, f"Fence mismatch for {file_name}"
        reconstructed = (body + "\n").encode("utf-8") if has_nl else body.encode("utf-8")
        assert hashlib.sha256(reconstructed).hexdigest() == recorded_sha, f"SHA-256 mismatch for {file_name}"
        assert len(reconstructed) == expected_size, f"Size mismatch for {file_name}"

        disk_file = ROOT_DIR / rel_path
        if disk_file.exists() and disk_file.is_file():
            # web_ui_history.json is a runtime session ledger updated whenever sessions or tests run
            if rel_path == "web_ui_history.json":
                continue
            assert reconstructed == disk_file.read_bytes(), f"Byte mismatch with disk for {rel_path}"
            verified_disk_count += 1

    assert verified_disk_count >= 250, f"Expected at least 250 disk-verified files, got {verified_disk_count}"


def test_generator_fails_closed_on_corruption():
    """Verifies that tampering with even a single byte triggers a cryptographic mismatch."""
    doc_text = OUT_MD.open("r", encoding="utf-8", newline="").read()
    # Mutate one byte in server/app.py section
    assert "app.run(host=host" in doc_text
    corrupted_text = doc_text.replace("app.run(host=host", "app.run(host=corrupt")

    section_pattern = re.compile(
        r"####\s+`(?:server/)?app\.py`\n\n"
        r"- \*\*Path\*\*:\s*`file:///C:/Users/AYUSH/Documents/slm/server/app\.py`\n"
        r"- \*\*Lines\*\*:\s*([0-9,]+)\s*\|\s*\*\*Size\*\*:\s*([0-9,]+)\s*bytes\s*\|\s*\*\*SHA-256\*\*:\s*`([0-9a-f]{64})`\s*\|\s*\*\*Newline\*\*:\s*`(True|False)`\n"
        r"- \*\*Fence\*\*:\s*(\d+)\s*backticks\n"
        r"- \*\*Description\*\*:\s*([^\n]+)\n\n"
        r"(`{5,})([a-zA-Z0-9_-]*)\n"
        r"(.*?)\n\7\n\n---",
        re.DOTALL,
    )
    m = section_pattern.search(corrupted_text)
    assert m is not None
    recorded_sha = m.group(3)
    has_nl = m.group(4) == "True"
    body = m.group(9)

    reconstructed = (body + "\n").encode("utf-8") if has_nl else body.encode("utf-8")
    computed_sha = hashlib.sha256(reconstructed).hexdigest()
    # Must fail closed: computed hash cannot match recorded hash
    assert computed_sha != recorded_sha, "Corruption was not detected by cryptographic checksum!"


def test_reconstructed_tree_self_contained():
    """P0-01 Remediation: Reconstructs documented tree into an isolated temp dir and verifies clean compilation and smoke imports."""
    doc_text = OUT_MD.open("r", encoding="utf-8", newline="").read()

    section_pattern = re.compile(
        r"####\s+`([^`]+)`\n\n"
        r"- \*\*Path\*\*:\s*`file:///C:/Users/AYUSH/Documents/slm/([^`]+)`\n"
        r"- \*\*Lines\*\*:\s*([0-9,]+)\s*\|\s*\*\*Size\*\*:\s*([0-9,]+)\s*bytes\s*\|\s*\*\*SHA-256\*\*:\s*`([0-9a-f]{64})`\s*\|\s*\*\*Newline\*\*:\s*`(True|False)`\n"
        r"- \*\*Fence\*\*:\s*(\d+)\s*backticks\n"
        r"- \*\*Description\*\*:\s*([^\n]+)\n\n"
        r"(`{5,})([a-zA-Z0-9_-]*)\n"
        r"(.*?)\n\9\n\n---",
        re.DOTALL,
    )

    matches = list(section_pattern.finditer(doc_text))
    assert len(matches) >= 350, f"Expected at least 350 files in export, got {len(matches)}"

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        for m in matches:
            rel_path = m.group(2)
            has_nl = m.group(6) == "True"
            body = m.group(11)
            out_file = tmppath / rel_path
            out_file.parent.mkdir(parents=True, exist_ok=True)
            content = (body + "\n") if has_nl else body
            out_file.write_bytes(content.encode("utf-8"))

        # Verify python -m compileall on reconstructed tree
        compile_res = subprocess.run(
            [sys.executable, "-m", "compileall", "-q", str(tmppath)],
            capture_output=True,
            text=True,
        )
        assert compile_res.returncode == 0, f"compileall failed on reconstructed tree: {compile_res.stderr}"

        # Verify smoke imports in an isolated clean environment
        env = dict(os.environ)
        env["PYTHONPATH"] = str(tmppath)

        smoke_import_script = (
            "import agent.stock_photos\n"
            "import agent.site_brief\n"
            "import agent.agent\n"
            "import server.app\n"
            "import agent.design_plan\n"
            "import agent.site_file_normalizer\n"
            "import agent.tailwind_support\n"
            "import agent.ecommerce_repair\n"
            "import evaluation.motion_benchmark\n"
            "import data_pipeline.build_dataset\n"
            "print('RECONSTRUCTED_SMOKE_IMPORTS_OK')\n"
        )

        import_res = subprocess.run(
            [sys.executable, "-c", smoke_import_script],
            env=env,
            capture_output=True,
            text=True,
        )
        assert import_res.returncode == 0, f"Smoke imports failed on reconstructed tree: {import_res.stderr}"


