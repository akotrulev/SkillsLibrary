# Deep-dive details — `qa-api-test-author-generator-dotnet`

Sections moved out of SKILL.md for on-demand loading. Read what the task needs.

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

`ProblemDetailsDto` (in `ApiTests/Models/CommonModels/`) already exposes all common extension fields: `MethodId`, `AccountId`, `RecurringDepositId`, `TransactionId`, `CurrentStatus`, `ExpectedStatus`. If your domain needs a new extension, add it to that DTO via the `qa/dotnet/skills/api-dto-writer` skill.

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
