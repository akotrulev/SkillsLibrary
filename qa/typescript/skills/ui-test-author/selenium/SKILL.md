---
name: qa-ui-test-writer-selenium-typescript
description: Use when the user asks to scaffold a TypeScript + Selenium 4 page object or Mocha/Vitest UI test, following the BasePage / DriverFactory pattern. Triggers: "create a Selenium page object for X in TS", "add a TypeScript Selenium page for screen Y", "write a Selenium TS UI test for Z". For end-to-end suite work prefer the staged agent `qa-ui-typescript` (or the matching slash command), which loads this skill inside its workflow; use this skill directly for a single targeted artifact.
---

# QA — Selenium TypeScript Page Object & Test Generator

Scaffolds Selenium 4 page objects and Mocha (or Vitest) UI tests in TypeScript strict mode, mirroring the Java and .NET siblings. Uses a thin `BasePage` with explicit waits, element accessors that return `Promise<WebElement>`, and a `DriverFactory` that produces one driver per worker for parallel-safe runs.

> Most TypeScript shops doing UI tests pick Playwright over Selenium. This skill exists for parity and for projects that must stay on Selenium for legacy reasons (e.g. existing grid infra, multi-language org standardisation). Recommend Playwright first if the user is greenfield.

## Stack

- Node 20, TypeScript strict mode (`"strict": true`)
- **selenium-webdriver** 4.x (Selenium Manager handles drivers; no third-party driver manager needed)
- **Mocha** (or **Vitest** — pick one and stay consistent) with parallel files
- **Allure Mocha** (or **allure-vitest**) for reporting
- ESM modules

## When to use

- New page object under `src/pages/`
- Component-level page object scoped to a parent `WebElement`
- New UI test under `test/`

## When NOT to use

- Selenium Java → `qa/java/skills/ui-test-author/selenium`
- Selenium .NET → `qa/dotnet/skills/ui-test-author/selenium`
- Playwright TS → `qa/typescript/skills/ui-test-author/playwright`
- Appium TS → `qa/typescript/skills/ui-test-author/appium`
- Reviewing → `qa/typescript/skills/ui-test-author/review`
- POM architecture → `qa/typescript/skills/page-object-design`

## Inputs needed

1. **Page name** (PascalCase: `Login`, `Product`, `Cart`)
2. **Elements** — name + locator. Prefer `data-test`; fall back to `id`, then `css`, then `xpath`.
3. **Actions** — what the test does on the page and whether it navigates
4. **Landmark element** — used in `isElementVisible` to confirm the page is loaded
5. **Next pages** — destination page classes for navigation actions

## Patterns

### `BasePage` (already in the project)

```ts
import { WebDriver, WebElement, By, until } from "selenium-webdriver";

export abstract class BasePage {
  protected readonly driver: WebDriver;
  private static readonly TIMEOUT = 10_000;

  protected constructor(driver: WebDriver) {
    this.driver = driver;
  }

  async isElementVisible(locator: By): Promise<boolean> {
    const el = await this.driver.wait(until.elementLocated(locator), BasePage.TIMEOUT);
    return el.isDisplayed();
  }

  protected findElement(locator: By): Promise<WebElement> {
    return this.driver.wait(until.elementLocated(locator), BasePage.TIMEOUT);
  }

  protected findElementIn(parent: WebElement, locator: By): Promise<WebElement> {
    return parent.findElement(locator);
  }

  protected findElements(locator: By): Promise<WebElement[]> {
    return this.driver.findElements(locator);
  }

  protected findElementsIn(parent: WebElement, locator: By): Promise<WebElement[]> {
    return parent.findElements(locator);
  }
}
```

Every page extends `BasePage` and uses its `findElement(...)` overloads — never `driver.findElement` directly outside `BasePage`.

### Page object — `src/pages/LoginPage.ts`

