# desktop-macos Conformance Checklist — the 21 sections

The audit's spine. Section letters and check numbers are **permanent** — a finding is `<letter><n>` (`B3`, `M1`) and keeps that ID across every round, forever. Never renumber; append new checks at the end of a section with the next free number. The letters are identical on both desktop platforms (`macos`, `windows`) and keep their meaning from the mobile checklists: `M` is Accessibility everywhere. `Q` (motion) and `T` (release) are unused: motion is in E, release in L.

**How to read a row.** *Check* = the invariant. *Violation looks like* = what disqualifies it. *Find it with* = a mechanical lead (a grep hit is never a finding — read the code). *Sev* = the default severity; adjust for real impact and say why.

**Recipes** use `rg` (ripgrep), which honours `.gitignore` — so `.build/`, `DerivedData/` and `*.xcodeproj` contents when ignored are skipped without flags. Without ripgrep, `grep -rn --include='*.swift' --include='*.plist' --include='*.entitlements' --include='*.xcconfig' --exclude-dir=.build` is equivalent. Set the source roots once:

```bash
SRC=$(ls -d Sources App *App* 2>/dev/null | tr '\n' ' ')   # adjust to the repo layout
rg -n "<pattern>" $SRC -g '*.swift'   # the shape every recipe below uses
```

If the repo gitignores generated sources (SwiftGen, Sourcery output) you still need to read, add `--no-ignore` and exclude it explicitly — and say so in the report's coverage line.

**The version lane gates everything.** Before flagging, confirm the check applies to the detected Xcode / Swift language mode (Swift 6 primary, Swift 5-mode supported), the deployment target and whether the UI is SwiftUI or AppKit. Rows tagged **[mac15+]**, **[mac27SDK]**, **[AppKit]**, **[MAS]** and **[DevID]** apply only in that lane.

**Fragment sections.** K, L and U carry no rows here: their rows live in `desktop/_shared/<skill>/references/audit-checks.md` and are filtered by the `Platforms` column. X is not applicable on macOS. Every other section is filled by the task that writes its skill — an empty section means that skill is not written yet, not that the code passes.

**Severity.** blocker — ships a crash, a store or notarization rejection, or a hard security rule break. major — a rule in CLAUDE.md § Desktop code rules broken where it will hurt soon. minor — style, naming, a single missing label. nit — preference.

---

