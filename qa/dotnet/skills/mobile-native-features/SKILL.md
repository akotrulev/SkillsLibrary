---
name: qa-mobile-native-features-dotnet
description: Use when the user needs to test the **device-native, OS-level capabilities** a mobile app uses that a normal Appium page-object UI test doesn't exercise. Triggers: "test our deep link opens the right screen in Appium C#", "handle the camera/location permission dialog", "test Face ID / fingerprint login on the simulator". For end-to-end suite work prefer the phased agent `qa-mobile-dotnet` (or the matching slash command), which loads this skill inside its workflow; use this skill directly for a single targeted artifact.
---

# QA — Mobile Native Features (.NET: Appium.WebDriver + NUnit)

Scaffolds Appium tests for the **device-native, OS-level capabilities** a mobile app touches but a normal
page-object UI test never exercises — deep links, runtime permission dialogs, biometric auth, push notifications,
and the app's background/foreground lifecycle. It sits **directly on top of `qa/dotnet/skills/ui-test-author/appium`**: the
`BaseAppiumPage` / `AppiumDriverFactory` / `Env` lifecycle and the page objects run **unchanged** — this skill adds
the layer that drives the OS surfaces *around* your screens.

> **The discipline this skill encodes** — four ideas that separate a correct native-feature test from a
> page-object reflex:
>
> 1. **A native feature lives OUTSIDE your app's DOM — it is an OS-level surface, so you drive it through the
>    device/driver API, not page-object selectors.** A runtime permission dialog, the biometric prompt, the
>    notification shade, the deep-link intent, the app's lifecycle state — none of these are elements on *your*
>    screens; they belong to Android/iOS. Reaching for `FindByAccessibilityId(...)` on the OS permission dialog is
>    the native-testing analogue of looking for an HTTP status on a gRPC call: **the surface isn't yours.** You
>    drive it with `Driver.ExecuteScript("mobile: …")`, `Driver.BackgroundApp/TerminateApp/ActivateApp`, the
>    clipboard/biometric APIs, or `Driver.SwitchTo().Alert()` — and you assert the *effect* on your own screen via
>    the page object.
> 2. **A deep link is tested by ROUTING, not by tapping.** Launch the app via the link (`mobile: deepLink` / a URL)
>    and assert your page object shows the **right destination screen** — never reproduce the navigation by tapping
>    through the UI (that tests your taps, not the link). The link is the OS surface; the destination screen is
>    yours.
> 3. **Biometric and the permission dialog are injected/forced for determinism — and driven for real only when the
>    flow itself is under test.** A fingerprint/face match is **injected** on the emulator/simulator
>    (`FingerPrint(int)` / `mobile: sendBiometricMatch`) — *never* a real sensor, *never* a `Thread.Sleep` waiting
>    for one. A permission grant is made **deterministic** with a capability (`autoGrantPermissions` /
>    `autoAcceptAlerts`) for the 90% of tests that just need the permission *out of the way* — and you drive the
>    real OS dialog only for the handful of tests where *the dialog flow itself* (deny → degraded UX) is under test.
> 4. **The app lifecycle is a first-class assertion target — assert state is restored on resume, never sleep
>    through it.** Backgrounding, resuming, terminating, a push arriving — each is a `mobile:` / driver call, and
>    each is followed by a **bounded wait on the app's observable reaction** (an explicit `WebDriverWait` on the
>    restored screen), never a fixed `Thread.Sleep`. "Restored after resume" is an assertion you write, not a pause
>    you hope through.

## Decision matrix — native surface → test shape

