# Dedup, decontamination & filtering — runnable recipes

Reference implementations. Adapt thresholds to the corpus; the SKILL.md holds the rules and the ordering.

## Normalization (step 1, before any hash)

```python
import unicodedata, re
def normalize(t: str) -> str:
    t = unicodedata.normalize("NFC", t)
    t = "".join(c for c in t if c == "\n" or c == "\t" or ord(c) >= 32)
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()
```

## Exact dedup

```python
import hashlib
seen = set()
def keep_exact(payload: str) -> bool:
    h = hashlib.sha256(normalize(payload).encode()).hexdigest()
    if h in seen: return False
    seen.add(h); return True
```

## Near-dedup — MinHash + LSH (datasketch)

```python
from datasketch import MinHash, MinHashLSH

def shingles(text, n=5):
    toks = normalize(text).split()
    return {" ".join(toks[i:i+n]) for i in range(max(1, len(toks)-n+1))}

def minhash(text, perm=128):
    m = MinHash(num_perm=perm)
    for s in shingles(text): m.update(s.encode())
    return m

lsh = MinHashLSH(threshold=0.8, num_perm=128)   # 0.7 for SFT paraphrase
mh = {}
for rec in records:                              # rec = {"id":..., "payload":...}
    m = minhash(rec["payload"]); mh[rec["id"]] = m
    lsh.insert(rec["id"], m)

# union-find over LSH neighbours → clusters; keep one representative per cluster,
# and record cluster_id on every member so splits assign whole clusters together.
```

Representative choice: longest document, or highest quality score. Persist `cluster_id` — it is the split key.

## Decontamination — 13-gram substring + MinHash

```python
def ngrams(text, n=13):
    toks = normalize(text).split()
    return {" ".join(toks[i:i+n]) for i in range(max(1, len(toks)-n+1))}

# Build the eval pool once (your test split + every public benchmark you report).
eval_grams = set()
for e in eval_pool: eval_grams |= ngrams(e["text"])

def is_contaminated(train_text) -> bool:
    if ngrams(train_text) & eval_grams:        # exact 13-gram overlap
        return True
    # plus MinHash near-match ≥ 0.7 against eval MinHashes (LSH query)
    return bool(eval_lsh.query(minhash(train_text)))
```

For multiple-choice benchmarks, run `ngrams()` on the **question stem only**. Report the hit rate in the card. A 0% rate on a web corpus means the check is broken.

Public benchmark question sources to pull for the eval pool: MMLU, GSM8K, HumanEval/MBPP, HellaSwag, ARC, TruthfulQA, WinoGrande; VLM — VQAv2, TextVQA, DocVQA, MMMU, ChartQA.

## Heuristic quality filters (pretraining — Gopher/C4/RefinedWeb style)

Drop a document when any holds:

- Fewer than 50 or more than 100k words.
- Mean word length < 3 or > 10 characters.
- Symbol-to-word ratio > 0.1 (`#`, `…`, ellipsis-heavy).
- < 80% of lines are unique, or the top line/paragraph repeats > 30%.
- < 90% of characters are in the target script/alphabet.
- Fewer than 2 of a stopword set present (English: the, be, to, of, and, that, have, with).
- Ends abruptly mid-sentence with no terminal punctuation on > 30% of lines (nav/boilerplate).
- Perplexity under a small reference LM (KenLM on Wikipedia) above a percentile cutoff.

Test the rule set on a labeled sample first — these delete code, tables, and non-English if applied blind.

## Language ID

`fasttext` `lid.176.bin` or `langdetect`; keep the target language(s) above a confidence floor (0.65). Store the detected `lang` in `meta` so multilingual balance is measurable.

## PII / secrets

- **Presidio** (`presidio-analyzer`) for named-entity PII (person, email, phone, credit card, IBAN, SSN-like) with redaction/pseudonymization operators.
- **detect-secrets** / **gitleaks** regex packs for API keys, tokens, private keys — drop the record entirely, never mask.
- LLM pass for free-text names/addresses the regex packs miss (expensive; sample or run only on flagged records).
