---
name: qa-mobile-native-features-typescript
description: Use when the user needs to test the **device-native, OS-level capabilities** a mobile app uses that a normal Appium page-object UI test doesn't exercise. Triggers: "test our deep link opens the right screen in WebdriverIO", "handle the camera/location permission dialog", "test Face ID / fingerprint login on the simulator". For end-to-end suite work prefer the phased agent `qa-mobile-typescript` (or the matching slash command), which loads this skill inside its workflow; use this skill directly for a single targeted artifact.
---

# QA — Mobile Native Features (TypeScript: WebdriverIO + Appium)

Scaffolds Appium tests for the **device-native, OS-level capabilities** a mobile app touches but a normal
page-object UI test never exercises — deep links, runtime permission dialogs, biometric auth, push notifications,
and the app's background/foreground lifecycle. It sits **directly on top of `qa/typescript/skills/ui-test-author/appium`**:
the `BasePage` selector helpers and the WDIO session lifecycle run **unchanged** — this skill adds the layer that
drives the OS surfaces *around* your screens.

> **The discipline this skill encodes** — four ideas that separate a correct native-feature test from a
> page-object reflex:
>
> 1. **A native feature lives OUTSIDE your app's DOM — it is an OS-level surface, so you drive it through the
>    device command API, not page-object selectors.** A runtime permission dialog, the biometric prompt, the
>    notification shade, the deep-link intent, the app's lifecycle state — none of these are elements on *your*
>    screens; they belong to Android/iOS. Reaching for `$('~…')` on the OS permission dialog is the native-testing
>    analogue of looking for an HTTP status on a gRPC call: **the surface isn't yours.** You drive it with
>    `driver.execute('mobile: …')`, `driver.background`/`terminateApp`/`activateApp`, the clipboard/biometric
>    commands, or `driver.acceptAlert()`/`dismissAlert()` — and you assert the *effect* on your own screen via the
>    page object.
> 2. **A deep link is tested by ROUTING, not by tapping.** Launch the app via the link (`mobile: deepLink` / a URL)
>    and assert your page object shows the **right destination screen** — never reproduce the navigation by tapping
>    through the UI (that tests your taps, not the link). The link is the OS surface; the destination screen is
>    yours.
> 3. **Biometric and the permission dialog are injected/forced for determinism — and driven for real only when the
>    flow itself is under test.** A fingerprint/face match is **injected** on the emulator/simulator
>    (`driver.fingerPrint(int)` / `mobile: sendBiometricMatch`) — *never* a real sensor, *never* a `browser.pause`
>    waiting for one. A permission grant is made **deterministic** with a capability (`autoGrantPermissions` /
>    `autoAcceptAlerts`) for the 90% of tests that just need the permission *out of the way* — and you drive the
>    real OS dialog only for the handful of tests where *the dialog flow itself* (deny → degraded UX) is under test.
> 4. **The app lifecycle is a first-class assertion target — assert state is restored on resume, never sleep
>    through it.** Backgrounding, resuming, terminating, a push arriving — each is a `mobile:` / device command, and
>    each is followed by a **bounded wait on the app's observable reaction** (`waitForDisplayed` on the restored
>    screen), never `browser.pause`. "Restored after resume" is an assertion you write, not a pause you hope through.

## Decision matrix — native surface → test shape

