---
name: qa-device-cloud-typescript
description: Use when the user needs the **real-device-cloud specifics** of running TypeScript + WebdriverIO Appium tests on a mobile device farm. Triggers: "upload our app to BrowserStack App Automate and run the WebdriverIO tests", "run our mobile suite across a real-device matrix in TypeScript", "test biometric login on a real device with WebdriverIO". Not for web grids (`qa-browser-cloud-setup-typescript`) or OS-surface features (`qa-mobile-native-features-typescript`).
---

# QA — Mobile Device Farm (TypeScript: WebdriverIO + Appium on a real-device cloud)

Runs TypeScript + WebdriverIO Appium tests against a **managed real-device cloud** — BrowserStack App Automate, Sauce Labs Real Device Cloud, or AWS Device Farm — and owns the parts that are *specific to the farm* rather than to a generic grid: getting the app **onto** the farm, **picking the devices**, exercising **real-device-only features** (GPS, network conditions, biometrics, permissions, locale), and the **remote-run** orchestration paradigm.

> **Boundary — this skill builds ON `qa/typescript/skills/browser-cloud-setup`, it does not repeat it.** `browser-cloud-setup` is the *wiring*: how you connect a driver to a remote hub (`@wdio/browserstack-service` / `@wdio/sauce-service`), the `bstack:options` / `sauce:options` capability-block schemas, mapping the plan's session cap onto WDIO `maxInstances`, surfacing the session URL + marking pass/fail, and starting a tunnel. All of that is assumed here and cross-linked, **not re-derived**. This skill is the layer above: the **app**, the **devices**, the **device-only capabilities**, and the **schedule-and-poll** paradigm — exactly the depth `browser-cloud-setup` said it defers to `device-cloud`.

## Stack

- Node 24, TypeScript (`strict: true`)
- **Appium**: WebdriverIO (`webdriverio` `remote()` / `@wdio/cli`), `@wdio/appium-service`, `@wdio/browserstack-service`
- **App upload (REST)**: global `fetch` + `FormData` + `Blob` (built into Node 22 and 24) — no extra HTTP dependency
- **Remote-run farm**: AWS SDK for JS v3 `@aws-sdk/client-device-farm` (`DeviceFarmClient`)
- **Condition waits**: `browser.waitUntil(...)` for the app; a bounded `pollUntil` (deadline + check interval) for AWS — never `browser.pause` / `setTimeout` *as* a wait
- Test runner: Vitest or WDIO's Mocha (`describe`/`it`); device matrix via `describe.each`
- Farm support code under `test/support/farm/`; credentials via **env vars only** (`BROWSERSTACK_USERNAME` / `BROWSERSTACK_ACCESS_KEY`; AWS creds via the default credential provider chain / OIDC)
- Runs in CI under `qa/cicd/typescript/skills/ci-pipelines`; the page objects come from `qa/typescript/skills/ui-test-author/appium` and run **unchanged** on the farm

## When to use

- Uploading a build (`.apk`/`.aab`/`.xapk`/`.ipa`) to the farm and referencing it from the `app` capability (by `bs://…` id or `custom_id`)
- Running the same Appium test across a **matrix of real devices / OS versions**
- Testing a feature that needs a **real device**: biometric login, GPS-based behavior, a specific network condition, app permissions, a localized build
- Driving **AWS Device Farm**'s upload → schedule → poll lifecycle (the suite runs on the farm, you collect the result)
- Choosing between a **live-session** farm (BrowserStack/Sauce — your test drives a remote device in real time) and a **remote-run** farm (Device Farm — you ship the test package and poll for the verdict)

## When NOT to use

- The connect / capability-block / parallelism / tunnel / session-status wiring → `qa/typescript/skills/browser-cloud-setup` (this skill assumes it)
- The Java / .NET device-farm stacks → `qa/{java,dotnet}/skills/device-cloud`
- Writing the mobile page objects / tests → `qa/typescript/skills/ui-test-author/appium`
- CI shard/worker mechanics (matrix fan-out, sharding props, Allure merge) → `qa/cicd/typescript/skills/ci-pipelines/*` — cross-link, don't duplicate
- Web (Playwright) cloud runs → `qa/typescript/skills/browser-cloud-setup`; this node is mobile real-device only

