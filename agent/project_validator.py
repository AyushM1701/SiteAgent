"""
agent/project_validator.py - Authoritative Project Validation Engine

Implements the multi-stage project verification sequence specified by the blueprint:
1. Quick Gate: Static token and syntax linting
2. Full Workspace Typecheck: `npm run typecheck` (tsc --noEmit -p tsconfig.json)
3. Production Bundler Check: `npm run build` (vite build)
4. Vite Preview Server: verifies live preview serving on 127.0.0.1
5. Browser Runtime Check: Playwright headless Chromium monitoring unhandled pageerror,
   console.error, and #root DOM mount verification.
"""

import dataclasses
import json
import os
import re
import shutil
import socket
import signal
import subprocess
import time
import urllib.request
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
try:
    from agent.evidence_validation import GateEvidence, ProjectValidation
except ImportError:
    from evidence_validation import GateEvidence, ProjectValidation

BASE_DIR = Path(__file__).resolve().parent.parent


@dataclasses.dataclass
class InteractionEvidence:
    """Explicit behavioral evidence for a required or exercised DOM interaction."""
    requirement_id: str
    locator: str
    initial_state: Any
    action: str
    expected_state: Any
    observed_state: Any
    passed: bool
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "requirement_id": self.requirement_id,
            "locator": self.locator,
            "initial_state": self.initial_state,
            "action": self.action,
            "expected_state": self.expected_state,
            "observed_state": self.observed_state,
            "passed": self.passed,
            "error": self.error,
        }
        return result


@dataclasses.dataclass
class InteractionValidationResult:
    """Structured outcome of interactive DOM interaction testing (Gate 4b)."""
    passed: bool = False
    status: str = "not_requested"
    errors: list = dataclasses.field(default_factory=list)
    interactions_tested: int = 0
    interactions_required: int = 0
    interaction_evidence: list = dataclasses.field(default_factory=list)

    def to_dict(self) -> dict:
        result = {
            "passed": self.passed,
            "status": self.status,
            "errors": self.errors,
            "interactions_tested": self.interactions_tested,
            "interactions_required": self.interactions_required,
            "interaction_evidence": [e.to_dict() if hasattr(e, "to_dict") else e for e in self.interaction_evidence],
        }
        return result


@dataclasses.dataclass
class VisualValidationResult:
    """Structured outcome of visual rendering & screenshot heuristic scoring."""
    passed: bool = False
    status: str = "failed"
    score: Optional[float] = None
    issues: list = dataclasses.field(default_factory=list)
    screenshot_path: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "status": self.status,
            "score": self.score,
            "issues": self.issues,
            "screenshot_path": self.screenshot_path,
        }


@dataclasses.dataclass
class ValidationResult:
    """Structured outcome of full project verification across authoritative 7 gates (typecheck, build, lint, contract, accessibility, motion, runtime/preview/interaction)."""
    typecheck_passed: bool = False
    build_passed: bool = False
    lint_passed: bool = False
    contract_passed: bool = False
    accessibility_passed: bool = False
    motion_passed: bool = True
    three_d_passed: bool = True
    three_d_status: str = "not_requested"
    three_d_static_status: str = "not_requested"
    three_d_runtime_status: str = "not_requested"
    runtime_passed: bool = False
    preview_running: bool = False
    interaction_passed: bool = True
    errors: list = dataclasses.field(default_factory=list)
    warnings: list = dataclasses.field(default_factory=list)
    repair_attempts: int = 0
    runtime_unverified: bool = False
    interactions_tested: int = 0
    interactions_required: int = 0
    interaction_evidence: list = dataclasses.field(default_factory=list)
    interaction_errors: list = dataclasses.field(default_factory=list)
    typecheck_status: str = "failed"
    build_status: str = "failed"
    lint_status: str = "failed"
    contract_status: str = "failed"
    accessibility_status: str = "failed"
    motion_status: str = "passed"
    motion_runtime_status: str = "not_requested"
    runtime_status: str = "failed"
    preview_status: str = "failed"
    interaction_status: str = "not_requested"
    motion_plan: list = dataclasses.field(default_factory=list)
    motion_failures: list = dataclasses.field(default_factory=list)

    def __post_init__(self):
        if self.typecheck_passed and self.typecheck_status == "failed":
            self.typecheck_status = "passed"
        if self.build_passed and self.build_status == "failed":
            self.build_status = "passed"
        if self.lint_passed and self.lint_status == "failed":
            self.lint_status = "passed"
        if self.contract_passed and self.contract_status == "failed":
            self.contract_status = "passed"
        if self.accessibility_passed and self.accessibility_status == "failed":
            self.accessibility_status = "passed"
        if not self.motion_passed and self.motion_status == "passed":
            self.motion_status = "failed"
        if self.runtime_unverified:
            self.runtime_passed = False
            if self.runtime_status != "runtime_unverified":
                self.runtime_status = "unverified"
            self.interaction_passed = False
            if self.interaction_status != "interaction_unverified":
                self.interaction_status = "unverified"
        elif self.runtime_passed and self.runtime_status in ("failed", "unverified"):
            self.runtime_status = "passed"
        if self.preview_running and self.preview_status == "failed":
            self.preview_status = "passed"

        # Interaction Gate Truth States:
        if any("[Interaction Error]" in str(e) for e in self.errors) or self.interaction_errors:
            self.interaction_passed = False
            self.interaction_status = "failed"
        elif self.runtime_unverified:
            self.interaction_passed = False
            self.interaction_status = "unverified"
        elif self.interactions_required > 0:
            passed_count = sum(
                1 for e in self.interaction_evidence
                if (e.passed if hasattr(e, "passed") else (e.get("passed", False) if isinstance(e, dict) else False))
            )
            # Tested >= required AND passed >= required
            if self.interactions_tested >= self.interactions_required and passed_count >= self.interactions_required:
                self.interaction_passed = True
                self.interaction_status = "passed"
            else:
                self.interaction_passed = False
                self.interaction_status = "failed"
        elif self.interaction_status == "not_requested":
            # Explicitly not requested is distinct from a runtime pass. Never
            # infer interaction evidence from browser/runtime success.
            self.interaction_passed = True
        elif self.interaction_passed and self.interaction_status in ("failed", "unverified"):
            self.interaction_status = "passed"
        elif not self.interaction_passed and self.interaction_status == "passed":
            self.interaction_passed = True

    @property
    def typecheckPassed(self) -> bool:
        return self.typecheck_passed

    @property
    def buildPassed(self) -> bool:
        return self.build_passed

    @property
    def lintPassed(self) -> bool:
        return self.lint_passed

    @property
    def contractPassed(self) -> bool:
        return self.contract_passed

    @property
    def accessibilityPassed(self) -> bool:
        return self.accessibility_passed

    @property
    def typecheckStatus(self) -> str:
        return self.typecheck_status

    @property
    def buildStatus(self) -> str:
        return self.build_status

    @property
    def lintStatus(self) -> str:
        return self.lint_status

    @property
    def contractStatus(self) -> str:
        return self.contract_status

    @property
    def accessibilityStatus(self) -> str:
        return self.accessibility_status

    @property
    def motionPassed(self) -> bool:
        return self.motion_passed

    @property
    def motionStatus(self) -> str:
        return self.motion_status

    @property
    def motionPlan(self) -> list:
        return self.motion_plan

    @property
    def motionFailures(self) -> list:
        return self.motion_failures

    @property
    def previewStatus(self) -> str:
        return self.preview_status

    @property
    def runtimePassed(self) -> bool:
        return self.runtime_passed

    @property
    def runtimeUnverified(self) -> bool:
        return self.runtime_unverified

    @property
    def runtimeStatus(self) -> str:
        return self.runtime_status

    @property
    def previewRunning(self) -> bool:
        return self.preview_running

    @property
    def repairAttempts(self) -> int:
        return self.repair_attempts

    @property
    def code_passed(self) -> bool:
        """Compilation and static validation status (lint, typecheck, build, contract, accessibility, motion)."""
        return (
            self.typecheck_passed
            and self.build_passed
            and self.lint_passed
            and self.contract_passed
            and self.accessibility_passed
            and self.motion_passed
            and self.three_d_passed
        )

    @property
    def codePassed(self) -> bool:
        return self.code_passed

    @property
    def interactionPassed(self) -> bool:
        return self.interaction_passed

    @property
    def interactionStatus(self) -> str:
        return self.interaction_status

    @property
    def interactionsRequired(self) -> int:
        return self.interactions_required

    @property
    def interactionEvidence(self) -> list:
        return self.interaction_evidence

    @property
    def interaction_validation(self) -> InteractionValidationResult:
        return InteractionValidationResult(
            passed=self.interaction_passed,
            status=self.interaction_status,
            errors=self.interaction_errors,
            interactions_tested=self.interactions_tested,
            interactions_required=self.interactions_required,
            interaction_evidence=self.interaction_evidence,
        )

    @property
    def visual_validation(self) -> VisualValidationResult:
        v_passed = self.passed and not any("[Visual Error]" in str(e) for e in self.errors)
        return VisualValidationResult(
            passed=v_passed,
            status="passed" if v_passed else "failed",
            score=5.0 if v_passed else 0.0,
            issues=[str(e) for e in self.errors if "[Visual" in str(e)],
        )

    @property
    def passed(self) -> bool:
        """All required gates must pass before declaring success (authoritative 7-gate validation engine)."""
        return (
            self.typecheck_passed
            and self.build_passed
            and self.lint_passed
            and self.contract_passed
            and self.accessibility_passed
            and self.motion_passed
            and self.three_d_passed
            and self.runtime_passed
            and not self.runtime_unverified
            and self.preview_running
            and self.interaction_passed
            and self.typecheck_status == "passed"
            and self.build_status == "passed"
            and self.lint_status == "passed"
            and self.contract_status == "passed"
            and self.accessibility_status == "passed"
            and self.motion_status == "passed"
            and self.runtime_status == "passed"
            and self.preview_status == "passed"
            and self.interaction_status in ("passed", "not_requested")
            and self.three_d_status in ("passed", "not_requested")
        )

    @property
    def all_gates_passed(self) -> bool:
        return self.passed

    def to_dict(self) -> dict:
        return {
            "typecheck_passed": self.typecheck_passed,
            "typecheckPassed": self.typecheck_passed,
            "build_passed": self.build_passed,
            "buildPassed": self.build_passed,
            "lint_passed": self.lint_passed,
            "lintPassed": self.lint_passed,
            "contract_passed": self.contract_passed,
            "contractPassed": self.contract_passed,
            "accessibility_passed": self.accessibility_passed,
            "accessibilityPassed": self.accessibility_passed,
            "runtime_passed": self.runtime_passed,
            "runtimePassed": self.runtime_passed,
            "interaction_passed": self.interaction_passed,
            "interactionPassed": self.interaction_passed,
            "interactions_tested": self.interactions_tested,
            "interactionsTested": self.interactions_tested,
            "interactions_required": self.interactions_required,
            "interactionsRequired": self.interactions_required,
            "interaction_evidence": [e.to_dict() if hasattr(e, "to_dict") else e for e in self.interaction_evidence],
            "interactionEvidence": [e.to_dict() if hasattr(e, "to_dict") else e for e in self.interaction_evidence],
            "interaction_errors": self.interaction_errors,
            "interactionErrors": self.interaction_errors,
            "interaction_status": self.interaction_status,
            "interactionStatus": self.interaction_status,
            "runtime_unverified": self.runtime_unverified,
            "runtimeUnverified": self.runtime_unverified,
            "typecheck_status": self.typecheck_status,
            "typecheckStatus": self.typecheck_status,
            "build_status": self.build_status,
            "buildStatus": self.build_status,
            "lint_status": self.lint_status,
            "lintStatus": self.lint_status,
            "contract_status": self.contract_status,
            "contractStatus": self.contract_status,
            "accessibility_status": self.accessibility_status,
            "accessibilityStatus": self.accessibility_status,
            "motion_passed": self.motion_passed,
            "motionPassed": self.motion_passed,
            "motion_status": self.motion_status,
            "motionStatus": self.motion_status,
            "motion_runtime_status": self.motion_runtime_status,
            "motionRuntimeStatus": self.motion_runtime_status,
            "three_d_passed": self.three_d_passed,
            "threeDPassed": self.three_d_passed,
            "three_d_status": self.three_d_status,
            "threeDStatus": self.three_d_status,
            "three_d_static_status": self.three_d_static_status,
            "threeDStaticStatus": self.three_d_static_status,
            "three_d_runtime_status": self.three_d_runtime_status,
            "threeDRuntimeStatus": self.three_d_runtime_status,
            "motion_plan": self.motion_plan,
            "motionPlan": self.motion_plan,
            "motion_failures": self.motion_failures,
            "motionFailures": self.motion_failures,
            "runtime_status": self.runtime_status,
            "runtimeStatus": self.runtime_status,
            "preview_status": self.preview_status,
            "previewStatus": self.preview_status,
            "preview_running": self.preview_running,
            "previewRunning": self.preview_running,
            "code_passed": self.code_passed,
            "codePassed": self.code_passed,
            "errors": self.errors,
            "warnings": self.warnings,
            "repair_attempts": self.repair_attempts,
            "repairAttempts": self.repair_attempts,
            "passed": self.passed,
            "all_gates_passed": self.passed,
            "allGatesPassed": self.passed,
        }
        result["gates"] = self.to_project_validation().to_dict()
        return result

    def to_project_validation(self) -> ProjectValidation:
        """Canonical evidence view; legacy scalar fields remain compatibility-only."""
        def make(status: str, checks: int = 1, errors: Optional[list] = None) -> GateEvidence:
            normalized = status if status in {"passed", "failed", "unverified", "not_requested"} else "failed"
            return GateEvidence(status=normalized, checks_run=checks, errors=errors or [])
        return ProjectValidation(
            typecheck=make(self.typecheck_status), build=make(self.build_status),
            lint=make(self.lint_status), contract=make(self.contract_status),
            accessibility=make(self.accessibility_status), motion=make(self.motion_status, errors=self.motion_failures),
            three_d=make(self.three_d_status), runtime=make(self.runtime_status),
            interaction=make(self.interaction_status, self.interactions_tested, self.interaction_errors),
            preview=make(self.preview_status),
        )


def _stop_process_tree(proc: subprocess.Popen):
    """Cleanly stops dev server processes and their child processes."""
    if proc is None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    else:
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except Exception:
            pass
    try:
        proc.wait(timeout=3)
    except Exception:
        if os.name != "nt":
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except Exception:
                pass
        else:
            try:
                proc.kill()
            except Exception:
                pass
        try:
            proc.wait(timeout=2)
        except Exception:
            pass


