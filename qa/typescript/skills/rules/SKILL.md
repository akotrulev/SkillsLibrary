---
name: rules
description: Use when installing or updating the qa-typescript test standards in .claude/rules/qa-typescript/. Triggers "install the QA rules", "set up this project". Not for reviewing tests (ui-tests-review).
argument-hint: "[replace | keep | beside]"
---

# Install the qa-typescript rules

Plugins cannot ship Claude Code rules, so this skill copies them into the project. Each rule file carries `paths:` frontmatter, and Claude Code loads it only once the session reads or edits a matching file.

The source folder is `${CLAUDE_SKILL_DIR}`. The target is `<root>/.claude/rules/qa-typescript/`.

## Run by a model

A model runs this skill itself, as `qa-typescript:rules`, when it is asked to set up a project or to install or update the rules, and when it finds this plugin enabled in a project that has no `.claude/rules/qa-typescript/`. One argument answers the differing-file question below for every file in advance: `replace`, `keep` or `beside`.

Where a step needs the user's answer and nobody is there to give it (a queued plan task, a subagent, a headless run) and no argument settles it, take the choice that changes nothing of theirs and list it under `Waiting for the user:` in the report.

## Procedure

1. **Find the project root**: `git rev-parse --show-toplevel`, or the working directory when it is not a git repo.
2. **List the source**: every `*.md` in `${CLAUDE_SKILL_DIR}` except `SKILL.md`. If the list is empty, stop and say so; never write a rule from memory.
3. **Copy each file** that is missing from the target: `mkdir -p <root>/.claude/rules/qa-typescript` and `cp` it byte for byte. Done when every source file is in the target.
4. **For each file already present**, `cmp` it with the source.
   - Identical: up to date.
   - Different: the team may have edited it. Show `diff -u <target> <source>` and ask: **replace** with the plugin's copy, **keep** theirs, or **write the plugin's copy beside it** as `<name>.plugin` to merge by hand. Never overwrite without that answer or a `replace` argument.

   With nobody to ask and no argument, write the plugin's copy beside it. Done when each file already present is up to date, replaced, kept or written beside as `<name>.plugin`.
5. **Fit the paths to where this project's suites live.** `*.ts` is shared with the app's own code and its unit tests (be-node, fe-react, mobile-react-native), so the defaults name only the usual suite folders. Find the real ones:
   - Playwright: `git ls-files '*playwright.config.*'`, then each config's `testDir`; page objects: `git grep -l -e 'readonly page: Page' -e 'from .@playwright/test.' -- '*.ts'`.
   - WebdriverIO / Appium: `git ls-files '*wdio*.conf.*'`, then its `specs`; Maestro: `git ls-files '*.yaml' | xargs grep -l '^appId:'`.
   - API suites: `git grep -l -e 'from .zod.' -- '*.spec.ts' '*.test.ts'` together with the folders holding `*Client.ts` built on the suite's base client, and its `actions/` and `models/` folders when they sit outside `tests/` (`src/actions/` is not a default: front-end apps use the name).
   - BDD: `git ls-files '*.feature'` and the `steps` / `import` globs in `playwright.config.*` or `wdio*.conf.*`.
   - k6: `git grep -l "from 'k6" -- '*.js' '*.ts'`; evals: `git ls-files '*promptfooconfig*'`.
   - ESLint: `git ls-files '*eslint.config.*' '*tsconfig*.json'`; `qa-typescript-lint.md` matches both at any depth, and a project that keeps its config elsewhere gets that path added.

   For every folder found that no default glob covers, propose a directory glob (for example `"**/qa/web/**/*.ts"`) for the core file and for the matching suite file, and add it to the installed copies with the user's agreement. Never widen to `**/*.ts` or `**/*.spec.ts`: app unit tests would then load these rules. If a default glob matches app code here (a `tests/integration/` the backend owns, a `.github/workflows/` with no test jobs), offer to drop it. With nobody to ask, change no path and list each proposed glob under `Waiting for the user:` in the report. Done when every file each command lists is matched by an installed glob, or a glob is proposed for it.
6. **Check it will be committed**: `git check-ignore -q <root>/.claude/rules/qa-typescript/qa-typescript.md`. If it is ignored, say so; the rules then apply on this machine only.
7. **Check for conflicts**: read the project's `CLAUDE.md` (root and `.claude/`) for test rules that contradict these files and list them. A written contradiction is the user's to settle. Done when each contradiction is listed, or the report says none.
8. **Report lint gaps.** Read the `## Enforced by the build` table in `<root>/.claude/rules/qa-typescript/qa-typescript-lint.md`, then the project's `eslint.config.*` and `tsconfig.json`. A row is enforced when each of its ids is set to `error` for the files the row names (a rule the preset turns on counts), for a `no-restricted-*` row its selector, global, property or import is in the options, and the `tsc` row is enforced when `tsconfig.json` has the option. List every other row under `Not enforced by the build:` with its id and house rule. Never edit the project's config: the user, or a stack agent they ask, turns the rule on. Done when each table row is enforced or listed.

## Report

```
qa-typescript rules: <file>: installed | up to date | replaced | kept | written as .plugin   (one line per file)
Path: <root>/.claude/rules/qa-typescript/
Suite paths: default | widened with <globs> | dropped <globs>
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
