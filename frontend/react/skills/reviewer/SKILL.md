---
name: fe-react-reviewer
description: Use when reviewing React code (React 19/18 + TS) — misplaced `'use client'`, hook-rule violations, `useEffect`-to-derive-state, missing cleanup, index keys, hydration mismatches, un-memoized context, server data in a client store, `<div onClick>` navigation, missing testids, await waterfalls. Triggers: "review this component/page", "why does this re-render", "is this 'use client' in the right place", "Rendered more hooks than during the previous render", "Each child in a list should have a unique key prop". Do NOT use for explanations (`reference`) or generating code (`generator`).
---

# React Design Patterns — Reviewer (TypeScript)

Reviews React code (React 19/18 + TypeScript — Next.js App Router / RSC primary, Vite SPA fallback) against the patterns enforced by [`generator`](../generator/SKILL.md), the Vercel rule set vendored at `frontend/react/vendor/reference/`, and the global + FE code rules in `CLAUDE.md`. Findings in the standard severity table; does **not** rewrite — hands off to [`generator`](../generator/SKILL.md).

**Version rule:** detect the installed React (and Next.js) major from `package.json` before flagging. `forwardRef` is a finding only on React 19 (where `ref` is a plain prop); on 18 it's correct. Hand-rolled `useMemo`/`useCallback` are a finding on a **React Compiler**-enabled project (auto-memoization) but correct where the compiler is off. Manual `isPending`/rollback is correct on 18 (where `useActionState`/`useOptimistic` don't exist). Never flag a down-level project for lacking an API it doesn't have.

## When to use

- A `.tsx` diff submitted (component, hook, context, route, `page.tsx`/`layout.tsx`/`error.tsx`)
- Pre-merge gate on a PR touching `app/`, `src/components/`, `src/hooks/`, `src/features/`
- "Why does this page re-render / hydrate twice / fetch twice?"
- Audit `'use client'` placement, effect/cleanup hygiene, or `data-testid` coverage

## When NOT to use

- Conceptual lookup → [`reference`](../reference/SKILL.md)
- Generating new code → [`generator`](../generator/SKILL.md)
- Reviewing **UI test code** (Playwright specs / POMs) → **peer** `qa/typescript/skills/ui-test-author/reviewer`
- Blazor review → `frontend/blazor/skills/reviewer`
- Auth wiring review → `auth/auth0-react` + general review

## Inputs needed

1. **Files** (component, hook, context, route file)
2. **Framework / render target** — Next.js App Router (RSC), Pages Router (legacy), or Vite SPA
3. **State / data source** — local, server (RSC fetch / TanStack Query / SWR), global (Zustand / Redux / Context)
4. **React + Next major**, React Compiler on/off, and any project conventions that override defaults

## Review checklist

### RSC & the `'use client'` boundary (App Router)

| Check | Bad sign | Severity |
|---|---|---|
| `'use client'` on the smallest interactive leaf | Directive on a route/page just because one button is interactive — drags the whole subtree into the bundle | major |
| Server Components fetch; Client Components interact | `async`/`await` data in a Client Component body | major |
| Data crosses the boundary as serializable props | Passing a function/class instance/Date-heavy object into a Client Component | major |
| Client Component composes server output via `children` | A Client Component `import`ing a Server Component (ships server code) | major |
| Server-only secrets never in a client module | API key / DB call / server dep imported into a `'use client'` file | blocker |
| No sequential-await waterfall | Independent `await`s serialized in one RSC instead of `Promise.all` / parallel | major |
| Streaming via `<Suspense>` on slow sections | One slow fetch blocks the whole route's TTFB | minor |

### Hook rules & data flow

| Check | Bad sign | Severity |
|---|---|---|
| Hooks called unconditionally at the top level | Hook inside `if`/`for`/early return (except `use()`, which may be conditional) | blocker |
| Custom hooks named `use*` so lint applies hook rules | `function getUser()` containing `useState` | blocker |
| `useEffect` deps exhaustive | Missing dep the body reads, or an `eslint-disable` silencing the lint | major |
| Effects clean up subscriptions/timers/listeners | Subscription/interval opened with no teardown; setState after unmount | major |
| **No `useEffect` to derive state** | `useState`+`useEffect` recomputing a value from props instead of computing in render | major |
| No set-state-from-props effect | `useEffect(() => setX(props.x), [props.x])` — pass `key` or compute inline | major |
| No async side effects in render | `fetch(...)` / promise at the top level of a component body | blocker |
| Lazy `useState` initializer for expensive/`localStorage` values | `useState(expensive())` / `useState(localStorage.getItem(...))` runs every render | minor |

### Hydration (client components)

| Check | Bad sign | Severity |
|---|---|---|
| No browser-only reads during render | `window`/`localStorage`/`Date.now()`/`Math.random()` in the render body → server/client markup mismatch | major |
| Browser access in `useEffect` or behind a mounted flag | Reading `navigator`/`matchMedia` at module/render time | major |
| `suppressHydrationWarning` only for intentional cosmetic diffs | Blanket suppression hiding a real mismatch | minor |

