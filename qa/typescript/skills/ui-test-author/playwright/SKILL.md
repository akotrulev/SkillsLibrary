---
name: qa-ui-test-author-playwright-typescript
description: Use when the user asks to scaffold Playwright UI tests in TypeScript — new spec files, page objects under `tests/pages/`, or a specific scenario (login, form, accessibility, visual). Triggers: "write a Playwright test for X in TypeScript", "add a Playwright TS page object for screen Y", "scaffold a Playwright spec (TS)". For end-to-end suite work prefer the phased agent `qa-ui-typescript` / `qa-bdd-typescript` (or the matching slash command), which loads this skill inside its workflow; use this skill directly for a single targeted artifact.
---

# QA — Playwright Test & Page Object Generator (TypeScript)

Scaffolds Playwright `@playwright/test` specs and page objects in TypeScript. Uses the **fixture-driven page object pattern**: page objects are exposed as Playwright fixtures, not constructed manually in every test. Locators use `getByTestId` first (`data-testid` is the standing contract with the dev team — see `qa/typescript/skills/pom-builder` for extraction and the missing-testid report), falling back to role/label semantics — never raw CSS where anything better exists.

## Stack

- Node 20 + TypeScript (strict mode)
- `@playwright/test` (Playwright Test runner)
- Page objects under `tests/pages/`, specs under `tests/specs/`
- Fixtures under `tests/fixtures/`
- Allure reporter (`allure-playwright`) where the project uses Allure
- `eslint-plugin-playwright` (`flat/recommended`) wired into `eslint.config.mjs` — many anti-patterns below are caught automatically

## When to use

- New `*.spec.ts` under `tests/specs/`
- New page object under `tests/pages/`
- New fixture (auth state, seeded data, page-object factory) under `tests/fixtures/`
- Adding a scenario to an existing spec

## When NOT to use

- Mobile / Appium → `qa/typescript/skills/ui-test-author/appium`
- Java Selenium → `qa/java/skills/ui-test-author/selenium`
- Reviewing existing Playwright code → `qa/typescript/skills/ui-test-author/reviewer`
- Designing the overall page-object hierarchy → `qa/typescript/skills/page-object-architect`

## Inputs needed

1. **Feature / page** under test (e.g. `Login`, `CheckoutCart`)
2. **User journey** — concrete steps + the user-visible outcome to assert
3. **Locators** — for each element: `getByTestId` whenever the element has a `data-testid`; otherwise `getByRole` / `getByLabel`, then `getByText`; CSS only as last resort. Missing testids are reported via `qa/typescript/skills/pom-builder`'s `missing-testids.md`
4. **Auth requirement** — anonymous, or signed-in (which user role + how the session is established)
5. **Test data** — seeded by API, by fixture, or inline

## Patterns

### Page object — `tests/pages/LoginPage.ts`

```typescript
import { Page, Locator, expect } from '@playwright/test';

export class LoginPage {
  readonly page: Page;
  readonly email: Locator;
  readonly password: Locator;
  readonly submit: Locator;
  readonly errorBanner: Locator;

  constructor(page: Page) {
    this.page = page;
    this.email = page.getByLabel('Email');
    this.password = page.getByLabel('Password');
    this.submit = page.getByRole('button', { name: 'Sign in' });
    this.errorBanner = page.getByTestId('login-error');
  }

  async goto(): Promise<void> {
    await this.page.goto('/login');
  }

  async signIn(email: string, password: string): Promise<void> {
    await this.email.fill(email);
    await this.password.fill(password);
    await this.submit.click();
  }

  async expectLoaded(): Promise<void> {
    await expect(this.email).toBeVisible();
  }
}
```

### Fixture — `tests/fixtures/pages.ts`

Expose page objects as fixtures so tests destructure them — no per-test `new LoginPage(page)` boilerplate.

```typescript
import { test as base } from '@playwright/test';
import { LoginPage } from '../pages/LoginPage';
import { HomePage } from '../pages/HomePage';

type Pages = {
  loginPage: LoginPage;
  homePage: HomePage;
};

export const test = base.extend<Pages>({
  loginPage: async ({ page }, use) => { await use(new LoginPage(page)); },
  homePage:  async ({ page }, use) => { await use(new HomePage(page)); },
});

export { expect } from '@playwright/test';
```

### Spec — `tests/specs/login.spec.ts`

```typescript
import { test, expect } from '../fixtures/pages';

test.describe('Login', () => {
  test('signs in with valid credentials', async ({ loginPage, homePage }) => {
    await loginPage.goto();
    await loginPage.signIn(process.env.E2E_USER!, process.env.E2E_PASSWORD!);

    await homePage.expectLoaded();
    await expect(homePage.greeting).toContainText('Welcome');
  });

  test('shows an error for an invalid password', async ({ loginPage }) => {
    await loginPage.goto();
    await loginPage.signIn(process.env.E2E_USER!, 'wrong');

    await expect(loginPage.errorBanner).toBeVisible();
    await expect(loginPage.errorBanner).toHaveText(/invalid credentials/i);
  });
});
```

