# Deep-dive details — `qa-auth0-test-tokens-dotnet`

Sections moved out of SKILL.md for on-demand loading. Read what the task needs.

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
