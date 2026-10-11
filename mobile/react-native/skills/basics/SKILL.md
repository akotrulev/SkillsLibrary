---
name: concepts
description: Use when explaining or checking React Native + Expo fundamentals on SDK 57 — New Architecture, Hermes V1, JS/UI/worklet threads, React Compiler, the web-React to RN map (no RSC, DOM, CSS cascade or SEO), Expo as the framework. Triggers "RN equivalent of X", "why no server component", "JS thread vs UI thread", "Expo Go vs dev build". Do NOT use for scaffolding (`mobile-react-native:project-setup`), routes (`-navigation`), screens (`-ui-components`) or React web (`fe-react:concepts`).
---

# React Native / Expo — Basics

The on-device rendering model and the "this isn't the DOM" surprises for developers arriving from React web. Everything runs **on the device**; there is no server render.

## Version lane

Detect the Expo SDK, React Native and React majors from `package.json` first; key every recipe to them. Never up-level a project as a side effect.

| Lane | Expo SDK | RN | React | Notes |
|---|---|---|---|---|
| **Primary** | **57** | 0.86 | 19.2 | Node ≥ 22.13, Xcode 26.4+, iOS 16.4+, Android 7+, compile/target SDK 36 |
| Next `[SDK58]` | 58 (beta) | 0.88 RC | 19.3 | Becomes primary the day it ships stable |
| Supported | 55–56 | 0.83 / 0.85 | 19.2 | SDK 56 + Hermes V1 has a Reanimated memory regression fixed in `expo@57.0.9` — steer to 57 |
| Floor | 54 | 0.81 | 19.1 | Last SDK where the legacy architecture can be on — migration bridge only |
| Below 54 | — | — | — | A finding plus a `mobile-react-native:migration` run; never author for it |

`[SDK58]` deltas, named where each skill owns them: native tabs stable at `expo-router/native-tabs`, Gesture Handler 3, Reanimated 4.7 + worklets 0.13, scene lifecycle default (iOS 27), AGP 9, Expo Router core reworked.

## Facts every skill assumes

- **New Architecture only** since RN 0.82 / SDK 55 (the interop layer still exists). Never author a Paper/bridge recipe.
- **Hermes V1** is the default engine (RN 0.84 / SDK 56). Release builds run bytecode.
- **React Compiler 1.0 is on** in the default template (`reactCompiler: true`): do not hand-write `useMemo` / `useCallback` / `memo` for render-cost reasons; keep them where identity matters (effect deps, Reanimated).
- **React Native officially recommends a framework, and it is Expo.** Expo Router, development builds, CNG.
- **RN 0.87 strict TS API**: deep `react-native/Libraries/*` imports are type errors; `InteractionManager` is removed.
- `EXPO_PUBLIC_*` is inlined in plain text — public, never a secret.
- Jest is the only runner (`jest-expo`); Vitest is not viable.

## When to use

- "What is the RN equivalent of `<div>` / `<a>` / CSS / `useMediaQuery`?"
- "Why is there no Server Component / `'use client'` here?"
- "What runs on the JS thread vs the UI thread?"
- "Expo Go vs development build vs bare — which am I on?"
- Confirming a recipe matches the detected lane before another skill applies it.

## When NOT to use

- Standing up a project, EAS, config plugins → [`project-setup`](../project-setup/SKILL.md)
- Routes, navigators, deep links → [`navigation`](../navigation/SKILL.md)
- Screens and components → [`ui-components`](../ui-components/SKILL.md)
- State library choice → [`architecture`](../architecture/SKILL.md)
- Animation → [`animation`](../animation/SKILL.md); lists and profiling → [`performance`](../performance/SKILL.md)
- React **web** → `fe-react:concepts`

## No server render

Every component runs on the device, always. There is:

- **No RSC, `'use client'`, `'use server'`, Server Actions or hydration.** There is no boundary to look for.
- **No SEO, metadata or crawling.** A binary is not a web page.
- **No URL as state.** State that would sit in the URL on web is a **typed route param** (screen-scoped) or a store (app-wide).
- **No DOM, no CSS cascade.** Styles are objects per element; nothing inherits except some `Text` props.

Carries over unchanged: hooks and their rules, one-way data flow, keys, exhaustive effect deps, React 19 APIs, Suspense, composition.

## Native primitives replace the DOM

| React web | React Native | Rule |
|---|---|---|
| `<div>` | `<View>` | Flexbox is the only layout; column is the default direction |
| bare text | `<Text>` | **All text inside `<Text>`** — `vendor/react-native-guidelines/rules/rendering-text-in-text-component.md` |
| `<a href>` | Expo Router `<Link href>` | A real link, not a handler on a `View` — [`navigation`](../navigation/SKILL.md) |
| `<button>` | `<Pressable>` | `vendor/.../rules/ui-pressable.md` |
| `<img>` | `Image` from `expo-image` | `vendor/.../rules/ui-expo-image.md` |
| `<input>` | `<TextInput>` | Controlled the same way; see [`forms`](../forms/SKILL.md) |
| scroll container | `ScrollView` (small) · FlashList / Legend List (lists) | Never `.map` a large array in a `ScrollView` — `vendor/.../rules/list-performance-virtualize.md` |
| CSS / `sx` | `StyleSheet.create` | No `@media`; responsiveness is `useWindowDimensions` — [`styling`](../styling/SKILL.md) |
| `data-testid` | `testID` | [`test-ids`](../test-ids/SKILL.md) |

