---
name: qa-feature-flag-testing-typescript
description: >-
  Write **feature-flag** tests in Node 20 + TypeScript (strict) with **OpenFeature**
  (`@openfeature/server-sdk` + its built-in **`InMemoryProvider`**) as the vendor-neutral spine and
  **LaunchDarkly** (`@launchdarkly/node-server-sdk` + its first-class **`TestData`** fixture) as the named
  real-provider path + Vitest, proving code whose behavior **branches on a flag** is correct on EVERY branch.
  Covers the trait that makes a flag test deterministic: **you NEVER evaluate the flag against a live/remote
  flag service — you PIN the flag state inside the test** (an in-memory/test data source wired in setup; the
  production SDK key never appears in a test run), because "run against whatever the environment's flags say"
  makes the test nondeterministic, environment-coupled, and incapable of exercising the *other* branch. The
  discipline: **a flag is a branch — test BOTH sides** (and every variation of a multivariate flag) as a matrix;
  **targeting rules are tested via the evaluation context** (user/segment attributes in the OpenFeature
  `EvaluationContext` / `LDContext` → assert the right variation lands, incl. the fallthrough/default); **flag
  lifecycle is part of the test** (flip a kill-switch mid-test via `td.update(...)` and assert the degradation
  path engages without a restart; clean flag state between tests so it never leaks). Covers the OpenFeature
  flag-configuration map (variants + `defaultVariant` + `contextEvaluator`), `setProviderAndWait` with
  domain-scoped clients, `putConfiguration`, LaunchDarkly `new integrations.TestData()` →
  `{ updateProcessor: td.getFactory() }`, the flag builder
  (`booleanFlag`/`variations`/`variationForContext`/`ifMatch`/`fallthroughVariation`), `sendEvents: false`, and
  the LaunchDarkly OpenFeature provider bridging both. Triggers: "test a feature flag / feature toggle", "test
  both sides of a flag", "pin a flag state in tests", "test LaunchDarkly targeting rules", "OpenFeature
  InMemoryProvider test", "test the kill-switch path", "our test fails depending on which flags are on in the
  environment". Do NOT use for: the Java stack (use qa-feature-flag-testing-java), the .NET stack (use
  qa-feature-flag-testing-dotnet), stubbing the flag service's **HTTP endpoint** with MSW (use the SDK's test
  data source instead — mocking the wire is the anti-pattern here, see qa-api-mocking-msw-typescript only for
  dependencies that have no test fixture), standing the flag service up as a **container** (flag state is pinned
  in-process, not via qa-test-environments-typescript), **dependency-fault** resilience (a broken DB/API is
  qa-chaos-testing-typescript; a kill-switch *flag* flip is this skill), the generic **parameterized-matrix
  mechanics** (qa-data-driven-testing-typescript — the on/off table binds through it), or flag
  **management/rollout strategy** (percentage rollouts, experimentation/A-B analytics, dashboard ops — out of
  scope).
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

## Path A — OpenFeature `InMemoryProvider` (the vendor-neutral spine, idea #1)

The provider is the seam. Production code asks an OpenFeature `Client` for flag values; the test swaps in an
`InMemoryProvider` holding exactly the flags the scenario pins. **Use a domain-scoped provider + client**
(`setProviderAndWait('checkout', ...)` / `getClient('checkout')`) — the `OpenFeature` singleton is global state,
and a domain keeps parallel test files from clobbering each other's provider. In Node the flag's
`contextEvaluator` returns the **variant key** for a given context.

```typescript
// tests/support/flags/flag-fixture.ts
import {
  Client,
  EvaluationContext,
  InMemoryProvider,
  OpenFeature,
  type FlagConfiguration,
} from '@openfeature/server-sdk';

/** Pins flag state for one test: a fresh InMemoryProvider per fixture, bound to a domain-scoped client. */
export class FlagFixture {
  private readonly flags: FlagConfiguration = {};

  constructor(private readonly domain: string) {}

  /** Pin a boolean flag to a fixed state — the simplest "pin, don't fetch". */
  withBooleanFlag(key: string, enabled: boolean): this {
    this.flags[key] = {
      disabled: false,
      variants: { on: true, off: false },
      defaultVariant: enabled ? 'on' : 'off',
    };
    return this;
  }

  /** Pin a multivariate flag to one named variant (test EVERY variant via the matrix, idea #2). */
  withVariant<T>(key: string, variants: Record<string, T>, selected: string): this {
    this.flags[key] = { disabled: false, variants, defaultVariant: selected };
    return this;
  }

  /** Pin a context-aware rule: the evaluator picks the VARIANT KEY from the EvaluationContext (idea #3). */
  withRule<T>(
    key: string,
    variants: Record<string, T>,
    defaultVariant: string,
    variantForContext: (ctx: EvaluationContext) => string,
  ): this {
    this.flags[key] = { disabled: false, variants, defaultVariant, contextEvaluator: variantForContext };
    return this;
  }

  /** Wire the pinned flags in and return the client the code under test should use. */
  async client(): Promise<Client> {
    await OpenFeature.setProviderAndWait(this.domain, new InMemoryProvider(this.flags)); // awaits READY — no race
    return OpenFeature.getClient(this.domain);
  }
}
```

