# Deep-dive details — `qa-dotnet:test-login-tokens`

Sections moved out of SKILL.md for on-demand loading. Read what the task needs.

## Templates

### Config — `Tests/Support/Auth/Auth0Config.cs`

Every value comes from the environment, and **secrets are read lazily** through methods so unrelated tests
don't require them. No static initializer touches a secret, and no tenant or API URL is a literal default — a
default would silently point a run at somebody's tenant.

```csharp
namespace Tests.Support.Auth;

public static class Auth0Config
{
    public static string Domain => Required("AUTH0_DOMAIN");
    public static string Audience => Required("AUTH0_AUDIENCE");
    public static string Realm => Environment.GetEnvironmentVariable("AUTH0_REALM") ?? "Username-Password-Authentication";

    public static string M2MClientId() => Required("AUTH0_M2M_CLIENT_ID");
    public static string M2MClientSecret() => Required("AUTH0_M2M_CLIENT_SECRET");
    public static string RopgClientId() => Required("AUTH0_ROPG_CLIENT_ID");
    public static string? RopgClientSecret() => Environment.GetEnvironmentVariable("AUTH0_ROPG_CLIENT_SECRET");
    public static string DeviceClientId() => Required("AUTH0_DEVICE_CLIENT_ID");
    public static (string Username, string Password) TestUser() =>
        (Required("AUTH0_TEST_USERNAME"), Required("AUTH0_TEST_PASSWORD"));

    private static string Required(string name) =>
        Environment.GetEnvironmentVariable(name)
        ?? throw new InvalidOperationException($"Environment variable {name} is not set (Auth0 test-token config)");
}
```

`Realm` defaults to Auth0's own default database connection name, not to anything of the app's.
`RopgClientSecret()` is optional: a public (SPA-style) client sends none.

### Cached token provider — `Tests/Support/Auth/CachedTokenProvider.cs`

One provider per grant, caching the token for its `ExpiresIn` and re-fetching 60 s early so a token never
expires mid-test. **No sleep, no per-test fetch.** The clock is injected so the cache logic is unit-testable,
and a `SemaphoreSlim` keeps NUnit's parallel fixtures from stampeding the token endpoint.

```csharp
using Auth0.AuthenticationApi;
using Auth0.AuthenticationApi.Models;

namespace Tests.Support.Auth;

public abstract class CachedTokenProvider(Func<DateTimeOffset>? now = null)
{
    private static readonly TimeSpan Skew = TimeSpan.FromSeconds(60);
    private readonly SemaphoreSlim _gate = new(1, 1);
    private readonly Func<DateTimeOffset> _now = now ?? (() => DateTimeOffset.UtcNow);
    private string? _token;
    private DateTimeOffset _expiresAt;

    protected abstract Task<AccessTokenResponse> FetchTokenAsync();

    public async Task<string> GetAccessTokenAsync()
    {
        if (IsFresh())
        {
            return _token!;
        }
        await _gate.WaitAsync();
        try
        {
            if (!IsFresh())
            {
                var response = await FetchTokenAsync();
                _token = response.AccessToken;
                _expiresAt = _now().AddSeconds(response.ExpiresIn);
            }
            return _token!;
        }
        finally
        {
            _gate.Release();
        }
    }

    private bool IsFresh() => _token is not null && _now() < _expiresAt - Skew;
}

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

public sealed class TestUserTokenProvider(Func<DateTimeOffset>? now = null) : CachedTokenProvider(now)
{
    private readonly AuthenticationApiClient _client = new(new Uri($"https://{Auth0Config.Domain}/"));

    protected override Task<AccessTokenResponse> FetchTokenAsync()
    {
        var (username, password) = Auth0Config.TestUser();
        return _client.GetTokenAsync(new ResourceOwnerTokenRequest
        {
            ClientId = Auth0Config.RopgClientId(),
            ClientSecret = Auth0Config.RopgClientSecret(),
            Username = username,
            Password = password,
            Audience = Auth0Config.Audience,
            Scope = "openid profile email",
            Realm = Auth0Config.Realm,
        });
    }
}
```

The `try`/`finally` releases the semaphore inside a helper; no test carries one. Setting `Realm` makes the
request the `password-realm` grant.

### Suite-wide providers — `Tests/Support/Auth/Tokens.cs`

One token per suite, **not per test**: tests never construct a provider or call `GetTokenAsync` directly.

```csharp
namespace Tests.Support.Auth;

public static class Tokens
{
    public static readonly M2MTokenProvider M2M = new();
    public static readonly TestUserTokenProvider TestUser = new();
}
```

