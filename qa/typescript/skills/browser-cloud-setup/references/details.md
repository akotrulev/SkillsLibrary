# Deep-dive details — `qa-browser-cloud-setup-typescript`

Sections moved out of SKILL.md for on-demand loading. Read what the task needs.

## Patterns

### Secrets first — never in code or committed config

Credentials are a username + an access key per vendor. They are read from **env vars only** and never logged. A leaked access key is a billable, exfiltratable secret (CLAUDE.md hard rule). Sauce has no implicit region, so its region is read explicitly.

```typescript
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
  region: required('SAUCE_REGION'),
});
export const lambdatest = () => ({
  username: required('LT_USERNAME'),
  accessKey: required('LT_ACCESS_KEY'),
});
```

`tests/support/grid/credentials.ts`. In CI these env vars come from the runner's secret store; for cloud auth (e.g. an OIDC-minted token used to reach AWS Device Farm) prefer OIDC over a long-lived PAT — see `qa/cicd/typescript/skills/ci-pipelines`.

### Web — the BrowserStack endpoint, with the installed Playwright version

The only thing that changes vs a local run is the **connection**: instead of launching a local browser, Playwright connects to the grid's WebSocket endpoint with caps embedded as a URL-encoded JSON `caps` query param. **Flat caps** for BrowserStack Playwright direct-connect (not `bstack:options`). The client version cap is read from the installed `@playwright/test/package.json`, never typed in, so a Playwright upgrade can never leave the grid on a different version.

```typescript
import { createRequire } from 'node:module';
import { join } from 'node:path';
import { browserstack } from './credentials';

export type GridTarget = {
  readonly browser: 'chrome' | 'playwright-firefox' | 'playwright-webkit';
  readonly os: string;
  readonly osVersion: string;
  readonly buildName: string;
  readonly sessionName: string;
  readonly projectName: string;
};

const requireFromRoot = createRequire(join(process.cwd(), 'package.json'));
export const playwrightVersion: string = requireFromRoot('@playwright/test/package.json').version;

export function browserStackEndpoint(target: GridTarget): string {
  const { userName, accessKey } = browserstack();
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
    'client.playwrightVersion': playwrightVersion,
  };
  return `wss://cdp.browserstack.com/playwright?caps=${encodeURIComponent(JSON.stringify(caps))}`;
}
```

`tests/support/grid/playwrightConnect.ts`. `createRequire` from the project root works whether the suite compiles to CommonJS or ESM.

### Web — route 1: `use.connectOptions` (no fixture code)

`connectOptions` is a built-in test option: when a project sets it, Playwright's worker-scoped `browser` fixture **connects** to the endpoint instead of launching, once per worker, and every test still gets its own `context` and `page`. Specs, page objects and the writer's fixtures do not change.

```typescript
import { defineConfig, devices } from '@playwright/test';
import { browserStackEndpoint } from './tests/support/grid/playwrightConnect';

const buildName = process.env.BUILD_NAME ?? 'local-build';

export default defineConfig({
  workers: Number(process.env.GRID_CONCURRENCY ?? 5),
  use: {
    baseURL: process.env.BASE_URL,
    trace: 'retain-on-failure',
    video: 'retain-on-failure',
    screenshot: { mode: 'only-on-failure', fullPage: true },
  },
  projects: [
    {
      name: 'browserstack-chrome-win11',
      use: {
        ...devices['Desktop Chrome'],
        connectOptions: {
          wsEndpoint: browserStackEndpoint({
            browser: 'chrome', os: 'Windows', osVersion: '11',
            buildName, sessionName: 'checkout-web chrome', projectName: 'checkout-web',
          }),
        },
      },
    },
  ],
});
```

The grid holds one session per worker, so the dashboard groups by build and session name. `connectOptions` cannot mark that session's verdict; a suite that must mark it uses route 2. Playwright's own trace, video and screenshot are still recorded client-side under `test-results/` (`qa/typescript/skills/evidence-capture`).

### Web — route 2: a worker-scoped `browser` override that marks the session

Override the built-in worker-scoped `browser` fixture when the grid session must carry a verdict, or the endpoint is built per worker. One connection per worker — never a `connect()` inside a test-scoped fixture, which opens a billable grid session per test.

```typescript
import { test as base, type Browser, type Page } from '@playwright/test';
import { browserStackEndpoint } from './playwrightConnect';

async function executor(page: Page, command: object): Promise<string> {
  return page.evaluate(() => {}, `browserstack_executor: ${JSON.stringify(command)}`);
}

async function markSession(browser: Browser, failures: readonly string[]): Promise<void> {
  const page = await browser.newPage();
  const status = failures.length === 0 ? 'passed' : 'failed';
  const reason = failures.length === 0 ? 'every test passed' : `failed: ${failures.join(', ')}`;
  await executor(page, { action: 'setSessionStatus', arguments: { status, reason } });
  await page.close();
}