## Pick a paradigm — the choice that shapes everything

A device farm is one of two fundamentally different shapes. Get this right first — it decides whether your test code drives the device or whether you ship the test code to the farm.

| | **Live-session farm** | **Remote-run farm** |
|---|---|---|
| **Vendors** | BrowserStack App Automate, Sauce Labs RDC, LambdaTest | AWS Device Farm (also Firebase Test Lab) |
| **How it runs** | Your WDIO process runs locally/CI and drives a remote device over a hub URL in real time | You upload the **app + a packaged test suite**, the farm runs it on its own infra, you poll for the result |
| **The "app"** | Upload once → reference `bs://…` / `custom_id` in the `app` cap | Upload as a versioned **ARN**; referenced when you schedule the run |
| **Device choice** | A capability (`deviceName` + `osVersion`) per session | A **device-pool ARN** (a named set of devices) |
| **What you assert** | In your test, live, against the running device | After the run, by fetching artifacts / the run summary |
| **Real-device features** | Set as caps + injected mid-session via `browserstack_executor` | Configured on the scheduled run; less interactive |
| **This skill's focus** | App upload, device caps, device-only feature caps | `CreateUpload` → poll → `ScheduleRun` → poll `GetRun` |

**Decision rule.** *Want your existing WDIO/page-object suite to drive real devices with full live control (mid-session GPS changes, biometric prompts, network flips)?* → **live-session** (BrowserStack App Automate is the canonical here). *Already deep in AWS, need private-VPC devices, or want the farm to own execution end-to-end?* → **remote-run** (Device Farm). Most teams start live-session; reach for remote-run only when AWS integration or a hands-off run is the actual requirement. Don't build an abstraction over both — wire the one you need behind the farm helpers below.

---

## Live-session farm — BrowserStack App Automate (the canonical path)

### 1. App lifecycle — get the build onto the farm, reference it by id

The farm runs *an uploaded build*, never a local file path. Upload the `.apk`/`.aab`/`.ipa` once to the App Automate REST endpoint; you get back a `bs://…` id you put in the `app` capability. Give it a **`custom_id`** so re-uploads under the same id let the `app` cap always pick the latest build — the CI-friendly pattern (build → upload under `custom_id` → tests reference the `custom_id`, no id-plumbing between jobs).

```typescript
// test/support/farm/app-uploader.ts
import { readFile } from 'node:fs/promises';
import { basename } from 'node:path';
import type { BrowserStackCreds } from './farm-credentials';

const UPLOAD_URL = 'https://api-cloud.browserstack.com/app-automate/upload';

export interface UploadedApp {
  readonly appUrl: string;
  readonly customId: string;
}

/** Upload a local build under a custom_id. Re-uploading the same custom_id rotates "latest". */
export async function uploadApp(buildPath: string, customId: string, creds: BrowserStackCreds): Promise<UploadedApp> {
  const form = new FormData();
  const bytes = await readFile(buildPath);
  form.append('file', new Blob([bytes]), basename(buildPath));
  form.append('custom_id', customId);

  const auth = Buffer.from(`${creds.userName}:${creds.accessKey}`).toString('base64'); // env-sourced, never logged
  const res = await fetch(UPLOAD_URL, {
    method: 'POST',
    headers: { Authorization: `Basic ${auth}` }, // fetch sets the multipart boundary from FormData
    body: form,
  });
  if (!res.ok) throw new Error(`App upload failed: HTTP ${res.status}`);
  const json = (await res.json()) as { app_url: string }; // {"app_url":"bs://...","custom_id":...}
  return { appUrl: json.app_url, customId };
}
```

