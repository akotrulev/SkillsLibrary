# Design language: detection and the style interview

A **design language** here is seven parts: palette (surfaces, text tones, accent, status set, light and dark), type (faces, weights, scale), spacing (base unit and scale), radius, elevation (borders, shadows, what floats), components (the library and its density), and iconography (family, size, stroke). A prototype uses the project's language as it stands. This file says where to find each part, how to show what was found, what to do when parts are missing, and how to choose a language when there is none.

## Detection order

Walk the sources in this order. For each part, the first source that answers it wins; later sources fill only the parts still open. Read the stack from the project first (`package.json`, `*.csproj`, `Package.swift` or `*.xcodeproj`, `build.gradle.kts`, `app.json`), the same way the corpus skill does.

1. **A persisted corpus design system.** `design-system/<project-slug>/MASTER.md`, written by the corpus's `--persist`. When `design-system/<project-slug>/pages/<page>.md` exists for this screen, its values override the master's. It answers every part it states, on every stack.
2. **Tokens in the code**, per stack:

   | Stack | Where to look | Yields |
   |---|---|---|
   | React, Next.js, Vite | `tailwind.config.*` (`theme.extend`); a Tailwind v4 `@theme` block in the global CSS (search for `@theme`); custom properties on `:root` and `.dark` or `[data-theme]` in `globals.css` / `app.css` / `index.css` | palette, type, spacing, radius, elevation; light and dark when both blocks exist |
   | shadcn/ui | `components.json` (`style`, `baseColor`, `cssVariables`, `iconLibrary`), then the CSS variables it points at | palette and radius from the variables; component style; icon family |
   | MUI, Mantine, Chakra | the `createTheme` / `MantineProvider theme` / `createSystem` or `extendTheme` file | palette, type, spacing, radius, shadows; light and dark from the colour-scheme setup |
   | Style Dictionary, DTCG | `*.tokens.json`, `tokens/**/*.json` | whatever tiers they define; read the semantic tier, not the primitives |
   | Blazor | the component library's theme (MudBlazor `MudTheme` with `PaletteLight` / `PaletteDark`, Fluent UI Blazor design tokens and `FluentDesignTheme`, a Radzen theme), then `:root` in `wwwroot/app.css` | palette, type, radius, elevation; light and dark from the theme's two palettes |
   | React Native | the theme module (`theme.ts`, `constants/Colors.ts`), `tamagui.config.ts`, a NativeWind `tailwind.config.js`, a Unistyles theme | palette, type, spacing, radius; light and dark when the module has both |
   | iOS, macOS (SwiftUI) | `Assets.xcassets/**/*.colorset/Contents.json` (light and dark appearances), `Color`, `Font` and `ShapeStyle` extensions | palette with appearances, type roles; no named colour means the system semantic colours |
   | Android (Compose) | `ui/theme/Color.kt`, `Type.kt`, `Theme.kt` (`lightColorScheme` / `darkColorScheme`, dynamic colour), `Shape.kt`; `res/values/colors.xml`, `themes.xml` | palette, type scale, shapes; dynamic colour means a Material 3 baseline stands in for the wallpaper |
   | Windows (WinUI, WPF) | `ResourceDictionary` files merged in `App.xaml`, with `ThemeDictionaries` for Light, Dark and HighContrast; accent overrides of `SystemAccentColor` | palette per theme, radius (`ControlCornerRadius`), type ramp; none found means the Fluent defaults |

