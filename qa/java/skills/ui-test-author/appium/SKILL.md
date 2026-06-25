---
name: qa-ui-test-author-appium-java
description: Use when the user asks to scaffold a Java + Appium 2.x page object or TestNG mobile UI test, following the BasePage / DriverFactory / TestNG pattern. Triggers: "create an Appium page object for X in Java", "add a Java mobile page for screen Y", "write an Appium TestNG test for Z".
---

# QA — Appium Java Page Object & Test Generator

Scaffolds Appium 2.x page objects and TestNG mobile UI tests in Java, mirroring the .NET and TypeScript siblings. Uses a thin `BaseAppiumPage` with `WebDriverWait`, accessibility-id-first locators, typed return values for navigation, and an `AppiumDriverFactory` that produces one `AppiumDriver` per thread for parallel-safe runs.

## Stack

- Java 21
- Gradle (Kotlin DSL — `build.gradle.kts`)
- **Appium Java client** 9.x (`io.appium:java-client`) on top of Selenium 4
- **Appium server** 2.x (started locally or hit via Selenium Grid / cloud provider)
- **TestNG** for tests (the global default for Java test runners)
- **Allure TestNG** for reporting
- `AndroidDriver` / `IOSDriver` selected by capability profile

## When to use

- New page object under `src/main/java/pom/mobile/`
- Component-level page object scoped to a parent `WebElement` (list item, card, sheet)
- New TestNG mobile UI test under `src/test/java/`

## When NOT to use

- Appium .NET → `qa/dotnet/skills/ui-test-author/appium`
- Appium TypeScript / WebdriverIO → `qa/typescript/skills/ui-test-author/appium`
- Selenium / web → `qa/java/skills/ui-test-author/selenium` or `qa/java/skills/ui-test-author/playwright`
- Reviewing an existing page object → `qa/java/skills/ui-test-author/reviewer`
- Designing the whole POM architecture → `qa/java/skills/page-object-architect`

## Inputs needed

1. **Screen name** (PascalCase, e.g. `Login`, `Home`, `OrderConfirmation`)
2. **Platform** — Android, iOS, or both (decides locator strategies allowed)
3. **Elements** — for each: name + `accessibility id` (preferred), platform id, predicate / UIAutomator selector, or XPath (last resort)
4. **Actions** — what the test will do, and whether each navigates to a different screen
5. **Landmark element** — the one element that proves the page is currently visible (used in `verifyPageLoaded`)
6. **Next pages** — destination page class names for navigation actions

## Patterns

### `BaseAppiumPage` (already in the project)

```java
package pom.mobile;

import io.appium.java_client.AppiumDriver;
import io.appium.java_client.AppiumBy;
import org.openqa.selenium.By;
import org.openqa.selenium.WebElement;
import org.openqa.selenium.support.ui.ExpectedConditions;
import org.openqa.selenium.support.ui.WebDriverWait;

import java.time.Duration;
import java.util.List;

public abstract class BaseAppiumPage {
    protected final AppiumDriver driver;
    private final WebDriverWait wait;

    protected BaseAppiumPage(AppiumDriver driver) {
        this.driver = driver;
        this.wait = new WebDriverWait(driver, Duration.ofSeconds(10));
    }

    public boolean isElementVisible(By locator) {
        return wait.until(ExpectedConditions.visibilityOfElementLocated(locator)).isDisplayed();
    }

    protected WebElement findByAccessibilityId(String id) {
        return wait.until(ExpectedConditions.presenceOfElementLocated(AppiumBy.accessibilityId(id)));
    }

    protected WebElement findById(String id) {
        return wait.until(ExpectedConditions.presenceOfElementLocated(By.id(id)));
    }

    protected WebElement findByXPath(String xpath) {
        return wait.until(ExpectedConditions.presenceOfElementLocated(By.xpath(xpath)));
    }

    protected List<WebElement> findAllByAccessibilityId(String id) {
        return driver.findElements(AppiumBy.accessibilityId(id));
    }
}
```

Every page extends `BaseAppiumPage` and goes through the inherited finders — never `driver.findElement(...)` directly.

### Page object — `src/main/java/pom/mobile/{Name}Page.java`

