---
name: qa-page-object-architect-java
description: Use when the user is designing the page object structure for a Java UI test project. Triggers: "design page objects for app X in Java", "how should I structure pom/ for TestNG", "split this giant page".
---

# QA — Page Object Architect (Java)

Designs the **shape** of a Page Object Model in a Java UI test project (Gradle Kotlin DSL + TestNG by default): page vs component vs flow, base-class hierarchy, where shared locators and helpers live, and how to split when one page gets too big. Output is an architecture sketch — package tree + class responsibilities + decision rationale — not concrete page code.

## When to use

- Greenfield UI test suite — first POM layout in `pom/`
- Existing suite has grown to 30+ pages and patterns are diverging
- Multi-platform app (web + mobile via Appium Java) needs shared abstractions
- One page object has grown past ~250 lines (Java explicit-accessor style runs longer than .NET/TS) and feels wrong
- Tests are slow / brittle and the root cause is structural

## When NOT to use

- Writing the page object code itself → `qa/java/skills/ui-test-author/playwright`, `qa/java/skills/ui-test-author/selenium`, or `qa/java/skills/ui-test-author/appium`
- Reviewing a single existing page object → `qa/java/skills/ui-test-author/reviewer`
- Designing test data / fixtures → `qa/java/skills/test-data-builder`
- Designing the entire test strategy → `qa/manual/test-strategy`
- .NET POM architecture → `qa/dotnet/skills/page-object-architect`
- TypeScript POM architecture → `qa/typescript/skills/page-object-architect`

## Inputs needed

1. **App shape** — single web app, mobile, or web + mobile
2. **Stacks in play** — Playwright Java, Selenium Java, Appium Java, or a mix
3. **Existing structure** (if any) — package tree of `pom/`
4. **Pain points** — what is brittle, slow, or duplicated
5. **Team shape** — one team or many
6. **Runner & build tool** — TestNG (default) or JUnit 5; Gradle (Kotlin DSL preferred) or Maven; Allure or not

## Core decisions

### Page vs component vs flow

| Concept | What it models | Lifetime | Examples |
|---|---|---|---|
| **Page** | A discrete screen / route | One per URL or top-level navigation target | `LoginPage`, `CheckoutOverviewPage` |
| **Component** | A reusable piece appearing inside multiple pages | Scoped to a parent `WebElement` / `Locator` | `ProductCard`, `NavigationMenu`, `Modal`, `Toast` |
| **Flow** | An end-to-end sequence across pages | None — a class with static methods, or a `@BeforeMethod` helper | `CheckoutFlow.signInAndCheckout(user, cart)` |

Rules of thumb:

- Has its own URL → page
- Reused on 2+ pages → component
- Touches 3+ pages → flow helper, not a class
- When in doubt → **component**

### Base class hierarchy

Keep it **shallow** — at most two levels.

```
BasePage              ← driver/page field, common waits, verifyPageLoaded() abstract
 └─ (rarely) AuthenticatedPage — only if every signed-in page truly shares something
 └─ <ConcretePage>
```

Avoid: `BasePage → FormPage → MultiStepFormPage → CheckoutInformationPage` (four levels usually hide imaginary abstractions).

### Java driver-lifecycle implications for the design

- Pages must not own driver lifetime — `BaseTest` (or a `DriverFactory`) owns it. Pages take the driver in the constructor.
- **Parallel safety:** Selenium / Appium drivers must come from a `ThreadLocal<WebDriver>` in `DriverFactory`. **Never** a `public static WebDriver driver`. With TestNG `parallel="methods"`, anything else races.
- **Playwright Java** is sync — page methods are sync (`void` or `NextPage`); no async/CompletableFuture in the POM.
- **Mixing Playwright + Selenium pages under one `BasePage` is rarely worth it** — keep the bases separate and only share component-level behavior (e.g. a `Toast` interface).
- Build: **Gradle Kotlin DSL** for new projects; Maven only when the project standard mandates it.

### Multi-platform sharing

Three viable strategies, ordered by cost:

1. **Per-platform pages, shared flow helpers** (cheapest, recommended default) — `pom.web.LoginPage`, `pom.mobile.LoginPage`; one shared `CheckoutFlow.signIn(loginPage, user)` accepting either via a small interface.
2. **Per-platform pages + a shared interface** (`LoginScreen`) — useful when both platforms drive the same domain workflow.
3. **Abstract base + per-platform subclass** — only when the screens are truly the same minus locators.

Avoid `if (platform.equals("iOS")) …` inside a single page object.

### Locator ownership

- Locators belong **inside the page / component class** as `private static final By` (Selenium / Appium) or `private final Locator` fields (Playwright Java) — never in tests.
- A shared `Locators` constants class is an anti-smell. The only exception is brand-wide a11y test ids.
- Components scoped to a parent take that parent `WebElement` / `Locator` in the constructor and query inside it.
- **No `@FindBy`** when the project standard is explicit `findElement`. Don't mix the two.

### Where flow helpers live

