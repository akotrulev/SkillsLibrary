---
name: be-shared-epic-map
description: Use when a backlog's epics need arranging into what can be built at the same time — cross-epic dependencies, the disjoint-file-set parallelism rule, and the wave table that says how many sessions an operator can open at once. Triggers "which epics can run in parallel", "what has to land first", "how many lanes does this plan have". Do NOT use to write epics (`ba-epic-writer`), to order tasks (`be-shared-delivery-plan`), or to size them (`be-shared-session-budget`).
---

# Epic Map — what can be built at the same time

The artifact that sits between a backlog and a task list. `epics.md` says *what* is being built; `delivery-plan.md` says *in what order*. This says **what can run concurrently**, and it is the only place that question is decided.

It exists as its own document because it is the thing that actually gets checked. Parallelism buried in a task list is parallelism nobody reviews — and a wrong call here does not produce a slow plan, it produces two sessions writing one file.

**The lane, not the epic, is the unit of concurrency.** An epic is usually one lane, but where two of its stories share no files they are two lanes. What the operator opens is a lane, and the wave table counts lanes.

**Announce at start:** "I'm using the `be-shared-epic-map` skill to work out which epics can run in parallel."

**Prerequisites:** `epics.md` and `stories.md` (from `requirements-author`), and the approved `blueprint.md` — its functional areas and routing map are what tell you which file trees each epic lands in. Mapping epics without knowing where their code goes produces a wave table with no evidence behind it.

## When to use

- Step 6 of a `solution-planner` run — after the detail pack, before the delivery plan
- When an epic is added, split, or re-scoped and the waves have to be re-derived
- When a wave completes and the next one needs checking against what actually got built

## When NOT to use

- Writing the epics themselves → `ba-epic-writer`, via `requirements-author`
- Ordering tasks and binding them to agents → `be-shared-delivery-plan`
- Sizing tasks or writing the prompts → `be-shared-session-budget`
- Deciding which of two concurrent *tasks* is safe → `be-shared-delivery-plan`'s streams table, which applies the same rule one level down

## Output

**`docs/plans/<NNN>-<initiative>/epic-map.md`**. A filled golden example is at `references/example-epic-map.md` (the shared `001-workshop-booking` pack — shapes normative, domain content illustrative).

---

## Procedure

### Step 1 — Take the epics as given, then add `E0`

The epics are `E1…En` from `epics.md`, with their `US` stories. **Do not renumber them, do not merge them, and do not invent one.** If the backlog is wrong, that is a `requirements-author` finding, not something to fix here.

Then add **`E0` — contract and foundations**, which the planner creates and the backlog never contains:

> the scaffold, the module layout, config and its startup validation, the CI skeleton, the migration sequence, the shared DTOs and the error envelope, auth wiring, the typed endpoint contracts both sides bind to, the generated or hand-written API client, and the app shell + nav map + route tree.

`E0` **carries no stories** — it delivers nothing a person does, which is exactly why it is not in `epics.md`. It exists only here and in `delivery-plan.md`, it is always wave 1, and everything else waits on it. A cross-artifact check that expects a backlog entry for `E0` is checking the wrong thing, and this document says so in one line so the next reader does not go looking.

Where the initiative is brownfield and the foundations already exist, `E0` still appears — with the tasks that are `Done` and the ones that remain. An `E0` that is empty is stated as empty; it is not dropped.

### Step 2 — Place each epic's file trees

For every epic, write down the file trees its stories land in, from `blueprint.md`'s functional areas and the routing map. This is the evidence the whole document rests on, and it is what makes the parallelism claim checkable by someone who did not make it:

| Epic | Stories | Lands in | Agents |
|---|---|---|---|
| `E1` Membership | US1–US4 | `src/Membership/*`, `web/app/members/*` | `be-dotnet`, `fe-react` |

Two rules on this table:

- **Trees, not areas.** `src/Booking/*` is a claim that can be falsified; "the booking area" is not.
- **An epic that lands in a tree it shares with another epic says so here**, in its own row, rather than leaving it to be discovered in Step 3.

