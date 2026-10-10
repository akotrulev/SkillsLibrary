# Assertions — Playwright 1.64 (TypeScript)

Web-first assertions retry until they pass or the `expect` timeout (5 s by default, `expect: { timeout }`
in the config) runs out. They are the only way a UI test checks state. The version in brackets is where
an API first shipped.

## 1. The web-first set

**Locator assertions** — `await expect(locator).<matcher>(...)`:

| Checks | Matcher |
|---|---|
| Presence and visibility | `toBeVisible()`, `toBeHidden()`, `toBeAttached()`, `toBeInViewport()` |
| State | `toBeEnabled()`, `toBeDisabled()`, `toBeEditable()`, `toBeChecked()`, `toBeFocused()`, `toBeEmpty()` |
| Text | `toHaveText(text \| text[])` (whole text), `toContainText(...)` (substring) |
| Form values | `toHaveValue('42')`, `toHaveValues(['a', 'b'])` for a multi-select |
| Count | `toHaveCount(3)` |
| Accessibility | `toHaveAccessibleName('Sign in')`, `toHaveAccessibleDescription(...)`, `toHaveAccessibleErrorMessage('Email is required')` [1.50], `toHaveRole('button')` |
| Classes | `toContainClass('selected')` [1.52] matches class names one by one; `toHaveClass('a b')` matches the whole attribute |
| Attributes and style | `toHaveAttribute('aria-expanded', 'true')`, `toHaveId(...)`, `toHaveCSS('color', 'rgb(0, 0, 0)')`, `toHaveCSS(..., { pseudo: '::before' })` [1.60], `toHaveJSProperty(...)` |
| Structure | `toMatchAriaSnapshot(yaml)` |

`toBeEditable()` throws when the element is not an editable kind of element at all, such as a `<div>`
[1.50]; point it at the input itself.

**Page assertions** — `await expect(page).<matcher>(...)`, used through a fixture or page object:

- `toHaveURL(url)`: a **string** must equal the whole URL, with a relative path resolved against
  `baseURL`; a **RegExp** matches part of it; a **predicate** `(url: URL) => boolean` [1.51] checks
  structured parts (`url => url.searchParams.get('tab') === 'billing'`). `ignoreCase` is an option.
- `toHaveTitle(...)`.
- `toMatchAriaSnapshot(yaml)` on the whole page [1.60].

Screenshots (`toHaveScreenshot`) belong to `qa/typescript/skills/visual-regression`.

## 2. Aria snapshots

`toMatchAriaSnapshot` compares the accessibility tree against a YAML template. It is the cheapest
structural check of a region: roles, names and states without pixels.

```typescript
await expect(orders.list).toMatchAriaSnapshot(`
  - list "Orders":
    - listitem: /Order #\\d+/
`);
```

- Locator form since 1.49, page form since 1.60.
- `/children: equal` makes child matching strict and `/url:` checks link targets [1.52]; input
  `placeholder` is compared [1.56].
- Keep large templates in files: `toMatchAriaSnapshot({ name: 'orders.aria.yml' })` [1.50] stores them under
  `<spec>-snapshots/`. An empty template `toMatchAriaSnapshot('')` is filled in on a local run.
- Snapshot updates follow `updateSnapshots` in the config (`assets/playwright.config.ts`: `'none'` on CI,
  `'missing'` locally) and the `--update-snapshots` flag; see `config-and-fixtures.md` for the 1.64 change.

## 3. One expected condition

Every assertion states one value. Assert `toHaveText('Saved')`, never `toHaveText(/Saved|Success/)`;
`toHaveCount(3)`, never "at least 3"; never `expect([a, b]).toContain(x)` or a `||` inside an `expect`; never
an assertion on an `or()` locator. A regex alternation is the commonest disguise. If two outcomes are
reachable, split them into one test each, or one generated test per row. The only exception is an explicit
instruction to accept more than one value, recorded in the test as an annotation
(`{ annotation: { type: 'accepted-values', description: '<who asked, where>' } }`).

Prefer the positive matcher: `toBeHidden()` over `.not.toBeVisible()`, `toBeDisabled()` over
`.not.toBeEnabled()`.

## 4. No one-shot reads

A value read once and then compared does not retry, so it races the UI and fails without evidence.

| One-shot read (banned) | Web-first fix |
|---|---|
| `expect(await loc.isVisible()).toBe(true)` | `await expect(loc).toBeVisible()` |
| `expect(await loc.textContent()).toBe('Saved')` / `innerText()` | `await expect(loc).toHaveText('Saved')` |
| `expect(await loc.inputValue()).toBe('42')` | `await expect(loc).toHaveValue('42')` |
| `expect(await loc.count()).toBe(3)` | `await expect(loc).toHaveCount(3)` |
| `expect(await loc.getAttribute('aria-expanded')).toBe('true')` | `await expect(loc).toHaveAttribute('aria-expanded', 'true')` |
| `expect(page.url()).toBe(...)` | `await expect(page).toHaveURL(...)` |
| `expect(await loc.isChecked()).toBe(true)` | `await expect(loc).toBeChecked()` |

Reading a value is fine when the value feeds the next step rather than an assertion (an order number
copied from the confirmation into a search box).

## 5. Polling, retry blocks and soft assertions

- **`expect.poll(fn, { timeout, intervals })`** retries a non-DOM value — an API status, a queue depth:
  `await expect.poll(() => orders.statusOf(id), { timeout: 10_000 }).toBe('Shipped')`. Never use it for
  something a web-first matcher covers.
- **`expect(async () => { ... }).toPass({ timeout, intervals })`** retries a block of steps that must pass
  together. Its own timeout defaults to none, so always set one, and give the inner assertions a short
  `{ timeout: 1_000 }` so the block can iterate. It replaces every hand-rolled `while (retries--)` loop.
- **`expect.soft(...)`** records a failure and lets the test continue; the test still fails at the end.
  Use it deliberately for independent checks on one screen, never as a quiet hard assertion.
  `expect.soft.poll(...)` [1.61] is the polling form.
- **`expect.configure({ timeout, soft })`** builds a scoped `expect` for a slow region instead of raising
  the global timeout. `expect.extend({ ... })` adds a project matcher when one domain check repeats.
- `page.waitForFunction(...)` and `locator.waitForFunction(fn)` [1.62] are for state no matcher can see;
  UI state uses the matchers.

## 6. Failure messages name the subject

A failure reading `expected '' to be 'Saved'` cannot be told apart from a locator that matched the wrong
element. Give each assertion its subject.

| Stack | How |
|---|---|
| TypeScript | The message argument: ``await expect(banner, `success banner for order ${orderId}`).toHaveText('Saved')`` |
| Java | `assertThat` has no message parameter. Name the locator with `describe("Success banner")`, so the failure prints it |
| .NET | `await Expect(banner, "success banner").ToHaveTextAsync("Saved")` [1.60] |

`locator.describe()` [1.53] helps in every stack: the trace and the report show the description instead
of the selector chain.

## 7. HTTP responses inside UI tests

A fixture that seeds data through `request` asserts the exact status with the body as evidence:
`expect(response.status(), await response.text()).toBe(201)`. Never `expect(response.ok()).toBeTruthy()`
and never `toBeOK()` — both accept any 2xx and print nothing useful. `assets/fixtures.ts` shows it.
