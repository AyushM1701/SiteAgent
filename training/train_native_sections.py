#!/usr/bin/env python3
"""QLoRA fine-tune of Qwen3-4B on native section data (scripts/build_native_section_data.py).

The model learns to write a site section's TSX and CSS from a design spec plus its
approved copy, and keeps its copy-writing skill (content rows are mixed in).
Uses the same RTX 4050 6 GB profile as training/train_sft.py: 4-bit base, LoRA on
all projection layers, 8-bit AdamW, gradient checkpointing, prompt-masked loss on
the final assistant turn only, and a 5.5 GiB peak-allocation governor.

Gates for this dataset (instead of train_sft.py's reviewed-freeform-site gates):
  * every business family in validation is absent from training (family-disjoint);
  * no source brief or exact prompt appears in both splits;
  * every code target is the design kit's own rendering, which the builder checks
    parses, and every row fits the context with no truncation.
The candidate is written to its own directory and is never promoted automatically.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
if (BASE_DIR / "base-model").exists():
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
os.environ["UNSLOTH_CE_LOSS_TARGET_GB"] = "0.25"

from training.preflight import CHAT_MARKERS, read_jsonl, output_paths, sha256  # noqa: E402
from training.cuda_budget import assert_cuda_budget  # noqa: E402

TARGET_MODULES = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]


def validate_row(row: dict) -> list[dict]:
    """Native rows: system, user, assistant. Code targets must parse; content targets must be JSON."""
    from agent.site_kit.native import parse_native_files
    from agent.site_kit.content import parse_json_object
    messages = row.get("messages")
    if not isinstance(messages, list) or [m.get("role") for m in messages] != ["system", "user", "assistant"]:
        raise ValueError("Expected system, user and assistant messages")
    for message in messages:
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise ValueError("Empty message")
        if any(marker in content for marker in CHAT_MARKERS) or "<thought>" in content:
            raise ValueError("Chat or thinking marker inside a message")
    target = messages[-1]["content"]
    if row.get("task_type") == "section_code":
        import re
        component = re.search(r"Files: src/components/(\w+)\.tsx", messages[1]["content"])
        if not component or parse_native_files(target, component.group(1))[1]:
            raise ValueError("Code target does not parse as the section's two files")
    elif row.get("task_type") == "section_content":
        if parse_json_object(target) is None:
            raise ValueError("Content target is not a JSON object")
    else:
        raise ValueError(f"Unknown task_type {row.get('task_type')!r}")
    return messages


def encode_rows(rows: list[dict], tokenizer, chat_tokenizer, max_length: int) -> list[dict]:
    """Tokenise with the native chat template; supervise only the final assistant turn
    (and its end-of-turn token). Refuses truncation and duplicate conversations."""
    from agent.agent_protocol import format_chatml
    encoded, seen = [], set()
    for index, row in enumerate(rows, 1):
        messages = validate_row(row)
        key = json.dumps(messages, sort_keys=True)
        if key in seen:
            raise ValueError(f"Row {index}: duplicate conversation")
        seen.add(key)
        text = format_chatml(messages, False, tokenizer=chat_tokenizer)
        prefix = format_chatml(messages[:-1], True, tokenizer=chat_tokenizer)
        if not text.startswith(prefix):
            raise ValueError(f"Row {index}: target does not continue the inference prompt")
        ids = tokenizer.encode(text, add_special_tokens=False)
        if len(ids.ids) > max_length:
            raise ValueError(f"Row {index} ({row.get('task_id')}): {len(ids.ids)} tokens > {max_length}; no truncation allowed")
        end = text.index("<|im_end|>", len(prefix)) + len("<|im_end|>")
        labels = [token if len(prefix) <= left and right <= end else -100
                  for token, (left, right) in zip(ids.ids, ids.offsets)]
        if not any(label != -100 for label in labels):
            raise ValueError(f"Row {index}: no supervised tokens")
        encoded.append({"input_ids": ids.ids, "attention_mask": [1] * len(ids.ids), "labels": labels})
    return encoded


def check_split(train: list[dict], validation: list[dict]) -> None:
    for key in ("family_id", "source_task_id"):
        if any(not row.get(key) for row in train + validation):
            raise ValueError(f"Every row needs {key}")
        overlap = {r[key] for r in train} & {r[key] for r in validation}
        if overlap:
            raise ValueError(f"Train/validation overlap in {key}: {sorted(overlap)[:5]}")
    prompts = lambda rows: {m["content"] for r in rows for m in r["messages"] if m["role"] == "user"}
    if prompts(train) & prompts(validation):
        raise ValueError("A user prompt appears in both splits")


def train(args) -> None:
    from transformers import AutoTokenizer
    from tokenizers import Tokenizer

    base = BASE_DIR / "base-model"
    from agent.base_model_fingerprint import verify_base_model_architecture
    fingerprint = verify_base_model_architecture(base, strict=True, require_4b=True)
    if not fingerprint["is_authentic_qwen3"]:
        raise ValueError("Training requires the authentic Qwen3-4B base model")
    export_dir, run_dir = output_paths(BASE_DIR, args.output, args.checkpoint_dir)

    raw_train, raw_val = read_jsonl(args.data), read_jsonl(args.validation_data)
    check_split(raw_train, raw_val)
    if args.max_validation_rows and len(raw_val) > args.max_validation_rows:
        # A fixed, family-balanced subset keeps periodic evaluation affordable.
        raw_val = sorted(raw_val, key=lambda r: (r["task_id"]))[:: max(1, len(raw_val) // args.max_validation_rows)][: args.max_validation_rows]

    cpu_tok = Tokenizer.from_file(str(base / "tokenizer.json"))
    cpu_tok.no_truncation()
    cpu_tok.no_padding()
    chat_tok = AutoTokenizer.from_pretrained(str(base), local_files_only=True)
    from agent.agent_protocol import set_default_tokenizer
    set_default_tokenizer(chat_tok)
    train_rows = encode_rows(raw_train, cpu_tok, chat_tok, args.max_seq_length)
    eval_rows = encode_rows(raw_val, cpu_tok, chat_tok, args.max_seq_length)
    lengths = sorted(len(r["input_ids"]) for r in train_rows)
    manifest = {
        "task": "native_section_authoring",
        "dataset_path": str(Path(args.data).resolve()), "dataset_sha256": sha256(args.data),
        "validation_dataset_sha256": sha256(args.validation_data),
        "train_rows": len(train_rows), "validation_rows": len(eval_rows),
        "train_by_type": {t: sum(r.get("task_type") == t for r in raw_train) for t in ("section_code", "section_content")},
        "max_seq_length": args.max_seq_length,
        "length_p50": lengths[len(lengths) // 2], "length_max": lengths[-1],
        "supervised_tokens": sum(sum(t != -100 for t in r["labels"]) for r in train_rows),
        "rank": args.rank, "lora_alpha": args.lora_alpha, "learning_rate": args.learning_rate,
        "epochs": args.epochs, "max_steps": args.max_steps, "gradient_accumulation_steps": args.grad_accum,
        "loss_masking": "final assistant content and end-of-turn token only",
        "base_fingerprint": fingerprint.get("sha256") or fingerprint.get("fingerprint"),
        "status": "preflight",
    }
    print(json.dumps(manifest, indent=2), flush=True)
    if args.preflight_only:
        return

    os.chdir(BASE_DIR)
    from unsloth import FastLanguageModel
    import torch
    from datasets import Dataset
    from transformers import TrainerCallback
    from trl import SFTTrainer, SFTConfig
    from trl.trainer.sft_trainer import DataCollatorForLanguageModeling

    if not torch.cuda.is_available():
        raise RuntimeError("This QLoRA profile requires CUDA")
    torch.backends.cuda.enable_flash_sdp(True)
    torch.backends.cuda.enable_math_sdp(False)
    torch.backends.cuda.enable_mem_efficient_sdp(True)
    torch.backends.cuda.enable_cudnn_sdp(True)
    free_bytes, _ = torch.cuda.mem_get_info()
    if free_bytes < 4.9 * 1024**3:
        raise RuntimeError("Less than 4.9 GiB GPU memory free. Stop the workbench (it holds the model) before training.")
    ceiling = int(5.5 * 1024**3)
    run_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = run_dir / "run_manifest.json"

    def save_status(status, **values):
        manifest.update(status=status, **values)
        tmp = manifest_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(manifest, indent=2, default=str) + "\n", encoding="utf-8")
        tmp.replace(manifest_path)

    save_status("loading")
    model, tokenizer = FastLanguageModel.from_pretrained(model_name=str(base), max_seq_length=args.max_seq_length,
                                                         load_in_4bit=True, local_files_only=True)
    from agent.agent_protocol import set_default_tokenizer, format_chatml
    set_default_tokenizer(tokenizer)
    for row, encoded in list(zip(raw_train, train_rows))[:50]:
        if tokenizer(format_chatml(row["messages"], False, tokenizer=tokenizer), add_special_tokens=False)["input_ids"] != encoded["input_ids"]:
            raise ValueError("Loaded tokenizer differs from preflight; refusing mismatched labels")
    model = FastLanguageModel.get_peft_model(model, r=args.rank, lora_alpha=args.lora_alpha, lora_dropout=0.0,
                                             target_modules=TARGET_MODULES, bias="none",
                                             use_gradient_checkpointing="unsloth", random_state=42)
    FastLanguageModel.for_training(model, use_gradient_checkpointing="unsloth")
    trainable = [(n, p) for n, p in model.named_parameters() if p.requires_grad]
    if not trainable or any("lora_" not in n for n, _ in trainable):
        raise ValueError("Expected only LoRA parameters to be trainable")
    manifest["trainable_parameters"] = sum(p.numel() for _, p in trainable)
    manifest["versions"] = {k: __import__("importlib.metadata").metadata.version(k)
                            for k in ("torch", "transformers", "trl", "unsloth", "peft")}
    model.config.use_cache = False
    bf16 = torch.cuda.is_bf16_supported()
    config = SFTConfig(
        output_dir=str(run_dir), per_device_train_batch_size=1, per_device_eval_batch_size=1,
        gradient_accumulation_steps=args.grad_accum, num_train_epochs=args.epochs, max_steps=args.max_steps,
        learning_rate=args.learning_rate, warmup_ratio=0.03, lr_scheduler_type="cosine",
        optim="adamw_8bit", weight_decay=0.01, fp16=not bf16, bf16=bf16, fp16_full_eval=not bf16, bf16_full_eval=bf16,
        logging_steps=5, max_grad_norm=1.0, eval_strategy="steps", eval_steps=args.eval_steps,
        save_strategy="steps", save_steps=args.eval_steps, save_total_limit=2, eval_on_start=False,
        prediction_loss_only=True, eval_accumulation_steps=1, load_best_model_at_end=True,
        metric_for_best_model="eval_loss", greater_is_better=False, report_to="none", seed=42, data_seed=42,
        max_length=args.max_seq_length, packing=False, dataset_kwargs={"skip_prepare_dataset": True},
        dataloader_num_workers=0, dataloader_pin_memory=False,
    )

    class Health(TrainerCallback):
        def on_optimizer_step(self, args_, state, control, **kwargs):
            torch.cuda.empty_cache()
            assert_cuda_budget("after optimizer step", torch)

        def on_log(self, args_, state, control, logs=None, **kwargs):
            for key in ("loss", "eval_loss", "grad_norm"):
                value = (logs or {}).get(key)
                if value is not None and not math.isfinite(float(value)):
                    raise FloatingPointError(f"Non-finite {key}: {value}")
            peak = torch.cuda.max_memory_allocated()
            save_status("training", global_step=state.global_step, max_steps=state.max_steps,
                        latest_metrics=logs, peak_gpu_allocated_bytes=peak)
            if peak > ceiling:
                raise RuntimeError(f"Peak CUDA allocation {peak / 1024**3:.2f} GiB exceeds the 5.5 GiB ceiling")

    class Collator(DataCollatorForLanguageModeling):
        def torch_call(self, examples):
            batch = super().torch_call(examples)
            if "attention_mask" in batch and bool(batch["attention_mask"].all()):
                del batch["attention_mask"]
            return batch

    class BoundedEvalTrainer(SFTTrainer):
        def prediction_step(self, model_, inputs, prediction_loss_only, ignore_keys=None):
            from training.memory_loss import chunked_causal_loss
            inputs = self._prepare_inputs(inputs)
            base_model = self.accelerator.unwrap_model(model_).get_base_model()
            with torch.no_grad(), self.compute_loss_context_manager():
                hidden = base_model.model(input_ids=inputs["input_ids"], attention_mask=inputs.get("attention_mask"),
                                          use_cache=False, return_dict=True).last_hidden_state
                loss = chunked_causal_loss(hidden, inputs["labels"], base_model.get_output_embeddings())
            return loss.detach(), None, None

    trainer = BoundedEvalTrainer(
        model=model, processing_class=tokenizer, args=config,
        train_dataset=Dataset.from_list(train_rows), eval_dataset=Dataset.from_list(eval_rows),
        data_collator=Collator(pad_token_id=tokenizer.pad_token_id, completion_only_loss=False),
        callbacks=[Health()],
    )
    batch = trainer.data_collator([train_rows[0]])
    if batch["labels"][0, :len(train_rows[0]["labels"])].tolist() != train_rows[0]["labels"]:
        raise ValueError("Data collator altered response-only loss masks")
    torch.cuda.reset_peak_memory_stats()
    save_status("training")
    result = trainer.train(resume_from_checkpoint=args.resume or None)
    final = trainer.evaluate()
    export_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(export_dir))
    tokenizer.save_pretrained(str(export_dir))
    from agent.base_model_fingerprint import generate_adapter_promotion_manifest
    manifest["promotion_manifest"] = generate_adapter_promotion_manifest(
        adapter_dir=export_dir, base_dir=base, lora_rank=args.rank, target_modules=TARGET_MODULES,
        base_revision=manifest["versions"].get("transformers", "unknown"), strict=True)
    save_status("complete", global_step=trainer.state.global_step,
                best_model_checkpoint=trainer.state.best_model_checkpoint,
                training_metrics=result.metrics, evaluation_metrics=final,
                adapter_sha256=sha256(export_dir / "adapter_model.safetensors"),
                peak_gpu_allocated_bytes=torch.cuda.max_memory_allocated())
    (export_dir / "training_manifest.json").write_text(json.dumps(manifest, indent=2, default=str) + "\n", encoding="utf-8")
    print(f"Candidate adapter saved to {export_dir}. Evaluate it before using it in the workbench.", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data", default=str(BASE_DIR / "data/native_sections/train.jsonl"))
    parser.add_argument("--validation-data", default=str(BASE_DIR / "data/native_sections/validation.jsonl"))
    parser.add_argument("--output", default=str(BASE_DIR / "models/qwen3-siteagent-native-sections-r16"))
    parser.add_argument("--checkpoint-dir", default=str(BASE_DIR / "runs/qwen3-siteagent-native-sections-checkpoints"))
    parser.add_argument("--max-seq-length", type=int, default=8192)
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--max-steps", type=int, default=-1)
    parser.add_argument("--rank", type=int, default=16)
    parser.add_argument("--lora-alpha", type=int, default=32)
    parser.add_argument("--learning-rate", type=float, default=1e-4)
    parser.add_argument("--grad-accum", type=int, default=8)
    parser.add_argument("--eval-steps", type=int, default=50)
    parser.add_argument("--max-validation-rows", type=int, default=120)
    parser.add_argument("--resume", help="Checkpoint directory to resume from")
    parser.add_argument("--preflight-only", action="store_true")
    train(parser.parse_args())
