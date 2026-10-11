---
name: requirements-breakdown
description: Use when the user hands over a story, BRD, acceptance criteria, API contract, or a loose feature description and wants it distilled into a structured, sourced test-basis document before any test cases are written. Triggers: "summarize the business logic of this story", "turn this spec into a testable breakdown", "what are the rules/validations in this doc". Not for the test cases themselves (test-case-writer) or a test plan (test-plan-writer).
---

# QA Test Basis Analyzer

Turns raw, scattered, or partial inputs — a user story, a BRD section, acceptance criteria, an API contract, a state diagram, a Figma flow, or just a paragraph describing part of a feature — into **one concise, structured document that captures everything a tester needs to know about the feature**: its business logic, the high-level implementation details that affect observable behavior, every validation, and every restriction.

This is the **ISTQB test-analysis step**: the inputs are the *test basis*; this skill analyzes them to produce a distilled, testable feature breakdown. It is the artifact that **precedes** test design. It does not enumerate cases, pick techniques, or assign coverage — it produces the single source of truth those steps consume. It backs **Steps 1–2 of the `qa/manual/agents/qa-test-case-designer` agent** ("Analyze the test basis" and "Map the connections").

## When to use

- The user provides a story / spec / contract / description and wants it distilled before test cases exist
- Inputs are scattered across several artifacts (story + a Slack thread + an API schema) and need consolidating into one testable view
- The feature description is partial and you need to make the gaps explicit before anyone designs cases
- A team wants a reviewable "this is what we understood the feature to be" document to confirm with the PO/dev before investing in test design

## When NOT to use

- The user wants the actual test cases → `qa/manual/test-case-writer`
- The user wants partitions / boundaries / decision-table rules derived → `qa/manual/test-design-techniques`
- The user wants release-level risk register + quality gates → `qa/manual/test-strategy`
- The user wants an unscripted exploratory charter → `qa/manual/exploratory-charter-writer`
- Nothing has been explored yet and no docs exist → run Exploration mode in `qa/manual/agents/qa-test-case-designer` (charter + `exploratory-charter-writer`) first; this skill then distills the **session report** it produces

## Core principle — distill, don't invent

The inputs are the source of truth. **Every line of the output traces back to an input** (cite it). Where the inputs are silent, contradictory, or untestable, that is a **finding**, not something you quietly fill in from intuition:

