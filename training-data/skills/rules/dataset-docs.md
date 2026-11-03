---
paths:
  - "**/docs/datasets/**/*.md"
---

<!-- training-data rules v1 (2026-11-03): dataset cards and audit reports. Installed by /training-data:rules; edit the paths above to where this project keeps them. -->

# Dataset card and audit report standards

Severity tags as in the core dataset rules: **blocker**, **major**, **minor**, **nit**. The project wins where it consistently does otherwise.

## The card, `<name>-card.md`

- It has five sections: what it is (stage, modality, intended use, one example record); provenance (each `source` value with its count, license and how it was obtained; teacher model and batch ids); construction (filters, dedup and decontamination applied, the drop count at each step, split method and counts); composition (a table by `meta` tag); limitations and risks. *major*
- It records the decisions: the contamination rate found and against which targets (a 0 % on a web corpus means the check is broken); the PII redaction strategy; the safety policy (what the model must handle versus never reproduce); the system-prompt choice; the teacher terms-of-use decision; the pinned judge and its human-agreement rate. *major*
- Pretraining states the token budget, counted with the real tokenizer, and the mixing blend as a source × tokens × % table; VLM states its coordinate convention. *major*
- A number in the card comes from a run on these files. When the files change, the check is re-run, never carried over. *major*

## Audit reports, `audits/<NNN>-<dataset>-audit-r<N>.md`

- One file per round; an earlier round is never overwritten or edited, and finding ids are permanent and never reused. *major*
- A finding is marked Resolved only by a later round that re-ran its check; a fix commit or an updated card is a lead, not evidence. Never edit a report to mark a finding fixed. *major*
- Every finding carries `id` or `file:line` evidence read that round, a severity and its section. *minor*
