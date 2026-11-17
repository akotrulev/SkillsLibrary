# Control components — Microsoft.Playwright 1.63

The catalogue of control components for the .NET UI lane: one class per design-system widget, in
`Components/Controls/`, namespace `<Root>.Components.Controls`. The rules they follow (extracted at first
use, root in the constructor, intent methods with domain-typed arguments, no assertion, no URL, two markups
are two classes) are in the `page-objects.md` rule file; this page is the mechanics. Every API below is in
1.63; on 1.63 a child scoped to a locator held elsewhere is `parent.Locator(child)`, never `Within()`.

## The shape every control shares

- The constructor takes the root `ILocator` the page hands it, usually `page.GetByTestId("Orders.PlacedOn")`,
  and builds every child from it. A popup the widget renders in a portal outside its root (a listbox, a
  calendar) is a second constructor argument, never a `page` field.
- Public methods are one user action each, named for it, with a domain argument: a `DateOnly`, an option's
  visible text, a row key, a column name, a file path. No `bool` that switches behaviour.
- A locator is public only as a described assertion target that no action uses (`Dropdown.SelectedOption`,
  `DataGrid.DataRows`); everything an action touches is a `private readonly ILocator` field.
- The page exposes the control as a get-only property, so a test reads as intent:
  `await _ordersPage.PlacedOn.SelectAsync(placedOn)`. A page method may compose several controls
  (`OrdersPage.FilterAsync`).
- A control never derives from a page base class and never knows which page it is mounted on.

## The catalogue

| Control | Root it takes | Intent methods | Playwright API behind them |
|---|---|---|---|
| [`DatePicker`](../assets/Components/Controls/DatePicker.cs) | the picker's wrapper; the text box inside it | `SelectAsync(DateOnly)`, `ClearAsync()` | `GetByRole(AriaRole.Textbox)`, `FillAsync` with the app's input format, `PressAsync("Enter")`, `ClearAsync` |
| `CalendarDatePicker` | the trigger, plus the calendar popup | `PickAsync(DateOnly)` | `ClickAsync` on the trigger; in the popup `GetByRole(AriaRole.Button, new() { Name = "Next month" })` clicked the computed number of months; the day by `GetByRole(AriaRole.Gridcell, new() { Name = …, Exact = true })` |
| [`Dropdown`](../assets/Components/Controls/Dropdown.cs) | the native `<select>` | `SelectAsync(string option)`; `SelectedOption` (assertion target) | `SelectOptionAsync(new SelectOptionValue { Label = option })`; `Locator("option:checked")` |
| [`Combobox`](../assets/Components/Controls/Combobox.cs) | the `role=combobox` input, plus its listbox | `SelectAsync(string option)`, `ClearAsync()` | `FillAsync` to filter, then `listbox.GetByRole(AriaRole.Option, new() { Name = option, Exact = true }).ClickAsync()` |
| [`DataGrid`](../assets/Components/Controls/DataGrid.cs) | the `role=grid` element | `Row(string key)` → `GridRow`, `SortByAsync(string column)`, `ColumnValuesAsync(string column)` (query); `DataRows` (assertion target) | `GetByRole(AriaRole.Row)` filtered with `Has = root.Page.GetByRole(AriaRole.Gridcell, new() { Name = key, Exact = true })`; `GetByRole(AriaRole.Columnheader)`; the column's cells by `aria-colindex`, read with `AllInnerTextsAsync` |
| [`GridRow`](../assets/Components/Controls/GridRow.cs) | the row locator `DataGrid.Row` built, plus the grid | `CellAsync(string column)` (assertion target), `ChooseActionAsync(string action)`, `SelectAsync()` | the header's `aria-colindex` read with `GetAttributeAsync`, then the cell with the same index; `GetByRole(AriaRole.Button, …)`, `GetByRole(AriaRole.Checkbox).CheckAsync()` |
| `Pagination` | the `navigation` landmark | `GoToPageAsync(int number)`, `NextAsync()`, `PreviousAsync()`; `CurrentPage` (assertion target) | `GetByRole(AriaRole.Button, new() { Name = $"Page {number}" })` or the link equivalent; `CurrentPage` is the element with `aria-current="page"` |
| `Modal` | the `role=dialog` element, by its accessible name | `ConfirmAsync()`, `CancelAsync()`, `CloseAsync()`; `Title` (assertion target) | `page.GetByRole(AriaRole.Dialog, new() { Name = "Delete order" })`, buttons by role inside it; the action that opens it returns it |
| `Toast` | the `role=status` (or `alert`) region | `DismissAsync()`; `Message` (assertion target) | `GetByRole(AriaRole.Status)` with `Visible` (1.63 property); an unpredictable toast over a control goes through `AddLocatorHandlerAsync` (`locators.md` §8), never an `if` |
| `Tabs` | the `role=tablist` element | `OpenAsync(string tab)`; `Selected` (assertion target) | `GetByRole(AriaRole.Tab, new() { Name = tab, Exact = true }).ClickAsync()`; `Selected` filters with `GetByRole(AriaRole.Tab, new() { Selected = true })` |
| `FileUpload` | the drop zone or its `input[type=file]` | `UploadAsync(string path)`, `UploadAsync(FilePayload file)` | `SetInputFilesAsync` on the input, which needs no file chooser; a zone with no input uses `page.RunAndWaitForFileChooserAsync` and `IFileChooser.SetFilesAsync` |

