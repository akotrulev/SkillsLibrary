---
name: styling
description: Use when styling SwiftUI — Liquid Glass (forced by the iOS 27 SDK) on system chrome and custom glass surfaces, semantic colours, Dynamic Type text styles, asset-catalog colour and image tokens, dark mode, size classes, resizable iPad windows. Triggers "custom colours", "my bar looks flat", "support iPad", "Dynamic Type clips". Do NOT use for view structure (`mobile-ios:ui-components`), routes (`-navigation`) or motion (`-animation`).
---

# iOS — Styling, Liquid Glass and Adaptive Layout

One styling authority: **the system plus an asset-catalog token layer.** System materials, semantic colours and text styles carry the platform look; the catalog carries your brand. Design facts come from `design/ui-ux-pro-max` — `search.py "<query>" --stack swiftui` (rows 16–20 spacing and modifiers, 42–44 accessibility) and `app-interface.csv`; where this skill and the corpus disagree, the corpus wins. Brand direction, palettes and type pairing are `design/visual-identity`, `design/design-tokens` and `design/theme-presets`; this skill applies them on iOS.

## Version lane

| Concern | Xcode 27 / iOS 27 SDK (primary) | Notes |
|---|---|---|
| **Liquid Glass** | **Forced.** Linking the iOS 27 SDK applies it to system bars, tabs, sheets, buttons and search; **`UIDesignRequiresCompatibility` is ignored** | There is no opt-out. Adopt it: remove custom bar backgrounds that fight it, and treat a custom glass surface as the exception |
| Custom glass | `glassEffect(_:in:)`, `GlassEffectContainer`, `.buttonStyle(.glass)` / `.glassProminent` | Introduced with iOS 26; confirm signatures in the installed SDK's docs before use |
| `[iOS16]` / iOS 17–25 deployment | Glass APIs are availability-gated (`#available(iOS 26, *)`) with a plain-material fallback | The deployment target, not the SDK, decides which APIs are guarded |
| Semantic colours, text styles, asset catalog | iOS 13+ | No lane |
| `Color(.accent)`-style generated asset symbols | Xcode 15+ (`ASSETCATALOG_COMPILER_GENERATE_ASSET_SYMBOLS`) | Supported |
| `[UIKit]` | `UIColor` named assets, `UIFont.preferredFont(forTextStyle:)`, `UIGlassEffect` for glass | [`uikit`](../uikit/SKILL.md) |

A project built with an older SDK keeps its look until it moves; **never advise opting a project out of Liquid Glass once it links the iOS 27 SDK**, and never raise a deployment target to reach a glass API.

## When to use

- Defining colours, type and spacing; theming dark mode
- A bar, sheet or button looks wrong after the SDK change
- Adding a custom glass surface
- Making a screen work at accessibility text sizes, on iPad and in a resizable window

## When NOT to use

- Structure, states, lists → [`ui-components`](../ui-components/SKILL.md)
- Route containers, tabs, sheets → [`navigation`](../navigation/SKILL.md)
- Motion and transitions → `mobile-ios:animation`
- VoiceOver and Differentiate Without Color mechanics → `mobile-ios:accessibility`
- Brand identity from scratch → `design/visual-identity`
- Android Material → `mobile-android:styling`; RN → `mobile-react-native:styling`

## Inputs needed

- Brand palette (light and dark) and any custom font
- Deployment target; devices (iPhone only vs iPad)
- Which surfaces are custom (a floating control, a media overlay)

## Liquid Glass — take it, don't fight it

Standard components adopt it by recompiling. The work is **removing what contradicts it**:

- **Delete custom `toolbarBackground`, `UINavigationBarAppearance` and tab-bar backgrounds** that paint over the system material, and `.background(.ultraThinMaterial)` stacked behind a system bar.
- **Let content scroll under bars.** Do not pin content to a fixed inset; use `safeAreaInset`, `scrollContentBackground`, and the scroll-edge effect so content reads through the glass. Custom tab bars (a `ZStack` pretending to be a `TabView`) get no glass — replace with `TabView` ([`navigation`](../navigation/SKILL.md)).
- **Use `.buttonStyle(.glass)` / `.glassProminent`** for controls floating over content; `.borderedProminent` for in-content primary actions. Do not put glass on glass.
- **Glass is for the navigation layer**, floating above content — not for content rows, cards or full-screen backgrounds. Tint sparingly: a tint signals the primary action.
- **Custom glass surface** (the exception):

```swift
GlassEffectContainer(spacing: 12) {
    HStack(spacing: 12) {
        Button("Filter", systemImage: "line.3.horizontal.decrease") { showFilters = true }
            .buttonStyle(.glass)
            .accessibilityIdentifier("Orders.FilterButton")
        Button("Sort", systemImage: "arrow.up.arrow.down") { showSort = true }
            .buttonStyle(.glass)
            .accessibilityIdentifier("Orders.SortButton")
    }
}
```

  Group neighbouring glass in one `GlassEffectContainer` so it samples and morphs together. A `#available(iOS 26, *)` check with a `.regularMaterial` background is the fallback on a lower deployment target.
- **Legibility is yours.** Glass adds no contrast: text on or under it still meets contrast in light, dark and Increase Contrast, and Reduce Transparency must leave a readable result — test with both settings on.

## Colour — semantic first, catalog second

