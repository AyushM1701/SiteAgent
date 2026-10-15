"""
agent/dependency_manager.py - Project Dependency Manager with Controlled Package Policy

Provides safe dependency management for the model and projects:
- Controlled package allowlist policy explicitly supporting Three.js, R3F, animation, and UI utilities
- Protection of core dependencies (react, react-dom, vite, typescript) from accidental removal
- Safe execution via SafeExecutor (non-shell, parameter-validated)
- Real-time command and status event emission
"""

import json
import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

try:
    from agent.safe_executor import SafeExecutor, safe_executor
except (ImportError, ModuleNotFoundError):
    from safe_executor import SafeExecutor, safe_executor


class PackagePolicyError(Exception):
    """Raised when a package violates the project dependency policy."""
    pass


class PackagePolicy:
    """
    Defines approved packages and immutable core dependencies for React/3D projects.
    Blueprint target ecosystem: Three.js, @react-three/fiber, @react-three/drei, motion, and UI primitives.
    """

    # Approved packages with tested default version constraints
    ALLOWED_CATALOG: Dict[str, str] = {
        # 3D & Graphics Ecosystem (Blueprint target)
        "three": "^0.170.0",
        "@types/three": "^0.170.0",
        "@react-three/fiber": "^8.17.10",
        "@react-three/drei": "^9.117.0",
        "troika-three-text": "^0.51.1",
        "gl-matrix": "^3.4.3",
        "@types/gl-matrix": "^3.4.1",
        "simplex-noise": "^4.0.3",
        "canvas-confetti": "^1.9.4",
        "@types/canvas-confetti": "^1.9.0",

        # Icons, Styling & Motion
        "lucide-react": "^0.475.0",
        "framer-motion": "^12.0.0",
        "clsx": "^2.1.1",
        "tailwind-merge": "^2.6.0",
        "class-variance-authority": "^0.7.1",

        # Core React & Tooling Ecosystem
        "react": "^19.0.0",
        "react-dom": "^19.0.0",
        "@types/react": "^19.0.10",
        "@types/react-dom": "^19.0.4",
        "typescript": "^5.7.3",
        "vite": "^6.0.0",
        "@vitejs/plugin-react": "^4.3.4",
    }

    # Core dependencies that can NEVER be removed
    PROTECTED_PACKAGES: Set[str] = {
        "react",
        "react-dom",
        "@types/react",
        "@types/react-dom",
        "typescript",
        "vite",
        "@vitejs/plugin-react",
    }

    # Packages explicitly blocked for security (e.g. arbitrary shells, backdoors)
    BLOCKED_PATTERNS: List[re.Pattern] = [
        re.compile(r"^node-pty", re.I),
        re.compile(r"^child_process", re.I),
        re.compile(r"^shelljs", re.I),
        re.compile(r"^sudo", re.I),
        re.compile(r"^express", re.I),
        re.compile(r"^nodemon", re.I),
        re.compile(r"^axios", re.I),
        re.compile(r"^request", re.I),
        re.compile(r"^http-server", re.I),
    ]

    @classmethod
    def is_package_allowed(cls, package_name: str) -> bool:
        """Returns True if package_name is in the approved catalog or matches approved @types."""
        clean = package_name.strip().lower()
        if any(p.search(clean) for p in cls.BLOCKED_PATTERNS):
            return False
        if clean in cls.ALLOWED_CATALOG:
            return True
        # Allow corresponding @types/* for any allowed package
        if clean.startswith("@types/"):
            base_pkg = clean[7:]
            if base_pkg in cls.ALLOWED_CATALOG:
                return True
        return False

    @classmethod
    def is_protected_package(cls, package_name: str) -> bool:
        """Returns True if package_name is an essential project framework dependency."""
        return package_name.strip().lower() in cls.PROTECTED_PACKAGES

    @classmethod
    def get_default_version(cls, package_name: str) -> Optional[str]:
        """Returns the recommended version string for an approved package."""
        return cls.ALLOWED_CATALOG.get(package_name.strip().lower())

    @classmethod
    def validate_install(cls, package_name: str) -> None:
        """Validates that a package is allowed to be installed."""
        clean = package_name.strip()
        if not cls.is_package_allowed(clean):
            allowed_preview = [
                "three", "@react-three/fiber", "@react-three/drei",
                "lucide-react", "framer-motion", "clsx", "tailwind-merge", "canvas-confetti"
            ]
            raise PackagePolicyError(
                f"[Package Policy Rejection] Package '{clean}' is not permitted by project policy. "
                f"Approved ecosystem includes: {', '.join(allowed_preview)}."
            )

    @classmethod
    def validate_remove(cls, package_name: str) -> None:
        """Validates that a package can be safely uninstalled."""
        clean = package_name.strip()
        if cls.is_protected_package(clean):
            raise PackagePolicyError(
                f"[Package Policy Rejection] Cannot remove core framework dependency '{clean}'."
            )


