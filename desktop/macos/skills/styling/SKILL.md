---
name: styling
description: Use when styling a Mac SwiftUI app (Liquid Glass, semantic colours, density, materials, Reduce Transparency, motion and Reduce Motion). Triggers "dark mode". Not for structure (ui-components).
---

# macOS — Styling, Liquid Glass, Density and Motion

One styling authority: **the system plus an asset-catalog token layer.** System materials, semantic colours and text styles carry the Mac look; the catalog carries your brand. Design facts come from `design/ui-ux-pro-max`: `search.py "<query>" --stack swiftui` (spacing and modifier rows, accessibility rows) and `app-interface.csv`; where this skill and the corpus disagree, the corpus wins. Brand direction, palettes and type pairing are `design/visual-identity`, `design/design-tokens` and `design/theme-presets`; this skill applies them on the Mac.

## Version lane

| Concern | Xcode 27 / macOS 27 SDK (primary) | Notes |
|---|---|---|
| **Liquid Glass** | **Forced.** Linking the macOS 27 SDK applies it to the toolbar, sidebar, sheets and controls; **`UIDesignRequiresCompatibility` is ignored** at macOS 27 | There is no opt-out. Adopt it; a custom glass surface is the exception |
| 27 automatic changes | A hard scroll-edge effect under free-floating title text; sidebars extend to the window edges with semibold selection; bordered toolbar items over the sidebar adopt glass | Remove what fights them |
| Custom glass | `glassEffect(_:in:)`, `GlassEffectContainer`, `glassEffectID(_:in:)`, `.buttonStyle(.glass)` / `.glassProminent` | **macOS 26+.** The pages are not machine-readable here: confirm each signature in the installed SDK's documentation before use |
| macOS 14–15 deployment | Glass APIs are gated with `#available(macOS 26, *)` and a plain-material fallback | The deployment target, not the SDK, decides which APIs are guarded |
| Concentric corners | `concentricCornerRadii` on `GeometryProxy` (SwiftUI), `NSView.cornerConfiguration` → `.containerConcentric` (AppKit, macOS 27) | `[mac27SDK]` |
| Control state resets | `controlSize`, `buttonSizing`, `menuIndicatorVisibility` and `ButtonBorderShape` **reset inside sheets and popovers** on the 27 SDK | Set them again inside the presented content |
| Inactive windows | `@Environment(\.appearsActive)` dims custom chrome | Any |
| `[AppKit]` | `NSVisualEffectView`, `NSColor` named assets, `NSFont.preferredFont`; AppKit's own design-compatibility key is **not verified**: do not advise one | [`appkit`](../appkit/SKILL.md) |

Never advise opting a project out of Liquid Glass once it links the macOS 27 SDK, and never raise a deployment target to reach a glass API.

## When to use

- Defining colours, type, spacing, dark mode; applying a brand
- A toolbar, sidebar or sheet looks wrong after the SDK change
- Adding a custom glass surface
- Density: control size, compact vs regular rows
- Adding animation, or making animation respect Reduce Motion

## When NOT to use

- Structure, states, lists → [`ui-components`](../ui-components/SKILL.md)
- Window placement, toolbars at window level → `windows-and-scenes`
- VoiceOver, Full Keyboard Access mechanics → `accessibility`
- Brand identity from scratch → `design/visual-identity`
- iOS Dynamic Type and iPad classes → `mobile-ios:styling`; Windows Fluent → `desktop-windows:styling`

## Inputs needed

- Brand palette (light and dark) and any custom font
- Deployment target; whether the window is resizable to narrow widths
- Which surfaces are custom (a floating control, a media overlay)

## Liquid Glass — take it, don't fight it

Standard components adopt it by recompiling. The work is **removing what contradicts it**:

- Delete custom `toolbarBackground` and `.background(.ultraThinMaterial)` stacked behind a system toolbar or sidebar.
- Let content scroll under the toolbar; use `safeAreaInset` and the scroll-edge effect so content reads through the glass. A title drawn over scrolling content gets the hard edge automatically: do not add your own gradient.
- A `NSTitlebarAccessoryViewController` may draw outside its bounds (glass shadows) when linked on 27: check clipping.
- Sidebars extend under the window edge: never pin a sidebar background colour.

**A custom glass surface is earned**, for one floating control group over rich content. A little goes a long way; interactive glass (bounce on click, pointer-aware) is for controls, not panels.

```swift
GlassEffectContainer(spacing: 12) {
    HStack(spacing: 12) {
        Button("Play", systemImage: "play.fill", action: play)
            .buttonStyle(.glass)
        Button("Shuffle", systemImage: "shuffle", action: shuffle)
            .buttonStyle(.glass)
    }
}
```

- Group nearby glass in one `GlassEffectContainer` (shared sampling, morphing); never glass on glass.
- Gate by `#available(macOS 26, *)` where the target is lower, with `.background(.regularMaterial, in: .rect(cornerRadius: 12))` as the fallback.
- Tint carries meaning (primary action), never decoration.

## Semantic colours and the token layer

- **Semantic first**: `.primary`, `.secondary`, `Color(nsColor: .windowBackgroundColor)`, `.tint`/accent. They adapt to light, dark, Increase Contrast and the user's accent colour.
- **Brand colours live in the asset catalog** with Any / Dark / High Contrast variants, read as generated symbols (`Color(.brandAccent)`; `ASSETCATALOG_COMPILER_GENERATE_ASSET_SYMBOLS = YES`). No `Color(red:green:blue:)` literal in a view.
- **Respect the user's accent colour** unless the brand colour carries meaning; never override the system accent for selection.
- **Never show state by colour alone**: pair a colour with an icon, a label or a shape (Differentiate Without Color).
- Contrast: body text 4.5:1 against its background in light, dark and with Increase Contrast; verify the High Contrast variant exists.

