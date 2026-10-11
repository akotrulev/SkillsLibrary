---
name: device-cloud
description: Use when the user needs the **real-device-cloud specifics** of running Java Appium tests on a mobile device farm. Triggers: "upload our app to BrowserStack App Automate and run the Appium Java tests", "run our TestNG mobile suite across a real-device matrix", "test biometric login on a real device on BrowserStack". Not for web grids (`qa-java:browser-cloud-setup`) or OS-surface features (`qa-java:mobile-native-features`).
---

# QA — Mobile Device Farm (Java: Appium java-client on a real-device cloud)

Runs Java Appium tests against a **managed real-device cloud** — BrowserStack App Automate, Sauce Labs Real Device Cloud, or AWS Device Farm — and owns the parts that are *specific to the farm* rather than to a generic grid: getting the app **onto** the farm, **picking the devices**, exercising **real-device-only features** (GPS, network conditions, biometrics, permissions, locale), and the **remote-run** orchestration paradigm.

> **Boundary — this skill builds ON `qa/java/skills/browser-cloud-setup`, it does not repeat it.** `browser-cloud-setup` is the *wiring*: connecting a driver to a remote hub, the `bstack:options` / `sauce:options` capability-block schemas, the plan's session cap, surfacing the session URL + marking pass/fail, and starting a tunnel. This skill is the layer above: the **app**, the **devices**, the **device-only capabilities**, and the **schedule-and-poll** paradigm.

## Stack

- Java 21, Gradle (Kotlin DSL)
- **Appium**: `io.appium:java-client` 11.0.0 with `selenium-support` ≥ 4.50 on Appium 3 (`AndroidDriver`/`IOSDriver`, `UiAutomator2Options`/`XCUITestOptions`), TestNG runner; java-client 10.x on Appium 2 is the supported lane, and the pins live in `qa/java/skills/ui-test-author/appium/SKILL.md`
- **App upload (REST)**: `com.squareup.okhttp3:okhttp` 4.x + `com.google.code.gson:gson` for the BrowserStack App Automate upload endpoint; the JDK's `java.net.http.HttpClient` for Device Farm's presigned `PUT`
- **Remote-run farm**: AWS SDK for Java v2 `software.amazon.awssdk:devicefarm` (`DeviceFarmClient`)
- **Condition waits**: `org.awaitility:awaitility` for upload-status / run-result polling — never `Thread.sleep`
- Farm support code under `src/test/java/.../support/farm/`; every Allure call is allure-java 3.0; credentials via **env vars only** (`BROWSERSTACK_USERNAME` / `BROWSERSTACK_ACCESS_KEY`; AWS creds via the default provider chain / OIDC)
- Runs in CI under `qa/cicd/java/skills/ci-pipelines`; the page objects from `qa/java/skills/ui-test-author/appium` run **unchanged**

## Does the farm run Appium 3?

The primary lane is java-client 11 on Appium 3. java-client 11 needs an Appium 3 server, so **check the vendor before bumping**; a cloud still on Appium 2 keeps the suite on java-client 10.x and Appium 2, the supported lane.

1. Read the vendor's own list of Appium versions, and the capability that selects one: `appiumVersion` inside `bstack:options` (BrowserStack) or `sauce:options` (Sauce Labs). BrowserStack's public page listed only 2.x and Sauce's migration page showed 2.13.1 on 2026-10-10, so neither is assumed to offer 3.
2. Set the capability to a 3.x value and start one session. A vendor without Appium 3 rejects it or falls back to 2; a green run does not tell which.
3. `driver.getCapabilities()` on the started session shows what the vendor actually granted.
4. AWS Device Farm takes its Appium version from the test spec and the host image; read the spec before the bump.

## When to use

- Uploading a build (`.apk`/`.aab`/`.xapk`/`.ipa`) to the farm and referencing it from the `app` capability (by `bs://…` id or `custom_id`)
- Running the same Appium test across a **matrix of real devices / OS versions**
- Testing a feature that needs a **real device**: biometric login, GPS-based behavior, a specific network condition, app permissions, a localized build
- Driving **AWS Device Farm**'s upload → schedule → poll lifecycle (the suite runs on the farm, you collect the result)
- Choosing between a **live-session** farm (BrowserStack/Sauce — your test drives a remote device in real time) and a **remote-run** farm (Device Farm — you ship the test package and poll for the verdict)

## When NOT to use

- The connect / capability-block / parallelism / tunnel / session-status wiring → `qa/java/skills/browser-cloud-setup` (this skill assumes it)
- The TypeScript / .NET device-farm stacks → `qa/{typescript,dotnet}/skills/device-cloud`
- Writing the mobile page objects / tests → `qa/java/skills/ui-test-author/appium`
- CI shard/worker mechanics (matrix fan-out, sharding props, Allure merge) → `qa/cicd/java/skills/ci-pipelines/*` — cross-link, don't duplicate

## Pick a paradigm — the choice that shapes everything

