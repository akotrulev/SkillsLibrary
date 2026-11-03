---
name: rules
description: Use when installing or updating the fe-react coding standards as path-scoped rules in .claude/rules/fe-react/. Triggers "install the React rules". Not for reviewing code (conventions-review).
disable-model-invocation: true
---

# Install the fe-react rules

Plugins cannot ship Claude Code rules, so this skill copies them into the project. Each rule file carries `paths:` frontmatter, and Claude Code loads it only once the session reads or edits a matching file, so a session that never touches a form never pays for the form rules.

| File (beside this SKILL.md) | Loads when the session touches |
|---|---|
| `react.md`: simplicity, the RSC boundary, hooks, rendering and state, types, accessibility, data regions, test ids, comments | any `*.tsx` / `*.jsx` |
| `react-data.md`: fetching, caching, timeouts, retries, Server Actions, 401 and version skew | App Router `page` / `layout` / `route` / `error` / `loading` files, `actions/`, `queries/`, `*.actions.ts`, `*.queries.ts`, `middleware.ts` |
| `react-forms.md` | `*Form*.tsx`, `forms/` |
| `react-tests.md`: Vitest + React Testing Library | `*.test.tsx` / `*.spec.tsx`, `__tests__/**/*.tsx` |
| `react-styling.md`: styling authority, tokens, dark mode, breakpoints, motion | `*.css` / `*.scss`, `tailwind.config.*`, `theme.ts`, `theme/` |

The source folder is `${CLAUDE_SKILL_DIR}`. The target is `<root>/.claude/rules/fe-react/`.

## Procedure

1. **Find the project root**: `git rev-parse --show-toplevel`, or the working directory when it is not a git repo.
2. **Check the source**: all five files exist in `${CLAUDE_SKILL_DIR}`. If one is missing, stop and say so; never write a rule from memory.
3. **Copy each file** that is missing from the target: `mkdir -p <root>/.claude/rules/fe-react` and `cp` it byte for byte.
4. **For each file already present**, `cmp` it with the source.
   - Identical: up to date.
   - Different: the team may have edited it. Show `diff -u <target> <source>` and ask: **replace** with the plugin's copy, **keep** theirs, or **write the plugin's copy beside it** as `<name>.plugin` to merge by hand. Never overwrite without that answer.
5. **Fit the paths to where the web app lives.** `*.tsx` and `*.ts` are shared with other stacks in a monorepo (a React Native or Expo app, a Node backend, a TypeScript test suite), so the default globs can load these rules for code that is not this web app's.
   - **Find the web apps**: the `package.json` files that depend on `react-dom` or `next`: `git ls-files '*package.json' | xargs grep -l -e '"react-dom"' -e '"next"'`. Each one's directory is a web app.
   - **Find the other TypeScript stacks**: `package.json` files that depend on `react-native` or `expo` (mobile), `@nestjs/core`, `express` or `fastify` (backend), or `@playwright/test` / `webdriverio` (test suites).
   - **When a web app is not the only TypeScript code in the repo**, propose rewriting every glob in the installed copies to start at the web app's directory (`"**/*.tsx"` becomes `"apps/web/**/*.tsx"`, one line per web app). An Expo Router app also has an `app/` folder, and a Node backend has `actions/` or `*.test.ts` files of its own, so this matters most for `react.md` and `react-data.md`.
   - **Widen to where the code really is.** Find the fetch code, Server Actions and query hooks: `git grep -l -e "'use server'" -e "server-only" -e 'useQuery(' -e 'useMutation(' -- '<webapp>/**/*.ts' '<webapp>/**/*.tsx'`. If a file it lists matches none of the `react-data.md` globs, propose the directory globs that would cover it (for example `"apps/web/src/lib/api/**/*.ts"`). Do the same for forms (`git grep -l 'useForm(' -- '<webapp>/**'`) and for plain logic tests: add `"<webapp>/**/*.test.ts"` to `react-tests.md`, scoped to the web app, never as a bare `**/*.test.ts`.
   - Change the installed copies only with the user's agreement, and list each glob added or rewritten.
6. **Check it will be committed**: `git check-ignore -q <root>/.claude/rules/fe-react/react.md`. If it is ignored, say so; the rules then apply on this machine only.
7. **Check for conflicts**: read the project's `CLAUDE.md` (root and `.claude/`) and any other `.claude/rules/` folder for React or front-end rules that contradict these files, and list them. A written contradiction is the user's to settle.

## Report

```
fe-react rules: <file>: installed | up to date | replaced | kept | written as .plugin   (one line per file)
Path: <root>/.claude/rules/fe-react/
Web apps: <dirs>; other TypeScript stacks: <dirs or none>
Paths: default | scoped to <dirs> | widened with <globs>
Committed: yes | ignored by git
Conflicts with CLAUDE.md: none | <one line each>
```

Then tell the user to commit the folder, and that a rule shows in `/memory` once the session has read a matching file.
