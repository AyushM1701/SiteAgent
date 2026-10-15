"""Inventory actual curriculum supervision and verifiable review artifacts."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re

from training.preflight import sha256


def audit(path):
    rows = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
    actions, families = Counter(), set()
    stats = Counter()
    for row in rows:
        families.add(row.get('family_id') or row.get('task_id'))
        assistant = [m.get('content', '') for m in row.get('messages', []) if m.get('role') == 'assistant']
        targets = [assistant[-1]] if assistant else [row.get('chosen', '')]
        for target in targets:
            match = re.search(r'<tool_call\s+name=["\']([^"\']+)', target)
            actions[match.group(1) if match else 'finish' if '<finish' in target else 'other'] += 1
            stats['targets_with_navigation'] += bool(re.search(r'<nav\b', target))
            stats['targets_with_main_file'] += 'src/components/Main.tsx' in target
            stats['targets_with_styled_jsx'] += bool(re.search(r'<style\s+jsx\b', target))
        stats['rows_with_source'] += bool(row.get('source'))
        stats['rows_with_visual_review'] += bool(row.get('visual_review'))
        stats['rows_with_preference_metadata'] += bool(row.get('preference_metadata'))
        stats['rows_with_named_preference_reviewer'] += bool((row.get('preference_metadata') or {}).get('reviewer_id'))
        for field in ('chosen_verification_receipt', 'rejected_verification_receipt'):
            receipt = row.get(field) or {}
            stats['inline_verification_receipts'] += bool(receipt)
            # A provenance word and true flags cannot verify browser execution.
            artifact = Path(str(receipt.get('path') or ''))
            stats['receipts_with_matching_artifact'] += bool(artifact.is_file() and receipt.get('sha256') == sha256(artifact))
    return {'dataset': str(path.resolve()), 'sha256': sha256(path), 'rows': len(rows),
            'families': len(families), 'final_target_actions': dict(actions), 'evidence_counts': dict(stats)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    paths = sorted(Path('data/curriculum').glob('*.jsonl')) + [Path('data/full_site_training_v3/train.jsonl')]
    result = {'purpose': 'Evidence inventory; inline receipts are not independently verified passes',
              'datasets': [audit(path) for path in paths if path.is_file()]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))
