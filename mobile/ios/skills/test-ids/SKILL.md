---
name: mobile-ios-test-ids
description: Use when adding, auditing or fixing `accessibilityIdentifier` so Appium (XCUITest driver) and Maestro can target an iOS app — including consuming a `missing-testids.md` from QA's screen explorer. Covers SwiftUI and UIKit, static row ids, PascalCase naming, grouping that hides children, never accessibilityLabel as an id. Triggers "add test ids", "E2E can't find this element". Do NOT use for writing the device tests (`qa-mobile-ios`).
---

# iOS — Testability (`accessibilityIdentifier` writer)

Adds and audits `accessibilityIdentifier` on SwiftUI and UIKit views so device suites locate elements by one stable id. It is the dev-side half of a loop QA owns: `qa-mobile-ios`'s explorer reads the live page source and files a `missing-testids.md`; this skill consumes that report. Sibling and contract source: [`mobile-react-native-test-ids`](../../../react-native/skills/test-ids/SKILL.md) (the verified cross-platform mapping) — the naming, static-row and "one attribute only" rules carry over unchanged. Web analog: [`fe-react-test-ids`](../../../../frontend/react/skills/test-ids/SKILL.md).

## Version lane

| Concern | Detail |
|---|---|
| SwiftUI | `.accessibilityIdentifier(_:)` — iOS 14+, same on iOS 16 / 17 / 18 / 26 |
| UIKit | `UIAccessibilityIdentification.accessibilityIdentifier` on any `UIView`, `UIBarItem`, `UIAccessibilityElement` |
| Cost | None at runtime beyond a string; unlike React Native there is no view-flattening trade-off, but an id on every decorative view is still noise in the page source |
| `[iOS27 SDK]` | No change known; re-run the page-source check below when the Xcode major changes |

## The contract — one id, three consumers (R3-verified)

| Consumer | Reads | Locator for `Login.EmailField` |
|---|---|---|
| **XCUITest** (the driver under Appium) | `accessibilityIdentifier` is the element's `identifier`; Appium's page source shows it as the **`name`** attribute | Appium accessibility id `~Login.EmailField`; or `-ios predicate string: name == "Login.EmailField"` |
| **Maestro** `id:` | `accessibilityIdentifier` — Maestro docs: "translates this to the `id` selector… the gold standard for reliable tests"; `accessibilityLabel` is matched by `text:` | `id: "Login.EmailField"` |
| **Android peer** | The same string on the other platform: Compose `Modifier.testTag` with `testTagsAsResourceId = true` → `resource-id`; Views `android:id`; React Native `testID` lands on both | Appium `id=Login.EmailField` / Maestro `id:` |

So **one string serves Appium and Maestro on every stack**. Notes carried from R3 (`mobile-react-native-test-ids`, D20):

- **`accessibilityLabel` / `accessibilityHint` are for people** — translated, spoken by VoiceOver, edited with copy. They are **never** an identifier and an identifier is **never** copied into a label. On iOS the Appium `label` attribute is the VoiceOver label; `name` is the identifier **or, when no identifier is set, the label** — so a missing id can look present in the page source. Check the **attribute**, not just that something has a name.
- Maestro's `id` (and `text`) are **case-insensitive regular expressions**: the `.` in `Login.EmailField` also matches any character. Escape it (`Login\.EmailField`) when two ids differ only at a dot.
- The page source of the **same build** is the final authority; the explorer records both `name` and `label`.

## When to use

- Add identifiers to one or more SwiftUI views / UIKit controllers
- Audit a screen for missing, duplicated, label-derived or unstable ids
- A `missing-testids.md` has been handed over by QA
- An E2E flow finds an element on Android (or in React Native) but not on iOS

## When NOT to use

- Writing page objects or device tests → `qa-mobile-ios` (peer; plan 003)
- Labels, traits, VoiceOver order → `mobile-ios-accessibility`
- Choosing or building components → [`ui-components`](../ui-components/SKILL.md)
- Another stack → `mobile-react-native-test-ids`, `mobile-android-test-ids`

## Output format

One modifier only: `.accessibilityIdentifier("…")`. **Never `accessibilityLabel` (or a hint) as the identifier, and never label text copied into the id.** Always PascalCase, dot-separated segments.

## The rules

### 1. Where the modifier goes