| Native surface | Where it lives | Test shape (C#) |
|----------------|----------------|-----------------|
| **Deep / universal link** | OS intent / URL handler | `Driver.ExecuteScript("mobile: deepLink", {url, package/bundleId})` → assert destination **page object** is loaded (routing, not taps) |
| **Runtime permission — out of the way** | OS permission dialog | Cap `autoGrantPermissions=true` (Android) / `autoAcceptAlerts=true` (iOS) → the dialog never appears; test the feature behind it |
| **Runtime permission — the flow IS the test** | OS permission dialog / Springboard | Drive the real dialog: Android `mobile: changePermissions` or the `permissioncontroller` buttons; iOS `Driver.SwitchTo().Alert().Dismiss()` / `mobile: alert` → assert granted vs degraded UX |
| **Biometric — approved** | OS biometric prompt | Android `((AndroidDriver)Driver).FingerPrint(1)`; iOS `mobile: sendBiometricMatch {type, match:true}` → assert the unlocked screen |
| **Biometric — rejected** | OS biometric prompt | same, `match:false` → assert the fallback (PIN screen / error), not a crash |
| **Push notification** | Notification shade / Center | Android `((AndroidDriver)Driver).OpenNotifications()` + assert + tap; iOS sim `mobile: pushNotification` → open from Center → assert deep-linked screen |
| **Background → resume** | App lifecycle | `Driver.BackgroundApp(TimeSpan.FromSeconds(3))` → **wait** for the restored screen → assert state preserved |
| **Terminate → relaunch** | App lifecycle | `Driver.TerminateApp(bundleId)` → `Driver.ActivateApp(bundleId)` → assert cold-vs-warm start state; `GetAppState` to verify |
| **Clipboard** | OS pasteboard | `Driver.SetClipboardText("…", "plaintext")` → paste in-app → assert; or read what the app copied |
| **Camera / file / photo picker** | OS picker (not your UI) | seed the file with `PushFile`, then mock/drive the picker — never automate the real camera |
| **Orientation** | OS rotation | `Driver.Orientation = ScreenOrientation.Landscape` → assert layout reflows |

## Stack

- .NET 8, nullable reference types enabled
- **Appium .NET client** `Appium.WebDriver` 8.x (`OpenQA.Selenium.Appium`, `.Android`, `.iOS`, `.Enums`) on
  Selenium 4 — `AppiumDriver` exposes `BackgroundApp` / `TerminateApp` / `ActivateApp` / `GetAppState` /
  `SetClipboardText` / `GetClipboardText` / `Orientation` / `PushFile`; `AndroidDriver` adds `FingerPrint(int)` /
  `OpenNotifications()`
- **NUnit** (the global default .NET runner); fluent `Assert.That(...)`
- **Allure NUnit** for reporting (attach a screenshot of the restored/deep-linked screen per native-flow result)
- Reuses `qa/dotnet/skills/ui-test-author/appium`'s `AppiumDriverFactory`, `BaseMobileTest`, page objects, and `Env` —
  **unchanged**
- App path / device caps / Appium server URL via `Env` — never hardcoded; no secrets in code
- Native-feature helpers under `AppiumTests/Support/Native/`

```xml
<!-- AppiumTests.csproj (excerpt) — same deps as the appium/dotnet skill; nothing new for native features -->
<PackageReference Include="Appium.WebDriver" Version="8.0.0" />
<PackageReference Include="NUnit" Version="4.2.2" />
<PackageReference Include="Allure.NUnit" Version="2.12.1" />
```

## When to use

- Verifying a **deep / universal link** opens the correct in-app screen
- Testing behavior **behind a runtime permission** (camera, location, notifications, contacts) — either with the
  dialog auto-handled, or with the **dialog flow itself** under test (grant vs deny)
- Testing **biometric** login / step-up on an emulator or simulator (approve and reject paths)
- Asserting **app state survives backgrounding / resume**, a cold relaunch, or a push tap
- Driving **clipboard**, a **camera/file/photo picker**, or **orientation** changes the app reacts to

## When NOT to use

- Driving **your app's own screens** via page objects → `qa/dotnet/skills/ui-test-author/appium` (this skill builds **on** it)
- The **real-device-cloud** layer + GPS/network/biometric **cap-injection plumbing** → `qa/dotnet/skills/mobile-device-farm`
  (`mobile-device-farm` = *where* the test runs + how caps are injected on a farm; `mobile-native-features` = *what* you assert on those caps — they
  compose)
- Asserting the **network requests** an app makes → `qa/dotnet/skills/network-monitoring/*` (`mobile-native-features` = the app's *reaction* to airplane
  mode / a permission; network-monitoring = asserting the requests)
- The Java / TypeScript native-feature stacks → `qa/{java,typescript}/skills/mobile-native-features`
- **Token-based** auth → `qa/dotnet/skills/auth0-test-tokens` (biometric *unlock* vs token *auth* are different surfaces)

---

## The foundation — page objects + driver lifecycle run unchanged

Every test here extends `qa/dotnet/skills/ui-test-author/appium`'s `BaseMobileTest` and uses its `AppiumDriverFactory`. The
page objects (`LoginPage`, `DashboardPage`, …) drive **your** screens exactly as before. This skill adds a thin
`NativeFeatures` helper that owns the **OS-surface** calls, so a test reads as: *drive the OS surface → assert the
effect on a page object.* The native call is the only new vocabulary; the assertion is still a page object.

```csharp
// AppiumTests/Support/Native/NativeFeatures.cs
using OpenQA.Selenium;
using OpenQA.Selenium.Appium;
using OpenQA.Selenium.Appium.Android;

namespace AppiumTests.Support.Native;

/// <summary>
/// Owns the OS-level surfaces around the app. Every method drives a device/driver API or a `mobile:` command —
/// NEVER a page-object selector. The CALLER asserts the effect on a page object afterwards.
/// </summary>
public sealed class NativeFeatures(AppiumDriver driver)
{
    // --- 1. Deep links: launch via the OS, assert routing on a page object ---
    public void OpenDeepLink(string url, string appIdentifier) =>
        // UiAutomator2: {url, package}; XCUITest: {url, bundleId} — see the per-platform helpers below.
        driver.ExecuteScript("mobile: deepLink", new Dictionary<string, object>
        {
            ["url"] = url,
            ["package"] = appIdentifier,
        });

    // --- 3. Biometric: inject a match/no-match — emulator/simulator only, never a real sensor ---
    public void ApproveFingerprint(int fingerId) =>
        ((AndroidDriver)driver).FingerPrint(fingerId);   // enrolled finger id on the emulator

    public void SendIosBiometric(string type, bool match) =>
        driver.ExecuteScript("mobile: sendBiometricMatch", new Dictionary<string, object>
        {
            ["type"] = type,   // "touchId" | "faceId"
            ["match"] = match,
        });

    // --- 4. Lifecycle: background/terminate/activate — each followed by a bounded wait in the test ---
    public void BackgroundFor(TimeSpan duration) => driver.BackgroundApp(duration);
    public void Terminate(string bundleOrPackage) => driver.TerminateApp(bundleOrPackage);
    public void Activate(string bundleOrPackage)  => driver.ActivateApp(bundleOrPackage);

    // --- clipboard / orientation: OS surfaces the app reacts to ---
    public void SetClipboard(string text) => driver.SetClipboardText(text, "plaintext");
    public string GetClipboard()          => driver.GetClipboardText();
    public ScreenOrientation Orientation  { set => driver.Orientation = value; }
}
```

---

## 1. Deep / universal links — test the routing, not the taps (idea #2)

A deep link's contract is: *given this URL, the app opens this screen.* So launch the app **via the link** and
assert your page object shows the destination — never reproduce the navigation by tapping through the UI. The link
is the OS surface (`mobile: deepLink` builds the intent / opens the URL); the destination is your screen.

```csharp
// Android (UiAutomator2): mobile: deepLink {url, package}
[Test]
public void Should_OpenOrderDetails_When_DeepLinkOpened()
{
    var os = new NativeFeatures(Driver);

    os.OpenDeepLink("myapp://orders/A-1001", "com.example.shop");   // OS routes the intent — no taps

    var details = new OrderDetailsPage(Driver);
    details.VerifyPageLoaded();                                     // page object proves the ROUTE landed
    Assert.That(details.OrderId(), Is.EqualTo("A-1001"));           // …and carried the param through
}
```

> **iOS differs by where the app runs.** On the **simulator**, `mobile: deepLink` takes `{url, bundleId}` and works
> for custom-scheme and Universal Links. On a **real iOS device** you cannot just hand the URL to the app — open it
> through **Safari** (`Driver.Url = url` in a Safari session, then tap "Open") because a custom scheme has to be
> resolved by the OS. Android `mobile: deepLink` (an `am start -d <url>`) is uniform across emulator and real device.
> **Universal Links vs custom-scheme deep links:** a Universal/App Link is an `https://` URL the OS associates with
> the app; a custom-scheme link (`myapp://`) is app-private. Test the **https** form for Universal Links so you also
> prove the association resolved.

---

## 2. Runtime permission dialogs — deterministic by default, driven only when the flow is the test (idea #3)

The OS permission dialog is **not your UI** — it belongs to the system, its selectors differ per OS version, and
it pops up nondeterministically. So there are two modes, and picking the right one is the whole skill:

**Mode A — get the dialog out of the way (the 90% case).** Most tests want to test *the feature behind* a
permission, not the dialog. Grant it deterministically with a capability so the dialog never appears:

```csharp
// Android: grant all manifest permissions on install — the dialog never shows
android.AddAdditionalAppiumOption("autoGrantPermissions", true);

// iOS: auto-accept any system alert that appears (or autoDismissAlerts to deny)
ios.AddAdditionalAppiumOption("autoAcceptAlerts", true);
```

> Android also has `mobile: changePermissions` / `mobile: getPermissions` to **set a specific permission state**
> before a flow (`granted` / `denied`) — sharper than the all-or-nothing cap when you want camera granted but
> location denied. Prefer it when the test needs a *specific* permission posture.

**Mode B — the dialog flow IS the test (the handful that matters).** When you're testing what happens on **deny**
(degraded UX, a "go to Settings" prompt) or the grant flow itself, you must drive the **real** OS dialog — through
the OS surface, not a page object on your screens:

```csharp
// iOS: the system alert is reachable via the standard alert API or `mobile: alert`
[Test]
public void Should_ShowDegradedMap_When_LocationDenied()
{
    var map = new MapPage(Driver);
    map.TapUseMyLocation();                                  // triggers the OS permission dialog

    Driver.SwitchTo().Alert().Dismiss();                     // DENY on the real OS dialog (not your UI)
    // or: Driver.ExecuteScript("mobile: alert", new Dictionary<string, object> { ["action"] = "dismiss" });

    map.VerifyManualLocationPromptShown();                   // assert the DEGRADED path your app renders
}
```

```csharp
// Android: the dialog is the permissioncontroller package; drive its real buttons when the flow is under test.
// (For determinism prefer the cap / mobile: changePermissions; only walk the buttons when testing the dialog UX.)
Driver.FindElement(AppiumBy.Id("com.android.permissioncontroller:id/permission_deny_button")).Click();
```

> **iOS Springboard nuance:** when a permission/system alert is at the foreground, the active app context is
> `com.apple.springboard`, not your app. The XCUITest alert API handles this for you; if you ever need to interact
> with the dialog directly, `mobile: activateApp` Springboard first. Don't hardcode Springboard button coordinates.

---

## 3. Biometric auth — inject the match, assert the unlock (and the reject) (idea #3)

A fingerprint/Face ID match is **injected** on the emulator/simulator — there is no real sensor in CI, and a
`Thread.Sleep` waiting for a human finger is banned and pointless. Enroll biometrics on the device, trigger the
prompt from your screen, inject the match, then assert the unlocked screen. Always test **both** the approved and
the rejected path.

```csharp
// Android: emulator must have a fingerprint enrolled; AndroidDriver.FingerPrint(id) injects a touch
[Test]
public void Should_ReachDashboard_When_FingerprintApproved()
{
    var login = new LoginPage(Driver);
    login.TapBiometricSignIn();                 // YOUR screen triggers the OS biometric prompt

    new NativeFeatures(Driver).ApproveFingerprint(1);   // inject a MATCH for enrolled finger id 1

    var dashboard = login.AwaitDashboard();             // explicit wait inside the page object — no sleep
    Assert.That(dashboard.IsLoaded(), Is.True);
}

[Test]
public void Should_ShowPinFallback_When_FingerprintRejected()
{
    var login = new LoginPage(Driver);
    login.TapBiometricSignIn();

    // a non-enrolled finger id injects a NO-MATCH; assert the fallback, not a crash
    new NativeFeatures(Driver).ApproveFingerprint(99);

    Assert.That(login.IsPinFallbackShown(), Is.True);
}
```

```csharp
// iOS: enroll once, then send a match/no-match. Requires the sim to allow biometric enrollment.
// ios.AddAdditionalAppiumOption("allowEnrollBiometrics", true) at session start; then:
Driver.ExecuteScript("mobile: enrollBiometric", new Dictionary<string, object> { ["isEnabled"] = true });
new NativeFeatures(Driver).SendIosBiometric("faceId", true);    // match
// reject path: SendIosBiometric("faceId", false) → assert the passcode fallback screen
```

> **Real-device biometric is a farm concern, not this skill's.** On a real device you can't inject a sensor read
> locally — that's BrowserStack/Sauce sensor instrumentation (`enableBiometric` + `browserstack_executor
> performBiometric`), which `qa/dotnet/skills/mobile-device-farm` owns. They **compose**: write the approve/reject
> *assertions* here, run them on the farm's injected biometric there. Never wire a real fingerprint into a test.

---

## Deep-dive reference

These sections live in `references/details.md` — **read it when the task touches them**: **4. Push notifications + backgrounding / resume — assert state, never sleep through it (idea #4)**.

## Clipboard, pickers, orientation — the smaller OS surfaces

```csharp
// Clipboard: seed the OS pasteboard, paste in-app, assert; or read what the app copied
var os = new NativeFeatures(Driver);
os.SetClipboard("PROMO2026");
sharePage.TapPasteCode();
Assert.That(checkoutPage.PromoField(), Is.EqualTo("PROMO2026"));

// Orientation: the app should reflow, not crash
os.Orientation = ScreenOrientation.Landscape;
Assert.That(galleryPage.ColumnsVisible(), Is.EqualTo(3));   // layout reacts to the OS rotation
```

> **Camera / photo / file pickers are an OS surface you don't automate directly.** You can't drive the real camera
> in CI. Seed the file the picker will return with `Driver.PushFile(remotePath, bytes)`, then either mock the
> picker or select the seeded file from the gallery picker — and assert your app handled the result. Never try to
> "take a photo."

---

## Anti-patterns

| Smell | Why it's wrong | Do instead |
|---|---|---|
| `FindByAccessibilityId(...)` on the OS permission/biometric dialog | The dialog is the OS's UI, selectors differ per OS version, and it's nondeterministic | Drive it via the cap (`autoGrantPermissions`/`autoAcceptAlerts`), `mobile: changePermissions`, or `Driver.SwitchTo().Alert()` |
| Testing a deep link by **tapping through** the UI to the screen | Tests your taps, not the link's routing | `mobile: deepLink` / launch the URL → assert the destination **page object** |
| `Thread.Sleep` after backgrounding / a biometric injection / a push | Banned by CLAUDE.md; the OS reacts at its own pace | `WebDriverWait` on the restored / unlocked / deep-linked screen |
| A **real fingerprint / camera** in the test | Impossible in CI, flaky, and unsafe | Inject biometric (`FingerPrint`/`sendBiometricMatch`); seed picker files with `PushFile` |
| Only testing the **approve** biometric path | Reject (fallback to PIN) is where apps crash | Test both `match:true` and `match:false`/non-enrolled id |
| Auto-granting permissions for **every** test, including the deny-UX test | The deny path never gets exercised | Mode A (cap) for feature tests; Mode B (drive the real dialog) for the flow-under-test |
| Hardcoding Springboard / `permissioncontroller` button coordinates | OS-version-fragile | Use the XCUITest alert API / stable resource-ids; activate Springboard via `mobile: activateApp` |
| Asserting a push was **sent** via Appium | That's a backend/push-provider concern | Assert the app's **reaction** (shade → tap → screen); push *sending* → provider sandbox |
| Re-deriving the driver factory / page objects here | Duplicates `appium/dotnet`, drifts | Reuse `BaseMobileTest` + page objects unchanged; add only `NativeFeatures` |

## Examples

**End-to-end: a deep link proves the routing discipline.** A page-object author writes a test that taps
Home → Orders → search → row to reach order detail. The native-correct version launches
`myapp://orders/A-1001` and asserts `OrderDetailsPage` loaded with the right id — it proves the **link routes**,
which the tap-through test never does. Same destination screen, two completely different things proven: the OS
surface (the link) vs your in-app navigation.

**Composing with `mobile-device-farm`.** This skill writes the *assertions* — "approved fingerprint reaches
the dashboard", "denied location degrades gracefully". `mobile-device-farm` owns *where they run and how the cap is injected* on a
real-device cloud. They compose: the biometric reject test you write here runs on the farm's injected sensor there.
The boundary mirrors gRPC's "assert the typed message" vs Testcontainers' "stand the service up" — *what you assert*
vs *where it runs*.

## Rules (hard constraints)

- **The OS surface is driven by the device/driver API, never a page-object selector.** Permission dialogs,
  biometric prompts, the notification shade, deep-link intents, lifecycle state → `mobile: …` /
  `BackgroundApp`/`TerminateApp`/`ActivateApp` / `Driver.SwitchTo().Alert()`. Assert the **effect** on your screen
  via the page object.
- **Deep links are tested by routing.** Launch via `mobile: deepLink` / the URL and assert the destination page
  object — never reproduce the navigation by tapping. Test the **https** Universal/App Link form so the association
  is proven, not just a custom scheme.
- **Permissions: deterministic by default, real only when the flow is the test.** Use `autoGrantPermissions` /
  `autoAcceptAlerts` / `mobile: changePermissions` for feature tests; drive the **real** OS dialog only when the
  grant/deny flow itself is under test, and exercise the **deny** path.
- **Biometric is injected on emulator/simulator only** (`FingerPrint(int)` / `mobile: sendBiometricMatch`), never a
  real sensor; test **both** approve and reject. Real-device biometric injection → `qa/dotnet/skills/mobile-device-farm`.
- **Lifecycle events assert restored state on a bounded wait.** `BackgroundApp` / `TerminateApp` / `ActivateApp` /
  `GetAppState`, each followed by a `WebDriverWait` on the observable result. **No `Thread.Sleep`** anywhere —
  including for OS animations, dialog appearance, or push delivery.
- **Push tests assert the app's reaction, not the send.** Open the shade/Center (`OpenNotifications` /
  `mobile: pushNotification`), assert, tap, assert the routed screen. Push *delivery* is a provider concern.
