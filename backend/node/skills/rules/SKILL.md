---
name: rules
description: Use when installing or updating the be-node coding standards in .claude/rules/be-node/. Triggers "install the Node backend rules", "set up this project". Not for reviewing code (conventions-review).
argument-hint: "[replace | keep | beside]"
---

# Install the be-node rules

Plugins cannot ship Claude Code rules, so this skill copies them into the project. Each rule file carries `paths:` frontmatter, and Claude Code loads it only once the session reads or edits a matching file.

`*.ts` is shared with the React, React Native and TypeScript QA plugins, often in one monorepo, so no default glob is `**/*.ts`: backend rules must not load into frontend, app or test-suite work. The defaults cover the common backend locations only, and step 5 adds the places this project really keeps its backend.

The source folder is `${CLAUDE_SKILL_DIR}`. The target is `<root>/.claude/rules/be-node/`.

## Run by a model

A model runs this skill itself, as `be-node:rules`, when it is asked to set up a project or to install or update the rules, and when it finds this plugin enabled in a project that has no `.claude/rules/be-node/`. One argument answers the differing-file question below for every file in advance: `replace`, `keep` or `beside`.

Where a step needs the user's answer and nobody is there to give it (a queued plan task, a subagent, a headless run) and no argument settles it, take the choice that changes nothing of theirs and list it under `Waiting for the user:` in the report.

## Procedure

1. **Find the project root**: `git rev-parse --show-toplevel`, or the working directory when it is not a git repo.
2. **List the source**: every `*.md` in `${CLAUDE_SKILL_DIR}` except `SKILL.md`. If the list is empty, stop and say so; never write a rule from memory.
3. **Copy each file** that is missing from the target: `mkdir -p <root>/.claude/rules/be-node` and `cp` it byte for byte. Done when every source file is in the target.
4. **For each file already present**, `cmp` it with the source.
   - Identical: up to date.
   - Different: the team may have edited it. Show `diff -u <target> <source>` and ask: **replace** with the plugin's copy, **keep** theirs, or **write the plugin's copy beside it** as `<name>.plugin` to merge by hand. Never overwrite without that answer or a `replace` argument.

   With nobody to ask and no argument, write the plugin's copy beside it. Done when each file already present is up to date, replaced, kept or written beside as `<name>.plugin`.
5. **Fit the paths to where this project's backend lives.**
   - **Backend packages**: `git grep -l -E '"(express|@nestjs/core|fastify|hono|koa)"' -- '*package.json'`. Each hit's folder is a backend package root. When it is the root `package.json` of a single-package service, `<pkg>` below is `src` for code, `{src,test}` for tests and nothing for config, never `**`, which would also cover scripts and tooling.
   - **Schema and data access**: `git ls-files '*.prisma'`, `git grep -l -E 'pgTable\(|mysqlTable\(|@Entity\(|new PrismaClient' -- '*.ts'`.
   - **Leave out** a package that also depends on `react`, `react-native`, `expo` or `next`: propose only its server folders (`src/server/**`, `app/api/**`, `pages/api/**`), never the whole package. A package whose only test dependencies are `@playwright/test`, `webdriverio` or `@cucumber/cucumber` is a QA suite, never a backend. A Drizzle `sqliteTable` in an Expo app is mobile code, not this plugin's.
   - **Lint config**: `git ls-files -- '*eslint.config.*' '*.eslintrc*' '*tsconfig*.json'`. `node-lint.md` matches `eslint.config.*` and `tsconfig*.json` at any depth; propose a glob only for a shared lint-config package whose files carry other names.
   - For each backend package root `<pkg>` that no default glob covers, propose `"<pkg>/**/*.ts"` for `node.md`, `"<pkg>/**/*.{test,spec}.ts"` for `node-tests.md` and `"<pkg>/{package.json,tsconfig*.json,vitest.config.*,.env*}"` for `node-config.md`. For each schema or data-access file the persistence globs miss, propose the narrowest directory glob that covers it for `node-persistence.md`. Show the list and add the globs to the installed copies with the user's agreement.

   With nobody to ask, change no path and list each proposed glob under `Waiting for the user:` in the report. Done when every file each command lists is matched by an installed glob, or a glob is proposed for it.
6. **Check it will be committed**: `git check-ignore -q <root>/.claude/rules/be-node/node.md`. If it is ignored, say so; the rules then apply on this machine only.
7. **Check for conflicts**: read the project's `CLAUDE.md` (root and `.claude/`) for TypeScript or Node rules that contradict these files and list them. A written contradiction is the user's to settle. Done when each contradiction is listed, or the report says none.
8. **Report lint gaps.** Read the `## Enforced by the build` table in `<root>/.claude/rules/be-node/node-lint.md`, then the project's `eslint.config.*` (and any shared config it imports) and `tsconfig*.json`. A row is enforced when its rule id is `error` in a config object that matches the files the rule is about and, for a `no-restricted-*` row, its property, selector or global is in that rule's options; a `tsc` row is enforced when its option is `true` in `tsconfig.json`. A project still on `.eslintrc*` has no flat config, so every row is listed. List every other row under `Not enforced by the build:` with its id and house rule. Never edit the project's config: the user, or a stack agent they ask, turns the rule on. Done when each table row is enforced or listed.

## Report

```
be-node rules: <file>: installed | up to date | replaced | kept | written as .plugin   (one line per file)
Path: <root>/.claude/rules/be-node/
Backend paths: default | widened with <globs>   (left out: <frontend/mobile/QA packages found>)
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
