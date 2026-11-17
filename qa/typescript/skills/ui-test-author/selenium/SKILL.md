---
name: ui-tests-selenium
description: Use when scaffolding a TypeScript Selenium 4 page object or Mocha/Vitest UI test (BasePage pattern). Triggers "create a Selenium page object for X". Not for Playwright projects (ui-tests-playwright).
---

# QA — Selenium TypeScript Page Object & Test Generator

Scaffolds Selenium 4 page objects and Mocha (or Vitest) UI tests in TypeScript strict mode, mirroring the Java and .NET siblings. Uses a thin `BasePage` with explicit waits, private `By` constants behind intent methods and value queries, components built from a root locator, and a `DriverFactory` that produces one driver per worker for parallel-safe runs.

> Most TypeScript shops doing UI tests pick Playwright over Selenium. This skill exists for parity and for projects that must stay on Selenium for legacy reasons (e.g. existing grid infra, multi-language org standardisation). Recommend Playwright first if the user is greenfield.

## Stack

- Node 24, TypeScript strict mode (`"strict": true`)
- **selenium-webdriver** 4.x (Selenium Manager handles drivers; no third-party driver manager needed)
- **Mocha** (or **Vitest** — pick one and stay consistent) with parallel files
- **Allure Mocha** (or **allure-vitest**) for reporting
- ESM modules

## When to use

- New page object under `src/pages/`
- A region component (a card, a row) or a control component (a dropdown, a date picker) under `src/components/controls/`
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
4. **Landmark element** — waited for in `verifyPageLoaded` to confirm the page is loaded
5. **Next pages** — destination page classes for navigation actions

## Patterns

Locators are `private static readonly` `By` constants; nothing outside the class sees an element. Actions are
intent methods that return `Promise<void>` or the next page; queries return a value (text, a boolean, a count).
Every method is one user action, top to bottom.

### `BasePage` (already in the project)

```ts
import { By, until, WebDriver, WebElement } from "selenium-webdriver";

export abstract class BasePage {
  protected static readonly TIMEOUT_MS = 10_000;
  private static readonly PROGRESS_BAR = By.css("[data-testid='App.ProgressBar']");

  protected constructor(protected readonly driver: WebDriver) {}

  protected find(locator: By): Promise<WebElement> {
    return this.driver.wait(until.elementLocated(locator), BasePage.TIMEOUT_MS, `${locator} was not located`);
  }

  protected async waitForVisible(locator: By, name: string): Promise<void> {
    await this.driver.wait(until.elementIsVisible(await this.find(locator)), BasePage.TIMEOUT_MS, `${name} was not visible`);
  }

  protected async waitUntilIdle(): Promise<void> {
    const cleared = async () => (await this.driver.findElements(BasePage.PROGRESS_BAR)).length === 0;
    await this.driver.wait(cleared, BasePage.TIMEOUT_MS, "the app progress bar did not clear");
  }

  abstract verifyPageLoaded(): Promise<void>;
}
```

Every page extends `BasePage` and finds through `find(...)`, never `driver.findElement` directly. `waitUntilIdle()` is the app's own busy signal (its progress bar) as a named wait: the action that starts a load calls it before it returns, and a test never does. A snackbar or overlay the app raises gets the same treatment, one named wait each.

### Page object — `src/pages/LoginPage.ts`

```ts
import { By, WebDriver } from "selenium-webdriver";
import { env } from "../config/env.js";
import { BasePage } from "./BasePage.js";
import { ProductPage } from "./ProductPage.js";

export class LoginPage extends BasePage {
  private static readonly USERNAME = By.css("[data-test='username']");
  private static readonly PASSWORD = By.css("[data-test='password']");
  private static readonly SUBMIT = By.css("[data-test='login-button']");
  private static readonly ERROR = By.css("[data-test='error']");

  constructor(driver: WebDriver) {
    super(driver);
  }

  async goto(): Promise<void> {
    await this.driver.get(env.baseUiUrl);
  }

  async verifyPageLoaded(): Promise<void> {
    await this.waitForVisible(LoginPage.SUBMIT, "LoginPage sign-in button");
  }

  async signIn(user: string, password: string): Promise<ProductPage> {
    await (await this.find(LoginPage.USERNAME)).sendKeys(user);
    await (await this.find(LoginPage.PASSWORD)).sendKeys(password);
    await (await this.find(LoginPage.SUBMIT)).click();
    return new ProductPage(this.driver);
  }

  async errorText(): Promise<string> {
    return (await this.find(LoginPage.ERROR)).getText();
  }
}
```

