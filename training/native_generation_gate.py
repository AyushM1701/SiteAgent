"""Fail closed before GPU training unless the native development suite passes."""
import json
from pathlib import Path

from training.preflight import sha256


def require_native_completion(report_path, expected_model_dir=None):
    path = Path(report_path)
    if not path.is_file():
        raise ValueError(f'Native completion gate missing: {path}; run scripts/native_site_gate.py first')
    report = json.loads(path.read_text(encoding='utf-8'))
    if report.get('provenance') != 'live_model_native_development_gate' or report.get('passed') is not True:
        raise ValueError('Native completion gate has not passed live evaluation')
    if report.get('repair_count') != 0 or report.get('fallback_count') != 0:
        raise ValueError('Native gate cannot include repairs or fallbacks')
    from scripts.native_site_gate import ROOT, PIPELINE_SOURCES
    sources = report.get('pipeline_sources', {})
    if set(sources) != set(PIPELINE_SOURCES) or any(sha256(ROOT / name) != value for name, value in sources.items()):
        raise ValueError('Native gate missing current generation pipeline fingerprints; rerun it')
    cases = report.get('cases', [])
    if len(cases) != 3 or {c.get('domain') for c in cases} != {'portfolio', 'store', 'unfamiliar'}:
        raise ValueError('Native gate requires portfolio, store, and unfamiliar-topic sites')
    model = Path(report['model'])
    if expected_model_dir is not None and model.resolve() != Path(expected_model_dir).resolve():
        raise ValueError('Native gate was run on a different model than the training initialization')
    if report.get('adapter_sha256') and sha256(model / 'adapter_model.safetensors') != report['adapter_sha256']:
        raise ValueError('Native gate adapter fingerprint mismatch')
    identity = report.get('model_files', {})
    if not identity or not any(name.endswith('.safetensors') for name in identity):
        raise ValueError('Native model identity missing')
    for name, fingerprint in identity.items():
        if Path(name).name != name or not (model / name).is_file() or sha256(model / name) != fingerprint:
            raise ValueError('Native model fingerprint mismatch')
    for case in cases:
        if case.get('passed') is not True or case.get('errors'):
            raise ValueError('Native case failed')
        if case.get('stop_reason') != 'tool_complete':
            raise ValueError('Native output was not complete')
        if not all(case.get('compilation', {}).get(name, {}).get('passed') is True for name in ('typescript', 'build')):
            raise ValueError('Native compilation evidence missing')
        browser = case.get('browser', [])
        if len(browser) != 3 or {v.get('viewport') for v in browser} != {'desktop', 'mobile', 'reduced_motion'} or not all(v.get('passed') is True for v in browser):
            raise ValueError('Native browser evidence missing or failed')
        folder = path.parent / case['domain']
        if not (folder / 'response.txt').is_file() or not all((folder / f'{view}.png').is_file() for view in ('desktop', 'mobile', 'reduced_motion')):
            raise ValueError('Native artifacts missing')
        artifacts = case.get('artifacts', {})
        required = {'response.txt', 'src/components/Main.tsx', 'src/components/Main.css', 'desktop.png', 'mobile.png', 'reduced_motion.png'}
        if not required.issubset(artifacts):
            raise ValueError('Native artifact fingerprints missing')
        for relative, fingerprint in artifacts.items():
            artifact = (folder / relative).resolve()
            if folder.resolve() not in artifact.parents or not artifact.is_file() or sha256(artifact) != fingerprint:
                raise ValueError('Native artifact fingerprint mismatch')
    return {'path': str(path.resolve()), 'sha256': sha256(path), 'adapter_sha256': report['adapter_sha256']}
