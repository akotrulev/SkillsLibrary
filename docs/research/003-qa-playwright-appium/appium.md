# Appium research: current versions, Appium 3, evidence capture, scoped lookup (as of 2026-10-10)

Method: versions come from the npm registry, Maven Central and the NuGet API, queried on 2026-10-10. API names come from the client and driver source trees (shallow clones of `appium/java-client`, `appium/dotnet-client`, `appium/appium` (master and the `appium4` branch), `appium/appium-uiautomator2-driver`, `appium/appium-xcuitest-driver`, `webdriverio/webdriverio`, `microsoft/playwright@v1.64.0`) and their docs. A claim that could not be confirmed from a primary source is marked **UNVERIFIED**.

---

## 0. Headline findings (read first)

- **Three clients shipped a major release in the last four weeks.** All three agents need a version bump, not only an audit:
  - `io.appium:java-client` **11.0.0** (2026-10-07). AppiumDriver is no longer a `RemoteWebDriver`, the client depends on `selenium-api` only, TouchAction is removed, and Appium 3 is the minimum server.
  - `Appium.WebDriver` **9.0.0** (2026-09-16). The only breaking change is strong-name signing.
  - WebdriverIO **10.0.x** (10.0.0 on 2026-10-05). It requires **Appium 3** and Node **22.19+**, makes `$` strict, and removes `touchAction`.
- **Appium server 3.8.0 is latest.** **Appium 4.0.0-beta.4** exists (2026-10-09, npm `beta` tag) with a published 3→4 migration guide on the `appium4` branch. Do not target it yet.
- **Allure Java 3.0.0** (2026-09-11) renamed `Allure.addAttachment(...)` to `Allure.attachment(...)` and moved to a Java 17 baseline. **NUnit 5.0.0** shipped on 2026-09-27; there, `Assert.ThrowsAsync` returns a `Task` that must be awaited.
- **Google is deprecating `UiSelector`, `UiScrollable`, `UiObject` and `UiCollection`.** The UiAutomator2 README warns that this will invalidate every `-android uiautomator` locator. The agents should stop teaching `UiSelector().childSelector()` as the main scoping tool and use element-scoped `findElement` instead.
- **There is an official Appium MCP server, `appium-mcp`** (npm 1.95.8, repo `appium/appium-mcp`), listed on appium.io's Tools page. WebdriverIO also ships `@wdio/mcp` 4.0.0 and the `wdio session` CLI.

---

## 1. Version table

| Component | Latest (2026-10-10) | Published | Notes | Source |
|---|---|---|---|---|
| Appium server (`appium`) | **3.8.0** | 2026-09-24 | engines `node: ^20.19.0 \|\| ^22.12.0 \|\| >=24.0.0`, `npm >=10` | https://registry.npmjs.org/appium/latest · https://github.com/appium/appium/blob/master/packages/appium/CHANGELOG.md |
| Appium server, next major | 4.0.0-beta.4 (npm `beta`) | 2026-10-09 | engines `node: ^22.22.2 \|\| ^24.15.0 \|\| >=26.0.0`; prerelease | https://registry.npmjs.org/appium · https://github.com/appium/appium/blob/appium4/packages/appium/docs/en/guides/migrating-3-to-4.md |
| `appium-uiautomator2-driver` | **8.7.0** | 2026-09-14 | peer `appium ^3.0.0-rc.2`; ESM-only since 8.0.0; Android API 26+ since 6.0.0 | https://registry.npmjs.org/appium-uiautomator2-driver · https://github.com/appium/appium-uiautomator2-driver/blob/master/CHANGELOG.md |
| `appium-xcuitest-driver` | **12.16.0** | 2026-10-08 | peer `appium ^3.0.0-rc.2`; ESM-only since 12.0.0 | https://registry.npmjs.org/appium-xcuitest-driver · https://github.com/appium/appium-xcuitest-driver/blob/master/CHANGELOG.md |
| `appium-espresso-driver` | **9.3.6** | 2026-09-21 | peer `appium ^3.0.0-rc.2` | https://registry.npmjs.org/appium-espresso-driver |
| `appium-flutter-driver` (Appium team/community) | 4.0.0 | 2026-08-25 | peer `appium ^3.0.0` | https://registry.npmjs.org/appium-flutter-driver |
| `appium-flutter-integration-driver` (community, AppiumTestDistribution) | 2.0.3 | 2025-10-17 | peer `appium ^3.0.0` | https://registry.npmjs.org/appium-flutter-integration-driver |
| `appium-mac2-driver` / `appium-windows-driver` / `appium-wincore-driver` | 4.3.6 / 6.3.1 / 3.1.2 | — / — / 2026-10-07 | Appium 4 replaces the `windows` shortcut with `wincore` | npm registry; migrating-3-to-4.md |
| `@appium/images-plugin` | 5.0.1 | 2026-09-24 | `appium plugin install images`, then `--use-plugins=images` | https://registry.npmjs.org/@appium/images-plugin |
| Appium Inspector (standalone) | **v2026.9.2** | (tag) | plugin form `appium-inspector-plugin` 2026.9.2 (2026-09-20), served at the server's `/inspector` path | `git ls-remote --tags https://github.com/appium/appium-inspector` · https://registry.npmjs.org/appium-inspector-plugin |
| `appium-mcp` (official MCP server) | **1.95.8** | 2026-10-10 | Node >=22; repo `github.com/appium/appium-mcp` | https://registry.npmjs.org/appium-mcp · https://github.com/appium/appium-mcp |
| `io.appium:java-client` | **11.0.0** | 2026-10-07 | depends on `selenium-api [4.50.0, 5.0)` only; bytecode target Java 11 | https://repo1.maven.org/maven2/io/appium/java-client/maven-metadata.xml · https://github.com/appium/java-client/releases/tag/v11.0.0 |
| `io.appium:java-client-selenium-bridge` (optional, new) | 11.0.0 | 2026-10-07 | gives `RemoteWebDriver` and Selenium BiDi interop | https://repo1.maven.org/maven2/io/appium/java-client-selenium-bridge/maven-metadata.xml |
| Selenium Java (latest) | 4.51.0 | 2026-10-09 (metadata) | java-client 11 needs **>= 4.50.0** | https://repo1.maven.org/maven2/org/seleniumhq/selenium/selenium-java/maven-metadata.xml |
| `Appium.WebDriver` (NuGet) | **9.0.0** | 2026-09-16 | nuspec: `Selenium.WebDriver >= 4.46.0`; netstandard2.0; strong-name signed | https://api.nuget.org/v3-flatcontainer/appium.webdriver/9.0.0/appium.webdriver.nuspec · https://github.com/appium/dotnet-client/releases/tag/v9.0.0 |
| `Selenium.WebDriver` (NuGet, latest) | 4.51.0 | — | | https://api.nuget.org/v3-flatcontainer/selenium.webdriver/index.json |
| `webdriverio` / `@wdio/cli` / `@wdio/appium-service` | **10.0.2** | 2026-10-08 | engines `node >=22.19.0`; last 9.x is 9.32.0 (2026-09-20) | https://registry.npmjs.org/webdriverio · https://webdriver.io/blog/2026/10/05/webdriverio-v10-release |
| `@wdio/allure-reporter` | 10.0.1 | 2026-10-07 | targets Allure 3 (`allure-js-commons ^3.10.0`) | https://registry.npmjs.org/@wdio/allure-reporter |
| `@wdio/mcp` | 4.0.0 | 2026-10-08 | WebdriverIO MCP server for browsers and Appium | https://registry.npmjs.org/@wdio/mcp |
| `io.qameta.allure:allure-testng` | **3.0.0** | 2026-09-11 | Java 17 baseline; `Allure.attachment(...)` API | https://repo1.maven.org/maven2/io/qameta/allure/allure-testng/maven-metadata.xml · https://github.com/allure-framework/allure-java/releases/tag/3.0.0 |
| `org.testng:testng` | 7.12.0 | — | | https://repo1.maven.org/maven2/org/testng/testng/maven-metadata.xml |
| `Allure.NUnit` | 2.15.0 (3.0.0-preview.1 is xUnit v3/MTP-focused) | 2026-04-28 | references NUnit 3.13.3 as minimum; **NUnit 5 compatibility UNVERIFIED** | https://github.com/allure-framework/allure-csharp/releases |
| `NUnit` | **5.0.0** | 2026-09-27 | drops the .NET 6 target; `Assert.ThrowsAsync` returns a `Task` | https://docs.nunit.org/articles/nunit/release-notes/framework.html |
| Playwright | **1.64.0** | 2026-10-07 | `_android` is still **experimental**, JS only | https://registry.npmjs.org/playwright · https://playwright.dev/docs/api/class-android |

**Node floors.** Appium 3 requires `^20.19.0 || ^22.12.0 || >=24.0.0`, WDIO 10 requires `>=22.19.0`, `appium-mcp` requires `>=22`, and Appium 4 (beta) requires `^22.22.2 || ^24.15.0 || >=26`. The library's Node 24 default satisfies all of them. Node 20 technically satisfies Appium 3 but is EOL and fails WDIO 10.

---

## 2. Appium 2 → 3 (and client) migration

### 2.1 Server breaking changes (source: https://appium.io/docs/en/latest/guides/migrating-2-to-3/ — mirrored at `packages/appium/docs/en/guides/migrating-2-to-3.md`)

