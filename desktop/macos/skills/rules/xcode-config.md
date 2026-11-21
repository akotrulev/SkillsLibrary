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

<!-- desktop-macos rules v2 (2026-11-21): project, entitlements, signing config and lint. Ids checked against the SwiftLint rule directory and the Swift compiler on 2026-11-21 (SwiftLint 0.65, Xcode 27, Swift 6.4). Installed by /desktop-macos:rules; edit to fit this project. -->

# Xcode project, entitlements and signing standards (macOS)

Severity tags as in the core Swift rules. The codebase wins where it consistently does otherwise. Recipes: `project-setup`, `shared/distribution`, `migration`.

- No secret in an xcconfig, `Info.plist`, committed plist or the bundle; no committed `.p12`, notarization password or Sparkle private key. *blocker*
- The App Sandbox is on in every configuration, Debug included. *blocker for a Mac App Store build; major for Developer ID*
- Every entitlement has a recorded reason and the narrowest form; no temporary exception without a dated reason. *major*
- Developer ID builds set Hardened Runtime and a secure timestamp, are notarized with `notarytool` and stapled. *blocker*
- A Mac App Store build has no self-updater, no licence keys and no downloaded code. *blocker*
- A shipped `.pkg` is signed under a Developer ID G2 certificate, with `hostArchitectures` set explicitly. *blocker after 2027-02-01; major before*
- No `NSAllowsArbitraryLoads` or other ATS exception without a recorded reason. *blocker*
- Every protected resource has a specific `NS…UsageDescription`, localized. *blocker*
- `PrivacyInfo.xcprivacy` declares collected data. *major*
- `SWIFT_VERSION` and warnings-as-errors are set explicitly, never inherited from the template; default isolation `MainActor` in the app target only. *major*
- Never raise `SWIFT_VERSION`, `MACOSX_DEPLOYMENT_TARGET` or `ARCHS` as a side effect; the target is stated once per module. *major*
- No `MACOSX_DEPLOYMENT_TARGET = 27.1` and no `-ld_classic`. *major*
- One xcconfig per environment; no `#if DEBUG` branching through features. *major*
- Modules are local packages depending one way, `App → Features → Core`; no `Common` / `Utils` package. *major*
- Tuist or XcodeGen present: edit the manifest and regenerate, never the generated `.pbxproj`. *major*
- No CocoaPods in a new project; an existing `Podfile` has a dated move to SPM. *major*
- A login item, agent or XPC service has its own entitlements file and a reason. *minor*

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
- `implicitly_unwrapped_optional` skips an `@IBOutlet` by default, which is the one exception the house rule allows (an AppKit outlet).
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
