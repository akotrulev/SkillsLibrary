---
name: qa-ui-test-writer-appium-typescript
description: Use when the user asks to scaffold a TypeScript + WebdriverIO (Appium service) page object or Mocha/Vitest mobile UI test. Triggers: "create an Appium page object for X in TS", "add a WebdriverIO mobile page for screen Y", "write an Appium TS test for Z". For end-to-end suite work prefer the staged agent `qa-mobile-typescript` / `qa-bdd-typescript` (or the matching slash command), which loads this skill inside its workflow; use this skill directly for a single targeted artifact.
---

# QA — Appium TypeScript Page Object & Test Generator

Scaffolds WebdriverIO + Appium page objects and Mocha (or Vitest) mobile UI tests in TypeScript strict mode, mirroring the Java and .NET siblings. Uses a thin `BasePage` with accessibility-id-first selectors, typed return values for navigation, and a session per worker for parallel-safe runs.

> WebdriverIO with the `@wdio/appium-service` is the de-facto TypeScript client for Appium 2.x — it bootstraps the Appium server, handles capabilities, and exposes `browser.$` / `browser.$$` over the WebDriver protocol. Native `appium-webdriver` bindings exist but are rarely used for new projects.

## Stack

- Node 20, TypeScript strict mode (`"strict": true`)
- **WebdriverIO** 9.x with `@wdio/appium-service` (manages the Appium 2.x server)
- **Mocha** (or **Vitest** — pick one and stay consistent) with `@wdio/mocha-framework`
- **Allure WDIO reporter** (`@wdio/allure-reporter`)
- ESM modules
- `appium` 2.x with the relevant driver (`appium-uiautomator2-driver` / `appium-xcuitest-driver`)

## When to use

- New page object under `src/pages/mobile/`
- Component-level page object scoped to a parent `WebdriverIO.Element`
- New mobile UI test under `test/specs/`

## When NOT to use

- Appium .NET → `qa/dotnet/skills/ui-test-author/appium`
- Appium Java → `qa/java/skills/ui-test-author/appium`
- Selenium / web TS → `qa/typescript/skills/ui-test-author/selenium` or `qa/typescript/skills/ui-test-author/playwright`
- Reviewing an existing page object → `qa/typescript/skills/ui-test-author/review`
- POM architecture → `qa/typescript/skills/page-object-design`

## Inputs needed

1. **Screen name** (PascalCase: `Login`, `Home`, `OrderConfirmation`)
2. **Platform** — Android, iOS, or both (decides selector strategies allowed)
3. **Elements** — for each: name + `accessibility id` (preferred), platform id, predicate / UIAutomator selector, or XPath (last resort)
4. **Actions** — what the test does, and whether each navigates
5. **Landmark element** — used in `verifyPageLoaded` to confirm the screen is visible
6. **Next pages** — destination page classes for navigation actions

## Patterns

### `BasePage` (already in the project)

```ts
import type { ChainablePromiseElement } from "webdriverio";

export abstract class BasePage {
  private static readonly TIMEOUT = 10_000;

  // ── Selector helpers ─────────────────────────────────────────────────────
  // Priority: accessibility id → id → -ios predicate / android uiautomator → xpath

  protected byAccessibilityId(id: string): ChainablePromiseElement {
    return $(`~${id}`);
  }

  protected byId(id: string): ChainablePromiseElement {
    return $(`id=${id}`);
  }

  protected byIosPredicate(predicate: string): ChainablePromiseElement {
    return $(`-ios predicate string:${predicate}`);
  }

  protected byAndroidUiAutomator(selector: string): ChainablePromiseElement {
    return $(`android=${selector}`);
  }

  protected byXPath(xpath: string): ChainablePromiseElement {
    return $(xpath);
  }

  async isElementVisible(el: ChainablePromiseElement): Promise<boolean> {
    await el.waitForDisplayed({ timeout: BasePage.TIMEOUT });
    return el.isDisplayed();
  }

  abstract verifyPageLoaded(): Promise<void>;
}
```

Every page extends `BasePage` and goes through these selector helpers — never `browser.$(...)` directly outside `BasePage`.

### Page object — `src/pages/mobile/LoginPage.ts`

```ts
import { expect } from "@wdio/globals";
import { BasePage } from "./BasePage";
import { HomePage } from "./HomePage";

export class LoginPage extends BasePage {
  private static readonly EMAIL_FIELD_ID = "login-email";
  private static readonly PASSWORD_FIELD_ID = "login-password";
  private static readonly SUBMIT_BUTTON_ID = "login-submit";

  private get emailField()    { return this.byAccessibilityId(LoginPage.EMAIL_FIELD_ID); }
  private get passwordField() { return this.byAccessibilityId(LoginPage.PASSWORD_FIELD_ID); }
  private get submitButton()  { return this.byAccessibilityId(LoginPage.SUBMIT_BUTTON_ID); }

  async verifyPageLoaded(): Promise<void> {
    await expect(this.emailField).toBeDisplayed({
      message: "Expected LoginPage to be visible but the email field was not found.",
    });
  }

  async login(email: string, password: string): Promise<HomePage> {
    await this.emailField.clearValue();
    await this.emailField.setValue(email);
    await this.passwordField.clearValue();
    await this.passwordField.setValue(password);
    await this.submitButton.click();
    return new HomePage();
  }
}
```

