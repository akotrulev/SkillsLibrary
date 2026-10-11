# Deep-dive details — `qa-dotnet:device-cloud`

Sections moved out of SKILL.md for on-demand loading. Read what the task needs.

## Live-session farm — BrowserStack App Automate

### 1. App lifecycle — get the build onto the farm, reference it by id

The farm runs *an uploaded build*, never a local file path. Upload the `.apk`/`.aab`/`.ipa` once to the App Automate REST endpoint; the response carries a `bs://…` id for the `app` option. Give it a **`custom_id`** so re-uploads under the same id let the `app` option always pick the latest build: build → upload under `custom_id` → tests reference the `custom_id`, with no id passed between jobs.

```csharp
using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;

namespace AppiumTests.Support.Farm;

public sealed class AppUploader(HttpClient http, BrowserStackCredentials credentials)
{
    private const string UploadUrl = "https://api-cloud.browserstack.com/app-automate/upload";

    public async Task<string> UploadAsync(string buildPath, string customId, CancellationToken cancellationToken = default)
    {
        using var content = new MultipartFormDataContent();
        var file = new ByteArrayContent(await File.ReadAllBytesAsync(buildPath, cancellationToken));
        file.Headers.ContentType = new MediaTypeHeaderValue("application/octet-stream");
        content.Add(file, "file", Path.GetFileName(buildPath));
        content.Add(new StringContent(customId), "custom_id");

        using var request = new HttpRequestMessage(HttpMethod.Post, UploadUrl) { Content = content };
        var basic = Convert.ToBase64String(Encoding.UTF8.GetBytes($"{credentials.UserName}:{credentials.AccessKey}"));
        request.Headers.Authorization = new AuthenticationHeaderValue("Basic", basic);

        using var response = await http.SendAsync(request, cancellationToken);
        var body = await response.Content.ReadAsStringAsync(cancellationToken);
        if (!response.IsSuccessStatusCode)
        {
            throw new InvalidOperationException($"Upload of {Path.GetFileName(buildPath)} failed with {(int)response.StatusCode}: {body}");
        }
        using var json = JsonDocument.Parse(body);
        return json.RootElement.GetProperty("app_url").GetString()
            ?? throw new InvalidOperationException($"Upload response has no app_url: {body}");
    }
}
```

> **Reference the app three ways, in order of CI-friendliness:** (1) `custom_id`: `options.AddAdditionalAppiumOption("app", "MyApp")` picks the **last build uploaded under that id**; (2) the raw `bs://…` id from a one-off upload; (3) a **public URL** (the `url` form field on upload). Apps are **deleted 30 days after last use**: re-upload in the build job, and never commit a `bs://…` id as if it were stable.

### 2. Device selection — pin a device, or fan out a matrix

On App Automate every session is a **real device** by default. You pick it with `deviceName` + `osVersion` in `bstack:options`. The matrix lives in configuration, not in code, so a device change is a data change:

```json
[
  { "DeviceName": "Samsung Galaxy S23", "OsVersion": "13.0" },
  { "DeviceName": "Google Pixel 8", "OsVersion": "14.0" }
]
```

`farm-devices.json` is copied to the output folder (`<None Update="farm-devices.json" CopyToOutputDirectory="PreserveNewest" />`) and read once:

```csharp
using System.Text.Json;

namespace AppiumTests.Support.Farm;

public sealed record TargetDevice(string DeviceName, string OsVersion)
{
    public override string ToString() => $"{DeviceName} ({OsVersion})";
}

public static class DeviceMatrix
{
    private static readonly string DevicesFile = Path.Combine(AppContext.BaseDirectory, "farm-devices.json");

    public static IEnumerable<TargetDevice> Devices =>
        JsonSerializer.Deserialize<List<TargetDevice>>(File.ReadAllText(DevicesFile))
            ?? throw new InvalidOperationException($"{DevicesFile} holds no device list");
}
```

> **Pick devices by intent, not "all of them."** A matrix covers the segments that actually differ (a vendor skin, an old OS, a screen size that breaks layout), not 200 devices on every PR. Reserve the broad sweep for nightly. The cap on how many run at once is the plan's session cap, mapped onto `NumberOfTestWorkers` by `browser-cloud-setup`.

### 3. Real-device-only capabilities

Set the static ones at session start; flip the dynamic ones **mid-session** through the `browserstack_executor` hook. The driver comes from a factory, as `ui-test-author/appium`'s `AppiumDriverFactory` does for local sessions; only the option block and the hub URL change.

