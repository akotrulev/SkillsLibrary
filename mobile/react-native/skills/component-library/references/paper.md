# React Native Paper — Material Design

React Native Paper is a batteries-included **Material Design 3** component set (Button, Card, Dialog, Snackbar, TextInput, DataTable, FAB, Appbar) with MD3 theming and solid accessibility. Pick it when you want a Material look out of the box and don't want to build the atom layer yourself. Styling stays **`StyleSheet` + the Paper theme** ([`styling`](../../styling/SKILL.md)); Paper owns component look, you own layout.

**Version:** **Paper v5** (MD3), New-Architecture ready. Install via `npx expo install`; needs `react-native-safe-area-context` and the `PaperProvider` at the root. Verify with `expo-doctor`.

## Setup

```bash
npx expo install react-native-paper react-native-safe-area-context
```

## Provider — once at the root

```tsx
// app/_layout.tsx
import { useColorScheme } from 'react-native';
import { PaperProvider, MD3LightTheme, MD3DarkTheme } from 'react-native-paper';
import { SafeAreaProvider } from 'react-native-safe-area-context';

const light = { ...MD3LightTheme, colors: { ...MD3LightTheme.colors, primary: '#1867c0' } };
const dark  = { ...MD3DarkTheme,  colors: { ...MD3DarkTheme.colors,  primary: '#7ca9e6' } };

export default function RootLayout() {
  const scheme = useColorScheme();
  return (
    <SafeAreaProvider>
      <PaperProvider theme={scheme === 'dark' ? dark : light}>
        {/* <Stack /> */}
      </PaperProvider>
    </SafeAreaProvider>
  );
}
```

Feed the two theme palettes from the [`design/frontend-design`](../../../../../design/frontend-design/SKILL.md) token system ([`styling`](../../styling/SKILL.md) owns the mapping) — dark is a **deliberately-authored second palette** (desaturated primary, not an inversion), swapped by `useColorScheme()`.

## Usage

```tsx
import { Button, Dialog, Portal, Text, Snackbar } from 'react-native-paper';

function DeleteFlow({ onConfirm }: { onConfirm: () => Promise<void> }) {
  const [open, setOpen] = useState(false);
  const [toast, setToast] = useState(false);
  return (
    <>
      <Button mode="contained" onPress={() => setOpen(true)} testID="Orders.Delete">Delete</Button>
      <Portal>
        <Dialog visible={open} onDismiss={() => setOpen(false)} testID="Orders.DeleteDialog">
          <Dialog.Title>Delete this order?</Dialog.Title>            {/* name the object — ui-conventions */}
          <Dialog.Content><Text>This cannot be undone.</Text></Dialog.Content>
          <Dialog.Actions>
            <Button onPress={() => setOpen(false)}>Cancel</Button>
            <Button onPress={async () => { await onConfirm(); setOpen(false); setToast(true); }}
              testID="Orders.DeleteConfirm">Delete</Button>
          </Dialog.Actions>
        </Dialog>
      </Portal>
      <Snackbar visible={toast} onDismiss={() => setToast(false)}>Order deleted</Snackbar>
    </>
  );
}
```

Wrap dialogs/menus in `<Portal>` (Paper mounts them above the tree). `DataTable` is client-side only — for large data, page against a [`data-access`](../../data-access/SKILL.md) call and feed one page at a time; a huge list still belongs in FlashList ([`performance`](../../performance/SKILL.md)), not `DataTable`.

## testID

Paper components forward `testID` to the underlying view — pass it inline. → [`testability`](../../testability/SKILL.md).

## Gotchas

| Symptom | Cause | Fix |
|---|---|---|
| Dialog/menu renders behind content | Not wrapped in `<Portal>` | Wrap in `<Portal>` |
| Safe-area warnings / cut-off Appbar | `SafeAreaProvider` missing | Add it above `PaperProvider` |
| Theme colors don't apply | Component color set inline | Set the theme palette, not per-component `color` props |
| DataTable janky with many rows | Client-side table used as a list | Page server-side; use FlashList for long scrolls |

## Validation

- App builds iOS + Android; `expo-doctor` clean (New-Arch compatible).
- `PaperProvider` (+ `SafeAreaProvider`) mounts once at the root; a Dialog + Snackbar render via `<Portal>`.
- Dark mode swaps the MD3 palette via `useColorScheme()` — a second authored palette, not an inversion.
- `testID` inline lands on the rendered native view.
