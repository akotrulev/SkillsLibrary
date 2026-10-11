---
name: dataset-formats
description: Use when deciding how a training dataset is stored on disk — record schema, chat format, VLM image references, provenance/license fields, splits, and shard layout. Triggers: "what format should the SFT data be", "JSONL schema for a chat dataset", "how do I lay out train/val/test", "shard a pretraining corpus", "ShareGPT vs OpenAI messages format". Do NOT use for quality filtering (`training-data:data-quality`), synthesis (`training-data:synthetic-generation`), or engine-specific storage DDL (`data/<db>`).
---

# Training Data — Dataset Formats & Layout (cross-stage)

The on-disk contract every training dataset in this domain obeys: the record schema, the conversation format, how VLM examples reference images, the provenance/license fields that ride on every record, and how splits and shards are laid out. Stage skills (`training-data:pretraining-corpus`, `training-data:instruction-sft`, `training-data:preference-data`, `training-data:eval-sets`, `training-data:vision-language-data`) fill in *what* goes in a record; this skill fixes *how* it is stored so every downstream tool — the tokenizer, the trainer, the auditor — reads it the same way.

## When to use

- Deciding the record schema and file format before generating or curating any example
- Choosing a conversation format (OpenAI `messages` vs ShareGPT vs raw chat-template string)
- Laying out train / validation / test splits and sharding a large corpus
- Fixing the provenance, license, and PII fields that must exist on every record
- Deciding how VLM records reference images (path vs base64 vs URL) and where images live

## When NOT to use

- Deduplication, decontamination, quality filtering → `training-data:data-quality`
- Generating records with a teacher model → `training-data:synthetic-generation`
- Corpus collection / cleaning mechanics → `training-data:pretraining-corpus`
- Image-specific record content (bbox, OCR, VQA) → `training-data:vision-language-data`

## The one rule: JSONL, one example per line

**Every dataset in this domain is newline-delimited JSON (`.jsonl`), UTF-8, one complete example per line, no trailing commas, no wrapping array.** It streams without loading the whole file into memory, `wc -l` counts examples, `head`/`sed`/`shuf` slice it, and a corrupt line fails one example instead of the file. Parquet is the *export* target for very large pretraining corpora where columnar compression pays (note it in the dataset card); JSONL stays the authoring and review format. Never author a dataset as one giant JSON array.

## Record envelope — every record, every stage

Every record carries a payload plus a fixed metadata envelope. The payload shape is stage-specific; the envelope is universal:

```json
{
  "id": "sft-000123",
  "source": "synthetic:claude-distill" ,
  "license": "CC-BY-4.0",
  "created_at": "2026-08-18",
  "meta": { "topic": "sql-tuning", "difficulty": "medium", "lang": "en" }
}
```

| Field | Required | Purpose |
|---|---|---|
| `id` | yes | Stable, unique, prefix-by-stage (`sft-`, `pref-`, `pt-`, `eval-`, `vlm-`). Never reuse an id, never renumber on regeneration — it is how the auditor and decontamination track a record across rounds. |
| `source` | yes | Where it came from: `web:<domain>`, `human:<team>`, `synthetic:<teacher-model>`, `public:<dataset-name>`. Drives license and contamination reasoning. |
| `license` | yes | The license the *content* is usable under (`CC-BY-4.0`, `MIT`, `proprietary-internal`, `synthetic-review-required`). A record with no known license is a **finding**, not a default-to-permissive. |
| `created_at` | yes | ISO date. Lets a corpus be time-sliced and lets the auditor spot a stale generation batch. |
| `meta` | optional | Free-form tags used for balancing/coverage (topic, difficulty, language, persona, task type). |

The payload is one of the stage shapes below and lives at the top level beside the envelope (`messages`, `text`, `chosen`/`rejected`, etc.).

## Conversation format — the `messages` array

SFT, preference, and eval chat records use the **OpenAI `messages`** shape as the canonical authoring format. It is unambiguous, role-typed, and every trainer's chat-template step consumes it:

```json
{ "id": "sft-000123", "source": "synthetic:claude-distill", "license": "synthetic-review-required", "created_at": "2026-08-18",
  "messages": [
    { "role": "system", "content": "You are a terse SQL tutor." },
    { "role": "user", "content": "Why is my query doing a seq scan?" },
    { "role": "assistant", "content": "Because the predicate isn't SARGable..." }
  ] }
```

Rules:

- **Roles are `system` | `user` | `assistant` | `tool`.** Exactly one leading `system` message at most; roles alternate `user`/`assistant` after it; a multi-turn record ends on `assistant` (that is the target the model learns to produce).
- **ShareGPT (`conversations` with `from`/`value`) is an import format, not the authoring format.** Convert it to `messages` on ingest (`from: human → user`, `from: gpt → assistant`) so one shape flows downstream. Note the conversion in `source`.
- **Do not pre-apply the chat template.** Store structured `messages`; the trainer applies the model's own template (ChatML, Llama-3, Gemma, Qwen — they differ). A dataset with `<|im_start|>` baked into `content` is locked to one model and re-tokenizes wrong on another. The *only* exception is a raw-text pretraining corpus (below), which has no roles.
- **Tool-use traces** carry `tool_calls` on the assistant message and a following `role: "tool"` message with the result; keep the JSON of the call intact — see `training-data:instruction-sft`.
- **The `system` prompt is training signal, not decoration.** Decide deliberately whether it is fixed, varied, or absent, and record the choice in the dataset card — the model learns the distribution you show it.

## Pretraining record — raw text

Pretraining has no roles. One document per line:

