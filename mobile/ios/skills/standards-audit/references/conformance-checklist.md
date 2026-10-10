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
| D12 | `[UIKit]` A scene delegate owns the window; the app delegate does not | `window` created in `application(_:didFinishLaunchingWithOptions:)`, no `UIApplicationSceneManifest`, `UIApplication.shared.keyWindow` | `rg -n "var window: UIWindow\|keyWindow\|UIApplicationSceneManifest\|UIWindowSceneDelegate" -g '*.swift' -g 'Info.plist'` | major |
| D13 | `[UIKit]` Controllers take dependencies in `init`, not through singletons or later-set optionals | `static let shared` reached from a controller, `var client: APIClient!`, a property assigned after `instantiateViewController` | `rg -n "\.shared\.\|: [A-Z][A-Za-z]*!$" $SRC -g '*ViewController.swift'` | major |
| D14 | `[UIKit]` A `Task` or observer a controller starts is cancelled when the screen goes | `Task { }` / `NotificationCenter` token / `Timer` with no cancel in `viewDidDisappear` / `deinit`; a delegate declared strong | `rg -n "Task \{\|addObserver\|Timer\.scheduled\|var delegate:" $SRC -g '*.swift'`; check each for teardown | major |
| D15 | `[UIKit]` Collections use diffable data sources with stable ids; no `reloadData()` for ordinary updates | `reloadData()` after every change; snapshots of model values that change on edit; index-based `cellForRowAt` over a mutable array | `rg -n "reloadData\(\)\|numberOfItemsInSection\|numberOfRowsInSection" $SRC -g '*.swift'` | minor |
| D16 | `[UIKit]` Layout uses Auto Layout with safe-area and keyboard guides, and Dynamic Type | `UIScreen.main.bounds`, frame math in a layout that must adapt, a fixed label height, `adjustsFontForContentSizeCategory` missing | `rg -n "UIScreen\.main\|\.frame = CGRect\|systemFont\(ofSize\|heightAnchor\.constraint\(equalToConstant" $SRC -g '*.swift'` | major |
| D17 | `[UIKit]` SwiftUI is hosted as a child through `UIHostingController` / `UIHostingConfiguration`; no second navigation stack inside a pushed host | A `NavigationStack` inside a hosting controller pushed onto a `UINavigationController`; host view added without `addChild` / `didMove` | `rg -n "UIHostingController\|UIHostingConfiguration\|addChild" $SRC -g '*.swift'`; read each site | major |
| D18 | `[UIKit]` `UIViewRepresentable` builds in `make`, applies state idempotently in `update`, keeps delegates in a `Coordinator` and cleans up in `dismantle` | Subviews created in `updateUIView`, state mutated from it, a delegate set to the SwiftUI struct, no `dismantleUIView` for a delegate or observer | `rg -n "UIViewRepresentable\|UIViewControllerRepresentable\|updateUIView\|dismantleUIView" $SRC -g '*.swift'` | major |
| D19 | `[UIKit]` `@Observable` read in UIKit is tracked where tracking is on, or the codebase's binding is kept | Observation reads in `viewDidLoad` expecting updates; `@Observable` introduced into a Combine / KVO codebase; iOS 18 target without `UIObservationTrackingEnabled` | `rg -n "updateProperties\|withObservationTracking\|UIObservationTrackingEnabled" $SRC -g '*.swift' -g 'Info.plist'` | minor |
| D20 | `[UIKit]` A UIKit codebase is extended in UIKit; no unrequested rewrite | A PR or plan converting screens to SwiftUI, removing storyboards or bridging Objective-C that the task did not ask for | `git diff --stat`; read the task | minor |

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
| F12 | Push and link payloads decide a destination only after validation | `userInfo["screen"]` or a link parameter routed, opened with `openURL`, or used in a path or query unchecked; an unknown shape that crashes or opens something | `rg -n "userInfo\[\|didReceive response\|onContinueUserActivity\|NSUserActivityTypeBrowsingWeb" -A6 $SRC -g '*.swift'` | blocker |
| F13 | Universal links are narrow and verified; a custom scheme carries no secret | `applinks:` with an AASA claiming `/*`; an auth code or token accepted through `myapp://`; AASA served with a redirect or a wrong content type | `rg -n "applinks:\|CFBundleURLSchemes" -g '*.entitlements' -g 'Info.plist'`; read the hosted AASA — requires dynamic test → `qa-security` | major |
| F14 | Link parsing is one pure function and ignores what it does not recognise | Route built inline in `onOpenURL` / `scene(_:continue:)`; a force-unwrap or unchecked index on `pathComponents`; no host allow-list | `rg -n "onOpenURL\|pathComponents\|URLComponents" -B2 -A8 $SRC -g '*.swift'` | major |
| F15 | `canOpenURL` is not used to probe for apps; `LSApplicationQueriesSchemes` is empty without a reason | `canOpenURL` for installed-app detection; a populated queries list with no recorded reason | `rg -n "canOpenURL\|LSApplicationQueriesSchemes" $SRC -g '*.swift' -g 'Info.plist'` | minor |

