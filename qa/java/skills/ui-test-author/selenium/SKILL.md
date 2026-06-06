---
name: qa-ui-test-author-selenium-java
description: Use when the user asks to scaffold a Java + Selenium 4 page object or TestNG UI test, following the BasePage / DriverFactory / TestNG pattern. Triggers: "create a Selenium page object for X", "add a Java page for screen Y", "write a Selenium UI test for Z". Do NOT use for Selenium .NET (use `qa/dotnet/skills/ui-test-author/selenium`), Selenium TypeScript (use `qa/typescript/skills/ui-test-author/selenium`), Playwright (use `qa/java/skills/ui-test-author/playwright`), Appium / mobile (use `qa/java/skills/ui-test-author/appium`), or Accelerator tests (use `qa/manual/accelerator-conventions`).
---

# QA — Selenium Java Page Object & Test Generator

Scaffolds Selenium 4 page objects and TestNG UI tests in Java, modeled on [`akotrulev/EndavaUi`](https://github.com/akotrulev/EndavaUi). Uses a thin `BasePage` with `WebDriverWait`, element accessors that return raw `WebElement`, and a `DriverFactory` that manages a `ThreadLocal<WebDriver>` for parallel-safe runs.

## Stack

- Java 21
- Gradle
- **Selenium 4** (`org.seleniumhq.selenium:selenium-java`)
- **WebDriverManager** (`io.github.bonigarcia:webdrivermanager`) for browser driver setup
- **TestNG** for tests (the global default for Java test runners)
- **Allure TestNG** for reporting

## When to use

- New page object under `src/main/java/pom/`
- Component-level page object (e.g. a card inside a list) scoped to a parent `WebElement`
- New TestNG UI test under `src/test/java/`

## When NOT to use

- Playwright / Node / .NET → `qa/java/skills/ui-test-author/playwright`
- Appium mobile → `qa/java/skills/ui-test-author/appium`
- Accelerator-owned tests → `qa/manual/accelerator-conventions`
- Reviewing a page object → `qa/java/skills/ui-test-author/reviewer`
- Designing the whole POM architecture → `qa/java/skills/page-object-architect`

## Inputs needed

1. **Page name** (PascalCase, e.g. `Login`, `Product`, `Cart`)
2. **Elements** — for each: name + locator. Prefer `data-test` attributes; fall back to `id`, then `css`, then `xpath`.
3. **Actions** — what the test will do on the page and whether it navigates
4. **Landmark element** — used in `isElementVisible` to confirm the page is loaded
5. **Next pages** — for navigation actions, the destination page class

## Patterns

### `BasePage` (already in the project)

```java
public class BasePage {
    protected WebDriver driver;
    private WebDriverWait wait;

    public BasePage(WebDriver driver) {
        this.driver = driver;
        this.wait = new WebDriverWait(driver, Duration.ofSeconds(10));
    }

    public boolean isElementVisible(By locator) { /* ... */ }
    public WebElement findElement(By locator) { /* ... */ }
    public WebElement findElement(By locator, WebElement parent) { /* ... */ }
    public List<WebElement> findElements(By locator) { /* ... */ }
    public List<WebElement> findElements(By locator, WebElement parent) { /* ... */ }
}
```

Every page extends `BasePage` and uses its `findElement(...)` / `findElements(...)` overloads — never `driver.findElement` directly.

### Page object — `src/main/java/pom/{Name}Page.java`

```java
package pom;

import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.WebElement;
import utility.SystemPropertyUtil;

public class LoginPage extends BasePage {

    public LoginPage(WebDriver driver) {
        super(driver);
    }

    public void goToPage() {
        navigateToUrl(SystemPropertyUtil.getBaseUiUrl());
    }

    public WebElement username()    { return findElement(By.id("user-name")); }
    public WebElement password()    { return findElement(By.id("password")); }
    public WebElement loginButton() { return findElement(By.cssSelector("[data-test='login-button']")); }
    public WebElement errorBox()    { return findElement(By.className("error-message-container")); }

    public ProductPage successfulLogin(String user, String pwd) {
        goToPage();
        username().sendKeys(user);
        password().sendKeys(pwd);
        loginButton().click();
        return new ProductPage(driver);
    }
}
```

### Component page object — scoped to a parent `WebElement`

For repeating elements (cards, rows, list items), create a component class that takes the parent `WebElement` in its constructor and queries inside it.

```java
public class ProductCard extends BasePage {
    private final WebElement parent;

    public ProductCard(WebDriver driver, WebElement parent) {
        super(driver);
        this.parent = parent;
    }

    public WebElement name()  { return findElement(By.cssSelector("[data-test='inventory-item-name']"), parent); }
    public WebElement price() { return findElement(By.cssSelector("[data-test='inventory-item-price']"), parent); }
    public WebElement addToCart() {
        return findElement(By.cssSelector(String.format("[data-test='add-to-cart-%s']", toSlug(name().getText()))));
    }

    private static String toSlug(String s) { return s.replace(" ", "-").toLowerCase(); }
}
```

The container page exposes a `List<ProductCard>` built from the parent finds:

```java
public List<ProductCard> productCards() {
    List<ProductCard> cards = new ArrayList<>();
    findElements(By.cssSelector("[data-test='inventory-item']"))
        .forEach(el -> cards.add(new ProductCard(driver, el)));
    return cards;
}
```

### Sub-flow pages — namespaced sub-package

Multi-step flows (checkout, onboarding) live under a sub-package: `pom/checkout/CheckoutInformationPage.java`, `CheckoutOverviewPage.java`, `CompleteOrderPage.java`. Each step page extends `BasePage` and returns the next step's page object.

### Test — `src/test/java/{Name}Test.java`

```java
import org.testng.Assert;
import org.testng.annotations.Test;
import pom.LoginPage;
import pom.ProductPage;

public class AuthenticationTest extends BaseTest {

    @Test(groups = "Smoke")
    public void successfulLogin() {
        LoginPage loginPage = new LoginPage(driver);
        loginPage.goToPage();
        loginPage.username().sendKeys(users.getFirst());
        loginPage.password().sendKeys(password);
        loginPage.loginButton().click();

        ProductPage productPage = new ProductPage(driver);
        Assert.assertTrue(productPage.navigationMenu.cart().isDisplayed(),
            "Cart button not visible after login attempt.");
    }
}
```

`BaseTest` handles driver lifecycle via `DriverFactory` (one `ThreadLocal<WebDriver>` per thread), `@BeforeMethod` to start, `@AfterMethod` to quit, and `@BeforeSuite` to harvest seed data (default users/password) used across tests.

## Rules

### Page object rules
- Always extend `BasePage`; pass `driver` to `super(driver)`
- Element accessors return `WebElement` (or `List<WebElement>`) — keep them one-liners (`return findElement(By...)`)
- **No `@FindBy` / `PageFactory`** — the reference repo deliberately uses explicit `findElement(By)` calls so locators are visible in the method body
- **Locator preference order:** `data-test` attribute → `id` → `cssSelector` → `className` → `xpath` (last resort, add `// TODO` to replace)
- One class per page; multi-step flows live in a sub-package (e.g. `pom/checkout/`)
- Reusable components (cards, rows) take a parent `WebElement` and use `findElement(By, parent)` overloads
- Navigation methods (`successfulLogin`, `submitOrder`) return the next page object; same-page actions return `void`
- Page constants and helper formatters (e.g. `toSlug`) are `private static` and scoped to the page

### Test rules
- Extend `BaseTest` — it provides the per-test `WebDriver driver` and any shared `@BeforeSuite` seed data
- Test method names describe behavior: `successfulLogin`, `cartShowsAddedProduct`, `loginRejectsLockedUser`
- Use `@Test(groups = "Smoke" | "Regression" | ...)` to enable selective runs
- Assertions live in the test class, **never** inside page methods. Page methods return `WebElement` / next page; the test asserts.
- Use TestNG `Assert.assertTrue` / `assertEquals` with a message argument — every failure must explain itself
- Use `SoftAssert` when verifying multiple fields after one user action; call `soft.assertAll()` at the end

### Waits
- Default 10s implicit wait is set in `DriverFactory`
- For conditional / explicit waits use the inherited `WebDriverWait` via `isElementVisible(By)` or write a typed `ExpectedConditions` wait
- **No `Thread.sleep`** anywhere — including for page transitions

### Driver lifecycle
- Always go through `DriverFactory.setDriver()` / `getDriver()` / `quitDriver()` — never instantiate `ChromeDriver` directly in a test
- Browser type is configured via `SystemPropertyUtil.getBrowserType()` — pass `-Dbrowser=firefox` to switch
- One driver per test thread (`ThreadLocal`) — safe for parallel TestNG runs

### What NOT to do

- No `Thread.sleep` — use `WebDriverWait` / `ExpectedConditions`
- No `driver.findElement(...)` in a page object — go through `findElement(By)` so future changes (logging, retries) have one place to land
- No assertions inside page methods — page methods model the page, tests own the assertions
- No `@FindBy` annotations or `PageFactory.initElements` — explicit `findElement(By)` calls only
- No raw `xpath` when a `data-test` attribute exists — refactor the app to expose one rather than locking the test to brittle DOM structure
- No shared mutable state on page objects — every page is constructed fresh from the test
- No business logic in page objects (e.g. computing discounts) — model the screen, not the workflow
- No hardcoded URLs or credentials — use `SystemPropertyUtil`

## Generation steps

1. Confirm **page name**, **elements + locators**, **actions**, and **next pages** with the user.
2. For each element with no `data-test` attribute, flag whether it can be added to the app — note the technical debt rather than silently using XPath.
3. Generate `src/main/java/pom/{Name}Page.java`:
   - Constructor calls `super(driver)`
   - One element accessor method per element (one-line `findElement(...)`)
   - One action method per user-intent action (`void` or next-page return)
   - For repeating items, a `List<{Component}>` method that wraps each `WebElement` in a component class
4. If a destination page doesn't exist yet, create a stub or recursively generate it.
5. Generate the test class extending `BaseTest`; one `@Test` per scenario, with assertions on user-visible outcomes (not implementation details).
6. Run `./gradlew test` — expect 0 failures. If browser drivers fail to download, check the `WebDriverManager` version and `system.properties`.

## Handoffs

- Architecting the POM structure (sub-packages, base classes) → `qa/java/skills/page-object-architect`
- Test data builders → `qa/java/skills/test-data-builder`
- Reviewing a page object → `qa/java/skills/ui-test-author/reviewer`
- Allure reporting → `qa/java/skills/allure-reporting`
