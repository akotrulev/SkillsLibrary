---
name: design-tokens
description: Use when building or auditing the variable layer a design system runs on — primitive → semantic → component token tiers, the color/type/spacing/radius/elevation scales, dark mode as a semantic swap. Owns the discipline `design-visual-identity` feeds and `styling` consumes. Triggers "set up design tokens", "define the spacing/type scale", "hardcoded hex values everywhere". Not for palette/type CHOICE (`design-visual-identity`) or CSS mechanics (the stack's `styling`).
---

# Design Tokens — the token system discipline

Owns the **structure** of a design-token system, stack-agnostic: how many tiers, how tokens are named, which categories a web app needs, how theming is a swap set, and what shape the tokens ship in. This is the discipline that sits *between* the taste and the mechanics.

**What this skill owns:** the token *system* — the tier model, the naming rules, the category set and each category's scale shape, theming as a semantic remap, and the delivery format decision. **What it does not own:** the *values* (which blue, which type pairing — that's [`design/visual-identity`](../visual-identity/SKILL.md)'s per-brief taste, or an existing brand via [`design/brand-import`](../brand-import/SKILL.md)), and the *application mechanics* (how a token becomes CSS in a `.razor.css`, how contrast is verified — the stack's `styling` / `accessibility`). Taste picks values → this skill gives them structure → the stack's `styling` renders that structure as CSS.

**Corpus authority.** The facts this skill decides with come from the vendored [`design-ui-ux-pro-max`](../ui-ux-pro-max/SKILL.md) corpus — **it is the source of truth, and where it and this skill disagree on a fact, the corpus wins.** The corpus's `--design-system` output is the **input** to this skill: it emits a concrete `--color-*` set (all 17 semantic slots), a `--space-*` scale tuned by the `--density` dial, and the type roles. Take those values as the primitive/semantic starting point rather than inventing scales:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/design/ui-ux-pro-max/scripts/search.py" "<brief>" --design-system --density <1-10> -f markdown
```

This skill owns the tier discipline — primitive → semantic → component, naming by purpose, dark mode as a semantic swap. The corpus owns what the values are.

## When to use

- Standing up a token system on a new app, or refactoring a flat pile of `--color-*` variables into tiers.
- Deciding whether a project needs two tiers or three, and where a given token belongs.
- Naming tokens, or reviewing a set for value-named smells (`--color-red`, `--blue-500` used directly in components).
- Designing dark mode / brand variants as a swap set rather than a per-component override.
- Choosing the delivery shape: CSS custom properties vs W3C DTCG JSON.

Do **not** use it to *choose* the palette or type pairing (that decision is `visual-identity`), to write the actual CSS that consumes tokens (the stack's `styling`), or to pull a preset theme (`theme-presets`).

## The tier model

Three tiers, each with one job. A token in a lower tier **references** one in the tier above it — never a raw value, never a skip.

| Tier | Holds | Example | Rule |
|---|---|---|---|
| **Primitive** (raw) | a literal value, no meaning | `--blue-600: #1867c0`, `--space-4: 1rem`, `--font-size-16: 1rem` | The only place a literal ever lives. Named by *what it is*. Never referenced directly by a component. |
| **Semantic** (purpose) | an intent, pointing at a primitive | `--color-accent: var(--blue-600)`, `--surface-raised`, `--space-gutter`, `--color-danger` | Named by *why*, not *what*. This is the layer everything else reads. Theming remaps happen here. |
| **Component** (scoped) | a local UI decision, pointing at a semantic | `--button-primary-bg: var(--color-accent)`, `--card-padding: var(--space-gutter)` | Only when a component needs to diverge from the semantic default. Most components should read semantic tokens directly — don't mint a component token per property by reflex. |

**When two tiers are enough.** A small app with one theme and no component library rarely needs the component tier — primitive + semantic covers it, and you add component tokens only when a real divergence appears (a button that must not follow `--color-accent`). Starting with three tiers "to be safe" is over-engineering; the indirection has a cost in traceability. Add the third tier when a component fights the semantic layer, not before.

**The load-bearing rule:** components consume **semantic** (and occasionally component) tokens, **never primitives**. `color: var(--blue-600)` in a component is a primitive that escaped — the same smell as a raw hex literal. The indirection is the whole point: it's what lets a theme swap or an accessibility fix be a one-line edit at the semantic tier.

## Naming

- **Name for *why*, not *what*, at the semantic and component tiers.** `--color-danger`, not `--color-red`. `--surface-raised`, not `--gray-50`. A value-named functional token is a literal wearing a variable's clothes: rename the brand from red to teal and every `--color-red` now lies. Primitives are the *only* tier named by appearance (`--blue-600`) — that's their job.
- **Keep the semantic status set (`success` / `warning` / `danger` / `info`) separate from brand tokens** so a brand color can never silently become a status color, and a status color can't drift when the brand changes. (The brand-vs-functional split *decision* is `visual-identity`'s taste; this skill is where it becomes two disjoint token groups.)
- **One consistent shape:** `--<category>-<role>[-<variant>]` — `--color-text-muted`, `--space-gutter`, `--radius-pill`, `--shadow-raised`. Pick group-hyphen or dot (`color.text.muted` in DTCG JSON) and never mix within a system.
- **One token set app-wide.** No per-feature palette forks. A feature that "needs its own colors" needs a semantic token added to the shared set, not a parallel system.

