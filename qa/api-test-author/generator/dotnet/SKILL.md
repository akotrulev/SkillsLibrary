---
name: qa-api-test-author-generator-dotnet
description: Use when the user asks to scaffold .NET API tests (NUnit + RestSharp) — new fixtures, new test methods on an existing `*Tests.cs` file, or a specific scenario (happy path, 4xx with ProblemDetails, 401). Triggers: "write an API test for X", "add a 404 test to YTests", "scaffold an ApiTests fixture for Z". Do NOT use for UI tests (use `qa/ui-test-author`), for client/DTO scaffolding (use `qa/api-client-writer` / `qa/api-dto-writer`), or for explaining what API tests are.
---

# QA — API Test Writer (.NET)

Scaffolds NUnit-based API tests against a REST backend that emits a uniform `ProblemDetails` envelope on every 4xx. Output mirrors a single canonical fixture, applies a rich happy-path template for 2xx and a strict `ProblemDetails` template for 4xx.

## When to use

- New `{Resource}Tests.cs` fixture in `ApiTests/Tests/`
- Adding test methods (happy path, 4xx, 401) to an existing fixture
- Generating parameterized validation tests against a single endpoint

## When NOT to use

- UI / browser tests → `qa/ui-test-author`
- Generating the typed client itself → `qa/api-client-writer`
- Generating request/response DTOs → `qa/api-dto-writer`
- Performance / load tests → `qa/performance`

## Canonical example

The reference fixture is `ApiTests/Tests/RecurringDepositTests.cs`. Mirror its structure: rich happy-path assertions for 200 responses, strict `ProblemDetails` validation for 4xx responses. Skim it before generating new tests against a similar resource.

## Templates

### New fixture — `ApiTests/Tests/{Resource}Tests.cs`

```csharp
using System.Net;
using ApiTests.Clients;
using ApiTests.Helpers;
using ApiTests.Models.{Api}.{Resource}Models;
using Allure.Net.Commons;
using Allure.NUnit.Attributes;
using NUnit.Framework;

namespace ApiTests.Tests;

[TestFixture]
public class {Resource}Tests : BaseApiTest
{
    // Apply rich happy-path template (below) for 200 tests, and
    // strict ProblemDetails template for 400/404/422 tests.
}
```

### Happy-path template (preferred for 200 responses)

For Create/Update endpoints returning a full DTO: assert every request field on the response, every server-generated field, then `GetById` and verify persistence round-trip. Wrap all assertions in `Assert.Multiple` so every failure is reported in one run.

```csharp
[Test]
[AllureFeature("{Feature}")]
[AllureStory("Create {resource}")]
[AllureSeverity(SeverityLevel.normal)]
public void Create{Resource}_WithValidData_ReturnsOk()
{
    {Resource}Client {resource}Client = new {Resource}Client(AuthToken);

    DateTime startDate = DateTime.UtcNow.AddDays(1).Date;

    {Resource}InDto dto = new {Resource}InDto
    {
        // populate every required field
    };

    {Resource}Dto created = {resource}Client.Create(_account.Id, dto, HttpStatusCode.OK);

    try
    {
        {Resource}Dto fetched = {resource}Client.GetById(_account.Id, created.Id, HttpStatusCode.OK);

        Assert.Multiple(() =>
        {
            // --- CREATE response: fields from the request ---
            Assert.That(created.Id, Is.Not.Null.And.Not.Empty, "created.Id must not be null or empty.");
            Assert.That(created.AccountId, Is.EqualTo(_account.Id));
            Assert.That(created.{ForeignKeyId}, Is.EqualTo(dto.{ForeignKeyId}.ToString()));
            Assert.That(created.{Field}, Is.EqualTo(dto.{Field}));
            // ... one assertion per request field ...

            // --- CREATE response: server-generated fields ---
            Assert.That(created.Status, Is.EqualTo("{InitialStatus}"));
            Assert.That(created.CreatedOn, Is.GreaterThan(DateTimeOffset.UtcNow.AddMinutes(-1)));
            Assert.That(created.UpdatedOn, Is.Null, "UpdatedOn must be null on a fresh resource.");
            // ... assert every nullable timestamp / counter is in its initial state ...

            // --- PERSISTENCE round-trip: fetched matches created ---
            Assert.That(fetched.Id, Is.EqualTo(created.Id));
            Assert.That(fetched.AccountId, Is.EqualTo(created.AccountId));
            Assert.That(fetched.{Field}, Is.EqualTo(created.{Field}));
            // ... one assertion per field, comparing fetched vs created ...
        });
    }
    finally
    {
        try { {resource}Client.{CleanupVerb}(_account.Id, created.Id); } catch { }
    }
}
```

