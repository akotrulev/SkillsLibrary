---
name: qa-bdd-project-setup-typescript
description: Use when adding a BDD/Gherkin layer onto a TypeScript UI/mobile test project, or standing one up from zero — playwright-bdd (on the Playwright Test runner) for web, CucumberJS + WebdriverIO + Appium for mobile. Triggers: "set up playwright-bdd", "add a BDD layer to our Playwright tests in TS", "wire bddgen and fixtures". Do NOT use to write feature files (`feature-file-writer`), generate step definitions (`gherkin-step-code`), or build page objects (`page-object-design`).
---

# BDD Project Scaffold (TypeScript / Node 24, 22 maintenance)

Wires a **BDD/Gherkin layer** onto a TypeScript test project: packages, runner config, the `features/` folder, the state/driver-sharing mechanism, the per-scenario lifecycle, and the smoke `.feature` that proves the rig parses and runs. It produces the **empty rig** — no feature files, no step logic; those come from `feature-file-writer` and `gherkin-step-code`.

This is the BDD analogue of `ui-project-setup`; it assumes a Playwright (web) or WebdriverIO+Appium (mobile) page-object project either exists or will be built by `qa-ui-typescript` / `qa-mobile-typescript`.

## The TypeScript split (read this first)

TypeScript has **no single BDD framework** that spans web and mobile — the runner differs by platform, and so does the state-sharing model. Pick the path, then scaffold only that path:

| Platform | Framework | Runner | State/driver sharing |
|---|---|---|---|
| **Web** | **playwright-bdd** (by vitalets) | Playwright Test (via `bddgen` codegen) | **Playwright fixtures** — no World, no DI container |
| **Mobile** | **@cucumber/cucumber (CucumberJS) + WebdriverIO + @wdio/appium-service** | CucumberJS via `@wdio/cucumber-framework` | **custom `World`** (`setWorldConstructor`), driver built in a `Before` hook |

The two paths never share a runner. A project that tests **both** scaffolds both rigs side by side (a `web/` and a `mobile/` folder), not one merged config. The central difference downstream — **fixtures vs World** — is taught in full by `gherkin-step-code`.

## Stack

**Web — playwright-bdd** — the pins are the **Versions** table of `qa/typescript/skills/ui-test-author/playwright/SKILL.md`:

| Package | Version |
|---|---|
| `@playwright/test` | 1.64.0 |
| `playwright-bdd` | 9.2.1 |
| `allure-playwright`, `allure-js-commons` | 3.13.0 (needs `@playwright/test` ≥ 1.62) |

- Node 24 (22 maintenance; Node 20 is EOL — flag it), TypeScript (`strict: true`)
- Model: `npx bddgen` compiles `features/**/*.feature` → generated Playwright specs in `.features-gen/`; `npx playwright test` runs them (free parallelism, auto-wait, the failure evidence, HTML report)
- Page objects shared as **fixtures**; reporting via Playwright reporters, Allure, and the built-in `cucumberReporter('html', …)`
- On a project pinned to an older `@playwright/test`, keep its version and pick the `playwright-bdd` and `allure-playwright` lines that support it — never up-level the project as a side effect

**Mobile — CucumberJS + WebdriverIO**
- Node 24 (22 maintenance), TypeScript (`strict: true`), ESM
- The WebdriverIO and Appium pins are the **Versions** table of `qa/typescript/skills/ui-test-author/appium` (Appium 3 with WebdriverIO 10 primary; Appium 2 with WebdriverIO 9 supported); `@cucumber/cucumber` 13.3.0 with `@wdio/cucumber-framework` 10.0.1
- ⚠️ **Version-compat check:** `@wdio/cucumber-framework` pins a `@cucumber/cucumber` peer range (`^13.2.1` for 10.0.1) — keep inside it. Verify the peer range before locking the lockfile.
- Reporting via `@wdio/allure-reporter`; standalone CucumberJS HTML formatter is bundled in `@cucumber/cucumber`

## When to use

- A TS UI/mobile project needs a BDD layer added (packages, config, lifecycle).
- Starting a Gherkin suite from zero.

## When NOT to use

- Writing `.feature` files → `qa/_shared/bdd/feature-file-writer`
- Generating step definitions → `qa/typescript/skills/gherkin-step-code`
- Building page objects → `qa/typescript/skills/page-object-design` / `page-objects-from-url` / `mobile-screen-objects`
- BDD in .NET/Java → `qa/{dotnet,java}/skills/bdd-project-scaffold` (Reqnroll / Cucumber-JVM)

## Inputs needed

Confirm at most 2–3.

