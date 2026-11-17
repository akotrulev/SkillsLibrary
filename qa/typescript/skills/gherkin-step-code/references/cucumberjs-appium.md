# CucumberJS + WebdriverIO Step Bindings + POM Implementation (Mobile / TypeScript)

The **mobile** path of the TypeScript `gherkin-step-code` family. Binds Gherkin steps to **@cucumber/cucumber** step definitions (`Given`/`When`/`Then`), run under `@wdio/cucumber-framework` against **WebdriverIO + Appium**. State is shared across steps via a **custom `World`** (`this.login`, …) — not fixtures. Assertions use WDIO's `expect`. The World, hooks, and `wdio.conf.ts` already exist from `bdd-project-scaffold`.

> Read the family router `../SKILL.md` first for the shared rules (one file per domain, Cucumber Expressions, the step as the intent layer, one binding per field, assertions in `Then`, reuse the catalog, build missing POMs first). This file is the mobile-specific deep dive: the **World** model, end to end.

## Stack

- `@cucumber/cucumber` 13.3.0 inside the peer range of `@wdio/cucumber-framework` 10.0.1 (`^13.2.1`; verify it before locking), `webdriverio` and `appium` at the pins of `qa/typescript/skills/ui-test-author/appium` (Appium 3 / WDIO 10 primary; Appium 2 / WDIO 9 supported), `@wdio/appium-service`
- Step files under `steps/`, the World + hooks under `support/`, screen objects from the existing mobile project under `pages/mobile/`
- `CustomWorld` from `support/world.ts` (the scaffold owns it); `expect` from `@wdio/globals`
- Run: `npx wdio run ./wdio.conf.ts`

## The World model (the core difference from playwright-bdd)

CucumberJS has **no fixtures**. State is shared via the **World** — the `this` of every step and hook. The scaffold subclassed `World` (`CustomWorld`) and registered it with `setWorldConstructor`; the WebdriverIO `browser` is a global started by `@wdio/appium-service`, and the World exposes the screen objects built against it.

Because the World **is** `this`, every step and hook must be a **`function` expression — never an arrow function** (arrows capture the outer `this` and lose the World). Type `this` explicitly as `CustomWorld`.

`support/world.ts` comes from `bdd-project-scaffold`; do not re-create it.

```typescript
import { World, setWorldConstructor } from '@cucumber/cucumber';
import { LoginPage } from '../pages/mobile/LoginPage';

export class CustomWorld extends World {
  private _login?: LoginPage;
  get login(): LoginPage { return (this._login ??= new LoginPage()); }
}
setWorldConstructor(CustomWorld);
```

## Templates

### Step definition — `steps/authentication.steps.ts`

```typescript
import { Given, When, Then } from '@cucumber/cucumber';
import { expect } from '@wdio/globals';
import type { CustomWorld } from '../support/world';

Given('I am on the login screen', async function (this: CustomWorld) {
  await this.login.verifyPageLoaded();
});

When('I sign in as a registered customer', async function (this: CustomWorld) {
  await this.login.signIn(process.env.E2E_USER!, process.env.E2E_PASSWORD!);
});

When(
  'I sign in with email {string} and password {string}',
  async function (this: CustomWorld, email: string, password: string) {
    await this.login.signIn(email, password);
  },
);

Then('I land on the dashboard', async function (this: CustomWorld) {
  await this.dashboard.verifyPageLoaded();
});

Then('I see the error {string}', async function (this: CustomWorld, message: string) {
  expect(await this.login.errorText()).toBe(message);
});
```

Note: `function` (not arrow), `this: CustomWorld` typed, Cucumber-Expression captures after `this`. A `Then` asserts on what a query returns (`errorText()`), and the query waits for its element before reading it.

### A step acting on an exposed element — `steps/deals.steps.ts`

Outside BDD a screen object exposes no element. In a BDD suite the step is the intent layer, so a screen object used by steps may expose named elements and controls, and a single interaction needs no screen method; a method stays for a sequence (`signIn`). The screen object still owns every selector.

```typescript
import { $ } from '@wdio/globals';

export class DealFilterScreen {
  get counterparty() { return $('~DealFilter.Counterparty'); }
  get search() { return $('~DealFilter.Search'); }
}
```

```typescript
import { When } from '@cucumber/cucumber';
import type { CustomWorld } from '../support/world';

When('I enter {string} for Counterparty filter', async function (this: CustomWorld, name: string) {
  await this.dealFilter.counterparty.setValue(name);
});

When('I search', async function (this: CustomWorld) {
  await this.dealFilter.search.click();
});
```

Each field has its own binding named after it; a generic `I enter {string} for {string} filter` would look the field up by name inside the step, which is a branch.

### Pre-clean — a `Given … does not exist` step

A precondition removing a leftover record before the scenario, through an API seeder the World exposes, never a UI sequence. The `After` hook still removes what the scenario creates.

```typescript
import { Given } from '@cucumber/cucumber';
import type { CustomWorld } from '../support/world';

Given('the customer {string} does not exist', async function (this: CustomWorld, email: string) {
  await this.customerSeeder.deleteByEmail(email);
});
```

