"""Quick integration test for the compile-test pipeline.
Run once to verify npm+tsc work correctly in a subprocess context.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

NPM = r"C:\Program Files\nodejs\npm.cmd"
TSC = r"C:\Users\AYUSH\AppData\Roaming\npm\tsc.cmd"

TSCONFIG = {
    "compilerOptions": {
        "target": "ES2020",
        "module": "CommonJS",
        "jsx": "react-jsx",
        "strict": True,
        "noEmit": True,
        "skipLibCheck": True,
        "lib": ["ES2020", "DOM", "DOM.Iterable"],
    },
    "include": ["**/*.tsx", "**/*.ts"],
    "exclude": ["node_modules"],
}

PKG = {
    "name": "slm-compile-test",
    "private": True,
    "devDependencies": {
        "@types/react": "^18.0.0",
        "@types/react-dom": "^18.0.0",
        "typescript": "*",
    },
}

GOOD_TSX = """import React from 'react';

interface Props { name: string; }

export const Hello = ({ name }: Props) => (
  <div className="hello">Hello, {name}!</div>
);
"""

BAD_TSX = """import React from 'react';

// deliberate type error: boolean assigned to string
const x: string = true;
export const Bad = () => <div>{x}</div>;
"""


def main():
    with tempfile.TemporaryDirectory(prefix="slm_ci_") as tmpdir:
        d = Path(tmpdir)
        (d / "package.json").write_text(json.dumps(PKG), encoding="utf-8")
        (d / "tsconfig.json").write_text(json.dumps(TSCONFIG), encoding="utf-8")

        print("Installing type declarations...")
        r = subprocess.run(
            [NPM, "install", "--prefer-offline", "--no-audit", "--silent"],
            cwd=d, capture_output=True, timeout=180,
        )
        if r.returncode != 0:
            print(f"FAIL: npm install failed (code {r.returncode})")
            print(r.stderr.decode()[:500])
            sys.exit(1)
        print("  npm install: OK")

        # Test 1: good file should pass
        (d / "Good.tsx").write_text(GOOD_TSX, encoding="utf-8")
        r1 = subprocess.run(
            [TSC, "--noEmit", "--project", str(d / "tsconfig.json")],
            cwd=d, capture_output=True, text=True, timeout=30,
        )
        if r1.returncode != 0:
            print(f"FAIL: good file produced tsc errors:\n{r1.stdout[:400]}")
            sys.exit(1)
        print("  Test 1 (good file): PASS (exit 0)")

        # Test 2: bad file should fail
        (d / "Bad.tsx").write_text(BAD_TSX, encoding="utf-8")
        r2 = subprocess.run(
            [TSC, "--noEmit", "--project", str(d / "tsconfig.json")],
            cwd=d, capture_output=True, text=True, timeout=30,
        )
        if r2.returncode == 0:
            print("FAIL: bad file should have produced tsc errors but didn't")
            sys.exit(1)
        has_ts2322 = "TS2322" in r2.stdout
        print(f"  Test 2 (bad file): PASS (exit {r2.returncode}, TS2322={'yes' if has_ts2322 else 'no — got: '+r2.stdout[:80]})")

    print("\nAll integration tests passed. npm+tsc subprocess pipeline is functional.")
    print(f"NPM: {NPM}")
    print(f"TSC: {TSC}")


if __name__ == "__main__":
    main()
