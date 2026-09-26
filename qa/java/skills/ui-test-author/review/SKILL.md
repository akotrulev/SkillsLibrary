---
name: qa-ui-test-review-java
description: Use when the user asks to review existing Java UI test code or page objects. Triggers: "review this Playwright Java spec", "look at this Selenium page object", "is this Appium Java test any good". Do NOT use for writing new tests (`qa-ui-test-writer-playwright-java`) or reviewing a Gherkin/Cucumber layer (`qa-bdd-reviewer-java`).
---

# QA — UI Test & Page Object Reviewer (Java)

Reviews Java UI test code (Playwright Java, Selenium Java, Appium Java) against the patterns enforced by the matching generator skills. Produces a findings table in the format defined in `CLAUDE.md`. **Does not rewrite the code** — points to the fix and lets the human apply it.

## When to use

- A diff or file (page object, `@Test` class, fixture, `BaseTest`, `BasePage`) is submitted for review
- Pre-merge gate on a PR touching `src/main/java/pom/`, `src/test/java/`, or any TestNG/JUnit UI test
- Second opinion on whether a Java page object is well-structured

## When NOT to use

- Generating new code → `qa/java/skills/ui-test-author/playwright`, `qa/java/skills/ui-test-author/selenium`, `qa/java/skills/ui-test-author/appium`
- Architecting the POM (sub-packages, base classes) → `qa/java/skills/page-object-design`
- Reviewing API tests → `qa/java/skills/api-test-author/review`
- Reviewing .NET UI code → `qa/dotnet/skills/ui-test-author/review`
- Reviewing TypeScript UI code → `qa/typescript/skills/ui-test-author/review`

## Inputs needed

1. **Stack** — Playwright Java, Selenium Java, or Appium Java
2. **Files** to review (page objects, `@Test` classes, fixtures, `BaseTest`/`BasePage`)
3. **Context** — new feature, refactor, or bug fix?
4. **Project conventions** — anything overriding the stack defaults (e.g. project bans XPath, mandates Allure `@Step`)

## Output format

```
| Severity | Location                       | Issue                                              | Suggested fix                                                |
|----------|--------------------------------|----------------------------------------------------|--------------------------------------------------------------|
| blocker  | pom/LoginPage.java:42          | `Thread.sleep(2000)` — arbitrary wait              | Replace with `WebDriverWait` + `ExpectedConditions.visibilityOf` |
| major    | pom/ProductPage.java:18        | XPath where a `data-test` attribute exists         | Switch to `By.cssSelector("[data-test='inventory-item']")`   |
| minor    | pom/CartPage.java:55           | Inline `By.cssSelector(...)` repeated in 3 methods | Promote to `private static final By CART_BADGE`              |
```

Severities (from `CLAUDE.md`):

- **blocker** — ships a bug, breaks the build, or violates a hard rule (e.g. `Thread.sleep`, shared driver, raw credentials)
- **major** — design or correctness issue that will hurt soon (brittle locators, assertions in page objects)
- **minor** — style or small inconsistency (naming, missing constant)
- **nit** — optional preference

**Do not rewrite the code during review.** If the user wants a rewrite, hand off to the matching generator skill.

## Cross-stack smells (apply to every Java UI review)

