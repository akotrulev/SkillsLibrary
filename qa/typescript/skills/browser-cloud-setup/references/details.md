# Deep-dive details — `qa-browser-cloud-setup-typescript`

Sections moved out of SKILL.md for on-demand loading. Read what the task needs.

## Patterns

### Secrets first — never in code or committed config

Credentials are a username + an access key per vendor. They are read from **env vars only** and never logged. A leaked access key is a billable, exfiltratable secret (CLAUDE.md hard rule).

```typescript
// tests/support/grid/credentials.ts
/** Read a required env var or fail loudly — never default a credential to a literal. */
function required(name: string): string {
  const value = process.env[name];
  if (!value) throw new Error(`Missing required env var ${name} — set it in your shell or CI secret store.`);
  return value;
}

export const browserstack = () => ({
  userName: required('BROWSERSTACK_USERNAME'),
  accessKey: required('BROWSERSTACK_ACCESS_KEY'),
});
export const sauce = () => ({
  username: required('SAUCE_USERNAME'),
  accessKey: required('SAUCE_ACCESS_KEY'),
  region: process.env.SAUCE_REGION ?? 'us-west-1', // explicit — Sauce has no implicit default
});
export const lambdatest = () => ({
  username: required('LT_USERNAME'),
  accessKey: required('LT_ACCESS_KEY'),
});
```

In CI these env vars come from the runner's secret store; for cloud auth (e.g. an OIDC-minted token used to reach AWS Device Farm) prefer OIDC over a long-lived PAT — see `qa/cicd/typescript/skills/ci-pipelines`.

### Web — Playwright on BrowserStack via `chromium.connect`

The only thing that changes vs a local run is the **connection**: instead of launching a local browser, connect to the grid's WebSocket endpoint with caps embedded as a URL-encoded JSON `caps` query param. **Flat caps** for BrowserStack Playwright direct-connect (not `bstack:options`).

```typescript
// tests/support/grid/playwrightConnect.ts
import { chromium, Browser } from '@playwright/test';
import { browserstack } from './credentials';

export interface GridTarget {
  browser: 'chrome' | 'playwright-firefox' | 'playwright-webkit';
  os: string;        // 'osx' | 'Windows'
  osVersion: string; // 'Sequoia' | '11'
  buildName: string;
  sessionName: string;
  projectName: string;
}

/** Connect Playwright to BrowserStack. Returns the remote Browser; the caller manages the page. */
export async function connectBrowserStack(target: GridTarget): Promise<Browser> {
  const { userName, accessKey } = browserstack();
  // FLAT caps for Playwright direct-connect — NOT bstack:options.
  const caps = {
    browser: target.browser,
    os: target.os,
    os_version: target.osVersion,
    name: target.sessionName,
    build: target.buildName,
    project: target.projectName,
    'browserstack.username': userName,
    'browserstack.accessKey': accessKey,
    'browserstack.networkLogs': 'true',
    'browserstack.console': 'errors',
    'client.playwrightVersion': '1.x', // pin to your installed Playwright in real config
  };
  const wsEndpoint = `wss://cdp.browserstack.com/playwright?caps=${encodeURIComponent(JSON.stringify(caps))}`;
  return chromium.connect({ wsEndpoint });
}
```

Wire it into a Playwright fixture so specs stay grid-agnostic — they receive a `page`, never the grid plumbing:

```typescript
// tests/support/grid/gridFixture.ts
import { test as base, Browser } from '@playwright/test';
import { connectBrowserStack } from './playwrightConnect';
import { markSessionStatus } from './sessionStatus';

export const test = base.extend<{ gridBrowser: Browser }>({
  gridBrowser: async ({}, use, testInfo) => {
    const browser = await connectBrowserStack({
      browser: 'chrome', os: 'Windows', osVersion: '11',
      buildName: process.env.BUILD_NAME ?? 'local-build',
      sessionName: testInfo.title,
      projectName: 'checkout-web',
    });
    const page = await browser.newPage();
    await use(browser);
    // Mark the session pass/fail on the dashboard before closing (see § Session status).
    await markSessionStatus(page, testInfo.status === 'passed' ? 'passed' : 'failed', testInfo.title);
    await browser.close();
  },
});
export { expect } from '@playwright/test';
```

> The `browserstack-node-sdk` is the lower-ceremony alternative: `npm i -D browserstack-node-sdk`, add a `browserstack.yml` (W3C-style `userName`/`accessKey`/`platforms[]`/`buildName`/`projectName`/`browserStackLocal`/`parallelsPerPlatform`), and run your **unmodified** command prefixed — `npx browserstack-node-sdk npx playwright test`. The SDK instruments the connection, manages the Local tunnel, and reports status. Prefer it when you don't need per-test control over the connection.

### Web — Sauce Labs (`saucectl`) and LambdaTest

**Sauce has no public ad-hoc Playwright `connect`** — you drive it with `saucectl` and a `.sauce/config.yml`, which uploads and runs the project in Sauce's cloud. `region` is mandatory and explicit.

```yaml
# .sauce/config.yml — Sauce runs Playwright via saucectl (no connect())
apiVersion: v1alpha
kind: playwright
sauce:
  region: us-west-1          # explicit — no implicit default
  concurrency: 5             # respect the plan's session cap (see § Parallelism)
