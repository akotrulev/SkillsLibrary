# Deep-dive details — `qa-api-test-graphql-dotnet`

Sections moved out of SKILL.md for on-demand loading. Read what the task needs.

## Three layers

### 1. Operation — `ApiTests/Operations/UserOperations.cs`

Operations are **parameterized documents**: variable values live in a separate object passed as `variables`,
**never interpolated into the query string** (interpolation invites injection and defeats server-side query
caching / APQ).

```csharp
namespace ApiTests.Operations;

public static class UserOperations
{
    public const string GetUser = """
        query GetUser($id: ID!) {
          user(id: $id) {
            id
            email
            firstName
            lastName
          }
        }
        """;

    public const string CreateUser = """
        mutation CreateUser($input: CreateUserInput!) {
          createUser(input: $input) {
            id
            email
            firstName
            lastName
          }
        }
        """;
}
```

### 2. Client — `ApiTests/Clients/GraphQLBaseClient.cs` + `UserGraphQLClient.cs`

`ExecuteAsync` POSTs `{ query, variables }` and **always returns the raw `GraphQLResponse<T>`** — it never
throws on a GraphQL error, because the test decides whether errors are expected.

```csharp
using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using ApiTests.Models;

namespace ApiTests.Clients;

public abstract class GraphQLBaseClient
{
    private static readonly HttpClient Http = new();
    private static readonly JsonSerializerOptions JsonOptions =
        new() { PropertyNameCaseInsensitive = true };   // GraphQL JSON is camelCase; map to PascalCase records

    private readonly string _endpoint = ConfigurationLoader.GraphQLEndpoint;   // e.g. https://api.example.com/graphql
    protected readonly Dictionary<string, string> Headers = new();

    protected async Task<GraphQLResponse<T>> ExecuteAsync<T>(string query, object? variables = null)
    {
        return await SendAsync<T>(new { query, variables });
    }

    // Forwards `extensions` too — used by the persisted-query tests.
    protected async Task<GraphQLResponse<T>> ExecuteRawAsync<T>(object payload)
    {
        return await SendAsync<T>(payload);
    }

    private async Task<GraphQLResponse<T>> SendAsync<T>(object payload)
    {
        using HttpRequestMessage request = new(HttpMethod.Post, _endpoint)
        {
            Content = JsonContent.Create(payload),
        };
        foreach (KeyValuePair<string, string> header in Headers)
        {
            request.Headers.TryAddWithoutValidation(header.Key, header.Value);
        }

        using HttpResponseMessage response = await Http.SendAsync(request);
        string raw = await response.Content.ReadAsStringAsync();
        GraphQLEnvelope<T>? body = JsonSerializer.Deserialize<GraphQLEnvelope<T>>(raw, JsonOptions);

        return new GraphQLResponse<T>(response.StatusCode, body!.Data, body.Errors);
        // NOTE: no throw on body.Errors — returning the envelope is the whole point.
    }
}
```

```csharp
using ApiTests.Models;
using ApiTests.Operations;

namespace ApiTests.Clients;

public sealed class UserGraphQLClient : GraphQLBaseClient
{
    public UserGraphQLClient(string authToken)
    {
        if (!string.IsNullOrEmpty(authToken))
        {
            Headers["authorization"] = $"Bearer {authToken}";
        }
    }

    public Task<GraphQLResponse<GetUserData>> GetUserAsync(string id) =>
        ExecuteAsync<GetUserData>(UserOperations.GetUser, new { id });

    public Task<GraphQLResponse<CreateUserData>> CreateUserAsync(CreateUserInput input) =>
        ExecuteAsync<CreateUserData>(UserOperations.CreateUser, new { input });
}
```

### 3. Models — `ApiTests/Models/`

Records (immutability preferred). The `Data` record models the **selection set**; the error envelope is shared.

