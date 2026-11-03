---
paths:
  - "**/*.tsx"
  - "**/*.jsx"
---

<!-- fe-react rules v1 (2026-11-03): core. Installed by /fe-react:rules; edit to fit this project, re-run to compare with the plugin's copy. -->

# React / Next.js code standards

Apply these to every component you write, edit or review. The tag after a rule is the severity a review reports: **blocker** ships a bug or breaks a security rule, **major** is a design or correctness problem, **minor** is style, **nit** is preference. Data, forms, tests and styling rules are separate files that load with those files.

**The codebase wins.** Where this project consistently does something another way, follow it and do not flag it. Detect the React and Next majors and the React Compiler from `package.json` before writing: no React 19 API (`use()`, `useActionState`, `useOptimistic`, `ref` as a prop) in an 18 project, no Next 15 async request API in 14; `forwardRef` is a finding only on 19, hand-written memoization only with the Compiler on. Never flag a down-level project for lacking an API.

## Simplicity

- Write the simplest thing that meets the requirement, then stop: no wrapper that only forwards props, no store or context for state one component owns, no hook or base component with one caller, no abstraction over what the framework or library does. Earned on the second real need. *major, fix by inlining*
- Cut structure, never correctness: validation, error states, accessibility, cleanup and tests stay.
- Feature folders; a component goes shared on its second consumer. *minor*

## Server and client boundary (App Router)

- Server Components by default; `'use client'` on the smallest interactive leaf, never on a route or layout for one leaf. *major*
- Server Components fetch, Client Components interact: no `await` in a Client Component body; data crosses as serializable props; server output enters a Client Component as `children`, never by import. *major*
- No secret, `server-only` module or DB dependency reachable from a `'use client'` file; no `NEXT_PUBLIC_` on a secret. *blocker*
- No `window`, `localStorage`, `Date.now()` or `Math.random()` read during render; use an effect or a mount guard. *major*
- No mutable module-level state shared between components or requests. *blocker*

## Hooks and effects

- Hooks at the top level only (`use()` excepted); custom hooks are named `use*`. *blocker*
- No fetch or promise started in the render body. *blocker*
- Exhaustive effect deps; a bare `eslint-disable` of `react-hooks/exhaustive-deps` is itself the finding. *major*
- Every subscription, timer, listener and channel is torn down in the cleanup. *major*
- No effect to derive state or copy props into state: compute in render, or remount with `key`. *major*

## Rendering and state

- `key` is a stable domain id, never the array index. *major*
- A Context `value` is memoized; read and write contexts split under churn; one context or store per concern. *major*
- No component defined inside another. *major*
- `useMemo` / `useCallback` / `React.memo` only where a memoized consumer skips work; no fresh inline object or array passed to one. *minor*
- Virtualize long lists; code-split heavy, non-critical widgets. *major*
- Server data lives in RSC or TanStack Query, never copied into Zustand, Redux, Context or `useState`. *major*
- Client state: local first, lifted only as far as needed; bookmarkable filters, paging and sort live in the URL. *major*
- Storage access is guarded and degrades to memory; no token, PII or server data persisted. *major*

## Components and types

- `strict` TypeScript: no `any`, `as any` or `as unknown as`; no `@ts-ignore` / `@ts-expect-error` without a reason. *major*
- Variant props are discriminated unions; event handlers are typed. *major*
- Controlled or uncontrolled, never both; one concern per component, logic in hooks or services. *major*

## Markup, accessibility and navigation

- Semantic HTML before ARIA: `<button>` for actions, never `<div onClick>`; real `<nav>` / `<main>` / `<footer>`. *major*
- In-app navigation is a `<Link href>`, never `onClick` + `router.push`. Same tab by default; `target="_blank"` only with `rel="noopener"` and an "opens in new tab" cue. *major*
- Every input has a label, every icon-only button an `aria-label`, every image `alt` (`""` when decorative); state is never shown by colour alone. *major*
- Dialogs trap and restore focus; a client route change focuses `<main>` or the `<h1>`. Composite widgets come from Radix, React Aria or the library. No `tabIndex > 0`, no outline removed without a replacement. *major*
- Every route sets a title (`metadata` / `generateMetadata`). *minor*

## Data regions and UI correctness

- Every data region renders loading, loaded and failed; a failure never reads as blank or "no data". The failure is scoped to the response-fed subtree: search, filters and toolbars keep rendering. Never render `error.message` or a raw body; show friendly text, the correlation id and a retry. *major*
- Every surfaced failure also raises the persistent top-right notification: no auto-dismiss, closed only by its close button. A failed refetch keeps its data, marked stale. *major*
- Enums humanized, names instead of ids, one shared `Intl` formatter per type; lists sort deterministically with a unique tiebreaker. *minor*
- A destructive action confirms by naming the object, with a verb-labelled danger button; never `window.confirm`. *major*

## Test ids

- `data-testid` on every interactive element, list or grid container and data-region state, named `Page.Element[.Qualifier]` in PascalCase; row locators are static, never an index, id, GUID or state value. No wrapper component just to carry one. *minor; major for a collision or a dynamic row locator*

## Comments

- No comments inside bodies (step markers, restating the next line, commented-out code); extract and name the step. TSDoc only for a contract the props cannot express. Scaffold comments go. *minor; major when wrong*
