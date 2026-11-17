# The two-pass process

The depth behind [`visual-identity`](../SKILL.md)'s *Process* section. Calibration stays in the skill; run it before pass 1.

**Work in two passes.**

*Pass 1 — brainstorm a compact design plan* from the brief, as a token system with four parts:
- **Color** — the palette as 4–6 named hex values.
- **Type** — the typefaces for 2+ roles: a characterful display face used with restraint, a complementary body face, and a utility face for captions/data if needed.
- **Layout** — a layout concept, described in one-sentence prose plus ASCII wireframes to ideate and compare.
- **Signature** — the single unique element this page will be remembered by, one that embodies the brief (application lane: a detail, per the recipe above).

This four-part plan is the *taste* — the chosen values. Its *structure* — how those values become a tiered token system (primitive → semantic → component), how they're named by purpose, and how theming/dark-mode is a semantic swap set — is owned by [`design/design-tokens`](../../design-tokens/SKILL.md); decide the values here, encode them as a system there, and the stack's `styling` renders that system as CSS. This skill is the **greenfield** path (invent an identity); when a project must instead match an *existing* brand book, [`design/brand-import`](../../brand-import/SKILL.md) is the brownfield counterpart (composition/signature/hero still come from here even under a fixed brand).

*Then critique the plan against the brief before building.* If any part reads like the generic default you'd produce for *any* similar page — work through a similar prompt in your head and see if you land somewhere similar — revise that part, and say what you changed and why. Only after confirming the relative uniqueness of the plan do you start writing code, following the revised plan exactly and deriving every color and type decision from it.

**CSS specificity when you build.** Structure your selector specificities carefully — it's easy to generate classes that cancel each other out (a type-based `.section` vs an element-based `.cta`), most often with paddings/margins between sections.

Do most of this planning and iteration in your thinking; only show ideas to the user when you have higher confidence they'll delight.