```java
package pom.mobile;

import io.appium.java_client.AppiumDriver;
import org.openqa.selenium.WebElement;
import org.testng.Assert;

public class LoginPage extends BaseAppiumPage {

    private static final String EMAIL_FIELD_ID   = "login-email";
    private static final String PASSWORD_FIELD_ID = "login-password";
    private static final String SUBMIT_BUTTON_ID = "login-submit";

    public LoginPage(AppiumDriver driver) {
        super(driver);
    }

    public void verifyPageLoaded() {
        WebElement email = findByAccessibilityId(EMAIL_FIELD_ID);
        Assert.assertTrue(email.isDisplayed(),
            "Expected LoginPage to be visible but the email field was not found.");
    }

    public HomePage login(String email, String password) {
        WebElement emailField = findByAccessibilityId(EMAIL_FIELD_ID);
        emailField.clear();
        emailField.sendKeys(email);

        WebElement pwdField = findByAccessibilityId(PASSWORD_FIELD_ID);
        pwdField.clear();
        pwdField.sendKeys(password);

        findByAccessibilityId(SUBMIT_BUTTON_ID).click();
        return new HomePage(driver);
    }
}
```

### Component page object — scoped to a parent `WebElement`

For repeating elements (list rows, cards, swipeable cells), create a component class that takes the parent `WebElement` in its constructor and queries inside it.

```java
public class OrderRow extends BaseAppiumPage {
    private final WebElement parent;

    public OrderRow(AppiumDriver driver, WebElement parent) {
        super(driver);
        this.parent = parent;
    }

    public WebElement title()  { return parent.findElement(AppiumBy.accessibilityId("order-title")); }
    public WebElement amount() { return parent.findElement(AppiumBy.accessibilityId("order-amount")); }

    public OrderDetailsPage open() {
        parent.click();
        return new OrderDetailsPage(driver);
    }
}
```

The container page exposes a `List<OrderRow>`:

```java
public List<OrderRow> orderRows() {
    return findAllByAccessibilityId("order-row").stream()
        .map(el -> new OrderRow(driver, el))
        .toList();
}
```

### Sub-flow pages — namespaced sub-package

Multi-step flows (onboarding, checkout) live under `pom/mobile/onboarding/{WelcomePage,ConsentPage,ProfilePage}.java`. Each extends `BaseAppiumPage` and returns the next step's page object.

### Test — `src/test/java/{Name}Test.java`

```java
import io.appium.java_client.AppiumDriver;
import io.qameta.allure.Story;
import org.testng.Assert;
import org.testng.annotations.Test;
import pom.mobile.HomePage;
import pom.mobile.LoginPage;

public class AuthenticationTest extends BaseMobileTest {

    @Test(groups = "Smoke")
    @Story("Successful login from cold start")
    public void successfulLoginLandsOnHome() {
        LoginPage login = new LoginPage(driver);
        login.verifyPageLoaded();
        HomePage home = login.login(users.getFirst(), password);

        home.verifyPageLoaded();
        Assert.assertTrue(home.profileAvatar().isDisplayed(),
            "Profile avatar not visible after login.");
    }
}
```

`BaseMobileTest` owns the per-thread `AppiumDriver` via `AppiumDriverFactory` (one `ThreadLocal<AppiumDriver>` per test thread), `@BeforeMethod` to start, `@AfterMethod` to quit. Capabilities (platform name, device name, app path) are loaded from `system.properties` or `-D` flags.

## Rules

### Page object rules
- Always extend `BaseAppiumPage`; pass `driver` to `super(driver)`
- Element accessors return `WebElement` (or `List<WebElement>`) — keep them one-liners
- **Locator preference order**: `AppiumBy.accessibilityId` → `By.id` (resource-id) → `AppiumBy.androidUIAutomator` (Android) / `AppiumBy.iOSNsPredicateString` · `AppiumBy.iOSClassChain` (iOS) → `By.xpath` (last resort, leave a `// TODO`). Per the Appium team, treat a working XPath as proof the node exists, **not** the final locator — downgrade to a native strategy once the source exposes one. On iOS, `id` / `name` / `accessibility id` are synonyms over the element's `name` attribute.
- **Locator constants** — declare each as `private static final String {ELEMENT}_ID` at the top of the class. Never inline a locator string inside an action method.
- One class per screen; multi-step flows live in a sub-package
- Reusable components take a parent `WebElement` and query inside it
- Navigation methods return the next page object; same-screen actions return `void`
- **Every page object must include a `verifyPageLoaded()` method** that asserts the landmark element is displayed
- Method naming describes user intent (`login`, `tapPrimaryAction`, `enterEmail`), not Appium mechanics

