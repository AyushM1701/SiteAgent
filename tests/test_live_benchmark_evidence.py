import hashlib
import json

import pytest

from scripts.benchmark_full_sites import run_full_site_benchmark, SiteBenchmarkScore, SiteBenchmarkScorer
from training import provenance


def test_adapter_provenance_identifies_base_weights_and_holdout(tmp_path, monkeypatch):
    base = tmp_path / 'base'
    adapter = tmp_path / 'candidate'
    base.mkdir()
    adapter.mkdir()
    fingerprint = 'a' * 64
    (base / 'manifest.json').write_text(json.dumps({'immutable_fingerprint_sha256': fingerprint}))
    (adapter / 'adapter_config.json').write_text(json.dumps({'base_model_name_or_path': str(base)}))
    weights = adapter / 'adapter_model.safetensors'
    weights.write_bytes(b'isolated candidate weights')
    holdout = tmp_path / 'holdout.jsonl'
    holdout.write_text('{"prompt":"unfamiliar subject"}\n')
    monkeypatch.setattr(provenance, '_get_hardware_description', lambda: 'test hardware')
    record = provenance.generate_provenance_record(model_path=str(adapter), dataset_path=str(holdout))
    assert record['model_sha256'] == fingerprint
    assert record['adapter_sha256'] == hashlib.sha256(weights.read_bytes()).hexdigest()
    assert record['dataset_sha256'] == hashlib.sha256(holdout.read_bytes()).hexdigest()


def test_completed_site_evidence_survives_later_browser_failure(tmp_path, monkeypatch):
    benchmark = tmp_path / 'holdout.jsonl'
    benchmark.write_text('\n'.join(json.dumps({'task_id': f'case_{i}', 'name': 'Site', 'domain': 'portfolio'}) for i in range(2)))
    monkeypatch.setattr('scripts.benchmark_full_sites.generate_mock_site_files', lambda _: {})
    calls = []
    def evaluate(self, **kwargs):
        calls.append(kwargs['prompt_spec']['task_id'])
        if len(calls) == 2:
            raise RuntimeError('browser crashed')
        return SiteBenchmarkScore(calls[-1], 'portfolio', 'Site', 0.5, False)
    monkeypatch.setattr(SiteBenchmarkScorer, 'evaluate_site', evaluate)
    output = tmp_path / 'report.json'
    with pytest.raises(RuntimeError, match='browser crashed'):
        run_full_site_benchmark(mock=True, benchmark_file=benchmark, output_report_path=output,
                                workspace_base=tmp_path / 'workspace', keep_workspace=True)
    progress = json.loads(output.with_suffix('.progress.json').read_text())
    assert progress['completed_sites'] == 1 and progress['total_sites'] == 2
    assert progress['evaluation_mode'] == 'mock_harness'
    assert progress['site_results'][0]['passed'] is False
    assert progress['site_results'][0]['details']['outcome_scorecards']['model_native']['passed'] is None
