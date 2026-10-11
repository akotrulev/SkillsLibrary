---
name: test-ids
description: Use when adding, auditing or fixing test ids so Appium and Maestro can target a Compose or Views app — Modifier.testTag with testTagsAsResourceId at the root, android:id in Views, static row ids, PascalCase naming, never contentDescription as an id. Triggers "add test tags", "E2E can't find this element", "content-desc vs testTag", a `missing-testids.md`. Do NOT use for writing device tests (`qa-mobile-*`).
---

# Android — Testability (`testTag` writer)

Adds and audits test ids on Compose and Views so device suites locate elements by one stable id. It is the dev-side half of a loop QA owns: `qa-mobile-*`'s `mobile-screen-explorer` reads the live page source and files a `missing-testids.md`; this skill consumes that report. The RN twin is [`mobile-react-native:test-ids`](../../../react-native/skills/test-ids/SKILL.md) (it carries the verified Appium / Maestro selector semantics) — the naming, static-row and "one attribute only" rules carry over unchanged.

## Version lane

| Concern | Compose (primary) | `[Views]` |
|---|---|---|
| Id | `Modifier.testTag("Login.EmailField")` | `android:id="@+id/login_email_field"` |
| Exposed to UiAutomator / Appium / Maestro as | `resource-id` — **only** when `testTagsAsResourceId = true` is set on an ancestor | `resource-id` = `<package>:id/login_email_field` |
| Opt-in | The semantics property may need `@OptIn(ExperimentalComposeUiApi::class)`; the compiler says so for the BOM in use | None |
| Compose UI tests | `onNodeWithTag` works **without** the root flag — the flag is for external tools only | `withId` / `R.id` |
| `[API37]` | No change known; re-run the page-source check when the Compose BOM changes | — |

