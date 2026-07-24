---
name: qa-bdd-step-bindings-dotnet
description: Use when turning Gherkin .feature files into Reqnroll step definitions in C#/.NET, implementing each step against existing Page Object Models. Triggers: "generate Reqnroll step definitions for these features", "bind these Gherkin steps to our page objects", "split the step definitions by domain". Do NOT use to write the .feature files (`gherkin-authoring`), scaffold the Reqnroll project/hooks/DI (`bdd-project-scaffold`), or build page objects (`page-object-architect`). For end-to-end suite work prefer the phased agent `qa-bdd-dotnet` (or the matching slash command), which loads this skill inside its workflow; use this skill directly for a single targeted artifact.
---

# Reqnroll Step Bindings + POM Implementation (C# / .NET 8)

Parses `.feature` files (and the **Step Catalog** from `gherkin-authoring`) into Reqnroll `[Binding]` classes, **split by domain**, with parameterized Cucumber-Expression steps, and **implements each step by calling existing page-object intent methods**. Assertions live in `Then` steps; page objects only act and expose `ExpectLoadedAsync()`. The Reqnroll project, DI container, hooks, and `ScenarioState` already exist (from `bdd-project-scaffold`).

## Stack

- Reqnroll.NUnit 3.3.x + `Reqnroll.Microsoft.Extensions.DependencyInjection`
- C# / .NET 8, `async Task` step methods (Playwright web) or sync (Appium mobile)
- Page objects from the existing UI/mobile project (`qa/dotnet/skills/page-object-architect`)
- `Microsoft.Playwright.Assertions` (web-first `Expect`) for `Then` steps

## When to use

- `.feature` files exist (from `gherkin-authoring`) and need step definitions.
- A scenario reports **undefined** or **ambiguous** steps and needs bindings written/fixed.
- Implementing the bodies of generated step skeletons against page objects.

## When NOT to use

- Authoring/canonicalizing `.feature` files → `qa/_shared/bdd/gherkin-authoring`
- Project/DI/hooks scaffold → `qa/dotnet/skills/bdd-project-scaffold`
- Building or extracting page objects → `qa/dotnet/skills/page-object-architect` / `pom-builder` / `appium-page-object`
- Reviewing features + bindings → `qa/dotnet/skills/bdd-reviewer`
- Java/TS step glue → `qa/{java,typescript}/skills/bdd-step-bindings`

## Inputs needed

Confirm at most 2–3.

1. **The `.feature` files + Step Catalog** (from `gherkin-authoring`) and the **Cleanup handoff** note.
2. **The page objects** available (paths) — which intent methods exist; what's missing.
3. **Platform** — Playwright (async) or Appium (sync).

## Core rules

### 1. One binding class per domain, mapped to the Step Catalog

Group steps by feature/domain (`AuthenticationSteps`, `CartSteps`), **not** one giant `Steps.cs`. Each canonical Step-Catalog row becomes exactly one step method — reuse across scenarios, never duplicate. A step shared by many features goes in a `CommonSteps` binding.

### 2. Cucumber Expressions, not regex

Default to Cucumber Expressions (`{string}`, `{int}`, `{word}`, `{decimal}`, enums as `{MyEnum}`). Reqnroll auto-detects regex only if the pattern starts with `^`/ends with `$` or contains regex tokens — keep steps as plain Cucumber Expressions so the catalog params map cleanly. Custom types via `[StepArgumentTransformation]`.

### 3. Inject shared state via the constructor — never new up the page or use the context bag

Step classes take `ScenarioState` (the scoped DI object from the scaffold) in the constructor. The page/driver was created in the `[BeforeScenario]` hook; steps reach page objects through `_state`. No static fields, no `ScenarioContext["key"]` bag for typed state.

### 4. Steps are thin; mechanics live in page objects

A step body is one or two page-object calls. **No selectors, no `IPage.Locator(...)`, no waits in step definitions** — those belong in the page object. `Given`/`When` act; `Then` asserts with web-first `Expect(...)`. Page objects never assert (except `ExpectLoadedAsync()`).

### 5. Async all the way (web)

`async Task` step methods; `await` every page-object call. Never `.Result`/`.Wait()`. No `Thread.Sleep`/`WaitForTimeoutAsync` — rely on Playwright auto-waiting and web-first assertions.

