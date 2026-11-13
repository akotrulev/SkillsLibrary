---
paths:
  - "docs/plans/**/stories.md"
---

<!-- business-analysis rules v2 (2026-11-13): stories. Installed by /business-analysis:rules; edit to fit this project. -->

# Story standards

For `docs/plans/<NNN>-<initiative>/stories.md`, and the checklist `business-analysis:story-review` applies to any backlog. Severity: **blocker** the story cannot proceed, **major** will hurt soon, **minor** format or naming, **nit** preference. The template, the worked example and the know-how are `business-analysis:stories`'s.

- Each story is `## US<n> — <the feature's name>` with `**Epic:** E<n>`. Ids run flat across the initiative, never restart per epic and are never renumbered; a dropped story keeps its id with a line saying why. *blocker*
- A story is one feature a person would name, with one goal. Two goals are two stories. *major*
- A story is whole: every part its goal needs is inside it. A part that is no use without another (login with no way to register) is a fragment: merge it into its feature. *major*
- A technical task, or one layer of a feature ("the API", "the screen"), is not a story. *major*
- The sections, in order: Goal, How we get there, What is included, Acceptance criteria, Not included, Depends on, Source. *minor*
- The goal says who needs the feature, what they can do once it is built and why that matters to them or the business. A goal that only names the feature, or matters only to the system, is no goal. *blocker*
- The person is specific ("a member with a confirmed account"), never a bare "user". *major*
- How we get there is the plan in the product's own terms: the approach chosen and over what, what it builds on, the order of the parts, decisions already taken. Restating the goal is not a plan. *major*
- No technology anywhere: no table, endpoint, screen, component or library. A constraint the business imposed is cited from requirements.md §5, not restated. *major*
- What is included lists every part with what it does. Each part is something a person does or something that happens for them. Every requirements.md §4 capability the story covers appears as a part. *major*
- Acceptance criteria are bullets, each a condition that is true when the story is done. They are not Given / When / Then scenarios. *minor*
- Each criterion can be marked met or not met by someone who did not write it. One that restates a part's name ("login works") or says "the user can do X" with no check is untestable. *blocker*
- One situation per criterion, with its outcome; a criterion that walks through several steps or situations is split. *major*
- Every included part has criteria for it working and for what happens when it cannot (wrong input, expired, refused, already done). A part with no criterion is unproven. *major*
- Criteria are `AC1..ACn`, flat within the story and grouped under the part they prove; whole-feature ones (security, accessibility, audit, speed) under `Across the feature`. Cited downstream as `US<n> AC<k>`: never reused or renumbered, and a dropped one keeps its id with a line saying why. *major*
- A validation states field, rule and outcome on violation. No unfalsifiable word ("fast", "secure", "user-friendly", "recently") without a number. *major*
- A number is a business rule from the requirements. One the requirements do not give is `[TBD — <who decides>]` and an open question, never invented. *blocker*
- A contradiction between criteria, or between the story and its epic, is a finding, never silently resolved. *blocker*
- Not included is listed per story, each item with its reason and where it goes. *minor*
- Dependencies by story id (`Depends on: US<n>`, or none); an undeclared one is a finding. *major*
- Source cites the requirements.md §4 lines and business rules, never designs or contracts. *minor*
