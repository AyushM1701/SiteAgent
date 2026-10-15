"""Exact causal evaluation loss without a sequence-by-vocabulary logits tensor.

P1-08 scope boundary
---------------------
chunked_causal_loss() solves ONE specific memory problem:

  EVALUATION logit memory:
    A standard lm_head pass over a full sequence materializes an
    [sequence_length × vocab_size] float32 tensor (e.g. 8192 × 151936 ≈ 4.7 GiB).
    Chunking the supervised positions avoids this peak entirely.

It does NOT address, and provides NO safety guarantee for:

  TRAINING forward/backward activation memory:
    During a training step, PyTorch retains intermediate activations for all
    36 transformer layers across the full sequence to compute gradients.
    This memory is governed separately by:
      - gradient checkpointing (recomputes activations; trades compute for memory)
      - the HealthCallback VRAM_CEILING_BYTES governor in training/train_sft.py
      - sequence-length bucketing and batch size 1

Concretely: a sequence of 8192 tokens at 4-bit base + LoRA rank 16 may consume
substantially more than 5.5 GiB of CUDA memory during the backward pass, even
when the same sequence evaluates comfortably.  The chunked evaluator cannot
prove that 8192-token training fits the RTX 4050 budget.  Only a live benchmark
with peak CUDA allocation monitoring can establish that.

See: HealthCallback.on_log() in training/train_sft.py (P1-06 VRAM governor).
"""
def chunked_causal_loss(hidden_states, labels, lm_head, chunk_size=128):
    import torch
    import torch.nn.functional as functional
    targets = labels[:, 1:]
    keep = targets != -100
    states = hidden_states[:, :-1][keep]
    targets = targets[keep]
    if targets.numel() == 0:
        raise ValueError('Evaluation batch has no supervised next-token targets')
    total = torch.zeros((), dtype=torch.float32, device=hidden_states.device)
    for start in range(0, targets.numel(), chunk_size):
        logits = lm_head(states[start:start+chunk_size])
        total += functional.cross_entropy(logits.float(), targets[start:start+chunk_size], reduction='sum')
    return total / targets.numel()
