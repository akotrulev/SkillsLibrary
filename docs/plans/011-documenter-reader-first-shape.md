# 011 — The documenter's reader-first shape: tasks per person, diagrams, callouts, HTML — plan (2026-11-13)

**Goal:** `dev:doc-business-model` writes guides (Level 1) and behind-the-scenes accounts (Level 2) that read in the order a person meets the product — who uses it, the few ideas and one picture of how it fits together, then each person's tasks in the order life happens — with Mermaid diagrams, GitHub-style callouts and examples beside the rule they show, screen labels the trace found and never invented ones, no internal ids in the body, and lengths the lint enforces. It works on greenfield and brownfield alike: a new KB is written in this shape, and existing documentation is only ever updated in place into it, never recreated (D8), with a check that no number or quoted message was lost. A script turns any guide into one standalone, consistently styled `.html` file to send to a client.

**Status:** T1 and T2 are built (2026-11-13): the Level 1 and Level 2 shapes are in `BD/SKILL.md` and `level-2-behind-the-scenes.md`, the three golden examples follow them, and the lint reads both and measures size, sentences, labels and the diagram; the three examples pass with 0 errors and 0 warnings and 154 tests pass. Still the old rules: the overview and INDEX (T3), the renderer (T4). T3 is next. The agentic-shop pilot (that repo's plan 168, task D1) waits for this plan's W1 and for the user to update the `dev` plugin there; that plan's F1 draws three callout kinds and must add `[!WARNING]`, the fourth kind this plan allows (D6). The rule-based evals (`evals/`) are agent runs and are not part of any gate here: until the user runs the fixture eval (the row under W1 in the prompts table), the new shape is proven only by the golden examples passing the lint.

## 1. What already exists, and what is missing

The evidence is the 2026-11-13 run on agentic-shop (plan 167 there: 28 areas × 3 levels, `docs/business-model/`), read against `backend/_shared/business-documentation/` at `92f14828`.

| Need | Today | Gap |
|---|---|---|
| A guide reads in the order a person meets the product | `SKILL.md` Level 1 skeleton: Overview → Scope → Setup → How it works → How it connects → Example → Who can do what → Open questions → Going deeper. agentic-shop `checkout-and-orders.md` opens with ten rate limits (Setup) before saying what an order is | Who uses it comes first; Rules and limits come after the tasks |
| Terms are explained before a task uses them | Overview is two to four sentences; the checkout guide lists a concept ("What an order freezes") as a flow because nothing else holds it | `## How it fits together` holds up to six key ideas beside the diagram |
| Steps say what the person does | `SKILL.md` "How it works": "Numbered steps, business verbs, **in the order the code runs them**". The checkout guide's "Placing an order" is ten guard checks; nothing says "press **Place order**" | Steps are the person's actions with bold labels and a `**Where:**` path; "What happens next" lists only what the person then sees, receives or is charged; the system's other checks are Level 2's |
| A screen label is never invented | `SKILL.md` "The client's words" asks for the labels the trace harvested; nothing checks it, and the UI may not be in the codebase (the eval fixture has staff labels in `staff-ui.en.json` and no member screen) | Lint `labels`: a bold label in a `Where:` line or a person's step is in Level 3's vocabulary table; a task with no screen found has plain steps and no `Where:` (D12) |
| Flows grouped by person, in lifecycle order | Flows are one flat list under `## How it works`; the checkout guide interleaves customer and owner (rating, which needs a shipped order, comes before the owner ships) | `## For <person>` sections, tasks in lifecycle order with headings unique in the guide, automatic work in `## What happens automatically` |
| Examples next to the rule they show | One `## Example` at the end covering every flow (checkout: 55 lines, four timelines) | A short example inside each task that computes; one end-to-end story only when numbers carry across tasks |
| Visuals | Level 1 has no diagram and no callouts; Level 2 has one Mermaid "who tells whom" diagram; `**Important:**` is a bold word | GFM alerts (`[!NOTE]`, `[!TIP]`, `[!IMPORTANT]`, `[!WARNING]`) and one Mermaid lifecycle or journey picture in Level 1 |
| Metadata out of the reader's way | Six header lines plus a `**Models:**` line (ten links in checkout) before the first sentence | Levels 1–2: one `**Levels:**` line at the top (Level 2 keeps `**Audience:** internal` beside it), the rest in a closing `## About this document` |
| No internal ids in the body | Checkout guide body cites AREA-003, FLOW-110, DEC-112, Q1–Q12 inline | Areas linked by name; ids only in `## About this document`; Q ids only in the open-questions table |
| Lengths that hold | `SKILL.md`: guide "under about 2,000 words", Level 3 "up to about 4,000"; nothing checks it. agentic-shop: 26 of the 28 guides are over 2,500 words (up to 5,704) and all 28 technical files are over 4,000 (up to 11,125), by `wc -w` | Lint ERRORs: Level 1 > 2,500, Level 2 > 3,000, Level 3 main file > 4,000 (evidence index excluded); a fixed order for what leaves a guide that is over; WARNs on a task's step and outcome counts |
| Sentences a client reads once | Checkout "Placing an order" step 3 is one sentence of five clauses; `INDEX.md` lines run to 70 words | Lint `long-sentence`: a Level 1 sentence over 30 words is a WARN |
| Level 2 follows the same order | `references/level-2-behind-the-scenes.md`: flows under `## What happens behind the scenes`, "same names as Level 1" but nothing checks names or order | Level 1's `## For <person>` sections and task headings, in the same order, leaving out a task with nothing behind it; lint `flow-mirror` |
| The overview is organised by reader | `references/system-overview.md`: `## The areas` table by AREA id; agentic-shop overview lists 28 areas in creation order | Areas grouped by who uses them; one journey diagram; `## Who uses it` with where each person starts |
| One INDEX line format | `business-analysis/skills/ba-project-memory/SKILL.md` "INDEX.md format" gives an example line; agentic-shop `INDEX.md` lines vary in shape and run to 70 words | A fixed line shape with a ≤ 20-word description, checked by lint `index-line` |
| Works on greenfield and brownfield | Greenfield: a FULL run writes from nothing. Brownfield: `SKILL.md` "Reconcile procedure" step 4 "Update, don't rewrite — `~~old~~ → new`" covers changed facts, but nothing says what to do with a set written in an older layout, and nothing checks that an update kept every statement | Greenfield writes the new shape directly. Brownfield **updates the existing files in place** into the new shape (D8) — same files, same `Created` date, every statement kept — and never regenerates them; the lint reports a not-yet-updated set as one WARN instead of a wall of ERRORs, and `--kept-from <rev>` reports every number or quoted message the update lost |
| The trace gives the UI path | `feature-trace/SKILL.md` `Client vocabulary`: `\| Client term \| Where seen \| Code name \|` | A `Where in the product` column (screen › control) that feeds `**Where:**` |
| A shareable, good-looking page | — | `scripts/render-html.py`: guide → one standalone `.html`, with no internal metadata and no reconcile marks |

## 2. The Level 1 guide

```markdown
# <Area name>

<One sentence, the client's words: what a person can do here.>

**Levels:** [Guide](<name>.md) · [Behind the scenes](<name>.behind-the-scenes.md) · [Technical reference](<name>.technical.md)

> [!IMPORTANT]
> <The one rule that governs everything below.>          ← optional

## Who uses it
| Who | What they do here |

## How it fits together                                    ← key ideas, then one Mermaid diagram
## For <person>                                             ← one per person in "Who uses it", in that table's order
### <Task — what the person does: "Place an order">
## What happens automatically                               ← optional: scheduled and event-started work
### <Work — named by what it does: "Monthly posting">
## Rules and limits                                         ← optional; was Setup
## A <period> in numbers                                    ← optional: one story whose numbers carry across tasks
## Good to know                                             ← optional
## Related areas                                            ← optional; was How it connects
## Open questions                                           ← for the product owner
## About this document                                      ← the metadata, last
```

**Order of the people.** `## Who uses it` lists people in the order they meet the area (the customer who places an order before the owner who accepts it); the `## For <person>` sections follow that order, and inside each section the tasks follow the record's lifecycle (place → find again → cancel → rate → order again). The heading is `## For <plural or role>` — `## For customers`, `## For the owner`, `## For makers`.

**A task:**

````markdown
### Cancel an order

You can cancel an order yourself until the shop starts working on it; after that you ask.

**Where:** **Your orders** → the order → **Cancel order**

1. Open the order and press **Cancel order**.
2. Give a reason if you like, and press **Confirm**.

**What happens next**

- If nobody at the shop has accepted the order yet, it is cancelled and the timeline shows it.
- If it has been accepted, **Cancel order** becomes **Ask to cancel**: your request, with a reason, waits for the owner.

**If it doesn't go through**

| Situation | What you see | What to do |
|---|---|---|
| The owner accepted it a moment earlier | “This order was accepted while you were deciding.” | Press **Ask to cancel** |

> [!NOTE]
> Any money you paid comes back as a refund — see **Online payments & maker payouts**.
````

- **Second person, imperative, to the person the section names.** Field names in *italics*. **One idea per sentence**: a sentence over 30 words is split (lint `long-sentence`).
- **Bold is a screen label, and a label is evidence.** In a `**Where:**` line and in the person's steps, bold is only ever a label exactly as the screen shows it, and every such label is in the first column of Level 3's *Business ↔ code vocabulary* (lint `labels`, D12).
- **`**Where:**`** is the arrow path from the trace's new `Where in the product` column. A task reached through another channel names it without bold (`**Where:** your own AI assistant, through the shop's order tool`).
- **No screen found** — the UI is not in this codebase, or the search came back empty: the task has no `**Where:**` line and no bold label, and its steps say what the person asks for in plain verbs ("Ask to cancel the booking"). The negative search is a Level 3 row. When no screen was found for the whole area, one open question asks where people do this.
- **The person's steps are numbered; "What happens next" is a bulleted list of outcomes.** An outcome is something the person sees, receives or is charged; alternatives are separate bullets starting "If …". Everything else the system does — its checks, what it records, what it tells other parts — is Level 2's (D2). The evidence index cites `<Task> · step N` and `<Task> · outcome N`, counted from the top of each list. An outcome that computes keeps the formula block (`Name = expression`, then `Where:`).
- **At most seven steps and five outcomes** (lint `limits`); a task that needs more is two tasks.
- **Task headings are unique in the guide** (lint `task-unique`): a task two people do is named for each ("Cancel a booking" under members, "Cancel a member's booking" under staff), the second one short and pointing at the first by name.
- **Automatic work** — a `###` under `## What happens automatically` — keeps today's flow shape because nobody acts: `**Trigger:**`, numbered steps in business verbs, `**Result:**`. Its steps are cited `· step N`.
- **"If it doesn't go through"** keeps the exact-message rule; its third column is what to do, not what the system does.
- **An example sits inside the task that computes**, as `**Example**` and a few lines or a small table, numbers carried to the result. `## A <period> in numbers` exists only when one story's numbers carry across several tasks (credits spent on booking, returned on cancelling, posted at month end); it replaces the old `## Example`.
- **Callouts** are GFM alerts and only four kinds: `[!IMPORTANT]` (a rule that governs — replaces `**Important:**`), `[!NOTE]` (a prerequisite or where something else is handled), `[!TIP]` (a shortcut), `[!WARNING]` (an action that cannot be undone or that charges money — nothing else). At most one inside a task (lint `limits`).
- **`## How it fits together`** holds the key ideas, then the picture; it is left out only when the area has one task, no states and no term to explain.
  - **Key ideas** — up to six `**Term** — one line` entries: the words the tasks use that a new reader would not know (credit, session tier, overage), and any concept that is not a task (what an order freezes). The detail is Level 2's.
  - **One Mermaid diagram**, nine nodes at most, labels in the client's words and in double quotes, node ids single lowercase words: a `stateDiagram-v2` of the area's main record when it has states, otherwise a `flowchart LR` of the people and what passes between them. It is drawn from the trace's states and transitions; where the KB has the record's `ENT-nnn` grid the two agree, and `## About this document` links it (D10). **Every arrow is a task or automatic work in this guide** — the picture shows nothing the text does not say.
- **`## Rules and limits`** — `| Rule | Value | Can it be changed? |`; layered configuration keeps a `Level` column and one line naming the precedence. The answer in *Can it be changed?* is "on the <screen> screen", "by a deployment setting" or "no — fixed in the system".
- **`## Good to know`** — `### <what the person wants to know, in their words>` and an answer that starts with the direct answer ("Yes.", "No.", "Up to 12 months.") and then says what to do instead. It holds only what has no task to live in: what the product does not do (the trace's negative searches), a limit that spans tasks, an unhandled case. It never repeats a row of "If it doesn't go through" or of *Rules and limits*, and has six entries at most (lint `limits`). **It never promises**: "Not yet." and "coming soon" are roadmap claims no code shows (lint `guarantee-words`). Every answer has an evidence-index row.
- **`## Related areas`** — `**Starts from**`, `**Sets off**`, `**Shares**`, each a short list linking the other area's guide **by name**.
- **`## Open questions`** — one line saying these are questions for the product owner that the code cannot answer, then `| # | Question | Why it matters |`. **An inferred purpose appears here and nowhere else in Level 1** — the body states what happens, never "appears to exist so that".
- **`## About this document`** — `**Id:**` (the `AREA-nnn`; a feature document has none), `**Created:**`, `**Last updated:**`, `**Owned by:**`, `**Derived from:**`, `**Audience:**`, `**Models:**` (the FLOW/ENT/DEC links) — one per line, in that order. A feature document carries its `**Generated by …**` line here instead of `Owned by`/`Derived from`.

**Ids.** `AREA-`, `FLOW-`, `ENT-`, `DEC-`, `EVT-`, `RX-`, `INV-` ids appear in Levels 1–2 only inside `## About this document`; `Q<n>` only in the first column of the open-questions table. The KB keeps every id — `INDEX.md`, Level 3 and the models carry them.

**When a guide is over its length** (2,500 words, counted outside fenced blocks and `## About this document`, table cells included), detail moves out in this order until it fits:

1. an outcome the person does not notice → Level 2;
2. a rule nobody meets in a task (a setting only a deployment changes and no person runs into) → Level 3's *Configuration*;
3. a *Good to know* entry → the task it is closest to, as one sentence, or Level 2;
4. example lines beyond the one that shows the rule → `## A <period> in numbers`, or Level 3.

Nothing is dropped; it moves down a level. A guide still over after that documents an area too big for one guide: a new KB splits it at the survey; an existing area is named in the report as a split candidate and its ERROR stands — facts are never trimmed to pass.

## 3. The Level 2 account

```markdown
# <Area name> — Behind the scenes

<One sentence: what this explains.>

**Levels:** …
**Audience:** internal

## At a glance                     ← 3–5 sentences and the who-tells-whom Mermaid diagram (unchanged)
## The parts involved
## For <person>                     ← Level 1's sections, same order
### <Task — same heading as Level 1>   ← lanes: Straight away · Afterwards · On a schedule (unchanged)
## What happens automatically       ← when Level 1 has it
## What is remembered, and where
## Timing and ordering
## When parts fail or are slow
## Outside services                 ← optional
## Settings and switches            ← optional
## If you change this
## Open questions                   ← continues Level 1's numbering
## About this document
```

Level 2's `## For <person>` sections, `## What happens automatically` and their `###` headings are Level 1's, with the same wording and in the same order (lint `flow-mirror`). It adds no task of its own, and it **leaves out a task with nothing behind it** — one where nothing happens beyond what the guide already says — rather than padding it. `**Audience:** internal` stays at the top, under `**Levels:**`: its job is to stop the file being forwarded, and at the bottom it cannot. The lane rules, the neutral wording, the failure table and the guarantee-words rule are unchanged. Callouts are allowed with the same four kinds.

## 4. The system overview

`system-overview.md`:

```markdown
# <System>

<One sentence: what it is and for whom.>

**Levels:** …

> [!IMPORTANT]                       ← optional: the rule that governs the whole system

## Who uses it                        ← | Who | What they do | Start here |  (Start here = the first guide that person reads)
## The journey                        ← one Mermaid flowchart LR of the main end-to-end journey, nodes = area names, ≤ 9
## Areas, by who uses them
### For <person>                      ← | Area | What you can do there |, the area name linking its guide; an area used by several people sits under the first, and the others link to it
### Running the shop                  ← operator and automatic areas, when there are any
## End-to-end flows                   ← unchanged: ### per journey, numbered steps naming each area's guide by name
## Foundations
## What is not documented
## Open questions                     ← questions that cross areas
## About this document
```

`system-overview.behind-the-scenes.md` gains `## About this document`, with the `**Levels:**` and `**Audience:**` lines on top like an area's Level 2; its sections are otherwise unchanged. `system-overview.technical.md` is unchanged.

## 5. INDEX.md lines

One line per area, exactly:

```markdown
- [<Area name>](areas/<name>.md) — AREA-nnn · <who, comma-separated> · <what a person does there, ≤ 20 words> · [behind the scenes](areas/<name>.behind-the-scenes.md) · [technical](areas/<name>.technical.md) · @ `<sha>`
```

The description is the area's row in the overview's `## Areas, by who uses them`, not a list of everything it touches. `ba-project-memory`'s "INDEX.md format" example adopts it; entity, flow and decision lines are unchanged. **An old-shape set's line is edited when the set is updated, not before**: `index-line` reads only the lines of sets already in the new shape, so a KB of old sets does not turn red the day the plugin is updated.

## 6. The lint (`scripts/doc-lint.py`)

| Rule | Severity | Checks | Task |
|---|---|---|---|
| `sections` | ERROR | Level 1 requires `Who uses it`, at least one `For …` section, `Open questions`, `About this document`; Level 2 requires today's list with `What happens behind the scenes` replaced by the `For …` sections, plus `About this document`; overview Level 1 requires `Who uses it`, `The journey`, `Areas, by who uses them`, `End-to-end flows`, `What is not documented`, `About this document` | T1, T2, T3 |
| flow parents | — | flows are the `###` headings under a `## For …` heading or `## What happens automatically` (Levels 1–2), `## End-to-end flows` (overview). A flow's numbered items are its steps and the bullets under `**What happens next**` its outcomes; `index-coverage` and `index-steps` read both (`· step N`, `· outcome N`) | T1, T2 |
| `header` | ERROR | Levels 1–2: the metadata lines inside `## About this document`, `**Id:** AREA-nnn` first on an area set; Level 2's `**Audience:**` is read from the top, under `**Levels:**`; Level 3: unchanged, at the top | T1, T2 |
| `levels-links` | ERROR | unchanged, read from the `**Levels:**` line wherever it sits | T1 |
| `internal-ids` | ERROR | Levels 1–2: an `AREA-/FLOW-/ENT-/DEC-/EVT-/RX-/INV-` id outside `## About this document`; a `Q<n>` outside the first cell of an open-questions table row | T1 |
| `alerts` | ERROR | a `> [!X]` alert whose kind is not `NOTE`, `TIP`, `IMPORTANT` or `WARNING` | T1 |
| `code-nouns`, `jargon` | as today | inside a ` ```mermaid ` fence only the quoted labels and the text after a `:` are scanned, as prose; node ids and arrows are not | T1 |
| `example` | WARN | a Level 1 task with a formula line and no `**Example**` in it, when the guide has no `## A … in numbers` | T1 |
| `flow-mirror` | ERROR | Level 2's `For …` / `What happens automatically` sections and their `###` headings are Level 1's, none added and none out of order; a Level 1 task may be absent | T2 |
| `task-unique` | ERROR | two `###` task headings with the same text in one Level 1 or Level 2 file | T2 |
| `length` | ERROR | words outside fenced blocks and `## About this document`, table cells included: Level 1 > 2,500; Level 2 > 3,000; Level 3 main file > 4,000 excluding `## Evidence index` (split by topic per `level-3-technical.md`) | T2 |
| `limits` | WARN | Level 1: a task with more than seven steps, more than five outcomes or more than one alert; more than six key ideas; more than six `Good to know` entries | T2 |
| `long-sentence` | WARN | Level 1: a sentence over 30 words, outside tables, fenced blocks and formula lines | T2 |
| `labels` | ERROR | Level 1: a bold span in a `**Where:**` line or in a person's numbered step that appears nowhere in the first column of Level 3's *Business ↔ code vocabulary* | T2 |
| `diagram` | ERROR | Level 1, area and overview: more than one ` ```mermaid ` fence; a first line other than `stateDiagram-v2` or `flowchart LR`; a flowchart node label not in double quotes | T2 |
| `guarantee-words` | WARN | as today, plus roadmap promises: a line starting `Not yet`, `coming soon`, `not yet available / supported / possible`, `in a future version / release` | T2 |
| `old-shape` | WARN | a set whose guide has `## How it works` and no `## Who uses it`: one WARN for the set and **no other check runs on it** | T3 |
| `index-line` | ERROR | `--dir` mode, when `<dir>/INDEX.md` exists: every set under `areas/` that is not old-shape has exactly one line of §5's shape, its links resolve, its description ≤ 20 words | T3 |
| `fact-kept` | WARN | only with `--kept-from <git-rev>`: a number (not part of an id) or a quoted message in the guide or Level 2 at that revision that appears nowhere in the set's three levels now | T3 |

Each new rule has a unit test that passes on a good document and one that fails on purpose, in `scripts/test_doc_lint.py`, and the module docstring's rule list stays the single place a reader learns the rules. A WARN is fixed, or the report says why it stands (`SKILL.md` self-check, unchanged).

## 7. The HTML page (`scripts/render-html.py`)

```bash
uv run backend/_shared/business-documentation/scripts/render-html.py --out <dir> <file.md>…
uv run backend/_shared/business-documentation/scripts/render-html.py --out <dir> --dir docs/business-model
```

- **A PEP 723 script** (`# /// script` block): `markdown-it-py` and `mdit-py-plugins`, exact versions pinned, `requires-python = ">=3.12"`. `uv run` installs them; nothing is added to any project.
- `--dir` renders every Level 1 guide under it and `system-overview.md`; files named on the command line are rendered as given (a Level 2 file only when named).
- **One standalone `<name>.html` per input**: inline CSS (light and dark from `prefers-color-scheme`, a print stylesheet that keeps tables and diagrams on one page where they fit), a table of contents from the `##` headings, GFM tables, the four alerts styled with an icon and colour, headings anchored. The only request the page makes is for the Mermaid script.
- **Mermaid**: a ` ```mermaid ` fence becomes `<pre class="mermaid">` and the page loads Mermaid from `https://cdn.jsdelivr.net/npm/mermaid@<exact version>/dist/mermaid.min.js`, with an `integrity` hash of that exact file and `crossorigin="anonymous"` (D11). When the script does not load — offline, a mail client's preview — the reader sees one line, "This diagram needs an internet connection", not the diagram's source; no fact is lost, because every arrow is also a task in the text (§2).
- **A client's page carries nothing internal**:
  - `## About this document` is rendered as one closing line, "Last updated <date>" (the `Last updated` date, else `Created`); the ids, the sha and the model links are not rendered;
  - a reconcile mark `~~old~~ → new` is rendered as `new`;
  - a file whose `**Audience:**` is `internal` (a Level 2 file named on the command line) carries "Internal — not for sharing" under its title.
- **Links**: a link to another guide becomes `<name>.html`; a link to a `.behind-the-scenes.md` or `.technical.md` file is rendered as its text (those levels are internal); any other relative link is rendered as its text; `https:` links stay.
- **Never commits.** `--out` is required; the documenter's report gives the command and never writes the files into the KB.

## Decisions

**D1 — Markdown stays the only source; HTML is generated.**

| Option | Verdict | Why |
|---|---|---|
| The agent writes `.html` | rejected | Level 3 is read by agents (HTML costs ~3× the tokens); the KB contract, the lint, the reconcile `~~old~~ → new` and evidence citations are markdown; 28 areas written by many sessions would each be styled differently; agentic-shop turns raw HTML off |
| `.md` source, HTML rendered by a script | **chosen** | one look for every page, zero tokens, the source stays diffable |

Costs: a reader without the renderer sees diagrams as text.

**D2 — Steps are what the person does; "What happens next" holds only what the person then sees, receives or is charged.** Replaces "in the order the code runs them". Every other thing the system does is Level 2's, and the code's order is Level 3's. Without the filter the old guard checks only move under a new bold label. Costs: a rule a person never triggers (a rate limit) has no step — it goes in `## Rules and limits`; outcomes are cited by position, so reordering them re-cites the evidence index.

**D3 — Tasks are grouped by person, in lifecycle order; Level 2 follows the same sections and headings, in order, and may leave a task out.** Costs: a task two people do (the customer and the owner both cancel) appears under each with its own heading, the second one short and pointing at the first by name; a reader of Level 2 does not find every guide task there.

**D4 — Metadata moves to `## About this document` in Levels 1–2; Level 3 keeps it on top.** Level 3's reader is an agent that needs the sha first. Level 2 keeps `**Audience:** internal` on top. Costs: an agent checking staleness reads the end of a Level 1–2 file, not its head.

**D5 — Internal ids leave the Level 1–2 body; inferred purposes leave the Level 1 body.** Costs: a reader cannot jump from a guide sentence to its FLOW without the About section.

**D6 — Visuals are GFM alerts (four kinds, one per task at most) and Mermaid; no screenshots.** The documenter reads code and cannot take screenshots. `[!WARNING]` is only for an action that cannot be undone or that charges money. GitHub draws both; agentic-shop's `/admin/docs` needs its plan 168 F1, which was written for three kinds and must add the fourth.

**D7 — Lengths are lint ERRORs, counts and sentence length are WARNs.** L1 2,500, L2 3,000, L3 main 4,000 excluding the evidence index; the 2026-11-13 run ignored the prose limits, and 26 of its 28 guides are over. A cap alone makes a writer compress, so §2 fixes the order in which detail leaves a guide, and `limits` and `long-sentence` measure the task and the sentence. Those two are WARNs because a count has honest exceptions. Costs: a big area must move detail into Level 3 or be split at the survey; an existing area that cannot fit stays red until the user splits it.

**D8 — Greenfield writes the new shape; brownfield updates existing documentation in place, never recreates it.** A set in the old shape (`## How it works` and no `## Who uses it`) is updated, file by file, inside the reconcile procedure:

1. **Same files, same history.** The three files are edited, never deleted and regenerated; `Created` is kept, a `Last updated` line is added, `#confirmed` statements are untouched, and `~~old~~ → new` still marks every changed **fact**.
2. **Move, don't rewrite.** Each existing statement is moved under its new section (a flow → the `### task` under the `## For <person>` it belongs to; a system check the person does not notice → Level 2; Setup → Rules and limits; How it connects → Related areas; Who can do what → Who uses it; the end example → the task it illustrates, or `## A … in numbers`; inline ids and inferred purposes → About this document / Open questions). Its wording changes only where the new shape demands it (second person, a step that becomes the person's action) — a layout move is not struck through.
3. **Add only what the shape needs and the old trace lacks**: the `Who uses it` table, the key ideas, `**Where:**` paths and labels, the diagram, callouts. These come from a **targeted** lookup (the UI routes and labels, the trace's states), not a full re-trace. Where the lookup finds no screen, the task takes §2's no-screen form.
4. **Re-trace only what the code delta touched** — the git diff between the file's `Derived from` sha and `HEAD` for the area's paths, as the reconcile procedure already does. No delta, no re-trace.
5. **The evidence index is re-cited, not rebuilt**: each row keeps its evidence and gets the new `<Task> · step N` or `· outcome N`.
6. **Over the length cap**, detail moves down a level in §2's order (Level 1 → Level 2 → Level 3); it is never dropped.
7. **The update is checked, not trusted**: `doc-lint.py --kept-from <the set's old sha or the commit before the update>` lists every number and quoted message of the old guide and Level 2 that no longer appears at any level. Each `fact-kept` WARN is restored, or the report names the code change that removed it.

The lint reports a set not yet updated as one `old-shape` WARN, so a half-updated KB still lints green. Costs: an updated guide can keep an old sentence's wording where a fresh one would read better — the price of never losing a reviewed or confirmed statement; `fact-kept` sees numbers and quoted messages, not every sentence.

**D9 — The HTML is rendered on demand and never committed.** A committed copy drifts the first time the markdown is edited without re-rendering.

**D10 — The guide's diagram is a derived picture: the one place a model is redrawn.** `SKILL.md` says "never duplicate the diagram", and Level 2 links a `FLOW-nnn` instead of redrawing it. Level 1's reader does not follow a link to a model, so the guide draws one picture, from the trace, agreeing with the `ENT-nnn` grid where there is one. Costs: one more place to keep true — the reconcile procedure re-checks the diagram whenever a state or a transition changed.

**D11 — Mermaid loads from a pinned CDN address with an integrity hash; it is not inlined.**

| Option | Verdict | Why |
|---|---|---|
| Inline `mermaid.min.js` in every page | rejected | 2.6 MB a page (11.4.1 measured 2,571,900 bytes); a 28-area KB is about 75 MB to send |
| Pre-render to SVG | rejected | needs Node and a headless browser wherever the documenter runs |
| Pinned CDN script with `integrity` | **chosen** | pages stay small; the hash stops a changed file from running |

Costs: offline, the reader gets a one-line notice in place of the picture.

**D12 — A screen label is evidence.** Bold in a `Where:` line or a person's step must be in Level 3's vocabulary table, and a task whose screen the trace did not find is written without labels. Otherwise D2's "press **Place order**" invites invented buttons wherever the UI lives in another repository. Costs: a backend-only codebase yields guides with no `Where:` paths until someone supplies the screens.

**D13 (2026-11-13, T1) — `internal-ids` runs on the Level 1 area guide only, not on Level 2.** §6 lists it for Levels 1–2. The old `example-behind-the-scenes.md` carries `FLOW-004`, `Q6`, `Q9` in its body and must keep passing until T2 rewrites it, and the overview guide still lists AREA ids until T3. T1 ran it on Level 1 area guides; T2 extends it to Level 2 (after moving the ids into `## About this document` / the open-questions first cell) and keeps the overview out until T3. `alerts` already covers Levels 1–2. Also: Level 1's `**Id:**` joined `HEADER_PREFIXES`, and the example's "Cancel a member's booking" has no `**Where:**` because the fixture has no label for cancelling one booking (`Cancel session` cancels a whole session, so it appears in a `[!NOTE]`).

**D14 (2026-11-13, T2) — three small readings the plan left open.** (a) `length` and `task-unique` run on every set, the overview included (the plan says "Level 1"); `diagram` runs on every Level 1 file; `internal-ids`, `flow-mirror`, `limits`, `long-sentence` and `labels` run on area sets only, so the overview stays untouched until T3. (b) Level 2's `**Audience:**` is read from the top only — the same line in `## About this document` is reported missing — while its other metadata is read from About, and `header_line` falls back to the top for both Levels 1–2. (c) `length` counts a header line (`**Created:**`…, `**Levels:**`) as nothing, and a word is any whitespace- or pipe-separated token holding a letter or digit, so `£6.00` is one word and a table's `|---|` none. Costs: a Level 2 file that moves its Audience under About fails `audience` instead of passing quietly.

## Answered questions (2026-11-13)

**O1 — Title as a question (Trading212 style)?** No: the title is the area's plain name.
**O2 — Separate public help-article output?** No: Level 1 takes the reader-first shape and stays the client's guide.
**O3 — Does Level 2 get the same ordering?** Yes (§3).
**O4 — Mermaid, with agentic-shop rendering it?** Yes; the renderer is agentic-shop plan 168 F1.
**O5 — A standalone HTML renderer?** Yes (§7).
**O6 — Greenfield and brownfield?** Both: a new KB is written in the new shape; existing documentation is only updated in place, never recreated (D8).

## 8. Tasks

All tasks are `docs` on `general-purpose`, as in every library plan. Paths are relative to the repo root; `BD` = `backend/_shared/business-documentation`. Coverage is read from `coverage report -m`: its `Missing` column lists each unexecuted branch as `from->to`, and the floor is counted over the functions the task added or changed.

### T1 — the Level 1 guide shape, its golden example and the lint that reads it

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `BD/references/example-area.md` is a guide in §2's shape, as `BD/SKILL.md` now describes it, and passes `doc-lint.py` together with the other two examples under §6's T1 rules, each rule with a passing and a failing unit test.
**Depends on:** —
**Budget:** ~140k — the two CLAUDE.md files 20k, this plan §1–§2, §6, D2–D7, D10, D12 14k, `BD/SKILL.md` 10k read + 5k edits, `example-area.md` 7k read + 9k write, `example-technical.md` 12k read + 4k edits, `level-3-technical.md` evidence-index rules 2k + 1k, `doc-lint.py` 8k read + 6k edits, `test_doc_lint.py` 7k read + 6k write, test and lint output 10k, reasoning 19k.
**Gate: own tests** — `python3 -m unittest discover -s BD/scripts`, `python3 BD/scripts/doc-lint.py BD/references/example-area.md BD/references/example-behind-the-scenes.md BD/references/example-technical.md`, `uv run --with coverage coverage run --branch -m unittest discover -s BD/scripts && uv run --with coverage coverage report -m --include='*doc-lint.py'` (≥ 80% of the branches T1 wrote). Do not run the evals.

- `BD/SKILL.md`: replace "## Level 1 — the guide" with §2 (skeleton, task shape, labels, `Where:` and the no-screen form, steps and outcomes, automatic work, callouts, key ideas and diagram, Rules and limits, story section, Good to know, Related areas, Open questions, About this document, ids, what leaves a guide that is over its length); change discipline 3 to "who uses it → how it fits together → each person's tasks in lifecycle order → examples beside the rule"; in "Header block", say the block sits in `## About this document` for Levels 1–2 (Level 2's `**Audience:**` stays on top) and on top for Level 3, and the `**Levels:**` line stays on top everywhere; in "Language discipline — by level", add the ids rule, the bold-is-a-label rule and the roadmap promises beside the guarantee words.
- `BD/references/example-area.md`: rewrite the credits guide in §2's shape, so that it shows the hard cases and not only the easy one:
  - `## How it fits together` — key ideas (credit, session tier, overage) and a `stateDiagram-v2` of a booking's credits (spent → returned / kept → posted);
  - `## For members` (Book a session, Cancel a booking) — **the no-screen case**: the fixture has no member screen, so these tasks have plain steps, no `**Where:**` and no bold label;
  - `## For staff` (Set up plans and tiers, Cancel a member's booking) — labels as the staff screen shows them, each in `example-technical.md`'s vocabulary table; a task two people do, under two headings;
  - `## What happens automatically` (Monthly posting) in the Trigger / steps / Result shape;
  - `## Rules and limits` — including the rules nobody triggers (the 24-hour cut-off, the posting moment) with "no — fixed in the system";
  - an inline example on Book a session; "A month in numbers" keeps Ana's March; Q1–Q5 under `## Open questions`, the inferred purpose living only there.
  Keep every fact, number and quoted message (T3's `--kept-from 92f14828` checks it); change the introduction paragraph to describe what the new example demonstrates. Write to §2's limits — seven steps, five outcomes, one alert a task, sentences of 30 words at most — although their lint rules land in T2.
- `BD/references/example-technical.md`: re-cite every evidence-index row whose Level is Guide to the new task headings, `· step N` and `· outcome N`; add to the first column of *Business ↔ code vocabulary* every staff-screen label the guide now shows in bold; nothing else changes. Level 2's rows are T2's.
- `BD/references/level-3-technical.md`: in the evidence-index rules, a statement in a task cites `<Task> · step N` or `<Task> · outcome N`; the example table's `Guide | Overview` and `Guide | Setup` rows cite sections that exist in §2 (`Open questions`, `Rules and limits`).
- `BD/scripts/doc-lint.py` + `test_doc_lint.py`: §6's T1 rows — Level 1 `sections`, flow parents with steps and outcomes for Level 1, `header` from `## About this document` in Level 1 with `**Id:**`, `internal-ids`, `alerts`, the mermaid-fence treatment in `code-nouns`/`jargon`, `example`; `qid-unique` and `ref-resolves` keep reading `## Open questions`. Update the module docstring's rule list. Level 2 and overview rules stay as they are until T2/T3, so the old example-behind-the-scenes still passes.
- **As built (2026-11-13):** Level 1 shape in `BD/SKILL.md` ("## Level 1 — the guide", "### Header block", discipline 3, "Language discipline"), `references/example-area.md` rewritten (members' tasks Book a session / Cancel a booking carry no `**Where:**` and no bold; staff tasks Set up plans and tiers / Cancel a member's booking; `[!IMPORTANT]`, `[!NOTE]`, `[!WARNING]`; `stateDiagram-v2`; Monthly posting; Rules and limits; A month in numbers; Q1–Q5 kept). `example-technical.md`: 38 Guide evidence rows re-cited, five staff labels added to the vocabulary table (Session credits, Monthly allowance, Overage rate (per credit), Personal overage rate, Cancel session). `level-3-technical.md`: citation rules incl. `· outcome N`, the opening callout cited `Important`, a no-screen task's negative-search row. `doc-lint.py`: `sections`, `flow_tasks()`/`flows()` returning `(steps, outcomes)`, `header` from About with `**Id:**` first, `internal-ids`, `alerts`, `example`, `mermaid_prose()`; `load()` anchors on the `**Levels` line. Proof: `python3 BD/scripts/doc-lint.py <three examples>` → `0 error(s), 0 warning(s)`; 103 tests pass; `doc-lint.py` 99% (361 stmts, 142 branches, one miss at the `__main__` guard).
- **Not in T1:** Level 2, and the `length`, `limits`, `long-sentence`, `labels`, `diagram`, `task-unique` and roadmap-promise rules (T2); the overview, INDEX, `old-shape`, `fact-kept`, the trace's `Where in the product` column and the agents (T3) — `SKILL.md` names that column as it will exist; the renderer (T4); the catalog, README, evals and `requirements-breakdown` (W1).

### T2 — the Level 2 account follows Level 1, and the lint measures what a reader feels

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `BD/references/example-behind-the-scenes.md` follows T1's guide section for section in §3's shape, as `BD/references/level-2-behind-the-scenes.md` now describes it, and the three examples pass the lint under §6's T2 rules without one finding from them, each rule with a passing and a failing unit test.
**Depends on:** T1 (the guide it follows; the same lint and test files).
**Budget:** ~133k — CLAUDE.md files 20k, plan §2 (limits, labels, diagram), §3, §6, D3–D7, D10, D12 10k, `level-2-behind-the-scenes.md` 3k + 3k write, `example-area.md` as T1 left it 9k + 2k fixes, `example-behind-the-scenes.md` 7k read + 8k write, `example-technical.md` evidence index and vocabulary 7k + 3k edits, `level-3-technical.md` 2k, `doc-lint.py` 9k + 8k edits, tests 8k + 8k, output 10k, reasoning 16k.
**Gate: own tests** — the three commands of T1's gate, with `--include='*doc-lint.py'` measured over the branches T2 wrote; the lint over the three examples prints no `length`, `limits`, `long-sentence`, `labels`, `diagram`, `task-unique`, `flow-mirror` or `guarantee-words` line.

- `level-2-behind-the-scenes.md`: §3's skeleton; flows sit under Level 1's `## For …` sections and `## What happens automatically`, same headings, same order, no task of its own, and a task with nothing behind it is left out; `**Audience:** internal` stays under `**Levels:**`; `## About this document` closes the file; callouts allowed with the four kinds.
- `example-behind-the-scenes.md`: reorder into T1's sections and tasks; keep every fact; move the metadata to `## About this document`, the Audience line staying on top. A task the existing example says nothing about behind the scenes is left out, not given an invented lane — check "Set up plans and tiers" against what the file already states.
- `example-technical.md`: re-cite evidence-index rows whose Level is Behind the scenes.
- `doc-lint.py` + tests: Level 2 `sections`, flow parents for Level 2, `header` in Level 2 (Audience read from the top), `flow-mirror` as an ordered subset, `task-unique`, `length` for all three levels, `limits`, `long-sentence`, `labels`, `diagram`, the roadmap promises in `guarantee-words`. Update the docstring.
- Where one of the new rules reports a finding on `example-area.md`, fix the example, not the rule: T1 wrote it to §2 without these checks.
- **Not in T2:** the overview, INDEX, `old-shape`, `fact-kept`, the trace column, the agents (T3).
- **As built (2026-11-13):** `level-2-behind-the-scenes.md` rewritten to §3 (follows the guide, Audience on top, About last, ids and `Q<n>` out of the body, 3,000-word ceiling). `example-behind-the-scenes.md`: `## For members` (Book a session, Cancel a booking), `## For staff` (Cancel a member's booking — the whole-session cancellation paragraph lives here), `## What happens automatically` (Monthly posting); *Set up plans and tiers* is left out (nothing behind it beyond what the guide and *What is remembered* say); `FLOW-004` moved to `**Models:**`, `Q6`/`Q9` in the body became "see *Open questions*". `example-technical.md`: the 12 Behind-the-scenes rows re-cited to the new headings (the staff-cancel row now cites *Cancel a member's booking*). `example-area.md`: three sentences over 30 words split (lines 83, 208, 209), no fact changed. `doc-lint.py`: `check_flow_mirror` (ordered subset over `(section, task)` pairs, `outline()`), `check_task_unique`, `check_length` (`Doc.reader_lines()`), `check_limits`, `check_long_sentence` (`sentences()`), `check_labels`, `check_diagram`, `ROADMAP_PROMISE` in `check_guarantee_words`, Level 2 `sections`/flow parents/`header`/`internal-ids`; docstring updated. Proof: `python3 -m unittest discover -s BD/scripts` → 154 tests OK; `doc-lint.py <three examples>` → `0 error(s), 0 warning(s)`; `doc-lint.py` coverage 99% (478 stmts, 208 branches, one miss at the `__main__` guard). Built but unverified: the lint on any real KB — the evals were not run.

### T3 — the overview, INDEX lines, and updating an old set in place without losing a fact

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** the skill, both documenter agents and the lint treat a KB as §4, §5 and D8 say — the overview by reader, one INDEX line shape, an old-shape set updated in place and checked by `--kept-from` — proven by a `--dir` lint over a scratch KB holding one old-shape and one new set, and by `--kept-from 92f14828` over the golden examples printing no `fact-kept` line.
**Depends on:** T2 (the same lint and test files; the shape the agents describe).
**Budget:** ~135k — CLAUDE.md files 20k, plan §4–§6, D8, D10, D12 9k, `system-overview.md` 3k + 4k write, `BD/SKILL.md` Output + Reconcile + Self-check 4k + 3k edits, `ba-project-memory/SKILL.md` "INDEX.md format" 2k, `be-documenter.md` 4k + 2k, `be-feature-documenter.md` 3k + 2k, `codebase-survey/references/documentation-plan.md` 3k + 2k, `feature-trace/SKILL.md` + `trace-recipes.md` 6k + 2k, `doc-lint.py` 10k + 7k, tests 10k + 7k, output 10k, reasoning 20k.
**Gate: own tests** — the three commands of T1's gate, with coverage over the branches T3 wrote, plus:
a scratch KB under `$TMPDIR` holding one old-shape set (copy of `example-area.md` at `92f14828`, its two siblings), one new set, and an `INDEX.md` with a §5 line for the new set and an old-style line for the old one: `python3 BD/scripts/doc-lint.py --dir <scratch>` exits 0 with exactly one `old-shape` WARN and no `index-line`; deleting the new set's INDEX line makes it exit 1 on `index-line`;
`python3 BD/scripts/doc-lint.py --kept-from 92f14828 BD/references/example-area.md BD/references/example-behind-the-scenes.md BD/references/example-technical.md` prints no `fact-kept` line.

- `system-overview.md`: §4.
- `BD/SKILL.md`: "Output" names §5's INDEX line; "Reconcile procedure" gains D8's seven points as a step after "Check staleness per file" ("An old-shape set — `## How it works` and no `## Who uses it` — is updated in place into the current shape: …"), its "Update, don't rewrite" step says layout moves are not struck through and re-checks the guide's diagram when a state or transition changed (D10); self-check item 2 names `old-shape` WARNs as not done, and a `--kept-from` run with every `fact-kept` WARN restored or explained closes an in-place update. State once, near the top of the Level 1 section, that a FULL run on a project without documentation writes this shape directly and a run on existing documentation updates it.
- `business-analysis/skills/ba-project-memory/SKILL.md`: the `## Areas` example line in "INDEX.md format" becomes §5's. Existing INDEX lines are edited into the shape in place, never regenerated, each with its set.
- `feature-trace/SKILL.md`: `Client vocabulary` becomes `| Client term | Where seen | Where in the product (screen › control) | Code name |`; the harvesting paragraph says to record the screen and control path where the UI is in the repo, and the search when it is not — the search is what lets the guide take §2's no-screen form honestly. Add the per-stack searches for routes and navigation labels to `feature-trace/references/trace-recipes.md` (Next.js `app/` routes, React Router route tables, Blazor `@page`); D8's targeted lookup uses the same searches.
- `be-documenter.md`: Step 0 (Orient) reports which existing sets are old-shape; Step 4's row and the REFRESH paragraph name the new sections, `Where:` and the no-screen form, the in-place update (D8: move, add what is missing, re-trace only the delta, run `--kept-from`, never recreate), and the length ERRORs with §2's order for what leaves a guide; the final report gives the render command (`uv run …/render-html.py --out <dir> --dir docs/business-model`) — T4 writes the script, so the line names it as it will exist. `be-feature-documenter.md`: the same, for `docs/features/` (an existing feature document is updated in place).
- `codebase-survey/references/documentation-plan.md`: a REFRESH plan over an old-shape KB sizes each area as an in-place update — reading the three existing files, the targeted lookup for `Who uses it`/`Where:`/diagram, and a re-trace only of the delta's paths — and its last task's whole-KB lint has no `old-shape` WARN left and its `--kept-from` run no unexplained `fact-kept`.
- `doc-lint.py` + tests: overview `sections` (both plain levels), `old-shape`, `index-line` (new-shape sets only), `--kept-from` and `fact-kept`. Keep the comparison a pure function over the old and new text, with the `git show <rev>:./<file>` read beside it, so the unit tests need no repository. Update the docstring.
- **Not in T3:** the renderer (T4); `evals/`, `qa/manual/requirements-breakdown/SKILL.md`, `docs/skills-catalog.md`, `README.md`, `engineering-practices/rules/feature-docs.md`, `business-analysis/skills/rules/business-model.md` (W1). `docs/plans/005-cross-feature-test-design.md` cites old section names but is another plan in flight: do not edit it; W1 records it.

### T4 — `render-html.py`: a guide as one standalone page

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `uv run BD/scripts/render-html.py --out <dir> --dir BD/references` writes `example-area.html` per §7 — table of contents, styled alerts, a Mermaid diagram that a headless browser draws, nothing internal on the page — and `BD/scripts/test_render_html.py` covers ≥ 80% of its branches.
**Depends on:** T3 (the agents' report line names this script; `BD/SKILL.md` is edited by both).
**Budget:** ~80k — CLAUDE.md files 20k, plan §7, D1, D9, D11 4k, `example-area.md` 9k, `doc-lint.py` (its module shape, how tests import a hyphenated script) 5k, write the script 12k and its tests 10k, output 8k, reasoning 12k.
**Gate: own tests** — `uv run --with markdown-it-py==<pin> --with mdit-py-plugins==<pin> --with coverage coverage run --branch -m unittest discover -s BD/scripts -p 'test_render*.py' && uv run --with coverage coverage report -m --include='*render-html.py'` (≥ 80%), then `uv run BD/scripts/render-html.py --out "$TMPDIR/render" --dir BD/references`, then the diagram is seen drawn without a person looking: `"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless --disable-gpu --virtual-time-budget=15000 --dump-dom "file://$TMPDIR/render/example-area.html" | grep -c "<svg"` prints 1 or more (checked on this machine against Mermaid 11.4.1 on 2026-11-13). Without Chrome, `Status:` records the drawn diagram as unverified.

- `BD/scripts/render-html.py` per §7. Pin the newest `markdown-it-py` and `mdit-py-plugins` releases `uv` resolves today, and the newest Mermaid 11.x release on jsdelivr (`curl -sI https://cdn.jsdelivr.net/npm/mermaid@<v>/dist/mermaid.min.js` returns 200); compute the script's `integrity` value from that exact file (`curl -s <url> | openssl dgst -sha384 -binary | openssl base64 -A`); write the pins into the gate line of this plan's W1 block.
- Alerts: markdown-it has no GFM-alert rule — transform the blockquote tokens whose first inline starts `[!NOTE]`/`[!TIP]`/`[!IMPORTANT]`/`[!WARNING]`, in a small function with its own tests. An unknown kind renders as a plain blockquote (the lint already refuses it at source).
- The client's page (§7): the About section reduced to "Last updated <date>", `~~old~~ → new` rendered as `new`, the internal line on a file whose Audience is `internal`, and the one-line notice shown in place of a diagram when the Mermaid script did not load — each with its own test.
- `BD/SKILL.md`: a short "## Sharing a guide" section — the command, D9, what the reader loses offline.
- **Not in T4:** wiring into agentic-shop (plan 168 there renders through `/admin/docs`; its D1 runs this script once for the pilot).

### W1 — the close-out: catalog, README, rules, evals, and the whole set

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** every library surface that describes the documenter matches §2–§7; the whole set below is green; the plan is filed in `docs/plans/implemented/`.
**Depends on:** T1, T2, T3, T4.
**Budget:** ~100k — CLAUDE.md files 20k, this plan's Status, As-built notes and Decisions 10k, `docs/skills-catalog.md` documenter paragraphs only (grep `be-documenter\|doc-business-model\|business-documentation`) 8k + 3k, `README.md` two command rows 1k, `engineering-practices/rules/feature-docs.md` 3k + 2k, `business-analysis/skills/rules/business-model.md` 3k + 2k, `qa/manual/requirements-breakdown/SKILL.md` (its section references) 3k, `evals/evals.json` + `README.md` 4k + 3k, gate output 15k, fixes 10k, reasoning 13k.
**Gate (this is the last task, so it runs the whole set once more across the plan, in run order):**
`python3 -m unittest discover -s BD/scripts -p 'test_doc_lint.py'` ·
`uv run --with markdown-it-py==<pin> --with mdit-py-plugins==<pin> --with coverage coverage run --branch -m unittest discover -s BD/scripts && uv run --with coverage coverage report -m --include='*doc-lint.py,*render-html.py'` (≥ 80% of the branches the plan wrote) ·
`python3 BD/scripts/doc-lint.py BD/references/example-area.md BD/references/example-behind-the-scenes.md BD/references/example-technical.md` (0 errors, 0 warnings) ·
`python3 BD/scripts/doc-lint.py --kept-from 92f14828 BD/references/example-area.md BD/references/example-behind-the-scenes.md BD/references/example-technical.md` (no `fact-kept` line) ·
`uv run BD/scripts/render-html.py --out "$TMPDIR/render" --dir BD/references` and T4's headless-Chrome line ·
`python3 tools/plugin-surface-check.py` · `python3 tools/token-audit.py` (the `dev` row stays within its budget).

- `docs/skills-catalog.md`: the `be-documenter` / `be-feature-documenter` / `doc-business-model` paragraphs describe the reader-first shape, the lint's new rules, `--kept-from` and `render-html.py`. `README.md`: the two documenter command rows.
- `engineering-practices/rules/feature-docs.md`, `business-analysis/skills/rules/business-model.md`: the section names and the About-section rule.
- `qa/manual/requirements-breakdown/SKILL.md`: re-point its references to guide sections (`How it works`, `Who can do what`, `How it connects`) to the new names.
- `evals/evals.json` + `evals/README.md`: expectations that name old sections now name new ones; add: the guide's first `##` is `Who uses it`; no `AREA-` id in a guide's body; Level 2's task headings are the guide's, in order, none added; the fixture has no member screen, so the member tasks carry no `**Where:**` and no bold label; every bold label in a staff task is a value of `staff-ui.en.json`.
- Record in the plan's Decisions a dated `D<n>` that `docs/plans/005-cross-feature-test-design.md` cites the old guide section names, for whoever runs 005 next.
- Fix what the gate finds by the fix loop; a failure may be T1–T4's.
- Commit and push to `master` (this repo's rule). Then tell the user, in this order: run the fixture eval (`evals/README.md`, eval 1) before the pilot, because an instruction defect is cheaper to find on the fixture than on 28 areas; update the `dev` plugin in agentic-shop; add `[!WARNING]` to that repo's plan 168 F1; then run plan 168 (F1, then D1).

## Close-out — every task

Before you stop, in this order, in this file. Another task may be running in this working tree:
re-read this file immediately before these edits, and touch only your own task block, your own prompt
block and the line that says which have landed.

1. **As built** — append a dated `**As built (YYYY-MM-DD):**` bullet to your task block: what differed
   from the plan, the ids and names you assigned, what is built but unverified, and the `file:line` or
   command output that proves the deliverable exists. Never edit an earlier note.
2. **Decisions** — where you built something differently from the plan, append a dated `D<n>` to
   `## Decisions` with both readings. A divergence is recorded, never absorbed.
3. **The blocks below yours** — rewrite, in place, every prompt block whose assumptions your work
   changed (a renamed file, a changed signature, a moved gate), and write any block left
   `Blocked on <your id>` from what you now know.
4. **Status** — rewrite the header `**Status:**` line: what is built, what is next, what is built but
   unverified. When a task is running beside you, leave it: the next task that waits for you rewrites it.
5. **Commit the work** — the code, its tests and these plan edits together, on the current branch (under
   Plan Queue, the plan's branch in its worktree; never check out the default branch), adding only your
   own files, by path — never `git add -A`. Your prompt block is still in the plan.
6. **Merge, last task only** — if this plan runs on its own branch, merge the default branch into it
   now, resolve every conflict by keeping both sides' rows, re-run the failing suites if code conflicted,
   and commit the merge, so the plan merges back cleanly.
7. **Your own block** — only now delete it, and update the line above the blocks that says which have
   landed, in a follow-up commit of its own: `docs: delete <id>'s prompt (<plan>)`. Do not stop between
   the two commits. Stopping mid-task: keep it, with a `Picking up from:` line. Blocked: keep it, naming
   the blocker and its owner. When the queue says other tasks of this plan are running beside you, do
   not commit, stash, reset or check out at all: make this deletion your last edit, and the queue
   commits the work and the deletion together.
8. **Filing** — if your deletion left no blocks, rewrite `**Status:**` one final time (what the plan
   delivered, what is still unverified), `git mv` this plan into `docs/plans/implemented/`, same name and
   number — a `solution-planner` pack moves its whole initiative folder — and add its row to that
   folder's README where there is one, in the same follow-up commit.

## Prompts — one per task

Run them in order, one session each; each block is complete on its own. Every task edits `BD/scripts/doc-lint.py` or files the next one reads, so nothing runs beside anything. No prompt runs the evals in `BD/evals/` (they are agent runs the user starts). The agentic-shop pilot is that repo's plan 168, after W1, after the fixture eval and after the user updates the `dev` plugin there.

| # | Stack | Agent | Depends on | Runs beside | Budget |
|---|---|---|---|---|---|
| T3 | `docs` | `general-purpose` | T2 | — | ~135k |
| T4 | `docs` | `general-purpose` | T3 | — | ~80k |
| W1 | `docs` | `general-purpose` | T1, T2, T3, T4 | — | ~100k |
| — | run the fixture eval (`evals/README.md`, eval 1); update the `dev` plugin in agentic-shop; add `[!WARNING]` to its plan 168 F1; run plan 168 | **the user** | W1 | — | — |

T1 and T2 have landed; T3, T4 and W1 are live.

---

### T3 — the overview, INDEX lines, and updating an old set in place without losing a fact (general-purpose, docs)

````
Depends on: T2
Agent: general-purpose · Stack: docs

You are working in the SkillsLibrary repo. Task T3 of docs/plans/011-documenter-reader-first-shape.md:
reshape the system overview, fix the INDEX line, give the trace its screen-path column, teach the
reconcile procedure and both documenter agents to update an old-shape set in place (brownfield: never
recreate; greenfield writes the new shape directly), and add the lint rules that make a half-updated
KB lint green and an update that lost a fact visible.

Read, in this order:
1. CLAUDE.md (Comments, KISS, Test code rules).
2. The plan: §4, §5, §6 (rows marked T3), D8, D10, D12, task T3, the As-built notes of T1–T2, and
   "Close-out — every task".
3. backend/_shared/business-documentation/references/system-overview.md (whole).
4. backend/_shared/business-documentation/SKILL.md — "Output", "Reconcile procedure", "Self-check".
5. business-analysis/skills/ba-project-memory/SKILL.md — "## INDEX.md format" only.
6. backend/_shared/agents/be-documenter.md (whole); be-feature-documenter.md (whole).
7. backend/_shared/codebase-survey/references/documentation-plan.md (whole).
8. backend/_shared/feature-trace/SKILL.md — the `Client vocabulary` paragraph and table;
   references/trace-recipes.md — the client-vocabulary searches.
9. scripts/doc-lint.py and test_doc_lint.py as T2 left them.

Build what task T3 lists. The render command in the agents' report line is
`uv run ${CLAUDE_PLUGIN_ROOT}/backend/_shared/business-documentation/scripts/render-html.py --out <dir> --dir docs/business-model`
— T4 writes that script; name it as it will exist.

Traps:
- `old-shape` must short-circuit: a set it flags gets that one WARN and no other check, or an
  agentic-shop KB with 27 old sets drowns in ERRORs (D8).
- `index-line` runs only in `--dir` mode, only when `<dir>/INDEX.md` exists, and only for sets that are
  not old-shape; feature folders (docs/features/) have no INDEX and must not fail.
- `fact-kept` compares text, so keep the comparison a pure function (old guide and Level 2 text in,
  the new three levels' text in, findings out) and the `git show <rev>:./<file>` read beside it; the
  unit tests then need no repository. A number inside an id (`AREA-004`) is not a fact; a
  `~~old~~ → new` mark keeps the old value present, which is right.
- If `--kept-from 92f14828` reports a `fact-kept` on the golden examples, T1 or T2 dropped a fact:
  restore it in the example. Do not narrow the rule to make the line go away.
- docs/plans/005-cross-feature-test-design.md cites old section names: do not edit it (another plan in
  flight); W1 records it. The evals and qa/manual/requirements-breakdown are W1's.
- D8 is the user's rule: existing documentation is only updated, never recreated. The agents must not
  delete and regenerate a file, must keep `Created`, `#confirmed` statements and evidence rows, must
  re-trace only the code delta, and close the update with a `--kept-from` run. Write it so an agent
  cannot read "update" as "regenerate and diff".

Gate: own tests — the three commands in T1's gate line (coverage over the branches T3 wrote), plus:
  S="$TMPDIR/kb011" && rm -rf "$S" && mkdir -p "$S/areas"
  git show 92f14828:backend/_shared/business-documentation/references/example-area.md > "$S/areas/old.md"   (and its two siblings as old.behind-the-scenes.md / old.technical.md, the same way)
  copy the current three examples in as new.*.md; write an INDEX.md with a §5 line for the new set and an old-style line for the old one
  python3 backend/_shared/business-documentation/scripts/doc-lint.py --dir "$S"   → exit 0, exactly one old-shape WARN, no index-line
  remove the new set's INDEX line → exit 1 on index-line
  python3 backend/_shared/business-documentation/scripts/doc-lint.py --kept-from 92f14828 backend/_shared/business-documentation/references/example-area.md backend/_shared/business-documentation/references/example-behind-the-scenes.md backend/_shared/business-documentation/references/example-technical.md   → no fact-kept line
Do not run the evals.

Commit: `feat(documenters): reader-first overview, INDEX line, in-place update of old sets with a kept-facts check (011 T3)`.
Close out per the plan's "Close-out — every task" before you stop.
````

### T4 — `render-html.py`: a guide as one standalone page (general-purpose, docs)

````
Depends on: T3
Agent: general-purpose · Stack: docs

You are working in the SkillsLibrary repo. Task T4 of docs/plans/011-documenter-reader-first-shape.md:
write the script that turns a guide into one standalone, consistently styled HTML page a client can
be sent.

Read, in this order:
1. CLAUDE.md (Comments, KISS, Test code rules).
2. The plan: §7, D1, D9, D11, task T4, and "Close-out — every task".
3. backend/_shared/business-documentation/references/example-area.md (whole) — your test input.
4. backend/_shared/business-documentation/scripts/test_doc_lint.py — the first 30 lines, for how a
   test imports a hyphenated script.

Build what task T4 lists: `scripts/render-html.py` (PEP 723, `uv run`), `scripts/test_render_html.py`
(every branch: alerts of each of the four kinds and an unknown kind, a mermaid fence, a guide link, a
Level 2/3 link, a relative non-guide link, an https link, the About section reduced to its date with
and without a `Last updated` line, a `~~old~~ → new` mark, an internal file, `--dir` vs named files,
`--out` missing), and SKILL.md's "## Sharing a guide".

Traps:
- markdown-it has no GitHub-alert rule; transform the blockquote's tokens, do not regex the HTML.
- Pin exact versions (markdown-it-py, mdit-py-plugins, Mermaid 11.x on jsdelivr) after checking they
  resolve, and compute the script tag's `integrity` from the exact file you pinned; then write the two
  Python pins into W1's gate line in this plan (Close-out step 3).
- The page must work opened from disk (`file://`): no fetches besides the Mermaid script.
- Nothing internal reaches the page: no id, sha or model link from `## About this document`, no struck
  old value. A lone `~~text~~` with no arrow is ordinary strikethrough and stays.
- When Mermaid does not load, the reader sees the one-line notice, never the diagram's source.

Gate: own tests —
  uv run --with markdown-it-py==<pin> --with mdit-py-plugins==<pin> --with coverage coverage run --branch -m unittest discover -s backend/_shared/business-documentation/scripts -p 'test_render*.py' && uv run --with coverage coverage report -m --include='*render-html.py'   (≥ 80%)
  uv run backend/_shared/business-documentation/scripts/render-html.py --out "$TMPDIR/render" --dir backend/_shared/business-documentation/references
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless --disable-gpu --virtual-time-budget=15000 --dump-dom "file://$TMPDIR/render/example-area.html" | grep -c "<svg"   → 1 or more: the diagram drew
  Without Chrome on the machine, write the drawn diagram into `Status:` as unverified; do not claim it.

Commit: `feat(documenters): render-html.py — a guide as one standalone page (011 T4)`.
Close out per the plan's "Close-out — every task" before you stop.
````

### W1 — the close-out: catalog, README, rules, evals, and the whole set (general-purpose, docs)

````
Depends on: T1, T2, T3, T4
Agent: general-purpose · Stack: docs

You are working in the SkillsLibrary repo. Task W1 of docs/plans/011-documenter-reader-first-shape.md:
bring every library surface that describes the documenter in line with the plan, run the whole set,
fix what it finds, and file the plan.

Read, in this order:
1. CLAUDE.md.
2. The plan: Status, §2–§7 headings, Decisions, every task's As-built note, task W1, and
   "Close-out — every task".
3. docs/skills-catalog.md — only the paragraphs `grep -n "be-documenter\|doc-business-model\|business-documentation\|be-feature-documenter"` finds.
4. README.md — the `/dev:document-system` and `/dev:document-feature` rows.
5. engineering-practices/rules/feature-docs.md; business-analysis/skills/rules/business-model.md.
6. qa/manual/requirements-breakdown/SKILL.md — grep for "How it works", "Who can do what",
   "How it connects", "Going deeper" and read those paragraphs only.
7. backend/_shared/business-documentation/evals/evals.json and evals/README.md.

Build what task W1 lists, then run the gate.

Traps:
- The catalog is ~200 KB: edit only the documenter paragraphs; never read it whole.
- token-audit's `dev` row: if the new SKILL.md text pushed it over, move detail into a reference that
  loads only when writing that level — do not delete rules.
- The evals' "Golden-copy check" expectations are facts about the fixture, not the shape — keep them.
  The new expectations are in task W1; the fixture's only screen labels are in `staff-ui.en.json`.
- The fix loop: run the whole set once, fix each failure with the narrowest rerun, rerun only what
  failed, then the whole set once more.

Gate (this is the last task, so it runs the whole set once more across the plan, in run order):
  python3 -m unittest discover -s backend/_shared/business-documentation/scripts -p 'test_doc_lint.py'
  uv run --with markdown-it-py==<pin> --with mdit-py-plugins==<pin> --with coverage coverage run --branch -m unittest discover -s backend/_shared/business-documentation/scripts && uv run --with coverage coverage report -m --include='*doc-lint.py,*render-html.py'
    (≥ 80% of the branches the plan wrote: files from `git diff --name-only "$(git log --diff-filter=A --format=%h -1 -- docs/plans/011-documenter-reader-first-shape.md)" HEAD`; the `Missing` column lists each unexecuted branch as `from->to`)
  python3 backend/_shared/business-documentation/scripts/doc-lint.py backend/_shared/business-documentation/references/example-area.md backend/_shared/business-documentation/references/example-behind-the-scenes.md backend/_shared/business-documentation/references/example-technical.md   → 0 errors, 0 warnings
  python3 backend/_shared/business-documentation/scripts/doc-lint.py --kept-from 92f14828 backend/_shared/business-documentation/references/example-area.md backend/_shared/business-documentation/references/example-behind-the-scenes.md backend/_shared/business-documentation/references/example-technical.md   → no fact-kept line
  uv run backend/_shared/business-documentation/scripts/render-html.py --out "$TMPDIR/render" --dir backend/_shared/business-documentation/references
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless --disable-gpu --virtual-time-budget=15000 --dump-dom "file://$TMPDIR/render/example-area.html" | grep -c "<svg"   → 1 or more
  python3 tools/plugin-surface-check.py
  python3 tools/token-audit.py

Commit: `docs(documenters): catalog, README, rules and evals for the reader-first shape (011 W1)`; push to master.
Finish by telling the user, in this order: run the fixture eval (evals/README.md, eval 1) before the
pilot; update the `dev` plugin in agentic-shop; add `[!WARNING]` to that repo's
docs/plans/168-docs-diagrams-and-reader-first-pilot.md F1; then run plan 168 (F1, then D1).
Close out per the plan's "Close-out — every task" before you stop.
````