### Render performance

| Check | Bad sign | Severity |
|---|---|---|
| Context `value` memoized (stable identity) | `<Ctx value={{ a, b }}>` allocated inline every render | major |
| `key` is a stable domain id | `key={index}` on a reorder-capable list — state/focus corruption | major |
| Read/write contexts split when write churn re-renders readers | One provider carrying everything → whole tree re-renders on any change | major |
| Large lists virtualized | 10k rows rendered straight into the DOM | major |
| `useMemo`/`useCallback` justified (compiler off) or absent (compiler on) | Memo hooks sprinkled with no memoized consumer — pure cost | minor |
| No new object/array literal default props defeating downstream memo | `<Foo items={[]} />` breaking a memoized child | minor |

### State ownership (FE code rule)

| Check | Bad sign | Severity |
|---|---|---|
| Server state in RSC fetch / TanStack Query — **not** a client store | Fetched server data copied into Zustand/Redux/`useState` | major |
| Client state (UI, session) in Zustand/Context; ephemeral state local | Global store holding a dropdown's open flag | minor |
| State lifted only as far as needed | A value two siblings share owned by one of them and drilled sideways | major |
| Derived data computed in render, not stored | A second `useState` mirroring a filtered/sorted list | major |

### Component design

| Check | Bad sign | Severity |
|---|---|---|
| Controlled/uncontrolled is explicit | `value` without `onChange`, or both `value` and `defaultValue` accepted | major |
| One concern per component | Component doing fetch + form + modal + analytics | major |
| Compound components share state via context, not prop-drilling | `<Tabs>` threading `active` through every child manually | major |
| Composition over configuration | 20 boolean/mode props where slots (`children`/named `ReactNode`) would do | minor |
| `ref` as a prop (React 19) / `forwardRef` (React 18) | `forwardRef` on a React 19 project; reaching into the DOM for what props express | minor |

### Forms & validation (FE code rule)

| Check | Bad sign | Severity |
|---|---|---|
| React Hook Form + Zod (or Server Action + `useActionState`) | Hand-rolled `useState` per field with ad-hoc validation | major |
| Field-level `aria-invalid` + error text tied by `aria-describedby` | Errors only in a summary, not associated with the field | minor |
| Server errors mapped back to fields (`setError`) | `ProblemDetails`/422 swallowed or shown as a raw blob | major |
| Submit disabled/pending while in flight | Double-submit possible; no pending affordance | minor |

### Accessibility

| Check | Bad sign | Severity |
|---|---|---|
| Interactive elements are real `<button>`/`<a>`/`<input>` | `<div onClick>` / `<span onClick>` — loses keyboard + SR | major |
| In-app nav is a real `<Link href>` | `onClick` calling `router.push` on a `<div>`/`<button>` | major |
| Form fields have labels | `<input>` with no `<label>`/`aria-label` | major |
| Composite widgets carry roles + relationships | Tabs/menu/dialog missing `role`/`aria-*`; hand-rolled instead of Radix/React Aria | major |
| Focus managed on dialogs + client route changes | Modal opens without moving focus; route change leaves focus stranded (no `<main>` focus/announce) | major |
| Color not the sole state signifier | Error shown only by a red border | minor |
| Images have meaningful `alt` (or `alt=""` if decorative) | `<img>` with no `alt`; raw `<img>` instead of `next/image` in `app/` | minor |

### Error handling & resilience (FE code rule)

| Check | Bad sign | Severity |
|---|---|---|
| Three-state data regions (loading/loaded/failed) | Failure collapses into a blank section indistinguishable from "no data" | major |
| Error boundary wraps failable features (`error.tsx` / `react-error-boundary`) | A single data error crashes the whole page | major |
| Friendly error text; never leak `error.message`/response body | Raw exception rendered to the user | major |
| No swallowed rejections | `try {…} catch { /* nothing */ }`; `void fetchX()` with no error path | major |
| Retry only idempotent requests | Blind retry of a POST/mutation | major |

### TypeScript / strict mode

| Check | Bad sign | Severity |
|---|---|---|
| No `any` | `: any`, `as any`, `as unknown as X` | major |
| No bare `@ts-ignore`/`@ts-expect-error` | Suppression with no comment/justification | major |
| Discriminated unions for variant props | `variant?: string` with stringly-typed branching | major |
| Event handlers typed | `(e: any) => …` | minor |

### Testability (convention: [`testability`](../testability/SKILL.md))

| Check | Bad sign | Severity |
|---|---|---|
| Interactive elements / grids carry `data-testid` | Button, input, or grid container without a testid | minor |
| Locators unique per screen | Same testid on two distinct elements (collision) | major |
| Row locators static | Array index, numeric id, or GUID inside a locator value | major |
| PascalCase dot-separated segments | kebab/snake-case segments | nit |

### UI correctness (convention: [`ui-conventions`](../ui-conventions/SKILL.md))

