---
name: mobile-native-features
description: Use when the user needs to test the **device-native, OS-level capabilities** a mobile app uses that a normal Appium page-object UI test doesn't exercise. Triggers: "test our deep link opens the right screen in WebdriverIO", "handle the camera/location permission dialog", "test Face ID / fingerprint login on the simulator". Not for device-cloud wiring (`qa-typescript:device-cloud`) or ordinary screen flows (`qa-typescript:ui-tests-appium`).
---

# QA — Mobile Native Features (TypeScript: WebdriverIO 10 + Appium 3)

Appium tests for the **OS-level capabilities** a mobile app touches but a page-object UI test never exercises: deep links, runtime permission dialogs, biometrics, push notifications, the app lifecycle, the clipboard, orientation. It sits on `qa/typescript/skills/ui-test-author/appium`: `BasePage`, the page objects and the `wdio.conf.ts` session run **unchanged**. This skill adds the layer that drives the OS surfaces *around* your screens.

> **Four ideas separate a native-feature test from a page-object reflex:**
>
> 1. **A native feature lives outside your app's element tree.** A permission dialog, the biometric prompt, the notification shade, a deep-link intent and the lifecycle state belong to Android or iOS. Drive them with `mobile:` extensions and the WDIO device commands, then assert the *effect* on your own screen through a page object.
> 2. **A deep link is tested by routing, not by tapping.** Launch through the link and assert the destination page. Tapping through the UI tests your taps.
> 3. **Biometrics and permissions are injected for determinism, and driven for real only when the flow is under test.** A fingerprint or face match is injected on the emulator or simulator, never a real sensor. A permission is pre-granted by capability for the tests that only need it out of the way; the real dialog is driven for the few tests about grant versus deny.
> 4. **The lifecycle is an assertion target.** Background, resume, terminate and a push arriving are each followed by a bounded wait on the app's reaction, never a pause.

## Decision matrix — native surface → test shape

| Native surface | Test shape (WebdriverIO 10) |
|---|---|
| **Deep / universal link** | `browser.deepLink(url, appIdentifier)` → assert the destination **page object** |
| **Permission — out of the way** | `'appium:autoGrantPermissions': true` (Android) · `'appium:autoAcceptAlerts': true` (iOS) |
| **Permission — a specific state** | Android `mobile: changePermissions` · iOS simulator `mobile: setPermission` |
| **Permission — the dialog is the test** | `browser.acceptAlert()` / `browser.dismissAlert()` (iOS) · the `permissioncontroller` buttons (Android) → assert granted versus degraded UX |
| **Biometric — approved / rejected** | Android `browser.fingerPrint(id)` · iOS `mobile: sendBiometricMatch { type, match }` → assert the unlocked screen, then the fallback |
| **Push** | Android `browser.openNotifications()` · iOS simulator `mobile: pushNotification` → open it → assert the routed screen |
| **Background → resume** | `browser.background(3)` → wait on the restored screen |
| **Terminate → relaunch** | `mobile: terminateApp` → `mobile: activateApp` → `mobile: queryAppState` |
| **Clipboard** | `browser.setClipboard(base64, 'plaintext')` → paste → assert |
| **Camera / file picker** | seed the file with `browser.pushFile`, drive the picker, never the real camera |
| **Orientation** | `browser.setOrientation('LANDSCAPE')` → assert the layout reflows |

## Stack

- Node 24, TypeScript `strict: true`; **WebdriverIO 10.0.2** with `@wdio/appium-service` on **Appium 3.8.0** (Appium 2 with WDIO 9 is the supported lane; the helpers below exist in both)
- **Mocha** with `@wdio/mocha-framework`; `expect` from `@wdio/globals`
- `@wdio/allure-reporter` — failure evidence is `ui-test-author/appium`'s `BaseTest.ts`; this skill adds no second hook
- Reuses `BasePage`, the page objects and `wdio.conf.ts` of `qa/typescript/skills/ui-test-author/appium` unchanged
- App path and device from env in `wdio.conf.ts`; helpers under `src/support/nativefeatures/`

WDIO 10 sends every one of these helpers through a `mobile:` extension, because Appium 3 removed the old `/appium/*` routes. Never hand-roll an HTTP call to one.

## When to use

- A **deep or universal link** must open the right screen
- Behavior **behind a runtime permission**, with the dialog handled or under test
- **Biometric** login or step-up on an emulator or simulator, approve and reject
- State that must survive **backgrounding**, a cold relaunch, or a push tap
- **Clipboard**, **picker** or **orientation** behavior

## When NOT to use

- The app's own screens → `qa/typescript/skills/ui-test-author/appium`
- Real-device farm wiring and farm-side biometric/GPS injection → `qa/typescript/skills/device-cloud`
- The requests an app makes → `qa/typescript/skills/network-mocking/*`
- Token auth → `qa/typescript/skills/test-login-tokens`
- Java / .NET → `qa/{java,dotnet}/skills/mobile-native-features`

