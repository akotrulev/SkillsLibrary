---
name: qa-ui-test-review-typescript
description: Use when the user asks to review existing TypeScript UI test code or page objects. Triggers: "review this Playwright spec", "look at this page object class", "is this WebdriverIO test any good". Do NOT use for writing new tests (`qa-ui-test-writer-playwright-typescript`) or reviewing a Gherkin layer (`qa-bdd-reviewer-typescript`).
---

# QA — UI Test & Page Object Reviewer (TypeScript)

Reviews TypeScript UI test code (Playwright Test, Selenium WebDriverJS / WebdriverIO, Appium with
WebdriverIO) against the patterns the matching generator skills enforce. Produces a findings table in the
`CLAUDE.md` format. **Does not rewrite the code** — it points to the fix and lets the human apply it.

The Playwright rules it checks against are owned by `qa/typescript/skills/ui-test-author/playwright`:
locators in `references/locators.md`, assertions in `references/assertions.md`, the config in
`references/config-and-fixtures.md`.

## When to use

- A diff or file (page object, `.spec.ts`, fixture, config, base class) is submitted for review
- Pre-merge gate on a PR touching `tests/`, `e2e/`, `pages/` or `pageObjects/`
- A second opinion on whether a TypeScript page object is well structured

## When NOT to use

- Generating new code → `qa/typescript/skills/ui-test-author/playwright`, `…/selenium`, `…/appium`
- Architecting the POM → `qa/typescript/skills/page-object-design`
- API tests → `qa/typescript/skills/api-test-author/review`
- .NET or Java UI code → `qa/dotnet/skills/ui-test-author/review`, `qa/java/skills/ui-test-author/review`

## Inputs needed

1. **Stack** — Playwright TS, Selenium WebDriverJS / WebdriverIO, or WebdriverIO + Appium
2. **Files** — page objects, `*.spec.ts`, fixtures, `playwright.config.ts`, base classes
3. **Context** — new feature, refactor or bug fix
4. **Project conventions** that override the stack defaults (a different test-id attribute, a mandated lint plugin)

## Output format

```
| Severity | Location                    | Issue                                              | Suggested fix                                         |
|----------|-----------------------------|----------------------------------------------------|-------------------------------------------------------|
| blocker  | tests/specs/cart.spec.ts:42 | `page.waitForTimeout(2000)` — arbitrary sleep      | Assert the state: `await expect(cart.total).toHaveText('€40.00')` |
| blocker  | pages/LoginPage.ts:18       | `expect` inside a page-object method               | Expose the locator; assert in the spec                |
| major    | pages/ProductPage.ts:31     | `page.locator('.btn-primary')` on an element with a test id | `page.getByTestId('Product.AddToCart')`       |
| minor    | pages/CartPage.ts:55        | The same locator re-typed in three methods         | Promote to a `readonly cartBadge: Locator` field      |
```

Severities (from `CLAUDE.md`):

- **blocker** — ships a bug, breaks the build, or violates a hard rule (`waitForTimeout`, `expect` in page objects, shared driver, raw credentials, floating promises)
- **major** — a design or correctness issue that will hurt soon (brittle or unscoped locators, `force: true`, `networkidle`, one-shot reads)
- **minor** — style or a small inconsistency (naming, a missing constant)
- **nit** — optional preference

**Do not rewrite the code during review.** If the user wants a rewrite, hand off to the matching generator.

## Cross-stack smells (every TypeScript UI review)

