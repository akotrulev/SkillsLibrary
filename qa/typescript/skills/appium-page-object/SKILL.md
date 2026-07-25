---
name: qa-appium-page-object-typescript
description: Use when the user wants a TypeScript (WebdriverIO) Appium page object created or updated from elements already discovered on a live screen. Triggers: "create a page object for the Login screen", "add a page for the … screen", "implement the … page". For end-to-end suite work prefer the phased agent `qa-mobile-typescript` / `qa-bdd-typescript` (or the matching slash command), which loads this skill inside its workflow; use this skill directly for a single targeted artifact.
---

# QA — Appium Page Object Builder (TypeScript)

Turns a discovered element inventory into a **WebdriverIO page object** — a `BasePage` subclass under `src/pages/mobile/`. It consumes the element table + locator-ladder rungs from `qa/typescript/skills/appium-explore` (or an inventory the user supplies directly) and emits/updates one screen class. This skill owns **codegen and the create/update diff** — the page-object *conventions* (base class, selector helpers, `verifyPageLoaded`, naming, return types, waits) are owned by `qa/typescript/skills/ui-test-author/appium`; load it and follow it rather than re-deriving the rules here.

## When to use

- Elements for a screen have been discovered (via `appium-explore`) and now need a page-object class
- An existing page object must be reconciled against a freshly explored screen (elements added/removed/renamed)
- The user describes a screen's elements and ids directly and wants the class emitted

## When NOT to use

- The elements/locators aren't known yet → `qa/typescript/skills/appium-explore` first (don't fabricate locators)
- Writing or tagging the tests that use the page → `qa/typescript/skills/ui-test-author/appium`
- Designing the screen-object hierarchy (base classes, sub-folders, capabilities) → `qa/typescript/skills/page-object-architect`
- Web page objects → `qa/typescript/skills/pom-builder`
- Reviewing an existing page object → `qa/typescript/skills/ui-test-author/reviewer`
- Java / .NET stacks → `qa/java/skills/appium-page-object` / `qa/dotnet/skills/appium-page-object`

## Inputs needed

1. **Screen name** (PascalCase → `LoginPage`, `OrderConfirmationPage`)
2. **Element list** — per element: name, type, and the locator-ladder rung from `appium-explore` (accessibility id preferred; resource-id / UIAutomator / predicate / XPath fallback)
3. **Landmark element** — the one element that proves the screen is visible (used by `verifyPageLoaded()`)
4. **Actions** — user-intent actions and, for each, whether it navigates to another screen (→ destination `*Page` class name)
5. **Target project** — repo path and existing `src/pages/mobile/` location/convention to match

## Conventions (owned by `ui-test-author/appium`)

Before writing, **load `qa/typescript/skills/ui-test-author/appium/SKILL.md`** and apply its page-object rules. The non-negotiables it defines:

- Extend `BasePage`; pages take **no `driver` parameter** — WebdriverIO's `browser` is implicit. Never call `browser.$(...)` directly outside `BasePage`.
- All element access goes through the inherited selector helpers, in ladder order: `byAccessibilityId` → `byId` → native query (`byAndroidUiAutomator` · `byIosPredicate` / `-ios class chain`) → `byXPath` (+ `// TODO`). An XPath rung is a temporary scaffold, not a destination — when `appium-explore` later reports a native locator for that element, downgrade to it and drop the TODO.
- Each locator id is a `private static readonly {ELEMENT}_ID` constant at the top; elements are exposed as `private get` accessors that call the matching selector helper — never inline a selector string in an action.
- Return types: `Promise<void>` for same-screen actions; `Promise<{Destination}Page>` for navigation actions (return `new {Destination}Page()`).
- **Every page object implements `verifyPageLoaded(): Promise<void>`** asserting the landmark is displayed (`expect(...).toBeDisplayed()` — the only assertion allowed inside a page object).
- Returned elements are `ChainablePromiseElement`; no manual `browser` plumbing.
- No `browser.pause(ms)` / `setTimeout` waits — the base class's `waitForDisplayed` handles timing.
- Folder `src/pages/mobile/`; file `src/pages/mobile/<Screen>Page.ts`; multi-step flows in a sub-folder, repeating rows as components scoped to a parent `ChainablePromiseElement`.

