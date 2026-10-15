"""Build a versioned, statically screened candidate; never mark it visually approved.

All supervised assistant turns are checked, not just the last repaired answer.
Rejected records remain traceable to immutable source hashes.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from agent.agent_protocol import parse_agent_output, WriteSiteAction
from agent.site_acceptance import check_site_files
from training.preflight import read_jsonl, validate_messages, check_holdout, sha256


def screen(row):
    """Return static defects and a code-only signature, ignoring prompt paraphrases."""
    validate_messages(row)
    errors, targets = [], []
    for message in row['messages']:
        if message['role'] != 'assistant':
            continue
        action = parse_agent_output(message['content']).action
        if isinstance(action, WriteSiteAction):
            files = dict(action.files)
            errors.extend(check_site_files(files)['errors'])
            targets.append(sorted((path, code.strip()) for path, code in files.items()))
        else:
            targets.append(message['content'].strip())
    signature = hashlib.sha256(json.dumps(targets, sort_keys=True).encode()).hexdigest()
    return sorted(set(errors)), signature


def build(output):
    source = ROOT / 'data/premium_training/train.jsonl'
    validation = ROOT / 'data/quality_candidate/validation.jsonl'
    output = Path(output).resolve()
    if output.exists():
        raise ValueError('Use a new output directory; prior dataset evidence is immutable')
    accepted, rejected, signatures = [], [], set()
    for index, row in enumerate(read_jsonl(source), 1):
        try:
            defects, signature = screen(row)
            if signature in signatures:
                defects.append('Duplicate assistant target despite different prompt/context')
            if defects:
                rejected.append({'source_line': index, 'task_id': row.get('task_id'), 'reasons': defects})
                continue
            signatures.add(signature)
            accepted.append(row)
        except ValueError as error:
            rejected.append({'source_line': index, 'task_id': row.get('task_id'), 'reasons': [str(error)]})
    if not accepted:
        raise ValueError('No survivors; do not start training')
    check_holdout(accepted, read_jsonl(validation))
    output.mkdir(parents=True)
    train = output / 'train.jsonl'
    train.write_text(''.join(json.dumps(r, ensure_ascii=False)+'\n' for r in accepted), encoding='utf-8')
    (output/'rejections.json').write_text(json.dumps(rejected, indent=2)+'\n', encoding='utf-8')
    family_counts = Counter(str(r['family_id']) for r in accepted)
    report = {
        'accepted': len(accepted), 'rejected': len(rejected),
        'family_counts': dict(family_counts), 'independent_families': len(family_counts),
        'largest_family_fraction': max(family_counts.values()) / len(accepted),
        'source_sha256': sha256(source), 'validation_sha256': sha256(validation),
        'train_sha256': sha256(train),
        'training_ready': False,
        'remaining_gates': ['Review family/style balance after filtering',
                            'Compile and browser-test survivors; static checks cannot verify interactions',
                            'Add independently reviewed original 3D and tool-feedback trajectories',
                            'Run tokenizer/context preflight before training'],
        'limitation': 'Static screening only. No model weights changed and no visual quality claim.'}
    (output/'report.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k != 'family_counts'}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default=str(ROOT/'data/quality_v2'))
    build(parser.parse_args().output)
