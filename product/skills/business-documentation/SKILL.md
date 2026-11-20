---
name: doc-business-model
description: Use when a trace must be written up as a user guide for every role, admins included, or a plan's delivery note. Triggers "turn this trace into docs". Not for tracing code (doc-feature-trace).
disable-model-invocation: true
---

# Business Documentation — one trace, one guide, every user

Every area (and every feature) is written **once, as a guide**: what each person who uses it — customers, members, staff, **administrators** — can do there, step by step, in the words the product shows them, which rules apply and how a figure is calculated, with a few screenshots where a picture saves a paragraph. There is no second, technical document. Three readers: **end users** (what do I do, what happens), **business analysts** (which rules apply, how is it calculated) and **product owners** (what was built, what changed, what is still open).

| File | Reader | Audience | Language | Answers |
|---|---|---|---|---|
| `<name>.md` | Every user of the product, business analysts, the client, product owner, support | `shareable` | Plain. No technical talk at all | Who uses this, what can I do here, where, what happens, which rules apply, how it is calculated, what is open |
| `docs/deliveries/<NNN>-<plan-slug>.md` | Product owner | `shareable` | Plain. Same language rules | What a plan delivered, what works differently now, what was planned and is not there |

**Load by condition:** writing or editing a guide body → [`references/guide-shape.md`](references/guide-shape.md); `system-overview.md` → [`references/system-overview.md`](references/system-overview.md); a delivery note (the `DOC1` run of a plan) → [`references/delivery-note.md`](references/delivery-note.md); tone or shape against a model → the golden example, [`references/example-area.md`](references/example-area.md).

Six disciplines:

1. **Write for the person, and stay plain.** Never "handler", "endpoint" or a class name; a sentence that would make a non-technical user ask "what does that mean?" does not belong.
2. **Never let inference pass as fact.** The guide states what the product does, as the trace read it in the code this session. A purpose is stated, in one plain sentence, only when one of three sources says it: a person's answer in *Open questions* (folded in by the next run); the stories of the plan that built it (`docs/plans/<NNN>-<initiative>/requirements.md`, `epics.md`, `stories.md`, also under `implemented/`); a `#confirmed` KB entry. Anything else a rule might be *for* is a row in *Open questions*, and where the code and a story disagree the guide states what the code does. "The code enforces X; I could not determine why" is a complete answer.
3. **Simple, flows, examples.** Every guide reads: in short → who uses it → how it fits together → each person's tasks in lifecycle order → every rule in one table → the calculations, with **examples beside the rule they show**.
4. **Every person, administrators included.** Every role the trace found acting in the area is a row in *Who uses it* and has its own `## For <role>` section. Administration screens are tasks, not footnotes.
5. **A few screenshots, never one per step** (see *Screenshots*).
6. **Describe, never judge.** Behaviour is stated neutrally ("the credits are returned twice"). The words *bug, defect, flaw, broken, wrong, mistake, vulnerability* and *should have* never appear (lint WARN; text quoted verbatim from the product is exempt). A defect found while tracing goes to the run's report, routed to `code-auditor`, never into the guide; where the code and a story disagree the guide states what the code does and the difference goes to the delivery note's *Not delivered* and the report.

**Prerequisites:** a confirmed area map (`product:doc-codebase-survey`) or feature scope, and per-area evidence (`product:doc-feature-trace`) including its `Tasks` inventory, its `Client vocabulary` table and the verbatim refusal texts of its `Validations & gates`. A non-production environment with a test login per role is wanted for screenshots and never blocks the text. **When `docs/business-model/` exists or is being written, load `product:knowledge-base` first**: it owns the KB layout, IDs, annotation grammar and the read-first/update-after contract. A standalone feature run skips it.

**The golden example** is the `workshop-booking` toy system as an inherited codebase, one area: [`references/example-area.md`](references/example-area.md). Its shape, tone and example and screenshot discipline are normative; its domain content is an illustration, never a source. Every fact, number, currency, message, actor and screenshot in a guide comes from this run's trace and capture; a claim the trace did not find becomes an open question.

## Output — into the KB, under its contract