For action endpoints with no body (Pause/Resume/Cancel/etc.): assert `RestResponse.StatusCode == OK` on the action call, then `GetById` and assert the full updated DTO state — including invariants that did not change (Amount, Currency, etc.) and the field that did (Status, UpdatedOn).

```csharp
[Test]
[AllureFeature("{Feature}")]
[AllureStory("{Action} {resource}")]
[AllureSeverity(SeverityLevel.normal)]
public void {Action}{Resource}_When{Precondition}_ReturnsOkAndStatusIs{NewStatus}()
{
    {Resource}Client {resource}Client = new {Resource}Client(AuthToken);
    {Resource}Dto created = {resource}Client.Create(_account.Id, new {Resource}InDto { /*...*/ }, HttpStatusCode.OK);

    try
    {
        RestResponse actionResponse = {resource}Client.{Action}(_account.Id, created.Id);
        {Resource}Dto fetched = {resource}Client.GetById(_account.Id, created.Id, HttpStatusCode.OK);

        Assert.Multiple(() =>
        {
            Assert.That(actionResponse.StatusCode, Is.EqualTo(HttpStatusCode.OK),
                "{Action} must return 200 OK.");

            // --- State change ---
            Assert.That(fetched.Status, Is.EqualTo("{NewStatus}"));
            Assert.That(fetched.UpdatedOn, Is.Not.Null);
            Assert.That(fetched.UpdatedOn!.Value, Is.GreaterThan(DateTimeOffset.UtcNow.AddMinutes(-1)));

            // --- Invariants: every other field must match the original create ---
            Assert.That(fetched.Id, Is.EqualTo(created.Id));
            Assert.That(fetched.{Field}, Is.EqualTo(created.{Field}));
            // ...
        });
    }
    finally
    {
        try { {resource}Client.{CleanupVerb}(_account.Id, created.Id); } catch { }
    }
}
```

### Strict ProblemDetails template (preferred for 400 / 404 / 422)

The backend's `RegisterProblemDetails` middleware emits a uniform error envelope on every 4xx. Always assert all five sections so failures pinpoint the exact missing or wrong field.

