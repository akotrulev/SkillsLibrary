---
paths:
  - "docs/business-model/entities/**/*.md"
---

<!-- business-analysis rules v1 (2026-11-03): entity state grids. Installed by /business-analysis:rules; edit to fit this project. -->

# Entity state-grid standards

Severity tags as in the core business-model rules: **blocker**, **major**, **minor**, **nit**. The KB wins where it consistently does otherwise. The template and the procedure are `business-analysis:state-grid`'s.

- One model per business entity, shared by every feature. A new feature's states and events are overlaid on it, never kept in a copy of their own. *blocker*
- States are business conditions from the glossary ("Submitted", "Suspended"), not implementation flags. A near-synonym of an existing state is terminology drift. *major*
- Every `state × event` cell is filled: the target state with its owning feature id, `—` (illegal by decision) or `?` (unspecified, a finding). Never a blank cell. *major*
- Events include lifecycle jobs (expiry, archival, cleanup), not only user actions. *major*
- Once `events.md` exists, each column header is the trigger's `EVT-` id with a label. *minor*
- Every legal transition names exactly one owning feature. Two owners is a double-fire finding; none is an orphan. *major*
- Guards are recorded with their feature and source; two features demanding different guards on one transition is a finding. *major*
- Every finding names its boundary condition ("subscription expires while the upgrade payment is mid-capture"). *major*
- A grid is earned at three or more states, or two or more features touching the lifecycle; below that, a note in the flow file. *nit*
