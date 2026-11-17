---
name: gherkin-step-code
description: Use when turning Gherkin .feature files into Reqnroll steps in .NET bound to page objects. Triggers "generate step definitions". Not for writing .feature files (feature-files).
---

# Reqnroll Step Bindings + POM Implementation (C# / .NET 10)

Parses `.feature` files (and the **Step Catalog** from `feature-file-writer`) into Reqnroll `[Binding]` classes, **split by domain**, with parameterized Cucumber-Expression steps, and **implements each step against existing page objects**: a page intent method for a sequence of interactions, or one call on a control or element the page exposes. In a BDD suite the step definition is the intent layer. `Given`/`When` steps act; **only `Then` steps assert**, on the locators and queries the page objects expose. The Reqnroll project, DI container, hooks, failure evidence and `ScenarioState` already exist (from `bdd-project-scaffold`).

## Stack

- Reqnroll.NUnit 3.3.x + `Reqnroll.Microsoft.Extensions.DependencyInjection`, at the pins in `bdd-project-scaffold`
- C# / .NET 10 (8/9 supported — match the host project), `async Task` step methods (Playwright web) or sync (Appium mobile)
- Page objects from the existing UI/mobile project (`qa/dotnet/skills/ui-test-author/playwright` assets, `qa/dotnet/skills/page-object-design`) — `LoginPage`, `HomePage`, `LoginPage.Credentials`
- `Microsoft.Playwright.Assertions` (web-first `Expect`) for `Then` steps, at the Playwright version in `qa/dotnet/skills/ui-test-author/playwright`'s **Versions** table

## When to use

- `.feature` files exist (from `feature-file-writer`) and need step definitions.
- A scenario reports **undefined** or **ambiguous** steps and needs bindings written/fixed.
- Implementing the bodies of generated step skeletons against page objects.

## When NOT to use

- Authoring/canonicalizing `.feature` files → `qa/_shared/bdd/feature-file-writer`
- Project/DI/hooks scaffold → `qa/dotnet/skills/bdd-project-scaffold`
- Building or extracting page objects → `qa/dotnet/skills/page-object-design` / `page-objects-from-url` / `mobile-screen-objects`
- Reviewing features + bindings → `qa/dotnet/skills/bdd-reviewer`
- Java/TS step glue → `qa/{java,typescript}/skills/gherkin-step-code`

## Inputs needed

Confirm at most 2–3.

1. **The `.feature` files + Step Catalog** (from `feature-file-writer`) and the **Cleanup handoff** note.
2. **The page objects** available (paths) — which intent methods exist; what's missing.
3. **Platform** — Playwright (async) or Appium (sync).

## Core rules

### 1. One binding class per domain, mapped to the Step Catalog

Group steps by feature/domain (`AuthenticationSteps`, `CartSteps`), **not** one giant `Steps.cs`. Each canonical Step-Catalog row becomes exactly one step method — reuse across scenarios, never duplicate. A step shared by many features goes in a `CommonSteps` binding.

One binding per field, filter or column, named after it and calling one named control: `I select {string} for Deal Type filter`, `I select {string} for Region filter`. Never a generic `I select {string} for {string} filter`: it needs a lookup from the field name to a control, which is a branch. One phrasing per concept still holds.

### 2. Cucumber Expressions, not regex

Default to Cucumber Expressions (`{string}`, `{int}`, `{word}`, `{decimal}`, enums as `{MyEnum}`). Reqnroll auto-detects regex only if the pattern starts with `^`/ends with `$` or contains regex tokens — keep steps as plain Cucumber Expressions so the catalog params map cleanly. Custom types via `[StepArgumentTransformation]`.

### 3. Inject shared state via the constructor — never new up the page or use the context bag

Step classes take `ScenarioState` (the scoped DI object from the scaffold) in the constructor. The page/driver was created in the `[BeforeScenario]` hook; steps reach page objects through `state`. No static fields, no `ScenarioContext["key"]` bag for typed state.

### 4. The step is the intent layer; mechanics live in page objects

