---
name: animation
description: Use when an element must animate — CSS transitions/keyframes in CSS Modules first, `prefers-reduced-motion` as a hard floor, staggered and scroll reveals, the React exit-animation gap (`animation` `AnimatePresence` or View Transitions), route transitions. Triggers "animate this page-load sequence", "fade elements in on scroll", "the exit animation never plays". Not for deciding WHETHER motion serves the design (`design:visual-identity`).
---

# React — Motion

Owns the **mechanics** of animating a React UI: how a reveal, transition, exit, or route-to-route motion is actually built. The **taste** — whether a surface should animate at all, and what the orchestrated moment *is* — belongs to [`design/visual-identity`](../../../../design/visual-identity/SKILL.md) ("leverage motion deliberately… an orchestrated moment usually lands harder than scattered effects; extra animation is one of the strongest tells a design is AI-generated"). Decide the intent there; implement it here.

**The motion catalog is not decided here either.** *What* the motion is — the product-wide intensity tier, the preset for each trigger, and its duration, easing, do/don't and teardown obligation — comes from [`design/motion`](../../../../design/motion/SKILL.md), backed by the vendored `design:corpus` corpus, **which is the source of truth for those values.** Take the numbers verbatim; this skill decides only how they are built. The house CSS-first bias below is the preferred technique wherever CSS reaches the same duration, easing and reduced-motion behavior — the tiers it cannot reach (scroll-scrub pinning, shared-element Flip morphs, split-text reveals, pointer-follow) are why the corpus specifies GSAP for the Complex tier.

**House bias: CSS first, a JS animation library only where CSS can't reach.** CSS transitions, keyframes, scroll-driven animations, and view transitions run on the compositor, ship no JS, survive re-renders, and honour `prefers-reduced-motion` with a single media query. React's job is to add/remove a class or mount/unmount a node — the animation itself lives in CSS. Reach for a JS library (`animation` / Framer Motion) only for the things CSS genuinely can't express on its own: **exit animations** (see below — React's headline motion gap), layout/shared-element tweening, gesture-follow, and physics/spring feel.

