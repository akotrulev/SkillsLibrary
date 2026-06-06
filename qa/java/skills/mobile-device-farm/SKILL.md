---
name: qa-mobile-device-farm-java
description: Use when the user needs the **real-device-cloud specifics** of running Java Appium tests on a mobile device farm — BrowserStack App Automate, Sauce Labs Real Device Cloud, or AWS Device Farm — beyond the basic grid wiring. Covers: **app lifecycle** (upload an `.apk`/`.aab`/`.ipa` to the farm via REST → get a `bs://…` / `storage:` id → reference it in the `app` cap, `custom_id` for "always latest build", 30-day retention), **device selection** (real device vs emulator, pinning a device + OS version, a **device matrix** via a TestNG `@DataProvider`, private/dedicated device pools), **real-device-only capabilities** (GPS `gpsLocation` / `driver.setLocation`, `networkProfile` simulation, biometric injection via sensor instrumentation + `browserstack_executor performBiometric`, `appium:autoGrantPermissions`, `language`/`locale`/`timezone`, device orientation — set at session start AND mid-session), and the **remote-run paradigm** (AWS Device Farm `createUpload` → poll → `scheduleRun` against a device-pool ARN → poll `getRun`, the whole suite run on the farm vs a live Appium session). Triggers: "upload our app to BrowserStack App Automate and run the Appium Java tests", "run our TestNG mobile suite across a real-device matrix", "test biometric login on a real device on BrowserStack", "mock GPS / simulate a 3G network for our Appium tests", "schedule an Appium run on AWS Device Farm". Do NOT use for the basic grid connect/capability-block/parallelism/tunnel wiring (use `qa/java/skills/cloud-grid-config` — this skill builds ON it), the TypeScript device-farm stack (use `qa/typescript/skills/mobile-device-farm`), the .NET device-farm stack (use `qa/dotnet/skills/mobile-device-farm`), writing the mobile page objects / tests themselves (use `qa/java/skills/ui-test-author/appium`), or CI shard mechanics (use `qa/java/skills/ci-pipelines/*`).
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
- Runs in CI under `qa/java/skills/ci-pipelines/github-actions`; the page objects come from `qa/java/skills/ui-test-author/appium` and run **unchanged** on the farm

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

## Live-session farm — BrowserStack App Automate (the canonical path)

### 1. App lifecycle — get the build onto the farm, reference it by id

The farm runs *an uploaded build*, never a local file path. Upload the `.apk`/`.aab`/`.ipa` once to the App Automate REST endpoint; you get back a `bs://…` id you put in the `app` capability. Give it a **`custom_id`** so re-uploads under the same id let the `app` cap always pick the latest build — the CI-friendly pattern (build → upload under `custom_id` → tests reference the `custom_id`, no id-plumbing between jobs).

```java
// src/test/java/.../support/farm/AppUploader.java
package support.farm;

import com.google.gson.Gson;
import com.google.gson.JsonObject;
import okhttp3.*;
import java.io.File;
import java.io.IOException;

/** Uploads a build to BrowserStack App Automate and returns the bs:// app id. */
public final class AppUploader {
    private static final String UPLOAD_URL = "https://api-cloud.browserstack.com/app-automate/upload";
    private static final Gson GSON = new Gson();
    private final OkHttpClient http = new OkHttpClient();
    private final FarmCredentials.BrowserStack creds;

    public AppUploader(FarmCredentials.BrowserStack creds) { this.creds = creds; }

    public record UploadedApp(String appUrl, String customId) {}

    /** Upload a local build under a custom_id. Re-uploading the same custom_id rotates "latest". */
    public UploadedApp upload(File build, String customId) throws IOException {
        RequestBody body = new MultipartBody.Builder()
            .setType(MultipartBody.FORM)
            .addFormDataPart("file", build.getName(),
                RequestBody.create(build, MediaType.parse("application/octet-stream")))
            .addFormDataPart("custom_id", customId)
            .build();
        Request request = new Request.Builder()
            .url(UPLOAD_URL)
            .header("Authorization", Credentials.basic(creds.userName(), creds.accessKey())) // env-sourced, never logged
            .post(body)
            .build();
        try (Response response = http.newCall(request).execute()) {
            if (!response.isSuccessful()) {
                throw new IOException("App upload failed: HTTP " + response.code());
            }
            JsonObject json = GSON.fromJson(response.body().string(), JsonObject.class);
            return new UploadedApp(json.get("app_url").getAsString(), customId); // {"app_url":"bs://...","custom_id":...}
        }
    }
}
```

