from pathlib import Path

from agent.agent import _site_import_violations, _site_output_truncated
from agent.output_budget import BudgetTier, estimate_output_budget, extract_complexity_factors


def test_unfinished_site_envelope_is_rejected():
    assert _site_output_truncated('<tool_call name="write_site"><file path="Hero.tsx">return (')
    assert _site_output_truncated('<file path="Hero.tsx">content')
    assert not _site_output_truncated('<tool_call name="write_site"><file path="Hero.tsx">ok</file></tool_call>')


def test_site_import_gate_rejects_undeclared_package(tmp_path: Path):
    files = [("src/components/Hero.tsx", "import React from 'react';\nimport { Link } from 'react-router-dom';\nimport './Hero.css';")]
    assert "react-router-dom" in "\n".join(_site_import_violations(files, tmp_path))
    assert not _site_import_violations([("Hero.tsx", "import React from 'react'; import './Hero.css';")], tmp_path)


def test_interactive_site_section_gets_larger_budget():
    factors = extract_complexity_factors(
        prompt="Build a calculator with sliders and live results",
        task_mode="site_section",
        requested_files=["Calculator.tsx", "Calculator.css"],
    )
    assert estimate_output_budget(factors).tier == BudgetTier.INTERACTIVE_SITE_SECTION.value
