# MUI (Material UI) — default

Free (MIT) Material-Design component library, the largest React component ecosystem, `theme` + `sx` styling and the MUI X DataGrid. The library default unless a decision-matrix row fits better.

**Version:** pin `@mui/material` to your React line. **MUI v7** (stable Mar 2025, [release notes](https://mui.com/blog/material-ui-v7-is-here/)) is current — clean ESM/CJS exports and improved App-Router support; it works with React 18 and 19. MUI X (DataGrid, DatePickers, Charts) versions track alongside — the community DataGrid is free (MIT); virtualization, server-side row grouping, and Excel export are **Pro/Premium**. Use `@mui/material-nextjs` for the App Router SSR style flush.

## Setup

```bash
pnpm add @mui/material @emotion/react @emotion/styled @mui/material-nextjs @mui/x-data-grid
```

MUI styles with **Emotion** (a CSS-in-JS runtime) — that's why interactive MUI lives in Client Components (see gotchas). The `@mui/material-nextjs` package flushes Emotion's styles during SSR so there's no unstyled flash on the App Router.

## Provider — a `'use client'` island, once at the root

The theme provider relies on React Context + the Emotion runtime, so it **cannot** be a Server Component. Put it in one client `Providers` component rendered from `app/layout.tsx`:

```tsx
// app/providers.tsx
'use client';
import { ThemeProvider, CssBaseline } from '@mui/material';
import { AppRouterCacheProvider } from '@mui/material-nextjs/v15-appRouter';
import { theme } from '@/theme';                     // one theme object — styling skill owns it

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <AppRouterCacheProvider>                          {/* SSR style flush, App Router */}
      <ThemeProvider theme={theme} defaultMode="system">  {/* v7 built-in system dark mode */}
        <CssBaseline />
        {children}
      </ThemeProvider>
    </AppRouterCacheProvider>
  );
}
```

```tsx
// app/layout.tsx — a Server Component that renders the client island
import { Providers } from './providers';
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="en" suppressHydrationWarning><body><Providers>{children}</Providers></body></html>;
}
```

**Vite SPA lane:** no `AppRouterCacheProvider` — just wrap `<App/>` in `<ThemeProvider>` in `main.tsx`.

## Theming + dark mode

One `theme` object at the root; feed its palette from the [`design/frontend-design`](../../../../../design/frontend-design/SKILL.md) token system ([`styling`](../../styling/SKILL.md) owns the mapping). MUI v7's `createTheme` supports a **CSS-variables** color-scheme mode so dark mode is a class/attribute swap with no flash:

```tsx
// theme.ts
import { createTheme } from '@mui/material/styles';
export const theme = createTheme({
  cssVariables: { colorSchemeSelector: 'data' },   // emit CSS vars; dark under [data-mui-color-scheme="dark"]
  colorSchemes: { light: true, dark: true },
  palette: { primary: { main: '#1867c0' } },
  typography: { fontFamily: 'var(--font-body), sans-serif' },
});
```

Toggle with the `useColorScheme()` hook (`{ mode, setMode }`) from a client control; `defaultMode="system"` follows the OS. Set `cssVariables` + `InitColorSchemeScript` (`@mui/material-nextjs`) in `<head>` to stamp the scheme before first paint and avoid the light→dark flash. **Don't hand-set component colors** — set palette tokens, let components derive.

## DataGrid — server-side by default

`<DataGrid>` (MUI X) with server-side paging/sort/filter — never load a full table client-side. The grid is a client component; drive it from a [`data-access`](../../data-access/SKILL.md) call:

```tsx
'use client';
import { DataGrid, type GridColDef, type GridPaginationModel } from '@mui/x-data-grid';

const columns: GridColDef<OrderDto>[] = [
  { field: 'number', headerName: 'Order #', flex: 1 },
  { field: 'total', headerName: 'Total', type: 'number', valueFormatter: (v) => formatCurrency(v) },
];

export function OrdersGrid() {
  const [model, setModel] = useState<GridPaginationModel>({ page: 0, pageSize: 25 });
  const { rows, rowCount, loading } = useOrders(model);   // TanStack Query hook — data-access
  return (
    <DataGrid
      columns={columns} rows={rows} rowCount={rowCount} loading={loading}
      paginationMode="server" sortingMode="server" filterMode="server"
      paginationModel={model} onPaginationModelChange={setModel}
      pageSizeOptions={[25, 50, 100]}
      data-testid="Orders.Grid"
    />
  );
}
```

`paginationMode="server"` (plus `sortingMode`/`filterMode`) makes the grid emit callbacks instead of slicing in the browser; translate the model/sort/filter into the `data-access` query. Row virtualization on huge grids is a **Pro** feature.

## Dialog + snackbar

MUI ships components, not a global service — compose a `<Dialog>` and use `notistack` (or your own toast context) for snackbars. Both are client:

```tsx
'use client';
import { Dialog, DialogTitle, DialogContent, DialogActions, Button } from '@mui/material';
import { useSnackbar } from 'notistack';

function DeleteButton({ order }: { order: OrderDto }) {
  const [open, setOpen] = useState(false);
  const { enqueueSnackbar } = useSnackbar();
  async function confirm() {
    await deleteOrder(order.id);                          // Server Action / mutation — data-access
    setOpen(false);
    enqueueSnackbar(`Order ${order.number} deleted`, { variant: 'success' });
  }
  return (
    <>
      <Button color="error" onClick={() => setOpen(true)} data-testid="Orders.Delete">Delete</Button>
      <Dialog open={open} onClose={() => setOpen(false)} data-testid="Orders.DeleteDialog">
        <DialogTitle>Delete order {order.number}?</DialogTitle>       {/* name the object — ui-conventions */}
        <DialogContent>This cannot be undone.</DialogContent>
        <DialogActions>
          <Button onClick={() => setOpen(false)}>Cancel</Button>
          <Button color="error" onClick={confirm} data-testid="Orders.DeleteConfirm">Delete</Button>
        </DialogActions>
      </Dialog>
    </>
  );
}
```

Mount `<SnackbarProvider>` (notistack) once inside the client `Providers` island.

## RSC gotchas

| Symptom | Cause | Fix |
|---|---|---|
| `useContext`/`createContext` error, or "hooks can only be used in Client Components" | An interactive MUI component (Button with `onClick`, Dialog, Menu) rendered in a Server Component | Move it under a `'use client'` boundary; the provider is a client island |
| Unstyled flash then styled on hydrate (App Router) | Emotion styles not flushed during SSR | Wrap in `AppRouterCacheProvider` from `@mui/material-nextjs` |
| Theme flashes light then dark on load | Color scheme applied after first paint | `cssVariables` + `InitColorSchemeScript` in `<head>` to stamp before paint |
| Grid loads the whole table then pages in the browser | `paginationMode`/`sortingMode`/`filterMode` left at `client` | Set them to `server` and wire the callbacks to a `data-access` query |
| `sx`/`styled` types error | `@emotion/react`/`@emotion/styled` missing | Install both Emotion peers |

**`data-testid` on MUI controls:** inline `data-testid="..."` forwards to the rendered root for most components; for slotted internals use `slotProps` (e.g. `slotProps={{ root: { 'data-testid': '...' } }}`). Full rules in [`testability`](../../testability/SKILL.md).

## Validation

- `AppRouterCacheProvider` + `ThemeProvider` mount once in a client `Providers` island; no unstyled flash on the App Router.
- A `<Dialog>` and a snackbar fire from a client island (they can't be called from an RSC).
- `<DataGrid>` pages/sorts/filters **server-side** (`paginationMode="server"`; Network shows one page).
- Dark mode toggles via `useColorScheme()` and follows OS, no light→dark flash.
- `data-testid` set inline appears on the rendered root in DevTools.
