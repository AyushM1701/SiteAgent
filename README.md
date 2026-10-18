# SiteAgent

SiteAgent is a local website builder powered by a small language model. You describe a site in
plain English; SiteAgent plans it, writes it as a React and TypeScript project, builds it, checks
it in a real browser, and shows a live preview you can inspect and edit. Everything runs on your
own machine with [Qwen3-4B](https://huggingface.co/Qwen/Qwen3-4B) - on an NVIDIA or AMD GPU, an
Apple Silicon Mac, or a CPU.

[![CI](https://github.com/AyushM1701/SiteAgent/actions/workflows/ci.yml/badge.svg)](https://github.com/AyushM1701/SiteAgent/actions/workflows/ci.yml)

## Features

- **Prompt to finished site.** Sections, copy, layout, art direction, photography, motion, a
  favicon, OpenGraph tags and a 404 page, generated as a Vite + React + TypeScript project you can
  download as a ZIP.
- **Checked before you see it.** Every site goes through TypeScript, a production build, a
  section contract, accessibility (contrast, focus, landmarks), motion rules and a headless
  browser run. Problems are repaired automatically where possible and reported where not.
- **Honest content.** Prices, products, people, testimonials and contact details appear only when
  you supply them; instructions and style words never leak into the copy.
- **Workbench.** Chat with the agent to refine a site; the workspace shows a live preview at real
  desktop, tablet and mobile widths, a code editor with a file tree, per-turn diffs with revert,
  persistent logs and a terminal. The inspector lets you click any element in the preview and ask
  the agent to change it.
- **Two writers.** The default design kit writes the code from the model's copy (fast); the
  fine-tuned native adapter lets the model write every section's code itself.

## Requirements

- Python 3.10 to 3.13
- [Node.js](https://nodejs.org) 18 or newer
- Git and about 15 GB of free disk space (the model is 8 GB)
- Optional: a GPU (see [Hardware](#hardware))

## Quick start

```bash
git clone https://github.com/AyushM1701/SiteAgent.git
cd SiteAgent
```

Install. The setup script creates a `.venv`, installs the right PyTorch build for your hardware,
builds the workbench UI, downloads Qwen3-4B and runs a health check.

```bash
bash scripts/setup.sh          # macOS, Linux, Git Bash
scripts\setup.bat              # Windows
```

Start the workbench and open <http://127.0.0.1:5000>:

```bash
bash scripts/run_web_ui.sh     # macOS, Linux, Git Bash
scripts\run_web_ui.bat         # Windows
```

The top bar shows **Loading model** while the model loads and **Ready** when you can send a prompt.
Check your setup at any time with:

```bash
python slm.py doctor
```

Setup options: `--cpu` (force CPU), `--skip-model` (download later with `python slm.py download`),
`--base Qwen/Qwen3-1.7B` (smaller model for low-memory machines),
`--adapter AyushM1701/siteagent-native-qwen3-4b` (also download the native adapter, about 130 MB).

## Hardware

`agent/hardware.py` detects the machine and picks the backend, precision and context length.

| Machine | How the model runs | Notes |
| --- | --- | --- |
| NVIDIA GPU, 6 GB VRAM or more | 4-bit (Unsloth or bitsandbytes) | Developed on a 6 GB RTX 4050, about 25 tokens/s |
| NVIDIA GPU without the 4-bit libraries | float16 on the GPU | Needs about 8 GB VRAM; used automatically as a fallback |
| AMD GPU on Linux (ROCm) | Transformers on the GPU | Unsloth is NVIDIA-only |
| Apple Silicon, 16 GB or more | float16 on Metal | |
| CPU only, 12 GB RAM or more | bfloat16 on the CPU | A few tokens/s; a kit-mode site takes about 5 minutes |
| Less memory | `--base Qwen/Qwen3-1.7B` | Kit mode only; the native adapter needs Qwen3-4B |

Override any choice with environment variables:

| Variable | Values | Purpose |
| --- | --- | --- |
| `SLM_DEVICE` | `cuda`, `mps`, `cpu` | Device to run on |
| `SLM_BACKEND` | `unsloth`, `transformers` | Loader |
| `SLM_LOAD_IN_4BIT` | `1`, `0` | 4-bit quantisation on CUDA |
| `SLM_CONTEXT_LENGTH` | e.g. `8192` | Context window |
| `MODEL_PATH` | path | Base model or adapter folder to load |
| `SITE_STRATEGY` | `kit`, `native` | Default site writer |

## How a site is built

1. **Plan.** The planner reads the request (an inline `Sections: a, b, c` or `Include: a, b, c`
   list is followed exactly), picks one of 12 contrast-checked art directions, and assigns
   subject-matched photography.
2. **Copy.** The model writes each section's copy as a small JSON object. Integrity filters drop
   invented facts, leaked instructions and style words.
3. **Code.** One of two writers turns copy into React and CSS:
   - **Design kit** (default, about 1-2 minutes per site on a 6 GB GPU). Deterministic renderers in
     `agent/site_kit/` for headers, heroes, menus, galleries, products and carts, FAQs, pricing,
     contact forms and footers, with a native motion system that respects reduced motion.
   - **Native** (about 20-40 minutes per site on a 6 GB GPU). The fine-tuned adapter writes every
     section's component and CSS against the kit's design tokens. A section is used only if it
     typechecks, keeps the approved copy exactly and keeps every behaviour the design system
     requires (scroll reveals, ARIA, image sources, links, handlers); otherwise the kit renders it.
4. **Verify.** The project is built and checked in a browser, then repaired if needed.

Choose the writer per request in the composer (*Advanced* > *Site code written by*), or start in
native mode with `scripts/run_web_ui.sh --native` after downloading the adapter:

```bash
python slm.py download --adapter AyushM1701/siteagent-native-qwen3-4b
```

On 36 held-out sections from business types never seen in training, native mode accepted:

| Model | Sections accepted | Fidelity to the design system |
| --- | --- | --- |
| Fine-tuned adapter ([model card](https://huggingface.co/AyushM1701/siteagent-native-qwen3-4b)) | 33 of 36 (92%) | 0.93 |
| Untuned Qwen3-4B | 2 of 36 (6%) | 0.28 |

Details are in [docs/NATIVE_SECTION_TRAINING.md](docs/NATIVE_SECTION_TRAINING.md).

## Writing good prompts

Describe the business, audience, sections, visual direction and any facts that must appear:

```
Saltmarsh Kitchen - a seasonal seafood restaurant in Whitstable. Sections: menu (Starters,
Mains, Desserts), our story, the team, FAQ, visit us. Deep navy and brass tones, gentle scroll
reveals. Do not mention opening hours. Email table@saltmarshkitchen.co.uk.
```

- Name the sections you want; categories in brackets become tabs or groups.
- Supply products with prices (`Sourdough loaf 6 GBP`) to get a shop with a cart.
- Exclusions such as "Do not show testimonials" are respected.
- Follow up in the chat ("make the hero darker", "add a pricing section"), or pick an element with
  *Inspect* and choose *Edit with AI*.

## Training your own adapter

Training needs an NVIDIA GPU with Unsloth (`pip install -r requirements-gpu.txt`); 6 GB is enough.

```bash
python scripts/build_native_section_data.py generate --per-family 5    # copy from the base model (~2 h)
python scripts/build_native_section_data.py assemble                    # train/validation rows
python training/train_native_sections.py                                # QLoRA, ~4-5 h on 6 GB
python scripts/eval_native_sections.py --model models/<adapter> --out runs/eval.json
python scripts/publish_adapter.py models/<adapter> --repo <your-name>/<repo>   # share on Hugging Face
```

Business families listed in `HOLDOUT_FAMILIES` never reach training and are used for validation.

## Project layout

```
agent/              Agent runtime: planner, design kit (site_kit/), native authoring, validators, hardware detection
server/             Flask workbench server, preview manager, project WebSocket, PTY shell
frontend/           Workbench UI source (React, Vite); builds into web_ui_static/
web_ui_static/      Compiled workbench UI served by the server
training/           QLoRA trainers (native sections, legacy SFT/DPO) and preflight checks
scripts/            Setup, doctor, model download/publish, data building, evaluation
data_pipeline/      Brief bank for native training and legacy trajectory tooling
evaluation/         Motion, 3D and visual scoring used by the validators
data/               Datasets and evaluation sets
examples/           Reference sites used by the data pipeline
tests/              Python test suite (pytest); frontend tests live in frontend/tests
docs/               Design notes and generated source export
```

Model weights (`base-model/`, `models/`), generated sites (`generated_components/`), sessions and
runs are created locally and ignored by git.

## Commands

| Command | Purpose |
| --- | --- |
| `python slm.py setup` | Install everything for this machine |
| `python slm.py doctor` | Check hardware, dependencies and models, and print fixes |
| `python slm.py download` | Download Qwen3-4B and, with `--adapter`, a native adapter |
| `python slm.py serve` | Start the workbench on port 5000 |
| `python slm.py train` | Legacy QLoRA SFT trainer |
| `python slm.py evaluate` | Legacy component benchmark |

## Testing

```bash
python -m pytest -q --ignore=tests/e2e     # Python suite
npm --prefix frontend test                 # workbench UI tests
npm --prefix frontend run typecheck
```

Tests that need the downloaded model or local training runs skip themselves with a reason. CI runs
the suite on Ubuntu without a GPU on every push.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| Top bar stays on *Loading model* | Check the server console and run `python slm.py doctor` |
| CUDA out of memory | Close other GPU apps, set `SLM_CONTEXT_LENGTH=4096`, or `SLM_DEVICE=cpu` |
| `bitsandbytes` or `unsloth` failed to install | The loader falls back to float16 Transformers (about 8 GB VRAM) |
| Preview says the build failed | The panel shows the error; fix the file in the Code tab or choose *Rebuild preview* |
| Browser checks are skipped | `python -m playwright install chromium` |
| The workbench page is blank | `npm --prefix frontend ci && npm --prefix frontend run build` |

## License

MIT, see [LICENSE](LICENSE). Qwen3-4B is released by Alibaba Cloud under the Apache 2.0 license.
