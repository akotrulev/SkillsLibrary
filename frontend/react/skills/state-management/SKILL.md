---
name: fe-react-state-management
description: Use when state has outgrown `useState` or lives in the wrong place — local state, lifted state, Context + reducer, Zustand, Redux Toolkit, Jotai, and the server-vs-client-state split (TanStack Query / RSC own server state). Triggers "what's the right state library here", "Redux Toolkit vs Zustand", "Context or store", "I'm prop-drilling everywhere", "this state is out of sync across pages". Not for forms (`forms`) or data fetching itself (`data-fetching`).
---

# React — State Management

Picks the right state primitive for the job. House style: **local first, lift only when shared, Context for cross-cutting non-frequent client state, TanStack Query (or RSC/Server Actions) for server state, Zustand for global client state when needed, Redux Toolkit only when the team's already on it.** React 19 + TypeScript strict; Next.js App Router primary (RSC changes *where* state lives), Vite SPA fallback.

## When to use

- A feature needs to share state across components
- Existing code prop-drills more than ~2 levels
- Choosing between Context, Zustand, Redux, Jotai
- Separating **server state** (what the API knows) from **client state** (UI-only)
- Migrating from a heavyweight store to a lighter one

## When NOT to use

- New component scaffolding → [`component-writer`](../component-writer/SKILL.md)
- Form state specifically → [`forms`](../forms/SKILL.md)
- The data-fetching mechanics themselves (RSC fetch, Server Actions, TanStack Query setup) → [`data-fetching`](../data-fetching/SKILL.md)
- Conceptual lookup → [`basics`](../basics/SKILL.md)
- Blazor → `frontend/blazor/skills/state-management`

## Inputs needed

1. **What kind of state**: server data (fetched from API), UI state (toggles, modals, focus), session state (current user, theme), form state, URL-derivable state
2. **Sharing scope**: one component, one screen, one feature, app-wide
3. **Mutation pattern**: rarely changed, edited frequently, optimistic updates needed
4. **Persistence**: in-memory, sessionStorage, localStorage, URL, cookie
5. **Framework**: Next.js App Router (RSC implications) or Vite SPA

## Decision tree

```
Is this server data (fetched from an API / DB)?
  ├─ yes → In an RSC route? fetch in the Server Component; mutate with a Server Action.
  │        Need it in a Client Component (caching, refetch, optimistic)? → TanStack Query.
  │        Never put server state in a global client store.
  └─ no  ↓
Can it be derived from the URL (filter, page, tab, selected id)?
  ├─ yes → the URL is the state — useSearchParams. Shareable + back-button works.
  └─ no  ↓
Is the state used by only one component?
  ├─ yes → useState / useReducer in that component
  └─ no  ↓
Is it a parent + a few children?
  ├─ yes → lift to the parent + prop passing. Two levels is fine.
  └─ no  ↓
Is it cross-cutting (theme, user, feature flags)?
  ├─ yes → React Context + a consumer hook
  └─ no  ↓
Changed frequently or by many disconnected components?
  ├─ yes → Zustand (or Redux Toolkit if already adopted)
  └─ no  → Context is still fine
```

## Server state vs client state — the #1 lesson

```
Server state           Client state
─────────────────────  ──────────────────────────
Lives in the API/DB    Lives in the browser
Async                  Sync
Shared with others     Single user
Stale unless refreshed Always current
Needs caching          Doesn't need caching
```

**Don't store server data in Redux / Zustand / Context.** That re-invents caching, refetch, invalidation, and optimistic updates — and always loses against the tools built for it. On the App Router, the *first* answer for server state is **not a client library at all**: fetch in a Server Component and pass props; mutate with a Server Action and `revalidate`. Reach for TanStack Query when a **Client Component** needs client-side caching/refetch/optimism. [`data-fetching`](../data-fetching/SKILL.md) owns the fetch mechanics; this skill owns *which bucket the state belongs in*.

