---
name: td-pretraining-corpus
description: Use when building a raw-text pretraining corpus for a small LLM — collecting sources, extracting clean text from HTML/PDF, quality/language filters, dedup, and sharding with a mixing blend. Triggers: "build a pretraining corpus", "extract clean text from these web pages / PDFs", "shard a corpus for training", "what mixing weights for my pretraining data". Do NOT use for instruction/chat data (`td-instruction-sft`), preference data (`td-preference-data`), or eval sets (`td-eval-sets`).
---

# Training Data — Pretraining Corpus

The raw-text foundation a small LLM learns language from. Pretraining data is judged on three things: **volume** (enough tokens for the model size), **cleanliness** (text a human would recognize as real prose/code, not nav bars and cookie banners), and **composition** (the blend of sources decides what the model is good at). This skill owns collection → extraction → cleaning → filtering → dedup → sharding; it hands the dedup/filter *mechanics* to `td-data-quality` and the on-disk shape to `td-dataset-formats`.

## When to use

- Assembling a text corpus to pretrain (or continue-pretrain) a small language model
- Extracting readable text from HTML, PDF, ePub, code repos, or a document dump
- Deciding and documenting the source mixing blend
- Sharding a large corpus for training and estimating its token count

## When NOT to use

- Chat/instruction data → `td-instruction-sft`
- Preference/DPO data → `td-preference-data`
- Held-out benchmarks → `td-eval-sets`
- Image-text pretraining pairs → `td-vision-language-data`
- The dedup/filter algorithms themselves → `td-data-quality` (this skill calls it)

## How much data — size the corpus to the model

A small model does not need a trillion tokens, but it needs *enough*: the Chincherror-optimal rule of thumb is **~20 tokens per parameter**, and small models are usually trained past that (more tokens, since compute is cheap relative to a good small model). Ballpark targets:

| Model size | Compute-optimal tokens | Practical target for a strong small model |
|---|---|---|
| 100–350M | ~2–7B | 10–50B (train past optimal) |
| 1B | ~20B | 50–200B |
| 3–7B | ~60–140B | 200B–2T |

State the token budget up front — it decides how much you must collect and how hard you can afford to filter. Under-data a model and it underfits; over-filter a small corpus and you starve it. Count tokens with the *actual tokenizer* you'll train (`td-dataset-formats` manifest), not word counts.

## Collection

- **Prefer permissively-licensed and curated sources.** Public pretraining sets already cleaned (FineWeb / FineWeb-Edu, The Stack for code, Wikipedia, C4, Project Gutenberg, arXiv, OpenWebMath, DCLM) save you the crawl-and-clean cost and come with known provenance. For a small model, a smaller *high-quality* curated corpus usually beats a larger raw crawl.
- **Record the source and license on every document** (`td-dataset-formats` envelope). `web:<domain>`, `public:<dataset>`, `human:<team>`. A document with no license is a liability, not free data.
- **Respect robots/ToS when crawling yourself**, and keep the crawl date — the web changes and a corpus is a snapshot.

## Extraction — get the real text out

Raw HTML/PDF is mostly not the content. Extraction quality is the single biggest lever on corpus quality:

| Source | Tool | Watch |
|---|---|---|
| HTML | **trafilatura** (main-content extraction) or resiliparse; not naive `BeautifulSoup.get_text()` | Keep article body, drop nav/footer/ads/cookie banners; preserve paragraph and code-block structure |
| PDF | pdfplumber / PyMuPDF; **Marker** or a VLM-OCR path for scanned/complex layout | Column order, headers/footers repeated per page, hyphenation across line breaks, tables become garbage — validate on samples |
| Code | read files directly; keep license headers for attribution but consider stripping for training | Filter by language, drop vendored/minified/generated files, cap file size |
| ePub/docs | ebooklib / pandoc | Chapter boundaries, front-matter |

Always **eyeball a random sample** of extracted text before trusting the pipeline — extraction fails silently and at scale.

## Cleaning and filtering

Run the pipeline in `td-data-quality`'s order: normalize → cheap filters → exact dedup → near-dedup → quality filter. Pretraining-specific notes:

- **Boilerplate removal** is extraction's job first, then line-level heuristics catch the rest (repeated headers, "Share this article", pagination).
- **Language filter** to the target language(s); keep the detected `lang` for balance.
- **Quality heuristics** are the Gopher/C4/RefinedWeb rules (`td-data-quality` reference) — length bounds, symbol ratios, repetition, stopword presence. Tune on a labeled sample; blind application deletes code and tables.
- **Both dedup passes matter for pretraining** — document-level MinHash *and* substring/suffix-array dedup of repeated spans within and across documents. Duplicated text is memorized, wastes compute, and inflates apparent volume.
- **Decontaminate against your eval sets last** (`td-data-quality`) — a pretraining corpus that contains your benchmarks makes every downstream number meaningless.

## Composition — the mixing blend is the model's personality

The final blend of sources is a design decision, not an accident of what you collected:

- **Up/down-sample to a target ratio.** A code-capable model needs a real code fraction (20–40% for a code-leaning small model); a chat-leaning model needs more clean conversational/web prose; a domain model needs its domain over-represented but not to the exclusion of general language (or it forgets how to write).
- **Repeat high-quality data before diluting with low-quality data.** A few epochs over a clean curated set beats one pass over a noisy larger one — small models especially.
- **State the final blend in the dataset card** as a table (source → token count → % of corpus). Skew you don't measure is skew you ship.

## Sharding and output

- Emit JSONL with the raw-text record (`{"id","source","license","created_at","text"}` — `td-dataset-formats`), one whole document per line, uncut (the trainer packs/truncates to context length).
- **Shard** into fixed-size files (`train/shard-0000.jsonl`, …; ~256 MB–1 GB or 100k–500k records) and list every shard + record count + SHA-256 in `manifest.json`.
- Very large corpora export to **Parquet** for the trainer; keep JSONL as the authoring/review format.
- Split off a small `val`/`test` by dedup cluster (`td-dataset-formats`) so you can measure held-out loss.
- Write the token count (via the target tokenizer) into the manifest and card.

## Hard rules

- **Size the corpus to the model and state the token budget.** Count with the real tokenizer, not words.
- **Extraction quality is checked on samples** before scaling — silent extraction failure poisons everything downstream.
- **Both dedup passes** (document + substring) and **decontamination-last** are mandatory for pretraining.
- **The mixing blend is a documented decision**, reported as a source × token × % table in the card.
- **Every document keeps its source + license.** Unlicensed data is a finding.

## References

- `references/extraction-and-sources.md` — extraction tool setup per source type, a curated public-corpus catalog with licenses, and the shard/token-count worksheet.
