---
name: qa-ui-test-author-reviewer-typescript
description: Use when the user asks to review existing TypeScript UI test code or page objects. Triggers: "review this Playwright spec", "look at this page object class", "is this WebdriverIO test any good". For end-to-end suite work prefer the phased agent `qa-ui-typescript` / `qa-mobile-typescript` / `qa-bdd-typescript` (or the matching slash command), which loads this skill inside its workflow; use this skill directly for a single targeted artifact.
---

# QA — UI Test & Page Object Reviewer (TypeScript)

Reviews TypeScript UI test code (Playwright TS, Selenium WebDriverJS / WebdriverIO, Appium TS) against the patterns enforced by the matching generator skills. Produces a findings table in the format defined in `CLAUDE.md`. **Does not rewrite the code** — points to the fix and lets the human apply it.

## When to use

- A diff or file (page object, `.spec.ts`, fixture, `BasePage`) is submitted for review
- Pre-merge gate on a PR touching `tests/`, `e2e/`, `pages/`, or `pageObjects/`
- Second opinion on whether a TypeScript page object is well-structured

## When NOT to use

- Generating new code → `qa/typescript/skills/ui-test-author/playwright`, `qa/typescript/skills/ui-test-author/selenium`, `qa/typescript/skills/ui-test-author/appium`
- Architecting the POM → `qa/typescript/skills/page-object-architect`
- Reviewing API tests → `qa/typescript/skills/api-test-author/reviewer`
- Reviewing .NET UI code → `qa/dotnet/skills/ui-test-author/reviewer`
- Reviewing Java UI code → `qa/java/skills/ui-test-author/reviewer`

## Inputs needed

1. **Stack** — Playwright TS, Selenium WebDriverJS / WebdriverIO TS, or WebdriverIO + Appium TS
2. **Files** to review (page objects, `*.spec.ts`, fixtures, base classes)
3. **Context** — new feature, refactor, or bug fix?
4. **Project conventions** — anything overriding the stack defaults (e.g. project requires `getByRole` only, forbids `page.locator('css')`, mandates `eslint-plugin-playwright`)

## Output format

```
| Severity | Location                            | Issue                                              | Suggested fix                                              |
|----------|-------------------------------------|----------------------------------------------------|------------------------------------------------------------|
| blocker  | tests/specs/cart.spec.ts:42         | `page.waitForTimeout(2000)` — arbitrary sleep      | Replace with `expect(loc).toBeVisible()` auto-wait         |
| blocker  | pages/LoginPage.ts:18               | `expect` inside page object method                 | Move assertion to the spec                                 |
| major    | pages/ProductPage.ts:31             | `page.locator('.btn-primary')` where button has role+name | Use `page.getByRole('button', { name: 'Sign in' })` |
| minor    | pages/CartPage.ts:55                | Inline `page.locator('[data-test="...”]')` repeated | Promote to `readonly cartBadge: Locator` in constructor    |
```

Severities (from `CLAUDE.md`):

- **blocker** — ships a bug, breaks the build, or violates a hard rule (`waitForTimeout`, `expect` in page objects, shared driver, raw credentials)
- **major** — design or correctness issue that will hurt soon (brittle locators, `force: true`, `networkidle` waits)
- **minor** — style or small inconsistency (naming, missing constant)
- **nit** — optional preference

**Do not rewrite the code during review.** If the user wants a rewrite, hand off to the matching generator.

## Cross-stack smells (apply to every TypeScript UI review)

| Check | Bad sign | Severity |
|---|---|---|
| Strict TypeScript honored | `strict: true` disabled in tsconfig, scattered `any`, `as unknown as X` casts | major |
| No `waitForTimeout` / `browser.pause` / `setTimeout` as UI sync | Any literal millisecond sleep | blocker |
| Locators are semantic | Raw CSS / XPath where role/label/`testID`/`data-test` exists | major |
| Assertions live in tests, not page objects | `expect(...)` inside page action methods | blocker |
| No business logic in page objects | Price calculation, JSON parsing, branching on app state inside POM | major |
| Tests are independent | Test B depends on data created by Test A; `test.describe.serial` (Playwright) chaining setup across tests | blocker |
| One logical behavior per test | One `test(...)` verifies login + cart + checkout | major |
| Test names describe behavior | `test1`, `'login test'`, `'click button'` | minor |
| No hardcoded credentials / base URLs | Literal `admin@example.com`, hardcoded `https://staging.x.y` | major |
| Locators promoted to `readonly Locator` fields / module constants | Inline locator strings re-typed across methods | minor |
| No conditional logic driving assertions | `if (x) expect(...)` instead of parameterized cases / `test.each` | major |
| `test.each` / parameterized cases for data-driven tests, not `for` loops in `test(...)` | Loop-driven multi-case test that hides which case failed | major |
| No floating promises | `async` function calls without `await` (or `await`-less `expect`) | blocker |
| ESLint configured for the stack | `eslint-plugin-playwright` / `wdio` plugin missing | nit |

