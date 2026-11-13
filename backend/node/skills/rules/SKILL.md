---
name: rules
description: Use when installing or updating the be-node coding standards as path-scoped rules in .claude/rules/be-node/. Triggers "install the Node backend rules", "set up this project". Not for reviewing code (conventions-review).
argument-hint: "[replace | keep | beside]"
---

# Install the be-node rules

Plugins cannot ship Claude Code rules, so this skill copies them into the project. Each rule file carries `paths:` frontmatter, and Claude Code loads it only once the session reads or edits a matching file, so a session that never touches persistence code never pays for the persistence rules.

`*.ts` is shared with the React, React Native and TypeScript QA plugins, often in one monorepo, so no default glob is `**/*.ts`: backend rules must not load into frontend, app or test-suite work. The defaults cover the common backend locations only, and step 5 adds the places this project really keeps its backend.

| File (beside this SKILL.md) | Loads when the session touches |
|---|---|
| `node.md`: simplicity, types, errors and async, boundaries, DI, logging, architecture, comments | `apps/api/**`, any `server/` or `backend/` folder, NestJS `*.controller` / `*.service` / `*.module` / `*.guard` / `*.interceptor` / `*.resolver` `.ts` files |
| `node-persistence.md`: Prisma, Drizzle, TypeORM, SQL | `*.prisma`, `prisma/`, `drizzle/`, `drizzle.config.ts`, `*.repository.ts` / `*.entity.ts`, `persistence/`, `repositories/` |
| `node-tests.md` | `*.test.ts` / `*.spec.ts` under `apps/api/`, `server/` or `backend/`, or beside a NestJS-named file |
| `node-config.md`: tsconfig, package.json, Vitest config, `.env` | those files at the root of `apps/api/` or of a `server/` or `backend/` folder |

The source folder is `${CLAUDE_SKILL_DIR}`. The target is `<root>/.claude/rules/be-node/`.

## Run by a person or by a model

A person types `/be-node:rules`. A model runs this skill itself, as `be-node:rules`, when it is asked to set up a project or to install or update the rules, and when it finds this plugin enabled in a project that has no `.claude/rules/be-node/`. One argument answers the differing-file question below for every file in advance: `replace`, `keep` or `beside`.

Where a step needs the user's answer or agreement and nobody is there to give it (a queued plan task, a subagent, a headless run) and no argument settles it, take the choice that changes nothing of theirs: a differing file gets the plugin's copy beside it as `<name>.plugin`, and a path or any other change to an installed copy is not made. List each one under `Waiting for the user:` in the report. Never guess the answer.

## Procedure

1. **Find the project root**: `git rev-parse --show-toplevel`, or the working directory when it is not a git repo.
2. **Check the source**: all four files exist in `${CLAUDE_SKILL_DIR}`. If one is missing, stop and say so; never write a rule from memory.
3. **Copy each file** that is missing from the target: `mkdir -p <root>/.claude/rules/be-node` and `cp` it byte for byte.
4. **For each file already present**, `cmp` it with the source.
   - Identical: up to date.
   - Different: the team may have edited it. Show `diff -u <target> <source>` and ask: **replace** with the plugin's copy, **keep** theirs, or **write the plugin's copy beside it** as `<name>.plugin` to merge by hand. Never overwrite without that answer or a `replace` argument.
5. **Fit the paths to where this project's backend lives.**
   - **Backend packages**: `git grep -l -E '"(express|@nestjs/core|fastify|hono|koa)"' -- '*package.json'`. Each hit's folder is a backend package root. When it is the root `package.json` of a single-package service, `<pkg>` below is `src` for code, `{src,test}` for tests and nothing for config, never `**`, which would also cover scripts and tooling.
   - **Schema and data access**: `git ls-files '*.prisma'`, `git grep -l -E 'pgTable\(|mysqlTable\(|@Entity\(|new PrismaClient' -- '*.ts'`.
   - **Leave out** a package that also depends on `react`, `react-native`, `expo` or `next`: propose only its server folders (`src/server/**`, `app/api/**`, `pages/api/**`), never the whole package. A package whose only test dependencies are `@playwright/test`, `webdriverio` or `@cucumber/cucumber` is a QA suite, never a backend. A Drizzle `sqliteTable` in an Expo app is mobile code, not this plugin's.
   - For each backend package root `<pkg>` that no default glob covers, propose `"<pkg>/**/*.ts"` for `node.md`, `"<pkg>/**/*.{test,spec}.ts"` for `node-tests.md` and `"<pkg>/{package.json,tsconfig*.json,vitest.config.*,.env*}"` for `node-config.md`. For each schema or data-access file the persistence globs miss, propose the narrowest directory glob that covers it for `node-persistence.md`. Show the list and add the globs to the installed copies with the user's agreement.
6. **Check it will be committed**: `git check-ignore -q <root>/.claude/rules/be-node/node.md`. If it is ignored, say so; the rules then apply on this machine only.
7. **Check for conflicts**: read the project's `CLAUDE.md` (root and `.claude/`) for TypeScript or Node rules that contradict these files and list them. A written contradiction is the user's to settle.

## Report

```
be-node rules: <file>: installed | up to date | replaced | kept | written as .plugin   (one line per file)
Path: <root>/.claude/rules/be-node/
Backend paths: default | widened with <globs>   (left out: <frontend/mobile/QA packages found>)
Committed: yes | ignored by git
Conflicts with CLAUDE.md: none | <one line each>
Waiting for the user: none | <one line each: the file or path change, and the question>
```

Then tell the user to commit the folder, and that a rule shows in `/memory` once the session has read a matching file.
