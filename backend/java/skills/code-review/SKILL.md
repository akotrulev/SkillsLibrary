---
name: conventions-review
description: Use when reviewing Java/Spring Boot code for pattern misuse, @Transactional, threading or DI anti-patterns. Triggers "review this Spring service". Not for explanations (patterns).
---

# Java / Spring Boot — Reviewer

Reviews Java + Spring Boot code against the be-java rule file and produces a findings table. It does **not** rewrite: it points to the fix and hands off to `pattern-writer`.

## The checklist is the rule file

Every check, and the severity it reports, lives in one place: the be-java rule files `java.md` (core), `java-persistence.md`, `java-tests.md` and `spring-config.md`.

1. **The project's copies first**: `.claude/rules/be-java/` at the project root. The team may have edited them, and its edits win.
2. **Otherwise the plugin's copies**: `backend/java/skills/rules/` (under `${CLAUDE_PLUGIN_ROOT}` in an installed plugin). Say in the report that the project has no installed rules and that `/be-java:rules` installs them.

Read `java.md`, plus each other file whose `paths:` match a file under review, in full before the first finding. A rule loaded on its own by the session is not enough: a review needs every file that applies, not just the ones the session happened to open. Never review from memory of the rules, and never add a check the file does not contain; propose it as a rule change instead.

## Version policy

Detect the Java release and Spring Boot major first. Do not flag a Java 17 / Spring Boot 2.x project for lacking sealed types, record patterns or virtual threads. The rule file's "the codebase wins" line applies: a convention the project follows consistently is not a finding.

## When to use

- A diff or file submitted for review: a service, repository, handler, DI configuration, decorator
- A pre-merge gate on a change touching `domain`, `application` or `infrastructure` code
- A second opinion on whether a pattern earns its complexity

## When NOT to use

- Conceptual lookup → `backend/java/skills/pattern-guide`
- Generating new code → `backend/java/skills/pattern-writer`
- Test-suite review → `qa-java:api-tests-review` / `qa-java:ui-tests-review`

## Procedure

1. Read the rule file, then each changed file end to end.
2. Walk the rules in this order: Transactions, persistence, Threading and async, then the rest. Most blockers live there.
3. Per finding: file and line, the rule broken, a one-sentence fix. The severity is the tag on the rule, never a new judgment.
4. Do not rewrite. Hand off to `backend/java/skills/pattern-writer`.

## Output format

```
| Severity | Location                              | Issue                                                     | Suggested fix                                                        |
|----------|---------------------------------------|-----------------------------------------------------------|----------------------------------------------------------------------|
| blocker  | application/OrderService.java:42      | `this.confirm(...)` calls a `@Transactional` method on self | Move `confirm` to its own `@Service` so the proxy applies            |
| major    | application/CheckoutService.java:21   | `switch (mode)` selects pricing logic inline              | Extract a `PricingStrategy` bean selected by key; remove the switch  |
| major    | infrastructure/PaymentClient.java:55  | Network call inside a `@Transactional` method             | Call after commit, or write an outbox row and dispatch async          |
| minor    | domain/Order.java:12                  | Getter/setter class for a value object                    | `public record Order(...)`                                            |
```

End with one line: `Rules: project .claude/rules/be-java/ | plugin copy (not installed)`.

## Handoffs

- Need a rewrite → `backend/java/skills/pattern-writer`
- Conceptual lookup → `backend/java/skills/pattern-guide`
- A rule is missing or wrong → edit the project's `.claude/rules/be-java/`; for every project, the plugin's `backend/java/skills/rules/`
- Cross-stack architecture critique → `backend/_shared/code-review`
