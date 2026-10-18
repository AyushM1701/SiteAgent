# SiteAgent (ReactAgent SLM)

> **A local website builder powered by a small language model.**
> Describe a site in plain English; SiteAgent plans it, writes it as a React + TypeScript project,
> builds it, checks it in a real browser (types, build, accessibility, motion, runtime) and shows a
> live preview you can inspect and edit. Built on `Qwen/Qwen3-4B`; runs on your own machine —
> an NVIDIA/AMD GPU, an Apple Silicon Mac, or just a CPU.

---

## Quick start

**You need:** Python 3.10–3.13, [Node.js 18+](https://nodejs.org), Git, ~15 GB of free disk
(8 GB is the model). A GPU is optional.

```bash
git clone <this-repo-url> siteagent
cd siteagent
```

**1. Install** (creates `.venv`, picks the right PyTorch for your hardware, builds the UI,
downloads Qwen3-4B, then runs a health check):

```bash
# macOS / Linux / Git Bash
bash scripts/setup.sh
```

```bat
:: Windows (Command Prompt or PowerShell)
scripts\setup.bat
```

Options: `--cpu` (force CPU), `--skip-model` (download later with `python slm.py download`),
`--base Qwen/Qwen3-1.7B` (smaller model for low-memory machines),
`--adapter USER/REPO` (also download a fine-tuned native adapter).

**2. Run the workbench** at <http://127.0.0.1:5000>:

```bash
bash scripts/run_web_ui.sh          # macOS / Linux / Git Bash
scripts\run_web_ui.bat              # Windows
```

**3. Check your setup at any time:**

```bash
python slm.py doctor
```

It prints your hardware profile (GPU, memory, backend, context length) and every missing piece
with the command that fixes it. The top bar of the workbench shows the model's state:
amber **Loading model** while it loads, green **Ready** when you can send a prompt.

### Hardware

The model loader (`agent/hardware.py`) detects your machine and picks the backend, precision and
context length automatically:

| Machine | How the model runs | Notes |
|---|---|---|
| NVIDIA GPU, 6 GB+ VRAM | 4-bit (Unsloth or bitsandbytes) on the GPU | Developed on a 6 GB RTX 4050. ~25 tokens/s. |
| NVIDIA GPU, 8 GB+ without 4-bit libraries | float16 on the GPU | Used automatically if Unsloth/bitsandbytes can't install. |
| AMD GPU (Linux, ROCm) | Transformers on the GPU | Unsloth is NVIDIA-only. |
| Apple Silicon (M1+), 16 GB+ | float16 on Metal | |
| CPU only, 12 GB+ RAM | bfloat16 on the CPU | Works; a few tokens/s. Kit mode stays usable. |
| Less memory | use `--base Qwen/Qwen3-1.7B` | Kit mode only (the native adapter needs Qwen3-4B). |

Override anything with environment variables: `SLM_DEVICE=cuda|mps|cpu`,
`SLM_BACKEND=unsloth|transformers`, `SLM_LOAD_IN_4BIT=0|1`, `SLM_CONTEXT_LENGTH=8192`,
`MODEL_PATH=<model or adapter folder>`.

### Two ways to build a site

* **Design kit (default, fast — about 1–2 minutes per site).** The model writes each section's
  copy as JSON and the design kit (`agent/site_kit/`) renders accessible, token-driven React/CSS:
  12 contrast-checked art directions, vetted photography, menus, galleries, carts, FAQs, forms,
  a native motion system, favicons and OpenGraph tags.
* **Native (the model writes the code — about 20–40 minutes per site on a 6 GB GPU).** A
  fine-tuned LoRA adapter writes every section's React component and CSS itself; the kit only
  plans the site and supplies shared design tokens. Each section is accepted only if it
  typechecks, keeps the approved copy exactly and keeps every behaviour the design system requires;
  otherwise the kit renders that section. On held-out business types the adapter's sections were
  accepted 92% of the time vs 6% for the untuned model — see
  [docs/NATIVE_SECTION_TRAINING.md](docs/NATIVE_SECTION_TRAINING.md).
  Choose it per request in the composer (*Advanced → Site code written by → The model*), or start
  with `scripts/run_web_ui.sh --native`. It needs an adapter in `models/`: download one with
  `python slm.py download --adapter USER/REPO`, or train your own (below).

### Website requests

Describe the audience, content, visual style and interactions you want. An inline
`Sections: a, b, c` or `Include: a, b, c` list is followed exactly. Products, prices, projects,
testimonials and contact details appear only when you supply them — the site never invents them.

### Training your own adapter

```bash
python scripts/build_native_section_data.py generate --per-family 5   # copy from the base model (GPU, ~2 h)
python scripts/build_native_section_data.py assemble                   # train/validation rows
python training/train_native_sections.py                               # QLoRA, ~4-5 h on a 6 GB GPU
python scripts/eval_native_sections.py --model models/<adapter> --out runs/eval.json
python scripts/publish_adapter.py models/<adapter> --repo YOUR_NAME/siteagent-native-qwen3-4b  # share it
```

Training needs an NVIDIA GPU with Unsloth (`pip install -r requirements-gpu.txt`).

### Troubleshooting

| Symptom | Fix |
|---|---|
| Top bar stays **Loading model** | Check the server console; run `python slm.py doctor`. |
| CUDA out of memory | Close other GPU apps, or `SLM_CONTEXT_LENGTH=4096`, or `SLM_DEVICE=cpu`. |
| `bitsandbytes`/`unsloth` failed to install | Fine — the loader falls back to float16 Transformers (needs ~8 GB VRAM). |
| Preview shows "build failed" | The panel shows the error; fix the file in the Code tab or click *Rebuild preview*. |
| Browser checks skipped | `python -m playwright install chromium` |
| Blank workbench page | `cd frontend && npm ci && npm run build` |

---

## 🏗️ Architecture & Directory Layout

```
reactagent-slm/
├── README.md                      # Project overview and quickstart guide
├── LICENSE                        # MIT License
├── .gitignore                     # Excludes heavy checkpoints, caches, and test runs
├── requirements.txt               # Pinned Python dependencies
├── package.json                   # Root npm config for Vitest & TypeScript compiler
├── tsconfig.json                  # Strict TypeScript configuration
├── vitest.config.ts               # jsdom + React Testing Library test harness
├── vitest.setup.ts                # RTL ambient test environment
├── css.d.ts                       # CSS module ambient type definitions
│
├── slm.py                         # Unified path-safe CLI entry point
│
├── agent/                         # Core Agent Runtime & Protocol
│   ├── agent.py                   # Multi-turn autonomous agent loop & self-correction
│   ├── agent_protocol.py          # XML ChatML schema, system prompts & output parser
│   ├── site_brief.py              # Two-stage XML content brief synthesizer (15+ domains)
│   ├── site_kit/                  # Design kit: themes, imagery, base CSS, content model, renderers
│   ├── style_ingest.py            # Zero-LLM CSS design system parser, presets & conformance validator
│   └── visual_judge.py            # Playwright visual quality & aesthetic scoring judge
│
├── server/                        # Web Workbench Backend
│   ├── app.py                     # Flask SSE streaming server + Vite scaffolder + browser auto-launch
│   └── shell_server.py            # Isolated WebSocket PTY terminal runner (cross-platform)
│
├── web_ui_static/                 # Web Workbench Frontend
│   └── index.html                 # Single-page reactive workbench & live preview canvas
│
├── training/                      # Training & Evaluation
│   ├── train_sft.py               # QLoRA Supervised Fine-Tuning (RTX 4050 6GB tuned)
│   ├── train_dpo.py               # Direct Preference Optimization for 1-shot boost
│   └── evaluate.py                # High-performance Vitest+RTL benchmark evaluation harness
│
├── data_pipeline/                 # Consolidated Data Mining & Curation
│   ├── generate_trajectories.py   # Gold-standard site trajectory generator (Batches 1-5 + Interactive)
│   ├── generate_batch6.py         # Batch 6 aesthetic trajectories (85 domains across 5 design archetypes)
│   ├── curate_dataset.py          # Multi-source dataset ingestion (shadcn, HF, Teacher LLMs, Stack v2)
│   └── build_dataset.py           # Dataset builder (STaR task bank, leak-free expanded, merge, validate)
│
├── data/                          # Versioned Training & Evaluation Datasets
│   ├── training_data.jsonl        # Master merged SFT training corpus
│   ├── star_task_bank.jsonl       # 150 held-out STaR tasks with complete Vitest test suites
│   ├── website_task_bank.jsonl    # Multi-domain website specifications
│   ├── dpo/                       # DPO Preference Pairs
│   │   ├── dpo_pairs.jsonl
│   │   └── dpo_pairs_verified.jsonl
│   └── eval/                      # Held-out Benchmark Eval Set
│       └── react_ts_css_eval_set_combined.jsonl
│
├── docs/                          # Documentation & Historical Runs
│   ├── RUNBOOK.md                 # Complete operations and troubleshooting runbook
│   ├── PROJECT_JOURNEY.md         # Architecture decision log and research trajectory
│   ├── architecture_and_source.md # Complete source and architecture documentation
│   ├── architecture.md            # Pure system architecture and engineering deep-dive
│   ├── source.md                  # Complete source code index and module catalog
│   └── agent_results.json         # Benchmark evaluation trajectory records
│
└── scripts/                       # Cross-Platform Automation Commands
    ├── setup.sh / setup.bat       # One-click environment bootstrap & weight download
    ├── train_all.sh / train_all.bat # One-command dataset merge, validate, and SFT training
    └── run_web_ui.sh / run_web_ui.bat # One-command web workbench server & browser launcher
```

---

## 🎯 Key Features & Capabilities

### 1. Autonomous Multi-Turn Self-Correction Loop
- **Turn 1 Best-of-2 Sampling**: Samples two distinct candidates on Turn 1 with cached evaluation reuse to maximize 1-shot accuracy without doubling multi-turn costs.
- **Strict Protocol Enforcement**: Uses XML tool-calling syntax (`<tool_call name="write_component">`, `<tool_call name="write_site">`, `<finish>`) with ChatML formatting.
- **Intelligent Observation Pruning**: Automatically extracts primary TypeScript compiler errors, strips verbose stack traces, and provides actionable compiler feedback to the model.
- **Anti-Stuck Escalation**: Detects repetitive error cycles across turns and escalates temperature / repetition penalty to break out of local minima.

### 2. Full-Website & Component Scaffolding
- **Multi-Turn Site Architecture**: Generates cohesive 4-to-6 section websites (Header, Hero, Services, Interactive Widgets, Pricing Calculator, Testimonials, Footer).
- **Domain-Specific Visual Systems**: Tailors color palettes, typography tokens (Cinzel, Space Grotesk, Outfit, Playfair), and glassmorphism styling across 15+ business verticals.
- **Automatic Vite Preview**: Instantly scaffolds `package.json`, `vite.config.ts`, and `index.html` to run hot-reloading dev servers directly in the browser iframe.

### 3. High-Performance Evaluation Harness
- **153 Disjoint Held-Out Tasks**: Covers 4 strict verification variants: `tsc_only`, `tsc_and_render`, `tsc_render_a11y`, and `tsc_render_interact`.
- **Fast Batch Mode**: Runs the complete test suite in 10–15 seconds via parallelized Vitest processes.
- **Zero-Overlap Guarantee**: Enforces compile-time and run-time checks preventing any train/eval data contamination.

---

## 🧠 Model & LoRA Configuration

**Default model:** the workbench runs the **base `Qwen/Qwen3-4B` model** (design kit mode). The native
section adapter (`models/qwen3-siteagent-native-sections-r16-v2`, trained with
`training/train_native_sections.py`) is loaded with `MODEL_PATH` / `scripts/run_web_ui.sh --native`.
Older candidate adapters under `models/` are unpromoted experiments.
`my-react-agent-lora/` holds the historical Qwen2.5 adapter and is not loaded by default.

The QLoRA training profile used for Qwen3 candidates:

| Hyperparameter | Value | Notes |
|---|---|---|
| **Base Model** | `Qwen/Qwen3-4B` | 4B-parameter base model in `./base-model` |
| **LoRA Rank (`r`)** | `16` | Adapter rank |
| **LoRA Alpha (`alpha`)** | `16` | Scaling factor $\alpha / r = 1.0$ |
| **Target Modules** | `q_proj`, `k_proj`, `v_proj`, `o_proj`, `gate_proj`, `up_proj`, `down_proj` | All 7 attention & MLP projections |
| **LoRA Dropout** | `0.0` | 0.0 for Unsloth fast kernel patching |
| **Precision** | `4-bit NF4` (QLoRA) | Fits in 6GB VRAM (RTX 4050 Laptop GPU) |
| **Max Sequence Length** | `8192` tokens | Thread-safe generation window |
| **Rank Sweep Options** | `r in [8, 16, 32, 64]` | Configurable in `training/train_sft.py --rank` |

---

## 🛠️ Unified CLI Reference (`slm.py`)

The root CLI provides a unified interface across all workflows:

| Command | Description |
|---|---|
| `python slm.py pipeline` | Full end-to-end training pipeline (merge → validate → train SFT) |
| `python slm.py setup` | Install everything for this machine (`--cpu`, `--skip-model`, `--adapter`) |
| `python slm.py doctor` | Check hardware, dependencies and models; print fixes |
| `python slm.py download` | Download Qwen3-4B (`--base`, `--adapter USER/REPO`) |
| `python slm.py serve` | Launch web UI workbench on `http://127.0.0.1:5000` |
| `python slm.py train` | Run QLoRA SFT training (`training/train_sft.py`) |
| `python slm.py train-dpo` | Run Direct Preference Optimization (`training/train_dpo.py`) |
| `python slm.py evaluate` | Run Vitest + jsdom benchmark evaluation suite |
| `python slm.py agent` | Run autonomous agent loop interactively or with `--mock` |
| `python slm.py dataset merge` | Merge all trajectory sources into `data/training_data.jsonl` |
| `python slm.py dataset validate` | Validate trajectories through live tsc and Vitest compilers |
| `python slm.py generate site` | Generate site trajectory batches (`--batch 1|2|3|4|5|interactive|all`) |

---

## 💻 Hardware Requirements

See [Hardware](#hardware) above: NVIDIA (4-bit, 6 GB+), AMD ROCm, Apple Silicon and CPU-only machines
are supported for inference. Training scripts need an NVIDIA GPU (6 GB is enough) with Unsloth.

---

## 📜 License

Distributed under the [MIT License](LICENSE).
