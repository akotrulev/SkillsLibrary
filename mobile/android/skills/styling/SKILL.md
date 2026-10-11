---
name: styling
description: Use when theming a Compose app — Material 3 theme and tokens (1.4 stable vs Expressive in 1.5), dynamic colour, typography in sp, window size classes and adaptive layout, large-screen rules at target 36 / 37, edge-to-edge insets. Triggers "set up the theme", "dark mode", "tablet layout", "status bar overlaps". Do NOT use for component structure (`mobile-android:ui-components`), routes (`-navigation`) or TalkBack (`-accessibility`).
---

# Android — Styling, Theming and Adaptive Layout

One theme, tokens instead of literals: `MaterialTheme` colour scheme, typography and shapes read through `MaterialTheme.*`; dynamic colour with a fallback; sizes in `dp` and text in `sp`; layout that adapts to **window size classes** rather than device type; insets handled in composables. Design facts come from `design:corpus --stack jetpack-compose`; audit rows are section E of `mobile-android:standards-audit`.

## Version lane

| Concern | Material 3 1.4 (primary, stable) | Material 3 1.5 `[M3-1.5]` | Brownfield |
|---|---|---|---|
| Theme | `MaterialTheme(colorScheme, typography, shapes, content)` | **Material 3 Expressive stable in 1.5** (beta now): `MaterialExpressiveTheme`, `MotionScheme.expressive()`, expressive components | In 1.4 Expressive is `@ExperimentalMaterial3ExpressiveApi` — opt in only where the project already did |
| Dynamic colour | `dynamicLightColorScheme` / `dynamicDarkColorScheme`, API 31+ | Same | Same |
| Window size | `currentWindowAdaptiveInfo()` → `windowSizeClass` | Same; Large / Extra-large width need `supportLargeAndXLargeWidth = true` | Same, or manual `BoxWithConstraints` |
| Edge-to-edge | **Enforced at target 35** | Same | Targets below 35: call `enableEdgeToEdge()` anyway |
| Large screens | **Orientation / resizability locks ignored ≥ sw600dp at target 36; no opt-out at 37** | Same | Targets ≤ 35 still honour them |
| Material 2 `[M2]` | Not new work; migration is [`migration`](../migration/SKILL.md) | — | A finding where a screen mixes M2 and M3 |

Never raise the Compose BOM or opt into Expressive as a side effect of a styling task. A 1.5 beta dependency is a recorded decision.

## When to use

- Setting up or changing the theme, colours, typography, shapes
- Dark mode, dynamic colour, a brand palette
- Phones vs tablets / foldables / desktop windowing; list-detail layouts
- Status bar or keyboard overlapping content

## When NOT to use

- Composable structure, state, lists → [`ui-components`](../ui-components/SKILL.md)
- Motion → [`animation`](../animation/SKILL.md); contrast and TalkBack → [`accessibility`](../accessibility/SKILL.md)
- Navigation containers' behaviour → [`navigation`](../navigation/SKILL.md)
- String resources, RTL, locale formatting → `mobile-android:i18n`
- iOS / RN theming → `mobile-ios:styling`, `mobile-react-native:styling`

## Inputs needed

- Compose BOM / material3 version; brand colours and fonts, if any
- Minimum SDK (dynamic colour needs 31+) and the supported form factors
- Compose-only, or Views screens sharing the theme

## One theme, tokens everywhere

```kotlin
@Composable
fun AppTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    dynamicColor: Boolean = true,
    content: @Composable () -> Unit,
) {
    val context = LocalContext.current
    val colorScheme = when {
        dynamicColor && Build.VERSION.SDK_INT >= Build.VERSION_CODES.S ->
            if (darkTheme) dynamicDarkColorScheme(context) else dynamicLightColorScheme(context)
        darkTheme -> DarkColors
        else -> LightColors
    }
    MaterialTheme(colorScheme = colorScheme, typography = AppTypography, shapes = AppShapes, content = content)
}
```

