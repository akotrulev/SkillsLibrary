---
name: design-visual-identity
description: The authority for a SHIPPING web app's visual identity — invents one per-brief design direction (palette, type scale, spacing, layout, motion) and hands it down as a token system a stack's `styling` consumes. Two lanes — a MARKETING page gets a hero, a signature element and one aesthetic risk; an APPLICATION (grids, forms, nav) gets the modern-app recipe (neutral surfaces, one accent, tonal hierarchy, hairline borders) with layout/shell decisions taken from `design-ux-patterns`. Triggers "give this app a look", "make this UI not look AI-generated", "pick a palette and fonts", "restyle this app". Not for CSS mechanics (the stack's `styling`), token naming (`design-tokens`), a brand book (`design-brand-import`), or presets (`design-theme-presets`).
---

# Frontend Design

Approach this as the design lead at a small studio known for giving every client a visual identity that could not be mistaken for anyone else's. The client has already rejected proposals that felt templated, and is paying for a distinctive point of view: make deliberate, opinionated choices about palette, typography, and layout that are specific to *this* brief, and take one real aesthetic risk you can justify — where the lane below allows it.

**Corpus authority.** The facts this skill decides with come from the vendored [`design-ui-ux-pro-max`](../ui-ux-pro-max/SKILL.md) corpus — **it is the source of truth, and where it and this skill disagree on a fact, the corpus wins.** Query it before choosing a style, palette, or type pairing:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/design/ui-ux-pro-max/scripts/search.py" "<product> <industry> <keywords>" --design-system -p "<Project>"
```

That one call returns the resolved landing pattern, style profile (with its light/dark support, performance and accessibility risk), the full 17-slot semantic palette, the font pairing with its imports, the effects, and the anti-patterns to avoid — 88 styles, 192 product palettes, 192 product→style reasoning profiles and 74 pairings behind it. Supplement with `--domain style`, `--domain color`, `--domain typography`, `--domain product`, or `--domain google-fonts` (1934 families) when one dimension needs more options. **Never invent a palette or pairing this skill's judgment can instead be applied to.** The corpus supplies the candidates and their trade-offs; this skill picks the one direction, spends the boldness, and rejects the AI-default look.

## Two lanes: marketing page vs application

Classify the brief first, and say which lane you chose:

- **Marketing lane** — a landing page, a campaign page, a product site: the page's job is to *persuade* in one visit. Everything in *Design principles*, *Composition & atmosphere*, and the "signature element" of the plan applies in full.
- **Application lane** — a product people *use*: lists, detail pages, forms, navigation, dashboards. The job is to get out of the way of the task. The hero, the layout stunt, and the aesthetic risk are wrong here; the section *The application lane — the modern-app recipe* replaces them, and the layout, shell, and page anatomy come from [`design/ux-patterns`](../ux-patterns/SKILL.md), not from this skill's composition section.

A brief can hold both (a marketing site and the app behind it) — then the two get one token system and two lanes, and the app never inherits the landing page's drama.

**What this skill owns:** the *taste* — the visual direction, the per-brief token system, the composition, whether/where motion serves the subject, and the copy voice. **What it does not own:** the *mechanics* — how the tokens become CSS, how the animation is coded, how contrast is verified. Those belong to the stack skills (`styling`, `motion`, `accessibility`, `responsive-design`) and to `design/ux-writing` for the copy rules in depth. This skill is the primary theming authority: its token system feeds `styling`'s CSS custom properties, not the other way around, and `design/theme-presets` is only an optional quick-start when a brief doesn't warrant a bespoke system.

## Ground it in the subject

If the brief does not pin down what the product or subject is, pin it yourself before designing: name one concrete subject, its audience, and the page's single job, and state your choice. If there's anything in memory about the human's preferences, what they're building, or designs made before — use it as a hint. The subject's own world — its materials, instruments, artifacts, and vernacular — is where distinctive choices come from. Build with the brief's real content and subject matter throughout, not lorem ipsum.

## Design principles

**The hero is a thesis** *(marketing lane)*. For a marketing page, open with the most characteristic thing in the subject's world, in whatever form makes sense for it: a headline, an image, an animation, a live demo, an interactive moment. Be deliberate: a big number with a small label, supporting stats, and a gradient accent is the *template* answer — use it only if it's truly the best option for this subject.

**Typography carries the personality of the page.** Pair the display and body faces deliberately — not the same families you'd reach for on any other project — and set a clear type scale with intentional weights, widths, and spacing. Make the type treatment itself a memorable part of the design, not a neutral delivery vehicle. (The *scale-as-tokens* mechanics — modular ratio, `clamp()` responsive type, weight/tracking discipline — are implemented in the stack's `styling` type-scale subsection; decide the treatment here, encode it there.)

**Structure is information.** Structural devices — numbering, eyebrows, dividers, labels — should encode something true about the content, not decorate it. Numbered markers (01 / 02 / 03) are only appropriate if the content actually *is* a sequence (a real process, a typed timeline where order carries information). Question whether a device makes sense before incorporating it.

**Leverage motion deliberately.** In the application lane motion is feedback only — press, hover, region enter/exit — never atmosphere. For a marketing page, think about where and *if* animation serves the subject: a page-load sequence, a scroll-triggered reveal, hover micro-interactions, ambient atmosphere. An orchestrated moment usually lands harder than scattered effects; choose what the direction calls for. Sometimes less is more — extra animation is one of the strongest tells that a design is AI-generated. Decide the motion *intent* here; the implementation (CSS transitions/keyframes, `prefers-reduced-motion` as a hard floor, scroll reveals, view transitions) lives in the stack's `motion` skill.

**Match complexity to the vision.** Maximalist directions need elaborate execution; minimal directions need precision in spacing, type, and detail. Elegance is executing the chosen vision well — not intensity for its own sake.

**Color is a system, not a mood.** Decide the palette as two separate jobs and keep them from colliding:
- **Brand colors carry identity; functional colors carry meaning.** Reserve a consistent semantic set — success / warning / danger / info — and don't let the brand palette overrun it (a red-brand product still needs a danger red that reads as *danger*, distinct from the brand). The mechanics — naming these by purpose (`--color-danger`, not `--color-red`) so meaning survives a theme change — belong to the stack's `styling`; decide the split here.
- **Spend one dominant accent.** If everything is colorful, nothing stands out; a 60-30-10 split (neutral / secondary / accent) is a serviceable default, with the accent reserved for the primary action and the signature element. This is the color face of "spend your boldness in one place."
- **Never let color be the only signal.** ~1 in 12 men have a color-vision deficiency — pair every meaningful color with an icon, label, or shape (the verification is the stack's `accessibility`).
- **Dark mode is a second palette, not an inversion.** If the brief needs it, design dark tokens deliberately — desaturate accents, avoid pure-black surfaces — never programmatically flip the light values. (The token-swap mechanics and per-pair contrast re-check are the stack's `styling` / `accessibility`.)

**Consider the written content carefully.** A brief often lacks real copy, and it's up to you to write it. Generic copy makes a design feel as templated as generic visuals. Follow the writing section below (and `design/ux-writing` for the full discipline).

## Composition & atmosphere

*Marketing lane.* Layout is a design decision, not just a responsive-mechanics problem. The stack's `styling`/`responsive-design` own *how* a grid reflows across breakpoints; this skill owns *what the composition says*:

- **Spatial composition** — consider unexpected layouts: asymmetry, overlap, diagonal flow, deliberate grid-breaking, an off-center focal point. Choose between **generous negative space** (the vision breathes) and **controlled density** (the vision is rich and packed) — commit to one; timid in-between spacing reads as a default. One grid container should own each region's geometry (siblings don't self-position) so the composition holds across breakpoints.
- **Atmosphere & depth** — create atmosphere rather than defaulting to flat solid fills where the direction wants more: gradient meshes, subtle noise/grain textures, geometric patterns, layered transparencies, dramatic or layered shadows, decorative borders, custom cursors. These are how a page gains depth — but they are accessories (see restraint below), and the thin CSS implementation (`background`, `box-shadow`, `filter`, layered pseudo-elements) is `styling`'s.

Avoid the reflexive defaults: purple gradients on white, evenly-distributed timid palettes, predictable card grids, and cookie-cutter component patterns with no context-specific character.

## The application lane — the modern-app recipe

An application looks modern by being quiet and consistent, so the data and the actions are the loudest thing on the screen. Decide these values here; [`design/design-tokens`](../design-tokens/SKILL.md) gives them structure and the stack's `styling` renders them:

- **A neutral surface scale** — base, raised, overlay — carrying nearly every pixel; tinted, not pure white or pure black.
- **One accent**, spent on the primary action and the active nav item; the semantic status set (success / warning / danger / info) stays separate and is never the brand color.
- **Three text tones** — primary, muted, disabled — and weight for emphasis; headings step the type scale, body text does not.
- **Hairline borders over heavy shadows.** Elevation is reserved for what actually floats: menus, drawers, dialogs.
- **A 4/8-px spacing rhythm**, one radius scale, one icon family at one stroke weight.
- **A deliberate dark palette** — desaturated accent, no pure-black surface, contrast re-verified — never an inversion.
- **Typography restraint:** the body face does the work; at most one display face, used on page titles and the brand mark.
- **The signature is a detail, not a stunt** — the empty-state illustration, the brand-mark treatment, one characterful transition — never an asymmetric grid or a hero on a list page.

The three-AI-default-looks critique below applies to this lane too: a cream-and-terracotta admin panel is as templated as a cream-and-terracotta landing page.

## Process: brainstorm, explore, plan, critique, build, critique again

**Calibration** *(perishable — this list is dated, and a stale one is worse than none: it waves through exactly what it exists to catch. **Reviewed 2026-08; re-check by 2027-08.** If today's generated work no longer looks like this, the list is the thing that is wrong.)*

AI-generated and trend-following design right now clusters around six looks — three that arrived with the current image and code models, and three older ones that have not fully cleared:

1. **Bento grid** — modular asymmetric tiles, one large feature block among smaller ones, applied to any content whether or not the tiles differ in weight.
2. **Glassmorphism / Liquid Glass** — frosted translucent panels over a blurred backdrop, spread across cards, nav and page chrome alike. Apple's 2025 Liquid Glass announcement accelerated this precisely as the backlash began; the disciplined form ("Glassmorphism 2.0") keeps glass on the layer that genuinely floats — modals, floating toolbars, notification panels — and nowhere else.
3. **Kinetic / elastic display type** — letterforms stretching, softening and implying motion, used as decoration rather than at a brand moment that earns it.
4. A warm cream background (near `#F4F1EA`) with a high-contrast serif display and a terracotta accent.
5. A near-black background with a single bright acid-green or vermilion accent.
6. A broadsheet layout with hairline rules, zero border-radius, and dense newspaper columns.

All six are legitimate for *some* briefs, but they are defaults rather than choices, and they appear regardless of subject. Where the brief pins down a visual direction, follow it exactly — the brief's own words always win, including when it asks for one of these looks. Where it leaves an axis free, **don't spend that freedom on one of these defaults.** The test for the first three is the same one the whole skill runs on: **what does this effect do for the user here?** Glass on the modal that floats over content is depth doing a job; glass on every card is a filter. A bento grid whose tiles are genuinely different weights of content is structure; one whose tiles are all the same thing is a card grid wearing a costume. Like a hired human designer, balance doing what you're good at against treating each project as a chance to experiment.

**Work in two passes.**

*Pass 1 — brainstorm a compact design plan* from the brief, as a token system with four parts:
- **Color** — the palette as 4–6 named hex values.
- **Type** — the typefaces for 2+ roles: a characterful display face used with restraint, a complementary body face, and a utility face for captions/data if needed.
- **Layout** — a layout concept, described in one-sentence prose plus ASCII wireframes to ideate and compare.
- **Signature** — the single unique element this page will be remembered by, one that embodies the brief (application lane: a detail, per the recipe above).

This four-part plan is the *taste* — the chosen values. Its *structure* — how those values become a tiered token system (primitive → semantic → component), how they're named by purpose, and how theming/dark-mode is a semantic swap set — is owned by [`design/design-tokens`](../design-tokens/SKILL.md); decide the values here, encode them as a system there, and the stack's `styling` renders that system as CSS. This skill is the **greenfield** path (invent an identity); when a project must instead match an *existing* brand book, [`design/brand-import`](../brand-import/SKILL.md) is the brownfield counterpart (composition/signature/hero still come from here even under a fixed brand).

*Then critique the plan against the brief before building.* If any part reads like the generic default you'd produce for *any* similar page — work through a similar prompt in your head and see if you land somewhere similar — revise that part, and say what you changed and why. Only after confirming the relative uniqueness of the plan do you start writing code, following the revised plan exactly and deriving every color and type decision from it.

**CSS specificity when you build.** Structure your selector specificities carefully — it's easy to generate classes that cancel each other out (a type-based `.section` vs an element-based `.cta`), most often with paddings/margins between sections.

Do most of this planning and iteration in your thinking; only show ideas to the user when you have higher confidence they'll delight.

## Restraint and self-critique

**Spend your boldness in one place.** (Marketing lane; in the application lane the boldness budget is the one accent and the signature detail.) Let the signature element be the one memorable thing; keep everything around it quiet and disciplined, and cut any decoration that doesn't serve the brief. Not taking a risk can be a risk itself. Build to a quality floor without announcing it: responsive down to mobile, visible keyboard focus, reduced motion respected.

**Critique your own work as you build** — take screenshots if the environment supports it; a picture is worth 1000 tokens. Apply Chanel's advice: before leaving the house, look in the mirror and **remove one accessory**. Human creators have memory and always try something new — if there's a space to jot notes about what you've tried, it helps future passes. (This restraint check is exactly the visual self-critique the `fe-blazor` agent runs in its Review step.)

## Writing in design

Words appear in a design for one reason: to make it easier to understand, and therefore easier to use. They are design material, not decoration. Bring the same intentionality to copy that you bring to spacing and color. Before writing anything, ask what the design needs to say and how it can best be said to help the person navigate the experience.

- **Write from the end user's side of the screen.** Name things by what people control and recognize, never by how the system is built (a person manages *notifications*, not *webhook config*). Describe what something does in plain terms rather than selling it. Specific beats clever.
- **Active voice as default.** A control says exactly what happens when used: "Save changes," not "Submit." An action keeps the same name through the whole flow — the button that says "Publish" produces a toast that says "Published." The vocabulary of an interface is the signposting for someone navigating it.
- **Failure and emptiness are moments for direction, not mood.** Explain what went wrong and how to fix it, in the interface's voice. Errors don't apologize and are never vague. An empty screen is an invitation to act.
- **Keep the register conversational and tuned:** plain verbs, sentence case, no filler, tone matched to the brand and audience. Let each element do exactly one job — a label labels, an example demonstrates, nothing quietly does double duty.

The full voice/microcopy discipline — and how it fills the error/empty-state slots the engineering stack defines — lives in [`design/ux-writing`](../ux-writing/SKILL.md); this section is the design-side summary.
