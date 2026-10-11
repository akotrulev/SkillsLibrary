---
name: pattern-catalog
description: Use when explaining a design pattern in language-agnostic terms — intent, when to use, when not to, trade-offs, what it looks like across stacks. Triggers: "what is the Strategy pattern", "when should I use Repository", "compare CQRS to plain service+repo", "should I use the Saga pattern here". Do NOT use for stack-specific code, scaffolding, or reviewing (`backend/<stack>/skills/{reference,generator,reviewer}`).
---

# Design Patterns — Shared Reference (language-agnostic)

The "what & when" of design patterns at a level that survives stack switches. Each card explains intent, when to use, when NOT to use, and the most common failure mode. Stack-specific implementations live in `backend/<stack>/skills/pattern-guide`.

## When to use

- "What does pattern X solve?"
- "When should I reach for pattern X vs Y?"
- Comparing patterns conceptually before picking a stack
- Onboarding a new contributor to the library's pattern vocabulary

## When NOT to use

- Need executable code in a specific language → `backend/<stack>/skills/pattern-guide`
- Scaffolding into a repo → `backend/<stack>/skills/pattern-writer`
- Reviewing existing code → `backend/<stack>/skills/code-review`

## Core principles (apply everywhere)

| Principle | Why |
|---|---|
| **Composition over inheritance** | Inheritance couples lifecycle + structure + behavior; composition lets you change each axis independently |
| **Depend on abstractions, not implementations** | Swappable infra, testable code, smaller blast radius on change |
| **One pattern per problem** | Stacking 4 patterns on a CRUD slice adds cognition without solving anything |
| **Wait for the second instance before extracting** | Premature abstraction is more expensive than duplication |
| **Make impossible states unrepresentable** | Sealed types / discriminated unions / tagged structs forcefully prevent illegal combinations |

## Pattern cards

### Strategy

**Intent:** Encapsulate interchangeable algorithms behind a common interface so the caller swaps them without code change.

**When to use:**
- `if`/`else` / `switch` chain selects behavior by a type or mode field
- New variants added regularly
- Variants share input/output shape

**When NOT:**
- Two variants, no growth → method overload or a default + override
- Variants have different shapes → bending the interface is worse than the switch

**Common failure mode:** The abstraction starts pure (one method) and accumulates per-variant exceptions (`if (this is Promotional p) ...` inside the calling code) — sign that the strategies don't really share the shape.

### Decorator

**Intent:** Wrap a service with cross-cutting behavior (logging, retry, caching, metrics) without modifying it.

**When to use:**
- A concern (logging, retry) applies to every method of a service
- You want to mix-and-match per environment (cache in prod, not in dev)
- You can keep concerns separate

**When NOT:**
- One concern, applied once → just write it inline
- Cross-cutting logic that needs the *real* method's identity (transaction boundary) — usually the framework already provides this

**Common failure mode:** A `LoggingAndRetryAndCachingDecorator` fusing concerns — refactor into separate decorators ordered explicitly.

### Repository

**Intent:** Abstract persistence behind a domain-shaped interface.

**When to use:**
- Multiple data sources for one logical store (DB + cache + API)
- The query language leaks too much into domain code
- You have a clear named-query set (`findActiveByCustomer`, `findOverdue`) the type earns

**When NOT:**
- Wrapping `JpaRepository` / `DbContext` / Prisma 1:1 with `Get/Save/Delete` — that's the underlying ORM with extra ceremony
- Single store, simple CRUD

**Common failure mode:** `IFooRepository` exposing `IQueryable<Foo>` / raw query objects — leaks every storage detail, defeats the point.

### CQRS (Command / Query Responsibility Segregation)

**Intent:** Separate read and write models when their shapes diverge enough that one model serves neither well.

**When to use:**
- Real read/write asymmetry (read joins many tables; write is one aggregate)
- Many endpoints / many cross-cutting concerns (pipeline behaviors)
- Event-driven projection of read models from write events

**When NOT:**
- A few endpoints over one aggregate — direct service + repository is fine and cheaper
- "We'll need it later" — adopt when the pain shows, not before

**Common failure mode:** Every CRUD endpoint becomes a Command/Query record + handler + mediator dispatch; net effect = +50% boilerplate, no shape change.

### Factory / Abstract Factory

**Intent:** Encapsulate non-trivial construction decisions; the caller asks for "a thing of kind X" rather than knowing which subtype to `new`.

