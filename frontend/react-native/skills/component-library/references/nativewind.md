# Nativewind — Tailwind for React Native

Nativewind compiles **Tailwind CSS class names** to RN `StyleSheet` objects at build time — the same utility DX as web Tailwind, on device. Pick it when the team is Tailwind-fluent or you want to share a token/design language with a web app. When Nativewind is present, the **styling authority flips to Tailwind** ([`styling`](../../styling/SKILL.md)) — you write `className`, not `StyleSheet`.

**Version:** **Nativewind v4** (current) — New-Architecture ready, Tailwind v3-style config. Install via `npx expo install` so the RN-compatible versions are pinned. Needs Babel + Metro config; verify with `expo-doctor`.

## Setup

```bash
npx expo install nativewind react-native-reanimated react-native-safe-area-context
npm i -D tailwindcss@^3 prettier-plugin-tailwindcss
npx tailwindcss init
```

```js
// tailwind.config.js
module.exports = {
  content: ['./app/**/*.{ts,tsx}', './components/**/*.{ts,tsx}'],
  presets: [require('nativewind/preset')],
  theme: { extend: { colors: { primary: 'var(--color-primary)' } } },  // tokens → styling skill
  plugins: [],
};
```

```js
// babel.config.js
module.exports = (api) => {
  api.cache(true);
  return {
    presets: [['babel-preset-expo', { jsxImportSource: 'nativewind' }], 'nativewind/babel'],
  };
};
```

```js
// metro.config.js
const { getDefaultConfig } = require('expo/metro-config');
const { withNativeWind } = require('nativewind/metro');
module.exports = withNativeWind(getDefaultConfig(__dirname), { input: './global.css' });
```

```css
/* global.css */
@tailwind base; @tailwind components; @tailwind utilities;
```

Import `global.css` once in the root `app/_layout.tsx`.

## Usage

```tsx
import { View, Text, Pressable } from 'react-native';

export function PrimaryButton({ label, testID }: { label: string; testID?: string }) {
  return (
    <Pressable accessibilityRole="button" testID={testID}
      className="rounded-xl bg-primary px-5 py-3 active:opacity-85">
      <Text className="text-center text-base font-semibold text-white">{label}</Text>
    </Pressable>
  );
}
```

## Theme + dark mode

Dark mode is Tailwind's `dark:` variant, driven by RN's color scheme (Nativewind reads `useColorScheme` and also exposes `useColorScheme()` from `nativewind` with a `setColorScheme`). Define semantic colors as CSS-var-backed tokens in the Tailwind config so light/dark are a token swap, not scattered `dark:` guesses on every element. [`styling`](../../styling/SKILL.md) owns the token structure; here they surface as Tailwind theme colors.

```tsx
import { useColorScheme } from 'nativewind';
const { colorScheme, setColorScheme } = useColorScheme();   // 'light' | 'dark' | 'system'
// <Pressable onPress={() => setColorScheme(colorScheme === 'dark' ? 'light' : 'dark')} />
```

```tsx
<View className="bg-white dark:bg-neutral-900">…</View>
```

## testID

Pass `testID` inline on the RN primitive under the class names — Nativewind styles the same element `testID` targets, so nothing changes. → [`testability`](../../testability/SKILL.md).

## Gotchas

| Symptom | Cause | Fix |
|---|---|---|
| Classes have no effect | Metro/Babel config missing or `content` globs wrong | Add `withNativeWind` + `nativewind/babel`; fix `content` paths |
| `dark:` never triggers | Color scheme not wired | Use `useColorScheme` from `nativewind`; set `darkMode` per v4 docs |
| `className` + a competing `StyleSheet` color on one element | Two styling authorities | Tailwind is the authority — drop the StyleSheet color ([`styling`](../../styling/SKILL.md)) |
| Reanimated errors after install | Missing/misordered Reanimated plugin | Reanimated Babel plugin must be **last**; reinstall via `npx expo install` |

## Validation

- App builds iOS + Android; `expo-doctor` clean (New-Arch compatible).
- Tailwind classes render styles; `global.css` imported once at the root.
- Dark mode flips via the color-scheme toggle; semantic colors come from config tokens, not per-element `dark:` guesses.
- One styling authority (Tailwind) — no competing `StyleSheet` colors.
- `testID` inline on a primitive lands on the rendered native view.
