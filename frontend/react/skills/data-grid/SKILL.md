---
name: data-grid
description: Use when building, extending, or reviewing a data grid / table — the house `<DataGrid>` on TanStack Table v9 + Tailwind, its server-side paging/sort/filter contract, and the feature surface (columns, selection, grouping, tree data, editing, virtualization, export, a11y, URL state). Triggers "add a table/grid", "our grid loads every row", "column picker", "export to CSV", "replace MUI DataGrid". Not for picking the component library (`component-library`) or the fetch layer (`data-fetching`).
---

# React — Data Grid (the house grid)

**One grid component per app, built once from this skill, reused by every table in that app.** It is *generated per project*, not consumed from a shared package — the conventions are shared, the code is local. Promote to a real published package only when three or more apps are demonstrably fighting over one fix; until then a shared grid package costs more (semver, peer ranges, release cadence) than it saves.

**Default stack — Tailwind lane:** **TanStack Table v9** (headless engine) + **shadcn `<Table>`** markup + **TanStack Virtual** for large sets. TanStack Table is MIT and complete: everything MUI X sells behind Pro/Premium — multi-sort, multi-filter, column pinning, row grouping, aggregation, tree data, cell range selection — is in the free core. You supply the markup and the toolbar; that is the whole trade.

**Version rule — detect before writing a line:**

- **TanStack Table v9** is stable (4 Aug 2026) and the target. Features are **opt-in and tree-shaken**: `useTable({ features, ... })` where `features = tableFeatures({ ... })`. The hook is `useTable`, **not** `useReactTable`.
- **v8 projects**: `useReactTable` + `getCoreRowModel()` is *correct for v8* — never flag it as obsolete. Migrate only when asked; `useLegacyTable` from `@tanstack/react-table/legacy` runs the v8 shape on the v9 engine, and `stockFeatures` restores all-features-included at bundle cost.
- **shadcn's generated `data-table` example still tracks the v8 shape** ([shadcn-ui/ui#11389](https://github.com/shadcn-ui/ui/issues/11389)). Take shadcn's `<Table>` **markup** and write the engine wiring yourself from this skill — do not paste its example wholesale into a v9 app.
- Renames that bite: `sortingFn`→`sortFn`, `columnSizingInfo`→`columnResizing`, `columnPinning.left/right`→`.start/.end`, `table.getState()`→`table.state`.

## When to use

- Adding any table past a static list — anything that sorts, filters, pages, selects, or exports
- Building the app's `<DataGrid>` for the first time, or extending it with a feature it lacks
- Replacing MUI X DataGrid (paywall, or the styling authority moved to Tailwind)
- Reviewing a grid: server-side contract, virtualization, a11y, testability

## When NOT to use

- Choosing the component library / styling authority → [`component-library`](../component-library/SKILL.md), [`styling`](../styling/SKILL.md)
- The query itself — caching, keys, invalidation, streaming → [`data-fetching`](../data-fetching/SKILL.md)
- Editable-cell *validation* rules → [`forms`](../forms/SKILL.md)
- `data-testid` naming mechanics → [`test-ids`](../test-ids/SKILL.md)
- Deterministic sort, empty-state copy, confirmation rules → [`ui-rules`](../ui-rules/SKILL.md)

## Feature surface — parity with MUI X, and who supplies it

`Engine` = TanStack Table v9 core. `You` = markup/UX you write once into the house grid. Depth for every "You" row is in [`feature-recipes`](references/feature-recipes.md).

| Feature | MUI X tier | Ours | Supplied by |
|---|---|---|---|
| Sorting (single + multi) | Community / **Pro** for multi | ✅ | Engine — `rowSortingFeature` |
| Column filters + global search | Community / **Pro** for multi | ✅ | Engine — `columnFilteringFeature`, `globalFilteringFeature` |
| Faceted filter values (distinct + counts) | — | ✅ | Engine — `columnFacetingFeature` |
| Pagination | Community | ✅ | Engine — `rowPaginationFeature` |
| Row selection (+ shift-range) | Community | ✅ | Engine — `rowSelectionFeature` |
| Column visibility (column picker) | Community | ✅ | Engine + your menu |
| Column ordering | **Pro** | ✅ | Engine — `columnOrderingFeature`; drag UX is yours |
| Column resizing | **Pro** | ✅ | Engine — `columnResizingFeature` |
| Column pinning | **Pro** | ✅ | Engine — `columnPinningFeature` (`.start`/`.end`) + sticky CSS |
| Row pinning | Community | ✅ | Engine — `rowPinningFeature` |
| Row expanding / master-detail | **Pro** | ✅ | Engine — `rowExpandingFeature` |
| Tree data (hierarchical rows) | **Pro** | ✅ | Engine — `rowExpandingFeature` + `getSubRows` |
| Row grouping | **Premium** | ✅ | Engine — `columnGroupingFeature` |
| Aggregation (incl. multiple per column) | **Premium** | ✅ | Engine — `rowAggregationFeature` |
| Cell selection / rectangular range + drag | **Premium** | ✅ | Engine — v9 cell selection |
| Cell spanning (row + column) | — | ✅ | Engine — v9 |
| Row virtualization | Community (rows) | ✅ | `@tanstack/react-virtual` |
| Column virtualization | **Pro** | ✅ | `@tanstack/react-virtual` (horizontal) |
| Cell editing | Community | ⚠️ | **You** — engine holds no edit UI |
| CSV export | Community | ⚠️ | **You** — ~20 lines, no dep |
| Excel export | **Premium** | ⚠️ | **You** — `exceljs`/`sheetjs` |
| Print view | Community | ⚠️ | **You** — a `print:` Tailwind variant |
| Clipboard copy/paste | Community | ⚠️ | **You** — over cell selection |
| Keyboard navigation | Community | ⚠️ | **You** — roving tabindex |
| ARIA grid semantics | Community | ⚠️ | **You** — semantic `<table>` first |
| Density toggle | Community | ⚠️ | **You** — one Tailwind class map |
| Pivoting | **Premium** | ❌ | Not built. Needs it? That is a BI surface, not a grid. |

