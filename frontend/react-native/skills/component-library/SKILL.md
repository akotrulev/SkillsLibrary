---
name: fe-react-native-component-library
description: Use when choosing or wiring a React Native UI kit — the decision between RN primitives + StyleSheet (default), Nativewind (Tailwind for RN), Tamagui (compiler-optimized universal), React Native Paper (Material Design), or gluestack-ui — plus setup, the theme/provider + dark-mode wiring, and the New-Architecture / Expo compatibility each one carries. Triggers: "which RN component library should we use", "set up Nativewind / Tamagui / Paper / gluestack", "do we need a UI kit at all", "add a themed Button/Dialog/Snackbar", "does this kit support the New Architecture / Expo Go". Do NOT use for hand-written StyleSheet / tokens / dark-mode mechanics (use `frontend/react-native/skills/styling`), `testID` mechanics per kit (use `frontend/react-native/skills/testability`), the component-layering taxonomy (use `frontend/react-native/skills/reference`), native UI patterns like Pressable/expo-image/menus (use `frontend/react-native/skills/ui-conventions`), forms (use `frontend/react-native/skills/forms`), or React web libraries (use `frontend/react/skills/component-library`).
---

# React Native — Component Library (one-of-N family)

Picks and wires the UI kit that supplies your themed buttons, inputs, dialogs, and (sometimes) styling engine. **One** kit per app — mixing two doubles the theming story and the bundle. This SKILL.md is the **decision matrix + shared rules**; the per-kit setup/theme/dark-mode/compatibility depth lives in `references/<kit>.md` — read exactly one after you've chosen.

Unlike the web, **the default here is often no kit at all**: RN ships a small set of primitives (`View`/`Text`/`Pressable`/`TextInput`) and `StyleSheet`, and many production apps build their own atom layer on top rather than adopt a Material kit. Reach for a kit for a themed component set + accessibility out of the box, or when the team wants Tailwind/utility DX.

## Version applicability

Detect the **Expo SDK / RN** majors first (`package.json`, `app.json`). The load-bearing compatibility axis is the **New Architecture** (Fabric/TurboModules, always-on since SDK 55) — a kit that hasn't shipped New-Arch support is disqualifying, not a warning. Current lines: **Nativewind v4**, **Tamagui** (New-Arch-ready), **React Native Paper v5**, **gluestack-ui v2** (the NativeBase successor; NativeBase itself is deprecated — never pick it). Pin the kit major to your SDK line and read the reference's version notes; verify Expo compatibility via `npx expo install` + `expo-doctor`.

## When to use

- Choosing a UI kit for a new RN app (or justifying no kit / a change)
- Wiring the chosen kit's provider, theme, and dark mode
- Adding a themed Button/Dialog/Snackbar/Input and needing the kit-native way
- Diagnosing a kit that breaks under the New Architecture or in Expo Go

## When NOT to use

- Hand-written `StyleSheet`, tokens, dark-mode token swap, type scale → [`styling`](../styling/SKILL.md)
- `testID` placement per kit → [`testability`](../testability/SKILL.md)
- Atom/molecule/organism layering + when a molecule owns state → [`reference`](../reference/SKILL.md)
- Native UI patterns (`Pressable` over `TouchableOpacity`, `expo-image`, native menus/modals) → [`ui-conventions`](../ui-conventions/SKILL.md)
- Forms + validation → [`forms`](../forms/SKILL.md)
- React web → `frontend/react/skills/component-library`

## The decision

```
Want a utility/Tailwind DX and the team is Tailwind-fluent?
  YES → Nativewind        (Tailwind classNames → StyleSheet; styling authority flips to Tailwind) → references/nativewind.md
  NO  ↓
Want a compiler-optimized, themeable design system (universal RN + web), performance-first?
  YES → Tamagui           (compiler flattens styles; own component set + tokens)                  → references/tamagui.md
  NO  ↓
Want Material Design components with theming + a11y out of the box?
  YES → React Native Paper (Material 3, MD3 theming, free)                                        → references/paper.md
  NO  ↓
Want a broad copy-in-ish accessible component set with a utility-style API?
  YES → gluestack-ui v2    (accessible primitives, Nativewind-based styling)                       → references/gluestack.md
  NO  → none              (DEFAULT — RN primitives + StyleSheet; build your own atoms)             → references/none.md
```

| Kit | Cost | Look | Strength | New-Arch / Expo reality | Reference |
|---|---|---|---|---|---|
| **none** (primitives + StyleSheet) | — | Fully custom | Zero dep/bundle; total control; pairs with [`styling`](../styling/SKILL.md) | Always compatible; you own everything | [`none`](references/none.md) |
| **Nativewind** | Free (MIT) | Custom (Tailwind) | Tailwind classes compiled to `StyleSheet`; fast DX; shared tokens with web | v4 New-Arch-ready; `npx expo install`; Babel/Metro config | [`nativewind`](references/nativewind.md) |
| **Tamagui** | Free (MIT) | Themeable design system | **Compile-time style flattening** (best runtime perf), universal RN+web, rich token system | New-Arch-ready; needs the Tamagui Babel plugin + config | [`tamagui`](references/tamagui.md) |
| **React Native Paper** | Free (MIT) | Material Design 3 | Batteries-included Material set, MD3 theming, solid a11y | v5 New-Arch-ready; `react-native-safe-area-context` + provider | [`paper`](references/paper.md) |
| **gluestack-ui v2** | Free (MIT) | Neutral, accessible | Accessible component set on a Nativewind styling core; NativeBase successor | v2 New-Arch-ready; **never NativeBase** (deprecated) | [`gluestack`](references/gluestack.md) |

