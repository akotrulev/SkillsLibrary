---
name: qa-mobile-device-farm-dotnet
description: Use when the user needs the **real-device-cloud specifics** of running .NET (C#) Appium tests on a mobile device farm. Triggers: "upload our app to BrowserStack App Automate and run the C# Appium tests", "run our NUnit mobile suite across a real-device matrix", "test biometric login on a real device in .NET".
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
- Runs in CI under `qa/dotnet/skills/ci-pipelines`; the page objects come from `qa/dotnet/skills/ui-test-author/appium` and run **unchanged** on the farm

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

## Deep-dive reference

These sections live in `references/details.md` — **read it when the task touches them**: **Live-session farm — BrowserStack App Automate (the canonical path)**.

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

> **Device Farm specifics:** the test package type matches your suite (`APPIUM_JAVA_TESTNG_TEST_PACKAGE` + an `APPIUM_JAVA_TESTNG_TEST_SPEC` YAML; Device Farm runs the *uploaded* package, the C# `AmazonDeviceFarmClient` only orchestrates); the app type is `ANDROID_APP` / `IOS_APP`. A **device pool** is created once (in the console or via `CreateDevicePoolAsync` with a device-selection rule) and referenced by ARN. AWS auth comes from the **default credential chain** — in CI prefer **OIDC role assumption** over a long-lived access key (see `qa/dotnet/skills/ci-pipelines`). Artifacts (logs, video, screenshots) are fetched per-job via `ListArtifactsAsync(runArn)` after the run completes.

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
- **`qa/dotnet/skills/ci-pipelines`** — build-then-upload job, OIDC for AWS, sharding the matrix across runners (cross-link; don't duplicate).
- **`qa/dotnet/skills/allure-reporting`** — attach the session/run dashboard URL + device name to the report so a farm failure is one click from the replay.
