---
name: conventions-review
description: Use when reviewing Node/TypeScript backend code for type-safety leaks, async bugs or missing runtime validation. Triggers "review this TS service". Not for explanations (patterns).
disable-model-invocation: true
---

# Node / TypeScript backend — Reviewer

Reviews Node + TypeScript (strict mode) backend code against the be-node rule files and produces a findings table. It does **not** rewrite: it points to the fix and hands off to `pattern-writer`.

## The checklist is the rule files

Every check, and the severity it reports, lives in one place: the be-node rule files `node.md` (core), `node-persistence.md`, `node-tests.md`, `node-config.md` and `node-lint.md`.

1. **The project's copies first**: `.claude/rules/be-node/` at the project root. The team may have edited them, and its edits win.
2. **Otherwise the plugin's copies**: `backend/node/skills/rules/` (under `${CLAUDE_PLUGIN_ROOT}` in an installed plugin). Say in the report that the project has no installed rules and that `/be-node:rules` installs them.

Read `node.md`, plus each other file that applies to a file under review, in full before the first finding. A file under review is in scope for `node.md` whenever it is backend code, even where the project's globs miss it: `*.ts` is shared with frontend and test code, so the globs are narrow and a session may not have loaded every file that applies. Never review from memory of the rules, and never add a check the files do not contain; propose it as a rule change instead.

## Version policy

Detect the Node major (`engines`, `.nvmrc`, the lockfile), the TypeScript version and its `strict` settings, and the framework first. Do not flag a Node 22 project for lacking a Node 24 feature. The rule file's "the codebase wins" line applies: a convention the project follows consistently is not a finding.

## Procedure

1. Read the rule files, then each changed file end to end.
2. Walk the rules in this order: Types, Boundaries (runtime validation and config), Errors and async, persistence, then the rest. Most blockers and majors live there.
3. Per finding: file and line, the rule broken, a one-sentence fix. The severity is the tag on the rule, never a new judgment.
4. Do not rewrite. Hand off to `backend/node/skills/pattern-writer`.

## Output format

```
| Severity | Location                                 | Issue                                              | Suggested fix                                                        |
|----------|------------------------------------------|----------------------------------------------------|----------------------------------------------------------------------|
| blocker  | src/orders/order-queries.ts:18           | `$queryRawUnsafe` with a concatenated customer id  | `prisma.$queryRaw` tagged template with the id bound                 |
| major    | src/api/order-routes.ts:42               | `req.body as CreateOrderDto`, no runtime validation | `CreateOrderDto.parse(req.body)`; reject with 400 on a schema error  |
| major    | src/features/orders/pricing.ts:14        | `switch (mode.kind)` has no exhaustiveness check   | End it with `const _exhaustive: never = mode.kind;`                  |
| minor    | src/shared/types.ts:9                    | `enum OrderStatus` with four members               | `type OrderStatus = 'pending' \| 'paid' \| …`                        |
```

End with one line: `Rules: project .claude/rules/be-node/ | plugin copy (not installed)`.
