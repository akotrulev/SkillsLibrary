---
name: rules
description: Use when installing or updating the fe-react coding standards in .claude/rules/fe-react/. Triggers "install the React rules", "set up this project". Not for reviewing code (conventions-review).
argument-hint: "[replace | keep | beside]"
---

# Install the fe-react rules

Plugins cannot ship Claude Code rules, so this skill copies them into the project. Each rule file carries `paths:` frontmatter, and Claude Code loads it only once the session reads or edits a matching file.

The source folder is `${CLAUDE_SKILL_DIR}`. The target is `<root>/.claude/rules/fe-react/`.

## Run by a model

A model runs this skill itself, as `fe-react:rules`, when it is asked to set up a project or to install or update the rules, and when it finds this plugin enabled in a project that has no `.claude/rules/fe-react/`. One argument answers the differing-file question below for every file in advance: `replace`, `keep` or `beside`.

Where a step needs the user's answer and nobody is there to give it (a queued plan task, a subagent, a headless run) and no argument settles it, take the choice that changes nothing of theirs and list it under `Waiting for the user:` in the report.

## Procedure

1. **Find the project root**: `git rev-parse --show-toplevel`, or the working directory when it is not a git repo.
2. **List the source**: every `*.md` in `${CLAUDE_SKILL_DIR}` except `SKILL.md`. If the list is empty, stop and say so; never write a rule from memory.
3. **Copy each file** that is missing from the target: `mkdir -p <root>/.claude/rules/fe-react` and `cp` it byte for byte. Done when every source file is in the target.
4. **For each file already present**, `cmp` it with the source.
   - Identical: up to date.
   - Different: the team may have edited it. Show `diff -u <target> <source>` and ask: **replace** with the plugin's copy, **keep** theirs, or **write the plugin's copy beside it** as `<name>.plugin` to merge by hand. Never overwrite without that answer or a `replace` argument.

   With nobody to ask and no argument, write the plugin's copy beside it. Done when each file already present is up to date, replaced, kept or written beside as `<name>.plugin`.
5. **Fit the paths to where the web app lives.** `*.tsx` and `*.ts` are shared with other stacks in a monorepo (a React Native or Expo app, a Node backend, a TypeScript test suite), so the default globs can load these rules for code that is not this web app's.
   - **Find the web apps**: the `package.json` files that depend on `react-dom` or `next`: `git ls-files '*package.json' | xargs grep -l -e '"react-dom"' -e '"next"'`. Each one's directory is a web app.
   - **Find the other TypeScript stacks**: `package.json` files that depend on `react-native` or `expo` (mobile), `@nestjs/core`, `express` or `fastify` (backend), or `@playwright/test` / `webdriverio` (test suites).
   - **When a web app is not the only TypeScript code in the repo**, propose rewriting every glob in the installed copies to start at the web app's directory (`"**/*.tsx"` becomes `"apps/web/**/*.tsx"`, one line per web app). An Expo Router app also has an `app/` folder, and a Node backend has `actions/` or `*.test.ts` files of its own, so this matters most for `react.md` and `react-data.md`.
   - **Widen to where the code really is.** Find the fetch code, Server Actions and query hooks: `git grep -l -e "'use server'" -e "server-only" -e 'useQuery(' -e 'useMutation(' -- '<webapp>/**/*.ts' '<webapp>/**/*.tsx'`. If a file it lists matches none of the `react-data.md` globs, propose the directory globs that would cover it (for example `"apps/web/src/lib/api/**/*.ts"`). Do the same for forms (`git grep -l 'useForm(' -- '<webapp>/**'`) and for plain logic tests: add `"<webapp>/**/*.test.ts"` to `react-tests.md`, scoped to the web app, never as a bare `**/*.test.ts`.
   - **Lint config**: `git ls-files -- '*eslint.config.*' '*.eslintrc*' '*tsconfig*.json'`. `react-lint.md` matches `eslint.config.*` and `tsconfig*.json` at any depth; propose a glob only for a shared lint-config package whose files carry other names.
   - Change the installed copies only with the user's agreement, and list each glob added or rewritten.

   With nobody to ask, change no path and list each proposed glob under `Waiting for the user:` in the report. Done when every file each command lists is matched by an installed glob, or a glob is proposed for it.
6. **Check it will be committed**: `git check-ignore -q <root>/.claude/rules/fe-react/react.md`. If it is ignored, say so; the rules then apply on this machine only.
7. **Check for conflicts**: read the project's `CLAUDE.md` (root and `.claude/`) and any other `.claude/rules/` folder for React or front-end rules that contradict these files, and list them. A written contradiction is the user's to settle. Done when each contradiction is listed, or the report says none.
8. **Report lint gaps.** Read the `## Enforced by the build` table in `<root>/.claude/rules/fe-react/react-lint.md`, then the project's `eslint.config.*` (and any shared config it imports) and `tsconfig*.json`. A row is enforced when its rule id is `error` in a config object that matches the files the rule is about, `eslint-config-next/core-web-vitals` counting for the ids it sets to `error` itself, and, for a `no-restricted-*` row, its selector or global is in that rule's options; a `tsc` row is enforced when its option is `true` in `tsconfig.json`. A row for `react-hooks/set-state-in-effect` or `react-hooks/static-components` is listed when the project's `eslint-plugin-react-hooks` is below 7. A project still on `.eslintrc*` has no flat config, so every row is listed. List every other row under `Not enforced by the build:` with its id and house rule. Never edit the project's config: the user, or a stack agent they ask, turns the rule on. Done when each table row is enforced or listed.

## Report

```
fe-react rules: <file>: installed | up to date | replaced | kept | written as .plugin   (one line per file)
Path: <root>/.claude/rules/fe-react/
Web apps: <dirs>; other TypeScript stacks: <dirs or none>
Paths: default | scoped to <dirs> | widened with <globs>
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
