---
name: qa-auth0-test-tokens-java
description: Use when the user asks to obtain Auth0 access tokens *for automated tests* in Java (TestNG). Triggers: "get an Auth0 M2M token for my RestAssured tests", "log in a test user without the UI in Java", "mint an Auth0 token for a test user".
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

## Deep-dive reference

These sections live in `references/details.md` — **read it when the task touches them**: **Templates**.

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
- `clientSecret`, test-user passwords, `AUTH0_DOMAIN`, `AUTH0_AUDIENCE`, `realm` via **env vars only**, read **lazily** (methods, not static field initializers). Never logged, never committed. In CI, source them per `qa/java/skills/ci-pipelines`.
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
- **`qa/java/skills/ci-pipelines`** — where the Auth0 secrets are sourced in CI (OIDC / encrypted secrets), never hardcoded.
