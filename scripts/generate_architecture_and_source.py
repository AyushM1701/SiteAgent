#!/usr/bin/env python3
"""
scripts/generate_architecture_and_source.py - Corruption-Proof Architecture & Source Exporter.

Generates docs/architecture_and_source.md with:
1. Dynamic fence length sizing: max(5, max_backticks + 1) to eliminate fence contamination.
2. Cryptographic SHA-256 checksums embedded next to each file section.
3. Automated round-trip extraction and verification against original file bytes.
4. Fail-closed execution: Exits with code 1 if round-trip reconstruction is not 100% byte-exact.
"""

import hashlib
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ROOT_DIR = Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT_DIR / "docs"
ARCH_MD = DOCS_DIR / "architecture.md"
SOURCE_MD = DOCS_DIR / "source.md"
OUT_MD = DOCS_DIR / "architecture_and_source.md"

LANG_MAP = {
    ".py": "python",
    ".ts": "tsx",
    ".tsx": "tsx",
    ".js": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".json": "json",
    ".jsonl": "json",
    ".html": "html",
    ".css": "css",
    ".md": "markdown",
    ".sh": "bash",
    ".bat": "bat",
    ".yml": "yaml",
    ".yaml": "yaml",
    ".toml": "toml",
    ".txt": "text",
}


