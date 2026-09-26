---
name: fe-react-performance
description: Use when the UI is slow, janky, or heavy — render throughput (`key`, derive-don't-effect, memo/Compiler, split contexts), bundle & startup (push `'use client'` to leaves, code-split, import costs), server render (parallel fetches, streaming), Core-Web-Vitals budgets. Triggers "this list re-renders too much", "the bundle is huge", "typing lags", "my fetches waterfall", "Maximum update depth exceeded". Not for CSS/layout (`styling`, `responsive-design`) or load testing (a qa peer).
---

# React — Performance

Owns making a React app fast and keeping it fast across four cost centers that behave differently on the App Router: **render throughput** (how often and how cheaply components re-render), **bundle & startup** (how much JS ships and when it hydrates), **server render** (how the RSC tree fetches and streams), and the **concurrency** features that keep input responsive under load. Plus the **diagnostics** to measure them and the **budgets** to hold the line.

The **primary source** for the concrete recipes is the Vercel React/Next performance ruleset vendored at `frontend/react/vendor/reference/rules/` (the `rerender-*`, `bundle-*`, `server-*`, `async-*`, `js-*`, `client-*` families) — this skill is the curated, house-style entry point to it; reach into a specific rule file for the deep example.

**Version rule:** detect the React/Next major first (`package.json`). `key`, derive-don't-effect, `useDeferredValue`/`useTransition`, `next/dynamic`, and parallel fetching behave the same across 18/19. The **React 19** delta is the **React Compiler** — with it on (default in new Next 15 apps), most `useMemo`/`useCallback`/`React.memo` is automatic; you add them by hand only where the compiler can't prove safety. On **React 18** memoization is manual. Never assume the Compiler is on without checking `next.config` / the babel plugin. The Vite SPA lane has no RSC — the bundle/startup levers still apply; the server-render section doesn't.

## When to use

- A component (or a list row) re-renders more than it should; a parent update repaints a whole subtree
- The JS bundle is large; TTI/INP is slow; hydration is heavy
- Typing/scrolling janks while an expensive derived render runs
- Deciding what to code-split (`next/dynamic`/`lazy`) and where the `'use client'` boundary belongs *for bundle size*
- Server fetches waterfall instead of running in parallel; a slow section blocks first paint
- Wiring perf diagnostics (Profiler, web-vitals, bundle analyzer) and setting Core-Web-Vitals budgets

## When NOT to use

- CSS / layout / asset styling → [`styling`](../styling/SKILL.md), [`responsive-design`](../responsive-design/SKILL.md)
- Live/server-pushed data as a *feature* → [`realtime`](../realtime/SKILL.md)
- Fetch/cache *correctness* (revalidate, dedup, `cache`) → [`data-fetching`](../data-fetching/SKILL.md) (this skill owns the *shape* of fetching for speed; that skill owns caching semantics)
- Server-side query/DB tuning → `data/*`
- Load/stress/soak of the deployed app → `qa/typescript/skills/load-testing` (peer)
- Deep conceptual "why does this re-render/hydrate" → [`basics`](../basics/SKILL.md)

## Cost-center routing — where is my slowness?

```
Is the JS bundle big / first paint / TTI slow?
  YES → bundle & startup   → §"Bundle & startup"
Is the app interactive but a specific interaction / typing / scroll janks?
  YES → render throughput  → §"Render throughput"  (+ §"Concurrency")
Is the server response itself slow (fetches waterfall, section blocks paint)?
  YES → server render      → §"Server render"
Don't know which?        → wire the diagnostics first → §"Diagnostics"
```

| Symptom | Cost center | Section |
|---|---|---|
| "Big bundle, slow TTI, spinner for seconds" | JS shipped | Bundle & startup |
| "Clicking a row re-renders the whole page" | render throughput | Render throughput |
| "Typing in the filter lags the list" | render + concurrency | Render throughput / Concurrency |
| "10k-row grid freezes the tab" | render throughput | Render throughput (virtualize) |
| "The page waits on a slow API before anything shows" | server render | Server render (parallel + Suspense) |
| "Every leaf is `'use client'` and the bundle ballooned" | bundle | Bundle & startup (RSC boundary) |

---

## Render throughput

React re-renders a component when its state changes, its parent re-renders, or a Context it consumes changes. The cost is the **render + diff**, not the paint — a cheap component rendered 1000×/sec still burns the main thread. Levers, in order of leverage:

### Keys — stable identity in lists

Every item in a rendered list gets a **stable domain-id `key`** (`order.id`), never the array index. An index key makes React match old→new by position, so inserting/reordering corrupts child state, focus, and inputs and forces needless remounts ([`basics`](../basics/SKILL.md), [`test-ids`](../test-ids/SKILL.md) share this rule). Key on the entity id.

### Derive during render — don't store derived state in an effect

The single most common needless-render bug: a `useState` + `useEffect` that recomputes a value from props/state. It renders once with the stale value, then the effect fires and renders **again**. Derive during render instead:

```tsx
// ✗ two renders + state drift
const [fullName, setFullName] = useState('');
useEffect(() => setFullName(`${first} ${last}`), [first, last]);

// ✓ one render, no drift
const fullName = `${first} ${last}`;
```

Never `setState` in an effect purely to react to a prop change — derive it, or reset with a `key` remount. (`rerender-derived-state-no-effect`; also a [`component-writer`](../component-writer/SKILL.md) rule.)

### Memoization — Compiler first, then by hand

- **React 19 + Compiler on:** most `useMemo`/`useCallback`/`React.memo` is inserted automatically — don't scatter them. Add manual memo only where the Compiler can't prove safety (a value handed to a non-React API, a measured hot path).
- **React 18 / Compiler off:** `React.memo` a pure child that re-renders under an unchanged-props parent; `useMemo` an expensive computation; `useCallback` a callback passed to a memoized child. Memo only pays when the memoized value is **actually consumed** by something that skips work — a `useMemo` whose result feeds a non-memoized child is pure cost.
- **Never allocate a fresh object/array/lambda inline** for a prop consumed by a memoized child or a Context value — it defeats the memo every render (hoist it, `useMemo` it, or `useCallback` it). Context `value=` is always `useMemo`'d ([`basics`](../basics/SKILL.md)).

### Don't define components inside components

A component declared inside another's body is a **new type every render** — React unmounts and remounts the whole subtree each time, destroying its state. Hoist it to module scope (or pass it as a prop). (`rerender-no-inline-components`.)

### Split Contexts and combined hooks

A Context re-renders **every** consumer when its value changes. Split a read Context from a write Context so components that only dispatch don't re-render on data churn ([`state-management`](../state-management/SKILL.md), [`basics`](../basics/SKILL.md)). Likewise, split a combined `useState` object when unrelated fields update independently (`rerender-split-combined-hooks`), and use **functional `setState`** (`setX(x => …)`) to drop a dependency and avoid stale closures.

### Large lists — virtualize

Past ~100 rows, render only the viewport with `@tanstack/react-virtual` (or `react-window`). Pair with server-side paging ([`ui-rules`](../ui-rules/SKILL.md) table ergonomics) for large/remote sets — don't ship 10k rows to the client to then virtualize.

### Render anti-patterns

| Anti-pattern | Cost | Fix |
|---|---|---|
| `key={index}` on a mutable list | remount + state/focus corruption on reorder | `key` on the entity id |
| `useState`+`useEffect` deriving a value | double render + drift | derive during render |
| Component defined inside a component | full remount every render | hoist to module scope |
| Fresh `{}`/`[]`/`() =>` prop to a memoized child | memo defeated every render | hoist / `useMemo` / `useCallback` |
| One Context for data **and** dispatch | every consumer re-renders on data change | split read/write Contexts |
| Un-virtualized 10k-row list | whole set rendered + diffed | virtualize + server paging |
| `useMemo`/`useCallback` everywhere "for perf" | allocation + dep-check cost, no benefit | memo only where a consumer skips work |

---

## Concurrency — keep input responsive

When user input triggers an expensive render, use React's concurrent features so the input stays snappy while the heavy work runs at lower priority:

- **`useDeferredValue`** — filtering/searching a large list, or an expensive chart reacting to a field. Defer the value, `useMemo` the expensive derivation on the *deferred* value (without the memo it still runs every render), and dim the stale result:

  ```tsx
  const deferred = useDeferredValue(query);
  const results = useMemo(() => filterBig(items, deferred), [items, deferred]);
  const isStale = query !== deferred;   // opacity cue while catching up
  ```

- **`useTransition` / `startTransition`** — wrap a frequent, non-urgent state update (scroll position, tab switch that renders a heavy panel) so it doesn't block the urgent input update. `isPending` drives a subtle loading cue.

(`rerender-use-deferred-value`, `rerender-transitions`.) These are React-18+; on the App Router, navigation and Server-Action updates are already transitions.

---

## Bundle & startup

The startup cost is JS **downloaded, parsed, and hydrated** before interactivity. Levers, in order of leverage:

### 1. RSC ships no JS — push `'use client'` to the leaves

The biggest lever on the App Router: a **Server Component ships zero JS to the browser**. Every leaf you leave as a Server Component is bundle you don't pay for. The classic regression is defensive `'use client'` creeping up the tree until the whole route hydrates — mark the directive on the **smallest interactive leaf**, pass server-rendered output through client shells as `children`, and keep static content server-side ([`basics`](../basics/SKILL.md) owns the boundary model; this is its *bundle* consequence). This is the App-Router analog of Blazor's "static SSR default, interactivity per island."

### 2. Code-split heavy, non-critical components

Lazy-load anything large that isn't needed for first paint (a rich editor, a charting lib, a modal's body):

