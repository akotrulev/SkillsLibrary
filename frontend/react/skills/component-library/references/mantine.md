# Mantine

Free (MIT), the **richest free React component set** — 130+ components, 100+ hooks, a free `mantine-datatable`, DatePickers, Charts, Notifications, and modals — with superb TypeScript DX. Pick this when a rich free component set (especially a free DataTable) is the deciding factor. It plays Radzen's role from the Blazor stack.

**Version:** pin `@mantine/core` to your React line. **Mantine v8** (May 2025, [v8.0.0](https://mantine.dev/changelog/8-0-0/)) and **v9** (Mar 2026) are current; both support the App Router. Mantine styles with **CSS (real stylesheets + CSS variables)**, not a CSS-in-JS runtime — lighter than Emotion, but it still needs its provider and a pre-paint color-scheme script.

## Setup

```bash
pnpm add @mantine/core @mantine/hooks
# optional families: @mantine/notifications @mantine/modals @mantine/dates mantine-datatable
```

Import the core stylesheet once (root layout) and add the PostCSS preset so Mantine's mixins/breakpoints resolve:

```bash
pnpm add -D postcss postcss-preset-mantine postcss-simple-vars
```

```tsx
// app/layout.tsx (root)
import '@mantine/core/styles.css';
// import '@mantine/notifications/styles.css';  // if used
```

## Provider — a `'use client'` island + `ColorSchemeScript`

`MantineProvider` uses React Context, so it's a Client Component. `ColorSchemeScript` (a Server Component helper) stamps the color scheme into `<html>` before first paint — put it in `<head>`:

```tsx
// app/layout.tsx — Server Component
import { ColorSchemeScript, mantineHtmlProps } from '@mantine/core';
import { Providers } from './providers';

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" {...mantineHtmlProps}>
      <head><ColorSchemeScript defaultColorScheme="auto" /></head>
      <body><Providers>{children}</Providers></body>
    </html>
  );
}
```

```tsx
// app/providers.tsx
'use client';
import { MantineProvider } from '@mantine/core';
import { Notifications } from '@mantine/notifications';
import { theme } from '@/theme';

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <MantineProvider theme={theme} defaultColorScheme="auto">
      <Notifications />                {/* toast portal — once */}
      {children}
    </MantineProvider>
  );
}
```

**Vite SPA lane:** no `ColorSchemeScript` server helper — Mantine reads/persists the scheme client-side; just wrap `<App/>` in `<MantineProvider>`.

## Theming + dark mode

One `theme` from `createTheme`, fed by the [`design/visual-identity`](../../../../../design/visual-identity/SKILL.md) tokens ([`styling`](../../styling/SKILL.md) maps them). Mantine emits **CSS variables** from the theme, so your CSS Modules can read `var(--mantine-color-*)`:

```tsx
// theme.ts
import { createTheme } from '@mantine/core';
export const theme = createTheme({
  primaryColor: 'brand',
  colors: { brand: ['#e7f0fb', /* …10 shades… */ '#0d47a1'] },  // Mantine wants a 10-shade tuple
  fontFamily: 'var(--font-body), sans-serif',
});
```

**Dark mode:** `defaultColorScheme="auto"` follows the OS; toggle with `useMantineColorScheme()` (`{ colorScheme, setColorScheme, toggleColorScheme }`) from a client control. `ColorSchemeScript` prevents the flash. Author the dark palette deliberately — don't invert ([`styling`](../../styling/SKILL.md) owns the dark-palette discipline).

## DataTable — server-side by default

`mantine-datatable` is the free grid; drive paging/sort from a [`data-fetching`](../../data-fetching/SKILL.md) call, never load a full table:

```tsx
'use client';
import { DataTable } from 'mantine-datatable';

export function OrdersTable() {
  const [page, setPage] = useState(1);
  const [sort, setSort] = useState({ columnAccessor: 'number', direction: 'asc' as const });
  const { rows, total, fetching } = useOrders({ page, pageSize: 25, sort });   // TanStack Query — data-fetching
  return (
    <DataTable
      records={rows} totalRecords={total} recordsPerPage={25} page={page} onPageChange={setPage}
      sortStatus={sort} onSortStatusChange={setSort} fetching={fetching}
      columns={[
        { accessor: 'number', title: 'Order #', sortable: true },
        { accessor: 'total', title: 'Total', textAlign: 'right', render: (o) => formatCurrency(o.total) },
      ]}
      data-testid="Orders.Grid"
    />
  );
}
```

Paging/sort are controlled props → callbacks → your server query. For very long lists, virtualize with `@mantine/core` `ScrollArea` + windowing, still server-paged.

## Dialog + notifications

`@mantine/modals` gives a **modal manager** (imperative confirm/alert) and `@mantine/notifications` gives toasts:

```tsx
'use client';
import { modals } from '@mantine/modals';
import { notifications } from '@mantine/notifications';

function deleteOrder(order: OrderDto) {
  modals.openConfirmModal({
    title: `Delete order ${order.number}?`,               // name the object — ui-rules
    children: 'This cannot be undone.',
    labels: { confirm: 'Delete', cancel: 'Cancel' },
    confirmProps: { color: 'red', 'data-testid': 'Orders.DeleteConfirm' },
    onConfirm: async () => {
      await deleteOrderAction(order.id);                  // Server Action / mutation — data-fetching
      notifications.show({ color: 'green', message: `Order ${order.number} deleted` });
    },
  });
}
```

Mount `<ModalsProvider>` (from `@mantine/modals`) and `<Notifications />` once inside the client `Providers` island.

## RSC gotchas

| Symptom | Cause | Fix |
|---|---|---|
| Context/hook error in a Server Component | An interactive Mantine component rendered in an RSC | Move under a `'use client'` boundary; provider is a client island |
| Color-scheme flash on load | `ColorSchemeScript` missing from `<head>` | Add `<ColorSchemeScript>` (App Router) so the scheme is stamped pre-paint |
| Styles missing / components unstyled | `@mantine/core/styles.css` (and family stylesheets) not imported | Import the core stylesheet once in the root layout |
| PostCSS mixins (`light-dark`, breakpoints) don't resolve | `postcss-preset-mantine` not configured | Add the preset to `postcss.config.cjs` |
| Grid loads whole table then pages client-side | `page`/`sortStatus` not wired to a server query | Control them and translate to a `data-fetching` call |

**`data-testid` on Mantine controls:** inline `data-testid="..."` forwards to the rendered root (Mantine spreads rest props). Full rules in [`test-ids`](../../test-ids/SKILL.md).

## Validation

- `@mantine/core/styles.css` imported once; `ColorSchemeScript` in `<head>`; `MantineProvider` in a client island.
- A confirm modal (`@mantine/modals`) and a notification fire from a client island.
- `mantine-datatable` pages/sorts **server-side** (Network shows one page).
- Dark mode toggles via `useMantineColorScheme()` and follows OS, no flash.
- `data-testid` set inline appears on the rendered root in DevTools.
