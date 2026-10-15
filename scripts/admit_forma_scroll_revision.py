"""Admit the separately scored Forma scroll revision as immutable training evidence."""

from __future__ import annotations

import argparse
import copy
import csv
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent.site_prompt import SITE_AGENT_SYSTEM_PROMPT
from data_pipeline.reviewed_site_examples import validate_reviewed_site_rows
from evaluation.human_visual_review import RUBRIC_AXES
from scripts.build_diverse_curriculum import envelope
from training.preflight import encode_row, sha256

SOURCE = ROOT / 'data/diverse_reference/source/forma_scroll_v2'
VERIFICATION = ROOT / 'runs/diverse_reference_review/forma_scroll_v2/verification.json'
BANK = ROOT / 'data/reviewed_full_sites/evidence/forma_scroll_v2'
TARGET = ROOT / 'data/reviewed_full_sites/forma_scroll_v2.jsonl'
SECTIONS = ('Hero', 'Collection', 'Contact')
REQUESTS = (
    'Build the Forma navigation and editorial hero with warm stone, clay, a large serif headline '
    '"Less object. More presence.", and dimensional CSS blocks. Link #work and #contact. '
    'The sculpture must shift subtly with scroll, remove listeners on cleanup, and remain static under reduced motion.',
    'Build #work with Quiet Column, The Space Between, and Low Horizon sculptural CSS illustrations. '
    'All, Objects, and Studies filters must change visible items with aria-pressed and focus styling. '
    'Stagger the cards into view on scroll; make them immediately visible under reduced motion and clean up the observer.',
    'Build #contact as an honest fictional studio footer. Include a back-to-top link to #intro; do not fabricate contact details.',
)


