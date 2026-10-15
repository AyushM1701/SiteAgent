# Reviewed website training sources

The admitted inputs for `data/full_site_training_v3` are named explicitly in its manifest:

- `diverse_v1.jsonl`: three original scored sites and observed repair turns.
- `forma_scroll_v2.jsonl`: the separately scored scroll revision and observed repair turn.
- `flattened_v2.jsonl`: complete single-pair site outputs whose desktop and mobile DOM and pixels match the scored source sites; see `evidence/flattened_v1/*/verification.json`.
- `contract_repairs_v1.jsonl`: compiler-observed JSX and validator-observed CSS repairs of the scored Paperkite site.

`flattened_v1.jsonl` is retained only as a source provenance record. Its user prompts contained a conflicting section-only instruction, so **do not train on it**. `flattened_v2.jsonl` corrects the prompts without changing the assistant source or rendered site.

Review scores describe the corresponding authored site visuals. They are not model-native scores or substitutes for the later two-person blinded A/B promotion review.
