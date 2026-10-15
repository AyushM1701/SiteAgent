"""
tests/test_dependency_manager.py - Unit & Integration Tests for DependencyManager & SafeExecutor

Validates:
1. Controlled PackagePolicy (allowlist, Three.js / R3F / Lucide / Motion catalog, protected core packages)
2. SafeExecutor non-shell execution, security boundaries, and command event emission
3. DependencyManager get_dependencies, install_package, install_packages, remove_package
4. package.json write protection against model direct file modification
5. Protocol parser support for install_package, remove_package, get_dependencies actions
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from agent.safe_executor import SafeExecutor, SafeExecutorError, ExecutionResult
from agent.dependency_manager import PackagePolicy, PackagePolicyError, DependencyManager
from agent.agent_protocol import (
    parse_agent_output,
    InstallPackageAction,
    RemovePackageAction,
    GetDependenciesAction,
)
from server.app import resolve_project_path as server_resolver
from server.sessions import resolve_project_path as sessions_resolver
from agent.agent import resolve_project_path as agent_resolver


# ── 1. PackagePolicy Tests ───────────────────────────────────────────────────

def test_package_policy_allowed_catalog():
    """Verify that target 3D, animation, and UI packages are approved."""
    allowed = [
        "three",
        "@types/three",
        "@react-three/fiber",
        "@react-three/drei",
        "lucide-react",
        "framer-motion",
        "clsx",
        "tailwind-merge",
        "canvas-confetti",
        "@types/canvas-confetti",
        "troika-three-text",
        "simplex-noise",
    ]
    for pkg in allowed:
        assert PackagePolicy.is_package_allowed(pkg) is True, f"Expected {pkg} to be allowed"
        PackagePolicy.validate_install(pkg)  # Should not raise


def test_package_policy_blocks_unauthorized_packages():
    """Verify that unauthorized or dangerous packages are blocked."""
    disallowed = [
        "express",
        "nodemon",
        "child_process",
        "node-pty",
        "shelljs",
        "sudo",
        "curl",
        "arbitrary-malicious-pkg",
    ]
    for pkg in disallowed:
        assert PackagePolicy.is_package_allowed(pkg) is False, f"Expected {pkg} to be blocked"
        with pytest.raises(PackagePolicyError, match="not permitted"):
            PackagePolicy.validate_install(pkg)


def test_package_policy_protected_packages():
    """Verify that essential core framework packages cannot be removed."""
    protected = ["react", "react-dom", "typescript", "vite", "@vitejs/plugin-react"]
    for pkg in protected:
        assert PackagePolicy.is_protected_package(pkg) is True
        with pytest.raises(PackagePolicyError, match="Cannot remove core"):
            PackagePolicy.validate_remove(pkg)


def test_package_policy_allows_removal_of_non_core_packages():
    """Verify that non-core installed packages can be uninstalled."""
    PackagePolicy.validate_remove("three")
    PackagePolicy.validate_remove("@react-three/fiber")
    PackagePolicy.validate_remove("lucide-react")


# ── 2. SafeExecutor Tests ────────────────────────────────────────────────────

def test_safe_executor_blocks_dangerous_binaries():
    """Verify that SafeExecutor blocks shell and system execution binaries."""
    executor = SafeExecutor()
    blocked = ["cmd", "powershell", "pwsh", "sh", "bash", "curl", "rm", "del"]
    for b in blocked:
        with pytest.raises(SafeExecutorError, match="blocked for model tools"):
            executor._resolve_executable(b)


def test_safe_executor_blocks_unlisted_executables():
    """Verify that unlisted arbitrary executables are rejected."""
    executor = SafeExecutor()
    with pytest.raises(SafeExecutorError, match="not in the model safe executor allowlist"):
        executor._resolve_executable("python_evil")


def test_safe_executor_emits_command_events(tmp_path):
    """Verify that SafeExecutor emits running and completed command events."""
    events = []
    executor = SafeExecutor()

    mock_result = ExecutionResult(
        success=True,
        returncode=0,
        stdout="installed",
        stderr="",
        duration_ms=10.0,
        command=["npm", "--version"],
    )

    with patch.object(executor, "_resolve_executable", return_value="npm"), \
         patch("subprocess.Popen") as mock_popen:
        proc = Mock()
        proc.communicate.return_value = (b"10.0.0\n", b"")
        proc.returncode = 0
        mock_popen.return_value = proc

        res = executor.execute(["npm", "--version"], cwd=tmp_path, event_callback=events.append)
        assert res.success is True
        assert len(events) == 2
        assert events[0]["status"] == "running"
        assert events[1]["status"] == "completed"


# ── 3. DependencyManager Tests ───────────────────────────────────────────────

def test_dependency_manager_get_dependencies(tmp_path):
    """Verify get_dependencies accurately parses package.json."""
    pkg_data = {
        "name": "test-app",
        "dependencies": {"react": "^19.0.0", "three": "^0.170.0"},
        "devDependencies": {"typescript": "^5.7.3", "vite": "^6.0.0"},
    }
    (tmp_path / "package.json").write_text(json.dumps(pkg_data), encoding="utf-8")

    dm = DependencyManager(tmp_path)
    deps = dm.get_dependencies()

    assert deps["dependencies"]["three"] == "^0.170.0"
    assert deps["devDependencies"]["vite"] == "^6.0.0"
    assert "three" in deps["all"]
    assert "vite" in deps["all"]


def test_dependency_manager_install_package(tmp_path):
    """Verify install_package validates policy, executes via SafeExecutor, and records in package.json."""
    pkg_data = {"name": "test-app", "dependencies": {"react": "^19.0.0"}}
    (tmp_path / "package.json").write_text(json.dumps(pkg_data), encoding="utf-8")

    mock_executor = Mock()
    mock_executor.execute.return_value = ExecutionResult(
        success=True, returncode=0, stdout="added 1 package", stderr="", duration_ms=15.0, command=[]
    )

    dm = DependencyManager(tmp_path, executor=mock_executor)
    res = dm.install_package("three", version="^0.170.0")

    assert res["success"] is True
    assert res["package"] == "three"

    # Verify package.json was safely updated
    updated_pkg = json.loads((tmp_path / "package.json").read_text(encoding="utf-8"))
    assert updated_pkg["dependencies"]["three"] == "^0.170.0"


def test_dependency_manager_install_packages_batch(tmp_path):
    """Verify batch installation of Three.js and R3F packages."""
    pkg_data = {"name": "test-app", "dependencies": {}}
    (tmp_path / "package.json").write_text(json.dumps(pkg_data), encoding="utf-8")

    mock_executor = Mock()
    mock_executor.execute.return_value = ExecutionResult(
        success=True, returncode=0, stdout="ok", stderr="", duration_ms=10.0, command=[]
    )

    dm = DependencyManager(tmp_path, executor=mock_executor)
    batch_res = dm.install_packages(["three", "@react-three/fiber", "@react-three/drei"])

    assert batch_res["success"] is True
    assert set(batch_res["installed"]) == {"three", "@react-three/fiber", "@react-three/drei"}

    updated_pkg = json.loads((tmp_path / "package.json").read_text(encoding="utf-8"))
    assert "three" in updated_pkg["dependencies"]
    assert "@react-three/fiber" in updated_pkg["dependencies"]
    assert "@react-three/drei" in updated_pkg["dependencies"]


def test_dependency_manager_remove_package(tmp_path):
    """Verify remove_package removes non-core packages and updates package.json."""
    pkg_data = {
        "name": "test-app",
        "dependencies": {"react": "^19.0.0", "three": "^0.170.0"},
    }
    (tmp_path / "package.json").write_text(json.dumps(pkg_data), encoding="utf-8")

    mock_executor = Mock()
    mock_executor.execute.return_value = ExecutionResult(
        success=True, returncode=0, stdout="removed 1 package", stderr="", duration_ms=10.0, command=[]
    )

    dm = DependencyManager(tmp_path, executor=mock_executor)
    res = dm.remove_package("three")
    assert res["success"] is True

    updated_pkg = json.loads((tmp_path / "package.json").read_text(encoding="utf-8"))
    assert "three" not in updated_pkg["dependencies"]
    assert "react" in updated_pkg["dependencies"]


def test_dependency_manager_refuses_protected_removal(tmp_path):
    """Verify remove_package refuses to remove protected dependencies."""
    dm = DependencyManager(tmp_path)
    with pytest.raises(PackagePolicyError, match="Cannot remove core framework dependency"):
        dm.remove_package("react")


# ── 4. package.json Write Protection Tests ───────────────────────────────────

@pytest.mark.parametrize("resolver", [server_resolver, sessions_resolver, agent_resolver])
def test_resolvers_block_direct_package_json_modification(resolver, tmp_path):
    """Verify that resolve_project_path blocks direct model writes targeting package.json."""
    with pytest.raises(PermissionError, match="Direct modification of package.json is blocked"):
        resolver(tmp_path, "package.json")

    with pytest.raises(PermissionError, match="Direct modification of package.json is blocked"):
        resolver(tmp_path, "/package.json")

    with pytest.raises(PermissionError, match="Direct modification of package.json is blocked"):
        resolver(tmp_path, r"\package.json")


@pytest.mark.parametrize("resolver", [server_resolver, sessions_resolver, agent_resolver])
def test_resolvers_allow_authorized_package_json(resolver, tmp_path):
    """Verify that internal authorized calls with allow_package_json=True succeed."""
    resolved = resolver(tmp_path, "package.json", allow_package_json=True)
    assert resolved == (tmp_path / "package.json").resolve()


@pytest.mark.parametrize("resolver", [server_resolver, sessions_resolver, agent_resolver])
def test_resolvers_allow_normal_code_files(resolver, tmp_path):
    """Verify that standard TSX and CSS code files resolve without interference."""
    res_tsx = resolver(tmp_path, "src/components/Hero.tsx")
    assert res_tsx == (tmp_path / "src/components/Hero.tsx").resolve()


# ── 5. Protocol Parser Tests ─────────────────────────────────────────────────

def test_parse_install_package_json_envelope():
    """Verify parsing JSON action envelope for install_package."""
    text = json.dumps({
        "action": "install_package",
        "statusMessage": "Installing Three.js for 3D hero scene",
        "arguments": {
            "package": "three",
            "version": "^0.170.0"
        }
    })
    turn = parse_agent_output(text)
    assert isinstance(turn.action, InstallPackageAction)
    assert turn.action.package == "three"
    assert turn.action.version == "^0.170.0"
    assert turn.is_tool_call is True


def test_parse_remove_package_json_envelope():
    """Verify parsing JSON action envelope for remove_package."""
    text = json.dumps({
        "action": "remove_package",
        "arguments": {
            "package": "canvas-confetti"
        }
    })
    turn = parse_agent_output(text)
    assert isinstance(turn.action, RemovePackageAction)
    assert turn.action.package == "canvas-confetti"
    assert turn.is_tool_call is True


def test_parse_get_dependencies_json_envelope():
    """Verify parsing JSON action envelope for get_dependencies."""
    text = json.dumps({
        "action": "get_dependencies"
    })
    turn = parse_agent_output(text)
    assert isinstance(turn.action, GetDependenciesAction)
    assert turn.is_tool_call is True


def test_parse_install_package_xml_tool_call():
    """Verify parsing XML tool call for install_package."""
    raw = '<tool_call name="install_package">{"package": "@react-three/fiber", "version": "^8.17.10"}</tool_call>'
    turn = parse_agent_output(raw)
    assert isinstance(turn.action, InstallPackageAction)
    assert turn.action.package == "@react-three/fiber"
    assert turn.action.version == "^8.17.10"
    assert turn.is_tool_call is True
