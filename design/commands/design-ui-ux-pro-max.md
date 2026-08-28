---
description: Query the vendored UI/UX design-intelligence corpus — 88 styles, 192 palettes, 74 font pairings, 119 UX guidelines, 105 icons, 34 landing patterns, 17 motion presets, 25 chart types, 22 stacks — or generate a full design system from a brief
argument-hint: [a brief to generate a design system from, or a design question to search]
---

Load and follow the **`design-ui-ux-pro-max`** skill for this task.

1. `Read` the skill at `${CLAUDE_PLUGIN_ROOT}/design/ui-ux-pro-max/SKILL.md` (fall back to `design/ui-ux-pro-max/SKILL.md` when working inside the SkillsLibrary repo itself).
2. Follow it as your operating instructions for the rest of this task — do not improvise past what it specifies.

**This corpus is the source of truth for design facts.** Where it and a prose `design/*` skill disagree on a fact, the corpus wins; the prose skill supplies the judgment layered on top.

Choose the smallest search mode that fits: `--design-system` for a new page/product or a system-wide visual direction, one explicit `--domain` for a targeted concern, `--stack` for implementation conventions. One dominant intent and 2–5 meaningful terms per query. Retry once with a narrower rewrite before declaring no match — and never present a zero-result search as if it returned data.

**The task:**

$ARGUMENTS

If no task was given above, ask what to generate or look up.
