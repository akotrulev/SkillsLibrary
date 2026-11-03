---
paths:
  - "**/*.java"
---

<!-- be-java rules v1 (2026-11-03): core. Installed by /be-java:rules; edit to fit this project, re-run to compare with the plugin's copy. -->

# Java / Spring Boot code standards

Apply these to every Java file you write, edit or review. The tag after a rule is the severity a review reports: **blocker** ships a bug or breaks a security rule, **major** is a design or correctness problem, **minor** is style, **nit** is preference. Persistence, test and Spring-config rules are separate files that load with those files.

**The codebase wins.** Where this project consistently does something another way, follow the project and do not flag it. Detect the Java release and Spring Boot major before writing: never use a construct the project's version lacks (sealed types, record patterns and virtual threads need Java 21; virtual threads in Spring need Boot 3.2), and never flag a down-level project for lacking one.

## Simplicity

- Write the simplest thing that meets the requirement, then stop. No interface with one implementer, no layer that only forwards, no config knob nothing sets, no wrapper over what Spring already gives you. An abstraction is earned on the second real need. *major, fix by inlining*
- One pattern per problem. Repository + Specification + handler + decorator on one CRUD slice is stacking. *major*
- Command/query handlers only where reads and writes really differ, never for a CRUD slice. *major*
- Cut structure, never correctness: validation, error handling, resource disposal and tests stay.
- Package by feature; one top-level type per file. *minor*

## Dependency injection

- Constructor injection only, dependencies `private final`. Never `@Autowired` on a field or setter. *major*
- No static mutable state; `static final` constants are fine. *major*
- Configuration through a `@ConfigurationProperties` record, not `@Value("${…}")` scattered across classes. *minor*
- One `@Configuration` class per module for bean wiring. *minor*
- A prototype-scoped bean reaches a singleton only through `ObjectProvider`. *major*
- `@PostConstruct` work is fast and cannot fail startup on a transient error. *major*

## Transactions

- `@Transactional` on service methods only, never on controllers; `readOnly = true` on pure reads. *major; minor for readOnly*
- Never call a `@Transactional` method through `this.`: the proxy is bypassed and no transaction starts. Move it to another bean. *blocker*
- No HTTP, messaging or cache call inside a transaction; it holds the connection. Use an outbox or call after commit. *major*
- Propagation other than `REQUIRED` is written out deliberately. *major*

## Threading and async

- No `Thread.sleep` or busy-wait in production code. *major*
- `InterruptedException` restores the interrupt flag (`Thread.currentThread().interrupt()`) or rethrows; never swallowed. *blocker*
- No `new Thread(…)` or hand-rolled executor in business code; use a managed `Executor` or virtual threads. *major*
- `@Async` returns `CompletableFuture<?>`, never `void`, and the chain handles its error. *major*
- A `ThreadLocal` set in a request is removed in `finally`. *major*
- No `synchronized` over a singleton bean's instance fields; make the bean stateless. *major*

## Types

- Records for value-shaped data (DTOs, value objects, events); classes for behaviour. *minor*
- Sealed types and a pattern-matching `switch` for a closed set of cases, not an `instanceof` chain. *major*
- The same `switch (mode)` repeated across services becomes a strategy bean selected by key. *major*
- `Optional` is a return type only, never a field or a parameter. *major*
- No `null` return where `Optional` or a sealed result fits; `Objects.requireNonNull` on external input at the boundary. *major*
- No exception thrown for ordinary control flow where a sealed result fits. *minor*

## Logging, errors and secrets

- SLF4J with placeholders: `log.info("Order {} placed", orderId)`. Never concatenation, `String.format`, `System.out` or `printStackTrace()`. *major*
- The exception is the last argument to `log.error`/`log.warn`, logged once, where it is handled. *major*
- Catch specific exceptions; no `catch (Exception e)` that swallows. A rethrow keeps the cause: `new OrderException("…", e)`. *major*
- Log ids and counts, not whole entities or DTOs.
- New behaviour (an entry point, an outbound call, a background job, a business event) is instrumented as it is built: a log at each decision point, a span around the operation where auto-instrumentation misses it, and a business metric with low-cardinality labels. *major*
- No secret or personal data in a log line, span attribute or metric label, and no secret in code; read it from the environment or a secret store. *blocker*

## Architecture

- Domain classes carry no Spring annotations. *major*
- Controllers call application services; they never touch `EntityManager` or a repository. *major*
- Application code depends on ports it owns; infrastructure implements them. *major*
- In a modular monolith a module reaches another only through that module's public API package: no import of its `internal` package, no `@ManyToOne` to its entities, no join into its schema. *major*

## Comments

- No comments inside method bodies: no step markers, no restating the next line, no commented-out code, no `TODO`. Extract and name the step instead. *minor; major when the comment is wrong*
- Javadoc only where the name cannot carry the meaning: a non-obvious business rule, a constraint on callers (must run inside the transaction, not thread-safe), a deliberate deviation and its reason, or a contract such as `@throws`. Never on getters, records, DTOs or a method whose signature says it all. *nit*
- `@SuppressWarnings` states its reason; IDE and archetype header comments are removed. *minor*
