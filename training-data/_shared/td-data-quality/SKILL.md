---
name: td-data-quality
description: Use when cleaning, filtering, deduplicating, or decontaminating a training dataset — the gate every dataset passes before training. Triggers: "dedup this corpus", "check for eval contamination", "filter low-quality examples", "scrub PII from the SFT data", "balance the dataset by topic". Do NOT use for record schema (`td-dataset-formats`), synthesis (`td-synthetic-generation`), or corpus collection (`td-pretraining-corpus`).
---

# Training Data — Quality, Dedup & Decontamination (cross-stage)

The quality gate every dataset — pretraining, SFT, preference, eval, VLM — passes before it is trained on. Garbage, duplicates, and eval leakage are the three ways a training set silently ruins a model: garbage teaches noise, duplicates memorize and waste compute, and contamination inflates every eval number so you cannot tell whether the model learned or cheated. This skill owns the universal filters and the two dedup/decontamination passes; stage skills call it and add their own content checks.

## When to use

- Removing exact and near-duplicate records from any dataset
- Checking a train split for contamination against the test/eval split (the non-negotiable pass)
- Filtering by quality (heuristics, a trained classifier, or an LLM grader)
- Scrubbing or redacting PII; filtering toxicity/unsafe content to the policy the model needs
- Language identification and length/format filtering
- Balancing/mixing a dataset so no topic, source, or template dominates

## When NOT to use

- The record schema and split boundaries → `td-dataset-formats`
- Generating records → `td-synthetic-generation`
- HTML/PDF extraction and boilerplate stripping → `td-pretraining-corpus`
- Preference-pair validity (is `chosen` actually better) → `td-preference-data`

## The order of operations (do not reorder)

Filtering is cheap and dedup is expensive, so filter first; decontamination must run on what actually ships, so it runs last, after splitting:

1. **Normalize** — Unicode NFC, strip control chars, collapse whitespace, fix mojibake. Same text must hash the same.
2. **Cheap filters** — language, length, format validity, hard content rules. Drop obvious garbage before paying for dedup.
3. **Exact dedup** — hash the normalized payload; keep one.
4. **Near-dedup** — MinHash/LSH clustering; keep one representative per cluster.
5. **Quality filter** — heuristic score, classifier, or LLM grade; drop below threshold.
6. **Split** — assign whole near-dup clusters to train/val/test (`td-dataset-formats`).
7. **Decontaminate** — remove any train record that near-matches any test/eval record. **Last, always, no exceptions.**

Log counts removed at every step into the dataset card. A pipeline that drops 80% of its data at step 5 is telling you something about the source — surface it, don't hide it.

## Exact deduplication

Hash the **normalized** payload (the `text`, or the concatenated `messages` content, or the `prompt`+`chosen` for preference), keep the first occurrence, drop the rest. This alone removes boilerplate reposts, re-crawled pages, and accidental double-generations. Deduplicate **across splits and across the whole corpus**, not per-file. Record which `id` survived so provenance stays traceable.

## Near-deduplication (the one that matters)

Exact dedup misses the real problem: documents that differ by a timestamp, a header, or three words. Use **MinHash + LSH** (e.g. `datasketch`) on shingled n-grams:

- Shingle each document into overlapping token n-grams (5-grams is a sane default).
- MinHash each document (128–256 permutations).
- LSH-bucket at a Jaccard threshold (**0.8** for pretraining, **0.7** for SFT where paraphrase is the duplication).
- Each connected cluster → keep one representative (longest, or highest quality score), drop the rest.
- **The cluster id is what splits assign on** — every member of a near-dup cluster goes to the *same* split, or the held-out set is contaminated by construction.

