---
name: doc-feature-trace
description: Use when one area of an existing backend must be traced in depth into file:line-evidenced inventories. Triggers "trace how this area works". Not for writing the docs (doc-business-model).
---

# Feature Trace — recovering behavior from code

Depth, one area at a time. The output is **structured evidence**, not prose: nine inventories, every item with its `file:line`, ready for `dev:doc-business-model` to turn into three documents. One trace serves all three readers: the guide needs rules and formulas, behind-the-scenes needs the Edges (who tells whom, when, what happens on failure), the technical reference needs everything with exact names, paths, contracts, configuration, tests and telemetry. A second trace per reader is the waste this prevents.

The discipline: **separate what the code does from what you think it means.** Every extracted item is `#observed` with a `file:line` read this session. Intent is a separate, marked layer; where it is not recoverable, the honest output is the behavior plus a question.

**Prerequisite:** a confirmed area from `dev:doc-codebase-survey` (entry points, depth), or `be-feature-documenter`'s confirmed Step 1 scope table.

## When to use

- Step 2 of a `be-documenter` run, once the area split is confirmed; a `REFRESH` re-trace of moved code
- Learning what a module enforces before changing it

## When NOT to use

- Areas not mapped yet → `dev:doc-codebase-survey`
- Defect findings with severities → `dev:audit-feature` (same technique; it asks what is wrong, this asks what is true). A defect noticed while tracing is a finding to report — never switch to auditing
- The readable write-up → `dev:doc-business-model`; this skill produces its evidence

## Output

Per-area evidence: working material for `be-documenter` Steps 3–4, never a KB artifact or raw content of `docs/business-model/`. Evidence consumed within the session stays there (or in the scratchpad, if the area is large); evidence that must survive it goes to `.trace/`.

**Multi-session runs persist the trace.** When a FULL run spans confirmed sessions, one that ends between Trace and Write would lose its evidence. So a run that will not reach Write in the same session persists each completed area's inventory to **`docs/business-model/.trace/<area>.md`** — working files, never in `INDEX.md`, each opening with:

```markdown
**Working trace by `be-documenter` @ <commit> on <date> — not a KB artifact**
```

On resume, a persisted trace is a **lead, not evidence**: spot-check three citations at the current commit; if it moved or a check fails, re-trace. Step 5 (Consolidate) deletes `.trace/` once every write-up cites its evidence; a leftover `.trace/` means a run ended before consolidation.

---

## The trace path

For **every** entry point, walk this path in order; each stop answers a different business question, and skipping one loses a category of rule:

| Stop | The business question it answers | What to extract |
|---|---|---|
| 1. **Entry point** | What can someone ask the system to do? | The capability, in a verb phrase; who can invoke it |
| 2. **Authorization** | Who is allowed to do it? | Roles, permissions, scopes; ownership and tenancy checks ("any user" vs "the owner") |
| 3. **Input validation** | What counts as a valid request? | Required fields, formats, ranges, allowed values, cross-field rules |
| 4. **Preconditions & lookups** | What must already be true? | Referenced things that must exist, be visible, be in a permitted state |
| 5. **Orchestration** | What happens, in what order? | The steps; what is transactional, best-effort, fire-and-forget |
| 6. **Domain rules** | What does the business logic decide? | Every branch, threshold, calculation, eligibility condition — **the highest-value stop** |
| 7. **Persistence** | What is remembered, and what does it constrain? | `Entity.field` reads and writes, DB constraints (constraints *are* rules), audit trails, soft deletes |
| 8. **External calls** | What crosses an organisational boundary? | Which system, when, what is sent, what happens if it fails |
| 9. **Events emitted — and who reacts** | What else reacts? | Events, messages, outbox rows, notifications — the seams to other areas — each with its consumers, one hop out (Edges) |
| 10. **Failure paths** | What does the user experience when it goes wrong? | Every error branch, in business terms |

**Follow the call, do not skim the file:** a five-line handler often delegates to twenty conditions. Depth `full` follows calls to where decisions are made; `shallow` stops at stop 5 and says so.

## The nine inventories

### 1. Capabilities
What a user or system can make this area do: one business-language verb phrase each, with actor and entry point, plus the entry point's **contract** in one line (request → response, or the schema file holding it) and its **authorization** string (policy, permission, scope).

> "A customer can cancel an order that has not yet shipped (`OrdersController.cs:88`)" `#observed`

### 2. Business rules
Every condition, threshold, calculation and eligibility test the code enforces — what the business cares most about, and most likely written nowhere else.

| Rule | Condition | Effect | Evidence | Tier |
|---|---|---|---|---|
| Refund window | Order closed more than 30 days ago | Refund rejected | `RefundService.cs:88` | `#observed` |
| Free shipping | Order total ≥ 5000 minor units and tenant has `freeShipping` enabled | Shipping cost set to 0 | `ShippingCalculator.cs:41` | `#observed` |

