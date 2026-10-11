---
name: qa-mobile-native-features-dotnet
description: Use when testing the device-native, OS-level capabilities a mobile app uses that a normal Appium page-object UI test doesn't exercise — permissions, push, deep links, biometrics, camera. Triggers "test our deep link opens the right screen in Appium C#", "handle the camera/location permission dialog", "test Face ID / fingerprint login on the simulator". Not for device-cloud wiring (`device-cloud`).
---

# QA — Mobile Native Features (.NET: Appium.WebDriver 9 + Appium 3 + NUnit)

Appium tests for the **OS-level capabilities** a mobile app touches but a page-object UI test never exercises: deep links, runtime permission dialogs, biometrics, push notifications, the app lifecycle, the clipboard, orientation. It sits on `qa/dotnet/skills/ui-test-author/appium`: `BaseAppiumPage`, `AppiumDriverFactory`, `BaseMobileTest` and the page objects run **unchanged**. This skill adds the layer that drives the OS surfaces *around* your screens.

> **Four ideas separate a native-feature test from a page-object reflex:**
>
> 1. **A native feature lives outside your app's element tree.** A permission dialog, the biometric prompt, the notification shade, a deep-link intent and the lifecycle state belong to Android or iOS. Drive them with `mobile:` commands and the driver's device calls, then assert the *effect* on your own screen through a page object.
> 2. **A deep link is tested by routing, not by tapping.** Launch through the link and assert the destination page. Tapping through the UI tests your taps.
> 3. **Biometrics and permissions are injected for determinism, and driven for real only when the flow is under test.** A fingerprint or face match is injected on the emulator or simulator, never a real sensor. A permission is pre-granted by capability for the tests that only need it out of the way; the real dialog is driven for the few tests about grant versus deny.
> 4. **The lifecycle is an assertion target.** Background, resume, terminate and a push arriving are each followed by a bounded wait on the app's reaction, never a sleep.

## Decision matrix — native surface → test shape

| Native surface | Test shape (Appium.WebDriver 9) |
|---|---|
| **Deep / universal link** | `mobile: deepLink` → assert the destination **page object** |
| **Permission — out of the way** | option `autoGrantPermissions` (Android) · `autoAcceptAlerts` (iOS), set in `AppiumDriverFactory` |
| **Permission — a specific state** | Android `mobile: changePermissions` · iOS simulator `mobile: setPermission` |
| **Permission — the dialog is the test** | `Driver.SwitchTo().Alert()` (iOS) · the `permissioncontroller` buttons (Android) → assert granted versus degraded UX |
| **Biometric — approved / rejected** | Android `mobile: fingerprint` · iOS `mobile: sendBiometricMatch` → assert the unlocked screen, then the fallback |
| **Push** | Android `OpenNotifications()` · iOS simulator `mobile: pushNotification` → open it → assert the routed screen |
| **Background → resume** | `BackgroundApp(TimeSpan)` → wait on the restored screen |
| **Terminate → relaunch** | `TerminateApp` → `ActivateApp` → `GetAppState` |
| **Geolocation** | Android `mobile: setGeolocation` · iOS `mobile: setSimulatedLocation` → assert the location-driven screen |
| **Clipboard** | `mobile: setClipboard` (base64) → paste → assert |
| **Camera / file picker** | seed the file with `PushFile`, drive the picker, never the real camera |
| **Orientation** | `Driver.Orientation = ScreenOrientation.Landscape` → assert the layout reflows |

## Stack

