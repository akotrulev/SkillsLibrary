---
name: api-tests
description: Use when scaffolding .NET API tests (NUnit + RestSharp) — new fixtures, new test methods on an existing `*Tests.cs`, or a specific scenario (happy path, 4xx with ProblemDetails, 401). Triggers "write an API test for X", "add a 404 test to YTests", "scaffold an ApiTests fixture for Z". Not for GraphQL (`api-test-author/graphql`), gRPC (`api-test-author/grpc`), or Playwright-based API tests (`api-test-author/playwright`).
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

## Rules

### Class structure (new fixtures only)
- File: `ApiTests/Tests/{Resource}Tests.cs`
- Class name: `{Resource}Tests` — PascalCase resource noun + `Tests` suffix (e.g. `UserTests`, `PostTests`)
- Always inherit from `BaseApiTest`
- Namespace: `ApiTests.Tests`
- Decorate the class with `[TestFixture]`

### Test method rules
- Naming: `[Action]_[Condition]_[ExpectedOutcome]` — e.g. `GetUser_ById_ReturnsOk`, `DeleteUser_WhenNotAuthenticated_ReturnsUnauthorized`
- Every test must have `[Test]` (or `[TestCase]`) + `[AllureFeature]` + `[AllureStory]` + `[AllureSeverity]`
- Instantiate the client **inside** each test method. Exception: `[SetUp]` may create test data (see the Templates section in `references/details.md`)
- Follow Arrange / Act / Assert structure within the method body
- **No `var`** — always use explicit types for local variables when the type is known (e.g. `RestResponse response`, `WatchlistGroupDto group`, `List<UserDto> users`)
- **Meaningful client variable names** — name the client variable after its concrete type in camelCase, not a generic `client` (e.g. `watchlistClient`, `authLoginClient`). For unauthenticated calls in negative tests, construct the client inline without storing in a variable.

### Auth token convention
`BaseApiTest` exposes a single `AuthToken` property for authenticated calls. Pass it into every client constructor.

For unauthenticated negative tests, pass `string.Empty` to the client constructor.

### Unauthorized access coverage
- Every endpoint must have a corresponding test that calls it **without an auth token** and asserts `HttpStatusCode.Unauthorized`
- Pass `string.Empty` as the `AuthToken` argument to create an unauthenticated client
- Naming convention: `{Action}_WhenNotAuthenticated_ReturnsUnauthorized` — e.g. `GetUser_WhenNotAuthenticated_ReturnsUnauthorized`
- Use the 401 template from `references/details.md` for these tests

### Assertions
- Use **NUnit assertions only** — `Assert.That` and `Assert.Multiple`. Never FluentAssertions.
- **One expected condition per assertion — never an `OR`.** `Assert.That(response.StatusCode, Is.EqualTo(HttpStatusCode.OK))`, never `Is.EqualTo(HttpStatusCode.OK).Or.EqualTo(HttpStatusCode.NoContent)`; `Is.EqualTo(HttpStatusCode.BadRequest)`, never `.Or.EqualTo(HttpStatusCode.Conflict)`. The rule covers every assertion, not just status: field values, collection counts, error codes, and elapsed-time budgets are asserted against the single value the test expects. No `Is.AnyOf(...)`, no `Or`/`||` inside a constraint, no `Assert.That(x == a || x == b)`. If two outcomes are both possible, the scenario is under-specified — split it into one test per expected outcome, parameterize it via `[TestCase]`, or establish which value is correct. The only exception is an explicit instruction to accept more than one value; when that happens, state the instruction in a comment on the assertion.
- **Positive tests use typed client overloads.** When the client has a `({args}, HttpStatusCode expected)` overload, call that overload — it asserts the status code internally and returns the deserialized DTO directly. Do not assert `response.StatusCode` in the test, and do not call `Deserialize` in the test body for positive scenarios.
- **Apply the rich happy-path template by default for 200 responses.** Assert every request field on the response, every server-generated field (Status, CreatedOn, UpdatedOn, FailureCount, etc.), then `GetById` and assert the persistence round-trip. The minimal "just check one field" pattern is acceptable only for trivial reads where there is nothing else to verify.
- **For 4xx errors (400 / 404 / 422), apply the strict ProblemDetails template.** Use the raw `RestResponse` overload, call `AttachBody(response)` first, then assert: status code → deserialize → tracking fields (`TraceId`, `RequestId`, `Instance`) → standard fields (`Type`, `Title`, `Status`) → `Errors` dict (400) or `ErrorCode` + extension fields (404/422). Never settle for a single status-code assertion on a 4xx that has a body.
- **For 401 unauthorized**, a single status-code assertion is sufficient — auth middleware does not emit a `ProblemDetails` body.
- Wrap two or more related assertions in `Assert.Multiple(() => { ... })` so all failures are reported at once.
- Use `Deserialize<ProblemDetailsDto>(response)` (from `BaseApiTest`) for the strict template — `TryProblem` is a lenient helper used only when the body might not be parseable (e.g. tolerating a documented backend defect that returns 500).
- Always call `AttachBody(response)` before assertions on error tests so the actual body lands in the Allure report when assertions fail.