---

## G — Forms & input
*Owning skill: [`forms`](../../forms/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| G1 | Form fields use `Form` / `Section` and system controls | `ScrollView` + `VStack` imitating a form; custom text-field chrome copying Material | `rg -n "TextField\|SecureField" -B3 $SRC -g '*.swift'`; read the container | minor |
| G2 | One validator, a pure function over a draft, drives the errors | Validation inside `body`, in a `Task` per keystroke, or duplicated across views; error strings built in the view | `rg -n "isValid\|validate" $SRC -g '*.swift'` | major |
| G3 | Field errors sit beside their field, as localized text, and clear when fixed | A single alert for all errors; colour-only error state; `Text(error.localizedDescription)`; a raw server message | `rg -n "localizedDescription\|\.alert\(" $SRC -g '*Form*.swift' -g '*SignUp*.swift' -g '*Login*.swift'` | major |
| G4 | Focus order follows the layout and Return moves on or submits | No `@FocusState`; no `.submitLabel` / `.onSubmit`; the first invalid field not focused after a failed submit | `rg -n "FocusState\|submitLabel\|onSubmit" $SRC -g '*.swift'`; compare with the field count | minor |
| G5 | Submit guards re-entry in code and shows progress | Only `.disabled(isSubmitting)` with a `.onSubmit` path that bypasses it; no in-flight state; a second tap sends a second request | `rg -n "isSubmitting\|isLoading" -A4 $SRC -g '*.swift'`; read each submit | major |
| G6 | Credentials, addresses and codes declare `textContentType`; secrets use `SecureField` | A password in a `TextField`; sign-in without `.username` / `.password`; no `.oneTimeCode` | `rg -n "textContentType\|SecureField\|isSecureTextEntry" $SRC -g '*.swift'` | major |
| G7 | Server field errors map to fields; an unmapped one reaches a form-level message | A ProblemDetails `errors` dictionary ignored; a field name that matches nothing silently dropped | `rg -n "ProblemDetails\|\.errors\b" $SRC -g '*.swift'`; read the mapper | major |
| G8 | Email, username and code fields turn autocapitalization and autocorrect off | `TextField` for an email with the defaults | `rg -n "emailAddress\|username" -A6 $SRC -g '*.swift'` | minor |
| G9 | A multi-step flow holds one draft above the steps; no secret is persisted in a draft | A draft per step copied forward; a password or token written to `@AppStorage` / `@SceneStorage` / SwiftData | `rg -n "@SceneStorage\|@AppStorage" $SRC -g '*.swift'` | major |
| G10 | Every control and error text has a static `accessibilityIdentifier` | Missing ids on fields, submit and error text; an id built from the label or state | `rg -L "accessibilityIdentifier" $SRC -g '*Form*.swift'` | minor |

---

## H — Networking & realtime
*Owning skill: [`networking`](../../networking/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| H1 | One concrete API client; no protocol with a single conformer; no second HTTP layer | `protocol APIClientProtocol` with one type; Alamofire beside a working `URLSession` client | `rg -n "protocol .*Client\|import Alamofire\|import Moya" $SRC -g '*.swift'`; count conformers | major |
| H2 | Every request has a timeout budget by endpoint class | `URLSession.shared` with default timeouts; `timeoutIntervalForResource` left at 7 days; budgets scattered at call sites | `rg -n "URLSession\.shared\|timeoutInterval\|URLSessionConfiguration" $SRC -g '*.swift'` | major |
| H3 | `.task(id:)` or an owned `Task` cancels a request when its key changes or the screen goes; `CancellationError` is silent | `Task { }` fire-and-forget for a request; `catch { state = .failed }` that also catches cancellation | `rg -n "catch \{" -B6 $SRC -g '*.swift'`; `rg -n "Task\.detached" $SRC -g '*.swift'` | major |
| H4 | Retries are bounded, jittered, honour `Retry-After`, skip writes without an idempotency key, and never run offline | A retry loop at a call site on top of the client's; fixed-interval retry; retrying a `POST`; retrying with no connectivity | `rg -n "retry\|Task\.sleep\|Retry-After\|Idempotency" $SRC -g '*.swift'` | major |
| H5 | A decode failure is a categorised error and renders as failed | `try? decoder.decode` / `?? []` | `rg -n "try\? .*decode\|try\? JSONDecoder" $SRC -g '*.swift'` | major |
| H6 | 401 triggers one shared refresh, one replay, then re-auth in place | Each request refreshing on its own; an unbounded replay; a refresh token in `UserDefaults` | `rg -n "refresh\|401\|unauthorized" $SRC -g '*.swift'` | major |
| H7 | TLS is never bypassed in code | A `URLSessionDelegate` returning `.useCredential` for every `serverTrust`; `NSAllowsArbitraryLoads` | `rg -n "serverTrust\|useCredential\|NSAllowsArbitraryLoads" $SRC -g '*.swift' -g 'Info.plist'` | blocker |
| H8 | No token, body or PII reaches a log | `print` / `Logger` of a request, header, response body or URL with a query secret | `rg -n "print\(\|Logger.*(request\|body\|token\|Authorization)" $SRC -g '*.swift'` | major |
| H9 | Reads outside the critical path do not fail the screen; independent calls do not wait on each other serially | `try await a(); try await b()` where both are independent; one optional call in a throwing `TaskGroup` | `rg -n "try await .*\n.*try await" -U $SRC -g '*.swift'`; read each screen's loads | minor |
| H10 | Foreground and reconnect revalidate; sockets close on background and on owner exit | No `scenePhase` / `NWPathMonitor` hook; a `URLSessionWebSocketTask` created in `body` or never cancelled; reconnect while offline | `rg -n "scenePhase\|NWPathMonitor\|webSocketTask" $SRC -g '*.swift'` | major |
| H11 | Endpoints are built by name from one place; no unsubstituted placeholder reaches the wire | String-concatenated URLs at call sites; a `{id}` left in a path | `rg -n "URL\(string:" $SRC -g '*.swift'` | minor |
| H12 | `[iOS16]` A `Result`-or-completion-handler API is not newly written where `async` is available | New `URLSession.dataTask(with:completionHandler:)` code in an async codebase | `rg -n "dataTask\(with\|completionHandler:" $SRC -g '*.swift'` | minor |

---

## I — Offline, storage & sync
*Owning skill: [`offline-and-storage`](../../offline-and-storage/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| I1 | Each kind of data is in its right store; SwiftData only on iOS 17+ | A SwiftData model on an iOS 16 target; a second store beside the existing Core Data / GRDB; server responses cached in `UserDefaults` | `rg -n "import SwiftData\|NSPersistentContainer\|import GRDB" $SRC -g '*.swift'`; compare with the deployment target | major |
| I2 | Every shipped SwiftData schema is versioned and has a migration stage `[iOS17+]` | `@Model` edited with no new `VersionedSchema`; `ModelContainer(for:)` without a `migrationPlan` after the first release | `rg -n "VersionedSchema\|SchemaMigrationPlan\|ModelContainer\(" $SRC -g '*.swift'`; `git log -p -- '*Model*.swift'` | blocker |
| I3 | Core Data and GRDB changes migrate existing stores `[iOS16]` | A new `.xcdatamodel` change with no model version; `eraseDatabaseOnSchemaChange = true` in a release path | `rg -n "eraseDatabaseOnSchemaChange\|DatabaseMigrator\|NSInferMappingModel" $SRC -g '*.swift'` | blocker |
| I4 | Secrets live in the Keychain with a `…ThisDeviceOnly` class | A token or key in `UserDefaults`, `@AppStorage`, a plist, a file or a model column; `kSecAttrAccessibleAlways*`; `kSecAttrAccessibleWhenUnlocked` without `ThisDeviceOnly` and no restore requirement | `rg -n "kSecAttrAccessible\|kSecClass" $SRC -g '*.swift'`; `rg -n "UserDefaults.*(token\|secret\|password)\|AppStorage\(\"[^\"]*(token\|secret\|key)" -i $SRC -g '*.swift'` | blocker |
| I5 | Keychain writes update before adding, and a fresh install clears stale items | `SecItemDelete` then `SecItemAdd`; no first-launch check | `rg -n "SecItemDelete\|SecItemUpdate\|SecItemAdd" $SRC -g '*.swift'` | minor |
| I6 | Biometric-gated secrets use `SecAccessControl` with `.biometryCurrentSet`, not a boolean `evaluatePolicy` | An `LAContext` result gating a screen that shows a stored token | `rg -n "evaluatePolicy\|biometryCurrentSet\|SecAccessControlCreateWithFlags" $SRC -g '*.swift'` | major |
| I7 | `UserDefaults` use is declared in `PrivacyInfo.xcprivacy` | `UserDefaults` / `@AppStorage` in code and no `NSPrivacyAccessedAPICategoryUserDefaults` entry | `rg -n "UserDefaults\|@AppStorage" $SRC -g '*.swift'`; `rg -n "UserDefaults" -g '*.xcprivacy'` — shares row L1 | major |
| I8 | Model objects do not cross actors; background work uses `@ModelActor` or a background context | A `@Model` / `NSManagedObject` passed into a `Task` or returned from an actor; a large fetch on the main context | `rg -n "@ModelActor\|performBackgroundTask\|mainContext\|viewContext" $SRC -g '*.swift'` | major |
| I9 | Private files carry file protection; regenerable files are excluded from backup | `data.write(to:)` with no options for private data; a cache in Application Support without `isExcludedFromBackup` | `rg -n "completeFileProtection\|isExcludedFromBackup\|\.write\(to:" $SRC -g '*.swift'` | major |
| I10 | Caches are rebuildable and sit in `Caches`; a miss is normal | Required data stored in `Caches` or `tmp`; no handling for an empty cache | `rg -n "cachesDirectory\|temporaryDirectory\|applicationSupportDirectory" $SRC -g '*.swift'` | minor |
| I11 | Offline writes are queued with an idempotency key, replayed in order through the one client, and shown as pending or failed | A write dropped when offline; replay creating duplicates; failed rows invisible | `rg -n "PendingMutation\|pending\|outbox\|idempotenc" -i $SRC -g '*.swift'` | major |
| I12 | Each entity has a stated conflict rule | "Sync" with no rule; silent overwrite of a `409` | read the sync code and its doc comment / PR notes | minor |
| I13 | A store that fails to open degrades to memory with a notice; it does not crash | `fatalError` / `try!` on `ModelContainer` or `loadPersistentStores` in release paths | `rg -n "try! ModelContainer\|fatalError.*(Container\|store)\|loadPersistentStores" $SRC -g '*.swift'` | major |
| I14 | Logout clears the store, caches and Keychain items | Logout that only nils an in-memory token | `rg -n "logout\|signOut" -A10 $SRC -g '*.swift'` | major |

---

## J — Device features, permissions & native code
*Owning skills: [`device-features`](../../device-features/SKILL.md) · [`notifications-and-links`](../../notifications-and-links/SKILL.md) · [`system-integration`](../../system-integration/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| J1 | The system picker is used where it needs no permission | Full photo-library access (`PHPhotoLibrary.requestAuthorization(.readWrite)`) to choose one photo; a custom file browser instead of `fileImporter` | `rg -n "PHPhotoLibrary\.requestAuthorization\|PhotosPicker\|fileImporter" $SRC -g '*.swift'` | major |
| J2 | Every protected resource has a specific, localized `NS…UsageDescription` | A missing key (crash at request), a generic string, a key for a resource the app never uses | `rg -n "NS[A-Za-z]*UsageDescription" -g 'Info.plist' -g '*.xcstrings' -g '*.strings'`; compare with `rg -n "AVCaptureDevice\|CLLocationManager\|CNContactStore\|LAContext" $SRC -g '*.swift'` | blocker |
| J3 | Permissions are requested from `notDetermined`, in context, after a pre-prompt; never at launch | `requestAccess` / `requestWhenInUseAuthorization` in `App.init`, `onAppear` of the first screen or a launch service; no pre-prompt | `rg -n "requestAccess\|requestWhenInUse\|requestAlways\|requestAuthorization" -B4 $SRC -g '*.swift'` | major |
| J4 | The denied and restricted states are working screens with an alternative and a Settings route, rechecked on foreground | A denied branch that is empty or a dead button; no `openSettingsURLString`; status read once at `init` | `rg -n "\.denied\|\.restricted\|openSettingsURLString" $SRC -g '*.swift'` | major |
| J5 | Capture sessions and location updates are tied to the screen | `startRunning()` on the main thread; a session or `liveUpdates()` loop still running after the screen is gone | `rg -n "startRunning\|stopRunning\|liveUpdates\|startUpdatingLocation\|stopUpdatingLocation" $SRC -g '*.swift'` | major |
| J6 | Location asks When In Use at the accuracy the feature needs; coordinates stay out of logs | `requestAlwaysAuthorization` for a foreground feature; `kCLLocationAccuracyBest` for a store locator; a coordinate in `Logger` or analytics | `rg -n "requestAlways\|desiredAccuracy\|kCLLocationAccuracy" $SRC -g '*.swift'` | major |
| J7 | Biometric flows declare `NSFaceIDUsageDescription` and have a passcode / password fallback | Biometrics-only policy with no fallback; the key missing | `rg -n "NSFaceIDUsageDescription" -g 'Info.plist'`; `rg -n "deviceOwnerAuthentication" $SRC -g '*.swift'` | major |
| J8 | `fileImporter` URLs are accessed through the security-scoped calls | A picked URL read with no `startAccessingSecurityScopedResource` | `rg -n "fileImporter\|startAccessingSecurityScopedResource" $SRC -g '*.swift'` | major |
| J9 | Heavy device work (image decode, capture start, large file copy) is off the main actor | Full-size `UIImage(data:)` in a view task on the main actor; `Data(contentsOf:)` of a picked file on main | `rg -n "UIImage\(data\|Data\(contentsOf\|loadTransferable" $SRC -g '*.swift'` | major |
| J10 | No `canOpenURL:` probing; no pasteboard read at launch | `canOpenURL` for installed-app detection; `UIPasteboard.general.string` read in launch code | `rg -n "canOpenURL\|UIPasteboard" $SRC -g '*.swift'` | major |
| J11 | Haptics follow a user-initiated result, not passive events | `.sensoryFeedback` or a feedback generator in a scroll or timer path | `rg -n "sensoryFeedback\|UIImpactFeedbackGenerator\|UINotificationFeedbackGenerator" $SRC -g '*.swift'` | minor |
| J12 | A resource's Required Reason API use is declared (file timestamps, disk space) | `creationDate` / `volumeAvailableCapacity…` in code with no manifest entry — shares row L1 | `rg -n "creationDate\|modificationDate\|volumeAvailableCapacity" $SRC -g '*.swift'` | major |
| J13 | Notification permission is asked in context after a pre-prompt, from `.notDetermined`; denied is a working screen | `requestAuthorization` in `App.init` / `didFinishLaunching`; no pre-prompt; a denied branch with no in-app list or Settings route | `rg -n "requestAuthorization\|authorizationStatus\|openNotificationSettingsURLString" -B4 $SRC -g '*.swift'` | major |
| J14 | The `UNUserNotificationCenter` delegate is set before launch finishes | Delegate assigned in a view's `onAppear` or after `await`; a cold-start tap lost | `rg -n "UNUserNotificationCenter.current\(\)\.delegate" -B3 $SRC -g '*.swift'` | major |
| J15 | The device token is re-registered every launch once authorised, uploaded off the main path, and deleted on sign-out | `registerForRemoteNotifications` called once at first grant only; a blocking upload at launch; no unregister or server delete on sign-out | `rg -n "registerForRemoteNotifications\|didRegisterForRemoteNotifications\|unregisterForRemoteNotifications" -B2 -A6 $SRC -g '*.swift'` | major |
| J16 | No sensitive data in a push payload or its lock-screen text; an extension handler always answers | PII or a code in `aps.alert`; a service extension that never calls `contentHandler`, or shows ciphertext on a decrypt failure | `rg -n "serviceExtensionTimeWillExpire\|contentHandler\|mutableCopy" -A8 $SRC -g '*.swift'` — shares row K20 | major |
| J17 | Only entitlements and background modes the code uses are declared | `aps-environment` / `UIBackgroundModes` entries (`fetch`, `processing`, `remote-notification`) with no matching code; the wrong `aps-environment` for the build | `rg -n "aps-environment\|UIBackgroundModes\|BGTaskSchedulerPermittedIdentifiers" -g '*.entitlements' -g 'Info.plist'` | minor |
| J18 | Promotional push has an opt-in and an opt-out; push is not required for the app to work | Marketing sent on the transactional channel; a core flow that needs the token to proceed | read the notification settings screen and the registration call sites — requires dynamic test → `qa-security` | major |
| J19 | Widgets and Live Activities carry no sensitive data and mark private views | An account balance, code or message body in a timeline entry or `ContentState`; no `.privacySensitive()` | `rg -n "ActivityAttributes\|ContentState\|TimelineEntry\|privacySensitive" -A6 $SRC -g '*.swift'` | major |
| J20 | A widget does not poll and shows how old its data is where staleness matters | A `Timeline` with `.after` seconds-scale or a loop of reloads; `reloadAllTimelines()` on every change; no age or stale state | `rg -n "reloadTimelines\|reloadAllTimelines\|\.after\(\|policy:" $SRC -g '*.swift'` | major |
| J21 | A Live Activity starts on a user action, ends with its event, and is never promotional (guideline 4.5.3) | `Activity.request` from launch or a background path with no user action; an activity with no `end`; promotional `ContentState` | `rg -n "Activity.request\|\.end\(\|NSSupportsLiveActivities\|pushToStartToken" -B3 $SRC -g '*.swift' -g 'Info.plist'` | blocker |
| J22 | Live Activity pushes use the activity token, not the device token; `ContentState` decodes tolerantly | The device token used for `liveactivity` pushes; a renamed `ContentState` field with a required decode | `rg -n "pushTokenUpdates\|ContentState" -A6 $SRC -g '*.swift'` | major |
| J23 | App Intent parameters are validated, destructive intents authenticate and confirm | An intent that deletes or pays with no `authenticationPolicy` or `requestConfirmation`; ids used unchecked | `rg -n "AppIntent\|authenticationPolicy\|requestConfirmation" -A8 $SRC -g '*.swift'` | major |
| J24 | Extensions share data through an App Group snapshot, not a singleton or the full store | A widget opening the full SwiftData / Core Data stack; a `static var` shared between app and extension; a token in the group container | `rg -n "suiteName\|containerURL(forSecurityApplicationGroupIdentifier\|group\." $SRC -g '*.swift' -g '*.entitlements'` | major |
| J25 | BG tasks are registered at launch, reschedule, expire cleanly and call `setTaskCompleted` | `register` inside a view; no `expirationHandler` or cancellation check; a path that never completes the task; an identifier missing from `BGTaskSchedulerPermittedIdentifiers` | `rg -n "BGTaskScheduler\|\.backgroundTask\(\|setTaskCompleted\|expirationHandler" -B2 -A8 $SRC -g '*.swift'` | major |
| J26 | Background work is a head start, never the only path to correct data | A screen that shows stale data forever unless a refresh task ran | read the resume path against `scenePhase`, see O-section resume rows | major |
| J27 | Background transfers use a delegate-based background `URLSession`, uploaded from a file | `URLSession.shared` or an `async` call for a transfer meant to outlive the app; `uploadTask(with:from: Data)` on a background session | `rg -n "URLSessionConfiguration.background\|handleEventsForBackgroundURLSession\|uploadTask" -A5 $SRC -g '*.swift'` | major |
| J28 | `beginBackgroundTask` finishes a write and is always ended | `beginBackgroundTask` used to run a long job; a missing `endBackgroundTask` | `rg -n "beginBackgroundTask\|endBackgroundTask" -B2 -A6 $SRC -g '*.swift'` | minor |

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
| P1 | New strings live in a String Catalog; no new `.strings` or `.stringsdict` file | A `.strings` file created after the catalog exists; `Localizable.strings` extended by hand | `rg --files -g '*.strings' -g '*.stringsdict' -g '*.xcstrings'` | major |
| P2 | No hard-coded UI string once localization is on, and no sentence built by concatenation | Literal text with `+` or interpolation outside `String(localized:)`; `Text(someString)` for UI copy; `accessibilityLabel`, alert and tab text unlocalized | `rg -n 'Text\("[^"]*" *\+\|NSLocalizedString\|\.alert\("[A-Z]' $SRC -g '*.swift'` | major |
| P3 | Plurals and gendered wording are catalog variations, not `if count == 1` | `count == 1 ? "item" : "items"`; a plural built from a pre-formatted string | `rg -n 'count == 1\|\.count == 1\|== 1 \?' $SRC -g '*.swift'` | major |
| P4 | Custom views take `LocalizedStringKey` / `LocalizedStringResource` for copy, and `Text(verbatim:)` marks data | A view with a `title: String` passed straight to `Text`; server data localized by accident | `rg -n "let title: String\|let message: String\|Text\(verbatim" $SRC -g '*.swift'` | minor |
| P5 | Layout uses leading / trailing, never left / right | `.padding(.left`, `Alignment.left`, `UIEdgeInsets(left:`, `.leftAnchor` in shared views | `rg -n '\.(left\|right)\b\|leftAnchor\|rightAnchor\|UIEdgeInsets\(' $SRC -g '*.swift'` | major |
| P6 | Dates, numbers and money use `FormatStyle`, not literals or per-row formatters | `DateFormatter()` / `NumberFormatter()` built in `body` or a row; `"$\(price)"`; a hand-written display date pattern | `rg -n 'DateFormatter\(\)\|NumberFormatter\(\)\|"\$\\\(\|dateFormat =' $SRC -g '*.swift'` | major |
| P7 | The currency comes from data, never from the locale; money is not a `Double` | `Locale.current.currency` as the price currency; a `Double` price | `rg -n 'Locale.current.currency\|: Double.*price\|price: Double' $SRC -g '*.swift'` | major |
| P8 | Purpose strings and the display name are localized in `InfoPlist.xcstrings` | Only an English `Info.plist` purpose string in an app with several localizations | `rg --files -g 'InfoPlist.xcstrings' -g 'InfoPlist.strings'`; compare with `rg -n "NS[A-Za-z]*UsageDescription" -g 'Info.plist'` | major |
| P9 | A shipped language has a complete catalog; none is half-translated | *New* / *Needs Review* entries in a language listed in the project's Localizations | open the catalog's per-language progress; `rg -n '"state" : "(new\|needs_review)"' -g '*.xcstrings'` | minor |
| P10 | Fixed-format dates use a POSIX locale or ISO 8601; user-visible dates do not | `DateFormatter` with `dateFormat` and no `en_US_POSIX` for an API value; an ISO string shown to the user | `rg -n 'dateFormat\|ISO8601' -B2 $SRC -g '*.swift'` | minor |
| P11 | No in-app language picker unless a recorded reason says so | A custom language switcher overriding `Bundle` or `AppleLanguages` | `rg -n 'AppleLanguages\|Bundle.setLanguage\|\.environment\(\\\.locale' $SRC -g '*.swift'` | minor |

---

## Q — Motion & gestures
*Owning skill: [`animation`](../../animation/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| Q1 | Reduce Motion is honoured wherever motion is custom | `withAnimation`, transitions, `phaseAnimator`, `keyframeAnimator` or a looping effect in a file that never reads `accessibilityReduceMotion` | `rg -ln "withAnimation\|\.transition\|phaseAnimator\|keyframeAnimator\|matchedGeometryEffect" $SRC -g '*.swift'` against `rg -ln "accessibilityReduceMotion\|isReduceMotionEnabled" $SRC -g '*.swift'` | major |
| Q2 | `.animation` always carries `value:` | `.animation(.easeInOut)` or `.animation(nil)` on a container with no `value:` | `rg -n '\.animation\([^,)]*\)' $SRC -g '*.swift'` | major |
| Q3 | Animated properties are composited ones (offset, scale, opacity, rotation, colour) | Animating `frame` / `padding` / a changing text length in a hot path | `rg -n 'withAnimation' -A4 $SRC -g '*.swift'`; read what each toggle changes | minor |
| Q4 | A transition sits on a conditional view inside `withAnimation` or `.animation(_:value:)` | `.transition` on an always-present view; a conditional insert with no animation context | `rg -n '\.transition\(' -B4 $SRC -g '*.swift'` | minor |
| Q5 | Animated list rows have stable domain ids | `ForEach(items.indices)`, `id: \.self` on mutable data, or `UUID()` per render | `rg -n 'ForEach\(.*indices\|id: \\\.self\|id: \\\.offset\|UUID\(\)' $SRC -g '*.swift'` | major |
| Q6 | Looping and long animations have a stop condition | `phaseAnimator` with no `trigger:` that runs forever; a `Timer.publish` never cancelled; `repeatForever` with no `onDisappear` | `rg -n 'repeatForever\|phaseAnimator\|Timer\.publish' -B2 -A4 $SRC -g '*.swift'` | major |
| Q7 | A gesture-only action has an accessible alternative | `DragGesture` / `.swipeActions`-less swipe delete with no `accessibilityAction` or button | `rg -n 'DragGesture\|LongPressGesture\|MagnifyGesture' -B2 -A8 $SRC -g '*.swift'`; read for `accessibilityAction` | major |
| Q8 | Transient gesture state is `@GestureState`; a gesture inside a scroller does not steal it | A `@State` offset left non-zero when a drag is cancelled; a `DragGesture()` with `minimumDistance: 0` on a scrolling row | `rg -n 'DragGesture\|@GestureState' $SRC -g '*.swift'` | minor |
| Q9 | `matchedGeometryEffect` has one source per id; iOS 18 zoom uses `matchedTransitionSource` | The same id on two visible views; a hand-built fake hero across a push on iOS 18+ | `rg -n 'matchedGeometryEffect\|matchedTransitionSource\|navigationTransition' $SRC -g '*.swift'` | minor |
| Q10 | An API newer than the deployment target is `#available`-gated | `phaseAnimator`, `.sensoryFeedback`, `.navigationTransition` in an iOS 16 target with no gate | `rg -n 'phaseAnimator\|keyframeAnimator\|navigationTransition\|symbolEffect' $SRC -g '*.swift'` against the target in `project.pbxproj` / `Package.swift` | major |
| Q11 | UIKit motion honours Reduce Motion and is interruptible | `UIView.animate` for a gesture-driven move with no `UIViewPropertyAnimator`; no read of `isReduceMotionEnabled` [UIKit] | `rg -n 'UIView\.animate\|UIViewPropertyAnimator\|isReduceMotionEnabled' $SRC -g '*.swift'` | minor |

---

## R — Testability & test ids
*Owning skill: [`test-ids`](../../test-ids/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| R1 | Every interactive element carries an `accessibilityIdentifier` | A `Button`, `TextField`, `SecureField`, `Toggle`, `Picker` or tab item with no identifier | `rg -n '\b(Button\|TextField\|SecureField\|Toggle\|Picker\|NavigationLink)\b' $SRC -g '*.swift'` against `rg -n 'accessibilityIdentifier' $SRC -g '*.swift'`; read per view | major |
| R2 | Every list / grid container carries an identifier | A `List`, `LazyVStack` in a `ScrollView`, `LazyVGrid` or `UICollectionView` with none | `rg -n '\bList\b\|LazyVStack\|LazyVGrid\|UICollectionView\|UITableView' $SRC -g '*.swift'` | major |
| R3 | The id is `accessibilityIdentifier`, never the accessibility label | `.accessibilityLabel("Login.EmailField")`; a label string reused as the identifier | `rg -n 'accessibilityLabel\("[A-Z][A-Za-z]*\.[A-Z]' $SRC -g '*.swift'` | major |
| R4 | Ids are PascalCase dot-separated | `login-email`, `login_email`, `loginEmail`, spaces | `rg -n 'accessibilityIdentifier\("[^"]*[-_ ][^"]*"\|accessibilityIdentifier\("[a-z]' $SRC -g '*.swift'` | minor |
| R5 | Ids are static: no row id, GUID, index or state value | `"Row.\(order.id)"`, `"Item\(index)"`, `"Tab.\(selected)"` | `rg -n 'accessibilityIdentifier\(".*\\\(' $SRC -g '*.swift'`; read each — a prefix or enum-case interpolation is allowed, a model id or index is not | major |
| R6 | List rows share one locator namespace and are addressed by index | A row identifier built from the row's id; children not namespaced under the row id | `rg -n 'accessibilityIdentifier' -B3 $SRC -g '*Row*.swift' -g '*Cell*.swift'` | major |
| R7 | Region states and the error banner are tagged | A region with `Loading` / `Error` / `Empty` / `Retry` states and no ids on them; the banner and its close untagged | `rg -n 'ProgressView\|ContentUnavailableView\|Retry' $SRC -g '*.swift'` and `rg -n 'accessibilityIdentifier' -g '*Banner*.swift'` | major |
| R8 | Reusable views compose a prefix; no wrapper exists only to carry ids | A `testIdPrefix` ignored by a terminal view; an `AppButton` that only adds an identifier | `rg -n 'testIdPrefix\|struct App(Button\|Field)' $SRC -g '*.swift'` | minor |
| R9 | Decorative and layout views are not tagged | An identifier on a `Spacer`, a plain `VStack` or a decorative image | `rg -n 'accessibilityIdentifier' -B2 $SRC -g '*.swift'`; read the host view | nit |
| R10 | Grouping does not hide tagged children; a container id does not replace a leaf id | `.accessibilityElement(children: .combine)` over views whose child ids the tests need; a container id with unnamed children | `rg -n 'accessibilityElement\(children' -A8 $SRC -g '*.swift'`; confirm on a simulator build's page source — requires dynamic test → `qa-mobile-ios` | major |

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