Write the rule as the business would state it. **Record the number, not a rounding** — "30 days", not "about a month".

### 3. Validations & gates
Authorization, input validation, preconditions, state guards — each with its failure in user terms **and** the technical outcome (status or problem type, exception type). Where the person sees a message, **quote the refusal text verbatim** with its source (`"You can't cancel within 24 hours of the session."` — `Resources/Bookings.en.resx:12`); "none shown — searched …" when it reaches the user as a bare status. It doubles as the security-review map and negative-test matrix.

### 4. Entity states & transitions
Per owned entity: the states, the moves, who triggers each, and what is blocked — from enums, status columns, guard clauses and the transitions the code *refuses*. **Refusals matter as much as transitions:** a missing arrow is a business rule ("a shipped order never returns to pending"), usually written nowhere else.

### 5. Decision points
Any branch where more than two inputs combine to select an outcome (pricing, eligibility, routing, discounting, risk scoring): the inputs, the combinations, the result of each. Decision tables built from them expose the code's gaps and contradictions.

### 6. Integrations
Per external system: the trigger, what is sent (business-level, not payload schemas), what comes back, and **what happens when it fails** — timeout, retry, fallback, or unhandled (a finding).

### 7. Edges
Where this area touches another, one hop out. For every emitted event, message, outbox row or notification, find its consumers (`file:line`, owning area). For every written field, find the readers **and other writers**, scheduled jobs' queries included. State how each reaction runs and what happens when it fails.

| # | Entry point | Kind | Reads | Writes | Also written by | Emits | Reacted to by (one hop out) | Mode | On failure | Evidence |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `POST /bookings/{id}/cancel` | command | `Booking.status`, `Session.start` | `Booking.status`, `Session.seats_taken` | `Booking.status`: `BookingExpiryJob.cs:31` (Scheduling) | `BookingCancelled` | `BookingCancelledHandler.cs:19` (Credits) | after commit, `?` | `?` | `BookingService.cs:88-104` |

- **Kind**: `command`, `schedule`, `timeout`, `external`, `event`. **Mode**: `in request`, `after commit, <guarantee>`, `scheduled`, `best effort`. **On failure**: rolls back, retried n× then dead-letter, compensates, unhandled.
- **A mode or guarantee the code does not show is `?`.** A library name proves nothing: at-least-once only where a retry, redelivery or missing acknowledgement is visible in code or configuration.
- **A negative claim names its search**: "no consumer of `BookingCancelled` — searched `BookingCancelled`, `booking.cancelled` under `src/`".
- Stop at one hop; the consumer's own events are its row when its area is traced.
- **Also record, for behind-the-scenes:** what is inside the transaction and what runs after commit; the retry count and what follows the last retry; any idempotency key, lock or version column guarding the write; a reaction's delay where the code shows a delay, schedule or poll interval. Anything not shown is `?`.

### 8. Configuration & switches
Every configuration key, option class, environment variable name, feature flag and behaviour-changing constant: where defined, default, effect, whether it varies per environment or tenant. **Names only — never a secret's value.** A constant that looks like it should be configurable (cut-off, rate, window) is recorded with its number and is an open question. "None — searched …" is recorded.

### 9. Tests & telemetry
The tests covering the area (path and line, what each covers, what none covers — boundaries especially) and the telemetry emitted (decision-point logs, spans, metrics; library and names). Tests evidence intent, never behaviour. A missing test or telemetry is a technical finding.

## Harvest the client's words

Record the client's own words, so the guide speaks them instead of code names: UI copy, translation and resource files, email and notification templates, validation and problem-detail text, enum display names, domain terms in docs and test names. Each goes in `Client vocabulary` with where seen, **where in the product** it is met, and its code name; a code name with no client term is recorded with the search. Where the UI is in the repository, record the screen and control path as `screen › control` (`Your orders › Cancel order`) from the routes, navigation and the label's own file; where it is not, or the search finds nothing, record the search instead — that negative row is what lets the guide take its no-screen form (no `**Where:**` line, no bold label) honestly instead of inventing a button. `references/trace-recipes.md` has the per-stack searches.

## Evidence rules

- **Every item carries `file:line`, read this session** — not from the cache, a prior run or memory. The map says where to look; only the read is evidence.
- **Negative claims name their search.** "No rate limiting" is usable only as: *searched for `RateLimit|Throttle|Bucket` across `src/Ordering/**` — no matches* `#observed`.
- **Tier every item.** `#observed` for behavior; `#inferred` for intent or purpose. Never `#confirmed`.
- **Comments and tests evidence intent, not behavior.** "30-day window per card scheme rules" is a strong `#inferred` *why*; only code evidences *what*. A stale comment contradicting the code is a finding.
- **Commit history is a source for intent** — `git log -S'<the constant>'` or `git log --follow <file>` often surfaces the ticket. Cite it; still `#inferred` unless the message states the rule outright.
- **Config and flags change the answer.** A rule inside `if (featureFlags.NewPricing)` is conditional: record both branches and which environments run which, or `[TBD - who knows the flag state]`.

