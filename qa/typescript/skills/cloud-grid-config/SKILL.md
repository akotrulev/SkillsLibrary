---
name: qa-cloud-grid-config-typescript
description: Use when the user needs to run TypeScript Playwright (web) or WebdriverIO/Appium (mobile) tests on a **hosted cloud grid** — BrowserStack, Sauce Labs, LambdaTest, or AWS Device Farm — instead of local browsers/emulators. Covers: Playwright cloud connect (`chromium.connect({ wsEndpoint })` to `cdp.browserstack.com/playwright`, or the `browserstack-node-sdk` / `saucectl` path), WebdriverIO grid services (`@wdio/browserstack-service` / `@wdio/sauce-service`), vendor capability blocks (`bstack:options` / `sauce:options` / `LT:Options`), build/session/project tagging, **parallelism caps** mapped onto Playwright `workers` / WDIO `maxInstances`, **artifacts** (video, network/console logs, the session dashboard URL surfaced on failure), **secret handling** (user + access key via env/OIDC, never committed), **local tunnels** (BrowserStackLocal / Sauce Connect 5 / LambdaTest Tunnel start-stop), and **marking the session pass/fail** back to the vendor. Triggers: "run our Playwright tests on BrowserStack", "wire WebdriverIO to Sauce Labs", "set up LambdaTest caps for our Appium TS tests", "connect Playwright to a cloud grid in TypeScript", "add a BrowserStackLocal tunnel to our TS suite". Do NOT use for the .NET grid stack (use `qa/dotnet/skills/cloud-grid-config`), the Java grid stack (use `qa/java/skills/cloud-grid-config`), writing the page objects / specs themselves (use `qa/typescript/skills/ui-test-author/playwright` or `qa/typescript/skills/ui-test-author/appium`), CI shard mechanics (use `qa/typescript/skills/ci-pipelines/*`), or deep mobile-farm device-pool specifics (use `qa/typescript/skills/mobile-device-farm`).
---

# QA — Cloud Grid Config (TypeScript: Playwright + WebdriverIO/Appium)

Wires TypeScript tests to a **hosted device/browser grid** — BrowserStack, Sauce Labs, LambdaTest, or AWS Device Farm — so the same Playwright web specs and WebdriverIO/Appium mobile specs that run locally execute at scale on someone else's infrastructure. This skill is the **bridge** between `qa/typescript/skills/ui-test-author/{playwright,appium}/typescript` (which write the tests) and the grid that runs them: connection wiring, vendor capabilities, parallelism, artifacts, secrets, tunnels, and result reporting. It is **config/wiring** — it does not author page objects or specs.

> **Why this skill exists.** A local Playwright/Appium suite hard-codes nothing about a grid: it launches a local browser or a local emulator. Moving it to a grid changes exactly one thing per stack — **how the driver/browser is connected** — plus a capability block, a parallelism cap, and secret hygiene. Get those five things right and every existing page object runs unchanged. Get them wrong and you leak an access key, blow the plan's session cap, or stare at a green local run that was actually a grid that never connected.

## Stack

- Node 20 + TypeScript (strict mode)
- **Web**: `@playwright/test` connected to a cloud grid via `chromium.connect({ wsEndpoint })`, the `browserstack-node-sdk` wrapper, or `saucectl`
- **Mobile**: WebdriverIO 9.x + Appium 2.x with `@wdio/browserstack-service` / `@wdio/sauce-service` (or raw `bstack:options`/`sauce:options`/`LT:Options` caps)
- Tunnels: `browserstack-local` (npm), Sauce Connect 5 (`sc` binary), LambdaTest Tunnel (`LT` binary)
- Grid config under `tests/support/grid/`; credentials via **env vars only** (`BROWSERSTACK_USERNAME` / `BROWSERSTACK_ACCESS_KEY`, `SAUCE_USERNAME` / `SAUCE_ACCESS_KEY`, `LT_USERNAME` / `LT_ACCESS_KEY`)
- These suites run in CI under `qa/typescript/skills/ci-pipelines/github-actions` — secrets injected via the runner's secret store / OIDC, sharding driven by the runner (see § Parallelism)

## When to use

- Running existing Playwright web specs on a cloud browser matrix instead of local Chromium/Firefox/WebKit
- Running existing WebdriverIO/Appium mobile specs on cloud real devices / emulators
- Picking and wiring the **right vendor capability block** (`bstack:options` vs `sauce:options` vs `LT:Options`) for a TS stack
- Capping concurrent sessions to the plan and mapping that onto Playwright `workers` / WDIO `maxInstances`
- Surfacing the **session dashboard URL** + video/logs on failure, and marking the session pass/fail back to the vendor
- Reaching a private/staging URL from the grid via a **local tunnel**

## When NOT to use

