---
name: qa-bdd-step-bindings-typescript
description: Use when turning Gherkin .feature files into TypeScript step definitions and implementing each step against existing Page Object Models. Web binds via playwright-bdd (createBdd + fixtures); mobile binds via CucumberJS + WebdriverIO (Given/When/Then + custom World). Triggers: "generate step definitions for these features", "bind these Gherkin steps to our page objects in TS", "implement the steps for this .feature", "split the step definitions by domain". Pick the framework, then read its reference file. Do NOT use to write/refactor the .feature files (use `qa/_shared/bdd/gherkin-authoring`), to scaffold the BDD project/hooks (use `qa/typescript/skills/bdd-project-scaffold`), or to build the page objects themselves (use `qa/typescript/skills/page-object-architect`).
---

# BDD Step Bindings + POM Implementation (TypeScript)

One registered skill, two frameworks — a TypeScript project uses exactly one per platform. Parses `.feature` files (and the **Step Catalog** from `gherkin-authoring`) into step definitions, **split by domain**, with parameterized Cucumber-Expression steps, and **implements each step by calling existing page-object intent methods**. The BDD project, lifecycle, and state-sharing layer already exist (from `bdd-project-scaffold`).

Identify the project's framework (web vs mobile; check `package.json`, `playwright.config.ts` vs `wdio.conf.ts`; ask one question if ambiguous), then **read the matching `references/<framework>.md` end-to-end before writing any step code** — it carries the full model, templates (fixtures vs World), patterns, and hard rules. This file only routes and holds the rules shared by both frameworks.

## Frameworks in this family

| Read | Use when |
|------|----------|
| `references/playwright-bdd.md` | **Web** — steps via `createBdd(test)`, page objects shared as **Playwright fixtures**, `expect` from `@playwright/test`, `async` bodies, run via `bddgen` + `playwright test` |
| `references/cucumberjs-appium.md` | **Mobile** — steps via `@cucumber/cucumber` `Given/When/Then`, state via a **custom `World`**, WebdriverIO `expect`, `async` bodies, run via `@wdio/cucumber-framework` |

## Decision matrix — pick the framework

| Platform | Framework | State model | Assertion lib | Runner | Step signature |
|---|---|---|---|---|---|
| **Web** | playwright-bdd → `references/playwright-bdd.md` | **Fixtures** (`base.extend`, destructured per step) — no World | `expect` from `@playwright/test` (web-first, auto-retry) | `bddgen` → `playwright test` | `Given('…', async ({ loginPage }) => { … })` |
| **Mobile** | CucumberJS + WDIO → `references/cucumberjs-appium.md` | **custom `World`** (`this.login`, `setWorldConstructor`) | `expect` from `@wdio/globals` (WDIO matchers) | `@wdio/cucumber-framework` | `Given('…', async function (this: CustomWorld) { … })` |

