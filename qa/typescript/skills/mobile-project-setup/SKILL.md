---
name: mobile-project-setup
description: Use when starting a mobile (iOS/Android) test project from zero in TypeScript — Node 24, WebdriverIO 10 + Mocha, exact pins, Appium 3 server + drivers + emulator setup, capabilities from environment variables, a first smoke run. Triggers "scaffold a mobile test project", "set up a WebdriverIO Appium suite from scratch". Do NOT use for authoring screens or tests (`ui-test-author/appium`), or device clouds (`device-cloud`).
---

# Mobile Test Project Scaffold (TypeScript, WebdriverIO 10)

This skill stands up a **runnable Appium 3 test project from zero**: the package layout, exact versions, the Appium server, drivers and emulator, the capability configuration, and a first smoke run. It owns the **project shell and the environment**. Screen-object and test conventions belong to `ui-test-author/appium`; the compilable project that drops into the layout below is `qa/typescript/skills/ui-test-author/appium/assets/`, and this skill points at it instead of copying it.

**Version rule:** new projects use Node 24 (22 maintenance) and TypeScript strict mode. WebdriverIO 10 needs Node ≥ 22.19 and an Appium 3 server. Node 20 is end-of-life: never target it.

## When to use

- A fresh repo with no TypeScript mobile test project, and the user wants iOS or Android coverage.
- The user asks which versions, layout or Appium setup a WebdriverIO mobile framework should use.

## When NOT to use

- The project exists → author into it with `qa/typescript/skills/ui-test-author/appium`.
- Real-device clouds → `qa/typescript/skills/device-cloud`.
- Web-UI or API scaffolding → the matching `*-project-setup` skill.

## Versions

The table is the **Versions** table of `ui-test-author/appium/SKILL.md`, and `assets/package.json` there holds the same pins.

| Concern | Package / tool | Version | Notes |
|---|---|---|---|
| Runtime | Node | **24** | WebdriverIO 10 needs ≥ 22.19; 22 is the maintenance lane. `engines.node` is `>=22.19.0` |
| Language | `typescript` | **5.9.3** | `strict: true`, `noUncheckedIndexedAccess`, `module: NodeNext` |
| Automation | `webdriverio` · `@wdio/cli` · `@wdio/globals` · `@wdio/appium-service` | **10.0.2** | Needs Appium 3 |
| Runner pieces | `@wdio/mocha-framework` · `@wdio/types` | **10.0.1** | Mocha is the framework; WDIO has no Vitest framework |
| Matchers, logger | `expect-webdriverio` · `@wdio/logger` | **8.0.0** · **10.0.0** | `expect-webdriverio` is a required peer of `@wdio/globals`; `BaseTest.ts` imports the logger |
| Reporting | `@wdio/allure-reporter` | **10.0.1** | Writes `allure-results/` |
| Appium server | `appium` | **3.8.0** | Needs Node ^20.19 \|\| ^22.12 \|\| ≥ 24 |
| Android driver | `appium-uiautomator2-driver` | **8.7.0** | Majors ≥ 5 need Appium 3 |
| iOS driver | `appium-xcuitest-driver` | **12.17.1** | Macs only. Majors ≥ 10 need Appium 3 |
| Types | `@types/node` · `@types/mocha` | **24.19.2** · **10.0.10** | |

## Prerequisites

| Need | Check |
|---|---|
| Node 24 (22.19 or newer) and npm | `node --version` |
| Android SDK, with `ANDROID_HOME` pointing at it and `platform-tools` on `PATH` | `echo $ANDROID_HOME` · `adb version` |
| An Android emulator image (a system image plus an AVD) | `avdmanager list avd` |
| Xcode and a simulator runtime, macOS only | `xcrun simctl list devices` |

A **real iOS device** also needs WebDriverAgent signed with a development team. That is a human step in Xcode: Appium cannot do it, and an unsigned WDA is the commonest reason a real-device session never starts. Simulators need none of it.

## Appium 3 server and drivers

`appium` is a project dependency (`package.json`), and `@wdio/appium-service` starts it for the run, so no global install is needed. Drivers are installed into the Appium home once per machine:

```bash
npm ci
npx appium setup
npx appium driver list --installed
npx appium driver doctor uiautomator2
npx appium driver doctor xcuitest
```

