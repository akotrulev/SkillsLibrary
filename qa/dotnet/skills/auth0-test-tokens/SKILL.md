---
name: qa-auth0-test-tokens-dotnet
description: Use when the user asks to obtain Auth0 access tokens *for automated tests* in .NET (NUnit) — programmatic token acquisition so suites authenticate WITHOUT driving the interactive login UI. Covers the three grants a QA org uses: Client Credentials (M2M) for API-test suites hitting protected endpoints, Resource Owner Password Grant (ROPG / `password-realm`) to mint a token *as a specific test user*, and the Device Authorization Flow for CLI/input-constrained cases — plus token caching for the token's `expires_in` lifetime and stashing it into the API client (`Authorization: Bearer`) or seeding Playwright .NET `StorageState`. Built on `Auth0.AuthenticationApi` (`AuthenticationApiClient.GetTokenAsync` with `ClientCredentialsTokenRequest` / `ResourceOwnerTokenRequest` / `DeviceCodeTokenRequest`) or bare `HttpClient` to `/oauth/token`. Triggers: "get an Auth0 M2M token for my .NET API tests", "log in a test user without the UI in C#", "mint an Auth0 token for a test user", "cache the Auth0 token across the NUnit suite", "seed Playwright .NET auth state from an Auth0 token". Do NOT use for app-side login flows / wiring Auth0 into an ASP.NET app (use `auth/auth0-dotnet` / `auth/auth0-blazor`), for the Auth0 concept model (use `auth/_shared/auth0-concepts`), or for the TypeScript / JVM stacks (`qa/{typescript,java}/skills/auth0-test-tokens`).
---

# QA — Auth0 Test Tokens (.NET / NUnit)

Scaffolds **programmatic Auth0 token acquisition for automated tests** in .NET. The goal is narrow: get a valid `access_token` into a test's API client or browser session **without driving the interactive `/authorize` login UI** on every run. This is the *test-token slice* — it complements, and does not replace, the app-side login skills in `auth/auth0-{dotnet,blazor}` (which implement the real user-facing flows).

Three grants cover what a QA org actually needs:

- **Client Credentials (M2M)** — a service-to-service token with no user context. The default for API-test suites that hit protected endpoints. `grant_type=client_credentials` + `audience` + `client_id`/`client_secret`.
- **Resource Owner Password Grant (ROPG)** — mint a token *as a specific test user* (username + password) with no UI. **Test-only, and must be explicitly enabled on the tenant** (see the security caveat). This is the one that unblocks UI auth-state seeding.
- **Device Authorization Flow** — for input-constrained / CLI scenarios: get a `device_code`, then poll `/oauth/token` until the user authorizes. Lowest priority, but included for completeness.

Two cross-cutting rules shape every example:

- **Cache the token for its `expires_in` lifetime.** Fetch once per fixture/suite, reuse until ~60s before expiry, then re-fetch. **Never** fetch a token per test. Never sleep-poll.
- **Secrets only via env, read lazily.** `client_secret`, test-user passwords, `AUTH0_DOMAIN`, `audience` come from env vars (CLAUDE.md hard rule). Never logged, never committed, never read in a static initializer.

## Stack

- .NET 8, C# (nullable reference types enabled)
- **`Auth0.AuthenticationApi`** NuGet — `AuthenticationApiClient` + `GetTokenAsync` overloads; falls back to `HttpClient` + `System.Text.Json` for device-code polling
- **NUnit** as the runner
- **Playwright .NET** (`Microsoft.Playwright`) for the UI auth-state seeding example
- Token plumbing under `Tests/Support/Auth/`; secrets via **env vars only**

## When to use

