---
name: dataset-formats
description: Use when deciding how a training dataset is stored (record schema, chat format, provenance, splits, shards). Triggers "JSONL schema for a chat dataset". Not for quality filtering (data-quality).
disable-model-invocation: true
---

# Training Data — Dataset Formats & Layout (cross-stage)

The on-disk contract every training dataset in this domain obeys: the record schema, the conversation format, how splits and shards are laid out, the manifest and the card. Stage skills (`training-data:pretraining-corpus`, `training-data:instruction-sft`, `training-data:preference-data`, `training-data:eval-sets`, `training-data:vision-language-data`) fill in *what* goes in a record; this skill fixes *how* it is stored so every downstream tool — the tokenizer, the trainer, the auditor — reads it the same way.

The record rules are the training-data rule files: `datasets.md` (records, envelope, splits, layout) and `dataset-docs.md` (the card). Read the project's copy in `.claude/rules/training-data/`, or the plugin's in `training-data/skills/rules/` when the project has not installed them (`/training-data:rules` does). Where they and this skill disagree, the rule files win.

## JSONL, one example per line

Every dataset is `.jsonl` (file rules: `datasets.md` "Files"). It streams without loading the whole file into memory, `wc -l` counts examples, `head`/`sed`/`shuf` slice it, and a corrupt line fails one example instead of the file. Parquet is the *export* target for very large pretraining corpora where columnar compression pays (note it in the dataset card); JSONL stays the authoring and review format.

## Record envelope — every record, every stage

Every record carries a payload plus the fixed metadata envelope. The payload shape is stage-specific; the envelope is universal (each field's rule is `datasets.md` "Envelope and provenance"):

```json
{
  "id": "sft-000123",
  "source": "synthetic:claude-sonnet-5-5",
  "license": "synthetic-review-required",
  "created_at": "2026-08-18",
  "meta": { "topic": "sql-tuning", "difficulty": "medium", "lang": "en" }
}
```

The payload lives at the top level beside the envelope (`messages`, `text`, `chosen`/`rejected`, etc.).

## Conversation format — the `messages` array

SFT, preference and eval chat records use the **OpenAI `messages`** shape as the canonical authoring format: unambiguous, role-typed, and every trainer's chat-template step consumes it. The trainer applies the model's own template, because they differ (ChatML, Llama-3, Gemma, Qwen): a dataset with `<|im_start|>` baked into `content` is locked to one model and re-tokenizes wrong on another. A raw-text pretraining corpus, which has no roles, is the one exception.

```json
{ "id": "sft-000123", "source": "synthetic:claude-sonnet-5-5", "license": "synthetic-review-required", "created_at": "2026-08-18",
  "messages": [
    { "role": "system", "content": "You are a terse SQL tutor." },
    { "role": "user", "content": "Why is my query doing a seq scan?" },
    { "role": "assistant", "content": "Because the predicate isn't SARGable..." }
  ] }
```

## Record shapes per stage

The full schemas are in `references/format-catalog.md`. Stage → read the catalog section:

| Stage | Catalog section |
|---|---|
| SFT with tool calls | "SFT — tool use" |
| Preference (DPO / ORPO) | "Preference — DPO / ORPO" |
| Preference (KTO) | "Preference — KTO" |
| Pretraining | "Pretraining — raw text" |
| Eval | "Eval — graded item" |
| VLM (images by `path` into `images/`, never base64 or a URL) | "VLM — multimodal chat"; image token placement and bbox/OCR payloads in `training-data:vision-language-data` |
| A ShareGPT import | "ShareGPT → messages conversion" |

## Splits — train / validation / test

Splits follow `datasets.md` "Quality, splits and contamination" (by near-dup cluster, drawn before any tuning decision), and `eval-sets.md` freezes the test split. Default ratios: **98 / 1 / 1** for large pretraining corpora, **90 / 5 / 5** for SFT/preference sets, or a fixed-size held-out test (e.g. 1–2k examples) when the set is small. State the actual counts in the card. The files are `train.jsonl` / `val.jsonl` / `test.jsonl` plus a `manifest.json`.

## On-disk layout

Datasets live under `datasets/<name>/` at the project root; the human-readable dataset card and any spec/audit `.md` live under `docs/datasets/`:

```
datasets/<name>/
  train.jsonl
  val.jsonl
  test.jsonl
  images/                # VLM only — content-hashed image files
  manifest.json         # machine record: counts, splits, shard list, format version, hashes
docs/datasets/
  <name>-card.md        # the human dataset card (datasheet)
```

**Sharding** (large corpora only): `train/shard-0000.jsonl`, `shard-0001.jsonl`, … at a fixed target size (256 MB–1 GB compressed, or ~100k–500k records) so downloads/reads parallelize and one bad shard is re-fetchable. List every shard + its record count and SHA-256 in `manifest.json`.

## The dataset card (datasheet)

Every dataset ships `docs/datasets/<name>-card.md` before it is done, with the sections and recorded decisions of `dataset-docs.md`. It is how the next person, and the trained model's evaluators, know what the model actually saw.

## References

- `references/format-catalog.md` — full JSON schemas for each stage record, ShareGPT↔messages conversion, tool-call trace shape, and the `manifest.json` schema.