- **System colours and semantic styles** (`.primary`, `.secondary`, `Color(.systemBackground)`, `.tint`, `.foregroundStyle(.secondary)`) for everything that is not brand. They adapt to dark mode, Increase Contrast and Liquid Glass without code.
- **Brand colours are named colour sets in the asset catalog**, each with Any / Dark (and High Contrast) variants — the catalog is the token file. Generated symbols give `Color.brandPrimary`; the semantic names describe role (`accent`, `surfaceRaised`, `danger`), never the hue (`blue`).
- **`AccentColor` set** is the app tint; do not call `.tint(...)` on every view.
- **No hex literals in views.** A colour value in Swift code is a smell; the one place it appears is a computed colour that has no catalog form.
- **Never state by colour alone** — pair colour with a symbol, text or shape (Differentiate Without Color is honoured: `@Environment(\.accessibilityDifferentiateWithoutColor)`).
- Dark mode is a catalog variant, not a code branch; `@Environment(\.colorScheme)` only where an image or a chart genuinely needs it.

## Type — text styles and Dynamic Type

- **Use text styles** (`.font(.body)`, `.headline`, `.title2`) — never `.font(.system(size: 16))`. Weight and design through `.fontWeight` / `.fontDesign`.
- **A custom font is scaled**: `Font.custom("Brand-Regular", size: 17, relativeTo: .body)`; a fixed `size:` that does not scale is a defect. Bundle the font, list it in `UIAppFonts`, and check its licence.
- **`@ScaledMetric`** scales spacing and icon sizes with type: `@ScaledMetric(relativeTo: .body) private var iconSize = 24`.
- **Layouts survive the accessibility sizes (AX1–AX5).** Rows reflow: `ViewThatFits`, or switch an `HStack` to a `VStack` when `dynamicTypeSize.isAccessibilitySize`. Text wraps — `lineLimit(1)` on content that matters is a defect; truncation is by design only for secondary text.
- Never lock the text size (`.dynamicTypeSize(...)` caps are for dense chrome only and recorded). Test with Xcode's Environment Overrides and a `.dynamicTypeSize(.accessibility3)` preview.

## Spacing and tokens

Spacing, radii and sizes are a small set of named constants (a `Spacing` enum of static `let`s, or the catalog) — not magic numbers in each view. Prefer the system's default spacing (`VStack(spacing: nil)`, `padding()`) until the design needs otherwise. Touch targets are ≥ 44 pt — `.frame(minWidth: 44, minHeight: 44)` or `.contentShape(.rect)` on small controls.

## Adaptive layout — size classes, iPad, windows

- **Branch on width, not on device.** `@Environment(\.horizontalSizeClass)` (`.compact` / `.regular`) and `ViewThatFits`, never `UIDevice.current.userInterfaceIdiom` in a view.
- **`NavigationSplitView`** gives sidebar / content / detail that collapses to a stack on compact ([`navigation`](../navigation/SKILL.md)); a two-column layout is not hand-built with `HStack`.
- **Resizable iPad windows are the default:** a window can be any size, and Stage Manager / windowed mode resizes live. No `UIScreen.main.bounds`, no assumed orientation; read the container (`containerRelativeFrame`, `GeometryReader` only as a last resort) and let content reflow. Multitasking and multiple scenes are on; do not set `UIRequiresFullScreen`.
- **Readable width:** constrain body text on regular width with `.frame(maxWidth: 700)` or `readableContentGuide` equivalents so lines do not span a 13" screen.
- **Safe areas:** content respects them; backgrounds extend under them with `.ignoresSafeArea()` on the background only.
- **Landscape and the keyboard** are layouts to test, not afterthoughts.

## Rules

- Take Liquid Glass; delete custom bar backgrounds; glass belongs to the navigation layer.
- Semantic colours and system materials first; brand colours are named catalog sets with dark variants.
- Text styles only; custom fonts scale; spacing uses `@ScaledMetric` where tied to type.
- Branch on size class, never on device idiom; iPad windows are resizable.
- No colour-only meaning; contrast holds with Increase Contrast and Reduce Transparency.
- No hex, no fixed font size, no magic spacing in views.

## What NOT to do

- Advise `UIDesignRequiresCompatibility` or any opt-out of Liquid Glass.
- Layer `.ultraThinMaterial` behind a system bar, or glass on glass.
- Build a custom tab bar instead of `TabView`.
- Fix a Dynamic Type clip by capping the size or `lineLimit(1)`.
- Import a web or Material palette wholesale; imitate Android widgets.
- Assume a phone-sized or full-screen window.

## Validation (exit gate)

- [ ] No custom bar / tab / toolbar background fights the system material
- [ ] No hex literal or fixed `.system(size:)` in views; colours come from the catalog or semantic styles
- [ ] Each screen is checked at an AX3 size, in dark mode, with Increase Contrast and Reduce Transparency
- [ ] iPad: the screen reflows in a narrow and a wide window; no idiom checks
- [ ] Custom glass is grouped in a `GlassEffectContainer` and has a fallback where the target is below iOS 26

## Handoffs

- Views and states → [`ui-components`](../ui-components/SKILL.md)
- Tabs, split view, sheets → [`navigation`](../navigation/SKILL.md)
- Transitions, Reduce Motion → `mobile-ios:animation`
- VoiceOver, Differentiate Without Color → `mobile-ios:accessibility`
- Brand, tokens, palettes → `design/visual-identity`, `design/design-tokens`
- UIKit appearance → [`uikit`](../uikit/SKILL.md)
