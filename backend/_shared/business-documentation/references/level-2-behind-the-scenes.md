# Level 2 — behind the scenes

Load this when writing or refreshing a Level 2 file (`<name>.behind-the-scenes.md`) — never for Levels 1 or 3. Golden example: [example-behind-the-scenes.md](example-behind-the-scenes.md).

Still plain language, but for a reader who wants to know **how the work actually gets done**: which parts are involved, who tells whom, what happens while the person waits and what happens afterwards, what is remembered and where, and what happens when a part is slow or down. It is where a project manager finds out why a charge can arrive a day late, or what else to check before changing a rule. It adds detail to Level 1 — it never re-explains the rules, it links to them.

```markdown
# <Area name> — Behind the scenes
<header block: Created · Owned by · Derived from · Audience: internal · Levels>

## At a glance               ← 3–5 sentences and one simple diagram of the parts and who tells whom
## The parts involved        ← | Part | What it does here | Runs when |
## What happens behind the scenes
### <Flow — same names as Level 1>
## What is remembered, and where
## Timing and ordering       ← what must come first, what can happen twice or out of order, two people at once
## When parts fail or are slow
## Outside services          ← optional: only when the area talks to one
## Settings and switches     ← optional: only when something differs by environment, customer or switch
## If you change this        ← what else is affected
## Open questions            ← numbering continues from Level 1 (Q5, Q6 …)
```

Every section is required except the two marked optional, which are **dropped** when they do not apply — never written to say there is nothing — and the search that proved it is one row in Level 3's evidence index.

**Audience.** The header carries `**Audience:** internal`. A person may promote it to `shareable` after reading it; an agent never does.

**At a glance** carries one **Mermaid** diagram: boxes are the *parts* (named exactly as in *The parts involved*), arrows are "tells" / "asks" / "saves to", each labelled in business words ("booking confirmed"). Five to nine boxes. It is a **who-tells-whom picture, never a second copy of a flow**:

- In a `be-documenter` run (a KB with `flows/` exists), any branching path is linked as `FLOW-nnn` and not redrawn.
- In a feature run (no KB), the Level 2 diagram is the authoritative one; draw the branching path here.

If no flow of the area has background or scheduled work, *At a glance* says so in one sentence ("Everything here happens while the person waits; nothing runs later or on a schedule").

**The parts involved** names every part once, in a plain role name — "the booking service", "the monthly billing job", "the member record" — with what it does here and when it runs. The mapping to class and module names is Level 3's *Business ↔ code vocabulary*; the same plain name is used for the same part in every document of the set.

**Each flow** repeats Level 1's flow (same `###` heading) with the machinery added, as numbered steps under up to three lanes, in the order they happen:

- **Straight away (while the person waits)** — what is done and saved before they get their answer, and which part does it.
- **Afterwards (in the background)** — what is set off afterwards: who is told, what they do, whether the person is told when it finishes. A duration is stated only where the code shows a delay, schedule or poll interval; otherwise it is unknown and an open question.
- **On a schedule** — anything the clock starts.

**A lane with nothing in it is dropped**, never written as "nothing happens". Steps stay numbered continuously across lanes so the evidence index can cite `<Flow> · step N`. Close a flow with **What the person notices if a later step fails** only when the flow has a later step (a lane after *Straight away*, or more than one scheduled step); a flow done entirely while the person waits does not carry it.

**What is remembered, and where** — a table: Information · Kept as (plain: "on the member's record", "a line on the booking", "in the accounts ledger") · Who may change it. Name the *only* writer where there is one.

**Timing and ordering** states, in plain sentences, what the code guarantees and what it does not: "pricing happens after the booking is saved, so for a moment a booking exists that has not been priced". A guarantee the code does not show is *unknown* and is an open question — never a guess.

**When parts fail or are slow** — a table: Situation · What happens · What people notice · Fixes itself? "Nothing is done about it" is a valid, important answer.

**If you change this** — a short list of what else is touched, from the Edges inventory. Each item is a fact with a Level 3 row, not advice.

## Neutral behaviour

Level 2 **states what happens and never judges it**. "The credits are returned twice" — not "a bug returns the credits twice". The words *bug, defect, flaw, broken, wrong, mistake, vulnerability* and *should have* do not appear in Levels 1 or 2; the lint reports each as a warning, and every one is fixed or explained in the report. Text quoted verbatim from the product (a refusal message) is exempt. Calling something a defect happens only in Level 3's Findings. A Level 2 statement that is also a finding has an evidence-index row citing the finding (`see **F1**`), so a reader who wants the verdict can follow it.

**Guarantee words** — *exactly once, at most one / once, immediately, instantly, as soon as, in real time, right away* — are lint warnings too: a timing or delivery guarantee is written only when the code shows it and it has an evidence-index row; otherwise reword it or ask.

## Language

Plain sentences, the Level 1 standard, with these everyday technical words allowed once each is explained in passing: *database, background job, scheduled job, message / notification (between parts), retry, queue ("a waiting line"), outside service, switch (feature switch), environment (test / live)*. Third-party services are named by product ("the payments provider, Stripe"). **Banned:** class, method, table and column names (a client's own term listed in the first column of Level 3's *Business ↔ code vocabulary* stays), file names and paths, HTTP verbs and status codes, exception types, SQL, framework and library names, inline code, tier tags, `file:line`, and the defect words above.

Under about 2,000 words.