- **Silent** (the spec doesn't say what happens) → record the gap under *Open questions*; if you must state behavior to make the doc usable, tag it `#assumption` and surface it.
- **Contradictory** (two inputs disagree) → record both and flag the conflict; do not silently pick a winner.
- **Untestable** (no observable outcome, or "fast"/"user-friendly" with no criteria) → flag it and propose the measurable rewrite you'd need.
- **Implementation detail that doesn't change observable behavior** (which ORM, which queue) → leave it out. Only capture implementation details a *black-box tester can observe or must account for* (e.g. "validation runs server-side too", "tokens expire in 15 min", "list is paginated at 50").

Concise is the goal. This is a 1–2 page distillation, not a re-typing of the spec. Collapse, deduplicate, and structure — don't transcribe.

## Inputs needed

Confirm before analyzing. Ask only what's missing, at most 2–3 questions:

1. **The material** — the story/BRD/contract/description, plus any linked specs (if it references other docs in the repo, `Glob`/`Grep` for them and read them too)
2. **Scope** — is this the whole feature or one part of it? what's explicitly out of scope?
3. **Where the document should be written** (default: `docs/test-cases/<NNN>-<feature-slug>-basis.md`, `NNN` = the number the suite will take; a project that already keeps basis documents elsewhere wins)

## Procedure

1. **Read everything fully** before writing anything. Follow references to linked specs/diagrams and read those too.
2. **Identify the input shape** and the source of truth within it:

   | Input shape | Source of truth | What you mine for |
   |---|---|---|
   | User story + acceptance criteria | the ACs | business logic, validations per AC |
   | Requirements / BRD | numbered requirements | rules, restrictions, dependencies between requirements |
   | API contract (OpenAPI/Swagger) | endpoints + schemas | per-field validations, required/optional, formats, auth/restrictions, status codes |
   | State diagram / workflow | states + events | the state model, legal/illegal transitions, guards |
   | Business-model KB artifact (`docs/business-model/` flow/entity/decision file) and the §8 slice | the artifact's tables + IDs | rules/transitions with sources already traced; open questions + `⚠️ Assumption` items carry over as flags; the slice becomes §8 (`references/connections.md`) |
   | Feature document (`docs/features/<NNN>-<slug>.md` from `be-feature-documenter`) | its numbered steps, formulas, "who can do what" table and evidence table | steps → rules (BR) and states; formulas + worked example → data dictionary ranges and rounding; "who can do what" → actors; its open questions carry over; rows tiered `#inferred` there stay `#assumption` here; *How it connects* → §8 |
   | Code-trace evidence (`dev:doc-feature-trace`, run by the agent's Code mode) | the trace's inventories, `file:line` on every row | rules, states and validations tagged `#observed`; the Edges inventory → §8; intent the code cannot show → `#assumption` + question |
   | Exploratory session report (`exploratory-charter-writer` output, live app) | observations, findings, test-case candidates | every row sourced `#observed <session/finding id>`; a candidate becomes a BR/V row, a finding a V row with the *actual* violation behavior; anything the docs contradict is a ⚠️ conflict, not a fact |
   | Business-rules table | the rules | the rule set (candidate decision table) |
   | Loose description / partial feature | the prose | best-effort extraction; gaps become Open questions — heaviest flagging |

   **OpenAPI, mechanically.** Walk the contract rather than reading it as prose — each keyword lands in one place, and schema constraints go to the data dictionary, never to one validation row each:

   | Schema / operation keyword | Lands in |
   |---|---|
   | `required` array | data dictionary `Required = yes` |
   | `minimum` / `maximum` / `exclusiveMinimum` / `minLength` / `maxLength` / `minItems` / `maxItems` | data dictionary *Range* (note open vs closed) |
   | `enum` / `pattern` / `format` | data dictionary *Format* |
   | `default` / `nullable` / `readOnly` | data dictionary *Notes* |
   | each `4xx` response + its schema | the *On violation* column of the data-dictionary field it rejects; a `4xx` that no field or rule explains is an Open question ("what triggers 409?") |
   | `security` / scopes per operation | actors & roles; one V row per operation-scope pair — authorization is a rule |
   | `x-`-extensions, `description` prose | rules (BR) only when they state a decision; otherwise ignored |

   A constraint the schema states and the prose contradicts is a ⚠️ conflict row.

3. **Extract into sections 1–7** (see Output). For each, pull from the inputs and cite the source line/section.
4. **Separate business logic from implementation detail.** Business logic = *what the system decides and why* (rules, calculations, outcomes). Implementation detail = *how*, captured only when observable (server-side re-validation, async processing, caching, expiry windows, pagination sizes, rate limits).
5. **Catalog every business validation and every restriction** as a discrete, testable line — cross-field, state-dependent, authorization and rule-based, each with the message/outcome on violation. Plain schema constraints are not V rows: they sit in the data dictionary, where EP and BVA read them.
6. **Sweep for the silent / contradictory / untestable** and log each as an Open question or `#assumption`.
7. **Map the connections (§8)** per `references/connections.md`: slice the KB first, trace the code where the KB is missing or stale, read the docs only as the thin fallback. Every row cites a source; an edge nobody can confirm is an open question.
8. **Keep it lean.** Re-read; cut anything that doesn't help someone design or run a test.

## Output format

A single concise document. Sections may be empty — say "None in the source" rather than omitting, so a reader knows it was considered.

```markdown
# Test Basis — <Feature name>

**Sources**: <story ID / doc links / contract path — what was analyzed>
**Scope**: <what's in; what's explicitly out>
**Analyzed**: <date>
**Status**: draft — pending author confirmation of the flagged items below

## 1. Summary
<2–4 sentences: what the feature does and for whom, in plain language. The elevator pitch a tester reads first.>

## 2. Actors & roles
| Actor / role | Permissions / what they can do here |
|---|---|
| <e.g. Customer> | <can place an order; cannot refund> |

## 3. Business logic & rules
The decisions the system makes and why. Each rule is a discrete "if … then …", traceable to a source line.
| # | Rule | Source |
|---|---|---|
| BR-1 | If order total ≥ $100, free shipping applies | STORY-1247 AC3 |
| BR-2 | Discount and free-shipping cannot both apply to one order | BRD §4.2 |

## 4. Validations & restrictions
Business validations and restrictions only: cross-field, state-dependent, authorization and rule-based. Schema constraints (required, range, length, enum, pattern, format) are in §6.
| # | Field / action | Rule | On violation | Source |
|---|---|---|---|---|
| V-1 | Email | must not already belong to another account | inline error "Email already registered" | AC1 |
| V-2 | Quantity | at most the stock on hand | rejected, field highlighted | STORY-1247 AC4 |
| V-3 | Refund | only within 30 days of purchase | button hidden / 403 | BRD §6 |

## 5. Workflow & states *(if the feature has stateful behavior)*
States, the events that move between them, and which transitions are illegal.
- **States**: <Draft → Submitted → Approved → Paid → Refunded>
- **Transitions**: <Submitted→Approved on reviewer approval; Refunded→* is terminal>
- **Illegal**: <cannot go Paid→Submitted>
*(or "No stateful behavior — single-shot action.")*

## 6. Data dictionary
Every input field with every schema constraint — the raw material for equivalence partitioning / boundary analysis.
| Field | Type | Required | Range / format | On violation | Notes |
|---|---|---|---|---|---|
| email | string | yes | RFC-5322 | 400 `invalid_email` | trimmed before validation |
| quantity | int | yes | 1–99 | 400 `invalid_quantity` | default 1 |

## 7. High-level implementation notes *(observable behavior only)*
Things a black-box tester must account for, not internal architecture.
- Schema constraints (§6) enforced **server-side as well as** client-side
- Order confirmation email sent **asynchronously** (may lag a few seconds)
- Session/token expires after 15 min of inactivity

## 8. Connections
**Built from:** KB slice @ <date> | code trace @ <sha> | docs only (thin) — <what was missing>

### Triggers and chains
| Trigger | Reaction (owner) | Effects | Emits → next | Mode | On failure | Source |
### States this feature relies on
| Entity · state | Other owners' triggers legal here | `—` / `?` cells | Source |
### Shared data
| Field / entity | Other writers | Other readers | Source |
### Invariants
| INV | Statement | Threatened here by | Enforced? | Source |
### Known interactions
| CONF | Pair | Boundary condition | Status |
### KB candidates
<edges found in code or docs that the KB lacks — handed to `business-analyst`>
*(or "Not built — single-feature basis" when this skill runs standalone)*

Every row cites a source: a KB id, `file:line #observed`, or a document line. Filled §8: `qa/manual/cross-feature-test-design/references/example-cancel-booking.md`.

## Open questions & flags
Ambiguous, contradictory, silent, or untestable items — resolve with the author before test design.
- ❓ <AC2 doesn't say what happens to in-flight orders when a discount is removed mid-checkout>
- ⚠️ Conflict: <story says 30-day refund window; BRD §6 says 14 days>
- 🏷️ `#assumption`: <treating "recently" in AC4 as "within 24h" until confirmed>
- 🚩 Untestable as written: <"the page must load fast" — needs a number, e.g. p95 < 2s>
```

## Quality bar

The document must:

- [ ] Fit on one to two pages, plus §8 — distilled, not a re-typing of the spec
- [ ] Have **every rule, validation, and restriction traced to a source** line/section
- [ ] Separate **business logic** (what/why) from **observable implementation detail** (how, only when testers see it) — and omit non-observable internals
- [ ] List every input field in the data dictionary with type, required, and range/format
- [ ] Express each business validation as a discrete testable line (field → rule → outcome on violation); schema constraints sit in the data dictionary with their `On violation`
- [ ] Write §8 from the KB slice, a trace or the docs, every row sourced, every unconfirmed edge an open question, and no edge written to the KB
- [ ] Surface **every** silent/contradictory/untestable item under Open questions — none swept under the rug
- [ ] Tag any stated-but-unconfirmed behavior `#assumption`
- [ ] State "None in the source" for empty sections rather than dropping them

This document does **not**: enumerate test cases, name test techniques, assign priorities/IDs, or claim coverage. Those are downstream.

## Example

A filled basis, with its input, is in `references/example-promo-codes.md`.

## Anti-example

User pastes a story and asks for the test basis.

Bad response: a list of test cases (TC-001, TC-002…). That's `test-case-writer`'s job, and it skips the distillation step that makes the cases trustworthy.

Also bad: re-typing the entire spec verbatim into prose, or silently writing "expired codes show an error and the total stays the same" as fact when the spec left the second-code behavior undefined.

Good response: the structured document of the example — concise, sourced, with the genuine gaps flagged for the author.

## Handoffs

- Derive the techniques / coverage items from this basis → `qa/manual/test-design-techniques`
- Turn §8 Connections into coverage items → `qa/manual/cross-feature-test-design`
- Format the cases into a Setup → Cases → Cleanup suite → `qa/manual/test-case-writer`
- Orchestrate the full doc → basis → suite flow → `qa/manual/agents/qa-test-case-designer`
- Risk-rank the conditions before designing → `qa/manual/test-strategy`
- Build the basis from a live app when docs are thin → Exploration mode in `qa/manual/agents/qa-test-case-designer` + `qa/manual/exploratory-charter-writer`
- File defects noticed while analyzing → `qa/manual/bug-report-writer`
- Building the connections into the KB (this skill only reads it) → `business-analysis/skills/ba-dependency-map`; cross-feature conflicts / the whole-project business model → `business-analysis/skills/ba-feature-conflict-check` + `business-analysis/agents/business-analyst`
- The doc is a vague initiative that needs scoping (not testing) → `business-analysis/skills/ba-scoping-writeup` + `business-analysis/agents/requirements-author`
