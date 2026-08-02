---
name: be-shared-codebase-survey
description: Use when an existing backend must be split into functional areas before it can be documented or understood — inventory every entry point, scheduled job, queue consumer, domain module and external client, group them by business capability (not technical layer), and produce a reading plan with an order, a depth, and a coverage ledger, then confirm the split with the human. Triggers "split this codebase into areas", "what are the functional areas here", "plan how to read this service", "we inherited this backend, where do we start". Do NOT use to trace one area in depth (`be-shared-feature-trace`), to write the documentation (`be-shared-business-documentation`), to find defects (`ep-feature-audit`), or to plan new work (`be-shared-solution-blueprint`).
---

# Codebase Survey — the area map and the reading plan

Breadth before depth. A backend of any size cannot be read end-to-end in one pass, and reading it in file order produces notes rather than understanding. This skill produces two things: a **map of functional areas** a business person would recognise, and a **plan for reading them** — which order, from which evidence, to what depth.

It also produces the thing that keeps the whole exercise honest: a **coverage ledger** where every entry point in the system is assigned to exactly one area or explicitly parked. Without it, "we documented the system" means "we documented the parts we happened to open".

**Announce at start:** "I'm using the `be-shared-codebase-survey` skill to map the functional areas and plan the reading pass."

## When to use

- Phase 1 of a `be-documenter` run
- An inherited or long-lived backend needs decomposing before anyone can reason about it
- A `be-planner` `RESUME`/`EXTEND` run needs to know what functional areas already exist in the code

## When NOT to use

- One area is already named and needs tracing → `be-shared-feature-trace`
- The area map already exists and is confirmed → go straight to tracing (re-survey only what the git delta touched)
- The goal is finding defects → `ep-feature-audit` (it decomposes into *surfaces* for fault-finding, not *areas* for comprehension)

## Output

The area map and reading plan. On a `be-documenter` run they are presented for confirmation and then recorded in the KB's `system-overview.md` (per `ba-project-memory`); the coverage ledger persists in the orientation cache so later runs reuse it.

---

## Procedure

### Step 1 — Inventory the surfaces (read-only, breadth-first)

You are looking for **every way the system can be made to do something**. Miss a category and you will miss the areas that live only there — background work and event consumers are where undocumented business rules concentrate, precisely because no UI exposes them.

| Surface | Where to look | Why it matters |
|---|---|---|
| **HTTP entry points** | Controllers, minimal-API/route registrations, `@RestController`, Express/Nest routers, GraphQL resolvers, gRPC services | The obvious surface — and the one a user recognises |
| **Scheduled jobs** | Hosted services, `@Scheduled`, cron registrations, Hangfire/Quartz/Temporal, serverless schedules | Time-driven business rules (expiry, dunning, reminders, reconciliation) live only here |
| **Queue/event consumers** | Message handlers, `@KafkaListener`, SQS/Service Bus/RabbitMQ subscribers, webhook receivers | Reactive rules, and the seams between areas |
| **Domain modules** | Folders/namespaces holding entities, services, aggregates | The vocabulary the system was designed in |
| **Persistence** | Entities, migrations, constraints, triggers, seeds | Constraints *are* business rules — often the only place one is written down |
| **External clients** | HTTP/SDK clients, outbound integrations | Where capability crosses an organisational boundary |
| **Auth surfaces** | Policies, roles, scopes, permission attributes/guards | The actor model, recoverable from nowhere else this cheaply |
| **Feature flags & config** | Flag definitions, options classes, environment config | Behavior that differs per tenant/environment — an area may be half-live |
| **Admin/back-office paths** | Internal-only routes, seeded admin roles, CLI/management commands | A whole class of user nobody thinks to document |

Useful, stack-agnostic first cuts:

```bash
git log --oneline -20 && git ls-files | wc -l
git ls-files | sed 's|/[^/]*$||' | sort | uniq -c | sort -rn | head -40   # where the mass is
grep -rlE '\[Route|\[Http(Get|Post|Put|Patch|Delete)|MapGet|MapPost|@RestController|@RequestMapping|@(Get|Post|Put|Patch|Delete)Mapping|@(Get|Post|Put|Patch|Delete)\(|router\.(get|post|put|patch|delete)|app\.(get|post|put|patch|delete)' --include=* . | head -60
grep -rlE '@Scheduled|BackgroundService|IHostedService|RecurringJob|cron|@Cron' . | head -30
grep -rlE '@KafkaListener|IConsumer<|SqsListener|ServiceBusProcessor|@EventPattern|@RabbitListener|@SqsListener' . | head -30
```

Adapt to what the stack actually uses — the orientation pass already told you which. **Record counts**, not just presence: 4 controllers and 120 controllers imply completely different reading plans.

### Step 2 — Derive the functional areas

A **functional area** is a slice of business capability a non-engineer would recognise and name. The test: *could you say "this part of the system handles ___" to a support lead and have them nod?*

**Group by capability, not by structure:**

| This is an area | This is not |
|---|---|
| Ordering · Billing · Identity & access · Notifications · Catalog · Reporting · Fulfilment | `Controllers` · `Services` · `Repositories` · `Common` · `Utils` — technical layers |
| Subscription lifecycle | `SubscriptionController` — one class is not an area |
| Tenant onboarding | "The `/admin` folder" — a location is not a capability |

Rules that make the map hold up:

- **Name it in business words, not code words.** If the code calls it `PolicyEngine` and the business calls it *pricing rules*, the area is **Pricing rules**, with the code name recorded in the glossary mapping. Every downstream artifact is filed under this name, which is why Step 4 confirms it.
- **The folder structure is a hint, not the answer.** A well-modularised codebase often maps 1:1 and you should say so. A layered one (`Controllers/`, `Services/`, `Data/`) maps to *nothing* — derive areas from the entry points' subject matter instead.
- **An area is one sitting to trace.** Roughly 3–15 entry points. Larger splits (`Billing` → `Invoicing` + `Payments` + `Dunning`); smaller merges, unless it is genuinely standalone.
- **Cross-cutting concerns are not areas.** Auth, logging, config, error handling, telemetry — they are *how* the system works, not *what it does for someone*. Record them once in a Foundations section; do not give them an `areas/` file.
- **Aim for 4–10 areas.** Beyond ~12, either several belong together or the system is really several systems, and that is itself the most valuable finding in the survey.
- **An area with no user is a finding.** Either you have not found its caller, or it is dead. Say which.

### Step 3 — Build the coverage ledger

Every surface from Step 1 gets assigned. This is what makes a later coverage claim checkable rather than rhetorical:

| Surface | Kind | Area | Note |
|---|---|---|---|
| `POST /api/orders` | HTTP | Ordering | |
| `OrderExpiryJob` | Scheduled | Ordering | runs nightly |
| `PaymentWebhookController` | HTTP (inbound webhook) | Billing | anonymous, signature-verified |
| `LegacyImportController` | HTTP | **parked** | no route registration found — likely dead `#observed` |

Parking is legitimate; parking silently is not. Every parked row states **why** (dead, out of scope for this run, owned by another team, deferred to a later batch).

### Step 4 — Write the reading plan

The order matters, and not for tidiness:

1. **Identity & access first.** It defines the *actors* every other area's use cases refer to. Documenting Ordering before you know who a "customer" versus an "account manager" is means rewriting Ordering.
2. **Then the areas that own the core entities** — the nouns other areas reference.
3. **Then the areas that consume them** (billing, notifications, reporting).
4. **Cross-cutting foundations alongside the first area**, since you meet them there anyway.
5. **Background jobs and consumers with the area that owns their entity**, never as a separate "jobs" area — a job is a business rule with a clock attached.

Then, per area, state the plan:

| Area | Entry points | Depth | Primary evidence | Est. |
|---|---|---|---|---|
| Identity & access | 6 HTTP, 1 job | full | auth policies, user entity, registration flow | 1 pass |
| Ordering | 12 HTTP, 2 jobs, 1 consumer | full | order aggregate, state transitions, `OrderService` | 2 passes |
| Reporting | 9 HTTP | shallow | read-only projections; rules live upstream | 1 pass |