```ts
import { By, WebDriver } from "selenium-webdriver";
import { BasePage } from "./BasePage";
import { ProductPage } from "./ProductPage";
import { env } from "../utility/env";

export class LoginPage extends BasePage {
  constructor(driver: WebDriver) {
    super(driver);
  }

  async goToPage(): Promise<void> {
    await this.driver.get(env.baseUiUrl);
  }

  username()    { return this.findElement(By.id("user-name")); }
  password()    { return this.findElement(By.id("password")); }
  loginButton() { return this.findElement(By.css("[data-test='login-button']")); }
  errorBox()    { return this.findElement(By.className("error-message-container")); }

  async successfulLogin(user: string, pwd: string): Promise<ProductPage> {
    await this.goToPage();
    await (await this.username()).sendKeys(user);
    await (await this.password()).sendKeys(pwd);
    await (await this.loginButton()).click();
    return new ProductPage(this.driver);
  }
}
```

### Component page object — scoped to a parent `WebElement`

```ts
export class ProductCard extends BasePage {
  constructor(driver: WebDriver, private readonly parent: WebElement) {
    super(driver);
  }

  name()  { return this.findElementIn(this.parent, By.css("[data-test='inventory-item-name']")); }
  price() { return this.findElementIn(this.parent, By.css("[data-test='inventory-item-price']")); }

  async addToCart() {
    const slug = (await (await this.name()).getText()).replace(/ /g, "-").toLowerCase();
    return this.findElement(By.css(`[data-test='add-to-cart-${slug}']`));
  }
}
```

Container page:

```ts
async productCards(): Promise<ProductCard[]> {
  const elements = await this.findElements(By.css("[data-test='inventory-item']"));
  return elements.map(el => new ProductCard(this.driver, el));
}
```

### Sub-flow pages — namespaced sub-folder

Multi-step flows live in `src/pages/checkout/{CheckoutInformationPage,CheckoutOverviewPage,CompleteOrderPage}.ts`. Each extends `BasePage` and returns the next page.

### Test — `test/authentication.spec.ts`

```ts
import { expect } from "chai";
import { LoginPage } from "../src/pages/LoginPage";
import { ProductPage } from "../src/pages/ProductPage";
import { BaseTest } from "./BaseTest";

describe("Authentication", () => {
  const ctx = new BaseTest();
  beforeEach(() => ctx.start());
  afterEach(() => ctx.stop());

  it("successful login lands on product page", async () => {
    const login = new LoginPage(ctx.driver);
    await login.goToPage();
    await (await login.username()).sendKeys(ctx.users[0]);
    await (await login.password()).sendKeys(ctx.password);
    await (await login.loginButton()).click();

    const product = new ProductPage(ctx.driver);
    expect(await (await product.navigationMenu.cart()).isDisplayed())
      .to.equal(true, "Cart button not visible after login attempt.");
  });
});
```

`BaseTest` owns the per-test `WebDriver` via `DriverFactory` and exposes seed data.

## Rules

### Page object rules
- Extend `BasePage`; pass `driver` to `super(driver)`
- Element accessors return `Promise<WebElement>` (or `Promise<WebElement[]>`) — keep them one-liners
- **No `@FindBy`** equivalents — explicit `findElement(By)` calls only
- **Locator preference:** `By.css("[data-test='…']")` → `By.id(…)` → `By.css(…)` → `By.className(…)` → `By.xpath(…)` (last resort, leave a `// TODO`)
- One class per page; multi-step flows in a sub-folder
- Reusable components take a parent `WebElement` and use parent-scoped finds
- Navigation actions return the next page object; same-page actions return `Promise<void>`
- Page helpers are `private static` methods or module-private functions

