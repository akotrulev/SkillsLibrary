# Control components — Playwright for Java 1.63

The catalogue of control components: one class per design-system widget, in the `components.controls`
package, extracted the first time a page uses the widget. The rules are `qa-java-page-objects.md`; this file
holds the shape of each control and the Playwright API it drives. Every API below is in 1.63. Five controls
ship as compiling assets (`assets/DatePicker.java`, `Dropdown.java`, `Combobox.java`, `DataGrid.java`,
`GridRow.java`), and `assets/OrdersPage.java` with `OrdersTest.java` shows a page composing two of them.

## 1. The shape every control shares

- **The constructor takes the root `Locator`** the page hands it (`page.getByTestId("Orders.PlacedOn")`) and
  builds every child from it with `root.getBy*` or `root.locator(child)`. The page decides where the
  control is mounted; the control never knows.
- **Public methods are user intent with domain-typed arguments**: a `LocalDate`, an option's visible text, a
  row key, a column name. No URL, no assertion, no `boolean` parameter that picks a behaviour.
- **Locators an action uses are private.** A control may return a `Locator` only as an assertion target,
  `describe(...)`d, for the test to pass to `assertThat` (`dropdown.selectedOption()`, `row.cell("Status")`).
- **The markup decides the class.** A native `<select>` is `Dropdown`; a custom listbox is `Combobox`. When
  a library ships two markups of one widget, write two classes, never one with a branch on which it found.
- **A portaled popup** (a listbox or calendar rendered at the end of `<body>`) is the one child a control
  finds outside its root: from `root.page()`, by role, and only while it is the single open one. Where the
  trigger carries `aria-controls`, prefer scoping to that id.
- **Controls compose.** `DatePicker` holds two `Dropdown`s for its month and year selects; a page holds the
  controls as `private final` fields and exposes them as intent (`orders.placedOn().select(date)`).

The roles and accessible names in the assets ("Choose date", "Month", "Year") are a typical design system's.
Read the real ones from the app's markup or the aria snapshot (`locators.md` §11) and change the constants
of the class, never the page.

## 2. The catalogue

| Control | Root | Intent methods | Playwright API |
|---|---|---|---|
| `DatePicker` | the picker wrapper (field, toggle button, calendar dialog) | `select(LocalDate)`; `field()` as the assertion target | `toggle.click()`, the month and year `Dropdown`s, `getByRole(GRIDCELL, setName(day).setExact(true)).click()` |
| `Dropdown` | the native `<select>` itself | `choose(String optionText)`; `selectedOption()` | `selectOption(new SelectOption().setLabel(text))`; `locator("option:checked")` |
| `Combobox` | the combobox wrapper (input plus listbox) | `choose(String optionText)`; `input()` | `getByRole(COMBOBOX).fill(text)`, then `getByRole(LISTBOX).getByRole(OPTION, setName(text).setExact(true)).click()` |
| `DataGrid` | the `role="grid"` element | `row(String key)` returns a `GridRow`; `columnValues(String column)` for an every-row check; `rows()` for `hasCount` | `getByRole(ROW).filter(setHas(gridcell named key))`, `getByRole(COLUMNHEADER).allInnerTexts()` after `waitFor()`; `rows.all()` mapped to each row's cell once `aria-busy` clears |
| `GridRow` | one row, found by its key cell | `cell(String column)` as the assertion target; `perform(String action)` | `getByRole(GRIDCELL).nth(columnIndex)`, `getByRole(BUTTON, setName(action).setExact(true)).click()` |
| `Pagination` | the `navigation` landmark around the pager | `goTo(int pageNumber)`, `next()`, `previous()`; `current()` | `getByRole(BUTTON, setName(String.valueOf(n)).setExact(true)).click()`; `locator("[aria-current='page']")` |
| `Modal` | the `dialog` returned by the action that opens it | `confirm()`, `dismiss()`, `fill(...)` for its form; `title()` | `page.getByRole(DIALOG, setName(title))`; buttons by role and name inside it |
| `Toast` | the toast region (`status` or `alert`) | `close()`; `message()` | `getByRole(STATUS)`; `page.addLocatorHandler` when a toast may cover a later action (`locators.md` §8) |
| `Tabs` | the `tablist` | `open(String tabName)`; `selectedTab()`, `panel()` | `getByRole(TAB, setName(name).setExact(true)).click()`; `getByRole(TAB, setSelected(true))`, `page.getByRole(TABPANEL)` |
| `FileUpload` | the drop zone or the file `input` | `upload(Path file)`, `remove(String fileName)`; `files()` | `locator("input[type=file]").setInputFiles(path)`; a hidden input needs no click. A drop zone without one: `page.waitForFileChooser(() -> trigger.click()).setFiles(path)` |