- **Read tokens, never literals**: `MaterialTheme.colorScheme.primary`, `MaterialTheme.typography.bodyLarge`, `MaterialTheme.shapes.medium`. `Color(0xFF…)` or `TextStyle(fontSize = 14.sp)` inside a screen is a finding; palettes live in `Color.kt` / the theme file only.
- **Semantic roles** (`onSurfaceVariant`, `errorContainer`, `surfaceContainerHigh`) over brand names; pair `x` with `onX`. A custom role the scheme lacks (success, warning) is a `CompositionLocal` provided by `AppTheme`, defined once with light and dark values.
- **Dynamic colour (API 31+) on by default** with the static scheme as the fallback for lower SDKs and for a brand that must not shift — the choice is recorded. Generate the static scheme from a seed with the Material Theme Builder; do not hand-pick 30 roles.
- **Dark theme follows the system** (`isSystemInDarkTheme()`); a manual override lives in DataStore ([`offline-and-storage`](../offline-and-storage/SKILL.md)) and is passed in as the parameter. **No colour is fixed across themes** outside a brand mark.
- **Shapes and elevation** from `MaterialTheme.shapes` and tonal elevation, not hand-drawn corner radii; spacing from a small `Spacing` object (4 / 8 / 12 / 16 / 24 dp) read through a `CompositionLocal` or constants — one scale, not magic numbers.
- **State never by colour alone** — pair `error` colour with an icon and text; check contrast of custom pairs (4.5:1 text, 3:1 large text and UI — [`accessibility`](../accessibility/SKILL.md)).
- **Views screens `[Views]`** share the Material 3 XML theme (`Theme.Material3.DayNight`); a Compose `AppTheme` plus a matching XML theme, not two palettes ([`views-interop`](../views-interop/SKILL.md)).

## Material 3 Expressive — version-keyed

- **material3 1.4 (stable):** the standard theme above. Expressive APIs exist behind `@OptIn(ExperimentalMaterial3ExpressiveApi::class)` — acceptable only where the project already opts in and accepts API churn.
- **material3 1.5 `[M3-1.5]` (stable when it ships):** `MaterialExpressiveTheme` with `motionScheme = MotionScheme.expressive()`, and the expressive components. Adopting it is a deliberate redesign task — shape morphing, bolder tonal colour, springy motion — not a default.
- Never mix `MaterialTheme` and `MaterialExpressiveTheme` in one tree. Check the release notes (developer.android.com/jetpack/androidx/releases/compose-material3) for the exact stable version before writing it as fact.

## Typography — `sp`, scalable, never locked

- **Text sizes in `sp`**, drawn from `MaterialTheme.typography` (`displayLarge … labelSmall`); a screen picks a role, not a size. Custom fonts load through `FontFamily(Font(R.font.x, weight))` or downloadable fonts, with a fallback, and are wired once into `AppTypography`.
- **Text scales to 200% without clipping**: no fixed `height` / `size` on a text container, `minHeight` instead; `maxLines` with an ellipsis only for secondary text; primary content wraps. **Never lock scaling** (`Density(fontScale = 1f)`, `TextUnit` in `dp`).
- **Line height and tracking** come with the role; do not override per screen. Numbers in tables use `fontFeatureSettings = "tnum"`.
- Corpus: `design:corpus --stack jetpack-compose` and `--domain typography` for pairings; the platform default (Roboto Flex / the system font) is correct unless a brand font is specified.

## Window size classes and adaptive layout

```kotlin
val sizeClass = currentWindowAdaptiveInfo(supportLargeAndXLargeWidth = true).windowSizeClass
val showTwoPane = sizeClass.isWidthAtLeastBreakpoint(WindowSizeClass.WIDTH_DP_EXPANDED_LOWER_BOUND)
```

| Class | Width | Height |
|---|---|---|
| Compact | < 600 dp | < 480 dp |
| Medium | 600–839 dp | 480–899 dp |
| Expanded | 840–1199 dp | ≥ 900 dp |
| Large | 1200–1599 dp | — |
| Extra-large | ≥ 1600 dp | — |

