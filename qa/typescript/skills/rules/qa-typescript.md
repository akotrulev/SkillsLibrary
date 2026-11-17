---
paths:
  - "**/e2e/**/*.ts"
  - "**/{e2e-tests,api-tests,apitests,ui-tests,mobile-tests,desktop-tests,acceptance-tests}/**/*.ts"
  - "**/tests/{api,ui,e2e,mobile,desktop,integration,specs,clients,schemas,operations,proto,pages,flows,builders,mothers,support}/**/*.ts"
  - "**/test/specs/**/*.ts"
  - "**/src/specs/**/*.ts"
  - "**/src/pages/{web,mobile}/**/*.ts"
  - "**/src/windows/**/*.ts"
  - "**/{steps,step-definitions}/**/*.ts"
  - "**/playwright.config.ts"
  - "**/wdio*.conf.ts"
---

<!-- qa-typescript rules v2 (2026-11-17): core. Installed by /qa-typescript:rules; edit the paths above to where this project keeps its test suites, re-run to compare with the plugin's copy. -->

# TypeScript test-automation standards

Apply these to every test, page object, component, client, builder and fixture in a TypeScript test suite (Vitest + Zod, Playwright, WebdriverIO/Appium, playwright-bdd/Cucumber). The tag after a rule is its review severity: **blocker** ships a bug or breaks a security rule, **major** is a design or correctness problem, **minor** is style, **nit** is preference. API, UI, page-object, test-data, mobile, desktop, BDD, k6, LLM-eval and CI rules are separate files.

**The codebase wins.** Where this suite consistently does otherwise (Jest or Mocha over Vitest, its own layout), follow it and do not flag it. Detect versions first: Node (24 primary, 22 maintenance; flag end-of-life 20), `@playwright/test` (1.64 here; `locator.within()`, `page.webmcp`, `getByRef` need it), WebdriverIO 10 + Appium 3 (a cloud still on Appium 2 stays on WebdriverIO 9). Never use an API the pinned version lacks, nor flag a suite for lacking one.

## Simplicity

- No wrapper or DSL over the runner, driver or HTTP client, no speculative base class. Cut structure, never rigour. *major*
- Page objects, components, clients, builders and fixtures are the suite's structure: made at first use, never inlined into a test; a review does not count callers. *major*

## Tests

- Names state behaviour (`Should_X_When_Y` or the suite's form), one `describe` per feature or endpoint. *minor*
- Every test asserts one logical behaviour; several `expect` calls may check it. *blocker when nothing is asserted, else major*
- Every assertion expects one value, never an `OR`: no `||` in an `expect`, no `expect([a, b]).toContain(x)`, no `/a|b/`, no `oneOf`. Split per outcome; accepting several values needs a recorded instruction. *major*
- A failure names its subject and carries the evidence: `expect(dto.status, \`order ${id} status\`).toBe('paid')`. *minor*
- A test body is linear: no `if`, `else`, `switch`, ternary, loop or `try` anywhere. Reaching the screen, signing in and creating data happen in a hook or fixture; the body is the action and outcome. Data variants are one test per row (`it.each`, `test.for`). *major*
- Tests run alone in any order: no `describe.serial`, no module-level `let` reassigned by tests, no test reading what it did not create except named reference data. *blocker*
- What a test creates is removed in a teardown hook or fixture, never inline (or kept on failure). *major*

## Roles

- Every reusable piece is named for its role: page object, component, client, flow, builder or ObjectMother, fixture, seeder, probe, token provider, driver factory, env/config, wait condition, custom matcher. Nothing is named `helper(s)`, `util(s)`, `utility`, `common` or `misc`; a piece fitting no role is a missing object. Third-party names stay. *major*
- A spec file holds tests, hooks and fields; no function there drives the app or builds data. *major*
- Branching lives only in infrastructure: base-test failure evidence, env/config loader, driver factory, platform locator finder, teardown registry, a row source. *major*

## Errors

- No `try`/`catch`/`finally` in a test or cleanup hook, no `.catch(() => {})`. An expected rejection is `await expect(p).rejects…`; an unexpected one reaches the runner. *major*
- Only a client, seeder, probe, base class, driver factory or teardown registry catches, narrowing one named error and logging or rethrowing it; never blanket or silent. *major*
- A failed parse names what broke: the client's `safeParse` throws with `issues[].path`, `issues[].code` and the raw body. Never loosen a schema (`.passthrough()`, `.optional()`) to pass a drifted contract. *major*

## Waiting and async

- No sleeps: no `waitForTimeout`, `browser.pause`, `setTimeout` promise. Wait on a condition (web-first assertion, `expect.poll`, `vi.waitFor`, `waitUntil`). *blocker*
- Every promise is awaited, Allure calls too; `no-floating-promises` stays on. *blocker*
- `strict: true`; no `any`, `as unknown as X`, `@ts-ignore` or bare `eslint-disable` to silence a type. *major*

## Data, config and secrets

- Builders, reference data, pre-clean, keep on failure: `test-data.md`; on reference data, assert a non-empty result first. *blocker for a missing guard*
- No hardcoded base URL, host, credential or token; read them through the config loader and token provider, failing fast when missing. *blocker*
- No secret, token or real personal data in code, data files, logs or attachments; synthetic data only. *blocker*
- No `console.log` in tests; use runner steps. *minor*

## Flakes and reporting

- `retries: 0`. A flaky test is quarantined (tag, ticket, owner) and still runs in a non-gating lane; never `skip`/`fixme` as quarantine or more retries. A deterministic failure is a bug. *major*
- A skip carries its reason and ticket. *minor*
- Allure calls come from `allure-js-commons`; never attach a secret. *major*

## Comments

- No comments inside a test or object body: no AAA banners, step markers, commented-out code or `TODO`. A step that needs one moves onto the object that owns it. *minor; major when the comment is wrong*
- Permitted in tests only: a defect id, a recorded instruction to deviate from these rules, or a magic value's source. TSDoc only where a name cannot carry the contract. Scaffolded comments go. *nit*
