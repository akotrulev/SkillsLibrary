---
name: languages
description: Use when a Windows app needs localization (.resw files, x:Uid, ResourceLoader, plurals, RTL, culture formats). Triggers "translate this app", "add German". Not for labels and Narrator (accessibility).
disable-model-invocation: true
---

# Windows — Languages and Localization

How a Windows app is localized: **every user-visible string lives in a `.resw` file, XAML binds to it with `x:Uid`, code reads it through one `ResourceLoader`, layout mirrors for right-to-left, and numbers, dates and sorting follow the user's culture.** Audit rows: section P of `desktop-windows:standards-audit`. Design facts: `design/ui-ux-pro-max --stack winui`.

## Version lane

| Concern | WinUI on WinAppSDK 2.6 (primary) | Note |
|---|---|---|
| Resources | `Strings/<bcp47>/Resources.resw`, one folder per language, `en-US` as the default | Learn, "Localize strings in your UI and app package manifest" (2026-09-05) |
| XAML | `x:Uid` + property identifiers (`Greeting.Text`) | Attached properties need `Greeting.[using:Microsoft.UI.Xaml.Automation]AutomationProperties.Name` |
| Code | `Microsoft.Windows.ApplicationModel.Resources.ResourceLoader` | The Windows App SDK type, not `Windows.ApplicationModel.Resources` (UWP) |
| Packaged | Declare each language in `Package.appxmanifest` (`<Resource Language="en-US"/>`), replacing `x-generate` | The manifest strings (`DisplayName`) also move to `.resw` via `ms-resource:` |
| `[unpackaged]` | `makepri new` builds `resources.pri` by hand, copied next to the `.exe`; the system display language is used, not the preferred-language list | Rebuild the PRI whenever a `.resw` changes |
| `[WPF]` `[WinForms]` | `.resx` + `ResourceManager` + `CultureInfo.CurrentUICulture`; WPF binds through a generated `Resources` class | Not `.resw`; never add MRT Core to a WPF app as a side effect |
| `[C++]` | Same `.resw` and `ResourceLoader` (`winrt::Microsoft::Windows::ApplicationModel::Resources`) | |

Detect first: `Strings/**/*.resw` or `*.resx`, `x:Uid` in XAML, the languages in the manifest, and a third-party localization library already in use. Extend what exists.

## Strings

### In XAML

```xaml
<TextBlock x:Uid="Orders.Heading" />
<Button x:Uid="Orders.Refresh" AutomationProperties.AutomationId="Orders.RefreshButton" />
```

```text
Orders.Heading.Text          Orders
Orders.Refresh.Content       Refresh
Orders.Refresh.[using:Microsoft.UI.Xaml.Automation]AutomationProperties.Name   Refresh orders
```

- **One `x:Uid` per element, and every property identifier must exist on that element's type.** `Greeting.Text` on a `Button` fails at run time. A `x:Uid` value overrides the same property set in markup, so leave the markup property empty.
- **A simple identifier (`Farewell`) and property identifiers on the same stem (`Farewell.Text`) cannot coexist:** a duplicate entry. Name code-loaded strings with a different stem.
- Identifiers are case insensitive and unique per file; **never rename one after it went to translators**: a shifted identifier is a deletion plus an addition and is retranslated.
- The `Comment` column is for translators: say who sees the string, what the placeholders are.
- A string that is not translatable (a brand, a protocol token, a test id) is not in `.resw`.

### In code

```csharp
public sealed partial class OrdersViewModel(ResourceLoader strings, IOrderService orders) : ObservableObject
{
    private string CountText(int count) =>
        string.Format(CultureInfo.CurrentCulture, strings.GetString("OrdersCount"), count);
}
```

- **One `ResourceLoader` per file, created once in the host and injected** (`desktop-windows:architecture`). View models never construct a loader or read `.resw` directly, and no `Strings` wrapper class is added to forward to it.
- A dotted name is read with slashes: `Orders.Heading.Text` → `GetString("Orders/Heading/Text")`.
- A second file is addressed `x:Uid="/ErrorMessages/PasswordTooWeak"`, and in code through the two-parameter `ResourceLoader(ResourceLoader.GetDefaultResourceFilePath(), "ErrorMessages")`. The one-parameter overload takes a `.pri` path, not a map name.
- **Never build a sentence by concatenation** (`"You have " + n + " orders"`): word order differs. Use one resource with a placeholder (`{0}`).
- A missing key throws or returns empty; a test loads every key the code names (`desktop-windows:unit-testing`).

### Plurals

`.resw` has **no plural forms** that this skill verified (2026-11-15; re-check on the Learn page before relying on it). Do not branch on `count == 1` in code: Arabic, Polish and Russian have more categories than English.

| Option | Use when |
|---|---|
| One key per CLDR category (`OrdersCount.One`, `.Few`, `.Other`) and a small pure function that picks the category for the culture | The project has a plural-rule source already; the function has a unit test per category and per language |
| A MessageFormat (ICU) library | The project already ships one; do not add it for one string |

Zero is its own message (`No orders`) in every language, never `0 orders`.

## Language selection

