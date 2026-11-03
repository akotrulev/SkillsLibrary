---
name: rules
description: Use when installing or updating the fe-blazor coding standards as path-scoped rules in .claude/rules/fe-blazor/. Triggers "install the Blazor rules". Not for reviewing code (conventions-review).
disable-model-invocation: true
---

# Install the fe-blazor rules

Plugins cannot ship Claude Code rules, so this skill copies them into the project. Each rule file carries `paths:` frontmatter, and Claude Code loads it only once the session reads or edits a matching file, so a session that only touches a stylesheet never pays for the component rules.

| File (beside this SKILL.md) | Loads when the session touches |
|---|---|
| `blazor.md`: simplicity, render modes, lifecycle, state, data and errors, interop, logging, comments | any `*.razor` or `*.razor.cs` |
| `blazor-markup.md`: accessibility, links, `<PageTitle>`, `data-testid` | any `*.razor` |
| `blazor-forms.md`: `EditForm`, validation, edit semantics | any `*.razor` |
| `blazor-ui.md`: display, lists, actions, navigation, localization, public pages | any `*.razor` |
| `blazor-styles.md` | `*.razor.css`, `wwwroot/**/*.css` |
| `blazor-js.md` | `*.razor.js`, `wwwroot/**/*.js` |
| `blazor-tests.md` | `*Test.razor` / `*Tests.razor`, `.razor` files in `*.Tests` / `*.UnitTests` / `*.ComponentTests` projects |
| `blazor-config.md`: secrets, project settings, PWA | `*.Client.csproj`, `wwwroot/appsettings*.json`, the web manifest, `wwwroot/service-worker*.js` |

C# files (`*.cs`, `*.csproj`, `appsettings*.json`) are shared with the be-dotnet and qa-dotnet plugins, so the defaults stop at Blazor-only names. Step 5 adds the folders where this project's Blazor code really lives.

The source folder is `${CLAUDE_SKILL_DIR}`. The target is `<root>/.claude/rules/fe-blazor/`.

## Procedure

1. **Find the project root**: `git rev-parse --show-toplevel`, or the working directory when it is not a git repo.
2. **Check the source**: all eight files exist in `${CLAUDE_SKILL_DIR}`. If one is missing, stop and say so; never write a rule from memory.
3. **Copy each file** that is missing from the target: `mkdir -p <root>/.claude/rules/fe-blazor` and `cp` it byte for byte.
4. **For each file already present**, `cmp` it with the source.
   - Identical: up to date.
   - Different: the team may have edited it. Show `diff -u <target> <source>` and ask: **replace** with the plugin's copy, **keep** theirs, or **write the plugin's copy beside it** as `<name>.plugin` to merge by hand. Never overwrite without that answer.
5. **Fit the paths to this project.** Find the Blazor projects:
   - `git grep -l -e 'Microsoft.NET.Sdk.BlazorWebAssembly' -e 'Microsoft.NET.Sdk.Razor' -- '*.csproj'`, plus the folder of every project that holds `.razor` files: `git ls-files '*.razor'`, then the nearest `.csproj` above each.
   - For each, propose `"<dir>/**/*.cs"` for `blazor.md` (state containers, typed clients, validators and services are Blazor code there), and `"<dir>/*.csproj"`, `"<dir>/appsettings*.json"`, `"<dir>/Program.cs"` for `blazor-config.md`. When a host project also carries backend API code, propose its component folders only (`"<dir>/Components/**/*.cs"`), and leave the rest to the backend rules.
   - Find the bUnit test projects: `git grep -l -i 'Include="bunit"' -- '*.csproj'`. Propose `"<dir>/**/*.cs"` and `"<dir>/**/*.razor"` for `blazor-tests.md`.
   - Add the globs to the installed copies only with the user's agreement, and list them in the report.
6. **Check it will be committed**: `git check-ignore -q <root>/.claude/rules/fe-blazor/blazor.md`. If it is ignored, say so; the rules then apply on this machine only.
7. **Check for conflicts**: read the project's `CLAUDE.md` (root and `.claude/`) for Blazor or UI rules that contradict these files and list them. A written contradiction is the user's to settle.

## Report

```
fe-blazor rules: <file>: installed | up to date | replaced | kept | written as .plugin   (one line per file)
Path: <root>/.claude/rules/fe-blazor/
Blazor projects: <dirs found>   Paths: default | widened with <globs per file>
Committed: yes | ignored by git
Conflicts with CLAUDE.md: none | <one line each>
```

Then tell the user to commit the folder, and that a rule shows in `/memory` once the session has read a matching file.
