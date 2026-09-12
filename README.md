# ReactAgent SLM 🚀

> **Autonomous Small Language Model (SLM) for React, TypeScript, and Modern CSS.**  
> Fine-tuned from `Qwen/Qwen2.5-Coder-3B-Instruct` to generate, test, and self-correct production-grade web components and complete websites. Runs locally on consumer GPUs (e.g., 6GB RTX 4050).

---

## ⚡ Quick Start

### 1. Setup Environment & Base Weights
Clone the repository and run the setup script:
```bash
# POSIX / Linux / macOS / Git Bash
bash scripts/setup.sh

# Windows Command Prompt
scripts\setup.bat
```
*Installs Python and npm dependencies, and downloads `Qwen/Qwen2.5-Coder-3B-Instruct` base weights into `./base-model`.*

### 2. Launch the Web Workbench (One Command)
```bash
# POSIX / Linux / macOS / Git Bash
bash scripts/run_web_ui.sh

# Windows Command Prompt
scripts\run_web_ui.bat

# Or via unified CLI:
python slm.py serve
```
*Spawns the Flask SSE backend and isolated PTY terminal server, and automatically opens `http://127.0.0.1:5000` in your browser.*

### 3. Full Training Pipeline (One Command)
To rebuild datasets and retrain from scratch:
```bash
# POSIX / Linux / macOS / Git Bash
bash scripts/train_all.sh

# Windows Command Prompt
scripts\train_all.bat

# Or via unified CLI:
python slm.py pipeline
```
*Merges all trajectory datasets → validates syntax and types through Vitest & tsc → trains with QLoRA SFT.*

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

## 🛠️ Unified CLI Reference (`slm.py`)

The root CLI provides a unified interface across all workflows:

| Command | Description |
|---|---|
| `python slm.py pipeline` | Full end-to-end training pipeline (merge → validate → train SFT) |
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

- **Inference**: NVIDIA GPU with >= 6GB VRAM (e.g., RTX 4050 Laptop GPU, RTX 3060, or better). Runs comfortably in 4-bit/8-bit QLoRA.
- **Training**: 6GB VRAM (QLoRA with Unsloth gradient checkpointing, `max_seq_length=9216`, batch size 1 with gradient accumulation).
- **RAM**: 16GB+ recommended.
- **OS**: Windows 10/11 or Linux / macOS.

---

## 📜 License

Distributed under the [MIT License](LICENSE).
