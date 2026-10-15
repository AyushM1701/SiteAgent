#!/usr/bin/env python3
"""
train.py - Fine-Tune Qwen3-4B into an Agentic SLM with QLoRA
Tuned for: RTX 4050 Laptop GPU (6GB VRAM), 24GB DDR5 RAM.

Validates bounded XML-agent records and an explicit family-disjoint holdout.
Exports only isolated candidate adapters; benchmark tasks never select checkpoints.
"""

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

base_model_dir = BASE_DIR / "base-model"
if base_model_dir.exists():
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
# The auto loss-chunk heuristic can allocate several GiB on WDDM. Bound its
# logits workspace before Unsloth imports the fused-loss module.
os.environ["UNSLOTH_CE_LOSS_TARGET_GB"] = "0.25"

import re
from training.preflight import read_jsonl, prepare_rows, check_holdout, output_paths, sha256, build_canonical_train_manifest
from training.cuda_budget import assert_cuda_budget


def _extract_symbols(text: str) -> set:
    """Extracts component and hook identifiers enclosed in backticks or PascalCase/useX patterns."""
    backticks = set(re.findall(r'`([A-Za-z0-9_]+)`', text))
    pascal = set(re.findall(r'\b([A-Z][A-Za-z0-9]+)\b', text))
    hooks = set(re.findall(r'\b(use[A-Z][A-Za-z0-9]+)\b', text))
    common_words = {
        "Write", "Build", "Create", "Style", "Implement", "React", "TypeScript",
        "CSS", "HTML", "DOM", "API", "JSON", "The", "When", "If", "Each", "All",
        "For", "Use", "Ensure", "Every", "Add", "Make", "Provide", "Support", "Given"
    }
    return (backticks | hooks | (pascal - common_words))


def _extract_code_fingerprint(messages: list) -> dict:
    """Extract structural fingerprints from the source code in assistant messages.

    P1-07: Benchmark leakage can occur even when prompts differ if the generated
    TSX/CSS structure is nearly identical.  This function extracts three structural
    signals from every assistant target in a trajectory:

    jsx_tags     - set of JSX element names (e.g. {"section", "div", "Button"})
    css_decls    - set of normalized CSS declaration fingerprints ("property:value")
    code_tokens  - frozenset of normalized code tokens for MinHash-style Jaccard

    Returns a dict with those three keys, or empty sets if no code is present.
    """
    all_code = []
    for m in messages:
        if m.get("role") != "assistant":
            continue
        content = m.get("content", "")
        # Extract content of <file>...</file> blocks (TSX/CSS targets)
        file_blocks = re.findall(r'<file\b[^>]*>(.*?)</file>', content, re.DOTALL)
        all_code.extend(file_blocks)
        # Also capture raw <tsx>...</tsx> / <css>...</css> blocks
        all_code.extend(re.findall(r'<tsx>(.*?)</tsx>', content, re.DOTALL))
        all_code.extend(re.findall(r'<css>(.*?)</css>', content, re.DOTALL))

    combined = "\n".join(all_code)
    if not combined.strip():
        return {"jsx_tags": frozenset(), "css_decls": frozenset(), "code_tokens": frozenset()}

    # JSX element names: <ComponentName or <htmltag (ignore closing tags / comments)
    jsx_tags = frozenset(
        t.lower() for t in re.findall(r'<([A-Za-z][A-Za-z0-9]*)', combined)
        if t.lower() not in {"file", "tool_call", "finish", "tsx", "css", "thought", "think"}
    )

    # CSS declarations: property:value pairs, normalized
    css_decl_raw = re.findall(r'([a-z-]{2,40})\s*:\s*([^;{}\n]{1,80})', combined)
    css_decls = frozenset(
        f"{prop}:{re.sub(chr(32) + '+', ' ', val.strip().lower())}"
        for prop, val in css_decl_raw
        if prop not in {"http", "https", "src", "href", "alt"}
    )

    # Code token MinHash fingerprint: identifier/keyword tokens, lowercased, de-duped
    code_tokens = frozenset(
        t.lower() for t in re.findall(r'\b[A-Za-z][A-Za-z0-9_]{2,}\b', combined)
        if len(t) >= 3
    )

    return {"jsx_tags": jsx_tags, "css_decls": css_decls, "code_tokens": code_tokens}



def _compute_token_jaccard(text1: str, text2: str) -> float:
    """Computes Jaccard similarity over alphanumeric word tokens."""
    w1 = set(re.sub(r'[^a-z0-9]+', ' ', text1.lower()).split())
    w2 = set(re.sub(r'[^a-z0-9]+', ' ', text2.lower()).split())
    if not w1 or not w2:
        return 0.0
    return len(w1 & w2) / len(w1 | w2)