**Decision rule:** the platform decides the framework, and the framework decides the **state model** — this is the one design difference you must get right. playwright-bdd steps receive page objects as **destructured fixture arguments** and must be arrow functions (the fixture object is the argument). CucumberJS steps reach page objects through **`this` (the World)** and must therefore be `function` expressions, never arrows (arrows can't bind `this`). Mixing the two — a World in a playwright-bdd project, or fixture destructuring in a CucumberJS step — is the most common cross-framework error.

## Shared rules (both frameworks)

### 1. One binding file per domain, mapped to the Step Catalog
Group steps by feature/domain (`steps/authentication.steps.ts`, `steps/cart.steps.ts`), **not** one giant `steps.ts`. Each canonical Step-Catalog row becomes exactly one step definition — reuse across scenarios, never duplicate. A step shared by many features goes in `steps/common.steps.ts`.

### 2. Cucumber Expressions, not regex
Default to Cucumber Expressions (`{string}`, `{int}`, `{word}`, `{float}`, custom param types). Both `createBdd` and CucumberJS treat a `/…/` literal as regex and a plain string as a Cucumber Expression — keep steps as plain Cucumber Expressions so the catalog params map cleanly. Custom types via `defineParameterType` (CucumberJS) / the playwright-bdd parameter-type API.

### 3. Reach shared state through the framework's mechanism — never `new` the page in a step
Web: destructure the page-object **fixture** (`async ({ loginPage }) => …`). Mobile: reach the page object through the **World** (`this.login`). The page/driver was created by the scaffold (fixture setup / `Before` hook). No module-level mutable state, no `new LoginPage(page)` inside a step.

### 4. Steps are thin; mechanics live in page objects
A step body is one or two page-object calls. **No selectors, no `page.locator(...)` / `browser.$(...)`, no waits in step definitions** — those belong in the page object. `Given`/`When` act; `Then` asserts. Page objects never assert (except `expectLoaded()` / `verifyPageLoaded()`).

### 5. Async all the way, no arbitrary sleeps
`async` step bodies; `await` every page-object call. No `page.waitForTimeout` / `browser.pause(ms)` — rely on Playwright auto-waiting + web-first assertions (web) or WDIO's built-in waits / `waitUntil` on a condition (mobile). No floating promises (strict TS, ESLint `no-floating-promises`).

### 6. Implement the Cleanup as a hook/teardown, not steps
The `gherkin-authoring` Cleanup handoff becomes **fixture teardown** (web, after `await use(...)`) or an **`After` hook** (mobile) — the scaffold owns hook placement. Never Gherkin steps, never a step definition.

### 7. Missing page objects → build them first
If a step needs a page object/method that doesn't exist, stop and build it via `page-object-architect`/`pom-builder`/`appium-page-object` (or hand to `qa-ui-typescript`/`qa-mobile-typescript`). Do not inline locators into the step to "make it pass."

## Procedure

1. Pick the framework (web → `references/playwright-bdd.md`, mobile → `references/cucumberjs-appium.md`) and **read that reference end-to-end**.
2. Read the `.feature` files + Step Catalog + Cleanup handoff and the available page objects.
3. For each distinct catalog step, write **one** step definition in the right domain file; reuse for repeats.
4. Pick the keyword (`Given`/`When`/`Then`) from the catalog; use Cucumber-Expression params matching the catalog's `{...}` placeholders and `Examples` columns.
5. Implement each body with page-object calls only; put assertions in `Then` with the framework's `expect`.
6. For any missing page object/method, build it before binding the step.
7. Ensure the Cleanup is implemented as teardown/`After` (scaffold layer), not as steps.
8. Run the toolchain (web: `npx bddgen && npx playwright test`; mobile: `npx wdio run`): every step bound (no undefined/ambiguous), the smoke scenario green.

## Anti-patterns to flag (both frameworks)

- One mega step file instead of per-domain files.
- Duplicate step definitions for steps the catalog already unified — parameterize and reuse.
- `page.locator(...)` / `browser.$(...)`, CSS, or waits inside step definitions — promote to a page object.
- `new LoginPage(page)` or module-level mutable state inside a step.
- **Wrong state model:** a World in a playwright-bdd project, or fixture-style destructuring in a CucumberJS step.
- **Wrong function form:** an arrow function in a CucumberJS step (loses `this`/World).
- Assertions inside page-object actions, or `When`/`Given` doing assertions.
- `page.waitForTimeout` / `browser.pause(ms)` / floating promises.
- Regex step expressions where a Cucumber Expression reads cleaner.
- Implementing Cleanup as Gherkin/steps instead of fixture teardown (web) / an `After` hook (mobile).

## Cross-references

Each `references/<framework>.md` carries its own templates and sibling cross-references. Route there after picking the framework.

## Handoffs

- `.feature` files / Step Catalog → `qa/_shared/bdd/gherkin-authoring`
- Project/lifecycle/state layer → `qa/typescript/skills/bdd-project-scaffold`
- Page objects → `qa/typescript/skills/page-object-architect` / `pom-builder` / `appium-page-object`
- Review features + bindings → `qa/typescript/skills/bdd-reviewer`
- Allure labels from tags → `qa/reporting/typescript/skills/allure-reporting`
