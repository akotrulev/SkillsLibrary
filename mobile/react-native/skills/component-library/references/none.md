# StyleSheet + your own atoms (default)

No third-party UI kit. You compose RN primitives (`View`, `Text`, `Pressable`, `TextInput`) and a small atom layer (`AppText`, `PrimaryButton`) over `StyleSheet` and a token object. **Native controls that must look and behave like the platform** — pickers, switches, date pickers, context menus, sheets — come from **Expo UI** ([`expo-ui`](expo-ui.md)), which is part of this default, not an alternative to it.

This is the honest default for a bespoke product design: a Material or Tailwind layer fights a custom look, and each kit is a dependency that must earn its place by a need that exists now.

**Compatibility:** New-Architecture compatible. Needs a development build only if you adopt Expo UI. Pairs with [`styling`](../../styling/SKILL.md), which owns the token object, dark-mode swap, type scale and adaptive layout.

## The split

| Need | Source |
|---|---|
| Layout, text, cards, rows, buttons that carry your brand | Your atoms over `StyleSheet` + tokens |
| A control the OS already provides (switch, picker, date, menu, sheet) | Expo UI (`@expo/ui`), or the RN core control |
| Images, lists, menus, modals | [`ui-components`](../../ui-components/SKILL.md) |

## Atoms you own

```tsx
import { StyleSheet, Text, type TextProps } from 'react-native';
import { useTokens } from '@/theme';

type Variant = 'body' | 'title' | 'caption';

export function AppText({ variant = 'body', style, ...rest }: TextProps & { variant?: Variant }) {
  const tokens = useTokens();
  return <Text style={[styles[variant], { color: tokens.color.text }, style]} {...rest} />;
}

const styles = StyleSheet.create({
  title: { fontSize: 20, fontWeight: '600' },
  body: { fontSize: 16 },
  caption: { fontSize: 13, opacity: 0.7 },
});
```

```tsx
import { Pressable, StyleSheet, Text, type PressableProps } from 'react-native';
import { useTokens } from '@/theme';

export function PrimaryButton({ label, ...rest }: PressableProps & { label: string }) {
  const tokens = useTokens();
  return (
    <Pressable
      accessibilityRole="button"
      style={({ pressed }) => [styles.base, { backgroundColor: tokens.color.actionPrimary, opacity: pressed ? 0.85 : 1 }]}
      {...rest}
    >
      <Text style={[styles.label, { color: tokens.color.onAction }]}>{label}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  base: { minHeight: 44, paddingHorizontal: 20, borderRadius: 12, borderCurve: 'continuous', alignItems: 'center', justifyContent: 'center' },
  label: { fontSize: 16, fontWeight: '600' },
});
```

`testID` flows through `...rest` to the `Pressable`, so a caller passes it inline. `minHeight: 44` keeps the touch target at 44 pt.

## Theme provider

There is no third-party provider: your token Context supplies colours, spacing and the scheme. Mount it once in `src/app/_layout.tsx`; the swap mechanics are in [`styling`](../../styling/SKILL.md).

## Dialogs, sheets, menus

Native-first, owned by [`ui-components`](../../ui-components/SKILL.md): RN `Modal` or a `formSheet` route presentation, Expo UI menus and pickers, `expo-image` for images. Do not build a JS menu.

## Gotchas

| Symptom | Cause | Fix |
|---|---|---|
| Text renders nothing or crashes | A bare string outside `<Text>` | All text inside `<Text>` |
| Parent `color` does not reach child text | No CSS cascade | Read the token in each `<Text>` or use `AppText` |
| A dozen near-identical buttons per screen | No shared atom layer | Build the atoms once, compose everywhere |
| Square corners look off on iOS | Missing `borderCurve` | `borderRadius` + `borderCurve: 'continuous'` |
| A hand-rolled switch or date picker | Native control exists | Expo UI |

## Validation

- Builds on iOS and Android; `npx expo-doctor` clean.
- Screens compose atoms, not raw primitives with inline styles.
- Dark mode flips via `useColorScheme()` with no per-component colour edits.
- `testID` on an atom lands on the rendered native view.
