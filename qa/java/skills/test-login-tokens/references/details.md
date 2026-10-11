# Deep-dive details — `qa-java:test-login-tokens`

Sections moved out of SKILL.md for on-demand loading. Read what the task needs.

## Templates

### Config — `support/auth/Auth0Config.java`

Non-secret config (domain, audience, realm) can have fallbacks; **secrets are read lazily** through methods so
unrelated tests don't require them. No static initializer touches a secret, and importing the class fetches no
token. `AUTH0_ROPG_CLIENT_SECRET` is optional because only a confidential ROPG application has one.

```java
package support.auth;

public final class Auth0Config {
    private Auth0Config() {}

    private static String required(String name) {
        String v = System.getenv(name);
        if (v == null || v.isBlank()) {
            throw new IllegalStateException("Missing required env var " + name + " (Auth0 test-token config).");
        }
        return v;
    }

    private static String orDefault(String name, String fallback) {
        String v = System.getenv(name);
        return (v == null || v.isBlank()) ? fallback : v;
    }

    public static String domain()   { return orDefault("AUTH0_DOMAIN", "yourco-dev.eu.auth0.com"); }
    public static String audience() { return orDefault("AUTH0_AUDIENCE", "https://api.flexinvest.test"); }
    public static String realm()    { return orDefault("AUTH0_REALM", "Username-Password-Authentication"); }

    public static String m2mClientId()      { return required("AUTH0_M2M_CLIENT_ID"); }
    public static String m2mClientSecret()  { return required("AUTH0_M2M_CLIENT_SECRET"); }
    public static String ropgClientId()     { return required("AUTH0_ROPG_CLIENT_ID"); }
    public static String ropgClientSecret() { return orDefault("AUTH0_ROPG_CLIENT_SECRET", ""); }
    public static String testUsername()     { return required("AUTH0_TEST_USERNAME"); }
    public static String testPassword()     { return required("AUTH0_TEST_PASSWORD"); }
}
```

### Cached token provider — `support/auth/CachedTokenProvider.java`

One provider per grant, caching the token for its `getExpiresIn()`. Re-fetches ~60s early so a token never
expires mid-test. **No sleep, no per-test fetch.** A `Supplier<Instant>` clock is injected (constructor
injection) so the cache logic is unit-testable. `synchronized` makes the refresh safe under TestNG parallelism.

```java
package support.auth;

import java.time.Instant;
import java.util.function.Supplier;

public abstract class CachedTokenProvider {
    private static final long SKEW_SECONDS = 60;

    private final Supplier<Instant> now;
    private String token;
    private Instant expiresAt = Instant.MIN;

    protected CachedTokenProvider(Supplier<Instant> now) {
        this.now = now;
    }

    protected abstract Fetched fetchToken() throws Exception;

    public synchronized String getAccessToken() throws Exception {
        if (token != null && now.get().isBefore(expiresAt.minusSeconds(SKEW_SECONDS))) {
            return token;
        }
        Fetched fetched = fetchToken();
        token = fetched.accessToken();
        expiresAt = now.get().plusSeconds(fetched.expiresInSeconds());
        return token;
    }

    public record Fetched(String accessToken, long expiresInSeconds) {}
}
```

The M2M provider is the default for API-test suites; the ROPG provider mints a token **as** a specific test user
(test-only). The `login(...)` overload that takes a realm uses the `password-realm` grant.

```java
package support.auth;

import com.auth0.client.auth.AuthAPI;
import com.auth0.json.auth.TokenHolder;
import java.time.Instant;
import java.util.function.Supplier;

public final class M2MTokenProvider extends CachedTokenProvider {
    private final AuthAPI authAPI = AuthAPI
        .newBuilder(Auth0Config.domain(), Auth0Config.m2mClientId(), Auth0Config.m2mClientSecret())
        .build();

    public M2MTokenProvider() { super(Instant::now); }
    public M2MTokenProvider(Supplier<Instant> now) { super(now); }

    @Override
    protected Fetched fetchToken() throws Exception {
        TokenHolder holder = authAPI.requestToken(Auth0Config.audience()).execute().getBody();
        return new Fetched(holder.getAccessToken(), holder.getExpiresIn());
    }
}
```

```java
package support.auth;

import com.auth0.client.auth.AuthAPI;
import com.auth0.json.auth.TokenHolder;
import java.time.Instant;
import java.util.function.Supplier;

public final class TestUserTokenProvider extends CachedTokenProvider {
    private final AuthAPI authAPI = AuthAPI
        .newBuilder(Auth0Config.domain(), Auth0Config.ropgClientId(), Auth0Config.ropgClientSecret())
        .build();

    public TestUserTokenProvider() { super(Instant::now); }
    public TestUserTokenProvider(Supplier<Instant> now) { super(now); }

    @Override
    protected Fetched fetchToken() throws Exception {
        TokenHolder holder = authAPI
            .login(Auth0Config.testUsername(), Auth0Config.testPassword().toCharArray(), Auth0Config.realm())
            .setAudience(Auth0Config.audience())
            .setScope("openid profile email")
            .execute()
            .getBody();
        return new Fetched(holder.getAccessToken(), holder.getExpiresIn());
    }
}
```

