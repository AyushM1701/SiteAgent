"""Combine bounded replay and original reference records without changing holdouts."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tokenizers import Tokenizer
from training.preflight import read_jsonl, encode_row, check_holdout, sha256


def build():
    sources = [ROOT/'data/quality_candidate/train.jsonl', ROOT/'data/premium_reference/train.jsonl']
    validation = ROOT/'data/quality_candidate/validation.jsonl'
    tokenizer_path = ROOT/'my-react-agent-lora/tokenizer.json'
    tokenizer = Tokenizer.from_file(str(tokenizer_path))
    accepted, rejected, seen = [], [], set()
    for source in sources:
        for row in read_jsonl(source):
            try:
                encode_row(row, tokenizer, 8192)
                fingerprint = json.dumps(row['messages'], sort_keys=True)
                if fingerprint in seen:
                    raise ValueError('duplicate conversation')
                seen.add(fingerprint)
                accepted.append(row)
            except ValueError as error:
                rejected.append({'task_id':row.get('task_id'), 'reason':str(error)})
    check_holdout(accepted, read_jsonl(validation))
    destination = ROOT/'data/premium_training'
    destination.mkdir(exist_ok=True)
    train_path = destination/'train.jsonl'
    train_path.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in accepted),encoding='utf-8')
    (destination/'rejections.json').write_text(json.dumps(rejected,indent=2)+'\n',encoding='utf-8')
    report = {'accepted':len(accepted), 'rejected':len(rejected), 'independent_families':len({r['family_id'] for r in accepted}),
              'source_hashes':{str(s.relative_to(ROOT)):sha256(s) for s in sources},
              'train_sha256':sha256(train_path), 'validation_sha256':sha256(validation),
              'tokenizer_sha256':sha256(tokenizer_path),
              'limitation':'Protocol-valid does not imply visually approved. Existing replay data retains its original quality limitations.'}
    (destination/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    build()
