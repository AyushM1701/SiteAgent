"""
tests/test_edit_scaffold_lifecycle.py - Blueprint Scaffolding Lifecycle Tests

Verifies Item 8:
createProject()          -> scaffold once
followUpEdit()           -> edit target files only (never clobber project config)
missingCriticalFile()    -> repair that specific file
explicitFrameworkChange()-> alter project config deliberately
"""

import json
import shutil
from pathlib import Path
import pytest

from agent.safe_executor import ExecutionResult
from agent.dependency_manager import DependencyManager
from server.app import (
    repair_missing_critical_files,
    explicit_framework_change,
    _scaffold_site_vite_runner,
    _scaffold_vite_runner,
)


@pytest.fixture
def workspace(tmp_path):
    ws = tmp_path / "workspace"
    ws.mkdir()
    return ws


# ── 1. missingCriticalFile() & Granular Repair ────────────────────────────────

def test_repair_preserves_existing_custom_config_and_code(workspace):
    """repair_missing_critical_files must never overwrite existing developer customizations."""
    # Write custom package.json with extra dependency
    custom_pkg = {
        "name": "custom-site",
        "dependencies": {"react": "^19.0.0", "react-dom": "^19.0.0", "three": "^0.170.0"},
        "customFlag": True
    }
    (workspace / "package.json").write_text(json.dumps(custom_pkg, indent=2), encoding="utf-8")

    # Write custom vite.config.ts with alias
    custom_vite = """import { defineConfig } from 'vite';
export default defineConfig({
  resolve: { alias: { '@': './src' } },
  server: { strictPort: true, host: '127.0.0.1', open: false },
});
"""
    (workspace / "vite.config.ts").write_text(custom_vite, encoding="utf-8")

    # Write custom App.tsx and App.css
    (workspace / "App.tsx").write_text("export default function App() { return <h1>Custom App</h1>; }", encoding="utf-8")
    (workspace / "App.css").write_text("body { background: #123456; }", encoding="utf-8")
    (workspace / "index.html").write_text("<!doctype html><html><body><div id='root'></div><script type='module' src='/main.tsx'></script></body></html>", encoding="utf-8")
    (workspace / "main.tsx").write_text("import React from 'react';\nimport ReactDOM from 'react-dom/client';\nimport App from './App';\nReactDOM.createRoot(document.getElementById('root')!).render(<App />);", encoding="utf-8")
    (workspace / "tsconfig.json").write_text('{"compilerOptions": {"strict": true}}', encoding="utf-8")

    # Run repair on a complete workspace
    repaired = repair_missing_critical_files(workspace, "CustomSite", mode="site")

    # package.json, vite.config.ts, App.tsx, App.css must NOT be in repaired list
    assert "package.json" not in repaired
    assert "vite.config.ts" not in repaired
    assert "App.tsx" not in repaired
    assert "App.css" not in repaired

    # Verify contents are 100% untouched
    pkg_data = json.loads((workspace / "package.json").read_text(encoding="utf-8"))
    assert pkg_data.get("customFlag") is True
    assert "three" in pkg_data["dependencies"]
    assert "@" in (workspace / "vite.config.ts").read_text(encoding="utf-8")
    assert "Custom App" in (workspace / "App.tsx").read_text(encoding="utf-8")
    assert "#123456" in (workspace / "App.css").read_text(encoding="utf-8")


def test_repair_missing_single_critical_file(workspace):
    """If only main.tsx is missing, only main.tsx is repaired."""
    # Write custom package.json
    (workspace / "package.json").write_text('{"name": "test-pkg"}', encoding="utf-8")
    (workspace / "vite.config.ts").write_text("export default {}", encoding="utf-8")
    (workspace / "tsconfig.json").write_text("{}", encoding="utf-8")
    (workspace / "index.html").write_text("<html></html>", encoding="utf-8")
    (workspace / "App.tsx").write_text("export default function App() { return <div/>; }", encoding="utf-8")
    (workspace / "App.css").write_text("/* style */", encoding="utf-8")

    # main.tsx is missing
    assert not (workspace / "main.tsx").exists()

    repaired = repair_missing_critical_files(workspace, "TestSite", mode="site")
    assert "main.tsx" in repaired
    assert (workspace / "main.tsx").exists()
    assert "package.json" not in repaired
    assert (workspace / "package.json").read_text(encoding="utf-8") == '{"name": "test-pkg"}'


