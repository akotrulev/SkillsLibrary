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

---

## C — Architecture, state & DI
*Owning skill: [`architecture`](../../architecture/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|

---

## D — UI components & platform conventions
*Owning skills: [`ui-components`](../../ui-components/SKILL.md) · [`uikit`](../../uikit/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|

---

## E — Styling, theming & adaptive layout
*Owning skill: [`styling`](../../styling/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|

---

## F — Navigation & deep links
*Owning skills: [`navigation`](../../navigation/SKILL.md) · [`notifications-and-links`](../../notifications-and-links/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|

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
