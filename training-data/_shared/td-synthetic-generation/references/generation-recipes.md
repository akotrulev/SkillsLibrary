# Generation recipes — prompts and skeletons

Templates for the synthesis engine. The SKILL.md holds the discipline; this holds the copy-paste. All use the Claude API (`ai-development/claude-api` for SDK mechanics, model ids, batching, caching).

## Seed grid

```python
axes = {
  "topic":     [...50+ topics...],
  "difficulty":["easy","medium","hard","expert"],
  "persona":   ["terse expert","patient tutor","skeptical reviewer"],
  "format":    ["direct answer","step-by-step","with a worked example"],
}
seeds = [dict(zip(axes, combo)) for combo in itertools.product(*axes.values())]
random.shuffle(seeds)   # vary the batch composition
```

## Self-instruct — new instructions from seeds

```
System: You write NEW, self-contained user instructions for a dataset. They must be
answerable without extra context, varied in topic and phrasing, and NOT duplicates of
the examples shown. Return a JSON array of 10 instruction strings.

User: Here are example instructions:
{5 random existing instructions}
Write 10 new ones in the same spirit but on different content. Vary difficulty and format.
```

Pool, near-dedup (`training-data:data-quality`), then generate responses in a second pass.

## Evol-instruct — deepen an instruction

```
System: Rewrite the given instruction to make it HARDER along the axis: {axis}.
Axes: add-constraints | deepen-reasoning | increase-steps | make-concrete | broaden-scope.
Keep it answerable and self-contained. Return only the rewritten instruction.

User: {instruction}
```

Evolve 1–3 rungs; keep each rung as its own example so the difficulty tail is populated.

## Grounded QA from a corpus

```
System: Using ONLY the passage below, write {n} question/answer pairs a student could be
tested on. Questions must be answerable from the passage alone; answers must be supported
by it verbatim or by direct paraphrase. Return JSON [{ "q":..., "a":..., "quote":... }].

User: {passage chunk}
```

`quote` is the supporting span — keep it for a groundedness check.

## Pairwise judge — with bias controls

```
System: You compare two assistant responses to a user prompt. Judge on: correctness,
grounding, completeness, instruction-following, safety. Ignore length and style unless they
affect those. Return JSON {"winner":"A"|"B"|"tie","reason":"one sentence"}.

User: PROMPT:
{prompt}
RESPONSE A:
{resp_1}
RESPONSE B:
{resp_2}
```

- Randomize which sampled response is A vs B per call (position bias).
- Judge each pair **twice with A/B swapped**; a winner that flips → `tie`.
- Pin model id + this exact prompt + a version tag into `meta.judge`.
- Calibrate on a human-labeled set first; report agreement before scaling.

## Batched generation skeleton

```python
# 1. Build requests from the seed grid (one per seed, cache the fixed system prefix).
# 2. Submit via the Message Batches API (ai-development/claude-api).
# 3. On completion, parse → attach envelope (id, source="synthetic:<model-id>",
#    batch_id, created_at) → write JSONL.
# 4. Route the batch through training-data:data-quality (near-dedup + decontaminate).
# 5. Judge/grade survivors with the pinned judge → drop below threshold, keep reasons.
```

## Cost worksheet

```
per_record_tokens ≈ prompt_in + few_shot_in + expected_out
gen_cost   = records × per_record_tokens × gen_price_per_token
judge_cost = records × judge_tokens × judge_price_per_token   # ×2 if pairwise-swap
total ≈ gen_cost + judge_cost      # prompt caching cuts the fixed-prefix portion sharply
```

Pull current per-model prices from `ai-development/claude-api` (`shared/models.md`). Put the estimate in front of the human before any batch over a few thousand records.
