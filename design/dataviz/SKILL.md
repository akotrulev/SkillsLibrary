---
name: dataviz
description: Use when designing the VISUAL of a product dashboard, chart, or report — picking the chart type for the question (comparison / trend / distribution / part-of-whole / relationship / flow) and avoiding the do-not list (pie >5 slices, dual axes, 3D, truncated bar baselines), the viz color system (categorical / sequential / diverging, colorblind-safe, kept SEPARATE from the brand accent and disjoint from status colors), dashboard composition (headline KPIs → charts → detail, stat-tile anatomy, density), and axis / legend / tooltip / direct-labeling discipline. Stack-agnostic taste layer. Triggers "design a dashboard", "which chart for this data", "pick chart colors", "categorical vs sequential palette", "stat-tile / KPI layout". Do NOT use for charting-library code (a stack concern), the queries behind a chart (`data/`), OPS/service dashboards (`observability/grafana-dashboards` — RED/USE), metric DEFINITIONS (`qa/manual/quality-metrics`), or the brand token system (`design/design-tokens`).
---

# Data Visualization — chart & dashboard design

Owns the **design** of product-facing charts, dashboards, and reports, stack-agnostic: which chart answers the question, how viz color is its own system separate from the brand, how a dashboard is composed, and the axis/legend/label discipline that makes a chart readable. This is taste and structure — the *rendering* (a charting library, the data query) is a stack/data concern that consumes these decisions.

**What this skill owns:** the chart-type choice, the viz palette system, dashboard composition and stat-tile anatomy, and chart-element discipline. **What it does not own:** the charting-library code (Recharts / Chart.js / a Blazor chart component — a future stack `charts` skill), the queries that feed a chart (`data/`), metric *definitions* and SLO targets ([`qa/manual/quality-metrics`](../../qa/manual/quality-metrics/SKILL.md)), and **ops/service** dashboards ([`observability/grafana-dashboards`](../../observability/grafana-dashboards/SKILL.md) owns RED/USE/golden-signals — this skill owns *product* dashboards a user reads).

## When to use

- Designing a product dashboard, analytics view, or report screen.
- Choosing the chart type for a given question, or fixing a chart that reads wrong (a pie with 11 slices, a bar chart whose axis starts at 40).
- Picking chart colors — deciding categorical vs sequential vs diverging, and keeping the series palette from colliding with brand or status colors.
- Laying out a KPI row / stat tile, or deciding the hierarchy of a dense dashboard.

Do **not** use it to write the charting-library code, to design an **ops** dashboard (`observability/grafana-dashboards`), or to *define* what a metric means (`quality-metrics`).

## Chart-type selection

Pick the chart from the **question**, not from what looks impressive. Every chart answers exactly one of these; naming the question first eliminates most bad choices.

| The question | Family | Default chart | Notes |
|---|---|---|---|
| **Comparison** — how do discrete categories rank? | categorical | **horizontal bar** | Horizontal when labels are long or there are many categories. Sort by value, not alphabetically, unless the category has a natural order. |
| **Trend** — how does a value move over continuous time? | time series | **line** (area only for cumulative/stacked totals) | Time on X, left→right. One line per series; past ~4 lines, small-multiples beat a spaghetti chart. |
| **Distribution** — how is a single variable spread? | distribution | **histogram** / **box plot** | Histogram for shape, box/violin for comparing spreads across groups. |
| **Part-of-whole** — what share of a total? | composition | **stacked bar** or a single **bar** vs total | A pie is acceptable *only* for ≤3–4 slices summing to a meaningful 100%. Prefer a bar — humans compare lengths better than angles. |
| **Relationship** — do two variables correlate? | correlation | **scatter** (bubble for a 3rd dimension) | Add a trend line only if the correlation is the point. |
| **Flow / movement** — how does volume move between stages/nodes? | flow | **funnel** / **Sankey** | Funnel for a linear drop-off (signup steps); Sankey for many-to-many. |
| **Single number in context** — one KPI vs a target/prior | single value | **stat tile** (+ sparkline / delta) | See stat-tile anatomy below. A number *is* a visualization; don't force a chart. |

