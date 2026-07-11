---
name: auth-auth0-blazor
description: Use when the user asks to set up or modify Auth0 in Blazor Server or Blazor WebAssembly — `Microsoft.AspNetCore.Authentication.OpenIdConnect` for Server (Authorization Code + PKCE), `Microsoft.AspNetCore.Components.WebAssembly.Authentication` for WASM — including Blazor Server session lifecycle (revalidating auth-state provider, session registry, refresh tokens on circuits, logout/reset revocation). Triggers: "add Auth0 to Blazor Server", "Blazor WASM Auth0 login", "protect a Blazor route", "call a protected API from Blazor", "user stays logged in after logout/expiry", "refresh tokens in Blazor Server". Do NOT use for plain ASP.NET Core APIs (use `auth/auth0-dotnet`), React (use `auth/auth0-react`), or concepts (use `auth/_shared/auth0-concepts`).
---

# Auth — Auth0 in Blazor (Server & WebAssembly)

Wires Auth0 into Blazor Server and Blazor WebAssembly. Server uses Authorization Code + PKCE via OpenIdConnect + cookie auth; WASM uses the OIDC SPA flow via `Microsoft.AspNetCore.Components.WebAssembly.Authentication`. Both target .NET 8.

## Stack

- **.NET 8** + Blazor (Server, WASM, or interactive Auto)
- **Blazor Server**: `Microsoft.AspNetCore.Authentication.OpenIdConnect` + cookie auth (acts like a Regular Web App in Auth0)
- **Blazor WASM**: `Microsoft.AspNetCore.Components.WebAssembly.Authentication` (acts like a SPA in Auth0)
- Backend Web API (if separate) uses `auth/auth0-dotnet`

## When to use

- Adding Auth0 sign-in to a Blazor Server app
- Adding Auth0 sign-in to a Blazor WASM app
- Protecting `<AuthorizeView>` / `[Authorize]`-routed components
- Calling a protected backend API from Blazor (token attached automatically)

## When NOT to use

- Plain ASP.NET Core API → `auth/auth0-dotnet`
- React SPA → `auth/auth0-react`
- Java backend → `auth/auth0-java`
- Concepts → `auth/_shared/auth0-concepts`

## Inputs needed

1. **Blazor hosting model** (Server, WASM, or Interactive Auto in .NET 8)
2. **Auth0 tenant domain** + **Application** (Regular Web App for Server, SPA for WASM) + **API audience**
3. **Required permissions** per page / endpoint
4. **Backend API** the Blazor app calls (its audience + scopes)
5. **Logout flow** preference — local sign-out only or full Auth0 SSO sign-out

## Blazor Server setup

Blazor Server signs the user in server-side, stores the OIDC tokens in the authentication cookie, and exposes `AuthenticationStateProvider` to components.

### Packages

```bash
dotnet add package Microsoft.AspNetCore.Authentication.OpenIdConnect
```

### Program.cs

