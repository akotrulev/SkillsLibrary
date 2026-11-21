---
paths:
  - "**/*.xcconfig"
  - "**/*Info.plist"
  - "**/*.entitlements"
  - "**/*.xcprivacy"
  - "**/Package.swift"
  - "**/Project.swift"
  - "**/project.pbxproj"
  - "**/Podfile"
  - "**/.swiftlint.yml"
---

<!-- mobile-ios rules v2 (2026-11-21): project, build config and lint. Ids checked against the SwiftLint rule directory and the Swift compiler on 2026-11-21 (SwiftLint 0.65, Xcode 27, Swift 6.4). Installed by /mobile-ios:rules; edit to fit this project. -->

# Xcode project and configuration standards

Severity tags as in the core Swift rules: **blocker**, **major**, **minor**, **nit**. The codebase wins where it consistently does otherwise.

- No secret in an xcconfig, `Info.plist`, committed plist or the bundle; no committed `Local.xcconfig`, `.p12` or server-keyed `GoogleService-Info.plist`. *blocker*
- No `NSAllowsArbitraryLoads` or other ATS exception without a recorded reason. *blocker*
- Every protected resource has a specific `NS…UsageDescription`, localized in `InfoPlist.xcstrings`; `When In Use` location, never `Always` for a foreground feature. *blocker; major for the location class*
- `PrivacyInfo.xcprivacy` exists in the app and in each package that uses a Required Reason API. *major*
- `SWIFT_VERSION = 6` and warnings-as-errors are set explicitly (xcconfig, `swiftLanguageModes`, `treatAllWarnings`), never inherited from the template. *major*
- Default isolation `MainActor` in the app target only; packages stay `nonisolated`. *major*
- Never raise `SWIFT_VERSION` or `IPHONEOS_DEPLOYMENT_TARGET` as a side effect of other work; the deployment target is stated once per module. *major*
- One xcconfig per environment, read once; no `#if DEBUG` / `#if STAGING` branching through features. *major*
- Modules are local packages depending one way, `App → Features → Core`; no `Common` / `Utils` package every module imports. *major*
- Tuist or XcodeGen present: edit the manifest and regenerate, never the generated `.pbxproj`. *major*
- No CocoaPods in a new project; an existing `Podfile` has a dated move to SPM. No dependency for something the SDK does, and no second crash or metrics SDK beside MetricKit and the one reporter. *major*
- The scene manifest and a launch screen are present; no `UIRequiresFullScreen`. *major*
- Only the entitlements and background modes the code uses; `LSApplicationQueriesSchemes` empty without a reason. *minor*
- `swift-format` and SwiftLint are committed and agree; no SwiftLint `--fix` in a build phase. *minor*

Each row below is a rule of `swift.md` or `xcode-config.md` that SwiftLint or the Swift compiler detects, so the build catches it before a review does. Rules neither detects stay in those files and get no row: `@unchecked Sendable`, `nonisolated(unsafe)`, `Task.detached`, a blocking call other than `DispatchQueue.main`, `try?`, `ObservableObject`, and a `Task { }` nobody cancels.

## Enforced by the build

| House rule (file, section) | Tool | Rule id or setting | Level |
|---|---|---|---|
| No `!` outside tests (`swift.md`, Safety and types) | SwiftLint | `force_unwrapping` | error |
| No `as!` outside tests (`swift.md`, Safety and types) | SwiftLint | `force_cast` | error |
| No `try!` outside tests (`swift.md`, Safety and types) | SwiftLint | `force_try` | error |
| No implicitly unwrapped optional outside an `@IBOutlet` (`swift.md`, Safety and types) | SwiftLint | `implicitly_unwrapped_optional` | error |
| No empty `catch` (`swift.md`, Errors, logging and secrets) | SwiftLint | `no_empty_block`, statement blocks only | error |
| No mutable global state: no `static var` (`swift.md`, Safety and types) | Swift compiler, strict concurrency | `SWIFT_VERSION = 6`, or `swiftLanguageModes: [.v6]` in a package | setting |
| Warnings are errors, set explicitly (`xcode-config.md`) | Swift compiler | `SWIFT_TREAT_WARNINGS_AS_ERRORS = YES`, or `.treatAllWarnings(as: .error)` in a package, tools 6.2 and later | setting |
| `os.Logger` only: no `print`, `NSLog`, `debugPrint` or `dump` (`swift.md`, Errors, logging and secrets) | SwiftLint | `custom_rules`: `no_print` | error |
| Nothing blocks the main actor and no GCD hop: no `DispatchQueue.main` (`swift.md`, Concurrency) | SwiftLint | `custom_rules`: `no_gcd_main` | error |

A row the project's config does not enforce is *minor*.

Turning a row off to pass a gate is *major* (`engineering:quality-constraints`).

How the rows are wired:

- The SwiftLint rows are `.swiftlint.yml` at the repo root, run as `swiftlint lint --strict` (SwiftLint 0.65). `force_cast` and `force_try` are errors by default. `force_unwrapping`, `implicitly_unwrapped_optional` and `no_empty_block` are opt-in and default to `warning`, so the config turns each on at `severity: error`.
- `implicitly_unwrapped_optional` skips an `@IBOutlet` by default, which is the one exception the house rule allows.
- `no_empty_block` flags every empty block. The config keeps it to statement blocks (`catch {}`, `if {}`) and turns it off for function, initializer and closure bodies. A `catch` holding only a comment passes the rule and stays a review finding.
- Tests: a child `.swiftlint.yml` in each tests folder turns `force_unwrapping` and `force_try` off, because `swift-tests.md` allows a fixed fixture literal. `force_cast` and the other rows still hold there.
- Generated code: SwiftLint lints every file under `included`, a committed generated source too, so list its folder in `excluded`. A `// swiftlint:disable all` header does not work: `blanket_disable_command` flags it. Both compiler rows reach a generated file in the same target.
- `no_print` and `no_gcd_main` are `custom_rules`, regex checks, the one place the stack writes a rule of its own. `no_gcd_main` also matches `DispatchQueue.main.sync`.
- Swift 6 strict concurrency is the compiler, never a SwiftLint id. A Swift 5-mode module keeps `SWIFT_VERSION = 5` by the version lane, and that is not a gap in the first setting row.
- `disabled_rules` hands whitespace and line length to `swift-format`, so the two tools do not argue.

`.swiftlint.yml`:

```yaml
included: [App, Packages]
excluded: [.build, "**/.build", DerivedData, "**/Generated"]
opt_in_rules: [force_unwrapping, implicitly_unwrapped_optional, no_empty_block]
disabled_rules: [trailing_whitespace, line_length]
force_unwrapping:
  severity: error
force_cast:
  severity: error
force_try:
  severity: error
implicitly_unwrapped_optional:
  severity: error
no_empty_block:
  severity: error
  disabled_block_types: [function_bodies, initializer_bodies, closure_blocks]
custom_rules:
  no_print:
    regex: '\b(print|NSLog|debugPrint|dump)\('
    message: Use os.Logger.
    severity: error
  no_gcd_main:
    regex: 'DispatchQueue\.main'
    message: Use MainActor isolation.
    severity: error
```

`.swiftlint.yml` in each tests folder:

```yaml
disabled_rules: [force_unwrapping, force_try]
```