> **Reference the app three ways, in order of CI-friendliness:** (1) `custom_id` — `options.setCapability("appium:app", "MyApp")` always picks the **last build uploaded under that id** (best for CI: no id passed between jobs); (2) the raw `bs://…` id from a one-off upload; (3) a **public URL** (`-F "url=https://…"` on upload). Apps are **deleted 30 days after last use** — never assume an id is permanent; re-upload in the build job. Don't commit a `bs://…` id as if it were stable.

### 2. Device selection — pin a device, or fan out a matrix

On App Automate every session is a **real device** by default (no emulator flag needed). You pick it with `deviceName` + `osVersion` in `bstack:options`. To run a test across a **device matrix**, drive the device list from a TestNG `@DataProvider` — one independent parameterized case per device, so a failure names the device. (The data-driven mechanics themselves belong to `qa/java/skills/data-driven-testing`; here it's the farm's device list.)

```java
// src/test/java/.../support/farm/DeviceMatrix.java
package support.farm;

import org.testng.annotations.DataProvider;

public final class DeviceMatrix {
    private DeviceMatrix() {}

    /** The real-device matrix this suite targets. Keep it small and meaningful, not every device. */
    @DataProvider(name = "devices", parallel = true) // parallel honours the plan cap via thread-count (see cloud-grid-config)
    public static Object[][] devices() {
        return new Object[][] {
            { "Samsung Galaxy S23", "13.0" },
            { "Google Pixel 8",     "14.0" },
            { "Samsung Galaxy S21", "12.0" },
        };
    }
}
```

> **Pick devices by intent, not "all of them."** A device matrix is for covering the segments that actually differ (a vendor skin, an old OS, a screen size that breaks layout) — not for running 200 devices on every PR. Reserve the broad sweep for nightly. The cap on how many run at once is the **plan's session cap → TestNG `thread-count`**, which `cloud-grid-config` owns; don't set a thread count here that exceeds it. A **private/dedicated device pool** (a plan add-on) is selected the same way — the device is just reserved to your org.

### 3. Real-device-only capabilities — the reason a farm exists

These are the features you *cannot* exercise on a local emulator and the core value of a real-device farm. Set the static ones as caps at session start; flip the dynamic ones **mid-session** via the `browserstack_executor` JS hook. Build the driver behind a factory (constructor injection, never a service locator), exactly as `qa/java/skills/ui-test-author/appium` does for local sessions — only the cap block and hub URL change.

```java
// src/test/java/.../support/farm/RealDeviceDriverFactory.java
package support.farm;

import io.appium.java_client.android.AndroidDriver;
import io.appium.java_client.android.options.UiAutomator2Options;
import java.net.URL;
import java.util.HashMap;
import java.util.Map;

public final class RealDeviceDriverFactory {
    private static final String HUB = "https://hub-cloud.browserstack.com/wd/hub";
    private final FarmCredentials.BrowserStack creds;

    public RealDeviceDriverFactory(FarmCredentials.BrowserStack creds) { this.creds = creds; }

    /** A real-device Android session with device-only features set up front. */
    public AndroidDriver create(String deviceName, String osVersion, String appRef, String sessionName) throws Exception {
        UiAutomator2Options options = new UiAutomator2Options();
        Map<String, Object> bstack = new HashMap<>();
        bstack.put("userName", creds.userName());
        bstack.put("accessKey", creds.accessKey());
        bstack.put("deviceName", deviceName);          // a REAL device on App Automate
        bstack.put("osVersion", osVersion);
        bstack.put("projectName", "checkout-mobile");
        bstack.put("buildName", System.getenv().getOrDefault("BUILD_NAME", "local-build"));
        bstack.put("sessionName", sessionName);
        // --- real-device-only features ---
        bstack.put("gpsLocation", "40.730610,-73.935242"); // "lat,long" — initial device location
        bstack.put("networkProfile", "4g-lte-advanced-good"); // simulate a network condition
        bstack.put("language", "fr");                   // localized-build testing
        bstack.put("locale", "fr_FR");
        bstack.put("timezone", "Europe/Paris");
        bstack.put("deviceOrientation", "portrait");
        bstack.put("enableBiometric", true);            // sensor instrumentation for biometric prompts
        options.setCapability("bstack:options", bstack);

        options.setCapability("appium:app", appRef);    // bs://… or a custom_id
        options.setCapability("appium:autoGrantPermissions", true); // grant manifest permissions on install

        return new AndroidDriver(new URL(HUB), options);
    }
}
```

Then drive the **dynamic** device features in the test through a small helper. Each is a `browserstack_executor` command (biometric / network) or a standard Appium location call (GPS) — and each must be **awaited on the app's reaction**, never followed by a sleep.

