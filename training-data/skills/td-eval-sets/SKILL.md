---
name: td-eval-sets
description: Use when building held-out evaluation data to measure a small LLM/VLM you trained — golden test sets, multiple-choice/exact-match items, rubric and LLM-judge data, contamination checks, and canary strings. Triggers: "build an eval set for my model", "golden test set", "how do I measure my fine-tuned model", "LLM-as-judge eval data", "check my model isn't contaminated". Do NOT use for training data itself (`td-instruction-sft` etc.), or the eval-running harness (qa `ai-feature-testing`).
---

# Training Data — Evaluation Sets

The held-out data that answers "did the model actually get better?" An eval set is only trustworthy if it is **isolated from training** (contamination makes every number a lie), **representative** of what the model must do, and **scored the same way every time** (a drifting judge is a drifting ruler). This skill owns building the eval *data*; the harness that runs it and asserts on results is the QA domain's `ai-feature-testing` / `ai-answer-quality-testing` (named as peers, not loaded here).

## When to use

- Building a golden/held-out test set to measure a trained or fine-tuned model
- Designing multiple-choice, exact-match, or generative eval items
- Building rubric or LLM-judge eval data for open-ended outputs
- Setting up contamination checks and canary strings so eval integrity is provable
- Assembling a domain-specific eval when public benchmarks don't fit the product

## When NOT to use

- Training data of any stage → the stage skills
- Running the eval / asserting pass-rates / red-teaming → qa `ai-feature-testing`, `ai-answer-quality-testing` (peers)
- Preference *training* data → `td-preference-data`
- VLM-specific eval item content → `td-vision-language-data`

## The cardinal rule: the eval set is sacred and isolated

Everything about an eval set follows from one requirement — **nothing the model trained on may appear in it, and nothing in it may leak back into training**:

- **Draw it before training and freeze it.** The frozen test split from `td-dataset-formats` is one input; a purpose-built eval is another. Once frozen, it does not change between model versions — a moving eval can't show a trend.
- **It is the decontamination target** (`td-data-quality`): every train record is checked against it and dropped on a near-match. Run the check and report the rate in the eval card.
- **Seed canary strings** — a unique GUID per eval set embedded in items (`td-dataset-formats` `canary`). If it ever surfaces in a corpus or a model's output, you have proof of leakage.
- **Never tune on the test set.** Keep a separate `dev`/`val` set for iteration; the test set is looked at rarely and never optimized against. Optimizing against your eval is how you get a model that aces the eval and fails in production.

## Match the item type to what you're measuring

| Item type | Scoring | Use for | Watch |
|---|---|---|---|
| **Multiple choice** | exact — compare chosen letter | knowledge, classification, reasoning with defined answers | Randomize option order; balance the correct-letter distribution; match on the *stem* for decontamination, not the letter |
| **Exact / normalized match** | string/number equality after normalization | math (final answer), extraction, closed QA | Define normalization (whitespace, case, numeric tolerance) up front; a right answer failing on formatting is a broken eval |
| **Reference + similarity** | ROUGE/BLEU/BERTScore/embedding | summarization, translation — coarse signal | These correlate weakly with quality; use as a tripwire, not the verdict |
| **Rubric / LLM-judge** | scored against explicit criteria by a pinned judge | open-ended generation, chat quality, grounding | Pin the judge; calibrate against human labels; carry the reason — see below |
| **Golden pass/fail** | a checker function | code (does it run/pass tests), tool use (valid call), format compliance | Deterministic and best where it applies — prefer it over a judge when a checker exists |

**Prefer deterministic scoring where it exists** (exact match, a test runner, a schema validator) — it is cheap, reproducible, and unarguable. Reserve LLM-judge for genuinely open-ended outputs.

## Rubric and LLM-judge eval data

For open-ended quality, the eval *item* carries the rubric or reference the judge scores against:

- **Write the rubric into the item** (or reference a shared rubric id) — the criteria, each scored, so scoring is consistent across items and runs.
- **Pin the judge** (model id + prompt + version, recorded in the eval card) and **calibrate it against a human-labeled subset** before trusting it. Report the human-agreement rate — an uncalibrated judge is an unknown ruler.
- **Keep the judge's reason** per scored output so a human can spot-audit and so regressions are debuggable.
- Guard the same biases as `td-synthetic-generation`: position (randomize), length (control), self-preference (a judge favoring its own family).

The QA `ai-answer-quality-testing` skill owns the RAG-triad and retrieval metrics if the model is a RAG system — build the golden set with reference contexts and hand off.

## Coverage — the eval mirrors the intended use

An eval that tests one capability certifies one capability. Cover:

- **Every task bucket the SFT set targeted** (`td-instruction-sft` taxonomy) — so you can see per-capability regression, not just an average.
- **Difficulty spread** including a hard tail — an eval of only easy items saturates and stops discriminating.
- **Safety/refusal** — does the model refuse what it should and comply with what it should.
- **The failure modes you tuned against** (from `td-preference-data`) — did the preference tuning actually fix them.
- **Public benchmarks** relevant to the model (MMLU, GSM8K, HumanEval, HellaSwag; VLM: VQAv2, TextVQA, DocVQA, MMMU) as a comparability anchor — but a small domain model is best judged on a **domain eval you build**, not only public leaderboards it wasn't built for.

Report per-bucket counts in the eval card; a per-bucket score table is far more useful than a single number.

## Build small, label carefully

Eval quality outweighs eval size — **a few hundred carefully-verified items beat ten thousand auto-generated unverified ones**, because a wrong gold answer silently penalizes a correct model. If you synthesize eval items with a teacher (`td-synthetic-generation`), a human verifies the gold answers before they count. Never let the model-under-test (or its own family, for a judge) grade its own eval unchecked.

## Output

Eval items in the `td-dataset-formats` eval shape (`messages` + `reference` + `eval` block + optional `canary`), a frozen `test.jsonl`, and an eval card documenting: item types, scoring method, the pinned judge + calibration result, coverage table, contamination rate found, and the public benchmarks included.

## Hard rules

- **The eval set is frozen, isolated, and the decontamination target.** Never tune on it; iterate on a separate dev set.
- **Seed canary strings** so leakage is provable.
- **Prefer deterministic scoring**; reserve LLM-judge for open-ended items and pin + calibrate it.
- **Cover every capability the model claims** (per-bucket score table), including safety and the tuned failure modes.
- **Human-verify gold answers**, especially synthetic ones — a wrong gold answer punishes a right model.
- **Report the contamination rate** found against this eval in every model's card.

## Fences

- Building the eval *data* is here; **running it, asserting pass-rates, stochastic sampling, and red-teaming are the QA peers** `ai-feature-testing` / `ai-answer-quality-testing` (OWASP-LLM red-teaming lives there too). Build the set, hand it over.
- The frozen `test.jsonl` from any stage skill is a valid eval input; this skill turns it into a *scored* eval by adding references and an eval block.
