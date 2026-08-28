---
name: design-motion
description: Use when deciding WHAT a UI's motion is — the intensity tier (subtle / standard / complex) the product earns, which of the 17 vendored presets fits the trigger (hover, scroll reveal, stagger, page transition, parallax, skeleton, carousel), and the duration/easing/cleanup contract each carries. Stack-agnostic; backed by the `gsap` domain of `design-ui-ux-pro-max`. Triggers "what animation should this have", "pick a scroll reveal", "our animations feel random", "how long should this transition be", "motion intensity for this product". Not for whether motion serves the brief at all (`design-visual-identity`) or how it is coded in a stack (a stack's `animation`).
---

# Motion design — the tier, the preset, the floor

Owns the **motion catalog**: which of the seven motion categories a surface needs, at which of the three intensity tiers, with what duration, easing, do/don't, and cleanup obligation. The catalog is not invented here — it is the `gsap` domain of the vendored corpus ([`design-ui-ux-pro-max`](../ui-ux-pro-max/SKILL.md)), **the source of truth for every value in it.** This skill is how the catalog is chosen from and applied.

**The three-way fence:**

| | Owns | Who |
|---|---|---|
| **Whether** motion serves the brief at all, and what the one orchestrated moment is | the intent | [`design-visual-identity`](../visual-identity/SKILL.md) |
| **What** the motion is — category, tier, duration, easing, the do/don't | the catalog | **this skill** |
| **How** it is built in the codebase | the mechanics | a stack's `animation` ([Blazor](../../frontend/blazor/skills/animation/SKILL.md) · [React](../../frontend/react/skills/animation/SKILL.md)) |

## When to use

- A surface needs motion and nobody has said *which* motion — pick the category and tier here.
- The animations across a product feel arbitrary (one 800ms hover next to a 100ms modal) — this is a tier problem, not a code problem.
- A brief carries a motion dial (`--motion 1-10` on the design-system generator) and it has to become concrete presets.
- A scroll, stagger, parallax, page-transition, skeleton, or carousel behavior is being specified.

