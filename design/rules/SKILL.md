---
name: rules
description: Use when installing or updating the design-token and UI-copy standards as path-scoped rules in .claude/rules/design/. Triggers "install the design rules", "set up this project". Not for building tokens (tokens).
argument-hint: "[replace | keep | beside]"
---

# Install the design rules

Plugins cannot ship Claude Code rules, so this skill copies them into the project. Each rule file carries `paths:` frontmatter, and Claude Code loads it only once the session reads or edits a matching file, so a session that never opens the token file never pays for the token rules.

The design plugin owns no source files: components, stylesheets and screens are governed by the `fe-*` and `mobile-*` rule sets. These two files cover only what those do not, the token system and the words in the message catalogs, and they load beside the stack's rules on a shared file without contradicting them.

| File (beside this SKILL.md) | Loads when the session touches |
|---|---|
| `design-tokens.md`: tiers, naming, scales, status and chart colour groups, theming as a swap, brand fidelity, delivery format | `tokens.{css,scss,json}`, `*.tokens`, `*.tokens.json`, `tokens/`, `design-tokens/` |
| `ui-copy.md`: labels, names, errors, empty states, sentence case, confirmations | `messages/*.json`, `locales/**/*.json`, `*.xcstrings`, `res/values*/strings.xml` |

The source folder is `${CLAUDE_SKILL_DIR}`. The target is `<root>/.claude/rules/design/`.

## Run by a person or by a model

A person types `/design:rules`. A model runs this skill itself, as `design:rules`, when it is asked to set up a project or to install or update the rules, and when it finds this plugin enabled in a project that has no `.claude/rules/design/`. One argument answers the differing-file question below for every file in advance: `replace`, `keep` or `beside`.

Where a step needs the user's answer or agreement and nobody is there to give it (a queued plan task, a subagent, a headless run) and no argument settles it, take the choice that changes nothing of theirs: a differing file gets the plugin's copy beside it as `<name>.plugin`, and a path or any other change to an installed copy is not made. List each one under `Waiting for the user:` in the report. Never guess the answer.

## Procedure

1. **Find the project root**: `git rev-parse --show-toplevel`, or the working directory when it is not a git repo.
2. **Check the source**: both files exist in `${CLAUDE_SKILL_DIR}`. If one is missing, stop and say so; never write a rule from memory.
3. **Copy each file** that is missing from the target: `mkdir -p <root>/.claude/rules/design` and `cp` it byte for byte.
4. **For each file already present**, `cmp` it with the source.
   - Identical: up to date.
   - Different: the team may have edited it. Show `diff -u <target> <source>` and ask: **replace** with the plugin's copy, **keep** theirs, or **write the plugin's copy beside it** as `<name>.plugin` to merge by hand. Never overwrite without that answer or a `replace` argument.
5. **Fit the paths to where this project keeps its tokens and its copy.** The defaults only catch files named for the purpose. Most apps keep tokens in a general stylesheet, and a glob as wide as `**/*.css` would load the token rules on every stylesheet, so propose **exact file paths**, never a wider pattern.
   - **Tokens**: the files that define them. `git grep -l -E '^\s*--[a-z0-9-]+\s*:' -- '*.css' '*.scss'`, kept to those with a `:root`, `[data-theme` or `@theme` block (a `globals.css`, `app.css`, `wwwroot/css/tokens.css`); `git grep -l '"\$value"' -- '*.json'` for DTCG files; the theme file of a component library (`git grep -l -e 'createTheme(' -e 'extendTheme(' -e 'MudTheme'`). In a mobile app, the Compose `ui/theme/Color.kt` and `Type.kt`, an iOS `*.xcassets/**/*.colorset/Contents.json`, a React Native `theme.ts`. Propose each one as a literal path (`"apps/web/src/app/globals.css"`).
   - **Copy**: the catalogs the UI reads. next-intl `messages/`, i18next `locales/`, a Blazor or MAUI client's `Resources/**/*.resx`, `*.po`, `*.xlf`, `*.arb`. Scope a `.resx` glob to the UI project (`"src/Shop.Client/Resources/**/*.resx"`), never a bare `**/*.resx`, which also catches a backend's resource files. If a default glob matches something that is not UI copy (a `messages/` folder of queue schemas), narrow it to the UI app's directory.
   - Change the installed copies only with the user's agreement, and list each glob added or narrowed.
6. **Check it will be committed**: `git check-ignore -q <root>/.claude/rules/design/design-tokens.md`. If it is ignored, say so; the rules then apply on this machine only.
7. **Check for conflicts**: read the project's `CLAUDE.md` (root and `.claude/`) and the other `.claude/rules/` folders (`fe-react`, `fe-blazor`, `mobile-*`) for token or copy rules that contradict these files (a Title Case house style, a third token tier the project mandates, a different dark-mode mechanism), and list them. A written contradiction is the user's to settle.

## Report

```
design rules: <file>: installed | up to date | replaced | kept | written as .plugin   (one line per file)
Path: <root>/.claude/rules/design/
Token paths: default | added <paths>
Copy paths: default | added <globs> | narrowed <globs>
Committed: yes | ignored by git
Conflicts with CLAUDE.md or other rules: none | <one line each>
Waiting for the user: none | <one line each: the file or path change, and the question>
```

Then tell the user to commit the folder, and that a rule shows in `/memory` once the session has read a matching file.