```tsx
// App Router / Next
const MonacoEditor = dynamic(() => import('./monaco-editor').then(m => m.MonacoEditor), { ssr: false });
// Vite / plain React
const Reports = lazy(() => import('./Reports'));   // render inside <Suspense fallback={…}>
```

Use `ssr: false` for genuinely client-only widgets so they never prerender. (`bundle-dynamic-imports`.) Best for large, rarely-hit areas (admin, reporting, editors).

### 3. Watch import cost — barrels and third-party

- **Barrel-file imports** (`import { Icon } from '@acme/ui'`) can pull the whole package into the chunk when tree-shaking can't prune it — import from the deep path, or configure `optimizePackageImports` (Next). (`bundle-barrel-imports`.)
- **Defer heavy third-party scripts** (analytics, chat widgets) with `next/script` `strategy="lazyOnload"`/`afterInteractive` — never render-blocking. (`bundle-defer-third-party`.)
- Prefer smaller deps (`date-fns`/`Intl` over moment; a 3-line util over a lib) and run the analyzer (below) before adding a big one.

### 4. Preload / prefetch the critical path

`next/link` prefetches in-viewport routes automatically. For a known next step, `router.prefetch` or `<link rel="preload">` the critical asset (`bundle-preload`, `rendering-resource-hints`). Don't preload everything — it competes with the critical path.

