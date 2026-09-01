---
name: ba-story-writer
description: Use when the user wants to convert a scoped requirement or BA writeup into INVEST user stories with acceptance criteria. Separates functional from non-functional AC. Triggers: "write user stories for X", "turn this into stories the team can pick up", "add acceptance criteria to this story", "split this epic". Do NOT use for high-level scoping (`ba-scoping-writeup`), test cases (qa/manual/test-case-writer), or bug reports (qa/manual/bug-report-writer).
---

# User Story Writer

Turns a scoped requirement into a set of INVEST-quality user stories with Gherkin-style acceptance criteria. Stories are sized for one team, one sprint, and one deployable slice.

## When to use

- BA writeup is done and ready to refine into stories
- An epic needs splitting before refinement
- Existing stories lack acceptance criteria or are too large

## When NOT to use

- Requirement is still vague → `business-analysis/skills/ba-scoping-writeup` first
- Stories were authored elsewhere and need a review-only readiness audit → `business-analysis/skills/ba-story-quality-review` (this skill *fixes* stories; that one only *finds*)
- User wants test scripts → `qa/manual/test-case-writer`
- User wants a defect filed → `qa/manual/bug-report-writer`

## Inputs needed

1. **The epics** (`epics.md` from `ba-epic-writer`, ideally) and the requirements document they cover
2. **The user role(s)** the story is for (be specific — "logged-in admin", not "user")
3. **Known constraints** that affect splitting (a stated delivery window, compliance sequencing, dependencies)

## Procedure

1. **Story format is "As a / I want / So that".** The "so that" is mandatory — it carries the *why*. If you can't write it, the story doesn't belong yet.
2. **Apply INVEST on every story:**
   - **I**ndependent — can ship without other stories in the same set
   - **N**egotiable — describes intent, not implementation
   - **V**aluable — the "so that" passes a stakeholder sniff test
   - **E**stimable — team has enough info to size
   - **S**mall — fits one sprint with margin
   - **T**estable — acceptance criteria are objectively verifiable
3. **Split using a real strategy, not "split because it's too big":**
   - Workflow steps (happy path → edge cases → error handling)
   - User roles (admin first, then end-user)
   - Data variations (single record → bulk → import)
   - CRUD operations (read before write before delete)

   **Never by layer.** "The API" and "the screen" are not stories — a story that ships one side of a capability cannot be demoed, so it fails INVEST on its own terms. Layers are cut later, at task level, by the planner; a story stays whole.
4. **Acceptance criteria in Gherkin.** `Given / When / Then`. One scenario per criterion. No `And` chains that hide multiple behaviors.
5. **Separate functional AC from non-functional AC.** Performance, accessibility, audit logging — these are AC too, just labeled.
6. **Out-of-scope list at the story level**, not just the epic. Reviewers will assume it's in scope otherwise.
7. **Dependencies are explicit**, by story id. "Depends on: US3" beats discovering it at standup.
8. **Every story carries an id and its parent epic.** Ids are `US1..USn`, flat across the initiative (never restarted per epic); the parent is its `E` id. Ids are assigned once and never renumbered — downstream plans and prompts cite them. A dropped story keeps its id with a line saying why.

## Output format

```markdown
## US<n> — <short title>

**Epic:** E<n>

**As a** <specific role>
**I want** <capability>
**So that** <outcome / why>

### Acceptance criteria

**Functional**
- [ ] Given <context>, when <action>, then <outcome>
- [ ] Given <context>, when <action>, then <outcome>

**Non-functional**
- [ ] <Performance / accessibility / security / audit criterion>

### Out of scope
- <explicit exclusion>

### Dependencies
- Depends on: US<n> (<what it provides>) — or none
- Related: US<n>

### Source
<the requirements.md §4 lines and business rules this story realises — never implementation hints, designs or contracts; those are solution-planner's>
```

**No technology in a story.** No table, endpoint, screen, component or library — the AC describe what a person observes. A business-imposed constraint lives in `requirements.md` §5 and is cited, not restated.

## Anti-patterns to flag

- **"As a user" with no role.** Every system has multiple roles; pick one.
- **"So that the system can..."** — value flows to a *person*, not the system.
- **AC that restates the story.** "Then the user can do X" with no observable check.
- **Story that ships only one layer of a capability** ("the endpoint", "the screen"). It cannot be demoed; merge it back into the capability it belongs to.
- **AC list with `And` chaining 5 behaviors.** Each one is a separate scenario.
- **Story that can't be demoed.** If there's nothing to show the stakeholder, it isn't a user story — it's a technical task.

## Handoffs

- Inside the delivery lane → `requirements-author` (`/dev-refine`) runs this skill as its Step 4 and writes the output to `docs/plans/<NNN>-<initiative>/stories.md`; the `business-analyst` sweep follows when the stories change shared business rules
- Tests next → `qa/manual/requirements-breakdown` first (distills the stories' business logic, validations, and observable implementation notes into the test basis), then `qa/manual/test-case-writer`; or hand the whole flow to `qa/manual/agents/qa-test-case-designer`
- Architecture, contracts, task plan → `solution-planner` (`/dev-plan-solution`)

Only `qa/manual/requirements-breakdown` ships in this plugin; the other `qa/*` peers and `solution-planner` are invoked separately, never loaded here.