> **Reference the app three ways, in order of CI-friendliness:** (1) `custom_id` — `'appium:app': 'MyApp'` always picks the **last build uploaded under that id** (best for CI: no id passed between jobs); (2) the raw `bs://…` id from a one-off upload; (3) a **public URL** (`url` form-field on upload). Apps are **deleted 30 days after last use** — never assume an id is permanent; re-upload in the build job. Don't commit a `bs://…` id as if it were stable.

### 2. Device selection — pin a device, or fan out a matrix

On App Automate every session is a **real device** by default (no emulator flag needed). You pick it with `deviceName` + `osVersion` in `bstack:options`. To run a test across a **device matrix**, drive the device list from a `describe.each` (Vitest) or a WDIO capabilities array — one independent parameterized case per device, so a failure names the device. (The data-driven mechanics themselves belong to `qa/typescript/skills/data-driven-testing`; here it's the farm's device list.)

```typescript
// test/support/farm/device-matrix.ts
export interface TargetDevice {
  readonly deviceName: string;
  readonly osVersion: string;
}

/** The real-device matrix this suite targets. Keep it small and meaningful, not every device. */
export const DEVICE_MATRIX: readonly TargetDevice[] = [
  { deviceName: 'Samsung Galaxy S23', osVersion: '13.0' },
  { deviceName: 'Google Pixel 8',     osVersion: '14.0' },
  { deviceName: 'Samsung Galaxy S21', osVersion: '12.0' },
];
```

> **Pick devices by intent, not "all of them."** A device matrix is for covering the segments that actually differ (a vendor skin, an old OS, a screen size that breaks layout) — not for running 200 devices on every PR. Reserve the broad sweep for nightly. The cap on how many run at once is the **plan's session cap → WDIO `maxInstances`**, which `browser-cloud-setup` owns; don't set a value here that exceeds it. A **private/dedicated device pool** (a plan add-on) is selected the same way — the device is just reserved to your org.

### 3. Real-device-only capabilities — the reason a farm exists

These are the features you *cannot* exercise on a local emulator and the core value of a real-device farm. Set the static ones as caps at session start; flip the dynamic ones **mid-session** via the `browserstack_executor` JS hook. Build the session behind a factory, exactly as `qa/typescript/skills/ui-test-author/appium` does for local sessions — only the cap block and hub URL change.

```typescript
// test/support/farm/real-device-session.ts
import { remote, type Browser } from 'webdriverio';
import type { TargetDevice } from './device-matrix';
import type { BrowserStackCreds } from './farm-credentials';

/** A real-device Android session with device-only features set up front. */
export async function createRealDeviceSession(
  device: TargetDevice, appRef: string, sessionName: string, creds: BrowserStackCreds,
): Promise<Browser> {
  return remote({
    protocol: 'https',
    hostname: 'hub-cloud.browserstack.com',
    port: 443,
    path: '/wd/hub',
    capabilities: {
      platformName: 'Android',
      'appium:automationName': 'UiAutomator2',
      'appium:app': appRef,                    // bs://… or a custom_id
      'appium:autoGrantPermissions': true,     // grant manifest permissions on install
      'bstack:options': {
        userName: creds.userName,
        accessKey: creds.accessKey,
        deviceName: device.deviceName,         // a REAL device on App Automate
        osVersion: device.osVersion,
        projectName: 'checkout-mobile',
        buildName: process.env.BUILD_NAME ?? 'local-build',
        sessionName,
        // --- real-device-only features ---
        gpsLocation: '40.730610,-73.935242',   // "lat,long" — initial device location
        networkProfile: '4g-lte-advanced-good',// simulate a network condition
        language: 'fr',                        // localized-build testing
        locale: 'fr_FR',
        timezone: 'Europe/Paris',
        deviceOrientation: 'portrait',
        enableBiometric: true,                 // sensor instrumentation for biometric prompts
      },
    },
  });
}
```