**Version rule.** CSS transitions/keyframes, `prefers-reduced-motion`, `animation-timeline: view()`, and the browser `@view-transition` rule are **framework-version-agnostic** (React 18/19, Next 14/15 identical — they're browser capabilities, not React APIs). The one React-version-sensitive piece is the **`<ViewTransition>` component**: it ships on React's **experimental/canary** channel (and Next's `experimental.viewTransition`), *not* stable React 19.0 — treat it as opt-in-experimental, and use the browser-native `document.startViewTransition` + CSS `@view-transition` (stable everywhere) or `animation` (production-ready) as the default route-transition path. `animation-timeline: view()` is broadly available across engines as of late 2025, with the IntersectionObserver hook as the fallback for older targets.

## When to use

- A page-load entrance sequence (staggered reveals of a hero, cards, list rows)
- Fade/slide/scale an element in as it scrolls into view
- Animating an element **out** as it leaves the list/DOM (the React-specific case)
- A transition between routes/pages
- Hover/press micro-interactions on interactive elements
- Making any of the above respect `prefers-reduced-motion` correctly

## When NOT to use

- Deciding *whether* or *where* to animate, the orchestrated concept → [`design/visual-identity`](../../../../design/visual-identity/SKILL.md)
- Setting up CSS Modules, tokens, dark mode → [`styling`](../styling/SKILL.md)
- Focus movement + live-region announcement on navigation (not "motion") → [`accessibility`](../accessibility/SKILL.md)
- A component library's own transition props (MUI `Fade`/`Grow`/`Slide`/`Collapse`, `TransitionComponent`) → [`component-library`](../component-library/SKILL.md) — use them before hand-rolling
- `useDeferredValue`/`useTransition` to keep input responsive (that's *scheduling*, not visual motion) → [`performance`](../performance/SKILL.md)

## The technique decision

```
What triggers the motion?
  A state class flips, or an element MOUNTS (enter only)
    → CSS transition / @keyframes in a *.module.css. Cheapest, no JS.
  A one-shot entrance sequence when a list first renders
    → CSS @keyframes + animation, staggered via animation-delay from a --i index. No JS.
  The element scrolling into the viewport
    → CSS animation-timeline: view()  (declarative, compositor, auto reduced-motion)
      └ target browser lacks it, or entering must run JS? → IntersectionObserver hook
  An element LEAVING the DOM (exit / list removal / route content swap)
    → React unmounts it immediately — CSS alone can't animate a gone node.
      Use `animation` <AnimatePresence>, or the View Transitions API.
  Navigating between routes/pages
    → CSS @view-transition (stable) + optionally React <ViewTransition> (experimental)
  Physics, gesture-follow, shared-element layout tween, spring feel
    → `animation` (Framer Motion), in a 'use client' component
```

| Technique | JS lib? | Use for | Cost |
|---|---|---|---|
| **CSS transition** | No | State-class flips, hover/press, show (mount) | ~none; the default |
| **CSS `@keyframes` + `animation-delay`** | No | One-shot entrance / staggered reveals | Runs on mount regardless of viewport |
| **CSS `animation-timeline: view()`** | No | Scroll-triggered reveals (opacity/transform) | Browser-support floor; hook fallback for old targets |
| **IntersectionObserver hook** | No lib (built-in) | Scroll trigger on old browsers, or when entering must run JS (lazy-load, analytics) | `useEffect` + ref + `disconnect()` cleanup |
| **`@view-transition` (CSS)** | No | Cross-document / route crossfade | Opt-in CSS; degrades to instant swap |
| **`animation` (`AnimatePresence`)** | Yes | **Exit animations**, layout/shared-element, gesture, spring | Client bundle; `'use client'` |
| **React `<ViewTransition>`** | Built-in (experimental) | Enter/exit/shared under `startTransition`/Suspense | Experimental channel only |

## `prefers-reduced-motion` is a hard floor, not a nicety

Every animation this skill produces must degrade to *no motion* (or a near-instant opacity change) when the user asks for it. This is a WCAG 2.3.3 obligation and a `design/visual-identity` quality-floor rule. The CSS techniques handle it for you when you author them correctly; the JS-library path you must guard yourself.

- **Author transitions/keyframes as opt-*in* motion, gated by a media query** — so the reduced-motion path is the element's resting state and needs no override:

```css
/* Card.module.css */
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
- **For the `animation` library, read the preference and disable animation** — the hook `useReducedMotion()` returns the user's setting; branch the `animate`/`transition` props (or pass a near-zero duration) so a JS animation can't bypass the floor. A `animation` animation with no reduced-motion branch fails WCAG.
- **Never** ship an animation whose only reduced-motion handling is a check you forgot to add. If the motion lives in CSS, the media query is the guarantee.

## Staggered entrance reveals — CSS only

A page-load sequence is the highest-value motion and needs **zero JS**: one keyframe, and an incrementing `animation-delay` per item. Drive the delay from the map index with a CSS custom property so it works for any `.map()` without per-item classes:

```tsx
<ul>
  {items.map((item, i) => (
    <li key={item.id} className={styles.reveal} style={{ '--i': i } as React.CSSProperties}>
      {item.name}
    </li>
  ))}
</ul>
```
```css
/* List.module.css */
@media (prefers-reduced-motion: no-preference) {
  .reveal {
    opacity: 0;
    animation: rise .45s ease-out forwards;
    animation-delay: calc(min(var(--i), 8) * 60ms);   /* stagger, capped at ~8 */
  }
}
```

- **`key` is the stable domain id, not the array index** — the index only feeds the *visual* delay via `--i`; using it as `key` is the re-render bug [`performance`](../performance/SKILL.md) and the FE React code rules forbid.
- **Cap the stagger.** Beyond ~8–10 items the tail feels sluggish — the `min(var(--i), 8)` clamp keeps late rows from lagging.
- A `@keyframes` entrance fires on **mount regardless of viewport**; if items are below the fold, use the scroll technique so the reveal happens when they're actually seen.
- Keep the keyframe animating **`opacity`/`transform` only** — animating layout properties (`height`, `top`, `margin`, `width`) causes reflow jank on every frame.

## Scroll-triggered reveals

**Prefer CSS scroll-driven animations** — declarative, compositor-run, auto reduced-motion, no cleanup, and they work inside a Server Component (no `'use client'`):

```css
/* Section.module.css */
@media (prefers-reduced-motion: no-preference) {
  .onScroll {
    animation: rise linear both;
    animation-timeline: view();
    animation-range: entry 0% entry 40%;   /* play as it enters the viewport */
  }
}
```

**Fallback / callback path — an IntersectionObserver hook.** In React this is *not* an interop hop (there's no interop barrier — [`basics`](../basics/SKILL.md)); it's a plain `useEffect` + `ref`, which means it forces the component to `'use client'`. Use it only when the target browser lacks scroll-driven animations, or when entering the viewport must run **JS** (lazy-load the next page, fire an analytics beacon). Always disconnect on cleanup:

```tsx
'use client';
export function useInView<T extends Element>(onEnter?: () => void) {
  const ref = useRef<T>(null);
  const [inView, setInView] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) { setInView(true); return; }
    const io = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) { setInView(true); onEnter?.(); io.unobserve(el); }
    }, { threshold: 0.2 });
    io.observe(el);
    return () => io.disconnect();          // ← the cleanup is mandatory
  }, [onEnter]);
  return { ref, inView };
}
```

- **The `return () => io.disconnect()` is not optional** — a listener/observer without cleanup is the same leak-across-navigation the FE React code rules and [`realtime`](../realtime/SKILL.md) warn about; React runs effect cleanup on unmount and on every dep change.
- Guard the JS path with the same reduced-motion check (shown above) so it matches the CSS floor — reduced-motion users get the content revealed immediately, not held below the fold.

## Exit animations — React's headline motion gap

This is the one thing CSS **cannot** do alone in React, and the most common motion mistake. When you remove an item from state, React unmounts its node **synchronously** — it's gone from the DOM before any CSS transition can play. A CSS exit animation on an unmounting element simply never runs.

Two correct resolutions:

1. **`animation` (`AnimatePresence`)** — the production default. It keeps the exiting node mounted until its `exit` animation finishes, then removes it. Client-only:

```tsx
'use client';
import { AnimatePresence, motion } from 'motion/react';

