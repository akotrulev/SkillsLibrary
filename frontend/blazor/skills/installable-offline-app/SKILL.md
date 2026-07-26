---
name: fe-blazor-installable-offline-app
description: Use when making a Blazor WebAssembly app an installable PWA and/or offline-capable (.NET 8/9/10) — the manifest, the two-service-worker model, cache-first strategy, the update lifecycle (updates apply only after ALL tabs close — surface a prompt), offline UX, and that API data isn't cached by the template. Triggers: "make this installable", "add offline support", "PWA won't update after deploy". Do NOT use for interactive-Server apps (the circuit can't run offline).
---

# Blazor — PWA & Offline

Owns making a Blazor **WebAssembly** app **installable** (a PWA the OS treats like a native app) and **offline-capable** (it loads and runs with no network). These are two goals; a manifest gets you installable, a service worker gets you offline, and *real* offline for dynamic data takes more than the template gives you.

**Hard scope: offline is a WASM story, not a Server one.** An interactive-**Server** Blazor app is a live SignalR circuit — no network means no app, full stop. You can bolt a manifest onto a Server app so it's *installable*, but it will show your offline/reconnection UI the instant it's offline, never a working page. If a project needs genuine offline function, the offline surfaces must be **WASM** ([`project-setup`](../project-setup/SKILL.md) owns that render-mode call). Everything below assumes WASM (standalone, or the `.Client` of a Web App with the net10 caveat noted).

