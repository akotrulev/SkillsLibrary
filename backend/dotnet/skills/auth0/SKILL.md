---
name: be-dotnet-auth0
description: Use when setting up or modifying Auth0 in an ASP.NET Core service (.NET 10 primary, 8/9) — JWT bearer validation, RBAC policies, Authorization Code + PKCE for server-rendered web, Client Credentials M2M, custom claim mapping. Triggers: "add Auth0 to my ASP.NET Core API", "validate Auth0 JWTs in .NET", "wire [Authorize(Policy=...)] for permissions". Do NOT use for SPA flows (`auth/auth0-react` / `auth/auth0-blazor`), Cognito (the `cognito` sibling), or concepts (`auth/_shared/auth0-concepts`).
---

# Auth — Auth0 in ASP.NET Core (.NET 10 primary / 8-9 supported)

Wires Auth0 into an ASP.NET Core service. Validates RS256 JWTs from Auth0 via JWKS, enforces RBAC permissions through authorization policies, and calls outbound APIs with the Client Credentials flow. Reads cleanly against the concepts in `auth/_shared/auth0-concepts` — read that first if you're unfamiliar.

## Version policy

Detect the project's `<TargetFramework>` (`net8.0` / `net9.0` / `net10.0`) before wiring. Everything below — `AddJwtBearer`, `AddAuthorization` policies, `AddOpenIdConnect`, `IHttpClientFactory` + `DelegatingHandler` — is unchanged across 8/9/10. Never flag a down-level project for lacking a net10-only API; none is used here.

## Stack

- **.NET 10 primary, 8/9 supported** + ASP.NET Core
- `Microsoft.AspNetCore.Authentication.JwtBearer`
- For outbound M2M: `IHttpClientFactory` + `Microsoft.IdentityModel.Tokens` (no Auth0-specific SDK needed for the call)
- For server-rendered web that signs users in (rare; SPA is the default for browsers): `Microsoft.AspNetCore.Authentication.OpenIdConnect`
- Configuration via `appsettings.json` overrides + env vars + Key Vault — never hardcoded

## When to use

- Protecting an ASP.NET Core Web API with Auth0 JWTs
- Adding `[Authorize(Policy = "orders:read")]`-style permission checks
- Calling another API with Client Credentials (M2M)
- A server-rendered MVC / Razor Pages app that needs to sign users in via Auth0 (Authorization Code + PKCE)

## When NOT to use

- React SPA token acquisition → `auth/auth0-react`
- Blazor Server / WASM → `auth/auth0-blazor`
- Java / Spring → `backend/java/skills/auth0`
- AWS Cognito instead of Auth0 → `backend/dotnet/skills/cognito`
- Concepts (audience, RBAC, organizations) → `auth/_shared/auth0-concepts`

## Inputs needed

1. **Auth0 tenant domain** per env (`yourco-dev.eu.auth0.com`)
2. **API identifier** (the JWT `aud`) — `https://api.yourco.com` (or per-service equivalent)
3. **Required permissions** per endpoint (e.g. `orders:read`, `orders:write`)
4. **Outbound M2M targets** (other APIs, their audience + required scopes)
5. **Custom claim namespace** if your tenant adds `https://yourco.com/<claim>` claims

## Inbound — validating Auth0 JWTs

### Packages

```bash
dotnet add package Microsoft.AspNetCore.Authentication.JwtBearer
```

### Program.cs

```csharp
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.IdentityModel.Tokens;
using System.Security.Claims;

var builder = WebApplication.CreateBuilder(args);

var domain   = builder.Configuration["Auth0:Domain"]!;     // yourco-dev.eu.auth0.com
var audience = builder.Configuration["Auth0:Audience"]!;   // https://api.yourco.com

builder.Services
    .AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
    .AddJwtBearer(options =>
    {
        options.Authority = $"https://{domain}/";
        options.Audience  = audience;
        options.RequireHttpsMetadata = true;
        options.TokenValidationParameters = new TokenValidationParameters
        {
            ValidateIssuer           = true,
            ValidIssuer              = $"https://{domain}/",
            ValidateAudience         = true,
            ValidAudience            = audience,
            ValidateLifetime         = true,
            ValidateIssuerSigningKey = true,
            ClockSkew                = TimeSpan.FromSeconds(30),
            NameClaimType            = ClaimTypes.NameIdentifier,
        };
    });

builder.Services.AddAuthorization(o =>
{
    // One policy per Auth0 API permission
    o.AddPolicy("orders:read",  p => p.RequireAssertion(HasPermission("orders:read")));
    o.AddPolicy("orders:write", p => p.RequireAssertion(HasPermission("orders:write")));
});

static Func<AuthorizationHandlerContext, bool> HasPermission(string permission) =>
    ctx => ctx.User.Claims.Any(c => c.Type == "permissions" && c.Value == permission);
```

