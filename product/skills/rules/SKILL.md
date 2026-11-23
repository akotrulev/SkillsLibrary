---
name: rules
description: Use when installing or updating the product standards for plans, feature docs, KB and backlog in .claude/rules/product/. Triggers "install the product rules". Not for writing a plan (plan-feature).
argument-hint: "[replace | keep | beside]"
---

# Install the product rules

Plugins cannot ship Claude Code rules, so this skill copies them into the project. Each rule file carries `paths:` frontmatter, and Claude Code loads it only once the session reads or edits a matching file. A Plan Queue task does open its plan, so it closes out with the standards loaded even when its agent knows nothing about plans. A session that edits the KB keeps it consistent even when no `ba-*` skill or agent is running (a plan task, `documenter`, a person fixing a typo).

The rules hold each document's **standards**: what must be in it, what must never be, ids and invariants. Templates and procedures stay in the skills.

Finished plans in `docs/plans/implemented/` match no glob on purpose: later work reads them often and never edits them. A feature spec's design sections get no rule of their own: only `/product:plan-feature` writes them, and it loads their skills.

The ten files and the documents they load for:

| File | `paths:` default |
|---|---|
| `plans.md` | `docs/plans/*.md`, `docs/plans/*/delivery-plan.md` |
| `feature-docs.md` | `docs/features/*-*.md` |
| `system-plans.md` | `docs/plans/*-system.md` |
| `backlog-stories.md` | `docs/plans/**/stories.md` |
| `business-model.md` | `docs/business-model/**/*.md` |
| `business-model-entities.md` | `docs/business-model/entities/**/*.md` |
| `business-model-flows.md` | `docs/business-model/flows/**/*.md` |
| `business-model-decisions.md` | `docs/business-model/decisions/**/*.md` |
| `business-model-connections.md` | `docs/business-model/{events,shared-data,invariants}.md` |
| `business-model-interactions.md` | `docs/business-model/interaction-map.md` |

The source folder is `${CLAUDE_SKILL_DIR}`. The target is `<root>/.claude/rules/product/`.

## Run by a model

A model runs this skill itself, as `product:rules`, when it is asked to set up a project or to install or update the rules, and when it finds this plugin enabled in a project that has no `.claude/rules/product/`. One argument answers the differing-file question below for every file in advance: `replace`, `keep` or `beside`.

Where a step needs the user's answer and nobody is there to give it (a queued plan task, a subagent, a headless run) and no argument settles it, take the choice that changes nothing of theirs and list it under `Waiting for the user:` in the report.

## Procedure

1. **Find the project root**: `git rev-parse --show-toplevel`, or the working directory when it is not a git repo.
2. **List the source**: every `*.md` in `${CLAUDE_SKILL_DIR}` except `SKILL.md`. If the list is empty, stop and say so; never write a rule from memory.
3. **Copy each file** that is missing from the target: `mkdir -p <root>/.claude/rules/product` and `cp` it byte for byte. Done when every source file is in the target.
4. **For each file already present**, `cmp` it with the source.
   - Identical: up to date.
   - Different: the team may have edited it. Show `diff -u <target> <source>` and ask: **replace** with the plugin's copy, **keep** theirs, or **write the plugin's copy beside it** as `<name>.plugin` to merge by hand. Never overwrite without that answer or a `replace` argument.

   With nobody to ask and no argument, write the plugin's copy beside it. Done when each file already present is up to date, replaced, kept or written beside as `<name>.plugin`.