### Component page object — scoped to a parent element

```ts
import type { ChainablePromiseElement } from "webdriverio";
import { BasePage } from "./BasePage";
import { OrderDetailsPage } from "./OrderDetailsPage";

export class OrderRow extends BasePage {
  constructor(private readonly parent: ChainablePromiseElement) {
    super();
  }

  title()  { return this.parent.$("~order-title"); }
  amount() { return this.parent.$("~order-amount"); }

  async open(): Promise<OrderDetailsPage> {
    await this.parent.click();
    return new OrderDetailsPage();
  }

  async verifyPageLoaded(): Promise<void> {
    // Component itself; the host page owns the screen landmark.
    await this.title().waitForDisplayed();
  }
}
```

Container page:

```ts
async orderRows(): Promise<OrderRow[]> {
  const els = await $$("~order-row");
  return els.map(el => new OrderRow(el as ChainablePromiseElement));
}
```

### Sub-flow pages — namespaced sub-folder

Multi-step flows live in `src/pages/mobile/onboarding/{WelcomePage,ConsentPage,ProfilePage}.ts`. Each extends `BasePage` and returns the next page.

### Test — `test/specs/authentication.spec.ts`

```ts
import { expect } from "@wdio/globals";
import { LoginPage } from "../../src/pages/mobile/LoginPage";
import { seed } from "../support/seed";

describe("Authentication", () => {
  it("successful login lands on home", async () => {
    const login = new LoginPage();
    await login.verifyPageLoaded();

    const home = await login.login(seed.users[0], seed.password);
    await home.verifyPageLoaded();

    await expect(home.profileAvatar()).toBeDisplayed();
  });
});
```

WDIO owns the driver session via `wdio.conf.ts`; one session per worker is automatic when `maxInstances > 1`. Capabilities (platformName, deviceName, app, automationName) live in `wdio.conf.ts` and are selected via the `--suite` flag or env vars.

## Rules

### Page object rules
- Extend `BasePage`; pages do not take a `driver` parameter — WDIO's `browser` is implicit
- Element accessors return `ChainablePromiseElement` (no `await` needed at the accessor — chaining handles it)
- **Selector preference order**: `~accessibility-id` → `id=…` → `-ios predicate string:…` / `android=…` → XPath (last resort, leave a `// TODO`). Per the Appium team, treat a working XPath as **proof the node exists, not the final locator** — downgrade to a native strategy (`android=…` / `-ios class chain:…`) once the source exposes one, and drop the TODO. On iOS, `id` / `name` / `accessibility id` are synonyms over the element's `name` attribute. **Discover and verify these selectors against the live app via `qa/typescript/skills/mobile-screen-explorer` before hand-writing them**, and let `qa/typescript/skills/mobile-screen-objects` emit the class from that inventory — this skill owns the conventions both of those defer to.
- **Selector constants** — declare each as `private static readonly` at the top of the class. Never inline a selector string inside an action method.
- One class per screen; multi-step flows live in a sub-folder
- Reusable components take a parent element in their constructor and query inside it
- Navigation actions return the next page object; same-screen actions return `Promise<void>`
- **Every page object must implement `verifyPageLoaded()`** asserting the landmark element is displayed
- Method naming describes user intent (`login`, `tapPrimaryAction`, `enterEmail`), not WDIO mechanics

### Test rules
- Use Mocha `describe` / `it` (or Vitest `describe` / `test`) — no class inheritance in TS tests
- Test names describe behavior: `"successful login lands on home"`, `"locked user sees error banner"`
- Tag groups via spec file path or Mocha grep (`--mochaOpts.grep "@smoke"`)
- Assertions live in the test, never in pages (except the `verifyPageLoaded()` landmark assertion)
- Every assertion has a `message`: `expect(x).toBeDisplayed({ message: "why this matters" })`
- Use `expect.soft` (Vitest) or aggregate `await Promise.all([...])` patterns when verifying multiple fields after one user action
- **One expected condition per assertion — never an `OR`.** `await expect(banner).toHaveText('Saved')`, never `toHaveText(/Saved|Success/)`, `expect(['Saved', 'Success']).toContain(text)`, or a `||` inside an `expect`. The rule covers label text, element counts, screen landmarks, attribute values, and displayed/enabled state alike — and applies per platform: when Android and iOS legitimately show different copy, that is two platform-scoped expectations, never one `OR`. If both outcomes are genuinely reachable on one platform the test does not know what the app should do — split it into one `it(...)` per expected outcome, generate one test per row from a case array, or pin down the correct behavior. The only exception is an explicit instruction to accept more than one value; record that instruction in a comment on the assertion.
- **No `try`/`catch` in a test — and none in the cleanup hook.** An unexpected rejection must reach the runner; an expected one is asserted with `await expect(...).rejects` / `expect(fn).toThrow()`, which is an assertion, not error handling. Anything the test created is tracked and deleted in `afterEach` with no catch — a cleanup that fails should fail loudly rather than leak state into the next run. The suite's only catches live in **I/O helpers where narrowing one named error is the contract** — an `isDisplayed()` probe, a session-teardown helper — never a bare `catch {}` or `.catch(() => {})`, and never a catch that lets a failed action continue into the assertions.
- **Failures name the subject.** `expect(await banner.getText(), \`success banner after saving order ${orderId}\`).toBe('Saved')`. A UI failure reported as `expected '' to be 'Saved'` with no subject is indistinguishable from a locator that matched the wrong element.

