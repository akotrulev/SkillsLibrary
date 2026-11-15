# Desktop research: the cross-platform landscape and desktop E2E automation (as of 2026-11-15)

Method: versions and dates come from the npm registry (`registry.npmjs.org`, `api.npmjs.org/downloads`), the NuGet v3 API, Maven Central `maven-metadata.xml`, the GitHub REST API (stars, releases, `archived`) and `endoflife.date`, all queried on 2026-11-15. Driver behaviour comes from each project's own README and docs tree. Adoption share comes from the Stack Overflow survey pages and Desktop Insights. Anything that could not be confirmed from a primary source is in the closing **Not verified** list.

Feeds: plan 012 (`desktop-macos`, `desktop-windows`). Precedent: `docs/plans/implemented/002-mobile-plugins.md` §3.

---

## 0. Headline findings

- **Appium 4 is in beta, and the desktop drivers already moved to it.** Appium `4.0.0-beta.8` shipped on 2026-11-13; `latest` is still `3.9.1` (2026-11-14). The newest Mac2 driver (`5.0.x`) and WinCore driver (`4.x`) declare `appium ^4.0.0-beta`, and `appium-xcuitest-driver` 13 / `appium-uiautomator2-driver` 9 did the same in November. A plan pinned to Appium 3 must pin the driver versions explicitly: **`mac2@4.6.1`** and **`appium-wincore-driver@3.3.2`**. ([npm appium](https://registry.npmjs.org/appium), [npm appium-mac2-driver](https://registry.npmjs.org/appium-mac2-driver), [npm appium-wincore-driver](https://registry.npmjs.org/appium-wincore-driver), [Mac2 getting started](https://github.com/appium/appium-mac2-driver/blob/master/docs/getting-started/index.md))
- **The Appium Windows driver is deprecated and its repo is archived.** Its README says it "is not compatible with Appium 4 and later, since the WinAppDriver server only speaks the legacy JSONWP protocol", and names the **Appium WinCore Driver** as the official replacement. WinAppDriver's last release is `v1.2.99` (2021-07-01). ([appium-windows-driver README](https://github.com/appium/appium-windows-driver), [GitHub API: archived=true](https://api.github.com/repos/appium/appium-windows-driver), [WinAppDriver releases](https://github.com/microsoft/WinAppDriver/releases))
- **The library's QA pins are one minor behind.** Appium `3.9.1` is latest (pins say 3.8.0) and Playwright Node `1.65.1` shipped 2026-11-13 (pins say 1.64). Neither change blocks desktop work. ([npm appium](https://registry.npmjs.org/appium), [npm playwright](https://registry.npmjs.org/playwright))
- **.NET MAUI 11 reached GA on 2026-11-10.** Plan 002 deferred MAUI until this date, so the revisit is due now. ([dotnet/maui releases](https://github.com/dotnet/maui/releases))
- **The Stack Overflow survey has not had a framework list since 2024.** The 2025 and 2026 technology pages carry no Electron, Tauri or Flutter rows, so 2024 is still the latest survey with a framework list, as in plan 002. ([SO 2026 technology.md](https://survey.stackoverflow.co/2026/technology.md), [SO 2025 technology](https://survey.stackoverflow.co/2025/technology), [SO 2024 technology](https://survey.stackoverflow.co/2024/technology))

---

## Part A: the cross-platform desktop landscape

### A.1 Evidence

The columns are the Stack Overflow 2024 "Other frameworks and libraries" share of all respondents, the share of 28,699 shipped macOS and Windows apps that Desktop Insights tracks, GitHub stars, weekly package downloads, the latest stable release, and notable shipping apps.

| Framework | SO 2024 | Desktop Insights | GitHub stars | Weekly downloads | Latest stable (date) | Notable shipping desktop apps |
|---|---|---|---|---|---|---|
| **Electron** | **6.5%** | **2,684 apps (9.4%)** | 123.9k | **12.5M** (npm `electron`) | 45.3.3 (2026-11-14); a new major every ~8 weeks (42 → 45 between May and Oct 2026) | VS Code, Slack, Discord, Notion, Figma, 1Password, Obsidian, Postman, Signal, Claude, ChatGPT |
| **Tauri 2** | 2.4% | **1,816 apps (6.3%)** | 112.9k | 4.8M (`@tauri-apps/api`) | 2.12.5 (2026-10-21); **3.0.0-alpha.6** (2026-11-06) | Spacedrive, AppFlowy, Clash Verge (secondary source only) |
| Flutter (desktop) | 9.4% (all targets) | 52 apps (0.2%) | 181.3k | n/a | 3.50.0 (2026-11-11) | Ubuntu Desktop installer; Ubuntu App Center |
| .NET MAUI | 3.1% | 229 apps (0.8%) | 23.3k | n/a | **11.0.10** (11.0.0 GA 2026-11-10) | none notable; Desktop Insights lists small utilities |
| Avalonia 11/12 | not listed | 199 apps (0.7%) | 31.8k | n/a | 12.1.6 and 11.3.23 (both 2026-11-09); 12.0 stable 2026-04-07 | JetBrains, Unity (Plastic SCM), LINQPad, Devolutions, Schneider Electric |
| Uno Platform | not listed | page failed to load | 10.1k | n/a | 7.0.65 (2026-11-13) | Toyota, TradeZero (enterprise customers; desktop use not stated) |
| Compose Multiplatform Desktop | not listed (KMP: see plan 002) | page failed to load | 19.5k | n/a | 1.12.2 (2026-10-15) | JetBrains Toolbox App |
| Qt 6 | 7.3% | 1,101 apps (3.8%) | 3.1k (qtbase mirror) | n/a | 6.12 (2026-09-30, flagged LTS) | the C++/QML incumbent; no list was fetched |
| React Native for Windows / macOS | 8.4% (all RN) | 45 apps (0.2%) | 17.4k / 4.4k | 83k / 82k | RNW 0.85.2 (0.85.0 on 2026-10-20); RN-macOS 0.83.0 | Microsoft Office (the Copilot pane) |

Sources:
- SO 2024 shares: [survey.stackoverflow.co/2024/technology](https://survey.stackoverflow.co/2024/technology) ("Other frameworks and libraries", all respondents).
- Desktop Insights: [/tech/electron](https://desktopinsights.com/tech/electron), [/tech/tauri](https://desktopinsights.com/tech/tauri), [/tech/flutter](https://desktopinsights.com/tech/flutter), [/tech/net-maui](https://desktopinsights.com/tech/net-maui), [/tech/avalonia](https://desktopinsights.com/tech/avalonia), [/tech/qt](https://desktopinsights.com/tech/qt), [/tech/react-native](https://desktopinsights.com/tech/react-native). Its method extracts SDKs from shipped apps ([desktopinsights.com/tech](https://desktopinsights.com/tech)). It counts AppKit in only 60 apps, so its detection undercounts native toolkits; read it as a relative signal between web-shell frameworks, not an absolute share.
- Stars: the GitHub REST API (`/repos/{owner}/{repo}`) for `electron/electron`, `tauri-apps/tauri`, `flutter/flutter`, `dotnet/maui`, `AvaloniaUI/Avalonia`, `unoplatform/uno`, `JetBrains/compose-multiplatform`, `qt/qtbase`, `microsoft/react-native-windows` and `microsoft/react-native-macos`.
- Downloads: `api.npmjs.org/downloads/point/last-week/{pkg}` for 2026-11-07 to 2026-11-13.
- Releases: [electron releases](https://github.com/electron/electron/releases); [endoflife.date/electron](https://endoflife.date/api/electron.json); [tauri releases](https://github.com/tauri-apps/tauri/releases); [Flutter release feed](https://storage.googleapis.com/flutter_infra_release/releases/releases_macos.json); [dotnet/maui releases](https://github.com/dotnet/maui/releases); [NuGet Avalonia](https://www.nuget.org/packages/Avalonia); [Avalonia releases](https://github.com/AvaloniaUI/Avalonia/releases); [Avalonia 12.0 announcement](https://avaloniaui.net/whats-new/12-0); [NuGet Uno.WinUI](https://www.nuget.org/packages/Uno.WinUI); [compose-multiplatform releases](https://github.com/JetBrains/compose-multiplatform/releases); [endoflife.date/qt](https://endoflife.date/api/qt.json); [react-native-windows releases](https://github.com/microsoft/react-native-windows/releases); [npm react-native-macos](https://registry.npmjs.org/react-native-macos).
- Apps: [electronjs.org](https://www.electronjs.org/); [Tauri apps (secondary)](https://jlw-newsletter.pages.dev/jlw-2026-01-26-tauri.html); [Canonical: Flutter and Ubuntu](https://ubuntu.com/blog/flutter-and-ubuntu-so-far); [Launchpad app-center](https://edge.launchpad.net/app-center); [Desktop Insights .NET MAUI](https://desktopinsights.com/tech/net-maui); [Avalonia showcase](https://avaloniaui.net/showcase); [TechCrunch on Uno customers](https://techcrunch.com/2025/08/12/in-a-world-of-vibe-coding-startups-uno-platform-is-targeting-enterprise-developers); [JetBrains Toolbox case study](https://blog.jetbrains.com/kotlin/2021/12/compose-multiplatform-toolbox-case-study/); [Microsoft: Office modernizes with React Native](https://devblogs.microsoft.com/react-native/2025-05-09-office-modernize).

**JetBrains survey.** The JetBrains Developer Ecosystem report's cross-platform question is about mobile (Flutter, React Native, KMP); no desktop breakdown was found. Plan 002 already cites the mobile figures. ([State of Developer Ecosystem 2025](https://devecosystem-2025.jetbrains.com/))

### A.2 Plugins a lane could attach to (from `ls` and `README.md`)

| Existing plugin | Folder | What a desktop lane would reuse |
|---|---|---|
| `fe-react` | `frontend/react/` | The renderer of an Electron or Tauri app: React, Vite, `forms`, `data-fetching`, `test-ids`, `component-testing` |
| `fe-blazor` | `frontend/blazor/` | Blazor Hybrid (`BlazorWebView` in MAUI, WPF or WinForms) |
| `mobile-react-native` | `mobile/react-native/` | React Native for Windows and macOS (out-of-tree platforms on the same RN 0.83 to 0.85 line) |
| `mobile-android` | `mobile/android/` (has a `kotlin-multiplatform` skill) | A Compose Multiplatform `jvm("desktop")` target added to the KMP lane |
| `be-rust` | `backend/rust/` | Tauri's Rust core: `async-concurrency`, `unit-testing`, `code-review` |
| `desktop-windows` (planned) | n/a | WinUI 3 and WPF XAML skills transfer to Avalonia (XAML), Uno (the WinUI API) and the MAUI Windows head (WinUI 3) |

### A.3 Verdicts

| Framework | Verdict | Why |
|---|---|---|
| **Electron** | **Lane of `fe-react`** (an `electron` skill covering the process model, IPC and `contextIsolation` security, packaging, signing and notarization, and auto-update). It is the first candidate to become its own plugin if the lane grows past one skill set. | It is #1 on every measure: the largest SO share of any desktop shell, 9.4% of tracked apps and 12.5M npm downloads a week. The renderer *is* a React app, so a separate plugin would duplicate `fe-react`. |
| **Tauri 2** | **Lane of `fe-react`** for the web front end, sharing the desktop-shell skill with Electron. Rust commands point to `be-rust` (`async-concurrency`, `unit-testing`). Teach Tauri 2; watch 3.0, which is still alpha. | It is #2 by shipped apps (6.3%) with 4.8M downloads a week. Its stack splits naturally across two existing plugins. |
| Flutter desktop | **Deferred** to the Flutter plugin that plan 002 (D12) already queued, as a desktop target inside it. | Desktop adoption is tiny (52 apps, 0.2%). It belongs with Flutter mobile, not with the native desktop plugins. |
| .NET MAUI | **Lane of `desktop-windows`**: the MAUI Windows head is WinUI 3. A Blazor Hybrid pointer goes to `fe-blazor`. No plugin. | MAUI 11 is GA (2026-11-10), but it has 3.1% SO share and 0.8% of tracked apps with no notable desktop apps. Plan 002's revisit condition is met, and the evidence still does not justify more than a lane. |
| **Avalonia 11/12** | **Lane of `desktop-windows`**, a cross-platform .NET XAML lane. Version lanes: 12.x primary, 11.3 supported (both are still patched). | It is the most credible cross-platform .NET desktop stack: 31.8k stars, notable adopters (JetBrains, Unity), and 12.0 stable since April 2026 with patches every few weeks. |
| Uno Platform | **Mention only**, inside the `desktop-windows` WinUI skills ("the WinUI API on Skia; WinUI skills transfer"). | 10.1k stars; 7.0 shipped in November 2026; no independent evidence of desktop adoption. |
| Compose Multiplatform Desktop | **Lane of `mobile-android`'s KMP lane** (a `jvm("desktop")` target), following plan 002 A5. | Same language, Gradle and Compose. JetBrains Toolbox ships on it. 1.12 is stable. |
| Qt 6 | **Deferred** (no C++/QML category in the library). Revisit on demand. | It has real share (7.3% SO, 3.8% of tracked apps), but it needs a new language lane, and nobody has asked for one. |
| React Native for Windows / macOS | **Mention only**, inside `mobile-react-native` ("out-of-tree platforms exist; not taught"). | Only 45 tracked apps. It mainly serves Microsoft's own use (Office). RN-macOS trails RN by two minors. |
| Wails, NW.js, Neutralino, GTK, WinForms | **Mention only** | marginal in every source above |

---

## Part B: desktop E2E automation, owned by the QA plugins

### B.1 The tools

| Tool | Platform | Latest (date) | Server / protocol | Status | Source |
|---|---|---|---|---|---|
| **Appium Mac2 driver** | macOS | **4.6.1** for Appium 3 (2026-11-06); 5.0.1 for Appium 4 (2026-11-13) | Appium, W3C; WebDriverAgentMac on XCTest | Active (releases every 1 to 3 weeks); 85k npm downloads a week | [npm](https://registry.npmjs.org/appium-mac2-driver), [compatibility table](https://github.com/appium/appium-mac2-driver/blob/master/docs/getting-started/index.md) |
| XCUITest for Mac (XCTest UI tests) | macOS | ships with Xcode | in-process, Swift | Apple's own framework; Mac2 is built on it | [Mac2 README](https://github.com/appium/appium-mac2-driver) |
| **Appium WinCore driver** | Windows | **3.3.2** for Appium 3 (2026-10-29); 4.1.1 for Appium 4 (2026-11-13) | Appium, W3C; native UIA3 | New: repo created 2026-03-16, first npm release 2026-09-02, 27 versions. Apache-2.0, under the `appium` org. 1.5k npm downloads a week. Shares maintainers with NovaWindows. | [README](https://github.com/appium/appium-wincore-driver), [npm](https://registry.npmjs.org/appium-wincore-driver), [contributors](https://api.github.com/repos/appium/appium-wincore-driver/contributors) |
| NovaWindows driver | Windows | 1.5.0 (2026-10-24); 2.0.0-preview.2 | Appium 2/3, W3C; PowerShell back end | Active. Its README describes the PowerShell back end as interim ("plan to update to a better, .NET-based backend"). 3.3k npm downloads a week. | [README](https://github.com/AutomateThePlanet/appium-novawindows-driver), [npm](https://registry.npmjs.org/appium-novawindows-driver) |
| Appium Windows driver | Windows | 6.3.1 (2026-10-08) | Appium 3 → WinAppDriver (JSONWP) | **Deprecated; repo archived.** Not compatible with Appium 4. | [README](https://github.com/appium/appium-windows-driver) |
| WinAppDriver | Windows | v1.2.99 (2021-07-01) | its own server | Unmaintained ("has not been maintained by Microsoft for years") | [releases](https://github.com/microsoft/WinAppDriver/releases), [appium-windows-driver README](https://github.com/appium/appium-windows-driver) |
| **FlaUI** (`FlaUI.UIA3`) | Windows, .NET only | **5.0.0** (2025-02-25); targets net48, net6.0-windows and net8.0-windows | in-process UIA2/UIA3, no server | Mature (3.2k stars; last push 2026-08-13). No release in 21 months. | [NuGet registration](https://api.nuget.org/v3/registration5-gz-semver2/flaui.uia3/index.json), [releases](https://github.com/FlaUI/FlaUI/releases) |
| FlaUI.WebDriver | Windows | v0.4.0 (2025-07-22) | W3C WebDriver server on FlaUI (`automationName: FlaUI`) | Pre-1.0 | [repo](https://github.com/FlaUI/FlaUI.WebDriver) |
| **Playwright `_electron`** | Electron apps (all OSes) | Playwright 1.65.1 | CDP | "Playwright has **experimental** support for Electron automation"; Electron v21+. **Node only**: the Java, .NET and Python `class-electron` pages return 404. | [docs](https://playwright.dev/docs/api/class-electron), [java 404](https://playwright.dev/java/docs/api/class-electron), [dotnet 404](https://playwright.dev/dotnet/docs/api/class-electron) |
| **Playwright WebView2** | Windows WebView2 hosts (WinUI 3, WPF, WinForms, MAUI-Windows, Tauri-Windows) | all four languages | `connectOverCDP` with `WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS=--remote-debugging-port=…` | Documented. Each test or worker needs its own `WEBVIEW2_USER_DATA_FOLDER`. | [dotnet docs](https://playwright.dev/dotnet/docs/webview2), [java docs](https://playwright.dev/java/docs/webview2) |
| WebdriverIO desktop services | Electron, Tauri | `@wdio/electron-service` 10.4.1; `@wdio/tauri-service` 1.5.1 (both 2026-10-24) | WebDriver | Active | [npm electron-service](https://registry.npmjs.org/@wdio/electron-service), [npm tauri-service](https://registry.npmjs.org/@wdio/tauri-service), [WebdriverIO Tauri page](https://webdriver.io/docs/desktop-testing/tauri) |
| tauri-driver | Tauri | n/a | WebDriver | Windows and Linux only when driven directly. On macOS, use the WDIO service's embedded server; CrabNebula's fork needs "a paid API key … for macOS". | [Tauri WebDriver docs](https://v2.tauri.app/develop/tests/webdriver/) |
| pywinauto | Windows, Python | 0.6.9 on PyPI; 1.0.0b1 tagged 2026-10-15 | in-process | Mention only: the library has no Python QA lane | [PyPI](https://pypi.org/pypi/pywinauto/json), [releases](https://github.com/pywinauto/pywinauto/releases) |

WebdriverIO's own Windows page still says there is "at the moment no stable driver for automating Windows applications" and does not mention WinCore or NovaWindows. The docs lag the drivers. ([webdriver.io/docs/desktop-testing/windows](https://webdriver.io/docs/desktop-testing/windows)) Its macOS page recommends Mac2. ([webdriver.io/docs/desktop-testing/macos](https://webdriver.io/docs/desktop-testing/macos))

### B.2 How each tool reads the test id

| Platform | What the developer sets | What the tool matches | Source |
|---|---|---|---|
| macOS (SwiftUI `.accessibilityIdentifier`, AppKit `setAccessibilityIdentifier`) | the accessibility identifier | Mac2's `accessibility id`, `id` and `name` strategies are all aliases of the XCTest `identifier` attribute. `predicate string` and `class chain` can also reference it. `useDomIdAsAccessibilityId` maps `WKWebView` DOM ids (needs the Accessibility permission). | [Mac2 locator strategies](https://github.com/appium/appium-mac2-driver/blob/master/docs/reference/locator-strategies.md), [Mac2 element attributes](https://github.com/appium/appium-mac2-driver/blob/master/docs/reference/element-attributes.md), [Apple XCUIElementAttributes.identifier](https://developer.apple.com/documentation/xcuiautomation/xcuielementattributes/identifier) |
| Windows (`AutomationProperties.AutomationId` in WinUI 3 / WPF; control ID in Win32) | the UIA `AutomationId` | WinCore's `accessibility id` (`~Id` in WDIO) is a native `PropertyCondition(AutomationId)`, rated "A+ (Fastest)". NovaWindows: `accessibility id` = "AutomationId attribute in inspect.exe". FlaUI: `ByAutomationId`. FlaUI.WebDriver: `accessibility id`. | [WinCore API.md](https://github.com/appium/appium-wincore-driver/blob/main/API.md), [NovaWindows README](https://github.com/AutomateThePlanet/appium-novawindows-driver), [FlaUI.WebDriver README](https://github.com/FlaUI/FlaUI.WebDriver) |
| Windows: uniqueness | n/a | `AutomationId` is unique **among siblings only**, not across the tree. It is absent on WPF elements without an ID or `x:Uid` and on Win32 controls without a control ID. Search from the app window or a container, not the desktop root. | [Microsoft Learn: Use the AutomationID property](https://learn.microsoft.com/en-us/dotnet/framework/ui-automation/use-the-automationid-property) |
| Windows: Uno | n/a | `AutomationId` only takes effect when the `IsUiAutomationMappingEnabled` MSBuild property is `true` | [Uno AutomationProperties](https://platform.uno/docs/articles/features/accessibility/automation-properties.html) |

The `mobile-screen-explorer` contract carries over unchanged. A single page-source read inventories structure and ids, because the id is an attribute of every node (`identifier` on macOS, `AutomationId` on Windows). Elements with no id fall back to another locator, and each fallback is a row in `missing-testids.md`.

### B.3 CI constraints

| Host | Constraint | Source |
|---|---|---|
| Windows, any desktop driver | UI tests for desktop apps need an **interactive session**: the agent runs as an interactive process with autologon, not as a service. Disconnecting RDP locks the session, so use `tscon … /dest:console`. Run in parallel across machines, not inside one (focus is exclusive). | [Azure Pipelines: UI testing considerations](https://learn.microsoft.com/en-us/azure/devops/pipelines/test/ui-testing-considerations) |
| Azure Pipelines Microsoft-hosted agents | "Visible UI testing is not supported in Microsoft-hosted agents" (fails with "element not interactable"). **Desktop E2E on Azure DevOps needs self-hosted agents.** | same page |
| GitHub-hosted `windows-latest` | Reported to give an interactive desktop session, so FlaUI and WinAppDriver work. **Secondary sources only.** | [tessl FlaUI notes](https://tessl.io/registry/testland/flaui-tests/files/references/flaui-api.md), [tessl WinAppDriver CI notes](https://tessl.io/registry/testland/winappdriver/files/references/locators-and-ci.md) |
| macOS, Mac2 | Needs Xcode 13+ and macOS 11.3+. Grant **Xcode Helper** the Accessibility permission. Silence the automation-mode prompt with `automationmodetool enable-automationmode-without-authentication`. Finding, clicking and typing do **not** need the Accessibility permission; moving or resizing windows and `useDomIdAsAccessibilityId` do, granted to `WebDriverAgentRunner-Runner.app`. The grant is lost on every ad-hoc rebuild unless WDA is signed with a stable identity. | [Mac2 getting started](https://github.com/appium/appium-mac2-driver/blob/master/docs/getting-started/index.md), [Mac2 accessibility permission](https://github.com/appium/appium-mac2-driver/blob/master/docs/guides/accessibility-permission.md) |
| macOS, Mac2 parallelism | "Parallel execution of multiple Mac2 driver instances is **highly discouraged**." There is one session per server, and a new session terminates the old one. | [Mac2 parallel tests](https://github.com/appium/appium-mac2-driver/blob/master/docs/guides/parallel-tests.md) |
| macOS, GitHub-hosted runners | WDA problems on hosted macOS images are reported and unresolved. Untested here. | [actions/runner-images discussion 9781](https://github-redirect.dependabot.com/actions/runner-images/discussions/9781) |

### B.4 Device clouds

| Vendor | Native desktop apps | Source |
|---|---|---|
| BrowserStack | **No.** "Installing native applications on Windows or MacOS platform is not supported"; App Live and App Automate cover mobile only. | [BrowserStack FAQ](https://www.browserstack.com/support/faq/live/test-session/i-want-to-test-a-native-windows-or-macos-app-is-this-possible-to-do-in-live) |
| Sauce Labs | **Electron apps only, beta**, on Windows 10/11 and macOS (macOS 14+ needs Premium). No native desktop app support found. | [Sauce Labs Electron docs](https://docs.saucelabs.com/web-apps/automated-testing/electron/) |
| TestMu AI (LambdaTest) | Blog posts on WinAppDriver on its grid and on KaneAI for Electron. No current docs found. | [TestMu blog: WinAppDriver](https://dev.to/testmuai/how-to-automate-desktops-apps-using-winappdriver-2pe), [TestMu blog: desktop apps](https://www.testmuai.com/blog/test-desktop-apps/) |

**Consequence:** desktop E2E runs on owned hardware: self-hosted Windows agents with autologon, and Macs with Xcode. A `device-cloud` desktop section would carry one paragraph saying so, not a recipe.

### B.5 Client support per QA lane

| Lane | Mac2 | WinCore / NovaWindows | Electron | WebView2 | Source |
|---|---|---|---|---|---|
| Java (`java-client` 11.0.0, 2026-10-07) | `io.appium.java_client.mac.Mac2Driver` + options | `WindowsDriver` exists, but `WindowsOptions` hard-sets `automationName` to `Windows`. For WinCore, override it to `Wincore` (or `NovaWindows`) or use `BaseOptions`. | Playwright Java: no Electron API | `connectOverCDP` | [Maven metadata](https://repo1.maven.org/maven2/io/appium/java-client/maven-metadata.xml), [mac package](https://github.com/appium/java-client/tree/master/src/main/java/io/appium/java_client/mac), [WindowsOptions.java:75](https://github.com/appium/java-client/blob/master/src/main/java/io/appium/java_client/windows/options/WindowsOptions.java) |
| .NET (`Appium.WebDriver` 9.0.0, 2026-09-16; FlaUI 5.0.0) | `OpenQA.Selenium.Appium.Mac` | `OpenQA.Selenium.Appium.Windows` + `AppiumOptions` with `automationName`; **or FlaUI in-process** | Playwright .NET: no Electron API | `ConnectOverCDPAsync` | [NuGet Appium.WebDriver](https://api.nuget.org/v3/registration5-gz-semver2/appium.webdriver/index.json), [client tree](https://github.com/appium/appium-dotnet-driver/tree/main/src/Appium.Net/Appium) |
| TypeScript (WebdriverIO 10.2.0; Playwright 1.65.1) | `appium:automationName: 'mac2'` | `'Wincore'` / `'NovaWindows'` (WinCore's README examples are WDIO) | **Playwright `_electron`** (experimental) or `@wdio/electron-service` | `connectOverCDP` | [npm webdriverio](https://registry.npmjs.org/webdriverio), [WinCore README](https://github.com/appium/appium-wincore-driver) |

Exploration tooling: `appium-mcp` 1.99.3 (2026-11-04) creates sessions embedded for Android and iOS only. Desktop drivers work through its "general" mode against a running Appium server, and its README shows a `mac2` capability example. ([appium-mcp README](https://github.com/appium/appium-mcp)) A separate `wincore-mcp` exists but has 1 star. ([verisoft-ai/wincore-mcp](https://github.com/verisoft-ai/wincore-mcp))

### B.6 Recommendation

**Build it as a desktop skill set inside the three existing QA plugins, not as a new plugin.** Each of `qa/java`, `qa/dotnet` and `qa/typescript` gets three skills that mirror the mobile trio:

- `desktop-project-setup`: Appium 3 server, pinned drivers, OS prerequisites, a first smoke run.
- `desktop-screen-explorer`: page-source inventory through `appium-mcp` general mode, and the same `missing-testids.md` hand-off keyed on `identifier` / `AutomationId`.
- `desktop-window-objects`: window objects that expose intent; multi-window switching.

Shared rules and the CI and permissions facts go under `qa/_shared`. The `device-cloud` skill gets a "desktop: none; self-host" note.

| Lane | Teach | Alternative documented | Do not teach |
|---|---|---|---|
| **Java** | Appium 3.9.x + `java-client` 11 + TestNG: **Mac2 `4.6.1`** (macOS) and **WinCore `3.3.2`** (Windows), both installed with an explicit `@version` | NovaWindows 1.5.0 if WinCore misbehaves on a legacy app | the Windows driver, WinAppDriver |
| **.NET** | the same Appium pair through `Appium.WebDriver` 9 + NUnit, for one locator contract and one server shape across all three lanes | **FlaUI 5.0.0 (UIA3)** for Windows-only suites that live beside a WPF or WinUI codebase and want no Node/Appium server; WebView2 content through Playwright .NET `ConnectOverCDPAsync` | the Windows driver, WinAppDriver |
| **TypeScript** | WebdriverIO 10 + Appium (Mac2 4.6.1, WinCore 3.3.2) for native apps; **Playwright `_electron`** for Electron apps; `@wdio/tauri-service` for Tauri | `@wdio/electron-service` when the suite is already WDIO | `tauri-driver` direct on macOS (unsupported) |

Version lane: **Appium 3 primary; Appium 4 tagged "from 4.0 GA"** with `mac2` 5.x and `wincore` 4.x. Teach the explicit `appium driver install mac2@4.6.1` form, because the unpinned install now resolves to drivers that need Appium 4. This mirrors the existing pin note for `uiautomator2` 8.x / `xcuitest` 12.x, which also have Appium-4-only majors now (9.x / 13.x). The mobile skills need the same explicit-pin fix.

Risk to record as a plan decision: WinCore is eight weeks old on npm. If plan 012 judges that too young, the fallback is NovaWindows 1.5.0, which has the same `accessibility id` → AutomationId contract, so the locators carry over.

---

## Not verified

- **What an unpinned `appium driver install mac2` does on Appium 3.9.1**: whether it resolves to the last compatible 4.6.1 or tries 5.x and fails. Pin explicitly either way.
- **Appium 4 GA date.** Only betas exist (beta.0 on 2026-09-19 through beta.8 on 2026-11-13). No GA date was found.
- **GitHub-hosted `windows-latest` interactive session**: secondary sources only. No GitHub doc was found.
- **Mac2 on GitHub-hosted macOS runners**: one unresolved WDA report. Whether `automationmodetool` (which needs sudo) and Xcode Helper's Accessibility grant can be scripted on hosted images is untested.
- **WinCore maturity on real WinUI 3 / WPF apps**: no independent reports. WinCore and NovaWindows share contributors (`teo-nikolov`, `yuri-schwab`), but no source states that WinCore is NovaWindows's successor.
- **Whether WinUI 3 falls back to `x:Name` when `AutomationId` is unset.** The WPF `GetAutomationId` behaviour differs and was not checked against WinUI 3. Confirm with Accessibility Insights on a sample app.
- **SO 2024 admired/desired figures for Electron and Tauri.** The scraped chart did not pair names with values unambiguously, so they are omitted.
- **Desktop Insights for Uno, Compose Multiplatform, SwiftUI and WinForms.** Those pages failed to load, and the dataset undercounts native toolkits (AppKit = 60 apps).
- **Notable Tauri apps.** Only secondary sources were found (Spacedrive, AppFlowy, Clash Verge).
- **Qt notable-app list.** Not fetched.
- **The JetBrains survey's desktop framework breakdown.** None was found; its cross-platform question covers mobile.
- **Sauce Labs Electron beta's current status, and TestMu AI desktop-app support.** Only marketing or blog pages were found.
- **FlaUI on .NET 10.** The package targets `net8.0-windows`, and forward compatibility to net10 is assumed, not tested.