```csharp
using OpenQA.Selenium.Appium;
using OpenQA.Selenium.Appium.Android;

namespace AppiumTests.Support.Farm;

public sealed class RealDeviceDriverFactory(BrowserStackCredentials credentials)
{
    private static readonly Uri Hub = new("https://hub-cloud.browserstack.com/wd/hub");

    public AndroidDriver Create(TargetDevice device, string appReference, string sessionName)
    {
        var options = new AppiumOptions { AutomationName = "UiAutomator2", PlatformName = "Android" };
        var bstack = new Dictionary<string, object>
        {
            ["userName"] = credentials.UserName,
            ["accessKey"] = credentials.AccessKey,
            ["deviceName"] = device.DeviceName,
            ["osVersion"] = device.OsVersion,
            ["projectName"] = Environment.GetEnvironmentVariable("BROWSERSTACK_PROJECT") ?? "mobile-tests",
            ["buildName"] = Environment.GetEnvironmentVariable("BUILD_NAME") ?? "local-build",
            ["sessionName"] = sessionName,
            ["gpsLocation"] = "40.730610,-73.935242",
            ["networkProfile"] = "4g-lte-advanced-good",
            ["language"] = "fr",
            ["locale"] = "fr_FR",
            ["timezone"] = "Europe/Paris",
            ["deviceOrientation"] = "portrait",
            ["enableBiometric"] = true,
        };
        options.AddAdditionalAppiumOption("bstack:options", bstack);
        options.AddAdditionalAppiumOption("app", appReference);
        options.AddAdditionalAppiumOption("autoGrantPermissions", true);
        options.AddAdditionalAppiumOption("appium:settings[disableIdLocatorAutocompletion]", true);
        return new AndroidDriver(Hub, options);
    }
}
```

The `gpsLocation`, `networkProfile`, `language`, `locale` and `timezone` values above are the example's, not defaults to copy; read them from the same configuration as the device list when a test needs another. Then drive the **dynamic** features in the test through a small helper; each is awaited on the app's reaction, never followed by a sleep:

```csharp
using OpenQA.Selenium;
using OpenQA.Selenium.Appium;

namespace AppiumTests.Support.Farm;

public static class DeviceFeatures
{
    public static void RespondToBiometric(AppiumDriver driver, bool match) =>
        ((IJavaScriptExecutor)driver).ExecuteScript(
            $"browserstack_executor: {{\"action\":\"performBiometric\",\"arguments\":{{\"match\":\"{(match ? "true" : "false")}\"}}}}");

    public static void SwitchNetworkProfile(AppiumDriver driver, string profile) =>
        ((IJavaScriptExecutor)driver).ExecuteScript(
            $"browserstack_executor: {{\"action\":\"updateNetworkProfile\",\"arguments\":{{\"networkProfile\":\"{profile}\"}}}}");
}
```

> **The real-device feature set** (App Automate): `gpsLocation`; `networkProfile` (presets like `2g-gprs-good`, `4g-lte-advanced-good`, or a custom profile) and mid-session `updateNetworkProfile`; **biometric** through `enableBiometric` (sensor instrumentation) and `performBiometric`; `autoGrantPermissions`; `language` / `locale` / `timezone`; `deviceOrientation`; plus camera-image injection and OTP/SIM workflows. **iOS** uses an XCUITest `AppiumOptions` with the same `bstack:options` block. A mid-session GPS change goes through the vendor's own call; the removed legacy `/location` route is not the way (Appium 4 drops it), and a `mobile:` geolocation command on a farm device is unverified here. The `performBiometric` and `updateNetworkProfile` argument spellings come from the vendor's documentation and were not run here.

### 4. Put it together — a real-device test

The test reads like any Appium test from `ui-test-author/appium`; only the setup wires the farm. The driver is built in the test and quit in `[TearDown]`, so a failed assertion still releases the device. The assertion waits on the app's reaction (an explicit wait inside the page object), never a sleep.

```csharp
using AppiumTests.Pages;
using AppiumTests.Support.Farm;
using NUnit.Framework;
using OpenQA.Selenium.Appium.Android;

namespace AppiumTests.Tests;

public class BiometricLoginTests
{
    private AndroidDriver? _driver;

    private static IEnumerable<TargetDevice> Devices => DeviceMatrix.Devices;

    [TearDown]
    public void QuitDriver() => _driver?.Quit();

    [TestCaseSource(nameof(Devices))]
    public void Should_ReachDashboard_When_BiometricIsApproved(TargetDevice device)
    {
        _driver = new RealDeviceDriverFactory(BrowserStackCredentials.FromEnvironment())
            .Create(device, appReference: "checkout-app", sessionName: $"biometric-login@{device}");
        var login = new LoginPage(_driver);
        login.TapBiometricSignIn();

        DeviceFeatures.RespondToBiometric(_driver, match: true);

        Assert.That(login.AwaitDashboard().IsLoaded(), Is.True, $"dashboard after an approved biometric on {device}");
    }
}
```

> **Reuse `browser-cloud-setup`'s teardown**: marking the session pass/fail and attaching the dashboard URL to Allure are that skill's job, and `evidence-capture/references/appium.md` § Device farms lists the executor calls. This skill adds the app, device and feature setup.