### Errors & failure messages
- **Never swallow an error, and never write a `try`/`catch` in a test.** A `[Test]` body contains no catch blocks at all — not around the act, not around the assert, not for cleanup. An unexpected exception must reach NUnit untouched. An **expected** exception is asserted, not caught: `Assert.ThrowsAsync<T>(...)` is an assertion, not error handling.
- **`[TearDown]` gets no `try`/`catch` either.** If the cleanup delete throws, NUnit reports a teardown error and you go fix the leak — that is the system working. A swallowed cleanup failure means the suite quietly leaks data until the environment rots.
- **`try`/`catch` belongs in one place only: a helper that performs I/O**, where converting a specific failure into a useful message *is* the helper's contract (`Deserialize<T>`, a polling probe). It catches one named exception type, never `Exception` blanket, and rethrows or reports — it never returns a silent default.
- **Every failure message names the subject and carries the evidence.** `Assert.That(dto.Status, Is.EqualTo("Active"), $"Account {dto.Id} status after activation")` — a bare failure printing `Expected: "Active" But was: "Pending"` with no id sends the reader hunting through logs for which record it was.
- **A deserialization failure explains itself — inside the helper, not the test.** Always `AttachBody(response)` **before** deserializing, so the payload is in the Allure report when the parse throws. `Deserialize<T>(response)` on `BaseApiTest` is the one place that catches `JsonException`: it rethrows with the **property path** the exception carries, the target type, and the raw body — so the report reads "`GET /orders` → `$.total` expected Int32, got string" instead of a bare "The JSON value could not be converted". A parse failure is a **failed** test with a contract-drift message, never a skip and never an inconclusive.

