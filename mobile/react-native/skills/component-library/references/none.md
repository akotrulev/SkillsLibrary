# none — RN primitives + StyleSheet (default)

No UI kit. You compose the RN primitives (`View`/`Text`/`Pressable`/`TextInput`/`ScrollView`) and build your own atom layer (`AppText`, `PrimaryButton`, `AppTextInput`) on top of `StyleSheet` + a token object. Zero dependency, zero bundle cost, total control — and the design is entirely yours. This is the honest default for a bespoke product design; a Material kit fights a custom look.

**Compatibility:** always New-Architecture compatible and Expo-Go-friendly (no native deps beyond RN itself). Pairs directly with [`styling`](../../styling/SKILL.md), which owns the token object, dark-mode swap, and type scale.

## What you build instead of a kit

A small, owned atom set — the RN analog of shadcn's "own the code," minus even the copy-in step:

```tsx
// components/atoms/AppText.tsx
import { Text, type TextProps, StyleSheet } from 'react-native';
import { useTokens } from '@/theme';                 // styling skill owns the token hook

type Variant = 'body' | 'title' | 'caption';
export function AppText({ variant = 'body', style, ...rest }: TextProps & { variant?: Variant }) {
  const t = useTokens();
  return <Text style={[styles[variant], { color: t.color.text }, style]} {...rest} />;
}
const styles = StyleSheet.create({
  title:   { fontSize: 20, fontWeight: '600' },
  body:    { fontSize: 16 },
  caption: { fontSize: 13, opacity: 0.7 },
});
```

```tsx
// components/atoms/PrimaryButton.tsx — Pressable over TouchableOpacity (ui-conventions)
import { Pressable, Text, StyleSheet, type PressableProps } from 'react-native';
import { useTokens } from '@/theme';

export function PrimaryButton({ label, testID, ...rest }: PressableProps & { label: string }) {
  const t = useTokens();
  return (
    <Pressable
      accessibilityRole="button"
      testID={testID}
      style={({ pressed }) => [styles.base, { backgroundColor: t.color.actionPrimary, opacity: pressed ? 0.85 : 1 }]}
      {...rest}
    >
      <Text style={[styles.label, { color: t.color.onAction }]}>{label}</Text>
    </Pressable>
  );
}
const styles = StyleSheet.create({
  base:  { paddingVertical: 12, paddingHorizontal: 20, borderRadius: 12, borderCurve: 'continuous', alignItems: 'center' },
  label: { fontSize: 16, fontWeight: '600' },
});
```

## Theme provider

There's no third-party provider — your own token Context (or a Zustand store) supplies colors/spacing and the current color scheme. Mount it once at the root `app/_layout.tsx`; drive dark mode off `useColorScheme()`. Full mechanics (token object, dark swap, type scale) live in [`styling`](../../styling/SKILL.md).

```tsx
// app/_layout.tsx
import { useColorScheme } from 'react-native';
import { ThemeProvider } from '@/theme';             // your own token provider (styling skill)

export default function RootLayout() {
  const scheme = useColorScheme() ?? 'light';
  return <ThemeProvider scheme={scheme}>{/* <Stack /> */}</ThemeProvider>;
}
```

## Dialogs, sheets, menus

You don't get these free — but you rarely want a kit's versions anyway. Use the **native-first** components ([`ui-conventions`](../../ui-conventions/SKILL.md)): RN core `Modal` or `@gorhom/bottom-sheet` for sheets, `expo-image` for images, Zeego for native context menus. That skill owns the choices.

## testID

Pass `testID` inline on your atoms; forward it to the underlying primitive (as shown above). Because you own the atom, there's never a wrapper-to-carry-a-testid smell — the prop lands where you route it. → [`testability`](../../testability/SKILL.md).

## Gotchas

| Symptom | Cause | Fix |
|---|---|---|
| Text renders nothing / crashes | A bare string outside `<Text>` | All text goes inside `<Text>` |
| Parent `color` doesn't reach child text | No CSS cascade in RN | Read the token in each `<Text>` (or pass via `AppText` variant) |
| Reinventing a dozen atoms per screen | No shared atom layer | Build the atom set once, compose everywhere |
| Square iOS corners look off | Missing `borderCurve` | `borderRadius` + `borderCurve: 'continuous'` (styling seed rule) |

## Validation

- App builds on iOS + Android; `expo-doctor` clean (no native deps to break New Arch).
- A shared atom layer exists (`AppText`/`PrimaryButton`/inputs) — screens compose atoms, not raw primitives with inline styles.
- Dark mode flips via `useColorScheme()` with no per-component color edits (all read tokens).
- `testID` on an atom forwards to the rendered native view.
