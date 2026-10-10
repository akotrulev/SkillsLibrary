# Locators — Playwright for Java 1.63

The one owner of locator mechanics for the Java UI lane. `page-object-design`, `page-objects-from-url` and
`ui-test-author/review` link here instead of restating it. Every API below is in 1.63, the version
`SKILL.md` pins; the version in brackets is where it first shipped. A 1.64 API is named only on a
"from 1.64" line, because it does not compile on 1.63 — and playwright.dev's Java pages already list some
of them, so check the installed version, not the docs page.

## 1. The ladder

Pick the first rung the element supports. Never skip a rung because the lower one is shorter to type.

| # | Locator | Use when |
|---|---|---|
| 1 | `page.getByTestId("Login.Submit")` | The element carries the project's test-id attribute. This is the contract with the app team |
| 2 | `page.getByRole(AriaRole.BUTTON, new Page.GetByRoleOptions().setName("Sign in"))` | No test id. The accessibility tree names the element |
| 3 | `page.getByLabel("Email")` | A form control with a label and no test id |
| 4 | `page.getByPlaceholder("you@example.com")` | A control with no label |
| 5 | `page.getByText("Order placed", new Page.GetByTextOptions().setExact(true))` | Static visible text, mainly for assertions |
| 6 | `page.getByAltText(...)` / `page.getByTitle(...)` | Images and elements named only by `alt` / `title` |
| 7 | `page.locator("css=…")` | Nothing above works. Shortest stable CSS, never a positional XPath chain |

**Test ids are PascalCase dot-separated and static** — `Login.Submit`, `OrderRow`, `OrderRow.Title` — which
is what `fe-react` and `fe-blazor` generate. A repeated row shares one static id (`OrderRow`); the row is
picked by its content (§3), never by an id that embeds a database key, an index or a state value.

**A fallback carries no marker in the code.** When an element has no test id, use the next rung and add a
row to `missing-testids.md` (page, element, suggested id, fallback locator in use). That report is the
contract; the extraction workflow is `qa/java/skills/page-objects-from-url`. No `TODO` comment, no inline
comment on the locator.

## 2. `getBy*` details

- `GetByRoleOptions`: `setName`, `setExact`, `setDescription` [1.60] (the accessible description, which
  separates two buttons that share a name), `setChecked`, `setPressed`, `setExpanded`, `setSelected`,
  `setDisabled`, `setLevel`, `setIncludeHidden`.
- Name and text matching are case-insensitive substrings by default. Call `setExact(true)` when the expected
  text is a prefix of a neighbour (`Submit` vs `Submit order`), or a later label change becomes a
  strict-mode violation.
- A `Pattern` name is for dynamic text you cannot pin (`Pattern.compile("^Order #\\d+$")`), never for
  accepting two outcomes.
- Every `getBy*` also exists on `Locator` and `FrameLocator`, which is how a component chains from its root.

## 3. Narrowing: `filter`, `and`, `or`

| API | Returns | Use for |
|---|---|---|
| `rows.filter(new Locator.FilterOptions().setHasText("Pending"))` | rows whose text contains the string | picking a container by its visible content |
| `.setHasNotText("Archived")` | rows without it | excluding |
| `.setHas(page.getByTestId("OrderRow.Overdue"))` | rows that contain the inner match | picking a container by a child element |
| `.setHasNot(…)` | rows that do not | excluding by child |
| `.setVisible(true)` [1.51] | visible rows only | responsive layouts that render hidden twins |
| `a.and(b)` [1.34] | elements matching both | one element by role **and** test id or title |
| `a.or(b)` [1.33] | elements matching either | an action on genuinely alternative markup |

`setHas` / `setHasNot` take a locator relative to the container, with no `FrameLocator` inside it.

**Never assert on an `or()` locator.** `assertThat(a.or(b)).isVisible()` passes on either state, which is an
`OR` assertion. An overlay that may or may not appear is handled with `addLocatorHandler` (§8).

```java
Locator row = page.getByTestId("OrderRow").filter(new Locator.FilterOptions().setHasText(orderNumber));
row.getByRole(AriaRole.BUTTON, new Locator.GetByRoleOptions().setName("Cancel")).click();
```

## 4. Chaining from a component root

A component object takes its root `Locator` and builds every child from it, so the same component works
wherever it is mounted. `assets/LoginPage.java` does this with `SignInForm`.

```java
public final class OrderRow {
    private final Locator title;
    private final Locator cancel;

    public OrderRow(Locator root) {
        this.title = root.getByTestId("OrderRow.Title");
        this.cancel = root.getByRole(AriaRole.BUTTON, new Locator.GetByRoleOptions().setName("Cancel"));
    }
}
```

## 5. One locator inside another: `parent.locator(child)`

`parent.locator(child)` returns the child's matches inside each element the parent matches. The child may
be a selector string or a `Locator` built elsewhere, which is how a page object scopes a locator it already
holds. Both must belong to the same frame, and the result is strict for actions like any locator.

