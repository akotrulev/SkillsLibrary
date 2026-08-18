---
name: td-preference-data
description: Use when building preference / alignment data for a small LLM — chosen/rejected pairs for DPO/ORPO, single-response labels for KTO, ranking data, on-policy sampling against the student model, and constitutional self-critique pairs — with judge-pinning, margin control, and bias guards. Triggers: "make DPO pairs", "build preference data", "chosen/rejected dataset", "on-policy preference data for my model", "constitutional AI self-critique pairs". Do NOT use for SFT/instruction data (`td-instruction-sft`), eval sets (`td-eval-sets`), or the judge/generation mechanics themselves (`td-synthetic-generation`).
---

# Training Data — Preference / Alignment

The data that tunes a model's *behavior* after SFT — which of two responses is better, so DPO/ORPO/KTO can push the model toward the preferred one. Preference data has one job and one failure mode: it must encode a **real, consistent preference with a meaningful margin**, and it fails when the two responses differ by noise (the model learns nothing) or when the "preferred" one isn't actually better (the model learns the wrong thing). This skill owns pair construction; it uses `td-synthetic-generation` for sampling+judging and `td-dataset-formats` for the `chosen`/`rejected` shape.

## When to use

- Building chosen/rejected pairs for DPO or ORPO
- Building single-response + label data for KTO
- Producing ranking data (n responses ordered)
- Generating on-policy preference data against the model you are training
- Constitutional / self-critique preference pairs (revise-against-a-principle)

## When NOT to use

- Instruction/SFT data → `td-instruction-sft`
- Held-out eval / benchmarks → `td-eval-sets`
- The pairwise-judge prompt and bias controls → `td-synthetic-generation` (this skill calls it)
- Multimodal preference data → `td-vision-language-data`

## Pick the format first — it constrains everything

| Trainer | Record shape | When |
|---|---|---|
| **DPO / IPO** | `prompt` + `chosen` + `rejected` (paired) | The default; you can produce two responses per prompt and rank them |
| **ORPO** | same paired shape, but runs *without* a separate SFT stage | You want one-stage SFT+preference; needs clean pairs |
| **KTO** | `prompt` + `completion` + boolean `label` | You have thumbs-up/down signals, not pairs — unpaired is fine, cheaper to collect |
| **Ranking (PPO/reward-model)** | prompt + n ranked responses | You're training a reward model, not doing direct preference optimization |

One preference file uses **one** shape (`td-dataset-formats`). For a small model, **DPO on clean pairs is the usual choice** — it skips the reward-model machinery and is stable.

## The prompt set decides what you align

Preference data teaches "given *these* prompts, prefer *this* behavior." Draw the prompts from where the model will actually be used and where it currently fails:

- **Reuse SFT prompts** for baseline coverage.
- **Target known weaknesses** — prompts where the SFT model is verbose, hedges, hallucinates, ignores constraints, or is unsafe. This is where preference tuning earns its keep.
- **Include safety/refusal prompts** with a preferred refusal vs a preferred-not compliance — this is how you tune the refusal boundary.

## Building the pairs

### Off-policy (from a teacher)

Sample n responses to each prompt at temperature (n=4–8 — variance is the point), judge them with the **pinned, calibrated judge** (`td-synthetic-generation`), take the top as `chosen` and a **plausibly-worse** one as `rejected`. Record `margin` and `judge_reason` in `meta`.

### On-policy (from the student) — usually stronger

Sample the responses from **the model you are training** (its current checkpoint), then judge. This targets the model's *actual* failure modes rather than the teacher's, and is what makes DPO/iterative alignment work: the rejected responses are things the model really does. Re-sample after each round (iterative DPO). Off-policy pairs from a much stronger teacher can be *too* far from the student's distribution to be a useful gradient.

### Constitutional / self-critique

Generate a response, critique it against an explicit principle, revise. `(revised, original)` is a preference pair; the critique is SFT signal for a critic model. State the principles — they *are* the alignment target — and keep them in the card.

## The margin rule — the thing most preference sets get wrong

- **`rejected` must be plausibly worse, not garbage.** The model learns the *difference*. "Excellent answer vs empty string" teaches nothing transferable; "grounded answer vs confident hallucination" teaches the thing you want. Prefer pairs where both responses are on-topic and the loser fails on one clear axis.
- **Ties are not preferences.** If the judge flips on A/B swap, or the two responses are equivalent, drop the pair — a coin-flip label is noise the optimizer will chase. Record the tie rate; a high one means your sampling isn't producing real variance.
- **Control for length and format bias.** LLM judges (and humans) prefer longer, more formatted answers regardless of quality. If `chosen` is systematically longer, your model will learn to pad. Measure the length delta distribution; if it's skewed, control for it (length-balanced judging, or penalize length in the rubric).
- **Consistency across the set.** The same axis should decide preference throughout — don't mix "prefer concise" and "prefer thorough" without a signal telling the model which context wants which, or you teach contradiction.

## Quality gate

Route pairs through `td-data-quality`: dedup prompts, PII scrub, decontaminate prompts against evals. Then preference-specific checks: drop ties, check the margin distribution isn't collapsed, check the length-bias distribution, and spot-audit `judge_reason` on a sample so a human confirms the judge's calls hold up. Keep dropped pairs with reasons.

## Split

Split by prompt dedup cluster so the same prompt never straddles train/test (`td-dataset-formats`). A held-out preference test lets you measure preference accuracy after tuning.

## Hard rules

- **One trainer format per file** (DPO-style paired *or* KTO-style labeled), decided first.
- **`rejected` is plausibly worse, not garbage** — the margin is the signal.
- **Ties are dropped**, not labeled; a judge decision that flips on swap is a tie.
- **Length/format bias is measured and controlled** — otherwise you tune a padding machine.
- **Prefer on-policy pairs** (sampled from the student) for real alignment; re-sample each round.
- **Judge pinned + calibrated**, reasons kept for audit; prompts decontaminated against evals.

## Fences

- `td-instruction-sft` produces the SFT model preference tuning runs *on top of* — preference data is a second stage, not a replacement.
- The sampling-and-judging *mechanics* (n-sampling, the pairwise-judge prompt, position/length bias controls, calibration) live in `td-synthetic-generation`; this skill owns the *pair-construction discipline* (margin, ties, on-policy, format choice).
- Scoring the tuned model's alignment is `td-eval-sets`.