| Native surface | Where it lives | Test shape (WebdriverIO) |
|----------------|----------------|--------------------------|
| **Deep / universal link** | OS intent / URL handler | `driver.execute('mobile: deepLink', {url, package/bundleId})` → assert destination **page object** is loaded (routing, not taps) |
| **Runtime permission — out of the way** | OS permission dialog | Cap `'appium:autoGrantPermissions': true` (Android) / `'appium:autoAcceptAlerts': true` (iOS) → the dialog never appears |
| **Runtime permission — the flow IS the test** | OS permission dialog / Springboard | Drive the real dialog: Android `mobile: changePermissions` or the `permissioncontroller` buttons; iOS `driver.dismissAlert()` / `mobile: alert` → assert granted vs degraded UX |
| **Biometric — approved** | OS biometric prompt | Android `driver.fingerPrint(1)`; iOS `mobile: sendBiometricMatch {type, match:true}` → assert the unlocked screen |
| **Biometric — rejected** | OS biometric prompt | same, `match:false` → assert the fallback (PIN screen / error), not a crash |
| **Push notification** | Notification shade / Center | Android `driver.openNotifications()` + assert + tap; iOS sim `mobile: pushNotification` → open from Center → assert deep-linked screen |
| **Background → resume** | App lifecycle | `await driver.background(3)` → **wait** for the restored screen → assert state preserved |
| **Terminate → relaunch** | App lifecycle | `driver.terminateApp(bundleId)` → `driver.activateApp(bundleId)` → assert cold-vs-warm start state; `queryAppState` to verify |
| **Clipboard** | OS pasteboard | `driver.setClipboard('…', 'plaintext')` → paste in-app → assert; or read what the app copied |
| **Camera / file / photo picker** | OS picker (not your UI) | seed the file with `driver.pushFile`, then mock/drive the picker — never automate the real camera |
| **Orientation** | OS rotation | `driver.setOrientation('LANDSCAPE')` → assert layout reflows |

## Stack

- Node 20, TypeScript strict mode (`"strict": true`), ESM
- **WebdriverIO** 9.x with `@wdio/appium-service` (manages the Appium 2.x server) — exposes the device commands
  `driver.background(seconds)` / `terminateApp` / `activateApp` / `queryAppState` / `setClipboard` / `getClipboard` /
  `setOrientation` / `pushFile` / `openNotifications` / `fingerPrint`, and `driver.execute('mobile: …')` for the rest
- **Mocha** (or **Vitest** — pick one and stay consistent) with `@wdio/mocha-framework`; `@wdio/globals` `expect`
- **Allure WDIO reporter** (`@wdio/allure-reporter`) — attach a screenshot of the restored/deep-linked screen
- Reuses `qa/typescript/skills/ui-test-author/appium`'s `BasePage` selector helpers, page objects, and `wdio.conf.ts`
  capability/session setup — **unchanged**
- App path / device caps configured in `wdio.conf.ts`, parameterized by env (`PLATFORM`, `DEVICE`, `APP_PATH`) —
  never hardcoded; no secrets in code
- Native-feature helpers under `src/support/native/`

```jsonc
// package.json (excerpt) — same deps as the appium/typescript skill; nothing new for native features
"devDependencies": {
  "@wdio/cli": "^9.0.0",
  "@wdio/appium-service": "^9.0.0",
  "@wdio/mocha-framework": "^9.0.0",
  "appium": "^2.11.0"
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

- Driving **your app's own screens** via page objects → `qa/typescript/skills/ui-test-author/appium` (this skill builds
  **on** it)
- The **real-device-cloud** layer + GPS/network/biometric **cap-injection plumbing** →
  `qa/typescript/skills/mobile-device-farm` (`mobile-device-farm` = *where* the test runs + how caps are injected on a farm; `mobile-native-features` = *what* you
  assert on those caps — they compose)
- Asserting the **network requests** an app makes → `qa/typescript/skills/network-monitoring/*` (`mobile-native-features` = the app's *reaction* to airplane
  mode / a permission; network-monitoring = asserting the requests)
- The Java / .NET native-feature stacks → `qa/{java,dotnet}/skills/mobile-native-features`
- **Token-based** auth → `qa/typescript/skills/auth0-test-tokens` (biometric *unlock* vs token *auth* are different
  surfaces)

---

## The foundation — page objects + session lifecycle run unchanged

Every test here uses `qa/typescript/skills/ui-test-author/appium`'s `BasePage` and WDIO session. The page objects
(`LoginPage`, `DashboardPage`, …) drive **your** screens exactly as before. This skill adds a thin `NativeFeatures`
helper that owns the **OS-surface** calls, so a test reads as: *drive the OS surface → assert the effect on a page
object.* The native call is the only new vocabulary; the assertion is still a page object. (WDIO's `driver` is the
implicit global, so the helper takes no constructor arg.)

```ts
// src/support/native/NativeFeatures.ts
/**
 * Owns the OS-level surfaces around the app. Every method drives a device command or a `mobile:` command —
 * NEVER a page-object selector. The CALLER asserts the effect on a page object afterwards.
 */