| Check | Bad sign | Severity |
|---|---|---|
| Strict TypeScript honoured | `strict: true` off, scattered `any`, `as unknown as X` casts | major |
| No sleeps as UI sync | `waitForTimeout`, `browser.pause`, `setTimeout` — any duration | blocker |
| Locators follow the ladder (test id → role → label → placeholder → text → alt/title → CSS) | Raw CSS / XPath, or a role locator, where a test id exists | major |
| Test ids are PascalCase dot-separated and static | `login-submit`, `order-row-42`, an index or a GUID in the id | minor |
| Fallback locators carry no marker | A `// TODO: missing data-testid` comment instead of a `missing-testids.md` row | minor |
| Assertions live in tests, not page objects | `expect(...)` in a page-object action | blocker |
| No business logic in page objects | Price maths, JSON parsing, branching on app state | major |
| Tests are independent | Test B relies on Test A's data; `test.describe.serial` chaining | blocker |
| One logical behaviour per test | One test covers login + cart + checkout | major |
| No `try` / `catch` / `finally` in a test or cleanup hook | Any catch in a test; `.catch(() => {})` on an action | major |
| Failures identify the subject | Assertions with no message, so a failure cannot be told from a bad locator | minor |
| One expected condition per assertion | `expect([a, b]).toContain(x)`, `\|\|` in an `expect`, `/a\|b/` in `toHaveText` / `toHaveURL`, an assertion on an `or()` locator | major |
| Test names are `Should_X_When_Y` | `test1`, `'login test'`, `'click button'` | minor |
| Tags in the details object | `test('@smoke signs in', …)` instead of `{ tag: '@smoke' }` | nit |
| No hardcoded credentials or base URLs | Literal `admin@example.com`, `https://staging.x.y` | major |
| Locators promoted to `readonly` fields | Locator strings re-typed across methods | minor |
| No conditional logic driving assertions | `if (x) expect(...)` | major |
| Data-driven cases generate one `test()` per row | A `for` loop of assertions inside one `test()`, or `test.each` (Playwright Test has none) | major |
| No floating promises | An un-awaited action, `expect` or Allure call | blocker |
| No unearned base class | A `BasePage` / `BaseMobilePage` with fewer than three real sharers, or one that only forwards | major |
| Lint configured | `eslint-plugin-playwright` / `eslint-plugin-wdio` missing; no `no-floating-promises` | nit |

## Playwright / TypeScript smells

| Check | Bad sign | Severity |
|---|---|---|
| Every test asserts something | The body ends with an action and no `expect` | blocker |
| Web-first assertions, no one-shot reads | `expect(await loc.isVisible()).toBe(true)`, `textContent()`, `inputValue()`, `count()`, `getAttribute()`, `expect(page.url())` | major |
| Exact status on API calls in fixtures | `expect(res.ok()).toBeTruthy()`, `toBeOK()` | minor |
| No raw `page.` calls in specs | `page.locator(...)`, `page.goto(...)` in a spec file | major |
| No page-level selector APIs | `page.click(sel)`, `page.fill(sel)`, `page.innerText(sel)`, `page.$(sel)` — discouraged; use locators | major |
| Locators scoped, not left to match many | `page.getByText('Delete')` or `getByRole('alert')` hitting several elements | major |
| No positional picks without a reason | `.nth(2)` / `.first()` that silences strictness; the name does not say why order matters | major |
| `visible()` instead of `:visible` | `locator('button:visible')` on 1.63+ | minor |
| `exact: true` on ambiguous names | `getByText('Submit')` matching `Submit order` | minor |
| Overlays handled by `addLocatorHandler` | `if (await banner.isVisible()) await close()` | major |
| Locators are `readonly` fields | Functions that return `page.locator(...)` per call | minor |
| No `{ waitUntil: 'networkidle' }` | `goto(url, { waitUntil: 'networkidle' })` | major |
| No `{ force: true }` | `.click({ force: true })`, `.fill(..., { force: true })` | major |
| No redundant pre-waits | `loc.waitFor()` right before `loc.click()` | minor |
| `waitForResponse` ordered | Awaited before the triggering action, or created after it | major |
| No hand-rolled retry loops | `while (retries--) { … }` instead of `toPass` / `expect.poll` | major |
| `toPass` bounded | No `timeout` on `toPass`, or inner assertions without a short `{ timeout }` | minor |
| `expect.poll` / `waitForFunction` not used for DOM state | `expect.poll(() => loc.textContent())` where `toHaveText` works | minor |
| Deprecated APIs gone | `page.waitForNavigation(...)` | major |
| Positive matchers | `.not.toBeVisible()` where `toBeHidden()` exists | nit |
| Auth through a setup project | Every test calls `loginPage.signIn(...)`; `globalSetup` where a setup project fits | major |
| Page objects come from fixtures | A spec calls `new SomePage(page)` | minor |
| Seeded data cleaned in fixture teardown | Records created in a test and never deleted, or deleted in the test body | major |
| Failure evidence configured | `trace` / `video` not `'retain-on-failure'` — `'on-first-retry'` with `retries: 0` records nothing; `'on'` on CI costs every run | minor |
| HAR recorded through a valid option | `test.use({ recordHar })` — not a test option; use `contextOptions: { recordHar }` or `context.tracing.startHar()` (1.60) | major |
| Allure calls awaited, from `allure-js-commons` | `allure.attachment(...)` without `await`; `import { allure } from 'allure-playwright'` (deprecated) | blocker |
| `test.step` labels long journeys | Twelve actions and no steps | nit |

