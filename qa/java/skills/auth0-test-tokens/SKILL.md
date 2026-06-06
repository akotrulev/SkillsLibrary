---
name: qa-auth0-test-tokens-java
description: Use when the user asks to obtain Auth0 access tokens *for automated tests* in Java (TestNG) — programmatic token acquisition so suites authenticate WITHOUT driving the interactive login UI. Covers the three grants a QA org uses: Client Credentials (M2M) for API-test suites hitting protected endpoints, Resource Owner Password Grant (ROPG / `password-realm`) to mint a token *as a specific test user*, and the Device Authorization Flow for CLI/input-constrained cases — plus token caching for the token's `expires_in` lifetime and stashing it into the API client (`Authorization: Bearer`) or seeding Playwright Java auth state. Built on `com.auth0:auth0` `AuthAPI` (`requestToken(audience)` for M2M, `login(user, pass, realm)` for ROPG, `TokenHolder`) or bare `java.net.http.HttpClient` to `/oauth/token` for device-code. Triggers: "get an Auth0 M2M token for my RestAssured tests", "log in a test user without the UI in Java", "mint an Auth0 token for a test user", "cache the Auth0 token across the TestNG suite", "seed Playwright Java auth state from an Auth0 token". Do NOT use for app-side login flows / wiring Auth0 into a Spring Boot app (use `auth/auth0-java`), for the Auth0 concept model (use `auth/_shared/auth0-concepts`), or for the TypeScript / .NET stacks (`qa/{typescript,dotnet}/skills/auth0-test-tokens`).
---

# QA — Auth0 Test Tokens (Java / TestNG)

Scaffolds **programmatic Auth0 token acquisition for automated tests** in Java. The goal is narrow: get a valid `access_token` into a test's API client or browser session **without driving the interactive `/authorize` login UI** on every run. This is the *test-token slice* — it complements, and does not replace, the app-side login skill in `auth/auth0-java` (which implements the real user-facing flows).

Three grants cover what a QA org actually needs:

- **Client Credentials (M2M)** — a service-to-service token with no user context. The default for API-test suites that hit protected endpoints. `grant_type=client_credentials` + `audience` + `client_id`/`client_secret`.
- **Resource Owner Password Grant (ROPG)** — mint a token *as a specific test user* (username + password) with no UI. **Test-only, and must be explicitly enabled on the tenant** (see the security caveat). This is the one that unblocks UI auth-state seeding.
- **Device Authorization Flow** — for input-constrained / CLI scenarios: get a `device_code`, then poll `/oauth/token` until the user authorizes. Lowest priority, but included for completeness.

Two cross-cutting rules shape every example:

- **Cache the token for its `expires_in` lifetime.** Fetch once per suite, reuse until ~60s before expiry, then re-fetch. **Never** fetch a token per test. Never sleep-poll.
- **Secrets only via env, read lazily.** `client_secret`, test-user passwords, `AUTH0_DOMAIN`, `audience` come from env vars (CLAUDE.md hard rule). Never logged, never committed, never read in a static initializer.

## Stack

- Java 21
- **`com.auth0:auth0`** — `AuthAPI` builder + `TokenHolder`; falls back to `java.net.http.HttpClient` + Jackson for device-code polling
- **TestNG** as the runner
- **Playwright for Java** (`com.microsoft.playwright`) for the UI auth-state seeding example
- Gradle (Kotlin DSL); token plumbing under `src/test/java/.../support/auth/`; secrets via **env vars only**

## When to use

