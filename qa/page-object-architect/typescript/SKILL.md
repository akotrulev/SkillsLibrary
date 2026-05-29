---
name: qa-page-object-architect-typescript
description: Use when the user is designing the page object structure for a TypeScript UI test project — Playwright TS, WebdriverIO (web), or WebdriverIO + Appium (mobile) — what becomes a page, what becomes a component, where the base page lives, how to split a giant page object, and how to share code across platforms. Triggers: "design page objects for app X in TypeScript", "how should I structure pages/ for Playwright TS", "split this giant POM module", "where do shared helpers live in the WebdriverIO project". Do NOT use for individual page code (use `qa/ui-test-author/playwright/typescript`, `qa/ui-test-author/selenium/typescript`, or `qa/ui-test-author/appium/typescript`), reviewing one file (use `qa/ui-test-author/reviewer/typescript`), .NET POM architecture (use `qa/page-object-architect/dotnet`), or Java POM architecture (use `qa/page-object-architect/java`).
---

# QA — Page Object Architect (TypeScript)

Designs the **shape** of a Page Object Model in a TypeScript UI test project: page vs component vs flow, base-class hierarchy, where shared locators and helpers live, and how to split when one page gets too big. Output is an architecture sketch — folder tree + class responsibilities + decision rationale — not concrete page code.

## When to use

- Greenfield UI test suite — first POM layout in `pages/` or `pageObjects/`
- Existing suite has grown to 30+ pages and patterns are diverging
- Multi-platform app (web + mobile via WebdriverIO Appium) needs shared abstractions
- One page object has grown past ~200 lines and feels wrong
- Tests are slow / brittle and the root cause is structural

## When NOT to use

- Writing the page object code itself → `qa/ui-test-author/playwright/typescript`, `qa/ui-test-author/selenium/typescript`, or `qa/ui-test-author/appium/typescript`
- Reviewing a single existing page object → `qa/ui-test-author/reviewer/typescript`
- Designing test data / fixtures → `qa/test-data-builder/typescript`
- Designing the entire test strategy → `qa/_shared/test-strategy`
- .NET POM architecture → `qa/page-object-architect/dotnet`
- Java POM architecture → `qa/page-object-architect/java`

## Inputs needed

1. **App shape** — single web app, mobile, or web + mobile
2. **Stacks in play** — Playwright TS, WebdriverIO (web), WebdriverIO + Appium (mobile), or a mix
3. **Existing structure** (if any) — file tree of `pages/`, `pageObjects/`, `e2e/`
4. **Pain points** — what is brittle, slow, or duplicated
5. **Team shape** — one team or many
6. **Runner & lint tooling** — Playwright Test (default for Playwright), WebdriverIO runner, Vitest for unit-on-pages; `eslint-plugin-playwright` / `eslint-plugin-wdio`; Allure or not

## Core decisions

### Page vs component vs flow

| Concept | What it models | Lifetime | Examples |
|---|---|---|---|
| **Page** | A discrete screen / route | One per URL or top-level navigation target | `LoginPage`, `CheckoutOverviewPage` |
| **Component** | A reusable piece appearing inside multiple pages | Scoped to a parent `Locator` / `Element` | `ProductCard`, `NavigationMenu`, `Modal`, `Toast` |
| **Flow** | An end-to-end sequence across pages | None — a **Playwright fixture** (preferred) or a module-level async function | `seededCart` fixture, `signIn(loginPage, user)` |

Rules of thumb:

- Has its own URL → page
- Reused on 2+ pages → component
- Touches 3+ pages → flow helper, not a class
- When in doubt → **component**

### Base class hierarchy

Keep it **shallow** — at most two levels.

```
BasePage              ← page field, common waits, expectLoaded() abstract
 └─ (rarely) AuthenticatedPage — only if every signed-in page truly shares something
 └─ <ConcretePage>
```

Avoid: `BasePage → FormPage → MultiStepFormPage → CheckoutInformationPage` (four levels usually hide imaginary abstractions).

**Composition over class hierarchy.** In TypeScript especially, you can often skip the base class entirely and use small composable helpers (`expectLoaded(page, locator)` as a free function) or a single mixin. Don't introduce `BasePage` unless 3+ concrete pages already share genuine behavior.

### TypeScript driver-lifecycle implications for the design