Facts verified 2026-10-10: the pattern `Modifier.semantics { testTagsAsResourceId = true }` on a root container with `Modifier.testTag` below it, and the Appium UiAutomator2 behaviour below (appium discussion threads — **community sources, not Appium's reference**). The exact resource-id string Compose produces for a tag was not on developer.android.com's testing pages; the RN skill's rule — the bare tag, no package prefix — is the one to confirm in the page source of the real build.

## The one switch — once, at the root

```kotlin
@OptIn(ExperimentalComposeUiApi::class)
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            AppTheme {
                Box(Modifier.semantics { testTagsAsResourceId = true }) {
                    AppNavigation()
                }
            }
        }
    }
}
```

- **Set it once, on the single root of `setContent`**, never per screen, per component or per `testTag` call — it applies to the node and **all its descendants** — one set of ids then serves Appium and Maestro.
- **A `Dialog`, `ModalBottomSheet`, `DropdownMenu` and `Popup` create their own window and composition**, so the ancestor flag may not reach their content. **Not verified for the BOM in use** — set the same one-line `Modifier.semantics { testTagsAsResourceId = true }` on the root content of each window composable your app owns and confirm in the page source; a shared `TestIdRoot { }` wrapper is not needed for one call site.
- It is safe to leave on in all build types: it exposes only the static ids you wrote, in the accessibility tree. If a security review forbids it in release, gate it on a build-config flag (`BuildConfig.EXPOSE_TEST_IDS`) at the one place it is set — never on each tag.
- A multi-activity app sets it once per activity's `setContent` (single activity is the house rule — [`project-setup`](../project-setup/SKILL.md)).

## How a tag reaches the device

| Layer | What it sees |
|---|---|
| `Modifier.testTag("Login.EmailField")` + the root flag | The accessibility node's `resource-id` is the tag. Appium UiAutomator2 page source `resource-id="Login.EmailField"`; Maestro `id: "Login.EmailField"` (R3 verified `id:` matches `resource-id` on Android) |
| `contentDescription` | `content-desc` — **a label for people**, not the tag. Appium's `~` (accessibility id) reads `content-desc` on Android and therefore does **not** reach a `testTag` |

**Locator guidance for QA (record, do not decide for them):**

- Appium Android: **`new UiSelector().resourceId("Login.EmailField")` is exact** and works with a bare tag. The `id` strategy may **prepend the app package** to a bare id (Appium's id-locator autocompletion), so `id=Login.EmailField` can miss; the setting `disableIdLocatorAutocompletion` switches that off. **Built but unverified here** — the page source of the real build is the authority, and QA's explorer records both attributes.
- Appium iOS uses `~Login.EmailField` for the same id; Maestro uses `id:` on both — one id, one name, three tools.
- Maestro's `id` is a case-insensitive regex, so the `.` also matches any character — still the intended element; escape it only when two ids differ at a dot.

## Naming: `Screen.ElementType[.Qualifier]`

PascalCase, dot-separated; no spaces, snake_case, kebab-case, numeric ids, GUIDs, list indexes or state values.

- **Screen** — the destination key / route name: `OrdersList` → `Orders`, `OrderDetail` → `Orders.Detail` (drop params).
- **ElementType** — the role: `SubmitButton`, `EmailField`, `List`, `Row`, `Tab`, `Banner`.
- **Qualifier** — a semantic name (enum member, field name, action) in scope, never an id.

```
Login.EmailField       Login.SubmitButton      Orders.List
Orders.Row             Orders.Row.Title        Orders.Row.Status
Tabs.Orders            Notifications.Banner.Close
```

## Rules

### 1. Where the modifier goes

| Element | How |
|---|---|
| Compose component you own | A `modifier: Modifier = Modifier` first optional parameter ([`ui-components`](../ui-components/SKILL.md)); the **caller** passes `Modifier.testTag("Login.SubmitButton")`; the leaf applies `modifier` to its root |
| Material 3 control | `Modifier.testTag` on the control itself (`Button`, `OutlinedTextField`, `Switch`, `Tab`); confirm it lands on the **interactive** node (rule 7) |
| `LazyColumn` / `LazyVerticalGrid` / `Pager` | `Modifier.testTag("Orders.List")` on the lazy container — the list container id |
| Component with an internal suffix | Takes a `testTag: String` prefix parameter and composes its own suffix (rule 4) |
| `[Views]` | `android:id`; snake_case is the only legal resource name — derive it mechanically: `Login.EmailField` → `login_email_field` |

Prefer inline. Do not add `AppButton` / `AppTextField` wrappers just to carry tags, and do not rely on `Modifier.layoutId` or `contentDescription` as a hook.

### 2. Constants for repeated ids

A static id used more than once is a `const val` in an `object` named for the screen or feature; three or more sharing a prefix extract the prefix:

```kotlin
private object LoginTags {
    const val Prefix = "Login"
    const val EmailField = "$Prefix.EmailField"
    const val SubmitButton = "$Prefix.SubmitButton"
}
```

### 3. Components compose their suffix

```kotlin
@Composable
fun StatusBadge(status: OrderStatus, modifier: Modifier = Modifier, testTag: String = "") {
    Text(
        text = status.label(),
        modifier = modifier.testTag("$testTag.StatusBadge"),
    )
}
```

The caller passes the **prefix only** — `StatusBadge(status, testTag = "Orders.Detail.Header")` → `Orders.Detail.Header.StatusBadge`. A pass-through forwards the prefix untouched; only the terminal composable appends.

### 4. Which elements get one

Tag every interactive element (buttons, fields, switches, tabs, menu items, sheet actions), every list / grid container, and the read anchors a test asserts — totals, status text, banners, empty states. Tag the **states of every data region and the error banner**: `<Region>.Loading`, `<Region>.Error`, `<Region>.Retry`, `<Region>.Empty`, `<Region>.Stale`, `Notifications.Banner`, `Notifications.Banner.Close` — so a test can tell a **failed** region from an **empty** one and see the offline state ([`error-handling`](../error-handling/SKILL.md)). Tag the permission primer, the denied screen and its **Open Settings** button ([`device-features`](../device-features/SKILL.md)), and the notification list rows ([`notifications-and-links`](../notifications-and-links/SKILL.md)).

Skip layout containers, decorative icons (`contentDescription = null`) and spacers.

### 5. List rows: one static locator, addressed by index

A row composable **must not** take a per-row id for its tag. The parent locator is a constant; children namespace under it; tests address a row **by index** over the shared locator.

```kotlin
private const val RowTag = "Orders.Row"

@Composable
fun OrderRow(order: Order, onOpen: () -> Unit, modifier: Modifier = Modifier) {
    ListItem(
        headlineContent = { Text(order.reference, Modifier.testTag("$RowTag.Title")) },
        supportingContent = { Text(order.status.label(), Modifier.testTag("$RowTag.Status")) },
        modifier = modifier
            .clickable(onClick = onOpen)
            .testTag(RowTag),
    )
}
```

The lazy list's **`key = { it.id }` stays the stable domain id** — a key is unique per row, a test tag is static so the set is selectable. Identical tags across rows are intended; Appium `findElements` and Maestro `index:` pick one. If the same role appears twice in a row, sub-namespace it (`Orders.Row.Total`, `Orders.Row.Refund.Total`).

### 6. Derive from data in scope, not lookup tables

```kotlin
tabs.forEach { tab ->
    NavigationBarItem(modifier = Modifier.testTag("Tabs.${tab.name}"), /* … */)
}
```

No hand-maintained `Map<Enum, String>` of ids — it drifts when a value is renamed. A localized label is never interpolated into an id.

### 7. Merged semantics hide children

`Modifier.clickable`, `toggleable`, `selectable` and Material `ListItem` **merge their descendants** into one accessibility node. UiAutomator reads the **merged** tree, so `Orders.Row.Title` inside a `clickable` row is not a separate node while `Orders.Row` is. Either assert on the row, or pass `Modifier.semantics(mergeDescendants = false)` on a grouping container where children must be addressed — and weigh that against TalkBack, which then reads each child ([`accessibility`](../accessibility/SKILL.md)). Compose's `onNodeWithTag(…, useUnmergedTree = true)` sees them in a dev-side test; the device tools do not. **Confirm in the page source** of one screen.

### 8. Put the tag on the node that behaves

`testTag` goes **on the node that carries the behaviour** — chained with `clickable` / `toggleable` it lands on the one merged node; a `testTag` on a wrapper `Box` around a `Button` tags the wrapper, not the button. A node that uses `clearAndSetSemantics` replaces its semantics wholesale: set the tag inside that block (`testTag = …`) and confirm it in the page source.

## One attribute only

**Never `contentDescription` (or `stateDescription`, `onClickLabel`) as an identifier, and never a label copied into a tag.** A label is for a person, is translated ([`languages`](../languages/SKILL.md)), changes with copy edits and is read aloud; a tag is for a machine, never translated and never spoken. Do not mirror one into the other. The QA explorer's old assumption that Android `content-desc` is the RN `testID` is wrong — W1 corrects it.

## Consuming a `missing-testids.md`

QA's `mobile-screen-explorer` writes, per screen, a table of `| Element | Type | Visible text / label | Suggested testID | Fallback locator in use |`.

1. Treat each row as a rule 4 candidate; derive its id by the naming rule. **The "Suggested testID" column is a hint, not the id** — this library's convention is PascalCase dot-separated, not the kebab-case the report suggests.
2. Rows whose fallback is an XPath (⚠ brittle) are first.
3. A row rule 4 calls decorative: do not tag; list it back so QA re-anchors.
4. Reply with `Element → assigned tag → file:line`, plus counts and **collisions** (the same id on two distinct non-row elements — these block completion). QA regenerates the page objects from it.
5. A fallback of `id=com.app:id/…` is a native `resource-id` (a Views `android:id` or a generated one); assign the tag anyway and tell QA the new `resource-id` is the **bare** tag.

## Procedure

1. Confirm scope (a screen, a feature folder, or a `missing-testids.md`); do not rewrite the tree unasked.
2. Confirm the root flag exists (`rg -n "testTagsAsResourceId" -g '*.kt'`) in every window composable you rely on; add it once if missing.
3. For each file: derive the screen name from its key; walk the composables; apply rules 1–8; list decoratives skipped.
4. For a Material control, confirm the tag lands on the interactive node, otherwise tag the wrapping touch target.
5. Report per file: tags added, decoratives skipped, collisions, merged-semantics cases.
6. Outside a `Gate: none` plan task, read one screen's page source from a dev build (UiAutomator dump / Appium inspector) and confirm `resource-id` carries the bare tag.

## Anti-patterns

| Anti-pattern | Fix |
|---|---|
| `testTagsAsResourceId` set per screen or per element | Once at the root (and each separate window root) |
| `Modifier.testTag("Row.${order.id}")` | Static `Orders.Row` (rule 5) |
| `contentDescription = "Login.EmailField"` or label text as the id | `testTag`; the label stays human copy |
| Locating by `~` / `content-desc` to reach a tag | `UiSelector().resourceId(…)` or Maestro `id:` |
| `testTag` on every layout `Box` | Remove — interactive elements and read anchors only |
| `Map<Enum, String>` id table | Interpolate from the value (rule 6) |
| snake_case or kebab-case tags in Compose | PascalCase dot-separated |
| Translated string, index or GUID in a tag | Enum / field name |
| Same tag on two non-row elements | Sub-namespace one |
| A wrapper composable added only to carry tags | Inline `Modifier.testTag` |
| Tag on a `Box` around a `Button` | Tag the `Button` (rule 8) |

## Handoffs

- Page objects, Appium and Maestro flows, device runs → `qa-mobile-*` (peer; plan 003)
- Labels, roles, merged semantics, TalkBack order → [`accessibility`](../accessibility/SKILL.md)
- Components that take a `modifier` and emit ids → [`ui-components`](../ui-components/SKILL.md)
- Region states and banner ids → [`error-handling`](../error-handling/SKILL.md)
- Test-id hygiene as part of a broader review → [`code-review`](../code-review/SKILL.md)
