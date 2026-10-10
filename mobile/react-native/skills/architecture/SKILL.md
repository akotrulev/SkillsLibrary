---
name: mobile-react-native-architecture
description: Use when picking or setting up state management in a React Native + Expo app (React 19 + TypeScript strict) — local state, lifted state, Context + reducer, Zustand, TanStack Query, and the server-vs-client-state split. Covers the RN deltas: no RSC/Server Actions, no URL-as-state (navigation params + a store take its place), AsyncStorage/MMKV persistence instead of web storage, and the derived-state / dispatch-updater / fallback-state discipline. Triggers "what state library here", "Zustand vs Context", "server state vs client state", "I'm prop-drilling everywhere", "persist this across app restarts", "share state across screens". Do NOT use for component scaffolding (use `mobile/react-native/skills/generator`), forms (use `mobile/react-native/skills/forms`), data-fetching mechanics (use `mobile/react-native/skills/data-access`), offline sync/queues (use `mobile/react-native/skills/offline-first`), navigation params as routing (use `mobile/react-native/skills/navigation`), or React web (use `frontend/react/skills/state-management`).
---

# React Native — State Management

Picks the right state primitive for the job. House style: **local first, lift only when shared, Context for cross-cutting non-frequent client state, TanStack Query for server state, Zustand for global client state when Context isn't enough.** React 19 + TypeScript strict, on-device. There is **no RSC, no Server Actions, and no URL** — so the web stack's "fetch in a Server Component / put it in `searchParams`" answers don't exist here; the equivalents are navigation params and a client store.

## Version applicability

Detect the Expo SDK / RN / React majors first (`package.json`, `app.json`). React 19 (SDK 53+) is primary: `use()` + Suspense, `useOptimistic`, `ref` as a plain prop. On an SDK ≤52 (React 18) project the classic equivalents are correct — don't flag them. Zustand v5, TanStack Query v5 are the current lines; both are runtime-agnostic and behave identically across the supported SDKs.

## When to use

- A feature needs to share state across components or screens
- Existing code prop-drills more than ~2 levels
- Choosing between Context, Zustand, and TanStack Query
- Separating **server state** (what the API knows) from **client state** (UI-only)
- Persisting state across app restarts

## When NOT to use

- New component scaffolding → [`generator`](../generator/SKILL.md)
- Form state specifically → [`forms`](../forms/SKILL.md)
- Data-fetching mechanics (fetch, cancellation, `AppState` refetch) → [`data-access`](../data-access/SKILL.md)
- Offline persistence queue / optimistic mutation sync → [`offline-first`](../offline-first/SKILL.md)
- Route params as the routing mechanism → [`navigation`](../navigation/SKILL.md)
- Conceptual lookup (no server render, thread model) → [`basics`](../basics/SKILL.md)
- React web → `frontend/react/skills/state-management`

## Inputs needed

1. **What kind of state**: server data (fetched), UI state (toggles, modals, focus), session state (current user, theme), form state, route-scoped state
2. **Sharing scope**: one component, one screen, one feature, app-wide
3. **Mutation pattern**: rarely changed, edited frequently, optimistic updates needed
4. **Persistence**: in-memory, `AsyncStorage`, `MMKV`, `expo-secure-store` (sensitive)

## Decision tree

```
Is this server data (fetched from an API / DB)?
  ├─ yes → TanStack Query — the cache IS your server-state store.
  │        Never copy server data into Zustand/Context (see below).
  └─ no  ↓
Is it scoped to one screen and passed on navigation (selected id, filter, mode)?
  ├─ yes → navigation params (typed route params) — the RN analog of URL state.
  │        → navigation skill. Don't lift screen-local selection into a global store.
  └─ no  ↓
Is the state used by only one component?
  ├─ yes → useState / useReducer in that component
  └─ no  ↓
Is it a parent + a few children (≤2 levels)?
  ├─ yes → lift to the parent + prop passing
  └─ no  ↓
Is it cross-cutting (theme, current user, feature flags), read widely, written rarely?
  ├─ yes → React Context + a consumer hook
  └─ no  ↓
Changed frequently or by many disconnected components/screens?
  ├─ yes → Zustand (selector subscriptions)
  └─ no  → Context is still fine
```

## Server state vs client state — the #1 lesson

```
Server state           Client state
─────────────────────  ──────────────────────────
Lives in the API/DB    Lives on the device
Async                  Sync
Shared with others     Single user
Stale unless refreshed Always current
Needs caching          Doesn't need caching
```