**Default = none** (primitives + StyleSheet) for a bespoke design owned end-to-end. Pick **Nativewind** for Tailwind DX / shared web tokens; **Tamagui** when runtime style performance and a universal design system matter; **Paper** for Material out of the box; **gluestack** for a broad accessible set with utility styling.

## Cross-cutting rules (every kit)

- **One kit per app.** Two kits = two theme systems and two style engines fighting. Migrate wholesale, never screen-by-screen.
- **The provider/theme is mounted once at the root** — in Expo Router that's `app/_layout.tsx` (Paper's `PaperProvider`, Tamagui's `TamaguiProvider`, gluestack's `GluestackUIProvider`). There is **no `'use client'` boundary** — every component runs on device, so unlike the web there's no RSC gotcha; the only rule is "mount the provider above every consumer."
- **Theme once, centrally.** One theme object / token set at the root; per-component color overrides are a smell. Dark mode is a theme concern — drive it from `useColorScheme()` (system) + one toggle, redefining tokens, never per-component conditional colors. The palette/fonts source is [`design/frontend-design`](../../../../design/frontend-design/SKILL.md); [`styling`](../styling/SKILL.md) owns mapping it to tokens.
- **`testID` forwards through the kit component's props** to the rendered native view. The exact prop per kit lives in [`testability`](../testability/SKILL.md)'s matrix — kept consistent with this one on purpose. (`testID` replaces web's `data-testid`.)
- **Styling authority follows the kit.** Nativewind/gluestack → **Tailwind classes** are the authority; Tamagui → its **styled/tokens** API; Paper/none → **`StyleSheet` + tokens** ([`styling`](../styling/SKILL.md)). Never two authorities on one element (e.g. Nativewind `className` *and* a competing `StyleSheet` color).
- **New-Architecture + Expo Go compatibility is a gate, not a nicety.** Install via `npx expo install`, run `expo-doctor`; a kit (or its transitive native deps) that isn't New-Arch-ready fails on SDK 55+. Some kits need a **dev client** (custom native) rather than Expo Go — that's a [`project-scaffold`](../project-scaffold/SKILL.md) decision.
- **Don't wrap kit controls in `App*` wrappers** just to set defaults or carry test ids — pass `testID` inline (testability), use the theme for defaults.

## Anti-patterns

| Smell | Fix |
|---|---|
| Two component kits in one app | One kit; migrate wholesale if changing |
| NativeBase in a new app | Deprecated — use gluestack-ui v2 (its successor) |
| Provider added per screen | Once, at the root `app/_layout.tsx` |
| Per-component color overrides scattered across screens | One central theme; dark mode from `useColorScheme` + one toggle |
| Nativewind `className` + a competing `StyleSheet` color on one element | Pick one styling authority ([`styling`](../styling/SKILL.md)) |
| Kit chosen without checking New-Arch/Expo support | `npx expo install` + `expo-doctor` before committing |
| `AppButton` wrapper introduced to carry a `testID` | Inline `testID` on the kit control (testability) |

## Workflow

1. **Choose** via the decision tree. State the reason (one line) in the Phase-1 architecture record ([`project-scaffold`](../project-scaffold/SKILL.md)).
2. **Read the one `references/<kit>.md`** — packages, provider wiring, theme + dark mode, New-Arch/Expo notes, the kit's test-id prop.
3. **Wire the provider once** at the root layout; install with `npx expo install`, verify with `expo-doctor`.
4. **Theme centrally** from the [`design/frontend-design`](../../../../design/frontend-design/SKILL.md) output via [`styling`](../styling/SKILL.md); wire dark mode off `useColorScheme` + a toggle.
5. **Verify:** a themed screen renders on both platforms; a dialog/snackbar fires; dark mode toggles cleanly with no per-component edits; `testID`s land on rendered native views (testability).

## Validation

- App builds on iOS + Android (`expo run` / EAS) and `expo-doctor` is clean (New-Arch compatible).
- The theme/provider resolves once at the root; a dialog and a snackbar render from the kit.
- Dark mode toggles from one control and follows system (`useColorScheme`), with no per-component color edits.
- Only one styling authority present (no Nativewind + competing StyleSheet color on one element).
- `testID` set inline on a kit control appears on the rendered native view.

## Handoffs

- Hand-written `StyleSheet`, tokens as JS objects, dark-mode token swap, type scale → [`styling`](../styling/SKILL.md)
- `testID` per-kit mechanics → [`testability`](../testability/SKILL.md)
- Component layering (atom/molecule/organism), prop-drilling limits → [`reference`](../reference/SKILL.md)
- Native UI patterns (Pressable, expo-image, native menus/modals) → [`ui-conventions`](../ui-conventions/SKILL.md)
- Provider placement, dev-client-vs-Expo-Go decision → [`project-scaffold`](../project-scaffold/SKILL.md)
- Forms/validation with kit inputs → [`forms`](../forms/SKILL.md)
- Theme palette/fonts source → [`design/frontend-design`](../../../../design/frontend-design/SKILL.md) (primary), `design/theme-factory` (quick-start)
- Breakpoints, orientation, safe areas → [`responsive-design`](../responsive-design/SKILL.md)