- .NET 10; the pins (`Appium.WebDriver` 9.0.0, `Selenium.Support`, NUnit 4.6.1, `Allure.NUnit` 2.15.0) are the **Versions** table of `qa/dotnet/skills/ui-test-author/appium/SKILL.md`. This skill adds no package; Appium.WebDriver 8.x is the supported lane and every helper below exists there
- **NUnit** assertions with a subject (`Assert.That(actual, Is.EqualTo(expected), subject)`); failure evidence is `BaseMobileTest`, and this skill adds no second hook
- Helpers live in `AppiumTests/Support/Native/`
- Appium 3 removed the old `/appium/*` routes and Appium.WebDriver 8.0 removed `ToggleWifi`, `ToggleData`, `ToggleAirplaneMode` and `SetConnectionType`. Network state is `mobile: setConnectivity` (`wifi`, `data`, `airplaneMode`); there is no client method to call
- `AppiumDriver` has `BackgroundApp`, `ActivateApp`, `TerminateApp`, `PushFile`, `FingerPrint(int)` and `Orientation`. `GetAppState`, the clipboard methods and `OpenNotifications()` sit on `AndroidDriver` / `IOSDriver`, which is why the helper below uses the `mobile:` form for the clipboard and a `switch` for the state

## When to use

- A **deep or universal link** must open the right screen
- Behavior **behind a runtime permission**, with the dialog handled or under test
- **Biometric** login or step-up on an emulator or simulator, approve and reject
- State that must survive **backgrounding**, a cold relaunch, or a push tap
- **Geolocation**, **clipboard**, **picker** or **orientation** behavior

## When NOT to use

- The app's own screens → `qa/dotnet/skills/ui-test-author/appium`
- Real-device farm wiring and farm-side biometric/GPS injection → `qa/dotnet/skills/device-cloud`
- The requests an app makes → `qa/dotnet/skills/network-mocking/*`
- Token auth → `qa/dotnet/skills/test-login-tokens`

## The helper

`NativeFeatures` owns every OS-surface call, including the ones that touch OS UI, so no test holds a raw `FindElement` or a wait. A test reads: *drive the OS surface, assert the effect on a page object.* The identifier is a package on Android and a bundle id on iOS, so one private method picks the key.

```csharp
using System.Text;
using OpenQA.Selenium;
using OpenQA.Selenium.Appium;
using OpenQA.Selenium.Appium.Android;
using OpenQA.Selenium.Appium.Enums;
using OpenQA.Selenium.Appium.iOS;
using OpenQA.Selenium.Support.UI;

namespace AppiumTests.Support.Native;

public sealed class NativeFeatures(AppiumDriver driver)
{
    private static readonly TimeSpan Timeout = TimeSpan.FromSeconds(10);
    private const int UnenrolledFingerprintId = 99;
    private const string PermissionDenyButtonId = "com.android.permissioncontroller:id/permission_deny_button";

    public void OpenDeepLink(string url, string appIdentifier) =>
        driver.ExecuteScript("mobile: deepLink", new Dictionary<string, object>
        {
            ["url"] = url,
            [IsIos ? "bundleId" : "package"] = appIdentifier,
        });

    public void ApproveFingerprint(int fingerprintId) =>
        driver.ExecuteScript("mobile: fingerprint", new Dictionary<string, object> { ["fingerprintId"] = fingerprintId });

    public void RejectFingerprint() => ApproveFingerprint(UnenrolledFingerprintId);

    public void SendIosBiometric(string type, bool match) =>
        driver.ExecuteScript("mobile: sendBiometricMatch", new Dictionary<string, object> { ["type"] = type, ["match"] = match });

    public void BackgroundFor(TimeSpan duration) => driver.BackgroundApp(duration);

    public void Terminate(string appIdentifier) => driver.TerminateApp(appIdentifier);

    public void Activate(string appIdentifier) => driver.ActivateApp(appIdentifier);

    public AppState StateOf(string appIdentifier) => driver switch
    {
        AndroidDriver android => android.GetAppState(appIdentifier),
        IOSDriver ios => ios.GetAppState(appIdentifier),
        _ => throw new InvalidOperationException($"No app state for {driver.GetType().Name}"),
    };

    public void SetAndroidLocation(double latitude, double longitude) =>
        driver.ExecuteScript("mobile: setGeolocation", new Dictionary<string, object> { ["latitude"] = latitude, ["longitude"] = longitude });

    public void SetIosLocation(double latitude, double longitude) =>
        driver.ExecuteScript("mobile: setSimulatedLocation", new Dictionary<string, object> { ["latitude"] = latitude, ["longitude"] = longitude });

    public void SetClipboard(string text) =>
        driver.ExecuteScript("mobile: setClipboard", new Dictionary<string, object>
        {
            ["content"] = Convert.ToBase64String(Encoding.UTF8.GetBytes(text)),
            ["contentType"] = "plaintext",
        });

    public string Clipboard()
    {
        var base64 = (string?)driver.ExecuteScript("mobile: getClipboard", new Dictionary<string, object> { ["contentType"] = "plaintext" });
        return Encoding.UTF8.GetString(Convert.FromBase64String(base64 ?? string.Empty));
    }

    public void DismissIosAlert() => driver.SwitchTo().Alert().Dismiss();

    public void DenyAndroidPermission() =>
        new WebDriverWait(driver, Timeout)
            .Until(_ => driver.FindElements(MobileBy.Id(PermissionDenyButtonId)).FirstOrDefault(button => button.Enabled))!
            .Click();

    public void OpenAndroidNotification(string text)
    {
        driver.ExecuteScript("mobile: openNotifications", new Dictionary<string, object>());
        new WebDriverWait(driver, Timeout)
            .Until(_ => driver.FindElements(By.XPath($"//*[contains(@text, '{text}')]")).FirstOrDefault(row => row.Displayed))!
            .Click();
    }

    public ScreenOrientation Orientation
    {
        set => driver.Orientation = value;
    }

    private bool IsIos => driver is IOSDriver;
}
```