```csharp
[Test]
[AllureFeature("{Feature}")]
[AllureStory("{Action} {resource} validation")]
[AllureSeverity(SeverityLevel.normal)]
public void {Action}{Resource}_With{InvalidCondition}_Returns{Code}()
{
    RestResponse response = new {Resource}Client(AuthToken).{Action}({args});

    AttachBody(response);

    // --- 1. Status assertion (strict) ---
    Assert.That(response.StatusCode, Is.EqualTo(HttpStatusCode.{Code}),
        "{Reason from spec}.");

    // --- 2. Deserialize → ProblemDetailsDto ---
    ProblemDetailsDto problem = Deserialize<ProblemDetailsDto>(response);
    Assert.That(problem, Is.Not.Null,
        "Response body must be a ProblemDetails object on {numericCode}.");

    // --- 3. Tracking fields (every 4xx response gets these) ---
    Assert.That(problem.TraceId,   Is.Not.Null.And.Not.Empty, "ProblemDetails.TraceId must not be null or empty.");
    Assert.That(problem.RequestId, Is.Not.Null.And.Not.Empty, "ProblemDetails.RequestId must not be null or empty.");
    Assert.That(problem.Instance,  Is.Not.Null.And.Not.Empty, "ProblemDetails.Instance must not be null or empty.");

    // --- 4. Standard ProblemDetails fields ---
    Assert.That(problem.Type,   Is.EqualTo("{ValidationViolation | BusinessViolation}"));
    Assert.That(problem.Title,  Is.EqualTo("{Validation violation | Business rule violation}"));
    Assert.That(problem.Status, Is.EqualTo({400 | 404 | 422}));

    // --- 5a. For 400: per-field Errors dictionary ---
    Assert.That(problem.Errors, Is.Not.Null);
    Assert.That(problem.Errors, Contains.Key("{FieldName}"));
    Assert.That(problem.Errors["{FieldName}"], Has.Some.Contains("{expected message fragment}"));

    // --- 5b. For 404/422: ErrorCode + extension fields ---
    Assert.That(problem.ErrorCode, Is.EqualTo("{BUSINESS_ERROR_CODE}"));
    // + the specific extension fields for the error code (see ground-truth table)
}
```

### ProblemDetails ground truth (reference)

When you generate a 4xx test, look up the expected `Type`/`Title`/`ErrorCode` and extension fields here. These are emitted by `Shared/FlexInvest.Core/Service/Registrations/ProblemDetails.cs` plus per-domain exceptions.

| Status | Trigger | `Type` | `Title` | `ErrorCode` | Extension fields |
|---|---|---|---|---|---|
| 400 | FluentValidation fail | `ValidationViolation` | `Validation violation` | _(none)_ | `errors` dict keyed by field |
| 400 | ASP.NET model-binder fail (e.g. empty Guid) | _(none — default ASP.NET ValidationProblemDetails)_ | _(none)_ | _(none)_ | `errors` dict keyed by `$.{field}` or `dto` — match key case-insensitively |
| 404 | Domain entity not found | `BusinessViolation` | `Business rule violation` | `{ENTITY}_NOT_FOUND` | `{entity}Id`, `accountId` |
| 422 | Invalid state transition | `BusinessViolation` | `Business rule violation` | `INVALID_TRANSACTION_STATE` | `transactionId`, `currentStatus`, `expectedStatus` |
| 422 | Other domain rule violation | `BusinessViolation` | `Business rule violation` | `{DOMAIN_ERROR_CODE}` | rule-specific extensions |

`ProblemDetailsDto` (in `ApiTests/Models/CommonModels/`) already exposes all common extension fields: `MethodId`, `AccountId`, `RecurringDepositId`, `TransactionId`, `CurrentStatus`, `ExpectedStatus`. If your domain needs a new extension, add it to that DTO via the `qa/api-dto-writer` skill.

### Unauthorized test (401)

`401` responses come from auth middleware and have no `ProblemDetails` body. A single status-code check is sufficient — do not apply the strict template.

```csharp
[Test]
[AllureFeature("{Feature}")]
[AllureStory("{Story}")]
[AllureSeverity(SeverityLevel.normal)]
public void {Action}{Resource}_WhenNotAuthenticated_ReturnsUnauthorized()
{
    RestResponse response = new {Resource}Client(string.Empty).{Method}({args});

    Assert.That(response.StatusCode, Is.EqualTo(HttpStatusCode.Unauthorized));
}
```

### Parameterized test (`[TestCase]`)

```csharp
[TestCase(0, HttpStatusCode.BadRequest)]
[TestCase(-1, HttpStatusCode.BadRequest)]
[TestCase(999999, HttpStatusCode.NotFound)]
[AllureFeature("{Feature}")]
[AllureStory("{Story}")]
[AllureSeverity(SeverityLevel.normal)]
public void {Action}_{Condition}_{ExpectedOutcome}(int id, HttpStatusCode expectedStatus)
{
    {Resource}Client {resource}Client = new {Resource}Client(AuthToken);

    RestResponse response = {resource}Client.GetById(id);

    Assert.That(response.StatusCode, Is.EqualTo(expectedStatus));
}
```

