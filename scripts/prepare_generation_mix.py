"""Build an immutable generation-focused mix; keep unreviewed legacy rows separate."""
import argparse
from collections import Counter, defaultdict
import copy
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from training.preflight import read_jsonl, sha256, check_holdout, prepare_rows
from scripts.prepare_full_v2_training import normalize, site_contract_errors


def classify_target(row):
    messages = row.get('messages') or []
    if not messages or messages[-1].get('role') != 'assistant':
        return 'excluded', 'missing final assistant target'
    target = messages[-1].get('content', '')
    from agent.agent_protocol import parse_agent_output
    action = parse_agent_output(target).action
    files = dict(getattr(action, 'files', []))
    if '<finish' in target or re.search(r'<tool_call\s+name=["\']finish', target):
        prior_writes = [m for m in messages[:-1] if m.get('role') == 'assistant' and 'write_site' in m.get('content', '')]
        observations = [m for m in messages[:-1] if m.get('role') == 'tool']
        if prior_writes and observations:
            try:
                observation = json.loads(observations[-1]['content'])
            except (ValueError, TypeError):
                observation = {}
            if observation.get('status') == 'accepted' and observation.get('project_complete') is True:
                return 'finish', 'preceding project generation and accepted completion observation'
        return 'excluded', 'finish has no preceding generated and accepted complete project'
    if not files:
        return 'excluded', 'not a paired site-file action'
    if row.get('category') == 'repair':
        diagnostics = row.get('repair_diagnostics') or {}
        if not any(diagnostics.get(key) for key in ('compiler', 'dom', 'interaction', 'css', 'validator')):
            return 'excluded', 'repair lacks concrete diagnostics'
        return 'repair', 'paired files with recorded repair diagnostics'
    if 'src/components/Main.tsx' in files and 'src/components/Main.css' in files:
        return 'complete_site', 'self-contained Main file pair'
    request = '\n'.join(m.get('content', '') for m in messages if m.get('role') == 'user')
    if re.search(r'\b(?:section scope|write only|write the .*? section)\b', request, re.I):
        return 'section', 'explicit section request with project brief'
    return 'excluded', 'isolated section target contradicts complete-site request'


def scope_section_row(row, siblings):
    scoped = copy.deepcopy(row)
    from agent.agent_protocol import parse_agent_output
    files = dict(getattr(parse_agent_output(scoped['messages'][-1]['content']).action, 'files', []))
    symbols = [Path(path).stem for path in files if path.endswith('.tsx')]
    if len(symbols) != 1 or symbols[0] == 'Main':
        return scoped
    user = next((m for m in reversed(scoped['messages'][:-1]) if m.get('role') == 'user'), None)
    if user:
        user['content'] += (f'\nSection scope: implement only {symbols[0]} in this turn, including its paired CSS. '
                            'The complete brief above supplies project context. The host composes the supplied '
                            f'section modules: {", ".join(siblings)}. Do not claim the full project is complete.')
        scoped['scope_alignment'] = {'symbol': symbols[0], 'sibling_modules': siblings,
                                    'assistant_source_modified': False}
    return scoped


def mark_final_target(row):
    """These rows already select one prefix/target; earlier assistants are context."""
    result = copy.deepcopy(row)
    turns = sum(message.get('role') == 'assistant' for message in result['messages'])
    result['exploded_turn'] = turns
    result['total_turns'] = turns
    result['supervision_scope'] = 'final_assistant_only; already selected prefix-target pair'
    return result


def build(output, reviewed_paths):
    legacy_path = ROOT / 'data/full_site_training_v3/train.jsonl'
    validation_path = ROOT / 'data/full_site_training_v3/validation.jsonl'
    legacy = [r for r in read_jsonl(legacy_path) if not r.get('visual_review')]
    validation = read_jsonl(validation_path)
    from agent.agent_protocol import parse_agent_output
    families = defaultdict(set)
    for row in legacy + validation:
        files = getattr(parse_agent_output(row['messages'][-1]['content']).action, 'files', [])
        families[str(row.get('family_id'))].update(Path(path).stem for path, _ in files if path.endswith('.tsx'))
    exclusions, pool, heldout = [], [], []
    for split, rows in (('legacy_pool', legacy), ('validation', validation)):
        for row in rows:
            scoped = scope_section_row(row, sorted(families[str(row.get('family_id'))]))
            kind, reason = classify_target(scoped)
            errors = site_contract_errors(scoped) if kind != 'excluded' else []
            if kind == 'excluded' or errors:
                exclusions.append({'split': split, 'task_id': row.get('task_id'), 'reason': reason, 'errors': errors})
            else:
                scoped['supervision_kind'] = kind
                scoped['admission_status'] = 'legacy_technical_pool_requires_visual_review'
                (pool if split == 'legacy_pool' else heldout).append(mark_final_target(normalize(scoped)))
    reviewed = [row for path in reviewed_paths for row in read_jsonl(path)]
    train = []
    for row in reviewed:
        kind, reason = classify_target(row)
        if kind == 'excluded':
            raise ValueError(f'Reviewed row {row.get("task_id")} has invalid supervision: {reason}')
        item = normalize(row)
        item['supervision_kind'] = kind
        train.append(mark_final_target(item))
    from data_pipeline.reviewed_site_examples import require_reviewed_training_examples
    require_reviewed_training_examples(train, heldout)
    if len({r['task_id'] for r in train}) != len(train):
        raise ValueError('Duplicate reviewed task IDs')
    check_holdout(train, heldout)
    check_holdout(pool, heldout)
    from tokenizers import Tokenizer
    from transformers import AutoTokenizer
    encoder = Tokenizer.from_file(str(ROOT / 'base-model/tokenizer.json'))
    native = AutoTokenizer.from_pretrained(ROOT / 'base-model', local_files_only=True)
    encoded = prepare_rows(train, encoder, 8192, chat_tokenizer=native)
    prepare_rows(heldout, encoder, 8192, chat_tokenizer=native)
    output.mkdir(parents=True, exist_ok=False)
    for name, rows in (('train', train), ('validation', heldout), ('legacy_pool', pool)):
        (output / f'{name}.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows), encoding='utf-8')
    (output / 'excluded_rows.json').write_text(json.dumps(exclusions, indent=2), encoding='utf-8')
    manifest = {'status': 'reviewed_generation_mix_requires_native_gate_and_preflight',
        'training_started': False, 'train_rows': len(train), 'validation_rows': len(heldout),
        'legacy_pool_rows_not_admitted': len(pool), 'excluded_rows': len(exclusions),
        'train_target_types': dict(Counter(r['supervision_kind'] for r in train)),
        'train_families': len({r['family_id'] for r in train}), 'train_domains': sorted({r['domain'] for r in train}),
        'max_encoded_tokens': max(len(row['input_ids']) for row in encoded),
        'source_sha256': {str(p): sha256(p) for p in [legacy_path, validation_path, *reviewed_paths]},
        'output_sha256': {p.name: sha256(p) for p in output.glob('*.jsonl')},
        'policy': 'Only reviewed rows enter train.jsonl. Legacy rows remain a separate unreviewed pool; no assistant targets rewritten.'}
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--reviewed', type=Path, action='append', required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.output, args.reviewed), indent=2))
