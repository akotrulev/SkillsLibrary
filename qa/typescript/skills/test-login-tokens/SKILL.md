---
name: qa-test-login-tokens-typescript
description: Use when the user asks to obtain Auth0 access tokens *for automated tests* in TypeScript (Vitest / Jest / Playwright). Triggers: "get an Auth0 M2M token for my API tests", "log in a test user without the UI", "mint an Auth0 token for a test user". For end-to-end suite work prefer the phased agent `qa-api-typescript` / `qa-ui-typescript` / `qa-mobile-typescript` (or the matching slash command), which loads this skill inside its workflow; use this skill directly for a single targeted artifact.
---

# QA — Auth0 Test Tokens (TypeScript)

Scaffolds **programmatic Auth0 token acquisition for automated tests** in TypeScript. The goal is narrow: get a valid `access_token` into a test's API client or browser session **without driving the interactive `/authorize` login UI** on every run. This is the *test-token slice* — it complements, and does not replace, the app-side login skills in `auth/auth0-*` (which implement the real user-facing flows).

Three grants cover what a QA org actually needs:

- **Client Credentials (M2M)** — a service-to-service token with no user context. The default for API-test suites that hit protected endpoints. `grant_type=client_credentials` + `audience` + `client_id`/`client_secret`.
- **Resource Owner Password Grant (ROPG)** — mint a token *as a specific test user* (username + password) with no UI. **Test-only, and must be explicitly enabled on the tenant** (see the security caveat). This is the one that unblocks UI auth-state seeding.
- **Device Authorization Flow** — for input-constrained / CLI scenarios: get a `device_code`, then poll `/oauth/token` until the user authorizes. Lowest priority, but included for completeness.

Two cross-cutting rules shape every example:

- **Cache the token for its `expires_in` lifetime.** Fetch once per suite/worker, reuse until ~60s before expiry, then re-fetch. **Never** fetch a token per test. Never sleep-poll.
- **Secrets only via env, read lazily.** `client_secret`, test-user passwords, `AUTH0_DOMAIN`, `audience` come from env vars (CLAUDE.md hard rule). Never logged, never committed, never read at module top-level.

## When to use

