"""CPU-only, fail-closed dataset and output checks shared by training and tests."""
import copy
import hashlib
import json
from pathlib import Path
import re

from agent.agent_protocol import format_chatml, parse_agent_output, WriteSiteAction, WriteComponentAction

# Qwen ChatML role boundary markers (Qwen2.5 and Qwen3) plus Qwen3's native
# thinking tokens.  None of these must appear in message content — they would
# corrupt the tokeniser's role-boundary detection and loss-mask offsets.
CHAT_MARKERS = ('<|im_start|>', '<|im_end|>', '<|endoftext|>', '<think>', '</think>')
MAX_EXPLODED_TURNS = 8
MAX_ROWS_PER_FAMILY = 64


def read_jsonl(path):
    rows = []
    for line_number, line in enumerate(Path(path).read_text(encoding='utf-8').splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f'{path}:{line_number}: invalid JSON') from error
        if not isinstance(row, dict):
            raise ValueError(f'{path}:{line_number}: expected an object')
        rows.append(row)
    if not rows:
        raise ValueError(f'{path}: empty dataset')
    return rows


def validate_messages(row):
    messages = row.get('messages')
    if not isinstance(messages, list) or len(messages) < 2:
        raise ValueError('Expected at least user and assistant messages')
    roles = [m.get('role') for m in messages if isinstance(m, dict)]
    expected = ['system'] if roles and roles[0] == 'system' else []
    remaining = len(messages) - len(expected)
    expected += ['user', 'assistant'] * (remaining // 2)
    if roles != expected or remaining % 2:
        raise ValueError('Messages must alternate user/assistant after an optional system')
    for message in messages:
        content = message.get('content')
        if not isinstance(content, str) or not content.strip():
            raise ValueError('Empty or non-string message content')
        if any(marker in content for marker in CHAT_MARKERS):
            raise ValueError('Embedded ChatML marker would corrupt role boundaries')
        if message['role'] == 'assistant':
            # Neither Qwen3's native thinking tokens (<think>) nor legacy XML
            # thought tokens (<thought>) may appear in supervised assistant targets.
            # They shift byte offsets, corrupt loss-mask positions, and violate
            # Qwen3's zero-thought policy.
            for tag in ('<think>', '</think>', '<thought>', '</thought>'):
                if tag in content:
                    raise ValueError(
                        f'Gold target contains {tag} tag. '
                        'Strip thinking and thought blocks before adding to training data.'
                    )
            if len(re.findall(r'<(?:tool_call\s+name=|finish>)', content)) != 1:
                raise ValueError('Target must contain exactly one agent action')
            turn = parse_agent_output(content)
            if turn.action is None:
                raise ValueError('Assistant target has no valid agent action')
            if isinstance(turn.action, WriteSiteAction):
                if not turn.action.files or any(not code.strip() for _, code in turn.action.files):
                    raise ValueError('Empty file target')
                paths = [path for path, _ in turn.action.files]
                if len(paths) != len(set(paths)):
                    raise ValueError('Duplicate file paths in target')
                if any(path.startswith(('/', '\\')) or ':' in path or '..' in path.replace('\\','/').split('/') for path in paths):
                    raise ValueError('Unsafe file path in target')
            if isinstance(turn.action, WriteComponentAction) and not turn.action.tsx.strip():
                raise ValueError('Empty component target')
            # The parser is intentionally forgiving at inference. Gold targets cannot be.
            for tag in ('thought', 'tool_call', 'file', 'tsx', 'css', 'finish'):
                opened = len(re.findall(r'<' + tag + r'(?:\s[^>]*|)>', content))
                if opened != content.count(f'</{tag}>'):
                    raise ValueError(f'Unbalanced {tag} tags in assistant target')
    return messages


def encode_row(row, tokenizer, max_length, chat_tokenizer=None):
    """Mask by message boundaries, not marker searches through untrusted content.

    Keep one native end-of-turn token; format_chatml already appends it. Token
    offsets handle BPE boundaries without independently tokenizing substrings.
    """
    messages = validate_messages(row)
    template = chat_tokenizer if chat_tokenizer is not None else tokenizer
    text = format_chatml(messages, False, tokenizer=template)
    if chat_tokenizer is not None:
        prefix = format_chatml(messages[:-1], True, tokenizer=chat_tokenizer)
        if not text.startswith(prefix):
            raise ValueError('Training target does not continue the inference non-thinking prompt')
    encoded = tokenizer.encode(text, add_special_tokens=False)
    if len(encoded.ids) > max_length:
        raise ValueError(f'Context overflow: {len(encoded.ids)} > {max_length}; no truncation allowed')
    spans, position = [], 0
    for index, message in enumerate(messages):
        header = f'<|im_start|>{message["role"]}\n'
        start = text.index(header, position) + len(header)
        end = text.index('<|im_end|>', start) + len('<|im_end|>')
        if message['role'] == 'assistant' and (chat_tokenizer is None or index == len(messages) - 1):
            # Native Qwen3 strips reasoning prefixes from historical assistants.
            # Only the final answer is a target; older turns are context. The
            # empty non-thinking prefix is supplied at inference, so mask it.
            spans.append((len(prefix) if chat_tokenizer is not None else start, end))
        position = end
    labels = [token if any(start <= left < right <= end for start, end in spans) else -100
              for token, (left, right) in zip(encoded.ids, encoded.offsets)]
    if not any(label != -100 for label in labels):
        raise ValueError('No supervised assistant tokens')
    return {'input_ids': encoded.ids, 'attention_mask': [1] * len(encoded.ids), 'labels': labels}


def prepare_rows(rows, tokenizer, max_length, chat_tokenizer=None):
    encoded = []
    seen = set()
    for index, row in enumerate(rows, 1):
        fingerprint = json.dumps(row.get('messages'), sort_keys=True)
        if fingerprint in seen:
            raise ValueError(f'Row {index}: duplicate conversation')
        seen.add(fingerprint)
        try:
            encoded.append(encode_row(row, tokenizer, max_length, chat_tokenizer=chat_tokenizer))
        except ValueError as error:
            raise ValueError(f'Row {index} ({row.get("task_id")}): {error}') from error
    return encoded


def check_holdout(train, validation):
    """Require family metadata, plus independent identity/content checks."""
    for split in (train, validation):
        if any(not row.get('family_id') for row in split):
            raise ValueError('Explicit validation requires nonempty family_id on every row')
    for key in ('family_id', 'source_task_id', 'task_id'):
        left = {str(r[key]) for r in train if r.get(key) is not None}
        right = {str(r[key]) for r in validation if r.get(key) is not None}
        if left & right:
            raise ValueError(f'Train/validation overlap in {key}')
    def content_keys(rows):
        return {re.sub(r'\s+', ' ', m['content'].strip()).casefold()
                for row in rows for m in row['messages'] if m['role'] == 'user'}
    if content_keys(train) & content_keys(validation):
        raise ValueError('Train/validation prompt overlap')
    from training.leakage_guard import compute_token_jaccard, compute_semantic_similarity
    train_prompts = [
        m['content'].strip()
        for row in train
        for m in row.get('messages', [])
        if m.get('role') == 'user' and not m.get('content', '').startswith('<observation')
    ]
    val_prompts = [
        m['content'].strip()
        for row in validation
        for m in row.get('messages', [])
        if m.get('role') == 'user' and not m.get('content', '').startswith('<observation')
    ]
    def distinctive_content(text):
        # Generated briefs share long XML instructions. Compare the requested
        # business and content, not the identical serialization boilerplate.
        fields = re.findall(
            r'<(?:business_name|tagline|headline|description|feature|name|title)>(.*?)</(?:business_name|tagline|headline|description|feature|name|title)>',
            text, flags=re.I | re.S,
        )
        return ' '.join(fields).strip() or text

    for tp in train_prompts:
        for vp in val_prompts:
            tp_content = distinctive_content(tp)
            vp_content = distinctive_content(vp)
            if compute_token_jaccard(tp_content, vp_content) >= 0.70:
                raise ValueError('Train/validation prompt overlap: token similarity exceeds threshold')
            if compute_semantic_similarity(tp_content, vp_content) >= 0.85:
                raise ValueError('Train/validation prompt overlap: semantic similarity exceeds threshold')


def output_paths(root, output, checkpoints):
    if not output or not checkpoints:
        raise ValueError('Supply separate --output and --checkpoint-dir paths for a candidate')
    output, checkpoints = Path(output).resolve(), Path(checkpoints).resolve()
    served = (root / 'my-react-agent-lora').resolve()
    for path in (output, checkpoints):
        if path == served or path in served.parents or served in path.parents:
            raise ValueError('Cannot write into or around the served adapter')
        if path.exists() and any(path.iterdir()):
            raise ValueError(f'Output directory is not empty: {path}')
    if output == checkpoints or output in checkpoints.parents or checkpoints in output.parents:
        raise ValueError('Export and checkpoint directories must be separate')
    return output, checkpoints


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


# ── P1-03: Thought-block stripping ────────────────────────────────────────────

# Matches both legacy XML <thought>...</thought> and Qwen3's <think>...</think>.
# These are GREEDY-blocked by DOTALL so nested content is fully captured.
_THOUGHT_BLOCK_RE = re.compile(
    r'<(?:thought|think)>.*?</(?:thought|think)>',
    re.DOTALL | re.IGNORECASE,
)


def normalize_assistant_target(text: str) -> str:
    """Remove private reasoning from one supervised assistant target."""
    cleaned = _THOUGHT_BLOCK_RE.sub('', text or '').strip()
    if re.search(r'<(?:think|thought)>', cleaned, re.IGNORECASE):
        raise ValueError('Reasoning tag survived normalization')
    return cleaned


def strip_thought_blocks(row: dict) -> dict:
    """Return a deep copy of *row* with all <thought> / <think> blocks removed
    from every assistant message.

    This is the authoritative normalization step (P1-03) that must be applied
    before validate_messages() is called.  Raw trajectories generated before the
    Qwen3 zero-thought protocol may carry <thought> blocks that would otherwise
    trigger validate_messages() to raise ValueError.

    The function is idempotent: calling it twice produces the same result.
    """
    out = copy.deepcopy(row)
    for message in out.get('messages', []):
        if message.get('role') == 'assistant':
            cleaned = normalize_assistant_target(message.get('content', ''))
            # Collapse runs of whitespace left by the removed blocks.
            message['content'] = re.sub(r'\n{3,}', '\n\n', cleaned).strip()
    return out


# ── P1-04: Multi-turn trajectory explosion ─────────────────────────────────────

def explode_to_prefix_target_pairs(row: dict) -> list:
    """Explode a multi-turn trajectory into one training example per assistant turn.

    Background (P1-04)
    ------------------
    Qwen3 inference uses a non-thinking prefix at the start of each new turn,
    which means the correct loss-masking strategy is:

        Supervised  = the LAST assistant message in the conversation.
        Context     = everything before it (all historical user + assistant turns).

    When a single row has N assistant turns and is encoded as-is, only the final
    assistant response is trained as an output.  The other N-1 action-generating
    turns are wasted context.

    This function converts one N-turn row into N separate rows, where each row
    ends at a different assistant turn so every action becomes a final supervised
    target exactly once:

        Row 1:  messages[:user_1+asst_1]                -> supervise asst_1
        Row 2:  messages[:user_1+asst_1+user_2+asst_2]  -> supervise asst_2
        ...                                             -> ...
        Row N:  full conversation                       -> supervise asst_N

    This preserves Qwen3 inference parity (final assistant is always the target)
    while multiplying useful training signal by N for multi-turn trajectories.

    Notes:
    - The system message, if present, is included in every generated row.
    - Each generated row inherits family_id, task_id, and source_task_id from
      the parent, with the turn index appended to task_id to keep it unique.
    - Rows with a single assistant turn are returned unchanged (no explosion).
    - validate_messages() must be called on the source row BEFORE exploding.
    """
    messages = row.get('messages', [])
    system_prefix = [messages[0]] if messages and messages[0].get('role') == 'system' else []
    non_system = messages[len(system_prefix):]

    # Identify the positions of each (user, assistant) pair boundary.
    # non_system is guaranteed to alternate user/assistant by validate_messages.
    pairs = []
    i = 0
    while i + 1 < len(non_system):
        if non_system[i].get('role') == 'user' and non_system[i + 1].get('role') == 'assistant':
            pairs.append(i + 2)  # slice end index (inclusive of this asst turn)
        i += 2

    if row.get('exploded_turn') is not None:
        # Already an exploded prefix/target trajectory; do not re-explode prefixes.
        return [row]

    if len(pairs) <= 1:
        # Single-turn or empty: no explosion needed.
        return [row]
    if len(pairs) > MAX_EXPLODED_TURNS:
        raise ValueError(f'Trajectory has {len(pairs)} assistant turns; maximum supported explosion is {MAX_EXPLODED_TURNS}')

    exploded = []
    base_task_id = str(row.get('task_id', ''))
    for turn_idx, end in enumerate(pairs, 1):
        child_messages = system_prefix + non_system[:end]
        child = {
            **{k: v for k, v in row.items() if k != 'messages'},
            'messages': child_messages,
            'task_id': f"{base_task_id}_turn{turn_idx}",
            'source_task_id': row.get('source_task_id') or base_task_id,
            'exploded_turn': turn_idx,
            'total_turns': len(pairs),
        }
        exploded.append(child)
    return exploded


def build_canonical_train_manifest(raw_rows: list) -> list:
    """Apply the full normalization pipeline to raw trajectories:

    1. strip_thought_blocks     — remove private reasoning (P1-03)
    2. validate_messages        — enforce Qwen3 zero-thought protocol
    3. explode_to_prefix_target_pairs — maximise supervised signal (P1-04)

    Raises ValueError on the first row that fails validate_messages after
    stripping.  Returns the list of training-ready rows ready for encode_row.

    Never call prepare_rows() directly on data/training_data.jsonl; always call
    this function first to obtain a sealed, normalised manifest.
    """
    train_rows = []
    family_counts = {}
    for idx, raw in enumerate(raw_rows, 1):
        stripped = strip_thought_blocks(raw)
        try:
            validate_messages(stripped)
        except ValueError as exc:
            raise ValueError(
                f'Row {idx} ({raw.get("task_id")}): still invalid after stripping: {exc}'
            ) from exc
        children = explode_to_prefix_target_pairs(stripped)
        family = str(stripped.get('family_id') or stripped.get('source_task_id') or stripped.get('task_id') or f'row_{idx}')
        family_counts[family] = family_counts.get(family, 0) + len(children)
        if family_counts[family] > MAX_ROWS_PER_FAMILY:
            raise ValueError(f'Family {family!r} produces too many exploded rows; trajectory weighting is capped at {MAX_ROWS_PER_FAMILY}')
        train_rows.extend(children)
    return train_rows


def normalize_jsonl(source, destination):
    """CLI entry point used by Windows launchers (avoids fragile ``python -c``)."""
    rows = build_canonical_train_manifest(read_jsonl(source))
    Path(destination).write_text(
        ''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in rows), encoding='utf-8')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Normalize and explode SFT trajectories')
    parser.add_argument('source')
    parser.add_argument('destination')
    args = parser.parse_args()
    normalize_jsonl(args.source, args.destination)