- **Node floor:** `20.19.0` (`^20.19.0 || ^22.12.0 || >=24.0.0`), npm `>=10`.
- **Deprecated endpoints removed.** Endpoints from the old JSONWP and MJSONWP protocols, and the `/appium/...` helpers, were removed. Each one now maps either to a W3C endpoint or to a driver `mobile:` execute method. Notable mappings:
  - App lifecycle:
    - `appium/app/background` → `mobile: backgroundApp`
    - `appium/app/close` → `mobile: terminateApp`
    - `appium/app/launch` → `mobile: launchApp` (iOS) or `mobile: activateApp` / `mobile: startActivity` (Android)
    - `appium/app/reset` → `mobile: clearApp`
    - `appium/app/strings` → `mobile: getAppStrings`
  - Android device queries:
    - `appium/device/current_activity` → `mobile: getCurrentActivity`
    - `current_package` → `mobile: getCurrentPackage`
    - `system_bars` → `mobile: getSystemBars` (Android) or `mobile: deviceScreenInfo` (iOS)
  - Keys:
    - `press_keycode` and `long_press_keycode` → `mobile: pressKey`
    - `keyevent` → `mobile: pressKey` (Android) or `mobile: keys` (iPadOS)
  - Connectivity:
    - `toggle_wifi`, `toggle_data` and `toggle_airplane_mode` → `mobile: setConnectivity`
    - `toggle_location_services` → `mobile: toggleGps`
  - Lock, unlock and clipboard:
    - `lock`, `unlock` and `is_locked` → `mobile: lock`, `mobile: unlock` and `mobile: isLocked`
    - `get_clipboard` and `set_clipboard` → `mobile: getClipboard` and `mobile: setClipboard`
  - Biometrics:
    - `finger_print` → `mobile: fingerprint` (the guide spells it `fingerPrint`; the UiA2 README spells it `mobile: fingerprint`)
    - `simulator/touch_id` → `mobile: sendBiometricMatch`
    - `simulator/toggle_touch_id_enrollment` → `mobile: enrollBiometric`
  - Performance data:
    - `getPerformanceData` → `mobile: getPerformanceData`
    - `performanceData/types` → `mobile: getPerformanceDataTypes`
  - Logs, element screenshots and scripts:
    - `POST /log` → `POST /se/log`
    - `GET /log/types` → `GET /se/log/types`
    - `GET /screenshot/:elementId` → `GET /element/:elementId/screenshot`
    - `POST /execute` → `/execute/sync`
  - **All touch routes** (`touch/click`, `touch/perform`, `touch/multi/perform`, `touch/scroll`, `touch/flick`, `touch/longclick`, `touch/down`, `touch/up`, `touch/move`) → W3C Actions (`POST /actions`) or the driver gesture methods: `mobile: clickGesture`, `longClickGesture`, `scrollGesture`, `swipeGesture` and `flingGesture` (UiA2); `mobile: tap`, `touchAndHold`, `scroll` and `swipe` (XCUITest).
  - **`appium/start_recording_screen` and `stop_recording_screen` are "Moved to drivers".** The XCUITest, UiA2, Espresso, Mac2 and Windows drivers still serve them. The execute-method alternatives are `mobile: startMediaProjectionRecording` (Android) and `mobile: startXCTestScreenRecording` (iOS). So `startRecordingScreen()` in all three clients keeps working against current drivers.
- **Modified endpoints accept W3C parameters only:**
  - `POST /session` accepts only `capabilities` (`desiredCapabilities` and `requiredCapabilities` are gone)
  - element value takes `text` (not `value`)
  - timeouts take `script`, `pageLoad` and `implicit` (not `type`/`ms`)
  - `POST /window` takes `handle`
- **Feature flags must be scoped.** Use `--allow-insecure=<driver>:<feature>` or `*:<feature>`; the old unscoped form throws. Example: `appium --allow-insecure=uiautomator2:adb_shell`. Server-scope features such as `session_discovery` need `*:`. `--relaxed-security` is unchanged. Appium 3.8.0 matches prefixes by `automationName`, case-insensitively.
- **Session discovery:**
  - `GET /sessions` → `GET /appium/sessions`, which requires the `*:session_discovery` flag.
  - Appium Inspector "Attach to Session" needs Inspector `>= 2025.3.1`.
- **Unzip logic moved into drivers**, so keep drivers current. **Express 5** internally.
- **Install and setup:**
  - Install with `npm install -g appium` (optionally run `appium setup reset` first).
  - `appium setup` with no argument means `mobile`, which installs `uiautomator2`, `xcuitest` (on macOS) and `espresso`, plus the `images` and `inspector` plugins.
  - The other presets are `appium setup browser|desktop|reset`.

  Sources: `reference/cli/setup.md`, https://appium.io/docs/en/latest/reference/cli/setup/
- **Driver updates:**
  - `appium driver update <name> --unsafe` allows major-version updates; `appium driver update installed` updates everything.
  - `appium driver list --installed --updates` shows what is outdated. `appium driver doctor uiautomator2` checks prerequisites.

  Source: `reference/cli/extensions.md`

### 2.2 Appium 3 → 4 preview (for awareness only; beta)

Source: https://github.com/appium/appium/blob/appium4/packages/appium/docs/en/guides/migrating-3-to-4.md

- Node `^22.22.2 || ^24.15.0 || >=26`.
- All packages are ESM-only.
- Removed flags:
  - `--nodeconfig` (use the Grid 4 relay instead)
  - `--allow-cors` (use `--allow-insecure=*:cors` instead)
- The default `--log-level` becomes `info`.
- CLI output moves to stdout.
- Timeout errors return HTTP 500.
- Removed endpoints:
  - the IME endpoints
  - legacy `location`
  - `network_connection`
  - `GET /session/:id`
- The `appium:eventTimings` capability is removed.
- The `windows` driver shortcut is replaced by `wincore` (`appium-wincore-driver`).
- New `--app-url-rules` flag.
- Client implications: java-client 11's README promises support only for the current and previous server majors, and WDIO 10 states it requires Appium 3.

### 2.3 Driver majors since Appium 3

- **UiA2:**
  - 5.0.0 (2025-08-19): Appium 3, Node 20.19.
  - 6.0.0: Android API levels below 26 dropped.
  - 7.0.0: `mobile: listApps` output format now matches XCUITest's.
  - 8.0.0 (2026-06-26): ESM-only.

  Source: https://github.com/appium/appium-uiautomator2-driver/blob/master/CHANGELOG.md
- **XCUITest:**
  - 10.0.0 (2025-08-19): Appium 3.
  - 11.0.0 (2026-04-14):
    - Removed `appium:launchWithIDB`, `mobile: startPcap`/`stopPcap` and `mobile: listXCTestsInTestBundle`.
    - Removed the capabilities `appInstallStrategy`, `calendarAccessAuthorized`, `useSimpleBuildTest`, `waitForQuiescence` and `simpleIsVisibleCheck`. Tune idling with `appium:waitForIdleTimeout` instead.
    - BiDi event `appium.contextUpdated` → `appium:xcuitest.contextUpdated`.
  - 12.0.0 (2026-07-23): ESM-only.

  Source: https://github.com/appium/appium-xcuitest-driver/blob/master/CHANGELOG.md
- **Espresso:** Appium 3; Android API below 26 dropped; AGP 8.x dropped and Kotlin 2.3.20 is the default; listApps format change; ESM-only.

  Source: https://github.com/appium/appium-espresso-driver/blob/master/CHANGELOG.md

### 2.4 Java client: 9 → 10 → 11 (exact API changes)

- **v8/v9 (history, still relevant for audits).** Source: https://github.com/appium/java-client/blob/master/docs/v8-to-v9-migration-guide.md
  - `MobileElement` was removed in v8.
  - `MobileBy` was removed in v9; use `AppiumBy`.
  - The old capability interfaces were removed in v9: `MobileCapabilityType`, `AndroidMobileCapabilityType` and `IOSMobileCapabilityType`. Use `UiAutomator2Options`, `XCUITestOptions` and `EspressoOptions` (`io.appium.java_client.android.options.*`, `io.appium.java_client.ios.options.*`).
  - v9 requires Java 11+.
  - `launchApp`, `resetApp` and `closeApp` were removed in v9.
- **v10.** Selenium 4.35+ is required, and the deprecated `Location`/`LocationContext` usages were removed; use `io.appium.java_client.Location`. Source: https://github.com/appium/java-client/blob/master/docs/v9-to-v10-migration-guide.md
- **v11 (2026-10-07).** Sources: https://github.com/appium/java-client/blob/master/docs/v10-to-v11-migration-guide.md and https://github.com/appium/java-client/releases/tag/v11.0.0
  - **Dependencies:** depends on `selenium-api` only (>= 4.50.0). You must **declare `selenium-support` yourself** for `WebDriverWait`, `ExpectedConditions` and `EventFiringDecorator`, and `selenium-remote-driver` for `RemoteWebDriver`.
  - **Driver and element types:** `AppiumDriver extends io.appium.java_client.remote.AppiumRemoteWebDriver` and is **not a `RemoteWebDriver`**. Elements are `io.appium.java_client.remote.AppiumWebElement`, not `RemoteWebElement`. Code typed against `WebDriver`/`WebElement` needs no change. Casts to `RemoteWebDriver` break; use `SeleniumBridge.asRemoteWebDriver(driver)` from the optional `java-client-selenium-bridge` artifact.
  - **BiDi:** `HasBiDi`, `getBiDi()` and `maybeGetBiDi()` were removed; use the bridge.
  - **Touch API removed:** `TouchAction`, `MultiTouchAction`, `PerformsTouchActions`, `AndroidTouchAction`, `IOSTouchAction` and `io.appium.java_client.touch.*`. Use W3C `PointerInput`/`Sequence` with `driver.perform(List.of(seq))`, or `mobile:` gestures.
  - **Removed helpers:** `AppiumFunction`, `AndroidMobileCommandHelper`, `IOSMobileCommandHelper`, `CanRememberExtensionPresence` and the deprecated `MobileCommand` constants. Driver interface methods (`installApp`, `lockDevice`, ...) now call **only** `mobile:` extensions, so server `UnsupportedCommandException` is no longer swallowed.
  - **Page factory and waits:** the page factory (`FindBy`, `FindBys`, `FindAll`, `CacheLookup`, `PageFactory`) and the `FluentWait` engine were vendored into `io.appium.java_client.support`. `PageFactory.initElements(driver, page)` was removed; use `PageFactory.initElements(new AppiumFieldDecorator(driver), page)`.
  - **Config and executor:** `ClientConfig` → `AppiumClientConfig.defaultConfig()`, and `HttpCommandExecutor` → `AppiumCommandExecutor`.
  - **Local service:** `AppiumDriverLocalService` and `AppiumServiceBuilder` are no longer `DriverService` types.
  - **Still working:** `manage().logs()`, shadow roots and virtual authenticators.
  - **Migration tooling:** an OpenRewrite recipe, `io.appium.java_client.MigrateToV11`, fixes most imports, and `FindV11Breakages` marks the rest. Run it **before** bumping the version.
