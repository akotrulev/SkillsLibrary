---
name: ui-tests-appium
description: Use when scaffolding a .NET Appium 3 (Appium.WebDriver) page object or mobile UI test. Triggers "write an Appium test for X". Not for exploring a live screen (mobile-screen-explorer).
---

# QA — Appium .NET Page Object & Test Generator

Scaffolds Appium page objects and NUnit mobile UI tests in C#, mirroring the Java and TypeScript siblings. A thin `BaseAppiumPage` with `WebDriverWait`, a per-platform test-id finder, scoped components that re-resolve on every call, typed navigation, and one driver per test fixture. The compilable reference is `assets/`.

## Versions

| Artifact | Primary | Supported |
|---|---|---|
| `Appium.WebDriver` | **9.0.0** | 8.x |
| `Selenium.WebDriver` · `Selenium.Support` | 4.51.0 (≥ 4.46 required by the client) | 4.46–4.50 |
| Appium server | **3.8.0** | 2.19 (frozen) |
| `appium-uiautomator2-driver` / `appium-xcuitest-driver` | 8.x / 12.x | 4.x / 9.x |
| NUnit · adapter · Test SDK · `Allure.NUnit` | 4.6.1 · 6.3.1 · 18.10.1 · 2.15.0 | — |
| .NET | 10 | 8, 9 (match the project's TFM) |

- **Detect the project's lane first** (`Appium.WebDriver` in `Directory.Packages.props`, `appium -v`) and keep it. Appium.WebDriver 8.x is the first client built for Appium 3's `mobile:` commands, and 9.0.0's only breaking change is **strong-name signing**: a project that moves from 8.x rebuilds every project that references the client. The client's major does **not** track Selenium's.
- 8.0 removed `ToggleWifi`, `ToggleData`, `ToggleAirplaneMode`, `SetConnectionType` and `StartActivity` (re-added in 8.1 over `mobile: startActivity`); use `mobile: setConnectivity`. `TouchAction` and `MultiAction` went in 6.0: use W3C actions or a `mobile:` gesture.
- **There is no `AppiumBy` in .NET.** Locators are `MobileBy` (`OpenQA.Selenium.Appium`). Capabilities are `AppiumOptions` (`AutomationName`, `DeviceName`, `App`, `PlatformVersion`, `PlatformName`) plus `AddAdditionalAppiumOption`, which adds the `appium:` prefix to a bare name. There are no per-driver options classes, and `DesiredCapabilities` is long gone.
- **NUnit stays 4.x (D18).** NUnit 5 changes `Assert.ThrowsAsync` to return a `Task` that must be awaited, and `Allure.NUnit` 2.15 on NUnit 5 is unverified. Do not move a project to NUnit 5 as a side effect.
- A device cloud that still runs Appium 2 keeps the project on the supported lane; `device-cloud` says how to check.

## When to use

- New page object under `AppiumTests/Pages/`, a scoped component (list row, card, sheet), or an NUnit test under `AppiumTests/Tests/`
- Gestures, WebView switching, app state or failure evidence in an Appium C# suite

## When NOT to use

- Appium Java → `qa/java/skills/ui-test-author/appium`; TypeScript → `qa/typescript/skills/ui-test-author/appium`
- Selenium / web → `qa/dotnet/skills/ui-test-author/selenium` or `…/playwright`
- Reviewing an existing page object → `qa/dotnet/skills/ui-test-author/review`
- Designing the whole POM architecture → `qa/dotnet/skills/page-object-design`

## Inputs needed

1. **Screen name** (PascalCase) and **platform** — Android, iOS or both
2. **Elements** — name plus the ladder rung from `mobile-screen-explorer`
3. **Landmark element** for `VerifyPageLoaded`
4. **Actions** and whether each navigates, plus the destination pages

## The assets

`assets/` is one runnable test project (namespaces `AppiumTests.Support`, `.Pages`, `.Tests`); copy it, do not retype it.

| File | Holds |
|---|---|
| `Directory.Packages.props`, `AppiumTests.csproj`, `mobile.runsettings` | Exact pins, `net10.0`, one NUnit worker |
| `Env.cs` | The one `Required(name)` helper and `AppiumUrl` |
| `AppiumDriverFactory.cs` | One `AppiumDriver` from env (`PLATFORM`, `DEVICE_NAME`, `APP_PATH`, `PLATFORM_VERSION`, `APPIUM_URL`); the Android options set `appium:settings[disableIdLocatorAutocompletion]` |
| `BaseMobileTest.cs` | Driver per fixture, the recording per test and, on failure, a screenshot, page source, device log and the recording; see `qa/dotnet/skills/evidence-capture/references/appium.md` |
| `BaseAppiumPage.cs` | `TestId` and the other ladder finders, `IsTestIdVisible`, the abstract `VerifyPageLoaded` |
| `LoginPage.cs`, `OrdersPage.cs`, `page_template.cs` | Screens; `SignIn` returns the destination; the template is the shape to copy |
| `OrderRow.cs` | A scoped component: a row key, re-resolved on every call |
| `OrdersTests.cs` | One test |
| `GestureExtensions.cs` | `ScrollGesture`, `LongPress`, `Swipe`, `Tap` |

Platform selection is one mechanism: the `PLATFORM` variable read by the factory. A run is `PLATFORM=android dotnet test`; there is no `appsettings.<platform>.json` and no `--filter "Platform=…"`.

## Locator ladder

A React Native `testID` is the iOS `accessibilityIdentifier` (the element's `name`) and the Android `resource-id`. The accessibility label (`content-desc`) is screen-reader text, never a test id.

| Rung | iOS | Android |
|---|---|---|
| 1 — the test id | `MobileBy.AccessibilityId("Login.Submit")` | `MobileBy.Id("Login.Submit")` |
| 2 — a native query | `MobileBy.IosNSPredicate` · `MobileBy.IosClassChain` | `MobileBy.AndroidUIAutomator` |
| 3 — XPath | last resort | last resort |

- `BaseAppiumPage.TestId` picks the rung-1 form for the running platform, so a page has one accessor per element on both platforms. `ByContentDescription` is the Android `AccessibilityId` lookup for an app that exposes only a `content-desc`.
- Android prefixes every `id` lookup with `<package>:id/`. A React Native or Compose `testTag` id has no prefix, so the option `appium:settings[disableIdLocatorAutocompletion]` set to `true` switches the prefixing off (the factory sets it). Compose also needs `testTagsAsResourceId` in the app, or the `mapTestTagToResourceId` setting on driver 8.4+. A Views app whose ids carry the package leaves the setting off. Check the live page source before choosing.
- `UiSelector` is secondary. Google is deprecating `UiSelector`, `UiScrollable`, `UiObject` and `UiCollection`, and the UiAutomator2 driver warns this will invalidate every `-android uiautomator` locator. Reach for it only for a query no other rung can express.
- A working XPath proves the node exists, not that it is the final locator. Downgrade it as soon as the source exposes a stronger rung. Each XPath row goes into `missing-testids.md` (page, element, fallback in use); the code carries no marker, and the constant's name says it is a fallback (`PasswordRevealXPathFallback`).

## Scoped components

A repeating row cannot be found with a bare child locator, and a held element goes stale when a RecyclerView or table view recycles its cells.

1. A component holds a **row key**, never an element. The row is found again on every call (`OrderRow.Root()`).
2. Find the row by a visible key inside it, with **element-scoped finds first**: enumerate the rows with `FindElements`, then read the key with `row.FindElement(...)`. The ids are static; no index, no data in the locator.
3. Only when the platform can do the whole job in one query, scope there: an iOS class chain ``**/XCUIElementTypeCell[`name == "OrderRow"`]/**/XCUIElementTypeStaticText[`name == "OrderRow.Title"`]``. Mind the `UiSelector` caveat on Android.
4. Components do **not** extend `BaseAppiumPage`. They use a small set of scoped finds and have no `VerifyPageLoaded`; the host page owns the landmark.
5. An Android XPath from an element starts with `.` (`.//x`); a bare `//x` can escape the element's scope.

## Gestures, WebView, app state

Code for each is in [`references/details.md`](references/details.md) — read it when the task touches them.

- **Gestures.** Prefer a driver `mobile:` command (Android `clickGesture`, `longClickGesture`, `doubleClickGesture`, `dragGesture`, `swipeGesture`, `scrollGesture`; iOS `tap`, `touchAndHold`, `doubleTap`, `swipe`, `scroll`); fall back to W3C `PointerInputDevice` and `ActionSequence`. `GestureExtensions` holds both. A gesture sits in a page method named for its intent, never in a test; coordinates come from `AppiumElement.Rect`, never a literal.
- `mobile: scrollGesture` scrolls **by a percent** and returns whether more content remains; it does not stop at an element. To reach one, repeat it on a bounded wait, or use iOS `mobile: scrollToElement`.
- **WebView.** Wait for the `WEBVIEW*` context, switch, act, and switch back in a `finally` of a page helper. If the element is missing from the native page source, check the context before the locator. Android WebViews need a Chromedriver that matches the WebView: start the **server** with `--allow-insecure=uiautomator2:chromedriver_autodownload`, or point `appium:chromedriverExecutableDir` at a folder of drivers. There is no `chromedriverAutodownload` capability.
- **App state.** `ResetApp`, `CloseApp` and `LaunchApp` are gone with the removed `/appium/app/*` routes. In order: a fresh driver per fixture (`appium:noReset` false); `mobile: clearApp` on an emulator or simulator; `TerminateApp` then `ActivateApp` for a cold start.

## Rules

The standards this skill's output must meet are the qa-dotnet rule files, not a list here: `automation.md` and `mobile-ui.md`. Read the project's copy in `.claude/rules/qa-dotnet/`, or the plugin's in `qa/dotnet/skills/rules/` when the project has not installed them (`/qa-dotnet:rules` does). Where they and this skill's recipes disagree, the rule files win.

## Conventions

- On iOS `id`, `name` and `accessibility id` are synonyms over the element's `name`. `IsTestIdVisible` returns `false` when the element is not displayed within the timeout and lets anything else through.
- Flows live in a sub-namespace; repeating items are components scoped to a parent `AppiumElement`.
- Tests extend `BaseMobileTest`, which provides `Driver`, and are tagged with `[Category]`. `Assert.Multiple` only for several fields after one action. Different Android and iOS copy is two platform-scoped expectations, never an `OR`.
- `BaseAppiumPage.Wait` builds a 10 s `WebDriverWait`.
- What `BaseMobileTest` keeps on failure, and where: `qa/dotnet/skills/evidence-capture/references/appium.md`.

## Generation steps

1. Confirm the screen, platforms, landmark, elements with rungs, actions and destinations.
2. For each element with no test id, record it in `missing-testids.md`; do not silently fall back to XPath.
3. Write `AppiumTests/Pages/<Screen>Page.cs` from `assets/page_template.cs`: constants, `VerifyPageLoaded`, intent actions, and a scoped component for each repeating group.
4. Stub missing destination pages; write the test with one `[Test]` per scenario.
5. Run `PLATFORM=android dotnet test AppiumTests` and expect zero failures. For a remote session, `curl -s http://127.0.0.1:4723/status` answers and `appium driver list --installed` lists the driver.

A visible element missing from the page source is usually an accessibility, app-state, active-app (a system alert) or native-versus-WebView problem; fix that before the locator. For doctor failures and driver questions the Appium docs tools (`mcp__appium-mcp__appium_documentation_query`, `mcp__appium-mcp__appium_skills`, on when `APPIUM_MCP_DOCS_ENABLED=true`) answer from the official docs.

## Handoffs

- Selectors on the live app → `qa/dotnet/skills/mobile-screen-explorer`
- A class from an inventory → `qa/dotnet/skills/mobile-screen-objects`
- POM architecture → `qa/dotnet/skills/page-object-design`
- Test data → `qa/dotnet/skills/test-data-builder`
- Failure evidence → `qa/dotnet/skills/evidence-capture`
- Allure → `qa/reporting/dotnet/skills/test-reports`
- Cloud farms → `qa/dotnet/skills/device-cloud`
- Review → `qa/dotnet/skills/ui-test-author/review`
- Formal test cases → the `qa-test-case-designer` agent

## Cross-references

- Java sibling (TestNG + `io.appium:java-client` 11) → `qa/java/skills/ui-test-author/appium`
- TypeScript sibling (WebdriverIO 10 + `@wdio/appium-service`) → `qa/typescript/skills/ui-test-author/appium`
- Web UI (.NET) → `qa/dotnet/skills/ui-test-author/selenium`, `qa/dotnet/skills/ui-test-author/playwright`
- Cloud device grid (BrowserStack / Sauce / Device Farm) → `qa/dotnet/skills/device-cloud`
- Network capture for non-Playwright stacks → `qa/dotnet/skills/network-mocking`
