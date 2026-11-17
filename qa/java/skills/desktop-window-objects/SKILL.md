---
name: desktop-window-objects
description: Use when creating or updating a Java Appium window object for a macOS or Windows app from explored elements. Triggers "create a window object". Not for finding elements (desktop-screen-explorer).
---

# QA — Desktop Window Object Builder (Java)

Turns a discovered element inventory into a **Java Appium window object**: a `BaseWindow` subclass under `windows/`. It consumes the element table and locator rungs from `qa/java/skills/desktop-screen-explorer` (or an inventory the user supplies) and emits or updates one window class. It owns **codegen, multi-window and dialog handling, waits, and the create/update diff**. The shared rules (id contract, window-object rules, window scoping) are `qa/_shared/desktop-testing`; the TestNG spec conventions are `qa/java/skills/ui-test-author/appium`. The mobile twin is `qa/java/skills/mobile-screen-objects`.

## When to use

- Elements for a window were discovered and now need a class.
- An existing window object must be reconciled against a freshly explored window.
- The user describes a window's elements and ids directly and wants the class emitted.

## When NOT to use

- Locators are not known yet → `qa/java/skills/desktop-screen-explorer` first. Never fabricate one.
- Writing the tests that use the object → `qa/java/skills/ui-test-author/appium`.
- Mobile screens → `qa/java/skills/mobile-screen-objects`; web pages → `qa/java/skills/page-objects-from-url`.
- Reviewing an existing object → `qa/java/skills/ui-test-author/review`.
- TypeScript / .NET → `qa/typescript/skills/desktop-window-objects` / `qa/dotnet/skills/desktop-window-objects`.

## Inputs needed

1. **Window name** (PascalCase: `LibraryWindow`, `SettingsWindow`, `ExportDialog`) and whether it is a main window, a document window, a sheet or a dialog.
2. **Element list**: per element the name, type and rung from the explorer (the test id first, `accessibilityId`).
3. **Landmark**: one container id that proves the window is up (used by `verifyWindowLoaded()`).
4. **Actions**: user-intent actions, and for each whether it opens another window or dialog (→ its class).
5. **Target project**: repo path and the existing `windows/` convention.

## Conventions

The standards an emitted object must meet are the qa-java rule files `qa-java-page-objects.md`, `desktop-tests.md` and `qa-java.md` (the project's copy in `.claude/rules/qa-java/`, or the plugin's in `qa/java/skills/rules/`). The codegen specifics:

- Element access goes through `BaseWindow`'s finders, in ladder order: `byTestId` (`AppiumBy.accessibilityId`, the same on both platforms) → a find inside the container for rows → a label or native query as a named fallback → XPath last.
- Each id is a `private static final String {ELEMENT}_ID` constant (a fallback is `{ELEMENT}_FALLBACK`); a window exposes intent and queries, never a `WebElement`.
- Navigation actions return the destination window object; same-window actions return `void`.
- Package `windows`, file `windows/<Window>.java`.
- **Repeating rows are region components**: a row key, re-resolved from its container on every call, picked by its content, never by position. They do not extend `BaseWindow`.
- **Native controls are control components at first use** (a date picker, a combo box, an outline or data grid, a tab view, a toolbar segmented control): a class in `components.controls` that takes the control's container id and exposes intent with domain types (`select(LocalDate)`, `choose(String item)`). Two platforms' markups are two classes, never a branch.
- One user action per method, named for the action, never the outcome; no boolean parameter selecting behaviour.
- Per-platform ids (only where one object serves both apps) live in a locator map keyed by platform: one accessor per element, and no action branches on the platform.
- No `PageFactory`, `@FindBy`, `@AndroidFindBy` or `@iOSXCUITFindBy`, and no raw `RemoteWebElement`.

## Template