## Template

```ts
import { expect } from "@wdio/globals";
import { BasePage } from "./BasePage";
import { HomePage } from "./HomePage";

export class LoginPage extends BasePage {
  // Locator constants — accessibility id (testID) first; fallbacks carry a TODO
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

For an element with no accessibility id, use the fallback helper and mark it. Prefer a native query (`byAndroidUiAutomator` / `byIosPredicate`) over XPath whenever the source exposes one; reserve XPath for when it doesn't:

```ts
// TODO: missing accessibility id 'login-password-reveal' — see missing-testids.md
//       XPath is a scaffold; replace with a native locator once the app exposes one.
private static readonly PASSWORD_REVEAL_XPATH = '//*[@class="…ImageButton"][2]';
private get passwordReveal() { return this.byXPath(LoginPage.PASSWORD_REVEAL_XPATH); }
```

## Procedure

1. **Check for an existing page object.** Glob the project for `**/pages/mobile/**/<Screen>Page.ts` (and `**/pages/**`). Exists → this is an **update** (step 4). Missing and the project has no `pages/mobile/` at all → load `qa/typescript/skills/page-object-architect` first to lay down the base class + structure.
2. **Map every element to a constant + selector helper** using its locator-ladder rung. Accessibility-id elements use `byAccessibilityId`; fallbacks use the matching helper and carry a `// TODO` referencing `missing-testids.md`.
3. **Write the class** per the conventions above: constants block, `private get` accessors, `verifyPageLoaded()` on the landmark, one intent-named `async` action per user action (returning `Promise<void>` or the destination `*Page`), one query method per datum a test reads. Stub any destination page that doesn't exist yet.
4. **Update mode — diff before writing:**
   - New element on screen, not in class → add constant + accessor/action
   - Constant in class, element gone from screen → flag and **ask** before deleting (may belong to a state you didn't reach)
   - Element's accessibility id changed → update the constant, note it as a breaking rename for the team
   - Fallback locator where an accessibility id now exists → upgrade to `byAccessibilityId`, drop the `// TODO`, remove the row from `missing-testids.md`
   - Never reorder/rename existing public methods tests already call without flagging it
5. **Verify:** `npx tsc --noEmit` (or the project equivalent) → type-checks clean. Confirm `verifyPageLoaded()`'s landmark matches what `appium-explore` reported for this screen.
6. **Report:** class created/updated (diff summary), counts (accessibility-id-backed / fallback / ⚠ XPath), destination stubs created, open questions.

## Rules

- **Discovery is not this skill's job** — never invent a locator. If an element wasn't in the `appium-explore` inventory, go get it there first.
- **Accessibility-id-first** in the emitted code, matching the discovery contract; fallbacks always carry the `// TODO`.
- **`ui-test-author/appium` wins on every convention conflict** — this skill is its codegen-from-inventory front end, not a competing rulebook.
- **No assertions outside `verifyPageLoaded()`**, no business logic / API calls, no test code in the page object.
- One class per screen; update in place rather than creating a parallel duplicate.

## Handoffs

- Discovering the elements first → `qa/typescript/skills/appium-explore`
- The page-object rulebook this skill applies → `qa/typescript/skills/ui-test-author/appium`
- Screen-object architecture (base class, sub-folders, components) → `qa/typescript/skills/page-object-architect`
- Writing the tests against the page → `qa/typescript/skills/ui-test-author/appium`
- Reviewing the result → `qa/typescript/skills/ui-test-author/reviewer`
- Java / .NET siblings → `qa/java/skills/appium-page-object` / `qa/dotnet/skills/appium-page-object`