A device farm is one of two fundamentally different shapes. Get this right first — it decides whether your test code drives the device or whether you ship the test code to the farm.

| | **Live-session farm** | **Remote-run farm** |
|---|---|---|
| **Vendors** | BrowserStack App Automate, Sauce Labs RDC, LambdaTest | AWS Device Farm (also Firebase Test Lab) |
| **How it runs** | Your TestNG process runs locally/CI and drives a remote device over a hub URL in real time | You upload the **app + a packaged test suite**, the farm runs it on its own infra, you poll for the result |
| **The "app"** | Upload once → reference `bs://…` / `custom_id` in the `app` cap | Upload as a versioned **ARN**; referenced when you schedule the run |
| **Device choice** | A capability (`deviceName` + `osVersion`) per session | A **device-pool ARN** (a named set of devices) |
| **What you assert** | In your test, live, against the running device | After the run, by fetching artifacts / the run summary |
| **Real-device features** | Set as caps + injected mid-session via `browserstack_executor` | Configured on the scheduled run; less interactive |
| **This skill's focus** | App upload, device caps, device-only feature caps | `createUpload` → poll → `scheduleRun` → poll `getRun` |

**Decision rule.** *Want your existing TestNG/page-object suite to drive real devices with full live control (mid-session GPS changes, biometric prompts, network flips)?* → **live-session** (BrowserStack App Automate is the canonical here). *Already deep in AWS, need private-VPC devices, or want the farm to own execution end-to-end?* → **remote-run** (Device Farm). Most teams start live-session; reach for remote-run only when AWS integration or a hands-off run is the actual requirement. Don't build an abstraction over both.

---

## Deep-dive reference

These sections live in `references/details.md` — **read it when the task touches them**: **Live-session farm — BrowserStack App Automate (the canonical path)**.

## Remote-run farm — AWS Device Farm

Device Farm is the **other paradigm**: you upload the app and a packaged test suite, schedule a run against a **device-pool ARN**, and poll for the result. `references/aws-device-farm.md` holds the whole `DeviceFarmRunner`: `createUpload` → an HTTP `PUT` to the presigned URL (it throws on any status but `200`, so a failed upload is never a five-minute poll timeout) → poll until `SUCCEEDED` → `scheduleRun` → poll until `COMPLETED`. Every wait is an Awaitility condition, never a `Thread.sleep`. AWS auth is the default credential provider chain, and OIDC in CI.

---

## Secrets — env / provider chain only, never logged

Farm credentials are a billable, exfiltratable secret (CLAUDE.md hard rule). BrowserStack is a username + access key from env; AWS is the default provider chain (OIDC in CI) with the region from `AWS_REGION`, so no AWS credential class exists here. Read them lazily, fail loudly if missing, never log them, never persist them into an artifact or HAR.

```java
package support.farm;

public final class FarmCredentials {
    private FarmCredentials() {}

    private static String required(String name) {
        String value = System.getenv(name);
        if (value == null || value.isBlank())
            throw new IllegalStateException("Missing env var " + name + " — set it in your shell or CI secret store.");
        return value;
    }

    public record BrowserStack(String userName, String accessKey) {}

    public static BrowserStack browserStack() {
        return new BrowserStack(required("BROWSERSTACK_USERNAME"), required("BROWSERSTACK_ACCESS_KEY"));
    }
}
```

---

## Comparison — the three farms, app + device + features side by side

| Concept | **BrowserStack App Automate** | **Sauce Labs RDC** | **AWS Device Farm** |
|---|---|---|---|
| Paradigm | Live session | Live session | Remote run (upload + schedule) |
| App upload | `POST api-cloud.browserstack.com/app-automate/upload` → `bs://…` | `POST …/v1/storage/upload` (appStorage) → file id | `createUpload` → presigned PUT → ARN |
| App reference | `appium:app` = `bs://…` or `custom_id` | `appium:app` = `storage:filename=app.apk` or `storage:<id>` | `appArn` on `scheduleRun` |
| "Always latest" | re-upload same `custom_id` | re-upload same filename | new upload ARN per build |
| Device choice | `bstack:options.deviceName` + `osVersion` | `sauce:options.deviceName` + `platformVersion` | device-pool ARN |
| Real device? | default | `appium:options` real-device flags | physical devices in the pool |
| GPS | `gpsLocation` + `setLocation` | `setLocation` | run config |
| Network sim | `networkProfile` + `updateNetworkProfile` | network condition caps | run config |
| Biometric | `enableBiometric` + `performBiometric` | biometric instrumentation | n/a (run-level) |
| Permissions | `appium:autoGrantPermissions` | `appium:autoGrantPermissions` | `appium:autoGrantPermissions` |
| Retention | apps deleted 30 days after last use | per plan | per S3 lifecycle |

**Capability-block schemas** (`bstack:options` vs `sauce:options`), **session pass/fail reporting**, **parallelism** and **tunnels** are owned by `qa/java/skills/browser-cloud-setup`; this skill only adds the app/device/feature/remote-run layer on top.