### Test data setup with `[SetUp]` / `[TearDown]`

When tests need a precondition (e.g. a resource must exist before testing delete/update), use `[SetUp]` to create it and `[TearDown]` to clean up:

```csharp
[TestFixture]
public class {Resource}Tests : BaseApiTest
{
    private {Resource}Dto testResource = null!;

    [SetUp]
    public void CreateTestData()
    {
        testResource = new {Resource}Client(AuthToken)
            .Create(new {Resource}InDto { /* required fields */ }, HttpStatusCode.OK);
    }

    [TearDown]
    public void CleanupTestData()
    {
        try
        {
            new {Resource}Client(AuthToken).Remove(testResource.Id);
        }
        catch
        {
            // Swallow cleanup errors to avoid masking test failures
        }
    }

    [Test]
    [AllureFeature("{Feature}")]
    [AllureStory("{Story}")]
    [AllureSeverity(SeverityLevel.normal)]
    public void Delete{Resource}_WhenAuthenticated_ReturnsNoContent()
    {
        {Resource}Client {resource}Client = new {Resource}Client(AuthToken);

        RestResponse response = {resource}Client.Remove(testResource.Id);

        Assert.That(response.StatusCode, Is.EqualTo(HttpStatusCode.NoContent));
    }
}
```

### Account setup — fetch existing Trading account

When tests need a trading account, **do not create a new account**. Fetch an existing Trading account from the logged-in user instead. This avoids creating disposable accounts that pollute the environment and may fail if account creation requires additional setup (wallets, KYC, etc.).

```csharp
[TestFixture]
public class {Resource}Tests : BaseApiTest
{
    private AccountDto _account = null!;

    [SetUp]
    public void SetUpAccount()
    {
        _account = new AccountClient(AuthToken)
            .GetAll(HttpStatusCode.OK)
            .First(a => a.AccountType == "Trading");
    }

    // No TearDown needed — the account is not created by the test
}
```

Use `[OneTimeSetUp]` instead of `[SetUp]` when every test in the fixture uses the same account and none of them modify the account itself:

```csharp
[OneTimeSetUp]
public void SetUpAccount()
{
    _account = new AccountClient(AuthToken)
        .GetAll(HttpStatusCode.OK)
        .First(a => a.AccountType == "Trading");
}
```

### Payment method setup (tokenize → create)

Creating a usable payment method for a test is a **two-step flow**: call `Tokenize` with the card details, then `Create` passing the returned token plus echoed card metadata into `MethodInDto`. Card numbers come from the `PaysafeTestCards` enum + `Build` helper in `ApiTests/TestData/PaysafeTestCards.cs` — never hardcode a card number.

#### Shared payment method — `[OneTimeSetUp]`

Use when multiple tests in the fixture only *read* from the same payment method (deposits, simulations, listing). Avoids repeating the tokenize + create round-trip per test.

```csharp
[TestFixture]
public class {Resource}Tests : BaseApiTest
{
    private const string Currency = "EUR";

    private PaymentMethodClient methodClient = null!;
    private AccountDto account = null!;
    private MethodDto method = null!;

    [OneTimeSetUp]
    public void CreateSharedPaymentMethod()
    {
        methodClient = new PaymentMethodClient(AuthToken);
        account = new AccountClient(AuthToken)
            .GetAll(HttpStatusCode.OK)
            .First(a => a.BaseCurrency == Currency && a.AccountType == "Trading");

        TokenizedMethodDto tokenized = methodClient.Tokenize(
            account.Id,
            PaysafeTestCards.Build(PaysafeTestCard.VisaUs1, Currency),
            HttpStatusCode.OK);

        method = methodClient.Create(account.Id, new MethodInDto
        {
            Token = tokenized.Token,
            Last4 = tokenized.Last4,
            Type = "Card",
            ExpiryMonth = PaysafeTestCards.DefaultExpiryMonth,
            ExpiryYear = PaysafeTestCards.DefaultExpiryYear,
            Currency = Currency
        }, HttpStatusCode.OK);
    }

    [OneTimeTearDown]
    public void CleanupSharedPaymentMethod()
    {
        try { methodClient.Delete(account.Id, method.Id); } catch { }
    }
}
```