- `appium setup` with no argument is the `mobile` preset: `uiautomator2`, `xcuitest` (on macOS) and `espresso`, plus the `images` and `inspector` plugins. To install only what the suite uses, run `npx appium driver install uiautomator2` and `npx appium driver install xcuitest` instead.
- Confirm the installed majors with `appium driver list --installed`: UiAutomator2 **8.x** and XCUITest **12.x** pair with Appium 3.8.0 (the `package.json` pins are 8.7.0 and 12.17.1). An older driver left in the Appium home after an upgrade is a mismatch, not a quirk: run `npx appium driver update installed`.
- `appium driver doctor <driver>` must come back clean before the first run. Fix what it names (the Android SDK path, `adb`, Xcode command-line tools) rather than skipping it.
- Server feature flags are **scoped** to a driver: `--allow-insecure=uiautomator2:adb_shell` or `--allow-insecure=*:session_discovery`. The unscoped form throws on Appium 3. In `wdio.conf.ts` the service takes the same value as `services: [['appium', { args: { allowInsecure: 'uiautomator2:chromedriver_autodownload' } }]]`. Add a flag only for the feature a test needs; Android WebView tests need `chromedriver_autodownload`.
- `appium-mcp` for live exploration carries its own drivers and needs no server, but it needs Node ≥ 22.
- Screen recording needs `ffmpeg` on the Appium host (always on iOS; on Android only for recordings above 180 s). See `qa/typescript/skills/evidence-capture/references/appium.md`.

## Project layout

```
<product>-mobile-tests/
├── package.json                # assets/package.json: every exact pin
├── tsconfig.json               # assets/tsconfig.json
├── wdio.conf.ts                # assets/wdio.conf.ts: Mocha, appium service, allure reporter
├── BaseTest.ts                 # assets/BaseTest.ts: the evidence hooks
├── env.ts                      # assets/env.ts: the one requiredEnv helper
├── .gitignore
├── .env.example
├── README.md
├── src/pages/mobile/
│   ├── BasePage.ts             # waits and the test-id helpers
│   ├── LoginPage.ts            # the landing screen the smoke verifies
│   ├── OrdersPage.ts
│   └── OrderRow.ts             # scoped component
└── test/specs/
    ├── smoke.spec.ts
    └── orders.spec.ts
```

The assets are one flat set. Copy the ten files, then make the three edits that the folders need:

1. `wdio.conf.ts`: `specs: ['./test/specs/*.spec.ts']`.
2. `orders.spec.ts` (and `smoke.spec.ts` below): import `requiredEnv` from `../../env.js` and the pages from `../../src/pages/mobile/<Page>.js`.
3. `tsconfig.json`: `"include": ["*.ts", "src/**/*.ts", "test/**/*.ts"]`.

The page files import each other with `./`, so they stay together. `LoginPage`, `OrdersPage`, `OrderRow` and `orders.spec.ts` are the worked example: replace them with the app's own screens, or delete them and keep the bases. Commit `package-lock.json`.

## Capabilities and configuration

**One mechanism:** environment variables, read by `wdio.conf.ts` through `requiredEnv`, which throws naming the missing variable. `PLATFORM` picks the capability set. There are no per-platform config files, no `wdio.android.conf.ts` / `wdio.ios.conf.ts` pair and no CLI flags for the device, and a test never branches on platform: the page's selector helper does.

| Variable | Used for |
|---|---|
| `PLATFORM` | `android` or `ios`; anything else fails with a message naming the value |
| `DEVICE_NAME` | The emulator AVD / simulator / device name |
| `APP_PATH` | Absolute path to the `.apk`, `.app` or `.ipa` |
| `PLATFORM_VERSION` | iOS only: the simulator or device OS version |
| `E2E_USER`, `E2E_PASSWORD` | The test account the example flow signs in with |
| `E2E_ORDER_NUMBER`, `E2E_ORDER_TITLE` | The seeded data the example spec asserts |
| `DEVICE_FARM` | Set on a device cloud: skips the local screen recording |

`.env.example`, committed, with no real values:

```
PLATFORM=android
DEVICE_NAME=Pixel_7_API_34
APP_PATH=/absolute/path/to/app.apk
PLATFORM_VERSION=
E2E_USER=
E2E_PASSWORD=
E2E_ORDER_NUMBER=
E2E_ORDER_TITLE=
```

Load a local copy with `set -a; source .env; set +a`; CI injects the same names from its secret store. Credentials and the app path never go into source or `wdio.conf.ts`.

Capability keys carry the `appium:` prefix (`'appium:automationName'`, `'appium:app'`): unprefixed `automationName` and `deviceName` select nothing in WDIO 10. The Android set includes `'appium:settings[disableIdLocatorAutocompletion]': true`, because Android prefixes every `id` lookup with `<package>:id/` and a React Native or Compose test id has no prefix. A Views app whose ids carry the package turns it off. Check the live page source before choosing (`ui-test-author/appium`, locator ladder).

