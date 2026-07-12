---
name: iconography
description: Use when choosing, using, or auditing ICONS and social/OG imagery as a SYSTEM for a web app — one icon family per product (stroke vs fill, weight, grid), the library decision (Lucide default · Heroicons · Material Symbols · a component library's own set), inline-SVG discipline (`currentColor`, size via `em`/tokens, decorative-vs-labeled a11y), when an icon may stand alone vs needing a text label, and OG/social-image craft (dimensions, safe zones, thumbnail legibility). Stack-agnostic taste layer; rendering mechanics belong to the stack. Triggers "which icon library should we use", "our icons look inconsistent", "how do I size/color an inline SVG icon", "should this button have an icon or a label", "make an OG/social share image". Do NOT use for the token system (`design/design-tokens`), palette/type taste (`design/frontend-design`), a component library's setup (a stack's `component-library`), the accessible-label mechanics or icon-only-button rule (a stack's `accessibility` / `ui-conventions`), or a logo.
---

# Iconography — icons and social imagery as a system

Owns icons and share imagery as a *system*, stack-agnostic: one family, one library, one set of SVG rules, one policy on when an icon can stand alone. The failure mode this prevents is the app that pulls three icon packs, mixes stroke and fill at random, hardcodes fills, and ships an OG image that's illegible as a thumbnail.

**What this skill owns:** the icon-family decision, the library choice, inline-SVG discipline, the icon+label policy, and OG/social-image craft. **What it does not own:** the *color values* (`design/frontend-design` taste + `design/design-tokens` structure — icons consume `currentColor`, they don't define palette), the accessible-label *mechanics* and the icon-only-button *rule* (a stack's `accessibility` / `ui-conventions` — this skill points there), a component library's install/theming (a stack's `component-library`), or logo *creation* (off-mission).

## When to use

- Picking an icon library for a new app, or reconciling an app that has drifted into several.
- An icon set looks inconsistent — mixed weights, some stroke some fill, sizes that don't align to text.
- Writing or reviewing inline SVG for color/size/accessibility correctness.
- Deciding whether a control can be icon-only or needs a visible label.
- Designing an Open Graph / social share image that must survive being scaled to a feed thumbnail.

## One family per product

An icon set reads as a system only when every glyph shares construction. Pick one family and hold it:

- **Style: stroke *or* fill as the default — not both by accident.** Choose one as the resting style; the other is reserved for a deliberate signal (commonly **filled = selected/active**, stroke = default). Never mix them arbitrarily in the same context.
- **One stroke weight** across the set (≈1.5–2px on a 24px grid). A heavier weight on some icons and a lighter on others is the most common consistency break.
- **One grid.** 24×24 is the web default (divides by 2/4/8/12, scales cleanly to 16 and up); keep ~2px padding so the live area is ~20px and optical sizes stay even. Whatever the family's grid, don't mix icons drawn on different ones.
- **Consistent optical weight and corner radius** — icons should look like they came from one hand. If you must add a glyph the library lacks, match its grid, stroke, and radius or don't add it.

## Library decision

Prefer one well-maintained open library over hand-drawing. Default order:

| Choice | When |
|---|---|
| **Lucide** (default) | General web apps. Large, consistent 24px stroke set, permissive license, framework-agnostic SVG, tree-shakeable per-icon imports. The safe default when nothing else decides. |
| **Heroicons** | Tailwind-flavored projects; ships matched **outline + solid** variants (clean stroke↔fill selected-state pairing) at 24px and a 20px micro set. |
| **Material Symbols** | Material-design apps or when you need the huge coverage / variable-font axes (weight, fill, grade) — heavier, opinionated look. |
| **The component library's own set** | When a stack's `component-library` ([Blazor](../../frontend/blazor/skills/component-library/SKILL.md) · [React](../../frontend/react/skills/component-library/SKILL.md)) is in play (MudBlazor, Fluent, Radzen; MUI, Mantine, Chakra) and ships a coherent icon set — use it rather than layering a second pack on top. One library's chrome + another's icons rarely aligns. |

**Rule: one library, chosen once.** Mixing packs reintroduces exactly the inconsistency the family rule forbids. If the chosen library is missing an icon, draw the one-off to match — don't import a second pack for a single glyph.

## Inline-SVG discipline

