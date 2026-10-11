---
name: qa-mobile-native-features-java
description: Use when the user needs to test the **device-native, OS-level capabilities** a mobile app uses that a normal Appium page-object UI test doesn't exercise. Triggers: "test our deep link opens the right screen in Appium Java", "handle the camera/location permission dialog", "test Face ID / fingerprint login on the simulator". Not for device-cloud wiring (`qa-device-cloud-java`) or ordinary screen flows (`qa-ui-test-writer-appium-java`).
---

# QA — Mobile Native Features (Java: java-client 11 + Appium 3 + TestNG)

Appium tests for the **OS-level capabilities** a mobile app touches but a page-object UI test never exercises: deep links, runtime permission dialogs, biometrics, push notifications, the app lifecycle, the clipboard, orientation. It sits on `qa/java/skills/ui-test-author/appium`: `BaseAppiumPage`, `AppiumDriverFactory`, `BaseMobileTest` and the page objects run **unchanged**. This skill adds the layer that drives the OS surfaces *around* your screens.

> **Four ideas separate a native-feature test from a page-object reflex:**
>
> 1. **A native feature lives outside your app's element tree.** A permission dialog, the biometric prompt, the notification shade, a deep-link intent and the lifecycle state belong to Android or iOS. Drive them with `mobile:` extensions and the driver's device commands, then assert the *effect* on your own screen through a page object.
> 2. **A deep link is tested by routing, not by tapping.** Launch through the link and assert the destination page. Tapping through the UI tests your taps.
> 3. **Biometrics and permissions are injected for determinism, and driven for real only when the flow is under test.** A fingerprint or face match is injected on the emulator or simulator, never a real sensor. A permission is pre-granted by capability for the tests that only need it out of the way; the real dialog is driven for the few tests about grant versus deny.
> 4. **The lifecycle is an assertion target.** Background, resume, terminate and a push arriving are each followed by a bounded wait on the app's reaction, never a sleep.

## Decision matrix — native surface → test shape

| Native surface | Test shape (java-client 11) |
|---|---|
| **Deep / universal link** | `mobile: deepLink` → assert the destination **page object** |
| **Permission — out of the way** | `UiAutomator2Options.setAutoGrantPermissions(true)` · `XCUITestOptions.setAutoAcceptAlerts(true)` |
| **Permission — a specific state** | Android `mobile: changePermissions` · iOS simulator `mobile: setPermission` |
| **Permission — the dialog is the test** | `driver.switchTo().alert()` (iOS) · the `permissioncontroller` buttons (Android) → assert granted versus degraded UX |
| **Biometric — approved / rejected** | Android `mobile: fingerprint` · iOS `mobile: sendBiometricMatch` → assert the unlocked screen, then the fallback |
| **Push** | Android `mobile: openNotifications` · iOS simulator `mobile: pushNotification` → open it → assert the routed screen |
| **Background → resume** | `mobile: backgroundApp` → wait on the restored screen |
| **Terminate → relaunch** | `terminateApp` → `activateApp` → `queryAppState` |
| **Geolocation** | Android `mobile: setGeolocation` · iOS `mobile: setSimulatedLocation` → assert the location-driven screen |
| **Clipboard** | `mobile: setClipboard` (base64) → paste → assert |
| **Camera / file picker** | seed the file with `pushFile`, drive the picker, never the real camera |
| **Orientation** | `rotate(ScreenOrientation.LANDSCAPE)` → assert the layout reflows |

## Stack

- Java 21, Gradle (Kotlin DSL); the pins (`io.appium:java-client` 11.0.0, `selenium-support` ≥ 4.50, TestNG, AssertJ, `allure-testng` 3.0.0) are the **Versions** table of `qa/java/skills/ui-test-author/appium/SKILL.md`. This skill adds no dependency; java-client 10.x is the supported lane and every helper below exists there
- **AssertJ** for every assertion outside Appium; failure evidence is `BaseMobileTest`, and this skill adds no second hook
- `WebDriverWait` and `ExpectedConditions` need `selenium-support`, which java-client 11 no longer pulls in
- Helpers live in `src/test/java/.../support/nativefeatures/` (the package is `support.nativefeatures`; `native` is a reserved word, so `support/native/` cannot be a package)
- The old location types `org.openqa.selenium.html5.Location` and `LocationContext` are gone (Selenium 4.35); geolocation is a `mobile:` command

