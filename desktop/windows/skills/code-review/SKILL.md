---
name: conventions-review
description: Use when reviewing a C#, XAML or C++/WinRT Windows app diff against plugin conventions, plus a window screenshot pass. Triggers "review this PR". Not for a whole-repo audit (standards-audit).
disable-model-invocation: true
---

# Windows — Code Review

A **hostile review of one diff** against the desktop-windows rule files, then a **screenshot pass** on the running app. Findings go in the standard severity table; the review **does not rewrite**: it points, and the `desktop-windows` agent (or the author) fixes. A whole-repo sweep with a saved report is [`standards-audit`](../standards-audit/SKILL.md).

## The checklist is the rule files

Every check, and the severity it reports, lives in one place: the desktop-windows rule files: `csharp.md` (core), `winui-xaml.md`, `wpf.md`, `winforms.md`, `cppwinrt.md`, `win-accessibility.md`, `win-styling.md`, `win-localization.md`, `dotnet-networking.md`, `win-persistence.md`, `win-tests.md` and `package-config.md`.

1. **The project's copies first**: `.claude/rules/desktop-windows/` at the project root. The team may have edited them, and its edits win.
2. **Otherwise the plugin's copies**: `desktop/windows/skills/rules/` (under `${CLAUDE_PLUGIN_ROOT}` in an installed plugin). Say in the report that the project has no installed rules and that `/desktop-windows:rules` installs them.

Read `csharp.md` for any `.cs` file and `cppwinrt.md` for any C++ file, plus each other file whose `paths:` match a file under review, in full before the first finding. A view in a folder no glob covers still gets its lane's view rules, `win-accessibility.md`, `win-styling.md` and `win-localization.md`; judge by what the file is, not by whether its path matched. A rule loaded on its own by the session is not enough: a review needs every file that applies. Never review from memory of the rules, and never add a check the files do not contain; propose it as a rule change instead.

## Version lane and the lane filter

Detect before flagging: the TFM and the Windows App SDK major (`*.csproj`, `Directory.Packages.props`), the UI lane **per project** (`UseWinUI`, `UseWPF`, `UseWindowsForms`, a `.vcxproj` with `Microsoft.Windows.CppWinRT`), packaged or unpackaged (`Package.appxmanifest`, `WindowsPackageType`), and the distribution channel. The rule files' "the codebase wins" line applies: a convention the project follows consistently is not a finding.

**One lane per file.** A C# file is never judged against `cppwinrt.md`, a `.cpp` file never against C# rules, and a WPF window never against `winui-xaml.md`. A mixed solution is reviewed per project, and the report names each lane it covered.

| Lane | Review consequence |
|---|---|
| **.NET 10 · Windows App SDK 2.x · WinUI · packaged** | The rules as written |
| .NET 11 | Supported; a .NET 11-only API on a .NET 10 TFM is a finding |
| .NET 8 or 9 | One finding (out of support since 2026-11-10) plus a [`migration`](../migration/SKILL.md) run; never reviewed as if current |
| Windows App SDK 1.x | One finding plus a migration run; 2.x-only APIs are not demanded of it |
| WPF / WinForms | `wpf.md` / `winforms.md` apply; a WinUI rule is not flagged there and the app is not asked to convert |
| C++/WinRT | `cppwinrt.md` applies to `*.cpp`, `*.h`, `*.idl`, `*.vcxproj`; coverage is lines unless `llvm-cov` reports branches |
| **[unpackaged]** | No package identity: `ApplicationData.Current`, toasts and background tasks need the unpackaged path |

## When to use

- A `.cs` / `.xaml` / `.cpp` / `.h` / `.idl` / `.resw` / `.csproj` / `.vcxproj` / `Package.appxmanifest` diff, before merge
- Step 5 of the agent: the whole change set, after the quality layers
- "Why does this crash after the await / lose its window / fail signing?"

## When NOT to use