### 5. Avoid the hydration double-cost

Reading `window`/`Date.now()`/`localStorage` in render causes a hydration mismatch → React throws away the server HTML and re-renders ([`basics`](../basics/SKILL.md) hydration trap). Keep those in effects. A mismatch is a correctness *and* a performance bug.

---

## Server render (App Router)

The RSC tree's own render time is a cost center. Two rules dominate:

### Parallel, not waterfall, fetches

Sequential `await`s in one Server Component (or a parent that awaits before rendering a child that also fetches) create a **request waterfall** — total latency is the sum, not the max. Kick off independent fetches together:

```tsx
// ✗ waterfall: user then orders
const user = await getUser(id);
const orders = await getOrders(id);
// ✓ parallel: both in flight at once
const [user, orders] = await Promise.all([getUser(id), getOrders(id)]);
```

For independent sections, prefer **separate Suspense boundaries** over one big `await` so each streams in when ready. (`server-parallel-fetching`, `server-parallel-nested-fetching`.)

### Stream with strategic Suspense boundaries

Don't block the whole page on the slowest section. Return the shell immediately and wrap each slow region in `<Suspense fallback={<Skeleton/>}>` so it streams into the same response — the wrapper (sidebar, header, nav) paints first ([`data-fetching`](../data-fetching/SKILL.md) owns the fetch mechanics; this owns *where the boundaries go* for speed). The skeleton **approximates the final layout** (height/columns) so there's no layout shift (a generic spinner shifts — hurts CLS). (`async-suspense-boundaries`.) Keep server-side work off the request path where possible (`after()` for non-blocking post-response work — `server-after-nonblocking`).

---

## Diagnostics

Measure before optimizing. Layers:

| Tool | Watches |
|---|---|
| **React DevTools Profiler** | render counts + durations per commit; "why did this render" (highlight updates) |
| **`web-vitals`** (`onLCP`/`onINP`/`onCLS`) | real Core Web Vitals; report to your analytics/OTel |
| **Next bundle analyzer** (`@next/bundle-analyzer`) | per-route/per-chunk JS size; find the bloat |
| **Lighthouse / Lighthouse CI** | LCP/TBT/CLS/TTI scores on a throttled profile |
| **`why-did-you-render`** (dev only) | flags avoidable re-renders during development |