Appium 3 removed the old `/appium/*` routes, and java-client 11's driver methods call only `mobile:` extensions. Where this skill calls `executeScript("mobile: …")` directly, that is the same command with no wrapper in between.

## When to use

- A **deep or universal link** must open the right screen
- Behavior **behind a runtime permission**, with the dialog handled or under test
- **Biometric** login or step-up on an emulator or simulator, approve and reject
- State that must survive **backgrounding**, a cold relaunch, or a push tap
- **Geolocation**, **clipboard**, **picker** or **orientation** behavior

## When NOT to use

- The app's own screens → `qa/java/skills/ui-test-author/appium`
- Real-device farm wiring and farm-side biometric/GPS injection → `qa/java/skills/device-cloud`
- The requests an app makes → `qa/java/skills/network-mocking/*`
- Token auth → `qa/java/skills/test-login-tokens`
- TypeScript / .NET → `qa/{typescript,dotnet}/skills/mobile-native-features`

## The helper

`NativeFeatures` owns every OS-surface call, including the ones that touch OS UI, so no test holds a raw `findElement` or a wait. A test reads: *drive the OS surface, assert the effect on a page object.* The identifier is a package on Android and a bundle id on iOS, so one private method picks the key.

```java
package support.nativefeatures;

import io.appium.java_client.AppiumBy;
import io.appium.java_client.AppiumDriver;
import io.appium.java_client.InteractsWithApps;
import io.appium.java_client.appmanagement.ApplicationState;
import io.appium.java_client.ios.IOSDriver;
import io.appium.java_client.remote.SupportsRotation;
import org.openqa.selenium.By;
import org.openqa.selenium.ScreenOrientation;
import org.openqa.selenium.support.ui.ExpectedConditions;
import org.openqa.selenium.support.ui.WebDriverWait;

import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.Base64;
import java.util.Map;

public final class NativeFeatures {
    private static final Duration TIMEOUT = Duration.ofSeconds(10);
    private static final int UNENROLLED_FINGERPRINT_ID = 99;
    private static final String PERMISSION_DENY_BUTTON_ID = "com.android.permissioncontroller:id/permission_deny_button";

    private final AppiumDriver driver;

    public NativeFeatures(AppiumDriver driver) {
        this.driver = driver;
    }

    public void openDeepLink(String url, String appIdentifier) {
        driver.executeScript("mobile: deepLink", Map.of("url", url, isIos() ? "bundleId" : "package", appIdentifier));
    }

    public void approveFingerprint(int fingerprintId) {
        driver.executeScript("mobile: fingerprint", Map.of("fingerprintId", fingerprintId));
    }

    public void rejectFingerprint() {
        approveFingerprint(UNENROLLED_FINGERPRINT_ID);
    }

    public void sendIosBiometric(String type, boolean match) {
        driver.executeScript("mobile: sendBiometricMatch", Map.of("type", type, "match", match));
    }

    public void backgroundFor(Duration duration) {
        driver.executeScript("mobile: backgroundApp", Map.of("seconds", duration.toSeconds()));
    }

    public void terminate(String appIdentifier) {
        ((InteractsWithApps) driver).terminateApp(appIdentifier);
    }

    public void activate(String appIdentifier) {
        ((InteractsWithApps) driver).activateApp(appIdentifier);
    }

    public ApplicationState appState(String appIdentifier) {
        return ((InteractsWithApps) driver).queryAppState(appIdentifier);
    }

    public void setAndroidLocation(double latitude, double longitude) {
        driver.executeScript("mobile: setGeolocation", Map.of("latitude", latitude, "longitude", longitude));
    }

    public void setIosLocation(double latitude, double longitude) {
        driver.executeScript("mobile: setSimulatedLocation", Map.of("latitude", latitude, "longitude", longitude));
    }

    public void setClipboard(String text) {
        String base64 = Base64.getEncoder().encodeToString(text.getBytes(StandardCharsets.UTF_8));
        driver.executeScript("mobile: setClipboard", Map.of("content", base64, "contentType", "plaintext"));
    }

    public String clipboard() {
        String base64 = (String) driver.executeScript("mobile: getClipboard", Map.of("contentType", "plaintext"));
        return new String(Base64.getDecoder().decode(base64), StandardCharsets.UTF_8);
    }

    public void dismissIosAlert() {
        driver.switchTo().alert().dismiss();
    }

    public void denyAndroidPermission() {
        new WebDriverWait(driver, TIMEOUT)
                .until(ExpectedConditions.elementToBeClickable(AppiumBy.id(PERMISSION_DENY_BUTTON_ID)))
                .click();
    }

    public void openAndroidNotification(String text) {
        driver.executeScript("mobile: openNotifications", Map.of());
        new WebDriverWait(driver, TIMEOUT)
                .until(ExpectedConditions.elementToBeClickable(By.xpath("//*[contains(@text, '" + text + "')]")))
                .click();
    }

    public void rotate(ScreenOrientation orientation) {
        ((SupportsRotation) driver).rotate(orientation);
    }

    private boolean isIos() {
        return driver instanceof IOSDriver;
    }
}
```