## The categories a web app needs

A token system is not "colors + a font." Cover these, each with a **scale** (a bounded set of deliberate rungs), not ad-hoc values:

| Category | Scale shape |
|---|---|
| **Color** | primitive ramps (e.g. 50→900 per hue) → semantic roles (`text`, `text-muted`, `surface`, `surface-raised`, `border`, `accent`, status set). Purpose-named at the semantic tier. |
| **Type scale** | one modular ratio (1.2 minor-third dense UI · 1.25 major-third · 1.333 perfect-fourth editorial) generated from one base, plus weight and line-height tokens. The *ratio choice* is taste; the *scale as tokens* is here; the `clamp()` responsive mechanics are the stack's `styling`. |
| **Spacing** | one base unit (commonly 4px / `0.25rem`) and a geometric-ish ramp (`4 8 12 16 24 32 48 64`), not arbitrary pixels. Semantic aliases where useful (`--space-gutter`, `--space-section`). |
| **Radius** | a small set (`none xs sm md lg pill`) — not a free-for-all of one-off `border-radius` values. |
| **Elevation / shadow** | a stepped set (`raised overlay sticky modal`) tied to z-context, not hand-tuned `box-shadow`s per component. |
| **Motion** | duration tokens (`fast base slow`, ~120/200/320ms) and easing tokens (standard/emphasized). Taste decides *whether/where* motion serves the subject (`visual-identity`); the durations/easings live here; the keyframe mechanics are the stack's `motion`. |
| **Breakpoints** | the named breakpoint set as tokens, mirrored wherever the stack reads them (the stack's `responsive-design` owns the C# / query mechanics; the *values* are one source of truth here). |

## Theming as a swap set

Dark mode and brand variants are a **semantic remap only — primitives never fork.** A theme redefines the semantic tier's pointers (or a subset), leaving primitives and component tokens untouched, so every consumer follows automatically:

```css
:root { --color-surface: var(--white); --color-text: var(--gray-900); }        /* light (default) */
:root[data-theme="dark"] { --color-surface: var(--gray-900); --color-text: var(--gray-50); }
```

- **A theme is a second set of assignments, not an inversion.** Never `filter: invert()` or an algorithm that negates each hex — dark mode wants *deliberately* chosen assignments (desaturated accents, no pure-black surface). The *taste* of the dark palette is `visual-identity`; that it's a swap set and not a per-component override is the discipline here.
- **If a component needs a `dark:`-specific rule, a color escaped into a literal.** Fix the token, not the component. Zero component CSS should change when a theme is added.
- **Re-verify contrast per theme** — a pair that passes on white routinely fails on a dark surface. That's the stack's `accessibility` pass, not a reuse of the light-mode result.

## Delivery shape

- **CSS custom properties are the default delivery format.** A web app consumes `var(--token)`; the tier model above maps directly onto nested `:root` definitions. Ship tokens as CSS unless you have a concrete reason not to.
- **W3C DTCG JSON (`$value` / `$type`, `{color.brand.500}` references) only when a pipeline exists** — i.e. Style Dictionary / Terrazzo / Tokens Studio generating platform outputs (CSS + iOS + Android) from one source, or a Figma↔code token sync. The DTCG format reached its first stable version (2025.10) and every major tool reads it, so it's the right *interchange* format — but it's a build input, not something a browser consumes directly. Don't stand up a token pipeline for a single-platform web app that only needs CSS; that's tooling for its own sake.
- Whichever shape ships, the **tier model and naming rules are identical** — DTCG groups are just the JSON encoding of primitive/semantic/component.

## Review checklist

- Every literal value lives in a **primitive**; no raw hex / px / ms below that tier.
- Components read **semantic** (or component) tokens — grep for primitives used directly in component styles → none.
- Functional/status tokens are **purpose-named** (`--color-danger`) and **disjoint from brand** tokens.
- Two tiers unless a real divergence justifies the third — no reflexive component-token-per-property.
- Each category is a **bounded scale**, not ad-hoc values (spacing off one base, radius/shadow/motion from a small set).
- Theming is a **semantic remap**; primitives don't fork; no component CSS changes per theme; no `invert()`.
- Delivery is **CSS custom properties** unless a real multi-platform / Figma-sync pipeline justifies DTCG JSON.

## Related

- [`design/visual-identity`](../visual-identity/SKILL.md) — the taste that *chooses* the palette/type values this system gives structure to (primary theming authority; its per-brief token system feeds this skill's tiers).
- [`design/brand-import`](../brand-import/SKILL.md) — the brownfield path: an existing brand book normalized into this tier model.
- [`design/theme-presets`](../theme-presets/SKILL.md) — preset themes; their palettes are **primitive-tier starting values** you assign semantic roles to.
- A stack's `styling` ([Blazor](../../frontend/blazor/skills/styling/SKILL.md) · [React](../../frontend/react/skills/styling/SKILL.md)) — consumes this structure and owns the CSS mechanics (isolation, `clamp()` type sizing, `var(--token)` application). It defers the tier/naming rules here.
- [`design-ui-ux-pro-max`](../ui-ux-pro-max/SKILL.md) — `--design-system` emits the concrete `--color-*` / `--space-*` values these tiers encode.
