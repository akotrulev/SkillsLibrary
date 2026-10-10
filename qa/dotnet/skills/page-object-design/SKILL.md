---
name: qa-page-object-design-dotnet
description: Use when the user is designing the page object structure for a .NET UI test project. Triggers: "design page objects for app X in C#", "how should I structure Pages/ for our NUnit suite", "split this giant ILocator-heavy page". Do NOT use for extracting locators from a live URL (`qa-page-objects-from-url-dotnet`) or Appium screens (`qa-mobile-screen-objects-dotnet`).
---

# QA — Page Object Architect (.NET / C#)

Designs the **shape** of a Page Object Model in a .NET UI test project: page vs component vs flow, base-class hierarchy, where shared locators and helpers live, and how to split when one page gets too big. Output is an architecture sketch — folder tree + class responsibilities + decision rationale — not concrete page code.

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

7. **Screen map** (mobile, if one exists) — `docs/app-map/screen-map.md` from `qa/dotnet/skills/mobile-app-crawler`. Its **Component candidates** table is counted evidence for the "reused on 2+ screens → component" call below; prefer it over guessing which elements recur.

## Core decisions

### Page vs component vs flow

| Concept | What it models | Lifetime | Examples |
|---|---|---|---|
| **Page** | A discrete screen / route | One per URL or top-level navigation target | `LoginPage`, `CheckoutOverviewPage` |
| **Component** | A reusable piece appearing inside multiple pages | Scoped to a parent `ILocator` / `IWebElement` | `ProductCard`, `NavigationMenu`, `Modal`, `Toast` |
| **Flow** | An end-to-end sequence across pages | None — a `static` helper | `SignInAndCheckoutAsync(user, cart)` |

Rules of thumb:

- Has its own URL → page
- Reused on 2+ pages → component
- Touches 3+ pages → flow helper, not a class
- When in doubt → **component**. Pages turn into hairballs faster than components do.

### Base class hierarchy

**Playwright: the default is no base class.** Pages take `IPage`, components take their root `ILocator`, and shared behaviour is a component field. Introduce `BasePage` only when a **third** concrete page shares real behaviour (not just the `IPage` field), and keep it to one level. **Selenium / Appium** use the thin `BasePage` / `BaseAppiumPage` their writer skills define (the driver plus one synchronization helper).

```
<ConcretePage>                     ← Playwright default: no base
BasePage → <ConcretePage>          ← Playwright: only on the third real sharer; Selenium / Appium: the writer's thin base
```

Avoid:

- `BasePage → FormPage → MultiStepFormPage → CheckoutInformationPage` — four levels almost always hides imaginary abstractions, and a base class that only forwards to `IPage`
- A `MobileBasePage` + `DesktopBasePage` before there are 3+ concrete pages on each side

### .NET driver-lifecycle implications for the design

- Pages must not own their own driver lifetime — `BaseTest` owns it. Pages take the `IPage` / driver in the constructor and are built in the test class's `[SetUp]`, never as properties of `BaseTest`.
- **Playwright:** the one `BaseTest : PageTest` (`qa/dotnet/skills/ui-test-author/playwright/assets/BaseTest.cs`) gives each test its own context and page, with `[Parallelizable(ParallelScope.Self)]` — the only scope Playwright supports. A role, a device or a locale is an override of `ContextOptions()` that amends `base.ContextOptions()`, never a second base class. **Selenium / Appium:** `AsyncLocal<IWebDriver>` in a `DriverFactory`. **Never** a `public static IWebDriver Driver`.
- Async-all-the-way (Playwright .NET, Appium .NET): page method signatures return `Task` / `Task<NextPage>`. No `.Result`/`.Wait()` ever — including inside `BasePage`.
- Selenium .NET is sync API; keep page methods sync there. **Do not** mix sync Selenium pages with async Playwright pages under the same `BasePage`.

### Multi-platform sharing

Three viable strategies, ordered by cost:

