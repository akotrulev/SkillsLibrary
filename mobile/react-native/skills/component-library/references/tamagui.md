# Tamagui — compiler-optimized universal design system

Tamagui is a themeable component set + token system with a **compile-time optimizing compiler** that flattens styles and hoists them out of render — the best *runtime* style performance of the RN kits, which matters on lower-end devices and long lists. It's universal (the same components render on RN and web), so it's the strongest pick when you share a design system across a mobile app and a web app. The **styling authority is Tamagui's `styled`/tokens API**, not `StyleSheet`.

**Version:** current Tamagui is New-Architecture ready. Install via `npx expo install`; it requires the **Tamagui Babel plugin** and a `tamagui.config.ts`. Verify with `expo-doctor`. Some setups want a dev client rather than Expo Go — confirm in [`project-scaffold`](../../project-scaffold/SKILL.md).

## Setup

```bash
npx expo install @tamagui/core @tamagui/config tamagui react-native-reanimated
npm i -D @tamagui/babel-plugin
```

```ts
// tamagui.config.ts
import { defaultConfig } from '@tamagui/config/v4';
import { createTamagui } from 'tamagui';
export const config = createTamagui(defaultConfig);   // swap tokens/themes from design/frontend-design
export type Conf = typeof config;
declare module 'tamagui' { interface TamaguiCustomConfig extends Conf {} }
```

```js
// babel.config.js
module.exports = (api) => {
  api.cache(true);
  return {
    presets: ['babel-preset-expo'],
    plugins: [
      ['@tamagui/babel-plugin', { components: ['tamagui'], config: './tamagui.config.ts', logTimings: true }],
      'react-native-reanimated/plugin',   // must stay last
    ],
  };
};
```

## Provider — once at the root

```tsx
// app/_layout.tsx
import { useColorScheme } from 'react-native';
import { TamaguiProvider, Theme } from 'tamagui';
import { config } from '../tamagui.config';

export default function RootLayout() {
  const scheme = useColorScheme() ?? 'light';
  return (
    <TamaguiProvider config={config} defaultTheme={scheme}>
      <Theme name={scheme}>{/* <Stack /> */}</Theme>
    </TamaguiProvider>
  );
}
```

## Usage + theming

```tsx
import { Button, YStack, Text } from 'tamagui';

export function SavePanel({ onSave, testID }: { onSave: () => void; testID?: string }) {
  return (
    <YStack gap="$3" padding="$4">
      <Text fontSize="$6" fontWeight="600">Save changes?</Text>
      <Button theme="active" onPress={onSave} testID={testID}>Save</Button>
    </YStack>
  );
}
```

Tokens (`$3`, `$6`, `$color`) come from `tamagui.config.ts` — map the [`design/frontend-design`](../../../../../design/frontend-design/SKILL.md) palette/spacing there once ([`styling`](../../styling/SKILL.md) owns the mapping). Dark mode is a **theme swap** driven by `useColorScheme()` + the `<Theme name>` — never per-component color props.

## testID

Tamagui components forward `testID` to the underlying native view — pass it inline. → [`testability`](../../testability/SKILL.md).

## Gotchas

| Symptom | Cause | Fix |
|---|---|---|
| Styles not flattened / slow | Babel plugin missing or misconfigured | Add `@tamagui/babel-plugin` with the right `config` path |
| Reanimated crash | Plugin order | `react-native-reanimated/plugin` must be **last** |
| Token types error (`$color` unknown) | `declare module 'tamagui'` missing | Add the module augmentation in `tamagui.config.ts` |
| Works in Expo Go, breaks on build | A transitive native dep | Use a dev client; `expo-doctor` |

## Validation

- App builds iOS + Android; `expo-doctor` clean; Babel plugin `logTimings` shows styles being extracted.
- `TamaguiProvider` mounts once at the root; tokens come from `tamagui.config.ts`.
- Dark mode flips via `useColorScheme()` + `<Theme>` with no per-component color props.
- One styling authority (Tamagui `styled`/tokens) — no competing `StyleSheet` colors.
- `testID` inline lands on the rendered native view.
