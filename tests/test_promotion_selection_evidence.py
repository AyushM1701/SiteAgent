import hashlib
import json
from pathlib import Path

import pytest


def test_gate_labels_alone_cannot_select_adapter(monkeypatch, tmp_path):
    monkeypatch.setenv('NO_AUTO_LOAD_MODEL', '1')
    from server import app as server
    from agent import base_model_fingerprint
    adapter = tmp_path / 'candidate'
    adapter.mkdir()
    (adapter / 'adapter_config.json').write_text('{}')
    pointer = tmp_path / 'promoted_model.json'
    pointer.write_text(json.dumps({'promoted_model_path': str(adapter), 'gate_status': 'PASSED',
        'verified_gates': ['completion', 'fidelity', 'interaction', 'visual_quality', 'motion', 'runtime_3d']}))
    monkeypatch.setattr(server, '_PROMOTED_PTR', pointer)
    monkeypatch.setattr(base_model_fingerprint, 'verify_lora_adapter_compatibility', lambda *args: None)
    assert Path(server._resolve_default_model()).resolve() == (server.BASE_DIR / 'base-model').resolve()


def test_missing_evidence_rejected(tmp_path):
    from training.promotion_evidence import require_promotion_evidence
    with pytest.raises(ValueError, match='evidence'):
        require_promotion_evidence({}, tmp_path, tmp_path)


def test_changed_evidence_rejected(tmp_path):
    from training.promotion_evidence import read_evidence
    report = tmp_path / 'report.json'
    report.write_text('{"passed":true}')
    reference = {'path': str(report), 'sha256': hashlib.sha256(report.read_bytes()).hexdigest()}
    assert read_evidence(reference, tmp_path)[0]['passed'] is True
    report.write_text('{"passed":false}')
    with pytest.raises(ValueError, match='fingerprint'):
        read_evidence(reference, tmp_path)


@pytest.fixture
def release_fixture(tmp_path, monkeypatch):
    from training import native_generation_gate, methodology
    from evaluation import human_visual_review
    from types import SimpleNamespace
    monkeypatch.setattr(native_generation_gate, 'require_native_completion', lambda *a, **k: None)
    monkeypatch.setattr(human_visual_review, 'validate_human_review', lambda *a: [])
    monkeypatch.setattr(methodology, 'evaluate_promotion_gate', lambda *a: SimpleNamespace(is_eligible=True))
    adapter = tmp_path / 'adapter'
    adapter.mkdir()
    (adapter / 'adapter_model.safetensors').write_bytes(b'test fixture, not model weights')
    fingerprint = hashlib.sha256((adapter / 'adapter_model.safetensors').read_bytes()).hexdigest()
    tasks = [{'task_id': str(i), 'details': {'project_validation': {
        'motion_runtime_status': 'passed', 'three_d_runtime_status': 'passed'}}} for i in range(30)]
    reports = {
        'native_gate': {},
        'site_benchmark': {'adapter_sha256': fingerprint, 'provenance': 'real', 'mock': False,
            'outcome_scorecards_summary': {stage: {'evaluated_sites': 30, 'passed_sites': 30, 'pass_rate': 1.0}
                for stage in ('model_native', 'deterministic_repair', 'model_repair', 'final_rendered_site')},
            'site_results': tasks},
        'component_benchmark': {'adapter_sha256': fingerprint, 'provenance': 'real', 'mock': False},
        'human_review': {'site_reviews': [{'task_id': str(i)} for i in range(30)]},
    }
    pointer = {'adapter_sha256': fingerprint, 'promotion_evidence': {}}

    def save():
        for name, report in reports.items():
            path = tmp_path / f'{name}.json'
            path.write_text(json.dumps(report))
            pointer['promotion_evidence'][name] = {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
        return pointer, adapter, tmp_path
    return reports, save


def test_verified_report_chain_can_pass(release_fixture):
    from training.promotion_evidence import require_promotion_evidence
    _, save = release_fixture
    assert require_promotion_evidence(*save())['verified'] is True


@pytest.mark.parametrize('failure', ['mock', 'wrong_adapter', 'missing_scorecard', 'missing_motion', 'unrelated_reviews', 'native_failure'])
def test_report_chain_rejects_release_failures(release_fixture, failure):
    from training.promotion_evidence import require_promotion_evidence
    reports, save = release_fixture
    sites = reports['site_benchmark']
    if failure == 'mock':
        sites['mock'] = True
    elif failure == 'wrong_adapter':
        sites['adapter_sha256'] = '0' * 64
    elif failure == 'missing_scorecard':
        del sites['outcome_scorecards_summary']['model_repair']
    elif failure == 'missing_motion':
        for row in sites['site_results']:
            row['details']['project_validation']['motion_runtime_status'] = 'not_requested'
    elif failure == 'unrelated_reviews':
        reports['human_review']['site_reviews'][0]['task_id'] = 'unrelated'
    else:
        sites['outcome_scorecards_summary']['model_native']['pass_rate'] = .1
    with pytest.raises(ValueError):
        require_promotion_evidence(*save())