**The do-not list** (each defeats the chart's own purpose):

- **Pie/donut with >5 slices**, or slices that don't sum to a meaningful whole → bar chart.
- **Dual Y-axes** — the crossover point is arbitrary and invites false correlation. Use two stacked panels sharing an X-axis, or index both series to a common baseline.
- **3D anything** — depth distorts the very lengths/areas you're asking the reader to compare.
- **Truncated bar baseline** — bars encode value by *length*, so a bar axis MUST start at zero. (A *line* axis may be truncated — it encodes by position — but label it.)
- **Rainbow sequential ramp** — a multi-hue gradient (jet/rainbow) creates false boundaries where the data is smooth. Use a single-hue ramp.
- **A legend when direct labeling fits** — see below.

## Viz color — a system of its own

Chart color is **not** the brand palette reused. It's a separate, purpose-built system with three palette kinds; the brand accent is at most *one* voice in it, never the whole set. Model these as their own semantic token group (`--viz-cat-1…n`, `--viz-seq-*`, `--viz-div-*`) alongside — not inside — the brand tokens ([`design/design-tokens`](../design-tokens/SKILL.md) owns the tier mechanics; this skill owns *what the viz group must contain*).

| Palette | For | Rule |
|---|---|---|
| **Categorical** | distinct groups with no order (product lines, regions) | Max **6–8** hues — human vision can't separate more; beyond that, group the tail into "Other" or switch chart. Maximize perceptual distance; verify colorblind-safe (deuteranopia is ~8% of men). Order-independent. |
| **Sequential** | ordered magnitude, low→high (heatmap, choropleth) | **Single hue**, light→dark. Lightness carries the value; more steps = finer resolution but ~5–7 is the readable ceiling. |
| **Diverging** | a meaningful midpoint with two directions (profit/loss, sentiment, ±target) | Two hues meeting at a neutral middle. The midpoint must be the *real* zero/target, not the data mean. |

**The collision rules — the part teams get wrong:**

- **Categorical series must be disjoint from the semantic status set** (`success`/`danger`/`warning`). If "Series 3" is the same green as your success state, a reader reads meaning into an arbitrary label. Reserve status colors for status; draw categorical hues from elsewhere in the wheel.
- **Don't reuse the brand accent as a data-encoding color** where non-accent series exist — the accented series will read as "the important one." The accent belongs to *the UI chrome around* the chart (selected state, focus), not to an arbitrary data series.
- **Color is the last encoding, not the first.** Position and length are read faster and more accurately than hue. Use color to *group* or *highlight*, not as the sole carrier of a quantitative value where a position could do it.

## Dashboard composition

A dashboard is read top-left first, in an F/Z scan. Compose to that, not as a uniform grid of equal tiles.

1. **Hierarchy, three bands.** Headline **KPIs** (the 3–5 numbers that answer "is it healthy?") across the top → **supporting charts** (the trends/breakdowns that explain the KPIs) in the middle → **detail tables** (the row-level data to drill into) at the bottom. Density increases as the eye travels down.
2. **One dashboard answers one question / serves one role.** An exec overview and an analyst's working view are two dashboards, not one crowded screen. Filters and drill-downs let the analyst dig without burdening the exec's summary.
3. **Stat-tile anatomy** (the KPI card): **label** (what) → **value** (large, the one thing scanned) → **comparison** (delta vs prior period or target, with direction *and* whether up-is-good) → optional **sparkline/trend** for shape. A bare number with no comparison isn't a KPI — it's trivia; "1,204 orders" means nothing without "▲ 12% vs last week."
4. **Information density is deliberate.** Remove chart junk (gridline clutter, redundant legends, borders, backgrounds) so ink maps to data. But don't strip context a reader needs (axis labels, units, the reference line). Whitespace groups related tiles; a heavy border does not.
5. **Every data region has explicit loading / loaded / empty / error states.** A chart that silently renders nothing on no-data reads as "zero" — a lie. The *structure* of those states is the stack's `error-resilience`; the *words* in the empty/error state are [`design/ux-writing`](../ux-writing/SKILL.md) ("No orders yet" + how to get some, not "No data"). This skill's job: mandate that the four states exist and that empty ≠ zero ≠ error.

## Chart-element discipline

- **Direct-label over a legend wherever it fits.** Put the series name at the end of its line, on its bar, or beside its slice. A legend forces a saccade-and-match round-trip for every read; a label is read in place. Reserve legends for dense categorical charts where direct labels would collide.
- **Axes:** label both with units; start a *bar* axis at zero; keep gridlines light and few; format ticks for humans (`1.2k`, `$3M`, not `1200000`). Don't rotate X labels to vertical — angle them, shorten them, or go horizontal-bar.
- **Tooltips add precision, they don't replace the visual.** The chart must be readable without hovering; the tooltip gives the exact figure. Never hide the *only* copy of a value in a tooltip.
- **Annotate the "why."** A callout on the spike ("deploy v2.3", "Black Friday") turns a chart from data into an explanation. One well-placed annotation beats a paragraph beneath.
- **Sort and orient for reading.** Bars sorted by value; time always left→right; the most important series drawn last (on top) or highlighted while others recede to gray.

## Review checklist

- Each chart answers **one** named question, and the chart family matches it (comparison→bar, trend→line, …).
- No item from the **do-not list**: no >5-slice pie, no dual axis, no 3D, no truncated bar baseline, no rainbow ramp.
- Viz palette is its **own** system — right kind (categorical/sequential/diverging) for the data, ≤6–8 categorical hues, colorblind-checked.
- Categorical series are **disjoint from status colors**; the **brand accent** isn't an arbitrary data series.
- Dashboard reads top-down in three bands (**KPIs → charts → detail**); serves one role.
- Stat tiles carry **label + value + comparison** (up-is-good made explicit), not a bare number.
- Every data region has **loading / loaded / empty / error** states; empty ≠ zero.
- **Direct labels** where they fit; axes labeled with units; values not hidden only in tooltips.

## Related

- [`design/design-tokens`](../design-tokens/SKILL.md) — owns the token tier/naming mechanics; the viz palette is a **separate semantic token group** whose *contents* this skill specifies.
- [`design/frontend-design`](../frontend-design/SKILL.md) — the brief-level taste (the brand accent that this skill keeps *out* of the data-series palette).
- [`design/ux-writing`](../ux-writing/SKILL.md) — the microcopy for empty/error states, stat-tile labels, and annotations.
- [`observability/grafana-dashboards`](../../observability/grafana-dashboards/SKILL.md) — **ops/service** dashboards (RED / USE / golden signals). This skill owns *product* dashboards; that one owns operational ones.
- [`qa/manual/quality-metrics`](../../qa/manual/quality-metrics/SKILL.md) — *defines* the metrics and SLO targets a dashboard then visualizes.
- A stack's `error-resilience` ([Blazor](../../frontend/blazor/skills/error-resilience/SKILL.md) · [React](../../frontend/react/skills/error-resilience/SKILL.md)) — the loading/empty/error state *structure* this skill's composition rule depends on.
