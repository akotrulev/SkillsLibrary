---
name: standards-audit
description: Use when auditing a whole Windows app (WinUI, WPF, WinForms, C++/WinRT) against desktop-windows conventions; read-only report. Triggers "audit our Windows app". Not for one diff (conventions-review).
disable-model-invocation: true
---

# desktop-windows Conformance Audit

Audit an existing **Windows app** against the conventions this plugin defines (CLAUDE.md § Desktop code rules plus the hard rules each `desktop/windows/skills/*` skill owns and the three `desktop/_shared/*` fragments) and produce **one saved report**: every finding evidenced at `file:line`, severity-tabled, mapped to the skill that owns the fix.

**Read-only analysis on product code.** The audit points; the `desktop-windows` agent fixes.

State the mode, Mode A (baseline) or Mode B (re-audit), the lanes covered and the target path in the first line of output.

## Read before sweeping

1. **[`engineering/standards-audit-engine`](../../../../engineering/standards-audit-engine/SKILL.md)**: Mode A/B rounds, the artifact contract, evidence rules, severity semantics, grouping and coverage policy, the five steps, the hostile self-review. **Read it first**; this file adds only what is specific to Windows.
2. [`references/conformance-checklist.md`](references/conformance-checklist.md): sections A–X and every check; the section index at its end. **Read end-to-end** before Step 2.
3. `engineering/standards-audit-engine/references/report-template.md`: the Round-1 / Round-N skeletons. Read before Step 3.
4. The fragments for sections K, L, U: `desktop/_shared/{security,distribution,observability}/references/audit-checks.md`, rows whose `Platforms` column names `windows`.

Load the **owning skill** (named per section in the checklist) whenever a check is ambiguous, version-keyed, or you are about to write its fix direction. When checklist and skill disagree, **the skill wins**, and report the disagreement.

Report path: `docs/audits/<NNN>-desktop-windows-conformance-r<N>.md`.

## The fence — what this is not

| Job | Owner |
|---|---|
| Review one diff, inline table, no artifact, screenshot pass | [`code-review`](../code-review/SKILL.md): this skill reuses its rows at repo scale |
| Code vs a written spec / stories | `engineering:audit-spec` (or the `code-auditor` agent) |
| How one feature works, where it is defective | `engineering:audit-feature` |
| Proof of package capabilities, signing, SmartScreen behaviour, on-disk data, IPC abuse on a built app | **peer** `qa-security`: a row a static read cannot prove is reported **unverified**, never passed |
| E2E suites, window journeys | **peer** `qa-desktop-java` / `qa-desktop-dotnet` / `qa-desktop-typescript` |
| Design heuristics on windows | `design/ux-review` on window screenshots |
| Applying any fix | the `desktop-windows` agent |

## Step 0 — the .NET / Windows App SDK version lane and the UI lanes *(never skip)*

```bash
ls -d *.sln *.slnx *.csproj *.vcxproj Directory.Build.props Directory.Packages.props global.json nuget.config 2>/dev/null
rg -n "TargetFramework|TargetPlatformMinVersion|UseWinUI|UseWPF|UseWindowsForms|WindowsPackageType|EnableMsixTooling|PublishAot|Nullable|TreatWarningsAsErrors|Platforms|RuntimeIdentifiers" -g '*.csproj' -g '*.props'
rg -n "Microsoft.WindowsAppSDK|Microsoft.Windows.CsWinRT|Microsoft.Windows.CppWinRT|WinUIAnalyzer|CommunityToolkit.Mvvm|Microsoft.Extensions.Hosting|Velopack|Sentry|OpenTelemetry" -g '*.csproj' -g '*.props' -g '*.vcxproj' -g 'packages.lock.json'
rg -n "<Identity|runFullTrust|rescap:Capability|<Capability|allowElevation|requestedExecutionLevel" -g 'Package.appxmanifest' -g 'app.manifest'
rg -ln "Microsoft.Maui|Avalonia|Uno.WinUI|Xamarin" -g '*.csproj' | head
git ls-files | rg -c '\.cs$'; git ls-files | rg -c '\.(cpp|h|idl)$'; git ls-files | rg -c '\.xaml$'; git log --oneline -5
```

Record **per project** (a solution is audited project by project): **TFM** (`net10.0-windows10.0.26100.0` primary · `net11.0-…` supported · `net8.0` / `net9.0` out of support since 2026-11-10 → finding A2 and a [`migration`](../migration/SKILL.md) hand-off) · **Windows App SDK** (2.6.x primary · 1.x → A3 and a migration hand-off) · **UI lane** (WinUI · WPF · WinForms · C++/WinRT; a `.vcxproj` without `Microsoft.Windows.CppWinRT` is Win32 or MFC and is reported, not audited) · **packaged or unpackaged** and the distribution channel (Store, MSIX sideload, unpackaged + Velopack) · **CsWinRT** version · **test projects and runners** (NUnit, the WinUI Unit Test App, GoogleTest) · **MAUI / Avalonia / Uno** markers (named, not audited, A7).

**The version rule binds every finding.** Never flag a down-level project for lacking an up-level API (a .NET 11 API on .NET 10, a 2.x control on a 1.x project); never apply an up-level recipe to it. A **`[WinUI]`**, **`[WPF]`**, **`[WinForms]`**, **`[C++]`**, **`[packaged]`** or **`[unpackaged]`** row applies only in that lane. A project mid-migration is finding A, not a licence to audit it against the highest lane present.