### Shared, suite-wide providers — `support/auth/Tokens.java`

One token per suite, **not per test**. Tests never construct a provider or call `AuthAPI` directly; the token is
cached inside the provider.

```java
package support.auth;

public final class Tokens {
    private Tokens() {}

    public static final M2MTokenProvider M2M = new M2MTokenProvider();
    public static final TestUserTokenProvider TEST_USER = new TestUserTokenProvider();
}
```

### Stash into an API client — `Authorization: Bearer` (RestAssured)

The provider is injected (constructor injection), so a fake can be passed in unit tests. The cache makes
per-request header attachment cheap.

```java
package support.auth;

import static io.restassured.RestAssured.given;
import io.restassured.response.Response;

public final class OrdersClient {
    private final String baseUrl;
    private final CachedTokenProvider tokens;

    public OrdersClient(String baseUrl, CachedTokenProvider tokens) {
        this.baseUrl = baseUrl;
        this.tokens = tokens;
    }

    public Response getOrder(String id) throws Exception {
        String token = tokens.getAccessToken();
        return given()
            .baseUri(baseUrl)
            .header("Authorization", "Bearer " + token)
            .when()
            .get("/orders/{id}", id);
    }
}
```

### Signed-in browser state from a token (skip the login UI)

The UI suite's signed-in state follows J1's lifecycle (`qa/java/skills/ui-test-author/playwright/references/lifecycle.md`
§6): **one `@BeforeSuite` writes one state file per role**, and each signed-in class picks its role in
`contextOptions()`. This is the token variant of that `AuthSetup`: instead of driving the login form, it mints the
test user's token and writes it where the SPA reads it, at the `BASE_URL` origin.

`support/TokenAuthSetup.java`, in the `support` package beside `BaseTest`, listed in `testng.xml` as a `<class>`
next to the `<packages>` entry:

```java
package com.example.uitests.support;

import com.example.uitests.pages.HomePage;
import com.microsoft.playwright.Browser;
import com.microsoft.playwright.BrowserContext;
import com.microsoft.playwright.Page;
import com.microsoft.playwright.Playwright;
import org.testng.annotations.BeforeSuite;
import support.auth.Tokens;

import java.nio.file.Path;

import static com.microsoft.playwright.assertions.PlaywrightAssertions.assertThat;

public class TokenAuthSetup {
    public static final Path TEST_USER_STATE = Path.of("build", ".auth", "test-user.json");

    @BeforeSuite(alwaysRun = true)
    public void saveTestUserState() throws Exception {
        String token = Tokens.TEST_USER.getAccessToken();
        try (Playwright playwright = Playwright.create()) {
            BrowserContext context = playwright.chromium().launch()
                    .newContext(new Browser.NewContextOptions().setBaseURL(BaseTest.requiredEnv("BASE_URL")));
            Page page = context.newPage();
            page.navigate("/");
            page.evaluate("token => window.localStorage.setItem('flexinvest.accessToken', token)", token);
            page.reload();
            assertThat(new HomePage(page).greeting()).isVisible();
            context.storageState(new BrowserContext.StorageStateOptions().setPath(TEST_USER_STATE));
        }
    }
}
```

A signed-in class chooses the role in its `contextOptions()`; a signed-out class does not override it:

```java
@Override
protected Browser.NewContextOptions contextOptions() {
    return new Browser.NewContextOptions().setStorageStatePath(TokenAuthSetup.TEST_USER_STATE);
}
```

- The storage key (`flexinvest.accessToken`) and its shape are the app's; read them from the SPA's auth code.
- The page navigates to the **`BASE_URL` origin** first: `localStorage` is per origin, and a state file saved
  from another origin never reaches the app.
- The **greeting assertion after the reload** proves the app accepted the token before the state is saved;
  saving straight after `setItem` would save a state the app may reject.
- A second role is a second state file written by the same method (`build/.auth/admin.json` from an admin
  token). The files live under `build/`, so they are rewritten every run and never committed.
- **What storage state carries:** cookies and `localStorage`, and IndexedDB only when saved with
  `setIndexedDB(true)` on `StorageStateOptions` [1.51]. It never carries `sessionStorage`, and never an
  in-memory token cache (the default `auth0-spa-js` cache is in memory: configure the SPA's test build with
  `cacheLocation: 'localstorage'`, or seed through the login UI instead).
- The `Playwright` is created and closed inside the one method, so the thread rule holds even though
  `@BeforeSuite` runs on its own thread (`lifecycle.md` §1).

### Device Authorization Flow — `support/auth/DeviceCodeProvider.java`