Then drive the **dynamic** device features in the test through a small helper. Each is a `browserstack_executor` command (biometric / network) or the standard WDIO location API (GPS) — and each must be **awaited on the app's reaction**, never followed by a `pause`.

```typescript
// test/support/farm/device-features.ts
import type { Browser } from 'webdriverio';

export const DeviceFeatures = {
  /** Answer the next biometric prompt: match=true approves, false rejects. */
  async respondToBiometric(driver: Browser, match: boolean): Promise<void> {
    await driver.execute(`browserstack_executor: {"action":"performBiometric","arguments":{"match":${match}}}`);
  },

  /** Flip the network condition mid-session (e.g. drop to 2G to test a slow-network path). */
  async switchNetworkProfile(driver: Browser, profile: string): Promise<void> {
    await driver.execute(`browserstack_executor: {"action":"updateNetworkProfile","arguments":{"networkProfile":"${profile}"}}`);
  },

  /** Move the device GPS mid-session via the standard WDIO location API. */
  async setLocation(driver: Browser, latitude: number, longitude: number): Promise<void> {
    await driver.setGeoLocation({ latitude, longitude, altitude: 0 });
  },
};
```

> **The full real-device feature set** (App Automate): `gpsLocation` + mid-session `setGeoLocation`; `networkProfile` (presets like `2g-gprs-good`, `4g-lte-advanced-good`, or a custom bandwidth/latency/loss profile) + mid-session `updateNetworkProfile`; **biometric** via `enableBiometric` (sensor instrumentation injects a mock into the app) + `performBiometric`; `appium:autoGrantPermissions`; `language`/`locale`/`timezone`; `deviceOrientation`; plus camera-image injection, OTP/SIM workflows, and file upload-to-device for richer flows. **iOS** uses `'appium:automationName': 'XCUITest'` with the same `bstack:options` block (biometric = Touch/Face ID injection). Set static features as caps; flip dynamic ones mid-session.

### 4. Put it together — a real-device test

The test reads like any Appium test from `qa/typescript/skills/ui-test-author/appium`; only setup wires the farm. Note the assertion **waits on the app's reaction** to the biometric injection (an explicit `waitUntil`/page-object wait), never a `browser.pause`/`setTimeout`.

```typescript
// test/biometric-login.test.ts
import { describe, it, expect, afterEach } from 'vitest';
import type { Browser } from 'webdriverio';
import { DEVICE_MATRIX } from './support/farm/device-matrix';
import { createRealDeviceSession } from './support/farm/real-device-session';
import { DeviceFeatures } from './support/farm/device-features';
import { browserStackCreds } from './support/farm/farm-credentials';
// page objects from qa/typescript/skills/ui-test-author/appium

describe.each(DEVICE_MATRIX)('biometric login on $deviceName ($osVersion)', (device) => {
  let driver: Browser;
  afterEach(async () => {
    // session status + dashboard URL are owned by browser-cloud-setup's teardown; reuse it
    await driver?.deleteSession();
  });

  it('should log in when biometric is approved', async () => {
    driver = await createRealDeviceSession(device, 'checkout-app', `biometric-login@${device.deviceName}`, browserStackCreds());
    const login = new LoginPage(driver);             // intent-expressing page object, farm-agnostic
    await login.tapBiometricSignIn();
    await DeviceFeatures.respondToBiometric(driver, true); // approve the prompt
    const dashboard = await login.awaitDashboard();  // explicit wait inside the page object — no pause
    expect(await dashboard.isLoaded()).toBe(true);
  });
});
```

> **Reuse `browser-cloud-setup`'s teardown**, don't re-invent it: marking the session pass/fail (`browserstack_executor setSessionStatus`) and attaching the dashboard URL to Allure are that skill's job. This skill adds the *app/device/feature* setup; the session-result reporting is shared.

---

## Remote-run farm — AWS Device Farm

Device Farm is the **other paradigm**: you don't drive a live device — you upload the app and a packaged test suite, schedule a run against a **device-pool ARN**, and poll for the result. Every step that "waits" for AWS is a **bounded condition poll**, never a `setTimeout` *as* a wait.