The `permissions` claim is the array Auth0 emits when **"Add Permissions in the Access Token"** is enabled on the API (per `auth/_shared/auth0-concepts`).

### appsettings.json

```json
{
  "Auth0": {
    "Domain":   "yourco-dev.eu.auth0.com",
    "Audience": "https://api.yourco.com"
  }
}
```

Per-env overrides (`appsettings.Production.json` or env vars: `Auth0__Domain`, `Auth0__Audience`). Never commit a production domain default.

### Pipeline

```csharp
var app = builder.Build();

app.UseAuthentication();
app.UseAuthorization();

app.MapGet("/orders",       () => /* ... */).RequireAuthorization("orders:read");
app.MapPost("/orders",      (CreateOrder dto) => /* ... */).RequireAuthorization("orders:write");
app.MapGet("/orders/{id}",  (Guid id) => /* ... */).RequireAuthorization("orders:read");
```

For Controllers, decorate with `[Authorize(Policy = "orders:read")]`. For Minimal API, `.RequireAuthorization("...")`.

### Reading user / tenant claims

```csharp
app.MapGet("/me", (ClaimsPrincipal user) => new
{
    sub      = user.FindFirstValue(ClaimTypes.NameIdentifier),
    email    = user.FindFirstValue("email"),
    tenantId = user.FindFirstValue("https://yourco.com/tenant_id"),
    perms    = user.FindAll("permissions").Select(c => c.Value).ToArray(),
});
```

Custom claims live under the namespace declared by your post-login Action; the prefix is non-negotiable (Auth0 drops un-namespaced custom claims).

## Outbound — Client Credentials (M2M)

When this service needs to call another protected API, request an access token from Auth0 and forward it.

### Token acquisition with caching

```csharp
public sealed class Auth0M2MTokenService(IHttpClientFactory http, IMemoryCache cache, IConfiguration cfg)
{
    public async Task<string> GetTokenAsync(string targetAudience, CancellationToken ct)
    {
        var key = $"m2m:{targetAudience}";
        if (cache.TryGetValue<string>(key, out var cached) && cached is not null) return cached;

        using var client = http.CreateClient();
        var resp = await client.PostAsync(
            $"https://{cfg["Auth0:Domain"]}/oauth/token",
            new FormUrlEncodedContent(new Dictionary<string, string>
            {
                ["grant_type"]    = "client_credentials",
                ["client_id"]     = cfg["Auth0:M2M:ClientId"]!,
                ["client_secret"] = cfg["Auth0:M2M:ClientSecret"]!,
                ["audience"]      = targetAudience,
            }), ct);

        resp.EnsureSuccessStatusCode();
        var payload = await resp.Content.ReadFromJsonAsync<TokenResponse>(cancellationToken: ct)
                      ?? throw new InvalidOperationException("Empty token response");

        // Cache for (expires_in - 60s) so we refresh before expiry
        cache.Set(key, payload.AccessToken, TimeSpan.FromSeconds(payload.ExpiresIn - 60));
        return payload.AccessToken;
    }

    private sealed record TokenResponse(
        [property: System.Text.Json.Serialization.JsonPropertyName("access_token")] string AccessToken,
        [property: System.Text.Json.Serialization.JsonPropertyName("expires_in")]   int    ExpiresIn);
}
```

Register `IHttpClientFactory`, `AddMemoryCache()`, and `AddSingleton<Auth0M2MTokenService>()`. Use as a delegating handler on the typed `HttpClient` for the downstream API so calls automatically carry the token:

```csharp
public sealed class M2MAuthHandler(Auth0M2MTokenService tokens, IOptions<DownstreamOptions> opt) : DelegatingHandler
{
    protected override async Task<HttpResponseMessage> SendAsync(HttpRequestMessage req, CancellationToken ct)
    {
        var token = await tokens.GetTokenAsync(opt.Value.Audience, ct);
        req.Headers.Authorization = new("Bearer", token);
        return await base.SendAsync(req, ct);
    }
}

services.AddHttpClient<IOrdersDownstream, OrdersDownstream>(c => c.BaseAddress = new Uri(opt.Value.BaseUrl))
        .AddHttpMessageHandler<M2MAuthHandler>();
```

Each downstream API gets its own M2M Application in Auth0 — never share a client secret across services.

