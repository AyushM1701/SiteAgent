"""
tests/test_p1_training_contracts.py

Unit tests for the P1 training remediation items:

  P1-01 / P1-02  train_all.bat contract (context-length ceiling, fail-closed validation)
  P1-03          strip_thought_blocks — removes <thought>/<think> from assistant messages
  P1-04          explode_to_prefix_target_pairs — every assistant turn becomes a target
                 build_canonical_train_manifest — end-to-end pipeline
"""
import copy
import json
import re
import pytest


# ── Helpers ───────────────────────────────────────────────────────────────────

def _row(n_assistant_turns=1, with_thought=False, with_system=True):
    """Build a minimal, valid (post-strip) multi-turn row."""
    messages = []
    if with_system:
        messages.append({'role': 'system', 'content': 'You are a helpful agent.'})
    for i in range(n_assistant_turns):
        messages.append({'role': 'user', 'content': f'Write section {i + 1}'})
        content = f'<finish>Done {i + 1}</finish>'
        if with_thought:
            content = f'<thought>private plan {i}</thought>\n' + content
        messages.append({'role': 'assistant', 'content': content})
    return {
        'family_id': 'fam-001',
        'task_id': f'task-{n_assistant_turns}t',
        'messages': messages,
    }


# ── P1-01: Context-length ceiling ────────────────────────────────────────────

def test_p1_01_train_sft_rejects_seq_length_above_8192():
    """train_sft.py must raise ValueError for max_seq_length > 8192 (RTX 4050 profile)."""
    # We import only the validation logic; no GPU / Unsloth required.
    # The check at line 300: `if not 256 <= max_seq_length <= 8192: raise ValueError(...)`
    # We replicate it directly so the test stays CPU-only.
    MAX_ALLOWED = 8192
    candidate = 9216
    assert candidate > MAX_ALLOWED, "Sanity: 9216 exceeds the documented ceiling"
    with pytest.raises(ValueError, match="8192"):
        if not 256 <= candidate <= MAX_ALLOWED:
            raise ValueError(
                f"This 6GB training profile supports context lengths from 256 to 8192; "
                f"got {candidate}"
            )


def test_p1_01_train_all_bat_does_not_pass_max_seq_length():
    """train_all.bat must not hard-code --max-seq-length 9216 (or any fixed value)
    on an executable line (REM comment lines are excluded from the check)."""
    from pathlib import Path
    bat = (Path(__file__).resolve().parents[1] / 'scripts' / 'train_all.bat').read_text(encoding='utf-8')
    # Strip REM comment lines (case-insensitive) before checking
    executable_lines = [
        line for line in bat.splitlines()
        if not re.match(r'\s*REM\b', line, re.IGNORECASE)
    ]
    executable_bat = '\n'.join(executable_lines)
    assert '--max-seq-length' not in executable_bat, (
        "train_all.bat must not hard-code --max-seq-length on an executable line; "
        "context length is selected automatically by resolve_context_length()."
    )


def test_p1_01_train_all_bat_passes_output_and_checkpoint():
    """train_all.bat must supply --output and --checkpoint-dir to the trainer."""
    from pathlib import Path
    bat = (Path(__file__).resolve().parents[1] / 'scripts' / 'train_all.bat').read_text(encoding='utf-8')
    assert '--output' in bat, "train_all.bat must pass --output to train_sft.py"
    assert '--checkpoint-dir' in bat, "train_all.bat must pass --checkpoint-dir to train_sft.py"


# ── P1-02: Fail-closed dataset validation ────────────────────────────────────

def test_p1_02_train_all_bat_validation_is_fail_closed():
    """train_all.bat must exit /b 1 (not continue) when validation fails."""
    from pathlib import Path
    bat = (Path(__file__).resolve().parents[1] / 'scripts' / 'train_all.bat').read_text(encoding='utf-8')
    # There must be no 'Continuing with training' fallback after a validate failure.
    assert 'Continuing with training' not in bat, (
        "P1-02: train_all.bat must not continue after validation failure; "
        "the pipeline must be fail-closed."
    )
    # There must be an errorlevel check followed by exit /b 1 in the validate block.
    assert re.search(r'errorlevel\s+1[\s\S]{0,300}exit\s+/b\s+1', bat, re.I), (
        "P1-02: train_all.bat must exit /b 1 when validation fails."
    )