#### Per-test payment method — `[SetUp]`

Use when the test body mutates or deletes the method (DELETE, set-default, update). Guarantees isolation so one test's mutations don't leak into another.

```csharp
[TestFixture]
public class PaymentMethodMutationTests : BaseApiTest
{
    private const string Currency = "EUR";

    private PaymentMethodClient methodClient = null!;
    private AccountDto account = null!;
    private MethodDto method = null!;

    [SetUp]
    public void CreateFreshPaymentMethod()
    {
        methodClient = new PaymentMethodClient(AuthToken);
        account = new AccountClient(AuthToken)
            .GetAll(HttpStatusCode.OK)
            .First(a => a.BaseCurrency == Currency && a.AccountType == "Trading");

        TokenizedMethodDto tokenized = methodClient.Tokenize(
            account.Id,
            PaysafeTestCards.Build(PaysafeTestCard.VisaUs1, Currency),
            HttpStatusCode.OK);

        method = methodClient.Create(account.Id, new MethodInDto
        {
            Token = tokenized.Token,
            Last4 = tokenized.Last4,
            Type = "Card",
            ExpiryMonth = PaysafeTestCards.DefaultExpiryMonth,
            ExpiryYear = PaysafeTestCards.DefaultExpiryYear,
            Currency = Currency
        }, HttpStatusCode.OK);
    }

    [TearDown]
    public void DeletePaymentMethod()
    {
        try { methodClient.Delete(account.Id, method.Id); } catch { }
    }
}
```

### Collection response test

When the resource was created earlier in the test, assert the collection contains it AND that the matched item equals the original on every field — not just the id.

```csharp
[Test]
[AllureFeature("{Feature}")]
[AllureStory("List {resource}s")]
[AllureSeverity(SeverityLevel.normal)]
public void GetAll{Resource}s_When{Precondition}_ReturnsOk()
{
    {Resource}Client {resource}Client = new {Resource}Client(AuthToken);
    {Resource}Dto created = {resource}Client.Create(_account.Id, new {Resource}InDto { /*...*/ }, HttpStatusCode.OK);

    try
    {
        RestResponse response = {resource}Client.GetAll(_account.Id);
        List<{Resource}Dto> items = Deserialize<List<{Resource}Dto>>(response);
        {Resource}Dto? match = items.FirstOrDefault(x => x.Id == created.Id);

        Assert.Multiple(() =>
        {
            Assert.That(response.StatusCode, Is.EqualTo(HttpStatusCode.OK));
            Assert.That(items, Is.Not.Null);
            Assert.That(match, Is.Not.Null, "GetAll response must contain the resource just created.");

            // --- Matched item must equal the originally-created resource on every field ---
            Assert.That(match!.Id, Is.EqualTo(created.Id));
            Assert.That(match.{Field}, Is.EqualTo(created.{Field}));
            // ...
        });
    }
    finally
    {
        try { {resource}Client.{CleanupVerb}(_account.Id, created.Id); } catch { }
    }
}
```

### Paginated response test

When the API returns a wrapper envelope (e.g. `{ "data": [...], "page": 1, "total": 50 }`), use a wrapper DTO:

```csharp
[Test]
[AllureFeature("{Feature}")]
[AllureStory("List {resource}s")]
[AllureSeverity(SeverityLevel.normal)]
public void Get{Resource}s_FirstPage_ReturnsPaginatedResults()
{
    {Resource}Client {resource}Client = new {Resource}Client(AuthToken);

    {Resource}ListDto body = {resource}Client.GetAll(page: 1, resultsPerPage: 10, HttpStatusCode.OK);

    Assert.Multiple(() =>
    {
        Assert.That(body.Page, Is.EqualTo(1));
        Assert.That(body.Total, Is.GreaterThan(0));
        Assert.That(body.Data, Is.Not.Empty);
        Assert.That(body.Data.Count, Is.LessThanOrEqualTo(10));
    });
}
```

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
- Instantiate the client **inside** each test method. Exception: `[SetUp]` may create test data (see template above)
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
- Use the 401 template above for these tests

### Assertions
- Use **NUnit assertions only** — `Assert.That` and `Assert.Multiple`. Never FluentAssertions.
- **Positive tests use typed client overloads.** When the client has a `({args}, HttpStatusCode expected)` overload, call that overload — it asserts the status code internally and returns the deserialized DTO directly. Do not assert `response.StatusCode` in the test, and do not call `Deserialize` in the test body for positive scenarios.
- **Apply the rich happy-path template by default for 200 responses.** Assert every request field on the response, every server-generated field (Status, CreatedOn, UpdatedOn, FailureCount, etc.), then `GetById` and assert the persistence round-trip. The minimal "just check one field" pattern is acceptable only for trivial reads where there is nothing else to verify.
- **For 4xx errors (400 / 404 / 422), apply the strict ProblemDetails template.** Use the raw `RestResponse` overload, call `AttachBody(response)` first, then assert: status code → deserialize → tracking fields (`TraceId`, `RequestId`, `Instance`) → standard fields (`Type`, `Title`, `Status`) → `Errors` dict (400) or `ErrorCode` + extension fields (404/422). Never settle for a single status-code assertion on a 4xx that has a body.
- **For 401 unauthorized**, a single status-code assertion is sufficient — auth middleware does not emit a `ProblemDetails` body.
- Wrap two or more related assertions in `Assert.Multiple(() => { ... })` so all failures are reported at once.
- Use `Deserialize<ProblemDetailsDto>(response)` (from `BaseApiTest`) for the strict template — `TryProblem` is a lenient helper used only when the body might not be parseable (e.g. tolerating a documented backend defect that returns 500).
- Always call `AttachBody(response)` before assertions on error tests so the actual body lands in the Allure report when assertions fail.

