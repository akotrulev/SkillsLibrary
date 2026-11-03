---
name: conventions-review
description: Use when reviewing React code (misplaced 'use client', hook rules, effect-derived state, index keys, hydration bugs). Triggers "review this component". Not for writing code (component-writer).
---

# React — Reviewer (TypeScript)

Reviews React code (React 19/18 + TypeScript — Next.js App Router / RSC primary, Vite SPA fallback) against the fe-react rule files and produces a findings table. It does **not** rewrite: it points to the fix and hands off to [`component-writer`](../component-writer/SKILL.md).

## The checklist is the rule files

Every check, and the severity it reports, lives in one place: the fe-react rule files `react.md` (core), `react-data.md`, `react-forms.md`, `react-tests.md` and `react-styling.md`.

1. **The project's copies first**: `.claude/rules/fe-react/` at the project root. The team may have edited them (and may have scoped their paths to the web app), and its edits win.
2. **Otherwise the plugin's copies**: `frontend/react/skills/rules/` (under `${CLAUDE_PLUGIN_ROOT}` in an installed plugin). Say in the report that the project has no installed rules and that `/fe-react:rules` installs them.

Read `react.md`, plus each other file whose `paths:` match a file under review, in full before the first finding. A rule loaded on its own by the session is not enough: a review needs every file that applies, not just the ones the session happened to open. Never review from memory of the rules, and never add a check the files do not contain; propose it as a rule change instead.

## Version policy

Detect the installed React (and Next.js) major and whether the React Compiler is on, from `package.json`, before flagging. `forwardRef` is a finding only on React 19 (where `ref` is a plain prop); on 18 it's correct. Hand-rolled `useMemo`/`useCallback` are a finding on a Compiler-enabled project but correct where the Compiler is off. Manual `isPending`/rollback is correct on 18 (where `useActionState`/`useOptimistic` don't exist). Never flag a down-level project for lacking an API it doesn't have. The rule files' "the codebase wins" line applies: a convention the project follows consistently is not a finding.

## When to use

- A `.tsx` diff submitted (component, hook, context, route, `page.tsx`/`layout.tsx`/`error.tsx`)
- Pre-merge gate on a PR touching `app/`, `src/components/`, `src/hooks/`, `src/features/`
- "Why does this page re-render / hydrate twice / fetch twice?"
- Audit `'use client'` placement, effect/cleanup hygiene, or `data-testid` coverage

## When NOT to use

- Conceptual lookup → [`basics`](../basics/SKILL.md)
- Generating new code → [`component-writer`](../component-writer/SKILL.md)
- Reviewing **UI test code** (Playwright specs / POMs) → **peer** `qa/typescript/skills/ui-test-author/review`
- Blazor review → `frontend/blazor/skills/code-review`
- Auth wiring review → `auth/auth0-react` + general review

## Inputs needed

1. **Files** (component, hook, context, route file)
2. **Framework / render target** — Next.js App Router (RSC), Pages Router (legacy), or Vite SPA
3. **State / data source** — local, server (RSC fetch / TanStack Query / SWR), global (Zustand / Redux / Context)
4. **React + Next major**, React Compiler on/off, and any project conventions that override defaults

## Procedure

1. Read the rule files, then each changed file end to end.
2. Identify the **render target** (App Router RSC / Vite SPA) and, for each file, whether it's a Server or Client Component — half the findings depend on it.
3. Walk the rules, top offenders first: the server and client boundary, hooks and effects, rendering and state, then data regions and the rest.
4. Cross-reference the vendored Vercel rules (`frontend/react/vendor/reference/`) for perf / Next.js specifics.
5. Per finding: file and line, the rule broken, a one-sentence fix. The severity is the tag on the rule, never a new judgment.
6. **Do not rewrite.** Hand off to [`component-writer`](../component-writer/SKILL.md).

## Output format

```
| Severity | Location                              | Issue                                                              | Suggested fix                                                              |
|----------|---------------------------------------|--------------------------------------------------------------------|----------------------------------------------------------------------------|
| blocker  | app/(shop)/cart/page.tsx:18          | `await fetch('/api/cart')` in a `'use client'` component body        | Fetch in the Server Component parent and pass as props, or use TanStack Query |
| major    | src/features/cart/CartContext.tsx:24 | Context value `{ items, add, remove }` allocated inline every render  | Wrap in `useMemo` keyed on `items`; split read/write contexts               |
| major    | src/components/Menu.tsx:42           | `<div role="button" onClick>` instead of a real `<button>`           | Use `<button type="button">` for keyboard + screen-reader support           |
| major    | src/features/orders/OrderList.tsx:9  | `key={index}` on a reorderable list                                  | Key on `order.id` (stable domain id)                                        |
```

End with one line: `Rules: project .claude/rules/fe-react/ | plugin copy (not installed)`.

## Handoffs

- Rewrite → [`component-writer`](../component-writer/SKILL.md)
- Conceptual lookup → [`basics`](../basics/SKILL.md)
- Vercel rule deep-dive → `frontend/react/vendor/reference/`
- Composition deep-dive → `frontend/react/vendor/composition-patterns`
- Component tests to lock a fix → [`component-testing`](../component-testing/SKILL.md)
- UI test-code review → **peer** `qa/typescript/skills/ui-test-author/review`
- Auth0 wiring review → `auth/auth0-react`
- A rule is missing or wrong → edit the project's `.claude/rules/fe-react/`; for every project, the plugin's `frontend/react/skills/rules/`