- The .NET / Java grid stacks → `qa/{dotnet,java}/skills/cloud-grid-config`
- Writing the page objects / specs → `qa/typescript/skills/ui-test-author/playwright`, `qa/typescript/skills/ui-test-author/appium`
- CI shard/worker mechanics (matrix, `--shard`, artifact upload) → `qa/typescript/skills/ci-pipelines/*` — this skill maps the cap *onto* those, it doesn't re-derive them
- Deep AWS Device Farm device-pool / ARN orchestration → `qa/typescript/skills/mobile-device-farm` (row #40); this node covers the wiring, that one the farm specifics

## Pick a vendor — quick orientation

| Vendor | Web (Playwright) connect | Mobile (Appium) hub | Vendor cap block | Tunnel binary |
|---|---|---|---|---|
| **BrowserStack** | `wss://cdp.browserstack.com/playwright` (flat caps) **or** `browserstack-node-sdk` | `hub-cloud.browserstack.com/wd/hub` | `bstack:options` (W3C, Selenium/Appium); **flat `browserstack.*` for Playwright direct-connect** | `browserstack-local` (npm `Local`) |
| **Sauce Labs** | **`saucectl` only** (no public ad-hoc `connect`) | `ondemand.<region>.saucelabs.com/wd/hub` | `sauce:options` | Sauce Connect 5 (`sc run`) |
| **LambdaTest** | `wss://cdp.lambdatest.com/playwright` (SDK `lambdatest-setup`) | `mobile-hub.lambdatest.com/wd/hub` | `LT:Options` | LambdaTest Tunnel (`LT`) |
| **AWS Device Farm** | signed TestGrid Selenium URL (not a Playwright ws endpoint) | managed run (project ARN + device-pool ARN) or `remoteDriverEndpoint` | none — ARN/upload model | VPC/endpoint config, not a CLI tunnel |

**Decision rule.** *Mostly web on a broad browser/OS matrix? Any of BrowserStack / Sauce / LambdaTest — pick on price/plan.* *Real-device mobile depth or app-management?* BrowserStack and Sauce are strongest; LambdaTest is the cheapest broad option. *Already deep in AWS and need private-VPC devices?* Device Farm — but it's an **ARN/upload paradigm, not a caps-on-a-hub grid**, so the wiring differs most there (see § AWS Device Farm). Don't over-engineer multi-vendor abstraction; wire one vendor cleanly behind the `gridCaps` helper and add a second only when a real need appears.

> **The one gotcha that bites everyone (Playwright + BrowserStack).** BrowserStack's Playwright **direct-connect still uses LEGACY FLAT caps** (`browser`, `os`, `os_version`, `browserstack.username`, `browserstack.accessKey`, …) — **not** the W3C `bstack:options` nesting used by Selenium/Appium. The nested block is for the `browserstack.yml` SDK and for Appium. Don't mix them. Sauce has **no public Playwright `connect` endpoint at all** — it's `saucectl`-driven, the biggest cross-vendor divergence.

## Inputs needed

Ask at most 3 questions; infer the rest from the existing test project.

1. **Web or mobile** — Playwright web, or WebdriverIO/Appium mobile? This decides the connection idiom entirely.
2. **Which vendor** — BrowserStack / Sauce / LambdaTest / Device Farm? (And, for Sauce/Device Farm, **which region**, since there is no implicit default.)
3. **Private target?** — does the grid need to reach a staging/localhost URL (→ tunnel), and what's the **concurrent-session cap** on the plan (→ `workers` / `maxInstances`)?

---

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

In CI these env vars come from the runner's secret store; for cloud auth (e.g. an OIDC-minted token used to reach AWS Device Farm) prefer OIDC over a long-lived PAT — see `qa/typescript/skills/ci-pipelines/github-actions`.

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

For WDIO it's `maxInstances` (shown above). The **sharding mechanics** (matrix fan-out, `--shard`, merging blob reports) belong to `qa/typescript/skills/ci-pipelines/github-actions` — cross-link it; don't re-derive it here. The rule: `total runner shards × workers-per-shard ≤ plan session cap`.

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

Device Farm is **not a caps-on-a-hub grid**. You upload the app + a test package to a **project ARN**, then `aws devicefarm schedule-run` against a **device-pool ARN**. For live/client-side Appium, create a remote-access session and read the `remoteDriverEndpoint` from `GetRemoteAccessSession`; for desktop browsers, the TestGrid APIs mint a short-lived signed Selenium URL you hand to a remote driver. The wiring is AWS-SDK calls, not capability JSON. For the full device-pool/ARN orchestration defer to `qa/typescript/skills/mobile-device-farm`; this node covers only the connection shape.

## Rules

### Connection
- **Web**: connect, don't launch. Playwright → BrowserStack `chromium.connect({ wsEndpoint })` with **flat caps**; Sauce → `saucectl`; LambdaTest → its connect endpoint with `LT:Options`.
- **Mobile**: set `user`/`key`/`hostname` + the vendor service in `wdio.conf.ts`; the page objects don't change.
- **Never mix** BrowserStack's flat Playwright caps with the W3C `bstack:options` nesting — they apply to different connection paths.
- Pin the Playwright/Appium version cap to your installed version; a version skew is a confusing remote failure.

### Capabilities
- Use the **current** key names (`userName`/`buildName`/`sessionName`, not legacy `browserstack.user`/`version`). Vendors renamed them off JSON-Wire.
- Always set `buildName`/`build`, `sessionName`/`name`, and a project tag so runs are findable on the dashboard.
- App under test is referenced by the vendor's uploaded id (`bs://…`, `storage:…`), **never a local file path** in the cap.

### Parallelism
- Read the concurrent-session cap from **one env var** (`GRID_CONCURRENCY`) and map it onto `workers` / `maxInstances`. Never hard-code.
- `total CI shards × workers-per-shard ≤ plan session cap`. Sharding mechanics live in `qa/typescript/skills/ci-pipelines/*` — cross-link, don't duplicate.

### Secrets
- Username + access key via **env vars only** (`required(...)` helper). Never a literal, never in `wdio.conf.ts`/`browserstack.yml`/`.sauce/config.yml` committed to the repo.
- In CI inject via the secret store; for cloud (Device Farm) auth prefer **OIDC** over a long-lived key.
- Never log a credential or persist it into an artifact/HAR.

### Artifacts & status
- Surface the **session dashboard URL** in output / Allure on failure — a failed grid run should be one click from the replay.
- **Mark the session pass/fail** back to the vendor (`setSessionStatus` / `sauce:job-result` / `lambda-status`), or let the `@wdio/*-service` do it. The dashboard must reflect reality.

### Tunnels
- Start the tunnel **before** the suite, stop it in teardown; tie sessions via `local`+`localIdentifier` / `tunnelName`.
- Tunnel key from env, never a literal. One tunnel identifier per run so parallel runs don't collide.

### Waits
- **No `setTimeout`-as-a-wait / `page.waitForTimeout` / `browser.pause`** anywhere — grid latency is higher than local, which makes fixed sleeps both flakier and slower. Use Playwright auto-wait / WDIO `waitForDisplayed` / explicit conditions, exactly as the local suite does.

### What NOT to do
- No launching a local browser when the intent is a grid run — connect to the grid.
- No `bstack:options` on a BrowserStack Playwright **direct-connect** — it's flat caps there.
- No hard-coded session/worker count — read the plan cap from env and map it.
- No credential literals in code or committed config — env vars only.
- No grid run that doesn't **report status** to the vendor and **surface the session URL** on failure.
- No tunnel without a stop in teardown, and no tunnel key as a literal.
- No `waitForTimeout`/`pause` to paper over grid latency.

## Generation steps

1. Confirm **web vs mobile**, **vendor** (+ region for Sauce/Device Farm), **private target?** (tunnel), and the **session cap**.
2. Add `tests/support/grid/credentials.ts` with the `required(...)` env reads — no literals.
3. **Web**: add `playwrightConnect.ts` (BrowserStack flat-cap `connect`) + a `gridFixture` that yields a `page` and marks status in teardown; or scaffold `.sauce/config.yml` (Sauce) / the LambdaTest connect. **Mobile**: edit `wdio.conf.ts` — `user`/`key`/`hostname` + vendor service + `bstack:options`/`sauce:options`/`LT:Options` caps.
4. Map the session cap onto `workers` / `maxInstances` from `GRID_CONCURRENCY`; note the `shards × workers ≤ cap` rule and cross-link `qa/typescript/skills/ci-pipelines/*`.
5. Wire artifacts (`attachSessionUrl`) + session status (`markSessionStatus`) into the fixture teardown.
6. If the target is private, add the tunnel lifecycle (`GridTunnel` start/stop in global setup/teardown) and tie sessions via the cap.
7. Run a single spec against the grid first (one worker) to confirm the connection + caps before fanning out. Confirm the session appears on the dashboard with the right build/project tags.

## Cross-references

- **`qa/dotnet/skills/cloud-grid-config`** + **`qa/java/skills/cloud-grid-config`** — sibling grid stacks. Same five moves (connect → caps → parallelism → artifacts/status → tunnel), different SDKs (`BrowserType.ConnectAsync`/`AppiumOptions`; Playwright Java `connect`/`UiAutomator2Options`). Structure ported, not code.
- **`qa/typescript/skills/ui-test-author/playwright`** — writes the web specs/page objects this skill runs on a grid (connection patterns to extend).
- **`qa/typescript/skills/ui-test-author/appium`** — writes the mobile specs/page objects; this skill swaps the local Appium session for a grid one.
- **`qa/typescript/skills/ci-pipelines/github-actions`** — sharding/`--shard`/blob-merge + OIDC secret injection; this skill maps the plan cap onto those shards (don't duplicate the mechanics).
- **`qa/typescript/skills/mobile-device-farm`** (row #40, Phase 3) — deeper cloud-Appium / device-pool specifics; this node is config/wiring, that one is the farm.
- **`qa/typescript/skills/network-monitoring/proxy`** — when a grid run also needs out-of-browser traffic capture (the proxy + tunnel combine).
