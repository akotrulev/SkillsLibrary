---
name: desktop-testing
description: Use when a qa-desktop-* agent plans or reviews native macOS or Windows E2E: drivers, test-id contract, CI hosts. Triggers "desktop E2E rules". Not for mobile (qa-mobile-*) or web (qa-ui-*).
---

# QA — Native Desktop E2E Rules (Shared)

Cross-stack. The `qa-desktop-typescript`, `qa-desktop-java` and `qa-desktop-dotnet` agents load this skill first; their `desktop-project-setup`, `desktop-screen-explorer` and `desktop-window-objects` skills do the per-language work. This skill owns **what is the same in every lane**: the pinned Appium drivers, the test-id contract with the dev agents, how window objects behave, and the CI facts that decide where a desktop suite can run.

Scope: **native** macOS (SwiftUI, AppKit) and Windows (WinUI, WPF, WinForms, C++/WinRT) apps. Electron and Tauri shells are out of scope (plan 012, Q1); embedded WebView2 content is reached through Playwright over CDP (see *The test-id contract*).

## Version lane

Verified 2026-11-15. The lane is **Appium 3 primary**; Appium 4 is a tagged lane (below).

| Concern | Teach | Notes |
|---|---|---|
| Appium server | **3.8.0**, the library pin (`tools/qa-version-check.py`) | Latest is 3.9.1; the library pin is not moved here |
| macOS driver | **Mac2 4.6.1**, `appium driver install mac2@4.6.1` | Peer range `appium ^3.0.0-rc.2`, which includes 3.8.0. Mac2 5.x needs Appium 4. `automationName` is `mac2`, `platformName` is `mac` |
| Windows driver | **WinCore 3.3.2**, `appium driver install --source=npm appium-wincore-driver@3.3.2` | Peer range `appium ^3.0.0-rc.2`, includes 3.8.0. WinCore 4.x needs Appium 4. `automationName` is `Wincore`, `platformName` is `Windows`. On npm since 2026-09: young, so a real app may need the fallback |
| Windows fallback | **NovaWindows 1.5.0**, `appium driver install --source=npm appium-novawindows-driver@1.5.0` | Peer range `appium ^3.0.0-rc.2`. `automationName` is `NovaWindows`. Same `accessibility id` → `AutomationId` contract, so locators carry over. PowerShell back end, which its README calls interim |
| Windows-only .NET | **FlaUI 5.0.0** (UIA3, in process) | `qa-desktop-dotnet` only, chosen per suite and never mixed with Appium in one suite |
| Clients | `webdriverio` 10.0.2 · `java-client` 11 (`Mac2Driver`) · `Appium.WebDriver` 9.0.0 | The library pins; each lane skill states its own |
| Never taught | the legacy **Appium Windows driver** and **WinAppDriver** | Deprecated and archived; WinAppDriver's last release was 2021 (D9) |

**Pin drivers with an explicit `@version`.** An unpinned `appium driver install mac2` may resolve to a major that needs Appium 4. After install, `appium driver list --installed` must show `mac2@4.6.1` and `wincore@3.3.2`. A driver whose peer range excludes the server in use is a mismatch to report, never to work around by bumping the Appium pin.

## Drivers and capabilities

| | macOS (Mac2) | Windows (WinCore) |
|---|---|---|
| `platformName` | `mac` | `Windows` |
| `appium:automationName` | `mac2` | `Wincore` |
| App under test | `appium:bundleId` (default is Finder: always set it). `appium:appPath` launches by path when the bundle id is set. `appium:arguments`, `appium:environment` | `appium:app`: exe path or UWP AUMID. `appium:appArguments`, `appium:appWorkingDir`, `appium:appEnvironment`. `appium:app: Root` attaches to the desktop for launching by shortcut |
| Keep state between sessions | `appium:noReset: true` | `appium:shouldCloseApp: false` |
| Attach to a running window | `bundleId` of the running app (an already-running app is activated) | `appium:appTopLevelWindow`: a window handle |
| Launch wait | `macos: activateApp` / `launchApp` | `appium:ms:waitForAppLaunch`: seconds, up to 120 |

Capability keys carry the `appium:` prefix except `platformName`. Credentials and app paths come from environment variables, never from source.

## The test-id contract

