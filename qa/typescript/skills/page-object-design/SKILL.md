---
name: page-object-design
description: Use when designing the page object structure for a TypeScript UI test project. Triggers "design page objects for app X". Not for a POM from a live URL (page-objects-from-url).
disable-model-invocation: true
---

# QA — Page Object Architect (TypeScript)

Designs the **shape** of a Page Object Model in a TypeScript UI test project: which of the four kinds (page, region component, control component, flow) each piece is, the base-class hierarchy, where shared locators live, and how to split when one page gets too big. Output is an architecture sketch — folder tree + class responsibilities + decision rationale — not concrete page code.

## Inputs needed

1. **App shape** — single web app, mobile, or web + mobile
2. **Stacks in play** — Playwright TS, WebdriverIO (web), WebdriverIO + Appium (mobile), or a mix
3. **Existing structure** (if any) — file tree of `pages/`, `pageObjects/`, `e2e/`
4. **Pain points** — what is brittle, slow, or duplicated
5. **Team shape** — one team or many
6. **Runner & lint tooling** — Playwright Test (default for Playwright), WebdriverIO runner, Vitest for unit-on-pages; `eslint-plugin-playwright` / `eslint-plugin-wdio`; Allure or not

7. **Screen map** (mobile, if one exists) — `docs/app-map/screen-map.md` from `qa/typescript/skills/mobile-app-crawler`. Its **Component candidates** table is counted evidence for the region-component call below; prefer it over guessing which elements recur.

## Core decisions

### The four kinds

| Kind | What it models | Created | Examples |
|---|---|---|---|
| **Page** | One route, screen or window | Per screen; owns its URL in `goto()` | `LoginPage`, `CheckoutOverviewPage` |
| **Region component** | An app-specific part of a page with its own root: a form, a card, a nav menu, a row | When it repeats on the page (rows, cards: always) or appears on a second page | `SignInForm`, `ProductCard`, `NavigationMenu` |
| **Control component** | A design-system widget: date picker, dropdown (native `<select>`), combobox (custom listbox), data grid + grid row, pagination, modal, toast, tabs, file upload | **At first use** | `DatePicker`, `Dropdown`, `Combobox`, `DataGrid`, `GridRow` |
| **Flow** | A sequence across several pages | When a test's setup needs it | `seededCart` fixture, `CheckoutFlow` |

Rules of thumb:

- Has its own URL or screen → page
- Comes from the design system or a UI library, or takes more than one driver call to operate → control component, at first use. Caller count is not the test
- Repeats on the page, or appears on a second page → region component
- Spans several pages → flow: a fixture (preferred in Playwright Test) or a `<Something>Flow` class that takes its pages in the constructor; never a free function
- Two markups of "the same" widget → two classes (`Dropdown` for a native `<select>`, `Combobox` for a custom listbox), never one class with a branch
- A grid → `DataGrid` with `row(key)` returning a `GridRow`, picked by content, never by index; the row exposes cells by column and its actions

