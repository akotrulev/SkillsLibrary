---
paths:
  - "**/e2e/**/*.ts"
  - "**/{e2e-tests,api-tests,apitests,ui-tests,mobile-tests,acceptance-tests}/**/*.ts"
  - "**/tests/{api,ui,e2e,mobile,integration,specs,clients,schemas,operations,proto,pages,flows,builders,mothers,support}/**/*.ts"
  - "**/test/specs/**/*.ts"
  - "**/src/specs/**/*.ts"
  - "**/src/pages/{web,mobile}/**/*.ts"
  - "**/{steps,step-definitions}/**/*.ts"
  - "**/playwright.config.ts"
  - "**/wdio*.conf.ts"
---

<!-- qa-typescript rules v1 (2026-11-03): core. Installed by /qa-typescript:rules; edit the paths above to where this project keeps its test suites, re-run to compare with the plugin's copy. -->

# TypeScript test-automation standards

Apply these to every test, page object, client, fixture and helper you write, edit or review in a TypeScript test suite (Vitest + fetch + Zod, Playwright, WebdriverIO/Appium, playwright-bdd/CucumberJS). The tag after a rule is the severity a review reports: **blocker** ships a bug or breaks a security rule, **major** is a design or correctness problem, **minor** is style, **nit** is preference. API, UI, mobile, BDD, k6, LLM-eval and CI rules are separate files that load with those files.

**The codebase wins.** Where this suite consistently does something another way (Jest over Vitest, Mocha over Vitest, its own folder layout), follow it and do not flag it. Detect the versions before writing: the Node major (24 primary, 22 maintenance; Node 20 is end of life, flag it), `@playwright/test` (1.64 on this lane; `locator.within()`, `page.webmcp` and `getByRef` need 1.64), WebdriverIO 10 + Appium 3 (a device cloud still on Appium 2 stays on WebdriverIO 9). Never use an API the pinned version lacks, and never flag a down-level suite for lacking one.

## Simplicity

- Write the simplest test that proves the behaviour, then stop. No wrapper or DSL over the runner, driver or HTTP client, no base class where a plain helper does, no fixture, builder or helper with one caller. Extract on the second real need. *major, fix by inlining*
- Cut structure, never rigour: one behaviour per test, single-value assertions, condition waits, loud failures and independent tests all stay.

## Tests

- Names state behaviour: `Should_X_When_Y` (or the suite's established form), grouped by one `describe` per feature or endpoint. *minor*
- Every test asserts; one logical behaviour per test. Several `expect` calls are fine when they check one behaviour. *blocker when nothing is asserted, else major*
- Every assertion expects one value, never an `OR`: no `||` inside an `expect`, no `expect([a, b]).toContain(x)`, no `/a|b/` alternation, no `oneOf`. Split per outcome or parameterize; an instruction to accept several values is recorded on the assertion. *major*
- A failure names its subject and carries the evidence: `expect(dto.status, \`order ${id} status\`).toBe('paid')`. *minor*
- No `if` or loop driving assertions; rows that differ only in data become one generated test per row (`it.each`, `test.for`, a case array outside the body). *major*
- Tests are independent and run in any order: no `describe.serial`, no module-level `let` reassigned by tests, no test reading what another created. *blocker*
- What a test creates is tracked and removed in a teardown hook or fixture teardown, never inline or in a `try`/`finally`. *major*

## Errors

- No `try`/`catch`/`finally` in a test body or a cleanup hook, and no `.catch(() => {})`. An expected rejection is `await expect(p).rejects…`; an unexpected one reaches the runner untouched. *major*
- A `catch` lives only in an I/O helper that narrows one named error and logs or rethrows it; never a blanket catch, never a silent default. *major*
- A failed parse names what broke: `safeParse` inside a helper that throws with `issues[].path`, `issues[].code` and the raw body. Never loosen a schema (`.passthrough()`, `.optional()`) to make a drifted contract pass. *major*

## Waiting and async

- No sleeps of any length: no `waitForTimeout`, `browser.pause`, `setTimeout` promise. Wait on a condition (web-first assertion, `expect.poll`, `vi.waitFor`, `waitUntil`). *blocker*
- Every promise is awaited, Allure calls included; `no-floating-promises` stays on. *blocker*
- `strict: true`; no `any`, no `as unknown as X`, no `@ts-ignore` or bare `eslint-disable` to silence a type. *major*

## Data, config and secrets

- Test data with four or more fields comes from a builder or ObjectMother: pure (no persistence, no async), typed as the real DTO, with deterministic defaults that form a valid object (no `Date.now()`, no randomness on an asserted field). *minor*
- No hardcoded base URL, host, credential or token; read them through the suite's config loader and auth helper, failing fast when missing. *blocker*
- No secret, token or real personal data in code, committed data files, logs or report attachments; synthetic data only. *blocker*
- No `console.log` in tests; use the runner's steps and reporter. *minor*

## Flakes and reporting

- `retries: 0`. A flaky test is quarantined with a tag, a ticket and an owner and still runs in a non-gating lane; never `skip`/`fixme` as quarantine, never raise retries to go green. A deterministic failure is a bug, not a flake. *major*
- A skipped test carries its reason and ticket. *minor*
- Allure runtime calls come from `allure-js-commons`; never attach a secret or token. *major*

## Comments

- No comments inside a test or page-object body: no AAA banners, no step markers, no commented-out code, no `TODO`. A step that needs one becomes a named method. *minor; major when the comment is wrong*
- Permitted in tests only: a linked defect id, a recorded instruction to deviate from these rules, or the source of a magic value. TSDoc only where a name cannot carry a non-obvious contract. Scaffolded template comments are removed. *nit*