3. **The component library and one or two existing screens.** The library in `package.json` (or the stack's equivalent) names the components. Read one or two screens closest to the one being prototyped for what tokens do not say: density (row height, table or cards), spacing habits, page anatomy (sidebar or top navigation, page header shape), button hierarchy, empty-state treatment, and the icon import (`lucide-react`, `@phosphor-icons/react`, SF Symbols, Material Symbols, Segoe Fluent Icons).
4. **The plan and the brand.** `docs/plans/<NNN>-*/experience-plan.md` gives the screen's purpose, its states and its anatomy; read it for the variants, not for the language. A brand book, a logo or brand colours with no tokens behind them are an intake for `brand-import`: say so, offer `/design:brand-import`, and use the stated brand values for this prototype only, with the corpus filling the rest (see "Partial language" below).

Native targets render in HTML as an approximation: the system font stack (`-apple-system, "SF Pro Text"` on Apple platforms, `Roboto` on Android, `"Segoe UI Variable"` on Windows) and the platform's semantic colours, with no web font loaded.

## The design-language block

Show it before building, one row per part, each with the file and line it came from:

```
Design language — <screen>, <date>
| Part        | Value                                   | From                         |
|-------------|-----------------------------------------|------------------------------|
| Palette     | <surfaces, accent, status set, themes>  | <file:line>                  |
| Type        | <faces, weights, scale>                 | <file:line>                  |
| Spacing     | <base unit, scale>                      | <file:line>                  |
| Radius      | <scale>                                 | <file:line>                  |
| Elevation   | <borders, shadows, what floats>         | <file:line>                  |
| Components  | <library, density, the pieces used>     | <file or folder>             |
| Iconography | <family, size, stroke>                  | <file:line>                  |
Missing: <parts>, asked below.
```

When the language came from the style interview, the **From** column cites the corpus rows: the style id, the colour row, the typography pairing.

The same sources go into the file's `prototype-language` line, shortened to one line.

## Partial language

- **Found parts are used as they are.** A value the project defines is never improved, recoloured or replaced, even when the corpus suggests better. A contrast failure in the project's own tokens is reported to the user, not fixed here.
- **Only the missing parts are asked**, in one round, each with a recommended answer that fits the parts already found. Take the recommendation from the corpus, queried with the found parts as constraints: a missing pairing from `--domain typography` with the product's mood, a missing status set from `--domain color` in the palette's temperature, missing spacing from the `--density` dial.
- **Two sources that disagree** on one part (two accents, two radius scales) are one question: which one is current.
- **The answers stay in the prototype.** Writing them into the project's tokens is `visual-identity`'s or `brand-import`'s work, offered and never done here.

## Style interview

Used when detection found no part at all. A round is one set of questions asked together. With a multiple-choice question tool (AskUserQuestion), a round is at most 4 questions with 2–4 options each, the recommended option first and labelled `(Recommended)`. Without one, a round is numbered text: `**Q1 — <title>:** <body>`, then `➡️ <recommended answer>`, worded so "yes" accepts it.

**Round one**, four questions:

1. **Product and audience**: what the product is and who uses it, in what setting ("booking app for a yoga studio's members, on their phones").
2. **Mood**: two or three words ("calm, warm, trustworthy").
3. **Density**: spacious, standard, or dense (dashboard).
4. **Theme**: light, dark, or both.

Map the answers to the corpus dials: density spacious → `--density 3`, standard → `5`, dense → `8`. Mood words that ask for restraint ("calm", "minimal", "quiet") → `--variance 3`; neutral → `5`; "bold", "playful", "editorial" → `8`. An application screen takes `--motion 2`, since its motion is feedback only.

**The query.** Run the design-system search once per direction, without `--persist`. Installed as a plugin:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/design/ui-ux-pro-max/scripts/search.py" "<product> <industry> <mood>" --design-system --variance <1-10> --motion <1-10> --density <1-10> --json
```

Inside the SkillsLibrary repo:

```bash
python3 design/ui-ux-pro-max/scripts/search.py "<product> <industry> <mood>" --design-system --variance <1-10> --motion <1-10> --density <1-10> --json
```

The first run uses the answers as given. Build the second and third directions by moving one input each: the next-strongest mood word, or the variance dial one tier up or down. `design_system.source_identities` in the JSON names the rows to cite (`style`, `color`, `typography`). Check that `design_system.category` fits the product; when it does not, retry once with a narrower query, and when that also misses, say the direction is a fallback.

**Round two**, one question: the 2–3 directions as its options. Each option names its style (id and name), its palette row with the accent and surface hexes, its font pairing, whether it supports dark, and one line on how it would feel on this screen. The recommended direction is the one closest to the stated mood.

**Done when** one direction is chosen. Show it as the design-language block, with corpus rows as its sources, and offer `visual-identity` to make it the project's real tokens (delegate to the stack agent, or type `/design:visual-identity`).
