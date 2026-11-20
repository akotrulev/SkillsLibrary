---
name: knowledge-base
description: Use when reading or updating the business-model knowledge base (docs/business-model/) before any BA modeling. Triggers "read the KB first". Not for the connection map (dependency-map).
disable-model-invocation: true
---

# BA — Project Knowledge (the KB protocol)

Every other `ba-*` skill reasons **against the whole project's business model, not just the task at hand**. That model lives as a small, versioned knowledge base in the target project. This skill defines where it lives, what goes in it, and the read/write contract — so a session that starts cold reconstructs the project's business reality from files, and every analysis leaves the model better than it found it.

The shape — read-all-first, update-on-trigger, stable-vs-dynamic tiers — is applied to a *business domain* model instead of a coding-agent's context.

## The KB layout

Lives **in the target repo**, versioned with the code, diffable and PR-reviewable — i.e. under the project root of whatever repo the session is actually working in (resolve `docs/business-model/` against the current working directory), **never** under this skills-library checkout or a global config directory (`~/.claude/...`), unless the user explicitly asks for a shared/global copy:

```
docs/business-model/
├── INDEX.md              # loaded first, every session — one line per artifact + relevance hook
├── glossary.md           # canonical terms; the terminology-drift defense
├── system-overview.md    # in short, who uses the system, the area map + cross-area journeys — plain-language guide, owned by product:doc-business-model
├── areas/<area>.md       # one functional area per file (AREA-nnn), the guide for users, analysts and the product owner: in short, who uses it (administrators included), each person's tasks, every rule, the calculations, worked examples, open questions with their answers — owned by product:doc-business-model
├── areas/screenshots/<area>/   # the guide's few screenshots, captured from the running product
├── flows/<flow>.md       # one business flow per file (FLOW-nnn) — owned by product:process-flow
├── entities/<entity>.md  # one state model per business entity (ENT-nnn) — owned by product:state-grid
├── decisions/<point>.md  # one merged decision table per shared decision point (DEC-nnn) — owned by product:decision-table
├── events.md             # triggers and reactions (EVT-, RX-) — owned by product:dependency-map
├── shared-data.md        # CRUD matrix + shared fields — owned by product:dependency-map
├── invariants.md         # what must always hold (INV-) — owned by product:dependency-map
├── interaction-map.md    # known feature interactions + their resolution decisions (CONF-nnn) — owned by product:conflict-check
└── active-context.md     # dynamic tier: last sessions' changes + open questions/hotspots
```

## The contract

Read and update the KB per `business-model.md`: read `INDEX.md` in full and the files it names for the ids the task touches before any modeling or conflict reasoning, then close the work with the touched artifacts, `active-context.md` and `INDEX.md` updated. A KB with no `INDEX.md`: offer to initialise it (below) before proceeding. Done when the task's analysis names the KB files it read, and the report lists every file it changed.

### Refresh (on the explicit command "refresh the business model")

Re-read **all** files, reconcile drift against the current requirements/codebase reality the user points at, prune stale entries, and re-verify `#inferred` items. Report what changed.

## Authoring standards

The standards every KB file must meet are the product rule files: `business-model.md` for every file under `docs/business-model/`, plus the `business-model-*.md` file of the artifact the task touches. Read the project's copy in `.claude/rules/product/`, or the plugin's in `product/skills/rules/` when the project has not installed them (`/product:rules` does). Where they and this skill disagree, the rule files win. Installed, they load in any session that touches the KB, so a plan task or `documenter` editing a KB file keeps it consistent without loading this skill.

**The lint** is `python3 ${CLAUDE_PLUGIN_ROOT}/product/skills/ba-project-memory/scripts/kb-lint.py [<kb dir>]`; `--help` lists every rule it checks. Run it as the last step of every update. Fix every blocker and major (exit 1); one that is itself an open model finding (an orphan, an unconsumed event) stands only with its line in *Open questions*. Area guides are `doc-lint.py`'s.

## INDEX.md and active-context.md examples

One example line per artifact type. `kb-lint.py` checks the lines, ids and headers.