**Depth is a real choice.** `full` (every rule, every branch, every failure path) for areas where the business logic lives; `shallow` (capabilities and actors only) for pass-through, read-only, or CRUD-only areas. Documenting a read-only reporting area to the same depth as a pricing engine wastes the run's budget on the part with the fewest rules.

### Step 5 — Confirm with the human (blocking)

Present in **one message**: the area table, the coverage ledger summary, the reading order with its reason, the depth per area, and what is parked. Then ask.

Confirm these three things specifically, because they are the ones that are expensive to change later:

1. **Are these the right area names?** — you derived them from code; the business may call them something else, and every artifact gets filed under them.
2. **Is the split right?** — should anything merge or divide.
3. **Is the scope right?** — everything, or a subset first; anything parked that should not be.

Use the harness's structured-question tool if one is available. Do not begin tracing before the answer: a rename after Phase 4 means re-filing every artifact and re-writing every cross-reference.

If the human has no opinion (common — they may know the business but not the codebase), say which names you are least confident in and proceed on your own proposal, marking those `#inferred` in `system-overview.md`.

---

## Area map template

```markdown
## Functional areas

| # | Area | What it does for users | Actors | Entry points | Depth | Confidence |
|---|---|---|---|---|---|---|
| AREA-001 | Identity & access | Sign-up, sign-in, roles, tenant membership | Customer, Admin | 6 HTTP, 1 job | full | `#observed` |

## Foundations (cross-cutting, not areas)
| Concern | Approach | Where |
|---|---|---|
| Authorization | Permission claims on JWT, policy per endpoint | `Auth/Policies.cs` |

## Coverage ledger
| Surface | Kind | Area | Note |
|---|---|---|---|

## Reading plan
| Order | Area | Depth | Primary evidence | Why this position |
|---|---|---|---|---|

## Parked
| Surface | Why | Revisit when |
|---|---|---|

## Survey findings
<!-- Things worth saying before any tracing starts: dead code, an area with no caller,
     a system that is really two systems, a module with no tests and no comments,
     a vocabulary clash between two areas. Each with file:line. -->
```

## Self-check before handing off

1. Every surface from Step 1 appears exactly once in the coverage ledger — assigned or parked with a reason.
2. No area is named after a technical layer, a class, or a folder.
3. Every area has at least one entry point and at least one plausible human or system actor.
4. Cross-cutting concerns are in Foundations, not in `areas/`.
5. The reading order puts identity/actors first and consumers last, and says why.
6. Depth is assigned per area and justified, not uniform by default.
7. The split was **confirmed** — or the human declined to weigh in, and the low-confidence names are marked `#inferred`.

## Handoffs

- **→ `be-shared-feature-trace`** — the reading plan drives it, one area at a time, in the confirmed order.
- **→ `be-shared-business-documentation`** — the area names become `areas/<area>.md`; the Foundations table becomes part of `system-overview.md`.
- **→ `ba-project-memory`** — the area map is recorded in `system-overview.md` under the KB contract.
- **→ `code-auditor`** — if the survey's findings are dominated by defects rather than capabilities, the user wants an audit, not documentation. Say so.
- **→ `be-shared-solution-blueprint`** — a confirmed area map of an existing system is directly reusable as the functional-area decomposition of a plan to extend it.

## Version policy

Surface detection is **stack-keyed**, per `CLAUDE.md`'s Stack defaults: **.NET** (attribute routing vs minimal APIs vs `MapGroup`; `IHostedService`/`BackgroundService`; `IConsumer<T>`) · **Java + Spring Boot 3.x** (`@RestController`/`@RequestMapping`, `@Scheduled`, `@KafkaListener`, `@RabbitListener`) · **Node 24/22** (Express/Fastify routers, Nest `@Controller`/`@EventPattern`/`@Cron`, serverless handler manifests). Take the stack and version from the orientation pass and search the idioms that version actually uses — a survey that greps for the wrong idiom silently under-reports entry points, which is the worst failure this skill can have.
