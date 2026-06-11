---
name: qa-mobile-device-farm-java
description: Use when the user needs the **real-device-cloud specifics** of running Java Appium tests on a mobile device farm. Triggers: "upload our app to BrowserStack App Automate and run the Appium Java tests", "run our TestNG mobile suite across a real-device matrix", "test biometric login on a real device on BrowserStack".
---

# QA — Mobile Device Farm (Java: Appium java-client on a real-device cloud)

Runs Java Appium tests against a **managed real-device cloud** — BrowserStack App Automate, Sauce Labs Real Device Cloud, or AWS Device Farm — and owns the parts that are *specific to the farm* rather than to a generic grid: getting the app **onto** the farm, **picking the devices**, exercising **real-device-only features** (GPS, network conditions, biometrics, permissions, locale), and the **remote-run** orchestration paradigm.

> **Boundary — this skill builds ON `qa/java/skills/cloud-grid-config`, it does not repeat it.** `cloud-grid-config` is the *wiring*: how you connect a driver to a remote hub, the `bstack:options` / `sauce:options` capability-block schemas, mapping the plan's session cap onto TestNG `thread-count`, surfacing the session URL + marking pass/fail, and starting a tunnel. All of that is assumed here and cross-linked, **not re-derived**. This skill is the layer above: the **app**, the **devices**, the **device-only capabilities**, and the **schedule-and-poll** paradigm — exactly the depth `cloud-grid-config` said it defers to `mobile-device-farm`.

## Stack

- Java 21, Gradle (Kotlin DSL)
- **Appium**: `io.appium:java-client` 9.x (`AndroidDriver`/`IOSDriver`, `UiAutomator2Options`/`XCUITestOptions`), TestNG runner
- **App upload (REST)**: `com.squareup.okhttp3:okhttp` 4.x + `com.google.code.gson:gson` for the BrowserStack App Automate upload endpoint
- **Remote-run farm**: AWS SDK for Java v2 `software.amazon.awssdk:devicefarm` (`DeviceFarmClient`)
- **Condition waits**: `org.awaitility:awaitility` for upload-status / run-result polling — never `Thread.sleep`
- Farm support code under `src/test/java/.../support/farm/`; credentials via **env vars only** (`BROWSERSTACK_USERNAME` / `BROWSERSTACK_ACCESS_KEY`; AWS creds via the default provider chain / OIDC)
- Runs in CI under `qa/java/skills/ci-pipelines`; the page objects come from `qa/java/skills/ui-test-author/appium` and run **unchanged** on the farm

## When to use

- Uploading a build (`.apk`/`.aab`/`.xapk`/`.ipa`) to the farm and referencing it from the `app` capability (by `bs://…` id or `custom_id`)
- Running the same Appium test across a **matrix of real devices / OS versions**
- Testing a feature that needs a **real device**: biometric login, GPS-based behavior, a specific network condition, app permissions, a localized build
- Driving **AWS Device Farm**'s upload → schedule → poll lifecycle (the suite runs on the farm, you collect the result)
- Choosing between a **live-session** farm (BrowserStack/Sauce — your test drives a remote device in real time) and a **remote-run** farm (Device Farm — you ship the test package and poll for the verdict)

## When NOT to use

- The connect / capability-block / parallelism / tunnel / session-status wiring → `qa/java/skills/cloud-grid-config` (this skill assumes it)
- The TypeScript / .NET device-farm stacks → `qa/{typescript,dotnet}/skills/mobile-device-farm`
- Writing the mobile page objects / tests → `qa/java/skills/ui-test-author/appium`
- CI shard/worker mechanics (matrix fan-out, sharding props, Allure merge) → `qa/java/skills/ci-pipelines/*` — cross-link, don't duplicate
- Web (Playwright) cloud runs → `qa/java/skills/cloud-grid-config`; this node is mobile real-device only

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

**Decision rule.** *Want your existing TestNG/page-object suite to drive real devices with full live control (mid-session GPS changes, biometric prompts, network flips)?* → **live-session** (BrowserStack App Automate is the canonical here). *Already deep in AWS, need private-VPC devices, or want the farm to own execution end-to-end?* → **remote-run** (Device Farm). Most teams start live-session; reach for remote-run only when AWS integration or a hands-off run is the actual requirement. Don't build an abstraction over both — wire the one you need behind the farm helpers below.

---

## Deep-dive reference

These sections live in `references/details.md` — **read it when the task touches them**: **Live-session farm — BrowserStack App Automate (the canonical path)**.

## Remote-run farm — AWS Device Farm

Device Farm is the **other paradigm**: you don't drive a live device — you upload the app and a packaged test suite, schedule a run against a **device-pool ARN**, and poll for the result. Every step that "waits" for AWS to finish is an **Awaitility condition poll**, never a `Thread.sleep`.