### Both sides of the branch — the on/off matrix (idea #2)

One parameterized test per flag-touching behavior; one row per flag state. The rows pin the flag; the assertions
verify **each branch's own contract** — the off-row asserts the *legacy* behavior, not merely "no error".

```typescript
// tests/flags/checkout-flag.test.ts
import { describe, expect, it } from 'vitest';
import { FlagFixture } from '../support/flags/flag-fixture';
import { CheckoutService } from '../../src/checkout/checkout-service';

describe('checkout flow under the new-checkout flag', () => {
  // flagState | expectedFlow — BOTH sides, every run (idea #2)
  it.each([
    { enabled: true,  expectedFlow: 'express-checkout' },
    { enabled: false, expectedFlow: 'classic-checkout' },
  ])('should route to $expectedFlow when the flag is $enabled', async ({ enabled, expectedFlow }) => {
    const flags = await new FlagFixture('checkout')
      .withBooleanFlag('new-checkout', enabled) // PINNED — not fetched (idea #1)
      .client();

    const checkout = new CheckoutService(flags); // constructor injection — the client is a dependency

    const result = await checkout.startCheckout('sku-1');
    expect(result.flow).toBe(expectedFlow);
  });
});
```

> The off-row is **not** a formality: it is the only coverage of the path every un-migrated user is on, and the
> only proof a rollback is safe. A multivariate flag gets one row per variation — exhaustively (`control` /
> `treatment-a` / `treatment-b`), via the same `it.each` mechanics as `qa-data-driven-testing-typescript`.

### Targeting via the evaluation context (idea #3)

The rule lives in the fixture; the test varies the **context** and asserts three cases — matching, non-matching,
and **the fallthrough/default** (the case targeting bugs hide in).

```typescript
it('should serve the new checkout only to beta-tier users', async () => {
  const flags = await new FlagFixture('checkout')
    .withRule('new-checkout', { on: true, off: false }, 'off', (ctx) =>
      ctx.tier === 'beta' ? 'on' : 'off',
    )
    .client();

  const betaUser   = { targetingKey: 'user-1', tier: 'beta' };
  const freeUser   = { targetingKey: 'user-2', tier: 'free' };
  const anonNoTier = { targetingKey: 'user-3' };               // the forgotten third case

  await expect(flags.getBooleanValue('new-checkout', false, betaUser)).resolves.toBe(true);   // matching
  await expect(flags.getBooleanValue('new-checkout', false, freeUser)).resolves.toBe(false);  // non-matching
  await expect(flags.getBooleanValue('new-checkout', false, anonNoTier)).resolves.toBe(false); // fallthrough
});
```

## Path B — LaunchDarkly `TestData` (the named real-provider path)

`new integrations.TestData()` replaces LaunchDarkly's streaming connection with a programmable in-process source
— the **real LD evaluation engine** runs your targeting rules against it. Wire it in via
`{ updateProcessor: td.getFactory(), sendEvents: false }` (no analytics leave the test) — the SDK key is a
placeholder, never the production key.

```typescript
// tests/support/flags/launchdarkly-fixture.ts
import { init, integrations, type LDClient } from '@launchdarkly/node-server-sdk';

/** A deterministic LDClient: TestData replaces the stream; no events; placeholder key. */
export class LaunchDarklyFixture {
  readonly data = new integrations.TestData();
  readonly client: LDClient;

  constructor() {
    this.client = init('test-sdk-key-not-real', {
      updateProcessor: this.data.getFactory(), // PINNED in-process — never the live service (idea #1)
      sendEvents: false,                       // no analytics calls leave the test run
    });
  }

  async ready(): Promise<void> {
    await this.client.waitForInitialization({ timeout: 10 });
  }

  close(): void {
    this.client.close();
  }
}
```

### Targeting with the real rule engine — `ifMatch` / `variationForContext` / fallthrough

