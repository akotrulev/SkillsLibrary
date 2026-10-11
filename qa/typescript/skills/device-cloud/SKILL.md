---
name: device-cloud
description: Use when the user needs the **real-device-cloud specifics** of running TypeScript + WebdriverIO Appium tests on a mobile device farm. Triggers: "upload our app to BrowserStack App Automate and run the WebdriverIO tests", "run our mobile suite across a real-device matrix in TypeScript", "test biometric login on a real device with WebdriverIO", "does the farm run Appium 3". Not for web grids (`qa-typescript:browser-cloud-setup`) or OS-surface features (`qa-typescript:mobile-native-features`).
---

# QA — Mobile Device Farm (TypeScript: WebdriverIO + Appium on a real-device cloud)

Runs TypeScript + WebdriverIO Appium tests against a **managed real-device cloud** — BrowserStack App Automate, Sauce Labs Real Device Cloud, or AWS Device Farm — and owns what is *specific to the farm*: getting the app **onto** it, **picking the devices**, **real-device-only features** (GPS, network, biometrics, locale), and the **remote-run** paradigm.

> **This skill builds on `qa/typescript/skills/browser-cloud-setup`**, which owns the wiring: hub, capability blocks, session cap → `maxInstances`, status, tunnels. This one adds the app, the devices, the device-only capabilities and schedule-and-poll.

## Stack

- Node 24, TypeScript `strict: true`; the WebdriverIO and Appium pins are the **Versions** table of `qa/typescript/skills/ui-test-author/appium`
- **The farm runs through `wdio.conf.ts`**, never a standalone `remote()` session: the page objects use WDIO's global `$`, which only a runner binds. A farm is a second config that imports the local one and overrides the connection and the capabilities.
- **Mocha**; the matrix is a **capabilities array**, one session per device, so a failure names its device
- App upload: global `fetch` + `FormData` + `Blob` (built into Node 22 and 24)
- Remote-run: `@aws-sdk/client-device-farm` (`DeviceFarmClient`)
- Waits: `browser.waitUntil(...)`, and a bounded poll for AWS; never `browser.pause`
- Farm code under `test/support/farm/`; credentials from env only (`BROWSERSTACK_USERNAME`, `BROWSERSTACK_ACCESS_KEY`; AWS through its default credential chain or OIDC)

## Does the farm run Appium 3?

The primary lane is Appium 3 with WebdriverIO 10. WDIO 10 needs an Appium 3 server, so **check the vendor before bumping**; a cloud still on Appium 2 keeps the suite on WDIO 9 and Appium 2, the supported lane.

1. Read the vendor's own list of Appium versions, and the capability that selects one: `appiumVersion` inside `bstack:options` (BrowserStack) or `sauce:options` (Sauce Labs). BrowserStack's public page listed only 2.x and Sauce's migration page showed 2.13.1 on 2026-10-10, so neither is assumed to offer 3.
2. Set the capability to a 3.x value and start one session. A vendor without Appium 3 rejects it or falls back to 2; a green run does not tell which.
3. `browser.capabilities` on the started session shows what the vendor actually granted; `GET <hub>/status` reports `build.version` where the hub proxies it.
4. Check the vendor's WDIO service as well. `@wdio/browserstack-service` was on 9.39.4 on 2026-10-11, with a peer of `@wdio/cli` ≤ 9, so it does not install on WDIO 10; `@wdio/sauce-service` has a 10.0.2. On WDIO 10 against BrowserStack, connect without the service (below) and mark the status in the hook.

## When to use

- Uploading a build (`.apk`/`.aab`/`.xapk`/`.ipa`) and referencing it from the `app` capability
- One suite across a **matrix of real devices and OS versions**
- A feature that needs a **real device**: biometric, GPS, a network condition, a localized build
- AWS Device Farm's upload → schedule → poll lifecycle, or choosing between the two paradigms

## When NOT to use

- Connect, capability blocks, parallelism, tunnels, status wiring → `qa/typescript/skills/browser-cloud-setup`
- Java / .NET farms → `qa/{java,dotnet}/skills/device-cloud`
- Page objects and tests → `qa/typescript/skills/ui-test-author/appium`
- CI matrix and sharding → `qa/cicd/typescript/skills/ci-pipelines`