## Playwright / TypeScript smells

| Check | Bad sign | Severity |
|---|---|---|
| Every test asserts something | `test(...)` body ends with an action and no `expect` | blocker |
| Web-first assertions used | `expect(await loc.isVisible()).toBe(true)` / `expect(await loc.textContent()).toBe(...)` / `expect(await loc.count()).toBe(n)` | major |
| `getByRole` / `getByLabel` / `getByTestId` preferred | `page.locator('css...')` in spec files | major |
| Locators are `readonly Locator` fields initialized in constructor | Functions that return `page.locator(...)` per call | minor |
| No hardcoded sleeps | `page.waitForTimeout(...)` anywhere | blocker |
| No `{ waitUntil: 'networkidle' }` | `goto(url, { waitUntil: 'networkidle' })` | major |
| No `{ force: true }` to bypass actionability | `.click({ force: true })` / `.fill(..., { force: true })` | major |
| No redundant pre-waits before auto-waiting actions | `loc.waitFor({ state: 'visible' })` immediately before `loc.click()` | minor |
| `waitForResponse` ordering correct | `await page.waitForResponse(...)` placed before the triggering action, or set up after the action (race) | major |
| Custom retry loops replaced by `toPass` / `expect.poll` | `while (retries--) { … waitForTimeout … }` | major |
| `toPass` inner assertions have short explicit timeouts | `expect(loc).toHaveText(...)` inside `toPass` with no `{ timeout }` | minor |
| `expect.poll` not used for plain DOM checks | `expect.poll(() => loc.textContent()).toBe('x')` where `toHaveText` would do | minor |
| `waitForFunction` not used for plain UI state | `page.waitForFunction(() => document.querySelector(...))` for visible/text checks | minor |
| Deprecated APIs removed | `page.waitForNavigation(...)` in code | major |
| Positive matchers preferred over `.not` | `.not.toBeVisible()` where `toBeHidden()` exists | nit |
| `{ exact: true }` set for ambiguous text/role names | `getByText('Submit')` matching multiple labels (`Submit Order`, `Submitting…`) | minor |
| No serial-dependent tests | `test.describe.serial(...)` chaining setup across tests | major |
| Auth via `storageState`, not per-test login | Every test calls `loginPage.signIn(...)` | major |
| `expectLoaded()` exists on every page object | No landmark assertion method | minor |
| Tests destructure fixtures, no manual `new SomePage(page)` | Spec instantiates page objects directly | minor |
| `test.step('...')` used for non-trivial workflows | A test with 12 actions and no step labels | nit |
| `eslint-plugin-playwright` configured | `eslint.config.*` has no playwright plugin entry | nit |
| Trace / video config set in `playwright.config.ts` | `use: { trace: 'on' }` in production CI (perf cost) — should be `'retain-on-failure'` | minor |

## Selenium WebDriverJS / WebdriverIO (TS) smells

| Check | Bad sign | Severity |
|---|---|---|
| Page objects extend a thin `BasePage` | Pages calling `browser.$(...)` / `driver.findElement(...)` directly without a base abstraction | major |
| Locator preference order (`data-test` → id → css → xpath) honored | XPath used where `data-test` exists | major |
| Component classes scoped to a parent element for repeating items | One giant page object that re-queries the DOM for every card | major |
| WebdriverIO async API only (v8+) | `browser.$(...).click()` synchronous usage (sync mode removed in v8) | blocker |
| No `browser.pause(...)` | `browser.pause(2000)` used as sync | blocker |
| `waitForDisplayed` / `waitForClickable` / `waitForExist` for conditional waits | `setTimeout` / `browser.pause` for synchronization | blocker |
| Multi-step flows live in sub-folders (`pages/checkout/`) | Flat `pages/` with 30 unrelated files | minor |
| Navigation methods return the destination page object | Navigation method returns `void`; spec instantiates the next page | minor |
| `browser.execute` not used to click around actionability | `browser.execute('arguments[0].click()', el)` workaround | major |
| Element getters return the element / chainable, not pre-asserted booleans | `async isLoginButtonVisible(): boolean` returning the assertion | minor |
| `expect` from `@wdio/globals` for chai-style web-first assertions | Mixing `chai.expect` with `wdio`-native matchers inconsistently | minor |

## Appium / WebdriverIO TS smells

