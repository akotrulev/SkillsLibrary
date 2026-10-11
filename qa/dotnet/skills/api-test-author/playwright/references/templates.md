# Fixture templates — `qa-api-test-playwright-dotnet`

The fixture shape SKILL.md's rules describe, on the `BasePlaywrightApiTest` from SKILL.md § Base class
template. DTOs come from `qa/dotnet/skills/api-models`, the `{Resource}Client` from
`qa/dotnet/skills/api-client-writer` (its `(IAPIRequestContext)` constructor variant), the token from
`qa/dotnet/skills/test-login-tokens`.

## A resource fixture

```csharp
using System.Net;
using Allure.NUnit.Attributes;
using Allure.Net.Commons;
using ApiTests.Base;
using ApiTests.Clients;
using ApiTests.Models;
using Microsoft.Playwright;
using NUnit.Framework;
using Tests.Support.Auth;

namespace ApiTests.Tests;

[AllureFeature("Users")]
public class UserTests : BasePlaywrightApiTest
{
    private UserClient userClient = null!;
    private UserClient anonymousClient = null!;

    [SetUp]
    public async Task CreateClientsAsync()
    {
        userClient = new UserClient(await NewContextAsync(await Tokens.TestUser.GetAccessTokenAsync()));
        anonymousClient = new UserClient(await NewContextAsync(string.Empty));
    }

    [Test]
    [AllureStory("TC-USER-001 — list users")]
    [AllureSeverity(SeverityLevel.critical)]
    public async Task Should_ReturnUsers_When_TheCallerIsAuthorized()
    {
        List<UserDto> users = await userClient.GetAllAsync(HttpStatusCode.OK);

        Assert.That(users, Is.Not.Empty, "Expected at least one user.");
    }

    [Test]
    [AllureStory("TC-USER-002 — unauthorized")]
    [AllureSeverity(SeverityLevel.critical)]
    public async Task Should_Return401_When_TheCallerIsAnonymous()
    {
        IAPIResponse response = await anonymousClient.GetAllAsync();

        Assert.That((HttpStatusCode)response.Status, Is.EqualTo(HttpStatusCode.Unauthorized), await response.TextAsync());
    }

    [Test]
    [AllureStory("TC-USER-004 — not found")]
    [AllureSeverity(SeverityLevel.normal)]
    public async Task Should_ReturnANotFoundProblem_When_TheUserDoesNotExist()
    {
        IAPIResponse response = await userClient.GetByIdAsync("999999");

        AttachBody(response);
        Assert.That((HttpStatusCode)response.Status, Is.EqualTo(HttpStatusCode.NotFound));
        ProblemDetailsDto problem = Deserialize<ProblemDetailsDto>(response);
        Assert.Multiple(() =>
        {
            Assert.That(problem.Type, Is.EqualTo("BusinessViolation"));
            Assert.That(problem.ErrorCode, Is.EqualTo("USER_NOT_FOUND"));
        });
    }
}
```

- The clients are built in the fixture's `[SetUp]`, after `PlaywrightTest` created `Playwright`; the base
  `[TearDown]` disposes their contexts after the fixture's own `[TearDown]` has cleaned up.
- The 401 test asserts the status only, with the body as the message: auth middleware emits no
  `ProblemDetails`.

## Cleanup — `[TearDown]` only

Create/update flows keep the RestSharp sibling's discipline: the rich happy-path template (request fields +
server-generated fields + `GetById` round-trip in `Assert.Multiple`), and cleanup in the fixture's
**`[TearDown]` only**. Each test records the ids it created; the `[TearDown]` deletes them through the client and
asserts each delete's exact status, with the body as the message. No `try`/`catch`/`finally` in a test or a
hook.

```csharp
private readonly List<string> createdUserIds = [];

[Test]
[AllureStory("TC-USER-010 — create")]
[AllureSeverity(SeverityLevel.critical)]
public async Task Should_ReturnTheCreatedUser_When_TheRequestIsValid()
{
    CreateUserRequest request = Users.AValidRequest().Build();

    UserDto created = await userClient.CreateAsync(request, HttpStatusCode.Created);
    createdUserIds.Add(created.Id);

    UserDto fetched = await userClient.GetByIdAsync(created.Id, HttpStatusCode.OK);
    Assert.Multiple(() =>
    {
        Assert.That(created.Email, Is.EqualTo(request.Email));
        Assert.That(created.Id, Is.Not.Empty);
        Assert.That(fetched, Is.EqualTo(created));
    });
}

[TearDown]
public async Task DeleteCreatedUsersAsync()
{
    await Assert.MultipleAsync(async () =>
    {
        foreach (string id in createdUserIds)
        {
            IAPIResponse deleted = await userClient.DeleteAsync(id);
            Assert.That((HttpStatusCode)deleted.Status, Is.EqualTo(HttpStatusCode.NoContent), $"DELETE /users/{id}: {await deleted.TextAsync()}");
        }
    });
    createdUserIds.Clear();
}
```

- The id is recorded **before** any assertion, so a failing assertion still leaves the record for the
  teardown to delete.
- `Assert.MultipleAsync` attempts every delete and reports each failure, instead of leaking the rest behind the
  first one. The fixture's `[TearDown]` runs before the base one, so `userClient`'s context is still open.
- The request comes from a builder (`qa/dotnet/skills/test-data-builder`) — four or more fields.
