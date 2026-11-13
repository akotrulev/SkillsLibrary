---
name: rules
description: Use when installing or updating the be-python coding standards as path-scoped rules in .claude/rules/be-python/. Triggers "install the Python rules", "set up this project". Not for reviewing code (conventions-review).
argument-hint: "[replace | keep | beside]"
---

# Install the be-python rules

Plugins cannot ship Claude Code rules, so this skill copies them into the project. Each rule file carries `paths:` frontmatter, and Claude Code loads it only once the session reads or edits a matching file, so a session that never touches the Dockerfile never pays for the container rules.

| File (beside this SKILL.md) | Loads when the session touches |
|---|---|
| `python.md`: simplicity, types, injection, errors, concurrency, hostile input, logging, comments | any `*.py` |
| `python-pipeline.md`: validation, SVG, metadata strip, operations, per-job isolation, verdict | `src/**/*.py` (the worker package) |
| `python-tests.md` | `tests/**`, `test_*.py`, `*_test.py`, `conftest.py` |
| `python-container.md`: network, rootfs, capabilities, baked weights, limits | `Dockerfile*`, `*.Dockerfile`, `*compose*.yml` / `.yaml` |
| `python-project.md`: interpreter, mypy, ruff, pytest, dependencies | `pyproject.toml` |

The source folder is `${CLAUDE_SKILL_DIR}`. The target is `<root>/.claude/rules/be-python/`.

## Run by a person or by a model

A person types `/be-python:rules`. A model runs this skill itself, as `be-python:rules`, when it is asked to set up a project or to install or update the rules, and when it finds this plugin enabled in a project that has no `.claude/rules/be-python/`. One argument answers the differing-file question below for every file in advance: `replace`, `keep` or `beside`.

Where a step needs the user's answer or agreement and nobody is there to give it (a queued plan task, a subagent, a headless run) and no argument settles it, take the choice that changes nothing of theirs: a differing file gets the plugin's copy beside it as `<name>.plugin`, and a path or any other change to an installed copy is not made. List each one under `Waiting for the user:` in the report. Never guess the answer.

## Procedure

1. **Find the project root**: `git rev-parse --show-toplevel`, or the working directory when it is not a git repo.
2. **Check the source**: all five files exist in `${CLAUDE_SKILL_DIR}`. If one is missing, stop and say so; never write a rule from memory.
3. **Copy each file** that is missing from the target: `mkdir -p <root>/.claude/rules/be-python` and `cp` it byte for byte.
4. **For each file already present**, `cmp` it with the source.
   - Identical: up to date.
   - Different: the team may have edited it. Show `diff -u <target> <source>` and ask: **replace** with the plugin's copy, **keep** theirs, or **write the plugin's copy beside it** as `<name>.plugin` to merge by hand. Never overwrite without that answer or a `replace` argument.
5. **Fit the paths to where the worker lives.** The defaults assume a worker-only repo; in a monorepo the core and container globs would also catch Python scripts, tooling and other services' images, which these rules do not govern.
   - **Find the worker package(s)**: `git ls-files '*pyproject.toml'`; a worker's `pyproject.toml` depends on Pillow, defusedxml, rembg or vtracer. Then `git ls-files '*.py'`. If every Python file sits under a worker directory, keep `**/*.py`. Otherwise propose narrowing `python.md` to `"<worker-dir>/**/*.py"`, `python-tests.md` to `"<worker-dir>/tests/**/*.py"` (plus any other test folder it has) and `python-project.md` to `"<worker-dir>/pyproject.toml"`, and name the Python left out.
   - **Find the pipeline modules**: `git grep -l -e 'from PIL' -e 'import PIL' -e defusedxml -e rembg -e vtracer -- '*.py'`. If a file it lists matches none of the `python-pipeline.md` globs (a flat layout with no `src/`), propose the directory glob that covers it, such as `"<worker-dir>/upload_worker/**/*.py"`.
   - **Find the images**: `git ls-files '*Dockerfile*' '*compose*.yml' '*compose*.yaml'`. If the repo builds images other than the worker's, propose narrowing `python-container.md` to the worker's Dockerfile and the compose or manifest file that defines its service.
   Change the installed copies only with the user's agreement.
6. **Check it will be committed**: `git check-ignore -q <root>/.claude/rules/be-python/python.md`. If it is ignored, say so; the rules then apply on this machine only.
7. **Check for conflicts**: read the project's `CLAUDE.md` (root and `.claude/`) for Python or worker rules that contradict these files and list them. A written contradiction is the user's to settle.

## Report

```
be-python rules: <file>: installed | up to date | replaced | kept | written as .plugin   (one line per file)
Path: <root>/.claude/rules/be-python/
Worker paths: default | narrowed to <globs> | widened with <globs>
Committed: yes | ignored by git
Conflicts with CLAUDE.md: none | <one line each>
Waiting for the user: none | <one line each: the file or path change, and the question>
```

Then tell the user to commit the folder, and that a rule shows in `/memory` once the session has read a matching file.