<AnimatePresence>
  {items.map((item) => (
    <motion.li key={item.id}
      initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }}>
      {item.name}
    </motion.li>
  ))}
</AnimatePresence>
```

2. **The View Transitions API** — for enter/exit under a `startTransition` (React `<ViewTransition>`, experimental) or a route swap (`@view-transition`, stable). The browser snapshots before/after and tweens the difference, so a removed element can fade out via `::view-transition-old`.

- **`key` on the animating element must be the stable domain id** — `AnimatePresence` tracks presence by `key`; an index key makes exit animations play on the wrong item.
- Don't hand-roll a "delay unmount with a `setTimeout`" — it's the bug `AnimatePresence` exists to solve, and it leaks timers.

## Route / page transitions

- **Stable path — CSS `@view-transition`.** For MPA-style cross-document navigation, opt in with one global rule; the browser crossfades old→new and honours `prefers-reduced-motion` for free:

```css
/* globals.css — a document-level concern, not a CSS Module */
@view-transition { navigation: auto; }

@media (prefers-reduced-motion: no-preference) {
  ::view-transition-old(root) { animation: fade-out .2s ease both; }
  ::view-transition-new(root) { animation: fade-in  .2s ease both; }
}
```

- **App Router client navigation** doesn't reload the document, so `@view-transition`'s `navigation: auto` doesn't fire on `<Link>` clicks. For animated client-side route transitions use **React's `<ViewTransition>`** (wrap the animating region; drive the swap through `startTransition`) behind Next's `experimental.viewTransition` flag — treat it as experimental — or `animation` keyed on `usePathname()`. See the vendored seed [`frontend/react/vendor/view-transitions`](../../vendor/view-transitions/SKILL.md) for the full pattern catalogue (shared element, Suspense reveal, list reorder, directional nav).
- **Shared-element** transitions: give the source and destination elements the same `view-transition-name` (CSS) or the same `name` prop (`<ViewTransition name="...">`); the browser tweens between them across the swap.
- If the browser lacks the API, navigation still works — it swaps instantly. **No JS fallback needed**; the motion is pure enhancement.

## When is motion worth a JS library?

Almost never for entrance/scroll/route cases — CSS covers them and ships no JS. Pay for `animation` only when:
- you need an **exit animation** (the CSS-can't case), **or**
- the motion is **layout/shared-element tweening** (an item reflows to a new position and should slide, not jump — `animation`'s `layout` prop), **or**
- it's fundamentally **imperative** — gesture-follow, drag, spring physics, scroll-linked parallax with JS values.

Anything using `animation` is a **Client Component** (`'use client'`) and adds to the bundle — keep it at the leaf, not the layout ([`performance`](../performance/SKILL.md): push client boundaries down). A whole page wrapped in `animation` to fade one card in is the wrong layer — move it to a CSS keyframe.

## Rules

- **CSS first**; a JS library (`animation`) only for exit/layout/gesture/physics CSS can't express, kept at a `'use client'` leaf.
- **`prefers-reduced-motion` is a hard floor** — author CSS motion as `@media (prefers-reduced-motion: no-preference)` opt-in so the resting state *is* the reduced state; branch `animation` on `useReducedMotion()`.
- **Animate `opacity`/`transform` only** — never layout properties (reflow jank).
- **Staggered entrances via `animation-delay` from a CSS `--i` index**, capped (~8); `key` stays the stable id, index feeds only the delay.
- **Scroll reveals: `animation-timeline: view()` first**, an IntersectionObserver hook (with `disconnect()` cleanup) as the fallback/callback path.
- **Exit animations need `AnimatePresence` or View Transitions** — React unmounts synchronously; CSS alone can't animate a gone node.
- **Route transitions: `@view-transition` (stable) for cross-document**; `<ViewTransition>` (experimental) or `animation` for App Router client nav; degrades to instant swap with no fallback code.
- **Use the component library's transition components before hand-rolling** (MUI `Fade`/`Grow`/`Collapse`).

## What NOT to do

- No animation without a reduced-motion path — a bare `animation:`/`transition:` with no media guard, or a `animation` prop with no `useReducedMotion()` branch, fails WCAG 2.3.3.
- No animating `height`/`top`/`margin`/`width` for motion — reflow every frame; use `transform`.
- No array index as `key` on an animated list — breaks stagger targeting and `AnimatePresence` exit tracking (and is a re-render bug regardless).
- No `setTimeout`-delayed unmount to fake an exit animation — use `AnimatePresence`; the manual version leaks timers.
- No IntersectionObserver in a `useEffect` without `disconnect()` in the cleanup — leaks across navigation.
- No `'use client'` on a whole route just to animate one leaf — push the motion component down.
- No page-transition fallback shim — `@view-transition` and `<ViewTransition>` degrade to instant on unsupported browsers by design.
- No motion decision made *here* — where/whether to animate is [`design/visual-identity`](../../../../design/visual-identity/SKILL.md)'s call.

## Validation

Inside a `Gate: none` plan task, run none of these checks and report "written, not run"; the plan's gate task runs them.

- Toggle OS **Reduce Motion** on → every reveal/transition drops to instant (or a bare crossfade); nothing slides, bounces, or is held below the fold; `animation` components render at rest.
- Reload a page with a staggered entrance → items rise in sequence, the tail isn't sluggish, no layout shift while they animate.
- Scroll a long page → below-the-fold sections reveal as they enter, not all at once on load.
- Remove a list item → it animates **out** (doesn't vanish); the remaining items reflow smoothly.
- Navigate between routes → the transition plays where wired; on a browser without the API it swaps instantly with no error.
- DevTools Performance → animated frames stay on the compositor (no purple "Layout" bars per frame).
- Unmount a component using the IntersectionObserver hook → no leaked observer (cleanup ran).

## Handoffs

- Whether/where to animate, the orchestrated concept, restraint ("remove one accessory") → [`design/visual-identity`](../../../../design/visual-identity/SKILL.md)
- CSS Modules, tokens, `:focus-visible`, dark mode → [`styling`](../styling/SKILL.md)
- Focus movement + announcement on client-side navigation (not visual motion) → [`accessibility`](../accessibility/SKILL.md)
- Component-library transition components (use before hand-rolling) → [`component-library`](../component-library/SKILL.md)
- `useDeferredValue`/`useTransition` scheduling, keeping the client bundle lean → [`performance`](../performance/SKILL.md)
- The full View Transitions pattern catalogue (shared element, Suspense reveal, directional nav) → the vendored seed [`frontend/react/vendor/view-transitions`](../../vendor/view-transitions/SKILL.md)
- Effect-cleanup / subscription-teardown discipline (same rule) → [`realtime`](../realtime/SKILL.md)