| Check | Bad sign | Severity |
|---|---|---|
| No `Thread.sleep` / `page.waitForTimeout` | Any literal millisecond sleep | blocker |
| Locators are semantic | Raw XPath where `data-test`/role/label exists | major |
| Assertions live in tests, not page objects | `Assert.*` calls inside `click`/`enter*`/`select*` methods on a page class | major |
| No business logic in page objects | Price calculation, JSON parsing, branching on app state inside POM | major |
| Tests are independent | `@Test(dependsOnMethods = {...})` chaining a flow across tests | blocker |
| One logical behavior per test | One `@Test` verifies login + cart + checkout | major |
| No `try`/`catch` in a test or `@AfterMethod` | Any catch block in a `@Test`; a swallowing teardown; a blanket `catch (Exception)` in a page helper | major |
| Failures identify the subject | Assertions with no message argument, so a failure cannot be told from a bad locator | minor |
| Every assertion states one expected condition | `assertTrue(a \|\| b)`, `anyOf(...)` / `either().or()` matchers, `Pattern.compile("a\|b")` in a text/URL assertion | major |
| Test names describe behavior | `test1`, `loginTest`, `clickButtonTest` | minor |
| No hardcoded credentials / base URLs | Literal `admin@example.com`, hardcoded `https://staging.x.y` | major |
| Locators promoted to `private static final By` or `private final Locator` fields | Inline locator strings re-typed across methods | minor |
| No conditional logic driving assertions | `if (x) Assert.assertTrue(...)` instead of parameterized cases | major |
| TestNG `@DataProvider` used for parameterization, not `for` loops in `@Test` | Loop-driven multi-case test that hides which case failed | major |
| Build is Gradle (Kotlin DSL) for new projects | Maven `pom.xml` when project standard is Gradle | minor |

## Playwright Java smells

| Check | Bad sign | Severity |
|---|---|---|
| Every test asserts something | `@Test` body ends with an action and no `PlaywrightAssertions.assertThat(...)` | blocker |
| Web-first assertions used | `Assert.assertTrue(locator.isVisible())` / `assertEquals(locator.textContent(), ...)` / `assertEquals(locator.count(), n)` | major |
| `page.getByRole` / `getByLabel` / `getByTestId` preferred | `page.locator("css...")` in test classes | major |
| Locators are `private final Locator` fields initialized in constructor | Methods that return `page.locator(...)` per call | minor |
| No hardcoded sleeps | `page.waitForTimeout(...)` or `Thread.sleep(...)` anywhere | blocker |
| No `setWaitUntil(WaitUntilState.NETWORKIDLE)` | `navigate(url, new Page.NavigateOptions().setWaitUntil(NETWORKIDLE))` | major |
| No `setForce(true)` to bypass actionability | `.click(new Locator.ClickOptions().setForce(true))` / same on `fill` / `check` | major |
| No redundant pre-waits before auto-waiting actions | `locator.waitFor()` immediately before `locator.click()` | minor |
| `waitForResponse` ordering correct | `page.waitForResponse(predicate, callback)` is the runnable form — never call after the action | major |
| Custom retry loops replaced by assertion timeouts or Awaitility | `while (retries-- > 0) { ... Thread.sleep ... }` | major |
| `waitForFunction` not used for plain UI state | `page.waitForFunction("() => ...")` for visible/text checks | minor |
| Deprecated APIs removed | `page.waitForNavigation(...)` in code | major |
| Positive matchers preferred over `.not` | `not().isVisible()` where `isHidden()` exists | nit |
| `setExact(true)` set for ambiguous text/role names | `getByText("Submit")` matching multiple labels (`Submit Order`, `Submitting…`) | minor |
| Auth via `storageState`, not per-test login | Every test calls `loginPage.signIn(...)` | major |
| `expectLoaded()` exists on every page object | No landmark assertion method | minor |
| Tests extend `BaseTest` — no manual `Playwright.create()` | Test class manages its own Playwright/browser lifecycle | major |
| Allure `@Step` used for non-trivial workflows | A test with 12 actions and no step labels | nit |

## Selenium Java smells