def external_imports(files: Dict[str, str]) -> Set[str]:
    """Return package roots imported by generated JS/TS source files."""
    packages: Set[str] = set()
    pattern = re.compile(r"(?:\bfrom\s*|\bimport\s*\(|\bimport\s*)['\"]([^'\"]+)['\"]")
    for path, content in files.items():
        if not path.endswith((".js", ".jsx", ".ts", ".tsx")):
            continue
        for spec in pattern.findall(content):
            if spec.startswith((".", "/")):
                continue
            packages.add("/".join(spec.split("/")[:2]) if spec.startswith("@") else spec.split("/")[0])
    return packages


def reconcile_manifest_imports(manifest: Dict[str, Any], files: Dict[str, str]) -> List[str]:
    """Declare approved imports; return policy violations for unsupported packages."""
    errors: List[str] = []
    dependencies = manifest.setdefault("dependencies", {})
    dev_dependencies = manifest.setdefault("devDependencies", {})
    for package in sorted(external_imports(files)):
        if package in dependencies or package in dev_dependencies:
            continue
        if not PackagePolicy.is_package_allowed(package):
            errors.append(f"Unsupported external import: {package}")
            continue
        version = PackagePolicy.get_default_version(package)
        if version is None:
            errors.append(f"No approved version for external import: {package}")
            continue
        dependencies[package] = version
    return errors


def ensure_runtime_packages(files: Dict[str, str], runtime_root: Path, event_callback=None) -> List[str]:
    """Install approved generated-code imports in the shared workbench runtime."""
    failures: List[str] = []
    manager = DependencyManager(runtime_root, event_callback=event_callback)
    for package in sorted(external_imports(files)):
        if package in {"react", "react-dom"}:
            continue
        if not PackagePolicy.is_package_allowed(package):
            failures.append(f"Unsupported external import: {package}")
            continue
        if (runtime_root / "node_modules" / package).exists():
            continue
        result = manager.install_package(package)
        if not result["success"]:
            failures.append(f"Could not install {package}: {result.get('output', '')[:500]}")
    return failures


