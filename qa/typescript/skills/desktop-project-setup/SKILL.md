---
name: desktop-project-setup
description: Use when starting a desktop E2E project in TypeScript (WebdriverIO 10, Appium 3, Mac2, WinCore). Triggers "scaffold a desktop test project". Not for writing tests (desktop-window-objects).
disable-model-invocation: true
---

# Desktop Test Project Scaffold (TypeScript, WebdriverIO 10)

Stands up a **runnable Appium 3 desktop test project from zero**: package layout, exact versions, the Appium server, the pinned Mac2 and WinCore drivers, OS prerequisites, the env-driven capabilities and a first smoke run. It owns the **project shell and the environment**. The shared rules (drivers, the test-id contract, CI hosts) are `qa/_shared/desktop-testing`; load it first. The mobile twin is `qa/typescript/skills/mobile-project-setup`, whose `ui-test-author/appium/assets/` `tsconfig.json`, `env.ts` and `package.json` this skill reuses rather than copies.

**Version rule:** Node 24 (22 maintenance), TypeScript strict. WebdriverIO 10 needs Node ≥ 22.19 and an Appium 3 server. Node 20 is end-of-life: never target it. Electron and Tauri apps are out of scope.

## Versions

Verified 2026-11-15; the pins are those of `mobile-project-setup` and `tools/qa-version-check.py`.

| Concern | Package / tool | Version | Notes |
|---|---|---|---|
| Runtime | Node | **24** | `engines.node` `>=22.19.0` |
| Language | `typescript` | **5.9.3** | `strict: true`, `noUncheckedIndexedAccess`, `module: NodeNext` |
| Automation | `webdriverio` · `@wdio/cli` · `@wdio/globals` · `@wdio/appium-service` | **10.0.2** | Needs Appium 3 |
| Runner pieces | `@wdio/mocha-framework` · `@wdio/types` | **10.0.1** | Mocha is the framework |
| Matchers, logger, reporting | `expect-webdriverio` · `@wdio/logger` · `@wdio/allure-reporter` | **8.0.0** · **10.0.0** · **10.0.1** | |
| Appium server | `appium` | **3.8.0** | Latest is 3.9.1; not moved here |
| macOS driver | `appium-mac2-driver` | **4.6.1** | Peer `appium ^3.0.0-rc.2`: includes 3.8.0. 5.x needs Appium 4 |
| Windows driver | `appium-wincore-driver` | **3.3.2** | Peer `appium ^3.0.0-rc.2`: includes 3.8.0. 4.x needs Appium 4 |
| Windows fallback | `appium-novawindows-driver` | **1.5.0** | Peer `appium ^3.0.0-rc.2`. Same `AutomationId` contract |

**From 4.0 GA:** Appium 4 with Mac2 5.x and WinCore 4.x. Appium 4 is in beta with no GA date; do not scaffold on it.

## Prerequisites

| Host | Need | Check |
|---|---|---|
| Both | Node 24 (22.19+), npm | `node --version` |
| macOS | macOS 11.3+, **Xcode 13+** with command-line tools, the app built and installed | `xcodebuild -version` |
| macOS | **Xcode Helper** granted the Accessibility permission (System Settings → Privacy & Security → Accessibility) | a human step |
| macOS | `sudo automationmodetool enable-automationmode-without-authentication`, to silence the automation-mode prompt | a human step; `sudo` cannot run unattended |
| macOS | `WebDriverAgentRunner-Runner.app` granted Accessibility, **only** for moving or resizing windows and `useDomIdAsAccessibilityId`. The grant is lost on every ad-hoc WDA rebuild unless WDA is signed with a stable identity | `appium driver run mac2 setup-accessibility` may script it |
| Windows | Windows 10 or later, the app built or installed (exe path or UWP AUMID) | |
| Windows | An **interactive session with autologon**: the runner is a process, not a service | see `qa/_shared/desktop-testing` § CI and hosts |

A headless Mac or a disconnected RDP session is the commonest reason a desktop session never starts or clicks land nowhere. Both permissions are human steps: report them, never skip them.

## Appium 3 server and drivers

`appium` is a project dependency and `@wdio/appium-service` starts it for the run. Install **only the driver for the host**, with an explicit version, into the Appium home once per machine:

```bash
npm ci
npx appium driver install mac2@4.6.1
npx appium driver install --source=npm appium-wincore-driver@3.3.2
npx appium driver list --installed
npx appium driver doctor mac2
```

- Run the first command on a Mac, the second on Windows. **Never an unpinned `appium driver install mac2`**: it may resolve to a major that needs Appium 4.
- `appium driver list --installed` must show `mac2@4.6.1` or `wincore@3.3.2`. Anything else is a mismatch; `npx appium driver update` is the wrong fix because it can cross a major.
- `appium driver doctor mac2` must come back clean before the first run. There is no equivalent doctor check for WinCore; its proof is the smoke run.
- Fallback when WinCore misbehaves on a legacy app: `npx appium driver install --source=npm appium-novawindows-driver@1.5.0` and `appium:automationName: 'NovaWindows'`. The locators do not change. Record why in the README.
- The legacy Appium Windows driver and WinAppDriver are never installed (D9).
- Feature flags are scoped, `--allow-insecure=mac2:<feature>`; add one only for the feature a test needs.

## Project layout

```
<product>-desktop-tests/
├── package.json                # the mobile asset's pins, minus the mobile drivers
├── tsconfig.json               # ui-test-author/appium/assets/tsconfig.json
├── wdio.desktop.conf.ts
├── env.ts                      # ui-test-author/appium/assets/env.ts
├── .env.example
├── .gitignore
├── README.md
├── src/windows/
│   ├── BaseWindow.ts           # waits and the test-id finder
│   ├── LibraryWindow.ts        # the landing window the smoke verifies
│   └── AlbumRow.ts             # scoped component
└── test/specs/
    └── smoke.spec.ts
```