Feed `web-vitals` into the observability stack (`observability/opentelemetry-node`, external). On the App Router, `useReportWebVitals` reports field metrics.

---

## Budgets

Set explicit budgets and fail CI when they regress — an unmeasured perf rule rots. Suggested starting budgets (tune per app):

| Metric | Budget (starting point) | Where enforced |
|---|---|---|
| LCP | ≤ 2.5 s (mid-tier / throttled) | Lighthouse CI |
| INP | ≤ 200 ms | Lighthouse CI + `web-vitals` field data |
| CLS | ≤ 0.1 | Lighthouse CI |
| Initial route JS (First Load JS) | ≤ ~130–170 KB gzipped per route | bundle analyzer check in CI |
| Largest list without virtualization | ≤ 100 rows | [`code-review`](../code-review/SKILL.md) rule |
| Re-renders on a key interaction | no unbounded growth per interaction | React DevTools Profiler |

---

## Rules

- **Stable domain-id `key`** in every list; never the array index.
- **Derive during render**; never `setState` in an effect to mirror props/state.
- **Compiler-first memoization** on React 19; manual `React.memo`/`useMemo`/`useCallback` only where a consumer actually skips work — never blanket. **No fresh inline object/array/lambda** for a memoized child or Context value.
- **Never define a component inside another** (new type → remount). Hoist to module scope.
- **Split read/write Contexts**; functional `setState` to drop deps.
- **Virtualize past ~100 rows** + server paging for large/remote sets.
- **`useDeferredValue`/`useTransition`** for expensive input-driven renders (memo the derivation on the deferred value).
- **RSC by default; `'use client'` on the smallest leaf** — bundle you don't ship is the cheapest win.
- **Code-split** heavy non-critical components (`next/dynamic`/`lazy`), `ssr:false` for client-only widgets; watch barrel + third-party import cost.
- **Parallel fetches** (`Promise.all`) and **per-section Suspense** on the server; layout-approximating skeletons (no CLS).
- **Wire diagnostics** (Profiler, `web-vitals`, bundle analyzer) and set **explicit Core-Web-Vitals + bundle budgets** enforced in CI.
- Measure first, optimize the proven hot path, measure again — never speculatively.

## What NOT to do

- No `key={index}` on a mutable list; no unstable keys.
- No `useEffect` deriving state that could be computed in render.
- No component defined inside a component; no fresh inline props defeating a memo.
- No `useMemo`/`useCallback`/`React.memo` sprinkled with no memoized consumer.
- No blanket `'use client'` on a route because one leaf is interactive — it ships the whole subtree.
- No render-blocking heavy import (editor/chart/analytics) that could be code-split or deferred.
- No sequential `await`s for independent data (waterfall); no single `await` blocking the whole page where a Suspense boundary fits.
- No generic spinner where a layout-approximating skeleton avoids CLS.
- No `window`/`Date.now()` in render (hydration mismatch = correctness + perf bug).
- No "we optimized it" without a before/after Profiler/Lighthouse measurement.

## Validation

Inside a `Gate: none` plan task, run none of these checks and report "written, not run"; the plan's gate task runs them.

- React DevTools Profiler: toggle a `memo`/`key`/Context-split fix off→on and confirm the render count drops on the target interaction.
- Bundle analyzer: initial First Load JS per route within budget; heavy widgets in their own async chunks; no barrel pulling a whole package.
- Network/Performance: independent server fetches run in parallel (overlapping in the waterfall), slow sections stream via Suspense, wrapper paints first.
- Typing in a filtered list stays responsive (deferred value); no long tasks in the Performance panel.
- Lighthouse CI: LCP/INP/CLS within budget on a throttled profile; `web-vitals` field data trends within budget.

## Handoffs

- Conceptual "why does this re-render / hydrate" → [`basics`](../basics/SKILL.md); the full Vercel rule files → `frontend/react/vendor/reference/rules/`
- CSS/layout/asset styling → [`styling`](../styling/SKILL.md); breakpoint/layout perf → [`responsive-design`](../responsive-design/SKILL.md)
- Fetch/cache correctness (revalidate, dedup, `cache`) → [`data-fetching`](../data-fetching/SKILL.md)
- Live-data as a feature (not perf) → [`realtime`](../realtime/SKILL.md)
- Server-side query/DB tuning → `data/*`
- `web-vitals`/OTel export to Grafana → `observability/opentelemetry-node`
- Load/stress/soak of the deployed app → `qa/typescript/skills/load-testing` (peer)