**When to use:**
- Subtype selection depends on input data
- Construction has dependencies that vary per subtype
- The factory is reused across many call sites

**When NOT:**
- Trivial construction (`new Foo(bar)`) — direct construction is clearer
- Single subtype "for future-proofing"

### Builder

**Intent:** Construct complex objects step by step; fluent, readable, sometimes enforcing invariants per step.

**When to use:**
- 4+ constructor parameters, some optional, many combinations
- Test data factories (see `qa/<stack>/skills/test-data-builder` — this is the canonical use)
- Construction has invariants that the builder enforces

**When NOT:**
- Simple value classes — a record / data class with named parameters does the job

### Specification

**Intent:** Compose predicates over data with `and` / `or` / `not`.

**When to use:**
- Queries combine many filter predicates dynamically
- Same predicate logic must work in-memory and as a DB query (e.g. JPA `Specification` translating to SQL)

**When NOT:**
- One fixed query — don't build a DSL for one shape

### Mediator

**Intent:** Decouple sender and handler via a dispatch surface.

**When to use:**
- Many senders, many handlers, no compile-time coupling desired
- Cross-cutting concerns (logging, validation, transactions) benefit from pipeline behaviors
- In-process command bus / domain event dispatch

**When NOT:**
- Two services calling three handlers — direct method calls are simpler and traceable

### Pipeline / Chain of Responsibility

**Intent:** Stage-by-stage processing where each stage decides to handle or pass.

**When to use:**
- HTTP middleware (auth → throttle → validate → handle)
- ETL: extract → transform → load
- Anywhere "do A then B then C, with B sometimes terminal"

**When NOT:**
- The framework already gives you a middleware / interceptor chain — don't reinvent

### State machine (sealed types)

**Intent:** Make impossible states unrepresentable; allowed transitions are explicit and enforced.

**When to use:**
- Domain entity has a fixed set of states with non-trivial transitions (Order: Pending → Paid → Refunded)
- Side effects vary by state
- You want the compiler to flag missing transitions on additions

**When NOT:**
- Two-state booleans (`isActive`) — just use the bool
- States with no behavior differences — just use a string + check

### Options pattern (typed config)

**Intent:** Replace scattered string-keyed configuration reads with a typed object validated at startup.

**When to use:**
- App reads more than 3-4 config values across the codebase
- Config has structural invariants (range, format, required)
- Misconfiguration should fail at startup, not at first use

**When NOT:**
- One env var read once at startup

### Saga / Process Manager

**Intent:** Coordinate a long-running, multi-step business process spanning multiple services with compensating actions on failure.

**When to use:**
- Workflow crosses multiple services with no shared transaction
- Failure handling is part of the domain (refund on a failed step)
- Steps are observable / queryable mid-flight

**When NOT:**
- All steps fit in one service / one DB transaction
- Failure is unrecoverable anyway — log + alert is enough

### Outbox

**Intent:** Reliably publish events about state changes by writing them in the same DB transaction as the state change, then asynchronously dispatching.

**When to use:**
- Event publishing must be at-least-once even if the broker is down
- Domain state and event publication must agree

**When NOT:**
- Best-effort events for a side-channel notification — fire-and-forget is fine

## Anti-patterns (cross-stack)

- **Pattern stacking** on a CRUD slice (Repository + UoW + Specification + Mediator + Decorator on `GET /foo/{id}`)
- **Anemic-domain + service+repository** where rich domain models would be clearer
- **Premature abstraction** — interface with one implementation, "in case"
- **Service locator** in business code — coupling on a global, untestable
- **God object / god service** — break it up by responsibility
- **Pattern as ceremony** — Builder for a 2-field object, Mediator for a 2-handler app
- **Mixed paradigms** in one slice (CQRS commands + direct repository calls + a saga + a strategy) without a clear architectural rationale

## Decision flow

```
Is this an existing problem the language idiom solves?     → use the idiom (records, sealed types, async, traits)
   ↓ no
Is there a real abstraction surface (≥ 2 implementations)? → introduce a pattern
   ↓ no
Wait. Add when the second instance arrives.
```

## Handoffs

- Specific stack code → `backend/<stack>/skills/pattern-guide` + `backend/<stack>/skills/pattern-writer`
- Reviewing existing code for misuse → `backend/<stack>/skills/code-review` or `backend/_shared/code-review`
- Test data builders → `qa/<stack>/skills/test-data-builder`
