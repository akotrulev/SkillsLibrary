---
name: ui-tests-review
description: Use when the user asks to review existing Java UI test code or page objects. Triggers: "review this Playwright Java spec", "look at this Selenium page object", "is this Appium Java test any good". Do NOT use for writing new tests (`qa-java:ui-tests-playwright`) or reviewing a Gherkin/Cucumber layer (`qa-java:bdd-reviewer`).
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
| Severity | Location                | Issue                                              | Suggested fix                                                    |
|----------|-------------------------|----------------------------------------------------|------------------------------------------------------------------|
| blocker  | pom/LoginPage.java:42   | `Thread.sleep(2000)` — arbitrary wait              | Replace with `WebDriverWait` + `ExpectedConditions.visibilityOf` |
| major    | pom/ProductPage.java:18 | XPath where a `data-testid` exists                 | Switch to `By.cssSelector("[data-testid='Inventory.Item']")`     |
| minor    | pom/CartPage.java:55    | Inline `By.cssSelector(...)` repeated in 3 methods | Promote to `private static final By CART_BADGE`                  |
```

Severities follow `CLAUDE.md`: **blocker** (a bug, a broken build, a hard rule), **major**, **minor**, **nit**.

**Do not rewrite the code during review.** If the user wants a rewrite, hand off to the matching generator skill.

## Cross-stack smells (apply to every Java UI review)

| Check | Bad sign | Severity |
|---|---|---|
| No `Thread.sleep` / `page.waitForTimeout` | Any literal millisecond sleep | blocker |
| Locators are semantic | Raw XPath where a test id, role or label exists | major |
| Test ids follow the contract | Kebab-case or dynamic ids (`login-submit`, `row-42`) instead of PascalCase dot-separated static ids (`Login.Submit`, `OrderRow`) | minor |
| A fallback is recorded, not marked | A `// TODO: missing data-testid` marker or comment on a fallback locator instead of a `missing-testids.md` row | minor |
| Assertions live in tests, not page objects | `Assert.*` / `assertThat` inside `click`/`enter*`/`select*` methods on a page class | major |
| No business logic in page objects | Price calculation, JSON parsing, branching on app state inside POM | major |
| Tests are independent | `@Test(dependsOnMethods = {...})` chaining a flow across tests | blocker |
| One logical behavior per test | One `@Test` verifies login + cart + checkout | major |
| No `try`/`catch` in a test or a hook body | Any catch in a `@Test` or a hook body; a blanket `catch (Exception)`; a helper catch that does not log. A narrow, logged catch of one named exception inside an I/O helper is the only allowed one | major |
| Failures identify the subject | An asserted Playwright locator with no `describe()`, or an AssertJ / TestNG value assertion with no `.as(...)` / message. Java's `assertThat(locator)` has no message parameter | minor |
| Every assertion states one expected condition | `assertTrue(a \|\| b)`, `anyOf(...)` / `either().or()` matchers, `Pattern.compile("a\|b")` in a text/URL assertion, an assertion on an `or()` locator | major |
| Test names are `Should_X_When_Y` | `test1`, `loginTest`, `signsInWithValidCredentials` | minor |
| No hardcoded credentials / base URLs | Literal `admin@example.com`, hardcoded `https://staging.x.y` | major |
| Locators promoted to `private static final By` or `private final Locator` fields | Inline locator strings re-typed across methods; methods that re-query per call; public locator fields | minor |
| No conditional logic driving assertions | `if (x) Assert.assertTrue(...)` instead of parameterized cases | major |
| TestNG `@DataProvider` used for parameterization, not `for` loops in `@Test` | Loop-driven multi-case test that hides which case failed | major |
| Build is Gradle (Kotlin DSL) for new projects | Maven `pom.xml` when project standard is Gradle | minor |

## Playwright Java smells

The writer's rules and mechanics are in `qa/java/skills/ui-test-author/playwright` (`references/lifecycle.md`, `locators.md`, `assertions.md`).

