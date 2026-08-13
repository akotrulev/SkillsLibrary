---
name: be-shared-code-review
description: Use when the user asks for a language-agnostic critique of pattern usage — pattern stacking, premature abstraction, missing abstractions where they'd help, layering violations. Triggers: "audit our use of patterns", "is this architecture overdesigned", "where are we under-abstracting", "review this for cross-cutting smells". Do NOT use for stack-specific syntax-level reviews (use `backend/<stack>/skills/code-review`).
---

# Design Patterns — Shared Reviewer (language-agnostic)

Reviews codebases or proposed designs at the pattern / architecture altitude — independent of language. Spots stacking, premature abstraction, under-abstraction, layering bleeds, and pattern-as-ceremony. Stack-specific syntax reviews live in `backend/<stack>/skills/code-review`.

## When to use

- Architecture review across multiple services / multiple stacks
- "Is this design overengineered" / "underengineered" question
- Pre-RFC sanity check on a proposed pattern adoption
- Cross-stack consistency audit (Java service + .NET service + TS service should treat patterns the same way)

## When NOT to use

- Per-file syntax-level review → `backend/<stack>/skills/code-review`
- API tests → `qa/<stack>/skills/api-test-author/code-review`
- UI tests → `qa/<stack>/skills/ui-test-author/code-review`
- Page-object architecture → `qa/<stack>/skills/page-object-design`

## Inputs needed

1. **Scope** — one service, one feature, one repo, multiple repos
2. **Architecture style** — Onion / Clean / Hexagonal / vertical slice / "we don't know"
3. **Top symptom** — slow to change, hard to test, hard to understand, hard to onboard
4. **Diagrams** (if any) — file tree + a one-paragraph "how data flows" suffices

## Cross-stack checklist

### Layering

| Check | Bad sign | Severity |
|---|---|---|
| Domain depends on nothing outside itself | Domain class importing framework / ORM / HTTP types | major |
| Application orchestrates; doesn't know HTTP | Controllers calling DB / cache directly | major |
| Infrastructure adapters implement application ports | Application code newing up infrastructure types | major |
| Cross-feature references through public contracts | Feature A reaching into Feature B's internals | major |

### Pattern stacking

| Check | Bad sign | Severity |
|---|---|---|
| One pattern per problem | Repository + UoW + Specification + Mediator + Decorator on CRUD | major |
| Each pattern earns its keep | Pattern adopted "because we'll need it later" | major |
| Patterns named at the layer they belong | A "service" doing repository + mapper + presenter work | major |

### Abstraction

| Check | Bad sign | Severity |
|---|---|---|
| No "one implementation forever" interfaces | `IFooBar` with exactly `FooBar : IFooBar` after 1 year | minor |
| No service locator | Code calls `Container.Resolve<X>()` instead of taking `X` in the constructor | major |
| No god objects | A "manager" or "service" with 25 unrelated methods | major |
| Composition over inheritance for code reuse | Multi-level base classes used to share helpers | major |

### State & purity

| Check | Bad sign | Severity |
|---|---|---|
| No static mutable state | A "global cache" sitting in a static field | blocker |
| Domain immutability where it fits | Mutable aggregates with public setters | minor |
| Concurrency model named | Background work spawning threads / tasks without coordination | major |

### Cross-stack consistency

| Check | Bad sign | Severity |
|---|---|---|
| Same patterns used the same way across services | Service A uses Repository as 1:1 wrapper; Service B uses it as a real abstraction | minor |
| Naming conventions consistent | `*Service` in one stack, `*Manager` in another for the same role | nit |
| Error contracts agree (ProblemDetails / Result-like shape) | Each service invents its own error envelope | major |

### Boundaries

| Check | Bad sign | Severity |
|---|---|---|
| External input parsed / validated at boundary | Raw DTO assigned to domain object | major |
| Outbound calls behind a port | Direct `HttpClient` calls in domain logic | major |
| Persistence is an adapter, not the domain | Aggregates have ORM attributes / decorators | major |