class DependencyManager:
    """
    Project-scoped Dependency Manager.
    Reads and updates project dependencies with policy validation and safe execution.
    """

    def __init__(
        self,
        workspace_dir: Path,
        executor: Optional[SafeExecutor] = None,
        event_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ):
        self.workspace_dir = Path(workspace_dir).resolve()
        self.executor = executor or safe_executor
        self.event_callback = event_callback
        self.package_json_path = self.workspace_dir / "package.json"

    def _read_package_json(self) -> Dict[str, Any]:
        """Safely reads project package.json."""
        if not self.package_json_path.exists():
            return {"name": "slm-project", "private": True, "dependencies": {}, "devDependencies": {}}
        try:
            return json.loads(self.package_json_path.read_text(encoding="utf-8"))
        except Exception as e:
            raise RuntimeError(f"Could not read package.json in {self.workspace_dir}: {e}")

    def _write_package_json(self, data: Dict[str, Any]) -> None:
        """Safely writes updated package.json."""
        self.package_json_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def get_dependencies(self) -> Dict[str, Any]:
        """Returns the current dependencies, devDependencies, and combined inventory."""
        data = self._read_package_json()
        deps = data.get("dependencies", {})
        dev_deps = data.get("devDependencies", {})
        return {
            "dependencies": deps,
            "devDependencies": dev_deps,
            "all": {**deps, **dev_deps},
        }

    def install_package(
        self,
        name: str,
        version: Optional[str] = None,
        is_dev: bool = False,
    ) -> Dict[str, Any]:
        """
        Validates package against policy, executes installation via SafeExecutor,
        and records dependency state in package.json.
        """
        clean_name = name.strip()
        PackagePolicy.validate_install(clean_name)

        target_version = version or PackagePolicy.get_default_version(clean_name) or "^1.0.0"
        pkg_spec = f"{clean_name}@{target_version}"

        if self.event_callback:
            try:
                self.event_callback({
                    "type": "activity.started",
                    "activity": f"Installing {clean_name}",
                    "package": clean_name,
                    "version": target_version,
                    "status": f"Installing {clean_name}…",
                    "text": f"[Dependencies] Installing approved package: {clean_name} ({target_version})",
                })
            except Exception:
                pass

        # Execute safe installation
        install_args = ["npm", "install", pkg_spec, "--legacy-peer-deps"]
        if is_dev:
            install_args.append("--save-dev")
        else:
            install_args.append("--save")

        exec_res = self.executor.execute(
            args=install_args,
            cwd=self.workspace_dir,
            timeout_s=90.0,
            event_callback=self.event_callback,
        )

        if not exec_res.success:
            return {
                "success": False,
                "package": clean_name,
                "version": target_version,
                "is_dev": is_dev,
                "returncode": exec_res.returncode,
                "output": exec_res.stdout or exec_res.stderr,
            }

        # Record only dependencies that npm actually installed.
        data = self._read_package_json()
        target_section = "devDependencies" if is_dev else "dependencies"
        if target_section not in data:
            data[target_section] = {}
        data[target_section][clean_name] = target_version
        self._write_package_json(data)

        # Also install corresponding @types if package requires it and it exists in catalog
        types_pkg = f"@types/{clean_name}"
        if PackagePolicy.is_package_allowed(types_pkg) and types_pkg not in data.get("devDependencies", {}):
            try:
                types_ver = PackagePolicy.get_default_version(types_pkg) or target_version
                types_result = self.executor.execute(
                    args=["npm", "install", f"{types_pkg}@{types_ver}", "--save-dev", "--legacy-peer-deps"],
                    cwd=self.workspace_dir,
                    timeout_s=60.0,
                )
                if types_result.success:
                    data = self._read_package_json()
                    data.setdefault("devDependencies", {})[types_pkg] = types_ver
                    self._write_package_json(data)
            except Exception:
                pass

        return {
            "success": exec_res.success,
            "package": clean_name,
            "version": target_version,
            "is_dev": is_dev,
            "returncode": exec_res.returncode,
            "output": exec_res.stdout or exec_res.stderr,
        }

    def install_packages(
        self,
        names: List[str],
        is_dev: bool = False,
    ) -> Dict[str, Any]:
        """Installs a batch of approved packages (e.g. three, @react-three/fiber, @react-three/drei)."""
        results = []
        for n in names:
            res = self.install_package(n, is_dev=is_dev)
            results.append(res)
        all_success = all(r.get("success", False) for r in results)
        return {
            "success": all_success,
            "installed": [r["package"] for r in results if r.get("success")],
            "results": results,
        }

    def remove_package(self, name: str) -> Dict[str, Any]:
        """
        Validates that package is not core/protected, executes uninstallation via SafeExecutor,
        and removes package from package.json.
        """
        clean_name = name.strip()
        PackagePolicy.validate_remove(clean_name)

        if self.event_callback:
            try:
                self.event_callback({
                    "type": "activity.started",
                    "activity": f"Removing {clean_name}",
                    "package": clean_name,
                    "status": f"Removing {clean_name}…",
                    "text": f"[Dependencies] Removing package: {clean_name}",
                })
            except Exception:
                pass

        exec_res = self.executor.execute(
            args=["npm", "uninstall", clean_name],
            cwd=self.workspace_dir,
            timeout_s=60.0,
            event_callback=self.event_callback,
        )

        data = self._read_package_json()
        if "dependencies" in data and clean_name in data["dependencies"]:
            del data["dependencies"][clean_name]
        if "devDependencies" in data and clean_name in data["devDependencies"]:
            del data["devDependencies"][clean_name]
        self._write_package_json(data)

        return {
            "success": exec_res.success,
            "package": clean_name,
            "returncode": exec_res.returncode,
            "output": exec_res.stdout or exec_res.stderr,
        }