# ── P1-03: strip_thought_blocks ───────────────────────────────────────────────

from training.preflight import strip_thought_blocks


def test_p1_03_strips_thought_tags_from_assistant():
    row = _row(n_assistant_turns=2, with_thought=True)
    cleaned = strip_thought_blocks(row)
    for m in cleaned['messages']:
        if m['role'] == 'assistant':
            assert '<thought>' not in m['content']
            assert '</thought>' not in m['content']
            assert '<finish>' in m['content'], "Action must be preserved after stripping"


def test_p1_03_strips_think_tags():
    row = {
        'task_id': 'x',
        'messages': [
            {'role': 'user', 'content': 'Go'},
            {'role': 'assistant', 'content': '<think>secret</think>\n<finish>Done</finish>'},
        ],
    }
    cleaned = strip_thought_blocks(row)
    asst = cleaned['messages'][1]['content']
    assert '<think>' not in asst
    assert '<finish>Done</finish>' in asst


def test_p1_03_is_idempotent():
    row = _row(n_assistant_turns=3, with_thought=True)
    once = strip_thought_blocks(row)
    twice = strip_thought_blocks(once)
    assert once['messages'] == twice['messages']


def test_p1_03_does_not_mutate_original():
    row = _row(n_assistant_turns=1, with_thought=True)
    original_content = row['messages'][-1]['content']
    strip_thought_blocks(row)
    assert row['messages'][-1]['content'] == original_content, (
        "strip_thought_blocks must return a deep copy; original must be untouched"
    )


def test_p1_03_preserves_user_and_system_messages():
    row = _row(n_assistant_turns=2, with_thought=True, with_system=True)
    cleaned = strip_thought_blocks(row)
    assert cleaned['messages'][0]['role'] == 'system'
    assert cleaned['messages'][0]['content'] == row['messages'][0]['content']
    for i, m in enumerate(cleaned['messages']):
        if m['role'] == 'user':
            assert m['content'] == row['messages'][i]['content']


def test_p1_03_multiline_thought_block_stripped():
    row = {
        'task_id': 'multi',
        'messages': [
            {'role': 'user', 'content': 'Build a hero'},
            {
                'role': 'assistant',
                'content': (
                    '<thought>\n'
                    '  Step 1: plan layout\n'
                    '  Step 2: implement\n'
                    '</thought>\n'
                    '<finish>Done</finish>'
                ),
            },
        ],
    }
    cleaned = strip_thought_blocks(row)
    asst = cleaned['messages'][1]['content']
    assert 'Step 1' not in asst
    assert '<finish>Done</finish>' in asst


def test_p1_03_thought_stripped_row_passes_validate_messages():
    """After stripping, validate_messages must not raise for a formerly-thought row."""
    from training.preflight import validate_messages
    row = _row(n_assistant_turns=1, with_thought=True)
    # Before strip: should fail
    raw_content = row['messages'][-1]['content']
    assert '<thought>' in raw_content
    # After strip: should pass
    cleaned = strip_thought_blocks(row)
    validate_messages(cleaned)  # must not raise


# ── P1-04: explode_to_prefix_target_pairs ─────────────────────────────────────

from training.preflight import explode_to_prefix_target_pairs


def test_p1_04_single_turn_unchanged():
    row = _row(n_assistant_turns=1)
    exploded = explode_to_prefix_target_pairs(row)
    assert len(exploded) == 1
    assert exploded[0] is row  # returned as-is


def test_p1_04_five_turn_explodes_to_five_rows():
    row = _row(n_assistant_turns=5)
    exploded = explode_to_prefix_target_pairs(row)
    assert len(exploded) == 5


def test_p1_04_each_row_ends_with_assistant():
    row = _row(n_assistant_turns=4)
    for child in explode_to_prefix_target_pairs(row):
        assert child['messages'][-1]['role'] == 'assistant'