The same contract as `mobile-screen-explorer`: one id per element, written by the dev agent, read by the suite with `accessibility id`. The dev side is `desktop-macos:test-ids` and `desktop-windows:test-ids`; they carry the naming and static-row rules.

| Platform | The developer sets | The suite reads |
|---|---|---|
| macOS | SwiftUI `.accessibilityIdentifier`, AppKit `setAccessibilityIdentifier` | Mac2 `accessibility id`: `id`, `name` and `accessibility id` are **all aliases of the XCTest `identifier`**. `predicate string` and `class chain` can also reference it |
| Windows | `AutomationProperties.AutomationId` (WinUI, WPF, C++/WinRT XAML); `Control.Name` on WinForms (not verified: confirm in the live tree); the control ID on Win32 | WinCore and NovaWindows `accessibility id` (`~Id` in WebdriverIO). FlaUI: `ByAutomationId` |
| Embedded WebView2 | the page's own `data-testid` | Playwright `connectOverCDP` with `WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS=--remote-debugging-port=<port>`; each worker needs its own `WEBVIEW2_USER_DATA_FOLDER` |

Rules that follow:

- **`accessibilityLabel` and `AutomationProperties.Name` are for people, never ids.** A locator on `label` or `name` is a label locator and gets a `missing-testids.md` row.
- **WinCore's `id` strategy is the `RuntimeId`**, a number that changes every run: never use it as a stable locator.
- **An `AutomationId` is unique among siblings only.** Two rows or two screens may repeat one. Every list and container carries its own id; a locator starts at the app window or a container and descends, never at the desktop root. Rows share one static id and are picked inside their container, by position or by the text of a child.
- **On macOS a row carries one static id** (`Library.Row`), found inside its container and addressed by index. `.accessibilityElement(children: .combine)` hides child ids: assert on the row.
- **Fallbacks are reported, not hidden.** An element with no id falls back to `class chain` / `predicate string` (macOS), `name` / `class name` / `xpath` (Windows) or `ByName` (FlaUI). Each fallback is a row in `missing-testids.md`, which routes to the **`desktop-macos`** agent or the **`desktop-windows`** agent. Test ids and every app-side fix are theirs, never the QA agent's.
- Uno apps expose `AutomationId` only with the `IsUiAutomationMappingEnabled` build property set to `true`.

## Window objects

