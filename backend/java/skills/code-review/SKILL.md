---
name: be-java-code-review
description: Use when reviewing Java 21 / Spring Boot 3 code for design-pattern misuse, over-abstraction, threading violations, transactional boundary bugs, DI anti-patterns, or modern-Java omissions (no records / sealed types). Triggers: "review this for pattern misuse", "is this CQRS justified", "check for @Transactional misuse". Do NOT use for explanations (`pattern-guide`) or generating new code (`pattern-writer`).
---

# Java Design Patterns — Reviewer

Reviews Java 21 + Spring Boot 3.x code against the patterns and rules enforced by `backend/java/skills/pattern-writer` and the global rules in `CLAUDE.md`. Produces a findings table in the `CLAUDE.md` review format. Does **not** rewrite — points to the fix and hands off to the generator.

## Version policy

Detect the reviewed project's Java release and Spring Boot major first. Don't flag a Java 17 / Spring Boot 2.x project for lacking sealed types, records-as-DTOs, or virtual threads — those are Java 21 / Boot 3.x recipes, not universal rules. Do apply them as findings once the project is confirmed on 21 / 3.x.

## When to use

- Diff / file submitted (service, repository, handler, DI config, decorator)
- Pre-merge gate on PRs touching `src/main/java/com/.../application` / `infrastructure` / `domain`
- Second opinion on whether a pattern earns its complexity
- Spotting modern-Java omissions (string concatenation where records would help, `if-instanceof` where pattern matching applies)

## When NOT to use

- Conceptual lookup → `backend/java/skills/pattern-guide`
- Generating new code → `backend/java/skills/pattern-writer`
- API test review → `qa/java/skills/api-test-author/review`
- UI test review → `qa/java/skills/ui-test-author/review`

## Review checklist

### Threading & async

| Check | Bad sign | Severity |
|---|---|---|
| No `Thread.sleep` in production code | Sleeps anywhere not in tests / retry helpers | major |
| `InterruptedException` re-interrupts or rethrows | `catch (InterruptedException e) { /* swallow */ }` | blocker |
| Virtual threads / async correctly scoped | `@Async` returning `void` swallowing exceptions; `CompletableFuture` chains without error handling | major |
| `ThreadLocal` cleared in finally | `ThreadLocal.set` without remove in a request scope | major |
| No `synchronized` on a single-tenant service that should be stateless | Locks on a Spring singleton's instance fields | major |

### DI & lifecycle

| Check | Bad sign | Severity |
|---|---|---|
| Constructor injection only | `@Autowired` on fields / setters | major |
| Final fields on dependencies | Mutable fields injected | minor |
| One `@Configuration` per module | DI sprinkled across the codebase | minor |
| `@Component` vs `@Service` vs `@Repository` used semantically | `@Component` on everything | nit |
| Bean lifetime / scope is right | Prototype-scoped bean consumed by a singleton without `ObjectProvider` | major |
| `@PostConstruct` work is fast and exception-safe | Slow / fragile work during startup that blocks readiness | major |

### Transactions

| Check | Bad sign | Severity |
|---|---|---|
| `@Transactional` on service methods, not controllers | Controller annotated `@Transactional` | major |
| No `@Transactional` self-invocation | `this.someTxMethod()` called from another method of the same class | blocker |
| Read-only intent declared | `@Transactional` (read-write) on pure reads | minor |
| Propagation specified deliberately when not `REQUIRED` | Implicit `REQUIRED` on nested calls that need a new TX | major |
| Long-running TX absent | Network / external calls inside `@Transactional` | major |

### Pattern application

| Check | Bad sign | Severity |
|---|---|---|
| One pattern per problem | Repository + Specification + UoW + handler + decorator on a CRUD slice | major |
| Repository earns its keep | Spring Data interface that mirrors `JpaRepository` 1:1 | major |
| CQRS justified | Lightweight CQRS for a 2-endpoint service with no read/write asymmetry | major |
| Strategy / Factory replace `switch` chains | Repeated `switch (mode)` across services | major |
| Decorators have one responsibility | `LoggingAndRetryAndCachingDecorator` | major |
| Pipeline / interceptor reuse Spring's existing chains | Hand-rolled middleware where `HandlerInterceptor` / Filter would do | minor |

### Modern Java

| Check | Bad sign | Severity |
|---|---|---|
| Records for value-shaped data | Boilerplate `class` with getters / equals / hashCode for a DTO | minor |
| Sealed types for closed sums | `if-instanceof` chains across many subclasses | major |
| Pattern matching used | Verbose casts after `instanceof` checks | minor |
| `Optional` only as return type | `Optional` field, `Optional` parameter | major |
| `var` for local inference where it improves readability | `Map<String, List<UserDto>> result = ...` repeated needlessly | nit |
| Streams used where loops would be clearer | A 7-line stream that a `for` loop expresses better | nit |

### Null & types

