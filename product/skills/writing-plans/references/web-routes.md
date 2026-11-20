# Web routes in a plan

Read this when the plan adds or changes a web route. Native mobile and desktop plans skip it.

## Decide the rendering in Step 1, per route

Where an `experience-plan.md` exists, cite its §4a `rendering_plan` and change nothing in it. Otherwise write a `## Rendering per route` section with the `rendering_plan` block from [`backend/_shared/experience-plan/references/rendering-strategy.md`](../../../backend/_shared/experience-plan/references/rendering-strategy.md): the signals, mode, cache and server-rendered content per route, checked against that file's anti-patterns. The pattern chosen is a `D<n>`. Every web `fe` task quotes its routes' entries, and the `Q` journey task asserts their server-rendered content on the raw HTML.

## The self-review criterion

Every web route the plan adds or changes has a rendering entry (mode, cache, signals, server-rendered content) in §4a of the experience plan or in `## Rendering per route`, with no anti-pattern from `rendering-strategy.md`. Its `fe` task quotes that entry, and a `Q` task asserts its server-rendered content on the raw HTML.
