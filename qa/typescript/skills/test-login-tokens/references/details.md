# Deep-dive details — `qa-typescript:test-login-tokens`

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

export const auth0Config = {
  domain: process.env.AUTH0_DOMAIN ?? 'yourco-dev.eu.auth0.com',
  audience: process.env.AUTH0_AUDIENCE ?? 'https://api.flexinvest.test',
  realm: process.env.AUTH0_REALM ?? 'Username-Password-Authentication',
} as const;

export const auth0Secrets = {
  m2mClientId: () => required('AUTH0_M2M_CLIENT_ID'),
  m2mClientSecret: () => required('AUTH0_M2M_CLIENT_SECRET'),
  ropgClientId: () => required('AUTH0_ROPG_CLIENT_ID'),
  ropgClientSecret: () => process.env.AUTH0_ROPG_CLIENT_SECRET,
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

const SKEW_MS = 60_000;

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

export class TestUserTokenProvider extends CachedTokenProvider {
  private readonly client = new AuthenticationClient({
    domain: auth0Config.domain,
    clientId: auth0Secrets.ropgClientId(),
    clientSecret: auth0Secrets.ropgClientSecret(),
  });

  protected async fetchToken() {
    const { username, password } = auth0Secrets.testUser();
    const { data } = await this.client.oauth.passwordGrant({
      username,
      password,
      audience: auth0Config.audience,
      scope: 'openid profile email',
      realm: auth0Config.realm,
    });
    return { accessToken: data.access_token, expiresInSec: data.expires_in };
  }
}
```

### Shared, suite-wide singletons — `tests/integration/auth/tokens.ts`

One token per suite/worker, **not per test**. Export ready-made singletons so specs never construct a provider or fetch directly.

```ts
import { M2MTokenProvider, TestUserTokenProvider } from './token-provider';

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

### Seed Playwright auth state from a token — a setup project

Mint a token as the test user, put it where the SPA reads it, check the app is signed in, and save the state once
for every test — **token in → state file out → reused by every test**, no login form. It is a **setup project**,
the model `qa/typescript/skills/ui-test-author/playwright` teaches (`references/config-and-fixtures.md` §3):
it shows in the report, gets fixtures and a trace, and its origin is the config's `baseURL` (from `BASE_URL`),
never a URL typed into the file. The writer's config already runs `*.setup.ts` as the `setup` project and starts
the browser projects from `authFile`; this file is a second `*.setup.ts` beside (or instead of) its UI sign-in.

```ts
import { authFile, expect, test as setup } from './fixtures';
import { testUserTokens } from './integration/auth/tokens';

const TOKEN_KEY = 'flexinvest.accessToken';

function tokenState(baseURL: string | undefined, accessToken: string) {
  if (baseURL === undefined) {
    throw new Error('baseURL is not set: export BASE_URL before seeding the signed-in state');
  }
  return {
    cookies: [],
    origins: [{ origin: new URL(baseURL).origin, localStorage: [{ name: TOKEN_KEY, value: accessToken }] }],
  };
}

setup('Should_StoreSignedInState_When_TestUserTokenIsSeeded', async ({ context, baseURL, homePage }) => {
  const accessToken = await testUserTokens.getAccessToken();
  await context.setStorageState(tokenState(baseURL, accessToken));

  await homePage.goto();

  await expect(homePage.greeting).toBeVisible();
  await context.storageState({ path: authFile });
});
```

`tests/token.setup.ts`. `context.setStorageState(state)` [1.59] loads the token into the setup test's own context
without a new one; the greeting proves the app accepted it before the state is saved. Shape `TOKEN_KEY` and the
value to whatever your SPA reads on boot. On a project below 1.59, write the same object to `authFile` with
`fs.writeFile` and let the dependent projects load it — that skips the check, so the first UI test is the check.

**What a storage state can and cannot carry:**

| Where the app keeps the token | Storage state | Do this |
|---|---|---|
| Cookies, `localStorage` | saved and restored | the setup project above |
| IndexedDB (Firebase Auth and similar) | only with `context.storageState({ path: authFile, indexedDB: true })` [1.51] | add `indexedDB: true` to the save |
| `sessionStorage` | **never saved** | a fixture that re-seeds it with `context.addInitScript(...)` before the app boots, from a value the setup wrote to its own file |
| Memory only (auth0-spa-js's default `cacheLocation: 'memory'`) | nothing to save | the UI sign-in setup (`assets/auth.setup.ts`), or a test build that sets `cacheLocation: 'localstorage'` |

- One setup test and one state file per identity (`user.json`, `admin.json`), each feeding its own project.
- `context.setStorageState(...)` [1.59] also switches identity **inside** a test — a fixture that loads
  `admin.json` into the current context — without opening a second context.
- The state file holds a live token: `playwright/.auth/` is git-ignored, and the token's `expires_in` must
  outlast the run. A suite longer than the token lifetime re-runs the setup per shard, not per test.

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

const waitInterval = (sec: number) => new Promise((r) => setTimeout(r, sec * 1000));

export async function getDeviceToken(): Promise<string> {
  const clientId = auth0Secrets.ropgClientId();
  const flow = await startDeviceFlow(clientId);
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
    if (body.error === 'authorization_pending') continue;
    if (body.error === 'slow_down') { interval += 5; continue; }
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
    now = 30 * 60 * 1000;
    expect(await p.getAccessToken()).toBe('tok-1');
    expect(p.fetches).toBe(1);
  });

  it('Should_RefetchToken_When_PastExpiryMinusSkew', async () => {
    let now = 0;
    const p = new FakeProvider(() => now);

    expect(await p.getAccessToken()).toBe('tok-1');
    now = 3600 * 1000;
    expect(await p.getAccessToken()).toBe('tok-2');
    expect(p.fetches).toBe(2);
  });
});
```
