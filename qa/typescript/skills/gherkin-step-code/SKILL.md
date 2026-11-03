---
name: gherkin-step-code
description: Use when turning Gherkin .feature files into playwright-bdd/CucumberJS steps in TypeScript bound to page objects. Triggers "generate step definitions". Not for writing .feature files (feature-files).
---

# BDD Step Bindings + POM Implementation (TypeScript)

One registered skill, two frameworks — a TypeScript project uses exactly one per platform. Parses `.feature` files (and the **Step Catalog** from `feature-file-writer`) into step definitions, **split by domain**, with parameterized Cucumber-Expression steps, and **implements each step by calling existing page-object intent methods**. The BDD project, lifecycle, and state-sharing layer already exist (from `bdd-project-scaffold`).

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

## Layout (both frameworks)

- One binding file per domain (`steps/authentication.steps.ts`, `steps/cart.steps.ts`); a step shared by many features goes in `steps/common.steps.ts`. Each canonical Step-Catalog row becomes exactly one step definition.
- Custom parameter types via `defineParameterType` (CucumberJS) or the playwright-bdd parameter-type API.
- The page or driver is created by the scaffold (fixture setup / `Before` hook); the Cleanup handoff from `feature-file-writer` is fixture teardown (web) or an `After` hook (mobile), which the scaffold places.
- A step that needs a page object or method that does not exist: build it first via `page-object-design` / `page-objects-from-url` / `mobile-screen-objects` (or hand to `qa-ui-typescript` / `qa-mobile-typescript`).

## Rules

The standards this skill's output must meet are the qa-typescript rule files, not a list here: `bdd.md` and `qa-typescript.md`. Read the project's copy in `.claude/rules/qa-typescript/`, or the plugin's in `qa/typescript/skills/rules/` when the project has not installed them (`/qa-typescript:rules` does). Where they and this skill's recipes disagree, the rule files win.

## Procedure

1. Pick the framework (web → `references/playwright-bdd.md`, mobile → `references/cucumberjs-appium.md`) and **read that reference end-to-end**.
2. Read the `.feature` files + Step Catalog + Cleanup handoff and the available page objects.
3. For each distinct catalog step, write **one** step definition in the right domain file; reuse for repeats.
4. Pick the keyword (`Given`/`When`/`Then`) from the catalog; use Cucumber-Expression params matching the catalog's `{...}` placeholders and `Examples` columns.
5. Implement each body with page-object calls only; put assertions in `Then` with the framework's `expect`.
6. For any missing page object/method, build it before binding the step.
7. Ensure the Cleanup is implemented as teardown/`After` (scaffold layer), not as steps.
8. Run the toolchain (web: `npx bddgen && npx playwright test`; mobile: `npx wdio run`): every step bound (no undefined/ambiguous), the smoke scenario green.

## Cross-references

Each `references/<framework>.md` carries its own templates and sibling cross-references. Route there after picking the framework.

## Handoffs

- `.feature` files / Step Catalog → `qa/_shared/bdd/feature-file-writer`
- Project/lifecycle/state layer → `qa/typescript/skills/bdd-project-scaffold`
- Page objects → `qa/typescript/skills/page-object-design` / `page-objects-from-url` / `mobile-screen-objects`
- Review features + bindings → `qa/typescript/skills/bdd-reviewer`
- Allure labels from tags → `qa/reporting/typescript/skills/test-reports`
