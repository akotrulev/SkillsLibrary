# Data Grid — feature recipes (TanStack Table v9 + Tailwind/shadcn)

Depth for every row of the parity matrix in [`SKILL.md`](../SKILL.md). Read only the section for the feature you are adding. All snippets are **v9** (`useTable`, `tableFeatures`) — on a v8 project use `useReactTable` + `getCoreRowModel()` and the v8 names.

## 1. Base wiring — server-side by default

```tsx
'use client';

import {
  useTable,
  tableFeatures,
  rowSortingFeature,
  rowPaginationFeature,
  columnFilteringFeature,
  createColumnHelper,
  flexRender,
} from '@tanstack/react-table';

const features = tableFeatures({
  rowSortingFeature,
  rowPaginationFeature,
  columnFilteringFeature,
});

export function DataGrid<TRow>({
  columns, page, query, onQueryChange, status, getRowId, testId, emptyState,
}: DataGridProps<TRow>) {
  const table = useTable({
    features,
    columns,
    data: page?.rows ?? [],
    getRowId,
    rowCount: page?.total ?? 0,
    manualPagination: true,
    manualSorting: true,
    manualFiltering: true,
    state: {
      sorting: query.sort,
      columnFilters: query.filters,
      pagination: { pageIndex: query.page, pageSize: query.pageSize },
    },
    onSortingChange: (sort) => onQueryChange({ ...query, sort: withTiebreaker(sort), page: 0 }),
    onColumnFiltersChange: (filters) => onQueryChange({ ...query, filters, page: 0 }),
    onPaginationChange: ({ pageIndex, pageSize }) =>
      onQueryChange({ ...query, page: pageIndex, pageSize }),
  });
  ...
}
```

No `createSortedRowModel`/`createFilteredRowModel`/`createPaginatedRowModel` is registered — registering one while `manual*` is true makes the engine re-process rows the server already processed, and the grid silently sorts one page against itself.

`withTiebreaker` appends the unique id column to every sort so pages don't shuffle:

```ts
const withTiebreaker = (sort: GridSort[]): GridSort[] =>
  sort.some((s) => s.id === 'id') ? sort : [...sort, { id: 'id', desc: false }];
```

## 2. The three states

The failure is scoped to `<tbody>`; the toolbar and header row keep rendering.

```tsx
<table data-testid={`${testId}.Grid`} className="w-full border-collapse">
  <thead className="sticky top-0 z-10 bg-background">{headerRows}</thead>
  <tbody>
    {status === 'pending' && <SkeletonRows count={query.pageSize} columns={table.getAllLeafColumns().length} />}
    {status === 'error' && <FailedRow columns={...} onRetry={...} />}
    {status === 'success' && page?.rows.length === 0 && <EmptyRow>{emptyState}</EmptyRow>}
    {status === 'success' && table.getRowModel().rows.map(renderRow)}
  </tbody>
</table>
```

`SkeletonRows` renders exactly `pageSize` rows at the real row height — that is what stops the layout shift. `FailedRow` shows a retry affordance and never renders `error.message`; the same failure also raises the app's persistent notification ([`error-handling`](../../error-handling/SKILL.md)).

## 3. Sorting — accessible headers

```tsx
<th scope="col" aria-sort={ariaSort(header.column)} className="text-left">
  {header.column.getCanSort() ? (
    <button
      type="button"
      onClick={() => header.column.toggleSorting(undefined, true)}
      data-testid={`${testId}.Sort.${header.column.id}`}
      className="flex items-center gap-1"
    >
      {flexRender(header.column.columnDef.header, header.getContext())}
      <SortIcon direction={header.column.getIsSorted()} />
    </button>
  ) : (
    flexRender(header.column.columnDef.header, header.getContext())
  )}
</th>
```

```ts
const ariaSort = (column: Column) =>
  column.getIsSorted() === 'asc' ? 'ascending'
  : column.getIsSorted() === 'desc' ? 'descending'
  : column.getCanSort() ? 'none' : undefined;
```

The `true` second argument to `toggleSorting` is multi-sort — gate it on shift-click if the API only supports one sort key.

## 4. Filtering, global search, faceting

Add `columnFilteringFeature` (per column) and `globalFilteringFeature` (one search box). Both are `manual` — they emit into `GridQuery` and the server does the work.

**Debounce the search box, not the filters.** 300 ms on free text; a select/date filter fires immediately.

`columnFacetingFeature` supplies distinct values + counts for a filter dropdown — but **only over loaded rows**, which under server-side paging is one page. For real facets the counts come from the API alongside the page:

```ts
export type GridPage<TRow> = {
  rows: TRow[];
  total: number;
  facets?: Record<string, { value: string; count: number }[]>;
};
```

## 5. Pagination