### Waits
- Default 10s `waitForDisplayed` baked into `BasePage`
- WDIO's auto-wait covers most element resolution; for conditional waits use `waitForDisplayed` / `waitForEnabled` / `waitUntil(...)`
- **No `await new Promise(r => setTimeout(r, n))`** for synchronization — ever, including for screen transitions or animations
- **No `browser.pause(n)`** — `pause` is a `setTimeout` in WDIO's clothing

### Driver / session lifecycle
- Capabilities (`platformName`, `deviceName`, `app`, `automationName`) configured in `wdio.conf.ts`, parameterised by env vars (`PLATFORM`, `DEVICE`, `APP_PATH`)
- Appium server is auto-started by `@wdio/appium-service` — do not run `appium` manually and hardcode `http://localhost:4723`
- One session per WDIO worker; parallel runs handled by `maxInstances` in config
- For cloud providers (BrowserStack, Sauce) swap `services: ['appium']` for the provider's service

### What NOT to do

- No `setTimeout` / `browser.pause` waits — use `waitForDisplayed`, `waitForEnabled`, or `waitUntil`
- No `browser.$(...)` outside `BasePage` — the selector helpers are the single funnel
- No assertions inside page methods (except the `verifyPageLoaded()` landmark)
- No `OR` in any assertion — no `||` inside an `expect`, no `expect([a, b]).toContain(x)`, no `/a|b/` alternation, and no OR-ing Android and iOS copy into one expectation. One expected value per assertion (see Test rules)
- No `try`/`catch` in a test or cleanup hook — expected rejections use `await expect(...).rejects`; catches live only in I/O helpers narrowing one named error (see Test rules)
- No XPath when an `accessibility id` could be added to the app — flag as tech debt
- No shared mutable state on page objects — instantiate fresh per test
- No business logic / API calls in page objects — pages model the screen, tests own the workflow
- No hardcoded device names, app paths, or server URLs — go through `wdio.conf.ts` and env vars
- No `any` in page or test code — strict TS
- No `as unknown as ChainablePromiseElement` casts to suppress typing problems — fix the selector helper instead

## Generation steps

1. Confirm **screen name**, **platform(s)**, **landmark element**, **elements + selectors**, **actions**, **next pages**.
2. For each element with no `accessibility id`: flag whether one can be added to the app. Don't silently fall back to XPath.
3. Generate `src/pages/mobile/{ScreenName}Page.ts`:
   - One `private static readonly` selector constant per element
   - One `private get` accessor per element (returns `ChainablePromiseElement`)
   - `verifyPageLoaded()` asserts the landmark element is displayed
   - One action method per user-intent action (`Promise<void>` or `Promise<NextPage>`)
   - For repeating items, an `async {component}s(): Promise<Component[]>` method
4. If a destination page is missing, stub it or recursively generate it.
5. Generate the spec file using `describe`/`it`; one `it(...)` per scenario, with assertions on user-visible outcomes.
6. Run `npx wdio run wdio.conf.ts --suite mobile` — expect 0 failures. If the Appium service fails to start, check that the relevant driver (`uiautomator2` / `xcuitest`) is installed via `appium driver list --installed`; a manually-run server should answer `curl -s http://127.0.0.1:4723/status` and list your driver under `Available drivers:`.

> **A test that can't find a visible element is usually not a locator bug.** Per the Appium team, an element absent from page source is most often an accessibility, app-state, active-app (system alert/overlay), or native-vs-WebView context problem — fix that before rewriting the selector. For environment/doctor failures and driver-specific locator questions, the `@appium/mcp-documentation` server (`appium_skills`, `appium_documentation_query`) answers authoritatively; prefer it over community forums.

## Handoffs

- Discovering / verifying selectors on the live app → `qa/typescript/skills/mobile-screen-explorer`
- Emitting / updating the page object from a discovered inventory → `qa/typescript/skills/mobile-screen-objects`
- POM architecture (capabilities profiles, sub-folders, base classes) → `qa/typescript/skills/page-object-design`
- Test data builders → `qa/typescript/skills/test-data-builder`
- Reviewing a page object → `qa/typescript/skills/ui-test-author/review`
- Allure reporting → `qa/reporting/typescript/skills/test-reports`
