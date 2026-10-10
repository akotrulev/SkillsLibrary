# Locators — Microsoft.Playwright 1.63

The one owner of locator mechanics for the .NET UI lane. `page-object-design`, `page-objects-from-url` and
`ui-test-author/review` link here instead of restating it. Every API below is in 1.63, the version
`SKILL.md` pins; the version in brackets is where it first shipped. A 1.64 API is named only on a
"from 1.64" line, because it does not compile on 1.63 — and playwright.dev's .NET pages already list some
of them, so check the installed package, not the docs page.

## 1. The ladder

Pick the first rung the element supports. Never skip a rung because the lower one is shorter to type.

| # | Locator | Use when |
|---|---|---|
| 1 | `page.GetByTestId("Login.Submit")` | The element carries the project's test-id attribute. This is the contract with the app team |
| 2 | `page.GetByRole(AriaRole.Button, new() { Name = "Sign in" })` | No test id. The accessibility tree names the element |
| 3 | `page.GetByLabel("Email")` | A form control with a label and no test id |
| 4 | `page.GetByPlaceholder("you@example.com")` | A control with no label |
| 5 | `page.GetByText("Order placed", new() { Exact = true })` | Static visible text, mainly for assertions |
| 6 | `page.GetByAltText(...)` / `page.GetByTitle(...)` | Images and elements named only by `alt` / `title` |
| 7 | `page.Locator("css=…")` | Nothing above works. Shortest stable CSS, never a positional XPath chain |

**Test ids are PascalCase dot-separated and static** — `Login.Submit`, `OrderRow`, `OrderRow.Title` — which
is what `fe-react` and `fe-blazor` generate. A repeated row shares one static id (`OrderRow`); the row is
picked by its content (§3), never by an id that embeds a database key, an index or a state value.

**A fallback carries no marker in the code.** When an element has no test id, use the next rung and add a
row to `missing-testids.md` (page, element, suggested id, fallback locator in use). That report is the
contract; the extraction workflow is `qa/dotnet/skills/page-objects-from-url`. No `TODO` comment, no inline
comment on the locator.

## 2. `GetBy*` details

- `PageGetByRoleOptions` / `LocatorGetByRoleOptions`: `Name` (or `NameRegex`), `Exact`, `Description`
  [1.60] (the accessible description, which separates two buttons that share a name), `Checked`,
  `Pressed`, `Expanded`, `Selected`, `Disabled`, `Level`, `IncludeHidden`.
- Name and text matching are case-insensitive substrings by default. Set `Exact = true` when the expected
  text is a prefix of a neighbour (`Submit` vs `Submit order`), or a later label change becomes a
  strict-mode violation.
- A `Regex` name is for dynamic text you cannot pin (`new Regex(@"^Order #\d+$")`), never for accepting
  two outcomes.
- Every `GetBy*` also exists on `ILocator` and `IFrameLocator`, which is how a component chains from its
  root.

## 3. Narrowing: `Filter`, `And`, `Or`

| API | Returns | Use for |
|---|---|---|
| `rows.Filter(new() { HasText = "Pending" })` | rows whose text contains the string | picking a container by its visible content |
| `new() { HasNotText = "Archived" }` | rows without it | excluding |
| `new() { Has = page.GetByTestId("OrderRow.Overdue") }` | rows that contain the inner match | picking a container by a child element |
| `new() { HasNot = … }` | rows that do not | excluding by child |
| `new() { Visible = true }` [1.51] | visible rows only | responsive layouts that render hidden twins |
| `a.And(b)` [1.34] | elements matching both | one element by role **and** test id or title |
| `a.Or(b)` [1.33] | elements matching either | an action on genuinely alternative markup |

`Has` / `HasNot` take a locator relative to the container, with no `FrameLocator` inside it.

**Never assert on an `Or()` locator.** `Expect(a.Or(b)).ToBeVisibleAsync()` passes on either state, which
is an `OR` assertion. An overlay that may or may not appear is handled with `AddLocatorHandlerAsync` (§8).

```csharp
var row = page.GetByTestId("OrderRow").Filter(new() { HasText = orderNumber });
await row.GetByRole(AriaRole.Button, new() { Name = "Cancel" }).ClickAsync();
```

## 4. Chaining from a component root

A component object takes its root `ILocator` and builds every child from it, so the same component works
wherever it is mounted. `assets/LoginPage.cs` does this with `SignInForm`.

```csharp
public sealed class OrderRow
{
    public OrderRow(ILocator root)
    {
        Title = root.GetByTestId("OrderRow.Title");
        Cancel = root.GetByRole(AriaRole.Button, new() { Name = "Cancel" });
    }

    public ILocator Title { get; }

    public ILocator Cancel { get; }
}
```

Locators are built once, in the constructor, as `private readonly ILocator` fields or get-only properties
for the ones tests assert on. An expression-bodied property (`ILocator Error => _page.GetByRole(...)`) is
not slower and does not "re-query the DOM" — a locator is lazy and queries nothing until an action or an
assertion — but it rebuilds the locator on every access and spreads the definitions across the class.

## 5. One locator inside another: `parent.Locator(child)`

`parent.Locator(child)` returns the child's matches inside each element the parent matches. The child may
be a selector string or an `ILocator` built elsewhere, which is how a page object scopes a locator it
already holds. Both must belong to the same frame, and the result is strict for actions like any locator.

