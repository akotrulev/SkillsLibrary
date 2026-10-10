# Unistyles — StyleSheet with themes and breakpoints

Unistyles 3 keeps the `StyleSheet.create` shape but runs on a C++ engine (Nitro), so a theme change, a rotation or a breakpoint crossing updates native views **without re-rendering React components**. Pick it when you want the default StyleSheet mental model plus themes, breakpoints and variants, without Tailwind. The **styling authority is Unistyles' `StyleSheet`** — never React Native's `StyleSheet` beside it in the same component.

**Version:** Unistyles 3.5 (New Architecture only). `[SDK58]` — re-run `expo-doctor`; Reanimated 4.7 + worklets 0.13 are peers. Needs a **development build** (native code), never Expo Go.

## Setup

```bash
npx expo install react-native-unistyles react-native-nitro-modules react-native-edge-to-edge
```

Add the Babel plugin so `StyleSheet.create` and `useUnistyles` are rewritten:

```js
module.exports = (api) => {
  api.cache(true);
  return {
    presets: ['babel-preset-expo'],
    plugins: [['react-native-unistyles/plugin', { root: 'src' }]],
  };
};
```

## Configure once, before the first render

```ts
import { StyleSheet } from 'react-native-unistyles';
import { darkTheme, lightTheme } from './themes';

const breakpoints = { xs: 0, sm: 360, md: 600, lg: 840, xl: 1200 } as const;

StyleSheet.configure({
  themes: { light: lightTheme, dark: darkTheme },
  breakpoints,
  settings: { adaptiveThemes: true },
});

type AppThemes = { light: typeof lightTheme; dark: typeof darkTheme };
type AppBreakpoints = typeof breakpoints;

declare module 'react-native-unistyles' {
  export interface UnistylesThemes extends AppThemes {}
  export interface UnistylesBreakpoints extends AppBreakpoints {}
}
```

Import this file at the top of the entry (`src/app/_layout.tsx`'s first import). `adaptiveThemes: true` follows the OS scheme — dark mode is the token swap [`styling`](../../styling/SKILL.md) describes, done by the engine. Breakpoints that mean tablets and foldables are `md` and up.

## Usage

```tsx
import { Pressable, Text, View } from 'react-native';
import { StyleSheet } from 'react-native-unistyles';

export function Card({ title }: { title: string }) {
  return (
    <View style={styles.card} testID="Card.Root">
      <Text style={styles.title}>{title}</Text>
    </View>
  );
}

const styles = StyleSheet.create((theme) => ({
  card: {
    padding: {
      xs: theme.space[4],
      md: theme.space[6],
    },
    borderRadius: theme.radius.md,
    borderCurve: 'continuous',
    backgroundColor: theme.color.surface,
  },
  title: { fontSize: theme.text.lg, color: theme.color.text },
}));
```

Breakpoint-keyed values (`{ xs, md }`) replace `useWindowDimensions` branching for style differences; layout that changes structure still branches on width in [`styling`](../../styling/SKILL.md). Use `useUnistyles()` only to read a theme value outside a style prop (a non-style prop, a native colour) — it re-renders.

## Rules

- Import the unistyles `StyleSheet`, never both in one file.
- Configure before any component renders.
- Tokens come from [`styling`](../../styling/SKILL.md); themes are typed through the module declaration.
- Do not wrap unistyles-styled views in a component that reads the theme through `useUnistyles()` just to forward a colour.

## Gotchas

| Symptom | Cause | Fix |
|---|---|---|
| Crash on launch in Expo Go | Native module absent | Development build |
| Styles do not react to theme | Babel plugin missing or `root` wrong | Add the plugin; point `root` at the source folder |
| Type errors on `theme.*` | Module declaration missing | Add `UnistylesThemes` / `UnistylesBreakpoints` augmentation |
| Third-party component ignores styles | Library wraps `View` internally | Use `withUnistyles` for that component |

## Validation

- Development build runs on iOS and Android; `npx expo-doctor` clean.
- Toggling the OS appearance and rotating the device update styles with no component re-render.
- No `StyleSheet` imported from `react-native` in a unistyles-styled file.
- `testID` reaches the native view.
