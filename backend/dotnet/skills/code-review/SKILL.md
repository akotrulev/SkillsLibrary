---
name: conventions-review
description: Use when reviewing C#/.NET code for pattern misuse, over-abstraction, async or DI anti-patterns. Triggers "review this .NET service", "is this CQRS justified". Not for explanations (patterns).
---

# C# / .NET — Reviewer

Reviews C# / .NET backend code against the be-dotnet rule files and produces a findings table. It does **not** rewrite: it points to the fix and hands off to `pattern-writer`.

## The checklist is the rule file

Every check, and the severity it reports, lives in one place: the be-dotnet rule files `dotnet.md` (core), `dotnet-persistence.md`, `dotnet-api.md`, `dotnet-tests.md` and `dotnet-config.md`.

1. **The project's copies first**: `.claude/rules/be-dotnet/` at the project root. The team may have edited them, and its edits win.
2. **Otherwise the plugin's copies**: `backend/dotnet/skills/rules/` (under `${CLAUDE_PLUGIN_ROOT}` in an installed plugin). Say in the report that the project has no installed rules and that `/be-dotnet:rules` installs them.

Read `dotnet.md`, plus each other file whose `paths:` match a file under review, in full before the first finding. A file under review that no glob matches (a backend project the installed globs miss) still gets `dotnet.md`. A rule loaded on its own by the session is not enough: a review needs every file that applies, not just the ones the session happened to open. Never review from memory of the rules, and never add a check the file does not contain; propose it as a rule change instead. Auth-provider specifics (Auth0, Cognito) are checked against the `auth0` / `cognito` skills' Rules sections.

## Version policy

Detect every reviewed project's `<TargetFramework>` first. Do not flag a net8/net9 project for lacking a net10-only API; do flag a net10 project that ignores one available to it, at the severity its rule carries. The rule file's "the codebase wins" line applies: a convention the project follows consistently is not a finding.

## When to use

- A diff or file submitted for review: a service, handler, DI registration, decorator, repository, endpoint
- A pre-merge gate on a change touching `Application/`, `Infrastructure/`, `Program.cs` or a `*Module.cs`
- A second opinion on whether a pattern earns its complexity, or a smell that needs naming

## When NOT to use

- Conceptual lookup → `backend/dotnet/skills/pattern-guide`
- Generating new code → `backend/dotnet/skills/pattern-writer`
- A whole service, saved as a re-runnable report → `backend/dotnet/skills/standards-audit`
- Test-suite review → `qa-dotnet:api-tests-review` / `qa-dotnet:ui-tests-review`

## Procedure

1. Read the rule files, then each changed file end to end.
2. Walk the rules in this order: DI lifetimes, Async, persistence, then the rest. Most blockers live there.
3. Per finding: file and line, the rule broken, a one-sentence fix. The severity is the tag on the rule, never a new judgment.
4. Do not rewrite. Hand off to `backend/dotnet/skills/pattern-writer`.

## Output format

```
| Severity | Location                                  | Issue                                                  | Suggested fix                                                     |
|----------|-------------------------------------------|--------------------------------------------------------|-------------------------------------------------------------------|
| blocker  | Application/Orders/OrderService.cs:54     | `_repo.GetAsync(id).Result` — sync-over-async          | `await _repo.GetAsync(id, ct)`; thread the `CancellationToken`    |
| blocker  | Application/Modules.cs:18                 | Singleton `OrderService` depends on scoped `AppDbContext` | Register `OrderService` scoped                                 |
| major    | Application/Pricing/PricingService.cs:33  | `switch (cart.Mode)` selects the pricing algorithm inline | Extract `IPricingStrategy` with keyed DI; remove the switch    |
| minor    | Application/Orders/OrderService.cs:12     | Concrete `OrderService` is not `sealed`                | Mark it `sealed`                                                  |
```

End with one line: `Rules: project .claude/rules/be-dotnet/ | plugin copy (not installed)`.

## Handoffs

- Need a rewrite → `backend/dotnet/skills/pattern-writer`
- Conceptual lookup → `backend/dotnet/skills/pattern-guide`
- A rule is missing or wrong → edit the project's `.claude/rules/be-dotnet/`; for every project, the plugin's `backend/dotnet/skills/rules/`
- Cross-stack architecture critique → `backend/_shared/code-review`
