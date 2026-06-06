---
name: qa-mobile-native-features-java
description: >-
  Use when the user needs to test the **device-native, OS-level capabilities** a mobile app uses that a normal
  Appium page-object UI test doesn't exercise — in Java 21 with `io.appium:java-client` 9.x + TestNG. Covers the
  trait that makes native-feature testing its own discipline: **a native feature lives OUTSIDE your app's own
  DOM/UI — it is an OS-level surface (a deep-link/intent, a runtime permission dialog, the biometric prompt, a push
  notification, the app's background/foreground lifecycle) — so you drive it through Appium's device/driver APIs and
  `executeScript("mobile: …")` commands, NEVER through page-object selectors on your app's screens** (the "find the
  element and tap it" reflex is wrong for an OS dialog the same way `assertEquals(status, 404)` is wrong for a gRPC
  call). Covers the four native surfaces, each tested differently — **deep / universal links** (launch via
  `mobile: deepLink` / a URL → assert the app *routed* to the right screen via your page object, not by tapping
  through the UI), **runtime permission dialogs** (the OS dialog is not your UI → `autoGrantPermissions` /
  `autoAcceptAlerts` caps for determinism, OR drive the real system dialog / Springboard when the *flow itself* is
  under test), **biometric auth** (`AndroidDriver.fingerPrint(int)` / iOS `mobile: sendBiometricMatch` — on the
  emulator/simulator injection APIs ONLY, never a real fingerprint), and **push notifications + backgrounding /
  resume** (`((InteractsWithApps) driver).runAppInBackground(Duration)` / `mobile: backgroundApp` → assert state
  restored on resume; `openNotifications` / `mobile: pushNotification`). Plus app lifecycle (`terminateApp` /
  `activateApp` / `queryAppState`), clipboard (`HasClipboard`), camera/file pickers (`mobile: pushFile`), device
  orientation (`SupportsRotation`), and the boundary with network conditioning. Triggers: "test our deep link opens
  the right screen in Appium Java", "handle the camera/location permission dialog", "test Face ID / fingerprint
  login on the simulator", "assert app state is restored after backgrounding", "test our push notification opens the
  app". Do NOT use for: driving YOUR app's own screens via page objects (use qa/java/skills/ui-test-author/appium — this
  skill builds ON it and adds the OS-surface layer), the real-device-cloud layer + GPS/network/biometric cap
  *injection plumbing* on BrowserStack/Sauce/Device Farm (use qa/java/skills/mobile-device-farm — #45 is *what* you assert,
  #40 is *where* it runs), asserting the network requests an app makes (use qa/java/skills/network-monitoring/*), the .NET stack
  (use qa/dotnet/skills/mobile-native-features), the TypeScript/WebdriverIO stack (use qa/typescript/skills/mobile-native-features),
  or token-based auth (use qa/java/skills/auth0-test-tokens).
---

# QA — Mobile Native Features (Java: Appium java-client + TestNG)

Scaffolds Appium tests for the **device-native, OS-level capabilities** a mobile app touches but a normal
page-object UI test never exercises — deep links, runtime permission dialogs, biometric auth, push notifications,
and the app's background/foreground lifecycle. It sits **directly on top of `qa/java/skills/ui-test-author/appium`**: the
`BaseAppiumPage` / `AppiumDriverFactory` / `SystemPropertyUtil` lifecycle and the page objects run **unchanged** —
this skill adds the layer that drives the OS surfaces *around* your screens.

> **The discipline this skill encodes** — four ideas that separate a correct native-feature test from a
> page-object reflex:
>
> 1. **A native feature lives OUTSIDE your app's DOM — it is an OS-level surface, so you drive it through the
>    device/driver API, not page-object selectors.** A runtime permission dialog, the biometric prompt, the
>    notification shade, the deep-link intent, the app's lifecycle state — none of these are elements on *your*
>    screens; they belong to Android/iOS. Reaching for `findByAccessibilityId(...)` on the OS permission dialog is
>    the native-testing analogue of looking for an HTTP status on a gRPC call: **the surface isn't yours.** You
>    drive it with `executeScript("mobile: …")`, `((InteractsWithApps) driver)`, `((HasClipboard) driver)`, the
>    biometric injection APIs, or `driver.switchTo().alert()` — and you assert the *effect* on your own screen via
>    the page object.
> 2. **A deep link is tested by ROUTING, not by tapping.** Launch the app via the link (`mobile: deepLink` / a URL)
>    and assert your page object shows the **right destination screen** — never reproduce the navigation by tapping
>    through the UI (that tests your taps, not the link). The link is the OS surface; the destination screen is
>    yours.
> 3. **Biometric and the permission dialog are injected/forced for determinism — and driven for real only when the
>    flow itself is under test.** A fingerprint/face match is **injected** on the emulator/simulator
>    (`fingerPrint(int)` / `mobile: sendBiometricMatch`) — *never* a real sensor, *never* a `Thread.sleep` waiting
>    for one. A permission grant is made **deterministic** with a capability (`autoGrantPermissions` /
>    `autoAcceptAlerts`) for the 90% of tests that just need the permission *out of the way* — and you drive the
>    real OS dialog only for the handful of tests where *the dialog flow itself* (deny → degraded UX, "ask every
>    time") is the thing under test.
> 4. **The app lifecycle is a first-class assertion target — assert state is restored on resume, never sleep
>    through it.** Backgrounding, resuming, terminating, a push arriving — each is a `mobile:` / `InteractsWithApps`
>    call, and each is followed by a **bounded wait on the app's observable reaction** (an explicit `WebDriverWait`
>    on the restored screen), never a fixed `Thread.sleep`. "Restored after resume" is an assertion you write, not a
>    pause you hope through.

## Decision matrix — native surface → test shape

| Native surface | Where it lives | Test shape (Java) |
|----------------|----------------|-------------------|
| **Deep / universal link** | OS intent / URL handler | `executeScript("mobile: deepLink", {url, package/bundleId})` → assert destination **page object** is loaded (routing, not taps) |
| **Runtime permission — out of the way** | OS permission dialog | Cap `autoGrantPermissions(true)` (Android) / `autoAcceptAlerts(true)` (iOS) → the dialog never appears; test the feature behind it |
| **Runtime permission — the flow IS the test** | OS permission dialog / Springboard | Drive the real dialog: Android `mobile: changePermissions` or the `permissioncontroller` buttons; iOS `driver.switchTo().alert().accept()` / `mobile: alert` → assert granted vs degraded UX |
| **Biometric — approved** | OS biometric prompt | Android `((AndroidDriver) driver).fingerPrint(1)`; iOS `mobile: sendBiometricMatch {type, match:true}` → assert the unlocked screen |
| **Biometric — rejected** | OS biometric prompt | same, `match:false` → assert the fallback (PIN screen / error), not a crash |
| **Push notification** | Notification shade / Center | Android `((AndroidDriver) driver).openNotifications()` + assert + tap; iOS sim `mobile: pushNotification` → open from Center → assert deep-linked screen |
| **Background → resume** | App lifecycle | `((InteractsWithApps) driver).runAppInBackground(Duration.ofSeconds(3))` → **wait** for the restored screen → assert state preserved |
| **Terminate → relaunch** | App lifecycle | `terminateApp(bundleId)` → `activateApp(bundleId)` → assert cold-vs-warm start state; `queryAppState` to verify |
| **Clipboard** | OS pasteboard | `((HasClipboard) driver).setClipboardText("…")` → paste in-app → assert; or read what the app copied |
| **Camera / file / photo picker** | OS picker (not your UI) | seed the file with `mobile: pushFile`, then mock/drive the picker — never automate the real camera |
| **Orientation** | OS rotation | `((SupportsRotation) driver).rotate(ScreenOrientation.LANDSCAPE)` → assert layout reflows |

## Stack

- Java 21, Gradle (Kotlin DSL)
- **Appium**: `io.appium:java-client` 9.x — `AndroidDriver` (UiAutomator2) / `IOSDriver` (XCUITest), and the
  capability interfaces it implements: `InteractsWithApps` (background/terminate/activate/queryAppState),
  `HasClipboard`, `SupportsRotation`, `PushesFiles`, plus `AndroidDriver.fingerPrint(int)` / `openNotifications()`
- **TestNG** (`org.testng:testng`) — the global default Java runner; **AssertJ** (`assertThat`) for fluent assertions
- **Allure TestNG** for reporting (attach a screenshot of the restored/deep-linked screen per native-flow result)
- Reuses `qa/java/skills/ui-test-author/appium`'s `AppiumDriverFactory` (one `ThreadLocal<AppiumDriver>` per thread),
  `BaseMobileTest`, page objects, and `SystemPropertyUtil` — **unchanged**
- App path / device caps / Appium server URL via `SystemPropertyUtil` — never hardcoded; no secrets in code
- Native-feature helpers under `src/test/java/.../support/native/`

```kotlin
// build.gradle.kts (excerpt) — same deps as the appium/java skill; nothing new for native features
dependencies {
    testImplementation("io.appium:java-client:9.3.0")   // brings InteractsWithApps, HasClipboard, SupportsRotation
    testImplementation("org.testng:testng:7.10.2")
    testImplementation("org.assertj:assertj-core:3.26.3")
    testImplementation("io.qameta.allure:allure-testng:2.29.0")
}
```

## When to use

- Verifying a **deep / universal link** opens the correct in-app screen
- Testing behavior **behind a runtime permission** (camera, location, notifications, contacts) — either with the
  dialog auto-handled, or with the **dialog flow itself** under test (grant vs deny)
- Testing **biometric** login / step-up on an emulator or simulator (approve and reject paths)
- Asserting **app state survives backgrounding / resume**, a cold relaunch, or a push tap
- Driving **clipboard**, a **camera/file/photo picker**, or **orientation** changes the app reacts to

## When NOT to use

- Driving **your app's own screens** via page objects → `qa/java/skills/ui-test-author/appium` (this skill builds **on** it)
- The **real-device-cloud** layer (BrowserStack/Sauce/Device Farm) + GPS/network/biometric **cap-injection plumbing**
  → `qa/java/skills/mobile-device-farm` (#40 is *where* the test runs + how caps are injected on a farm; #45 is *what* you
  assert on those caps — they compose: run #45's biometric/permission tests on #40's real-device cloud)
- Asserting the **network requests** an app makes → `qa/java/skills/network-monitoring/*` (draw the line: #45 = the app's
  *reaction* to airplane mode / a permission; network-monitoring = asserting the requests)
- The .NET / TypeScript native-feature stacks → `qa/{dotnet,typescript}/skills/mobile-native-features`
- **Token-based** auth → `qa/java/skills/auth0-test-tokens` (biometric *unlock* vs token *auth* are different surfaces)

---

## The foundation — page objects + driver lifecycle run unchanged

Every test here extends `qa/java/skills/ui-test-author/appium`'s `BaseMobileTest` and uses its `AppiumDriverFactory`. The
page objects (`LoginPage`, `DashboardPage`, …) drive **your** screens exactly as before. This skill adds a thin
`NativeFeatures` helper that owns the **OS-surface** calls, so a test reads as: *drive the OS surface → assert the
effect on a page object.* The native call is the only new vocabulary; the assertion is still a page object.

```java
// src/test/java/.../support/native/NativeFeatures.java
package support.nativefeatures;

import io.appium.java_client.AppiumDriver;
import io.appium.java_client.HasClipboard;
import io.appium.java_client.InteractsWithApps;
import io.appium.java_client.android.AndroidDriver;
import org.openqa.selenium.ScreenOrientation;
import io.appium.java_client.remote.SupportsRotation;

import java.time.Duration;
import java.util.Map;

/**
 * Owns the OS-level surfaces around the app. Every method drives a device/driver API or a `mobile:` command —
 * NEVER a page-object selector. The CALLER asserts the effect on a page object afterwards.
 */
public final class NativeFeatures {
    private final AppiumDriver driver;

    public NativeFeatures(AppiumDriver driver) { this.driver = driver; }

    // --- 1. Deep links: launch via the OS, assert routing on a page object ---
    public void openDeepLink(String url, String appIdentifier) {
        // UiAutomator2: {url, package}; XCUITest: {url, bundleId} — see the per-platform helpers below.
        driver.executeScript("mobile: deepLink", Map.of("url", url, "package", appIdentifier));
    }

    // --- 3. Biometric: inject a match/no-match — emulator/simulator only, never a real sensor ---
    public void approveFingerprint(int fingerId) {
        ((AndroidDriver) driver).fingerPrint(fingerId);   // enrolled finger id on the emulator
    }

    public void sendIosBiometric(String type, boolean match) {
        driver.executeScript("mobile: sendBiometricMatch", Map.of("type", type, "match", match)); // type: touchId | faceId
    }

    // --- 4. Lifecycle: background/terminate/activate — each followed by a bounded wait in the test ---
    public void backgroundFor(Duration duration) {
        ((InteractsWithApps) driver).runAppInBackground(duration);   // -1 / negative = indefinitely; activate to return
    }

    public void terminate(String bundleOrPackage) { ((InteractsWithApps) driver).terminateApp(bundleOrPackage); }
    public void activate(String bundleOrPackage)  { ((InteractsWithApps) driver).activateApp(bundleOrPackage); }

    // --- clipboard / orientation: OS surfaces the app reacts to ---
    public void setClipboard(String text) { ((HasClipboard) driver).setClipboardText(text); }
    public String getClipboard()          { return ((HasClipboard) driver).getClipboardText(); }
    public void rotate(ScreenOrientation o) { ((SupportsRotation) driver).rotate(o); }
}
```

---

## 1. Deep / universal links — test the routing, not the taps (idea #2)

A deep link's contract is: *given this URL, the app opens this screen.* So launch the app **via the link** and
assert your page object shows the destination — never reproduce the navigation by tapping through the UI. The link
is the OS surface (`mobile: deepLink` builds the intent / opens the URL); the destination is your screen.

```java
// Android (UiAutomator2): mobile: deepLink {url, package}
@Test
public void Should_open_order_details_When_deep_link_opened() {
    NativeFeatures os = new NativeFeatures(driver);

    os.openDeepLink("myapp://orders/A-1001", "com.example.shop");   // OS routes the intent — no taps

    OrderDetailsPage details = new OrderDetailsPage(driver);
    details.verifyPageLoaded();                                     // page object proves the ROUTE landed
    assertThat(details.orderId()).isEqualTo("A-1001");              // …and carried the param through
}
```

> **iOS differs by where the app runs.** On the **simulator**, `mobile: deepLink` takes `{url, bundleId}` and works
> for custom-scheme and Universal Links. On a **real iOS device** you cannot just hand the URL to the app — open it
> through **Safari** (`driver.get(url)` in a Safari session, then tap "Open") because a custom scheme has to be
> resolved by the OS. Android `mobile: deepLink` (an `am start -d <url>`) is uniform across emulator and real device.
> **Universal Links vs custom-scheme deep links:** a Universal/App Link is an `https://` URL the OS associates with
> the app (verified via `apple-app-site-association` / Android `assetlinks.json`); a custom-scheme link
> (`myapp://`) is app-private. Test the **https** form for Universal Links so you also prove the association
> resolved — a custom scheme bypasses it.

---

## 2. Runtime permission dialogs — deterministic by default, driven only when the flow is the test (idea #3)

The OS permission dialog is **not your UI** — it belongs to the system, its selectors differ per OS version, and
it pops up nondeterministically. So there are two modes, and picking the right one is the whole skill:

**Mode A — get the dialog out of the way (the 90% case).** Most tests want to test *the feature behind* a
permission, not the dialog. Grant it deterministically with a capability so the dialog never appears:

```java
// Android: grant all manifest permissions on install — the dialog never shows
UiAutomator2Options android = new UiAutomator2Options().autoGrantPermissions(true);

// iOS: auto-accept any system alert that appears (or autoDismissAlerts to deny)
XCUITestOptions ios = new XCUITestOptions().autoAcceptAlerts(true);
```

> Android also has `mobile: changePermissions` / `mobile: getPermissions` to **set a specific permission state**
> before a flow (`granted` / `denied`) — sharper than the all-or-nothing cap when you want camera granted but
> location denied. Prefer it when the test needs a *specific* permission posture.

**Mode B — the dialog flow IS the test (the handful that matters).** When you're testing what happens on **deny**
(degraded UX, a "go to Settings" prompt) or the grant flow itself, you must drive the **real** OS dialog — and do
it through the OS surface, not a page object on your screens:

```java
// iOS: the system alert is reachable via the standard alert API or `mobile: alert`
@Test
public void Should_show_degraded_map_When_location_denied() {
    MapPage map = new MapPage(driver);
    map.tapUseMyLocation();                                  // triggers the OS permission dialog

    driver.switchTo().alert().dismiss();                     // DENY on the real OS dialog (not your UI)
    // or: driver.executeScript("mobile: alert", Map.of("action", "dismiss"));

    map.verifyManualLocationPromptShown();                   // assert the DEGRADED path your app renders
}
```

```java
// Android: the dialog is the permissioncontroller package; drive its real buttons when the flow is under test.
// (For determinism prefer the cap / mobile: changePermissions; only walk the buttons when testing the dialog UX.)
driver.findElement(io.appium.java_client.AppiumBy.id(
    "com.android.permissioncontroller:id/permission_deny_button")).click();
```

> **iOS Springboard nuance:** when a permission/system alert is at the foreground, the active app context is
> `com.apple.springboard`, not your app. The XCUITest alert API handles this for you; if you ever need to interact
> with the dialog directly, `mobile: activateApp` Springboard first. Don't hardcode Springboard button coordinates.

---

## 3. Biometric auth — inject the match, assert the unlock (and the reject) (idea #3)

A fingerprint/Face ID match is **injected** on the emulator/simulator — there is no real sensor in CI, and a
`Thread.sleep` waiting for a human finger is banned and pointless. Enroll biometrics on the device, trigger the
prompt from your screen, inject the match, then assert the unlocked screen. Always test **both** the approved and
the rejected path.

```java
// Android: emulator must have a fingerprint enrolled; AndroidDriver.fingerPrint(id) injects a touch
@Test
public void Should_reach_dashboard_When_fingerprint_approved() {
    LoginPage login = new LoginPage(driver);
    login.tapBiometricSignIn();                 // YOUR screen triggers the OS biometric prompt

    new NativeFeatures(driver).approveFingerprint(1);   // inject a MATCH for enrolled finger id 1

    DashboardPage dashboard = login.awaitDashboard();   // explicit wait inside the page object — no sleep
    assertThat(dashboard.isLoaded()).isTrue();
}

@Test
public void Should_show_pin_fallback_When_fingerprint_rejected() {
    LoginPage login = new LoginPage(driver);
    login.tapBiometricSignIn();

    // a non-enrolled finger id injects a NO-MATCH; assert the fallback, not a crash
    new NativeFeatures(driver).approveFingerprint(99);

    assertThat(login.isPinFallbackShown()).isTrue();
}
```

```java
// iOS: enroll once, then send a match/no-match. Requires the sim to allow biometric enrollment.
// XCUITestOptions().allowEnrollBiometrics(true) at session start; then:
driver.executeScript("mobile: enrollBiometric", Map.of("isEnabled", true));
new NativeFeatures(driver).sendIosBiometric("faceId", true);    // match
// reject path: sendIosBiometric("faceId", false) → assert the passcode fallback screen
```

> **Real-device biometric is a farm concern, not this skill's.** On a real device you can't inject a sensor read
> locally — that's BrowserStack/Sauce sensor instrumentation (`enableBiometric` + `browserstack_executor
> performBiometric`), which `qa/java/skills/mobile-device-farm` (#40) owns. They **compose**: write the approve/reject
> *assertions* here, run them on the farm's injected biometric there. Never wire a real fingerprint into a test.

---

## 4. Push notifications + backgrounding / resume — assert state, never sleep through it (idea #4)

**App lifecycle.** Backgrounding and resuming is a real user behavior that breaks fragile apps (lost form state,
re-auth loops). Drive it with `InteractsWithApps`, then **wait on the restored screen** — a bounded
`WebDriverWait`, never a `Thread.sleep` guessing how long the OS takes.

```java
@Test
public void Should_preserve_cart_When_app_backgrounded_and_resumed() {
    CartPage cart = new CartPage(driver);
    cart.addItem("SKU-42");
    assertThat(cart.itemCount()).isEqualTo(1);

    NativeFeatures os = new NativeFeatures(driver);
    os.backgroundFor(java.time.Duration.ofSeconds(3));   // home → wait → return to foreground

    cart.verifyPageLoaded();                              // explicit wait on the restored screen (no sleep)
    assertThat(cart.itemCount()).isEqualTo(1);            // STATE survived the lifecycle event
}
```

```java
// Cold relaunch: terminate then activate; queryAppState confirms the transition deterministically
@Test
public void Should_require_login_When_app_terminated_and_relaunched() {
    String bundle = SystemPropertyUtil.getAppBundleId();
    NativeFeatures os = new NativeFeatures(driver);

    os.terminate(bundle);
    assertThat(((io.appium.java_client.InteractsWithApps) driver).queryAppState(bundle))
        .isEqualTo(io.appium.java_client.appmanagement.ApplicationState.NOT_RUNNING);

    os.activate(bundle);                                  // cold start
    LoginPage login = new LoginPage(driver);
    login.verifyPageLoaded();                             // session did NOT survive a cold start — by design
}
```

**Push notifications.** Open the OS notification surface — *not* your app's UI — assert the notification, then tap
it and assert the deep-linked screen (this composes with idea #2's routing assertion).

```java
// Android: open the notification shade via the driver, assert + tap the notification
@Test
public void Should_open_message_When_push_tapped() {
    ((io.appium.java_client.android.AndroidDriver) driver).openNotifications();

    org.openqa.selenium.WebElement push = new org.openqa.selenium.support.ui.WebDriverWait(
            driver, java.time.Duration.ofSeconds(10))
        .until(org.openqa.selenium.support.ui.ExpectedConditions.visibilityOfElementLocated(
            io.appium.java_client.AppiumBy.androidUIAutomator(
                "new UiSelector().textContains(\"New message from\")")));
    push.click();

    new MessageThreadPage(driver).verifyPageLoaded();     // the push routed into the right screen
}
```

> **iOS push on the simulator** is simulated with `mobile: pushNotification` (wraps `simctl push`) carrying an APNs
> payload; then open **Notification Center** and tap it. Asserting the *server actually sent* a push is a backend
> concern (your push provider's sandbox), not Appium's — this skill asserts the **app's reaction** to a push, the
> same boundary as `qa/java/skills/network-monitoring/*` for requests.

---

## Clipboard, pickers, orientation — the smaller OS surfaces

```java
// Clipboard: seed the OS pasteboard, paste in-app, assert; or read what the app copied
NativeFeatures os = new NativeFeatures(driver);
os.setClipboard("PROMO2026");
sharePage.tapPasteCode();
assertThat(checkoutPage.promoField()).isEqualTo("PROMO2026");

// Orientation: the app should reflow, not crash
os.rotate(org.openqa.selenium.ScreenOrientation.LANDSCAPE);
assertThat(galleryPage.columnsVisible()).isEqualTo(3);   // layout reacts to the OS rotation
```

> **Camera / photo / file pickers are an OS surface you don't automate directly.** You can't drive the real camera
> in CI. Seed the file the picker will return with `mobile: pushFile` (push an image to the device), then either
> mock the picker or select the seeded file from the gallery picker — and assert your app handled the result. Never
> try to "take a photo." For pure file *upload* flows, `((PushesFiles) driver).pushFile(remotePath, bytes)`.

---

## Anti-patterns

| Smell | Why it's wrong | Do instead |
|---|---|---|
| `findByAccessibilityId(...)` on the OS permission/biometric dialog | The dialog is the OS's UI, selectors differ per OS version, and it's nondeterministic | Drive it via the cap (`autoGrantPermissions`/`autoAcceptAlerts`), `mobile: changePermissions`, or `driver.switchTo().alert()` |
| Testing a deep link by **tapping through** the UI to the screen | Tests your taps, not the link's routing | `mobile: deepLink` / launch the URL → assert the destination **page object** |
| `Thread.sleep` after backgrounding / a biometric injection / a push | Banned by CLAUDE.md; the OS reacts at its own pace | `WebDriverWait` on the restored / unlocked / deep-linked screen |
| A **real fingerprint / camera** in the test | Impossible in CI, flaky, and unsafe | Inject biometric (`fingerPrint`/`sendBiometricMatch`); seed picker files with `mobile: pushFile` |
| Only testing the **approve** biometric path | Reject (fallback to PIN) is where apps crash | Test both `match:true` and `match:false`/non-enrolled id |
| Auto-granting permissions for **every** test, including the deny-UX test | The deny path never gets exercised | Mode A (cap) for feature tests; Mode B (drive the real dialog) for the flow-under-test |
| Hardcoding Springboard / `permissioncontroller` button coordinates | OS-version-fragile | Use the XCUITest alert API / stable resource-ids; activate Springboard via `mobile: activateApp` |
| Asserting a push was **sent** via Appium | That's a backend/push-provider concern | Assert the app's **reaction** (shade → tap → screen); push *sending* → provider sandbox |
| Re-deriving the driver factory / page objects here | Duplicates `appium/java`, drifts | Reuse `BaseMobileTest` + page objects unchanged; add only `NativeFeatures` |

## Examples

**End-to-end: a deep link proves the routing discipline.** A page-object author writes a test that taps
Home → Orders → search → row to reach order detail. The native-correct version launches
`myapp://orders/A-1001` and asserts `OrderDetailsPage` loaded with the right id — it proves the **link routes**,
which the tap-through test never does. Same destination screen, two completely different things proven: the OS
surface (the link) vs your in-app navigation.

**Composing with `mobile-device-farm` (#40).** This skill writes the *assertions* — "approved fingerprint reaches
the dashboard", "denied location degrades gracefully". #40 owns *where they run and how the cap is injected* on a
real-device cloud (`enableBiometric` + `performBiometric`, `gpsLocation`, `networkProfile`). They compose: the
biometric reject test you write here runs on the farm's injected sensor there. The boundary mirrors gRPC's "assert
the typed message" vs Testcontainers' "stand the service up" — *what you assert* vs *where it runs*.

## Rules (hard constraints)

- **The OS surface is driven by the device/driver API, never a page-object selector.** Permission dialogs,
  biometric prompts, the notification shade, deep-link intents, lifecycle state → `mobile: …` / `InteractsWithApps`
  / `HasClipboard` / `driver.switchTo().alert()`. Assert the **effect** on your screen via the page object.
- **Deep links are tested by routing.** Launch via `mobile: deepLink` / the URL and assert the destination page
  object — never reproduce the navigation by tapping. Test the **https** Universal/App Link form so the association
  is proven, not just a custom scheme.
- **Permissions: deterministic by default, real only when the flow is the test.** Use `autoGrantPermissions` /
  `autoAcceptAlerts` / `mobile: changePermissions` for feature tests; drive the **real** OS dialog only when the
  grant/deny flow itself is under test, and exercise the **deny** path.
- **Biometric is injected on emulator/simulator only** (`fingerPrint(int)` / `mobile: sendBiometricMatch`), never a
  real sensor; test **both** approve and reject. Real-device biometric injection → `qa/java/skills/mobile-device-farm`.
- **Lifecycle events assert restored state on a bounded wait.** `runAppInBackground` / `terminateApp` /
  `activateApp` / `queryAppState`, each followed by a `WebDriverWait` on the observable result. **No `Thread.sleep`**
  anywhere — including for OS animations, dialog appearance, or push delivery.
- **Push tests assert the app's reaction, not the send.** Open the shade/Center (`openNotifications` /
  `mobile: pushNotification`), assert, tap, assert the routed screen. Push *delivery* is a provider concern.
- **Reuse `appium/java` unchanged** — `BaseMobileTest`, `AppiumDriverFactory`, page objects, `SystemPropertyUtil`.
  Add only `NativeFeatures`. App ids / device caps / server URL via `SystemPropertyUtil`; no secrets in code.

## Cross-references

- **`qa/java/skills/ui-test-author/appium`** — the **foundation this skill builds on**: `BaseAppiumPage` /
  `AppiumDriverFactory` / `BaseMobileTest` / `SystemPropertyUtil`, the capability/`mobile:`-command idioms, explicit
  waits, native↔WEBVIEW context switching. The page objects + driver lifecycle run **unchanged**; #45 adds the
  OS-surface layer. Mirror its locator/wait idioms exactly.
- **`qa/java/skills/mobile-device-farm`** (#40) — the **real-device-cloud layer** + GPS/network/biometric **cap-injection
  plumbing**. #40 = *where* the test runs + *how* the cap is injected; #45 = *what* you assert on those caps. They
  compose (run #45's biometric/permission tests on #40's farm). Don't duplicate the farm wiring.
- **`qa/typescript/skills/mobile-native-features`** + **`qa/dotnet/skills/mobile-native-features`** — the sibling stacks
  (WebdriverIO + `driver.execute('mobile: …')` · Appium .NET + `driver.ExecuteScript("mobile: …")`); same four
  ideas, different client idioms. Structure ported, not redesigned.
- **`qa/java/skills/network-monitoring/*`** — the **boundary** on network conditioning/requests: #45 tests the app's *reaction*
  to airplane mode / a network flip; network-monitoring asserts the *requests*.
- **`qa/java/skills/data-driven-testing`** (#39) — drive a **device / permission / locale matrix** via a `@DataProvider`
  (one independent named case per row); this skill supplies the rows, that one the data-driven discipline.
- **`qa/java/skills/cloud-grid-config`** (#15) — the grid/session wiring the device session connects through (under #40).
- **`qa/java/skills/auth0-test-tokens`** (#16) — token-based auth, the boundary vs biometric *unlock*.
- **`qa/java/skills/allure-reporting`** — attach a screenshot of the deep-linked / restored / unlocked screen per
  native-flow result so a failure is one click from the replay.
