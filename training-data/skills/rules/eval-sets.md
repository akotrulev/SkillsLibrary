---
paths:
  - "**/datasets/**/test*.jsonl"
  - "**/datasets/**/test/**/*.jsonl"
---

<!-- training-data rules v1 (2026-11-03): eval sets. Installed by /training-data:rules; edit the paths above to where this project keeps its frozen test and eval sets. -->

# Eval set standards (the frozen test split and purpose-built evals)

Severity tags as in the core dataset rules: **blocker**, **major**, **minor**, **nit**. The dataset wins where it consistently does otherwise.

- The test set is drawn once and frozen: it does not change between model versions, it is never tuned on, and iteration happens on `val`/dev. *blocker*
- It is the decontamination target: every change to train is re-checked against it, and the rate found is reported in the card. *blocker*
- An item is `messages` + `reference` (gold answer or rubric id) + an `eval` block (`type` of `exact_match` | `multiple_choice` | `rubric` | `llm_judge`, with `choices` and `answer` where they apply). *major*
- Each eval set seeds a unique `canary` GUID in its items, so leakage into a corpus is provable. *major*
- Gold answers are human-verified, synthetic ones especially; the model under test, or a judge of its own family, never grades its own eval unchecked. *major*
- Deterministic scoring (exact match, a checker, a schema validator) wherever it exists; a rubric or LLM judge only for open-ended items, with the rubric in the item or a shared rubric id, and the judge pinned and calibrated against a human-labelled subset. *major*
- Exact match states its normalization (whitespace, case, numeric tolerance) up front. *minor*
- Multiple choice randomizes option order and balances the correct letter; decontamination matches on the stem, not the letter. *minor*
- Coverage mirrors the intended use: every task bucket the training set targeted, a hard tail, safety and refusal cases, the failure modes preference tuning aimed at, and for VLM unanswerable and negative visual cases. Per-bucket counts go in the card. *major*
