---
paths:
  - "**/*.resw"
  - "**/*.resx"
  - "**/*.xaml"
  - "**/{Strings,Resources,Localization}/**"
---

<!-- desktop-windows rules v1 (2026-11-15): localization. Installed by /desktop-windows:rules; edit the paths above to where this project keeps its strings. -->

# Windows localization standards

Severity tags as in the core C# rules: **blocker**, **major**, **minor**, **nit**. The codebase wins where it consistently does otherwise. WinUI and C++/WinRT use `.resw` and `x:Uid`; WPF and WinForms use `.resx` and `CurrentUICulture`, and no `.resw` is added to them. *minor*

- No user-visible literal in XAML or code; every string has an identifier. *major*
- Every `x:Uid` property (`Button1.Content`) exists on the element's type, and no identifier collides. *major*
- Strings reach code through one injected `ResourceLoader` (or `ResourceManager`), never by concatenation or a pasted sentence. *major*
- Every declared language has the full identifier set, and the manifest declares the languages. *major for packaged*
- Plurals are chosen by category and separate strings, never `== 1`; plural support in MRT Core is not assumed. *major*
- Display formatting is culture-aware (`Format`, dates, numbers, currency); wire formats are invariant (`CultureInfo.InvariantCulture`). *major*
- Comparison and case change use the right culture mode (`StringComparison.Ordinal` for identifiers, culture for display). *minor*
- Layout survives right-to-left (`FlowDirection`) and 30–40% longer text; no fixed-width label. *minor*
- Manifest strings (`DisplayName`, `Description`) are localized through `ms-resource:`. *minor for packaged*
- Test ids and log messages are not localized. *major*