| Check | Bad sign | Severity |
|---|---|---|
| Parallel-safe lifecycle | `static Playwright` / `Browser` / `BrowserContext` / `Page`, or a `ThreadLocal` holding them | blocker |
| Suite parallelism matches the thread rule | `parallel="methods"` in `testng.xml`, or `@DataProvider(parallel = true)`, with Playwright | blocker |
| Tests extend the one `BaseTest` | A class calls `Playwright.create()` itself, or a second base class per role / device | major |
| Configuration methods survive group filters | A `BaseTest` hook without `alwaysRun = true` | major |
| A base URL is set | Relative `navigate("/x")` / `request().post("/api/x")` with no `setBaseURL`, or a hardcoded host instead of `BASE_URL` | major |
| Video kept after the close | `video.saveAs(...)` before `context.close()` — Java throws | major |
| Code compiles on the pinned version | `within(`, `getByRef`, `setRecordVideoFps` or screencast `setFps` on 1.63; `Allure.addAttachment(...)` on allure-testng 3 | blocker |
| `Locator` has no `getText()` | `locator.getText()` — Selenium's `WebElement` API; it does not compile | blocker |
| Per-assertion timeouts use the matcher's options | `new AssertOptions().setTimeout(...)` — no such class; use `new LocatorAssertions.IsVisibleOptions().setTimeout(...)` | blocker |
| `waitForResponse` is typed and ordered | `APIResponse r = page.waitForResponse(...)` (it returns `Response`); a wait started after the action instead of `waitForResponse(predicate, action)` | blocker |
| Every test asserts something | `@Test` body ends with an action and no assertion | blocker |
| Web-first assertions used | `assertTrue(locator.isVisible())` / `assertEquals(locator.textContent(), ...)` / `assertEquals(locator.count(), n)` | major |
| Exact HTTP status | `assertThat(response).isOK()` or `assertTrue(response.ok())` in seeding | major |
| Locator ladder | `page.locator("css...")` where a test id or role exists, or in a test class | major |
| No page-level selector or deprecated APIs | `page.click(selector)`, `page.fill(selector)`, `page.innerText(selector)`, `page.type(...)`, `waitForSelector`, `querySelector` / `ElementHandle`, `waitForNavigation` | major |
| Scoped, not positional | `.first()` / `nth()` silencing a strictness error with no reason in the name | major |
| `visible()` over `:visible` | `:visible` in a selector on 1.63+ | minor |
| No sleeps | `page.waitForTimeout(...)` or `Thread.sleep(...)` anywhere. In a `page.route(...)` handler it also stops the Playwright dispatcher for every event — fake latency with CDP throttling (`network-mocking/references/cdp.md`) or a stub-server delay | blocker |
| No `NETWORKIDLE` | `setWaitUntil(WaitUntilState.NETWORKIDLE)` or `waitForLoadState(LoadState.NETWORKIDLE)` | major |
| No `setForce(true)` | `.click(new Locator.ClickOptions().setForce(true))` / same on `fill` / `check` | major |
| No redundant pre-waits | `locator.waitFor()` immediately before `locator.click()` | minor |
| No hand-rolled retry loops | `while (retries-- > 0) { ... Thread.sleep ... }` | major |
| `waitForFunction` not used for plain UI state | `page.waitForFunction("() => ...")` for visible/text checks | minor |
| Positive matchers preferred | `not().isVisible()` where `isHidden()` exists | nit |
| `setExact(true)` for ambiguous names | `getByText("Submit")` matching `Submit Order`, `Submitting…` | minor |
| Auth via storage state | Every test calls `loginPage.signIn(...)` before its real behaviour | major |
| Pages built in the test class | Page objects as `protected` fields of `BaseTest` | minor |

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
| Page objects subclass `BaseAppiumPage` (or project equivalent); a scoped component does not | Extends `AppiumDriver`; a component extends the base page | major |
| Test id first, per platform (iOS `accessibilityId`, Android `id`) → native query → XPath | XPath where an id exists; `accessibilityId` on Android for a React Native `testID` | major |
| `AppiumDriver`, not a raw `WebDriver` field; nothing typed `RemoteWebDriver` | `AppiumDriver<MobileElement>`; a `RemoteWebDriver` cast | major |
| `verifyPageLoaded()` present and asserts a landmark | Missing or empty implementation | major |
| Navigation actions return the destination page object | Navigation method returns `void` | minor |
| Locators are `private static final String {ELEMENT}_ID` constants | Literals inline in action methods; a mix of `String` and `By` constants | minor |
| Platform branching behind the finder | `if (platform.equals("iOS"))` in actions | major |
| App state: a fresh driver, `mobile: clearApp`, or `terminateApp` + `activateApp` | Tests leak data through shared app state | blocker |
| No removed Appium 2 calls | `resetApp`, `closeApp`, `launchApp`, a removed `/appium/*` route | blocker |
| Capabilities from env (`UiAutomator2Options` / `XCUITestOptions`) | `DesiredCapabilities`; a literal `deviceName` in a base | major |
| Gestures via `PointerInput` / `mobile:` gestures | `TouchAction` / `MultiTouchAction` (removed in java-client 11) | major |
| Repeating rows are scoped components, element-scoped finds, re-resolved per call | A row element held across calls; a bare child locator | major |
| `selenium-support` declared for `WebDriverWait` | java-client 11 without it | major |
| No `Thread.sleep` between gestures | `Thread.sleep(1500)` after a swipe waiting for animation | blocker |
| Test names describe user behavior on device, not screen names | `screen1Test`, `tapButton2` | minor |

