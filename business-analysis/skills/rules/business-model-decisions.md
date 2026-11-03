---
paths:
  - "docs/business-model/decisions/**/*.md"
---

<!-- business-analysis rules v1 (2026-11-03): decision tables. Installed by /business-analysis:rules; edit to fit this project. -->

# Decision-table standards

Severity tags as in the core business-model rules: **blocker**, **major**, **minor**, **nit**. The KB wins where it consistently does otherwise. Hit-policy semantics, the template and the procedure are `business-analysis:decision-table`'s.

- One merged table per decision point (one question, its outputs), holding the rules of every feature that touches it. Never a second table for the same point. *blocker*
- A hit policy is declared: U, A, F, P, or a Collect with its aggregation (C list, C+ sum, C< min, C> max, C# count). Author toward U; F or P only where the business stated precedence, C only where combining is intended, each with its source. *major*
- A policy or operator nobody decided resolves nothing: the header says `[TBD - needs business decision]` and the finding is filed. Never pick first-match order or an operator yourself. *blocker*
- Every rule row names its owning feature id and its source (`US<n> AC<k>`, BRD section). *major*
- Every input has its type, partitions and glossary meaning ("total" pre- or post-discount is drift that fakes agreement). *major*
- A Checks section records both checks. Completeness: every input combination no rule matches is a gap finding naming that combination. Overlap: rules matching one combination with different outputs are a contradiction unless a sourced policy resolves it; identical outputs are a redundancy marked for merge. *major*
- Don't-care inputs are `-`. *nit*
- A single-rule decision with no second contributor in sight is a line in the flow's Steps table, not a table. *nit*
