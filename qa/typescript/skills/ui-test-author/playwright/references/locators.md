# Locators — Playwright 1.64 (TypeScript)

The one owner of locator mechanics for the TypeScript UI lane. `page-object-design`, `page-objects-from-url`
and `ui-test-author/review` link here instead of restating it. Every API below is in the version
`SKILL.md` pins; the version in brackets is where it first shipped, so a down-level project knows what it
lacks.

## 1. The ladder

Pick the first rung the element supports. Never skip a rung because the lower one is shorter to type.

| # | Locator | Use when |
|---|---|---|
| 1 | `getByTestId('Login.Submit')` | The element carries the project's test-id attribute. This is the contract with the app team |
| 2 | `getByRole('button', { name: 'Sign in' })` | No test id. The accessibility tree names the element |
| 3 | `getByLabel('Email')` | A form control with a label and no test id |
| 4 | `getByPlaceholder('you@example.com')` | A control with no label |
| 5 | `getByText('Order placed', { exact: true })` | Static visible text, mainly for assertions |
| 6 | `getByAltText(...)` / `getByTitle(...)` | Images and elements that are only named by `alt` / `title` |
| 7 | `locator('css=…')` | Nothing above works. Shortest stable CSS, never a positional XPath chain |

**Test ids are PascalCase dot-separated and static** — `Login.Submit`, `OrderRow`, `OrderRow.Title` — which
is what `fe-react` and `fe-blazor` generate. A repeated row shares one static id (`OrderRow`); the row is
picked by its content (§3), never by an id that embeds a database key, an index or a state value.

**A fallback carries no marker in the code.** When an element has no test id, use the next rung and add a
row to `missing-testids.md` (page, element, suggested id, fallback locator in use). That report is the
contract; the extraction workflow is `qa/typescript/skills/page-objects-from-url`. No `TODO` comment, no
inline comment on the locator.

## 2. `getBy*` details

- `getByRole(role, { name, exact, description, checked, pressed, expanded, selected, disabled, level, includeHidden })`.
  `description` [1.60] matches the accessible description, which separates two buttons that share a name.
- `name` and text matching are case-insensitive substrings by default. Pass `exact: true` when the expected
  text is a prefix of a neighbour (`Submit` vs `Submit order`), or a later label change becomes a
  strict-mode violation.
- A RegExp `name` is for dynamic text you cannot pin (`/^Order #\d+$/`), never for accepting two outcomes.

## 3. Narrowing: `filter`, `and`, `or`

| API | Returns | Use for |
|---|---|---|
| `rows.filter({ hasText: 'Pending' })` | rows whose text contains the string | picking a container by its visible content |
| `rows.filter({ hasNotText: 'Archived' })` | rows without it | excluding |
| `rows.filter({ has: page.getByTestId('OrderRow.Overdue') })` | rows that contain the inner match | picking a container by a child element |
| `rows.filter({ hasNot: … })` | rows that do not | excluding by child |
| `rows.filter({ visible: true })` [1.51] | visible rows only | responsive layouts that render hidden twins |
| `a.and(b)` [1.34] | elements matching both | one element by role **and** test id or title |
| `a.or(b)` [1.33] | elements matching either | an action on genuinely alternative markup |

`has` / `hasNot` take a locator relative to the container, with no `FrameLocator` inside it.

**Never assert on an `or()` locator.** `expect(a.or(b)).toBeVisible()` passes on either state, which is an
`OR` assertion. An overlay that may or may not appear is handled with `addLocatorHandler` (§8), not `or()`.

```typescript
const row = page.getByTestId('OrderRow').filter({ hasText: orderNumber });
await row.getByRole('button', { name: 'Cancel' }).click();
```

## 4. Chaining from a component root

A component object takes its root `Locator` and builds every child from it, so the same component works
wherever it is mounted. `assets/LoginPage.ts` does this with `SignInForm`.

```typescript
export class OrderRow {
  readonly title: Locator;
  readonly cancel: Locator;

  constructor(readonly root: Locator) {
    this.title = root.getByTestId('OrderRow.Title');
    this.cancel = root.getByRole('button', { name: 'Cancel' });
  }
}
```

## 5. `within()` [1.64] and its neighbours

`child.within(parent)` returns the child's matches inside each element the parent matches. It is exactly
`parent.locator(child)` in reverse order ("this button, within that dialog"), so reach for it when both
locators already exist — typically as page-object fields. It takes **no options**. Both locators must be
in the same frame. It is strict for actions like any locator.

```typescript
const form = page.getByTestId('Login.Form');
const error = page.getByRole('alert').within(form);
```

That is the `assets/LoginPage.ts` case: the app shell renders its own alert region, so
`page.getByRole('alert')` matches two elements. Scoping it to the form resolves the strictness and says
what it means.

