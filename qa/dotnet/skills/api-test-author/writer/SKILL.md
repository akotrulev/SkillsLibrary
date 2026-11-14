---
name: api-tests
description: Use when writing .NET REST API tests with NUnit + RestSharp. Triggers "write an API test for X", "automate these test cases". Not for Playwright-runner API tests (api-tests-playwright).
---

# QA — API Test Writer (.NET)

Scaffolds NUnit-based API tests against a REST backend that emits a uniform `ProblemDetails` envelope on every 4xx. Output mirrors a single canonical fixture, applies a rich happy-path template for 2xx and a strict `ProblemDetails` template for 4xx.

## When to use

- New `{Resource}Tests.cs` fixture in `ApiTests/Tests/`
- Adding test methods (happy path, 4xx, 401) to an existing fixture
- Generating parameterized validation tests against a single endpoint

## When NOT to use

- UI / browser tests → `qa/dotnet/skills/ui-test-author`
- Generating the typed client itself → `qa/dotnet/skills/api-client-writer`
- Generating request/response DTOs → `qa/dotnet/skills/api-models`
- Performance / load tests → `qa/dotnet/skills/load-testing`

## Source of truth & input modes

Before generating, establish the **source of truth** — one of:

1. **An OpenAPI/Swagger spec** — derive the resources, endpoints, body shapes, and the scenario set per endpoint (happy, 401, 404, 400 validation, boundary) directly from it. Do not re-ask what the spec already states. Missing DTOs/clients are generated first via `qa/dotnet/skills/api-models` then `qa/dotnet/skills/api-client-writer`.
2. **A formal test-case document** (TC-IDs, e.g. from `qa/manual/test-case-writer`) — map **one test method per TC-ID** and carry the id forward for traceability (below). Generate only the DTOs/clients the planned cases actually need.
3. **A verbal scenario list** — fall back to the interactive Generation-steps questions below.

**TC-ID traceability.** When a test-case document drives generation, tag each test so Allure can trace test → case. Use `[AllureTms("TC-USER-001", "<link or id>")]` where a TMS is wired, otherwise `[Property("TmsLink", "TC-USER-001")]` (or an `[AllureStory("TC-USER-001 — …")]` carrying the id). Every TC-ID must map to a generated test or be explicitly deferred.

## Canonical example

The reference fixture is `ApiTests/Tests/RecurringDepositTests.cs`. Mirror its structure: rich happy-path assertions for 200 responses, strict `ProblemDetails` validation for 4xx responses. Skim it before generating new tests against a similar resource.

## Deep-dive reference

These sections live in `references/details.md` — **read it when the task touches them**: **Templates**.

## Generation checks

Two checks bracket the code, both in [`references/generation-checks.md`](references/generation-checks.md):
**oracles first** — a scenario × oracle table (response, data, negative, side effect), taken from the
contract or the requirement and never from the code, before any test is written; and a **hallucination gate**
after — every endpoint (and test id) the new tests use is looked up in the stored OpenAPI spec (and the app
source) and reported `MISSING` instead of guessed.

## Rules

The standards this skill's output must meet are the qa-dotnet rule files, not a list here: `automation.md` and `api.md`. Read the project's copy in `.claude/rules/qa-dotnet/`, or the plugin's in `qa/dotnet/skills/rules/` when the project has not installed them (`/qa-dotnet:rules` does). Where they and this skill's recipes disagree, the rule files win.

## Conventions

### Fixture shape (new fixtures only)
- File `ApiTests/Tests/{Resource}Tests.cs`; class `{Resource}Tests : BaseApiTest`, namespace `ApiTests.Tests`, `[TestFixture]` on the class.
- The client is created inside each test from the single `AuthToken` that `BaseApiTest` exposes; an unauthenticated client gets `string.Empty` and is constructed inline. `[SetUp]` may create test data (templates in `references/details.md`).
- Names follow the rule file (`Should_X_When_Y`); a suite already on `[Action]_[Condition]_[ExpectedOutcome]` keeps its shape. Each endpoint's anonymous test is `Should_ReturnUnauthorized_When_NotAuthenticated` (or the suite's equivalent) and uses the 401 template.

### Assertion templates
- **Happy path (200):** the typed overload; assert every request field on the response, every server-generated field (`Status`, `CreatedOn`, `UpdatedOn`, …), then `GetById` for the persistence round-trip. A one-field check is only for a trivial read.
- **400 / 404 / 422:** the raw overload, `AttachBody(response)`, then status → `Deserialize<ProblemDetailsDto>(response)` → tracking fields (`TraceId`, `RequestId`, `Instance`) → `Type`, `Title`, `Status` → the `Errors` dictionary (400) or `ErrorCode` and extension fields (404/422). `TryProblem` is the lenient helper for a documented defect whose body may not parse (a 500).
- `Deserialize<T>(response)` on `BaseApiTest` is the one place that catches `JsonException`: it rethrows with the property path, the target type and the raw body, so a parse failure reads as contract drift.

