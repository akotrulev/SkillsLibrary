---
name: api-tests-review
description: Use when reviewing existing TypeScript API test code (Vitest + fetch + Zod) for quality. Triggers "review this API test". Not for writing new tests (api-tests).
---

# QA — API Test Reviewer (TypeScript / Vitest + fetch + Zod)

Reviews TypeScript API test code against the patterns enforced by `qa/typescript/skills/api-test-author/writer`, `qa/typescript/skills/api-client-writer`, and `qa/typescript/skills/api-models` (the Zod schema/types + `{resource}Client` factory with dual raw/typed methods layering). Produces a findings table in the `CLAUDE.md` review format. Does **not** rewrite — points to the fix and lets the human apply it.

## When to use

- A diff or file is submitted for review (`*.spec.ts`, `{resource}Client.ts`, Zod schema/types module)
- Pre-merge gate on a PR that touches `src/specs/`, `src/clients/`, or `src/models/`
- The user wants a second opinion on schema coverage, `ProblemDetails` handling, or async assertion style

## When NOT to use

- Generating new TS tests → `qa/typescript/skills/api-test-author/writer`
- .NET reviews → `qa/dotnet/skills/api-test-author/review`
- Java reviews → `qa/java/skills/api-test-author/review`
- Schema/client scaffolding → `qa/typescript/skills/api-models` / `qa/typescript/skills/api-client-writer`
- UI tests → `qa/typescript/skills/ui-test-author/review`
- Reviewing the overall test strategy / pyramid → `qa/manual/test-strategy`

## Inputs needed

1. **Files** under review — Vitest spec, `{resource}Client.ts`, Zod schema/types module
2. **Endpoint contract** if available (OpenAPI snippet, sample 4xx body) — needed to grade `ProblemDetails` / error-body assertions
3. **Project conventions** that override defaults (e.g. project uses `safeParse` everywhere, custom error schema name)
4. **`tsconfig.json` strict flags** if questionable — needed to grade `any` / nullable usage

## The checklist is the rule files

Every check, and the severity it reports, lives in one place: the qa-typescript rule files `qa-typescript.md` (core) and `api-tests.md`, plus `ci-tests.md` when a pipeline file is in the diff.

1. **The project's copies first**: `.claude/rules/qa-typescript/` at the project root. The team may have edited them, and its edits win.
2. **Otherwise the plugin's copies**: `qa/typescript/skills/rules/` (under `${CLAUDE_PLUGIN_ROOT}` in an installed plugin). Say in the report that the project has no installed rules and that `/qa-typescript:rules` installs them.

Read `qa-typescript.md` and `api-tests.md` in full before the first finding. A rule loaded on its own by the session is not enough: a review needs every file that applies, not just the ones the session happened to open. Never review from memory of the rules, and never add a check the files do not contain; propose it as a rule change instead.

## Version policy

Detect the runner (Vitest or Jest, or Playwright's `request` fixture), Zod's major and the Node major from `package.json` first. The rule files' "the codebase wins" line applies: a convention the suite follows consistently (`safeParse` everywhere, its own error-schema name) is not a finding.

## Good signals (counter-list)

Read `references/good-signals.md` when grading a suite that looks clean: it lists what a correct factory-client, typed-method and cleanup layout looks like, so you do not flag it.

## Procedure

1. Confirm imports show Vitest + the client factory + the Zod types module (`import { describe, it, expect } from 'vitest';`, `import { create{Resource}Client } from '../../../clients/...';`).
2. Read the whole vertical slice (spec **plus** the imported `{resource}Client.ts` **plus** the schema/types module) before writing findings — most real bugs are cross-file (e.g. a raw method that parses, so the negative spec is dead code).
3. Walk the rules: errors and async (unawaited assertions, catches, swallowed cleanup) and the client layering first, where most blockers live, then the rest.
4. For each finding, capture: file + line, the rule broken, and a one-sentence fix. The severity is the tag on the rule, never a new judgment.
5. **Do not rewrite the code.** Hand off to `qa/typescript/skills/api-test-author/writer` if the user wants the rewrite.

## Output format

```
| Severity | Location                                          | Issue                                                       | Suggested fix                                                          |
|----------|---------------------------------------------------|-------------------------------------------------------------|------------------------------------------------------------------------|
| blocker  | src/specs/user/users/getUser.spec.ts:42           | `expect(client.getAllTyped(200)).resolves...` not awaited   | Add `await` — unawaited `.resolves` chains pass on failures            |
| major    | src/clients/user/userClient.ts:60                 | Raw `getById` runs `Schema.parse` and returns the DTO       | Return `ApiResponse`; parsing belongs in the `…Typed` method           |
| major    | src/specs/user/users/getUser.spec.ts:18           | Auth chosen via `new UserClient(true)` flag                 | Build via `createUserClient(await authHelper.getToken(...))`           |
| minor    | src/specs/user/users/getUser.spec.ts:10           | All `it(...)` flat, no `describe`                            | Wrap in `describe('GET /api/users', () => { ... })`                    |
| nit      | src/specs/user/users/getUser.spec.ts:14           | Test title `'test 1'`                                       | Rename to behavior: `'returns the first page of users'`                |
```

Severities (from `CLAUDE.md`):

- **blocker** — ships a bug, breaks the build, hard rule violation (missing `await`, hardcoded secrets, `setTimeout` waits, shared state)
- **major** — design / correctness issue that will hurt soon (silent failures, lost coverage, `any` types, wrong layering)
- **minor** — style / small inconsistency (naming, grouping)
- **nit** — optional preference

End with one line: `Rules: project .claude/rules/qa-typescript/ | plugin copy (not installed)`.

## Handoffs

- Need a rewrite → `qa/typescript/skills/api-test-author/writer`
- Schemas / types need fixing → `qa/typescript/skills/api-models`
- Client layer needs refactor → `qa/typescript/skills/api-client-writer`
- Whole test pyramid is the issue → `qa/manual/test-strategy`
- .NET sibling → `qa/dotnet/skills/api-test-author/review`
- Java sibling → `qa/java/skills/api-test-author/review`
- A rule is missing or wrong → edit the project's `.claude/rules/qa-typescript/`; for every project, the plugin's `qa/typescript/skills/rules/`
