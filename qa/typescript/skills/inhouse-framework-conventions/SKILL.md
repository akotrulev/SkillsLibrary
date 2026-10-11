---
name: qa-inhouse-framework-conventions-typescript
description: Use when working in the TypeScript Accelerator test automation framework (Node 24 (22 supported) + @playwright/test + WebdriverIO/Appium + Vitest, JSON-driven page objects) or any consumer of it. Triggers: "add a test to the TS Accelerator", "scaffold a screen for the WebdriverIO suite", "create a Playwright page object for X in Accelerator". Not for a suite outside the Accelerator (`qa-page-object-design-typescript`, `qa-ui-test-writer-playwright-typescript`).
---

# Accelerator Conventions (TypeScript)

The Accelerator is a Node 24 + TypeScript (strict mode) test automation framework, organized as a monorepo with workspace packages for `appium-tests`, `playwright-tests`, `api-tests`, and `test-core`. It uses a JSON-driven page object pattern, `@playwright/test` for web and WebdriverIO (Appium service) for mobile, Vitest for API tests, Allure for reporting, BrowserStack for cloud execution, and a two-agent Claude Code workflow (Opus planner + Sonnet implementer).

This skill encodes the conventions that distinguish "Accelerator code" from generic test automation.

## When to use

- The user is adding or modifying code inside the TypeScript Accelerator repo
- The user is consuming Accelerator from another project and asks how to wire it up
- The user wants to know whether a piece of code follows Accelerator conventions

## When NOT to use

- The user wants generic Playwright / WebdriverIO / fetch tutorials → use the generic skills
- The user is starting a brand-new automation framework from scratch (Accelerator might be the wrong choice)

## Project layout

A workspace monorepo (pnpm / npm workspaces). `test-core` is the shared package; each suite is its own package.

```
accelerator/
├── package.json               # workspaces: packages/*
├── tsconfig.base.json         # strict: true, shared compiler options
├── packages/
│   ├── test-core/             # shared abstractions, helpers, base classes
│   │   └── src/
│   │       ├── config/        # env config, BrowserStack creds, run options
│   │       ├── reporting/     # Allure attachments, step helpers
│   │       ├── screens/       # JSON loader, screen/page base class
│   │       └── waits/         # explicit wait helpers
│   ├── api-tests/             # Vitest + fetch + Zod API tests
│   │   └── src/
│   │       ├── clients/       # typed API clients (one per service)
│   │       ├── builders/      # test data factories
│   │       └── tests/         # grouped by service / feature
│   ├── playwright-tests/      # Web UI tests (@playwright/test, fixture-driven)
│   │   └── src/
│   │       ├── pages/         # page objects, one per screen, JSON-driven
│   │       ├── fixtures/      # page-object fixtures
│   │       └── tests/         # grouped by feature (*.spec.ts)
│   └── appium-tests/          # Mobile tests (WebdriverIO + Appium service)
│       └── src/
│           ├── screens/       # screen objects, JSON-driven
│           └── tests/         # grouped by feature
├── screen-definitions/        # *.screen.json files — selectors + metadata (shared by web + mobile)
└── .claude/
    ├── commands/              # planner + implementer slash commands
    └── settings.json
```

## Conventions

### Screen / Page object pattern

Page and screen objects are **JSON-driven**. Selectors live in `*.screen.json` files under `screen-definitions/`, not in code. The page class reads its selectors from the JSON at construction time.

Why: changing a selector doesn't recompile/rebuild. The same JSON can drive both Playwright (web) and WebdriverIO/Appium (mobile) when the screen exists in both contexts.

**Screen JSON example** (`LoginScreen.screen.json`):

```json
{
  "name": "LoginScreen",
  "platforms": {
    "web": {
      "emailInput": "[data-testid='Login.Email']",
      "passwordInput": "[data-testid='Login.Password']",
      "signInButton": "[data-testid='Login.Submit']",
      "errorMessage": "[data-testid='Login.Error']"
    },
    "ios": {
      "emailInput": "//XCUIElementTypeTextField[@name='email']",
      "passwordInput": "//XCUIElementTypeSecureTextField[@name='password']",
      "signInButton": "//XCUIElementTypeButton[@name='Sign in']"
    },
    "android": {
      "emailInput": "//*[@resource-id='com.app:id/email']",
      "passwordInput": "//*[@resource-id='com.app:id/password']",
      "signInButton": "//*[@resource-id='com.app:id/sign_in']"
    }
  }
}
```

