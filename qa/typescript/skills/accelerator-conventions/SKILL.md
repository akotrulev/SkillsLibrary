---
name: qa-accelerator-conventions-typescript
description: Use when working in the TypeScript Accelerator test automation framework (Node 24 (22 supported) + @playwright/test + WebdriverIO/Appium + Vitest, JSON-driven page objects) or any consumer of it. Triggers: "add a test to the TS Accelerator", "scaffold a screen for the WebdriverIO suite", "create a Playwright page object for X in Accelerator".
---

# Accelerator Conventions (TypeScript)

The Accelerator is a Node 20 + TypeScript (strict mode) test automation framework, organized as a monorepo with workspace packages for `appium-tests`, `playwright-tests`, `api-tests`, and `test-core`. It uses a JSON-driven page object pattern, `@playwright/test` for web and WebdriverIO (Appium service) for mobile, Vitest for API tests, Allure for reporting, BrowserStack for cloud execution, and a two-agent Claude Code workflow (Opus planner + Sonnet implementer).

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
      "emailInput": "[data-testid='email']",
      "passwordInput": "[data-testid='password']",
      "signInButton": "[data-testid='sign-in']",
      "errorMessage": "[data-testid='login-error']"
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

**Page class example** (web, Playwright):

```typescript
export class LoginPage extends PageBase {
  constructor(page: Page) {
    super(page, 'LoginScreen');
  }

  async signIn(email: string, password: string): Promise<void> {
    await this.page.fill(this.selector('emailInput'), email);
    await this.page.fill(this.selector('passwordInput'), password);
    await this.page.click(this.selector('signInButton'));
  }

  getErrorMessage(): Promise<string> {
    return this.page.innerText(this.selector('errorMessage'));
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
  test('redirects to dashboard when credentials are valid', async ({ page, loginPage }) => {
    const user = aValidUser().build();

    await loginPage.goTo();
    await loginPage.signIn(user.email, user.password);

    await expect(page).toHaveURL(/\/dashboard/);
  });
});
```

Rules:
- One spec file per feature or screen, not per AC
- Test title reads as a behavior sentence: `'<outcome> when <condition>'`
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
  withYearsActive(years: number): this { this.yearsActive = years; return this; }
  build(): User { return { email: this.email, password: this.password, yearsActive: this.yearsActive }; }
}

export const aValidUser = (): UserBuilder => new UserBuilder();
```

### Waits

- **Never** use `page.waitForTimeout(...)`, `browser.pause(...)`, or `setTimeout`-based sleeps in test code
- Use Playwright's auto-waiting (`click`, `fill`, `expect(...).toBeVisible()`)
- For WebdriverIO/Appium, use the helpers in `test-core` `waits` — `waitUntilVisible`, `waitUntilStable` (backed by `waitUntil`, never fixed pauses)
- If you need a wait that doesn't exist, add it to `test-core` `waits`, don't inline it

### Allure reporting

- Tag every test with at least suite / feature / story metadata (`allure.epic`, `allure.feature`, `allure.story` or the `@playwright/test` tags wired to the Allure reporter)
- Attach evidence on failure: screenshot, page source, network HAR
- Use `allure.step(...)` (or step decorators) on page object methods so steps appear in the Allure tree

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

- [ ] No literal selectors in page/screen methods
- [ ] No `waitForTimeout` / `browser.pause` / `setTimeout` sleeps in tests
- [ ] Test title reads as a behavior sentence
- [ ] Test data via a builder
- [ ] Allure metadata present
- [ ] One logical assertion per test
- [ ] Page object methods describe intent, not mechanics
- [ ] Builders provide valid defaults
- [ ] No conditional logic in tests (`if`, `for` driving assertions) — use parameterized tests
- [ ] No `any`; everything typed under `strict`
- [ ] Tests are independent and order-agnostic

## Anti-examples

```typescript
// BAD: literal selector in page object
async signIn() {
  await this.page.click('button.signin-btn');  // ❌ selector in code
}

// BAD: sleep
await page.waitForTimeout(2000);  // ❌

// BAD: implementation-named test
test('clicks the login button', ...);  // ❌

// BAD: inline test data
await loginPage.signIn('user@test.com', 'Password1!');  // ❌ use a builder

// BAD: conditional in test
if (env === 'staging') { ... } else { ... }  // ❌ use parameterized tests or fixtures

// BAD: untyped escape hatch
const body: any = await res.json();  // ❌ validate with Zod
```