---

## Anti-patterns

| Smell | Why it's wrong | Do instead |
|---|---|---|
| `appium:app` = a local file path | The farm runs an *uploaded* build; a local path is meaningless to a remote device | Upload first, reference the `bs://…` id / `custom_id` |
| Hard-coding a `bs://…` id in the repo | Apps are deleted 30 days after last use — the id rots | Re-upload in the build job under a stable `custom_id` |
| `Thread.sleep(5000)` after a biometric/network injection | Flaky and slow; the device reacts at its own pace | `WebDriverWait` / Awaitility on the app's observable reaction |
| `Thread.sleep` polling an AWS run | Wastes time, races the result | `await().atMost(...).until(run is COMPLETED)` |
| Running every device on every PR | Slow, expensive, exceeds the session cap | A small intent-chosen matrix on PR; broad sweep nightly |
| Concurrency > plan session cap | Sessions queue or get rejected | Keep it at or under the cap (browser-cloud-setup owns this) |
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
- Drive a **device matrix** from a `@Factory` fed by a sequential `@DataProvider` (one test-class instance per device, so a failure names it); pick devices by intent, not "all of them." A `@DataProvider(parallel = true)` with Appium is banned (D8): fan devices out across CI jobs, one device per job.
- Keep concurrent devices ≤ the plan session cap; `parallel="classes"` and the cap are owned by `browser-cloud-setup`.

### Real-device features
- Set static features (`gpsLocation`, `networkProfile`, `language`/`locale`/`timezone`, `deviceOrientation`, `enableBiometric`, `autoGrantPermissions`) as caps at session start.
- Flip dynamic features mid-session via `browserstack_executor` (biometric / network) or a `mobile:` location command (GPS: Android `mobile: setGeolocation`, iOS `mobile: setSimulatedLocation`).
- After any injection, **wait on the app's observable reaction** (explicit wait), never a `Thread.sleep`.

### Remote-run (Device Farm)
- `createUpload` → PUT bytes (throw on a failed PUT) → **poll until SUCCEEDED**; `scheduleRun` → **poll until COMPLETED**; both via Awaitility, never sleep.
- AWS auth via the default provider chain / **OIDC** in CI, never a literal key. Fetch artifacts after the run via `listArtifacts`.

### Secrets & boundary
- Credentials via env / provider chain only, read lazily, never logged or persisted to an artifact.
- Do **not** re-derive capability blocks, parallelism, tunnels, or session-status reporting here — cross-link `qa/java/skills/browser-cloud-setup`.

## Generation steps

0. Check **Does the farm run Appium 3?** before raising the client.
1. Confirm the **paradigm** (live-session BrowserStack/Sauce vs remote-run Device Farm) and **platform** (Android/iOS).
2. Add `support/farm/FarmCredentials.java` (env reads; AWS via provider chain) — no literals.
3. **Live-session**: add `AppUploader` (REST upload → `bs://…`/`custom_id`), `RealDeviceDriverFactory` (real-device caps + the device-only features the test needs), and `DeviceFeatures` for mid-session injection; drive a device matrix from a `@Factory`.
4. **Remote-run**: add `DeviceFarmRunner` from `references/aws-device-farm.md`.
5. Reuse `browser-cloud-setup`'s session-status + dashboard-URL teardown; map concurrency onto the plan cap per its rules.
6. Run **one** device/session first to confirm the upload + caps + features before fanning the matrix out; confirm the session/run appears on the dashboard with the right build/project tags. Inside a plan task marked `Gate: none`, run none of this and report the files as "written, not run".

## Cross-references

- **`qa/java/skills/browser-cloud-setup`** — the **prerequisite wiring** this skill builds on: connect, capability-block schemas, parallelism → `thread-count`, tunnels, session pass/fail + dashboard URL. This skill adds the app/device/feature/remote-run layer; that one owns the connection plumbing.
- **`qa/typescript/skills/device-cloud`** + **`qa/dotnet/skills/device-cloud`** — sibling device-farm stacks. Same four moves (app lifecycle → device selection → real-device features → remote-run), different SDKs. Structure ported, not code.
- **`qa/java/skills/ui-test-author/appium`** — writes the mobile page objects / tests that run **unchanged** on the farm; this skill only swaps the local session for a farm one.
- **`qa/java/skills/data-driven-testing`** — the `@DataProvider` mechanics (one independent case per row); this skill supplies the device list, that one the data-driven discipline.
- **`qa/cicd/java/skills/ci-pipelines`** — build-then-upload job, OIDC for AWS, sharding the matrix across runners (cross-link; don't duplicate).
- **`qa/java/skills/evidence-capture/references/appium.md`** — what a failed Appium run keeps locally, and the vendor video and pass/fail marking on a farm.
- **`qa/reporting/java/skills/test-reports`** — attach the session/run dashboard URL + device name to the report so a farm failure is one click from the replay.