1. **Target project path** and whether a Playwright/WebdriverIO page-object project already exists (reuse it; don't duplicate page objects).
2. **Platform** — web (playwright-bdd), mobile (CucumberJS+WDIO), or both (two rigs).
3. **Reporting** — native HTML (default) or Allure (the library standard, owned by `qa-reporting-typescript`).

## Procedure

1. Read 2–3 existing files (`package.json`, an existing page object, `playwright.config.ts` / `wdio.conf.ts`) to match conventions.
2. Add the platform's packages to `package.json`. (Web: playwright-bdd. Mobile: cucumber + wdio + appium-service — run the version-compat check.)
3. Web: add `defineBddConfig(...)` to `playwright.config.ts` and a `bddgen` script. Mobile: add `wdio.conf.ts` with the appium service + the cucumber framework + the World/hooks files.
4. Create the state/lifecycle layer — web: a `test` fixture extending page objects (no World); mobile: a `CustomWorld` + `Before`/`After` hooks that own the driver **with teardown**.
5. Create the empty `features/` folder and one throwaway smoke `.feature` to prove the rig parses and runs.
6. Run the toolchain (web: `npx bddgen && npx playwright test`; mobile: `npx wdio run`), confirm the smoke scenario is green. Inside a plan task marked `Gate: none`, run none of this and report the files as "written, not run".
7. Report files created and hand off to `feature-file-writer` (features) + `gherkin-step-code` (steps).

## Templates — Web (playwright-bdd)

### `package.json` (deps)

```json
{
  "scripts": {
    "bddgen": "bddgen",
    "test:bdd": "bddgen && playwright test"
  },
  "devDependencies": {
    "@playwright/test": "1.64.0",
    "playwright-bdd": "9.2.1",
    "allure-playwright": "3.13.0",
    "allure-js-commons": "3.13.0"
  }
}
```

Exact versions, no `^`: the browser build and the Docker image tag (`mcr.microsoft.com/playwright:v1.64.0-noble`)
must equal the installed `@playwright/test`. `typescript` stays at the project's existing version.

### `playwright.config.ts`

```typescript
import { defineConfig, devices } from '@playwright/test';
import { cucumberReporter, defineBddConfig } from 'playwright-bdd';

const isCI = !!process.env.CI;

const testDir = defineBddConfig({
  features: 'features/**/*.feature',
  steps: 'steps/**/*.ts',
});

export default defineConfig({
  testDir,
  forbidOnly: isCI,
  fullyParallel: true,
  retries: 0,
  reporter: [
    ['html', { open: 'never' }],
    ['allure-playwright', { resultsDir: 'allure-results' }],
    cucumberReporter('html', { outputFile: 'cucumber-report/index.html' }),
  ],
  use: {
    baseURL: process.env.BASE_URL,
    testIdAttribute: 'data-testid',
    trace: 'retain-on-failure',
    video: 'retain-on-failure',
    screenshot: { mode: 'only-on-failure', fullPage: true },
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
});
```

- `testDir` is the **generated** dir `bddgen` writes, never `features/`.
- The evidence settings are the writer's failure defaults: trace and video `retain-on-failure`, a full-page
  screenshot `only-on-failure`. They work with `retries: 0` (`qa/cicd/ci-conventions`); `on-first-retry` records
  nothing without a retry. What each mode keeps and how a failed scenario's trace is read is
  `qa/typescript/skills/evidence-capture`.
- `cucumberReporter('html', …)` is the living documentation (it depends internally on `@cucumber/html-formatter`);
  the Playwright HTML report carries the trace, video and screenshot of a failed scenario; Allure is the CI
  dashboard, its labels and history owned by `qa-reporting-typescript`. Attach calls come from `allure-js-commons`,
  awaited.
- A signed-in suite adds the writer's `setup` project and `storageState` (`references/config-and-fixtures.md` §3
  of `ui-test-author/playwright`).

### `steps/fixtures.ts` — page objects as fixtures (NO World)

Page objects come from the existing page-object project and are exposed as fixtures; every step destructures
the ones it needs. This is the playwright-bdd analogue of a World/DI container — there is no World here.

```typescript
import { test as base, createBdd } from 'playwright-bdd';
import { DashboardPage } from '../pages/DashboardPage';
import { LoginPage } from '../pages/LoginPage';

type Fixtures = {
  loginPage: LoginPage;
  dashboardPage: DashboardPage;
};

export const test = base.extend<Fixtures>({
  loginPage: async ({ page }, use) => { await use(new LoginPage(page)); },
  dashboardPage: async ({ page }, use) => { await use(new DashboardPage(page)); },
});

export const { Given, When, Then, Before, After } = createBdd(test);
```

> Teardown is **fixture teardown** — anything after the `await use(...)` line, plus Playwright's per-test `page`/`context` disposal. There is no `[AfterScenario]` hook to write; the Cleanup handoff from `feature-file-writer` becomes a fixture teardown (or a `gherkin-step-code` `After` from `createBdd`), never Gherkin.

### `features/smoke.feature` — throwaway rig check

```gherkin
@smoke
Feature: BDD rig smoke
  Scenario: the toolchain compiles and runs
    Given the application is reachable
    Then the home page is shown
```

## Templates — Mobile (CucumberJS + WebdriverIO + Appium)

### `package.json` (deps)