```java
package com.example.desktoptests.windows;

import io.appium.java_client.AppiumBy;
import io.appium.java_client.AppiumDriver;
import org.openqa.selenium.By;
import org.openqa.selenium.TimeoutException;
import org.openqa.selenium.WebElement;
import org.openqa.selenium.support.ui.ExpectedConditions;
import org.openqa.selenium.support.ui.WebDriverWait;

import java.time.Duration;

public abstract class BaseWindow {
    static final Duration TIMEOUT = Duration.ofSeconds(10);

    protected final AppiumDriver driver;
    private final WebDriverWait wait;

    protected BaseWindow(AppiumDriver driver) {
        this.driver = driver;
        this.wait = new WebDriverWait(driver, TIMEOUT);
    }

    protected WebElement byTestId(String id) {
        return present(AppiumBy.accessibilityId(id));
    }

    protected WebElement byXPath(String xpath) {
        return present(By.xpath(xpath));
    }

    protected boolean isTestIdVisible(String id) {
        try {
            wait.until(ExpectedConditions.visibilityOfElementLocated(AppiumBy.accessibilityId(id)));
            return true;
        } catch (TimeoutException e) {
            return false;
        }
    }

    public abstract void verifyWindowLoaded();

    private WebElement present(By locator) {
        return wait.until(ExpectedConditions.presenceOfElementLocated(locator));
    }
}
```

```java
package com.example.desktoptests.windows;

import io.appium.java_client.AppiumDriver;

import static org.assertj.core.api.Assertions.assertThat;

public final class LibraryWindow extends BaseWindow {
    private static final String ROOT_ID = "Library.Window";
    private static final String SEARCH_ID = "Library.SearchField";
    private static final String ALBUM_TABLE_ID = "Library.AlbumTable";

    public LibraryWindow(AppiumDriver driver) {
        super(driver);
    }

    @Override
    public void verifyWindowLoaded() {
        assertThat(isTestIdVisible(ROOT_ID))
                .as("Expected LibraryWindow to be visible but Library.Window was not found")
                .isTrue();
    }

    public void searchFor(String text) {
        byTestId(SEARCH_ID).sendKeys(text);
    }

    public AlbumRow album(String title) {
        return new AlbumRow(driver, ALBUM_TABLE_ID, title);
    }
}
```

The row is picked by its title and re-resolved from its container on each call, because a Windows `AutomationId` repeats across rows and is unique among siblings only:

```java
package com.example.desktoptests.windows;

import io.appium.java_client.AppiumBy;
import io.appium.java_client.AppiumDriver;
import org.openqa.selenium.StaleElementReferenceException;
import org.openqa.selenium.WebElement;
import org.openqa.selenium.support.ui.WebDriverWait;

public final class AlbumRow {
    private static final String ROW_ID = "Library.Row";
    private static final String TITLE_ID = "Library.Row.Title";
    private static final String ARTIST_ID = "Library.Row.Artist";

    private final AppiumDriver driver;
    private final String tableId;
    private final String title;

    AlbumRow(AppiumDriver driver, String tableId, String title) {
        this.driver = driver;
        this.tableId = tableId;
        this.title = title;
    }

    public String artist() {
        return row().findElement(AppiumBy.accessibilityId(ARTIST_ID)).getText();
    }

    public void open() {
        row().click();
    }

    private WebElement row() {
        return new WebDriverWait(driver, BaseWindow.TIMEOUT)
                .ignoring(StaleElementReferenceException.class)
                .withMessage("No " + ROW_ID + " titled " + title + " in " + tableId)
                .until(d -> d.findElement(AppiumBy.accessibilityId(tableId))
                        .findElements(AppiumBy.accessibilityId(ROW_ID)).stream()
                        .filter(row -> title.equals(row.findElement(AppiumBy.accessibilityId(TITLE_ID)).getText()))
                        .findFirst()
                        .orElse(null));
    }
}
```

On macOS a row that combines its children (`.accessibilityElement(children: .combine)`) exposes only the row id: match the key on the row's own `label` or `value` and drop the child accessors. A fresh `WebElement` is found on every call, so a table that redraws never leaves a stale reference.

