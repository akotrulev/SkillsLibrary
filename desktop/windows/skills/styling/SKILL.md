---
name: styling
description: Use when theming a WinUI app (Fluent 2 theme resources, light/dark/High Contrast, Mica, type ramp, icons, motion, DPI). Triggers "dark mode". Not for control structure (ui-components).
disable-model-invocation: true
---

# Windows — Styling (Fluent 2, theme, motion)

How a WinUI app looks: **theme resources, never literals; light, dark and High Contrast from one set of dictionaries; one backdrop per window; the Windows type ramp; Segoe Fluent Icons; motion that honours the animation-effects setting.** Audit rows: section E of `desktop-windows:standards-audit`. Design facts come from `design/ui-ux-pro-max --stack winui` (WPF lane: `--stack wpf`); the corpus wins over this skill. Cite the row you used.

## Version lane

| Concern | Primary (WinUI, WinAppSDK 2.6) | Other lane |
|---|---|---|
| Backdrop | `Window.SystemBackdrop` = `MicaBackdrop` / `DesktopAcrylicBackdrop`; `SystemBackdropElement` hosts one inside a `CornerRadius` (2.0) | WPF: Fluent theme opt-in, `ThemeMode` (.NET 9+); "Fluent style support still in progress" (.NET 10). WinForms: `Application.SetColorMode` (.NET 10), no Mica |
| Theme resources | `{ThemeResource}` in `ResourceDictionary.ThemeDictionaries` (`Default`, `Light`, `Dark`, `HighContrast`) | WPF: `DynamicResource` + `Fluent` merged dictionaries |
| Binding a theme resource from code | Experimental `SetThemeResourceBinding` (2.5.4-exp): **never** in production | — |
| OS floor for Mica | Windows 11 (build 22000); below it the backdrop falls back to a solid colour | — |

## When to use

- Defining colours, brushes, typography, corner radius, spacing, icons
- Dark mode and High Contrast; choosing Mica vs Acrylic
- Motion, transitions, the animation-effects setting; DPI and adaptive layout

## When NOT to use

- Control choice, templates, `x:Bind`, dialogs → [`ui-components`](../ui-components/SKILL.md)
- Titlebar, `AppWindow`, snap layouts → `desktop-windows:windows-and-navigation`
- Labels, UI Automation, contrast ratios, text scaling → `desktop-windows:accessibility`
- `.resw`, RTL → `desktop-windows:languages`
- WPF theme details → `desktop-windows:wpf`

---

## Theme resources, not literals

- **Colours and brushes come from the system theme resources** (`TextFillColorPrimaryBrush`, `LayerFillColorDefaultBrush`, `CardBackgroundFillColorDefaultBrush`, `AccentFillColorDefaultBrush`, `ControlStrokeColorDefaultBrush`). A hex literal or `Colors.White` in a page is a finding: it breaks dark mode and High Contrast.
- **App-specific brushes** go in `Resources/Theme.xaml` with a key in **each** of `Light`, `Dark` and `HighContrast`:

```xml
<ResourceDictionary xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
                    xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
  <ResourceDictionary.ThemeDictionaries>
    <ResourceDictionary x:Key="Light">
      <SolidColorBrush x:Key="StatusPositiveBrush" Color="#0F7B0F" />
    </ResourceDictionary>
    <ResourceDictionary x:Key="Dark">
      <SolidColorBrush x:Key="StatusPositiveBrush" Color="#6CCB5F" />
    </ResourceDictionary>
    <ResourceDictionary x:Key="HighContrast">
      <SolidColorBrush x:Key="StatusPositiveBrush" Color="{ThemeResource SystemColorHighlightColor}" />
    </ResourceDictionary>
  </ResourceDictionary.ThemeDictionaries>
</ResourceDictionary>
```

- **Use `{ThemeResource}`, not `{StaticResource}`,** for anything that changes with theme; `StaticResource` freezes the value at load.
- **Accent colour is the user's.** Use `AccentFillColorDefaultBrush` and friends; never hard-code a brand colour over it. A brand colour is for an identity moment (logo, a primary call to action), checked for 4.5:1 contrast on every theme.
- **Never state by colour alone:** pair a status colour with an icon or text (CLAUDE.md § Desktop code rules).
- **Styles in dictionaries,** merged once in `App.xaml`; a style copied per page is a finding. Implicit styles over `Style="{StaticResource …}"` repeated on every element.

