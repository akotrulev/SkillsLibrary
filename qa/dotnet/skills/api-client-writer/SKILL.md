---
name: qa-api-client-writer-dotnet
description: Use when the user asks to create a new API client or `*Client.cs` file in the Accelerator `ApiTests` project (RestSharp, .NET 8). Triggers: "write an API client for X", "add a Client.cs for the {resource} endpoints", "scaffold {Resource}Client".
---

# qa-api-client-writer-dotnet

Generator skill. Scaffolds a single `{Resource}Client.cs` file in the Accelerator `ApiTests` project, following the conventions below.

## When to use

- The user asks to add a new client class under `ApiTests/Clients/`.
- A new endpoint group has been added to the API under test and needs a typed wrapper for tests to call.
- The user is adding endpoints to an existing resource and wants the client extended in the same style.

## When NOT to use

- Writing the test fixture or test cases — that's `qa/dotnet/skills/api-test-author/generator`.
- Reviewing an existing client for convention drift — that's a reviewer skill.
- Authoring DTOs the client returns — use `qa/dotnet/skills/api-dto-writer` first, then come back here.
- Java stack (RestAssured) — use `qa/java/skills/api-client-writer`.
- TypeScript stack (native `fetch` + Zod) — use `qa/typescript/skills/api-client-writer`.
- Any non-.NET / non-RestSharp stack not covered by the siblings above.

## Folder & naming convention

Clients are organized by API group. **No Public/Management subfolders, no `P`/`M` suffix** — one client per resource holds both user-facing and admin endpoints when both exist.

```
ApiTests/Clients/
├── BaseApiClient.cs
├── AuthHelper.cs
├── AuthConfigClient.cs           ← root, no auth required
└── {Api}/
    └── {Resource}Client.cs       ← one file per resource
```

**Exception:** `AuthConfigClient` lives at the root `Clients/` — it is unauthenticated and has no API group.

### API group reference

| API Group  | Clients                                                        |
|------------|----------------------------------------------------------------|
| User       | UserClient, KycClient, ConsentClient, PreferencesClient, WatchlistClient |
| Assessment | AssessmentClient                                               |
| Legal      | DocumentClient                                                 |
| Reference  | ReferenceClient                                                |
| Auth       | AuthConfigClient (root, no group — unauthenticated)            |

When a resource has both user-facing (`/api/{resource}/...`) and admin (`/api/management/{resource}/...`) endpoints, both live in the same client. Distinguish them via the path constant names (e.g. `GetAllPath` vs `GetAllManagementPath`).

## Dual-method pattern

Every endpoint that returns a DTO gets **two overloads**:

1. **Raw** — returns `RestResponse` (no assertion, no deserialization). Used when the test inspects the status code itself (negative tests).
2. **Typed** — same signature plus a trailing `HttpStatusCode expected` parameter. Calls the raw overload, asserts the status, and returns the deserialized DTO. Used as a convenience in happy-path tests.

```csharp
// Raw — caller handles assertion and deserialization.
public RestResponse GetById(string id) =>
    Execute(new RestRequest(GetByIdPath).AddUrlSegment("id", id));

// Typed — asserts status, returns deserialized DTO.
public {Resource}Dto GetById(string id, HttpStatusCode expected)
{
    var response = GetById(id);
    Assert.That(response.StatusCode, Is.EqualTo(expected));
    return Deserialize<{Resource}Dto>(response);
}
```

For collection responses:

```csharp
public RestResponse GetAll() =>
    Execute(new RestRequest(GetAllPath));

public List<{Resource}Dto> GetAll(HttpStatusCode expected)
{
    var response = GetAll();
    Assert.That(response.StatusCode, Is.EqualTo(expected));
    return Deserialize<List<{Resource}Dto>>(response);
}
```

Endpoints with **no response body** (DELETE → 204, PATCH → 204) get only the raw method — there is no DTO to deserialize.

## Template

