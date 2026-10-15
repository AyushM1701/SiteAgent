from types import SimpleNamespace

from evaluation.three_d_performance_validator import validate_three_d_performance
from scripts.benchmark_full_sites import build_outcome_scorecards


def test_empty_canvas_cannot_pass_three_d_gate():
    report = validate_three_d_performance({"src/Hero.tsx": "export default function Hero(){return <canvas />;}"})
    assert report["all_passed"] is False
    assert report["scene_contract"]["passed"] is False
    assert report["score"] == 0
    assert "scene_contract" in report["failed_checks"]


def test_drawable_r3f_scene_has_separate_static_result():
    report = validate_three_d_performance({"src/Hero.tsx": "<Canvas><mesh><boxGeometry /></mesh></Canvas>"})
    assert report["scene_contract"]["passed"] is True
    assert report["all_passed"] is True
    assert len(report["checks"]) == 6


def test_live_scorecards_preserve_native_failure_after_repair():
    failed = SimpleNamespace(passed=False)
    passed = SimpleNamespace(passed=True)
    repair = SimpleNamespace(validation_after_deterministic=passed,
                             deterministic_files=["src/Shop.tsx"], repair_attempts=1, validation=passed)
    final = SimpleNamespace(passed=True, composite_score=0.9)
    cards = build_outcome_scorecards(mock=False,
        generation_result={"generation_quality": "partial", "final_passed": False, "validation": failed},
        repair_result=repair, final_score=final)
    assert cards["model_native"]["passed"] is False
    assert cards["deterministic_repair"]["passed"] is True
    assert cards["model_repair"]["passed"] is True
    assert cards["final_rendered_site"]["passed"] is True


def test_mock_scorecard_never_claims_model_success():
    cards = build_outcome_scorecards(mock=True, final_score=SimpleNamespace(passed=True))
    assert cards["mock_harness"]["passed"] is True
    assert cards["model_native"]["status"] == "not_evaluated"
    assert cards["final_rendered_site"]["status"] == "not_evaluated"


def test_status_reports_loaded_process_not_configured_path(monkeypatch):
    monkeypatch.setenv("NO_AUTO_LOAD_MODEL", "1")
    from server import app as server
    monkeypatch.setattr(server, "_runner", None)
    monkeypatch.setattr(server, "_loaded_model_info", None)
    monkeypatch.setattr(server, "_model_status", "loading")
    pending = server.app.test_client().get("/api/status").get_json()
    assert pending["model_loaded"] is False
    assert pending["model_path"] is None
    assert pending["adapter_compatible"] is None
    monkeypatch.setattr(server, "_runner", SimpleNamespace(model_path="base-model"))
    monkeypatch.setattr(server, "_loaded_model_info", {"model_name": "actual-base", "base_fingerprint": "basehash", "gpu_ready": False, "adapter_compatible": True})
    monkeypatch.setattr(server, "_model_status", "ready")
    loaded = server.app.test_client().get("/api/status").get_json()
    assert loaded["model_loaded"] is True
    assert loaded["model_name"] == "actual-base"
    assert loaded["base_fingerprint"] == "basehash"
    assert loaded["adapter_compatible"] is True


def test_revoked_promotion_resolves_to_base(monkeypatch):
    monkeypatch.setenv("NO_AUTO_LOAD_MODEL", "1")
    from pathlib import Path
    from server import app as server
    assert Path(server._resolve_default_model()).resolve() == (server.BASE_DIR / "base-model").resolve()