```tsx
// ✅ Client-side server state via TanStack Query (a Client Component that needs caching)
'use client';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

export function useOrders(customerId: string) {
  return useQuery({
    queryKey: ['orders', customerId],
    queryFn: () => api.get(`/orders?customerId=${customerId}`),
    staleTime: 30_000,
  });
}

export function useCreateOrder() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (cmd: CreateOrder) => api.post('/orders', cmd),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['orders'] }),
  });
}
```

```tsx
// ✅ Client state via useState / Zustand / Context — never server data
const [isMenuOpen, setMenuOpen] = useState(false);
```

## useState / useReducer

The default. `useState` for one or two scalars; `useReducer` when state has multiple related fields with non-trivial transitions — it makes the transitions explicit and discoverable:

```tsx
type CartAction =
  | { type: 'add'; item: CartItem }
  | { type: 'remove'; id: string }
  | { type: 'clear' };

function cartReducer(state: CartItem[], action: CartAction): CartItem[] {
  switch (action.type) {
    case 'add':    return [...state, action.item];
    case 'remove': return state.filter(i => i.id !== action.id);
    case 'clear':  return [];
  }
}
// const [items, dispatch] = useReducer(cartReducer, []);
```

**Derive, don't store.** If a value can be computed from existing state/props during render, compute it — don't add a second `useState` kept in sync with a `useEffect`. That effect-sync pattern is the most common state bug in React.

## Context — for cross-cutting client state

Use for state that's read by many components, written rarely (theme, current user, locale, feature flags), and app- or feature-wide.

```tsx
'use client';
import { createContext, use, useMemo, useState, type ReactNode } from 'react';

type AuthValue = { user: User | null; setUser: (u: User | null) => void };
const AuthContext = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const value = useMemo<AuthValue>(() => ({ user, setUser }), [user]);
  return <AuthContext value={value}>{children}</AuthContext>; // React 19 provider shorthand
}

export function useAuth() {
  const ctx = use(AuthContext);            // React 19 use(); React 18: useContext
  if (!ctx) throw new Error('useAuth must be used within <AuthProvider>');
  return ctx;
}
```

Rules: **memoize the value**, **throw on use-outside-provider**, and **split read/write** if consumers differ.

### Split read/write contexts

When a frequently-changing value would re-render readers that only care about actions:

```tsx
const StateCtx   = createContext<State | null>(null);
const ActionsCtx = createContext<Actions | null>(null);

export function CartProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(cartReducer, []);
  const actions = useMemo(() => ({
    add:    (i: CartItem) => dispatch({ type: 'add', item: i }),
    remove: (id: string)  => dispatch({ type: 'remove', id }),
    clear:  ()            => dispatch({ type: 'clear' }),
  }), []);
  return (
    <ActionsCtx value={actions}>
      <StateCtx value={state}>{children}</StateCtx>
    </ActionsCtx>
  );
}
export const useCartState   = () => use(StateCtx)!;
export const useCartActions = () => use(ActionsCtx)!;
```

A component using only `useCartActions` no longer re-renders on every state change.

## Zustand — when Context isn't enough

The right choice when a store must be reachable across non-overlapping trees, many components subscribe to specific slices (selector-based subscriptions), or you want `persist`/`devtools` middleware without Redux ceremony:

```tsx
// src/stores/cart.ts
import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';

type CartState = {
  items: CartItem[];
  add: (item: CartItem) => void;
  remove: (id: string) => void;
  totalMinor: () => number;
};

export const useCart = create<CartState>()(
  devtools(persist((set, get) => ({
    items: [],
    add:    (item) => set({ items: [...get().items, item] }, false, 'cart/add'),
    remove: (id)   => set({ items: get().items.filter(i => i.id !== id) }, false, 'cart/remove'),
    totalMinor: () => get().items.reduce((s, i) => s + i.priceMinor * i.qty, 0),
  }), { name: 'cart' })),
);

// Selector-based subscription — re-renders only when items.length changes
function CartBadge() {
  const count = useCart(s => s.items.length);
  return <span>{count}</span>;
}
```

