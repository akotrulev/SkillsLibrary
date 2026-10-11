---
name: test-ids
description: Use when adding, auditing or fixing `testID` props so Appium and Maestro can target an Expo SDK 57 app — including consuming a `missing-testids.md` from QA's screen explorer. Covers how testID surfaces on iOS and Android, static row ids, PascalCase naming, never accessibilityLabel as an id. Triggers "add testIDs", "E2E can't find this element", "content-desc vs testID". Do NOT use for writing the device tests (`qa-mobile-typescript`).
---

# React Native — Testability (`testID` writer)

Adds and audits `testID` on React Native components so device suites locate elements by one stable id. It is the dev-side half of a loop QA owns: `qa-mobile-typescript`'s `mobile-screen-explorer` reads the live page source and files a `missing-testids.md`; this skill consumes that report. Web analog: [`fe-react:test-ids`](../../../../frontend/react/skills/test-ids/SKILL.md) — the naming, static-row and "one attribute only" rules carry over unchanged; `data-testid`, per-library slot props and DOM verification do not.

## Version lane

| Concern | Detail |
|---|---|
| Prop | `testID` on core components (`View`, `Text`, `TextInput`, `Pressable`, `Image`, `ScrollView`, `FlatList`) and on anything that forwards to them; same on SDK 54–58 and RN 0.81–0.88 |
| Cost | A `testID` (or `nativeID`) **disables the layout-only view removal optimisation** for that view — tag elements a test uses, not every wrapper |
| `[SDK58]` | No change known; re-run the mapping check below when the RN minor changes |
| Libraries | A library component forwards `testID` to its root only if it spreads props; confirm in the page source (below) |

## How `testID` reaches the device — verified 2026-10-10

The reactnative.dev `View` page says only that `testID` is "used to locate this view in end-to-end tests"; it **does not state the platform mapping**. The mapping below is read from the React Native source (`main`), and the selector semantics from Maestro's docs and source.

| Platform | What `testID` becomes | Source |
|---|---|---|
| **iOS** (Fabric) | `accessibilityIdentifier` — `RCTViewComponentView.mm` sets `accessibilityView.accessibilityIdentifier = identifier` from `newViewProps.testId` | https://github.com/facebook/react-native/blob/main/packages/react-native/React/Fabric/Mounting/ComponentViews/View/RCTViewComponentView.mm |
| **Android** | The Android **`resource-id`** (`AccessibilityNodeInfo.viewIdResourceName`): `BaseViewManager.setTestId` stores it in `R.id.react_test_id` (and, temporarily, `view.setTag(testId)`); `ReactAccessibilityDelegate.onInitializeAccessibilityNodeInfo` sets `info.viewIdResourceName = testId` | https://github.com/facebook/react-native/blob/main/packages/react-native/ReactAndroid/src/main/java/com/facebook/react/uimanager/BaseViewManager.java · …/ReactAccessibilityDelegate.kt |
| API docs | `testID` — "used to locate this view in end-to-end tests" | https://reactnative.dev/docs/view |

**Consequences**

- **Android `content-desc` is NOT the `testID`.** `content-desc` carries `accessibilityLabel` / `aria-label`. The claim in `qa/*/skills/mobile-screen-explorer/SKILL.md` line 10 ("`content-desc` on Android … mapping to a React Native `testID`") is wrong; W1 corrects it. This skill only records the verified answer.
- The Android `resource-id` is the **bare `testID`** (`Login.Email`), **not** `com.example.app:id/Login.Email` — RN writes the string as given. A locator written as `<package>:id/<name>` finds nothing.
- On **iOS**, `testID` is the `name` attribute in the XCUITest source and the Appium accessibility id (`~`). On **Android**, `~` (accessibility id) resolves `content-desc` and therefore does **not** reach a `testID`; use the `id` strategy or a UiSelector `resourceId`. One id, two locator strategies by platform.
- Because an unset `accessibilityLabel` falls back to a different `name` on iOS, a missing `testID` can look present in the iOS source (`name` = the label). Check the **attribute**, not just that something has a name.

### Which identifier Maestro's `id:` matches — verified 2026-10-10

| Platform | `id:` matches | Source |
|---|---|---|
| iOS | `accessibilityIdentifier` — "Maestro translates this to the `id` selector… the gold standard for reliable tests"; `accessibilityLabel` → the `text` selector | https://docs.maestro.dev/platform-support/ios-uikit |
| Android | the node's **`resource-id`** attribute — `Filters.idMatches` reads `attributes["resource-id"]` | https://github.com/mobile-dev-inc/maestro (`maestro-client/src/main/java/maestro/Filters.kt`) |
| React Native | "use the `testID` property, which Maestro maps to a unique `id`" | https://docs.maestro.dev/platform-support/react-native |

So **one `testID` serves Appium and Maestro**: Maestro `id: "Login.Email"`; Appium iOS `~Login.Email`; Appium Android `id=Login.Email` (UiAutomator2) or `android=new UiSelector().resourceId("Login.Email")`. Notes:

- Maestro's `id` (and `text`) are **regular expressions**, case-insensitive: the `.` in `Login.Email` also matches any character. It still selects the intended element; escape it (`Login\.Email`) when two ids differ only at a dot.
- **Built but unverified:** whether UiAutomator2's `id=` strategy prepends the app package to a bare name — QA confirms with `appium_get_page_source` on the real build and falls back to the UiSelector form, which is exact.
- The page source of the **same build** is the final authority; the explorer records both `resource-id` and `name`.

## When to use

- Add `testID` to one or more `.tsx` screens or components
- Audit a screen for missing, duplicated, label-derived or unstable ids
- A `missing-testids.md` has been handed over by QA
- An E2E flow cannot find an element on one platform but can on the other

## When NOT to use

- Writing page objects or device tests → `qa-mobile-typescript` (peer)
- Labels and roles for screen readers → [`accessibility`](../accessibility/SKILL.md)
- Choosing or building components → [`ui-components`](../ui-components/SKILL.md)

## Output format

One prop only: `testID="…"`. **Never `accessibilityLabel` (or `aria-label`, `accessibilityHint`) as an identifier, and never a label copied into `testID`.** A label is for a person, is translated ([`languages`](../languages/SKILL.md)), changes with copy edits, and is read aloud; an id is for a machine, is never translated and never spoken. Do not mirror one into the other. Always PascalCase, dot-separated segments.

## The rules

### 1. Where the prop goes

| Element | How |
|---|---|
| Core component (`View`, `Pressable`, `TextInput`, `Text`, `Image`) | Inline: `<Pressable testID="Login.SubmitButton">` |
| `FlatList` / `FlashList` / `ScrollView` | `testID` on the list — it lands on the scroll container; this is the list container id |
| Third-party / Expo component | Inline; if it does not forward, wrap the touch target in a `View` with the id or use the library's own prop — then **verify in the page source** that it landed on the interactive element |
| Custom component you own | Takes a `testId` **prefix** prop and composes its own suffix (rule 4); the leaf forwards `testID` to a core component |
| `Animated.*` | Inline — it forwards to the native view ([`animation`](../animation/SKILL.md)) |

Prefer inline. Do **not** add `AppButton` / `AppInput` wrappers just to carry ids. Do not rely on `nativeID`: it is not what Appium or Maestro read.

### 2. Naming: `Screen.ElementType[.Qualifier]`

PascalCase, dot-separated; no spaces, kebab-case, numeric ids, GUIDs, array indexes or state values.

- **Screen / component** — derived from the Expo Router file path: `app/(app)/orders/index.tsx` → `Orders`; `app/(app)/orders/[orderId].tsx` → `Orders.Detail` (drop params, route groups and layout segments).
- **ElementType** — the role: `SubmitButton`, `EmailField`, `List`, `Row`, `Tab`, `Banner`.
- **Qualifier** — a semantic name (enum member, field name, action) in scope, never an id.

```
Login.EmailField          Login.SubmitButton        Orders.List
Orders.Row                Orders.Row.Title          Orders.Row.Status
Tabs.Orders               Notifications.Error.Close
```

### 3. Constants for repeated ids

A static id used more than once is a module-level `const` (PascalCase name); three or more sites sharing a prefix extract `TestIdPrefix`. When composing from an optional prefix, fall back to `''` so the prop is always a string:

```tsx
const TestIdPrefix = 'Login';

<TextInput testID={`${TestIdPrefix}.EmailField`} />
<Pressable testID={`${TestIdPrefix}.SubmitButton`} />
```

### 4. Components compose their suffix

```tsx
type Props = { testId?: string; status: OrderStatus };

export function StatusBadge({ testId, status }: Props) {
  return <Text testID={`${testId ?? ''}.StatusBadge`}>{statusLabel(status)}</Text>;
}
```

The caller passes the **prefix only**: `<StatusBadge testId="Orders.Detail.Header" />` → `Orders.Detail.Header.StatusBadge`. A pass-through wrapper forwards `testId` untouched; only the terminal component appends.

### 5. Which elements get one

Tag: every interactive element (`Pressable`, `TextInput`, `Switch`, tab triggers, menu items, sheet actions), every list / grid container, and the read anchors a test asserts — totals, status text, banners, empty states. Tag the **states of every data region and the error banner**: `<Region>.Loading`, `<Region>.Error`, `<Region>.Retry`, `<Region>.Empty`, `<Region>.Stale`, `Notifications.Banner`, `Notifications.Banner.Close` — so a test can tell a **failed** region from an **empty** one and see the offline state ([`error-handling`](../error-handling/SKILL.md)). Tag the permission primer and denied screens ([`device-features`](../device-features/SKILL.md)).

Skip layout `View`s, decorative icons and wrappers — each tag disables the layout-only optimisation.

### 6. List rows: one static locator, addressed by index

A row component **must not** take a per-row id prop. The parent locator is a hard-coded constant; children namespace under it; tests address a row **by index** over the shared locator — never by embedding the row's id.

