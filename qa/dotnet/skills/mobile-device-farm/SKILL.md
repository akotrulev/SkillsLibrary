---
name: qa-mobile-device-farm-dotnet
description: Use when the user needs the **real-device-cloud specifics** of running .NET (C#) Appium tests on a mobile device farm — BrowserStack App Automate, Sauce Labs Real Device Cloud, or AWS Device Farm — beyond the basic grid wiring. Covers: **app lifecycle** (upload an `.apk`/`.aab`/`.ipa` to the farm via REST with `HttpClient` → get a `bs://…` / `storage:` id → reference it in the `app` cap, `custom_id` for "always latest build", 30-day retention), **device selection** (real device vs emulator, pinning a device + OS version, a **device matrix** via NUnit `[TestCaseSource]`, private/dedicated device pools), **real-device-only capabilities** (GPS `gpsLocation` / `ILocationContext.Location`, `networkProfile` simulation, biometric injection via sensor instrumentation + `browserstack_executor performBiometric`, `appium:autoGrantPermissions`, `language`/`locale`/`timezone`, device orientation — set at session start AND mid-session), and the **remote-run paradigm** (AWS Device Farm `CreateUploadAsync` → poll → `ScheduleRunAsync` against a device-pool ARN → poll `GetRunAsync`, the whole suite run on the farm vs a live Appium session). Triggers: "upload our app to BrowserStack App Automate and run the C# Appium tests", "run our NUnit mobile suite across a real-device matrix", "test biometric login on a real device in .NET", "mock GPS / simulate a 3G network for our Appium tests", "schedule an Appium run on AWS Device Farm from C#". Do NOT use for the basic grid connect/capability-block/parallelism/tunnel wiring (use `qa/dotnet/skills/cloud-grid-config` — this skill builds ON it), the Java device-farm stack (use `qa/java/skills/mobile-device-farm`), the TypeScript device-farm stack (use `qa/typescript/skills/mobile-device-farm`), writing the mobile page objects / tests themselves (use `qa/dotnet/skills/ui-test-author/appium`), or CI shard mechanics (use `qa/dotnet/skills/ci-pipelines/*`).
---

# QA — Mobile Device Farm (.NET: Appium.WebDriver on a real-device cloud)

Runs .NET Appium tests against a **managed real-device cloud** — BrowserStack App Automate, Sauce Labs Real Device Cloud, or AWS Device Farm — and owns the parts that are *specific to the farm* rather than to a generic grid: getting the app **onto** the farm, **picking the devices**, exercising **real-device-only features** (GPS, network conditions, biometrics, permissions, locale), and the **remote-run** orchestration paradigm.

> **Boundary — this skill builds ON `qa/dotnet/skills/cloud-grid-config`, it does not repeat it.** `cloud-grid-config` is the *wiring*: how you connect a driver to a remote hub, the `bstack:options` / `sauce:options` capability-block schemas, mapping the plan's session cap onto NUnit `LevelOfParallelism`, surfacing the session URL + marking pass/fail, and starting a tunnel. All of that is assumed here and cross-linked, **not re-derived**. This skill is the layer above: the **app**, the **devices**, the **device-only capabilities**, and the **schedule-and-poll** paradigm — exactly the depth `cloud-grid-config` said it defers to `mobile-device-farm`.

## Stack

- .NET 8, C# (nullable reference types enabled)
- **Appium**: `Appium.WebDriver` 8.x (`AndroidDriver`/`IOSDriver`, `AppiumOptions` + `AddAdditionalAppiumOption`), NUnit runner
- **App upload (REST)**: `System.Net.Http.HttpClient` + `MultipartFormDataContent` + `System.Text.Json` for the BrowserStack App Automate upload endpoint
- **Remote-run farm**: AWS SDK for .NET `AWSSDK.DeviceFarm` (`AmazonDeviceFarmClient`)
- **Condition waits**: a bounded poll helper (`CancellationTokenSource` deadline + a check interval) — never `Task.Delay` *as* a wait
- Farm support code under `Tests/Support/Farm/`; credentials via **env vars only** (`BROWSERSTACK_USERNAME` / `BROWSERSTACK_ACCESS_KEY`; AWS creds via the default credential chain / OIDC)
- Runs in CI under `qa/dotnet/skills/ci-pipelines/github-actions`; the page objects come from `qa/dotnet/skills/ui-test-author/appium` and run **unchanged** on the farm

## When to use

- Uploading a build (`.apk`/`.aab`/`.xapk`/`.ipa`) to the farm and referencing it from the `app` capability (by `bs://…` id or `custom_id`)
- Running the same Appium test across a **matrix of real devices / OS versions**
- Testing a feature that needs a **real device**: biometric login, GPS-based behavior, a specific network condition, app permissions, a localized build
- Driving **AWS Device Farm**'s upload → schedule → poll lifecycle (the suite runs on the farm, you collect the result)
- Choosing between a **live-session** farm (BrowserStack/Sauce — your test drives a remote device in real time) and a **remote-run** farm (Device Farm — you ship the test package and poll for the verdict)

## When NOT to use

- The connect / capability-block / parallelism / tunnel / session-status wiring → `qa/dotnet/skills/cloud-grid-config` (this skill assumes it)
- The Java / TypeScript device-farm stacks → `qa/{java,typescript}/skills/mobile-device-farm`
- Writing the mobile page objects / tests → `qa/dotnet/skills/ui-test-author/appium`
- CI shard/worker mechanics (matrix fan-out, sharding props, Allure merge) → `qa/dotnet/skills/ci-pipelines/*` — cross-link, don't duplicate
- Web (Playwright) cloud runs → `qa/dotnet/skills/cloud-grid-config`; this node is mobile real-device only

## Pick a paradigm — the choice that shapes everything

A device farm is one of two fundamentally different shapes. Get this right first — it decides whether your test code drives the device or whether you ship the test code to the farm.

| | **Live-session farm** | **Remote-run farm** |
|---|---|---|
| **Vendors** | BrowserStack App Automate, Sauce Labs RDC, LambdaTest | AWS Device Farm (also Firebase Test Lab) |
| **How it runs** | Your NUnit process runs locally/CI and drives a remote device over a hub URL in real time | You upload the **app + a packaged test suite**, the farm runs it on its own infra, you poll for the result |
| **The "app"** | Upload once → reference `bs://…` / `custom_id` in the `app` cap | Upload as a versioned **ARN**; referenced when you schedule the run |
| **Device choice** | A capability (`deviceName` + `osVersion`) per session | A **device-pool ARN** (a named set of devices) |
| **What you assert** | In your test, live, against the running device | After the run, by fetching artifacts / the run summary |
| **Real-device features** | Set as caps + injected mid-session via `browserstack_executor` | Configured on the scheduled run; less interactive |
| **This skill's focus** | App upload, device caps, device-only feature caps | `CreateUpload` → poll → `ScheduleRun` → poll `GetRun` |

**Decision rule.** *Want your existing NUnit/page-object suite to drive real devices with full live control (mid-session GPS changes, biometric prompts, network flips)?* → **live-session** (BrowserStack App Automate is the canonical here). *Already deep in AWS, need private-VPC devices, or want the farm to own execution end-to-end?* → **remote-run** (Device Farm). Most teams start live-session; reach for remote-run only when AWS integration or a hands-off run is the actual requirement. Don't build an abstraction over both — wire the one you need behind the farm helpers below.

---

## Live-session farm — BrowserStack App Automate (the canonical path)

### 1. App lifecycle — get the build onto the farm, reference it by id

The farm runs *an uploaded build*, never a local file path. Upload the `.apk`/`.aab`/`.ipa` once to the App Automate REST endpoint; you get back a `bs://…` id you put in the `app` capability. Give it a **`custom_id`** so re-uploads under the same id let the `app` cap always pick the latest build — the CI-friendly pattern (build → upload under `custom_id` → tests reference the `custom_id`, no id-plumbing between jobs).

```csharp
// Tests/Support/Farm/AppUploader.cs
using System.Net.Http.Headers;
using System.Text.Json;

namespace Tests.Support.Farm;

/// <summary>Uploads a build to BrowserStack App Automate and returns the bs:// app id.</summary>
public sealed class AppUploader
{
    private const string UploadUrl = "https://api-cloud.browserstack.com/app-automate/upload";
    private readonly HttpClient _http;
    private readonly FarmCredentials.BrowserStack _creds;

    public AppUploader(HttpClient http, FarmCredentials.BrowserStack creds) // constructor injection
    {
        _http = http;
        _creds = creds;
    }

    public sealed record UploadedApp(string AppUrl, string CustomId);

    /// <summary>Upload a local build under a custom_id. Re-uploading the same custom_id rotates "latest".</summary>
    public async Task<UploadedApp> UploadAsync(string buildPath, string customId, CancellationToken ct = default)
    {
        using var content = new MultipartFormDataContent();
        var fileBytes = await File.ReadAllBytesAsync(buildPath, ct);
        var fileContent = new ByteArrayContent(fileBytes);
        fileContent.Headers.ContentType = new MediaTypeHeaderValue("application/octet-stream");
        content.Add(fileContent, "file", Path.GetFileName(buildPath));
        content.Add(new StringContent(customId), "custom_id");

        using var request = new HttpRequestMessage(HttpMethod.Post, UploadUrl) { Content = content };
        var basic = Convert.ToBase64String(
            System.Text.Encoding.UTF8.GetBytes($"{_creds.UserName}:{_creds.AccessKey}")); // env-sourced, never logged
        request.Headers.Authorization = new AuthenticationHeaderValue("Basic", basic);

        using var response = await _http.SendAsync(request, ct);
        response.EnsureSuccessStatusCode();
        using var json = JsonDocument.Parse(await response.Content.ReadAsStringAsync(ct));
        // {"app_url":"bs://...","custom_id":...}
        return new UploadedApp(json.RootElement.GetProperty("app_url").GetString()!, customId);
    }
}
```

> **Reference the app three ways, in order of CI-friendliness:** (1) `custom_id` — `options.AddAdditionalAppiumOption("app", "MyApp")` always picks the **last build uploaded under that id** (best for CI: no id passed between jobs); (2) the raw `bs://…` id from a one-off upload; (3) a **public URL** (`url` form-field on upload). Apps are **deleted 30 days after last use** — never assume an id is permanent; re-upload in the build job. Don't commit a `bs://…` id as if it were stable.

### 2. Device selection — pin a device, or fan out a matrix

On App Automate every session is a **real device** by default (no emulator flag needed). You pick it with `deviceName` + `osVersion` in `bstack:options`. To run a test across a **device matrix**, drive the device list from an NUnit `[TestCaseSource]` — one independent parameterized case per device, so a failure names the device. (The data-driven mechanics themselves belong to `qa/dotnet/skills/data-driven-testing`; here it's the farm's device list.)

```csharp
// Tests/Support/Farm/DeviceMatrix.cs
namespace Tests.Support.Farm;

public sealed record TargetDevice(string DeviceName, string OsVersion)
{
    public override string ToString() => $"{DeviceName} ({OsVersion})"; // a failing case names the device
}

public static class DeviceMatrix
{
    /// <summary>The real-device matrix this suite targets. Keep it small and meaningful, not every device.</summary>
    public static IEnumerable<TargetDevice> Devices =>
    [
        new("Samsung Galaxy S23", "13.0"),
        new("Google Pixel 8",     "14.0"),
        new("Samsung Galaxy S21", "12.0"),
    ];
}
```

> **Pick devices by intent, not "all of them."** A device matrix is for covering the segments that actually differ (a vendor skin, an old OS, a screen size that breaks layout) — not for running 200 devices on every PR. Reserve the broad sweep for nightly. The cap on how many run at once is the **plan's session cap → NUnit `LevelOfParallelism`**, which `cloud-grid-config` owns; don't set a level here that exceeds it. A **private/dedicated device pool** (a plan add-on) is selected the same way — the device is just reserved to your org.

### 3. Real-device-only capabilities — the reason a farm exists

These are the features you *cannot* exercise on a local emulator and the core value of a real-device farm. Set the static ones as caps at session start; flip the dynamic ones **mid-session** via the `browserstack_executor` JS hook. Build the driver behind a factory (constructor injection, never a service locator), exactly as `qa/dotnet/skills/ui-test-author/appium` does for local sessions — only the cap block and hub URL change.

```csharp
// Tests/Support/Farm/RealDeviceDriverFactory.cs
using OpenQA.Selenium.Appium;
using OpenQA.Selenium.Appium.Android;

namespace Tests.Support.Farm;

public sealed class RealDeviceDriverFactory
{
    private const string Hub = "https://hub-cloud.browserstack.com/wd/hub";
    private readonly FarmCredentials.BrowserStack _creds;

    public RealDeviceDriverFactory(FarmCredentials.BrowserStack creds) => _creds = creds;

    /// <summary>A real-device Android session with device-only features set up front.</summary>
    public AndroidDriver Create(TargetDevice device, string appRef, string sessionName)
    {
        var options = new AppiumOptions { AutomationName = "UiAutomator2", PlatformName = "Android" };
        var bstack = new Dictionary<string, object>
        {
            ["userName"]    = _creds.UserName,
            ["accessKey"]   = _creds.AccessKey,
            ["deviceName"]  = device.DeviceName,   // a REAL device on App Automate
            ["osVersion"]   = device.OsVersion,
            ["projectName"] = "checkout-mobile",
            ["buildName"]   = Environment.GetEnvironmentVariable("BUILD_NAME") ?? "local-build",
            ["sessionName"] = sessionName,
            // --- real-device-only features ---
            ["gpsLocation"]       = "40.730610,-73.935242", // "lat,long" — initial device location
            ["networkProfile"]    = "4g-lte-advanced-good", // simulate a network condition
            ["language"]          = "fr",                    // localized-build testing
            ["locale"]            = "fr_FR",
            ["timezone"]          = "Europe/Paris",
            ["deviceOrientation"] = "portrait",
            ["enableBiometric"]   = true,                    // sensor instrumentation for biometric prompts
        };
        options.AddAdditionalAppiumOption("bstack:options", bstack);
        options.AddAdditionalAppiumOption("app", appRef);                 // bs://… or a custom_id
        options.AddAdditionalAppiumOption("autoGrantPermissions", true);  // grant manifest permissions on install

        return new AndroidDriver(new Uri(Hub), options);
    }
}
```

Then drive the **dynamic** device features in the test through a small helper. Each is a `browserstack_executor` command (biometric / network) or the standard Appium location API (GPS) — and each must be **awaited on the app's reaction**, never followed by a sleep.

```csharp
// Tests/Support/Farm/DeviceFeatures.cs
using OpenQA.Selenium;
using OpenQA.Selenium.Appium;

namespace Tests.Support.Farm;

public static class DeviceFeatures
{
    /// <summary>Answer the next biometric prompt: match=true approves, false rejects.</summary>
    public static void RespondToBiometric(AppiumDriver driver, bool match) =>
        ((IJavaScriptExecutor)driver).ExecuteScript(
            $"browserstack_executor: {{\"action\":\"performBiometric\",\"arguments\":{{\"match\":{match.ToString().ToLowerInvariant()}}}}}");

    /// <summary>Flip the network condition mid-session (e.g. drop to 2G to test a slow-network path).</summary>
    public static void SwitchNetworkProfile(AppiumDriver driver, string profile) =>
        ((IJavaScriptExecutor)driver).ExecuteScript(
            $"browserstack_executor: {{\"action\":\"updateNetworkProfile\",\"arguments\":{{\"networkProfile\":\"{profile}\"}}}}");

    /// <summary>Move the device GPS mid-session via the standard Appium location API.</summary>
    public static void SetLocation(AppiumDriver driver, double lat, double lon) =>
        driver.Location = new Location { Latitude = lat, Longitude = lon, Altitude = 0 };
}
```

> **The full real-device feature set** (App Automate): `gpsLocation` + mid-session `Location`; `networkProfile` (presets like `2g-gprs-good`, `4g-lte-advanced-good`, or a custom bandwidth/latency/loss profile) + mid-session `updateNetworkProfile`; **biometric** via `enableBiometric` (sensor instrumentation injects a mock into the app) + `performBiometric`; `autoGrantPermissions`; `language`/`locale`/`timezone`; `deviceOrientation`; plus camera-image injection, OTP/SIM workflows, and file upload-to-device for richer flows. **iOS** uses an `XCUITest` `AppiumOptions` with the same `bstack:options` block (biometric = Touch/Face ID injection). Set static features as caps; flip dynamic ones mid-session.

### 4. Put it together — a real-device test

The test reads like any Appium test from `qa/dotnet/skills/ui-test-author/appium`; only setup wires the farm. Note the assertion **waits on the app's reaction** to the biometric injection (an explicit `WebDriverWait` condition), never a `Task.Delay`/`Thread.Sleep`.

```csharp
// Tests/BiometricLoginTests.cs
using NUnit.Framework;
using OpenQA.Selenium.Appium.Android;
using Tests.Support.Farm;
// page objects from qa/dotnet/skills/ui-test-author/appium

[TestFixture]
public class BiometricLoginTests
{
    private static IEnumerable<TargetDevice> Devices => DeviceMatrix.Devices;

    [TestCaseSource(nameof(Devices))]
    public void Should_log_in_When_biometric_is_approved(TargetDevice device)
    {
        var creds = FarmCredentials.BrowserStack();
        AndroidDriver driver = new RealDeviceDriverFactory(creds)
            .Create(device, appRef: "checkout-app", sessionName: $"biometric-login@{device}"); // custom_id app ref
        try
        {
            var login = new LoginPage(driver);          // intent-expressing page object, farm-agnostic
            login.TapBiometricSignIn();
            DeviceFeatures.RespondToBiometric(driver, match: true); // approve the prompt
            var dashboard = login.AwaitDashboard();     // explicit wait inside the page object — no sleep
            Assert.That(dashboard.IsLoaded, Is.True, "biometric login should reach the dashboard");
        }
        finally
        {
            // session status + dashboard URL are owned by cloud-grid-config's teardown; reuse it
            driver.Quit();
        }
    }
}
```

> **Reuse `cloud-grid-config`'s teardown**, don't re-invent it: marking the session pass/fail (`browserstack_executor setSessionStatus`) and attaching the dashboard URL to Allure are that skill's job. This skill adds the *app/device/feature* setup; the session-result reporting is shared.

---

## Remote-run farm — AWS Device Farm

Device Farm is the **other paradigm**: you don't drive a live device — you upload the app and a packaged test suite, schedule a run against a **device-pool ARN**, and poll for the result. Every step that "waits" for AWS is a **bounded condition poll**, never a `Task.Delay` *as* a wait.

```csharp
// Tests/Support/Farm/DeviceFarmRunner.cs
using Amazon.DeviceFarm;
using Amazon.DeviceFarm.Model;

namespace Tests.Support.Farm;

/// <summary>Orchestrates an AWS Device Farm scheduled run: upload → poll → schedule → poll.</summary>
public sealed class DeviceFarmRunner
{
    private readonly IAmazonDeviceFarm _df; // built with the default credential chain / OIDC — no literal keys

    public DeviceFarmRunner(IAmazonDeviceFarm df) => _df = df;

    /// <summary>Create an upload, PUT the bytes, and wait until the farm reports it processed. Returns the upload ARN.</summary>
    public async Task<string> UploadAndAwaitAsync(string projectArn, string name, UploadType type, byte[] bytes,
                                                  CancellationToken ct = default)
    {
        var created = await _df.CreateUploadAsync(
            new CreateUploadRequest { ProjectArn = projectArn, Name = name, Type = type }, ct);
        var upload = created.Upload;
        await PutBytesToPresignedUrlAsync(upload.Url, bytes, ct); // HTTP PUT to the presigned URL

        await PollUntilAsync(TimeSpan.FromMinutes(5), TimeSpan.FromSeconds(5), async () =>
        {
            var status = (await _df.GetUploadAsync(new GetUploadRequest { Arn = upload.Arn }, ct)).Upload.Status;
            if (status == UploadStatus.FAILED) throw new InvalidOperationException($"upload failed: {name}");
            return status == UploadStatus.SUCCEEDED;
        }, ct);
        return upload.Arn;
    }

    /// <summary>Schedule the run and wait until it completes; return the aggregate result.</summary>
    public async Task<ExecutionResult> ScheduleAndAwaitAsync(string projectArn, string appArn, string testPkgArn,
                                                             string devicePoolArn, CancellationToken ct = default)
    {
        var scheduled = await _df.ScheduleRunAsync(new ScheduleRunRequest
        {
            ProjectArn = projectArn,
            AppArn = appArn,
            DevicePoolArn = devicePoolArn,
            Test = new ScheduleRunTest { Type = TestType.APPIUM_JAVA_TESTNG, TestPackageArn = testPkgArn },
        }, ct);
        var runArn = scheduled.Run.Arn;

        await PollUntilAsync(TimeSpan.FromMinutes(30), TimeSpan.FromSeconds(15), async () =>
            (await _df.GetRunAsync(new GetRunRequest { Arn = runArn }, ct)).Run.Status == ExecutionStatus.COMPLETED, ct);

        return (await _df.GetRunAsync(new GetRunRequest { Arn = runArn }, ct)).Run.Result; // PASSED / FAILED / ERRORED
    }

    /// <summary>Bounded condition poll — the interval is between CHECKS, not a sleep-as-wait.</summary>
    private static async Task PollUntilAsync(TimeSpan timeout, TimeSpan interval, Func<Task<bool>> condition,
                                             CancellationToken ct)
    {
        using var cts = CancellationTokenSource.CreateLinkedTokenSource(ct);
        cts.CancelAfter(timeout);
        while (!await condition())
        {
            cts.Token.ThrowIfCancellationRequested(); // deadline → fail loudly, don't hang
            await Task.Delay(interval, cts.Token);     // poll interval between condition checks
        }
    }

    private static Task PutBytesToPresignedUrlAsync(string url, byte[] bytes, CancellationToken ct) =>
        Task.CompletedTask; // HttpClient PUT — omitted for brevity
}
```

> **Device Farm specifics:** the test package type matches your suite (`APPIUM_JAVA_TESTNG_TEST_PACKAGE` + an `APPIUM_JAVA_TESTNG_TEST_SPEC` YAML; Device Farm runs the *uploaded* package, the C# `AmazonDeviceFarmClient` only orchestrates); the app type is `ANDROID_APP` / `IOS_APP`. A **device pool** is created once (in the console or via `CreateDevicePoolAsync` with a device-selection rule) and referenced by ARN. AWS auth comes from the **default credential chain** — in CI prefer **OIDC role assumption** over a long-lived access key (see `qa/dotnet/skills/ci-pipelines/github-actions`). Artifacts (logs, video, screenshots) are fetched per-job via `ListArtifactsAsync(runArn)` after the run completes.

---

## Secrets — env / credential chain only, never logged

Farm credentials are a billable, exfiltratable secret (CLAUDE.md hard rule). BrowserStack is a username + access key from env; AWS is the default credential chain (OIDC in CI). Read them lazily, fail loudly if missing, never log them, never persist them into an artifact or HAR.

```csharp
// Tests/Support/Farm/FarmCredentials.cs
namespace Tests.Support.Farm;

public static class FarmCredentials
{
    private static string Required(string name) =>
        Environment.GetEnvironmentVariable(name) is { Length: > 0 } v
            ? v
            : throw new InvalidOperationException($"Missing env var {name} — set it in your shell or CI secret store.");

    public sealed record BrowserStack(string UserName, string AccessKey);

    public static BrowserStack BrowserStack() =>
        new(Required("BROWSERSTACK_USERNAME"), Required("BROWSERSTACK_ACCESS_KEY"));
    // AWS Device Farm: no creds here — use the default credential chain / OIDC, region from AWS_REGION.
}
```

---

## Comparison — the three farms, app + device + features side by side

| Concept | **BrowserStack App Automate** | **Sauce Labs RDC** | **AWS Device Farm** |
|---|---|---|---|
| Paradigm | Live session | Live session | Remote run (upload + schedule) |
| App upload | `POST api-cloud.browserstack.com/app-automate/upload` → `bs://…` | `POST …/v1/storage/upload` (appStorage) → file id | `CreateUpload` → presigned PUT → ARN |
| App reference | `app` = `bs://…` or `custom_id` | `app` = `storage:filename=app.apk` or `storage:<id>` | `AppArn` on `ScheduleRun` |
| "Always latest" | re-upload same `custom_id` | re-upload same filename | new upload ARN per build |
| Device choice | `bstack:options.deviceName` + `osVersion` | `sauce:options.deviceName` + `platformVersion` | device-pool ARN |
| Real device? | default | real-device flags | physical devices in the pool |
| GPS | `gpsLocation` + `Location` | `Location` | run config |
| Network sim | `networkProfile` + `updateNetworkProfile` | network condition caps | run config |
| Biometric | `enableBiometric` + `performBiometric` | biometric instrumentation | n/a (run-level) |
| Permissions | `autoGrantPermissions` | `autoGrantPermissions` | `autoGrantPermissions` |
| Retention | apps deleted 30 days after last use | per plan | per S3 lifecycle |

**Capability-block schemas** (`bstack:options` vs `sauce:options`), **session pass/fail reporting**, **parallelism → `LevelOfParallelism`**, and **tunnels** are the same across these and are owned by `qa/dotnet/skills/cloud-grid-config` — see it for the side-by-side block table. This skill only adds the app/device/feature/remote-run layer on top.

---

## Anti-patterns

| Smell | Why it's wrong | Do instead |
|---|---|---|
| `app` = a local file path | The farm runs an *uploaded* build; a local path is meaningless to a remote device | Upload first, reference the `bs://…` id / `custom_id` |
| Hard-coding a `bs://…` id in the repo | Apps are deleted 30 days after last use — the id rots | Re-upload in the build job under a stable `custom_id` |
| `Task.Delay(5000)` after a biometric/network injection | Flaky and slow; the device reacts at its own pace | `WebDriverWait` on the app's observable reaction |
| `Task.Delay` polling an AWS run | Wastes time, races the result | `PollUntilAsync(...)` bounded on a deadline |
| Running every device on every PR | Slow, expensive, exceeds the session cap | A small intent-chosen matrix on PR; broad sweep nightly |
| `LevelOfParallelism` > plan session cap | Sessions queue or get rejected | Map the cap onto it (cloud-grid-config owns this) |
| Credentials / access key in code or a committed config | Billable, exfiltratable secret | `Required(...)` env read; AWS via OIDC |
| Re-deriving the capability block / tunnel / status here | Duplicates `cloud-grid-config`, drifts out of sync | Cross-link `cloud-grid-config`; add only the farm layer |
| Emulator caps when the test needs a real device | Biometric/GPS/network features need real hardware | Pin a real `deviceName` (App Automate default) |

## Rules

### App lifecycle
- Upload the build to the farm and reference it by **id** (`bs://…`) or **`custom_id`** — never a local path in the `app` cap.
- Prefer `custom_id` in CI: re-upload under the same id so the `app` cap always picks the latest build with no id-plumbing between jobs.
- Treat the app id as **ephemeral** (30-day retention) — re-upload in the build job; never commit an id as if stable.

### Device selection
- Pin a real device with `deviceName` + `osVersion` (App Automate sessions are real devices by default).
- Drive a **device matrix** from `[TestCaseSource]` (one independent case per device, `ToString()` names it); pick devices by intent, not "all of them."
- Keep concurrent devices ≤ the plan session cap — that cap → NUnit `LevelOfParallelism` is owned by `cloud-grid-config`.

### Real-device features
- Set static features (`gpsLocation`, `networkProfile`, `language`/`locale`/`timezone`, `deviceOrientation`, `enableBiometric`, `autoGrantPermissions`) as caps at session start.
- Flip dynamic features mid-session via `browserstack_executor` (biometric / network) or `driver.Location` (GPS).
- After any injection, **wait on the app's observable reaction** (explicit wait), never a `Task.Delay`/`Thread.Sleep`.

### Remote-run (Device Farm)
- `CreateUpload` → PUT bytes → **poll until SUCCEEDED**; `ScheduleRun` → **poll until COMPLETED**; both via a bounded condition poll, never sleep.
- AWS auth via the default credential chain / **OIDC** in CI, never a literal key. Fetch artifacts after the run via `ListArtifacts`.

### Secrets & boundary
- Credentials via env / credential chain only, read lazily, never logged or persisted to an artifact.
- Do **not** re-derive capability blocks, parallelism, tunnels, or session-status reporting here — cross-link `qa/dotnet/skills/cloud-grid-config`.

## Generation steps

1. Confirm the **paradigm** (live-session BrowserStack/Sauce vs remote-run Device Farm) and **platform** (Android/iOS).
2. Add `Tests/Support/Farm/FarmCredentials.cs` (env reads; AWS via credential chain) — no literals.
3. **Live-session**: add `AppUploader` (REST upload → `bs://…`/`custom_id`), `RealDeviceDriverFactory` (real-device caps + the device-only features the test needs), and `DeviceFeatures` for mid-session injection; drive a device matrix from `[TestCaseSource]`.
4. **Remote-run**: add `DeviceFarmRunner` (`CreateUpload` → poll → `ScheduleRun` → poll `GetRun`) with the bounded `PollUntilAsync` helper.
5. Reuse `cloud-grid-config`'s session-status + dashboard-URL teardown; map the device count onto `LevelOfParallelism` per its rules.
6. Run **one** device/session first to confirm the upload + caps + features before fanning the matrix out; confirm the session/run appears on the dashboard with the right build/project tags.

## Cross-references

- **`qa/dotnet/skills/cloud-grid-config`** — the **prerequisite wiring** this skill builds on: connect, capability-block schemas, parallelism → `LevelOfParallelism`, tunnels, session pass/fail + dashboard URL. This skill adds the app/device/feature/remote-run layer; that one owns the connection plumbing.
- **`qa/java/skills/mobile-device-farm`** (canonical) + **`qa/typescript/skills/mobile-device-farm`** — sibling device-farm stacks. Same four moves (app lifecycle → device selection → real-device features → remote-run), different SDKs. Structure ported, not code.
- **`qa/dotnet/skills/ui-test-author/appium`** — writes the mobile page objects / tests that run **unchanged** on the farm; this skill only swaps the local session for a farm one.
- **`qa/dotnet/skills/data-driven-testing`** — the `[TestCaseSource]` device-matrix mechanics (one independent case per device); this skill supplies the device list, that one the data-driven discipline.
- **`qa/dotnet/skills/ci-pipelines/github-actions`** — build-then-upload job, OIDC for AWS, sharding the matrix across runners (cross-link; don't duplicate).
- **`qa/dotnet/skills/allure-reporting`** — attach the session/run dashboard URL + device name to the report so a farm failure is one click from the replay.
