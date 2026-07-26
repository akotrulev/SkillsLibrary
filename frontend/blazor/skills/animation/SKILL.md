---
name: fe-blazor-animation
description: Use when adding animation/motion to a Blazor app (.NET 8/9/10) — CSS transitions/keyframes in `.razor.css` isolation over JS, `prefers-reduced-motion` as a hard floor, staggered reveals, scroll reveals (CSS `animation-timeline` first), View Transitions. Triggers: "animate this component / page-load sequence", "fade elements in on scroll", "add a page transition". Do NOT use to decide WHETHER motion serves the design (`design/visual-identity`) or CSS-isolation setup (`styling`).
---

# Blazor — Motion

Owns the **mechanics** of animating a Blazor UI: how a reveal, transition, or page-to-page motion is actually built. The **taste** — whether a surface should animate at all, and what the orchestrated moment *is* — belongs to [`design/visual-identity`](../../../../design/visual-identity/SKILL.md) ("leverage motion deliberately… an orchestrated moment usually lands harder than scattered effects; extra animation is one of the strongest tells a design is AI-generated"). Decide the intent there; implement it here.

**House bias: CSS first, JS interop only where CSS can't reach.** Blazor re-renders and diffs the DOM; a JS animation library that mutates the same nodes fights the renderer. Native CSS (transitions, keyframes, scroll-driven animations, view transitions) runs on the compositor, needs no interop hop, and survives a re-render. Reach for JS interop only for the two things CSS genuinely can't do: an animation whose *trigger* is a JS callback (IntersectionObserver, ResizeObserver) on browsers without the CSS equivalent, and imperatively starting the View Transitions API.

**Version rule:** CSS transitions/keyframes and `prefers-reduced-motion` are version-agnostic (net8/9/10 identical). The net-sensitive piece is **enhanced-navigation view transitions** — enhanced navigation is net8+ (default in static SSR), so the `::view-transition` cross-document/enhanced-nav flow applies net8/9/10 the same; net10 changes nothing about the API. CSS scroll-driven animations (`animation-timeline: view()`) are a *browser* capability, not a .NET one — broadly available across engines as of late 2025, with the IntersectionObserver fallback for older targets.

## When to use

- A page-load entrance sequence (staggered reveals of a hero, cards, list rows)
- Fade/slide/scale an element in as it scrolls into view
- A transition between routes/pages under enhanced navigation
- Hover/press micro-interactions on interactive elements
- Making any of the above respect `prefers-reduced-motion` correctly

## When NOT to use

- Deciding *whether* or *where* to animate, the orchestrated concept → [`design/visual-identity`](../../../../design/visual-identity/SKILL.md)
- Setting up CSS isolation, tokens, dark mode → [`styling`](../styling/SKILL.md)
- Reconnection modal / circuit pause-resume UX → [`error-handling`](../error-handling/SKILL.md)
- Focus movement + live-region announcement (not "motion") → [`accessibility`](../accessibility/SKILL.md)
- A component library's own transition props (MudBlazor `Transition`, Fluent motion tokens) → [`component-library`](../component-library/SKILL.md) — use them before hand-rolling

## The technique decision

```
What triggers the motion?
  Element enters/leaves the DOM or a state class flips
    → CSS transition on the property (opacity/transform). Cheapest, no keyframes.
  A one-shot entrance when the component first renders
    → CSS @keyframes + animation, staggered via animation-delay. No JS.
  The element scrolling into the viewport
    → CSS animation-timeline: view()  (declarative, compositor, auto reduced-motion)
      └ target browser lacks it? → IntersectionObserver via JS interop (adds a class)
  Navigating between routes/pages
    → View Transitions API under enhanced navigation (net8+)
  Something CSS fundamentally can't express (physics, gesture-follow, canvas)
    → JS interop to a library, scoped to a node Blazor does NOT re-render into
```

| Technique | Interop? | Use for | Cost |
|---|---|---|---|
| **CSS transition** | No | State-class flips, hover/press, show/hide | ~none; the default |
| **CSS `@keyframes` + `animation-delay`** | No | One-shot entrance / staggered reveals | Runs on first render regardless of viewport |
| **CSS `animation-timeline: view()`** | No | Scroll-triggered reveals (opacity/transform) | Browser-support floor; fallback needed for old targets |
| **IntersectionObserver (JS interop)** | Yes | Scroll trigger on old browsers, or when a **C# callback** must fire (lazy-load, analytics) | Interop hop + `IAsyncDisposable` cleanup |
| **View Transitions API** | Minimal | Route/page transitions under enhanced nav | net8+; opt-in CSS, one small script |

## `prefers-reduced-motion` is a hard floor, not a nicety

