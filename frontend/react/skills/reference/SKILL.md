---
name: fe-react-reference
description: Use when explaining how React 19 / the Next.js App Router actually works — Server vs Client Components and the `'use client'` boundary, hydration, hooks, `use()`/Actions/`useActionState`/`useOptimistic`, Context vs store, `ref` as a prop. Triggers "Server or Client Component here", "where does 'use client' go", "Context vs Zustand", "Hydration failed because the server rendered HTML didn't match". Not for scaffolding (`generator`), reviewing (`reviewer`), or route files (`routing`).
---

# React Design Patterns — Reference

Conceptual reference for React 19 on Next.js App Router (RSC) — the primary target — with a Vite SPA fallback lane noted where it diverges. Covers the Server/Client component split and the `'use client'` boundary, hooks and the lifecycle they replace, the React 19 additions (`use()`, Actions, `useActionState`, `useOptimistic`, `ref` as a prop), Context vs stores, Suspense/streaming, and the "wait, is this running on the server or in the browser?" surprises that come with RSC.

## Version applicability

React 19 idioms are the primary recipes; React 18 equivalents are kept as explicitly tagged fallbacks — an 18 pattern is not obsolete, it's correct for that version. Detect the installed React (and Next.js) major from `package.json` and key the recipe to it.

| Concern | React 19 (primary) | React 18 (fallback) |
|---|---|---|
| Forwarding a ref | `ref` is a normal prop on function components | `forwardRef((props, ref) => …)` |
| Reading a promise / context in render | `use(promise)` / `use(Context)` — callable conditionally | `useContext` (unconditional); data via a hook, not in render |
| Form submit + pending + result | `<form action={fn}>` + `useActionState` | controlled `onSubmit` + manual `isPending` state |
| Optimistic UI | `useOptimistic` | manual "pending" copy of state + rollback |
| Document metadata | `<title>`/`<meta>`/`<link>` hoist from anywhere in the tree | `react-helmet` / Next `metadata` API only |
| Memoization | React Compiler auto-memoizes; hand `useMemo`/`useCallback` only where it can't | manual `useMemo`/`useCallback`/`React.memo` |
| Context provider | `<Ctx>` (provider shorthand) | `<Ctx.Provider>` |

Next.js: 15 (App Router, async request APIs, `cache` semantics) is primary; 14 is the tagged fallback. The Pages Router is legacy — the App Router recipes below assume `app/`.

## When to use

- "What's the right state pattern for X in React?"
- "Should this be a Server or a Client Component?"
- "Where does the `'use client'` boundary go?"
- "What does `use()` / `useActionState` / `useOptimistic` do?"
- Comparing two React approaches conceptually

## When NOT to use

- Scaffolding a component/hook → [`generator`](../generator/SKILL.md)
- Reviewing → [`reviewer`](../reviewer/SKILL.md)
- Where files live on disk → [`project-scaffold`](../project-scaffold/SKILL.md)
- Picking a state library in depth → [`state-management`](../state-management/SKILL.md)
- Blazor → `frontend/blazor/skills/reference`
- Auth0 in React → `auth/auth0-react`

---

## The rendering model — Server vs Client Components

