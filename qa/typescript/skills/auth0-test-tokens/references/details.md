# Deep-dive details — `qa-auth0-test-tokens-typescript`

Sections moved out of SKILL.md for on-demand loading. Read what the task needs.

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
