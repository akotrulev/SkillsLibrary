---
name: qa-device-cloud-dotnet
description: Use when running .NET (C#) Appium tests on a real-device cloud — app upload, device matrix, cloud capabilities, parallel runs. Triggers "upload our app to BrowserStack App Automate and run the C# Appium tests", "run our NUnit mobile suite across a real-device matrix", "test biometric login on a real device". Not for local emulator runs or OS-surface features (`mobile-native-features`).
---

# QA — Mobile Device Farm (.NET: Appium.WebDriver 9 on a real-device cloud)

Runs .NET Appium tests against a **live-session real-device cloud** — BrowserStack App Automate, Sauce Labs Real Device Cloud or LambdaTest — and owns the parts that are *specific to the farm* rather than to a generic grid: getting the app **onto** the farm, **picking the devices**, and exercising **real-device-only features** (GPS, network conditions, biometrics, permissions, locale).

> **Boundary — this skill builds ON `qa/dotnet/skills/browser-cloud-setup`, it does not repeat it.** `browser-cloud-setup` is the *wiring*: connecting a driver to a remote hub, the `bstack:options` / `sauce:options` block schemas, mapping the plan's session cap onto NUnit `NumberOfTestWorkers`, the session URL and pass/fail, and tunnels. All of that is assumed here and cross-linked.

## Stack

- .NET 10, C# (nullable reference types enabled); the pins (`Appium.WebDriver` 9.0.0, NUnit 4.6.1, `Allure.NUnit` 2.15.0) are the **Versions** table of `qa/dotnet/skills/ui-test-author/appium/SKILL.md`
- **App upload (REST):** `HttpClient` + `MultipartFormDataContent` + `System.Text.Json` for the BrowserStack App Automate endpoint
- Farm support code under `AppiumTests/Support/Farm/`; credentials via **env vars only** (`BROWSERSTACK_USERNAME` / `BROWSERSTACK_ACCESS_KEY`)
- The page objects come from `ui-test-author/appium` and run **unchanged** on the farm; only the driver differs
- Runs in CI under `qa/cicd/dotnet/skills/ci-pipelines`

## Does the farm run Appium 3?

The primary lane is Appium 3 with Appium.WebDriver 9. **Check the vendor before relying on it**; a cloud still on Appium 2 keeps the suite on the supported lane (Appium.WebDriver 8.x, UiAutomator2 4.x, XCUITest 9.x).

1. Read the vendor's own list of Appium versions, and the capability that selects one: `appiumVersion` inside `bstack:options` (BrowserStack) or `sauce:options` (Sauce Labs). BrowserStack's public page listed only 2.x and Sauce's migration page showed 2.13.1 on 2026-10-10, so neither is assumed to offer 3.
2. Set the capability to a 3.x value and start one session. A vendor without Appium 3 rejects it or falls back to 2; a green run does not tell which.
3. `driver.Capabilities` on the started session shows what the vendor granted; `GET <hub>/status` reports `build.version` where the hub proxies it.
4. Appium.WebDriver 9's only breaking change is strong-name signing, so the client bump is not itself gated on the server; the `mobile:` commands it sends are what an older driver may lack. One session settles it.

## When to use

- Uploading a build (`.apk`/`.aab`/`.xapk`/`.ipa`) and referencing it from the `app` capability (by `bs://…` id or `custom_id`)
- One suite across a **matrix of real devices and OS versions**
- A feature that needs a **real device**: biometric login, GPS-based behavior, a network condition, permissions, a localized build

## When NOT to use

- Connect, capability blocks, parallelism, tunnels, status wiring → `qa/dotnet/skills/browser-cloud-setup`
- Java / TypeScript farms → `qa/{java,typescript}/skills/device-cloud`
- Page objects and tests → `qa/dotnet/skills/ui-test-author/appium`
- CI matrix and sharding → `qa/cicd/dotnet/skills/ci-pipelines/*`
- Web (Playwright) cloud runs → `qa/dotnet/skills/browser-cloud-setup`

## AWS Device Farm cannot run a .NET Appium suite

Device Farm is a **remote-run** farm: it runs an uploaded test package on its own infrastructure. Its `ScheduleRunTest` types name Appium for Java (JUnit, TestNG), Python, Node and Ruby, and **none for .NET**, so a NUnit suite cannot be shipped there and polled for a verdict. A custom-environment test spec that runs `dotnet test` on the farm's host is conceivable, but it is unverified here and this skill does not teach it. For a .NET suite use a **live-session** farm: your NUnit process runs locally or in CI and drives the remote device over the hub URL. A team already on AWS that needs Device Farm writes the Appium suite in Java or TypeScript for that run (`qa/{java,typescript}/skills/device-cloud`).

| | **Live-session farm** (usable from .NET) |
|---|---|
| Vendors | BrowserStack App Automate, Sauce Labs RDC, LambdaTest |
| How it runs | Your NUnit process drives a remote device over a hub URL in real time |
| The app | Upload once → reference `bs://…` / `custom_id` in the `app` option |
| Device choice | `deviceName` + `osVersion` per session |
| Assertions | In your test, live, against the running device |

## Deep-dive reference

`references/details.md` holds the **BrowserStack App Automate** path with its code: the app upload, the device matrix read from configuration, the real-device driver factory, the mid-session `DeviceFeatures`, and a worked test — **read it when the task touches them**.

## Secrets — env only, never logged

Farm credentials are a billable, exfiltratable secret. Read them lazily, fail loudly if missing, never log them, never persist them into an artifact or HAR.

```csharp
namespace AppiumTests.Support.Farm;

public sealed record BrowserStackCredentials(string UserName, string AccessKey)
{
    public static BrowserStackCredentials FromEnvironment() =>
        new(Required("BROWSERSTACK_USERNAME"), Required("BROWSERSTACK_ACCESS_KEY"));

    private static string Required(string name) =>
        Environment.GetEnvironmentVariable(name) is { Length: > 0 } value
            ? value
            : throw new InvalidOperationException($"Missing env var {name} — set it in your shell or CI secret store");
}
```

## Comparison — the live-session farms side by side

| Concept | **BrowserStack App Automate** | **Sauce Labs RDC** |
|---|---|---|
| App upload | `POST api-cloud.browserstack.com/app-automate/upload` → `bs://…` | `POST …/v1/storage/upload` (appStorage) → file id |
| App reference | `app` = `bs://…` or `custom_id` | `app` = `storage:filename=app.apk` or `storage:<id>` |
| "Always latest" | re-upload same `custom_id` | re-upload same filename |
| Device choice | `bstack:options.deviceName` + `osVersion` | `sauce:options.deviceName` + `platformVersion` |
| GPS | `gpsLocation` | the vendor's location capability |
| Network sim | `networkProfile` + `updateNetworkProfile` | network condition caps |
| Biometric | `enableBiometric` + `performBiometric` | biometric instrumentation |
| Permissions | `autoGrantPermissions` | `autoGrantPermissions` |
| Retention | apps deleted 30 days after last use | per plan |

Capability-block schemas, **session pass/fail**, **parallelism** and **tunnels** are owned by `qa/dotnet/skills/browser-cloud-setup`. The farm's own capability names for device and network logs are unverified here.

## Anti-patterns

| Smell | Do instead |
|---|---|
| `app` = a local file path | Upload first, reference the `bs://…` id / `custom_id` |
| Hard-coding a `bs://…` id in the repo | Re-upload in the build job under a stable `custom_id` (ids rot after 30 days) |
| `Task.Delay` after a biometric or network injection | `WebDriverWait` on the app's observable reaction |
| A device list written in a C# file | Read it from `farm-devices.json` |
| Running every device on every PR | A small intent-chosen matrix on PR; broad sweep nightly |
| `NumberOfTestWorkers` above the plan's session cap | Map the cap onto it (`browser-cloud-setup` owns this) |
| `try`/`finally` around the driver in a test | Quit it in `[TearDown]` |
| Credentials in code or a committed config | `Required(...)` env read |
| Re-deriving the capability block, tunnel or status here | Cross-link `browser-cloud-setup` |
| Emulator options when the test needs a real device | Pin a real `deviceName` (App Automate default) |
| Scheduling a .NET suite on AWS Device Farm | A live-session farm, or a Java/TypeScript suite |

## Rules

### App lifecycle
- Upload the build to the farm and reference it by **id** (`bs://…`) or **`custom_id`** — never a local path in the `app` option.
- Prefer `custom_id` in CI: re-upload under the same id so the `app` option always picks the latest build.
- Treat the app id as **ephemeral** (30-day retention); never commit an id as if stable.

### Device selection
- Pin a real device with `deviceName` + `osVersion`.
- Drive a **device matrix** from `[TestCaseSource]` (one independent case per device, `ToString()` names it) over devices read from **configuration**, never literals in code; pick devices by intent.
- Keep concurrent devices at or below the plan's session cap.

### Real-device features
- Set static features (`gpsLocation`, `networkProfile`, `language`/`locale`/`timezone`, `deviceOrientation`, `enableBiometric`, `autoGrantPermissions`) at session start.
- Flip dynamic features mid-session through `browserstack_executor` (biometric, network).
- After any injection, **wait on the app's observable reaction**, never `Task.Delay` or `Thread.Sleep`.

### Secrets and boundary
- Credentials via env only, read lazily, never logged or persisted to an artifact.
- Do **not** re-derive capability blocks, parallelism, tunnels or session-status reporting — cross-link `browser-cloud-setup`.

## Generation steps

1. Confirm the farm is a live-session one, the **platform**, and that the farm runs Appium 3 (or fall back to the supported lane).
2. Add `AppiumTests/Support/Farm/BrowserStackCredentials.cs` — no literals.
3. Add `AppUploader`, `RealDeviceDriverFactory`, `DeviceFeatures`, `DeviceMatrix` and `farm-devices.json` from `references/details.md`; drive the matrix from `[TestCaseSource]`.
4. Reuse `browser-cloud-setup`'s session-status teardown; map the device count onto `NumberOfTestWorkers`.
5. Run **one** device first to confirm the upload, options and features before fanning the matrix out.

## Cross-references

- **`qa/dotnet/skills/browser-cloud-setup`** — connect, capability blocks, parallelism, tunnels, session pass/fail and dashboard URL
- **`qa/java/skills/device-cloud`**, **`qa/typescript/skills/device-cloud`** — the sibling stacks, including the AWS Device Farm remote-run lane that .NET lacks
- **`qa/dotnet/skills/ui-test-author/appium`** — the page objects and `BaseMobileTest` that run unchanged on the farm
- **`qa/dotnet/skills/evidence-capture`** — farm session video and the pass/fail mark (`references/appium.md` § Device farms)
- **`qa/dotnet/skills/data-driven-testing`** — the `[TestCaseSource]` mechanics
- **`qa/cicd/dotnet/skills/ci-pipelines`** — build-then-upload job, sharding the matrix
- **`qa/reporting/dotnet/skills/test-reports`** — attach the session dashboard URL and device name to the report