- **Compatibility matrix (README):**

  | java-client | Selenium |
  |---|---|
  | 11.0.0 | 4.50.0 |
  | 10.1.1 | 4.42–4.49 |
  | 10.0.0 | 4.35–4.39 |

  Source: https://github.com/appium/java-client#compatibility-matrix

### 2.5 .NET client: 5 → 6 → 7 → 8 → 9

| Version | Released | Changes | Source |
|---|---|---|---|
| 5.0 | — | Selenium 4 rewrite; `AppiumWebElement` renamed `AppiumElement`; `FindElementBy*` helpers removed in favour of `FindElement(MobileBy.X(...))`; default base path `/` (Appium 2); TouchAction/MultiAction deprecated | https://github.com/appium/dotnet-client/releases/tag/v5.0.0 |
| 6.0.0 | 2024-10-19 | **TouchAction and MultiAction methods removed** (W3C `PointerInputDevice` / `ActionSequence` / `driver.PerformActions`); target becomes netstandard2.0; Newtonsoft replaced by System.Text.Json; Selenium.Support dropped | https://github.com/appium/dotnet-client/releases/tag/v6.0.0 |
| 7.0.0 | 2024-12-27 | Lock, IsLocked and Unlock use `mobile:` commands | https://github.com/appium/dotnet-client/releases/tag/v7.0.0 |
| **8.0.0** | 2025-05-31 | "use extension commands for deprecated endpoints" (Appium 3 compatibility). Removed `ToggleAirplaneMode`, `ToggleData`, `ToggleWifi`, `SetConnectionType`, `GetConnectionType` (use `mobile: setConnectivity` / `getConnectivity`), `EndTestCoverage`, `StartActivity(WithIntent)` (use `mobile: startActivity`), and the `HideKeyboard` strategy argument | https://github.com/appium/dotnet-client#v8 |
| 8.1.0 | — | Re-added `StartActivity` via the extension; `InstallApp`; Android `StartLogcatBroadcast` | — |
| 8.4.0 | — | iOS `StartSyslogBroadcast` | — |
| **9.0.0** | 2026-09-16 | Strong-name signed (public key token `8b7475dcfe6734d4`); consumers compiled against an unsigned release must rebuild | https://github.com/appium/dotnet-client/releases/tag/v9.0.0 |

**There are no per-driver options classes in .NET.** Use `AppiumOptions`, which has `AutomationName`, `DeviceName`, `App` and `PlatformVersion` properties plus `AddAdditionalAppiumOption(name, value)`. `PlatformName` comes from the Selenium `DriverOptions` base. Source: `src/Appium.Net/Appium/AppiumOptions.cs`.

### 2.6 WebdriverIO 9 → 10 (mobile-relevant)

Sources: https://webdriver.io/docs/v10-migration (repo `website/docs/v10Migration.md`) and https://webdriver.io/blog/2026/10/05/webdriverio-v10-release

- **Requirements:**
  - Node 22.19+.
  - **Appium 3 required:** `npm i -D appium@^3` and `appium driver update installed`. `@wdio/appium-service` refuses older servers, and cloud vendors still on Appium 2 force you to stay on WDIO 9.
- **Fallbacks and protocol commands:**
  - Mobile helpers no longer fall back to the removed HTTP endpoints; use `browser.execute('mobile: …', args)` or the WDIO mobile commands.
  - Protocol commands such as `appiumLock` and `touchPerform` are removed, along with the MJSONWP map.
- **Capabilities:** unprefixed `automationName`, `deviceName` and `appiumVersion` no longer select Appium. Use `appium:` prefixes or `appium:options`.
- **Changed command semantics:**
  - `getValue` on mobile now reads the element **property**.
  - `stopRecordingScreen` takes a single options object, e.g. `browser.stopRecordingScreen({ remotePath, method })`.
  - `startActivity` takes only `{ appPackage, appActivity }`.
- **Removed commands:** `touchAction` (`browser` and `element`) and `browser.throttle` are gone. Use `browser.action('pointer', { parameters: { pointerType: 'touch' } })` or `tap`/`swipe`.
- **`$` is strict.** It throws `StrictSelectorError` on more than one match, at every step of a chain (`$(a).$(b)`), mobile selectors included. Opt out per call with `$(sel, { strict: false })` or globally with `strictSelectors: false`.
- **`$$` returns an `ElementArray`.** Use `await $$(sel).length` or `for await`.
- **New features:**
  - Cross-platform mobile commands: `tap`, `swipe`, `longPress`, `dragAndDrop`, `pinch`, `zoom`, `scrollIntoView`, `deepLink`, `getContext`, `switchContext`.
  - The Appium service adds the "Native Mobile Selector Performance Optimizer" (beta, iOS for now), which times XPath selectors and suggests faster replacements.
  - `npx start-appium-inspector` opens Appium Inspector in one step.
  - `wdio session`, a step-by-step CLI for agents.
  - `@wdio/mcp`.
  - Allure 3 support in the Allure reporter.
  - `@wdio/allure-reporter`'s `addEnvironment()` was removed; use `reportedEnvironmentVars`.

### 2.7 Appium 2 → 3 migration checklist (all three stacks)

1. [ ] Upgrade Node to 22.19+ (24 LTS recommended) and npm to 10+. Run `node -v` in CI images.
2. [ ] Run `npm i -g appium@3` (or `npm i -D appium@^3` in a WDIO project). Optionally run `appium setup reset`, then `appium setup` (mobile preset).
3. [ ] Run `appium driver update installed --unsafe` (major bumps), then `appium driver list --installed --updates`. Target UiA2 8.x, XCUITest 12.x and Espresso 9.x.
4. [ ] Run `appium driver doctor uiautomator2` and `appium driver doctor xcuitest`.
5. [ ] Rewrite every `--allow-insecure=foo` as `--allow-insecure=<driver>:foo` or `*:foo`. Session discovery needs `*:session_discovery`, and server logs need `*:get_server_logs` (or `uiautomator2:get_server_logs`).
6. [ ] Remove `desiredCapabilities`, `requiredCapabilities` and JSONWP `value`/`type`/`ms` payloads, which come from hand-rolled HTTP clients.
7. [ ] Replace every removed `/appium/...` and `touch/*` call with W3C Actions or a `mobile:` method (see 2.1).
8. [ ] **Java:**
   - Move to java-client 11 and Selenium 4.50+.
   - Add the `selenium-support` dependency if `WebDriverWait`/`ExpectedConditions` are used.
   - Run the `MigrateToV11` OpenRewrite recipe **before** the bump.
   - Delete `TouchAction`; replace `RemoteWebDriver` casts and parameters with `WebDriver` or `SeleniumBridge`.
   - Replace `PageFactory.initElements(driver, this)` with `PageFactory.initElements(new AppiumFieldDecorator(driver), this)`.
   - Replace `MobileCommand` usages with `executeScript("mobile: …", Map.of(...))`.
   - Note that Allure Java 3 renames `addAttachment` to `attachment`.
9. [ ] **.NET:**
   - Move to Appium.WebDriver 9.0.0 and Selenium.WebDriver 4.46+ (pin explicitly; latest is 4.51.0).
   - Rebuild everything (strong-name identity changed).
   - Remove `Toggle*`/`SetConnectionType` calls; use `ExecuteScript("mobile: setConnectivity", …)`.
   - If moving to NUnit 5, `await Assert.ThrowsAsync(...)`.
10. [ ] **WDIO:**
    - Move to `webdriverio`, `@wdio/cli` and `@wdio/appium-service` 10.0.x.
    - Prefix all Appium capabilities with `appium:`.
    - Fix every `StrictSelectorError` by narrowing the selector or scoping it to a container.
    - Change `stopRecordingScreen(...)` to an options object.
    - Replace `touchAction`.
11. [ ] Update Appium Inspector to v2026.9.2 (or install the plugin with `appium plugin install inspector`, then `--use-plugins=inspector`).
12. [ ] **Device cloud:** confirm the vendor offers an Appium 3 image before bumping WDIO to 10 or java-client to 11.
    - **UNVERIFIED** for BrowserStack: its public version page lists 2.x only.
    - **UNVERIFIED** for Sauce Labs: its migration page shows `latest` = 2.13.1 and may be stale.
    - TestingBot documents Appium 3 support.

---

## 3. Screenshots

| | Java (java-client 11) | C# (Appium.WebDriver 9) | WebdriverIO 10 (TS) |
|---|---|---|---|
| Full screen | `byte[] png = driver.getScreenshotAs(OutputType.BYTES);` (`AppiumRemoteWebDriver implements TakesScreenshot`) | `Screenshot s = driver.GetScreenshot(); s.AsByteArray; s.SaveAsFile(path);` | `await browser.saveScreenshot('./shot.png')` → `Buffer`; `await browser.takeScreenshot()` → base64 `string` |
| Element | `byte[] png = element.getScreenshotAs(OutputType.BYTES);` (`AppiumWebElement implements TakesScreenshot`) | `((ITakesScreenshot)element).GetScreenshot()` (Selenium `WebElement` contract) | `await $(sel).saveScreenshot('./el.png')`; protocol `browser.takeElementScreenshot(elementId)` |
| All displays (Android 10+) | `driver.executeScript("mobile: screenshots", Map.of())` → map of `{id, name, isDefault, payload(base64 PNG)}` | `driver.ExecuteScript("mobile: screenshots", new Dictionary<string, object>())` | `await browser.execute('mobile: screenshots', {})` |
| Viewport without status bar (iOS) | `mobile: viewportScreenshot` (the driver doc marks it **"Unreliable"** and recommends `getScreenshot`) | same | same |

