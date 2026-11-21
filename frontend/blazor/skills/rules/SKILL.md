---
name: rules
description: Use when installing or updating the fe-blazor coding standards in .claude/rules/fe-blazor/. Triggers "install the Blazor rules", "set up this project". Not for reviewing code (conventions-review).
argument-hint: "[replace | keep | beside]"
---

# Install the fe-blazor rules

Plugins cannot ship Claude Code rules, so this skill copies them into the project. Each rule file carries `paths:` frontmatter, and Claude Code loads it only once the session reads or edits a matching file.

C# files (`*.cs`, `*.csproj`, `appsettings*.json`) are shared with the be-dotnet and qa-dotnet plugins, so the defaults stop at Blazor-only names. Step 5 adds the folders where this project's Blazor code really lives.

The source folder is `${CLAUDE_SKILL_DIR}`. The target is `<root>/.claude/rules/fe-blazor/`.

## Run by a model

A model runs this skill itself, as `fe-blazor:rules`, when it is asked to set up a project or to install or update the rules, and when it finds this plugin enabled in a project that has no `.claude/rules/fe-blazor/`. One argument answers the differing-file question below for every file in advance: `replace`, `keep` or `beside`.

Where a step needs the user's answer and nobody is there to give it (a queued plan task, a subagent, a headless run) and no argument settles it, take the choice that changes nothing of theirs and list it under `Waiting for the user:` in the report.

## Procedure

1. **Find the project root**: `git rev-parse --show-toplevel`, or the working directory when it is not a git repo.
2. **List the source**: every `*.md` in `${CLAUDE_SKILL_DIR}` except `SKILL.md`. If the list is empty, stop and say so; never write a rule from memory.
3. **Copy each file** that is missing from the target: `mkdir -p <root>/.claude/rules/fe-blazor` and `cp` it byte for byte. Done when every source file is in the target.
4. **For each file already present**, `cmp` it with the source.
   - Identical: up to date.
   - Different: the team may have edited it. Show `diff -u <target> <source>` and ask: **replace** with the plugin's copy, **keep** theirs, or **write the plugin's copy beside it** as `<name>.plugin` to merge by hand. Never overwrite without that answer or a `replace` argument.

   With nobody to ask and no argument, write the plugin's copy beside it. Done when each file already present is up to date, replaced, kept or written beside as `<name>.plugin`.
5. **Fit the paths to this project.** Find the Blazor projects:
   - `git grep -l -e 'Microsoft.NET.Sdk.BlazorWebAssembly' -e 'Microsoft.NET.Sdk.Razor' -- '*.csproj'`, plus the folder of every project that holds `.razor` files: `git ls-files '*.razor'`, then the nearest `.csproj` above each.
   - For each, propose `"<dir>/**/*.cs"` for `blazor.md` (state containers, typed clients, validators and services are Blazor code there), and `"<dir>/*.csproj"`, `"<dir>/appsettings*.json"`, `"<dir>/Program.cs"` for `blazor-config.md`. When a host project also carries backend API code, propose its component folders only (`"<dir>/Components/**/*.cs"`), and leave the rest to the backend rules.
   - Find the bUnit test projects: `git grep -l -i 'Include="bunit"' -- '*.csproj'`. Propose `"<dir>/**/*.cs"` and `"<dir>/**/*.razor"` for `blazor-tests.md`.
   - Find the analyzer config: `git ls-files -- '*.globalconfig' '*.editorconfig' '*Directory.Build.props' '*BannedSymbols*.txt'`. `blazor-lint.md` matches `.globalconfig`, `Directory.Build.props` and `BannedSymbols*.txt` at any depth, so there is nothing to widen.
   - Add the globs to the installed copies only with the user's agreement, and list them in the report.

   With nobody to ask, change no path and list each proposed glob under `Waiting for the user:` in the report. Done when every file each command lists is matched by an installed glob, or a glob is proposed for it.
6. **Check it will be committed**: `git check-ignore -q <root>/.claude/rules/fe-blazor/blazor.md`. If it is ignored, say so; the rules then apply on this machine only.
7. **Check for conflicts**: read the project's `CLAUDE.md` (root and `.claude/`) for Blazor or UI rules that contradict these files and list them. A written contradiction is the user's to settle. Done when each contradiction is listed, or the report says none.
8. **Report lint gaps.** Read the `## Enforced by the build` table in `<root>/.claude/rules/fe-blazor/blazor-lint.md`, then the project's `.globalconfig`, `.editorconfig`, `Directory.Build.props` and every `BannedSymbols*.txt`. A row is enforced when its id is set to `error` in a `.globalconfig` and, for an `RS0030` row, its symbol is in a banned-symbols file the project references. List every other row under `Not enforced by the build:` with its id and house rule. Never edit the project's config: the user, or a stack agent they ask, turns the rule on. Done when each table row is enforced or listed.

## Report

```
fe-blazor rules: <file>: installed | up to date | replaced | kept | written as .plugin   (one line per file)
Path: <root>/.claude/rules/fe-blazor/
Blazor projects: <dirs found>   Paths: default | widened with <globs per file>
Committed: yes | ignored by git
Conflicts with CLAUDE.md: none | <one line each>
Not enforced by the build: none | <id: house rule>   (one line per row)
Waiting for the user: none | <one line each: the file or path change, and the question>
```

Then tell the user to commit the folder, and that a rule shows in `/memory` once the session has read a matching file.

## When to use

- Installing or updating the rules.

## When NOT to use

- Writing code: the rule files apply themselves.