- An API-test suite (`qa/typescript/skills/api-test-author/*`) needs a `Bearer` token to call protected endpoints → **M2M**
- A UI suite needs to skip the login form by seeding an authenticated browser session → **ROPG** → `storageState`
- You need a token *as a particular seeded test user* (with that user's roles/permissions) → **ROPG**
- A CLI/headless tool or a device without a browser needs to authenticate → **device-code**
- You're re-fetching a token on every test and want to cache it correctly

## When NOT to use

- Wiring Auth0 into the **application under test** (login redirect, callback handling, JWT middleware) → `auth/auth0-react` / `backend/dotnet/skills/auth0` / `backend/java/skills/auth0` / `auth/auth0-blazor`
- Understanding the Auth0 entity/flow model conceptually → `auth/_shared/auth0-concepts`
- Validating JWTs *inside* your backend → that's app-side; see the backend `auth/auth0-*` skills
- .NET or JVM test suites → `qa/{dotnet,java}/skills/test-login-tokens`

## Decision matrix — which grant for which test

| | **Client Credentials (M2M)** | **ROPG (`password-realm`)** | **Device Authorization** |
|---|---|---|---|
| User context? | **None** — token represents a *service* | **A specific test user** (their roles/perms) | A specific user (interactive consent once) |
| Serves which test | API tests against protected endpoints | UI auth-state seeding; per-user API tests | CLI / TV / input-constrained clients |
| `grant_type` | `client_credentials` | `password` or `http://auth0.com/oauth/grant-type/password-realm` | `urn:ietf:params:oauth:grant-type:device_code` |
| Credentials | `client_id` + `client_secret` | M2M-ish app + **username + password** | `client_id` (public) |
| Tenant config | M2M app authorized for the API | **ROPG grant enabled** on the app + a DB `realm` | Device Code grant enabled; "Device" app |
| Interactivity | None | None | One-time browser approval per device code |
| Security caveat | Standard; keep the secret in env | **Test-only — never production**; needs a real password | Approval step can't be fully headless |
| Consumer | `qa/typescript/skills/api-test-author/*` | `qa/typescript/skills/ui-test-author/*` `storageState` + API tests | rarely in CI; tooling |

**Default to M2M** for API suites. Reach for **ROPG** only when the test genuinely needs *this user's* identity (their permissions, their data). Use **device-code** only for the niche input-constrained case.

## Inputs needed

Ask at most 2–3; infer the rest from `package.json` and existing fixtures.

1. Which grant(s)? (M2M for API tests / ROPG for a test user / device-code) — default M2M.
2. The API **audience** identifier and the **tenant domain** — and for ROPG, the test-user credentials + the connection **realm** (e.g. `Username-Password-Authentication`).
3. Where do the secrets come from in this environment (CI secret store, `.env.test`)? Confirm they are **not** committed.

## Auth0 SDK surface (cheat-sheet — `auth0` npm, `AuthenticationClient`)

| Call | Purpose |
|---|---|
| `new AuthenticationClient({ domain, clientId, clientSecret })` | Injectable auth client. `clientSecret` only for confidential grants (M2M, ROPG with a confidential app). |
| `await client.oauth.clientCredentialsGrant({ audience })` | **M2M** token. Returns `{ data: { access_token, expires_in, token_type, ... } }`. |
| `await client.oauth.passwordGrant({ username, password, audience, scope, realm })` | **ROPG**. With `realm` the SDK uses the `password-realm` grant; without it, plain `password`. |
| `client.oauth.*` responses | The v4+ SDK wraps responses as `{ data, status, headers }` — read `response.data.access_token`. |
| Bare `fetch('https://{domain}/oauth/token', { method: 'POST', ... })` | For **device-code** (poll loop) and when you'd rather not add the SDK. Body is `application/json` or form-encoded. |
| `POST /oauth/device/code` | Start device flow → `{ device_code, user_code, verification_uri_complete, interval, expires_in }`. |

The `/oauth/token` JSON response for all grants: `{ access_token, expires_in, token_type: 'Bearer', scope?, refresh_token? }`. Device-code polling returns `403` with `{ error: 'authorization_pending' }` (keep waiting) or `{ error: 'slow_down' }` (increase the interval) until the user approves.

## Deep-dive reference

These sections live in `references/details.md` — **read it when the task touches them**: **Templates**.

## Rules

### Grant choice
- **M2M is the default for API suites.** It has no user context — use it whenever the test doesn't need a *specific* user's identity.
- Use **ROPG** only when the test needs *this test user's* roles/permissions/data. It is **test-only** — see the security caveat.
- Use **device-code** only for input-constrained clients; it can't be made fully non-interactive (approval step).

### ROPG security caveat (call out once, loudly)
- ROPG (`password`/`password-realm`) sends a username+password to the token endpoint. It **must be explicitly enabled** on the Auth0 app's grant types and is **for test tenants only** — never production. It bypasses MFA and brute-force protections by design. Use a dedicated **test tenant** with **seeded test users**, never real customer credentials.

### Caching & expiry
- Fetch a token **once per suite/worker** and cache it for `expires_in`. Refresh ~60s early (skew). Never fetch per test.
- **Never sleep-poll.** For device-code, wait the server-dictated `interval` and back off on `slow_down`; for everything else there's nothing to poll — you have the token or an error.
- One token per worker — in parallel runs each worker gets its own cached token; that's fine and avoids contention.

### Secrets
- `client_secret`, test-user passwords, `AUTH0_DOMAIN`, `AUTH0_AUDIENCE`, `realm` via **env vars only**, read **lazily** (functions, not module-top consts). Never logged, never committed. In CI, source them per `qa/cicd/typescript/skills/ci-pipelines`.
- Never log a token. Treat the `access_token` as a secret in flight.

### Stashing
- API tests: inject the provider into the client; add `Authorization: Bearer <token>` per request (the cache makes this cheap).
- UI tests: mint once in `globalSetup`, seed the storage your SPA reads, save `storageState`, reuse — see `qa/typescript/skills/ui-test-author/playwright`.

### What NOT to do
- No token fetch per test, no uncached `clientCredentialsGrant` in a loop.
- No `Thread.Sleep`-equivalent fixed `setTimeout` waits except the *server-dictated* device-code interval.
- No ROPG against a production tenant or with real user credentials.
- No secret or token in source, logs, or committed fixtures.
- No reading secrets at import time — it breaks tests that don't need them.

## Generation steps

1. Read `package.json` (Vitest vs Jest; Playwright present?) and existing `tests/` fixtures for house style.
2. Confirm `auth0` is installed (`npm i -D auth0`) — or decide on bare `fetch` if you'd rather not add it.
3. Confirm the env vars are wired into the test environment (CI secret store / `.env.test`), **not** committed: `AUTH0_DOMAIN`, `AUTH0_AUDIENCE`, `AUTH0_M2M_CLIENT_ID/SECRET`, and for ROPG `AUTH0_ROPG_CLIENT_ID`, `AUTH0_TEST_USERNAME/PASSWORD`, `AUTH0_REALM`.
4. Generate `auth0.config.ts`, `token-provider.ts`, `tokens.ts`, plus the consumer wiring (API client header and/or Playwright `globalSetup`).
5. Run the cache unit test anywhere (offline); run the live token tests with the secrets present.

## Cross-references

- **`qa/dotnet/skills/test-login-tokens`** (`Auth0.AuthenticationApi` `AuthenticationApiClient.GetTokenAsync`), **`qa/java/skills/test-login-tokens`** (`com.auth0:auth0` `AuthAPI`) — the sibling stacks; same three grants, same cache + stash shape.
- **`auth/_shared/auth0-concepts`** — the entity/flow model (Tenant / Application / API / audience / grant types) this skill assumes. Read it to understand *why* M2M vs ROPG.
- **`auth/auth0-react`**, **`backend/dotnet/skills/auth0`**, **`backend/java/skills/auth0`**, **`auth/auth0-blazor`** — the **app-side** login flows this skill complements. This skill never implements user-facing login; those do.
- **`qa/typescript/skills/api-test-author/writer`** — the M2M consumer: where the `Bearer` header lands on the API client.
- **`qa/typescript/skills/ui-test-author/playwright`** — the ROPG consumer: `storageState` / fixture patterns for seeding auth without the login UI.
- **`qa/typescript/skills/test-data-builder`** — provisioning/seeding the test users that ROPG authenticates as.
- **`qa/cicd/typescript/skills/ci-pipelines`** — where the Auth0 secrets are sourced in CI (OIDC / encrypted secrets), never hardcoded.