### Test data setup & cleanup
- **Trading accounts:** Never create new accounts in tests. Fetch an existing Trading account from the logged-in user: `new AccountClient(AuthToken).GetAll(HttpStatusCode.OK).First(a => a.AccountType == "Trading")`. No `[TearDown]` needed for fetched accounts.
- `[SetUp]` (or `[OneTimeSetUp]`) may create test data via API calls and store results in instance fields (e.g. `private {Resource}Dto testResource`).
- If `[SetUp]` creates data, always add a `[TearDown]` that deletes it — plainly, with no `try`/`catch`. A cleanup that throws is a real problem and NUnit reports it as one.
- **Cleanup of resources created inside the test body is registered, not inlined.** The test does not wrap itself in `try/finally`. Record the id as it is created (`_createdIds.Add(dto.Id)` on the fixture) and let `[TearDown]` delete the tracked ids. The test body stays linear — arrange, act, assert — with no control-flow scaffolding around it, and cleanup happens whether the test passed, failed, or threw.
- Do NOT wrap the test body in try/finally as a substitute for proper `[SetUp]`/`[TearDown]` when a precondition is shared by only some tests — set the precondition up inline as a normal first step in those tests; reserve try/finally for actual cleanup of resources the test method itself created.
- Client instances in `[SetUp]`/`[TearDown]` are disposable (create inline, don't store).
- **Payment methods follow the tokenize → create two-step flow.** Call `PaymentMethodClient.Tokenize(accountId, PaysafeTestCards.Build(PaysafeTestCard.VisaUs1, currency), HttpStatusCode.OK)` to get a `TokenizedMethodDto`, then pass its `Token` and `Last4` into `MethodInDto` together with `Type = "Card"`, `ExpiryMonth`/`ExpiryYear` (from `PaysafeTestCards.DefaultExpiryMonth/Year`), and the currency. Never hardcode card numbers — always use the `PaysafeTestCards` enum + `Build` helper in `ApiTests/TestData/PaysafeTestCards.cs`. Clean up with `methodClient.Delete(account.Id, method.Id)` wrapped in try/catch. Use `[OneTimeSetUp]` when the method is read-only across tests; `[SetUp]` when tests mutate or delete it.

### Deserialization
- For positive tests, deserialization is handled inside the client's typed overload — do not repeat it in the test
- For negative tests or structural tests that need raw response access, use the inherited `Deserialize<T>(response)` helper from `BaseApiTest` — never call `JsonSerializer.Deserialize` directly in test code
- If the response is a plain array, deserialize as `Deserialize<List<T>>(response)`
- If the API returns a wrapper envelope (e.g. `{ "data": [...] }`), create a wrapper DTO (e.g. `{Resource}ListDto`) with a `Data` property — use the `qa/dotnet/skills/api-models` skill to generate it

### What NOT to do
- No `var` — use explicit types for all local variables
- No generic `client` variable name — use the concrete type name in camelCase (e.g. `watchlistClient`, not `client`)
- No `Thread.Sleep()` or manual delays
- No `OR` in any assertion — no `.Or.`, no `Is.AnyOf(...)`, no `||` inside an `Assert.That` condition. One expected value per assertion (see Assertions)
- No `try`/`catch` in a test method or in `[TearDown]` — none, for any reason including cleanup. Expected exceptions use `Assert.ThrowsAsync<T>`; catches live only in I/O helpers (see Errors & failure messages)
- No `try`/`finally` wrapping a test body for cleanup — track created ids and delete them in `[TearDown]`
- No bare deserialization failures — attach the body first and fail with the property path and payload, not a raw `JsonException` trace
- No inter-test dependencies — tests must not rely on state created, modified, or deleted by another test; each test is self-contained
- No `[SetUp]` for preconditions shared by only some tests — if not all tests in the fixture need it, set it up inline as a normal first step in those tests. (Per-test cleanup of resources the test method itself created IS allowed — and expected — to use try/finally; see Test data setup & cleanup.)
- No "minimal" 4xx tests that only assert `response.StatusCode` when the response carries a `ProblemDetails` body — apply the strict template instead so failures pinpoint the missing field. The single-status-code shortcut applies only to 401 unauthorized.
- No shared mutable client instances between tests
- No hardcoded base URLs or credentials — always use `ConfigurationLoader`
- No FluentAssertions (`.Should()`, `AssertionScope`) — use `Assert.That` and `Assert.Multiple` only
- No `Newtonsoft.Json` — use `System.Text.Json` only
- No direct `JsonSerializer.Deserialize` in test code — use the typed client overload for positive tests, or `Deserialize<T>(response)` from `BaseApiTest` when raw access is needed
- No deserialization in raw `RestResponse` client methods — only typed overloads (those accepting `HttpStatusCode expected`) may deserialize and return the DTO

## Generation steps

0. Establish the **source of truth** (see *Source of truth & input modes*). From an **OpenAPI/Swagger spec**, derive resources, endpoints, body shapes, and the scenario set per endpoint — skip the interactive questions the spec already answers. From a **test-case document**, map one test method per TC-ID and tag it for traceability. Only fall back to steps 1–3 for verbal scenarios.
1. Ask: **new fixture** or **adding methods to an existing fixture**?
2. Ask: which client/resource to use.
3. Ask: which scenario(s) to cover (happy path, unauthorized, not found, validation error, etc.).
4. Read the canonical example `ApiTests/Tests/RecurringDepositTests.cs` to confirm the expected style for both templates before generating.
5. If the DTO doesn't exist yet, use the `qa/dotnet/skills/api-models` skill to generate it. If the test asserts a `ProblemDetails` extension field that's missing from `ProblemDetailsDto` (e.g. a new `{entity}Id`), add it via `qa/dotnet/skills/api-models` rather than reading from `Errors`.
6. Generate the file or add the method(s) to the target fixture:
   - **200 happy path** → apply the rich happy-path template (request fields + server-generated fields + `GetById` round-trip in `Assert.Multiple`). For Pause/Resume/Cancel-style action endpoints, assert state change + `UpdatedOn` + invariants.
   - **400 validation** → apply the strict ProblemDetails template; expect `Type="ValidationViolation"`, `Title="Validation violation"`, and `Errors["FieldName"]` containing the FluentValidation message fragment.
   - **404 not found** → apply the strict ProblemDetails template; expect `Type="BusinessViolation"`, `Title="Business rule violation"`, `ErrorCode="{ENTITY}_NOT_FOUND"`, plus the relevant `{entity}Id`/`accountId` extension fields.
   - **422 invalid state / business rule** → apply the strict ProblemDetails template; expect `Type="BusinessViolation"`, `Title="Business rule violation"`, `ErrorCode="INVALID_TRANSACTION_STATE"` (or other domain code), plus `transactionId`/`currentStatus`/`expectedStatus` extensions where applicable.
   - **401 unauthorized** → single status-code assertion; no body validation.
   - For positive tests, use the typed client overload (`{resource}Client.{Method}(HttpStatusCode.OK)`); if the client does not yet have one, add it following the `qa/dotnet/skills/api-client-writer` skill.
   - For 4xx tests, use the raw `RestResponse` overload, call `AttachBody(response)`, then `Deserialize<ProblemDetailsDto>(response)` from `BaseApiTest`.
   - Use explicit types (no `var`) for all local variables in test methods.
   - Track any resource the test creates (`_createdIds.Add(dto.Id)`) and delete it in `[TearDown]` — no `try`/`finally` in the test, no `try`/`catch` in the teardown.
7. Run `dotnet build ApiTests/ApiTests.csproj` — expect 0 errors. Inside a plan task marked `Gate: none`, run none of this and report the files as "written, not run".
