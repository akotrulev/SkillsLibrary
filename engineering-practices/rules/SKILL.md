---
name: rules
description: Use when installing or updating the dev standards for plans and other documents in .claude/rules/dev/. Triggers "install the dev rules", "set up this project". Not for writing a plan (plan-feature).
argument-hint: "[replace | keep | beside]"
---

# Install the dev rules

Plugins cannot ship Claude Code rules, so this skill copies them into the project. Each rule file carries `paths:` frontmatter, and Claude Code loads it only once the session reads or edits a matching file. A Plan Queue task does open its plan, so it closes out with the standards loaded even when its agent knows nothing about plans.

Finished plans in `docs/plans/implemented/` match no glob on purpose: later work reads them often and never edits them. The other files of a planning pack get no dev rule: `requirements.md`, `epics.md` and `stories.md` are the business-analysis plugin's (`/business-analysis:rules`), and the detail artifacts (`blueprint.md`, `data-model.md`, …) are written only by `solution-planner`, which loads their skills.

The source folder is `${CLAUDE_SKILL_DIR}`. The target is `<root>/.claude/rules/dev/`.

## Run by a model

A model runs this skill itself, as `dev:rules`, when it is asked to set up a project or to install or update the rules, and when it finds this plugin enabled in a project that has no `.claude/rules/dev/`. One argument answers the differing-file question below for every file in advance: `replace`, `keep` or `beside`.

Where a step needs the user's answer and nobody is there to give it (a queued plan task, a subagent, a headless run) and no argument settles it, take the choice that changes nothing of theirs and list it under `Waiting for the user:` in the report.

## Procedure

1. **Find the project root**: `git rev-parse --show-toplevel`, or the working directory when it is not a git repo.
2. **List the source**: every `*.md` in `${CLAUDE_SKILL_DIR}` except `SKILL.md`. If the list is empty, stop and say so; never write a rule from memory.
3. **Copy each file** that is missing from the target: `mkdir -p <root>/.claude/rules/dev` and `cp` it byte for byte. Done when every source file is in the target.
4. **For each file already present**, `cmp` it with the source.
   - Identical: up to date.
   - Different: the team may have edited it. Show `diff -u <target> <source>` and ask: **replace** with the plugin's copy, **keep** theirs, or **write the plugin's copy beside it** as `<name>.plugin` to merge by hand. Never overwrite without that answer or a `replace` argument.

   With nobody to ask and no argument, write the plugin's copy beside it. Done when each file already present is up to date, replaced, kept or written beside as `<name>.plugin`.
5. **Fit the paths to where this project keeps its documents.** The defaults assume `docs/plans/`. Find the real places:
   - Plans: `git grep -l -e '^## Prompts' -e '^## Close-out — every task' -- '*.md'`.
   - Audits and feature docs: the folders holding `*-audit-r*.md` / `*-requirements.md` rounds and `docs/features`-style documents, when the project keeps them somewhere else.
   - Any other rule file: read its `paths:` and look for the documents it names in the same way.

   For each document found that no default glob covers (plans in `plans/` or `docs/plan/`, a monorepo's `apps/web/docs/plans/`), propose the glob that would cover it and add it to the installed copy with the user's agreement. Never widen to `**/*.md`: every README and design doc would load these rules. With nobody to ask, change no path and list each proposed glob under `Waiting for the user:` in the report. Done when every file each command lists is matched by an installed glob, or a glob is proposed for it.
6. **Check it will be committed**: `git check-ignore -q <root>/.claude/rules/dev/plans.md`. If it is ignored, say so; the rules then apply on this machine only.
7. **Check for conflicts**: read the project's `CLAUDE.md` (root and `.claude/`) and any `docs/plans/README.md` for plan rules that differ from these files (prompt-heading shape, the `Depends on:` and `Agent:` lines, when and in which commit a prompt is deleted, branch and merge rules, how plans are numbered or filed) and list them. The rule files already say the project wins; the list tells the user which installed lines to edit so the two never read differently. Done when each contradiction is listed, or the report says none.

## Report

```
dev rules: <file>: installed | up to date | replaced | kept | written as .plugin   (one line per file)
Path: <root>/.claude/rules/dev/
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