- **Playwright Test** owns the `Page` lifecycle via fixtures — pages take `page: Page` in the constructor. Never call `chromium.launch()` inside a page object.
- **Custom fixtures** are the idiomatic way to share state (seeded user, cart, storageState). Reach for `test.extend<...>` before reaching for a static helper.
- **`storageState`** belongs at the project/test level (`playwright.config.ts → projects[].use.storageState` or per-test) — never log in inside `BasePage`.
- **WebdriverIO v8+** is async-only. Page methods return `Promise<NextPage>`. No floating promises — turn on ESLint `no-floating-promises`.
- **Strict TS.** Page method signatures must not return `Promise<any>` or `Promise<unknown>`. Use explicit return types.

### Multi-platform sharing

Three viable strategies, ordered by cost:

1. **Per-platform pages, shared flow helpers** (cheapest, recommended default) — `pages/web/LoginPage.ts`, `pages/mobile/LoginPage.ts`; one shared `signIn(loginPage: LoginScreen, user)` accepting a small `LoginScreen` interface.
2. **Per-platform pages + a shared interface** (`LoginScreen`) — useful when flows are reused across both platforms.
3. **Abstract base + per-platform subclass** — only when the screens are truly the same minus locators.

Avoid `if (driver.isIOS) …` inside a single page — that conditional logic in pages contradicts the global "no conditional logic in tests" rule.

### Locator ownership

- Locators belong **inside the page / component class** as `readonly Locator` fields (Playwright) or `private readonly` getters (WebdriverIO) — never in the test (spec file).
- A shared `locators.ts` constants module is an anti-smell. Exception: brand-wide a11y test ids (small file).
- Components scoped to a parent take that parent `Locator` / `WebdriverIO.Element` in the constructor and query inside it via `parent.locator(...)` / `parent.$(...)`.
- Prefer `page.getByRole` / `getByLabel` / `getByTestId` (Playwright) — keeps the design semantic and accessible-first.

### Where flow helpers live

- **Playwright TS (preferred):** Custom fixtures in `tests/fixtures/` — `seededCart`, `signedInAdmin`. The fixture seeds state and gives the test the resulting page object.
- **Playwright TS (acceptable):** Free async functions in `tests/flows/`, called from `test.beforeEach` or directly inside a test, returning the resulting page.
- **WebdriverIO:** Module of free async functions in `flows/`, invoked from `beforeAll` / `beforeEach` hooks. WebdriverIO has no `test.extend`; mimic fixtures via shared hook functions.

A flow helper does **not** own assertions — it sets up state and returns the resulting page object.

## Recommended folder layouts

### Playwright TS (single web app)

```
e2e/
├── tests/
│   ├── fixtures/
│   │   ├── auth.ts                ← storageState fixture, seededAdmin
│   │   └── seededCart.ts
│   ├── flows/                     ← optional free-function flows
│   │   └── signIn.ts
│   └── specs/
│       └── checkout.spec.ts
├── pages/
│   ├── BasePage.ts                ← optional, only if real shared behavior
│   ├── LoginPage.ts
│   ├── catalog/
│   │   ├── ProductListPage.ts
│   │   └── ProductCard.ts          ← component, takes Locator parent
│   └── checkout/
│       ├── InformationPage.ts
│       ├── OverviewPage.ts
│       └── CompletePage.ts
├── components/                    ← cross-feature shells
│   ├── NavigationMenu.ts
│   └── Toast.ts
├── playwright.config.ts
└── tsconfig.json                  ← "strict": true
```

### WebdriverIO + Appium (multi-platform)

```
e2e/
├── wdio.conf.ts
├── pages/
│   ├── BasePage.ts
│   ├── web/
│   │   ├── LoginPage.ts
│   │   └── …
│   └── mobile/
│       ├── BaseMobilePage.ts
│       ├── LoginPage.ts
│       └── …
├── components/
├── flows/
│   └── checkout.ts
└── specs/
    └── checkout.spec.ts
```

## Splitting heuristics

A page object should split when **any** are true:

- File > ~200 lines
- More than 3 conceptually distinct UI sections (header + form + sidebar + footer)
- Two team members would name the same element differently because they describe it via different parent UI
- The same locator string appears identically on another page (component candidate)
- More than one method modifies state another method needs to inspect (page hiding sub-state — promote to component)

