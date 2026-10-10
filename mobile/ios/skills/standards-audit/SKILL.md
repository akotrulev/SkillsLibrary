---
name: mobile-ios-standards-audit
description: Use to audit a whole iOS app (Swift, SwiftUI, UIKit) against the mobile-ios plugin's conventions — version lane, structure, UI, navigation, data, device and extension code, accessibility, resilience, test ids, security and store fragments — as a saved, re-runnable report in `docs/audits/`. Read-only. Triggers "audit our iOS app against the plugin conventions". Do NOT use to review one diff (`mobile-ios-code-review`) or check code against a spec (`code-auditor`).
---

# mobile-ios Conformance Audit

Audit an existing **iOS app** against the conventions this plugin defines — CLAUDE.md § Mobile code rules plus the hard rules each `mobile/ios/skills/*` skill owns and the five `mobile/_shared/*` fragments — and produce **one saved report**: every finding evidenced at `file:line`, severity-tabled, mapped to the skill that owns the fix.

**Read-only analysis on product code.** The audit points; the `mobile-ios` agent fixes.

State the mode — Mode A (baseline) or Mode B (re-audit) — and the target path in the first line of output.

## Read before sweeping

1. **[`ep-standards-audit-engine`](../../../../engineering-practices/standards-audit-engine/SKILL.md)** — Mode A/B rounds, the artifact contract, evidence rules, severity semantics, grouping and coverage policy, the five steps, the hostile self-review. **Read it first**; this file adds only what is specific to iOS.
2. [`references/conformance-checklist.md`](references/conformance-checklist.md) — sections A–X and every check; the section index at its end. **Read end-to-end** before Step 2.
3. `engineering-practices/standards-audit-engine/references/report-template.md` — the Round-1 / Round-N skeletons. Read before Step 3.
4. The fragments for sections K, L, T, U, X: `mobile/_shared/{security,store-compliance,release,observability,in-app-purchases}/references/audit-checks.md` — rows whose `Stacks` column names `ios`.

Load the **owning skill** (named per section in the checklist) whenever a check is ambiguous, version-keyed, or you are about to write its fix direction. When checklist and skill disagree, **the skill wins** — and report the disagreement.

Report path: `docs/audits/<NNN>-mobile-ios-conformance-r<N>.md`.

## The fence — what this is not

| Job | Owner |
|---|---|
| Review one diff, inline table, no artifact, screenshot pass | [`code-review`](../code-review/SKILL.md) — this skill reuses its rows at repo scale |
| Code vs a written spec / stories | `ep-spec-vs-code-audit` (or the `code-auditor` agent) |
| How one feature works, where it is defective | `ep-feature-audit` |
| Proof of pinning, on-disk data, resilience controls on a built IPA | **peer** `qa-security` (`mobile-app-scan`, `mobile-runtime-testing`) — a row a static read cannot prove is reported **unverified**, never passed |
| E2E suites, device journeys | **peer** `qa-mobile-java` / `qa-mobile-dotnet` / `qa-mobile-typescript` |
| Design heuristics on screens | `design/ux-review` on simulator screenshots |
| Applying any fix | the `mobile-ios` agent |

## Step 0 — the Xcode / Swift version lane *(never skip)*

```bash
ls -d *.xcodeproj *.xcworkspace Package.swift Podfile Project.swift project.yml 2>/dev/null
rg -n "SWIFT_VERSION|IPHONEOS_DEPLOYMENT_TARGET|SWIFT_DEFAULT_ACTOR_ISOLATION|SWIFT_APPROACHABLE_CONCURRENCY|SWIFT_STRICT_CONCURRENCY|SWIFT_TREAT_WARNINGS_AS_ERRORS" -g '*.pbxproj' -g '*.xcconfig'
rg -n "swift-tools-version|swiftLanguageModes|defaultIsolation|platforms:|treatAllWarnings" -g 'Package.swift'
rg -n "UIApplicationSceneManifest|UILaunchScreen|UIDesignRequiresCompatibility" -g 'Info.plist' -g '*.pbxproj'
rg -ln "ComposableArchitecture|import Dependencies|import Alamofire|import Combine" -g '*.swift' | head
git ls-files | rg -c '\.swift$'; git ls-files | rg -c '\.(m|mm)$'; git log --oneline -5
```

Record: **Xcode and Swift** (27.0 / 6.4 primary · 26.x / 6.2–6.3 supported) · **language mode per target and package** (Swift 6 · Swift 5) · **default isolation and Approachable Concurrency per module** · **deployment target** (17 primary · 16 supported · below 16 → finding A8 and a [`migration`](../migration/SKILL.md) hand-off, UIKit lane only, never audited as if current) · **SwiftUI vs UIKit share** (view counts against controller counts) · **persistence** (SwiftData, Core Data, GRDB) · **dependency manager** (SPM, CocoaPods, Tuist — a `Podfile` is A10, dated 2026-12-02) · **extensions** present (widgets, intents, notification service, share) · **purchases** (StoreKit) · **Objective-C file count** · **TCA / Factory / swift-dependencies** in use.