### Stash into an API client — `Authorization: Bearer`

The provider is injected, so a fake can be passed in unit tests; the cache makes per-request attachment cheap.

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

### Seed the Playwright signed-in state from a token (skip the login UI)

This is the token variant of `assets/AuthSetup.cs` in `qa/dotnet/skills/ui-test-author/playwright`
(`references/lifecycle.md` §7). It keeps that file's class name, its root namespace and its `UserState` path, so
every signed-in fixture's `ContextOptions()` (`options.StorageStatePath = AuthSetup.UserState`) is unchanged; a
project uses one body or the other, never both. **Token in → state file out → reused by every test.**

```csharp
using System.Text.Json;
using Example.UiTests.Pages;
using Example.UiTests.Support;
using Microsoft.Playwright;
using Microsoft.Playwright.TestAdapter;
using NUnit.Framework;
using Tests.Support.Auth;
using static Microsoft.Playwright.Assertions;

namespace Example.UiTests;

[SetUpFixture]
public class AuthSetup
{
    private const string TokenStorageKey = "auth.accessToken";

    public static string UserState => Path.Combine(TestContext.CurrentContext.WorkDirectory, "auth-user.json");

    [OneTimeSetUp]
    public async Task SaveSignedInState()
    {
        var baseUrl = BaseTest.RequiredEnv("BASE_URL");
        var token = await Tokens.TestUser.GetAccessTokenAsync();
        using var playwright = await Playwright.CreateAsync();
        await using var browser = await playwright[PlaywrightSettingsProvider.BrowserName].LaunchAsync(PlaywrightSettingsProvider.LaunchOptions);
        var context = await browser.NewContextAsync(new() { BaseURL = baseUrl, StorageState = TokenState(baseUrl, token) });
        var page = await context.NewPageAsync();

        await page.GotoAsync("/");
        await Expect(new HomePage(page).Greeting, "greeting with the seeded token").ToBeVisibleAsync();

        await context.StorageStateAsync(new() { Path = UserState });
    }

    private static string TokenState(string baseUrl, string token) =>
        JsonSerializer.Serialize(new
        {
            cookies = Array.Empty<object>(),
            origins = new[]
            {
                new
                {
                    origin = new Uri(baseUrl).GetLeftPart(UriPartial.Authority),
                    localStorage = new[] { new { name = TokenStorageKey, value = token } },
                },
            },
        });
}
```

- **The origin is `BASE_URL`'s** — scheme, host and port — so the seeded entry applies to the app under test,
  wherever the run points. Storage is per origin: an entry for another origin is never read.
- **`TokenStorageKey` is the key your SPA reads** (its auth library's storage key, or the app's own). Look it up
  in the app; do not guess.
- **The greeting is checked before saving**, so a rejected or expired token fails here, once, with a message —
  not in every signed-in test. This `[SetUpFixture]` is plumbing, not a test class, so it navigates with
  `page.GotoAsync("/")` and borrows `HomePage` only for the assertion.
- **The state is saved after the app has loaded**, so whatever the app writes on start (a session cookie, a
  refreshed token) is in the file too.
- The file is `<WorkDirectory>/auth-user.json` — one path for both `AuthSetup` bodies, under `bin/`, never
  committed. From 1.59, `IBrowserContext.SetStorageStateAsync(path)` loads a saved file into an existing context;
  a fixture still points at the file through `ContextOptions()`.

### What a storage state carries

| Where the app keeps its session | In `StorageStateAsync`? | Seedable this way? |
|---|---|---|
| Cookies (incl. `HttpOnly`) | yes | yes — `cookies` |
| `localStorage` | yes | yes — `origins[].localStorage` |
| IndexedDB | only with `new() { Path = …, IndexedDB = true }` [1.51] | save after a real sign-in with the option on |
| `sessionStorage` | **never** | no — set it per test with `Context.AddInitScriptAsync` |
| In memory only (the Auth0 SPA SDK's default `cacheLocation: 'memory'`) | **never** | no — the app must use `cacheLocation: 'localstorage'` in test builds, or sign in through the UI (`AuthSetup`'s default body) |

### Device Authorization Flow — `Tests/Support/Auth/DeviceCodeProvider.cs`

Niche: input-constrained clients. Start the flow, surface `VerificationUriComplete` for approval, then **poll
the token endpoint at the server-dictated `Interval`** — `authorization_pending` means keep polling,
`slow_down` means add five seconds, anything else is a failure. The poll reads the JSON error field, so no
exception is caught and swallowed.

