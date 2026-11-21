---
name: rules
description: Use when installing or updating the be-dotnet coding standards in .claude/rules/be-dotnet/. Triggers "install the .NET rules", "set up this project". Not for reviewing code (conventions-review).
argument-hint: "[replace | keep | beside]"
---

# Install the be-dotnet rules

Plugins cannot ship Claude Code rules, so this skill copies them into the project. Each rule file carries `paths:` frontmatter, and Claude Code loads it only once the session reads or edits a matching file.

`*.cs` is also written by fe-blazor (components) and qa-dotnet (integration, API and UI suites), so the defaults name backend project folders rather than every C# file. Step 5 fits them to this project.

The source folder is `${CLAUDE_SKILL_DIR}`. The target is `<root>/.claude/rules/be-dotnet/`.

## Run by a model

A model runs this skill itself, as `be-dotnet:rules`, when it is asked to set up a project or to install or update the rules, and when it finds this plugin enabled in a project that has no `.claude/rules/be-dotnet/`. One argument answers the differing-file question below for every file in advance: `replace`, `keep` or `beside`.

Where a step needs the user's answer and nobody is there to give it (a queued plan task, a subagent, a headless run) and no argument settles it, take the choice that changes nothing of theirs and list it under `Waiting for the user:` in the report.

## Procedure

1. **Find the project root**: `git rev-parse --show-toplevel`, or the working directory when it is not a git repo.
2. **List the source**: every `*.md` in `${CLAUDE_SKILL_DIR}` except `SKILL.md`. If the list is empty, stop and say so; never write a rule from memory.
3. **Copy each file** that is missing from the target: `mkdir -p <root>/.claude/rules/be-dotnet` and `cp` it byte for byte. Done when every source file is in the target.
4. **For each file already present**, `cmp` it with the source.
   - Identical: up to date.
   - Different: the team may have edited it. Show `diff -u <target> <source>` and ask: **replace** with the plugin's copy, **keep** theirs, or **write the plugin's copy beside it** as `<name>.plugin` to merge by hand. Never overwrite without that answer or a `replace` argument.

   With nobody to ask and no argument, write the plugin's copy beside it. Done when each file already present is up to date, replaced, kept or written beside as `<name>.plugin`.
5. **Fit the paths to this project.** Find where the backend code really lives, then check each location against the installed globs:
   - **Backend projects**: `git grep -l -e 'Sdk="Microsoft.NET.Sdk.Web"' -e 'Sdk="Microsoft.NET.Sdk.Worker"' -- '*.csproj'`, plus the class libraries they reference (`<ProjectReference>`) that are not test projects. Leave out a web project that holds `*.razor` files or references `Microsoft.AspNetCore.Components.WebAssembly`: that is fe-blazor's, unless the user says it also hosts the API.
   - **Persistence**: `git grep -l -e ': DbContext' -e 'IEntityTypeConfiguration<' -- '*.cs'`, and every `Migrations/` folder.
   - **Unit tests**: test projects (`NUnit`, `xunit` or `MSTest` referenced) that reference none of `Microsoft.AspNetCore.Mvc.Testing`, `Testcontainers`, `Microsoft.Playwright`, `Selenium`, `Appium`, `bunit`, `Reqnroll`, `SpecFlow` or `RestSharp`. Those others are qa-dotnet's or fe-blazor's lane.
   - **Endpoints**: `git grep -l -e '\[ApiController\]' -e 'MapGet(' -e 'MapPost(' -e 'MapGroup(' -- '*.cs'`.
   - **Analyzer config**: `git ls-files -- '*.editorconfig' '*.globalconfig' '*Directory.Build.props' '*BannedSymbols*.txt'`. `dotnet-lint.md` matches `.editorconfig`, `Directory.Build.props` and `BannedSymbols*.txt` at any depth; propose a glob only for a `.globalconfig` or `.ruleset` file that holds the analyzer severities.
   For each project or file a default glob misses, propose a directory glob (for example `"src/Shop/**/*.cs"` for `dotnet.md` and `"src/Shop/appsettings*.json"` for `dotnet-config.md` when the API host is `src/Shop`, `"src/Shop/Orders/Storage/**/*.cs"` for `dotnet-persistence.md`) and add it to the installed copy with the user's agreement. Never widen `dotnet.md` to `**/*.cs` in a repo that also holds Blazor or qa-dotnet projects. With nobody to ask, change no path and list each proposed glob under `Waiting for the user:` in the report. Done when every file each command lists is matched by an installed glob, or a glob is proposed for it.
6. **Check it will be committed**: `git check-ignore -q <root>/.claude/rules/be-dotnet/dotnet.md`. If it is ignored, say so; the rules then apply on this machine only.
7. **Check for conflicts**: read the project's `CLAUDE.md` (root and `.claude/`), `.editorconfig` and `Directory.Build.props` for C# rules that contradict these files and list them. A written contradiction is the user's to settle. Done when each contradiction is listed, or the report says none.
8. **Report lint gaps.** Read the `## Enforced by the build` table in `<root>/.claude/rules/be-dotnet/dotnet-lint.md`, then the project's `.editorconfig`, `.globalconfig`, `Directory.Build.props` and every `BannedSymbols*.txt`. A row is enforced when its id is set to `error` (or its setting is present) and, for an `RS0030` row, its symbol is in a banned-symbols file the project references. List every other row under `Not enforced by the build:` with its id and house rule. Never edit the project's config: the user, or a stack agent they ask, turns the rule on. Done when each table row is enforced or listed.

## Report

```
be-dotnet rules: <file>: installed | up to date | replaced | kept | written as .plugin   (one line per file)
Path: <root>/.claude/rules/be-dotnet/
Paths: default | widened with <globs, per file>
Left to other stacks: <Blazor or qa-dotnet projects not covered, or none>
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
