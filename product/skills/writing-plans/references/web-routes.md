# Web routes in a plan

Read this when the plan adds or changes a web route. Native mobile and desktop plans skip it.

## Decide the rendering in Step 1, per route

Where the spec has an `## Experience`, cite its `### Rendering plan` and change nothing in it. Otherwise write a `## Rendering per route` section with the `rendering_plan` block from [`product/skills/experience-plan/references/rendering-strategy.md`](../../experience-plan/references/rendering-strategy.md): the signals, mode, cache and server-rendered content per route, checked against that file's anti-patterns. The pattern chosen is a `D<n>`. Every web `fe` task quotes its routes' entries, and the `Q` journey task asserts their server-rendered content on the raw HTML.

## The self-review criterion

Every web route the plan adds or changes has a rendering entry (mode, cache, signals, server-rendered content) in the spec's `### Rendering plan` or in `## Rendering per route`, with no anti-pattern from `rendering-strategy.md`. Its `fe` task quotes that entry, and a `Q` task asserts its server-rendered content on the raw HTML.