**App Router caveat:** a module-level store is shared process-wide on the server, which leaks state between requests. Create per-request stores via a provider (the `createStore` + Context pattern) for anything that renders on the server, or keep the store strictly inside `'use client'` components that only run in the browser. Never read/write a global store during a Server Component render.

## Redux Toolkit — when the team's already on it

RTK is fine; the modern setup (`createSlice`, `createAsyncThunk`, RTK Query) removes classic-Redux ceremony. **RTK Query** handles server state inside Redux — reasonable when the team wants one store. For new projects without Redux, **TanStack Query + Zustand** is lighter and tends to win.

```tsx
const cartSlice = createSlice({
  name: 'cart',
  initialState: { items: [] as CartItem[] },
  reducers: {
    added(state, a: PayloadAction<CartItem>) { state.items.push(a.payload); },
    removed(state, a: PayloadAction<string>)  { state.items = state.items.filter(i => i.id !== a.payload); },
  },
});
export const { added, removed } = cartSlice.actions;
```

## Jotai — atomic state

Atom-based primitives for fine-grained reactive UI (complex calculators, canvas tools). Niche — don't introduce without a measured need.

## Persisting state

| Where | Use case |
|---|---|
| **memory (`useState`/store)** | default — survives a render, not a reload |
| **`sessionStorage`** | per-tab, cleared on close (in-progress wizard step) |
| **`localStorage`** | cross-tab, persistent (theme, recently-viewed) — wrap in a `useLocalStorage` hook, never touch in render (hydration) |
| **URL search params** | shareable/deep-linkable state (filter, page, tab) |
| **Cookie** | server-readable (auth/session — see `auth/auth0-react`) |

### Storage can fail — degrade, never crash

`localStorage` is not a reliable dependency. It **throws** on quota exceeded (`QuotaExceededError`), in Safari private mode, and where the browser blocks storage for embedded/third-party contexts; IndexedDB can be blocked outright. Every one of those throws is a *write* — which means a Zustand `persist` store, a persisted TanStack Query cache, or a `useLocalStorage` hook can take down a render that had nothing to do with persistence.

- **Route all storage access through one guarded wrapper** (`try/catch` on read, write, *and* `JSON.parse`) that **falls back to in-memory** and logs once. Persistence is an optimization; losing it degrades the session, it must never break it.
- **A parse failure is a corrupt entry** — discard the key and continue with defaults, rather than throwing on every subsequent read.
- **Don't persist what you can't afford to lose or leak.** No tokens, no PII, no server data (that's the query cache's job). Prune what you do persist — an unbounded "recently viewed" list is how you hit quota in the first place.
- **Storage is shared across tabs** — see multi-tab below.

### Multi-tab coordination

Two tabs of one app are two copies of your client state with one shared origin. The failure is silent divergence: a user signs out in tab A and tab B keeps rendering as signed-in; tab A refreshes the token and tab B holds a dead one; both write the same persisted key and last-writer-wins.

Broadcast the transitions that matter — `BroadcastChannel` (or the `storage` event as the fallback) for **auth state changes, logout, and "your session ended"** — so sibling tabs re-render or show the re-auth affordance rather than failing on the next call ([`error-handling`](../error-handling/SKILL.md) session ladder; `auth/auth0-react` owns the token side). Cross-tab sync for ordinary UI state is usually *not* wanted — two tabs are allowed to show different filters. Sync identity and session; leave view state alone.

**URL state is underused.** Encode filters/pagination/selected-tab in the URL so pages are shareable and the back button works:

```tsx
'use client';
import { useRouter, useSearchParams, usePathname } from 'next/navigation'; // App Router
// SPA lane: useSearchParams from react-router-dom
const params = useSearchParams();
const page = Number(params.get('page') ?? 1);
```

On the App Router, URL state also lets a **Server Component** read `searchParams` and render the filtered result server-side — no client store needed.

## Next.js App Router specifics

