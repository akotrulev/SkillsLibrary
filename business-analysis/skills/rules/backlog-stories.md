---
paths:
  - "docs/plans/**/stories.md"
---

<!-- business-analysis rules v1 (2026-11-03): user stories. Installed by /business-analysis:rules; edit to fit this project. -->

# User story standards

For `docs/plans/<NNN>-<initiative>/stories.md`, and the checklist `business-analysis:story-review` applies to any backlog. Severity: **blocker** the story cannot proceed, **major** will hurt soon, **minor** format or naming, **nit** preference. The template and splitting know-how are `business-analysis:stories`'s.

- Each story is `## US<n> — <title>` with `**Epic:** E<n>`. Ids run flat across the initiative, never restart per epic and are never renumbered; a dropped story keeps its id with a line saying why. *blocker*
- As a / I want / So that, and the so-that names value to a person, never "so that the system can…". *blocker*
- The role is specific ("logged-in admin"), never a bare "user". *major*
- A story is demoable to a stakeholder. A technical task, or one layer of a capability ("the API", "the screen"), is not a story: merge it back into its capability. *major*
- INVEST: independent of its siblings, negotiable (intent, not an implementation spec), valuable, estimable, small enough for one sprint (two capabilities is a split), testable. *major*
- Acceptance criteria are Given / When / Then. *minor*
- One behaviour per scenario; an `And` chain hiding several behaviours is split. *major*
- Every Then is an observable outcome; an AC that restates the title or "the user can do X" with no check is untestable. *blocker*
- Functional and non-functional AC (performance, accessibility, audit) are separate labelled lists. *minor*
- A contradiction between AC, or between the story and its epic, is a finding, never silently resolved. *blocker*
- A validation states field, rule and outcome on violation. No unfalsifiable word ("fast", "user-friendly", "recently") without a number. *major*
- No technology: no table, endpoint, screen, component or library. A business constraint is cited from requirements.md §5, not restated. *major*
- Out of scope is listed per story. *minor*
- Dependencies by story id (`Depends on: US<n>`, or none); an undeclared one is a finding. *major*
- Source cites the requirements.md §4 lines and business rules, never designs or contracts. *minor*
