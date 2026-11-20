---
name: ui-tests-selenium
description: Use when scaffolding a Java Selenium 4 page object or TestNG UI test (BasePage pattern). Triggers "create a Selenium page object for X". Not for Playwright projects (ui-tests-playwright).
disable-model-invocation: true
---

# QA — Selenium Java Page Object & Test Generator

Scaffolds Selenium 4 page objects, components and TestNG UI tests in Java, on the layout of [`akotrulev/EndavaUi`](https://github.com/akotrulev/EndavaUi) with its element accessors made private. A thin `BasePage` holds the driver, one `WebDriverWait` and the finders; pages expose intent and queries that return values, never a `WebElement`; components take their root element; and a `DriverFactory` manages a `ThreadLocal<WebDriver>` for parallel-safe runs.

## Stack

- Java 21
- Gradle
- **Selenium 4** (`org.seleniumhq.selenium:selenium-java`)
- **WebDriverManager** (`io.github.bonigarcia:webdrivermanager`) for browser driver setup
- **TestNG** for tests (the global default for Java test runners)
- **Allure TestNG** for reporting

## When to use

- New page object under `src/main/java/pom/`
- A region component (a card, a row) scoped to its root `WebElement`, or a control component (a dropdown, a date picker, a grid) under `pom/components/controls/`
- New TestNG UI test under `src/test/java/`

## When NOT to use

- Playwright / Node / .NET → `qa/java/skills/ui-test-author/playwright`
- Appium mobile → `qa/java/skills/ui-test-author/appium`
- A new project from zero → `qa/java/skills/ui-project-setup` (its Selenium lane)
- Reviewing a page object → `qa/java/skills/ui-test-author/review`
- Designing the whole POM architecture → `qa/java/skills/page-object-design`

## Inputs needed

1. **Page name** (PascalCase, e.g. `Login`, `Inventory`, `Cart`)
2. **Elements** — for each: name + locator. Prefer `data-test` attributes; fall back to `id`, then `css`, then `xpath`.
3. **Actions** — what the test will do on the page and whether it navigates
4. **Landmark element** — the one element `verifyPageLoaded()` waits for
5. **Next pages** — for navigation actions, the destination page class
6. **Widgets** — which elements are design-system controls (native `<select>`, date picker, grid)

## Patterns

### `BasePage`

```java
package pom;

import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.WebElement;
import org.openqa.selenium.support.ui.ExpectedConditions;
import org.openqa.selenium.support.ui.WebDriverWait;

import java.time.Duration;
import java.util.List;

public abstract class BasePage {
    private static final By LOADING_BAR = By.cssSelector("[data-test='loading-bar']");

    protected final WebDriver driver;
    private final WebDriverWait wait;

    protected BasePage(WebDriver driver) {
        this.driver = driver;
        this.wait = new WebDriverWait(driver, Duration.ofSeconds(10));
    }

    protected WebElement find(By locator) {
        return wait.until(ExpectedConditions.visibilityOfElementLocated(locator));
    }

    protected List<WebElement> findAll(By locator) {
        return wait.until(ExpectedConditions.presenceOfAllElementsLocatedBy(locator));
    }

    protected void waitForLandmark(By landmark) {
        wait.withMessage(getClass().getSimpleName() + " did not load: " + landmark + " is not visible")
                .until(ExpectedConditions.visibilityOfElementLocated(landmark));
    }

    protected void waitUntilLoadingBarGone() {
        wait.withMessage("The loading bar is still visible")
                .until(ExpectedConditions.invisibilityOfElementLocated(LOADING_BAR));
    }

    public abstract void verifyPageLoaded();
}
```

Every page extends `BasePage` and finds through `find` / `findAll`, never `driver.findElement` directly. A component does not extend it. `waitUntilLoadingBarGone()` is a named application wait: the page action that starts a load (a search, a filter) calls it before it returns, never the test.

### Page object — `src/main/java/pom/{Name}Page.java`

```java
package pom;

import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;

public final class LoginPage extends BasePage {
    private static final By USERNAME = By.cssSelector("[data-test='username']");
    private static final By PASSWORD = By.cssSelector("[data-test='password']");
    private static final By SUBMIT = By.cssSelector("[data-test='login-button']");
    private static final By ERROR = By.cssSelector("[data-test='error']");

    public LoginPage(WebDriver driver) {
        super(driver);
    }

    @Override
    public void verifyPageLoaded() {
        waitForLandmark(SUBMIT);
    }

    public void goTo() {
        driver.get(Env.required("BASE_URL") + "/");
    }

    public InventoryPage signIn(Credentials credentials) {
        find(USERNAME).sendKeys(credentials.username());
        find(PASSWORD).sendKeys(credentials.password());
        find(SUBMIT).click();
        return new InventoryPage(driver);
    }

    public String errorMessage() {
        return find(ERROR).getText();
    }

    public record Credentials(String username, String password) {
    }
}
```

`Env.required(name)` is the suite's config class: it reads an environment variable and fails naming it when it is missing (the Appium asset `Env.java` is the same class). `verifyPageLoaded()` is the page's one landmark check: a wait that fails naming the page and the locator.

### Region component — scoped to its root `WebElement`

A repeating card or row is a component that takes its root element and finds every child inside it. The page picks it by its content; the component never extends `BasePage`.

```java
package pom.components;

import org.openqa.selenium.By;
import org.openqa.selenium.WebElement;

public final class ProductCard {
    private static final By PRICE = By.cssSelector("[data-test='inventory-item-price']");
    private static final By ADD_TO_CART = By.cssSelector("button[data-test^='add-to-cart']");

    private final WebElement root;

    public ProductCard(WebElement root) {
        this.root = root;
    }

    public String price() {
        return root.findElement(PRICE).getText();
    }

    public void addToCart() {
        root.findElement(ADD_TO_CART).click();
    }
}
```

```java
public ProductCard product(String name) {
    return findAll(CARD).stream()
            .filter(card -> card.findElement(CARD_NAME).getText().equals(name))
            .findFirst()
            .map(ProductCard::new)
            .orElseThrow(() -> new IllegalStateException("No product card named " + name));
}
```

A list that re-renders between calls makes a held root stale; there, hold the row's key and re-find the root on every call, as the Appium `OrderRow` asset does.

To check every row of a result, the page or grid returns one column's values (`List<String> prices()`, mapped from `findAll`); the test asserts the list is not empty, then asserts on all of it with AssertJ `allSatisfy` / `allMatch`, never a loop in the test or the first row standing for the set. Where the app's ids embed the row index, the component resolves the index from the row's content; the test never passes one.

### Control component — a `Dropdown` over `Select`

A design-system widget is a control component at first use, in `pom/components/controls/`. A native `<select>` is `Dropdown`; a custom listbox is a second class (`Combobox`), never a branch inside this one.

```java
package pom.components.controls;

import org.openqa.selenium.WebElement;
import org.openqa.selenium.support.ui.Select;

public final class Dropdown {
    private final WebElement select;

    public Dropdown(WebElement select) {
        this.select = select;
    }

    public void choose(String optionText) {
        new Select(select).selectByVisibleText(optionText);
    }

    public String selectedOption() {
        return new Select(select).getFirstSelectedOption().getText();
    }
}
```

The page holds it and exposes intent: `public void sortBy(String order) { new Dropdown(find(SORT)).choose(order); }`. The Playwright control catalogue (`ui-test-author/playwright/references/components.md`) lists the other controls; a Selenium version keeps their intent methods and swaps the driver calls.

### Multi-step pages — namespaced sub-package

Multi-step journeys (checkout, onboarding) live under a sub-package: `pom/checkout/CheckoutInformationPage.java`, `CheckoutOverviewPage.java`, `CompleteOrderPage.java`. Each step returns the next step's page object. A sequence a test's setup needs across them is a `CheckoutFlow` class that takes those pages in its constructor.

### Test — `src/test/java/{Feature}Test.java`

```java
import org.testng.annotations.BeforeMethod;
import org.testng.annotations.Test;
import pom.Env;
import pom.InventoryPage;
import pom.LoginPage;
import pom.LoginPage.Credentials;

import static org.assertj.core.api.Assertions.assertThat;

public class LoginTest extends BaseTest {
    private LoginPage loginPage;
    private Credentials user;

    @BeforeMethod(alwaysRun = true)
    public void openLoginPage() {
        loginPage = new LoginPage(DriverFactory.getDriver());
        user = new Credentials(Env.required("E2E_USER"), Env.required("E2E_PASSWORD"));
        loginPage.goTo();
        loginPage.verifyPageLoaded();
    }

    @Test(groups = "smoke")
    public void Should_ShowProducts_When_CredentialsAreValid() {
        InventoryPage inventory = loginPage.signIn(user);

        assertThat(inventory.title()).as("inventory page title").isEqualTo("Products");
    }

    @Test(groups = "regression")
    public void Should_ShowCredentialsError_When_PasswordIsWrong() {
        loginPage.signIn(new Credentials(user.username(), user.password() + "-wrong"));

        assertThat(loginPage.errorMessage()).as("sign-in error")
                .isEqualTo("Epic sadface: Username and password do not match any user in this service");
    }
}
```

`BaseTest` owns the driver: `DriverFactory.setDriver()` in `@BeforeMethod(alwaysRun = true)`, `DriverFactory.quitDriver()` in `@AfterMethod(alwaysRun = true)`, one `ThreadLocal<WebDriver>` per test thread, and failure evidence. Records a test needs are created in its own `@BeforeMethod` and deleted in its `@AfterMethod`, never shared through `@BeforeSuite`.

## Rules

The standards this skill's output must meet are the qa-java rule files, not a list here: `qa-java.md` (core), `qa-java-ui.md` and `qa-java-page-objects.md`. Read the project's copy in `.claude/rules/qa-java/`, or the plugin's in `qa/java/skills/rules/` when the project has not installed them (`/qa-java:rules` does). Where they and this skill's recipes disagree, the rule files win.

## Conventions

- Pages extend `BasePage`, pass `driver` to `super(driver)`, and keep every locator a `private static final By`. Explicit `find(By)` calls through the base, never `@FindBy` / `PageFactory`.
- A page exposes intent (`signIn`, `sortBy`) and queries that return values (`errorMessage()`, `title()`, `product(name).price()`), never a `WebElement`. Navigation returns the next page.
- Region components (cards, rows) take their root `WebElement`; control components (`Dropdown`, a date picker, a grid) take the widget's root and live in `pom/components/controls/`. Neither extends `BasePage`.
- Tests extend `BaseTest`, build their pages and reach the screen under test in `@BeforeMethod(alwaysRun = true)`, and keep the body to the action and its outcome. Groups: `@Test(groups = "smoke" | "regression" | ...)`.
- Waits are the base's `WebDriverWait` with `ExpectedConditions`; a wait a page needs beyond `find` is a named method on that page, and the app's own busy signal (loading bar, snackbar) is a named wait on `BasePage`, called by the action that triggers it.
- The driver comes from `DriverFactory.setDriver()` / `getDriver()` / `quitDriver()`, one per test thread (`ThreadLocal`). The browser is `BROWSER` (default `chrome`), and URLs and credentials come from `Env`.

## Generation steps

1. Confirm **page name**, **elements + locators**, **actions**, **widgets** and **next pages** with the user.
2. For each element with no `data-test` attribute, add a `missing-testids.md` row and use the next rung; the code carries no marker.
3. For each widget, reuse the project's control in `pom/components/controls/` or add one (a `Dropdown` for a native `<select>`).
4. Generate `src/main/java/pom/{Name}Page.java`:
   - Constructor calls `super(driver)`; `verifyPageLoaded()` on the landmark
   - One `private static final By` per element
   - One intent method per user action (`void` or next-page return), one query per value a test reads
   - For repeating items, a method that returns the region component picked by its content
5. If a destination page doesn't exist yet, create a stub or recursively generate it.
6. Generate the test class extending `BaseTest`: setup in `@BeforeMethod(alwaysRun = true)`, one `@Test` per scenario with a `Should_X_When_Y` name, assertions on user-visible values.
7. Run `./gradlew test` — expect 0 failures. If browser drivers fail to download, check the `WebDriverManager` version and the `BROWSER` variable.

## Handoffs

- Architecting the POM structure (sub-packages, base classes) → `qa/java/skills/page-object-design`
- Test data builders → `qa/java/skills/test-data-builder`
- Reviewing a page object → `qa/java/skills/ui-test-author/review`
- Allure reporting → `qa/reporting/java/skills/test-reports`
