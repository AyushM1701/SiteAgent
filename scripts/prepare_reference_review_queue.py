"""Index original full-site references for human review without assigning scores."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
CAPTURES = ROOT / "runs/reviewed_source_candidates"
SITES = {
    "margin": ("editorial_workspace", "editorial", "Original fictional writing workspace"),
    "fieldwork": ("analytics_platform", "dashboard", "Original fictional analytics platform"),
    "parallax": ("dimensional_consultancy", "agency", "Original fictional design consultancy"),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    typecheck = subprocess.run(
        ["node", str(ROOT / "node_modules/typescript/bin/tsc"), "--noEmit", "--jsx", "react-jsx", "--moduleResolution", "bundler",
         "--module", "esnext", "--target", "es2020", "--lib", "DOM,ES2020",
         "--allowSyntheticDefaultImports", "--skipLibCheck",
         *[str(ROOT / "examples/reference-curriculum" / name / "main.tsx") for name in SITES]],
        cwd=ROOT, capture_output=True, text=True,
    )
    if typecheck.returncode:
        raise RuntimeError("Reference sites failed TypeScript: " + typecheck.stdout + typecheck.stderr)
    from data_pipeline.build_reference_curriculum import source_hash
    queue = []
    for name, (family, domain, description) in SITES.items():
        source = ROOT / "data/premium_reference/source" / name
        preview = ROOT / "examples/reference-curriculum" / name
        evidence_file = CAPTURES / name / "evidence.json"
        verification_file = ROOT / "data/premium_reference/verification" / f"{name}.json"
        evidence = json.loads(evidence_file.read_text(encoding="utf-8"))
        verification = json.loads(verification_file.read_text(encoding="utf-8"))
        if not verification.get("passed"):
            raise ValueError(f"Prior interaction verification failed for {name}")
        if verification.get("source_sha256") != source_hash(name):
            raise ValueError(f"Interaction verification is stale for {name}")
        if any(capture.get("browser_errors") for capture in evidence["captures"].values()):
            raise ValueError(f"Browser capture has errors for {name}")
        if not (CAPTURES / name / "dist/index.html").is_file():
            raise ValueError(f"Production build is missing for {name}")
        queue.append({
            "site_id": name, "family_id": f"reference_{family}", "domain": domain,
            "description": description, "source": str(source.relative_to(ROOT)),
            "source_files": {p.relative_to(source).as_posix(): sha256(p) for p in source.rglob("*") if p.is_file()},
            "license": "MIT (repository LICENSE)",
            "preview": str(preview.relative_to(ROOT)),
            "validation": {
                "typecheck": True, "production_build": True, "browser_console_errors": 0,
                "interaction_verification": str(verification_file.relative_to(ROOT)),
                "interaction_verification_date": verification.get("checked_on"),
            },
            "browser_evidence": evidence["captures"],
            "human_visual_review": None,
            "admission_status": "awaiting_independent_human_review",
        })
    output = CAPTURES / "queue.json"
    output.write_text(json.dumps(queue, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"review_queue": str(output), "sites": len(queue), "admitted_training_sites": 0}, indent=2))


if __name__ == "__main__":
    main()