## Selenium WebDriverJS / WebdriverIO (TS) smells

| Check | Bad sign | Severity |
|---|---|---|
| Locator order: `data-testid` (or the project's test-id attribute) → id → CSS → XPath | XPath where a test id exists | major |
| Components scoped to a parent element for repeating items | One page object re-querying the DOM for every card | major |
| WebdriverIO async API only (v8+) | Synchronous `browser.$(...).click()` | blocker |
| No `browser.pause(...)` | `browser.pause(2000)` as sync | blocker |
| Conditional waits | `setTimeout` / `browser.pause` instead of `waitForDisplayed` / `waitForClickable` / `waitForExist` | blocker |
| Multi-step flows in sub-folders (`pages/checkout/`) | A flat `pages/` with 30 unrelated files | minor |
| Navigation returns the destination page object | Returns `void`; the spec builds the next page | minor |
| No `browser.execute` around actionability | `browser.execute('arguments[0].click()', el)` | major |
| Getters return the element, not a pre-asserted boolean | `async isLoginButtonVisible(): boolean` | minor |
| One assertion library | `chai.expect` mixed with `@wdio/globals` `expect` | minor |

## Appium / WebdriverIO TS smells

| Check | Bad sign | Severity |
|---|---|---|
| Screen objects share behaviour by composition | A `BasePage` with fewer than three real sharers; a class extending `WebdriverIO.Browser`; a scoped component that extends `BasePage` | major |
| Test id first, per platform (iOS `~id`, Android `id=`) → native query → XPath | XPath where an `accessibilityIdentifier` or a `resource-id` exists; `~id` on Android for a React Native `testID` | major |
| Typed element accessors | A page returns `any` or `unknown` | minor |
| `verifyPageLoaded()` asserts a landmark | Missing or empty | major |
| Navigation returns the destination screen object | Returns `void` | minor |
| Locator strings are `private static readonly` constants | Literals inline in action methods | minor |
| Platform branching behind a locator map | `if (browser.isIOS) … else …` across pages or actions | major |
| App state between tests: a fresh session, `mobile: clearApp`, or `terminateApp` + `activateApp` | Tests leak data through shared app state | blocker |
| No removed Appium 2 calls | `driver.reset()`, `resetApp`, `closeApp`, or a hand-rolled call to a removed `/appium/*` route | blocker |
| Capabilities from an env-driven `wdio.conf.ts`, with the `appium:` prefix | `deviceName: 'Pixel_6'` hardcoded in a spec; an unprefixed `automationName` | major |
| Gestures via `tap` / `swipe` / `browser.action('pointer')` / `mobile:` | `touchAction`, which WDIO 10 removed | major |
| Repeating rows are scoped components that re-resolve on every call | A row element held across calls, or a bare child selector that matches in every row | major |
| WDIO 10 `$` left strict | `{ strict: false }` or `strictSelectors: false` to silence a `StrictSelectorError` | major |
| Mocha (or Cucumber) is the runner | Vitest or Jest specs under `wdio run` | major |
| `isElementVisible` returns `false` on a timeout | A "visible" helper that only returns `true` or throws | minor |
| Clipboard content is base64 | `setClipboard('text', 'plaintext')` | major |
| Failure evidence comes from `BaseTest`'s `afterTest` | A spec with its own screenshot hook, or no evidence on failure | major |
| No `browser.pause` between gestures | `browser.pause(1500)` after a swipe | blocker |
| Test names describe behaviour on the device | `'screen1Test'`, `'tap button 2'` | minor |

## Good signals (TypeScript)

The shape of `qa/typescript/skills/ui-test-author/playwright/assets/`: intent-revealing page methods,
components that take their root `Locator`, scoped `readonly` locators on the highest ladder rung,
`Should_X_When_Y` tests on fixtures with `{ tag }`, web-first assertions with a subject, a setup project
for auth, seeded data deleted in fixture teardown, and the canonical config.

## Always-flag anti-patterns

- **An `OR` in an assertion** — `toContain` over candidates, `||`, a `/a|b/` alternation, an `or()`
  locator. It passes on the wrong state. Split per outcome, generate a test per row, or pin the value.
- **A test that asserts nothing**; **`expect` inside a page object**; **login in every test**.
- **Sleeps**, **`force: true`**, **`networkidle`**, and **floating promises** (Allure calls included).
- **A brittle or positional chain** — `div > div > span:nth-child(3) > a`, an unexplained `.first()`.
- **Any `try` / `catch` in a test or a cleanup hook.** An expected rejection is `await expect(...).rejects`;
  cleanup is fixture teardown. The only catches belong in I/O helpers narrowing one named error.
- **A failure message that names no subject**; **`any` / `as unknown as X`** in fixtures or page objects.
- **Any inline comment** in a test body or page-object method, and any stale comment (`ep-code-comments`).

## Comments in test code

Load **[`ep-code-comments`](../../../../../engineering-practices/code-comments/SKILL.md)** for the rule, the
complex-flow test that earns a doc comment, the trivia list and the severity mapping. Its **test-code**
section carries the AAA-banner rule and the three permitted comments. Here it also covers page-object and
screen-object bodies: an intent-revealing method name is the page object's documentation.

| TypeScript mechanic | What to check |
|---|---|
| Doc syntax | TSDoc (`/** … */`); a doc block on a locator field, or restating `clickSave`, is trivia |
| Skips need a reason and a ticket | A bare `test.skip(...)` / `.fixme` |
| Suppressions need a reason | `@ts-expect-error` / `eslint-disable` in a fixture or page-object type |
| Where an unclear interaction goes instead | A named page-object method, not a comment above the chain |

**The locator corollary.** A comment explaining a locator (`// the third span is the price`) is evidence
the locator is **positional and brittle**, not a comment finding. File it under the locator rows: request a
test id and record it in `missing-testids.md`.

## Procedure

1. Identify the **stack** from imports and config files, and the Playwright version from `package.json`.
2. Read each file end to end before writing findings — context sets severity.
3. Walk the cross-stack list, then the stack-specific list.
4. For each finding: file and line, issue, a one-sentence fix.
5. **Do not rewrite the code.** Hand off to the generator if the user asks for a rewrite.

## Handoffs

- Rewrite → `qa/typescript/skills/ui-test-author/playwright`, `…/selenium` or `…/appium`
- Architecture is the real problem → `qa/typescript/skills/page-object-design`
- Test data shape → `qa/typescript/skills/test-data-builder`
- API tests in the same PR → `qa/typescript/skills/api-test-author/review`
- Evidence settings beyond the config defaults → `qa/typescript/skills/evidence-capture`
- Allure reporting → `qa/reporting/typescript/skills/test-reports`