## Threads

RN runs three contexts:

| Thread | Runs | Consequence |
|---|---|---|
| **JS** (Hermes) | Your components, effects, state | Heavy work drops frames; a re-render per frame is jank |
| **UI / main** | Native views, layout, drawing | Never blocked by app code in the managed lane |
| **Worklet** (UI runtime) | Reanimated worklets, Gesture Handler callbacks | Animates `transform` / `opacity` without the JS thread |

Animating through React state re-renders on the JS thread; animate through shared values on the worklet runtime — [`animation`](../animation/SKILL.md), `vendor/.../rules/animation-gpu-properties.md`, `animation-derived-value.md`. A JS-thread frame budget is a correctness rule (CLAUDE.md § Mobile code rules).

## New Architecture, briefly

- **JSI** — synchronous C++ interface between JS and native; no JSON bridge.
- **Fabric** — renderer; layout can be measured synchronously.
- **TurboModules** — lazily loaded native modules typed through Codegen.
- **Bridgeless** — the old bridge is gone.

An app developer's practical exposure is dependency compatibility: an unmaintained native library may not run. `npx expo-doctor` checks installed packages against React Native Directory.

## Expo workflows

| | Expo Go | Development build | Bare |
|---|---|---|---|
| Custom native code | No — SDK modules only | **Yes** — config plugins, Expo Modules | Yes |
| `ios/` `android/` in repo | No | No — generated by `prebuild` | Yes |
| This stack | prototypes only | **default for a real app** | brownfield / fallback lane `[bare]` |

Native configuration goes in **config plugins**, never hand edits to generated `ios/` / `android/` — [`project-setup`](../project-setup/SKILL.md).

## React 19 in RN

- `use()` + Suspense, `useActionState`, `useOptimistic` work on device; there are no Server Actions, so an action is a plain async function. Forms use React Hook Form + Zod — [`forms`](../forms/SKILL.md).
- `ref` is a plain prop; no `forwardRef` on React 19. On a React 18 project `forwardRef` is correct — do not flag it.
- The React Compiler has Reanimated gotchas: `vendor/.../rules/react-compiler-reanimated-shared-values.md`, `react-compiler-destructure-functions.md`.

## State discipline

One source of truth; derive everything else in render; subscribe to the minimum. `vendor/.../rules/state-ground-truth.md`, `react-state-minimize.md`, `react-state-fallback.md`, `react-state-dispatcher.md`; library choice in [`architecture`](../architecture/SKILL.md).

## Layering

Atom (one primitive, no domain) → molecule (a few atoms, one job) → organism (a section with its own data) → screen (a route file; owns navigation and the fetch). Prop-drilling past 2–3 levels moves to Context or a store; server state belongs to TanStack Query, never a store.

## Web ↔ RN cheat sheet

| Web idiom | React Native | Skill |
|---|---|---|
| `'use client'` | none | this file |
| Next.js routing | Expo Router file routes | [`navigation`](../navigation/SKILL.md) |
| CSS / MUI | `StyleSheet` / Expo UI / kit | [`styling`](../styling/SKILL.md) · [`component-library`](../component-library/SKILL.md) |
| `useMediaQuery` | `useWindowDimensions` + safe-area insets | [`styling`](../styling/SKILL.md) |
| service worker / PWA | MMKV + sync queue | [`offline-and-storage`](../offline-and-storage/SKILL.md) |
| axe / Lighthouse | `accessibilityRole` / `accessibilityLabel`, VoiceOver, TalkBack | [`accessibility`](../accessibility/SKILL.md) |
| Vitest + RTL | Jest + RNTL 14 (async APIs) | [`component-testing`](../component-testing/SKILL.md) |

## The vendored rules pack

`mobile/react-native/vendor/react-native-guidelines/rules/` holds impact-ranked rules with incorrect-vs-correct examples. Reach it through the skill that routes into it ([`performance`](../performance/SKILL.md), [`animation`](../animation/SKILL.md), [`ui-components`](../ui-components/SKILL.md), [`navigation`](../navigation/SKILL.md), this skill), never as a standalone skill. The vendored tree is read-only.

## Rules

- Detect the lane first; never author below the SDK 54 floor and never up-level.
- Never a Paper-architecture recipe as the primary path.
- All text inside `<Text>`; no URL-as-state; no DOM assumptions.
- Native changes go in config plugins; Expo Go is a prototype tool.
- Public config only in `EXPO_PUBLIC_*`.

## Handoffs

- Project scaffold, EAS → [`project-setup`](../project-setup/SKILL.md)
- Routing → [`navigation`](../navigation/SKILL.md)
- State → [`architecture`](../architecture/SKILL.md)
- Styling and adaptive layout → [`styling`](../styling/SKILL.md)
- SDK upgrades → [`migration`](../migration/SKILL.md)
- Review → [`code-review`](../code-review/SKILL.md)
