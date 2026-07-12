---
name: auth-cognito-blazor
description: Use when the user asks to set up or modify AWS Cognito (user pools) in Blazor Server or Blazor WebAssembly — `Microsoft.AspNetCore.Authentication.OpenIdConnect` for Server (Authorization Code + PKCE, confidential app client), `Microsoft.AspNetCore.Components.WebAssembly.Authentication` for WASM (public app client), including the Cognito-specific deltas (issuer vs hosted-UI domain, no `audience`/resource-server scopes, non-standard `/logout`, `cognito:groups`, token revocation) and the Blazor Server session lifecycle. Triggers: "add Cognito to Blazor", "Cognito user pool login in Blazor Server/WASM", "call a Cognito-protected API from Blazor", "Cognito logout in .NET", "cognito:groups role policy", "refresh/revoke Cognito tokens in Blazor". Do NOT use for Auth0 (use `auth/auth0-blazor`), plain ASP.NET Core APIs (use `backend/dotnet/skills/cognito`), React SPAs (use `auth/cognito-react`), Java APIs (use `backend/java/skills/cognito`), or Cognito **identity pools**/AWS-credential vending (out of scope — this is user-pool OIDC sign-in).
---

# Auth — AWS Cognito in Blazor (Server & WebAssembly)

Wires an **Amazon Cognito user pool** into Blazor Server and Blazor WebAssembly over OIDC. Server uses Authorization Code + PKCE via OpenIdConnect + cookie auth (a **confidential** app client, with secret); WASM uses the OIDC SPA flow via `Microsoft.AspNetCore.Components.WebAssembly.Authentication` (a **public** app client, no secret). This is the Cognito sibling of [`auth/auth0-blazor`](../auth0-blazor/SKILL.md) — same Blazor mechanics, different IdP wiring.

> **Generic OIDC mental model** (roles, Authorization Code + PKCE, ID vs access token, JWT validation, refresh rotation, Auth0-vs-Cognito comparison) lives in [`auth/_shared/oidc-concepts`](../_shared/oidc-concepts/SKILL.md). This skill covers only the Cognito-specific deltas + the Blazor plumbing.

## Cognito vs Auth0 — the deltas that matter here