Niche: input-constrained clients. The Java SDK has no device helper, so use bare `HttpClient`. Start the flow,
surface the `verification_uri_complete` for approval, then **poll `/oauth/token` at the server-dictated
`interval`** — `authorization_pending` means keep waiting, `slow_down` means add 5 seconds to the interval (RFC
8628). The sleep in this helper is that protocol cadence, the one sanctioned interval in this skill; the
deadline is the device code's `expires_in`. The `client_id` is a Device-Code-enabled public application.

```java
package support.auth;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.net.URI;
import java.net.http.*;
import java.time.Instant;

public final class DeviceCodeProvider {
    private static final ObjectMapper MAPPER = new ObjectMapper();
    private static final System.Logger LOG = System.getLogger(DeviceCodeProvider.class.getName());
    private final HttpClient http = HttpClient.newHttpClient();

    public String getDeviceToken() throws Exception {
        String domain = Auth0Config.domain();
        String clientId = Auth0Config.ropgClientId();

        JsonNode flow = post("https://" + domain + "/oauth/device/code",
            "client_id=" + clientId + "&scope=openid%20profile%20email&audience=" + Auth0Config.audience());
        LOG.log(System.Logger.Level.INFO, "Approve the device login at {0}", flow.get("verification_uri_complete").asText());

        String deviceCode = flow.get("device_code").asText();
        Instant deadline = Instant.now().plusSeconds(flow.get("expires_in").asLong());
        long interval = flow.get("interval").asLong();

        while (Instant.now().isBefore(deadline)) {
            Thread.sleep(interval * 1000);
            HttpResponse<String> res = postRaw("https://" + domain + "/oauth/token",
                "grant_type=urn:ietf:params:oauth:grant-type:device_code"
                    + "&device_code=" + deviceCode + "&client_id=" + clientId);
            JsonNode body = MAPPER.readTree(res.body());
            if (res.statusCode() == 200) {
                return body.get("access_token").asText();
            }
            String error = body.path("error").asText();
            if ("slow_down".equals(error)) {
                interval += 5;
            } else if (!"authorization_pending".equals(error)) {
                throw new IllegalStateException("Device token failed: " + error);
            }
        }
        throw new IllegalStateException("Device authorization timed out before approval.");
    }

    private JsonNode post(String url, String form) throws Exception {
        return MAPPER.readTree(postRaw(url, form).body());
    }

    private HttpResponse<String> postRaw(String url, String form) throws Exception {
        HttpRequest req = HttpRequest.newBuilder(URI.create(url))
            .header("content-type", "application/x-www-form-urlencoded")
            .POST(HttpRequest.BodyPublishers.ofString(form))
            .build();
        return http.send(req, HttpResponse.BodyHandlers.ofString());
    }
}
```

### TestNG — M2M token reaches the API as a Bearer header

```java
package api;

import org.testng.annotations.Test;
import support.auth.OrdersClient;
import support.auth.Tokens;
import support.auth.Auth0Config;
import static org.testng.Assert.assertEquals;

public class OrdersApiTest {

    @Test
    public void Should_Return200_When_CalledWithM2MToken() throws Exception {
        OrdersClient client = new OrdersClient(Auth0Config.audience(), Tokens.M2M);

        int status = client.getOrder("ord_123").statusCode();

        assertEquals(status, 200);
    }
}
```

### TestNG — the provider caches, not re-fetches (offline, fake clock)

The cache is the contract: one fetch, reused until near expiry. Inject the clock and count fetches with a test
subclass — no network. Thirty minutes is well inside the hour; the hour itself is past expiry minus the skew.

```java
package support.auth;

import org.testng.annotations.Test;
import java.time.Instant;
import java.util.concurrent.atomic.AtomicReference;
import static org.testng.Assert.assertEquals;

public class CachedTokenProviderTest {

    private static final class FakeProvider extends CachedTokenProvider {
        int fetches = 0;
        FakeProvider(AtomicReference<Instant> clock) { super(clock::get); }
        @Override protected Fetched fetchToken() {
            fetches++;
            return new Fetched("tok-" + fetches, 3600);
        }
    }

    @Test
    public void Should_ReuseToken_When_NotNearExpiry() throws Exception {
        AtomicReference<Instant> now = new AtomicReference<>(Instant.EPOCH);
        FakeProvider provider = new FakeProvider(now);
        provider.getAccessToken();
        now.set(Instant.EPOCH.plusSeconds(30 * 60));

        provider.getAccessToken();

        assertEquals(provider.fetches, 1);
    }

    @Test
    public void Should_RefetchToken_When_PastExpiryMinusSkew() throws Exception {
        AtomicReference<Instant> now = new AtomicReference<>(Instant.EPOCH);
        FakeProvider provider = new FakeProvider(now);
        provider.getAccessToken();
        now.set(Instant.EPOCH.plusSeconds(3600));

        String token = provider.getAccessToken();

        assertEquals(token, "tok-2");
    }
}
```