| Check | Bad sign | Severity |
|---|---|---|
| Destructive actions confirm by naming the object | Generic "Are you sure?"; `window.confirm` | major |
| Grids sort deterministically with a tiebreaker | List reorders on every refetch | minor |
| Display values humanized | Raw enum int / bare GUID shown where a name exists | minor |
| Every route sets a title (`metadata`/`generateMetadata`) | Browser tab shows the app default on a content page | minor |
| Links open same-tab by default | `target="_blank"` on an internal route, or without `rel="noopener"` + a cue | major |
| Surface chosen deliberately | Long/multi-step flow trapped in a modal; blocking modal over data the user must reference | major |
| Dark mode is an authored palette | Dark theme via `filter: invert()` / negated hex, contrast not re-checked | major |

### Cross-cutting

| Check | Bad sign | Severity |
|---|---|---|
| Follow-the-library styling (no Tailwind atop MUI) | Two styling authorities fighting | minor |
| Structured server logging | `console.log` in server code / hot render paths | minor |
| Fetch through a typed client / server util | `fetch` string literals scattered with no error typing | minor |
| No mutable module-level state as "shared" component state | `let cache = []` at module scope holding user state | blocker |

## Procedure

1. Identify the **render target** (App Router RSC / Vite SPA) and, for each file, whether it's a Server or Client Component — half the findings depend on it.
2. Walk the checklists. The top offenders, in order: misplaced `'use client'`, `useEffect`-to-derive/sync-state, index keys, missing cleanup, un-memoized context, server-data-in-a-client-store.
3. Cross-reference the vendored Vercel rules (`frontend/react/vendor/reference/`) for perf / Next.js specifics.
4. For each finding: file + line, concrete issue, one-sentence fix.
5. **Do not rewrite.** Hand off to [`generator`](../generator/SKILL.md).

## Output format

```
| Severity | Location                              | Issue                                                              | Suggested fix                                                              |
|----------|---------------------------------------|--------------------------------------------------------------------|----------------------------------------------------------------------------|
| blocker  | app/(shop)/cart/page.tsx:18          | `await fetch('/api/cart')` in a `'use client'` component body        | Fetch in the Server Component parent and pass as props, or use TanStack Query |
| major    | src/features/cart/CartContext.tsx:24 | Context value `{ items, add, remove }` allocated inline every render  | Wrap in `useMemo` keyed on `items`; split read/write contexts               |
| major    | src/components/Menu.tsx:42           | `<div role="button" onClick>` instead of a real `<button>`           | Use `<button type="button">` for keyboard + screen-reader support           |
| major    | src/features/orders/OrderList.tsx:9  | `key={index}` on a reorderable list                                  | Key on `order.id` (stable domain id)                                        |
```

Severities per `CLAUDE.md`:
- **blocker** — ships a bug, breaks hook rules, async in render, secret in a client bundle, mutable module state
- **major** — design/perf issue that will hurt soon (misplaced `'use client'`, un-memoized context, derive-with-effect, server data in a client store, `<div onClick>`, missing three-state region)
- **minor** — style or small inconsistency
- **nit** — optional preference

## Anti-patterns to always flag

- **`'use client'` on a route just because one leaf is interactive** — push the directive down to the smallest interactive leaf.
- **`useEffect` to derive state** — compute in render; memoize only if profiling justifies it.
- **Set-state-from-props effect** — pass `key` to remount, or restructure ownership.
- **`await`ing data in a Client Component body** — fetch in the RSC parent, or use `use()` / a data hook.
- **Reading `window`/`localStorage`/`Date.now()` in render** — hydration mismatch; move to `useEffect`.
- **A Client Component importing a Server Component** — pass it through as `children` instead.
- **Server data in a client store** — that's RSC / TanStack Query's job, not Zustand's.
- **`key={index}` on a reorderable list** — state/focus corruption.
- **Context with everything in one provider** — re-renders the whole tree; split read/write.
- **Sequential awaits of independent fetches** — parallelize with `Promise.all` or push to RSC.
- **Hook inside `if`/`for`/early return** — the lint would catch it if it weren't disabled.
- **`<div onClick>` / click-handler-only nav** — loses keyboard, SR, prefetch, and open-in-new-tab; use `<button>` / `<Link>`.
- **Missing effect cleanup** — leaked subscriptions/timers across navigations.
- **`forwardRef` on React 19** — `ref` is a plain prop now.
- **Secret / server-only import in a `'use client'` module** — the client bundle is public.

## Handoffs

- Rewrite → [`generator`](../generator/SKILL.md)
- Conceptual lookup → [`reference`](../reference/SKILL.md)
- Vercel rule deep-dive → `frontend/react/vendor/reference/`
- Composition deep-dive → `frontend/react/vendor/composition-patterns`
- Component tests to lock a fix → [`component-testing`](../component-testing/SKILL.md)
- UI test-code review → **peer** `qa/typescript/skills/ui-test-author/reviewer`
- Auth0 wiring review → `auth/auth0-react`
