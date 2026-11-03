---
paths:
  - "**/*{View,Screen,Row,Sheet,Form,Controller,Cell}.swift"
  - "**/{Views,Screens,Components,UI,Controllers,ViewControllers}/**/*.swift"
  - "**/*.xcstrings"
---

<!-- mobile-ios rules v1 (2026-11-03): localization. Installed by /mobile-ios:rules; edit the paths above to where this project keeps its UI. -->

# iOS localization standards

Severity tags as in the core Swift rules: **blocker**, **major**, **minor**, **nit**. The codebase wins where it consistently does otherwise.

- New strings live in a String Catalog; no new `.strings` or `.stringsdict` file. *major*
- No sentence built by concatenation, and no `if count == 1` plural: plurals and gendered wording are catalog variations. *major*
- Custom views take `LocalizedStringKey` / `LocalizedStringResource` for copy; `Text(verbatim:)` marks data. *minor*
- Layout uses leading and trailing, never left and right. *major*
- Dates, numbers and money use `FormatStyle`, never a formatter built per row or a literal; the currency comes from data, never the locale, and money is not a `Double`. *major*
- Fixed-format dates use a POSIX locale or ISO 8601; user-visible dates never do. *minor*
