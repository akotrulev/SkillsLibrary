---
name: rules
description: Use when installing or updating the desktop-windows standards as path-scoped rules in .claude/rules/desktop-windows/. Triggers "install the Windows rules". Not for reviewing code (conventions-review).
argument-hint: "[replace | keep | beside]"
---

# Install the desktop-windows rules

Plugins cannot ship Claude Code rules, so this skill copies them into the project. Each rule file carries `paths:` frontmatter, and Claude Code loads it only once the session reads or edits a matching file, so a session that never touches a view never pays for the view rules. Install all twelve: a file for a lane the project does not use costs nothing until a matching file is touched, and the agent reads only the lane's files.

| File (beside this SKILL.md) | Loads when the session touches |
|---|---|
| `csharp.md`: simplicity, safety, UI thread, state and DI, errors, logging, secrets, permissions, lifecycle, comments | any `*.cs` |
| `winui-xaml.md`: binding, region states, windows, navigation, commands, forms (WinUI only) | `*.xaml`, `*Page` / `*Window` / `*Control` / `*Dialog` / `*View` code-behind, `Views/`, `Pages/`, `Controls/`, `Dialogs/` |
| `wpf.md` (WPF only) | `*.xaml`, `*Window` / `*Control` / `*Dialog` / `*View` / `*Page` code-behind, `Views/`, `Controls/`, `Dialogs/` |
| `winforms.md` (WinForms only) | `*Form.cs`, `*Form.Designer.cs`, `*UserControl.cs`, `*Dialog.cs`, `Forms/`, `Controls/`, `Dialogs/` |
| `cppwinrt.md`: ownership, coroutines, UI thread, errors, IDL, build, tests (C++/WinRT only) | `*.cpp`, `*.h`, `*.idl`, `*.vcxproj` |
| `win-accessibility.md`: accessibility, keyboard, test ids | the XAML and form paths above |
| `win-styling.md`: Fluent 2, theme resources, High Contrast, motion | `*.xaml`, `Themes/`, `Styles/`, `Resources/`, `Assets/` |
| `win-localization.md`: `.resw`, `.resx`, plurals, RTL, formatting | `*.resw`, `*.resx`, `*.xaml`, `Strings/`, `Resources/`, `Localization/` |
| `dotnet-networking.md` | `*Client` / `*Api` / `*Endpoint(s)` / `*Socket` / `*Gateway` files, `Networking/`, `Network/`, `Api/`, `Http/`, `Clients/` |
| `win-persistence.md`: `ApplicationData`, SQLite and EF Core, `PasswordVault`, DPAPI, settings, migrations | `*Store` / `*Storage` / `*Vault` / `*Database` / `*DbContext` / `*Settings` / `*Migration` / `*Repository` / `*Cache` files, `Persistence/`, `Storage/`, `Data/`, `Migrations/`, `Settings/` |
| `win-tests.md` | `*Tests/` folders, `*Tests` / `*Test` files (`.cs` and `.cpp`) |
| `package-config.md`: secrets, TFM, Windows App SDK, MSIX, capabilities, signing, AOT | `Package.appxmanifest`, `*.csproj`, `*.vcxproj`, `Directory.Build.props`, `Directory.Packages.props`, `app.manifest`, `*.pubxml`, `nuget.config` |

The source folder is `${CLAUDE_SKILL_DIR}`. The target is `<root>/.claude/rules/desktop-windows/`.

## Run by a person or by a model

A person types `/desktop-windows:rules`. A model runs this skill itself, as `desktop-windows:rules`, when it is asked to set up a project or to install or update the rules, and when it finds this plugin enabled in a project that has no `.claude/rules/desktop-windows/`. One argument answers the differing-file question below for every file in advance: `replace`, `keep` or `beside`.

Where a step needs the user's answer or agreement and nobody is there to give it (a queued plan task, a subagent, a headless run) and no argument settles it, take the choice that changes nothing of theirs: a differing file gets the plugin's copy beside it as `<name>.plugin`, and a path or any other change to an installed copy is not made. List each one under `Waiting for the user:` in the report. Never guess the answer.