Every animation this skill produces must degrade to *no motion* (or a near-instant opacity change) when the user asks for it. This is a WCAG 2.3.3 obligation and a `design/visual-identity` quality-floor rule. Two of the techniques handle it for you; two you must guard yourself.

- **Author transitions/keyframes as opt-*in* motion, gated by a media query** — so the reduced-motion path is the element's resting state and needs no override:

```css
/* Card.razor.css */
.card { opacity: 1; }                              /* reduced-motion default: just visible */

@media (prefers-reduced-motion: no-preference) {
  .card {
    opacity: 0;
    animation: rise .5s ease-out forwards;
  }
}
@keyframes rise { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: none; } }
```

- **`animation-timeline: view()`** and the **View Transitions API** both suppress motion automatically under `prefers-reduced-motion: reduce` — but still wrap any *large* transform in the `no-preference` guard, because "reduced" means *less*, not necessarily *none*, and a big slide can trigger vestibular issues even when the browser keeps a crossfade.
- **Never** ship an animation whose only reduced-motion handling is a JS check you forgot to add. If the motion lives in CSS, the media query is the guarantee.

## Staggered entrance reveals — CSS only

A page-load sequence is the highest-value motion and needs **zero JS**: one keyframe, and an incrementing `animation-delay` per item. Drive the delay from an index with a CSS custom property so it works for a Blazor `@foreach` without per-item classes:

```razor
@foreach (var (item, i) in Items.Select((x, i) => (x, i)))
{
    <li class="reveal" style="--i:@i">@item.Name</li>
}
```
```css
/* List.razor.css */
@media (prefers-reduced-motion: no-preference) {
  .reveal {
    opacity: 0;
    animation: rise .45s ease-out forwards;
    animation-delay: calc(var(--i) * 60ms);   /* stagger from the row index */
  }
}
```

- **Cap the stagger.** Beyond ~8–10 items the tail feels sluggish — clamp with `min(var(--i), 8)` so late rows don't lag.
- A `@keyframes` entrance fires on **first render regardless of viewport**; if items are below the fold, use the scroll technique instead so the reveal happens when they're actually seen.
- Keep the keyframe animating **`opacity`/`transform` only** — animating layout properties (`height`, `top`, `margin`) causes reflow jank on every frame.

## Scroll-triggered reveals

**Prefer CSS scroll-driven animations** — declarative, compositor-run, auto reduced-motion, no cleanup:

```css
/* Section.razor.css */
@media (prefers-reduced-motion: no-preference) {
  .on-scroll {
    animation: rise linear both;
    animation-timeline: view();
    animation-range: entry 0% entry 40%;   /* play as it enters the viewport */
  }
}
```

**Fallback / callback path — IntersectionObserver via JS interop.** Use it only when the target browser lacks scroll-driven animations, or when entering the viewport must run **C# logic** (lazy-load the next page, fire an analytics beacon). Collocate the module and dispose it:

```razor
@implements IAsyncDisposable
@inject IJSRuntime JS
<div @ref="_el" class="on-scroll">@ChildContent</div>
@code {
    private ElementReference _el;
    private IJSObjectReference? _module;
    protected override async Task OnAfterRenderAsync(bool firstRender)
    {
        if (!firstRender) return;
        _module = await JS.InvokeAsync<IJSObjectReference>("import", "./Section.razor.js");
        await _module.InvokeVoidAsync("observe", _el, DotNetObjectReference.Create(this));
    }
    [JSInvokable] public void OnEnter() { /* add the class / load more / log */ }
    public async ValueTask DisposeAsync()
    {
        if (_module is not null) { await _module.InvokeVoidAsync("dispose"); await _module.DisposeAsync(); }
    }
}
```
```js
// Section.razor.js — one observer per element, torn down on dispose
let io;
export function observe(el, dotnet) {
  io = new IntersectionObserver((entries) => {
    for (const e of entries) if (e.isIntersecting) { el.classList.add('in'); dotnet.invokeMethodAsync('OnEnter'); io.unobserve(el); }
  }, { threshold: 0.2 });
  io.observe(el);
}
export function dispose() { io?.disconnect(); }
```

- **Always `IAsyncDisposable` + `disconnect()`** — an un-disposed observer + `DotNetObjectReference` is a memory leak on every navigation, exactly the failure [`realtime`](../realtime/SKILL.md) and [`accessibility`](../accessibility/SKILL.md) warn about for interop lifecycles.
- Guard the JS path with the same reduced-motion check (`window.matchMedia('(prefers-reduced-motion: reduce)').matches`) so it matches the CSS floor.

## Page transitions — the View Transitions API under enhanced navigation

