---
name: ui-tests-selenium
description: Use when scaffolding a TypeScript Selenium 4 page object or Mocha/Vitest UI test (BasePage pattern). Triggers "create a Selenium page object for X". Not for Playwright projects (ui-tests-playwright).
---

# QA — Selenium TypeScript Page Object & Test Generator

Scaffolds Selenium 4 page objects and Mocha (or Vitest) UI tests in TypeScript strict mode, mirroring the Java and .NET siblings. Uses a thin `BasePage` with explicit waits, element accessors that return `Promise<WebElement>`, and a `DriverFactory` that produces one driver per worker for parallel-safe runs.

> Most TypeScript shops doing UI tests pick Playwright over Selenium. This skill exists for parity and for projects that must stay on Selenium for legacy reasons (e.g. existing grid infra, multi-language org standardisation). Recommend Playwright first if the user is greenfield.

## Stack

- Node 24, TypeScript strict mode (`"strict": true`)
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
2. **Elements** — name + locator. Prefer the test-id attribute — `data-testid` by default; a project whose app ships `data-test` (as the SauceDemo samples below do) uses that attribute throughout — then `id`, then `css`, then `xpath`.
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

## Driver lifecycle
- Always go through `DriverFactory.create()` / `quit()` — never `new Builder().forBrowser('chrome').build()` in a test
- Browser configured via env var `BROWSER` (`chrome` | `firefox` | `edge`)
- One driver per worker; if running Mocha `--parallel`, each worker holds its own driver
- Selenium Manager auto-resolves drivers — do not add `chromedriver`/`geckodriver` npm packages unless pinning a version

## Rules

The standards this skill's output must meet are the qa-typescript rule files, not a list here: `qa-typescript.md` and `ui-tests.md`. Read the project's copy in `.claude/rules/qa-typescript/`, or the plugin's in `qa/typescript/skills/rules/` when the project has not installed them (`/qa-typescript:rules` does). Where they and this skill's recipes disagree, the rule files win.

## Generation steps

1. Confirm **page name**, **elements + locators**, **actions**, **next pages**.
2. Record each element without a test id in `missing-testids.md`; don't silently default to XPath.
3. Generate `src/pages/{Name}Page.ts`:
   - Constructor calls `super(driver)`
   - One element accessor method per element
   - One action method per user intent (`Promise<void>` or `Promise<NextPage>`)
   - For repeating items, an `async {component}s(): Promise<Component[]>` method
4. If a destination page is missing, stub it or recursively generate it.
5. Generate the spec file using `BaseTest`; one `it(...)` per scenario.
6. Run the project's own test script with the package manager `packageManager` names — expect 0 failures.

## Handoffs

- POM architecture → `qa/typescript/skills/page-object-design`
- Test data builders → `qa/typescript/skills/test-data-builder`
- Reviewing → `qa/typescript/skills/ui-test-author/review`
- Allure → `qa/reporting/typescript/skills/test-reports`