**Don't store server data in Zustand / Context.** That re-invents caching, refetch, invalidation, and optimistic updates — and loses against the tool built for it. The *first* answer for server state is **TanStack Query**: one query key per resource; [`data-access`](../data-access/SKILL.md) owns the fetch mechanics (cancellation, `AppState`-aware refetch, ProblemDetails→UI), this skill owns *which bucket the state belongs in*. Persist the query cache for offline via [`offline-first`](../offline-first/SKILL.md), not by hand-copying rows into a store.

```tsx
// ✅ Server state via TanStack Query
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

export function useOrders(customerId: string) {
  return useQuery({
    queryKey: ['orders', customerId],
    queryFn: ({ signal }) => api.get(`/orders?customerId=${customerId}`, { signal }),
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
// ✅ Client state — never server data
const [isSheetOpen, setSheetOpen] = useState(false);
```

## useState / useReducer — and the derived-state discipline

`useState` for one or two scalars; `useReducer` when state has multiple related fields with non-trivial transitions.

**State is the minimal ground truth; everything else is derived.** This is the most common RN state bug — mirroring a computed value into a second `useState` kept in sync with `useEffect`. Compute it during render instead. (Applies to Reanimated shared values too: store `pressed`, derive `scale` — see `../../vendor/react-native-guidelines/rules/state-ground-truth.md` and `.../rules/react-state-minimize.md`.)

```tsx
// ❌ redundant state synced by an effect
const [items, setItems] = useState<Item[]>([]);
const [total, setTotal] = useState(0);
useEffect(() => setTotal(items.reduce((s, i) => s + i.price, 0)), [items]);

// ✅ derive during render
const [items, setItems] = useState<Item[]>([]);
const total = items.reduce((s, i) => s + i.price, 0);
```

**Two more native-flavored rules from the seed:**

- **Dispatch updaters when next state depends on current state** — `setCount(prev => prev + 1)`, never `setCount(count + 1)` (stale-closure safe; a callback firing off an `onLayout`/gesture reads a stale `count` otherwise). → `.../rules/react-state-dispatcher.md`
- **Fallback state, not synced `initialState`** — for a value that starts from a prop/server default but the user can override, initialize `undefined` and coalesce: `const value = _value ?? fallback`. `undefined` means "user hasn't chosen"; the fallback stays reactive if the source changes, without an effect to re-sync. → `.../rules/react-state-fallback.md`

## Context — for cross-cutting client state

Read by many components, written rarely (theme, current user, locale, feature flags), app- or feature-wide. No `'use client'` wrapper needed — everything is a client component on device.

```tsx
import { createContext, use, useMemo, useState, type ReactNode } from 'react';

type AuthValue = { user: User | null; setUser: (u: User | null) => void };
const AuthContext = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const value = useMemo<AuthValue>(() => ({ user, setUser }), [user]);
  return <AuthContext value={value}>{children}</AuthContext>; // React 19 provider shorthand
}

export function useAuth() {
  const ctx = use(AuthContext);              // React 19 use(); React 18: useContext
  if (!ctx) throw new Error('useAuth must be used within <AuthProvider>');
  return ctx;
}
```

Rules: **memoize the value**, **throw on use-outside-provider**, and **split read/write** if a frequently-changing value would re-render consumers that only call actions. Mount providers once, high in the tree — in Expo Router that's the root `app/_layout.tsx`.

### Split read/write contexts

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

A component using only `useCartActions` no longer re-renders on every state change — matters more in RN, where a stray re-render of a list item costs a dropped frame.

## Zustand — when Context isn't enough