export class NativeFeatures {
  // --- 1. Deep links: launch via the OS, assert routing on a page object ---
  async openDeepLink(url: string, appIdentifier: string): Promise<void> {
    // UiAutomator2: {url, package}; XCUITest: {url, bundleId} — see the per-platform helpers below.
    await driver.execute("mobile: deepLink", { url, package: appIdentifier });
  }

  // --- 3. Biometric: inject a match/no-match — emulator/simulator only, never a real sensor ---
  async approveFingerprint(fingerId: number): Promise<void> {
    await driver.fingerPrint(fingerId); // enrolled finger id on the emulator
  }

  async sendIosBiometric(type: "touchId" | "faceId", match: boolean): Promise<void> {
    await driver.execute("mobile: sendBiometricMatch", { type, match });
  }

  // --- 4. Lifecycle: background/terminate/activate — each followed by a bounded wait in the test ---
  async backgroundFor(seconds: number): Promise<void> {
    await driver.background(seconds); // negative = indefinitely; activate to return
  }

  async terminate(bundleOrPackage: string): Promise<void> { await driver.terminateApp(bundleOrPackage); }
  async activate(bundleOrPackage: string):  Promise<void> { await driver.activateApp(bundleOrPackage); }

  // --- clipboard / orientation: OS surfaces the app reacts to ---
  async setClipboard(text: string): Promise<void> { await driver.setClipboard(text, "plaintext"); }
  async getClipboard(): Promise<string>            { return driver.getClipboard(); }
  async rotate(o: "LANDSCAPE" | "PORTRAIT"): Promise<void> { await driver.setOrientation(o); }
}
```

---

## 1. Deep / universal links — test the routing, not the taps (idea #2)

A deep link's contract is: *given this URL, the app opens this screen.* So launch the app **via the link** and
assert your page object shows the destination — never reproduce the navigation by tapping through the UI. The link
is the OS surface (`mobile: deepLink` builds the intent / opens the URL); the destination is your screen.

```ts
// Android (UiAutomator2): mobile: deepLink {url, package}
import { expect } from "@wdio/globals";
import { OrderDetailsPage } from "../../src/pages/mobile/OrderDetailsPage";
import { NativeFeatures } from "../../src/support/native/NativeFeatures";

it("opens order details when the deep link is opened", async () => {
  const os = new NativeFeatures();

  await os.openDeepLink("myapp://orders/A-1001", "com.example.shop"); // OS routes the intent — no taps

  const details = new OrderDetailsPage();
  await details.verifyPageLoaded();                                   // page object proves the ROUTE landed
  await expect(details.orderId()).toHaveText("A-1001");               // …and carried the param through
});
```

> **iOS differs by where the app runs.** On the **simulator**, `mobile: deepLink` takes `{url, bundleId}` and works
> for custom-scheme and Universal Links. On a **real iOS device** you cannot just hand the URL to the app — open it
> through **Safari** (`driver.url(url)` in a Safari session, then tap "Open") because a custom scheme has to be
> resolved by the OS. Android `mobile: deepLink` (an `am start -d <url>`) is uniform across emulator and real device.
> **Universal Links vs custom-scheme deep links:** a Universal/App Link is an `https://` URL the OS associates with
> the app; a custom-scheme link (`myapp://`) is app-private. Test the **https** form for Universal Links so you also
> prove the association resolved.

