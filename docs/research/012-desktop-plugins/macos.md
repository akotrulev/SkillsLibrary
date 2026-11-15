# Native macOS apps — research for the `desktop-macos` plugin

**Date:** 2026-11-15 · **Scope:** what a coding standard, a skill set and a dev agent for native Mac apps should teach today, verified on the web on this date. Feeds plan 012 (desktop plugins). Facts already pinned for the iOS sibling (Swift 6.4 language features, Swift Testing default, MetricKit Swift API, TCA/GRDB lanes, CocoaPods trunk read-only) are in [`002-mobile-plugins.md` §4.2](../../plans/implemented/002-mobile-plugins.md) and are repeated here only where macOS differs. Every row carries its source; claims the sources did not settle are in the closing **Not verified** list.

## Overview

**macOS 27 Golden Gate shipped 2026-09-14 with Xcode 27 / Swift 6.4 / macOS 27 SDK, and it is the first Apple-silicon-only macOS.** macOS 26 Tahoe is the last release for Intel Macs (security updates ~3 years), macOS 27 is the last with full Rosetta, and **Intel software stops running on macOS 28** (legacy games excepted). Xcode 27 itself runs only on Apple silicon, raised the macOS deployment floor to **12**, and stops building Universal by default once a target's deployment target is 27. Linking the macOS 27 SDK forces Liquid Glass (the compatibility key is ignored), hides most menu-item icons, and deprecates `FileDocument` in favour of the new `ReadableDocument` / `WritableDocument` / `Document` protocols. **Mac App Store uploads have no published SDK deadline** — unlike iOS (April 2027) — but Developer ID distribution has a hard date: **the original Developer ID Sub-CA expires 2027-02-01**. Since 2026-11-06 Macs with a touch display ship, and the HIG gained touch-on-Mac guidance on 2026-10-28.

---

## 1. Toolchain lanes

### 1.1 Releases