## Dark mode and High Contrast

- **Follow the system:** leave `RequestedTheme` unset on the app. An in-app theme toggle is a setting that stores `Light` / `Dark` / `Default` and sets `FrameworkElement.RequestedTheme` on the window's root; `Default` follows the OS.
- **High Contrast is a first-class theme.** Keep controls on system resources so the user's palette applies; for a custom brush, give it a `HighContrast` entry mapped to a `SystemColor*Color` (above). **Test every screen in High Contrast** (Settings → Accessibility → Contrast themes) — borders appear, fills disappear, images with baked-in text vanish.
- **Never rely on a background fill to separate regions** in High Contrast; keep a stroke (`ControlStrokeColor…`) too.
- **Detect a change at runtime** with `AccessibilitySettings.HighContrastChanged` only when custom drawing needs it; XAML theme resources update by themselves.

## Backdrop: Mica

- **Mica is the base layer of a long-lived window,** applied **once** (one backdrop per window), visible through the titlebar. **Mica Alt** is for a window with a tabbed titlebar.
- **Content sits on the layer brush:** `LayerFillColorDefaultBrush` on Mica; `LayerOnMicaBaseAltFillColorDefaultBrush` on Mica Alt. Do not stack a second Mica or Acrylic on top of it.
- **Acrylic** (`DesktopAcrylicBackdrop`) is for transient surfaces (flyouts, context menus), which the controls already do. Not for the main window.

```xml
<Window.SystemBackdrop>
  <MicaBackdrop Kind="Base" />
</Window.SystemBackdrop>
```

- **Mica falls back to a solid colour** when transparency is off, on battery saver, on low-end hardware, when the window is inactive, and below build 22000. Never assume it is visible; text must keep contrast on the fallback.
- **High Contrast:** Mica shows the user's chosen colour; check text on it.
- **Windowing details** (the titlebar, caption buttons) are `desktop-windows:windows-and-navigation`.

## Typography: Segoe UI Variable and the type ramp

- **One font, Segoe UI Variable** (the default for common controls; optical size matches the requested size automatically). **Non-Latin UI** uses the recommended font per language (`LanguageFont` APIs; Yu Gothic UI, Microsoft YaHei UI, Malgun Gothic, Nirmala UI) — do not force Segoe UI Variable over them.
- **Use the type-ramp styles, never raw `FontSize`:**

| Style | Size / line height (epx) | Weight |
|---|---|---|
| `CaptionTextBlockStyle` | 12 / 16 | Regular |
| `BodyTextBlockStyle` | 14 / 20 | Regular |
| `BodyStrongTextBlockStyle` | 14 / 20 | Semibold |
| `BodyLargeTextBlockStyle` | 18 / 24 | Regular |
| `SubtitleTextBlockStyle` | 20 / 28 | Semibold |
| `TitleTextBlockStyle` | 28 / 36 | Semibold |
| `TitleLargeTextBlockStyle` | 40 / 52 | Semibold |
| `DisplayTextBlockStyle` | 68 / 92 | Semibold |

- **Weights: Regular and Semibold.** No bold, no italic in UI (dyslexia); **sentence case** for all UI text including titles; **left-aligned** by default (centre only under an icon).
- **Minimum:** 12 px Regular, 14 px Semibold. Smaller is illegible in some languages.
- **Text scales** with Settings → Accessibility → Text size; never lock `IsTextScaleFactorEnabled="False"` on a `TextBlock` (CLAUDE.md § Desktop code rules). Lay out with room to grow.
- **Truncate with ellipsis** (`TextTrimming="CharacterEllipsis"`) in a defined container; clip only in a container with no visible boundary.
- Fluent type ramp values re-checked 2026-11-15 against learn.microsoft.com (typography, 2026-07-14).

## Icons and imagery