```csharp
using System.Net;
using System.Text.Json.Serialization;

namespace ApiTests.Models;

// The wire envelope as it arrives: { "data": {...}, "errors": [...] }
public sealed record GraphQLEnvelope<T>(T? Data, IReadOnlyList<GraphQLError>? Errors);

// What the client hands the test — HTTP status folded in.
public sealed record GraphQLResponse<T>(HttpStatusCode Status, T? Data, IReadOnlyList<GraphQLError>? Errors);

public sealed record GraphQLError(
    string Message,
    [property: JsonPropertyName("path")] IReadOnlyList<object>? Path,
    [property: JsonPropertyName("extensions")] GraphQLErrorExtensions? Extensions);

public sealed record GraphQLErrorExtensions(
    [property: JsonPropertyName("code")] string? Code);

// User entity — only the fields the operation selects.
public sealed record User(string Id, string Email, string FirstName, string LastName);

// Per-operation data shapes (the selection set).
public sealed record GetUserData(User? User);          // `user` is nullable — not-found returns null + an errors[] entry
public sealed record CreateUserData(User CreateUser);

public sealed record CreateUserInput(string Email, string FirstName, string LastName);
```

### 4. Test — `ApiTests/Tests/UserGraphQLTests.cs`

Status first (it's 200 — assert it, but it is *not* the gate), then the **envelope** is the gate.

```csharp
using System.Net;
using ApiTests.Clients;
using ApiTests.Models;
using Allure.NUnit.Attributes;
using NUnit.Framework;

namespace ApiTests.Tests;

[TestFixture]
public class UserGraphQLTests : BaseApiTest
{
    [Test]
    [AllureFeature("Users")]
    [AllureStory("Query user")]
    public async Task GetUser_WhenExists_ReturnsUserWithoutErrors()
    {
        UserGraphQLClient userClient = new(AuthToken);

        GraphQLResponse<GetUserData> response = await userClient.GetUserAsync("1");

        Assert.Multiple(() =>
        {
            Assert.That(response.Status, Is.EqualTo(HttpStatusCode.OK));   // 200 even when wrong — assert, not the gate
            Assert.That(response.Errors, Is.Null);                         // THE gate for a happy path
            Assert.That(response.Data!.User, Is.Not.Null);
            Assert.That(response.Data.User!.Email, Is.EqualTo("george.bluth@example.com"));
        });
    }

    [Test]
    [AllureFeature("Users")]
    [AllureStory("Query user — not found")]
    public async Task GetUser_WhenUnknownId_ReturnsNotFoundErrorWithHttp200()
    {
        UserGraphQLClient userClient = new(AuthToken);

        GraphQLResponse<GetUserData> response = await userClient.GetUserAsync("999999");

        Assert.Multiple(() =>
        {
            Assert.That(response.Status, Is.EqualTo(HttpStatusCode.OK));        // NOT 404 — GraphQL keeps the 200
            Assert.That(response.Errors, Is.Not.Null.And.Not.Empty);           // assert on the ENVELOPE
            Assert.That(response.Errors![0].Extensions!.Code, Is.EqualTo("NOT_FOUND"));
            Assert.That(response.Errors[0].Path, Is.EqualTo(new object[] { "user" }));   // error names the failing field
            Assert.That(response.Data!.User, Is.Null);                         // data present; failing field null
        });
    }

    [Test]
    [AllureFeature("Users")]
    [AllureStory("Query user — unauthenticated")]
    public async Task GetUser_WhenNoToken_ReturnsUnauthenticated()
    {
        UserGraphQLClient userClient = new(string.Empty);

        GraphQLResponse<GetUserData> response = await userClient.GetUserAsync("1");

        // Two valid server designs: a 200 with an errors[] code, OR a transport 401. Assert the contract you have.
        if (response.Status == HttpStatusCode.OK)
        {
            Assert.That(response.Errors![0].Extensions!.Code, Is.EqualTo("UNAUTHENTICATED"));
        }
        else
        {
            Assert.That(response.Status, Is.EqualTo(HttpStatusCode.Unauthorized));
        }
    }
}
```

> The unauthenticated test shows the **one place a GraphQL response legitimately varies its HTTP status** — auth
> middleware may reject at the transport (401) before any resolver runs, or the schema may surface
> `UNAUTHENTICATED` in `errors[]` with a 200. This is the *only* conditional you'll see in these fixtures; pin it
> to your server's actual contract and delete the branch you don't use. (CLAUDE.md bans conditionals that *drive
> assertions* across cases; this single contract-pinning branch is the documented exception, not a loop.)