def get_language(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    return LANG_MAP.get(ext, "text")


def compute_fence(text: str) -> Tuple[str, int]:
    """Finds max run of backticks and chooses a strictly longer fence of at least 5 backticks."""
    matches = [len(m.group(0)) for m in re.finditer(r"`+", text)]
    max_bt = max(matches) if matches else 0
    fence_len = max(5, max_bt + 1)
    return "`" * fence_len, fence_len


def parse_source_catalog(source_md_path: Path) -> List[Dict[str, str]]:
    """Parses module entries from docs/source.md table."""
    pattern = re.compile(
        r"^\|\s*`([^`]+)`\s*\|\s*([^|]+)\|\s*([^|]+)\|\s*([^|]+)\|\s*\[([^\]]+)\]\(([^)]+)\)\s*\|"
    )
    entries = []
    if not source_md_path.exists():
        return entries

    with open(source_md_path, "r", encoding="utf-8") as f:
        for line in f:
            m = pattern.match(line.strip())
            if m:
                entries.append({
                    "name": m.group(1).strip(),
                    "lines": m.group(2).strip(),
                    "size": m.group(3).strip(),
                    "description": m.group(4).strip(),
                    "link": m.group(6).strip(),
                })
    return entries


def extract_sections_from_existing_doc(existing_doc_path: Path) -> Dict[str, Dict[str, str]]:
    """Extracts existing embedded files from existing architecture_and_source.md as historical fallback."""
    sections = {}
    if not existing_doc_path.exists():
        return sections

    content = existing_doc_path.read_text(encoding="utf-8", errors="replace")
    header_pattern = re.compile(
        r"####\s+`([^`]+)`\r?\n\r?\n"
        r"- \*\*Path\*\*:\s*`([^`]+)`\r?\n"
        r"- \*\*Lines\*\*:\s*([^\r\n]+)\r?\n"
        r"(?:- \*\*Fence\*\*:\s*[^\r\n]+\r?\n)?"
        r"- \*\*Description\*\*:\s*([^\r\n]+)\r?\n\r?\n"
        r"(`{4,})([a-zA-Z0-9_-]*)\r?\n"
        r"(.*?)\r?\n\5(?:\r?\n\r?\n---|\Z)",
        re.DOTALL,
    )

    for m in header_pattern.finditer(content):
        rel_name = m.group(1).strip()
        path_link = m.group(2).strip()
        desc = m.group(4).strip()
        body = m.group(7)
        sections[rel_name] = {
            "path_link": path_link,
            "description": desc,
            "content": body,
        }
    return sections


def generate_architecture_and_source():
    print("[SourceExport] Starting corruption-proof documentation export...")

    # Optional hand-written preamble; the README is the project overview.
    arch_text = ARCH_MD.read_text(encoding="utf-8") if ARCH_MD.exists() else (
        "# SiteAgent - complete source export\n\n"
        "Every source file of the repository, verbatim, with size and SHA-256 metadata. "
        "See README.md for an overview; `scripts/reconstruct_export.py` rebuilds the tree from this file."
    )
    # Take architecture content up to directory tree end / separator
    if "## 3. Complete Source Code of Every File" in arch_text:
        arch_section = arch_text.split("## 3. Complete Source Code of Every File")[0].strip()
    elif "> [!NOTE]\n> For the exhaustive verbatim source code" in arch_text:
        arch_section = arch_text.split("> [!NOTE]\n> For the exhaustive verbatim source code")[0].strip()
    else:
        arch_section = arch_text.strip()

    catalog = parse_source_catalog(SOURCE_MD)
    print(f"[SourceExport] Loaded {len(catalog)} catalog entries from {SOURCE_MD.name}")

    historical_sections = extract_sections_from_existing_doc(OUT_MD)
    print(f"[SourceExport] Loaded {len(historical_sections)} fallback sections from existing export")

    embedded_blocks: List[str] = []
    processed_count = 0
    disk_verified_count = 0

    for item in catalog:
        rel_path = item["name"]
        desc = item["description"]
        link = item["link"]

        # Resolve path on disk
        disk_path = ROOT_DIR / rel_path
        if not disk_path.exists():
            # Try path from link: file:///C:/Users/AYUSH/Documents/slm/...
            norm_link = re.sub(r"^file:///[A-Za-z]:/Users/AYUSH/Documents/slm/", "", link, flags=re.IGNORECASE)
            if (ROOT_DIR / norm_link).exists():
                disk_path = ROOT_DIR / norm_link

        if disk_path.exists() and disk_path.is_file():
            # Canonical LF content: git checks text out as CRLF on Windows and LF elsewhere,
            # so the export (and its SHA-256 metadata) must not depend on the OS it ran on.
            raw_bytes = disk_path.read_bytes().replace(b"\r\n", b"\n")
            text_content = raw_bytes.decode("utf-8", errors="replace")
            sha256_hex = hashlib.sha256(raw_bytes).hexdigest()
            byte_size = len(raw_bytes)
            line_count = len(text_content.splitlines())
            has_trailing_nl = text_content.endswith("\n")
            is_from_disk = True
            norm_rel_path = disk_path.relative_to(ROOT_DIR).as_posix()
        elif rel_path in historical_sections:
            hist = historical_sections[rel_path]
            text_content = hist["content"]
            raw_bytes = text_content.encode("utf-8")
            sha256_hex = hashlib.sha256(raw_bytes).hexdigest()
            byte_size = len(raw_bytes)
            line_count = len(text_content.splitlines())
            has_trailing_nl = text_content.endswith("\n")
            is_from_disk = False
            norm_rel_path = rel_path
        else:
            print(f"[SourceExport] WARNING: Skipping missing file {rel_path}")
            continue

        lang = get_language(norm_rel_path)
        fence, fence_len = compute_fence(text_content)

        # Ensure newline separation before closing fence
        body_with_nl = text_content if text_content.endswith("\n") else (text_content + "\n")

        block = (
            f"#### `{norm_rel_path}`\n\n"
            f"- **Path**: `file:///C:/Users/AYUSH/Documents/slm/{norm_rel_path}`\n"
            f"- **Lines**: {line_count:,} | **Size**: {byte_size:,} bytes | **SHA-256**: `{sha256_hex}` | **Newline**: `{has_trailing_nl}`\n"
            f"- **Fence**: {fence_len} backticks\n"
            f"- **Description**: {desc}\n\n"
            f"{fence}{lang}\n"
            f"{body_with_nl}"
            f"{fence}\n\n"
            f"---\n"
        )
        embedded_blocks.append(block)
        processed_count += 1
        if is_from_disk:
            disk_verified_count += 1

    print(f"[SourceExport] Assembled {processed_count} files ({disk_verified_count} directly from active disk)")

    # Construct final document
    header_section = (
        arch_section.rstrip()
        + "\n\n---\n\n"
        + "## 3. Complete Source Code of Every File\n\n"
        + "Every line of source code across all project files is provided below verbatim without truncation.\n"
        + "All embedded source blocks are protected with dynamic-length fences exceeding any backtick sequence inside the source.\n"
        + "Each section records an authoritative SHA-256 checksum validated via automated round-trip extraction.\n\n"
        + "---\n\n"
    )

    full_document = header_section + "\n".join(embedded_blocks)

    # ── Strict Round-Trip Validation ──────────────────────────────────────────
    print("[SourceExport] Executing strict round-trip extraction and SHA-256 validation...")
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

    matches = list(section_pattern.finditer(full_document))
    if len(matches) != processed_count:
        print(f"[SourceExport] ERROR: Extraction count mismatch! Expected {processed_count}, extracted {len(matches)}", file=sys.stderr)
        sys.exit(1)

    for m in matches:
        file_name = m.group(1)
        rel_disk_path = m.group(2)
        expected_size = int(m.group(4).replace(",", ""))
        expected_sha = m.group(5)
        has_nl = m.group(6) == "True"
        fence_len = int(m.group(7))
        description = m.group(8)
        extracted_fence = m.group(9)
        lang = m.group(10)
        body = m.group(11)

        if len(extracted_fence) != fence_len:
            print(f"[SourceExport] ERROR: Fence length mismatch for {file_name}: expected {fence_len}, got {len(extracted_fence)}", file=sys.stderr)
            sys.exit(1)

        # Reconstruct exact source text
        reconstructed_text = (body + "\n") if has_nl else body
        reconstructed_bytes = reconstructed_text.encode("utf-8")
        computed_sha = hashlib.sha256(reconstructed_bytes).hexdigest()

        if computed_sha != expected_sha:
            print(f"[SourceExport] ERROR: SHA-256 mismatch for {file_name}!", file=sys.stderr)
            print(f"  Expected: {expected_sha}", file=sys.stderr)
            print(f"  Computed: {computed_sha}", file=sys.stderr)
            sys.exit(1)

        if len(reconstructed_bytes) != expected_size:
            print(f"[SourceExport] ERROR: Byte size mismatch for {file_name} (expected {expected_size}, got {len(reconstructed_bytes)})", file=sys.stderr)
            sys.exit(1)

        # If file exists on disk, assert 100% byte equality with file on disk
        target_file = ROOT_DIR / rel_disk_path
        if target_file.exists() and target_file.is_file():
            actual_disk_bytes = target_file.read_bytes().replace(b"\r\n", b"\n")
            if reconstructed_bytes != actual_disk_bytes:
                print(f"[SourceExport] ERROR: Reconstructed bytes differ from disk for {rel_disk_path}!", file=sys.stderr)
                sys.exit(1)

    print(f"[SourceExport] [OK] 100% of {len(matches)} files passed round-trip reconstruction and SHA-256 verification!")

    # Verify server/app.py specifically
    app_matches = [m for m in matches if "server/app.py" in m.group(2) or m.group(1) == "server/app.py" or m.group(1) == "app.py"]
    if not app_matches:
        print("[SourceExport] ERROR: server/app.py section was not found in export!", file=sys.stderr)
        sys.exit(1)

    app_disk_bytes = (ROOT_DIR / "server" / "app.py").read_bytes().replace(b"\r\n", b"\n")
    app_extracted = (app_matches[0].group(11) + "\n").encode("utf-8")
    if app_extracted != app_disk_bytes:
        print("[SourceExport] ERROR: server/app.py extracted bytes do not match server/app.py on disk!", file=sys.stderr)
        sys.exit(1)
    print(f"[SourceExport] [OK] server/app.py verified uncontaminated and byte-exact ({len(app_disk_bytes):,} bytes)")

    # Atomic write to disk preserving exact raw newlines
    tmp_out = OUT_MD.with_suffix(".tmp")
    with open(tmp_out, "w", encoding="utf-8", newline="") as f:
        f.write(full_document)

    if OUT_MD.exists():
        OUT_MD.unlink()
    tmp_out.rename(OUT_MD)

    total_lines = len(full_document.splitlines())
    total_bytes = len(full_document.encode("utf-8"))
    print(f"[SourceExport] Successfully generated {OUT_MD.name} ({total_lines:,} lines, {total_bytes:,} bytes)")


if __name__ == "__main__":
    generate_architecture_and_source()
