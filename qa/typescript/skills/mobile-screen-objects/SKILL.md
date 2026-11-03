---
name: mobile-screen-objects
description: Use when creating or updating a WebdriverIO Appium page object from live-screen elements. Triggers "create a page object for the Login screen". Not for finding elements (mobile-screen-explorer).
---

# QA — Appium Page Object Builder (TypeScript)

Turns a discovered element inventory into a **WebdriverIO page object** — a `BasePage` subclass under `src/pages/mobile/`. It consumes the element table + locator-ladder rungs from `qa/typescript/skills/mobile-screen-explorer` (or an inventory the user supplies directly) and emits/updates one screen class. This skill owns **codegen and the create/update diff** — the page-object *conventions* (base class, selector helpers, `verifyPageLoaded`, naming, return types, waits) are owned by `qa/typescript/skills/ui-test-author/appium`; load it and follow it rather than re-deriving the rules here.

## When to use

- Elements for a screen have been discovered (via `mobile-screen-explorer`) and now need a page-object class
- An existing page object must be reconciled against a freshly explored screen (elements added/removed/renamed)
- The user describes a screen's elements and ids directly and wants the class emitted

## When NOT to use

- The elements/locators aren't known yet → `qa/typescript/skills/mobile-screen-explorer` first (don't fabricate locators)
- Writing or tagging the tests that use the page → `qa/typescript/skills/ui-test-author/appium`
- Designing the screen-object hierarchy (base classes, sub-folders, capabilities) → `qa/typescript/skills/page-object-design`
- Web page objects → `qa/typescript/skills/page-objects-from-url`
- Reviewing an existing page object → `qa/typescript/skills/ui-test-author/review`
- Java / .NET stacks → `qa/java/skills/mobile-screen-objects` / `qa/dotnet/skills/mobile-screen-objects`

## Inputs needed

1. **Screen name** (PascalCase → `LoginPage`, `OrderConfirmationPage`)
2. **Element list** — per element: name, type, and the locator-ladder rung from `mobile-screen-explorer` (the test id first: iOS `~`, Android `id=`; then a native query; XPath last)
3. **Landmark element** — the one element that proves the screen is visible (used by `verifyPageLoaded()`)
4. **Actions** — user-intent actions and, for each, whether it navigates to another screen (→ destination `*Page` class name)
5. **Target project** — repo path and existing `src/pages/mobile/` location/convention to match

## Conventions

The standards an emitted screen object must meet are the qa-typescript rule files `mobile-tests.md` and `qa-typescript.md`: the project's copy in `.claude/rules/qa-typescript/`, or the plugin's in `qa/typescript/skills/rules/` when the project has not installed them (`/qa-typescript:rules` does). `ui-test-author/appium` carries the `BasePage` and the scoped-component recipe. The codegen specifics:

- Element access goes through the inherited selector helpers, in ladder order: `byTestId` (iOS `~`, Android `id=`) → native query (`byIosPredicate` · `byIosClassChain` · `byAndroidUiAutomator`, the last secondary because Google is deprecating `UiSelector`) → `byXPath`. An XPath rung is a temporary scaffold: when `mobile-screen-explorer` later reports a stronger locator, downgrade to it and drop its row from `missing-testids.md`.
- Each locator id is a `private static readonly {ELEMENT}_ID` constant (a fallback is `{ELEMENT}_XPATH_FALLBACK`); elements are `private get` accessors calling the matching helper.
- Navigation actions return `Promise<{Destination}Page>` (`return new {Destination}Page()`); same-screen actions return `Promise<void>`.
- Folder `src/pages/mobile/`, file `src/pages/mobile/<Screen>Page.ts`; multi-step flows in a sub-folder, repeating rows as scoped components that do not extend `BasePage`.

## Template