- The W3C element screenshot route is `GET /session/:id/element/:elementId/screenshot`. The legacy `/screenshot/:elementId` was removed in Appium 3. Source: migrating-2-to-3.md.
- `mobile: screenshots` (UiA2) takes a `displayId` argument, which is a physical or virtual ID from `mobile: listDisplays`. Source: https://github.com/appium/appium-uiautomator2-driver#mobile-screenshots
- `mobile: viewportScreenshot` (XCUITest): https://appium.github.io/appium-xcuitest-driver/latest/reference/execute-methods/#mobile-viewportscreenshot
- Image comparison against screenshots: see section 6 (images plugin).

**Attaching to Allure**

- **Java, Allure 3.0.0.** Source: allure-java `allure-java-commons/src/main/java/io/qameta/allure/Allure.java@3.0.0` and `AttachmentOptions.java`.
  - `Allure.attachment(String name, String type, InputStream content, AttachmentOptions options)`, with `AttachmentOptions.withFileExtension("png")`.
  - Also `Allure.attachment(name, type, String content)`.
  - Allure 2.35.x used `Allure.addAttachment(name, type, InputStream, fileExtension)`. **That method does not exist in 3.0.0.**
  - The `@Attachment` annotation still exists.
- **C#, Allure.Net.Commons 2.15.0.** Source: allure-csharp `src/Allure.Net.Commons/AllureApi.cs@2.15.0`.
  - `AllureApi.AddAttachment(string name, string type, byte[] content, string fileExtension = "")`
  - `AllureApi.AddAttachment(string name, string type, string path)`
  - `AllureApi.AddAttachment(string path, string? name = null)`
  - The path overload derives the extension with `Path.GetExtension`, which includes the dot. Pass `".png"`.
- **WDIO.** Source: https://github.com/webdriverio/webdriverio/blob/main/packages/wdio-allure-reporter/README.md
  - `import allureReporter from '@wdio/allure-reporter'`, then `allureReporter.addAttachment(name, content, type?)`.
  - `browser.takeScreenshot()` is **auto-attached** when the reporter option `disableWebdriverScreenshotsReporting: false` is set.

---

## 4. Screen recording

### 4.1 Client APIs (exact spellings)

| | Java | C# | WebdriverIO |
|---|---|---|---|
| Start | `driver.startRecordingScreen()` / `driver.startRecordingScreen(opts)` (`CanRecordScreen`, implemented by `AndroidDriver` and `IOSDriver`) | `driver.StartRecordingScreen()` / `driver.StartRecordingScreen(IScreenRecordingOptions)` (on `AppiumDriver`) | `await browser.startRecordingScreen(options?)` |
| Stop | `String b64 = driver.stopRecordingScreen()` / `stopRecordingScreen(opts)` | `string b64 = driver.StopRecordingScreen()` / `StopRecordingScreen(opts)` | `const b64 = await browser.stopRecordingScreen(options?)` (v10: single options object) |
| Save helper | — (decode with `Base64.getDecoder()`) | — (`Convert.FromBase64String`) | `await browser.saveRecordingScreen('./video.mp4')` → `Buffer` (stops and saves) |
| Android options | `new AndroidStartScreenRecordingOptions()` or `AndroidStartScreenRecordingOptions.startScreenRecordingOptions()`, then `.withTimeLimit(Duration)`, `.withBitRate(int)`, `.withVideoSize("1280x720")`, `.enableBugReport()`, `.enableForcedRestart()` / `.disableForcedRestart()`, `.withUploadOptions(ScreenRecordingUploadOptions)` | `AndroidStartScreenRecordingOptions.GetAndroidStartScreenRecordingOptions()`, then `.WithTimeLimit(TimeSpan)`, `.WithBitRate(int)`, `.WithVideoSize(string)`, `.EnableBugReport()`, `.EnableForcedRestart()`, `.WithUploadOptions(...)` | plain object: `{ timeLimit, bitRate, videoSize, bugReport, forceRestart }` |
| iOS options | `new IOSStartScreenRecordingOptions()`, then `.withVideoType(String)`, `.withVideoQuality(VideoQuality.LOW\|MEDIUM\|HIGH\|PHOTO)`, `.withFps(int)`, `.withVideoScale(String)`, `.withTimeLimit(Duration)`, `.withVideoFilters(String)` | `IOSStartScreenRecordingOptions.GetIosStartScreenRecordingOptions()`, then `.WithVideoType(...)`, `.WithVideoQuality(VideoQuality.LOW…)`, `.WithVideoFps(string)`, `.WithVideoScale(string)`, `.WithPixelFormat(string)`, `.WithVideoFilter(string)`, `.WithTimeLimit(TimeSpan)` | `{ videoType, videoQuality, videoFps, videoScale, pixelFormat, videoFilters, timeLimit, forceRestart }` |
| Stop options | `AndroidStopScreenRecordingOptions` / `IOSStopScreenRecordingOptions` (upload: `remotePath`, `user`, `pass`, `method`, …) | `AndroidStopScreenRecordingOptions` / `IOSStopScreenRecordingOptions` | `{ remotePath, user, pass, method, headers, fileFieldName, formFields }` |

Sources:
- Java: `src/main/java/io/appium/java_client/screenrecording/CanRecordScreen.java`, `android/AndroidStartScreenRecordingOptions.java`, `ios/IOSStartScreenRecordingOptions.java`, `screenrecording/BaseStartScreenRecordingOptions.java` (java-client master = 11.0.0).
- .NET: `src/Appium.Net/Appium/AppiumDriver.cs` (lines ~534–550), `Android/AndroidStartScreenRecordingOptions.cs`, `iOS/IOSStartScreenRecordingOptions.cs`, `ScreenRecording/BaseStartScreenRecordingOptions.cs`.
- WDIO: `packages/wdio-protocols/src/protocols/appium.ts`, `packages/webdriverio/src/commands/browser/saveRecordingScreen.ts`, v10Migration.md.
- .NET has `EnableForcedRestart()` but **no** `DisableForcedRestart()`.

### 4.2 Driver-level behaviour and limits

- **Android `startRecordingScreen` (adb `screenrecord`):**
  - Each `screenrecord` chunk is capped at **180 s**.
  - `timeLimit` may be **1–1800 s**. Above 180 s, the driver records successive 3-minute chunks and merges them with **ffmpeg on the Appium host**. If ffmpeg is not on PATH, the stop call fails with "ffmpeg utility is not available in PATH". (The Java doc says only the last chunk is returned in that case; the driver source shows an error path.)
  - Options: `videoSize`, `timeLimit`, `bugReport` (API 27+ overlay), `bitRate`, `forceRestart`.

  Sources: `appium-android-driver@14.2.3 lib/commands/recordscreen.ts` (`MAX_RECORDING_TIME_SEC = 180`, `MAX_TIME_SEC = 1800`, ffmpeg merge); Java javadoc in `AndroidStartScreenRecordingOptions.withTimeLimit`.
- **Android `mobile: startMediaProjectionRecording`:**
  - Android 10+, via the Appium Settings helper; records video and audio.
  - Args: `resolution` (one of `1920x1080`, `1280x720`, `720x480`, `320x240`, `176x144`), `maxDurationSec` (default **900**), `priority` (`high`/`normal`/`low`), `filename` (`.mp4`).
  - Returns `true` if started and `false` if one is already running.
  - Stop with `mobile: stopMediaProjectionRecording` (`remotePath`, `user`, `pass`, `method`, `headers`, `fileFieldName`, `formFields`, `uploadTimeout`), which returns base64. Check status with `mobile: isMediaProjectionRecordingRunning`.

  Source: https://github.com/appium/appium-uiautomator2-driver#mobile-startmediaprojectionrecording
- **iOS `startRecordingScreen`:**
  - Simulator since Xcode 9, real device since iOS 11.
  - **Requires `ffmpeg`** on the Appium host (`brew install ffmpeg`); no audio.
  - Calling it while a recording is running force-stops it and starts a new one.
  - `timeLimit` default 180 s, max **4200 s**. Defaults: fps 10, quality medium, vcodec mjpeg.
  - The execute-method equivalent is `mobile: startScreenRecording` / `mobile: stopScreenRecording`, with the same options as top-level keys.

  Sources: https://appium.github.io/appium-xcuitest-driver/latest/reference/commands/#startrecordingscreen; `lib/commands/recordscreen.ts` (`MAX_RECORDING_TIME_SEC = 4200`).
- **iOS `mobile: startXCTestScreenRecording`:**
  - Native XCTest recording; Xcode 15 / iOS 17+. The driver docs call it the best quality for the lowest performance cost.
  - Arg: `fps` (default 24). Returns `{uuid, fps, codec, startedAt}`. It is a no-op if a recording is already running.
  - Stop with `mobile: stopXCTestScreenRecording` (upload args as above), which returns `payload` (base64 **.mov**). Query with `mobile: getXCTestScreenRecordingInfo`.
  - On real devices, automatic deletion needs iOS 18+ and `appium-ios-remotexpc >= 0.44.0`; otherwise the `xctest_screen_record` security flag is needed.

  Source: https://appium.github.io/appium-xcuitest-driver/latest/reference/execute-methods/#mobile-startxctestscreenrecording
- **Parallel recording:** give each parallel session a unique `appium:mjpegServerPort` (UiA2 README, "Parallel Tests").
- **Base64 limit:** if the media is too big for the server's memory, the stop call throws. Use `remotePath` upload for long runs (driver docs).

### 4.3 Pattern: start in setup, stop in teardown, keep only on failure

- Start recording in the per-test setup hook with `forceRestart` enabled, so a leftover recording from a crashed test never leaks into this one.
- Stop recording in the per-test teardown, **unconditionally**: always stop and release.
- Attach the video **only if the test failed**. Discard it otherwise.
- Keep the Android recording at or under 180 s per test unless ffmpeg is guaranteed on the Appium host. Prefer `mobile: startMediaProjectionRecording` (15 min default, no ffmpeg) on Android 10+, and `mobile: startXCTestScreenRecording` on iOS 17+.
- **On device clouds, don't record locally.** The vendor already records the session; mark pass/fail and link the vendor session instead (4.4).

### 4.4 Device clouds

