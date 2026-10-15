# Original website reference curriculum

Prepared September 16, 2026. **21 training records, from 3 independent websites.**
These are hand-authored React/TypeScript/CSS targets, not outputs from the local model.

## Contents

| Original site | Visual direction | Functional examples | Inspiration |
|---|---|---|---|
| Margin | Warm editorial paper, expressive serif, layered notes | Editable word counter, notes toggle, annual billing switch | [Ellipsus](https://ellipsus.com/#introduction) |
| Fieldwork | Forest/lime palette, offset headline blocks, dimensional data columns | Keyboard-operated analytics tabs, accessible chart table, disclosures | [Mode](https://mode.com) |
| Parallax | Ivory/copper, oversized typography, floating interface panels | Animation pause, accordion, project filters, local brief form | [Ventriloc](https://ventriloc.ca/en/) |

All section colors resolve through declared theme tokens, matching the runtime color gate. The token migration was checked by reconstructing each prior CSS file exactly; TSX behavior is unchanged.

The references inform high-level composition. Their code, text, logos, and image assets are not included.
All businesses, product data, and project studies are fictional and labeled accordingly.

- `source/`: 15 complete TSX/CSS section pairs, five per site.
- `train.jsonl`: 15 section-generation records, 3 synthetic envelope repairs, 3 synthetic behavior repairs.
- `verification/`: recorded browser checks tied to source SHA-256 hashes.
- `report.json`: exact counts, tokenizer hash and token measurements.
- Previews live at the repository's `examples/reference-curriculum/`.

Repair inputs contain deliberately introduced defects. Their assistant targets are the complete verified implementations. Synthetic repair observations are not actual model failures or benchmark results.

## Preview and rebuild

From the repository root:

```powershell
python data_pipeline/build_reference_curriculum.py
node node_modules/vite/bin/vite.js examples/reference-curriculum --host 127.0.0.1 --port 5183 --strictPort
```

Open http://127.0.0.1:5183/. Each site includes its global theme and five assembled sections.

After source changes, repeat browser/type checks and update the evidence with the new hash before publishing:

```powershell
python data_pipeline/build_reference_curriculum.py --publish
python -m unittest discover -s tests -p test_reference_curriculum.py
```

Publication fails if verification is stale, file envelopes do not round-trip through the actual agent parser, or a record exceeds its token budget. Source files remain the authority; generated previews and JSONL are rebuildable artifacts.

## RTX 4050 6GB strategy

Measured with the shipped tokenizer: **maximum target 1,495 tokens; maximum complete training record 7,846 tokens**, including the existing system prompt and repair context. No supervised answer is truncated.

Keep the existing 3B model and 4-bit QLoRA approach. The local training script already supports rank 16, batch size 1, gradient accumulation 4 and Unsloth gradient checkpointing. Use an 8,192-token context for these records. The earlier 8K pilot fit this laptop; this particular corpus has not yet been trained or memory-profiled. A model-serving process must release GPU memory before training.

Generate complete sections in separate turns, then compose the site. Allow at least 2,048 output tokens for these section examples and enough total context for the input; larger requests need further decomposition. Increasing the output ceiling alone does not teach better designs.

The dimensional artwork uses CSS perspective/transforms and gradients with motion preferences, rather than loading large 3D assets or a new rendering dependency. This teaches lightweight dimensional visuals, not arbitrary 3D asset generation. Browser rendering and model inference are separate workloads, although both can compete for laptop GPU resources.

## Training and evaluation discipline

This corpus is ready as an additional source for the next curated training mix. It has **not** been used to update or replace the served adapter. Training only on these 21 records risks memorization and loss of existing agent behavior; retain the broader component/repair corpus in the mix.

All sections and repairs from a site share `family_id`. The preparation utility now honors explicit family IDs so related sections cannot cross a newly created train/validation split. Preserve the existing `data/quality_candidate/validation.jsonl` and `data/eval/premium_sites.jsonl` holdouts; do not randomly split individual sections or use reference reconstruction as evidence of generalization.

An isolated candidate must beat the retained adapter on unseen briefs, complete file envelopes, TypeScript compilation, actual interactions, mobile overflow, and human visual preference before promotion. The earlier pilot failed protocol validation and was not promoted; these repair examples address that observed weakness without claiming to solve it.

## Verification scope

All three assembled sites passed TypeScript compilation. Desktop and 375px mobile views were inspected; checked pages had one H1, resolved fragment links, no mobile horizontal overflow, and no captured console errors. Browser checks covered the interactions listed in each evidence JSON. The form sends no data.

Reduced-motion rules exist in source, but browser preference emulation and a full screen-reader/cross-browser audit were not performed. These are reviewed teaching examples, not a professional-quality score for the model.

## Useful feedback

Review the three previews and identify the strongest and weakest sections. Specific feedback on typography, spacing, motion and artwork is more useful than multiplying lightly renamed templates. Further references from different industries, with permission to use any supplied assets, will help expand genuine layout diversity.
