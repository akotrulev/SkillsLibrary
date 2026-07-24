---
name: fe-react-pwa-offline
description: Use when the app must be installable and/or work offline — manifest, service worker via Serwist (Next.js) or `vite-plugin-pwa`, precache vs runtime caching, the update lifecycle (a waiting worker needs skip-waiting), offline UX with queued writes, and that API/RSC data isn't cached by default. Triggers: "make this installable", "add offline support", "PWA won't update after deploy", "add to home screen". Do NOT use for server-side caching (`data-access`) or live-data reconnection (`realtime`).
---

# React — PWA & Offline

Owns making a React app **installable** (a PWA the OS treats like a native app) and **offline-capable** (it loads and runs with no network). These are two goals: a manifest gets you installable, a service worker gets you offline, and *real* offline for dynamic data takes more than the shell cache.

**Tooling.** On **Next.js (primary)** use **Serwist** (`@serwist/next`) — the actively-maintained successor to the abandoned `next-pwa`, built on Google's Workbox, and the approach the Next.js docs point to. On the **Vite SPA fallback** use **`vite-plugin-pwa`** (also Workbox-based). Both generate the service worker, inject a content-hashed **precache manifest**, and register it. Don't hand-write a service worker from scratch — you'll re-implement Workbox's cache-versioning and update lifecycle badly.

**Hard scope: what "offline" means depends on the render strategy.** A page that is **statically rendered** (SSG) or a **client-rendered SPA shell** can be precached and served offline. A page that is **dynamically server-rendered per request** (RSC that hits a DB/API on every load, `dynamic = 'force-dynamic'`, or Server Actions) **cannot run offline** — there's no server to render it. So an offline-capable app is built from static/client-rendered routes plus a client data cache; the parts that must be dynamic show an offline state, not a working page ([`project-scaffold`](../project-scaffold/SKILL.md) owns the per-route render-strategy call — the App Router analog of Blazor's "offline is WASM, not Server").

**Version rule.** The service-worker contract (precache manifest, cache-first, the update lifecycle) is a **browser/Workbox** concern — identical across React 18/19 and Next 14/15. Serwist replaces `next-pwa` specifically because `next-pwa` stalled on newer Next versions; on a brownfield project you may find `@ducanh2912/next-pwa` (a maintained fork) — prefer Serwist for new work. `manifest.ts` (typed, file-convention) is App-Router-native; a static `manifest.webmanifest` works everywhere.

## When to use