```json
{
  "type": "module",
  "scripts": {
    "test:bdd": "wdio run ./wdio.conf.ts"
  },
  "devDependencies": {
    "@cucumber/cucumber": "13.3.0",
    "@types/node": "24.19.2",
    "@wdio/allure-reporter": "10.0.1",
    "@wdio/appium-service": "10.0.2",
    "@wdio/cli": "10.0.2",
    "@wdio/cucumber-framework": "10.0.1",
    "@wdio/globals": "10.0.2",
    "@wdio/types": "10.0.1",
    "appium": "3.8.0",
    "appium-uiautomator2-driver": "8.7.0",
    "appium-xcuitest-driver": "12.17.1",
    "typescript": "5.9.3",
    "webdriverio": "10.0.2"
  }
}
```

The pins are exact. Install only the driver for the platform under test, and keep the Appium 2 / WebdriverIO 9 lane on a project or a device cloud that has not moved.

### `wdio.conf.ts`

```typescript
import { requiredEnv } from './env.js';

export const config: WebdriverIO.Config = {
  runner: 'local',
  framework: 'cucumber',
  specs: ['./features/**/*.feature'],
  services: ['appium'],
  cucumberOpts: {
    import: ['./steps/**/*.ts', './support/**/*.ts'],
    timeout: 60_000,
  },
  reporters: [['allure', { outputDir: 'allure-results', disableWebdriverScreenshotsReporting: true }]],
  capabilities: [{
    platformName: 'Android',
    'appium:automationName': 'UiAutomator2',
    'appium:deviceName': requiredEnv('DEVICE_NAME'),
    'appium:app': requiredEnv('APP_PATH'),
    'appium:settings[disableIdLocatorAutocompletion]': true,
  }],
};
```

`@wdio/appium-service` manages the Appium server, so no `appium` process runs by hand. `requiredEnv` is the helper in `ui-test-author/appium/assets/env.ts`, and that skill explains the capability block and the id-prefix setting.

### `support/world.ts` — custom World (the state container)

```typescript
import { World, setWorldConstructor, type IWorldOptions } from '@cucumber/cucumber';
import { LoginPage } from '../pages/mobile/LoginPage.js';

export class CustomWorld extends World {
  private loginPage?: LoginPage;

  constructor(options: IWorldOptions) {
    super(options);
  }

  get login(): LoginPage {
    this.loginPage ??= new LoginPage();
    return this.loginPage;
  }
}

setWorldConstructor(CustomWorld);
```

CucumberJS shares state through the World, not fixtures. The driver is the WebdriverIO `browser`, a global the runner starts, so the World holds only the screen objects, built lazily on first use.

### `support/hooks.ts` — per-scenario lifecycle (with teardown)

```typescript
import { After, Before, Status, type ITestCaseHookParameter } from '@cucumber/cucumber';
import { browser } from '@wdio/globals';
import { requiredEnv } from '../env.js';
import type { CustomWorld } from './world.js';

Before(async function (this: CustomWorld) {
  const appId = requiredEnv('APP_ID');
  await browser.execute('mobile: clearApp', browser.isIOS ? { bundleId: appId } : { appId });
});

After(async function (this: CustomWorld, scenario: ITestCaseHookParameter) {
  if (scenario.result?.status === Status.FAILED) {
    this.attach(Buffer.from(await browser.takeScreenshot(), 'base64'), 'image/png');
    this.attach(await browser.getPageSource(), 'application/xml');
  }
});
```

`Before` gives each scenario fresh app state through `mobile: clearApp`, which works on an emulator or simulator; on a real device a new session is the reset. `After` attaches the screenshot and page source to the scenario, and the Cleanup handoff from `feature-file-writer` is implemented here, never as Gherkin. The recording, the device log and the rest of the failure evidence are `qa/typescript/skills/evidence-capture/references/appium.md`.

### `features/smoke.feature` — throwaway rig check

```gherkin
@smoke
Feature: BDD rig smoke
  Scenario: the toolchain launches the app
    Given the app is launched
    Then the login screen is shown
```

## Anti-patterns to flag

- **Web:** pointing Playwright `testDir` at `features/` instead of the **generated** dir from `defineBddConfig` — bddgen output is what runs.
- **Web:** introducing a World or a DI container — playwright-bdd uses fixtures; reaching for `setWorldConstructor` here is wrong.
- **Mobile:** sharing state via module-level mutable variables instead of the World — violates "no static mutable state."
- **Mobile:** launching/quitting the Appium server by hand instead of `@wdio/appium-service`.
- **Mobile:** an `@cucumber/cucumber` version outside the range `@wdio/cucumber-framework` takes as a peer — broken peer deps.
- Putting browser/driver lifecycle in a step body instead of a fixture (web) / `Before` hook (mobile).
- Missing teardown — leaked browser contexts (web) or app sessions (mobile).
- Re-declaring page objects in the BDD project instead of importing the existing UI project.
- Implementing the Cleanup as Gherkin steps instead of fixture teardown (web) / `After` hook (mobile).

## Handoffs

- Feature files → `qa/_shared/bdd/feature-file-writer`
- Step definitions + POM wiring → `qa/typescript/skills/gherkin-step-code`
- Page objects → `qa/typescript/skills/page-object-design` / `page-objects-from-url` / `mobile-screen-objects`
- Allure reporting → `qa/reporting/typescript/skills/test-reports`
- CI (feature shard, publish report) → `qa/cicd/typescript/skills/ci-pipelines`