- **BrowserStack App Automate:**
  - Video is "enabled by default"; disable it with `bstack:options` → `video: "false"`.
  - Mark the result with the executor `browserstack_executor: {"action": "setSessionStatus", "arguments": {"status":"<passed/failed>", "reason": "<reason>"}}`, or after the run with REST `PUT https://api-cloud.browserstack.com/app-automate/sessions/<session_id>.json`. The reason is at most 256 characters.

  Sources: https://www.browserstack.com/docs/app-automate/appium/set-up-tests/mark-tests-as-pass-fail · https://www.browserstack.com/docs/app-automate/appium/debug-failed-tests/video-recording · device, network and appium log capability names **UNVERIFIED**.
- **Sauce Labs:**
  - `executeScript("sauce:job-result=passed|failed")`, `sauce:job-name=…` and `sauce:context=…`. All are supported on real devices (RDC ✓).
  - `sauce:options` has `recordScreenshots`, `recordLogs` and `appiumVersion` (`'latest'`/`'stable'`).

  Sources: https://docs.saucelabs.com/basics/test-config-annotation/test-annotation/ · https://docs.saucelabs.com/dev/test-configuration-options/ · `recordVideo` / `videoUploadOnPass` **UNVERIFIED** on the fetched page.
- **LambdaTest (TestMu AI):**
  - `executeScript("lambda-status=passed|failed")`. Allowed values are `passed`, `failed`, `skipped`, `ignored`, `unknown` and `error`.
  - The Appium Java sample uses the same call plus `devicelog: true` and `network: true|false` capabilities.
  - The lambda-hooks page itself documents Selenium and Playwright only, so Appium support is shown only by the sample.

  Sources: https://www.lambdatest.com/support/docs/lambda-hooks/ · https://www.lambdatest.com/support/docs/appium-java/ · video capability for app automation **UNVERIFIED**.
- **WDIO** has vendor services (`@wdio/sauce-service`, plus a BrowserStack service from the vendor) that set status automatically. `@wdio/mcp` can start sessions on BrowserStack, Sauce Labs, TestMu (LambdaTest) and TestingBot (WDIO MCP docs).

---

## 5. Scoped element lookup

### 5.1 Locator priority (from the drivers)