- **Playwright Java / Selenium Java / Appium Java**: `pom.flows.CheckoutFlow` with public static methods. Returns the resulting page object — never asserts.
- For test-setup-only flows (seeded session, app reset), a specialized `BaseTest` with `@BeforeMethod` is fine — keep it free of business logic.

## Recommended package layouts

### Playwright Java (single web app)

```
src/test/java/com/{org}/uitests/
├── BaseTest.java
├── pom/
│   ├── BasePage.java
│   ├── LoginPage.java
│   ├── catalog/
│   │   ├── ProductListPage.java
│   │   └── ProductCard.java        ← component, takes Locator parent
│   └── checkout/
│       ├── InformationPage.java
│       ├── OverviewPage.java
│       └── CompletePage.java
├── components/                     ← cross-feature shells
│   ├── NavigationMenu.java
│   └── Toast.java
├── flows/
│   └── CheckoutFlow.java
└── fixtures/
    └── SeededCartFixture.java
```

### Selenium Java / Appium Java (multi-platform)

```
src/test/java/com/{org}/uitests/
├── BaseTest.java
├── driver/
│   ├── DriverFactory.java          ← ThreadLocal<WebDriver>
│   └── AppiumDriverFactory.java
├── pom/
│   ├── BasePage.java
│   ├── web/
│   │   ├── LoginPage.java
│   │   └── …
│   └── mobile/
│       ├── BaseAppiumPage.java
│       ├── LoginPage.java
│       └── …
├── components/
└── flows/
    └── CheckoutFlow.java
```

## Splitting heuristics

A page object should split when **any** are true:

- File > ~250 lines (Java's explicit `findElement` style runs a bit longer than .NET/TS)
- More than 3 conceptually distinct UI sections (header + form + sidebar + footer)
- Two team members would name the same element differently because they describe it via different parent UI
- The same locator string appears identically on another page (component candidate)
- More than one method modifies state another method needs to inspect (page hiding sub-state — promote to component)

| Smell | Move |
|---|---|
| Repeated card across pages | Extract `ProductCard` / `Row` component scoped to a parent `WebElement` |
| Step-by-step flow (checkout, onboarding) | Sub-package per step under `pom/checkout/` |
| Persistent shell (nav, footer) | Extract `NavigationMenu` / `SidePanel` exposed as a field on every page that has it |
| Modal / dialog | Return modal class from the action that opens it; assertion on the modal |
| Cross-page widget (toast) | Hang off `BasePage` so every page exposes `toast()` |

## Naming conventions

- Pages: `{Feature}Page` — `LoginPage`, `CheckoutOverviewPage`
- Components: `{Element}` (no `Page` suffix) — `NavigationMenu`, `ProductCard`, `Toast`
- Flow helpers: `{Verb}{Object}` static methods on `{Feature}Flow` — `CheckoutFlow.signIn(...)`
- Base classes: `Base{Type}` — `BasePage`, `BaseAppiumPage`, `BaseTest` — at most one of each per stack
- Packages: lowercase, follow folders (`com.{org}.uitests.pom.checkout`)

## Output format

```markdown
# Page Object Architecture: <app name> (Java)

## Package tree
<proposed tree with one-line annotations>

## Class responsibilities
| Class | Type | Owns | Doesn't own |
|-------|------|------|-------------|
| BasePage | base | driver field, wait helpers, `verifyPageLoaded()` abstract | assertions, business logic |
| LoginPage | page | login form locators, `signIn()` | navigation to product list (returns `ProductListPage`) |
| ProductCard | component | card-internal locators, `addToCart()` | iterating the product list |

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
- **Flow class with mutable state** — flows are stateless static methods
- **`@FindBy` + explicit `findElement` mixed** in the same project — pick one
- **`BaseTest` doing app-specific work** — bases handle infrastructure (driver, fixtures), not domain workflow
- **Test extends a page object** to "reuse helpers" — push the helper into a flow or `BaseTest`
- **`public static WebDriver driver`** — breaks TestNG parallel execution; use `ThreadLocal<WebDriver>` in a factory
- **Mixing implicit + explicit waits** in `BasePage` — `driver.manage().timeouts().implicitlyWait(...)` together with `WebDriverWait` causes unpredictable timeouts; pick explicit

## Procedure

1. Collect inputs (skip questions answerable from the existing package tree).
2. Map every existing class (or every screen for greenfield) onto **page / component / flow / base**.
3. Apply splitting heuristics to anything in the wrong bucket.
4. Pick the multi-platform strategy if relevant.
5. Produce the output: package tree, responsibilities table, base hierarchy, migration plan (smallest refactor first).
6. Hand off code generation to the matching generator skill.

## Handoffs

- Implementing the design → `qa/java/skills/ui-test-author/playwright`, `qa/java/skills/ui-test-author/selenium`, or `qa/java/skills/ui-test-author/appium`
- Reviewing existing pages → `qa/java/skills/ui-test-author/reviewer`
- Test data / builders → `qa/java/skills/test-data-builder`
- Higher-level strategy → `qa/manual/test-strategy`
