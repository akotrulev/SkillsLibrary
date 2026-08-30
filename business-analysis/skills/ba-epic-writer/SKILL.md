---
name: ba-epic-writer
description: Use when converting a scoped business-analysis writeup into one or more epics — sized for a release/quarter, sliced into user stories, with measurable outcomes and a plain-English section (user-story line, what gets built, how it fits with everything else) carrying no technology at all. Triggers: "write an epic for X", "slice this BA writeup into epics", "size this initiative into a quarter". Do NOT use for high-level scoping (`ba-scoping-writeup`) or individual stories with AC (`ba-story-writer`).
---

# Epic Writer

Closes the **BA → Epic → Story** chain. Takes a scoped business-analysis writeup and produces one or more epics: each sized for a release or quarter, with a clear outcome, a slicing strategy, an enumeration of child stories, and explicit out-of-scope. Epics are the negotiation surface with product and engineering leadership — bigger than a sprint, smaller than a roadmap.

## When to use

- BA writeup is done and the initiative is too big for stories — needs an epic shape first
- An existing "mega-story" needs splitting into epics + stories
- A roadmap item needs to become refinement-ready
- Multiple teams will touch the same outcome — epics align them around a shared "done"

## When NOT to use

- Vague requirement, no scope yet → `business-analysis/skills/ba-scoping-writeup` first
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
2. **Write the plain-English section before anything else, and write it first for a reason.** Section 2 is the epic in the language of the person who asked for it — a user-story line, what gets built, and how it fits with what already exists. It is not a summary of the sections below and not a translation of them: it is the epic as it was understood, and the rest of the document is the working-out. **If you cannot write it without naming a technology, you do not yet have an epic** — you have a technical task, and the fix is upstream in the scoping, not a better paragraph. Where it disagrees with a section further down, one of the two is wrong; find out which before shipping the epic.
3. **Slice by outcome, then by team.** Two epics each delivering a shippable outcome beat one epic where Team A blocks Team B for two months.
4. **Spell out the value increment.** What's better for the user or business when the epic is done vs at the start. Vague "platform improvements" with no outcome is a tech-debt item, not an epic.
5. **Time-box explicitly.** Epics that take a quarter end exactly when planned, never longer. If the epic threatens to exceed the timebox, split or descope — never extend the timebox silently.
6. **Slicing strategy first, story enumeration second.** Pick a slicing axis (workflow steps, user roles, data variations, CRUD, vertical slices by feature flag) and stick to it across child stories.
7. **Every epic ships a thin vertical slice.** "Read-only API + UI for the new entity" is a valid first epic; "API only" or "UI only" is usually wrong because nothing ships to a user.
8. **Out-of-scope is part of the epic.** What is *deliberately* deferred to a follow-up epic, with the reason.
9. **Risks at the epic level**, not just per story. A risk that affects the whole initiative needs naming early.

## Output format

```markdown
# Epic: <short, outcome-shaped title>

**Owner:** <name / squad>   **Status:** Draft / Approved / In progress / Done
**Target window:** <quarter / release / date range>
**Linked BA:** <link to BA writeup>

## 1. Outcome (one sentence)
When this epic is done, **<who>** can **<do what>** so that **<measurable change>**.

## 2. In plain English
<!-- No technology anywhere in this section. No table, endpoint, service, component, library,
     queue or framework — not even by implication. If it cannot be written without one, the
     epic is a technical task wearing an epic's clothes. -->

**As a** <actor>, **I want** <the thing they want>, **so that** <why they want it>.

**What gets built**
<2–4 sentences describing what will exist, told the way you would tell the person who is going
to use it. What they will be able to do that they cannot do today, and what it will feel like
to do it. No mechanism, no numbers — the outcome line above carries the measurement.>

**How it fits with everything else**
<2–4 sentences placing this epic in the whole. What already exists that this leans on, what it
adds to, what becomes possible afterwards that was not before, and which other epics a person
would notice this one connecting to — named by what they are, not by their ids alone
("the timetable members already browse", not "E1"). Where the epic is the first of its kind in
the system, say that instead: what it establishes that nothing else has yet.>

## 3. Why now
<1–3 sentences: why this quarter, what costs not doing it>

## 4. Success metrics
- **Primary:** <metric with baseline → target> (e.g. "Time-to-first-export drops from 4 min to <1 min for 80% of users")
- **Secondary:** <metric>

## 5. Slicing strategy
<one paragraph naming the axis: workflow / role / CRUD / data variation / feature-flag rollout — and why this axis was chosen>

## 6. Child stories (anticipated)
| # | Story | Slice | Sprint guess |
|---|-------|-------|--------------|
| 1 | Read-only list endpoint + minimal UI | First slice (read) | S1 |
| 2 | Create flow with validation | Add write | S1–S2 |
| 3 | Bulk operations | Data variation | S2 |
| ... | ... | ... | ... |

These are enumerated, not committed — refinement will produce the real INVEST stories via `business-analysis/skills/ba-story-writer`.

## 7. In scope / out of scope / deferred
| In scope | Out of scope | Deferred (next epic) |
|----------|--------------|----------------------|

## 8. Dependencies
- **Blocked by:** <epic / team / external>
- **Blocks:** <epic / team>
- **Parallel:** <epic that touches the same area; coordinate>

## 9. Risks
| Risk | L | I | Mitigation |
|------|---|---|------------|

## 10. Cross-team contracts
<APIs / message schemas / feature flags / data shapes that must be agreed before stories start — link to design docs>

## 11. Definition of Done (epic-level)
- [ ] Primary success metric measurable + measured in prod
- [ ] All in-scope stories `Done`
- [ ] Out-of-scope explicitly handed to the next epic or accepted as won't-do
- [ ] Runbook / docs updated
- [ ] Stakeholder update posted

## 12. Handoffs
- Per-story refinement → `business-analysis/skills/ba-story-writer`
- Release / steerco update → `communication/stakeholder-updates`
- API contract scaffolds → `qa/<stack>/skills/api-models`
- Test strategy for the epic → `qa/manual/test-strategy`
```

