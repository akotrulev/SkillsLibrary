---
name: page-object-design
description: Use when designing the page object structure for a .NET UI test project. Triggers "design page objects for app X". Not for a POM from a live URL (page-objects-from-url).
disable-model-invocation: true
---

# QA — Page Object Architect (.NET / C#)

Designs the **shape** of a Page Object Model in a .NET UI test project: page vs region component vs control component vs flow, base-class hierarchy, where controls and flows live, and how to split when one page gets too big. Output is an architecture sketch — folder tree + class responsibilities + decision rationale — not concrete page code.

## When to use

- Greenfield UI test suite — first POM layout in `Pages/`
- Existing suite has grown to 30+ pages and patterns are diverging
- Multi-platform app (web + mobile via Appium .NET) needs shared abstractions
- One page object has grown past ~200 lines and feels wrong
- Tests are slow / brittle and the root cause is structural

## When NOT to use

- Writing the page object code itself → `qa/dotnet/skills/ui-test-author/playwright`, `qa/dotnet/skills/ui-test-author/selenium`, or `qa/dotnet/skills/ui-test-author/appium`
- Reviewing a single existing page object → `qa/dotnet/skills/ui-test-author/review`
- Designing test data / fixtures → `qa/dotnet/skills/test-data-builder`
- Designing the entire test strategy → `qa/manual/test-strategy`
- Java POM architecture → `qa/java/skills/page-object-design`
- TypeScript POM architecture → `qa/typescript/skills/page-object-design`

## Inputs needed

1. **App shape** — single web app, mobile, or web + mobile
2. **Stacks in play** — Playwright .NET, Selenium .NET, Appium .NET, or a mix
3. **Existing structure** (if any) — file tree of `Pages/` / `AppiumTests/Pages/`
4. **Pain points** — what's brittle, slow, or duplicated
5. **Team shape** — one team or many
6. **Runner & report tooling** — NUnit (default) or xUnit; Allure or not

7. **Screen map** (mobile, if one exists) — `docs/app-map/screen-map.md` from `qa/dotnet/skills/mobile-app-crawler`. Its **Component candidates** table is counted evidence for the region-component call below; prefer it over guessing which elements recur.

## Core decisions

### The four kinds

| Kind | Models | Created | Examples |
|---|---|---|---|
| **Page** (screen, window) | One route / screen / window | Per screen | `LoginPage`, `CheckoutOverviewPage` |
| **Region component** | An app-specific part of a page with its own root: a form, a card, a nav menu, a row | When the region repeats on the page (rows, cards: always) or appears on a second page | `SignInForm`, `ProductCard`, `OrderRow`, `NavigationMenu` |
| **Control component** | A design-system widget: date picker, dropdown, combobox, data grid + grid row, pagination, modal, toast, tabs, file upload | **At first use** | `DatePicker`, `Dropdown`, `DataGrid`, `GridRow`, `Modal` |
| **Flow** | A sequence across several pages | When a test's setup needs it | `CheckoutFlow`, `SignInFlow` |

Rules of thumb:

- Has its own URL or screen → page.
- Comes from the design system or a UI library, or takes more than one driver call to operate → control component, the first time it is used. Caller count is not the test.
- Repeats on the page, or shows up on a second page → region component.
- A test's setup crosses several pages → a `<Something>Flow` class.
- A component takes its root in the constructor, exposes intent with domain-typed arguments (`checkout.DeliveryDate.SelectAsync(date)`), and never inherits the page base class. Two markups of "the same" widget (`Dropdown` over `<select>`, `Combobox` over a custom listbox) are two classes.
- A screen that repeats with a different label (one property page per section) is **one page class constructed with that data**: `new SimplePropertyPage(page, "Suicide Genes")`. The label is data that builds the locators, not a flag, so it is allowed; a `bool` or enum argument that selects behaviour becomes two methods or two classes (`page-objects.md`).

The Playwright control catalogue (root, intent methods, API per control) is [`ui-test-author/playwright/references/components.md`](../ui-test-author/playwright/references/components.md); its compiled examples are in `ui-test-author/playwright/assets/Components/Controls/`.

### Base class hierarchy

**Playwright: the default is no base class.** Pages take `IPage`, components take their root `ILocator`, and shared behaviour is a component field. Introduce `BasePage` only when a **third** concrete page shares real behaviour (not just the `IPage` field), and keep it to one level. **Selenium / Appium** use the thin `BasePage` / `BaseAppiumPage` their writer skills define (the driver, the finders and one wait).

```
<ConcretePage>                     ← Playwright default: no base
BasePage → <ConcretePage>          ← Playwright: only on the third real sharer; Selenium / Appium: the writer's thin base
```

Avoid:

- `BasePage → FormPage → MultiStepFormPage → CheckoutInformationPage` — four levels almost always hides imaginary abstractions, and a base class that only forwards to `IPage`
- A `MobileBasePage` + `DesktopBasePage` before there are 3+ concrete pages on each side

### Named application waits

A wait for the app's own busy signal (loading bar gone, snackbar gone) is a named wait condition on the base page or the shell component (`WaitUntilLoadedAsync()`), called by the action that triggers the load, never by the test. Playwright needs one only where auto-waiting cannot see the signal; Selenium and Appium put it on the thin base.

