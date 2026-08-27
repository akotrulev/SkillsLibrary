---
name: design-ux-review
description: Use when reviewing a built UI, screenshot, mockup, or Figma flow at EXPERIENCE altitude — captures its own evidence (Playwright screenshot per primary task), then Nielsen's 10 heuristics, flow friction (steps-to-goal, dead ends), IA sanity, and the responsiveness budget — checked against the initiative's `experience-plan.md` where one exists — output is a severity-tabled findings list, no rewrites. Triggers "review the UX", "heuristic evaluation", "is this flow confusing", "usability audit", "why does this feel clunky". Not for code-level UI audit (`design-ui-code-audit`), a11y scans (qa `accessibility-testing`), or copy voice (`design-ux-writing`).
---

# UX heuristics — experience-level review

Reviews a design or a built UI at **experience altitude**: is the flow usable, is the information architecture predictable, does the interface follow the well-established usability heuristics — independent of whether the code is clean. The failure mode this prevents is a build that passes every code lint, ships every `data-testid`, scores green on a11y scans, and is still confusing to *use*: a five-step path that should be two, a dead end with no back-button, a destructive action guarded by a modal where an undo would serve better, a label that means one thing here and another there.

**What this skill owns:** the heuristic evaluation (Nielsen's 10 as review questions), flow-friction review, and IA sanity, delivered as a findings table under the house severity scale. **What it does not own:** the *code-level* UI-guideline audit ([`design/ui-code-audit`](../ui-code-audit/SKILL.md) stays at the code layer — this is the experience layer above it), automated **accessibility scanning** (a stack's / qa `accessibility-testing` runs axe/Lighthouse; this only flags a usability *heuristic* an a11y scan can't see, e.g. "no visible focus path through this flow"), **bug** hunting (qa `exploratory-charter-writer` charters an exploratory session to find *defects* — this judges the *experience* of a build that already works), copy *voice* ([`design/ux-writing`](../ux-writing/SKILL.md)), and visual *taste* ([`design/visual-identity`](../visual-identity/SKILL.md)).

## When to use

- Reviewing a design plan, a mockup, or a built UI for usability before it ships.
- A flow "feels clunky" and you need to locate *where* and *why*, not just sense it.
- Deciding whether an interaction is over-guarded (a confirm where undo fits) or under-guarded (a destructive action with no safety).
- Auditing information architecture: nav is too deep, labels don't predict what's behind them, users can't tell where they are.
- Running a heuristic evaluation as a structured pass rather than an ad-hoc "does this look right".

## The review contract

Same as the rest of the library: **you find and locate problems; you do not rewrite the design.** Output is a findings table. Point to the fix, let the human apply it.

```
| Severity | Location            | Heuristic / issue              | Suggested fix                          |
|----------|---------------------|--------------------------------|----------------------------------------|
| major    | Checkout, step 3    | Error prevention (#5)          | Validate card inline before submit      |
| minor    | Settings > Account  | Consistency (#4)               | "Delete" here, "Remove" elsewhere — pick one |
```

Severities are the house scale (see `CLAUDE.md`): **blocker** (the user cannot complete the task, or loses data), **major** (a friction that will hurt users soon — a heuristic clearly violated on a primary flow), **minor** (a smaller inconsistency or friction), **nit** (optional polish). Rank a finding by its impact on the *user's task*, not by how offended the heuristic feels.

Best practice from the discipline: a heuristic evaluation catches more when **run as several independent passes** — 3–5 evaluators find ~60% of issues one finds far fewer of. When you review alone, make **two deliberate passes** (once free-exploring the flow, once walking the checklist) rather than one, and note the primary user tasks you evaluated so coverage is legible.

## Capture the evidence

A review without evidence is an opinion. Before the first heuristic:

1. **Name the primary user tasks** you will walk (from the brief, or from `docs/plans/<NNN>-*/experience-plan.md`'s actors & tasks where the initiative has one).
2. **Capture each task end to end.** With a running app, drive it through the Playwright MCP and take one screenshot per screen in the task's path, at the desktop and the narrowest supported width. Without one, use the user-supplied screenshots / mockup / Figma frames and say so.
3. **Record what was captured** in the report header — tasks walked, screens seen, widths — so the coverage is legible and a screen you never reached is not silently "passed".

**Where an `experience-plan.md` exists it is the reference, not the build.** Every IA or steps-to-goal finding names the plan decision the build contradicts — the screen id (`S4`), the nav-map row, the journey's step count — and a build that matches a plan decision you would have flagged is a finding *against the plan*, routed to `be-planner`, not against the build.

## Nielsen's 10 heuristics, as review questions

Walk each defined user task against these. Each is a question you answer with a finding or a pass:

1. **Visibility of system status** — Does every action give immediate, visible feedback? Is a loading/saving/failed state always shown (never a frozen or blank region)? Does the user always know where they are and what's happening?
2. **Match between system and the real world** — Is the language the user's, not the system's/jargon? Do concepts, ordering, and metaphors match how the user thinks about the task?
3. **User control and freedom** — Is there a clearly marked exit from every state (back, cancel, close)? Can the user **undo/redo**? Is there an escape from a mistake without dead-ending?
4. **Consistency and standards** — Do the same words, patterns, and interactions mean the same thing everywhere (internal consistency)? Do they follow platform/web conventions the user already knows (external)? *(One-name-one-concept is the IA face of `ux-writing`'s rule — cross-check there.)*
5. **Error prevention** — Do constraints, good defaults, and confirmation-of-consequence stop the error *before* it happens? Are slips (accidental) and mistakes (wrong-intent) both designed against? Prevention beats a good error message.
6. **Recognition rather than recall** — Are options, actions, and needed information **visible** rather than something the user must remember from a previous screen? Is context carried forward so nothing must be memorized across steps?
7. **Flexibility and efficiency of use** — Are there accelerators (shortcuts, saved defaults, bulk actions) for frequent/expert users that don't get in the novice's way? Can common tasks be done faster on repeat?
8. **Aesthetic and minimalist design** — Does each screen carry only what's relevant to its task? Is secondary information behind progressive disclosure rather than competing with the primary action? *(This is the usability face of restraint; visual taste is `visual-identity`.)*
9. **Help users recognize, diagnose, and recover from errors** — Do error messages say, in plain language, **what happened and how to fix it** (not a code)? Do they point at the offending field/action? *(Message wording is `ux-writing`; whether the recovery *path* exists is here.)*
10. **Help and documentation** — Where help is needed, is it contextual, findable, task-oriented, and concise? (The best system needs little; where the task is inherently complex, help must exist and be reachable in-context.)

## Flow-friction review

Beyond the ten, walk each primary task end to end and measure the *path*:

- **Steps-to-goal.** Count the actions to complete the core task. Flag every step that isn't load-bearing — a screen that only forwards, a confirm that guards nothing, a field that could be defaulted or inferred. The shortest correct path is the target.
- **Dead ends.** Every screen must offer a forward action *and* a way out. A state the user can enter but not leave (a form with no cancel, a result with no next step, an empty state with no call to action) is a friction at minimum, a blocker if it traps the task.
- **Back-button safety.** Browser/OS back and in-app back must not lose work, double-submit, or land the user somewhere incoherent. A flow that punishes back is broken even if forward works.
- **Undo over confirm, where the action is reversible.** A confirmation dialog interrupts *every* use to guard against the *rare* mistake; an undo affordance lets the common case flow and still catches the mistake. Reserve confirmations for the genuinely irreversible (delete-with-no-recovery, send, pay) — and there, confirm **by object name** (defer the confirmation-copy mechanics to `ux-writing` / a stack's `ui-rules`). Flag reversible actions that block behind a modal.
- **State legibility.** At any point the user should be able to answer "where am I, what just happened, what can I do next" without guessing.

## Responsiveness pass

Perceived speed is part of the experience; the budget is [`design/ux-patterns`](../ux-patterns/SKILL.md) §9, here as review questions:

- **Does every press acknowledge within ~100 ms** — a pressed state, a submit button that disables and shows in-flight — or does the user click twice?
- **Does a load show a skeleton shaped like the content**, in its region, or a blank / a page-centre spinner?
- **Does a long load say it is alive** at ~4 s, and does a failure land in the region with a retry rather than blanking the page?
- **Does anything shift** when content arrives — a header that jumps, a table that pushes the toolbar?
- **Is optimism used where reversible** (toggle, star, reorder) **and nowhere irreversible** (pay, send, delete)?
- **Does one region's wait block the page?** Independent regions load independently; the shell renders at once.

## IA sanity

- **Nav depth.** Primary destinations should be reachable shallowly; a task buried three-plus levels deep, or reachable only by a path the user won't guess, is a finding. Prefer breadth the user can scan over depth they must remember.
- **Label predictability.** A nav label must predict what's behind it — the user should choose correctly on the first try. Vague, clever, or overloaded labels ("More", "Manage", "Tools") that could hold anything are friction. *(The wording discipline is `ux-writing`; whether the label *predicts its destination* is the IA question here.)*
- **One name, one concept.** The same concept carries one name across nav, headings, breadcrumbs, and buttons; one name never covers two concepts. (Shared with `ux-writing`'s and `ui-rules`' one-name-one-concept rule — this is the navigation-structure face of it.)
- **You-are-here.** The current location is always indicated (active nav state, breadcrumb, title) so the user has a mental map.

## Review checklist

- **Evidence captured** — tasks walked, screens seen, widths — before any judgement; the report says what was and was not reached.
- **Two passes**, primary user tasks named, each task walked against **all ten heuristics** — findings, not vibes.
- **Responsiveness measured** against the §9 budget: press feedback, skeletons, the ~4 s acknowledgement, no layout shift, optimism only where reversible.
- **Plan referenced** where `experience-plan.md` exists — each IA / steps-to-goal finding names the screen id or nav-map row it contradicts.
- **Flow measured:** steps-to-goal minimized, no dead ends, back-button safe, **undo preferred over confirm** for reversible actions, state always legible.
- **IA checked:** nav shallow and scannable, labels predict destinations, one-name-one-concept holds, you-are-here always shown.
- **Output is a findings table** (severity / location / heuristic / suggested fix) on the **house severity scale** — **no rewrites**, each finding ranked by user-task impact.
- **Scope respected:** code-level audit left to `ui-code-audit`, a11y *scanning* to `accessibility-testing`, *bug* hunting to `exploratory-charter-writer`, copy *wording* to `ux-writing`, visual *taste* to `visual-identity` — this skill flags the *experience*.

## Related

- [`design/ux-patterns`](../ux-patterns/SKILL.md) — the **generative** counterpart: the IA, shell, page-anatomy and responsiveness decisions this review judges a build against; `be-shared-experience-plan` carries them per initiative.
- [`design/ui-code-audit`](../ui-code-audit/SKILL.md) — the **code-level** UI audit one layer below this; this reviews the experience, that reviews the implementation.
- [`design/ux-writing`](../ux-writing/SKILL.md) — owns the **wording** of labels, errors, and confirmations this review judges the *structure* of; shares the one-name-one-concept rule.
- [`design/visual-identity`](../visual-identity/SKILL.md) — owns **visual taste**; heuristic #8 (minimalism) is the usability face of its restraint discipline.
- A stack's `ui-rules` ([Blazor](../../frontend/blazor/skills/ui-rules/SKILL.md) · [React](../../frontend/react/skills/ui-rules/SKILL.md)) — owns the confirmation-by-object-name and empty-state *mechanics* this review defers to.
- A stack's / qa `accessibility-testing` — runs the **automated** a11y scans; this only flags usability heuristics a scanner can't see.
- qa `exploratory-charter-writer` — charters an exploratory session to find **defects**; this judges the **experience** of a build that already works.