```tsx
<nav aria-label="Pagination" className="flex items-center gap-2">
  <span aria-live="polite">
    {query.page * query.pageSize + 1}–{Math.min((query.page + 1) * query.pageSize, page?.total ?? 0)} of {page?.total ?? 0}
  </span>
  <button disabled={query.page === 0} onClick={() => table.previousPage()} data-testid={`${testId}.PrevPage`}>Previous</button>
  <button disabled={!table.getCanNextPage()} onClick={() => table.nextPage()} data-testid={`${testId}.NextPage`}>Next</button>
</nav>
```

`getCanNextPage()` is only correct because `rowCount` was passed. Without it the grid thinks every page is the last.

For an infinite/lazy lane, swap the pager for `fetchNextPage` from a `useInfiniteQuery` and feed the flattened pages as `data` — the rest of the grid is unchanged.

## 6. Row selection across pages

```tsx
const features = tableFeatures({ rowSelectionFeature, ... });

const table = useTable({
  ...,
  enableRowSelection: true,
  state: { rowSelection: selection },
  onRowSelectionChange: setSelection,
});
```

`selection` is `Record<string, boolean>` keyed by **`getRowId`'s domain id**, and it lives *above* the grid (page state or URL), so paging away and back preserves it. The header checkbox selects the **current page**; "select all N matching" is a separate explicit affordance that sets a flag sent to the server with the current filters — never a loop that fetches every page to tick boxes.

Shift-click range selection is built into v9.

## 7. Column visibility, ordering, resizing, pinning

```ts
const features = tableFeatures({
  columnVisibilityFeature,
  columnOrderingFeature,
  columnSizingFeature,
  columnResizingFeature,
  columnPinningFeature,
});
```

These are **client-only view state** — they never enter `GridQuery`. Persist per table id:

```ts
const [prefs, setPrefs] = useGridPreferences(testId);
```

backed by `localStorage` with a try/catch and a schema check on read (a stale shape from an older release must fall back to defaults, not crash the grid).

**Pinning is `.start`/`.end` in v9** (renamed from `.left`/`.right`). The sticky CSS is yours:

```tsx
className={cn(
  cell.column.getIsPinned() === 'start' && 'sticky left-0 z-20 bg-background',
  cell.column.getIsPinned() === 'end' && 'sticky right-0 z-20 bg-background',
)}
```

Pinned cells need an opaque background or rows show through them while scrolling.

**Resizing** writes `columnResizing` state; apply it via `style={{ width: header.getSize() }}` and set `table-layout: fixed` on the `<table>`, or the browser's auto-layout overrides your widths.

**Reordering**: the engine holds `columnOrder`; the drag UX is yours — `@dnd-kit/sortable` over the header row. Keep a keyboard path (move-left/move-right in the column menu), or reordering is mouse-only.

## 8. Expanding, master-detail, tree data

All three are `rowExpandingFeature`:

```ts
const table = useTable({
  features: tableFeatures({ rowExpandingFeature }),
  getSubRows: (row) => row.children,
  getRowCanExpand: () => true,
  state: { expanded },
  onExpandedChange: setExpanded,
});
```

- **Master-detail**: render an extra `<tr>` after an expanded row spanning all columns.
- **Tree data**: supply `getSubRows`; indent by `row.depth`. Under server-side paging, children are fetched on expand and merged into the row — the expand toggle is a fetch trigger, and it gets its own pending state on that row.

The toggle is a `<button aria-expanded>`; a detail row is `role="region"` labelled by its parent's row header.

## 9. Grouping + aggregation

```ts
tableFeatures({ columnGroupingFeature, rowAggregationFeature, rowExpandingFeature });
```

```ts
columnHelper.accessor('amount', {
  header: 'Amount',
  aggregationFn: 'sum',
  aggregatedCell: ({ getValue }) => <strong>{formatMoney(getValue())}</strong>,
});
```

v9 supports **multiple aggregations per column**. Grouping is client-side over loaded rows — under server-side paging it groups one page, which is almost never what the user means. **Grouped totals across the whole result set come from the API**, as a totals row alongside the page. Say which one you are showing; a "Total" that silently means "total of this page" is a defect.

## 10. Cell selection, clipboard, editing

Cell range selection (rectangular, drag, shift-extend) is in v9's core. Clipboard is yours:

```ts
const copySelection = async () => {
  const tsv = selectedCells
    .map((row) => row.map((cell) => String(cell.getValue() ?? '')).join('\t'))
    .join('\n');
  await navigator.clipboard.writeText(tsv);
};
```

TSV is what spreadsheets expect from a paste. Bind to `Ctrl/Cmd+C` on the grid root and mirror it in a context menu — a keyboard-only shortcut is undiscoverable.

