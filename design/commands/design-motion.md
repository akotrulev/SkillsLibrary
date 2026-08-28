---
description: Decide a UI's motion — the product-wide intensity tier, the preset for each trigger (hover, scroll reveal, stagger, page transition, parallax, skeleton, carousel), and the duration/easing/cleanup contract each carries
argument-hint: [the surface or product that needs motion decided]
---

Load and follow the **`design-motion`** skill for this task.

1. `Read` the skill at `${CLAUDE_PLUGIN_ROOT}/design/motion/SKILL.md` (fall back to `design/motion/SKILL.md` when working inside the SkillsLibrary repo itself).
2. Follow it as your operating instructions for the rest of this task — do not improvise past what it specifies.

Query the `gsap` domain of `design-ui-ux-pro-max` before specifying any duration or easing; those values are the specification, not a starting point. Decide the intensity tier once, product-wide — the application lane is Subtle. `prefers-reduced-motion` renders a static final state everywhere, and every loop, listener, timer and ScrollTrigger ships with its teardown.

**The task:**

$ARGUMENTS

If no task was given above, ask what needs motion decided.