```csharp
using Microsoft.AspNetCore.Authentication.Cookies;
using Microsoft.AspNetCore.Authentication.OpenIdConnect;
using Microsoft.IdentityModel.Tokens;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddRazorComponents().AddInteractiveServerComponents();

var domain   = builder.Configuration["Auth0:Domain"]!;
var clientId = builder.Configuration["Auth0:ClientId"]!;
var secret   = builder.Configuration["Auth0:ClientSecret"]!;
var audience = builder.Configuration["Auth0:Audience"]!;

builder.Services
    .AddAuthentication(options =>
    {
        options.DefaultScheme          = CookieAuthenticationDefaults.AuthenticationScheme;
        options.DefaultChallengeScheme = OpenIdConnectDefaults.AuthenticationScheme;
    })
    .AddCookie()
    .AddOpenIdConnect(OpenIdConnectDefaults.AuthenticationScheme, o =>
    {
        o.Authority    = $"https://{domain}";
        o.ClientId     = clientId;
        o.ClientSecret = secret;
        o.ResponseType = "code";
        o.UsePkce      = true;
        o.SaveTokens   = true;                                  // access_token saved in the cookie
        o.GetClaimsFromUserInfoEndpoint = true;

        o.Scope.Clear();
        o.Scope.Add("openid");
        o.Scope.Add("profile");
        o.Scope.Add("email");
        o.Scope.Add("offline_access");

        // Audience is Auth0-specific — required to get an access token usable by your API
        o.Events.OnRedirectToIdentityProvider = ctx =>
        {
            ctx.ProtocolMessage.SetParameter("audience", audience);
            return Task.CompletedTask;
        };

        // Auth0 logout endpoint (RP-initiated logout takes returnTo)
        o.Events.OnRedirectToIdentityProviderForSignOut = ctx =>
        {
            var logoutUri = $"https://{domain}/v2/logout?client_id={clientId}&returnTo={Uri.EscapeDataString(ctx.Request.Scheme + "://" + ctx.Request.Host)}";
            ctx.Response.Redirect(logoutUri);
            ctx.HandleResponse();
            return Task.CompletedTask;
        };

        o.TokenValidationParameters = new TokenValidationParameters
        {
            NameClaimType = "name",
            RoleClaimType = "https://yourco.com/roles",         // if you push roles as a custom claim
        };
    });

builder.Services.AddAuthorization(o =>
{
    o.AddPolicy("orders:read",  p => p.RequireAssertion(c =>
        c.User.Claims.Any(x => x.Type == "permissions" && x.Value == "orders:read")));
});

builder.Services.AddCascadingAuthenticationState();

var app = builder.Build();
app.UseStaticFiles();
app.UseRouting();
app.UseAuthentication();
app.UseAuthorization();
app.UseAntiforgery();
app.MapRazorComponents<App>().AddInteractiveServerRenderMode();

app.MapGet("/login",  () => Results.Challenge(new() { RedirectUri = "/" }, new[] { OpenIdConnectDefaults.AuthenticationScheme }));
app.MapGet("/logout", () => Results.SignOut(new() { RedirectUri = "/" },
    new[] { CookieAuthenticationDefaults.AuthenticationScheme, OpenIdConnectDefaults.AuthenticationScheme }));

app.Run();
```

### Calling a backend API

Inject `IHttpClientFactory` + use the saved `access_token`:

```csharp
public sealed class ApiClient(IHttpClientFactory http, IHttpContextAccessor ctx)
{
    public async Task<T?> GetAsync<T>(string path, CancellationToken ct)
    {
        var token = await ctx.HttpContext!.GetTokenAsync("access_token");
        using var client = http.CreateClient("api");
        var req = new HttpRequestMessage(HttpMethod.Get, path);
        req.Headers.Authorization = new("Bearer", token);
        var res = await client.SendAsync(req, ct);
        res.EnsureSuccessStatusCode();
        return await res.Content.ReadFromJsonAsync<T>(cancellationToken: ct);
    }
}

builder.Services.AddHttpContextAccessor();
builder.Services.AddHttpClient("api", c => c.BaseAddress = new Uri(cfg["Api:BaseUrl"]!));
builder.Services.AddScoped<ApiClient>();
```

### Authorization in components

```razor
@page "/orders"
@attribute [Authorize(Policy = "orders:read")]

<AuthorizeView Policy="orders:write">
    <Authorized>
        <button @onclick="CreateOrder">New order</button>
    </Authorized>
    <NotAuthorized>
        <span>You don't have permission to create orders.</span>
    </NotAuthorized>
</AuthorizeView>
```

## Blazor Server session lifecycle

Blazor Server circuits capture the authentication state **once**, at circuit creation, and then have **no live `HttpContext`** — the cookie is never re-read while the circuit lives. Without the pieces below, a user stays "logged in" on an open tab long after their session was revoked, their password reset, or their token expired.

### Revalidating auth-state provider + session registry

