# mobile-ios Conformance Checklist — the 23 sections

The audit's spine. Section letters and check numbers are **permanent** — a finding is `<letter><n>` (`B3`, `M1`) and keeps that ID across every round, forever. Never renumber; append new checks at the end of a section with the next free number. The letters are identical on all three mobile stacks (`react-native`, `ios`, `android`): `M` is Accessibility everywhere.

**How to read a row.** *Check* = the invariant. *Violation looks like* = what disqualifies it. *Find it with* = a mechanical lead (a grep hit is never a finding — read the code). *Sev* = the default severity; adjust for real impact and say why.

**Recipes** use `rg` (ripgrep), which honours `.gitignore` — so `.build/`, `Pods/`, `Carthage/`, `DerivedData/` and `*.xcodeproj` contents when ignored are skipped without flags. Without ripgrep, `grep -rn --include='*.swift' --exclude-dir=.build --exclude-dir=Pods --exclude-dir=Carthage` is equivalent. Set the source roots once:

```bash
SRC=$(ls -d Sources App *App* 2>/dev/null | tr '\n' ' ')   # adjust to the repo layout
rg -n "<pattern>" $SRC -g '*.swift'                      # the shape every recipe below uses
```

If the repo gitignores generated sources (R.swift, Sourcery, SwiftGen output) you still need to read, add `--no-ignore` and exclude it explicitly — and say so in the report's coverage line.

**The version lane gates everything.** Before flagging, confirm the check applies to the detected Xcode / Swift language mode (Swift 6 primary, Swift 5-mode supported), the deployment target (iOS 17 primary, iOS 16 supported) and whether the UI is SwiftUI or UIKit. Rows tagged **[iOS17+]**, **[Swift6]** and **[UIKit]** apply only in that lane.

**Fragment sections.** K, L, T, U and X carry no rows here: their rows live in `mobile/_shared/<skill>/references/audit-checks.md` and are filtered by the `Stacks` column. Every other section is filled by the task that writes its skill — an empty section means that skill is not written yet, not that the code passes.

**Severity.** blocker — ships a crash, a store rejection, or a hard security rule break. major — a rule in CLAUDE.md § Mobile code rules broken where it will hurt soon. minor — style, naming, a single missing label. nit — preference.

---