**The version rule binds every finding.** Never flag a down-level project for lacking an up-level API (`@Observable` on an iOS 16 target, `Observations` below iOS 26, `glassEffect` below iOS 26, a Swift 6.4 construct on a 6.2 toolchain); never apply an up-level recipe to it. A **`[iOS17+]`** row applies only at a 17+ target, **`[Swift6]`** only to a module in Swift 6 mode (or a *new* module that should be), **`[UIKit]`** only to UIKit code, **`[TCA]`** / **`[Tuist]`** only where that tool is already in use. A project mid-migration is finding A, not a licence to audit it against the highest lane present.

Then read 2–3 representative files (a feature view, the API client, a model with its injection site) to calibrate conventions.

## Step 1 — applicability

| Section | Applies when | Probe |
|---|---|---|
| D (SwiftUI rows D1–D11) | SwiftUI views exist | `rg -ln "import SwiftUI" -g '*.swift'` |
| D (UIKit rows D12–D20 `[UIKit]`) | `UIViewController` subclasses or `UIViewRepresentable` exist | `rg -ln "UIViewController\|UIViewRepresentable\|UIHostingController" -g '*.swift'` |
| F (links, AASA rows F13–F15) | A URL scheme, `applinks:` or `onOpenURL` is present | `rg -n "CFBundleURLSchemes\|applinks:\|onOpenURL" -g 'Info.plist' -g '*.entitlements' -g '*.swift'` |
| I (SwiftData rows I2 `[iOS17+]`) | `import SwiftData` | `rg -ln "import SwiftData" -g '*.swift'` |
| I (Core Data / GRDB rows I3) | `NSPersistentContainer` or `GRDB` | `rg -ln "NSPersistentContainer\|import GRDB" -g '*.swift'` |
| J (notifications J13–J18) | Push or `UNUserNotificationCenter` is referenced | `rg -ln "UNUserNotificationCenter\|aps-environment" -g '*.swift' -g '*.entitlements'` |
| J (extensions J19–J28) | A widget, App Intents, Live Activity, BG task or background session target exists | `rg -ln "WidgetKit\|AppIntent\|ActivityKit\|BGTaskScheduler\|URLSessionConfiguration.background" -g '*.swift'`; `ls */*Extension* */*Widget* 2>/dev/null` |
| P (localization) | More than one localization is shipped or a String Catalog exists | `fd -e xcstrings -e strings` |
| Q (motion) | Animation APIs or custom gestures are used | `rg -ln "withAnimation\|phaseAnimator\|DragGesture\|UIViewPropertyAnimator" -g '*.swift'` |
| S (tests) | A test target or plan exists — **no dev-side tests at all is a section S finding** (cite S1), not N/A | `fd -e xctestplan`; `rg -ln "@Test\|XCTestCase" -g '*.swift'` |
| T (release) | Fastlane, an Xcode Cloud workflow, a CI archive step or signing config exists — absent is a finding | `ls fastlane ci_scripts .github/workflows 2>/dev/null` |
| U (observability) | Always; **absent crash reporting is a finding**, not N/A | `rg -ln "Sentry\|Crashlytics\|MetricKit\|import OSLog" -g '*.swift' -g 'Package.swift'` |
| X (in-app purchases) | The app sells anything: `StoreKit`, `RevenueCat` | `rg -ln "import StoreKit\|RevenueCat\|Purchases" -g '*.swift' -g 'Package.swift'` |

A–C, E, G, H, K, L, M, N, O, R, V apply to every app. A section that is N/A must name the probe that decided it. `$SRC` is set by the checklist's recipe header.

## Step 2 notes — what the engine does not say

- **Generated and vendored code.** `.build/`, `Pods/`, `Carthage/` and `DerivedData/` are skipped by `rg`; do not add `--no-ignore` unless the project commits generated sources it owns (SwiftGen, Sourcery output), and state it in the coverage line. A committed `Pods/` is a finding (A10), not code to audit.
- **Static-first.** Run no build, test, `swiftlint`, Instruments or simulator unless the user opts in for this audit. A row about Swift 6 runtime isolation (A1 on a module that just moved) says **requires dynamic test** and is reported unverified.
- **Fragments.** Cite fragment findings with the fragment's own id (`K3`, `L2`); unreachable-by-static rows say **requires dynamic test → `qa-security`**. Rows shared with a section here (I7 / L1, J12 / L1, J16 / K20) are reported once, under the fragment's id.
- **Deviations.** A deliberate project convention (TCA as the architecture, Core Data over SwiftData, UIKit as the UI lane, Factory as the container) is a noted deviation, not a finding; an inconsistent one is a finding.
- **Swift 5-mode modules** are audited against the Swift 5 rows only and carry one A1 finding with the module list — not a finding per file.

## Handoffs

- **Apply fixes** → the `mobile-ios` agent, FIX or EXTEND; a version or lane finding → [`migration`](../migration/SKILL.md) as its own run. The priority table is the artifact.
- **One diff instead** → [`code-review`](../code-review/SKILL.md)
- **Security-flavoured and unverified rows (K, part of L, T)** → peer `qa-security`
- **E2E gaps and test-id coverage proof** → peer `qa-mobile-java` / `qa-mobile-dotnet` / `qa-mobile-typescript`
- **Design review of screens** → `design/ux-review`
- **A spec or feature trace** → `ep-spec-vs-code-audit` / `ep-feature-audit` / `code-auditor`