- Whole codebase, saved re-runnable report → [`standards-audit`](../standards-audit/SKILL.md)
- Explaining a concept → [`basics`](../basics/SKILL.md); writing code → the owning feature skill
- Reviewing **E2E test code** (WinCore, FlaUI) → peer `qa-desktop-java` / `qa-desktop-dotnet` / `qa-desktop-typescript`
- Pen-test or runtime security → peer `qa-security`
- A spec-versus-code audit → `code-auditor`

## Inputs needed

1. **The diff** (files or `git diff` range) and the windows and commands it touches
2. **Lane facts** above, per project
3. **Whether the app can be built and launched** for the screenshot pass

## Procedure

1. **Read the rule files** that apply (above), then each changed file end to end. Over a large diff, the *Find it with* recipes in [`conformance-checklist.md`](../standards-audit/references/conformance-checklist.md) are search leads; its rows are not extra checks.
2. **Walk the rules in this order**: safety and the UI thread (`csharp.md`, `cppwinrt.md`), secrets, capabilities and elevation, unvalidated activation, bridge or IPC input, persistence migrations, then the rest. Most blockers live there.
3. **Read the code at every hit.** A grep hit is a lead, not a finding. Load the owning feature skill when a rule's application is ambiguous.
4. **Per finding**: file and line, the rule broken, a one-sentence fix. The severity is the tag on the rule, never a new judgment. One row per defect family with a count, not per site.
5. **Run the screenshot pass** (below) if the app builds and launches; otherwise say it was not run.
6. **Do not rewrite.** Hand off (below).

## The screenshot pass (Step 5)

Only when the app builds and launches; otherwise report "screenshot pass not run" and why.

```powershell
winapp ui screenshot -a <AppName> -o win-<window>.png
```

`winapp` (0.8.0, public preview, Developer Mode on) is optional (D10); confirm the flags with `winapp ui screenshot --help`. Without it, capture the window with a short PowerShell script kept in the scratch folder (`System.Drawing` `CopyFromScreen` over the window rectangle from `GetWindowRect`, with the process made DPI-aware), or Snipping Tool. A blank image is "screenshot pass not run", not a pass. `Read` each image. Capture the changed windows in **light and dark**, at the **smallest supported window size** and a large one, at **150% scale** where the diff touches layout, with **High Contrast** on where it touches colour, in each of loading, loaded, failed and empty where the diff changes them. Check against the diff, not against taste: backdrop and title bar, text truncation at small sizes and with longer translations, contrast and focus visuals, control sizes and density, the `InfoBar` position inside the window content, commands present and disabled rather than hidden, platform-native controls (no web look). Cite the `design/ux-review` heuristic and the corpus row (`design/ui-ux-pro-max --stack winui | wpf`) behind each visual finding. Save images only under a scratch folder inside the worktree and delete them before committing.

## Output format

```
| Severity | Location | Issue | Suggested fix |
|----------|----------|-------|---------------|
| blocker  | src/Orders/ImportService.cs:41 | `File.OpenRead(args.Path)` on a path taken from file activation with no validation | Canonicalize and check the root per `activation-and-notifications`; no unvalidated path |
| major    | src/Orders/OrdersPage.xaml:18 | `Visibility="{x:Bind Vm.HasSelection}"` hides the Archive command | `IsEnabled` bound to `CanExecute` per `windows-and-navigation` |
```

Close with the lane line (`.NET 10 · Windows App SDK 2.6 · WinUI · packaged`, one per lane covered), the screenshot-pass status, the finding counts by severity, and one line: `Rules: project .claude/rules/desktop-windows/ | plugin copy (not installed)`.

## Handoffs

- Fix → the `desktop-windows` agent (FIX or EXTEND), or the owning feature skill
- Repo-wide → [`standards-audit`](../standards-audit/SKILL.md); version moves → [`migration`](../migration/SKILL.md)
- Lock the fix with a test → [`unit-testing`](../unit-testing/SKILL.md)
- A rule is missing or wrong → edit the project's `.claude/rules/desktop-windows/`; for every project, the plugin's `desktop/windows/skills/rules/`
- Missing ids → [`test-ids`](../test-ids/SKILL.md); E2E review → peer `qa-desktop-java` / `qa-desktop-dotnet` / `qa-desktop-typescript`
- Security proof → peer `qa-security`