Do **not** use it to decide whether the page should animate at all (`design-visual-identity`), or to write the animation code (the stack's `animation`).

## Query the catalog first

Never specify motion from memory. Every value below comes from the corpus:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/design/ui-ux-pro-max/scripts/search.py" "scroll reveal stagger" --domain gsap
```

The `--design-system --motion <1-10>` dial resolves a tier and attaches the matching preset — snippet, framework notes, do/don't, and performance notes — directly to the generated system. Use that when the brief is being generated; use `--domain gsap` when one surface needs one preset.

## The intensity tier — decide this once, per product

The tier is a **product-level decision**, not a per-element one. A product picks one tier and every category is realised at that tier; mixing tiers is what makes motion feel random.

| Tier | Reads as | Fits | Dial |
|---|---|---|---|
| **Subtle** | feedback only — you notice its absence, not its presence | applications, dashboards, admin, data-dense tools, anything used all day | `--motion 1-3` |
| **Standard** | motion that has a point of view without asking for attention | most product marketing, SaaS sites, content products | `--motion 4-7` |
| **Complex** | choreography as part of the product's argument | launch pages, portfolios, storytelling, brand moments | `--motion 8-10` |

**The application lane is Subtle by default.** A grid, a form, a settings page gets press/hover/region-enter feedback and nothing more — the same rule `design-visual-identity` states as "in the application lane motion is feedback only, never atmosphere."

## The seven categories

Each has a Subtle / Standard / Complex realisation in the corpus. Query the row before implementing — the snippet, framework notes, and performance notes matter as much as the numbers.

| Category | Trigger | Subtle | Standard | Complex |
|---|---|---|---|---|
| **Hover micro-interaction** | hover | 150–200ms `power1.out`, ≤2px displacement | 200–300ms `power2.out`, lift + 1.02 scale + shadow | 300–500ms `elastic.out`, magnetic / 3D tilt |
| **Scroll reveal** | viewport enter | 300–400ms fade + 8–16px y | 400–600ms slide-up, ≤8-child stagger | scrub-driven pin / scrollytelling |
| **Stagger list** | load or scroll | 250–350ms, 0.02–0.04s per item | 300–450ms `back.out`, grid-aware wave | SplitText char reveal, headlines only |
| **Page transition** | route change | 200–300ms fade, exit ≤250ms | 400–600ms overlay wipe | shared-element / Flip morph, 500–800ms |
| **Parallax scroll** | continuous scroll | one layer, 5–15 yPercent | 3–4 layers, speed varied by depth | — |
| **Loading / skeleton** | mount / async wait | 1200–1600ms gradient sweep loop | 800–1200ms dot/progress loop | — |
| **Carousel / auto-rotation** | timer / focus / hover / visibility | — | user-controlled or stopped; prev/next + play/pause required | — |

## The non-negotiables

These hold at every tier, and the corpus repeats them across rows because they are the ones teams skip.

1. **`prefers-reduced-motion` is a floor, not a preference.** Every preset gates behind `matchMedia('(prefers-reduced-motion: reduce)')` and renders a **static final state** — not a shortened animation, not a no-op that leaves content invisible. A scroll reveal under reduced motion means the content is simply *there*.
2. **Animate transform and opacity only.** Width, height, margin, top/left force layout and drop off the compositor thread. This is why the hover rows say ≤2px displacement rather than a padding change.
3. **Every loop and listener is killed.** `repeat: -1` tweens, pointer handlers, timers, ScrollTriggers and SplitText splits leak on SPA route changes unless explicitly torn down — `useGSAP` scope in React, the framework's cleanup hook elsewhere, `split.revert()` to restore real text nodes for assistive tech.
4. **Offscreen and hidden means stopped.** IntersectionObserver pauses animation that has scrolled away; `visibilitychange` pauses work in a background tab. A shimmer running behind a hidden tab is pure battery cost.
5. **Motion never carries meaning alone,** and never blocks. Exit animations cap at ~250ms so navigation stays responsive; a loader under ~300ms of wait should not appear at all.
6. **Auto-advancing content is stoppable.** A carousel needs visible previous/next *and* play/pause, pauses on hover and on focus inside it, announces the current slide without moving focus, and does not auto-advance under reduced motion. This is WCAG 2.2 territory, not taste — see [`design-accessible-by-design`](../accessible-by-design/SKILL.md).
7. **Never parallax body copy or interactive controls.** Decorative and background layers only; parallaxed reading text hurts comprehension and triggers motion sickness.
8. **Reveal is not a content-hiding strategy.** Below-the-fold content that is invisible by default needs a no-JS fallback, or crawlers and assistive tech see an empty page.

## Applying a preset

1. **Confirm the tier** from the product lane (application → Subtle) or the brief's motion dial.
2. **Query the row** — `--domain gsap` with the trigger, not the technique (`"route change overlay"`, not `"gsap timeline"`).
3. **Take the numbers verbatim.** The duration and easing in the row are the specification; "roughly 300ms, some ease-out" is how a product ends up with fourteen different transition feels.
4. **Hand the row to the stack's `animation` skill** for implementation. The corpus's snippet is GSAP; where the stack's CSS-first path expresses the same preset with the same duration, easing, and reduced-motion behavior, that path is preferred — the *values* are not negotiable, the *technique* is. The tiers CSS genuinely cannot reach (scrub-pinning, Flip shared-element morphs, SplitText, magnetic pointer-follow) are why the corpus specifies GSAP for the Complex tier.
5. **Record the cleanup obligation** with the component that owns the motion. A preset with a `repeat: -1` or a pointer listener is not done until its teardown exists.

## Review checklist

- One **intensity tier** applies product-wide; no surface animates at a tier the product didn't choose. Application lane is Subtle.
- Every preset's **duration and easing came from the corpus row**, not from memory.
- **`prefers-reduced-motion` renders a static final state** everywhere — no hidden content, no shortened flourish.
- Only **transform/opacity** animate; no width/height/margin/top/left tweens.
- Every **loop, listener, timer, ScrollTrigger and SplitText split has a teardown**; SplitText reverts on unmount.
- Offscreen and background-tab animation is **paused**, not just invisible.
- Exit/route animation is **≤250ms** and never blocks navigation; sub-300ms waits get no loader.
- Auto-rotating content has **prev/next + play/pause**, pauses on hover and focus, and stops under reduced motion.
- **No parallax on body copy or controls**; reveal-hidden content has a no-JS fallback.

## Related

- [`design-ui-ux-pro-max`](../ui-ux-pro-max/SKILL.md) — the `gsap` domain that is this skill's catalog, and the `--motion` dial that resolves the tier.
- [`design-visual-identity`](../visual-identity/SKILL.md) — decides whether motion serves the brief and what the one orchestrated moment is.
- [`design-accessible-by-design`](../accessible-by-design/SKILL.md) — the WCAG 2.2 side of pause/stop, focus, and non-motion alternatives.
- [`design-landing-patterns`](../landing-patterns/SKILL.md) — the landing patterns whose "recommended effects" column names the motion a section expects.
- A stack's `animation` ([Blazor](../../frontend/blazor/skills/animation/SKILL.md) · [React](../../frontend/react/skills/animation/SKILL.md)) — builds the chosen preset.