| Element | How |
|---|---|
| `Button`, `Toggle`, `TextField`, `SecureField`, `Picker`, `Slider`, `Stepper`, `Link` | On the control: `Button("Sign in") { … }.accessibilityIdentifier("Login.SubmitButton")` |
| `List` / `LazyVStack` in a `ScrollView` | On the **container**: `List { … }.accessibilityIdentifier("Orders.List")` |
| `NavigationLink(value:)` row | On the row **content** (rule 6), not on the `NavigationLink` wrapper alone |
| `TabView` item | On the tab's label content (`Label` in `.tabItem` / the `Tab` initializer); confirm in the page source that it reached the tab-bar button |
| `ForEach` content | Inside the row view (rule 6) |
| Custom view you own | Takes a `testIdPrefix: String` and composes its own suffix (rule 4); the leaf applies `.accessibilityIdentifier` to a core control |
| `[UIKit]` | `button.accessibilityIdentifier = "Login.SubmitButton"` in the view's setup; `UIBarButtonItem.accessibilityIdentifier`; a cell sets it on `contentView` or a subview |
| System UI (alerts, `confirmationDialog`, share sheet, permission dialogs) | **Not taggable** — QA locates them by their system label (and the OS language); keep the app's own pre-prompt controls tagged |

Prefer inline. Do **not** add `AppButton` / `AppField` wrappers just to carry ids (CLAUDE.md § Simplicity).

### 2. Naming: `Screen.ElementType[.Qualifier]`

PascalCase, dot-separated; no spaces, kebab-case, numeric ids, GUIDs, array indexes or state values.

- **Screen / component** — derived from the SwiftUI view or controller name: `OrdersView.swift` → `Orders`; `OrderDetailView.swift` → `Orders.Detail` (drop the `View` / `Screen` / `ViewController` suffix and any parameters).
- **ElementType** — the role: `SubmitButton`, `EmailField`, `List`, `Row`, `Tab`, `Banner`.
- **Qualifier** — a semantic name (enum case, field name, action) in scope, never an id.

```
Login.EmailField          Login.SubmitButton        Orders.List
Orders.Row                Orders.Row.Title          Orders.Row.Status
Tabs.Orders               Notifications.Error.Close
```

### 3. Constants for repeated ids

A static id used more than once is a `static let` in a nested `enum` per screen (not a runtime lookup); three or more sites sharing a prefix extract the prefix:

```swift
private enum TestID {
    static let prefix = "Login"
    static let email = "\(prefix).EmailField"
    static let submit = "\(prefix).SubmitButton"
}

TextField("Email", text: $email).accessibilityIdentifier(TestID.email)
Button("Sign in", action: signIn).accessibilityIdentifier(TestID.submit)
```

A single-use id stays an inline literal.

### 4. Components compose their suffix

```swift
struct StatusBadge: View {
    let status: OrderStatus
    var testIdPrefix = ""

    var body: some View {
        Text(status.title)
            .accessibilityIdentifier("\(testIdPrefix).StatusBadge")
    }
}
```

The caller passes the **prefix only**: `StatusBadge(status: order.status, testIdPrefix: "Orders.Detail.Header")` → `Orders.Detail.Header.StatusBadge`. A pass-through wrapper forwards `testIdPrefix` untouched; only the terminal view appends.

### 5. Which elements get one

Tag: every interactive element (`Button`, `Toggle`, `TextField`, `Picker`, tab and menu items, sheet actions), every list / grid container, and the read anchors a test asserts — totals, status text, banners, empty states. Tag the **states of every data region and the error banner** — `<Region>.Loading`, `<Region>.Error`, `<Region>.Retry`, `<Region>.Empty`, `<Region>.Stale`, `Notifications.Banner`, `Notifications.Banner.Close` — so a test can tell a **failed** region from an **empty** one and see the offline state ([`error-handling`](../error-handling/SKILL.md)). Tag the permission pre-prompt and denied screens ([`device-features`](../device-features/SKILL.md)).

Skip layout stacks, spacers, decorative images (`Image(decorative:)`) and wrappers.

### 6. List rows: one static locator, addressed by index

A row view **must not** take a per-row id for its identifier. The parent locator is a hard-coded constant; children namespace under it; tests address a row **by index** over the shared locator — never by embedding the row's id.

```swift
struct OrderRow: View {
    let order: Order
    private static let id = "Orders.Row"

    var body: some View {
        VStack(alignment: .leading) {
            Text(order.reference).accessibilityIdentifier("\(Self.id).Title")
            Text(order.status.title).accessibilityIdentifier("\(Self.id).Status")
        }
    }
}

List(orders) { order in
    NavigationLink(value: Route.order(order.id)) { OrderRow(order: order) }
}
.accessibilityIdentifier("Orders.List")
```

