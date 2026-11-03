---
paths:
  - "docs/plans/**/requirements.md"
---

<!-- business-analysis rules v1 (2026-11-03): initiative requirements. Installed by /business-analysis:rules; edit to fit this project. -->

# Initiative requirements standards

For `docs/plans/<NNN>-<initiative>/requirements.md`. The tag after a rule is the severity a review reports: **blocker** the document cannot be planned from, **major** will mislead the epics or the plan, **minor** is shape or format, **nit** is wording. The project's own requirements convention wins where it consistently does otherwise. The template and the elicitation are `business-analysis:scoping`'s.

- Ten sections in this order, none dropped (an empty one says why): the ask verbatim, problem and why now, actors, what it must do, constraints, success, scope, assumptions, risks, open questions. *minor*
- §1 quotes the stakeholder verbatim, never paraphrased; everything below is checked against it. *major*
- The problem is stated in the business's terms before any solution wording. "Add a button" is a solution: the requirement is the workflow it unblocks. *major*
- §4 states capabilities as outcomes an actor gets, plus business rules with their numbers (limit, window, threshold). No technology: no stack, table, endpoint, screen or component. *major*
- A business-imposed constraint ("must reuse the current identity provider") is a §5 constraint, attributed to whoever stated it. *minor*
- Every actor has a goal, and one is named the decision-maker who approves scope. *major*
- Success is a measure with baseline and target, or an explicitly qualitative signal and who judges it. An unknown is an open question, never an invented number. *blocker*
- Scope has three columns: in, out (refused) and deferred (a follow-up commitment). Scope that is everything the stakeholder mentioned is no analysis. *minor*
- Every inference made because the stakeholder did not say is one line in §8 Assumptions. *major*
- Risks carry likelihood and impact separately (L/M/H), with a mitigation. *minor*
- Open questions are unknowns, not risks: each names who can answer it and what it blocks. *minor*
