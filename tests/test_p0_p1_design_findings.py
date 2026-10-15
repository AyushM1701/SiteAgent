import pytest

from agent.agent_protocol import parse_agent_output
from agent.design_plan import DesignPlan
from agent.archetype_templates import validate_archetype
from agent.site_acceptance import check_site_files
from agent.visual_judge import score_trajectory_visual, evaluate_motion_polish
from evaluation.site_benchmark_scorer import SiteBenchmarkScorer


def test_truncated_write_site_is_not_parsed_as_a_write():
    turn = parse_agent_output('<tool_call name="write_site"><file path="src/App.tsx">export default 1</file>')
    assert turn.action is None
    assert "Malformed" in turn.status_message


def test_cached_visual_score_requires_receipt():
    result = score_trajectory_visual({"visual_score": 5, "files": {"src/App.tsx": "export default 1"}})
    assert result["pass"] is False
    assert result["visual_verified"] is False


def test_static_acceptance_exposes_unverified_live_evidence():
    result = check_site_files({"src/App.tsx": "export default function App(){return <main/>}"})
    assert result["static_passed"] is True
    assert result["live_interaction_evidence"] is False


def test_interactions_fail_without_live_receipt():
    score, details = SiteBenchmarkScorer().score_interactions(
        {"required_interactions": ["mobile_nav_toggle"]},
        {"src/App.tsx": "const [isMenuOpen,setMenuOpen]=useState(false); <button onClick={()=>setMenuOpen(true)} aria-expanded={isMenuOpen}/>"},
    )
    assert score == 0
    assert details["live_evidence_required"] is True


def test_design_plan_rejects_malformed_schema_and_emits_xml():
    with pytest.raises(ValueError):
        DesignPlan.from_dict({"heroArchetype": "split"})
    plan = DesignPlan("editorial", "split", "airy", "display-heavy", topology=["asymmetric"])
    assert '<layout archetype="split"' in plan.to_layout_xml()


def test_archetype_validation_and_motion_missing_are_fail_closed():
    assert validate_archetype("grid") == "bento"
    with pytest.raises(ValueError):
        validate_archetype("unknown")
    result = evaluate_motion_polish("<main />", ".card { color: red; }", "grid")
    assert result["pass"] is False
    assert any("Missing motion" in issue for issue in result["issues"])