The clipboard travels as **base64** in both directions: a raw string is not a valid payload.

## 1. Deep and universal links — test the routing (idea 2)

`mobile: deepLink` builds the intent on Android and opens the URL on iOS. The test never taps.

```java
@Test
public void Should_OpenOrderDetails_When_OrderLinkIsOpened() {
    new NativeFeatures(driver).openDeepLink("myapp://orders/A-1001", "com.example.shop");

    OrderDetailsPage details = new OrderDetailsPage(driver);
    details.verifyPageLoaded();
    assertThat(details.orderNumber()).as("order shown by the deep link").isEqualTo("A-1001");
}
```

- On iOS, `mobile: deepLink` works on a simulator and on a real device from iOS 16.4 and Xcode 14.3; only below that does a real device need the link opened in Safari.
- A Universal or App Link is an `https://` URL the OS associates with the app (`apple-app-site-association`, `assetlinks.json`); a custom scheme (`myapp://`) is app-private. Test the **https** form to prove the association resolves.

## 2. Permission dialogs — deterministic by default (idea 3)

**Out of the way (most tests).** The capability is set where the session is built (`AppiumDriverFactory`): `setAutoGrantPermissions(true)` on `UiAutomator2Options`, `setAutoAcceptAlerts(true)` on `XCUITestOptions` (`setAutoDismissAlerts(true)` denies).

**A specific posture.** Android: `mobile: changePermissions` with `permissions`, `appPackage` and `action` `grant` or `revoke`, and `mobile: getPermissions`. iOS simulator: `mobile: setPermission` with `bundleId` and `access` such as `camera` → `yes`.

**The dialog is the test.** Drive the real OS dialog through `NativeFeatures`, then assert the degraded path your app renders:

```java
@Test
public void Should_ShowManualLocationPrompt_When_LocationIsDenied() {
    MapPage map = new MapPage(driver);
    map.tapUseMyLocation();

    new NativeFeatures(driver).dismissIosAlert();

    assertThat(map.isManualLocationPromptShown()).as("manual location prompt after a denied permission").isTrue();
}
```

On Android the dialog belongs to the `com.android.permissioncontroller` package, and `denyAndroidPermission()` waits for its button by resource id. Prefer the capability or `changePermissions`, and walk the buttons only when the dialog UX is under test. On iOS a foreground system alert makes the active app `com.apple.springboard`; the alert API handles that, so never hardcode button coordinates.

## 3. Biometrics — inject the match, assert the unlock and the reject (idea 3)

There is no sensor in CI. Enroll on the device, trigger the prompt from your screen, inject, assert. Test both paths.