### 6. Implement the Cleanup as a hook, not steps

The `gherkin-authoring` Cleanup handoff becomes an `[AfterScenario]` in the support layer (the scaffold owns hook placement) — never Gherkin steps and never a step definition.

### 7. Missing page objects → build them first

If a step needs a page object/method that doesn't exist, stop and build it via `page-object-architect`/`pom-builder` (or hand to `qa-ui-dotnet`/`qa-mobile-dotnet`). Do not inline locators into the step to "make it pass."

## Templates

### Step definition — `StepDefinitions/AuthenticationSteps.cs` (Playwright/web)

```csharp
using Microsoft.Playwright;
using Reqnroll;
using Bdd.Tests.Support;
using static Microsoft.Playwright.Assertions;

namespace Bdd.Tests.StepDefinitions;

[Binding]
public sealed class AuthenticationSteps
{
    private readonly ScenarioState _state;

    public AuthenticationSteps(ScenarioState state) => _state = state;

    [Given("I am on the login page")]
    public async Task GivenIAmOnTheLoginPage()
    {
        await _state.Login.GoToAsync();
        await _state.Login.ExpectLoadedAsync();
    }

    [When("I sign in as a registered customer")]
    public async Task WhenISignInAsRegisteredCustomer() =>
        await _state.Login.SignInAsync(
            Environment.GetEnvironmentVariable("E2E_USER")!,
            Environment.GetEnvironmentVariable("E2E_PASSWORD")!);

    [When("I sign in with email {string} and password {string}")]
    public async Task WhenISignInWith(string email, string password) =>
        await _state.Login.SignInAsync(email, password);

    [Then("I land on the dashboard")]
    public async Task ThenILandOnTheDashboard() =>
        await _state.Dashboard.ExpectLoadedAsync();

    [Then("I see the error {string}")]
    public async Task ThenISeeTheError(string message) =>
        await Expect(_state.Login.ErrorBanner).ToHaveTextAsync(message);
}
```

### Custom parameter type — `Support/Transforms.cs`

```csharp
using Reqnroll;

namespace Bdd.Tests.Support;

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
    _state.LoginScreen.Login(email, password);
```

## Procedure

1. Read the `.feature` files + Step Catalog + Cleanup handoff and the available page objects.
2. For each distinct catalog step, write **one** step method in the right domain binding class; reuse for repeats.
3. Pick the binding keyword (`[Given]`/`[When]`/`[Then]`) from the catalog; use Cucumber-Expression params matching the catalog's `{...}` placeholders and `Examples` columns.
4. Implement each body with page-object calls only; put assertions in `Then` with web-first `Expect`.
5. For any missing page object/method, build it (`page-object-architect`/`pom-builder`) before binding the step.
6. Ensure the Cleanup is implemented as the `[AfterScenario]` hook (scaffold layer), not as steps.
7. `dotnet build`, then run the features: every step bound (no undefined/ambiguous), the smoke scenario green.

## Anti-patterns to flag

- One mega step-definition file instead of per-domain classes.
- Duplicate step methods for steps the catalog already unified — parameterize and reuse.
- `IPage.Locator(...)`, CSS, or waits inside step definitions — promote to a page object.
- `new LoginPage(page)` or static state inside a step — inject `ScenarioState`.
- `ScenarioContext["x"]` string-bag for typed state — use DI.
- Assertions inside page-object actions, or `When`/`Given` doing assertions.
- `Thread.Sleep` / `WaitForTimeoutAsync` / `.Result` / `.Wait()`.
- Regex step expressions where a Cucumber Expression reads cleaner.
- Implementing Cleanup as Gherkin/steps instead of an `[AfterScenario]` hook.

## Handoffs

- `.feature` files / Step Catalog → `qa/_shared/bdd/gherkin-authoring`
- Project/DI/hooks → `qa/dotnet/skills/bdd-project-scaffold`
- Page objects → `qa/dotnet/skills/page-object-architect` / `pom-builder` / `appium-page-object`
- Review features + bindings → `qa/dotnet/skills/bdd-reviewer`
- Allure labels from tags → `qa/reporting/dotnet/skills/allure-reporting`
