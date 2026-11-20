---
name: migration
description: Use when a Windows project changes lane (.NET 8/9 to 10, Windows App SDK 1.x to 2.x, UWP, WPF or WinForms to WinUI or modernized). Triggers "move us to .NET 10". Not for a new app (project-setup).
disable-model-invocation: true
---

# Windows — Migration

Owns changing the **runtime, SDK, UI framework, project format or packaging** of an existing Windows project. Every other Windows skill applies what is already there; this one is the only skill that moves the lane, and it does so as **its own change**: never inside feature work, never two moves at once, never past one project or one window per commit series.

## Version lane

| Lane | Value | Migration consequence |
|---|---|---|
| **Primary** | .NET 10 LTS · Windows App SDK 2.6.x · `net10.0-windows10.0.26100.0` · WinUI · packaged MSIX | The target unless the project names another |
| Supported | .NET 11 STS (GA 2026-11-10; needs x86-64-v2 / Arm64 LSE) · WPF · WinForms · C++/WinRT lanes | A lane stays itself; never converted to reach a feature |
| Dated | **.NET 8 and 9 are out of support since 2026-11-10** · **Windows App SDK 1.8 left maintenance 2026-09-24; 1.7 and older are out of support** · the 2.0 line is serviced to 2027-04-29 | Deadlines, not preferences: [`dotnet-8-9-to-10`](references/dotnet-8-9-to-10.md), [`windows-app-sdk-1-to-2`](references/windows-app-sdk-1-to-2.md) |
| Floor | Windows 10 1809 (17763) is the Windows App SDK API floor; Windows 10 consumer ESU runs to 2027-10-12 | `TargetPlatformMinVersion` stays unless the owner raises it |

## When to use

- The user names a move: .NET 10, Windows App SDK 2.x, UWP to WinUI, WPF or WinForms to WinUI, .NET Framework to .NET 10, modernizing WPF or WinForms in place
- The audit reports A1–A7 ([`standards-audit`](../standards-audit/SKILL.md) section A)
- A post-migration break: a window that lost its state, a package that no longer installs, a toast that stopped arriving

## When NOT to use

- New app → [`project-setup`](../project-setup/SKILL.md)
- Feature work, a bug fix → the agent's FIX / EXTEND modes; they never up-level a lane
- A patch or minor dependency bump, or a package major with no lane change: dependency hygiene
- Signing, MSIX or update-channel setup that is not a move → `desktop/_shared/distribution`
- macOS → `desktop-macos:migration`; iOS → `mobile-ios:migration`
- **Xamarin.Forms / MAUI → WinUI** is a rewrite, not a migration: MAUI is detected and named, not taught ([`basics`](../basics/SKILL.md)). Say so, point to [`project-setup`](../project-setup/SKILL.md) and the plan skills, and offer to plan it as new work
- **Win32 / MFC → C++/WinRT** is new work in the [`cpp-winrt`](../cpp-winrt/SKILL.md) lane, not a move this skill owns

## Inputs needed

1. **The move**: one of the six below. A request for two is two runs, in the order the table gives
2. **Current state**: TFM per project, Windows App SDK version, the UI lane per project, packaged or unpackaged, CsWinRT version, `packages.lock.json` or central versions, the count of `{Binding}`, P/Invoke, COM and `System.Configuration` uses, third-party control vendors
3. **The unit**: one project, one window or one page per commit; the order is leaves first (libraries nothing else references, windows nothing else opens)
4. **Whether the app ships this quarter**: it decides whether the dated rows are urgent

## The gate — before any lane moves

1. **Clean tree, green baseline.** Record the build (`dotnet build -warnaserror`, or `msbuild App.vcxproj /p:Configuration=Debug /p:Platform=x64 /p:TreatWarningAsError=true` on the C++ lane), the test run (`dotnet test`, `CoreTests.exe`) and `dotnet format --verify-no-changes` *before* touching anything, or no later failure is attributable. Run them.
2. **One project, one change.** Commit the move per project (window, page) so a failure bisects to one unit. Work in the checkout you are given; never create a branch or worktree.
3. **Inventory the blast radius first**: count the warnings the new TFM reports, the `{Binding}` sites, the P/Invoke and COM uses, the blockers the decision guide names (WCF server, ASMX, `System.Configuration`, third-party vendors). That number is the real size of the job; a number you cannot bound is a reason to ask.
4. **Read the source of the move**, not memory: the .NET breaking-changes list for the target, the Windows App SDK release notes for the version, Microsoft's migration decision guide, learn.microsoft.com for dates. Flag, property and package names move between releases: read the installed SDK's docs.
5. **Never combine** two moves. A TFM raise plus a Windows App SDK 2.x raise plus a WinUI port in one change leaves no way to tell which one broke a window.

## The six moves