```csharp
var form = page.GetByTestId("Login.Form").Describe("Sign-in form");
var error = form.Locator(page.GetByRole(AriaRole.Alert)).Describe("Sign-in error");
```

That is the `assets/LoginPage.cs` case: the app shell renders its own alert region, so
`page.GetByRole(AriaRole.Alert)` matches two elements. Scoping it to the form resolves the strictness and
says what it means.

**From 1.64: `child.Within(parent)`** — the same result written child-first. .NET gets it when NuGet
publishes 1.64; do not write it on 1.63.

| API | Returns | Use when |
|---|---|---|
| `parent.Locator(child)` | **child** elements inside each parent; also takes `LocatorLocatorOptions` (`Has`, `HasText`, …) | scoping one locator to another |
| `parent.GetByRole(...)` | the same, built from the root | chaining inside a component |
| `parent.GetByRole(...).Nth(2)` | `Nth` over the **flattened** result | "the Nth match overall" |
| `parent.Filter(new() { Has = child })` | **parent** elements that contain a child | picking the row or card by its content |
| `a.And(b)` | elements matching both | two conditions on one element |
| `locator.Visible` / `Filter(new() { Visible = true })` | the same elements, visible only | replacing `:visible` |

**Do not rely on per-parent `Nth`.** Whether `parent.Locator(childWithNth)` resolves `Nth` inside each
parent before 1.64 is unverified, so "the third cell of every row" is not written on 1.63. Pick the row
first (§3), then the cell inside it.

## 6. `Visible` [1.63] instead of `:visible`

`locator.Visible` matches only visible elements and replaces the `:visible` pseudo-class (still accepted,
no longer taught). **In .NET it is a property**, not a method: `page.GetByTestId("Toast").Visible`. Below
1.63 use `Filter(new() { Visible = true })` [1.51].

## 7. Frames

- `page.FrameLocator("#checkout")` returns an `IFrameLocator`; chain `GetBy*` from it.
- `page.FrameLocator()` with **no selector** [1.63] searches every frame in the subtree and fails if the
  matches span several frames. Use it when the iframe has no stable selector.
- `locator.ContentFrame` (a property) turns a located `<iframe>` into an `IFrameLocator`, so the iframe
  itself is found on the ladder:
  `page.GetByTestId("Checkout.PaymentFrame").ContentFrame.GetByLabel("Card number")`.
- `frameLocator.Owner` goes the other way, to the `<iframe>` element.
- From 1.64, elements inside a hidden iframe count as hidden for actions, `IsVisibleAsync()` and
  `ToBeVisibleAsync()`; expect that change when the project moves to 1.64.

## 8. Strictness, positional picks and overlays

- **Locators are strict for actions.** A click on a locator that matches two elements fails. Fix it by
  scoping (§4, §5) or filtering (§3), never by appending `.First`.
- **`Nth()` / `First` / `Last` only with a stated reason**, and the reason is the field or property
  name: `NewestNotification = notifications.First` where newest-first order is the behaviour under test.
  An unnamed `.First` that silences a strictness error is a defect.
- **`page.AddLocatorHandlerAsync(locator, handler, options)`** runs the handler whenever the locator
  becomes visible before an action or an assertion — the cookie banner, the "new version" toast. Register
  it in the test class's `[SetUp]` so every test gets it; `Times = n` limits it,
  `RemoveLocatorHandlerAsync` removes it. It replaces "close the overlay if it is there" branches, which
  would be conditional logic.

```csharp
await Page.AddLocatorHandlerAsync(Page.GetByTestId("Consent.Banner"),
    banner => banner.GetByRole(AriaRole.Button, new() { Name = "Accept" }).ClickAsync());
```

## 9. Naming locators: `Describe()` [1.53]

`locator.Describe("Sign-in error")` labels the locator in the trace and the failure message;
`locator.Description` [1.57] reads it back. Describe every locator a test asserts on. .NET also takes a
message on the assertion itself, `Expect(locator, "message")` [1.60] (`assertions.md` §6).

## 10. The test-id attribute

`GetByTestId` reads `data-testid` by default. `assets/ui.runsettings` sets it explicitly with
`<TestIdAttribute>data-testid</TestIdAttribute>`; `PlaywrightTest` applies it before every test, so it is
the one place to change it. A project whose app ships `data-test` changes that element and keeps
`GetByTestId` everywhere. A call to `Playwright.Selectors.SetTestIdAttribute(...)` in a test is overwritten
by the next test's setup. TypeScript sets `testIdAttribute` in the config; Java calls
`playwright.selectors().setTestIdAttribute(...)`.

## 11. Agent-facing locators

These help an agent exploring a live page; committed tests use the ladder.

- `await page.AriaSnapshotAsync(new() { Mode = AriaSnapshotMode.Ai })` [1.59] returns the aria tree with
  `[ref=eN]` markers; `Depth` limits it, `Boxes` [1.60] adds bounding boxes.
- `await locator.NormalizeAsync()` [1.59] returns the locator rewritten to best-practice form.
- `await page.PickLocatorAsync()` / `CancelPickLocatorAsync()` [1.59] let a person click an element in a
  headed browser and return its locator.
- From 1.64: `page.GetByRef("e2")` resolves a ref from an AI-mode snapshot. Not on 1.63.