```markdown
## Areas
- [Ordering](areas/ordering.md) — AREA-003 · customers, support agents · Place, change, cancel and track an order · @ `4f2a91c`
## Entities
- [Order](entities/order.md) — ENT-001; lifecycle Draft→…→Refunded; owners: checkout, fulfillment, refunds
## Flows
- [Checkout](flows/checkout.md) — FLOW-001; happy path + payment-failure/timeout branches
## Decisions
- [Order pricing](decisions/order-pricing.md) — DEC-001; hit policy C+ (stacking); contributed by promos, loyalty, shipping
## Dependencies
- [Events & reactions](events.md) — 7 triggers, 7 reactions; 1 unconsumed event, 2 reactions with `?` failure
## Cross-cutting
- [Interaction map](interaction-map.md) — 4 resolved conflicts, 1 open (CONF-005)
```

An area line has the shape ``- [<Area name>](areas/<name>.md) — AREA-nnn · <who, comma-separated> · <what a person does there, at most 20 words> · @ `<sha>` ``, which `product:doc-business-model`'s lint (`index-line`) checks; its description is the area's row in the system overview's *Areas, by who uses them*. A line in the older style is edited into the shape in place, together with its guide when that guide is updated, never regenerated.

`glossary.md` follows `${CLAUDE_PLUGIN_ROOT}/product/skills/domain-modeling/references/glossary-format.md`, the one format every writer of the glossary shares.

`active-context.md` is `## Sessions` (newest directly under the heading) then one `## Open questions` list for the whole KB:

```markdown
### <YYYY-MM-DD> — <skill or agent>
- <what changed, with the artifact ids>

- <question> — <artifact id> · owner: <who can answer> · blocks: <what> · raised <YYYY-MM-DD>
```

A line leaves *Open questions* only when its answer is written into the artifact it names.

## Connection cross-section

Building one feature's connection cross-section (its triggers, reactions, states, decisions, shared data, invariants and known interactions), as `ba-feature-conflict-check` and QA do: read `references/feature-cross-section.md`.

## Initializing a KB

When no `docs/business-model/` exists and the user wants one:

1. Confirm the path (default `docs/business-model/`; respect an existing docs convention if the project has one).
2. Create `INDEX.md`, `glossary.md`, `active-context.md`, `interaction-map.md` with headers and empty sections (`events.md`, `shared-data.md` and `invariants.md` are created by `product:dependency-map` on first use) — plus the `areas/`, `flows/`, `entities/`, `decisions/` directories. A `glossary.md` that already exists, written by a `product:feature` interview before the KB, is adopted as it is and listed in `INDEX.md`, never recreated.
3. Do **not** backfill the whole model speculatively. The KB accretes as features are analyzed; seed it only with what the current task's analysis actually produces.
4. Offer `/product:rules`, so the KB's standards load in every later session that edits it.

**The one exception — evidence-based backfill from code.** The `documenter` agent deliberately populates the KB in bulk by reading an existing implementation. That does not violate the rule above, because the rule forbids *speculation*, not *volume*: every model row it writes (`flows/`, `entities/`, `decisions/`, the dependency map) is `#observed` with a `file:line` read that session, or `#inferred` and simultaneously raised as an open question. The area guides carry no tags: they are user documentation — who uses the area, each person's tasks, every rule, the calculations, worked examples — and every purpose that no answered question, plan story or `#confirmed` entry states is an open question; the documenter folds each answered question into the guide and lists it for `business-analyst`, who decides whether a model row becomes `#confirmed`. It never writes `#confirmed` — promotion is a human act — and it never overwrites a `#confirmed` entry, since a human's confirmation outranks a trace. See `product/skills/business-documentation`.

## Provenance — telling generated from hand-authored

An artifact derived from code rather than from requirements carries, beneath its header:

```markdown
**Derived from:** code by `documenter` @ `<commit sha>` on YYYY-MM-DD
```

A guide carries it differently: its provenance is the `source: documenter @ <sha>` of the stamp comment that closes the file (`**Derived from:**` is not written on a guide), and the id, owner, models and stories sit in the same comment.

Without it a generated `#inferred` line is indistinguishable from a business decision someone actually made — and the whole value of the KB is that a reader can tell which is which. On refresh, re-verify the citations against the current commit and re-stamp; a `file:line` that has silently drifted is worse than none, because it still looks checkable.

## Anti-example

Bad: a session models a new refund feature, finds it collides with the loyalty-points flow, resolves it in chat — and writes nothing. The next session re-derives (or misses) the same conflict. The KB exists precisely to make that impossible.

Also bad: dumping the full BRD into `flows/` verbatim. The KB is a distilled model with traceability links back to sources — not a copy of them.