---

## 2. Runtime permission dialogs — deterministic by default, driven only when the flow is the test (idea #3)

The OS permission dialog is **not your UI** — it belongs to the system, its selectors differ per OS version, and
it pops up nondeterministically. So there are two modes, and picking the right one is the whole skill:

**Mode A — get the dialog out of the way (the 90% case).** Most tests want to test *the feature behind* a
permission, not the dialog. Grant it deterministically with a capability so the dialog never appears (set in
`wdio.conf.ts`):

```ts
// wdio.conf.ts capabilities
// Android: grant all manifest permissions on install — the dialog never shows
"appium:autoGrantPermissions": true,
// iOS: auto-accept any system alert that appears (or autoDismissAlerts to deny)
"appium:autoAcceptAlerts": true,
```

> Android also has `mobile: changePermissions` / `mobile: getPermissions` to **set a specific permission state**
> before a flow (`granted` / `denied`) — sharper than the all-or-nothing cap when you want camera granted but
> location denied. Prefer it when the test needs a *specific* permission posture.

**Mode B — the dialog flow IS the test (the handful that matters).** When you're testing what happens on **deny**
(degraded UX, a "go to Settings" prompt) or the grant flow itself, you must drive the **real** OS dialog — through
the OS surface, not a page object on your screens:

```ts
// iOS: the system alert is reachable via the standard alert API or `mobile: alert`
import { MapPage } from "../../src/pages/mobile/MapPage";

it("shows degraded map when location is denied", async () => {
  const map = new MapPage();
  await map.tapUseMyLocation();                       // triggers the OS permission dialog

  await driver.dismissAlert();                        // DENY on the real OS dialog (not your UI)
  // or: await driver.execute("mobile: alert", { action: "dismiss" });

  await map.verifyManualLocationPromptShown();        // assert the DEGRADED path your app renders
});
```

```ts
// Android: the dialog is the permissioncontroller package; drive its real buttons when the flow is under test.
// (For determinism prefer the cap / mobile: changePermissions; only walk the buttons when testing the dialog UX.)
await $("id=com.android.permissioncontroller:id/permission_deny_button").click();
```

> **iOS Springboard nuance:** when a permission/system alert is at the foreground, the active app context is
> `com.apple.springboard`, not your app. The XCUITest alert API handles this for you; if you ever need to interact
> with the dialog directly, `mobile: activateApp` Springboard first. Don't hardcode Springboard button coordinates.

---

## 3. Biometric auth — inject the match, assert the unlock (and the reject) (idea #3)

A fingerprint/Face ID match is **injected** on the emulator/simulator — there is no real sensor in CI, and a
`browser.pause` waiting for a human finger is banned and pointless. Enroll biometrics on the device, trigger the
prompt from your screen, inject the match, then assert the unlocked screen. Always test **both** the approved and
the rejected path.

```ts
// Android: emulator must have a fingerprint enrolled; driver.fingerPrint(id) injects a touch
import { expect } from "@wdio/globals";
import { LoginPage } from "../../src/pages/mobile/LoginPage";
import { NativeFeatures } from "../../src/support/native/NativeFeatures";

it("reaches the dashboard when the fingerprint is approved", async () => {
  const login = new LoginPage();
  await login.tapBiometricSignIn();                   // YOUR screen triggers the OS biometric prompt

  await new NativeFeatures().approveFingerprint(1);   // inject a MATCH for enrolled finger id 1

  const dashboard = await login.awaitDashboard();     // explicit wait inside the page object — no pause
  await expect(dashboard.root()).toBeDisplayed();
});

it("shows the PIN fallback when the fingerprint is rejected", async () => {
  const login = new LoginPage();
  await login.tapBiometricSignIn();

  // a non-enrolled finger id injects a NO-MATCH; assert the fallback, not a crash
  await new NativeFeatures().approveFingerprint(99);

  await expect(login.pinFallback()).toBeDisplayed();
});
```