- An API-test suite (`qa/java/skills/api-test-author/generator`, RestAssured) needs a `Bearer` token to call protected endpoints → **M2M**
- A UI suite needs to skip the login form by seeding an authenticated browser session → **ROPG** → storage state
- You need a token *as a particular seeded test user* (with that user's roles/permissions) → **ROPG**
- A CLI/headless tool or a device without a browser needs to authenticate → **device-code**
- You're re-fetching a token on every test and want to cache it correctly

## When NOT to use

- Wiring Auth0 into the **application under test** (Spring Security resource server, JWT validation, login redirect) → `auth/auth0-java`
- Understanding the Auth0 entity/flow model conceptually → `auth/_shared/auth0-concepts`
- TypeScript or .NET test suites → `qa/{typescript,dotnet}/skills/auth0-test-tokens`

## Decision matrix — which grant for which test

| | **Client Credentials (M2M)** | **ROPG (`password-realm`)** | **Device Authorization** |
|---|---|---|---|
| User context? | **None** — token represents a *service* | **A specific test user** (their roles/perms) | A specific user (interactive consent once) |
| Serves which test | API tests against protected endpoints | UI auth-state seeding; per-user API tests | CLI / input-constrained clients |
| `AuthAPI` call | `requestToken(audience)` | `login(user, pass, realm)` | bare `HttpClient` poll (no SDK helper) |
| `grant_type` | `client_credentials` | `password-realm` (with `realm`) / `password` | `urn:ietf:params:oauth:grant-type:device_code` |
| Credentials | `clientId` + `clientSecret` | app + **username + password** (+ `realm`) | `clientId` (public) |
| Tenant config | M2M app authorized for the API | **ROPG grant enabled** + a DB `realm` | Device Code grant enabled; "Device" app |
| Security caveat | Standard; keep the secret in env | **Test-only — never production** | Approval step can't be fully headless |
| Consumer | `qa/java/skills/api-test-author/generator` | `qa/java/skills/ui-test-author/playwright` storage state | rarely in CI; tooling |

**Default to M2M** for API suites. Reach for **ROPG** only when the test genuinely needs *this user's* identity. Use **device-code** only for the niche input-constrained case.

## Inputs needed

Ask at most 2–3; infer the rest from the build file and existing fixtures.

1. Which grant(s)? (M2M for API tests / ROPG for a test user / device-code) — default M2M.
2. The API **audience** identifier and the **tenant domain** — and for ROPG, the test-user credentials + the connection **realm** (e.g. `Username-Password-Authentication`).
3. Where do the secrets come from in this environment (CI secret store, env)? Confirm they are **not** committed.

## Auth0 SDK surface (cheat-sheet — `com.auth0:auth0` `AuthAPI`)

| Call | Purpose |
|---|---|
| `AuthAPI.newBuilder(domain, clientId, clientSecret).build()` | The auth client. `clientSecret` only for confidential grants. |
| `authAPI.requestToken(audience).execute().getBody()` | **M2M** token → `TokenHolder` (`getAccessToken`, `getExpiresIn`, `getTokenType`). |
| `authAPI.login(username, password.toCharArray(), realm).setAudience(aud).setScope(...).execute().getBody()` | **ROPG** with a `realm` → `password-realm` grant. Omit the realm overload → plain `password`. |
| `bare HttpClient → POST /oauth/device/code` | Start the device flow (the SDK has no device helper). |
| `bare HttpClient → POST /oauth/token` (`grant_type=...device_code`) | Poll the device-code exchange. |
| `TokenHolder { getAccessToken(), getExpiresIn(), getTokenType(), getScope(), getRefreshToken() }` | The shape `AuthAPI` grants return. `getExpiresIn()` is `long` seconds. |

`.execute()` returns a `Response<TokenHolder>`; `.getBody()` unwraps it. For ROPG, pass the password as a `char[]`. Device-code polling returns `403` with `{ "error": "authorization_pending" }` (keep waiting) or `{ "error": "slow_down" }` (raise the interval) until the user approves.

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

## Rules

### Grant choice
- **M2M is the default for API suites.** No user context — use it whenever the test doesn't need a *specific* user's identity.
- Use **ROPG** only when the test needs *this test user's* roles/permissions/data. It is **test-only** — see the caveat.
- Use **device-code** only for input-constrained clients; the approval step can't be fully headless.

### ROPG security caveat (call out once, loudly)
- ROPG (`login(user, pass, realm)`, `password`/`password-realm`) sends a username+password to the token endpoint. It **must be explicitly enabled** on the Auth0 app's grant types and is **for test tenants only** — never production. It bypasses MFA and brute-force protections by design. Use a dedicated **test tenant** with **seeded test users**, never real customer credentials. Pass the password as a `char[]`, not a `String`.

### Caching & expiry
- Fetch a token **once per suite** and cache it for `getExpiresIn()`. Refresh ~60s early (skew). Never fetch per test.
- **Never sleep-poll.** For device-code, `Thread.sleep(interval)` at the server-dictated cadence and back off on `slow_down`; for the other grants there's nothing to poll.
- Guard the refresh with `synchronized` so TestNG parallel tests don't stampede the token endpoint.

### Secrets
- `clientSecret`, test-user passwords, `AUTH0_DOMAIN`, `AUTH0_AUDIENCE`, `realm` via **env vars only**, read **lazily** (methods, not static field initializers). Never logged, never committed. In CI, source them per `qa/java/skills/ci-pipelines/github-actions`.
- Never log a token. Treat the access token as a secret in flight.

### Stashing
- API tests: inject the provider into the client; add the `Authorization: Bearer <token>` header (RestAssured `.header(...)`).
- UI tests: mint once, seed the storage your SPA reads, save storage state, reuse — see `qa/java/skills/ui-test-author/playwright`.

### What NOT to do
- No token fetch per test, no uncached `requestToken`/`login` in a loop.
- No fixed `Thread.sleep` except the *server-dictated* device-code interval.
- No ROPG against a production tenant or with real user credentials.
- No secret or token in source, logs, or committed fixtures.
- No reading secrets in a static initializer — it breaks tests that don't need them.

## Generation steps

1. Read the build file (`build.gradle.kts`) and existing test fixtures for house style and TestNG conventions.
2. Confirm `com.auth0:auth0` is a test dependency (and `com.microsoft.playwright:playwright` if seeding UI state).
3. Confirm the env vars are wired into the test environment (CI secret store / run config), **not** committed: `AUTH0_DOMAIN`, `AUTH0_AUDIENCE`, `AUTH0_M2M_CLIENT_ID/SECRET`, and for ROPG `AUTH0_ROPG_CLIENT_ID`, `AUTH0_TEST_USERNAME/PASSWORD`, `AUTH0_REALM`.
4. Generate `Auth0Config.java`, `CachedTokenProvider.java` + the two providers, `Tokens.java`, plus the consumer wiring (API client header and/or Playwright state seeder).
5. Run the cache unit tests anywhere (offline); run the live token tests with the secrets present.

## Cross-references

- **`qa/typescript/skills/auth0-test-tokens`** (`auth0` npm `AuthenticationClient`), **`qa/dotnet/skills/auth0-test-tokens`** (`Auth0.AuthenticationApi` `GetTokenAsync`) — the sibling stacks; same three grants, same cache + stash shape.
- **`auth/_shared/auth0-concepts`** — the entity/flow model (Tenant / Application / API / audience / grant types) this skill assumes.
- **`auth/auth0-java`** — the **app-side** login flow (Spring Security resource server) this skill complements. This skill never implements user-facing login; that does.
- **`qa/java/skills/api-test-author/generator`** — the M2M consumer: where the `Bearer` header lands on the RestAssured client.
- **`qa/java/skills/ui-test-author/playwright`** — the ROPG consumer: storage-state / fixture patterns for seeding auth without the login UI.
- **`qa/java/skills/test-data-builder`** — provisioning/seeding the test users that ROPG authenticates as.
- **`qa/java/skills/ci-pipelines/github-actions`** — where the Auth0 secrets are sourced in CI (OIDC / encrypted secrets), never hardcoded.
