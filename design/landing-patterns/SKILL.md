---
name: design-landing-patterns
description: Use when structuring a MARKETING page — section order, primary-CTA placement, color strategy, effects and conversion rules from the 34 vendored landing patterns, picked from the product type rather than defaulting to hero-features-CTA. Triggers "structure the landing page", "what sections should this page have", "where does the CTA go", "design the pricing/waitlist page". Not for the look itself (`design-visual-identity`) or an application's IA (`design-ux-patterns`).
---

# Landing patterns — the section order a marketing page earns

Owns the **structure** of a page whose job is to persuade in one visit: which of the 34 patterns fits the product, what sections it runs in what order, where the primary CTA sits, what color strategy the sections use, and the conversion rules the pattern carries. The catalog is the `landing` domain of the vendored corpus ([`design-ui-ux-pro-max`](../ui-ux-pro-max/SKILL.md)) — **the source of truth for every pattern, its section order, and its conversion rules.**

**Where this sits:** [`design-visual-identity`](../visual-identity/SKILL.md)'s marketing lane decides the *look* — the hero thesis, the signature element, the one aesthetic risk. This skill decides the *skeleton* those choices are hung on. [`design-ux-patterns`](../ux-patterns/SKILL.md) owns the other side of the fence: an **application's** IA, shell, and page anatomy. A brief with a marketing site and the app behind it uses both, and the app never inherits the landing page's structure.

## When to use

- A landing, campaign, launch, pricing, waitlist, or portfolio page needs its section order decided.
- The page exists but converts badly, or reads as a generic hero-features-CTA template.
- The `--design-system` generator returned a pattern and it has to become real sections.
- Deciding where the primary CTA goes, and how many CTAs the page gets.

Do **not** use it for an application's navigation and page anatomy (`design-ux-patterns`), for the visual direction (`design-visual-identity`), or for the words in the sections (`design-ux-writing`).

## Query the catalog first