- **A window object exposes user intent, not elements.** `signIn(user)`, `openAlbum(title)`, `confirmSave()`: never `emailField` or `getButton`. The test id lives in the object as a `private static readonly` constant; accessors are private.
- **One class per window or dialog**, plus scoped components for repeating rows that are re-resolved from their container on each call.
- **`verifyWindowLoaded()` asserts one landmark** (a container id) and is the only assertion inside a window object. No business logic, no API calls.
- **Platform differences live in a locator map**, never an `if (isMac)` inside an action. A cross-platform suite has one window object interface per window only when two real apps share it; otherwise one object per platform.
- **Menus are driven the way the platform does it.** macOS menu-bar items are not addressed by id here (not verified that a SwiftUI command's identifier reaches the menu item): locate them by `title` through `predicate string` and record each as a `missing-testids.md` row. Windows menu items carry `AutomationId` like any element; open the menu first, then find the item.

## Multi-window and dialogs

- A window is a separate scope. Select the window first, then find the id inside it; ids repeat across document windows, so never encode a window or document number into an id.
- **Mac2:** `macos: listWindows` (driver 4.5.0 and later) returns each window's `windowId`, `title`, `isMain` and `isFocused`. Moving and resizing (`macos: adjustWindow` with `x`, `y`, `width`, `height`) and the `maximized` state need the Accessibility permission for `WebDriverAgentRunner-Runner.app`; the `normal`, `minimized` and `fullscreen` states do not.
- **WinCore:** `getWindowHandles()` omits untitled windows; `windows: getWindows` returns `{ handle, title, className }` for every visible top-level window. Switch with `switchToWindow(handle)` or `windows: switchToWindowByTitle`. A modal dialog or message box is a window of its own: switch to it, act, switch back.
- **A system dialog** (a file open/save panel, a permission prompt, a UAC prompt) belongs to another process. Drive the panel through its own accessibility tree where the driver can see it; a UAC prompt on the secure desktop cannot be driven, so a test never requires elevation.
- **Quit with unsaved work asks first**: assert the prompt appears, then choose, rather than force-killing the app.

## Waits

- **No fixed sleeps**: no `Thread.Sleep`, `browser.pause`, `time.sleep`, `Task.Delay` as a wait. Wait on a condition: element displayed, enabled, a value changed, a window handle count changed.
- A wait is a named wait condition on the base window object, with a timeout budget and a failure message naming the element and the window. A test never inlines a poll.
- **Native desktop animations and window opens are slow.** Wait for the landmark of the destination window, never a duration.
- `delayBeforeClick` and `delayAfterClick` (WinCore) are driver tuning for one legacy control, never a replacement for a wait.

## CI and hosts

| Host | Fact |
|---|---|
| Windows, any desktop driver | The agent must run as an **interactive process with autologon**, not as a service. Disconnecting RDP locks the session: use `tscon <id> /dest:console`. Focus is exclusive, so parallelise across machines, never inside one |
| Azure Pipelines | **Microsoft-hosted agents do not support visible UI testing** ("element not interactable"). Use **self-hosted** agents |
| GitHub-hosted `windows-latest` | Reported to give an interactive session; **secondary sources only**, not verified |
| macOS, Mac2 | Needs Xcode 13+ and macOS 11.3+. Grant **Xcode Helper** the Accessibility permission. `automationmodetool enable-automationmode-without-authentication` (needs sudo) silences the automation-mode prompt. Finding, clicking and typing need no Accessibility grant; moving, resizing and `useDomIdAsAccessibilityId` do, granted to `WebDriverAgentRunner-Runner.app`. The grant is lost on every ad-hoc rebuild unless WDA is signed with a stable identity |
| macOS, parallelism | **One Mac2 session at a time** per server; a new session ends the old one. Parallel Mac2 instances are highly discouraged: `maxInstances: 1` (or one worker), and one Mac per parallel lane |
| macOS, GitHub-hosted runners | WDA problems on hosted images are reported and unresolved. Not verified |

## Device clouds: none

**No device cloud runs native desktop apps.** BrowserStack: no (App Live and App Automate are mobile only). Sauce Labs: Electron apps only, in beta. So desktop E2E runs on **owned hardware**: self-hosted Windows agents with autologon, and Macs with Xcode. Do not write a cloud recipe; say so and name the self-hosted route.

## Appium 4 (from 4.0 GA)

Appium 4 is in beta (beta.8 on 2026-11-13) and has **no GA date**. From 4.0 GA the lane moves to **Mac2 5.x** and **WinCore 4.x**, and the client pins move with the library. Until then every recipe teaches the Appium 3 pair above, and any Appium 4 line is tagged "from 4.0 GA". Never mix: Mac2 5.x or WinCore 4.x refuse an Appium 3 server.

## Exploration

Page source is the evidence: a single read inventories structure and ids, because the id is an attribute of every node (`identifier` on macOS, `AutomationId` on Windows). `appium-mcp` creates embedded sessions for Android and iOS only; desktop sessions work through its **general mode against a running Appium server**. Not connected → say so and fall back to the app source, Accessibility Inspector (macOS) or Accessibility Insights (Windows) output the user supplies. Never fabricate a locator.

## Not verified here

- WinCore on real WinUI 3 and WPF apps (no independent reports); whether WinUI 3 falls back to `x:Name` when `AutomationId` is unset.
- GitHub-hosted `windows-latest` and macOS runners for desktop UI tests.
- macOS menu-bar item ids from SwiftUI commands.
- The Appium 4 GA date.

## Handoffs

- Scaffold, explore, window objects → the lane's `desktop-project-setup`, `desktop-screen-explorer`, `desktop-window-objects`
- Missing ids and every app-side fix → the `desktop-macos` agent (`test-ids`) or the `desktop-windows` agent (`test-ids`)
- Test-case design and bug reports → `qa-test-case-designer`
- Flake quarantine and Allure → `qa-reporting-<lang>`; the self-hosted pipeline → `qa-cicd-<lang>`
- Acceptance tests written before the app exists → `qa/_shared/test-first`
- Mobile apps → `qa-mobile-<lang>`; browser and WebView content in a browser → `qa-ui-<lang>`