### Test data setup and cleanup
- `[SetUp]` / `[OneTimeSetUp]` may create data into instance fields; a `[TearDown]` deletes it. Ids created in a test body go into `_createdIds` on the fixture and `[TearDown]` deletes them.
- A precondition only some tests need is set up inline as their first step, not in `[SetUp]`. Client instances in `[SetUp]` / `[TearDown]` are created inline, not stored.
- **Trading accounts** are fetched, never created: `new AccountClient(AuthToken).GetAll(HttpStatusCode.OK).First(a => a.AccountType == "Trading")`; no `[TearDown]` for them.
- **Payment methods** follow tokenize → create: `PaymentMethodClient.Tokenize(accountId, PaysafeTestCards.Build(PaysafeTestCard.VisaUs1, currency), HttpStatusCode.OK)` returns a `TokenizedMethodDto`; pass its `Token` and `Last4` into `MethodInDto` with `Type = "Card"`, `ExpiryMonth` / `ExpiryYear` (`PaysafeTestCards.DefaultExpiryMonth/Year`) and the currency. Never hardcode a card number; use the `PaysafeTestCards` enum in `ApiTests/TestData/PaysafeTestCards.cs`. Delete with `methodClient.Delete(account.Id, method.Id)` in `[TearDown]`; `[OneTimeSetUp]` when the method is read-only across tests, `[SetUp]` when tests mutate or delete it.

### Deserialization
- Positive tests get the DTO from the typed overload; negative or structural tests use `Deserialize<T>(response)`.
- A plain array is `Deserialize<List<T>>(response)`; an envelope (`{ "data": [...] }`) gets a `{Resource}ListDto` with a `Data` property, generated with `qa/dotnet/skills/api-models`.

## Generation steps

0. Establish the **source of truth** (see *Source of truth & input modes*). From an **OpenAPI/Swagger spec**, derive resources, endpoints, body shapes, and the scenario set per endpoint — skip the interactive questions the spec already answers. From a **test-case document**, map one test method per TC-ID and tag it for traceability. Only fall back to steps 1–3 for verbal scenarios.
1. Ask: **new fixture** or **adding methods to an existing fixture**?
2. Ask: which client/resource to use.
3. Ask: which scenario(s) to cover (happy path, unauthorized, not found, validation error, etc.).
4. Write the scenario × oracle table (`references/generation-checks.md` §1) — no test code before it exists.
5. Read the canonical example `ApiTests/Tests/RecurringDepositTests.cs` to confirm the expected style for both templates before generating.
6. If the DTO doesn't exist yet, use the `qa/dotnet/skills/api-models` skill to generate it. If the test asserts a `ProblemDetails` extension field that's missing from `ProblemDetailsDto` (e.g. a new `{entity}Id`), add it via `qa/dotnet/skills/api-models` rather than reading from `Errors`.
7. Generate the file or add the method(s) to the target fixture:
   - **200 happy path** → apply the rich happy-path template (request fields + server-generated fields + `GetById` round-trip in `Assert.Multiple`). For Pause/Resume/Cancel-style action endpoints, assert state change + `UpdatedOn` + invariants.
   - **400 validation** → apply the strict ProblemDetails template; expect `Type="ValidationViolation"`, `Title="Validation violation"`, and `Errors["FieldName"]` containing the FluentValidation message fragment.
   - **404 not found** → apply the strict ProblemDetails template; expect `Type="BusinessViolation"`, `Title="Business rule violation"`, `ErrorCode="{ENTITY}_NOT_FOUND"`, plus the relevant `{entity}Id`/`accountId` extension fields.
   - **422 invalid state / business rule** → apply the strict ProblemDetails template; expect `Type="BusinessViolation"`, `Title="Business rule violation"`, `ErrorCode="INVALID_TRANSACTION_STATE"` (or other domain code), plus `transactionId`/`currentStatus`/`expectedStatus` extensions where applicable.
   - **401 unauthorized** → single status-code assertion; no body validation.
   - For positive tests, use the typed client overload (`{resource}Client.{Method}(HttpStatusCode.OK)`); if the client does not yet have one, add it following the `qa/dotnet/skills/api-client-writer` skill.
   - For 4xx tests, use the raw `RestResponse` overload, call `AttachBody(response)`, then `Deserialize<ProblemDetailsDto>(response)` from `BaseApiTest`.
   - Use explicit types (no `var`) for all local variables in test methods.
   - Track any resource the test creates (`_createdIds.Add(dto.Id)`) and delete it in `[TearDown]` — no `try`/`finally` in the test, no `try`/`catch` in the teardown.
8. Run the hallucination gate (`references/generation-checks.md` §2); report every `MISSING` endpoint and write no test against it.
9. Run `dotnet build ApiTests/ApiTests.csproj` — expect 0 errors.
