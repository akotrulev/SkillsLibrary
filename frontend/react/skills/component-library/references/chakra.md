# Chakra UI v3

Free (MIT), accessible component library with a **style-props + recipes** DX. v3 is a **complete rewrite on Ark UI** (headless, WAI-ARIA primitives) with a Panda-inspired styling system. Pick this when you want the ergonomic style-props/recipe API and strong out-of-the-box accessibility.

**Version:** pin `@chakra-ui/react` to your React line. **Chakra v3** ([Announcing v3](https://chakra-ui.com/blog/announcing-v3)) is a breaking rewrite — the API, theming (`createSystem`), and imports differ substantially from v2, and most snippets online are still v2. Verify you're reading v3 docs. v3 works with React 18 and 19 and the App Router. It uses **Emotion** under the hood (CSS-in-JS runtime) — same client-boundary consequence as MUI.

## Setup

```bash
pnpm add @chakra-ui/react @emotion/react next-themes
```

`next-themes` drives color mode (v3 delegates dark mode to it rather than owning a color-mode manager).

## Provider — a `'use client'` island, once at the root

v3's `Provider` (wrapping `ChakraProvider` + the `next-themes` `ThemeProvider`) uses Context + Emotion, so it's a Client Component:

```tsx
// components/ui/provider.tsx
'use client';
import { ChakraProvider } from '@chakra-ui/react';
import { ThemeProvider } from 'next-themes';
import { system } from '@/theme';                     // createSystem output — styling skill owns it

export function Provider({ children }: { children: React.ReactNode }) {
  return (
    <ChakraProvider value={system}>
      <ThemeProvider attribute="class" defaultTheme="system" disableTransitionOnChange>
        {children}
      </ThemeProvider>
    </ChakraProvider>
  );
}
```

```tsx
// app/layout.tsx — Server Component
import { Provider } from '@/components/ui/provider';
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html suppressHydrationWarning><body><Provider>{children}</Provider></body></html>;
}
```

**Vite SPA lane:** same `Provider`, wrapping `<App/>` in `main.tsx`.

## Theming + dark mode

v3 theming is `createSystem` + `defaultConfig` — define tokens (colors, fonts, semantic tokens) in the config, fed from [`design/frontend-design`](../../../../../design/frontend-design/SKILL.md) ([`styling`](../../styling/SKILL.md) maps them):

```tsx
// theme.ts
import { createSystem, defaultConfig, defineConfig } from '@chakra-ui/react';
const config = defineConfig({
  theme: {
    tokens: { colors: { brand: { 500: { value: '#1867c0' } } }, fonts: { body: { value: 'var(--font-body)' } } },
    semanticTokens: { colors: { 'bg.canvas': { value: { base: '{colors.white}', _dark: '{colors.gray.900}' } } } },
  },
});
export const system = createSystem(defaultConfig, config);
```

**Dark mode:** `next-themes` with `attribute="class"` toggles a `.dark` class; `_dark` conditions in semantic tokens resolve automatically. Toggle with `useTheme()` (`setTheme('dark'|'light'|'system')`) from a client control; `defaultTheme="system"` follows the OS and `suppressHydrationWarning` + `next-themes` prevents the flash. Author the dark palette deliberately ([`styling`](../../styling/SKILL.md)).

## DataGrid — Chakra has none; compose or bring one

Chakra ships primitives (`Table`, `Pagination` in v3), **not** a feature-complete DataGrid. For a real grid, pair Chakra's `Table` markup with **TanStack Table** (headless) for sort/filter/pagination logic, server-driven off a [`data-access`](../../data-access/SKILL.md) call:

```tsx
'use client';
import { Table } from '@chakra-ui/react';
// columns/state from TanStack Table with manualPagination + manualSorting = true → server-driven
```

Set `manualPagination`/`manualSorting`/`manualFiltering` true so TanStack Table emits state changes you translate into the server query — never load the full table. (If a batteries-included grid matters more than the style-props DX, reconsider **Mantine**.)

## Dialog + toaster

v3 uses `Dialog` (Ark-based) and a `createToaster` + `<Toaster>` pattern:

```tsx
'use client';
import { Dialog, Button } from '@chakra-ui/react';
import { toaster } from '@/components/ui/toaster';     // createToaster() singleton

function DeleteDialog({ order }: { order: OrderDto }) {
  return (
    <Dialog.Root>
      <Dialog.Trigger asChild><Button colorPalette="red" data-testid="Orders.Delete">Delete</Button></Dialog.Trigger>
      <Dialog.Content data-testid="Orders.DeleteDialog">
        <Dialog.Header>Delete order {order.number}?</Dialog.Header>   {/* name the object — ui-conventions */}
        <Dialog.Body>This cannot be undone.</Dialog.Body>
        <Dialog.Footer>
          <Dialog.ActionTrigger asChild><Button variant="outline">Cancel</Button></Dialog.ActionTrigger>
          <Button colorPalette="red" data-testid="Orders.DeleteConfirm"
            onClick={async () => { await deleteOrderAction(order.id); toaster.success({ title: `Order ${order.number} deleted` }); }}>
            Delete
          </Button>
        </Dialog.Footer>
      </Dialog.Content>
    </Dialog.Root>
  );
}
```

Mount `<Toaster />` once inside the client `Provider` island.

## RSC gotchas

| Symptom | Cause | Fix |
|---|---|---|
| Context/hook error in a Server Component | An interactive Chakra component in an RSC | Move under a `'use client'` boundary; provider is a client island |
| Color-mode flash on load | `next-themes` not wired, or `suppressHydrationWarning` missing on `<html>` | Wrap in `next-themes` `ThemeProvider`, add `suppressHydrationWarning` |
| v2 snippets don't compile | v3 is a rewrite — different imports/theming API | Read v3 docs; `createSystem`, not `extendTheme` |
| Missing a real DataGrid | Chakra has primitives only | Compose `Table` + TanStack Table (server-driven) or pick Mantine |

**`data-testid` on Chakra controls:** inline `data-testid="..."` forwards to the rendered root; for compound parts, put it on the specific part (`Dialog.Content`, `Table.Row`). Full rules in [`testability`](../../testability/SKILL.md).

## Validation

- `ChakraProvider value={system}` + `next-themes` mount once in a client island; no color-mode flash (`suppressHydrationWarning` on `<html>`).
- A `Dialog` and a toast fire from a client island.
- The composed grid pages/sorts **server-side** (TanStack Table `manual*` true → `data-access` query).
- Dark mode toggles via `useTheme()` and follows OS.
- `data-testid` set inline appears on the rendered root in DevTools.
