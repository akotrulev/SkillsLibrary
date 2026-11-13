---
name: rules
description: Use when installing or updating the KB and backlog standards as path-scoped rules in .claude/rules/business-analysis/. Triggers "install the BA rules", "set up this project". Not for the KB protocol (knowledge-base).
argument-hint: "[replace | keep | beside]"
---

# Install the business-analysis rules

Plugins cannot ship Claude Code rules, so this skill copies them into the project. Each rule file carries `paths:` frontmatter, and Claude Code loads it only once the session reads or edits a matching file. A session that edits the KB keeps it consistent even when no BA skill or agent is running (a plan task, `be-documenter`, a person fixing a typo), and a session that never opens a decision table never pays for its rules.

The rules hold each document's **standards**: what must be in it, what must never be, ids and invariants. Templates and procedures stay in the skills.

| File (beside this SKILL.md) | Loads when the session touches |
|---|---|
| `business-model.md`: what the KB holds, ids, traceability, annotation grammar, headers, provenance, deciding | any `docs/business-model/**/*.md` |
| `business-model-flows.md` | `docs/business-model/flows/` |
| `business-model-entities.md` | `docs/business-model/entities/` |
| `business-model-decisions.md` | `docs/business-model/decisions/` |
| `business-model-connections.md` | `events.md`, `shared-data.md`, `invariants.md` in the KB |
| `business-model-interactions.md` | the KB's `interaction-map.md` |
| `backlog-requirements.md` | `docs/plans/**/requirements.md` |
| `backlog-epics.md` | `docs/plans/**/epics.md` |
| `backlog-stories.md` | `docs/plans/**/stories.md` |

The source folder is `${CLAUDE_SKILL_DIR}`. The target is `<root>/.claude/rules/business-analysis/`.

## Run by a person or by a model

A person types `/business-analysis:rules`. A model runs this skill itself, as `business-analysis:rules`, when it is asked to set up a project or to install or update the rules, and when it finds this plugin enabled in a project that has no `.claude/rules/business-analysis/`. One argument answers the differing-file question below for every file in advance: `replace`, `keep` or `beside`.

Where a step needs the user's answer or agreement and nobody is there to give it (a queued plan task, a subagent, a headless run) and no argument settles it, take the choice that changes nothing of theirs: a differing file gets the plugin's copy beside it as `<name>.plugin`, and a path or any other change to an installed copy is not made. List each one under `Waiting for the user:` in the report. Never guess the answer.

## Procedure

1. **Find the project root**: `git rev-parse --show-toplevel`, or the working directory when it is not a git repo.
2. **Check the source**: all nine files exist in `${CLAUDE_SKILL_DIR}`. If one is missing, stop and say so; never write a rule from memory.
3. **Copy each file** that is missing from the target: `mkdir -p <root>/.claude/rules/business-analysis` and `cp` it byte for byte.
4. **For each file already present**, `cmp` it with the source.
   - Identical: up to date.
   - Different: the team may have edited it. Show `diff -u <target> <source>` and ask: **replace** with the plugin's copy, **keep** theirs, or **write the plugin's copy beside it** as `<name>.plugin` to merge by hand. Never overwrite without that answer or a `replace` argument.
5. **Fit the paths to this project.** The defaults assume the KB at `docs/business-model/` and initiative folders under `docs/plans/`, both at the root.
   - Find the KB: `git ls-files '*INDEX.md' | xargs grep -l '^# Business Model'`, plus any directory named `business-model`. A KB somewhere else (a monorepo package's `docs/`, a `documentation/` folder) gets its own globs, the same suffixes under its real prefix (for example `"services/billing/docs/business-model/**/*.md"`), added to each `business-model*.md` copy with the user's agreement.
   - Find the backlogs: `git ls-files '*requirements.md' '*epics.md' '*stories.md'`. Any outside `docs/plans/` that follow the same shape (`US<n>` stories, `E<n>` epics) get the matching glob added to the `backlog-*.md` copies, with agreement. Never widen to a bare `**/requirements.md`: it would load on unrelated files.
   - No KB yet: keep the defaults; `business-analysis:knowledge-base` creates it there.
6. **Check it will be committed**: `git check-ignore -q <root>/.claude/rules/business-analysis/business-model.md`. If it is ignored, say so; the rules then apply on this machine only.
7. **Check for conflicts**: read the project's `CLAUDE.md` (root and `.claude/`) and any other installed rule set whose `paths:` reach `docs/business-model/` or `docs/plans/` (for example a plan-format rule set). List every statement that contradicts these files. A written contradiction is the user's to settle.

## Report

```
business-analysis rules: <file>: installed | up to date | replaced | kept | written as .plugin   (one line per file)
Path: <root>/.claude/rules/business-analysis/
KB paths: default | widened with <globs>
Backlog paths: default | widened with <globs>
Committed: yes | ignored by git
Conflicts: none | <one line each, with the file that states it>
Waiting for the user: none | <one line each: the file or path change, and the question>
```

Then tell the user to commit the folder, and that a rule shows in `/memory` once the session has read a matching file.