```java
Locator form = page.getByTestId("Login.Form").describe("Sign-in form");
Locator error = form.locator(page.getByRole(AriaRole.ALERT)).describe("Sign-in error");
```

That is the `assets/LoginPage.java` case: the app shell renders its own alert region, so
`page.getByRole(AriaRole.ALERT)` matches two elements. Scoping it to the form resolves the strictness and
says what it means.

**From 1.64: `child.within(parent)`** — the same result written child-first. Java gets it when Maven
publishes 1.64; do not write it on 1.63.

| API | Returns | Use when |
|---|---|---|
| `parent.locator(child)` | **child** elements inside each parent; also takes `LocatorOptions` (`setHas`, `setHasText`, …) | scoping one locator to another |
| `parent.getByRole(...)` | the same, built from the root | chaining inside a component |
| `parent.getByRole(...).nth(2)` | `nth` over the **flattened** result | "the Nth match overall" |
| `parent.filter(new FilterOptions().setHas(child))` | **parent** elements that contain a child | picking the row or card by its content |
| `a.and(b)` | elements matching both | two conditions on one element |
| `locator.visible()` / `filter(setVisible(true))` | the same elements, visible only | replacing `:visible` |

**Do not rely on per-parent `nth`.** Whether `parent.locator(childWithNth)` resolves `nth` inside each
parent before 1.64 is unverified, so "the third cell of every row" is not written on 1.63. Pick the row
first (§3), then the cell inside it.

## 6. `visible()` [1.63] instead of `:visible`

`locator.visible()` matches only visible elements and replaces the `:visible` pseudo-class (still accepted,
no longer taught). In Java it is a method; in .NET and Python it is a property. Below 1.63 use
`filter(new Locator.FilterOptions().setVisible(true))` [1.51].

## 7. Frames

- `page.frameLocator("#checkout")` returns a `FrameLocator`; chain `getBy*` from it.
- `page.frameLocator()` with **no selector** [1.63] searches every frame in the subtree and fails if the
  matches span several frames. Use it when the iframe has no stable selector.
- `locator.contentFrame()` turns a located `<iframe>` into a `FrameLocator`, so the iframe itself is found
  on the ladder: `page.getByTestId("Checkout.PaymentFrame").contentFrame().getByLabel("Card number")`.
- `frameLocator.owner()` goes the other way, to the `<iframe>` element.
- From 1.64, elements inside a hidden iframe count as hidden for actions, `isVisible()` and
  `assertThat(locator).isVisible()`; expect that change when the project moves to 1.64.

## 8. Strictness, positional picks and overlays

- **Locators are strict for actions.** A click on a locator that matches two elements fails. Fix it by
  scoping (§4, §5) or filtering (§3), never by appending `.first()`.
- **`nth()` / `first()` / `last()` only with a stated reason**, and the reason is the field or method name:
  `newestNotification = notifications.first()` where newest-first order is the behaviour under test. An
  unnamed `.first()` that silences a strictness error is a defect.
- **`page.addLocatorHandler(locator, handler, options)`** runs the handler whenever the locator becomes
  visible before an action or an assertion — the cookie banner, the "new version" toast. Register it in the
  test class's `@BeforeMethod` so every test gets it; `setTimes(n)` limits it, `page.removeLocatorHandler`
  removes it. It replaces "close the overlay if it is there" branches, which would be conditional logic.

```java
page.addLocatorHandler(page.getByTestId("Consent.Banner"),
        banner -> banner.getByRole(AriaRole.BUTTON, new Locator.GetByRoleOptions().setName("Accept")).click());
```

## 9. Naming locators: `describe()` [1.53]

`locator.describe("Sign-in error")` labels the locator in the trace, the report and the failure message;
`locator.description()` [1.57] reads it back. Java's `assertThat` has no message parameter, so this is how a
failure names its subject (`assertions.md` §6). Describe every locator a test asserts on.

## 10. The test-id attribute

`getByTestId` reads `data-testid` by default. `BaseTest` sets it explicitly with
`playwright.selectors().setTestIdAttribute("data-testid")` in `@BeforeClass`, because the setting belongs to
one `Playwright` instance and each class creates its own. A project whose app ships `data-test` changes that
one constant and keeps `getByTestId` everywhere. TypeScript sets `testIdAttribute` in the config; .NET sets
`TestIdAttribute` in the `.runsettings`.

## 11. Agent-facing locators

These help an agent exploring a live page; committed tests use the ladder.

- `page.ariaSnapshot(new Page.AriaSnapshotOptions().setMode(AriaSnapshotMode.AI))` [1.59] returns the aria
  tree with `[ref=eN]` markers; `setDepth` limits it.
- `locator.normalize()` [1.59] returns the locator rewritten to best-practice form.
- `page.pickLocator()` / `page.cancelPickLocator()` [1.59] let a person click an element in a headed browser
  and return its locator.
- From 1.64: `page.getByRef("e2")` resolves a ref from an AI-mode snapshot. Not on 1.63.