def _link_node_modules(target_nm: Path, source_nm: Path):
    """Creates a directory junction (Windows) or symlink (POSIX) to node_modules."""
    if not source_nm.exists() or target_nm.exists():
        return
    try:
        if os.name == "nt":
            res = subprocess.run(
                ["cmd.exe", "/c", "mklink", "/J", str(target_nm), str(source_nm)],
                capture_output=True,
                text=True,
            )
            if res.returncode != 0:
                try:
                    os.symlink(str(source_nm), str(target_nm), target_is_directory=True)
                except Exception:
                    pass
        else:
            try:
                os.symlink(str(source_nm), str(target_nm), target_is_directory=True)
            except Exception:
                pass
    except Exception as err:
        print(f"[ProjectValidator] Note: node_modules link: {err}")


def _ensure_project_configs(workspace_dir: Path):
    """Ensures workspace has valid package.json, tsconfig.json, vite.config.ts, vite-env.d.ts, and node_modules linked."""
    target_nm = workspace_dir / "node_modules"
    source_nm = BASE_DIR / "node_modules"
    _link_node_modules(target_nm, source_nm)

    # 1. vite-env.d.ts for CSS module and client type support
    src_dir = workspace_dir / "src"
    src_dir.mkdir(parents=True, exist_ok=True)
    env_dts = src_dir / "vite-env.d.ts"
    if not env_dts.exists():
        env_dts.write_text('/// <reference types="vite/client" />\ndeclare module "*.css";\ndeclare module "*.module.css";\n', encoding="utf-8")

    # 2. tsconfig.json with modern bundler resolution and relaxed extension imports
    import json
    tsconfig_path = workspace_dir / "tsconfig.json"
    tsconfig_data = {}
    if tsconfig_path.exists():
        try:
            tsconfig_data = json.loads(tsconfig_path.read_text(encoding="utf-8"))
        except Exception:
            tsconfig_data = {}
    
    opts = tsconfig_data.setdefault("compilerOptions", {})
    opts.setdefault("target", "ES2022")
    opts.setdefault("lib", ["ES2022", "DOM"])
    opts.setdefault("jsx", "react-jsx")
    opts.setdefault("module", "ESNext")
    opts.setdefault("moduleResolution", "bundler")
    opts["allowImportingTsExtensions"] = True
    opts["noEmit"] = True
    opts["skipLibCheck"] = True
    opts["esModuleInterop"] = True
    tsconfig_data.setdefault("include", ["**/*.ts", "**/*.tsx", "src/vite-env.d.ts"])
    tsconfig_path.write_text(json.dumps(tsconfig_data, indent=2), encoding="utf-8")

    # 3. vite.config.ts
    vite_cfg = workspace_dir / "vite.config.ts"
    if not vite_cfg.exists():
        cfg_text = """import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  define: {
    'process.env': {},
  },
  server: {
    strictPort: false,
    host: '127.0.0.1',
    open: false,
  },
});
"""
        vite_cfg.write_text(cfg_text, encoding="utf-8")

    # 4. package.json with typecheck and build scripts
    pkg_path = workspace_dir / "package.json"
    pkg_data = {}
    if pkg_path.exists():
        try:
            pkg_data = json.loads(pkg_path.read_text(encoding="utf-8"))
        except Exception:
            pkg_data = {}
    
    pkg_data.setdefault("name", "slm-project")
    pkg_data.setdefault("private", True)
    pkg_data.setdefault("version", "1.0.0")
    pkg_data.setdefault("type", "module")
    scripts = pkg_data.setdefault("scripts", {})
    scripts.setdefault("dev", "vite")
    scripts["typecheck"] = "tsc --noEmit"
    scripts["build"] = "vite build"
    scripts.setdefault("preview", "vite preview")
    pkg_data.setdefault("dependencies", {"react": "^19.0.0", "react-dom": "^19.0.0"})
    pkg_data.setdefault("devDependencies", {
        "@types/react": "^19.0.10",
        "@types/react-dom": "^19.0.4",
        "@vitejs/plugin-react": "^4.3.4",
        "typescript": "^5.7.3",
        "vite": "^6.0.0",
    })
    pkg_path.write_text(json.dumps(pkg_data, indent=2), encoding="utf-8")

    # 5. index.html entry if missing
    index_html = workspace_dir / "index.html"
    if not index_html.exists():
        index_html.write_text("""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>SLM Workspace</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/main.tsx"></script>
  </body>
</html>
""", encoding="utf-8")

    main_tsx = workspace_dir / "main.tsx"
    if not main_tsx.exists():
        cand = "App" if (workspace_dir / "App.tsx").exists() or (workspace_dir / "src" / "App.tsx").exists() else "Component"
        main_tsx.write_text(f"""import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './{cand}';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
""", encoding="utf-8")


def run_static_lint(workspace_dir: Path) -> Tuple[bool, List[str], List[str]]:
    """Quick gate: Static linting of CSS syntax, token conformance, and selector scoping.

    Fail-closed contract:
      • If check_site_files omits 'static_passed' (schema change / partial return),
        this function immediately returns (False, [error], warnings) rather than
        defaulting to success.  "Missing key" is treated as a malformed result.
    """
    errors: List[str] = []
    warnings: List[str] = []
    try:
        from agent.site_acceptance import check_site_files
        current_files = {}
        for p in workspace_dir.rglob("*"):
            if p.is_file() and not any(part in p.parts for part in ["node_modules", ".git", "dist", ".vite"]):
                rel_path = p.relative_to(workspace_dir).as_posix()
                try:
                    current_files[rel_path] = p.read_text(encoding="utf-8")
                except Exception:
                    pass
        if current_files:
            acceptance = check_site_files(current_files)
            # --- P0-05 fail-closed: missing key must never default to True ---
            if "static_passed" not in acceptance:
                errors.append(
                    "[Lint Error] Malformed acceptance result: 'static_passed' key absent. "
                    "check_site_files returned an unexpected schema — failing closed."
                )
                return (False, errors, warnings)
            if not acceptance["static_passed"]:
                for err in acceptance.get("errors", []):
                    errors.append(f"[Lint Error] {err}")
            for w in acceptance.get("warnings", []):
                warnings.append(f"[Lint Warning] {w}")
            from agent.dependency_manager import PackagePolicy, external_imports
            source_files = {
                name: content for name, content in current_files.items()
                if name.startswith("src/") or name in ("App.tsx", "main.tsx", "main.jsx")
            }
            manifest_path = workspace_dir / "package.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
            declared = set(manifest.get("dependencies", {})) | set(manifest.get("devDependencies", {}))
            for package in sorted(external_imports(source_files)):
                if not PackagePolicy.is_package_allowed(package):
                    errors.append(f"[Lint Error] Unsupported external import '{package}'.")
                elif package not in declared and package not in {"react", "react-dom"}:
                    errors.append(f"[Lint Error] External import '{package}' is missing from package.json.")
            return (len(errors) == 0, errors, warnings)
    except Exception as exc:
        errors.append(f"[Lint Checker Exception] Static lint failed closed: {exc}")
        return (False, errors, warnings)
    return (True, errors, warnings)


def run_rendering_contract_check(workspace_dir: Path, prompt: str = "") -> List[str]:
    """Inspect only source reachable from a real entry point, including its styles."""
    from agent.site_quality import collect_site_rendering_diagnostics
    entries = [workspace_dir / path for path in ("main.tsx", "src/main.tsx", "src/main.jsx", "src/index.tsx", "src/App.tsx", "App.tsx")]
    pending = [path for path in entries if path.is_file()][:1]
    sources = {}
    while pending:
        path = pending.pop()
        try:
            relative = path.resolve().relative_to(workspace_dir.resolve()).as_posix()
        except ValueError:
            continue
        if relative in sources or not path.is_file():
            continue
        source = path.read_text(encoding="utf-8", errors="replace")
        sources[relative] = source
        imports = re.findall(r"(?:\bfrom\s*|\bimport\s*(?:\(\s*)?|@import\s*)['\"](\.[^'\"]+)['\"]", source)
        for target in imports:
            base = path.parent / target
            candidates = [base] + [Path(str(base) + suffix) for suffix in (".tsx", ".ts", ".jsx", ".js", ".css")] + [base / "index.tsx", base / "index.ts"]
            match = next((item for item in candidates if item.is_file()), None)
            if match:
                pending.append(match)
    return [f"[Rendering Contract Error] {item}" for item in collect_site_rendering_diagnostics(sources, prompt)]


def run_contract_check(workspace_dir: Path) -> Tuple[bool, List[str], List[str]]:
    """Gate 5a: Contract compliance (structural integrity, section completeness, no count leaks or fake contacts)."""
    errors: List[str] = []
    warnings: List[str] = []
    try:
        from agent.site_acceptance import _COUNT_LEAK_RE, _FAKE_CONTACT_RE, _FABRICATED_TESTIMONIAL_RE
        
        # Check required files
        app_file = workspace_dir / "App.tsx"
        if not app_file.is_file() and not (workspace_dir / "src" / "App.tsx").is_file():
            # Only flag missing App.tsx if workspace already contains tsx files or configs
            if any(workspace_dir.glob("*.tsx")) or (workspace_dir / "package.json").is_file():
                errors.append("[Contract Error] Missing App.tsx root component.")
            
        source_parts: List[str] = []
        for p in workspace_dir.rglob("*"):
            if p.is_file() and p.suffix in (".tsx", ".ts", ".jsx", ".js") and not any(part in p.parts for part in ["node_modules", ".git", "dist", ".vite"]):
                try:
                    content = p.read_text(encoding="utf-8")
                except Exception:
                    continue
                rel_path = p.relative_to(workspace_dir).as_posix()
                source_parts.append(content)
                if _COUNT_LEAK_RE.search(content):
                    errors.append(f"[Contract Error] {rel_path}: layout count leaked into product content.")
                if _FAKE_CONTACT_RE.search(content):
                    warnings.append(f"[Contract Warning] {rel_path}: placeholder contact details detected.")
                if _FABRICATED_TESTIMONIAL_RE.search(content):
                    # P0-06: HARD ERROR — ContentProvenance.GENERATED_PLACEHOLDER blocked for
                    # 'testimonials' / 'people' categories.  Fabricated named endorsements must
                    # not ship in a production export.
                    errors.append(
                        f"[Contract Error] {rel_path}: fabricated testimonial detected "
                        f"(job-title + org pattern — ContentProvenance.GENERATED_PLACEHOLDER "
                        f"is blocked for testimonials/people). "
                        f"Use only user-supplied or explicitly-illustrative endorsements."
                    )
                if (p.suffix in (".tsx", ".jsx")
                        and any(token in p.stem.lower() for token in ("header", "navbar", "navigation"))
                        and re.search(r'\bhidden\s+md:flex\b', content)
                        and not re.search(r'<button\b|aria-controls=|menu-button|mobile-menu', content, re.I)):
                    errors.append(f"[Responsive Error] {rel_path}: desktop navigation is hidden on mobile without a menu control.")
                    
        brief_path = workspace_dir / "content_brief.json"
        if brief_path.is_file():
            brief = json.loads(brief_path.read_text(encoding="utf-8"))
            manifest = brief.get("requirement_manifest") or {}
            source_lower = "\n".join(source_parts).lower()
            for fact in manifest.get("exact_facts", []):
                if str(fact).lower() not in source_lower:
                    errors.append(f"[Requirement Error] User-supplied fact is absent: {fact}")
            for route in manifest.get("routes", []):
                if str(route).lower() not in source_lower:
                    errors.append(f"[Requirement Error] Requested route is absent: {route}")
            for section in manifest.get("explicit_sections", []):
                if str(section).lower() not in source_lower:
                    errors.append(f"[Requirement Error] Explicit section is absent: {section}")
        return (len(errors) == 0, errors, warnings)
    except Exception as exc:
        errors.append(f"[Contract Checker Exception] Contract check failed closed: {exc}")
        return (False, errors, warnings)


VALID_ARIA_ROLES = {
    "alert", "alertdialog", "application", "article", "banner", "button", "cell",
    "checkbox", "columnheader", "combobox", "complementary", "contentinfo",
    "definition", "dialog", "directory", "document", "feed", "figure", "form",
    "grid", "gridcell", "group", "heading", "img", "link", "list", "listbox",
    "listitem", "log", "main", "marquee", "math", "menu", "menubar", "menuitem",
    "menuitemcheckbox", "menuitemradio", "navigation", "none", "note", "option",
    "presentation", "progressbar", "radio", "radiogroup", "region", "row",
    "rowgroup", "rowheader", "scrollbar", "search", "searchbox", "separator",
    "slider", "spinbutton", "status", "switch", "tab", "table", "tablist",
    "tabpanel", "term", "textbox", "timer", "toolbar", "tooltip", "tree",
    "treegrid", "treeitem",
}


def parse_color_to_rgb(color_str: str) -> Optional[Tuple[float, float, float]]:
    """Parses hex (#fff, #ffffff, #ffffff80) or rgb/rgba to normalized (r, g, b) float tuple in 0.0-1.0."""
    color_str = color_str.strip()
    if color_str.startswith("#"):
        hex_val = color_str.lstrip("#")
        if len(hex_val) == 3:
            hex_val = "".join(c * 2 for c in hex_val)
        if len(hex_val) in (6, 8):
            try:
                r = int(hex_val[0:2], 16) / 255.0
                g = int(hex_val[2:4], 16) / 255.0
                b = int(hex_val[4:6], 16) / 255.0
                return (r, g, b)
            except ValueError:
                return None
    rgb_m = re.match(r'rgba?\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)', color_str, re.I)
    if rgb_m:
        return (
            int(rgb_m.group(1)) / 255.0,
            int(rgb_m.group(2)) / 255.0,
            int(rgb_m.group(3)) / 255.0,
        )
    return None


