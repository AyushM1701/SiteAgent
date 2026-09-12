# Exact Steps: Fine-Tune a Code SLM for React + TypeScript + CSS

Tuned for your hardware: **RTX 4050 Laptop (6GB VRAM), 24GB DDR5 RAM**.
Base model: **Qwen2.5-Coder-3B-Instruct** (fits comfortably in 6GB with QLoRA; 7B is possible later via a rented cloud GPU using the exact same script).

Domain: React + TypeScript + CSS component/UI generation.

---

## Step 1 — Set up the environment

```bash
python3 -m venv slm-env
source slm-env/bin/activate

# PyTorch with CUDA (check pytorch.org/get-started if this doesn't match your driver)
pip install torch --index-url https://download.pytorch.org/whl/cu121

pip install unsloth
pip install datasets trl peft accelerate bitsandbytes
```

Verify GPU is visible:
```bash
python3 -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"
```
Should print `True NVIDIA GeForce RTX 4050 Laptop GPU`. Also check free VRAM before training:
```bash
nvidia-smi
```
Close browsers/other GPU apps before training — every MB counts on 6GB.

---

## Step 2 — Download the base model

```bash
pip install huggingface_hub
huggingface-cli login    # token from https://huggingface.co/settings/tokens

huggingface-cli download unsloth/Qwen2.5-Coder-3B-Instruct --local-dir ./base-model
```

---

## Step 3 — Build your held-out evaluation set (BEFORE training)

Create `eval_set.jsonl` — 50–200 real examples of React/TS/CSS tasks you actually want the model to handle well. Each needs a way to check correctness (here: does the generated `.tsx` compile / pass a lint+type check).

Example lines:

```json
{"prompt": "Write a React functional component in TypeScript called `Badge` that takes a `label: string` and `variant: 'success' | 'warning' | 'error'` prop, and renders a styled span. Include a CSS module with class names for each variant.", "check": "tsc_and_render"}
{"prompt": "Write a React TypeScript component `Accordion` that takes an array of `{title: string, content: string}` items and toggles open/closed state per item on click. Style it with plain CSS (no libraries).", "check": "tsc_and_render"}
{"prompt": "Write a custom React hook `useDebouncedValue<T>(value: T, delayMs: number): T` that returns a debounced version of the input value.", "check": "tsc_only"}
```

Base your real eval set on actual component requests you'd get in your own work — copy from real PRs/tickets if you have them. That's what makes the eval meaningful.

Save as `eval_set.jsonl`.

### Correctness checker for React/TS/CSS (Vitest + jsdom + Testing Library)
Unlike plain Python, "does it run" means "does it typecheck, render, and pass functional/a11y/interaction tests."

Install the testing harness dependencies:
```powershell
npm install -D vitest jsdom @testing-library/react @testing-library/jest-dom @testing-library/user-event @vitejs/plugin-react react react-dom @types/react @types/react-dom typescript
```

`vitest.config.ts`:
```typescript
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./vitest.setup.ts'],
    css: true,   // handles CSS module imports without erroring
    globals: true,
  },
});
```

`vitest.setup.ts`:
```typescript
import '@testing-library/jest-dom';
```

---

## Step 4 — Build your training dataset

### 4a. Collect raw examples
Best source: your own repo's real components (strip out anything sensitive/proprietary before using). Pair a natural-language instruction with the actual component code:

```json
{"instruction": "Create a reusable Button component in React + TypeScript with primary/secondary/ghost variants, a loading state, and CSS module styling.", "output": "// Button.tsx\nimport styles from './Button.module.css';\n\ninterface ButtonProps {\n  variant?: 'primary' | 'secondary' | 'ghost';\n  loading?: boolean;\n  children: React.ReactNode;\n  onClick?: () => void;\n}\n\nexport function Button({ variant = 'primary', loading = false, children, onClick }: ButtonProps) {\n  return (\n    <button\n      className={`${styles.button} ${styles[variant]}`}\n      onClick={onClick}\n      disabled={loading}\n    >\n      {loading ? 'Loading...' : children}\n    </button>\n  );\n}\n\n/* Button.module.css */\n.button { padding: 8px 16px; border-radius: 6px; border: none; cursor: pointer; }\n.primary { background: #2563eb; color: white; }\n.secondary { background: #e5e7eb; color: #111827; }\n.ghost { background: transparent; color: #2563eb; }"}
```

