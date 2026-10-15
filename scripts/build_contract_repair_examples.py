"""Build observed JSX and stylesheet repair turns from an approved shop reference."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent.site_prompt import SITE_AGENT_SYSTEM_PROMPT
from agent.style_ingest import check_css_selector_coverage, check_css_syntactic_completeness
from data_pipeline.reviewed_site_examples import validate_reviewed_site_rows
from scripts.build_diverse_curriculum import envelope
from training.preflight import encode_row, sha256

TARGET = ROOT / 'data/reviewed_full_sites/contract_repairs_v1.jsonl'
EVIDENCE = ROOT / 'data/reviewed_full_sites/evidence/contract_repairs_v1/paperkite'


def typecheck(tsx: str, css: str, name: str) -> tuple[bool, str]:
    path = EVIDENCE / name
    path.mkdir(parents=True, exist_ok=True)
    (path / 'Shop.tsx').write_text(tsx, encoding='utf-8')
    (path / 'Shop.css').write_text(css, encoding='utf-8')
    (path / 'globals.d.ts').write_text("declare module '*.css';", encoding='utf-8')
    command = ['node', str(ROOT / 'node_modules/typescript/bin/tsc'), '--noEmit', '--jsx', 'react-jsx',
               '--module', 'ESNext', '--moduleResolution', 'bundler', '--target', 'ES2020',
               '--lib', 'ES2020,DOM', '--skipLibCheck', '--allowSyntheticDefaultImports',
               str(path / 'Shop.tsx'), str(path / 'globals.d.ts')]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=60)
    return result.returncode == 0, (result.stdout + result.stderr).replace(str(path), 'src/components')


def main() -> None:
    if TARGET.exists():
        raise ValueError(f'Immutable reviewed repair dataset already exists: {TARGET}')
    original_rows = [json.loads(line) for line in (ROOT / 'data/reviewed_full_sites/diverse_v1.jsonl').read_text(encoding='utf-8').splitlines()]
    approved = next(row for row in original_rows if row['task_id'] == 'diverse_paperkite_shop')
    source = ROOT / approved['source']
    tsx = (source / 'Shop.tsx').read_text(encoding='utf-8')
    css = (source / 'Shop.css').read_text(encoding='utf-8')
    if sha256(source / 'Shop.tsx') != approved['source_files']['Shop.tsx'] or sha256(source / 'Shop.css') != approved['source_files']['Shop.css']:
        raise ValueError('Approved source changed')
    from tokenizers import Tokenizer
    from transformers import AutoTokenizer
    encoder = Tokenizer.from_file(str(ROOT / 'base-model/tokenizer.json'))
    native = AutoTokenizer.from_pretrained(ROOT / 'base-model', local_files_only=True)
    meta = {key: copy.deepcopy(approved[key]) for key in ('family_id', 'domain', 'source', 'license',
            'source_files', 'validation', 'browser_evidence', 'visual_review', 'provenance')}
    meta['provenance']['repair_source'] = 'fault injection into the exact human-scored Paperkite source'
    meta['admission_status'] = 'reviewed'
    rows = []

    good_expression = "{count===1?'print':'prints'}"
    bad_expression = "{count===1?'print'?'print':'prints'}"
    if tsx.count(good_expression) != 1:
        raise ValueError('Expected cart expression is missing or ambiguous')
    broken_tsx = tsx.replace(good_expression, bad_expression, 1)
    broken_passes, diagnostic = typecheck(broken_tsx, css, 'jsx_conditional')
    fixed_passes, _ = typecheck(tsx, css, 'jsx_conditional_fixed')
    if broken_passes or not fixed_passes or 'error TS' not in diagnostic:
        raise ValueError('JSX conditional repair lacks an observed compiler failure and clean fix')
    (EVIDENCE / 'jsx_conditional' / 'diagnostic.txt').write_text(diagnostic, encoding='utf-8')
    jsx_row = {**copy.deepcopy(meta), 'task_id': 'reviewed_paperkite_jsx_conditional_repair',
               'category': 'repair',
               'repair_diagnostics': {'origin': 'fault injection; actual TypeScript diagnostic',
                                      'before_tsx': broken_tsx, 'compiler': diagnostic,
                                      'after_typecheck': True},
               'messages': [{'role': 'system', 'content': SITE_AGENT_SYSTEM_PROMPT},
                            {'role': 'user', 'content': 'Fix the invalid nested conditional in the Paperkite shop. '
                             'Keep the visible store and cart behavior unchanged. Return the full Shop.tsx and paired CSS.\n'
                             'Current Shop.tsx:\n' + broken_tsx + '\nCurrent Shop.css:\n' + css +
                             '\nObserved compiler output:\n' + diagnostic},
                            {'role': 'assistant', 'content': envelope('Shop', tsx, css)}]}
    jsx_row['native_encoded_tokens'] = len(encode_row(jsx_row, encoder, 8192, chat_tokenizer=native)['input_ids'])
    rows.append(jsx_row)

    bad_css, count = re.subn(r'\.kite-demo-note\{[^}]*\}', '', css, count=1)
    if count != 1:
        raise ValueError('CSS fault injection target is missing')
    static_tsx = re.sub(r'className=\{`[^`]*`\}', '', tsx)
    broken_coverage, missing = check_css_selector_coverage(static_tsx, bad_css)
    fixed_coverage, _ = check_css_selector_coverage(static_tsx, css)
    syntax_valid, syntax_errors = check_css_syntactic_completeness(bad_css)
    if broken_coverage or 'kite-demo-note' not in missing or not fixed_coverage or not syntax_valid:
        raise ValueError(f'CSS selector repair is not observable: {missing}, {syntax_errors}')
    diagnostic = f'Missing CSS selectors for classes used in Shop.tsx: {missing}'
    css_folder = EVIDENCE / 'missing_css_selector'
    css_folder.mkdir(parents=True, exist_ok=True)
    (css_folder / 'before.css').write_text(bad_css, encoding='utf-8')
    (css_folder / 'diagnostic.txt').write_text(diagnostic, encoding='utf-8')
    css_row = {**copy.deepcopy(meta), 'task_id': 'reviewed_paperkite_css_selector_repair',
               'category': 'repair',
               'repair_diagnostics': {'origin': 'fault injection; actual CSS selector validator diagnostic',
                                      'before_css': bad_css, 'validator': diagnostic,
                                      'after_selector_coverage': True},
               'messages': [{'role': 'system', 'content': SITE_AGENT_SYSTEM_PROMPT},
                            {'role': 'user', 'content': 'Fix the missing paired CSS selector without changing '
                             'the Paperkite shop markup, cart, or styling elsewhere. Return full Shop.tsx and Shop.css.\n'
                             'Current Shop.tsx:\n' + tsx + '\nCurrent Shop.css:\n' + bad_css +
                             '\nObserved validator output:\n' + diagnostic},
                            {'role': 'assistant', 'content': envelope('Shop', tsx, css)}]}
    css_row['native_encoded_tokens'] = len(encode_row(css_row, encoder, 8192, chat_tokenizer=native)['input_ids'])
    rows.append(css_row)
    errors = validate_reviewed_site_rows(rows, [])
    if errors:
        raise ValueError('\n'.join(errors))
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in rows), encoding='utf-8')
    print(json.dumps({'rows': len(rows), 'max_tokens': max(row['native_encoded_tokens'] for row in rows),
                      'dataset_sha256': sha256(TARGET), 'path': str(TARGET)}, indent=2))


if __name__ == '__main__':
    main()
