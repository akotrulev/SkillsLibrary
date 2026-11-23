---
paths:
  - "docs/plans/**/stories.md"
---

<!-- product rules v6 (2026-11-23): stories. Installed by /product:rules; edit to fit this project. -->

# Story standards

For `docs/plans/**/stories.md` and the `product/skills/ba-story-quality-review` checklist. Severity: **blocker** cannot proceed, **major** will hurt soon, **minor** format, **nit** preference. Recipe: `product/skills/ba-story-writer`, read by the `business-analyst` agent.

- Each story is `## US<n> — <the feature's name>` with `**Epic:** E<n>`. Ids run flat across the initiative and are never renumbered; a dropped story keeps its id with the reason. *blocker*
- A story is one whole feature a person would name, with one goal. Two goals are two stories; a part useless without another is merged into its feature; a layer or a technical task is no story. *major*
- The sections, in order: Goal, How we get there, What is included, Acceptance criteria, Not included, Depends on, Source. *minor*
- The goal names who needs the feature (a specific person, not "the user"), what they can do once it is built and why it matters. *blocker*
- How we get there is the plan in the product's terms (approach, what it builds on, order, decisions taken), not the goal restated. No technology anywhere; a business-imposed constraint is cited from the system plan's §2 Constraints. *major*
- What is included lists every part with what it does, covering every §2 What it must do capability the story serves. *major*
- Criteria are `AC1..ACn` bullets, flat in the story, grouped under the part they prove (whole-feature ones under `Across the feature`) and cited as `US<n> AC<k>`: never reused or renumbered, a dropped one keeps its id with the reason. *major*
- Each criterion is one situation with its outcome, markable met or not by someone else. Restating a part's name or "the user can do X" is untestable. *blocker*
- Every included part has criteria for working and for failing. *major*
- A validation states field, rule and outcome on violation. No unfalsifiable word without a number. *major*
- A number comes from the requirements, otherwise `[TBD — <who decides>]` plus an open question; never invented. *blocker*
- A contradiction between criteria, or with the epic, is a finding, never silently resolved. *blocker*
- Dependencies are `Depends on: US<n>` or none; an undeclared one is a finding. *major*
- Not included lists each item with its reason and destination; Source cites §2 What it must do lines and business rules, never designs. *minor*
