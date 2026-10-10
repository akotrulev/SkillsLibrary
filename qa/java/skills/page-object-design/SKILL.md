---
name: qa-page-object-design-java
description: Use when the user is designing the page object structure for a Java UI test project. Triggers: "design page objects for app X in Java", "how should I structure pom/ for TestNG", "split this giant page". Do NOT use for extracting locators from a live URL (`qa-page-objects-from-url-java`) or Appium screens (`qa-mobile-screen-objects-java`).
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
- Reviewing a single existing page object → `qa/java/skills/ui-test-author/review`
- Designing test data / fixtures → `qa/java/skills/test-data-builder`
- Designing the entire test strategy → `qa/manual/test-strategy`
- .NET POM architecture → `qa/dotnet/skills/page-object-design`
- TypeScript POM architecture → `qa/typescript/skills/page-object-design`

## Inputs needed

1. **App shape** — single web app, mobile, or web + mobile
2. **Stacks in play** — Playwright Java, Selenium Java, Appium Java, or a mix
3. **Existing structure** (if any) — package tree of `pom/`
4. **Pain points** — what is brittle, slow, or duplicated
5. **Team shape** — one team or many
6. **Runner & build tool** — TestNG (default) or JUnit 5; Gradle (Kotlin DSL preferred) or Maven; Allure or not

7. **Screen map** (mobile, if one exists) — `docs/app-map/screen-map.md` from `qa/java/skills/mobile-app-crawler`. Its **Component candidates** table is counted evidence for the "reused on 2+ screens → component" call below; prefer it over guessing which elements recur.

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

**Playwright: the default is no base class.** Pages take `Page`, components take their root `Locator`, and shared behaviour is a component field. Introduce `BasePage` only when a **third** concrete page shares real behaviour (not just the `page` field), and keep it to one level. **Selenium / Appium** use the thin `BasePage` / `BaseAppiumPage` their writer skills define (the driver plus one synchronization helper).

```
<ConcretePage>                     ← Playwright default: no base
BasePage → <ConcretePage>          ← Playwright: only on the third real sharer; Selenium / Appium: the writer's thin base
```

Avoid: `BasePage → FormPage → MultiStepFormPage → CheckoutInformationPage` (four levels usually hide imaginary abstractions), and a base class that only forwards to `page`.

### Java driver-lifecycle implications for the design

- Pages must not own driver lifetime — `BaseTest` (or a `DriverFactory`) owns it. Pages take the `Page` / driver in the constructor and are built in the test class, never as fields of `BaseTest`.
- **Parallel safety, Playwright and Appium:** instance fields in the one `BaseTest`, a browser or driver per class in `@BeforeClass`, TestNG `parallel="classes"` — no static state, no `ThreadLocal`. Playwright Java is not thread-safe, and that mode keeps a class on one thread (`qa/java/skills/ui-test-author/playwright/references/lifecycle.md`). **Selenium:** a `ThreadLocal<WebDriver>` in `DriverFactory`, as its writer teaches. **Never** a `public static WebDriver driver` or `static Playwright`.
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
- **A component takes its parent `Locator`** (`WebElement` on Selenium) in the constructor and builds every child from it, so it works wherever it is mounted. The scoping mechanics — chaining from the root, `parent.locator(child)` (the 1.63 form of the 1.64 `within()`), `filter(setHas)`, strictness, positional picks — are owned by [`ui-test-author/playwright/references/locators.md`](../ui-test-author/playwright/references/locators.md); `assets/LoginPage.java` there is the worked example.
- Every Playwright locator follows one ladder: `getByTestId` → `getByRole` → `getByLabel` → `getByPlaceholder` → `getByText` → `getByAltText` / `getByTitle` → CSS. Selenium and Appium put the test id first too, then their writer's order. Test ids are PascalCase dot-separated and static (`OrderRow`, `OrderRow.Title`); a fallback is recorded in `missing-testids.md`, never marked in the code.
- **No `@FindBy`** when the project standard is explicit `findElement`. Don't mix the two.

### Where flow helpers live

- **Playwright Java / Selenium Java / Appium Java**: `pom.flows.CheckoutFlow` with public static methods. Returns the resulting page object — never asserts.
- Test-setup-only flows go in the test class's own `@BeforeMethod` (seeded records) or, for Playwright, `AuthSetup` (the signed-in session) — never a second `BaseTest`.

## Recommended package layouts

### Playwright Java (single web app)

```
src/test/java/com/{org}/uitests/
├── support/
│   ├── BaseTest.java               ← the one lifecycle (ui-test-author/playwright assets)
│   └── AuthSetup.java              ← signed-in state, once per suite run
├── pages/
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
└── tests/
    └── CheckoutTest.java           ← seeds its data in its own @BeforeMethod
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
| Cross-page widget (toast) | A `Toast` component field on each page that shows it, built from the page's root `Locator` |

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
| LoginPage | page | `goTo()`, the sign-in form component, `signIn()` | assertions, the landing page's locators |
| ProductCard | component | card-internal locators, `addToCart()` | iterating the product list |

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
- **Flow class with mutable state** — flows are stateless static methods
- **`@FindBy` + explicit `findElement` mixed** in the same project — pick one
- **`BaseTest` doing app-specific work** — bases handle infrastructure (driver, fixtures), not domain workflow; page objects are not `BaseTest` fields
- **Playwright `BasePage` before a third concrete page shares real behaviour**, or a base that only holds `page`
- **Test extends a page object** to "reuse helpers" — push the helper into a flow or `BaseTest`
- **`public static WebDriver driver` / `static Playwright`** — breaks TestNG parallel execution; Playwright and Appium use instance fields with `parallel="classes"`, Selenium a `ThreadLocal<WebDriver>` factory
- **Mixing implicit + explicit waits** in `BasePage` — `driver.manage().timeouts().implicitlyWait(...)` together with `WebDriverWait` causes unpredictable timeouts; pick explicit

## Procedure

1. Collect inputs (skip questions answerable from the existing package tree).
2. Map every existing class (or every screen for greenfield) onto **page / component / flow / base**.
3. Apply splitting heuristics to anything in the wrong bucket.
4. Decide whether a Playwright `BasePage` is warranted: only when a third page shares real behaviour. Pick the multi-platform strategy if relevant.
5. Produce the output: package tree, responsibilities table, base hierarchy, migration plan (smallest refactor first).
6. Hand off code generation to the matching generator skill.

## Handoffs

- Implementing the design → `qa/java/skills/ui-test-author/playwright`, `qa/java/skills/ui-test-author/selenium`, or `qa/java/skills/ui-test-author/appium`
- Reviewing existing pages → `qa/java/skills/ui-test-author/review`
- Test data / builders → `qa/java/skills/test-data-builder`
- Higher-level strategy → `qa/manual/test-strategy`