def test_component_mode_repairs_missing_component_entry(workspace):
    """Component mode repairs missing {title}.tsx if App.tsx also does not exist."""
    (workspace / "package.json").write_text('{"name": "btn"}', encoding="utf-8")
    (workspace / "vite.config.ts").write_text("export default {}", encoding="utf-8")
    (workspace / "tsconfig.json").write_text("{}", encoding="utf-8")
    (workspace / "index.html").write_text("<html></html>", encoding="utf-8")
    (workspace / "main.tsx").write_text("/* main */", encoding="utf-8")

    repaired = repair_missing_critical_files(workspace, "AwesomeButton", mode="component")
    assert "AwesomeButton.tsx" in repaired
    assert (workspace / "AwesomeButton.tsx").exists()
    assert "AwesomeButton" in (workspace / "AwesomeButton.tsx").read_text(encoding="utf-8")


# ── 2. followUpEdit() Lifecycle (Target Files Only) ───────────────────────────

def test_follow_up_edit_preserves_installed_r3f_and_vite_config(workspace, monkeypatch):
    """
    Simulates a mature project where the user installed Three.js / R3F and added a Vite alias.
    A follow-up edit modifies Hero.tsx.
    The scaffolder MUST NOT overwrite package.json or vite.config.ts.
    """
    # 1. Initial scaffold (createProject)
    _scaffold_site_vite_runner(workspace, "SpaceAgency", {
        "src/components/Hero.tsx": "export default function Hero() { return <section>Original Hero</section>; }"
    })

    # 2. Developer/Agent installs Three.js and adds custom alias
    dm = DependencyManager(workspace)
    fake_res = ExecutionResult(command=["npm"], returncode=0, stdout="Installed simulated package", stderr="", success=True, duration_ms=0.0)
    monkeypatch.setattr(dm.executor, "execute", lambda *args, **kwargs: fake_res)
    dm.install_package("three")
    dm.install_package("@react-three/fiber")

    # Developer manually edits vite.config.ts to add custom plugin / alias
    cfg_path = workspace / "vite.config.ts"
    custom_cfg = cfg_path.read_text(encoding="utf-8") + "\n// Developer added custom post-processing\n"
    cfg_path.write_text(custom_cfg, encoding="utf-8")

    # Developer also customized App.tsx layout
    app_path = workspace / "App.tsx"
    app_path.write_text("export default function App() { return <div className='custom-wrapper'><Hero /></div>; }", encoding="utf-8")

    # 3. followUpEdit(): Model edits only target file src/components/Hero.tsx
    hero_path = workspace / "src" / "components" / "Hero.tsx"
    hero_path.parent.mkdir(parents=True, exist_ok=True)
    hero_path.write_text("export default function Hero() { return <section>3D Updated Hero</section>; }", encoding="utf-8")

    # Instead of calling _scaffold_site_vite_runner(), the follow-up turn calls repair_missing_critical_files()
    repaired = repair_missing_critical_files(workspace, "SpaceAgency", mode="site")
    assert "package.json" not in repaired
    assert "vite.config.ts" not in repaired
    assert "App.tsx" not in repaired

    # 4. Verify all configurations and customizations remain 100% preserved
    pkg_data = json.loads((workspace / "package.json").read_text(encoding="utf-8"))
    assert "three" in pkg_data["dependencies"]
    assert "@react-three/fiber" in pkg_data["dependencies"]
    assert "Developer added custom post-processing" in (workspace / "vite.config.ts").read_text(encoding="utf-8")
    assert "custom-wrapper" in (workspace / "App.tsx").read_text(encoding="utf-8")
    assert "3D Updated Hero" in hero_path.read_text(encoding="utf-8")


# ── 3. explicitFrameworkChange() Lifecycle ────────────────────────────────────

def test_explicit_framework_change_vite_alias(workspace):
    """explicitFrameworkChange('add_vite_alias') adds alias without stomping config."""
    vite_cfg = workspace / "vite.config.ts"
    vite_cfg.write_text("""import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: { strictPort: true },
});
""", encoding="utf-8")

    res = explicit_framework_change(workspace, "add_vite_alias", {"alias": "@", "target": "./src"})
    assert res["success"] is True
    updated = vite_cfg.read_text(encoding="utf-8")
    assert "import path from 'path';" in updated
    assert "resolve:" in updated
    assert "'@': path.resolve(__dirname, './src')" in updated
    assert "strictPort: true" in updated  # existing server settings preserved


def test_explicit_framework_change_tsconfig_paths(workspace):
    """explicitFrameworkChange('set_tsconfig_paths') cleanly updates compilerOptions."""
    tsconfig = workspace / "tsconfig.json"
    tsconfig.write_text(json.dumps({
        "compilerOptions": {"strict": True, "target": "ES2022"}
    }), encoding="utf-8")

    res = explicit_framework_change(workspace, "set_tsconfig_paths", {
        "paths": {"@/*": ["./src/*"], "@components/*": ["./src/components/*"]}
    })
    assert res["success"] is True
    data = json.loads(tsconfig.read_text(encoding="utf-8"))
    assert data["compilerOptions"]["strict"] is True  # preserved
    assert data["compilerOptions"]["baseUrl"] == "."
    assert "@/*" in data["compilerOptions"]["paths"]
    assert "@components/*" in data["compilerOptions"]["paths"]


