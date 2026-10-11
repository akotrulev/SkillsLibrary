---
name: styling
description: Use when styling or adapting layout in an Expo SDK 57 app — `StyleSheet.create`, typed tokens, `useColorScheme` dark mode, type scale, safe-area insets, `useWindowDimensions`, tablets, foldables, the one-styling-authority rule. Triggers "set up tokens", "dark mode", "content under the notch", "work on iPad / foldable". Do NOT use for a kit's theme (`mobile-react-native:component-library`), palette choice (`design/visual-identity`), screens (`-ui-components`) or web CSS.
---

# React Native — Styling and Adaptive Layout

Owns how an RN app is styled with **styles you write** and how that layout adapts to the screen: `StyleSheet.create`, a typed token layer, a type scale, dark mode, safe areas, window size, tablets and foldables, and the one decision that keeps a codebase coherent — which **styling authority** owns the app. A kit's own theme object is [`component-library`](../component-library/SKILL.md)'s.

There is **no CSS cascade, no `@media`, no inheritance.** Styles are plain objects on each element.

## Version lane

| Lane | SDK / RN | Consequence |
|---|---|---|
| **Primary** | **57** / 0.86 | `boxShadow` string, `experimental_backgroundImage` gradients, `borderCurve`, `gap` are available; Android is edge-to-edge (target SDK 36) so insets are always your job |
| `[SDK58]` | 58 / 0.88 RC | Re-check insets after the upgrade; scene lifecycle default on iOS 27 |
| Supported | 55–56 / 0.83–0.85 | Same patterns |
| Floor | 54 / 0.81 | Same patterns; below the floor is a [`migration`](../migration/SKILL.md) finding |

Design facts (palette, type, spacing, platform convention) come from `design/ui-ux-pro-max` (`--stack react-native`); where it disagrees with this skill, the corpus wins.

## When to use

- Structuring a component's styles; setting up tokens and a type scale
- Dark mode; fonts; modern shadow / gradient / spacing patterns
- Content under the notch, home indicator, keyboard or system bars
- A layout that must work on phones, tablets, foldables and rotation
- Deciding the styling authority

## When NOT to use

- A kit's theme (Paper MD3, Tamagui, Unistyles config) → [`component-library`](../component-library/SKILL.md)
- Choosing the palette and fonts → `design/visual-identity`, `design/theme-presets`; token tier discipline → `design/design-tokens`
- Contrast, font scaling, touch targets audit → [`accessibility`](../accessibility/SKILL.md)
- Screens, `Pressable`, lists → [`ui-components`](../ui-components/SKILL.md)
- React web CSS → `fe-react:styling`

## The styling authority

One per app, set by the choice in [`component-library`](../component-library/SKILL.md):

```
NativeWind or gluestack?   -> Tailwind classNames
Tamagui?                   -> Tamagui styled + tokens
Unistyles?                 -> Unistyles StyleSheet
otherwise (default, Paper) -> StyleSheet.create + a typed token layer
```

Never two on one element — a `className` and a competing `StyleSheet` colour fails review. This file teaches the default `StyleSheet` path; the others are in their references.

## `StyleSheet.create` — the default

```tsx
import { StyleSheet, Text, View } from 'react-native';
import { useTokens } from '@/theme';

export function Card({ title, subtitle }: { title: string; subtitle: string }) {
  const tokens = useTokens();
  return (
    <View style={[styles.card, { backgroundColor: tokens.color.surface }]}>
      <Text style={[styles.title, { color: tokens.color.text }]}>{title}</Text>
      <Text style={[styles.subtitle, { color: tokens.color.textMuted }]}>{subtitle}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  card: { padding: 16, gap: 8, borderRadius: 12, borderCurve: 'continuous', boxShadow: '0 2px 8px rgba(0,0,0,0.08)' },
  title: { fontSize: 20, fontWeight: '600' },
  subtitle: { fontSize: 16 },
});
```

- `StyleSheet.create`, not inline literals, for anything reused or inside a list item — an inline `style={{…}}` allocates per render: `vendor/react-native-guidelines/rules/list-performance-inline-objects.md`.
- Compose with arrays; the last wins. Atoms accept an optional `style` prop so callers extend.
- **No cascade:** a parent `color` does not reach child `<Text>`; set it on the `<Text>` or in an `AppText` atom.