```typescript
// test/support/farm/device-farm-runner.ts
import {
  DeviceFarmClient, CreateUploadCommand, GetUploadCommand, ScheduleRunCommand, GetRunCommand,
  type UploadType,
} from '@aws-sdk/client-device-farm';

/** Orchestrates an AWS Device Farm scheduled run: upload → poll → schedule → poll. */
export class DeviceFarmRunner {
  // built with the default credential provider chain / OIDC — no literal keys
  constructor(private readonly df: DeviceFarmClient) {}

  /** Create an upload, PUT the bytes, and wait until the farm reports it processed. Returns the upload ARN. */
  async uploadAndAwait(projectArn: string, name: string, type: UploadType, bytes: Buffer): Promise<string> {
    const created = await this.df.send(new CreateUploadCommand({ projectArn, name, type }));
    const upload = created.upload!;
    await this.putBytesToPresignedUrl(upload.url!, bytes); // HTTP PUT to the presigned URL

    await pollUntil(5 * 60_000, 5_000, async () => {
      const status = (await this.df.send(new GetUploadCommand({ arn: upload.arn }))).upload!.status;
      if (status === 'FAILED') throw new Error(`upload failed: ${name}`);
      return status === 'SUCCEEDED';
    });
    return upload.arn!;
  }

  /** Schedule the run and wait until it completes; return the aggregate result. */
  async scheduleAndAwait(projectArn: string, appArn: string, testPackageArn: string, devicePoolArn: string): Promise<string> {
    const scheduled = await this.df.send(new ScheduleRunCommand({
      projectArn, appArn, devicePoolArn,
      test: { type: 'APPIUM_JAVA_TESTNG', testPackageArn }, // Device Farm runs the uploaded package; type matches it
    }));
    const runArn = scheduled.run!.arn!;

    await pollUntil(30 * 60_000, 15_000, async () =>
      (await this.df.send(new GetRunCommand({ arn: runArn }))).run!.status === 'COMPLETED');

    return (await this.df.send(new GetRunCommand({ arn: runArn }))).run!.result!; // PASSED / FAILED / ERRORED
  }

  private async putBytesToPresignedUrl(_url: string, _bytes: Buffer): Promise<void> { /* fetch PUT — omitted */ }
}

/** Bounded condition poll — the interval is between CHECKS, not a sleep-as-wait. */
async function pollUntil(timeoutMs: number, intervalMs: number, condition: () => Promise<boolean>): Promise<void> {
  const deadline = Date.now() + timeoutMs;
  while (!(await condition())) {
    if (Date.now() > deadline) throw new Error('timed out waiting for condition');
    await new Promise((resolve) => setTimeout(resolve, intervalMs)); // poll interval between condition checks
  }
}
```

> **Device Farm specifics:** the test package type matches your suite (`APPIUM_JAVA_TESTNG_TEST_PACKAGE` + an `APPIUM_JAVA_TESTNG_TEST_SPEC` YAML; Device Farm runs the *uploaded* package, the JS `DeviceFarmClient` only orchestrates); the app type is `ANDROID_APP` / `IOS_APP`. A **device pool** is created once (in the console or via `CreateDevicePoolCommand` with a device-selection rule) and referenced by ARN. AWS auth comes from the **default credential provider chain** — in CI prefer **OIDC role assumption** over a long-lived access key (see `qa/cicd/typescript/skills/ci-pipelines`). Artifacts (logs, video, screenshots) are fetched per-job via `ListArtifactsCommand(runArn)` after the run completes.

---

## Secrets — env / provider chain only, never logged

Farm credentials are a billable, exfiltratable secret (CLAUDE.md hard rule). BrowserStack is a username + access key from env; AWS is the default credential provider chain (OIDC in CI). Read them lazily, fail loudly if missing, never log them, never persist them into an artifact or HAR.