### Authenticated state via `storageState`

For tests that need a signed-in session, create a global setup that signs in once and persists `storageState`:

```typescript
// tests/auth.setup.ts
import { test as setup } from '@playwright/test';
import { LoginPage } from './pages/LoginPage';

const STATE = 'playwright/.auth/user.json';

setup('authenticate', async ({ page }) => {
  const loginPage = new LoginPage(page);
  await loginPage.goto();
  await loginPage.signIn(process.env.E2E_USER!, process.env.E2E_PASSWORD!);
  await page.context().storageState({ path: STATE });
});
```

In `playwright.config.ts`, declare a `setup` project that other projects depend on:

```typescript
projects: [
  { name: 'setup', testMatch: /.*\.setup\.ts/ },
  { name: 'chromium', use: { ...devices['Desktop Chrome'], storageState: STATE }, dependencies: ['setup'] },
]
```

### API-seeded data

When test data is created via API, do it in a fixture so the spec stays focused:

```typescript
export const test = base.extend<{ seededOrder: Order }>({
  seededOrder: async ({ request }, use) => {
    const res = await request.post('/api/orders', { data: orderFixture() });
    expect(res.ok()).toBeTruthy();
    const order = await res.json();
    await use(order);
    await request.delete(`/api/orders/${order.id}`);
  },
});
```

## Rules

### Locator preference order (strict)

1. `getByTestId(id)` — **preferred whenever the element carries a `data-testid`**; the attribute is the agreed contract with the app team. Elements missing it go in the `missing-testids.md` dev-team report (extraction workflow: `qa/typescript/skills/pom-builder`) and use a fallback below with `// TODO: missing data-testid '<suggested>'`
2. `getByRole(role, { name })` — best fallback; matches the accessibility tree
3. `getByLabel(text)` — for form inputs
4. `getByPlaceholder(text)` — only when there is no label
5. `getByText(text, { exact })` — for assertions on visible text
6. CSS / XPath — **last resort**; add `// TODO: replace with data-testid locator` and a brief reason

### Page object rules

- Locators are `readonly Locator` instance fields initialized in the constructor — **not** functions that re-query the DOM
- Constructor signature is `(page: Page)` — never take strings or config
- Action methods are `async` and return `Promise<void>` for same-page actions; for navigation return the next page object (e.g. `Promise<HomePage>`)
- An `expectLoaded(): Promise<void>` method must exist and assert one landmark locator is visible
- **No assertions inside actions** — actions perform; tests and `expectLoaded` assert
- **No `page.locator('css selector')` in spec files** — wrap inside a page object

### Test rules

- Use `test.describe` to group scenarios per feature; one spec file per feature
- Test titles describe behavior in lowercase imperative: `signs in with valid credentials`, `shows an error for an invalid password`
- One logical behavior per `test(...)`. Multiple `expect` calls are fine if they verify one behavior; otherwise split.
- **Every test asserts something.** A test that ends after an action with no `expect` is not a test.
- Use web-first assertions: `expect(loc).toBeVisible()` / `.toHaveText(...)` / `.toHaveURL(...)` / `.toHaveCount(n)` / `.toBeEnabled()`. They retry until timeout. Never `expect(await loc.isVisible()).toBe(true)` or `expect(await loc.textContent()).toBe('x')` — one-shot checks lose auto-waiting.
- Prefer positive assertions over negated ones: `toBeHidden()` over `.not.toBeVisible()`, `toBeDisabled()` over `.not.toBeEnabled()`.
- **No `page.waitForTimeout(ms)`** — use a web-first assertion or `expect(...).toPass()` for conditional waits.
- **Do not pass `{ waitUntil: 'networkidle' }` to `goto`.** It is brittle on SPAs with long-polling / WebSockets. Navigate, then assert a user-visible landmark.
- **Do not pre-wait before auto-waiting actions.** `click` / `fill` / `check` already wait for actionability — `locator.waitFor({ state: 'visible' })` followed by `locator.click()` is redundant.
- **Do not use `{ force: true }`.** It skips actionability checks and hides real bugs (covered elements, hidden inputs). Fix the flow — close the overlay, scroll into view — instead of forcing.
- **`waitForNavigation` is deprecated.** Use `page.waitForURL('**/path')` or a web-first URL/landmark assertion.
- **`waitForResponse` ordering:** set the listener first **without** `await`, perform the action, then `await` the promise:
  ```typescript
  const responsePromise = page.waitForResponse(r => r.url().includes('/api/data') && r.status() === 200);
  await loginPage.submit.click();
  await responsePromise;
  ```
  Awaiting before the action will hang; awaiting after the action races the response.
