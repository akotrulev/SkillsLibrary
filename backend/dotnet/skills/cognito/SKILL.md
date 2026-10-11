---
name: cognito
description: Use when setting up AWS Cognito (user pools) in an ASP.NET Core service (.NET 10 primary, 8/9) — validating Cognito access-token JWTs (issuer/JWKS, no `aud`, `token_use=access`), resource-server scope policies, `cognito:groups` roles, Client Credentials M2M. Triggers: "add Cognito to my ASP.NET Core API", "why does my Cognito token have no audience". Do NOT use for the Blazor SPA flow (`auth/cognito-blazor`), Auth0 (the `auth0` sibling), or generic OIDC (`auth/_shared/oidc-concepts`).
---

# Auth — AWS Cognito in ASP.NET Core (.NET 10 primary / 8-9 supported)

Wires an Amazon Cognito **user pool** into an ASP.NET Core service as an OAuth2 resource server. Validates RS256 access-token JWTs via the pool's JWKS, authorizes by **resource-server scope** (and/or `cognito:groups`), and calls outbound APIs with the Client Credentials flow. The .NET sibling of `auth/cognito-blazor`; the Auth0 equivalent is `backend/dotnet/skills/auth0`.

> Generic OIDC/JWT concepts + the Auth0-vs-Cognito comparison live in `auth/_shared/oidc-concepts`.

## Version policy

Detect the project's `<TargetFramework>` before wiring. Everything below is unchanged across net8.0/net9.0/net10.0; never flag a down-level project for lacking a net10-only API.

## The Cognito deltas vs Auth0 (what this skill changes)

| Concern | Auth0 (`backend/dotnet/skills/auth0`) | **Cognito (here)** |
|---|---|---|
| Issuer | `https://{domain}/` | **`https://cognito-idp.{region}.amazonaws.com/{userPoolId}`** (JWKS at `/.well-known/jwks.json`, auto-discovered) |
| Audience | validate `aud` == API identifier | **no `aud` claim** on Cognito access tokens → **`ValidateAudience = false`**; instead validate **`token_use == "access"`** + **`client_id`** ∈ allowed clients |
| Permissions | `permissions` claim | **`scope` claim** (space-delimited resource-server scopes, e.g. `https://api.yourco.com/orders.read`) |
| Roles | namespaced custom claim | **`cognito:groups`** (array) |
| Outbound M2M | `/oauth/token` + `audience` param | **`{hostedDomain}/oauth2/token`** + `scope` param (resource-server scope); **no `audience`**; HTTP Basic client auth |

## Stack

- **.NET 10 primary, 8/9 supported** + ASP.NET Core, `Microsoft.AspNetCore.Authentication.JwtBearer`
- Outbound M2M: `IHttpClientFactory` + `IMemoryCache` (no Cognito SDK needed for the token call)
- Config via `appsettings.json` + env vars + Secrets Manager / Key Vault — never hardcoded

## When to use

- Protecting an ASP.NET Core Web API with Cognito user-pool access tokens
- `[Authorize(Policy = "orders:read")]`-style **scope** or **group** checks
- Calling another Cognito-protected API with Client Credentials (M2M)

## When NOT to use

- Blazor Server / WASM sign-in → `auth/cognito-blazor`
- Auth0 → `backend/dotnet/skills/auth0`
- Java → `backend/java/skills/cognito`
- Cognito **identity pools** / temporary AWS credentials → out of scope (user-pool OIDC only)
- Concepts → `auth/_shared/oidc-concepts`

## Inputs needed

1. **Region** + **`userPoolId`** per env
2. **Allowed `client_id`(s)** whose tokens this API accepts
3. **Resource server** identifier + **scopes** the API enforces (e.g. `https://api.yourco.com` → `orders.read`, `orders.write`)
4. **Outbound M2M** targets (their scopes + the hosted domain + a machine app client with secret)

## Inbound — validating Cognito access tokens

### Packages

```bash
dotnet add package Microsoft.AspNetCore.Authentication.JwtBearer
```

### Program.cs