MUI tier boundaries move between releases — verify against MUI's pricing page before quoting them in a decision record.

## The contract

One generic component, one hook, one query shape. Every table in the app goes through it.

```ts
export type GridSort = { id: string; desc: boolean };
export type GridFilter = { id: string; value: unknown };

export type GridQuery = {
  page: number;
  pageSize: number;
  sort: GridSort[];
  filters: GridFilter[];
  search?: string;
};

export type GridPage<TRow> = { rows: TRow[]; total: number };
```

```tsx
type DataGridProps<TRow> = {
  columns: GridColumns<TRow>;
  page: GridPage<TRow> | undefined;
  query: GridQuery;
  onQueryChange: (next: GridQuery) => void;
  status: 'pending' | 'success' | 'error';
  getRowId: (row: TRow) => string;
  testId: string;
  emptyState?: React.ReactNode;
};
```

- **`getRowId` is required, not optional.** It returns a domain id. Row index as an id breaks selection the moment the page changes.
- **The grid owns no data.** It receives a page and emits a query. Fetching belongs to [`data-fetching`](../data-fetching/SKILL.md).
- **`status` is required** so the grid renders all three states itself — no caller can forget one.

## Rules

- **Server-side by default.** `manualPagination`, `manualSorting`, `manualFiltering` are `true` in the house grid, and the row-model factories for those are omitted. Client-side is the opt-in for a bounded set that genuinely fits in memory (a few hundred rows), stated explicitly at the call site.
- **Total comes from the server.** `rowCount`/`total` is a server field. Deriving page count from `rows.length` silently caps the grid at one page.
- **Deterministic sort with a unique tiebreaker.** Every query carries a final sort on a unique column (usually the id), or rows shuffle between pages ([`ui-rules`](../ui-rules/SKILL.md)).
- **Three states, scoped to the rows.** Toolbar, search, filters, and column picker keep rendering when the fetch fails — only the row area swaps to the failed body, and the failure raises the app's persistent top-right notification. A drifted or unparseable response is **failed**, never empty. Never leak `error.message`.
- **Loading is a skeleton of `pageSize` rows**, not a spinner and not a blank region — the grid's height must not collapse, or every fetch shifts the page.
- **Selection survives paging.** Selection state is keyed by domain id and lives above the current page; "select all" across pages is a server-side flag, never a client loop over pages.
- **Grid state that a user would bookmark lives in the URL** — page, sort, filters, search. Column visibility/order/width/density are per-user preferences: `localStorage`, keyed by table id. Never put server rows in a client store.
- **Semantic `<table>` first.** `<table>/<thead>/<tbody>/<th scope>` carries most of the grid's a11y for free. Reach for `role="grid"` + roving tabindex only once you add cell-level keyboard navigation — and then you owe the full keyboard model, not half of it.
- **Sortable headers are `<button>`s inside `<th>`** with `aria-sort` on the `<th>`. A `<th onClick>` is not keyboard reachable.
- **Virtualize past ~200 rendered rows**, not before. Virtualization and `<table>` layout fight; the recipe (fixed row height, `contain`, the sticky-header interaction) is in [`feature-recipes`](references/feature-recipes.md).
- **`data-testid` on the grid root and every interactive control**, PascalCase dot-separated (`Orders.Grid`, `Orders.Grid.Row.<domainId>`). Row locators use the domain id — never the array index, never a GUID that changes per run ([`test-ids`](../test-ids/SKILL.md)).
- **Declare only the features a table uses.** That is the point of v9's `tableFeatures()`. Reaching for `stockFeatures` in new code discards the tree-shaking; it exists for migration.
- **The house grid is one component, not a hierarchy.** No `BaseGrid` → `AppGrid` → `OrdersGrid` chain. Per-table differences are columns and props. An unearned wrapper is a major finding whose fix is to inline it.

## Non-Tailwind lanes

The engine, the query contract, and every rule above are styling-agnostic — only the markup layer changes.

