---
name: qa-bdd-project-setup-typescript
description: Use when adding a BDD/Gherkin layer onto a TypeScript UI/mobile test project, or standing one up from zero — playwright-bdd (on the Playwright Test runner) for web, CucumberJS + WebdriverIO + Appium for mobile. Triggers: "set up playwright-bdd", "add a BDD layer to our Playwright tests in TS", "wire bddgen and fixtures". Do NOT use to write feature files (`feature-file-writer`), generate step definitions (`gherkin-step-code`), or build page objects (`page-object-design`).
---

# BDD Project Scaffold (TypeScript / Node 20)

Wires a **BDD/Gherkin layer** onto a TypeScript test project: packages, runner config, the `features/` folder, the state/driver-sharing mechanism, the per-scenario lifecycle, and the smoke `.feature` that proves the rig parses and runs. It produces the **empty rig** — no feature files, no step logic; those come from `feature-file-writer` and `gherkin-step-code`.

This is the BDD analogue of `ui-project-setup`; it assumes a Playwright (web) or WebdriverIO+Appium (mobile) page-object project either exists or will be built by `qa-ui-typescript` / `qa-mobile-typescript`.

## The TypeScript split (read this first)

TypeScript has **no single BDD framework** that spans web and mobile — the runner differs by platform, and so does the state-sharing model. Pick the path, then scaffold only that path:

| Platform | Framework | Runner | State/driver sharing |
|---|---|---|---|
| **Web** | **playwright-bdd** (by vitalets) | Playwright Test (via `bddgen` codegen) | **Playwright fixtures** — no World, no DI container |
| **Mobile** | **@cucumber/cucumber (CucumberJS) + WebdriverIO + @wdio/appium-service** | CucumberJS via `@wdio/cucumber-framework` | **custom `World`** (`setWorldConstructor`), driver built in a `Before` hook |

The two paths never share a runner. A project that tests **both** scaffolds both rigs side by side (a `web/` and a `mobile/` folder), not one merged config. The central difference downstream — **fixtures vs World** — is taught in full by `gherkin-step-code`.

## Stack (pinned, verify latest at author time)

**Web — playwright-bdd**
- Node ≥ 20, TypeScript (`strict: true`)
- `playwright-bdd` (latest line **9.2.x**), peer `@playwright/test` **≥ 1.44**
- Model: `npx bddgen` compiles `features/**/*.feature` → generated Playwright specs in `.features-gen/`; `npx playwright test` runs them (free parallelism, auto-wait, trace/video, HTML report)
- Page objects shared as **fixtures**; reporting via Playwright reporters + built-in `cucumberReporter('html', …)`

**Mobile — CucumberJS + WebdriverIO**
- Node ≥ 20, TypeScript (`strict: true`), ESM
- `@cucumber/cucumber` (latest line **13.0.x**), `webdriverio` 9.x, `@wdio/appium-service`, `@wdio/cucumber-framework`, `appium` 2.x + the platform driver
- ⚠️ **Version-compat check:** `@wdio/cucumber-framework` often pins an **older** `@cucumber/cucumber` line than the latest standalone 13.x — pin the version it expects, don't force 13.x blindly. Verify the peer range before locking the lockfile.
- Reporting via `@wdio/allure-reporter`; standalone CucumberJS HTML formatter is bundled in `@cucumber/cucumber`

## When to use

- A TS UI/mobile project needs a BDD layer added (packages, config, lifecycle).
- Starting a Gherkin suite from zero.

## When NOT to use

- Writing `.feature` files → `qa/_shared/bdd/feature-file-writer`
- Generating step definitions → `qa/typescript/skills/gherkin-step-code`
- Building page objects → `qa/typescript/skills/page-object-design` / `page-objects-from-url` / `mobile-screen-objects`
- BDD in .NET/Java → `qa/{dotnet,java}/skills/bdd-project-setup` (Reqnroll / Cucumber-JVM)

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
6. Run the toolchain (web: `npx bddgen && npx playwright test`; mobile: `npx wdio run`), confirm the smoke scenario is green.
7. Report files created and hand off to `feature-file-writer` (features) + `gherkin-step-code` (steps).

## Templates — Web (playwright-bdd)

### `package.json` (deps)

```jsonc
{
  "scripts": {
    "bddgen": "bddgen",
    "test:bdd": "bddgen && playwright test"
  },
  "devDependencies": {
    "@playwright/test": "^1.49.0",
    "playwright-bdd": "^9.2.0",
    "typescript": "^5.6.0"
  }
}
```

### `playwright.config.ts`