playwright:
  version: package.json      # match the installed Playwright
suites:
  - name: checkout-web
    platformName: "Windows 11"
    params: { browserName: chromium }
```

LambdaTest mirrors BrowserStack's connect model via its setup helper: `wss://cdp.lambdatest.com/playwright?capabilities=<encoded LT:Options + browser caps>`. The capability block is `LT:Options` (see § Capability blocks).

### Mobile — WebdriverIO + Appium on a grid

For mobile the change is also one place — `wdio.conf.ts`. Set `user`/`key` at the root, add the vendor **service** (which auto-manages the tunnel and reports status), and nest the grid caps under `bstack:options`. The page objects from `qa/typescript/skills/ui-test-author/appium` run unchanged.

```typescript
// wdio.conf.ts (excerpt) — WebdriverIO on BrowserStack App Automate
import { browserstack } from './tests/support/grid/credentials';
const bs = browserstack();

export const config: WebdriverIO.Config = {
  user: bs.userName,
  key: bs.accessKey,
  hostname: 'hub-cloud.browserstack.com',
  // @wdio/browserstack-service launches BrowserStackLocal and marks job status from results.
  services: [['browserstack', { browserstackLocal: true, testObservability: true }]],

  // Map the plan's concurrent-session cap onto WDIO workers (see § Parallelism).
  maxInstances: Number(process.env.GRID_CONCURRENCY ?? 5),

  capabilities: [{
    platformName: 'android',
    'appium:automationName': 'UiAutomator2',
    'appium:app': process.env.BS_APP_URL, // bs://<id> from a prior app upload — never a path
    'bstack:options': {
      deviceName: 'Google Pixel 8',
      osVersion: '14.0',
      buildName: process.env.BUILD_NAME ?? 'local-build',
      sessionName: 'authentication',
      projectName: 'checkout-mobile',
      networkLogs: true,
      debug: true,    // visual logs / screenshots
      local: true,    // route through the tunnel
    },
  }],
};
```

For Sauce swap the service for `['sauce']` + `region`; the hub is `ondemand.<region>.saucelabs.com`. For LambdaTest use `mobile-hub.lambdatest.com` and the `LT:Options` block. The `@wdio/*-service` packages handle session status automatically — for the manual case (Playwright, or raw RemoteWebDriver) see § Session status.

### Capability blocks — the three schemas

Pinning the right keys matters — vendors renamed them off the legacy JSON-Wire names. All three nest vendor-specifics under one object; standard W3C keys (`browserName`, `platformName`) stay flat alongside.

```typescript
// tests/support/grid/capabilities.ts — the per-vendor blocks, side by side
import { browserstack, sauce, lambdatest } from './credentials';

export const bstackOptions = (build: string, session: string) => ({
  ...browserstack(), // userName, accessKey
  buildName: build, sessionName: session, projectName: 'checkout',
  os: 'Windows', osVersion: '11',
  networkLogs: true, consoleLogs: 'errors', video: true, debug: true,
});

export const sauceOptions = (build: string, name: string) => {
  const { username, accessKey } = sauce();
  return { username, accessKey, build, name, tags: ['regression'],
           screenResolution: '1920x1080', extendedDebugging: true };
};

export const ltOptions = (build: string, name: string) => ({
  ...lambdatest(), // username, accessKey
  build, name, project: 'checkout',
  platformName: 'Windows 11', network: true, video: true, console: true, w3c: true,
});
```

| Concept | BrowserStack (`bstack:options`) | Sauce (`sauce:options`) | LambdaTest (`LT:Options`) |
|---|---|---|---|
| Credentials | `userName` / `accessKey` | `username` / `accessKey` | `username` / `accessKey` |
| Build group | `buildName` | `build` | `build` |
| Session label | `sessionName` | `name` | `name` |
| Project tag | `projectName` | (via `tags`) | `project` |
| Network logs | `networkLogs` | (always on) | `network` |
| Console logs | `consoleLogs` | (always on) | `console` |
| Video | `video` | (always on) | `video` |
| Tunnel | `local` + `localIdentifier` | `tunnelName` | `tunnel` + `tunnelName` |

### Parallelism — respect the plan's session cap

The grid plan has a hard **concurrent-session limit**. Exceeding it queues or rejects sessions; mismatching it to the runner wastes paid slots. Map the cap onto the runner's worker/shard count — never hard-code a number, read it from one env var so CI and local agree.

