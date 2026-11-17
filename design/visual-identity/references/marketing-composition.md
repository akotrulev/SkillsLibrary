# The hero, composition and atmosphere (marketing lane)

The depth behind [`visual-identity`](../SKILL.md)'s *Composition & atmosphere* section, plus the hero principle moved from its *Design principles*. It applies to the marketing lane only.

## The hero is a thesis

**The hero is a thesis** *(marketing lane)*. For a marketing page, open with the most characteristic thing in the subject's world, in whatever form makes sense for it: a headline, an image, an animation, a live demo, an interactive moment. Be deliberate: a big number with a small label, supporting stats, and a gradient accent is the *template* answer — use it only if it's truly the best option for this subject.

## Composition & atmosphere

*Marketing lane.* Layout is a design decision, not just a responsive-mechanics problem. The stack's `styling`/`responsive-design` own *how* a grid reflows across breakpoints; this skill owns *what the composition says*:

- **Spatial composition** — consider unexpected layouts: asymmetry, overlap, diagonal flow, deliberate grid-breaking, an off-center focal point. Choose between **generous negative space** (the vision breathes) and **controlled density** (the vision is rich and packed) — commit to one; timid in-between spacing reads as a default. One grid container should own each region's geometry (siblings don't self-position) so the composition holds across breakpoints.
- **Atmosphere & depth** — create atmosphere rather than defaulting to flat solid fills where the direction wants more: gradient meshes, subtle noise/grain textures, geometric patterns, layered transparencies, dramatic or layered shadows, decorative borders, custom cursors. These are how a page gains depth — but they are accessories (see restraint below), and the thin CSS implementation (`background`, `box-shadow`, `filter`, layered pseudo-elements) is `styling`'s.

Avoid the reflexive defaults: purple gradients on white, evenly-distributed timid palettes, predictable card grids, and cookie-cutter component patterns with no context-specific character.