def check_benchmark_disjointness(
    training_file: str,
    eval_file: str = "react_ts_css_eval_set_combined.jsonl",
    similarity_threshold: float = 0.50,
):
    """
    Enforces absolute disjointness between the training dataset and the benchmark evaluation set.
    Performs multi-level integrity checks across 9 dimensions:
      1. Exact prompt match & prefix collision
      2. Normalized full-text prompt match
      3. Structural symbol overlap (PascalCase, hooks, backticks)
      4. Token Jaccard similarity >= similarity_threshold
      5. Family-level holdout (family_id, source_task_id, task_id)
      6. Semantic similarity checks (character/word n-gram & TF-IDF overlap)
      7. JSX element tag fingerprint overlap (P1-07: code-level provenance)
      8. CSS declaration fingerprint overlap (P1-07: code-level provenance)
      9. Code token MinHash Jaccard similarity (P1-07: code-level provenance)
    Also verifies cryptographic manifest if evaluating against sealed_final_benchmark.jsonl.
    Raises RuntimeError if any prompt or structural overlap is detected.
    """
    from training.leakage_guard import (
        compute_semantic_similarity,
        verify_sealed_benchmark_manifest,
    )

    if not os.path.exists(eval_file):
        if (BASE_DIR / "data" / "eval" / eval_file).exists():
            eval_file = str(BASE_DIR / "data" / "eval" / eval_file)
        elif (BASE_DIR / "data" / eval_file).exists():
            eval_file = str(BASE_DIR / "data" / eval_file)
        elif (BASE_DIR / eval_file).exists():
            eval_file = str(BASE_DIR / eval_file)
        else:
            raise FileNotFoundError(f"Required benchmark missing: {eval_file}")

    # Verify cryptographic seal if evaluating against sealed final benchmark
    if Path(eval_file).name == "sealed_final_benchmark.jsonl":
        manifest_file = Path(eval_file).parent / "sealed_final_benchmark_manifest.json"
        if manifest_file.exists():
            verify_sealed_benchmark_manifest(eval_file, str(manifest_file))

    import math
    from collections import Counter

    eval_prompts_prefix = set()
    eval_prompts_clean = set()
    eval_prompts_exact = set()
    eval_family_ids = set()
    eval_task_ids = set()
    eval_items = []

    with open(eval_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
                p = item.get("prompt", "")
                if not isinstance(p, str) or not p.strip():
                    raise ValueError('Benchmark record is missing its prompt')
                p = p.strip()
                p_lower = p.lower()
                clean_p = re.sub(r'[^a-z0-9]+', ' ', p_lower).strip()
                eval_prompts_exact.add(p)
                eval_prompts_prefix.add(p_lower[:60])
                eval_prompts_clean.add(clean_p)
                if item.get("family_id"):
                    eval_family_ids.add(str(item["family_id"]))
                if item.get("task_id"):
                    eval_task_ids.add(str(item["task_id"]))

                w_words = set(clean_p.split())
                w_counter = Counter(re.findall(r"\b[a-zA-Z0-9_]+\b", p_lower))
                w_norm = math.sqrt(sum(v * v for v in w_counter.values()))
                ngrams = {clean_p[idx : idx + 3] for idx in range(len(clean_p) - 2)} if len(clean_p) >= 3 else set()

                eval_items.append({
                    "task_id": item.get("task_id", "unknown"),
                    "family_id": item.get("family_id"),
                    "prompt": p,
                    "clean": clean_p,
                    "symbols": _extract_symbols(p),
                    "words": w_words,
                    "counter": w_counter,
                    "norm": w_norm,
                    "ngrams": ngrams,
                    # P1-07: Code-level structural fingerprints (from benchmark reference output if present)
                    "code_fp": _extract_code_fingerprint(item.get("messages", [])),
                })
            except (ValueError, TypeError, AttributeError) as error:
                raise ValueError(f"Invalid record in {eval_file}: {line[:80]}") from error

    if not eval_items:
        raise ValueError(f"Benchmark has no usable prompts: {eval_file}")

    leak_count = 0
    max_similarity = 0.0

    with open(training_file, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                # Check 5: Family-level holdout
                fam = rec.get("family_id")
                src_task = rec.get("source_task_id")
                rec_task = rec.get("task_id")
                if fam and str(fam) in eval_family_ids:
                    print(f"[Disjointness Failure - Family Holdout] Line {i}: Family ID '{fam}' collides with benchmark family.", flush=True)
                    leak_count += 1
                if src_task and str(src_task) in eval_task_ids:
                    print(f"[Disjointness Failure - Task Holdout] Line {i}: Source task ID '{src_task}' collides with benchmark task.", flush=True)
                    leak_count += 1
                if rec_task and str(rec_task) in eval_task_ids:
                    print(f"[Disjointness Failure - Task Holdout] Line {i}: Task ID '{rec_task}' collides with benchmark task.", flush=True)
                    leak_count += 1

                for m in rec.get("messages", []):
                    if m.get("role") == "user" and not m.get("content", "").startswith("<observation"):
                        u = m.get("content", "").strip()
                        u_lower = u.lower()
                        clean_u = re.sub(r'[^a-z0-9]+', ' ', u_lower).strip()

                        # 1. Exact prompt match & prefix collision
                        if u in eval_prompts_exact or u_lower[:60] in eval_prompts_prefix:
                            print(f"[Disjointness Failure - Prefix/Exact] Line {i}: Prompt matches held-out eval set prefix: {u[:50]}...", flush=True)
                            leak_count += 1
                            continue

                        # 2. Normalized full-text collision
                        if clean_u in eval_prompts_clean:
                            print(f"[Disjointness Failure - Exact Match] Line {i}: Normalized prompt matches held-out eval item: {u[:50]}...", flush=True)
                            leak_count += 1
                            continue

                        # Precompute features for prompt u
                        u_symbols = _extract_symbols(u)
                        u_words = set(clean_u.split())
                        u_counter = Counter(re.findall(r"\b[a-zA-Z0-9_]+\b", u_lower))
                        u_norm = math.sqrt(sum(v * v for v in u_counter.values()))
                        u_ngrams = {clean_u[idx : idx + 3] for idx in range(len(clean_u) - 2)} if len(clean_u) >= 3 else set()

                        for eit in eval_items:
                            common_symbols = u_symbols & eit["symbols"]
                            if not u_words or not eit["words"]:
                                jaccard = 0.0
                            else:
                                jaccard = len(u_words & eit["words"]) / len(u_words | eit["words"])

                            if jaccard > max_similarity:
                                max_similarity = jaccard

                            # Symbol overlap with token similarity
                            if common_symbols and jaccard >= 0.35:
                                print(
                                    f"[Disjointness Failure - Structural Similarity] Line {i}: "
                                    f"Prompt shares symbol {common_symbols} and has Jaccard similarity "
                                    f"{jaccard:.2f} >= 0.35 with eval item: {u[:50]}...",
                                    flush=True,
                                )
                                leak_count += 1
                                break

                            # Token similarity threshold
                            if jaccard >= similarity_threshold:
                                print(
                                    f"[Disjointness Failure - Token Similarity] Line {i}: "
                                    f"Prompt has Jaccard similarity {jaccard:.2f} >= {similarity_threshold} "
                                    f"with eval item: {u[:50]}...",
                                    flush=True,
                                )
                                leak_count += 1
                                break

                            # Semantic similarity checks
                            dot = sum(u_counter[k] * eit["counter"].get(k, 0) for k in u_counter)
                            cos_sim = dot / (u_norm * eit["norm"]) if (u_norm and eit["norm"]) else 0.0
                            dice_sim = (2.0 * len(u_ngrams & eit["ngrams"]) / (len(u_ngrams) + len(eit["ngrams"]))) if (u_ngrams and eit["ngrams"]) else 0.0
                            sem_sim = 0.50 * cos_sim + 0.50 * dice_sim

                            if sem_sim >= 0.65:
                                print(
                                    f"[Disjointness Failure - Semantic Similarity] Line {i}: "
                                    f"Prompt has semantic similarity {sem_sim:.2f} >= 0.65 with eval item: {u[:50]}...",
                                    flush=True,
                                )
                                leak_count += 1
                                break

                # P1-07: Code-level structural fingerprint check.
                # Runs once per training row (not per user turn) because the targets
                # are on the assistant side, not the prompt side.
                train_code_fp = _extract_code_fingerprint(rec.get("messages", []))
                if train_code_fp["code_tokens"]:
                    for eit in eval_items:
                        eval_fp = eit["code_fp"]
                        if not eval_fp["code_tokens"]:
                            continue

                        # 7. JSX element tag overlap (>= 80% overlap of the smaller set)
                        if train_code_fp["jsx_tags"] and eval_fp["jsx_tags"]:
                            overlap = train_code_fp["jsx_tags"] & eval_fp["jsx_tags"]
                            smaller = min(len(train_code_fp["jsx_tags"]), len(eval_fp["jsx_tags"]))
                            if smaller > 3 and len(overlap) / smaller >= 0.80:
                                print(
                                    f"[Disjointness Failure - JSX Tag Fingerprint] Line {i}: "
                                    f"Training code shares {len(overlap)}/{smaller} JSX tags with "
                                    f"benchmark item '{eit['task_id']}'. Code-level leak suspected.",
                                    flush=True,
                                )
                                leak_count += 1
                                break

                        # 8. CSS declaration fingerprint overlap
                        if train_code_fp["css_decls"] and eval_fp["css_decls"]:
                            decl_overlap = train_code_fp["css_decls"] & eval_fp["css_decls"]
                            smaller_d = min(len(train_code_fp["css_decls"]), len(eval_fp["css_decls"]))
                            if smaller_d > 5 and len(decl_overlap) / smaller_d >= 0.75:
                                print(
                                    f"[Disjointness Failure - CSS Declaration Fingerprint] Line {i}: "
                                    f"Training code shares {len(decl_overlap)}/{smaller_d} CSS declarations with "
                                    f"benchmark item '{eit['task_id']}'. Code-level leak suspected.",
                                    flush=True,
                                )
                                leak_count += 1
                                break

                        # 9. Code token MinHash Jaccard similarity
                        common_code = train_code_fp["code_tokens"] & eval_fp["code_tokens"]
                        union_code = train_code_fp["code_tokens"] | eval_fp["code_tokens"]
                        code_jaccard = len(common_code) / len(union_code) if union_code else 0.0
                        if code_jaccard >= 0.70:
                            print(
                                f"[Disjointness Failure - Code Token Similarity] Line {i}: "
                                f"Training code token Jaccard {code_jaccard:.2f} >= 0.70 with "
                                f"benchmark item '{eit['task_id']}'. Code-level leak suspected.",
                                flush=True,
                            )
                            leak_count += 1
                            break
            except (ValueError, TypeError, AttributeError) as error:
                raise ValueError(f"Invalid training record at {training_file}:{i}") from error

    if leak_count > 0:
        raise RuntimeError(
            f"Pre-flight data integrity check FAILED: {leak_count} training examples collide with held-out eval set!"
        )
    print(
        f"[Disjointness Verified] 0 leaks (exact or structural) detected between {training_file} and {eval_file}. "
        f"Peak structural similarity: {max_similarity:.3f} (threshold: {similarity_threshold}).",
        flush=True,
    )


def train(
    dataset_path=None, epochs=1, rank=16, lora_alpha=None, learning_rate=2e-5,
    lora_dropout=0.0, validation_split=0.0, min_trajectories=10,
    max_seq_length=None, neftune_noise_alpha=0.0, validation_dataset_path=None,
    output_path=None, checkpoint_dir=None, max_steps=-1, initial_adapter=None,
    preflight_only=False, benchmark_report="runs/qwen3_context_benchmark.json",
    override_methodology_gate=False,
    native_gate_report='runs/native_three_domain_gate_v1/report.json',
):
    import math
    from tokenizers import Tokenizer
    from training.context_decision import (
        resolve_context_length,
        format_preflight_histogram,
        calculate_percentiles,
    )

    max_seq_length, context_decision_info = resolve_context_length(
        benchmark_report_path=benchmark_report,
        explicit_length=max_seq_length,
        default_length=8192,
    )

    if validation_split:
        raise ValueError('Random row splitting is unsafe. Supply --validation-data with family IDs.')
    if epochs <= 0 or max_steps == 0 or max_steps < -1 or min_trajectories < 1:
        raise ValueError('Invalid epoch, step or minimum-row count')
    if not 0 < learning_rate < 1 or not math.isfinite(learning_rate):
        raise ValueError('Learning rate must be finite and between zero and one')
    if rank <= 0 or (lora_alpha is not None and lora_alpha <= 0) or not 0 <= lora_dropout < 1:
        raise ValueError('Invalid LoRA configuration')
    from training.methodology import guard_hyperparameter_sweep
    guard_hyperparameter_sweep(
        rank=rank,
        learning_rate=learning_rate,
        lora_dropout=lora_dropout,
        override=override_methodology_gate,
    )
    # Authoritative Base Model Architecture Verification
    from agent.base_model_fingerprint import verify_base_model_architecture
    base_fingerprint = verify_base_model_architecture(base_model_dir, strict=True, require_4b=True)
    if not base_fingerprint["is_authentic_qwen3"]:
        raise ValueError("Training requires authentic Qwen3 base tensors; legacy override is not permitted")
    if neftune_noise_alpha != 0:
        raise ValueError('NEFTune is disabled for protocol-preserving training')
    if not 256 <= max_seq_length <= 8192:
        raise ValueError('This 6GB training profile supports context lengths from 256 to 8192')
    if not preflight_only:
        if not output_path:
            raise ValueError("--output is required for training")
        if not checkpoint_dir:
            raise ValueError("--checkpoint-dir is required for training")
        export_dir, run_dir = output_paths(BASE_DIR, output_path, checkpoint_dir)
    else:
        export_dir = Path(output_path).resolve() if output_path else None
        run_dir = Path(checkpoint_dir).resolve() if checkpoint_dir else None

    adapter = Path(initial_adapter).resolve() if initial_adapter else None
    if adapter:
        if export_dir and (adapter == export_dir or adapter in export_dir.parents):
            raise ValueError('Candidate output cannot overwrite its initialization adapter')
        from agent.base_model_fingerprint import verify_lora_adapter_compatibility
        verify_lora_adapter_compatibility(adapter, base_model_dir)

    native_evidence = None
    if not preflight_only:
        from training.native_generation_gate import require_native_completion
        native_evidence = require_native_completion(
            native_gate_report, expected_model_dir=adapter or base_model_dir)

    raw_dataset = dataset_path or 'data/quality_candidate/train.jsonl'
    p = Path(raw_dataset)
    if not p.is_absolute() and not p.exists() and (BASE_DIR / raw_dataset).exists():
        trajectory_file = (BASE_DIR / raw_dataset).resolve()
    else:
        trajectory_file = p.resolve()

    if validation_dataset_path:
        vp = Path(validation_dataset_path)
        if not vp.is_absolute() and not vp.exists() and (BASE_DIR / validation_dataset_path).exists():
            validation_file = (BASE_DIR / validation_dataset_path).resolve()
        else:
            validation_file = vp.resolve()
    else:
        validation_file = None

    raw_train = build_canonical_train_manifest(read_jsonl(trajectory_file))
    raw_validation = build_canonical_train_manifest(read_jsonl(validation_file)) if validation_file else []
    if 'reviewed_full_sites' in trajectory_file.parts:
        if not raw_validation:
            raise ValueError('Reviewed full-site training requires a nonempty held-out validation split')
        from data_pipeline.reviewed_site_examples import validate_reviewed_site_rows
        review_errors = validate_reviewed_site_rows(raw_train, raw_validation)
        if review_errors:
            raise ValueError('Reviewed full-site admission failed: ' + '; '.join(review_errors[:10]))
    if raw_validation:
        check_holdout(raw_train, raw_validation)
    for path in (trajectory_file, validation_file):
        if path:
            check_benchmark_disjointness(str(path))
            check_benchmark_disjointness(str(path), str(BASE_DIR / 'data/eval/premium_sites.jsonl'))
            sealed_bench = BASE_DIR / 'data/eval/sealed_final_benchmark.jsonl'
            if sealed_bench.exists():
                check_benchmark_disjointness(str(path), str(sealed_bench))
            visual_holdout = BASE_DIR / 'data/eval/visual_holdout_v1.jsonl'
            if visual_holdout.exists():
                check_benchmark_disjointness(str(path), str(visual_holdout))
    tokenizer_dir = adapter or BASE_DIR / 'base-model'
    tokenizer_file = tokenizer_dir / 'tokenizer.json'
    cpu_tokenizer = Tokenizer.from_file(str(tokenizer_file))
    cpu_tokenizer.no_truncation()
    cpu_tokenizer.no_padding()

    # Pass the chat serializer explicitly: the Rust encoder has no template and
    # previously shadowed the registry, silently selecting legacy ChatML.
    from transformers import AutoTokenizer
    preflight_tok = AutoTokenizer.from_pretrained(str(tokenizer_dir), local_files_only=True)
    if not preflight_tok.chat_template:
        raise ValueError('Native chat template required for training')
    if not callable(getattr(preflight_tok, 'apply_chat_template', None)):
        raise ValueError('Tokenizer must provide native apply_chat_template encoding')
    train_rows = prepare_rows(raw_train, cpu_tokenizer, max_seq_length, chat_tokenizer=preflight_tok)
    eval_rows = prepare_rows(raw_validation, cpu_tokenizer, max_seq_length, chat_tokenizer=preflight_tok) if raw_validation else []
    if len(train_rows) < min_trajectories:
        raise ValueError('Not enough valid training examples')
    actual_alpha = lora_alpha if lora_alpha is not None else rank
    if adapter:
        config = json.loads((adapter / 'adapter_config.json').read_text(encoding='utf-8'))
        if (config['r'], config['lora_alpha'], config['lora_dropout']) != (rank, actual_alpha, lora_dropout):
            raise ValueError('Requested LoRA configuration differs from initialization adapter')

    seq_lengths = [len(r['input_ids']) for r in train_rows + eval_rows]
    min_len = min(seq_lengths)
    max_len = max(seq_lengths)
    avg_len = sum(seq_lengths) / len(seq_lengths)
    stats = calculate_percentiles(seq_lengths)
    p50 = stats['p50']
    p75 = stats['p75']
    p90 = stats['p90']
    p95 = stats['p95']
    p99 = stats['p99']

    print("\n--- Sequence Length Statistics ---", flush=True)
    print(format_preflight_histogram(seq_lengths, [6144, 8192]), flush=True)
    print(f"\nContext Decision: {max_seq_length} tokens (selected from {context_decision_info.get('source')}; policy: {context_decision_info.get('policy_decision')})", flush=True)
    if context_decision_info.get('rationale'):
        print(f"Rationale       : {context_decision_info['rationale']}\n", flush=True)

    manifest = {
        'chat_format': 'qwen3_native_non_thinking',
        'tokenizer_encoding': 'native_apply_chat_template',
        'supervision': 'final_assistant_content_and_eos',
        'chat_template_sha256': hashlib.sha256(preflight_tok.chat_template.encode('utf-8')).hexdigest(),
        'dataset_path': str(trajectory_file), 'dataset_sha256': sha256(trajectory_file),
        'validation_dataset_sha256': sha256(validation_file) if validation_file else None,
        'tokenizer_sha256': sha256(tokenizer_file),
        'initial_adapter': str(adapter) if adapter else None,
        'initial_adapter_sha256': sha256(adapter / 'adapter_model.safetensors') if adapter else None,
        'train_rows': len(train_rows), 'validation_rows': len(eval_rows),
        'max_seq_length': max_seq_length,
        'context_decision': context_decision_info,
        'sequence_length_stats': {
            'count': len(seq_lengths),
            'min': min_len,
            'max': max_len,
            'mean': round(avg_len, 1),
            'p50': p50,
            'p75': p75,
            'p90': p90,
            'p95': p95,
            'p99': p99,
            'fits_6144_pct': round((sum(1 for l in seq_lengths if l <= 6144) / len(seq_lengths)) * 100, 1),
            'fits_8192_pct': round((sum(1 for l in seq_lengths if l <= 8192) / len(seq_lengths)) * 100, 1),
        },
        'maximum_observed_length': max_len,
        'minimum_supervised_tokens': min(sum(t != -100 for t in r['labels']) for r in train_rows),
        'rank': rank, 'lora_alpha': actual_alpha, 'lora_dropout': lora_dropout,
        'learning_rate': learning_rate, 'epochs': epochs, 'max_steps': max_steps,
        'loss_masking': 'Exact assistant content and single native end-of-turn token; all prompts masked',
        'attention_backend': 'PyTorch fused SDPA (flash/efficient/cuDNN); quadratic math fallback disabled',
        'fused_loss_workspace_target_gib': 0.25,
        # This is deliberately distinct from a completed training run.  Consumers
        # must never interpret a CPU-only preflight as a promotable candidate.
        'status': 'preflight_only' if preflight_only else 'training_ready',
    }
    print(json.dumps(manifest, indent=2), flush=True)
    if preflight_only:
        return manifest

    # Hyperparameter overrides do not waive native generation or reviewed data.
    manifest['native_completion_gate'] = native_evidence
    from data_pipeline.reviewed_site_examples import require_reviewed_training_examples
    manifest['reviewed_training_examples'] = require_reviewed_training_examples(raw_train, raw_validation)

    # Historical adapters name ./base-model; resolve that relative to this repo.
    os.chdir(BASE_DIR)
    # Unsloth must patch Transformers before importing Trainer/PEFT/TRL.
    from unsloth import FastLanguageModel
    import torch
    from datasets import Dataset
    from transformers import TrainerCallback
    from trl import SFTTrainer, SFTConfig
    from trl.trainer.sft_trainer import DataCollatorForLanguageModeling
    import importlib.metadata
    if not torch.cuda.is_available():
        raise RuntimeError('This QLoRA profile requires CUDA')
    # Do not silently fall back to quadratic attention on a 6GB laptop.
    torch.backends.cuda.enable_flash_sdp(True)
    torch.backends.cuda.enable_math_sdp(False)
    torch.backends.cuda.enable_mem_efficient_sdp(True)
    torch.backends.cuda.enable_cudnn_sdp(True)
    free_bytes, total_bytes = torch.cuda.mem_get_info()
    # P1-06: The physical VRAM ceiling for the RTX 4050 6 GB profile is 5.5 GiB.
    # This is not a benchmark recommendation — it is a physical invariant.
    # We enforce it here (pre-training gate) AND in HealthCallback (mid-training governor).
    VRAM_CEILING_BYTES = int(5.5 * 1024**3)
    if free_bytes < 5.0 * 1024**3 - 100 * 1024**2:
        raise RuntimeError('Less than 5.0 GiB GPU memory free. Stop inference before training. '
                           'Qwen3-4B at 4-bit requires more headroom than Qwen2.5-3B.')
    manifest['versions'] = {name: importlib.metadata.version(name) for name in ('torch', 'transformers', 'trl', 'unsloth', 'peft')}
    manifest['gpu'] = torch.cuda.get_device_name(0)
    run_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = run_dir / 'run_manifest.json'
    def save_status(status, **values):
        manifest.update(status=status, **values)
        temp = manifest_path.with_suffix('.tmp')
        temp.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
        temp.replace(manifest_path)
    save_status('loading')
    try:
        model, tokenizer = FastLanguageModel.from_pretrained(
            model_name=str(adapter or BASE_DIR / 'base-model'), max_seq_length=max_seq_length,
            load_in_4bit=True, local_files_only=True,
        )
        assert_cuda_budget('after model load', torch)
        if tokenizer.eos_token != '<|im_end|>':
            raise ValueError(
                f'Unexpected tokenizer EOS token: {tokenizer.eos_token!r}. '
                'Expected <|im_end|> for Qwen3-4B (and Qwen2.5-Coder). '
                'Verify the correct base model is in base-model/.'
            )
        # The live tokenizer must agree with the CPU preflight tokenizer exactly.
        from agent.agent_protocol import set_default_tokenizer, format_chatml
        set_default_tokenizer(tokenizer)
        for row, encoded in zip(raw_train + raw_validation, train_rows + eval_rows):
            if tokenizer(format_chatml(row['messages'], False, tokenizer=tokenizer), add_special_tokens=False)['input_ids'] != encoded['input_ids']:
                raise ValueError('Loaded tokenizer differs from preflight; refusing mismatched labels')
        if not adapter:
            model = FastLanguageModel.get_peft_model(
                model, r=rank, lora_alpha=actual_alpha, lora_dropout=lora_dropout,
                target_modules=['q_proj','k_proj','v_proj','o_proj','gate_proj','up_proj','down_proj'],
                bias='none', use_gradient_checkpointing='unsloth', random_state=42,
            )
        assert_cuda_budget('after adapter attach', torch)
        FastLanguageModel.for_training(model, use_gradient_checkpointing='unsloth')
        trainable = [(name,p) for name,p in model.named_parameters() if p.requires_grad]
        if not trainable or any('lora_' not in name for name,_ in trainable):
            raise ValueError('Expected only LoRA parameters to be trainable')
        if any(not torch.isfinite(p).all().item() for _,p in trainable):
            raise ValueError('Adapter contains non-finite weights')
        manifest['trainable_parameters'] = sum(p.numel() for _,p in trainable)
        model.config.use_cache = False
        use_bf16 = torch.cuda.is_bf16_supported()
        has_eval = bool(eval_rows)
        config = SFTConfig(
            output_dir=str(run_dir), per_device_train_batch_size=1, per_device_eval_batch_size=1,
            gradient_accumulation_steps=4, num_train_epochs=epochs, max_steps=max_steps,
            learning_rate=learning_rate, warmup_ratio=0.05, lr_scheduler_type='cosine',
            optim='adamw_8bit', weight_decay=0.01, fp16=not use_bf16, bf16=use_bf16,
            fp16_full_eval=not use_bf16, bf16_full_eval=use_bf16,
            logging_steps=1, logging_nan_inf_filter=False, max_grad_norm=1.0,
            eval_strategy='steps' if has_eval else 'no', eval_steps=25,
            save_strategy='steps', save_steps=25, save_total_limit=2,
            eval_on_start=has_eval, prediction_loss_only=True, eval_accumulation_steps=1,
            load_best_model_at_end=has_eval, metric_for_best_model='eval_loss' if has_eval else None,
            greater_is_better=False, report_to='none', seed=42, data_seed=42,
            max_length=max_seq_length, packing=False, dataset_kwargs={'skip_prepare_dataset':True},
            dataloader_num_workers=0, dataloader_pin_memory=False,
        )
        class HealthCallback(TrainerCallback):
            def on_train_batch_end(self, args, state, control, **kwargs):
                assert_cuda_budget('after forward/backward', torch)

            def on_optimizer_step(self, args, state, control, **kwargs):
                torch.cuda.empty_cache()
                assert_cuda_budget('after optimizer step', torch)

            def on_log(self, args, state, control, logs=None, **kwargs):
                for key in ('loss','eval_loss','grad_norm'):
                    value = (logs or {}).get(key)
                    if value is not None and not math.isfinite(float(value)):
                        raise FloatingPointError(f'Non-finite {key}: {value}')
                save_status('training', global_step=state.global_step, latest_metrics=logs,
                            peak_gpu_allocated_bytes=torch.cuda.max_memory_allocated())
                # P1-06: Mid-training CUDA memory governor.
                # This is a separate check from the pre-training free-memory gate.
                # Activation + gradient memory for long sequences can exceed the ceiling
                # even when free memory was sufficient at startup.
                peak = torch.cuda.max_memory_allocated()
                assert_cuda_budget('training step', torch)
                if peak > VRAM_CEILING_BYTES:
                    raise RuntimeError(
                        f'Peak CUDA allocation {peak / 1024**3:.2f} GiB exceeds the '
                        f'5.5 GiB RTX 4050 ceiling. Reduce sequence length, LoRA rank, '
                        f'or gradient accumulation steps and retry.'
                    )
        class UnpaddedCollator(DataCollatorForLanguageModeling):
            def torch_call(self, examples):
                batch = super().torch_call(examples)
                # An all-ones padding mask is redundant and can block fused SDPA.
                # Keep masks for genuinely padded batches.
                if 'attention_mask' in batch and bool(batch['attention_mask'].all()):
                    del batch['attention_mask']
                return batch
        class BoundedEvaluationTrainer(SFTTrainer):
            def prediction_step(self, model, inputs, prediction_loss_only, ignore_keys=None):
                from training.memory_loss import chunked_causal_loss
                inputs = self._prepare_inputs(inputs)
                base = self.accelerator.unwrap_model(model).get_base_model()
                with torch.no_grad(), self.compute_loss_context_manager():
                    hidden = base.model(input_ids=inputs['input_ids'],
                                        attention_mask=inputs.get('attention_mask'),
                                        use_cache=False, return_dict=True).last_hidden_state
                    loss = chunked_causal_loss(hidden, inputs['labels'], base.get_output_embeddings())
                assert_cuda_budget('benchmark/evaluation forward', torch)
                return loss.detach(), None, None
        trainer = BoundedEvaluationTrainer(
            model=model, processing_class=tokenizer, args=config,
            train_dataset=Dataset.from_list(train_rows),
            eval_dataset=Dataset.from_list(eval_rows) if has_eval else None,
            data_collator=UnpaddedCollator(pad_token_id=tokenizer.pad_token_id, completion_only_loss=False),
            callbacks=[HealthCallback()],
        )
        # Verify the actual collator keeps response masks, including EOS, intact.
        batch = trainer.data_collator([train_rows[0], train_rows[-1]])
        for i, row in enumerate((train_rows[0], train_rows[-1])):
            if batch['labels'][i,:len(row['labels'])].tolist() != row['labels']:
                raise ValueError('Data collator altered response-only loss masks')
        del batch
        torch.cuda.reset_peak_memory_stats()
        save_status('training')
        result = trainer.train()
        final_metrics = trainer.evaluate() if has_eval else {}
        if any(not torch.isfinite(p).all().item() for _,p in trainable):
            raise FloatingPointError('Non-finite final adapter weights')
        export_dir.mkdir(parents=True, exist_ok=True)
        model.save_pretrained(str(export_dir))
        tokenizer.save_pretrained(str(export_dir))
        trainer.save_state()
        # P1-05: Generate the immutable promotion manifest immediately after saving.
        # This records the exact base-model identity (config/tokenizer hashes, dims,
        # LoRA rank) so verify_adapter_promotion_manifest() can fail closed at
        # promotion time if the base model files have changed.
        from agent.base_model_fingerprint import generate_adapter_promotion_manifest
        lora_target_modules = ['q_proj', 'k_proj', 'v_proj', 'o_proj', 'gate_proj', 'up_proj', 'down_proj']
        try:
            promo_manifest = generate_adapter_promotion_manifest(
                adapter_dir=export_dir,
                base_dir=base_model_dir,
                lora_rank=rank,
                target_modules=lora_target_modules,
                base_revision=manifest.get('versions', {}).get('transformers', 'unknown'),
                strict=True,
            )
            manifest['promotion_manifest'] = promo_manifest
        except Exception as promo_exc:
            # A candidate without complete provenance is not promotable.
            manifest['promotion_manifest_error'] = str(promo_exc)
            raise
        save_status('complete', global_step=trainer.state.global_step,
                    best_model_checkpoint=trainer.state.best_model_checkpoint,
                    training_metrics=result.metrics, evaluation_metrics=final_metrics,
                    adapter_sha256=sha256(export_dir / 'adapter_model.safetensors'),
                    peak_gpu_allocated_bytes=torch.cuda.max_memory_allocated())
        (export_dir / 'training_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
        from training.model_card import write_candidate_card
        write_candidate_card(export_dir, manifest)
        print(f'Candidate saved to {export_dir}. Evaluate before promotion.', flush=True)
    except BaseException as error:
        save_status('failed', error=f'{type(error).__name__}: {error}')
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--data',
        '--dataset',
        dest='dataset_path',
        default='data/quality_candidate/train.jsonl',
    )
    parser.add_argument('--validation-data', dest='validation_dataset_path')
    parser.add_argument('--output', dest='output_path')
    parser.add_argument('--checkpoint-dir')
    parser.add_argument('--initial-adapter', help='Continue this adapter; otherwise initialize from the base model')
    parser.add_argument('--epochs', type=int, default=1)
    parser.add_argument('--max-steps', type=int, default=-1)
    parser.add_argument('--rank', type=int, default=16, choices=[8,16,32,64])
    parser.add_argument('--lora-alpha', type=int)
    parser.add_argument('--lora-dropout', type=float, default=0.0)
    parser.add_argument('--learning-rate', type=float, default=2e-5)
    parser.add_argument(
        '--max-seq-length',
        type=int,
        default=None,
        help='Max sequence length (default: selected from --benchmark-report)',
    )
    parser.add_argument(
        '--benchmark-report',
        default='runs/qwen3_context_benchmark.json',
        help='Path to benchmark report for data-driven context selection',
    )
    parser.add_argument('--min-trajectories', type=int, default=10)
    parser.add_argument('--validation-split', type=float, default=0.0)
    parser.add_argument('--preflight-only', action='store_true')
    parser.add_argument('--native-gate-report', default='runs/native_three_domain_gate_v1/report.json',
                        help='Passing live native portfolio/store/unfamiliar-topic smoke report required before training')
    parser.add_argument(
        '--override-methodology-gate',
        action='store_true',
        help='Bypass the methodology guard requiring measured limitations before sweeping hyperparameters',
    )
    train(**vars(parser.parse_args()))
