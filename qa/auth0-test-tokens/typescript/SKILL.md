---
name: qa-auth0-test-tokens-typescript
description: Use when the user asks to obtain Auth0 access tokens *for automated tests* in TypeScript (Vitest / Jest / Playwright) — programmatic token acquisition so suites authenticate WITHOUT driving the interactive login UI. Covers the three grants a QA org uses: Client Credentials (M2M) for API-test suites hitting protected endpoints, Resource Owner Password Grant (ROPG / `password-realm`) to mint a token *as a specific test user*, and the Device Authorization Flow for CLI/input-constrained cases — plus token caching for the token's `expires_in` lifetime and stashing it into the API client (`Authorization: Bearer`) or seeding Playwright `storageState`. Built on the `auth0` npm SDK `AuthenticationClient` (`oauth.clientCredentialsGrant` / `oauth.passwordGrant`) or bare `fetch` to `/oauth/token`. Triggers: "get an Auth0 M2M token for my API tests", "log in a test user without the UI", "mint an Auth0 token for a test user", "seed Playwright auth state from an Auth0 token", "cache the Auth0 token across the suite". Do NOT use for app-side login flows / wiring Auth0 into a running app (use `auth/auth0-react` / `auth/auth0-dotnet` / `auth/auth0-java` / `auth/auth0-blazor`), for the Auth0 concept model (use `auth/_shared/auth0-concepts`), or for the .NET / JVM stacks (`qa/auth0-test-tokens/{dotnet,java}`).
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