`ForEach` / `List` identity still uses the **stable domain id** (`Identifiable`) — identity and test id are different concerns: identity is unique per row, the test id is static so the set is selectable. Identical ids across rows are intended; Appium `findElements` and Maestro `index:` select one. A role that appears twice in a row sub-namespaces: `Orders.Row.Total` vs `Orders.Row.Refund.Total`.

### 7. Derive from data in scope, not lookup tables

```swift
ForEach(Tab.allCases) { tab in
    Label(tab.title, systemImage: tab.symbol)
        .accessibilityIdentifier("Tabs.\(tab.rawValue.capitalized)")
}
```

No hand-maintained `[Enum: String]` dictionary of ids — it drifts when a case is renamed.

### 8. Grouping and containers change what is reachable

- **`.accessibilityElement(children: .combine)`** (and a `Button` / `NavigationLink` row, which SwiftUI treats as one element) **merges its children into one accessibility element on iOS** — the children's identifiers are not exposed to XCUITest, so `Orders.Row.Title` inside a combined row is unreachable while the row's own id is. Either assert on the row, or use `.accessibilityElement(children: .contain)` where the children must be addressed — and weigh that against VoiceOver's reading order ([`accessibility`](../accessibility/SKILL.md)).
- **An identifier on a container can be applied to elements inside it that have none of their own** (varies by SwiftUI version and container type) — tag the leaves explicitly and **confirm in the page source** that a container id did not replace a child's.
- `.accessibilityElement(children: .ignore)` plus your own label makes one element with the identifier you gave — the right form for a custom control drawn from many views.
- A `ScrollView` or `List` id lands on the scroll container, which is what a test needs to scroll and to count rows.
- (From XCUITest experience; not re-verified against Apple documentation this session — check the page source of a real build.)

## Consuming a `missing-testids.md`

QA's explorer writes, per screen, a table of `Element | Type | Visible text / label | Suggested id | Fallback locator in use`.

1. Treat each row as a rule 5 candidate; derive its id by rules 2–7. **The "Suggested" column is a hint, not the id** — this library's convention is PascalCase dot-separated (`Login.EmailField`), not the kebab-case the report may suggest.
2. Rows with a brittle fallback (an index XPath, a class chain) first.
3. A row rule 5 calls decorative: do not tag; list it back so QA re-anchors.
4. Reply with `Element → assigned id → file:line`, plus counts and **collisions** (the same id on two distinct, non-row elements — these block completion). QA regenerates the page objects from it.
5. A fallback of the form `~<label>` or `name == "<visible text>"` is a **VoiceOver label**, not an identifier; assign the identifier anyway and tell QA the label is no longer a locator.

## Procedure

1. Confirm scope (a file, a feature folder, or a `missing-testids.md`); do not rewrite the whole tree unasked.
2. For each target file, derive the screen name; walk the view body; apply rules 1–7; skip decoratives and list them.
3. For a grouped or combined element, decide the reachable level (rule 8) and say which.
4. Report per file: ids added, decoratives skipped, collisions, and any grouping that hides children.
5. Outside a `Gate: none` plan task, build the target; with a simulator build, read one screen's page source (`appium_get_page_source`) and confirm `name` matches each assigned id.

## Anti-patterns

| Anti-pattern | Fix |
|---|---|
| `.accessibilityIdentifier("Row.\(order.id)")` | Static `Orders.Row` (rule 6) |
| `.accessibilityLabel("Login.EmailField")`, or label text used as the id | `.accessibilityIdentifier`; the label stays human copy |
| Locating by visible text (`name == "Sign in"`) or a translated label | The identifier; text breaks in every other locale |
| An id on every layout stack | Remove — page-source noise |
| `[Enum: String]` id map | Interpolate from the value (rule 7) |
| kebab-case or snake_case ids | PascalCase segments |
| Translated string, index or GUID in an id | Enum / field name |
| Same id on two non-row elements | Sub-namespace one |
| A wrapper view added only to carry ids | Inline `.accessibilityIdentifier` |
| Assuming a container's id reaches the children | Tag leaves; verify in the page source |

## Handoffs

- Page objects, Appium and Maestro flows, device runs → `qa-mobile-ios` (peer; plan 003)
- Labels, traits, order, Dynamic Type → `mobile-ios-accessibility`
- Components that emit ids by default → [`ui-components`](../ui-components/SKILL.md)
- Region states and banner ids → [`error-handling`](../error-handling/SKILL.md)
- Hygiene as part of a broader review → `mobile-ios-code-review`
