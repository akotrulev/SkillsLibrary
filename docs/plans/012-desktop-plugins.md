# 012 — Desktop plugins: macOS (Swift / SwiftUI) and Windows 11 (WinUI / C#, C++/WinRT) — plan (2026-11-15)

**Goal:** Two marketplace plugins in one new `desktop/` domain. `desktop-macos` covers Swift, SwiftUI and the AppKit lane. `desktop-windows` covers WinUI on Windows App SDK 2.x with C#, plus WPF, WinForms and C++/WinRT lanes. Each has the library's plugin shape: a coding standard installed as path-scoped rules, the common use-case skills, a step-by-step agent that works on greenfield and brownfield, two commands and a conformance audit. A shared desktop layer (distribution, security, observability) is bundled into both, and native Auth0 skills ship with them. The QA plugins gain a desktop E2E lane: three skills and a `qa-desktop-<lang>` agent in each of `qa-java`, `qa-dotnet` and `qa-typescript`, driven by the same test ids the dev agents emit.

**Status:** Planned 2026-11-15; no task has landed. Research is done and saved beside this plan in `docs/research/012-desktop-plugins/{macos,windows,cross-platform-and-qa}.md`. Every fact in §4 comes from those files, verified on 2026-11-15; the §4.6 items are not verified. **Next:** C1, then S1–S3, M1 and W1 side by side. Built but unverified, once landed: no agent has been run against a real Mac or Windows app, and no desktop E2E suite has run on a real runner.

