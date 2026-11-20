---
name: i18n
description: Use when a Mac app must support more languages or regions (String Catalogs, plurals, FormatStyle, RTL window layouts). Triggers "translate the app". Not for copy wording (design:ux-writing).
disable-model-invocation: true
---

# macOS: Localization and Globalization

Two jobs: **localization** (swap the text via catalogs) and **globalization** (format numbers, dates, money and plurals for the locale; always relevant, even with one language). On macOS the **system owns the locale and the per-app language**, and SwiftUI mirrors window layout for RTL as long as the code uses leading / trailing. Web analog: [`fe-react:i18n`](../../../../frontend/react/skills/languages/SKILL.md): stable ids, plurals in the catalog, no concatenated sentences. Sibling: [`mobile-ios:i18n`](../../../../mobile/ios/skills/languages/SKILL.md) (the same catalog and `FormatStyle` rules; the Mac adds menus, window titles and an AppKit lane). Audit rows are section P of `desktop-macos:standards-audit`.

## Version lane

| Concern | macOS 14+ (primary) | `[mac13]` / AppKit |
|---|---|---|
| Catalog | **String Catalog** `.xcstrings` (Xcode 15+): extraction, state, plurals, device variations | Compiled to `.strings` / `.stringsdict` at build; deploys back |
| Lookup | `String(localized:)`, `LocalizedStringResource`, SwiftUI `Text("…")` | AppKit: `String(localized:)` / `NSLocalizedString` in existing code; new strings still go in the catalog |
| Formatting | `FormatStyle`: `.formatted(.number)`, `.currency(code:)`, `.dateTime`, `.relative`, `ListFormatStyle`, `Measurement` | Same |
| Layout | Leading / trailing; the `layoutDirection` environment | AppKit: `leadingAnchor`, `NSDirectionalEdgeInsets`, `userInterfaceLayoutDirection` |
| Per-app language | System Settings → General → Language & Region → Applications, once the app has more than one localization | Same |
| `[mac27SDK]` | Nothing changes for catalogs; confirm any newer translation tooling in the installed Xcode | |

**New strings go in a String Catalog, never a new `.strings` file.** An existing `.strings` / `.stringsdict` file is migrated with Xcode's "Migrate to String Catalog". Facts are long-standing API, not re-confirmed against Apple pages this session.

## When to use

- Adding a language, or setting up localization from nothing
- Plural, gendered or device-specific wording; interpolated strings
- Dates, money, numbers and measurements that look wrong in another locale
- An RTL language (Arabic, Hebrew, Persian, Urdu) in a Mac window with sidebar, toolbar and inspector
- Menu titles, window titles, toolbar labels, purpose strings and the app name per language

## When NOT to use

- Wording, tone, microcopy → [`design:ux-writing`](../../../../design/ux-writing/SKILL.md)
- VoiceOver language, label rules → [`accessibility`](../accessibility/SKILL.md)
- Layout mechanics, density, materials → [`styling`](../styling/SKILL.md)
- Store listing text per locale → [`desktop/_shared/distribution`](../../../_shared/distribution/SKILL.md)
- Windows apps → `desktop-windows:languages` (`.resw`); iOS → `mobile-ios:i18n`

## String Catalogs

- **`Localizable.xcstrings`** is the default table; other tables (`Menus.xcstrings`) are named in the call. **`InfoPlist.xcstrings`** localizes `CFBundleDisplayName` and **every `NS…UsageDescription`** ([`sandbox-and-permissions`](../sandbox-and-permissions/SKILL.md)): an English-only purpose string in a Spanish app is a gap.
- **Xcode extracts strings at build**: `Text("…")`, `String(localized:)`, `LocalizedStringResource` and `Label`, `Button`, `Toggle` titles appear automatically with state **New → Needs Review → Translated**; a string no longer in code is **Stale**.
- **Keys**: English sentence as the key (the default) or a **symbolic key** (`library.empty.title`); one style per app.
- **A comment for translators** on every non-obvious string: `String(localized: "Open", comment: "Menu item that opens the selected album")`. A menu item is a verb: say so.
- **A `String` is not localized by `Text`.** `Text(someString)` is verbatim; a custom view takes `LocalizedStringKey` or `LocalizedStringResource`, not `String`. Data that must not translate uses `Text(verbatim:)`.
- **Never build a sentence by concatenation**; word order and plurals differ. Interpolation lives inside the localized string:

```swift
Text("^[\(count) album](inflect: true)")

let summary = String(localized: "\(count) albums imported from \(folder)", comment: "Import result line")
```

- **Plurals and variations are catalog features**: **Vary by Plural** adds the categories the language needs; **Vary by Device** adds Mac-specific wording where it differs. Pass the **count as an integer** so the catalog can vary on it.
- **Menus, commands and windows are localized text too.** `CommandMenu("Library")`, `Button("Add Album…")` in `commands`, `.navigationTitle`, `Window("Activity", id:)`, toolbar `Label`s, `Settings` tab titles, alert and confirmation text, tooltips (`.help(…)`) and accessibility labels all go through the catalog. A keyboard shortcut is **not** translated, but one that depends on a letter in the English word is a review question in a language where the letter differs.
- **No hard-coded UI string** once localization is on.
- A stored `LocalizedStringResource` (`static let title: LocalizedStringResource = "Library"`) resolves **when used**; a `String` built once at launch freezes the language.

## Globalization: `FormatStyle`, not formatters in a loop

```swift
struct PriceText: View {
    let amount: Decimal
    let currencyCode: String

    var body: some View {
        Text(amount, format: .currency(code: currencyCode))
    }
}

let importedOn = album.importedAt.formatted(.dateTime.day().month(.wide).year())
let names = artists.formatted(.list(type: .and))
```

