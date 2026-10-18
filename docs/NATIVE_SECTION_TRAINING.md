# Native section authoring

In the default **kit** strategy the model writes each section's copy as JSON and the
design kit renders the React/CSS. In the **native** strategy the model writes the copy
*and then each section's code itself*. The kit still plans the site (sections, theme,
photos) and supplies the shared design system (`src/App.css` tokens and layout classes,
fonts, page shell).

## How a native section is accepted

For every section the model gets `agent/site_kit/native.py:native_messages` — the
design spec (kind, theme mode, tint, reveal, store) plus the approved content JSON —
and replies with `src/components/<Name>.tsx` and `.css`. The reply is used only if

1. both files are present with the right paths and the component is exported;
2. it imports nothing but `react`, `react-dom` and its own CSS;
3. the repo's parser preflight passes; and
4. its `const DATA` object is **exactly** the approved content (no rewritten,
   dropped or invented copy).

Otherwise the model gets one retry, then the kit renders that section and the result
lists it under `native_code_fallbacks`. The whole site then goes through the normal
project gates (typecheck, build, contract, accessibility, motion, runtime).

## Data and training

| Step | Command |
| --- | --- |
| Generate copy with the base model (resumable) | `python scripts/build_native_section_data.py generate --per-family 5` |
| Assemble train/validation rows | `python scripts/build_native_section_data.py assemble` |
| Fine-tune (QLoRA, RTX 4050 profile) | `python training/train_native_sections.py` |
| Section-level evaluation | `python scripts/eval_native_sections.py --model <path> --out <report.json>` |
| Full-site evaluation (server running) | `python scripts/eval_native_sites.py --strategy native --out <report.json>` |

* Briefs come from `data_pipeline/native_site_prompts.py`: 40 business families,
  varied phrasing, products, menus, pricing tiers, exclusions and art direction.
  Briefs the planner misreads are skipped rather than trained on.
* Families in `HOLDOUT_FAMILIES` never reach training; they form the validation
  split and the evaluation briefs.
* Each site is rendered with its own theme and one alternative theme, so the same
  copy teaches different design flags.
* About a quarter of rows are content rows (the kit content prompt → the model's
  own usable JSON) so the adapter keeps its copy-writing behaviour.

## Running the workbench with the adapter

The recommended adapter is published as [`AyushM1701/siteagent-native-qwen3-4b`](https://huggingface.co/AyushM1701/siteagent-native-qwen3-4b)
(`python slm.py download --adapter AyushM1701/siteagent-native-qwen3-4b`; locally `models/qwen3-siteagent-native-sections-r16-v2`)
(92% of held-out sections accepted vs 6% for the base model; see `runs/native_sections/RESULTS.md`).

Use the `workbench-native` launch configuration (or set `MODEL_PATH` to the adapter
directory and `SITE_STRATEGY=native`). In the composer, *Advanced → Site code written by*
switches between **Design kit (fast)** and **The model (native)** per request.

Native generation is slower than the kit: the model writes every section's code
(several thousand tokens for the header and hero).
