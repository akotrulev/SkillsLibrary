---
paths:
  - "**/*.xaml"
  - "**/{Themes,Styles,Resources,Assets}/**"
---

<!-- desktop-windows rules v1 (2026-11-15): Fluent 2 styling. Installed by /desktop-windows:rules; edit the paths above to where this project keeps its resources. -->

# Windows styling standards (Fluent 2)

Severity tags as in the core C# rules: **blocker**, **major**, **minor**, **nit**. The codebase wins where it consistently does otherwise. WPF and WinForms projects keep their own theme lane (`wpf.md`, `winforms.md`); the colour, scaling and High Contrast rules apply to all three.

- Colours come from theme resources, never literals; `{ThemeResource}` for anything that changes with the theme (`{StaticResource}` freezes it). *major*
- A custom brush has `Light`, `Dark` and `HighContrast` dictionary entries. *major*
- One backdrop (Mica or Acrylic) per window, none stacked on an opaque root; transparency settings are honoured. *minor*
- Typography uses the type-ramp styles (`BodyTextBlockStyle`, `SubtitleTextBlockStyle`, …), Regular and Semibold only; never a fixed pixel font size that ignores text scaling. *minor*
- Text scaling is never locked. *major*
- Corner radius uses `ControlCornerRadius` / `OverlayCornerRadius`; spacing sits on the 4 px grid. *nit*
- Motion honours the animation-effects setting; no decorative loop; transitions use the theme transitions. *major*
- Windows are adaptive: no fixed page sizes, a stated minimum size, visual states for narrow widths. *minor*
- State is never shown by colour alone; each state has an icon, a label or a shape. *major*
- Raster images ship at scale variants (`.scale-100/200/400`); icons come from Segoe Fluent Icons, not a bundled icon font. *nit*
- Design facts (palette, type, spacing, motion) come from `design/ui-ux-pro-max --stack winui | wpf`; where this file and the corpus disagree the corpus wins. *minor*