1. **Per-platform pages, shared flow helpers** (cheapest, recommended default) — `Web/LoginPage.cs`, `Mobile/LoginPage.cs`; one shared `SignInFlow.SignInAsync(loginPage, user)`.
2. **Per-platform pages + a shared interface** (`ILoginPage`) — useful when both platforms drive the same domain workflow and a flow takes the interface.
3. **Abstract base + per-platform subclass** — only when the screens are truly the same minus locators.

Avoid the `if (Platform == "iOS") …` trap inside a single page — that conditional logic in pages contradicts the global "no conditional logic in tests" rule.

### Locator ownership

- Locators belong **inside the page / component class**, built once in the constructor — `private readonly ILocator` fields or get-only properties (Playwright), `private static readonly By` (Selenium / Appium) — never in the test.
- A shared `Locators` constants file is an anti-smell. The only exception is brand-wide test ids (e.g. a project-wide `Nav.PrimaryCta`) — keep that file small.
- **A component takes its parent `ILocator`** (`IWebElement` on Selenium) in the constructor and builds every child from it, so it works wherever it is mounted. The scoping mechanics — chaining from the root, `parent.Locator(child)` (the 1.63 form of the 1.64 `Within()`), `Filter(new() { Has = ... })`, strictness, positional picks — are owned by [`ui-test-author/playwright/references/locators.md`](../ui-test-author/playwright/references/locators.md); `assets/LoginPage.cs` there is the worked example.
- Every Playwright locator follows one ladder: `GetByTestId` → `GetByRole` → `GetByLabel` → `GetByPlaceholder` → `GetByText` → `GetByAltText` / `GetByTitle` → CSS. Selenium and Appium put the test id first too, then their writer's order. Test ids are PascalCase dot-separated and static (`OrderRow`, `OrderRow.Title`); a fallback is recorded in `missing-testids.md`, never marked in the code.

### Where flow helpers live

- **Playwright .NET**: a `Flows/` static class whose methods take page objects and return the resulting page. Records a test needs are seeded through `Page.APIRequest` in the test class's own `[SetUp]` and deleted in its `[TearDown]`; the signed-in session is the root-namespace `AuthSetup` `[SetUpFixture]`. **Never seed in `[OneTimeSetUp]` of a `PageTest`:** no `Page` exists there, and a record shared by a fixture's tests makes them depend on each other.
- **Selenium .NET**: `Flows/CheckoutFlow.cs` with `public static async Task SignInAsync(...)` (when paired with async helpers) or sync static methods.
- **Appium .NET**: same pattern as Selenium; reset app state in `[SetUp]`.

A flow helper does **not** own assertions — it sets up state and returns the resulting page object.

## Recommended folder layouts

### Playwright .NET (single web app)

```
UiTests/
├── UiTests.csproj
├── ui.runsettings               ← browser, headless, expect timeout, test-id attribute
├── AuthSetup.cs                 ← root namespace: signed-in state, once per run
├── Support/
│   └── BaseTest.cs              ← the one lifecycle (ui-test-author/playwright assets)
├── Pages/
│   ├── LoginPage.cs
│   ├── Catalog/
│   │   ├── ProductListPage.cs
│   │   └── ProductCard.cs       ← component, takes ILocator parent
│   └── Checkout/
│       ├── InformationPage.cs
│       ├── OverviewPage.cs
│       └── CompletePage.cs
├── Components/                  ← cross-feature shells
│   ├── NavigationMenu.cs
│   └── Toast.cs
├── Flows/
│   └── CheckoutFlow.cs
└── Tests/
    └── CheckoutTests.cs         ← seeds its data in its own [SetUp]
```

Configuration lives in the `.runsettings`; there is no `playwright.config.ts` in a .NET project.

### Selenium .NET / Appium .NET (multi-platform)

