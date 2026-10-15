#!/usr/bin/env python3
"""
scripts/sync_source_catalog.py - Synchronizes docs/source.md with canonical relative paths and disk stats.
"""

import re
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
SOURCE_MD = ROOT_DIR / "docs" / "source.md"

pattern = re.compile(
    r"^\|\s*`([^`]+)`\s*\|\s*([^|]+)\|\s*([^|]+)\|\s*([^|]+)\|\s*\[([^\]]+)\]\(([^)]+)\)\s*\|"
)

lines = []
catalog_paths = set()
updated_count = 0

with open(SOURCE_MD, "r", encoding="utf-8") as f:
    for line in f:
        m = pattern.match(line.strip())
        if m:
            name = m.group(1).strip()
            lines_val = m.group(2).strip()
            size_val = m.group(3).strip()
            desc = m.group(4).strip()
            link_text = m.group(5).strip()
            link = m.group(6).strip()

            norm_link = re.sub(r"^file:///[A-Za-z]:/Users/AYUSH/Documents/slm/", "", link, flags=re.IGNORECASE)
            disk_p = ROOT_DIR / norm_link
            if disk_p.exists() and disk_p.is_file():
                raw_bytes = disk_p.read_bytes()
                actual_size = f"{len(raw_bytes):,}"
                actual_lines = f"{len(raw_bytes.decode('utf-8', errors='replace').splitlines()):,}"
                canon_name = norm_link
                canon_link_text = Path(norm_link).name
                new_line = f"| `{canon_name}` | {actual_lines} | {actual_size} | {desc} | [{canon_link_text}]({link}) |\n"
                lines.append(new_line)
                catalog_paths.add(canon_name)
                updated_count += 1
            else:
                lines.append(line)
                catalog_paths.add(name)
        else:
            lines.append(line)

# Check if tests/test_import_smoke.py is present
smoke_rel = "tests/test_import_smoke.py"
if smoke_rel not in catalog_paths:
    smoke_path = ROOT_DIR / smoke_rel
    if smoke_path.exists():
        raw_bytes = smoke_path.read_bytes()
        actual_size = f"{len(raw_bytes):,}"
        actual_lines = f"{len(raw_bytes.decode('utf-8', errors='replace').splitlines()):,}"
        smoke_line = (
            f"| `{smoke_rel}` | {actual_lines} | {actual_size} | "
            f"Automated smoke import test suite verifying clean pipeline imports and self-containment (P0-01). | "
            f"[{smoke_path.name}](file:///C:/Users/AYUSH/Documents/slm/{smoke_rel}) |\n"
        )
        # Insert before package.json or at end
        pkg_idx = None
        for i, l in enumerate(lines):
            if "`package.json`" in l:
                pkg_idx = i
                break
        if pkg_idx is not None:
            lines.insert(pkg_idx, smoke_line)
        else:
            lines.append(smoke_line)
        print(f"Added {smoke_rel} to catalog.")

with open(SOURCE_MD, "w", encoding="utf-8", newline="\n") as f:
    f.writelines(lines)

print(f"Successfully synchronized {SOURCE_MD.name}: {updated_count} entries updated.")