### Test data setup & cleanup
- **Trading accounts:** Never create new accounts in tests. Fetch an existing Trading account from the logged-in user: `new AccountClient(AuthToken).GetAll(HttpStatusCode.OK).First(a => a.AccountType == "Trading")`. No `[TearDown]` needed for fetched accounts.
- `[SetUp]` (or `[OneTimeSetUp]`) may create test data via API calls and store results in instance fields (e.g. `private {Resource}Dto testResource`).
- If `[SetUp]` creates data, always add a `[TearDown]` that deletes it. Wrap the cleanup in try/catch so cleanup failures do not mask test failures.
- **Per-test cleanup of resources created inside the test body uses try/finally.** When a test method creates a resource as part of its arrange phase (e.g. `Create(...)` returning a `{Resource}Dto`), wrap the act + assert phases in `try { ... } finally { try { client.{CleanupVerb}(...); } catch { } }`. The inner try/catch in `finally` ensures cleanup errors never mask the actual test failure. This is the dominant pattern in `RecurringDepositTests.cs`.
- Do NOT wrap the test body in try/finally as a substitute for proper `[SetUp]`/`[TearDown]` when a precondition is shared by only some tests — set the precondition up inline as a normal first step in those tests; reserve try/finally for actual cleanup of resources the test method itself created.
- Client instances in `[SetUp]`/`[TearDown]` are disposable (create inline, don't store).
- **Payment methods follow the tokenize → create two-step flow.** Call `PaymentMethodClient.Tokenize(accountId, PaysafeTestCards.Build(PaysafeTestCard.VisaUs1, currency), HttpStatusCode.OK)` to get a `TokenizedMethodDto`, then pass its `Token` and `Last4` into `MethodInDto` together with `Type = "Card"`, `ExpiryMonth`/`ExpiryYear` (from `PaysafeTestCards.DefaultExpiryMonth/Year`), and the currency. Never hardcode card numbers — always use the `PaysafeTestCards` enum + `Build` helper in `ApiTests/TestData/PaysafeTestCards.cs`. Clean up with `methodClient.Delete(account.Id, method.Id)` wrapped in try/catch. Use `[OneTimeSetUp]` when the method is read-only across tests; `[SetUp]` when tests mutate or delete it.

### Deserialization
- For positive tests, deserialization is handled inside the client's typed overload — do not repeat it in the test
- For negative tests or structural tests that need raw response access, use the inherited `Deserialize<T>(response)` helper from `BaseApiTest` — never call `JsonSerializer.Deserialize` directly in test code
- If the response is a plain array, deserialize as `Deserialize<List<T>>(response)`
- If the API returns a wrapper envelope (e.g. `{ "data": [...] }`), create a wrapper DTO (e.g. `{Resource}ListDto`) with a `Data` property — use the `qa/api-dto-writer` skill to generate it

### What NOT to do
- No `var` — use explicit types for all local variables
- No generic `client` variable name — use the concrete type name in camelCase (e.g. `watchlistClient`, not `client`)
- No `Thread.Sleep()` or manual delays
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

1. Ask: **new fixture** or **adding methods to an existing fixture**?
2. Ask: which client/resource to use.
3. Ask: which scenario(s) to cover (happy path, unauthorized, not found, validation error, etc.).
4. Read the canonical example `ApiTests/Tests/RecurringDepositTests.cs` to confirm the expected style for both templates before generating.
5. If the DTO doesn't exist yet, use the `qa/api-dto-writer` skill to generate it. If the test asserts a `ProblemDetails` extension field that's missing from `ProblemDetailsDto` (e.g. a new `{entity}Id`), add it via `qa/api-dto-writer` rather than reading from `Errors`.
6. Generate the file or add the method(s) to the target fixture:
   - **200 happy path** → apply the rich happy-path template (request fields + server-generated fields + `GetById` round-trip in `Assert.Multiple`). For Pause/Resume/Cancel-style action endpoints, assert state change + `UpdatedOn` + invariants.
   - **400 validation** → apply the strict ProblemDetails template; expect `Type="ValidationViolation"`, `Title="Validation violation"`, and `Errors["FieldName"]` containing the FluentValidation message fragment.
   - **404 not found** → apply the strict ProblemDetails template; expect `Type="BusinessViolation"`, `Title="Business rule violation"`, `ErrorCode="{ENTITY}_NOT_FOUND"`, plus the relevant `{entity}Id`/`accountId` extension fields.
   - **422 invalid state / business rule** → apply the strict ProblemDetails template; expect `Type="BusinessViolation"`, `Title="Business rule violation"`, `ErrorCode="INVALID_TRANSACTION_STATE"` (or other domain code), plus `transactionId`/`currentStatus`/`expectedStatus` extensions where applicable.
   - **401 unauthorized** → single status-code assertion; no body validation.
   - For positive tests, use the typed client overload (`{resource}Client.{Method}(HttpStatusCode.OK)`); if the client does not yet have one, add it following the `qa/api-client-writer` skill.
   - For 4xx tests, use the raw `RestResponse` overload, call `AttachBody(response)`, then `Deserialize<ProblemDetailsDto>(response)` from `BaseApiTest`.
   - Use explicit types (no `var`) for all local variables in test methods.
   - Wrap any resource the test creates in `try { ... } finally { try { client.{CleanupVerb}(...); } catch { } }`.
7. Run `dotnet build ApiTests/ApiTests.csproj` — expect 0 errors.

## Changelog

- 2026-05-27: Authored from production .NET ApiTests skill; collapsed `*PClient`/`*MClient` → single `*Client`, `UserAuthToken`/`AdminAuthToken` → single `AuthToken`.
