# Emulation and mobile web — Microsoft.Playwright 1.63

Playwright emulates a device by configuring a browser context: viewport, screen, user agent, device scale
factor, touch and media features. It is fast and runs on CI, but it is not a device. In .NET every one of
these is a `BrowserNewContextOptions` property, set by amending `base.ContextOptions()` in the fixture that
needs it (`lifecycle.md` §4). The version in brackets is where an API first shipped.

## 1. Devices: `Playwright.Devices[...]`

`Playwright.Devices` is Playwright's device registry: a read-only dictionary of `BrowserNewContextOptions`
keyed by name (`"Pixel 5"`, `"iPhone 13"`, `"Desktop Chrome"`), with the values of the installed version.
Copy the descriptor's values onto the base options, so `BaseURL`, the video folder and the locale survive:

```csharp
public class CheckoutOnPixel5Tests : CheckoutTests
{
    public override BrowserNewContextOptions ContextOptions()
    {
        var options = base.ContextOptions();
        var pixel5 = Playwright.Devices["Pixel 5"];
        options.UserAgent = pixel5.UserAgent;
        options.ViewportSize = pixel5.ViewportSize;
        options.ScreenSize = pixel5.ScreenSize;
        options.DeviceScaleFactor = pixel5.DeviceScaleFactor;
        options.IsMobile = pixel5.IsMobile;
        options.HasTouch = pixel5.HasTouch;
        return options;
    }
}
```

- Returning `Playwright.Devices["Pixel 5"]` itself would drop `BaseURL` and the video folder — the
  `new()` defect in another form.
- **To run an existing fixture on a device, derive from it** and override `ContextOptions()`; NUnit runs the
  inherited tests again in the derived fixture, which runs in parallel with the original.
- `Playwright` is the `PlaywrightTest` property, set before `ContextOptions()` is called.
- A descriptor's browser is not an option: `iPhone 13` is a WebKit device in Playwright's list, but
  the options carry no browser. The browser comes from the runsettings `BrowserName` (or `BROWSER`), so an
  iPhone profile under Chromium is Chromium with an iPhone's size and user agent. A WebKit run is a
  separate `dotnet test -- Playwright.BrowserName=webkit` run and a WebKit install.
- The descriptor's user agent carries that release's browser version, so it moves when Playwright moves.
  The 1.64 change that makes Node's test-runner device descriptors forward `screen` does not apply:
  `ScreenSize` is copied explicitly.

## 2. Touch and mobile viewport

- `IsMobile = true` honours the page's `<meta name="viewport">` and enables mobile layout behaviour. It is
  not supported in Firefox.
- `HasTouch = true` enables touch events. `locator.TapAsync()` needs it; `ClickAsync()` still works on a
  touch context, so use `TapAsync()` only where the app handles touch differently.
- Swipe, pinch and long-press have no first-class locator API. A native gesture suite belongs to
  `qa/dotnet/skills/ui-test-author/appium`.

## 3. Viewport

- Set the viewport **per fixture**, in `ContextOptions()`
  (`options.ViewportSize = new() { Width = 1280, Height = 720 }`), so each test starts at its size.
- `Page.SetViewportSizeAsync(width, height)` inside a test is only for tests whose behaviour **is** the
  live resize — the layout switching when the window crosses a breakpoint — and it goes through a page
  object method.
- Breakpoint coverage (one `[TestCase]` per breakpoint) is owned by `qa/dotnet/skills/responsive-testing`;
  it links here for the mechanics.

## 4. Media features

| Feature | Context option | Values |
|---|---|---|
| Colour scheme | `ColorScheme = ColorScheme.Dark` | `Light`, `Dark`, `NoPreference` |
| Reduced motion | `ReducedMotion = ReducedMotion.Reduce` | `Reduce`, `NoPreference` |
| Forced colours | `ForcedColors = ForcedColors.Active` | `Active`, `None` |
| Contrast [1.51] | `Contrast = Contrast.More` | `More`, `NoPreference` |
| Media type | `await Page.EmulateMediaAsync(new() { Media = Media.Print })` | `Screen`, `Print` |

The enums live in `Microsoft.Playwright`. `ContextTest` already sets `ColorScheme = Light`; a dark-mode
fixture overrides that one property. Switch mid-test with
`await Page.EmulateMediaAsync(new() { ColorScheme = ColorScheme.Dark })` only when the test is about the
switch.

## 5. Locale, time zone, geolocation, permissions

- `Locale = "de-DE"` sets `navigator.language`, `Accept-Language` and number and date formatting
  (`ContextTest` defaults it to `en-US`); `TimezoneId = "Europe/Berlin"` sets the zone. Translation and
  formatting suites are owned by `qa/dotnet/skills/language-testing`, which runs one fixture per locale with
  `[TestFixture("de-DE", "Europe/Berlin")]`.
- `Geolocation = new() { Latitude = 52.52f, Longitude = 13.405f }` plus `Permissions = new[] { "geolocation" }`.
  Move the user mid-test with `await Context.SetGeolocationAsync(new() { Latitude = 48.137f, Longitude = 11.575f })`.
- `await Context.GrantPermissionsAsync(new[] { "clipboard-read" })` and `ClearPermissionsAsync()`. Since
  1.62 the headless clipboard is isolated from the OS, so a test reads it through the page, never the host.

## 6. Time: `Page.Clock`

Install the clock **before** the page loads — in the test class's `[SetUp]`, before the page object
navigates — so every timer the app starts is controlled.

| Call | Effect |
|---|---|
| `await Page.Clock.InstallAsync(new() { TimeDate = new DateTime(2026, 10, 10, 9, 0, 0, DateTimeKind.Utc) })` | Replaces `Date`, timers and `requestAnimationFrame` with a controllable clock |
| `await Page.Clock.SetFixedTimeAsync(new DateTime(2026, 10, 10, 9, 0, 0, DateTimeKind.Utc))` | `Date.now()` always returns that instant; timers still run. For "today is …" rendering |
| `await Page.Clock.RunForAsync("01:00")` / `RunForAsync(60_000)` | Advances time, firing every timer due in that span. For a session-timeout warning |
| `await Page.Clock.FastForwardAsync("30:00")` | Jumps ahead, firing due timers once |
| `await Page.Clock.PauseAtAsync(...)` / `ResumeAsync()` | Stops at an instant, then lets time flow again |
| `await Page.Clock.SetSystemTimeAsync(...)` | Changes the wall clock without firing timers |

Frozen time is how visual and locale suites make dates stable, and it replaces every wait for a timer.
The clock API has not changed between 1.51 and 1.64.

## 7. Offline

`Offline = true` on the options, or `await Context.SetOfflineAsync(true)` mid-test, takes the context
offline; assert the app's offline state, then `SetOfflineAsync(false)`. Request mocking and throttling are
owned by `qa/dotnet/skills/network-mocking`.

## 8. Emulation is not a device

An emulated Pixel 5 is desktop Chromium with a phone's viewport, user agent and touch. Neither it nor an
iPhone profile reproduces the device's GPU, soft keyboard, browser chrome, OS permission dialogs or real
network. Use emulation for layout, responsive behaviour and media features on every run; send real-device
mobile web to `qa/dotnet/skills/device-cloud`, and native apps to `qa/dotnet/skills/ui-test-author/appium`.
