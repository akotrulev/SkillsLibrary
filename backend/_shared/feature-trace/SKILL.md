---
name: doc-feature-trace
description: Use when one functional area of an existing backend must be read in depth to recover what it actually does — following every entry point through auth, validation, domain rules, persistence and failure into six file:line-evidenced inventories. Triggers "trace how this area works", "what business rules are in this module". Do NOT use to split a codebase into areas first (`dev:doc-codebase-survey`), write documentation (`dev:doc-business-model`), or find defects (`dev:audit-feature`).
---

# Feature Trace — recovering behavior from code

Depth, one area at a time. The output is not prose — it is **structured evidence**: six inventories, every item tagged with the file and line it came from, ready for `dev:doc-business-model` to turn into something a business reader can use.

The discipline that makes it worth doing: **separate what the code does from what you think it means.** Every item you extract is `#observed` with a `file:line` read this session. Intent is a separate, clearly-marked layer — and where intent is not recoverable, the honest output is the behavior plus a question.

**Prerequisite:** a confirmed area from `dev:doc-codebase-survey`, with its entry points and its assigned depth.

## When to use

- Step 2 of a `be-documenter` run, once the area split is confirmed
- Someone needs to know what a specific module enforces before changing it
- A `REFRESH` run re-tracing an area whose code has moved

## When NOT to use

- The areas are not mapped yet → `dev:doc-codebase-survey`
- The deliverable is defect findings with severities → `dev:audit-feature`. **Same technique, different question**: that skill asks what is wrong, this asks what is true. If you notice a defect while tracing, record it as a finding to report — do not switch modes and start auditing
- The deliverable is the readable write-up → that is the next skill; this one produces the evidence it consumes

## Output

Per-area structured evidence. On a `be-documenter` run it is working material that feeds Steps 3–4; it is not itself a KB artifact, and it is not written into `docs/business-model/` in raw form. One rule for where it lives: evidence consumed within the session stays in the session (or the scratchpad, if the area is large); evidence that must survive the session goes to `.trace/`, below.

**Multi-session runs persist the trace.** When a FULL run spans sessions (a large codebase documented in confirmed batches), a session that ends between Trace and Write would otherwise lose its evidence and force a full re-read. So: on a run that will not reach Write in the same session, persist each completed area's evidence inventory to **`docs/business-model/.trace/<area>.md`** — working files, never listed in `INDEX.md`, each opening with the line:

```markdown
**Working trace by `be-documenter` @ <commit> on <date> — not a KB artifact**
``` On resume, a persisted trace is a **lead, not evidence**: spot-check three of its `file:line` citations against the current commit — if the commit moved or a spot-check fails, re-trace the area rather than trusting the file. Step 5 (Consolidate) deletes `.trace/` once every area's write-up cites its evidence; a leftover `.trace/` folder is a sign a run ended before consolidation.

---

## The trace path

For **every** entry point in the area, walk this path in order. Each stop answers a different business question, and skipping one loses a category of rule permanently:

| Stop | The business question it answers | What to extract |
|---|---|---|
| 1. **Entry point** | What can someone ask the system to do? | The capability, in a verb phrase; who can invoke it |
| 2. **Authorization** | Who is allowed to do it? | Roles, permissions, scopes; ownership and tenancy checks; the difference between "any user" and "the owner" |
| 3. **Input validation** | What counts as a valid request? | Required fields, formats, ranges, allowed values, cross-field rules |
| 4. **Preconditions & lookups** | What must already be true? | Referenced things that must exist, be visible, and be in a permitted state |
| 5. **Orchestration** | What happens, in what order? | The steps; what is transactional; what is best-effort; what is fire-and-forget |
| 6. **Domain rules** | What does the business logic actually decide? | Every branch, threshold, calculation, and eligibility condition — **the highest-value stop** |
| 7. **Persistence** | What is remembered, and what does it constrain? | State changes, DB constraints (constraints *are* rules), audit trails, soft deletes |
| 8. **External calls** | What crosses an organisational boundary? | Which system, when, what is sent, what happens if it fails |
| 9. **Events emitted** | What else reacts? | Events/messages published — these are the seams to other areas |
| 10. **Failure paths** | What does the user experience when it goes wrong? | Every error branch, and what it means in business terms |

**Follow the call, do not skim the file.** A handler that reads as five clean lines routinely delegates to a service holding twenty conditions. Depth `full` means you followed those calls to where decisions are actually made; depth `shallow` means you stopped at stop 5 and said so.

## The six inventories

### 1. Capabilities
What a user or system can make this area do. One line each, as a verb phrase in business language, with its actor and its entry point.

> "A customer can cancel an order that has not yet shipped (`OrdersController.cs:88`)" `#observed`

### 2. Business rules
Every condition, threshold, calculation and eligibility test the code enforces. This is the inventory the business will care most about, and the one most likely to exist nowhere else.

| Rule | Condition | Effect | Evidence | Tier |
|---|---|---|---|---|
| Refund window | Order closed more than 30 days ago | Refund rejected | `RefundService.cs:88` | `#observed` |
| Free shipping | Order total ≥ 5000 minor units and tenant has `freeShipping` enabled | Shipping cost set to 0 | `ShippingCalculator.cs:41` | `#observed` |

Write the rule as the business would state it. **Record the number, not a rounding of it** — "30 days" not "about a month" — because the exact value is usually the thing someone needs to check.