```csharp
using System.Net;
using ApiTests.Config;
using ApiTests.Models.{Api}.{Resource}Models;
using NUnit.Framework;
using RestSharp;

namespace ApiTests.Clients.{Api};

public class {Resource}Client : BaseApiClient
{
    // User-facing endpoints
    private const string GetAllPath = "/api/{basePath}";
    private const string GetByIdPath = "/api/{basePath}/{id}";
    private const string PostPath = "/api/{basePath}";

    // Management endpoints (only if this resource exposes admin operations)
    private const string GetAllManagementPath = "/api/management/{basePath}";
    private const string PutManagementPath = "/api/management/{basePath}/{id}";
    private const string PatchManagementPath = "/api/management/{basePath}/{id}";
    private const string DeleteManagementPath = "/api/management/{basePath}/{id}";

    public {Resource}Client(string jwt)
        : base(ConfigurationLoader.GetTestEnvironment().ApiUri)
    {
        SetDefaultHeader("Authorization", $"Bearer {jwt}");
    }

    // Returns all {resource}s (user-facing).
    public RestResponse GetAll() =>
        Execute(new RestRequest(GetAllPath));

    public List<{Resource}Dto> GetAll(HttpStatusCode expected)
    {
        var response = GetAll();
        Assert.That(response.StatusCode, Is.EqualTo(expected));
        return Deserialize<List<{Resource}Dto>>(response);
    }

    // Returns a single {resource} by id.
    public RestResponse GetById(string id) =>
        Execute(new RestRequest(GetByIdPath).AddUrlSegment("id", id));

    public {Resource}Dto GetById(string id, HttpStatusCode expected)
    {
        var response = GetById(id);
        Assert.That(response.StatusCode, Is.EqualTo(expected));
        return Deserialize<{Resource}Dto>(response);
    }

    // Creates a new {resource}.
    public RestResponse Create({Resource}InDto body) =>
        Execute(new RestRequest(PostPath, Method.Post).AddJsonBody(body));

    public {Resource}Dto Create({Resource}InDto body, HttpStatusCode expected)
    {
        var response = Create(body);
        Assert.That(response.StatusCode, Is.EqualTo(expected));
        return Deserialize<{Resource}Dto>(response);
    }

    // --- Management operations (only if applicable) ---

    // Returns all {resource}s (admin view).
    public RestResponse GetAllManagement() =>
        Execute(new RestRequest(GetAllManagementPath));

    public List<{Resource}Dto> GetAllManagement(HttpStatusCode expected)
    {
        var response = GetAllManagement();
        Assert.That(response.StatusCode, Is.EqualTo(expected));
        return Deserialize<List<{Resource}Dto>>(response);
    }

    // Replaces the {resource} with the given id.
    public RestResponse Update(string id, {Resource}InDto body) =>
        Execute(new RestRequest(PutManagementPath, Method.Put)
            .AddUrlSegment("id", id)
            .AddJsonBody(body));

    // Partially updates the {resource} with the given id.
    public RestResponse PatchById(string id, {Resource}ModDto body) =>
        Execute(new RestRequest(PatchManagementPath, Method.Patch)
            .AddUrlSegment("id", id)
            .AddJsonBody(body));

    // Deletes the {resource} with the given id.
    public RestResponse Remove(string id) =>
        Execute(new RestRequest(DeleteManagementPath, Method.Delete).AddUrlSegment("id", id));
}
```

Omit any block that does not apply — e.g. a read-only reference client has no `Create`/`Update`/`Remove`; a public-only resource has no management section.

### Requests with query parameters

```csharp
// Returns a paginated list of {resource}s.
public RestResponse GetAll(int page, int resultsPerPage)
{
    var request = new RestRequest(GetAllPath)
        .AddQueryParameter("page", page)
        .AddQueryParameter("per_page", resultsPerPage);
    return Execute(request);
}
```

## Rules

### Class structure

- Class name: `{Resource}Client` — PascalCase resource noun + `Client`. **No `P`/`M` suffix.**
- Always inherit from `BaseApiClient` (never from `RestClient` directly).
- Namespace follows folder: `ApiTests.Clients.{Api}` (or root `ApiTests.Clients` for `AuthConfigClient`).
- Usings: `ApiTests.Config` + `ApiTests.Models.{Api}.{Resource}Models` + `RestSharp` — typed overloads also require `System.Net` and `NUnit.Framework`. No other imports unless strictly required.

### Constructor