The clipboard travels as **base64** in both directions: a raw string is not a valid payload.

## 1. Deep and universal links — test the routing (idea 2)

`mobile: deepLink` builds the intent on Android and opens the URL on iOS. The test never taps.

```csharp
[Test]
public void Should_OpenOrderDetails_When_OrderLinkIsOpened()
{
    new NativeFeatures(Driver).OpenDeepLink("myapp://orders/A-1001", "com.example.shop");

    var details = new OrderDetailsPage(Driver);
    details.VerifyPageLoaded();
    Assert.That(details.OrderNumber(), Is.EqualTo("A-1001"), "order shown by the deep link");
}
```

- On iOS, `mobile: deepLink` works on a simulator and on a real device from iOS 16.4 and Xcode 14.3; only below that does a real device need the link opened in Safari.
- A Universal or App Link is an `https://` URL the OS associates with the app (`apple-app-site-association`, `assetlinks.json`); a custom scheme (`myapp://`) is app-private. Test the **https** form to prove the association resolves.

## 2. Permission dialogs — deterministic by default (idea 3)

**Out of the way (most tests).** The options are set where the session is built (`AppiumDriverFactory`): `autoGrantPermissions` on Android, `autoAcceptAlerts` on iOS (`autoDismissAlerts` denies), each through `AddAdditionalAppiumOption`.

**A specific posture.** Android: `mobile: changePermissions` with `permissions`, `appPackage` and `action` `grant` or `revoke`, and `mobile: getPermissions`. iOS simulator: `mobile: setPermission` with `bundleId` and `access` such as `camera` → `yes`.

**The dialog is the test.** Drive the real OS dialog through `NativeFeatures`, then assert the degraded path your app renders:

```csharp
[Test]
public void Should_ShowManualLocationPrompt_When_LocationIsDenied()
{
    var map = new MapPage(Driver);
    map.TapUseMyLocation();

    new NativeFeatures(Driver).DismissIosAlert();

    Assert.That(map.IsManualLocationPromptShown(), Is.True, "manual location prompt after a denied permission");
}
```

On Android the dialog belongs to the `com.android.permissioncontroller` package, and `DenyAndroidPermission()` waits for its button by resource id. Prefer the option or `changePermissions`, and walk the buttons only when the dialog UX is under test. On iOS a foreground system alert makes the active app `com.apple.springboard`; the alert API handles that, so never hardcode button coordinates.

## 3. Biometrics — inject the match, assert the unlock and the reject (idea 3)

There is no sensor in CI. Enroll on the device, trigger the prompt from your screen, inject, assert. Test both paths.