| Move | Reference | One-line shape | Order |
|---|---|---|---|
| .NET 8 / 9 → 10 (or 11) | [`dotnet-8-9-to-10`](references/dotnet-8-9-to-10.md) | **Dated.** `global.json`, TFM, packages and CI image per project, leaves first; read the breaking-changes list | 0 — dated |
| Windows App SDK 1.x → 2.x | [`windows-app-sdk-1-to-2`](references/windows-app-sdk-1-to-2.md) | **Dated.** Packages, the generated-`Main` rename, unpackaged storage, pickers; SemVer from 2.0.1 | 0 — dated |
| .NET Framework → .NET 10 (WPF, WinForms) | [`framework-to-dotnet10`](references/framework-to-dotnet10.md) | Upgrade in place first; WinUI cannot target .NET Framework; Copilot modernization optional | 1 |
| UWP → WinUI | [`uwp-to-winui`](references/uwp-to-winui.md) | App model, `CoreWindow` gone, pickers need a window id; page by page | 2 |
| WPF → WinUI, or modernize WPF in place | [`wpf-to-winui-or-modernize`](references/wpf-to-winui-or-modernize.md) | A recorded decision first; in place is the default; view by view if WinUI | 3 |
| WinForms modernization | [`winforms-modernization`](references/winforms-modernization.md) | .NET 10, dark mode, DPI, async dialogs, binding; the lane stays WinForms | 4 |

Order 0 moves first when its date is near; the numbered ones follow by dependency: a WinUI port wants .NET 10 and Windows App SDK 2.x underneath, and WPF and WinForms leave .NET Framework before anything else.

## Cross-move rules

- **Never up-level as a side effect.** A feature task that finds .NET 8, Windows App SDK 1.x, a WPF app with no Fluent theme or an unpackaged app reports it and offers this skill; it does not start it (CLAUDE.md § Desktop code rules).
- **A TFM raise is its own move** and the only one that may delete `#if` and OS-version branches. The Windows part of the TFM (`windows10.0.26100.0`) and `TargetPlatformMinVersion` are decided in the same run, and `x64;ARM64` stays (`Any CPU` is not a platform on a packaged project).
- **Never add WinUI to WPF or WinForms as a side effect**, and never convert either to WinUI without the recorded decision ([`interop`](../interop/SKILL.md) for hosting).
- **Warnings are the work list.** `TreatWarningsAsErrors` goes on at the end of a project's move, not before; never silence an analyzer warning or an AOT or trim warning to finish faster.
- **Tests move with the code.** A moved project keeps its runner split (NUnit; the WinUI Unit Test App only for XAML types, D8); a migration with no test that fails on the old behaviour has proved nothing ([`unit-testing`](../unit-testing/SKILL.md)).
- **Identity and storage are part of every move that changes packaging.** A move between packaged and unpackaged re-checks `ApplicationData`, the vault, notifications and activation ([`offline-and-storage`](../offline-and-storage/SKILL.md), [`activation-and-notifications`](../activation-and-notifications/SKILL.md)).
- **Do not require the AI agents.** Microsoft's `winui@win-dev-skills` plugin (`winui-wpf-migration`) and GitHub Copilot app modernization can help where installed (D10); a project that migrates without them is correct, and the result is verified the same way.

## Verification (every move, non-negotiable)

1. Build is clean with warnings as errors for the unit just moved; `dotnet format --verify-no-changes` matches or beats the baseline.
2. The test run matches or beats the baseline; a test exists that exercises the moved seam.
3. The app launches (`winapp run` or Visual Studio F5) and the primary flow runs end to end; a screenshot for the record on a UI move, read back as an image ([`code-review`](../code-review/SKILL.md)).
4. A packaged build installs on a clean machine or account and starts; an unpackaged build starts from a path with spaces.
5. For a TFM or SDK move, `dotnet list package --outdated --include-transitive` and `--deprecated` agree with the stated decision, and no 3.x CsWinRT or experimental package slipped in.
6. Re-run the conformance audit's section A ([`standards-audit`](../standards-audit/SKILL.md)).

## Anti-patterns

- **Raising every project's TFM in one commit** and fixing what the compiler lists: the list hides the runtime ones.
- **Raising Windows App SDK and the TFM together.**
- **Converting a WPF or WinForms app to WinUI "while we are here"**, or hosting WinUI in it with no recorded decision.
- **Targeting .NET 8 or 9 on a new project because the build agent has it.**
- **Adopting CsWinRT 3.0 preview or an experimental Windows App SDK package** to reach one API.
- **Rewriting a window and redesigning it in the same commit**: the diff cannot be reviewed.
- **Deleting `packages.config` or the `.NET Framework` project before the new project builds and tests green.**
- **Bundling a feature into the migration commit.**

## Handoffs

- The C# and XAML standard → [`basics`](../basics/SKILL.md); project, props and manifest layout → [`project-setup`](../project-setup/SKILL.md)
- State ownership after the move → [`architecture`](../architecture/SKILL.md); WPF and WinForms lanes → [`wpf`](../wpf/SKILL.md), [`winforms`](../winforms/SKILL.md)
- Hosting, P/Invoke, COM, CsWinRT → [`interop`](../interop/SKILL.md); the C++ lane → [`cpp-winrt`](../cpp-winrt/SKILL.md)
- Store model migrations (EF Core) → [`offline-and-storage`](../offline-and-storage/SKILL.md)
- Signing, MSIX, updates → `desktop/_shared/distribution`
- Review the migration diff → [`code-review`](../code-review/SKILL.md); conformance after the move → [`standards-audit`](../standards-audit/SKILL.md)
- Tests that lock the move → [`unit-testing`](../unit-testing/SKILL.md); window journeys → peer `qa-desktop-java` / `qa-desktop-dotnet` / `qa-desktop-typescript`