| Concern | Auth0 | **Cognito** |
|---|---|---|
| Issuer / metadata | `https://{domain}` | **`https://cognito-idp.{region}.amazonaws.com/{userPoolId}`** — set as **`MetadataAddress`** (`.../.well-known/openid-configuration`) so `iss` matches exactly |
| Hosted-UI domain | same as issuer | **separate**: `https://{domain}.auth.{region}.amazoncognito.com` (or a custom domain) — `/authorize`, `/token`, `/logout`, `/oauth2/revoke` live here (discovery returns them) |
| API authorization | `audience` param → API-scoped access token (opaque without it) | **no `audience`**. Access token is **always a JWT**; authorize your API with a **Resource Server + custom scopes** (`https://api.yourco.com/orders.read`) validated on the `scope` claim. There is **no `aud` claim** — the API validates `iss` + `token_use=access` + `client_id` + `scope` |
| Logout | `/v2/logout?client_id=&returnTo=` | **`/logout?client_id=&logout_uri=`** on the hosted domain — **`end_session_endpoint` is absent from metadata**, so you build the URL by hand; `logout_uri` must be in **Allowed sign-out URLs** |
| Roles | namespaced custom claim | **`cognito:groups`** claim (array, on ID *and* access tokens) → `RoleClaimType = "cognito:groups"` |
| Refresh token | `offline_access` scope | **returned automatically** with the code grant — **do NOT request `offline_access`** (Cognito rejects unknown scopes). Validity is set on the app client (default 30 days) |
| Revocation | `/oauth/revoke` + Management API | **`/oauth2/revoke`** (refresh token; enable "Token revocation" on the app client) + **`AdminUserGlobalSignOut`** (Admin API, IAM creds — revokes *all* of a user's refresh/ID/access tokens) |
| Standard scopes | any | only `openid`, `profile`, `email`, `phone`, `aws.cognito.signin.user.admin`, and your resource-server scopes |

## When to use

- Adding Cognito user-pool sign-in to a Blazor Server or WASM app
- Protecting `<AuthorizeView>` / `[Authorize]`-routed components with Cognito groups or scopes
- Calling a Cognito-protected backend API from Blazor (token attached automatically)
- Getting the Blazor Server session lifecycle right (revalidation, refresh, revoke-on-logout)

## When NOT to use

- Auth0 → [`auth/auth0-blazor`](../auth0-blazor/SKILL.md)
- Plain ASP.NET Core API validating Cognito JWTs → `backend/dotnet/skills/cognito`
- React SPA → `auth/auth0-react`
- Cognito **identity pools** / vending temporary AWS credentials → out of scope (this is user-pool OIDC sign-in only)
- Generic OIDC concepts → [`auth/_shared/oidc-concepts`](../_shared/oidc-concepts/SKILL.md)

## Inputs needed

1. **Blazor hosting model** — Server, WASM, or Interactive Auto
2. **User pool**: region + `userPoolId`; **hosted-UI domain** (or custom domain)
3. **App client(s)**: a **confidential** client (with secret) for Server; a **public** client (no secret) for WASM
4. **Resource server + custom scopes** if the app calls your own API (e.g. `https://api.yourco.com` → `orders.read`, `orders.write`)
5. **Callback + sign-out URLs** to register on the app client (sign-out URLs gate `logout_uri`)
6. **Groups** (`cognito:groups`) or scopes that gate each page/action

## Blazor Server setup

Blazor Server signs the user in server-side, stores the OIDC tokens in the auth cookie, and exposes `AuthenticationStateProvider` to components.

### Packages

```bash
dotnet add package Microsoft.AspNetCore.Authentication.OpenIdConnect
```

### Program.cs

```csharp
using Microsoft.AspNetCore.Authentication.Cookies;
using Microsoft.AspNetCore.Authentication.OpenIdConnect;
using Microsoft.IdentityModel.Tokens;
using System.Net.Http.Headers;

var builder = WebApplication.CreateBuilder(args);
builder.Services.AddRazorComponents().AddInteractiveServerComponents();

var region      = builder.Configuration["Cognito:Region"]!;        // e.g. eu-west-1
var userPoolId  = builder.Configuration["Cognito:UserPoolId"]!;    // e.g. eu-west-1_ABC123
var clientId    = builder.Configuration["Cognito:ClientId"]!;
var clientSecret= builder.Configuration["Cognito:ClientSecret"]!;  // confidential client — Key Vault/Secrets Manager
var hostedDomain= builder.Configuration["Cognito:HostedDomain"]!;  // https://yourco.auth.eu-west-1.amazoncognito.com
var issuer      = $"https://cognito-idp.{region}.amazonaws.com/{userPoolId}";
var apiScope    = builder.Configuration["Cognito:ApiScope"];        // e.g. https://api.yourco.com/orders.read (optional)

builder.Services
    .AddAuthentication(o =>
    {
        o.DefaultScheme          = CookieAuthenticationDefaults.AuthenticationScheme;
        o.DefaultChallengeScheme = OpenIdConnectDefaults.AuthenticationScheme;
    })
    .AddCookie()
    .AddOpenIdConnect(OpenIdConnectDefaults.AuthenticationScheme, o =>
    {
        // Cognito: point at the DISCOVERY doc; issuer must match exactly, so use MetadataAddress (not Authority)
        o.MetadataAddress = $"{issuer}/.well-known/openid-configuration";
        o.ClientId     = clientId;
        o.ClientSecret = clientSecret;                              // confidential app client
        o.ResponseType = "code";
        o.UsePkce      = true;
        o.SaveTokens   = true;                                     // access_token in the cookie (HTTP paths only)
        o.GetClaimsFromUserInfoEndpoint = true;

        o.Scope.Clear();
        o.Scope.Add("openid");
        o.Scope.Add("profile");
        o.Scope.Add("email");
        if (!string.IsNullOrEmpty(apiScope)) o.Scope.Add(apiScope); // resource-server scope — NOT "audience", NOT "offline_access"

        // Cognito has NO end_session_endpoint in metadata — build the /logout URL by hand.
        o.Events.OnRedirectToIdentityProviderForSignOut = ctx =>
        {
            var returnTo = $"{ctx.Request.Scheme}://{ctx.Request.Host}/signout-callback-oidc";
            var logoutUrl = $"{hostedDomain}/logout?client_id={clientId}&logout_uri={Uri.EscapeDataString(returnTo)}";
            ctx.Response.Redirect(logoutUrl);                       // logout_uri MUST be an Allowed sign-out URL
            ctx.HandleResponse();
            return Task.CompletedTask;
        };

        o.TokenValidationParameters = new TokenValidationParameters
        {
            NameClaimType = "cognito:username",
            RoleClaimType = "cognito:groups",                       // Cognito group membership → roles
        };
    });

builder.Services.AddAuthorization(o =>
{
    // Coarse RBAC via groups:
    o.AddPolicy("admins", p => p.RequireRole("Admins"));
    // Fine-grained API authz via resource-server scope on the access token:
    o.AddPolicy("orders:read", p => p.RequireAssertion(c =>
        c.User.FindFirst("scope")?.Value?.Split(' ').Contains("https://api.yourco.com/orders.read") == true));
});

builder.Services.AddCascadingAuthenticationState();

var app = builder.Build();
app.UseStaticFiles();
app.UseRouting();
app.UseAuthentication();
app.UseAuthorization();
app.UseAntiforgery();
app.MapRazorComponents<App>().AddInteractiveServerRenderMode();

app.MapGet("/login",  () => Results.Challenge(new() { RedirectUri = "/" }, [OpenIdConnectDefaults.AuthenticationScheme]));
app.MapGet("/logout", () => Results.SignOut(new() { RedirectUri = "/" },
    [CookieAuthenticationDefaults.AuthenticationScheme, OpenIdConnectDefaults.AuthenticationScheme]));

app.Run();
```

### Calling a backend API

Use the saved `access_token` **on HTTP request paths**; circuit code goes through the session-cached token service (see lifecycle below):

```csharp
public sealed class ApiClient(IHttpClientFactory http, IHttpContextAccessor ctx)
{
    public async Task<T?> GetAsync<T>(string path, CancellationToken ct)
    {
        var token = await ctx.HttpContext!.GetTokenAsync("access_token");   // HTTP path only
        using var client = http.CreateClient("api");
        var req = new HttpRequestMessage(HttpMethod.Get, path);
        req.Headers.Authorization = new AuthenticationHeaderValue("Bearer", token);
        var res = await client.SendAsync(req, ct);
        res.EnsureSuccessStatusCode();
        return await res.Content.ReadFromJsonAsync<T>(cancellationToken: ct);
    }
}

builder.Services.AddHttpContextAccessor();
builder.Services.AddHttpClient("api", c => c.BaseAddress = new Uri(builder.Configuration["Api:BaseUrl"]!));
builder.Services.AddScoped<ApiClient>();
```

The API validates the token by `iss` (= the user-pool issuer), `token_use == "access"`, `client_id`, and the required `scope` — **not** an `aud` claim (Cognito access tokens don't carry one).

### Authorization in components

```razor
@page "/orders"
@attribute [Authorize(Policy = "orders:read")]

<AuthorizeView Roles="Admins">
    <Authorized><button @onclick="CreateOrder">New order</button></Authorized>
    <NotAuthorized><span>You don't have permission to create orders.</span></NotAuthorized>
</AuthorizeView>
```

## Blazor Server session lifecycle

**Identical in shape to [`auth0-blazor`](../auth0-blazor/SKILL.md#blazor-server-session-lifecycle)** — read it for the full rationale. A circuit captures auth state **once** and has **no live `HttpContext`**, so without the pieces below a user stays "logged in" on an open tab after logout/expiry/revocation. The Cognito-specific bindings:

- **Revalidating provider + session registry.** Derive from `RevalidatingServerAuthenticationStateProvider`; validate on a 1–5 min interval against a **server-side session registry** (`IDistributedCache`/Redis on scale-out), not the cookie. Cognito has no stable per-session `sid` claim, so **stamp your own GUID session marker in `OnTokenValidated`** and record it in the registry; revalidation asks "is this marker still active?".
- **Refresh — the dual flow.** The code grant returns a refresh token automatically (no `offline_access`). (1) **HTTP path:** `CookieAuthenticationEvents.OnValidatePrincipal` checks `expires_at`, redeems the refresh token at `{hostedDomain}/oauth2/token` near expiry, and rewrites the ticket (`ShouldRenew = true`). (2) **Circuit path:** circuits can't rewrite the cookie — route token access through a scoped token service backed by a **server-side cache** keyed by the session marker; refresh against `/oauth2/token` and update the cache. Never `HttpContext.GetTokenAsync` from circuit code.
- **Logout revokes, not just redirects.** In addition to local sign-out + the Cognito `/logout` redirect, **revoke the refresh token** at `{hostedDomain}/oauth2/revoke` (enable "Token revocation" on the app client) and **evict the session-registry entry**.
- **Password reset / kill-switch.** Call **`AdminUserGlobalSignOut`** (Cognito Admin API, IAM creds) to revoke *all* of the user's refresh/ID/access tokens, and evict **all** their session-registry entries so every live circuit signs out on next revalidation. Caveat: an already-issued access-token JWT stays cryptographically valid until it expires unless your API checks revocation — so keep **access-token lifetime short** (5–15 min) and lean on the registry + short expiry, exactly as the checklist verifies.
- **Hosted login on a custom domain.** Prefer the Cognito Hosted UI on a **custom domain** (`auth.yourco.com`) over a native in-app credential form — the app never touches credentials and the redirect stays first-party.

### Lifecycle test checklist (peer: `qa-ui-dotnet`)

- [ ] **Expiry mid-task:** access token expires while a circuit is active → token service refreshes transparently; no logout flash.
- [ ] **Cross-tab logout:** log out in tab A → tab B's circuit fails revalidation within the interval and lands signed-out.
- [ ] **Replayed cookie:** replay a pre-logout cookie → rejected (registry entry gone).
- [ ] **Revoked refresh token / global sign-out:** `AdminUserGlobalSignOut` → next refresh fails → session evicted, no retry loop.
- [ ] **Password reset:** reset password → all the user's live circuits sign out within the interval.

## Blazor WASM setup

WASM is a SPA using a **public** app client (no secret) + PKCE.

### Packages

```bash
dotnet add package Microsoft.AspNetCore.Components.WebAssembly.Authentication
```

### Program.cs (WASM)

```csharp
var builder = WebAssemblyHostBuilder.CreateDefault(args);
builder.RootComponents.Add<App>("#app");

builder.Services.AddOidcAuthentication(options =>
{
    builder.Configuration.Bind("Cognito", options.ProviderOptions);
    options.ProviderOptions.ResponseType = "code";                 // Authorization Code + PKCE
    options.UserOptions.RoleClaim  = "cognito:groups";
    options.UserOptions.NameClaim  = "cognito:username";
    // No client secret, no "audience", no "offline_access".
});

await builder.Build().RunAsync();
```

### wwwroot/appsettings.json (public — ships to the browser)

```json
{
  "Cognito": {
    "Authority": "https://cognito-idp.eu-west-1.amazonaws.com/eu-west-1_ABC123",
    "MetadataUrl": "https://cognito-idp.eu-west-1.amazonaws.com/eu-west-1_ABC123/.well-known/openid-configuration",
    "ClientId": "<public-app-client-id>",
    "RedirectUri": "https://localhost:5001/authentication/login-callback",
    "PostLogoutRedirectUri": "https://localhost:5001/authentication/logout-callback",
    "ResponseType": "code",
    "DefaultScopes": [ "openid", "profile", "email", "https://api.yourco.com/orders.read" ]
  }
}
```

Conventional auth page — `Pages/Authentication.razor`:

```razor
@page "/authentication/{action}"
@using Microsoft.AspNetCore.Components.WebAssembly.Authentication
<RemoteAuthenticatorView Action="@Action" />
@code { [Parameter] public string? Action { get; set; } }
```

> **WASM logout gotcha:** because Cognito omits `end_session_endpoint` from its metadata, `RemoteAuthenticatorView`'s standard logout won't redirect to the Cognito Hosted UI on its own. After the local sign-out completes, navigate the browser to the Cognito `/logout?client_id={clientId}&logout_uri={postLogoutUri}` URL yourself (a small handler on the logged-out callback) so the Cognito session cookie is also cleared. `logout_uri` must be an Allowed sign-out URL.

### Calling the API from WASM

The framework's `AuthorizationMessageHandler` injects the access token — never build the header by hand:

```csharp
builder.Services.AddTransient<CognitoAuthorizationMessageHandler>();
builder.Services.AddHttpClient("api", c => c.BaseAddress = new Uri("https://api.yourco.com"))
    .AddHttpMessageHandler<CognitoAuthorizationMessageHandler>();

public class CognitoAuthorizationMessageHandler : AuthorizationMessageHandler
{
    public CognitoAuthorizationMessageHandler(IAccessTokenProvider provider, NavigationManager nav)
        : base(provider, nav)
    {
        ConfigureHandler(
            authorizedUrls: ["https://api.yourco.com"],
            scopes: ["https://api.yourco.com/orders.read"]);       // resource-server scope
    }
}
```

This handler is what the frontend [`data-access`](../../frontend/blazor/skills/data-access/SKILL.md) and [`realtime`](../../frontend/blazor/skills/realtime/SKILL.md) skills consume as their **IdP-neutral** token source — they don't care that it's Cognito rather than Auth0.

## Rules

### Both modes
- Authorization Code + PKCE only; never Implicit.
- Use **`MetadataAddress`/`MetadataUrl`** (the discovery doc) so `iss` validation matches the user-pool issuer exactly.
- **No `audience` param, no `offline_access` scope** — authorize your API with **resource-server custom scopes** on the `scope` claim; the refresh token comes automatically.
- Roles from **`cognito:groups`**; permissions enforced via `[Authorize(Policy=…)]` / `<AuthorizeView>`, never string comparison in components.
- The Cognito **`/logout`** URL is built by hand (no `end_session_endpoint`); `logout_uri` must be an Allowed sign-out URL.
- Access-token lifetime short (5–15 min) — Cognito can't invalidate an already-issued JWT before expiry.

### Blazor Server specific
- Confidential app client **with secret**, stored in Key Vault / AWS Secrets Manager / env vars — never in `appsettings.json`.
- `o.SaveTokens = true`; `HttpContext.GetTokenAsync("access_token")` on **HTTP paths only**; circuit code uses the session-cached token service.
- `RevalidatingServerAuthenticationStateProvider` + server-side session registry keyed by a self-stamped GUID marker.
- Logout revokes the refresh token (`/oauth2/revoke`) + evicts the registry; password reset calls `AdminUserGlobalSignOut` + evicts all the user's markers.
- Hosted UI on a custom domain — never a native credential form.

### Blazor WASM specific
- **Public** app client, no secret; `wwwroot/appsettings.json` is public — only public-safe values.
- `AuthorizationMessageHandler` per backend host.
- Handle the Cognito logout redirect explicitly (the `end_session_endpoint` gap).

## What NOT to do

- No `audience` parameter (Auth0-ism — Cognito ignores it; the access token is already a JWT).
- No `offline_access` scope — Cognito rejects it; the refresh token is returned automatically.
- No `Authority` where the discovery `iss` won't match — use `MetadataAddress` to avoid issuer-mismatch failures.
- No relying on a standard `end_session_endpoint` — build the Cognito `/logout` URL by hand (both modes).
- No client secret in WASM (`wwwroot/appsettings.json` ships to the browser).
- No reading the ID token to call the API — use the access token (Server: `GetTokenAsync`; WASM: handler).
- No `HttpContext.GetTokenAsync` from circuit code — no live `HttpContext`; use the session-cached token service.
- No trusting once-captured circuit auth state for the circuit's whole life — revalidate against the registry.
- No treating `AdminUserGlobalSignOut` as instant JWT invalidation — pair it with short access-token expiry + the registry.
- No un-scoped API access — define a resource server; validate `token_use`/`scope`, not `aud`.
- No mixing user pools across environments.

## Generation steps

1. Confirm hosting model; region + `userPoolId`; hosted-UI (custom) domain; app client(s) — confidential for Server, public for WASM; resource server + scopes if calling your API; callback + **sign-out** URLs; gating groups/scopes.
2. In Cognito: create the app client(s), enable Hosted UI + the OIDC flows, register callback/sign-out URLs, enable **Token revocation** (Server), define the resource server + custom scopes.
3. **Server:** install `Microsoft.AspNetCore.Authentication.OpenIdConnect`; wire the `Program.cs` template (`MetadataAddress`, manual `/logout`, `cognito:groups` role claim); add `/login` + `/logout` endpoints; wire the session-lifecycle pieces.
4. **WASM:** install `Microsoft.AspNetCore.Components.WebAssembly.Authentication`; configure via `wwwroot/appsettings.json`; add `Authentication.razor`; handle the Cognito logout redirect.
5. Wire the API `HttpClient` (Server: typed client + token from context/token service; WASM: `AuthorizationMessageHandler`).
6. Add `[Authorize(Policy=…)]` / `<AuthorizeView>` where access is gated.
7. Smoke: visit a protected page → Cognito Hosted UI → sign in → land back → call the API → sign out → confirm the Cognito session cookie is cleared.

## Handoffs

- Generic OIDC concepts + Auth0-vs-Cognito comparison → [`auth/_shared/oidc-concepts`](../_shared/oidc-concepts/SKILL.md)
- Auth0 equivalent → [`auth/auth0-blazor`](../auth0-blazor/SKILL.md) (session-lifecycle rationale in full)
- Backend API validating Cognito JWTs → `backend/dotnet/skills/cognito` · `backend/java/skills/cognito`
- Blazor data/realtime consuming the token → [`frontend/blazor/skills/data-access`](../../frontend/blazor/skills/data-access/SKILL.md), [`realtime`](../../frontend/blazor/skills/realtime/SKILL.md) (IdP-neutral)
- Storing the client secret → `devops/environment-config` + AWS Secrets Manager / Key Vault
- E2E auth with Playwright → `qa/dotnet/skills/ui-test-author/playwright`