- An API-test suite (`qa/api-test-author/*`) needs a `Bearer` token to call protected endpoints → **M2M**
- A UI suite needs to skip the login form by seeding an authenticated browser session → **ROPG** → `storageState`
- You need a token *as a particular seeded test user* (with that user's roles/permissions) → **ROPG**
- A CLI/headless tool or a device without a browser needs to authenticate → **device-code**
- You're re-fetching a token on every test and want to cache it correctly

## When NOT to use

- Wiring Auth0 into the **application under test** (login redirect, callback handling, JWT middleware) → `auth/auth0-react` / `auth/auth0-dotnet` / `auth/auth0-java` / `auth/auth0-blazor`
- Understanding the Auth0 entity/flow model conceptually → `auth/_shared/auth0-concepts`
- Validating JWTs *inside* your backend → that's app-side; see the backend `auth/auth0-*` skills
- .NET or JVM test suites → `qa/auth0-test-tokens/{dotnet,java}`

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
| Consumer | `qa/api-test-author/*` | `qa/ui-test-author/*` `storageState` + API tests | rarely in CI; tooling |

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

## Templates

### Config — `tests/integration/auth/auth0.config.ts`

Non-secret defaults (domain, audience, realm) can have fallbacks; **secrets are read lazily** so unrelated tests don't require them.

```ts
function required(name: string): string {
  const v = process.env[name];
  if (!v) throw new Error(`Missing required env var ${name} (Auth0 test-token config).`);
  return v;
}

/** Non-secret config — safe to have defaults; no token is fetched just by importing this. */
export const auth0Config = {
  domain: process.env.AUTH0_DOMAIN ?? 'yourco-dev.eu.auth0.com',
  audience: process.env.AUTH0_AUDIENCE ?? 'https://api.flexinvest.test',
  realm: process.env.AUTH0_REALM ?? 'Username-Password-Authentication',
} as const;

/** Secrets — read lazily, only when a token is actually fetched. Never logged, never committed. */
export const auth0Secrets = {
  m2mClientId: () => required('AUTH0_M2M_CLIENT_ID'),
  m2mClientSecret: () => required('AUTH0_M2M_CLIENT_SECRET'),
  ropgClientId: () => required('AUTH0_ROPG_CLIENT_ID'),
  ropgClientSecret: () => process.env.AUTH0_ROPG_CLIENT_SECRET, // optional: only for confidential apps
  testUser: () => ({
    username: required('AUTH0_TEST_USERNAME'),
    password: required('AUTH0_TEST_PASSWORD'),
  }),
};
```

### Cached token provider — `tests/integration/auth/token-provider.ts`

One provider per grant, caching the token for its `expires_in`. Re-fetches ~60s early so a token never expires mid-test. **No sleep, no per-test fetch** — the cache is the whole point. `nowMs` is injectable so the cache logic is unit-testable without faking the clock globally.

```ts
import { AuthenticationClient } from 'auth0';
import { auth0Config, auth0Secrets } from './auth0.config';

export interface TokenSet {
  accessToken: string;
  expiresAtMs: number;
}

const SKEW_MS = 60_000; // refresh 60s before the token actually expires

/** Caches a single token for its lifetime. Subclasses supply how to fetch one. */
export abstract class CachedTokenProvider {
  private cached: TokenSet | null = null;

  constructor(protected readonly nowMs: () => number = () => Date.now()) {}

  protected abstract fetchToken(): Promise<{ accessToken: string; expiresInSec: number }>;

  async getAccessToken(): Promise<string> {
    if (this.cached && this.nowMs() < this.cached.expiresAtMs - SKEW_MS) {
      return this.cached.accessToken;
    }
    const { accessToken, expiresInSec } = await this.fetchToken();
    this.cached = { accessToken, expiresAtMs: this.nowMs() + expiresInSec * 1000 };
    return accessToken;
  }
}

/** Client Credentials (M2M) — the default for API-test suites. */
export class M2MTokenProvider extends CachedTokenProvider {
  private readonly client = new AuthenticationClient({
    domain: auth0Config.domain,
    clientId: auth0Secrets.m2mClientId(),
    clientSecret: auth0Secrets.m2mClientSecret(),
  });

  protected async fetchToken() {
    const { data } = await this.client.oauth.clientCredentialsGrant({
      audience: auth0Config.audience,
    });
    return { accessToken: data.access_token, expiresInSec: data.expires_in };
  }
}

/** Resource Owner Password Grant — a token AS a specific test user. Test-only. */
export class TestUserTokenProvider extends CachedTokenProvider {
  private readonly client = new AuthenticationClient({
    domain: auth0Config.domain,
    clientId: auth0Secrets.ropgClientId(),
    clientSecret: auth0Secrets.ropgClientSecret(), // undefined for public apps — fine
  });

  protected async fetchToken() {
    const { username, password } = auth0Secrets.testUser();
    const { data } = await this.client.oauth.passwordGrant({
      username,
      password,
      audience: auth0Config.audience,
      scope: 'openid profile email',
      realm: auth0Config.realm, // → uses the password-realm grant
    });
    return { accessToken: data.access_token, expiresInSec: data.expires_in };
  }
}
```

### Shared, suite-wide singletons — `tests/integration/auth/tokens.ts`

One token per suite/worker, **not per test**. Export ready-made singletons so specs never construct a provider or fetch directly.

```ts
import { M2MTokenProvider, TestUserTokenProvider } from './token-provider';

/** Reused across the whole worker — the token is cached inside the provider. */
export const m2mTokens = new M2MTokenProvider();
export const testUserTokens = new TestUserTokenProvider();
```

### Stash into an API client — `Authorization: Bearer`

The token reaches a protected endpoint as a header. The provider is injected (constructor injection), so a unit test can pass a fake.

```ts
import { m2mTokens } from './auth/tokens';
import type { CachedTokenProvider } from './auth/token-provider';

export class OrdersClient {
  constructor(
    private readonly baseUrl: string,
    private readonly tokens: Pick<CachedTokenProvider, 'getAccessToken'> = m2mTokens,
  ) {}

  async getOrder(id: string): Promise<Response> {
    const token = await this.tokens.getAccessToken();
    return fetch(`${this.baseUrl}/orders/${id}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
  }
}
```

### Seed Playwright auth state from a token (skip the login UI)

Mint a token as the test user, write it where the SPA expects it, save `storageState` once, and reuse it across specs. Most Auth0 SPAs read the session from `localStorage` (auth0-spa-js cache key) — adapt the key/shape to your app, or simpler: set an app-level token your app trusts. The pattern is **token in → storageState file out → reused by every test**, no login form.

```ts
// global-setup.ts — runs once before the suite
import { chromium } from '@playwright/test';
import { testUserTokens } from './tests/integration/auth/tokens';