`deleteByEmail` searches by the email and deletes every match, so a clean environment is zero deletions, not a branch. `dealFilter` and `customerSeeder` are World getters, added as the next section shows.

### A scenario ahead of its automation

No binding is left with an empty body: it passes doing nothing. The scenario carries the suite's excluded tag and a ticket (`@not-automated @JIRA-1234`), and `cucumberOpts: { tags: 'not @not-automated' }` in `wdio.conf.ts` keeps it out of the run.

### A screen object the World doesn't yet expose

Add the getter to `CustomWorld` in `support/world.ts` (don't `new` it in the step):

```typescript
private _dashboard?: DashboardPage;
get dashboard(): DashboardPage { return (this._dashboard ??= new DashboardPage()); }
```

### Custom parameter type

`support/parameter-types.ts`:

```typescript
import { defineParameterType } from '@cucumber/cucumber';

defineParameterType({
  name: 'daysAgo',
  regexp: /(\d+) days? ago/,
  transformer: (n: string) => new Date(Date.now() - Number(n) * 86_400_000),
});
```

### Data tables and doc strings

```typescript
When('I add the following items to the cart', async function (this: CustomWorld, table: DataTable) {
  await this.cart.addItems(table.hashes().map((row) => ({ sku: row.sku, quantity: Number(row.qty) })));
});
```

The table goes to the screen object whole: repeating `addItem` over the rows is `CartPage.addItems`'s job, so the
step stays one line of intent. `DataTable` is imported from `@cucumber/cucumber`.

### Cleanup → `After` hook (NOT a step)

The `feature-file-writer` Cleanup handoff is implemented in the scaffold's `support/hooks.ts` as an `After` hook — never a Gherkin step. The same hook keeps the failure evidence: the screenshot is **attached to the scenario**, so it reaches the Cucumber report and Allure instead of being discarded.

```typescript
import { After, Status, type ITestCaseHookParameter } from '@cucumber/cucumber';
import { browser } from '@wdio/globals';
import type { CustomWorld } from './world';

After(async function (this: CustomWorld, scenario: ITestCaseHookParameter) {
  if (scenario.result?.status === Status.FAILED) {
    this.attach(Buffer.from(await browser.takeScreenshot(), 'base64'), 'image/png');
  }
  await this.api?.deleteSeededData();
});
```

`browser.takeScreenshot()` returns base64, so the hook decodes it before `attach`. Page source, device log and the recording are `qa/typescript/skills/evidence-capture/references/appium.md`; under Cucumber its hook runs in `afterScenario`, not `afterTest`.

## Hard rules (mobile)

- **`function` expressions only** — type `this: CustomWorld`; never arrow functions (they lose the World).
- **Reach screen objects through `this` (the World), never `new`** them in a step.
- `async` bodies; `await` every screen-object call; no floating promises.
- **No `browser.$(...)` / selectors / waits in steps** — promote to the screen object. Acting on an element the screen object exposes by name is the step's job.
- **One binding per field, filter or column**; no step that takes the field name.
- **No empty body**; a scenario ahead of its automation is tagged out (`not @not-automated`) with a ticket.
- `Then` asserts with WDIO `expect(...)` on the value a screen-object query returns; `Given`/`When` never assert; screen objects assert only in `verifyPageLoaded()`.
- **No `browser.pause(ms)`** — use WDIO's auto-waiting matchers or `browser.waitUntil(condition)` on a condition.
- **Version-compat:** keep `@cucumber/cucumber` inside the peer range of `@wdio/cucumber-framework`; do not force a newer standalone major.
- No hardcoded credentials/URLs — env vars / config.

## Anti-patterns to flag (mobile)

- An **arrow-function** step (`Given('…', async () => …)`) — loses `this`/World; state becomes inaccessible.
- Fixture-style destructuring (`async ({ login }) => …`) — that's the playwright-bdd model, wrong here.
- `new LoginPage()` inside a step instead of a World getter.
- Module-level mutable state shared between steps instead of the World — violates "no static mutable state."
- Launching/quitting the Appium server by hand instead of `@wdio/appium-service`.
- `browser.$(...)` / selectors / `browser.pause(ms)` in a step body.
- A generic step taking a field name, or a step with an empty body.
- Assertions in `Given`/`When`, or inside screen-object actions.
- A failure screenshot taken and thrown away: it must be attached with `this.attach`.
- An `@cucumber/cucumber` version outside the `@wdio/cucumber-framework` peer range.

## Cross-references

- Mobile screen objects / WDIO conventions → `qa/typescript/skills/ui-test-author/appium`
- Screen-object extraction → `qa/typescript/skills/mobile-screen-objects` / `mobile-screen-explorer`
- POM architecture → `qa/typescript/skills/page-object-design`
- Allure labels from Gherkin tags → `qa/reporting/typescript/skills/test-reports`
- CI (device matrix, publish report) → `qa/cicd/typescript/skills/ci-pipelines`