- **The currency comes from the data, the locale from the user.** Never infer a currency from the locale; money is a `Decimal` or integer minor units, never a `Double`.
- **Dates are stored and sent as ISO 8601 UTC** and formatted at the edge; pass `timeZone:` explicitly when the time belongs to a zone.
- **`DateFormatter` / `NumberFormatter` are expensive**: never build one in `body` or a table cell. Prefer `FormatStyle`.
- A **fixed-format** date (file name, API) uses `en_US_POSIX` or `ISO8601FormatStyle`; a user-visible date never uses a hand-written pattern.
- `Measurement.formatted()` follows the user's measurement system; `PersonNameComponents.formatted()` orders names by locale; **sorting visible text** (table columns, sidebars) uses `localizedStandardCompare` / `.localizedStandard`, not `<` on strings. A `Table` sort comparator on text uses `KeyPathComparator(\.title, comparator: .localizedStandard)`.
- The first weekday, calendar and number system come from `Calendar.current` / `Locale.current`. The locale can change while the app runs: derive on render, never cache formatted text in a `static let`.
- File and document names the user sees are localized display names (`FileManager.displayName(atPath:)`), not raw paths.

## Following the system

- **Per-app language** appears in System Settings automatically with more than one localization; the app does **not** build its own language picker (platform conventions first). A picker is a recorded product decision. Previews and tests override the locale through the environment only.
- Declare shipped languages from the project's Localizations list; a language with an incomplete catalog is **not** added: a half-translated app is worse than the fallback. `CFBundleDevelopmentRegion` is the fallback: a missing translation shows the source string, never a raw key.
- **Server-sent copy**: notification text carries a key plus arguments resolved from the app's catalog; API text is localized by the server from `Accept-Language`, which `URLSession` sends from `Locale.preferredLanguages`.
- Export with `xcodebuild -exportLocalizations`, re-import with `-importLocalizations`; the catalog stays the source of truth.

## RTL

- SwiftUI **mirrors layout automatically**: `HStack` reverses, `.leading` / `.trailing` flip, a `NavigationSplitView` puts the sidebar on the right and the inspector on the left. **Use `.leading` and `.trailing`**, never `.left` / `.right`.
- **Window chrome mirrors itself** (title bar traffic lights stay on the left by system convention; do not move them). Toolbar order follows the system.
- **Do not mirror** logos, clocks, media transport controls, or phone numbers and other LTR runs. System symbols that are directional mirror themselves (`chevron.forward`); a custom directional image gets `.flipsForRightToLeftLayoutDirection(true)`.
- Mixed-direction text is handled by the system's bidi layout; never reorder by hand.
- `[AppKit]` use `leadingAnchor` / `trailingAnchor`, `NSDirectionalEdgeInsets`, and `NSCell` / `NSTableColumn` alignment `.natural`, never `.left`.
- **Test with pseudolanguages**: the scheme's Run → Options → *Application Language* offers *Right-to-Left Pseudolanguage* and *Double-Length Pseudolanguage*. Previews: `.environment(\.layoutDirection, .rightToLeft)`.
- **Layouts survive 30 to 50 % longer text**: no fixed-width labels, `lineLimit(nil)` or a deliberate `minimumScaleFactor`, `ViewThatFits` for button rows, a toolbar that overflows instead of clipping. A Mac window is resizable: a long German label grows the window's minimum size, not a truncated button.
- One test id per element regardless of language ([`test-ids`](../test-ids/SKILL.md)): a locator built from a translated string breaks in every other locale.

## Rules

Standards come from the desktop-macos rule file `mac-localization.md` in `.claude/rules/desktop-macos/` (`/desktop-macos:rules` installs it), or the plugin's copy when the project has none; CLAUDE.md § Desktop code rules wins where they differ.

## Procedure

1. Detect the existing setup (`.xcstrings`, legacy `.strings`, `.stringsdict`, third-party i18n), supported languages and development region; keep one system.
2. New or migrated strings go in a String Catalog; extract with a build, review state per language, add translator comments.
3. Replace literals with `String(localized:)` / `Text("…")`, including menus, window titles and tooltips; replace concatenation with interpolation; add plural and device variations.
4. Replace `DateFormatter` / `NumberFormatter` / `"$\(x)"` with `FormatStyle`; take currency from data.
5. Add `InfoPlist.xcstrings` for the display name and every purpose string.
6. Run with the pseudolanguages and one real RTL language; fix hard-coded `.left` / `.right` and fixed widths.

## Validation

- The catalog shows no *New* or *Needs Review* in a shipped language; no *Stale* entries linger.
- Double-Length and RTL pseudolanguages: no truncated primary action, the menu bar and toolbar read correctly, nothing laid out left-to-right that should mirror.
- A Mac set to Arabic and a region with different separators: plurals read correctly, numbers and dates follow the region.
- `rg 'Text\("[^"]*" *\+'` and `rg '\.(left|right)\b'` → none in shared views (P2, P6).
- Dev-side tests: formatting helpers with a fixed `Locale` and `TimeZone` injected ([`unit-testing`](../unit-testing/SKILL.md)); no test depends on the machine's locale.

## Handoffs

- Wording and voice → [`design:ux-writing`](../../../../design/ux-writing/SKILL.md)
- Labels and VoiceOver language → [`accessibility`](../accessibility/SKILL.md)
- Layout, density, mirrored icons → [`styling`](../styling/SKILL.md)
- Menu titles and commands → [`menus-and-commands`](../menus-and-commands/SKILL.md)
- Purpose strings per resource → [`sandbox-and-permissions`](../sandbox-and-permissions/SKILL.md)
- Test ids that ignore language → [`test-ids`](../test-ids/SKILL.md)
