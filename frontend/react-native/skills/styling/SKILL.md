---
name: fe-react-native-styling
description: Use when styling a React Native + Expo app with StyleSheet you write — `StyleSheet.create` as the default authority, design tokens as a typed JS object (from a `design/frontend-design` palette), a type scale + heading hierarchy, dark mode as a token swap driven by `useColorScheme()`, the no-CSS-cascade discipline (styles don't inherit; text lives in `<Text>`), and the follow-the-kit styling-authority decision (StyleSheet vs Nativewind/Tailwind vs Tamagui — never two at once). Triggers "how do I structure styles here", "set up design tokens in RN", "dark mode with useColorScheme", "StyleSheet or Nativewind or Tamagui", "why doesn't my parent color reach the child", "modern RN styling patterns / shadows / gradients". Do NOT use for a UI kit's own theme object (use `frontend/react-native/skills/component-library`), the palette/font design itself (use `design/frontend-design`), breakpoints/orientation/safe-area layout (use `frontend/react-native/skills/responsive-design`), native component patterns (use `frontend/react-native/skills/ui-conventions`), accessibility contrast (use `frontend/react-native/skills/accessibility`), or React web CSS (use `frontend/react/skills/styling`).
---

# React Native — Styling (StyleSheet, tokens, dark mode, the styling authority)

Owns how an RN app is styled with **styles you write**: `StyleSheet.create` objects, a typed token layer, a type scale, dark mode, and the one decision that keeps a codebase coherent — **which styling authority owns the app**. It does **not** own a UI kit's theme system (Paper's MD3 theme, Tamagui tokens) — that's [`component-library`](../component-library/SKILL.md); this skill is the default (no-kit) path and defines when the authority flips to Tailwind/Tamagui.

The web analog is CSS Modules + custom properties; RN is different in one load-bearing way: **there is no CSS cascade, no `@media`, no inheritance.** Styles are plain objects on each element. That changes the mechanics below.

## Version applicability

Detect the Expo SDK / RN majors first. The modern-styling patterns here (CSS `boxShadow` string, `experimental_backgroundImage` gradients, `borderCurve`) are **RN 0.76+ / New-Architecture** APIs — primary for SDK 53+. On an older RN, fall back to the legacy `shadow*`/`elevation` objects and a gradient library, and don't flag their absence. `StyleSheet`, tokens, and `useColorScheme` behave identically across the supported SDKs.

## When to use

- Structuring a component's styles (`StyleSheet.create`)
- Setting up design tokens (a typed JS object) from a `design/frontend-design` palette
- Dark mode, a type scale, modern shadow/gradient/spacing patterns
- Deciding the styling authority: StyleSheet vs Nativewind vs Tamagui

## When NOT to use

- A UI kit's theme/token object (Paper MD3, Tamagui `createTamagui`) → [`component-library`](../component-library/SKILL.md)
- Picking the palette, fonts, visual direction → [`design/frontend-design`](../../../../design/frontend-design/SKILL.md) (primary), `design/theme-factory` (quick-start)
- Contrast/WCAG auditing, dynamic type, touch targets → [`accessibility`](../accessibility/SKILL.md)
- Breakpoints, orientation, `SafeAreaView`, tablet layout → [`responsive-design`](../responsive-design/SKILL.md)
- Native component patterns (Pressable, expo-image, menus) → [`ui-conventions`](../ui-conventions/SKILL.md)
- React web CSS → `frontend/react/skills/styling`

## The styling authority decision

Pick **one** primary styling authority per app. Driven by the kit choice ([`component-library`](../component-library/SKILL.md)):

```
Using Nativewind or gluestack-ui?
  YES → Tailwind classNames are the authority. StyleSheet only for the rare escape hatch.
  NO ↓
Using Tamagui?
  YES → Tamagui's styled/tokens API is the authority.
  NO ↓
No kit (or Paper, which owns only component look)?
  YES → StyleSheet.create + a typed token layer (the DEFAULT).
```

**One authority, always.** Never a Nativewind `className` *and* a competing `StyleSheet` color on the same element. This skill owns the **StyleSheet** path; the Tailwind/Tamagui paths live in their references under [`component-library`](../component-library/SKILL.md).

## StyleSheet.create — the default

```tsx
import { StyleSheet, View, Text } from 'react-native';
import { tokens } from '@/theme';

function Card({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <View style={styles.card}>
      <Text style={styles.title}>{title}</Text>
      <Text style={styles.subtitle}>{subtitle}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  card:     { padding: tokens.space[4], gap: tokens.space[2], borderRadius: 12, borderCurve: 'continuous',
              backgroundColor: tokens.color.surface, boxShadow: '0 2px 8px rgba(0,0,0,0.08)' },
  title:    { fontSize: tokens.text.lg, fontWeight: '600', color: tokens.color.text },
  subtitle: { fontSize: tokens.text.base, color: tokens.color.textMuted },
});
```