5. **Retire the old folders.** Before this plugin the same rules were installed under two other names. Under `<root>/.claude/rules/`, look in the folders named `dev` and `business-analysis`. For `plans.md` and `feature-docs.md` in `dev`, and every file in `business-analysis`, `cmp` it with the plugin's file of the same name.
   - Identical: delete it.
   - Different: the team edited it, and the new copy sits in `.claude/rules/product/` already. Show `diff -u <old> <source>` and ask: **delete** the old file (its edits are lost), or **keep** it. With the `replace` argument, delete it. With the `keep` or `beside` argument, or with nobody to ask, keep it and list it under `Waiting for the user:`.
   - A file in the `dev` folder that is not `plans.md` or `feature-docs.md` is left alone (`audits.md` belongs to `engineering:rules`).

   Then retire the two files merged into `system-plans.md`, `backlog-{requirements,epics}.md`, in `<root>/.claude/rules/product/` and in the `business-analysis` folder. The plugin no longer ships them, so there is nothing to `cmp` against. Ask: **delete** it (its rules now live in `system-plans.md`, and the documents it loaded for are no longer written), or **keep** it. With the `replace` argument, delete it. With the `keep` or `beside` argument, or with nobody to ask, keep it and list it under `Waiting for the user:`.

   Remove each old folder once it is empty. Done when each old file is deleted or listed as kept.
6. **Fit the paths to where this project keeps its documents.** The defaults assume `docs/plans/`, `docs/features/` and the KB at `docs/business-model/`, all at the root. Find the real places:
   - Plans: `git grep -l -e '^## Prompts' -e '^## Close-out — every task' -- '*.md'`.
   - Feature docs: the folder holding the `docs/features`-style documents, when the project keeps them somewhere else.
   - The KB: `git ls-files '*INDEX.md' | xargs grep -l '^# Business Model'`, plus any directory named `business-model`. A KB somewhere else (a monorepo package's `docs/`, a `documentation/` folder) gets its own globs, the same suffixes under its real prefix (for example `"services/billing/docs/business-model/**/*.md"`), added to each `business-model*.md` copy.
   - System plans: `git grep -l '^## Feature prompts — paste one per session' -- '*.md'`. One outside `docs/plans/` gets its glob added to the `system-plans.md` copy.
   - Story backlogs: `git ls-files '*stories.md'`. Any outside `docs/plans/` that follow the same shape (`US<n>` stories) get the matching glob added to the `backlog-stories.md` copy. Never widen to a bare `**/stories.md`: it would load on unrelated files.
   - No KB yet: keep the defaults; the `business-analyst` agent creates it there (it loads `product:knowledge-base`, which you cannot invoke yourself).

   For each document found that no default glob covers, propose the glob that would cover it and add it to the installed copy with the user's agreement. Never widen to `**/*.md`: every README and design doc would load these rules. With nobody to ask, change no path and list each proposed glob under `Waiting for the user:` in the report. Done when every document each command lists is matched by an installed glob, or a glob is proposed for it.
7. **Check it will be committed**: `git check-ignore -q <root>/.claude/rules/product/plans.md`. If it is ignored, say so; the rules then apply on this machine only.
8. **Check for conflicts**: read the project's `CLAUDE.md` (root and `.claude/`), any `docs/plans/README.md` and any other installed rule set whose `paths:` reach `docs/plans/`, `docs/features/` or `docs/business-model/`. List every statement that differs from these files: prompt-heading shape, the `Depends on:` and `Agent:` lines, when and in which commit a prompt is deleted, branch and merge rules, how plans are numbered or filed, KB ids and invariants. The rule files already say the project wins; the list tells the user which installed lines to edit so the two never read differently. Done when each contradiction is listed, or the report says none.

## Report

```
product rules: <file>: installed | up to date | replaced | kept | written as .plugin   (one line per file)
Path: <root>/.claude/rules/product/
Old files: removed | <file kept: an old-folder file, or a backlog-{requirements,epics}.md> | none found
Document paths: default | widened with <globs>
Committed: yes | ignored by git
Conflicts: none | <one line each, with the file that states it>
Waiting for the user: none | <one line each: the file or path change, and the question>
```

Then tell the user to commit the folder, and that a rule shows in `/memory` once the session has read a matching file.

## When to use

- Installing or updating the rules.

## When NOT to use

- Writing code: the rule files apply themselves.
