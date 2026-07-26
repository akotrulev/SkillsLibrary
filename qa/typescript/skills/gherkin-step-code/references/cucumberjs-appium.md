# CucumberJS + WebdriverIO Step Bindings + POM Implementation (Mobile / TypeScript)

The **mobile** path of the TypeScript `gherkin-step-code` family. Binds Gherkin steps to **@cucumber/cucumber** step definitions (`Given`/`When`/`Then`), run under `@wdio/cucumber-framework` against **WebdriverIO + Appium**. State is shared across steps via a **custom `World`** (`this.login`, …) — not fixtures. Assertions use WDIO's `expect`. The World, hooks, and `wdio.conf.ts` already exist from `bdd-project-setup`.

> Read the family router `../SKILL.md` first for the shared rules (one file per domain, Cucumber Expressions, thin steps, assertions in `Then`, reuse the catalog, build missing POMs first). This file is the mobile-specific deep dive: the **World** model, end to end.

## Stack

- `@cucumber/cucumber` 13.x (⚠️ pin to the line `@wdio/cucumber-framework` expects — verify the peer range), `webdriverio` 9.x, `@wdio/appium-service`, `appium` 2.x
- Step files under `steps/`, the World + hooks under `support/`, screen objects from the existing mobile project under `pages/mobile/`
- `CustomWorld` from `support/world.ts` (the scaffold owns it); `expect` from `@wdio/globals`
- Run: `npx wdio run ./wdio.conf.ts`

## The World model (the core difference from playwright-bdd)

CucumberJS has **no fixtures**. State is shared via the **World** — the `this` of every step and hook. The scaffold subclassed `World` (`CustomWorld`) and registered it with `setWorldConstructor`; the WebdriverIO `browser` is a global started by `@wdio/appium-service`, and the World exposes the screen objects built against it.

Because the World **is** `this`, every step and hook must be a **`function` expression — never an arrow function** (arrows capture the outer `this` and lose the World). Type `this` explicitly as `CustomWorld`.

```typescript
// support/world.ts (from bdd-project-setup) — recap, do not re-create
import { World, setWorldConstructor } from '@cucumber/cucumber';
import { LoginScreen } from '../pages/mobile/LoginScreen';

export class CustomWorld extends World {
  private _login?: LoginScreen;
  get login(): LoginScreen { return (this._login ??= new LoginScreen()); }
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
  await expect(this.login.errorBanner).toHaveText(message);
});
```

Note: `function` (not arrow), `this: CustomWorld` typed, Cucumber-Expression captures after `this`. WDIO matchers (`toHaveText`, `toBeDisplayed`, `toBeExisting`) auto-retry like Playwright's.

### A screen object the World doesn't yet expose

Add the getter to `CustomWorld` (don't `new` it in the step):

```typescript
// in support/world.ts
private _dashboard?: DashboardScreen;
get dashboard(): DashboardScreen { return (this._dashboard ??= new DashboardScreen()); }
```

### Custom parameter type

```typescript
// support/parameter-types.ts
import { defineParameterType } from '@cucumber/cucumber';

defineParameterType({
  name: 'daysAgo',
  regexp: /(\d+) days? ago/,
  transformer: (n: string) => new Date(Date.now() - Number(n) * 86_400_000),
});
```

### Data tables and doc strings

```typescript
When('I add the following items to the cart', async function (this: CustomWorld, table) {
  for (const row of table.hashes()) {
    await this.cart.addItem(row.sku, Number(row.qty));
  }
});
```

### Cleanup → `After` hook (NOT a step)

The `feature-file-writer` Cleanup handoff is implemented in the scaffold's `support/hooks.ts` as an `After` hook — never a Gherkin step.

```typescript
// support/hooks.ts (scaffold owns it) — recap
import { After, type ITestCaseHookParameter } from '@cucumber/cucumber';
import type { CustomWorld } from './world';

After(async function (this: CustomWorld, scenario: ITestCaseHookParameter) {
  if (scenario.result?.status === 'FAILED') await browser.takeScreenshot();
  await this.api?.deleteSeededData(); // the Cleanup handoff lives here, never in Gherkin
});
```

## Hard rules (mobile)

- **`function` expressions only** — type `this: CustomWorld`; never arrow functions (they lose the World).
- **Reach screen objects through `this` (the World), never `new`** them in a step.
- `async` bodies; `await` every screen-object call; no floating promises.
- **No `browser.$(...)` / selectors / waits in steps** — promote to the screen object.
- `Then` asserts with WDIO `expect(...)` (auto-retry); `Given`/`When` never assert; screen objects assert only in `verifyPageLoaded()`.
- **No `browser.pause(ms)`** — use WDIO's auto-waiting matchers or `browser.waitUntil(condition)` on a condition.
- **Version-compat:** keep `@cucumber/cucumber` on the line `@wdio/cucumber-framework` pins; don't force the latest standalone major.
- No hardcoded credentials/URLs — env vars / config.

## Anti-patterns to flag (mobile)

- An **arrow-function** step (`Given('…', async () => …)`) — loses `this`/World; state becomes inaccessible.
- Fixture-style destructuring (`async ({ login }) => …`) — that's the playwright-bdd model, wrong here.
- `new LoginScreen()` inside a step instead of a World getter.
- Module-level mutable state shared between steps instead of the World — violates "no static mutable state."
- Launching/quitting the Appium server by hand instead of `@wdio/appium-service`.
- `browser.$(...)` / selectors / `browser.pause(ms)` in a step body.
- Assertions in `Given`/`When`, or inside screen-object actions.
- Forcing `@cucumber/cucumber@13` against an older `@wdio/cucumber-framework` peer.

## Cross-references

- Mobile screen objects / WDIO conventions → `qa/typescript/skills/ui-test-author/appium`
- Screen-object extraction → `qa/typescript/skills/mobile-screen-objects` / `mobile-screen-explorer`
- POM architecture → `qa/typescript/skills/page-object-design`
- Allure labels from Gherkin tags → `qa/reporting/typescript/skills/test-reports`
- CI (device matrix, publish report) → `qa/cicd/typescript/skills/ci-pipelines`
