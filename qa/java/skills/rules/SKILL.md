---
name: rules
description: Use when installing or updating the qa-java test-automation standards as path-scoped rules in .claude/rules/qa-java/. Triggers "install the QA Java rules", "set up this project". Not for reviewing tests (api-tests-review).
argument-hint: "[replace | keep | beside]"
---

# Install the qa-java rules

Plugins cannot ship Claude Code rules, so this skill copies them into the project. Each rule file carries `paths:` frontmatter, and Claude Code loads it only once the session reads or edits a matching file, so a session that never touches a Gatling simulation never pays for the performance rules.

| File (beside this SKILL.md) | Loads when the session touches |
|---|---|
| `qa-java.md`: simplicity, lifecycle, isolation, assertions, waits, secrets, reporting, flakes, comments | test-module folders (`apitests`, `ui-tests`, `e2e`, …), role folders under test sources (`tests`, `pages`, `clients`, `steps`, `builders`, …), `pom/` under `src/main`, `src/gatling` |
| `qa-java-api.md`: clients, DTOs, status and error assertions | `apitests` / `api-tests`, `clients/` and `models/` under test sources, `*Client` / `*Dto` test files |
| `qa-java-ui.md`: locators, page objects, drivers, waits, Appium | `uitests` / `ui-tests` / `mobile-tests` / `e2e`, `pages/` `screens/` `components/` `flows/` under test sources, `*Page` / `*Screen` test files, `pom/` |
| `qa-java-bdd.md`: feature files, glue, hooks | `*.feature`, `steps/` `stepdefs/` `glue/` `hooks/`, `*Steps` / `*Hooks` |
| `qa-java-data.md`: builders, seeders, probes, Testcontainers | `builders/` `mothers/` `db/` `probes/` `seeders/`, `*Builder` / `*Mother` / `*Probe` / `*Seeder` under test sources |
| `qa-java-perf.md`: Gatling | `src/gatling/`, `*Simulation.java` |
| `qa-java-suite.md`: TestNG, Allure, test-module builds | `testng*.xml`, `allure` / `junit-platform` / `cucumber` properties, `categories.json`, test-module build files |
| `qa-java-ci.md`: test pipelines | test, Allure and perf workflows, `azure-pipelines*.yml`, `.gitlab-ci.yml` |

The source folder is `${CLAUDE_SKILL_DIR}`. The target is `<root>/.claude/rules/qa-java/`.

The be-java plugin installs `java-tests.md` for unit tests (`src/test`, `*Test` / `*IT`). The two sets do not conflict; a file both match loads both.

## Run by a person or by a model

A person types `/qa-java:rules`. A model runs this skill itself, as `qa-java:rules`, when it is asked to set up a project or to install or update the rules, and when it finds this plugin enabled in a project that has no `.claude/rules/qa-java/`. One argument answers the differing-file question below for every file in advance: `replace`, `keep` or `beside`.

Where a step needs the user's answer or agreement and nobody is there to give it (a queued plan task, a subagent, a headless run) and no argument settles it, take the choice that changes nothing of theirs: a differing file gets the plugin's copy beside it as `<name>.plugin`, and a path or any other change to an installed copy is not made. List each one under `Waiting for the user:` in the report. Never guess the answer.

## Procedure

1. **Find the project root**: `git rev-parse --show-toplevel`, or the working directory when it is not a git repo.
2. **Check the source**: all eight rule files exist in `${CLAUDE_SKILL_DIR}`. If one is missing, stop and say so; never write a rule from memory.
3. **Copy each file** that is missing from the target: `mkdir -p <root>/.claude/rules/qa-java` and `cp` it byte for byte.
4. **For each file already present**, `cmp` it with the source.
   - Identical: up to date.
   - Different: the team may have edited it. Show `diff -u <target> <source>` and ask: **replace** with the plugin's copy, **keep** theirs, or **write the plugin's copy beside it** as `<name>.plugin` to merge by hand. Never overwrite without that answer or a `replace` argument.
5. **Fit the paths to where this project's suites live.** The defaults follow the library's layouts; Java test code shares its extension with production code, so they stay narrow on purpose. Find the real locations:
   - Test modules: `git grep -l -e org.testng -e io.rest-assured -e com.microsoft.playwright -e io.appium -e io.cucumber -e io.gatling -- '*build.gradle*' '*pom.xml'`. A module directory none of the `qa-java.md` globs covers gets `"<module>/**/*.java"` there and its build file in `qa-java-suite.md`. When the whole repository is a test-automation project (no production code), propose `"**/*.java"` for `qa-java.md`.
   - API: `git grep -l -e 'extends BaseApiClient' -e 'io.restassured' -e APIRequestContext -- '*.java'`, for `qa-java-api.md`.
   - UI: `git grep -l -e 'com.microsoft.playwright.Page;' -e 'org.openqa.selenium.WebDriver;' -e 'io.appium.java_client' -- '*.java'`, for `qa-java-ui.md`.
   - BDD: `git ls-files '*.feature'` and `git grep -l io.cucumber.java -- '*.java'`, for `qa-java-bdd.md`.
   - Data: `git grep -l -e NamedParameterJdbcTemplate -e org.testcontainers -e 'class .*Builder' -- '*.java'` within the test modules, for `qa-java-data.md`.
   - Perf: `git grep -l io.gatling.javaapi -- '*.java'`, for `qa-java-perf.md`.
   - CI: `git grep -l -e 'gradlew' -e 'mvn ' -e allure -- '.github/workflows' '*pipelines*' '.gitlab-ci.yml'`, for `qa-java-ci.md`.

   For each file a search lists that its rule file's globs miss, propose the directory glob that covers it (for example `"**/checkout-tests/src/test/java/**/*.java"`) and add it to the installed copy with the user's agreement. Never widen a glob onto production source.
6. **Check it will be committed**: `git check-ignore -q <root>/.claude/rules/qa-java/qa-java.md`. If it is ignored, say so; the rules then apply on this machine only.
7. **Check for conflicts**: read the project's `CLAUDE.md` (root and `.claude/`) and any installed `.claude/rules/be-java/java-tests.md` for test rules that contradict these files, and list them. A written contradiction is the user's to settle.

## Report

```
qa-java rules: <file>: installed | up to date | replaced | kept | written as .plugin   (one line per file)
Path: <root>/.claude/rules/qa-java/
Suite paths: default | widened with <file>: <globs>   (one line per widened file)
Committed: yes | ignored by git
Conflicts with CLAUDE.md or be-java rules: none | <one line each>
Waiting for the user: none | <one line each: the file or path change, and the question>
```

Then tell the user to commit the folder, and that a rule shows in `/memory` once the session has read a matching file.