| Check | Bad sign | Severity |
|---|---|---|
| Page objects subclass `BaseMobilePage` (or project equivalent) | Class extends `Browser` / `WebdriverIO.Browser` directly | major |
| Accessibility ID first (`~accessibilityId`) → id → xpath | XPath used where `accessibilityIdentifier` / `contentDescription` exists | major |
| `WebdriverIO.Element` returned by accessors — strongly typed | Page returns `any` or untyped `unknown` | minor |
| `verifyPageLoaded()` present and asserts a landmark | Missing or empty implementation | major |
| Navigation actions return the destination page object | Navigation method returns `void` | minor |
| Locator strings declared as `private readonly` class fields or module constants | Locator literals inline in action methods | minor |
| Platform branching abstracted behind a strategy / locator map | `if (driver.isIOS) … else …` scattered across pages | major |
| App state reset between tests (`driver.reset()` / fresh install / `noReset:false`) | Tests leak data into each other through shared app state | blocker |
| Capabilities loaded from `wdio.conf.ts` env-driven config, not hardcoded inline | Literal `deviceName: 'Pixel_6'` hardcoded in spec | major |
| Gestures via W3C Actions / `driver.execute('mobile: ...')` (Appium 2.x) | Deprecated `TouchAction` calls | major |
| No `browser.pause` between gestures | `browser.pause(1500)` after a swipe waiting for animation | blocker |
| Test names describe user behavior on device | `'screen1Test'`, `'tap button 2'` | minor |

## Good signals (TypeScript)

Code that looks well-written in this stack tends to share these traits:

- `tsconfig.json` has `"strict": true` (and at minimum `noImplicitAny`, `strictNullChecks`)
- Page objects expose intent-revealing methods (`signIn`, `addProductToCart`) and return the next page object on navigation
- Locators are `readonly Locator` fields initialized in the constructor — not inline magic strings
- One `test(...)` per behavior with a descriptive title, no `test.describe.serial(...)` chains
- Tests destructure custom fixtures (`test.extend<...>`) instead of `new SomePage(page)` in the spec body
- Web-first assertions (`expect(locator).toHave...`) used everywhere; no one-shot `expect(await ...)` checks
- `getByRole` / `getByLabel` / `getByTestId` preferred — semantic selectors over CSS / XPath
- Auth handled via `storageState` (Playwright) or a per-suite seeded session (WebdriverIO)
- `test.each` / parameterized data for multi-case scenarios; failure message identifies which case failed
- `playwright.config.ts` sets `trace: 'retain-on-failure'`, `video: 'retain-on-failure'`, project-level browser matrix
- `eslint-plugin-playwright` (or `eslint-plugin-wdio`) enforces no-`waitForTimeout`, no-`force`, web-first-assertions rules
- No floating promises; ESLint `no-floating-promises` enabled

## Always-flag anti-patterns

- **Test that asserts nothing.** A spec that ends after a `click()` with no `expect` is not a test.
- **`expect` inside a page object.** Always a blocker — moves assertion ownership away from the test.
- **`waitForTimeout` / `browser.pause` / `setTimeout` for UI sync.** Always a blocker, regardless of duration.
- **`{ force: true }` / `{ waitUntil: 'networkidle' }`.** Both bypass Playwright's actionability/loading guarantees — fix the locator or wait condition instead.
- **Floating promises.** Missing `await` on `expect` or page actions silently passes tests.
- **Brittle locator chain.** `page.locator('div > div > span:nth-child(3) > a')` will break on the next DOM tweak.
- **Login-in-every-test.** Use `storageState` (Playwright) or per-suite seeded session.
- **`try/catch` wrapping the whole test body.** Hides failures. Cleanup belongs in fixtures/teardown.
- **`any` / `as unknown as X` casts in fixtures or page object types.** Defeats the purpose of TS strict mode.
- **Comments that restate what the code does** (`// click login`). Comment the *why*.

## Procedure

1. Identify the **stack** (Playwright / WebdriverIO / WebdriverIO+Appium) from imports and config files.
2. Read the file end-to-end before writing findings — context matters for severity.
3. Walk the cross-stack list, then the stack-specific list.
4. For each finding, capture: file path + line, issue, one-sentence suggested fix.
5. **Do not rewrite the code.** Hand off to the matching generator if the user asks for a rewrite.

## Handoffs

- Need to rewrite → `qa/typescript/skills/ui-test-author/playwright`, `qa/typescript/skills/ui-test-author/selenium`, or `qa/typescript/skills/ui-test-author/appium`
- Architecture is the real problem (not the code) → `qa/typescript/skills/page-object-architect`
- Test data shape is wrong → `qa/typescript/skills/test-data-builder`
- API tests in the same PR → `qa/typescript/skills/api-test-author/reviewer`
- Allure reporting questions → `qa/reporting/typescript/skills/allure-reporting`
