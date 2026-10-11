---
name: architecture
description: Use when laying out or choosing state in an Expo SDK 57 app — feature-first folders, server state in TanStack Query 5, client state in Zustand 5 or Context, route params as state, React Compiler effects. Triggers "what state library", "Zustand vs Context", "I'm prop-drilling", "persist across restarts". Do NOT use for fetch mechanics (`mobile-react-native:networking`), forms (`-forms`), offline queues (`-offline-and-storage`) or route params (`-navigation`).
---

# React Native — Architecture and State

Picks the right place for each piece of state and the folder shape around it. House order: **local first, lift only when shared, Context for cross-cutting low-churn client state, TanStack Query for server state, Zustand when Context is not enough.** There is no RSC, no Server Action and no URL — route params and a store take their place.

## Version lane

| Concern | Primary (SDK 57 · React 19.2) | Notes |
|---|---|---|
| React Compiler | On in the default template | Do not add `useMemo` / `useCallback` for render cost; keep them for effect-dependency identity and Reanimated |
| TanStack Query | 5 | `focusManager` on `AppState`, `onlineManager` on NetInfo — mechanics in [`networking`](../networking/SKILL.md) |
| Zustand | 5 | Selector subscriptions; `persist` over MMKV |
| MMKV | 4 | `createMMKV()` (Nitro); synchronous |
| `[SDK58]` | React 19.3 | No architecture change; same rules |
| Floor SDK 54 | React 19.1 | Same recipes |

On a React 18 project the classic equivalents (`useContext`, `forwardRef`) are correct — do not flag them.

## When to use

- A feature must share state across components or screens
- Prop-drilling past ~2 levels
- Choosing Context vs Zustand vs TanStack Query
- Splitting server state from client state; persisting client state
- Deciding the feature-first folder layout

## When NOT to use

- Fetch, cancel, retry, token refresh → [`networking`](../networking/SKILL.md)
- Form state → [`forms`](../forms/SKILL.md)
- Offline cache persistence, mutation queue → [`offline-and-storage`](../offline-and-storage/SKILL.md)
- Route params as routing → [`navigation`](../navigation/SKILL.md)
- Concepts → [`basics`](../basics/SKILL.md)
- React web → `fe-react:state-management`

## Feature-first layout

```
src/features/orders/
  components/        organisms for this feature
  hooks/             useOrders, useCreateOrder
  api.ts             typed fetchers
  store.ts           only if client state is shared
src/lib/             api client, query client, env
src/app/orders/      thin route files that compose the feature
```

A feature imports from `lib` and from other features' public hooks, never their internals. Route files stay thin ([`project-setup`](../project-setup/SKILL.md)).

## Decision tree

```
Is it server data (fetched from an API)?
  yes -> TanStack Query. The cache is the server-state store.
  no  ->
Screen-scoped and passed on navigation (selected id, filter, mode)?
  yes -> typed route param (navigation skill)
  no  ->
One component only?               -> useState / useReducer
A parent and <= 2 levels below?   -> lift + props
Cross-cutting, read widely, written rarely (theme, user, flags)? -> Context
Frequent writes or many disconnected readers? -> Zustand
```

## Server state vs client state

| Server state | Client state |
|---|---|
| Lives in the API | Lives on the device |
| Async, shared, stale unless refreshed | Sync, single user, always current |
| Needs caching and invalidation | Does not |

**Never copy server data into Zustand or Context** — it re-invents caching, refetch and invalidation. One query key per resource:

```tsx
export function useOrders(customerId: string) {
  return useQuery({
    queryKey: ['orders', customerId],
    queryFn: ({ signal }) => api.get(`/orders?customerId=${customerId}`, { signal }),
    staleTime: 30_000,
  });
}

export function useCreateOrder() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (command: CreateOrder) => api.post('/orders', command),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['orders'] }),
  });
}
```

`signal` is forwarded so leaving the screen cancels the request. Persisting the cache for offline is [`offline-and-storage`](../offline-and-storage/SKILL.md)'s, not a hand-copied store.

## `useState` / `useReducer` and derived state

State is the minimal ground truth; everything else is computed in render. Mirroring a computed value into a second `useState` kept in sync by an effect is the most common RN state bug: `vendor/react-native-guidelines/rules/state-ground-truth.md`, `react-state-minimize.md`.

