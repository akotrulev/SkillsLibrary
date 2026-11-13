---
paths:
  - "docs/plans/**/epics.md"
---

<!-- business-analysis rules v2 (2026-11-13): epics. Installed by /business-analysis:rules; edit to fit this project. -->

# Epic standards

For `docs/plans/<NNN>-<initiative>/epics.md`. Severity as in the requirements rules: **blocker** cannot be planned from, **major** will mislead the stories or the plan, **minor** shape or format, **nit** wording. The template, examples and know-how are `business-analysis:epics`'s.

- Epics are `E1..En`; every requirements.md §4 capability is covered by exactly one, and an initiative has at least one. Ids are cited downstream: never renumber. `E0` is the planner's foundations epic, never written here. *blocker*
- One goal per epic: **who** can **do what** so that **measurable change**. Two goals are two epics. An unknown measure is `[TBD — <who decides>]` plus an open question, never an invented number. *blocker*
- Every epic has its plain-English section: "Who it is for and why", "What gets built", "How it fits with everything else". It names no technology, is not a summary of the sections below, and "how it fits" says what becomes possible and names other epics by what they are, not as a dependency list. *major*
- No technology anywhere in the document: no table, endpoint, service, component, library, queue or framework, no API list or data shape. *major*
- No goal-less or tech-only epic ("platform improvements", "migrate to v3"); that is a tech-debt task. *major*
- "How we get there" is the route across the stories: the axis they are cut along (workflow, role, read-before-write, data variation), which comes first and why it is usable alone, what each later one adds, decisions taken. Restating the goal is not a route. *major*
- "What is included" lists the stories, each one whole feature a person would name with the parts it holds, never a layer ("API only", "UI only") or a fragment no use on its own. The first is usable end to end, and all follow the named axis. *major*
- The listed stories are anticipated, not committed. *minor*
- In scope / out of scope / deferred, each excluded item with its reason and follow-up. *minor*
- Dependencies both ways: blocked by, blocks, parallel. *minor*
- Risks are the epic's own (sequencing, parallel work), with likelihood, impact and mitigation, not copied from the requirements. *minor*
- The Definition of Done is a binary checklist with no "tested" item. *minor*
- A stated delivery window is held: a slip is a split or a replan, never a silent extension. *major*
