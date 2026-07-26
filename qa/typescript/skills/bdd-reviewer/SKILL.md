---
name: qa-bdd-reviewer-typescript
description: Use when reviewing existing Gherkin .feature files and TypeScript step definitions (playwright-bdd web, CucumberJS + WebdriverIO mobile) for living-documentation quality, step reusability, and correct binding/state/lifecycle. Triggers: "review these feature files", "audit our playwright-bdd step definitions", "check our BDD layer". Do NOT use to generate features (`feature-file-writer`) or step definitions (`gherkin-step-code`). For end-to-end suite work prefer the phased agent `qa-bdd-typescript` (or the matching slash command), which loads this skill inside its workflow; use this skill directly for a single targeted artifact.
---

# BDD / Gherkin Reviewer (TypeScript)

Audits a BDD layer across **two surfaces** — the `.feature` files (Gherkin quality / living documentation) and the TypeScript step definitions + support code (binding correctness, reuse, the **state model**, async, library rules). TypeScript has two frameworks; the binding checklist below has a shared core plus **two model-specific blocks** — apply the one(s) the project uses. Returns findings in the standard table; does not rewrite code.

## When to use

- A `.feature` + `steps/` set exists and needs a critique.
- Steps report undefined/ambiguous matches, or the suite is flaky/duplicative.
- A PR adds BDD coverage and you want a hostile senior review.

## When NOT to use

- "Write feature files" → `qa/_shared/bdd/feature-file-writer`
- "Generate / implement step definitions" → `qa/typescript/skills/gherkin-step-code`
- Code is pseudocode / incomplete → ask for the real files.

## Procedure

1. Identify the framework (web playwright-bdd vs mobile CucumberJS+WDIO — check `package.json`, `playwright.config.ts` vs `wdio.conf.ts`).
2. Read every `.feature` file and every step file + the support layer (`steps/fixtures.ts` for web; `support/world.ts` + `support/hooks.ts` for mobile). Do not skim.
3. Walk the Gherkin checklist + the shared binding checklist + the model-specific block(s) that apply, marking each item pass / fail / N/A.
4. Produce findings in the standard table. Point to fixes; do not rewrite.
5. Close with an "Overall" paragraph and a coverage/traceability note (every TC-ID + AC accounted for?).

## Gherkin checklist (`.feature` files)

- [ ] Steps are declarative — no `click`/`type`/CSS/URLs unless the mechanic is the subject under test.
- [ ] One event under test per scenario (one `When`); no conjunction steps.
- [ ] `Background` holds only preconditions every scenario needs; no `When`/`Then`/data in it.
- [ ] Data-driven variants use `Scenario Outline` + `Examples`, one behavior per outline; valid/invalid split into separate `Examples` (invalid tagged `@negative`).
- [ ] Steps reuse a canonical catalog — no near-duplicate steps differing only by a literal; one verb per concept.
- [ ] Tags carry priority (`@p1..`), tier (`@smoke`/`@regression`), type (`@negative`/`@boundary`/`@edge`), and AC traceability (`@AC-<n>`).
- [ ] Each scenario reads as documentation without the code; names state behavior, not data.
- [ ] Every TC-ID / AC from the source suite maps to a scenario (no silent gaps).

## Binding checklist — shared core (both frameworks)

- [ ] Step definitions split by domain (no mega `steps.ts`); each catalog step bound exactly once.
- [ ] Cucumber Expressions (`{string}`/`{int}`/`{float}`/…) over regex unless regex is genuinely needed.
- [ ] No selectors / `page.locator(...)` / `browser.$(...)` / waits in step definitions — mechanics live in page objects.
- [ ] `Then` steps assert; `Given`/`When` don't assert; page objects don't assert (except `expectLoaded()` / `verifyPageLoaded()`).
- [ ] `async` step bodies; every page-object call awaited; no floating promises; strict TS (no `as any` in step signatures).
- [ ] No `page.waitForTimeout` / `browser.pause(ms)` — auto-wait + web-first/WDIO assertions only.
- [ ] Cucumber-Expression captures typed explicitly (`(email: string)`), not `any`.
- [ ] Cleanup implemented as fixture teardown (web) / `After` hook (mobile), not as Gherkin steps.
- [ ] No hardcoded credentials/URLs — env vars / config.