**Version rule:** the template mechanics (two service workers, the assets manifest, cache-first) are **stable across net8/9/10**. The one real delta is a **net10 Blazor-Web-App + PWA setup friction** (the unified template doesn't wire PWA as cleanly as standalone WASM did; see the dotnet/aspnetcore tracking issue) — prefer a **standalone WASM** project for a serious offline app, or wire the `.Client` deliberately. No net-version changes the service-worker contract itself.

## When to use

- Making the app installable (Add to Home Screen / install icon): manifest + icons
- Caching the app shell so it launches offline: the published service worker
- Fixing "my PWA won't update after I deploy" (the #1 PWA support ticket)
- Offline UX: detecting connectivity, an offline banner, deferring writes
- Deciding what offline actually requires for *data*, not just the app shell

## When NOT to use

- Interactive-Server offline — impossible; the circuit needs the network. Reconnection UX for a dropped circuit → [`error-handling`](../error-handling/SKILL.md)
- Server-side/distributed caching of API responses → [`data-fetching`](../data-fetching/SKILL.md) (`HybridCache`) — that's server memory, not client offline
- Live/push data and its disconnect handling → [`realtime`](../realtime/SKILL.md)
- WASM startup size/trimming (offline caching makes payload size matter *more*) → [`performance`](../performance/SKILL.md)

## Installable: the web app manifest

`wwwroot/manifest.webmanifest`, linked from the host page. Installability needs a manifest, HTTPS, and a registered service worker.

```json
{
  "name": "Contoso Field Ops",
  "short_name": "FieldOps",
  "start_url": "./",
  "display": "standalone",
  "background_color": "#ffffff",
  "theme_color": "#0b5cff",
  "icons": [
    { "src": "icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "icon-512.png", "sizes": "512x512", "type": "image/png" },
    { "src": "icon-512-maskable.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable" }
  ]
}
```

- Ship a **maskable** icon so Android doesn't letterbox your logo; `theme_color` should match your top bar (cross-check [`styling`](../styling/SKILL.md) tokens / dark mode).
- Icon/OG asset craft (sizes, safe zones) is [`design/iconography`](../../../../design/iconography/SKILL.md)'s domain — reuse it, don't re-derive.

## Offline: the two-service-worker model

The PWA template ships **two** files, and mixing them up is the classic mistake:

- **`service-worker.js`** — used **in development**; intentionally a **no-op** (no caching) so every change shows immediately without a hard refresh.
- **`service-worker.published.js`** — used **only in a published build**; this is where offline caching lives.

Wire them via MSBuild:

```xml
<ItemGroup>
  <ServiceWorker Include="wwwroot\service-worker.js"
                 PublishedContent="wwwroot\service-worker.published.js" />
</ItemGroup>
<PropertyGroup>
  <ServiceWorkerAssetsManifest>service-worker-assets.js</ServiceWorkerAssetsManifest>
</PropertyGroup>
```

- At publish, the build generates **`service-worker-assets.js`** — every static asset the app needs offline (.NET assemblies, JS, CSS, wasm) with **content hashes**. The published worker precaches exactly this list, so a new deploy = new hashes = the worker knows to update.
- **Offline works only in a published build.** To test locally, temporarily copy `service-worker.published.js`'s content into `service-worker.js` — then revert.
- The default strategy is **cache-first**: the worker serves cached assets and only hits the network on a miss. Great for the immutable app shell, wrong for live data (below).

## The update problem — why "I redeployed and nothing changed"

This is the single most-reported PWA behavior, so encode it explicitly. A new service worker goes **installing → waiting → activated**. The new worker sits in **waiting** and does **not** take control while any tab running the old one is open — and **refreshing the tab is not enough**; the user must close the app in **every** tab. So a plain reload after deploy shows the *old* app.

Two acceptable resolutions — pick one and implement it, don't leave it to chance:

1. **Prompt the user.** Register a callback for a waiting worker, show a non-blocking "A new version is available — Reload" toast, and on click `postMessage({type:'SKIP_WAITING'})` → the worker calls `self.skipWaiting()` → reload. Best UX; the user isn't surprised by a mid-session swap.
2. **Auto-update on next launch.** Accept that updates land on the next cold start (all tabs closed). Simpler, but a long-lived tab can run a stale build for days — document that trade-off.

Never pretend a redeploy is instantly live for installed users. If a change is **critical** (a broken API contract), you need the prompt path plus a server-side version check that forces it.

## Offline for *data*, not just the shell

The template caches the **app** offline; it does **nothing** for your API responses. A cache-first shell over a dead API is a UI that loads and then shows errors everywhere. Real offline is a deliberate data strategy:

- **Read data:** cache API responses (a runtime `Cache` entry, or persist to **IndexedDB**) and read from the cache when `!navigator.onLine`. Choose a policy per endpoint — stale-while-revalidate for a dashboard, network-first for a balance.
- **Write data:** you can't PUT offline. **Queue** the intent locally (IndexedDB) and replay it on reconnect (Background Sync where supported, or a manual flush when `online` fires). Show the user their write is *pending*, not *done*.
- **Conflicts:** replayed writes can clash with server state — carry the optimistic-concurrency token ([`data-fetching`](../data-fetching/SKILL.md)) so a stale write is rejected, not silently lost.
- Be honest about scope: full offline-first (local-first sync) is a large commitment. Many apps only need the **shell installable + graceful read-only offline** — say which you're building.

## Offline UX

- Detect with `navigator.onLine` + the `online`/`offline` events (a small JS-interop bridge — [`javascript-calls`](../javascript-calls/SKILL.md) discipline: collocated module, disposed).
- Show a persistent **offline banner** so the user knows why writes are deferred — this pairs with [`error-handling`](../error-handling/SKILL.md)'s three-state/failed-region work; an offline read served from cache is a *loaded* state, a blocked write is a *deferred* state, neither is a blank screen.
- Disable or re-label actions that require the network (a queued "Save" reads "Will sync when online"), consistent with [`ui-rules`](../ui-rules/SKILL.md) disable-don't-hide + label-persists rules.

## Rules

- **Offline = WASM only.** Server apps can be *installable* but never *offline*; put offline surfaces on WASM.
- **Two service workers:** `service-worker.js` is a dev no-op; `service-worker.published.js` does the caching — offline works only in a published build.
- **Ship the maskable icon + full manifest**; installability needs manifest + HTTPS + a registered worker.
- **Handle the update lifecycle explicitly** — a waiting worker needs all tabs closed *or* a skip-waiting prompt; a refresh alone won't update.
- **The template caches the shell, not your data** — add response caching / IndexedDB per endpoint for real offline.
- **Queue offline writes**, mark them pending, replay on reconnect with a concurrency token.
- **Surface connectivity** — offline banner, deferred-action labels; never a silent failure.
- **Watch payload size** — precaching a bloated WASM app makes first install slow ([`performance`](../performance/SKILL.md)).

## What NOT to do

- No offline promises on an interactive-Server app — it can't work without the circuit.
- No editing `service-worker.published.js` expecting it to run in `dotnet watch` — dev uses the no-op worker.
- No "redeploy = instantly updated" assumption — implement a skip-waiting prompt or document next-launch update.
- No cache-first over live API data without a freshness policy — users see stale or broken data.
- No offline write that reports success — mark it pending until it actually syncs.
- No hand-maintained cache list — let `service-worker-assets.js` (content-hashed) drive precaching.
- No manifest without a maskable icon + `theme_color` — poor install presentation.
- No net10 Blazor-Web-App PWA wiring assumed to "just work" — prefer standalone WASM or wire `.Client` deliberately.

## Validation

- Publish, install the app, go fully offline → it launches and the shell renders (no browser dino).
- Offline read of a cached endpoint → data shows (from cache), clearly marked if stale; an uncached endpoint degrades to a friendly offline state, not a crash.
- Make a write offline → it's queued and labeled pending; reconnect → it replays and reconciles (concurrency token honored).
- Deploy a new build, reload once → you correctly see *either* the update prompt *or* the documented next-launch behavior — never a silent stale app with no path forward.
- Lighthouse PWA audit passes (manifest, installable, offline start).
- DevTools → Application → Service Workers shows the published worker controlling the page in prod, and no caching worker in dev.

## Handoffs

- Which surfaces are WASM (a prerequisite for offline) → [`project-setup`](../project-setup/SKILL.md)
- Reconnection UX for a dropped Server circuit (a different problem) → [`error-handling`](../error-handling/SKILL.md)
- Server/distributed response caching (not client offline) → [`data-fetching`](../data-fetching/SKILL.md)
- WASM payload/startup budget the precache depends on → [`performance`](../performance/SKILL.md)
- `navigator.onLine` bridge + any SW messaging interop → [`javascript-calls`](../javascript-calls/SKILL.md)
- Icon/manifest asset craft (sizes, maskable safe zone) → [`design/iconography`](../../../../design/iconography/SKILL.md)
- Offline banner / deferred-action labeling conventions → [`ui-rules`](../ui-rules/SKILL.md) + [`design/ux-writing`](../../../../design/ux-writing/SKILL.md)
