# Extraction, sources & sharding — reference

## Extraction setup

```python
# HTML — main-content extraction, not raw get_text()
import trafilatura
text = trafilatura.extract(html, include_comments=False, include_tables=True,
                           favor_precision=True)

# PDF — text layer
import pymupdf
text = "\n".join(page.get_text("text") for page in pymupdf.open(path))
# scanned/complex layout → Marker (marker-pdf) or a VLM-OCR pass (td-vision-language-data)

# Code — read directly, filter by language/size, drop generated/minified/vendored
```

Validate on a random sample every run: print 20 extracted docs and read them. Extraction fails silently.

## Curated public pretraining sources (check each license for your use)

| Source | Content | License note |
|---|---|---|
| FineWeb / FineWeb-Edu | filtered web (edu subset is quality-filtered) | ODC-BY; per-doc varies |
| DCLM | filtered CommonCrawl | check terms |
| The Stack v2 | permissively-licensed code | per-repo license retained; opt-out honored |
| Wikipedia | encyclopedic | CC-BY-SA (share-alike obligations) |
| Project Gutenberg | public-domain books | PD (US); check jurisdiction |
| arXiv | scientific papers | per-paper license; many non-commercial |
| OpenWebMath / proof-pile | math text | check terms |
| C4 | cleaned CommonCrawl | ODC-BY |

For a small model, a smaller high-quality curated blend beats a raw crawl. Prefer the already-filtered edu/quality subsets.

## Mixing blend — worksheet

```
For each source: raw_tokens, keep_after_filter, target_share
target_tokens[source] = corpus_budget × target_share
repeat_factor[source] = target_tokens / keep_after_filter   # >1 means up-sample (repeat)
```

Report the final table: source → tokens → % → repeat_factor. Keep repeats on high-quality sources modest (a few epochs); do not up-sample low-quality web to hit a token target — collect more or shrink the budget instead.

## Token counting & sharding

```python
# Count with the ACTUAL tokenizer you will train, not word counts.
from transformers import AutoTokenizer
tok = AutoTokenizer.from_pretrained("<your-tokenizer>")
n_tokens = sum(len(tok(doc["text"], add_special_tokens=False)["input_ids"]) for doc in docs)

# Shard at a fixed record/byte target; record counts + sha256 in manifest.json.
```

Documents stay whole in JSONL — the trainer packs multiple docs into a context window with a separator and truncates. Do not pre-chunk to context length.
