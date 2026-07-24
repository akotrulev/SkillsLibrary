---
name: design-brand-intake
description: Use when a project starts from an EXISTING brand — a brand book, style guide, logo, or "our colors are X and Y" — that must become a working token system: normalize into primitive→semantic tiers, gap-fill what the brand never specified in its own voice. Triggers: "we have a brand book, turn it into tokens", "match our existing brand". Do NOT use to invent an identity (`design/frontend-design`), for presets (`design/theme-factory`), or token naming (`design/design-tokens`).
---

# Brand Intake — an existing brand becomes a token system

The brownfield counterpart to [`design/frontend-design`](../frontend-design/SKILL.md). frontend-design *invents* an identity for a blank brief; this skill *consumes* one that already exists — a brand book, a logo lockup, a live marketing site, or a two-line "our colors are #123456 and white" — and turns it into the working token system a web app runs on. The output is a filled-in [`design/design-tokens`](../design-tokens/SKILL.md) tier structure, not a new look.

**What this skill owns:** the extract → normalize → gap-fill pipeline, the fidelity-mode decision, and the discipline of extending a brand *in its own voice*. **What it does not own:** the token tier/naming mechanics (`design/design-tokens`), inventing an identity where none exists (`frontend-design`), preset themes (`theme-factory`), or logo/asset *creation* (off-mission — this reads a logo, it doesn't draw one).

## When to use

- A client or product hands you a brand book / PDF style guide / Figma library and you need a web token system that matches it.
- The only brand input is informal ("primary is our blue #1a56db, headings are Poppins") and you must build a full system around it.
- The brand exists for print or a logo and is missing everything an app needs (states, a type *scale*, spacing, dark mode, sufficient contrast pairs).
- You need to decide, and state, how strictly the app must match the brand.

Do **not** use it to invent a palette/voice from nothing (`frontend-design`), to grab a ready-made theme (`theme-factory`), or as a substitute for the tier/naming rules — those live in `design-tokens` and this skill *feeds* them.

## The pipeline: extract → normalize → gap-fill

### 1. Extract — inventory what the brand actually gives you

Read the source and record only what is *stated*, verbatim, before interpreting anything. A brand book almost never maps 1:1 onto app tokens — catalog the gap up front:

| Brand source usually provides | An app token system also needs |
|---|---|
| 1–3 brand colors + black/white | full neutral ramp, `text-muted`, `border`, `surface` vs `surface-raised`, hover/active states |
| a logo color, maybe a secondary | a **status set** (success/warning/danger/info) a logo palette never includes |
| display + body typeface names | a **type scale** (ratio + rungs), weights, line-heights — brand books give faces, not scales |
| print colors (Pantone / CMYK / spot) | screen **hex/RGB**, and a note that print values are the source of truth, not the reverse |
| logo clear-space, min size | web spacing scale, radius set, elevation set — rarely in a brand book at all |
| one intended look | a **dark-mode** surface/text set the brand never drew |

Flag each missing row explicitly — the gap list *is* the scope of the gap-fill step, and the thing to confirm with the client before you start assigning.

### 2. Normalize — map the given values onto the tier model

Brand values are **primitives**. Assign them **semantic** roles per `design-tokens`; never let a component read a brand primitive directly.

- **Convert to screen space.** Pantone/CMYK/spot are print references — translate to hex/sRGB (bridge via the brand's own hex if the book lists one; otherwise a Pantone→sRGB conversion, and flag it as approximate for sign-off). Keep the original print value in a comment as provenance; the hex primitive is what ships.
- **Name primitives by appearance, assign semantics by purpose** (the `design-tokens` rule): `--brand-blue-600: #1a56db` (primitive) → `--color-accent: var(--brand-blue-600)` (semantic). The brand's "primary" becomes `--color-accent`; its neutrals fill the surface/text/border roles.
- **Don't over-assign.** A single brand color is `--color-accent`, not simultaneously the danger, link, and focus color. Roles that the brand doesn't cover go to the gap-fill step — resist collapsing them onto a brand hue.
- **Keep the status set disjoint from brand tokens** — the `design-tokens` collision rule matters double here, because a brand palette will happily offer a red that is *also* the logo red. A status color that doubles as a brand color drifts the moment either changes.

### 3. Gap-fill — extend in the brand's voice, don't start a second identity

The missing rows get filled by **deriving from the brand**, not by importing a generic default. This is the skill's core judgment: every added value should look like it *could have been* in the brand book.

- **Neutrals:** if the brand gives one gray, build the ramp by holding its hue/temperature and stepping lightness — a warm-gray brand gets a warm-gray ramp, never a default cool `#808080` set.
- **Status colors the brand lacks:** choose a danger/success/warning/info that sit in the brand's saturation and temperature register, then verify contrast on the brand's own surfaces. A muted, dusty brand gets muted status hues, not full-saturation stoplight colors.
- **Type scale:** the brand names the faces; you generate the *scale* — pick one modular ratio (per `design-tokens`) that suits the brand's character (tight 1.2 for a dense utilitarian brand, 1.333 for an editorial one) and generate rungs from a base. Respect any sizes the brand *does* pin (e.g. a fixed H1) as anchors.
- **Dark mode:** a brand book almost never specifies it — derive a dark theme as a semantic remap (per `design-tokens`), desaturating brand accents so they don't vibrate on dark surfaces. This is a *deliberate second set of assignments*, not an inversion.
- **Contrast:** brand color pairs frequently fail WCAG (a pale brand accent on white). You may **not** silently recolor the brand; instead add a darker/lighter primitive *of the same hue* for text use and note it, keeping the original for large/decorative use. Flag the failure — the fix is a client conversation, not a unilateral hue change. (Verification mechanics: the stack's `accessibility`.)

**The line you don't cross:** gap-fill *extends* the brand's language; it never introduces a competing one. If a needed value can't be derived in the brand's voice without clashing, that's a flagged decision for the brand owner — say so rather than inventing.

## Fidelity mode — state it before you assign

Declare which mode you're in at the top of the token file; it changes what "gap-fill" is allowed to do:

- **Strict compliance** (enterprise client, agency deliverable, regulated brand): every stated value is reproduced exactly; nothing brand-visible is altered. Gaps are filled conservatively and **every** derived value is listed for sign-off. Contrast failures are raised as issues, not fixed in place. The brand book wins every tie.
- **Brand-inspired** (internal tool, MVP, "in the spirit of our brand"): the brand sets direction — accent, typeface, character — and you have latitude to modernize scales, choose states, and resolve contrast without a sign-off loop. Faster, looser, appropriate when no one will audit pixel-for-pixel.

When unsure which applies, ask once — it's the single decision that most changes the work, and guessing strict-as-inspired (or the reverse) wastes the most effort.

## Where per-brief taste still applies

A fixed brand constrains the *tokens*, not the *composition*. Even under strict compliance, [`design/frontend-design`](../frontend-design/SKILL.md) still owns:

- **Composition & layout** — the brand says which blue, not how the page is arranged.
- **The signature element** — the one memorable moment of an interface is designed per-brief within the brand's constraints.
- **The hero thesis** — what a given screen is *about* is still a design decision.

So the handoff is: this skill produces the token system from the brand → frontend-design composes *with* those tokens instead of choosing new ones. Say explicitly in the output that composition remains open.

## Example-brand fixture

When you need a worked example or a stand-in brand to demonstrate the pipeline, use the **Anthropic brand** (from Anthropic's `brand-guidelines` skill) as the fixture: primitives `#141413` (dark), `#faf9f5` (light), `#b0aea5` / `#e8e6dc` (grays), accents `#d97757` / `#6a9bcc` / `#788c5d`; **Poppins** (Arial fallback) for headings ≥24pt, **Lora** (Georgia fallback) for body. It's a realistic brownfield case — three accents but no status set, faces but no scale, no dark mode — so it exercises every gap-fill branch. (Provenance noted in [`../ATTRIBUTIONS.md`](../ATTRIBUTIONS.md).)

## Review checklist

- Every **stated** brand value is captured as a primitive with print/original values kept as provenance; nothing brand-visible was silently changed.
- Brand values are **normalized into semantic roles**, not read directly by components; the brand primary is one accent, not five roles at once.
- The **status set is disjoint** from brand tokens even when the brand offers a matching hue.
- Gap-filled values are **derived in the brand's voice** (neutrals hold the brand's temperature; status colors sit in its register; the type scale suits its character) — no generic defaults imported.
- **Dark mode** is a deliberate semantic remap, not an inversion; contrast is **re-verified per theme**.
- **Contrast failures** on brand pairs are flagged for the owner, not fixed by recoloring the brand.
- The **fidelity mode is stated**, and gap-fill latitude matches it.
- The output notes that **composition/signature/hero remain per-brief** (`frontend-design`).

## Related

- [`design/design-tokens`](../design-tokens/SKILL.md) — the tier model, naming, categories, and theming discipline this skill fills in. **Read it first**; this skill is its brownfield input path.
- [`design/frontend-design`](../frontend-design/SKILL.md) — the greenfield counterpart (invents identity) and the still-open owner of composition/signature/hero under a fixed brand.
- [`design/theme-factory`](../theme-factory/SKILL.md) — preset themes; use it when there is *no* brand and you want a fast starting point, not when a real brand must be matched.
- [`design/ux-writing`](../ux-writing/SKILL.md) — a brand's **voice/tone** guidance (if the book includes it) feeds microcopy here.
- A stack's `styling` / `accessibility` — render the resulting tokens as CSS and verify the flagged contrast pairs.