Everything lands in **`docs/business-model/`**, per `product:knowledge-base`. A standalone feature (`feature-documenter`) writes one guide under `docs/features/<NNN>-<slug>.md` and its screenshots in `docs/features/screenshots/<NNN>-<slug>/`.

| File | Owner | This skill's role |
|---|---|---|
| `areas/<area>.md` (`AREA-nnn`) | **this skill** | The area's guide |
| `areas/screenshots/<area>/<task>.png` | **this skill** | The guide's screenshots |
| `docs/deliveries/<NNN>-<plan-slug>.md` | **this skill** | The delivery note — written only by a delivery plan's `DOC1` task, by both documenter agents; shape in [`references/delivery-note.md`](references/delivery-note.md) |
| `system-overview.md` | **this skill** | The guide to the whole system |
| `glossary.md` | shared | Terms, the client's own words, and the business ↔ code mapping |
| `INDEX.md`, `active-context.md` | shared | Updated per the KB contract. **One `INDEX.md` line per area**, in this shape and no other (lint `index-line`): `- [<Area name>](areas/<name>.md) — AREA-nnn · <who, comma-separated> · <what a person does there, at most 20 words> · @ \`<sha>\``. The description is the area's row in the overview's `## Areas, by who uses them`. An existing line is edited into the shape together with its guide, never regenerated |
| `events.md`, `shared-data.md`, `invariants.md` | `product:dependency-map` | **Not yours.** |
| `flows/`, `entities/`, `decisions/` | `process-flow` · `state-grid` · `decision-table` | **Not yours.** You link to them by ID in the stamp comment |

---

## The guide

**Read [`references/guide-shape.md`](references/guide-shape.md) before writing or editing a guide body.** A guide reads in the order a person meets the product: `## In short` → `## Who uses it` → `## How it fits together` → one `## For <person>` per person, each task in lifecycle order → `## Rules and limits` → `## How it is calculated` → `## Open questions` → `## About this document`. A FULL run on a project with no documentation writes that shape directly; a run on existing documentation **updates it in place** (*Reconcile procedure*). The tasks are the rows of the trace's `Tasks` inventory, never one per endpoint.

Done when every section the trace's evidence calls for is present in the reference's order, and every optional section that does not apply is dropped.

---

## Screenshots

A screenshot replaces a paragraph of "on the left, below the summary…", never the steps. **Load [`references/screenshots.md`](references/screenshots.md) when the run has an environment to capture from, or is a capture pass.**

- **Source:** a running **non-production** environment, signed in with a test login for the task's role, administrators included. Logins stay in the browser, never in a guide, cache, plan, trace or report.
- **Screenshots never block the text.** The run asks **once** for the environment and a test login per role, in the scope or area-split message it already shows, and never waits on the answer.
- **No environment:** write the guide in full (`**Where:**` paths and bold labels from `Client vocabulary`), hold no image and record `**Screenshots:** pending — <why>`; the report repeats what is needed.
- **Capture pass:** a later run given the environment signs in as each role, checks every bold label against the screen (the screen wins; a difference is fixed in the guide and is an open question), captures, and replaces `pending` with `captured from …`. No re-trace.
- **Waived** is only the person's decision: `**Screenshots:** waived — <the person's reason>`.
- **Few:** one per task at most, only for a task with a `**Where:**` line; six per guide (lint WARN beyond). A guide whose tasks have screens has at least one unless `pending` or `waived` (lint ERROR otherwise).

---

## Language discipline

A table of the same fact as code and as guide is in [`references/glossary.md`](references/glossary.md); load it when unsure how to turn code into the client's words.

Banned in the guide: class, method, table and column names, file names, status codes, exception types, framework nouns, inline code, jargon such as *endpoint, payload, handler, middleware, idempotent, eventual consistency*, tier tags, `file:line`, the judging words of discipline 6, and internal ids (`AREA-`, `FLOW-`, `ENT-`, `DEC-`, `EVT-`, `RX-`, `INV-`, story ids, `Q<n>` outside the open-questions table's first column) anywhere but the stamp comment. **Bold is only a screen label**, never emphasis. A word that needs a definition is replaced, not defined; a client's own technical-sounding word ("API keys") stays when the product shows it, as a bold label or a key idea.

**Guarantee words** — *exactly once, at most one / once, immediately, instantly, as soon as, in real time, right away* — are lint warnings: a timing or delivery guarantee is written only when the code shows it; otherwise reword or ask. **Roadmap promises** — "Not yet.", "coming soon", "in a future version" — no code shows, so the guide never writes them.

## Glossary (KB runs)

Load [`references/glossary.md`](references/glossary.md) when a KB run writes `glossary.md`. Every domain term goes in with its business meaning and the mapping between the client's term and the code's name. **Terminology drift is a finding, not a merge**: record both, flag it, and let `business-analyst` resolve it.

## Reconcile procedure (every run that finds an existing guide)

**Load [`references/reconcile.md`](references/reconcile.md) before the first step.** It holds each step's detail under the same numbers, including the old-shape conversions.

1. **Fold the answers** — the first act of the run: each filled *Answer* goes into the body as one plain sentence and its row is removed, its id never reused. An answer the code contradicts stays and is escalated.
2. **Check staleness**: the stamp's `source:` sha against `HEAD` and the git delta for the area's paths.
3. **Update in place**, never delete and regenerate. A guide in an earlier shape moves into the current shape in the same file, every fact kept. Close with `doc-lint.py --kept-from <old sha> --dir <folder>`, restoring or accounting for every `fact-kept` WARN.
4. **Verdict every statement** against the re-trace: **Agrees** · **New** · **Gone** · **Contradicts**.
5. **Update, don't rewrite**: `~~old~~ → new` keeps one generation of history. Re-check the diagram, the example's arithmetic and the screenshot of every task that changed.
6. **`Gone` needs care**: say whether the feature was removed or your trace missed it; never delete a `#confirmed` KB statement on a failed search.
7. **`Contradicts` escalates** both readings, *stale documentation* vs *code defect*; never pick one silently.
8. **Re-stamp** with the new sha, `Last updated` and `Describes`; log the session in `active-context.md` (KB runs).