def immutable_copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if sha256(destination) != sha256(source):
            raise ValueError(f'Immutable reviewed evidence differs: {destination}')
        return
    shutil.copy2(source, destination)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--human-scores', type=Path, required=True)
    args = parser.parse_args()
    with args.human_scores.open(encoding='utf-8-sig', newline='') as handle:
        scores = list(csv.DictReader(handle))
    if len(scores) != 1 or scores[0].get('site_id') != 'forma_scroll_v2':
        raise ValueError('Score file must contain exactly the Forma scroll v2 review')
    score = scores[0]
    if score.get('approved', '').strip().lower() != 'yes' or not score.get('reviewer_id', '').strip():
        raise ValueError('Explicit approval and reviewer ID are required')
    values = {axis: float(score[axis]) for axis in RUBRIC_AXES}
    if any(value < 3 or value > 5 for value in values.values()) or sum(values.values()) / len(values) < 4:
        raise ValueError('Every rubric score must be at least 3 and mean at least 4')
    verification = json.loads(VERIFICATION.read_text(encoding='utf-8'))
    if verification.get('passed') is not True or any(not item['passed'] for item in verification['interactions']):
        raise ValueError('Revision browser validation is incomplete')
    for filename, digest in verification['source_files'].items():
        if sha256(SOURCE / filename) != digest:
            raise ValueError(f'Source changed since browser validation: {filename}')

    immutable_copy(args.human_scores, BANK / 'human_scores.csv')
    immutable_copy(VERIFICATION, BANK / 'verification.json')
    for filename in verification['source_files']:
        immutable_copy(SOURCE / filename, BANK / 'source' / filename)
    evidence = {}
    for mode, capture in verification['browser_evidence']['captures'].items():
        archived = {key: value for key, value in capture.items() if key not in ('screenshot', 'scroll_video')}
        for kind in ('screenshot', 'scroll_video'):
            original = Path(capture[kind])
            destination = BANK / 'captures' / original.name
            immutable_copy(original, destination)
            archived[kind] = str(destination)
            archived[kind + '_sha256'] = sha256(destination)
        evidence[mode] = archived

    review = {'reviewer_id': score['reviewer_id'].strip(), 'rubric_scores': values,
              'notes': score.get('notes', ''), 'review_type': 'human_visual',
              'review_form_sha256': sha256(BANK / 'human_scores.csv'),
              'review_form': str(BANK / 'human_scores.csv')}
    meta = {'family_id': 'original_diverse_forma', 'domain': 'portfolio',
            'source': str((BANK / 'source').relative_to(ROOT)),
            'license': 'MIT (repository LICENSE)',
            'source_files': verification['source_files'],
            'validation': {'typecheck': True, 'build': True, 'runtime': True, 'interaction': True},
            'browser_evidence': evidence,
            'provenance': {'author': 'Codex', 'origin': 'authored Forma revision; not a native model result',
                           'supersedes': 'diverse_forma_hero and diverse_forma_collection only for this site version'},
            'visual_review': review, 'admission_status': 'reviewed'}

    from tokenizers import Tokenizer
    from transformers import AutoTokenizer
    encoder = Tokenizer.from_file(str(ROOT / 'base-model/tokenizer.json'))
    native = AutoTokenizer.from_pretrained(ROOT / 'base-model', local_files_only=True)
    history = [{'role': 'system', 'content': SITE_AGENT_SYSTEM_PROMPT}]
    rows = []
    for section, request in zip(SECTIONS, REQUESTS):
        tsx = (BANK / 'source' / f'{section}.tsx').read_text(encoding='utf-8')
        css = (BANK / 'source' / f'{section}.css').read_text(encoding='utf-8')
        user = ('Build the complete Forma object-design portfolio, one section at a time in the order '
                'Hero, Collection, Contact. The host supplies border-box sizing, body margin 0, Arial, '
                'and reduced-motion-aware anchor scrolling. ' + request + ' Write only '
                f'src/components/{section}.tsx and {section}.css with a paired CSS import and named plus default export.')
        history.extend(({'role': 'user', 'content': user},
                        {'role': 'assistant', 'content': envelope(section, tsx, css)}))
        row = {**copy.deepcopy(meta), 'task_id': f'diverse_forma_scroll_v2_{section.lower()}',
               'category': 'full_site', 'messages': copy.deepcopy(history)}
        row['native_encoded_tokens'] = len(encode_row(row, encoder, 8192, chat_tokenizer=native)['input_ids'])
        rows.append(row)

    section = 'Collection'
    tsx = (BANK / 'source' / 'Collection.tsx').read_text(encoding='utf-8')
    css = (BANK / 'source' / 'Collection.css').read_text(encoding='utf-8')
    good, bad = 'setFilter(item)', 'setFiltre(item)'
    if good not in tsx:
        raise ValueError('Repair injection target is missing')
    broken = tsx.replace(good, bad, 1)
    probe = BANK / 'repair_probe'
    probe.mkdir(parents=True, exist_ok=True)
    (probe / f'{section}.tsx').write_text(broken, encoding='utf-8')
    (probe / f'{section}.css').write_text(css, encoding='utf-8')
    (probe / 'globals.d.ts').write_text("declare module '*.css';", encoding='utf-8')
    command = ['node', str(ROOT / 'node_modules/typescript/bin/tsc'), '--noEmit', '--jsx', 'react-jsx',
               '--module', 'ESNext', '--moduleResolution', 'bundler', '--target', 'ES2020',
               '--lib', 'ES2020,DOM', '--skipLibCheck', '--allowSyntheticDefaultImports',
               str(probe / f'{section}.tsx'), str(probe / 'globals.d.ts')]
    failed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=60)
    if failed.returncode == 0:
        raise ValueError('Injected repair fault unexpectedly typechecks')
    diagnostic = (failed.stdout + failed.stderr).replace(str(probe), 'src/components').replace(str(ROOT), '[workspace]')
    (probe / 'diagnostic.txt').write_text(diagnostic, encoding='utf-8')
    (probe / 'before.tsx.txt').write_text(broken, encoding='utf-8')
    (probe / f'{section}.tsx').write_text(tsx, encoding='utf-8')
    fixed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=60)
    if fixed.returncode:
        raise ValueError('Correct repair does not typecheck')
    repair = {**copy.deepcopy(meta), 'task_id': 'diverse_forma_scroll_v2_repair',
              'category': 'repair',
              'repair_diagnostics': {'origin': 'authored fault injection; actual compiler output',
                                     'before': broken, 'compiler': diagnostic, 'after_typecheck': True},
              'messages': [{'role': 'system', 'content': SITE_AGENT_SYSTEM_PROMPT},
                           {'role': 'user', 'content': 'Repair this Forma Collection component without changing its appearance or behavior. '
                            'Return the complete corrected TSX and unchanged paired CSS.\nCurrent src/components/Collection.tsx:\n'
                            + broken + '\nCurrent CSS:\n' + css + '\nObserved compiler diagnostic:\n' + diagnostic},
                           {'role': 'assistant', 'content': envelope(section, tsx, css)}]}
    repair['native_encoded_tokens'] = len(encode_row(repair, encoder, 8192, chat_tokenizer=native)['input_ids'])
    rows.append(repair)
    errors = validate_reviewed_site_rows(rows, [])
    if errors:
        raise ValueError('\n'.join(errors))
    rendered = ''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in rows)
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    if TARGET.exists() and TARGET.read_text(encoding='utf-8') != rendered:
        raise ValueError(f'Immutable reviewed dataset differs: {TARGET}')
    TARGET.write_text(rendered, encoding='utf-8')
    print(json.dumps({'rows': len(rows), 'mean_score': sum(values.values()) / len(values),
                      'reviewer': review['reviewer_id'], 'max_tokens': max(row['native_encoded_tokens'] for row in rows),
                      'dataset_sha256': sha256(TARGET), 'path': str(TARGET)}, indent=2))


if __name__ == '__main__':
    main()
