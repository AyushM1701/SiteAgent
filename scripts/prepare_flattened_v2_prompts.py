"""Correct the full-site request text while preserving pixel-verified source and review."""

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_pipeline.reviewed_site_examples import validate_reviewed_site_rows
from scripts.build_flattened_reviewed_sites import BRIEFS
from training.preflight import encode_row, sha256

SOURCE = ROOT / 'data/reviewed_full_sites/flattened_v1.jsonl'
TARGET = ROOT / 'data/reviewed_full_sites/flattened_v2.jsonl'
SOURCE_SHA256 = '43e558204644b8457d3fd416c8dbffdf1bbd375f0a2393278407417a07f6d0e2'


def main() -> None:
    if sha256(SOURCE) != SOURCE_SHA256:
        raise ValueError('Source dataset changed; review the correction before applying it')
    if TARGET.exists():
        raise ValueError(f'Corrected dataset already exists: {TARGET}')
    from tokenizers import Tokenizer
    from transformers import AutoTokenizer
    encoder = Tokenizer.from_file(str(ROOT / 'base-model/tokenizer.json'))
    native = AutoTokenizer.from_pretrained(ROOT / 'base-model', local_files_only=True)
    rows = [json.loads(line) for line in SOURCE.read_text(encoding='utf-8').splitlines()]
    for row in rows:
        site = row['task_id'].removeprefix('flattened_').removesuffix('_main')
        if site not in BRIEFS:
            raise ValueError(f'Unexpected source task {row["task_id"]}')
        report = json.loads(Path(row['provenance']['pixel_equivalence_report']).read_text(encoding='utf-8'))
        if not report['passed'] or not all(mode['dom_identical'] and mode['pixels_identical']
                                           for mode in report['pixel_equivalence'].values()):
            raise ValueError(f'Pixel equivalence is not established for {site}')
        row['messages'][1]['content'] = (
            f'Build the complete {site.replace("_", " ")} website as one self-contained React Main component '
            'and paired Main.css. Include all sections, navigation, visual composition, and working interactions. '
            'Return exactly src/components/Main.tsx and Main.css with named and default Main exports. '
            + BRIEFS[site])
        row['provenance']['prompt_revision'] = 'v2: removed conflicting section-only instruction; source and rendering unchanged'
        row['native_encoded_tokens'] = len(encode_row(row, encoder, 8192, chat_tokenizer=native)['input_ids'])
    errors = validate_reviewed_site_rows(rows, [])
    if errors:
        raise ValueError('\n'.join(errors))
    TARGET.write_text(''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in rows), encoding='utf-8')
    print(json.dumps({'rows': len(rows), 'max_tokens': max(row['native_encoded_tokens'] for row in rows),
                      'dataset_sha256': sha256(TARGET), 'path': str(TARGET)}, indent=2))


if __name__ == '__main__':
    main()