## What to do with things that are not documentation

You are tracing, not auditing; handle what you find like this and keep moving:

| Found | Do |
|---|---|
| A defect (wrong calculation, missing check, unhandled failure) | A **finding to report**, with evidence. Never fix it, switch to auditing, or document it as intended behavior |
| Unreachable code (no route, dead flag, no caller anywhere) | Record it as unreachable; **never document it as a capability** — the most common way generated docs go wrong |
| A trigger whose caller is outside the repository (a message nothing here publishes, a handler another service calls) | **Not unreachable.** A capability, plus a finding and the open question "who triggers this?" |
| Two contradicting rules | Both with evidence; escalate — `business-analyst` owns which wins |
| A rule whose purpose is unrecoverable | The behavior plus an open question — a normal outcome, not a failed trace |
| Something that should obviously change | Route it to the owning `be-<stack>` agent; you do not change code |

## Trace record shape

```markdown
## Area: <name> — trace evidence
**Traced:** YYYY-MM-DD · **Depth:** full | shallow · **Commit:** <sha>
**Entry points covered:** <n>/<n> — <any not covered, and why>

### Capabilities
| # | Capability | Actor | Entry point | Evidence |

### Business rules
| # | Rule | Condition | Effect | Evidence | Tier |

### Validations & gates
| # | Check | Applies to | On failure (user-visible) | Exact message shown (verbatim, source) | Evidence |

### Entity states
| Entity | States | Transitions (trigger → from → to) | Refused transitions | Evidence |

### Decision points
| # | Decision | Inputs | Outcomes | Evidence |

### Integrations
| System | Trigger | Sends | Expects | On failure | Evidence |

### Edges
| # | Entry point | Kind | Reads | Writes | Also written by | Emits | Reacted to by (one hop out) | Mode | On failure | Evidence |

### Configuration & switches
| # | Key / constant | Defined at | Default | Effect | Varies by | Evidence |

### Tests & telemetry
| # | Kind (test / log / span / metric) | Name / path | Covers | Gap | Evidence |

### Client vocabulary
| Client term | Where seen | Where in the product (screen › control) | Code name |

### Intent notes (`#inferred`)
| Observation | Probable purpose | Basis (comment / test / commit / naming) | Question for the business |

### Findings (not documentation)
| # | What | Evidence | Kind (defect / unreachable / contradiction / stale comment) |
```

## Self-check before handing off

1. Every entry point the ledger assigns to this area is traced, or listed as not traced with a reason.
2. Every inventory item has `file:line` read this session; every negative claim names its search.
3. Every item is tiered; no `#confirmed`.
4. The domain-rules inventory is not empty, or the area is declared a pass-through — an empty rules table usually means the trace stopped at stop 5.
5. Refused state transitions are recorded, not only permitted ones.
6. Every integration has a stated failure behavior, including "unhandled".
7. Findings sit in the findings list, out of the documentation stream.
8. Every emitted event has its reactors, or a negative search naming what was searched.
9. Every written field has its readers and other writers, jobs' queries included.
10. Every reaction states its mode and failure behavior, or `?` — never a guessed guarantee.
11. Configuration and constants are inventoried (or a negative search recorded); no secret value is written.
12. Tests and telemetry are inventoried with their gaps, or a negative search recorded.
13. Client words are in `Client vocabulary`; every user-facing refusal quotes its exact text and source (or the search that found none).

## Handoffs

- **→ `business-analysis:process-flow`** — orchestration and failure paths become `FLOW-nnn` diagrams.
- **→ `business-analysis:state-grid`** — inventory 4 becomes `ENT-nnn` state × event grids; refused transitions are its meaningful `—` cells.
- **→ `business-analysis:decision-table`** — inventory 5 becomes `DEC-nnn` tables with a declared hit policy; completeness exposes the combinations the code never handles.
- **→ `business-analysis:dependency-map`** — Edges become `events.md`, `shared-data.md`, `invariants.md`; `be-documenter` writes them, `be-feature-documenter` does not.
- **→ `dev:doc-business-model`** — the three documents: capabilities, rules and decisions the guide (client vocabulary, exact refusal text); Edges the guide's *Related areas* and all of *Behind the scenes*; every inventory, with exact names, the technical reference.
- **→ `code-auditor`** — the findings list; it lands in the technical reference's Findings, never in the plain-language levels.
- **→ `qa-test-case-designer`** — rules and validations are a test basis; thresholds are BVA seeds.

## Version policy

Where rules hide is **stack- and version-specific** — `references/trace-recipes.md` has the per-stack searches, keyed to `CLAUDE.md`'s Stack defaults: **.NET 10 / 8-9** · **Java 21 + Spring Boot 3.x** · **Node 24 / 22**. Take stack and version from orientation; searching for idioms the version does not use silently under-reports rules.
