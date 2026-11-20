---
name: standards-audit
description: Use when auditing a whole Mac app (Swift, SwiftUI, AppKit) against desktop-macos conventions; read-only report. Triggers "audit our Mac app". Not for one diff (conventions-review).
disable-model-invocation: true
---

# desktop-macos Conformance Audit

Audit an existing **Mac app** against the conventions this plugin defines (CLAUDE.md § Desktop code rules plus the hard rules each `desktop/macos/skills/*` skill owns and the three `desktop/_shared/*` fragments) and produce **one saved report**: every finding evidenced at `file:line`, severity-tabled, mapped to the skill that owns the fix.

**Read-only analysis on product code.** The audit points; the `desktop-macos` agent fixes.

State the mode, Mode A (baseline) or Mode B (re-audit), and the target path in the first line of output.

## Read before sweeping

1. **[`engineering-practices/standards-audit-engine`](../../../../engineering-practices/standards-audit-engine/SKILL.md)**: Mode A/B rounds, the artifact contract, evidence rules, severity semantics, grouping and coverage policy, the five steps, the hostile self-review. **Read it first**; this file adds only what is specific to the Mac.
2. [`references/conformance-checklist.md`](references/conformance-checklist.md): sections A–X and every check; the section index at its end. **Read end-to-end** before Step 2.
3. `engineering-practices/standards-audit-engine/references/report-template.md`: the Round-1 / Round-N skeletons. Read before Step 3.
4. The fragments for sections K, L, U: `desktop/_shared/{security,distribution,observability}/references/audit-checks.md`, rows whose `Platforms` column names `macos`. Section X is not applicable on macOS.

Load the **owning skill** (named per section in the checklist) whenever a check is ambiguous, version-keyed, or you are about to write its fix direction. When checklist and skill disagree, **the skill wins**, and report the disagreement.

Report path: `docs/audits/<NNN>-desktop-macos-conformance-r<N>.md`.

## The fence — what this is not

| Job | Owner |
|---|---|
| Review one diff, inline table, no artifact, screenshot pass | [`code-review`](../code-review/SKILL.md): this skill reuses its rows at repo scale |
| Code vs a written spec / stories | `dev:audit-spec` (or the `code-auditor` agent) |
| How one feature works, where it is defective | `dev:audit-feature` |
| Proof of sandbox behaviour, Hardened Runtime, on-disk data, notarization, IPC abuse on a built app | **peer** `qa-security`: a row a static read cannot prove is reported **unverified**, never passed |
| E2E suites, window journeys | **peer** `qa-desktop-java` / `qa-desktop-dotnet` / `qa-desktop-typescript` |
| Design heuristics on windows | `design/ux-review` on window screenshots |
| Applying any fix | the `desktop-macos` agent |

## Step 0 — the Xcode / Swift version lane *(never skip)*

```bash
ls -d *.xcodeproj *.xcworkspace Package.swift Podfile Project.swift project.yml 2>/dev/null
rg -n "SWIFT_VERSION|MACOSX_DEPLOYMENT_TARGET|ARCHS|SWIFT_DEFAULT_ACTOR_ISOLATION|SWIFT_APPROACHABLE_CONCURRENCY|SWIFT_STRICT_CONCURRENCY|SWIFT_TREAT_WARNINGS_AS_ERRORS|ENABLE_HARDENED_RUNTIME|SUPPORTS_MACCATALYST" -g '*.pbxproj' -g '*.xcconfig'
rg -n "swift-tools-version|swiftLanguageModes|defaultIsolation|platforms:|treatAllWarnings" -g 'Package.swift'
rg -n "com.apple.security.app-sandbox|SUPublicEDKey|SUFeedURL|NSPrincipalClass|LSUIElement" -g '*.entitlements' -g 'Info.plist' -g '*.pbxproj'
rg -ln "ComposableArchitecture|import Dependencies|import Alamofire|import Combine|import Sparkle" -g '*.swift' | head
git ls-files | rg -c '\.swift$'; git ls-files | rg -c '\.(m|mm)$'; git log --oneline -5
```

Record: **Xcode and Swift** (27.x / 6.4 primary · 26.x / 6.2–6.3 supported) · **language mode per target and package** (Swift 6 · Swift 5) · **default isolation and Approachable Concurrency per module** · **deployment target** (15 primary for a new app · 14 supported · 13 the existing-app floor · below 13 → finding A1 and a [`migration`](../migration/SKILL.md) hand-off, AppKit lane only, never audited as if current) · **architectures** (`ARCHS`, universal or arm64) · **SwiftUI vs AppKit share** (view counts against controller counts) · **Catalyst** target present · **persistence** (SwiftData, Core Data, GRDB) · **dependency manager** (SPM, CocoaPods, Tuist; a `Podfile` is A8, dated 2026-12-02) · **channel** (Developer ID, Mac App Store, both) · **sandbox** on or off · **helpers and extensions** (login items, XPC services, widgets, intents) · **Objective-C file count** · **TCA / Factory / swift-dependencies** in use.

**The version rule binds every finding.** Never flag a down-level project for lacking an up-level API (`@Observable` on a macOS 13 target, `UtilityWindow` on a 14 target, `Document` on a pre-27 SDK, a Swift 6.4 construct on a 6.2 toolchain); never apply an up-level recipe to it. A **`[mac15+]`** row applies only at a 15+ target, **`[mac27SDK]`** only when building on the 27 SDK, **`[AppKit]`** only to AppKit code, **`[MAS]`** only to a Mac App Store build, **`[DevID]`** only to a Developer ID build, **`[TCA]`** / **`[Tuist]`** only where that tool is already in use. A project mid-migration is finding A, not a licence to audit it against the highest lane present.

