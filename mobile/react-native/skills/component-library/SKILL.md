---
name: component-library
description: Use when choosing or wiring a React Native UI layer on SDK 57 — StyleSheet + Expo UI (default), NativeWind, Tamagui, Unistyles, gluestack or React Native Paper — plus provider, theme, dark mode and New Architecture fit. Triggers "which RN component library", "set up NativeWind / Unistyles / Paper", "do we need a UI kit". Do NOT use for hand-written tokens (`mobile-react-native:styling`), screens (`-ui-components`), `testID` rules (`-test-ids`) or web libraries (`fe-react:component-library`).
---

# React Native — Component Library (one-of-N)

Picks the UI layer that supplies buttons, inputs, sheets and (sometimes) the styling engine. **One** per app — two doubles the theme and the bundle. This file is the decision matrix and the shared rules; per-option setup lives in `references/<option>.md` — read exactly one after choosing.

## Version lane

| Lane | Expo SDK | What changes for this choice |
|---|---|---|
| **Primary** | **57** (RN 0.86) | Expo UI (`@expo/ui`, SwiftUI + Compose primitives) stable since SDK 56; New Architecture only |
| `[SDK58]` | 58 (RN 0.88 RC) | Re-run `expo-doctor`; Reanimated 4.7 + worklets 0.13 affect NativeWind, Unistyles and Tamagui animation peers |
| Supported | 55–56 | Same options; Expo UI exists but check the SDK's `@expo/ui` surface |
| Floor | 54 | Last SDK that can run the legacy architecture — a kit that is not New-Architecture-ready is disqualifying |

Detect the SDK first. A kit without New Architecture support is a blocker on SDK 55+, not a warning.

## When to use

- Choosing a UI layer for a new app, or justifying a change
- Wiring the chosen option's provider, theme and dark mode
- A kit breaks under the New Architecture or in a development build

## When NOT to use

- Hand-written `StyleSheet`, tokens, dark-mode swap, responsive layout → [`styling`](../styling/SKILL.md)
- Screens, `Pressable`, `expo-image`, lists, menus → [`ui-components`](../ui-components/SKILL.md)
- `testID` placement → [`test-ids`](../test-ids/SKILL.md)
- Forms → [`forms`](../forms/SKILL.md)
- React web → `fe-react:component-library`

## The decision

```
Default: no third-party kit.
  StyleSheet + Expo UI for native controls, your own atoms        -> references/expo-ui.md, references/none.md
Team is Tailwind-fluent, shares tokens with a web app?
  NativeWind (v4.2 stable; v5 is an RC)                           -> references/nativewind.md
Want a StyleSheet-shaped API with themes, breakpoints, no re-renders?
  Unistyles 3.5                                                    -> references/unistyles.md
Compiler-optimised universal design system for RN + web?
  Tamagui 3.0                                                      -> references/tamagui.md
Want Material Design 3 out of the box?
  React Native Paper 5                                             -> references/paper.md
Want a broad accessible set on a Tailwind core, or leaving NativeBase?
  gluestack v5                                                     -> references/gluestack.md
```

| Option | Look | Strength | Reality on SDK 57 | Styling authority | Reference |
|---|---|---|---|---|---|
| **StyleSheet + Expo UI** (default) | Platform-native controls, custom layout | Zero third-party UI dependency; SwiftUI / Compose widgets | `@expo/ui` stable since 56; development build | `StyleSheet` + tokens | [`expo-ui`](references/expo-ui.md), [`none`](references/none.md) |
| **NativeWind** | Custom (Tailwind) | Utility DX, shared web tokens | **4.2 stable; v5 is an RC** — do not start a production app on an RC without recording why | Tailwind classes | [`nativewind`](references/nativewind.md) |
| **Unistyles** | Custom | `StyleSheet.create` API with themes + breakpoints, updates without re-render | 3.5; Nitro; needs a development build | Unistyles `StyleSheet` | [`unistyles`](references/unistyles.md) |
| **Tamagui** | Themeable system | Compile-time style flattening, universal RN + web | 3.0; Babel/Metro plugin | `styled` + tokens | [`tamagui`](references/tamagui.md) |
| **React Native Paper** | Material 3 | Batteries-included, MD3 theming | 5.x New-Architecture ready | `StyleSheet` + Paper theme | [`paper`](references/paper.md) |
| **gluestack** | Neutral, accessible | Large accessible set, copy-in components | v5; styling core is Tailwind-based (NativeWind) | Tailwind classes | [`gluestack`](references/gluestack.md) |

NativeBase is deprecated — never pick it.

## Cross-cutting rules (every option)

- **One option per app.** Migrate wholesale, never screen by screen.
- **Mount the provider once at the root** — `src/app/_layout.tsx` in Expo Router. There is no `'use client'` boundary on device; the only rule is "above every consumer".
- **Theme once, centrally.** One theme or token set at the root; per-component colour overrides are a smell. Dark mode is a token swap driven by `useColorScheme()`, never per-component conditionals. The palette source is `design/visual-identity` (or a `design/theme-presets` preset); [`styling`](../styling/SKILL.md) maps it to tokens.
- **Styling authority follows the choice** (table above). Never two authorities on one element — a `className` plus a competing `StyleSheet` colour fails review.
- **`testID` goes inline on the control** — no `App*` wrapper just to carry it ([`test-ids`](../test-ids/SKILL.md)).
- **Compatibility is a gate.** Install with `npx expo install`, run `npx expo-doctor`. A library with native code needs a development build, not Expo Go ([`project-setup`](../project-setup/SKILL.md)).
- **Platform conventions first.** A Material kit on iOS imitates the other platform — choose Paper for an Android-first product, not by default. Design facts: `design/ui-ux-pro-max` (`--stack react-native`); where it disagrees with a reference here, the corpus wins.

## Anti-patterns

| Smell | Fix |
|---|---|
| Two kits in one app | One; migrate wholesale |
| NativeBase in new work | gluestack v5 |
| Provider added per screen | Once, in the root layout |
| Colour overrides scattered across screens | Central theme + `useColorScheme()` |
| `className` + `StyleSheet` colour on one element | Pick one authority |
| NativeWind v5 RC in production with no recorded reason | v4.2, or record the decision |
| Kit chosen without `expo-doctor` | Run it before committing |
| `AppButton` wrapper added to carry a `testID` | Inline `testID` |

## Workflow

1. Choose via the tree; record the reason in one line.
2. Read the one `references/<option>.md`.
3. Install with `npx expo install`; wire the provider at the root.
4. Theme from the palette via [`styling`](../styling/SKILL.md); wire dark mode off `useColorScheme()`.
5. Verify: a themed screen on both platforms, dark mode flips with no per-component edit, `expo-doctor` clean, `testID` lands on the native view.

## Rules

- Default is StyleSheet + Expo UI; a kit must earn its place by a need that exists now.
- One option, one provider, one authority.
- New Architecture compatibility is checked, not assumed.
- Record RC choices (NativeWind v5) as a decision.

## Handoffs

- Tokens, dark mode, adaptive layout → [`styling`](../styling/SKILL.md)
- Screens and native patterns → [`ui-components`](../ui-components/SKILL.md)
- `testID` per option → [`test-ids`](../test-ids/SKILL.md)
- Development build, provider placement → [`project-setup`](../project-setup/SKILL.md)
- Forms with kit inputs → [`forms`](../forms/SKILL.md)
- Palette and fonts → `design/visual-identity`, `design/theme-presets`