`env` is the suite's config module (`src/config/env.ts`), failing fast on a missing variable.

### Control component — `src/components/controls/Dropdown.ts`

A design-system or native widget gets its own class at first use. It takes the driver and its root locator,
re-finds the root on each call, never extends `BasePage` and holds no assertion. A custom listbox is a second
class (`Combobox`), never a branch inside this one.

```ts
import { By, until, WebDriver } from "selenium-webdriver";
import { Select } from "selenium-webdriver/lib/select.js";

export class Dropdown {
  private static readonly TIMEOUT_MS = 10_000;

  constructor(
    private readonly driver: WebDriver,
    private readonly root: By,
  ) {}

  async select(option: string): Promise<void> {
    await (await this.control()).selectByVisibleText(option);
  }

  private async control(): Promise<Select> {
    return new Select(await this.driver.wait(until.elementLocated(this.root), Dropdown.TIMEOUT_MS, `${this.root} was not located`));
  }
}
```

### Region component — a row found by its content

A repeating card or row holds its key, never a `WebElement`, and finds its root again on every call through a
wait condition with a message, so a re-rendered list cannot go stale and a missing row fails with its key.

```ts
import { By, WebDriver, WebElement, WebElementCondition } from "selenium-webdriver";

export class ProductCard {
  private static readonly CARD = By.css("[data-test='inventory-item']");
  private static readonly NAME = By.css("[data-test='inventory-item-name']");
  private static readonly PRICE = By.css("[data-test='inventory-item-price']");
  private static readonly ADD_TO_CART = By.css("button[data-test^='add-to-cart']");
  private static readonly TIMEOUT_MS = 10_000;

  constructor(
    private readonly driver: WebDriver,
    private readonly productName: string,
  ) {}

  async price(): Promise<string> {
    return (await (await this.root()).findElement(ProductCard.PRICE)).getText();
  }

  async addToCart(): Promise<void> {
    await (await (await this.root()).findElement(ProductCard.ADD_TO_CART)).click();
  }

  private root(): Promise<WebElement> {
    const shown = new WebElementCondition(`for a product card showing ${this.productName}`, () => this.matchingCard());
    return this.driver.wait(shown, ProductCard.TIMEOUT_MS);
  }

  private async matchingCard(): Promise<WebElement | null> {
    const cards = await this.driver.findElements(ProductCard.CARD);
    const names = await Promise.all(cards.map(async (card) => (await card.findElement(ProductCard.NAME)).getText()));
    return cards[names.indexOf(this.productName)] ?? null;
  }
}
```

To check every row of a result, the page exposes a query returning one column's values (`productPrices(): Promise<string[]>`); the test asserts the array is not empty, then asserts on the whole array in one `expect`, never on `[0]` standing for the result set. Where the app's ids embed the row index, the component finds the index from the row's content; a test never passes one.

The page exposes both kinds as intent:

```ts
import { By, WebDriver } from "selenium-webdriver";
import { Dropdown } from "../components/controls/Dropdown.js";
import { BasePage } from "./BasePage.js";
import { ProductCard } from "./ProductCard.js";

export class ProductPage extends BasePage {
  private static readonly TITLE = By.css("[data-test='title']");
  private static readonly SORT = By.css("[data-test='product-sort-container']");
  private static readonly PRODUCT_NAME = By.css("[data-test='inventory-item-name']");

  readonly sort: Dropdown;

  constructor(driver: WebDriver) {
    super(driver);
    this.sort = new Dropdown(driver, ProductPage.SORT);
  }

  async verifyPageLoaded(): Promise<void> {
    await this.waitForVisible(ProductPage.TITLE, "ProductPage title");
  }

  card(productName: string): ProductCard {
    return new ProductCard(this.driver, productName);
  }

  async firstProductName(): Promise<string> {
    return (await this.find(ProductPage.PRODUCT_NAME)).getText();
  }
}
```