Copy `tsconfig.json` and `env.ts` from `qa/typescript/skills/ui-test-author/appium/assets/`, take `package.json` from the same place, delete its `appium-uiautomator2-driver` and `appium-xcuitest-driver` lines (the desktop drivers are installed into the Appium home, below), rename the `test:mobile` script to `test:desktop` (`wdio run ./wdio.desktop.conf.ts`), and set `"include": ["*.ts", "src/**/*.ts", "test/**/*.ts"]`. Commit `package-lock.json`. The window classes are written with `desktop-window-objects`.

## Capabilities and configuration

**One mechanism:** environment variables read by `wdio.desktop.conf.ts` through `requiredEnv`. `PLATFORM` picks the capability set; there are no per-platform config files, no CLI flags for the app and a test never branches on platform: the window object's locator map does.

| Variable | Used for |
|---|---|
| `PLATFORM` | `macos` or `windows`; anything else fails naming the value |
| `APP_ID` | macOS: the bundle id. Windows: the exe path or the UWP AUMID |
| `APP_ARGUMENTS` | Optional launch arguments (a test data folder, a feature flag) |
| `E2E_USER`, `E2E_PASSWORD` | The test account the example flow signs in with |

```typescript
import { requiredEnv } from './env.js';

function macCapabilities() {
  return {
    platformName: 'mac',
    'appium:automationName': 'mac2',
    'appium:bundleId': requiredEnv('APP_ID'),
  };
}

function windowsCapabilities() {
  return {
    platformName: 'Windows',
    'appium:automationName': 'Wincore',
    'appium:app': requiredEnv('APP_ID'),
    'appium:ms:waitForAppLaunch': 30,
  };
}

function capabilitiesFor(platform: string) {
  if (platform === 'macos') return macCapabilities();
  if (platform === 'windows') return windowsCapabilities();
  throw new Error(`PLATFORM must be macos or windows, got ${platform}`);
}

export const config: WebdriverIO.Config = {
  runner: 'local',
  framework: 'mocha',
  specs: ['./test/specs/*.spec.ts'],
  maxInstances: 1,
  capabilities: [capabilitiesFor(requiredEnv('PLATFORM'))],
  services: ['appium'],
  reporters: [['allure', { outputDir: 'allure-results', disableWebdriverScreenshotsReporting: true }]],
  outputDir: 'test-results/desktop/logs',
  logLevel: 'warn',
  mochaOpts: { ui: 'bdd', timeout: 120_000 },
};
```

- Capability keys carry the `appium:` prefix except `platformName`. `appium:bundleId` is mandatory on Mac2: the default app is Finder.
- **`maxInstances: 1`.** Mac2 runs one session at a time and a new session ends the old one; Windows focus is exclusive. Parallelism is more machines, never more workers.
- A session starts a fresh app by default. Keep state only deliberately: `appium:noReset: true` (Mac2) or `appium:shouldCloseApp: false` (WinCore).
- Evidence on failure (screenshot and page source into `test-results/desktop/<test title>/`) comes from one `afterTest` hook that calls `browser.takeScreenshot()` and `browser.getPageSource()`; the failure message is written there, never swallowed. Model it on `ui-test-author/appium/assets/BaseTest.ts` and drop the device-log and recording parts.

`.env.example`, committed, with no real values:

```
PLATFORM=macos
APP_ID=com.example.Library
APP_ARGUMENTS=
E2E_USER=
E2E_PASSWORD=
```

Load a local copy with `set -a; source .env; set +a`; CI injects the same names from its secret store. Credentials and the app path never go into source.

## `.gitignore`

```
node_modules/
test-results/
allure-results/
.env
```

## First smoke

The smoke proves the chain (server, driver, permissions, app launch, a window object) before any real test is written.

```typescript
import { LibraryWindow } from '../../src/windows/LibraryWindow.js';

describe('Smoke', () => {
  it('Should_ShowLibraryWindow_When_AppLaunches', async () => {
    await new LibraryWindow().verifyWindowLoaded();
  });
});
```

`verifyWindowLoaded` checks one landmark container id and names the window in its failure message. Run it with the app installed:

```bash
PLATFORM=macos APP_ID=com.example.Library npm run test:desktop -- --spec test/specs/smoke.spec.ts
PLATFORM=windows APP_ID='C:\Apps\Library\Library.exe' npm run test:desktop -- --spec test/specs/smoke.spec.ts
```

The exit gate: it typechecks, the driver is listed at its pinned version, `appium driver doctor mac2` is clean (macOS), and the smoke is green on one host.

## CI

Desktop E2E runs on **owned hardware**: a self-hosted Windows agent in an interactive autologon session (Microsoft-hosted Azure agents do not support visible UI tests), and a Mac with Xcode and the permissions above. No device cloud runs native desktop apps. The pipeline itself is `qa/cicd/typescript/skills/ci-pipelines`; this skill does not write CI.

## Setup checklist

- [ ] Node 24 (22.19+); Xcode and the two Accessibility grants on macOS, an interactive autologon session on Windows
- [ ] `package.json` pins `appium` 3.8.0 and `webdriverio` 10.0.2; `package-lock.json` committed
- [ ] `appium driver list --installed` shows `mac2@4.6.1` or `wincore@3.3.2`; no unpinned install
- [ ] `wdio.desktop.conf.ts` reads `PLATFORM` and `APP_ID` from the environment; `maxInstances: 1`
- [ ] `.env.example` committed, `.env` ignored
- [ ] `smoke.spec.ts` launches the app and verifies the landing window
- [ ] `npm run typecheck` clean; the smoke green on the host
