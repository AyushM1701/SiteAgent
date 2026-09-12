"""
train_dpo.py — Direct Preference Optimization (DPO) for ReactAgent SLM
Fine-tunes my-react-agent-lora using verified self-correction preference pairs
(e.g., dpo_pairs_verified.jsonl) to boost 1-shot pass rate from ~51% to 60%+.

Usage:
    python train_dpo.py --dataset dpo_pairs_verified.jsonl --epochs 1 --beta 0.1
"""

import argparse
import json
import os
import sys
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "agent"))

from agent_protocol import AGENT_SYSTEM_PROMPT, format_chatml, DEFAULT_MAX_SEQ_LENGTH


def wrap_completion(code_or_xml: str) -> str:
    """Ensures response is wrapped in standard XML tool_call format if bare code."""
    if "<tool_call" in code_or_xml:
        return code_or_xml.strip()
    return (
        f"<thought>\nImplementing component according to specification.\n</thought>\n"
        f'<tool_call name="write_component">\n'
        f"<tsx>\n{code_or_xml.strip()}\n</tsx>\n"
        f"</tool_call>"
    )


def load_dpo_dataset(dataset_path: str, tokenizer):
    """Loads and formats verified preference pairs into DPO format: prompt, chosen, rejected."""
    from datasets import Dataset

    if not os.path.exists(dataset_path):
        if (BASE_DIR / "data" / "dpo" / dataset_path).exists():
            dataset_path = str(BASE_DIR / "data" / "dpo" / dataset_path)
        elif (BASE_DIR / "data" / dataset_path).exists():
            dataset_path = str(BASE_DIR / "data" / dataset_path)
        elif (BASE_DIR / dataset_path).exists():
            dataset_path = str(BASE_DIR / dataset_path)
        else:
            raise FileNotFoundError(f"DPO dataset not found: {dataset_path}")

    raw_items = []
    with open(dataset_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    raw_items.append(json.loads(line))
                except Exception:
                    continue

    if not raw_items:
        raise ValueError(f"No valid DPO items loaded from {dataset_path}")

    formatted_data: Dict[str, List[str]] = {
        "prompt": [],
        "chosen": [],
        "rejected": [],
    }

    for item in raw_items:
        user_prompt = item.get("prompt", "")
        chosen_code = item.get("chosen", "")
        rejected_code = item.get("rejected", "")

        if not user_prompt or not chosen_code or not rejected_code:
            continue

        # Format conversation prompt up to assistant generation prefix
        messages = [
            {"role": "system", "content": AGENT_SYSTEM_PROMPT},
            {"role": "user", "content": f"Write a React component in TypeScript with CSS Modules for: {user_prompt}"},
        ]
        prompt_text = format_chatml(messages, add_generation_prompt=True)

        chosen_text = wrap_completion(chosen_code) + tokenizer.eos_token
        rejected_text = wrap_completion(rejected_code) + tokenizer.eos_token

        formatted_data["prompt"].append(prompt_text)
        formatted_data["chosen"].append(chosen_text)
        formatted_data["rejected"].append(rejected_text)

    print(f"Loaded {len(formatted_data['prompt'])} verified DPO training pairs from {dataset_path}.")
    return Dataset.from_dict(formatted_data)


def train_dpo(
    dataset_path: str = "dpo_pairs_verified.jsonl",
    model_path: str = "my-react-agent-lora",
    output_dir: str = "my-react-agent-lora-dpo",
    epochs: int = 1,
    beta: float = 0.1,
    learning_rate: float = 5e-5,
    max_seq_length: int = DEFAULT_MAX_SEQ_LENGTH,
    batch_size: int = 1,
    gradient_accumulation_steps: int = 4,
):
    print("=" * 75)
    print("       DPO PREFERENCE ALIGNMENT TRAINING (ReactAgent SLM)           ")
    print("=" * 75)

    import torch

    if not torch.cuda.is_available():
        print("Error: CUDA GPU not detected. DPO training requires an NVIDIA GPU.")
        sys.exit(1)

    print(f"Detected GPU: {torch.cuda.get_device_name(0)}")
    print(f"Allocated VRAM: {torch.cuda.memory_allocated(0)/(1024**2):.1f} MB")

    from unsloth import FastLanguageModel, PatchDPOTrainer
    from trl import DPOTrainer, DPOConfig

    # Enable Unsloth memory-efficient DPO patching
    try:
        PatchDPOTrainer()
    except Exception as e:
        print(f"[Note]: PatchDPOTrainer note: {e}")

    print(f"\n1. Loading model from {model_path} (max_seq_length={max_seq_length})...")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=model_path,
        max_seq_length=max_seq_length,
        load_in_4bit=True,
    )

    print("\n2. Loading and preparing DPO pairs...")
    dpo_dataset = load_dpo_dataset(dataset_path, tokenizer)
    if len(dpo_dataset) < 2:
        print("Error: insufficient DPO pairs for training (need at least 2).")
        sys.exit(1)

    print(f"\n3. Configuring DPO Trainer (epochs={epochs}, beta={beta}, lr={learning_rate})...")
    dpo_config = DPOConfig(
        output_dir=output_dir,
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        gradient_accumulation_steps=gradient_accumulation_steps,
        learning_rate=learning_rate,
        beta=beta,
        fp16=not torch.cuda.is_bf16_supported(),
        bf16=torch.cuda.is_bf16_supported(),
        logging_steps=1,
        save_strategy="no",
        optim="adamw_8bit",
        seed=42,
    )

    trainer = DPOTrainer(
        model=model,
        ref_model=None,  # Implicit reference model supported by PEFT LoRA
        args=dpo_config,
        beta=beta,
        train_dataset=dpo_dataset,
        tokenizer=tokenizer,
        max_length=max_seq_length,
        max_prompt_length=max_seq_length // 2,
    )

    print("\n4. Starting DPO Training...")
    trainer.train()

    print(f"\n5. DPO Training Complete! Saving aligned adapter to: {output_dir}...")
    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)
    print(f"Saved successfully to: {os.path.abspath(output_dir)}")
    print("\nNext step: evaluate aligned model with:")
    print(f"python evaluate.py --model {output_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run DPO Alignment on ReactAgent SLM")
    default_dpo = str(BASE_DIR / "data" / "dpo" / "dpo_pairs_verified.jsonl")
    if not Path(default_dpo).exists():
        default_dpo = "dpo_pairs_verified.jsonl"
    parser.add_argument("--dataset", "--data", dest="dataset", type=str, default=default_dpo, help="Path to verified DPO pairs JSONL.")
    parser.add_argument("--model-path", type=str, default=str(BASE_DIR / "my-react-agent-lora"), help="Path to base LoRA adapter.")
    parser.add_argument("--output-dir", type=str, default=str(BASE_DIR / "my-react-agent-lora-dpo"), help="Output directory for aligned LoRA.")
    parser.add_argument("--epochs", type=int, default=1, help="Number of training epochs (default: 1).")
    parser.add_argument("--beta", type=float, default=0.1, help="DPO beta parameter (default: 0.1).")
    parser.add_argument("--learning-rate", type=float, default=5e-5, help="Learning rate (default: 5e-5).")
    parser.add_argument("--max-seq-length", type=int, default=DEFAULT_MAX_SEQ_LENGTH, help=f"Max sequence length (default: {DEFAULT_MAX_SEQ_LENGTH}).")
    parser.add_argument("--batch-size", type=int, default=1, help="Batch size per device (default: 1).")
    parser.add_argument("--grad-accum", type=int, default=4, help="Gradient accumulation steps (default: 4).")
    args = parser.parse_args()

    train_dpo(
        dataset_path=args.dataset,
        model_path=args.model_path,
        output_dir=args.output_dir,
        epochs=args.epochs,
        beta=args.beta,
        learning_rate=args.learning_rate,
        max_seq_length=args.max_seq_length,
        batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
    )