def calculate_relative_luminance(rgb: Tuple[float, float, float]) -> float:
    """Computes WCAG relative luminance L = 0.2126*R + 0.7152*G + 0.0722*B."""
    def channel(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * channel(rgb[0]) + 0.7152 * channel(rgb[1]) + 0.0722 * channel(rgb[2])


def calculate_contrast_ratio(c1: Any, c2: Any) -> Optional[float]:
    """Calculates WCAG 2.1 contrast ratio between two colors (hex/rgb string or RGB tuple, e.g. 7.0 for 7:1)."""
    rgb1 = tuple(c1) if isinstance(c1, (tuple, list)) else parse_color_to_rgb(c1)
    rgb2 = tuple(c2) if isinstance(c2, (tuple, list)) else parse_color_to_rgb(c2)
    if not rgb1 or not rgb2:
        return None
    l1 = calculate_relative_luminance(rgb1)
    l2 = calculate_relative_luminance(rgb2)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def verify_css_contrast_tokens(css_text: str, filename: str) -> List[str]:
    """Inspects CSS variables or explicit color rules for contrast ratio adherence (WCAG AAA >= 7:1, AA >= 4.5:1)."""
    warns: List[str] = []
    bg_m = re.findall(r'--(?:color-)?(?:bg|background|surface)[a-zA-Z0-9_-]*\s*:\s*(#[0-9a-fA-F]{3,8}|rgba?\([^)]+\))', css_text)
    fg_m = re.findall(r'--(?:color-)?(?:text|foreground|content)[a-zA-Z0-9_-]*\s*:\s*(#[0-9a-fA-F]{3,8}|rgba?\([^)]+\))', css_text)
    for bg in bg_m:
        for fg in fg_m:
            ratio = calculate_contrast_ratio(fg, bg)
            if ratio is not None:
                if ratio < 4.5:
                    warns.append(
                        f"[A11y Warning] {filename}: Color token pairing fg={fg} on bg={bg} yields contrast ratio {ratio:.2f}:1 "
                        f"(fails WCAG AA 4.5:1 and AAA 7:1 for normal text)."
                    )
                elif ratio < 7.0:
                    warns.append(
                        f"[A11y Note] {filename}: Color token pairing fg={fg} on bg={bg} yields contrast ratio {ratio:.2f}:1 "
                        f"(meets WCAG AA 4.5:1, but below WCAG AAA 7:1 for normal text)."
                    )
    return warns


def run_accessibility_check(workspace_dir: Path) -> Tuple[bool, List[str], List[str]]:
    """Gate 5b: Authoritative accessibility compliance (semantic landmarks, alt attributes, form labels, controls, headings, ARIA)."""
    errors: List[str] = []
    warnings: List[str] = []
    try:
        app_candidates = [workspace_dir / "App.tsx", workspace_dir / "src" / "App.tsx"]
        app_file = next((f for f in app_candidates if f.is_file()), None)
        
        has_main = False
        has_h1 = False
        ts_files = [
            p for p in workspace_dir.rglob("*")
            if p.is_file() and p.suffix in (".tsx", ".jsx")
            and not any(part in p.parts for part in ["node_modules", ".git", "dist", ".vite"])
        ]

        for p in ts_files:
            try:
                content = p.read_text(encoding="utf-8")
            except Exception:
                continue
            rel = p.relative_to(workspace_dir).as_posix()
            
            # 1. Main landmark detection
            if "<main" in content or 'id="site-main"' in content or 'role="main"' in content or "role='main'" in content:
                has_main = True
            
            # 2. Heading inspection
            if "<h1" in content:
                has_h1 = True
            # Material heading hierarchy skip: e.g. <h1 ...> then jumping directly to <h4 or <h5 or <h6 without intermediate h2/h3
            if "<h1" in content and ("<h4" in content or "<h5" in content or "<h6" in content):
                if "<h2" not in content and "<h3" not in content:
                    errors.append(f"[A11y Error] {rel}: Material heading hierarchy skip: jumped from <h1> directly to <h4/h5/h6> without intermediate <h2> or <h3>.")

            # 3. Meaningful <img> missing 'alt' attribute
            for match in re.finditer(r'<img\b([^>]*)>', content):
                tag_attrs = match.group(1)
                if "alt=" not in tag_attrs and 'role="presentation"' not in tag_attrs and 'aria-hidden="true"' not in tag_attrs:
                    errors.append(f"[A11y Error] {rel}: <img> element missing required 'alt' attribute for screen readers.")

            # 4. Form controls accessible name check (WCAG SC 3.3.2 / 4.1.2)
            html_for_labels = set(re.findall(r'<label\b[^>]*\b(?:htmlFor|for)=["\']([^"\']+)["\']', content))
            html_for_labels.update(re.findall(r'<label\b[^>]*\b(?:htmlFor|for)=\{\s*["\']([^"\']+)["\']\s*\}', content))
            label_spans = [m.span() for m in re.finditer(r'<label\b[^>]*>[\s\S]*?</label>', content)]

            for match in re.finditer(r'<input\b([^>]*)>', content):
                tag_attrs = match.group(1)
                type_m = re.search(r'type=["\']([^"\']+)["\']', tag_attrs)
                input_type = type_m.group(1).lower() if type_m else "text"
                if input_type not in ("hidden", "submit", "button", "reset"):
                    has_aria_or_title = any(attr in tag_attrs for attr in ["aria-label", "aria-labelledby", "title="])
                    id_m = re.search(r'\bid=["\']([^"\']+)["\']', tag_attrs) or re.search(r'\bid=\{\s*["\']([^"\']+)["\']\s*\}', tag_attrs)
                    has_matching_label = bool(id_m and id_m.group(1) in html_for_labels)
                    is_wrapped = any(start <= match.start() <= end for start, end in label_spans)
                    has_acc_label = has_aria_or_title or has_matching_label or is_wrapped
                    if not has_acc_label:
                        errors.append(
                            f"[A11y Error] {rel}: Inaccessible form <input type=\"{input_type}\"> missing accessible name "
                            f"(must have 'aria-label', 'aria-labelledby', or matching <label htmlFor=\"...\">; "
                            f"bare 'id' or 'placeholder' is insufficient under WCAG SC 3.3.2/4.1.2)."
                        )

            for match in re.finditer(r'<textarea\b([^>]*)>', content):
                tag_attrs = match.group(1)
                has_aria_or_title = any(attr in tag_attrs for attr in ["aria-label", "aria-labelledby", "title="])
                id_m = re.search(r'\bid=["\']([^"\']+)["\']', tag_attrs) or re.search(r'\bid=\{\s*["\']([^"\']+)["\']\s*\}', tag_attrs)
                has_matching_label = bool(id_m and id_m.group(1) in html_for_labels)
                is_wrapped = any(start <= match.start() <= end for start, end in label_spans)
                if not (has_aria_or_title or has_matching_label or is_wrapped):
                    errors.append(
                        f"[A11y Error] {rel}: Inaccessible form <textarea> missing accessible name "
                        f"(must have 'aria-label', 'aria-labelledby', or matching <label htmlFor=\"...\">)."
                    )

            for match in re.finditer(r'<select\b([^>]*)>', content):
                tag_attrs = match.group(1)
                has_aria_or_title = any(attr in tag_attrs for attr in ["aria-label", "aria-labelledby", "title="])
                id_m = re.search(r'\bid=["\']([^"\']+)["\']', tag_attrs) or re.search(r'\bid=\{\s*["\']([^"\']+)["\']\s*\}', tag_attrs)
                has_matching_label = bool(id_m and id_m.group(1) in html_for_labels)
                is_wrapped = any(start <= match.start() <= end for start, end in label_spans)
                if not (has_aria_or_title or has_matching_label or is_wrapped):
                    errors.append(
                        f"[A11y Error] {rel}: Inaccessible form <select> missing accessible name "
                        f"(must have 'aria-label', 'aria-labelledby', or matching <label htmlFor=\"...\">)."
                    )

            # 5. Unlabeled interactive controls (<button> missing text and aria-label)
            for match in re.finditer(r'<button\b([^>]*)>(.*?)</button>', content, re.DOTALL):
                btn_attrs = match.group(1)
                btn_body = match.group(2).strip()
                has_aria = any(attr in btn_attrs for attr in ["aria-label", "aria-labelledby", "title="])
                text_content = re.sub(r'<[^>]+>', '', btn_body).strip()
                if not has_aria and not text_content:
                    errors.append(f"[A11y Error] {rel}: Interactive <button> is unlabeled (missing visible text and 'aria-label').")

            # 6. Inaccessible text-reveal semantics
            if re.search(
                r'(?:char|letter|split-word|word)\b[^>]*style=\{\s*\{[^}]*?(?:animation|transition)',
                content,
                re.IGNORECASE,
            ) or "splitText" in content:
                if 'aria-hidden="true"' not in content and "aria-hidden='true'" not in content:
                    errors.append(f"[A11y Error] {rel}: Inaccessible text-reveal semantics: animated character fragments must have aria-hidden=\"true\" with an accessible label on the parent.")

            # 7. Duplicate element IDs (WCAG SC 4.1.1)
            file_ids = [m.group(1) for m in re.finditer(r'\bid=["\']([a-zA-Z0-9_\-]+)["\']', content)]
            seen_ids = set()
            for eid in file_ids:
                if eid in seen_ids:
                    errors.append(f"[A11y Error] {rel}: Duplicate element id '{eid}' violates WCAG SC 4.1.1.")
                seen_ids.add(eid)

            # 8. Landmark uniqueness (WCAG SC 1.3.1)
            nav_matches = list(re.finditer(r'<nav\b([^>]*)>', content))
            if len(nav_matches) > 1:
                unlabeled_navs = [m for m in nav_matches if not any(attr in m.group(1) for attr in ["aria-label", "aria-labelledby"])]
                if unlabeled_navs:
                    errors.append(f"[A11y Error] {rel}: Multiple <nav> landmarks detected; each must have a unique 'aria-label' or 'aria-labelledby' to distinguish them.")

            # 9. Invalid ARIA roles (WCAG SC 4.1.2)
            for m in re.finditer(r'\brole=["\']([a-zA-Z0-9_\-]+)["\']', content):
                role_val = m.group(1).lower()
                if role_val not in VALID_ARIA_ROLES:
                    errors.append(f"[A11y Error] {rel}: Invalid or non-standard ARIA role '{role_val}'.")

        # Full site checks
        if len(ts_files) > 1 and app_file:
            if not has_main:
                errors.append("[A11y Error] Workspace missing required semantic <main id=\"site-main\"> (or role=\"main\") landmark.")
            if not has_h1:
                errors.append("[A11y Error] Full site workspace missing top-level <h1> heading.")

        # 10. Precomputed color contrast checking on CSS tokens
        css_files = [
            p for p in workspace_dir.rglob("*")
            if p.is_file() and p.suffix in (".css",)
            and not any(part in p.parts for part in ["node_modules", ".git", "dist", ".vite"])
        ]
        for cp in css_files:
            try:
                css_text = cp.read_text(encoding="utf-8")
                contrast_warnings = verify_css_contrast_tokens(css_text, cp.relative_to(workspace_dir).as_posix())
                warnings.extend(contrast_warnings)
            except Exception:
                pass

        return (len(errors) == 0, errors, warnings)
    except Exception as exc:
        errors.append(f"[A11y Checker Exception] Accessibility check failed closed: {exc}")
        return (False, errors, warnings)


def run_motion_rules_check(workspace_dir: Path) -> Tuple[bool, List[str], List[str]]:
    """Motion Implementation Rules verification (Section 5)."""
    errors: List[str] = []
    warnings: List[str] = []
    
    # 1. Detect if motion was requested in content brief, prompt, or workspace files
    requested_motion = False
    cb_file = workspace_dir / "content_brief.json"
    if cb_file.is_file():
        try:
            cb_data = json.loads(cb_file.read_text(encoding="utf-8"))
            if cb_data.get("motion_plan") or cb_data.get("requested_motion"):
                requested_motion = True
        except Exception:
            pass

    for p in [workspace_dir / "prompt.txt", workspace_dir / "user_prompt.txt"]:
        if p.is_file():
            try:
                p_text = p.read_text(encoding="utf-8", errors="ignore").lower()
                if any(kw in p_text for kw in ["parallax", "scroll reveal", "scroll-reveal", "horizontal scroll", "marquee", "motion", "reveal"]):
                    requested_motion = True
            except Exception:
                pass

    current_files: Dict[str, str] = {}
    for p in workspace_dir.rglob("*"):
        if p.is_file() and not any(part in p.parts for part in ["node_modules", ".git", "dist", ".vite"]):
            rel_path = p.relative_to(workspace_dir).as_posix()
            try:
                content = p.read_text(encoding="utf-8")
                current_files[rel_path] = content
                if any(kw in content.lower() for kw in ["parallax", "scrollreveal", "scroll-reveal", "horizontal-scroll", "gsap", "framermotion", "framer-motion"]):
                    requested_motion = True
            except Exception:
                pass

    try:
        from agent.motion_patterns import validate_motion_rules
    except ImportError:
        try:
            from motion_patterns import validate_motion_rules
        except ImportError:
            validate_motion_rules = None

    if validate_motion_rules is None:
        if requested_motion:
            return (False, ["[Motion Verification Error] Motion validation unavailable."], [])
        else:
            warnings.append("[Motion Checker Note] Motion rules check skipped: motion patterns module unavailable.")
            return (True, errors, warnings)

    try:
        if current_files:
            pkg_path = workspace_dir / "package.json"
            res = validate_motion_rules(current_files, package_json=pkg_path, workspace_dir=workspace_dir)
            for err in res.violations:
                errors.append(f"[Motion Rule Violation] {err}")
            for w in res.warnings:
                warnings.append(f"[Motion Rule Warning] {w}")
            return (len(errors) == 0, errors, warnings)
    except Exception as exc:
        if requested_motion:
            errors.append(f"[Motion Verification Error] Motion rules check failed: {exc}")
            return (False, errors, warnings)
        else:
            warnings.append(f"[Motion Rule Checker Note] Motion rules check skipped: {exc}")
            return (True, errors, warnings)
            
    return (True, errors, warnings)



def run_project_typecheck(workspace_dir: Path, timeout_s: int = 45) -> Tuple[bool, List[str]]:
    """Authoritative gate 1: full workspace TypeScript compilation with cross-file import check."""
    _ensure_project_configs(workspace_dir)
    errors: List[str] = []
    try:
        proc = subprocess.run(
            ["npx", "tsc", "--noEmit", "-p", "tsconfig.json"],
            cwd=str(workspace_dir),
            capture_output=True,
            text=True,
            timeout=timeout_s,
            shell=(os.name == "nt"),
        )
        if proc.returncode != 0:
            raw = (proc.stdout + "\n" + proc.stderr).strip()
            for line in raw.splitlines():
                line_str = line.strip()
                if line_str and not line_str.startswith("npm notice"):
                    errors.append(f"[TypeScript Error] {line_str}")
            return (False, errors)
        return (True, [])
    except subprocess.TimeoutExpired:
        return (False, [f"[TypeScript Error] Typecheck timed out after {timeout_s}s."])
    except Exception as exc:
        return (False, [f"[TypeScript Error] Failed to execute tsc: {exc}"])


def run_project_build(workspace_dir: Path, timeout_s: int = 60) -> Tuple[bool, List[str]]:
    """Authoritative gate 2: production bundler build via Vite / Rollup."""
    _ensure_project_configs(workspace_dir)
    errors: List[str] = []
    try:
        proc = subprocess.run(
            ["npx", "vite", "build"],
            cwd=str(workspace_dir),
            capture_output=True,
            text=True,
            timeout=timeout_s,
            shell=(os.name == "nt"),
        )
        if proc.returncode != 0:
            raw = (proc.stdout + "\n" + proc.stderr).strip()
            for line in raw.splitlines():
                line_str = line.strip()
                if line_str and ("error" in line_str.lower() or "failed" in line_str.lower() or "is not exported" in line_str):
                    errors.append(f"[Build Error] {line_str}")
            if not errors and raw:
                # Capture last few lines of bundler output if no explicit 'error' keyword matched
                for line in raw.splitlines()[-6:]:
                    if line.strip():
                        errors.append(f"[Build Error] {line.strip()}")
            return (False, errors)
        return (True, [])
    except subprocess.TimeoutExpired:
        return (False, [f"[Build Error] Production build timed out after {timeout_s}s."])
    except Exception as exc:
        return (False, [f"[Build Error] Failed to execute vite build: {exc}"])


# Shared predicate for Playwright candidates and browser-side accessibility checks.
# is_visible() alone includes transparent, aria-hidden and offscreen skip controls.
VISIBLE_INTERACTIVE_JS = """el => {
    if (!el || !el.isConnected || el.closest('[hidden], [inert], [aria-hidden="true"]')) return false;
    if (el.matches('a[href^="#"]') && (
        /skip|jump.to.(?:main|content)/i.test([el.className, el.id, el.textContent, el.getAttribute('aria-label')].join(' '))
    )) return false;
    if (el.closest('.site-skip-link, .skip-link, .visually-hidden, .sr-only, [role="presentation"], [role="none"]')) return false;
    if (el.getAttribute('tabindex') === '-1' || el.hasAttribute('disabled') || el.getAttribute('aria-disabled') === 'true') return false;
    const r = el.getBoundingClientRect();
    if (r.width <= 0 || r.height <= 0 || r.right <= 0 || r.bottom <= 0) return false;
    for (let node = el; node && node.nodeType === 1; node = node.parentElement) {
        const s = getComputedStyle(node);
        if (s.display === 'none' || s.visibility !== 'visible' || Number(s.opacity) === 0) return false;
    }
    return true;
}"""


def _visible_interactive_controls(locator: Any) -> List[Any]:
    """Return only rendered, onscreen, non-decorative, operable controls."""
    return [node for node in locator.all() if node.is_visible() and node.evaluate(VISIBLE_INTERACTIVE_JS)]


def check_mobile_control_bounds(page: Any) -> List[str]:
    """Detect inaccessible horizontal controls even when overflow hides them."""
    clipped = page.evaluate("""() => [...document.querySelectorAll('a[href],button,input:not([type=hidden]),select,textarea')].filter(el => {
        if (el.closest('[hidden],[inert],[aria-hidden="true"],.site-skip-link,.skip-link,.sr-only,.visually-hidden')) return false;
        if (el.disabled || el.getAttribute('tabindex') === '-1') return false;
        for (let n=el;n && n.nodeType===1;n=n.parentElement) {
            const s=getComputedStyle(n); if(s.display==='none'||s.visibility!=='visible'||Number(s.opacity)===0) return false;
        }
        const r=el.getBoundingClientRect();
        return r.width>0 && r.height>0 && (r.left < -2 || r.right > innerWidth+2);
    }).map(el => (el.getAttribute('aria-label')||el.textContent||el.tagName).trim().slice(0,80)).slice(0,12)""")
    return [f"[Interaction Error] Mobile control outside visible horizontal bounds: {name}" for name in clipped]


def _first_interactive_control(locator: Any) -> Optional[Any]:
    controls = _visible_interactive_controls(locator)
    return controls[0] if controls else None


def _check_brief_interactions(page: Any, brief_text: str) -> Tuple[List[InteractionEvidence], List[str], int, int]:
    """
    Deterministic DOM interaction evaluation for explicitly requested brief features.
    Produces explicit behavioral InteractionEvidence for every required interaction.
    Returns: (evidence_list, failures, interactions_tested, interactions_required)
    """
    failures: List[str] = []
    evidence_list: List[InteractionEvidence] = []
    tested_count = 0
    required_count = 0

    if not brief_text:
        return evidence_list, failures, tested_count, required_count

    try:
        brief = json.loads(brief_text)
    except (TypeError, ValueError):
        brief = {}

    requested = {str(item).lower() for item in brief.get("required_interactions", []) if isinstance(item, str)}
    manifest_interactions = (brief.get("requirement_manifest") or {}).get("interactions", [])
    requested.update(str(item).lower() for item in manifest_interactions if isinstance(item, str))
    interaction_contracts = (brief.get("requirement_manifest") or {}).get("interaction_constraints", [])

    # Helper to append structured evidence
    def record_evidence(
        req_id: str,
        locator: str,
        initial_state: Any,
        action: str,
        expected_state: Any,
        observed_state: Any,
        passed: bool,
        error: Optional[str] = None,
    ):
        ev = InteractionEvidence(
            requirement_id=req_id,
            locator=locator,
            initial_state=initial_state,
            action=action,
            expected_state=expected_state,
            observed_state=observed_state,
            passed=passed,
            error=error,
        )
        evidence_list.append(ev)
        if not passed and error:
            failures.append(f"[Interaction Error] {error}")

    # 1. Cart state
    if "cart_state" in requested or re.search(r"\b(cart state|add to cart|shopping cart)\b", brief_text):
        required_count += 1
        tested_count += 1
        add = _first_interactive_control(page.get_by_role("button", name=re.compile(r"\badd(?:\s+to\s+(?:cart|bag|basket))?\b", re.I)))
        cart = _first_interactive_control(page.locator('header [data-cart-count], header button[aria-label*="cart" i], header a[aria-label*="cart" i], header button:has-text("Cart"), header a:has-text("Cart"), nav [data-cart-count], [data-cart-count], button[aria-label*="cart" i], a[aria-label*="cart" i], button:has-text("Cart"), a:has-text("Cart")'))
        if not add or not cart:
            record_evidence(
                req_id="cart_state",
                locator="add-to-cart button / header cart indicator",
                initial_state=None,
                action="locate product add button and shared cart indicator",
                expected_state="both controls present and visible in DOM",
                observed_state=f"add_found={bool(add)}, cart_found={bool(cart)}",
                passed=False,
                error="Cart requires a product action and shared cart indicator.",
            )
        else:
            cart_state = lambda: (cart.inner_text(), cart.get_attribute("aria-label"), cart.get_attribute("data-cart-count"))
            before = cart_state()
            add.click(timeout=1000)
            page.wait_for_timeout(150)
            after = cart_state()
            passed = (after != before)
            cart_contract = next((item for item in interaction_contracts if item.get("type") == "cart_state"), {})
            states = [before, after]
            if cart_contract.get("repeated_clicks_required") or cart_contract.get("products"):
                def quantity(state):
                    badge = state[2]
                    if badge and str(badge).isdigit():
                        return int(badge)
                    match = re.search(r"\b(\d+)\b", " ".join(str(item or "") for item in state[:2]))
                    return int(match.group(1)) if match else None
                before_count, after_count = quantity(before), quantity(after)
                passed = before_count is not None and after_count == before_count + 1
                buttons = _visible_interactive_controls(page.get_by_role("button", name=re.compile(r"\badd(?:\s+to\s+(?:cart|bag|basket))?\b", re.I)))
                expected_products = len(cart_contract.get("products", []))
                passed = passed and len(buttons) >= max(1, expected_products)
                for button in [add, *buttons[1:expected_products]]:
                    previous = quantity(cart_state())
                    button.click(timeout=1000)
                    page.wait_for_timeout(100)
                    states.append(cart_state())
                    current = quantity(states[-1])
                    passed = passed and previous is not None and current == previous + 1
            record_evidence(
                req_id="cart_state",
                locator="header cart indicator",
                initial_state=str(before),
                action="click product buttons, including repeated clicks" if len(states) > 2 else "click add-to-cart button",
                expected_state="visible cart quantity increments for every requested product and repeated click",
                observed_state=str(states),
                passed=passed,
                error="Adding a product did not update the shared cart indicator." if not passed else None,
            )

    if "flat_view_toggle" in requested:
        required_count += 1
        tested_count += 1
        control = _first_interactive_control(page.get_by_role("button", name=re.compile(r"flat|2d", re.I)))
        if not control:
            control = _first_interactive_control(page.get_by_role("checkbox", name=re.compile(r"flat|2d", re.I)))
        geometry_js = """() => [...document.querySelectorAll('*')].filter(el => {
            const s=getComputedStyle(el),r=el.getBoundingClientRect();
            return r.width>0&&r.height>0&&(s.transformStyle==='preserve-3d'||s.perspective!=='none'||s.transform.startsWith('matrix3d'));
        }).map(el=>{const s=getComputedStyle(el);return [el.tagName,s.perspective,s.transformStyle,s.transform]})"""
        initial = page.evaluate(geometry_js)
        after, restored = None, None
        passed = False
        if control:
            handle = control.element_handle()
            try:
                handle.click(timeout=1000)
                page.wait_for_timeout(250)
                after = page.evaluate(geometry_js)
                handle.click(timeout=1000)
                page.wait_for_timeout(250)
                restored = page.evaluate(geometry_js)
                passed = bool(initial) and len(after) < len(initial) and bool(restored) and len(restored) == len(initial)
            except Exception as exc:
                passed = False
                failures.append(f"[Interaction Error] Flat-view control could not be operated: {str(exc).splitlines()[0][:240]}")
        record_evidence("flat_view_toggle", "flat/2D control and computed scene geometry", initial,
                        "toggle flat view and back", "scene depth changes and returns", [after, restored], passed,
                        None if passed else "Flat-view control must visibly change scene depth and restore it.")

    if "anchor_navigation" in requested:
        required_count += 1
        tested_count += 1
        anchors = _visible_interactive_controls(page.locator('a[href^="#"]'))
        broken = []
        for anchor in anchors:
            target = (anchor.get_attribute("href") or "")[1:]
            if not target or not page.evaluate("id => !!document.getElementById(id)", target):
                broken.append(target or "empty target")
        passed = bool(anchors) and not broken
        record_evidence("anchor_navigation", 'a[href^="#"]', None, "resolve visible in-page links",
                        "all requested links have real DOM targets", broken, passed,
                        None if passed else "Navigation contains missing section targets: " + ", ".join(broken))

    # 2. Filter state
    if "filter_state" in requested or re.search(r"\b(filter state|category filter|product filter)\b", brief_text):
        required_count += 1
        tested_count += 1
        filter_nodes = _visible_interactive_controls(page.locator('[data-filter]'))
        controls = filter_nodes if filter_nodes else _visible_interactive_controls(page.locator('select, button[aria-pressed]'))
        results = page.locator('[data-product], [data-result], article:visible')
        if not controls or not results.count():
            record_evidence(
                req_id="filter_state",
                locator="filter controls / product results",
                initial_state=None,
                action="locate filter controls and result cards",
                expected_state="filter controls and result cards present in DOM",
                observed_state=f"controls={len(controls)}, results={results.count()}",
                passed=False,
                error="Requested filter lacks controls or visible results.",
            )
        else:
            before = results.all_inner_texts()
            control = controls[0]
            if control.evaluate("el => el.tagName === 'SELECT'"):
                options = control.locator("option")
                if options.count() > 1:
                    control.select_option(index=1, timeout=1000)
            else:
                alternate = controls[1] if len(controls) > 1 else control
                alternate.click(timeout=1000)
            page.wait_for_timeout(100)
            after = results.all_inner_texts()
            passed = (after != before)
            record_evidence(
                req_id="filter_state",
                locator="[data-product], [data-result], article:visible",
                initial_state=before[:3],
                action="change filter option or click filter toggle",
                expected_state="visible product/result cards change",
                observed_state=after[:3],
                passed=passed,
                error="Filter did not change the visible results." if not passed else None,
            )

    # 3. Metrics Tab Filter
    if "metrics_tab_filter" in requested or re.search(r"\b(interactive metrics explorer|metrics tab filter)\b", brief_text):
        required_count += 1
        tested_count += 1
        section = page.locator("#features")
        filter_button = _first_interactive_control(section.get_by_role("button", name=re.compile(r"security|telemetry|real.time", re.I)))
        if not section.count() or not filter_button:
            record_evidence(
                req_id="metrics_tab_filter",
                locator="#features button[name=security|telemetry|real.time]",
                initial_state=None,
                action="locate metrics filter controls in #features section",
                expected_state="features section and filter buttons present in DOM",
                observed_state=f"section={section.count()}, filter_button={bool(filter_button)}",
                passed=False,
                error="Metrics filter controls are missing from the features section.",
            )
        else:
            before = section.locator("h3:visible").all_inner_texts()
            filter_button.click(timeout=1000)
            page.wait_for_timeout(100)
            after = section.locator("h3:visible").all_inner_texts()
            passed = bool(before and after and before != after)
            record_evidence(
                req_id="metrics_tab_filter",
                locator="#features h3:visible",
                initial_state=before,
                action="click filter button (security/telemetry/real.time)",
                expected_state="visible feature cards change",
                observed_state=after,
                passed=passed,
                error="Metrics filter does not change the visible feature cards." if not passed else None,
            )

    # 4. Pricing / Billing Toggle
    if "pricing_toggle" in requested or "billing_toggle" in requested or re.search(r"\b(monthly\s*(?:vs|/|and)\s*annual|billing toggle|pricing toggle|annual billing)\b", brief_text):
        required_count += 1
        tested_count += 1
        section = page.locator("#pricing")
        annual = _first_interactive_control(section.get_by_role("button", name=re.compile(r"annual|yearly", re.I)) if section.count()
                                            else page.get_by_role("button", name=re.compile(r"annual|yearly", re.I)))
        if not annual:
            record_evidence(
                req_id="pricing_toggle",
                locator="#pricing button[name=annual|yearly]",
                initial_state=None,
                action="locate annual pricing toggle button",
                expected_state="annual toggle button present and visible in DOM",
                observed_state="annual button not found",
                passed=False,
                error="Annual pricing control is missing.",
            )
        else:
            target_area = section if section.count() else page.locator("body")
            before = re.findall(r"\$\s?\d[\d,.]*", target_area.inner_text())
            annual.click(timeout=1000)
            page.wait_for_timeout(100)
            after = re.findall(r"\$\s?\d[\d,.]*", target_area.inner_text())
            passed = bool(before and after and before != after)
            record_evidence(
                req_id="pricing_toggle",
                locator="pricing values in #pricing",
                initial_state=before,
                action="click annual toggle button",
                expected_state="displayed dollar prices update",
                observed_state=after,
                passed=passed,
                error="Annual pricing control does not change displayed pricing." if not passed else None,
            )

    # 5. Mobile Nav Toggle / Drawer
    if "mobile_nav_toggle" in requested or "mobile_drawer" in requested or re.search(r"\b(mobile drawer|hamburger menu|mobile menu)\b", brief_text):
        required_count += 1
        tested_count += 1
        page.set_viewport_size({"width": 390, "height": 844})
        toggle = _first_interactive_control(page.locator('header button[aria-controls], header button[aria-label*="menu" i], header button[aria-label*="navigation" i], button[aria-controls], button[aria-label*="menu" i]'))
        if not toggle:
            record_evidence(
                req_id="mobile_nav_toggle",
                locator="header mobile menu button",
                initial_state=None,
                action="locate mobile nav toggle button at 390px viewport",
                expected_state="visible mobile navigation button with accessible label",
                observed_state="toggle missing or invisible",
                passed=False,
                error="Mobile navigation toggle lacks an accessible label or target.",
            )
        else:
            target_id = toggle.get_attribute("aria-controls")
            target = page.locator(f"#{target_id}") if target_id else page.locator("header nav:visible, [role='navigation']:visible")
            before = target.count() and target.first.is_visible()
            toggle.click(timeout=1000)
            page.wait_for_timeout(150)
            opened = target.count() and target.first.is_visible()
            page.keyboard.press("Escape")
            page.wait_for_timeout(100)
            closed = (not target.count() or not target.first.is_visible()) or toggle.get_attribute("aria-expanded") == "false"
            passed = bool(opened and (not before or closed))
            record_evidence(
                req_id="mobile_nav_toggle",
                locator="mobile menu / drawer",
                initial_state=f"initially_visible={before}",
                action="click toggle, verify opened, press Escape, verify closed",
                expected_state="menu opens on click and closes on Escape",
                observed_state=f"opened={opened}, closed={closed}",
                passed=passed,
                error="Mobile navigation toggle does not open menu or Escape does not close it." if not passed else None,
            )
        page.set_viewport_size({"width": 1280, "height": 900})

    # 6. Tabs
    if "tabs" in requested or re.search(r"\b(tabs|tabbed interface|tab switcher)\b", brief_text):
        required_count += 1
        tested_count += 1
        tabs = _visible_interactive_controls(page.locator('[role="tab"]'))
        if len(tabs) < 2:
            record_evidence(
                req_id="tabs",
                locator='[role="tab"]',
                initial_state=f"count={len(tabs)}",
                action="locate tabs in DOM",
                expected_state="at least 2 tab elements with role='tab'",
                observed_state=f"found {len(tabs)} tabs",
                passed=False,
                error="Requested tabs are missing (fewer than 2 tabs found).",
            )
        else:
            panels = page.locator('[role="tabpanel"]:visible')
            before_panel = panels.first.inner_text() if panels.count() else None
            tab = tabs[1]
            tab.click(timeout=1000)
            page.wait_for_timeout(100)
            sel = tab.get_attribute("aria-selected")
            panels = page.locator('[role="tabpanel"]:visible')
            after_panel = panels.first.inner_text() if panels.count() else None
            passed = (sel == "true") and (before_panel is not None and panels.count() > 0 and after_panel != before_panel)
            record_evidence(
                req_id="tabs",
                locator='[role="tab"], [role="tabpanel"]',
                initial_state=f"selected={tabs[0].get_attribute('aria-selected')}, panel_preview={str(before_panel)[:30]}",
                action="click second tab",
                expected_state="second tab aria-selected='true' and visible tabpanel content changes",
                observed_state=f"selected={sel}, panel_preview={str(after_panel)[:30]}",
                passed=passed,
                error="Tab selection failed or panel content did not change." if not passed else None,
            )

    # 7. Calculator / interactive slider
    if "calculator" in requested or re.search(r"\b(calculator|live calculation|interactive slider)\b", brief_text):
        required_count += 1
        tested_count += 1
        controls = _visible_interactive_controls(page.locator('input[type="range"], input[type="number"]'))
        outputs = page.locator('output, [aria-live="polite"], [aria-live="assertive"]')
        if not controls or outputs.count() == 0:
            record_evidence(
                req_id="calculator",
                locator="input[type='range'|'number'], output",
                initial_state=None,
                action="locate calculator input and output display",
                expected_state="input control and live output display present in DOM",
                observed_state=f"inputs={len(controls)}, outputs={outputs.count()}",
                passed=False,
                error="Requested calculator lacks an input or live output.",
            )
        else:
            before = outputs.first.inner_text()
            control = controls[0]
            prior = control.input_value()
            next_value = "75" if prior != "75" else "25"
            if control.get_attribute("type") == "range":
                control.evaluate("(el, value) => { Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(el, value); el.dispatchEvent(new Event('input', {bubbles: true})); el.dispatchEvent(new Event('change', {bubbles: true})); }", next_value)
            else:
                control.fill(next_value, timeout=1000)
            page.wait_for_timeout(100)
            after = outputs.first.inner_text()
            passed = bool(before != after)
            record_evidence(
                req_id="calculator",
                locator="output display",
                initial_state=before,
                action=f"update calculator input to {next_value}",
                expected_state="calculator live output changes",
                observed_state=after,
                passed=passed,
                error="Calculator output does not change after input." if not passed else None,
            )

    # 8. Accordion / FAQ
    if "accordion" in requested or re.search(r"\b(accordion|expandable faq)\b", brief_text):
        required_count += 1
        tested_count += 1
        details = [(item, summary) for item in page.locator("details").all()
                   for summary in _visible_interactive_controls(item.locator("summary"))]
        triggers = _visible_interactive_controls(page.locator('[aria-expanded="false"]'))
        if details:
            item, summary = details[0]
            summary.click(timeout=1000)
            page.wait_for_timeout(100)
            is_open = item.get_attribute("open") is not None
            record_evidence(
                req_id="accordion",
                locator="details summary",
                initial_state="closed (open attribute absent)",
                action="click details summary",
                expected_state="details has 'open' attribute",
                observed_state=f"open={is_open}",
                passed=is_open,
                error="Accordion does not expand." if not is_open else None,
            )
        elif triggers:
            trigger = triggers[0]
            trigger.click(timeout=1000)
            page.wait_for_timeout(100)
            is_expanded = trigger.get_attribute("aria-expanded") == "true"
            record_evidence(
                req_id="accordion",
                locator='[aria-expanded="false"]',
                initial_state="aria-expanded='false'",
                action="click accordion trigger",
                expected_state="aria-expanded becomes 'true'",
                observed_state=f"aria-expanded='{trigger.get_attribute('aria-expanded')}'",
                passed=is_expanded,
                error="Accordion does not expand." if not is_expanded else None,
            )
        else:
            record_evidence(
                req_id="accordion",
                locator="details or [aria-expanded]",
                initial_state=None,
                action="locate accordion elements in DOM",
                expected_state="details or [aria-expanded] present in DOM",
                observed_state="none found",
                passed=False,
                error="Requested accordion is missing.",
            )

    # 9. Carousel
    if "carousel" in requested or re.search(r"\b(carousel|slider with arrows|slideshow)\b", brief_text):
        required_count += 1
        tested_count += 1
        next_button = _first_interactive_control(page.get_by_role("button", name=re.compile(r"next|advance|right arrow", re.I)))
        slides = page.locator('[aria-roledescription="slide"], [data-slide], [class*="slide" i]:visible')
        if not next_button or not slides.count():
            record_evidence(
                req_id="carousel",
                locator="carousel next button / slides",
                initial_state=None,
                action="locate carousel controls and slides in DOM",
                expected_state="next button and slide elements present in DOM",
                observed_state=f"next_button={bool(next_button)}, slides={slides.count()}",
                passed=False,
                error="Requested carousel is missing a next control or slides.",
            )
        else:
            before = [(s.is_visible(), s.inner_text()) for s in slides.all()[:5]]
            next_button.click(timeout=1000)
            page.wait_for_timeout(150)
            after = [(s.is_visible(), s.inner_text()) for s in slides.all()[:5]]
            passed = (before != after)
            record_evidence(
                req_id="carousel",
                locator="carousel slides",
                initial_state=before,
                action="click carousel next button",
                expected_state="active/visible slide advances",
                observed_state=after,
                passed=passed,
                error="Carousel next control does not change the visible slide." if not passed else None,
            )

    # 10. Form Validation
    if "contact_form" in requested or re.search(r"\b(contact form|signup form|booking form|reservation form)\b", brief_text):
        required_count += 1
        tested_count += 1
        form = _first_interactive_control(page.locator("form"))
        if not form:
            record_evidence(
                req_id="contact_form",
                locator="form",
                initial_state=None,
                action="locate form in DOM",
                expected_state="form present in DOM",
                observed_state="no form found",
                passed=False,
                error="Requested form is missing.",
            )
        else:
            required = _visible_interactive_controls(form.locator("input[required], textarea[required]"))
            initially_invalid = not form.evaluate("el => el.checkValidity()") if required else True
            if not required or not initially_invalid:
                record_evidence(
                    req_id="contact_form",
                    locator="form input[required]",
                    initial_state="checkValidity() == true on empty form",
                    action="verify form validation constraints on empty submit",
                    expected_state="empty required form fails validity check",
                    observed_state=f"required_fields={len(required)}, valid_when_empty={not initially_invalid}",
                    passed=False,
                    error="Form does not reject empty required fields.",
                )
            else:
                for field in required:
                    field_type = field.get_attribute("type") or "text"
                    if field_type not in {"checkbox", "radio", "hidden"}:
                        field.fill("test@example.com" if field_type == "email" else "Test user", timeout=1000)
                finally_valid = form.evaluate("el => el.checkValidity()")
                record_evidence(
                    req_id="contact_form",
                    locator="form fields",
                    initial_state="initially invalid when required fields empty",
                    action="fill valid test data into required fields",
                    expected_state="form checkValidity() becomes true",
                    observed_state=f"checkValidity={finally_valid}",
                    passed=finally_valid,
                    error="Form rejects valid required fields." if not finally_valid else None,
                )

    if page.evaluate("() => document.documentElement.scrollWidth > window.innerWidth + 2"):
        failures.append("[Interaction Error] Page has horizontal overflow at the checked viewport.")

    for anchor in _visible_interactive_controls(page.locator('a[href^="#"]')):
        href = anchor.get_attribute("href")
        if href and len(href) > 1 and page.locator(f'[id="{href[1:]}"]').count() == 0:
            failures.append(f"[Interaction Error] CTA target {href} does not exist.")

    return evidence_list, failures, tested_count, required_count


def _has_requested_motion(brief: dict) -> bool:
    return bool((brief.get('requirement_manifest') or {}).get('motion_constraints')) or bool(re.search(
        r"\b(?:scroll(?:ing)?\s+(?:text\s+)?reveals?|parallax|horizontal scroll|sticky story|text reveals?|micro.interactions?|animat\w*)\b",
        str(brief.get('original_prompt', '')), re.I))


def _check_motion_browser(page, browser, url: str, workspace_dir: Path, brief_text: str) -> List[str]:
    """Exercise explicitly requested motion in the browser and save behavioral evidence."""
    try:
        brief = json.loads(brief_text)
    except (TypeError, ValueError):
        brief = {}
    if not _has_requested_motion(brief):
        return []
    specs = [spec for spec in brief.get("motion_plan", []) if isinstance(spec, dict) and spec.get("type")]
    if not specs:
        return ["[Motion Runtime Error] Requested motion has no typed motion plan for browser verification."]
    from evaluation.motion_benchmark import evaluate_motion_page
    report = evaluate_motion_page(page, motion_specs=specs)
    (workspace_dir / "motion_runtime_evidence.json").write_text(
        json.dumps(report.to_dict(), indent=2), encoding="utf-8"
    )
    failures = []
    for name, result in report.behavioral_results.items():
        if not result.passed:
            failures.append(f"[Motion Runtime Error] {name}: {'; '.join(result.errors) or 'behavior failed'}")
    if report.performance_result and not report.performance_result.passed:
        failures.extend(f"[Motion Runtime Error] {issue}" for issue in report.performance_result.violations)
    if not report.behavioral_results:
        failures.append("[Motion Runtime Error] No requested motion family was tested.")
    if not report.passed and not failures:
        failures.append("[Motion Runtime Error] Motion performance checks did not pass.")
    return failures


def _check_three_d_browser(page, browser, url: str, workspace_dir: Path, brief_text: str) -> List[str]:
    """Verify the scene actually renders and record a short browser evidence timeline."""
    from evaluation.three_d_performance_validator import is_three_d_requested
    if not is_three_d_requested(brief_text):
        return []
    from io import BytesIO
    from PIL import Image, ImageStat

    failures: List[str] = []
    try:
        brief_data = json.loads(brief_text)
    except (ValueError, TypeError):
        brief_data = {}
    motion_requested = bool(brief_data.get("motion_plan")) or bool(re.search(
        r"\b(animat\w*|motion|rotat\w*|spin\w*|orbit\w*)\b",
        str(brief_data.get("original_prompt", brief_text)), re.I,
    ))
    evidence: Dict[str, Any] = {"desktop": {}, "mobile": {}, "reduced_motion": {}, "fallback": {}}
    css_visible_js = """() => [...document.querySelectorAll('*')].some(parent => {
        const p = getComputedStyle(parent), r = parent.getBoundingClientRect();
        if (r.width < 80 || r.height < 80 || p.transformStyle !== 'preserve-3d') return false;
        return [...parent.querySelectorAll('*')].some(child => {
            const c = getComputedStyle(child), box = child.getBoundingClientRect();
            return box.width > 0 && box.height > 0 && c.transform !== 'none';
        });
    })"""
    canvas = page.locator("canvas:visible").first
    has_canvas = canvas.count() > 0
    if has_canvas:
        try:
            state = canvas.evaluate("""el => {
                const gl = el.getContext('webgl2') || el.getContext('webgl');
                const r = el.getBoundingClientRect();
                return {width:r.width,height:r.height,webgl:!!gl,lost:gl ? gl.isContextLost() : null,
                    error:gl ? gl.getError() : null};
            }""")
            evidence["desktop"].update(state)
            if not state["webgl"] or state["lost"] or state["error"]:
                failures.append("[3D Runtime Error] WebGL context unavailable, lost, or returned an error.")
            if state["width"] < 80 or state["height"] < 80:
                failures.append("[3D Runtime Error] 3D canvas is too small to be visible.")
            image = Image.open(BytesIO(canvas.screenshot())).convert("RGB")
            variance = max(ImageStat.Stat(image.resize((32, 32))).var)
            evidence["desktop"]["pixel_variance"] = round(variance, 3)
            if variance < 2.0:
                failures.append("[3D Runtime Error] Canvas rendered no discernible scene pixels.")
            first_frame = canvas.screenshot()
            page.wait_for_timeout(500)
            second_frame = canvas.screenshot()
            first_path = workspace_dir / "three_d_motion_0.png"
            second_path = workspace_dir / "three_d_motion_500.png"
            first_path.write_bytes(first_frame)
            second_path.write_bytes(second_frame)
            evidence["desktop"]["motion_samples_ms"] = [0, 500]
            evidence["desktop"]["motion_frame_paths"] = [str(first_path), str(second_path)]
            evidence["desktop"]["frames_differ"] = first_frame != second_frame
            if motion_requested and first_frame == second_frame:
                failures.append("[3D Runtime Error] Requested 3D motion produced identical sampled frames.")
        except Exception as exc:
            failures.append(f"[3D Runtime Error] Could not inspect rendered canvas: {exc}")
    else:
        css_scene = page.evaluate(css_visible_js)
        evidence["desktop"]["css_scene_visible"] = css_scene
        if not css_scene:
            failures.append("[3D Runtime Error] No visible WebGL canvas or transformed CSS 3D scene.")

    mobile = browser.new_page(viewport={"width": 390, "height": 844})
    try:
        mobile.goto(url, wait_until="domcontentloaded", timeout=12000)
        mobile.wait_for_timeout(400)
        visible = mobile.locator("canvas:visible").count() > 0 if has_canvas else bool(mobile.evaluate(css_visible_js))
        evidence["mobile"]["scene_visible"] = visible
        if not visible:
            failures.append("[3D Runtime Error] 3D scene is not visible on mobile.")
    finally:
        mobile.close()

    reduced = browser.new_page(reduced_motion="reduce", viewport={"width": 1280, "height": 900})
    try:
        reduced.goto(url, wait_until="domcontentloaded", timeout=12000)
        reduced.wait_for_timeout(400)
        reduced_visible = reduced.locator("canvas:visible").count() > 0 if has_canvas else bool(reduced.evaluate(css_visible_js))
        evidence["reduced_motion"]["scene_visible"] = reduced_visible
        if not reduced_visible:
            failures.append("[3D Runtime Error] 3D scene disappears with reduced motion enabled.")
        if reduced_visible and motion_requested:
            reduced_target = reduced.locator("canvas:visible").first if has_canvas else reduced.locator("body")
            reduced_first = reduced_target.screenshot()
            reduced.wait_for_timeout(500)
            reduced_second = reduced_target.screenshot()
            evidence["reduced_motion"]["frames_differ"] = reduced_first != reduced_second
            if reduced_first != reduced_second:
                failures.append("[3D Runtime Error] Requested reduced-motion mode still animates the 3D scene.")
    finally:
        reduced.close()

    if has_canvas:
        fallback_query = """() => [...document.querySelectorAll('[data-webgl-fallback], [data-3d-fallback]')].some(el => {
            const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0;
        })"""
        fallback = browser.new_page()
        try:
            fallback.add_init_script("""(() => {
                const original = HTMLCanvasElement.prototype.getContext;
                HTMLCanvasElement.prototype.getContext = function(kind, ...args) {
                    if (/^(webgl|webgl2|experimental-webgl)$/.test(kind)) return null;
                    return original.call(this, kind, ...args);
                };
            })()""")
            fallback.goto(url, wait_until="domcontentloaded", timeout=12000)
            fallback.wait_for_timeout(500)
            fallback_visible = fallback.evaluate(fallback_query)
            evidence["fallback"]["visible_without_webgl"] = fallback_visible
            if not fallback_visible:
                failures.append("[3D Runtime Error] No visible fallback when WebGL is unavailable.")
        finally:
            fallback.close()
        loss_page = browser.new_page()
        try:
            loss_page.goto(url, wait_until="domcontentloaded", timeout=12000)
            loss_page.wait_for_timeout(400)
            lost = loss_page.evaluate("""() => {
                const canvas = document.querySelector('canvas');
                if (!canvas) return false;
                const gl = canvas.getContext('webgl2') || canvas.getContext('webgl');
                const ext = gl && gl.getExtension('WEBGL_lose_context');
                if (!ext) return false;
                ext.loseContext(); return true;
            }""")
            loss_page.wait_for_timeout(350)
            loss_fallback = loss_page.evaluate(fallback_query)
            evidence["fallback"]["context_loss_triggered"] = lost
            evidence["fallback"]["visible_after_context_loss"] = loss_fallback
            if not lost or not loss_fallback:
                failures.append("[3D Runtime Error] WebGL context loss did not show the fallback.")
        finally:
            loss_page.close()
    (workspace_dir / "three_d_runtime_evidence.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    return failures


def _run_runtime_accessibility_eval(
    page: Any,
    browser: Any,
    url: str,
    workspace_dir: Path,
) -> Tuple[List[str], List[str], Dict[str, Any]]:
    """
    Authoritative multi-layer browser runtime accessibility evaluation:
    1. Computed-style contrast checking on live rendered text nodes (WCAG SC 1.4.3 AA / 1.4.6 AAA)
    2. Keyboard operability and visible focus indicator verification (WCAG SC 2.1.1 / 2.4.7)
    3. Target sizes verification (WCAG SC 2.5.8 minimum target size >= 24x24px)
    4. Reflow / 400% zoom emulation at 320px viewport (WCAG SC 1.4.10)
    5. Live accessibility tree snapshot verification (interactive nodes must have accessible names)
    6. Runtime DOM duplicate ID detection (WCAG SC 4.1.1)
    7. Reduced-motion runtime behavior verification (WCAG SC 2.3.3)
    Returns: (errors, warnings, evidence_dict)
    """
    errors: List[str] = []
    warnings: List[str] = []
    evidence: Dict[str, Any] = {
        "contrast_checks": [],
        "focus_checks": [],
        "target_size_checks": [],
        "reflow_320px": {},
        "duplicate_ids": [],
        "a11y_tree_checks": {},
        "reduced_motion": {},
    }

    try:
        # Layer 1: Computed-Style Color Contrast on live rendered text
        contrast_js = """() => {
            function parseColor(value) {
                if (value === 'transparent') return [0, 0, 0, 0];
                const m = value.match(/^rgba?\\(\\s*([\\d.]+)\\s*,\\s*([\\d.]+)\\s*,\\s*([\\d.]+)\\s*(?:,\\s*([\\d.]+)\\s*)?\\)$/i);
                if (!m) return null;
                const color = [Number(m[1]), Number(m[2]), Number(m[3]), m[4] === undefined ? 1 : Number(m[4])];
                return color.every(Number.isFinite) && color[3] >= 0 && color[3] <= 1 ? color : null;
            }
            function over(top, bottom) {
                return top.slice(0, 3).map((v, i) => v * top[3] + bottom[i] * (1 - top[3]));
            }
            function effectiveBackground(el) {
                const layers = [];
                for (let node = el; node; node = node.parentElement) {
                    const style = getComputedStyle(node);
                    if (style.backgroundImage !== 'none' || Number(style.opacity) !== 1 ||
                        style.mixBlendMode !== 'normal' || style.filter !== 'none' || style.backdropFilter !== 'none') {
                        return {reason: 'background image, blend mode, filter, or opacity'};
                    }
                    const layer = parseColor(style.backgroundColor);
                    if (!layer) return {reason: 'unsupported background color'};
                    layers.push(layer);
                }
                // The browser's default canvas is white. Composite from root to text.
                let bg = [255, 255, 255];
                for (const layer of layers.reverse()) bg = over(layer, bg);
                return {color: bg};
            }
            function lum([r, g, b]) {
                const a = [r, g, b].map(v => {
                    v /= 255;
                    return v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
                });
                return a[0] * 0.2126 + a[1] * 0.7152 + a[2] * 0.0722;
            }
            function contrastRatio(fg, bg) {
                const l1 = lum(fg);
                const l2 = lum(bg);
                const lighter = Math.max(l1, l2);
                const darker = Math.min(l1, l2);
                return (lighter + 0.05) / (darker + 0.05);
            }
            const items = [];
            const elements = document.querySelectorAll('h1, h2, h3, h4, h5, h6, p, span, a, button, label, input, li');
            for (const el of elements) {
                const r = el.getBoundingClientRect();
                if (r.width === 0 || r.height === 0 || window.getComputedStyle(el).display === 'none' || window.getComputedStyle(el).visibility === 'hidden') {
                    continue;
                }
                const text = el.innerText ? el.innerText.trim() : '';
                if (!text || text.length < 2) continue;

                const style = window.getComputedStyle(el);
                const fg = style.color;
                const background = effectiveBackground(el);
                const foreground = parseColor(fg);
                const verified = Boolean(background.color && foreground);
                const bg = background.color ? `rgb(${background.color.map(v => Math.round(v)).join(', ')})` : 'unresolved';
                const ratio = verified ? contrastRatio(over(foreground, background.color), background.color) : null;

                const fontSize = parseFloat(style.fontSize);
                const fontWeight = parseInt(style.fontWeight) || 400;
                const isLarge = fontSize >= 24 || (fontSize >= 18.66 && fontWeight >= 700);
                const minRatio = isLarge ? 3.0 : 4.5;

                items.push({
                    tag: el.tagName.toLowerCase(),
                    text: text.slice(0, 30),
                    fg,
                    bg,
                    verified,
                    reason: verified ? null : (background.reason || 'unsupported foreground color'),
                    ratio: verified ? Math.round(ratio * 100) / 100 : null,
                    minRatio,
                    passesAA: verified ? ratio >= minRatio : null,
                    passesAAA: verified ? ratio >= (isLarge ? 4.5 : 7.0) : null,
                });
                if (items.length >= 25) break;
            }
            return items;
        }"""
        contrast_results = page.evaluate(contrast_js)
        evidence["contrast_checks"] = contrast_results
        for res in contrast_results:
            if res.get("verified") is False:
                warnings.append(f"[A11y Runtime Warning] Text contrast unverified on <{res['tag']}> \"{res['text']}\": {res['reason']}.")
            elif not res.get("passesAA"):
                errors.append(
                    f"[A11y Runtime Error] Low computed text contrast {res['ratio']}:1 (minimum required: {res['minRatio']}:1) "
                    f"on <{res['tag']}> \"{res['text']}\" (foreground {res['fg']}, background {res['bg']})."
                )
            elif not res.get("passesAAA"):
                warnings.append(
                    f"[A11y Runtime Warning] Computed text contrast {res['ratio']}:1 on <{res['tag']}> \"{res['text']}\" "
                    f"meets AA (4.5:1) but falls below AAA (7.0:1)."
                )

        # Layer 2: Keyboard Operability & Visible Focus Ring (WCAG SC 2.1.1 / 2.4.7)
        focus_js = """() => {
            const isInteractive = __VISIBLE_INTERACTIVE__;
            const focusables = Array.from(document.querySelectorAll('button, a[href], input, select, textarea, [tabindex="0"]'))
                .filter(isInteractive);
            const checks = [];
            for (const el of focusables.slice(0, 8)) {
                const prevBorder = window.getComputedStyle(el).borderColor;
                el.focus();
                const style = window.getComputedStyle(el);
                const hasOutline = style.outlineStyle !== 'none' && parseFloat(style.outlineWidth) > 0;
                const hasBoxShadow = Boolean(style.boxShadow && style.boxShadow !== 'none');
                const hasBorderChange = style.borderColor !== prevBorder;
                const visibleFocus = hasOutline || hasBoxShadow || hasBorderChange;
                checks.push({
                    tag: el.tagName.toLowerCase(),
                    text: (el.innerText || el.getAttribute('aria-label') || '').trim().slice(0, 25),
                    visibleFocus,
                    outlineStyle: style.outlineStyle,
                    outlineWidth: style.outlineWidth,
                    hasBoxShadow,
                });
            }
            return checks;
        }""".replace("__VISIBLE_INTERACTIVE__", VISIBLE_INTERACTIVE_JS)
        focus_checks = page.evaluate(focus_js)
        evidence["focus_checks"] = focus_checks
        for fc in focus_checks:
            if not fc.get("visibleFocus"):
                errors.append(
                    f"[A11y Runtime Error] Interactive element <{fc['tag']}> \"{fc['text']}\" lacks visible focus indicator "
                    f"(outline is {fc['outlineStyle']} with no replacement box-shadow or focus ring, violating WCAG SC 2.4.7)."
                )

        # Test tab key navigation: ensure tab advances focus
        try:
            page.keyboard.press("Tab")
            active_tag = page.evaluate("() => document.activeElement ? document.activeElement.tagName.toLowerCase() : null")
            evidence["keyboard_active_after_tab"] = active_tag
        except Exception:
            pass

        # Layer 3: Minimum Target Size (WCAG SC 2.5.8 Target Size - Minimum 24x24px)
        target_size_js = """() => {
            const isInteractive = __VISIBLE_INTERACTIVE__;
            const targets = Array.from(document.querySelectorAll('button, [role="button"], input[type="button"], input[type="submit"]'))
                .filter(isInteractive);
            const checks = [];
            for (const el of targets.slice(0, 10)) {
                const r = el.getBoundingClientRect();
                const text = (el.innerText || el.getAttribute('aria-label') || '').trim().slice(0, 25);
                const passes = r.width >= 24 && r.height >= 24;
                checks.push({
                    tag: el.tagName.toLowerCase(),
                    text,
                    width: Math.round(r.width * 10) / 10,
                    height: Math.round(r.height * 10) / 10,
                    passes,
                });
            }
            return checks;
        }""".replace("__VISIBLE_INTERACTIVE__", VISIBLE_INTERACTIVE_JS)
        target_size_checks = page.evaluate(target_size_js)
        evidence["target_size_checks"] = target_size_checks
        for tc in target_size_checks:
            if not tc.get("passes"):
                errors.append(
                    f"[A11y Runtime Error] Interactive target <{tc['tag']}> \"{tc['text']}\" bounding box is "
                    f"{tc['width']}x{tc['height']}px, below WCAG SC 2.5.8 minimum target size of 24x24px."
                )

        # Layer 4: Reflow / 400% Zoom Emulation at 320px Viewport (WCAG SC 1.4.10)
        page.set_viewport_size({"width": 320, "height": 568})
        page.wait_for_timeout(200)
        has_320_overflow = bool(page.evaluate("() => document.documentElement.scrollWidth > window.innerWidth + 2"))
        evidence["reflow_320px"] = {
            "tested_viewport_width": 320,
            "has_horizontal_overflow": has_320_overflow,
            "passed": not has_320_overflow,
        }
        if has_320_overflow:
            errors.append(
                "[A11y Runtime Error] Page fails WCAG SC 1.4.10 Reflow: horizontal overflow detected at 320px viewport width (equivalent to 400% zoom)."
            )
        page.set_viewport_size({"width": 1280, "height": 900})

        # Layer 5: Live DOM Duplicate IDs (WCAG SC 4.1.1)
        dup_ids = page.evaluate("""() => {
            const allIds = Array.from(document.querySelectorAll('[id]')).map(el => el.id).filter(Boolean);
            const seen = new Set();
            const dups = [];
            for (const id of allIds) {
                if (seen.has(id)) dups.push(id);
                seen.add(id);
            }
            return Array.from(new Set(dups));
        }""")
        evidence["duplicate_ids"] = dup_ids
        for dup in dup_ids:
            errors.append(f"[A11y Runtime Error] Live DOM contains duplicate element id '{dup}' violating WCAG SC 4.1.1.")

        # Layer 6: Accessibility Tree Snapshot Verification
        try:
            snapshot = page.accessibility.snapshot()
            if snapshot:
                missing_names = []
                def traverse(node):
                    role = node.get("role", "")
                    name = node.get("name", "")
                    if role in ("button", "link", "checkbox", "radio", "textbox", "combobox"):
                        if not name or not name.strip():
                            missing_names.append(role)
                    for child in node.get("children", []):
                        traverse(child)
                traverse(snapshot)
                evidence["a11y_tree_checks"] = {
                    "missing_names_count": len(missing_names),
                    "missing_roles": missing_names[:5],
                    "passed": len(missing_names) == 0,
                }
                for mr in missing_names[:3]:
                    errors.append(f"[A11y Runtime Error] Accessibility tree node role=\"{mr}\" lacks an accessible name.")
        except Exception as snap_err:
            warnings.append(f"[A11y Runtime Warning] Accessibility snapshot inspection skipped: {snap_err}")

        # Layer 7: Reduced-Motion Runtime Verification (WCAG SC 2.3.3)
        try:
            reduced_page = browser.new_page(reduced_motion="reduce", viewport={"width": 1280, "height": 900})
            try:
                reduced_page.goto(url, wait_until="domcontentloaded", timeout=10000)
                reduced_page.wait_for_timeout(300)
                prefers_reduced = bool(reduced_page.evaluate("() => window.matchMedia('(prefers-reduced-motion: reduce)').matches"))
                evidence["reduced_motion"] = {
                    "media_query_matched": prefers_reduced,
                    "passed": prefers_reduced,
                }
                if not prefers_reduced:
                    errors.append("[A11y Runtime Error] Runtime prefers-reduced-motion emulation was not honored by the browser session.")
            finally:
                reduced_page.close()
        except Exception as rm_err:
            warnings.append(f"[A11y Runtime Warning] Reduced-motion runtime test note: {rm_err}")

    except Exception as exc:
        errors.append(f"[A11y Runtime Error] Browser accessibility runtime evaluation encountered an exception: {exc}")

    try:
        (workspace_dir / "accessibility_runtime_evidence.json").write_text(
            json.dumps(evidence, indent=2), encoding="utf-8"
        )
    except Exception:
        pass

    return errors, warnings, evidence


class BrowserRuntimeCheckResult(tuple):
    """
    4-tuple backward compatible return type for run_browser_runtime_check.
    Unpacks as (runtime_passed, preview_running, errors, saved_screenshot)
    while carrying rich structured interaction and accessibility evidence attributes.
    """
    runtime_passed: bool
    preview_running: bool
    errors: List[str]
    saved_screenshot: Optional[Path]
    interactions_tested: int
    interactions_required: int
    interaction_evidence: List[InteractionEvidence]
    interaction_errors: List[str]

    def __new__(
        cls,
        runtime_passed: bool,
        preview_running: bool,
        errors: List[str],
        saved_screenshot: Optional[Path],
        interactions_tested: int = 0,
        interactions_required: int = 0,
        interaction_evidence: Optional[List[InteractionEvidence]] = None,
        interaction_errors: Optional[List[str]] = None,
    ):
        instance = super().__new__(cls, (runtime_passed, preview_running, errors, saved_screenshot))
        instance.runtime_passed = runtime_passed
        instance.preview_running = preview_running
        instance.errors = errors
        instance.saved_screenshot = saved_screenshot
        instance.interactions_tested = interactions_tested
        instance.interactions_required = interactions_required
        instance.interaction_evidence = interaction_evidence or []
        instance.interaction_errors = interaction_errors or []
        return instance


def check_broken_rendered_images(page) -> List[str]:
    """A mounted page with failed product/hero images is not a valid preview."""
    broken = page.evaluate("""() => [...document.images].filter(image => {
        const r=image.getBoundingClientRect(),s=getComputedStyle(image);
        return image.complete && image.naturalWidth === 0 && r.width > 0 && r.height > 0
            && s.display !== 'none' && s.visibility !== 'hidden';
    }).map(image => ({src:(image.currentSrc || image.src).slice(0,200),alt:image.alt}))""")
    return [f"[Image Runtime Error] Failed image '{item['alt']}' at {item['src']}" for item in broken]


def run_browser_runtime_check(
    workspace_dir: Path,
    port: int = 0,
    timeout_s: int = 12,
    capture_screenshot: bool = True,
    screenshot_path: Optional[Path] = None,
) -> BrowserRuntimeCheckResult:
    """
    Authoritative gates 3 & 4 & 5 (Browser Runtime):
    - Starts/reuses Vite preview server (preview_running)
    - Loads page in Playwright headless Chromium
    - Monitors unhandled pageerror and console.error events
    - Evaluates #root DOM mount verification in live DOM
    - Tests brief-required interactions with explicit InteractionEvidence (tested == required AND passed == required)
    - Evaluates multi-layer runtime accessibility (contrast, visible focus, target size, reflow at 320px)
    - Captures screenshot.webp
    Returns: BrowserRuntimeCheckResult (unpacks as 4-tuple: runtime_passed, preview_running, errors, saved_screenshot_path)
    """
    _ensure_project_configs(workspace_dir)
    if port == 0:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
    errors: List[str] = []
    preview_running = False
    vite_proc = None
    url = f"http://127.0.0.1:{port}"
    saved_ss = None
    interaction_evidence: List[InteractionEvidence] = []
    interactions_tested = 0
    interactions_required = 0

    env = os.environ.copy()
    env["PORT"] = str(port)

    try:
        has_dist = (workspace_dir / "dist" / "index.html").exists()
        cmd = [
            "npx", "vite", "preview", "--port", str(port), "--strictPort", "--host", "127.0.0.1"
        ] if has_dist else [
            "npx", "vite", "--port", str(port), "--strictPort", "--host", "127.0.0.1"
        ]

        vite_proc = subprocess.Popen(
            cmd,
            cwd=str(workspace_dir),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=env,
            shell=(os.name == "nt"),
        )

        for _ in range(25):
            time.sleep(0.3)
            if vite_proc.poll() is not None:
                errors.append(f"[Runtime Error] Vite process exited prematurely (exit code {vite_proc.returncode}).")
                return BrowserRuntimeCheckResult(
                    runtime_passed=False,
                    preview_running=False,
                    errors=errors,
                    saved_screenshot=None,
                    interactions_tested=0,
                    interactions_required=0,
                    interaction_evidence=[],
                    interaction_errors=[],
                )
            try:
                with urllib.request.urlopen(url, timeout=1):
                    preview_running = True
                    break
            except Exception:
                continue

        if not preview_running:
            errors.append(f"[Runtime Error] Vite server did not become responsive on port {port} within timeout.")
            return BrowserRuntimeCheckResult(
                runtime_passed=False,
                preview_running=False,
                errors=errors,
                saved_screenshot=None,
                interactions_tested=0,
                interactions_required=0,
                interaction_evidence=[],
                interaction_errors=[],
            )

        try:
            from playwright.sync_api import sync_playwright
            runtime_exceptions: List[str] = []

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 1280, "height": 900})

                def on_page_error(err):
                    runtime_exceptions.append(f"[Browser Exception] {err}")

                def on_console(msg):
                    if msg.type == "error":
                        runtime_exceptions.append(f"[Console Error] {msg.text}")

                page.on("pageerror", on_page_error)
                page.on("console", on_console)

                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=timeout_s * 1000)
                    page.wait_for_timeout(400)
                except Exception as nav_err:
                    runtime_exceptions.append(f"[Navigation Error] {nav_err}")

                root_mounted = False
                try:
                    root_mounted = bool(page.evaluate("""() => {
                        const r = document.getElementById('root');
                        return !!(r && (r.children.length > 0 || (r.innerText && r.innerText.trim().length > 0)));
                    }"""))
                except Exception as eval_err:
                    runtime_exceptions.append(f"[DOM Evaluation Error] {eval_err}")

                if not root_mounted:
                    runtime_exceptions.append("[Runtime Error] Root container (#root) mounted 0 rendered child nodes.")
                runtime_exceptions.extend(check_broken_rendered_images(page))

                # Gate 4b & 5: Exercise controls requested in the saved content brief and evaluate a11y.
                try:
                    brief_text = ""
                    brief_path = workspace_dir / "content_brief.json"
                    if brief_path.is_file():
                        brief_text = brief_path.read_text(encoding="utf-8", errors="replace").lower()

                    # 1. Brief-required interactive behaviors
                    brief_ev, brief_fails, brief_tested, brief_req = _check_brief_interactions(page, brief_text)
                    runtime_exceptions.extend(brief_fails)
                    interaction_evidence.extend(brief_ev)
                    interactions_tested += brief_tested
                    interactions_required += brief_req

                    # 2. Motion and 3D browser checks
                    runtime_exceptions.extend(_check_motion_browser(page, browser, url, workspace_dir, brief_text))
                    runtime_exceptions.extend(_check_three_d_browser(page, browser, url, workspace_dir, brief_text))

                    # 3. Multi-layer live browser accessibility evaluation (contrast, visible focus, target size, reflow at 320px)
                    a11y_errs, a11y_warns, a11y_ev = _run_runtime_accessibility_eval(page, browser, url, workspace_dir)
                    runtime_exceptions.extend(a11y_errs)

                    # 4. Icon-only buttons must have accessible name
                    for button in _visible_interactive_controls(page.locator("button")):
                        if (button.inner_text().strip() or button.get_attribute("aria-label")
                                or button.get_attribute("aria-labelledby") or button.get_attribute("title")):
                            continue
                        runtime_exceptions.append("[Interaction Error] Visible icon-only button has no accessible name.")
                        break

                    # 5. Mobile viewport overflow check
                    page.set_viewport_size({"width": 390, "height": 844})
                    if page.evaluate("() => document.documentElement.scrollWidth > window.innerWidth + 2"):
                        runtime_exceptions.append("[Interaction Error] Page has horizontal overflow on mobile.")
                    runtime_exceptions.extend(check_mobile_control_bounds(page))
                    page.set_viewport_size({"width": 1280, "height": 900})

                    # 6. Generic interactive controls - do NOT swallow exceptions
                    interactive_nodes = _visible_interactive_controls(page.locator("button, [role='button'], a[href^='#'], input:not([type='hidden'])"))
                    for idx, elem in enumerate(interactive_nodes[:4]):
                        tag = elem.evaluate("el => el.tagName.toLowerCase()")
                        role = elem.get_attribute("role") or tag
                        text = (elem.inner_text() or elem.get_attribute("aria-label") or f"control-{idx}").strip()[:30]
                        interactions_tested += 1
                        try:
                            elem.hover(timeout=500)
                            elem.click(timeout=500)
                            page.wait_for_timeout(100)
                            interaction_evidence.append(InteractionEvidence(
                                requirement_id=f"generic_control_{idx}",
                                locator=f"{tag}[role={role}]",
                                initial_state="visible in DOM",
                                action="hover and click",
                                expected_state="exercised cleanly without runtime exception",
                                observed_state="interaction cleanly executed",
                                passed=True,
                                error=None,
                            ))
                        except Exception as exc:
                            err_msg = f"Generic interaction with <{tag}> '{text}' failed: {exc}"
                            runtime_exceptions.append(f"[Interaction Error] {err_msg}")
                            interaction_evidence.append(InteractionEvidence(
                                requirement_id=f"generic_control_{idx}",
                                locator=f"{tag}[role={role}]",
                                initial_state="visible in DOM",
                                action="hover and click",
                                expected_state="exercised cleanly without runtime exception",
                                observed_state=f"threw {type(exc).__name__}",
                                passed=False,
                                error=err_msg,
                            ))
                except Exception as int_err:
                    runtime_exceptions.append(f"[Interaction Error] DOM interaction evaluation failed: {int_err}")

                if capture_screenshot and screenshot_path:
                    try:
                        screenshot_path.parent.mkdir(parents=True, exist_ok=True)
                        page.screenshot(path=str(screenshot_path), type="webp")
                        saved_ss = screenshot_path
                    except Exception as ss_err:
                        print(f"[ProjectValidator] Screenshot capture note: {ss_err}")

                browser.close()

            int_errors = [e for e in runtime_exceptions if "[Interaction Error]" in e]
            if runtime_exceptions:
                errors.extend(runtime_exceptions)
                return BrowserRuntimeCheckResult(
                    runtime_passed=False,
                    preview_running=preview_running,
                    errors=errors,
                    saved_screenshot=saved_ss,
                    interactions_tested=interactions_tested,
                    interactions_required=interactions_required,
                    interaction_evidence=interaction_evidence,
                    interaction_errors=int_errors,
                )

            return BrowserRuntimeCheckResult(
                runtime_passed=True,
                preview_running=preview_running,
                errors=[],
                saved_screenshot=saved_ss,
                interactions_tested=interactions_tested,
                interactions_required=interactions_required,
                interaction_evidence=interaction_evidence,
                interaction_errors=[],
            )

        except ImportError:
            try:
                with urllib.request.urlopen(url, timeout=2) as resp:
                    body = resp.read().decode("utf-8", errors="replace")
                    if "<div id=\"root\">" in body:
                        errors.append(
                            "[Runtime Unverified] Playwright is not installed. Static container check found "
                            "<div id=\"root\">, but browser execution (React mount, console errors, page errors) "
                            "is UNVERIFIED. Static container check is reported as runtime_unverified, never passed."
                        )
                        return BrowserRuntimeCheckResult(
                            runtime_passed=False,
                            preview_running=preview_running,
                            errors=errors,
                            saved_screenshot=None,
                            interactions_tested=0,
                            interactions_required=0,
                            interaction_evidence=[],
                            interaction_errors=[],
                        )
                    else:
                        errors.append("[Runtime Error] HTML payload missing #root container.")
                        return BrowserRuntimeCheckResult(
                            runtime_passed=False,
                            preview_running=preview_running,
                            errors=errors,
                            saved_screenshot=None,
                            interactions_tested=0,
                            interactions_required=0,
                            interaction_evidence=[],
                            interaction_errors=[],
                        )
            except Exception as http_err:
                errors.append(f"[Runtime Error] Fallback HTTP verification failed: {http_err}")
                return BrowserRuntimeCheckResult(
                    runtime_passed=False,
                    preview_running=preview_running,
                    errors=errors,
                    saved_screenshot=None,
                    interactions_tested=0,
                    interactions_required=0,
                    interaction_evidence=[],
                    interaction_errors=[],
                )

    except Exception as exc:
        errors.append(f"[Runtime Error] Unexpected error during browser runtime check: {exc}")
        return BrowserRuntimeCheckResult(
            runtime_passed=False,
            preview_running=preview_running,
            errors=errors,
            saved_screenshot=None,
            interactions_tested=0,
            interactions_required=0,
            interaction_evidence=[],
            interaction_errors=[],
        )
    finally:
        if vite_proc:
            _stop_process_tree(vite_proc)


