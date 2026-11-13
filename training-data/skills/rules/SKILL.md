---
name: rules
description: Use when installing or updating the training-data standards as path-scoped rules in .claude/rules/training-data/. Triggers "install the dataset rules", "set up this project". Not for a record schema (dataset-formats).
argument-hint: "[replace | keep | beside]"
---

# Install the training-data rules

Plugins cannot ship Claude Code rules, so this skill copies them into the project. Each rule file carries `paths:` frontmatter, and Claude Code loads it only once the session reads or edits a matching file, so a session that hand-fixes a record, a plan task that adds a split, or a review of a dataset card meets the standards without running the `dataset-engineer` agent.

| File (beside this SKILL.md) | Loads when the session touches |
|---|---|
| `datasets.md`: JSONL, envelope and provenance, chat/tool/preference/VLM records, splits, decontamination, PII | any `*.jsonl` or `manifest.json` under a `datasets/` folder |
| `eval-sets.md`: the frozen test split, canaries, gold answers, scoring, coverage | `test*.jsonl` (and a sharded `test/`) under a `datasets/` folder |
| `dataset-docs.md`: the dataset card and the audit report | any `.md` under `docs/datasets/` |

Pipeline scripts get no rule file here: they have no fixed location, and they are code in the project's stack, whose plugin's rules apply to them.

The source folder is `${CLAUDE_SKILL_DIR}`. The target is `<root>/.claude/rules/training-data/`.

## Run by a person or by a model

A person types `/training-data:rules`. A model runs this skill itself, as `training-data:rules`, when it is asked to set up a project or to install or update the rules, and when it finds this plugin enabled in a project that has no `.claude/rules/training-data/`. One argument answers the differing-file question below for every file in advance: `replace`, `keep` or `beside`.

Where a step needs the user's answer or agreement and nobody is there to give it (a queued plan task, a subagent, a headless run) and no argument settles it, take the choice that changes nothing of theirs: a differing file gets the plugin's copy beside it as `<name>.plugin`, and a path or any other change to an installed copy is not made. List each one under `Waiting for the user:` in the report. Never guess the answer.

## Procedure

1. **Find the project root**: `git rev-parse --show-toplevel`, or the working directory when it is not a git repo.
2. **Check the source**: all three files exist in `${CLAUDE_SKILL_DIR}`. If one is missing, stop and say so; never write a rule from memory.
3. **Copy each file** that is missing from the target: `mkdir -p <root>/.claude/rules/training-data` and `cp` it byte for byte.
4. **For each file already present**, `cmp` it with the source.
   - Identical: up to date.
   - Different: the team may have edited it. Show `diff -u <target> <source>` and ask: **replace** with the plugin's copy, **keep** theirs, or **write the plugin's copy beside it** as `<name>.plugin` to merge by hand. Never overwrite without that answer or a `replace` argument.
5. **Fit the paths to where this project keeps its data.** The defaults follow the plugin's layout (`datasets/<name>/`, `docs/datasets/`). Datasets are often git-ignored or in LFS, so look on disk as well as in git:
   - Datasets: `find . -name manifest.json -not -path '*/node_modules/*'` and `find . -name '*.jsonl' -not -path '*/node_modules/*' | sed 's|/[^/]*$||' | sort -u`. A folder that holds training records (an `id`/`source`/`license` envelope, `messages`, `text` or `chosen`) and is not under a `datasets/` folder gets a directory glob, for example `"**/data/sft/**/*.jsonl"`, in `datasets.md`, and its test files one in `eval-sets.md`.
   - Cards: `find . -name '*-card.md'` and the `card` field of each manifest. A card outside `docs/datasets/` gets its own glob in `dataset-docs.md`.

   Propose each glob and add it to the installed copy with the user's agreement. Never widen to `**/*.jsonl`: logs, fixtures and exports would then load these rules. If a default glob matches something here that is not training data (a `datasets/` package of loader code holding JSONL fixtures), offer to narrow it.
6. **Check it will be committed**: `git check-ignore -q <root>/.claude/rules/training-data/datasets.md`. If it is ignored, say so; the rules then apply on this machine only.
7. **Check for conflicts**: read the project's `CLAUDE.md` (root and `.claude/`) for data rules that contradict these files and list them. A written contradiction is the user's to settle.

## Report

```
training-data rules: <file>: installed | up to date | replaced | kept | written as .plugin   (one line per file)
Path: <root>/.claude/rules/training-data/
Dataset paths: default | widened with <globs> | narrowed <globs>
Committed: yes | ignored by git
Conflicts with CLAUDE.md: none | <one line each>
Waiting for the user: none | <one line each: the file or path change, and the question>
```

Then tell the user to commit the folder, and that a rule shows in `/memory` once the session has read a matching file.