```json
{ "id": "pt-0004821", "source": "web:example.org", "license": "CC-BY-4.0", "created_at": "2026-08-18", "text": "..." }
```

Keep documents whole (don't pre-chunk to context length — the trainer packs/truncates); strip nothing the model should see; record the exact cleaning applied in the card. Very large corpora shard and export to Parquet (below).

## Preference record — chosen / rejected

DPO/ORPO/KTO records share a prompt and two responses:

```json
{ "id": "pref-000045", "source": "synthetic:claude-judge", "license": "synthetic-review-required", "created_at": "2026-08-18",
  "prompt": [ { "role": "user", "content": "..." } ],
  "chosen":  [ { "role": "assistant", "content": "the better response" } ],
  "rejected":[ { "role": "assistant", "content": "the worse response" } ] }
```

`prompt` is a `messages` array (may include `system`); `chosen`/`rejected` are the *continuations* only, so the trainer can concatenate prompt+chosen and prompt+rejected. KTO (single response + a boolean label) uses `completion` + `label` instead — pick one shape per file, never mix. Detail lives in `training-data:preference-data`.

## VLM record — image references

Multimodal records put images *inside* the message content as typed parts, never as a bare string:

```json
{ "id": "vlm-000012", "source": "public:coco", "license": "CC-BY-4.0", "created_at": "2026-08-18",
  "messages": [
    { "role": "user", "content": [
        { "type": "image", "path": "images/000000391895.jpg" },
        { "type": "text", "text": "What is the person doing?" } ] },
    { "role": "assistant", "content": [ { "type": "text", "text": "Riding a motorcycle." } ] } ] }
```

- **Reference images by relative `path` into a sibling `images/` directory — not base64, not a remote URL.** Base64 bloats the JSONL 33% and makes it un-greppable; a URL rots and leaks reads to a third party at train time. Store the bytes once, reference by path. Base64 is an *export* concern only, produced at load time if a trainer demands it.
- **One image is one file, deduped by content hash** (see `training-data:data-quality`) — the same picture referenced by ten records is ten `path`s to one file, not ten copies.
- Image token placement, resolution, interleaving, bbox/OCR payloads → `training-data:vision-language-data`.

## Splits — train / validation / test

- **Three splits, split *before* any tuning decision, and split by a de-duplication key, not by row.** If near-duplicate documents land on both sides of the train/test line, the eval is contaminated and the numbers lie. Group by `source` document / near-dup cluster (from `training-data:data-quality`) and assign whole clusters to one split.
- Default ratios: **98 / 1 / 1** for large pretraining corpora, **90 / 5 / 5** for SFT/preference sets, or a fixed-size held-out test (e.g. 1–2k examples) when the set is small. State the actual counts in the card.
- **The test split is drawn once and frozen.** It is also the decontamination target: nothing in train may near-match anything in test/eval (that check is `training-data:data-quality`'s job, but the split boundary is defined here).
- File layout: `train.jsonl` / `val.jsonl` / `test.jsonl` per dataset, plus a `manifest.json` (below).

## On-disk layout

Datasets live under `datasets/<name>/` at the project root; the human-readable dataset card and any spec/audit `.md` live under `docs/datasets/`:

```
datasets/<name>/
  train.jsonl            # or train/shard-0000.jsonl … for large corpora
  val.jsonl
  test.jsonl
  images/                # VLM only — content-hashed image files
  manifest.json         # machine record: counts, splits, shard list, format version, hashes
docs/datasets/
  <name>-card.md        # the human dataset card (datasheet) — see below
```

**Sharding** (large corpora only): `train/shard-0000.jsonl`, `shard-0001.jsonl`, … at a fixed target size (256 MB–1 GB compressed, or ~100k–500k records) so downloads/reads parallelize and one bad shard is re-fetchable. List every shard + its record count and SHA-256 in `manifest.json`.

## The dataset card (datasheet) — required, not optional

Every dataset ships a `docs/datasets/<name>-card.md` before it is considered done. It is the "datasheet for datasets": what the set is, who/what made it, and its limits. Minimum sections:

- **What it is** — stage (pretraining/SFT/preference/eval), modality (text/VLM), intended use, one example record.
- **Provenance** — every `source` value with its count, license, and how it was obtained; the teacher model + prompt-batch id for synthetic portions.
- **Construction** — curation and synthesis steps, the exact quality filters and dedup/decontamination applied (link the `training-data:data-quality` run), split method and counts.
- **Composition** — coverage/balance table by `meta` (topic/difficulty/language/task), so skew is visible.
- **Limitations & risks** — known gaps, biases, PII-handling, license constraints on downstream use, and anything the synthetic portion could not be verified for.

An undocumented dataset is an unusable dataset six months later — the card is how the next person (and the trained model's evaluators) knows what the model actually saw.

## Hard rules

- **JSONL, one example per line, UTF-8.** No wrapping array. Parquet is export-only.
- **Every record has `id`, `source`, `license`, `created_at`.** A missing license is a finding.
- **Store structured `messages`; never bake the chat template into `content`.** (Pretraining raw text excepted.)
- **VLM images are referenced by relative path to a content-hashed file; never base64 in the JSONL, never a remote URL.**
- **Splits are drawn by dedup cluster before tuning and frozen; the test split is the decontamination target.**
- **Ids are stable and never reused across regenerations.**
- **No dataset is done without its card.**

## References

- `references/format-catalog.md` — full JSON schemas for each stage record, ShareGPT↔messages conversion, tool-call trace shape, and the `manifest.json` schema.