Derive from `RevalidatingServerAuthenticationStateProvider` and validate on an interval against a **server-side source of truth** — not the cookie (the circuit can't see cookie changes):

```csharp
public sealed class SessionRevalidatingAuthenticationStateProvider(
    ILoggerFactory loggerFactory,
    ISessionRegistry sessions)
    : RevalidatingServerAuthenticationStateProvider(loggerFactory)
{
    protected override TimeSpan RevalidationInterval => TimeSpan.FromMinutes(5);

    protected override Task<bool> ValidateAuthenticationStateAsync(
        AuthenticationState authenticationState, CancellationToken ct)
    {
        var sessionId = authenticationState.User.FindFirst("sid")?.Value;
        return sessions.IsActiveAsync(sessionId, ct);
    }
}

builder.Services.AddScoped<AuthenticationStateProvider, SessionRevalidatingAuthenticationStateProvider>();
```

The registry is keyed by a **sign-in-stamped session marker**: on `OnTokenValidated`, stamp a session id (Auth0's `sid` claim, or your own GUID claim) and record it in the registry (`IDistributedCache`/Redis on scale-out, `IMemoryCache` single-node). Revalidation asks "is this session still active?" — logout, password reset, and admin kill-switch all evict entries, and every live circuit for that user fails its next revalidation and is signed out.

### Refresh tokens — the dual flow

`offline_access` gives you a refresh token; Blazor Server needs **two** refresh paths because tokens are consumed from two different lifetimes:

1. **HTTP requests (cookie path):** in `CookieAuthenticationEvents.OnValidatePrincipal`, check the saved `expires_at`; if the access token is near expiry, redeem the refresh token at Auth0's `/oauth/token`, then **rewrite the ticket** (`context.ShouldRenew = true` after replacing the stored tokens). This keeps the cookie's embedded tokens fresh for classic HTTP requests.
2. **Circuits (interactive path):** a circuit outlives requests and **cannot rewrite the cookie**. Route all token access through a scoped token service backed by a **server-side cache** keyed by the session marker: it returns the cached access token, refreshes at Auth0 when near expiry, and updates the cache — never `HttpContext.GetTokenAsync` from circuit code (there is no live context). The `ApiClient` above should take its token from this service, not from `IHttpContextAccessor`, in interactive render modes.

Refresh-token rotation should be ON in the Auth0 application; store only the latest rotated token in the server-side cache.

### Logout & password reset revoke, not just redirect

- **Logout:** in addition to local sign-out + Auth0 `/v2/logout`, **revoke the refresh token** (`/oauth/revoke`) and **evict the session registry entry** — otherwise the tokens cached server-side keep working and other live circuits stay signed in.
- **Password reset / compromise:** evict **all** of the target user's session-registry entries so every live circuit is signed out on next revalidation; revoke their refresh tokens (Auth0 Management API `DELETE /api/v2/users/{id}/sessions` + grant revocation) so nothing silently re-mints.

### Hosted login on a custom domain

Use Auth0's hosted Universal Login on a **custom domain** (`auth.yourco.com`) rather than native in-app credential forms — the app never touches credentials, and the custom domain keeps the redirect first-party (cookies, password managers, user trust).

### Lifecycle test checklist

Verify each of these end-to-end (peer: `qa-ui-dotnet` for automation):

- [ ] **Expiry mid-task:** let the access token expire while a circuit is active → the token service refreshes transparently; API calls keep working; no logout flash.
- [ ] **Cross-tab logout:** log out in tab A → tab B's circuit fails revalidation within the interval and lands on the signed-out UI.
- [ ] **Replayed cookie:** copy the auth cookie, log out, replay the cookie → rejected (session registry entry is gone; `OnValidatePrincipal` rejects).
- [ ] **Revoked refresh token:** revoke at the IdP → next refresh attempt fails → session evicted, user signed out, no infinite retry loop.
- [ ] **Password reset:** reset user's password → all their live circuits are signed out within the revalidation interval.

## Blazor WASM setup

WASM is a SPA. Pattern matches `auth/auth0-react` conceptually but uses Microsoft's WASM auth library.

### Packages

```bash
dotnet add package Microsoft.AspNetCore.Components.WebAssembly.Authentication
```

### Program.cs (WASM)

```csharp
var builder = WebAssemblyHostBuilder.CreateDefault(args);
builder.RootComponents.Add<App>("#app");
builder.Services.AddScoped(_ => new HttpClient { BaseAddress = new Uri(builder.HostEnvironment.BaseAddress) });

builder.Services.AddOidcAuthentication(options =>
{
    builder.Configuration.Bind("Auth0", options.ProviderOptions);
    options.ProviderOptions.ResponseType = "code";
    options.ProviderOptions.AdditionalProviderParameters.Add("audience", builder.Configuration["Auth0:Audience"]!);
    options.UserOptions.RoleClaim = "https://yourco.com/roles";
});

await builder.Build().RunAsync();
```

### wwwroot/appsettings.json

```json
{
  "Auth0": {
    "Authority": "https://yourco-dev.eu.auth0.com",
    "ClientId":  "<spa-client-id>",
    "RedirectUri": "https://localhost:5001/authentication/login-callback",
    "PostLogoutRedirectUri": "https://localhost:5001/authentication/logout-callback",
    "DefaultScopes": [ "openid", "profile", "email" ],
    "Audience": "https://api.yourco.com"
  }
}
```

The Authentication page is conventional — `Pages/Authentication.razor`:

```razor
@page "/authentication/{action}"
@using Microsoft.AspNetCore.Components.WebAssembly.Authentication
<RemoteAuthenticatorView Action="@Action" />
@code { [Parameter] public string? Action { get; set; } }
```

### Calling the API from WASM

The framework provides an `AuthorizationMessageHandler` that injects the access token:

```csharp
builder.Services.AddTransient<CustomAuthorizationMessageHandler>();
builder.Services.AddHttpClient("api", c => c.BaseAddress = new Uri("https://api.yourco.com"))
    .AddHttpMessageHandler<CustomAuthorizationMessageHandler>();

public class CustomAuthorizationMessageHandler : AuthorizationMessageHandler
{
    public CustomAuthorizationMessageHandler(IAccessTokenProvider provider, NavigationManager nav)
        : base(provider, nav)
    {
        ConfigureHandler(
            authorizedUrls: new[] { "https://api.yourco.com" },
            scopes: new[] { "openid", "profile", "email" });
    }
}
```

## Rules

### Both modes
- Authorization Code + PKCE only
- `audience` parameter must ride the `/authorize` request — otherwise the access token is opaque and your API can't use it
- Permissions enforced via `[Authorize(Policy = "...")]` and `<AuthorizeView Policy="...">` — never string-comparison inside components
- Auth0 logout (`/v2/logout`) called in addition to local sign-out so SSO clears
- Custom claims read via full namespaced URI

### Blazor Server specific
- `o.SaveTokens = true` so the access token is available via `HttpContext.GetTokenAsync("access_token")` — **HTTP request paths only**; circuit code goes through the session-cached token service
- `IHttpContextAccessor` registered; outbound HTTP attaches the access token via a typed client or delegating handler
- ClientSecret in Key Vault / env vars (Blazor Server is a *Regular Web App* in Auth0; it has a secret)
- A `RevalidatingServerAuthenticationStateProvider` validating against the session registry — circuits never trust the once-captured auth state for their whole lifetime
- Logout revokes the refresh token at the IdP and evicts the session registry; password reset evicts all of the user's live sessions
- Hosted Universal Login on a custom domain — never native in-app credential forms

### Blazor WASM specific
- No client secret (SPA)
- `AuthorizationMessageHandler` per backend host — never construct headers by hand in components
- `wwwroot/appsettings.json` is **public** (shipped to the browser); only put public-safe values there

## What NOT to do

- No omitting `audience` — silently produces opaque tokens
- No storing access tokens in component state or `localStorage` manually — let the framework cache
- No `Implicit Flow` (`response_type=token`) — code + PKCE only
- No reading the ID Token to call the API — use the access token (Server: `GetTokenAsync("access_token")`; WASM: handler)
- No `[AllowAnonymous]` on a page that touches user data
- No client secret in WASM (`wwwroot/appsettings.json` ships to the browser)
- No bypassing Auth0 logout — local sign-out alone leaves the SSO session alive in Auth0
- No `HttpContext.GetTokenAsync` from circuit (interactive) code — circuits have no live `HttpContext`; use the session-cached token service
- No relying on cookie expiry alone to end a Blazor Server session — circuits outlive the cookie; revalidate against the session registry
- No un-namespaced custom claims
- No mixing tenants across environments

## Generation steps

1. Confirm hosting model (Server / WASM / Auto), tenant domain (per env), client_id (and secret for Server), API audience, callback URLs, permissions.
2. Register URLs in the matching Auth0 Application (Regular Web App for Server, SPA for WASM).
3. **Server**: install `Microsoft.AspNetCore.Authentication.OpenIdConnect`; wire the `Program.cs` template; add `/login` + `/logout` endpoints.
4. **WASM**: install `Microsoft.AspNetCore.Components.WebAssembly.Authentication`; configure via `wwwroot/appsettings.json`; add the `Authentication.razor` page.
5. Wire the API HttpClient (Server: typed client with token from context; WASM: `AuthorizationMessageHandler`).
6. Add `[Authorize(Policy = "...")]` / `<AuthorizeView>` where access is gated.
7. Smoke flow: visit a protected page → redirect to Auth0 → sign in → land back, call the API, sign out, verify Auth0 SSO session cleared.

## Handoffs

- Concepts → `auth/_shared/auth0-concepts`
- Backend API validation → `auth/auth0-dotnet`
- React equivalent → `auth/auth0-react`
- Java backend → `auth/auth0-java`
- Storing secrets → `devops/environment-config` (when authored) + Key Vault
- E2E auth with Playwright → `qa/ui-test-author/playwright`