Rules:
- **`StyleSheet.create`, not inline object literals**, for anything reused or in a list item — an inline `style={{…}}` allocates a new object every render and breaks list-item memoization ([`performance`](../performance/SKILL.md), `../../vendor/react-native-guidelines/rules/list-performance-inline-objects.md`).
- **Compose with arrays**: `style={[styles.base, isActive && styles.active, props.style]}` — the last wins, the RN analog of `composes`. Accept an optional `style` prop on atoms so callers can extend.
- **No cascade.** A `color` on a parent `View` does **not** reach child `<Text>`. Set text color on the `<Text>` (or via a token-reading `AppText` atom). All text must be inside `<Text>`.

## Modern RN styling patterns (the seed)

From `../../vendor/react-native-guidelines/rules/ui-styling.md` — the current idioms on the New Architecture:

- **`borderCurve: 'continuous'` alongside every `borderRadius`** — smooth iOS "squircle" corners instead of a hard arc.
- **`gap` on the parent for spacing between; `padding` for spacing within** — not `marginBottom` on each child.
- **CSS `boxShadow` string** (`'0 2px 8px rgba(0,0,0,0.1)'`) — not the legacy `shadowColor`/`shadowOffset`/`shadowOpacity` objects or Android `elevation`.
- **`experimental_backgroundImage: 'linear-gradient(...)'`** for gradients — not a third-party `<LinearGradient>` library.
- **Limit font sizes; vary weight and grayscale color for hierarchy** — consistent sizing reads cleaner than five ad-hoc sizes (see the type scale below for the disciplined version).

## Design tokens — a typed JS object

RN has no CSS custom properties, so tokens are a **typed object** imported everywhere (or exposed via a small Context/`useTokens()` hook for theme swapping). This is the seam where the visual direction enters the code — map [`design/frontend-design`](../../../../design/frontend-design/SKILL.md)'s per-brief token system (primary; or a `design/theme-factory` preset) to it. The token *system* rules (tier model, purpose-naming, categories) are the stack-agnostic discipline in [`design/design-tokens`](../../../../design/design-tokens/SKILL.md); this is the RN **mechanics**.

```ts
// theme/tokens.ts
export const space = { 1: 4, 2: 8, 3: 12, 4: 16, 6: 24, 8: 32 } as const;
export const text  = { sm: 13, base: 16, lg: 20, xl: 25, '2xl': 31 } as const;   // ~1.25 ratio
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

Rules:
- **Styles consume tokens, never hardcoded values.** `color: tokens.color.text`, not `'#333'`; `padding: tokens.space[4]`, not `16` scattered.
- **Name functional tokens by purpose, not value** — `color.danger` / `color.actionPrimary`, never `color.red`. A palette or contrast fix becomes a one-line token edit.
- **One token set app-wide** — no per-screen palette forks.
- **Bridge to the kit, one source of truth.** With Paper/Tamagui, set the *kit theme* from these tokens (or vice-versa) — never two diverging color systems ([`component-library`](../component-library/SKILL.md)).

## Type scale & hierarchy

Typography is where `design/frontend-design`'s taste becomes tokens. Pick one ratio (1.2 dense / 1.25 / 1.333 editorial) and generate steps from one base (the `text` object above). Because there's no cascade, hierarchy lives in **reusable `<Text>` atoms**, not global element selectors:

```tsx
// components/atoms/AppText.tsx — the RN replacement for global h1..h4 rules
type Variant = 'display' | 'title' | 'body' | 'caption';
const variantStyle: Record<Variant, TextStyle> = {
  display: { fontSize: text['2xl'], fontWeight: '700', letterSpacing: -0.5 },
  title:   { fontSize: text.lg,     fontWeight: '600' },
  body:    { fontSize: text.base },
  caption: { fontSize: text.sm,     color: lightColors.textMuted },
};
```

**Custom fonts load via a config plugin / `expo-font`**, not a runtime `<link>` — see `../../vendor/react-native-guidelines/rules/fonts-config-plugin.md` and [`project-scaffold`](../project-scaffold/SKILL.md). Rules: sizes come from scale tokens (never a literal `fontSize: 17`); two–three weights; large display text wants slightly negative tracking; body line-height looser than headings.

## Dark mode

Dark mode is a **token swap**, not a per-component conditional. Drive it from `useColorScheme()` (system) plus an optional user override, and hand the right token object down through a `useTokens()` hook. Because every style reads tokens, **no component style changes** for dark mode — if a component needs a dark-specific rule, a color escaped into a literal; fix the token.

```tsx
// theme/ThemeProvider.tsx
import { createContext, use, useMemo, type ReactNode } from 'react';
import { useColorScheme } from 'react-native';
import { lightColors, darkColors, space, text, radius, type Tokens } from './tokens';