## Binding checklist — web (playwright-bdd) model block

- [ ] `Given/When/Then` come from `createBdd(test)` where `test` is the fixture-extended `test` (`steps/fixtures.ts`).
- [ ] Steps are **arrow functions** destructuring page-object **fixtures** (`async ({ loginPage }) => …`) — **no World**, no `this`.
- [ ] Page objects registered as fixtures in `steps/fixtures.ts`; **no `new LoginPage(page)`** inside a step.
- [ ] Fixture object is the first argument, inline captures after it, data-table last.
- [ ] `bddgen` runs before `playwright test`; `testDir` points at the generated dir, not `features/`.
- [ ] Web-first assertions (`expect(locator).toHaveText(...)`) in `Then`; no one-shot `expect(await loc.textContent())`.

## Binding checklist — mobile (CucumberJS + WDIO) model block

- [ ] State shared via the **custom `World`** (`setWorldConstructor`, `this.login`) — **not** module-level mutable state.
- [ ] Steps are **`function` expressions** with `this: CustomWorld` typed — **never arrow functions** (arrows lose the World).
- [ ] Screen objects reached through `this`; **no `new LoginScreen()`** inside a step.
- [ ] Driver/session managed by `@wdio/appium-service`; no hand-rolled Appium server start/stop.
- [ ] `Before`/`After` hooks (with **teardown**) live in `support/`; the Cleanup handoff is an `After` hook, not steps.
- [ ] `@cucumber/cucumber` version matches the line `@wdio/cucumber-framework` pins (no broken peer).
- [ ] WDIO `expect` matchers (auto-retry) in `Then`; no `browser.pause` to "stabilize."

## Output format

```
| Severity | Location                       | Issue                                   | Suggested fix                          |
|----------|--------------------------------|-----------------------------------------|----------------------------------------|
| major    | login.feature:12               | Imperative step "tap #submit"           | Raise to "When I sign in…"; move mechanic to LoginScreen |
| major    | authentication.steps.ts:20     | Arrow-function CucumberJS step          | Use `function (this: CustomWorld)`; reach page via this |
| major    | authentication.steps.ts:8      | new LoginPage(page) inside step (web)   | Register a fixture in steps/fixtures.ts; destructure it |
| minor    | cart.steps.ts:8                | Two near-duplicate add-item steps       | Parameterize: "I add {int} items"      |
```

After the table, add an **Overall** paragraph (2–3 sentences) and a **Traceability** line (TC-IDs/ACs covered vs gaps ⚠️).

## Severity guide

- **blocker**: undefined/ambiguous step that fails the run; leaked browser/session; arrow-function World step that throws at runtime; ships a bug.
- **major**: imperative/UI-coupled Gherkin; selectors or `new`/module-state in steps; wrong state model (World in playwright-bdd, or fixtures in CucumberJS); assertion in a page object; conjunction step that hides a second behavior.
- **minor**: duplicate steps that should be parameterized; missing tags; untyped captures; naming.
- **nit**: optional phrasing/style preferences.

## Examples

Input: a `login.feature` whose every scenario repeats `Given I open "/login"` / `When I fill "#email"…` and a single `login.steps.ts` (playwright-bdd) newing up the page object per step with `function`-style bodies.

Findings: imperative steps (major) → factor login into `Background` + declarative step; per-step `new LoginPage` (major) → register a fixture and destructure it; `function`/`this` style in a playwright-bdd project (major) → switch to arrow + fixture destructuring (no World on the web path); mechanics in steps (major) → move to `LoginPage`. Overall: the layer works but reads as a script, not documentation, and uses the wrong state model for the web framework.