export default async function globalSetup() {
  const token = await testUserTokens.getAccessToken();
  const browser = await chromium.launch();
  const page = await browser.newPage();

  await page.goto('https://app.flexinvest.test'); // origin must match for storage to apply
  await page.evaluate((accessToken) => {
    // Shape this to whatever your SPA reads on boot. Example: a simple app token store.
    window.localStorage.setItem('flexinvest.accessToken', accessToken);
  }, token);

  await page.context().storageState({ path: 'tests/.auth/user.json' });
  await browser.close();
}
```

```ts
// playwright.config.ts (excerpt) — every test starts already authenticated
export default {
  globalSetup: './global-setup.ts',
  use: { storageState: 'tests/.auth/user.json' },
};
```

### Device Authorization Flow — `tests/integration/auth/device-code.ts`

Niche: input-constrained clients. Start the flow, surface the `verification_uri_complete` for a human to approve, then **poll `/oauth/token` honoring the server-dictated `interval`** — wait on the endpoint's `authorization_pending` / `slow_down` responses, **never a fixed sleep**. Bare `fetch` (the SDK has no device helper).

```ts
import { auth0Config, auth0Secrets } from './auth0.config';

const TOKEN_URL = `https://${auth0Config.domain}/oauth/token`;
const DEVICE_URL = `https://${auth0Config.domain}/oauth/device/code`;

async function startDeviceFlow(clientId: string) {
  const res = await fetch(DEVICE_URL, {
    method: 'POST',
    headers: { 'content-type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
      client_id: clientId,
      scope: 'openid profile email',
      audience: auth0Config.audience,
    }),
  });
  if (!res.ok) throw new Error(`device/code failed: ${res.status}`);
  return res.json() as Promise<{
    device_code: string;
    user_code: string;
    verification_uri_complete: string;
    interval: number;
    expires_in: number;
  }>;
}

/** Wait the server-dictated interval — NOT a hardcoded sleep. */
const waitInterval = (sec: number) => new Promise((r) => setTimeout(r, sec * 1000));

export async function getDeviceToken(): Promise<string> {
  const clientId = auth0Secrets.ropgClientId(); // a "Device Code"-enabled public app
  const flow = await startDeviceFlow(clientId);
  // Surface this for approval (CI: a pre-authorized device; local: open the URL).
  console.log(`Approve at: ${flow.verification_uri_complete}`);

  const deadline = Date.now() + flow.expires_in * 1000;
  let interval = flow.interval;

  while (Date.now() < deadline) {
    await waitInterval(interval);
    const res = await fetch(TOKEN_URL, {
      method: 'POST',
      headers: { 'content-type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({
        grant_type: 'urn:ietf:params:oauth:grant-type:device_code',
        device_code: flow.device_code,
        client_id: clientId,
      }),
    });
    const body = await res.json();
    if (res.ok) return body.access_token as string;
    if (body.error === 'authorization_pending') continue; // user hasn't approved yet
    if (body.error === 'slow_down') { interval += 5; continue; } // back off per spec
    throw new Error(`device token failed: ${body.error}`);
  }
  throw new Error('Device authorization timed out before approval.');
}
```

### Vitest — M2M token reaches the API as a Bearer header

```ts
import { describe, it, expect } from 'vitest';
import { OrdersClient } from './auth/orders-client';

describe('OrdersClient with M2M auth', () => {
  it('Should_Return200_When_CalledWithM2MToken', async () => {
    const client = new OrdersClient(process.env.API_BASE_URL!);
    const res = await client.getOrder('ord_123');
    expect(res.status).toBe(200);
  });
});
```

### Vitest — the provider caches, not re-fetches (offline, fake clock)

The cache is the contract: one fetch, reused until near expiry. Inject `nowMs` and a fake `fetchToken` to prove it without the network.

```ts
import { describe, it, expect, vi } from 'vitest';
import { CachedTokenProvider } from './auth/token-provider';

class FakeProvider extends CachedTokenProvider {
  fetches = 0;
  protected async fetchToken() {
    this.fetches += 1;
    return { accessToken: `tok-${this.fetches}`, expiresInSec: 3600 };
  }
}