## A — Version lane, toolchain & migration hygiene
*Owning skills: [`project-setup`](../../project-setup/SKILL.md) · [`migration`](../../migration/SKILL.md) · [`basics`](../../basics/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| A1 | Swift language mode is declared, and is Swift 6 for new modules `[Swift6]` | A new module or package with `SWIFT_VERSION = 5.0` / no `swiftLanguageModes`; a Swift 5 module raised to 6 as a side effect of other work | `rg -n "SWIFT_VERSION\|swiftLanguageModes\|swift-tools-version" -g '*.pbxproj' -g '*.xcconfig' -g 'Package.swift'` | major |
| A2 | Default actor isolation matches the module kind | An app or UI module left `nonisolated` with `@MainActor` scattered on every type, or a **library package** with `MainActor` default isolation | `rg -n "SWIFT_DEFAULT_ACTOR_ISOLATION\|defaultIsolation" -g '*.pbxproj' -g '*.xcconfig' -g 'Package.swift'`; read each target's kind | major |
| A3 | Approachable Concurrency is a stated choice, not assumed | Code relying on `nonisolated async` running on the caller's actor in a module without `SWIFT_APPROACHABLE_CONCURRENCY` / `NonisolatedNonsendingByDefault` | `rg -n "APPROACHABLE_CONCURRENCY\|NonisolatedNonsendingByDefault\|InferIsolatedConformances" -g '*.pbxproj' -g '*.xcconfig' -g 'Package.swift'`; then `rg -n "nonisolated .*async" $SRC -g '*.swift'` | minor |
| A4 | Newer-than-target APIs carry availability `[iOS17+]` | `@Observable` on an iOS 16 target, `Observations` below iOS 26, a Swift 6.4-only construct on a 6.2 toolchain, with no `#available` / `@available` | `rg -n "@Observable\|Observations\b\|weak let" $SRC -g '*.swift'`; compare with the deployment target | major |
| A5 | `ObservableObject` on an iOS 17+ target is a migration finding, not new code `[iOS17+]` | `ObservableObject` / `@Published` / `@StateObject` in new code where the target is iOS 17+ | `rg -n "ObservableObject\|@Published\|@StateObject\|@ObservedObject" $SRC -g '*.swift'` | major |
| A6 | New app and module settings state Swift 6 mode explicitly, not the template's `5.0` `[Swift6]` | A target created from the Xcode 27 template still on `SWIFT_VERSION = 5.0` with no migration note; no `SWIFT_VERSION` set in the xcconfig | `rg -n "SWIFT_VERSION = 5" -g '*.pbxproj' -g '*.xcconfig'` | major |
| A7 | Warnings are errors in the app and every package `[Swift6]` | `SWIFT_TREAT_WARNINGS_AS_ERRORS` absent or `NO`; a package with no `treatAllWarnings(as: .error)` | `rg -n "TREAT_WARNINGS_AS_ERRORS\|treatAllWarnings" -g '*.pbxproj' -g '*.xcconfig' -g 'Package.swift'` | major |
| A8 | Deployment target is stated once per module and matches the lane | `IPHONEOS_DEPLOYMENT_TARGET` differing between app and packages with no reason; raised as a side effect of other work | `rg -n "IPHONEOS_DEPLOYMENT_TARGET\|platforms:" -g '*.pbxproj' -g '*.xcconfig' -g 'Package.swift'` | major |
| A9 | The iOS 27 SDK's mandatory pieces are in place: scene lifecycle and a launch screen | An app with window setup in the app delegate and no `UIApplicationSceneManifest`; no `UILaunchScreen` / launch storyboard | `rg -n "UIApplicationSceneManifest\|UILaunchScreen\|UILaunchStoryboardName\|UIWindowSceneDelegate" -g 'Info.plist' -g '*.pbxproj' -g '*.swift'` | major |
| A10 | No CocoaPods in a new project; an existing `Podfile` has a dated move to SPM | A `Podfile` in a new project, or one with no plan before the 2026-12-02 trunk freeze | `ls Podfile Podfile.lock Pods 2>/dev/null` | major |
| A11 | `PreviewProvider` is not used in new code | A new `PreviewProvider` where `#Preview` works | `rg -n "PreviewProvider" $SRC -g '*.swift'` | minor |

---

## B — Project structure, strictness & language standard
*Owning skills: [`project-setup`](../../project-setup/SKILL.md) · [`basics`](../../basics/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| B1 | No force unwrap outside tests | `value!`, `as!` or `try!` in app or module source | `rg -n "\w!\.\|\w!\)\|\w!$\|as!\|try!" $SRC -g '*.swift' -g '!*Tests*'` — read each hit; `!=` and `!` negation are not findings | blocker |
| B2 | No implicitly unwrapped optional outside an `@IBOutlet` | `var x: T!` for a dependency or model property | `rg -n "(var\|let) \w+: [\w<>\[\]]+!" $SRC -g '*.swift'` | major |
| B3 | No `@unchecked Sendable` or `nonisolated(unsafe)` without a written justification | The hatch with no stated invariant on its declaration | `rg -n -B2 "@unchecked Sendable\|nonisolated\(unsafe\)" $SRC -g '*.swift'` | major |
| B4 | No `print`, `NSLog`, `debugPrint` or `dump` | A debugging call left in source | `rg -n "\b(print\|NSLog\|debugPrint\|dump)\(" $SRC -g '*.swift'` | minor |
| B5 | `os.Logger` messages interpolate values with a privacy level, and log no secret | A `Logger` call building its message with `String(describing:)` or concatenation; a token, email or URL with a query logged `.public` | `rg -n "Logger\|logger\.\w+\(" $SRC -g '*.swift'`; read the interpolations | major |
| B6 | No empty `catch`, no `try?` hiding a failure the user must see | `catch { }`, or `try?` whose failure leaves the UI in a success state | `rg -n "catch \{ *\}\|try\?" $SRC -g '*.swift'` | major |
| B7 | `CancellationError` is not shown as a failure | A blanket `catch` setting a `failed` state with no `catch is CancellationError` | `rg -n -A4 "\} catch \{" $SRC -g '*.swift'` | major |
| B8 | No blocking on async work | `DispatchSemaphore`, `.wait()`, `RunLoop.current.run` or a sleep loop bridging async code | `rg -n "DispatchSemaphore\|\.wait\(\)\|RunLoop\.current\.run" $SRC -g '*.swift'` | blocker |
| B9 | No GCD main-queue hops in new code | `DispatchQueue.main.async` where `@MainActor` or `await MainActor.run` fits | `rg -n "DispatchQueue\.(main\|global)" $SRC -g '*.swift'` | minor |
| B10 | No `Task.detached` without a written reason; CPU work uses `@concurrent` `[Swift6]` | `Task.detached` used to leave the main actor | `rg -n "Task\.detached" $SRC -g '*.swift'` | major |
| B11 | Unstructured `Task { }` in a view is cancelled with the view | `Task { }` in `onAppear` or `body` with no stored handle; `.task` not used | `rg -n "Task \{" $SRC -g '*.swift'`; read the enclosing view | major |
| B12 | Library packages are not `@MainActor` by blanket | `MainActor` default isolation on a package, or `@MainActor` on a non-UI package type | `rg -n "@MainActor" $SRC -g '*.swift'` under package targets | major |
| B13 | No mutable global state | `static var` or a global `var` holding mutable state | `rg -n "^\s*(static )?var \w+" $SRC -g '*.swift'` at type or file scope | major |
| B14 | Access control is the narrowest that works | `public` on an app-target type; a package type `public` with no external caller; a non-`final` class with no subclass | `rg -n "^\s*(public\|open) " $SRC -g '*.swift'` | minor |
| B15 | Value types by default | A `class` holding plain data with no identity, `deinit` or sharing need | `rg -n "^\s*(final )?class \w+" $SRC -g '*.swift'`; read each hit | minor |
| B16 | A callback-to-async continuation resumes exactly once | A `withChecked(Throwing)Continuation` path that does not resume, or resumes twice | `rg -n -A12 "withChecked(Throwing)?Continuation" $SRC -g '*.swift'` | major |
| B17 | Each environment has its own xcconfig; no `#if` environment branching in features | A single configuration with API URLs hard-coded, or `#if STAGING` in feature code | `rg -n "#if (STAGING\|PROD\|DEV)" $SRC -g '*.swift'`; `ls Config/*.xcconfig` | major |
| B18 | No secret in an xcconfig, `Info.plist` or committed plist | An API secret, private key or token value in a committed config file | `rg -n -i "secret\|api[_-]?key\|token\|password" -g '*.xcconfig' -g 'Info.plist' -g '*.plist'` — requires dynamic test → `qa-security` for what the binary leaks | blocker |
| B19 | A formatter and a linter are committed and agree | No `.swift-format`; no `.swiftlint.yml`; SwiftLint left to format whitespace | `ls .swift-format .swiftlint.yml` | minor |
| B20 | Modules are local packages with one-way dependencies | A feature importing another feature's internals; a `Common` / `Utils` module every target imports; a package depending on the app | `rg -n "dependencies:\|\.package\(" -g 'Package.swift'` | major |
| B21 | Test plans exist and the shared scheme references them | No `.xctestplan`; a package test target absent from every plan | `ls TestPlans/*.xctestplan`; `rg -n "testPlans" -g '*.xcscheme'` | minor |
| B22 | `PrivacyInfo.xcprivacy` exists in the app target and in each package that uses a Required Reason API | No manifest, or a package calling `UserDefaults` / file-timestamp / disk-space APIs with none | `fd PrivacyInfo.xcprivacy`; `rg -n "UserDefaults\|systemUptime\|NSFileCreationDate\|volumeAvailableCapacity" $SRC -g '*.swift'` | major |
| B23 | A String Catalog exists and literals extract to it | No `.xcstrings`; `LOCALIZATION_PREFERS_STRING_CATALOGS` absent | `fd -e xcstrings`; `rg -n "LOCALIZATION_PREFERS_STRING_CATALOGS" -g '*.pbxproj' -g '*.xcconfig'` | minor |
| B24 | Generated projects are edited through the manifest `[Tuist]` | A hand edit in a `.pbxproj` that `Project.swift` / `project.yml` regenerates | `git log --stat -- '*.pbxproj'` on a repo with `Project.swift` | major |

---

## C — Architecture, state & DI
*Owning skill: [`architecture`](../../architecture/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| C1 | No `ObservableObject`-style ownership in iOS 17+ code: an `@Observable` is created with `@State` `[iOS17+]` | An `@Observable` held in a plain `let` / `var` created in `body`; `@StateObject` on an `@Observable` | `rg -n "@Observable" $SRC -g '*.swift'`; read how each is instantiated | major |
| C2 | One owner per model | `@State` on a model passed in from a parent; two views each creating the same model | `rg -n "@State (private )?var \w+: \w+(Model\|Store)" $SRC -g '*.swift'`; read for `init` parameters | major |
| C3 | `@Bindable` for bindings into an `@Observable`; `@Binding` only for values `[iOS17+]` | `@Binding` carrying an `@Observable`; a `Binding(get:set:)` hand-built over a model property | `rg -n "Binding\(get:\|@Binding" $SRC -g '*.swift'` | minor |
| C4 | Every view model is earned | An `XViewModel` that only mirrors a struct, forwards one call, or has no test or second user | `rg -n "class \w+(ViewModel\|Model)\b" $SRC -g '*.swift'`; for each, find its test and its users | major |
| C5 | Dependencies arrive by initializer or `@Environment` from the composition root | A singleton (`.shared`), service locator, or `static let` client used inside a view or model | `rg -n "\.shared\b\|ServiceLocator\|Container\.(resolve\|shared)" $SRC -g '*.swift'` | major |
| C6 | No DI container library where the codebase did not choose one | Factory / Swinject / Needle added to a project that used `init` injection | `rg -n "Factory\|Swinject\|Needle" -g 'Package.swift' -g 'Package.resolved' -g 'Podfile'` | major |
| C7 | No `protocol` with a single conformer in the architecture layer | A `FooProtocol` / `FooServicing` with one implementation and no test fake | `rg -n "^(public \|internal )?protocol \w+" $SRC -g '*.swift'`; count conformers | major |
| C8 | No I/O, formatter construction or sorting in `body` | A network call, `DateFormatter()`, decode or large `sorted` / `filter` inside `body` | `rg -n -A12 "var body: some View" $SRC -g '*.swift'`; read for the calls | major |
| C9 | Load state is one enum | `isLoading` + `error` + `isEmpty` booleans on a model | `rg -n "var isLoading\|var isEmpty\|var error: " $SRC -g '*.swift'` | minor |
| C10 | TCA / Factory / swift-dependencies appear only where the codebase already uses them `[TCA]` | A new feature in a non-TCA codebase using `ComposableArchitecture` | `rg -n "import ComposableArchitecture\|import Dependencies" $SRC -g '*.swift'` | major |

---

## D — UI components & platform conventions
*Owning skills: [`ui-components`](../../ui-components/SKILL.md) · [`uikit`](../../uikit/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| D1 | Async work starts in `.task`, not `Task { }` in `onAppear` | `.onAppear { Task { … } }` or a load in `init` | `rg -n "onAppear" -A3 $SRC -g '*.swift'`; `rg -n "Task \{" $SRC -g '*.swift'` | major |
| D2 | `.task(id:)` for loads keyed on input | A search / filter reload via `onChange` + `Task` | `rg -n "onChange\(of" -A4 $SRC -g '*.swift'` | minor |
| D3 | Each data region renders loading, loaded, empty and failed, scoped to the region | A `switch` / `if` missing the failed or empty case; a failure replacing the whole screen including search or toolbar | `rg -n "LoadState\|case \.failed\|case \.loading" $SRC -g '*.swift'`; read each region | major |
| D4 | A drifted or undecodable response is failed, not empty | `try?` / `?? []` on a decode that renders as an empty list | `rg -n "try\? .*decode\|\?\? \[\]" $SRC -g '*.swift'` | major |
| D5 | Framework or server error text is never shown to the user | `Text(error.localizedDescription)` | `rg -n "localizedDescription" $SRC -g '*.swift'` | major |
| D6 | Lists use stable domain ids | `id: \.self` on non-stable values, `ForEach(0..<n)`, `\.offset` | `rg -n "id: \\\.self\|ForEach\(0\.\.<\|\.enumerated\(\)" $SRC -g '*.swift'` | major |
| D7 | Long content is `List` or a lazy stack | A `VStack` / `HStack` inside `ScrollView` over an unbounded collection | `rg -n "ScrollView" -A4 $SRC -g '*.swift'`; read for `ForEach` over a collection | major |
| D8 | System icons come from SF Symbols; custom assets only without a symbol | Raster icons for common actions | `rg -n "Image\(\"" $SRC -g '*.swift'` | minor |
| D9 | `#Preview` exists for reusable views and covers states; none uses live data | A view with no preview, or one that calls the network | `rg -L "#Preview" $SRC -g '*View.swift'` | minor |
| D10 | No `AnyView`, no `GeometryReader` as a default layout tool | `AnyView` erasing a conditional; `GeometryReader` for plain sizing | `rg -n "AnyView\|GeometryReader" $SRC -g '*.swift'` | minor |
| D11 | Standard controls, not imitations of another platform | A custom tab bar, back button, switch or alert drawn to look like Material or web | `rg -n "ZStack" -B2 -A6 $SRC -g '*TabBar*.swift'`; read custom control views | major |

---

## E — Styling, theming & adaptive layout
*Owning skill: [`styling`](../../styling/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| E1 | Liquid Glass is not opted out of | `UIDesignRequiresCompatibility` set, or advice to set it | `rg -n "UIDesignRequiresCompatibility" -g 'Info.plist' -g '*.pbxproj' -g '*.xcconfig'` | major |
| E2 | No custom background fights a system bar or tab bar | `toolbarBackground`, `UINavigationBarAppearance` or a material stacked behind a system bar; a custom `ZStack` tab bar | `rg -n "toolbarBackground\|UINavigationBarAppearance\|UITabBarAppearance\|ultraThinMaterial" $SRC -g '*.swift'` | major |
| E3 | Custom glass is grouped, sparing and has a fallback where the target is below iOS 26 | `glassEffect` on content rows; adjacent glass views not in a `GlassEffectContainer`; no `#available` fallback on a lower target | `rg -n "glassEffect\|GlassEffectContainer\|\.glass" $SRC -g '*.swift'` | minor |
| E4 | Text uses text styles, not fixed sizes | `.font(.system(size: …))` or `UIFont.systemFont(ofSize:)` with no scaling | `rg -n "\.system\(size:\|systemFont\(ofSize" $SRC -g '*.swift'` | major |
| E5 | A custom font scales with Dynamic Type | `Font.custom("X", fixedSize:)`, or `custom(_, size:)` with no `relativeTo:` | `rg -n "Font\.custom\|\.custom\(\"" $SRC -g '*.swift'` | major |
| E6 | Layout survives accessibility sizes: no `lineLimit(1)` on primary content, no fixed-height text containers | `lineLimit(1)` on a title or message; `.frame(height:)` on text | `rg -n "lineLimit\(1\)\|\.frame\(height:" $SRC -g '*.swift'` | major |
| E7 | Dynamic Type is not capped except on dense chrome, with a recorded reason | `.dynamicTypeSize(...)` limiting content | `rg -n "dynamicTypeSize\(" $SRC -g '*.swift'` | major |
| E8 | Brand colours are asset-catalog colour sets with dark variants; no hex in views | `Color(red:green:blue:)` or a hex initializer in a view | `rg -n "Color\(red:\|Color\(hex\|UIColor\(red:\|0x[0-9A-Fa-f]{6}" $SRC -g '*.swift'` | minor |
| E9 | State is never conveyed by colour alone | A red / green indicator with no symbol or text; `accessibilityDifferentiateWithoutColor` never read | `rg -n "\.foregroundStyle\(\.(red\|green)\)\|differentiateWithoutColor" $SRC -g '*.swift'` | major |
| E10 | Layout branches on size class, never on device idiom | `UIDevice.current.userInterfaceIdiom`, `UIScreen.main.bounds` in a view | `rg -n "userInterfaceIdiom\|UIScreen\.main" $SRC -g '*.swift'` | major |
| E11 | iPad windows are resizable: no `UIRequiresFullScreen`, no fixed orientation assumptions | `UIRequiresFullScreen = YES`; a layout reading a fixed screen width | `rg -n "UIRequiresFullScreen\|UISupportedInterfaceOrientations" -g 'Info.plist' -g '*.pbxproj'` | major |
| E12 | Touch targets are at least 44 pt | A tappable control smaller than 44 pt with no `contentShape` / minimum frame | `rg -n "\.frame\(width: [0-9]{1,2}, height: [0-9]{1,2}\)" $SRC -g '*.swift'`; read each hit | major |

---

## F — Navigation & deep links
*Owning skills: [`navigation`](../../navigation/SKILL.md) · [`notifications-and-links`](../../notifications-and-links/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| F1 | No `NavigationView` or `NavigationLink(destination:)` in new code | `NavigationView { }`; `NavigationLink(destination: Detail())` | `rg -n "NavigationView\|NavigationLink\(destination" $SRC -g '*.swift'` | major |
| F2 | Routes are typed `Hashable` values carrying ids, not models | A route case holding a model object or closure | `rg -n "enum \w+Route\|navigationDestination\(for:" $SRC -g '*.swift'`; read each case | major |
| F3 | `navigationDestination(for:)` is declared once per type at the stack root | A destination declared inside a `List` row or lazily built view; two registrations of one type | `rg -n "navigationDestination\(for" -B3 $SRC -g '*.swift'` | major |
| F4 | In-app navigation is a `NavigationLink(value:)`, not a `Button` that mutates a path | A `Button { path.append(…) }` for a plain tap-to-open row | `rg -n "path\.append\|\.navigate" -B3 $SRC -g '*.swift'` | minor |
| F5 | Each tab owns its `NavigationStack`; selection is an enum | One `NavigationStack` wrapping a `TabView`; a shared path across tabs | `rg -n "TabView" -B3 -A12 $SRC -g '*.swift'` | major |
| F6 | The navigation container is not rebuilt by hand | A custom tab bar or back button instead of `TabView` / the system back | `rg -n "TabView\|\.navigationBarBackButtonHidden" $SRC -g '*.swift'` | major |
| F7 | A destination loads its own data from the id | A destination reading a model only its predecessor populated | read each `navigationDestination` body for its load | major |
| F8 | Sheets use `.sheet(item:)`, have a close affordance and their own stack when they navigate | `.sheet(isPresented:)` beside a separate selection state; a sheet with no `Done` / `Cancel`; `interactiveDismissDisabled` without a confirmation | `rg -n "\.sheet\(\|fullScreenCover\|interactiveDismissDisabled" $SRC -g '*.swift'` | minor |
| F9 | `presentationMode` is not used | `@Environment(\.presentationMode)` | `rg -n "presentationMode" $SRC -g '*.swift'` | minor |
| F10 | A URL maps to a route through one validated function; bad input is ignored | `onOpenURL` force-unwrapping components, indexing path parts unchecked, or building a route from an unvalidated id | `rg -n "onOpenURL\|URLComponents\|pathComponents" -A6 $SRC -g '*.swift'` | major |
| F11 | A sign-in gate on a route is client UX, not authorisation | A screen hidden by a flag with no server check noted | `rg -n "isSignedIn\|isAuthenticated" -B2 $SRC -g '*.swift'`; confirm the server enforces — requires dynamic test → `qa-security` | major |

---

## G — Forms & input
*Owning skill: [`forms`](../../forms/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|

---

## H — Networking & realtime
*Owning skill: [`networking`](../../networking/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|

---

## I — Offline, storage & sync
*Owning skill: [`offline-and-storage`](../../offline-and-storage/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|

---

## J — Device features, permissions & native code
*Owning skills: [`device-features`](../../device-features/SKILL.md) · [`notifications-and-links`](../../notifications-and-links/SKILL.md) · [`system-integration`](../../system-integration/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|

---

## K — Security
*Owning fragment: [`mobile/_shared/security`](../../../../_shared/security/references/audit-checks.md)*

This section holds no rows of its own. The rows are those of `mobile/_shared/security/references/audit-checks.md` whose `Stacks` column names `ios`, and the ids are the fragment's — finding `K3` is row K3 of the security fragment. A row a static read cannot prove says **requires dynamic test → `qa-security`** and is reported as unverified, never as passed.

---

## L — Privacy & store compliance
*Owning fragment: [`mobile/_shared/store-compliance`](../../../../_shared/store-compliance/references/audit-checks.md)*

This section holds no rows of its own. The rows are those of `mobile/_shared/store-compliance/references/audit-checks.md` whose `Stacks` column names `ios`, and the ids are the fragment's — finding `L3` is row L3 of the store-compliance fragment. A row a static read cannot prove says **requires dynamic test → `qa-security`** and is reported as unverified, never as passed.

---

## M — Accessibility
*Owning skill: [`accessibility`](../../accessibility/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|

---

## N — Performance
*Owning skill: [`performance`](../../performance/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|

---

## O — Error resilience
*Owning skill: [`error-handling`](../../error-handling/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|

---

## P — Localization
*Owning skill: [`languages`](../../languages/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|

---

## Q — Motion & gestures
*Owning skill: [`animation`](../../animation/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|

---

## R — Testability & test ids
*Owning skill: [`test-ids`](../../test-ids/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|

---

## S — Dev-side tests
*Owning skill: [`unit-testing`](../../unit-testing/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|

---

## T — Release & signing
*Owning fragment: [`mobile/_shared/release`](../../../../_shared/release/references/audit-checks.md)*

This section holds no rows of its own. The rows are those of `mobile/_shared/release/references/audit-checks.md` whose `Stacks` column names `ios`, and the ids are the fragment's — finding `T3` is row T3 of the release fragment. A row a static read cannot prove says **requires dynamic test → `qa-security`** and is reported as unverified, never as passed.

---

## U — Observability & logging
*Owning fragment: [`mobile/_shared/observability`](../../../../_shared/observability/references/audit-checks.md)*

This section holds no rows of its own. The rows are those of `mobile/_shared/observability/references/audit-checks.md` whose `Stacks` column names `ios`, and the ids are the fragment's — finding `U3` is row U3 of the observability fragment. A row a static read cannot prove says **requires dynamic test → `qa-security`** and is reported as unverified, never as passed.

---

## V — Comments & KISS
*Owning skills: [`ep-code-comments`](../../../../../engineering-practices/code-comments/SKILL.md) · CLAUDE.md § Comments and § Simplicity (KISS)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| V1 | No inline comments in a body | A `//` line inside a function or method body — a step marker, a restatement of the next line, a section banner | `rg -n "^\s+//[^/!]" $SRC -g '*.swift'` | minor |
| V2 | A doc comment states a contract, not the signature | A doc comment that restates the name or signature (`Returns the user id`, `@param id the id`) on a property, DTO, getter or single-expression function | `rg -n -A1 "^\s*/// (Returns\|Gets\|Sets) " $SRC -g '*.swift'` | minor |
| V3 | No commented-out code, no `TODO` / `FIXME` left behind | A `//` line holding code, or a `TODO` / `FIXME` / `HACK` marker in committed source | `rg -n "^\s*//\s*(let\|var\|func\|import\|return\|if\|await\|guard)\b" $SRC -g '*.swift'` · `rg -n "TODO\|FIXME\|HACK" $SRC -g '*.swift'` | minor |
| V4 | A comment that exists because the code is unclear | A comment explaining what a badly named local or method does — the fix is the rename or extraction, not a reworded comment | Read the comment hits from V1; ask whether a name would carry it | major |
| V5 | No `protocol` with one conformer | An abstraction introduced for one caller and one implementation, with no second real need | `rg -n "^(public \|internal )?protocol \w+" $SRC`; then count implementers per hit | major |
| V6 | No wrapper that only forwards | A class or function whose whole body delegates one call to the next layer (service → repository → ORM as three layers) | `rg -n -A2 "func \w+\(.*\) .*\{$" $SRC -g '*.swift'`; read each hit for a single delegated call | major |
| V7 | No configurability nothing uses | An options bag, flag, generic parameter or extension point that no caller passes or varies | `rg -n "configuration:\|options:\|\bconfig\b" $SRC -g '*.swift'`; then search for a call site that supplies it | major |
| V8 | A generated or scaffolded comment is removed | A template header, a framework placeholder comment or a wizard banner left in a source file, with no tool depending on it | `rg -n "Created by\|Generated by\|This file was\|Copyright \(c\)" $SRC` — skip generated sources (R.swift, Sourcery, SwiftGen output) | minor |

---

## X — In-app purchases
*Owning fragment: [`mobile/_shared/in-app-purchases`](../../../../_shared/in-app-purchases/references/audit-checks.md)*

This section holds no rows of its own. The rows are those of `mobile/_shared/in-app-purchases/references/audit-checks.md` whose `Stacks` column names `ios`, and the ids are the fragment's — finding `X3` is row X3 of the in-app-purchases fragment. A row a static read cannot prove says **requires dynamic test → `qa-security`** and is reported as unverified, never as passed. Not applicable unless the app sells anything.