A step is one interaction or one assertion. Its body either calls a page intent method, which exists only when the step is a sequence of interactions (`state.Deals.FilterAsync(dealType, region)`), or acts on one control or element the page exposes (`state.Deals.DealType.SelectAsync(option)`). Controls are the UI project's components (`Dropdown`, `DataGrid`, …). **No selectors, no `IPage.Locator(...)`, no waits and no branch in step definitions** — those belong in the page object or its controls. `Given`/`When` act and **never assert** — not even a "page loaded" check, which would make the precondition a hidden assertion; `Then` asserts with web-first `Expect(...)` on a locator the page object exposes (`state.Home.Greeting`). Page objects never assert. No `try`/`catch` in a step.

### 5. Async all the way (web)

`async Task` step methods; `await` every page-object call. Never `.Result`/`.Wait()`. No `Thread.Sleep`/`WaitForTimeoutAsync` — rely on Playwright auto-waiting and web-first assertions.

### 6. Implement the Cleanup as a hook, not steps

The `feature-file-writer` Cleanup handoff becomes an `[AfterScenario]` in the support layer (the scaffold owns hook placement) — never Gherkin steps and never a step definition.

### 7. No empty bindings

A binding whose body does nothing passes without testing anything: a **blocker**. A feature written ahead of its automation is tagged with the suite's skip tag (`@not-automated` when it has none) and a ticket, and the scaffold's run filter keeps it out; its steps stay unbound until they are implemented.

### 8. Pre-clean in a `Given`, through a seeder

A precondition that a record must not exist (`Given deal {string} does not exist`) deletes any leftover through the suite's API seeder, so a crashed run does not poison the next one. Never a long UI sequence, and the `[AfterScenario]` teardown still runs.

### 9. Missing page objects → build them first

If a step needs a page object/method that doesn't exist, stop and build it via `page-object-design`/`page-objects-from-url` (or hand to `qa-ui-dotnet`/`qa-mobile-dotnet`). Do not inline locators into the step to "make it pass."

## Templates

### Step definition — `StepDefinitions/AuthenticationSteps.cs` (Playwright/web)

```csharp
using Example.BddTests.Support;
using Example.UiTests.Pages;
using Example.UiTests.Support;
using Reqnroll;
using static Microsoft.Playwright.Assertions;

namespace Example.BddTests.StepDefinitions;

[Binding]
public sealed class AuthenticationSteps(ScenarioState state)
{
    [Given("I am on the login page")]
    public async Task GivenIAmOnTheLoginPage() => await state.Login.GoToAsync();

    [When("I sign in as a registered customer")]
    public async Task WhenISignInAsARegisteredCustomer() =>
        await state.Login.SignInAsync(new LoginPage.Credentials(BaseTest.RequiredEnv("E2E_USER"), BaseTest.RequiredEnv("E2E_PASSWORD")));

    [When("I sign in with email {string} and password {string}")]
    public async Task WhenISignInWith(string email, string password) =>
        await state.Login.SignInAsync(new LoginPage.Credentials(email, password));

    [Then("I see my greeting")]
    public async Task ThenISeeMyGreeting() =>
        await Expect(state.Home.Greeting).ToBeVisibleAsync();

    [Then("I see the error {string}")]
    public async Task ThenISeeTheError(string message) =>
        await Expect(state.Login.Error).ToHaveTextAsync(message);
}
```

- `LoginPage`, `HomePage` and `LoginPage.Credentials` are the UI project's page objects
  (`qa/dotnet/skills/ui-test-author/playwright/assets/`), reached through the `ProjectReference` the scaffold
  adds — never copied into the BDD project.
- Credentials come from `BaseTest.RequiredEnv`, which fails naming the missing variable; never
  `Environment.GetEnvironmentVariable(...)!`.
- The `Given` only navigates. Whether the page is ready is the `When`'s concern — Playwright's actions wait for
  their element — and whether the outcome happened is the `Then`'s.

### Step definition — `StepDefinitions/DealFilterSteps.cs` (controls, reference data, pre-clean)