```ts
// iOS: enroll once, then send a match/no-match. Requires the sim to allow biometric enrollment.
// 'appium:allowEnrollBiometrics': true at session start; then:
await driver.execute("mobile: enrollBiometric", { isEnabled: true });
await new NativeFeatures().sendIosBiometric("faceId", true);   // match
// reject path: sendIosBiometric("faceId", false) → assert the passcode fallback screen
```

> **Real-device biometric is a farm concern, not this skill's.** On a real device you can't inject a sensor read
> locally — that's BrowserStack/Sauce sensor instrumentation (`enableBiometric` + `browserstack_executor
> performBiometric`), which `qa/typescript/skills/mobile-device-farm` owns. They **compose**: write the approve/reject
> *assertions* here, run them on the farm's injected biometric there. Never wire a real fingerprint into a test.

---

## Deep-dive reference

These sections live in `references/details.md` — **read it when the task touches them**: **4. Push notifications + backgrounding / resume — assert state, never sleep through it (idea #4)**.

## Clipboard, pickers, orientation — the smaller OS surfaces

```ts
// Clipboard: seed the OS pasteboard, paste in-app, assert; or read what the app copied
const os = new NativeFeatures();
await os.setClipboard("PROMO2026");
await sharePage.tapPasteCode();
await expect(checkoutPage.promoField()).toHaveValue("PROMO2026");

