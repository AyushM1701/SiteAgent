"""Regression tests using the actual local Qwen3 template, not a ChatML mock."""
from pathlib import Path

import pytest
from tokenizers import Tokenizer

from agent.agent_protocol import format_chatml
from training.preflight import encode_row

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module')
def native():
    from transformers import AutoTokenizer
    if not (ROOT / 'base-model/tokenizer_config.json').exists():
        pytest.skip('Local Qwen3 tokenizer not installed')
    return AutoTokenizer.from_pretrained(ROOT / 'base-model', local_files_only=True)


def test_actual_template_target_continues_inference_and_masks_prefix(native):
    rust = Tokenizer.from_file(str(ROOT / 'base-model/tokenizer.json'))
    messages = [
        {'role': 'system', 'content': 'Build sites.'},
        {'role': 'user', 'content': 'Start'},
        {'role': 'assistant', 'content': '<finish>Previous</finish>'},
        {'role': 'user', 'content': 'Now finish'},
        {'role': 'assistant', 'content': '<finish>Complete</finish>'},
    ]
    prefix = format_chatml(messages[:-1], True, tokenizer=native)
    completed = format_chatml(messages, False, tokenizer=native)
    assert prefix.endswith('<think>\n\n</think>\n\n')
    assert completed == prefix + messages[-1]['content'] + '<|im_end|>\n'
    encoded = encode_row({'messages': messages}, rust, 8192, chat_tokenizer=native)
    assert encoded['input_ids'] == native(completed, add_special_tokens=False)['input_ids']
    target = rust.decode([v for v in encoded['labels'] if v != -100], skip_special_tokens=False)
    assert target == '<finish>Complete</finish><|im_end|>'
    assert encoded['labels'][:len(native(prefix, add_special_tokens=False)['input_ids'])] == [-100] * len(native(prefix, add_special_tokens=False)['input_ids'])


def test_legacy_encoding_is_demonstrably_different(native):
    rust = Tokenizer.from_file(str(ROOT / 'base-model/tokenizer.json'))
    messages = [{'role': 'user', 'content': 'Start'}, {'role': 'assistant', 'content': '<finish>Done</finish>'}]
    assert format_chatml(messages, False, tokenizer=rust) != format_chatml(messages, False, tokenizer=native)