```ts
import { expect } from '@wdio/globals';
import { BasePage } from './BasePage';
import { OrdersPage } from './OrdersPage';

export class LoginPage extends BasePage {
  private static readonly EMAIL_ID = 'Login.Email';
  private static readonly PASSWORD_ID = 'Login.Password';
  private static readonly SUBMIT_ID = 'Login.Submit';

  private get email() { return this.byTestId(LoginPage.EMAIL_ID); }
  private get password() { return this.byTestId(LoginPage.PASSWORD_ID); }
  private get submit() { return this.byTestId(LoginPage.SUBMIT_ID); }

  async verifyPageLoaded(): Promise<void> {
    await expect(this.email).toBeDisplayed({ message: 'Expected LoginPage to be visible but the email field was not found' });
  }

  async signIn(email: string, password: string): Promise<OrdersPage> {
    await this.email.setValue(email);
    await this.password.setValue(password);
    await this.submit.click();
    return new OrdersPage();
  }
}
```

`byTestId` picks `~id` on iOS and `id=id` on Android. Where the two platforms need different ids, the page keeps one locator map keyed by platform and one accessor per element; an action never branches on the platform. The compilable reference is `qa/typescript/skills/ui-test-author/appium/assets/`.

For an element with no test id, name the constant as a fallback, prefer a native query over XPath whenever the source exposes one, and add the row to `missing-testids.md`:

```ts
private static readonly PASSWORD_REVEAL_XPATH_FALLBACK = '//*[@class="…ImageButton"][2]';
private get passwordReveal() { return this.byXPath(LoginPage.PASSWORD_REVEAL_XPATH_FALLBACK); }
```

## Procedure

1. **Check for an existing page object.** Glob the project for `**/pages/mobile/**/<Screen>Page.ts` (and `**/pages/**`). Exists → this is an **update** (step 4). Missing and the project has no `pages/mobile/` at all → load `qa/typescript/skills/page-object-design` first to lay down the base class + structure.
2. **Map every element to a constant + selector helper** using its locator-ladder rung. Test-id elements use `byTestId`; fallbacks use the matching helper and are named `*_FALLBACK`, with a row in `missing-testids.md`. Each repeating group becomes a scoped component.
3. **Write the class** per the conventions above: constants block, `private get` accessors, `verifyPageLoaded()` on the landmark, one intent-named `async` action per user action (returning `Promise<void>` or the destination `*Page`), one query method per datum a test reads. Stub any destination page that doesn't exist yet.
4. **Update mode — diff before writing:**
   - New element on screen, not in class → add constant + accessor/action
   - Constant in class, element gone from screen → flag and **ask** before deleting (may belong to a state you didn't reach)
   - Element's accessibility id changed → update the constant, note it as a breaking rename for the team
   - Fallback locator where a test id now exists → upgrade to `byTestId`, rename the constant, remove the row from `missing-testids.md`
   - Never reorder/rename existing public methods tests already call without flagging it
5. **Verify:** `npx tsc --noEmit` (or the project equivalent) → type-checks clean. Confirm `verifyPageLoaded()`'s landmark matches what `mobile-screen-explorer` reported for this screen.
6. **Report:** class created/updated (diff summary), counts (accessibility-id-backed / fallback / ⚠ XPath), destination stubs created, open questions.

## Rules

- **Discovery is not this skill's job** — never invent a locator. If an element wasn't in the `mobile-screen-explorer` inventory, go get it there first.
- One class per screen; update in place rather than creating a parallel duplicate.
- Everything else an emitted screen object must meet is the rule files named under Conventions; where they and this skill disagree, the rule files win.

## Handoffs

- Discovering the elements first → `qa/typescript/skills/mobile-screen-explorer`
- The page-object rulebook this skill applies → `qa/typescript/skills/ui-test-author/appium`
- Screen-object architecture (base class, sub-folders, components) → `qa/typescript/skills/page-object-design`
- Writing the tests against the page → `qa/typescript/skills/ui-test-author/appium`
- Reviewing the result → `qa/typescript/skills/ui-test-author/review`
- Java / .NET siblings → `qa/java/skills/mobile-screen-objects` / `qa/dotnet/skills/mobile-screen-objects`