## Type, density and control size

Text styles first: `.body`, `.headline`, `.caption` and so on; **macOS default text is 13 pt, minimum 10 pt**. Dynamic Type on the Mac is **not verified**: do not claim the system text-size setting scales SwiftUI text like iOS; use text styles and relative layout, and say what you could not confirm.

| Item | Default | Minimum |
|---|---|---|
| Control | **28 × 28 pt** | **20 × 20 pt** |
| Text | **13 pt** | **10 pt** |

- `.controlSize(.small | .regular | .large)` for density; `.regular` is the default, `.small` for inspectors and dense tables, never below the minimum.
- A touch-capable Mac wants **larger targets without a denser or sparser layout**: let controls expand on touch (`buttonSizing`, hit-test padding with `.contentShape`) while keeping visual density.
- Custom fonts come from the asset bundle and scale with `Font.custom(_:size:relativeTo:)`; prefer the system font (San Francisco) for UI.
- Spacing on a 4 pt grid; `LabeledContent` and `Form` give Mac-correct alignment ([`forms`](../forms/SKILL.md)).

## Materials, transparency and contrast

- Use semantic materials (`.regularMaterial`, `.sidebar` via `NSVisualEffectView`) rather than hand-tuned opacity.
- **Reduce Transparency** (`accessibilityReduceTransparency`) makes materials and glass opaque: a custom translucent surface supplies an opaque fallback and is checked with the setting on.
- **Increase Contrast** (`colorSchemeContrast == .increased`) strengthens borders and separators; do not rely on a 1 pt hairline at 10 % opacity.
- Dark mode is not "invert": every asset has a dark variant; shadows lose weight, elevation is shown by material.

## Adaptive layout

A Mac window is resizable, movable, full-screen capable, and moves between displays and scales.

- Set a **minimum size** (`.frame(minWidth:minHeight:)` on the root, `.windowResizability(.contentMinSize)`) that keeps content usable; test at the minimum and at full screen on a large display.
- Use `ViewThatFits`, `NavigationSplitViewVisibility` and `Layout` for wide-vs-narrow; never test the device. Design for large displays: fewer nesting levels, less modality, comfortable density.
- Monitor and scale changes re-layout; images supply @1x/@2x or are vector. Window frame restoration is `windows-and-scenes`.

## Motion — and Reduce Motion

Motion explains change; it never decorates it, and the user can turn it off.

| Rule | Detail |
|---|---|
| **Honour Reduce Motion** | Read `@Environment(\.accessibilityReduceMotion)`; when `true`, replace movement, scaling and parallax with a cross-fade or no animation |
| **Transform and opacity only** | Animate `offset`, `scaleEffect`, `rotationEffect`, `opacity`; never animate layout-driving properties on a large view tree |
| **Short and interruptible** | 150–300 ms for UI feedback; use `.spring` / `.snappy` / `.smooth`; a new state interrupts the old animation |
| **Drive it by state** | `withAnimation` or `.animation(_:value:)`, never a timer; `PhaseAnimator` and `KeyframeAnimator` for multi-step |
| **Matched geometry** | `matchedGeometryEffect` for a shared element; glass morphing uses `glassEffectID` |
| **System transitions first** | `.transition(.opacity)`; window and sheet transitions are the system's |
| **Nothing essential is animation-only** | State the animation shows is also in the UI |
| **No infinite animation** by default; a `ProgressView` is allowed | Battery and distraction |

```swift
struct SyncBadge: View {
    let isSyncing: Bool
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    var body: some View {
        Image(systemName: "arrow.triangle.2.circlepath")
            .rotationEffect(.degrees(isSyncing && !reduceMotion ? 360 : 0))
            .animation(reduceMotion ? nil : .smooth, value: isSyncing)
            .opacity(isSyncing ? 1 : 0.4)
    }
}
```

Test with **System Settings → Accessibility → Display → Reduce motion** on; a view that moves must still communicate state.

## Common gotchas

- **Fighting glass**: a custom toolbar background; delete it.
- **Glass on glass**: a glass button inside a glass panel.
- **Sheet controls resetting size**: re-apply `controlSize` inside the sheet on the 27 SDK.
- **A fixed-height window**: no minimum size or no restoration.
- **Colour as the only signal**: add a symbol.
- **Animation with no Reduce Motion branch**.
- **A translucent surface with no Reduce Transparency fallback**.

## Validation (exit gate)

- [ ] No custom bar background paints over system glass; no glass on glass
- [ ] Colours are semantic or asset-catalog symbols with dark and High Contrast variants
- [ ] Controls are ≥ 20 pt, text ≥ 10 pt, and touch targets can expand
- [ ] Reduce Transparency, Increase Contrast and Reduce Motion are each handled and checked
- [ ] The window has a tested minimum size; no state is shown by colour alone
- [ ] Glass APIs below macOS 26 are availability-gated with a fallback

## Handoffs

- Structure and states → [`ui-components`](../ui-components/SKILL.md)
- Windows, toolbars, placement → `windows-and-scenes`
- VoiceOver, keyboard → `accessibility`
- Brand, tokens → `design/visual-identity`, `design/design-tokens`
- AppKit styling → [`appkit`](../appkit/SKILL.md)