**Editing** has no engine support — the grid holds no edit UI. Keep it explicit:

- A cell enters edit mode on `Enter`/double-click, renders a real input, and commits on `Enter`/blur, cancels on `Escape`.
- Validation is a Zod schema per column ([`forms`](../../forms/SKILL.md)); the error renders in-cell with `aria-invalid` and an accessible description.
- The mutation follows the write rules: double-submit guard, optimistic update with announced rollback, `409` handed back to the cell ([`error-handling`](../../error-handling/SKILL.md)).
- Batch edit ("save all") means a dirty-row map above the grid and one request — not N requests in a loop.

## 11. Virtualization

Past ~200 rendered rows, `@tanstack/react-virtual`:

```tsx
const rows = table.getRowModel().rows;
const virtualizer = useVirtualizer({
  count: rows.length,
  getScrollElement: () => scrollRef.current,
  estimateSize: () => ROW_HEIGHT,
  overscan: 8,
});
```

Virtualization and `<table>` layout fight, and there are only two honest resolutions:

- **Keep `<table>`**: absolutely position the virtual rows inside a spacer `<tr>` of the total height, and fix `table-layout: fixed` + a constant `ROW_HEIGHT`. Variable row heights need `measureElement`.
- **Drop `<table>`** for `role="grid"`/`role="row"`/`role="gridcell"` divs. You then owe the full ARIA grid contract including `aria-rowcount`/`aria-rowindex` — because the DOM no longer contains every row, the screen reader needs those to report position.

Horizontal virtualization (column virtualization) is a second `useVirtualizer` over `table.getVisibleLeafColumns()`, and it does not compose with column pinning for free — pinned columns render outside the virtual window.

Combining virtualization with server-side paging is usually wrong: pick infinite scroll *or* pages, not both.

## 12. Export

**CSV — no dependency:**

```ts
const toCsv = <TRow,>(rows: TRow[], columns: GridColumns<TRow>) =>
  [
    columns.map((c) => quote(c.header)).join(','),
    ...rows.map((row) => columns.map((c) => quote(c.export(row))).join(',')),
  ].join('\r\n');

const quote = (value: string) => `"${String(value ?? '').replace(/"/g, '""')}"`;
```

Prefix a leading `=`, `+`, `-`, or `@` with `'` before quoting — otherwise the export is a CSV-injection vector into the recipient's spreadsheet.

**Excel** needs `exceljs` (or `sheetjs`); load it dynamically so the grid chunk doesn't carry it.

**Export scope is a decision, not a default.** "Export" over a server-paged grid means *the whole filtered result set*, which is a server endpoint taking the same `GridQuery` and streaming a file — not `page.rows`. Exporting the visible page while the button says "Export" is a defect. If only the page is exportable, label it "Export this page".

**Print** is a Tailwind variant on the existing markup: `print:hidden` on the toolbar/pager, `print:table-header-group` on `<thead>` so headers repeat per page, and no virtualization (a virtualized grid prints one screenful).

## 13. Keyboard navigation

Semantic `<table>` + focusable controls covers reading and sorting. Cell-level arrow-key navigation is opt-in, and it is all-or-nothing:

- One tab stop for the grid (roving `tabIndex`), arrows move the focused cell, `Home`/`End` to row ends, `Ctrl+Home`/`Ctrl+End` to grid ends, `PageUp`/`PageDown` by viewport.
- The focused cell must be scrolled into view — under virtualization it may not be mounted, so drive `scrollToIndex` from the focus model.
- Add `role="grid"` only once this exists. Half a keyboard model with full grid semantics is worse for a screen-reader user than a plain table.

## 14. Density

One class map, no per-cell overrides:

```ts
const DENSITY = {
  compact: 'h-8 px-2 text-sm',
  standard: 'h-11 px-3 text-sm',
  comfortable: 'h-14 px-4 text-base',
} as const;
```

Density is a persisted preference, and it changes `ROW_HEIGHT` — feed the same constant to the virtualizer or the virtual window drifts out of sync with the rendered rows.

## 15. URL state

Page, sort, filters, and search are the bookmarkable set:

```ts
const [query, setQuery] = useGridQueryParams(defaults);
```

Serialize compactly (`?p=2&s=name:asc&f=status:open`), **validate on read with a Zod schema**, and fall back to defaults on anything malformed — a hand-edited URL must not crash the grid. Write with `router.replace` while the user is filtering so the back button doesn't step through every keystroke.

## 16. Composability across tables

v9 ships `tableOptions()` and `createTableHook()` to factor shared configuration once while keeping type inference. Use them for the house defaults (the `manual*` flags, `getRowId` wiring, the feature set) so each table declares only its columns — check the current signatures in the v9 docs before writing them. This is the *one* shared seam; it is not licence to build a wrapper component per table.
