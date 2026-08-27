---
name: be-shared-plain-language-companion
description: Use when a finished technical document needs a plain-language companion a non-technical reader can follow, saved beside the source as <name>-explained.md. A translation, never a second source of truth. Triggers "explain this plan in plain English", "write a version the business can read". Do NOT use to author the technical document (`be-shared-solution-blueprint` and the other planning skills), to write requirements (`requirements-author`), or on `be-documenter` / `be-feature-documenter` documents — those are already written in the plain, example-first shape and get no companion.
---

# Plain-Language Companion — the same document, for someone who doesn't build software

Every artifact in the backend planning lane is written for two audiences that read very differently: the agent or engineer who will act on it, and the person who owns the business it describes. Writing one document for both makes it worse for both — precision gets sanded off for readability, and readability gets sacrificed for precision.

So the technical document stays exactly as precise as it is, and this skill produces a **companion** beside it: same scope, same facts, plainer words, and — the part that carries the weight — **worked examples with real names and numbers**.

Two disciplines are the whole skill:

1. **The companion is derived, never independent.** It contains no rule, threshold, entity, endpoint, task, or decision that is not already in the source document. If writing it makes you want to state something the source does not, that is a gap in the *source* — fix it there, or leave it out. A companion that quietly introduces a fact becomes a second source of truth, and the two will disagree within a month.
2. **Examples are the payload, not decoration.** "Refunds are only possible within 30 days of delivery" is already fairly plain. What a non-technical reader actually needs is: *"Maria's order arrives on 3 March. She can ask for a refund up to 2 April. On 3 April the option is gone."* The rule is the source's; the walk-through is what this skill adds.

**Announce at start:** "I'm using the `be-shared-plain-language-companion` skill to write the plain-language companion for `<source file>`."

**Prerequisite:** a **finished** source document. Running this on a draft produces a companion that is stale on arrival, and companions are regenerated wholesale rather than patched — so the cost of running it early is paid twice.

## When to use

- Step 7 of a `be-planner` run — after the plan artifacts (five; six when an experience plan exists) are written and self-reviewed
- A stakeholder, product owner, support lead or client sponsor needs to review or sign off on work described in an existing technical artifact
- A source document changed and its companion needs regenerating

## When NOT to use

- The source document does not exist yet → author it first with its owning skill. This skill translates; it cannot recover what was never written down
- The reader is an engineer or an implementing agent → they read the source. A companion is not a shortcut for them, and pointing them at one costs precision
- The ask is really "the technical document is too dense" → that is a defect in the source, not a case for a companion. Route it back to the owning skill
- The ask is for new requirements, a proposal, or a summary that draws conclusions → `requirements-author` / `ba-scoping-writeup`. A companion concludes nothing
- The source is a `be-documenter` area document or a `be-feature-documenter` feature document → **no companion.** Those are written in the plain, example-first shape by design (`be-shared-business-documentation`: overview · setup · how it works · worked example · open questions, with the evidence in a closing table); a companion would be a second copy

## Naming convention — one companion per source, sitting beside it

The companion always takes the source's own filename plus **`-explained`**, in the source's own directory. That is the whole convention: adjacent, self-describing, sorts next to what it explains, and makes a missing companion visible at a glance in a directory listing.

**`be-planner` lane** — inside `docs/plans/<NNN>-<initiative>/`:

| Source | Companion |
|---|---|
| `blueprint.md` | `blueprint-explained.md` |
| `data-model.md` | `data-model-explained.md` |
| `experience-plan.md` | `experience-plan-explained.md` |
| `api-surface.md` | `api-surface-explained.md` |
| `integrations.md` | `integrations-explained.md` |
| `delivery-plan.md` | `delivery-plan-explained.md` |

Rules that come with the convention:

- **One companion per source file, never a merged one.** A single "everything explained" document loses the ability to say *this* companion is stale because *that* source moved.
- **`HANDOFF.md` and `references/` get no companion.** They are working files for whoever is executing, not documents anyone signs off on.
- **No index is needed** — the `-explained` name sitting beside its source in the initiative folder *is* the discoverability.

## The mandatory header

Every companion opens with this block, unchanged:

```markdown
# <Same title as the source> — in plain language

> **This is a plain-language companion to [`<source>.md`](<source>.md).**
> It explains the same thing in simpler words, with examples. It adds nothing new.
> **If the two ever disagree, `<source>.md` is right and this file is out of date.**

**Explains:** `<source>.md` (as of <YYYY-MM-DD>, commit `<sha>`) · **Written by:** `be-shared-plain-language-companion`
**Examples in this document are made up** to illustrate the rules. The names, dates and figures in them are not real data.
```

Three things it establishes, all load-bearing:

- **Precedence.** The reader knows which document wins, so a drifted companion misleads nobody who read the first three lines.
- **Provenance.** The source's state is pinned, so staleness is checkable rather than guessable.
- **Examples are examples.** Without this line, "Maria's order for £42" gets quoted back in a requirements meeting as a real case, or worse, as a requirement.

## How to translate — the five moves

Work section by section through the source. For each one, ask which of these it needs; most sections need two or three, and a source section that needs none gets dropped from the companion rather than padded.

**1. Say it in shorter words.** One idea per sentence. Second person for anything a user does ("you can cancel your order until it ships"). Active voice. If a term is unavoidable — *tenant*, *idempotent*, *reconcile* — define it once, in the sentence where it first appears, in a parenthesis: "each organisation's data is kept separate from every other organisation's (we call one organisation a *tenant*)."

**2. Walk it through in order.** Tables become a sequence. A per-endpoint contract table becomes "when you press Place Order, three things happen: …". A migration sequence becomes "first we add the new column, then we start writing to it, then we stop using the old one." Order is the single most useful thing you can add for a reader who does not think in tables.

**3. Give a worked example.** The move that makes the companion worth having. Concrete actor, concrete numbers, concrete outcome — and the numbers must be **the real thresholds from the source**. A made-up threshold is an invented rule; a made-up customer name is not.

**4. Show what happens when it goes wrong.** The source has this — failure paths, error catalogs, degraded modes, blocked tasks. Non-technical readers need it more than engineers do, because it is what they will be asked about. Same treatment: what the person sees, and what happens to their thing.

**5. Point at what you left out.** Close every companion with a short "what this doesn't cover" pointing back at the source sections you did not translate, and why. A companion that hides its own limits gets read as complete.

## The example discipline

Examples are where a well-meant companion invents requirements. Four rules keep that from happening:

| Rule | Why |
|---|---|
| **Every number in an example comes from the source.** Thresholds, windows, limits, prices used as *rules* are quoted exactly | A rounded or invented threshold is a new rule, stated to a reader who cannot check it |
| **Invent only the incidental.** Names, dates, order numbers, basket contents — the scaffolding a story needs | These carry no policy. A customer called Maria commits the business to nothing |
| **Use one running cast per document.** The same two or three characters across every example in the file | The reader learns them once. Three examples with three unrelated casts is three times the effort for the same point |
| **Examples illustrate, they never extend.** If the source does not say what happens on day 31, the example stops at day 30 and the gap goes to the source's open-questions list | Filling a gap inside a story is how an inference becomes policy without anyone deciding it |

A worked example that lands:

```markdown
**An example.** Maria orders a desk lamp on 3 March. It is delivered on 6 March.

- On 20 March she changes her mind — she can ask for a refund, because it is within 30 days of delivery.
- On 6 April she tries again. The 30 days ran out on 5 April, so the option is no longer offered
  and she is told the return window has closed.
- If the lamp had never been delivered, the 30 days would not have started counting yet.
```

The rule (30 days, from delivery) is the source's. Maria, the lamp and the dates are the companion's.

## Per-artifact focus

Each companion answers one question, and stops. Depth belongs to the source.

| Companion | The question it answers | Keep out |
|---|---|---|
| `blueprint-explained.md` | What are we building, in what pieces, and what did we decide and why? | Pattern rationale, the routing map, non-functional numbers |
| `data-model-explained.md` | What information does the system keep, and what does each thing mean in business terms? | Columns, keys, indexes, migration mechanics |
| `experience-plan-explained.md` | Who uses it, what do they see, and how do they get each thing done — the journeys walked as short stories | Screen ids, routes, page-type vocabulary, the endpoint matrix |
| `api-surface-explained.md` | What can be asked of the system, by whom, and what comes back? | Field tables, status codes, the validation catalog |
| `integrations-explained.md` | Which outside services do we rely on, what breaks if one is down, and what does someone need to go get? | Config key names, timeout and retry policy |
| `delivery-plan-explained.md` | What gets built in what order, what does each step deliver, and what is blocking us? | Task ids, file lists, `dependsOn` graphs, agent names |

