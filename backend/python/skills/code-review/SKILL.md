---
name: conventions-review
description: Use when reviewing Python worker or backend code for typing leaks, swallowed exceptions, blocking async or unsafe I/O. Triggers "review this Python module". Not for explanations (patterns).
---

# Python — Reviewer

Reviews Python worker code against the be-python rule files and produces a findings table. It does **not** rewrite: it points to the fix and hands off to `pattern-writer`, `media-processing` or `sandboxed-worker`. Loads `backend/_shared/code-review` for pattern-stacking and architecture-altitude concerns.

## The checklist is the rule file

Every check, and the severity it reports, lives in one place: the be-python rule files `python.md` (core), `python-pipeline.md`, `python-tests.md`, `python-container.md` and `python-project.md`.

1. **The project's copies first**: `.claude/rules/be-python/` at the project root. The team may have edited them, and its edits win.
2. **Otherwise the plugin's copies**: `backend/python/skills/rules/` (under `${CLAUDE_PLUGIN_ROOT}` in an installed plugin). Say in the report that the project has no installed rules and that `/be-python:rules` installs them.

Read `python.md`, plus each other file whose `paths:` match a file under review, in full before the first finding. Code that opens, parses or encodes an upload always gets `python-pipeline.md`, whatever its path. A rule loaded on its own by the session is not enough: a review needs every file that applies, not just the ones the session happened to open. Never review from memory of the rules, and never add a check the file does not contain; propose it as a rule change instead.

## Version policy

Detect the interpreter (`requires-python`, `.python-version`, the Dockerfile base image) and the Pillow major from `uv.lock` first. Do not flag a 3.12 project for lacking a 3.13 feature, or a Pillow 11 project for a 12-only API. The rule file's "the codebase wins" line applies: a convention the project follows consistently is not a finding.

## When to use

- A diff or module submitted: validator, sanitiser, pipeline step, composition root, isolation layer, tests, the worker's Dockerfile or compose service
- A pre-merge gate on anything under the worker's `src/` or `tests/`
- "Is this safe to point at customer uploads"

## When NOT to use

- Conceptual questions → `pattern-guide`
- Writing the fix → `pattern-writer` / `media-processing` / `sandboxed-worker`
- Container scanning, DAST → `qa-security`

## Procedure

1. Read the rule files, then each changed file end to end.
2. Walk the rules in this order: the core file's Hostile input section and `python-pipeline.md`, then Errors and resources, Concurrency and timeouts, then the rest. Most blockers live there.
3. Per finding: file and line, the rule broken, a one-sentence fix. The severity is the tag on the rule, never a new judgment.
4. Do not rewrite. Each fix names the skill section that has the recipe (`media-processing` Step 3, `sandboxed-worker` per-job isolation) rather than restating it.

## Output format

```
| Severity | Location                        | Issue                                                   | Suggested fix                                                          |
|----------|---------------------------------|---------------------------------------------------------|------------------------------------------------------------------------|
| blocker  | upload_worker/metadata.py:18    | `im.copy()` then `save()` keeps the JPEG comment and XMP | Rebuild with `Image.frombytes` after `exif_transpose` (`media-processing` Step 3) |
| blocker  | upload_worker/sanitize_svg.py:9 | `xml.etree.fromstring` on the upload                    | `defusedxml` with `forbid_dtd`, `forbid_entities`, `forbid_external`    |
| major    | upload_worker/api.py:40         | `remove(...)` called directly inside `async def`        | `await asyncio.to_thread(...)`, or keep the worker synchronous          |
| minor    | upload_worker/dpi.py:12         | `>= 300` inline                                         | `PRINT_READY_DPI = 300`                                                 |
```

Blockers first. A review of upload-handling code with no row from the hostile-input and pipeline rules says explicitly that they were applied and passed. End with one line: `Rules: project .claude/rules/be-python/ | plugin copy (not installed)`.

## Handoffs

- Fixes → `pattern-writer` / `media-processing` / `sandboxed-worker`
- Missing tests → `unit-testing`
- A rule is missing or wrong → edit the project's `.claude/rules/be-python/`; for every project, the plugin's `backend/python/skills/rules/`
- Cross-stack pattern concerns → `backend/_shared/code-review`
- Container / image scan findings → `qa-security`, `devops/docker`
