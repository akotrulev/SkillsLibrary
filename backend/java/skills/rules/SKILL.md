---
name: rules
description: Use when installing or updating the be-java coding standards in .claude/rules/be-java/. Triggers "install the Java rules", "set up this project". Not for reviewing code (conventions-review).
argument-hint: "[replace | keep | beside]"
---

# Install the be-java rules

Plugins cannot ship Claude Code rules, so this skill copies them into the project. Each rule file carries `paths:` frontmatter, and Claude Code loads it only once the session reads or edits a matching file.

The source folder is `${CLAUDE_SKILL_DIR}`. The target is `<root>/.claude/rules/be-java/`.

## Run by a model

A model runs this skill itself, as `be-java:rules`, when it is asked to set up a project or to install or update the rules, and when it finds this plugin enabled in a project that has no `.claude/rules/be-java/`. One argument answers the differing-file question below for every file in advance: `replace`, `keep` or `beside`.

Where a step needs the user's answer and nobody is there to give it (a queued plan task, a subagent, a headless run) and no argument settles it, take the choice that changes nothing of theirs and list it under `Waiting for the user:` in the report.

## Procedure

1. **Find the project root**: `git rev-parse --show-toplevel`, or the working directory when it is not a git repo.
2. **List the source**: every `*.md` in `${CLAUDE_SKILL_DIR}` except `SKILL.md`. If the list is empty, stop and say so; never write a rule from memory.
3. **Copy each file** that is missing from the target: `mkdir -p <root>/.claude/rules/be-java` and `cp` it byte for byte. Done when every source file is in the target.
4. **For each file already present**, `cmp` it with the source.
   - Identical: up to date.
   - Different: the team may have edited it. Show `diff -u <target> <source>` and ask: **replace** with the plugin's copy, **keep** theirs, or **write the plugin's copy beside it** as `<name>.plugin` to merge by hand. Never overwrite without that answer or a `replace` argument.

   With nobody to ask and no argument, write the plugin's copy beside it. Done when each file already present is up to date, replaced, kept or written beside as `<name>.plugin`.
5. **Fit the persistence paths to this project.** The default globs follow common naming. Find where the entities and repositories actually live: `git grep -l -e '@Entity' -e 'extends JpaRepository' -e 'extends CrudRepository' -- '*.java'`. If a file it lists matches none of the `java-persistence.md` globs, propose the directory globs that would cover them (for example `"**/orders/infrastructure/jpa/**/*.java"`) and add them to the installed copy with the user's agreement. Do the same for test sources outside `src/test` and `src/integrationTest`. With nobody to ask, change no path and list each proposed glob under `Waiting for the user:` in the report. Done when every file each command lists is matched by an installed glob, or a glob is proposed for it.
6. **Check it will be committed**: `git check-ignore -q <root>/.claude/rules/be-java/java.md`. If it is ignored, say so; the rules then apply on this machine only.
7. **Check for conflicts**: read the project's `CLAUDE.md` (root and `.claude/`) for Java rules that contradict these files and list them. A written contradiction is the user's to settle. Done when each contradiction is listed, or the report says none.

## Report

```
be-java rules: <file>: installed | up to date | replaced | kept | written as .plugin   (one line per file)
Path: <root>/.claude/rules/be-java/
Persistence paths: default | widened with <globs>
Committed: yes | ignored by git
Conflicts with CLAUDE.md: none | <one line each>
Waiting for the user: none | <one line each: the file or path change, and the question>
```

Then tell the user to commit the folder, and that a rule shows in `/memory` once the session has read a matching file.

## When to use

- Installing or updating the rules.

## When NOT to use

- Writing code: the rule files apply themselves.