```
UiTests/
├── BaseTest.cs
├── Driver/
│   ├── DriverFactory.cs         ← AsyncLocal<IWebDriver>
│   └── AppiumDriverFactory.cs
├── Pages/
│   ├── BasePage.cs
│   ├── Web/
│   │   ├── LoginPage.cs
│   │   └── …
│   └── Mobile/
│       ├── BaseAppiumPage.cs
│       ├── LoginPage.cs
│       └── …
├── Components/
└── Flows/
    └── CheckoutFlow.cs
```

## Splitting heuristics

A page object should split when **any** are true:

- File > ~200 lines (NUnit + explicit accessors lean a bit higher)
- More than 3 conceptually distinct UI sections (header + form + sidebar + footer)
- Two team members would name the same element differently because they describe it via different parent UI
- The same locator string appears identically on another page (component candidate)
- More than one method modifies state that other methods need to inspect (page hiding sub-state — promote to component)

| Smell | Move |
|---|---|
| Repeated card across pages | Extract `ProductCard` / `Row` component scoped to a parent `ILocator` |
| Step-by-step flow (checkout, onboarding) | Sub-folder per step under `Pages/Checkout/` |
| Persistent shell (nav, footer) | Extract `NavigationMenu` / `SidePanel` exposed as a field on every page that has it |
| Modal / dialog | Return modal class from the action that opens it; assertion on the modal |
| Cross-page widget (toast) | A `Toast` component property on each page that shows it, built from the page's root `ILocator` |

## Naming conventions

- Pages: `{Feature}Page` — `LoginPage`, `CheckoutOverviewPage`, `OrderHistoryPage`
- Components: `{Element}` (no `Page` suffix) — `NavigationMenu`, `ProductCard`, `Toast`, `LoginModal`
- Flow helpers: `{Verb}{Object}Async` for async, `{Verb}{Object}` for sync — `SignInAsync`, `SeedOrder`
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
| ProductCard | component | card-internal locators, `AddToCartAsync()` | iterating the product list |

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

## Anti-patterns to flag

- **God page** (300+ lines, every selector in the app)
- **Inheritance for code reuse** — prefer composition
- **Page returns DTOs** — that's API territory; page methods return next pages or visible text
- **Locators in a central constants file** — couples every page change to one file
- **Flow class with state** — flows are functions, not stateful objects
- **`PageFactory` + explicit `FindElement` mixed** in the same project — pick one (explicit; `PageFactory` is deprecated)
- **`BaseTest` doing app-specific work** — bases handle infrastructure (driver, context options, evidence), not domain workflow; page objects are not `BaseTest` properties
- **Playwright `BasePage` before a third concrete page shares real behaviour**, or a base that only holds `IPage`
- **Seeding in `[OneTimeSetUp]`** of a Playwright fixture — no `Page` exists there; seed per test in `[SetUp]`
- **`Test extends a page object`** to "reuse helpers" — push the helper into a flow
- **`public static IWebDriver Driver`** or `ParallelScope.All` with Playwright — breaks parallel execution; Playwright uses `PageTest` with `ParallelScope.Self`, Selenium / Appium an `AsyncLocal<IWebDriver>` factory
- **`.Result` / `.Wait()`** in `BasePage` to bridge sync test code over async Playwright — make the chain async

## Procedure

1. Collect inputs (skip questions answerable from the existing file tree).
2. Map every existing class (or every screen for greenfield) onto **page / component / flow / base**.
3. Apply splitting heuristics to anything in the wrong bucket.
4. Decide whether a Playwright `BasePage` is warranted: only when a third page shares real behaviour. Pick the multi-platform strategy if relevant.
5. Produce the output: folder tree, responsibilities table, base hierarchy, migration plan (smallest refactor first).
6. Hand off code generation to the matching generator skill.

## Handoffs

- Implementing the design → `qa/dotnet/skills/ui-test-author/playwright`, `qa/dotnet/skills/ui-test-author/selenium`, or `qa/dotnet/skills/ui-test-author/appium`
- Reviewing existing pages → `qa/dotnet/skills/ui-test-author/review`
- Test data / builders → `qa/dotnet/skills/test-data-builder`
- Higher-level strategy → `qa/manual/test-strategy`