def test_explicit_framework_change_setup_tailwind(workspace):
    """explicitFrameworkChange('setup_tailwind') injects Tailwind directive without wiping styles."""
    app_css = workspace / "App.css"
    app_css.write_text(":root { --primary: #00ffaa; }\nh1 { color: var(--primary); }\n", encoding="utf-8")

    res = explicit_framework_change(workspace, "setup_tailwind")
    assert res["success"] is True
    content = app_css.read_text(encoding="utf-8")
    assert '@import "tailwindcss";' in content
    assert "--primary: #00ffaa;" in content  # preserved original styles


# ── 4. Checkpoint Revert & API Tests ─────────────────────────────────────────

def test_checkpoint_revert_preserves_custom_config_without_rescaffolding(tmp_path):
    """Reverting to a checkpoint preserves restored custom dependencies without stomping defaults."""
    from server.sessions import Session

    sess_dir = tmp_path / "sess_ws"
    sess_dir.mkdir()

    s = Session(
        session_id="1700000000_abcdef",
        title="CustomSite",
        mode="site",
        prompt="Initial prompt",
        workspace_dir=sess_dir,
    )

    # Initial custom setup
    custom_pkg = {
        "name": "custom-site",
        "dependencies": {"react": "^19.0.0", "react-dom": "^19.0.0", "three": "^0.170.0"},
        "customFlag": True,
    }
    (sess_dir / "package.json").write_text(json.dumps(custom_pkg, indent=2), encoding="utf-8")
    (sess_dir / "vite.config.ts").write_text("// Custom vite config with three plugin\n", encoding="utf-8")
    (sess_dir / "App.tsx").write_text("export default function App() { return <div>3D Scene</div>; }", encoding="utf-8")
    (sess_dir / "index.html").write_text("<html></html>", encoding="utf-8")
    (sess_dir / "main.tsx").write_text("/* main */", encoding="utf-8")
    (sess_dir / "tsconfig.json").write_text("{}", encoding="utf-8")

    try:
        # Take checkpoint #1
        chk_num = s.create_checkpoint("Initial custom site")
        assert chk_num == 1

        # Now simulate a subsequent edit modifying App.tsx and corrupting/changing something
        (sess_dir / "App.tsx").write_text("export default function App() { return <div>Broken Edit</div>; }", encoding="utf-8")

        # Revert to checkpoint #1
        ok = s.revert_to_checkpoint(chk_num)
        assert ok is True

        # Run repair (as done in revert_session_checkpoint)
        repaired = repair_missing_critical_files(s.workspace_dir, s.title, s.mode)
        assert "package.json" not in repaired
        assert "vite.config.ts" not in repaired

        # Verify custom dependencies and config were restored and not clobbered
        pkg = json.loads((sess_dir / "package.json").read_text(encoding="utf-8"))
        assert pkg.get("customFlag") is True
        assert "three" in pkg["dependencies"]
        assert "Custom vite config with three plugin" in (sess_dir / "vite.config.ts").read_text(encoding="utf-8")
        assert "3D Scene" in (sess_dir / "App.tsx").read_text(encoding="utf-8")
    finally:
        from server.sessions import SESSIONS_DIR
        for p in SESSIONS_DIR.glob(f"{s.session_id}*"):
            try:
                p.unlink()
            except Exception:
                pass


def test_framework_config_api_endpoint(tmp_path):
    """POST /api/projects/<session_id>/framework-config modifies config cleanly."""
    from server.app import app
    from server.sessions import session_manager, SESSIONS_DIR

    sess_dir = tmp_path / "api_ws"
    sess_dir.mkdir()

    s = session_manager.create_session("ApiSite", mode="site", prompt="Test")
    s.workspace_dir = sess_dir
    (sess_dir / "vite.config.ts").write_text("import { defineConfig } from 'vite';\nexport default defineConfig({});\n", encoding="utf-8")
    s.save()

    try:
        client = app.test_client()
        resp = client.post(
            f"/api/projects/{s.session_id}/framework-config",
            json={"action": "add_vite_alias", "payload": {"alias": "@", "target": "./src"}}
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert "@" in (sess_dir / "vite.config.ts").read_text(encoding="utf-8")
    finally:
        for p in SESSIONS_DIR.glob(f"{s.session_id}*"):
            try:
                p.unlink()
            except Exception:
                pass