The right choice when a store must be reachable across non-overlapping screens, many components subscribe to specific slices, or you want `persist`/`devtools` without ceremony. **No SSR/per-request-leak caveat here** (the web stack's biggest Zustand gotcha) — the app is a single on-device process, so a module-level store is fine.

```tsx
// src/stores/cart.ts
import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import AsyncStorage from '@react-native-async-storage/async-storage';

type CartState = {
  items: CartItem[];
  add: (item: CartItem) => void;
  remove: (id: string) => void;
  totalMinor: () => number;
};

export const useCart = create<CartState>()(
  persist((set, get) => ({
    items: [],
    add:    (item) => set((s) => ({ items: [...s.items, item] })),
    remove: (id)   => set((s) => ({ items: s.items.filter(i => i.id !== id) })),
    totalMinor: () => get().items.reduce((sum, i) => sum + i.priceMinor * i.qty, 0),
  }), { name: 'cart', storage: createJSONStorage(() => AsyncStorage) }),
);

// Selector subscription — re-renders only when items.length changes
function CartBadge() {
  const count = useCart(s => s.items.length);
  return <Text>{count}</Text>;
}
```

**Persistence storage:** wire `persist` to `AsyncStorage` (default, async) or **MMKV** (`react-native-mmkv` — synchronous, faster, the go-to for large or hot state). Sensitive values (tokens, PII) go to `expo-secure-store`, never a plain store. The offline mutation queue (optimistic writes replayed on reconnect) is [`offline-first`](../offline-first/SKILL.md)'s job, not a raw persisted store.

## Persisting state

| Where | Use case |
|---|---|
| **memory (`useState`/store)** | default — survives renders, not an app restart |
| **`AsyncStorage`** | simple persisted client state (theme, onboarding-seen); async KV |
| **`react-native-mmkv`** | fast synchronous persistence, large/hot state, Zustand `persist` backend |
| **`expo-secure-store`** | tokens / PII (Keychain / Keystore-backed) — never a plain store |
| **navigation params** | screen-scoped selection passed on navigate (the URL-state analog) |
| **TanStack Query cache (persisted)** | server data offline — via `offline-first`, not hand-copied |

**There is no URL.** Web's "encode filters/selected-tab in `searchParams`" becomes: pass it as a **typed navigation param** when it's screen-scoped, or a store when it's app-wide. → [`navigation`](../navigation/SKILL.md).

## Common anti-patterns

- **Server data in a global store.** Use TanStack Query.
- **Context with everything.** Split by concern or move to a store.
- **`useEffect` syncing two states.** One should be derived.
- **Reading state directly in a gesture/`onLayout` callback.** Use a dispatch updater (stale closure).
- **Synced `initialState` from a prop.** Use `undefined` + `??` fallback.
- **Form state in a global store.** Forms have their own library ([`forms`](../forms/SKILL.md)).
- **Screen-local selection lifted app-wide.** Pass it as a navigation param.
- **Tokens in a plain persisted store.** `expo-secure-store`.

## Rules

- **Server state** → TanStack Query; never Zustand / Context.
- **Client state**: local first, lift second, Context for cross-cutting, Zustand when Context isn't enough.
- **Screen-scoped state travels as a navigation param**, not a global store.
- **State is minimal ground truth** — derive everything else in render; no effect-synced mirror state.
- **Dispatch updaters** when next state depends on current; **fallback state** (`undefined` + `??`) over synced `initialState`.
- **One store / one Context per concern** — no god stores; **selectors** for store subscriptions; **memoize** Context values; **split** read/write under write churn.
- **Persist deliberately**: `AsyncStorage`/`MMKV` for client state, `expo-secure-store` for secrets, the Query cache (via `offline-first`) for server data.

## What NOT to do

- No server data in client global stores.
- No 6-level prop drilling — extract Context or compose.
- No giant `AppStore` carrying user + theme + cart + flags.
- No `useEffect` syncing two states that could be one derived value.
- No `useReducer` for a single boolean.
- No secrets in a plain `AsyncStorage`-backed store.
- No re-implementing an offline mutation queue in a raw store — that's `offline-first`.

## Generation steps

1. Confirm the kind of state (server / navigation-scoped / UI / session / form) and sharing scope.
2. Walk the decision tree; recommend the lightest fit.
3. Server state → a TanStack Query hook per resource ([`data-access`](../data-access/SKILL.md)).
4. UI state → `useState`/`useReducer` (derive, don't mirror); shared → Context; app-wide client state → a Zustand store with selectors.
5. Move screen-scoped selection into navigation params ([`navigation`](../navigation/SKILL.md)).
6. Wire persistence deliberately (AsyncStorage/MMKV/SecureStore); sweep prop-drilling chains the new Context/store replaces.
7. Confirm types are tight (no `any`).

## Handoffs

- Component scaffolding using the new state → [`generator`](../generator/SKILL.md)
- Form state → [`forms`](../forms/SKILL.md)
- Data-fetching mechanics (fetch, cancellation, `AppState` refetch) → [`data-access`](../data-access/SKILL.md)
- Query-cache persistence, optimistic mutation queue → [`offline-first`](../offline-first/SKILL.md)
- Navigation params as screen-scoped state → [`navigation`](../navigation/SKILL.md)
- Conceptual lookup (no server render, thread model) → [`basics`](../basics/SKILL.md)
- Auth-driven state (current user) → `auth/auth0-react`
- React web equivalent → `frontend/react/skills/state-management`