- **Server Components fetch and pass props** — minimize client state in the server tree; a value that can be a server-computed prop shouldn't become client state.
- **`'use client'` boundaries are where stores and Context providers live** — mount providers in a small client component included from the root `layout.tsx`, not by making the layout itself client.
- **Server Actions + `revalidate`** replace "fetch, then invalidate a client cache" for mutations — often eliminating client-side TanStack Query on that route.
- The picture for new App Router apps: **RSC + Server Actions for the bulk of data, client stores only for genuine client state.**

## Common anti-patterns

- **Server data in a global store.** Use TanStack Query / RSC / Server Actions.
- **Context with everything.** Split by concern or move to a real store.
- **Mutating state directly** (`state.items.push(x)`). Outside Immer/RTK, breaks React's change detection.
- **`useEffect` syncing two states.** Almost always one should be derived.
- **Form state in a global store.** Forms have their own library ([`forms`](../forms/SKILL.md)).
- **A module-level Zustand store read during a Server Component render.** Per-request leak — use a provider-scoped store.
- **Client state that's really URL state.** Filters/pagination belong in `searchParams`.

## Rules

- **Server state** → TanStack Query / RSC / Server Actions; never Redux / Zustand / Context.
- **Client state**: local first, lift second, Context for cross-cutting, Zustand when Context isn't enough.
- **URL-derivable state lives in the URL.**
- **One store / one Context per concern** — no god stores.
- **Selectors** for store subscriptions; **memoize** Context values; **split** read/write Contexts under write churn.
- **Persist deliberately** — pick the right storage; wrap `localStorage` in a hook, and route every access through a **guarded wrapper that degrades to in-memory** (quota/private-mode/blocked-context throws must never break a render); discard corrupt entries; persist no tokens, PII, or server data; prune what grows.
- **Broadcast session/auth transitions across tabs** (`BroadcastChannel`/`storage`) so a logout or refresh in one tab doesn't leave a sibling live; don't sync ordinary view state.
- **App Router**: providers/stores behind `'use client'`; per-request store scope for server-rendered trees.
- **Devtools** middleware on stores in development.

## What NOT to do

- No server data in client global stores.
- No 6-level prop drilling — extract Context or compose.
- No giant `AppContext` carrying user + theme + cart + flags.
- No `useEffect` syncing two states that could be one derived value.
- No mutation of immutable state outside Immer / RTK.
- No unguarded `localStorage`/`sessionStorage`/IndexedDB access (it throws — quota, private mode, blocked context) and no unguarded `JSON.parse` of what comes back; no token/PII/server data persisted; no unbounded persisted list.
- No app that keeps rendering as signed-in in one tab after a logout in another.
- No `localStorage` in render (hydration mismatch) — wrap in a hook read in an effect.
- No Redux setup for a new small app — Zustand + TanStack Query is the modern default.
- No `useReducer` for a single boolean; no `'use client'` on a whole route just because one leaf needs a store.

## Generation steps

1. Confirm the kind of state (server / URL / UI / session / form) and sharing scope.
2. Walk the decision tree; recommend the lightest fit.
3. Server state → RSC fetch + Server Action, or a TanStack Query hook per resource ([`data-fetching`](../data-fetching/SKILL.md)).
4. UI state → `useState`/`useReducer`, or Context if shared; app-wide client state → a Zustand store with selectors (+ per-request scope on the App Router).
5. Move URL-derivable state into `searchParams`.
6. Sweep prop-drilling chains the new Context/store replaces; remove dead props.
7. Confirm types are tight (no `any`); add `satisfies` where useful.

## Handoffs

- Component scaffolding using the new state → [`component-writer`](../component-writer/SKILL.md)
- Form state → [`forms`](../forms/SKILL.md)
- Data-fetching mechanics (RSC fetch, Server Actions, TanStack Query setup, streaming) → [`data-fetching`](../data-fetching/SKILL.md)
- Conceptual lookup (Context vs store, hooks) → [`basics`](../basics/SKILL.md)
- Auth-driven state (current user) → `auth/auth0-react`
- Blazor equivalent → `frontend/blazor/skills/state-management`
