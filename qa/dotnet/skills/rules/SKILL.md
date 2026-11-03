---
name: rules
description: Use when installing or updating the qa-dotnet test standards as path-scoped rules in .claude/rules/qa-dotnet/. Triggers "install the .NET QA rules". Not for reviewing tests (ui-tests-review).
disable-model-invocation: true
---

# Install the qa-dotnet rules

Plugins cannot ship Claude Code rules, so this skill copies them into the project. Each rule file carries `paths:` frontmatter, and Claude Code loads it only once the session reads or edits a matching file, so a session that never touches a page object never pays for the UI rules.

| File (beside this SKILL.md) | Loads when the session touches |
|---|---|
| `automation.md`: test shape, assertions, errors and cleanup, waits, secrets, page objects, comments | C# in a `*ApiTests` / `*UiTests` / `*AppiumTests` / `*MobileTests` / `*E2ETests` / `*IntegrationTests` / `*AcceptanceTests` / `*BddTests` project, or `TestCore/` |
| `api.md`: typed clients, DTOs, status and `ProblemDetails` assertions | C# in `*ApiTests` / `*IntegrationTests`, `TestCore/**/{Http,Clients}/` |
| `web-ui.md`: `BaseTest`, locators, web-first assertions, Selenium | C# in `*UiTests` / `*E2ETests` |
| `mobile-ui.md`: screen objects, driver lifecycle, Appium waits | C# in `*AppiumTests` / `*MobileTests` |
| `bdd.md`: feature files, step definitions, hooks | `*.feature`, `StepDefinitions/` / `Steps/` / `Hooks/`, `*BddTests` / `*Bdd.Tests` |
| `test-data.md`: builders, ObjectMothers, data-driven rows | `Builders/` / `Mothers/` / `TestData/` and `*Builder.cs` / `*Mother.cs` inside a suite |
| `db-verification.md`: seeders, probes, database fixtures | `Db/` / `Database/` / `Probes/` / `Seeders/` and `*Probe.cs` / `*Seeder.cs` / `*DbFixture.cs` inside a suite |
| `performance.md`: NBomber scenarios | C# in `*PerfTests` / `*PerformanceTests` / `*LoadTests` |
| `suite-config.md`: secrets, CPM pins, `.runsettings`, Allure config | `*.runsettings`, `allureConfig.json`, `reqnroll.json`, a suite's `*.csproj` and `appsettings*.json` |

The defaults match the project names the qa-dotnet scaffolds create. They deliberately leave out unit-test projects (`*.Tests`, `*.UnitTests`), which belong to the backend plugin's own test rules, and Razor or Blazor `Pages/`, which are application code.

The source folder is `${CLAUDE_SKILL_DIR}`. The target is `<root>/.claude/rules/qa-dotnet/`.

## Procedure

1. **Find the project root**: `git rev-parse --show-toplevel`, or the working directory when it is not a git repo.
2. **Check the source**: all nine `.md` rule files listed above exist in `${CLAUDE_SKILL_DIR}`. If one is missing, stop and say so; never write a rule from memory.
3. **Copy each file** that is missing from the target: `mkdir -p <root>/.claude/rules/qa-dotnet` and `cp` it byte for byte.
4. **For each file already present**, `cmp` it with the source.
   - Identical: up to date.
   - Different: the team may have edited it. Show `diff -u <target> <source>` and ask: **replace** with the plugin's copy, **keep** theirs, or **write the plugin's copy beside it** as `<name>.plugin` to merge by hand. Never overwrite without that answer.
5. **Fit the paths to where the suites live.** C# is shared with the backend and Blazor plugins, so the defaults follow project names, not the extension. Find the automation projects: `git grep -l -E 'Include="(Microsoft\.Playwright|RestSharp|Reqnroll|Appium\.WebDriver|Selenium\.WebDriver|NBomber|Testcontainers|Microsoft\.AspNetCore\.Mvc\.Testing)' -- '*.csproj' 'Directory.Packages.props'`. A project referencing only NUnit/xUnit plus a mocking library is a unit-test project: leave it out. For each automation project whose folder no default glob matches, propose `"<dir>/**/*.cs"` for `automation.md` plus the discipline file its packages name (RestSharp or `Mvc.Testing` → `api.md`, Playwright or Selenium → `web-ui.md`, Appium → `mobile-ui.md`, Reqnroll → `bdd.md`, NBomber → `performance.md` and not `automation.md`), and `"<dir>/**/*.csproj"` for `suite-config.md`. Then look for the families the folder names miss: page objects (`git grep -l -E ':\s*(PageBase|BasePage|BaseAppiumPage)\b' -- '*.cs'`), bindings (`git grep -l '\[Binding\]' -- '*.cs'`), builders (`git grep -l -E 'class \w+(Builder|Mother)\b' -- '*.cs'` within the suites) and probes (`git grep -l -E 'Respawner|NpgsqlConnection|SqlConnection|QueryAsync<' -- '*.cs'` within the suites). Add the directory globs to the installed copies with the user's agreement; never widen a glob to `**/*.cs`.
6. **Check it will be committed**: `git check-ignore -q <root>/.claude/rules/qa-dotnet/automation.md`. If it is ignored, say so; the rules then apply on this machine only.
7. **Check for conflicts**: read the project's `CLAUDE.md` (root and `.claude/`) for test rules that contradict these files, and any other folder in `.claude/rules/` whose globs also match the suites (a backend plugin's test rules); list each contradiction. A written contradiction is the user's to settle.

## Report

```
qa-dotnet rules: <file>: installed | up to date | replaced | kept | written as .plugin   (one line per file)
Path: <root>/.claude/rules/qa-dotnet/
Suites found: <dir> (<packages>) — covered | widened with <globs>   (one line per suite)
Committed: yes | ignored by git
Conflicts: none | <one line each>
```

Then tell the user to commit the folder, and that a rule shows in `/memory` once the session has read a matching file.