| Styling authority | Markup layer | Note |
|---|---|---|
| **Tailwind + shadcn** (default) | shadcn `<Table>` primitives | The lane this skill is written against |
| **MUI** | Keep MUI X `<DataGrid>` | Don't hand-build a grid inside MUI — you'd be paying for the library and not using it. Map `GridQuery` onto `paginationModel`/`sortModel`/`filterModel` and keep the same contract ([`mui`](../component-library/references/mui.md)) |
| **Mantine** | `mantine-datatable` | Free and complete; same contract mapping |
| **none / headless** | Your own `<table>` + CSS Modules | Identical to the default lane minus shadcn |

Whichever lane, **`GridQuery`/`GridPage` stay the same** so the fetch layer and the API contract never depend on the UI choice.

## Anti-patterns

| Smell | Fix |
|---|---|
| Full table fetched, then paged in the browser | `manual*` flags true → server query; `total` from the server |
| `getRowId` defaulted to the row index | Domain id — index breaks selection and test locators across pages |
| Page count derived from `rows.length` | Server-supplied `total` |
| Fetch failure blanks the whole grid incl. toolbar | Scope the failed body to the rows; toolbar/filters keep rendering |
| Loading shows a centred spinner, region collapses | `pageSize` skeleton rows at full grid height |
| Sort with no unique tiebreaker | Append the id column to every sort |
| Column widths/visibility pushed into the URL | URL = page/sort/filters/search; preferences = `localStorage` per table id |
| Server rows copied into Zustand/Context | Query cache owns server state |
| `<th onClick>` for sorting | `<button>` inside `<th>` + `aria-sort` |
| `role="grid"` added with no keyboard model | Semantic `<table>`, or implement roving tabindex fully |
| `stockFeatures` in new v9 code | `tableFeatures({ ...only what this table uses })` |
| shadcn's v8-shaped `data-table` example pasted into a v9 app | Take the markup, write the v9 wiring |
| A wrapper per table (`OrdersGrid extends BaseGrid`) | One `<DataGrid>`; tables differ by columns + props |
| Virtualization added to a 50-row table | Virtualize past ~200 rendered rows |

## Workflow

1. **Detect** the TanStack Table major, the styling authority, and the render target. v8 stays v8 unless the ask is the migration.
2. **Confirm the lane** — MUI/Mantine keep their own grid; Tailwind/none build the house grid. One line in the decision record.
3. **Write the contract** (`GridQuery`, `GridPage`, `getRowId`) before any markup, and agree it with the API owner — server-side paging is a backend contract, not a UI detail.
4. **Build the house `<DataGrid>` once**: the three states, the toolbar slot, sorting, pagination, `data-testid`s. Only the features the first table needs.
5. **Add features on demand** from the parity matrix, each into the same component — read [`feature-recipes`](references/feature-recipes.md) for the one you're adding.
6. **Wire the query** to a [`data-fetching`](../data-fetching/SKILL.md) hook with the URL as the source of truth for page/sort/filters.
7. **Verify** against the checklist below.

## Validation

Inside a `Gate: none` plan task, run none of these checks and report "written, not run"; the plan's gate task runs them.

- Network shows **one page** of rows per interaction — never the whole table.
- Sorting, filtering, and paging each fire exactly one request, and the request carries the tiebreaker sort.
- Killing the API leaves the toolbar, search, and filters rendered; only the rows show the failed body, and one persistent notification appears.
- A slow response shows `pageSize` skeleton rows with no layout shift when data lands.
- Selecting rows on page 1, paging to 2 and back preserves the selection.
- Reloading a bookmarked URL restores page, sort, filters, and search.
- Keyboard alone: tab to a sortable header, `Enter` sorts, `aria-sort` updates; screen reader announces column headers per cell.
- `Orders.Grid` and stable per-row test ids resolve with zero collisions.
- `tsc --noEmit` clean with no `any` in the column definitions.
- Bundle: only declared features present (v9 tree-shaking) — check the grid chunk hasn't pulled `stockFeatures`.

## Handoffs

- Library choice + whether this lane applies at all → [`component-library`](../component-library/SKILL.md)
- The query hook, caching, invalidation after a mutation → [`data-fetching`](../data-fetching/SKILL.md)
- Tailwind tokens, sticky/print CSS, density classes → [`styling`](../styling/SKILL.md)
- Editable-cell schemas + error mapping → [`forms`](../forms/SKILL.md)
- Locator naming + the QA handshake → [`test-ids`](../test-ids/SKILL.md)
- Deterministic sort, empty-state copy, destructive-action confirmation → [`ui-rules`](../ui-rules/SKILL.md)
- Keyboard model, focus management, announcements → [`accessibility`](../accessibility/SKILL.md)
- Row-render cost, memoization, virtualization budgets → [`performance`](../performance/SKILL.md)
- Failure scoping + the notification surface → [`error-handling`](../error-handling/SKILL.md)
- Breakpoint behaviour (grid → card list on narrow) → [`responsive-design`](../responsive-design/SKILL.md)
