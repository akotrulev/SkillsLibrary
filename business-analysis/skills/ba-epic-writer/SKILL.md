---
name: ba-epic-writer
description: Use when converting a scoped requirements document into one or more epics — one capability-sized outcome each, sliced into user stories, with a measurable outcome and a plain-English section (user-story line, what gets built, how it fits) carrying no technology at all. Triggers: "write an epic for X", "slice this requirements doc into epics", "what are the epics for this initiative". Do NOT use for high-level scoping (`ba-scoping-writeup`) or individual stories with AC (`ba-story-writer`).
---

# Epic Writer

The middle of the **requirements → epics → stories** chain. Takes a scoped requirements document and produces one or more epics: each one capability a person gets, with a measurable outcome, a plain-English section, a slicing strategy, an enumeration of child stories, and explicit out-of-scope. **An epic is a capability, not a calendar unit.** Inside the delivery lane every initiative gets epics, however small — `E1..En` are what `solution-planner`'s epic map and delivery plan cite — so an initiative with one capability has one epic, never zero.

## When to use

- The requirements document is done and its capabilities (§4) need shaping into outcomes before stories are written
- An existing "mega-story" needs splitting into epics + stories
- A roadmap item needs to become refinement-ready
- Several people or teams will touch the same outcome — epics align them around a shared "done"

## When NOT to use

- Vague requirement, no scope yet → `business-analysis/skills/ba-scoping-writeup` first
- Epics exist and stories are the ask → `business-analysis/skills/ba-story-writer`
- Epics authored elsewhere need auditing, not shaping → `business-analysis/skills/ba-story-quality-review`

## Inputs needed

1. **The requirements document** (`requirements.md` from `ba-scoping-writeup`, ideally) — its §4 capabilities are what the epics cover, exactly once each
2. **Success measures** — from `requirements.md` §6, or the epic's own where one capability has its own signal
3. **Constraints that affect slicing** — from `requirements.md` §5; compliance, contractual sequencing, a deadline
4. **Known dependencies** — work that must complete before, or alongside
5. **Delivery window and teams**, only where the user has them — they shape sizing and the deferred column, never the outcome

## Procedure

1. **Write the plain-English section first.** Section 2 is the epic in the language of the person who asked for it — a user-story line, what gets built, and how it fits with what already exists. It is not a summary of the sections below and not a translation of them: it is the epic as it was understood, and the rest of the document is the working-out. **If you cannot write it without naming a technology, you do not yet have an epic** — you have a technical task, and the fix is upstream in the requirements, not a better paragraph. Where it disagrees with a section further down, one of the two is wrong; find out which before shipping the epic.
2. **Then the outcome line — an epic has exactly one.** If you can't write it in one sentence using a user / business term and a measurable change, it's two epics. Where the requirements carry no measure, the outcome line carries `[TBD — <who decides>]` in the measurable slot and the gap is the epic's first open question; never an invented number, and never a reason to stop.
3. **Slice by outcome, then by actor.** Two epics each delivering a usable capability beat one epic where one half blocks the other for two months.
4. **Spell out the value increment.** What's better for the user or business when the epic is done vs at the start. Vague "platform improvements" with no outcome is a tech-debt item, not an epic.
5. **Slicing strategy first, story enumeration second.** Pick a slicing axis (workflow steps, user roles, data variations, read-before-write) and stick to it across child stories.
6. **Every epic is usable end to end when done.** Its first stories deliver the thinnest complete capability a person can try; a slice a person cannot use is not a slice. Layers ("the API", "the screen") are never epics or stories — they are cut at task level by `solution-planner`.
7. **Out-of-scope is part of the epic.** What is *deliberately* deferred to a follow-up epic, with the reason.
8. **Risks at the epic level**, not just per story. A risk that affects the whole initiative needs naming early.
9. **Where a delivery window is stated, hold it.** An epic that threatens to exceed it is split or descoped — never silently extended.

## Output format

```markdown
# E<n> — <short, outcome-shaped title>

**Status:** Draft / Approved / In progress / Done
**Covers:** requirements.md §4 — <the capability lines this epic delivers>
**Delivery window:** <only where the user stated one; otherwise omit the line>

## 1. Outcome (one sentence)
When this epic is done, **<who>** can **<do what>** so that **<measurable change>**.

## 2. In plain English
<No technology anywhere in this section. No table, endpoint, service, component, library,
 queue or framework — not even by implication. If it cannot be written without one, the
 epic is a technical task wearing an epic's clothes. Delete this note in the written epic.>

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
<1–3 sentences: why this initiative, what not doing it costs>

## 4. Success measures
- **Primary:** <measure with baseline → target> (e.g. "Time-to-first-export drops from 4 min to <1 min for 80% of users")
- **Secondary:** <measure>

## 5. Slicing strategy
<one paragraph naming the axis: workflow / role / read-before-write / data variation — and why this axis was chosen>

## 6. Child stories (anticipated)
| # | Story | Slice |
|---|-------|-------|
| 1 | A member sees the classes they can book | First slice (read) |
| 2 | A member books a place on a class with room | Add the action |
| 3 | A member drops out of a class they booked | Data variation |
| ... | ... | ... |

These are enumerated, not committed — refinement produces the real INVEST stories via `business-analysis/skills/ba-story-writer`. Each line is something a person does, never a layer or a component.

## 7. In scope / out of scope / deferred
| In scope | Out of scope | Deferred (next epic) |
|----------|--------------|----------------------|

## 8. Dependencies
- **Blocked by:** <epic / external decision>
- **Blocks:** <epic>
- **Parallel:** <epic that touches the same capability; coordinate>

## 9. Risks
| Risk | L | I | Mitigation |
|------|---|---|------------|

## 10. Definition of Done (epic-level)
- [ ] Primary success measure is measurable, and measured once live
- [ ] All in-scope stories `Done`
- [ ] Out-of-scope explicitly handed to the next epic or accepted as won't-do
```

