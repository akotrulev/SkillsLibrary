---
name: fe-react-generator
description: Use when the user asks to scaffold a React pattern into the active repo (Next.js App Router primary, Vite SPA fallback; React 19 primary / 18 fallback) — a page/route, a reusable component, a form, a custom hook, a context+consumer, a compound component, container/presentation split, an error boundary, or a Suspense/lazy boundary. Triggers "scaffold a component/page for X", "extract this into a custom hook", "create a context provider for Y", "make a compound component for tabs", "split into container + presentation", "add a route with metadata", "wire a real Link instead of router.push". Do NOT use for explanations (use `frontend/react/skills/reference`), reviews (use `frontend/react/skills/reviewer`), form validation depth (use `frontend/react/skills/forms`), data-fetch mechanics (use `frontend/react/skills/data-access`), or Blazor (use `frontend/blazor/skills/generator`).
---

# React — Generator

Scaffolds React components, hooks, pages, and patterns into the active repo. Everything lands **RSC-by-default** (server component unless a leaf genuinely needs interactivity), typed strictly (no `any`), with a `data-testid` on every interactive element and list/grid container, real `<Link href>` for in-app navigation, `metadata` on every route, stable keys, cleaned-up effects, and a co-located test for non-trivial units.

**Version rule:** detect the React/Next major first (`package.json`). React 19 idioms are primary — `use()`, Actions + `useActionState`, `useOptimistic`, **ref-as-prop** (no `forwardRef`), `<title>`/`<meta>` hoisting. React 18 fallbacks (`forwardRef`, `useFormState`, `react-helmet`, manual data hooks) are tagged. Never emit a React-19-only API into an 18 project. Next.js 15 primary / 14 fallback tracks alongside; the Vite + React Router 7 SPA lane is the tagged fallback where a recipe is rendering-sensitive.

## When to use

- New page / route (App Router `page.tsx` or SPA route element)
- Reusable component (input, table, dialog, compound widget)
- Extracting a custom hook from inline `useState`/`useEffect` logic
- Replacing prop drilling with a context provider + consumer hook
- Converting coupled components into a compound component
- Splitting a fat component into container + presentation
- Wrapping a feature with an error boundary / a Suspense + lazy boundary

## When NOT to use

- Explaining a pattern → [`reference`](../reference/SKILL.md)
- Reviewing existing code → [`reviewer`](../reviewer/SKILL.md)
- Form validation / RHF+Zod / Server-Action forms depth → [`forms`](../forms/SKILL.md)
- Fetch / caching / mutation mechanics → [`data-access`](../data-access/SKILL.md)
- Auth UI (login/signup) → `auth/auth0-react`
- Blazor → `frontend/blazor/skills/generator`

## Inputs needed

1. **React / Next major** — React 19 vs 18, Next 15 vs 14, or Vite SPA (drives which recipe variant is emitted)
2. **Pattern** — page, component, custom hook, context, compound, container/presentation, error boundary, Suspense/lazy
3. **Component/route name** + responsibilities
4. **Boundary** — does this need interactivity (`'use client'`) or is it presentational (stays a Server Component)?
5. **Props in / events out** — the typed surface
6. **Data source** — RSC `fetch`, TanStack Query, Server Action, local state
7. **Shared state needed** — none / context / store

## The boundary decision (do this first)

Every generated artifact starts as a **Server Component**. Add `'use client'` **only** to the leaf that needs interactivity — state, effects, event handlers, browser APIs, a library component with hooks. Never blanket a whole route client because one button needs `onClick`; push the boundary to the smallest island and pass server-fetched data down as **serializable props**. The Vite SPA lane has no RSC — every component is a client component, so the directive is omitted there. Boundary placement per route is [`project-scaffold`](../project-scaffold/SKILL.md)'s; this skill applies it per artifact.

## Recipes

### Page / route (App Router, RSC + `metadata`)

```tsx
// app/orders/page.tsx  — a Server Component: fetches on the server, ships no JS
import type { Metadata } from 'next';
import Link from 'next/link';
import { OrdersTable } from '@/features/orders/OrdersTable';

export const metadata: Metadata = { title: 'Orders' };

export default async function OrdersPage() {
  const orders = await fetch('https://api.example.com/orders', {
    next: { revalidate: 60 },
  }).then((r) => r.json());

  return (
    <main>
      <h1>Orders</h1>
      <Link href="/orders/new" data-testid="Orders.NewLink">New order</Link>
      <OrdersTable orders={orders} data-testid="Orders.Grid" />
    </main>
  );
}
```

