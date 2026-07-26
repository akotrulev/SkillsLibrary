# playwright-bdd Step Bindings + POM Implementation (Web / TypeScript)

The **web** path of the TypeScript `gherkin-step-code` family. Binds Gherkin steps to **playwright-bdd** step definitions created via `createBdd(test)`, where the `test` object has been extended with page objects as **Playwright fixtures** (the scaffold's `steps/fixtures.ts`). Steps destructure the fixtures they need; assertions use the web-first `expect` from `@playwright/test`. The model, lifecycle, and `fixtures.ts` already exist from `bdd-project-setup`.

> Read the family router `../SKILL.md` first for the shared rules (one file per domain, Cucumber Expressions, thin steps, assertions in `Then`, reuse the catalog, build missing POMs first). This file is the web-specific deep dive: the **fixtures** model, end to end.

## Stack

- `playwright-bdd` 9.2.x on `@playwright/test` ≥ 1.44, Node ≥ 20, TypeScript strict
- Step files under `steps/`, page objects from the existing UI project under `pages/`
- `createBdd(test)` exported from `steps/fixtures.ts` (the scaffold owns that file)
- Run: `npx bddgen` (compiles `.feature` → specs in `.features-gen/`) then `npx playwright test`

## The fixtures model (the core difference from .NET/Java/mobile)

There is **no World and no DI container**. Page objects are Playwright **fixtures**: declared once in `steps/fixtures.ts` via `base.extend<Fixtures>(...)`, then **destructured as the step's argument**. Every step is an **arrow function** whose single argument is the fixture object.

```typescript
// steps/fixtures.ts (from bdd-project-setup) — recap, do not re-create
import { test as base, createBdd } from 'playwright-bdd';
import { LoginPage } from '../pages/LoginPage';
import { DashboardPage } from '../pages/DashboardPage';

type Fixtures = { loginPage: LoginPage; dashboardPage: DashboardPage };

export const test = base.extend<Fixtures>({
  loginPage: async ({ page }, use) => { await use(new LoginPage(page)); },
  dashboardPage: async ({ page }, use) => { await use(new DashboardPage(page)); },
});

export const { Given, When, Then } = createBdd(test);
```

Because `Given/When/Then` come from `createBdd(test)`, every step body receives the **same fixture object Playwright Test builds per test** — `page`, `request`, and the page-object fixtures are all reachable by destructuring. This is how state is shared across steps; you never `new` a page object in a step.

## Templates

### Step definition — `steps/authentication.steps.ts`

```typescript
import { expect } from '@playwright/test';
import { Given, When, Then } from './fixtures';

Given('I am on the login page', async ({ loginPage }) => {
  await loginPage.goto();
  await loginPage.expectLoaded();
});

When('I sign in as a registered customer', async ({ loginPage }) => {
  await loginPage.signIn(process.env.E2E_USER!, process.env.E2E_PASSWORD!);
});

When(
  'I sign in with email {string} and password {string}',
  async ({ loginPage }, email: string, password: string) => {
    await loginPage.signIn(email, password);
  },
);

Then('I land on the dashboard', async ({ dashboardPage }) => {
  await dashboardPage.expectLoaded();
});

Then('I see the error {string}', async ({ loginPage }, message: string) => {
  await expect(loginPage.errorBanner).toHaveText(message);
});
```

Note the argument order: the **fixture object first**, then the Cucumber-Expression captures (`email`, `password`, `message`) typed explicitly. `{string}` → `string`, `{int}` → `number`, `{float}` → `number`.

### A fixture that needs a different page object

When a step needs a page object not yet in `Fixtures`, **add it to `steps/fixtures.ts`** (don't construct it in the step):

```typescript
// in steps/fixtures.ts
type Fixtures = { loginPage: LoginPage; dashboardPage: DashboardPage; cartPage: CartPage };
// ...
cartPage: async ({ page }, use) => { await use(new CartPage(page)); },
```

### Custom parameter type

```typescript
// steps/parameter-types.ts
import { createBdd } from 'playwright-bdd';
import { test } from './fixtures';

const { defineParameterType } = createBdd(test);

defineParameterType({
  name: 'daysAgo',
  regexp: /(\d+) days? ago/,
  transformer: (n: string) => new Date(Date.now() - Number(n) * 86_400_000),
});
// usage: When('the order was placed {daysAgo}', async ({ … }, when: Date) => { … });
```

### Data tables and doc strings

```typescript
When('I add the following items to the cart', async ({ cartPage }, table) => {
  for (const row of table.hashes()) {
    await cartPage.addItem(row.sku, Number(row.qty));
  }
});
```

The data-table is the **last** parameter, after the fixture object and any inline captures.

### Cleanup → fixture teardown (NOT a step)

The `feature-file-writer` Cleanup handoff is implemented as **teardown inside a fixture** (the scaffold owns `fixtures.ts`), after the `await use(...)` line — or via an `After` from `createBdd(test)` for scenario-scoped teardown. Never a Gherkin step.

```typescript
// in steps/fixtures.ts — a fixture that seeds then cleans up
seededOrder: async ({ request }, use) => {
  const res = await request.post('/api/orders', { data: orderFixture() });
  const order = await res.json();
  await use(order);
  await request.delete(`/api/orders/${order.id}`); // teardown == the Cleanup handoff
},
```

## Hard rules (web)

- **Arrow functions only** — the step argument is the fixture object; never use `function` + `this`. There is no World.
- **Destructure fixtures, never `new`** a page object inside a step.
- `async` bodies; `await` every page-object call; no floating promises.
- **No `page.locator(...)` / CSS / waits in steps** — promote to the page object.
- `Then` asserts with web-first `expect(locator)…` (auto-retry); `Given`/`When` never assert; page objects assert only in `expectLoaded()`.
- **No `page.waitForTimeout`** — auto-wait + web-first assertions only.
- `bddgen` runs **before** `playwright test`; point `testDir` at the generated dir, never `features/`.
- No hardcoded credentials/URLs — env vars / config.

## Anti-patterns to flag (web)

- A `function`/`this`-based step (World-style) in a playwright-bdd project.
- `new LoginPage(page)` inside a step instead of a fixture.
- Forgetting to register a needed page object as a fixture (constructing it ad hoc).
- Running `playwright test` without a prior `bddgen` (stale generated specs).
- `page.locator(...)` / selectors / `waitForTimeout` in a step body.
- Assertions in `Given`/`When`, or inside page-object actions.

## Cross-references

- Web page objects / fixtures conventions → `qa/typescript/skills/ui-test-author/playwright`
- POM architecture → `qa/typescript/skills/page-object-design`
- Network stubbing inside BDD steps → `qa/typescript/skills/network-mocking`
- Allure labels from Gherkin tags → `qa/reporting/typescript/skills/test-reports`
- CI (bddgen step, shard, publish report) → `qa/cicd/typescript/skills/ci-pipelines`