### Multi-step pages

Multi-step journeys live in `src/pages/checkout/{CheckoutInformationPage,CheckoutOverviewPage,CompleteOrderPage}.ts`. Each extends `BasePage` and returns the next page. A sequence a test's setup repeats is a `CheckoutFlow` class that takes these pages in its constructor.

### Test — `test/products.spec.ts`

Reaching the screen happens in `beforeEach`; the body is the action and its assertion, with no branch, loop or
`try`, and no private function on the spec.

```ts
import { expect } from "chai";
import type { WebDriver } from "selenium-webdriver";
import { env } from "../src/config/env.js";
import { LoginPage } from "../src/pages/LoginPage.js";
import type { ProductPage } from "../src/pages/ProductPage.js";
import { DriverFactory } from "./DriverFactory.js";

describe("Products", () => {
  let driver: WebDriver;
  let products: ProductPage;

  beforeEach(async () => {
    driver = await DriverFactory.create();
    const login = new LoginPage(driver);
    await login.goto();
    await login.verifyPageLoaded();
    products = await login.signIn(env.user, env.password);
    await products.verifyPageLoaded();
  });

  afterEach(async () => {
    await driver.quit();
  });

  it("Should_ListCheapestProductFirst_When_SortedByPriceLowToHigh", async () => {
    await products.sort.select("Price (low to high)");

    expect(await products.firstProductName(), "first product after sorting").to.equal("Sauce Labs Onesie");
  });

  it("Should_ShowPrice_When_ProductIsListed", async () => {
    const price = await products.card("Sauce Labs Backpack").price();

    expect(price, "Sauce Labs Backpack price").to.equal("$29.99");
  });
});
```

## Driver lifecycle
- Always go through `DriverFactory.create()` in `beforeEach` and `driver.quit()` in `afterEach` — never `new Builder().forBrowser('chrome').build()` in a test
- Browser configured via env var `BROWSER` (`chrome` | `firefox` | `edge`)
- One driver per worker; if running Mocha `--parallel`, each worker holds its own driver
- Selenium Manager auto-resolves drivers — do not add `chromedriver`/`geckodriver` npm packages unless pinning a version

## Rules

The standards this skill's output must meet are the qa-typescript rule files, not a list here: `qa-typescript.md`, `page-objects.md`, `ui-tests.md` and `test-data.md`. Read the project's copy in `.claude/rules/qa-typescript/`, or the plugin's in `qa/typescript/skills/rules/` when the project has not installed them (`/qa-typescript:rules` does). Where they and this skill's recipes disagree, the rule files win.

## Generation steps

1. Confirm **page name**, **elements + locators**, **actions**, **next pages**.
2. Record each element without a test id in `missing-testids.md`; don't silently default to XPath.
3. For each widget (select, date picker, combobox, grid), reuse the class in `src/components/controls/` or write one at first use.
4. Generate `src/pages/{Name}Page.ts`:
   - Constructor calls `super(driver)` and builds its control fields
   - One `private static readonly` `By` constant per element; no public element accessor
   - One action method per user intent (`Promise<void>` or `Promise<NextPage>`), named for the action (`signIn`), never the outcome
   - Value queries for what tests assert (`errorText()`, `firstProductName()`)
   - For repeating items, a `{component}(key)` method returning a region component found by its content
5. If a destination page is missing, stub it or recursively generate it.
6. Generate the spec file: driver and screen reached in `beforeEach`, one `it(...)` per scenario named `Should_X_When_Y`.
7. Run the project's own test script with the package manager `packageManager` names — expect 0 failures.

## Handoffs

- POM architecture → `qa/typescript/skills/page-object-design`
- Test data builders → `qa/typescript/skills/test-data-builder`
- Reviewing → `qa/typescript/skills/ui-test-author/review`
- Allure → `qa/reporting/typescript/skills/test-reports`