Nothing technical belongs in the document: no cross-team contract section, no API list, no data shapes. Those are `solution-planner`'s artifacts (`api-surface.md`, `data-model.md`) and they cite the epic, not the other way round.

## Anti-patterns to flag

- **A plain-English section with technology in it.** "Members will be able to book from the new sessions endpoint" is the technical epic again, one layer down. Name what the person does, never what serves it.
- **A plain-English section that is a summary of the sections below.** It restates the slicing strategy and the story list in softer words and tells the reader nothing they could not get from the table. The section exists to say what is being built and how it connects — if it says neither, delete it and write it properly.
- **"How it fits" that only lists dependencies.** "Blocked by E1, blocks E4" is section 8's job and it is already there. This paragraph says what a person can do afterwards that they could not before, and what this leans on that already exists.
- **Tech-only outcome.** "Migrate to v3 of the library" is not an epic outcome unless you can name the user-facing benefit and metric. Otherwise it's a tech-debt task on a roadmap.
- **Outcome-less epic.** "Improvements to the orders area" — what improves, by how much?
- **God epic.** Several capabilities, ten dependencies, no slicing — it's a program, not an epic; needs to be split.
- **Window drift.** "Originally Q1, slipped to Q3, still tracking" — at slip #2, replan as two epics.
- **Slice that ships nothing.** A first slice a person cannot use means nothing ships. Pull in the thinnest complete capability.
- **Stories pre-committed in the epic.** Story sizing happens in refinement; the epic enumerates *anticipated* stories, with permission to revise.
- **Out-of-scope = "not in the epic"**, no rationale. Each deferred item needs a one-liner on why.
- **An invented success number.** "Shipping" is not a measure, and neither is a target nobody stated — an unknown is `[TBD — who decides]` plus an open question.
- **Risks copy-pasted from the requirements.** Epics introduce new risks (sequencing, parallel work) — surface those, don't just inherit.

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

An epic is one capability a person gets. Size follows from that, not from a calendar:

| Symptom | Shape |
|---|---|
| One capability, a handful of stories | **One epic** — small is fine; the epic still exists so the plan can cite it |
| One capability with several actors or data variations | **One epic**, sliced by actor or variation |
| Two capabilities that happen to share an area | **Two epics** — one outcome each, "parallel" dependency noted |
| A capability spanning several delivery windows | **Split by window**, each part usable on its own and with its own outcome line |

## Rules

- One outcome per epic, written in WHO / DO WHAT / SO THAT MEASURABLE CHANGE form
- **Every epic carries its plain-English section** — the As-a / I-want / So-that line, what gets built, and how it fits with everything else — and that section names no technology at all
- **The "how it fits" paragraph names other epics by what they are**, not only by id, and says what becomes possible after this one that was not before
- Slicing strategy named (workflow / role / read-before-write / data variation) — applied consistently across stories
- Every epic is usable end to end by its first 2–3 stories
- Out-of-scope itemized, each with rationale and pointer to the follow-up
- Success measure stated with baseline + target, or `[TBD — who decides]` plus an open question — never invented
- Dependencies named bidirectionally (blocked-by, blocks, parallel)
- Risks owned at the epic level, with mitigation
- Definition of Done is a binary checklist — no subjective items
- Story enumeration is *anticipated*, not committed — refinement produces the real INVEST stories
- Where a delivery window is stated, a slip is a replan, never a silent extension

## What NOT to do

- No invented success numbers — an unknown measure is an open question, not a reason to stop
- No "platform improvements" epics with no user-facing outcome
- No epic or anticipated story that is one layer of a capability ("API only", "UI only")
- No copy-pasted risks from the requirements — add epic-level risks
- No DoD items like "tested" — the test gate is the QA peers' to define, not the epic's
- No epic written for the team's convenience that produces nothing for the user (re-orgs of code that doesn't ship value)
- No mixing two outcomes in one epic — they are two epics
- No technology anywhere in the document

## Generation steps

1. Read the requirements document. If it is unscoped, route back to `business-analysis/skills/ba-scoping-writeup`. If it merely lacks a success measure, proceed — the measure becomes `[TBD — who decides]` and an open question
2. Write the plain-English section (§2): the As-a / I-want / So-that line, what gets built, how it fits. **Read it back with every technical noun removed** — if a sentence stops making sense, rewrite the sentence, do not reinstate the noun
3. Draft the one-sentence outcome from it — iterate with the user until WHO / DO WHAT / SO THAT MEASURABLE CHANGE all pass the sniff test
4. Pick the slicing strategy
5. Enumerate child stories (titles + slice) — note these are anticipated, not committed
6. Mark in-scope / out-of-scope / deferred with rationale
7. Surface epic-level risks and dependencies
8. Write the Definition of Done as a binary checklist
9. Hand off to `business-analysis/skills/ba-story-writer`

## Handoffs

- Inside the delivery lane → `requirements-author` (`/dev-refine`) runs this skill as its Step 3 and writes `docs/plans/<NNN>-<initiative>/epics.md`
- Up-stream (vague requirement) → `business-analysis/skills/ba-scoping-writeup`
- Down-stream (story refinement) → `business-analysis/skills/ba-story-writer`
- Epics/stories authored elsewhere need a readiness audit → `business-analysis/skills/ba-story-quality-review`
- Architecture, contracts, task plan → `solution-planner` (`/dev-plan-solution`), a peer agent invoked separately
