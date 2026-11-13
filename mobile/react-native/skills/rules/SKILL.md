---
name: rules
description: Use when installing or updating the React Native standards as path-scoped rules in .claude/rules/mobile-react-native/. Triggers "install the RN rules", "set up this project". Not for reviewing code (conventions-review).
argument-hint: "[replace | keep | beside]"
---

# Install the mobile-react-native rules

Plugins cannot ship Claude Code rules, so this skill copies them into the project. Each rule file carries `paths:` frontmatter, and Claude Code loads it only once the session reads or edits a matching file, so a session that never touches a test never pays for the test rules.

| File (beside this SKILL.md) | Loads when the session touches |
|---|---|
| `react-native.md`: simplicity, platform, state, data regions, network, secrets, lifecycle, permissions, comments | app `*.ts` / `*.tsx` |
| `react-native-ui.md`: components, lists, performance, styling | app `*.tsx` |
| `react-native-a11y.md`: accessibility, `testID`, motion | app `*.tsx` |
| `react-native-forms.md`: forms, i18n and formatting | app `*.tsx` |
| `react-native-data.md`: API client, retries, auth refresh, storage, offline, sync | app `*.ts` |
| `react-native-routes.md`: Expo Router navigation, params, guards, error boundaries | route files under `app/` or `src/app/` |
| `react-native-tests.md`: Jest + RNTL | `*-test.ts(x)`, `*.native.test.ts(x)` |
| `expo-config.md`: CNG, config plugins, TLS, permissions, OTA, native modules | `app.json`, `app.config.*`, `eas.json`, `plugins/**/with*`, `modules/*/{ios,android}`, `ios/`, `android/` |

"App" by default means `app/**`, `src/app/**` and the platform-extension files `*.native.*`, `*.ios.*`, `*.android.*`. TypeScript is shared with fe-react, be-node and qa-typescript, so the defaults stay this narrow; step 5 fits them to where the app really lives.

The source folder is `${CLAUDE_SKILL_DIR}`. The target is `<root>/.claude/rules/mobile-react-native/`.

## Run by a person or by a model

A person types `/mobile-react-native:rules`. A model runs this skill itself, as `mobile-react-native:rules`, when it is asked to set up a project or to install or update the rules, and when it finds this plugin enabled in a project that has no `.claude/rules/mobile-react-native/`. One argument answers the differing-file question below for every file in advance: `replace`, `keep` or `beside`.

Where a step needs the user's answer or agreement and nobody is there to give it (a queued plan task, a subagent, a headless run) and no argument settles it, take the choice that changes nothing of theirs: a differing file gets the plugin's copy beside it as `<name>.plugin`, and a path or any other change to an installed copy is not made. List each one under `Waiting for the user:` in the report. Never guess the answer.

## Procedure

1. **Find the project root**: `git rev-parse --show-toplevel`, or the working directory when it is not a git repo.
2. **Check the source**: all eight `.md` rule files exist in `${CLAUDE_SKILL_DIR}`. If one is missing, stop and say so; never write a rule from memory.
3. **Copy each file** that is missing from the target: `mkdir -p <root>/.claude/rules/mobile-react-native` and `cp` it byte for byte.
4. **For each file already present**, `cmp` it with the source.
   - Identical: up to date.
   - Different: the team may have edited it. Show `diff -u <target> <source>` and ask: **replace** with the plugin's copy, **keep** theirs, or **write the plugin's copy beside it** as `<name>.plugin` to merge by hand. Never overwrite without that answer or a `replace` argument.
5. **Fit the paths to where the app lives.** Find each React Native app: `git ls-files -- '*package.json' ':!:**/node_modules/**' | xargs grep -lE '"(expo|react-native)"[[:space:]]*:'`. Each match's folder is an app root (`<app>`, `.` at the repo root). If none matches, say so and stop at this step. For each app root, propose to the user and, with their agreement, add to the installed copies:
   - core: `<app>/**/*.{ts,tsx}`; ui, a11y and forms: `<app>/**/*.tsx`; data: `<app>/**/*.ts`.
   - routes: the folder that holds the root `_layout.tsx` (`git ls-files -- '*_layout.tsx'`), as `<that folder>/**/*.tsx`.
   - tests: `<app>/**/*.test.{ts,tsx}` and `<app>/**/__tests__/**`.
   - Expo config: `<app>/{ios,android}/**` and `<app>/modules/*/{ios,android}/**` when `<app>` is not the root, and the folder of any config plugin `app.json` names that is not `plugins/with*`.
   - **Collisions.** When `<app>` is the repo root, `**/*` globs are safe only if no other `package.json` belongs to a web, server or test package (`next`, `react-dom`, `vite`, `express`, `@nestjs/core`, `@playwright/test`); otherwise list each app folder rather than `**`. When a root `app/` or `src/app/` belongs to another package (a Next.js app), remove the default `app/**` and `src/app/**` globs from every installed file, or that app's pages load these rules.
6. **Check it will be committed**: `git check-ignore -q <root>/.claude/rules/mobile-react-native/react-native.md`. If it is ignored, say so; the rules then apply on this machine only.
7. **Check for conflicts**: read the project's `CLAUDE.md` (root and `.claude/`) for React Native rules that contradict these files and list them. A written contradiction is the user's to settle.

## Report

```
mobile-react-native rules: <file>: installed | up to date | replaced | kept | written as .plugin   (one line per file)
Path: <root>/.claude/rules/mobile-react-native/
App roots: <folders found>   Paths: default | widened with <globs> | defaults removed (<why>)
Committed: yes | ignored by git
Conflicts with CLAUDE.md: none | <one line each>
Waiting for the user: none | <one line each: the file or path change, and the question>
```

Then tell the user to commit the folder, and that a rule shows in `/memory` once the session has read a matching file.
