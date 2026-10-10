---
name: mobile-ios-languages
description: Use when an iOS app must support more than one language or region — String Catalogs (.xcstrings), String(localized:), plural and device variations, FormatStyle for numbers, dates and money, RTL layout, per-app language, localized purpose strings. Triggers "add Spanish", "translate the app", "Arabic layout flips", "date shows wrong format". Do NOT use for copy voice (`design-ux-writing`), text scale (`mobile-ios-accessibility`) or the web (`fe-react-languages`).
---

# iOS — Localization and Globalization

Two jobs: **localization** (swap the text via catalogs) and **globalization** (format numbers, dates, money and plurals for the locale — always relevant, even with one language). On iOS the **device owns the locale and the per-app language**, and the system mirrors layout for RTL on its own as long as the code uses leading/trailing. Web analog: [`fe-react-languages`](../../../../frontend/react/skills/languages/SKILL.md) — stable ids, plurals in the catalog, no concatenated sentences; routing by locale prefix does not carry over. Sibling: [`mobile-react-native-languages`](../../../react-native/skills/languages/SKILL.md).

## Version lane

| Concern | iOS 17+ (primary) | `[iOS16]` |
|---|---|---|
| Catalog | **String Catalog** `.xcstrings` (Xcode 15+) — extracts, tracks state, holds plurals and device variations | Deploys back to iOS 12; compiled to `.strings` / `.stringsdict` at build |
| Lookup | `String(localized:)`, `LocalizedStringResource`, SwiftUI `Text("…")` (a `LocalizedStringKey`) | Same |
| Formatting | `FormatStyle` — `.formatted(.number)`, `.currency(code:)`, `.dateTime`, `.relative`, `ListFormatStyle`, `Measurement` | Same (iOS 15+) |
| Layout | Leading / trailing; `layoutDirection` environment | Same |
| Per-app language | Settings → App → Language, shown automatically once the app has more than one localization | Same (iOS 13+) |
| `[iOS27 SDK]` | Nothing changes for catalogs; confirm any newer translation-assist tooling in the installed Xcode | — |

**New strings go in a String Catalog, never a new `.strings` file.** An existing `.strings` / `.stringsdict` file is migrated with Xcode's "Migrate to String Catalog" (right-click the file), not extended. Facts are long-standing API, not re-confirmed against Apple pages this session (plan D23).

## When to use

- Adding a language, or setting up localization from nothing
- Plural, gendered or device-specific wording; interpolated strings
- Dates, money, numbers and measurements that look wrong in another locale
- An RTL language (Arabic, Hebrew, Persian, Urdu)
- Purpose strings, the app name and notification copy per language

## When NOT to use

- Wording, tone, microcopy → [`design-ux-writing`](../../../../design/ux-writing/SKILL.md)
- Dynamic Type, VoiceOver language → `mobile-ios-accessibility`
- Layout mechanics, safe areas, size classes → [`styling`](../styling/SKILL.md)
- App Store listing text per locale → [`mobile-shared-release`](../../../_shared/release/SKILL.md)
- The web app's locale routing → [`fe-react-languages`](../../../../frontend/react/skills/languages/SKILL.md)

## String Catalogs

