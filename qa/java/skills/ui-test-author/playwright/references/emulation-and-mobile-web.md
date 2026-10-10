# Emulation and mobile web — Playwright for Java 1.63

Playwright emulates a device by configuring a browser context: viewport, screen, user agent, device scale
factor, touch and media features. It is fast and runs on CI, but it is not a device. In Java every one of
these is a `Browser.NewContextOptions` setter, applied through `BaseTest.contextOptions()`
(`lifecycle.md` §3). The version in brackets is where an API first shipped.

## 1. Devices: explicit options, because Java has no registry

TypeScript and .NET read `devices["Pixel 5"]`; **Playwright for Java has no device registry.** A device is
the same values set explicitly, on the class that runs on it:

```java
public class CheckoutOnPixel5Test extends BaseTest {
    @Override
    protected Browser.NewContextOptions contextOptions() {
        return new Browser.NewContextOptions()
                .setUserAgent("Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.8010.12 Mobile Safari/537.36")
                .setViewportSize(393, 727)
                .setScreenSize(393, 851)
                .setDeviceScaleFactor(2.75)
                .setIsMobile(true)
                .setHasTouch(true);
    }
}
```

- The values are Playwright's own descriptor for `Pixel 5` at v1.63.0
  (`packages/isomorphic/deviceDescriptorsSource.json` in `microsoft/playwright`). Copy them from the tag you
  pin: the user agent carries that release's browser version, so refresh it when Playwright moves.
- **To run an existing class on a device, subclass it** and override `contextOptions()`; TestNG runs the
  inherited tests again in the subclass. With `parallel="classes"` the device class runs on its own thread.
- When two classes share a device, a static factory method returning a **new** options object
  (`Devices.pixel5()`) holds the values once. Never share one options instance.
- A descriptor also names a browser: `iPhone 12` is `defaultBrowserType: webkit`. `BaseTest` launches
  Chromium, so an iPhone profile there is Chromium with an iPhone's size and user agent. A WebKit run is a
  change to the launch and the browser install, not an emulation option.
- The 1.64 change that makes Node's device descriptors forward `screen` does not apply here:
  `setScreenSize` is set explicitly.

## 2. Touch and mobile viewport

- `setIsMobile(true)` honours the page's `<meta name="viewport">` and enables mobile layout behaviour. It
  is not supported in Firefox.
- `setHasTouch(true)` enables touch events. `locator.tap()` needs it; `click()` still works on a touch
  context, so use `tap()` only where the app handles touch differently.
- Swipe, pinch and long-press have no first-class locator API. A native gesture suite belongs to
  `qa/java/skills/ui-test-author/appium`.

## 3. Viewport

- Set the viewport **per class**, in `contextOptions()`, so each test starts at its size.
- `page.setViewportSize(width, height)` inside a test is only for specs whose behaviour **is** the live
  resize — the layout switching when the window crosses a breakpoint — and it goes through a page object
  method.
- Breakpoint coverage (one row per breakpoint) is owned by `qa/java/skills/responsive-testing`; it links here
  for the mechanics.

## 4. Media features

| Feature | Context option | Values |
|---|---|---|
| Colour scheme | `setColorScheme(ColorScheme.DARK)` | `LIGHT`, `DARK`, `NO_PREFERENCE` |
| Reduced motion | `setReducedMotion(ReducedMotion.REDUCE)` | `REDUCE`, `NO_PREFERENCE` |
| Forced colours | `setForcedColors(ForcedColors.ACTIVE)` | `ACTIVE`, `NONE` |
| Contrast [1.51] | `setContrast(Contrast.MORE)` | `MORE`, `NO_PREFERENCE` |
| Media type | `page.emulateMedia(new Page.EmulateMediaOptions().setMedia(Media.PRINT))` | `SCREEN`, `PRINT` |

The enums live in `com.microsoft.playwright.options`. Set them per class; switch mid-test with
`page.emulateMedia(new Page.EmulateMediaOptions().setColorScheme(ColorScheme.DARK))` only when the test is
about the switch.

## 5. Locale, time zone, geolocation, permissions

- `setLocale("de-DE")` sets `navigator.language`, `Accept-Language` and number and date formatting;
  `setTimezoneId("Europe/Berlin")` sets the zone. Translation and formatting suites are owned by
  `qa/java/skills/language-testing`.
- `setGeolocation(52.52, 13.405)` plus `setPermissions(List.of("geolocation"))`. Move the user mid-test with
  `page.context().setGeolocation(new Geolocation(48.137, 11.575))`.
- `page.context().grantPermissions(List.of("clipboard-read"), options)` and `clearPermissions()`. Since 1.62
  the headless clipboard is isolated from the OS, so a test reads it through the page, never the host.

## 6. Time: `page.clock()`

Install the clock **before** the page loads — in the test class's `@BeforeMethod`, before the page object
navigates — so every timer the app starts is controlled.

| Call | Effect |
|---|---|
| `page.clock().install(new Clock.InstallOptions().setTime("2026-10-10T09:00:00Z"))` | Replaces `Date`, timers and `requestAnimationFrame` with a controllable clock |
| `page.clock().setFixedTime("2026-10-10T09:00:00Z")` | `Date.now()` always returns that instant; timers still run. For "today is …" rendering |
| `page.clock().runFor("01:00")` / `runFor(60_000)` | Advances time, firing every timer due in that span. For a session-timeout warning |
| `page.clock().fastForward("30:00")` | Jumps ahead, firing due timers once |
| `page.clock().pauseAt(...)` / `resume()` | Stops at an instant, then lets time flow again |
| `page.clock().setSystemTime(...)` | Changes the wall clock without firing timers |

Frozen time is how visual and locale suites make dates stable, and it replaces every wait for a timer.

## 7. Offline

`setOffline(true)` on the options, or `page.context().setOffline(true)` mid-test, takes the context
offline; assert the app's offline state, then `setOffline(false)`. Request mocking and throttling are owned
by `qa/java/skills/network-mocking`.

## 8. Emulation is not a device

An emulated Pixel 5 is desktop Chromium with a phone's viewport, user agent and touch. Neither it nor an
iPhone profile reproduces the device's GPU, soft keyboard, browser chrome, OS permission dialogs or real
network. Use emulation for layout, responsive behaviour and media features on every run; send real-device
mobile web to `qa/java/skills/device-cloud`, and native apps to `qa/java/skills/ui-test-author/appium`.