## Modern patterns (vendored `rules/ui-styling.md`)

- `borderCurve: 'continuous'` beside every `borderRadius`.
- `gap` on the parent for space between, `padding` for space within — not `marginBottom` per child.
- CSS `boxShadow` string, not `shadow*` objects or Android `elevation`.
- `experimental_backgroundImage: 'linear-gradient(...)'` for gradients, not a gradient library.
- Few font sizes; vary weight and grey for hierarchy.

## Tokens — a typed object

RN has no custom properties, so tokens are a typed object read through a hook. Map the palette from `design/visual-identity` (or a `design/theme-presets` preset) into it; the tier and naming discipline is `design/design-tokens`.

```ts
export const space = { 1: 4, 2: 8, 3: 12, 4: 16, 6: 24, 8: 32 } as const;
export const text = { sm: 13, base: 16, lg: 20, xl: 25, '2xl': 31 } as const;
export const radius = { sm: 8, md: 12, lg: 16 } as const;

export const lightColors = {
  actionPrimary: '#1867c0', onAction: '#ffffff',
  surface: '#ffffff', text: '#1a1a27', textMuted: '#5a5a6e',
  danger: '#c62828', success: '#2e7d32',
} as const;

export const darkColors: typeof lightColors = {
  actionPrimary: '#7ca9e6', onAction: '#0b1220',
  surface: '#14141c', text: '#f2f2f7', textMuted: '#a1a1b0',
  danger: '#ef5350', success: '#66bb6a',
};

export type Tokens = { space: typeof space; text: typeof text; radius: typeof radius; color: typeof lightColors };
```

- Styles consume tokens, never literal hex or scattered numbers.
- **Name by purpose, not value** — `color.danger`, never `color.red`.
- One token set app-wide; with a kit, bridge to **one** source so two colour systems never diverge.

## Type scale and platform fonts

One ratio (1.2 dense · 1.25 · 1.333 editorial) from one base, as tokens. Hierarchy lives in reusable `<Text>` atoms, not selectors. Two to three weights; display text slightly negative tracking; body line-height looser than headings. Sizes come from tokens, never `fontSize: 17`.

- **System fonts first** — San Francisco on iOS, Roboto on Android — unless the brand needs a custom face. A custom font loads through the **`expo-font` config plugin**, not runtime `loadAsync` in render: `vendor/.../rules/fonts-config-plugin.md`, [`project-setup`](../project-setup/SKILL.md).
- **Text scales with the system setting and is never locked** — no `allowFontScaling={false}`; design for the largest sizes ([`accessibility`](../accessibility/SKILL.md)).

## Dark mode

A **token swap** driven by `useColorScheme()` plus an optional persisted user override — no component style changes.

```tsx
import { createContext, use, type ReactNode } from 'react';
import { useColorScheme } from 'react-native';
import { darkColors, lightColors, radius, space, text, type Tokens } from './tokens';

const TokensContext = createContext<Tokens | null>(null);

export function ThemeProvider({ children, override }: { children: ReactNode; override?: 'light' | 'dark' }) {
  const system = useColorScheme();
  const scheme = override ?? system ?? 'light';
  const tokens: Tokens = { space, text, radius, color: scheme === 'dark' ? darkColors : lightColors };
  return <TokensContext value={tokens}>{children}</TokensContext>;
}

export function useTokens() {
  const tokens = use(TokensContext);
  if (!tokens) throw new Error('useTokens must be used within <ThemeProvider>');
  return tokens;
}
```

- Dark is an **authored second palette**, not an inversion: desaturate accents, avoid pure `#000`, re-verify every contrast pair.
- Follow the OS by default; persist an override ([`architecture`](../architecture/SKILL.md)).
- `expo-status-bar` `style="auto"` so status-bar text flips too.
- The Compiler is on in the template, so the provider value needs no `useMemo`.

## Safe areas and insets

Android is edge-to-edge and iOS draws under the notch, home indicator and translucent bars; **content must clear them deliberately.**