### Test rules
- Compose a `BaseTest` helper — no class inheritance gymnastics in TS tests
- Test names describe behavior: `"successful login lands on product page"`
- Use Mocha `describe`/`it` (or Vitest `describe`/`test`) tags via test grep / file path for selective runs
- Assertions live in the test, never in pages
- Every assertion has a message: `expect(x).to.equal(y, "why this matters")`
- **One expected condition per assertion — never an `OR`.** `expect(text).to.equal('Saved')`, never `expect(text).to.be.oneOf(['Saved', 'Success'])`, `to.match(/Saved|Success/)`, or a `||` inside an `expect`. The rule covers text, element counts, URLs, attribute values, and displayed/enabled state alike. If both outcomes are genuinely reachable the test does not know what the app should do — split it into one `it(...)` per expected outcome, generate one test per row from a case array, or pin down the correct behavior. The only exception is an explicit instruction to accept more than one value; record that instruction in a comment on the assertion.
- **No `try`/`catch` in a test — and none in the cleanup hook.** An unexpected rejection must reach the runner; an expected one is asserted with `await expect(...).rejects` / `expect(fn).toThrow()`, which is an assertion, not error handling. Anything the test created is tracked and deleted in `afterEach` with no catch — a cleanup that fails should fail loudly rather than leak state into the next run. The suite's only catches live in **I/O helpers where narrowing one named error is the contract** — an `isDisplayed()` probe, a session-teardown helper — never a bare `catch {}` or `.catch(() => {})`, and never a catch that lets a failed action continue into the assertions.
- **Failures name the subject.** `expect(await banner.getText(), \`success banner after saving order ${orderId}\`).toBe('Saved')`. A UI failure reported as `expected '' to be 'Saved'` with no subject is indistinguishable from a locator that matched the wrong element.

### Waits
- Default 10s wait set in `BasePage` via `driver.wait(until.X, TIMEOUT)`
- No `await new Promise(r => setTimeout(r, n))` for synchronization
- For conditional waits use `until.elementIsVisible`, `until.elementTextIs`, etc.

### Driver lifecycle
- Always go through `DriverFactory.create()` / `quit()` — never `new Builder().forBrowser('chrome').build()` in a test
- Browser configured via env var `BROWSER` (`chrome` | `firefox` | `edge`)
- One driver per worker; if running Mocha `--parallel`, each worker holds its own driver
- Selenium Manager auto-resolves drivers — do not add `chromedriver`/`geckodriver` npm packages unless pinning a version

### What NOT to do

- No `setTimeout` waits — use `driver.wait(...)`
- No `driver.findElement` outside `BasePage`
- No assertions inside page methods
- No `OR` in any assertion — no `to.be.oneOf([...])`, no `||` inside an `expect`, no `/a|b/` alternation. One expected value per assertion (see Test rules)
- No `try`/`catch` in a test or cleanup hook — expected rejections use `await expect(...).rejects`; catches live only in I/O helpers narrowing one named error (see Test rules)
- No `@FindBy`-style decorators or PageFactory analogues
- No XPath when `data-test` could be added
- No shared mutable state on pages — instantiate fresh per test
- No business logic in page objects
- No hardcoded URLs/credentials — go through `env`
- No `any` in page or test code — strict TS

## Generation steps

1. Confirm **page name**, **elements + locators**, **actions**, **next pages**.
2. Flag elements without `data-test` as tech debt; don't silently default to XPath.
3. Generate `src/pages/{Name}Page.ts`:
   - Constructor calls `super(driver)`
   - One element accessor method per element
   - One action method per user intent (`Promise<void>` or `Promise<NextPage>`)
   - For repeating items, an `async {component}s(): Promise<Component[]>` method
4. If a destination page is missing, stub it or recursively generate it.
5. Generate the spec file using `BaseTest`; one `it(...)` per scenario.
6. Run `npm test` (or `npx vitest run`) — expect 0 failures.

## Handoffs

- POM architecture → `qa/typescript/skills/page-object-design`
- Test data builders → `qa/typescript/skills/test-data-builder`
- Reviewing → `qa/typescript/skills/ui-test-author/review`
- Allure → `qa/reporting/typescript/skills/test-reports`