For very large corpora, suffix-array substring dedup (à la Google's `deduplicate-text-datasets`) removes repeated *spans* within documents; MinHash removes repeated *documents*. Pretraining wants both; SFT usually needs only document-level.

## Decontamination — the non-negotiable pass

**No training record may near-match any evaluation record.** This is how you keep eval numbers honest. Run it against:

- Your own frozen `test.jsonl` split.
- Every public benchmark you intend to report (MMLU, GSM8K, HumanEval, HellaSwag, the VLM benchmarks — pull their questions).
- Any customer/production eval set the model will be judged on.

Method: n-gram overlap (13-gram substring match is the field-standard bar) **and** MinHash near-match at Jaccard ≥ 0.7 between each train record and the eval pool; drop the train record on a hit. For multiple-choice benchmarks, match on the question stem, not the letter answer. Record the contamination rate found (`"0.3% of train near-matched MMLU — removed"`) in the card; a *zero* rate on a web corpus usually means the check is broken, not that the corpus is clean.

**Canary strings:** seed eval sets with a unique GUID (`td-dataset-formats` `canary` field). If that GUID ever appears in a corpus, you have proof of leakage and a grep-able tripwire.

## Quality filtering

Match the method to the stage — the bar for pretraining ("is this coherent human text") is not the bar for SFT ("is this a good answer"):

| Method | Cost | Use for | Watch |
|---|---|---|---|
| **Heuristics** — length bounds, symbol/word ratio, % alphabetic, repeated-line ratio, stopword presence, perplexity under a small LM | cheap | Pretraining bulk filtering (the C4/Gopher/RefinedWeb rules) | Over-aggressive rules delete code, tables, and non-English — test on a sample first |
| **Trained classifier** — fastText/logistic on "good vs bad" labels, or a reference-corpus classifier (Wikipedia-like = keep) | medium | Large corpora where heuristics plateau | The classifier inherits the bias of its "good" set — you are selecting for *resemblance to the reference*, not truth |
| **LLM grader** — score each record 1–5 on a rubric with the Claude API | expensive per record | SFT/preference where quality is semantic; small-to-medium sets | Pin the judge model + prompt + version; grade a human-labeled calibration set first (see `td-synthetic-generation` on judge-pinning) |

Always keep the **dropped** records in a `rejected/` file with the reason, at least until the dataset is validated — you cannot tune a threshold you can't inspect, and an over-eager filter is discovered by reading what it threw away.

## PII and safety

- **Detect and redact PII** (emails, phones, national ids, credit cards, keys/tokens, physical addresses) with a scanner (Presidio, regex packs, or an LLM pass for free-text names). Redaction strategy is a deliberate choice recorded in the card: drop the record, mask the span (`[EMAIL]`), or pseudonymize consistently. A model trained on un-redacted PII will regurgitate it.
- **Secrets never survive** — an API key or private key in the data is both a leak and a thing the model will emit; drop the record, don't mask.
- **Safety filtering is policy, not a universal switch.** A model that must *refuse* harmful requests needs harmful prompts *with refusals* in its SFT/preference data — filtering them all out produces a model that has never seen the category. Decide per dataset what the model must learn to handle vs never reproduce, and state it in the card.

## Balancing and mixing

A dataset's *composition* is training signal — the model learns the distribution you show it:

- **Pretraining mixing weights** — up/down-sample sources to a target blend (e.g. more code, less low-quality web); state the final blend in the card. Repeating high-quality data a few epochs beats diluting with low-quality data.
- **SFT/preference balance** — cap any single topic, template, persona, or `source` so it can't dominate; a set that is 60% "write a poem" makes a poem model. Use the `meta` tags from `td-dataset-formats` to measure and cap.
- **Report the composition table** in the card (count by `meta.topic` / `source` / `difficulty`) — skew you can't see is skew you ship.

## Hard rules

- **Decontamination runs last and always.** A dataset that hasn't been checked against its eval targets is not shippable, and its eval numbers are not trustworthy.
- **Near-dedup, not just exact.** Split by dedup cluster so near-duplicates never straddle the train/test line.
- **Keep dropped records with reasons** until the dataset is validated — a filter you can't inspect is a filter you can't trust.
- **PII/secrets are removed before training**; the redaction strategy is a recorded decision.
- **Every drop count and the final composition go in the dataset card.** Silent filtering is unreproducible filtering.

## References

- `references/dedup-decontam.md` — runnable MinHash/LSH and 13-gram decontamination recipes, heuristic filter thresholds (C4/Gopher/RefinedWeb), and the PII scanner setup.