Ship icons as inline SVG (or the framework's per-icon component), not `<img>` or icon fonts — inline SVG inherits color, scales crisply, and is accessible.

- **Color via `currentColor`.** The SVG's `stroke`/`fill` is `currentColor` so the icon takes the surrounding text `color` — a semantic token (per `design-tokens`) flows in for free, hover/disabled states follow, and the icon never hardcodes a hex. Hardcoded `fill="#333"` in an icon is the same smell as a raw hex in a component.
- **Size via `em` or a spacing/size token, not magic px.** `width: 1em; height: 1em` ties the icon to its text's font-size so it scales with the type; use a token when it must be fixed. Avoid per-use pixel values scattered through markup.
- **Import from one place.** A single icon module/package, tree-shaken — no `.svg` files copy-pasted ad hoc across the codebase.
- **Accessibility: decorative vs meaningful.**
  - *Decorative* (an icon beside a text label that already says it) → hide from assistive tech (`aria-hidden="true"` / `role="presentation"`, `focusable="false"`). It adds nothing to announce.
  - *Meaningful* (the icon *is* the control's only label — an icon-only button) → it must carry an accessible name. **The label mechanics and the icon-only-button rule are a stack's `accessibility` ([Blazor](../../frontend/blazor/skills/accessibility/SKILL.md) · [React](../../frontend/react/skills/accessibility/SKILL.md)) / `ui-conventions` ([Blazor](../../frontend/blazor/skills/ui-conventions/SKILL.md) · [React](../../frontend/react/skills/ui-conventions/SKILL.md))** — this skill defers there and does not restate them.

## Icon + label

- **Prefer icon *and* label** for primary actions and navigation. An icon alone is ambiguous far more often than designers assume (the classic overflow/kebab, hamburger, and "share" glyphs are the rare well-learned exceptions).
- **An icon may stand alone only when** the meaning is near-universal *and* the control is in a space-constrained, repeated context (toolbar, dense grid row) — and even then it carries an accessible name and ideally a tooltip. The *decision rule* pairs with `ui-conventions`' icon-only-button guidance; don't duplicate it, apply it.
- **Never rely on icon shape or color alone to carry state** (e.g. status). Pair with text or a label — the color-vision rule from `frontend-design` and the "state by color/icon alone" rule from a stack's `accessibility`.
- **One icon, one meaning, app-wide.** The same glyph must not mean "edit" in one place and "settings" in another; a meaning must not switch icons between screens. (Mirrors `ux-writing`'s one-name-one-concept discipline.)

## OG / social image craft

The Open Graph image is the app's thumbnail in every link preview (social, chat, search). Design it to survive scaling, not to be read at full size.

- **Dimensions:** 1200×630 (≈1.91:1) is the safe cross-platform size; it downsamples cleanly to the square/rounded crops some clients apply.
- **Safe zone:** keep essential text and logo within the central ~80% — outer edges get cropped by various clients. Assume a rounded-corner mask.
- **Legibility at thumbnail size:** large type, high contrast, one focal message. Body-copy-sized text vanishes in a feed. Test by shrinking the image to ~200px wide — if the message is gone, it's too busy.
- **On-brand and consistent:** use the app's tokens/typeface (via `design-tokens` / `brand-intake`); a templated per-page OG image (title + logo on a brand field) beats a generic screenshot.
- **Provide the tags:** `og:image` (+ `og:title`/`og:description`) and `twitter:card` — the emission and per-route wiring is the stack's SEO concern ([`seo-discoverability`](../../frontend/blazor/skills/seo-discoverability/SKILL.md)); the *image design* is here.

## Review checklist

- **One icon family**, one style default (stroke *or* fill), one stroke weight, one grid — no mixed packs or weights.
- **One library**, chosen deliberately; the component library's own set used when a stack library is in play; no second pack for a single glyph.
- Icons are **inline SVG** using **`currentColor`** and **`em`/token sizing** — no hardcoded hex, no magic-px, no icon fonts, imported from one place.
- **Decorative icons hidden** from assistive tech; **meaningful icons carry an accessible name** (mechanics deferred to a stack's `accessibility`).
- **Icon-only used only where** meaning is universal and space is constrained; primary actions/nav pair icon **with** label; **never state by icon/color alone**; one glyph = one meaning app-wide.
- **OG image** is 1200×630, essential content in the safe zone, legible at thumbnail size, on-brand; tags emitted by the stack's SEO skill.

## Related

- [`design/frontend-design`](../frontend-design/SKILL.md) — the color/character taste icons inherit (they don't set palette); the color-not-alone rule.
- [`design/design-tokens`](../design-tokens/SKILL.md) — the semantic color tokens that flow into `currentColor` and the size tokens icons use.
- [`design/brand-intake`](../brand-intake/SKILL.md) — supplies the brand tokens an OG image and icon color follow when the brand is fixed.
- A stack's `component-library` ([Blazor](../../frontend/blazor/skills/component-library/SKILL.md) · [React](../../frontend/react/skills/component-library/SKILL.md)) — its bundled icon set is the preferred family when the library is in play.
- A stack's `ui-conventions` ([Blazor](../../frontend/blazor/skills/ui-conventions/SKILL.md) · [React](../../frontend/react/skills/ui-conventions/SKILL.md)) — owns the **icon-only-button** decision rule this skill applies.
- A stack's `accessibility` ([Blazor](../../frontend/blazor/skills/accessibility/SKILL.md) · [React](../../frontend/react/skills/accessibility/SKILL.md)) — owns the accessible-name **mechanics** for meaningful icons.
- A stack's `seo-discoverability` ([Blazor](../../frontend/blazor/skills/seo-discoverability/SKILL.md) · [React](../../frontend/react/skills/seo-discoverability/SKILL.md)) — emits the `og:image` / `twitter:card` tags for the social image designed here.
