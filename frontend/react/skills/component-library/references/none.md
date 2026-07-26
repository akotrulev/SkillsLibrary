# none — headless primitives + your own CSS

No component library. You build a small set of primitives (Button, TextField, Dialog, Toast, DataTable) on **headless behavior libraries** — Radix UI or React Aria for accessibility/interaction, TanStack Table for grids — styled entirely with your own **CSS Modules** ([`styling`](../../styling/SKILL.md) owns this). Pick this when the design is fully bespoke, the payload budget is tight, or a component library would fight the design system rather than serve it.

**Trade-off, stated honestly:** headless libraries give you the hard accessibility parts (focus trap, ARIA wiring, keyboard nav) for free — that's why you reach for them instead of raw `<div>`s — but you own every visual detail, every responsive breakpoint, and the DataGrid features (virtualization, filter UIs) a batteries-included library ships. For most CRUD apps, MUI/Mantine is less work and more accessible out of the box. If you find yourself rebuilding a DataGrid from scratch, reconsider the decision.

## What replaces the library

| Library gives you | Here you use |
|---|---|
| Styled controls | **Your primitives** — Radix/React Aria behavior + **CSS Modules** ([`styling`](../../styling/SKILL.md) owns this) |
| Theme + dark mode | **Design tokens** as CSS custom properties on `:root` / `.dark`, from [`design/visual-identity`](../../../../../design/visual-identity/SKILL.md) — [`styling`](../../styling/SKILL.md) |
| DataGrid | `<table>` + **TanStack Table** (headless: sort/filter/pagination logic) + server paging via [`data-fetching`](../../data-fetching/SKILL.md); virtualize long lists with `@tanstack/react-virtual` |
| Dialog service | **Radix Dialog** (or React Aria) — focus trap + `Escape` + ARIA free — as a `'use client'` primitive |
| Snackbar/toast | **`sonner`** (or Radix Toast) — one `<Toaster />` mounted client-side |

Reaching for Radix/React Aria/TanStack instead of hand-rolling is the whole point: you get the accessibility floor without a full component library's payload or theme system.

## Providers — a client boundary where behavior lives

There's no theme Context to mount (tokens are CSS), so a Server Component can render a purely-presentational primitive with no boundary. The interactive primitives (Dialog, Menu, Toast) are Radix/React Aria based → **`'use client'`**, and the toast host mounts once:

```tsx
// app/layout.tsx
import { Toaster } from 'sonner';
import { ThemeProvider } from '@/components/theme-provider';   // next-themes, for dark mode

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html suppressHydrationWarning><body>
      <ThemeProvider>{children}<Toaster /></ThemeProvider>
    </body></html>
  );
}
```

Your own components that carry state/handlers are `'use client'`; the primitives compose Radix parts that already are.

## Dialog with Radix (focus trap + Escape free)

```tsx
'use client';
import * as Dialog from '@radix-ui/react-dialog';

export function ConfirmDialog({ order, onConfirm }: { order: OrderDto; onConfirm: () => Promise<void> }) {
  return (
    <Dialog.Root>
      <Dialog.Trigger data-testid="Orders.Delete">Delete</Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className={styles.overlay} />
        <Dialog.Content className={styles.content} data-testid="Orders.DeleteDialog">
          <Dialog.Title>Delete order {order.number}?</Dialog.Title>     {/* name the object — ui-rules */}
          <Dialog.Description>This cannot be undone.</Dialog.Description>
          <Dialog.Close>Cancel</Dialog.Close>
          <button onClick={onConfirm} data-testid="Orders.DeleteConfirm">Delete</button>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
```

Radix gives you the focus trap, `Escape`-to-close, scroll lock, and `Title`/`Description` ARIA wiring — most of the accessibility win — while every pixel is your CSS Module.

## DataTable with TanStack Table + server paging + virtualization

```tsx
'use client';
import { useReactTable, getCoreRowModel, flexRender } from '@tanstack/react-table';

const table = useReactTable({
  data: rows, columns, rowCount: total,
  manualPagination: true, manualSorting: true,        // server-driven — data-fetching owns the query
  state: { pagination, sorting }, onPaginationChange: setPagination, onSortingChange: setSorting,
  getCoreRowModel: getCoreRowModel(),
});
// render table.getRowModel().rows into <table data-testid="Orders.Grid">; sortable <th> are <button>s, not click-divs.
```

Windowing for thousands of rows is `@tanstack/react-virtual`; you still push sort/filter/page into the `data-fetching` query. You write the filter UI yourself.

## Theming + dark mode

Design tokens as CSS custom properties, toggled by a `.dark` class (or `data-theme`) via `next-themes` so there's no flash. This is entirely [`styling`](../../styling/SKILL.md)'s domain — read it. No component theme system to configure because there are no library components.

## RSC gotchas

| Symptom | Cause | Fix |
|---|---|---|
| Hook/Context error | A Radix/React Aria primitive (or your stateful component) rendered without `'use client'` | `'use client'` on the interactive primitive/component |
| Focus escapes the dialog | Hand-rolled dialog instead of Radix/React Aria, no focus trap | Use Radix Dialog / React Aria — trap + Escape are free |
| Table janky at thousands of rows | Full list rendered without windowing | `@tanstack/react-virtual` + server paging via `data-fetching` |
| Toast does nothing | `<Toaster/>` not mounted, or called from the server | Mount `<Toaster/>` once client-side; call `toast()` from a client component |

**`data-testid`:** trivial — it's your JSX. Inline `data-testid="..."` directly; your primitives take a `testId` prop and compose suffixes ([`test-ids`](../../test-ids/SKILL.md) rule for custom components).

## Validation

- Interactive primitives are `'use client'`; the toast host mounts once.
- Dialog uses Radix/React Aria (focus trap + Escape + ARIA verified with a keyboard-only pass — a11y is on you here).
- Long lists use TanStack Table + `react-virtual` with server paging via `data-fetching`.
- Dark mode toggles via `next-themes` + tokens ([`styling`](../../styling/SKILL.md)), no flash.
- `data-testid` set inline appears on the rendered root in DevTools.