- Making the app installable (Add to Home Screen / install icon): manifest + icons
- Caching the app shell so it launches offline: the Serwist/vite-plugin-pwa service worker
- Fixing "my PWA won't update after I deploy" (the #1 PWA support ticket)
- Offline UX: detecting connectivity, an offline banner, deferring writes
- Deciding what offline actually requires for *data*, not just the app shell

## When NOT to use

- Server-side/distributed caching of API responses, RSC `fetch` cache, `revalidateTag` → [`data-access`](../data-access/SKILL.md) — that's server cache, not client offline
- Live/push data and its disconnect handling → [`realtime`](../realtime/SKILL.md)
- The failed/offline UI states themselves (three-state regions, retry) → [`error-resilience`](../error-resilience/SKILL.md) (this skill wires the SW; that skill owns the states)
- Bundle/startup budget the precache size depends on → [`performance`](../performance/SKILL.md)
- Icon/OG asset craft (sizes, maskable safe zones) → [`design/iconography`](../../../../design/iconography/SKILL.md)

## Installable: the web app manifest

On the App Router, prefer the typed **`app/manifest.ts`** file convention (Next generates `/manifest.webmanifest` and links it); on Vite, a static `public/manifest.webmanifest` linked from `index.html`. Installability needs a manifest, HTTPS, and a registered service worker.

```ts
// app/manifest.ts
import type { MetadataRoute } from 'next';
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: 'Contoso Field Ops',
    short_name: 'FieldOps',
    start_url: '/',
    display: 'standalone',
    background_color: '#ffffff',
    theme_color: '#0b5cff',
    icons: [
      { src: '/icon-192.png', sizes: '192x192', type: 'image/png' },
      { src: '/icon-512.png', sizes: '512x512', type: 'image/png' },
      { src: '/icon-512-maskable.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
    ],
  };
}
```

- Ship a **maskable** icon so Android doesn't letterbox your logo; `theme_color` should match your top bar (cross-check [`styling`](../styling/SKILL.md) tokens / dark mode).
- Icon/OG asset craft (sizes, safe zones) is [`design/iconography`](../../../../design/iconography/SKILL.md)'s domain — reuse it, don't re-derive. The manifest `theme_color` and the `<meta name="theme-color">` (from [`seo-discoverability`](../seo-discoverability/SKILL.md) metadata) should agree.

## Offline: the service worker (Serwist)

Serwist wires the SW at build time. Configure the plugin, write a tiny SW entry that consumes the injected precache manifest, and **disable it in development** (a caching SW in `next dev` serves stale everything):

```ts
// next.config.mjs
import withSerwistInit from '@serwist/next';
const withSerwist = withSerwistInit({
  swSrc: 'app/sw.ts',
  swDest: 'public/sw.js',
  disable: process.env.NODE_ENV === 'development',   // ← the dev no-op, on purpose
});
export default withSerwist({ /* next config */ });
```
```ts
// app/sw.ts — consumes the build-injected precache list
import { defaultCache } from '@serwist/next/worker';
import { Serwist } from 'serwist';
const serwist = new Serwist({
  precacheEntries: self.__SW_MANIFEST,   // content-hashed asset list, injected at build
  skipWaiting: false,                    // ← DON'T auto-skip; prompt instead (see below)
  clientsClaim: true,
  navigationPreload: true,
  runtimeCaching: defaultCache,          // sensible Workbox strategies for Next assets
});
serwist.addEventListeners();
```

- At build, Serwist injects **`self.__SW_MANIFEST`** — every precacheable static asset with a **content hash**, so a new deploy = new hashes = the worker knows exactly what changed. Never hand-maintain this list.
- **Offline works only in a built app** (`next build && next start`), not `next dev`. `disable` is deliberately on in development so every change shows immediately.
- The default strategy is **cache-first** for the precached shell (immutable, hashed assets) and **runtime caching** (`runtimeCaching`) for everything else — great for the shell, deliberately *wrong* as a default for live data (below).

## The update problem — why "I redeployed and nothing changed"

This is the single most-reported PWA behavior, so encode it explicitly. A new service worker goes **installing → waiting → activated**. The new worker sits in **waiting** and does **not** take control while any tab running the old one is open — and **refreshing the tab is not enough**; the user must close the app in **every** tab. So a plain reload after deploy shows the *old* app.

Two acceptable resolutions — pick one and implement it, don't leave it to chance:

1. **Prompt the user (recommended).** Keep `skipWaiting: false`; register a listener for a waiting worker, show a non-blocking "A new version is available — Reload" toast, and on click `postMessage({type:'SKIP_WAITING'})` → the worker calls `self.skipWaiting()` → reload. Best UX; the user isn't surprised by a mid-session swap. `vite-plugin-pwa`'s `useRegisterSW` hook and Serwist both expose the waiting-worker signal.
2. **Auto-update on next launch.** Accept that updates land on the next cold start (all tabs closed). Simpler, but a long-lived tab can run a stale build for days — document that trade-off.

Never pretend a redeploy is instantly live for installed users. If a change is **critical** (a broken API contract), you need the prompt path plus a server-side version check that forces it.

## Offline for *data*, not just the shell

The service worker precaches the **app shell** offline; it does **nothing** for your API/RSC data by default. A cache-first shell over a dead API is a UI that loads and then shows errors everywhere. Real offline is a deliberate data strategy:

- **Read data:** add a **runtime caching** route for your API (`NetworkFirst` for freshness-sensitive reads, `StaleWhileRevalidate` for a dashboard) in `runtimeCaching`, or persist to **IndexedDB** and read from it when `!navigator.onLine`. Choose a policy per endpoint. **RSC/Server-Component data won't be there offline** — those routes must be static or the data must be client-fetched (TanStack Query) so the SW/IndexedDB can cache it. This is the App Router's version of Blazor's "the template caches the shell, not your data".
- **Write data:** you can't POST offline. **Queue** the intent locally (IndexedDB, or Workbox **Background Sync** where supported) and replay it on reconnect. Show the user their write is *pending*, not *done*.
- **Conflicts:** replayed writes can clash with server state — carry the optimistic-concurrency token ([`data-access`](../data-access/SKILL.md)) so a stale write is rejected, not silently lost.
- Be honest about scope: full offline-first (local-first sync) is a large commitment. Many apps only need the **shell installable + graceful read-only offline** — say which you're building.

## Offline UX

- Detect with `navigator.onLine` + the `online`/`offline` events in a small client hook (`useEffect` + listener, cleaned up on unmount — the FE React cleanup rule):

```tsx
'use client';
export function useOnline() {
  const [online, setOnline] = useState(true);   // assume online for SSR; correct on mount
  useEffect(() => {
    const up = () => setOnline(true), down = () => setOnline(false);
    setOnline(navigator.onLine);
    window.addEventListener('online', up); window.addEventListener('offline', down);
    return () => { window.removeEventListener('online', up); window.removeEventListener('offline', down); };
  }, []);
  return online;
}
```

- Show a persistent **offline banner** so the user knows why writes are deferred — this pairs with [`error-resilience`](../error-resilience/SKILL.md)'s three-state/failed-region work: an offline read served from cache is a *loaded* state, a blocked write is a *deferred* state, neither is a blank screen.
- **Initialize `online` to `true` for SSR and correct it on mount** — reading `navigator` during render crashes on the server and causes a hydration mismatch ([`reference`](../reference/SKILL.md)).
- Disable or re-label actions that require the network (a queued "Save" reads "Will sync when online"), consistent with [`ui-conventions`](../ui-conventions/SKILL.md) disable-don't-hide + label-persists rules.

## Rules

- **Offline needs a cacheable render strategy** — static/client-rendered routes precache; per-request dynamic RSC/Server Actions can't run offline. Put offline surfaces on static/client routes.
- **Serwist on Next.js, vite-plugin-pwa on Vite** — don't hand-roll a service worker; both are Workbox-based and inject a content-hashed precache manifest.
- **Disable the SW in development** — a caching worker in `next dev` serves stale; offline only works in a built app.
- **Ship the maskable icon + full manifest** (`app/manifest.ts`); installability needs manifest + HTTPS + a registered worker.
- **Handle the update lifecycle explicitly** — keep `skipWaiting: false` and prompt, *or* document next-launch update; a refresh alone won't update a waiting worker.
- **The SW caches the shell, not your data** — add `runtimeCaching`/IndexedDB per endpoint; RSC data must be static or client-fetched to be cacheable.
- **Queue offline writes**, mark them pending, replay on reconnect with a concurrency token.
- **Surface connectivity** — offline banner, deferred-action labels; `useOnline` initialized `true` for SSR; never a silent failure.
- **Watch payload size** — precaching a bloated bundle makes first install slow ([`performance`](../performance/SKILL.md)).

## What NOT to do

- No offline promises on a per-request dynamic route — there's no server to render it offline.
- No caching service worker running in `next dev` — you'll chase phantom stale-cache bugs; keep `disable` on.
- No hand-written service worker maintaining its own asset list — use the injected `__SW_MANIFEST`.
- No `skipWaiting: true` without a user prompt — it swaps the app mid-session under the user's feet.
- No "redeploy = instantly updated" assumption — implement the skip-waiting prompt or document next-launch behavior.
- No cache-first over live API data without a freshness policy — users see stale or broken data.
- No offline write that reports success — mark it pending until it actually syncs.
- No reading `navigator.onLine` during render/SSR — crashes on the server / hydration mismatch; read it in an effect.
- No manifest without a maskable icon + `theme_color` — poor install presentation.

## Validation

- Build (`next build && next start`), install the app, go fully offline → it launches and the shell renders (no browser dino).
- Offline read of a cached endpoint → data shows (from runtime cache/IndexedDB), clearly marked if stale; an uncached/dynamic route degrades to a friendly offline state, not a crash.
- Make a write offline → it's queued and labeled pending; reconnect → it replays and reconciles (concurrency token honored).
- Deploy a new build, reload once → you correctly see *either* the update prompt *or* the documented next-launch behavior — never a silent stale app with no path forward.
- `next dev` → DevTools shows **no** controlling service worker (dev disable held); production shows the Serwist worker controlling the page.
- Lighthouse PWA audit passes (manifest, installable, offline start).
- No hydration warning from the offline banner (SSR default held).

## Handoffs

- Which routes are static vs dynamic (a prerequisite for offline) → [`project-scaffold`](../project-scaffold/SKILL.md)
- Server/RSC response caching, `revalidateTag`, optimistic-concurrency tokens (not client offline) → [`data-access`](../data-access/SKILL.md)
- Live/push data and reconnection UX (a different problem) → [`realtime`](../realtime/SKILL.md)
- The offline/failed/loading UI states themselves (three-state regions, retry) → [`error-resilience`](../error-resilience/SKILL.md)
- Bundle/startup budget the precache depends on → [`performance`](../performance/SKILL.md)
- `theme-color` meta, manifest linkage from metadata → [`seo-discoverability`](../seo-discoverability/SKILL.md)
- Icon/manifest asset craft (sizes, maskable safe zone) → [`design/iconography`](../../../../design/iconography/SKILL.md)
- Offline banner / deferred-action labeling conventions → [`ui-conventions`](../ui-conventions/SKILL.md) + [`design/ux-writing`](../../../../design/ux-writing/SKILL.md)