async function sessionUrl(page: Page): Promise<string> {
  const details: { hashed_id: string } = JSON.parse(await executor(page, { action: 'getSessionDetails' }));
  return `https://automate.browserstack.com/dashboard/v2/sessions/${details.hashed_id}`;
}

export const test = base.extend<{ gridEvidence: void }, { gridFailures: string[] }>({
  gridFailures: [
    async ({}, use) => {
      await use([]);
    },
    { scope: 'worker' },
  ],
  browser: [
    async ({ playwright, gridFailures }, use, workerInfo) => {
      const browser = await playwright.chromium.connect(
        browserStackEndpoint({
          browser: 'chrome', os: 'Windows', osVersion: '11',
          buildName: process.env.BUILD_NAME ?? 'local-build',
          sessionName: `${workerInfo.project.name} worker ${workerInfo.workerIndex}`,
          projectName: 'checkout-web',
        }),
      );
      await use(browser);
      await markSession(browser, gridFailures);
      await browser.close();
    },
    { scope: 'worker' },
  ],
  gridEvidence: [
    async ({ page, gridFailures }, use, testInfo) => {
      await use();
      if (testInfo.status !== testInfo.expectedStatus) {
        gridFailures.push(testInfo.title);
        await testInfo.attach('BrowserStack session', { body: await sessionUrl(page), contentType: 'text/uri-list' });
      }
    },
    { auto: true },
  ],
});

export { expect } from '@playwright/test';
```

`tests/support/grid/gridFixture.ts`. The worker teardown marks the session once, with every failed title; the auto fixture records a failure and attaches the session URL to that test, while its page is still open. The attachment is awaited and reaches the HTML report and Allure; an Allure-only link is `await allure.link(url, 'BrowserStack session')` with `import * as allure from 'allure-js-commons'` (`qa/reporting/typescript/skills/test-reports`).

> The `browserstack-node-sdk` is the lower-ceremony alternative: `npm i -D browserstack-node-sdk`, add a `browserstack.yml` (W3C-style `userName`/`accessKey`/`platforms[]`/`buildName`/`projectName`/`browserStackLocal`/`parallelsPerPlatform`), and run your **unmodified** command prefixed — `npx browserstack-node-sdk npx playwright test`. The SDK instruments the connection, manages the Local tunnel, and reports status. Prefer it when you don't need control over the connection.

### Web — Sauce Labs (`saucectl`) and LambdaTest

**Sauce has no public ad-hoc Playwright `connect`** — you drive it with `saucectl` and a `.sauce/config.yml`, which uploads and runs the project in Sauce's cloud. `region` is mandatory and explicit; `concurrency` is the plan's session cap; `version: package.json` makes Sauce run the installed Playwright.

```yaml
apiVersion: v1alpha
kind: playwright
sauce:
  region: us-west-1
  concurrency: 5
playwright:
  version: package.json
suites:
  - name: checkout-web
    platformName: "Windows 11"
    params: { browserName: chromium }
```

LambdaTest mirrors BrowserStack's connect model: `wss://cdp.lambdatest.com/playwright?capabilities=<encoded LT:Options + browser caps>`, set as `connectOptions.wsEndpoint` or built in the `browser` override. The capability block is `LT:Options` (see § Capability blocks), and its client version cap comes from the same `playwrightVersion`.

### Mobile — WebdriverIO + Appium on a grid

For mobile the change is also one place — `wdio.conf.ts`. Set `user`/`key` at the root, add the vendor **service** (which manages the tunnel and reports status from the results), map the plan cap onto `maxInstances`, and nest the grid caps under `bstack:options`. The app is the `bs://` id of a prior upload, never a path. The page objects from `qa/typescript/skills/ui-test-author/appium` run unchanged; the WebdriverIO and Appium versions are that skill's.

```typescript
import { browserstack } from './tests/support/grid/credentials';

const bs = browserstack();

export const config: WebdriverIO.Config = {
  user: bs.userName,
  key: bs.accessKey,
  hostname: 'hub-cloud.browserstack.com',
  services: [['browserstack', { browserstackLocal: true, testObservability: true }]],
  maxInstances: Number(process.env.GRID_CONCURRENCY ?? 5),
  capabilities: [{
    platformName: 'android',
    'appium:automationName': 'UiAutomator2',
    'appium:app': process.env.BS_APP_URL,
    'bstack:options': {
      deviceName: 'Google Pixel 8',
      osVersion: '14.0',
      buildName: process.env.BUILD_NAME ?? 'local-build',
      sessionName: 'authentication',
      projectName: 'checkout-mobile',
      networkLogs: true,
      debug: true,
      local: true,
    },
  }],
};
```

