---
name: qa-ui-test-author-appium-dotnet
description: Use when the user asks to scaffold a .NET (C#) Appium page object for a mobile screen in `AppiumTests/Pages/`. Triggers: "create a C# Appium page object for X", "add a .NET page for the Y screen", "generate an Appium page object in C#", "implement the Z page". Do NOT use for Appium Java (use `qa/ui-test-author/appium/java`), Appium TypeScript / WebdriverIO (use `qa/ui-test-author/appium/typescript`), web tests (use `qa/ui-test-author/playwright`), tests inside the Accelerator (use `qa/accelerator-conventions`), or non-page Appium test fixtures.
---

# QA — Appium Page Object Generator

Generates a C# page object class for `AppiumTests/Pages/` that follows the project's Page Object Model: a `BaseAppiumPage` subclass with accessibility-id-first locators, typed return values for navigation, and a `VerifyPageLoaded()` landmark check.

## When to use

- Adding a page object for a new mobile screen
- Replacing an ad-hoc test helper with a proper page object
- Scaffolding the next page object in a navigation flow

## When NOT to use

- Web / Playwright tests → `qa/ui-test-author/playwright`
- Pages inside the Accelerator repo → `qa/accelerator-conventions`
- Non-page Appium fixtures (test classes, drivers, capabilities) → out of scope here
- Reviewing an existing page object → `qa/ui-test-author/reviewer`

## Inputs needed

Ask only what's missing:

1. **Screen name** (PascalCase, e.g. `Login`, `Home`, `OrderConfirmation`)
2. **Elements** to expose — for each: a human label + the `testID` / accessibility id from the app
3. **Actions** the test will perform — for each: what it does and whether it navigates
4. **Landmark element** — the one element that proves the page is currently visible (used in `VerifyPageLoaded`)
5. **Next pages** — for any action that navigates, the destination page object class name

## Rules

1. **Subclass `BaseAppiumPage`** — never extend `AppiumDriver` or any raw Appium class directly.
2. **Constructor** accepts `IWebDriver driver` and passes it to `base(driver)`.
3. **All element access** goes through the inherited finder methods, in priority order:
   - `FindByAccessibilityId(id)` — use first; maps to React Native `testID` prop
   - `FindById(id)` — use when no accessibility id is available
   - `FindByXPath(xpath)` — last resort only; add `// TODO: replace with AccessibilityId` comment
4. **Return types** for action methods:
   - `void` for actions that stay on the same screen
   - The next page object type (e.g. `return new HomePage(Driver);`) for navigation actions
5. **Every page object must include a `VerifyPageLoaded()` method** that uses `Assert.That` to confirm the page is visible (e.g. checks a landmark element is displayed).
6. **Do not use raw `IWebElement`** — all returned/stored elements must be `AppiumElement`.
7. **No `Thread.Sleep()`** — rely on Appium's built-in element-finding timeout or `WebDriverWait`.
8. **Namespace**: `AppiumTests.Pages`
9. **File location**: `AppiumTests/Pages/<ScreenName>Page.cs`
10. **Locator constants** — declare each locator as `private const string` at the top of the class, named `{Element}Id`. Never inline a locator string in an action method.
11. **Method naming** — actions describe user intent (`Login`, `TapPrimaryAction`, `EnterEmail`), not Appium mechanics (`ClickSubmitButton` is fine; `FindAndClickButton` is not).

## Template

See [`assets/page_template.cs`](assets/page_template.cs) for a ready-to-copy starting point.

Key structural sections (in order):

1. Locator constants
2. Constructor
3. `VerifyPageLoaded()`
4. Actions (state-changing methods)
5. Queries (read-only methods that return values)

## Example

> "Create a page object for the Login screen. It has a username field (testID: `login-email`), a password field (testID: `login-password`), and a Login button (testID: `login-submit`). On success it navigates to the Home screen."

Generates `AppiumTests/Pages/LoginPage.cs`:

```csharp
using NUnit.Framework;
using OpenQA.Selenium;

namespace AppiumTests.Pages;

public class LoginPage : BaseAppiumPage
{
    private const string EmailFieldId = "login-email";
    private const string PasswordFieldId = "login-password";
    private const string SubmitButtonId = "login-submit";

    public LoginPage(IWebDriver driver) : base(driver) { }

    public void VerifyPageLoaded()
    {
        var emailField = FindByAccessibilityId(EmailFieldId);
        Assert.That(emailField.IsDisplayed(), Is.True,
            $"Expected {nameof(LoginPage)} to be visible but the email field was not found.");
    }

    public HomePage Login(string email, string password)
    {
        var emailField = FindByAccessibilityId(EmailFieldId);
        emailField.Clear();
        emailField.SendKeys(email);

        var passwordField = FindByAccessibilityId(PasswordFieldId);
        passwordField.Clear();
        passwordField.SendKeys(password);

        FindByAccessibilityId(SubmitButtonId).Click();

        return new HomePage(Driver);
    }
}
```

## What NOT to do

- No `Thread.Sleep` / arbitrary delays — Appium's implicit wait covers element resolution; use `WebDriverWait` for conditional waits
- No raw `IWebElement` returns — keep everything as `AppiumElement`
- No locator strings inline in actions — promote to a `private const string`
- No `var landmark = driver.FindElement(...)` — always go through the inherited `FindByAccessibilityId` / `FindById` / `FindByXPath` helpers
- No business logic / API calls inside a page object — page objects model the screen, not the workflow. Test orchestration belongs in the test class.
- No assertions inside actions — assertions live in `VerifyPageLoaded()` and in test methods, never inside `Click`/`EnterText`/`Tap*` actions
- No multi-screen page objects — one class per screen. If the screen has tabs/sheets, model each as its own component or sub-page.

## Generation steps

1. Confirm the **screen name**, **landmark element**, and the list of **elements + actions** with the user.
2. For every element: capture the `testID` (preferred) or platform resource-id. Flag any element that has neither — those become XPath-with-TODO locators.
3. For every action that navigates: confirm the **destination page** class name (and create a stub for it if it doesn't exist).
4. Generate `AppiumTests/Pages/<ScreenName>Page.cs` from the template:
   - Add one `private const string` per element
   - Constructor passes `driver` to `base(driver)`
   - `VerifyPageLoaded()` asserts the landmark element is displayed
   - One action method per user-intent action, returning `void` or the destination `*Page` type
   - One query method per piece of data the test needs to read
5. Run `dotnet build AppiumTests/AppiumTests.csproj` — expect 0 errors. Any missing destination page class becomes a follow-up page-object generation.

## Handoffs

- Reviewing an existing page object → `qa/ui-test-author/reviewer`
- Authoring the test that uses this page object → `qa/test-case-writer`
- Test data setup → `qa/test-data-builder`

## Changelog

- 2026-05-27: Authored from production Appium POM skill.
- 2026-05-28: Relocated under `appium/dotnet/` as the .NET sibling of the new Java and TypeScript variants. Cross-references updated. Reference reading: BrowserStack "Appium Best Practices 2026", BrowserStack "Page Object Model and Page Factory in Appium", and the Appium .NET driver docs.
