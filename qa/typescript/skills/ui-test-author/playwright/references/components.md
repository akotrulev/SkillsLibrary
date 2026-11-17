# Control components — Playwright 1.64 (TypeScript)

The catalogue of control components for the TypeScript UI lane: one class per design-system widget, extracted
at first use. `page-object-design` decides which kind a piece is; this file says what each control takes, what
it offers and which Playwright API it drives. The standards are the rule file `page-objects.md`.

## 1. The shape every control shares

- **One root in the constructor.** The page builds it from its own locator ladder
  (`page.getByTestId('Orders.PlacedFrom')`) and passes it in; the control builds every child from it, so it
  works wherever it is mounted and knows nothing about the page.
- **Intent methods with domain-typed arguments**: a `Date`, an option's visible text, a row key, a column
  name. Never a selector, an index or a boolean that switches behaviour.
- **Action locators are `private readonly`.** A locator is public only as a `readonly`, described assertion
  target (`DatePicker.selected`, `GridRow.cell(column)`), which the test hands to a web-first assertion and
  never acts on.
- **No URL, no assertion, no `BasePage`.** A control waits through Playwright's auto-waiting and web-first
  assertions in the spec, never through a branch on visibility.
- **Two markups are two classes.** A native `<select>` is `Dropdown`; a custom listbox is `Combobox`. One class
  that inspects the markup and branches is a defect.
- **A popup rendered in a portal** (outside the root, under `<body>`) is a second constructor argument, built
  by the page from its own root: `new Combobox(page.getByTestId('Orders.Customer'), page.getByRole('listbox', { name: 'Customer' }))`.
  The control still never reaches for `page` itself.

The assets ship `DatePicker`, `Dropdown`, `Combobox`, `DataGrid` and `GridRow`; `OrdersPage.ts` composes
three of them and `orders.spec.ts` drives them through fixtures. The rest are written from the table at
first use, in the same shape.

## 2. The catalogue

| Control | Root | Intent methods | Assertion targets | Playwright API |
|---|---|---|---|---|
| `DatePicker` | the field wrapper | `select(date: Date)` | `selected` (the text box) | `getByRole('button', { name: 'Choose date' }).click()`, `selectOption` on the month and year selects, `getByRole('gridcell', { name, exact: true }).click()` |
| `Dropdown` | the native `<select>` | `select(option: string)` | none; the page's result region carries the outcome | `selectOption({ label })` |
| `Combobox` | the combobox wrapper | `choose(option)`, `search(query, option)` | none | `getByRole('combobox').click()` / `.fill(query)`, `getByRole('option', { name, exact: true }).click()` |
| `DataGrid` | the grid (`role="grid"` or the table) | `row(key): GridRow`, `sortBy(column)` | `column(name)`, every cell of one column; single rows answer through `GridRow` | `getByTestId('DataGrid.Row').filter({ has: page.getByText(key, { exact: true }) })`, `getByRole('columnheader', { name, exact: true }).click()` |
| `GridRow` | one row, found by its content | `select()`, `runAction(action)` | `cell(column)` | `getByTestId('DataGrid.Cell.<Column>')`, `getByRole('checkbox').check()`, `getByRole('button', { name, exact: true }).click()` |
| `Pagination` | the pagination `nav` | `next()`, `previous()`, `goTo(page: number)` | `current` (the item with `aria-current="page"`) | `getByRole('button', { name: 'Next page' })`, `getByRole('button', { name: String(page), exact: true })` |
| `Modal` | the dialog (`getByRole('dialog', { name })`) | `confirm()`, `cancel()`, `close()` | `heading`, `message` | `getByRole('button', { name })`; returned by the page action that opens it |
| `Toast` | the live region (`getByRole('status')` or `alert`) | `dismiss()` | `message` | `getByRole('button', { name: 'Dismiss' })`; an unsolicited toast is an `addLocatorHandler` in a fixture, never an `if` |
| `Tabs` | the `tablist` | `open(tab: string)` | `panel` (`getByRole('tabpanel')`) | `getByRole('tab', { name, exact: true }).click()` |
| `FileUpload` | the drop zone or field wrapper | `upload(path: string)`, `remove(fileName)` | `files` (the uploaded list) | `locator('input[type=file]').setInputFiles(path)`; a picker opened by a button: `page.waitForEvent('filechooser')` started before the click |

## 3. Rows are picked by content

`DataGrid.row(key)` filters the shared static row id by a cell whose text is exactly the key: an order
number, an email, a SKU. Never `nth()`, never an id with a database key in it (`locators.md` §1, §3). The row
locator is lazy, so a `GridRow` held across a sort or a refresh still finds the same record. A column is
addressed by name through the grid's static cell ids; a grid that renders no cell ids gets a
`missing-testids.md` row and, meanwhile, the column header's accessible name. Where the app's cell ids embed the
row index (`cell-value-status-3`), `GridRow` and `column` match them by pattern
(`getByTestId(/^cell-value-status-\d+$/)`) inside the row found by content: the index stays inside the control,
and no method takes one.

## 4. Asserting on every row of a result

A filter or search test checks every row, and the linear test body has no loop. `DataGrid.column(name)` returns
a described locator for all of that column's cells, and the test hands it to web-first assertions:

```ts
test.beforeEach(async ({ ordersPage }) => {
  await ordersPage.goto();
});

test('Should_ListOnlyShippedOrders_When_StatusFilterIsShipped', async ({ ordersPage }) => {
  await ordersPage.status.select('Shipped');
  await ordersPage.applyFilters();

  const statuses = ordersPage.orders.column('Status');
  await expect(statuses, 'Status column of the filtered grid').not.toHaveCount(0);
  await expect(statuses.filter({ hasNotText: 'Shipped' }), 'Status cells other than Shipped').toHaveCount(0);
});
```

- **Not empty first.** "Every cell says Shipped" over an empty grid passes and proves nothing; the first
  assertion is the guard, and a missing one is a blocker (`test-data.md`). A filter test over curated
  environment data names that data in the test; one over its own data seeds it in a fixture.
- **One assertion on the whole column.** "Every cell has X" is the column filtered to the cells without X,
  expected to have none: `filter({ hasNotText })` for "contains", `hasNotText: /^Shipped$/` for an exact match.
  A known, ordered result is `expect(column).toHaveText(['A-100', 'A-101'])`, which also checks the count.
- **Why a locator and not `allTextContents()`.** Both assertions retry until the grid settles, so a grid still
  showing the pre-filter rows does not race the check. `allTextContents()` reads once, with no wait, and
  needs a separate wait to be safe; keep it for a value the test computes with, never for the assertion.
- **Never `[0]` or `first()` standing for the result set.** One row is the subject only when the test is about
  that row, and then it is `row(key)`.

## 5. Exposing a control on a page

The page holds a control as a `readonly` field named for its meaning on that page, so a spec reads as the
user's action: `ordersPage.placedFrom.select(date)`, `ordersPage.orders.row(number).cell('Status')`. A step the
page alone completes (applying the filters) is the page's own intent method, not a raw locator. When that
action starts the app's own busy state (a progress bar, a snackbar), it waits for it to clear before returning,
through a named wait on the shell component (`await this.shell.waitUntilIdle()`, which runs
`progressBar.waitFor({ state: 'hidden' })`); the test never calls the wait itself.

A page that repeats with a different label (one property page per property) is one class constructed with that
label, `new PropertyPage(page, 'Suicide Genes')`, building its locators from it: the label is data, not a
behaviour flag.