- An API-test suite (`qa/dotnet/skills/api-test-author/generator`) needs a `Bearer` token to call protected endpoints → **M2M**
- A UI suite needs to skip the login form by seeding an authenticated browser session → **ROPG** → `StorageState`
- You need a token *as a particular seeded test user* (with that user's roles/permissions) → **ROPG**
- A CLI/headless tool or a device without a browser needs to authenticate → **device-code**
- You're re-fetching a token on every test and want to cache it correctly

## When NOT to use

- Wiring Auth0 into the **application under test** (auth middleware, JWT validation, login redirect) → `auth/auth0-dotnet` / `auth/auth0-blazor`
- Understanding the Auth0 entity/flow model conceptually → `auth/_shared/auth0-concepts`
- TypeScript or JVM test suites → `qa/{typescript,java}/skills/auth0-test-tokens`

## Decision matrix — which grant for which test

| | **Client Credentials (M2M)** | **ROPG (`password-realm`)** | **Device Authorization** |
|---|---|---|---|
| User context? | **None** — token represents a *service* | **A specific test user** (their roles/perms) | A specific user (interactive consent once) |
| Serves which test | API tests against protected endpoints | UI auth-state seeding; per-user API tests | CLI / input-constrained clients |
| `GetTokenAsync` request | `ClientCredentialsTokenRequest` | `ResourceOwnerTokenRequest` | `DeviceCodeTokenRequest` (poll) |
| `grant_type` (inferred) | `client_credentials` | `password` / `password-realm` (when `Realm` set) | `urn:ietf:params:oauth:grant-type:device_code` |
| Credentials | `ClientId` + `ClientSecret` | app + **username + password** (+ `Realm`) | `ClientId` (public) |
| Tenant config | M2M app authorized for the API | **ROPG grant enabled** + a DB `Realm` | Device Code grant enabled; "Device" app |
| Security caveat | Standard; keep the secret in env | **Test-only — never production** | Approval step can't be fully headless |
| Consumer | `qa/dotnet/skills/api-test-author/generator` | `qa/dotnet/skills/ui-test-author/playwright` `StorageState` | rarely in CI; tooling |

**Default to M2M** for API suites. Reach for **ROPG** only when the test genuinely needs *this user's* identity. Use **device-code** only for the niche input-constrained case.

## Inputs needed

Ask at most 2–3; infer the rest from the test project and existing fixtures.

1. Which grant(s)? (M2M for API tests / ROPG for a test user / device-code) — default M2M.
2. The API **audience** identifier and the **tenant domain** — and for ROPG, the test-user credentials + the connection **realm** (e.g. `Username-Password-Authentication`).
3. Where do the secrets come from in this environment (CI secret store, user-secrets, env)? Confirm they are **not** committed.

## Auth0 SDK surface (cheat-sheet — `Auth0.AuthenticationApi`)

| Call | Purpose |
|---|---|
| `new AuthenticationApiClient(new Uri($"https://{domain}/"))` | The auth client. Stateless; one instance is fine to share. |
| `await client.GetTokenAsync(new ClientCredentialsTokenRequest { ... })` | **M2M** token. Returns `AccessTokenResponse` (`AccessToken`, `ExpiresIn`, `TokenType`). |
| `await client.GetTokenAsync(new ResourceOwnerTokenRequest { ... })` | **ROPG**. Set `Realm` → grant becomes `password-realm`; omit `Realm` → plain `password`. |
| `await client.GetTokenAsync(new DeviceCodeTokenRequest { ... })` | **Device-code** exchange — poll while the user approves. |
| `await client.StartDeviceFlowAsync(new DeviceCodeRequest { ... })` | Start the device flow → `device_code`, `user_code`, `verification_uri_complete`, `interval`, `expires_in`. |
| `AccessTokenResponse { AccessToken, ExpiresIn, TokenType, Scope, RefreshToken }` | The shape every grant returns. `grant_type` is inferred from the request type. |

`ExpiresIn` is in seconds. For device-code, the SDK throws an `ErrorApiException` whose payload carries `authorization_pending` / `slow_down` while the user hasn't approved — catch and keep polling at the server-dictated `Interval`.

## Templates

### Config — `Tests/Support/Auth/Auth0Config.cs`

Non-secret config (domain, audience, realm) can have fallbacks; **secrets are read lazily** through methods so unrelated tests don't require them. No static initializer touches a secret.

```csharp
namespace Tests.Support.Auth;

public static class Auth0Config
{
    private static string Required(string name) =>
        Environment.GetEnvironmentVariable(name)
        ?? throw new InvalidOperationException($"Missing required env var {name} (Auth0 test-token config).");

    // Non-secret — safe defaults; importing this fetches no token.
    public static string Domain => Environment.GetEnvironmentVariable("AUTH0_DOMAIN") ?? "yourco-dev.eu.auth0.com";
    public static string Audience => Environment.GetEnvironmentVariable("AUTH0_AUDIENCE") ?? "https://api.flexinvest.test";
    public static string Realm => Environment.GetEnvironmentVariable("AUTH0_REALM") ?? "Username-Password-Authentication";

    // Secrets — read lazily, only when a token is actually fetched. Never logged, never committed.
    public static string M2MClientId() => Required("AUTH0_M2M_CLIENT_ID");
    public static string M2MClientSecret() => Required("AUTH0_M2M_CLIENT_SECRET");
    public static string RopgClientId() => Required("AUTH0_ROPG_CLIENT_ID");
    public static string? RopgClientSecret() => Environment.GetEnvironmentVariable("AUTH0_ROPG_CLIENT_SECRET"); // confidential apps only
    public static (string Username, string Password) TestUser() =>
        (Required("AUTH0_TEST_USERNAME"), Required("AUTH0_TEST_PASSWORD"));
}
```

### Cached token provider — `Tests/Support/Auth/CachedTokenProvider.cs`

One provider per grant, caching the token for its `ExpiresIn`. Re-fetches ~60s early so a token never expires mid-test. **No sleep, no per-test fetch.** A `Func<DateTimeOffset>` clock is injected (constructor injection) so the cache logic is unit-testable without faking the system clock. A `SemaphoreSlim` makes the refresh safe under NUnit parallelism.

```csharp
using Auth0.AuthenticationApi;
using Auth0.AuthenticationApi.Models;

namespace Tests.Support.Auth;

public abstract class CachedTokenProvider
{
    private static readonly TimeSpan Skew = TimeSpan.FromSeconds(60);
    private readonly SemaphoreSlim _gate = new(1, 1);
    private readonly Func<DateTimeOffset> _now;
    private string? _token;
    private DateTimeOffset _expiresAt;

    protected CachedTokenProvider(Func<DateTimeOffset>? now = null) =>
        _now = now ?? (() => DateTimeOffset.UtcNow);

    protected abstract Task<AccessTokenResponse> FetchTokenAsync();

    public async Task<string> GetAccessTokenAsync()
    {
        if (_token is not null && _now() < _expiresAt - Skew)
            return _token;

        await _gate.WaitAsync();
        try
        {
            if (_token is not null && _now() < _expiresAt - Skew)
                return _token;

            var response = await FetchTokenAsync();
            _token = response.AccessToken;
            _expiresAt = _now().AddSeconds(response.ExpiresIn);
            return _token;
        }
        finally
        {
            _gate.Release();
        }
    }
}

/// <summary>Client Credentials (M2M) — the default for API-test suites.</summary>
public sealed class M2MTokenProvider(Func<DateTimeOffset>? now = null) : CachedTokenProvider(now)
{
    private readonly AuthenticationApiClient _client = new(new Uri($"https://{Auth0Config.Domain}/"));

    protected override Task<AccessTokenResponse> FetchTokenAsync() =>
        _client.GetTokenAsync(new ClientCredentialsTokenRequest
        {
            ClientId = Auth0Config.M2MClientId(),
            ClientSecret = Auth0Config.M2MClientSecret(),
            Audience = Auth0Config.Audience,
        });
}

/// <summary>Resource Owner Password Grant — a token AS a specific test user. Test-only.</summary>
public sealed class TestUserTokenProvider(Func<DateTimeOffset>? now = null) : CachedTokenProvider(now)
{
    private readonly AuthenticationApiClient _client = new(new Uri($"https://{Auth0Config.Domain}/"));

    protected override Task<AccessTokenResponse> FetchTokenAsync()
    {
        var (username, password) = Auth0Config.TestUser();
        return _client.GetTokenAsync(new ResourceOwnerTokenRequest
        {
            ClientId = Auth0Config.RopgClientId(),
            ClientSecret = Auth0Config.RopgClientSecret(), // null for public apps — fine
            Username = username,
            Password = password,
            Audience = Auth0Config.Audience,
            Scope = "openid profile email",
            Realm = Auth0Config.Realm, // → uses the password-realm grant
        });
    }
}
```

### Shared, suite-wide singletons — `Tests/Support/Auth/Tokens.cs`

One token per fixture/suite, **not per test**. Expose ready-made singletons so tests never construct a provider or call `GetTokenAsync` directly.

```csharp
namespace Tests.Support.Auth;

public static class Tokens
{
    // Reused across the suite — the token is cached inside the provider.
    public static readonly M2MTokenProvider M2M = new();
    public static readonly TestUserTokenProvider TestUser = new();
}
```

### Stash into an API client — `Authorization: Bearer`

The provider is injected (constructor injection), so a fake can be passed in unit tests. The cache makes per-request header attachment cheap.

```csharp
namespace Tests.Support.Auth;

public sealed class OrdersClient(HttpClient http, CachedTokenProvider tokens)
{
    public async Task<HttpResponseMessage> GetOrderAsync(string id)
    {
        var token = await tokens.GetAccessTokenAsync();
        using var request = new HttpRequestMessage(HttpMethod.Get, $"/orders/{id}");
        request.Headers.Authorization = new("Bearer", token);
        return await http.SendAsync(request);
    }
}
```

### Seed Playwright .NET auth state from a token (skip the login UI)

Mint a token as the test user, write it where the SPA expects it, save `StorageState` once, reuse across the suite. Adapt the storage key/shape to your app. The pattern is **token in → state file out → reused by every test**, no login form.

```csharp
using Microsoft.Playwright;
using Tests.Support.Auth;

public static class AuthStateSeeder
{
    public static async Task SeedAsync(string statePath = ".auth/user.json")
    {
        var token = await Tokens.TestUser.GetAccessTokenAsync();

        using var playwright = await Playwright.CreateAsync();
        await using var browser = await playwright.Chromium.LaunchAsync();
        var context = await browser.NewContextAsync();
        var page = await context.NewPageAsync();

        await page.GotoAsync("https://app.flexinvest.test"); // origin must match for storage to apply
        await page.EvaluateAsync(
            "token => window.localStorage.setItem('flexinvest.accessToken', token)", token);

        await context.StorageStateAsync(new() { Path = statePath });
    }
}
```

Reuse the saved state on each context: `await browser.NewContextAsync(new() { StorageStatePath = ".auth/user.json" })`. See `qa/dotnet/skills/ui-test-author/playwright` for fixture wiring.

### Device Authorization Flow — `Tests/Support/Auth/DeviceCodeProvider.cs`

Niche: input-constrained clients. Start the flow, surface the `VerificationUriComplete` for approval, then **poll `GetTokenAsync` honoring the server-dictated `Interval`** — wait on the endpoint's `authorization_pending` / `slow_down` responses, **never a fixed sleep beyond that interval**.

```csharp
using Auth0.AuthenticationApi;
using Auth0.AuthenticationApi.Models;
using Auth0.Core.Exceptions;

namespace Tests.Support.Auth;

public static class DeviceCodeProvider
{
    public static async Task<string> GetDeviceTokenAsync()
    {
        var client = new AuthenticationApiClient(new Uri($"https://{Auth0Config.Domain}/"));
        var clientId = Auth0Config.RopgClientId(); // a Device-Code-enabled public app

        var flow = await client.StartDeviceFlowAsync(new DeviceCodeRequest
        {
            ClientId = clientId,
            Scope = "openid profile email",
            Audience = Auth0Config.Audience,
        });
        TestContext.Out.WriteLine($"Approve at: {flow.VerificationUriComplete}");

        var deadline = DateTimeOffset.UtcNow.AddSeconds(flow.ExpiresIn);
        var interval = TimeSpan.FromSeconds(flow.Interval);

        while (DateTimeOffset.UtcNow < deadline)
        {
            await Task.Delay(interval); // server-dictated interval — NOT an arbitrary sleep
            try
            {
                var token = await client.GetTokenAsync(new DeviceCodeTokenRequest
                {
                    ClientId = clientId,
                    DeviceCode = flow.DeviceCode,
                });
                return token.AccessToken;
            }
            catch (ErrorApiException ex) when (ex.ApiError.Error == "authorization_pending") { /* keep waiting */ }
            catch (ErrorApiException ex) when (ex.ApiError.Error == "slow_down") { interval += TimeSpan.FromSeconds(5); }
        }
        throw new TimeoutException("Device authorization timed out before approval.");
    }
}
```

### NUnit — M2M token reaches the API as a Bearer header

```csharp
using NUnit.Framework;
using Tests.Support.Auth;

[TestFixture]
public class OrdersApiTests
{
    [Test]
    public async Task Should_Return200_When_CalledWithM2MToken()
    {
        using var http = new HttpClient { BaseAddress = new Uri(Auth0Config.Audience) };
        var client = new OrdersClient(http, Tokens.M2M);

        using var response = await client.GetOrderAsync("ord_123");

        Assert.That(response.StatusCode, Is.EqualTo(System.Net.HttpStatusCode.OK));
    }
}
```

### NUnit — the provider caches, not re-fetches (offline, fake clock)

The cache is the contract: one fetch, reused until near expiry. Inject the clock and count fetches with a test subclass — no network.

```csharp
using Auth0.AuthenticationApi.Models;
using NUnit.Framework;
using Tests.Support.Auth;

[TestFixture]
public class CachedTokenProviderTests
{
    private sealed class FakeProvider(Func<DateTimeOffset> now) : CachedTokenProvider(now)
    {
        public int Fetches { get; private set; }
        protected override Task<AccessTokenResponse> FetchTokenAsync()
        {
            Fetches++;
            return Task.FromResult(new AccessTokenResponse { AccessToken = $"tok-{Fetches}", ExpiresIn = 3600 });
        }
    }

    [Test]
    public async Task Should_ReuseToken_When_NotNearExpiry()
    {
        var now = DateTimeOffset.UnixEpoch;
        var provider = new FakeProvider(() => now);

        Assert.That(await provider.GetAccessTokenAsync(), Is.EqualTo("tok-1"));
        now = now.AddMinutes(30); // well inside the hour
        Assert.That(await provider.GetAccessTokenAsync(), Is.EqualTo("tok-1"));
        Assert.That(provider.Fetches, Is.EqualTo(1));
    }

    [Test]
    public async Task Should_RefetchToken_When_PastExpiryMinusSkew()
    {
        var now = DateTimeOffset.UnixEpoch;
        var provider = new FakeProvider(() => now);

        Assert.That(await provider.GetAccessTokenAsync(), Is.EqualTo("tok-1"));
        now = now.AddSeconds(3600); // at expiry → past expiry - 60s skew
        Assert.That(await provider.GetAccessTokenAsync(), Is.EqualTo("tok-2"));
        Assert.That(provider.Fetches, Is.EqualTo(2));
    }
}
```

## Rules

### Grant choice
- **M2M is the default for API suites.** No user context — use it whenever the test doesn't need a *specific* user's identity.
- Use **ROPG** only when the test needs *this test user's* roles/permissions/data. It is **test-only** — see the caveat.
- Use **device-code** only for input-constrained clients; the approval step can't be fully headless.

### ROPG security caveat (call out once, loudly)
- ROPG (`ResourceOwnerTokenRequest`, `password`/`password-realm`) sends a username+password to the token endpoint. It **must be explicitly enabled** on the Auth0 app's grant types and is **for test tenants only** — never production. It bypasses MFA and brute-force protections by design. Use a dedicated **test tenant** with **seeded test users**, never real customer credentials.

### Caching & expiry
- Fetch a token **once per fixture/suite** and cache it for `ExpiresIn`. Refresh ~60s early (skew). Never fetch per test.
- **Never sleep-poll.** For device-code, `Task.Delay(interval)` at the server-dictated cadence and back off on `slow_down`; for the other grants there's nothing to poll.
- Guard the refresh with a `SemaphoreSlim` so NUnit parallel tests don't stampede the token endpoint.

### Async (CLAUDE.md hard rule)
- Async all the way: `await GetTokenAsync(...)`. **Never** `.Result` / `.Wait()` / `.GetAwaiter().GetResult()` on a token call.

### Secrets
- `ClientSecret`, test-user passwords, `AUTH0_DOMAIN`, `AUTH0_AUDIENCE`, `Realm` via **env vars only**, read **lazily** (methods, not static field initializers). Never logged, never committed. In CI, source them per `qa/dotnet/skills/ci-pipelines/github-actions`.
- Never log a token. Treat the `AccessToken` as a secret in flight.

### Stashing
- API tests: inject the provider into the client; set `request.Headers.Authorization = new("Bearer", token)`.
- UI tests: mint once, seed the storage your SPA reads, save `StorageState`, reuse — see `qa/dotnet/skills/ui-test-author/playwright`.

### What NOT to do
- No token fetch per test, no uncached `GetTokenAsync` in a loop.
- No `.Result` / `.Wait()` on token calls.
- No fixed `Task.Delay` except the *server-dictated* device-code interval.
- No ROPG against a production tenant or with real user credentials.
- No secret or token in source, logs, user-secrets committed to the repo.
- No reading secrets in a static initializer — it breaks tests that don't need them.

## Generation steps

1. Read the test project (`.csproj`, existing fixtures) for house style and NUnit conventions.
2. Confirm `Auth0.AuthenticationApi` is referenced (`dotnet add package Auth0.AuthenticationApi`).
3. Confirm the env vars are wired into the test environment (CI secret store / launch profile), **not** committed: `AUTH0_DOMAIN`, `AUTH0_AUDIENCE`, `AUTH0_M2M_CLIENT_ID/SECRET`, and for ROPG `AUTH0_ROPG_CLIENT_ID`, `AUTH0_TEST_USERNAME/PASSWORD`, `AUTH0_REALM`.
4. Generate `Auth0Config.cs`, `CachedTokenProvider.cs`, `Tokens.cs`, plus the consumer wiring (API client header and/or Playwright state seeder).
5. Run the cache unit tests anywhere (offline); run the live token tests with the secrets present.

## Cross-references

- **`qa/typescript/skills/auth0-test-tokens`** (`auth0` npm `AuthenticationClient`), **`qa/java/skills/auth0-test-tokens`** (`com.auth0:auth0` `AuthAPI`) — the sibling stacks; same three grants, same cache + stash shape.
- **`auth/_shared/auth0-concepts`** — the entity/flow model (Tenant / Application / API / audience / grant types) this skill assumes.
- **`auth/auth0-dotnet`**, **`auth/auth0-blazor`** — the **app-side** login flows this skill complements. This skill never implements user-facing login; those do.
- **`qa/dotnet/skills/api-test-author/generator`** — the M2M consumer: where the `Bearer` header lands on the API client.
- **`qa/dotnet/skills/ui-test-author/playwright`** — the ROPG consumer: `StorageState` / fixture patterns for seeding auth without the login UI.
- **`qa/dotnet/skills/test-data-builder`** — provisioning/seeding the test users that ROPG authenticates as.
- **`qa/dotnet/skills/ci-pipelines/github-actions`** — where the Auth0 secrets are sourced in CI (OIDC / encrypted secrets), never hardcoded.
