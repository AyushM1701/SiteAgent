import json

import pytest

from agent.style_ingest import check_css_selector_coverage
from training.native_generation_gate import require_native_completion


def test_css_prefix_is_not_a_selector_definition():
    passed, missing = check_css_selector_coverage('<div className="btn btn-terracotta btn--large"/>', '.btn {color:black}')
    assert not passed
    assert missing == ['btn--large', 'btn-terracotta']


@pytest.mark.parametrize('report', [
    {'provenance': 'mock', 'passed': True},
    {'provenance': 'live_model_native_development_gate', 'passed': False},
    {'provenance': 'live_model_native_development_gate', 'passed': True, 'repair_count': 1, 'fallback_count': 0},
    {'provenance': 'live_model_native_development_gate', 'passed': True, 'repair_count': 0, 'fallback_count': 0, 'cases': []},
])
def test_gate_rejects_mock_failed_repaired_or_incomplete_reports(tmp_path, report):
    path = tmp_path / 'report.json'
    path.write_text(json.dumps(report), encoding='utf-8')
    with pytest.raises(ValueError):
        require_native_completion(path)


def test_gate_missing_report_is_not_permission_to_train(tmp_path):
    with pytest.raises(ValueError, match='missing'):
        require_native_completion(tmp_path / 'missing.json')


def test_gate_accepts_complete_evidence_then_rejects_changed_artifact(tmp_path):
    from scripts.native_site_gate import ROOT, PIPELINE_SOURCES
    from training.preflight import sha256
    model = tmp_path / 'model'
    model.mkdir()
    weights = model / 'adapter_model.safetensors'
    weights.write_bytes(b'unit test model identity')
    report = {'provenance': 'live_model_native_development_gate', 'passed': True,
              'repair_count': 0, 'fallback_count': 0, 'model': str(model),
              'adapter_sha256': sha256(weights), 'cases': [],
              'model_files': {weights.name: sha256(weights)},
              'pipeline_sources': {name: sha256(ROOT / name) for name in PIPELINE_SOURCES}}
    for domain in ('portfolio', 'store', 'unfamiliar'):
        folder = tmp_path / domain
        artifacts = {}
        for name in ('response.txt', 'src/components/Main.tsx', 'src/components/Main.css',
                     'desktop.png', 'mobile.png', 'reduced_motion.png'):
            file = folder / name
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text('synthetic unit fixture', encoding='utf-8')
            artifacts[name] = sha256(file)
        report['cases'].append({'domain': domain, 'passed': True, 'errors': [],
            'stop_reason': 'tool_complete', 'artifacts': artifacts,
            'compilation': {key: {'passed': True} for key in ('typescript', 'build')},
            'browser': [{'viewport': key, 'passed': True} for key in ('desktop', 'mobile', 'reduced_motion')]})
    path = tmp_path / 'report.json'
    path.write_text(json.dumps(report), encoding='utf-8')
    assert require_native_completion(path)['sha256'] == sha256(path)
    assert require_native_completion(path, expected_model_dir=model)['sha256'] == sha256(path)
    with pytest.raises(ValueError, match='different model'):
        require_native_completion(path, expected_model_dir=tmp_path / 'other-model')
    (tmp_path / 'store/src/components/Main.css').write_text('changed', encoding='utf-8')
    with pytest.raises(ValueError, match='fingerprint mismatch'):
        require_native_completion(path)