- Constructor takes `string jwt`.
- Always calls `base(ConfigurationLoader.GetTestEnvironment().ApiUri)`.
- Always calls `SetDefaultHeader("Authorization", $"Bearer {jwt}")` — pass `string.Empty` for unauthenticated calls.
- Never call `AuthHelper.GetToken()` inside the client — the test obtains the token and passes it in.
- Never hardcode a URI string or credentials.

### Path constants

- One `private const string` per distinct path pattern at the top of the class.
- Name after purpose: `GetAllPath`, `GetByIdPath`, `PostPath`, `DeletePath`, etc.
- For resources with both user-facing and admin endpoints, suffix the management variants: `GetAllManagementPath`, `PutManagementPath`, etc.
- User-facing paths start with `/api/`; admin paths start with `/api/management/`.

### Method signatures

- Every endpoint that returns a DTO gets two overloads: raw `RestResponse` + typed (`HttpStatusCode expected`, asserts, returns DTO).
- Endpoints with no response body get only the raw overload.
- The typed overload calls the raw overload — do not duplicate request-building logic.
- Build a `RestRequest` and call inherited `Execute(request)`.
- Use `AddUrlSegment` for path params, `AddQueryParameter` for query strings, `AddJsonBody` for bodies.
- Body parameters are strongly-typed DTOs (e.g. `{Resource}InDto body`), not `object`.
- One-line comment per raw method; not repeated on the typed overload.
- Deserialization uses inherited `Deserialize<T>(response)` — never `JsonSerializer.Deserialize` directly.

### Method naming

| Operation             | Method name                              |
|-----------------------|------------------------------------------|
| Fetch collection      | `GetAll()`                               |
| Fetch admin collection| `GetAllManagement()`                     |
| Fetch by id           | `GetById(string id)`                     |
| Fetch by other key    | `GetBy{Key}({type} key)`                 |
| Create                | `Create({Resource}InDto body)`           |
| Full replace          | `Update(string id, {Resource}InDto body)`|
| Partial update        | `PatchById(string id, {Resource}ModDto body)` |
| Delete                | `Remove(string id)`                      |

### Raw body and object overloads (body manipulation tests only)

When the test plan includes **malformed JSON** scenarios:

```csharp
// Sends a raw string body (for malformed JSON testing).
public RestResponse CreateRaw(string rawJson) => PostRaw(PostPath, rawJson);
```

When the test plan includes **extra/missing property** scenarios, add an `object` overload for `Dictionary<string, object?>` bodies from `JsonBodyHelper`:

```csharp
// Accepts a pre-built body (e.g. from JsonBodyHelper) for body manipulation tests.
public RestResponse Create(object body) =>
    Execute(new RestRequest(PostPath, Method.Post).AddJsonBody(body));
```

Only add these overloads when the test plan requires them — not by default.

### What NOT to do

- No `Thread.Sleep()` or manual delays.
- No `RestClient` instantiation inside the class — that's `BaseApiClient`'s job.
- No hardcoded base URLs or credentials.
- No try/catch around HTTP calls — `BaseApiClient` logs failures automatically.
- Do not re-implement `LogResponse` logic — it's wired into every verb method in `BaseApiClient`.
- Do not deserialize in raw `RestResponse` methods — only in typed overloads.
- No `object` body parameters on the default overloads — always strongly-typed DTOs.
- No `P`/`M` class-name suffix, no `Public/` or `Management/` subfolders.

## Generation steps

0. If an **OpenAPI/Swagger spec** is supplied, derive the answers to steps 1–3 from it (API group from the path/tags, resource + base path segment from the paths, operations from the methods defined) — do not ask.
1. Ask the user: which **API group** does this client belong to? (User / Assessment / Legal / Reference / Auth)
2. Ask the user: resource name (noun) and base URL path segment (e.g. `users`).
3. Ask which **operations** are needed, and whether they are user-facing, admin, or both. Default to full CRUD on the user-facing surface.
4. Ensure the required DTOs exist in `Models/{Api}/{Resource}Models/`. If not, run the `api-dto-writer` skill first.
5. Generate the file at `ApiTests/Clients/{Api}/{Resource}Client.cs`.
6. Run `dotnet build ApiTests/ApiTests.csproj` — expect 0 errors.