**Page class example** (web, Playwright). `PageBase.locator(key)` turns the JSON key into
`this.page.locator(selector)` and throws, naming the screen and the key, when the key is missing. Every action
goes through that **`Locator`** — `locator.fill()`, `locator.click()` — never the page-level selector methods
(`page.fill(selector)`, `page.click(selector)`, `page.innerText(selector)`), which Playwright discourages: a
locator auto-waits, is strict about matching one element, and shows its name in the trace. State the test
asserts on is exposed as a `Locator`, so the assertion is web-first and retries; a `Promise<string>` getter
invites a one-shot read that races the page.

```typescript
import type { Locator, Page } from '@playwright/test';
import type { Credentials } from '../builders/user-builder';
import { PageBase } from '@accelerator/test-core';

export class LoginPage extends PageBase {
  readonly errorMessage: Locator;

  constructor(page: Page) {
    super(page, 'LoginScreen');
    this.errorMessage = this.locator('errorMessage');
  }

  async goTo(): Promise<void> {
    await this.page.goto('/login');
  }

  async signIn(user: Credentials): Promise<void> {
    await this.locator('emailInput').fill(user.email);
    await this.locator('passwordInput').fill(user.password);
    await this.locator('signInButton').click();
  }
}
```

Page objects are exposed as **Playwright fixtures**, never constructed manually in every test:

```typescript
export const test = base.extend<{ loginPage: LoginPage }>({
  loginPage: async ({ page }, use) => { await use(new LoginPage(page)); },
});
```

Rules:
- **No literal selectors in page methods.** Always go through `this.selector("key")`.
- **Method names describe user intent**, not mechanics. `signIn`, not `clickSignInButton`.
- **One page object per screen.** Composite flows live in test code or in flow helpers, not in page objects.
- **No assertions inside page objects.** They expose state; tests assert.
- **Locators in JSON are `data-testid`-first for web** — `data-testid` is the standing contract with the dev team.

### Test structure

```typescript
test.describe('Authentication › Login', () => {
  test('Should_ShowDashboard_When_CredentialsAreValid', async ({ loginPage, dashboardPage, registeredUser }) => {
    await loginPage.goTo();

    await loginPage.signIn(registeredUser);

    await expect(dashboardPage.heading).toBeVisible();
  });

  test('Should_ShowError_When_PasswordIsWrong', async ({ loginPage, registeredUser }) => {
    await loginPage.goTo();

    await loginPage.signIn(aValidUser().withEmail(registeredUser.email).withPassword('Wrong-Passw0rd!').build());

    await expect(loginPage.errorMessage).toHaveText('Invalid email or password');
  });
});
```

`registeredUser` is a fixture that creates the user through the API client and deletes it in its teardown, so
every test owns its data.

Rules:
- One spec file per feature or screen, not per AC
- Test names are `Should_<Outcome>_When_<Condition>`
- Three-section body: Arrange / Act / Assert — single blank line between, no comments needed
- Test data via builders/factories (`aValidUser().build()`), never inline literals
- One logical assertion per test
- `strict: true` — no `any`; page objects and builders are fully typed

### Test data builders

Every domain object gets a builder/factory. They:

- Live in `*-tests/src/builders/`
- Use the `a<Name>` / `an<Name>` naming for the fluent entry: `aValidUser()`, `anOrderWith(...)`
- Provide sensible defaults — calling `.build()` with no chained methods produces a valid object
- Return `this` from each `with*` method for fluent chaining

```typescript
export class UserBuilder {
  private email = `user-${crypto.randomUUID()}@test.local`;
  private password = 'Valid123!';
  private yearsActive = 1;

  withEmail(email: string): this { this.email = email; return this; }
  withPassword(password: string): this { this.password = password; return this; }
  withYearsActive(years: number): this { this.yearsActive = years; return this; }
  build(): User { return { email: this.email, password: this.password, yearsActive: this.yearsActive }; }
}

export const aValidUser = (): UserBuilder => new UserBuilder();
```

### Waits

