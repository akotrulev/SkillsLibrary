---
paths:
  - "docs/business-model/interaction-map.md"
---

<!-- business-analysis rules v1 (2026-11-03): interaction map. Installed by /business-analysis:rules; edit to fit this project. -->

# Interaction-map standards

Severity tags as in the core business-model rules: **blocker**, **major**, **minor**, **nit**. The KB wins where it consistently does otherwise. The sweep and the entry template are `business-analysis:conflict-check`'s.

- One entry per conflict, headed `## CONF-nnn — <feature> × <feature>: <the conflict>`, tagged `#resolved` once decided. Entries are never deleted or renumbered. *blocker*
- Each entry gives its class (one of the eleven: contradictory rules, trigger overlap, state interference, resource contention, ordering/race, circular dependency, policy stacking, permission/authority, duplication/subsumption, terminology drift, boundary divergence, with its number), its severity, its boundary condition, the pair as feature ids with labels, the sources, and the artifacts updated. *major*
- The boundary condition is the concrete scenario where the two features collide ("order at exactly $100.00 with a 20% promo and 500 points"). Without one it is a suspicion and is not entered. *major*
- Severity: **blocker** ships a wrong outcome in a realistic scenario, **major** will bite soon or blocks test design, **minor** is an ambiguity with a cheap fix, **nit** is wording or glossary hygiene. *minor*
- A resolution records the date, who decided, the decision, and why. Only a person decides: options are presented, nothing is auto-resolved, and an unresolved entry stays open and is listed in `active-context.md`. *blocker*
- A resolved conflict is not re-litigated; a new finding that breaks a resolution cites its `CONF-` id. *major*
