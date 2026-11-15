---
paths:
  - "**/*{View,Window,Row,Sheet,Form,Inspector,Scene,Controller,Cell}.swift"
  - "**/{Views,Windows,Scenes,Components,UI,Inspectors,Controllers,ViewControllers,Theme,DesignSystem}/**/*.swift"
---

<!-- desktop-macos rules v1 (2026-11-15): styling, density and motion. Installed by /desktop-macos:rules; edit the paths above to where this project keeps its UI. -->

# Mac styling and motion standards

Severity tags as in the core Swift rules: **blocker**, **major**, **minor**, **nit**. The codebase wins where it consistently does otherwise. Design facts (palette, type pairing, spacing) come from the design corpus (`design/ui-ux-pro-max --stack swiftui`), not from these rules.

## Styling and layout

- Take Liquid Glass: the 27 SDK cannot be opted out of; no custom toolbar or sidebar background, no `.ultraThinMaterial` behind a system bar, no glass on glass. *major*
- Semantic colours and system materials first; brand colours are named asset-catalog sets with Any, Dark and High Contrast variants. No hex, fixed font size or magic spacing in a view. *minor*
- The user's accent colour is respected for selection and controls unless the brand colour carries meaning. *minor*
- Text uses system text styles at Mac sizes (13 pt body); a custom font scales with the text styles. *major*
- Density follows `.controlSize`: regular by default, smaller only in dense inspectors; a sheet re-applies its `controlSize` on the 27 SDK. *minor*
- Translucent custom surfaces have an opaque fallback under Reduce Transparency; borders and separators strengthen under Increase Contrast. *major*
- Layout adapts to window size, never to a device idiom; the minimum window size is set and honoured by sidebar, content and inspector; no fixed-size main window. *major*
- Platform-native look: no imported iOS, Material or web palette and no imitation of another OS's controls. *major*

## Motion

- Custom animation honours Reduce Motion: movement becomes a fade or nothing, and the state change still shows. *major*
- `.animation(_:value:)` always carries `value:`, close to the changed property. *major*
- Looping and long animations have a stop condition and stop with the window. *major*
- Animate composited properties (offset, scale, opacity, rotation, colour), not `frame` or `padding`; a transition sits on a conditional view inside `withAnimation`; no `Timer` driving frames. *minor*