| API | Returns | Use when |
|---|---|---|
| `child.within(parent)` [1.64] | **child** elements inside each parent. `nth` / `first` / `last` inside the child resolve **per parent** | you hold both locators; column-style queries |
| `parent.locator(child)` | the same result; also takes `has` / `hasText` / `hasNot` / `hasNotText` | chaining from the container; a string selector child |
| `parent.getByRole(...).nth(2)` | `nth` over the **flattened** result | "the Nth match overall" |
| `parent.filter({ has: child })` | **parent** elements that contain a child | picking the row or card by its content |
| `a.and(b)` | elements matching both | two conditions on one element |
| `locator.visible()` / `filter({ visible })` | the same elements, visible only | replacing `:visible` |

**Per-parent `nth` is guaranteed only on 1.64.** `page.getByRole('cell').nth(2).within(page.getByRole('row'))`
is the third cell of every row. Whether `parent.locator(childWithNth)` behaved that way before 1.64 is
unverified, so a project below 1.64 does not rely on it.

**Down-level lane (below 1.64):** write `parent.locator(child)`. It gives the same result for everything
except the per-parent `nth` guarantee.

## 6. `visible()` [1.63] instead of `:visible`

`locator.visible()` matches only visible elements and is the recommended replacement for the `:visible`
pseudo-class (still accepted, no longer taught). Below 1.63 use `filter({ visible: true })` [1.51].

## 7. Frames

- `page.frameLocator('#checkout')` returns a `FrameLocator`; chain `getBy*` from it.
- `page.frameLocator()` with **no selector** [1.63] searches every frame in the subtree and errors if the
  matches span several frames. Use it when the iframe has no stable selector.
- `locator.contentFrame()` turns a located `<iframe>` into a `FrameLocator`, so the iframe itself can be
  found with the ladder: `page.getByTestId('Checkout.PaymentFrame').contentFrame().getByLabel('Card number')`.
- `frameLocator.owner()` goes the other way, to the `<iframe>` element.
- From 1.64, elements inside a hidden iframe count as hidden for actions, `isVisible()` and `toBeVisible()`.

## 8. Strictness, positional picks and overlays

- **Locators are strict for actions.** A click on a locator that matches two elements fails. Fix it by
  scoping (§4, §5) or filtering (§3), never by appending `.first()`.
- **`nth()` / `first()` / `last()` only with a stated reason**, and the reason is the field or method name:
  `newestNotification = notifications.first()` where newest-first order is the behaviour under test. An
  unnamed `.first()` that silences a strictness error is a defect.
- **`page.addLocatorHandler(locator, handler, { times, noWaitAfter })`** runs the handler whenever the
  locator becomes visible before an action or a web-first assertion — the cookie banner, the "new version"
  toast. Register it in a fixture so every test gets it, and remove it with `page.removeLocatorHandler`.
  It replaces "close the overlay if it is there" branches, which would be conditional logic in a test.

```typescript
await page.addLocatorHandler(page.getByTestId('Consent.Banner'), async (banner) => {
  await banner.getByRole('button', { name: 'Accept' }).click();
});
```

## 9. Naming locators: `describe()` [1.53]

`locator.describe('Sign-in error')` labels the locator in the trace, the HTML report and error messages;
`locator.description()` [1.57] reads it back. Use it on composed locators whose selector chain would read
as noise in a failure. `assets/LoginPage.ts` describes the form and its error.

## 10. The test-id attribute

| Stack | Where it is set |
|---|---|
| TypeScript runner | `use: { testIdAttribute: 'data-testid' }` in `playwright.config.ts` (or per project) |
| TypeScript library mode | `selectors.setTestIdAttribute('data-testid')` before creating pages |
| Java | `playwright.selectors().setTestIdAttribute("data-testid")` |
| .NET | `TestIdAttribute` in the `.runsettings` `Playwright` section |

`data-testid` is the default and the house contract. A project whose app ships `data-test` sets
`testIdAttribute: 'data-test'` and keeps `getByTestId` everywhere. Set one attribute name.

## 11. Agent-facing locators

These help an agent that is exploring a live page; committed tests use the ladder.

- `page.ariaSnapshot({ mode: 'ai' })` [1.59] returns the aria tree with `[ref=eN]` markers and includes
  iframes. `depth` limits it; `boxes` [1.60] appends bounding boxes.
- `page.getByRef('e2')` [1.64] resolves a ref from the latest AI-mode snapshot. Use it only in the
  session that took the snapshot.
- `await locator.normalize()` [1.59] rewrites a locator to best-practice form, and `.toString()` prints it
  as code — `await page.getByRef('e5').normalize()` turns a ref into a locator worth committing.
- `page.pickLocator()` / `page.cancelPickLocator()` [1.59] let a person click an element in a headed
  browser and return its locator.
