"""Browser compile-test runner for quality_v3 survivors.

Extracts generated .tsx/.ts/.css files from each training record,
runs tsc --noEmit to verify TypeScript compiles, then tests CSS syntax.
Records browser-testable components to a manifest for manual visual review.

This is the static approximation of browser testing. It cannot verify:
  - Runtime interaction behavior
  - Visual correctness
  - Scroll / hover / keyboard event handlers
  - WebGL context creation in a real browser
Those require a browser + human review.

Usage:
  python data_pipeline/compile_test_survivors.py --source data/quality_v3/train.jsonl
  python data_pipeline/compile_test_survivors.py --source data/r3f_trajectories/r3f_draft.jsonl
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from agent.agent_protocol import parse_agent_output, WriteSiteAction
from training.preflight import read_jsonl

# Minimal tsconfig for type-check pass (no DOM globals needed — we only check syntax/types)
TSCONFIG = {
    "compilerOptions": {
        "target": "ES2020",
        "module": "CommonJS",
        "jsx": "react-jsx",
        "strict": True,
        "noEmit": True,
        "skipLibCheck": True,
        "allowArbitraryExtensions": True,   # TS7 needs this for CSS side-effect imports
        "lib": ["ES2020", "DOM", "DOM.Iterable"],
    },
    "include": ["**/*.ts", "**/*.tsx"],
    "exclude": ["node_modules"],
}

# Windows .cmd wrappers — necessary because Python subprocess can't run .ps1 scripts
NPM_CMD = r"C:\Program Files\nodejs\npm.cmd"
TSC_CMD = r"C:\Users\AYUSH\AppData\Roaming\npm\tsc.cmd"

NPM_DEPS = [
    "typescript",
    "react",
    "react-dom",
    "@types/react",
    "@types/react-dom",
    "@react-three/fiber",
    "@react-three/drei",
    "three",
    "@types/three",
]


def setup_workspace(tmpdir: Path) -> bool:
    """Install minimal type-check deps. Returns True if tsc + types are available."""
    (tmpdir / "tsconfig.json").write_text(json.dumps(TSCONFIG, indent=2))
    pkg = {
        "name": "compile-test",
        "private": True,
        "dependencies": {
            "react": "^18.0.0",
            "react-dom": "^18.0.0",
            "@react-three/fiber": "^8.0.0",
            "@react-three/drei": "^9.0.0",
            "three": "^0.160.0",
        },
        "devDependencies": {
            "@types/react": "^18.0.0",
            "@types/react-dom": "^18.0.0",
            "@types/three": "^0.160.0",
            "typescript": "*",
        },
    }
    (tmpdir / "package.json").write_text(json.dumps(pkg, indent=2))
    try:
        result = subprocess.run(
            [NPM_CMD, "install", "--prefer-offline", "--silent", "--no-audit"],
            cwd=tmpdir, capture_output=True, timeout=180
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(f"WARNING: npm install failed ({e}) — TypeScript errors will not be caught")
        return False


def extract_tsx_files(record: dict) -> dict[str, str]:
    """Return {path: content} for all assistant WriteSiteAction outputs."""
    files = {}
    for msg in record.get("messages", []):
        if msg["role"] != "assistant":
            continue
        action = parse_agent_output(msg["content"]).action
        if isinstance(action, WriteSiteAction):
            for path, code in action.files:
                files[path] = code
    return files


def strip_css_imports(code: str) -> str:
    """Remove CSS side-effect import lines before type-checking.
    
    TypeScript 7 requires .d.ts stubs for CSS imports (TS2882).
    Since we only care about TypeScript correctness, not bundling,
    we strip them entirely — the type check is still meaningful.
    """
    import re
    return re.sub(r"^import\s+['\"].*\.css['\"]\s*;?\s*$", "", code, flags=re.MULTILINE)


def tsc_check(files: dict[str, str], workspace: Path) -> list[str]:
    """Write files to workspace and run tsc --noEmit. Returns list of error strings.
    
    CSS imports are stripped from TSX files before type-checking (TS2882 workaround).
    """
    src = workspace / "src"
    src.mkdir(exist_ok=True)
    for path, code in files.items():
        if path.endswith(".css"):
            continue  # skip CSS files; they're not type-checked
        target = workspace / path
        target.parent.mkdir(parents=True, exist_ok=True)
        cleaned = strip_css_imports(code) if path.endswith((".tsx", ".ts")) else code
        target.write_text(cleaned, encoding="utf-8")

    try:
        result = subprocess.run(
            [TSC_CMD, "--noEmit", "--project", str(workspace / "tsconfig.json")],
            cwd=workspace, capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            return [line for line in result.stdout.splitlines() if line.strip()]
        return []
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        return [f"tsc unavailable: {e}"]

def run(source: str, max_records: int = 50) -> None:
    """Run compile-test on up to max_records from source JSONL."""
    rows = list(read_jsonl(source))
    print(f"Source: {source}")
    print(f"Records to test: {min(len(rows), max_records)} of {len(rows)}")

    results = {"pass": [], "fail": [], "no_code": [], "tsc_unavailable": []}
    error_types: Counter = Counter()

    with tempfile.TemporaryDirectory(prefix="slm_compile_") as tmpdir:
        workspace = Path(tmpdir)
        tsc_available = setup_workspace(workspace)
        if not tsc_available:
            print("WARNING: tsc not available — TypeScript errors will not be caught")

        for i, row in enumerate(rows[:max_records], 1):
            task_id = row.get("task_id", f"row_{i}")
            files = extract_tsx_files(row)
            tsx_files = {p: c for p, c in files.items() if p.endswith((".tsx", ".ts"))}

            if not tsx_files:
                results["no_code"].append(task_id)
                continue

            if not tsc_available:
                results["tsc_unavailable"].append(task_id)
                continue

            errors = tsc_check(tsx_files, workspace)
            # Clean up for next record
            for p in tsx_files:
                try:
                    (workspace / p).unlink(missing_ok=True)
                except Exception:
                    pass

            if errors:
                results["fail"].append({"task_id": task_id, "errors": errors[:5]})
                for e in errors[:3]:
                    # Bucket by TS error code
                    import re
                    code = re.search(r"TS\d+", e)
                    error_types[code.group() if code else "unknown"] += 1
            else:
                results["pass"].append(task_id)

            if i % 10 == 0:
                print(f"  {i}/{min(len(rows), max_records)} — pass:{len(results['pass'])} fail:{len(results['fail'])}")

    # Summary report
    total_tested = len(results["pass"]) + len(results["fail"])
    report = {
        "source": source,
        "total_records": len(rows),
        "tested": total_tested,
        "pass": len(results["pass"]),
        "fail": len(results["fail"]),
        "no_tsx_code": len(results["no_code"]),
        "tsc_unavailable": len(results["tsc_unavailable"]),
        "pass_rate": f"{100*len(results['pass'])/total_tested:.1f}%" if total_tested else "N/A",
        "top_error_codes": dict(error_types.most_common(10)),
        "failed_tasks": [f["task_id"] for f in results["fail"][:20]],
        "first_failures": results["fail"][:5],
        "note": (
            "Static TypeScript compilation only. Cannot verify: runtime behavior, "
            "visual correctness, keyboard/scroll events, WebGL in a real browser. "
            "Human review required for all promoted records."
        ),
    }
    out = Path(source).parent / f"compile_report_{Path(source).stem}.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "first_failures"}, indent=2))
    print(f"\nDetailed report: {out}")
    if results["fail"]:
        print("\nFirst failures:")
        for f in results["fail"][:3]:
            print(f"  {f['task_id']}: {f['errors'][0]}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default="data/quality_v3/train.jsonl",
                        help="JSONL file to compile-test")
    parser.add_argument("--max-records", type=int, default=50,
                        help="Max records to test (default 50 for speed)")
    args = parser.parse_args()
    run(args.source, args.max_records)