### Step 3 — Decide what is parallel

**Two epics run in the same wave only when both hold:**

1. **Neither depends on the other.** No story in one needs a behaviour, an entity, a contract, or a screen the other delivers.
2. **Their file sets are disjoint.** Not "mostly disjoint", not "they can merge" — disjoint. Concurrent lanes execute against a single working tree, so two lanes writing one path is a lost write, not a merge conflict someone resolves later.

This is the same hard rule the delivery plan's streams table applies at task level; applying it here first is what keeps the two consistent.

**When two epics collide on one file, do not collapse them into one lane.** Three fixes, in order of preference:

| The overlap is | Do |
|---|---|
| An incidental shared edit — a DI registration module, a route table, a nav entry, a config key | Pull it out into `E0` as its own task. Both lanes stay |
| A real shared surface one epic builds and the other consumes | That is a dependency, not an overlap. The consumer waits a wave |
| Genuinely intertwined work across both trees | The epics were sliced wrong. Say so as a finding and route it back to `requirements-author` — do not paper over it with a serial order |

**Then split epics into lanes.** Within one epic, two stories that share no files and do not depend on each other are two lanes and may run at the same time. Say which stories are in which lane, and why each lane is internally sequential — the same claim the streams table makes, made once here at story altitude.

### Step 4 — Write the wave table

A **wave** is the set of lanes that can be open at the same time. A wave ends when every lane in it is done, because the next wave's dependencies are what the finished wave delivered.

```
Wave 1   E0                                    1 lane,  must land first
Wave 2   E1 ∥ E3 ∥ E4                          3 lanes, concurrently
Wave 3   E2  (depends on E1 — the member record it books against)
                                               1 lane
```

Every wave row carries its lane count, because that number is the answer to the only question the operator asks this document: **how many sessions can I open right now.**

Every dependency carries **what** it waits on, in a few words — `depends on E1`, on its own, is a claim nobody can check. `depends on E1 — the member record it books against` is one someone can disagree with.

**The reason is already written.** Each epic's plain-English *"how it fits with everything else"* paragraph in `epics.md` §2 says what it leans on and what becomes possible after it — that is the dependency in the author's own words, and it is what these edges should compress. Where an edge you need has no counterpart there, either the epic map has invented a dependency or `epics.md` missed a real one; find out which before writing it down.

### Step 5 — State the critical path and what it costs

The longest chain of waves is the plan's floor: nothing makes it shorter except changing the dependencies. Say what it is, in waves, and name the one dependency that would shorten it most if it were broken. That is the sentence a stakeholder acts on, and it is cheap to write once the table exists.

Where the operator will run the plan alone, back to back, say that too — the waves are then documentation of what *could* be concurrent rather than what will be, and the map still has to be truthful about it, because the same document handed to a second operator or to Mission Control is what they schedule against.

---

## The document

```markdown
# <Initiative> — Epic Map

**Date:** YYYY-MM-DD · **Written by:** `be-shared-epic-map`
**Pack:** `./epics.md` · `./stories.md` · `./blueprint.md` · `./delivery-plan.md`

> `E0` is planner-created: it carries no stories and does not appear in `epics.md`.
> It is the contract-and-foundations lane every other epic waits on.

## 1. Epics and where they land
| Epic | Stories | Lands in | Agents | Depends on |
|---|---|---|---|---|

## 2. Lanes
<!-- one row per lane: which epic/stories, why it is internally sequential -->
| Lane | Epic | Stories | Internally sequential because |
|---|---|---|---|

## 3. Waves
<!-- lanes that can be open at the same time, with the lane count per wave -->

## 4. Critical path
<!-- the longest chain, in waves, and the dependency whose removal would shorten it most -->

## 5. Overlaps resolved
<!-- every file-set collision found in Step 3 and which of the three fixes was applied -->
| Epics | Shared file | Resolution |
|---|---|---|

## 6. Open questions
| # | Question | Blocks | Owner |
|---|---|---|---|
```