```csharp
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.IdentityModel.JsonWebTokens;
using Microsoft.IdentityModel.Tokens;

var builder = WebApplication.CreateBuilder(args);

var region     = builder.Configuration["Cognito:Region"]!;        // eu-west-1
var userPoolId = builder.Configuration["Cognito:UserPoolId"]!;    // eu-west-1_ABC123
var allowedClientIds = builder.Configuration.GetSection("Cognito:AllowedClientIds").Get<string[]>() ?? [];
var issuer     = $"https://cognito-idp.{region}.amazonaws.com/{userPoolId}";

builder.Services
    .AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
    .AddJwtBearer(options =>
    {
        options.Authority = issuer;                                // JWKS discovered from {issuer}/.well-known/jwks.json
        options.RequireHttpsMetadata = true;
        options.TokenValidationParameters = new TokenValidationParameters
        {
            ValidateIssuer           = true,
            ValidIssuer              = issuer,
            ValidateAudience         = false,                      // Cognito access tokens carry NO aud claim
            ValidateLifetime         = true,
            ValidateIssuerSigningKey = true,
            ClockSkew                = TimeSpan.FromSeconds(30),
            NameClaimType            = "username",                 // access token: "username"; ID token: "cognito:username"
            RoleClaimType            = "cognito:groups",
        };
        // Replace the absent-audience check with token_use + client_id validation.
        options.Events = new JwtBearerEvents
        {
            OnTokenValidated = ctx =>
            {
                var jwt = (JsonWebToken)ctx.SecurityToken;
                if (jwt.GetClaim("token_use")?.Value != "access")
                    ctx.Fail("token_use is not 'access' (an ID token was presented).");
                var clientId = jwt.GetClaim("client_id")?.Value;
                if (allowedClientIds.Length > 0 && (clientId is null || !allowedClientIds.Contains(clientId)))
                    ctx.Fail("client_id is not in the allow-list.");
                return Task.CompletedTask;
            }
        };
    });

builder.Services.AddAuthorization(o =>
{
    // Fine-grained: resource-server scope on the space-delimited `scope` claim
    o.AddPolicy("orders:read",  p => p.RequireAssertion(HasScope("https://api.yourco.com/orders.read")));
    o.AddPolicy("orders:write", p => p.RequireAssertion(HasScope("https://api.yourco.com/orders.write")));
    // Coarse: Cognito group
    o.AddPolicy("admins", p => p.RequireRole("Admins"));
});

static Func<Microsoft.AspNetCore.Authorization.AuthorizationHandlerContext, bool> HasScope(string scope) =>
    ctx => ctx.User.FindFirst("scope")?.Value?.Split(' ', StringSplitOptions.RemoveEmptyEntries).Contains(scope) == true;
```

### appsettings.json

```json
{
  "Cognito": {
    "Region": "eu-west-1",
    "UserPoolId": "eu-west-1_ABC123",
    "AllowedClientIds": [ "<web-app-client-id>", "<spa-client-id>" ]
  }
}
```

Per-env overrides via env vars (`Cognito__Region`, `Cognito__UserPoolId`, …). Never commit a production pool id default.

### Pipeline & claims

```csharp
var app = builder.Build();
app.UseAuthentication();
app.UseAuthorization();

app.MapGet("/orders",      () => /* ... */).RequireAuthorization("orders:read");
app.MapPost("/orders",     (CreateOrder dto) => /* ... */).RequireAuthorization("orders:write");

app.MapGet("/me", (ClaimsPrincipal user) => new
{
    sub    = user.FindFirstValue("sub"),
    email  = user.FindFirstValue("email"),
    groups = user.FindAll("cognito:groups").Select(c => c.Value).ToArray(),
    scopes = user.FindFirst("scope")?.Value?.Split(' ') ?? [],
});
```

## Outbound — Client Credentials (M2M)

A machine app client (with secret) requests an access token carrying resource-server scopes:

```csharp
public sealed class CognitoM2MTokenService(IHttpClientFactory http, IMemoryCache cache, IConfiguration cfg)
{
    public async Task<string> GetTokenAsync(string scope, CancellationToken ct)
    {
        var key = $"cognito-m2m:{scope}";
        if (cache.TryGetValue<string>(key, out var cached) && cached is not null) return cached;

        using var client = http.CreateClient();
        var basic = Convert.ToBase64String(
            Encoding.ASCII.GetBytes($"{cfg["Cognito:M2M:ClientId"]}:{cfg["Cognito:M2M:ClientSecret"]}"));
        client.DefaultRequestHeaders.Authorization = new("Basic", basic);

        var resp = await client.PostAsync(
            $"{cfg["Cognito:HostedDomain"]}/oauth2/token",         // hosted-UI domain, NOT the issuer
            new FormUrlEncodedContent(new Dictionary<string, string>
            {
                ["grant_type"] = "client_credentials",
                ["scope"]      = scope,                            // resource-server scope; NO "audience"
            }), ct);

        resp.EnsureSuccessStatusCode();
        var payload = await resp.Content.ReadFromJsonAsync<TokenResponse>(cancellationToken: ct)
                      ?? throw new InvalidOperationException("Empty token response");
        cache.Set(key, payload.AccessToken, TimeSpan.FromSeconds(payload.ExpiresIn - 60));
        return payload.AccessToken;
    }

    private sealed record TokenResponse(
        [property: JsonPropertyName("access_token")] string AccessToken,
        [property: JsonPropertyName("expires_in")]   int    ExpiresIn);
}
```

Attach via a `DelegatingHandler` on the typed downstream client (same shape as `backend/dotnet/skills/auth0`'s Client Credentials section). Each downstream gets its own machine app client — never share a secret. Client-credentials tokens have **no user**, so `cognito:groups` is absent; authorize them by scope.

## Rules

- Issuer = the user-pool URL; **JWKS auto-discovered** — never build the JWKS URI by hand.
- **`ValidateAudience = false`** (no `aud`) — instead enforce **`token_use == "access"`** and an **allow-list of `client_id`s** in `OnTokenValidated`.
- Authorize by **resource-server scope** on the `scope` claim (`[Authorize(Policy=…)]`), roles by **`cognito:groups`** — never string-branch in handlers.
- Reject **ID tokens used as bearer** (they have `token_use == "id"`, an `aud`, and no `scope`).
- HTTPS metadata required; clock skew capped at 30s.
- Config via `Cognito:*` in `appsettings.json` + env vars; the M2M client secret in Secrets Manager / Key Vault only.
- Outbound M2M uses `{hostedDomain}/oauth2/token` with the `scope` param + Basic client auth; cache at `expires_in - 60s`.

## What NOT to do

- No `ValidateAudience = true` against a Cognito access token — it has no `aud`; auth will always fail or silently mis-validate.
- No skipping the `token_use` check — it's the only guard against an ID token being replayed as an access token.
- No `audience` param on the M2M token request — Cognito uses `scope`, not `audience`.
- No `HS256` — Cognito issues RS256; reject anything else.
- No reading the raw JWT in business code — use `ClaimsPrincipal`.
- No M2M token request per call — cache and renew before expiry.
- No client secret in `appsettings.json` or the client credentials on a public/SPA client.
- No `[Authorize]` without a policy on an endpoint that needs a specific scope.

## Generation steps

1. Confirm region + pool id (per env), allowed `client_id`s, resource server + scopes, and any outbound M2M targets.
2. Install `Microsoft.AspNetCore.Authentication.JwtBearer`; add `AddJwtBearer` with `Authority = issuer`, `ValidateAudience = false`, and the `OnTokenValidated` `token_use`/`client_id` guard.
3. Add `AddAuthorization` policies — scope-based (`HasScope`) and group-based (`RequireRole`).
4. `UseAuthentication()` + `UseAuthorization()`; guard endpoints with `.RequireAuthorization("…")`.
5. If outbound M2M is needed: add `CognitoM2MTokenService` + a `DelegatingHandler` on the typed client.
6. Smoke: call `/me` with a fresh access token → confirm `scopes`/`groups`; present an ID token → expect 401 (`token_use` guard).

## Handoffs

- Blazor client that obtains these tokens → `auth/cognito-blazor`
- Auth0 equivalent → `backend/dotnet/skills/auth0`
- Java backend equivalent → `backend/java/skills/cognito`
- Concepts → `auth/_shared/oidc-concepts`
- Pattern/persistence scaffolding for the rest of the service → `backend/dotnet/skills/{generator,persistence}`
- Storing secrets → `devops/environment-config` + Secrets Manager / Key Vault
- API contract tests with auth → `qa/dotnet/skills/api-test-author/writer` (seed a test user / M2M client)
