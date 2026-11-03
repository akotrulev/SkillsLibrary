---
paths:
  - "**/promptfooconfig*.{yaml,yml}"
  - "**/evals/**"
---

<!-- qa-typescript rules v1 (2026-11-03): LLM evals. Installed by /qa-typescript:rules; edit the paths above to where this project keeps its eval suites. -->

# LLM eval standards (promptfoo, DeepEval, in-test judges)

Severity tags as in the core rules. The codebase wins where it consistently does otherwise.

- Never assert an exact string on free-form output. Climb the ladder: deterministic properties (`contains`, `is-json`, `regex`, `javascript`), then embedding similarity, then a rubric or judge. `equals` only for genuinely fixed output. *major*
- The judge is a versioned artifact: its model id and version pinned apart from the model under test, the rubric in a file, calibrated on a human-labelled gold set before it is trusted and again on a model bump. *major*
- An eval is a dataset: one input and expected properties per row, each row an independent, named case. *major*
- Regression cases pin the model, `temperature: 0` and a seed and assert once; stochastic cases sample N ≥ 3 and assert a pass rate. Model non-determinism is never handed to flaky-test quarantine. *major*
- Cost and latency ceilings and a capped `max_tokens` are assertions. *minor*
- API keys come from env, read lazily; never in `promptfooconfig.yaml` or code. *blocker*
- No real customer prompts or personal data in committed cases; synthetic or redacted only. *blocker*
- RAG suites decompose retrieval, generation on a fixed context, and end to end; the golden set carries reference contexts or chunk ids; faithfulness gets the actual retrieved context; every suite has a not-in-corpus abstention case. *major*
- Deterministic retrieval metrics (recall@k, MRR, NDCG) where labels exist; a judge for relevance only where they do not. *minor*
