#!/usr/bin/env python3
"""Rebuild the source tree from docs/architecture_and_source.md into a clean directory.

Used by .github/workflows/verify_reconstructed_export.yml to prove the export is
self-contained:  python scripts/reconstruct_export.py clean_reconstructed_tree
"""
import re
import sys
from pathlib import Path

SECTION = re.compile(
    r'####\s+`([^`]+)`\n\n'
    r'- \*\*Path\*\*:\s*`file:///[^`]*?/slm/([^`]+)`\n'
    r'- \*\*Lines\*\*:\s*([0-9,]+)\s*\|\s*\*\*Size\*\*:\s*([0-9,]+)\s*bytes\s*\|\s*\*\*SHA-256\*\*:\s*`([0-9a-f]{64})`\s*\|\s*\*\*Newline\*\*:\s*`(True|False)`\n'
    r'- \*\*Fence\*\*:\s*(\d+)\s*backticks\n'
    r'- \*\*Description\*\*:\s*([^\n]+)\n\n'
    r'(`{5,})([a-zA-Z0-9_-]*)\n'
    r'(.*?)\n\9\n\n---',
    re.DOTALL,
)


def main() -> None:
    dest = Path(sys.argv[1] if len(sys.argv) > 1 else "clean_reconstructed_tree")
    text = Path("docs/architecture_and_source.md").read_text(encoding="utf-8")
    matches = list(SECTION.finditer(text))
    print(f"Extracting {len(matches)} files from docs/architecture_and_source.md ...")
    if len(matches) < 350:
        sys.exit(f"Expected at least 350 files, found {len(matches)}")
    for m in matches:
        out = dest / m.group(2)
        out.parent.mkdir(parents=True, exist_ok=True)
        body = m.group(11)
        out.write_bytes(((body + "\n") if m.group(6) == "True" else body).encode("utf-8"))
    print(f"Reconstructed {len(matches)} files into {dest}.")


if __name__ == "__main__":
    main()
