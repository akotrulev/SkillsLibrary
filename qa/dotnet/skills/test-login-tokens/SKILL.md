---
name: qa-test-login-tokens-dotnet
description: Use when the user asks to obtain Auth0 access tokens *for automated tests* in .NET (NUnit). Triggers: "get an Auth0 M2M token for my .NET API tests", "log in a test user without the UI in C#", "mint an Auth0 token for a test user". Do NOT use for Auth0 in the app itself (`auth-auth0-concepts`) or UI login journeys (`qa-ui-test-writer-playwright-dotnet`).
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

- An API-test suite (`qa/dotnet/skills/api-test-author/writer`) needs a `Bearer` token to call protected endpoints → **M2M**
- A UI suite needs to skip the login form by seeding an authenticated browser session → **ROPG** → `StorageState`
- You need a token *as a particular seeded test user* (with that user's roles/permissions) → **ROPG**
- A CLI/headless tool or a device without a browser needs to authenticate → **device-code**
- You're re-fetching a token on every test and want to cache it correctly

## When NOT to use

- Wiring Auth0 into the **application under test** (auth middleware, JWT validation, login redirect) → `backend/dotnet/skills/auth0` / `auth/auth0-blazor`
- Understanding the Auth0 entity/flow model conceptually → `auth/_shared/auth0-concepts`
- TypeScript or JVM test suites → `qa/{typescript,java}/skills/test-login-tokens`

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
| Consumer | `qa/dotnet/skills/api-test-author/writer` | `qa/dotnet/skills/ui-test-author/playwright` `StorageState` | rarely in CI; tooling |

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

## Deep-dive reference

These sections live in `references/details.md` — **read it when the task touches them**: **Templates**.

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
- `ClientSecret`, test-user passwords, `AUTH0_DOMAIN`, `AUTH0_AUDIENCE`, `Realm` via **env vars only**, read **lazily** (methods, not static field initializers). Never logged, never committed. In CI, source them per `qa/cicd/dotnet/skills/ci-pipelines`.
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
5. Run the cache unit tests anywhere (offline); run the live token tests with the secrets present. Inside a plan task marked `Gate: none`, run none of this and report the files as "written, not run".

## Cross-references

- **`qa/typescript/skills/test-login-tokens`** (`auth0` npm `AuthenticationClient`), **`qa/java/skills/test-login-tokens`** (`com.auth0:auth0` `AuthAPI`) — the sibling stacks; same three grants, same cache + stash shape.
- **`auth/_shared/auth0-concepts`** — the entity/flow model (Tenant / Application / API / audience / grant types) this skill assumes.
- **`backend/dotnet/skills/auth0`**, **`auth/auth0-blazor`** — the **app-side** login flows this skill complements. This skill never implements user-facing login; those do.
- **`qa/dotnet/skills/api-test-author/writer`** — the M2M consumer: where the `Bearer` header lands on the API client.
- **`qa/dotnet/skills/ui-test-author/playwright`** — the ROPG consumer: `StorageState` / fixture patterns for seeding auth without the login UI.
- **`qa/dotnet/skills/test-data-builder`** — provisioning/seeding the test users that ROPG authenticates as.
- **`qa/cicd/dotnet/skills/ci-pipelines`** — where the Auth0 secrets are sourced in CI (OIDC / encrypted secrets), never hardcoded.