| Fact | Value | Source |
|---|---|---|
| macOS 27 name / GA | **macOS 27 Golden Gate**, public 2026-09-14 (27.0.1 on 2026-09-28) | [MacRumors](https://www.macrumors.com/2026/09/10/macos-27-golden-gate-release-date/) (2026-09-10); [release notes](https://developer.apple.com/documentation/macos-release-notes/macos-27-release-notes); [blakecrosley.com](https://blakecrosley.com/blog/macos-27-golden-gate-release) (secondary) |
| macOS 27 hardware | M1 and later + MacBook Neo (A18 Pro); no Intel | MacRumors (above) |
| Xcode 27 | GA 2026-09-14 (27A266a); 27.1 on 2026-10-15; **27.2 current**; 27.3 beta | [Xcode 27 release notes](https://developer.apple.com/documentation/xcode-release-notes/xcode-27-release-notes); [Xcode support](https://developer.apple.com/support/xcode/) |
| Xcode 27 host | macOS Tahoe 26.6+, **Apple silicon only** ("Xcode 27 will only install and run on Apple silicon Macs") | Xcode 27 release notes, "Intel Deprecation" |
| Swift | 6.4 (Xcode 27.x); 6.3 (Xcode 26.4–26.6); 6.2.x (Xcode 26.0–26.3). Language modes 6, 5, 4.2, 4 | [Xcode support](https://developer.apple.com/support/xcode/) |
| macOS deployment range | **Xcode 27: macOS 12–27**; Xcode 26.x: 11–26.x (floor rose 11 → 12) | Xcode support |
| Xcode 27.2 SDK bug | macOS SDK wrongly accepts 27.1 as a deployment target — don't use it | [Xcode 27.2 release notes](https://developer.apple.com/documentation/xcode-release-notes/xcode-27_2-release-notes) |
| C++ stdlib floor | libc++ minimum deployment target on macOS raised to 11.0 | Xcode 27 release notes, "C++ Standard Library" |
| Linker | ld64 removed (`-ld_classic` ignored with a warning) | [blakecrosley.com](https://blakecrosley.com/blog/xcode-27-release) (secondary, author's repro) |
| Project format | Xcode 27.2 adds a JSON project format `.xcproj` ("merge-friendly, and easier for coding agents to edit"), opt-in in the File inspector, opens in earlier 27.x | Xcode 27.2 release notes |

### 1.2 Recommended lanes (for the coding standard)

| Item | Primary | Supported | Floor / rule |
|---|---|---|---|
| Xcode / Swift / SDK | **Xcode 27.x, Swift 6.4, macOS 27 SDK** | Xcode 26.x, Swift 6.2–6.3, macOS 26 SDK | Xcode 27 needs an Apple-silicon host on Tahoe 26.6+ |
| Deployment target — new app | **macOS 15** (UtilityWindow, `defaultWindowPlacement`, `windowLevel`, `restorationBehavior`, `defaultLaunchBehavior`, `WindowDragGesture`) | **macOS 14** (`@Observable`, SwiftData, `inspector`, `onKeyPress`, `openSettings`) — the lane aligned with the iOS plugin's iOS 17 primary for multiplatform code | — |
| Deployment target — existing app | keep what it has | macOS 13 (`NavigationSplitView`, `Window`, `MenuBarExtra`, `SMAppService`, `windowResizability`) | **macOS 12 is the Xcode 27 hard floor**; below 13 is the AppKit lane only, flagged. Never raise as a side effect |
| Architectures | arm64 only when deployment target ≥ 27 (`ARCHS_STANDARD` = arm64) | **Universal (arm64 + x86_64) while deployment target < 27 and Intel Macs on Tahoe are in scope** | A 27 target that must still ship x86_64 adds it to `ARCHS` explicitly — nothing warns |
| Language mode | Swift 6 + Approachable Concurrency for new modules | Swift 5-mode modules, migrated one at a time | Same as iOS (002 §4.2) |

The deployment-target choice is a recommendation derived from the API availabilities in §2; it is not an Apple rule.

### 1.3 Intel end of life

| Fact | Source |
|---|---|
| macOS 26 Tahoe is the last macOS for Intel Macs; those Macs get security updates for three years | [MacRumors](https://www.macrumors.com/2026/09/10/macos-27-golden-gate-release-date/); [heise](https://heise.de/-10438678) |
| "Build targets with a min deployment target set to macOS 27.0 or DriverKit 27.0 will not build Universal by default. The `ARCHS_STANDARD` build setting will no longer include x86_64 when `MACOSX_DEPLOYMENT_TARGET` … >= 27.0. The x86_64 architecture can be added to the `ARCHS` build setting if this is needed." | Xcode 27 release notes, "Intel Deprecation" |
| "The macOS 27 SDK supports back deploying Universal (Intel and Apple Silicon) apps to macOS 12 and later. Intel development is still possible with macOS versions that support Rosetta like macOS 27." | same |
| "All Intel-based software will no longer be compatible with macOS 28.0, excluding legacy games." Intel plug-ins (Audio Units/VST, printer PDEs, colour pickers, Quick Look/Spotlight plug-ins) may fail silently | [macOS 27 release notes](https://developer.apple.com/documentation/macos-release-notes/macos-27-release-notes), "Rosetta" |
| Rosetta is not restored after upgrading to 27; apps the user set to "Open using Rosetta" launch natively | same |
| **Installer packages with no `hostArchitecture` now default to arm64** — audit pre/post-install scripts and installer plug-ins | same |
| Get Info shows a treatment on Intel apps that won't run on macOS 28 | same, "Deprecation Information" |

### 1.4 App Store and upload requirements for macOS

| Requirement | Source |
|---|---|
| **No published macOS SDK minimum for uploads.** The 2026-04-28 "built with Xcode 26" rule names iOS, iPadOS, tvOS, visionOS, watchOS only; no macOS deployment-target floor either | [Upcoming requirements](https://developer.apple.com/news/upcoming-requirements/) |
| Since 2025-02-18: macOS apps uploaded to App Store Connect / TestFlight must not carry `com.apple.quarantine` on any file (`xattr -dr com.apple.quarantine App.app`) | same |
| Since 2023-11-01: the notary service rejects `altool` and Xcode ≤ 13 — `notarytool` only | same; [Notarizing macOS software](https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution) |
| Mac App Store guideline 2.4.5: sandboxed; packaged with Xcode, no third-party installers; no auto-launch / login code without consent; no downloading code; no root escalation; no licence keys or own copy protection; **updates only through the Mac App Store** | [App Review Guidelines 2.4.5](https://developer.apple.com/app-store/review/guidelines/#2.4.5) |
| Hardware-Checked Pointer Arithmetic (`arm64e.x1`) apps can't upload from Tahoe 26.6 with automatic signing — use macOS 27 + Xcode 27 or manual signing | Xcode 27 release notes, "Enhanced Security" |

---

## 2. UI

### 2.1 Scenes (SwiftUI) — availability on macOS

| API | macOS | Notes | Source |
|---|---|---|---|
| `WindowGroup`, `Settings`, `DocumentGroup`, `CommandGroup`, `.keyboardShortcut`, `.onOpenURL`, `.handlesExternalEvents` | 11 | `Settings` gives the app-menu "Settings…" item and ⌘, | [Settings](https://developer.apple.com/documentation/swiftui/settings); [DocumentGroup](https://developer.apple.com/documentation/swiftui/documentgroup) |
| `Table` | 12 | multi-column, sortable, selectable — the Mac list type | [Table](https://developer.apple.com/documentation/swiftui/table) |
| `Window`, `MenuBarExtra`, `NavigationSplitView`, `.windowResizability`, `focusedSceneObject` | 13 | `MenuBarExtra` `.menu` vs `.window` style; `isInserted:` binding; menu-bar-only app sets `LSUIElement` and is terminated if the user removes the extra | [MenuBarExtra](https://developer.apple.com/documentation/swiftui/menubarextra); [Window](https://developer.apple.com/documentation/swiftui/window) |
| `.inspector`, `openSettings`, `onKeyPress`, `focusable(interactions:)`, Observation, SwiftData | 14 | trailing-column inspectors restore their presentation state; `InspectorCommands` adds the shortcut | [inspector](https://developer.apple.com/documentation/swiftui/view/inspector(ispresented:content:)); [openSettings](https://developer.apple.com/documentation/swiftui/environmentvalues/opensettings) |
| `UtilityWindow` | 15 | floating, hides when app inactive, receives `FocusedValues` of the focused main scene, Escape dismisses, auto-adds a View-menu toggle | [UtilityWindow](https://developer.apple.com/documentation/swiftui/utilitywindow) |
| `.defaultWindowPlacement`, `.windowLevel`, `.restorationBehavior`, `.defaultLaunchBehavior`, `.windowManagerRole`, `.windowIdealSize`, `.windowToolbarFullScreenVisibility`, `WindowDragGesture` | 15 | restoration restores last size/position over the default placement | [defaultWindowPlacement](https://developer.apple.com/documentation/swiftui/scene/defaultwindowplacement(_:)); [restorationBehavior](https://developer.apple.com/documentation/swiftui/scene/restorationbehavior(_:)) |
| `.glassEffect`, `.windowResizeAnchor`, `NSHostingSceneRepresentation` | 26 | | Apple docs (`/documentation/swiftui/...`) |
| `ReadableDocument`, `WritableDocument`, `Document`, `TabsPickerStyle` | 27 | see 2.3 | macOS 27 release notes, "SwiftUI" |
| `pushWindow` | **not on macOS** (visionOS only) | use `openWindow` | [pushWindow](https://developer.apple.com/documentation/swiftui/environmentvalues/pushwindow) |

### 2.2 Toolbars, menus, keyboard (WWDC26 / 27 SDK)

| Fact | Source |
|---|---|
| Toolbar overflow and priority: `ToolbarItemGroup { … }.visibilityPriority(.high)`, `ToolbarOverflowMenu`, pinned trailing placement | [WWDC26 269 What's new in SwiftUI](https://developer.apple.com/videos/play/wwdc2026/269/) |
| **Menus linked on the 27 SDK hide symbol images by default** (menu bar and context menus); show one with `.labelStyle(.titleAndIcon)` (SwiftUI) or `NSMenuItem.preferredImageVisibility` (AppKit); system keeps icons for Settings, Share, Print. Linked on 27 SDK, non-symbol images are hidden too | macOS 27 release notes, "SwiftUI", "AppKit" |
| `LabeledContent` inside a `Menu` maps to the menu item's subtitle (27 SDK) | macOS 27 release notes, "SwiftUI" |
| `Picker`/`Menu` no longer backed by `NSPopUpButton`; `Slider` no longer `NSSlider` | same |
| `.squareBorder` / `.roundedBorder` text-field styles soft-deprecated → `.bordered` + `textInputBorderShape(_:)` | same |
| `controlSize`, `buttonSizing`, `menuIndicatorVisibility`, `ButtonBorderShape` reset inside sheets/popovers (27 SDK) | same |
| `@Environment(\.appearsActive)` to dim custom chrome in inactive windows | WWDC26 269 |
| `NSToolbarItemGroup.role` / `NSSegmentedControl.role = .tabs`, SwiftUI `TabsPickerStyle` — VoiceOver reads "tabs"; distinct look from value pickers | macOS 27 release notes, "AppKit", "SwiftUI" |

### 2.3 Documents (27 SDK)

| Fact | Source |
|---|---|
| New `ReadableDocument` / `WritableDocument` (async read/write, progress, direct URL access) and `Document` (both); **`FileDocument` deprecated; `ReferenceFileDocument` "remains available"** but `Document` is preferred | macOS 27 release notes, "SwiftUI" |
| `DocumentReader.read` / `DocumentWriter.write` are `@concurrent` — conformers using `nonisolated` must switch, or under default MainActor isolation they run on the main actor | same |
| `makeDocument` closures are `@MainActor`; `URLDocumentConfiguration` is `@MainActor @Observable`, no longer `Sendable` | same |
| `FileWrapperDocumentWriter.makeFileWrapper` gets `previous:` — mutate it to write only changed package children (source break for existing call sites) | same |
| `\.newDocument` accepts an in-memory document → "New from Template"; `DocumentGroupLaunchScene` with `NewDocumentButton(source:)` | same; WWDC26 269 |
| DocumentGroup gives ⌘N, ⌘O, edited indicator, autosave for free | WWDC26 269 |

### 2.4 Liquid Glass on macOS

| Fact | Source |
|---|---|
| `UIDesignRequiresCompatibility` (also honoured on macOS 26): "The system ignores this key when you build for … Mac Catalyst 27 or later, macOS 27 or later" — **linking the macOS 27 SDK forces the new design** | [UIDesignRequiresCompatibility](https://developer.apple.com/documentation/bundleresources/information-property-list/uidesignrequirescompatibility) |
| macOS 27 automatic changes: hard scroll-edge effect under free-floating title text; sidebars extend to window edges, semibold selection; bordered toolbar items over the sidebar adopt glass | [WWDC26 289 Modernize your AppKit app](https://developer.apple.com/videos/play/wwdc2026/289/) |
| Interactive glass (bounce on click) for controls / glass containers — "A little goes a long way"; SwiftUI interactive glass "optimized to work great with the mouse pointer" | WWDC26 289; WWDC26 269 |
| Concentric corners: `NSView.cornerConfiguration` → `.containerConcentric(minimum)` (AppKit, macOS 27); SwiftUI `concentricCornerRadii` on `GeometryProxy` | WWDC26 289; macOS 27 release notes |
| `NSTitlebarAccessoryViewController` may draw outside its bounds when linked on 27 (glass shadows) | macOS 27 release notes, "AppKit" |

### 2.5 AppKit lane (brownfield)

| Fact | Source |
|---|---|
| Apple's stance: "There are no expectations that an app needs to be entirely SwiftUI"; adopt `@Observable` first, SwiftUI for new or rewritten components | [WWDC26 272 Use SwiftUI with AppKit and UIKit](https://developer.apple.com/videos/play/wwdc2026/272/) |
| **AppKit Observation tracking**: reads of `@Observable` properties in `draw(_:)`, `updateConstraints()`, `layout()`, `updateLayer()` (and `NSViewController` equivalents) are tracked — no manual `needsDisplay`. On by default from the 2026 releases; back-deploy to **macOS 15** with `NSObservationTrackingEnabled` in Info.plist | same |
| Hosting: `NSHostingView` / `NSHostingController`; `NSViewRepresentable`; `NSGestureRecognizerRepresentable`; **`NSHostingMenu`** (SwiftUI-built `NSMenu`, macOS 14.4); **`NSHostingSceneRepresentation`** (add SwiftUI scenes — e.g. `Settings` — from an AppKit app delegate, macOS 26) | WWDC26 272; [NSHostingMenu](https://developer.apple.com/documentation/swiftui/nshostingmenu) |
| Input: prefer gesture recognizers, control events (`addTarget(_:action:for: .trackingEndedOutside)`), view-based selection/menu/drag APIs over `mouseDown:` and tracking loops; new `NSTextSelectionManager` (27) gives text selection to any view | WWDC26 289; macOS 27 release notes |
| 27 gesture changes: only the initially hit-tested hierarchy activates recognizers (`exclusiveGestureBehavior`, `NSViewGestureRecognizerIsExclusive` opt-out); stuck gestures auto-cancel; custom `NSGestureRecognizer` must override `locationInView:` (base returns zero) | macOS 27 release notes, "NSGestureRecognizer", "AppKit" |
| New AppKit 27: `NSRefreshController` (pull-to-refresh on `NSScrollView`), `.disableScreenCornerInteractions` presentation option | macOS 27 release notes |
| Keyboard loop: `window.autorecalculatesKeyViewLoop = true` | WWDC26 289 |
| Graceful quit: set `preventsApplicationTerminationWhenModal = false` on non-critical sheets | WWDC26 289 |
| State restoration (AppKit): window identifier + `isRestorable` + `restorationClass`; encode in `encodeRestorableState(with:)` and call `invalidateRestorableState()`; never encode document/database data; always call the restore completion handler | WWDC26 289 |

### 2.6 Mac Catalyst

| Fact | Source |
|---|---|
| Still shipping and maintained: 27 makes Catalyst apps behave like AppKit apps when activated with no windows; fixes for sidebar toolbar buttons, `UIStepper` | macOS 27 release notes, "Mac Catalyst" |
| Xcode 27.2 known issue: iOS 27.1-only APIs fail to compile for Catalyst | Xcode 27.2 release notes |
| Community view: native SwiftUI (+AppKit) for a Mac-first or new app; Catalyst only to bring an existing UIKit iPad app across, with extra work for Mac chrome; Liquid-Glass-era Catalyst still reported as glitchy | [Apple Forums "State of Mac Catalyst in 2026"](https://developer.apple.com/forums/thread/811728); [mjtsai](https://mjtsai.com/blog/?p=51309) (2026-03-19); [pilky.me](https://pilky.me/catalyst-vs-swiftui) |
| **Recommendation for the plugin:** not a primary lane. A `migration` recipe (Catalyst → native SwiftUI target) and a code-review rule that a Catalyst app still meets the Mac HIG checklist. | derived |

### 2.7 macOS HIG essentials

| Rule | Source |
|---|---|
| Menu order: App, File, Edit, Format, View, app-specific, Window, Help; support the system menus and their order | [HIG The menu bar](https://developer.apple.com/design/human-interface-guidelines/the-menu-bar) |
| "Always show the same set of menu items … disable the action instead of hiding it" | same |
| Support standard shortcuts for standard items; custom shortcuts only when necessary; ellipsis when more input is needed (`Open…`) | same |
| App menu: About (own group), Settings…, Services, Hide/Hide Others/Show All, Quit; File: New/Open/Open Recent/Close/Save/Duplicate (prefer Duplicate over Save As)/Rename…/Move To…/Export As…/Revert To/Print… | same |
| Design for large displays (fewer nesting levels, less modality, comfortable density); resizable, movable windows and full screen; every command in the menu bar; keyboard shortcuts for keyboard-only work; precise pointer input; customisable toolbars | [HIG Designing for macOS](https://developer.apple.com/design/human-interface-guidelines/designing-for-macos) (updated 2026-10-28) |
| **Touch on Mac (new 2026-10-28):** touch is for "brief, intentional interactions"; larger tap targets / controls that expand on touch while keeping density the same; hover-only controls need a tap-to-reveal path and a context-menu path; keep selection when revealing | same; [HIG Pointing devices](https://developer.apple.com/design/human-interface-guidelines/pointing-devices) (2026-10-28) |
| Touch-screen MacBook Pro announced 2026-10-28, shipping 2026-11-06 | [mixed-news.com](https://mixed-news.com/en/?p=38602); [The National](https://www.thenationalnews.com/future/technology/2026/10/28/glowing-apple-logo-macbook-proled-xdr/) (secondary) |
| Windows: main / key / inactive states; don't build custom window frames or controls; avoid opening new windows by default but offer "open in new window"; say "window", never "scene", in UI | [HIG Windows](https://developer.apple.com/design/human-interface-guidelines/windows) |
| Control size: macOS default **28×28 pt**, minimum **20×20 pt**; text default **13 pt**, minimum **10 pt** (vs iOS 44/28 pt and 17/11 pt) | [HIG Accessibility](https://developer.apple.com/design/human-interface-guidelines/accessibility) |

---

## 3. Platform

### 3.1 Sandbox, hardened runtime, entitlements

| Fact | Source |
|---|---|
| App Sandbox: mandatory for the Mac App Store (2.4.5(i)); optional for Developer ID. Container in `~/Library/Containers`; since macOS 14 bound to the code signature — another app's container access prompts | [Accessing files from the macOS App Sandbox](https://developer.apple.com/documentation/security/accessing-files-from-the-macos-app-sandbox) |
| **macOS 27: access to other teams' app containers and app-group containers is denied by default (no prompt)**; XProtect may block access to data commonly targeted by malware; apps can no longer read the TCC database | macOS 27 release notes, "System Integrity Protection", "TCC" |
| User-selected files: `com.apple.security.files.user-selected.read-only/read-write`; open/save panels (`fileImporter`/`fileExporter`, `NSOpenPanel`/`NSSavePanel`) extend the sandbox; standard-folder entitlements (Music, Movies, Pictures, Downloads) | same |
| **Security-scoped bookmarks**: create with `.withSecurityScope` (+ `.securityScopeAllowOnlyReadAccess`); resolve; if stale, recreate and store; `startAccessingSecurityScopedResource()` … `stop…` in balanced pairs; plain bookmarks to pass access to an XPC service/launch agent; document-relative bookmarks for project files; `NSIsRelatedItemType` + `NSFilePresenter` for sidecar files | same |
| App-group containers: Mac App Store or notarized, and the group id in the profile or prefixed with the team id — otherwise the user is prompted | same |
| Full Disk Access: no entitlement or API — the user grants it in System Settings; code must handle denial | same |
| Hardened Runtime is required for notarization; plug-ins inherit host entitlements (`cs.allow-jit`, `cs.allow-unsigned-executable-memory`, `cs.disable-library-validation`) | [Notarizing macOS software](https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution) |
| Xcode 27 ships an `audit-xcode-security-settings` agent skill (Enhanced Security, entitlements) | Xcode 27 release notes, "Security" |

### 3.2 TCC permissions and the denied path

| Permission | How the app asks / checks | Denied path | Source |
|---|---|---|---|
| Camera / microphone | `AVCaptureDevice.requestAccess(for:)` + `NSCameraUsageDescription` / `NSMicrophoneUsageDescription` + sandbox `device.camera` / `device.audio-input` | working screen + "Open System Settings" | [requestAccess](https://developer.apple.com/documentation/avfoundation/avcapturedevice/requestaccess(for:completionhandler:)); [device.camera](https://developer.apple.com/documentation/bundleresources/entitlements/com.apple.security.device.camera) |
| Screen recording | prefer `SCContentSharingPicker` (macOS 14, per-capture consent); else `CGPreflightScreenCaptureAccess` / `CGRequestScreenCaptureAccess` (10.15). Sequoia re-prompts standing grants periodically (monthly) | picker or explained settings link | [SCContentSharingPicker](https://developer.apple.com/documentation/screencapturekit/sccontentsharingpicker); [TidBITS](https://tidbits.com/2024/08/19/apple-reduces-excessive-sequoia-permission-requests-shifts-to-monthly) |
| Accessibility (control other apps) | `AXIsProcessTrustedWithOptions` with the prompt option; user toggles in Settings | feature off, explained | Apple ApplicationServices docs |
| Input Monitoring | `CGRequestListenEventAccess` (10.15) | same | [CGRequestListenEventAccess](https://developer.apple.com/documentation/coregraphics/cgrequestlisteneventaccess()) |
| Desktop / Documents / Downloads / removable volumes | `NSDesktopFolderUsageDescription` etc. (10.15); in the sandbox prefer user-selected access | panel-based access | [NSDesktopFolderUsageDescription](https://developer.apple.com/documentation/bundleresources/information-property-list/nsdesktopfolderusagedescription) |
| Full Disk Access | none — deep-link to Settings | degrade, never crash | Accessing files from the macOS App Sandbox |
| Automation (Apple Events) | `NSAppleEventsUsageDescription` + `com.apple.security.automation.apple-events` | — | Apple docs (not re-fetched) |

### 3.3 Background work, helpers, IPC

| Fact | Source |
|---|---|
| **`SMAppService`** (macOS 13): `.mainApp` login item, `.loginItem(identifier:)` (helper in `Contents/Library/LoginItems`), `.agent(plistName:)`, `.daemon(plistName:)` — replaces `SMLoginItemSetEnabled` and hand-installed `~/Library/LaunchAgents` plists; `status` incl. `.requiresApproval`; `openSystemSettingsLoginItems()` | [SMAppService](https://developer.apple.com/documentation/servicemanagement/smappservice) |
| App Store 2.4.5(iii): no login/auto-launch code without consent | App Review Guidelines |
| macOS 27: `launchd` no longer loads plists that carry the quarantine attribute | macOS 27 release notes, "Launch Daemons and Agents" |
| XPC: Swift `XPCSession` / `XPCListener` (macOS 14) for XPC services and helper IPC | [XPCSession](https://developer.apple.com/documentation/xpc/xpcsession) |
| Neural Engine in the background needs `com.apple.developer.background-tasks.continued-processing.inference` (27) | macOS 27 release notes, "Core AI" |

### 3.4 System integration

| Fact | Source |
|---|---|
| App Intents expose actions to Spotlight, Siri, Shortcuts, widgets, controls on Mac; Tahoe brought the Controls API (Control Center / menu bar) to macOS | [Apple Newsroom (2025-06)](https://www.apple.com/newsroom/2025/06/macos-tahoe-26-makes-the-mac-more-capable-productive-and-intelligent-than-ever/) |
| WWDC26: entity schemas feed the Spotlight semantic index; View Annotations map views to entities; `AppIntentsTesting` validates adoption without UI automation | [WWDC26 macOS guide](https://developer.apple.com/wwdc26/guides/macos/) |
| 27 SDK: existing `@AppEntity(schema: .photos.asset)` may not compile (new properties); AppEntity size limit 10 MB | macOS 27 release notes, "App Intents" |
| Notifications: `UNUserNotificationCenter` (10.14) | [UNUserNotificationCenter](https://developer.apple.com/documentation/usernotifications/unusernotificationcenter) |
| URL schemes / external events: `CFBundleURLTypes`, `.onOpenURL`, `.handlesExternalEvents` (11) route URLs to the right window | [onOpenURL](https://developer.apple.com/documentation/swiftui/view/onopenurl(perform:)) |
| Pasteboard / drag & drop: `.copyable`, `.onPasteCommand`, `Transferable`; 27 SDK `List` accepts drops into reorderable content and per-row `dropDestination`; new `.reorderable()` / `.reorderContainer(for:)` | macOS 27 release notes; WWDC26 269 |
| AppKit drag: `NSFilePromiseReceiver.receivePromisedFiles…` now throws if called outside the drag-operation callbacks | macOS 27 release notes, "AppKit" |
| Services menu is part of the standard app menu | HIG The menu bar |
| App Attest now verifies Mac apps (27) | [blakecrosley.com](https://blakecrosley.com/blog/macos-27-golden-gate-release) (secondary) |

### 3.5 Privacy manifest on macOS

| Fact | Source |
|---|---|
| `PrivacyInfo.xcprivacy`: collected data types are required **on all platforms**; **required-reason API declarations are required on iOS, iPadOS, tvOS, visionOS, watchOS — not macOS** | [Privacy manifest files](https://developer.apple.com/documentation/bundleresources/privacy-manifest-files) |
| Third-party SDKs on Apple's list still need a signed manifest | same |

---

## 4. Distribution

### 4.1 Channels

| | Mac App Store | Developer ID (direct) |
|---|---|---|
| Signing | Apple Distribution + Mac Installer Distribution | **Developer ID Application** (+ **Developer ID Installer** for `.pkg`) |
| Sandbox | required | optional (recommended) |
| Review | App Review | notarization (automated, "not App Review") |
| Updates | Mac App Store only (2.4.5(vii)) | your own — Sparkle |
| Beta | TestFlight for Mac | your own feed / channel |
| Source | [Guidelines 2.4.5](https://developer.apple.com/app-store/review/guidelines/#2.4.5) | [Notarizing macOS software](https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution) |

### 4.2 Notarization and Gatekeeper

| Fact | Source |
|---|---|
| Notarize all Developer ID software (required since 10.15). Requirements: every executable signed with Developer ID, **Hardened Runtime**, **secure timestamp**, no `get-task-allow`, SDK ≥ 10.9, well-formed entitlements | [Notarizing macOS software](https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution) |
| Notarizable artifacts: apps, non-app bundles, UDIF disk images, flat installer packages; `xcrun notarytool submit … --keychain-profile … --wait`, then `xcrun stapler staple` | same; [Customizing the notarization workflow](https://developer.apple.com/documentation/security/customizing-the-notarization-workflow) |
| Sequoia removed the Control-click Gatekeeper override — un-notarized apps need System Settings → Privacy & Security → Open Anyway | [AppleInsider](https://appleinsider.com/articles/24/08/06/apple-removes-control-click-option-for-skipping-gatekeeper-in-macos-sequoia) (2024-08-06) |
| macOS 27: `spctl --purge` cleans Gatekeeper entries for unmounted apps | macOS 27 release notes, "Gatekeeper" |
| **Developer ID Sub-CA expires 2027-02-01**: certificates from it stop working; **`.pkg` signed with an affected cert will not install from that date — re-sign**; already-notarized apps with a secure timestamp keep working; issue new certs from **Developer ID CA (G2)**, choose the G2 Sub-CA in Xcode | [Apple Developer News](https://developer.apple.com/news/?id=w4atic4c) (2026-10-01) |

### 4.3 Auto-update — Sparkle 2

| Fact | Source |
|---|---|
| **Sparkle 2.10.1**, 2026-10-25 ("Golden Gate Bump"); 2.10.0 on 2026-09-13; **requires macOS 12+**; CocoaPods support dropped | [Sparkle releases](https://github.com/sparkle-project/Sparkle/releases); `Package.swift` `.macOS(.v12)` |
| Setup: SPM; `SPUStandardUpdaterController` + "Check for Updates…" menu item (`SUUpdater` is a deprecated stub); `generate_keys` → **EdDSA** private key in Keychain, `SUPublicEDKey` in Info.plist; `SUFeedURL`; monotonic `CFBundleVersion`; `generate_appcast` builds appcast + deltas | [Sparkle documentation](https://sparkle-project.org/documentation/) |
| Hardening: `SURequireSignedFeed` (needs `SUVerifyUpdateBeforeExtraction`); signed feeds validated from 2.9; DSA signatures to be retired ("Migrating to EdDSA from DSA") | same |
| Signing: Developer ID + notarize; with library validation, ad-hoc local builds may fail to load Sparkle — use an Apple Development cert or relax library validation in Debug only; sandboxed apps keep Sparkle's XPC services (non-sandboxed may remove them) | same |

### 4.4 Packaging and CI

| Tool | Version / fact | Source |
|---|---|---|
| `create-dmg` (shell) | 1.3.0 (2026-07-02) | [create-dmg/create-dmg](https://github.com/create-dmg/create-dmg/releases) |
| `create-dmg` (Node, sindresorhus) | 8.1.0 (2026-03-21) | [sindresorhus/create-dmg](https://github.com/sindresorhus/create-dmg/releases) |
| `pkgbuild` / `productbuild` | set `hostArchitectures` explicitly (27 defaults missing value to arm64) | macOS 27 release notes, "Rosetta" |
| fastlane | 2.241.2 (2026-10-26); `notarize` action (`package`, `api_key`, staples unless `skip_stapling`) | [fastlane releases](https://github.com/fastlane/fastlane/releases); [notarize action](https://docs.fastlane.tools/actions/notarize/) |
| GitHub Actions | `macos-latest` = `macos-26` arm64 (26.7.2, image 2026-11-02); **`xcode-27` / `xcode-27-xlarge` arm64 label in preview**; Intel only as `macos-26-intel` / `macos-15-intel`; **macOS 14 images retired 2026-11-02** | [actions/runner-images README](https://github.com/actions/runner-images) |
| Xcode Cloud | builds, tests, distributes Mac apps to TestFlight, the App Store "or as a notarized app" | [Xcode Cloud](https://developer.apple.com/documentation/xcode/xcode-cloud) |

---

## 5. Accessibility on macOS

| Fact | Source |
|---|---|
| Support Full Keyboard Access (macOS Settings → Accessibility); don't override system shortcuts; everything reachable from the keyboard | [HIG Keyboards](https://developer.apple.com/design/human-interface-guidelines/keyboards); [HIG Accessibility](https://developer.apple.com/design/human-interface-guidelines/accessibility) |
| 27 fixes keyboard loop when full keyboard navigation is off; open/save panel tab order | macOS 27 release notes, "AppKit" |
| Test ids: SwiftUI `.accessibilityIdentifier` (macOS 11); AppKit `NSAccessibilityProtocol.accessibilityIdentifier()` / `setAccessibilityIdentifier` (10.10). Mac2 driver's `accessibility id`/`id`/`name` all map to `identifier` | [accessibilityIdentifier](https://developer.apple.com/documentation/swiftui/view/accessibilityidentifier(_:)); [Mac2 locators](https://appium.github.io/appium-mac2-driver/latest/reference/locator-strategies/) |
| SwiftUI on macOS 27: a `Menu` with `.plain`/custom button style now exposes AXTitle, not AXDescription | macOS 27 release notes, "SwiftUI" |
| Environment: `accessibilityReduceMotion`, `accessibilityReduceTransparency`, `colorSchemeContrast` (all 10.15) — Reduce Transparency matters more under Liquid Glass | Apple SwiftUI docs |
| **`XCUIVoiceOverService`** (Xcode 27, macOS 27): drive VoiceOver from UI tests, assert focus and spoken output | Xcode 27 release notes, "Testing"; [XCUIVoiceOverService](https://developer.apple.com/documentation/xcuiautomation/xcuivoiceoverservice) |
| Xcode 27 agent skills: accessibility-voiceover / dynamic-type / sufficient-contrast specialists | [blakecrosley.com](https://blakecrosley.com/blog/xcode-plugin-claude-code) (secondary) |

---

## 6. Testing

| Fact | Source |
|---|---|
| Swift Testing + XCTest on macOS as on iOS (002 §4.2). Xcode 27: cross-framework assertion misuse raises a runtime warning; `swift test --maximum-repetitions … --repeat-until` + failure summary; per-arg test-case links | Xcode 27 release notes, "Testing", "Swift Package Manager" |
| UI tests: `XCUIAutomation` framework (split out of XCTest, Xcode 16.3+); Mac UI tests run on the host Mac (no simulator); test plans can set app-crash severity (off/warning/failure/fatal) | [XCUIAutomation](https://developer.apple.com/documentation/xcuiautomation); Xcode 27 release notes |
| **Appium Mac2 driver**: 5.0.1 (2026-11-13) / 5.0.0 (2026-11-09) **require Appium 4**, which is still beta (4.0.0-beta.8, 2026-11-13); **stay on Mac2 4.6.1 (2026-11-06) with Appium 3 (3.9.1 stable, 2026-11-14)**; 1.x–2.x for Appium 2. Host macOS 11.3+, Xcode 13+; `platformName: mac`, `automationName: mac2`; `automationmodetool enable-automationmode-without-authentication` to silence the prompt | [Mac2 releases](https://github.com/appium/appium-mac2-driver/releases); [Getting started](https://appium.github.io/appium-mac2-driver/latest/getting-started/); [Appium releases](https://github.com/appium/appium/releases) |
| Mac2 locators: `accessibility id` = `id` = `name` → **`identifier`**; `className` → `elementType`; predicate string; class chain; XPath (slow, from page source) | [Mac2 locator strategies](https://appium.github.io/appium-mac2-driver/latest/reference/locator-strategies/) |
| Snapshot: swift-snapshot-testing **1.19.7** (2026-10-21), supports `NSView` / `NSViewController` image strategies | [releases](https://github.com/pointfreeco/swift-snapshot-testing/releases) |
| ViewInspector 0.10.5 (2026-09-30) for SwiftUI view unit tests (lane only where used) | [releases](https://github.com/nalexn/ViewInspector/releases) |

---

## 7. Performance and observability

| Fact | Source |
|---|---|
| A hang = main run loop busy > **250 ms** (Apple's tools' default); macOS shows the spinning wait cursor | [Understanding hangs in your app](https://developer.apple.com/documentation/xcode/understanding-hangs-in-your-app) |
| Instruments 27: Swift Executors instrument (Main Actor, cooperative pool), unified System Trace, Foundation Models instrument, `xctrace record --recording-options` | Xcode 27 release notes, "Instruments" |
| **MetricKit on macOS 12+**; diagnostics delivered immediately on macOS 12+; **macOS 27 `MetricManager` delivers `MetricReport` / `DiagnosticReport` as async sequences**; `HangDiagnostic`, `CrashDiagnostic`, `HangTimeMetric` | [MetricKit](https://developer.apple.com/documentation/metrickit) |
| Xcode 27 agents can read Organizer insights (crashes, hangs, disk writes, launch) | Xcode 27 release notes, "Coding Intelligence" |
| OpenTelemetry Swift **2.6.0** (2026-10-01), `Package.swift` floor `.macOS(.v12)` | [releases](https://github.com/open-telemetry/opentelemetry-swift/releases) |
| Sentry Cocoa **9.34.0** (2026-11-12); macOS 12+ from 9.25.0; uncaught `NSException` needs `enableUncaughtNSExceptionReporting`; **no Session Replay on macOS**; no automatic app-start / screen-load transactions on macOS | [Sentry macOS guide](https://docs.sentry.io/platforms/apple/guides/macos/); [releases](https://github.com/getsentry/sentry-cocoa/releases) |
| Firebase Apple SDK 13.2.0 (2026-11-13): **Crashlytics fully supported on macOS**; Performance Monitoring not listed for macOS; Auth "partial" | [Firebase platform support](https://firebase.google.com/docs/ios/learn-more#firebase_library_support_by_platform) |
| Unified logging: `os.Logger` (same as iOS) | 002 §4.2 |

---

## 8. Architecture and persistence

| Lane | Fact | Source |
|---|---|---|
| Default | MV + `@Observable` (macOS 14+); `@State` macro (Xcode 27) back-deploys to macOS 14 — no repeated `init` of `@State` models | [WWDC26 269](https://developer.apple.com/videos/play/wwdc2026/269/); macOS 27 release notes |
| Scene-scoped state | `@FocusedValue` / `focusedSceneValue` connect menu commands and utility windows to the focused window — the Mac-specific state seam | [UtilityWindow](https://developer.apple.com/documentation/swiftui/utilitywindow) |
| `@Entry` | 27 warns on default class instances / closures in the environment | macOS 27 release notes |
| TCA | 1.26.2 (2026-08-28) — lane where used | [releases](https://github.com/pointfreeco/swift-composable-architecture/releases) |
| SwiftData | macOS 14+; 27 fixed a `@Query` deadlock with background `ModelActor` saves | [SwiftData](https://developer.apple.com/documentation/swiftdata); macOS 27 release notes |
| GRDB / SQLiteData | GRDB **7.12.0** (2026-11-01); Point-Free SQLiteData **1.13.0** (2026-11-09) | [GRDB](https://github.com/groue/GRDB.swift/releases); [sqlite-data](https://github.com/pointfreeco/sqlite-data/releases) |
| Core Data | brownfield lane | — |
| Document apps | `DocumentGroup` + `Document` / `ReadableDocument` (27) or `ReferenceFileDocument`; package documents with incremental `FileWrapper` writes | §2.3 |

---

## 9. Agents and AI

| Fact | Source |
|---|---|
| Xcode 27: agents with editable Markdown plans; plugins with skills, MCP servers, ACP agents; Apple-built specialists; filesystem security layer for agents; Agent Client Protocol; Gemini added | Xcode 27 release notes, "Coding Intelligence" |
| **`sudo xcrun mcp-server enable`** (preview from beta 5): MCP server without an open workspace; `xcrun mcp-server status`; `--unsafe-always-allow-all-agents` for unattended CI only | same |
| MCP tools to edit build settings, entitlements and Info.plist keys, drive the debugger, render previews (incl. macOS preview groups); LLDB ships `lldb-mcp` | same |
| Apple's `xcode` Claude Code plugin (`xcrun agent plugin path --plugin-format claude`; one `xcode` MCP server via `xcrun mcpbridge`; 16 skills on 27.2: swiftui-specialist, swiftui-whats-new-27, app-intents-specialist, app-intents-whats-new-27, building-document-based-swiftui-applications, audit-xcode-security-settings, adopt-c-bounds-safety, app-resizability, accessibility-*-specialist ×3, modernize-tests, xctrace, translation, translation-coordinator, device-interaction) — none Mac-only | [blakecrosley.com](https://blakecrosley.com/blog/xcode-plugin-claude-code) (2026-11-11, secondary) |
| **Foundation Models on macOS 26+** (`SystemLanguageModel`); needs an Apple-Intelligence Mac — check `availability` (`.deviceNotEligible`, `.modelNotReady`); 27 adds Private Cloud Compute (`PrivateCloudComputeLanguageModel`, entitlement), dynamic profiles, multimodal prompts, custom `LanguageModel` providers | [Foundation Models](https://developer.apple.com/documentation/foundationmodels); [SystemLanguageModel](https://developer.apple.com/documentation/foundationmodels/systemlanguagemodel) |
| Core AI (new 27) for on-device custom models on Apple silicon | [WWDC26 macOS guide](https://developer.apple.com/wwdc26/guides/macos/) |

---

## 10. Migration paths

| Path | Key steps | Source |
|---|---|---|
| AppKit → SwiftUI | `@Observable` models first (AppKit tracks them; `NSObservationTrackingEnabled` for macOS 15); new views via `NSHostingView`; menus via `NSHostingMenu`; Settings via `NSHostingSceneRepresentation`; keep AppKit where it is better (text, complex tables) | [WWDC26 272](https://developer.apple.com/videos/play/wwdc2026/272/) |
| AppKit input modernisation | `mouseDown:` → gesture recognizers / control events / view-based APIs; `NSTextSelectionManager` | [WWDC26 289](https://developer.apple.com/videos/play/wwdc2026/289/) |
| `FileDocument` → `Document` | 27 SDK deprecation; `nonisolated` → `@concurrent` for read/write | macOS 27 release notes |
| Catalyst → native | add a native macOS SwiftUI target sharing model code; rebuild Mac chrome (menus, toolbar, Settings, windows) natively | §2.6 (derived) |
| Swift 5 → 6 | one module at a time, as iOS | 002 §4.2 |
| Intel → Apple silicon only | decide the Intel window (Tahoe gets security fixes ~3 yrs; Intel software dies on macOS 28); keep Universal while deployment target < 27; at 27 the build is arm64-only; audit `.pkg` `hostArchitectures`, x86_64-only dependencies and plug-ins | §1.3 |
| Electron → native | mention only — route to a SwiftUI rewrite per window/feature; no Apple guidance found | — |
| CocoaPods → SPM | Sparkle dropped CocoaPods; CocoaPods trunk read-only 2026-12-02 | Sparkle releases; 002 §4.2 |

---

## Not verified

- The exact behaviour of `NSDesignRequiresCompatibility` (if it exists) for pure AppKit apps — only the `UIDesignRequiresCompatibility` page (which lists macOS) was found.
- Whether XCUITest on macOS supports parallel UI test execution, and which TCC grants the test runner needs on 27.
- Whether `dropDestination(for:action:isTargeted:)` is actually deprecated at macOS 27.3 (the docs metadata shows "13.0 – 27.3", and `draggable(_:)` shows 27.3 — likely a 27.3-beta overload change).
- SwiftUI Dynamic Type equivalence on macOS (HIG asks for ≥ 200 % text enlargement but the macOS mechanism was not confirmed).
- Whether the shipping Sequoia/Tahoe/27 screen-recording re-prompt cadence is still monthly on macOS 27.
- `tccutil list` on unmanaged Macs (secondary source says it printed only usage).
- The `launchd` quarantine-plist change's exact scope (Apple's wording ambiguous per the secondary source).
- App Attest availability on Mac in 27 (secondary source only; docs metadata shows `DCAppAttestService` macOS 11).
- Xcode 27 macOS app templates' default `SWIFT_VERSION` (inferred from the iOS finding in 002, not re-checked for the macOS template).
- Control widgets' macOS availability version (Apple doc pages returned 404; only the 2025 newsroom statement).
- Touch-Mac prices/specs (secondary sources only); only the HIG touch guidance is primary.
- Xcode Cloud support for Developer ID notarized export of Mac apps beyond the doc's one-line "or as a notarized app".
