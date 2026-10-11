---
name: mobile-screen-objects
description: Use when the user wants a .NET (C#) Appium page object created or updated from elements already discovered on a live screen. Triggers: "create a page object for the Login screen", "add a page for the … screen", "implement the … page". Do NOT use for discovering a screen's elements (`qa-dotnet:mobile-screen-explorer`) or web page objects (`qa-dotnet:page-object-design`).
---

# QA — Appium Page Object Builder (.NET)

Turns a discovered element inventory into a **C# Appium page object** — a `BaseAppiumPage` subclass under `AppiumTests/Pages/`. It consumes the element table + locator-ladder rungs from `qa/dotnet/skills/mobile-screen-explorer` (or an inventory the user supplies directly) and emits/updates one screen class. This skill owns **codegen and the create/update diff** — the page-object *conventions* (base class, finder methods, `VerifyPageLoaded`, naming, return types, waits) are owned by `qa/dotnet/skills/ui-test-author/appium`; load it and follow it rather than re-deriving the rules here.

## When to use

- Elements for a screen have been discovered (via `mobile-screen-explorer`) and now need a page-object class
- An existing page object must be reconciled against a freshly explored screen (elements added/removed/renamed)
- The user describes a screen's elements and ids directly and wants the class emitted

## When NOT to use

- The elements/locators aren't known yet → `qa/dotnet/skills/mobile-screen-explorer` first (don't fabricate locators)
- Writing or tagging the tests that use the page → `qa/dotnet/skills/ui-test-author/appium`
- Designing the screen-object hierarchy (base classes, sub-packages, capabilities) → `qa/dotnet/skills/page-object-design`
- Web page objects → `qa/dotnet/skills/page-objects-from-url`
- Reviewing an existing page object → `qa/dotnet/skills/ui-test-author/review`
- Java / TypeScript stacks → `qa/java/skills/mobile-screen-objects` / `qa/typescript/skills/mobile-screen-objects`

## Inputs needed

1. **Screen name** (PascalCase → `LoginPage`, `OrderConfirmationPage`)
2. **Element list** — per element: name, type, and the locator-ladder rung from `mobile-screen-explorer` (the test id first; a native query, then XPath, as fallbacks)
3. **Landmark element** — the one element that proves the screen is visible (used by `VerifyPageLoaded()`)
4. **Actions** — user-intent actions and, for each, whether it navigates to another screen (→ destination `*Page` class name)
5. **Target project** — repo path and existing `AppiumTests/Pages/` location/convention to match

## Conventions (owned by `ui-test-author/appium`)

Before writing, **load `qa/dotnet/skills/ui-test-author/appium/SKILL.md`** and apply its page-object rules. The non-negotiables it defines:

- Extend `BaseAppiumPage`; constructor passes `driver` to `: base(driver)` — never extend `AppiumDriver` or call `Driver.FindElement(...)` directly
- All element access goes through the inherited finders, in ladder order: `ByTestId` (iOS `AccessibilityId`, Android `Id`) → a native query (`ByAndroidUiAutomator` · `ByIosPredicate` / `ByIosClassChain`) → `ByXPath`. An XPath rung is a temporary scaffold, not a destination — when `mobile-screen-explorer` later reports a stronger locator for that element, downgrade to it and drop the fallback row from `missing-testids.md`.
- Each locator is a `private const string {Element}Id` constant at the top (a fallback is `{Element}XPathFallback`) — never inline a locator string in a method
- Return types: `void` for same-screen actions; the destination page object for navigation actions
- **Every page object overrides `VerifyPageLoaded()`** asserting the landmark is displayed (the only assertion allowed inside a page object)
- Elements stay private: a page exposes intent methods and queries (`Title()`), never an `AppiumElement`; no PageFactory / `[FindsBy]`
- No `Thread.Sleep` — the base class's `WebDriverWait` handles timing
- Namespace `AppiumTests.Pages`; file `AppiumTests/Pages/<Screen>Page.cs`; multi-step flows in a sub-namespace, repeating rows as components scoped to a parent `AppiumElement`

## Template

The shape to emit is [`qa/dotnet/skills/ui-test-author/appium/assets/page_template.cs`](../ui-test-author/appium/assets/page_template.cs); `LoginPage.cs` beside it shows a navigating action (`SignIn` returns `OrdersPage`) and `OrderRow.cs` a scoped component. Copy and rename; do not retype.

For an element with no test id, use the fallback finder and record the row in `missing-testids.md` (page, element, suggested id, fallback in use). The code carries no marker; the constant's name says it is a fallback. Prefer a native query (`ByAndroidUiAutomator` / `ByIosClassChain`) over XPath whenever the source exposes one:

```csharp
private const string PasswordRevealXPathFallback = "//*[@class='…ImageButton'][2]";
```

## Procedure

1. **Check for an existing page object.** Glob the project for `**/Pages/**/<Screen>Page.cs` (and `**/Pom/**`). Exists → this is an **update** (step 4). Missing and the project has no `Pages/` at all → load `qa/dotnet/skills/page-object-design` first to lay down the base class + structure.
2. **Map every element to a constant + finder** using its locator-ladder rung. Test-id elements use `ByTestId`; fallbacks use the matching finder and have a row in `missing-testids.md`.
3. **Write the class** per the conventions above: constants block, constructor, `VerifyPageLoaded()` on the landmark, one intent-named action per user action (returning `void` or the destination `*Page`), one query method per datum a test reads. Stub any destination page that doesn't exist yet.
4. **Update mode — diff before writing:**
   - New element on screen, not in class → add constant + accessor/action
   - Constant in class, element gone from screen → flag and **ask** before deleting (may belong to a state you didn't reach)
   - Element's accessibility id changed → update the constant, note it as a breaking rename for the team
   - Fallback locator where a test id now exists → upgrade to `ByTestId`, remove the row from `missing-testids.md`
   - Never reorder/rename existing public methods tests already call without flagging it
5. **Verify:** `dotnet build` (or the project equivalent) → compiles clean. Confirm `VerifyPageLoaded()`'s landmark matches what `mobile-screen-explorer` reported for this screen. Inside a plan task marked `Gate: none`, run none of this and report the files as "written, not run".
6. **Report:** class created/updated (diff summary), counts (accessibility-id-backed / fallback / ⚠ XPath), destination stubs created, open questions.

## Rules

- **Discovery is not this skill's job** — never invent a locator. If an element wasn't in the `mobile-screen-explorer` inventory, go get it there first.
- **Test-id-first** in the emitted code, matching the discovery contract; every fallback has a `missing-testids.md` row and no marker in the code.
- **`ui-test-author/appium` wins on every convention conflict** — this skill is its codegen-from-inventory front end, not a competing rulebook.
- **No assertions outside `VerifyPageLoaded()`**, no business logic / API calls, no test code in the page object.
- One class per screen; update in place rather than creating a parallel duplicate.

## Handoffs

- Discovering the elements first → `qa/dotnet/skills/mobile-screen-explorer`
- The page-object rulebook this skill applies → `qa/dotnet/skills/ui-test-author/appium`
- Screen-object architecture (base class, sub-packages, components) → `qa/dotnet/skills/page-object-design`
- Writing the tests against the page → `qa/dotnet/skills/ui-test-author/appium`
- Reviewing the result → `qa/dotnet/skills/ui-test-author/review`
- Java / TypeScript siblings → `qa/java/skills/mobile-screen-objects` / `qa/typescript/skills/mobile-screen-objects`