## Anti-patterns to flag

- **A plain-English section with technology in it.** "Members will be able to book from the new sessions endpoint" is the technical epic again, one layer down. Name what the person does, never what serves it.
- **A plain-English section that is a summary of the sections below.** It restates the slicing strategy and the story list in softer words and tells the reader nothing they could not get from the table. The section exists to say what is being built and how it connects — if it says neither, delete it and write it properly.
- **"How it fits" that only lists dependencies.** "Blocked by E1, blocks E4" is section 8's job and it is already there. This paragraph says what a person can do afterwards that they could not before, and what this leans on that already exists.
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

## Example — the plain-English section, filled

`E2 Booking`, from the workshop-booking initiative. Its outcome line reads *"When this epic is done,
**members** can **book and manage a place on a session** so that **no-show rate falls from 18% to
under 8%**"* — accurate, measurable, and not something you would read aloud to the studio owner.
Section 2 is what you would read aloud:

```markdown
## 2. In plain English

**As a** gym member, **I want** to reserve my place on a class and change my mind later,
**so that** I know I have a spot and the studio knows to expect me.

**What gets built**
A member browsing the timetable can take a place on any class that still has room, in one action,
and see straight away that it worked. Their own upcoming classes are collected in one place, so
they can check what they signed up for and drop out of something they can no longer make. If a
class fills up before they get to it, they are told that plainly rather than being allowed to
book and disappointed later.

**How it fits with everything else**
It builds directly on the timetable members can already browse — booking is the action that
timetable was missing, and it lives on the class the member is already looking at. It is also the
first thing in the system that belongs to an individual member rather than to the studio, which is
what the confirmation email later hangs off, and what makes a member's own history worth keeping.
Nothing the studio does to the timetable changes; staff still publish classes exactly as before.
```

Read what it does not contain: no endpoint, no table, no screen name, no capacity constraint, no
percentage. The measurement is in section 1, the mechanism is `solution-planner`'s, and the studio
owner can tell you whether this is the thing they asked for.

## Sizing heuristics

| Symptom | Likely size |
|---|---|
| Fits one team, ~4–8 stories, ~1 sprint | **Too small for an epic** — write stories directly |
| Fits one team, ~10–30 stories, 1 quarter | **Right size** for an epic |
| Two+ teams, contract changes, multiple deploy windows | **One epic per team** under a shared theme; coordinate via a brief "program" doc |
| Three+ teams, multi-quarter | **Roadmap initiative** — split into per-quarter epics; each epic has its own outcome |

## Rules

- One outcome per epic, written in WHO / DO WHAT / SO THAT MEASURABLE CHANGE form
- **Every epic carries its plain-English section** — the As-a / I-want / So-that line, what gets built, and how it fits with everything else — and that section names no technology at all
- **The "how it fits" paragraph names other epics by what they are**, not only by id, and says what becomes possible after this one that was not before
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

1. Read the BA writeup; refuse to start if the BA is unscoped or has no measurable success criterion (point user back to `business-analysis/skills/ba-scoping-writeup`)
2. Draft the one-sentence outcome — iterate with the user until WHO / DO WHAT / SO THAT MEASURABLE CHANGE all pass the sniff test
3. Write the plain-English section (§2): the As-a / I-want / So-that line, what gets built, how it fits. **Read it back with every technical noun removed** — if a sentence stops making sense, rewrite the sentence, do not reinstate the noun
4. Pick the slicing strategy
5. Enumerate child stories (titles + slice + rough sprint guess) — note these are anticipated, not committed
6. Mark in-scope / out-of-scope / deferred with rationale
7. Surface epic-level risks and dependencies
8. Write the Definition of Done as a binary checklist
9. Hand off to `business-analysis/skills/ba-story-writer` for the first 2–3 stories

## Handoffs

- Up-stream (vague requirement) → `business-analysis/skills/ba-scoping-writeup`
- Down-stream (story refinement) → `business-analysis/skills/ba-story-writer`
- Epics/stories authored elsewhere need a readiness audit → `business-analysis/skills/ba-story-quality-review`
- Stakeholder update during execution → `communication/stakeholder-updates`
- Test plan for the epic → `qa/manual/test-strategy`
- API/DTO contracts that the epic depends on → `qa/<stack>/skills/api-models`