## Pick a paradigm

| | **Live-session farm** | **Remote-run farm** |
|---|---|---|
| **Vendors** | BrowserStack App Automate, Sauce Labs RDC, LambdaTest | AWS Device Farm (also Firebase Test Lab) |
| **How it runs** | Your WDIO process drives a remote device over a hub URL | You upload the **app and a packaged suite**; the farm runs it and you poll |
| **The app and devices** | Upload once, reference `bs://…` / `custom_id`; devices are capabilities | An uploaded **ARN** and a **device-pool ARN**, passed when scheduling |
| **What you assert** | In the test, live | After the run, from artifacts and the run summary |

**Decision rule.** Live control of real devices (mid-session GPS, biometric, network) → live-session, BrowserStack first. Already in AWS, private-VPC devices, or the farm owning execution → remote-run. No abstraction over both.

---

## Live-session farm — BrowserStack App Automate

### 1. App lifecycle

The farm runs an *uploaded build*, never a local path. Upload under a **`custom_id`** so the `app` capability always picks the latest build with no id passed between CI jobs.

```typescript
import { readFile } from 'node:fs/promises';
import { basename } from 'node:path';
import type { BrowserStackCreds } from './farm-credentials';

const UPLOAD_URL = 'https://api-cloud.browserstack.com/app-automate/upload';

export interface UploadedApp {
  readonly appUrl: string;
  readonly customId: string;
}

export async function uploadApp(buildPath: string, customId: string, creds: BrowserStackCreds): Promise<UploadedApp> {
  const form = new FormData();
  form.append('file', new Blob([await readFile(buildPath)]), basename(buildPath));
  form.append('custom_id', customId);

  const auth = Buffer.from(`${creds.userName}:${creds.accessKey}`).toString('base64');
  const response = await fetch(UPLOAD_URL, { method: 'POST', headers: { Authorization: `Basic ${auth}` }, body: form });
  if (!response.ok) throw new Error(`App upload failed: HTTP ${response.status}`);
  const body = (await response.json()) as { app_url: string };
  return { appUrl: body.app_url, customId };
}
```

Reference the app by `custom_id`, by the `bs://…` id of one upload, or by a public URL. Apps are **deleted 30 days after last use**, so re-upload in the build job and never commit a `bs://…` id.

### 2. Device selection — a capabilities array is the matrix

Every App Automate session is a real device. Pick it with `deviceName` and `osVersion` in `bstack:options`, and run a matrix by mapping the device list onto the capabilities array.

```typescript
export interface TargetDevice {
  readonly deviceName: string;
  readonly osVersion: string;
}

export const DEVICE_MATRIX: readonly TargetDevice[] = [
  { deviceName: 'Samsung Galaxy S23', osVersion: '13.0' },
  { deviceName: 'Google Pixel 8', osVersion: '14.0' },
  { deviceName: 'Samsung Galaxy S21', osVersion: '12.0' },
];
```

Choose devices by intent (a vendor skin, an old OS, a layout-breaking screen), and keep the broad sweep for nightly. `maxInstances` never exceeds the plan's session cap (`browser-cloud-setup` owns the mapping).

### 3. The farm config and the real-device capabilities

Static features are capabilities at session start; dynamic ones flip mid-session through `browserstack_executor`.

