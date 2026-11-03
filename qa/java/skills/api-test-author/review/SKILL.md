---
name: api-tests-review
description: Use when reviewing existing Java API test code (RestAssured + TestNG) for quality. Triggers "review this API test". Not for writing new tests (api-tests).
---

# QA — API Test Reviewer (Java / RestAssured + TestNG)

Reviews Java API test code against the qa-java rule files and the patterns enforced by `qa/java/skills/api-test-author/writer`, `qa/java/skills/api-client-writer`, and `qa/java/skills/api-models` (the DTO-records + `{Resource}Client` dual-overload layering). Produces a findings table in the `CLAUDE.md` review format. Does **not** rewrite — points to the fix and lets the human apply it.

## When to use

- A diff or file is submitted for review (TestNG class, `{Resource}Client`, record DTO)
- Pre-merge gate on a PR that touches `src/test/java/`
- The user wants a second opinion on assertion strategy or error-body coverage

## When NOT to use

- Generating new Java tests → `qa/java/skills/api-test-author/writer`
- .NET reviews → `qa/dotnet/skills/api-test-author/review`
- TypeScript reviews → `qa/typescript/skills/api-test-author/review`
- DTO scaffolding → `qa/java/skills/api-models`
- UI tests → `qa/java/skills/ui-test-author/review`
- Reviewing the overall test strategy / pyramid → `qa/manual/test-strategy`

## Inputs needed

1. **Files** under review — TestNG test class, `{Resource}Client`, record DTOs
2. **Endpoint contract** if available (OpenAPI snippet, sample 4xx body) — needed to grade error-body assertions
3. **Project conventions** that override defaults (e.g. project standardized on `ErrorPojo` rather than `ProblemDetailsDto`)

## The checklist is the rule file

Every check, and the severity it reports, lives in one place: the qa-java rule files `qa-java.md` (core), `qa-java-api.md`, and `qa-java-data.md` when the slice seeds or probes a database.

1. **The project's copies first**: `.claude/rules/qa-java/` at the project root. The team may have edited them, and its edits win.
2. **Otherwise the plugin's copies**: `qa/java/skills/rules/` (under `${CLAUDE_PLUGIN_ROOT}` in an installed plugin). Say in the report that the project has no installed rules and that `/qa-java:rules` installs them.

Read `qa-java.md`, plus each other file whose `paths:` match a file under review, in full before the first finding. A rule loaded on its own by the session is not enough: a review needs every file that applies, not just the ones the session happened to open. Never review from memory of the rules, and never add a check the files do not contain; propose it as a rule change instead. A clock, race or duplicate-delivery test is also held to the hard rules of `qa/java/skills/time-and-concurrency-testing`.

**Version policy.** Detect TestNG, RestAssured or Playwright Java, and allure-java first; the rule files' "the codebase wins" line applies, so a convention the suite follows consistently is not a finding.

## Procedure

1. Confirm imports show TestNG + RestAssured (`import org.testng.annotations.Test;`, `io.restassured.response.Response`).
2. Read the whole vertical slice (test + client + DTOs) before writing findings — cross-file issues are usually the real bugs.
3. Walk the rule files, core first, then `qa-java-api.md`.
4. Per finding: file and line, the rule broken, a one-sentence fix. The severity is the tag on the rule, never a new judgment.
5. **Do not rewrite the code.** Hand off to `qa/java/skills/api-test-author/writer` if the user wants the rewrite.

## Output format

```
| Severity | Location                                                | Issue                                                       | Suggested fix                                                          |
|----------|---------------------------------------------------------|-------------------------------------------------------------|------------------------------------------------------------------------|
| blocker  | tests/order/orders/PostOrderTest.java:67                | `Thread.sleep(2000)` between create and read                | Remove — the create is synchronous; rely on response body              |
| major    | clients/order/OrderClient.java:55                       | Raw `getById` deserializes and returns `OrderDto`           | Return `Response`; deserialization belongs in the typed overload       |
| minor    | clients/order/OrderClient.java:42                       | Inline path literal `"/api/orders/{id}"` repeated in 3 methods | Extract `private static final String GET_BY_ID_PATH`                |
| minor    | tests/order/orders/GetOrderTest.java:14                 | Test name `test1`                                           | Rename to behavior: `Should_ReturnOrder_When_FetchedById`              |
```

End with one line: `Rules: project .claude/rules/qa-java/ | plugin copy (not installed)`.

## Handoffs

- Need a rewrite → `qa/java/skills/api-test-author/writer`
- DTO is wrong → `qa/java/skills/api-models`
- Client layer needs refactor → `qa/java/skills/api-client-writer`
- Whole test pyramid is the issue → `qa/manual/test-strategy`
- .NET sibling → `qa/dotnet/skills/api-test-author/review`
- TypeScript sibling → `qa/typescript/skills/api-test-author/review`
- A rule is missing or wrong → edit the project's `.claude/rules/qa-java/`; for every project, the plugin's `qa/java/skills/rules/`
