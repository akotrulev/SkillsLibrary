---
paths:
  - "app/**/*.tsx"
  - "src/app/**/*.tsx"
  - "**/*.{native,ios,android}.tsx"
---

<!-- mobile-react-native rules v1 (2026-11-03): components, lists, styling. Installed by /mobile-react-native:rules; widen the paths above to this project's component folders. -->

# React Native components, lists and styling

Severity tags as in the core rules: **blocker**, **major**, **minor**, **nit**. The codebase wins where it consistently does otherwise.

- Platform conventions first: no iOS look on Android, no web look anywhere. Native primitives: `Pressable`, not `TouchableOpacity`; `expo-image`, not RN `Image`; a native modal, menu, sheet or `Switch`, not a JS one. *major*
- Every data list is virtualized: no `ScrollView` + `.map` over data of unknown size; FlashList or Legend List where the project has one. On FlashList 2 no `estimatedItemSize`, `inverted` or `MasonryFlashList`. *major*
- Rows are cheap: stable domain-id keys, one hoisted callback, primitives in, no inline object, style or closure in `renderItem`; no query, context stack or heavy `useMemo` in a row. *major*
- Compound components over boolean-prop sprawl. *minor*
- Images right-sized through `expo-image`; never a full-resolution image in a thumbnail. *minor*
- The first screen renders before heavy modules load; no analytics or crash SDK `init` blocks it; large libraries by leaf import, not a barrel. *minor*
- A performance change carries before and after numbers from a release build on a real device. *minor*
- One component kit per app, earned by a present need, its provider mounted once at the root. *major*
- One styling authority per element: never a `className` beside a competing `StyleSheet` colour; `StyleSheet.create`, no style literals in list items. *major*
- Tokens are a typed, purpose-named object; no hardcoded hex or literal values in styles; text colour set on the `<Text>`. *minor*
- Dark mode is an authored palette swapped by `useColorScheme()`, never hex inversion or per-component conditionals; contrast re-checked. *minor*
- Insets from `useSafeAreaInsets()` or `contentInsetAdjustmentBehavior`; no hardcoded notch offset, no `SafeAreaView` around a scroller. *major*
- Width from `useWindowDimensions()`, never `Dimensions.get` at module scope; no per-device-model branch; no orientation lock on large screens. *major*
- No legacy `shadow*` / `elevation` or gradient library on RN 0.76+. *minor*