| Smell | Move |
|---|---|
| Repeated card across pages | Extract `ProductCard` / `Row` component scoped to a parent `Locator` |
| Step-by-step flow (checkout, onboarding) | Sub-folder per step under `pages/checkout/` |
| Persistent shell (nav, footer) | Extract `NavigationMenu` / `SidePanel` exposed as a field on every page that has it |
| Modal / dialog | Return modal class from the action that opens it; assertion on the modal |
| Cross-page widget (toast) | Hang off `BasePage` (or as a free composable) so every page exposes `toast()` |
| Test sets up state via `loginPage.signIn(...)` repeatedly | Promote to a `seededAuth` fixture using `storageState` |

## Naming conventions

- Pages: `{Feature}Page` — `LoginPage`, `CheckoutOverviewPage`
- Components: `{Element}` (no `Page` suffix) — `NavigationMenu`, `ProductCard`, `Toast`
- Fixtures: `{noun}` — `seededCart`, `signedInAdmin`
- Flow helpers: `{verb}{Object}` — `signIn`, `seedOrder`
- Base classes: `Base{Type}` — `BasePage`, `BaseTest` — at most one of each
- Files: PascalCase for class files (`LoginPage.ts`), camelCase for fixture / flow modules (`seededCart.ts`, `signIn.ts`)

## Output format

```markdown
# Page Object Architecture: <app name> (TypeScript)

## Folder tree
<proposed tree with one-line annotations>

## Class responsibilities
| Class | Type | Owns | Doesn't own |
|-------|------|------|-------------|
| BasePage | base (optional) | `page` field, wait helpers, `expectLoaded()` abstract | assertions, business logic |
| LoginPage | page | login form locators, `signIn()` | navigation to product list (returns `ProductListPage`) |
| ProductCard | component | card-internal locators, `addToCart()` | iterating the product list |

## Base hierarchy
<3-line description; note if BasePage is unnecessary>

## Fixture strategy (Playwright)
<which fixtures own what; where storageState comes from>

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
- **Inheritance for code reuse** in TS — prefer composition / mixins / free helpers
- **Page returns DTOs** — that's API territory; page methods return next pages or visible text
- **Locators in a central constants file** — couples every page change to one file
- **Flow class with state** — flows are functions / fixtures, not stateful classes
- **`BasePage` constructed before there are 3+ concrete pages** sharing real behavior
- **`BaseTest` doing app-specific work** — bases handle infrastructure (page, fixtures), not domain workflow
- **Spec file instantiates pages with `new LoginPage(page)`** — use a fixture that yields the page
- **`storageState` setup repeated in every spec** — hoist to `playwright.config.ts` project or a fixture
- **`as any` / `as unknown as X` in page method signatures** — defeats strict TS
- **Floating promises** in page object method bodies — enable ESLint `no-floating-promises`
- **`page.waitForTimeout`** anywhere in the POM (always a blocker, separate from architecture)

## Procedure

1. Collect inputs (skip questions answerable from the existing file tree).
2. Map every existing module (or every screen for greenfield) onto **page / component / flow-or-fixture / base**.
3. Apply splitting heuristics to anything in the wrong bucket.
4. Decide whether `BasePage` is warranted (do not introduce it for fewer than 3 sharing pages).
5. Pick the multi-platform strategy if relevant; pick fixture vs free-function for flows.
6. Produce the output: folder tree, responsibilities table, fixture strategy, migration plan (smallest refactor first).
7. Hand off code generation to the matching generator skill.

## Handoffs

- Implementing the design → `qa/ui-test-author/playwright/typescript`, `qa/ui-test-author/selenium/typescript`, or `qa/ui-test-author/appium/typescript`
- Reviewing existing pages → `qa/ui-test-author/reviewer/typescript`
- Test data / builders → `qa/test-data-builder/typescript`
- Higher-level strategy → `qa/_shared/test-strategy`

## Changelog

- 2026-05-29: Split from monolithic `qa/page-object-architect/SKILL.md` into the TypeScript sibling. Adds TS-specific guidance: prefer Playwright fixtures over base-class inheritance, `storageState` at the project / fixture level, WebdriverIO async-only flows, strict TS return types, and discouragement of `BasePage` until 3+ pages truly share behavior.
