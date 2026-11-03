---
name: rules
description: Use when installing or updating the qa-typescript test standards as path-scoped rules in .claude/rules/qa-typescript/. Triggers "install the QA rules". Not for reviewing tests (ui-tests-review).
disable-model-invocation: true
---

# Install the qa-typescript rules

Plugins cannot ship Claude Code rules, so this skill copies them into the project. Each rule file carries `paths:` frontmatter, and Claude Code loads it only once the session reads or edits a matching file, so a session that never touches a k6 script never pays for the k6 rules.

| File (beside this SKILL.md) | Loads when the session touches |
|---|---|
| `qa-typescript.md`: simplicity, test shape, errors, waits, async, data, secrets, flakes, comments | any TypeScript file in a test suite: `e2e/`, `*-tests/`, `tests/{api,ui,e2e,mobile,integration,…}/`, `test/specs/`, `src/specs/`, `src/pages/{web,mobile}/`, `steps/`, `playwright.config.ts`, `wdio*.conf.ts` |
| `api-tests.md`: clients, status and schema assertions, GraphQL, gRPC, DB probes | `tests/{api,integration,clients,schemas,operations,proto}/`, `api-tests/`, `apitests/`, `src/specs/`, `*Seeder.ts`, `*Probe.ts` |
| `ui-tests.md`: locators, page objects, web-first assertions, waits, auth | `e2e/`, `tests/{ui,e2e,pages,flows}/`, `ui-tests/`, `e2e-tests/`, `src/pages/web/`, `playwright.config.ts` |
| `mobile-tests.md`: screen objects, platform locators, Appium session, Maestro flows | `mobile-tests/`, `.maestro/`, `tests/mobile/`, `test/specs/`, `src/pages/mobile/`, `wdio*.conf.ts` |
| `bdd.md`: feature files and step definitions | `*.feature`, `steps/`, `step-definitions/`, `features/support/` |
| `k6.md` | `k6/`, `perf/`, `load-tests/` scripts |
| `llm-evals.md`: promptfoo and eval datasets | `promptfooconfig*.yaml`, `evals/` |
| `ci-tests.md`: the jobs that run test suites | `.github/workflows/`, `azure-pipelines*.yml`, `.azure-pipelines/`, `.gitlab-ci.yml` |

The source folder is `${CLAUDE_SKILL_DIR}`. The target is `<root>/.claude/rules/qa-typescript/`.

## Procedure

1. **Find the project root**: `git rev-parse --show-toplevel`, or the working directory when it is not a git repo.
2. **Check the source**: all eight files exist in `${CLAUDE_SKILL_DIR}`. If one is missing, stop and say so; never write a rule from memory.
3. **Copy each file** that is missing from the target: `mkdir -p <root>/.claude/rules/qa-typescript` and `cp` it byte for byte.
4. **For each file already present**, `cmp` it with the source.
   - Identical: up to date.
   - Different: the team may have edited it. Show `diff -u <target> <source>` and ask: **replace** with the plugin's copy, **keep** theirs, or **write the plugin's copy beside it** as `<name>.plugin` to merge by hand. Never overwrite without that answer.
5. **Fit the paths to where this project's suites live.** `*.ts` is shared with the app's own code and its unit tests (be-node, fe-react, mobile-react-native), so the defaults name only the usual suite folders. Find the real ones:
   - Playwright: `git ls-files '*playwright.config.*'`, then each config's `testDir`; page objects: `git grep -l -e 'readonly page: Page' -e 'from .@playwright/test.' -- '*.ts'`.
   - WebdriverIO / Appium: `git ls-files '*wdio*.conf.*'`, then its `specs`; Maestro: `git ls-files '*.yaml' | xargs grep -l '^appId:'`.
   - API suites: `git grep -l -e 'from .zod.' -- '*.spec.ts' '*.test.ts'` together with the folders holding `*Client.ts` built on the suite's base client.
   - BDD: `git ls-files '*.feature'` and the `steps` / `import` globs in `playwright.config.*` or `wdio*.conf.*`.
   - k6: `git grep -l "from 'k6" -- '*.js' '*.ts'`; evals: `git ls-files '*promptfooconfig*'`.

   For every folder found that no default glob covers, propose a directory glob (for example `"**/qa/web/**/*.ts"`) for the core file and for the matching suite file, and add it to the installed copies with the user's agreement. Never widen to `**/*.ts` or `**/*.spec.ts`: app unit tests would then load these rules. If a default glob matches app code here (a `tests/integration/` the backend owns, a `.github/workflows/` with no test jobs), offer to drop it.
6. **Check it will be committed**: `git check-ignore -q <root>/.claude/rules/qa-typescript/qa-typescript.md`. If it is ignored, say so; the rules then apply on this machine only.
7. **Check for conflicts**: read the project's `CLAUDE.md` (root and `.claude/`) for test rules that contradict these files and list them. A written contradiction is the user's to settle.

## Report

```
qa-typescript rules: <file>: installed | up to date | replaced | kept | written as .plugin   (one line per file)
Path: <root>/.claude/rules/qa-typescript/
Suite paths: default | widened with <globs> | dropped <globs>
Committed: yes | ignored by git
Conflicts with CLAUDE.md: none | <one line each>
```

Then tell the user to commit the folder, and that a rule shows in `/memory` once the session has read a matching file.
