"""Audit serialized training targets against actual Qwen3 inference prefixes."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', default='data/full_site_training/train.jsonl')
    parser.add_argument('--output', default='runs/qwen3_non_thinking_format_audit.json')
    args = parser.parse_args()
    from tokenizers import Tokenizer
    from transformers import AutoTokenizer
    from agent.agent_protocol import format_chatml
    from training.preflight import read_jsonl, encode_row, sha256
    native = AutoTokenizer.from_pretrained(ROOT / 'base-model', local_files_only=True)
    encoder = Tokenizer.from_file(str(ROOT / 'base-model/tokenizer.json'))
    rows = read_jsonl(args.data)
    changed, mismatches, encoding_errors = [], [], []
    max_tokens = 0
    for row in rows:
        messages = row['messages']
        old = format_chatml(messages, False, tokenizer=encoder)
        new = format_chatml(messages, False, tokenizer=native)
        prefix = format_chatml(messages[:-1], True, tokenizer=native)
        if old != new:
            changed.append(row.get('task_id'))
        if not new.startswith(prefix):
            mismatches.append(row.get('task_id'))
        try:
            encoded = encode_row(row, encoder, 8192, chat_tokenizer=native)
            max_tokens = max(max_tokens, len(encoded['input_ids']))
        except ValueError as exc:
            encoding_errors.append({'task_id': row.get('task_id'), 'error': str(exc)})
    report = {'dataset': args.data, 'dataset_sha256': sha256(args.data), 'rows': len(rows),
        'legacy_native_different_count': len(changed), 'fixed_prefix_mismatches': mismatches,
        'encoding_errors': encoding_errors, 'max_native_tokens': max_tokens,
        'inference_suffix': prefix[-60:], 'training_target_policy': 'final assistant content and EOS; prompt including empty think prefix masked',
        'passed': not mismatches and not encoding_errors}
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
