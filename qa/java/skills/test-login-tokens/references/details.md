# Deep-dive details — `qa-test-login-tokens-java`

Sections moved out of SKILL.md for on-demand loading. Read what the task needs.

## Templates

### Config — `support/auth/Auth0Config.java`

Non-secret config (domain, audience, realm) can have fallbacks; **secrets are read lazily** through methods so unrelated tests don't require them. No static initializer touches a secret.

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

    // Non-secret — safe defaults; importing this fetches no token.
    public static String domain()   { return orDefault("AUTH0_DOMAIN", "yourco-dev.eu.auth0.com"); }
    public static String audience() { return orDefault("AUTH0_AUDIENCE", "https://api.flexinvest.test"); }
    public static String realm()    { return orDefault("AUTH0_REALM", "Username-Password-Authentication"); }

    // Secrets — read lazily, only when a token is actually fetched. Never logged, never committed.
    public static String m2mClientId()      { return required("AUTH0_M2M_CLIENT_ID"); }
    public static String m2mClientSecret()  { return required("AUTH0_M2M_CLIENT_SECRET"); }
    public static String ropgClientId()     { return required("AUTH0_ROPG_CLIENT_ID"); }
    public static String ropgClientSecret() { return orDefault("AUTH0_ROPG_CLIENT_SECRET", ""); } // confidential apps only
    public static String testUsername()     { return required("AUTH0_TEST_USERNAME"); }
    public static String testPassword()     { return required("AUTH0_TEST_PASSWORD"); }
}
```

### Cached token provider — `support/auth/CachedTokenProvider.java`

One provider per grant, caching the token for its `getExpiresIn()`. Re-fetches ~60s early so a token never expires mid-test. **No sleep, no per-test fetch.** A `Supplier<Instant>` clock is injected (constructor injection) so the cache logic is unit-testable. `synchronized` makes the refresh safe under TestNG parallelism.

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

    /** Returns (accessToken, expiresInSeconds). */
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

```java
package support.auth;

import com.auth0.client.auth.AuthAPI;
import com.auth0.json.auth.TokenHolder;
import java.time.Instant;
import java.util.function.Supplier;

/** Client Credentials (M2M) — the default for API-test suites. */
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

/** Resource Owner Password Grant — a token AS a specific test user. Test-only. */
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
            .getBody(); // realm overload → uses the password-realm grant
        return new Fetched(holder.getAccessToken(), holder.getExpiresIn());
    }
}
```

### Shared, suite-wide singletons — `support/auth/Tokens.java`

One token per suite, **not per test**. Expose ready-made singletons so tests never construct a provider or call `AuthAPI` directly.

```java
package support.auth;

public final class Tokens {
    private Tokens() {}

    // Reused across the suite — the token is cached inside the provider.
    public static final M2MTokenProvider M2M = new M2MTokenProvider();
    public static final TestUserTokenProvider TEST_USER = new TestUserTokenProvider();
}
```

### Stash into an API client — `Authorization: Bearer` (RestAssured)

The provider is injected (constructor injection), so a fake can be passed in unit tests. The cache makes per-request header attachment cheap.

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

### Seed Playwright Java auth state from a token (skip the login UI)

Mint a token as the test user, write it where the SPA expects it, save storage state once, reuse across the suite. Adapt the storage key/shape to your app. The pattern is **token in → state file out → reused by every test**, no login form.

```java
package support.auth;

import com.microsoft.playwright.*;
import java.nio.file.Paths;

public final class AuthStateSeeder {
    private AuthStateSeeder() {}

    public static void seed(String statePath) throws Exception {
        String token = Tokens.TEST_USER.getAccessToken();

        try (Playwright playwright = Playwright.create()) {
            Browser browser = playwright.chromium().launch();
            BrowserContext context = browser.newContext();
            Page page = context.newPage();

            page.navigate("https://app.flexinvest.test"); // origin must match for storage to apply
            page.evaluate("token => window.localStorage.setItem('flexinvest.accessToken', token)", token);

            context.storageState(new BrowserContext.StorageStateOptions().setPath(Paths.get(statePath)));
            browser.close();
        }
    }
}
```

Reuse the saved state on each context: `browser.newContext(new Browser.NewContextOptions().setStorageStatePath(Paths.get(statePath)))`. See `qa/java/skills/ui-test-author/playwright`.

### Device Authorization Flow — `support/auth/DeviceCodeProvider.java`

Niche: input-constrained clients. The Java SDK has no device helper, so use bare `HttpClient`. Start the flow, surface the `verification_uri_complete` for approval, then **poll `/oauth/token` honoring the server-dictated `interval`** — wait on the endpoint's `authorization_pending` / `slow_down` responses, **never a fixed sleep beyond that interval**.

```java
package support.auth;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.net.URI;
import java.net.http.*;
import java.time.Instant;

public final class DeviceCodeProvider {
    private static final ObjectMapper MAPPER = new ObjectMapper();
    private final HttpClient http = HttpClient.newHttpClient();

    public String getDeviceToken() throws Exception {
        String domain = Auth0Config.domain();
        String clientId = Auth0Config.ropgClientId(); // a Device-Code-enabled public app

        JsonNode flow = post("https://" + domain + "/oauth/device/code",
            "client_id=" + clientId + "&scope=openid%20profile%20email&audience=" + Auth0Config.audience());
        System.out.println("Approve at: " + flow.get("verification_uri_complete").asText());

        String deviceCode = flow.get("device_code").asText();
        Instant deadline = Instant.now().plusSeconds(flow.get("expires_in").asLong());
        long interval = flow.get("interval").asLong();

        while (Instant.now().isBefore(deadline)) {
            Thread.sleep(interval * 1000); // server-dictated interval — NOT an arbitrary sleep
            HttpResponse<String> res = postRaw("https://" + domain + "/oauth/token",
                "grant_type=urn:ietf:params:oauth:grant-type:device_code"
                    + "&device_code=" + deviceCode + "&client_id=" + clientId);
            JsonNode body = MAPPER.readTree(res.body());
            if (res.statusCode() == 200) {
                return body.get("access_token").asText();
            }
            String error = body.path("error").asText();
            if ("authorization_pending".equals(error)) { continue; }   // user hasn't approved yet
            if ("slow_down".equals(error)) { interval += 5; continue; } // back off per spec
            throw new IllegalStateException("Device token failed: " + error);
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

The cache is the contract: one fetch, reused until near expiry. Inject the clock and count fetches with a test subclass — no network.

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

        assertEquals(provider.getAccessToken(), "tok-1");
        now.set(Instant.EPOCH.plusSeconds(30 * 60)); // well inside the hour
        assertEquals(provider.getAccessToken(), "tok-1");
        assertEquals(provider.fetches, 1);
    }

    @Test
    public void Should_RefetchToken_When_PastExpiryMinusSkew() throws Exception {
        AtomicReference<Instant> now = new AtomicReference<>(Instant.EPOCH);
        FakeProvider provider = new FakeProvider(now);

        assertEquals(provider.getAccessToken(), "tok-1");
        now.set(Instant.EPOCH.plusSeconds(3600)); // at expiry → past expiry - 60s skew
        assertEquals(provider.getAccessToken(), "tok-2");
        assertEquals(provider.fetches, 2);
    }
}
```