```typescript
import { config as localConfig } from './wdio.conf.js';
import { afterTest as recordEvidence } from './BaseTest.js';
import { requiredEnv } from './env.js';
import { DEVICE_MATRIX, type TargetDevice } from './test/support/farm/device-matrix.js';
import { markSessionStatus } from './test/support/farm/device-features.js';

function realDeviceCapabilities(device: TargetDevice) {
  return {
    platformName: 'Android',
    'appium:automationName': 'UiAutomator2',
    'appium:app': requiredEnv('APP_REFERENCE'),
    'appium:autoGrantPermissions': true,
    'bstack:options': {
      appiumVersion: requiredEnv('APPIUM_VERSION'),
      deviceName: device.deviceName,
      osVersion: device.osVersion,
      projectName: 'checkout-mobile',
      buildName: process.env.BUILD_NAME ?? 'local-build',
      sessionName: `mobile@${device.deviceName}`,
      gpsLocation: '40.730610,-73.935242',
      networkProfile: '4g-lte-advanced-good',
      language: 'fr',
      locale: 'fr_FR',
      timezone: 'Europe/Paris',
      deviceOrientation: 'portrait',
      enableBiometric: true,
    },
  };
}

export const config: WebdriverIO.Config = {
  ...localConfig,
  user: requiredEnv('BROWSERSTACK_USERNAME'),
  key: requiredEnv('BROWSERSTACK_ACCESS_KEY'),
  hostname: 'hub-cloud.browserstack.com',
  port: 443,
  path: '/wd/hub',
  protocol: 'https',
  services: [],
  maxInstances: Number(requiredEnv('FARM_SESSION_CAP')),
  capabilities: DEVICE_MATRIX.map(realDeviceCapabilities),
  afterTest: async (...args: Parameters<typeof recordEvidence>) => {
    await recordEvidence(...args);
    await markSessionStatus(args[2].passed);
  },
};
```

Set `DEVICE_FARM=1` for these runs: `BaseTest.ts` then skips the local recording, because the vendor already records the session. An iOS entry uses `XCUITest` with the same block.

The dynamic features are helpers; each is awaited on the app's reaction, never followed by a pause.

```typescript
import { browser } from '@wdio/globals';

function executor(action: string, args: Record<string, unknown>): string {
  return `browserstack_executor: ${JSON.stringify({ action, arguments: args })}`;
}

export async function respondToBiometric(match: boolean): Promise<void> {
  await browser.execute(executor('performBiometric', { match }));
}

export async function switchNetworkProfile(networkProfile: string): Promise<void> {
  await browser.execute(executor('updateNetworkProfile', { networkProfile }));
}

export async function setLocation(latitude: number, longitude: number): Promise<void> {
  await browser.setGeoLocation({ latitude, longitude, altitude: 0 });
}

export async function markSessionStatus(passed: boolean): Promise<void> {
  await browser.execute(executor('setSessionStatus', { status: passed ? 'passed' : 'failed', reason: 'Set by the suite' }));
}
```

Sauce uses `sauce:options` and `executeScript('sauce:job-result=passed')`; LambdaTest uses `LT:Options` and `lambda-status=passed`. `networkProfile` takes presets such as `2g-gprs-good` or a custom profile.

### 4. The test

The spec is an ordinary Mocha spec from `ui-test-author/appium`; only the config wires the farm.

```typescript
import { expect } from '@wdio/globals';
import { LoginPage } from './LoginPage.js';
import { respondToBiometric } from './test/support/farm/device-features.js';

describe('Biometric login', () => {
  it('Should_ReachDashboard_When_BiometricIsApproved', async () => {
    const login = new LoginPage();
    await login.tapBiometricSignIn();

    await respondToBiometric(true);

    const dashboard = await login.awaitDashboard();
    await expect(dashboard.root()).toBeDisplayed({ message: 'Dashboard after an approved biometric' });
  });
});
```

Run it with `npx wdio run wdio.browserstack.conf.ts`. Where a vendor service exists for the WDIO major (`@wdio/sauce-service`), use it instead of `markSessionStatus`.

---

## Remote-run farm — AWS Device Farm

Device Farm runs the **uploaded** package; the SDK only orchestrates. A TypeScript WebdriverIO suite is an **Appium Node.js** run: the test package is `APPIUM_NODE_TEST_PACKAGE` (a zip of the suite with its dependencies), the spec is `APPIUM_NODE_TEST_SPEC` (YAML), and the run's `test.type` is **`APPIUM_NODE`**. `APPIUM_JAVA_TESTNG` is the Java type and is wrong for this suite. The app type is `ANDROID_APP` / `IOS_APP`. A **device pool** is made once (console or `CreateDevicePoolCommand`) and referenced by ARN. The farm starts its own Appium on the device host, so its config connects to that address and carries no `appium` service. Every wait on AWS is a **bounded poll**.