- **`Localizable.xcstrings`** is the default table; other tables (`Errors.xcstrings`) are named in the call (`String(localized: "…", table: "Errors")`). **`InfoPlist.xcstrings`** localizes the `Info.plist` keys — `CFBundleDisplayName` and **every `NS…UsageDescription`** ([`device-features`](../device-features/SKILL.md)) — so an English-only purpose string in a Spanish app is a gap, and a review question.
- **Xcode extracts strings at build**: `Text("Order shipped")`, `String(localized:)`, `LocalizedStringResource` and `Label`, `Button`, `Toggle` titles appear in the catalog automatically with state **New → Needs Review → Translated**; a string no longer in code is **Stale** (delete after a check).
- **Keys**: the Xcode default uses the **English sentence as the key** — fine and self-extracting; for a long or reused string use a **symbolic key** (`orders.empty.title`) with the English value in the catalog. Pick one style per app and keep it.
- **A comment for translators** on every non-obvious string: `String(localized: "Open", comment: "Button that opens a delivered order")` — "Open" is a verb or an adjective by language.
- **A `String` is not localized by `Text`.** `Text(someString)` shows the string verbatim; a custom view that takes a title takes `LocalizedStringKey` or `LocalizedStringResource`, **not** `String`, so the call site stays localized. Data that must not be translated (a user's name, a server value) uses `Text(verbatim:)`.
- **Never build a sentence by concatenation** (`"You have " + count + " orders"`) — word order and plurals differ. Interpolation lives **inside** the localized string:

```swift
Text("^[\(count) order](inflect: true)")

let summary = String(localized: "\(count) orders shipped to \(city)", comment: "Delivery summary line")
```

- **Plurals and variations are catalog features**: in the String Catalog editor, **Vary by Plural** adds the categories the language needs (Arabic has six, Russian four, Japanese one), and **Vary by Device** adds iPhone / iPad / Mac wording. The source stays one call; the variations are data, not `if count == 1` in code. The `inflect: true` markdown form (above) handles simple English-style nouns; anything beyond that uses a catalog variation.
- Pass the **count as an integer argument** (`%lld`) so the catalog can vary on it; a pre-formatted `String` count cannot be pluralised.
- Accessibility labels, hints, `placeholder`s, alert and confirmation-dialog text, tab titles and widget / intent titles ([`system-integration`](../system-integration/SKILL.md)) are localized the same way — **no hard-coded UI string** once localization is on.
- A `StaticString` or `LocalizedStringResource` stored in a constant (`static let title: LocalizedStringResource = "Orders"`) resolves **when used**, in the user's current locale — a `String` built once at launch freezes the language.

## Globalization — `FormatStyle`, not formatters in a loop

```swift
struct PriceText: View {
    let amount: Decimal
    let currencyCode: String

    var body: some View {
        Text(amount, format: .currency(code: currencyCode))
    }
}

let shippedOn = order.shippedAt.formatted(.dateTime.day().month(.wide).year())
let eta = order.eta.formatted(.relative(presentation: .named))
let names = participants.formatted(.list(type: .and))
```

- **The currency comes from the data, the locale from the user.** Never infer a currency from the locale; never format money with a fixed separator or a `"$"` literal. Money is a `Decimal` or integer minor units, never a `Double`.
- **Dates are stored and sent as ISO 8601 UTC** and formatted at the edge. `Date.FormatStyle` honours the locale, calendar and 12/24-hour setting; pass `timeZone:` explicitly when the time must be in a specific zone (a delivery in the recipient's zone).
- **`DateFormatter` and `NumberFormatter` are expensive to build** — never create one in `body` or a list row. Prefer `FormatStyle` (a cheap value); where a formatter is unavoidable, create one per locale and share it (a property of a model or `@State`, not a global mutable cache — [`basics`](../basics/SKILL.md)).
- A **fixed-format** date (`"yyyy-MM-dd"` for a file name or API) uses `Locale(identifier: "en_US_POSIX")` or `ISO8601FormatStyle`; a user-visible date never uses a hand-written pattern.
- `Measurement` + `.formatted()` for distance, weight and temperature follows the user's measurement system; `PersonNameComponents.formatted()` orders names by locale; sorting visible text uses `localizedStandardCompare` / `.sorted(using: .localizedStandard)`, not `<` on strings.
- The **first weekday**, calendar (Gregorian, Buddhist, Hijri) and number system (Arabic-Indic digits) come from the user's locale — read them from `Calendar.current` / `Locale.current`, never a constant.
- Locale **changes while the app runs** (Settings, region change): SwiftUI's `\.locale` environment updates; a value cached in a model or a `static let` of formatted text does not — derive on render.

## Following the device and the OS

- **Per-app language** appears in Settings automatically when the project has more than one localization; the app **does not build its own in-app language picker** — it links to `UIApplication.openSettingsURLString` where a user wants a different language (platform conventions first, CLAUDE.md § Mobile code rules). A picker is a product decision recorded with a reason, and it overrides with `Bundle`/environment locale only for SwiftUI previews and tests.
- Declare the shipped languages (`CFBundleLocalizations` is derived from the project's Localizations list) — a language with an incomplete catalog is **not** added to the list: a half-translated app is worse than the fallback. Track per-language coverage in the catalog's progress column.
- `CFBundleDevelopmentRegion` is the fallback language: a missing translation shows the source string, never a raw key. A symbolic-key catalog needs the development-language value filled in.
- **Server-sent copy**: push notifications carry `loc-key` + `loc-args` resolved from the app's catalog ([`notifications-and-links`](../notifications-and-links/SKILL.md)); text from an API is localized by the server from `Accept-Language`, which `URLSession` sends from `Locale.preferredLanguages` — the app does not translate API strings.
- Export for translators with `xcodebuild -exportLocalizations` and re-import with `-importLocalizations` (XLIFF); the catalog stays the source of truth in the repo.

## RTL

- SwiftUI **mirrors layout automatically** when the language is RTL: `HStack` reverses, `.leading` / `.trailing` flip, `NavigationStack` back moves to the right. **Use `.leading` and `.trailing`** (`.padding(.leading)`, `Edge.Set.horizontal`, `Alignment.leading`) — **never `.left` / `.right`** or `UIEdgeInsets.left`.
- **System symbols mirror themselves** where meaning is directional (`chevron.forward`, `arrow.backward`); prefer the `forward`/`backward` names to hard-coded `left`/`right` chevrons. A custom directional image gets `.flipsForRightToLeftLayoutDirection(true)`; **do not mirror** logos, clocks, media transport controls, or phone numbers and other LTR text runs.
- Mixed-direction text (an English brand name in an Arabic sentence) is handled by the system's bidi layout — never reorder by hand. A numeric field stays LTR inside RTL content.
- `[UIKit]` use `leadingAnchor` / `trailingAnchor`, `NSDirectionalEdgeInsets`, and `semanticContentAttribute` only where a control must not flip (a media scrubber).
- **Test with pseudolanguages**: the scheme's Run → Options → *Application Language* offers *Right-to-Left Pseudolanguage* and *Double-Length Pseudolanguage* (truncation) with no translations needed. Previews: `.environment(\.layoutDirection, .rightToLeft)` and `.environment(\.locale, Locale(identifier: "ar"))`.
- Layouts that survive 30–50 % longer text: no fixed-width labels, `lineLimit(nil)` or a deliberate `minimumScaleFactor`, `ViewThatFits` for button rows — [`styling`](../styling/SKILL.md).
- One test id per element regardless of language ([`test-ids`](../test-ids/SKILL.md)) — a locator built from a translated string breaks in every other locale.

## Procedure

1. Detect the existing localization setup (`.xcstrings`, legacy `.strings`, `.stringsdict`, third-party i18n), supported languages and development region; keep one system.
2. New or migrated strings go in a String Catalog; extract with a build, review state per language, add translator comments.
3. Replace literals with `String(localized:)` / `Text("…")`; replace concatenation with interpolation; add plural and device variations in the catalog.
4. Replace `DateFormatter` / `NumberFormatter` / `"$\(x)"` with `FormatStyle`; take currency from data.
5. Add `InfoPlist.xcstrings` for the display name and every purpose string.
6. Run with the pseudolanguages and one real RTL language; fix hard-coded `.left`/`.right` and fixed widths.

## Validation

Inside a `Gate: none` plan task, run none of these and report "written, not run"; the plan's gate task runs them.

- The catalog shows no *New* or *Needs Review* in a shipped language; no *Stale* entries linger.
- Run with the Double-Length and RTL pseudolanguages: no truncation of primary actions, nothing laid out left-to-right that should mirror.
- A device set to Arabic and a region with different separators: plurals read correctly, numbers and dates follow the region.
- `rg 'Text\("[^"]*" *\+'` and `rg '\.(left|right)\b'` → none in shared views (P2, P5).
- Dev-side tests: formatting helpers with a fixed `Locale` and `TimeZone` injected; no test depends on the machine's locale.

## Handoffs

- Wording and voice → [`design-ux-writing`](../../../../design/ux-writing/SKILL.md)
- Dynamic Type, VoiceOver language, accessibility strings → `mobile-ios-accessibility`
- Layout, size classes, mirrored icons in the design system → [`styling`](../styling/SKILL.md)
- Purpose strings per resource → [`device-features`](../device-features/SKILL.md)
- Notification copy by key → [`notifications-and-links`](../notifications-and-links/SKILL.md)
- Store listing per locale, screenshots → [`mobile-shared-release`](../../../_shared/release/SKILL.md)
- Test ids that ignore language → [`test-ids`](../test-ids/SKILL.md)