```tsx
const [items, setItems] = useState<Item[]>([]);
const total = items.reduce((sum, item) => sum + item.price, 0);
```

- **Dispatch updaters** when next state depends on current — `setCount((previous) => previous + 1)`; a gesture or `onLayout` callback otherwise reads a stale closure: `rules/react-state-dispatcher.md`.
- **Fallback state, not synced initial state** — initialise `undefined` and coalesce `value ?? fallback`: `rules/react-state-fallback.md`.
- Under the React Compiler, a plain computed value is already memoized; do not wrap it.

## Context — cross-cutting client state

```tsx
type AuthValue = { user: User | null; setUser: (user: User | null) => void };
const AuthContext = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  return <AuthContext value={{ user, setUser }}>{children}</AuthContext>;
}

export function useAuth() {
  const value = use(AuthContext);
  if (!value) throw new Error('useAuth must be used within <AuthProvider>');
  return value;
}
```

Throw on use-outside-provider; mount once at `src/app/_layout.tsx`. With the Compiler on, the provider value is memoized for you; on a project with the Compiler off, `useMemo` it. Split a **state context** from an **actions context** when writes are frequent, so action-only consumers do not re-render — a stray list-item re-render costs a frame.

## Zustand — when Context is not enough

Use when many non-overlapping screens read slices of the same client state. There is no per-request leak (single on-device process), so a module-level store is fine.

```tsx
import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';
import { createMMKV } from 'react-native-mmkv';

const storage = createMMKV({ id: 'cart' });
const mmkvStorage = createJSONStorage(() => ({
  getItem: (name) => storage.getString(name) ?? null,
  setItem: (name, value) => storage.set(name, value),
  removeItem: (name) => storage.remove(name),
}));

type CartState = { items: CartItem[]; add: (item: CartItem) => void; remove: (id: string) => void };

export const useCart = create<CartState>()(
  persist(
    (set) => ({
      items: [],
      add: (item) => set((state) => ({ items: [...state.items, item] })),
      remove: (id) => set((state) => ({ items: state.items.filter((item) => item.id !== id) })),
    }),
    { name: 'cart', storage: mmkvStorage },
  ),
);

const itemCount = useCart((state) => state.items.length);
```

Always subscribe with a selector. Tokens and PII never go through a plain persisted store.

## Where state persists

| Where | Use |
|---|---|
| memory | Default; gone on restart |
| MMKV 4 | Hot or large client state; Zustand `persist` backend |
| AsyncStorage | Legacy projects only; async |
| `expo-secure-store` | Tokens, PII (Keychain / Keystore) — never a plain store |
| typed route params | Screen-scoped selection |
| persisted Query cache | Server data offline — [`offline-and-storage`](../offline-and-storage/SKILL.md) |

## Dependency injection

Constructor-injection's RN form is **props, then context**: pass collaborators (an API client, a clock, a logger) as props to organisms and hooks, or provide them once from the root layout and read them through a throwing hook. No service locator, no module-level mutable singleton that tests cannot replace; the query client and API client are created in `src/lib` and provided at the root.

## Rules

- Server state → TanStack Query; never a store.
- Screen-scoped state is a typed route param.
- State is minimal ground truth; no effect-synced mirrors.
- One Context or store per concern; selectors on stores; throwing consumer hooks.
- Persist deliberately: MMKV for client state, `expo-secure-store` for secrets, the Query cache for server data.
- No manual memoization for render cost when the Compiler is on.

## What NOT to do

- No server data in Zustand or Context.
- No giant `AppStore`; no 6-level prop drilling.
- No `useEffect` syncing two states.
- No `useReducer` for a single boolean.
- No tokens in a plain persisted store.
- No hand-built offline mutation queue in a raw store.

## Handoffs

- Fetch mechanics → [`networking`](../networking/SKILL.md)
- Forms → [`forms`](../forms/SKILL.md)
- Offline and persistence → [`offline-and-storage`](../offline-and-storage/SKILL.md)
- Route params → [`navigation`](../navigation/SKILL.md)
- Performance of re-renders → [`performance`](../performance/SKILL.md)
- Auth state → `auth0-react-native`