`wdio.conf.ts` (excerpt). For Sauce swap the service for `['sauce']` + `region`; the hub is `ondemand.<region>.saucelabs.com`. For LambdaTest use `mobile-hub.lambdatest.com` and the `LT:Options` block. The `@wdio/*-service` packages handle session status automatically — for the manual case see § Session status.

### Capability blocks — the three schemas

Pinning the right keys matters — vendors renamed them off the legacy JSON-Wire names. All three nest vendor-specifics under one object; standard W3C keys (`browserName`, `platformName`) stay flat alongside.

```typescript
import { browserstack, lambdatest, sauce } from './credentials';

export const bstackOptions = (build: string, session: string) => ({
  ...browserstack(),
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
  ...lambdatest(),
  build, name, project: 'checkout',
  platformName: 'Windows 11', network: true, video: true, console: true, w3c: true,
});
```

`tests/support/grid/capabilities.ts`.

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

The grid plan has a hard **concurrent-session limit**. Exceeding it queues or rejects sessions; mismatching it to the runner wastes paid slots. With a session per worker (both web routes), `workers` **is** the session count: set it from one env var, `GRID_CONCURRENCY`, as the route 1 config does — never a literal — so CI and local agree. For WDIO it's `maxInstances` (shown above). The **sharding mechanics** (matrix fan-out, `--shard`, merging blob reports) belong to `qa/cicd/typescript/skills/ci-pipelines` — cross-link it; don't re-derive it here. The rule: `total runner shards × workers-per-shard ≤ plan session cap`.

### Artifacts — surface the session URL on failure

The grid records video, network, and console logs server-side; the value is surfacing the **dashboard session URL** in the report so a failure is one click from the replay. Route 2's `gridEvidence` fixture attaches it to every failed test (BrowserStack's `getSessionDetails` executor returns the session's `hashed_id`). Playwright's own trace, video and screenshot are recorded client-side as on a local run, so a failed grid test carries both. Every attach and every Allure call is awaited; the deprecated `allure` export of `allure-playwright` is never used.

### Session status — tell the vendor the verdict

The grid doesn't know your assertions passed; you tell it, so the dashboard reflects reality and analytics stay accurate. **Each vendor's syntax differs and is not interchangeable.** For Playwright on BrowserStack, route 2's `markSession` sends `setSessionStatus` through `page.evaluate` once per worker session. For WebdriverIO the `@wdio/browserstack-service` / `@wdio/sauce-service` do this automatically from the test result. For the manual WDIO/Selenium case:
- **BrowserStack**: `driver.execute('browserstack_executor: ' + JSON.stringify({ action: 'setSessionStatus', arguments: { status: 'passed', reason } }))`
- **Sauce**: `driver.execute('sauce:job-result=passed')` (or `failed`)
- **LambdaTest**: `driver.execute('lambda-status=passed')` (or the `lambda-hook:` form with a remark)

### Local tunnel — reach private/staging URLs from the grid

When the app under test is on a private/staging host the grid can't reach, start a **tunnel** before the suite and stop it after. The tunnel binds the grid sessions to your network; tie sessions to it via the cap (`local`+`localIdentifier` / `tunnelName`).

```typescript
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

`tests/support/grid/tunnel.ts`. `globalSetup` starts the tunnel and **returns its teardown**: Playwright runs the returned function after the last test, so the instance that stops is the one that started. A separate `globalTeardown` file would construct a second, never-started tunnel.

```typescript
import { GridTunnel } from './tests/support/grid/tunnel';

export default async function globalSetup(): Promise<() => Promise<void>> {
  const tunnel = new GridTunnel(process.env.BUILD_NAME ?? 'local-build');
  await tunnel.start();
  return () => tunnel.stop();
}
```

`global-setup.ts`, named by `globalSetup: './global-setup.ts'` in the config. Match the `localIdentifier` to the cap (`bstack:options.localIdentifier`). For **Sauce** the binary is **Sauce Connect 5** (`sc run --region us-west-1 --tunnel-name my-tunnel`), tied via `sauce:options.tunnelName`. For **LambdaTest** it's `LT --user … --key … --tunnelName …`, tied via `LT:Options.tunnel`+`tunnelName`. Never pass the key as a literal — read it from env.

### AWS Device Farm — the different paradigm

Device Farm is **not a caps-on-a-hub grid**. You upload the app + a test package to a **project ARN**, then `aws devicefarm schedule-run` against a **device-pool ARN**. For live/client-side Appium, create a remote-access session and read the `remoteDriverEndpoint` from `GetRemoteAccessSession`; for desktop browsers, the TestGrid APIs mint a short-lived signed Selenium URL you hand to a remote driver. The wiring is AWS-SDK calls, not capability JSON. For the full device-pool/ARN orchestration defer to `qa/typescript/skills/device-cloud`; this node covers only the connection shape.
