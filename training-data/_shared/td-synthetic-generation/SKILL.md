---
name: synthetic-generation
description: Use when generating training data with a teacher model (the Claude API) — distillation, self-instruct/evol-instruct, self-critique, and preference-pair generation. Triggers: "generate SFT data with Claude", "synthesize instruction pairs", "distill from a teacher model", "make DPO pairs by sampling and judging", "evol-instruct harder prompts". Do NOT use for the record schema (`training-data:dataset-formats`), dedup/decontamination (`training-data:data-quality`), or API mechanics (`ai-development/claude-api`).
---

# Training Data — Synthetic Generation (cross-stage engine)

Producing training data with a teacher model rather than collecting it. This is the synthesis half of the domain (curation is the stage skills' collection paths); it applies to SFT, preference, and eval data alike. The engine is the same every time — **seed → expand → grade → dedup → format** — and the two failure modes are always the same: **collapse** (everything sounds identical because the sampling was greedy and the seeds were narrow) and **false quality** (the teacher's confident mistakes become the student's ground truth). Everything below exists to fight those two.

**Load `ai-development/claude-api` for the API mechanics** — model ids, the Messages API, structured output, streaming, batching, prompt caching, token counting. This skill owns the *data-generation discipline* on top of it; it does not restate the SDK. Use the latest capable model as the teacher (a stronger model than the one being trained — that is the point of distillation) and pin its exact id in every record's `source`.

## When to use

- Generating instruction/response (SFT) pairs from a topic list, a seed set, or a document corpus
- Expanding a small seed set into a large diverse one (self-instruct / evol-instruct)
- Producing preference pairs by sampling multiple responses and judging them
- Building rubric-graded or LLM-judge eval items
- Diversifying an existing set that has collapsed onto a few patterns

## When NOT to use

- The on-disk record shape → `training-data:dataset-formats`
- Dedup, decontamination, PII → `training-data:data-quality` (always run after generation)
- Collecting/cleaning real corpora → the stage skills
- Raw API usage questions → `ai-development/claude-api`

## The legal and honesty line — read first

- **Respect the teacher model's terms.** Anthropic's terms govern whether and how Claude output may be used to train another model; check them for the intended use (internal eval data, a research model, a competing commercial model are different cases) before generating at scale. Record the decision in the dataset card. This skill does not grant permission it cannot grant.
- **Synthetic data is `synthetic-review-required` by default**, not verified truth. Every synthetic record carries `source: "synthetic:<exact-model-id>"` and a license/flag that says a human has not confirmed it. The teacher's hallucinations, stale facts, and biases pass straight through — treat generated content as a *draft the model will imitate*, and gate factual domains (medical, legal, code that must run) behind verification, not vibes.

## The engine: seed → expand → grade → dedup → format

### 1. Seed — diversity is decided here, not later

A synthetic set is only as diverse as its seeds. Collapse starts with a seed list of ten topics. Build breadth *before* generating:

- **Enumerate axes, then cross them**: topic × difficulty × persona × format × language. A seed is a point in that grid, not a bare topic. 50 topics × 4 difficulties × 3 personas = 600 distinct seeds before any sampling variance.
- **Ground seeds in real material** where you can: sample chunks from a document corpus and generate questions *about them* (grounded QA is more useful and less hallucinated than free invention). This is the bridge to curation — the corpus is real, the QA is synthetic.
- **Rotate the system/instruction prompt** across the grid so the teacher isn't answering in one voice.

### 2. Expand — self-instruct and evol-instruct

- **Self-instruct**: from a handful of human-written seed instructions, ask the teacher for *new* instructions in the same spirit but different content, pool them, dedup, then generate responses. Feed a few random existing instructions as in-context examples each call so new ones diverge.
- **Evol-instruct**: take an instruction and ask the teacher to make it *harder* along a chosen axis — add constraints, deepen reasoning, increase steps, make it more concrete, or broaden scope. This manufactures the difficulty tail that flat generation never reaches. Evolve in steps; keep the intermediate rungs as their own examples.
- **Sample with temperature** (0.7–1.0) for the *content* you want varied; keep temperature low for the *response* where correctness matters. Never generate a whole set greedily — identical decoding is the fastest route to collapse.
- **Batch it.** Use the Message Batches API for large synthesis runs — it is cheaper and rate-limit-friendly; tag each batch with an id recorded in `source` so a bad batch is traceable and re-runnable (`ai-development/claude-api`).

### 3. Grade — the judge, pinned

Filtering generated data is where false quality is caught. An LLM judge is standard, but an *unpinned* judge silently drifts:

- **Pin the judge**: exact model id + exact prompt + version, recorded in `meta.judge`. Changing any of them changes the dataset; treat the judge prompt as versioned code.
- **Calibrate before trusting.** Grade a small human-labeled set with the judge and check agreement *before* running it on 100k records. A judge that agrees with humans 60% of the time is a coin flip with a costume.
- **Score against a rubric, not a vibe** — explicit criteria (correct? grounded? complete? follows the instruction? safe?), each scored, with a one-line reason kept in `meta.judge_reason` so a human can spot-audit. Reasons are also how you debug a filter that's dropping good data.
- **Guard against known LLM-judge biases**: position bias (randomize order in pairwise), length bias (longer ≠ better — control for it), self-preference (a judge favors its own family's style). For pairwise preference, swap and re-judge; a decision that flips on swap is a tie, not a preference.

### 4. Dedup and decontaminate — hand off, don't skip

Generation *always* produces near-duplicates (the teacher has favorite phrasings). Route every synthetic batch through `training-data:data-quality`: near-dedup at Jaccard 0.7, and decontaminate against your eval targets — **a teacher that has seen a benchmark will happily regenerate it**, so synthetic data is a prime contamination source. This is not optional cleanup; it is part of generation.

### 5. Format — the stage shape

Emit records in the stage's shape from `training-data:dataset-formats` (`messages` for SFT, `chosen`/`rejected` for preference, the eval item for eval), with the full envelope, `source: "synthetic:<model-id>"`, the batch id, and the judge metadata.

## Preference pairs by sampling and judging

The common way to build DPO data without human labelers:

1. Take a prompt (real or synthetic).
2. Sample **n responses at temperature** (n=4–8) — variance is the whole point; greedy gives you nothing to prefer between.
3. Judge them into a ranking with the pinned judge and rubric; the top becomes `chosen`, a lower one `rejected`. Pick a `rejected` that is *plausibly worse*, not garbage — the model learns the *margin*, and "great vs obvious trash" teaches nothing useful.
4. Record the `margin` and `judge_reason` in `meta`.
5. Optionally add **on-policy** rejects: sample from the *student* model being trained, so the pairs target its actual failure modes rather than the teacher's. Detail in `training-data:preference-data`.

## Constitutional / self-critique data

Generate a first response, then ask the teacher to critique it against a stated principle and revise. The (revised, original) pair is a preference pair; the critique itself is SFT signal for a critic. This produces alignment data without human red-teamers for every case — but the principles are the design, so state them explicitly and keep them in the card.

## Cost and scale control

- **Prompt-cache the fixed prefix** (the long system prompt, rubric, few-shot block) across a batch — it is the cheapest large win (`ai-development/claude-api` prompt caching).
- **Batch API** for anything over a few thousand calls.
- **Generate small, validate, then scale.** Produce 200, run them through dedup + judge + a human eyeball, tune the prompts, *then* generate 200k. Generating the full set first and discovering the prompt was subtly wrong is the expensive mistake.
- **Estimate before running**: tokens/record × records × price, both generation and judging. Put the estimate in front of the human before a large batch.

## Hard rules

- **Diversity is engineered at the seed stage** (crossed axes + grounding + prompt rotation + sampling temperature), never hoped for at the end.
- **Every synthetic record is `synthetic:<exact-model-id>` + batch id + `synthetic-review-required`.** It is a draft, not verified truth.
- **The judge is pinned and calibrated** against human labels before it is trusted at scale; its reasons are kept for audit.
- **Synthetic batches are deduped and decontaminated** through `training-data:data-quality` — the teacher is a contamination source.
- **Generate small → validate → scale.** Never generate the full set before validating the prompt on a sample.
- **Respect the teacher model's terms of use**, decided and recorded before generating at scale.

## References

- `references/generation-recipes.md` — self-instruct and evol-instruct prompt templates, the pairwise-judge prompt with bias controls, a batched-generation skeleton, and a cost-estimation worksheet.
