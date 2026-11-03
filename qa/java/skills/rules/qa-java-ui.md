---
paths:
  - "**/{uitests,ui-tests,mobiletests,mobile-tests,e2e,e2e-tests}/**/*.java"
  - "**/src/{test,integrationTest}/java/**/{pages,pageobjects,screens,components,flows}/**/*.java"
  - "**/src/{test,integrationTest}/java/**/*{Page,Screen}.java"
  - "**/pom/**/*.java"
---

<!-- qa-java rules v1 (2026-11-03): UI and mobile. Installed by /qa-java:rules; edit the paths above to where this project keeps its page objects and UI tests. -->

# Java UI and mobile test standards

Severity tags as in the core qa-java rules: **blocker**, **major**, **minor**, **nit**. The codebase wins where it consistently differs.

- Test id first: Playwright test id → role → label → text → CSS; Selenium `data-test` → id → CSS → XPath; Appium id → native → XPath. Ids are static: no index, key or state. *major*
- Never invent a locator; a fallback is a `missing-testids.md` row, never a code comment or `TODO`. *minor*
- Scope instead of picking; `nth()` / `first()` only where order is the behaviour. Never assert on an `or()` locator. *major*
- One page object per page or screen. Locators are private fields or constants; methods name user intent (`signIn`); navigation returns the next page. *minor*
- Tests never call `driver.findElement`, `page.locator` or `page.navigate`; the page owns its URL. *major*
- No assertion in a page object beyond one landmark check (`expectLoaded()` / `verifyPageLoaded()`); no business logic, API call or test code. *major*
- No god page, no central locator file; a component takes its root element; no base page until three pages share behaviour. *major*
- Drivers come from the base or factory, never `new ChromeDriver()`, `Playwright.create()` or `new AndroidDriver()` in a test. Playwright and Appium: instance fields, `parallel="classes"`, no `ThreadLocal`, no `parallel="methods"`, no `@DataProvider(parallel = true)`. Selenium: a `ThreadLocal<WebDriver>` factory. *blocker*
- Explicit waits only, never mixed with an implicit wait; no forced click (`setForce(true)`, `JavascriptExecutor`). Playwright: web-first assertions, no `NETWORKIDLE`, `waitForNavigation` or page-level selector API. *major*
- Sign in once per role per run; reuse the storage state. *major*
- Evidence comes from the base class. *minor*
- Appium: platform differences live in the finder, not an `if`; app state reset per test; OS dialogs go through `mobile:` commands; no `TouchAction`, `resetApp`, `@AndroidFindBy` or `PageFactory`. *major; blocker for leaked state*