```tsx
const RowTestId = 'Orders.Row';

export function OrderRow({ order }: { order: Order }) {
  return (
    <Pressable testID={RowTestId} onPress={() => openOrder(order.id)}>
      <Text testID={`${RowTestId}.Title`}>{order.reference}</Text>
      <Text testID={`${RowTestId}.Status`}>{statusLabel(order.status)}</Text>
    </Pressable>
  );
}
```

The list's `keyExtractor` still returns the **stable domain id** — key and test id are different concerns: the key is unique per row, the test id is static so the set is selectable. Identical ids across rows are intended; Appium `findElements` / Maestro `index:` select one. If the same role appears twice in a row, sub-namespace: `Orders.Row.Total` vs `Orders.Row.Refund.Total`.

### 7. Derive from data in scope, not lookup tables

```tsx
{tabs.map((tab) => (
  <Tabs.Trigger key={tab.name} name={tab.name} testID={`Tabs.${tab.name}`} />
))}
```

No hand-maintained `Record<Enum, string>` of ids — it drifts when a value is renamed.

### 8. Accessibility grouping hides children on iOS

An element with `accessible` (the default for `Pressable`, `Text`, `TouchableOpacity`) is a single accessibility element; on iOS the **children inside it are not exposed individually** to XCUITest, so `Orders.Row.Title` inside an `accessible` row is unreachable from Appium while the row id is. Either assert on the row, or set `accessible={false}` on the grouping container where children must be addressed — and weigh that against screen-reader behaviour with [`accessibility`](../accessibility/SKILL.md). Confirm on the iOS page source. (From experience with XCUITest; not re-verified against Apple docs this session.)

## Consuming a `missing-testids.md`

QA's `mobile-screen-explorer` writes, per screen:

```markdown
## LoginScreen (extracted 2026-06-05, Pixel 8 / Android 15)

| Element | Type | Visible text / label | Suggested testID | Fallback locator in use |
|---------|------|----------------------|------------------|-------------------------|
| Email field   | EditText | (hint "Email")  | `login-email`  | `$('id=com.app:id/email')` |
| Password reveal | Button | (eye icon, no text) | `login-password-reveal` | `$('//*[@class="…ImageButton"][2]')` ⚠ brittle |
```

1. Treat each row as a rule 5 candidate; derive its id by rules 2–7. **The "Suggested testID" column is a hint, not the id** — this library's convention is PascalCase dot-separated (`Login.EmailField`), not the kebab-case the report suggests.
2. Rows with ⚠ (XPath-only) are first.
3. A row rule 5 calls decorative: do not tag; list it back so QA re-anchors.
4. Reply with the table `Element → assigned testID → file:line`, plus counts and **collisions** (the same id on two distinct, non-row elements — these block completion). QA regenerates the page objects from it.
5. A row whose "Fallback locator in use" is a package-prefixed `id=com.app:id/…` is a **native `resource-id`**, not a `testID` — the explorer is reading a different attribute; assign the `testID` anyway and tell QA the new `resource-id` is the bare id.

## Procedure

1. Confirm scope (a file, a feature folder, or a `missing-testids.md`); do not rewrite the whole tree unasked.
2. For each target file, derive the screen root; walk the JSX; apply rules 1–7; skip decoratives and list them.
3. For a component library control, confirm the id lands on the interactive element (page source, or the library's docs) — otherwise tag the wrapping touch target.
4. Report per file: ids added, decoratives skipped, collisions, and any `accessible` grouping that hides children (rule 8).
5. Outside a `Gate: none` plan task, typecheck with the project's script; with a dev build, read the page source of one screen on each platform.

## Anti-patterns

| Anti-pattern | Fix |
|---|---|
| `testID={`Row.${order.id}`}` | Static `Orders.Row` (rule 6) |
| `accessibilityLabel="Login.EmailField"` or label text used as the id | `testID`; the label stays human copy |
| Locating on Android by `~` / `content-desc` to reach a `testID` | `id=` / `resourceId`; `~` is the label |
| `testID` on every layout `View` | Remove — it defeats view flattening |
| `Record<Enum, string>` id map | Interpolate from the value (rule 7) |
| kebab-case or snake_case ids | PascalCase segments |
| Translated string, index or GUID in an id | Enum / field name |
| `nativeID` as a test hook | `testID` |
| Same id on two non-row elements | Sub-namespace one |
| A wrapper component added only to carry ids | Inline `testID` |

## Handoffs

- Page objects, Appium and Maestro flows, device runs → `qa-mobile-typescript` (peer; plan 003)
- Labels, roles, focus order, screen-reader text → [`accessibility`](../accessibility/SKILL.md)
- Components that emit ids by default → [`ui-components`](../ui-components/SKILL.md)
- Region states and banner ids → [`error-handling`](../error-handling/SKILL.md)
- Hygiene as part of a broader review → [`code-review`](../code-review/SKILL.md)