## Rules

- **`E0` is created here and stated here.** It never appears in `epics.md`, it carries no stories, and this document says so in a line so no cross-artifact check goes looking for one.
- **Backlog ids are read, never written.** `E1…En` and `US1…USn` come from `epics.md` and `stories.md` as they are. A renumbering here breaks every citation in the pack.
- **Disjoint means disjoint.** One shared file makes two lanes one lane, or makes the shared edit its own `E0` task. There is no third option and no size at which the rule relaxes.
- **Every dependency names what it waits on**, compressing the epic's own *"how it fits"* paragraph rather than inventing a new reason. An unexplained edge cannot be challenged, which means it will never be removed, which means the critical path is longer than it needs to be forever.
- **A lane is a story set, not always a whole epic.** Splitting an epic into two lanes is the cheapest parallelism in the plan, and it is invisible unless this document looks for it.
- **The waves are a claim about a single working tree.** Not about people, not about capacity. Two lanes are concurrent because their files do not collide, and for no other reason.
- **A brownfield `E0` is stated, not skipped.** "`E0` — scaffold, config, CI and auth wiring already exist (`src/Api/Program.cs:1-60`, read 2026-08-30); only the shared DTOs remain" is the useful form.

## Anti-patterns

| Anti-pattern | Why it fails |
|---|---|
| Two epics in one wave "because they are mostly separate" | The one shared file is where the lost write happens. Mostly-disjoint is not disjoint |
| Collapsing two colliding epics into one serial lane | Serialises work that only collided on a DI registration. Pull the registration into `E0` and keep both lanes |
| `E2 depends on E1` with no reason | Unfalsifiable, so it is never removed, so the critical path never gets shorter |
| Renumbering the backlog's epics to make the waves read better | Breaks every `US` and `E` citation in `stories.md` and in `delivery-plan.md` — its task blocks, its task table and every one of its prompt blocks |
| Putting `E0` in `epics.md` | It has no outcome a person can state, so it fails `ba-epic-writer`'s own gate. It is a planner construct and belongs here |
| A wave table with no lane counts | The operator's question is "how many sessions can I open", and the document declines to answer it |
| Treating one epic as one lane always | Two independent stories inside an epic are two sessions the plan never offered |

## Self-check

1. Every epic in `epics.md` appears exactly once, with its own id, unrenumbered — and `E0` appears, created here, marked as carrying no stories.
2. Every epic's row names the **file trees** its stories land in, not just an area name.
3. Every pair of epics in one wave has a disjoint file set, and the disjointness is visible from §1's trees.
4. Every cross-epic dependency names what it waits on, in a few words.
5. Every file-set collision found appears in §5 with the fix that was applied.
6. Every wave carries its lane count, and every lane's row says why it is internally sequential.
7. The critical path is stated in waves, with the dependency whose removal would shorten it most.
8. Nothing here contradicts `delivery-plan.md`'s streams table — the same file sets, one level apart.

## Handoffs

- **← `requirements-author`** — supplies `epics.md` and `stories.md`. Their ids are read, never rewritten.
- **← `be-shared-solution-blueprint`** — supplies the functional areas and the routing map that place each epic in a file tree.
- **→ `be-shared-delivery-plan`** — consumes the lanes and the waves: the streams table is this document's lanes at task altitude, and the task order respects the wave order.
- **→ `be-shared-session-budget`** — the lanes and the wave order are what its prompt blocks in the plan's `## Prompts — one per task` section are ordered by.
- **→ `ba-epic-writer`** (back upstream) — when Step 3 finds two epics that are genuinely intertwined, the slicing is the defect and it is fixed there, not here.

## Version policy

Stack- and version-agnostic: the rule is about file paths and dependencies, and those exist in every stack. The one thing that varies is what belongs in `E0` — a framework whose route registration is convention-based has fewer shared-file collisions to pull out than one with a central registration file, and the blueprint's detected stack is where that is read from, not assumed.
