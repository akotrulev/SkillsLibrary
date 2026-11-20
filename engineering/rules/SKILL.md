---
name: rules
description: Use when installing or updating the engineering standards for audits in .claude/rules/engineering/. Triggers "install the engineering rules", "set up this project". Not for running an audit (audit).
argument-hint: "[replace | keep | beside]"
---

# Install the engineering rules

Plugins cannot ship Claude Code rules, so this skill copies them into the project. Each rule file carries `paths:` frontmatter, and Claude Code loads it only once the session reads or edits a matching file. A session that edits an audit round keeps it consistent even when no audit skill or agent is running.

The one file is `audits.md`, loaded for `docs/audits/*-requirements.md` and `docs/audits/*-audit-r*.md`.

The source folder is `${CLAUDE_SKILL_DIR}`. The target is `<root>/.claude/rules/engineering/`.

## Run by a model

A model runs this skill itself, as `engineering:rules`, when it is asked to set up a project or to install or update the rules, and when it finds this plugin enabled in a project that has no `.claude/rules/engineering/`. One argument answers the differing-file question below for every file in advance: `replace`, `keep` or `beside`.

Where a step needs the user's answer and nobody is there to give it (a queued plan task, a subagent, a headless run) and no argument settles it, take the choice that changes nothing of theirs and list it under `Waiting for the user:` in the report.

## Procedure

1. **Find the project root**: `git rev-parse --show-toplevel`, or the working directory when it is not a git repo.
2. **List the source**: every `*.md` in `${CLAUDE_SKILL_DIR}` except `SKILL.md`. If the list is empty, stop and say so; never write a rule from memory.
3. **Copy each file** that is missing from the target: `mkdir -p <root>/.claude/rules/engineering` and `cp` it byte for byte. Done when every source file is in the target.
4. **For each file already present**, `cmp` it with the source.
   - Identical: up to date.
   - Different: the team may have edited it. Show `diff -u <target> <source>` and ask: **replace** with the plugin's copy, **keep** theirs, or **write the plugin's copy beside it** as `<name>.plugin` to merge by hand. Never overwrite without that answer or a `replace` argument.

   With nobody to ask and no argument, write the plugin's copy beside it. Done when each file already present is up to date, replaced, kept or written beside as `<name>.plugin`.
5. **Retire the old folder.** Before this plugin the same rule was installed as `audits.md` in the folder named `dev` under `<root>/.claude/rules/`. `cmp` it with the plugin's `audits.md`.
   - Identical: delete it.
   - Different: the team edited it, and the new copy sits in `.claude/rules/engineering/` already. Show `diff -u <old> <source>` and ask: **delete** the old file (its edits are lost), or **keep** it. With the `replace` argument, delete it. With the `keep` or `beside` argument, or with nobody to ask, keep it and list it under `Waiting for the user:`.
   - Any other file in the `dev` folder is left alone (`plans.md` and `feature-docs.md` belong to `product:rules`).

   Remove the `dev` folder once it is empty. Done when the old file is deleted, listed as kept, or absent.
6. **Fit the paths to where this project keeps its audits.** The default assumes `docs/audits/`. Find the real place: `git ls-files '*-audit-r*.md' '*-requirements.md'`. For each document found that no default glob covers, propose the glob that would cover it and add it to the installed copy with the user's agreement. Never widen to `**/*.md`: every README and design doc would load these rules. With nobody to ask, change no path and list each proposed glob under `Waiting for the user:` in the report. Done when every audit round found is matched by an installed glob, or a glob is proposed for it.
7. **Check it will be committed**: `git check-ignore -q <root>/.claude/rules/engineering/audits.md`. If it is ignored, say so; the rules then apply on this machine only.
8. **Check for conflicts**: read the project's `CLAUDE.md` (root and `.claude/`) for audit rules that differ from `audits.md` (where rounds are saved, how they are numbered, the finding classes) and list them. The rule file already says the project wins; the list tells the user which installed lines to edit so the two never read differently. Done when each contradiction is listed, or the report says none.

## Report

```
engineering rules: audits.md: installed | up to date | replaced | kept | written as .plugin
Path: <root>/.claude/rules/engineering/
Old folder: removed | audits.md kept in the dev folder under .claude/rules | none found
Document paths: default | widened with <globs>
Committed: yes | ignored by git
Differs from the project's own rules: none | <one line each>
Waiting for the user: none | <one line each: the file or path change, and the question>
```

Then tell the user to commit the folder, and that a rule shows in `/memory` once the session has read a matching file.

## When to use

- Installing or updating the rules.

## When NOT to use

- Writing code: the rule files apply themselves.
