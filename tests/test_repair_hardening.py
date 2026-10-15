import json
from types import SimpleNamespace

from agent.agent_protocol import site_envelope_errors
from agent.dependency_manager import DependencyManager
from server.app import _scaffold_site_vite_runner


def test_site_scaffold_preserves_dependencies_and_declares_approved_imports(tmp_path):
    (tmp_path / "package.json").write_text(
        json.dumps({"dependencies": {"lucide-react": "^0.475.0"}, "scripts": {"test": "echo ok"}}),
        encoding="utf-8",
    )
    files = {"src/components/Hero.tsx": "import { Canvas } from '@react-three/fiber'; export default function Hero(){ return <Canvas /> }"}
    _scaffold_site_vite_runner(tmp_path, "Example", files)
    manifest = json.loads((tmp_path / "package.json").read_text(encoding="utf-8"))
    assert manifest["dependencies"]["lucide-react"] == "^0.475.0"
    assert manifest["dependencies"]["@react-three/fiber"]
    assert manifest["scripts"]["test"] == "echo ok"


def test_failed_package_install_does_not_claim_dependency(tmp_path):
    class FailedExecutor:
        def execute(self, **_kwargs):
            return SimpleNamespace(success=False, returncode=1, stdout="", stderr="install failed")

    manager = DependencyManager(tmp_path, executor=FailedExecutor())
    result = manager.install_package("lucide-react")
    assert not result["success"]
    assert "lucide-react" not in manager.get_dependencies()["all"]


def test_live_write_rejects_incomplete_and_naked_file_tags():
    assert site_envelope_errors('<tool_call name="write_site"><file path="x.tsx">oops</file>')
    assert site_envelope_errors('<file path="x.tsx">oops</file>')
    assert site_envelope_errors('{"action": "write_site", "arguments": {')
    assert not site_envelope_errors('<tool_call name="write_site"><file path="x.tsx">ok</file></tool_call>')
