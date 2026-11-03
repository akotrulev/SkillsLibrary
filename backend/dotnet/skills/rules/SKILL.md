---
name: rules
description: Use when installing or updating the be-dotnet coding standards as path-scoped rules in .claude/rules/be-dotnet/. Triggers "install the .NET rules". Not for reviewing code (conventions-review).
disable-model-invocation: true
---

# Install the be-dotnet rules

Plugins cannot ship Claude Code rules, so this skill copies them into the project. Each rule file carries `paths:` frontmatter, and Claude Code loads it only once the session reads or edits a matching file, so a session that never touches persistence code never pays for the persistence rules.

| File (beside this SKILL.md) | Loads when the session touches |
|---|---|
| `dotnet.md`: simplicity, DI, async, types, layering, logging and telemetry, comments | `*.cs` under a `*.Api`, `*.WebApi`, `*.Application`, `*.Domain`, `*.Infrastructure`, `*.Persistence`, `*.Data` or `*.Worker` project folder |
| `dotnet-persistence.md`: DbContext, entities, queries, migrations | `*DbContext.cs`, `*Repository.cs`, `Persistence/`, `Data/`, `Entities/`, `Configurations/`, `Migrations/`, `*.Persistence` and `*.Data` projects |
| `dotnet-api.md`: endpoints, validation, ProblemDetails, authorization | `*Controller.cs`, `*Endpoints.cs`, `Controllers/`, `Endpoints/` |
| `dotnet-tests.md`: unit tests | `*.UnitTests` projects and `*.Application.Tests`, `*.Domain.Tests`, `*.Infrastructure.Tests` |
| `dotnet-config.md`: secrets, log levels, per-environment values | `appsettings*.json` in a `*.Api`, `*.WebApi` or `*.Worker` project |

`*.cs` is also written by fe-blazor (components) and qa-dotnet (integration, API and UI suites), so the defaults name backend project folders rather than every C# file. Step 5 fits them to this project.

The source folder is `${CLAUDE_SKILL_DIR}`. The target is `<root>/.claude/rules/be-dotnet/`.

## Procedure

1. **Find the project root**: `git rev-parse --show-toplevel`, or the working directory when it is not a git repo.
2. **Check the source**: all five files exist in `${CLAUDE_SKILL_DIR}`. If one is missing, stop and say so; never write a rule from memory.
3. **Copy each file** that is missing from the target: `mkdir -p <root>/.claude/rules/be-dotnet` and `cp` it byte for byte.
4. **For each file already present**, `cmp` it with the source.
   - Identical: up to date.
   - Different: the team may have edited it. Show `diff -u <target> <source>` and ask: **replace** with the plugin's copy, **keep** theirs, or **write the plugin's copy beside it** as `<name>.plugin` to merge by hand. Never overwrite without that answer.
5. **Fit the paths to this project.** Find where the backend code really lives, then check each location against the installed globs:
   - **Backend projects**: `git grep -l -e 'Sdk="Microsoft.NET.Sdk.Web"' -e 'Sdk="Microsoft.NET.Sdk.Worker"' -- '*.csproj'`, plus the class libraries they reference (`<ProjectReference>`) that are not test projects. Leave out a web project that holds `*.razor` files or references `Microsoft.AspNetCore.Components.WebAssembly`: that is fe-blazor's, unless the user says it also hosts the API.
   - **Persistence**: `git grep -l -e ': DbContext' -e 'IEntityTypeConfiguration<' -- '*.cs'`, and every `Migrations/` folder.
   - **Unit tests**: test projects (`NUnit`, `xunit` or `MSTest` referenced) that reference none of `Microsoft.AspNetCore.Mvc.Testing`, `Testcontainers`, `Microsoft.Playwright`, `Selenium`, `Appium`, `bunit`, `Reqnroll`, `SpecFlow` or `RestSharp`. Those others are qa-dotnet's or fe-blazor's lane.
   - **Endpoints**: `git grep -l -e '\[ApiController\]' -e 'MapGet(' -e 'MapPost(' -e 'MapGroup(' -- '*.cs'`.
   For each project or file a default glob misses, propose a directory glob (for example `"src/Shop/**/*.cs"` for `dotnet.md` and `"src/Shop/appsettings*.json"` for `dotnet-config.md` when the API host is `src/Shop`, `"src/Shop/Orders/Storage/**/*.cs"` for `dotnet-persistence.md`) and add it to the installed copy with the user's agreement. Never widen `dotnet.md` to `**/*.cs` in a repo that also holds Blazor or qa-dotnet projects.
6. **Check it will be committed**: `git check-ignore -q <root>/.claude/rules/be-dotnet/dotnet.md`. If it is ignored, say so; the rules then apply on this machine only.
7. **Check for conflicts**: read the project's `CLAUDE.md` (root and `.claude/`), `.editorconfig` and `Directory.Build.props` for C# rules that contradict these files and list them. A written contradiction is the user's to settle.

## Report

```
be-dotnet rules: <file>: installed | up to date | replaced | kept | written as .plugin   (one line per file)
Path: <root>/.claude/rules/be-dotnet/
Paths: default | widened with <globs, per file>
Left to other stacks: <Blazor or qa-dotnet projects not covered, or none>
Committed: yes | ignored by git
Conflicts with CLAUDE.md: none | <one line each>
```

Then tell the user to commit the folder, and that a rule shows in `/memory` once the session has read a matching file.