```java
// src/test/java/.../support/farm/DeviceFeatures.java
package support.farm;

import org.openqa.selenium.JavascriptExecutor;
import org.openqa.selenium.html5.Location;
import org.openqa.selenium.remote.RemoteWebDriver;

public final class DeviceFeatures {
    private DeviceFeatures() {}

    /** Answer the next biometric prompt: match=true approves, false rejects. */
    public static void respondToBiometric(JavascriptExecutor driver, boolean match) {
        driver.executeScript(
            "browserstack_executor: {\"action\":\"performBiometric\",\"arguments\":{\"match\":" + match + "}}");
    }

    /** Flip the network condition mid-session (e.g. drop to 2G to test a slow-network path). */
    public static void switchNetworkProfile(JavascriptExecutor driver, String profile) {
        driver.executeScript(
            "browserstack_executor: {\"action\":\"updateNetworkProfile\",\"arguments\":{\"networkProfile\":\"" + profile + "\"}}");
    }

    /** Move the device GPS mid-session via the standard Appium location API. */
    public static void setLocation(RemoteWebDriver driver, double lat, double lon) {
        ((org.openqa.selenium.html5.LocationContext) driver).setLocation(new Location(lat, lon, 0));
    }
}
```

> **The full real-device feature set** (App Automate): `gpsLocation` + mid-session `setLocation`; `networkProfile` (presets like `2g-gprs-good`, `4g-lte-advanced-good`, or a custom bandwidth/latency/loss profile) + mid-session `updateNetworkProfile`; **biometric** via `enableBiometric` (sensor instrumentation injects a mock into the app) + `performBiometric`; `appium:autoGrantPermissions`; `language`/`locale`/`timezone`; `deviceOrientation`; plus camera-image injection, OTP/SIM workflows, and file upload-to-device for richer flows. **iOS** uses `XCUITestOptions` with the same `bstack:options` block (biometric = Touch/Face ID injection). Set static features as caps; flip dynamic ones mid-session.

### 4. Put it together — a real-device test

The test reads like any Appium test from `qa/java/skills/ui-test-author/appium`; only setup wires the farm. Note the assertion **waits on the app's reaction** to the biometric injection (an explicit `WebDriverWait` condition), never a `Thread.sleep`.

```java
// src/test/java/tests/BiometricLoginTest.java
package tests;

import io.appium.java_client.android.AndroidDriver;
import org.openqa.selenium.JavascriptExecutor;
import org.testng.annotations.*;
import support.farm.*;
// page objects from qa/java/skills/ui-test-author/appium

public class BiometricLoginTest {

    @Test(dataProvider = "devices", dataProviderClass = DeviceMatrix.class)
    public void Should_log_in_When_biometric_is_approved(String deviceName, String osVersion) throws Exception {
        AndroidDriver driver = new RealDeviceDriverFactory(FarmCredentials.browserStack())
            .create(deviceName, osVersion, "checkout-app", "biometric-login@" + deviceName); // custom_id app ref
        try {
            LoginPage login = new LoginPage(driver);     // intent-expressing page object, farm-agnostic
            login.tapBiometricSignIn();
            DeviceFeatures.respondToBiometric((JavascriptExecutor) driver, true); // approve the prompt
            DashboardPage dashboard = login.awaitDashboard(); // explicit wait inside the page object — no sleep
            org.testng.Assert.assertTrue(dashboard.isLoaded(), "biometric login should reach the dashboard");
        } finally {
            // session status + dashboard URL are owned by cloud-grid-config's teardown; reuse it
            driver.quit();
        }
    }
}
```

> **Reuse `cloud-grid-config`'s teardown**, don't re-invent it: marking the session pass/fail (`browserstack_executor setSessionStatus`) and attaching the dashboard URL to Allure are that skill's job. This skill adds the *app/device/feature* setup; the session-result reporting is shared.

---

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

> **Device Farm specifics:** the test package type for a TestNG Appium suite is `APPIUM_JAVA_TESTNG_TEST_PACKAGE` (+ an `APPIUM_JAVA_TESTNG_TEST_SPEC` YAML to control the run); the app type is `ANDROID_APP` / `IOS_APP`. A **device pool** is created once (in the console or via `createDevicePool` with a device-selection rule) and referenced by ARN. AWS auth comes from the **default credential provider chain** — in CI prefer **OIDC role assumption** over a long-lived access key (see `qa/java/skills/ci-pipelines/github-actions`). Artifacts (logs, video, screenshots) are fetched per-job via `listArtifacts(runArn)` after the run completes.

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
- **`qa/java/skills/ci-pipelines/github-actions`** — build-then-upload job, OIDC for AWS, sharding the matrix across runners (cross-link; don't duplicate).
- **`qa/java/skills/allure-reporting`** — attach the session/run dashboard URL + device name to the report so a farm failure is one click from the replay.