- **Segoe Fluent Icons** through `FontIcon` (glyph from the font) or `SymbolIcon`; they inherit foreground colour, scale with DPI and follow High Contrast. A custom `FontIcon` font family is a finding unless an icon pack requires it.
- **Raster images** ship at 100 / 125 / 150 / 200 / 300 % scale (`logo.scale-200.png`); a single bitmap blurs at 200 %. Prefer vector (`SVG` via `ImageIcon` / `SvgImageSource`) for glyph-like art.
- **Every icon-only control has an accessible name and a tooltip** ([`ui-components`](../ui-components/SKILL.md)).

## Shape and spacing

- **Corner radius uses the global resources:** `ControlCornerRadius` (4 px; Button, TextBox, ListView, bars) and `OverlayCornerRadius` (8 px; `ContentDialog`, `Flyout`, `MenuFlyout`, `TeachingTip`). `ToolTip` is 4 px. Never a literal `CornerRadius="6"`. Override the two in `App.xaml` to retheme everything at once.
- **Nested corners shrink:** an element inside an 8 px container is 4 px. Touching segments (a `SplitButton`) are not rounded where they meet. Windows are square when maximized or snapped.
- **Spacing on the 4 px grid** (4 / 8 / 12 / 16 / 24 / 32); page margins 24 px; no literal `Margin="7,3"`. Spacing values are theme-level resources when reused.

## Motion — and the animation-effects setting

- **Prefer implicit transitions and the built-in control animations** (`EntranceThemeTransition`, `RepositionThemeTransition`, `Implicit.Showing` / `Hiding`); a hand-written `Storyboard` only when none fits. Animate **opacity and transform** (composition-thread), not layout properties (`Width`, `Margin`), which run on the UI thread and jank.
- **Honour Settings → Accessibility → Visual effects → Animation effects** (`UISettings.AnimationsEnabled`): when off, state changes are instant, with no parallax, slide or loop. Read it once into a service the view models share, not per animation; the built-in transitions already comply, a custom `Storyboard` must check it.
- **No looping or auto-playing decorative animation;** nothing that flashes more than three times per second.
- **Progress** uses `ProgressRing` / `ProgressBar` (indeterminate only when the duration is unknown).

## DPI and adaptive layout

- **Design in effective pixels;** XAML scales for 100–500 %. Never read `RasterizationScale` to multiply a size by hand except for pixel-exact interop.
- **Per-monitor DPI v2** is the WinUI default: a window dragged to another monitor rescales. Test at 100 %, 150 %, 200 % and across two monitors.
- **Adaptive:** the window is freely resizable; use `Grid` and `*` rows, `AdaptiveTrigger` / `VisualStateManager` for narrow widths (a `NavigationView` collapses its pane automatically), and a minimum window size the content genuinely needs. Never fixed `Width` / `Height` on a page.
- **Snap layouts** work when the window keeps the system maximize button and is resizable; do not remove it.

## Common gotchas

- **`{StaticResource}` for a theme brush** — stays light after the user switches to dark.
- **A second `SystemBackdrop` or an opaque `Background` on the root `Grid`** — hides Mica.
- **`Foreground="Black"`** on text — invisible in dark and High Contrast.
- **`FontSize="13"`** — off the ramp, does not follow the style.
- **A custom `Storyboard` that ignores `AnimationsEnabled`.**
- **Forgetting the `HighContrast` key** in a custom dictionary — falls back to `Default`, often a light colour on a dark theme.
- **Experimental controls** (`TableView`, `Chart`) styled for a demo and left in a production build — never ship them.

## Handoffs

- Control structure, dialogs, `InfoBar` → [`ui-components`](../ui-components/SKILL.md)
- Titlebar, window chrome, navigation → `desktop-windows:windows-and-navigation`
- Contrast, scaling, UI Automation → `desktop-windows:accessibility`
- Localised fonts, RTL, `FlowDirection` → `desktop-windows:languages`
- WPF Fluent opt-in → `desktop-windows:wpf`; WinForms dark mode → `desktop-windows:winforms`
- Startup cost of resources → `desktop-windows:performance`