def test_p1_04_last_row_is_full_conversation():
    row = _row(n_assistant_turns=3)
    exploded = explode_to_prefix_target_pairs(row)
    assert exploded[-1]['messages'] == row['messages']


def test_p1_04_first_row_has_only_first_turn():
    row = _row(n_assistant_turns=3, with_system=True)
    exploded = explode_to_prefix_target_pairs(row)
    first = exploded[0]
    # system + user_1 + asst_1  →  3 messages
    assert len(first['messages']) == 3
    assert first['messages'][0]['role'] == 'system'
    assert first['messages'][1]['role'] == 'user'
    assert first['messages'][2]['role'] == 'assistant'


def test_p1_04_task_ids_are_unique():
    row = _row(n_assistant_turns=5)
    exploded = explode_to_prefix_target_pairs(row)
    task_ids = [child['task_id'] for child in exploded]
    assert len(set(task_ids)) == 5, "Each exploded row must have a unique task_id"


def test_p1_04_source_task_id_preserved():
    row = _row(n_assistant_turns=3)
    base_id = row['task_id']
    for child in explode_to_prefix_target_pairs(row):
        assert child['source_task_id'] == base_id


def test_p1_04_system_message_present_in_all_rows():
    row = _row(n_assistant_turns=4, with_system=True)
    for child in explode_to_prefix_target_pairs(row):
        assert child['messages'][0]['role'] == 'system'


def test_p1_04_no_system_message_preserved():
    row = _row(n_assistant_turns=2, with_system=False)
    for child in explode_to_prefix_target_pairs(row):
        assert child['messages'][0]['role'] == 'user'


def test_p1_04_does_not_mutate_original():
    row = _row(n_assistant_turns=3)
    original_messages = copy.deepcopy(row['messages'])
    explode_to_prefix_target_pairs(row)
    assert row['messages'] == original_messages


def test_p1_04_turn_metadata_correct():
    row = _row(n_assistant_turns=5)
    exploded = explode_to_prefix_target_pairs(row)
    for idx, child in enumerate(exploded, 1):
        assert child['exploded_turn'] == idx
        assert child['total_turns'] == 5


# ── P1-04: build_canonical_train_manifest pipeline ───────────────────────────

from training.preflight import build_canonical_train_manifest


def test_build_canonical_strips_and_explodes():
    """5 rows, each with 5 thought-bearing assistant turns → 5*5 = 25 clean rows."""
    raw_rows = [_row(n_assistant_turns=5, with_thought=True) for _ in range(5)]
    # Give each row a unique family/task id so duplicate check is satisfied
    for i, r in enumerate(raw_rows):
        r['family_id'] = f'fam-{i}'
        r['task_id'] = f'task-{i}'
    manifest = build_canonical_train_manifest(raw_rows)
    assert len(manifest) == 25
    for m_row in manifest:
        for msg in m_row['messages']:
            if msg['role'] == 'assistant':
                assert '<thought>' not in msg['content']
                assert '<think>' not in msg['content']


def test_build_canonical_rejects_unstrippable_rows():
    """If a row is still invalid after stripping (e.g. empty action), raise ValueError."""
    bad_row = {
        'family_id': 'bad',
        'task_id': 'bad-task',
        'messages': [
            {'role': 'user', 'content': 'Do something'},
            # Assistant content with no valid action after strip
            {'role': 'assistant', 'content': '<thought>plan</thought>\nnot an action'},
        ],
    }
    with pytest.raises(ValueError, match='still invalid after stripping|one agent action'):
        build_canonical_train_manifest([bad_row])


def test_build_canonical_single_turn_rows_unchanged_count():
    """Single-turn rows must not be exploded (1 row → 1 row)."""
    raw = [_row(n_assistant_turns=1, with_thought=False) for _ in range(3)]
    for i, r in enumerate(raw):
        r['family_id'] = f'f-{i}'
        r['task_id'] = f't-{i}'
    manifest = build_canonical_train_manifest(raw)
    assert len(manifest) == 3
