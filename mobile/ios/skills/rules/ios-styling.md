---
paths:
  - "**/*{View,Screen,Row,Sheet,Form,Controller,Cell}.swift"
  - "**/{Views,Screens,Components,UI,Controllers,ViewControllers,Theme,DesignSystem}/**/*.swift"
---

<!-- mobile-ios rules v1 (2026-11-03): styling, adaptive layout and motion. Installed by /mobile-ios:rules; edit the paths above to where this project keeps its UI. -->

# iOS styling and motion standards

Severity tags as in the core Swift rules: **blocker**, **major**, **minor**, **nit**. The codebase wins where it consistently does otherwise. Design facts (palette, type pairing, spacing) come from the design corpus (`design/ui-ux-pro-max --stack swiftui`), not from these rules.

## Styling and layout

- Take Liquid Glass: no `UIDesignRequiresCompatibility` or other opt-out, no custom background or `.ultraThinMaterial` behind a system bar or tab bar, no glass on glass. *major*
- Semantic colours and system materials first; brand colours are named asset-catalog sets with dark variants. No hex, fixed font size or magic spacing in a view. *minor*
- A custom font scales with Dynamic Type. *major*
- Layout branches on size class, never on device idiom; never assume a phone-sized or full-screen window. *major*
- Platform-native look: no imported web or Material palette, no imitation of Android widgets. *major*

## Motion

- Custom animation honours Reduce Motion: movement becomes a fade or nothing, and the state change still shows. *major*
- `.animation(_:value:)` always carries `value:`, close to the changed property. *major*
- Looping and long animations have a stop condition. *major*
- Animate composited properties (offset, scale, opacity, rotation, colour), not `frame` or `padding`; a transition sits on a conditional view inside `withAnimation`; no `Timer` driving frames. *minor*
