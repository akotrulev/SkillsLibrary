---
paths:
  - "**/*{View,Window,Row,Sheet,Form,Inspector,Scene,Commands,Controller,Cell}.swift"
  - "**/{Views,Windows,Scenes,Components,UI,Commands,Inspectors,Controllers,ViewControllers}/**/*.swift"
  - "**/*.xcstrings"
---

<!-- desktop-macos rules v1 (2026-11-15): localization. Installed by /desktop-macos:rules; edit the paths above to where this project keeps its UI. -->

# Mac localization standards

Severity tags as in the core Swift rules: **blocker**, **major**, **minor**, **nit**. The codebase wins where it consistently does otherwise.

- New strings live in a String Catalog; no new `.strings` or `.stringsdict` file. *major*
- Menu titles, command names, window titles, toolbar labels and Settings tab titles are localized text, with a translator comment on every non-obvious string; a menu item is a verb. *major*
- No sentence built by concatenation, and no `if count == 1` plural: plurals and Mac-specific wording are catalog variations. *major*
- Custom views take `LocalizedStringKey` / `LocalizedStringResource` for copy; `Text(verbatim:)` marks data. *minor*
- Every `NS…UsageDescription` and `CFBundleDisplayName` is localized in `InfoPlist.xcstrings`. *major*
- Layout uses leading and trailing, never left and right; window chrome is left to the system; logos and media transport controls are not mirrored. *major*
- Layouts survive 30 to 50 percent longer text: no fixed-width labels, toolbars overflow instead of clipping. *major*
- Dates, numbers and money use `FormatStyle`, never a formatter built per row or a literal; the currency comes from data, never the locale, and money is not a `Double`. *major*
- Fixed-format dates use a POSIX locale or ISO 8601; user-visible dates never do. *minor*
- No in-app language picker unless a recorded product decision asks for one; per-app language is in System Settings. *minor*