## 3. The grid and its rows

- A row is picked **by its content**, never by index: `DataGrid.row("ORD-1042")` filters rows to the one
  holding a grid cell whose accessible name is exactly the key. A new id per test (seeded in setup) keeps the
  key unique.
- The inner locator of `setHas` is evaluated inside each row, so it is built from `page`, not from the grid's
  root: `rows.filter(new Locator.FilterOptions().setHas(page.getByRole(AriaRole.GRIDCELL, ...)))`. A locator
  chained from the root would look for the grid inside the row and match nothing.
- `GridRow.cell(column)` maps the column name to its index through the header texts, then takes
  `cells.nth(index)` inside the row. That is the one positional pick the rules allow: the column position is
  what the header defines. An unknown column throws with the names it found.
- The assets model an ARIA `grid` whose cells are all `gridcell`. A grid that renders its key column as
  `rowheader`, or a plain `<table>` (`cell`), is a second class with its own roles, not a parameter.
- **Every row of a result** is checked through `DataGrid.columnValues(column)`, which returns one column's
  texts once the grid's `aria-busy` marker clears. The test asserts the list is not empty, then asserts on the
  whole list with AssertJ `allSatisfy` / `allMatch` (§5): an "every row" check over an empty result proves
  nothing, and a loop in the test body is forbidden. Never `rows.first()` standing for the result set.
- **Test ids that embed the row index** (`cell-value-status-3`): the grid resolves the index from the row's
  content inside the control (the key row's position among `rows`), and builds the id there. The test only
  ever passes the key.
- Virtualized grids render only the visible rows. Scroll with the grid's own search or filter (seeded data
  plus a filter keeps the row on screen), never with a loop that scrolls until the row appears.

## 4. Choosing a date without a branch

A calendar that opens on the current month tempts a loop that clicks "next" until the right month shows,
which is a branch on state. The asset avoids it: the calendar's month and year selects jump straight to the
month, then the day cell is clicked by its exact name. When the widget offers a typeable field instead, the
intent method fills it in the widget's format and presses `Enter`; that is a different markup and a
different class (`DateField`), not a flag on `DatePicker`.

## 5. Using controls in a test

```java
ordersPage.placedOn().select(PLACED_ON);

assertThat(ordersPage.order(orderNumber).cell("Status")).hasText("Pending");
```

Every row of a filtered result, in one assertion over the column (`OrdersTest.Should_ListOnlyOrdersPlacedThatDay_When_FilteredByPlacedDate`):

```java
ordersPage.placedOn().select(PLACED_ON);

assertThat(ordersPage.orderColumn("Placed on"))
        .as("Placed on of every listed order")
        .isNotEmpty()
        .allSatisfy(placedOn -> assertThat(placedOn).isEqualTo(PLACED_ON.toString()));
```

The data comes from setup (`OrdersTest.seedOrderAndOpenOrders`, deleted in `@AfterMethod(alwaysRun = true)`),
and the body is the action and its outcome. The test never calls `click` or `fill` on a locator a control
returns.