### Test rules
- Extend `BaseMobileTest` — it provides the per-test `AppiumDriver driver` and any shared `@BeforeSuite` seed data
- Test method names describe behavior: `successfulLoginLandsOnHome`, `lockedUserSeesErrorBanner`
- Use `@Test(groups = "Smoke" | "Regression" | ...)` to enable selective runs
- Assertions live in the test class, **never** inside page methods (except the `verifyPageLoaded()` landmark assertion)
- Use TestNG `Assert.assertTrue` / `assertEquals` with a message argument
- Use `SoftAssert` when verifying multiple fields after one user action; call `soft.assertAll()` at the end

### Waits
- Default 10s `WebDriverWait` baked into `BaseAppiumPage`
- Appium's element-finding timeout handles initial element resolution; for conditional waits use the inherited `isElementVisible(By)` or write a typed `ExpectedConditions`
- **No `Thread.sleep`** anywhere — including for screen transitions or animations

### Driver lifecycle
- Always go through `AppiumDriverFactory.setDriver()` / `getDriver()` / `quitDriver()` — never instantiate `AndroidDriver` / `IOSDriver` in a test
- Platform selected by `-Dplatform=android|ios`; capability profiles loaded from `src/test/resources/capabilities/`
- One driver per test thread (`ThreadLocal`) — safe for parallel TestNG runs
- The Appium server URL is configured via `SystemPropertyUtil.getAppiumServerUrl()` — never hardcoded

### What NOT to do

- No `Thread.sleep` — use `WebDriverWait` / `ExpectedConditions`
- No `driver.findElement(...)` outside `BaseAppiumPage`
- No raw `IWebElement` / `RemoteWebElement` returns — `WebElement` is the contract
- No locator strings inline in actions — promote to a `private static final String`
- No assertions inside actions — assertions live in `verifyPageLoaded()` and in test methods, never inside `tap*` / `enter*` actions
- No multi-screen page objects — one class per screen. If the screen has tabs/sheets, model each as its own component or sub-page.
- No business logic / API calls inside a page object — page objects model the screen, not the workflow
- No hardcoded device names, app paths, or server URLs — use `SystemPropertyUtil`
- No `PageFactory` / `@FindBy` / `@AndroidFindBy` — explicit `findByAccessibilityId(...)` calls only, so the locator is visible in the method body

## Generation steps

1. Confirm the **screen name**, **platform(s)**, **landmark element**, and the list of **elements + actions** with the user.
2. For every element: capture the `accessibility id` (preferred) or platform resource-id. Flag any element that has neither — those become predicate / XPath locators with a `// TODO` to replace once the app exposes a stable `testID`.
3. For every action that navigates: confirm the **destination page** class name (and stub it if it doesn't exist).
4. Generate `src/main/java/pom/mobile/{ScreenName}Page.java`:
   - Add one `private static final String` per element
   - Constructor passes `driver` to `super(driver)`
   - `verifyPageLoaded()` asserts the landmark element is displayed
   - One action method per user-intent action, returning `void` or the destination `*Page` type
   - One query method per piece of data the test needs to read
5. If a destination page doesn't exist yet, create a stub or recursively generate it.
6. Generate the test class extending `BaseMobileTest`; one `@Test` per scenario, with assertions on user-visible outcomes.
7. Run `./gradlew test -Dplatform=android` (or `ios`) — expect 0 failures. If the Appium server isn't reachable, check `SystemPropertyUtil.getAppiumServerUrl()`, that `appium server` is running (`curl -s http://127.0.0.1:4723/status` succeeds), and that the server log's `Available drivers:` line lists your driver (`uiautomator2` / `xcuitest`).

> **A test that can't find a visible element is usually not a locator bug.** Per the Appium team, an element absent from page source is most often an accessibility, app-state, active-app (system alert/overlay), or native-vs-WebView context problem — fix that before rewriting the selector. For environment/doctor failures and driver-specific locator questions, the `@appium/mcp-documentation` server (`appium_skills`, `appium_documentation_query`) answers authoritatively; prefer it over community forums.

## Handoffs

- Architecting the POM structure (sub-packages, base classes, capabilities) → `qa/java/skills/page-object-architect`
- Test data builders → `qa/java/skills/test-data-builder`
- Reviewing a page object → `qa/java/skills/ui-test-author/reviewer`
- Allure reporting → `qa/reporting/java/skills/allure-reporting`
