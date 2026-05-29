---
name: qa-page-object-architect-dotnet
description: Use when the user is designing the page object structure for a .NET UI test project — Playwright .NET, Selenium .NET, or Appium .NET — what becomes a page, what becomes a component, where `BasePage` lives, how to split a giant page object, and how to share code across platforms. Triggers: "design page objects for app X in C#", "how should I structure Pages/ for our NUnit suite", "split this giant ILocator-heavy page", "where does this shared helper go in our Playwright .NET project". Do NOT use for individual page code (use `qa/ui-test-author/playwright/dotnet`, `qa/ui-test-author/selenium/dotnet`, or `qa/ui-test-author/appium/dotnet`), reviewing one file (use `qa/ui-test-author/reviewer/dotnet`), Java POM architecture (use `qa/page-object-architect/java`), or TypeScript POM architecture (use `qa/page-object-architect/typescript`).
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

- Writing the page object code itself → `qa/ui-test-author/playwright/dotnet`, `qa/ui-test-author/selenium/dotnet`, or `qa/ui-test-author/appium/dotnet`
- Reviewing a single existing page object → `qa/ui-test-author/reviewer/dotnet`
- Designing test data / fixtures → `qa/test-data-builder/dotnet`
- Designing the entire test strategy → `qa/_shared/test-strategy`
- Java POM architecture → `qa/page-object-architect/java`
- TypeScript POM architecture → `qa/page-object-architect/typescript`

## Inputs needed

1. **App shape** — single web app, mobile, or web + mobile
2. **Stacks in play** — Playwright .NET, Selenium .NET, Appium .NET, or a mix
3. **Existing structure** (if any) — file tree of `Pages/` / `AppiumTests/Pages/`
4. **Pain points** — what's brittle, slow, or duplicated
5. **Team shape** — one team or many
6. **Runner & report tooling** — NUnit (default) or xUnit; Allure or not

## Core decisions

### Page vs component vs flow

| Concept | What it models | Lifetime | Examples |
|---|---|---|---|
| **Page** | A discrete screen / route | One per URL or top-level navigation target | `LoginPage`, `CheckoutOverviewPage` |
| **Component** | A reusable piece appearing inside multiple pages | Scoped to a parent `ILocator` / `IWebElement` | `ProductCard`, `NavigationMenu`, `Modal`, `Toast` |
| **Flow** | An end-to-end sequence across pages | None — `static` helper or `[OneTimeSetUp]`-driven fixture | `SignInAndCheckoutAsync(user, cart)` |

Rules of thumb:

- Has its own URL → page
- Reused on 2+ pages → component
- Touches 3+ pages → flow helper, not a class
- When in doubt → **component**. Pages turn into hairballs faster than components do.

### Base class hierarchy

Keep it **shallow** — at most two levels.

```
BasePage              ← Page/IWebDriver field, common waits, ExpectLoadedAsync abstract method
 └─ (rarely) AuthenticatedPage — only if every signed-in page truly shares something (header, sign-out)
 └─ <ConcretePage>
```

Avoid:

- `BasePage → FormPage → MultiStepFormPage → CheckoutInformationPage` — four levels almost always hides imaginary abstractions
- A `MobileBasePage` + `DesktopBasePage` before there are 3+ concrete pages on each side

### .NET driver-lifecycle implications for the design

- Pages must not own their own driver lifetime — `BaseTest` (or NUnit `PageTest` in Playwright .NET) owns it. Pages take the driver via constructor.
- For parallel test execution, the driver/Page is per-test. Use `AsyncLocal<IWebDriver>` in `DriverFactory` (Selenium / Appium) or NUnit's built-in `PageTest` (Playwright). **Never** a `public static IWebDriver Driver`.
- Async-all-the-way (Playwright .NET, Appium .NET): page method signatures return `Task` / `Task<NextPage>`. No `.Result`/`.Wait()` ever — including inside `BasePage`.
- Selenium .NET is sync API; keep page methods sync there. **Do not** mix sync Selenium pages with async Playwright pages under the same `BasePage`.

### Multi-platform sharing