- **Branch on the window size class, never on device type, `Configuration.screenWidthDp` in a layout, or `Build.MODEL`.** The value changes at runtime (rotation, split screen, fold) and the UI must follow without restarting.
- **Pass the class (or derived booleans) down as a parameter**; only the top of the tree reads `currentWindowAdaptiveInfo()`.
- **Navigation chrome adapts**: `NavigationSuiteScaffold` picks bottom bar (compact) / rail (medium) / drawer (expanded). **List-detail and supporting-pane** use the adaptive scaffolds from `material3-adaptive-layout`, wired to Navigation 3 scene strategies ([`navigation`](../navigation/SKILL.md)).
- **Content width is bounded** on wide windows (`Modifier.widthIn(max = 840.dp)` for reading text) rather than stretched; lists become grids (`GridCells.Adaptive(minSize = 160.dp)`).
- **Large screens at target 36 / 37:** orientation and aspect-ratio locks (`screenOrientation`, `resizeableActivity=false`, `maxAspectRatio`) are **ignored on ≥ sw600dp at 36 with no opt-out at 37** — the app is resizable and rotates whether it planned for it or not. Test in a resizable emulator and with the multi-window / desktop windowing modes. A layout assuming portrait is a finding.
- Keyboard and mouse support (focus order, hover, shortcuts) is part of large-screen quality, not a bonus.

## Insets and edge-to-edge

- **Content draws behind the system bars from target 35**; `enableEdgeToEdge()` in `onCreate` ([`project-setup`](../project-setup/SKILL.md)). The window's insets are consumed by composables, not by `android:fitsSystemWindows` or hard-coded dp.
- **`Scaffold` passes `innerPadding`** — apply it to the content root (`Modifier.padding(innerPadding)` or `contentPadding` of a lazy list). A `Scaffold` whose `innerPadding` is ignored is a finding.
- **Outside a `Scaffold`**: `Modifier.windowInsetsPadding(WindowInsets.safeDrawing)`, `.statusBarsPadding()`, `.navigationBarsPadding()`; a full-bleed image ignores them on purpose and its text re-applies them.
- **Keyboard**: `Modifier.imePadding()` (with `android:windowSoftInputMode="adjustResize"`); a field the keyboard covers is a defect (`mobile-android:forms`).
- Gesture-nav and 3-button bars, display cutouts (`WindowInsets.displayCutout`) and a foldable's hinge are inset sources; `safeDrawing` covers them.

## Rules

- One `AppTheme`; screens read `MaterialTheme.*` tokens, no colour or text-size literals.
- Dynamic colour with a recorded static fallback; dark theme follows the system.
- Text in `sp` from typography roles; layouts survive 200% font scale; scaling is never locked.
- Layout branches on window size class; the class is read once at the top.
- No orientation or resizability lock; wide windows get two panes or bounded width.
- Insets are consumed in composables; `Scaffold` `innerPadding` is applied.
- Expressive only on material3 1.5 or an existing opt-in.

## What NOT to do

- Hard-code `Color(0x…)`, `14.sp` or `RoundedCornerShape(8.dp)` in a screen.
- Test `isTablet`, `Build.MODEL` or `screenWidthDp` to pick a layout.
- Lock `screenOrientation` or set `resizeableActivity="false"`.
- Ignore `innerPadding`, or use `fitsSystemWindows` in Compose.
- Mix Material 2 and Material 3 in a screen, or adopt Expressive while "just styling".
- Fix a font size to stop text growing.

## Validation (exit gate)

- [ ] `rg -n "Color\(0x|fontSize = [0-9]|RoundedCornerShape\([0-9]" -g '*.kt'` hits only the theme files
- [ ] Layout checked at 200% font scale, dark theme, compact and expanded widths
- [ ] No orientation / resizability lock in the manifest; resizable emulator pass
- [ ] `innerPadding` applied; no status-bar or keyboard overlap

## Handoffs

- Components and state → [`ui-components`](../ui-components/SKILL.md)
- Navigation suite and panes → [`navigation`](../navigation/SKILL.md)
- Contrast, scaling, TalkBack → [`accessibility`](../accessibility/SKILL.md)
- Motion scheme → [`animation`](../animation/SKILL.md)
- Dark-mode preference storage → `mobile-android:offline-and-storage`
- M2 → M3, XML theme → [`migration`](../migration/SKILL.md), [`views-interop`](../views-interop/SKILL.md)