Dynamic titles use `generateMetadata`; a per-route not-found uses `not-found.tsx` + `notFound()` from `next/navigation` ([`seo-discoverability`](../seo-discoverability/SKILL.md) owns the metadata/404 depth). **React 18 / SPA fallback:** no `metadata` export — set the title with `react-helmet` (or the Next Pages `Head`), and the page is a client component that fetches via TanStack Query.

### Reusable component (presentational — stays a Server Component)

```tsx
// features/orders/OrdersTable.tsx  — no hooks/handlers → no 'use client'
type Props = { orders: Order[]; 'data-testid'?: string };

export function OrdersTable({ orders, 'data-testid': testId }: Props) {
  return (
    <table data-testid={testId}>
      <tbody>
        {orders.map((o) => (
          <tr key={o.id} data-testid="Orders.Row">
            <td data-testid="Orders.Row.Reference">{o.reference}</td>
            <td data-testid="Orders.Row.Status">{o.status}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
```

Keys are the **stable domain id** (`o.id`), never the array index. Row `data-testid` is a **static** parent locator; children namespace under it — tests address rows by index over `Orders.Row` ([`testability`](../testability/SKILL.md) rules 2 & 6).

### Interactive component (`'use client'` island)

```tsx
'use client';
import { useState } from 'react';

type Props = {
  label: string;
  onConfirm: () => void;
  disabled?: boolean;
  disabledReason?: string;
};

export function ConfirmButton({ label, onConfirm, disabled, disabledReason }: Props) {
  const [busy, setBusy] = useState(false);
  return (
    <button
      type="button"
      disabled={disabled || busy}
      title={disabled ? disabledReason : undefined}   // disable-don't-hide — ui-conventions §4
      onClick={async () => { setBusy(true); try { await onConfirm(); } finally { setBusy(false); } }}
      data-testid="ConfirmButton"
    >
      {busy ? 'Working…' : label}
    </button>
  );
}
```

Only the interactive leaf is a client component; its parent page/table can stay a Server Component.

### Custom hook

One file per hook under `src/hooks/`, named `use<Verb><Noun>.ts`. Exhaustive dep array, cleanup returned, single responsibility.

```typescript
// src/hooks/useDebouncedValue.ts
import { useEffect, useState } from 'react';

export function useDebouncedValue<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const id = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(id);
  }, [value, delayMs]);
  return debounced;
}
```

### Context + provider + consumer hook

Three exports in one file: the context (private), the provider, and a consumer hook that throws outside the provider. Never expose the raw context — consumers would skip the null-check. The value is `useMemo`'d so readers don't re-render every parent render.

```tsx
// src/features/cart/CartContext.tsx
'use client';
import { createContext, useContext, useMemo, useState, type ReactNode } from 'react';

type CartContextValue = {
  items: ReadonlyArray<CartItem>;
  add: (item: CartItem) => void;
  remove: (id: string) => void;
};

const CartContext = createContext<CartContextValue | null>(null);

export function CartProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<CartItem[]>([]);
  const value = useMemo<CartContextValue>(() => ({
    items,
    add: (item) => setItems((xs) => [...xs, item]),
    remove: (id) => setItems((xs) => xs.filter((x) => x.id !== id)),
  }), [items]);
  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
}

export function useCart(): CartContextValue {
  const ctx = useContext(CartContext);
  if (!ctx) throw new Error('useCart must be used within <CartProvider>');
  return ctx;
}
```

Split read and write contexts when their consumers differ, so readers don't re-render when only the writer changes. Context is for **client** state — server state stays in TanStack Query / RSC fetch ([`state-management`](../state-management/SKILL.md)).

### Compound component

For parts with a strict ownership relationship, so the markup reads like the UI (`<Tabs>` + `<Tabs.Trigger>` + `<Tabs.Panel>`). Implemented via internal context — no prop drilling. `useId` gives SSR-safe ids; a11y attributes are part of the contract, generated alongside the markup.