- **Retry loops:** never hand-roll `while (retries--) { … sleep }`. Use `await expect(async () => { … }).toPass({ timeout, intervals })` or `await expect.poll(async () => …, { timeout, intervals }).toBe(...)`. Inside `toPass`, give inner assertions an explicit short `timeout` (e.g. `{ timeout: 1_000 }`) so the outer retry can iterate quickly.
- Prefer web-first assertions over `expect.poll` for plain DOM checks (`toHaveText`, `toBeVisible`, `toHaveCount`). Reserve `expect.poll` for non-DOM polling.
- Prefer web-first assertions over `page.waitForFunction(...)` for UI state.
- Pass `{ exact: true }` to `getByText` / `getByRole` when the expected text is a substring of other labels on the page (`Submit` vs `Submit Order` / `Submitting…`) — otherwise a future label change causes a strict-mode violation.
- **No `expect.soft` chains pretending to be hard assertions** — pick `expect` for blocking, `expect.soft` deliberately when the test must continue.
- Use `test.step('...')` to label substeps; substeps show up in the HTML report and Allure.
- **Do not use `test.describe.serial` to model multi-step flows.** Each test must set up its own state. If a flow is genuinely one journey, put the whole flow in a single test and use `test.step` for the phases.
- Tag tests via the title or annotations: `test('@smoke logs in', ...)` so projects can filter.

### Auth & storage state

- Sign in **once** per browser/project via the `setup` project and `storageState`; do not log in inside every test
- For tests that need a different role, create a separate `setup` project per role and a separate `storageState` file
- Anonymous tests run in the default project with no `storageState`

### What NOT to do

- No `page.waitForTimeout(ms)` — every wait must be conditional on a Locator or response
- No `{ waitUntil: 'networkidle' }` — assert a landmark instead
- No `{ force: true }` on `click` / `fill` / `check` — fix the underlying flow
- No `locator.waitFor(...)` immediately before an auto-waiting action — it is redundant
- No `waitForNavigation` (deprecated) — use `waitForURL` or a URL assertion
- No hand-rolled retry loops — use `expect(...).toPass()` or `expect.poll(...)`
- No `expect.poll`/`waitForFunction` for state covered by a web-first assertion
- No `.not.toBeVisible()` when `toBeHidden()` exists; no `.not.toBeEnabled()` when `toBeDisabled()` exists
- No `test.describe.serial` to chain dependent tests — one test + `test.step`
- No `page.locator('div.foo > span:nth-child(3)')` in specs — promote to a page object with a semantic locator
- No `await page.goto(...)` directly in specs — put it in the page object's `goto()` so it knows its own URL
- No `console.log` for debugging in committed tests — use `test.step` and the trace viewer instead
- No assertions in action methods — `expectLoaded()` is the only assertion that belongs on a page object
- No `if`/`for` driving assertions — use parameterized tests outside the `test` body (`for (const [name, value] of cases) test(name, ...)`)
- No shared mutable state between tests — each test gets a fresh `page` and fresh fixtures
- No hardcoded credentials, base URLs, or environment hostnames — read from env vars / `playwright.config.ts`
- No `expect(true).toBe(...)` boolean dance — call the real Playwright matcher with auto-waiting
- No test without at least one `expect` — actions without assertions verify nothing

## Generation steps

1. Confirm **feature**, **scenarios**, **locators**, **auth requirement**, and **data source** with the user.
2. For each new screen, generate or extend `tests/pages/{Name}Page.ts`:
   - One `readonly Locator` per element, initialized in the constructor with the best-available semantic locator
   - `goto()` method that owns the URL
   - `expectLoaded()` that asserts one landmark
   - One action method per user-intent action
3. Register the page object as a fixture in `tests/fixtures/pages.ts`.
4. Generate `tests/specs/{feature}.spec.ts`:
   - `test.describe(feature, () => { ... })`
   - One `test(...)` per scenario, destructuring the page-object fixtures
   - Use `test.step` for non-trivial workflows
5. For authenticated flows, ensure a `setup` project exists and the spec's project depends on it.
6. Run `npx playwright test` — expect 0 failures. Run `npx playwright test --ui` to verify locator strategies under the inspector before committing.

## Handoffs

- Designing the page-object hierarchy → `qa/typescript/skills/page-object-architect`
- Reviewing existing Playwright tests → `qa/typescript/skills/ui-test-author/reviewer`
- Test data builders → `qa/typescript/skills/test-data-builder`
- Allure reporter setup → `qa/reporting/typescript/skills/allure-reporting`