## Self-check before handing off

1. **Lint passes:** `python3 ${CLAUDE_PLUGIN_ROOT}/product/skills/business-documentation/scripts/doc-lint.py --dir <folder>` exits 0. Fix every `ERROR`; fix every `WARN` or say in the report why it stands (`screenshots-pending` stands until the capture pass).

Then only what the lint cannot check:

2. Every area from the confirmed map has its guide, or is in "What is not documented" with a reason. **An `old-shape`, `retired-level`, `renamed-section` or `about-shape` WARN means that guide is not done.**
3. **Every role is there** — administrators included — in *Who uses it*, each with its `## For <role>` section.
4. **Every rule the body states is a row of *Rules and limits*,** and every formula is in *How it is calculated*, not in a task.
5. **Every stated purpose has its source** (an answer, a story named in the stamp, a `#confirmed` entry); the rest are open questions. Every answered question is folded and its row gone.
6. **The worked example's arithmetic is recomputed**; every rule number is the code's exact value.
7. **Five statements spot-checked against the code** at random (a threshold, a refusal message, a step, an outcome, a who-can-do-it); one wrong means re-checking its whole task.
8. **Every screenshot looked at** once more: this task's screen, labels matching the steps, test data, nothing secret. A `pending` guide says in the report what is needed to capture.
9. The client's terms and the exact refusal messages are used.
10. `INDEX.md`, `active-context.md` and the glossary are updated (KB runs).
11. Nothing unreachable is documented as a capability.

## Sharing a guide

Load [`references/sharing.md`](references/sharing.md) when a guide or delivery note goes to a client. `render-html.py` turns guides into standalone pages on demand; they are never committed and never written into the KB:

```bash
uv run ${CLAUDE_PLUGIN_ROOT}/product/skills/business-documentation/scripts/render-html.py --out <dir> --dir docs/business-model
uv run ${CLAUDE_PLUGIN_ROOT}/product/skills/business-documentation/scripts/render-html.py --out <dir> docs/features/<NNN>-<slug>.md
uv run ${CLAUDE_PLUGIN_ROOT}/product/skills/business-documentation/scripts/render-html.py --out <dir> --dir docs/deliveries
```

## Version policy

Version-agnostic — this skill writes prose, not code. The guide is valid against the commit in the stamp's `source` and the screenshots against the capture date in *About this document*; a refresh re-checks both.