On a server-rendered page the hydration signal is a named wait too: `GoToAsync()` waits for `data-hydrated="true"` on `<body>`, and an intent method on a late-hydrating island waits on the island's own root, before it acts. Never visibility, never a sleep. Details: [`ui-test-author/playwright/references/server-rendered-pages.md`](../ui-test-author/playwright/references/server-rendered-pages.md).

### .NET driver-lifecycle implications for the design

- Pages must not own their own driver lifetime — `BaseTest` owns it. Pages take the `IPage` / driver in the constructor and are built in the test class's `[SetUp]`, never as properties of `BaseTest`.
- **Playwright:** the one `BaseTest : PageTest` (`qa/dotnet/skills/ui-test-author/playwright/assets/BaseTest.cs`) gives each test its own context and page, with `[Parallelizable(ParallelScope.Self)]` — the only scope Playwright supports. A role, a device or a locale is an override of `ContextOptions()` that amends `base.ContextOptions()`, never a second base class. **Selenium / Appium:** `AsyncLocal<IWebDriver>` in a `DriverFactory`. **Never** a `public static IWebDriver Driver`.
- Async-all-the-way (Playwright .NET, Appium .NET): page method signatures return `Task` / `Task<NextPage>`. No `.Result`/`.Wait()` ever — including inside `BasePage`.
- Selenium .NET is sync API; keep page methods sync there. **Do not** mix sync Selenium pages with async Playwright pages under the same `BasePage`.

### Multi-platform sharing

Three viable strategies, ordered by cost:

1. **Per-platform pages, shared flows** (cheapest, recommended default) — `Web/LoginPage.cs`, `Mobile/LoginPage.cs`; one `SignInFlow` per platform taking that platform's pages, or one taking an interface (strategy 2).
2. **Per-platform pages + a shared interface** (`ILoginPage`) — useful when both platforms drive the same domain workflow and a flow takes the interface.
3. **Abstract base + per-platform subclass** — only when the screens are truly the same minus locators.

Avoid the `if (Platform == "iOS") …` trap inside a single page — a page method never switches on the platform; the platform maps to a locator in the finder, the one place that branch is legal.

### Locator ownership

- Locators belong **inside the page / component class**, built once in the constructor — `private readonly ILocator` fields, with a described get-only property only for an assertion target no action uses (Playwright); `private static readonly By` (Selenium) or `private const string` ids (Appium), with no element exposed — never in the test. In a BDD suite the step definition is the intent layer, so a page the steps use may expose named controls and elements for a step to act on (`bdd.md`).
- A shared `Locators` constants file is an anti-smell. The only exception is brand-wide test ids (e.g. a project-wide `Nav.PrimaryCta`) — keep that file small.
- **A component takes its root** (an `ILocator`; on Selenium and Appium a root locator, or a row key it re-resolves) in the constructor and builds every child from it, so it works wherever it is mounted. The scoping mechanics — chaining from the root, `parent.Locator(child)` (the 1.63 form of the 1.64 `Within()`), `Filter(new() { Has = ... })`, strictness, positional picks — are owned by [`ui-test-author/playwright/references/locators.md`](../ui-test-author/playwright/references/locators.md); `assets/LoginPage.cs` there is the worked example.
- Every Playwright locator follows one ladder: `GetByTestId` → `GetByRole` → `GetByLabel` → `GetByPlaceholder` → `GetByText` → `GetByAltText` / `GetByTitle` → CSS. Selenium and Appium put the test id first too, then their writer's order. Test ids are PascalCase dot-separated and static (`OrderRow`, `OrderRow.Title`); a fallback is recorded in `missing-testids.md`, never marked in the code.

### Flows

- A flow is a class named `<Something>Flow` in `Flows/`: it takes its page objects in the constructor and has instance methods named for the journey (`SignInAsync(user)`, `CheckoutAsync(cart)`) that return the resulting page. No static flow class, no assertion, no state beyond its pages.
- **Playwright .NET**: pages are built in the test class's `[SetUp]`, and so is the flow over them. Records a test needs are seeded through `Page.APIRequest` in the same `[SetUp]` and deleted in its `[TearDown]`; the signed-in session is the root-namespace `AuthSetup` `[SetUpFixture]`. **Never seed in `[OneTimeSetUp]` of a `PageTest`:** no `Page` exists there, and a record shared by a fixture's tests makes them depend on each other.
- **Selenium .NET**: the same class with sync methods.
- **Appium .NET**: the same class; reset app state in `[SetUp]`.

## Recommended folder layouts

The Playwright single-app tree and the Selenium / Appium multi-platform tree are in [`references/folder-layouts.md`](references/folder-layouts.md): `Pages/` per feature, `Components/` for shared regions, `Components/Controls/` for design-system widgets, `Flows/`, and tests that seed their own data in `[SetUp]`.

## Splitting heuristics

A page object should split when **any** are true:

- File > ~200 lines (NUnit + explicit accessors lean a bit higher)
- More than 3 conceptually distinct UI sections (header + form + sidebar + footer)
- Two team members would name the same element differently because they describe it via different parent UI
- The same locator string appears identically on another page (region component candidate)
- A widget's driver calls (open, pick, confirm) are written inline in a page method (control component)
- More than one method modifies state that other methods need to inspect (page hiding sub-state — promote to component)

| Smell | Move |
|---|---|
| Repeated card across pages | Extract `ProductCard` / `Row` component scoped to a parent `ILocator` |
| Step-by-step flow (checkout, onboarding) | Sub-folder per step under `Pages/Checkout/` |
| Persistent shell (nav, footer) | Extract `NavigationMenu` / `SidePanel` exposed as a field on every page that has it |
| Modal / dialog | A `Modal` control returned from the action that opens it; the test asserts on its described locators |
| Cross-page widget (toast) | A `Toast` control property on each page that shows it, built from the page's root `ILocator` |
| Date picker, dropdown, grid operated inline | The matching control from `Components/Controls/`, exposed as a page property |

## Naming conventions

- Pages: `{Feature}Page` — `LoginPage`, `CheckoutOverviewPage`, `OrderHistoryPage`
- Region components: `{Element}` (no `Page` suffix) — `NavigationMenu`, `ProductCard`, `OrderRow`
- Control components: the widget named for its markup — `Dropdown`, `Combobox`, `DatePicker`, `DataGrid`, `GridRow`, `Modal`, `Toast`
- Flows: `{Something}Flow` with `{Verb}{Object}Async` methods (`{Verb}{Object}` on sync Selenium) — `CheckoutFlow.CheckoutAsync`
- Methods name the action (`SignInAsync`), never the outcome (`SuccessfulLogin`); no `Helper`, `Util` or `Common` anywhere
- Base classes: `Base{Type}` — `BasePage`, `BaseTest`, `BaseAppiumPage` — at most one of each
- Namespaces follow folders: `UiTests.Pages.Checkout`

## Output format

```markdown
# Page Object Architecture: <app name> (.NET)

## Folder tree
<proposed tree with one-line annotations>

## Class responsibilities
| Class | Type | Owns | Doesn't own |
|-------|------|------|-------------|
| LoginPage | page | `GoToAsync()`, the sign-in form component, `SignInAsync()` | assertions, the landing page's locators |
| ProductCard | region component | card-internal locators, `AddToCartAsync()` | iterating the product list |
| DatePicker | control component | its root and children, `SelectAsync(DateOnly)` | the page it is mounted on |
| CheckoutFlow | flow | the pages it takes, `CheckoutAsync(cart)` | assertions, state beyond its pages |

## Base hierarchy
<Playwright: none, unless a third page shares real behaviour — then name the three and what they share>

## Multi-platform strategy
<which of the three strategies + why>

## Migration plan (if existing code)
1. <smallest first refactor>
2. ...

## Open questions
- <question> — owner: <name>
```

## Rules

The page-object standards a design must meet are the qa-dotnet rule files, not a list here: `page-objects.md`, `automation.md`, `web-ui.md`, `mobile-ui.md` and `desktop-tests.md`. Read the project's copy in `.claude/rules/qa-dotnet/`, or the plugin's in `qa/dotnet/skills/rules/` when the project has not installed them (`/qa-dotnet:rules` does). Where they and this skill's recipes disagree, the rule files win.

## Design smells to flag

- **God page** (300+ lines, every selector in the app): split by screen and component.
- **Page returns DTOs**: that is API territory; page methods return the next page or visible state.
- **Locators in a central constants file**: couples every page change to one file.
- **Static flow, or a flow holding state beyond its pages**: a flow is a class over its pages with instance methods.
- **A control inlined in a page**: the page fills the date input, opens the listbox and clicks the option itself; extract the control.
- **One control class with a branch per markup**: two classes.
- **A `Helper` / `Util` / `Common` class**: find the missing role (page, component, flow, client, builder, seeder) and move the code there.
- **`BaseTest` doing app-specific work**: bases handle infrastructure (driver, context options, evidence), not domain workflow.
- **A test inheriting a page object** to reuse its methods: compose the page, or move the steps into a flow.

## Procedure

1. Collect inputs (skip questions answerable from the existing file tree).
2. Map every existing class (or every screen for greenfield) onto **page / region component / control component / flow / base**. List the design-system widgets in use first: each is a control, whatever its caller count.
3. Apply splitting heuristics to anything in the wrong bucket.
4. Decide whether a Playwright `BasePage` is warranted: only when a third page shares real behaviour. Pick the multi-platform strategy if relevant.
5. Produce the output: folder tree, responsibilities table, base hierarchy, migration plan (smallest refactor first).
6. Hand off code generation to the matching generator skill.

## Handoffs

- Implementing the design → `qa/dotnet/skills/ui-test-author/playwright`, `qa/dotnet/skills/ui-test-author/selenium`, or `qa/dotnet/skills/ui-test-author/appium`
- Reviewing existing pages → `qa/dotnet/skills/ui-test-author/review`
- Test data / builders → `qa/dotnet/skills/test-data-builder`
- Higher-level strategy → `qa/manual/test-strategy`
