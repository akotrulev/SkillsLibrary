---
name: mobile-screen-objects
description: Use when creating or updating a Java Appium page object from live-screen elements. Triggers "create a page object for the Login screen". Not for finding elements (mobile-screen-explorer).
disable-model-invocation: true
---

# QA — Appium Page Object Builder (Java)

Turns a discovered element inventory into a **Java Appium page object** — a `BaseAppiumPage` subclass under `src/main/java/pom/mobile/`. It consumes the element table + locator-ladder rungs from `qa/java/skills/mobile-screen-explorer` (or an inventory the user supplies directly) and emits/updates one screen class. This skill owns **codegen and the create/update diff** — the page-object *conventions* (base class, finder methods, `verifyPageLoaded`, naming, return types, waits) are owned by `qa/java/skills/ui-test-author/appium`; load it and follow it rather than re-deriving the rules here.

## Inputs needed

1. **Screen name** (PascalCase → `LoginPage`, `OrderConfirmationPage`)
2. **Element list** — per element: name, type, and the locator-ladder rung from `mobile-screen-explorer` (the test id first; a native query, then XPath, as the fallback)
3. **Landmark element** — the one element that proves the screen is visible (used by `verifyPageLoaded()`)
4. **Actions** — user-intent actions and, for each, whether it navigates to another screen (→ destination `*Page` class name)
5. **Target project** — repo path and existing `pom/mobile/` location/convention to match

## Conventions (owned by `ui-test-author/appium`)

Before writing, **load `qa/java/skills/ui-test-author/appium/SKILL.md`** and apply its page-object rules; the object model is the rule file `qa-java-page-objects.md`. The non-negotiables:

- Extend `BaseAppiumPage`; constructor passes `driver` to `super(driver)` — never call `driver.findElement(...)` directly. Pages take the driver, never a test context.
- All element access goes through the inherited finders, in ladder order: `byTestId` (`AppiumBy.accessibilityId` on iOS, `AppiumBy.id` on Android) → native query (`byIosPredicate` · `byIosClassChain` · `byAndroidUiAutomator`, the last secondary because Google is deprecating `UiSelector`) → `byXPath`. An XPath rung is a temporary scaffold, not a destination — when `mobile-screen-explorer` later reports a stronger locator for that element, downgrade to it and drop its row from `missing-testids.md`. The code carries no marker.
- Each locator is a `private static final String {ELEMENT}_ID` constant at the top (a fallback is named `{ELEMENT}_XPATH_FALLBACK`) — never inline a locator string in a method. A page exposes intent and queries, never a `WebElement`.
- Return types: `void` for same-screen actions; the destination page object for navigation actions
- **Every page object has a `verifyPageLoaded()`** asserting the landmark is visible (the only assertion allowed inside a page object)
- No `PageFactory`/`@FindBy`/`@AndroidFindBy`, no raw `RemoteWebElement`
- No `Thread.sleep` — the base class's `WebDriverWait` handles timing
- Package `pom.mobile`; file `src/main/java/pom/mobile/<Screen>Page.java`; multi-step screens in a sub-package.
- **Repeating rows and cards are region components**: a row key, re-resolved on every call, picked by its content, never by index (`OrderRow` in the assets). They do not extend `BaseAppiumPage`.
- **Native controls are control components at first use** (a picker wheel, a date picker, a segmented control, a bottom sheet): a class in `components.controls` that takes the control's container id and exposes intent with domain types (`select(LocalDate)`, `choose(String option)`). A control whose operation differs per platform is one class per platform, built by the per-platform page (`page-object-design`'s multi-platform strategy), never a `switch` on the platform.
- Methods are one user action each, named for the action (`signIn`), never the outcome; no boolean parameter selecting behaviour.

## Template

```java
package pom.mobile;

import io.appium.java_client.AppiumDriver;
import org.openqa.selenium.WebElement;

import static org.assertj.core.api.Assertions.assertThat;

public final class LoginPage extends BaseAppiumPage {
    private static final String EMAIL_ID = "Login.Email";
    private static final String PASSWORD_ID = "Login.Password";
    private static final String SUBMIT_ID = "Login.Submit";

    public LoginPage(AppiumDriver driver) {
        super(driver);
    }

    @Override
    public void verifyPageLoaded() {
        assertThat(isTestIdVisible(EMAIL_ID))
                .as("Expected LoginPage to be visible but the email field was not found")
                .isTrue();
    }

    public OrdersPage signIn(String email, String password) {
        type(byTestId(EMAIL_ID), email);
        type(byTestId(PASSWORD_ID), password);
        byTestId(SUBMIT_ID).click();
        return new OrdersPage(driver);
    }

    private static void type(WebElement field, String text) {
        field.clear();
        field.sendKeys(text);
    }
}
```

`byTestId` picks `accessibilityId` on iOS and `id` on Android, so one accessor serves both platforms. For an element with no test id, use the fallback finder and record the row in `missing-testids.md`; prefer a native query over XPath whenever the source exposes one:

```java
private static final String PASSWORD_REVEAL_XPATH_FALLBACK = "//*[@class='…ImageButton'][2]";
```

The compilable reference is `qa/java/skills/ui-test-author/appium/assets/`.

## Procedure

1. **Check for an existing page object.** Glob the project for `**/pom/mobile/**/<Screen>Page.java` (and `**/pages/**`). Exists → this is an **update** (step 4). Missing and the project has no `pom/mobile/` at all → load `qa/java/skills/page-object-design` first to lay down the base class + structure.
2. **Classify, then map.** Group the inventory first: repeating rows and cards become region components, native controls become control components (reuse the project's class when one exists), and their elements move into them. Map each remaining element to a constant + finder using its locator-ladder rung. Test-id elements use `byTestId`; fallbacks use the matching finder, and each gets a row in `missing-testids.md`.
3. **Write the class** per the conventions above: constants block, constructor, `verifyPageLoaded()` on the landmark, one intent-named action per user action (returning `void` or the destination `*Page`), one query method per datum a test reads, and a method returning each component (`row(orderNumber)`). Stub any destination page that doesn't exist yet.
4. **Update mode — diff before writing:**
   - New element on screen, not in class → add constant + accessor/action
   - Constant in class, element gone from screen → flag and **ask** before deleting (may belong to a state you didn't reach)
   - Element's accessibility id changed → update the constant, note it as a breaking rename for the team
   - Fallback locator where a test id now exists → upgrade to `byTestId`, rename the constant, remove the row from `missing-testids.md`
   - Never reorder/rename existing public methods tests already call without flagging it
5. **Verify:** `./gradlew compileTestJava` (or the project equivalent) → compiles clean. Confirm `verifyPageLoaded()`'s landmark matches what `mobile-screen-explorer` reported for this screen.
6. **Report:** class created/updated (diff summary), components created or reused, counts (test-id-backed / fallback / ⚠ XPath), destination stubs created, open questions.

## Rules

- **Discovery is not this skill's job** — never invent a locator. If an element wasn't in the `mobile-screen-explorer` inventory, go get it there first.
- **Test-id-first** in the emitted code, matching the discovery contract; every fallback has a `missing-testids.md` row, never a code marker.
- **`ui-test-author/appium` wins on every convention conflict** — this skill is its codegen-from-inventory front end, not a competing rulebook.
- **No assertions outside `verifyPageLoaded()`**, no business logic / API calls, no test code in the page object.
- One class per screen; update in place rather than creating a parallel duplicate.
