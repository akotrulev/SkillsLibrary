# Format catalog — full record schemas

Concrete JSON schemas and conversions for every record shape the domain uses. The SKILL.md holds the rules; this holds the copy-paste shapes.

## Envelope (all records)

```json
{
  "id":         "string, unique, stage-prefixed (sft- pref- pt- eval- vlm-)",
  "source":     "web:<domain> | human:<team> | synthetic:<model> | public:<dataset>",
  "license":    "SPDX id | proprietary-internal | synthetic-review-required",
  "created_at": "YYYY-MM-DD",
  "meta":       { "topic": "…", "difficulty": "easy|medium|hard", "lang": "en", "task": "…" }
}
```

## SFT — chat / instruction

```json
{ "...envelope": "…",
  "messages": [
    { "role": "system",    "content": "string (optional, at most one, leading)" },
    { "role": "user",      "content": "string" },
    { "role": "assistant", "content": "string (the learned target)" }
  ] }
```

Multi-turn: repeat `user`/`assistant` pairs; the record must end on `assistant`.

## SFT — tool use

```json
{ "...envelope": "…",
  "tools": [ { "name": "get_weather", "description": "…", "parameters": { "type": "object", "properties": { "city": { "type": "string" } }, "required": ["city"] } } ],
  "messages": [
    { "role": "user", "content": "Weather in Sofia?" },
    { "role": "assistant", "content": null,
      "tool_calls": [ { "id": "call_1", "type": "function", "function": { "name": "get_weather", "arguments": "{\"city\":\"Sofia\"}" } } ] },
    { "role": "tool", "tool_call_id": "call_1", "content": "{\"temp_c\":24}" },
    { "role": "assistant", "content": "It's 24°C in Sofia." }
  ] }
```

Keep `arguments` as a JSON *string* (matches the API wire format). The final `assistant` message is the target; the tool result is context.

## Preference — DPO / ORPO

```json
{ "...envelope": "…",
  "prompt":   [ { "role": "user", "content": "…" } ],
  "chosen":   [ { "role": "assistant", "content": "better" } ],
  "rejected": [ { "role": "assistant", "content": "worse" } ],
  "meta": { "margin": 2, "judge": "claude", "judge_reason": "chosen is grounded; rejected hallucinates a flag" } }
```

## Preference — KTO (single response + label)

```json
{ "...envelope": "…",
  "prompt":     [ { "role": "user", "content": "…" } ],
  "completion": [ { "role": "assistant", "content": "…" } ],
  "label": true }
```

One preference file uses one shape (DPO-style *or* KTO-style), never both.

## Pretraining — raw text

```json
{ "...envelope": "…", "text": "one whole document, uncut, cleaned per the card" }
```

## Eval — graded item

```json
{ "...envelope": "…",
  "messages": [ { "role": "user", "content": "the question" } ],
  "reference": "gold answer OR rubric id",
  "eval": { "type": "exact_match | multiple_choice | rubric | llm_judge", "choices": ["A","B","C","D"], "answer": "B" },
  "canary": "OPTIONAL unique GUID string to detect train-set leakage" }
```

## VLM — multimodal chat

```json
{ "...envelope": "…",
  "messages": [
    { "role": "user", "content": [
        { "type": "image", "path": "images/<sha256>.jpg", "width": 640, "height": 480 },
        { "type": "text",  "text": "question" } ] },
    { "role": "assistant", "content": [ { "type": "text", "text": "answer" } ] } ],
  "meta": { "task": "vqa | caption | ocr | grounding", "n_images": 1 } }
```

Grounding/bbox and OCR payload extensions are defined in `training-data:vision-language-data`.

## ShareGPT → messages conversion

| ShareGPT `from` | messages `role` |
|---|---|
| `system` | `system` |
| `human` | `user` |
| `gpt` / `assistant` / `bard` | `assistant` |
| `tool` / `observation` | `tool` |

```
{"conversations":[{"from":"human","value":"hi"},{"from":"gpt","value":"hello"}]}
→
{"messages":[{"role":"user","content":"hi"},{"role":"assistant","content":"hello"}]}
```

Record `source: "public:<name> (sharegpt→messages)"` so the conversion is auditable.

## manifest.json

```json
{
  "name": "sql-tutor-sft",
  "format_version": "1.0",
  "stage": "sft",
  "modality": "text",
  "splits": {
    "train": { "files": ["train.jsonl"], "records": 42000 },
    "val":   { "files": ["val.jsonl"],   "records": 2200 },
    "test":  { "files": ["test.jsonl"],  "records": 2200 }
  },
  "shards": [ { "file": "train/shard-0000.jsonl", "records": 100000, "sha256": "…" } ],
  "images_dir": "images/",
  "created_at": "2026-08-18",
  "card": "docs/datasets/sql-tutor-sft-card.md"
}
```
