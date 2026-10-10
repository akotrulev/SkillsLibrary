# Emulation and mobile web — Playwright 1.64 (TypeScript)

Playwright emulates a device by configuring a browser context: viewport, screen, user agent, device
scale factor, touch and media features. It is fast and runs on CI, but it is not a device. The version in
brackets is where an API first shipped.

## 1. Device profiles

A device is a project, so the whole suite runs per device and the report groups by it.

```typescript
projects: [
  { name: 'setup', testMatch: /.*\.setup\.ts/ },
  { name: 'chromium', use: { ...devices['Desktop Chrome'], storageState: authFile }, dependencies: ['setup'] },
  { name: 'mobile-chrome', use: { ...devices['Pixel 5'], storageState: authFile }, dependencies: ['setup'] },
  { name: 'mobile-safari', use: { ...devices['iPhone 12'], storageState: authFile }, dependencies: ['setup'] },
],
```

- A descriptor sets `userAgent`, `viewport`, `screen`, `deviceScaleFactor`, `isMobile`, `hasTouch` and
  `defaultBrowserType`, so `iPhone 12` runs on WebKit. Spread it first and override after it.
- **1.64 change:** descriptors now also apply `screen`, so `window.screen` and screen media queries follow
  the device. Opt out per project with `screen: undefined`; set it on its own with the `screen` option
  [1.64].
- `devices` is the registry in TypeScript and .NET (`Playwright.Devices["Pixel 5"]`). Java has no
  registry; it sets the same values explicitly on `Browser.NewContextOptions`.
- A device project can be `default: false` [1.64] so it runs only when named (`--project=mobile-safari`),
  for example in the nightly run.

## 2. Touch and mobile viewport

- `isMobile: true` honours the page's `<meta name="viewport">` and enables mobile layout behaviour. It is
  not supported in Firefox.
- `hasTouch: true` enables touch events. `locator.tap()` needs it; `click()` still works on a touch
  context, so use `tap()` only where the app handles touch differently.
- Swipe, pinch and long-press have no first-class locator API. Dispatch touch events only when the feature
  is the gesture itself; a native gesture suite belongs to `qa/typescript/skills/ui-test-author/appium`.

## 3. Viewport

- Set the viewport **per project** (a device) or **per file / `describe`** with
  `test.use({ viewport: { width: 768, height: 1024 } })`, so each test starts at its size.
- `page.setViewportSize(...)` inside a test is only for specs whose behaviour **is** the live resize — the
  layout switching when the window crosses a breakpoint.
- Breakpoint coverage (one generated test per breakpoint row) is owned by
  `qa/typescript/skills/responsive-testing`; it links here for the mechanics.

## 4. Media features

| Feature | Option | Values |
|---|---|---|
| Colour scheme | `colorScheme` | `'light'`, `'dark'`, `'no-preference'` |
| Reduced motion | `reducedMotion` | `'reduce'`, `'no-preference'` |
| Forced colours | `forcedColors` | `'active'`, `'none'` |
| Contrast [1.51] | `contrast` | `'more'`, `'no-preference'` |
| Media type | `page.emulateMedia({ media })` | `'screen'`, `'print'` |

Set them in a project or file `use` (`reducedMotion`, `forcedColors` and `contrast` are standalone options
from 1.63; below that they go in `contextOptions`). Switch mid-test with
`page.emulateMedia({ colorScheme: 'dark' })` when the test is about the switch.

## 5. Locale, time zone, geolocation, permissions

- `locale: 'de-DE'` sets `navigator.language`, `Accept-Language` and number and date formatting;
  `timezoneId: 'Europe/Berlin'` sets the zone. Translation and formatting suites are owned by
  `qa/typescript/skills/language-testing`.
- `geolocation: { latitude: 52.52, longitude: 13.405 }` plus `permissions: ['geolocation']`. Move the user
  with `context.setGeolocation(...)`.
- `context.grantPermissions(['clipboard-read'], { origin })` and `context.clearPermissions()`. Since 1.62
  the headless clipboard is isolated from the OS, so a test reads it through the page, never the host.

## 6. Time: `page.clock`

Install the clock **before** the page loads, so every timer the app starts is controlled.

| Call | Effect |
|---|---|
| `await page.clock.install({ time: new Date('2026-10-10T09:00:00Z') })` | Replaces `Date`, timers and `requestAnimationFrame` with a controllable clock |
| `await page.clock.setFixedTime(date)` | `Date.now()` always returns `date`; timers still run. For "today is …" rendering |
| `await page.clock.runFor('01:00')` / `runFor(60_000)` | Advances time, firing every timer due in that span. For a session-timeout warning |
| `await page.clock.fastForward('30:00')` | Jumps ahead, firing due timers once |
| `await page.clock.pauseAt(date)` / `resume()` | Stops at an instant, then lets time flow again |
| `await page.clock.setSystemTime(date)` | Changes the wall clock without firing timers |

Frozen time is how visual and locale suites make dates stable. It replaces every `waitForTimeout` that
waits for a timer.

## 7. Offline and network conditions

`use: { offline: true }`, or `context.setOffline(true)` mid-test, takes the context offline; assert the
app's offline state, then `setOffline(false)`. Request mocking and throttling are owned by
`qa/typescript/skills/network-mocking`.

## 8. Emulation is not a device

An emulated `Pixel 5` is desktop Chromium with a phone's viewport, user agent and touch. The `iPhone 12`
project is desktop WebKit, not iOS Safari. Neither reproduces the device's GPU, soft keyboard, browser
chrome, OS permission dialogs or real network. Use emulation for layout, responsive behaviour and media
features on every run; send real-device mobile web to `qa/typescript/skills/device-cloud`, and native
apps to `qa/typescript/skills/ui-test-author/appium`.
