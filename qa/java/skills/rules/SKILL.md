---
name: rules
description: Use when installing or updating the qa-java test standards in .claude/rules/qa-java/. Triggers "install the QA Java rules", "set up this project". Not for reviewing tests (api-tests-review).
argument-hint: "[replace | keep | beside]"
---

# Install the qa-java rules

Plugins cannot ship Claude Code rules, so this skill copies them into the project. Each rule file carries `paths:` frontmatter, and Claude Code loads it only once the session reads or edits a matching file.

The source folder is `${CLAUDE_SKILL_DIR}`. The target is `<root>/.claude/rules/qa-java/`.

The be-java plugin installs `java-tests.md` for unit tests (`src/test`, `*Test` / `*IT`). The two sets do not conflict; a file both match loads both.

## Run by a model

A model runs this skill itself, as `qa-java:rules`, when it is asked to set up a project or to install or update the rules, and when it finds this plugin enabled in a project that has no `.claude/rules/qa-java/`. One argument answers the differing-file question below for every file in advance: `replace`, `keep` or `beside`.

Where a step needs the user's answer and nobody is there to give it (a queued plan task, a subagent, a headless run) and no argument settles it, take the choice that changes nothing of theirs and list it under `Waiting for the user:` in the report.

## Procedure

1. **Find the project root**: `git rev-parse --show-toplevel`, or the working directory when it is not a git repo.
2. **List the source**: every `*.md` in `${CLAUDE_SKILL_DIR}` except `SKILL.md`. If the list is empty, stop and say so; never write a rule from memory.
3. **Copy each file** that is missing from the target: `mkdir -p <root>/.claude/rules/qa-java` and `cp` it byte for byte. Done when every source file is in the target.
4. **For each file already present**, `cmp` it with the source.
   - Identical: up to date.
   - Different: the team may have edited it. Show `diff -u <target> <source>` and ask: **replace** with the plugin's copy, **keep** theirs, or **write the plugin's copy beside it** as `<name>.plugin` to merge by hand. Never overwrite without that answer or a `replace` argument.

   With nobody to ask and no argument, write the plugin's copy beside it. Done when each file already present is up to date, replaced, kept or written beside as `<name>.plugin`.
5. **Fit the paths to where this project's suites live.** The defaults follow the library's layouts; Java test code shares its extension with production code, so they stay narrow on purpose. Find the real locations:
   - Test modules: `git grep -l -e org.testng -e io.rest-assured -e com.microsoft.playwright -e io.appium -e io.cucumber -e io.gatling -- '*build.gradle*' '*pom.xml'`. A module directory none of the `qa-java.md` globs covers gets `"<module>/**/*.java"` there and its build file in `qa-java-suite.md`. When the whole repository is a test-automation project (no production code), propose `"**/*.java"` for `qa-java.md`.
   - API: `git grep -l -e 'extends BaseApiClient' -e 'io.restassured' -e APIRequestContext -- '*.java'`, for `qa-java-api.md`.
   - UI: `git grep -l -e 'com.microsoft.playwright.Page;' -e 'org.openqa.selenium.WebDriver;' -e 'io.appium.java_client' -- '*.java'`, for `qa-java-ui.md` and `qa-java-page-objects.md`.
   - BDD: `git ls-files '*.feature'` and `git grep -l io.cucumber.java -- '*.java'`, for `qa-java-bdd.md`.
   - Data: `git grep -l -e NamedParameterJdbcTemplate -e org.testcontainers -e 'class .*Builder' -- '*.java'` within the test modules, for `qa-java-data.md`.
   - Perf: `git grep -l io.gatling.javaapi -- '*.java'`, for `qa-java-perf.md`.
   - CI: `git grep -l -e 'gradlew' -e 'mvn ' -e allure -- '.github/workflows' '*pipelines*' '.gitlab-ci.yml'`, for `qa-java-ci.md`.

   For each file a search lists that its rule file's globs miss, propose the directory glob that covers it (for example `"**/checkout-tests/src/test/java/**/*.java"`) and add it to the installed copy with the user's agreement. Never widen a glob onto production source. With nobody to ask, change no path and list each proposed glob under `Waiting for the user:` in the report. Done when every file each command lists is matched by an installed glob, or a glob is proposed for it.
6. **Check it will be committed**: `git check-ignore -q <root>/.claude/rules/qa-java/qa-java.md`. If it is ignored, say so; the rules then apply on this machine only.
7. **Check for conflicts**: read the project's `CLAUDE.md` (root and `.claude/`) and any installed `.claude/rules/be-java/java-tests.md` for test rules that contradict these files, and list them. A written contradiction is the user's to settle. Done when each contradiction is listed, or the report says none.

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

## When to use

- Installing or updating the rules.

## When NOT to use

- Writing code: the rule files apply themselves.