def find_fallback_components(workspace_dir: Path) -> List[str]:
    """Locate emergency section scaffolds that still need model repair."""
    components_dir = workspace_dir / "src" / "components"
    if not components_dir.is_dir():
        return []
    found = []
    for component in components_dir.rglob("*.tsx"):
        source = component.read_text(encoding="utf-8", errors="replace")
        if re.search(r'data-fallback\s*=\s*["\']true["\']', source):
            found.append(component.relative_to(workspace_dir).as_posix())
    return sorted(found)


def find_unverified_contact_files(workspace_dir: Path, original_prompt: str) -> List[str]:
    """Flag generated contact details that were absent from the site request."""
    if not original_prompt:
        return []
    components_dir = workspace_dir / "src" / "components"
    if not components_dir.is_dir():
        return []
    prompt_emails = {match.lower() for match in re.findall(
        r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}', original_prompt
    )}
    prompt_phone_digits = {
        re.sub(r'\D', '', match) for match in re.findall(
            r'(?:\+?\d{1,3}[\s.-]*)?\(?\d{3}\)?[\s.-]*\d{3}[\s.-]*\d{4}', original_prompt
        )
    }
    found = []
    for component in components_dir.rglob("*.tsx"):
        source = component.read_text(encoding="utf-8", errors="replace")
        emails = {match.lower() for match in re.findall(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}', source)}
        phones = {
            re.sub(r'\D', '', match) for match in re.findall(
                r'(?:\+?\d{1,3}[\s.-]*)?\(?\d{3}\)?[\s.-]*\d{3}[\s.-]*\d{4}', source
            )
        }
        if emails - prompt_emails or phones - prompt_phone_digits:
            found.append(component.relative_to(workspace_dir).as_posix())
    return sorted(found)


def validate_project(
    workspace_dir: Path,
    port: int = 0,
    capture_screenshot: bool = True,
    screenshot_path: Optional[Path] = None,
    event_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> ValidationResult:
    """
    Executes the authoritative 9-gate project validation sequence.

    Gate registry (GATES order):
      Gate 1  — TypecheckGate    : npm run typecheck (tsc --noEmit)
      Gate 2  — BuildGate        : npm run build (vite build)
      Gate 3  — LintGate         : Static CSS/token/import linting
      Gate 4  — ContractGate     : Structural integrity, section completeness, content provenance
      Gate 5  — AccessibilityGate: Static WCAG + runtime axe-core / contrast / keyboard / zoom
      Gate 6  — MotionGate       : Animation rule conformance + runtime motion benchmark
      Gate 7  — ThreeDGate       : 3-D performance contract (skipped when not requested)
      Gate 8  — RuntimeGate      : Preview server liveness + Playwright browser runtime check
      Gate 9  — InteractionGate  : Explicit DOM interaction evidence (tested == required)

    The UI renders whatever the backend ValidationResult schema reports; gate-count
    comments in logs must match this registry exactly.
    """
    all_errors: List[str] = []
    all_warnings: List[str] = []

    # Gate 3: Static Linting
    lint_passed, lint_errs, lint_warns = run_static_lint(workspace_dir)
    all_errors.extend(lint_errs)
    all_warnings.extend(lint_warns)

    # Gate 5: Contract & Accessibility
    contract_passed, contract_errs, contract_warns = run_contract_check(workspace_dir)
    all_errors.extend(contract_errs)
    all_warnings.extend(contract_warns)

    # A compilable emergency scaffold is still an unfinished section. Keep the
    # project repair loop active until it is replaced by generated content.
    for rel in find_fallback_components(workspace_dir):
        contract_passed = False
        all_errors.append(f"[Fallback Error] {rel}: Emergency scaffold must be replaced with a real section implementation.")

    brief_path = workspace_dir / "content_brief.json"
    if brief_path.is_file():
        try:
            original_prompt = str(json.loads(brief_path.read_text(encoding="utf-8")).get("original_prompt") or "")
        except (json.JSONDecodeError, OSError):
            original_prompt = ""
        for rel in find_unverified_contact_files(workspace_dir, original_prompt):
            contract_passed = False
            all_errors.append(f"[Content Error] {rel}: Contact details were not supplied in the original request.")
        rendering_errors = run_rendering_contract_check(workspace_dir, original_prompt)
        if rendering_errors:
            contract_passed = False
            all_errors.extend(rendering_errors)

    accessibility_passed, a11y_errs, a11y_warns = run_accessibility_check(workspace_dir)
    all_errors.extend(a11y_errs)
    all_warnings.extend(a11y_warns)

    # Gate 5c: Motion Implementation Rules (Section 5)
    motion_passed, motion_errs, motion_warns = run_motion_rules_check(workspace_dir)
    all_errors.extend(motion_errs)
    all_warnings.extend(motion_warns)

    brief_path = workspace_dir / "content_brief.json"
    brief_text = brief_path.read_text(encoding="utf-8", errors="replace") if brief_path.exists() else ""
    from evaluation.three_d_performance_validator import is_three_d_requested
    three_d_requested = is_three_d_requested(brief_text)
    three_d_passed = True
    three_d_status = "not_requested"
    if three_d_requested:
        from evaluation.three_d_performance_validator import validate_three_d_performance
        three_d_files = {
            p.relative_to(workspace_dir).as_posix(): p.read_text(encoding="utf-8", errors="replace")
            for p in (workspace_dir / "src").rglob("*") if p.is_file() and p.suffix in (".tsx", ".ts", ".jsx", ".js", ".css")
        }
        perf = validate_three_d_performance(three_d_files)
        three_d_passed = bool(perf["all_passed"])
        for name in perf["failed_checks"]:
            check = perf["scene_contract"] if name == "scene_contract" else perf["checks"][name]
            all_errors.append(f"[3D Error] Static check failed: {name}: {check['reason']}")
        three_d_status = "passed" if three_d_passed else "failed"

    # Gate 1: TypecheckGate — TypeScript Compilation
    if event_callback:
        try:
            event_callback({"type": "status", "status": "Running TypeScript checks…"})
            event_callback({"type": "log", "text": "[VALIDATION] Gate 1/9 TypecheckGate — Running TypeScript checks (npm run typecheck)…"})
        except Exception:
            pass

    typecheck_passed, ts_errs = run_project_typecheck(workspace_dir)
    all_errors.extend(ts_errs)

    # Gate 2: BuildGate — Production Bundler
    build_passed = False
    if typecheck_passed:
        if event_callback:
            try:
                event_callback({"type": "status", "status": "Running production build…"})
                event_callback({"type": "log", "text": "[VALIDATION] Gate 2/9 BuildGate — Running production build (npm run build)…"})
            except Exception:
                pass
        build_passed, b_errs = run_project_build(workspace_dir)
        all_errors.extend(b_errs)
    else:
        all_errors.append("[Build Error] Build skipped because TypeScript checks failed.")

    # Gate 8: RuntimeGate — Preview Server & Browser Runtime
    runtime_passed = False
    preview_running = False
    browser_res = None
    if build_passed:
        if event_callback:
            try:
                event_callback({"type": "status", "status": "Checking browser runtime…"})
                event_callback({"type": "log", "text": "[VALIDATION] Gate 8/9 RuntimeGate — Launching preview & browser runtime check…"})
            except Exception:
                pass
        ss_dest = screenshot_path or (workspace_dir / "screenshot.webp")
        browser_res = run_browser_runtime_check(
            workspace_dir=workspace_dir,
            port=port,
            capture_screenshot=capture_screenshot,
            screenshot_path=ss_dest,
        )
        runtime_passed, preview_running, r_errs, _ = browser_res
        all_errors.extend(r_errs)
        if preview_running and event_callback:
            try:
                event_callback({"type": "status", "status": "Preview running…"})
            except Exception:
                pass
    else:
        all_errors.append("[Runtime Error] Runtime checks skipped because build was not successful.")

    runtime_unverified = browser_res is None or any("[Runtime Unverified]" in err for err in all_errors)
    runtime_status = "runtime_unverified" if runtime_unverified else ("passed" if runtime_passed else "failed")
    three_d_static_status = three_d_status
    three_d_runtime_status = "not_requested"
    if three_d_requested:
        three_d_runtime_status = "passed" if runtime_passed else ("runtime_unverified" if runtime_unverified else "failed")
        three_d_passed = three_d_passed and runtime_passed
        three_d_status = "passed" if three_d_passed else three_d_runtime_status if three_d_static_status == "passed" else "failed"
    typecheck_status = "passed" if typecheck_passed else "failed"
    build_status = "passed" if build_passed else "failed"
    lint_status = "passed" if lint_passed else "failed"
    contract_status = "passed" if contract_passed else "failed"
    accessibility_status = "passed" if accessibility_passed else "failed"
    motion_status = "passed" if motion_passed else "failed"
    try:
        brief_record_for_motion = json.loads(brief_text)
    except (TypeError, ValueError):
        brief_record_for_motion = {}
    explicit_motion_requested = _has_requested_motion(brief_record_for_motion)
    motion_runtime_status = "not_requested"
    if explicit_motion_requested:
        motion_runtime_status = "runtime_unverified" if runtime_unverified else (
            "failed" if any("[Motion Runtime Error]" in error for error in all_errors) or not runtime_passed else "passed"
        )
        motion_passed = motion_passed and motion_runtime_status == "passed"
        motion_status = "passed" if motion_passed else "failed"
    preview_status = "passed" if preview_running else "failed"

    # Gate 5: Accessibility Gate (Static checks passed AND no runtime accessibility errors)
    a11y_runtime_errors = [e for e in all_errors if "[A11y Runtime Error]" in e]
    if a11y_runtime_errors:
        accessibility_passed = False
        accessibility_status = "failed"

    trimmed_errors = all_errors[:40]
    if len(all_errors) > 40:
        trimmed_errors.append(f"... ({len(all_errors) - 40} more errors omitted)")

    motion_failures = [e for e in all_errors if "[Motion Rule Violation]" in e or "[Motion Benchmark Failure]" in e]
    motion_plan: List[Dict[str, Any]] = []
    cb_file = workspace_dir / "content_brief.json"
    if cb_file.is_file():
        try:
            cb_data = json.loads(cb_file.read_text(encoding="utf-8"))
            raw_mp = cb_data.get("motion_plan", [])
            for item in raw_mp:
                if hasattr(item, "to_dict"):
                    motion_plan.append(item.to_dict())
                elif isinstance(item, dict):
                    motion_plan.append(item)
        except Exception:
            pass

    # Gate 4b: DOM Interaction Evidence Gate
    interaction_errors = [e for e in all_errors if "[Interaction Error]" in e]
    int_evidence = getattr(browser_res, "interaction_evidence", []) if browser_res else []
    int_tested = getattr(browser_res, "interactions_tested", 0) if browser_res else 0
    declared_interactions = (brief_record_for_motion.get("requirement_manifest") or {}).get("interaction_constraints", [])
    int_required = max(getattr(browser_res, "interactions_required", 0) if browser_res else 0, len(declared_interactions))

    if runtime_unverified:
        interaction_passed = False
        interaction_status = "unverified"
    elif len(interaction_errors) > 0:
        interaction_passed = False
        interaction_status = "failed"
    elif int_required > 0:
        passed_ev_count = sum(
            1 for e in int_evidence
            if (e.passed if hasattr(e, "passed") else (e.get("passed", False) if isinstance(e, dict) else False))
        )
        if int_tested >= int_required and passed_ev_count >= int_required and len(interaction_errors) == 0:
            interaction_passed = True
            interaction_status = "passed"
        else:
            interaction_passed = False
            interaction_status = "failed"
    elif int_required == 0:
        interaction_passed = True
        interaction_status = "not_requested"
    else:
        interaction_passed = False
        interaction_status = "failed"

    return ValidationResult(
        typecheck_passed=typecheck_passed,
        build_passed=build_passed,
        lint_passed=lint_passed,
        contract_passed=contract_passed,
        accessibility_passed=accessibility_passed,
        motion_passed=motion_passed,
        three_d_passed=three_d_passed,
        three_d_status=three_d_status,
        three_d_static_status=three_d_static_status,
        three_d_runtime_status=three_d_runtime_status,
        runtime_passed=runtime_passed,
        runtime_unverified=runtime_unverified,
        interaction_passed=interaction_passed,
        interaction_status=interaction_status,
        interaction_errors=interaction_errors,
        interactions_tested=int_tested,
        interactions_required=int_required,
        interaction_evidence=int_evidence,
        typecheck_status=typecheck_status,
        build_status=build_status,
        lint_status=lint_status,
        contract_status=contract_status,
        accessibility_status=accessibility_status,
        motion_status=motion_status,
        motion_runtime_status=motion_runtime_status,
        runtime_status=runtime_status,
        preview_status=preview_status,
        preview_running=preview_running,
        errors=trimmed_errors,
        warnings=all_warnings,
        motion_plan=motion_plan,
        motion_failures=motion_failures,
    )