The pattern is chosen from the corpus, not from habit:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/design/ui-ux-pro-max/scripts/search.py" "hero social-proof saas trial" --domain landing
```

`--design-system` already resolves a landing pattern from the product type and returns it alongside the style and palette — start there for a new product, and use `--domain landing` when only the structure is in question.

Each row carries six things, all of which apply together: **section order**, **primary CTA placement**, **color strategy**, **recommended effects**, **conversion optimization**, and the pattern's aliases. Taking the section order while ignoring the CTA placement and conversion rules is how a pattern stops working.

## Picking the pattern

Pick from **what the visitor must decide**, not from what looks impressive. The 34 patterns cluster into families:

| The visitor must… | Family | Representative patterns |
|---|---|---|
| Understand what this *is* | explanatory | Hero + Features + CTA · Hero-Centric Design · Feature-Rich Showcase · Bento Grid Showcase |
| Believe it works | proof-led | Hero + Testimonials + CTA · Trust & Authority + Conversion · Product Review/Ratings · Enterprise Gateway |
| See it work | demonstration | Product Demo + Features · Video-First Hero · Interactive 3D Configurator · Real-Time / Operations Landing |
| Choose between options | comparison | Comparison Table + CTA · Comparison Table Focus · Pricing Page + CTA · Pricing-Focused Landing |
| Commit an email now | capture | Lead Magnet + Form · Newsletter / Content First · Webinar Registration · Waitlist / Coming Soon |
| Be walked through it | narrative | Funnel (3-Step Conversion) · Scroll-Triggered Storytelling · Horizontal Scroll Journey · Before-After Transformation |
| Browse and judge | showcase | Portfolio Grid · Marketplace / Directory · App Store Style Landing · Community/Forum Landing |
| Find an answer | support | FAQ / Documentation Landing |

**Hero + Features + CTA is the default answer, which is exactly why it needs justifying.** If the visitor's real question is "is this credible" or "which plan", the explanatory pattern answers the wrong question well.

## The rules every pattern shares

1. **Proof precedes the ask.** In every proof-led pattern the testimonial, logo wall, or rating block sits *before* the CTA it is meant to unlock. A CTA above the evidence converts the already-convinced only.
2. **The primary CTA appears at least twice** — in or near the hero, and again after the argument that earns it. The corpus states the placement per pattern (sticky hero + bottom, post-testimonials, per-step mini-CTAs); take it from the row.
3. **One primary action per page.** Secondary actions are visually secondary (Contact Sales primary / Login secondary, not two equal buttons). A page with two primary CTAs has none.
4. **CTA label contrast is verified against the button fill at 4.5:1**, with 7:1 only where the product explicitly targets AAA normal text. This is in the corpus's color-strategy column for a reason — the accent-on-accent CTA is the most common contrast failure on a landing page.
5. **Every auto-moving element is stoppable.** Testimonial carousels, logo marquees, background video, screenshot carousels, countdown tickers: visible previous/next and play/pause, pause on hover and on focus inside, stop under `prefers-reduced-motion`, and never move focus on rotation. [`design-motion`](../motion/SKILL.md) owns the timing; [`design-accessible-by-design`](../accessible-by-design/SKILL.md) owns the criterion.
6. **Motion is the pattern's, not the page's.** The recommended-effects column names what the pattern expects (parallax hero, card hover lift, staggered bento reveal, scroll-jacked journey). Realise it at the product's motion tier — and scroll-jacking always keeps a normal vertical navigation path and disables under reduced motion.
7. **Progressive disclosure in staged patterns.** Funnels and step patterns show only what the current step needs, with a progress indicator and a mini-CTA per step.
8. **Mobile is the pattern, not a squeeze of it.** Bento grids stack, comparison tables become cards or scroll in their own container, horizontal journeys fall back to vertical. A pattern that only works with hover does not work on a phone — every hover-revealed value must also be reachable without a pointer.
9. **Forms ask for the minimum.** Capture patterns earn each field; an email plus one qualifier converts, a six-field form does not. The field rules themselves are the stack's `forms`.
10. **The page has a real navigation and a real footer** unless the pattern explicitly strips them (Minimal Single Column removes nav clutter deliberately). "No nav" is a pattern decision, never an omission.

## Working the pattern

1. **Name the visitor's decision** in one sentence, then pick the family, then query `--domain landing` with the product terms and that decision.
2. **Take the row whole** — section order, CTA placement, color strategy, effects, conversion rules.
3. **Map each section to content that exists.** A pattern section with no real content becomes a fake one (three invented testimonials, a logo wall of clip art) — drop the section or change pattern. Fabricated proof is a legal problem as well as a design one; [`design-ethical-patterns`](../ethical-patterns/SKILL.md) owns that line.
4. **Hand the look to `design-visual-identity`** — the pattern says *hero*, the identity says *what the hero is*.
5. **Hand the copy to [`design-ux-writing`](../ux-writing/SKILL.md)** — section headings and CTA labels are voice decisions, and "Get started" is rarely the best label the page can carry.

## Review checklist

- The pattern was **chosen from the corpus against the visitor's decision**, not defaulted to hero-features-CTA.
- The row was taken **whole** — section order, CTA placement, color strategy, effects, and conversion rules all applied.
- **Proof precedes the ask**; the primary CTA appears in the hero region and again after the argument.
- Exactly **one primary action**; secondary actions are visually secondary.
- **CTA label contrast ≥ 4.5:1** against its own fill, verified rather than assumed.
- Every **auto-moving element has prev/next + play/pause**, pauses on hover and focus, and stops under reduced motion.
- **Hover-only value is also reachable without a pointer**; the pattern has a real mobile form, not a squeeze.
- Every section maps to **content that actually exists** — no invented testimonials, no placeholder logo wall.
- Staged patterns show a **progress indicator** and disclose one step at a time.

## Related

- [`design-ui-ux-pro-max`](../ui-ux-pro-max/SKILL.md) — the `landing` domain that is this skill's catalog.
- [`design-visual-identity`](../visual-identity/SKILL.md) — the marketing lane's look: hero thesis, signature element, the one risk.
- [`design-ux-patterns`](../ux-patterns/SKILL.md) — the application counterpart: IA, shell, page anatomy.
- [`design-motion`](../motion/SKILL.md) — the tier and preset behind the recommended-effects column.
- [`design-ux-writing`](../ux-writing/SKILL.md) — section headings, value props, and CTA labels.
- [`design-ethical-patterns`](../ethical-patterns/SKILL.md) — urgency, scarcity, and proof claims that cross into deceptive design.