## Good signals (Java)

- Playwright and Appium: one base test with instance fields under `parallel="classes"`; Selenium: a `ThreadLocal` driver factory
- Locators are `private static final By` or `private final Locator` fields on the highest ladder rung
- One `@Test` per behavior named `Should_X_When_Y`; web-first assertions or `WebDriverWait`, never a sleep
- Components take a parent `WebElement` / `Locator`; a base page only where three pages share real behaviour
- `@DataProvider` for parameterization; Allure `@Step` on non-trivial workflows

## Always-flag anti-patterns

Each is a row above; flag it whatever else the review finds.

- **`OR` in an assertion**, including a `"Saved|Success"` regex inside `hasText(Pattern.compile(...))` — it passes on the wrong state.
- **A test that asserts nothing, or a page object that asserts.**
- **`Thread.sleep` for sync**, and any `try`/`catch` in a `@Test` or a hook body.
- **Static or thread-shared browser state** — `static WebDriver`, `static Playwright`, `parallel="methods"` with Playwright.
- **Any inline comment in a test body or a page-object method**, and any stale comment — rename or extract, never reword.

## Comments in test code

Load **[`engineering-practices/code-comments`](../../../../../engineering-practices/code-comments/SKILL.md)** for the rule, the complex-flow test that earns a doc comment, the trivia list, the severity mapping and its **test-code** section. Here it covers **page-object and screen-object bodies** as well as tests — an intent-revealing method name is the page object's documentation.

| Java mechanic | What to check |
|---|---|
| Doc syntax | Javadoc (`/** … */`) — a doc block on a locator field, or restating `ClickSave`, is trivia |
| Skips needing a reason and a ticket | `@Test(enabled = false)` / `@Ignore` with nothing recorded — a silently disabled test |
| Where an unclear interaction goes instead | Into a named page-object method, not a comment above the locator chain |

**The locator corollary — the one that matters most here.** A comment explaining a locator (`// the third span is the price`) is not a comment finding; it is evidence the locator is **positional and brittle**. Fix the locator: request a `data-testid` and record it in `missing-testids.md`. Cross-reference the finding to the locator-hygiene list rather than filing it as a comment.

## Procedure

1. Identify the **stack** from imports and file location, and read each file end-to-end before writing findings.
2. Walk the cross-stack list, then the stack-specific list.
3. For each finding: file path + line, issue, one-sentence fix. **Do not rewrite the code**; hand off to the matching generator.

## Handoffs

- Need to rewrite → `qa/java/skills/ui-test-author/playwright`, `qa/java/skills/ui-test-author/selenium`, or `qa/java/skills/ui-test-author/appium`
- Architecture is the real problem (not the code) → `qa/java/skills/page-object-design`
- Test data shape is wrong → `qa/java/skills/test-data-builder`
- API tests in the same PR → `qa/java/skills/api-test-author/review`
- Allure reporting questions → `qa/reporting/java/skills/test-reports`
