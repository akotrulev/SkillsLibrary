# shadcn/ui

**Not a dependency — a code-gen kit.** The CLI copies component source (built on **Radix UI** primitives + **Tailwind CSS**) into *your* repo, where you own and edit it. Pick this when the team wants full control of the component code, no runtime component dependency, and is fluent in Tailwind. **The styling authority flips to Tailwind here** (see [`styling`](../../styling/SKILL.md)) — this is the one library branch where Tailwind is correct.

**Version:** shadcn/ui tracks **Tailwind v4** and React 18/19; the CLI (`pnpm dlx shadcn@latest`) generates against your installed Tailwind/React. There's no library version to pin — you pin **Radix** primitive versions and Tailwind. Because you own the copied code, "upgrading" a component is re-running `add` and diffing. It fully supports the App Router; the generated components already carry `'use client'` where they need it.

## Setup

```bash
pnpm dlx shadcn@latest init          # sets up Tailwind v4, CSS variables, components.json, cn() util
pnpm dlx shadcn@latest add button dialog sonner data-table
```

`init` wires `tailwind.config`/`globals.css` with the CSS-variable design tokens (`--background`, `--foreground`, `--primary`, …) and the `cn()` class-merge helper. Components land in `components/ui/` — **your code**, edit freely.

## Provider — mostly none; a client boundary per interactive component

shadcn has **no theme Context provider** — theming is CSS variables in `globals.css`, so a Server Component can render a presentational shadcn component with no boundary. The two things that *do* need a client island:

- **Dark mode** via `next-themes` (a small client provider).
- **Toasts** (`sonner`) — one `<Toaster />` mounted client-side.

```tsx
// components/theme-provider.tsx
'use client';
import { ThemeProvider as NextThemes } from 'next-themes';
export function ThemeProvider({ children }: { children: React.ReactNode }) {
  return <NextThemes attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>{children}</NextThemes>;
}
```

```tsx
// app/layout.tsx
import { ThemeProvider } from '@/components/theme-provider';
import { Toaster } from '@/components/ui/sonner';
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html suppressHydrationWarning><body>
      <ThemeProvider>{children}<Toaster /></ThemeProvider>
    </body></html>
  );
}
```

Individual interactive components (`Dialog`, `DropdownMenu`, `Select`) are Radix-based and already `'use client'` in the generated file — a `<Button onClick>` in your own component still needs *that component* to be `'use client'`.

## Theming + dark mode

Tailwind design tokens as **CSS variables** in `globals.css` — the single source, fed from [`design/frontend-design`](../../../../../design/frontend-design/SKILL.md) ([`styling`](../../styling/SKILL.md) owns the mapping and the Tailwind-as-authority rules):

```css
/* globals.css */
:root { --background: 0 0% 100%; --foreground: 222 47% 11%; --primary: 214 80% 43%; --radius: 0.5rem; }
.dark { --background: 222 47% 11%; --foreground: 210 40% 98%; --primary: 214 90% 66%; }
```

**Dark mode:** `next-themes` toggles the `.dark` class; `defaultTheme="system"` follows the OS, `suppressHydrationWarning` + `next-themes` kills the flash. Author the `.dark` palette deliberately — don't invert.

## DataGrid — compose with TanStack Table

The `data-table` component wires shadcn's `<Table>` markup to **TanStack Table** (headless). For real data set `manualPagination`/`manualSorting`/`manualFiltering` true so it drives a [`data-access`](../../data-access/SKILL.md) server query — never load a full table:

```tsx
'use client';
import { useReactTable, getCoreRowModel } from '@tanstack/react-table';

const table = useReactTable({
  data: rows, columns, rowCount: total,
  manualPagination: true, manualSorting: true, manualFiltering: true,   // server-driven
  state: { pagination, sorting }, onPaginationChange: setPagination, onSortingChange: setSorting,
  getCoreRowModel: getCoreRowModel(),
});
```

Render `table.getRowModel().rows` into shadcn's `<Table>`; add `data-testid="Orders.Grid"` on the table root and stable ids on rows ([`testability`](../../testability/SKILL.md)).

## Dialog + toast (sonner)

```tsx
'use client';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogTrigger } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';

function DeleteDialog({ order }: { order: OrderDto }) {
  return (
    <Dialog>
      <DialogTrigger asChild><Button variant="destructive" data-testid="Orders.Delete">Delete</Button></DialogTrigger>
      <DialogContent data-testid="Orders.DeleteDialog">
        <DialogHeader><DialogTitle>Delete order {order.number}?</DialogTitle></DialogHeader>  {/* name the object */}
        <p>This cannot be undone.</p>
        <DialogFooter>
          <Button variant="destructive" data-testid="Orders.DeleteConfirm"
            onClick={async () => { await deleteOrderAction(order.id); toast.success(`Order ${order.number} deleted`); }}>
            Delete
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
```

## RSC gotchas

| Symptom | Cause | Fix |
|---|---|---|
| Hook/Context error when using `Dialog`/`Select`/`onClick` | Your wrapping component isn't `'use client'` | Add `'use client'` to *your* component (the shadcn part already has it) |
| Dark class flash on load | `next-themes` not wired / no `suppressHydrationWarning` | Wrap in the `next-themes` provider, add `suppressHydrationWarning` on `<html>` |
| Two styling systems fighting | Tailwind here *and* a CSS-in-JS library present | shadcn's authority is Tailwind — don't also run MUI/Chakra ([`styling`](../../styling/SKILL.md)) |
| Grid pages in the browser | TanStack Table `manual*` flags not set | Set `manualPagination`/`manualSorting`/`manualFiltering` and drive `data-access` |
| Copied component drifts from upstream | You own the code; there's no version | Re-run `add` and diff intentionally |

**`data-testid`:** trivial — the component source is yours; add `data-testid` directly on the JSX, or thread a `testId` prop. Full rules in [`testability`](../../testability/SKILL.md).

## Validation

- `init` wired Tailwind v4 + CSS-variable tokens; components live in `components/ui/` (your code).
- Dark mode via `next-themes` toggles the `.dark` class, follows OS, no flash.
- A `Dialog` and a `sonner` toast fire from a client component.
- The composed TanStack Table grid pages/sorts **server-side** (`manual*` true → `data-access`).
- Tailwind is the **only** styling authority (no CSS-in-JS library alongside).