## `.gitignore`

```
node_modules/
test-results/
allure-results/
evidence/
.env
```

`test-results/` holds the WDIO logs and `test-results/appium/`, where a failed test leaves its screenshot, page source, device log and recording. `allure-results/` is the report input and `evidence/` any hand-collected captures; none of the three is committed.

## First smoke

The smoke proves the whole chain (server, driver, device, app install, a screen object) before any real test is written. It launches the app and verifies the landing screen.

```typescript
import { LoginPage } from '../../src/pages/mobile/LoginPage.js';

describe('Smoke', () => {
  it('Should_ShowLandingScreen_When_AppLaunches', async () => {
    await new LoginPage().verifyPageLoaded();
  });
});
```

`verifyPageLoaded` is the screen object's one assertion: it checks the landing screen's landmark element and names the screen in its failure message, so the smoke needs no assertion of its own. For an app whose landing screen is not a login, replace `LoginPage` with that screen's page object.

## Create and run

```bash
mkdir <product>-mobile-tests && cd <product>-mobile-tests
git init
npm ci
npm run typecheck
```

Then, with a device booted (`adb devices` or `xcrun simctl list devices booted` shows it); the Appium service starts and stops the server itself:

```bash
PLATFORM=android DEVICE_NAME=Pixel_7_API_34 APP_PATH=/abs/app.apk npm run test:mobile -- --spec test/specs/smoke.spec.ts
PLATFORM=ios DEVICE_NAME="iPhone 15" PLATFORM_VERSION=17.4 APP_PATH=/abs/App.app npm run test:mobile -- --spec test/specs/smoke.spec.ts
```

The exit gate for the project: it typechecks, `appium driver doctor` is clean for each driver in use, and the smoke runs green on one device. Turning `allure-results/` into a report is `qa/reporting/typescript/skills/test-reports`; this skill installs no Allure CLI.

## Conventions (the shell only)

- **No `browser.pause`.** Waits are `browser.waitUntil` or the `waitFor*` element commands, inside the page's helpers; add a new wait there, never inline.
- **`maxInstances: 1`** and one session per worker: one emulator serves one spec file at a time. Raise it only with more devices or a cloud grid.
- **Screen objects expose intent, not selectors**; the test id first; the only assertion inside one is `verifyPageLoaded()`.
- **Session lifecycle** belongs to the WDIO runner and the `beforeTest` / `afterTest` hooks in `BaseTest.ts`; a spec never creates a session.

## Device clouds, CI and the supported lane

- A device cloud replaces the local server and emulator: switch the capabilities to the vendor's, set `DEVICE_FARM`, and follow `qa/typescript/skills/device-cloud`. Confirm the farm runs Appium 3 first.
- The pipeline (emulator job, upload of `test-results/appium/`, Allure publish) is `qa/cicd/typescript/skills/ci-pipelines`; this skill does not write CI.
- **Supported lane — Appium 2:** a device cloud that still runs Appium 2 needs WebdriverIO 9.x, UiAutomator2 4.x and XCUITest 9.x, because WDIO 10 and driver majors ≥ 5 / ≥ 10 refuse an Appium 2 server. Keep the layout and the environment variables; only the coordinates change, and the three WDIO 9 differences are listed in `ui-test-author/appium`.

## Setup checklist

- [ ] Node 24 (22.19+ supported), `ANDROID_HOME` and an emulator image present; Xcode and a simulator on macOS
- [ ] `package.json` pins `appium` 3.8.0, `webdriverio` 10.0.2 and the drivers; `package-lock.json` committed
- [ ] UiAutomator2 8.x and XCUITest 12.x listed by `appium driver list --installed`; `appium driver doctor` clean
- [ ] `wdio.conf.ts` uses Mocha, the `appium` service and the allure reporter; specs glob and imports follow the folders
- [ ] `wdio.conf.ts` reads `PLATFORM`, `DEVICE_NAME`, `APP_PATH` (and `PLATFORM_VERSION` on iOS) from the environment — nothing hard-coded
- [ ] `.env.example` committed, `.env` ignored; `.gitignore` takes `test-results/`, `allure-results/` and `evidence/`
- [ ] `smoke.spec.ts` launches the app and verifies the landing screen
- [ ] `npm run typecheck` clean; the smoke green on a booted device. Inside a plan task marked `Gate: none`, run none of this and report the files as "written, not run".