| Check | Bad sign | Severity |
|---|---|---|
| Null returns avoided | `null` returns where `Optional` or sealed `Result` fits | major |
| `@NonNull` / `@Nullable` (JSpecify or JetBrains) on public APIs | No null annotations, no Optional, no documentation | minor |
| `Objects.requireNonNull` at the boundary | Trusting nulls from external input | major |

### Logging & exceptions

| Check | Bad sign | Severity |
|---|---|---|
| SLF4J with placeholders | `log.info("user=" + id)` | major |
| Exceptions logged with the cause | `log.error("Failed: " + e.toString())` | major |
| Catch specific exceptions | `catch (Exception e)` blanket-swallow | major |
| No `e.printStackTrace()` in production | Direct stack-trace print | major |
| Re-throw preserves cause | `throw new RuntimeException(e.getMessage())` losing cause | major |

### Architecture

| Check | Bad sign | Severity |
|---|---|---|
| Domain has no Spring annotations | Domain class importing `@Service` / `@Component` | major |
| Application orchestrates, doesn't know HTTP | Controller calling `EntityManager` / repository directly | major |
| Adapters implement application ports | Application code newing up infrastructure types | major |

### Comments & Javadoc

Load **[`ep-code-comments`](../../../../engineering-practices/code-comments/SKILL.md)** for the rule itself, the complex-flow test that earns a doc comment, the never-comment trivia list, and the severity mapping. This section supplies only the mechanics that differ here.

| Java mechanic | What to check |
|---|---|
| Doc syntax | Javadoc (`/** … */`). `@throws` / `@return` carry real contract — `@return the result` is a **nit** |
| Suppressions needing a reason | `@SuppressWarnings("unchecked")` with nothing recorded |
| Directives, not comments — these stay | Spring / Jackson / Bean Validation annotations |
| Scaffolding to remove | IDE and Maven-archetype header comments in hand-written files |

**The Java corollary:** thread-safety and transaction-boundary constraints are exactly complex-flow case 2 — "must be called inside the transaction", "not safe after `close()`" earn their Javadoc. A comment restating `@Transactional` does not.

## Procedure

1. Read the file end-to-end before findings
2. Walk the checklists, transactions and threading first
3. Per finding: file + line, concrete issue, one-sentence fix
4. Do not rewrite; hand off to `backend/java/skills/pattern-writer`

## Output format

```
| Severity | Location                                          | Issue                                                       | Suggested fix                                                          |
|----------|---------------------------------------------------|-------------------------------------------------------------|------------------------------------------------------------------------|
| blocker  | application/OrderService.java:42                | `this.confirm(...)` calls a `@Transactional` method on self  | Extract `confirm` into a separate `@Service` so Spring proxy applies   |
| major    | application/CheckoutService.java:21             | `switch (mode)` selects pricing logic inline                | Extract `PricingStrategy` with `@Qualifier`; remove switch              |
| major    | infrastructure/PaymentClient.java:55            | Network call inside `@Transactional` method                   | Move HTTP call outside the TX or use a TxOutbox + async dispatch        |
| minor    | domain/Order.java:12                            | Verbose getter/setter `class Order` for a value object        | Convert to `public record Order(...)`                                   |
```

Severities per `CLAUDE.md`:
- **blocker** — ships a bug, breaks rules (self-invocation `@Transactional`, swallowed `InterruptedException`)
- **major** — design/correctness (long TX with network call, wrong layering, pattern stacking)
- **minor** — style / small inconsistency
- **nit** — optional preference

## Anti-patterns to always flag

- **`@Transactional` self-invocation.** Spring's proxy doesn't intercept; the TX never starts.
- **Network / RPC call inside `@Transactional`.** Holds the connection open; spikes pool exhaustion.
- **Field `@Autowired`.** Hides mutability, can't be constructed in tests cleanly.
- **`Optional` field / parameter.** Optional is a return-type convention.
- **`if (x instanceof A) { var a = (A) x; ... } else if (x instanceof B) { ... }`** — pattern matching exists.
- **Boilerplate class doing what a record does.**
- **Static mutable cache field** in a Spring component (`private static Map<...> cache`).
- **`new Thread(...)` / hand-rolled executors in business code.** Use a managed `Executor` / virtual threads.
- **Spring annotations in domain classes.** Domain is framework-agnostic.
- **`e.printStackTrace()`** in production paths.
- **CQRS adopted for two endpoints** "for future-proofing".
- **`@Async` returning `void`.** Exceptions vanish; return `CompletableFuture<?>` and chain `.exceptionally`.
- **Comments compensating for naming, and stale comments.** A body that needs a step-by-step commentary needs extracting; a comment that no longer matches the code is a confident lie. Both per `ep-code-comments` — the fix is the rename or the extraction, never a reword.

## Handoffs

- Need a rewrite → `backend/java/skills/pattern-writer`
- Conceptual lookup → `backend/java/skills/pattern-guide`
- API test review of same PR → `qa/java/skills/api-test-author/review`
- .NET review of cross-stack concerns → `backend/dotnet/skills/code-review`
