---
paths:
  - "docs/features/*-*.md"
---

<!-- dev rules v1 (2026-11-03): feature documents. Installed by /dev:rules; edit the path above if this project keeps feature documents elsewhere. -->

# Feature document standards

A feature document (`<NNN>-<slug>.md`) is evidence-based reverse documentation. Apply these when you write one, or edit one because the code changed. Severity: **blocker** states what nobody can check or confirmed, **major** weakens the evidence or the reader's grasp, **minor** is form. Where the project consistently does otherwise, follow it.

- Everything above **Where this lives in the code** is business language: no class, method, table or column names, status codes, exception types, framework nouns, tier tags or `file:line`. Those live only in that closing evidence table. *major*
- Every parameter, formula, threshold, step and branch in the body has an evidence row: `#observed` cites `file:line` read in this session, `#inferred` names its open question, a negative claim names its search. *blocker*
- Never write `#confirmed`; promotion is a human act. A row a human confirmed is not yours to change: escalate the contradiction. *blocker*
- Never invent a purpose. An inferred intent reads as uncertainty in the body ("appears to exist so that…") and is a row in Open questions. *blocker*
- The worked example is mandatory, numeric whenever there is a calculation, threshold, layered setting or time-based process. Every number used as a rule is the code's exact value, the arithmetic is recomputed after any change, one cast runs throughout, and it never extends past what the code says. *major*
- A formula is plain-text math on its own line with `Where:`, rounding and conventions stated; never code. *major*
- Optional sections are dropped, never padded; the negative search that proved the absence is an evidence row. *minor*
- Nothing unreachable is written up as a capability. Defects go to Findings, routed to their owner, never into the flows as intended behaviour. *major*
- When the code moves, update in place: re-read every citation at the current commit, re-stamp the header, re-run the example. A drifted `file:line` is worse than none. *major*
- `<NNN>` is never renumbered or reused. Nothing is written into `docs/business-model/`; cite a KB id rather than restating it. *minor*
