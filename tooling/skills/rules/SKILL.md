---
name: rules
description: Use when installing or updating the tool-contract standards as a path-scoped rule in .claude/rules/tooling/. Triggers "install the tooling rules", "set up this project". Not for writing a contract (capability-contract).
argument-hint: "[replace | keep | beside]"
---

# Install the tooling rules

Plugins cannot ship Claude Code rules, so this skill copies them into the project. A rule file carries `paths:` frontmatter, and Claude Code loads it only once the session reads or edits a matching file, so a planning session or a backend task that changes a tool contract meets its standards without running the `tooling-engineer` agent.

| File (beside this SKILL.md) | Loads when the session touches |
|---|---|
| `tool-contract.md`: the capability table, ids, kinds, contract blocks, flows, secrets, and the envelope, error, paging and wire-type contract every capability inherits | `docs/specs/*-tool-contract.md` |

There is deliberately no rule file for the MCP server or CLI code: it has no conventional location, and it is written in a stack whose own plugin's rules apply to it. The builder skills (`mcp-builder`, `cli-builder`) carry the code-level standards for the run that writes it.

The source folder is `${CLAUDE_SKILL_DIR}`. The target is `<root>/.claude/rules/tooling/`.

## Run by a person or by a model

A person types `/tooling:rules`. A model runs this skill itself, as `tooling:rules`, when it is asked to set up a project or to install or update the rules, and when it finds this plugin enabled in a project that has no `.claude/rules/tooling/`. One argument answers the differing-file question below for every file in advance: `replace`, `keep` or `beside`.

Where a step needs the user's answer or agreement and nobody is there to give it (a queued plan task, a subagent, a headless run) and no argument settles it, take the choice that changes nothing of theirs: a differing file gets the plugin's copy beside it as `<name>.plugin`, and a path or any other change to an installed copy is not made. List each one under `Waiting for the user:` in the report. Never guess the answer.

## Procedure

1. **Find the project root**: `git rev-parse --show-toplevel`, or the working directory when it is not a git repo.
2. **Check the source**: `tool-contract.md` exists in `${CLAUDE_SKILL_DIR}`. If it is missing, stop and say so; never write a rule from memory.
3. **Copy it** if it is missing from the target: `mkdir -p <root>/.claude/rules/tooling` and `cp` it byte for byte.
4. **If it is already present**, `cmp` it with the source.
   - Identical: up to date.
   - Different: the team may have edited it. Show `diff -u <target> <source>` and ask: **replace** with the plugin's copy, **keep** theirs, or **write the plugin's copy beside it** as `tool-contract.md.plugin` to merge by hand. Never overwrite without that answer or a `replace` argument.
5. **Fit the path to where this project keeps its contracts.** Find them: `git ls-files '*tool-contract*.md'`, and `git grep -l -e '| Capability | Intent | Kind' -- '*.md'` for a contract under another name. For each one the default glob does not cover, propose a glob (for example `"**/docs/tools/*-contract.md"`) and add it to the installed copy with the user's agreement. Never widen to `**/docs/specs/**`: other specs would then load these rules.
6. **Check it will be committed**: `git check-ignore -q <root>/.claude/rules/tooling/tool-contract.md`. If it is ignored, say so; the rule then applies on this machine only.
7. **Check for conflicts**: read the project's `CLAUDE.md` (root and `.claude/`) for tool, MCP or CLI conventions that contradict the file (another envelope, another error vocabulary, other exit codes) and list them. A written contradiction is the user's to settle.

## Report

```
tooling rules: tool-contract.md: installed | up to date | replaced | kept | written as .plugin
Path: <root>/.claude/rules/tooling/
Contract paths: default | widened with <globs>
Committed: yes | ignored by git
Conflicts with CLAUDE.md: none | <one line each>
Waiting for the user: none | <one line each: the file or path change, and the question>
```

Then tell the user to commit the folder, and that the rule shows in `/memory` once the session has read a matching file.