- **UiAutomator2 speed ranking** (source: https://github.com/appium/appium-uiautomator2-driver#element-location):
  - `id` (resource-id, package prefix auto-added) ⭐⭐⭐⭐⭐
  - `accessibilityId` (content-desc; React Native `accessibilityLabel`) ⭐⭐⭐⭐⭐
  - `className` ⭐⭐⭐⭐⭐
  - `-android uiautomator` ⭐⭐⭐⭐
  - `xpath` ⭐⭐⭐
- **UiSelector deprecation:** the README warns that Google will deprecate and remove `UiCollection`, `UiObject`, `UiScrollable` and `UiSelector`, which will invalidate `-android uiautomator` locators. Google's page says these "are being deprecated in a future release"; use `By`, `BySelector` and `UiObject2`. Sources: https://github.com/appium/appium-uiautomator2-driver#element-location · https://developer.android.com/training/testing/other-components/ui-automator-legacy
- **Jetpack Compose:** `testTag` becomes a resource-id via the app-side `testTagsAsResourceId`, or via the driver setting `mapTestTagToResourceId` (UiA2 8.4.0+). Source: UiA2 README, Settings API.
- **XCUITest** (source: https://appium.github.io/appium-xcuitest-driver/latest/reference/locator-strategies/):
  - `accessibility id`, `id` and `name` are aliases of the `name` attribute (⭐⭐⭐⭐⭐).
  - `-ios predicate string` ⭐⭐⭐⭐⭐ is for elements identifiable by their own attributes.
  - `-ios class chain` ⭐⭐⭐⭐ is for elements needing parent or descendant context.
  - `xpath` ⭐⭐ "can be much slower … sometimes up to 10x slower", and is XPath 1.0 only (WDA 13.2+ adds some XPath-2-style string functions).
- **Why XPath is discouraged:**
  - XCTest has no native XPath, so the driver must build the whole XML page source first (XCUITest docs).
  - On Android, it is evaluated over the page-source XML tree.
  - It is fragile to hierarchy changes.
  - WDIO 10's Appium service ships a selector optimizer that flags slow XPath and suggests replacements (https://webdriver.io/docs/appium-service#native-mobile-selector-performance-optimizer).
  - `appium-mcp`'s `appium_find_element` documents the priority `accessibility id > id > platform-native > xpath (last resort — slow & brittle)`.
- **Accessibility id is the primary cross-platform locator** (WDIO Selectors doc: "usually the best method"). It is the content-desc on Android and the accessibilityIdentifier on iOS.

### 5.2 Find-within-element per client

| | Java | C# | WebdriverIO |
|---|---|---|---|
| Scoped single | `WebElement row = driver.findElement(AppiumBy.accessibilityId("cart-row-42")); row.findElement(AppiumBy.accessibilityId("qty-plus")).click();` | `var row = driver.FindElement(MobileBy.AccessibilityId("cart-row-42")); row.FindElement(MobileBy.AccessibilityId("qty-plus")).Click();` | `await $('~cart-row-42').$('~qty-plus').click()` (strict at each step in v10) |
| Scoped many | `row.findElements(AppiumBy.className("android.widget.TextView"))` | `row.FindElements(MobileBy.ClassName("XCUIElementTypeStaticText"))` | `await $('~cart-list').$$('~cart-row')` → `ElementArray` |
| Strategies | `AppiumBy.accessibilityId`, `id`, `className`, `name`, `androidUIAutomator`, `androidDataMatcher`, `androidViewMatcher`, `androidViewTag`, `iOSClassChain`, `iOSNsPredicateString`, `image`, `custom` | `MobileBy.AccessibilityId`, `Id`, `ClassName`, `Name`, `TagName`, `AndroidUIAutomator` (string or `IUiAutomatorStatementBuilder`), `AndroidDataMatcher`, `AndroidViewMatcher`, `IosNSPredicate`, `IosClassChain`, `Image`, `WindowsAutomation`, `TizenAutomation` | `~id`, `id=…`, `android=new UiSelector()…`, `-ios predicate string:…`, `-ios class chain:…`, `-android viewtag:…`, Espresso data/view matcher objects, image file path |

Sources:
- Java: `src/main/java/io/appium/java_client/AppiumBy.java`.
- .NET: `src/Appium.Net/Appium/MobileBy.cs`; chained `FindElement(MobileBy…)` is used in `test/integration/Android/ElementTestEspresso.cs`.
- WDIO: https://webdriver.io/docs/selectors#mobile-selectors and `#chain-selectors`.

**Platform-native scoping inside one locator:**

- **Android `UiSelector`:**
  - `new UiSelector().resourceId("…:id/row").childSelector(new UiSelector().text("Buy"))` narrows to a child.
  - `.fromParent(new UiSelector()…)` starts the search from the parent, i.e. siblings.
  - Both are `UiSelector` methods (Android reference: `childSelector(UiSelector)`, "narrow the search scope to child widgets under a specific parent widget"; `fromParent(UiSelector)`).
  - The UiA2 server parses UiSelector chains reflectively. `childSelector` is covered by its unit test `shouldBeAbleToParseNestedUiSelector`; `fromParent` works through the same reflective path but is **not explicitly tested** (UNVERIFIED by test).
  - Scrolling: `new UiScrollable(new UiSelector().scrollable(true)).scrollIntoView(new UiSelector().text("X"))`.
  - Mind the deprecation in 5.1.

  Sources: https://developer.android.com/reference/androidx/test/uiautomator/UiSelector · `appium-uiautomator2-server` `UiSelectorParser.java` / `UiExpressionParser.java` (`method.invoke`) · https://github.com/appium/appium-uiautomator2-driver/blob/master/docs/uiautomator-uiselector.md
- **iOS class chain:** ``**/XCUIElementTypeCell[`name == "Product B"`]/**/XCUIElementTypeButton[`label == "Add"`]``. WDIO's docs example is ``**/XCUIElementTypeCell[`name BEGINSWITH "D"`]/**/XCUIElementTypeButton``.
- **iOS element-scoped class chain or predicate** (`element.findElement(AppiumBy.iOSClassChain("**/XCUIElementTypeButton"))`) resolves against that element's **descendants**. WDA's `/element/:uuid/element` handler calls `fb_descendantsMatchingClassChain` on the context element. Source: https://github.com/appium/WebDriverAgent/blob/master/WebDriverAgentLib/Commands/FBFindElementCommands.m
- **Android XPath from an element:** a relative XPath (`.//x`) is scoped only by default. Setting `limitXPathContextScope=false` lets `//x` escape the context, so always prefix with `.` (UiA2 Settings API).

### 5.3 Best practice: screen object with a container-scoped component

- A **screen object** exposes intent methods (`cart.row("Product B").increaseQuantity()`), never selectors (this matches the library's page-object rule).
- A **component object** wraps a **root container** found by a stable accessibility id, such as `cart-row-<sku>` set by developers. All child lookups go through `root.findElement(...)` (Java/C#) or `root.$()` (WDIO). This works because:
  - Children need only locally unique ids (`qty-plus`, `price`), so they are reusable across rows.
  - It avoids XPath with indexes.
  - In WDIO 10 it is the cure for `StrictSelectorError`.
- **Re-resolve the root per action** (store its locator, not the element) if the list re-renders, to avoid stale element references. WDIO elements re-query lazily: "An element remembers how it was queried" (v10 migration).
- For lists, use `$$(rowSelector)` / `findElements` to enumerate, then wrap each element in the component. Or locate a row by a user-facing attribute in one native query: a predicate on iOS, a `UiSelector().description(...)` on Android (deprecated), or preferably id plus a text filter in code.
- **For coordinates**, compute targets from `element.getRect()`. The W3C `rect` replaced the removed `location`/`size` routes in Appium 3.

---

## 6. Other modern capabilities worth teaching

All are `mobile:` execute methods unless noted. Call them as `driver.executeScript("mobile: X", Map.of(...))` (Java), `driver.ExecuteScript("mobile: X", new Dictionary<string, object>{...})` (C#), or `await browser.execute('mobile: X', {...})` (WDIO).

| Capability | Android (UiA2 8.x) | iOS (XCUITest 12.x) | Client sugar |
|---|---|---|---|
| Deep link | `mobile: deepLink {url, package?, waitForLaunch?}` | `mobile: deepLink {url, bundleId?}` (Xcode 14.3+/iOS 16.4+) | WDIO `browser.deepLink(link, appIdentifier, waitForLaunch?)` |
| App lifecycle | `mobile: activateApp {appId}`, `terminateApp {appId, timeout?}`, `queryAppState`, `backgroundApp {seconds}`, `clearApp`, `installApp`, `removeApp`, `isAppInstalled`, `listApps`, `startActivity` | `mobile: launchApp`, `activateApp {bundleId}`, `terminateApp`, `killApp`, `queryAppState`, `backgroundApp`, `clearApp` (simulator), `listApps` | Java `driver.activateApp(id)` / `terminateApp` / `queryApplicationState` (`InteractsWithApps`; v11 sends `mobile:` only); C# `ActivateApp`, `TerminateApp`, `BackgroundApp`; WDIO `activateApp`, `terminateApp`, `queryAppState` |
| Permissions | `mobile: changePermissions {permissions, appPackage?, action: grant\|revoke, target: pm\|appops}`, `mobile: getPermissions`; capability `appium:autoGrantPermissions` | `mobile: setPermission {bundleId, access:{camera:'yes',…}}` (simulator; some services need WIX `applesimutils`), `getPermission`, `resetPermission` | — |
| Biometrics | `mobile: fingerprint {fingerprintId}` (emulator) | `mobile: enrollBiometric {isEnabled}`, `sendBiometricMatch {type: touchId\|faceId, match}`, `isBiometricEnrolled` (simulator) | WDIO `fingerPrint`, `touchId`, `toggleEnrollTouchId` |
| Geolocation | `mobile: setGeolocation {latitude, longitude, altitude?, satellites?, speed?}`, `getGeolocation`, `resetGeolocation`, `refreshGpsCache` | `mobile: setSimulatedLocation {latitude, longitude}` (Xcode 14.3+/iOS 16.4+, recommended for iOS 17+ real devices), `getSimulatedLocation`, `resetSimulatedLocation` | WDIO `setGeoLocation` (protocol; Appium 4 removes the legacy `/location` route) |
| Network | `mobile: setConnectivity {wifi?, data?, airplaneMode?}`, `getConnectivity`; emulator `mobile: networkSpeed {speed}`, `gsmSignal`, … | real device iOS 13+: `mobile: listConditionInducers`, `enableConditionInducer {conditionID, profileID}`, `disableConditionInducer` | — |
| Clipboard | `mobile: setClipboard {content(base64), contentType}`, `getClipboard` | `mobile: setPasteboard` / `getPasteboard` (sim), `setClipboard` / `getClipboard` | Java `HasAndroidClipboard` / `HasIOSClipboard`; C# `SetClipboardText` / `GetClipboardText` |
| Push notifications | `mobile: getNotifications`, `openNotifications` | `mobile: pushNotification {bundleId, payload:{aps:{…}}}` (simulator), `mobile: expectNotification` | — |
| Logs (pull) | `getLogs` types `logcat`, `bugreport`, `server` (server needs the `get_server_logs` insecure feature) | types `syslog`, `crashlog`, `performance`, `safariConsole`, `safariNetwork`, `server` (same flag) | Java `driver.manage().logs().get("logcat")`; C# `driver.Manage().Logs.GetLog("logcat")`; WDIO `browser.getLogs('logcat')`, `browser.getLogTypes()` |
| Logs (stream) | `mobile: startLogsBroadcast` / `stopLogsBroadcast` (websocket `/ws/session/:id/appium/device/logcat`); the driver now recommends BiDi `log.entryAdded` | `mobile: startLogsBroadcast` / `stopLogsBroadcast`; BiDi `log.entryAdded` (`syslog`, `crashlog`, …) | Java `startLogcatBroadcast()` + `addLogcatMessagesListener(Consumer<String>)` / `startSyslogBroadcast()`; C# `await StartLogcatBroadcast()` + `AddLogcatMessagesListener(Action<string>)` / `await StartSyslogBroadcast()` |
| Performance | `mobile: getPerformanceData {packageName, dataType}`, `getPerformanceDataTypes` | `mobile: startPerfRecord` / `stopPerfRecord` (instruments), `startSystemMonitor` / `stopSystemMonitor`, `startNetworkMonitor` / `stopNetworkMonitor` | WDIO `getPerformanceData` |
| Accessibility audit | — | `mobile: performAccessibilityAudit {auditTypes?}` (Xcode 15/iOS 17) | — |
| Gestures | `mobile: clickGesture`, `longClickGesture`, `doubleClickGesture`, `dragGesture`, `flingGesture`, `pinchOpenGesture`, `pinchCloseGesture`, `swipeGesture`, `scrollGesture` | `mobile: tap`, `doubleTap`, `touchAndHold`, `twoFingerTap`, `swipe`, `scroll`, `scrollToElement`, `pinch`, `dragFromToForDuration`, `rotateElement` | W3C Actions in all three; WDIO 10 `tap`, `swipe`, `longPress`, `dragAndDrop`, `pinch`, `zoom`, `scrollIntoView` |

Sources:
- UiA2 README execute-method sections: https://github.com/appium/appium-uiautomator2-driver#platform-specific-extensions
- XCUITest execute methods: https://appium.github.io/appium-xcuitest-driver/latest/reference/execute-methods/
- Log types: `appium-android-driver lib/commands/log.ts`, `appium-xcuitest-driver lib/commands/log.ts`
- BiDi: `uia2/docs/bidi.md`, `xcui/docs/reference/bidi.md`
- Java interfaces: `AndroidDriver`/`IOSDriver` implements lists
- .NET: `AndroidDriver.cs` / `IOSDriver.cs`
- The XCUITest doc text for `enableConditionInducer` refers to `mobile: availableConditionInducer`, but the method list names it `mobile: listConditionInducers`. Use the latter.

**Waits and settings**

- Settings API: `POST/GET /session/:id/appium/settings`. Initialise a single setting via the `appium:settings[<name>]` capability, or several via `appium:settings: {...}` (Appium 2.1+). Source: https://appium.io/docs/en/latest/guides/settings/
- Client calls:
  - Java: `driver.setSetting(Setting.X, v)` / `setSettings(Map)` / `getSettings()` (`HasSettings`).
  - C#: `driver.SetSetting(name, value)` / `driver.Settings`.
  - WDIO: `browser.updateSettings({...})` / `browser.getSettings()`.
- UiA2 settings that matter for speed and flakiness: `waitForIdleTimeout` (default 10000 ms), `waitForSelectorTimeout` (10000 ms, uiautomator strategy only), `ignoreUnimportantViews`, `allowInvisibleElements`, `enableMultiWindows`, `limitXPathContextScope`, `disableIdLocatorAutocompletion`, `mapTestTagToResourceId`, `snapshotMaxDepth`.
- XCUITest settings: `waitForIdleTimeout` (float seconds, default 10; also the `appium:waitForIdleTimeout` capability; it replaced `waitForQuiescence`, which was removed in 11.0.0), `animationCoolOffTimeout`, `snapshotMaxDepth`, `useFirstMatch`, `pageSourceExcludedAttributes`, `respectSystemAlerts`, `reduceMotion`, `screenshotQuality`.
- Client-side waits:
  - Java v11: `WebDriverWait` (needs the `selenium-support` dependency) or `AppiumFluentWait` / `io.appium.java_client.support.ui.FluentWait`.
  - C#: Selenium `WebDriverWait`. Selenium.Support is no longer a transitive dependency since Appium.WebDriver 6.0, so add `Selenium.Support` explicitly. **UNVERIFIED** that it is required for `WebDriverWait`, which may live in Selenium.WebDriver itself in 4.x.
  - WDIO: auto-wait plus `waitForDisplayed` / `waitUntil`.

**Images plugin** (`@appium/images-plugin` 5.0.1). Sources: https://github.com/appium/appium/tree/master/packages/images-plugin · docs `find-by-image.md`, `image-comparison.md`

- Install with `appium plugin install images` and start with `--use-plugins=images`.
- **Find by image:** strategy `-image`; the selector is a base64 template. Settings: `imageMatchThreshold` (0.4), `fixImageTemplateScale`, among others.
  - Java: `AppiumBy.image(b64)`.
  - C#: `MobileBy.Image(b64)`.
  - WDIO: pass an image file path to `$()`.
- **Compare:** `POST /session/:id/appium/compare_images`, with modes feature matching, occurrence lookup and similarity.
  - Java (`ComparesImages`): `matchImagesFeatures(...)`, `findImageOccurrence(...)`, `getImagesSimilarity(...)`.
  - C#: `GetImagesSimilarity(...)` and its siblings.
  - WDIO: protocol `compareImages`.

**Appium Inspector**

- v2026.9.2 standalone, or the plugin (`appium plugin install inspector`, then `appium --use-plugins=inspector`, browse to `http://<host>:4723/inspector`).
- WDIO 10: `npx start-appium-inspector`.

Sources: https://appium.io/docs/en/latest/ecosystem/tools/ · https://github.com/appium/appium-inspector/tree/main/plugins · WDIO `@wdio/appium-service` README.

**AI-agent surfaces (MCP)**

- **`appium-mcp`** (official). Sources: https://github.com/appium/appium-mcp#readme · https://appium.io/docs/en/latest/ecosystem/tools/#appium-mcp
  - npm `appium-mcp@1.95.8`, Node >=22, repo `appium/appium-mcp`, listed on appium.io → Ecosystem → Tools.
  - Install:
    - Claude Code: `claude mcp add appium-mcp -- npx -y appium-mcp@latest`
    - Generic config: `{"command":"npx","args":["appium-mcp@latest"],"env":{"ANDROID_HOME":"…","CAPABILITIES_CONFIG":"…"}}`
  - Modes:
    - Embedded local UiA2/XCUITest drivers: no Appium server needed for `platform=android|ios`.
    - Remote server via `remoteServerUrl`: `platform=general`; restrict hosts with `REMOTE_SERVER_URL_ALLOW_REGEX`.
  - Tools:
    - Setup: `select_device` (required first), `prepare_ios_simulator`, `appium_prepare_ios_real_device`.
    - Session and device: `appium_session_management` (create, attach, detach, delete, list, select), `appium_mobile_device_control`, `appium_driver_settings`, `appium_context`.
    - Elements: `appium_find_element`, `appium_ai` (opt-in via `AI_VISION_ENABLED=true`), `appium_gesture` (tap, double_tap, long_press, scroll, swipe, pinch_zoom, scroll_to_element, back), `appium_drag_and_drop`, `appium_perform_actions`, `appium_set_value`, `appium_mobile_keyboard`, `appium_get_text`, `appium_mobile_clipboard`, `appium_alert`.
    - Screen and device info: `appium_screenshot`, `appium_get_window_size`, `appium_get_page_source`, `appium_orientation`, `appium_geolocation`, `appium_screen_recording` (start/stop; iOS needs ffmpeg), `appium_mobile_device_info`.
    - Apps: `appium_app_lifecycle` (activate, terminate, install, uninstall, list, is_installed, query_state, background, clear, deep_link), `appium_mobile_permissions`.
    - Generation and docs: `generate_locators`, `appium_generate_tests` (Java/TestNG), and `appium_documentation_query` / `appium_skills` (opt-in via `APPIUM_MCP_DOCS_ENABLED`).
  - Env: `SCREENSHOTS_DIR`, OpenTelemetry tracing.
- **`appium/skills`** (official agent skills repo, listed on the Tools page) helps with environment setup and WDA real-device preparation.
- **`@wdio/mcp` 4.0.0** (WebdriverIO).
  - Install: `npx @wdio/mcp`, or `claude mcp add --transport stdio wdio-mcp -- npx -y @wdio/mcp`.
  - Tools: `start_session`, `close_session`, `get_elements`, `get_accessibility_tree`, `get_screenshot`, `tap_element`, `swipe`, `drag_and_drop`, `get_contexts`, `switch_context`, `rotate_device`, `hide_keyboard`, `set_geolocation`, `get_app_state`, `execute_script`, `list_apps`, `upload_app`; plus cloud providers.
  - Source: https://webdriver.io/docs/mcp · `website/docs/mcp/tools.md`
- **Community:** AppClaw (`npm i -g appclaw`, built on Appium MCP) is listed as "not maintained by the Appium team".

---

## 7. Playwright for mobile (1.64)

- **Mobile web emulation:** `devices['iPhone 13']` etc. in `playwright.config.ts` projects, or `browser.newContext({...devices['Pixel 7']})`. It sets userAgent, screenSize, viewport, `hasTouch` and `isMobile`, and you can also emulate geolocation, locale, timezone, permissions and colorScheme. This is **browser-engine emulation, not a real device**: WebKit is not Mobile Safari, and there are no native apps. Source: https://playwright.dev/docs/emulation (repo `docs/src/emulation.md@v1.64.0`)
- **Android support is still experimental in 1.64** ("Playwright has **experimental** support for Android automation. This includes Chrome for Android and Android WebView."). Sources: https://playwright.dev/docs/api/class-android · repo `docs/src/mobile-api/class-android.md@v1.64.0`
  - JS/TS only (`langs: js`).
  - Requirements: ADB, Chrome 105+ on the device, and "Enable command line on non-rooted devices" in `chrome://flags`.
  - Limitations: no raw USB, the device must be awake for screenshots, and "not everything works".
  - API:
    - `const { _android: android } = require('playwright')`
    - `const [device] = await android.devices()`
    - `device.launchBrowser()` returns a `BrowserContext`.
    - `device.webView({ pkg })`, then `webview.page()`.
    - `device.shell(...)`, `device.screenshot({path})`, `device.installApk`, `device.push`.
    - Native-ish selectors: `device.fill({res: 'pkg:id/x'}, text)`, `tap`, `press`, `fling`, `scroll`, `pinchOpen`/`pinchClose`, `drag`, `longTap`.
    - `android.connect()` / `launchServer()`.
  - In the v1.64.0 repo the Android API docs live in `docs/src/mobile-api/`, separate from `docs/src/api/`. The release notes for 1.64 contain no Android changes.
- **No native iOS support.** Native app automation remains Appium's (or WDIO's on Appium) domain.

---

## 8. Per-client API matrix (exact spellings)

| Concern | Java (java-client 11 + TestNG) | C# (Appium.WebDriver 9 + NUnit) | WebdriverIO 10 (TS) |
|---|---|---|---|
| Driver and options | `new AndroidDriver(url, new UiAutomator2Options().setApp(...))`; `new IOSDriver(url, new XCUITestOptions()...)` | `new AndroidDriver(uri, new AppiumOptions { AutomationName = AutomationName.AndroidUIAutomator2, App = ... })` (+ `AddAdditionalAppiumOption`) | `capabilities: { platformName: 'Android', 'appium:automationName': 'UiAutomator2', 'appium:app': ... }` (prefix mandatory in v10) |
| Screenshot | `driver.getScreenshotAs(OutputType.BYTES)` | `driver.GetScreenshot().AsByteArray` | `browser.takeScreenshot()` / `browser.saveScreenshot(path)` |
| Element screenshot | `element.getScreenshotAs(OutputType.BYTES)` | `((ITakesScreenshot)element).GetScreenshot()` | `$(sel).saveScreenshot(path)` |
| Start recording | `driver.startRecordingScreen(new AndroidStartScreenRecordingOptions().withTimeLimit(Duration.ofSeconds(180)).enableForcedRestart())` | `driver.StartRecordingScreen(AndroidStartScreenRecordingOptions.GetAndroidStartScreenRecordingOptions().WithTimeLimit(TimeSpan.FromSeconds(180)).EnableForcedRestart())` | `browser.startRecordingScreen({ timeLimit: 180, forceRestart: true })` |
| Stop recording | `String b64 = driver.stopRecordingScreen()` | `string b64 = driver.StopRecordingScreen()` | `const b64 = await browser.stopRecordingScreen()` / `browser.saveRecordingScreen(path)` |
| Native recording (execute) | `driver.executeScript("mobile: startMediaProjectionRecording", Map.of("maxDurationSec", 600))` / `"mobile: startXCTestScreenRecording"` | `driver.ExecuteScript("mobile: startXCTestScreenRecording", new Dictionary<string, object>{{"fps", 24}})` | `browser.execute('mobile: stopXCTestScreenRecording', {})` |
| Scoped find | `root.findElement(AppiumBy.accessibilityId("x"))` | `root.FindElement(MobileBy.AccessibilityId("x"))` | `$('~root').$('~x')` |
| Scoped list | `root.findElements(AppiumBy.id("row"))` | `root.FindElements(MobileBy.Id("row"))` | `$('~root').$$('~row')` |
| Logs (pull) | `driver.manage().logs().get("logcat").getAll()`; `driver.manage().logs().getAvailableLogTypes()` | `driver.Manage().Logs.GetLog("logcat")`; `.AvailableLogTypes` | `browser.getLogs('logcat')`; `browser.getLogTypes()` |
| Logs (stream) | `((AndroidDriver) d).startLogcatBroadcast(); addLogcatMessagesListener(msg -> …)`; iOS `startSyslogBroadcast()` | `await androidDriver.StartLogcatBroadcast(); AddLogcatMessagesListener(msg => …)`; iOS `await StartSyslogBroadcast()` | `browser.execute('mobile: startLogsBroadcast', {})` (then a websocket) or BiDi `log.entryAdded` — exact WDIO BiDi subscription for Appium **UNVERIFIED** |
| Gestures (W3C) | `var f = new PointerInput(PointerInput.Kind.TOUCH, "finger"); var s = new Sequence(f, 0).addAction(f.createPointerMove(Duration.ZERO, PointerInput.Origin.viewport(), x, y)).addAction(f.createPointerDown(PointerInput.MouseButton.LEFT.asArg())).addAction(f.createPointerUp(PointerInput.MouseButton.LEFT.asArg())); driver.perform(List.of(s));` | `var touch = new PointerInputDevice(PointerKind.Touch, "finger"); var seq = new ActionSequence(touch); seq.AddAction(touch.CreatePointerMove(el, 0, 0, TimeSpan.FromMilliseconds(100))); seq.AddAction(touch.CreatePointerDown(MouseButton.Touch)); seq.AddAction(touch.CreatePointerUp(MouseButton.Touch)); driver.PerformActions(new List<ActionSequence>{ seq });` | `browser.action('pointer', { parameters: { pointerType: 'touch' } }).move({x, y}).down().up().perform()` |
| Gestures (driver) | `driver.executeScript("mobile: clickGesture", Map.of("x", x, "y", y))` (UiA2); `"mobile: tap"` (XCUITest); element id via `((AppiumWebElement) el).getId()` | `driver.ExecuteScript("mobile: scroll", new Dictionary<string, string>{{"element", el.Id}, {"direction", "down"}})` | `$(sel).tap()`, `browser.swipe({ direction: 'up' })`, `$(sel).longPress()`, `pinch`, `zoom`, `$(sel).scrollIntoView()` |
| Settings | `driver.setSetting("waitForIdleTimeout", 0)` / `getSettings()` | `driver.SetSetting("waitForIdleTimeout", 0)` / `driver.Settings` | `browser.updateSettings({ waitForIdleTimeout: 0 })` / `browser.getSettings()` |
| Deep link | `driver.executeScript("mobile: deepLink", Map.of("url", u, "package", p))` | `driver.ExecuteScript("mobile: deepLink", new Dictionary<string, object>{{"url", u}, {"bundleId", b}})` | `browser.deepLink(u, appId)` |
| Allure attach | `Allure.attachment(name, "image/png", in, AttachmentOptions.withFileExtension("png"))` (Allure 3) | `AllureApi.AddAttachment(name, "image/png", bytes, ".png")` | `allureReporter.addAttachment(name, content, 'image/png')` |

Notes:
- Java W3C snippet: verbatim from the v11 migration guide.
- C# W3C snippet: adapted from the dotnet-client README "Migration Guide to W3C actions". Its signature is `CreatePointerMove(IWebElement, int, int, TimeSpan)`.
- C# `el.Id` usage: from `test/integration/IOS/ScrollingSearchingTest.cs`.

---

## 9. Recommended "evidence on failure" pattern

**Principles:**
- Start recording in setup with `forceRestart`.
- In teardown, stop it **always**.
- Capture the screenshot, page source and log tail **only on failure**, and attach them all to Allure.
- Evidence capture must never mask the original failure. Each capture goes through a small helper that catches the **specific** I/O exception, logs it, and continues. That is consistent with the library rule allowing try/catch only in I/O helpers, with no blanket catches.
- On device clouds, skip local recording and set vendor pass/fail instead.

### 9.1 TestNG (Java 21, java-client 11, allure-testng 3.0.0)

```java
public abstract class MobileTestBase {
    private static final Logger log = LoggerFactory.getLogger(MobileTestBase.class);
    protected AndroidDriver driver;

    @BeforeMethod(alwaysRun = true)
    public void startRecording() {
        driver.startRecordingScreen(new AndroidStartScreenRecordingOptions()
                .withTimeLimit(Duration.ofSeconds(180))
                .withVideoSize("1280x720")
                .enableForcedRestart());
    }

    @AfterMethod(alwaysRun = true)
    public void captureEvidence(ITestResult result) {
        boolean failed = result.getStatus() == ITestResult.FAILURE;
        if (failed) {
            attachScreenshot();
            attachText("page-source", "application/xml", driver.getPageSource());
            attachLogcatTail();
        }
        String video = driver.stopRecordingScreen();
        if (failed) {
            Allure.attachment("screen-recording", "video/mp4",
                    new ByteArrayInputStream(Base64.getDecoder().decode(video)),
                    AttachmentOptions.withFileExtension("mp4"));
        }
    }

    private void attachScreenshot() {
        try {
            byte[] png = driver.getScreenshotAs(OutputType.BYTES);
            Allure.attachment("screenshot", "image/png", new ByteArrayInputStream(png),
                    AttachmentOptions.withFileExtension("png"));
        } catch (WebDriverException e) {
            log.warn("Screenshot capture failed for session {}", driver.getSessionId(), e);
        }
    }
    // attachText / attachLogcatTail: driver.manage().logs().get("logcat").getAll() → last N lines
}
```

- Sources: TestNG `ITestResult` and `@AfterMethod(alwaysRun = true)` are standard TestNG API (7.12.0). Allure 3 API: section 3.
- Allure 3.0.0 changelog: "Make TestNG custom listener evidence work automatically" and "Fix missing attachments from TestNG configuration listeners" (https://github.com/allure-framework/allure-java/releases/tag/3.0.0). Attachments from `@AfterMethod` appear under the test's tear-down fixture.
- The relative order of the listener's `onTestFailure` and `@AfterMethod` is **UNVERIFIED** here.
- **On device clouds**, replace the recording with `((JavascriptExecutor) driver).executeScript("browserstack_executor: {\"action\": \"setSessionStatus\", \"arguments\": {\"status\":\"failed\", \"reason\": \"...\"}}")`, or `"sauce:job-result=failed"`, or `"lambda-status=failed"`.

### 9.2 NUnit (Appium.WebDriver 9, NUnit 4.x / 5, Allure.NUnit 2.15)

```csharp
[SetUp]
public void StartRecording() =>
    _driver.StartRecordingScreen(AndroidStartScreenRecordingOptions
        .GetAndroidStartScreenRecordingOptions()
        .WithTimeLimit(TimeSpan.FromSeconds(180))
        .EnableForcedRestart());

[TearDown]
public void CaptureEvidence()
{
    var failed = TestContext.CurrentContext.Result.Outcome.Status == TestStatus.Failed;
    if (failed)
    {
        var shot = _driver.GetScreenshot();
        var path = Path.Combine(TestContext.CurrentContext.WorkDirectory, $"{TestContext.CurrentContext.Test.ID}.png");
        shot.SaveAsFile(path);
        TestContext.AddTestAttachment(path, "screenshot");
        AllureApi.AddAttachment("screenshot", "image/png", shot.AsByteArray, ".png");
        AllureApi.AddAttachment("page-source", "application/xml", Encoding.UTF8.GetBytes(_driver.PageSource), ".xml");
    }
    var video = _driver.StopRecordingScreen();
    if (failed)
        AllureApi.AddAttachment("screen-recording", "video/mp4", Convert.FromBase64String(video), ".mp4");
}
```

- `TestContext.CurrentContext.Result.Outcome.Status`, `TestStatus` (`NUnit.Framework.Interfaces`) and `TestContext.AddTestAttachment(path, description)` are standard NUnit API. The NUnit 5.0.0 release notes list no TestContext breaking changes.
- `Allure.NUnit` 2.15.0 still references NUnit 3.13.3 as its minimum, so **running Allure.NUnit on NUnit 5 is UNVERIFIED**.
- If moving to NUnit 5, `Assert.ThrowsAsync` must be awaited.
- Wrap each capture in a helper that catches `WebDriverException`, logs it with a template (`_logger.LogWarning(e, "Screenshot failed for {SessionId}", _driver.SessionId)`) and continues.

### 9.3 WDIO 10 (`wdio.conf.ts`, `@wdio/allure-reporter` 10)

```ts
import allureReporter from '@wdio/allure-reporter'

export const config: WebdriverIO.Config = {
    reporters: [['allure', { outputDir: 'allure-results', disableWebdriverScreenshotsReporting: false }]],
    services: [['appium', { args: { allowInsecure: 'uiautomator2:adb_shell' } }]],
    beforeTest: async () => {
        await browser.startRecordingScreen({ timeLimit: 180, forceRestart: true })
    },
    afterTest: async (test, context, { passed }) => {
        const video = await browser.stopRecordingScreen()
        if (passed) return
        await browser.takeScreenshot()
        allureReporter.addAttachment('screen-recording', Buffer.from(video, 'base64'), 'video/mp4')
        allureReporter.addAttachment('page-source', await browser.getPageSource(), 'application/xml')
        allureReporter.addAttachment('logcat', JSON.stringify(await browser.getLogs('logcat')), 'application/json')
    },
}
```

- `browser.takeScreenshot()` is auto-attached when `disableWebdriverScreenshotsReporting: false`.
- `afterTest(test, context, { error, result, duration, passed, retries })` is the documented hook signature (allure-reporter README). Cucumber uses `afterStep`.
- `args.allowInsecure` is a typed key (`allowInsecure?: string` in `packages/wdio-appium-service/src/types.ts`); args are lower-camel-case Appium CLI flags (service README). The value needs the Appium 3 scope prefix.

---

## 10. UNVERIFIED items (collected)

- BrowserStack and Sauce Labs Appium 3 availability. This gates WDIO 10 and java-client 11 on clouds.
- BrowserStack device, network and Appium log capability key names; the Sauce `recordVideo`/`videoUploadOnPass` defaults; the LambdaTest app-automation video capability.
- Allure.NUnit 2.15 on NUnit 5.
- TestNG listener-vs-`@AfterMethod` ordering.
- Whether `fromParent` parses in the UiA2 server. Reflection makes it likely, but no test covers it.
- The exact WDIO BiDi subscription API for Appium `log.entryAdded`.
- Whether `Selenium.Support` is needed for `WebDriverWait` in .NET (vs Selenium.WebDriver 4.x).
- The Android `screenrecord` "last chunk returned without ffmpeg" behaviour. The javadoc says so, but the driver source suggests an error.

## 11. Primary sources index

- Appium 2→3 guide: https://appium.io/docs/en/latest/guides/migrating-2-to-3/ ; Appium 3 blog: https://appium.io/docs/en/latest/blog/2025/08/07/-appium-3/
- Appium 3→4 (beta) guide: https://github.com/appium/appium/blob/appium4/packages/appium/docs/en/guides/migrating-3-to-4.md
- Appium CHANGELOG: https://github.com/appium/appium/blob/master/packages/appium/CHANGELOG.md
- `appium setup`: https://appium.io/docs/en/latest/reference/cli/setup/ ; extensions CLI: https://appium.io/docs/en/latest/reference/cli/extensions/ ; insecure features: https://appium.io/docs/en/latest/reference/cli/insecure-features/
- Settings: https://appium.io/docs/en/latest/guides/settings/ ; Tools (Inspector, MCP, skills): https://appium.io/docs/en/latest/ecosystem/tools/ ; Drivers: https://appium.io/docs/en/latest/ecosystem/drivers/
- java-client v11 release: https://github.com/appium/java-client/releases/tag/v11.0.0 ; migration: https://github.com/appium/java-client/blob/master/docs/v10-to-v11-migration-guide.md ; bridge: https://github.com/appium/java-client/blob/master/docs/selenium-bridge.md
- dotnet-client releases: https://github.com/appium/dotnet-client/releases ; README: https://github.com/appium/dotnet-client
- UiAutomator2 driver: https://github.com/appium/appium-uiautomator2-driver ; XCUITest docs: https://appium.github.io/appium-xcuitest-driver/latest/
- Images plugin: https://github.com/appium/appium/tree/master/packages/images-plugin
- appium-mcp: https://github.com/appium/appium-mcp
- WDIO v10 blog: https://webdriver.io/blog/2026/10/05/webdriverio-v10-release ; migration: https://webdriver.io/docs/v10-migration ; selectors: https://webdriver.io/docs/selectors ; MCP: https://webdriver.io/docs/mcp
- Allure Java 3.0.0: https://github.com/allure-framework/allure-java/releases/tag/3.0.0 ; allure-csharp: https://github.com/allure-framework/allure-csharp/releases
- NUnit 5 notes: https://docs.nunit.org/articles/nunit/release-notes/framework.html
- Playwright Android: https://playwright.dev/docs/api/class-android ; emulation: https://playwright.dev/docs/emulation
- Clouds: https://www.browserstack.com/docs/app-automate/appium/set-up-tests/mark-tests-as-pass-fail · https://docs.saucelabs.com/basics/test-config-annotation/test-annotation/ · https://www.lambdatest.com/support/docs/lambda-hooks/