### 3. Validations & gates
Authorization checks, input validation, precondition checks, state guards. Each with what happens when it fails, in user terms. This inventory doubles as the security-review starting map and as the negative-test matrix downstream.

### 4. Entity states & transitions
Per entity the area owns: the states, what moves between them, who can trigger each move, and what is blocked. Recovered from enums, status columns, guard clauses, and the transitions the code *refuses*.

**The refusals matter as much as the transitions.** A missing arrow is a business rule ("a shipped order can never go back to pending"), and it is usually written down nowhere else.

### 5. Decision points
Any branch where more than two inputs combine to select an outcome — pricing, eligibility, routing, discounting, risk scoring. Capture the inputs, the combinations, and the result of each. These become decision tables in the next step, and building the table is what exposes the gaps and contradictions the code has been quietly living with.

### 6. Integrations
Per external system: what triggers the call, what is sent (business-level, not payload schemas), what comes back, and — critically — **what happens when it fails**. Timeout, retry, fallback, or unhandled. "Unhandled" is a finding.

## Evidence rules

- **Every item carries `file:line`, read this session.** Not from the orientation cache, not from a prior run, not from memory. The map says where to look; only the read is evidence.
- **Negative claims name their search.** "No rate limiting in this area" is only usable as: *searched for `RateLimit|Throttle|Bucket` across `src/Ordering/**` — no matches* `#observed`.
- **Tier every item.** `#observed` for behavior; `#inferred` for intent, purpose, or "this is probably for X". Never `#confirmed`.
- **Comments and tests are evidence of intent, not of behavior.** A comment saying "30-day window per card scheme rules" is a strong `#inferred` for *why*; the code is the only evidence of *what*. A stale comment contradicting the code is a finding worth reporting.
- **Commit history is a legitimate source for intent** — `git log -S'<the constant>'` or `git log --follow <file>` frequently surfaces the ticket or the reason. Cite it, and it is still `#inferred` unless the message states the business rule outright.
- **Config and flags change the answer.** A rule inside `if (featureFlags.NewPricing)` is conditional behavior; record both branches and which environments run which, or mark it `[TBD - who knows the flag state]`.

## What to do with things that are not documentation

You are tracing, not auditing — but you will find things. Handle them like this, and keep moving:

| Found | Do |
|---|---|
| A defect (wrong calculation, missing check, unhandled failure) | Record it as a **finding to report**, with evidence. Do not fix it, do not switch to auditing, and do not write it into the business documentation as if it were intended behavior |
| Unreachable code (no route, dead flag, no caller) | Record it as unreachable. **Do not document it as a capability** — this is the most common way generated documentation goes wrong |
| Two rules that contradict each other | Record both with evidence; escalate. `business-analyst` owns which one wins |
| A rule whose purpose is unrecoverable | Record the behavior, add an open question. This is a normal, expected outcome — not a failure of the trace |
| Something that should obviously change | Note it, route it to the owning `be-<stack>` agent. You do not change code |

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
| # | Check | Applies to | On failure (user-visible) | Evidence |

### Entity states
| Entity | States | Transitions (trigger → from → to) | Refused transitions | Evidence |

### Decision points
| # | Decision | Inputs | Outcomes | Evidence |

### Integrations
| System | Trigger | Sends | Expects | On failure | Evidence |

### Intent notes (`#inferred`)
| Observation | Probable purpose | Basis (comment / test / commit / naming) | Question for the business |

### Findings (not documentation)
| # | What | Evidence | Kind (defect / unreachable / contradiction / stale comment) |
```

## Self-check before handing off

1. Every entry point assigned to this area in the coverage ledger was traced, or is listed as not traced with a reason.
2. Every inventory item has `file:line` read this session; every negative claim names its search.
3. Every item is tiered; no `#confirmed`.
4. The domain-rules inventory is not empty. An area with genuinely no business rules is a pass-through — say so explicitly, because an empty rules table usually means the trace stopped at stop 5.
5. Refused state transitions are recorded, not just the permitted ones.
6. Every integration has a stated failure behavior, including "unhandled".
7. Findings are kept out of the documentation stream and into the findings list.

## Handoffs

- **→ `business-analysis:process-flow`** — the orchestration and failure paths become `FLOW-nnn` diagrams.
- **→ `business-analysis:state-grid`** — inventory 4 becomes `ENT-nnn` state × event grids; the refused transitions are its `—` cells with meaning.
- **→ `business-analysis:decision-table`** — inventory 5 becomes `DEC-nnn` tables with a declared hit policy; the completeness check exposes the input combinations the code never handles.
- **→ `dev:doc-business-model`** — all six inventories become the area's end-user write-up.
- **→ `code-auditor`** — the findings list, when it turns out to be the interesting part.
- **→ `qa-test-case-designer`** — the rules and validations are a test basis; the thresholds are BVA seeds.

## Version policy

Where business rules hide is **stack- and version-specific** — see `references/trace-recipes.md` for the per-stack search patterns. Keyed to `CLAUDE.md`'s Stack defaults: **.NET 10 / 8-9** · **Java 21 + Spring Boot 3.x** · **Node 24 / 22**. Take the stack and version from the orientation pass; searching for idioms the project's version does not use silently under-reports rules, and an under-reported rule becomes a documented system that quietly lies.