```java
// src/test/java/.../support/farm/DeviceFarmRunner.java
package support.farm;

import software.amazon.awssdk.services.devicefarm.DeviceFarmClient;
import software.amazon.awssdk.services.devicefarm.model.*;
import java.time.Duration;
import static org.awaitility.Awaitility.await;

/** Orchestrates an AWS Device Farm scheduled run: upload → poll → schedule → poll. */
public final class DeviceFarmRunner {
    private final DeviceFarmClient df; // built with the default credential provider chain / OIDC — no literal keys

    public DeviceFarmRunner(DeviceFarmClient df) { this.df = df; }

    /** Create an upload, PUT the bytes, and wait until the farm reports it processed. Returns the upload ARN. */
    public String uploadAndAwait(String projectArn, String name, UploadType type, byte[] bytes) {
        CreateUploadResponse created = df.createUpload(r -> r.projectArn(projectArn).name(name).type(type));
        Upload upload = created.upload();
        putBytesToPresignedUrl(upload.url(), bytes); // HTTP PUT to the presigned URL (OkHttp)

        // Wait on the SUCCEEDED condition — never sleep a fixed interval.
        await().atMost(Duration.ofMinutes(5)).pollInterval(Duration.ofSeconds(5)).until(() -> {
            UploadStatus status = df.getUpload(g -> g.arn(upload.arn())).upload().status();
            if (status == UploadStatus.FAILED) throw new IllegalStateException("upload failed: " + name);
            return status == UploadStatus.SUCCEEDED;
        });
        return upload.arn();
    }

    /** Schedule the run and wait until it completes; return the aggregate result. */
    public ExecutionResult scheduleAndAwait(String projectArn, String appArn, String testPkgArn, String devicePoolArn) {
        ScheduleRunResponse scheduled = df.scheduleRun(r -> r
            .projectArn(projectArn)
            .appArn(appArn)
            .devicePoolArn(devicePoolArn)
            .test(t -> t.type(TestType.APPIUM_JAVA_TESTNG).testPackageArn(testPkgArn)));
        String runArn = scheduled.run().arn();

        await().atMost(Duration.ofMinutes(30)).pollInterval(Duration.ofSeconds(15)).until(() ->
            df.getRun(g -> g.arn(runArn)).run().status() == ExecutionStatus.COMPLETED);

        return df.getRun(g -> g.arn(runArn)).run().result(); // PASSED / FAILED / ERRORED
    }

    private void putBytesToPresignedUrl(String url, byte[] bytes) { /* OkHttp PUT — omitted for brevity */ }
}
```

> **Device Farm specifics:** the test package type for a TestNG Appium suite is `APPIUM_JAVA_TESTNG_TEST_PACKAGE` (+ an `APPIUM_JAVA_TESTNG_TEST_SPEC` YAML to control the run); the app type is `ANDROID_APP` / `IOS_APP`. A **device pool** is created once (in the console or via `createDevicePool` with a device-selection rule) and referenced by ARN. AWS auth comes from the **default credential provider chain** — in CI prefer **OIDC role assumption** over a long-lived access key (see `qa/java/skills/ci-pipelines`). Artifacts (logs, video, screenshots) are fetched per-job via `listArtifacts(runArn)` after the run completes.

---

## Secrets — env / provider chain only, never logged

Farm credentials are a billable, exfiltratable secret (CLAUDE.md hard rule). BrowserStack is a username + access key from env; AWS is the default provider chain (OIDC in CI). Read them lazily, fail loudly if missing, never log them, never persist them into an artifact or HAR.

```java
// src/test/java/.../support/farm/FarmCredentials.java
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
    // AWS Device Farm: no creds here — use the default provider chain / OIDC, region from AWS_REGION.
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

**Capability-block schemas** (`bstack:options` vs `sauce:options`), **session pass/fail reporting**, **parallelism → `thread-count`**, and **tunnels** are the same across these and are owned by `qa/java/skills/cloud-grid-config` — see it for the side-by-side block table. This skill only adds the app/device/feature/remote-run layer on top.

---

## Anti-patterns

| Smell | Why it's wrong | Do instead |
|---|---|---|
| `appium:app` = a local file path | The farm runs an *uploaded* build; a local path is meaningless to a remote device | Upload first, reference the `bs://…` id / `custom_id` |
| Hard-coding a `bs://…` id in the repo | Apps are deleted 30 days after last use — the id rots | Re-upload in the build job under a stable `custom_id` |
| `Thread.sleep(5000)` after a biometric/network injection | Flaky and slow; the device reacts at its own pace | `WebDriverWait` / Awaitility on the app's observable reaction |
| `Thread.sleep` polling an AWS run | Wastes time, races the result | `await().atMost(...).until(run is COMPLETED)` |
| Running every device on every PR | Slow, expensive, exceeds the session cap | A small intent-chosen matrix on PR; broad sweep nightly |
| Thread count > plan session cap | Sessions queue or get rejected | Map the cap onto `thread-count` (cloud-grid-config owns this) |
| Credentials / access key in code or a committed config | Billable, exfiltratable secret | `required(...)` env read; AWS via OIDC |
| Re-deriving the capability block / tunnel / status here | Duplicates `cloud-grid-config`, drifts out of sync | Cross-link `cloud-grid-config`; add only the farm layer |
| Emulator caps when the test needs a real device | Biometric/GPS/network features need real hardware | Pin a real `deviceName` (App Automate default) |