## The helper

`NativeFeatures` owns every OS-surface call. A test reads: *drive the OS surface, assert the effect on a page object.* The id argument is a package on Android and a bundle id on iOS, so one private method builds the arguments.

```ts
import { browser } from '@wdio/globals';

const UNENROLLED_FINGERPRINT_ID = 99;

export class NativeFeatures {
  async openDeepLink(url: string, appIdentifier: string): Promise<void> {
    await browser.deepLink(url, appIdentifier);
  }

  async approveFingerprint(fingerprintId: number): Promise<void> {
    await browser.fingerPrint(fingerprintId);
  }

  async rejectFingerprint(): Promise<void> {
    await browser.fingerPrint(UNENROLLED_FINGERPRINT_ID);
  }

  async sendIosBiometric(type: 'touchId' | 'faceId', match: boolean): Promise<void> {
    await browser.execute('mobile: sendBiometricMatch', { type, match });
  }

  async backgroundFor(seconds: number): Promise<void> {
    await browser.background(seconds);
  }

  async terminate(appIdentifier: string): Promise<void> {
    await browser.execute('mobile: terminateApp', this.appArguments(appIdentifier));
  }

  async activate(appIdentifier: string): Promise<void> {
    await browser.execute('mobile: activateApp', this.appArguments(appIdentifier));
  }

  async appState(appIdentifier: string): Promise<number> {
    return browser.execute<number, [Record<string, string>]>('mobile: queryAppState', this.appArguments(appIdentifier));
  }

  async setClipboard(text: string): Promise<void> {
    await browser.setClipboard(Buffer.from(text).toString('base64'), 'plaintext');
  }

  async clipboard(): Promise<string> {
    return Buffer.from(await browser.getClipboard(), 'base64').toString('utf8');
  }

  async dismissAlert(): Promise<void> {
    await new NativeFeatures().dismissAlert();
  }

  async rotate(orientation: 'LANDSCAPE' | 'PORTRAIT'): Promise<void> {
    await browser.setOrientation(orientation);
  }

  private appArguments(appIdentifier: string): Record<string, string> {
    return browser.isIOS ? { bundleId: appIdentifier } : { appId: appIdentifier };
  }
}
```

`setClipboard` and `getClipboard` carry **base64**: raw text is not a valid clipboard payload.

## 1. Deep and universal links — test the routing (idea 2)

`browser.deepLink` builds the intent on Android and opens the URL on iOS. The test never taps.

```ts
import { expect } from '@wdio/globals';
import { OrderDetailsPage } from '../../src/pages/mobile/OrderDetailsPage';
import { NativeFeatures } from '../../src/support/nativefeatures/NativeFeatures';

describe('Deep links', () => {
  it('Should_OpenOrderDetails_When_OrderLinkIsOpened', async () => {
    await new NativeFeatures().openDeepLink('myapp://orders/A-1001', 'com.example.shop');

    const details = new OrderDetailsPage();
    await details.verifyPageLoaded();
    expect(await details.orderNumber()).toBe('A-1001');
  });
});
```

- `mobile: deepLink` on iOS (XCUITest) works on a simulator and a real device from iOS 16.4 and Xcode 14.3; only below that does a real device need the link opened in Safari.
- A Universal or App Link is an `https://` URL the OS associates with the app; a custom scheme (`myapp://`) is app-private. Test the **https** form to prove the association resolves.

## 2. Permission dialogs — deterministic by default (idea 3)

**Out of the way (most tests).** Set the capability in `wdio.conf.ts`: `'appium:autoGrantPermissions': true` on Android, `'appium:autoAcceptAlerts': true` on iOS (`autoDismissAlerts` denies).

**A specific posture.** Android: `mobile: changePermissions { permissions, appPackage, action: 'grant' | 'revoke' }` and `mobile: getPermissions`. iOS simulator: `mobile: setPermission { bundleId, access: { camera: 'yes', location: 'no' } }`.

**The dialog is the test.** Drive the real OS dialog through `NativeFeatures`, then assert the degraded path your app renders:

```ts
import { MapPage } from '../../src/pages/mobile/MapPage';
import { NativeFeatures } from '../../src/support/nativefeatures/NativeFeatures';

describe('Location permission', () => {
  it('Should_ShowManualLocationPrompt_When_LocationIsDenied', async () => {
    const map = new MapPage();
    await map.tapUseMyLocation();

    await new NativeFeatures().dismissAlert();

    await map.verifyManualLocationPromptShown();
  });
});
```

On Android the dialog belongs to the `com.android.permissioncontroller` package; its buttons are reachable by resource id (`id=com.android.permissioncontroller:id/permission_deny_button`, written as a constant in `NativeFeatures`). Prefer the capability or `changePermissions`, and walk the buttons only when the dialog UX is under test. On iOS a foreground system alert makes the active app `com.apple.springboard`; the alert commands handle that, so never hardcode button coordinates.