On the App Router, **components are Server Components by default.** They run on the server (at build or per request), never ship to the browser, can be `async` and `await` data directly, and hold no state or effects. A component becomes a **Client Component** only when a file (or one it's imported from) carries the `'use client'` directive — then it and everything it imports ship to the browser and hydrate.

| | Server Component (default) | Client Component (`'use client'`) |
|---|---|---|
| Runs | Server, once | Server (prerender) **and** browser (hydrate) |
| Can `await` data in the body | Yes | No — use `use()`/hooks/TanStack Query |
| `useState`/`useEffect`/event handlers | No | Yes |
| Browser APIs (`window`, `localStorage`) | No | Yes (in effects) |
| Secrets / DB / server-only deps | Yes | **Never** — it ships to the client |
| Ships JS to the browser | No | Yes |

**The mental shift:** you are not building a client app backed by a server; you are building a **server app with selective client interactivity** — the App-Router analog of Blazor's "static SSR is the default, interactivity is an opt-in island."

### The `'use client'` boundary — push it to the leaves

`'use client'` marks where the client bundle *begins*: the file and its whole import subtree become client code. So:

- **Put the directive on the smallest interactive leaf**, not the route. A page that's mostly static with one interactive widget stays a Server Component and renders `<LikeButton>` (its own `'use client'` file) as a child. Marking the page client drags the entire subtree into the bundle.
- **You don't repeat it** on every child — one boundary covers everything below it.
- **A Client Component cannot `import` a Server Component** (that would ship server code). Instead pass server-rendered output *through* it as `children` (or any prop): `<ClientShell>{<ServerContent/>}</ClientShell>`. The client wrapper renders the server-provided node without importing it.
- **Defensive `'use client'` everywhere is the classic anti-pattern** — teams creep the whole tree client and end up with a bigger bundle than the old Pages Router. Default server; opt in per leaf.

### Vite SPA fallback lane

Without RSC, **every** component is a client component and there is no server body-`await`; data comes from hooks (TanStack Query / `use()` on a cached promise) and the root is `createRoot(...).render(<App/>)`. The "push the boundary to the leaves" rule still buys you code-splitting via `lazy`, but the server/client *type* distinction disappears. Skills tag Vite-specific guidance explicitly.

## Component composition

- **Props** are function parameters — typed with an explicit `Props` interface, no `any`.
- **Children** are `children: React.ReactNode`; named slots are just more `ReactNode` props (`header`, `footer`).
- **Two-way binding** is value-in / onChange-out — a controlled component takes `value` + `onChange`, it never owns the source of truth it's editing.
- **Event props** are plain callbacks — `onSelect: (id: string) => void`. (React's analog of Blazor's `EventCallback`; there's no awaitable-callback ceremony.)
- **Compound components** share implicit state through a Context the parent provides and the children consume (`<Tabs><Tab/></Tabs>`) — see [`state-management`](../state-management/SKILL.md).

### `ref` as a prop (React 19)

Function components receive `ref` as an ordinary prop — **`forwardRef` is gone.** A reusable input just declares `ref?: React.Ref<HTMLInputElement>` and spreads it. On React 18, wrap with `forwardRef` (tagged fallback). Never reach into the DOM with a `ref` to do what state/props express declaratively; `ref` is for focus, measurement, and integrating non-React widgets.

## Component architecture — the layering taxonomy

The atomic-design vocabulary (**atom → molecule → organism → template → page**) is the reasoning behind component structure. [`project-scaffold`](../project-scaffold/SKILL.md) owns the **placement heuristic** — which reuse level lives in a shared `components/` folder vs a feature folder, and the "promote on the second reuse" rule. This section is *why the levels differ*. Don't build a global `atoms/`/`molecules/` folder tree — the taxonomy is a placement heuristic, not a directory structure.

### The levels, and what changes as you go up

| Level | Domain awareness | Owns state? | Data reach | Server/Client |
|---|---|---|---|---|
| **Atom** | None | No — fully controlled | None | Agnostic (usually can be a Server Component; client only if it has an event handler) |
| **Molecule** | None (generic) | **Only ephemeral UI state** (open/closed, hover) | None | Client if interactive, else agnostic |
| **Organism** | Yes — knows a model slice | Local view state OK; domain data via props/hooks | Props, or a client data hook | Depends on interactivity |
| **Template** | None (layout only) | No | None | Server Component |
| **Page / route** | Yes — orchestrates | Owns the fetch + page-level state | Owns the data fetch (`await` in RSC) | The Server Component that **decides** where the `'use client'` islands sit |

The through-line: **domain knowledge and data ownership climb as you go up; a leaf stays domain-free and controlled.** An atom that reads a data hook or names a domain type has skipped two levels — it's a mislabeled organism and won't be reusable.

### Naming

- **Atom/molecule names describe the control, not the domain**: `CurrencyInput`, `SearchBox`, `Pagination`, `Badge` — never `OrderSearchBox` (that coupling makes it a one-use organism).
- **Organism names name the domain concept**: `OrderTable`, `CustomerCard`, `CheckoutSummary`.
- **Page/route names match the route**; templates name the arrangement (`TwoPaneLayout`, `AppShell`).
- One name → one concept across the app (the IA rule [`ui-conventions`](../ui-conventions/SKILL.md) enforces app-wide).

### Prop-drilling limits — when to stop passing props down

| Depth / shape | Use |
|---|---|
| 1–2 levels, one value | plain prop passing (explicit, testable) |
| Deep subtree, cross-cutting (theme, current user, locale) | **Context** + a consumer hook |
| Shared across routes / unrelated subtrees | a **store** (Zustand) — see [`state-management`](../state-management/SKILL.md) |
| Server data needed deep | fetch in the RSC and pass as props, or a **TanStack Query** hook at the point of use — never drill fetched data through 5 layers |

Rule of thumb: **drill props, Context cross-cutting client state, store shared client state, and fetch server state where it's used.** If you're drilling the same value past three components, promote it to a Context or store. If you're drilling a *callback* up through layers, the event probably belongs on a store the interested components subscribe to directly.

### When a component owns state

Default: components are **controlled** — value in via props, changes out via a callback. A component may own state only when it's **ephemeral and purely presentational**: a dropdown's open flag, a "show password" toggle, hover/focus visuals, an accordion's expanded section. The moment another component or the server needs the value — a picker's selection, a form field's value ([`forms`](../forms/SKILL.md) owns that), anything two components must agree on — **lift it** to a parent, a Context, or a store. *If someone else needs to know it, it isn't this component's to own.*

### Composition over configuration

Prefer composing small components (pass `children`/slot props) over one component with 20 boolean props and mode flags. A `Card` with `header`/`children`/`footer` slots beats a `Card` with `showHeader`/`headerText`/`showFooter` booleans — the global "composition over inheritance/configuration" rule applied to the render tree, and what keeps atoms/molecules domain-free (they expose slots; the organism fills them). See `frontend/react/vendor/composition-patterns` for the deep treatment (compound components, explicit variants over booleans).

## Hooks — the lifecycle, and the rules

There is no `OnInitialized`/`OnAfterRender` ladder; effects and derived values replace it.

- **`useState`** — one or two scalar values. **`useReducer`** — multiple related fields with non-trivial transitions (makes the transitions explicit).
- **`useEffect`** — synchronize with an *external* system (subscriptions, a non-React widget, the URL, a browser API). **It is not for deriving state from props** — compute that during render. Most "sync two states with an effect" code is a bug; the value should be derived or lifted. Every effect that subscribes **must** return a cleanup that unsubscribes.
- **`useMemo`/`useCallback`** — with the **React Compiler** on (default in new Next 15 apps), most memoization is automatic; add them by hand only where the compiler can't (a value passed to a non-React API, a measured hot path). Don't scatter them preemptively.
- **`useRef`** — mutable value that doesn't trigger re-render (a DOM node, a timer id, the latest value for an event handler).
- **Rules of hooks:** call them unconditionally at the top level of a component/hook — **except `use()`**, which may be called conditionally, in loops, and inside `if`.
- **`useDeferredValue` / `useTransition`** — keep the UI responsive during expensive updates (mark a state change non-urgent; show the old value while the new one computes). See [`performance`](../performance/SKILL.md).

### Client-only browser APIs (the "there is no interop barrier" note)

React has no Blazor-style JS-interop boundary: browser APIs (`window`, `localStorage`, `IntersectionObserver`, a charting lib) are just called from a **Client Component**, guarded so they don't run during the server render — inside `useEffect` (which never runs on the server) or behind a mounted check. Wrap the access in a custom hook (`useLocalStorage`, `useMediaQuery`) rather than touching the global directly in render. A third-party non-React widget is initialized in an effect against a `ref` and **torn down in the effect's cleanup**. That's the whole story — there's no separate interop skill.

## React 19 data & Actions

- **`use(promise)`** — read a promise during render; the component **suspends** until it resolves (needs a `<Suspense>` boundary above). In RSC you pass a promise created in a Server Component down to a Client Component and `use()` it, streaming the result.
- **`use(Context)`** — read Context, callable conditionally (unlike `useContext`).
- **Actions** — an `async` function passed to `<form action={fn}>` (or called in a transition). React tracks pending state and errors for you.
- **`useActionState(fn, initial)`** — wraps an Action, returning `[state, formAction, isPending]`; the canonical form-submit + server-error + pending pattern (owned in depth by [`forms`](../forms/SKILL.md)).
- **`useOptimistic(value, reducer)`** — show an immediate optimistic value that auto-reverts if the underlying Action fails.

On the App Router these pair with **Server Actions** (`'use server'` functions) for mutations — [`data-access`](../data-access/SKILL.md) and [`forms`](../forms/SKILL.md) own the recipes. React 18 fallback: controlled `onSubmit` with hand-rolled `isPending`/error/rollback state.

## Context — the built-in cross-cutting mechanism

The analog of Blazor's `CascadingValue`. One provider, many consumers:

```tsx
'use client';
import { createContext, use, useMemo, useState, type ReactNode } from 'react';

type Theme = { mode: 'light' | 'dark'; toggle: () => void };
const ThemeContext = createContext<Theme | null>(null);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [mode, setMode] = useState<'light' | 'dark'>('light');
  const value = useMemo<Theme>(
    () => ({ mode, toggle: () => setMode(m => (m === 'light' ? 'dark' : 'light')) }),
    [mode],
  );
  return <ThemeContext value={value}>{children}</ThemeContext>; // React 19 provider shorthand
}

export function useTheme() {
  const ctx = use(ThemeContext);
  if (!ctx) throw new Error('useTheme must be used within <ThemeProvider>');
  return ctx;
}
```

Rules: **memoize the value** (stable identity), **throw on use-outside-provider**, and **split read/write Contexts** when write churn would re-render read-only consumers ([`state-management`](../state-management/SKILL.md) shows the split). Don't cascade a 30-field "page model" — one Context per concern.

## Hydration & the double-render trap

A Client Component renders **on the server (prerender)** and **again in the browser (hydrate)** — the markup must match. Reading `window`/`Date.now()`/`localStorage`/`Math.random()` during render produces a **hydration mismatch** (server HTML ≠ client HTML). Fixes: read those in `useEffect` (post-hydration), gate on a mounted flag, or mark the subtree `suppressHydrationWarning` only when the difference is intentional and cosmetic. This is React's version of Blazor's prerender double-fetch — and RSC avoids the *data* double-fetch outright because the Server Component fetches once and the client never re-runs that body.

## Keys, lists, and reconciliation

- **Keys are stable domain ids** (`order.id`), never the array index — an index key corrupts state and focus when the list reorders or an item is removed. (The React analog of Blazor's `@key`.)
- Derive rendered lists from state during render; don't mirror a list into a second `useState`.
- Sort/filter deterministically — a grid with no stable sort reorders on every refetch ([`ui-conventions`](../ui-conventions/SKILL.md)).

## Navigation

- In-app navigation is a **real `<Link href>`** (`next/link`, or `<Link>`/`<NavLink>` from React Router in the SPA lane) — never an `onClick` calling `router.push` on a `<div>`. Real links get prefetch, middle-click, open-in-new-tab, and crawlability for free (the SEO rule — [`seo-discoverability`](../seo-discoverability/SKILL.md)).
- `useRouter().push` is for **programmatic** navigation only (after a mutation, a redirect) — not to replace anchors.

## Comparison: React ↔ Blazor

| Concept | React (App Router) | Blazor |
|---|---|---|
| Component | `.tsx` function | `.razor` file |
| Props | function parameters | `[Parameter]` |
| Default render | Server Component | Static SSR |
| Interactivity opt-in | `'use client'` leaf | `@rendermode` island |
| State | `useState` / Context / Zustand | service / `CascadingValue` / `[Parameter]` |
| Event prop | `(t: T) => void` | `EventCallback<T>` |
| Side effect | `useEffect` | `OnInitializedAsync` / `OnAfterRenderAsync` |
| Context | `createContext` + provider/hook | `CascadingValue` / `CascadingParameter` |
| Mutation + pending | Action + `useActionState` | `EditForm` + `OnValidSubmit` |
| No-double-fetch | RSC fetches once (no client re-run) | `[PersistentState]` |

## Common gotchas

- **Defensive `'use client'`** creeping the whole tree into the bundle — default server, opt in per leaf.
- **`await`ing data in a Client Component body** — you can't; fetch in the RSC parent, or use `use()`/a data hook.
- **Reading `window`/`localStorage` in render** → hydration mismatch. Do it in `useEffect`.
- **Index keys** in dynamic lists — state/focus corruption on reorder.
- **`useEffect` syncing two pieces of state** — almost always one should be derived, not stored.
- **Missing effect cleanup** — leaked subscriptions/timers across navigations.
- **Server data in a client store** — that's TanStack Query / RSC's job, not Zustand's ([`state-management`](../state-management/SKILL.md)).
- **A Client Component importing a Server Component** — pass it as `children` instead.

## Handoffs

- Scaffolding components/hooks/pages → [`generator`](../generator/SKILL.md)
- Reviewing React code → [`reviewer`](../reviewer/SKILL.md)
- Picking a state library → [`state-management`](../state-management/SKILL.md)
- Data fetching / Server Actions → [`data-access`](../data-access/SKILL.md); forms → [`forms`](../forms/SKILL.md)
- Where files live → [`project-scaffold`](../project-scaffold/SKILL.md)
- Auth0 wiring → `auth/auth0-react`