If you don't have enough real components, generate candidates with a frontier LLM (Claude/GPT-5) via prompts like *"Write a React+TypeScript+CSS component for X, following common conventions"* — then validate every single one with the Step 3 checker before including it. Never include unvalidated generated code in training data; it teaches the model your generator's mistakes.

Other sources to mine (filter down to only React+TS+CSS, don't dump these in wholesale):
```bash
huggingface-cli download nickrosh/Evol-Instruct-Code-80k-v1 --repo-type dataset --local-dir ./raw-data
```

### 4b. Format into instruction pairs
One JSON object per line in `train_data_raw.jsonl`, same shape as above (`instruction` / `output`).

### 4c. Validate every example
```python
# validate_data.py
import json
from check_tsx import typechecks

kept = []
with open("train_data_raw.jsonl") as f:
    for line in f:
        ex = json.loads(line)
        # Extract just the .tsx portion if the output mixes .tsx + .css;
        # adjust this split to match how you format your examples.
        tsx_part = ex["output"].split("/* ")[0]
        if typechecks(tsx_part):
            kept.append(ex)

print(f"Kept {len(kept)} valid examples")
with open("train_data.jsonl", "w") as f:
    for ex in kept:
        f.write(json.dumps(ex) + "\n")
```
```bash
python3 validate_data.py
```

**Target: 300–800 validated examples** — for a narrow domain like this, quality matters far more than hitting a big number. A smaller, cleaner set will beat a larger noisy one.

### 4d. Cover the domain's real variety
Make sure your dataset spans:
- Functional components with props/state (`useState`, `useEffect`, custom hooks)
- Styling approaches you actually use (CSS Modules, plain CSS, styled-components — pick ONE and be consistent, since mixing styling paradigms in training data will confuse a small model)
- Common patterns: forms, lists, modals, conditional rendering, event handlers
- Accessibility basics if that matters to you (aria-labels, semantic HTML) — include it explicitly in examples if you want the model to default to it

---

## Step 5 — Fine-tune with QLoRA (Unsloth, tuned for 6GB VRAM)

Create `train.py`:

```python
from unsloth import FastLanguageModel
from datasets import load_dataset
from trl import SFTTrainer, SFTConfig
import torch

# 1. Load base model in 4-bit — 3B fits comfortably in 6GB VRAM
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="unsloth/Qwen2.5-Coder-3B-Instruct",
    max_seq_length=1024,       # shorter than default 2048 — saves VRAM
    load_in_4bit=True,
)

# 2. Attach LoRA adapters
model = FastLanguageModel.get_peft_model(
    model,
    r=16,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                     "gate_proj", "up_proj", "down_proj"],
    lora_alpha=16,
    lora_dropout=0.05,
    bias="none",
    use_gradient_checkpointing="unsloth",
    random_state=42,
)

# 3. Load and format your dataset
dataset = load_dataset("json", data_files="train_data.jsonl", split="train")

def format_example(example):
    text = f"### Instruction:\n{example['instruction']}\n\n### Response:\n{example['output']}{tokenizer.eos_token}"
    return {"text": text}

dataset = dataset.map(format_example)

# 4. Train — small batch size + more accumulation steps to fit 6GB VRAM
trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=dataset,
    dataset_text_field="text",
    max_seq_length=1024,
    args=SFTConfig(
        per_device_train_batch_size=1,     # small — fits 6GB
        gradient_accumulation_steps=16,    # keeps effective batch size reasonable
        num_train_epochs=3,
        learning_rate=2e-4,
        fp16=not torch.cuda.is_bf16_supported(),
        bf16=torch.cuda.is_bf16_supported(),
        logging_steps=10,
        output_dir="outputs",
        optim="adamw_8bit",
        lr_scheduler_type="cosine",
        seed=42,
    ),
)

trainer.train()

model.save_pretrained("my-react-slm-lora")
tokenizer.save_pretrained("my-react-slm-lora")
```

Run it:
```bash
python3 train.py
```

If you hit `CUDA out of memory`:
- Drop `max_seq_length` to 768 or 512
- Confirm nothing else is using the GPU (`nvidia-smi`)
- As a last resort, drop LoRA rank `r` to 8

Expect roughly 1–3 hours for 300–800 examples at 3B on this GPU.

---

## Step 6 — Merge the LoRA adapter

```python
# merge.py
from unsloth import FastLanguageModel

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="my-react-slm-lora",
    max_seq_length=1024,
    load_in_4bit=False,
)
model.save_pretrained_merged("my-react-slm-merged", tokenizer, save_method="merged_16bit")
```
```bash
python3 merge.py
```

---

## Step 7 — Evaluate on your custom React/TS/CSS eval set

Use the Vitest + jsdom + RTL evaluation driver (`eval_custom.py`):

```bash
# Fast feedback iteration loop on a stratified 40-item subset (Batch mode, ~10s):
python eval_custom.py --model my-react-slm-merged --subset 40

# Full benchmark evaluation across all 153 examples:
python eval_custom.py --model my-react-slm-merged

# Sequential mode for live step-by-step debugging:
python eval_custom.py --model my-react-slm-merged --mode sequential

# Dry run / test harness pipeline without loading GPU weights:
python eval_custom.py --mock --subset 8
```

The driver automatically:
1. Enforces exact named exports in generation prompts (`Export the component as a named export called <Name>`).
2. Auto-binds named exports and provides fallback default export aliasing in test suites.
3. Splits TSX code and CSS modules into isolated test directories.
4. Validates TypeScript compilation (`tsc --noEmit`) and runs the full Vitest suite.
5. Reports breakdown pass rates across all 4 check categories:
   - `tsc_only`
   - `tsc_and_render`
   - `tsc_render_a11y`
   - `tsc_render_interact`
6. Exports full diagnostic error logs to `eval_results.json` for Step 9 retraining iteration.

Run this same eval set through three models to get your comparison:
1. **Base** `unsloth/Qwen2.5-Coder-3B-Instruct` (un-fine-tuned) — baseline
2. **Your fine-tuned** `my-react-slm-merged` — did it improve?
3. **Claude/GPT-5** via API with a well-written prompt — the frontier comparison

For a more thorough check beyond "does it typecheck," manually review 15–20 outputs for whether they actually follow your intended conventions (styling approach, prop naming, component structure) — typechecking catches broken code, not bad style.

---

## Step 8 — Deploy

### Local (fits your laptop easily at 3B size)
```bash
python3 -c "
from unsloth import FastLanguageModel
model, tokenizer = FastLanguageModel.from_pretrained('my-react-slm-merged', max_seq_length=1024)
model.save_pretrained_gguf('my-react-slm-gguf', tokenizer, quantization_method='q4_k_m')
"

curl -fsSL https://ollama.com/install.sh | sh
```
```
# Modelfile
FROM ./my-react-slm-gguf/model.gguf
```
```bash
ollama create my-react-slm -f Modelfile
ollama run my-react-slm
```

### If you later scale to 7B on a rented cloud GPU
Same `train.py`, just change `model_name` to `unsloth/Qwen2.5-Coder-7B-Instruct` and revert `max_seq_length` to 2048 and `per_device_train_batch_size` to 2 — the 24GB+ VRAM on a rented RTX 4090/A10 handles it without the tight tuning needed for 6GB.

---

## Step 9 — Iterate

1. Go through Step 7's failures — group them: type errors, wrong styling approach used, missed prop, ignored accessibility, wrong file structure (component vs. CSS split).
2. Write 20–40 new training examples specifically targeting your most common failure category.
3. Re-run Step 5 → Step 6 → Step 7.
4. Compare new pass rate + manual review quality against the previous run and against the frontier LLM baseline.
5. Repeat until you match/beat the frontier LLM on your eval set, or gains plateau.

---

## Order-of-operations summary

```
Step 1 → environment set up, 6GB VRAM confirmed free
Step 2 → Qwen2.5-Coder-3B-Instruct downloaded
Step 3 → eval_set.jsonl written (real React/TS/CSS tasks, BEFORE training)
Step 4 → train_data.jsonl built from real components + validated with tsc
Step 5 → train.py run (3B, 6GB-tuned settings) → LoRA adapter saved
Step 6 → merge.py run → standalone merged model
Step 7 → eval_custom.py run → base vs fine-tuned vs frontier LLM
Step 8 → GGUF/Ollama local deployment (or move to cloud GPU for 7B)
Step 9 → analyze failures, add targeted data, repeat Steps 5-7
```