Enhanced navigation (net8+, default for static SSR) swaps the DOM without a full reload — which is exactly what the browser's **View Transitions API** animates. Opt in with CSS; the browser cross-fades old→new by default and honours `prefers-reduced-motion` for free:

```css
/* app.css (global — this is a document-level concern, not component-scoped) */
@view-transition { navigation: auto; }

@media (prefers-reduced-motion: no-preference) {
  ::view-transition-old(root) { animation: fade-out .2s ease both; }
  ::view-transition-new(root) { animation: fade-in  .2s ease both; }
}
```

- For a **shared-element** transition (a card that morphs into a detail header), give both elements the same `view-transition-name` in their scoped CSS; the browser tweens between them across the navigation.
- If the target browser lacks the API, enhanced navigation still works — it just swaps instantly. No JS fallback needed; the motion is pure enhancement.
- This is the one motion concern that legitimately lives in the **global** stylesheet (it targets the document root pseudo-elements), not a `.razor.css` — everything else in this skill is component-scoped.

## When is motion worth a JS-interop hop?

Almost never for the reveal/transition cases above — CSS covers them. Pay the interop cost only when:
- the **trigger** is a JS observer and the CSS equivalent isn't available on your target browsers (scroll reveal on old engines), **or**
- entering/leaving the viewport must run **C# behaviour** (not just a visual change), **or**
- the motion is fundamentally imperative — physics, drag-follow, canvas/WebGL — where you hand a **node Blazor never re-renders into** (a `@ref`'d element with no interactive children) to a library, and tear it down in `DisposeAsync`.

If a re-render can wipe the animation's target, you've picked the wrong layer — move it to CSS or isolate the node.

## Rules

- **CSS first**; JS interop only for observer-triggered or imperative motion CSS can't express, always with `IAsyncDisposable` teardown.
- **`prefers-reduced-motion` is a hard floor** — author motion as `@media (prefers-reduced-motion: no-preference)` opt-in so the resting state *is* the reduced state; guard large transforms even where the browser auto-reduces.
- **Animate `opacity`/`transform` only** — never layout properties (reflow jank).
- **Staggered entrances via `animation-delay` from a CSS `--i` index**, capped (~8 items); use scroll reveals for below-the-fold content.
- **Scroll reveals: `animation-timeline: view()` first**, IntersectionObserver interop as the fallback/callback path.
- **Page transitions: opt into View Transitions** in global CSS under enhanced navigation (net8+); it degrades to instant swap with no fallback code.
- **Never let a JS animation library fight the renderer** — hand it only nodes Blazor won't re-render into.

## What NOT to do

- No JS animation on nodes Blazor diffs/re-renders (the animation resets or the library and renderer desync).
- No animation without a reduced-motion path — a bare `animation:` with no media guard fails WCAG 2.3.3.
- No animating `height`/`top`/`margin`/`width` for motion — reflow on every frame; use `transform`.
- No IntersectionObserver/interop module without `disconnect()` + `DisposeAsync` (leaks across navigation).
- No `animation-delay` stagger that runs unbounded — a 40-row list reveals for 2.4s; cap it.
- No page-transition JS shim — enhanced nav + View Transitions degrade to instant on unsupported browsers by design.
- No motion decision made *here* — where/whether to animate is [`design/visual-identity`](../../../../design/visual-identity/SKILL.md)'s call.

## Validation

- Toggle OS **Reduce Motion** on → every reveal/transition drops to instant (or a bare crossfade); nothing slides or bounces.
- Reload a page with a staggered entrance → items rise in sequence, the tail isn't sluggish, no layout shift while they animate.
- Scroll a long page → below-the-fold sections reveal as they enter, not all at once on load.
- Navigate between routes → the transition plays under enhanced nav; on a browser without the API it swaps instantly with no error.
- DevTools Performance/Rendering → animated frames stay on the compositor (no purple "Layout" bars per frame).
- Navigate away from a page using an IntersectionObserver → no leaked observer or `DotNetObjectReference` (the module's `dispose` ran).

## Handoffs

- Whether/where to animate, the orchestrated concept, restraint ("remove one accessory") → [`design/visual-identity`](../../../../design/visual-identity/SKILL.md)
- CSS isolation, tokens, `:focus-visible`, dark mode → [`styling`](../styling/SKILL.md)
- Reconnection/circuit UX (a different kind of "motion") → [`error-handling`](../error-handling/SKILL.md)
- Focus movement + announcement on navigation (not visual motion) → [`accessibility`](../accessibility/SKILL.md)
- Component-library transition props (use before hand-rolling) → [`component-library`](../component-library/SKILL.md)
- Interop-module lifecycle/disposal patterns → [`realtime`](../realtime/SKILL.md) (same `IAsyncDisposable` discipline)