```java
@Test
public void Should_ReachDashboard_When_FingerprintIsApproved() {
    LoginPage login = new LoginPage(driver);
    login.tapBiometricSignIn();

    new NativeFeatures(driver).approveFingerprint(1);

    assertThat(login.awaitDashboard().isLoaded()).as("dashboard after an approved fingerprint").isTrue();
}

@Test
public void Should_ShowPinFallback_When_FingerprintIsRejected() {
    LoginPage login = new LoginPage(driver);
    login.tapBiometricSignIn();

    new NativeFeatures(driver).rejectFingerprint();

    assertThat(login.isPinFallbackShown()).as("PIN fallback after a rejected fingerprint").isTrue();
}
```

On an iOS simulator, call `mobile: enrollBiometric` with `isEnabled` true once, then `sendIosBiometric("faceId", true)` or `false`. No capability enrolls biometrics.

A real device cannot take an injected read locally; BrowserStack and Sauce instrument the sensor, which `device-cloud` owns. Write the approve and reject assertions here and run them on the farm's injected biometric there.

## Deep-dive reference

`references/details.md` holds **4. Push notifications and backgrounding** — read it when the task touches them.

## Clipboard, pickers, orientation

```java
@Test
public void Should_FillPromoField_When_CodeIsPasted() {
    new NativeFeatures(driver).setClipboard("PROMO2026");

    sharePage.tapPasteCode();

    assertThat(checkoutPage.promoCode()).as("promo field after a paste").isEqualTo("PROMO2026");
}
```

A camera, photo or file picker is an OS surface you cannot drive in CI. Seed the file the picker returns with `((PushesFiles) driver).pushFile(remotePath, bytes)`, pick it from the gallery picker, and assert how your app handled it.

## Anti-patterns

| Smell | Do instead |
|---|---|
| A page-object finder on the OS permission or biometric dialog | The capability, `mobile: changePermissions`, or the alert API |
| Reaching a screen by tapping to test a deep link | `mobile: deepLink` → assert the destination page |
| `Thread.sleep` after a background, an injection or a push | `WebDriverWait` on the restored, unlocked or routed screen |
| A real fingerprint or camera | Inject the match; seed picker files with `pushFile` |
| Only the approve path | Test the reject path too; reject is where apps crash |
| Auto-granting permissions in every test | The capability for feature tests; the real dialog for the flow under test |
| Hardcoded Springboard or `permissioncontroller` coordinates | The alert API and stable resource ids |
| A raw `driver.findElement` or a wait inside a test body | An intent method on `NativeFeatures` |
| Asserting a push was sent | Assert the app's reaction; delivery belongs to the provider's sandbox |
| Rebuilding the driver factory or page objects here | Reuse `ui-test-author/appium`; add only `NativeFeatures` |

## Rules

- **The OS surface is driven by device commands and `mobile:` extensions, never a page-object selector.** Assert the effect on your screen.
- **Deep links are tested by routing**, and the https form proves the association.
- **Permissions are deterministic by default, real only when the flow is the test**, and the deny path is exercised.
- **Biometrics are injected on emulator or simulator only**; both approve and reject are tested, each with its own intent method (`approveFingerprint`, `rejectFingerprint`). Real-device injection belongs to `device-cloud`.
- **Lifecycle events assert restored state on a bounded wait.** No `Thread.sleep` anywhere.
- **Push tests assert the app's reaction**, not the send.
- **Clipboard content is base64** in both directions.
- Tests are `Should_X_When_Y`, assert with AssertJ and a subject (`.as(...)`), and never use `try`/`catch`. App ids and device settings come from env through `Env`; no secrets in code.

## Cross-references

- **`qa/java/skills/ui-test-author/appium`** — the foundation: `BaseAppiumPage`, `AppiumDriverFactory`, `BaseMobileTest`, gestures, WebView switching, the failure evidence
- **`qa/java/skills/device-cloud`** — where the tests run and how farm-side GPS, network and biometric are injected
- **`qa/java/skills/evidence-capture`** — what a failed native flow keeps
- **`qa/typescript/skills/mobile-native-features`**, **`qa/dotnet/skills/mobile-native-features`** — the sibling stacks
- **`qa/java/skills/network-mocking/*`** — the requests an app makes
- **`qa/java/skills/data-driven-testing`** — a device, permission or locale matrix, one case per row
- **`qa/java/skills/test-login-tokens`** — token auth, the boundary with biometric unlock