Three viable strategies, ordered by cost:

1. **Per-platform pages, shared flow helpers** (cheapest, recommended default) — `Web/LoginPage.cs`, `Mobile/LoginPage.cs`; one shared `SignInFlow.SignInAsync(loginPage, user)`.
2. **Per-platform pages + a shared interface** (`ILoginPage`) — useful when both platforms drive the same domain workflow and a flow takes the interface.
3. **Abstract base + per-platform subclass** — only when the screens are truly the same minus locators.

Avoid the `if (Platform == "iOS") …` trap inside a single page — that conditional logic in pages contradicts the global "no conditional logic in tests" rule.

### Locator ownership

- Locators belong **inside the page / component class** as `private readonly ILocator` fields (Playwright) or `private static readonly By` (Selenium / Appium) — never in the test.
- A shared `Locators` constants file is an anti-smell. The only exception is brand-wide a11y test ids (e.g. a project-wide `primary-cta` test id) — keep that file small.
- Components scoped to a parent take that parent in the constructor and query inside it. Don't re-query from the root.

### Where flow helpers live

- **Playwright .NET**: `Fixtures/` static class methods or a custom `BaseTest` extending `PageTest` that seeds state in `[OneTimeSetUp]`. Don't use `[SetUp]`-per-test when state can be seeded once per worker.
- **Selenium .NET**: `Flows/CheckoutFlow.cs` with `public static async Task SignInAsync(...)` (when paired with async helpers) or sync static methods.
- **Appium .NET**: same pattern as Selenium; reset app state in `[SetUp]`.

A flow helper does **not** own assertions — it sets up state and returns the resulting page object.

## Recommended folder layouts

### Playwright .NET (single web app)

```
UiTests/
├── BaseTest.cs                 ← extends PageTest, fixtures
├── Pages/
│   ├── BasePage.cs
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
├── Fixtures/
│   └── SeededCartFixture.cs
└── playwright.config.ts (if used)
```

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
| Cross-page widget (toast) | Hang off `BasePage` so every page exposes `Toast()` |

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
| BasePage | base | `IPage`/`IWebDriver` field, wait helpers, `ExpectLoadedAsync` abstract | assertions, business logic |
| LoginPage | page | login form locators, `SignInAsync()` | navigation to product list (returns `ProductListPage`) |
| ProductCard | component | card-internal locators, `AddToCartAsync()` | iterating the product list |

## Base hierarchy
<3-line description>

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
- **`BaseTest` doing app-specific work** — bases handle infrastructure (driver, fixtures), not domain workflow
- **`Test extends a page object`** to "reuse helpers" — push the helper into a fixture or base test
- **`public static IWebDriver Driver`** — breaks parallel execution; use `AsyncLocal<IWebDriver>` in a factory
- **`.Result` / `.Wait()`** in `BasePage` to bridge sync test code over async Playwright — make the chain async

## Procedure

1. Collect inputs (skip questions answerable from the existing file tree).
2. Map every existing class (or every screen for greenfield) onto **page / component / flow / base**.
3. Apply splitting heuristics to anything in the wrong bucket.
4. Pick the multi-platform strategy if relevant.
5. Produce the output: folder tree, responsibilities table, base hierarchy, migration plan (smallest refactor first).
6. Hand off code generation to the matching generator skill.

## Handoffs

- Implementing the design → `qa/ui-test-author/playwright/dotnet`, `qa/ui-test-author/selenium/dotnet`, or `qa/ui-test-author/appium/dotnet`
- Reviewing existing pages → `qa/ui-test-author/reviewer/dotnet`
- Test data / builders → `qa/test-data-builder/dotnet`
- Higher-level strategy → `qa/_shared/test-strategy`

## Changelog

- 2026-05-29: Split from monolithic `qa/page-object-architect/SKILL.md` into the .NET sibling. Adds .NET-specific guidance: `AsyncLocal<IWebDriver>` for parallel safety, NUnit `PageTest` lifecycle, sync Selenium vs async Playwright separation, nullable reference types in page fields, and recommended `Pages/` + `Components/` + `Fixtures/` layout.
