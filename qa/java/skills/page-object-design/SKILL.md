---
name: page-object-design
description: Use when designing the page object structure for a Java UI test project. Triggers "design page objects for app X". Not for a POM from a live URL (page-objects-from-url).
---

# QA — Page Object Architect (Java)

Designs the **shape** of a Page Object Model in a Java UI test project (Gradle Kotlin DSL + TestNG by default): which of the four kinds each piece is (page, region component, control component, flow), the base-class hierarchy, where locators live, and how to split when one page gets too big. Output is an architecture sketch — package tree + class responsibilities + decision rationale — not concrete page code.

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

7. **Screen map** (mobile, if one exists) — `docs/app-map/screen-map.md` from `qa/java/skills/mobile-app-crawler`. Its **Component candidates** table is counted evidence for the region-component call below; prefer it over guessing which elements recur.

## Core decisions

### The four kinds

| Kind | Models | Created | Examples |
|---|---|---|---|
| **Page** (screen, window) | One route / screen / window | Per screen | `LoginPage`, `CheckoutOverviewPage` |
| **Region component** | An app-specific part of a page with its own root: a form, a card, a nav menu, a row | When it repeats on the page (rows, cards: always) or appears on a second page | `SignInForm`, `ProductCard`, `NavigationMenu`, `OrderRow` |
| **Control component** | A design-system widget | **At first use** | `DatePicker`, `Dropdown`, `Combobox`, `DataGrid` + `GridRow`, `Pagination`, `Modal`, `Toast`, `Tabs`, `FileUpload` |
| **Flow** | A sequence across several pages | When a test's setup needs it | `CheckoutFlow` (takes its pages, instance methods) |

Classifying:

- Has its own URL, screen or window → page.
- Comes from the design system or a UI library, or takes more than one driver call to operate → control component, at first use. Caller count is not the test. The page exposes it as intent: `orders.placedOn().select(date)`.
- An app-specific region that repeats on the page, or appears on a second page → region component.
- A sequence across pages that setup needs → a `<Something>Flow` class.
- Two markups of "the same" widget are two classes: `Dropdown` over a native `<select>`, `Combobox` over a custom listbox. Never one class with a branch.
- A grid is `DataGrid` whose `row(key)` returns a `GridRow` picked by its content, never by index; `GridRow` exposes cells by column name and the row's actions.
- A component takes its root in the constructor (Playwright `Locator`, Selenium root `WebElement`, Appium and desktop a row key re-resolved on every call), builds every child from it, and exposes intent with domain-typed arguments (a `LocalDate`, an option's visible text, a row key, a column name). No URL, no assertion, no knowledge of the page it is mounted on.
- The Playwright control catalogue (root, intent methods, API per control) is [`ui-test-author/playwright/references/components.md`](../ui-test-author/playwright/references/components.md); the Selenium `Dropdown` and row are in [`ui-test-author/selenium`](../ui-test-author/selenium/SKILL.md).

### Base class hierarchy

**Playwright: the default is no base class.** Pages take `Page`, components take their root `Locator`, and shared behaviour is a component field. Introduce `BasePage` only when a **third** concrete page shares real behaviour (not just the `page` field), and keep it to one level. **Selenium / Appium** use the thin `BasePage` / `BaseAppiumPage` their writer skills define (the driver plus its wait and finders). **No component extends a page base class**, on any driver: composition over inheritance. An Appium component holds a row key and re-resolves its root on every call.

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

1. **Per-platform pages, one shared flow** (cheapest, recommended default) — `pom.web.LoginPage`, `pom.mobile.LoginPage`; one `CheckoutFlow` that takes either through a small interface in its constructor.
2. **Per-platform pages + a shared interface** (`LoginScreen`) — useful when both platforms drive the same domain workflow.
3. **Abstract base + per-platform subclass** — only when the screens are truly the same minus locators.

Avoid `if (platform.equals("iOS")) …` inside a single page object.

### Locator ownership

- Locators belong **inside the page / component class** as `private static final By` (Selenium), `private static final String {ELEMENT}_ID` (Appium; a fallback is `{ELEMENT}_XPATH_FALLBACK`) or `private final Locator` fields (Playwright Java) — never in tests.
- A shared `Locators` constants class is an anti-smell. The only exception is brand-wide a11y test ids.
- **A component takes its root `Locator`** (`WebElement` on Selenium) in the constructor and builds every child from it, so it works wherever it is mounted. A locator an action uses is private; Playwright may expose one only as a described assertion target, and Selenium / Appium expose no element at all (queries return text, a boolean or a count). The scoping mechanics — chaining from the root, `parent.locator(child)` (the 1.63 form of the 1.64 `within()`), `filter(setHas)`, strictness, positional picks — are owned by [`ui-test-author/playwright/references/locators.md`](../ui-test-author/playwright/references/locators.md); `assets/LoginPage.java` there is the worked example. In a BDD suite the step definitions are the intent layer: a page object the steps use may expose named elements and controls for a step to act on (`filterPage.dealType().selectOption(option)`), and keeps a method only for a sequence of interactions (`qa-java-bdd.md`).
- Every Playwright locator follows one ladder: `getByTestId` → `getByRole` → `getByLabel` → `getByPlaceholder` → `getByText` → `getByAltText` / `getByTitle` → CSS. Selenium puts the test id first too, and Appium picks the rung per platform (iOS `accessibilityId`, Android `id`), then a native query, then XPath. Test ids are PascalCase dot-separated and static (`OrderRow`, `OrderRow.Title`); a fallback is recorded in `missing-testids.md`, never marked in the code.
- **No `@FindBy`** when the project standard is explicit `findElement`. Don't mix the two.

### Parameterized pages and application waits

- A screen that repeats with a different label is **one page class constructed with that data**: `new SimplePropertyPage(driver, "Suicide Genes")`, the label building its landmark and locators. That is data, not a behaviour flag: the argument changes what the page finds, never which code path runs. A `boolean` or enum that picks behaviour is still two methods or two classes.
- The app's own busy signal (a loading bar, a snackbar) is a **named wait condition on the base page or shell component** (`waitUntilLoadingBarGone()`), called by the action that triggers it before it returns. The test never calls it.
- On a server-rendered page the hydration signal is a named wait too: `goTo()` waits for `data-hydrated="true"` on `<body>`, and an intent method on a late-hydrating island waits on the island's own root, before it acts. Never visibility, never a sleep (`ui-test-author/playwright/references/server-rendered-pages.md`).

### Flows

- `flows.CheckoutFlow` is a class that takes its page objects in the constructor and has instance methods (`signInAndCheckout(user, cart)`) returning the resulting page. No static methods, no assertions, no state beyond its pages.
- Setup that only one test class needs stays in that class's `@BeforeMethod(alwaysRun = true)` (seeded records) or, for Playwright, `AuthSetup` (the signed-in session) — never a second `BaseTest`, and never a private method on the test class that drives the app.

## Recommended package layouts

The Playwright single-app tree and the Selenium / Appium multi-platform tree are in [`references/package-layouts.md`](references/package-layouts.md): `support/` (the one `BaseTest`, `AuthSetup`), `pages/` or `pom/`, `components/` with `controls/`, `flows/`, `tests/`.

## Splitting heuristics

A page object should split when **any** are true:

- File > ~250 lines (Java's explicit `findElement` style runs a bit longer than .NET/TS)
- More than 3 conceptually distinct UI sections (header + form + sidebar + footer)
- Two team members would name the same element differently because they describe it via different parent UI
- The same locator string appears identically on another page (region component candidate)
- A widget from the design system is operated inline with several driver calls (control component, extract now)
- More than one method modifies state another method needs to inspect (page hiding sub-state — promote to component)

| Smell | Move |
|---|---|
| Repeated card or row | A region component scoped to its root (`ProductCard`, `OrderRow`) |
| Date picker, dropdown, grid driven inline | A control component in `components.controls`, exposed by the page as intent |
| One widget class with a branch on its markup | Two classes (`Dropdown`, `Combobox`) |
| Row picked by index | `DataGrid.row(key)` returning a `GridRow` found by its content |
| A static flow class or a private driving method on a test class | A `<Something>Flow` class with its pages in the constructor |
| Step-by-step flow (checkout, onboarding) | Sub-package per step under `pom/checkout/` |
| Persistent shell (nav, footer) | Extract `NavigationMenu` / `SidePanel` exposed as a field on every page that has it |
| Modal / dialog | A `Modal` control returned from the action that opens it; the test asserts on what it exposes |
| Cross-page widget (toast) | A `Toast` control field on each page that shows it, built from the page's root `Locator` |

## Naming conventions

- Pages: `{Feature}Page` — `LoginPage`, `CheckoutOverviewPage`
- Region components: `{Element}` (no `Page` suffix) — `NavigationMenu`, `ProductCard`, `OrderRow`
- Control components: the widget's name — `DatePicker`, `Dropdown`, `Combobox`, `DataGrid`, `GridRow`, `Modal`, `Toast`
- Flows: `{Feature}Flow` with `{verb}{Object}` instance methods — `checkoutFlow.signInAndCheckout(...)`
- Methods name the action (`signIn`), never the outcome (`successfulLogin`); no class or method named `Helper`, `Util` or `Common`
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
| LoginPage | page | `goTo()`, the `SignInForm` region, `signIn()` | assertions, the landing page's locators |
| ProductCard | region component | card-internal locators, `addToCart()` | iterating the product list |
| DatePicker | control component | `select(LocalDate)`, its calendar locators | which page it sits on |
| CheckoutFlow | flow | the pages it is given, `signInAndCheckout()` | assertions, static state |

## Control components
<each design-system widget the app uses, its class, and the pages that expose it>

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

The standards a page-object tree must meet are the qa-java rule files, not a list here: `qa-java-page-objects.md`, `qa-java-ui.md` (or `desktop-tests.md`) and `qa-java.md` (core). Read the project's copy in `.claude/rules/qa-java/`, or the plugin's in `qa/java/skills/rules/` when the project has not installed them (`/qa-java:rules` does). Where they and this skill's design disagree, the rule files win. One design call they leave to this skill: a page method returns the next page or visible text, never a DTO (that is API territory).

## Procedure

1. Collect inputs (skip questions answerable from the existing package tree).
2. Map every existing class (or every screen for greenfield) onto **page / region component / control component / flow / base**. List the design-system widgets the screens use; each becomes a control component now.
3. Apply splitting heuristics to anything in the wrong bucket.
4. Decide whether a Playwright `BasePage` is warranted: only when a third page shares real behaviour. Pick the multi-platform strategy if relevant.
5. Produce the output: package tree, responsibilities table, base hierarchy, migration plan (smallest refactor first).
6. Hand off code generation to the matching generator skill.

## Handoffs

- Implementing the design → `qa/java/skills/ui-test-author/playwright`, `qa/java/skills/ui-test-author/selenium`, or `qa/java/skills/ui-test-author/appium`
- Reviewing existing pages → `qa/java/skills/ui-test-author/review`
- Test data / builders → `qa/java/skills/test-data-builder`
- Higher-level strategy → `qa/manual/test-strategy`