const TokensCtx = createContext<Tokens | null>(null);

export function ThemeProvider({ children, override }: { children: ReactNode; override?: 'light' | 'dark' }) {
  const system = useColorScheme();                       // 'light' | 'dark' | null
  const scheme = override ?? system ?? 'light';
  const value = useMemo<Tokens>(() => ({
    space, text, radius, color: scheme === 'dark' ? darkColors : lightColors,
  }), [scheme]);
  return <TokensCtx value={value}>{children}</TokensCtx>;
}
export function useTokens() {
  const t = use(TokensCtx);
  if (!t) throw new Error('useTokens must be used within <ThemeProvider>');
  return t;
}
```

Rules:
- **Dark mode is a deliberately-authored second palette, not an inversion.** Never negate hex. **Desaturate accents** (saturated brand colors vibrate on dark), **avoid pure `#000`** (a very dark neutral reads better and lets shadows show), and **re-verify every contrast pair** ([`accessibility`](../accessibility/SKILL.md) — a ratio that passes on light routinely fails on dark).
- **Follow the OS by default (`useColorScheme`), let the user override, persist the override** (via a store — [`state-management`](../state-management/SKILL.md)).
- **With a kit, drive dark mode from its color-mode API** (Paper theme swap, Tamagui `<Theme>`, Nativewind `useColorScheme`) and keep it in sync with your tokens so both agree.
- Static images/status bar: pair with `expo-status-bar` `style="auto"` so the status bar text flips too.

## Rules

- **One styling authority** (StyleSheet · Nativewind/Tailwind · Tamagui) — never two on one element; [`component-library`](../component-library/SKILL.md) picks it.
- **`StyleSheet.create` by default**; no inline object literals in list items or reused components ([`performance`](../performance/SKILL.md)); compose with style arrays.
- **No cascade** — text color on the `<Text>` (or an `AppText` atom); all text inside `<Text>`.
- **Design tokens as a typed object**, sourced from `design/frontend-design`; styles consume tokens, never literals; functional tokens named by purpose; bridged to one source with the kit.
- **Modern patterns**: `borderCurve: 'continuous'`, `gap` for between / `padding` for within, `boxShadow` string, `experimental_backgroundImage` gradients, limited font sizes.
- **Type as a system** — one ratio + base as tokens, hierarchy via `<Text>` atoms, fonts via `expo-font`/config plugin.
- **Dark mode = an authored second palette** (desaturated accents, no pure black, contrast re-verified) swapped via `useColorScheme()` + `useTokens()` — never an inversion; user override persisted.

## What NOT to do

- No inline `style={{…}}` in list items / reused components — `StyleSheet.create` (memoization).
- No hardcoded hex/number literals in styles — use tokens.
- No relying on inheritance (`color` on a parent reaching child text) — RN has no cascade.
- No Tailwind (`className`) layered onto a competing `StyleSheet` color — pick one authority.
- No two color systems (kit tokens *and* diverging local tokens) — bridge to one.
- No value-named functional tokens (`color.red` for danger) — name by purpose.
- No dark mode by inversion (negated hex) — author a second palette and re-check contrast.
- No legacy `shadow*`/`elevation` or gradient libraries on RN 0.76+ — use `boxShadow` / `experimental_backgroundImage`.

## Validation

- App builds iOS + Android; toggling the OS appearance flips colors with **no** component style changes.
- Grep `StyleSheet.create` blocks (and inline styles) for hex/raw numbers → all come from tokens.
- Only one styling authority present (no Tailwind + competing StyleSheet color).
- No bare strings outside `<Text>`; no inline style literals inside a list `renderItem`.
- Corners use `borderCurve: 'continuous'`; shadows use `boxShadow` strings (RN 0.76+).

## Handoffs

- A UI kit's own theme object (Paper MD3, Tamagui, Nativewind-as-authority) → [`component-library`](../component-library/SKILL.md)
- Palette, fonts, visual direction, type *treatment* → [`design/frontend-design`](../../../../design/frontend-design/SKILL.md) (primary), `design/theme-factory` (quick-start)
- Token tier model / purpose-naming discipline → [`design/design-tokens`](../../../../design/design-tokens/SKILL.md)
- Contrast/WCAG check, dynamic type, touch targets → [`accessibility`](../accessibility/SKILL.md)
- Breakpoints, orientation, `SafeAreaView`, tablet layout → [`responsive-design`](../responsive-design/SKILL.md)
- Inline-style / list-perf cost, font loading → [`performance`](../performance/SKILL.md)
- Custom font config plugin, `expo-font` → [`project-scaffold`](../project-scaffold/SKILL.md)
- Native component look (Pressable, expo-image) → [`ui-conventions`](../ui-conventions/SKILL.md)