| Check | Bad sign | Severity |
|---|---|---|
| All page objects extend `BasePage` | Pages calling `driver.findElement` directly | major |
| Locator preference order (`data-test` → `id` → `css` → `class` → `xpath`) honored | XPath used where `data-test` exists | major |
| No `@FindBy` / `PageFactory` when project standard is explicit `findElement` | `@FindBy` annotations sprinkled across pages that should be explicit | minor |
| Component classes scoped to a parent `WebElement` for repeating items | One giant page object that re-queries the DOM for every card | major |
| Driver lifecycle via `DriverFactory` `ThreadLocal<WebDriver>` | `new ChromeDriver()` in a test or base class | blocker |
| `BaseTest` provides driver via `@BeforeMethod` / `@AfterMethod` | Per-test driver instantiation or shared static driver | major |
| `WebDriverWait` + `ExpectedConditions` for conditional waits | `Thread.sleep` for synchronization | blocker |
| Multi-step flows live in sub-packages (`pom/checkout/`) | Flat `pom/` with 30 unrelated pages | minor |
| Navigation methods return the destination page object | Navigation method returns `void`; the test instantiates the next page | minor |
| `SoftAssert` used when verifying multiple fields after one action | Multiple `Assert.assertEquals` that stop on first failure | minor |
| No `driver.manage().timeouts().implicitlyWait(...)` mixed with explicit waits | Implicit + explicit waits combined (causes unpredictable timeouts) | major |
| No `JavascriptExecutor` `.click()` workarounds | `((JavascriptExecutor) driver).executeScript("arguments[0].click()", el)` | major |
| Element accessors return `WebElement`, not booleans pre-asserted in the POM | `public boolean isLoginButtonVisible()` returning the assertion | minor |

## Appium Java smells

| Check | Bad sign | Severity |
|---|---|---|
| Page objects subclass `BaseAppiumPage` (or project equivalent) | Class extends `AppiumDriver` or raw Selenium types | major |
| Accessibility ID first (`AppiumBy.accessibilityId(...)`) → `id` → `xpath` | XPath used when `contentDescription` / `accessibilityIdentifier` exists | major |
| `AppiumDriver<MobileElement>` (or generic v2 `AppiumDriver`) — no raw `WebDriver` field | Page uses `WebDriver` instead of the Appium driver | minor |
| `verifyPageLoaded()` present and asserts a landmark | Missing or empty implementation | major |
| Navigation actions return the destination page object | Navigation method returns `void` | minor |
| Locator strings declared as `private static final By` | Locator literals inline in action methods | minor |
| Platform branching abstracted behind a strategy/locator map | `if (platform.equals("iOS")) ... else ...` scattered across pages | major |
| App state reset between tests (`driver.resetApp()` / fresh install / `--no-reset` off) | Tests leak data into each other through shared app state | blocker |
| Capabilities loaded from config, not hardcoded in `@BeforeMethod` | `DesiredCapabilities` literal `setCapability("deviceName", "Pixel_6")` in base | major |
| Gestures via `W3CActions` / `RemoteExecuteMethod` (Appium 2.x) | Deprecated `TouchAction` / `MultiTouchAction` calls | major |
| No `Thread.sleep` between gestures | `Thread.sleep(1500)` after a swipe waiting for animation | blocker |
| Test names describe user behavior on device, not screen names | `screen1Test`, `tapButton2` | minor |

## Good signals (Java)

Code that looks well-written in this stack tends to share these traits:

- Every page object extends a thin base (`BasePage` / `BaseAppiumPage`) with one synchronization helper
- Locators are `private static final By` constants or `private final Locator` fields — not magic strings
- One `@Test` per behavior, descriptive name (`successfulLogin`, `cartShowsAddedProduct`), no `dependsOnMethods`
- Driver / Playwright / Appium driver lifecycle owned by `BaseTest` via a `ThreadLocal` factory — parallel-safe
- `WebDriverWait` + `ExpectedConditions` (Selenium) or Playwright auto-waits (Playwright Java) — no `Thread.sleep`
- Multi-step flows live in a sub-package (`pom/checkout/`) with each step returning the next page
- Reusable components (cards, rows) take a parent `WebElement` / `Locator` and query inside it
- TestNG `@DataProvider` for parameterization; failure message identifies the failing case
- Constructor injection — no static mutable state on pages
- Allure `@Step` annotations on non-trivial workflows for human-readable reports

## Always-flag anti-patterns