describe('CachedTokenProvider', () => {
  it('Should_ReuseToken_When_NotNearExpiry', async () => {
    let now = 0;
    const p = new FakeProvider(() => now);

    expect(await p.getAccessToken()).toBe('tok-1');
    now = 30 * 60 * 1000; // 30 min later, well inside the hour
    expect(await p.getAccessToken()).toBe('tok-1');
    expect(p.fetches).toBe(1); // only fetched once
  });

  it('Should_RefetchToken_When_PastExpiryMinusSkew', async () => {
    let now = 0;
    const p = new FakeProvider(() => now);

    expect(await p.getAccessToken()).toBe('tok-1');
    now = 3600 * 1000; // exactly at expiry → past expiry - 60s skew
    expect(await p.getAccessToken()).toBe('tok-2');
    expect(p.fetches).toBe(2);
  });
});
```

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
- `client_secret`, test-user passwords, `AUTH0_DOMAIN`, `AUTH0_AUDIENCE`, `realm` via **env vars only**, read **lazily** (functions, not module-top consts). Never logged, never committed. In CI, source them per `qa/ci-pipelines/github-actions/typescript`.
- Never log a token. Treat the `access_token` as a secret in flight.

### Stashing
- API tests: inject the provider into the client; add `Authorization: Bearer <token>` per request (the cache makes this cheap).
- UI tests: mint once in `globalSetup`, seed the storage your SPA reads, save `storageState`, reuse — see `qa/ui-test-author/playwright/typescript`.

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

- **`qa/auth0-test-tokens/dotnet`** (`Auth0.AuthenticationApi` `AuthenticationApiClient.GetTokenAsync`), **`qa/auth0-test-tokens/java`** (`com.auth0:auth0` `AuthAPI`) — the sibling stacks; same three grants, same cache + stash shape.
- **`auth/_shared/auth0-concepts`** — the entity/flow model (Tenant / Application / API / audience / grant types) this skill assumes. Read it to understand *why* M2M vs ROPG.
- **`auth/auth0-react`**, **`auth/auth0-dotnet`**, **`auth/auth0-java`**, **`auth/auth0-blazor`** — the **app-side** login flows this skill complements. This skill never implements user-facing login; those do.
- **`qa/api-test-author/generator/typescript`** — the M2M consumer: where the `Bearer` header lands on the API client.
- **`qa/ui-test-author/playwright/typescript`** — the ROPG consumer: `storageState` / fixture patterns for seeding auth without the login UI.
- **`qa/test-data-builder/typescript`** — provisioning/seeding the test users that ROPG authenticates as.
- **`qa/ci-pipelines/github-actions/typescript`** — where the Auth0 secrets are sourced in CI (OIDC / encrypted secrets), never hardcoded.

## Sources synthesized (research-first per CLAUDE.md)

- [auth0/node-auth0 — `AuthenticationClient`, `oauth.clientCredentialsGrant`, `oauth.passwordGrant`](https://github.com/auth0/node-auth0) — v4+ SDK surface; responses wrapped as `{ data, status, headers }`; `passwordGrant` takes `realm` to use the `password-realm` grant; set `auth0-forwarded-for` for server-side brute-force protection.
- [Call Your API Using the Device Authorization Flow — Auth0 Docs](https://auth0.com/docs/get-started/authentication-and-authorization-flow/device-authorization-flow/call-your-api-using-the-device-authorization-flow) — `POST /oauth/device/code` → `device_code`/`user_code`/`verification_uri_complete`/`interval`; poll `/oauth/token` with `grant_type=urn:ietf:params:oauth:grant-type:device_code`, handling `authorization_pending` and `slow_down` (back off by raising the interval).
- [Auth0 ROPG / `password-realm` grant enablement](https://medium.com/@tripathi_vishnu_/grant-type-password-not-allowed-for-the-client-for-resource-owner-password-flow-3751e6c4443b) — the grant must be explicitly allowed on the app; `http://auth0.com/oauth/grant-type/password-realm` realm variant; test-only posture.

## Changelog

- 2026-05-31: Authored as the canonical TypeScript skill for the auth0-test-tokens node (`qa/GAP-ANALYSIS.md` row 16, Phase 2). The bridge between `auth/auth0-*` and QA — programmatic token acquisition for tests via three grants (M2M / ROPG / device-code), a `CachedTokenProvider` honoring `expires_in` with a 60s skew, Bearer-header stash + Playwright `storageState` seeding, secrets via env read lazily, ROPG test-only caveat. TS canonical for the 3-stack node; dotnet + java ported next.
