---
name: instruction-sft
description: Use when building supervised fine-tuning (SFT) data for a small LLM — single/multi-turn chat, instruction/response pairs, tool-use traces, and system prompts. Triggers: "build an SFT dataset", "make instruction-tuning data", "multi-turn chat data for fine-tuning", "tool-use / function-calling training traces", "convert our support logs into SFT data". Do NOT use for pretraining text (`training-data:pretraining-corpus`), preference/DPO data (`training-data:preference-data`), or eval sets (`training-data:eval-sets`).
---

# Training Data — Instruction / SFT

The data that turns a base model into one that follows instructions and holds a conversation. SFT quality beats SFT quantity by a wide margin for small models — **a few thousand excellent, diverse, correctly-formatted examples outperform a hundred thousand mediocre ones** (the LIMA result). This skill owns instruction/chat data end-to-end: task taxonomy → sourcing (curate and/or synthesize) → formatting → quality gate → split. It leans on `training-data:synthetic-generation` for the teacher-model path, `training-data:data-quality` for the gate, and `training-data:dataset-formats` for the `messages` shape.

## When to use

- Building an instruction-tuning / chat SFT set for a small model
- Curating real conversations (support logs, docs Q&A, existing transcripts) into training shape
- Synthesizing instruction/response pairs with a teacher model
- Creating tool-use / function-calling training traces
- Designing the system-prompt distribution the model will learn

## When NOT to use

- Raw pretraining text → `training-data:pretraining-corpus`
- chosen/rejected preference data → `training-data:preference-data`
- Benchmarks / held-out eval → `training-data:eval-sets`
- Multimodal instruction data → `training-data:vision-language-data`

## Start from the task taxonomy, not the data you happen to have

An SFT set teaches a *distribution of tasks*. Decide that distribution first, then fill it — otherwise you tune a model that is great at the three things your logs happened to contain and helpless at everything else. Enumerate the capabilities the model must have and target a coverage per bucket:

- open QA · closed/grounded QA · summarization · rewriting/editing · classification/extraction · reasoning/math · code (write/explain/fix) · multi-turn dialogue · instruction-following with constraints · refusal/safety · tool use.

Weight to the product (a support bot needs dialogue + grounded QA + refusal; a coding model needs code + reasoning). Track coverage with the `meta.task` tag (`training-data:dataset-formats`) and report the composition table in the card. **Balance is a first-class requirement, not an afterthought** — a set that is 60% one task produces a one-task model.

## Two sourcing paths, usually blended

### Curate real data

Real conversations are gold — they carry genuine user phrasing and real tasks. Turn them into SFT shape:

- **Logs / transcripts** → `messages`, cleaned of PII (`training-data:data-quality`), with the good assistant turn as the target. Drop or fix turns where the real answer was wrong — the model imitates the target verbatim.
- **Docs / FAQ / tickets** → grounded QA pairs (question + the doc-supported answer). This is the most useful curated source for a domain model.
- **Public SFT sets** (OpenHermes, Tulu, Dolly, OASST, No Robots, code-instruct sets) — convert to `messages` (`training-data:dataset-formats`), keep provenance, and **decontaminate against your evals** (public sets are frequently contaminated).

### Synthesize with a teacher

For coverage the real data doesn't reach, generate it (`training-data:synthetic-generation`): seed by crossed axes, expand with self-instruct/evol-instruct, ground QA in your corpus, grade with a pinned judge. Flag every synthetic record `synthetic-review-required`. Grounded synthesis (QA about *your* documents) is both more useful and less hallucinated than free invention.

The strongest small-model SFT sets are **blended**: real data for authentic distribution, synthetic for coverage and difficulty tail.

## Formatting — where SFT sets quietly break

- **Store structured `messages`; never bake the chat template into `content`** (`training-data:dataset-formats`). The trainer applies the model's own template.
- **Only the assistant turn(s) are the learning target.** Confirm the trainer masks the loss on system/user tokens (train on completions only) — training on the user's turn teaches the model to write *questions*. This is a config point but the data must be shaped for it (clean role boundaries).
- **Multi-turn records end on `assistant`** and keep the full prior context; don't flatten a conversation into disconnected single turns if the task is dialogue.
- **The system prompt is a distribution you choose.** Fixed (one persona), varied (many personas — improves robustness), or absent — decide deliberately and record it. If production always sends a specific system prompt, train with it.

## Tool-use traces

Function-calling data needs the full trace intact (`training-data:dataset-formats` catalog): `tools` schema → user turn → assistant `tool_calls` (arguments as a JSON string) → `role: "tool"` result → final assistant answer. Rules:

- **The tool call must be valid against the schema** — wrong argument names or types teach broken calling. Validate every trace's `arguments` against its `tools` JSON Schema before keeping it.
- Include **negative cases**: when *not* to call a tool, and how to recover from a tool error (a `tool` message carrying an error, then a graceful assistant response). A model trained only on happy-path calls hallucinates calls and can't handle failures.
- Keep multi-tool and multi-step traces if the product needs them; synthesize these with a teacher, they rarely exist in logs.

## Quality gate

Route every SFT record through `training-data:data-quality`: PII scrub, near-dedup (Jaccard 0.7 — paraphrase is the duplication here), and decontamination against evals. Then an **SFT-specific content check**:

- The assistant answer actually *follows the instruction* and is correct/grounded (LLM grade against a rubric, judge pinned — `training-data:synthetic-generation`).
- No truncation, no leaked template tokens, no "As an AI language model" boilerplate unless intended.
- Length sanity — a set of one-word answers teaches terseness; a set of essays teaches padding.
- Keep dropped records with reasons.

## Split

90/5/5 or a fixed held-out test, split by dedup cluster, frozen (`training-data:dataset-formats`). The test split doubles as an instruction-following eval — hand its shape to `training-data:eval-sets` if you want scored metrics.

## Hard rules

- **Coverage before volume.** Design the task distribution first; report the composition table. A few thousand excellent diverse examples beat a hundred thousand mediocre ones.
- **Only the assistant turn is the target** — clean role boundaries so the trainer can mask user/system tokens.
- **Structured `messages`, never a pre-applied chat template.**
- **Tool-call arguments validate against the tool schema**; include not-call and error-recovery cases.
- **Real + synthetic blended**, every synthetic record flagged `synthetic-review-required`.
- **Decontaminate against evals** (public SFT sets especially) before shipping.

## References

- `references/sft-recipes.md` — log→messages conversion, the grounded-QA-from-docs pattern, a tool-trace validator, and the task-coverage checklist with target weights.