```tsx
// src/components/Tabs.tsx
'use client';
import { createContext, useContext, useId, useState, type ReactNode } from 'react';

type TabsCtx = { active: string; setActive: (id: string) => void; baseId: string };
const Ctx = createContext<TabsCtx | null>(null);
const useTabs = () => {
  const c = useContext(Ctx);
  if (!c) throw new Error('Tabs.* must be used within <Tabs>');
  return c;
};

export function Tabs({ defaultValue, children }: { defaultValue: string; children: ReactNode }) {
  const [active, setActive] = useState(defaultValue);
  const baseId = useId();
  return <Ctx.Provider value={{ active, setActive, baseId }}>{children}</Ctx.Provider>;
}

Tabs.List = function List({ children }: { children: ReactNode }) {
  return <div role="tablist">{children}</div>;
};

Tabs.Trigger = function Trigger({ value, children }: { value: string; children: ReactNode }) {
  const { active, setActive, baseId } = useTabs();
  return (
    <button
      role="tab"
      id={`${baseId}-trigger-${value}`}
      aria-selected={active === value}
      aria-controls={`${baseId}-panel-${value}`}
      onClick={() => setActive(value)}
      data-testid={`Tabs.Trigger.${value}`}
    >
      {children}
    </button>
  );
};

Tabs.Panel = function Panel({ value, children }: { value: string; children: ReactNode }) {
  const { active, baseId } = useTabs();
  if (active !== value) return null;
  return (
    <div role="tabpanel" id={`${baseId}-panel-${value}`} aria-labelledby={`${baseId}-trigger-${value}`}>
      {children}
    </div>
  );
};
```

### Container / presentation split

Only when the presenter is reused with different data sources, or the container's state coordination would obscure the markup. Otherwise one component is fine. In App Router, prefer a **Server Component container** that fetches and passes serializable props to a `'use client'` presenter — marks `'use client'` only on the interactive leaf.

```tsx
// features/orders/OrdersList.presenter.tsx  — 'use client' only if it has handlers
'use client';
export function OrdersListPresenter({ orders, onSelect }: {
  orders: Order[]; onSelect: (id: string) => void;
}) {
  return (
    <ul data-testid="Orders.List">
      {orders.map((o) => (
        <li key={o.id}>
          <button onClick={() => onSelect(o.id)} data-testid="Orders.Row.SelectButton">
            {o.reference}
          </button>
        </li>
      ))}
    </ul>
  );
}

// app/orders/page.tsx  — Server Component container fetches, passes props down
import { OrdersListPresenter } from '@/features/orders/OrdersList.presenter';
export default async function OrdersPage() {
  const orders = await getOrders();       // server-side
  return <OrdersListPresenter orders={orders} onSelect={/* a client action */} />;
}
```

### Error boundary + fallback

App Router: use the framework's `error.tsx` file convention at the route level — don't hand-roll. Below a route, use `react-error-boundary`'s `<ErrorBoundary>` (function-component API) around a feature, with a fallback that offers **retry** and preserves layout (never collapses to blank — [`error-resilience`](../error-resilience/SKILL.md)).

```tsx
// app/orders/error.tsx  — App Router route error boundary (must be a client component)
'use client';
export default function OrdersError({ error, reset }: { error: Error; reset: () => void }) {
  return (
    <div role="alert" data-testid="Orders.Error">
      <p>Couldn’t load orders.</p>
      <button onClick={reset} data-testid="Orders.Error.Retry">Try again</button>
    </div>
  );
}
```

### Suspense + lazy

```tsx
import { lazy, Suspense } from 'react';
const Reports = lazy(() => import('./Reports'));

export function ReportsRoute() {
  return (
    <Suspense fallback={<ReportsSkeleton />}>
      <Reports />
    </Suspense>
  );
}
```

The skeleton **approximates the final layout** (height, columns) so there's no layout shift — a generic spinner shifts. For data-loading Suspense, use TanStack Query's suspense mode or RSC `<Suspense>` boundaries; don't roll your own.

## Rules

