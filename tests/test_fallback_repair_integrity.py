from unittest.mock import MagicMock

from agent.project_validator import ValidationResult
from server.app import verify_and_repair_project


def test_project_repair_rejects_marker_only_fallback_rewrite(tmp_path, monkeypatch):
    header = tmp_path / "src/components/Header.tsx"
    header.parent.mkdir(parents=True)
    source = (
        "import './Header.css';\n"
        "export default function Header() { return <header id=\"header\" "
        "data-fallback=\"true\">Home</header>; }\n"
    )
    header.write_text(source, encoding="utf-8")
    (header.parent / "Header.css").write_text(".header { display: block; }\n", encoding="utf-8")
    failed = ValidationResult(
        typecheck_passed=True, build_passed=True, lint_passed=True,
        contract_passed=False, accessibility_passed=True, runtime_passed=True,
        preview_running=True, errors=["[Fallback Error] src/components/Header.tsx: unfinished"],
    )
    monkeypatch.setattr("server.app._validate_workspace", lambda *args, **kwargs: failed)
    runner = MagicMock()
    runner.generate_turn.return_value = (
        '<tool_call name="write_site"><file path="src/components/Header.tsx">'
        + source.replace('data-fallback="true"', 'data-fallback="false"')
        + '</file></tool_call>'
    )
    result = verify_and_repair_project(
        workspace=tmp_path, runner=runner, original_prompt="Build a site",
        files_dict={"src/components/Header.tsx": source,
                    "src/components/Header.css": ".header { display: block; }\n"},
        sections=["header"], max_attempts=1, run_visual_check=False,
    )
    assert result.repair_attempts == 1
    assert 'data-fallback="true"' in header.read_text(encoding="utf-8")