- Expo Router mounts `SafeAreaProvider` at the root; read insets with `useSafeAreaInsets()` from `react-native-safe-area-context`.
- **Scrollable screens:** `contentInsetAdjustmentBehavior="automatic"` on the `ScrollView` / list, not a `SafeAreaView` wrapped around it: `vendor/.../rules/ui-safe-area-scroll.md`. Native stack headers and native tabs inset for you.
- **Non-scrolling fixed chrome** (a bottom bar, a banner): `paddingBottom: insets.bottom`, `paddingTop: insets.top`.
- **Keyboard** insets are [`forms`](../forms/SKILL.md)'s.
- Never hardcode `44` or `34` for a notch or indicator — insets differ per device and orientation.

```tsx
const insets = useSafeAreaInsets();
<View style={[styles.bar, { paddingBottom: Math.max(insets.bottom, 12) }]} />
```

## Window size, tablets and foldables

`useWindowDimensions()` re-renders on rotation, split-view resize and fold/unfold — never read `Dimensions.get('window')` once at module level.

```ts
export function useWidthClass() {
  const { width } = useWindowDimensions();
  if (width >= 840) return 'expanded';
  if (width >= 600) return 'medium';
  return 'compact';
}
```

- **Three width classes** (compact < 600 · medium 600–839 · expanded ≥ 840 dp) match the Android window-size classes; iPad split view lands in them too. Pick a layout per class, not per device model.
- **Compact → expanded** typically means a single column → master/detail or a two- or three-column grid; the route stays the same ([`navigation`](../navigation/SKILL.md)).
- **Style differences** with width use a numeric `maxWidth` on content (readable line length ≈ 600–700) plus `flexDirection` per class; **structural differences** branch on the class.
- **iPad:** set `ios.supportsTablet: true` in the config; multitasking sizes arrive as width changes. **Android large screens:** do not lock orientation in config — from Android 16 the OS ignores orientation and resizability restrictions on screens ≥ 600 dp, so a layout that only works in portrait is a defect.
- **Foldables:** a fold changes the window width while the app is running; the layout must reflow without losing state. Never key local state to the width class.
- **Orientation:** support both unless the product demands otherwise and record the reason; read the live value, never assume.
- Test targets: a small phone with the largest font scale, a tablet in split view, a foldable unfolded — the device lanes belong to `qa-mobile-typescript`.

## Rules

- One styling authority; `StyleSheet.create`, no inline literals in list items.
- Tokens as a typed object; purpose-named; no literals in styles.
- No cascade: text colour on the `<Text>`; all text in `<Text>`.
- Dark mode is an authored palette swapped by `useColorScheme()`; contrast re-verified.
- Insets from `useSafeAreaInsets()` / `contentInsetAdjustmentBehavior`, never hardcoded.
- Width from `useWindowDimensions()`, three classes, no orientation lock on large screens.
- Font scaling never disabled.

## What NOT to do

- No inline `style={{…}}` in `renderItem`; no hardcoded hex or notch offsets.
- No `Dimensions.get` at module scope.
- No `SafeAreaView` around a `ScrollView` that can inset itself.
- No Tailwind `className` on a competing `StyleSheet` colour.
- No dark mode by hex inversion; no value-named tokens.
- No legacy `shadow*` / `elevation` or gradient libraries on RN 0.76+.
- No per-device-model branches.

## Validation

- Toggling OS appearance flips colours with no component style edits.
- No hex literals or raw spacing in `StyleSheet.create` blocks; no `allowFontScaling={false}`.
- No bare strings outside `<Text>`; no inline style literals in a list `renderItem`.
- A screen renders without clipping on a notched phone, an iPad split view and a foldable, at the largest font scale.
- Corners use `borderCurve: 'continuous'`; shadows use `boxShadow`.

## Handoffs

- Kit theme or Tailwind / Unistyles authority → [`component-library`](../component-library/SKILL.md)
- Palette and type direction → `design/visual-identity`, `design/theme-presets`, `design/design-tokens`
- Contrast, font scale, touch targets → [`accessibility`](../accessibility/SKILL.md)
- Screens and native patterns → [`ui-components`](../ui-components/SKILL.md)
- List and inline-style cost → [`performance`](../performance/SKILL.md)
- Keyboard avoidance → [`forms`](../forms/SKILL.md)
- Font config plugin → [`project-setup`](../project-setup/SKILL.md)