```csharp
[Test]
public void Should_ReachDashboard_When_FingerprintIsApproved()
{
    var login = new LoginPage(Driver);
    login.TapBiometricSignIn();

    new NativeFeatures(Driver).ApproveFingerprint(1);

    Assert.That(login.AwaitDashboard().IsLoaded(), Is.True, "dashboard after an approved fingerprint");
}

[Test]
public void Should_ShowPinFallback_When_FingerprintIsRejected()
{
    var login = new LoginPage(Driver);
    login.TapBiometricSignIn();

    new NativeFeatures(Driver).RejectFingerprint();

    Assert.That(login.IsPinFallbackShown(), Is.True, "PIN fallback after a rejected fingerprint");
}
```

On an iOS simulator, call `mobile: enrollBiometric` with `isEnabled` true once, then `SendIosBiometric("faceId", true)` or `false`. No capability enrolls biometrics.

A real device cannot take an injected read locally; BrowserStack and Sauce instrument the sensor, which `device-cloud` owns. Write the approve and reject assertions here and run them on the farm's injected biometric there.

## Deep-dive reference

`references/details.md` holds **4. Push notifications and backgrounding** — read it when the task touches them.

## Clipboard, pickers, orientation

```csharp
[Test]
public void Should_FillPromoField_When_CodeIsPasted()
{
    new NativeFeatures(Driver).SetClipboard("PROMO2026");

    sharePage.TapPasteCode();

    Assert.That(checkoutPage.PromoCode(), Is.EqualTo("PROMO2026"), "promo field after a paste");
}
```

A camera, photo or file picker is an OS surface you cannot drive in CI. Seed the file the picker returns with `Driver.PushFile(remotePath, bytes)`, pick it from the gallery picker, and assert how your app handled it.

## Anti-patterns

| Smell | Do instead |
|---|---|
| A page-object finder on the OS permission or biometric dialog | The option, `mobile: changePermissions`, or the alert API |
| Reaching a screen by tapping to test a deep link | `mobile: deepLink` → assert the destination page |
| `Thread.Sleep` after a background, an injection or a push | `WebDriverWait` on the restored, unlocked or routed screen |
| A real fingerprint or camera | Inject the match; seed picker files with `PushFile` |
| Only the approve path | Test the reject path too; reject is where apps crash |
| A raw `FindElement` or a wait inside a test body | An intent method on `NativeFeatures` |
| `ToggleWifi`, `ToggleData`, `SetConnectionType` | `mobile: setConnectivity` (removed in 8.0) |
| Asserting a push was sent | Assert the app's reaction; delivery belongs to the provider's sandbox |
| Rebuilding the driver factory or page objects here | Reuse `ui-test-author/appium`; add only `NativeFeatures` |

## Rules

- **The OS surface is driven by device calls and `mobile:` commands, never a page-object selector.** Assert the effect on your screen.
- **Deep links are tested by routing**, and the https form proves the association.
- **Permissions are deterministic by default, real only when the flow is the test**, and the deny path is exercised.
- **Biometrics are injected on emulator or simulator only**; both approve and reject are tested, each with its own intent method (`ApproveFingerprint`, `RejectFingerprint`). Real-device injection belongs to `device-cloud`.
- **Lifecycle events assert restored state on a bounded wait.** No `Thread.Sleep` anywhere.
- **Clipboard content is base64** in both directions.
- Tests are `Should_X_When_Y`, assert with NUnit and a subject, and never use `try`/`catch`. App ids and device settings come from env through `Env`; no secrets in code.

## Cross-references

- **`qa/dotnet/skills/ui-test-author/appium`** — the foundation: `BaseAppiumPage`, `AppiumDriverFactory`, `BaseMobileTest`, gestures, WebView switching
- **`qa/dotnet/skills/device-cloud`** — where the tests run and how farm-side GPS, network and biometric are injected
- **`qa/dotnet/skills/data-driven-testing`** — a device, permission or locale matrix via `[TestCaseSource]`, one case per row
- **`qa/dotnet/skills/test-login-tokens`** — token auth, the boundary with biometric unlock
