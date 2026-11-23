---
name: plan-epic-map
description: Use when writing a system plan's §5, which features can be specced and built side by side, from dependencies and disjoint trees. Triggers "which features can run in parallel". Not for epics (epics).
disable-model-invocation: true
---

# Features side by side — the system plan's §5

Writes **§5 of a system plan, `## 5. Features side by side`**, and nothing else: one table over the
features that says, for each, where its code lands, what it waits on, which features can be **refined
beside** it (their spec sessions run at the same time) and which can be **built beside** it (their
implementation plans run at the same time in one working tree). `solution-planner` loads it for
`/product:plan-system`; the file around it is defined by
`product/skills/solution-blueprint/references/system-plan-format.md`.

It is its own section because it is the thing that actually gets checked. Parallelism buried in a
feature list is parallelism nobody reviews, and a wrong call here does not produce a slow system, it
produces two sessions writing one file.

**Prerequisites:** §3 written (its areas and their trees are where each feature's code lands) and §4
written (the epics and the `F` ids that serve them). A table written without the trees has no evidence
behind it.

## Output

````markdown
## 5. Features side by side

| Feature | Epic | Areas and trees | Depends on | Refined beside | Built beside |
|---|---|---|---|---|---|
| F1 <title> | — | <area>: `<tree>`, `<tree>` | — | F2, F3 | — |
| F2 <title> | E1 | <area>: `<tree>` | F1 — <what it waits on> | F3 | F4 |

<one or two sentences per non-obvious call: a pair that can be refined but not built beside, and why>
````

A filled example is
[`references/example-features-side-by-side.md`](references/example-features-side-by-side.md): its
shapes are normative, its domain content illustrative.

---

## Procedure

### Step 1 — Take the features as given

The features are `F1…Fn` from §4 and §6, with their epics. **Do not renumber, merge or invent one.**
A feature list that is wrong is a finding for `ba-epic-writer`, not something to fix here. The
foundation feature, where there is one, is a row like any other, with `—` as its epic.

### Step 2 — Place each feature's trees

For every feature, write the areas it touches and their trees from §3's `Areas` table. This is the
evidence the whole section rests on:

- **Trees, not areas.** `src/Booking/*` is a claim that can be falsified; "the booking area" is not.
- **A feature that edits a tree another feature also edits says so in its own row**, rather than
  leaving it to be found when two sessions collide.

Done when every feature's row names its trees.

### Step 3 — The dependencies

A feature depends on another when it needs a behaviour, an entity, a convention or a screen the other
delivers. Every edge points backwards in the `F` order and names **what** it waits on, in a few words:
`F1 — the member entity and auth`, never a bare `F1`. The brief of each feature in §6 and the reason
here say the same thing.

Done when every edge names what it waits on and none points forwards.

### Step 4 — Refined beside

**Two features can be refined beside each other when neither one's spec waits on a decision the other
makes.** Both bind to what §3 already fixed; neither needs the other to settle an entity, a rule or a
screen first. Their interview sessions can then run at the same time.

A dependency usually rules this out, but not always: a feature that needs another's code built can
still be specced beside it when §3 fixed everything the two share. Say so in the line under the table.

### Step 5 — Built beside

**Two features can be built beside each other only when both hold:**

1. **Neither depends on the other.**
2. **Their trees are disjoint.** Not "mostly disjoint", not "they can merge": disjoint. Implementation
   plans running at the same time share one working tree, so two writing one path is a lost write, not
   a merge conflict someone resolves later.

**When two features collide on one file**, in order of preference:

| The overlap is | Do |
|---|---|
| An incidental shared edit: a DI registration, a route table, a nav entry, a config key | Move it into the foundation feature, where there is one, so each feature only adds behind a seam that already exists. Without a foundation feature, the two are not built beside |
| A real shared surface one feature builds and the other consumes | A dependency, not an overlap: the consumer waits |
| Genuinely intertwined work across both trees | The features were cut wrong. Say so and route it back to `ba-epic-writer`; do not paper over it |

Done when every pair named in `Built beside` is independent and visibly disjoint from the trees.

### Step 6 — Say the critical path

Under the table, one sentence: the longest chain of dependencies, and the one edge that would shorten
it most if it were broken. That is the sentence a stakeholder acts on.

## Rules

- **Feature ids are read, never written.** `F` and `E` ids come from §4 and §6 as they are.
- **Disjoint means disjoint.** One shared file makes two features not built beside, or makes the
  shared edit the foundation feature's. There is no size at which the rule relaxes.
- **Every dependency names what it waits on.** An unexplained edge cannot be challenged, so it is
  never removed, and the critical path stays longer than it needs to be.
- **Refined beside and built beside are different claims.** Two features in one area often can be
  specced at once and never built at once; the table says both.
- **Built beside is a claim about one working tree**, not about people or capacity.

## Self-check

1. Every feature in §6 appears once, with its own id and its epic.
2. Every row names the file trees, not just an area name.
3. Every pair in `Built beside` is independent, and its disjointness is visible from the trees.
4. Every pair in `Refined beside` shares no undecided entity, rule or screen.
5. Every dependency points backwards and names what it waits on.
6. The relation is symmetric: if F2 lists F3, F3 lists F2.
7. The critical path is stated.

## Version policy

Stack- and version-agnostic: the rule is about file paths and dependencies, and those exist in every
stack. What varies is which edits are incidental: a framework whose route registration is
convention-based has fewer shared-file collisions than one with a central registration file, and §3's
detected stack is where that is read from.