Then read 2–3 representative files (a feature view, the API client, a model with its injection site) to calibrate conventions.

## Step 1 — applicability

| Section | Applies when | Probe |
|---|---|---|
| D (SwiftUI rows) | SwiftUI views exist | `rg -ln "import SwiftUI" -g '*.swift'` |
| D (AppKit rows `[AppKit]`) | `NSViewController`, `NSWindowController`, `NSViewRepresentable` or `NSHostingView` exist | `rg -ln "NSViewController\|NSWindowController\|NSViewRepresentable\|NSHostingView\|NSHostingController" -g '*.swift'` |
| F (windows and commands) | Always: a Mac app has windows and a menu bar; a menu-bar-only app still has commands | `rg -ln "WindowGroup\|Window(\|MenuBarExtra\|Settings\|CommandMenu\|NSMenu" -g '*.swift'` |
| I (SwiftData rows) | `import SwiftData` | `rg -ln "import SwiftData" -g '*.swift'` |
| I (Core Data / GRDB rows) | `NSPersistentContainer` or `GRDB` | `rg -ln "NSPersistentContainer\|import GRDB" -g '*.swift'` |
| I (documents) | `DocumentGroup`, `FileDocument`, `Document` or `NSDocument` | `rg -ln "DocumentGroup\|FileDocument\|NSDocument\|ReferenceFileDocument" -g '*.swift'` |
| J (permissions) | A usage string, a TCC-protected API or a security-scoped bookmark is present | `rg -n "NS[A-Za-z]+UsageDescription\|startAccessingSecurityScopedResource\|AVCaptureDevice\|CGRequestScreenCaptureAccess\|AXIsProcessTrusted" -g '*.swift' -g 'Info.plist'` |
| J (helpers) | `SMAppService`, an XPC service or a launch agent exists | `rg -ln "SMAppService\|XPCSession\|NSXPCConnection\|LaunchAgents" -g '*.swift' -g '*.plist'` |
| J (system integration) | App Intents, widgets, a URL scheme, Services or drag and drop are referenced | `rg -ln "AppIntent\|WidgetKit\|CFBundleURLTypes\|NSServices\|onDrop\|draggable" -g '*.swift' -g 'Info.plist'` |
| P (localization) | More than one localization is shipped or a String Catalog exists | `fd -e xcstrings -e strings` |
| S (tests) | A test target or plan exists; **no dev-side tests at all is a section S finding** (cite S1), not N/A | `fd -e xctestplan`; `rg -ln "@Test\|XCTestCase" -g '*.swift'` |
| K, L, U (fragments) | Always; **absent crash reporting is a finding**, not N/A | `rg -ln "Sentry\|MetricKit\|import OSLog\|OpenTelemetry" -g '*.swift' -g 'Package.swift'` |
| L (update channel rows) | Sparkle in a Developer ID build; for a Mac App Store build, an updater is itself the finding | `rg -ln "Sparkle\|SPUStandardUpdaterController" -g '*.swift' -g 'Package.swift'` |

A–C, E, G, H, M, N, O, R, V apply to every app. X is N/A on macOS. A section that is N/A must name the probe that decided it. `$SRC` is set by the checklist's recipe header.

## Step 2 notes — what the engine does not say

- **Generated and vendored code.** `.build/`, `Pods/`, `Carthage/` and `DerivedData/` are skipped by `rg`; do not add `--no-ignore` unless the project commits generated sources it owns (SwiftGen, Sourcery output), and state it in the coverage line. A committed `Pods/` is a finding (A8), not code to audit.
- **Static-first.** Run no build, test, `swiftlint`, Instruments or launch unless the user opts in for this audit. A row about Swift 6 runtime isolation (a module that just moved) says **requires dynamic test** and is reported unverified.
- **Entitlements are read from the file, not the build.** A sandbox that is on in the entitlements file but disabled for the Debug configuration is a finding about the configuration, with both file lines cited.
- **Fragments.** Cite fragment findings with the fragment's own id (`K3`, `L2`, `U4`); unreachable-by-static rows say **requires dynamic test → `qa-security`**. Rows shared with a section here are reported once, under the fragment's id.
- **Deviations.** A deliberate project convention (TCA as the architecture, Core Data over SwiftData, AppKit as the UI lane, Factory as the container) is a noted deviation, not a finding; an inconsistent one is a finding.
- **Swift 5-mode modules** are audited against the Swift 5 rows only and carry one A-section finding with the module list, not a finding per file.
- **Dated rows** (the 2027-02-01 Developer ID CA, CocoaPods) are reported with their date and how far away it is on the audit day.

## Handoffs

- **Apply fixes** → the `desktop-macos` agent, FIX or EXTEND; a version or lane finding → [`migration`](../migration/SKILL.md) as its own run. The priority table is the artifact.
- **One diff instead** → [`code-review`](../code-review/SKILL.md)
- **Security-flavoured and unverified rows (K, part of L)** → peer `qa-security`
- **E2E gaps and test-id coverage proof** → peer `qa-desktop-java` / `qa-desktop-dotnet` / `qa-desktop-typescript`
- **Design review of windows** → `design/ux-review`
- **A spec or feature trace** → `dev:audit-spec` / `dev:audit-feature` / `code-auditor`