```typescript
// playwright.config.ts (excerpt)
export default defineConfig({
  // One worker per grid session slot. Set GRID_CONCURRENCY to the plan cap (e.g. 5).
  workers: Number(process.env.GRID_CONCURRENCY ?? 5),
  // ...projects, reporters
});
```

For WDIO it's `maxInstances` (shown above). The **sharding mechanics** (matrix fan-out, `--shard`, merging blob reports) belong to `qa/cicd/typescript/skills/ci-pipelines` — cross-link it; don't re-derive it here. The rule: `total runner shards × workers-per-shard ≤ plan session cap`.

### Artifacts — surface the session URL on failure

The grid records video, network, and console logs server-side; the value is surfacing the **dashboard session URL** in test output and Allure so a failure is one click from the replay. For BrowserStack the session id is the WebDriver `sessionId`; the dashboard URL is `https://automate.browserstack.com/dashboard/v2/sessions/<sessionId>` (App Automate / Playwright have parallel URLs).

```typescript
// tests/support/grid/artifacts.ts
import { allure } from 'allure-playwright';

/** Attach the vendor session URL to the report so a failing test links straight to the replay. */
export function attachSessionUrl(sessionId: string): void {
  const url = `https://automate.browserstack.com/dashboard/v2/sessions/${sessionId}`;
  allure.link(url, 'BrowserStack session');
}
```

Call this in the fixture teardown (and especially on failure). Combined with marking the session status (below), a failed run is fully diagnosable from the report without re-running locally.

### Session status — tell the vendor the verdict

The grid doesn't know your assertions passed; you tell it, so the dashboard reflects reality and analytics stay accurate. **Each vendor's syntax differs and is not interchangeable.**

```typescript
// tests/support/grid/sessionStatus.ts
import { Page } from '@playwright/test';

/** BrowserStack: a JS-executor command via page.evaluate (Playwright form). */
export async function markSessionStatus(page: Page, status: 'passed' | 'failed', reason: string): Promise<void> {
  await page.evaluate(
    () => {},
    `browserstack_executor: ${JSON.stringify({ action: 'setSessionStatus', arguments: { status, reason } })}`,
  );
}
```

For WebdriverIO the `@wdio/browserstack-service` / `@wdio/sauce-service` do this automatically from the test result. For the manual WDIO/Selenium case:
- **BrowserStack**: `driver.execute('browserstack_executor: ' + JSON.stringify({ action: 'setSessionStatus', arguments: { status: 'passed', reason } }))`
- **Sauce**: `driver.execute('sauce:job-result=passed')` (or `failed`)
- **LambdaTest**: `driver.execute('lambda-status=passed')` (or the `lambda-hook:` form with a remark)

### Local tunnel — reach private/staging URLs from the grid

When the app under test is on a private/staging host the grid can't reach, start a **tunnel** before the suite and stop it after. The tunnel binds the grid sessions to your network; tie sessions to it via the cap (`local`+`localIdentifier` / `tunnelName`).

```typescript
// tests/support/grid/tunnel.ts — BrowserStackLocal lifecycle (promisified)
import { Local } from 'browserstack-local';
import { browserstack } from './credentials';

export class GridTunnel {
  private readonly bs = new Local();
  constructor(private readonly localIdentifier: string) {}

  start(): Promise<void> {
    const { accessKey } = browserstack();
    return new Promise((resolve, reject) =>
      this.bs.start({ key: accessKey, localIdentifier: this.localIdentifier, force: true },
        (err) => (err ? reject(err) : resolve())),
    );
  }
  stop(): Promise<void> {
    return new Promise((resolve) => this.bs.stop(() => resolve()));
  }
}
```

```typescript
// global-setup.ts — start once per run, stop in teardown (no hard-coded key)
import { GridTunnel } from './tests/support/grid/tunnel';
const tunnel = new GridTunnel(process.env.BUILD_NAME ?? 'local-build');
export default async function globalSetup() { await tunnel.start(); }
// global-teardown.ts → await tunnel.stop()
```

Match the `localIdentifier` to the cap (`bstack:options.localIdentifier`). For **Sauce** the binary is **Sauce Connect 5** (`sc run --region us-west-1 --tunnel-name my-tunnel`), tied via `sauce:options.tunnelName`. For **LambdaTest** it's `LT --user … --key … --tunnelName …`, tied via `LT:Options.tunnel`+`tunnelName`. Never pass the key as a literal — read it from env.

### AWS Device Farm — the different paradigm

Device Farm is **not a caps-on-a-hub grid**. You upload the app + a test package to a **project ARN**, then `aws devicefarm schedule-run` against a **device-pool ARN**. For live/client-side Appium, create a remote-access session and read the `remoteDriverEndpoint` from `GetRemoteAccessSession`; for desktop browsers, the TestGrid APIs mint a short-lived signed Selenium URL you hand to a remote driver. The wiring is AWS-SDK calls, not capability JSON. For the full device-pool/ARN orchestration defer to `qa/typescript/skills/device-cloud`; this node covers only the connection shape.