## A — Version lane, toolchain & migration hygiene
*Owning skills: [`project-setup`](../../project-setup/SKILL.md) · [`migration`](../../migration/SKILL.md) · [`basics`](../../basics/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| A1 | Deployment target is stated and was not raised as a side effect | `MACOSX_DEPLOYMENT_TARGET` above what the project had, or below 12 (Xcode 27's floor); a target the plan or PR never states | `rg -n "MACOSX_DEPLOYMENT_TARGET" -g '*.pbxproj' -g '*.xcconfig'`; compare with `git log -p` on the file | major |
| A2 | A new app targets macOS 15, or 14 with a stated reason `[mac15+]` | A greenfield app on 13 or 14 that uses no API the lower target needs, with no recorded reason (a recommendation, D4: a stated reason clears it) | `rg -n "MACOSX_DEPLOYMENT_TARGET" -g '*.xcconfig'` | minor |
| A3 | Xcode 27.2's 27.1 deployment target is not used | `MACOSX_DEPLOYMENT_TARGET = 27.1` (the SDK wrongly accepts it) | `rg -n "MACOSX_DEPLOYMENT_TARGET *= *27\.1" -g '*.xcconfig' -g '*.pbxproj'` | major |
| A4 | Architectures follow the deployment target `[mac27SDK]` | A target ≥ 27 that must ship Intel with no `ARCHS` entry for x86_64 (nothing warns); or a target < 27 with `ARCHS = arm64` and no stated decision to drop Intel | `rg -n "ARCHS\b\|ONLY_ACTIVE_ARCH\|EXCLUDED_ARCHS" -g '*.xcconfig' -g '*.pbxproj'` | major |
| A5 | No removed linker flag | `-ld_classic` in `OTHER_LDFLAGS` (ld64 is removed; ignored with a warning) | `rg -n "ld_classic" -g '*.xcconfig' -g '*.pbxproj'` | minor |
| A6 | An installer package names its architecture | A `.pkg` build with no `hostArchitecture` (defaults to arm64 now) while Intel is in scope; pre/post-install scripts assuming Intel | `rg -n "hostArchitecture" -g '*.xml' -g '*.plist' -g '*.sh'`; read the packaging scripts | minor |
| A7 | No toolchain, SDK or language mode was up-levelled as a side effect | `SWIFT_VERSION`, the Xcode pin or the SDK changed in a commit about something else | `git log -p -S"SWIFT_VERSION" -- '*.xcconfig' '*.pbxproj'` | major |
| A8 | Dependencies are SPM; no CocoaPods | A `Podfile` in a project that still resolves from the trunk (read-only from 2026-12-02) | `rg --files -g 'Podfile*' -g '*.podspec'` | minor |
| A9 | No deprecated `PreviewProvider` | `struct … : PreviewProvider` (deprecated by the 27 SDK) | `rg -n "PreviewProvider" $SRC -g '*.swift'` | minor |

---

## B — Project structure, strictness & language standard
*Owning skills: [`project-setup`](../../project-setup/SKILL.md) · [`basics`](../../basics/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| B1 | Swift 6 language mode is set explicitly on every new module | `SWIFT_VERSION = 5.0` (the template's default) on a module created for this change; a package with `swiftLanguageModes` unset | `rg -n "SWIFT_VERSION\|swiftLanguageModes\|swift-tools-version" -g '*.pbxproj' -g '*.xcconfig' -g 'Package.swift'` | major |
| B2 | Warnings are errors | `SWIFT_TREAT_WARNINGS_AS_ERRORS` or `GCC_TREAT_WARNINGS_AS_ERRORS` not `YES`; a package with no `.treatAllWarnings(as: .error)` | `rg -n "TREAT_WARNINGS_AS_ERRORS\|treatAllWarnings" -g '*.xcconfig' -g '*.pbxproj' -g 'Package.swift'` | major |
| B3 | App module defaults to `MainActor`; a package stays `nonisolated` | A package target with `.defaultIsolation(MainActor.self)`; an app target with unannotated UI types and no default isolation | `rg -n "defaultIsolation\|DEFAULT_ACTOR_ISOLATION\|APPROACHABLE_CONCURRENCY" -g 'Package.swift' -g '*.xcconfig' -g '*.pbxproj'` | major |
| B4 | App Sandbox is on `[MAS]` | `ENABLE_APP_SANDBOX` not `YES`, or `com.apple.security.app-sandbox` absent or `false` in a Mac App Store build (a Developer ID build records its reason) | `rg -n "ENABLE_APP_SANDBOX\|app-sandbox" -g '*.xcconfig' -g '*.pbxproj' -g '*.entitlements'` | blocker |
| B5 | Hardened Runtime is on `[DevID]` | `ENABLE_HARDENED_RUNTIME` not `YES` on a notarized target | `rg -n "ENABLE_HARDENED_RUNTIME" -g '*.xcconfig' -g '*.pbxproj'` | blocker |
| B6 | Every entitlement has a recorded reason | A key in the `.entitlements` file with no row in the project's entitlements table or PR notes | `rg -n "<key>com\.apple" -g '*.entitlements'`; compare with the table | major |
| B7 | No release entitlement that weakens the runtime without a reason | `cs.disable-library-validation`, `cs.allow-jit`, `cs.allow-unsigned-executable-memory` or `get-task-allow` in a Release entitlements file | `rg -n "disable-library-validation\|allow-jit\|allow-unsigned-executable-memory\|get-task-allow" -g '*.entitlements'` | major |
| B8 | One xcconfig per environment; no `#if STAGING` in features | Environment values in the build settings only, or `#if STAGING` / `#if DEBUG` scattered through feature code | `rg -n "#if (STAGING\|DEBUG\|PROD)" $SRC -g '*.swift'`; `rg --files -g '*.xcconfig'` | minor |
| B9 | A privacy manifest exists in the app target | No `PrivacyInfo.xcprivacy`, or one that declares tracking `true` with no domains; iOS Required-reason entries copied in (not required on macOS) | `rg --files -g 'PrivacyInfo.xcprivacy'`; read `NSPrivacyCollectedDataTypes` | major |
| B10 | No `print`, `NSLog`, `debugPrint` or `dump` | A call in app or package source | `rg -n "\b(print\|NSLog\|debugPrint\|dump)\(" $SRC -g '*.swift'` | major |
| B11 | No force unwrap, `as!` or `try!` outside tests | `value!`, `as! T`, `try! f()` in source (an `@IBOutlet` in AppKit is the one exception) | `rg -n "\w!\.\|\w!\)\|as! \|try! " $SRC -g '*.swift' -g '!*Tests*'` | major |
| B12 | No blocking primitive and no GCD in new code | `DispatchSemaphore`, `.wait()`, `DispatchQueue.main.async`, `RunLoop.current.run`, `Task.detached` with no reason | `rg -n "DispatchSemaphore\|\.wait\(\|DispatchQueue\.main\|Task\.detached" $SRC -g '*.swift'` | major |
| B13 | No `@unchecked Sendable` or `nonisolated(unsafe)` without a justification | Either marker with no explanation in the type's doc comment | `rg -n "@unchecked Sendable\|nonisolated\(unsafe\)" $SRC -g '*.swift'` | major |
| B14 | No mutable static state | `static var` holding state; a singleton with mutable properties | `rg -n "static var \|\.shared\b" $SRC -g '*.swift'` | major |
| B15 | Logging uses `Logger` with privacy annotations; no secret or document path logged | A `Logger` call interpolating a token, email, URL with a query or a user file path with no `.private` | `rg -n "Logger\.\w+\.\w+\(" $SRC -g '*.swift'`; read each interpolation | major |
| B16 | A `protocol` has more than one conformer | An interface introduced for one caller and one implementation | `rg -n "^(public \|internal )?protocol \w+" $SRC -g '*.swift'`; count conformers per hit | major |
| B17 | Formatter and linter are configured and clean | No `.swift-format` or `.swiftlint.yml`; a lint rule set that allows `print(` or `DispatchQueue.main` | `rg --files -g '.swift-format' -g '.swiftlint.yml'` | minor |

---

## C — Architecture, state & DI
*Owning skill: [`architecture`](../../architecture/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| C1 | State sits at the lowest level that works | An `@Observable` model for a toggle one view owns; app-wide state for per-window selection | `rg -n "@Observable\|@State\|@Environment\|@Bindable" $SRC -g '*.swift'`; read each owner | major |
| C2 | A model is `@State` in its owner, not re-created in `body` | `let model = Model()` in a view body; `@State var model = Model()` re-initialised on a macOS 13 or 14 target without the 27 SDK fix | `rg -n "= [A-Z]\w*(Model\|Store)\(" $SRC -g '*.swift'` | major |
| C3 | Several windows on the same data share one store | Each window's root view fetches its own list; two copies of the same records | `rg -n "WindowGroup\|Window\(\|DocumentGroup" $SRC -g '*.swift'`; read what each root creates | major |
| C4 | Per-window state is selection and layout only | Records stored in `@SceneStorage` or `@AppStorage` | `rg -n "@SceneStorage\|@AppStorage" $SRC -g '*.swift'`; read the value types | minor |
| C5 | A menu command reads `@FocusedValue`, and is disabled when it is nil | A command holding a reference to the model directly, or hidden with `if` when nothing is focused | `rg -n "@FocusedValue\|@FocusedObject\|focusedSceneValue\|focusedSceneObject" $SRC -g '*.swift'`; `rg -n "Commands" $SRC -g '*.swift'` | major |
| C6 | Constructor injection only; no service locator | `Container.shared`, `ServiceLocator`, a default instance in `@Entry`, a model built inside a view that needs a client | `rg -n "Container\.shared\|ServiceLocator\|@Entry var \w+ *= *\w+\(" $SRC -g '*.swift'` | major |
| C7 | A view model exists only where logic is tested apart from the view | A `ViewModel` that forwards one call to a service | `rg -n "class \w+ViewModel" $SRC -g '*.swift'`; read each body | major |
| C8 | Observation follows the target `[mac13]` | `@Observable` on a macOS 13 target; `ObservableObject` in a macOS 14+ module being written new | `rg -n "ObservableObject\|@Published\|@StateObject" $SRC -g '*.swift'` | minor |
| C9 | AppKit Observation is back-deployed explicitly `[AppKit]` | An `@Observable` read in `draw(_:)` / `layout()` with a target below the 2026 releases and no `NSObservationTrackingEnabled` | `rg -n "NSObservationTrackingEnabled" -g '*.plist'` | minor |
| C10 | Window revalidation is wired once | Reload code duplicated in each leaf view on `scenePhase`, wake or network change; none at all | `rg -n "scenePhase\|didWakeNotification\|NWPathMonitor" $SRC -g '*.swift'` | major |

---

## D — UI components & platform conventions
*Owning skills: [`ui-components`](../../ui-components/SKILL.md) · [`appkit`](../../appkit/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| D1 | A long list or table is virtualized `[mac15+]` | A `ForEach` of unbounded data inside a `ScrollView`; a `Table` wrapped in a `ScrollView` | `rg -n "ScrollView" -A6 $SRC -g '*.swift'`; look for `ForEach` / `Table` | major |
| D2 | Tabular data uses `Table`; selection is a set of stable ids | A `List` of `HStack` columns faking a table; selection by row index | `rg -n "Table\(\|List\(selection" $SRC -g '*.swift'` | minor |
| D3 | Every `ForEach` has stable domain ids | `id: \.self` on non-unique values; `.indices` as the identity | `rg -n "id: \\\.self\|\.indices" $SRC -g '*.swift'` | major |
| D4 | Every data region has loading, loaded, empty and failed states | A view that shows a blank pane on failure or treats an undecodable response as empty | `rg -n "LoadState\|ContentUnavailableView\|ProgressView" $SRC -g '*.swift'` | major |
| D5 | A failure is scoped to the response-dependent subtree and raises one persistent banner | A toolbar or search field replaced by an error; a modal alert for a background failure; an auto-dismissing banner | `rg -n "\.alert\(\|NSAlert\|confirmationDialog" $SRC -g '*.swift'` | major |
| D6 | Async loads use `.task`; nothing does I/O in `body` or `init` | `onAppear { Task { … } }`; `URLSession` or file reads in `init` | `rg -n "onAppear *\{[^}]*Task\|Task *\{" $SRC -g '*.swift'` | major |
| D7 | No action exists only in a context menu or on hover | A `contextMenu` item or an `onHover`-revealed button with no menu-bar or toolbar twin and no click path | `rg -n "contextMenu\|onHover\|hoverEffect" $SRC -g '*.swift'`; read each | major |
| D8 | In-app navigation is a real link or button | `onTapGesture` driving navigation on a `Text` or `Image` | `rg -n "onTapGesture" $SRC -g '*.swift'` | major |
| D9 | An inspector or sidebar shows the selection and has an empty state `[mac15+]` | An inspector that renders blank or crashes on no selection; no `InspectorCommands` so the keyboard cannot toggle it | `rg -n "\.inspector\(\|InspectorCommands" $SRC -g '*.swift'` | minor |
| D10 | Previews exist per state and use real views | No `#Preview`; a protocol built only for a preview; `PreviewProvider` | `rg -n "#Preview" $SRC -g '*.swift'` | minor |
| D11 | AppKit code uses gesture recognizers and target-action over `mouseDown:` `[AppKit]` | `override func mouseDown` or a tracking loop for a click that a recognizer or control event covers | `rg -n "override func mouse(Down\|Dragged\|Up)\|nextEvent\(matching" $SRC -g '*.swift'` | minor |
| D12 | A SwiftUI-in-AppKit host is owned and sized `[AppKit]` | An `NSHostingView` with no constraints or `sizingOptions`; a hosting controller never added as a child | `rg -n "NSHostingView\|NSHostingController\|NSViewRepresentable" $SRC -g '*.swift'` | minor |
| D13 | Menu icons are explicit on the 27 SDK `[mac27SDK]` | A menu or context-menu `Label` relying on its symbol with no `.labelStyle(.titleAndIcon)` where the icon carries meaning | `rg -n "Label\(" $SRC -g '*.swift'`; check menu content | nit |
| D14 | An AppKit view controller takes its dependencies by initializer and cancels its work `[AppKit]` | `NSApp.delegate as! AppDelegate` or a singleton read inside the controller; a load `Task` never cancelled in `viewDidDisappear` | `rg -n "NSApp\.delegate\|\.shared\b" $SRC -g '*.swift'`; `rg -n "class \w+: NSViewController" -A25 $SRC -g '*.swift'` | major |
| D15 | A hosting controller is a child and its content is constrained `[AppKit]` | `NSHostingController` whose `view` is added with no `addChild` or no constraints / `sizingOptions` (zero-size or focus-broken host) | `rg -n "NSHostingController" -A8 $SRC -g '*.swift'`; look for `addChild` | major |
| D16 | `NSViewRepresentable.updateNSView` is idempotent and a `Coordinator` owns delegates `[AppKit]` | State created in `updateNSView`; a delegate or target set to the representable struct; no `dismantleNSView` for a task or observer | `rg -n "NSViewRepresentable" -A30 $SRC -g '*.swift'` | major |
| D17 | AppKit `@Observable` reads sit in tracked methods `[AppKit]` | A property read only in a method other than `draw(_:)`, `layout()`, `updateConstraints()`, `updateLayer()` or their controller twins, with a manual `needsDisplay` patch on every change | `rg -n "needsDisplay = true\|needsLayout = true" $SRC -g '*.swift'`; read the observed reads | minor |
| D18 | AppKit menu items are validated, not removed `[AppKit]` | `validateMenuItem` setting `isHidden` for an unavailable command; `NSMenu` items added and removed per selection | `rg -n "validateMenuItem\|isHidden *=" $SRC -g '*.swift'` | major |
| D19 | State restoration encodes ids, never records `[AppKit]` | `encodeRestorableState` writing a document or database payload; a restoration handler that returns without calling its completion | `rg -n "encodeRestorableState\|restoreState\|restorationClass" -A10 $SRC -g '*.swift'` | major |
| D20 | A 27-SDK gesture recognizer overrides `location(in:)` `[AppKit]` | A custom `NSGestureRecognizer` subclass with no `location(in:)` override (the base returns zero) | `rg -n "class \w+: NSGestureRecognizer" -A20 $SRC -g '*.swift'` | minor |

---

## E — Styling, theming, motion & adaptive layout
*Owning skill: [`styling`](../../styling/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| E1 | No custom bar background fights Liquid Glass `[mac27SDK]` | `toolbarBackground`, `.background(.ultraThinMaterial)` behind a system toolbar or sidebar, a custom titlebar fill | `rg -n "toolbarBackground\|ultraThinMaterial\|NSTitlebarAccessoryViewController" $SRC -g '*.swift'` | major |
| E2 | No advice or code opts out of the new design on the 27 SDK `[mac27SDK]` | `UIDesignRequiresCompatibility` kept in `Info.plist` and described as working on a macOS 27 link | `rg -n "UIDesignRequiresCompatibility" -g '*.plist' -g '*.xcconfig'` | major |
| E3 | Custom glass is grouped, not stacked, and availability-gated | `glassEffect` inside another glass surface; ungrouped neighbours; used below macOS 26 with no `#available` and fallback | `rg -n "glassEffect\|GlassEffectContainer\|\.glass" $SRC -g '*.swift'` | major |
| E4 | Colours are semantic or asset symbols | `Color(red:green:blue:)`, hex literals or `NSColor(calibratedRed:` in views; no dark or High Contrast variant | `rg -n "Color\(red:\|Color\(hex\|NSColor\(calibrated\|UIColor\(red" $SRC -g '*.swift'` | major |
| E5 | State is never shown by colour alone | A status shown only by a red or green fill | `rg -n "foregroundStyle\(\.(red\|green)\|\.tint\(\.(red\|green)" $SRC -g '*.swift'`; read each | major |
| E6 | Controls and text meet the Mac minimums | A control frame under 20 × 20 pt; text under 10 pt; `.font(.system(size: 8))` | `rg -n "\.font\(\.system\(size: *([0-9]\|10)\b\|\.frame\((width\|height): *(1[0-9]\|[0-9])\b" $SRC -g '*.swift'` | major |
| E7 | Presented content re-applies control settings `[mac27SDK]` | A sheet or popover relying on a parent `.controlSize`, `.buttonSizing` or `.menuIndicatorVisibility` (reset on the 27 SDK) | `rg -n "\.sheet\(\|\.popover\(" -A8 $SRC -g '*.swift'` | minor |
| E8 | A window has a minimum size and survives narrow widths | No `frame(minWidth:minHeight:)` or `windowResizability`; content clipped at the minimum | `rg -n "minWidth\|windowResizability\|windowIdealSize" $SRC -g '*.swift'` | major |
| E9 | Reduce Transparency has an opaque fallback | A custom translucent surface that never reads `accessibilityReduceTransparency` | `rg -n "Material\|NSVisualEffectView" $SRC -g '*.swift'`; `rg -n "accessibilityReduceTransparency" $SRC -g '*.swift'` | major |
| E10 | Increase Contrast is honoured | A hairline separator or border at low opacity with no `colorSchemeContrast` branch | `rg -n "colorSchemeContrast\|\.opacity\(0\.[01]" $SRC -g '*.swift'` | minor |
| E11 | Every animation honours Reduce Motion | `withAnimation` or `.animation(` moving, scaling or rotating a view with no `accessibilityReduceMotion` branch in the file | `rg -n "withAnimation\|\.animation\(\|rotationEffect\|scaleEffect\|PhaseAnimator\|KeyframeAnimator" $SRC -g '*.swift'`; `rg -n "accessibilityReduceMotion" $SRC -g '*.swift'` | major |
| E12 | Animation is state-driven, short and interruptible | A `Timer` driving a view property; an infinite repeating animation; a duration over 400 ms for feedback | `rg -n "repeatForever\|Timer\.publish\|duration: *[1-9]" $SRC -g '*.swift'` | minor |
| E13 | Hover-only styling has a non-hover state | A control visible or enabled only on hover | `rg -n "onHover" -A4 $SRC -g '*.swift'` | major |

---

## F — Windows, navigation & commands
*Owning skills: [`windows-and-scenes`](../../windows-and-scenes/SKILL.md) · [`menus-and-commands`](../../menus-and-commands/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| F1 | Windows open with `openWindow`; no `pushWindow` | A `pushWindow` call (it does not exist on macOS); `NSApp.sendAction` or a hand-built `NSWindow` for a window SwiftUI can open | `rg -n "pushWindow\|NSWindow\(contentRect" $SRC -g '*.swift'` | blocker |
| F2 | The scene matches the need | A `WindowGroup` for a one-of window (duplicates); a `WindowGroup` or hand-built window for preferences instead of `Settings` | `rg -n "WindowGroup\|Window\(\|Settings" $SRC -g '*.swift'`; read each root | major |
| F3 | One store is created in the `App` and injected into every scene | A model created inside a scene's root view or per window | `rg -n "@State.*= *\w+(Model\|Store)\(" $SRC -g '*.swift'`; read where each is declared | major |
| F4 | Windows are resizable with a minimum size and restore their frame | A fixed-size window with no recorded reason; `restorationBehavior(.disabled)` with no reason; absolute frames stored by hand | `rg -n "windowResizability\|restorationBehavior\|setFrame\|frame\(width: *[0-9]+, *height: *[0-9]+\)" $SRC -g '*.swift'` | major |
| F5 | Restored window state is ids and layout only | Records or documents in `@SceneStorage` | `rg -n "@SceneStorage" $SRC -g '*.swift'`; read the types | minor |
| F6 | A window's work is cancelled when it closes; revalidation is at the window root | A stored `Task` with no cancel; reload code in leaf views on wake or reactivation | `rg -n "Task *\{\|scenePhase\|didWakeNotification" $SRC -g '*.swift'` | major |
| F7 | A `UtilityWindow` or `defaultWindowPlacement` is gated to macOS 15 `[mac15+]` | `UtilityWindow`, `defaultWindowPlacement` or `windowLevel` on a macOS 13 or 14 target with no `#available` | `rg -n "UtilityWindow\|defaultWindowPlacement\|windowLevel\|restorationBehavior\|defaultLaunchBehavior" $SRC -g '*.swift'`; compare `MACOSX_DEPLOYMENT_TARGET` | major |
| F8 | Every toolbar item also exists as a menu command and is labelled | A toolbar button with no menu item; an icon-only item with no `Label` or `.help` | `rg -n "ToolbarItem" -A6 $SRC -g '*.swift'`; cross-read `commands` | major |
| F9 | A menu-bar-only app saves on change and offers Quit and the main window `[LSUIElement]` | `LSUIElement` set with state saved only on quit; no `openWindow` path | `rg -n "MenuBarExtra\|LSUIElement" $SRC -g '*.swift' -g '*.plist'` | minor |
| F10 | Every command is in the menu bar | A command reachable only from a toolbar, a context menu or a button | `rg -n "CommandMenu\|CommandGroup\|\.commands" $SRC -g '*.swift'`; list the app's actions and match | major |
| F11 | A menu item is disabled, never hidden | `if` / `switch` around a `Button` inside `commands`; a `CommandMenu` made conditional | `rg -n "Commands" -A25 $SRC -g '*.swift'`; look for `if ` in the body | major |
| F12 | Commands read focused values | A command holding the model or a view reference; `focusedValue` on a leaf for a window-level command | `rg -n "@FocusedValue\|@FocusedObject\|focusedSceneValue\|focusedValue" $SRC -g '*.swift'` | major |
| F13 | The standard menu order and shortcuts hold | A custom shortcut on a standard action (⌘N for something else, ⌘, not Settings); a reordered or renamed system menu; a custom Settings item | `rg -n "keyboardShortcut" $SRC -g '*.swift'`; list against the HIG order | major |
| F14 | A context menu repeats menu-bar commands | A `contextMenu` item with no menu-bar twin | `rg -n "contextMenu" -A8 $SRC -g '*.swift'` | major |
| F15 | Menu icons are intentional on the 27 SDK `[mac27SDK]` | An item that needs its symbol to be told from another and has no `.labelStyle(.titleAndIcon)`; code that expects a menu image to appear | `rg -n "labelStyle\|Label\(" $SRC -g '*.swift'`; read menu content | minor |

---

## G — Forms & input
*Owning skill: [`forms`](../../forms/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| G1 | A form has one pure validator over a draft value | Validation rules inline in `onChange` closures; the model written before submit succeeds | `rg -n "func validate\|onChange\(of" $SRC -g '*.swift'` | major |
| G2 | Errors appear on the field that caused them, in more than colour | One error string for the whole form; red text only | `rg -n "foregroundStyle\(\.red\|Error\b" $SRC -g '*.swift'`; read the field views | major |
| G3 | Submit is guarded against a double submit | A Save button with no `isSubmitting` guard around an async call | `rg -n "Button\(\"(Save\|Submit\|Create)" -A6 $SRC -g '*.swift'` | major |
| G4 | Focus order and defaults are explicit; Return commits and Escape cancels | No `@FocusState` or `defaultFocus`; no `.defaultAction` / `.cancelAction` on a sheet form | `rg -n "FocusState\|defaultFocus\|keyboardShortcut\(\.(defaultAction\|cancelAction)" $SRC -g '*.swift'` | major |
| G5 | The key-view loop is complete and keyboard-reachable | A clickable `Text` or `onTapGesture` editing a value; an AppKit window with `autorecalculatesKeyViewLoop` off and no manual loop | `rg -n "onTapGesture\|autorecalculatesKeyViewLoop\|nextKeyView" $SRC -g '*.swift'` | major |
| G6 | Settings apply on change, with no Save button | A `Settings` pane with Save / Apply for plain preferences | `rg -n "Settings *\{" -A25 $SRC -g '*.swift'` | minor |
| G7 | An inspector shows an empty state with no selection and writes through the model | A form of blank fields with no selection; edits kept in local state until a button | `rg -n "\.inspector\(" -A10 $SRC -g '*.swift'` | minor |
| G8 | Every field has a visible label | A `TextField` whose only label is its prompt/placeholder | `rg -n "TextField\(\"\"" $SRC -g '*.swift'`; `rg -n "prompt:" $SRC -g '*.swift'` | major |
| G9 | Autofill content types are set on credential fields | A username or password field with no `textContentType` | `rg -n "SecureField\|textContentType" $SRC -g '*.swift'` | major |
| G10 | A server field error maps to its field; an unknown field becomes the form banner, never a modal alert | A server rejection shown in `.alert` or dropped | `rg -n "\.alert\(\|ProblemDetails\|422" $SRC -g '*.swift'` | major |
| G11 | Deprecated field styles are not new on the 27 SDK `[mac27SDK]` | New code with `.squareBorder` / `.roundedBorder` instead of `.bordered` + `textInputBorderShape` | `rg -n "squareBorder\|roundedBorder" $SRC -g '*.swift'` | minor |
| G12 | Sheet and popover controls re-apply sizing `[mac27SDK]` | A sheet form relying on the parent's `controlSize` or `buttonSizing` | `rg -n "\.sheet\(" -A12 $SRC -g '*.swift'` | minor |

---

## H — Networking & realtime
*Owning skill: [`networking`](../../networking/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| H1 | One concrete API client; no second HTTP layer | A protocol with one implementer mirroring the client; Alamofire beside a hand-rolled `URLSession` wrapper | `rg -n "URLSession\.(shared\|init)\|URLSession\(" $SRC -g '*.swift'` | major |
| H2 | Every request has a timeout budget by endpoint class | Default `timeoutIntervalForResource` (seven days); a `timeoutInterval` set at call sites | `rg -n "timeoutInterval\|timeoutIntervalFor" $SRC -g '*.swift'` | major |
| H3 | The sandbox grants outgoing network `[MAS]` | A sandboxed target calling an API with no `com.apple.security.network.client`; `network.server` with no listener | `rg -n "network\.(client\|server)" -g '*.entitlements'` | blocker |
| H4 | No blanket ATS exception | `NSAllowsArbitraryLoads` true; an `http://` host with no per-domain exception and reason | `rg -n "NSAllowsArbitraryLoads\|NSExceptionAllowsInsecureHTTPLoads\|http://" -g '*.plist' -g '*.swift' -g '*.xcconfig'` | major |
| H5 | Decode failure is a failed state, never empty | `try?` on `decode`; `?? []` after a decode; a list endpoint decoded as one object | `rg -n "try\? *(JSON)?[dD]ecoder\|decode\(.*\)\) *\?\? " $SRC -g '*.swift'` | major |
| H6 | Cancellation is not shown as a failure | `catch { state = .failed }` with no `CancellationError` / `URLError.cancelled` arm | `rg -n "CancellationError\|\.cancelled" $SRC -g '*.swift'`; read every `catch` after an `await` | major |
| H7 | Requests are owned by the window | `Task { }` or `Task.detached` for a request with no stored handle and no `.task(id:)` | `rg -n "Task\.detached\|Task *\{" $SRC -g '*.swift'` | major |
| H8 | Retries live in one place, bounded, with `Retry-After`; none while offline; writes only with an idempotency key | A retry loop in a view model; retrying `POST` without a key; sooner than `Retry-After`; a retry with `NWPath` unsatisfied | `rg -n "retry\|Retry-After\|Idempotency-Key\|NWPath" $SRC -g '*.swift'` | major |
| H9 | Token refresh is single-flight | N concurrent `401`s each refresh; a token held in a mutable class property | `rg -n "refresh\|401\|unauthorized" $SRC -g '*.swift'`; read the token owner | major |
| H10 | Connectivity is `NWPathMonitor`, never a ping | A reachability `GET` to a URL; `SCNetworkReachability` in new code | `rg -n "SCNetworkReachability\|NWPathMonitor\|ping" $SRC -g '*.swift'` | minor |
| H11 | Wake, activation and reconnect revalidate | No `NSWorkspace.didWakeNotification` observer; revalidation on `scenePhase` only; revalidating before `isOnline` | `rg -n "didWakeNotification\|willSleepNotification\|scenePhase" $SRC -g '*.swift'` | major |
| H12 | A write in one window reaches every window | One store instance per window; a request result written to `@State` only | `rg -n "ModelContainer\(\|@State .*= *\[\]\|DatabaseQueue\(" $SRC -g '*.swift'` | major |
| H13 | No secret, token, body or query secret is logged | `Logger` or `print` interpolating a request, URL with a query, or `Authorization` | `rg -n "Authorization\|\.absoluteString\|httpBody" $SRC -g '*.swift'`; read each log call | blocker |
| H14 | A socket is cancelled on window close and on sleep, reopened after reconnect, and revalidates what it feeds | A `URLSessionWebSocketTask` with no owner cancel; a reconnect that never refetches | `rg -n "webSocketTask\|AsyncBytes\|\.bytes\(for" $SRC -g '*.swift'` | major |
| H15 | A transfer that outlives the window uses a background session | A long download in a window-owned task; a background session with no app-wide owner | `rg -n "background\(withIdentifier" $SRC -g '*.swift'` | minor |

---

## I — Storage, documents & sync
*Owning skills: [`offline-and-storage`](../../offline-and-storage/SKILL.md) · [`documents`](../../documents/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| I1 | New document code uses `Document`, not `FileDocument` `[mac27SDK]` | A new `FileDocument` conformance in a project built with the 27 SDK and no recorded reason (deprecated there) | `rg -n ": *\(?FileDocument\|ReferenceFileDocument\|: *Document\b" $SRC -g '*.swift'` | major |
| I2 | Document read and write are off the main actor `[mac27SDK]` | A `nonisolated` `Document` conformer after the `@concurrent` change; UI access or main-actor work inside read or write | `rg -n "func write\|init\(reading\|init\(configuration" -A15 $SRC -g '*.swift'` | major |
| I3 | Every user edit registers undo | A document mutated with no `undoManager` registration, so the edited indicator stays clean | `rg -n "undoManager\|registerUndo" $SRC -g '*.swift'`; read each mutation | major |
| I4 | No hand-rolled save or autosave | A `Timer` writing the document URL; `Data.write(to:)` on the document URL outside the document API | `rg -n "\.write\(to:\|Timer\.scheduledTimer\|Timer\.publish" $SRC -g '*.swift'` | major |
| I5 | The UTI is declared and the role is right | A document type with no exported or imported type declaration; Editor role for a read-only type | `rg -n "UTExportedTypeDeclarations\|CFBundleDocumentTypes\|LSHandlerRank" -g '*.plist'`; `rg -n "UTType\(" $SRC -g '*.swift'` | major |
| I6 | A file package writes only changed parts and is versioned `[mac27SDK]` | `makeFileWrapper` building a fresh wrapper on every save, ignoring `previous:`; no version file in the package | `rg -n "makeFileWrapper\|FileWrapper\(" -A15 $SRC -g '*.swift'` | minor |
| I7 | Document menu items are the system's | A custom Save As where the HIG prefers Duplicate; a replaced New / Open | `rg -n "Save As\|CommandGroup\(replacing: \.(newItem\|saveItem)" $SRC -g '*.swift'` | minor |
| I8 | Unsaved work is never lost on quit or close | `applicationShouldTerminate` returning `.terminateNow` over edited documents; `preventsApplicationTerminationWhenModal` left on a blocking sheet | `rg -n "applicationShouldTerminate\|isDocumentEdited\|hasUnautosavedChanges" $SRC -g '*.swift'` | major |
| I9 | iCloud conflicts are surfaced and undownloaded files are a loading state | A conflict resolved silently by timestamp; a read of an evicted file reported as an error | `rg -n "NSFileVersion\|ubiquit\|isUbiquitousItem" $SRC -g '*.swift'` | minor |
| I10 | Every path resolves through `FileManager`, not a hard-coded string | `"~/Library/..."`, `NSHomeDirectory() + "/Library"`, `/Users/` in source | `rg -n "~/Library\|NSHomeDirectory\|\"/Users/" $SRC -g '*.swift'` | major |
| I11 | Each datum is in its home: secrets in Keychain, preferences in defaults, re-creatable data in Caches | A token or key in `UserDefaults`, a plist or a file; a cache in `Application Support` | `rg -n "UserDefaults.*(token\|secret\|password\|key)\|\.set\(.*(token\|secret)" -i $SRC -g '*.swift'` | blocker |
| I12 | Keychain items use the data protection keychain | A `SecItem*` query with no `kSecUseDataProtectionKeychain: true` | `rg -n "SecItem(Add\|CopyMatching\|Update\|Delete)\|kSecUseDataProtectionKeychain" $SRC -g '*.swift'` | major |
| I13 | One store for the app, created at the `App` level | A `ModelContainer`, `NSPersistentContainer` or `DatabasePool` created inside a view or per window | `rg -n "ModelContainer\(\|NSPersistentContainer\(\|DatabasePool\(\|DatabaseQueue\(" $SRC -g '*.swift'` | major |
| I14 | A schema change has a migration plan, tested from each released version | A `@Model` field edited with no `VersionedSchema` or `SchemaMigrationPlan`; an edited GRDB migration; `eraseDatabaseOnSchemaChange` outside Debug | `rg -n "VersionedSchema\|SchemaMigrationPlan\|registerMigration\|eraseDatabaseOnSchemaChange\|shouldInferMappingModelAutomatically" $SRC -g '*.swift'` | major |
| I15 | A store that will not open degrades: no crash, no silent wipe | `try!` or `fatalError` on a container; deleting the store file as recovery | `rg -n "try! *Model\|fatalError.*(store\|container\|database)\|removeItem.*(store\|sqlite)" -i $SRC -g '*.swift'` | blocker |
| I16 | A `@Model` or managed object does not cross actors | A `@Model` passed into a `@ModelActor` or `Task`; a `NSManagedObject` used off its context's queue | `rg -n "@ModelActor\|Task *\{.*(model\|object)\|perform *\{" $SRC -g '*.swift'` | major |
| I17 | Disk full and a locked keychain are recoverable states | A save `catch` that discards the user's value; a keychain read failure that wipes the item | `rg -n "catch" -B3 -A4 $SRC -g '*Store*.swift' -g '*Keychain*.swift'` | major |
| I18 | An offline write is queued durably with an idempotency key and reconciled after a quit | A queue held in memory; a `sending` row replayed blindly or dropped on relaunch | `rg -n "idempotency\|pending\|indeterminate\|outbox" -i $SRC -g '*.swift'` | major |
| I19 | The app does not read another app's or team's container | A path built from another bundle id; reading `Group Containers` without the app's own group | `rg -n "Containers/\|Group Containers\|containerURL\(forSecurityApplicationGroupIdentifier" $SRC -g '*.swift'` | blocker |
| I20 | Per-window UI state is `@SceneStorage`, preferences are `@AppStorage` and apply on change | A stored selection in `UserDefaults` shared by all windows; a preferences Save button | `rg -n "@SceneStorage\|@AppStorage\|UserDefaults" $SRC -g '*.swift'` | minor |

---

## J — Platform integration, permissions & background
*Owning skills: [`sandbox-and-permissions`](../../sandbox-and-permissions/SKILL.md) · [`background-and-helpers`](../../background-and-helpers/SKILL.md) · [`system-integration`](../../system-integration/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| J1 | The sandbox is on and was not disabled or widened as a side effect | `com.apple.security.app-sandbox` false or absent in a MAS or new Developer ID app; a new entitlement in an unrelated commit | `rg -n "app-sandbox" -g '*.entitlements'`; `git log -p -- '*.entitlements'` | blocker |
| J2 | Every entitlement is the narrowest that works and carries a recorded reason | `user-selected.read-write` where read-only suffices; a `temporary-exception` with no reason; an unexplained key | `rg -n "<key>com\.apple\." -g '*.entitlements'`; compare with the entitlement table in the repo | major |
| J3 | User files are reached through panels, drops or bookmarks | Reading `~/Documents` by path; a `temporary-exception.files.*` to reach a user folder | `rg -n "NSOpenPanel\|fileImporter\|bookmarkData\|temporary-exception" $SRC -g '*.swift' -g '*.entitlements'` | major |
| J4 | Security-scoped `start`/`stop` are balanced on every path | `startAccessingSecurityScopedResource()` with no `stop…` in a `defer`; a stop on the throw path missing; ignoring the `false` result | `rg -n "startAccessingSecurityScopedResource\|stopAccessingSecurityScopedResource" $SRC -g '*.swift'`; count per scope | major |
| J5 | A stale or unresolvable bookmark is a recoverable state | `bookmarkDataIsStale` ignored; a resolve failure that crashes or empties the list; no **Choose Folder…** path | `rg -n "bookmarkDataIsStale\|resolvingBookmarkData\|withSecurityScope" $SRC -g '*.swift'` | major |
| J6 | Every TCC permission has a usage string, a pre-prompt and a working denied path | A request with no `NS…UsageDescription`; the denied case is a blank view or an alert; no Open System Settings link | `rg -n "requestAccess\|CGRequest\|AXIsProcessTrusted\|UsageDescription" $SRC -g '*.swift' -g '*.plist'`; read each denied branch | major |
| J7 | Permissions are asked at the moment of use, not at launch | A request in `init`, `applicationDidFinishLaunching` or `.onAppear` of the root view | `rg -n "requestAccess\|requestAuthorization\|CGRequest" -B6 $SRC -g '*.swift'` | major |
| J8 | Permission state is re-read on activation | A state read once at launch; a screen that needs a relaunch to heal | `rg -n "authorizationStatus\|CGPreflight\|scenePhase" $SRC -g '*.swift'` | minor |
| J9 | Full Disk Access is never assumed or required | A launch gate or alert demanding FDA; reading the TCC database; no degrade path | `rg -n "Privacy_AllFiles\|TCC\.db\|full disk" -i $SRC -g '*.swift'` | blocker |
| J10 | Screen recording prefers `SCContentSharingPicker` `[mac15+]` | `CGRequestScreenCaptureAccess` for a per-capture feature on a target that has the picker | `rg -n "CGRequestScreenCaptureAccess\|SCContentSharingPicker" $SRC -g '*.swift'` | minor |
| J11 | Settings deep links are tested on the target and fall back | A hard-coded `x-apple.systempreferences:` anchor never opened on the deployment target; a force-unwrapped URL | `rg -n "x-apple\.systempreferences\|openSystemSettings" $SRC -g '*.swift'` | minor |
| J12 | Login items and agents use `SMAppService`, never hand-installed plists | `SMLoginItemSetEnabled`, `SMJobBless`, `launchctl`, a plist written to `~/Library/LaunchAgents` | `rg -n "SMLoginItemSetEnabled\|SMJobBless\|launchctl\|LaunchAgents\|LaunchDaemons" $SRC -g '*.swift' -g '*.sh' -g '*.plist'` | major |
| J13 | Launch at login registers only on the user's action and mirrors `status` `[MAS]` | `register()` at launch; a toggle backed by a stored Bool; `.requiresApproval` with no explanation or link | `rg -n "\.register\(\)\|SMAppService\|\.requiresApproval\|\.notFound" $SRC -g '*.swift'` | major |
| J14 | IPC uses `XPCSession`; `NSXPCConnection` only in a legacy lane, with caller verification `[mac14+]` | `NSXPCConnection` in new code on a 14+ target; a listener with no code-signing requirement | `rg -n "XPCSession\|XPCListener\|NSXPCConnection\|NSXPCListener\|setCodeSigningRequirement" $SRC -g '*.swift'` | major |
| J15 | Every XPC and helper message is validated untrusted input | A decoded message used unchecked (path, size, kind); an `NSSecureCoding` graph from an unverified peer | `rg -n "Codable\|NSSecureCoding\|incomingMessageHandler" $SRC -g '*.swift'`; read each handler | blocker |
| J16 | A dead helper is a scoped failed region, not a dead app | `try!` or `fatalError` on a session; a window blank after the service exits | `rg -n "cancellationHandler\|XPCRichError\|invalidationHandler" $SRC -g '*.swift'` | major |
| J17 | A helper receives a bookmark, not a path | A `String` path or `URL.path` in an XPC message | `rg -n "\.path\b" $SRC -g '*.swift'`; read the XPC message types | major |
| J18 | Background activity is deferrable, idempotent and cancellable | A `Timer` doing maintenance; `NSBackgroundActivityScheduler` that ignores `shouldDefer`; `beginActivity` never ended | `rg -n "NSBackgroundActivityScheduler\|shouldDefer\|beginActivity\|Timer\.scheduledTimer" $SRC -g '*.swift'` | minor |
| J19 | Every intent calls the model the UI calls and validates its parameters | Business logic inside `perform()`; a missing id crashing; an unbounded text parameter | `rg -n "AppIntent\|OpenIntent\|perform\(\) async" -A12 $SRC -g '*.swift'` | major |
| J20 | Entities are small and queries return current data `[mac27SDK]` | An entity carrying a payload near the 10 MB limit; a schema entity not rebuilt with the 27 SDK | `rg -n "AppEntity\|EntityQuery\|schema:" $SRC -g '*.swift'` | minor |
| J21 | A widget reads the shared store and reloads after writes | A network call in a `TimelineProvider`; a timer reload; no app group | `rg -n "TimelineProvider\|reloadTimelines\|application-groups" $SRC -g '*.swift' -g '*.entitlements'` | major |
| J22 | Notification authorization is asked in context with a denied path; a foreground failure is never a system notification | `requestAuthorization` at launch; a `UNNotificationRequest` for an error the user is looking at | `rg -n "requestAuthorization\|UNNotificationRequest\|UNUserNotificationCenter" $SRC -g '*.swift'` | major |
| J23 | One validated router handles URLs, notification responses, intents and file activations | A parser per entry point; an unvalidated host or id; a new window per URL (no `.handlesExternalEvents`) | `rg -n "onOpenURL\|handlesExternalEvents\|CFBundleURLTypes\|didReceive response" $SRC -g '*.swift' -g '*.plist'` | blocker |
| J24 | A URL or notification never carries a secret or triggers a destructive action unconfirmed | A token in a query; a `delete` route that acts on open | `rg -n "myapp://\|url\.query\|URLComponents" $SRC -g '*.swift'` | blocker |
| J25 | Pasted and dropped content is validated and its failure reported | A drop accepting any `UTType`; a pasted path opened as-is; a rejected drop with no banner | `rg -n "dropDestination\|onPasteCommand\|\.copyable\|NSItemProvider" $SRC -g '*.swift'` | major |
| J26 | A drop target has a targeted state and a click path | A hover-only affordance; a drop zone with no `isTargeted` | `rg -n "isTargeted\|onDrop\|dropDestination" $SRC -g '*.swift'` | minor |
| J27 | `NSFilePromiseReceiver` is used inside the drag callbacks `[AppKit]` `[mac27SDK]` | `receivePromisedFiles…` called from a stored closure after the drop returns | `rg -n "NSFilePromiseReceiver\|receivePromisedFiles" $SRC -g '*.swift'` | major |

---

## K — Security
*Owning fragment: [`desktop/_shared/security`](../../../../_shared/security/references/audit-checks.md)*

This section holds no rows of its own. The rows are those of `desktop/_shared/security/references/audit-checks.md` whose `Platforms` column names `macos`, and the ids are the fragment's — finding `K3` is row K3 of the security fragment. A row a static read cannot prove says **requires dynamic test → `qa-security`** and is reported as unverified, never as passed.

---

## L — Distribution & store compliance
*Owning fragment: [`desktop/_shared/distribution`](../../../../_shared/distribution/references/audit-checks.md)*

This section holds no rows of its own. The rows are those of `desktop/_shared/distribution/references/audit-checks.md` whose `Platforms` column names `macos`, and the ids are the fragment's — finding `L3` is row L3 of the distribution fragment. A row a static read cannot prove says **requires dynamic test → `qa-security`** and is reported as unverified, never as passed.

---

## M — Accessibility
*Owning skill: [`accessibility`](../../accessibility/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| M1 | Every interactive element has an accessible name, toolbar items included | An icon-only `Button`, a `ToolbarItem` or an `Image` inside a control with no label or text child | `rg -n '\b(Button\|Toggle\|Picker\|TextField\|ToolbarItem)\b' $SRC -g '*.swift'`; read each for a label | major |
| M2 | Controls are real controls, not tap gestures | `.onTapGesture` on a `Text` / `VStack` / `Image` acting as a button, with no `.isButton` trait | `rg -n 'onTapGesture' $SRC -g '*.swift'` | major |
| M3 | Every action is reachable by keyboard; the app survives Full Keyboard Access | A click-only or drag-only operation; a custom control with no `.focusable()` and no key handling; a command only in a context menu. requires dynamic test → `qa-desktop-<lang>` | `rg -n 'onTapGesture\|DragGesture\|contextMenu\|focusable\|onKeyPress' $SRC -g '*.swift'` | major |
| M4 | Standard shortcuts are not rebound and a new one collides with no system key | `.keyboardShortcut("q"`, `("w"`, `(","`, `("c"`, `("v"` with `.command` bound to another action | `rg -n 'keyboardShortcut\("[qwcvxzaf,]"' $SRC -g '*.swift'` | major |
| M5 | Focus order follows reading order; focus is visible | A removed focus ring (`.focusEffectDisabled()`) with no drawn replacement; `accessibilitySortPriority` papering over layout order; a sheet that traps Tab | `rg -n 'focusEffectDisabled\|accessibilitySortPriority\|focusSection' $SRC -g '*.swift'` | major |
| M6 | Escape closes and Return commits | A sheet, popover or inline editor with no `.cancelAction` / `.defaultAction` or `onKeyPress(.escape)` | `rg -n 'cancelAction\|defaultAction\|keyboardShortcut\(\.(cancelAction\|defaultAction)' $SRC -g '*.swift'` | minor |
| M7 | Controls are at least 20 × 20 pt, and `.small` / `.mini` is not the primary action; text is at least 10 pt | A `.frame(width:` or height under 20 on a control with no larger `contentShape`; `.font(.system(size: 9` | `rg -n 'frame\((width\|height): ([0-9]\|1[0-9])\b\|controlSize\(\.(mini\|small)\)\|font\(\.system\(size: [0-9]\b' $SRC -g '*.swift'` | major |
| M8 | Readable text uses text styles; no clamp and no fixed-height container around text | `.font(.system(size: …))` for body copy; `lineLimit(1)` on meaningful text; a fixed `.frame(height:)` around a label | `rg -n 'font\(\.system\(size\|lineLimit\(1\)\|frame\(height:' $SRC -g '*.swift'` | minor |
| M9 | State lives in traits and values, not in the label | A label such as "Sidebar, open", "Selected" or containing "button" | `rg -n -i 'accessibilityLabel\("[^"]*(button\|selected\|disabled\|open\|closed\|checked)' $SRC -g '*.swift'` | minor |
| M10 | Gesture, hover and drag operations have an accessibility action or a menu command | A hover-revealed button or custom drag with no `accessibilityAction(named:)` and no command | `rg -n 'onHover\|DragGesture\|\.draggable\|LongPressGesture' $SRC -g '*.swift'` — read each for an action | major |
| M11 | Async results and errors are announced without stealing focus | A save or error appearing with no `AccessibilityNotification.Announcement` / `NSAccessibility.post` | `rg -n 'Announcement\|NSAccessibility\.post\|accessibilityFocused' $SRC -g '*.swift'` | major |
| M12 | Decorative images are hidden, informative ones described; headings are marked; rows are one stop | A meaningful `Image` with no label; section titles as plain `Text` on a multi-section window; a row read as three elements | `rg -n 'Image\(\|isHeader\|accessibilityHidden\|accessibilityElement\(children' $SRC -g '*.swift'` | minor |
| M13 | Colour is never the only cue; Increase Contrast and Reduce Transparency are honoured | A state shown by colour alone with no `accessibilityDifferentiateWithoutColor` branch; hard-coded `Color(red:…)` pairs; custom glass or material with no `accessibilityReduceTransparency` read. Contrast requires a token check or a pass | `rg -n 'accessibilityDifferentiateWithoutColor\|accessibilityReduceTransparency\|colorSchemeContrast\|Color\(red:' $SRC -g '*.swift'` | major |
| M14 | Reduce Motion is honoured by custom animation | `withAnimation` / `PhaseAnimator` / `matchedGeometryEffect` with no `accessibilityReduceMotion` read | `rg -n 'accessibilityReduceMotion\|withAnimation\|PhaseAnimator' $SRC -g '*.swift'` | major |
| M15 | An accessibility label is never used as a test identifier, nor an identifier as a label | `.accessibilityLabel("Library.SearchField")` | `rg -n 'accessibilityLabel\("[A-Z][A-Za-z]*\.[A-Z]' $SRC -g '*.swift'` | major |
| M16 | Dynamic Type is not claimed on macOS, and no clamp or fixed-size trick pretends to it | A `@ScaledMetric` / `dynamicTypeSize` rule documented as Mac text scaling with no verified mechanism | `rg -n 'dynamicTypeSize\|ScaledMetric' $SRC -g '*.swift'` | nit |
| M17 | `[mac27SDK]` A `Menu` with a plain or custom button style is re-read for `AXTitle` | A tested menu whose accessible name changed after the SDK upgrade. requires dynamic test → `qa-desktop-<lang>` | `rg -n 'Menu *\{\|Menu\(' -A4 $SRC -g '*.swift'`; read the page source | minor |

---

## N — Performance
*Owning skill: [`performance`](../../performance/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| N1 | Nothing blocks the main thread | `Thread.sleep`, `DispatchSemaphore.wait`, `DispatchQueue.main.sync`, synchronous `Data(contentsOf:)` / `String(contentsOf:)` on a URL, a `FileManager` folder enumeration, in `@MainActor` or UI code | `rg -n 'Thread\.sleep\|\.wait\(\)\|DispatchSemaphore\|main\.sync\|Data\(contentsOf\|String\(contentsOf\|enumerator\(at' $SRC -g '*.swift'` | blocker |
| N2 | CPU-heavy or large-IO work runs off the main actor | Sorting / decoding / resizing / large JSON / large fetches inside a `@MainActor` method or `body`; `@concurrent` or a background actor absent | `rg -n 'JSONDecoder\(\)\.decode\|NSImage\(contentsOf\|\.sorted\(' $SRC -g '*.swift'` — read the isolation | major |
| N3 | `body` is pure and cheap | A formatter, sort, filter, decode or `DateFormatter()` created inside `body` or a `Table` cell | `rg -n 'DateFormatter\(\)\|NumberFormatter\(\)\|\.sorted\|\.filter' $SRC -g '*View*.swift'` | major |
| N4 | List and table identity is stable and domain-based; selection is by id | `ForEach(…, id: \.self)` on non-unique values; an index as identity; a selection holding row objects | `rg -n 'id: \\\.self\|ForEach\(0\.\.<\|enumerated\(\)\|selection: \$.*: *\[?[A-Z][a-z]+\]?\b' $SRC -g '*.swift'` | major |
| N5 | A `Table` / `List` is not wrapped in a `ScrollView`, and unbounded data is not built eagerly | `ScrollView { VStack { ForEach(items) … } }` over unknown-size data; a `Table` inside a `ScrollView` | `rg -n 'ScrollView' -A6 $SRC -g '*.swift' \| rg 'ForEach\|Table'` | major |
| N6 | Large data is sorted, filtered and paged in the model, off the main actor | A 100,000-row array sorted in a `sortOrder` handler on `@MainActor`; the whole store fetched to show one screen | `rg -n 'sortOrder\|FetchDescriptor\|fetchLimit' $SRC -g '*.swift'`; read the isolation and limits | major |
| N7 | `[AppKit]` An `NSTableView` is view-based, reuses cells and never calls `reloadData()` for one row | `reloadData()` in a per-change handler; cells created per row | `rg -n 'reloadData\(\)\|viewFor tableColumn\|makeView\(withIdentifier' $SRC -g '*.swift'` | major |
| N8 | No `AnyView` where a generic or `@ViewBuilder` works | `AnyView(` return types | `rg -n 'AnyView' $SRC -g '*.swift'` | minor |
| N9 | Images are downsampled to their display size | A full-resolution photo decoded for a thumbnail | `rg -n 'NSImage\(data:\|NSImage\(contentsOf\|Image\(nsImage' $SRC -g '*.swift'` | major |
| N10 | Launch does only first-window work | Synchronous network, file or database work, or non-essential SDK initialisation, in `App.init` / the root `body`; the crash reporter excepted; every restored window loading at once | `rg -n 'init\(\)' -A12 $SRC -g '*App.swift'` | major |
| N11 | Retain cycles and unowned tasks are avoided; a closed window releases its model | A stored closure capturing `self` strongly; a `Task`, observer, `NSEvent` monitor or timer not cancelled or removed on window close | `rg -n 'Task \{' -B2 $SRC -g '*.swift'`; `rg -n 'addLocalMonitorForEvents\|addObserver\|Timer\.scheduledTimer' $SRC -g '*.swift'` | major |
| N12 | Caches are bounded | A `[Key: Value]` dictionary used as an unbounded cache | `rg -n 'static var .*: \[.*:.*\] = \[:\]\|NSCache' $SRC -g '*.swift'` | minor |
| N13 | Idle work is coalescable: no polling `Timer`; activities are ended | A repeating `Timer` doing maintenance with no window active; `beginActivity` never ended; `NSBackgroundActivityScheduler` ignoring `shouldDefer` | `rg -n 'Timer\.scheduledTimer\|beginActivity\|endActivity\|NSBackgroundActivityScheduler\|shouldDefer' $SRC -g '*.swift'` | minor |
| N14 | Pointer-rate callbacks do not mutate shared state per move | `onContinuousHover` / `onHover` writing an `@Observable` property on every event | `rg -n 'onContinuousHover\|onHover' -A4 $SRC -g '*.swift'` | minor |
| N15 | One MetricKit subscription, forwarded to the single reporter, branched by deployment target | A second subscriber; `MXMetricManager` with no `#available(macOS 27, *)` branch where the target is 27+; `MetricManager` with a lower target | `rg -n 'MXMetricManager\|MetricManager\|MXMetricManagerSubscriber' $SRC -g '*.swift'` | major |
| N16 | Hangs are not hidden by a custom watchdog or swallowed by reporting | A watchdog that restarts the app or suppresses `MXHangDiagnostic` | `rg -n 'MXHangDiagnostic\|watchdog' $SRC -g '*.swift'` | minor |
| N17 | Performance is measured on a release build with a recorded figure | An optimisation commit with no before-and-after number; budgets undefined. requires dynamic test | read the change description and the release checklist | minor |
| N18 | Universal vs arm64-only is a recorded decision tied to the deployment target | A Universal binary at a 27 deployment target, or arm64-only with an Intel target and no reason | `rg -n 'ARCHS\|EXCLUDED_ARCHS\|ONLY_ACTIVE_ARCH\|MACOSX_DEPLOYMENT_TARGET' -g '*.xcconfig' -g '*.pbxproj'` | minor |

---

## O — Error resilience
*Owning skill: [`error-handling`](../../error-handling/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| O1 | A region is one `LoadState` with failed, stale and offline, not booleans | `isLoading` + `error` + `data` as separate properties; no `.stale` case | `rg -n 'var isLoading\|var errorMessage\|enum LoadState' $SRC -g '*.swift'` | major |
| O2 | No `try?` / empty `catch` turns a failure into empty | `try?` on a load assigned to `[]` / `nil`; `catch { }` | `rg -n 'try\? \|catch \{ *\}' $SRC -g '*.swift'` | major |
| O3 | No `try!`, force unwrap or `fatalError` for a recoverable condition | `try!` on a decode / request / XPC send; `!` on a server value | `rg -n 'try!\|fatalError\(\|[a-z\)]!\.' $SRC -g '*.swift'` | blocker |
| O4 | The failure is scoped to the response-dependent subtree: sidebar, toolbar, search and inspector keep working | An early `if case .failed … return`, or a `switch` wrapping the whole window, hiding the sidebar, toolbar or filters | `rg -n 'case \.failed' -B6 $SRC -g '*View*.swift'`; read the window's chrome | major |
| O5 | Every surfaced failure also raises the persistent inline banner | A failed region with no banner; or a banner with no inline region | `rg -n 'notifications\.raise\|Notifications' $SRC -g '*.swift'` | major |
| O6 | The banner is an inline `safeAreaInset` at the top of the window content, never auto-dismisses, closes only on its control | A `Task.sleep` / timer dismissing an error; a banner in an `overlay` over the table or in a sheet; no close control | `rg -n 'Banner' -A12 $SRC -g '*.swift'`; `rg -n 'safeAreaInset' $SRC -g '*.swift'` | major |
| O7 | No modal alert and no system notification for a failure the user did not cause | `NSAlert` / `.alert` for a background sync or fetch failure; a `UNNotificationRequest` for an error the user is looking at | `rg -n 'NSAlert\|runModal\|\.alert\(\|UNNotificationRequest' $SRC -g '*.swift'` | major |
| O8 | The banner is deduped, capped and rolled up by cause; one host per window, one raise-point per path | A banner per retry; more than three visible; a feature mounting its own toast | `rg -n 'raise\(' $SRC -g '*.swift'` | major |
| O9 | A timeout renders its own body; a cancelled request renders nothing | `.failed` set on `CancellationError` / `URLError.cancelled` (a closed window); no timeout body | `rg -n 'timedOut\|\.cancelled\|CancellationError' $SRC -g '*.swift'` | major |
| O10 | Offline is told apart from a server error and never retries | "Something went wrong" while `NWPath` is unsatisfied; a retry loop with no connectivity check | `rg -n 'isOnline\|NWPathMonitor' $SRC -g '*.swift'` | major |
| O11 | A failed refresh keeps the rows and marks them stale | A refresh command replacing the table with the failed body | `rg -n 'refreshable\|func reload\|func revalidate' -A8 $SRC -g '*.swift'` | major |
| O12 | Wake, reactivation and reconnect revalidate through the one load path, at the window root | No `didWakeNotification` / `scenePhase` handler; a handler duplicating the load; the same trigger in every leaf; old data shown as current | `rg -n 'didWakeNotification\|willSleepNotification\|scenePhase\|didBecomeActive' $SRC -g '*.swift'` | major |
| O13 | Several windows share one model; a write in one never leaves another on old data | Two `@State` copies of one fetch; a per-window cache of server data | `rg -n '@State .*: \[.*\] *=\|@State private var .*LoadState' $SRC -g '*.swift'` | major |
| O14 | A 401 runs the ladder (one refresh, one replay, in-place re-auth sheet); 403 is not 401; sign-out clears every window | Closing windows or navigating to login straight from a 401; sign-out on a 403 or a third-party 401; parallel refreshes; a second window keeping the last user's data | `rg -n '401\|forbidden\|403\|reauth\|signOut' $SRC -g '*.swift'` | major |
| O15 | An unsupported build shows the blocking prompt at the root of every window; the check fails open | No minimum-version check; a string comparison of versions; an update URL taken from the server; a window the prompt does not cover | `rg -n 'minimum\|CFBundleShortVersionString\|\.numeric\|SUUpdater\|SPUStandardUpdaterController' $SRC -g '*.swift'` | major |
| O16 | An update never restarts the app over unsaved work `[DevID]` | Sparkle relaunch with a dirty document and no save or confirmation; `updaterShouldRelaunchApplication` returning `true` unconditionally | `rg -n 'updaterShouldRelaunch\|SPUUpdaterDelegate\|installUpdatesIfAvailable' $SRC -g '*.swift'` | major |
| O17 | Writes disable while pending and carry one idempotency key per intent | An enabled submit or command during a request; a new `UUID()` per attempt | `rg -n 'UUID\(\)' -B3 $SRC -g '*.swift'`; `rg -n '\.disabled\(' $SRC -g '*.swift'` | major |
| O18 | An unknown write outcome is reconciled on relaunch, not reported as failed or dropped | A timeout shown as "failed"; a queued write lost on quit; a form cleared on failure | `rg -n 'unconfirmed\|timedOut\|applicationShouldTerminate' $SRC -g '*.swift'` | major |
| O19 | 409 / 412 is a decision; 422 lands on fields; bulk writes report per item | A conflict auto-retried; a 422 in the banner; "failed" for a partly applied batch | `rg -n '409\|412\|422\|conflict' $SRC -g '*.swift'` | major |
| O20 | A dead helper, XPC service or web content process is a scoped failed region | A window blank after the service exits; no reconnect action; a white `WKWebView` pane | `rg -n 'invalidationHandler\|cancellationHandler\|webViewWebContentProcessDidTerminate\|XPCRichError' $SRC -g '*.swift'` | major |
| O21 | A full disk degrades to memory with one notice; a secret is never downgraded to a weaker store | A blanket `catch` on a save; a token written to `UserDefaults` on Keychain failure | `rg -n 'fileWriteOutOfSpace\|StorageFull\|UserDefaults' $SRC -g '*.swift'` | major |
| O22 | A stale or revoked bookmark or denied container is an explained, recoverable state | `bookmarkDataIsStale` ignored; `startAccessingSecurityScopedResource()` result ignored; a blank list on denial; no Choose Folder… action | `rg -n 'bookmarkDataIsStale\|startAccessingSecurityScopedResource\|AccessLost' $SRC -g '*.swift'` | major |
| O23 | Third parties fail in their own region and never start the 401 ladder; optional SDKs initialise after the first window behind one adapter | A map, web or payment failure blanking the window; analytics failure shown to the user | `rg -n 'import (MapKit\|StoreKit\|WebKit\|Firebase\|Sentry)' $SRC -g '*.swift'` | major |
| O24 | A `404` on a record is "gone", not retryable; empty is three kinds | A retry button on a deleted record; one generic "No data" | `rg -n '404\|notFound\|ContentUnavailableView' $SRC -g '*.swift'` | minor |
| O25 | The UI never renders `localizedDescription`, a stack or a body | `Text(error.localizedDescription)` | `rg -n 'localizedDescription' $SRC -g '*.swift'` | major |
| O26 | Every state and the banner carry an `accessibilityIdentifier` | A loading / error / stale / empty body with none | `rg -n 'ProgressView\|ContentUnavailableView\|StaleMarker' -A4 $SRC -g '*.swift'` | minor |

---

## P — Localization
*Owning skill: [`languages`](../../languages/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| P1 | New strings live in a String Catalog; no new `.strings` or `.stringsdict` file | A `.strings` file created after the catalog exists; `Localizable.strings` extended by hand | `rg --files -g '*.strings' -g '*.stringsdict' -g '*.xcstrings'` | major |
| P2 | No hard-coded UI string once localization is on, and no sentence built by concatenation | Literal text with `+` outside `String(localized:)`; `Text(someString)` for UI copy; menu, window title, toolbar, tooltip, alert text unlocalized | `rg -n 'Text\("[^"]*" *\+\|NSLocalizedString\|\.alert\("[A-Z]\|\.help\("[A-Z]\|\.navigationTitle\("[A-Z]' $SRC -g '*.swift'` | major |
| P3 | Menus, commands, `Settings` tabs and window titles go through the catalog | `CommandMenu("…")` / `Button("…")` in `commands` / `Window("…")` built from a runtime `String` | `rg -n 'CommandMenu\(\|CommandGroup\|Window\("\|\.commands' -A4 $SRC -g '*.swift'` | major |
| P4 | Plurals and gendered wording are catalog variations, not `if count == 1` | `count == 1 ? "album" : "albums"`; a plural built from a pre-formatted string | `rg -n 'count == 1\|== 1 \?' $SRC -g '*.swift'` | major |
| P5 | Custom views take `LocalizedStringKey` / `LocalizedStringResource` for copy, and `Text(verbatim:)` marks data | A view with a `title: String` passed straight to `Text`; server data localized by accident | `rg -n "let title: String\|let message: String\|Text\(verbatim" $SRC -g '*.swift'` | minor |
| P6 | Layout uses leading / trailing, never left / right | `.padding(.left`, `Alignment.left`, `NSEdgeInsets(left:`, `.leftAnchor`, `.alignment = .left` in shared views | `rg -n '\.(left\|right)\b\|leftAnchor\|rightAnchor\|NSEdgeInsets\(' $SRC -g '*.swift'` | major |
| P7 | Dates, numbers and money use `FormatStyle`, not literals or per-row formatters | `DateFormatter()` / `NumberFormatter()` built in `body` or a `Table` cell; `"$\(price)"`; a hand-written display date pattern | `rg -n 'DateFormatter\(\)\|NumberFormatter\(\)\|"\$\\\(\|dateFormat =' $SRC -g '*.swift'` | major |
| P8 | The currency comes from data, never from the locale; money is not a `Double` | `Locale.current.currency` as the price currency; a `Double` price | `rg -n 'Locale.current.currency\|: Double.*price\|price: Double' $SRC -g '*.swift'` | major |
| P9 | Visible text sorts with `.localizedStandard`, not `<` | A `Table` / sidebar sorted by `<` on `String`; a `KeyPathComparator` on text with the default comparator | `rg -n 'KeyPathComparator\|sorted\(by: \{.*<\|\.sorted\(\)' $SRC -g '*.swift'` | minor |
| P10 | Purpose strings and the display name are localized in `InfoPlist.xcstrings` | Only an English `Info.plist` purpose string in an app with several localizations | `rg --files -g 'InfoPlist.xcstrings' -g 'InfoPlist.strings'`; compare with `rg -n "NS[A-Za-z]*UsageDescription" -g 'Info.plist'` | major |
| P11 | A shipped language has a complete catalog; none is half-translated | *New* / *Needs Review* entries in a language listed in the project's Localizations | open the catalog's per-language progress; `rg -n '"state" : "(new\|needs_review)"' -g '*.xcstrings'` | minor |
| P12 | Fixed-format dates use a POSIX locale or ISO 8601; user-visible dates do not | `DateFormatter` with `dateFormat` and no `en_US_POSIX` for an API value; an ISO string shown to the user | `rg -n 'dateFormat\|ISO8601' -B2 $SRC -g '*.swift'` | minor |
| P13 | No in-app language picker unless a recorded reason says so | A custom language switcher overriding `Bundle` or `AppleLanguages` | `rg -n 'AppleLanguages\|Bundle.setLanguage\|\.environment\(\\\.locale' $SRC -g '*.swift'` | minor |
| P14 | Window layouts survive RTL and double-length text | A fixed-width label or toolbar item that truncates a primary action; a window minimum size that ignores longer text. requires dynamic test (pseudolanguage run) | `rg -n 'frame\(width:\|minimumScaleFactor\|lineLimit' $SRC -g '*.swift'` | minor |

---

## R — Testability & test ids
*Owning skill: [`test-ids`](../../test-ids/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| R1 | Every interactive element carries an `accessibilityIdentifier` (Mac2 `accessibility id` = `identifier`) | A `Button`, `TextField`, `SecureField`, `Toggle`, `Picker`, sidebar item or toolbar control with no identifier | `rg -n '\b(Button\|TextField\|SecureField\|Toggle\|Picker\|NavigationLink)\b' $SRC -g '*.swift'` against `rg -n 'accessibilityIdentifier' $SRC -g '*.swift'`; read per view | major |
| R2 | Every list, table and outline container carries an identifier | A `Table`, `List`, `OutlineGroup`, `LazyVGrid` or `NSTableView` / `NSOutlineView` with none | `rg -n '\bTable\b\|\bList\b\|OutlineGroup\|LazyVGrid\|NSTableView\|NSOutlineView' $SRC -g '*.swift'` | major |
| R3 | The id is `accessibilityIdentifier`, never the accessibility label | `.accessibilityLabel("Library.SearchField")`; a label string reused as the identifier | `rg -n 'accessibilityLabel\("[A-Z][A-Za-z]*\.[A-Z]' $SRC -g '*.swift'` | major |
| R4 | Ids are PascalCase dot-separated | `library-search`, `library_search`, `librarySearch`, spaces | `rg -n 'accessibilityIdentifier\("[^"]*[-_ ][^"]*"\|accessibilityIdentifier\("[a-z]' $SRC -g '*.swift'` | minor |
| R5 | Ids are static: no row id, GUID, index, window number or state value | `"Row.\(album.id)"`, `"Item\(index)"`, `"Window\(n).Add"`, `"Tab.\(selected)"` | `rg -n 'accessibilityIdentifier\(".*\\\(' $SRC -g '*.swift'`; read each: a prefix or enum-case interpolation is allowed, a model id, index or window number is not | major |
| R6 | List and table rows share one locator namespace and are addressed by index | A row identifier built from the row's id; children not namespaced under the row id | `rg -n 'accessibilityIdentifier' -B3 $SRC -g '*Row*.swift' -g '*Cell*.swift'` | major |
| R7 | Region states and the inline banner are tagged | A region with `Loading` / `Error` / `Empty` / `Retry` states and no ids on them; the banner and its close untagged | `rg -n 'ProgressView\|ContentUnavailableView\|Retry' $SRC -g '*.swift'` and `rg -n 'accessibilityIdentifier' -g '*Banner*.swift'` | major |
| R8 | Reusable views compose a prefix; no wrapper exists only to carry ids | A `testIdPrefix` ignored by a terminal view; an `AppButton` that only adds an identifier | `rg -n 'testIdPrefix\|struct App(Button\|Field)' $SRC -g '*.swift'` | minor |
| R9 | Decorative and layout views are not tagged | An identifier on a `Spacer`, a plain `VStack` or a decorative image | `rg -n 'accessibilityIdentifier' -B2 $SRC -g '*.swift'`; read the host view | nit |
| R10 | Grouping does not hide tagged children; a container id does not replace a leaf id | `.accessibilityElement(children: .combine)` over views whose child ids tests need; a container id with unnamed children | `rg -n 'accessibilityElement\(children' -A8 $SRC -g '*.swift'`; confirm in a Mac2 page source — requires dynamic test → `qa-desktop-<lang>` | major |
| R11 | Each window has a root container id, so a test scopes by window and then id | A multi-window app whose windows expose no anchor; a window number encoded into ids | `rg -n 'WindowGroup\|Window\(' -A6 $SRC -g '*.swift'` against `rg -n 'accessibilityIdentifier' -g '*Window*.swift'` | minor |
| R12 | `[AppKit]` AppKit controls set the identifier in setup, on the control, not the label | An `NSButton` / `NSTextField` / `NSTableView` with no `setAccessibilityIdentifier`; a cell setting it on the wrong view | `rg -n 'NSButton\|NSTextField\|NSTableView\|NSOutlineView\|NSSearchField' $SRC -g '*.swift'` against `rg -n 'setAccessibilityIdentifier\|accessibilityIdentifier =' $SRC -g '*.swift'` | major |

---

## S — Dev-side tests
*Owning skill: [`unit-testing`](../../unit-testing/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| S1 | Swift Testing is used for new tests; XCTest only for UI automation, performance and Objective-C exceptions | New `XCTestCase` for pure logic in a project that has Swift Testing | `rg -n 'XCTestCase' $SRC -g '*Tests*.swift'` | minor |
| S2 | No mixed assertion frameworks in one test | `XCTAssert*` inside a `@Test`; `#expect` inside an `XCTestCase` | `rg -n 'XCTAssert' $SRC -g '*.swift' -l` against `rg -n '@Test' -l` | major |
| S3 | A test body contains no `do`/`catch`; errors are asserted with `#expect(throws:)` | `do { try … } catch { … }` in a `@Test` | `rg -n 'do \{\|catch' $SRC -g '*Tests*.swift'` | major |
| S4 | No `if` / `for` / `switch` drives assertions; variants are `@Test(arguments:)` | A loop of `#expect`s; a conditional assertion | `rg -n '^\s*(if\|for\|switch) ' $SRC -g '*Tests*.swift'` | major |
| S5 | Every assertion states one expected value | `#expect(x == a \|\| x == b)`; `#expect(code == 200 \|\| code == 204)` | `rg -n '#expect\(.*\|\|' $SRC -g '*Tests*.swift'` | major |
| S6 | No `Task.sleep`, `sleep` or `DispatchQueue` timing in a test | Waiting on wall-clock time; polling | `rg -n 'Task\.sleep\|sleep\(\|asyncAfter' $SRC -g '*Tests*.swift'` | major |
| S7 | Time, identity, randomness, config, I/O and the workspace (wake, activation) are initializer-injected; no protocol created only for a test | `Date()` / `UUID()` read inside the unit; a model reading `NSWorkspace.shared` itself; a one-conformer `protocol …Protocol` | `rg -n 'Date\(\)\|UUID\(\)\|\.random\|NSWorkspace\.shared' $SRC -g '*.swift'`; `rg -n 'protocol .*Protocol' $SRC -g '*.swift'` | major |
| S8 | Network tests use a `URLProtocol` stub on an ephemeral session, never `URLSession.shared` or a live host | `URLSession.shared` / a real URL in a test | `rg -n 'URLSession\.shared\|https?://' $SRC -g '*Tests*.swift'` | blocker |
| S9 | Unit tests never touch `UserDefaults.standard`, the real Keychain, `NSOpenPanel` or the user's folders | `UserDefaults.standard` or a path under `~` in a test; a panel opened in a test | `rg -n 'UserDefaults\.standard\|NSOpenPanel\|homeDirectory\|SecItem' $SRC -g '*Tests*.swift'` | major |
| S10 | Fakes over mocks: assertions are on outcomes, not call order | A hand-rolled mock asserting invocation counts and order | `rg -n 'callCount\|wasCalled\|verify' $SRC -g '*Tests*.swift'` | minor |
| S11 | Tests are independent: no shared mutable state, no `.serialized` hiding one | A static array mutated across tests; `.serialized` on a suite with no shared resource | `rg -n 'static var\|\.serialized' $SRC -g '*Tests*.swift'` | major |
| S12 | Test names state behaviour; test data comes from builders for four or more fields | `func test1`, `works`; the same large literal in several tests | `rg -n '@Test\("' -c $SRC -g '*Tests*.swift'`; `rg -n 'func test[0-9]' $SRC -g '*Tests*.swift'` | minor |
| S13 | No force unwrap or `try!` in a test beyond a fixed fixture literal; `#require` for preconditions | `try!`, `.first!` | `rg -n 'try!\|\.first!\|\.last!' $SRC -g '*Tests*.swift'` | minor |
| S14 | Snapshots cover single views only, never a whole window or dynamic content | `assertSnapshot` on a root window view; a date in the frame | `rg -n 'assertSnapshot' $SRC -g '*Tests*.swift'` | minor |
| S15 | Migration tests use an on-disk store; an in-memory store is not offered as migration proof | `isStoredInMemoryOnly: true` in a `SchemaMigrationPlan` test | `rg -n 'isStoredInMemoryOnly\|SchemaMigrationPlan' $SRC -g '*Tests*.swift'` | major |
| S16 | Unit tests run on the host without launching the app UI; no journeys are written as unit tests | `XCUIApplication` in the unit plan; a test needing a window. requires dynamic test → `qa-desktop-<lang>` | `rg -n 'XCUIApplication\|NSApplication\.shared\.run' $SRC -g '*Tests*.swift'` | minor |
| S17 | Two windows over one model are tested as two consumers of one model, not by creating windows | A test that opens `NSWindow`s to prove consistency | `rg -n 'NSWindow\(\|NSHostingController' $SRC -g '*Tests*.swift'` | minor |

---

## U — Observability & logging
*Owning fragment: [`desktop/_shared/observability`](../../../../_shared/observability/references/audit-checks.md)*

This section holds no rows of its own. The rows are those of `desktop/_shared/observability/references/audit-checks.md` whose `Platforms` column names `macos`, and the ids are the fragment's — finding `U3` is row U3 of the observability fragment. A row a static read cannot prove says **requires dynamic test → `qa-security`** and is reported as unverified, never as passed.

---

## V — Comments & KISS
*Owning skills: [`engineering-practices/code-comments`](../../../../../engineering-practices/code-comments/SKILL.md) · CLAUDE.md § Comments and § Simplicity (KISS)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| V1 | No inline comments in a body | A `//` line inside a function or method body — a step marker, a restatement of the next line, a section banner | `rg -n "^\s+//[^/!]" $SRC -g '*.swift'` | minor |
| V2 | A doc comment states a contract, not the signature | A doc comment that restates the name or signature (`Returns the user id`) on a property, DTO, getter or single-expression function | `rg -n -A1 "^\s*/// (Returns\|Gets\|Sets) " $SRC -g '*.swift'` | minor |
| V3 | No commented-out code, no `TODO` / `FIXME` left behind | A `//` line holding code, or a `TODO` / `FIXME` / `HACK` marker in committed source | `rg -n "^\s*//\s*(let\|var\|func\|import\|return\|if\|await\|guard)\b" $SRC -g '*.swift'` · `rg -n "TODO\|FIXME\|HACK" $SRC -g '*.swift'` | minor |
| V4 | A comment that exists because the code is unclear | A comment explaining what a badly named local or method does — the fix is the rename or extraction, not a reworded comment | Read the comment hits from V1; ask whether a name would carry it | major |
| V5 | No `protocol` with one conformer | An abstraction introduced for one caller and one implementation, with no second real need | `rg -n "^(public \|internal )?protocol \w+" $SRC -g '*.swift'`; then count implementers per hit | major |
| V6 | No wrapper that only forwards | A class or function whose whole body delegates one call to the next layer (service → repository → store as three layers) | `rg -n -A2 "func \w+\(.*\) .*\{$" $SRC -g '*.swift'`; read each hit for a single delegated call | major |
| V7 | No configurability nothing uses | An options bag, flag, generic parameter or extension point that no caller passes or varies | `rg -n "configuration:\|options:\|\bconfig\b" $SRC -g '*.swift'`; then search for a call site that supplies it | major |
| V8 | A generated or scaffolded comment is removed | A template header (`Created by … on …`), a framework placeholder comment or a wizard banner left in a source file, with no tool depending on it | `rg -n "Created by\|Generated by\|This file was\|Copyright \(c\)" $SRC -g '*.swift'` — skip generated sources | minor |

---

## X — Interop & native code
*Owning skills: none — not applicable on macOS*

This section is not applicable on macOS: there is no P/Invoke, COM or C++/WinRT lane. The letter stays reserved so the audits compare across platforms.

---

## Section index

| § | Section | Rows | Owner |
|---|---|---|---|
| A | Version lane, toolchain & migration hygiene | A1–A9 | `project-setup`, `migration`, `basics` |
| B | Project structure, strictness & language standard | B1–B17 | `project-setup`, `basics` |
| C | Architecture, state & DI | C1–C10 | `architecture` |
| D | UI components & platform conventions | D1–D20 | `ui-components`, `appkit` |
| E | Styling, theming, motion & adaptive layout | E1–E13 | `styling` |
| F | Windows, navigation & commands | F1–F15 | `windows-and-scenes`, `menus-and-commands` |
| G | Forms & input | G1–G12 | `forms` |
| H | Networking & realtime | H1–H15 | `networking` |
| I | Storage, documents & sync | I1–I20 | `offline-and-storage`, `documents` |
| J | Platform integration, permissions & background | J1–J27 | `sandbox-and-permissions`, `background-and-helpers`, `system-integration` |
| K | Security | fragment | `desktop/_shared/security` |
| L | Distribution & store compliance | fragment | `desktop/_shared/distribution` |
| M | Accessibility | M1–M17 | `accessibility` |
| N | Performance | N1–N18 | `performance` |
| O | Error resilience | O1–O26 | `error-handling` |
| P | Localization | P1–P14 | `languages` |
| R | Testability & test ids | R1–R12 | `test-ids` |
| S | Dev-side tests | S1–S17 | `unit-testing` |
| U | Observability & logging | fragment | `desktop/_shared/observability` |
| V | Comments & KISS | V1–V8 | `engineering-practices/code-comments`, CLAUDE.md § Simplicity |
| X | Interop & native code | N/A | none on macOS |

Sections Q (motion) and T (release) are unused: motion is in E, release in L. Fragment sections hold the rows of their `audit-checks.md` whose `Platforms` column names `macos`.