A fallback (no id yet): name the constant `*_FALLBACK`, use a label or native query before XPath, and add the row to `missing-testids.md`. The Windows form below uses `AppiumBy.name`, which reads the UIA `Name`; on Mac2 `name` is the `identifier`, so a macOS label fallback is a `predicate string` on `label`, sent as `driver.findElement("predicate string", …)` because `AppiumBy.iOSNsPredicateString` sends the prefixed name Mac2 does not accept:

```java
private static final String EXPORT_BUTTON_FALLBACK = "Export…";
driver.findElement(AppiumBy.name(EXPORT_BUTTON_FALLBACK));
```

## Multi-window and dialogs

- **A window object is bound to one window.** The action that opens another window returns the destination's object, and the destination's `verifyWindowLoaded()` switches to it. Switching is a method in `BaseWindow`, never inline in a test.
- **Mac2:** find the window with `driver.executeScript("macos: listWindows", Map.of())` (driver 4.5.0 and later) and match on `title`. **WinCore:** `driver.getWindowHandles()` omits untitled windows, so use `windows: getWindows` and match on `title` or `className`, then `driver.switchTo().window(handle)`.
- Switch back to the previous window object after a dialog closes: the action that confirms or cancels returns the parent window's object.
- Wait for the destination's landmark, never for a duration. A dialog that must appear is asserted with the base class's wait on its landmark, with a message naming the dialog.
- A system panel (open/save, permission) is another process: model it as its own small object with ids read from its tree, or report it. A UAC prompt is never driven.
- A quit with unsaved work is asserted: the confirmation prompt appears, then the test chooses.

## Waits

`BaseWindow`'s `WebDriverWait` finders are the only waits. Add a new wait to the base class, never inline in a window object or a test, and no `Thread.sleep` and no implicit wait anywhere. The timeout message names the element and the window.

## Procedure

1. **Check for an existing object.** Glob `**/windows/<Window>.java`. Exists → **update** (step 4). The project has no `windows/` and no `BaseWindow` → run `qa/java/skills/desktop-project-setup` first.
2. **Classify, then map.** Each repeating group becomes a region component addressed inside its container, and each native control a control component (reuse the project's class when one exists); their elements move into them. Map each remaining element to a constant and finder by its rung: test-id elements use `byTestId`; fallbacks are `*_FALLBACK` with a `missing-testids.md` row.
3. **Write the class** per the conventions: constants, constructor, `verifyWindowLoaded()` on the landmark, one intent-named action per user action, one query method per datum a test reads. Stub any destination window that does not exist.
4. **Update mode, diff before writing:**
   - New element, not in the class → add constant and finder or action.
   - Constant in the class, element gone from the window → flag and **ask** before deleting (it may belong to a state not reached).
   - An id changed → update the constant and note it as a breaking rename.
   - A fallback where an id now exists → upgrade to `byTestId`, rename, remove the row from `missing-testids.md`.
   - Never reorder or rename public methods tests already call without flagging it.
5. **Verify:** `./gradlew compileTestJava` clean. Confirm the landmark matches what the explorer reported.
6. **Report:** class created or updated (diff summary), components created or reused, counts (id-backed / fallback / ⚠ XPath), destination stubs, open questions.

## Rules

- **Discovery is not this skill's job**: never invent a locator.
- One class per window; update in place rather than creating a duplicate.
- A window object takes the driver and nothing else; the only assertion inside one is `verifyWindowLoaded()`. No business logic, API calls or test code.
- Everything else is the rule files named under Conventions; where they and this skill disagree, the rule files win.

## Handoffs

- Discovering the elements → `qa/java/skills/desktop-screen-explorer`
- Scaffold and OS prerequisites → `qa/java/skills/desktop-project-setup`
- Writing the tests → `qa/java/skills/ui-test-author/appium`
- Object architecture (base classes, sub-packages) → `qa/java/skills/page-object-design`
- Missing ids → the `desktop-macos` or `desktop-windows` agent
- Shared rules → `qa/_shared/desktop-testing`
- TypeScript / .NET siblings → `qa/typescript/skills/desktop-window-objects` / `qa/dotnet/skills/desktop-window-objects`