```csharp
using Example.BddTests.Support;
using Example.TestCore.Seeders;
using NUnit.Framework;
using Reqnroll;
using static Microsoft.Playwright.Assertions;

namespace Example.BddTests.StepDefinitions;

[Binding]
public sealed class DealFilterSteps(ScenarioState state, DealSeeder deals)
{
    [Given("deal {string} does not exist")]
    public async Task GivenDealDoesNotExist(string title) => await deals.DeleteAllTitledAsync(title);

    [When("I filter deals by {string} and {string}")]
    public async Task WhenIFilterDealsBy(string dealType, string region) =>
        await state.Deals.FilterAsync(dealType, region);

    [When("I select {string} for Deal Type filter")]
    public async Task WhenISelectForDealTypeFilter(string option) => await state.Deals.DealType.SelectAsync(option);

    [When("I select {string} for Region filter")]
    public async Task WhenISelectForRegionFilter(string option) => await state.Deals.Region.SelectAsync(option);

    [Then("every listed deal has Deal Type {string}")]
    public async Task ThenEveryListedDealHasDealType(string dealType)
    {
        await Expect(state.Deals.Results.DataRows, "deals listed: the reference data").Not.ToHaveCountAsync(0);
        IReadOnlyList<string> dealTypes = await state.Deals.Results.ColumnValuesAsync("Deal Type");
        Assert.That(dealTypes, Is.All.EqualTo(dealType), "Deal Type of every listed deal");
    }
}
```

- `DealsPage` exposes `DealType` and `Region` (`Dropdown`) and `Results` (`DataGrid`); `FilterAsync` exists because filtering by both is a sequence, while a single-filter step acts on the control directly.
- The `Then` reads curated reference data: it asserts that rows came back (a web-first assertion that also waits) before `Is.All`, because an "every row" check over no rows proves nothing (`test-data.md`). Never `rows[0]` for the whole result, never a loop.
- `DealSeeder` is the suite's API seeder, registered in `[ScenarioDependencies]`; `DeleteAllTitledAsync` lists by title and deletes each match.

### Custom parameter type — `Support/Transforms.cs`

```csharp
using Reqnroll;

namespace Example.BddTests.Support;

[Binding]
public sealed class Transforms
{
    [StepArgumentTransformation(@"(\d+) days? ago")]
    public DateTime DaysAgo(int days) => DateTime.UtcNow.AddDays(-days);
}
```

### Mobile variant (Appium, sync)

Same shape, but step methods are synchronous and call the Appium page objects:

```csharp
[When("I sign in with email {string} and password {string}")]
public void WhenISignInWith(string email, string password) =>
    state.LoginScreen.Login(email, password);
```

## Procedure

1. Read the `.feature` files + Step Catalog + Cleanup handoff and the available page objects.
2. For each distinct catalog step, write **one** step method in the right domain binding class; reuse for repeats; one binding per field, filter or column.
3. Pick the binding keyword (`[Given]`/`[When]`/`[Then]`) from the catalog; use Cucumber-Expression params matching the catalog's `{...}` placeholders and `Examples` columns.
4. Implement each body with one page intent method or one call on an exposed control or element; put assertions in `Then` with web-first `Expect`.
5. Check no binding body is empty; a scenario not yet automatable is tagged `@not-automated` (or the suite's skip tag) with a ticket instead.
6. For any missing page object/method, build it (`page-object-design`/`page-objects-from-url`) before binding the step.
7. Ensure the Cleanup is implemented as the `[AfterScenario]` hook (scaffold layer), not as steps.
8. `dotnet build`, then run the features: every step bound (no undefined/ambiguous), the smoke scenario green.

## Rules

The standards this skill's output must meet are the qa-dotnet rule files, not a list here: `bdd.md`, `automation.md`, `test-data.md` (reference data and pre-clean), and `page-objects.md` plus `web-ui.md` or `mobile-ui.md` for the page objects the steps call. Read the project's copy in `.claude/rules/qa-dotnet/`, or the plugin's in `qa/dotnet/skills/rules/` when the project has not installed them (`/qa-dotnet:rules` does). Where they and this skill's recipes disagree, the rule files win.

## Handoffs

- `.feature` files / Step Catalog → `qa/_shared/bdd/feature-file-writer`
- Project/DI/hooks → `qa/dotnet/skills/bdd-project-scaffold`
- Page objects → `qa/dotnet/skills/page-object-design` / `page-objects-from-url` / `mobile-screen-objects`
- Review features + bindings → `qa/dotnet/skills/bdd-reviewer`
- Allure labels from tags → `qa/reporting/dotnet/skills/test-reports`
