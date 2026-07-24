---
name: ba-story-writer
description: Use when the user wants to convert a scoped requirement or BA writeup into INVEST user stories with acceptance criteria. Separates functional from non-functional acceptance criteria. Triggers: "write user stories for X", "turn this into stories the team can pick up", "add acceptance criteria to this story", "write the Jira tickets for this", "write this as an 'as a user, I want' story", "split this epic", "add the non-functional AC". Do NOT use for high-level scoping (`ba-initiative-scoping`), test cases (qa/manual/test-case-writer), or bug reports (qa/manual/bug-report-writer).
---

# User Story Writer

Turns a scoped requirement into a set of INVEST-quality user stories with Gherkin-style acceptance criteria. Stories are sized for one team, one sprint, and one deployable slice.

## When to use

- BA writeup is done and ready to refine into stories
- An epic needs splitting before refinement
- Existing stories lack acceptance criteria or are too large

## When NOT to use

- Requirement is still vague → `business-analysis/skills/ba-initiative-scoping` first
- Stories were authored elsewhere and need a review-only readiness audit → `business-analysis/skills/ba-backlog-auditor` (this skill *fixes* stories; that one only *finds*)
- User wants test scripts → `qa/manual/test-case-writer`
- User wants a defect filed → `qa/manual/bug-report-writer`

## Inputs needed

1. **The scoped requirement or BA writeup** (link or paste)
2. **The user role(s)** the story is for (be specific — "logged-in admin", not "user")
3. **Definition of Done** the team uses (if non-standard)
4. **Known constraints** that affect splitting (deployment cadence, feature flags, dependencies)

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
   - Interface (API before UI, or vice versa per team contract)
4. **Acceptance criteria in Gherkin.** `Given / When / Then`. One scenario per criterion. No `And` chains that hide multiple behaviors.
5. **Separate functional AC from non-functional AC.** Performance, accessibility, audit logging — these are AC too, just labeled.
6. **Out-of-scope list at the story level**, not just the epic. Reviewers will assume it's in scope otherwise.
7. **Dependencies are explicit.** "Blocked by #123" beats discovering it at standup.

## Output format

```markdown
## Story: <short title>

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
- Blocked by: <story / ticket>
- Related: <story / ticket>

### Notes
<implementation hints, links to designs, API contracts — anything reviewers need>
```

## Anti-patterns to flag

- **"As a user" with no role.** Every system has multiple roles; pick one.
- **"So that the system can..."** — value flows to a *person*, not the system.
- **AC that restates the story.** "Then the user can do X" with no observable check.
- **Story that contains both API and UI work for the same capability.** Usually a split candidate.
- **AC list with `And` chaining 5 behaviors.** Each one is a separate scenario.
- **Story that can't be demoed.** If there's nothing to show the stakeholder, it isn't a user story — it's a technical task.

## Handoffs

- Tests next → `qa/manual/test-basis-analyzer` first (distills the stories' business logic, validations, and observable implementation notes into the test basis), then `qa/manual/test-case-writer`; or hand the whole flow to `qa/manual/agents/qa-manual-test-designer`
- API contracts next → `qa/<stack>/skills/api-dto-writer`
- Page objects / UI tests → `qa/<stack>/skills/page-object-architect` then `qa/<stack>/skills/ui-test-author`