```typescript
import { defineConfig } from '@playwright/test';
import { defineBddConfig, cucumberReporter } from 'playwright-bdd';

// bddgen compiles .feature files into Playwright specs in this generated dir.
const testDir = defineBddConfig({
  features: 'features/**/*.feature',
  steps: 'steps/**/*.ts',
});

export default defineConfig({
  testDir, // <- the GENERATED dir, not 'features/'
  reporter: [
    ['html', { open: 'never' }],
    // Living documentation — playwright-bdd's built-in Cucumber HTML formatter:
    cucumberReporter('html', { outputFile: 'cucumber-report/index.html' }),
  ],
  use: { trace: 'on-first-retry' },
  projects: [{ name: 'chromium', use: { browserName: 'chromium' } }],
});
```

> Living documentation: `cucumberReporter('html', …)` emits the Cucumber HTML report (it depends internally on `@cucumber/html-formatter`); the Playwright HTML reporter gives traces/video for free. For CI dashboards prefer Allure — `qa-reporting-typescript` owns that wiring.

### `steps/fixtures.ts` — page objects as fixtures (NO World)

```typescript
import { test as base, createBdd } from 'playwright-bdd';
import { LoginPage } from '../pages/LoginPage'; // the existing page-object project
import { DashboardPage } from '../pages/DashboardPage';

// Page objects are exposed as fixtures; every step destructures the ones it needs.
// This is the playwright-bdd analogue of a World/DI container — there is no World here.
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

```jsonc
{
  "scripts": {
    "test:bdd": "wdio run ./wdio.conf.ts"
  },
  "devDependencies": {
    "@cucumber/cucumber": "^13.0.0",      // ⚠️ pin to the version @wdio/cucumber-framework expects
    "@wdio/cli": "^9.0.0",
    "@wdio/cucumber-framework": "^9.0.0",
    "@wdio/appium-service": "^9.0.0",
    "@wdio/allure-reporter": "^9.0.0",
    "webdriverio": "^9.0.0",
    "appium": "^2.11.0",
    "typescript": "^5.6.0"
  }
}
```

### `wdio.conf.ts`

```typescript
import type { Options } from '@wdio/types';

export const config: Options.Testrunner = {
  runner: 'local',
  framework: 'cucumber',
  specs: ['./features/**/*.feature'],
  // WebdriverIO manages the Appium server — no manual `appium` process.
  services: [['appium', { args: { relaxedSecurity: true } }]],
  cucumberOpts: {
    require: ['./steps/**/*.ts', './support/**/*.ts'], // World + hooks live in support/
    timeout: 60_000,
  },
  reporters: [['allure', { outputDir: 'allure-results' }]],
  capabilities: [{
    platformName: 'Android',
    'appium:automationName': 'UiAutomator2',
    'appium:deviceName': process.env.DEVICE_NAME ?? 'emulator-5554',
    'appium:app': process.env.APP_PATH,
  }],
};
```

### `support/world.ts` — custom World (the state container)

```typescript
import { World, setWorldConstructor, type IWorldOptions } from '@cucumber/cucumber';
import type { LoginScreen } from '../pages/mobile/LoginScreen';

// CucumberJS shares state across steps via the World, NOT fixtures.
// The driver is the WebdriverIO `browser` (global, started by @wdio/appium-service);
// the World holds the lazily-built screen objects so every step shares them.
export class CustomWorld extends World {
  private _login?: LoginScreen;

  constructor(options: IWorldOptions) {
    super(options);
  }

  get login(): LoginScreen {
    // built lazily against the global WDIO `browser`
    this._login ??= new (require('../pages/mobile/LoginScreen').LoginScreen)();
    return this._login;
  }
}

setWorldConstructor(CustomWorld);
```

### `support/hooks.ts` — per-scenario lifecycle (with teardown)

```typescript
import { Before, After, type ITestCaseHookParameter } from '@cucumber/cucumber';
import type { CustomWorld } from './world';

// WebdriverIO + @wdio/appium-service start/stop the session per worker, so the
// Before/After hooks reset app state per scenario and own the Cleanup handoff.
Before(async function (this: CustomWorld) {
  await browser.reset?.(); // fresh app state per scenario; or relaunch the activity
});

After(async function (this: CustomWorld, scenario: ITestCaseHookParameter) {
  if (scenario.result?.status === 'FAILED') {
    await browser.takeScreenshot(); // attach to Allure in the reporter
  }
  // Cleanup handoff from feature-file-writer is implemented HERE, never as Gherkin.
});
```

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
- **Mobile:** forcing `@cucumber/cucumber@13` when `@wdio/cucumber-framework` pins an older line — broken peer deps.
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