- **RSC by default; `'use client'` opt-in per island.** Server Components fetch; Client Components interact; data crosses the boundary as serializable props. Never blanket a route client for one leaf.
- **Every interactive element and list/grid container carries a `data-testid`** per [`testability`](../testability/SKILL.md) — PascalCase dot-separated, static row locators, never array index / id / GUID.
- **In-app navigation is a real `<Link href>`** (`next/link`, or React Router `<Link>`/`<NavLink>` in the SPA lane) — never an `onClick` `router.push` on a `<div>`. Real links get prefetch, middle-click, open-in-new-tab, crawlability for free. Same tab by default; `target="_blank"` only for the [`ui-conventions`](../ui-conventions/SKILL.md) §7 exceptions, and then with `rel="noopener"` + a visible "opens in new tab" cue + an `aria-label` suffix.
- **Every route emits a title** — `metadata`/`generateMetadata` (App Router) or `react-helmet` (SPA).
- **Keys are stable domain ids**, never the array index.
- **Effects have exhaustive deps and return cleanup**; subscriptions/listeners/timers are torn down.
- **No `useEffect` for derived state** — derive during render. No effect to "sync state from props" — use `key` to remount or compute in render.
- **Context value is `useMemo`'d**; never a fresh object literal in the provider's `value=`.
- **`useMemo`/`useCallback` only when a real downstream memo benefits** — they cost; don't blanket them.
- **Hooks at the top level only** — never inside `if`/`for`/early return. Custom hooks are `use`-prefixed.
- **Ref-as-prop on React 19** (a `ref` prop, no `forwardRef`); `forwardRef` only on React 18.
- **Strict TypeScript, no `any`**; event handlers typed (`React.ChangeEvent<HTMLInputElement>`); component files PascalCase, hooks camelCase.
- **A11y attributes are part of the component contract** — roles, labels, `aria-*` generated with the markup, not deferred. Semantic HTML before ARIA; `<button>` for actions, never `<div onClick>`.
- **Every data region ships loading / loaded / failed states** (Suspense + error boundary, or the three-state hook) — a failure never collapses to blank.
- **No server data in client stores** — TanStack Query / RSC own server state; Zustand/Context own client state.

## What NOT to do

- No blanket `'use client'` on a route because one leaf is interactive — push the boundary to the leaf.
- No `onClick` `router.push` navigation on a `<div>`; no page/route without a title.
- No interactive element or grid container without a `data-testid`; no per-row testid prop (hardcode the static row locator).
- No array index as a key; no numeric id / GUID / index inside a locator.
- No `useEffect` for derived state or to copy props into state.
- No context `value={{ … }}` object literal without `useMemo`; no raw context exported to consumers.
- No `any` / `@ts-ignore` to silence the compiler — fix the type.
- No hooks called conditionally; no `forwardRef` on React 19 (use ref-as-prop); no `react-helmet` on App Router (use `metadata`).
- No `<div onClick>` for an interactive element; no un-torn-down subscription/timer.
- No `useMemo`/`useCallback` sprinkled "for performance" with no memoized consumer.
- No React-19-only API (`use()`, `useActionState`, `useOptimistic`, ref-as-prop, `<title>` hoist) emitted into a React 18 project.
- No server state duplicated into a client store.
- No business logic in components — push into hooks / services; components render and dispatch.

## Generation outputs

For every artifact:

1. The file(s) under the project's conventional folder (`app/`, `src/components/`, `src/hooks/`, `src/features/<feature>/`)
2. A barrel `index.ts` export when the project uses index files; otherwise direct imports
3. A **Vitest + React Testing Library** test for logic-bearing units — exercise behavior, not implementation (`getByRole('button', { name: 'Save' })`, not a `querySelector`) ([`component-testing`](../component-testing/SKILL.md))
4. A Storybook entry if Storybook is in the project

## Validation

- `pnpm tsc --noEmit` — 0 errors
- `pnpm lint` — 0 warnings (React Hooks + a11y rules included)
- `pnpm test` — generated tests pass
- Smoke in the dev server: interactivity behaves, no console/hydration errors, no double fetch across the RSC → client boundary, links navigate same-tab

## Handoffs

- Conceptual lookup → [`reference`](../reference/SKILL.md)
- Reviewing the result → [`reviewer`](../reviewer/SKILL.md)
- Form validation / RHF+Zod / Server-Action forms → [`forms`](../forms/SKILL.md)
- Fetch / caching / mutation mechanics → [`data-access`](../data-access/SKILL.md)
- `data-testid` placement rules → [`testability`](../testability/SKILL.md)
- Display / table / CRUD / confirmation / IA correctness → [`ui-conventions`](../ui-conventions/SKILL.md)
- Styling / theme / CSS Modules → [`styling`](../styling/SKILL.md)
- Auth wiring → `auth/auth0-react`
- E2E tests against these locators → `qa-ui-typescript` (peer)