**The lane filter keeps reports clean.** Rows tagged `[C++]` (B12, C12, N1, S1, X13–X22) are audited only in C++/WinRT projects and are **never reported against C# files**; the C# rows (and X1–X12) are never reported against C++ files. Untagged rows apply to every lane, read in the lane's own idiom: B5 reads as "core library with no XAML" in C++. A solution with both lanes carries two lane lines and its findings say which project they are in. WPF and WinForms rows are likewise never reported against a WinUI project.

Then read 2–3 representative files per lane (a page and its view model, the API client, the composition root, a C++ runtime class) to calibrate conventions.

## Step 1 — applicability

| Section | Applies when | Probe |
|---|---|---|
| D (`[WinUI]` rows) | A project with `UseWinUI` or `Microsoft.UI.Xaml` | `rg -ln "Microsoft.UI.Xaml" -g '*.xaml' -g '*.cs' -g '*.h'` |
| D (`[WPF]` / `[WinForms]` rows) | `UseWPF` / `UseWindowsForms` | `rg -ln "UseWPF\|UseWindowsForms" -g '*.csproj'` |
| F (windows and commands) | Always: a Windows app has windows; a tray-only app still has commands | `rg -ln "AppWindow\|NavigationView\|Window\b\|Form\b\|MenuBar" -g '*.cs' -g '*.xaml' -g '*.cpp'` |
| I (EF Core / SQLite rows) | `DbContext` or `Microsoft.Data.Sqlite` | `rg -ln "DbContext\|SqliteConnection" -g '*.cs'` |
| I (`[packaged]` / `[unpackaged]` rows) | `Package.appxmanifest` present or `WindowsPackageType=None` | `fd Package.appxmanifest`; `rg -n "WindowsPackageType" -g '*.csproj'` |
| J (activation, notifications) | `AppInstance`, `AppNotificationManager`, a protocol or file association | `rg -ln "AppInstance\|AppNotificationManager\|uap:Protocol\|FileTypeAssociation" -g '*.cs' -g '*.cpp' -g 'Package.appxmanifest'` |
| J (background, share, widgets, WebView2) | Any of them referenced | `rg -ln "BackgroundTask\|WebView2\|DataTransferManager\|Widget" -g '*.cs' -g '*.cpp' -g 'Package.appxmanifest'` |
| P (localization) | More than one language shipped or a `.resw` / `.resx` exists | `fd -e resw -e resx` |
| S (tests) | A test project exists; **no dev-side tests at all is a section S finding** (cite S2; S1 on the C++ lane), not N/A | `rg -ln "\[Test\]\|\[UITestMethod\]\|gtest/gtest.h" -g '*.cs' -g '*.cpp'` |
| K, L, U (fragments) | Always; **absent crash reporting is a finding**, not N/A | `rg -ln "Sentry\|OpenTelemetry\|Microsoft.Extensions.Logging" -g '*.cs' -g '*.csproj'` |
| L (update channel rows) | Velopack or another updater in an unpackaged build; a Store build has none | `rg -ln "Velopack\|UpdateManager" -g '*.cs' -g '*.csproj'` |
| X (C# rows X1–X12) | P/Invoke, COM, `unsafe` or XAML Islands | `rg -ln "DllImport\|LibraryImport\|ComImport\|DesktopWindowXamlSource" -g '*.cs'` |
| X (`[C++]` rows X13–X22) | A `.vcxproj` with `Microsoft.Windows.CppWinRT` | `rg -ln "Microsoft.Windows.CppWinRT" -g '*.vcxproj'` |

A–C, E, G, H, M, N, O, R, V apply to every app. X is N/A without P/Invoke, COM or C++ projects. A section that is N/A must name the probe that decided it. `$SRC` is set by the checklist's recipe header.

## Step 2 notes — what the engine does not say

- **Generated and vendored code.** `bin/`, `obj/`, `x64/`, `Generated Files/` and `*.g.cs` / `*.g.i.cs` / `*.g.h` are skipped by `rg`; do not add `--no-ignore` unless the project commits generated sources it owns, and state it in the coverage line. Never audit a file the build regenerates.
- **Static-first.** Run no build, test, analyzer, profiler or launch unless the user opts in for this audit. A row about the UI thread, a coroutine's lifetime or a Narrator pass says **requires dynamic test** and is reported unverified.
- **The manifest is read from the file, not the build.** A capability or `requestedExecutionLevel` in `Package.appxmanifest` or `app.manifest` is cited with its line; a Debug-only difference is a finding about the configuration.
- **Fragments.** Cite fragment findings with the fragment's own id (`K3`, `L2`, `U4`); unreachable-by-static rows say **requires dynamic test → `qa-security`**. Rows shared with a section here are reported once, under the fragment's id.
- **Deviations.** A deliberate project convention (MSTest as the only runner, a different container, WPF kept as the UI lane) is a noted deviation, not a finding; an inconsistent one is a finding.
- **Dated rows.** .NET 8 / 9 (out of support 2026-11-10), Windows App SDK 2.x servicing (2027-04-29) and the Artifact Signing eligibility list are reported with their date and how far away it is on the audit day.
