---
name: api-tests-review
description: Use when reviewing existing .NET API test code (NUnit + RestSharp) for quality. Triggers "review this API test". Not for writing new tests (api-tests).
---

# QA — API Test Reviewer (.NET / NUnit + RestSharp)

Reviews .NET API test code (tests, clients, DTOs) against the qa-dotnet rule files. Produces a findings table in the `CLAUDE.md` review format. Does **not** rewrite — points to the fix and lets the human apply it.

## When to use

- A diff or file is submitted for review (test fixture, RestSharp client, DTO)
- Pre-merge gate on a PR that touches `ApiTests/`
- The user wants a second opinion on assertion strategy or `ProblemDetails` coverage

## When NOT to use

- Generating new .NET tests → `qa/dotnet/skills/api-test-author/writer`
- Java reviews → `qa/java/skills/api-test-author/review`
- TypeScript reviews → `qa/typescript/skills/api-test-author/review`
- DTO scaffolding → `qa/dotnet/skills/api-models`
- UI tests → `qa/dotnet/skills/ui-test-author/review`
- Reviewing the overall test strategy / pyramid → `qa/manual/test-strategy`

## Inputs needed

1. **Files** under review — test fixture, RestSharp client, DTO
2. **Endpoint contract** if available (OpenAPI snippet, sample 4xx body) — needed to grade `ProblemDetails` / error-body assertions
3. **Project conventions** that override defaults (e.g. project standardized on `ErrorDto` rather than `ProblemDetailsDto`)

## The checklist is the rule file

Every check, and the severity it reports, lives in one place: the qa-dotnet rule files `automation.md` (core), `api.md`, and `test-data.md`, `db-verification.md` or `suite-config.md` when the files under review match their `paths:`.

1. **The project's copies first**: `.claude/rules/qa-dotnet/` at the project root. The team may have edited them, and its edits win.
2. **Otherwise the plugin's copies**: `qa/dotnet/skills/rules/` (under `${CLAUDE_PLUGIN_ROOT}` in an installed plugin). Say in the report that the project has no installed rules and that `/qa-dotnet:rules` installs them.

Read `automation.md` and `api.md`, plus each other file whose `paths:` match a file under review, in full before the first finding. A rule loaded on its own by the session is not enough: a review needs every file that applies. Never review from memory of the rules, and never add a check the files do not contain; propose it as a rule change instead.

## Version policy

Detect the TFM, NUnit major and client library first (`RestSharp`, `Microsoft.Playwright`, `HttpClient`). The rule file's "the codebase wins" line applies: a convention the suite follows consistently (an established naming shape, an `ErrorDto` in place of `ProblemDetailsDto`) is not a finding.

## Procedure

1. Read the rule files, then the whole of each file under review (test, client and DTO together); cross-file issues are usually the real bugs.
2. Walk the rules in this order: assertions (one value, exact status, `ProblemDetails`), errors and cleanup, async and waiting, then the rest. Most blockers live there.
3. Per finding: file and line, the rule broken, a one-sentence fix. The severity is the tag on the rule, never a new judgment.
4. **Do not rewrite the code.** Hand off to `qa/dotnet/skills/api-test-author/writer` (or `playwright`) if the user wants the rewrite.

## Output format

```
| Severity | Location                                          | Issue                                                       | Suggested fix                                                          |
|----------|---------------------------------------------------|-------------------------------------------------------------|------------------------------------------------------------------------|
| blocker  | ApiTests/Tests/OrderTests.cs:67                   | `Thread.Sleep(2000)` between create and read                | Remove — the create is synchronous; rely on response body              |
| major    | ApiTests/Tests/OrderTests.cs:88                   | 400 test asserts only `StatusCode`, ignores ProblemDetails  | Apply strict template: assert Type/Title/Status + `Errors["Amount"]`   |
| minor    | ApiTests/Clients/OrderClient.cs:42                | Raw integer `200` in expected status                        | Use `HttpStatusCode.OK`                                                |
| minor    | ApiTests/Tests/OrderTests.cs:14                   | Test name `Test1`                                           | Rename to behavior: `Should_ReturnTheOrder_When_TheIdExists`           |
```

End with one line: `Rules: project .claude/rules/qa-dotnet/ | plugin copy (not installed)`.

## Handoffs

- A rule is missing or wrong → edit the project's `.claude/rules/qa-dotnet/`; for every project, the plugin's `qa/dotnet/skills/rules/`
- Need a rewrite → `qa/dotnet/skills/api-test-author/writer`
- DTO is wrong → `qa/dotnet/skills/api-models`
- Client layer needs refactor → `qa/dotnet/skills/api-client-writer`
- Whole test pyramid is the issue → `qa/manual/test-strategy`
- Java sibling → `qa/java/skills/api-test-author/review`
- TypeScript sibling → `qa/typescript/skills/api-test-author/review`