## Server-rendered web (Authorization Code + PKCE)

Only when the app is a server-rendered MVC / Razor Pages app that needs to sign in browsers. If the user-facing UI is a SPA, use `auth/auth0-react` and consume the API instead.

```csharp
builder.Services
    .AddAuthentication(o => { o.DefaultScheme = "Cookies"; o.DefaultChallengeScheme = "Auth0"; })
    .AddCookie("Cookies")
    .AddOpenIdConnect("Auth0", o =>
    {
        o.Authority    = $"https://{domain}";
        o.ClientId     = cfg["Auth0:Web:ClientId"];
        o.ClientSecret = cfg["Auth0:Web:ClientSecret"];        // Regular Web App, has a secret
        o.ResponseType = "code";
        o.UsePkce      = true;
        o.Scope.Clear();
        o.Scope.Add("openid"); o.Scope.Add("profile"); o.Scope.Add("email");
        o.SaveTokens = true;
        o.CallbackPath  = "/callback";
        o.SignedOutCallbackPath = "/signout-callback";
    });
```

Log out via `/v2/logout?client_id=...&returnTo=...` on the Auth0 side **and** clear the local cookie.

## Rules

- One Auth0 API per backend service; one Application per client (SPA, M2M)
- Permissions are the source of truth for authorization — `[Authorize(Policy = "permission:name")]`, never role-string checks scattered through code
- Configuration via `Auth0:Domain` + `Auth0:Audience` (and `Auth0:M2M:*` for outbound) in `appsettings.json` + env vars; client secrets in Key Vault / Secrets Manager only
- HTTPS metadata required (`RequireHttpsMetadata = true`) in every non-local environment
- Clock skew capped at 30 seconds — not the default 5 minutes
- Custom claims always read via the full namespaced URI (`https://yourco.com/tenant_id`)
- M2M tokens cached locally with a safety margin (`expires_in - 60s`)
- Outbound HTTP uses a typed `HttpClient` with `DelegatingHandler` for auth — never manual `Authorization` headers in business code
- `[AllowAnonymous]` only on health / metrics / OIDC discovery endpoints

## What NOT to do

- No `HS256` validation — Auth0 issues RS256 access tokens; reject anything else
- No `ValidateLifetime = false` to "fix" clock issues — fix the clock or raise `ClockSkew` slightly
- No `Permissions in the Access Token` left off in the Auth0 API settings — silently empties the `permissions` claim
- No reading the access token in business code to extract user info — use `ClaimsPrincipal`
- No calling the API with the ID Token — that's a configuration bug somewhere upstream; fix the SPA / client
- No client secret in the SPA, Native, or mobile clients — PKCE replaces it
- No fetching JWKS manually — `AddJwtBearer` does it with caching and rotation
- No `[Authorize]` with no policy on an endpoint that needs a specific permission — be explicit
- No M2M token request per outbound call — cache; renew at `expires_in - 60s`
- No `client_credentials` for user-facing flows — that's a service identity, not a user

## Generation steps

1. Confirm tenant domain (per env), API identifier (audience), required permissions per endpoint, and whether the service makes outbound M2M calls.
2. Install `Microsoft.AspNetCore.Authentication.JwtBearer`. Add `AddAuthentication().AddJwtBearer(...)` and `AddAuthorization(o => { ... })` policies — one per Auth0 permission.
3. Add `app.UseAuthentication()` + `app.UseAuthorization()` to the pipeline.
4. Decorate endpoints with `.RequireAuthorization("permission:name")`.
5. If outbound M2M is needed: add `Auth0M2MTokenService` + `M2MAuthHandler` and register typed clients.
6. If server-rendered sign-in is needed: add `AddOpenIdConnect("Auth0", ...)` and cookie auth.
7. Smoke test: hit `/me` with a fresh access token; confirm `permissions` array; revoke and re-fetch.

## Handoffs

- Concepts → `auth/_shared/auth0-concepts`
- React SPA token acquisition → `auth/auth0-react`
- Blazor → `auth/auth0-blazor`
- Java backend equivalent → `backend/java/skills/auth0`
- AWS Cognito equivalent → `backend/dotnet/skills/cognito`
- Pattern/persistence scaffolding for the rest of the service → `backend/dotnet/skills/{generator,persistence}`
- Storing client secrets → `devops/environment-config` + Key Vault
- API contract tests with auth → `qa/dotnet/skills/api-test-author/generator` + `qa/dotnet/skills/auth0-test-tokens` (use a seeded test user; document tenant in `qa/manual/test-strategy`)