- **Never** use `page.waitForTimeout(...)`, `browser.pause(...)`, or `setTimeout`-based sleeps in test code
- Use Playwright's auto-waiting (`locator.click()`, `locator.fill()`, `expect(locator).toBeVisible()`)
- For WebdriverIO/Appium, use the helpers in `test-core` `waits` — `waitUntilVisible`, `waitUntilStable` (backed by `waitUntil`, never fixed pauses)
- If you need a wait that doesn't exist, add it to `test-core` `waits`, don't inline it

### Allure reporting

- Tag every test with at least suite / feature / story metadata — `await allure.epic(...)`, `await allure.feature(...)`, `await allure.story(...)` from `import * as allure from 'allure-js-commons'` (never the deprecated `allure` export of `allure-playwright`), or the `@playwright/test` `{ tag }` details the reporter maps
- Failure evidence on the web suite is the Playwright config's defaults — trace and video `retain-on-failure`, a full-page screenshot `only-on-failure` (`qa/typescript/skills/evidence-capture`) — not a hand-written `afterEach`; the mobile suite's evidence hook belongs to `qa/typescript/skills/ui-test-author/appium`
- Page object methods wrap their actions in an awaited `test.step(...)` (Playwright) so steps appear in the trace, the HTML report and the Allure tree

### API tests

- One typed client per service in `api-tests/src/clients/`
- Clients return strongly typed responses validated with **Zod**, not untyped `Response` bodies
- Test data via builders, same convention as UI
- Contract tests (Pact) run before integration tests in the pipeline

### Configuration & environments

- All config lives in env-specific files loaded by the `config` helper in `test-core` (`.env`, `.env.staging`), parsed/validated at startup
- BrowserStack creds, base URLs, and feature flags come from env vars
- Never commit `.env` files; commit `.env.example` only

### Claude Code workflow

The Accelerator uses a two-agent pattern:

- **Planner** (Opus): reads the task, produces a numbered plan with files to create/modify and a verification step. Does not write code.
- **Implementer** (Sonnet): executes the plan, one step at a time. After each step, runs the relevant tests (`pnpm --filter playwright-tests test`).

Slash commands:
- `/plan <task>` — invokes the planner
- `/implement` — invokes the implementer against the last plan
- `/review` — invokes a reviewer pass against the current branch

When rate-limited on one model, switch to another (Opus → Sonnet → Haiku) — the workflow is designed to degrade gracefully.

## Quality bar (reviewer checklist)

- [ ] No literal selectors in page/screen methods; actions go through `Locator`s, never `page.fill/click/innerText(selector)`
- [ ] No `waitForTimeout` / `browser.pause` / `setTimeout` sleeps in tests
- [ ] Test name is `Should_X_When_Y`
- [ ] Test data via a builder
- [ ] Allure metadata present
- [ ] One logical assertion per test
- [ ] Page object methods describe intent, not mechanics
- [ ] Builders provide valid defaults
- [ ] No conditional logic in tests (`if`, `for` driving assertions) — use parameterized tests
- [ ] No `any`; everything typed under `strict`
- [ ] Tests are independent and order-agnostic

## Anti-examples

| Anti-example | Why it's wrong | Instead |
|---|---|---|
| `await this.page.click('button.signin-btn')` in a page object | A selector in code, and a page-level selector method | `this.locator('signInButton').click()` with the selector in `*.screen.json` |
| `getErrorMessage(): Promise<string>` read once, then `expect(text).toBe(...)` | A one-shot read races the page | expose `errorMessage: Locator`; `await expect(loginPage.errorMessage).toHaveText(...)` |
| `await page.waitForTimeout(2000)` | A sleep | auto-wait, web-first assertions, `test-core` `waits` |
| `test('clicks the login button', ...)` | Names the mechanics, not the behaviour | `Should_ShowDashboard_When_CredentialsAreValid` |
| `await loginPage.signIn({ email: 'user@test.com', password: 'Password1!' })` | Inline test data | a builder: `aValidUser().build()` or a fixture-created user |
| `if (env === 'staging') { ... } else { ... }` in a test | Conditional logic in a test | a parameterized test or a fixture per environment |
| `const body: any = await res.json()` | An untyped escape hatch | parse with the Zod schema |