```typescript
// tests/flags/beta-targeting.test.ts
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { LaunchDarklyFixture } from '../support/flags/launchdarkly-fixture';

describe('beta targeting for the new checkout', () => {
  let ld: LaunchDarklyFixture;

  beforeEach(async () => {
    ld = new LaunchDarklyFixture(); // fresh state — no leakage between tests (idea #4)
    await ld.ready();
  });

  afterEach(() => ld.close());

  it('should target beta tier and one named user, and fall through for everyone else', async () => {
    await ld.data.update(
      ld.data
        .flag('new-checkout')
        .booleanFlag()
        .variationForContext('user', 'qa-canary', true)   // a per-context target
        .ifMatch('user', 'tier', 'beta').thenReturn(true) // a rule — evaluated by the REAL engine
        .fallthroughVariation(false),                     // the explicit default
    );

    const canary = { kind: 'user', key: 'qa-canary' };
    const beta   = { kind: 'user', key: 'user-7', tier: 'beta' };
    const free   = { kind: 'user', key: 'user-9', tier: 'free' };

    await expect(ld.client.boolVariation('new-checkout', canary, false)).resolves.toBe(true);  // named key
    await expect(ld.client.boolVariation('new-checkout', beta, false)).resolves.toBe(true);    // rule match
    await expect(ld.client.boolVariation('new-checkout', free, false)).resolves.toBe(false);   // fallthrough
  });
});
```

### The kill-switch lifecycle — flip mid-flight, assert graceful degradation (idea #4)

`td.update(...)` propagates to the live client **as if LaunchDarkly streamed the change** — so one test proves
the off-path engages *without a restart*. This is the flag analogue of `qa-chaos-testing-typescript`'s
steady → perturb → assert-degraded lifecycle (and the boundary: a *flag* flip is this skill; a *dependency fault*
is chaos).

```typescript
it('should engage the recommendations fallback when the kill-switch flips mid-flight', async () => {
  await ld.data.update(ld.data.flag('recommendations-enabled').booleanFlag().variationForAll(true));
  const page = new ProductPageService(ld.client);

  // 1. steady state — the feature is on and serving.
  await expect(page.render('sku-1')).resolves.toMatchObject({ hasRecommendations: true });

  // 2. flip the kill-switch — no restart, no redeploy; propagates like a streamed change.
  await ld.data.update(ld.data.flag('recommendations-enabled').booleanFlag().variationForAll(false));

  // 3. assert the DEGRADED path: the page still renders, recommendations replaced by the contracted fallback.
  const degraded = await page.render('sku-1');
  expect(degraded.isRendered).toBe(true);                 // page survives the kill
  expect(degraded.hasRecommendations).toBe(false);        // feature is off
  expect(degraded.fallbackMessage).toBe('Recommendations are temporarily unavailable');
});
```

> On the OpenFeature path the same lifecycle runs through **`provider.putConfiguration({...})`** — it replaces
> the in-memory flag set and emits a configuration-changed event to the live client.

### Bridging both — prod code on OpenFeature, `TestData` behind the LD provider

When production talks OpenFeature but the org runs LaunchDarkly, compose the two: the LD OpenFeature provider
accepts `LDOptions`, so the `TestData` factory threads straight through and the code under test stays
vendor-neutral.

```typescript
import { LaunchDarklyProvider } from '@launchdarkly/openfeature-node-server';

const ldProvider = new LaunchDarklyProvider('test-sdk-key-not-real', {
  updateProcessor: ld.data.getFactory(), // TestData behind the LD provider
  sendEvents: false,
});
await OpenFeature.setProviderAndWait('checkout', ldProvider);
const flags = OpenFeature.getClient('checkout'); // prod-shaped: pure OpenFeature
```

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
  *Fix:* the SDK's own test source; reserve `qa-api-mocking-msw-typescript` for dependencies without one.
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
(`qa-messaging-testing-sqs-typescript`), or renders a new page (`qa-ui-test-author-playwright-typescript`). This
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
- `qa-data-driven-testing-typescript` (#39) — the **matrix mechanics** the on/off/variation table binds through
  (`it.each` row-binding); this skill defines *what* the rows are, that one defines *how* rows drive tests.
- `qa-chaos-testing-typescript` (#48) — the **kill-switch boundary**: the off-path of a flag flip is this skill;
  a faulted dependency behind the feature is chaos. The lifecycle shape (steady → perturb → assert-degraded) is shared.
- `qa-api-mocking-msw-typescript` (#23) — what **not** to reach for here: the flag SDKs ship first-class test
  sources, so stubbing their wire protocol is the anti-pattern; MSW covers dependencies without a fixture.
- `qa-test-environments-typescript` (#14) — stands real dependencies up in containers; flag state is pinned
  **in-process**, no container needed — don't stand up a flag service to test a branch.
- `qa-api-test-author-generator-typescript` · `qa-ui-test-author-playwright-typescript` — the branch under test
  is usually an API or UI behavior; those skills own the assertion style inside each pinned branch.
- `qa-auth0-test-tokens-typescript` (#16) — the same "test fixture over live service" posture applied to auth;
  pairs when targeting rules key off claims-derived attributes.
- `qa-allure-reporting-typescript` — render the flag matrix as named results (one per variation row).