The `DeviceFarmRunner` (upload → poll → schedule → poll, with a real presigned `PUT` that fails on a non-OK status) is in [`references/aws-device-farm.md`](references/aws-device-farm.md). AWS auth comes from the default credential chain; in CI prefer OIDC role assumption over a long-lived key (`qa/cicd/typescript/skills/ci-pipelines`). The verdict is `PASSED`, `FAILED` or `ERRORED`, and artifacts are fetched per job after the run.

---

## Secrets — env or provider chain only

Farm credentials are billable and exfiltratable: read lazily, fail loudly, never log or write them into an artifact.

```typescript
import { requiredEnv } from '../../../env.js';

export interface BrowserStackCreds {
  readonly userName: string;
  readonly accessKey: string;
}

export function browserStackCreds(): BrowserStackCreds {
  return { userName: requiredEnv('BROWSERSTACK_USERNAME'), accessKey: requiredEnv('BROWSERSTACK_ACCESS_KEY') };
}
```

## The three farms side by side

| Concept | **BrowserStack App Automate** | **Sauce Labs RDC** | **AWS Device Farm** |
|---|---|---|---|
| Paradigm | Live session | Live session | Remote run |
| App upload | `POST api-cloud.browserstack.com/app-automate/upload` → `bs://…` | `POST …/v1/storage/upload` → file id | `CreateUpload` → presigned PUT → ARN |
| App reference | `appium:app` = `bs://…` or `custom_id` | `storage:filename=app.apk` or `storage:<id>` | `appArn` on `ScheduleRun` |
| Device choice | `bstack:options.deviceName` + `osVersion` | `sauce:options.deviceName` + `platformVersion` | device-pool ARN |
| Appium version | `bstack:options.appiumVersion` | `sauce:options.appiumVersion` | set by the test spec |
| GPS / network / biometric | `gpsLocation`, `networkProfile`, `enableBiometric` + executor | `setGeoLocation`, network caps, instrumentation | run config |
| Status | `setSessionStatus` executor | `sauce:job-result=…` | the run result |

## Anti-patterns

| Smell | Do instead |
|---|---|
| A standalone `remote()` session or `describe.each` with `new LoginPage(driver)` | `wdio.conf.ts` plus a capabilities array; pages use the global `$` |
| `appium:app` set to a local path | Upload, then reference `bs://…` or a `custom_id` |
| A committed `bs://…` id | Re-upload in the build job under a stable `custom_id` |
| `browser.pause` after an injection | `waitUntil` on the app's reaction |
| `maxInstances` above the plan's session cap | Map the cap onto it |
| `APPIUM_JAVA_TESTNG` for a WebdriverIO suite | `APPIUM_NODE` with its package and spec |
| Bumping to WDIO 10 without asking the vendor | Check the Appium version first; stay on WDIO 9 if the farm is on Appium 2 |
| A credential in code or a committed config | `requiredEnv`; AWS through OIDC |

## Generation steps

1. Confirm the paradigm, the platform and the vendor's Appium version.
2. Live session: `farm-credentials.ts`, `uploadApp`, `device-matrix.ts`, `device-features.ts`, the farm config. Remote run: `DeviceFarmRunner`.
3. Map the device count onto `maxInstances` per `browser-cloud-setup`, run **one** device first, and confirm the dashboard shows the right build tags. Inside a `Gate: none` plan task run none of this and report the files as "written, not run".

## Cross-references

- **`qa/typescript/skills/browser-cloud-setup`** — hub, capability blocks, parallelism, tunnels, status
- **`qa/typescript/skills/ui-test-author/appium`** — the pages, tests and `BaseTest.ts` that run unchanged on a farm; its Versions table owns the pins
- **`qa/typescript/skills/evidence-capture`** — a farm run keeps the dashboard URL and the status, not a local video
- **`qa/java/skills/device-cloud`**, **`qa/dotnet/skills/device-cloud`** — the sibling stacks
- **`qa/cicd/typescript/skills/ci-pipelines`** — build-then-upload, OIDC for AWS, sharding the matrix
- **`qa/reporting/typescript/skills/test-reports`** — the session or run URL and the device name in the report