```csharp
using System.Text.Json;
using Auth0.AuthenticationApi;
using Auth0.AuthenticationApi.Models;
using NUnit.Framework;

namespace Tests.Support.Auth;

public sealed class DeviceCodeProvider(HttpClient http)
{
    public async Task<string> GetDeviceTokenAsync()
    {
        var clientId = Auth0Config.DeviceClientId();
        var flow = await new AuthenticationApiClient(new Uri($"https://{Auth0Config.Domain}/")).StartDeviceFlowAsync(new DeviceCodeRequest
        {
            ClientId = clientId,
            Scope = "openid profile email",
            Audience = Auth0Config.Audience,
        });
        TestContext.Out.WriteLine("Approve the device at {0}", flow.VerificationUriComplete);
        var deadline = DateTimeOffset.UtcNow.AddSeconds(flow.ExpiresIn);
        var interval = TimeSpan.FromSeconds(flow.Interval);
        while (DateTimeOffset.UtcNow < deadline)
        {
            await Task.Delay(interval);
            using var response = await http.PostAsync($"https://{Auth0Config.Domain}/oauth/token", new FormUrlEncodedContent(new Dictionary<string, string>
            {
                ["grant_type"] = "urn:ietf:params:oauth:grant-type:device_code",
                ["device_code"] = flow.DeviceCode,
                ["client_id"] = clientId,
            }));
            using var body = JsonDocument.Parse(await response.Content.ReadAsStringAsync());
            if (response.IsSuccessStatusCode)
            {
                return body.RootElement.GetProperty("access_token").GetString()
                    ?? throw new InvalidOperationException("The token response carries no access_token");
            }
            var error = body.RootElement.GetProperty("error").GetString();
            if (error == "slow_down")
            {
                interval += TimeSpan.FromSeconds(5);
            }
            else if (error != "authorization_pending")
            {
                throw new InvalidOperationException($"Device authorization failed with {(int)response.StatusCode}: {body.RootElement}");
            }
        }
        throw new TimeoutException($"Device authorization was not approved within {flow.ExpiresIn} s");
    }
}
```

`Task.Delay(interval)` is the one sanctioned delay: the server dictates the interval, and polling faster earns
`slow_down`. It is never a wait for application state.

### NUnit — M2M token reaches the API as a Bearer header

```csharp
using System.Net;
using NUnit.Framework;
using Tests.Support.Auth;

namespace Tests;

public class OrdersApiTests
{
    [Test]
    public async Task Should_Return200_When_CalledWithAnM2MToken()
    {
        using var http = new HttpClient { BaseAddress = new Uri(Auth0Config.Audience) };
        var client = new OrdersClient(http, Tokens.M2M);

        using var response = await client.GetOrderAsync("ord_123");

        Assert.That(response.StatusCode, Is.EqualTo(HttpStatusCode.OK), await response.Content.ReadAsStringAsync());
    }
}
```

### NUnit — the provider caches, not re-fetches (offline, fake clock)

```csharp
using Auth0.AuthenticationApi.Models;
using NUnit.Framework;
using Tests.Support.Auth;

namespace Tests;

public class CachedTokenProviderTests
{
    [Test]
    public async Task Should_ReuseTheToken_When_ItIsNotNearExpiry()
    {
        var now = DateTimeOffset.UnixEpoch;
        var provider = new CountingProvider(() => now);
        await provider.GetAccessTokenAsync();
        now = now.AddMinutes(30);

        var token = await provider.GetAccessTokenAsync();

        Assert.Multiple(() =>
        {
            Assert.That(token, Is.EqualTo("tok-1"));
            Assert.That(provider.Fetches, Is.EqualTo(1));
        });
    }

    [Test]
    public async Task Should_RefetchTheToken_When_PastExpiryMinusSkew()
    {
        var now = DateTimeOffset.UnixEpoch;
        var provider = new CountingProvider(() => now);
        await provider.GetAccessTokenAsync();
        now = now.AddSeconds(3600);

        var token = await provider.GetAccessTokenAsync();

        Assert.Multiple(() =>
        {
            Assert.That(token, Is.EqualTo("tok-2"));
            Assert.That(provider.Fetches, Is.EqualTo(2));
        });
    }

    private sealed class CountingProvider(Func<DateTimeOffset> now) : CachedTokenProvider(now)
    {
        public int Fetches { get; private set; }

        protected override Task<AccessTokenResponse> FetchTokenAsync()
        {
            Fetches++;
            return Task.FromResult(new AccessTokenResponse { AccessToken = $"tok-{Fetches}", ExpiresIn = 3600 });
        }
    }
}
```