## 3. Biometrics — inject the match, assert the unlock and the reject (idea 3)

There is no sensor in CI. Enroll on the device, trigger the prompt from your screen, inject, assert. Test both paths.

```ts
import { expect } from '@wdio/globals';
import { LoginPage } from '../../src/pages/mobile/LoginPage';
import { NativeFeatures } from '../../src/support/nativefeatures/NativeFeatures';

describe('Biometric sign-in', () => {
  it('Should_ReachDashboard_When_FingerprintIsApproved', async () => {
    const login = new LoginPage();
    await login.tapBiometricSignIn();

    await new NativeFeatures().approveFingerprint(1);

    const dashboard = await login.awaitDashboard();
    await expect(dashboard.root()).toBeDisplayed({ message: 'Dashboard after an approved fingerprint' });
  });

  it('Should_ShowPinFallback_When_FingerprintIsRejected', async () => {
    const login = new LoginPage();
    await login.tapBiometricSignIn();

    await new NativeFeatures().rejectFingerprint();

    await expect(login.pinFallback()).toBeDisplayed({ message: 'PIN fallback after a rejected fingerprint' });
  });
});
```

On an iOS simulator, call `mobile: enrollBiometric { isEnabled: true }` once, then `sendIosBiometric('faceId', true)` or `false`. No capability enrolls biometrics.

A real device cannot take an injected read locally; BrowserStack and Sauce instrument the sensor, which `device-cloud` owns. Write the approve and reject assertions here and run them on the farm's injected biometric there.

## Deep-dive reference

`references/details.md` holds **4. Push notifications and backgrounding** — read it when the task touches them.

## Clipboard, pickers, orientation

```ts
describe('Promo code', () => {
  it('Should_FillPromoField_When_CodeIsPasted', async () => {
    await new NativeFeatures().setClipboard('PROMO2026');

    await sharePage.tapPasteCode();

    await expect(checkoutPage.promoField()).toHaveValue('PROMO2026');
  });
});
```

A camera, photo or file picker is an OS surface you cannot drive in CI. Seed the file the picker returns with `browser.pushFile(remotePath, base64)`, pick it from the gallery picker, and assert how your app handled it.

## Anti-patterns

| Smell | Do instead |
|---|---|
| `$('~…')` on the OS permission or biometric dialog | The capability, `mobile: changePermissions`, or the alert commands |
| Reaching a screen by tapping to test a deep link | `browser.deepLink` → assert the destination page |
| `browser.pause` or `setTimeout` after a background, an injection or a push | `waitForDisplayed` / `waitUntil` on the restored, unlocked or routed screen |
| A real fingerprint or camera | Inject the match; seed picker files with `pushFile` |
| Only the approve path | Test the reject path too; reject is where apps crash |
| Auto-granting permissions in every test | The capability for feature tests; the real dialog for the flow under test |
| Hardcoded Springboard or `permissioncontroller` coordinates | The alert commands and stable resource ids |
| Asserting a push was sent | Assert the app's reaction; delivery belongs to the provider's sandbox |
| Rebuilding the session config or page objects here | Reuse `ui-test-author/appium`; add only `NativeFeatures` |

## Rules

- **The OS surface is driven by device commands and `mobile:` extensions, never a page-object selector.** Assert the effect on your screen.
- **Deep links are tested by routing**, and the https form proves the association.
- **Permissions are deterministic by default, real only when the flow is the test**, and the deny path is exercised.
- **Biometrics are injected on emulator or simulator only**; both approve and reject are tested. Real-device injection belongs to `device-cloud`.
- **Lifecycle events assert restored state on a bounded wait.** No `browser.pause` or `setTimeout` anywhere.
- **Push tests assert the app's reaction**, not the send.
- **Clipboard content is base64** in both directions.
- Native-feature helpers live in `src/support/nativefeatures/`; no `any`, strict TypeScript, no secrets in code.

## Cross-references

- **`qa/typescript/skills/ui-test-author/appium`** — the foundation: `BasePage`, `wdio.conf.ts`, gestures, WebView switching, the `BaseTest.ts` failure evidence
- **`qa/typescript/skills/device-cloud`** — where the tests run and how farm-side GPS, network and biometric are injected
- **`qa/typescript/skills/evidence-capture`** — what a failed native flow keeps
- **`qa/java/skills/mobile-native-features`**, **`qa/dotnet/skills/mobile-native-features`** — the sibling stacks
- **`qa/typescript/skills/network-mocking/*`** — the requests an app makes
- **`qa/typescript/skills/data-driven-testing`** — a device, permission or locale matrix as one `it` per row
- **`qa/typescript/skills/test-login-tokens`** — token auth, the boundary with biometric unlock