The control catalogue (each control's root, intent methods and Playwright API) is [`ui-test-author/playwright/references/components.md`](../ui-test-author/playwright/references/components.md).

### Base class hierarchy

**The default is no base class.** Pages take `page: Page`, components take their root `Locator`, and shared behaviour is a component field or a role-named class (a flow, a client). Introduce `BasePage` only when a **third** concrete page shares real behaviour (not just the `page` field), and keep it to one level:

```
<ConcretePage>                     ← default: no base
BasePage → <ConcretePage>          ← only on the third real sharer
```

Avoid: `BasePage → FormPage → MultiStepFormPage → CheckoutInformationPage` (four levels usually hide imaginary abstractions), and a base class that only forwards to `page`. A component never extends `BasePage`: composition, not inheritance.

### TypeScript driver-lifecycle implications for the design

- **Playwright Test** owns the `Page` lifecycle via fixtures — pages take `page: Page` in the constructor. Never call `chromium.launch()` inside a page object.
- **Custom fixtures** are the idiomatic way to share state (seeded user, cart, storageState). Reach for `test.extend<...>` before reaching for a static class.
- **`storageState`** belongs at the project/test level (`playwright.config.ts → projects[].use.storageState` or per-test) — never log in inside `BasePage`.
- **WebdriverIO v8+** is async-only. Page methods return `Promise<NextPage>`. No floating promises — turn on ESLint `no-floating-promises`.
- **Strict TS.** Page method signatures must not return `Promise<any>` or `Promise<unknown>`. Use explicit return types.

### Multi-platform sharing

Three viable strategies, ordered by cost:

1. **Per-platform pages, one shared flow** (cheapest, recommended default) — `pages/web/LoginPage.ts`, `pages/mobile/LoginPage.ts`; one `SignInFlow` taking a small `LoginScreen` interface in its constructor.
2. **Per-platform pages + a shared interface** (`LoginScreen`) — useful when flows are reused across both platforms.
3. **Abstract base + per-platform subclass** — only when the screens are truly the same minus locators.

Avoid `if (driver.isIOS) …` inside a page: a platform difference lives in the base page's locator finder, the one place a platform branch is legal.

### Locator ownership

- Locators belong **inside the page / component class** as `private readonly` fields (Playwright) or `private` getters (WebdriverIO) — never in the spec. A Playwright locator is public only as a `readonly`, described assertion target; a test never acts on it. WebdriverIO objects expose no element, only queries returning values. In a BDD suite the step is the intent layer: a page object used by steps may expose named elements and controls for steps to act on (`bdd.md`).
- **A screen that repeats with a different label is one class constructed with that label**: `new PropertyPage(page, 'Suicide Genes')` builds its locators from it. The label is data; a boolean or enum that picks what a method does is still two methods.
- **The app's busy signal is a named wait** (loading bar gone, snackbar gone) on the shell component, or on `BasePage` where one exists: `waitUntilIdle()` runs `progressBar.waitFor({ state: 'hidden' })`. The action that triggers the busy state calls it; a test never does.
- **On a server-rendered page the hydration signal is a named wait too**: `goto()` waits for `data-hydrated="true"` on `<body>`, and an intent method on a late-hydrating island waits on the island's own root, before it acts. Never visibility, never a sleep. Details: [`ui-test-author/playwright/references/server-rendered-pages.md`](../ui-test-author/playwright/references/server-rendered-pages.md).
- A shared `locators.ts` constants module is an anti-smell. Exception: brand-wide a11y test ids (small file).
- **A component takes its parent `Locator`** (`WebdriverIO.Element` on WebdriverIO) in the constructor and builds every child from it, so it works wherever it is mounted. The scoping mechanics — chaining from the root, `within()`, `filter({ has })`, strictness, positional picks — are owned by [`ui-test-author/playwright/references/locators.md`](../ui-test-author/playwright/references/locators.md); `assets/LoginPage.ts` there is the worked example.
- Every locator follows one ladder: `getByTestId` → `getByRole` → `getByLabel` → `getByPlaceholder` → `getByText` → `getByAltText` / `getByTitle` → CSS. Test ids are PascalCase dot-separated and static (`OrderRow`, `OrderRow.Title`); a fallback is recorded in `missing-testids.md`, never marked in the code.

### Where flows live

- **Playwright TS (preferred):** custom fixtures in `tests/fixtures/` — `seededCart`, `signedInAdmin`. The fixture seeds state and gives the test the resulting page object.
- **Playwright TS (otherwise) and WebdriverIO:** a `<Something>Flow` class in `flows/` that takes its page objects in the constructor and has instance methods, built in `beforeEach`. WebdriverIO has no `test.extend`.

A flow owns no assertions and no state beyond its pages — it sets up state and returns the resulting page object. No free-function flows, no static flow classes.

## Recommended folder layouts

### Playwright TS (single web app)

```
e2e/
├── tests/
│   ├── fixtures/
│   │   ├── auth.ts                ← storageState fixture, seededAdmin
│   │   └── seededCart.ts
│   ├── flows/                     ← Flow classes, when a fixture does not fit
│   │   └── CheckoutFlow.ts
│   └── specs/
│       └── checkout.spec.ts
├── pages/
│   ├── BasePage.ts                ← only once a third page shares real behaviour
│   ├── LoginPage.ts
│   ├── catalog/
│   │   ├── ProductListPage.ts
│   │   └── ProductCard.ts          ← component, takes Locator parent
│   └── checkout/
│       ├── InformationPage.ts
│       ├── OverviewPage.ts
│       └── CompletePage.ts
├── components/                    ← region components shared by features
│   ├── NavigationMenu.ts
│   └── controls/                  ← design-system controls, one class each
│       ├── DatePicker.ts
│       ├── Dropdown.ts
│       ├── DataGrid.ts
│       ├── GridRow.ts
│       └── Toast.ts
├── playwright.config.ts
└── tsconfig.json                  ← "strict": true
```

### WebdriverIO + Appium (multi-platform)

```
e2e/
├── wdio.conf.ts
├── pages/
│   ├── web/
│   │   ├── LoginPage.ts
│   │   └── …
│   └── mobile/
│       ├── LoginPage.ts
│       └── …
├── components/
│   └── controls/
├── flows/
│   └── CheckoutFlow.ts
└── specs/
    └── checkout.spec.ts
```

## Splitting heuristics

A page object should split when **any** are true:

- File > ~200 lines
- More than 3 conceptually distinct UI sections (header + form + sidebar + footer)
- Two team members would name the same element differently because they describe it via different parent UI
- The same locator string appears identically on another page (region-component candidate)
- A design-system widget is driven through raw locators on the page (control-component candidate, at first use)
- More than one method modifies state another method needs to inspect (page hiding sub-state — promote to component)

| Smell | Move |
|---|---|
| Repeated card or row | Extract `ProductCard` / `OrderRow` region component scoped to its root `Locator` |
| Date picker, dropdown, grid, tabs driven inline | A control from `components/controls/`, exposed as a page field: `checkout.deliveryDate.select(date)` |
| One class with a branch for two widget markups | Two control classes |
| Step-by-step flow (checkout, onboarding) | Sub-folder per step under `pages/checkout/` |
| Persistent shell (nav, footer) | Extract `NavigationMenu` / `SidePanel` exposed as a field on every page that has it |
| Modal / dialog | Return modal class from the action that opens it; assertion on the modal |
| Cross-page widget (toast) | A `Toast` component field on each page that shows it, built from the page's root `Locator` |
| Test sets up state via `loginPage.signIn(...)` repeatedly | Promote to a `seededAuth` fixture using `storageState` |
| A function in the spec file drives the app or builds data | Move it onto the page, component, builder or fixture that owns it |

## Naming conventions

- Pages: `{Feature}Page` — `LoginPage`, `CheckoutOverviewPage`
- Region components: `{Element}` (no `Page` suffix) — `NavigationMenu`, `ProductCard`, `OrderRow`
- Control components: the widget's name — `DatePicker`, `Dropdown`, `Combobox`, `DataGrid`, `GridRow`
- Fixtures: `{noun}` — `seededCart`, `signedInAdmin`
- Flows: `{Something}Flow` — `CheckoutFlow`, `SignInFlow`
- Methods: the action (`signIn`), never the outcome (`successfulLogin`)
- Never `Helper`, `Utils`, `Common` or `Misc`: a piece that fits no role is a missing object
- Base classes: `Base{Type}` — `BasePage`, `BaseTest` — at most one of each
- Files: PascalCase for class files (`LoginPage.ts`, `CheckoutFlow.ts`), camelCase for fixture modules (`seededCart.ts`)

## Output format

```markdown
# Page Object Architecture: <app name> (TypeScript)

## Folder tree
<proposed tree with one-line annotations>

## Class responsibilities
| Class | Type | Owns | Doesn't own |
|-------|------|------|-------------|
| LoginPage | page | `goto()`, the sign-in form component, `signIn()` | assertions, the landing page's locators |
| ProductCard | region component | card-internal locators, `addToCart()` | iterating the product list |
| DatePicker | control component | its root, `select(date)` | the page it is mounted on, assertions |

## Component candidates
| Widget | Seen on | Kind | Existing class |
|--------|---------|------|----------------|

## Base hierarchy
<none, unless a third page shares real behaviour — then name the three and what they share>

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
- **Inheritance for code reuse** in TS — prefer composition: a component field
- **Page returns DTOs** — that's API territory; page methods return next pages or visible text
- **Locators in a central constants file** — couples every page change to one file
- **Flow with state or assertions** — a flow holds its pages and nothing else
- **Design-system widget driven inline** — a control component at first use, not on the second caller
- **Public action locator** — `loginPage.signInForm.email.fill(...)` from a spec; the action is an intent method
- **`BaseTest` doing app-specific work** — bases handle infrastructure (page, fixtures), not domain workflow

The code standards a page object must meet (no unearned `BasePage`, pages from fixtures, sign-in once per role, strict types, no floating promises, no sleeps) are the qa-typescript rule files `page-objects.md`, `ui-tests.md` and `qa-typescript.md`: the project's copy in `.claude/rules/qa-typescript/`, or the plugin's in `qa/typescript/skills/rules/` when the project has not installed them (`/qa-typescript:rules` does).

## Procedure

1. Collect inputs (skip questions answerable from the existing file tree).
2. Map every existing module (or every screen for greenfield) onto **page / region component / control component / flow-or-fixture / base**. List every design-system widget as a control at first use, matched to an existing class in `components/controls/` before proposing a new one.
3. Apply splitting heuristics to anything in the wrong bucket.
4. Decide whether `BasePage` is warranted: only when a third page shares real behaviour.
5. Pick the multi-platform strategy if relevant; pick fixture vs `Flow` class for flows.
6. Produce the output: folder tree, responsibilities table, fixture strategy, migration plan (smallest refactor first).
7. Hand off code generation to the matching generator skill.