// Orientation: the app should reflow, not crash
await os.rotate("LANDSCAPE");
await expect(galleryPage.columns()).toBeElementsArrayOfSize(3); // layout reacts to the OS rotation
```

> **Camera / photo / file pickers are an OS surface you don't automate directly.** You can't drive the real camera
> in CI. Seed the file the picker will return with `driver.pushFile(remotePath, base64)`, then either mock the
> picker or select the seeded file from the gallery picker — and assert your app handled the result. Never try to
> "take a photo."

---

## Anti-patterns

| Smell | Why it's wrong | Do instead |
|---|---|---|
| `$('~…')` on the OS permission/biometric dialog | The dialog is the OS's UI, selectors differ per OS version, and it's nondeterministic | Drive it via the cap (`autoGrantPermissions`/`autoAcceptAlerts`), `mobile: changePermissions`, or `driver.dismissAlert()` |
| Testing a deep link by **tapping through** the UI to the screen | Tests your taps, not the link's routing | `mobile: deepLink` / launch the URL → assert the destination **page object** |
| `browser.pause` / `setTimeout` after backgrounding / a biometric injection / a push | Banned by CLAUDE.md; the OS reacts at its own pace | `waitForDisplayed` / `waitUntil` on the restored / unlocked / deep-linked screen |
| A **real fingerprint / camera** in the test | Impossible in CI, flaky, and unsafe | Inject biometric (`fingerPrint`/`sendBiometricMatch`); seed picker files with `pushFile` |
| Only testing the **approve** biometric path | Reject (fallback to PIN) is where apps crash | Test both `match:true` and `match:false`/non-enrolled id |
| Auto-granting permissions for **every** test, including the deny-UX test | The deny path never gets exercised | Mode A (cap) for feature tests; Mode B (drive the real dialog) for the flow-under-test |
| Hardcoding Springboard / `permissioncontroller` button coordinates | OS-version-fragile | Use the XCUITest alert API / stable resource-ids; activate Springboard via `mobile: activateApp` |
| Asserting a push was **sent** via Appium | That's a backend/push-provider concern | Assert the app's **reaction** (shade → tap → screen); push *sending* → provider sandbox |
| Re-deriving the session config / page objects here | Duplicates `appium/typescript`, drifts | Reuse `BasePage` + page objects + `wdio.conf.ts` unchanged; add only `NativeFeatures` |

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

- **The OS surface is driven by the device command API, never a page-object selector.** Permission dialogs,
  biometric prompts, the notification shade, deep-link intents, lifecycle state → `driver.execute('mobile: …')` /
  `driver.background`/`terminateApp`/`activateApp` / `driver.dismissAlert()`. Assert the **effect** on your screen
  via the page object.
- **Deep links are tested by routing.** Launch via `mobile: deepLink` / the URL and assert the destination page
  object — never reproduce the navigation by tapping. Test the **https** Universal/App Link form so the association
  is proven, not just a custom scheme.
- **Permissions: deterministic by default, real only when the flow is the test.** Use `autoGrantPermissions` /
  `autoAcceptAlerts` / `mobile: changePermissions` for feature tests; drive the **real** OS dialog only when the
  grant/deny flow itself is under test, and exercise the **deny** path.
- **Biometric is injected on emulator/simulator only** (`driver.fingerPrint(int)` / `mobile: sendBiometricMatch`),
  never a real sensor; test **both** approve and reject. Real-device biometric injection →
  `qa/typescript/skills/mobile-device-farm`.
- **Lifecycle events assert restored state on a bounded wait.** `driver.background` / `terminateApp` /
  `activateApp` / `queryAppState`, each followed by `waitForDisplayed` on the observable result. **No `browser.pause`
  / `setTimeout`** anywhere — including for OS animations, dialog appearance, or push delivery.
- **Push tests assert the app's reaction, not the send.** Open the shade/Center (`openNotifications` /
  `mobile: pushNotification`), assert, tap, assert the routed screen. Push *delivery* is a provider concern.
- **Reuse `appium/typescript` unchanged** — `BasePage`, page objects, `wdio.conf.ts`. Add only `NativeFeatures`. App
  ids / device caps configured in `wdio.conf.ts` via env; no `any`, strict TS; no secrets in code.

## Cross-references

- **`qa/typescript/skills/ui-test-author/appium`** — the **foundation this skill builds on**: `BasePage` selector helpers,
  the `wdio.conf.ts` capability/session setup, `driver.execute('mobile: …')` gesture commands, WDIO auto-waits +
  `waitForDisplayed`, native↔WEBVIEW context switching. The page objects + session lifecycle run **unchanged**; `mobile-native-features`
  adds the OS-surface layer. Mirror its selector/wait idioms exactly.
- **`qa/typescript/skills/mobile-device-farm`** — the **real-device-cloud layer** + GPS/network/biometric
  **cap-injection plumbing**. `mobile-device-farm` = *where* the test runs + *how* the cap is injected; `mobile-native-features` = *what* you assert on
  those caps. They compose. Don't duplicate the farm wiring.
- **`qa/java/skills/mobile-native-features`** + **`qa/dotnet/skills/mobile-native-features`** — the sibling stacks (java-client
  `InteractsWithApps`/`fingerPrint` · `Appium.WebDriver` `BackgroundApp`/`FingerPrint`); same four ideas, different
  client idioms. Structure ported, not redesigned.
- **`qa/typescript/skills/network-monitoring/*`** — the **boundary** on network conditioning/requests: `mobile-native-features` tests the app's *reaction*;
  network-monitoring asserts the *requests*.
- **`qa/typescript/skills/data-driven-testing`** — drive a **device / permission / locale matrix** via Vitest
  `test.for` / a Mocha row-loop (one independent named case per row); this skill supplies the rows, that one the
  data-driven discipline.
- **`qa/typescript/skills/cloud-grid-config`** — the grid/session wiring the device session connects through (under
  `mobile-device-farm`).
- **`qa/typescript/skills/auth0-test-tokens`** — token-based auth, the boundary vs biometric *unlock*.
- **`qa/reporting/typescript/skills/allure-reporting`** — attach a screenshot of the deep-linked / restored / unlocked screen per
  native-flow result.