```typescript
// test/support/farm/farm-credentials.ts
export interface BrowserStackCreds {
  readonly userName: string;
  readonly accessKey: string;
}

function required(name: string): string {
  const value = process.env[name];
  if (!value) throw new Error(`Missing env var ${name} — set it in your shell or CI secret store.`);
  return value;
}

export function browserStackCreds(): BrowserStackCreds {
  return { userName: required('BROWSERSTACK_USERNAME'), accessKey: required('BROWSERSTACK_ACCESS_KEY') };
}
// AWS Device Farm: no creds here — use the default provider chain / OIDC, region from AWS_REGION.
```

---

## Comparison — the three farms, app + device + features side by side

| Concept | **BrowserStack App Automate** | **Sauce Labs RDC** | **AWS Device Farm** |
|---|---|---|---|
| Paradigm | Live session | Live session | Remote run (upload + schedule) |
| App upload | `POST api-cloud.browserstack.com/app-automate/upload` → `bs://…` | `POST …/v1/storage/upload` (appStorage) → file id | `CreateUpload` → presigned PUT → ARN |
| App reference | `appium:app` = `bs://…` or `custom_id` | `appium:app` = `storage:filename=app.apk` or `storage:<id>` | `appArn` on `ScheduleRun` |
| "Always latest" | re-upload same `custom_id` | re-upload same filename | new upload ARN per build |
| Device choice | `bstack:options.deviceName` + `osVersion` | `sauce:options.deviceName` + `platformVersion` | device-pool ARN |
| Real device? | default | `appium:options` real-device flags | physical devices in the pool |
| GPS | `gpsLocation` + `setGeoLocation` | `setGeoLocation` | run config |
| Network sim | `networkProfile` + `updateNetworkProfile` | network condition caps | run config |
| Biometric | `enableBiometric` + `performBiometric` | biometric instrumentation | n/a (run-level) |
| Permissions | `appium:autoGrantPermissions` | `appium:autoGrantPermissions` | `appium:autoGrantPermissions` |
| Retention | apps deleted 30 days after last use | per plan | per S3 lifecycle |

**Capability-block schemas** (`bstack:options` vs `sauce:options`), **session pass/fail reporting**, **parallelism → `maxInstances`**, and **tunnels** are the same across these and are owned by `qa/typescript/skills/browser-cloud-setup` — see it for the side-by-side block table. This skill only adds the app/device/feature/remote-run layer on top.

---

## Anti-patterns

| Smell | Why it's wrong | Do instead |
|---|---|---|
| `'appium:app'` = a local file path | The farm runs an *uploaded* build; a local path is meaningless to a remote device | Upload first, reference the `bs://…` id / `custom_id` |
| Hard-coding a `bs://…` id in the repo | Apps are deleted 30 days after last use — the id rots | Re-upload in the build job under a stable `custom_id` |
| `browser.pause(5000)` after a biometric/network injection | Flaky and slow; the device reacts at its own pace | `browser.waitUntil(...)` on the app's observable reaction |
| `setTimeout` polling an AWS run | Wastes time, races the result | `pollUntil(...)` bounded on a deadline |
| Running every device on every PR | Slow, expensive, exceeds the session cap | A small intent-chosen matrix on PR; broad sweep nightly |
| `maxInstances` > plan session cap | Sessions queue or get rejected | Map the cap onto it (browser-cloud-setup owns this) |
| Credentials / access key in code or a committed config | Billable, exfiltratable secret | `required(...)` env read; AWS via OIDC |
| Re-deriving the capability block / tunnel / status here | Duplicates `browser-cloud-setup`, drifts out of sync | Cross-link `browser-cloud-setup`; add only the farm layer |
| Emulator caps when the test needs a real device | Biometric/GPS/network features need real hardware | Pin a real `deviceName` (App Automate default) |

## Rules

