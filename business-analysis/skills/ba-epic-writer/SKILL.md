---
name: ba-epic-writer
description: Use when converting a scoped business-analysis writeup into one or more epics — sized for a release/quarter, sliced into user stories, with measurable outcomes. Triggers: "write an epic for X", "slice this BA writeup into epics", "size this initiative into a quarter". Do NOT use for high-level scoping (`ba-initiative-scoping`) or individual stories with AC (`ba-story-writer`).
---

# Epic Writer

Closes the **BA → Epic → Story** chain. Takes a scoped business-analysis writeup and produces one or more epics: each sized for a release or quarter, with a clear outcome, a slicing strategy, an enumeration of child stories, and explicit out-of-scope. Epics are the negotiation surface with product and engineering leadership — bigger than a sprint, smaller than a roadmap.

## When to use

- BA writeup is done and the initiative is too big for stories — needs an epic shape first
- An existing "mega-story" needs splitting into epics + stories
- A roadmap item needs to become refinement-ready
- Multiple teams will touch the same outcome — epics align them around a shared "done"

## When NOT to use

- Vague requirement, no scope yet → `business-analysis/skills/ba-initiative-scoping` first
- Scoped requirement, ready for stories → `business-analysis/skills/ba-story-writer`
- Status update to stakeholders → `communication/stakeholder-updates`
- A single sprint-sized piece of work → write a story, not an epic

## Inputs needed

1. **BA writeup or scoped problem statement** (the `business-analysis` output, ideally)
2. **Release window / quarter / OKR** the epic should fit into
3. **Teams involved** and their dependencies
4. **Success metric(s)** for the epic — measurable, not "improve UX"
5. **Constraints** that affect slicing — feature flags, deployment cadence, contract changes, compliance
6. **Known dependencies** — work that must complete before, or in parallel with

## Procedure

1. **An epic has exactly one outcome.** If you can't write the outcome in one sentence using a user / business term and a measurable change, it's two epics.
2. **Slice by outcome, then by team.** Two epics each delivering a shippable outcome beat one epic where Team A blocks Team B for two months.
3. **Spell out the value increment.** What's better for the user or business when the epic is done vs at the start. Vague "platform improvements" with no outcome is a tech-debt item, not an epic.
4. **Time-box explicitly.** Epics that take a quarter end exactly when planned, never longer. If the epic threatens to exceed the timebox, split or descope — never extend the timebox silently.
5. **Slicing strategy first, story enumeration second.** Pick a slicing axis (workflow steps, user roles, data variations, CRUD, vertical slices by feature flag) and stick to it across child stories.
6. **Every epic ships a thin vertical slice.** "Read-only API + UI for the new entity" is a valid first epic; "API only" or "UI only" is usually wrong because nothing ships to a user.
7. **Out-of-scope is part of the epic.** What is *deliberately* deferred to a follow-up epic, with the reason.
8. **Risks at the epic level**, not just per story. A risk that affects the whole initiative needs naming early.

## Output format

```markdown
# Epic: <short, outcome-shaped title>

**Owner:** <name / squad>   **Status:** Draft / Approved / In progress / Done
**Target window:** <quarter / release / date range>
**Linked BA:** <link to BA writeup>

## 1. Outcome (one sentence)
When this epic is done, **<who>** can **<do what>** so that **<measurable change>**.

## 2. Why now
<1–3 sentences: why this quarter, what costs not doing it>

## 3. Success metrics
- **Primary:** <metric with baseline → target> (e.g. "Time-to-first-export drops from 4 min to <1 min for 80% of users")
- **Secondary:** <metric>

## 4. Slicing strategy
<one paragraph naming the axis: workflow / role / CRUD / data variation / feature-flag rollout — and why this axis was chosen>

## 5. Child stories (anticipated)
| # | Story | Slice | Sprint guess |
|---|-------|-------|--------------|
| 1 | Read-only list endpoint + minimal UI | First slice (read) | S1 |
| 2 | Create flow with validation | Add write | S1–S2 |
| 3 | Bulk operations | Data variation | S2 |
| ... | ... | ... | ... |

These are enumerated, not committed — refinement will produce the real INVEST stories via `business-analysis/skills/ba-story-writer`.

## 6. In scope / out of scope / deferred
| In scope | Out of scope | Deferred (next epic) |
|----------|--------------|----------------------|

## 7. Dependencies
- **Blocked by:** <epic / team / external>
- **Blocks:** <epic / team>
- **Parallel:** <epic that touches the same area; coordinate>

## 8. Risks
| Risk | L | I | Mitigation |
|------|---|---|------------|

## 9. Cross-team contracts
<APIs / message schemas / feature flags / data shapes that must be agreed before stories start — link to design docs>

## 10. Definition of Done (epic-level)
- [ ] Primary success metric measurable + measured in prod
- [ ] All in-scope stories `Done`
- [ ] Out-of-scope explicitly handed to the next epic or accepted as won't-do
- [ ] Runbook / docs updated
- [ ] Stakeholder update posted

## 11. Handoffs
- Per-story refinement → `business-analysis/skills/ba-story-writer`
- Release / steerco update → `communication/stakeholder-updates`
- API contract scaffolds → `qa/<stack>/skills/api-dto-writer`
- Test strategy for the epic → `qa/manual/test-strategy`
```

