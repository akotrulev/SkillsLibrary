---
paths:
  - "**/datasets/**/*.jsonl"
  - "**/datasets/**/manifest.json"
---

<!-- training-data rules v1 (2026-11-03): core. Installed by /training-data:rules; edit the paths above to where this project keeps its datasets, re-run to compare with the plugin's copy. -->

# Training dataset standards (LLM / VLM: pretraining, SFT, preference, eval)

Apply these to every dataset file you write, edit, generate or review. The tag after a rule is the severity a review reports: **blocker** breaks the trainer, leaks a secret or personal data, or makes the eval numbers meaningless; **major** is a correctness or provenance problem; **minor** is a convention; **nit** is preference. The eval-split rules and the dataset card are separate files that load with those files.

**The dataset wins.** Where this project's datasets consistently do something another way (id prefixes, `source` vocabulary, split ratios, layout), follow them and do not flag it. Before writing, read the dataset's `manifest.json` (`format_version`, stage, modality, splits), its card and a sample of records, and know the target model's tokenizer: token counts and budgets are counted with it, never in words.

## Files

- JSONL: UTF-8, one complete example per line, no wrapping array, no trailing commas. Parquet is an export of a large corpus, never the authoring format. *blocker for a line that does not parse; major otherwise*
- One record shape per file: pretraining `text`; chat `messages`; preference `prompt` + `chosen`/`rejected` (DPO) or `prompt` + `completion` + `label` (KTO), never both. *major*
- After any edit the whole file still parses, and `manifest.json` still matches the files: per-split record counts, every shard with its record count and SHA-256, the card path. *major*

## Envelope and provenance

- Every record has `id`, `source`, `license` and `created_at` (ISO date); `meta` carries the balancing tags (topic, difficulty, lang, task). *major*
- `id` is unique, stage-prefixed (`pt-`, `sft-`, `pref-`, `eval-`, `vlm-`) and stable: never reused, never renumbered on regeneration. *major*
- `source` is `web:<domain>`, `human:<team>`, `public:<dataset>` or `synthetic:<exact-model-id>`; an import conversion is noted in it (`public:<name> (sharegpt→messages)`). *minor*
- A record with no known license is a finding, never defaulted to a permissive one. *major*
- A synthetic record carries `synthetic:<exact-model-id>`, its batch id and `license: "synthetic-review-required"` until a human verifies it; it is never relabelled human or verified. *major*
- A judge-graded record keeps the pinned judge (model id, prompt and version) in `meta.judge` and its one-line `meta.judge_reason`. *minor*

## Chat, tool and preference records

- Roles are `system` | `user` | `assistant` | `tool`: at most one leading `system`, then `user`/`assistant` alternate, and the record ends on `assistant`. *major*
- Structured `messages`, never a pre-applied chat template (`<|im_start|>`, `[INST]`) inside `content`. *major*
- ShareGPT (`conversations` / `from` / `value`) is converted to `messages` on ingest, never authored. *minor*
- A tool call is `tool_calls` on the assistant message, `arguments` a JSON string that validates against the record's tool schema, followed by a `role: "tool"` result; the set includes not-call and error-recovery cases. *major*
- Preference `prompt` is a `messages` array and `chosen`/`rejected` are the continuations only. `rejected` is plausibly worse, not garbage; a judge decision that flips when the order is swapped is a tie and is dropped, never labelled. *major*

## Pretraining and VLM records

- Pretraining: one whole document per line, not pre-chunked to context length. *minor*
- An image is a typed content part whose relative `path` points into the dataset's `images/`, one content-hashed file per image, and the file loads; never base64 in the JSONL, never a remote URL. *major*
- Images are deduped by content and perceptual hash and decontaminated against eval images, not only the text. Image EXIF/GPS is stripped, image licenses are tracked apart from caption licenses, and grounding uses the one coordinate convention the card states. *major*

## Quality, splits and contamination

- Splits are train / val / test, drawn by near-dup cluster (never by row) before any tuning decision; every member of a cluster sits in one split. *major*
- Nothing in train near-matches the test split or any named eval target (13-gram overlap, or MinHash Jaccard ≥ 0.7). Decontamination runs last, on what ships, and again after every change to train; a dataset never checked against its eval targets is not shippable. *blocker*
- Synthetic batches are deduped and decontaminated like curated data: a teacher regenerates the benchmarks it has seen. *major*
- No secret or key survives: drop the record, never mask it. PII is removed by the redaction strategy the card records (drop, mask or pseudonymize). *blocker*
- Dropped records are kept in `rejected/` with their reason until the dataset is validated. *minor*
- Composition is measured from the `meta` tags; no topic, template, persona or `source` dominates without the card saying so. *major*
- No dataset is done without its card (`docs/datasets/<name>-card.md`) and a valid `manifest.json`. *major*
