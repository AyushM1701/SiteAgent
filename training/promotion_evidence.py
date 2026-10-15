"""Verify persisted release evidence before an adapter becomes the default."""
from pathlib import Path
import json

from training.preflight import sha256

SCORECARDS = ('model_native', 'deterministic_repair', 'model_repair', 'final_rendered_site')


def read_evidence(reference, root):
    if not isinstance(reference, dict) or not reference.get('path') or not reference.get('sha256'):
        raise ValueError('Promotion evidence requires a report path and fingerprint')
    path = Path(reference['path'])
    if not path.is_absolute():
        path = Path(root) / path
    if not path.is_file() or sha256(path) != reference['sha256']:
        raise ValueError(f'Promotion evidence fingerprint mismatch or missing file: {path}')
    return json.loads(path.read_text(encoding='utf-8')), path


def require_promotion_evidence(pointer, adapter, root):
    """Labels on a pointer are claims; hashed live reports establish eligibility."""
    evidence = pointer.get('promotion_evidence')
    if not isinstance(evidence, dict):
        raise ValueError('Promotion evidence is missing; gate labels alone are insufficient')
    adapter_hash = sha256(Path(adapter) / 'adapter_model.safetensors')
    if pointer.get('adapter_sha256') != adapter_hash:
        raise ValueError('Promotion adapter fingerprint mismatch')
    from training.native_generation_gate import require_native_completion
    from evaluation.human_visual_review import validate_human_review
    from training.methodology import evaluate_promotion_gate

    _, native_path = read_evidence(evidence.get('native_gate'), root)
    require_native_completion(native_path, expected_model_dir=adapter)
    sites, _ = read_evidence(evidence.get('site_benchmark'), root)
    components, _ = read_evidence(evidence.get('component_benchmark'), root)
    human, _ = read_evidence(evidence.get('human_review'), root)
    for report in (sites, components):
        if report.get('adapter_sha256') != adapter_hash:
            raise ValueError('Promotion benchmark adapter fingerprint mismatch')
        if report.get('provenance') != 'real' or report.get('mock', report.get('is_mock')) is not False:
            raise ValueError('Promotion requires real, explicitly non-mock evidence')
    cards = sites.get('outcome_scorecards_summary', {})
    if any(name not in cards for name in SCORECARDS):
        raise ValueError('Promotion requires all four outcome scorecards')
    native = cards['model_native']
    if native.get('evaluated_sites', 0) < 30 or native.get('pass_rate', 0) < .85:
        raise ValueError('Promotion requires native completion on at least 30 sites at 85% or better')
    review_errors = validate_human_review(human, adapter_hash)
    reviewed_tasks = {row.get('task_id') for row in human.get('site_reviews', [])}
    site_tasks = {row.get('task_id') for row in sites.get('site_results', [])}
    if review_errors or reviewed_tasks != site_tasks:
        raise ValueError('Promotion human review invalid: ' + '; '.join(review_errors or ['reviewed sites differ from benchmark']))
    decision = evaluate_promotion_gate({**components, 'site_benchmark_metrics': sites})
    if not decision.is_eligible:
        raise ValueError(decision.summary)
    results = sites.get('site_results', [])
    for status in ('motion_runtime_status', 'three_d_runtime_status'):
        tested = [row.get('details', {}).get('project_validation', {}) for row in results
                  if row.get('details', {}).get('project_validation', {}).get(status) not in (None, 'not_requested')]
        if not tested or any(row.get(status) != 'passed' for row in tested):
            raise ValueError(f'Promotion requires passed browser evidence for {status}')
    return {'adapter_sha256': adapter_hash, 'verified': True}