## Anti-patterns to flag

- **Tech-only outcome.** "Migrate to v3 of the library" is not an epic outcome unless you can name the user-facing benefit and metric. Otherwise it's a tech-debt task on a roadmap.
- **Outcome-less epic.** "Improvements to the orders area" — what improves, by how much?
- **God epic.** Three quarters of work, ten dependencies, no slicing — it's a program, not an epic; needs to be split.
- **Time-box drift.** "Originally Q1, slipped to Q3, still tracking" — at slip #2, replan as two epics with new time-boxes.
- **Slice that ships nothing.** An "API-only" first slice with no UI for two months means nothing ships to a user. Pull in the thinnest UI.
- **Stories pre-committed in the epic.** Story sizing happens in refinement; the epic enumerates *anticipated* stories, with permission to revise.
- **Out-of-scope = "not in the epic"**, no rationale. Each deferred item needs a one-liner on why.
- **No success metric**, or success = "ship the epic". Shipping is not a metric.
- **Risks copy-pasted from the BA writeup.** Epics introduce new risks (sequencing, parallel work, contract drift) — surface those, don't just inherit.

## Examples — outcome shapes

| ✅ Strong | ❌ Weak |
|---|---|
| When this epic is done, **finance ops** can **reconcile partner payouts** so that **monthly reconciliation drops from 5 days to <1 day** | We will improve the payouts area |
| When this epic is done, **mobile users** can **complete onboarding offline** so that **drop-off on Signup step 3 falls from 22% to <10%** | Offline support for mobile |
| When this epic is done, **support agents** can **issue partial refunds in one click** so that **refund time-to-resolution p95 drops from 12 min to <3 min** | Refund flow improvements |

The pattern: **WHO** + **CAN DO WHAT** + **SO THAT MEASURABLE CHANGE**. If any of the three is missing, the epic isn't ready.

## Sizing heuristics

| Symptom | Likely size |
|---|---|
| Fits one team, ~4–8 stories, ~1 sprint | **Too small for an epic** — write stories directly |
| Fits one team, ~10–30 stories, 1 quarter | **Right size** for an epic |
| Two+ teams, contract changes, multiple deploy windows | **One epic per team** under a shared theme; coordinate via a brief "program" doc |
| Three+ teams, multi-quarter | **Roadmap initiative** — split into per-quarter epics; each epic has its own outcome |

## Rules

- One outcome per epic, written in WHO / DO WHAT / SO THAT MEASURABLE CHANGE form
- Time-box explicit; slip = replan, never silent extension
- Slicing strategy named (workflow / role / CRUD / data / flag) — applied consistently across stories
- Every epic ships an end-to-end user-visible slice in its first 2–3 stories
- Out-of-scope itemized, each with rationale and pointer to the follow-up
- Success metric measurable and committed (baseline + target)
- Dependencies named bidirectionally (blocked-by, blocks, parallel)
- Risks owned at the epic level, with mitigation
- Definition of Done is binary checklist — no subjective items
- Story enumeration is *anticipated*, not committed — refinement produces the real INVEST stories

## What NOT to do

- No epics without measurable success metrics
- No "platform improvements" epics with no user-facing outcome
- No "API only" or "UI only" first slice unless explicitly time-boxed and the followup is in the same release window
- No silent time-box extensions; replan instead
- No copy-pasted risks from the BA writeup — add epic-level risks
- No DoD items like "tested" — say *which* tests, by which gate (`qa/manual/test-strategy`)
- No epic written for the team's convenience that produces nothing for the user (re-orgs of code that doesn't ship value)
- No mixing two outcomes in one epic — they are two epics
- No epic without a named owner

## Generation steps

1. Read the BA writeup; refuse to start if the BA is unscoped or has no measurable success criterion (point user back to `business-analysis/skills/ba-initiative-scoping`)
2. Draft the one-sentence outcome — iterate with the user until WHO / DO WHAT / SO THAT MEASURABLE CHANGE all pass the sniff test
3. Pick the slicing strategy
4. Enumerate child stories (titles + slice + rough sprint guess) — note these are anticipated, not committed
5. Mark in-scope / out-of-scope / deferred with rationale
6. Surface epic-level risks and dependencies
7. Write the Definition of Done as a binary checklist
8. Hand off to `business-analysis/skills/ba-story-writer` for the first 2–3 stories

## Handoffs

- Up-stream (vague requirement) → `business-analysis/skills/ba-initiative-scoping`
- Down-stream (story refinement) → `business-analysis/skills/ba-story-writer`
- Epics/stories authored elsewhere need a readiness audit → `business-analysis/skills/ba-backlog-auditor`
- Stakeholder update during execution → `communication/stakeholder-updates`
- Test plan for the epic → `qa/manual/test-strategy`
- API/DTO contracts that the epic depends on → `qa/<stack>/skills/api-dto-writer`