The consistent instinct: **cut the machinery, keep the meaning, keep every deadline, threshold and blocker.** A stakeholder who reads only `delivery-plan-explained.md` must still learn that the Stripe credentials nobody has requested yet are holding up payments.

## Language rules

| Do not write | Write |
|---|---|
| "Returns 409 when the order is not in Pending" | "You can only cancel an order that hasn't shipped yet" |
| "Tenant-scoped soft delete with a uniqueness constraint per tenant" | "Deleted records are hidden rather than erased, and each organisation's numbering is its own" |
| "The endpoint is idempotent via an Idempotency-Key header" | "If the same request arrives twice — say the app retried after a dropped connection — it only takes effect once" |
| "P2 is parallel-safe across three agents" | "These three pieces of work don't touch each other, so they can be built at the same time" |
| "Optimistic concurrency on the version column" | "If two people edit the same record at once, the second one is told it changed underneath them, rather than overwriting the first" |
| "Circuit breaker opens after five consecutive failures" | "If the payment provider fails five times in a row, we stop calling it for a while instead of making every customer wait" |

Banned outright: class and method names, table and column names, HTTP status codes, exception types, framework and library nouns, task ids, agent names, file paths. The one exception is the header block and the closing pointer, which name the source file on purpose.

Sentence discipline: aim under 20 words. Two short sentences always beat one with a subordinate clause. If a sentence needs a comma to survive, it is probably two sentences.

## Regeneration, not patching

The companion is **generated wholesale from its source, every time the source changes.** Hand-patching one section is how the two drift apart in the places nobody looked.

- **The source changed → regenerate the whole companion**, re-stamp the header date and commit, and say in the run report which companions were regenerated.
- **A companion has no source** (the source was renamed or removed) → delete the companion. An orphaned explanation of something that no longer exists is worse than nothing.
- **Someone edited a companion by hand** → treat the edit as a comment on the *source*. If it added a fact, that fact belongs in the source; if it improved the wording, keep the wording and carry it into the regeneration.
- **A companion that is older than its source and cannot be regenerated this run** gets one line at the top: `> ⚠️ Out of date — <source>.md changed on <date>. Regenerate before relying on this.` Never leave a silently stale companion.

## Self-check before handing off

1. Every source document that warrants a companion has one, and every companion has a live source.
2. The header block is present and complete on each — precedence, provenance, and the made-up-examples line.
3. **No new facts.** Read each companion against its source and confirm every rule, number, threshold, dependency and deliverable traces to a source statement. This is the check that matters; do it deliberately, not by feel.
4. Every number used as a *rule* matches the source exactly. Nothing is rounded, simplified, or "about".
5. No banned vocabulary — grep for status codes, class-name casing, file extensions, task ids.
6. Each companion has at least one worked example, and every example is labelled and uses the running cast.
7. Each has a "what this doesn't cover" pointer back to the source.
8. Failure behavior and blockers survived the translation. They are the first thing lost and the most asked about.

## Handoffs

- **→ the source's owning skill** (`be-shared-solution-blueprint`, `be-shared-data-model-plan`, `be-shared-experience-plan`, `be-shared-api-surface-plan`, `be-shared-integration-plan`, `be-shared-delivery-plan`) — anything the translation exposed as missing, contradictory or unclear in the source. Fix it there; the companion is never the place to correct the record.
- **→ `design/ux-writing`** — for microcopy that ends up in the product itself. This skill explains documents; that one writes what users read on screen.

## Version policy

Version-agnostic — this skill writes prose about other prose. The only version-sensitive element is the **source pin** in the header: a companion is valid only against the source state recorded there, which is why the date and commit are mandatory and why regeneration re-stamps them rather than carrying them forward.
