# Deep-dive details — `qa-device-cloud-dotnet`

Sections moved out of SKILL.md for on-demand loading. Read what the task needs.

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

> **Pick devices by intent, not "all of them."** A device matrix is for covering the segments that actually differ (a vendor skin, an old OS, a screen size that breaks layout) — not for running 200 devices on every PR. Reserve the broad sweep for nightly. The cap on how many run at once is the **plan's session cap → NUnit `LevelOfParallelism`**, which `browser-cloud-setup` owns; don't set a level here that exceeds it. A **private/dedicated device pool** (a plan add-on) is selected the same way — the device is just reserved to your org.

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
            // session status + dashboard URL are owned by browser-cloud-setup's teardown; reuse it
            driver.Quit();
        }
    }
}
```

> **Reuse `browser-cloud-setup`'s teardown**, don't re-invent it: marking the session pass/fail (`browserstack_executor setSessionStatus`) and attaching the dashboard URL to Allure are that skill's job. This skill adds the *app/device/feature* setup; the session-result reporting is shared.

---