## Procedure

1. **Find the project root**: `git rev-parse --show-toplevel`, or the working directory when it is not a git repo.
2. **Check the source**: all twelve `.md` rule files above exist in `${CLAUDE_SKILL_DIR}`. If one is missing, stop and say so; never write a rule from memory.
3. **Copy each file** that is missing from the target: `mkdir -p <root>/.claude/rules/desktop-windows` and `cp` it byte for byte.
4. **For each file already present**, `cmp` it with the source.
   - Identical: up to date.
   - Different: the team may have edited it. Show `diff -u <target> <source>` and ask: **replace** with the plugin's copy, **keep** theirs, or **write the plugin's copy beside it** as `<name>.plugin` to merge by hand. Never overwrite without that answer or a `replace` argument.
5. **Fit the paths to this project.** The default globs follow common file naming; a feature-folder layout (`Features/Orders/OrdersDetail.xaml.cs`) often matches none of them. Find where each kind of file actually lives, leaving test files out of the first six:
   - WinUI views: `git grep -l -e 'xmlns:muxc' -e 'Microsoft.UI.Xaml' -- '*.xaml' '*.cs'` (`winui-xaml.md`, `win-accessibility.md`, `win-styling.md`, `win-localization.md`)
   - WPF views: `git grep -l -e 'UseWPF' -e 'presentation' -- '*.csproj' '*.xaml'` (`wpf.md`, plus the same three)
   - WinForms: `git grep -l -e ': Form' -e ': UserControl' -e 'InitializeComponent' -- '*.cs'` (`winforms.md`, `win-accessibility.md`, `win-localization.md`)
   - C++/WinRT: `git grep -l -e 'winrt::' -e 'namespace winrt' -- '*.cpp' '*.h' '*.idl'` (`cppwinrt.md`; fit its four globs to the folders that hold the project's C++, and leave a Win32 or MFC project out)
   - networking: `git grep -l -e 'HttpClient' -e 'ClientWebSocket' -e 'IHttpClientFactory' -- '*.cs'` (`dotnet-networking.md`)
   - persistence: `git grep -l -e 'ApplicationData' -e 'PasswordVault' -e 'DbContext' -e 'ProtectedData' -e 'SqliteConnection' -- '*.cs'` (`win-persistence.md`)
   - tests: `git grep -l -e 'NUnit' -e 'UITestMethod' -e 'gtest/gtest.h' -- '*.cs' '*.cpp'` (`win-tests.md`)

   For each file a search lists that its rule file's globs miss, propose the narrowest directory globs that cover them (for example `"**/Features/*/Views/**/*.cs"` or `"**/src/Orders.Core/Networking/**/*.cs"`) and add them to the installed copy with the user's agreement. Prefer a folder glob to `**/*.cs`, which would load every view rule into model and service work. A project with a lane it does not use (no WPF, no C++) keeps that lane's file installed and idle; deleting it is the user's choice. A solution with C# and C++ projects keeps `cppwinrt.md` scoped to the C++ folders, so the C++ rules never load beside C# files.
6. **Check it will be committed**: `git check-ignore -q <root>/.claude/rules/desktop-windows/csharp.md`. If it is ignored, say so; the rules then apply on this machine only.
7. **Check for conflicts**: read the project's `CLAUDE.md` (root and `.claude/`) for C#, XAML or C++ rules that contradict these files and list them. A written contradiction is the user's to settle.

## Report

```
desktop-windows rules: <file>: installed | up to date | replaced | kept | written as .plugin   (one line per file)
Path: <root>/.claude/rules/desktop-windows/
Paths: default | widened: <file> += <globs>   (one line per widened file)
Committed: yes | ignored by git
Conflicts with CLAUDE.md: none | <one line each>
Waiting for the user: none | <one line each: the file or path change, and the question>
```

Then tell the user to commit the folder, and that a rule shows in `/memory` once the session has read a matching file.