- **Default: the OS display language.** Packaged apps use the preferred-language list; fallback ends at the manifest's default language.
- An in-app language switch is a decision, not a default. If asked: set `ApplicationLanguages.PrimaryLanguageOverride` (packaged) and ask the user to restart, or build a `ResourceContext` with `Languages = new[] { "de-DE" }` for one lookup. Persist the choice in settings (`desktop-windows:offline-and-storage`).
- `CultureInfo.CurrentCulture` and `CurrentUICulture` are two settings: UI strings follow the second, number and date formatting the first.

## Formatting

| Value | Rule | Never |
|---|---|---|
| Date and time | `DateTimeOffset.ToString("d", culture)` / `"f"`; WinRT `DateTimeFormatter` for the user's regional settings | A hand-written `MM/dd/yyyy` |
| Number, currency | `ToString("N2", culture)`, `"C"` with the **currency of the data**, not the culture's | Hardcoding `$`; the culture's currency for a foreign amount |
| Lists, units | The formatter's pattern, or a resource with placeholders | Joining with `", "` and `" and "` |
| Sorting, search | `StringComparer.Create(culture, true)` or `CompareInfo` for display order; `StringComparison.Ordinal` for ids and keys | `ToLower()` comparisons; culture-sensitive comparison of an id |
| Case change | `ToUpperInvariant()` for keys, `ToUpper(culture)` only for display (Turkish dotless i) | `ToUpper()` on user text |
| Parsing user input | `TryParse(text, culture, out var value)` with the input culture | `Parse` in the invariant culture on typed text |
| Wire formats (JSON, query strings, files) | Invariant culture, ISO 8601 | The UI culture |

A `NumberBox` already formats by the user's culture; set its `NumberFormatter` only for a fixed digit count.

## Right-to-left

- `FlowDirection` follows the language: WinUI mirrors from the top-level `Window.Content`'s `FlowDirection` set from the language's direction; a localized string `Root.FlowDirection` set to `LeftToRight` / `RightToLeft` in each `.resw` is the pattern in Microsoft's guidance, but this skill did not re-verify it: confirm in the running app with a pseudo-RTL language.
- **Directional icons mirror** (back, forward, send); icons that show a real-world object (a clock, a phone, a play triangle for media) do not: `FontIcon.MirroredWhenRightToLeft`.
- Use `Start` / `End`-style alignment (`HorizontalAlignment="Stretch"`, `Padding` pairs set from a style), not `Left` / `Right` literals, wherever the layout carries meaning.
- Numbers, code and Latin brand names inside RTL text stay left-to-right; mixed-direction strings are tested.
- `[WPF]` `FlowDirection` on the root; `[WinForms]` `RightToLeft` + `RightToLeftLayout`.

## Layout for longer text

Translations run 30–40% longer (German, Finnish) and some scripts need more height (Thai, Hindi). No fixed `Width` or `Height` on a control that holds text, `TextWrapping="Wrap"` or `TextTrimming` with a tooltip, and a `Grid` with `Auto` / `*` columns. A pseudo-localized `.resw` (`[Ŝŏmé ŧéxŧ !!!]`, 40% longer) is the cheap test: add it as a language during development and remove it before release.

## Telemetry

A missing-resource lookup logs once at `Warning` with the key and language (never the value of user data) and falls back to the default language. A metric `app.language` is a gauge by language code only if the project already counts it.

## Rules

1. No user-visible literal in XAML or C#: the exceptions are test ids, log message templates and protocol tokens.
2. `x:Uid` for markup, one injected `ResourceLoader` for code.
3. Placeholders, never concatenation; plurals by category, never `== 1`.
4. Culture-aware formatting for display, invariant for the wire and for keys.
5. Layout survives +40% text and RTL; no fixed text widths.
6. The manifest's display name and package strings are localized through `ms-resource:`.
7. Each declared language has a complete `.resw`; the default language is the fallback.

## Generation steps

1. Detect the lane (above) and the existing `.resw` / `.resx` layout.
2. Create `Strings/en-US/Resources.resw`; set the default language in the manifest.
3. Move every literal: `x:Uid` in XAML, `GetString` in code behind an injected loader.
4. Add the plural and formatting helpers only for the values the app shows.
5. Add each language folder, declare it in the manifest, and run once with a pseudo-localized and an RTL language.
6. Add the key-coverage test.

## Validation

- Every `x:Uid` resolves: run the app in `en-US` and a second language and read the page; a missing `x:Uid` property throws.
- `rg -n "Text=\"[A-Za-z]" -g '*.xaml'` finds no literal text (excluding bindings).
- Each language's `.resw` has the same identifier set as the default.
- The app runs in a pseudo-localized language with no clipped text and in an RTL language with a mirrored layout.

## Common gotchas

- **`x:Uid` on the wrong control type** — `Greeting.Text` on a `Button` is a run-time error; name identifiers per element kind.
- **`ResourceLoader(string)` called with a map name** — it takes a `.pri` path.
- **Unpackaged app shows English only** — no `resources.pri` beside the `.exe`.
- **Resources shifted after translation** — renamed identifiers are retranslated.
- **A manifest still on `x-generate`** — the declared language set is not what you shipped.
- **`ToString()` in a log or key** — culture-dependent output as an id breaks on a comma-decimal machine.
- **A bound `Text` formatted in the view model with `CurrentCulture` read once at startup** — an in-app language change does not apply until it is re-read.