- **Reuse `appium/dotnet` unchanged** — `BaseMobileTest`, `AppiumDriverFactory`, page objects, `Env`. Add only
  `NativeFeatures`. App ids / device caps / server URL via `Env`; no secrets in code.

## Cross-references

- **`qa/dotnet/skills/ui-test-author/appium`** — the **foundation this skill builds on**: `BaseAppiumPage` /
  `AppiumDriverFactory` / `BaseMobileTest` / `Env`, the `AppiumOptions` capability idioms, `ExecuteScript("mobile:
  …")` gesture commands, explicit waits, native↔WEBVIEW context switching. The page objects + driver lifecycle run
  **unchanged**; `mobile-native-features` adds the OS-surface layer. Mirror its locator/wait idioms exactly.
- **`qa/dotnet/skills/mobile-device-farm`** — the **real-device-cloud layer** + GPS/network/biometric **cap-injection
  plumbing**. `mobile-device-farm` = *where* the test runs + *how* the cap is injected; `mobile-native-features` = *what* you assert on those caps. They
  compose. Don't duplicate the farm wiring.
- **`qa/java/skills/mobile-native-features`** + **`qa/typescript/skills/mobile-native-features`** — the sibling stacks (java-client
  `InteractsWithApps`/`fingerPrint` · WebdriverIO `driver.execute('mobile: …')`); same four ideas, different client
  idioms. Structure ported, not redesigned.
- **`qa/dotnet/skills/network-monitoring/*`** — the **boundary** on network conditioning/requests: `mobile-native-features` tests the app's *reaction*;
  network-monitoring asserts the *requests*.
- **`qa/dotnet/skills/data-driven-testing`** — drive a **device / permission / locale matrix** via `[TestCaseSource]`
  (one independent named case per row); this skill supplies the rows, that one the data-driven discipline.
- **`qa/dotnet/skills/cloud-grid-config`** — the grid/session wiring the device session connects through (under `mobile-device-farm`).
- **`qa/dotnet/skills/auth0-test-tokens`** — token-based auth, the boundary vs biometric *unlock*.
- **`qa/reporting/dotnet/skills/allure-reporting`** — attach a screenshot of the deep-linked / restored / unlocked screen per
  native-flow result.