### Cross-cutting concerns

| Check | Bad sign | Severity |
|---|---|---|
| Logging, metrics, tracing applied through decorators / interceptors / middleware | The same logging boilerplate copy-pasted into every method | minor |
| Transaction boundaries explicit | `@Transactional` / `using transaction` sprinkled inconsistently | major |
| Retry / timeout / circuit-breaker policies declared centrally | Each call site invents its own retry loop | minor |

### Comments & self-documentation

Load **[`ep-code-comments`](../../../engineering-practices/code-comments/SKILL.md)** for the rule itself, the complex-flow test that earns a doc comment, the never-comment trivia list, and the severity mapping. This section supplies only the mechanics that differ here. The rule is language-agnostic; the doc-comment syntax is not, so at this altitude judge the *discipline*, not the syntax.

| Check | Bad sign | Severity |
|---|---|---|
| Comment density is consistent across services | One service commented line-by-line, its sibling clean — two teams applying two rules | minor |
| No cross-service copy-pasted doc blocks | The same stale paragraph heading four services' `OrderService`, describing one of them | major |
| Explanation lives in the design, not the code | A comment carrying an architectural decision — that belongs in an ADR, where it can be superseded | minor |

## Output format

```
| Severity | Location                                    | Issue                                                              | Suggested fix                                                                |
|----------|---------------------------------------------|--------------------------------------------------------------------|------------------------------------------------------------------------------|
| blocker  | services/orders (whole module)              | Static cache field on `OrderService` shared across requests          | Move to a request-scoped or `IMemoryCache`/Redis-backed component             |
| major    | services/orders/Domain/Order.cs:8           | `Order` references `Microsoft.EntityFrameworkCore.Entity`            | Move EF mapping out to `Infrastructure/Persistence/OrderEntity` + mapper      |
| major    | services/orders                              | Repository + Specification + Mediator on a 3-endpoint CRUD service   | Drop CQRS and Specification; keep a thin Repository                           |
| minor    | services/orders + services/payments         | Order uses `*Service`; Payments uses `*Manager` for the same role    | Unify naming on `*Service`                                                    |
```

## Anti-patterns to always flag

- **Anemic Domain + thick Service** when a richer aggregate would express the rules better
- **Repository-as-DbSet** — the abstraction doesn't abstract anything
- **CQRS imposed on CRUD** — every Get/Post becomes Command/Query handlers without read/write asymmetry
- **Pattern stacking** on simple slices
- **Premature interface** with one implementation
- **God service** with mixed responsibilities
- **Service locator** anywhere in business code
- **Domain leaking framework types** (ORM attributes, HTTP types in entities)
- **Cross-feature reach-in** through internal namespaces / packages
- **Each service inventing its own error envelope** (one `ProblemDetails` / `Result` shape org-wide)
- **Static mutable state**
- **"We'll need it later" abstractions** — wait for the second instance
- **Hand-rolled cross-cutting** (logging copy-pasted, retry loops per call site) instead of decorators / middleware
- **Comments compensating for naming, and stale comments.** A body that needs a step-by-step commentary needs extracting; a comment that no longer matches the code is a confident lie. Both per `ep-code-comments` — the fix is the rename or the extraction, never a reword.

## Procedure

1. Skim the file tree; sketch the layer map (Domain / Application / Infrastructure / Presentation)
2. Walk the layering checklist first — bleeds compound over time
3. Walk pattern-stacking; flag the heaviest stacking
4. Walk abstraction (under and over)
5. Cross-stack: pick one representative class from each service and check consistency
6. Produce the table; do **not** rewrite

## Handoffs

- Need stack-specific rewrites → `backend/<stack>/skills/pattern-writer`
- Stack-specific syntax review → `backend/<stack>/skills/code-review`
- Page-object architecture (UI tests) → `qa/<stack>/skills/page-object-design`
- Test strategy → `qa/manual/test-strategy`
- Communication of findings to non-engineers → if `communication/stakeholder-updates` is available in your install