## Rows and grids

- A row is picked by its content, never by index: the key is a value the test seeded and owns (a unique
  title, an order number), and `Exact = true` keeps `Order 12` from matching `Order 123`.
- `Has` takes a locator built from the page (`root.Page.GetByRole(...)`), because it is matched relative to
  each row; one built from the grid root would look for the grid inside the row and match nothing.
- `GridRow.CellAsync` maps a column name to the header's `aria-colindex`; a grid that does not set it, or
  a native `<table>`, is a different markup and gets its own class (`Table` with `Row(key)` and cells by
  header position), never a branch inside `DataGrid`.
- Where the app's test ids embed the row index (`cell-value-status-3`), the grid resolves the index from
  the row's content inside `Row(key)` and builds the id from it; the test never passes an index.
- An app-specific row with domain actions (`OrderRow.CancelAsync()`) is a region component built from the
  same row locator; the generic `GridRow` stays generic.

## Asserting on every row

A test body has no loop, so "every listed order is Pending" is one query and one collection assertion.
`DataGrid.ColumnValuesAsync(column)` returns that column's text for every data row. The test first proves
rows came back, with a web-first assertion that also waits for them, then asserts on the whole collection
with `Is.All`, because `Is.All` over an empty list passes and proves nothing:

```csharp
await _ordersPage.FilterAsync(PlacedOn, "Pending");

await Expect(_ordersPage.Orders.DataRows, "orders listed").Not.ToHaveCountAsync(0);
IReadOnlyList<string> statuses = await _ordersPage.Orders.ColumnValuesAsync("Status");
Assert.That(statuses, Is.All.EqualTo("Pending"), "status of every listed order");
```

`OrdersTests.Should_ListOnlyPendingOrders_When_FilteredByPendingStatus` in the assets is the compiled
example. Never `rows[0]` standing for the result set, and never a `foreach` over rows in a test. Reading
curated reference data instead of a seeded record follows `test-data.md`, with the same non-empty guard.

## Adding a control

1. Check `Components/Controls/` and the design system's component list first: a second class for the same
   widget is a defect.
2. Copy the closest asset, rename it, keep its shape: root in the constructor, private child locators,
   intent methods, at most one described assertion target per state a test reads.
3. A widget whose markup differs (a native `<select>` and a custom listbox both called "dropdown") is a
   second class named for the markup.
4. Build: a control has no `[Test]` of its own; the first test that uses it proves it.
