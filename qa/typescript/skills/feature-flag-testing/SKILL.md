---
name: qa-feature-flag-testing-typescript
description: Use when testing feature-flagged code in Node 24 (22 supported) / TypeScript / Vitest — pin flag state in-process with OpenFeature's `InMemoryProvider` or LaunchDarkly's `TestData` fixture (never a live flag service), cover BOTH sides of every flag, drive targeting through the evaluation context. Triggers: "test a feature flag", "test both sides of a flag", "pin a flag state in tests".
---

# QA — Feature-Flag Testing (Node 20 + TypeScript / OpenFeature + LaunchDarkly `TestData` + Vitest)

Scaffolds **deterministic feature-flag tests** in TypeScript for code whose behavior branches on a flag, using
[**OpenFeature**](https://openfeature.dev) — the CNCF vendor-neutral flag API — with its built-in
**`InMemoryProvider`** as the test spine, and [**LaunchDarkly**](https://launchdarkly.com)'s Node server SDK
**`TestData`** fixture as the named real-provider path (the two compose: production code talks OpenFeature, the
LaunchDarkly OpenFeature provider sits behind it, and `TestData` pins what that provider sees). This is a
**ported sibling** of the **canonical** `qa-feature-flag-testing-java` — same four ideas, same fixtures, same
section order; the SDK surface is `@openfeature/server-sdk` + `@launchdarkly/node-server-sdk` and the runner is
Vitest.

> **The discipline this skill encodes** — four ideas that separate a correct flag test from an
> environment-coupled reflex:
>
> 1. **PIN the flag, don't fetch it.** A feature-flag test **never evaluates against a live/remote flag
>    service** — the reflex "run against whatever the environment's flags say" makes the test nondeterministic
>    (someone flips a flag → your suite changes meaning), environment-coupled, and structurally incapable of
>    testing the *other* branch. Instead the test **wires an in-memory/test data source in setup** — OpenFeature's
>    `InMemoryProvider`, or LaunchDarkly's `TestData` — and pins exactly the flag state the scenario needs. **The
>    production SDK key never appears in a test run.**
> 2. **A flag is a branch — test BOTH sides.** Shipping a flag means shipping *two* code paths (or N, for a
>    multivariate flag); a suite that only runs with the flag on has zero coverage of the path your users on the
>    old experience are living in — and zero proof the rollback is safe. Every flag-touching behavior gets a
>    **matrix**: on/off for a boolean, every variation for a multivariate — bound as parameterized rows
>    (`qa-data-driven-testing-typescript` mechanics, `it.each`), not copy-pasted test blocks.
> 3. **Targeting rules are tested via the evaluation context.** "Beta users get the new checkout" is a *rule*,
>    not a constant — so the test feeds **user/segment attributes** through the `EvaluationContext` (OpenFeature)
>    / `LDContext` (LaunchDarkly) and asserts the right variation lands for a matching context, a non-matching
>    context, **and the fallthrough/default** (the forgotten third case). With `TestData` the *real* LaunchDarkly
>    evaluation engine runs your rule — you're testing the targeting semantics, not a hand-rolled stub of them.
> 4. **Flag lifecycle is part of the discipline.** A kill-switch only earns its name if flipping it **mid-flight**
>    actually degrades gracefully — `td.update(...)` propagates to a live client like a streamed change, so one
>    test proves the off-path engages *without a restart* (the flag analogue of `qa-chaos-testing-typescript`'s
>    heal-and-recover). And flag state is **cleaned between tests** (fresh provider/fixture per test or rebuilt
>    in `beforeEach`) so a pinned flag never leaks into the next test — test independence.

## Decision matrix — flag scenario → mechanism → what you assert

| You want to prove | Pin via | Assert |
|---|---|---|
| **Behavior with the flag ON** | `InMemoryProvider` flag `defaultVariant: 'on'` / `td.flag(k).variationForAll(true)` | the new path's behavior (response shape, UI state, side effect) |
| **Behavior with the flag OFF** (the rollback path) | same fixture, `'off'` / `variationForAll(false)` | the **legacy** path still works — the branch your un-migrated users live in |
| **Every variation of a multivariate flag** | `variants` map / `variations(...)` + an `it.each` matrix | one row per variation; the matrix is exhaustive (idea #2) |
| **A targeting rule routes the right users** | `contextEvaluator` (OpenFeature) / `ifMatch(...).thenReturn(...)` (TestData — real LD rule engine) | matching context → new variation; non-matching → fallthrough; **default asserted explicitly** |
| **A specific user/key is targeted** | `td.flag(k).variationForContext('user', 'user-key', true)` | that key gets the variation; any other key gets the fallthrough |
| **The kill-switch degrades gracefully mid-flight** | flip with `td.update(...)` while the client is live | before: feature on; after the flip (no restart): the off-path/fallback engages |
| **The code uses the contracted default when evaluation fails** | unknown flag key / no provider for the domain | the *code default* (the value passed to `getBooleanValue(key, default)`) drives a safe path |
| **Flag state never leaks between tests** | fresh fixture per test (`beforeEach`) | any test runs alone and in any order — independence |

## Stack

- Node 20 + TypeScript (strict), **Vitest** (the global default TS runner) + Allure via `allure-vitest` where used
- **OpenFeature** — `@openfeature/server-sdk` — the vendor-neutral API the *production code* talks
  (`client.getBooleanValue/getStringValue/...`), plus the built-in test spine: **`InMemoryProvider`** + the
  flag-configuration map (variants + `defaultVariant` + `contextEvaluator`)
- **LaunchDarkly server SDK** — `@launchdarkly/node-server-sdk` — for projects on LaunchDarkly; its
  `integrations.TestData` fixture is the deterministic data source (`{ updateProcessor: td.getFactory() }`)
- **LaunchDarkly OpenFeature provider** — `@launchdarkly/openfeature-node-server` — bridges the two: prod code
  stays on OpenFeature, `TestData` pins what the LD provider sees (the provider accepts `LDOptions`, so the
  TestData factory threads straight through)
- Layout: `tests/flags/` (the flag tests), `tests/support/flags/` (the `FlagFixture` helper)

```jsonc
// package.json (devDependencies excerpt)
{
  "devDependencies": {
    "vitest": "^2.1.8",
    "@openfeature/server-sdk": "^1.17.0",              // includes InMemoryProvider
    "@launchdarkly/node-server-sdk": "^9.10.0",        // includes integrations.TestData
    "@launchdarkly/openfeature-node-server": "^1.0.0"
  }
}
```

> **Which path?** **OpenFeature `InMemoryProvider`** when the code under test talks the OpenFeature API (the
> recommended posture — vendor-neutral, no LD dependency in the test). **LaunchDarkly `TestData`** when the code
> talks the LD SDK directly, *or* when you need the **real LD evaluation engine** to run a targeting rule /
> per-context target / fallthrough exactly as production would (idea #3). They compose via the LD OpenFeature
> provider. Either way the production SDK key and the live flag service are **absent from the test**.

## Deep-dive reference

These sections live in `references/details.md` — **read it when the task touches them**: **Path B — LaunchDarkly `TestData` (the named real-provider path)**; **Path A — OpenFeature `InMemoryProvider` (the vendor-neutral spine, idea #1)**.

## The code default — the third state every flag has

Every evaluation carries a **code default** (`getBooleanValue('key', false)` / `boolVariation(..., false)`) used
when the flag is missing or the provider isn't ready. That default is a *contract*: it must select the **safe**
branch. Test it by evaluating a key the fixture never defined.

```typescript
it('should fall back to the safe legacy path when the flag is unknown', async () => {
  const flags = await new FlagFixture('checkout').client(); // NO flags pinned at all

  const checkout = new CheckoutService(flags);

  // The code default (false → classic) drives the behavior — the safe branch, asserted explicitly.
  await expect(checkout.startCheckout('sku-1')).resolves.toMatchObject({ flow: 'classic-checkout' });
});
```

## The boundary — flag *testing* vs flag *management*

This skill tests **code that branches on a flag**, with the flag state pinned in-process. It is **not** flag
management or rollout strategy: creating flags in the dashboard, percentage rollouts, prerequisites,
experimentation/A-B *analytics*, or flag-cleanup tooling are platform ops, out of scope. Two adjacent boundaries
worth drawing every time: stale-flag hygiene (a flag whose both-sides tests have asserted the same behavior for
months is a removal candidate — flag it in review, don't let the matrix rot), and the kill-switch *off-path
behavior* (this skill) vs a *dependency fault* behind it (`qa-chaos-testing-typescript`).

## Anti-patterns

- **Evaluating against the live/remote flag service** (the production SDK key + streaming connection in a test).
  Nondeterministic, environment-coupled, and someone flipping a dashboard toggle changes what your suite means.
  *Fix:* `InMemoryProvider` / `TestData` wired in setup; the live service and real key never appear (idea #1).
- **Stubbing the flag service's HTTP endpoint with MSW.** You'd be reverse-engineering the SDK's wire protocol
  (polling/streaming payload shapes) — brittle and pointless when the SDK ships a **first-class test fixture**.
  *Fix:* the SDK's own test source.
- **Testing only the flag-on path.** Zero coverage of the branch your un-migrated users run, zero proof the
  rollback is safe. *Fix:* the on/off (or all-variations) matrix — every flag-touching behavior, both sides (idea #2).
- **Asserting only "no error" on the off-row.** The legacy branch has its *own* contract. *Fix:* the off-row
  asserts the legacy behavior as specifically as the on-row asserts the new one.
- **Hand-rolling a targeting stub instead of testing the rule.** `vi.fn().mockReturnValue(true)` on an
  `isEnabled` wrapper bypasses the targeting semantics entirely. *Fix:* feed attributes through the
  `EvaluationContext` / `LDContext` and let the (in-memory or real-LD) engine evaluate; assert matching,
  non-matching, **and fallthrough** (idea #3).
- **Forgetting the fallthrough/default cases.** Targeting bugs live where no rule matches — and the *code default*
  is a separate, third state. *Fix:* one assertion per case: match / no-match / fallthrough; plus the
  unknown-flag test for the code default.
- **Flag state leaking between tests.** A test that pins `new-checkout=on` in a shared singleton poisons every
  test after it — order-dependent failures. *Fix:* fresh fixture per test (`beforeEach`), domain-scoped
  OpenFeature clients (the `OpenFeature` singleton is shared state — scope it), `close()` the `LDClient` in
  `afterEach`.
- **`if (flagEnabled) { expect A } else { expect B }` inside one test.** Conditional logic in tests is banned —
  and it means the test passes no matter which branch ran. *Fix:* the parameterized matrix: one `it.each` row per
  state, each with its own expected value.
- **Skipping `waitForInitialization` / `setProviderAndWait`.** The first evaluation races initialization and
  silently returns the code default — a green test proving nothing. *Fix:* await readiness in the fixture before
  handing the client out.
- **Treating a kill-switch as config you only test statically.** A kill-switch that's never been flipped
  mid-flight in a test is a hope, not a control. *Fix:* the lifecycle test — on → `td.update(off)` /
  `putConfiguration` → assert the degradation path, no restart (idea #4).

## Examples

**End-to-end: the inverted reflex.** An environment-coupled suite reads
`getBooleanValue('new-checkout', false)` against whatever the staging environment says — green Monday, red
Tuesday, and the off-path never runs. This skill's author writes: a `FlagFixture` pinning `new-checkout` per row,
a two-row `it.each` matrix asserting `express-checkout` *and* `classic-checkout`, a context test for the beta
rule with the fallthrough asserted, and a kill-switch flip test. Same flag, deterministic — and **both** branches
covered.

**Composing with the neighbors.** The branch under test often *contains* the things other skills assert — the
on-path writes a new table (`qa-db-testing-client-typescript`), emits a new event
(`qa-messaging-testing-typescript`), or renders a new page (`qa-ui-test-author-playwright-typescript`). This
skill pins which branch runs; those skills assert what the branch does. The variation matrix binds through
`qa-data-driven-testing-typescript`; the kill-switch degradation assertion borders `qa-chaos-testing-typescript`
(flag flip vs dependency fault — adjacent, not the same).

## Rules (hard constraints)

- **Pin the flag state in-process — never evaluate against a live/remote flag service in a test.** OpenFeature
  `InMemoryProvider` or LaunchDarkly `TestData`, wired in setup. The production SDK key never appears in a test
  run (and no real key in code anyway — no secrets in code).
- **Every flag-touching behavior is tested on BOTH sides** (every variation for multivariate) via a parameterized
  `it.each` matrix — never only the on-path, never conditional logic inside a test.
- **The off-row asserts the legacy branch's own contract**, not merely "no error".
- **Targeting rules are exercised through the evaluation context** (OpenFeature `EvaluationContext` /
  `LDContext`), asserting match, no-match, **and the fallthrough/default** — plus the **code default** via an
  unknown-flag evaluation.
- **Don't stub the flag service's HTTP wire** — use the SDK's first-class test source; MSW is for dependencies
  that lack one.
- **Kill-switches get a lifecycle test**: on → flip via `td.update(...)` / `putConfiguration` mid-flight → assert
  the degradation path engages without a restart.
- **Flag state never leaks between tests**: fresh fixture per test, domain-scoped OpenFeature clients (the
  `OpenFeature` singleton is shared state), `close()` the `LDClient` in teardown. Tests run alone, in any order.
- **The flag client is constructor-injected** into the code under test — never a static lookup. Vitest, strict
  TypeScript; **await readiness** (`setProviderAndWait` / `waitForInitialization`) so the first evaluation never
  races initialization.

## Cross-references

- `qa-feature-flag-testing-java` — the **canonical** stack this sibling is ported from (`dev.openfeature:sdk` +
  `launchdarkly-java-server-sdk` `TestData` + TestNG); same four ideas, same fixtures, different SDK surface.
- `qa-feature-flag-testing-dotnet` — the other sibling (`OpenFeature` NuGet + `LaunchDarkly.ServerSdk` `TestData`
  + NUnit).
- `qa-data-driven-testing-typescript` — the **matrix mechanics** the on/off/variation table binds through
  (`it.each` row-binding); this skill defines *what* the rows are, that one defines *how* rows drive tests.
- `qa-chaos-testing-typescript` — the **kill-switch boundary**: the off-path of a flag flip is this skill;
  a faulted dependency behind the feature is chaos. The lifecycle shape (steady → perturb → assert-degraded) is shared.
- `qa-api-test-author-generator-typescript` · `qa-ui-test-author-playwright-typescript` — the branch under test
  is usually an API or UI behavior; those skills own the assertion style inside each pinned branch.
- `qa-auth0-test-tokens-typescript` — the same "test fixture over live service" posture applied to auth;
  pairs when targeting rules key off claims-derived attributes.
- `qa-allure-reporting-typescript` — render the flag matrix as named results (one per variation row).