- **`OR` in an assertion.** `assertTrue(t.equals("Saved") || t.equals("Success"))`, a Hamcrest `anyOf(...)` / `either(...).or(...)`, or a `"Saved|Success"` regex alternation in a text/URL assertion — all the same defect: the test does not know what the app should render, so it passes on the wrong state and never fails when the app flips between the two. Watch for the regex form especially; it hides in `hasText(Pattern.compile(...))` and reads as a legitimate matcher. Fix by splitting into one `@Test` per expected outcome, driving it from a `@DataProvider`, or pinning the correct value.

- **Test that asserts nothing.** A `@Test` ending after a `click()` with no assertion is not a test.
- **Page object that asserts.** Move every `Assert.*` out of the POM and into the test.
- **`Thread.sleep` for sync.** Always a blocker, regardless of duration.
- **Brittle locator chain.** `By.xpath("//div/div/span[3]/a")` will break on the next DOM tweak.
- **Login-in-every-test.** Use `storageState` (Playwright), a seeded session (Selenium), or a token-injecting `@BeforeSuite`.
- **Any `try`/`catch` in a `@Test` — or in `@AfterMethod`.** There is no legitimate one. Wrapping the body hides failures; wrapping cleanup leaks state silently. An expected exception is asserted with `assertThrows`; an unexpected one must reach TestNG; cleanup is registered and deleted in `@AfterMethod(alwaysRun = true)` with no catch. The suite's only catches belong in an I/O helper narrowing **one named** exception (`isDisplayed(By)` catching `NoSuchElementException`) — never a blanket `catch (Exception)`.
- **A failure message that names no subject.** `expected [Saved] but found []` could be a wrong value or a locator that matched nothing — pass the message argument naming the element and the record.
- **`@FindBy` mixed with explicit `findElement` in the same project.** Pick one.
- **Shared static `WebDriver`** across tests. Breaks parallel execution.
- **Any inline comment in a test body or a page-object method** (`// click login`, `// Arrange`), and any stale comment. Per `ep-code-comments` — the name is the explanation; rename or extract, never reword.

## Comments in test code

Load **[`ep-code-comments`](../../../../../engineering-practices/code-comments/SKILL.md)** for the rule itself, the complex-flow test that earns a doc comment, the never-comment trivia list, and the severity mapping. Its **test-code** section carries the AAA-banner rule and the exactly-three-permitted-comments list. This section supplies only the mechanics that differ here. Here it covers **page-object and screen-object bodies** as well as tests — an intent-revealing method name is the page object's documentation.

| Java mechanic | What to check |
|---|---|
| Doc syntax | Javadoc (`/** … */`) — a doc block on a locator field, or restating `ClickSave`, is trivia |
| Skips needing a reason and a ticket | `@Test(enabled = false)` / `@Ignore` with nothing recorded — a silently disabled test |
| Where an unclear interaction goes instead | Into a named page-object method, not a comment above the locator chain |

**The locator corollary — the one that matters most here.** A comment explaining a locator (`// the third span is the price`) is not a comment finding; it is evidence the locator is **positional and brittle**. Fix the locator: request a `data-testid` and record it in `missing-testids.md`. Cross-reference the finding to the locator-hygiene list rather than filing it as a comment.

## Procedure

1. Identify the **stack** (Playwright / Selenium / Appium) from imports and file location.
2. Read the file end-to-end before writing findings — context matters for severity.
3. Walk the cross-stack list, then the stack-specific list.
4. For each finding, capture: file path + line, issue, one-sentence suggested fix.
5. **Do not rewrite the code.** Hand off to the matching generator if the user asks for a rewrite.

## Handoffs

- Need to rewrite → `qa/java/skills/ui-test-author/playwright`, `qa/java/skills/ui-test-author/selenium`, or `qa/java/skills/ui-test-author/appium`
- Architecture is the real problem (not the code) → `qa/java/skills/page-object-design`
- Test data shape is wrong → `qa/java/skills/test-data-builder`
- API tests in the same PR → `qa/java/skills/api-test-author/review`
- Allure reporting questions → `qa/reporting/java/skills/test-reports`