### App lifecycle
- Upload the build to the farm and reference it by **id** (`bs://…`) or **`custom_id`** — never a local path in the `app` cap.
- Prefer `custom_id` in CI: re-upload under the same id so the `app` cap always picks the latest build with no id-plumbing between jobs.
- Treat the app id as **ephemeral** (30-day retention) — re-upload in the build job; never commit an id as if stable.

### Device selection
- Pin a real device with `deviceName` + `osVersion` (App Automate sessions are real devices by default).
- Drive a **device matrix** from `describe.each` / a WDIO capabilities array (one independent case per device); pick devices by intent, not "all of them."
- Keep concurrent devices ≤ the plan session cap — that cap → WDIO `maxInstances` is owned by `browser-cloud-setup`.

### Real-device features
- Set static features (`gpsLocation`, `networkProfile`, `language`/`locale`/`timezone`, `deviceOrientation`, `enableBiometric`, `autoGrantPermissions`) as caps at session start.
- Flip dynamic features mid-session via `browserstack_executor` (biometric / network) or `setGeoLocation` (GPS).
- After any injection, **await the app's observable reaction** (`waitUntil` / a page-object wait), never `browser.pause`/`setTimeout`.

### Remote-run (Device Farm)
- `CreateUpload` → PUT bytes → **poll until SUCCEEDED**; `ScheduleRun` → **poll until COMPLETED**; both via a bounded condition poll, never sleep.
- AWS auth via the default provider chain / **OIDC** in CI, never a literal key. Fetch artifacts after the run via `ListArtifacts`.

### Secrets & boundary
- Credentials via env / provider chain only, read lazily, never logged or persisted to an artifact.
- Do **not** re-derive capability blocks, parallelism, tunnels, or session-status reporting here — cross-link `qa/typescript/skills/browser-cloud-setup`.

## Generation steps

1. Confirm the **paradigm** (live-session BrowserStack/Sauce vs remote-run Device Farm) and **platform** (Android/iOS).
2. Add `test/support/farm/farm-credentials.ts` (env reads; AWS via provider chain) — no literals.
3. **Live-session**: add `uploadApp` (REST upload → `bs://…`/`custom_id`), `createRealDeviceSession` (real-device caps + the device-only features the test needs), and `DeviceFeatures` for mid-session injection; drive a device matrix from `describe.each`.
4. **Remote-run**: add `DeviceFarmRunner` (`CreateUpload` → poll → `ScheduleRun` → poll `GetRun`) with the bounded `pollUntil` helper.
5. Reuse `browser-cloud-setup`'s session-status + dashboard-URL teardown; map the device count onto `maxInstances` per its rules.
6. Run **one** device/session first to confirm the upload + caps + features before fanning the matrix out; confirm the session/run appears on the dashboard with the right build/project tags. Inside a plan task marked `Gate: none`, run none of this and report the files as "written, not run".

## Cross-references

- **`qa/typescript/skills/browser-cloud-setup`** — the **prerequisite wiring** this skill builds on: connect (`@wdio/browserstack-service`), capability-block schemas, parallelism → `maxInstances`, tunnels, session pass/fail + dashboard URL. This skill adds the app/device/feature/remote-run layer; that one owns the connection plumbing.
- **`qa/java/skills/device-cloud`** (canonical) + **`qa/dotnet/skills/device-cloud`** — sibling device-farm stacks. Same four moves (app lifecycle → device selection → real-device features → remote-run), different SDKs. Structure ported, not code.
- **`qa/typescript/skills/ui-test-author/appium`** — writes the mobile page objects / tests that run **unchanged** on the farm; this skill only swaps the local session for a farm one.
- **`qa/typescript/skills/data-driven-testing`** — the `describe.each` device-matrix mechanics (one independent case per device); this skill supplies the device list, that one the data-driven discipline.
- **`qa/cicd/typescript/skills/ci-pipelines`** — build-then-upload job, OIDC for AWS, sharding the matrix across runners (cross-link; don't duplicate).
- **`qa/reporting/typescript/skills/test-reports`** — attach the session/run dashboard URL + device name to the report so a farm failure is one click from the replay.