**Test design:** none. This plan serves no stories (it builds skills, not a product), so it has no `TD` tasks.
**Documentation task:** none. This library's documentation is `CLAUDE.md`'s map, `docs/skills-catalog.md` and `README.md`, which G1 writes from the files that landed (as plan 002's G1 did). `be-documenter` documents applications, not a skills library.

**The cost, accepted and stated once:** the authoring tasks are documents with `Gate: none`, and the plan's runnable checks run once, in G1. Intermediate commits are not known to pass the library check, so the plan cannot be stopped halfway and trusted. `desktop/` and the new auth folders stay on CLAUDE.md's under-construction line until G1, so a half-built domain is never uploaded.

---

## 1. What already exists, and what is missing

| Need | Today | Gap |
|---|---|---|
| A desktop domain and plugins | Nothing. `grep -ril "winui\|appkit" --include='*.md'` finds only design-corpus rows and QA cloud notes. The mobile plugins are the shape to follow (`docs/plans/implemented/002-mobile-plugins.md` §2, §6–§8) | `desktop/` domain, `desktop-macos` and `desktop-windows` (C1, M1–M5, W1–W6) |
| A desktop coding standard | Web, mobile and backend code rules only (`CLAUDE.md:185` § Mobile code rules, `:237` § Backend code rules) | `## Desktop code rules` (§5) in `CLAUDE.md`, plus each plugin's `rules` skill (C1, M5, W6) |
| macOS skills | `mobile/ios/skills/*` covers Swift and SwiftUI on iPhone/iPad only. It cannot be registered by a desktop plugin (`tools/plugin-surface-check.py` rule 5, one category per folder) | 25 skills, agent, 2 commands (M1–M5) |
| Windows skills | `frontend/blazor` is web; `backend/dotnet` is services. Nothing teaches XAML, Windows App SDK, MSIX or UI Automation | 25 skills incl. WPF, WinForms and C++/WinRT lanes, agent, 2 commands (W1–W6) |
| Signing, notarization, MSIX, auto-update, desktop security, desktop telemetry | `mobile/_shared/{release,security,observability}` are phone-only (TestFlight, Play, MASVS) | Three `desktop/_shared/` skills with per-stack references and audit fragments (S1, S2) |
| Native desktop auth | `auth/auth0-ios` and `auth/auth0-android` (mobile category); `auth/auth0-blazor` and `auth/auth0-react` (web) | `auth/auth0-macos`, `auth/auth0-windows` (S3) |
| Desktop E2E in the QA plugins | Mobile only: `qa/*/skills/mobile-{project-setup,screen-explorer,screen-objects}`, `qa/*/agents/qa-mobile-<lang>.md`, `qa/*/commands/mobile.md`, `qa/*/skills/rules/mobile-tests.md`. `device-cloud` does not mention desktop apps | `qa/_shared/desktop-testing`, three `desktop-*` skills, a rules file, an agent and a command in each QA plugin (E1–E3) |
| Design layer for desktop | `design/ui-ux-pro-max/data/stacks/` already has `swiftui.csv`, `winui.csv`, `wpf.csv`, `uwp.csv`, `avalonia.csv`, `uno.csv` | Query with `--stack swiftui | winui | wpf`; no corpus change |
| The planning lane and the surface check know desktop | Stack tokens `be · fe · mobile · ts · data · infra · qa · docs · human` (`engineering-practices/writing-plans/references/plan-format.md:119`, `backend/_shared/delivery-plan/SKILL.md:44,128,345`, `backend/_shared/agents/solution-planner.md`); `STACK_CATEGORIES = ("qa", "fe", "be", "mobile")` at `tools/plugin-surface-check.py:35` | A `desktop` token, the two agents in the planner's routing, `desktop` added as a category (I1, D13) |

## 2. The shape

```
desktop/
  _shared/                      bundled into both plugins
    distribution/  security/  observability/
  macos/                        plugin desktop-macos
    skills/ (25)  agents/desktop-macos.md  commands/{desktop-macos,audit}.md
  windows/                      plugin desktop-windows
    skills/ (25)  agents/desktop-windows.md  commands/{desktop-windows,audit}.md
auth/auth0-macos/  auth/auth0-windows/
qa/_shared/desktop-testing/                    bundled into the three QA plugins
qa/<lang>/skills/{desktop-project-setup,desktop-screen-explorer,desktop-window-objects}/
qa/<lang>/skills/rules/desktop-tests.md  qa/<lang>/agents/qa-desktop-<lang>.md  qa/<lang>/commands/desktop.md
```

| | `desktop-macos` | `desktop-windows` |
|---|---|---|
| Own skills | `desktop/macos/skills/*` | `desktop/windows/skills/*` |
| Shared desktop | all 3 `desktop/_shared/*` | same |
| Auth | `auth/auth0-macos` | `auth/auth0-windows` |
| Dependencies | `dev`, `design` (as every `mobile-*` plugin) | same |
| Agent | `desktop-macos` | `desktop-windows` |

**Naming.** The plugins and agents are `desktop-macos` and `desktop-windows`. Skill `name:` values follow the current convention: short topic names without the stack prefix, unique within the plugin, never a Claude Code built-in (`tools/plugin-surface-check.py` rules 2–4). Read `mobile/ios/skills/*/SKILL.md` frontmatter for the pattern: the folder `basics` is named `concepts`, and the folder `rules` is named `rules`. Orientation caches go in `docs/agent-context/desktop-<os>.md`. Audit reports go in `docs/audits/<NNN>-desktop-<os>-conformance-r<N>.md`.

## 3. Which stacks, and why

The user asked for native macOS and native Windows 11 applications, built the same way as the other plugins. The evidence is in `cross-platform-and-qa.md` Part A and `windows.md` §1.

| Platform | Primary | Lanes | Not taught (named in `basics`, detected, handed off) |
|---|---|---|---|
| macOS | SwiftUI on the macOS 27 SDK, Swift 6.4 | AppKit (brownfield, `appkit`), mixed SwiftUI + AppKit hosting | Mac Catalyst (no new apps; migration path only), Electron/Tauri (Q1) |
| Windows | **WinUI on Windows App SDK 2.6.x, C#, .NET 10 LTS, packaged MSIX, MVVM with CommunityToolkit.Mvvm**. Microsoft calls WinUI "the recommended native UI framework for new Windows desktop apps" (`windows.md` §1) | WPF on .NET 10/11 (`wpf`); WinForms on .NET 10/11 (`winforms`); **C++/WinRT WinUI** (`cpp-winrt`, the user's answer O2) | .NET MAUI 11, Avalonia 12, Uno 7, Electron, Tauri, Qt (D5) |

Cross-platform verdicts (D5): Electron and Tauri lead the desktop market but are web apps in a shell. They belong in a later `fe-react` desktop-shell lane, not in this plan (Q1). Flutter desktop belongs with the Flutter plugin plan 002 queued. Compose Multiplatform Desktop is a mention in `mobile-android`'s KMP skill. MAUI, Avalonia and Uno are detected by `desktop-windows` and named, not taught. Qt is deferred because the library has no C++/QML lane. React Native for Windows/macOS is mention-only.

## 4. Version lanes (verified 2026-11-15)

Every skill is version-aware (CLAUDE.md § Version policy): detect first, key every recipe to what is detected, never up-level, never flag a down-level project for lacking an up-level API.

### 4.1 macOS

| Item | Primary | Supported | Floor / rule |
|---|---|---|---|
| Xcode / Swift / SDK | **Xcode 27.x, Swift 6.4, macOS 27 SDK** (macOS 27 "Golden Gate", 2026-09-14; Xcode 27.2 current) | Xcode 26.x, Swift 6.2–6.3, macOS 26 SDK | Xcode 27 installs only on Apple-silicon Macs on Tahoe 26.6+ |
| Deployment target, new app | **macOS 15** (UtilityWindow, `defaultWindowPlacement`, `windowLevel`, `restorationBehavior`, `WindowDragGesture`) | **macOS 14** (`@Observable`, SwiftData, `inspector`, `onKeyPress`, `openSettings`), aligned with `mobile-ios`'s iOS 17 for multiplatform code | — |
| Deployment target, existing app | keep it | macOS 13 (`NavigationSplitView`, `Window`, `MenuBarExtra`, `SMAppService`) | **macOS 12 is Xcode 27's hard floor**; below 13 is the AppKit lane only, flagged. Never raise it as a side effect (D4) |
| Architectures | arm64 only when the deployment target is ≥ 27 (`ARCHS_STANDARD` drops x86_64) | Universal while the target is < 27 and Intel Macs on Tahoe are in scope | macOS 26 Tahoe is the last macOS for Intel; Intel software stops running on macOS 28. A 27 target that must ship x86_64 adds it to `ARCHS` by hand, and nothing warns. `.pkg` files with no `hostArchitecture` now default to arm64 |
| Language mode | Swift 6 + Approachable Concurrency for new modules | Swift 5-mode modules, migrated one at a time | As `mobile-ios` |

Facts the skills carry (`macos.md` §2–§10):
- **SDK-forced changes.** Linking the macOS 27 SDK makes Liquid Glass impossible to opt out of and hides menu icons by default. It deprecates `FileDocument`; new document code uses `Document`.
- **Scenes and commands.** Scenes: `WindowGroup`, `Window`, `Settings` (⌘,), `MenuBarExtra`, `DocumentGroup`, `UtilityWindow`. Use `openWindow`; `pushWindow` does not exist on macOS. Commands read focused state through `@FocusedValue` / `focusedSceneValue`.
- **Mac App Store.** There is no published macOS SDK upload deadline. Uploads must strip `com.apple.quarantine`. Guideline 2.4.5 applies: sandboxed, no self-updater, no licence keys, no downloaded code.
- **Developer ID.** Builds need Hardened Runtime, a secure timestamp, `notarytool` and stapling (`altool` is rejected). **The original Developer ID CA expires 2027-02-01**; `.pkg` files signed under it stop installing and must be re-signed with a G2 certificate.
- **Library pins.** Sparkle **2.10.1** (EdDSA-signed feed), OpenTelemetry Swift **2.6.0** and Sentry **9.34** all need macOS 12+.
- **Touch.** Touch-screen Macs have shipped since 2026-11-06, so hover-only controls need a click or context-menu path.
- **Privacy manifest.** It declares collected data. Required-reason API declarations are not required on macOS.
- **Apple's agent tooling** in Xcode 27: agent skills and `xcrun mcp-server`; the Foundation Models framework is available on macOS (`macos.md` §9).

### 4.2 Windows

| Item | Primary | Supported | Floor / rule |
|---|---|---|---|
| .NET | **10 LTS** (10.0.15) | **11 STS** (GA 2026-11-10) | **.NET 8 and 9 have been out of support since 2026-11-10.** Flag them, never target them; this deviates from CLAUDE.md § Version policy (Q2, D2) |
| Windows App SDK | **2.6.x** (2.6.5, 2026-11-02; SemVer since 2.0.1, 2026-04-29; 2.0 line serviced to 2027-04-29) | — | 1.x is out of support: a migration finding. Experimental-channel APIs (`TableView`, `Chart`, Ink) never go into production builds |
| TFM / OS | `net10.0-windows10.0.26100.0` | `net11.0-windows10.0.26100.0`; the 28000-series SDK | API floor Windows 10 1809 (17763). Windows 10 consumer ESU runs to 2027-10-12 |
| UI lanes | WinUI (the "3" was dropped at Build 2026) | WPF (Fluent theme still "in progress"; .NET 11 bug fixes only), WinForms (dark mode and `ShowAsync` stable since .NET 10; `VisualStylesMode.Net11` opt-in), C++/WinRT (`Microsoft.Windows.CppWinRT` 3.0.260818.1) | Never add WinUI to a WPF or WinForms app as a side effect |
| Packaging | **Packaged MSIX, framework-dependent** (template default) | Packaged with external location; unpackaged (`WindowsPackageType=None`); self-contained | ClickOnce is not supported for WinUI. Unpackaged needs a recorded reason |
| Libraries | CommunityToolkit.Mvvm **8.4.2**; Windows Community Toolkit 8.2 (AOT-ready); CsWinRT **2.3.1** | CsWinRT 3.0 preview: do not adopt | Native AOT is supported (`PublishAot`) and needs `x:Bind` only |
| Tooling | Visual Studio 2026 ("WinUI application development" workload); **`winapp` CLI 0.8.0** (public preview): `winapp new --template winui|winui-mvvm|winui-unittest…`, `run`, `find-ui`, `find-api`, `ui inspect`, `pack`, `az-sign` | `dotnet` CLI | Developer Mode is required for `winapp run`. `Microsoft.Windows.SDK.BuildTools.WinUIAnalyzer` goes on every app project |
| Architectures | x64, ARM64 (`msixbundle` for multi-arch) | x86 | .NET 11 needs x86-64-v2 / Arm64 LSE (secondary source) |

Facts the skills carry (`windows.md` §3–§11):
- **Threading and binding.** Background work reaches the UI only through `DispatcherQueue.TryEnqueue`, batched. Use `x:Bind` over `{Binding}`.
- **Windows and activation.** `AppWindow` and the `TitleBar` control; single instancing via `AppInstance.FindOrRegisterForKey` / `RedirectActivationToAsync`. File access uses the new `Microsoft.Windows.Storage.Pickers` pickers, constructed with `AppWindow.Id`.
- **Notifications.** `AppNotificationManager`. Elevated apps cannot send notifications, so never require admin.
- **Secrets.** `PasswordVault` / DPAPI.
- **Look.** Mica, one backdrop per window. Every screen is tested in High Contrast.
- **Lists.** Virtualize lists over about 20 items (`ListView`, `GridView`, `ItemsRepeater`).
- **WebView2.** Lock it down: navigation allowlist, devtools off in release.
- **Signing.** Publish through the Store, or sign with **Azure Artifact Signing** ($9.99/month). EV certificates no longer bypass SmartScreen, and Smart App Control blocks unsigned executables. Unpackaged apps update through Velopack 1.2.161.
- **Windows AI APIs.** Use readiness checks and the Limited Access Feature gate. Phi Silica is being replaced by "Aion Instruct" (retail January 2027).
- **Microsoft's own Claude Code plugin** is `winui@win-dev-skills` v0.7.1, with a `winui-dev` agent and 8 skills (D10).

### 4.3 Shared rules and dates

| Rule set | Current fact | Source |
|---|---|---|
| Mac App Store | Guideline 2.4.5 (above); quarantine stripping since 2025-02-18; `notarytool` only since 2023-11-01 | `macos.md` §1.4, §4 |
| Developer ID | Original CA expires 2027-02-01: re-sign `.pkg` with G2 | `macos.md` §4.2 |
| Windows trust | Store or Azure Artifact Signing; SmartScreen reputation; Smart App Control blocks unsigned | `windows.md` §6 |
| Accessibility | WCAG 2.2 AA as the target (EN 301 549, European Accessibility Act since 2025-06-28; see 002 §4.4). macOS: VoiceOver, Full Keyboard Access, controls ≥ 20×20 pt (28 pt default), text ≥ 10 pt (13 pt default). Windows: UI Automation, Narrator, access keys, High Contrast, text scaling | `macos.md` §5; `windows.md` §7 |
| Telemetry | OTel Swift 2.6.0; OpenTelemetry .NET in a desktop app; Sentry .NET 7.0.0 | `macos.md` §7; `windows.md` §9 |

### 4.4 Desktop E2E (QA-owned)

| Item | Fact | Source |
|---|---|---|
| Appium | Library pin **3.8.0** (`tools/qa-version-check.py:24`); latest 3.9.1; **Appium 4 is in beta** (beta.8, 2026-11-13) | `cross-platform-and-qa.md` §0, B.1 |
| macOS driver | **Mac2 4.6.1** on Appium 3, installed with an explicit `@version` (Mac2 5.x needs Appium 4). `accessibility id` reads the XCTest `identifier` = `accessibilityIdentifier`. One session at a time; needs Xcode and some macOS permission setup | B.1, B.2, B.3 |
| Windows driver | **WinCore 3.3.2** on Appium 3 (WinCore 4.x needs Appium 4); the legacy Appium Windows driver is deprecated and archived, and WinAppDriver's last release was 2021. Fallback: **NovaWindows 1.5.0**. All locate by `AutomationId`, unique among siblings only | B.1, B.2 |
| Clients | Java `java-client` 11 (`Mac2Driver`; `WindowsOptions` hard-sets `automationName=Windows`, so override it to `Wincore`); .NET `Appium.WebDriver` 9, or **FlaUI 5.0.0** (UIA3, in process) for Windows-only suites; TypeScript WebdriverIO 10 | B.5 |
| Web content | WebView2 via Playwright `connectOverCDP`; Electron via Playwright `_electron` (experimental, Node only), out of scope here (Q1) | B.5 |
| CI | Windows desktop UI tests need an interactive autologon session; Microsoft-hosted Azure Pipelines agents do not support them, so use self-hosted. No device cloud runs native desktop apps (BrowserStack no; Sauce Electron-only beta): own hardware | B.3, B.4 |

### 4.5 Library pins this plan does not move

The QA lane uses the library's Appium 3.8.0 / WebdriverIO 10.0.2 / `java-client` 11 / `Appium.WebDriver` 9.0.0 pins, which `tools/qa-version-check.py` enforces. E1 confirms that Mac2 4.6.1 and WinCore 3.3.2 declare an Appium peer range that includes 3.8.0. If either does not, E1 records a dated `D<n>` and stops short of bumping the library pin (Q3).

### 4.6 Not verified: each owning task re-checks before writing it as fact

- macOS (`macos.md` "Not verified"): AppKit's own design-compatibility key; parallel XCUITest on Mac; the possible 27.3 `dropDestination` deprecation; Dynamic Type on macOS; Control widget availability on Mac.
- Windows (`windows.md` "Not verified"): Windows App SDK 2.6 and .NET 11 TFMs; the template's `TargetPlatformMinVersion`; whether `winui-mvvm` wires `Microsoft.Extensions.Hosting`; the Fluent type ramp, icons and corner tokens; startup/background-task and share-target APIs in 2.x; Windows Hello / passkey APIs; `PasswordVault` for unpackaged apps; Artifact Signing eligibility outside US/Canada.
- QA (`cross-platform-and-qa.md` "Not verified"): GitHub-hosted runners for desktop UI tests; WinCore maturity on real WinUI/WPF apps; the Appium 4 GA date.
- Not researched at all: the OWASP Desktop App Security Top 10 (S2 researches it); the C++/WinRT unit-test framework and coverage tooling (W4 researches them); Auth0's current WinUI/WPF SDK (S3 researches it).

## 5. Desktop code rules (the coding standard)

C1 copies this section into `CLAUDE.md` as `## Desktop code rules`, after § Mobile code rules. Every desktop skill applies it; every audit checks it.

Both platforms:

- **Platform conventions first.** The app looks and behaves like its OS: native menus, title bar, controls, system fonts and the OS's standard shortcuts. It is never a web page in a window and never imitates the other OS. Design facts come from `design/ui-ux-pro-max` (`--stack swiftui | winui | wpf`).
- **Keyboard-first.** Every command is reachable from the keyboard, focus order is complete and visible, and standard shortcuts are kept. On macOS every command lives in the menu bar in the standard order, with unavailable items disabled, never hidden. On Windows commands carry access keys and accelerators.
- **Windows are resizable, restore their size and position, and survive monitor and DPI changes.** Several windows on the same data share one source of truth, never a copy per window.
- **The UI thread never blocks**: no disk, network, database or heavy compute on the main actor or the dispatcher thread. Results return to it through the platform's mechanism (`@MainActor`, `DispatcherQueue.TryEnqueue`).
- **Lifecycle is part of the requirement.** Work a window starts is cancelled when it closes. Wake from sleep, a network change and window reactivation trigger a revalidate. Quitting with unsaved work asks first, and relaunch restores state.
- **Every data region has loading / loaded / failed states, plus stale and offline.** A failure is scoped to the response-dependent subtree. It raises one persistent banner inside the window content (an inline banner on macOS, an `InfoBar` on WinUI) that only the user dismisses. A background failure never raises a modal alert.
- **Least privilege.** Ship sandboxed: App Sandbox on macOS, packaged MSIX with minimal capabilities on Windows. Never require admin or root. Every entitlement and capability carries a recorded reason.
- **Secrets never ship in the binary, `Info.plist`, `appsettings.json` or plain files.** Tokens live only in the Keychain, `PasswordVault` or DPAPI. Nothing sensitive goes in logs, `UserDefaults` or settings storage.
- **Permissions** (macOS TCC, Windows privacy consent) are asked at the moment of use. The denied path is a working screen that links to the system settings page.
- **Only signed, verified updates.** On macOS: Developer ID + notarization + a Sparkle EdDSA feed, or the Mac App Store. On Windows: the Store, or MSIX / Artifact-Signed binaries with a signed feed. An update never restarts the app over unsaved work.
- **Embedded web content is locked down** (`WKWebView`, WebView2): a navigation allowlist, no devtools in release, and every bridge message validated as untrusted input. So are URL schemes, file activation and IPC messages.
- **Accessible by default.** Every interactive element is labelled (`accessibilityLabel`, `AutomationProperties.Name`). Increase Contrast / High Contrast, Reduce Motion / animation effects and Reduce Transparency are honoured. Text scales wherever the platform offers it, and no state is shown by colour alone.
- **Every interactive element and list container carries the platform's test id**: `accessibilityIdentifier` (macOS) or `AutomationProperties.AutomationId` (Windows). Ids are PascalCase dot-separated and static, **never the accessibility label**.
- Constructor / initializer injection only; no service locator; no static mutable state; async all the way, never blocking on a result.
- **Dev-side tests** cover the logic the agent writes: Swift Testing; NUnit for view models and services, and the MSTest WinUI Unit Test App only for code that needs XAML types (D8); the C++ lane's framework (W4). The floor is ≥ 80% of branches in Test code rules, or lines on Swift. Desktop E2E belongs to the `qa-desktop-<lang>` peer.
- Never up-level a toolchain, SDK, TFM, deployment target or Windows App SDK major as a side effect of other work.

Per platform:

- **macOS (Swift):**
  - Swift 6 mode and the concurrency rules of § Mobile code rules (iOS).
  - SwiftUI first; AppKit where the codebase is AppKit.
  - Settings live in a `Settings` scene. Commands read focused state through `@FocusedValue`. Open windows with `openWindow`.
  - File access goes only through open/save panels and security-scoped bookmarks, with start/stop balanced. Full Disk Access is never assumed.
  - Login items and helpers use `SMAppService`; IPC uses XPC.
  - Developer ID builds use Hardened Runtime and are notarized and stapled. Mac App Store builds have no self-updater and no licence keys.
  - A universal binary is a decision tied to the deployment target.
  - Use `os.Logger` only.
- **Windows (C#):**
  - New apps use WinUI on Windows App SDK 2.x; WPF and WinForms codebases stay what they are.
  - MVVM with CommunityToolkit.Mvvm source generators. DI through `Microsoft.Extensions.Hosting` or constructor wiring, never a locator.
  - Use `x:Bind` over `{Binding}`.
  - Packaged MSIX by default.
  - Single instancing through `AppInstance`, never a hand-rolled mutex. Use the Windows App SDK pickers.
  - Experimental-channel APIs never ship.
  - Lists are virtualized.
  - Structured logging through `ILogger`.
- **Windows (C++/WinRT):**
  - Use `winrt::com_ptr` and value types; no raw `new`/`delete`.
  - A coroutine that touches `this` after a suspension holds `get_strong()` or `get_weak()`.
  - Return to the UI thread through `wil::resume_foreground` / the dispatcher queue.
  - `winrt::hresult_error` is handled at the boundaries.
  - Warnings are errors.

  W4 verifies each C++ rule against current Microsoft docs and rewrites this bullet in `CLAUDE.md` if a fact differs.

## 6. The skill set

### 6.1 The spine, adapted (D6)

| Mobile spine folder | `desktop-macos` | `desktop-windows` | Audit § |
|---|---|---|---|
| `basics` | `basics`: Swift standard + the Mac mental model (adapted from `mobile-ios`, D3) | `basics`: C# + XAML standard, the Windows mental model, the lane map (WinUI / WPF / WinForms / C++ and the not-taught stacks) | A, B |
| `project-setup` | same name | same name | A, B |
| `architecture` | same | same | C |
| `ui-components` | same | same | D |
| `styling` (+ `animation` folded in) | same | same | E |
| `navigation` | `windows-and-scenes` | `windows-and-navigation` | F |
| — | `menus-and-commands` | (commands live in `windows-and-navigation`) | F |
| `forms` | same | same | G |
| `networking` | same | same | H |
| `offline-and-storage` | same | same | I |
| — | `documents` | (file activation in `activation-and-notifications`) | I |
| `device-features` | `sandbox-and-permissions` | `platform-integration` | J |
| `notifications-and-links` + `system-integration` | `system-integration`, `background-and-helpers` | `activation-and-notifications` | J |
| brownfield UI lane (`uikit`, `views-interop`) | `appkit` | `wpf`, `winforms` | D |
| — | — | `interop`, `cpp-winrt` | X |
| `languages` | same | same | P |
| `accessibility` | same | same | M |
| `performance` | same | same | N |
| `error-handling` | same | same | O |
| `test-ids` | same | same | R |
| `unit-testing` | same | same | S |
| `migration` | same | same | A |
| `code-review`, `standards-audit`, `rules` | same | same | — |

### 6.2 `desktop/macos/skills` (25)

| Folder | Content (facts in §4.1, `macos.md`) |
|---|---|
| `basics` | The Swift coding standard adapted from `mobile-ios` (`mobile/ios/skills/basics`), plus the Mac model: scenes and windows over screens, menu-bar-first commands, keyboard-first, pointer + touch, density, the sandbox |
| `project-setup` | Xcode 27 macOS app, Swift 6 set explicitly, sandbox + hardened runtime on from day one, entitlements file, xcconfig per environment, `xcrun swift-format` + SwiftLint, test plans, privacy manifest, deployment-target and architecture choice per §4.1 |
| `architecture` | MV with `@Observable` models injected through initializers / `@Environment`; per-window vs app-wide state; `@FocusedValue` plumbing; TCA only as an existing-codebase lane |
| `ui-components` | SwiftUI on Mac: `Table`, `List` with selection, `Inspector`, `NavigationSplitView` sidebars, context menus, hover and touch, `.task` loads, previews |
| `styling` | Liquid Glass (forced by the 27 SDK), semantic colours, control sizes and density, materials, Reduce Transparency / Increase Contrast; motion and Reduce Motion (the folded `animation`) |
| `windows-and-scenes` | `WindowGroup`, `Window`, `UtilityWindow`, `MenuBarExtra`, `Settings`; `openWindow`, placement, resizability, restoration, multi-window state, toolbars, full screen |
| `menus-and-commands` | `commands`, `CommandMenu`, `CommandGroup` replacing standard groups, keyboard shortcuts, the standard menu order, disabled-not-hidden, focused-value commands, the 27 SDK hidden menu icons |
| `forms` | `Form` in Settings and inspectors, `@FocusState`, validation, autofill and passkeys, the key-view loop |
| `networking` | As `mobile-ios` (`URLSession` async, timeouts, cancellation, ProblemDetails, refresh actor) plus the sandbox `network.client` entitlement and App Transport Security on Mac |
| `offline-and-storage` | SwiftData / Core Data / GRDB lanes, Keychain (data protection keychain on Mac), container paths in the sandbox, `UserDefaults` suites, migrations |
| `documents` | `DocumentGroup` and the 27 SDK `Document` (vs deprecated `FileDocument`), file packages, autosave and versions, iCloud documents |
| `appkit` | The brownfield lane: `NSViewController`, `NSHostingView` / `NSHostingController`, `NSViewRepresentable`, AppKit + Observation, gesture recognizers over `mouseDown:` |
| `sandbox-and-permissions` | Entitlements, TCC (camera, microphone, screen recording, accessibility, files and folders, Full Disk Access never assumed) with a working denied path, security-scoped bookmarks |
| `background-and-helpers` | `SMAppService` login items and agents, XPC services (`XPCSession`), helper tools, background activity scheduling |
| `system-integration` | App Intents / Shortcuts / Spotlight, widgets on Mac, notifications, URL schemes and universal links routed to windows, Services, pasteboard, drag and drop |
| `languages` | String Catalogs, plurals, `FormatStyle`, RTL in Mac layouts |
| `accessibility` | VoiceOver on Mac, Full Keyboard Access, rotors, element grouping, minimum control and text sizes (§4.3) |
| `performance` | Instruments, hangs, launch time, memory, `Table` with large data, energy; MetricKit availability on Mac checked |
| `error-handling` | The house rule set with the desktop deltas (§6.4) |
| `test-ids` | `accessibilityIdentifier` on every interactive element and container; Mac2 reads it as `accessibility id`; the `missing-testids.md` hand-off |
| `unit-testing` | Swift Testing by default, XCTest where XCUITest or performance needs it; fakes over mocks; clock and UUID seams |
| `migration` | AppKit → SwiftUI screen by screen, Catalyst → native, Swift 5 → 6, Intel → Apple silicon only (and the 2027-02-01 Developer ID CA), `FileDocument` → `Document`, Objective-C islands; Electron → native as a mention |
| `code-review` | Hostile review of a diff against every rule, plus a screenshot pass (`screencapture -l <windowid>`, then `Read`) |
| `standards-audit` | The conformance audit on `ep-standards-audit-engine` (§8) |
| `rules` | The installer and the path-scoped rule files (§8.6) |

### 6.3 `desktop/windows/skills` (25)

| Folder | Content (facts in §4.2, `windows.md`) |
|---|---|
| `basics` | The C# and XAML standard, the Windows model (packaged identity, activation, the UI thread, DPI), the lane table and how to detect each lane (`UseWinUI`, `UseWPF`, `UseWindowsForms`, `.vcxproj` + CppWinRT, MAUI / Avalonia / Uno markers) |
| `project-setup` | `winapp new` or VS 2026 templates, TFM per §4.2, packaged MSIX, `Directory.Build.props`, nullable + warnings as errors, the WinUI analyzer, `TargetPlatformMinVersion`, ARM64 |
| `architecture` | MVVM with CommunityToolkit.Mvvm (`[ObservableProperty]`, `[RelayCommand]`), DI via `Microsoft.Extensions.Hosting`, services, messenger only when earned |
| `ui-components` | XAML pages and user controls, `x:Bind`, `DataTemplate`s, virtualized `ListView` / `ItemsRepeater`, `InfoBar` for the failed state, `ContentDialog` rules, the experimental-control fence |
| `styling` | Fluent 2: theme resources, light/dark/High Contrast, Mica / Acrylic, type ramp, Segoe Fluent Icons, corner radius, DPI; motion and animation-effects setting (the folded `animation`) |
| `windows-and-navigation` | `AppWindow`, `TitleBar` control, multi-window, `NavigationView` + `Frame`, `TabView`, back, commands, access keys, accelerators |
| `activation-and-notifications` | `AppInstance` single-instance and redirection, protocol and file activation, startup tasks, restart, `AppNotificationManager`, push (WNS) |
| `platform-integration` | Windows App SDK pickers, share, clipboard, drag and drop, background tasks, widgets, WebView2 lockdown, Windows AI APIs (`references/windows-ai.md`) |
| `forms` | Input controls, validation (`ObservableValidator`), `NumberBox` / `CalendarDatePicker`, focus and tab order, server errors to fields |
| `networking` | `IHttpClientFactory` typed clients, timeouts, cancellation, `Retry-After`, ProblemDetails, token refresh, `ClientWebSocket` |
| `offline-and-storage` | `ApplicationData` (packaged) vs file paths (unpackaged), SQLite / EF Core local, `PasswordVault` / DPAPI, settings, migrations |
| `interop` | CsWinRT 2.3.1, HWND / COM / P/Invoke (`LibraryImport`), XAML Islands, hosting WinUI in WPF/WinForms, `winapp find-api` |
| `wpf` | The WPF lane on .NET 10/11: MVVM, the Fluent theme opt-in, `ThemeMode`, dark mode, modernizing in place, never WinUI as a side effect |
| `winforms` | The WinForms lane: dark mode `SetColorMode`, `ShowAsync` / `ShowDialogAsync`, high DPI, MVVM-ish binding, `VisualStylesMode.Net11` opt-in |
| `cpp-winrt` | The C++/WinRT lane: project shape (`.vcxproj`, MIDL / IDL, `Microsoft.Windows.CppWinRT`), ownership, coroutines and strong/weak `this`, dispatcher resume, errors, WIL, testing and coverage (W4 researches), `winapp run/pack` |
| `languages` | `.resw` resources, `x:Uid`, plurals, RTL (`FlowDirection`), culture-aware formatting |
| `accessibility` | UI Automation peers, `AutomationProperties.Name` / `HelpText` / `LiveSetting`, Narrator, keyboard and access keys, High Contrast, text scaling, Accessibility Insights for Windows |
| `performance` | Startup, `x:Bind` vs `{Binding}`, virtualization, event-handler leaks, Native AOT and trimming, PerfView / WPR / ETW |
| `error-handling` | The house rule set with the desktop deltas (§6.4), unhandled-exception handlers, stowed exceptions (`winapp run --debug-output`) |
| `test-ids` | `AutomationProperties.AutomationId` on every interactive element and container (unique among siblings, so containers carry their own); WinCore / NovaWindows / FlaUI read it; the `missing-testids.md` hand-off |
| `unit-testing` | NUnit for view models and services (house default); MSTest WinUI Unit Test App with `[UITestMethod]` only for code that needs XAML types (D8); fakes over mocks; `TimeProvider` seams |
| `migration` | UWP → WinUI, WPF → WinUI (or modernize WPF in place), WinForms modernization, .NET Framework → .NET 10, .NET 8/9 → 10, Windows App SDK 1.x → 2.x, Xamarin/MAUI mention; GitHub Copilot app modernization noted |
| `code-review` | Hostile review against every rule, plus a screenshot pass (`winapp ui screenshot`, or PowerShell capture, then `Read`) |
| `standards-audit` | The conformance audit on `ep-standards-audit-engine` (§8) |
| `rules` | The installer and the path-scoped rule files (§8.6) |

### 6.4 Error resilience: the desktop deltas

`error-handling` on both platforms is written against the full fe-react rule set (`frontend/react/skills/error-handling/{SKILL.md,references/*}`) and the mobile deltas (002 §6.5), with these desktop deltas:

| Rule | Desktop delta |
|---|---|
| Failure scoped to the subtree | A window with a sidebar, toolbar and inspector keeps all three when the content pane fails |
| Persistent, user-dismissed notification | An inline banner (macOS) or an `InfoBar` (WinUI) at the top of the window's content, never a modal alert and never a system notification for a foreground failure |
| Stale-tab restore | Becomes window reactivation and **wake from sleep** + network change → revalidate |
| Multi-tab consistency | Becomes **multi-window**: one model, every window observes it; a write in one window never leaves another showing old data |
| Version skew | An auto-update (Sparkle, Velopack, Store) never restarts over unsaved work; a forced minimum version is a server-driven prompt |
| Mutation failures | Quitting mid-write is routine: autosave, and on relaunch the indeterminate outcome is reconciled, never silently dropped |
| Storage failures degrade | A full disk or a revoked security-scoped bookmark / file permission is a recoverable, explained state |
| Third-party dependency failure | WebView2 runtime missing, a helper/XPC service dead, a COM server unregistered: each degrades to a scoped failed region |

Every `error-handling` SKILL.md fits 16,000 characters: rule bodies go in `references/` from the start.

### 6.5 Shared and auth skills

| Skill | Owns | References |
|---|---|---|
| `desktop/_shared/distribution` | Versioning; macOS: Developer ID vs Mac App Store, signing, Hardened Runtime, `notarytool` + stapling, DMG / pkg, Sparkle 2 (EdDSA feed), Mac App Store 2.4.5 rules, the 2027-02-01 CA; Windows: MSIX, Store, winget, `.appinstaller`, Velopack for unpackaged, Azure Artifact Signing, SmartScreen / Smart App Control, `msixbundle`; pinned CI runners and the secrets that never live in the repo. Pipeline YAML stays `devops-engineer`'s | `macos.md`, `windows.md`, `audit-checks.md` (letter L) |
| `desktop/_shared/security` | Desktop secure coding: least privilege, sandbox and capabilities, secrets storage, update-channel integrity, IPC / XPC / named-pipe hardening, URL scheme and file activation as untrusted input, WebView lockdown, DLL search-order and dylib hijacking, code-signing checks at runtime; mapped to the OWASP Desktop App Security Top 10 (S2 researches the current edition). What a static read cannot prove says **requires dynamic test → `qa-security`** | `macos.md`, `windows.md`, `audit-checks.md` (K) |
| `desktop/_shared/observability` | One crash reporter (Sentry), OTel per platform (§4.3), app → ingest gateway → OTel Collector / Alloy → Tempo / Loki / Prometheus, batching, sampling, PII scrubbing, `os.Logger` / `ILogger` structure. The Collector and backends are the be-* `observability-engineer-<stack>` agents' | `macos.md`, `windows.md`, `audit-checks.md` (U) |
| `auth/auth0-macos` | Auth0.swift on macOS, Universal Login via `ASWebAuthenticationSession`, `CredentialsManager` + Keychain, Sign in with Apple through Auth0 | — |
| `auth/auth0-windows` | RFC 8252 native-app flow: system browser + PKCE with loopback or protocol-activation redirect; Auth0's current .NET desktop SDK (S3 researches which one covers WinUI/WPF); tokens in `PasswordVault` / DPAPI | — |

### 6.6 QA desktop lane (D9)

| Path | Owns |
|---|---|
| `qa/_shared/desktop-testing` | The shared rules: Appium 3 + pinned drivers (§4.4), the test-id contract (§8.5), window objects expose intent, multi-window switching, CI facts (interactive session on Windows, macOS accessibility permission, one Mac2 session at a time), no device cloud: self-host, the Appium 4 "from 4.0 GA" tag |
| `qa/<lang>/skills/desktop-project-setup` | Appium server + `appium driver install mac2@4.6.1` / `wincore@3.3.2`, OS prerequisites, the client setup for the lane, a first smoke run |
| `qa/<lang>/skills/desktop-screen-explorer` | Page-source inventory (`appium-mcp` general mode against a running server), the same `missing-testids.md` hand-off keyed on `identifier` / `AutomationId`, routed to `desktop-macos` / `desktop-windows` |
| `qa/<lang>/skills/desktop-window-objects` | Window objects that expose user intent, multi-window and dialog handling, waits on conditions |
| `qa/<lang>/skills/rules/desktop-tests.md` | Path-scoped rules for desktop test code, beside `mobile-tests.md` |
| `qa/<lang>/agents/qa-desktop-<lang>.md` + `qa/<lang>/commands/desktop.md` | The step-by-step desktop E2E agent and its command, in the `qa-mobile-<lang>` shape |

Lane specifics: **Java**: TestNG + `java-client` 11, `Mac2Driver`, WinCore through `BaseOptions` / an overridden `automationName`. **.NET**: NUnit + `Appium.WebDriver` 9, or FlaUI 5.0.0 for Windows-only suites, and Playwright .NET `ConnectOverCDPAsync` for WebView2 content. **TypeScript**: WebdriverIO 10 + Appium; Electron and Tauri are out of scope (Q1).

## 7. The agents

Each agent follows `.skill-template/agent.md`: invariants, every-run steps (rules, orientation cache, green on arrival, representative files), the steps table, Fix / Extend, boundaries, report. `mobile/ios/agents/mobile-ios.md` (9,031 characters) is the shape. Each agent fits **14,000 characters** with a description ≤ 650, and carries the template's `Gate:` sentence verbatim.

### 7.1 Steps (greenfield; brownfield re-enters single rows)

| # | Step | Skills | Exit gate (outside a `Gate: none` plan task) |
|---|---|---|---|
| 0 | Project setup *(skip if one exists)* | `project-setup` | Builds; launches; one window renders |
| 1 | Foundations | `basics`, `architecture`, `styling`, `windows-and-scenes` / `windows-and-navigation`, `menus-and-commands` (macOS), `design/ux-patterns`, `design/ui-ux-pro-max` (`--design-system`, then `--stack swiftui\|winui\|wpf`), `design/visual-identity`; `auth/auth0-<os>` when there is sign-in | Decision record (the experience block, or the plan's `experience-plan.md` validated); state + DI plan; theme; window and command map; walking skeleton renders the shell |
| 2 | Feature build | `ui-components`, `forms`, `networking`, `offline-and-storage`, `documents`, `sandbox-and-permissions` / `platform-integration`, `system-integration` / `activation-and-notifications`, `background-and-helpers`, `test-ids`, `languages`; lanes `appkit` / `wpf` / `winforms` / `cpp-winrt` / `interop` when detected | Build + static checks clean; every region three-state; every interactive element tagged; permissions with a working denied path; activation inputs validated |
| 3 | Quality layers | `accessibility`, `performance`, `error-handling`, `desktop/_shared/security`, `desktop/_shared/observability` | §6.4 gate; keyboard-only pass; accessibility rules in code; security rules; crash reporting wired |
| 4 | Dev-side tests | `unit-testing` | Tests green; ≥ 80% of the branches written |
| 5 | Review | `code-review`, `design/ux-review`, `design/visual-identity` | No blocker / major rows after fixes; visual self-critique on captured window screenshots |
| 6 | Release readiness *(when shipping is in scope)* | `desktop/_shared/distribution` | Signing / notarization / packaging configured; distribution rows clean; no secret in the repo |

**Single-skill triggers:** a `missing-testids.md` from QA → `test-ids` alone; "audit against the conventions" → `standards-audit` alone (`/desktop-<os>:audit`); a version jump → `migration` alone, one major per change.

### 7.2 The commands each agent runs

| | macOS | Windows (C#) | Windows (C++/WinRT) |
|---|---|---|---|
| Build / run | `xcodebuild -scheme <Scheme> -destination 'platform=macOS' build`, then `open` the product | `winapp run` (or `dotnet build` + VS deploy for packaged) | `winapp run` on the `.vcxproj` / `msbuild` |
| Static | `xcrun swift-format lint --recursive <dirs>`, `swiftlint` | `dotnet build -warnaserror` with the WinUI analyzer, `dotnet format --verify-no-changes` | `/W4 /WX` build; clang-tidy where configured |
| Tests | `xcodebuild … test`; `swift test` in local packages | `dotnet test` (NUnit project; the WinUI Unit Test App where present) | W4 decides (D8) |
| Screenshot for Step 5 | `screencapture -l <windowid> <file>` | `winapp ui screenshot`, or a PowerShell capture | same |

### 7.3 Brownfield: orientation cache fields

| Section | `desktop-macos` | `desktop-windows` |
|---|---|---|
| Version lane | Xcode / Swift; deployment target; architectures; language mode per module; SwiftUI vs AppKit share; Catalyst?; package manager | TFM; Windows App SDK; UI lane(s); packaged or not; CsWinRT; C++ projects; MAUI / Avalonia / Uno markers |
| Build, run & test | schemes, test plans | solution, projects, `winapp` present?, test projects and runners |
| Distribution | Developer ID / Mac App Store / both; Sparkle feed | Store / MSIX sideload / unpackaged + Velopack; signing |
| Seams to reuse | models / services and their injection, scenes and commands, persistence, `accessibilityIdentifier` naming | view models, DI host, navigation, `AutomationId` naming |
| Known unknowns | Objective-C islands, helpers nobody owns, entitlements without a reason | P/Invoke nobody owns, COM registrations, unpackaged `ApplicationData` assumptions |

A legacy codebase is never modernized as a side effect: that is a separate `migration` run, offered, never assumed.

## 8. Audits

### 8.1 Sections (identical letters on both platforms)

Letters keep the mobile checklists' meaning, so the audits compare across domains. **Q** (motion) and **T** (release) are unused: motion is in E, release in L.

| § | Section | Owner (macOS) | Owner (Windows) |
|---|---|---|---|
| A | Version lane, toolchain & migration hygiene | `project-setup`, `migration`, `basics` | same |
| B | Project structure, strictness & language standard | `project-setup`, `basics` | same |
| C | Architecture, state & DI | `architecture` | same |
| D | UI components & platform conventions | `ui-components`, `appkit` | `ui-components`, `wpf`, `winforms` |
| E | Styling, theming, motion & adaptive layout | `styling` | same |
| F | Windows, navigation & commands | `windows-and-scenes`, `menus-and-commands` | `windows-and-navigation` |
| G | Forms & input | `forms` | same |
| H | Networking & realtime | `networking` | same |
| I | Storage, documents & sync | `offline-and-storage`, `documents` | `offline-and-storage` |
| J | Platform integration, permissions & background | `sandbox-and-permissions`, `background-and-helpers`, `system-integration` | `platform-integration`, `activation-and-notifications` |
| K | Security | `desktop/_shared/security` (fragment) | same |
| L | Distribution & store compliance | `desktop/_shared/distribution` (fragment) | same |
| M | Accessibility | `accessibility` | same |
| N | Performance | `performance` | same |
| O | Error resilience | `error-handling` | same |
| P | Localization | `languages` | same |
| R | Testability & test ids | `test-ids` | same |
| S | Dev-side tests | `unit-testing` | same |
| U | Observability & logging | `desktop/_shared/observability` (fragment) | same |
| V | Comments & KISS | `ep-code-comments`, CLAUDE.md § Simplicity | same |
| X | Interop & native code | — (N/A) | `interop`, `cpp-winrt` (N/A without P/Invoke, COM or C++ projects) |

### 8.2 How the checklists get built

C1 writes two skeletons at `desktop/<os>/skills/standards-audit/references/conformance-checklist.md`. Each carries the mobile-ios checklist's header text adapted (permanent ids, how to read a row, the recipe shape, the lane tags) and every section heading with its owners. Only section V gets rows. **Every skill task appends its own rows** the moment it writes the skill, with columns `| # | Check | Violation looks like | Find it with | Sev |`. Numbering continues from the last row, and lane tags go in brackets (`[mac15+]`, `[mac27SDK]`, `[AppKit]`, `[MAS]`, `[DevID]`, `[WinUI]`, `[WPF]`, `[WinForms]`, `[C++]`, `[packaged]`, `[unpackaged]`). Recipes use `rg` with the platform's globs (`*.swift,*.plist,*.entitlements,*.xcconfig` · `*.cs,*.xaml,*.csproj,*.appxmanifest,*.cpp,*.h,*.idl,*.vcxproj`).

**Sections K, L and U hold no rows of their own.** Their heading says the rows are those of `desktop/_shared/<skill>/references/audit-checks.md` whose `Platforms` column names this platform, under the fragment's ids. A row a static read cannot prove says **requires dynamic test → `qa-security`** and is reported as unverified. Each platform's last task writes the audit `SKILL.md` and a closing section index.

### 8.3 Severity anchors

| Severity | Meaning |
|---|---|
| blocker | Ships a crash, a store or notarization rejection, or a hard security break: a secret in the binary, an unsigned update channel, a required admin elevation, an unvalidated activation or bridge input |
| major | A §5 rule broken where it will hurt soon: an unvirtualized long list, no timeout, untagged interactive elements, a command reachable only by mouse, a permission with no denied path, a menu item hidden instead of disabled |
| minor | Style, naming, a single missing label |
| nit | Preference |

### 8.4 Commands

Each plugin ships `commands/desktop-<os>.md` (adopt the agent) and `commands/audit.md` (the conformance audit), in the shape of `mobile/ios/commands/{mobile-ios,audit}.md`.

### 8.5 The test-id contract and the QA hand-off

`qa-desktop-<lang>` locates by `accessibility id`. On macOS (Mac2) that is the XCTest `identifier`, which is the SwiftUI / AppKit `accessibilityIdentifier`. On Windows (WinCore, NovaWindows, FlaUI) it is `AutomationProperties.AutomationId`. An `AutomationId` is unique among siblings only, so every list and container carries its own id, and rows are located inside their container. The accessibility label (`accessibilityLabel`, `AutomationProperties.Name`) is for people, never an id. M4 and W5 verify the mapping against the current driver docs and write it into each `test-ids` skill. E1 writes the same contract into `qa/_shared/desktop-testing` and the explorers' `missing-testids.md` routes to the two dev agents.

### 8.6 The rules skill

Each plugin's `rules` skill copies path-scoped rule files into `.claude/rules/desktop-<os>/`, in the `mobile/ios/skills/rules/SKILL.md` shape (the replace / keep / beside question, the unattended default, paths fitted to the project).

| Platform | Rule files (each with `paths:` frontmatter) |
|---|---|
| macOS | `swift.md`, `swiftui-mac.md`, `appkit.md`, `mac-accessibility.md`, `mac-styling.md`, `mac-localization.md`, `swift-networking.md`, `swift-persistence.md`, `swift-tests.md`, `xcode-config.md` (entitlements, `Info.plist`, privacy manifest, signing settings) |
| Windows | `csharp.md`, `winui-xaml.md`, `wpf.md`, `winforms.md`, `cppwinrt.md`, `win-accessibility.md`, `win-styling.md`, `win-localization.md`, `dotnet-networking.md`, `win-persistence.md`, `win-tests.md`, `package-config.md` (`Package.appxmanifest`, `*.csproj` / `*.vcxproj`, `Directory.Build.props`) |

## 9. Integration (I1) and documentation (G1)

**Marketplace (I1).** Two entries in `.claude-plugin/marketplace.json`, in the `mobile-ios` entry's shape (`source "./"`, `strict false`, the author block, `MIT`, `category "development"`, `dependencies ["dev", "design"]`), placed after `mobile-android`. Build each `skills` array from `ls`, never from memory: own skills, the three `desktop/_shared/*` skills, the auth skill, and `rules`. Commands are the plugin's two; the agent is the plugin's one. The three QA entries gain their three `desktop-*` skills, `qa/_shared/desktop-testing`, the agent and the command. Descriptions are in the `mobile-ios` description's voice. The top-level marketplace description names the `desktop-*` category.

**Surface check (I1).** Add `"desktop"` to `STACK_CATEGORIES` in `tools/plugin-surface-check.py:35`.

**Planning lane (I1, D13).** Add `desktop` ("the native desktop client app") to the stack list at `plan-format.md:119`, `delivery-plan/SKILL.md:44,128,345` and `solution-planner.md`'s stack lists and routing (beside `mobile-*`). Add it to CLAUDE.md § Planning's one-stack bullet ("a web, app or desktop tree").

**QA peers (I1).** `qa/*/skills/device-cloud/SKILL.md` gains one line: native desktop apps run on owned hardware, with no device cloud (§4.4). `qa/_shared/security-testing/` peer lines name the two desktop dev agents as where fixes go.

**Documentation (G1).** `CLAUDE.md` gets § Stack defaults (a `**Desktop**` line), § Version policy (macOS and Windows lines from §4.1–§4.2), the § Repository map row `desktop/`, and `desktop/` plus the two auth folders leave the under-construction line. `docs/skills-catalog.md` gets its scope paragraph, the slash-command surface rows, a recomputed command count and a `## Desktop dev catalog` section. `README.md` gets its layout line and status-table rows.

## 10. Authoring rules (every skill task)

1. **Shape.** Follow the `.skill-template/` sections; the `mobile-ios` sibling of the same folder is the voice and size pattern. Put a version-lane table near the top, keyed to §4. Routing clauses name siblings by `name:`.
2. **Budgets** (`tools/token-audit.py`, enforced at G1). The description is **≤ 200 characters** in the sibling form: `Use when … Triggers "…". Not for … (<sibling>).` The SKILL.md body is **≤ 16,000 characters; aim for 14,000**, with per-lane or per-path detail in `references/` from the start. Agents are ≤ 14,000 characters with a description ≤ 650. Count your own files with `wc -m` as you go.
3. **Research first; §4 is the floor.** §4 and the three research files are verified. Check anything else you state as a version or a date against the official source (developer.apple.com, swift.org, learn.microsoft.com, github.com/microsoft, nuget.org) before writing it. Re-check the §4.6 items before use. A fact that contradicts §4 becomes a dated `D<n>`, never a silent edit.
4. **The house rules bind the examples.** Code samples follow §5, CLAUDE.md § Simplicity (no unearned protocol or interface) and `ep-code-comments` (no inline comments). Test samples follow CLAUDE.md § Test code rules.
5. **Checklist rows.** Append your section's rows per §8.2 in the same task. A skill with no audit rows is unfinished.
6. **Corpus.** Every design fact cites a `design/ui-ux-pro-max` query with `--stack swiftui | winui | wpf`. Where the corpus and a skill disagree, the corpus wins.
7. **Complement, don't copy** (D10). Microsoft's `winui@win-dev-skills` and Apple's Xcode agent skills exist. Our skills carry the house rules, lanes and audits; they may tell the agent to use `winapp find-ui` / `find-api` or `xcrun mcp-server` where installed, and never require them.
8. **Unattended-session shell limits** (learned in plan 001): no brace expansion, no `$VAR` expansion, no `.sh` files, nothing written outside the worktree (not even `/tmp`). Scratch work goes in an untracked `scratch/` folder inside the worktree, deleted before committing.

## 11. The gate (G1 only)

Run these from the repo root in this order, and fix what fails: a failure may belong to any task above G1.

1. `python3 -m json.tool .claude-plugin/marketplace.json > /dev/null` exits 0.
2. `python3 tools/plugin-surface-check.py` prints `OK`.
3. `python3 tools/qa-version-check.py` exits 0.
4. `python3 tools/token-audit.py | grep -E "desktop|auth0-(macos|windows)"` prints nothing. The script's own exit code reflects violations that existed before this plan; read the lines, not the exit code.
5. The library check below prints `OK`. Save it as `scratch/library-check.py` (untracked; delete before committing) and run `python3 scratch/library-check.py`.

```python
import json, os, re, sys

LANGS = ("java", "dotnet", "typescript")
QA_SKILLS = ("desktop-project-setup", "desktop-screen-explorer", "desktop-window-objects")
DIRS = ["desktop", "auth/auth0-macos", "auth/auth0-windows", "qa/_shared/desktop-testing"]
DIRS += [f"qa/{lang}/skills/{s}" for lang in LANGS for s in QA_SKILLS]
FILES = [f"qa/{lang}/agents/qa-desktop-{lang}.md" for lang in LANGS]
FILES += [f"qa/{lang}/skills/rules/desktop-tests.md" for lang in LANGS]
FILES += [f"qa/{lang}/commands/desktop.md" for lang in LANGS]
STACKS = {"macos": 25, "windows": 25}
SECTIONS = {"macos": "ABCDEFGHIJMNOPRSV", "windows": "ABCDEFGHIJMNOPRSVX"}
FRAGMENTS = {"security": "K", "distribution": "L", "observability": "U"}
ALLOW = {"data-testid"}
GATE_LINE = "`Gate:` line"

fail = []
market = json.load(open(".claude-plugin/marketplace.json"))
names = {p["name"] for p in market["plugins"]}
for plugin in ("desktop-macos", "desktop-windows"):
    if plugin not in names:
        fail.append(f"marketplace: no {plugin} plugin")
for lang in LANGS:
    entry = next(p for p in market["plugins"] if p["name"] == f"qa-{lang}")
    for s in QA_SKILLS:
        if f"./qa/{lang}/skills/{s}" not in entry["skills"]:
            fail.append(f"marketplace qa-{lang}: {s} not registered")

defined = set()
for root, dirs, files in os.walk("."):
    if "/.git" in root:
        continue
    defined.update(dirs)
    for f in files:
        if not f.endswith(".md"):
            continue
        path = os.path.join(root, f)
        if "/commands/" in path:
            defined.add(f[:-3])
        if f == "SKILL.md" or "/agents/" in path:
            m = re.search(r"^name:\s*(\S+)", open(path, errors="ignore").read(), re.M)
            if m:
                defined.add(m.group(1))

name_token = re.compile(r"`((?:ep|qa|be|fe|design|data|ba|tool|devops|secgov|pentest|observability|auth|dev|mobile|desktop)-[a-z0-9-]+)`")
md_link = re.compile(r"\]\((?!https?:|mailto:|#)([^)\s]+?\.md)(?:#[^)]*)?\)")
paths = list(FILES)
for top in DIRS:
    if not os.path.isdir(top):
        fail.append(f"missing folder {top}")
        continue
    for root, _, files in os.walk(top):
        paths += [os.path.join(root, f) for f in files if f.endswith(".md")]
for path in paths:
    if not os.path.exists(path):
        fail.append(f"missing {path}")
        continue
    text = open(path, errors="ignore").read()
    for m in name_token.finditer(text):
        if m.group(1) not in defined and m.group(1) not in ALLOW:
            fail.append(f"unresolved name: {path}: {m.group(1)}")
    for m in md_link.finditer(text):
        if not os.path.exists(os.path.normpath(os.path.join(os.path.dirname(path), m.group(1)))):
            fail.append(f"broken link: {path}: {m.group(1)}")
    if "/agents/" in path and GATE_LINE not in text:
        fail.append(f"agent without the Gate line: {path}")

for stack, count in STACKS.items():
    base = os.path.join("desktop", stack, "skills")
    folders = sorted(d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d)))
    if len(folders) != count:
        fail.append(f"{base}: {len(folders)} skill folders, expected {count}")
    for d in folders:
        if not os.path.exists(os.path.join(base, d, "SKILL.md")):
            fail.append(f"missing {base}/{d}/SKILL.md")
    checklist = open(os.path.join(base, "standards-audit", "references", "conformance-checklist.md")).read()
    for letter in SECTIONS[stack]:
        if not re.search(rf"^\| {letter}\d+ \|", checklist, re.M):
            fail.append(f"{stack} checklist: section {letter} has no rows")
    agent = os.path.join("desktop", stack, "agents", f"desktop-{stack}.md")
    if not os.path.exists(agent) or len(open(agent, encoding="utf-8").read()) > 14000:
        fail.append(f"{agent}: missing or over 14,000 characters")
for d, letter in FRAGMENTS.items():
    fragment = os.path.join("desktop", "_shared", d, "references", "audit-checks.md")
    if not os.path.exists(fragment) or not re.search(rf"^\| {letter}\d+ \|", open(fragment).read(), re.M):
        fail.append(f"{fragment}: missing or no {letter} rows")

claude = open("CLAUDE.md").read()
if "## Desktop code rules" not in claude:
    fail.append("CLAUDE.md: no ## Desktop code rules")
if re.search(r"Under construction.*desktop/", claude):
    fail.append("CLAUDE.md: desktop/ still under construction")

print("\n".join(fail) or "OK")
sys.exit(1 if fail else 0)
```

Every entry added to `ALLOW` is justified in G1's `As built` note. These five steps are also how to re-check the domain later.

## Decisions

**D1 — Two native plugins in a new `desktop/` domain, with a bundled `desktop/_shared` layer.**

| Option | Verdict | Why |
|---|---|---|
| A macOS lane inside `mobile-ios`, a Windows lane inside `fe-blazor` or `be-dotnet` | Rejected | It would mix categories and audiences: a Mac project would install 30 iOS skills, and a Windows app is neither a web client nor a service |
| One `desktop` plugin for both platforms | Rejected | Swift and C# share no code, and a project installs one platform's skills, not both |
| **`desktop-macos` + `desktop-windows`, sharing `desktop/_shared`** | Chosen | Mirrors `mobile-*`; a project enables only its own platform |

Cost: a new category to wire (D13), and about 60 new skills to maintain.

**D2 — Windows primary: WinUI on Windows App SDK 2.x, C#, .NET 10, packaged MSIX. WPF, WinForms and C++/WinRT are lanes inside `desktop-windows`.** This is Microsoft's stated recommendation (`windows.md` §1). C++/WinRT is the user's answer (O2). .NET 11 is supported; .NET 8/9 are flagged as out of support. This deviates from CLAUDE.md § Version policy, which still says "8–9 supported" (Q2). Cost: the C++ lane adds a fourth idiom and about a third more content to `desktop-windows`.

**D3 — `desktop-macos` writes its own Swift `basics` and rule files, adapted from `mobile-ios`.** `tools/plugin-surface-check.py` rule 5 forbids registering `mobile/ios/skills/basics` from another category. Depending on `mobile-ios` would install 30 iOS skills into a Mac project. Cost: two Swift standards that can drift. M1 records in its As built note the commit of `mobile/ios/skills/basics` it adapted, so a later diff finds the drift.

**D4 — macOS deployment targets: 15 primary for new apps, 14 supported, 13 for existing apps, 12 the floor.** A universal binary is chosen per deployment target (§4.1). Cost: this is a recommendation derived from API availability, not an Apple rule; `basics` says so.

**D5 — Cross-platform frameworks are not taught here.** Electron and Tauri go to a later `fe-react` desktop-shell lane (Q1). MAUI, Avalonia and Uno are detected and named in `desktop-windows/basics`, not taught. The research suggested MAUI and Avalonia as lanes; this plan defers them to keep the native scope the user asked for. Compose Desktop is a mention in `mobile-android`'s KMP skill, made by I1. Flutter desktop goes to the Flutter plan, and Qt is deferred. Cost: a MAUI or Avalonia project gets detection and a pointer, not guidance.

**D6 — The spine is adapted, not copied.** `navigation` folds into the windows skills, `animation` into `styling`, `device-features` into `sandbox-and-permissions` / `platform-integration`, and `notifications-and-links` into `system-integration` / `activation-and-notifications`. Audit letters keep the mobile meaning; Q and T are unused, and X is Windows interop. Cost: the folder lists of the two plugins differ from the mobile ones, so a cross-domain comparison goes by letter, not by folder.

**D7 — The shared layer is distribution, security and observability; there is no in-app-purchase skill.** Mac App Store / Microsoft Store purchase APIs are a mention in `distribution`. Cost: an app that sells inside the app gets no StoreKit-on-Mac or Store-purchase guidance until a later plan adds it.

**D8 — Windows unit tests: NUnit for view models and services; the MSTest WinUI Unit Test App with `[UITestMethod]` only for code that needs XAML types.** Using MSTest there is a recorded deviation from the house NUnit default, because XAML types need the app-hosted runner. For the C++ lane, W4 chooses between the Microsoft C++ Unit Test Framework and GoogleTest, and the coverage tool, from current docs, and records the choice as a dated `D<n>`. Cost: two runners in one Windows solution where both kinds of tests exist.

**D9 — Desktop E2E is a skill set inside the three QA plugins plus a `qa-desktop-<lang>` agent, not a new plugin.** Mac2 4.6.1 and WinCore 3.3.2 are pinned explicitly on Appium 3. NovaWindows is the documented fallback. FlaUI covers Windows-only .NET suites. The legacy Windows driver and WinAppDriver are never taught. Appium 4 is tagged "from 4.0 GA". Cost: WinCore has been on npm only since 2026-09; if it fails on real apps, the fallback keeps the same `AutomationId` contract.

**D10 — Complement Microsoft's `winui@win-dev-skills` and Apple's Xcode agent skills instead of duplicating them.** Our skills own the house rules, the lanes and the audits. The agent may use `winapp` CLI (`find-ui`, `find-api`, `run`, `ui screenshot`) or `xcrun mcp-server` where installed, and never requires them. Cost: `winapp` is a public preview, so every `winapp` recipe carries its version (0.8.0) and a non-`winapp` fallback.

**D11 — Authoring tasks are `Gate: none`; G1 runs the plan's runnable checks once.** A skill is a document; the library check, surface check, token audit and version check need the marketplace wiring that lands in I1. Cost: stated in the header.

**D12 — Native auth gets two new skills, `auth/auth0-macos` and `auth/auth0-windows`,** rather than reusing `auth/auth0-ios`, which rule 5 forbids across categories. Both use the RFC 8252 system-browser + PKCE flow. Cost: Auth0.swift guidance exists in two places (iOS and macOS), which can drift.

**D13 — `desktop` is a new stack token and a new plugin category.** It goes into `plan-format.md`, `delivery-plan`, `solution-planner`, CLAUDE.md § Planning and `tools/plugin-surface-check.py`. The user's global `~/.claude/CLAUDE.md` rule 1 lists the stacks too; changing it is the user's step (the `—` row after G1), because no task writes outside the worktree. Cost: until the user edits it, the global rule and the library disagree on the stack list.

## Answered questions (2026-11-15)

**O1 — Does this plan also add desktop E2E to the QA plugins?** Yes, in the same plan (E1–E3).
**O2 — Which languages does `desktop-windows` cover?** C# / .NET, plus a C++/WinRT lane.
**O3 — Are there existing desktop plugins?** No. `grep` finds none (§1).

## Open questions

| # | Question | Options | Blocks | Owner |
|---|---|---|---|---|
| Q1 | Add an Electron + Tauri desktop-shell lane to `fe-react` (research: #1 and #2 desktop shells)? | its own later plan / not at all | nothing in this plan | user |
| Q2 | CLAUDE.md § Stack defaults and § Version policy say ".NET 10 primary / 8–9 supported", but .NET 8 and 9 went out of support on 2026-11-10 and .NET 11 is GA | update every `.NET` lane library-wide in a separate plan / leave it | nothing here (`desktop-windows` already uses 10/11, D2) but the library contradicts itself until decided | user |
| Q3 | Library pins are one minor behind (Appium 3.9.1, Playwright 1.65.1), and the mobile QA skills' unpinned `appium driver install` now resolves to Appium-4-only drivers (xcuitest 13, uiautomator2 9) | a small QA pin-fix plan / wait for Appium 4 GA | nothing here (§4.5) | user |

## 12. Tasks

### C1 — the `desktop/` domain, the code rules and the checklist skeletons

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `CLAUDE.md` has `## Desktop code rules` (§5 verbatim) and lists `desktop/`, `auth/auth0-macos` and `auth/auth0-windows` as under construction. `desktop/{macos,windows}/{skills,agents,commands}/` and `desktop/_shared/` exist. Both `conformance-checklist.md` skeletons hold every §8.1 heading with its owners, and rows only in V.
**Depends on:** —
**Budget:** ~90k: CLAUDE.md files 20k; plan §2, §5, §8 ~12k; `mobile/ios/skills/standards-audit/references/conformance-checklist.md` header and V rows ~10k; writes ~15k; reasoning ~25k.
**Gate: none.** Documents only; the plan gates once, in G1 (D11).

- Insert §5 into `CLAUDE.md` after § Mobile code rules, and add `desktop/`, `auth/auth0-macos`, `auth/auth0-windows` to the under-construction line (`CLAUDE.md:266`).
- Create the folder tree of §2. Git tracks no empty folders, so each new folder gets the file this task writes or a `.gitkeep` that the first task writing into it deletes.
- Write both checklist skeletons per §8.2. The V rows are adapted from the mobile-ios checklist's V rows, with the platform globs.
- **Not in C1:** any skill body, the marketplace (I1), the map row and catalog (G1).

### S1 — shared: distribution

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `desktop/_shared/distribution/{SKILL.md,references/macos.md,references/windows.md,references/audit-checks.md}` exist, and the fragment holds `L` rows with a `Platforms` column.
**Depends on:** C1.
**Budget:** ~145k: CLAUDE.md files 20k; plan §4, §6.5, §8.2, §10 ~14k; `macos.md` §1.4, §4 and `windows.md` §2, §6 ~20k; `mobile/_shared/release/SKILL.md` + `references/audit-checks.md` as the pattern ~12k; research for Sparkle, `notarytool`, Velopack, Artifact Signing and winget ~30k; writes ~35k.
**Gate: none.** Documents (D11).

- Cover §6.5's distribution row, with Developer ID vs Mac App Store and Store vs sideload vs unpackaged as one-of-N decisions, each with its rule table.
- Version facts: Sparkle 2.10.1, Velopack 1.2.161, Artifact Signing $9.99/month, the Developer ID CA expiring 2027-02-01. Re-check the §4.6 Artifact Signing eligibility item before writing it.
- **Not in S1:** pipeline YAML (`devops-engineer`'s), security rules (S2).

### S2 — shared: security and observability

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `desktop/_shared/{security,observability}/` exist, each with `SKILL.md`, `references/{macos,windows,audit-checks}.md`, and `K` / `U` rows with a `Platforms` column. Each security row cites its OWASP Desktop App Security Top 10 id.
**Depends on:** C1.
**Budget:** ~150k: CLAUDE.md files 20k; plan §5, §6.5, §8.2, §10 ~12k; `mobile/_shared/{security,observability}/SKILL.md` + fragments as patterns ~20k; research for the OWASP Desktop Top 10, hardened runtime / library validation, DLL search order, WebView2 / `WKWebView` lockdown, OTel Swift 2.6.0, OTel .NET desktop, Sentry ~45k; writes ~45k.
**Gate: none.** Documents (D11).

- Security per §6.5. Rows a static read cannot prove are marked **requires dynamic test → `qa-security`**.
- Observability per §6.5. The Collector and backends belong to the be-* `observability-engineer-<stack>` agents and are named, not taught.
- **Not in S2:** distribution (S1), auth (S3).

### S3 — native desktop Auth0

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `auth/auth0-macos/SKILL.md` and `auth/auth0-windows/SKILL.md` exist. The Windows skill names the Auth0 .NET SDK it uses for WinUI and WPF, cited to its current docs page.
**Depends on:** C1.
**Budget:** ~110k: CLAUDE.md files 20k; plan §5, §6.5 ~6k; `auth/auth0-ios/SKILL.md` and `auth/_shared/{auth0-concepts,oidc-concepts}` headings ~15k; research for Auth0.swift on macOS, the Auth0 .NET OIDC client packages, RFC 8252 loopback vs protocol activation ~35k; writes ~20k.
**Gate: none.** Documents (D11).

- Both skills use the system browser + PKCE flow and keep tokens in the Keychain / `PasswordVault` / DPAPI. Logout and refresh go through Auth0's credentials manager where the SDK has one.
- **Not in S3:** server-side token validation (`be-*` auth skills).

### M1 — macOS foundations

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `desktop/macos/skills/{basics,project-setup,architecture,ui-components,styling}/SKILL.md` exist, and the macOS checklist has rows in A–E.
**Depends on:** C1.
**Budget:** ~150k: CLAUDE.md files 20k; plan §4.1, §5, §6.1–§6.2, §8.2, §10 ~15k; `macos.md` §1, §2, §8 ~15k; the five `mobile/ios/skills` siblings as patterns ~30k; research for Liquid Glass on macOS, `Table` / `Inspector` APIs ~25k; writes ~40k.
**Gate: none.** Documents (D11).

- `basics` is adapted from `mobile/ios/skills/basics` (D3). Record in the As built note the `git log -1 --format=%h -- mobile/ios/skills/basics` it was adapted from.
- `project-setup` sets `SWIFT_VERSION` 6, sandbox and hardened runtime, and the deployment target and architectures per §4.1 / D4.
- **Not in M1:** windows, menus and documents (M2).

### M2 — macOS windows, menus, forms, documents and AppKit

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `desktop/macos/skills/{windows-and-scenes,menus-and-commands,forms,documents,appkit}/SKILL.md` exist, and the macOS checklist has rows in D (AppKit), F, G and I (documents).
**Depends on:** M1 (same checklist file).
**Budget:** ~150k: CLAUDE.md files 20k; plan §4.1, §5, §6.2, §8.2, §10 ~12k; `macos.md` §2.1–§2.5, §2.7 ~15k; `mobile/ios/skills/{navigation,forms,uikit}` as patterns ~20k; research for scene APIs on macOS 15 / 27, `commands`, `Document` ~35k; writes ~45k.
**Gate: none.** Documents (D11).

- `menus-and-commands` carries the HIG menu order, disabled-not-hidden and the hidden menu icons of the 27 SDK. Re-check the §4.6 `dropDestination` item before writing drag rules.
- **Not in M2:** networking, storage and platform skills (M3).

### M3 — macOS networking, storage, sandbox, background and system integration

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `desktop/macos/skills/{networking,offline-and-storage,sandbox-and-permissions,background-and-helpers,system-integration}/SKILL.md` exist, and the macOS checklist has rows in H, I and J.
**Depends on:** M2 (same checklist file).
**Budget:** ~150k: CLAUDE.md files 20k; plan §5, §6.2, §8.2, §10 ~10k; `macos.md` §3 ~12k; `mobile/ios/skills/{networking,offline-and-storage,device-features,system-integration}` as patterns ~25k; research for TCC, security-scoped bookmarks, `SMAppService`, `XPCSession`, App Intents on Mac ~35k; writes ~45k.
**Gate: none.** Documents (D11).

- Each skill per its §6.2 row. Every TCC permission gets a denied path that links to System Settings.
- **Not in M3:** the quality layers (M4).

### M4 — macOS quality layers, test ids and unit tests

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `desktop/macos/skills/{languages,accessibility,performance,error-handling,test-ids,unit-testing}/SKILL.md` exist, the macOS checklist has rows in M, N, O, P, R and S, and `test-ids` states the §8.5 Mac2 mapping, verified against the Mac2 driver docs.
**Depends on:** M3 (same checklist file).
**Budget:** ~150k: CLAUDE.md files 20k; plan §4.3–§4.4, §5, §6.4, §8.2, §8.5, §10 ~15k; `macos.md` §5–§7 ~12k; `mobile/ios/skills` siblings + `frontend/react/skills/error-handling` headings ~30k; research for VoiceOver / Full Keyboard Access, MetricKit on Mac, Mac2 locators ~25k; writes ~45k.
**Gate: none.** Documents (D11).

- `error-handling` applies §6.4, with rule bodies in `references/` from the start.
- **Not in M4:** migration, review, audit, rules and agent (M5).

### M5 — macOS migration, review, audit, rules, agent and commands

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `desktop/macos/skills/{migration,code-review,standards-audit,rules}/` exist (the rules skill with the ten §8.6 files), `desktop/macos/agents/desktop-macos.md` is ≤ 14,000 characters, `desktop/macos/commands/{desktop-macos,audit}.md` exist, and the checklist ends with a section index.
**Depends on:** M4 (same checklist file), S1, S2, S3 (the agent names them).
**Budget:** ~145k: CLAUDE.md files 20k; plan §5, §6.2, §7, §8, §10 ~20k; `mobile/ios/{agents/mobile-ios.md,commands/*,skills/{migration,code-review,standards-audit,rules}}` as patterns ~35k; `.skill-template/agent.md` ~4k; writes ~50k.
**Gate: none.** Documents (D11).

- The agent follows §7, and its Related agents list names `qa-desktop-java`, `qa-desktop-dotnet` and `qa-desktop-typescript`. Those agents land in E1–E3; the name check runs only at G1.
- The rule files are adapted from `mobile/ios/skills/rules/*.md`, with `paths:` fitted to Mac projects.
- **Not in M5:** marketplace wiring (I1).

### W1 — Windows foundations

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `desktop/windows/skills/{basics,project-setup,architecture,ui-components,styling}/SKILL.md` exist, and the Windows checklist has rows in A–E.
**Depends on:** C1.
**Budget:** ~150k: CLAUDE.md files 20k; plan §4.2, §5, §6.1, §6.3, §8.2, §10 ~15k; `windows.md` §1–§4 ~18k; `mobile/android/skills` siblings + `frontend/blazor/skills/basics` headings as patterns ~25k; research for the `winapp` templates, CommunityToolkit.Mvvm 8.4, Fluent theme resources ~30k; writes ~40k.
**Gate: none.** Documents (D11).

- `basics` holds the lane table and the detection markers (§6.3). Re-check the §4.6 template items (`TargetPlatformMinVersion`, `winui-mvvm` DI) before writing them.
- **Not in W1:** windows, activation and platform skills (W2).

### W2 — Windows windows and navigation, activation and notifications, platform integration, forms

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `desktop/windows/skills/{windows-and-navigation,activation-and-notifications,platform-integration,forms}/SKILL.md` exist, plus `platform-integration/references/windows-ai.md`, and the Windows checklist has rows in F, G and J.
**Depends on:** W1 (same checklist file).
**Budget:** ~150k: CLAUDE.md files 20k; plan §4.2, §5, §6.3, §8.2, §10 ~12k; `windows.md` §3, §5 ~12k; research for `AppWindow` / `TitleBar`, `AppInstance`, `AppNotificationManager`, the new pickers, WebView2 security, the Windows AI APIs ~50k; writes ~45k.
**Gate: none.** Documents (D11).

- Re-check the §4.6 startup / background / share-target items before writing them.
- **Not in W2:** networking, storage and lanes (W3).

### W3 — Windows networking, storage, interop, WPF and WinForms

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `desktop/windows/skills/{networking,offline-and-storage,interop,wpf,winforms}/SKILL.md` exist, and the Windows checklist has rows in D (`[WPF]`, `[WinForms]`), H, I and X.
**Depends on:** W2 (same checklist file).
**Budget:** ~150k: CLAUDE.md files 20k; plan §4.2, §5, §6.3, §8.2, §10 ~12k; `windows.md` §1 (WPF, WinForms), §3, §10 ~12k; `backend/dotnet` HTTP-client skill headings ~8k; research for the WPF Fluent theme, WinForms .NET 10/11, CsWinRT 2.3, `LibraryImport`, `PasswordVault` unpackaged (§4.6) ~45k; writes ~50k.
**Gate: none.** Documents (D11).

- `wpf` and `winforms` say plainly that the lane stays itself, with modernization in place. Moving to WinUI is a `migration` run, never a side effect.
- **Not in W3:** the C++ lane (W4).

### W4 — the C++/WinRT lane

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `desktop/windows/skills/cpp-winrt/SKILL.md` and its `references/` exist. The Windows checklist has `[C++]` rows in X, plus a `[C++]` row in each of B, C, N and S where the C++ rule differs. A dated `D<n>` records the C++ unit-test framework and coverage tool (D8). The §5 C++/WinRT bullet in `CLAUDE.md` matches what was verified.
**Depends on:** W3 (same checklist file).
**Budget:** ~140k: CLAUDE.md files 20k; plan §4.2, §5, §6.3, §7.2, §8.2, D8 ~12k; `windows.md` §1 (Other stacks) ~4k; research for C++/WinRT docs (ownership, coroutines, strong/weak references, `wil`, IDL / MIDL, XAML in C++), the Microsoft C++ Unit Test Framework vs GoogleTest for WinUI, OpenCppCoverage / VS coverage ~60k; writes ~40k.
**Gate: none.** Documents (D11).

- Verify every C++ rule in §5 against learn.microsoft.com before writing it, and rewrite the `CLAUDE.md` bullet in place if a fact differs (a dated `D<n>` too).
- Rewrite W6's prompt for any C++ fact it must carry: the rule file `cppwinrt.md` and the agent's C++ build / test commands in §7.2.
- **Not in W4:** the shared quality layers (W5).

### W5 — Windows quality layers, test ids and unit tests

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `desktop/windows/skills/{languages,accessibility,performance,error-handling,test-ids,unit-testing}/SKILL.md` exist, the Windows checklist has rows in M, N, O, P, R and S, and `test-ids` states the §8.5 `AutomationId` mapping, verified against the WinCore and FlaUI docs.
**Depends on:** W4 (same checklist file).
**Budget:** ~150k: CLAUDE.md files 20k; plan §4.3–§4.4, §5, §6.4, §8.2, §8.5, D8, §10 ~15k; `windows.md` §7–§9 ~12k; `mobile/android/skills` siblings + `frontend/react/skills/error-handling` headings ~25k; research for UIA / Narrator, the WinUI Unit Test App, PerfView / WPR, AOT trimming ~30k; writes ~45k.
**Gate: none.** Documents (D11).

- `unit-testing` per D8. `error-handling` per §6.4, with stowed-exception triage.
- **Not in W5:** migration, review, audit, rules and agent (W6).

### W6 — Windows migration, review, audit, rules, agent and commands

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `desktop/windows/skills/{migration,code-review,standards-audit,rules}/` exist (the rules skill with the twelve §8.6 files), `desktop/windows/agents/desktop-windows.md` is ≤ 14,000 characters, `desktop/windows/commands/{desktop-windows,audit}.md` exist, and the checklist ends with a section index.
**Depends on:** W5 (same checklist file), S1, S2, S3.
**Budget:** ~150k: CLAUDE.md files 20k; plan §5, §6.3, §7, §8, §10 ~20k; `mobile/android/{agents,commands}` + `skills/{migration,code-review,standards-audit,rules}` as patterns ~35k; `windows.md` §10–§11 ~6k; writes ~55k.
**Gate: none.** Documents (D11).

- The agent covers the four lanes (C#: WinUI / WPF / WinForms; C++/WinRT) through §7's steps and §7.2's commands; detection decides the lane. Its Related agents name the three `qa-desktop-<lang>` agents.
- **Not in W6:** marketplace wiring (I1).

### E1 — QA desktop: shared rules and the TypeScript lane

**Stack:** `qa` · **Agent:** `general-purpose`
**Deliverable:** `qa/_shared/desktop-testing/SKILL.md` exists. In `qa/typescript/`: `skills/{desktop-project-setup,desktop-screen-explorer,desktop-window-objects}/SKILL.md`, `skills/rules/desktop-tests.md` (listed in that rules skill's table), `agents/qa-desktop-typescript.md` and `commands/desktop.md` exist. The Mac2 4.6.1 and WinCore 3.3.2 peer ranges are confirmed against Appium 3.8.0 (§4.5).
**Depends on:** M4, W5 (the test-id mapping).
**Budget:** ~150k: CLAUDE.md files 20k; plan §4.4–§4.5, §6.6, §8.5, D9 ~12k; `cross-platform-and-qa.md` Part B ~15k; `qa/typescript/{agents/qa-mobile-typescript.md,commands/mobile.md,skills/{mobile-project-setup,mobile-screen-explorer,mobile-screen-objects}/SKILL.md,skills/rules/mobile-tests.md}` as patterns ~45k; the two dev `test-ids` skills ~6k; writes ~45k.
**Gate: none.** Documents (D11). Do not run `tools/qa-version-check.py`; G1 runs it.

- Use the `qa-mobile-typescript` shape throughout. Every version follows §4.4–§4.5; Electron and Tauri are out of scope (Q1).
- Rewrite E2's and E3's prompts for anything they must mirror: shared-skill section names and the explorer's report shape.
- **Not in E1:** the Java and .NET lanes (E2, E3).

### E2 — QA desktop: the Java lane

**Stack:** `qa` · **Agent:** `general-purpose`
**Deliverable:** in `qa/java/`: the three `desktop-*` skills, `skills/rules/desktop-tests.md` (listed in its rules skill), `agents/qa-desktop-java.md` and `commands/desktop.md` exist.
**Depends on:** E1.
**Budget:** ~130k: CLAUDE.md files 20k; plan §4.4, §6.6, D9 ~8k; `cross-platform-and-qa.md` B.5–B.6 ~6k; `qa/_shared/desktop-testing` + E1's TypeScript skills as the pattern ~25k; `qa/java` mobile trio + agent + command ~30k; writes ~40k.
**Gate: none.** Documents (D11).

- Mirror E1. Use TestNG + `java-client` 11: `Mac2Driver`, and for WinCore, `BaseOptions` or `WindowsOptions` with `automationName` overridden.
- **Not in E2:** the `qa/dotnet` tree (E3, which runs beside this task).

### E3 — QA desktop: the .NET lane

**Stack:** `qa` · **Agent:** `general-purpose`
**Deliverable:** in `qa/dotnet/`: the three `desktop-*` skills (with the FlaUI 5.0.0 lane in `desktop-project-setup` and `desktop-window-objects`), `skills/rules/desktop-tests.md` (listed in its rules skill), `agents/qa-desktop-dotnet.md` and `commands/desktop.md` exist.
**Depends on:** E1.
**Budget:** ~140k: CLAUDE.md files 20k; plan §4.4, §6.6, D9 ~8k; `cross-platform-and-qa.md` B.1, B.5–B.6 ~8k; `qa/_shared/desktop-testing` + E1's skills ~25k; `qa/dotnet` mobile trio + agent + command ~30k; research for FlaUI 5 UIA3 and Playwright .NET `ConnectOverCDPAsync` ~15k; writes ~40k.
**Gate: none.** Documents (D11).

- Mirror E1. Use NUnit + `Appium.WebDriver` 9; FlaUI is the Windows-only alternative, and Playwright .NET covers WebView2 content.
- **Not in E3:** the `qa/java` tree (E2).

### I1 — marketplace, surface check, planning lane and QA wiring

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `.claude-plugin/marketplace.json` lists `desktop-macos` and `desktop-windows`, and the three QA entries list their desktop skills, agent and command, with every path existing on disk. `tools/plugin-surface-check.py` has `desktop` in `STACK_CATEGORIES`. The plan format, delivery plan and solution planner accept a `desktop` task routed to the two agents.
**Depends on:** M5, W6, E2, E3, S1, S2, S3.
**Budget:** ~120k: CLAUDE.md files 20k; plan §2, §9, D13 ~8k; the `mobile-ios` marketplace entry ~4k and five entries written or edited ~15k; `plan-format.md:119`, `delivery-plan/SKILL.md:44,128,345`, `solution-planner.md` stack lists and routing ~12k; `qa/*/skills/device-cloud/SKILL.md` ~6k; `qa/_shared/security-testing` peer lines ~3k; `mobile/android/skills/kotlin-multiplatform/SKILL.md` lane line ~3k; folder listings ~4k; edits ~15k.
**Gate: none.** Wiring only; G1 runs every check (D11).

- Marketplace per §9: build every array from `ls`. The planning lane per §9 and D13. The QA wiring per §9.
- Add one Compose Multiplatform Desktop mention line to `mobile-android`'s KMP skill (D5).
- **Not in I1:** the CLAUDE.md map and version lines, the catalog and README (G1).

### G1 — documentation, the gate and filing the plan

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `CLAUDE.md`, `docs/skills-catalog.md` and `README.md` describe the desktop domain and the QA desktop lane, §11's five checks pass, and this plan is in `docs/plans/implemented/`.
**Depends on:** I1 and every task above.
**Budget:** ~140k: CLAUDE.md files 20k; plan header, §2, §4.1–§4.2, §9, §11 ~16k; the catalog's scope paragraph, slash-command table and `## Mobile dev catalog` as the pattern ~12k; README layout and status rows ~4k; writes ~15k; gate output ~15k; fixes ~45k.
**Gate (this is the last task, so it runs the whole set once more across the plan, in run order):** §11 steps 1–5. Fix what fails by the fix loop: the whole set once; each failure fixed with the narrowest rerun; only the failed rerun; the whole set once more. A failure may belong to any task above.

- Documentation per §9: § Stack defaults `**Desktop**` line, § Version policy macOS and Windows lines, § Repository map `desktop/` row, the under-construction line, the catalog (recompute the command count, never guess it) and the README.
- Rewrite `**Status:**` one last time. Name what is delivered and what is unverified: no agent has been run against a real app, no desktop E2E has run on a runner, and the facts are as of 2026-11-15. Name what is next: Q1–Q3, and the user's global-rules edit.
- **Not in G1:** feature work of any kind.

## Close-out — every task

Before you stop, in this order, in this file. Another task may be running in this working tree:
re-read this file immediately before these edits, and touch only your own task block, your own prompt
block and the line that says which have landed.

1. **As built** — append a dated `**As built (YYYY-MM-DD):**` bullet to your task block: what differed
   from the plan, the ids and names you assigned, what is built but unverified, and the `file:line` or
   command output that proves the deliverable exists. Never edit an earlier note.
2. **Decisions** — where you built something differently from the plan, append a dated `D<n>` to
   `## Decisions` with both readings. A divergence is recorded, never absorbed.
3. **The blocks below yours** — rewrite, in place, every prompt block whose assumptions your work
   changed (a renamed file, a changed signature, a moved gate), and write any block left
   `Blocked on <your id>` from what you now know.
4. **Status** — rewrite the header `**Status:**` line: what is built, what is next, what is built but
   unverified. When a task is running beside you, leave it: the next task that waits for you rewrites it.
5. **Commit the work** — the code, its tests and these plan edits together, on the current branch (under
   Plan Queue, the plan's branch in its worktree; never check out the default branch), adding only your
   own files, by path — never `git add -A`. Your prompt block is still in the plan.
6. **Merge, gate task only** — if you are the task that ran the whole set and this plan runs on its own
   branch, merge the default branch into it now, resolve every conflict by keeping both sides' rows,
   re-run the failing suites if code conflicted, and commit the merge, so the plan merges back cleanly
   and the documentation task after you documents the merged code.
7. **Your own block** — only now delete it, and update the line above the blocks that says which have
   landed, in a follow-up commit of its own: `docs: delete <id>'s prompt (<plan>)`. Do not stop between
   the two commits. Stopping mid-task: keep it, with a `Picking up from:` line. Blocked: keep it, naming
   the blocker and its owner. When the queue says other tasks of this plan are running beside you, do
   not commit, stash, reset or check out at all: make this deletion your last edit, and the queue
   commits the work and the deletion together.
8. **Filing** — if your deletion left no blocks, rewrite `**Status:**` one final time (what the plan
   delivered, what is still unverified), `git mv` this plan into `docs/plans/implemented/`, same name and
   number — a `solution-planner` pack moves its whole initiative folder — and add its row to that
   folder's README where there is one, in the same follow-up commit.

## Prompts — one per task

Run them one Plan Queue session each; every block is complete on its own. After C1, the tasks S1, S2, S3, M1 and W1 run side by side. The M chain and the W chain then each run in order, because each chain shares one checklist file. E1 waits for M4 and W5. E2 and E3 run beside each other. I1 waits for both chains and the QA lane, and G1 runs last. Only G1 runs anything (§11): no other block runs `tools/token-audit.py`, `tools/plugin-surface-check.py`, `tools/qa-version-check.py`, §11's script, a linter or a build. Counting your own files with `wc -m` is allowed. No block edits `docs/plans/implemented/**`, `docs/audits/**` or `docs/research/**`. **Unattended sessions refuse some shell forms** (plan 001): no brace expansion, no `$VAR` expansion, no `.sh` files, and nothing written outside the worktree, not even `/tmp`. Scratch work goes in an untracked `scratch/` folder inside the worktree, deleted before committing. This repo commits straight to `master`.

| # | Stack | Agent | Depends on | Runs beside | Budget |
|---|---|---|---|---|---|
| C1 | `docs` | `general-purpose` | none | — | ~90k |
| S1 | `docs` | `general-purpose` | C1 | S2, S3, M1, W1 | ~145k |
| S2 | `docs` | `general-purpose` | C1 | S1, S3, M1, W1 | ~150k |
| S3 | `docs` | `general-purpose` | C1 | S1, S2, M1, W1 | ~110k |
| M1 | `docs` | `general-purpose` | C1 | S1–S3, W1 | ~150k |
| M2 | `docs` | `general-purpose` | M1 | W-chain | ~150k |
| M3 | `docs` | `general-purpose` | M2 | W-chain | ~150k |
| M4 | `docs` | `general-purpose` | M3 | W-chain | ~150k |
| M5 | `docs` | `general-purpose` | M4, S1, S2, S3 | W-chain | ~145k |
| W1 | `docs` | `general-purpose` | C1 | S1–S3, M1 | ~150k |
| W2 | `docs` | `general-purpose` | W1 | M-chain | ~150k |
| W3 | `docs` | `general-purpose` | W2 | M-chain | ~150k |
| W4 | `docs` | `general-purpose` | W3 | M-chain | ~140k |
| W5 | `docs` | `general-purpose` | W4 | M-chain | ~150k |
| W6 | `docs` | `general-purpose` | W5, S1, S2, S3 | M-chain, E1–E3 | ~150k |
| E1 | `qa` | `general-purpose` | M4, W5 | M5, W6 | ~150k |
| E2 | `qa` | `general-purpose` | E1 | E3, M5, W6 | ~130k |
| E3 | `qa` | `general-purpose` | E1 | E2, M5, W6 | ~140k |
| I1 | `docs` | `general-purpose` | M5, W6, E2, E3, S1, S2, S3 | — | ~120k |
| G1 | `docs` | `general-purpose` | I1 | — | ~140k |
| — | add `desktop` to rule 1's stack list in `~/.claude/CLAUDE.md` (D13), and enable `desktop-<os>` in a real project to try the agent | **the user** | G1 | — | — |

No task has landed; every prompt below is live.

---

### C1 — the desktop domain, the code rules and the checklist skeletons (general-purpose, docs)

````
Depends on: none
Agent: general-purpose · Stack: docs

Task C1 of docs/plans/012-desktop-plugins.md: create the `desktop/` domain, put the Desktop code rules into CLAUDE.md, and write the two conformance-checklist skeletons.

Deliverable: `CLAUDE.md` has `## Desktop code rules` (§5 verbatim) and lists `desktop/`, `auth/auth0-macos`, `auth/auth0-windows` as under construction; `desktop/{macos,windows}/{skills,agents,commands}/` and `desktop/_shared/` exist; both `desktop/<os>/skills/standards-audit/references/conformance-checklist.md` skeletons hold every §8.1 heading with its owners and rows only in V.

Read, in this order:
1. CLAUDE.md (§ Mobile code rules and the Repository map's under-construction line, `CLAUDE.md:266`).
2. The plan: §2, §5, §8.1–§8.2, D6, D11, and "Close-out — every task".
3. `mobile/ios/skills/standards-audit/references/conformance-checklist.md`: its header text and section V only.

Do:
- Insert §5 into CLAUDE.md directly after § Mobile code rules, verbatim. Add `desktop/`, `auth/auth0-macos`, `auth/auth0-windows` to the under-construction line.
- Create the §2 tree. Git tracks no empty folders: put a `.gitkeep` in each empty one.
- Write both checklist skeletons per §8.2: the header adapted to macOS / Windows, every §8.1 section heading with its owners (K, L, U say they take the `desktop/_shared/<skill>/references/audit-checks.md` rows whose `Platforms` column names the platform; X on macOS says N/A), and V rows adapted from mobile-ios's V rows with the §8.2 globs.

Traps:
- Q and T are unused letters (D6): do not write those headings.
- Do not touch the marketplace, `docs/skills-catalog.md` or README (I1, G1).

Gate: none. Documents only; the plan gates once, in G1.
Commit: `feat(desktop): domain skeleton, Desktop code rules, checklist skeletons (012 C1)`.
Close out per the plan's "Close-out — every task" before you stop.
````

### S1 — shared: distribution (general-purpose, docs)

````
Depends on: C1
Agent: general-purpose · Stack: docs

Task S1 of docs/plans/012-desktop-plugins.md: write the shared desktop distribution skill.

Deliverable: `desktop/_shared/distribution/{SKILL.md,references/macos.md,references/windows.md,references/audit-checks.md}` exist; the fragment holds `L` rows with a `Platforms` column.

Read, in this order:
1. CLAUDE.md.
2. The plan: §4.1–§4.3, §4.6, §6.5 (distribution row), §8.2, §8.3, §10, and "Close-out — every task".
3. `docs/research/012-desktop-plugins/macos.md` §1.4 and §4; `windows.md` §2 (Packaging row) and §6.
4. `mobile/_shared/release/SKILL.md` and `mobile/_shared/release/references/audit-checks.md`: the shape and the fragment columns.

Do:
- SKILL.md: when to use / not, a version-lane table, the channel decision per platform (Developer ID vs Mac App Store; Store vs MSIX sideload vs unpackaged + Velopack), the signing and update rules, the CI-runner pins and where secrets live. Per-platform detail goes in the two references.
- `audit-checks.md`: rows `L1…Ln` with columns `| # | Check | Violation looks like | Find it with | Sev | Platforms |`.
- Description ≤ 200 characters in the sibling form; body ≤ 16,000 (aim 14,000); `wc -m` as you go.

Traps:
- Re-check against the official page before writing it: Artifact Signing eligibility outside the US/Canada (§4.6), and Sparkle 2.10.1 / Velopack 1.2.161 still being current.
- The 2027-02-01 Developer ID CA expiry is a blocker-class row for `.pkg` signing.
- Pipeline YAML is `devops-engineer`'s: name it, do not write it.

Gate: none. Documents only (D11).
Commit: `feat(desktop): shared distribution skill (012 S1)`.
Close out per the plan's "Close-out — every task" before you stop.
````

### S2 — shared: security and observability (general-purpose, docs)

````
Depends on: C1
Agent: general-purpose · Stack: docs

Task S2 of docs/plans/012-desktop-plugins.md: write the shared desktop security and observability skills.

Deliverable: `desktop/_shared/security/` and `desktop/_shared/observability/` exist, each with `SKILL.md` and `references/{macos,windows,audit-checks}.md`; `K` and `U` rows carry a `Platforms` column; each security row cites its OWASP Desktop App Security Top 10 id.

Read, in this order:
1. CLAUDE.md.
2. The plan: §4.3, §4.6, §5, §6.5 (security and observability rows), §8.2–§8.3, §10, and "Close-out — every task".
3. `mobile/_shared/security/SKILL.md` + `references/audit-checks.md` and `mobile/_shared/observability/SKILL.md` + `references/audit-checks.md`: shape and columns.
4. `docs/research/012-desktop-plugins/macos.md` §3.1, §7; `windows.md` §5 (credentials, WebView2), §6, §9.

Research first (official sources): the current OWASP Desktop App Security Top 10 edition and ids; hardened runtime and library validation; Windows DLL search order and safe loading; WebView2 and `WKWebView` hardening; OTel Swift 2.6.0 and OpenTelemetry .NET in a desktop process; Sentry for macOS and WinUI.

Traps:
- What a static read cannot prove is marked **requires dynamic test → `qa-security`**, never passed.
- The Collector, Tempo, Loki and Prometheus are the be-* `observability-engineer-<stack>` agents': name them, do not teach them.
- Each SKILL.md ≤ 16,000 characters; description ≤ 200.

Gate: none. Documents only (D11).
Commit: `feat(desktop): shared security and observability skills (012 S2)`.
Close out per the plan's "Close-out — every task" before you stop.
````

### S3 — native desktop Auth0 (general-purpose, docs)

````
Depends on: C1
Agent: general-purpose · Stack: docs

Task S3 of docs/plans/012-desktop-plugins.md: write `auth/auth0-macos` and `auth/auth0-windows`.

Deliverable: `auth/auth0-macos/SKILL.md` and `auth/auth0-windows/SKILL.md` exist; the Windows skill names the Auth0 .NET SDK it uses for WinUI and WPF, cited to its current docs page.

Read, in this order:
1. CLAUDE.md.
2. The plan: §5, §6.5 (auth rows), D12, §10, and "Close-out — every task".
3. `auth/auth0-ios/SKILL.md` (shape and voice), and the headings of `auth/_shared/auth0-concepts` and `auth/_shared/oidc-concepts`.

Research first: Auth0.swift on macOS (`ASWebAuthenticationSession`, `CredentialsManager`); which Auth0 .NET OIDC client package currently supports WinUI and WPF, and how its redirect works (loopback vs protocol activation); RFC 8252.

Traps:
- Never an embedded web view for login. System browser + PKCE only.
- Tokens only in the Keychain / `PasswordVault` / DPAPI (§5).
- Description ≤ 200 characters; `name:` follows the existing auth skills' frontmatter.

Gate: none. Documents only (D11).
Commit: `feat(auth): Auth0 for macOS and Windows desktop apps (012 S3)`.
Close out per the plan's "Close-out — every task" before you stop.
````

### M1 — macOS foundations (general-purpose, docs)

````
Depends on: C1
Agent: general-purpose · Stack: docs

Task M1 of docs/plans/012-desktop-plugins.md: write the five macOS foundation skills.

Deliverable: `desktop/macos/skills/{basics,project-setup,architecture,ui-components,styling}/SKILL.md` exist; the macOS checklist has rows in A–E.

Read, in this order:
1. CLAUDE.md.
2. The plan: §4.1, §4.6, §5, §6.1–§6.2, §8.2–§8.3, D3, D4, D6, §10, and "Close-out — every task".
3. `docs/research/012-desktop-plugins/macos.md` §1, §2, §8.
4. The siblings `mobile/ios/skills/{basics,project-setup,architecture,ui-components,styling}/SKILL.md`: frontmatter (`name:` convention), shape, size.
5. `desktop/macos/skills/standards-audit/references/conformance-checklist.md` (C1's skeleton).

Do:
- Each skill per its §6.2 row, with a version-lane table keyed to §4.1. `styling` includes motion and Reduce Motion (D6).
- `basics` is adapted from `mobile/ios/skills/basics` (D3). Put `git log -1 --format=%h -- mobile/ios/skills/basics` in your As built note.
- Design facts cite `design/ui-ux-pro-max` with `--stack swiftui`.
- Append A–E rows per §8.2 with the `[mac15+]`, `[mac27SDK]` and other tags.

Traps:
- The deployment-target lanes are a recommendation (D4); say so in `basics`.
- Liquid Glass cannot be opted out of on the 27 SDK; confirm current glass API names against developer.apple.com before using them.
- Description ≤ 200 characters, body ≤ 16,000 (aim 14,000); `wc -m` as you go.

Gate: none. Documents only (D11).
Commit: `feat(desktop-macos): foundations (012 M1)`.
Close out per the plan's "Close-out — every task" before you stop.
````

### M2 — macOS windows, menus, forms, documents and AppKit (general-purpose, docs)

````
Depends on: M1
Agent: general-purpose · Stack: docs

Task M2 of docs/plans/012-desktop-plugins.md: write `windows-and-scenes`, `menus-and-commands`, `forms`, `documents` and `appkit` for macOS.

Deliverable: `desktop/macos/skills/{windows-and-scenes,menus-and-commands,forms,documents,appkit}/SKILL.md` exist; the macOS checklist has rows in D (`[AppKit]`), F, G and I (documents).

Read, in this order:
1. CLAUDE.md.
2. The plan: §4.1, §4.6, §5, §6.2, §8.2–§8.3, §10, and "Close-out — every task".
3. `docs/research/012-desktop-plugins/macos.md` §2.1–§2.5 and §2.7.
4. Siblings for shape: `mobile/ios/skills/{navigation,forms,uikit}/SKILL.md`; M1's `desktop/macos/skills/basics/SKILL.md` for routing names.
5. The macOS checklist as M1 left it: continue each section's numbering.

Traps:
- `pushWindow` does not exist on macOS: use `openWindow`. Commands read state through `@FocusedValue` / `focusedSceneValue`.
- Menu items are disabled, never hidden. The 27 SDK hides menu icons by default.
- New document code uses `Document`, not the deprecated `FileDocument`. Re-check the §4.6 `dropDestination` item before writing drag-and-drop rules.

Gate: none. Documents only (D11).
Commit: `feat(desktop-macos): windows, menus, forms, documents, AppKit (012 M2)`.
Close out per the plan's "Close-out — every task" before you stop.
````

### M3 — macOS networking, storage, sandbox, background and system integration (general-purpose, docs)

````
Depends on: M2
Agent: general-purpose · Stack: docs

Task M3 of docs/plans/012-desktop-plugins.md: write `networking`, `offline-and-storage`, `sandbox-and-permissions`, `background-and-helpers` and `system-integration` for macOS.

Deliverable: `desktop/macos/skills/{networking,offline-and-storage,sandbox-and-permissions,background-and-helpers,system-integration}/SKILL.md` exist; the macOS checklist has rows in H, I and J.

Read, in this order:
1. CLAUDE.md.
2. The plan: §4.1, §5, §6.2, §8.2–§8.3, §10, and "Close-out — every task".
3. `docs/research/012-desktop-plugins/macos.md` §3.
4. Siblings: `mobile/ios/skills/{networking,offline-and-storage,device-features,system-integration}/SKILL.md`.
5. The macOS checklist as M2 left it.

Traps:
- Every TCC permission has a working denied path that links to System Settings; Full Disk Access is never assumed.
- Security-scoped bookmarks: start/stop balanced, and a stale bookmark is a recoverable state (§6.4).
- Login items and helpers use `SMAppService`, never hand-installed launchd plists; IPC uses `XPCSession`.

Gate: none. Documents only (D11).
Commit: `feat(desktop-macos): networking, storage, sandbox, helpers, system integration (012 M3)`.
Close out per the plan's "Close-out — every task" before you stop.
````

### M4 — macOS quality layers, test ids and unit tests (general-purpose, docs)

````
Depends on: M3
Agent: general-purpose · Stack: docs

Task M4 of docs/plans/012-desktop-plugins.md: write `languages`, `accessibility`, `performance`, `error-handling`, `test-ids` and `unit-testing` for macOS.

Deliverable: the six `desktop/macos/skills/<folder>/SKILL.md` exist; the macOS checklist has rows in M, N, O, P, R and S; `test-ids` states the §8.5 Mac2 mapping, verified against the Mac2 driver docs.

Read, in this order:
1. CLAUDE.md (§ Test code rules too).
2. The plan: §4.3–§4.4, §5, §6.4, §8.2–§8.3, §8.5, §10, and "Close-out — every task".
3. `docs/research/012-desktop-plugins/macos.md` §5–§7; `cross-platform-and-qa.md` B.2.
4. Siblings: `mobile/ios/skills/{languages,accessibility,performance,error-handling,test-ids,unit-testing}/SKILL.md`; the headings of `frontend/react/skills/error-handling/SKILL.md`.
5. The macOS checklist as M3 left it.

Traps:
- `error-handling` applies §6.4: multi-window consistency, wake-from-sleep revalidation, no modal alerts for background failures. Rule bodies go in `references/` from the start.
- Minimum control 20×20 pt and text 10 pt are macOS HIG facts (§4.3); MetricKit on Mac is checked before it is claimed.
- E1 builds on your `test-ids` contract: state it as one table (element kind → identifier → what Mac2 reads).

Gate: none. Documents only (D11).
Commit: `feat(desktop-macos): quality layers, test ids, unit tests (012 M4)`.
Close out per the plan's "Close-out — every task" before you stop.
````

### M5 — macOS migration, review, audit, rules, agent and commands (general-purpose, docs)

````
Depends on: M4, S1, S2, S3
Agent: general-purpose · Stack: docs

Task M5 of docs/plans/012-desktop-plugins.md: finish `desktop-macos`: migration, code-review, standards-audit, the rules skill, the agent and the two commands.

Deliverable: `desktop/macos/skills/{migration,code-review,standards-audit,rules}/` exist (rules with the ten §8.6 files); `desktop/macos/agents/desktop-macos.md` ≤ 14,000 characters; `desktop/macos/commands/{desktop-macos,audit}.md` exist; the checklist ends with a section index.

Read, in this order:
1. CLAUDE.md.
2. The plan: §5, §6.2, §7, §8 (all), §10, and "Close-out — every task".
3. `.skill-template/agent.md`; `mobile/ios/agents/mobile-ios.md`; `mobile/ios/commands/{mobile-ios,audit}.md`.
4. `mobile/ios/skills/{migration,code-review,standards-audit}/SKILL.md` and `mobile/ios/skills/rules/` (the SKILL.md and the rule files to adapt).
5. The `name:` of every `desktop/macos/skills/*/SKILL.md`, `desktop/_shared/*/SKILL.md` and `auth/auth0-macos/SKILL.md`, for the agent's routing.

Traps:
- The agent carries the template's `Gate:` line verbatim and names `qa-desktop-java`, `qa-desktop-dotnet` and `qa-desktop-typescript` as related agents. Those land in E1–E3, and G1 checks the names.
- `migration` includes the 2027-02-01 Developer ID CA and Intel → Apple silicon only (§4.1).
- The rules skill's procedure and unattended default are copied from the mobile-ios one; only the file table and paths change.

Gate: none. Documents only (D11).
Commit: `feat(desktop-macos): migration, review, audit, rules, agent, commands (012 M5)`.
Close out per the plan's "Close-out — every task" before you stop.
````

### W1 — Windows foundations (general-purpose, docs)

````
Depends on: C1
Agent: general-purpose · Stack: docs

Task W1 of docs/plans/012-desktop-plugins.md: write the five Windows foundation skills.

Deliverable: `desktop/windows/skills/{basics,project-setup,architecture,ui-components,styling}/SKILL.md` exist; the Windows checklist has rows in A–E.

Read, in this order:
1. CLAUDE.md.
2. The plan: §3, §4.2, §4.6, §5, §6.1, §6.3, §8.2–§8.3, D2, D5, D10, §10, and "Close-out — every task".
3. `docs/research/012-desktop-plugins/windows.md` §1–§4.
4. Siblings for shape and `name:` convention: `mobile/android/skills/{basics,project-setup,architecture,ui-components,styling}/SKILL.md`.
5. `desktop/windows/skills/standards-audit/references/conformance-checklist.md` (C1's skeleton).

Do:
- `basics` holds the lane table (WinUI / WPF / WinForms / C++/WinRT) and the detection markers, and names MAUI, Avalonia and Uno as detected-not-taught (D5).
- `.NET 10` primary, `11` supported, `8/9` flagged as out of support (D2). Note the CLAUDE.md conflict as Q2, do not edit the Version policy.
- Design facts cite `design/ui-ux-pro-max` with `--stack winui` (and `--stack wpf` for the WPF lane).

Traps:
- Re-check the §4.6 template items (`TargetPlatformMinVersion` default, whether `winui-mvvm` wires `Microsoft.Extensions.Hosting`) before writing them.
- `winapp` CLI is a public preview (0.8.0): every `winapp` recipe has a `dotnet` / Visual Studio fallback (D10).
- Experimental-channel controls (`TableView`, `Chart`) never appear in a production recipe.

Gate: none. Documents only (D11).
Commit: `feat(desktop-windows): foundations (012 W1)`.
Close out per the plan's "Close-out — every task" before you stop.
````

### W2 — Windows windows and navigation, activation and notifications, platform integration, forms (general-purpose, docs)

````
Depends on: W1
Agent: general-purpose · Stack: docs

Task W2 of docs/plans/012-desktop-plugins.md: write `windows-and-navigation`, `activation-and-notifications`, `platform-integration` (with `references/windows-ai.md`) and `forms` for Windows.

Deliverable: the four `desktop/windows/skills/<folder>/SKILL.md` and `platform-integration/references/windows-ai.md` exist; the Windows checklist has rows in F, G and J.

Read, in this order:
1. CLAUDE.md.
2. The plan: §4.2, §4.6, §5, §6.3, §8.2–§8.3, §10, and "Close-out — every task".
3. `docs/research/012-desktop-plugins/windows.md` §3 and §5.
4. W1's `desktop/windows/skills/basics/SKILL.md` for routing names; the Windows checklist as W1 left it.

Traps:
- Single instancing uses `AppInstance.FindOrRegisterForKey` / `RedirectActivationToAsync`, never a mutex. Pickers are the `Microsoft.Windows.Storage.Pickers` ones, constructed with `AppWindow.Id`.
- Activation arguments (protocol, file, notification) are untrusted input, validated before routing (§5).
- Re-check the §4.6 startup-task, background-task and share-target items, and the Phi Silica → "Aion Instruct" change, before writing them.

Gate: none. Documents only (D11).
Commit: `feat(desktop-windows): windows, activation, platform integration, forms (012 W2)`.
Close out per the plan's "Close-out — every task" before you stop.
````

### W3 — Windows networking, storage, interop, WPF and WinForms (general-purpose, docs)

````
Depends on: W2
Agent: general-purpose · Stack: docs

Task W3 of docs/plans/012-desktop-plugins.md: write `networking`, `offline-and-storage`, `interop`, `wpf` and `winforms` for Windows.

Deliverable: the five `desktop/windows/skills/<folder>/SKILL.md` exist; the Windows checklist has rows in D (`[WPF]`, `[WinForms]`), H, I and X.

Read, in this order:
1. CLAUDE.md.
2. The plan: §4.2, §4.6, §5, §6.3, §8.2–§8.3, §10, and "Close-out — every task".
3. `docs/research/012-desktop-plugins/windows.md` §1 (WPF, WinForms), §3, §10.
4. The headings of the be-dotnet HTTP-client skill under `backend/dotnet/skills/` (find it with `ls`) for the typed-client voice; the Windows checklist as W2 left it.

Traps:
- `wpf` and `winforms` keep the lane itself; WinUI is a `migration` run, never a side effect. The WPF Fluent theme is still "in progress": say so with its version.
- `ApplicationData` exists only with package identity. Re-check `PasswordVault` for unpackaged apps (§4.6).
- CsWinRT 3.0 is a preview: not adopted (§4.2).

Gate: none. Documents only (D11).
Commit: `feat(desktop-windows): networking, storage, interop, WPF, WinForms (012 W3)`.
Close out per the plan's "Close-out — every task" before you stop.
````

### W4 — the C++/WinRT lane (general-purpose, docs)

````
Depends on: W3
Agent: general-purpose · Stack: docs

Task W4 of docs/plans/012-desktop-plugins.md: write the C++/WinRT lane skill and settle its test and coverage tooling.

Deliverable: `desktop/windows/skills/cpp-winrt/SKILL.md` and its `references/` exist. The Windows checklist has `[C++]` rows in X, plus one in each of B, C, N and S where the C++ rule differs. A dated `D<n>` records the C++ unit-test framework and coverage tool. The §5 C++/WinRT bullet in CLAUDE.md matches what you verified.

Read, in this order:
1. CLAUDE.md (§ Desktop code rules, C++/WinRT bullet).
2. The plan: §4.2, §5, §6.3 (`cpp-winrt` row), §7.2, §8.2, D8, §10, and "Close-out — every task".
3. `docs/research/012-desktop-plugins/windows.md` §1 (Other stacks) and §2 (`winapp` row).
4. The Windows checklist as W3 left it.

Research first (learn.microsoft.com, github.com/microsoft): C++/WinRT ownership and `com_ptr`, coroutines and `get_strong` / `get_weak`, resuming on the dispatcher queue (`wil::resume_foreground`), error handling with `hresult_error`, IDL / MIDL for XAML types, WIL; unit testing a C++/WinRT WinUI app (Microsoft C++ Unit Test Framework vs GoogleTest) and branch / line coverage (Visual Studio coverage, OpenCppCoverage).

Traps:
- Every C++ rule in §5 is verified before you write it. Where a fact differs, rewrite the CLAUDE.md bullet in place and add a dated `D<n>`.
- Where branch coverage is not reported, the floor is 80% of lines (CLAUDE.md § Test code rules).
- Rewrite W6's prompt block for the C++ facts it must carry: the `cppwinrt.md` rule file and the §7.2 C++ commands.

Gate: none. Documents only (D11).
Commit: `feat(desktop-windows): C++/WinRT lane (012 W4)`.
Close out per the plan's "Close-out — every task" before you stop.
````

### W5 — Windows quality layers, test ids and unit tests (general-purpose, docs)

````
Depends on: W4
Agent: general-purpose · Stack: docs

Task W5 of docs/plans/012-desktop-plugins.md: write `languages`, `accessibility`, `performance`, `error-handling`, `test-ids` and `unit-testing` for Windows.

Deliverable: the six `desktop/windows/skills/<folder>/SKILL.md` exist; the Windows checklist has rows in M, N, O, P, R and S; `test-ids` states the §8.5 `AutomationId` mapping, verified against the WinCore and FlaUI docs.

Read, in this order:
1. CLAUDE.md (§ Test code rules too).
2. The plan: §4.3–§4.4, §5, §6.4, §8.2–§8.3, §8.5, D8, §10, and "Close-out — every task".
3. `docs/research/012-desktop-plugins/windows.md` §7–§9; `cross-platform-and-qa.md` B.2.
4. Siblings: `mobile/android/skills/{languages,accessibility,performance,error-handling,test-ids,unit-testing}/SKILL.md`; the headings of `frontend/react/skills/error-handling/SKILL.md`; W4's C++ testing decision in `## Decisions`.
5. The Windows checklist as W4 left it.

Traps:
- `AutomationId` is unique among siblings only: containers carry their own id and rows are located inside them (§8.5).
- `unit-testing` per D8: NUnit by default, the WinUI Unit Test App only for code that needs XAML types; the C++ lane links to `cpp-winrt`.
- E1 builds on your `test-ids` contract: state it as one table (element kind → property → what WinCore / FlaUI read).

Gate: none. Documents only (D11).
Commit: `feat(desktop-windows): quality layers, test ids, unit tests (012 W5)`.
Close out per the plan's "Close-out — every task" before you stop.
````

### W6 — Windows migration, review, audit, rules, agent and commands (general-purpose, docs)

````
Depends on: W5, S1, S2, S3
Agent: general-purpose · Stack: docs

Task W6 of docs/plans/012-desktop-plugins.md: finish `desktop-windows`: migration, code-review, standards-audit, the rules skill, the agent and the two commands.

Deliverable: `desktop/windows/skills/{migration,code-review,standards-audit,rules}/` exist (rules with the twelve §8.6 files); `desktop/windows/agents/desktop-windows.md` ≤ 14,000 characters; `desktop/windows/commands/{desktop-windows,audit}.md` exist; the checklist ends with a section index.

Read, in this order:
1. CLAUDE.md.
2. The plan: §5, §6.3, §7, §8 (all), D8, D10, §10, W4's As built note, and "Close-out — every task".
3. `.skill-template/agent.md`; `mobile/android/agents/mobile-android.md`; `mobile/android/commands/*`.
4. `mobile/android/skills/{migration,code-review,standards-audit}/SKILL.md` and `mobile/ios/skills/rules/` (procedure to copy).
5. `docs/research/012-desktop-plugins/windows.md` §10–§11.
6. The `name:` of every `desktop/windows/skills/*/SKILL.md`, `desktop/_shared/*/SKILL.md` and `auth/auth0-windows/SKILL.md`.

Traps:
- One agent, four lanes: detection (basics) picks the lane, and the steps table loads the lane skill. Keep it within 14,000 characters by routing, not teaching.
- The agent carries the template's `Gate:` line verbatim and names the three `qa-desktop-<lang>` agents (they land in E1–E3).
- `migration` covers .NET 8/9 → 10 (out of support since 2026-11-10) and Windows App SDK 1.x → 2.x.

Gate: none. Documents only (D11).
Commit: `feat(desktop-windows): migration, review, audit, rules, agent, commands (012 W6)`.
Close out per the plan's "Close-out — every task" before you stop.
````

### E1 — QA desktop: shared rules and the TypeScript lane (general-purpose, qa)

````
Depends on: M4, W5
Agent: general-purpose · Stack: qa

Task E1 of docs/plans/012-desktop-plugins.md: write the shared desktop-testing skill and the TypeScript desktop E2E lane.

Deliverable: `qa/_shared/desktop-testing/SKILL.md` exists. In `qa/typescript/`: `skills/{desktop-project-setup,desktop-screen-explorer,desktop-window-objects}/SKILL.md`, `skills/rules/desktop-tests.md` (listed in that rules skill's table), `agents/qa-desktop-typescript.md` and `commands/desktop.md` exist. The Mac2 4.6.1 and WinCore 3.3.2 Appium peer ranges are confirmed against Appium 3.8.0.

Read, in this order:
1. CLAUDE.md (§ Test code rules).
2. The plan: §4.4–§4.5, §6.6, §8.5, D9, §10, and "Close-out — every task".
3. `docs/research/012-desktop-plugins/cross-platform-and-qa.md` Part B.
4. Patterns: `qa/typescript/agents/qa-mobile-typescript.md`, `qa/typescript/commands/mobile.md`, `qa/typescript/skills/{mobile-project-setup,mobile-screen-explorer,mobile-screen-objects}/SKILL.md`, `qa/typescript/skills/rules/{SKILL.md,mobile-tests.md}`.
5. The two dev `test-ids` skills: `desktop/macos/skills/test-ids/SKILL.md`, `desktop/windows/skills/test-ids/SKILL.md`.

Traps:
- Version pins follow §4.4–§4.5. Install drivers with an explicit `@version`. If a peer range excludes 3.8.0, record a dated `D<n>` and do not bump the library pin (Q3).
- Never the legacy Windows driver or WinAppDriver (D9). Electron and Tauri are out of scope (Q1).
- `missing-testids.md` routes to `desktop-macos` / `desktop-windows`.
- Rewrite E2's and E3's prompt blocks for anything they must mirror: shared-skill section names and the explorer's report shape.

Gate: none. Documents only (D11). Do not run `tools/qa-version-check.py`; G1 runs it.
Commit: `feat(qa): desktop E2E shared rules and TypeScript lane (012 E1)`.
Close out per the plan's "Close-out — every task" before you stop.
````

### E2 — QA desktop: the Java lane (general-purpose, qa)

````
Depends on: E1
Agent: general-purpose · Stack: qa

Task E2 of docs/plans/012-desktop-plugins.md: write the Java desktop E2E lane.

Deliverable: in `qa/java/`: `skills/{desktop-project-setup,desktop-screen-explorer,desktop-window-objects}/SKILL.md`, `skills/rules/desktop-tests.md` (listed in its rules skill), `agents/qa-desktop-java.md` and `commands/desktop.md` exist.

Read, in this order:
1. CLAUDE.md (§ Test code rules).
2. The plan: §4.4, §6.6, §8.5, D9, §10, E1's As built note, and "Close-out — every task".
3. `docs/research/012-desktop-plugins/cross-platform-and-qa.md` B.5–B.6.
4. `qa/_shared/desktop-testing/SKILL.md` and E1's three `qa/typescript/skills/desktop-*` skills: the pattern to mirror.
5. `qa/java/agents/qa-mobile-java.md`, `qa/java/commands/mobile.md`, `qa/java/skills/{mobile-project-setup,mobile-screen-objects}/SKILL.md`, `qa/java/skills/rules/{SKILL.md,mobile-tests.md}`.

Traps:
- `WindowsOptions` hard-sets `automationName` to `Windows`. For WinCore, override it or use `BaseOptions`.
- TestNG and `java-client` 11 at the library pins.
- E3 runs beside you in `qa/dotnet/`: touch only `qa/java/` and this plan's E2 blocks.

Gate: none. Documents only (D11).
Commit: `feat(qa-java): desktop E2E lane (012 E2)`.
Close out per the plan's "Close-out — every task" before you stop.
````

### E3 — QA desktop: the .NET lane (general-purpose, qa)

````
Depends on: E1
Agent: general-purpose · Stack: qa

Task E3 of docs/plans/012-desktop-plugins.md: write the .NET desktop E2E lane, including FlaUI.

Deliverable: in `qa/dotnet/`: `skills/{desktop-project-setup,desktop-screen-explorer,desktop-window-objects}/SKILL.md` (FlaUI 5.0.0 lane in setup and window objects), `skills/rules/desktop-tests.md` (listed in its rules skill), `agents/qa-desktop-dotnet.md` and `commands/desktop.md` exist.

Read, in this order:
1. CLAUDE.md (§ Test code rules).
2. The plan: §4.4, §6.6, §8.5, D9, §10, E1's As built note, and "Close-out — every task".
3. `docs/research/012-desktop-plugins/cross-platform-and-qa.md` B.1, B.5–B.6.
4. `qa/_shared/desktop-testing/SKILL.md` and E1's three `qa/typescript/skills/desktop-*` skills.
5. `qa/dotnet/agents/qa-mobile-dotnet.md`, `qa/dotnet/commands/mobile.md`, `qa/dotnet/skills/{mobile-project-setup,mobile-screen-objects}/SKILL.md`, `qa/dotnet/skills/rules/{SKILL.md,mobile-tests.md}`.

Research first: FlaUI 5.0.0 with UIA3 against WinUI and WPF; Playwright .NET `ConnectOverCDPAsync` for WebView2 (at the library's 1.63 pin).

Traps:
- NUnit + `Appium.WebDriver` 9 is the default; FlaUI is the Windows-only alternative, chosen per suite, never mixed in one suite.
- E2 runs beside you in `qa/java/`: touch only `qa/dotnet/` and this plan's E3 blocks.

Gate: none. Documents only (D11).
Commit: `feat(qa-dotnet): desktop E2E lane with FlaUI (012 E3)`.
Close out per the plan's "Close-out — every task" before you stop.
````

### I1 — marketplace, surface check, planning lane and QA wiring (general-purpose, docs)

````
Depends on: M5, W6, E2, E3, S1, S2, S3
Agent: general-purpose · Stack: docs

Task I1 of docs/plans/012-desktop-plugins.md: wire both desktop plugins and the QA desktop lane into the marketplace, the surface check and the planning lane.

Deliverable: `.claude-plugin/marketplace.json` lists `desktop-macos` and `desktop-windows`, and the three QA entries list their desktop skills, agent and command, with every path existing on disk; `tools/plugin-surface-check.py` has `desktop` in `STACK_CATEGORIES`; the plan format, delivery plan and solution planner accept a `desktop` task routed to the two agents.

Read, in this order:
1. CLAUDE.md (§ Planning).
2. The plan: §2, §9, D5, D13, and "Close-out — every task".
3. The `mobile-ios` entry in `.claude-plugin/marketplace.json` (the shape) and the three `qa-*` entries.
4. `engineering-practices/writing-plans/references/plan-format.md:119`; `backend/_shared/delivery-plan/SKILL.md:44,128,345`; `grep -n mobile backend/_shared/agents/solution-planner.md`.
5. `qa/*/skills/device-cloud/SKILL.md` (where the one desktop line goes); `grep -rn "mobile-ios" qa/_shared/security-testing` (the peer lines); `mobile/android/skills/kotlin-multiplatform/SKILL.md`.

Do:
- Marketplace per §9: build every `skills` array from `ls`, never from memory. Then assert every path exists with a short Python one-liner (reading files is not a gate).
- `STACK_CATEGORIES` gains `"desktop"`.
- The planning lane and the CLAUDE.md § Planning one-stack bullet per §9.
- QA lines per §9; one Compose Multiplatform Desktop mention line in the KMP skill (D5).

Traps:
- `plugin-surface-check.py` rule 5 forbids registering a folder from two categories: `desktop/_shared/*` goes only into the two desktop plugins, `qa/_shared/desktop-testing` only into the three QA plugins.
- Do not run `plugin-surface-check.py`, `token-audit.py` or `qa-version-check.py`; G1 runs them.

Gate: none. Wiring only; G1 runs every check (D11).
Commit: `feat: wire desktop-macos, desktop-windows and the QA desktop lane (012 I1)`.
Close out per the plan's "Close-out — every task" before you stop.
````

### G1 — documentation, the gate and filing the plan (general-purpose, docs)

````
Depends on: I1
Agent: general-purpose · Stack: docs

Task G1 of docs/plans/012-desktop-plugins.md: document the desktop domain, run the plan's whole gate, fix what it finds, and file the plan.

Deliverable: `CLAUDE.md`, `docs/skills-catalog.md` and `README.md` describe the desktop domain and the QA desktop lane; §11's five checks pass; this plan is in `docs/plans/implemented/`.

Read, in this order:
1. CLAUDE.md (§ Stack defaults, § Version policy, § Repository map).
2. The plan: header, §2, §4.1–§4.2, §9, §11, every task's As built note, `## Decisions` (dated ones too), and "Close-out — every task".
3. `docs/skills-catalog.md`: the scope paragraph, the slash-command surface table and `## Mobile dev catalog` (the section pattern). `README.md`: the layout line and the status table.

Do:
- Documentation per §9. Recompute the command count from the marketplace; never guess it.
- Run §11 steps 1–5 in order. Fix by the fix loop: the whole set once; each failure fixed and rerun with the narrowest command; the whole set once more. A failure may belong to any task above.
- Justify every `ALLOW` addition in your As built note.
- Rewrite `**Status:**` one last time per the task block, delete this prompt, and `git mv` the plan to `docs/plans/implemented/012-desktop-plugins.md` with its row in that folder's README if one exists.

Traps:
- `token-audit.py` exits non-zero on violations that existed before this plan; read the grep (§11 step 4), not the exit code.
- `desktop/` and the two auth folders leave CLAUDE.md's under-construction line only after the checks pass.
- After filing, tell the user the remaining steps: the global `~/.claude/CLAUDE.md` rule-1 edit (D13), and Q1–Q3.

Gate (this is the last task, so it runs the whole set once more across the plan, in run order): §11 steps 1–5.
Commit: `docs: desktop domain in CLAUDE.md, catalog and README; plan 012 gate (012 G1)`.
Close out per the plan's "Close-out — every task" before you stop.
````