## Rules

### App lifecycle
- Upload the build to the farm and reference it by **id** (`bs://…`) or **`custom_id`** — never a local path in the `app` cap.
- Prefer `custom_id` in CI: re-upload under the same id so the `app` cap always picks the latest build with no id-plumbing between jobs.
- Treat the app id as **ephemeral** (30-day retention) — re-upload in the build job; never commit an id as if stable.

### Device selection
- Pin a real device with `deviceName` + `osVersion` (App Automate sessions are real devices by default).
- Drive a **device matrix** from a `@DataProvider` (one independent case per device); pick devices by intent, not "all of them."
- Keep concurrent devices ≤ the plan session cap — that cap → TestNG `thread-count` is owned by `cloud-grid-config`.

### Real-device features
- Set static features (`gpsLocation`, `networkProfile`, `language`/`locale`/`timezone`, `deviceOrientation`, `enableBiometric`, `autoGrantPermissions`) as caps at session start.
- Flip dynamic features mid-session via `browserstack_executor` (biometric / network) or the Appium location API (GPS).
- After any injection, **wait on the app's observable reaction** (explicit wait), never a `Thread.sleep`.

### Remote-run (Device Farm)
- `createUpload` → PUT bytes → **poll until SUCCEEDED**; `scheduleRun` → **poll until COMPLETED**; both via Awaitility, never sleep.
- AWS auth via the default provider chain / **OIDC** in CI, never a literal key. Fetch artifacts after the run via `listArtifacts`.

### Secrets & boundary
- Credentials via env / provider chain only, read lazily, never logged or persisted to an artifact.
- Do **not** re-derive capability blocks, parallelism, tunnels, or session-status reporting here — cross-link `qa/java/skills/cloud-grid-config`.

## Generation steps

1. Confirm the **paradigm** (live-session BrowserStack/Sauce vs remote-run Device Farm) and **platform** (Android/iOS).
2. Add `support/farm/FarmCredentials.java` (env reads; AWS via provider chain) — no literals.
3. **Live-session**: add `AppUploader` (REST upload → `bs://…`/`custom_id`), `RealDeviceDriverFactory` (real-device caps + the device-only features the test needs), and `DeviceFeatures` for mid-session injection; drive a device matrix from a `@DataProvider`.
4. **Remote-run**: add `DeviceFarmRunner` (`createUpload` → poll → `scheduleRun` → poll `getRun`) with Awaitility condition waits.
5. Reuse `cloud-grid-config`'s session-status + dashboard-URL teardown; map the device count onto `thread-count` per its rules.
6. Run **one** device/session first to confirm the upload + caps + features before fanning the matrix out; confirm the session/run appears on the dashboard with the right build/project tags.

## Cross-references

- **`qa/java/skills/cloud-grid-config`** — the **prerequisite wiring** this skill builds on: connect, capability-block schemas, parallelism → `thread-count`, tunnels, session pass/fail + dashboard URL. This skill adds the app/device/feature/remote-run layer; that one owns the connection plumbing.
- **`qa/typescript/skills/mobile-device-farm`** + **`qa/dotnet/skills/mobile-device-farm`** — sibling device-farm stacks. Same four moves (app lifecycle → device selection → real-device features → remote-run), different SDKs. Structure ported, not code.
- **`qa/java/skills/ui-test-author/appium`** — writes the mobile page objects / tests that run **unchanged** on the farm; this skill only swaps the local session for a farm one.
- **`qa/java/skills/data-driven-testing`** — the `@DataProvider` device-matrix mechanics (one independent case per device); this skill supplies the device list, that one the data-driven discipline.
- **`qa/java/skills/ci-pipelines`** — build-then-upload job, OIDC for AWS, sharding the matrix across runners (cross-link; don't duplicate).
- **`qa/java/skills/allure-reporting`** — attach the session/run dashboard URL + device name to the report so a farm failure is one click from the replay.
